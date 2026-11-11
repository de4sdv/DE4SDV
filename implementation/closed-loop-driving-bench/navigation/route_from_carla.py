#!/usr/bin/env python3
"""Route between two points of a CARLA map, written as the ICD section 9 file.

Uses CARLA's own planner, ``PythonAPI/carla/agents/navigation/
global_route_planner.GlobalRoutePlanner(carla_map, sampling_resolution)`` and
its ``trace_route(start_location, end_location)``.  The resulting waypoints are
converted from CARLA's left-handed world to the right-handed map frame
(``x`` kept, ``y`` negated, heading negated -- see ``carla_frame.py``) and
written as::

    {"map": "Town10HD_Opt",
     "waypoints": [[x, y, heading_rad, road_id], ...],
     "destination": [x, y]}

exactly the keys ICD section 9 fixes.  ``heading_rad`` is counter-clockwise
from ``+x``; ``road_id`` is CARLA's road id as an integer, which the C++ route
reader uses to split the waypoint list into one lane segment per road.

Usage on the bench::

    python3 route_from_carla.py --host 10.10.0.2 --port 2000 \
        --start-spawn 0 --end-spawn 40 \
        --out /runs/<run>/navigation/route.json
    python3 route_from_carla.py --start 12.5,-3.0 --end 210.0,88.0 --out route.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import carla_frame

DEFAULT_SAMPLING_RESOLUTION_M = 2.0
ROUTE_EXPORTER_VERSION = "carla_route_v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Route between two CARLA points as the ICD section 9 file"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--sampling-resolution",
        type=float,
        default=DEFAULT_SAMPLING_RESOLUTION_M,
        help="GlobalRoutePlanner sampling resolution in metres",
    )
    parser.add_argument(
        "--start", help="start as CARLA world x,y (metres)"
    )
    parser.add_argument("--end", help="end as CARLA world x,y (metres)")
    parser.add_argument(
        "--start-spawn",
        type=int,
        default=None,
        help="index into map.get_spawn_points() for the start",
    )
    parser.add_argument(
        "--end-spawn",
        type=int,
        default=None,
        help="index into map.get_spawn_points() for the end",
    )
    parser.add_argument(
        "--carla-api-path",
        default=None,
        help="directory holding CARLA's PythonAPI 'agents' package, if not on "
        "sys.path (e.g. /opt/carla/PythonAPI/carla)",
    )
    parser.add_argument(
        "--map", default=None, help="expected map name; refuse a mismatch"
    )
    parser.add_argument("--out", required=True, help="route JSON path to write")
    parser.add_argument("--quiet", action="store_true")
    return parser


def _parse_xy(value: str, name: str) -> tuple[float, float]:
    parts = value.split(",")
    if len(parts) != 2:
        raise SystemExit(f"error: {name} must be 'x,y'")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        raise SystemExit(f"error: {name} is not numeric: {value!r}")


def import_global_route_planner(api_path: str | None):
    """``agents.navigation.global_route_planner`` from CARLA's PythonAPI."""
    if api_path:
        candidate = Path(api_path)
        if not candidate.is_dir():
            raise SystemExit(f"error: --carla-api-path {api_path} is not a directory")
        sys.path.insert(0, str(candidate))
    try:
        from agents.navigation.global_route_planner import (  # type: ignore
            GlobalRoutePlanner,
        )
    except ImportError as error:
        raise SystemExit(
            "error: cannot import agents.navigation.global_route_planner "
            f"({error}); pass --carla-api-path <CARLA>/PythonAPI/carla"
        )
    return GlobalRoutePlanner


def route_waypoints(trace) -> list[list[float]]:
    """Convert ``trace_route`` output to ICD waypoint rows, deduplicated."""
    rows: list[list[float]] = []
    seen: set[tuple[float, float]] = set()
    for entry in trace:
        # GlobalRoutePlanner returns (waypoint, RoadOption) pairs.
        waypoint = entry[0] if isinstance(entry, (tuple, list)) else entry
        transform = waypoint.transform
        map_x, map_y = carla_frame.carla_to_map_point(transform.location)
        heading = carla_frame.carla_to_map_heading_deg(transform.rotation.yaw)
        key = (round(map_x, 6), round(map_y, 6))
        if key in seen:
            continue
        seen.add(key)
        rows.append([map_x, map_y, heading, int(waypoint.road_id)])
    return rows


def build_route_file(
    *,
    map_name: str,
    waypoints: list[list[float]],
    destination_xy: tuple[float, float],
) -> dict:
    if len(waypoints) < 2:
        raise ValueError("a route needs at least two distinct waypoints")
    destination = list(carla_frame.carla_to_map_xy(*destination_xy))
    return {
        "map": str(map_name),
        "waypoints": waypoints,
        "destination": destination,
    }


def write_route_file(path: str | Path, payload: dict) -> str:
    import nav_map_json

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload, allow_nan=False, ensure_ascii=True, separators=(",", ":")
    )
    target.write_text(text + "\n", encoding="ascii")
    return nav_map_json.sha256_file(target)


def _spawn_location(carla_map, index: int):
    spawn_points = list(carla_map.get_spawn_points())
    if not 0 <= index < len(spawn_points):
        raise SystemExit(
            f"error: spawn point {index} out of range (0..{len(spawn_points) - 1})"
        )
    return spawn_points[index]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.start is None and args.start_spawn is None:
        raise SystemExit("error: give --start x,y or --start-spawn N")
    if args.end is None and args.end_spawn is None:
        raise SystemExit("error: give --end x,y or --end-spawn N")

    try:
        import carla

        client = carla.Client(args.host, int(args.port))
        client.set_timeout(float(args.timeout))
        carla_map = client.get_world().get_map()
    except Exception as error:  # pragma: no cover - bench only
        print(f"error: cannot reach CARLA at {args.host}:{args.port}: {error}",
              file=sys.stderr)
        return 2

    map_name = str(carla_map.name).split("/")[-1]  # CARLA 0.9.16 reports "Carla/Maps/<name>" (bench finding 2026-11-09)
    if args.map and args.map != map_name:
        print(f"error: connected map is {map_name!r}, expected {args.map!r}",
              file=sys.stderr)
        return 3

    if args.start_spawn is not None:
        start_transform = _spawn_location(carla_map, args.start_spawn).location
        start_xy = (float(start_transform.x), float(start_transform.y))
    else:
        start_xy = _parse_xy(args.start, "--start")
    if args.end_spawn is not None:
        end_transform = _spawn_location(carla_map, args.end_spawn).location
        end_xy = (float(end_transform.x), float(end_transform.y))
    else:
        end_xy = _parse_xy(args.end, "--end")

    GlobalRoutePlanner = import_global_route_planner(args.carla_api_path)
    planner = GlobalRoutePlanner(carla_map, float(args.sampling_resolution))
    # CARLA's planner works on the CARLA frame (it walks the map's topology).
    trace = planner.trace_route(
        carla.Location(x=start_xy[0], y=start_xy[1], z=0.0),
        carla.Location(x=end_xy[0], y=end_xy[1], z=0.0),
    )
    try:
        waypoints = route_waypoints(trace)
    except Exception as error:
        print(f"error: route conversion failed: {error}", file=sys.stderr)
        return 4
    if len(waypoints) < 2:
        print("error: GlobalRoutePlanner returned fewer than two distinct "
              "waypoints", file=sys.stderr)
        return 5

    payload = build_route_file(
        map_name=map_name, waypoints=waypoints, destination_xy=end_xy
    )
    # Read back with the same reader the C++ library mirrors.
    import nav_map_json

    digest = write_route_file(args.out, payload)
    readback = nav_map_json.read_route_file(args.out)
    if int(len(readback["waypoints"])) != len(waypoints):
        print("error: route file does not round-trip", file=sys.stderr)
        return 6

    if not args.quiet:
        print(json.dumps({
            "out": str(args.out),
            "map": map_name,
            "waypoints": len(waypoints),
            "destination": payload["destination"],
            "sample_resolution_m": float(args.sampling_resolution),
            "length_m": _length_m(waypoints),
            "sha256": digest,
            "headers": {"exporter": ROUTE_EXPORTER_VERSION,
                        "global_route_planner_sampling_m":
                            float(args.sampling_resolution)},
        }, indent=2, sort_keys=True))
    return 0


def _length_m(waypoints: list[list[float]]) -> float:
    total = 0.0
    for first, second in zip(waypoints, waypoints[1:]):
        total += math.hypot(second[0] - first[0], second[1] - first[1])
    return total


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
