"""
Flask web app - a Surfline-style dashboard for the South Bay LA surf spots.

Serves a small JSON API on top of core.py, plus the frontend in
templates/index.html + static/.

Run with:
    python app.py
Then open http://127.0.0.1:5050 in a browser.

Works on plain Python 3.9+ (Flask has no 3.10+ requirement, unlike the mcp
package used for mcp_server.py).
"""

from flask import Flask, jsonify, render_template, request

import core
from spot_guides import get_spot_guide
from quality import SKILL_LEVELS

app = Flask(__name__)


def _skill_param():
    """Read ?skill= from the query string, falling back to intermediate
    for anything missing or not one of the recognized levels."""
    skill = request.args.get("skill", default="intermediate")
    return skill if skill in SKILL_LEVELS else "intermediate"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/spots")
def api_spots():
    return jsonify(core.list_spots())


@app.route("/api/conditions")
def api_conditions():
    """Current snapshot (wave/swell/tide) for all 7 spots - powers the main grid."""
    try:
        return jsonify(core.get_all_conditions(skill_level=_skill_param()))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/conditions/<spot_id>")
def api_spot_conditions(spot_id):
    try:
        return jsonify(core.get_spot_conditions(spot_id, skill_level=_skill_param()))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/forecast/<spot_id>")
def api_forecast(spot_id):
    """Date-by-date forecast (wave height range, swell, tide events) - powers the detail view."""
    days = request.args.get("days", default=5, type=int)
    try:
        return jsonify(core.get_forecast_by_date(spot_id, days=days, skill_level=_skill_param()))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/guide/<spot_id>")
def api_guide(spot_id):
    """Static 'what makes this spot work' reference guide - not live data,
    see spot_guides.py for sourcing notes."""
    spot = next((s for s in core.list_spots() if s["id"] == spot_id), None)
    if not spot:
        return jsonify({"error": f"Unknown spot id '{spot_id}'"}), 404

    guide = get_spot_guide(spot_id)
    if not guide:
        return jsonify({"error": f"No guide written yet for '{spot_id}'"}), 404

    return jsonify({"spot": spot["name"], "spot_id": spot_id, **guide})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
