import asyncio
import requests
from xknx import XKNX
from xknx.telegram import Telegram
from xknx.telegram.address import GroupAddress
from xknx.dpt import DPTTemperature, DPTScaling, DPT2ByteFloat

# Współrzędne dla Łodzi
LATITUDE = 51.75
LONGITUDE = 19.46

# --- KONFIGURACJA POŁĄCZENIA KNX ---
# Wpisz IP swojego Gira IP-Routera z laboratorium:
IP_ROUTER_IP = "192.168.1.10"
IP_ROUTER_PORT = 3671

# --- ADRESY GRUPOWE Z DEFINICJI W ETS ---
GA_TEMP = "3/0/1"        # DPT 9.001 Temperature
GA_CLOUD = "3/0/3"       # DPT 5.001 Scaling
GA_IRRADIANCE = "3/0/4"  # DPT 9.022 Solar Radiation

# Czas między wysyłkami (15 sekund na czas testów w ETS)
INTERVAL_SECONDS = 15


async def pobierz_i_wyslij_pogode(knx: XKNX):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"current_weather=true&"
        f"hourly=cloudcover,direct_normal_irradiance"
    )
    
    print("\nWysyłanie zapytania do API Open-Meteo...")
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # 1. Odczyt surowych wartości z JSON
            t_out = data["current_weather"]["temperature"]
            cloud_cover = data["hourly"]["cloudcover"][0]
            direct_irradiance = data["hourly"]["direct_normal_irradiance"][0]
            
            print("\n=================== 1. POBRANE DANE Z API ===================")
            print(f"Temperatura (T_out)     : {t_out} °C")
            print(f"Zachmurzenie            : {cloud_cover} %")
            print(f"Irradiancja bezpośrednia: {direct_irradiance} W/m²")
            
            # 2. KONWERSJA NA FORMATY DPT (KNX)
            dpt_temp_payload = DPTTemperature.to_knx(t_out)
            dpt_cloud_payload = DPTScaling.to_knx(cloud_cover)
            dpt_irradiance_payload = DPT2ByteFloat.to_knx(direct_irradiance)
            
            print("\n=================== 2. KONWERSJA DPT DO KNX ===================")
            print(f"DPT 9.001 (Temp {GA_TEMP})    -> Surowe bajty HEX: {[hex(b) for b in dpt_temp_payload.value]}")
            print(f"DPT 5.001 (Cloud {GA_CLOUD})  -> Surowe bajty HEX: {[hex(b) for b in dpt_cloud_payload.value]}")
            print(f"DPT 9.022 (Irrad {GA_IRRADIANCE}) -> Surowe bajty HEX: {[hex(b) for b in dpt_irradiance_payload.value]}")
            
            # 3. TWORZENIE TELEGRAMÓW KNX
            t_temp = Telegram(
                destination_address=GroupAddress(GA_TEMP),
                payload=dpt_temp_payload
            )
            t_cloud = Telegram(
                destination_address=GroupAddress(GA_CLOUD),
                payload=dpt_cloud_payload
            )
            t_irradiance = Telegram(
                destination_address=GroupAddress(GA_IRRADIANCE),
                payload=dpt_irradiance_payload
            )

            # 4. WYSYŁKA TELEGRAMÓW NA MAGISTRALĘ
            print("\n=================== 3. WYSYŁANIE DO KNX ===================")
            await knx.telegrams.put(t_temp)
            await knx.telegrams.put(t_cloud)
            await knx.telegrams.put(t_irradiance)
            print("Telegramy zostały pomyślnie wysłane do IP-Routera!")
            
        else:
            print(f"Błąd HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"Błąd wykonania: {e}")


async def glowna_petla():
    # Połączenie z Gira IP-Routerem
    knx = XKNX(gateway_ip=IP_ROUTER_IP, gateway_port=IP_ROUTER_PORT)
    await knx.start()
    print(f"[SYSTEM] Nawiązano połączenie z IP-Routerem {IP_ROUTER_IP}:{IP_ROUTER_PORT}")

    try:
        while True:
            await pobierz_i_wyslij_pogode(knx)
            print(f"\n[TIMER] Czekam {INTERVAL_SECONDS} sekund do kolejnego cyklu...")
            await asyncio.sleep(INTERVAL_SECONDS)
            
    except asyncio.CancelledError:
        print("\n[SYSTEM] Zatrzymywanie pętli...")
    finally:
        await knx.stop()
        print("[SYSTEM] Połączenie z KNX zostało bezpiecznie zamknięte.")


if __name__ == "__main__":
    try:
        asyncio.run(glowna_petla())
    except KeyboardInterrupt:
        print("\nProgram został zatrzymany ręcznie.")