"""
Fetches per-spot swell/wave forecasts from the Open-Meteo Marine Weather API.

Data source: https://marine-api.open-meteo.com/v1/marine
Free, no API key required. Queried by exact lat/lon, so each surf spot gets its
own forecast rather than one blanket regional number. Model updates roughly
every 6 hours; resolution is regional-ocean scale, not down-to-the-sandbar,
but it's the best free source that will actually take a coordinate.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import requests

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
# Actual surface wind (speed/direction) isn't part of the marine API - it comes
# from Open-Meteo's regular weather forecast API instead.
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

LOCAL_TZ = "America/Los_Angeles"

HOURLY_VARS = [
    "wave_height", "wave_direction", "wave_period",
    "swell_wave_height", "swell_wave_direction", "swell_wave_period",
    "wind_wave_height", "wind_wave_direction", "wind_wave_period",
]


def _nearest_hour_index(times: list) -> int:
    """Index of the hourly-array entry closest to right now (local time).

    IMPORTANT: Open-Meteo's hourly arrays always start at 00:00 local time
    of the current day, not at the current hour - so index 0 is midnight,
    not "now". Using idx=0 as a stand-in for "current conditions" silently
    returns midnight's numbers, which can look nothing like what's actually
    happening outside (e.g. calm early-morning wind vs a real afternoon
    sea breeze). This finds the entry that's actually closest to now.
    """
    if not times:
        return 0
    now = datetime.now(ZoneInfo(LOCAL_TZ)).replace(tzinfo=None)
    best_idx, best_diff = 0, None
    for i, t in enumerate(times):
        try:
            dt = datetime.fromisoformat(t)
        except ValueError:
            continue
        diff = abs((dt - now).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff, best_idx = diff, i
    return best_idx


def fetch_marine_forecast(lat: float, lon: float, forecast_days: int = 3) -> dict:
    """Return the current-hour reading plus the full hourly series for a coordinate.

    Args:
        lat, lon: coordinates of the surf spot.
        forecast_days: how many days ahead to pull (Open-Meteo supports up to 16).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "America/Los_Angeles",
        "forecast_days": forecast_days,
    }
    resp = requests.get(MARINE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("No hourly marine data returned for this coordinate")

    # The hourly array starts at midnight local time, not "now" - find the
    # entry actually closest to the current hour for the "current" snapshot.
    idx = _nearest_hour_index(times)
    current = {"time": times[idx]}
    for var in HOURLY_VARS:
        series = hourly.get(var, [])
        current[var] = series[idx] if idx < len(series) else None

    return {
        "current": current,
        "hourly_series": hourly,
        "units": data.get("hourly_units", {}),
    }


def fetch_daily_summary(lat: float, lon: float, days: int = 5) -> list:
    """Group the hourly Open-Meteo series into one summary row per calendar date.

    Each row has the day's wave height range plus a single representative
    swell height/direction/period reading (closest to local noon - direction
    is a compass bearing, so averaging it across the day would be meaningless).
    """
    data = fetch_marine_forecast(lat, lon, forecast_days=days)
    hourly = data["hourly_series"]
    times = hourly.get("time", [])

    day_indexes = {}
    for i, t in enumerate(times):
        date_str = t.split("T")[0]
        day_indexes.setdefault(date_str, []).append(i)

    def _values(var, idxs):
        series = hourly.get(var, [])
        return [series[i] for i in idxs if i < len(series) and series[i] is not None]

    summary = []
    for date_str, idxs in day_indexes.items():
        wave_heights = _values("wave_height", idxs)

        # pick the reading nearest local noon to represent direction/period for the day
        noon_idx = next((i for i in idxs if times[i].endswith("T12:00")), None)
        if noon_idx is None and idxs:
            noon_idx = idxs[len(idxs) // 2]

        def _at_noon(var):
            series = hourly.get(var, [])
            if noon_idx is None or noon_idx >= len(series):
                return None
            return series[noon_idx]

        summary.append({
            "date": date_str,
            "wave_height_min_m": min(wave_heights) if wave_heights else None,
            "wave_height_max_m": max(wave_heights) if wave_heights else None,
            "swell_height_m": _at_noon("swell_wave_height"),
            "swell_direction_deg": _at_noon("swell_wave_direction"),
            "swell_period_s": _at_noon("swell_wave_period"),
            "wind_wave_height_m": _at_noon("wind_wave_height"),
        })

    return summary


def fetch_wind_forecast(lat: float, lon: float, days: int = 5) -> dict:
    """Return a per-date wind summary (speed, direction, gust) for a coordinate.

    Wind isn't part of the marine API - it's a separate weather model, so this
    hits Open-Meteo's regular forecast endpoint. Returns a dict keyed by date
    string so it's easy to merge into the marine daily summary.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "daily": "sunrise,sunset",
        "wind_speed_unit": "kn",
        "timezone": "America/Los_Angeles",
        "forecast_days": days,
    }
    resp = requests.get(WEATHER_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("No hourly wind data returned for this coordinate")

    daily = data.get("daily", {})
    daily_times = daily.get("time", [])
    sunrise_series = daily.get("sunrise", [])
    sunset_series = daily.get("sunset", [])
    sun_by_date = {
        d: {
            "sunrise": sunrise_series[i] if i < len(sunrise_series) else None,
            "sunset": sunset_series[i] if i < len(sunset_series) else None,
        }
        for i, d in enumerate(daily_times)
    }

    day_indexes = {}
    for i, t in enumerate(times):
        date_str = t.split("T")[0]
        day_indexes.setdefault(date_str, []).append(i)

    summary = {}
    for date_str, idxs in day_indexes.items():
        # same noon-snapshot approach as fetch_daily_summary - wind direction
        # is a bearing, so a same-day average would be meaningless
        noon_idx = next((i for i in idxs if times[i].endswith("T12:00")), None)
        if noon_idx is None and idxs:
            noon_idx = idxs[len(idxs) // 2]

        def _at_noon(var):
            series = hourly.get(var, [])
            if noon_idx is None or noon_idx >= len(series):
                return None
            return series[noon_idx]

        sun = sun_by_date.get(date_str, {})
        summary[date_str] = {
            "wind_speed_kt": _at_noon("wind_speed_10m"),
            "wind_direction_deg": _at_noon("wind_direction_10m"),
            "wind_gust_kt": _at_noon("wind_gusts_10m"),
            "sunrise": sun.get("sunrise"),
            "sunset": sun.get("sunset"),
        }

    return summary


def fetch_current_wind(lat: float, lon: float) -> dict:
    """Return right-now wind speed/direction/gust for a coordinate.

    Mirrors fetch_marine_forecast's "current" snapshot pattern - used for
    the quick spot-card view rather than the 5-day table.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "wind_speed_unit": "kn",
        "timezone": "America/Los_Angeles",
        "forecast_days": 1,
    }
    resp = requests.get(WEATHER_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("No hourly wind data returned for this coordinate")

    idx = _nearest_hour_index(times)
    return {
        "time": times[idx],
        "wind_speed_kt": hourly.get("wind_speed_10m", [None])[idx],
        "wind_direction_deg": hourly.get("wind_direction_10m", [None])[idx],
        "wind_gust_kt": hourly.get("wind_gusts_10m", [None])[idx],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_marine_forecast(33.8847, -118.4109, forecast_days=1), indent=2))
