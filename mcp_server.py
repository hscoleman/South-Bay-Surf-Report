"""
MCP server exposing South Bay LA surf conditions as tools any MCP client
(Claude Desktop, Claude Code, etc.) can call directly.

Register it in Claude Code with:
    claude mcp add southbay-surf -- python /full/path/to/mcp_server.py

Or add it manually to your MCP config, e.g.:
    {
      "mcpServers": {
        "southbay-surf": {
          "command": "python",
          "args": ["/full/path/to/southbay_surf/mcp_server.py"]
        }
      }
    }
"""

from mcp.server.fastmcp import FastMCP

import core

mcp = FastMCP("southbay-surf")


@mcp.tool()
def list_spots() -> list:
    """List all South Bay LA surf spots covered (Playa del Rey through Hermosa Beach)
    with their ids and coordinates. Call this first to see valid spot_id values."""
    return core.list_spots()


@mcp.tool()
def get_spot_conditions(spot_id: str) -> dict:
    """Get current swell/wave forecast, nearest buoy reading, and today's tides
    for a single surf spot. Use list_spots to find valid spot_id values
    (e.g. 'manhattan_beach_pier', 'hermosa_beach_pier', 'el_porto')."""
    return core.get_spot_conditions(spot_id)


@mcp.tool()
def get_all_conditions() -> list:
    """Get current conditions (swell forecast, buoy data, tides) for every
    South Bay surf spot at once, Playa del Rey through Hermosa Beach."""
    return core.get_all_conditions()


@mcp.tool()
def get_buoy_snapshot(station_id: str) -> dict:
    """Get the latest raw reading from a specific NOAA NDBC buoy station.
    Common stations: '46221' (Santa Monica Bay, primary), '46222' (San Pedro),
    '46025' (Santa Monica Basin, offshore)."""
    return core.get_buoy_snapshot(station_id)


@mcp.tool()
def get_tide_today() -> list:
    """Get today's high/low tide predictions for the South Bay reference station
    (Santa Monica, CA - NOAA CO-OPS station 9410840)."""
    return core.get_tide_today()


if __name__ == "__main__":
    mcp.run()
