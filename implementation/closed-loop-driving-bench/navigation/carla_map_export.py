#!/usr/bin/env python3
"""Export a CARLA 0.9.16 map as AutoE2E's navigation map JSON.

Runs on the bench next to the CARLA server (aarch64/x86 with the ``carla``
wheel); connects over RPC, samples every lane, and writes the primitives of
upstream ``navigation.contracts.NavigationMap`` as one JSON file that
``navigation_raster`` (C++) and ``nav_map_json.load_map`` (Python reference
path) both read.

What is exported, and from what CARLA API:

* lane centrelines -- ``map.generate_waypoints(sample_distance)`` grouped by
  ``(road_id, section_id, lane_id)`` and ordered in the lane's driving
  direction, from the lane's exact start to its exact end.  The samples stop
  up to ``sample_distance`` short of the far end of each road and lane
  section, so each lane is closed with the start ``map.get_topology()`` gives
  and the end ``Waypoint.next_until_lane_end`` or the topology gives
  (``lane_ends``);
* lane boundaries -- the centreline offset by half the waypoint's
  ``lane_width`` to each side (CARLA has no boundary geometry of its own; the
  lane width is the authoritative quantity);
* drivable polygons -- one closed polygon per lane, left boundary forward plus
  right boundary reversed, as upstream's OSM and Lanelet2 adapters do.  Each
  lane ends where the next one starts, so consecutive polygons meet as
  upstream's lanelets do at their shared nodes;
* intersections -- the convex hull of the drivable area of every lane whose
  waypoints report ``is_junction`` for that ``junction.id``; CARLA has no
  junction polygon, this is the junction's footprint;
* crosswalks -- ``map.get_crosswalks()``, four ``Location`` per quad;
* stop lines -- for every ``traffic.traffic_light`` actor, the lateral line
  through the waypoint underneath it (CARLA publishes no stop-line geometry);
* static traffic signals -- the traffic-light actor positions;
* traffic direction -- one directed lane field per lane centreline (the
  rasterizer encodes sin/cos of each segment's heading).

Not exported: road levels (CARLA has no layered roads, so channels 11-13 stay
zero), lane-change adjacency (the checkpoint's raster has no such channel).

Frame: CARLA's y is negated, headings are negated -- see ``carla_frame.py``.

Usage on the bench::

    python3 carla_map_export.py --host 10.10.0.2 --port 2000 \
        --out /runs/<run>/navigation/map.json --map Town10HD_Opt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from typing import Any, Iterable, Sequence

import numpy as np

import carla_frame
import nav_map_json

EXPORTER_VERSION = "carla_map_export_v2"
DEFAULT_SAMPLE_DISTANCE_M = 2.0
DEFAULT_ORIGIN = (0.0, 0.0)
PROJECTION = "CARLA world frame, metres, y negated (right-handed 2D)"


# --------------------------------------------------------------------------- args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a CARLA map as AutoE2E navigation map JSON"
    )
    parser.add_argument("--host", default="127.0.0.1", help="CARLA RPC host")
    parser.add_argument("--port", type=int, default=2000, help="CARLA RPC port")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--map",
        default=None,
        help="expected map name (the exported map_version); refuse a mismatch",
    )
    parser.add_argument(
        "--sample-distance",
        type=float,
        default=DEFAULT_SAMPLE_DISTANCE_M,
        help="lane waypoint spacing in metres",
    )
    parser.add_argument("--out", required=True, help="map JSON path to write")
    parser.add_argument(
        "--no-crosswalks",
        action="store_true",
        help="skip map.get_crosswalks() (it is a beta API in 0.9.16)",
    )
    parser.add_argument(
        "--origin-lat", type=float, default=DEFAULT_ORIGIN[0],
        help="WGS84 latitude named by the map frame (CARLA is not georeferenced)",
    )
    parser.add_argument(
        "--origin-lon", type=float, default=DEFAULT_ORIGIN[1],
        help="WGS84 longitude named by the map frame",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="no summary on stdout"
    )
    return parser


# --------------------------------------------------------------------- geometry


def convex_hull(points: Iterable[Sequence[float]]) -> list[list[float]]:
    """Monotone-chain convex hull of [x, y] points (counter-clockwise)."""
    unique = sorted({(round(float(p[0]), 9), round(float(p[1]), 9)) for p in points})
    if len(unique) < 3:
        return [[x, y, 0.0] for x, y in unique]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    return [[x, y, 0.0] for x, y in hull]


def _dedupe(points: list[list[float]], decimals: int = 6) -> list[list[float]]:
    out: list[list[float]] = []
    seen = set()
    for point in points:
        key = (round(point[0], decimals), round(point[1], decimals))
        if key in seen:
            continue
        seen.add(key)
        out.append(point)
    return out


def _polyline_digest(points: list[list[float]], decimals: int = 6) -> str:
    """Identity of a boundary polyline, so shared lane sides are drawn once.

    Two lanes that drive in opposite directions share their left side in
    opposite orders, so the identity does not depend on the order.
    """
    def digest(sequence: list[list[float]]) -> str:
        payload = ",".join(
            f"{round(point[0], decimals)!r},{round(point[1], decimals)!r}"
            for point in sequence
        )
        return hashlib.sha256(payload.encode("ascii")).hexdigest()[:32]

    return min(digest(points), digest(list(reversed(points))))


def _waypoint_yaw_rad(waypoint: Any) -> float:
    return math.radians(float(waypoint.transform.rotation.yaw))


# ------------------------------------------------------------------------ lanes


def is_drivable(waypoint: Any) -> bool:
    """Keep driving lanes only; CARLA also samples sidewalks and bike lanes."""
    lane_type = getattr(waypoint, "lane_type", None)
    if lane_type is None:
        return True
    return str(lane_type).rsplit(".", 1)[-1] in ("Driving", "1")


def _lane_key(waypoint: Any) -> tuple[int, int, int]:
    return (int(waypoint.road_id), int(waypoint.section_id), int(waypoint.lane_id))


def _distance(first: Any, second: Any) -> float:
    a = first.transform.location
    b = second.transform.location
    return math.hypot(float(a.x) - float(b.x), float(a.y) - float(b.y))


# A closing waypoint this close to a lane's first or last sample replaces it,
# so a lane never gets a segment shorter than this (its heading would be noise).
CLOSE_TOLERANCE_M = 1e-3


def sample_lanes(
    carla_map: Any, sample_distance: float
) -> dict[tuple[int, int, int], list[Any]]:
    """Waypoints of every directed lane, keyed and ordered in its driving direction.

    ``map.generate_waypoints`` samples each road every ``sample_distance`` from
    its start (s = 0), so the samples of a lane stop up to that distance short
    of the far end of its road and of its lane section.  That end is the end of
    a lane that drives along s and the start of one that drives against it, and
    a lane section shorter than the spacing may get no sample at all.  Each
    lane therefore runs from the exact start to the exact end CARLA gives
    (``lane_ends``), its samples in between.
    """
    waypoints = carla_map.generate_waypoints(float(sample_distance))
    lanes: dict[tuple[int, int, int], list[Any]] = defaultdict(list)
    for waypoint in waypoints:
        if not is_drivable(waypoint):
            continue
        lanes[_lane_key(waypoint)].append(waypoint)
    for key in lanes:
        lanes[key].sort(key=lambda item: float(item.s))
        lanes[key] = _in_driving_direction(lanes[key])
    starts, ends = lane_ends(carla_map, lanes, sample_distance)
    return {
        key: _closed(lanes.get(key, []), starts.get(key), ends.get(key))
        for key in sorted(set(lanes) | set(starts))
    }


def lane_ends(
    carla_map: Any,
    lanes: dict[tuple[int, int, int], list[Any]],
    sample_distance: float,
) -> tuple[dict[tuple[int, int, int], Any], dict[tuple[int, int, int], Any]]:
    """The waypoints where each lane starts and ends in its driving direction.

    ``Map.get_topology()`` pairs a waypoint at the start of every drivable lane
    of every lane section, in its driving direction, with the start of each
    lane it leads into; a lane that leads nowhere is paired with its own end
    (CARLA 0.9.16, ``road::Map::GenerateTopology``).  The first waypoint of the
    pair is the lane's start.  Its end:

    * a lane that leads into another road ends where its road ends, and the
      last waypoint of ``next_until_lane_end`` is that point of the lane;
    * otherwise it is the pair's second waypoint: the start of the lane's
      continuation in the next lane section of its road, or the lane's own
      end.  ``next_until_lane_end`` is not used there: it walks to the end of
      the road, past the lane section.
    """
    starts: dict[tuple[int, int, int], Any] = {}
    followers: dict[tuple[int, int, int], list[Any]] = defaultdict(list)
    for entry, exit_waypoint in carla_map.get_topology():
        if not is_drivable(entry):
            continue
        key = _lane_key(entry)
        starts.setdefault(key, entry)
        followers[key].append(exit_waypoint)
    ends: dict[tuple[int, int, int], Any] = {}
    for key, following in followers.items():
        samples = lanes.get(key) or [starts[key]]
        last = samples[-1]
        if all(int(waypoint.road_id) != key[0] for waypoint in following):
            ends[key] = last.next_until_lane_end(float(sample_distance))[-1]
        else:
            ends[key] = min(following, key=lambda waypoint: _distance(waypoint, last))
    return starts, ends


def _closed(samples: list[Any], start: Any | None, end: Any | None) -> list[Any]:
    """A lane's samples with its exact start and end added."""
    points = list(samples)
    if start is not None:
        if points and _distance(points[0], start) <= CLOSE_TOLERANCE_M:
            points[0] = start
        else:
            points.insert(0, start)
    if end is not None:
        if points and _distance(points[-1], end) <= CLOSE_TOLERANCE_M:
            points[-1] = end
        else:
            points.append(end)
    return points


def _in_driving_direction(waypoints: list[Any]) -> list[Any]:
    """A lane's waypoints, sorted along ``s``, turned to its driving direction.

    CARLA lets ``s`` grow along the road's reference line in every lane and
    faces each waypoint in its lane's driving direction; with right-hand
    traffic the lanes with a positive id drive against the reference line.
    The order follows the waypoints' own heading, so it needs no sign rule.
    """
    along = 0.0
    for previous, current in zip(waypoints, waypoints[1:]):
        yaw = _waypoint_yaw_rad(previous)
        along += (
            (float(current.transform.location.x) - float(previous.transform.location.x)) * math.cos(yaw)
            + (float(current.transform.location.y) - float(previous.transform.location.y)) * math.sin(yaw)
        )
    return list(reversed(waypoints)) if along < 0.0 else waypoints


def lane_geometry(waypoints: list[Any]):
    """Centreline (CARLA), yaws and half widths of one lane."""
    centerline = [(float(wp.transform.location.x), float(wp.transform.location.y))
                  for wp in waypoints]
    yaws = [_waypoint_yaw_rad(wp) for wp in waypoints]
    half_widths = [float(wp.lane_width) * 0.5 for wp in waypoints]
    return centerline, yaws, half_widths


def is_usable_lane(waypoints: list[Any]) -> bool:
    return len(waypoints) >= 2


# ----------------------------------------------------------------------- export


def export_map(
    carla_map: Any,
    *,
    world: Any | None = None,
    sample_distance: float = DEFAULT_SAMPLE_DISTANCE_M,
    include_crosswalks: bool = True,
    origin: tuple[float, float] = DEFAULT_ORIGIN,
    carla_version: str = "unknown",
) -> Any:
    """Build the upstream ``NavigationMap`` of a CARLA map."""
    contracts = nav_map_json.autoe2e_bridge.contracts()
    map_name = str(carla_map.name).split("/")[-1]  # CARLA 0.9.16 reports "Carla/Maps/<name>" (bench finding 2026-11-09)
    lanes = sample_lanes(carla_map, sample_distance)

    drivable: list[Any] = []
    boundaries: dict[str, Any] = {}
    centerlines: list[Any] = []
    directed: list[Any] = []
    junction_points: dict[int, list[list[float]]] = defaultdict(list)

    for key in sorted(lanes):
        waypoints = lanes[key]
        if not is_usable_lane(waypoints):
            continue
        road_id, section_id, lane_id = key
        lane_name = f"carla:{map_name}:road{road_id}:sec{section_id}:lane{lane_id}"
        centerline, yaws, half_widths = lane_geometry(waypoints)

        map_center = [
            list(carla_frame.carla_to_map_xy(x, y)) + [0.0]
            for x, y in centerline
        ]
        map_center = _dedupe(map_center)
        if len(map_center) < 2:
            continue

        centerlines.append(
            contracts.PolylinePrimitive(
                primitive_id=f"{lane_name}:centerline",
                points_enu_m=map_center,
                level=None,
            )
        )
        directed.append(
            contracts.DirectedLaneField(
                lane_id=lane_name,
                centerline_enu_m=map_center,
                level=None,
            )
        )

        left = carla_frame.lane_boundary_points(
            centerline, yaws, half_widths, side="left"
        )
        right = carla_frame.lane_boundary_points(
            centerline, yaws, half_widths, side="right"
        )
        polygon = _dedupe(left + list(reversed(right)))
        for side, points in (("left", left), ("right", right)):
            if len(points) < 2:
                continue
            digest = _polyline_digest(points)
            boundaries.setdefault(
                digest,
                contracts.PolylinePrimitive(
                    primitive_id=f"{lane_name}:{side}",
                    points_enu_m=points,
                    level=None,
                ),
            )
        if len(polygon) >= 3:
            primitive = contracts.PolygonPrimitive(
                primitive_id=f"{lane_name}:drivable",
                points_enu_m=polygon,
                level=None,
            )
            drivable.append(primitive)
            for waypoint in waypoints:
                # Only the lane's own waypoints: its end may be the start of
                # the lane it leads into, which can lie in a junction.
                if not bool(waypoint.is_junction) or _lane_key(waypoint) != key:
                    continue
                try:
                    junction_id = int(waypoint.get_junction().id)
                except Exception:  # no junction object: fall back to position
                    junction_id = -1
                junction_points[junction_id].extend(
                    [point[:2] for point in polygon]
                )

    intersections = []
    for junction_id in sorted(junction_points):
        hull = convex_hull(junction_points[junction_id])
        if len(hull) < 3:
            continue
        intersections.append(
            contracts.PolygonPrimitive(
                primitive_id=f"carla:{map_name}:junction{junction_id}",
                points_enu_m=hull,
                level=None,
            )
        )

    crosswalks = _crosswalk_polygons(
        carla_map, map_name, contracts, include_crosswalks
    )
    stop_lines, signals = _traffic_controls(
        carla_map, world, map_name, contracts
    )

    bound_points = []
    for primitive in (
        list(drivable)
        + list(boundaries.values())
        + centerlines
        + intersections
        + crosswalks
        + stop_lines
    ):
        bound_points.append(primitive.points_enu_m)
    for signal in signals:
        bound_points.append(signal.position_enu_m.reshape(1, 3))
    if not bound_points:
        raise ValueError(f"map {map_name!r} yielded no renderable primitives")
    stacked = np.concatenate(bound_points, axis=0)
    x_min = float(stacked[:, 0].min())
    y_min = float(stacked[:, 1].min())
    x_max = float(stacked[:, 0].max())
    y_max = float(stacked[:, 1].max())
    if x_min == x_max:
        x_min -= 0.5
        x_max += 0.5
    if y_min == y_max:
        y_min -= 0.5
        y_max += 0.5

    frame = contracts.MapFrame(
        frame_id=f"carla:{map_name}",
        origin_latitude_deg=float(origin[0]),
        origin_longitude_deg=float(origin[1]),
        projection=PROJECTION,
    )
    return contracts.NavigationMap(
        map_version=map_name,
        provider="carla",
        frame=frame,
        bounds_enu_m=(x_min, y_min, x_max, y_max),
        drivable_polygons=tuple(drivable),
        lane_boundaries=tuple(boundaries[key] for key in sorted(boundaries)),
        lane_centerlines=tuple(centerlines),
        intersection_polygons=tuple(intersections),
        crosswalk_polygons=tuple(crosswalks),
        stop_lines=tuple(stop_lines),
        static_traffic_signals=tuple(signals),
        directed_lane_fields=tuple(directed),
        layer_availability={
            "crosswalk": bool(crosswalks),
            "drivable_area": bool(drivable),
            "intersection": bool(intersections),
            "lane_boundary": bool(boundaries),
            "lane_centerline": bool(centerlines),
            "road_level": False,
            "static_traffic_signal": bool(signals),
            "stop_line": bool(stop_lines),
            "traffic_direction": bool(directed),
        },
        provenance={
            "adapter_version": EXPORTER_VERSION,
            "carla_version": carla_version,
            "map": map_name,
            "sample_distance_m": float(sample_distance),
            "frame_conversion": "x_map=x, y_map=-y, yaw_map=-yaw (ICD section 9)",
        },
    )


def _crosswalk_polygons(
    carla_map: Any, map_name: str, contracts: Any, include: bool
) -> list[Any]:
    if not include:
        return []
    getter = getattr(carla_map, "get_crosswalks", None)
    if getter is None:
        return []
    try:
        locations = list(getter())
    except Exception:
        return []
    if not locations:
        return []
    polygons = []
    for index, ring in enumerate(_closed_rings(locations)):
        points = [list(carla_frame.carla_to_map_point(item)) + [0.0]
                  for item in ring]
        points = _dedupe(points)
        if len(points) < 3:
            continue
        polygons.append(
            contracts.PolygonPrimitive(
                primitive_id=f"carla:{map_name}:crosswalk{index}",
                points_enu_m=points,
                level=None,
            )
        )
    return polygons


def _closed_rings(locations: list[Any], tolerance_m: float = 1e-3) -> list[list[Any]]:
    """CARLA's crosswalk list split into its polygons.

    ``Map.get_crosswalks`` gives every crosswalk as a closed polygon whose
    first point is repeated at its end, and the polygons need not have the
    same number of points. A ring ends where its first point comes back; the
    repeated point is not kept. A trailing run that never closes is left out.
    """
    rings: list[list[Any]] = []
    current: list[Any] = []
    for item in locations:
        if (
            len(current) >= 3
            and abs(float(item.x) - float(current[0].x)) <= tolerance_m
            and abs(float(item.y) - float(current[0].y)) <= tolerance_m
        ):
            rings.append(current)
            current = []
        else:
            current.append(item)
    return rings


def _traffic_controls(
    carla_map: Any, world: Any | None, map_name: str, contracts: Any
):
    """Stop lines and signal positions from the traffic-light actors."""
    if world is None:
        return [], []
    try:
        actors = list(world.get_actors().filter("traffic.traffic_light"))
    except Exception:
        return [], []
    stop_lines = []
    signals = []
    for index, actor in enumerate(actors):
        location = actor.get_transform().location
        map_x, map_y = carla_frame.carla_to_map_point(location)
        signals.append(
            contracts.StaticTrafficSignal(
                signal_id=f"carla:{map_name}:signal{index}",
                position_enu_m=[map_x, map_y, float(getattr(location, "z", 0.0))],
                level=None,
            )
        )
        try:
            waypoint = carla_map.get_waypoint(location)
        except Exception:
            continue
        yaw = _waypoint_yaw_rad(waypoint)
        half_width = float(waypoint.lane_width) * 0.5
        right_x, right_y = carla_frame.right_vector(yaw)
        center_x = float(waypoint.transform.location.x)
        center_y = float(waypoint.transform.location.y)
        ends = [
            (center_x - half_width * right_x, center_y - half_width * right_y),
            (center_x + half_width * right_x, center_y + half_width * right_y),
        ]
        points = [
            list(carla_frame.carla_to_map_xy(x, y)) + [0.0] for x, y in ends
        ]
        stop_lines.append(
            contracts.PolylinePrimitive(
                primitive_id=f"carla:{map_name}:stop_line{index}",
                points_enu_m=points,
                level=None,
            )
        )
    return stop_lines, signals


# ------------------------------------------------------------------------- main


def connect(host: str, port: int, timeout: float):
    import carla

    client = carla.Client(host, int(port))
    client.set_timeout(float(timeout))
    world = client.get_world()
    return carla, client, world, world.get_map()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        carla, client, world, carla_map = connect(args.host, args.port, args.timeout)
    except Exception as error:  # pragma: no cover - bench only
        print(f"error: cannot reach CARLA at {args.host}:{args.port}: {error}",
              file=sys.stderr)
        return 2

    map_name = str(carla_map.name).split("/")[-1]  # CARLA 0.9.16 reports "Carla/Maps/<name>" (bench finding 2026-11-09)
    if args.map and args.map != map_name:
        print(
            f"error: connected map is {map_name!r}, expected {args.map!r}",
            file=sys.stderr,
        )
        return 3

    navigation_map = export_map(
        carla_map,
        world=world,
        sample_distance=args.sample_distance,
        include_crosswalks=not args.no_crosswalks,
        origin=(args.origin_lat, args.origin_lon),
        carla_version=str(getattr(client, "get_client_version", lambda: "unknown")()),
    )
    digest = nav_map_json.dump_map(args.out, navigation_map)
    # Read the file back: the C++ library parses exactly this text.
    reloaded = nav_map_json.load_map(args.out)
    if nav_map_json.map_to_payload(reloaded) != nav_map_json.map_to_payload(
        navigation_map
    ):
        print("error: exported map JSON does not round-trip", file=sys.stderr)
        return 4

    summary = {
        "out": str(args.out),
        "map": map_name,
        "sha256": digest,
        "drivable_polygons": len(navigation_map.drivable_polygons),
        "lane_boundaries": len(navigation_map.lane_boundaries),
        "lane_centerlines": len(navigation_map.lane_centerlines),
        "intersection_polygons": len(navigation_map.intersection_polygons),
        "crosswalk_polygons": len(navigation_map.crosswalk_polygons),
        "stop_lines": len(navigation_map.stop_lines),
        "static_traffic_signals": len(navigation_map.static_traffic_signals),
        "directed_lane_fields": len(navigation_map.directed_lane_fields),
        "bounds_enu_m": list(navigation_map.bounds_enu_m),
    }
    if not args.quiet:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
