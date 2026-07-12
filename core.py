"""
Aggregates buoy, marine forecast, and tide data into per-spot surf reports.

This is the shared logic used both by the standalone CLI (cli.py) and the
MCP server (mcp_server.py) - keeping the fetch/parse code in one place so
both entry points stay in sync.
"""

import json
import os
import time

from buoys import fetch_buoy_latest
from marine import fetch_marine_forecast, fetch_daily_summary
from tides import fetch_today_tides, fetch_tides_range

SPOTS_PATH = os.path.join(os.path.dirname(__file__), "spots.json")

_CACHE = {}
_CACHE_TTL_SECONDS = 600  # 10 minutes - avoid hammering the APIs on repeat calls


def _load_config() -> dict:
    with open(SPOTS_PATH) as f:
        return json.load(f)


def _cached(key: str, fn):
    now = time.time()
    hit = _CACHE.get(key)
    if hit and (now - hit[0]) < _CACHE_TTL_SECONDS:
        return hit[1]
    value = fn()
    _CACHE[key] = (now, value)
    return value


def list_spots() -> list:
    """Return the configured list of South Bay surf spots (Playa del Rey -> Hermosa Beach)."""
    return _load_config()["spots"]


def get_buoy_snapshot(station_id: str) -> dict:
    """Return the latest raw reading from a specific NDBC buoy station."""
    return _cached(f"buoy:{station_id}", lambda: fetch_buoy_latest(station_id))


def get_tide_today() -> list:
    """Return today's high/low tide events for the configured reference tide station."""
    config = _load_config()
    station = config["tide_station"]["id"]
    return _cached(f"tide:{station}", lambda: fetch_today_tides(station))


def _find_spot(config: dict, spot_id: str) -> dict:
    spot = next((s for s in config["spots"] if s["id"] == spot_id), None)
    if not spot:
        valid_ids = ", ".join(s["id"] for s in config["spots"])
        raise ValueError(f"Unknown spot id '{spot_id}'. Valid ids: {valid_ids}")
    return spot


def get_spot_conditions(spot_id: str) -> dict:
    """Return a merged conditions report (forecast + buoy + tides) for one surf spot."""
    config = _load_config()
    spot = _find_spot(config, spot_id)

    marine = _cached(f"marine:{spot_id}", lambda: fetch_marine_forecast(spot["lat"], spot["lon"]))
    buoy = get_buoy_snapshot(spot["primary_buoy"])
    tides = get_tide_today()

    return {
        "spot": spot["name"],
        "spot_id": spot["id"],
        "coordinates": {"lat": spot["lat"], "lon": spot["lon"]},
        "forecast": marine["current"],
        "forecast_units": marine["units"],
        "nearby_buoy": buoy,
        "tide_today": tides,
    }


def get_all_conditions() -> list:
    """Return conditions reports for every configured spot, Playa del Rey through Hermosa Beach."""
    config = _load_config()
    return [get_spot_conditions(s["id"]) for s in config["spots"]]


def get_forecast_by_date(spot_id: str, days: int = 5) -> dict:
    """Return a date-by-date forecast (wave/swell + tide events per day) for one spot."""
    config = _load_config()
    spot = _find_spot(config, spot_id)

    daily_marine = _cached(
        f"daily_marine:{spot_id}:{days}",
        lambda: fetch_daily_summary(spot["lat"], spot["lon"], days=days),
    )

    tide_station = config["tide_station"]["id"]
    tide_range = _cached(
        f"tide_range:{tide_station}:{days}",
        lambda: fetch_tides_range(tide_station, days=days),
    )

    tides_by_date = {}
    for t in tide_range:
        tides_by_date.setdefault(t["date"], []).append(
            {"time": t["time"], "height_ft": t["height_ft"], "type": t["type"]}
        )

    for day in daily_marine:
        day["tides"] = tides_by_date.get(day["date"], [])

    return {
        "spot": spot["name"],
        "spot_id": spot["id"],
        "coordinates": {"lat": spot["lat"], "lon": spot["lon"]},
        "days": daily_marine,
    }
