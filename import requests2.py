import requests

def pobierz_dane_pogodowe():
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude=51.75&longitude=19.46&"
        f"current=temperature_2m,relative_humidity_2m,cloud_cover,direct_normal_irradiance,wind_speed_10m&"
        f"wind_speed_unit=ms"
    )
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Wszystkie aktualne dane znajdują się bezpośrednio w kluczu 'current'
            current = data["current"]
            
            t_out = current["temperature_2m"]              # REAL, °C
            humidity = current["relative_humidity_2m"]     # REAL, %
            cloud_cover = current["cloud_cover"]           # REAL, %
            irradiance = current["direct_normal_irradiance"]# REAL, W/m²
            wind_speed = current["wind_speed_10m"]          # REAL, m/s
            data_pomiaru = current["time"] 
            
            print("--- POBRANE DANE BIEŻĄCE Z OPEN-METEO ---")
            print(f"Temperatura (T_out)    : {t_out} °C")
            print(f"Wilgotność              : {humidity} %")
            print(f"Zachmurzenie            : {cloud_cover} %")
            print(f"Irradiancja             : {irradiance} W/m²")
            print(f"Prędkość wiatru         : {wind_speed} m/s")
           

            print(f"Data i godzina próbki z API: {data_pomiaru}")
            print(f"Temperatura: {current['temperature_2m']} °C")
            
            return {
                "t_out": t_out,
                "humidity": humidity,
                "cloud_cover": cloud_cover,
                "irradiance": irradiance,
                "wind_speed": wind_speed
            }
        else:
            print(f"Błąd HTTP: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Błąd połączenia z API: {e}")
        return None

if __name__ == "__main__":
    pobierz_dane_pogodowe()