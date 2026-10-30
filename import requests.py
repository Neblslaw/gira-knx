import requests

LATITUDE = 51.75
LONGITUDE = 19.46

def przetestuj_pobieranie_pogody():
    # Dodaliśmy direct_normal_irradiance oraz global_tilted_irradiance do parametru hourly
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"current_weather=true&"
        f"hourly=cloudcover,direct_normal_irradiance,shortwave_radiation"
    )
    
    print("Wysyłanie zapytania do Open-Meteo...")
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            t_out = data["current_weather"]["temperature"]
            wind_speed = data["current_weather"]["windspeed"]
            cloud_cover = data["hourly"]["cloudcover"][0]
            
            # Pobranie irradiancji z bieżącej godziny (W/m²)
            direct_irradiance = data["hourly"]["direct_normal_irradiance"][0]
            global_irradiance = data["hourly"]["shortwave_radiation"][0]
            
            print("\nSUKCES! Pobrane dane:")
            print(f"- Temperatura zewnętrzna (T_out): {t_out} °C")
            print(f"- Prędkość wiatru: {wind_speed} km/h")
            print(f"- Zachmurzenie: {cloud_cover} %")
            print(f"- Promieniowanie bezpośrednie: {direct_irradiance} W/m²")
            print(f"- Promieniowanie całkowite: {global_irradiance} W/m²")
        else:
            print(f"Błąd HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"Błąd połączenia: {e}")

if __name__ == "__main__":
    przetestuj_pobieranie_pogody()