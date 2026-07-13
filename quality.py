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


SKILL_LEVELS = ("beginner", "intermediate", "advanced")


def _score_swell_period(period_s, skill_level, max_points=25):
    """Points for swell period, tuned to what each skill level actually wants.

    Longer period = more powerful, more critical, steeper takeoffs - great
    for an advanced surfer chasing power, genuinely harder for a beginner.
    Beginners are better served by a moderate, organized-but-not-punchy
    period; very short period wind-chop is bad for everyone.
    """
    if period_s is None:
        return 0

    if skill_level == "beginner":
        if 8 <= period_s <= 12:
            return max_points
        if 6 <= period_s < 8 or 12 < period_s <= 15:
            return round(max_points * 0.6)
        if period_s > 15:
            return round(max_points * 0.25)  # powerful groundswell - tougher for a beginner
        return round(max_points * 0.25)

    if skill_level == "advanced":
        if period_s >= 14:
            return max_points
        if period_s >= 12:
            return round(max_points * 0.8)
        if period_s >= 9:
            return round(max_points * 0.4)
        return round(max_points * 0.12)

    # intermediate (default)
    if period_s >= 14:
        return max_points
    if period_s >= 12:
        return round(max_points * 0.8)
    if period_s >= 9:
        return round(max_points * 0.44)
    return round(max_points * 0.16)


def _score_swell_size(swell_height_m, skill_level, max_points=20):
    """Points for swell size, tuned to what each skill level can handle
    and enjoy - a beginner's sweet spot is meaningfully smaller than an
    advanced surfer's."""
    if swell_height_m is None:
        return 0

    ft = swell_height_m * 3.28084

    if skill_level == "beginner":
        if 1.0 <= ft <= 3.0:
            return max_points
        if 0.5 <= ft < 1.0 or 3.0 < ft <= 4.0:
            return round(max_points * 0.6)
        if ft > 4.0:
            return round(max_points * 0.15)  # past the point of being fun/safe for a beginner
        return round(max_points * 0.5)  # near flat - easy, just not much to ride

    if skill_level == "advanced":
        if 3.0 <= ft <= 10.0:
            return max_points
        if 1.5 <= ft < 3.0 or 10.0 < ft <= 14.0:
            return round(max_points * 0.6)
        if ft > 14.0:
            return round(max_points * 0.35)
        return round(max_points * 0.2)  # too small to be interesting

    # intermediate (default)
    if 1.5 <= ft <= 6:
        return max_points
    if 0.8 <= ft < 1.5 or 6 < ft <= 9:
        return round(max_points * 0.6)
    if ft > 9:
        return round(max_points * 0.3)  # big enough to be inconsistent/closed-out for most surfers
    return round(max_points * 0.2)  # near flat


def _score_wind_speed(wind_speed_kt, skill_level, max_points=10):
    """Points for wind speed - beginners need it glassy far more than an
    advanced surfer, who can work with some texture on the water."""
    if wind_speed_kt is None:
        return 0

    if skill_level == "beginner":
        if wind_speed_kt <= 5:
            return max_points
        if wind_speed_kt <= 10:
            return round(max_points * 0.4)
        return 0

    if skill_level == "advanced":
        if wind_speed_kt <= 8:
            return max_points
        if wind_speed_kt <= 15:
            return round(max_points * 0.6)
        return round(max_points * 0.2)

    # intermediate (default)
    if wind_speed_kt <= 6:
        return max_points
    if wind_speed_kt <= 12:
        return round(max_points * 0.5)
    return 0


def compute_quality(
    swell_height_m,
    swell_period_s,
    wind_quality,
    wind_speed_kt,
    swell_dir_score=0,
    tide_score=0,
    skill_level="intermediate",
):
    """Rough 0-100 day-quality score for one specific spot and skill level.

    Weighting: swell period (organization) 25 pts, swell size (rideable
    range) 20 pts, wind direction 20 pts, wind speed 10 pts, how well
    today's swell direction matches this spot's sweet spot 15 pts, how
    well the current tide matches this spot's preference 10 pts.

    skill_level ("beginner"/"intermediate"/"advanced") changes what counts
    as a "good" swell size, period, and wind speed - a beginner's ideal day
    looks meaningfully different from an advanced surfer's. Wind direction,
    swell-direction match, and tide match are left skill-independent: clean
    conditions and a swell reaching a spot's sweet spot matter the same way
    regardless of who's paddling out.

    swell_dir_score and tide_score are pre-computed via
    swell_direction_score() / tide_match_score() and passed in, so this
    function only has to combine them - keeps each factor independently
    testable.

    Returns a score, a Poor/Fair/Good/Great rating, and a 1-5 star count.
    """
    if skill_level not in SKILL_LEVELS:
        skill_level = "intermediate"

    score = 0
    score += _score_swell_period(swell_period_s, skill_level)
    score += _score_swell_size(swell_height_m, skill_level)

    if wind_quality == "Offshore":
        score += 20
    elif wind_quality == "Cross-shore":
        score += 10
    elif wind_quality == "Onshore":
        score += 2

    score += _score_wind_speed(wind_speed_kt, skill_level)

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
