"""
Fetches and parses live data from NOAA's National Data Buoy Center (NDBC).

Data source: https://www.ndbc.noaa.gov/data/realtime2/{station}.txt
Free, no API key required. Each station publishes a rolling ~45-day text file
of observations, most recent first. We only need the latest row.

Confirmed real column layout for station 46221 (Santa Monica Bay waverider):
#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
"MM" means the sensor doesn't report that field (common for wind on wave-only buoys).
"""

import requests

NDBC_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"

COLUMNS = [
    "YY", "MM", "DD", "hh", "mm",
    "WDIR", "WSPD", "GST", "WVHT", "DPD", "APD", "MWD",
    "PRES", "ATMP", "WTMP", "DEWP", "VIS", "PTDY", "TIDE",
]


def fetch_buoy_latest(station: str) -> dict:
    """Return the most recent reading from an NDBC realtime2 station feed.

    Args:
        station: NDBC station id, e.g. "46221" (Santa Monica Bay) or "46222" (San Pedro).
    """
    url = NDBC_URL.format(station=station)
    resp = requests.get(url, timeout=15, headers={"User-Agent": "southbay-surf/1.0"})
    resp.raise_for_status()

    data_lines = [line for line in resp.text.splitlines() if line and not line.startswith("#")]
    if not data_lines:
        raise ValueError(f"No data rows returned for buoy {station}")

    latest = data_lines[0].split()
    row = dict(zip(COLUMNS, latest))

    def _num(key):
        val = row.get(key)
        if val is None or val == "MM":
            return None
        try:
            return float(val)
        except ValueError:
            return None

    timestamp_utc = f"{row['YY']}-{row['MM']}-{row['DD']} {row['hh']}:{row['mm']} UTC"

    return {
        "station": station,
        "timestamp_utc": timestamp_utc,
        "wave_height_m": _num("WVHT"),
        "dominant_wave_period_s": _num("DPD"),
        "average_wave_period_s": _num("APD"),
        "mean_wave_direction_deg": _num("MWD"),
        "wind_dir_deg": _num("WDIR"),
        "wind_speed_mps": _num("WSPD"),
        "gust_mps": _num("GST"),
        "water_temp_c": _num("WTMP"),
        "air_temp_c": _num("ATMP"),
        "pressure_hpa": _num("PRES"),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_buoy_latest("46221"), indent=2))
