import asyncio
import time

import requests
from xknx import XKNX
from xknx.io import ConnectionConfig, ConnectionType
from xknx.telegram import Telegram
from xknx.telegram.address import GroupAddress
from xknx.dpt import (
    DPTTemperature,
    DPTHumidity,
    DPTScaling,
    DPTWspKmh,
    DPTPowerDensity,
)
from xknx.telegram.apci import GroupValueWrite

# ==============================================================================
# KONFIGURACJA API POGODOWEGO
# ==============================================================================
LATITUDE = 52.52
LONGITUDE = 13.41

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "is_day",
    "rain",
    "relative_humidity_2m",
    "cloud_cover",
    "wind_speed_10m",
    "direct_normal_irradiance",
]

# ==============================================================================
# KONFIGURACJA KNX (biblioteka xknx)
# ==============================================================================
IP_ROUTER_IP = "192.168.100.211"
IP_ROUTER_PORT = 3671


# ==============================================================================
#  MAPOWANIE PÓL API -> ADRES GRUPOWY + DPT
# ==============================================================================
DPT_MAP = {
    "temperature_2m": {
        "ga": "1/2/0",
        "dpt": "9.001",
        "klasa": DPTTemperature,
    },
    "relative_humidity_2m": {
        "ga": "1/2/1",
        "dpt": "9.007",
        "klasa": DPTHumidity,
    },
    "cloud_cover": {
        "ga": "1/2/2",
        "dpt": "9.007",
        "klasa": DPTHumidity,
    },
    "direct_normal_irradiance": {
        "ga": "1/2/3",
        "dpt": "9.022",
        "klasa": DPTPowerDensity,
    },
    "wind_speed_10m": {
        "ga": "1/2/4",
        "dpt": "9.005",
        "klasa": DPTWspKmh,
    },
}


# ==============================================================================
# POBIERANIE DANYCH (tylko current weather)
# ==============================================================================
def pobierz_dane_pogodowe():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ",".join(CURRENT_FIELDS),
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
        current = response.json()["current"]

        print(f"\n[API] Pobrano dane dla {current.get('time', 'brak czasu')}:")
        for field in CURRENT_FIELDS:
            print(f"  {field:26} = {current.get(field)}")
        return current

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"[BŁĄD API] Nie udało się pobrać danych: {e}")
        return None


# ==============================================================================
# KONWERSJA NA DPT (można zakomentować w main, jeśli używamy tylko HTTP API)
# ==============================================================================
def przetworz_na_dpt(dane):
    przetworzone = []

    for field, cfg in DPT_MAP.items():
        if field not in dane or dane[field] is None:
            print(f"  {field:26} -> pominięto (brak wartości w API)")
            continue

        wartosc = dane[field]
        if field == "is_day":
            wartosc = bool(wartosc)

        payload = cfg["klasa"].to_knx(wartosc)
        odkodowane = cfg["klasa"].from_knx(payload)

        if isinstance(payload.value, tuple):
            hex_bytes = " ".join(f"0x{b:02X}" for b in payload.value)
        else:
            hex_bytes = str(payload.value)

        print(
            f"  {field:26} {cfg['dpt']:>5} GA {cfg['ga']:>5} "
            f"-> {hex_bytes} (odkodowane: {odkodowane})"
        )

        przetworzone.append(
            {
                "field": field,
                "ga": cfg["ga"],
                "dpt": cfg["dpt"],
                "payload": payload,
            }
        )

    return przetworzone


# ==============================================================================
# WYSYŁKA - OPCJA 1: biblioteka xknx (bezpośrednio do IP-Routera)
# ==============================================================================
async def wyslij_przez_xknx(przetworzone):
    knx = XKNX(
        connection_config=ConnectionConfig(
            connection_type=ConnectionType.TUNNELING,
            gateway_ip=IP_ROUTER_IP,
            gateway_port=IP_ROUTER_PORT,
        )
    )

    await knx.start()
    print(f"\n[KNX] Połączono z IP-Routerem {IP_ROUTER_IP}:{IP_ROUTER_PORT}")

    try:
        for item in przetworzone:
            telegram = Telegram(
                destination_address=GroupAddress(item["ga"]),
                payload=GroupValueWrite(item["payload"]),
            )
            await knx.telegrams.put(telegram)
            print(f"[KNX] Wysłano {item['field']} ({item['dpt']}) na {item['ga']}")

        await knx.telegrams.join()
    finally:
        await knx.stop()
        print("[KNX] Rozłączono z magistralą.")

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    while True:
        dane = pobierz_dane_pogodowe()
        if dane is None:
            return

        print("\n[DPT] Konwersja na formaty KNX:")
        przetworzone = przetworz_na_dpt(dane)

        print("\n[WYSYŁKA]")

        asyncio.run(wyslij_przez_xknx(przetworzone))

        time.sleep(5*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram został zatrzymany ręcznie.")



