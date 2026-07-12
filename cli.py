"""
Standalone CLI - no MCP required.

Usage:
    python cli.py                    # all spots
    python cli.py all                # all spots
    python cli.py manhattan_beach_pier   # one spot
    python cli.py --list             # show valid spot ids
"""

import json
import sys

import core


def main():
    args = sys.argv[1:]

    if args and args[0] in ("--list", "-l"):
        for spot in core.list_spots():
            print(f"{spot['id']:24s} {spot['name']}")
        return

    if args and args[0] != "all":
        print(json.dumps(core.get_spot_conditions(args[0]), indent=2))
    else:
        print(json.dumps(core.get_all_conditions(), indent=2))


if __name__ == "__main__":
    main()
