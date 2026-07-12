# South Bay LA Surf Conditions

Live swell, buoy, and tide data for South Bay Los Angeles surf spots, from
Playa del Rey down to Hermosa Beach. Works three ways: as a standalone Python
script, as a browser dashboard (Surfline-style), or as an MCP server so Claude
(or any MCP client) can pull live conditions as tools.

## What it covers

7 spots, north to south: Playa del Rey / Toes Beach, Dockweiler State Beach,
El Segundo Beach, El Porto, Manhattan Beach Pier, Hermosa Beach 22nd Street,
Hermosa Beach Pier. Edit `spots.json` to add/remove spots or adjust coordinates.

## Data sources (all free, no API keys)

| Source | What it provides | 
|---|---|
| [NOAA NDBC](https://www.ndbc.noaa.gov/) buoy 46221 (Santa Monica Bay) | Live wave height, dominant/average period, mean wave direction |
| [Open-Meteo Marine API](https://open-meteo.com/en/docs/marine-weather-api) | Per-spot wave/swell/wind-wave height, direction, period forecast (exact lat/lon query) |
| [NOAA CO-OPS](https://tidesandcurrents.noaa.gov/) tide station 9410840 (Santa Monica) | Today's high/low tide times and heights |

Surfline was deliberately left out — it has no official public API, and
unofficial access relies on undocumented/reverse-engineered endpoints that can
break or violate their terms at any time. Everything here is a stable,
documented, official source.

## Setup

```bash
pip install -r requirements.txt
```

## Run standalone

```bash
python cli.py --list                     # see all spot ids
python cli.py manhattan_beach_pier       # one spot's full report
python cli.py all                        # every spot
```

## Run the web dashboard

```bash
python app.py
```
Then open http://127.0.0.1:5050 in a browser. You'll see all 7 spots as
cards (current wave height, swell direction/period, water temp, next tide) —
click any card for a 5-day date-by-date forecast table with wave height
range, swell direction/period, and tide highs/lows per day.

This only needs `requests` and `flask`, both of which work fine on Python
3.9 — no need for the 3.10+ upgrade unless you're also using the MCP server.

## Deploy a shareable live link (Render, free)

1. Push this folder to a GitHub repo (see steps below).
2. Go to [render.com](https://render.com), sign up with GitHub (no credit card needed).
3. Click **New +** → **Web Service** → connect your repo. Render will detect `render.yaml` and pre-fill the build/start commands — just click **Create Web Service**.
4. After ~1-2 minutes you'll get a live URL like `https://south-bay-surf-report.onrender.com` — that's your shareable link, works on any device.
5. From then on, every `git push` to your repo automatically triggers a rebuild and redeploy — no manual redeploy step.

Free tier note: the service spins down after 15 minutes idle and takes about a minute to spin back up on the next visit — fine for demoing, just not instant if it's been sitting unused.

**Getting the code onto GitHub** (from the project folder in a terminal):
```bash
git init
git add .
git commit -m "Initial commit"
```
Then create a new empty repo at github.com/new (don't check "add a README"), and:
```bash
git remote add origin https://github.com/<your-username>/South-Bay-Surf-Report.git
git branch -M main
git push -u origin main
```
`.gitignore` is already set up to skip your `venv`/`.venv` folders so they won't get committed.

## Run as an MCP server

Register with Claude Code:

```bash
claude mcp add southbay-surf -- python /full/path/to/southbay_surf/mcp_server.py
```

Or add manually to your MCP client config:

```json
{
  "mcpServers": {
    "southbay-surf": {
      "command": "python",
      "args": ["/full/path/to/southbay_surf/mcp_server.py"]
    }
  }
}
```

Once connected, 5 tools are available: `list_spots`, `get_spot_conditions`,
`get_all_conditions`, `get_buoy_snapshot`, `get_tide_today`.

## Files

- `spots.json` — spot list, coordinates, buoy/tide station config
- `buoys.py` — NDBC buoy fetch + parse
- `marine.py` — Open-Meteo per-spot swell/wave forecast fetch + parse, plus `fetch_daily_summary` for the multi-day view
- `tides.py` — NOAA CO-OPS tide fetch + parse, plus `fetch_tides_range` for multi-day tide events
- `core.py` — shared aggregation logic (with a 10-minute cache) used by all three entry points
- `cli.py` — standalone command-line entry point
- `app.py` — Flask web app (dashboard) entry point
- `templates/index.html`, `static/style.css`, `static/app.js` — the dashboard UI
- `mcp_server.py` — MCP server entry point (FastMCP)

## How this was verified

The buoy parser was tested against a real, live pull from NDBC station 46221.
The marine, tide, and daily-aggregation logic were tested against realistic
response shapes matching each API's documented schema, and the Flask routes
were tested end-to-end with Flask's test client (including that the page and
static assets serve correctly) — all with mocked network calls, since this
sandbox's network egress doesn't reach those specific domains. Before your
first real run, do a smoke test with `python cli.py manhattan_beach_pier` or
`python app.py` to confirm live connectivity from your own machine.

## Possible next steps

- Add Scripps CDIP nearshore wave model (MOP) data for point-break-level accuracy
- Cache results to SQLite for historical trend charts
- Add a scheduled job to snapshot conditions every hour
- Add a "best spot right now" ranking across all 7 based on swell/wind alignment
