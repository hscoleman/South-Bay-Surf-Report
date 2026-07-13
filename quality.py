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


def compute_quality(swell_height_m, swell_period_s, wind_quality, wind_speed_kt):
    """Rough 0-100 day-quality score from swell size/period + wind.

    Weighting: swell period (organization) 35 pts, swell size (rideable
    range) 25 pts, wind direction 30 pts, wind speed 10 pts. Returns a
    score, a Poor/Fair/Good/Great rating, and a 1-5 star count.
    """
    score = 0

    if swell_period_s is not None:
        if swell_period_s >= 14:
            score += 35
        elif swell_period_s >= 12:
            score += 28
        elif swell_period_s >= 9:
            score += 16
        else:
            score += 6

    if swell_height_m is not None:
        ft = swell_height_m * 3.28084
        if 1.5 <= ft <= 6:
            score += 25
        elif 0.8 <= ft < 1.5 or 6 < ft <= 9:
            score += 15
        elif ft > 9:
            score += 8  # big enough to be inconsistent/closed-out for most surfers
        else:
            score += 5  # near flat

    if wind_quality == "Offshore":
        score += 30
    elif wind_quality == "Cross-shore":
        score += 15
    elif wind_quality == "Onshore":
        score += 3

    if wind_speed_kt is not None:
        if wind_speed_kt <= 6:
            score += 10  # light wind forgives an imperfect direction
        elif wind_speed_kt <= 12:
            score += 5

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
