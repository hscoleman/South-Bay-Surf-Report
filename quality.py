"""
Turns raw wind/swell numbers into surfer-relevant labels: wind quality
(offshore/cross-shore/onshore), swell type (groundswell vs wind swell),
and an overall day-quality score.

These are transparent, documented heuristics based on standard surf
forecasting rules of thumb - not a proprietary model, and not a substitute
for checking a live cam. Treat the score as a rough at-a-glance guide.
"""


def _angle_diff(a: float, b: float) -> float:
    """Smallest angular difference between two compass bearings, 0-180."""
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


def classify_wind(wind_dir_deg, shore_facing_deg):
    """Classify wind direction relative to a beach's shore-facing bearing.

    shore_facing_deg is the compass direction you're looking when standing
    on the sand facing the ocean (roughly the direction swell approaches
    from). Offshore wind blows from land to sea - the opposite bearing -
    and holds wave faces up clean. Onshore wind blows the same direction
    as incoming swell and creates chop.

    Returns "Offshore", "Cross-shore", "Onshore", or None if either input
    is missing.
    """
    if wind_dir_deg is None or shore_facing_deg is None:
        return None

    offshore_deg = (shore_facing_deg + 180) % 360

    if _angle_diff(wind_dir_deg, offshore_deg) <= 55:
        return "Offshore"
    if _angle_diff(wind_dir_deg, shore_facing_deg) <= 55:
        return "Onshore"
    return "Cross-shore"


def classify_swell_period(period_s):
    """Bucket swell period into groundswell / mixed / wind swell.

    Longer period means the swell traveled farther and carries more energy
    per wave - more organized, powerful surf. Shorter period usually means
    locally wind-generated chop.
    """
    if period_s is None:
        return None
    if period_s >= 12:
        return "Groundswell"
    if period_s >= 9:
        return "Mixed swell"
    return "Wind swell"


def swell_direction_score(swell_dir_deg, optimal_swell_deg, max_points=15):
    """Points for how close today's actual swell direction is to a specific
    spot's known sweet-spot window (see spot_guides.py optimal_swell_deg).

    This is what makes the scoring spot-aware rather than one-size-fits-all:
    the same swell can be dead-on for one break and largely shadowed at
    another a few hundred meters away (e.g. El Porto wants NW/WNW and is
    shadowed from SW by the Palos Verdes Peninsula, while Manhattan Beach
    Pier a mile south wants that same SW swell most).
    """
    if swell_dir_deg is None or optimal_swell_deg is None:
        return 0
    diff = _angle_diff(swell_dir_deg, optimal_swell_deg)
    if diff <= 20:
        return max_points
    if diff <= 45:
        return round(max_points * 0.6)
    if diff <= 90:
        return round(max_points * 0.2)
    return 0


def tide_match_score(tide_bucket, tide_trend, best_tide_range, best_tide_trend, max_points=10):
    """Points for how well the current tide matches a spot's known
    preference (see spot_guides.py best_tide_range / best_tide_trend).
    """
    if not tide_bucket or not best_tide_range:
        return 0

    order = ["low", "mid", "high"]
    if tide_bucket in best_tide_range:
        points = max_points * 0.7
    else:
        gap = min(abs(order.index(tide_bucket) - order.index(b)) for b in best_tide_range)
        points = max_points * 0.3 if gap == 1 else 0

    if best_tide_trend and tide_trend and best_tide_trend == tide_trend:
        points += max_points * 0.3

    return round(min(points, max_points))


def compute_quality(
    swell_height_m,
    swell_period_s,
    wind_quality,
    wind_speed_kt,
    swell_dir_score=0,
    tide_score=0,
):
    """Rough 0-100 day-quality score for one specific spot.

    Weighting: swell period (organization) 25 pts, swell size (rideable
    range) 20 pts, wind direction 20 pts, wind speed 10 pts, how well
    today's swell direction matches this spot's sweet spot 15 pts, how
    well the current tide matches this spot's preference 10 pts.

    swell_dir_score and tide_score are pre-computed via
    swell_direction_score() / tide_match_score() and passed in, so this
    function only has to combine them - keeps each factor independently
    testable.

    Returns a score, a Poor/Fair/Good/Great rating, and a 1-5 star count.
    """
    score = 0

    if swell_period_s is not None:
        if swell_period_s >= 14:
            score += 25
        elif swell_period_s >= 12:
            score += 20
        elif swell_period_s >= 9:
            score += 11
        else:
            score += 4

    if swell_height_m is not None:
        ft = swell_height_m * 3.28084
        if 1.5 <= ft <= 6:
            score += 20
        elif 0.8 <= ft < 1.5 or 6 < ft <= 9:
            score += 12
        elif ft > 9:
            score += 6  # big enough to be inconsistent/closed-out for most surfers
        else:
            score += 4  # near flat

    if wind_quality == "Offshore":
        score += 20
    elif wind_quality == "Cross-shore":
        score += 10
    elif wind_quality == "Onshore":
        score += 2

    if wind_speed_kt is not None:
        if wind_speed_kt <= 6:
            score += 10  # light wind forgives an imperfect direction
        elif wind_speed_kt <= 12:
            score += 5

    score += swell_dir_score
    score += tide_score

    score = max(0, min(100, score))

    if score >= 75:
        rating = "Great"
    elif score >= 55:
        rating = "Good"
    elif score >= 35:
        rating = "Fair"
    else:
        rating = "Poor"

    stars = max(1, min(5, round(score / 20)))

    return {"score": score, "rating": rating, "stars": stars}
