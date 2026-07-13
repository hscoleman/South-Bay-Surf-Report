"""
Fetches today's high/low tide predictions from NOAA CO-OPS.

Data source: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
Free, no API key required, official NOAA source. Default station 9410840
(Santa Monica, CA) is the standard reference station for Santa Monica Bay /
South Bay tides.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

COOPS_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
LOCAL_TZ = "America/Los_Angeles"


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


def classify_tide_state(curve: list, reference_dt: datetime = None) -> dict:
    """Classify a point in a day's tide curve as low/mid/high and rising/
    falling, relative to that day's own min/max range (not some fixed
    absolute height - "high tide" at Santa Monica isn't the same number
    every day).

    Args:
        curve: list of {"time": "YYYY-MM-DD HH:MM", "height_ft": float} -
            a single day's hourly predictions (see fetch_tide_curve).
        reference_dt: the point in time to classify. Defaults to right now
            (Pacific time) - pass a specific datetime (e.g. a day's noon)
            when classifying a future forecast day instead of "today".
    """
    if not curve or len(curve) < 2:
        return {"height_ft": None, "bucket": None, "trend": None}

    if reference_dt is None:
        reference_dt = datetime.now(ZoneInfo(LOCAL_TZ)).replace(tzinfo=None)

    parsed = []
    for pt in curve:
        try:
            dt = datetime.fromisoformat(pt["time"].replace(" ", "T"))
        except (ValueError, KeyError):
            continue
        parsed.append((dt, pt["height_ft"]))

    if len(parsed) < 2:
        return {"height_ft": None, "bucket": None, "trend": None}

    parsed.sort(key=lambda p: p[0])
    idx = min(range(len(parsed)), key=lambda i: abs((parsed[i][0] - reference_dt).total_seconds()))

    heights = [h for _, h in parsed]
    day_min, day_max = min(heights), max(heights)
    current_height = parsed[idx][1]

    span = (day_max - day_min) or 1.0
    pct = (current_height - day_min) / span
    if pct < 0.34:
        bucket = "low"
    elif pct < 0.67:
        bucket = "mid"
    else:
        bucket = "high"

    if idx < len(parsed) - 1:
        trend = "rising" if parsed[idx + 1][1] > current_height else "falling"
    elif idx > 0:
        trend = "rising" if current_height > parsed[idx - 1][1] else "falling"
    else:
        trend = None

    return {"height_ft": round(current_height, 2), "bucket": bucket, "trend": trend}


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_today_tides(), indent=2))
