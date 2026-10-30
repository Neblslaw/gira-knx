import time
import requests
from xknx.dpt import DPTTemperature, DPTScaling, DPT2ByteFloat

# Współrzędne dla Łodzi
LATITUDE = 51.75
LONGITUDE = 19.46

# Czas między odświeżeniami w sekundach (15 s na czas testów w laboratorium)
INTERVAL_SECONDS = 15

def przetestuj_pobieranie_i_konwersje_dpt():
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"current_weather=true&"
        f"hourly=cloudcover,direct_normal_irradiance"
    )
    
    print("Wysyłanie zapytania do API Open-Meteo...")
    
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
            # Wyciągamy surowe bajty z atrybutu .value
            print(f"DPT 9.001 (Temp 1/0/6)    -> Surowe bajty HEX: {[hex(b) for b in dpt_temp_payload.value]}")
            print(f"DPT 5.001 (Cloud 0/0/19)  -> Surowe bajty HEX: {[hex(b) for b in dpt_cloud_payload.value]}")
            print(f"DPT 9.022 (Irradiance)    -> Surowe bajty HEX: {[hex(b) for b in dpt_irradiance_payload.value]}")
            
            print("\n=================== 3. WERYFIKACJA ODKODOWANIA ===================")
            print(f"Odkodowane DPT 9.001     : {DPTTemperature.from_knx(dpt_temp_payload)} °C")
            print(f"Odkodowane DPT 5.001     : {DPTScaling.from_knx(dpt_cloud_payload)} %")
            print(f"Odkodowane DPT 9.022     : {DPT2ByteFloat.from_knx(dpt_irradiance_payload)} W/m²")
            
        else:
            print(f"Błąd HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"Błąd: {e}")

if __name__ == "__main__":
    try:
        while True:
            przetestuj_pobieranie_i_konwersje_dpt()
            print(f"\n[TIMER] Odczekanie {INTERVAL_SECONDS} sekund do kolejnego wykonania...")
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nProgram został zatrzymany ręcznie.")