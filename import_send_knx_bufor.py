import asyncio
import requests
from datetime import datetime, timezone
from xknx import XKNX
from xknx.telegram import Telegram
from xknx.telegram.address import GroupAddress
from xknx.dpt import DPTTemperature, DPTScaling, DPT2ByteFloat

# ==============================================================================
# 1. KONFIGURACJA STANOWISKA GIRA (P1) I USŁUGI
# ==============================================================================
LATITUDE = 51.75
LONGITUDE = 19.46

# Adres IP Gira KNX IP-Routera na Waszym stanowisku w labie:
IP_ROUTER_IP = "192.168.1.10"
IP_ROUTER_PORT = 3671

# Adresy Grupowy zdefiniowane w ETS dla stacji pogodowej / parametrów
GA_TEMP = "3/0/1"        # DPT 9.001 (Temperatura °C)
GA_WIND = "3/0/2"        # DPT 9.005 (Prędkość wiatru m/s)
GA_CLOUD = "3/0/3"       # DPT 5.001 (Zachmurzenie %)
GA_IRRADIANCE = "3/0/4"  # DPT 9.022 (Irradiancja W/m²)

# Interwał odświeżania (15 sekund, docelowo ≤ 15 min)
INTERVAL_SECONDS = 15

# ==============================================================================
# 2. ZMIENNE GLOBALNE DLA OBSŁUGI JAKOŚCI I BUFOROWANIA 
# ==============================================================================
last_valid_data = {}
consecutive_failures = 0

# ==============================================================================
# 3. LOGIKA API + OBSŁUGA BŁĘDÓW + KONWERSJA + WYSYŁKA KNX
# ==============================================================================
async def pobierz_zkonwertuj_i_wyslij(knx: XKNX):
    global consecutive_failures, last_valid_data
    
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"current_weather=true&"
        f"hourly=cloudcover,direct_normal_irradiance"
    )
    
    # Znacznik czasu UTC (W8)
    ts_utc = datetime.now(timezone.utc).isoformat()
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Resetujemy licznik błędów po pomyślnym odebraniu pakietu
            consecutive_failures = 0
            quality = "GOOD"
            
            # 1. Odczyt surowy i przeliczanie jednostek (W1)
            t_out = data["current_weather"]["temperature"]
            wind_kmh = data["current_weather"]["windspeed"]
            wind_ms = round(wind_kmh / 3.6, 2)  # km/h -> m/s dla DPT 9.005
            cloud_cover = data["hourly"]["cloudcover"][0]
            irradiance = data["hourly"]["direct_normal_irradiance"][0]
            
            # Zapisujemy świeże dane do bufora
            last_valid_data = {
                "t_out": t_out,
                "wind_ms": wind_ms,
                "cloud_cover": cloud_cover,
                "irradiance": irradiance,
                "ts_utc": ts_utc,
                "quality": quality
            }
            
            print(f"\n[{ts_utc}] [Status: {quality}] Pobrano dane z API Open-Meteo:")
            print(f" -> T_out: {t_out} °C | Wiatr: {wind_ms} m/s | Zachmurzenie: {cloud_cover}% | Irradiancja: {irradiance} W/m²")
            
        else:
            raise Exception(f"Błąd HTTP {response.status_code}")
            
    except Exception as e:
        consecutive_failures += 1
        print(f"\n[{ts_utc}] [BŁĄD POŁĄCZENIA API]: {e} (Licznik błędów: {consecutive_failures})")
        
        # Określenie jakości danych wg wymogu W2 (brak aktualizacji przez 2 cykle -> BAD)
        if consecutive_failures == 1:
            quality = "STALE"
        else:
            quality = "BAD"
            
        if last_valid_data:
            last_valid_data["quality"] = quality
            print(f" -> [TRYB ZASTĘPCZY] Używam ostatnich znanych danych z {last_valid_data['ts_utc']} | Status: {quality}")
        else:
            # Domyślny stan zastępczy przy starcie bez sieci
            last_valid_data = {
                "t_out": 20.0,
                "wind_ms": 0.0,
                "cloud_cover": 0,
                "irradiance": 0.0,
                "ts_utc": ts_utc,
                "quality": "UNKNOWN"
            }

    # --- 2. TWORZENIE ŁADUNKÓW DPT I TELEGRAMÓW ---
    d_data = last_valid_data
    
    payload_temp = DPTTemperature.to_knx(d_data["t_out"])
    payload_wind = DPT2ByteFloat.to_knx(d_data["wind_ms"])
    payload_cloud = DPTScaling.to_knx(d_data["cloud_cover"])
    payload_irradiance = DPT2ByteFloat.to_knx(d_data["irradiance"])
    
    telegramy = [
        Telegram(destination_address=GroupAddress(GA_TEMP), payload=payload_temp),
        Telegram(destination_address=GroupAddress(GA_WIND), payload=payload_wind),
        Telegram(destination_address=GroupAddress(GA_CLOUD), payload=payload_cloud),
        Telegram(destination_address=GroupAddress(GA_IRRADIANCE), payload=payload_irradiance)
    ]
    
    # --- 3. WYSYŁKA PO MAGISTRALI KNX DO IP-ROUTERA ---
    try:
        print(f"[KNX] Wysyłanie 4 telegramów do IP-Routera ({IP_ROUTER_IP})...")
        for t in telegramy:
            await knx.telegrams.put(t)
        print("[KNX] Nadanie zakończone pomyślnie.")
    except Exception as knx_err:
        print(f"[BŁĄD KNX]: Nie udało się wysłać telegramu po magistrali: {knx_err}")

# ==============================================================================
# 4. GŁÓWNA PĘTLA ASYNCHRONICZNA APLIKACJI
# ==============================================================================
async def main():
    knx = XKNX(gateway_ip=IP_ROUTER_IP, gateway_port=IP_ROUTER_PORT)
    
    try:
        await knx.start()
        print(f"[SYSTEM] Nawiązano połączenie z Gira KNX IP-Routerem ({IP_ROUTER_IP}:{IP_ROUTER_PORT})")
        
        while True:
            await pobierz_zkonwertuj_i_wyslij(knx)
            print(f"[TIMER] Odczekanie {INTERVAL_SECONDS} s do kolejnego cyklu...")
            await asyncio.sleep(INTERVAL_SECONDS)
            
    except asyncio.CancelledError:
        print("\n[SYSTEM] Zamykanie pętli...")
    finally:
        await knx.stop()
        print("[SYSTEM] Rozłączono z magistralą KNX.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrzerwano działanie skryptu z klawiatury (Ctrl+C).")