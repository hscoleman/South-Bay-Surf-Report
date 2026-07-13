"""
Static "what makes this spot work" reference guide for each South Bay break.

Unlike the rest of this app, this content isn't pulled live from an API -
there's no free, open data source for "which swell angle is best at this
specific sandbar." It's compiled from public surf spot guides (Surfline
spot guides, Surf-Forecast.com, and other publicly written surf reports)
current as of mid-2026. Sandbars shift over time, so treat this as general
orientation, not gospel - always cross-check the live forecast above it.
"""

SPOT_GUIDES = {
    "playa_del_rey": {
        "optimal_swell": "SW groundswell, roughly 205-225°",
        "optimal_swell_deg": 215,
        "optimal_wind": "Offshore, NE around 45°",
        "optimal_wind_deg": 45,
        "best_tide": "Mid tide, falling",
        "best_season": "Winter - most consistent in December",
        "blurb": (
            "Toes Beach sits at the very north end of Playa del Rey, right where "
            "the Ballona Creek jetty meets the ocean. The jetty holds a sandbar in "
            "place that turns a southwest groundswell into a fairly consistent "
            "righthand wave. It's an exposed break, so it picks up more swell than "
            "spots tucked further into the bay - but also more current near the "
            "creek mouth."
        ),
    },
    "dockweiler": {
        "optimal_swell": "SW to SSW groundswell, roughly 205-225°",
        "optimal_swell_deg": 215,
        "optimal_wind": "Offshore NE around 45°; tolerates cross-shore",
        "optimal_wind_deg": 45,
        "best_tide": "Low tide",
        "best_season": "Fairly consistent year-round",
        "blurb": (
            "Dockweiler is a long, open A-frame beach break running from Ballona "
            "Creek down toward El Segundo, so it throws both lefts and rights "
            "depending on where the sandbars happen to be that season. It usually "
            "runs a notch smaller than El Porto a couple miles south - typically "
            "waist to chest high - with the north end occasionally pulling in "
            "extra size on bigger swells."
        ),
    },
    "el_segundo": {
        "optimal_swell": "SW groundswell, roughly 225°",
        "optimal_swell_deg": 225,
        "optimal_wind": "Offshore NE around 45°",
        "optimal_wind_deg": 45,
        "best_tide": "Low to negative tide for the best shape",
        "best_season": "Winter - most consistent in December",
        "blurb": (
            "This one breaks left off the jetty next to the El Segundo Energy "
            "Center (the peak just north of the jetty is locally called "
            "'Hammerland'). Paddle out about five feet off the end of the rocks - "
            "on very low or negative tides it can barrel for several yards past "
            "the jetty. It's usually one of the least crowded named breaks in the "
            "South Bay."
        ),
    },
    "el_porto": {
        "optimal_swell": "NW/WNW, roughly 292-315° (primary); also handles SW-W combo swells, 225-292°",
        "optimal_swell_deg": 300,
        "optimal_wind": "Offshore E-SE, roughly 90-135°",
        "optimal_wind_deg": 110,
        "best_tide": "Mid tide",
        "best_season": "Fall through spring (Oct-Apr); can hold 5-10ft",
        "blurb": (
            "El Porto is the South Bay's northwest-swell magnet - it's almost "
            "always the biggest spot in the region during winter NW swells, "
            "because south and southwest swells get largely blocked by the "
            "Palos Verdes Peninsula and the Channel Islands. It's entirely "
            "sandbar-dependent: when the banks line up with the swell angle and "
            "period it can get genuinely excellent (and crowded), but a "
            "mismatched swell produces some of the heaviest closeouts in the area."
        ),
    },
    "manhattan_beach_pier": {
        "optimal_swell": "SW groundswell, roughly 225° (most consistent); NW-WNW, 292-315°, brings the biggest winter surf",
        "optimal_swell_deg": 225,
        "optimal_wind": "Offshore E around 90°",
        "optimal_wind_deg": 90,
        "best_tide": "Low to mid tide",
        "best_season": "Winter most reliable; summer smaller and more playful",
        "blurb": (
            "A classic peaky Southern California beach break with shifting "
            "sandbars on both sides of the pier, producing both lefts and "
            "rights. Winter NW-WNW swells bring the most reliable size (2-6ft "
            "and up), while summer sees smaller, playful SW swells. Watch for "
            "the pier pilings and rip currents near the pylons - it's usually "
            "crowded."
        ),
    },
    "hermosa_beach_22nd": {
        "optimal_swell": "WNW, roughly 292° (primary); handles SSW-W, 202-270°, too",
        "optimal_swell_deg": 292,
        "optimal_wind": "Offshore E around 90°",
        "optimal_wind_deg": 90,
        "best_tide": "Mid to high tide, rising",
        "best_season": "Winter (Nov-Feb) for size; summer S swells are gentler for beginners",
        "blurb": (
            "A few blocks north of the pier, 22nd Street shares the same broad "
            "WNW-to-SW swell window as the rest of Hermosa Beach but usually "
            "draws a smaller crowd than the pier peak itself. Best on a rising "
            "mid-to-high tide with a light morning offshore wind."
        ),
    },
    "hermosa_beach_pier": {
        "optimal_swell": "WNW, roughly 292° (primary); also handles SW, 225°, in summer",
        "optimal_swell_deg": 292,
        "optimal_wind": "Offshore E around 90°",
        "optimal_wind_deg": 90,
        "best_tide": "Mid tide, rising",
        "best_season": "Winter (Nov-Feb) most reliable; summer better for beginners",
        "blurb": (
            "Peaky beach break on both sides of the pier, similar to Manhattan "
            "Beach Pier a bit further south along the same stretch. Winter WNW "
            "groundswells produce the most consistent, powerful surf (up to "
            "4-6ft), while summer south swells are softer and friendlier for "
            "beginners. It's a popular, often-crowded peak - watch for pilings "
            "and rip currents."
        ),
    },
}


def get_spot_guide(spot_id: str) -> dict:
    """Return the static guide entry for a spot, or None if not found."""
    return SPOT_GUIDES.get(spot_id)
