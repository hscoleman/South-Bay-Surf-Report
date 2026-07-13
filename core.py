"""
Aggregates buoy, marine forecast, and tide data into per-spot surf reports.

This is the shared logic used both by the standalone CLI (cli.py) and the
MCP server (mcp_server.py) - keeping the fetch/parse code in one place so
both entry points stay in sync.
"""

import json
import os
import time
from datetime import datetime

from buoys import fetch_buoy_latest
from marine import (
    fetch_marine_forecast,
    fetch_daily_summary,
    fetch_wind_forecast,
    fetch_current_wind,
)
from tides import fetch_today_tides, fetch_tides_range, fetch_tide_curve, classify_tide_state
from quality import (
    classify_wind,
    classify_swell_period,
    compute_quality,
    swell_direction_score,
    tide_match_score,
)
from spot_guides import get_spot_guide

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


def get_tide_curve_today() -> list:
    """Return today's hourly tide curve for the configured reference tide station.

    One station shared across all spots, so this is cached once regardless
    of how many spots ask for it.
    """
    config = _load_config()
    station = config["tide_station"]["id"]
    return _cached(f"tide_curve_today:{station}", lambda: fetch_tide_curve(station, days=1))


def _find_spot(config: dict, spot_id: str) -> dict:
    spot = next((s for s in config["spots"] if s["id"] == spot_id), None)
    if not spot:
        valid_ids = ", ".join(s["id"] for s in config["spots"])
        raise ValueError(f"Unknown spot id '{spot_id}'. Valid ids: {valid_ids}")
    return spot


def get_spot_conditions(spot_id: str) -> dict:
    """Return a merged conditions report (forecast + buoy + wind + tides + quality) for one spot."""
    config = _load_config()
    spot = _find_spot(config, spot_id)

    marine = _cached(f"marine:{spot_id}", lambda: fetch_marine_forecast(spot["lat"], spot["lon"]))
    buoy = get_buoy_snapshot(spot["primary_buoy"])
    tides = get_tide_today()
    wind = _cached(f"cur_wind:{spot_id}", lambda: fetch_current_wind(spot["lat"], spot["lon"]))

    forecast = marine["current"]
    guide = get_spot_guide(spot["id"]) or {}

    wind_quality = classify_wind(wind.get("wind_direction_deg"), spot.get("shore_facing_deg"))
    swell_type = classify_swell_period(forecast.get("swell_wave_period"))

    tide_curve_today = get_tide_curve_today()
    tide_state = classify_tide_state(tide_curve_today)

    sd_score = swell_direction_score(forecast.get("swell_wave_direction"), guide.get("optimal_swell_deg"))
    t_score = tide_match_score(
        tide_state.get("bucket"),
        tide_state.get("trend"),
        guide.get("best_tide_range"),
        guide.get("best_tide_trend"),
    )

    quality = compute_quality(
        forecast.get("swell_wave_height"),
        forecast.get("swell_wave_period"),
        wind_quality,
        wind.get("wind_speed_kt"),
        swell_dir_score=sd_score,
        tide_score=t_score,
    )

    return {
        "spot": spot["name"],
        "spot_id": spot["id"],
        "coordinates": {"lat": spot["lat"], "lon": spot["lon"]},
        "forecast": forecast,
        "forecast_units": marine["units"],
        "nearby_buoy": buoy,
        "tide_today": tides,
        "tide_state": tide_state,
        "wind": wind,
        "wind_quality": wind_quality,
        "swell_type": swell_type,
        "quality": quality,
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

    wind_by_date = _cached(
        f"wind:{spot_id}:{days}",
        lambda: fetch_wind_forecast(spot["lat"], spot["lon"], days=days),
    )

    tide_curve = _cached(
        f"tide_curve:{tide_station}:{days}",
        lambda: fetch_tide_curve(tide_station, days=days),
    )

    tides_by_date = {}
    for t in tide_range:
        tides_by_date.setdefault(t["date"], []).append(
            {"time": t["time"], "height_ft": t["height_ft"], "type": t["type"]}
        )

    tide_curve_by_date = {}
    for pt in tide_curve:
        tide_curve_by_date.setdefault(pt["date"], []).append(
            {"time": pt["time"], "height_ft": pt["height_ft"]}
        )

    shore_facing_deg = spot.get("shore_facing_deg")
    guide = get_spot_guide(spot["id"]) or {}

    for day in daily_marine:
        wind_today = wind_by_date.get(day["date"], {})
        day_tide_curve = tide_curve_by_date.get(day["date"], [])
        day["tides"] = tides_by_date.get(day["date"], [])
        day["tide_curve"] = day_tide_curve
        day["wind"] = wind_today
        day["sunrise"] = wind_today.get("sunrise")
        day["sunset"] = wind_today.get("sunset")

        # Use that day's noon as the reference point for tide state, same
        # noon-snapshot convention used for swell/wind on future days.
        noon_ref = None
        try:
            noon_ref = datetime.strptime(f"{day['date']} 12:00", "%Y-%m-%d %H:%M")
        except ValueError:
            pass
        tide_state = classify_tide_state(day_tide_curve, reference_dt=noon_ref)
        day["tide_state"] = tide_state

        wind_quality = classify_wind(wind_today.get("wind_direction_deg"), shore_facing_deg)
        day["wind_quality"] = wind_quality
        day["swell_type"] = classify_swell_period(day.get("swell_period_s"))

        sd_score = swell_direction_score(day.get("swell_direction_deg"), guide.get("optimal_swell_deg"))
        t_score = tide_match_score(
            tide_state.get("bucket"),
            tide_state.get("trend"),
            guide.get("best_tide_range"),
            guide.get("best_tide_trend"),
        )

        day["quality"] = compute_quality(
            day.get("swell_height_m"),
            day.get("swell_period_s"),
            wind_quality,
            wind_today.get("wind_speed_kt"),
            swell_dir_score=sd_score,
            tide_score=t_score,
        )

    return {
        "spot": spot["name"],
        "spot_id": spot["id"],
        "coordinates": {"lat": spot["lat"], "lon": spot["lon"]},
        "days": daily_marine,
    }
