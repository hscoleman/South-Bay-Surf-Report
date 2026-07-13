"""
Fetches today's high/low tide predictions from NOAA CO-OPS.

Data source: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
Free, no API key required, official NOAA source. Default station 9410840
(Santa Monica, CA) is the standard reference station for Santa Monica Bay /
South Bay tides.
"""

from datetime import date, timedelta

import requests

COOPS_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def fetch_today_tides(station: str = "9410840") -> list:
    """Return today's high/low tide events for a NOAA CO-OPS station.

    Args:
        station: NOAA CO-OPS station id. Default is Santa Monica, CA (9410840).
    """
    params = {
        "station": station,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "format": "json",
        "interval": "hilo",
        "date": "today",
    }
    resp = requests.get(COOPS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise ValueError(f"NOAA CO-OPS error: {data['error']}")

    predictions = data.get("predictions", [])
    return [
        {
            "time": p["t"],
            "height_ft": float(p["v"]),
            "type": "High" if p["type"] == "H" else "Low",
        }
        for p in predictions
    ]


def fetch_tides_range(station: str = "9410840", days: int = 5) -> list:
    """Return high/low tide events for a date range starting today.

    Args:
        station: NOAA CO-OPS station id. Default is Santa Monica, CA (9410840).
        days: number of days ahead to include (today counts as day 1).
    """
    begin = date.today().strftime("%Y%m%d")
    end = (date.today() + timedelta(days=days - 1)).strftime("%Y%m%d")

    params = {
        "station": station,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "format": "json",
        "interval": "hilo",
        "begin_date": begin,
        "end_date": end,
    }
    resp = requests.get(COOPS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise ValueError(f"NOAA CO-OPS error: {data['error']}")

    predictions = data.get("predictions", [])
    return [
        {
            "time": p["t"],
            "date": p["t"].split(" ")[0],
            "height_ft": float(p["v"]),
            "type": "High" if p["type"] == "H" else "Low",
        }
        for p in predictions
    ]


def fetch_tide_curve(station: str = "9410840", days: int = 5) -> list:
    """Return a continuous hourly tide-height curve for a date range.

    Unlike fetch_tides_range (high/low events only), this pulls an hourly
    prediction so the frontend can draw an actual tide curve/sparkline
    instead of just listing high/low times.
    """
    begin = date.today().strftime("%Y%m%d")
    end = (date.today() + timedelta(days=days - 1)).strftime("%Y%m%d")

    params = {
        "station": station,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "format": "json",
        "interval": "h",
        "begin_date": begin,
        "end_date": end,
    }
    resp = requests.get(COOPS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise ValueError(f"NOAA CO-OPS error: {data['error']}")

    predictions = data.get("predictions", [])
    return [
        {
            "time": p["t"],
            "date": p["t"].split(" ")[0],
            "height_ft": float(p["v"]),
        }
        for p in predictions
    ]


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_today_tides(), indent=2))
