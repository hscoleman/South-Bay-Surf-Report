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

app = Flask(__name__)


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
        return jsonify(core.get_all_conditions())
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/conditions/<spot_id>")
def api_spot_conditions(spot_id):
    try:
        return jsonify(core.get_spot_conditions(spot_id))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/forecast/<spot_id>")
def api_forecast(spot_id):
    """Date-by-date forecast (wave height range, swell, tide events) - powers the detail view."""
    days = request.args.get("days", default=5, type=int)
    try:
        return jsonify(core.get_forecast_by_date(spot_id, days=days))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    app.run(debug=True, port=5050)
