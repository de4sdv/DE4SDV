"""Synthetic navigation maps and routes for the rasterizar parity tests.

Three shapes of increasing nastiness -- a straight road, an L junction and a
roundabout-ish closed ring -- built as upstream ``NavigationMap`` objects so the
same JSON drives both the Python reference path and the C++ library.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import autoe2e_bridge

MAP_NAME = "Town10HD_Synthetic"


def _contracts():
    return autoe2e_bridge.contracts()


def _frame():
    contracts = _contracts()
    return contracts.MapFrame(
        frame_id="synthetic:map",
        origin_latitude_deg=0.0,
        origin_longitude_deg=0.0,
        projection="synthetic right-handed metric frame",
    )


def _rect(x0, y0, x1, y1):
    return np.asarray(
        [[x0, y0, 0.0], [x1, y0, 0.0], [x1, y1, 0.0], [x0, y1, 0.0]]
    )


def _line(points):
    return np.asarray([[x, y, 0.0] for x, y in points], dtype=np.float64)


def straight_road():
    contracts = _contracts()
    centre = _line([(-30.0, 0.0), (110.0, 0.0)])
    return contracts.NavigationMap(
        map_version=MAP_NAME,
        provider="synthetic",
        frame=_frame(),
        bounds_enu_m=(-30.0, -10.0, 110.0, 10.0),
        drivable_polygons=(
            contracts.PolygonPrimitive("road", _rect(-30.0, -7.0, 110.0, 7.0)),
        ),
        lane_boundaries=(
            contracts.PolylinePrimitive("boundary-left", _line([(-30.0, 3.5), (110.0, 3.5)])),
            contracts.PolylinePrimitive("boundary-right", _line([(-30.0, -3.5), (110.0, -3.5)])),
        ),
        lane_centerlines=(
            contracts.PolylinePrimitive("centre", centre),
            contracts.PolylinePrimitive(
                "centre-offset", _line([(-30.0, 1.75), (110.0, 1.75)])
            ),
        ),
        stop_lines=(
            contracts.PolylinePrimitive("stop", _line([(20.0, -7.0), (20.0, 7.0)])),
        ),
        static_traffic_signals=(
            contracts.StaticTrafficSignal("signal", np.asarray([20.0, 4.0, 0.0])),
        ),
        directed_lane_fields=(
            contracts.DirectedLaneField("lane-east", centre),
        ),
        layer_availability={"road_level": False},
        provenance={"fixture": "straight_road"},
    )


def l_junction():
    contracts = _contracts()
    horizontal = _line([(-30.0, 0.0), (100.0, 0.0)])
    vertical = _line([(100.0, 0.0), (100.0, 60.0)])
    return contracts.NavigationMap(
        map_version=MAP_NAME,
        provider="synthetic",
        frame=_frame(),
        bounds_enu_m=(-30.0, -10.0, 112.0, 60.0),
        drivable_polygons=(
            contracts.PolygonPrimitive("road-x", _rect(-30.0, -7.0, 107.0, 7.0)),
            contracts.PolygonPrimitive("road-y", _rect(93.0, -7.0, 107.0, 60.0)),
        ),
        lane_boundaries=(
            contracts.PolylinePrimitive("x-left", _line([(-30.0, 3.5), (107.0, 3.5)])),
            contracts.PolylinePrimitive("y-right", _line([(107.0, -7.0), (107.0, 60.0)])),
        ),
        lane_centerlines=(
            contracts.PolylinePrimitive("x-centre", horizontal),
            contracts.PolylinePrimitive("y-centre", vertical),
        ),
        intersection_polygons=(
            contracts.PolygonPrimitive("junction", _rect(93.0, -7.0, 107.0, 7.0)),
        ),
        crosswalk_polygons=(
            contracts.PolygonPrimitive("crosswalk", _rect(88.0, -7.0, 90.0, 7.0)),
        ),
        stop_lines=(
            contracts.PolylinePrimitive("stop", _line([(90.0, -7.0), (90.0, 7.0)])),
        ),
        static_traffic_signals=(
            contracts.StaticTrafficSignal("signal", np.asarray([90.0, 5.0, 0.0])),
        ),
        directed_lane_fields=(
            contracts.DirectedLaneField("lane-x", horizontal),
            contracts.DirectedLaneField("lane-y", vertical),
        ),
        layer_availability={"road_level": False},
        provenance={"fixture": "l_junction"},
    )


def roundabout_arc():
    contracts = _contracts()
    outer = [
        [23.5 * math.cos(math.radians(-90 + 10 * index)),
         23.5 * math.sin(math.radians(-90 + 10 * index)), 0.0]
        for index in range(36)
    ]
    inner = [
        [16.5 * math.cos(math.radians(-90 - 10 * index)),
         16.5 * math.sin(math.radians(-90 - 10 * index)), 0.0]
        for index in range(36)
    ]
    ring = np.asarray(outer + inner)
    arc = _line([
        (20.0 * math.cos(math.radians(-120 + 7.5 * index)),
         20.0 * math.sin(math.radians(-120 + 7.5 * index)))
        for index in range(49)
    ])
    return contracts.NavigationMap(
        map_version=MAP_NAME,
        provider="synthetic",
        frame=_frame(),
        bounds_enu_m=(-24.0, -24.0, 24.0, 24.0),
        drivable_polygons=(contracts.PolygonPrimitive("ring", ring),),
        lane_boundaries=(
            contracts.PolylinePrimitive(
                "outer", np.asarray(outer, dtype=np.float64)
            ),
            contracts.PolylinePrimitive(
                "inner", np.asarray(inner, dtype=np.float64)
            ),
        ),
        lane_centerlines=(contracts.PolylinePrimitive("arc", arc),),
        directed_lane_fields=(contracts.DirectedLaneField("arc", arc),),
        layer_availability={"road_level": False},
        provenance={"fixture": "roundabout_arc"},
    )


MAPS = {
    "straight": straight_road,
    "l_junction": l_junction,
    "roundabout": roundabout_arc,
}


def route_waypoints(kind: str):
    """Waypoints (x, y, heading, road_id) in the map frame, per fixture."""
    if kind == "straight":
        return [[x, 0.0, 0.0, 1] for x in np.arange(-10.0, 70.0, 2.0)]
    if kind == "l_junction":
        rows = [[x, 0.0, 0.0, 1] for x in np.arange(-10.0, 92.0, 2.0)]
        rows += [[100.0, y, math.pi / 2.0, 2] for y in np.arange(0.0, 12.0, 2.0)]
        return rows
    angles = np.radians(np.arange(-110.0, 140.0, 4.0))
    return [[20.0 * math.cos(a), 20.0 * math.sin(a), a + math.pi / 2.0, 1]
            for a in angles]


def write_route(path: Path, kind: str, *, destination=None) -> Path:
    return write_route_rows(path, route_waypoints(kind), destination=destination)


def write_route_rows(path: Path, rows, *, destination=None) -> Path:
    """A route file of the given waypoint rows (x, y, heading, road_id)."""
    rows = [[float(row[0]), float(row[1]), float(row[2]), int(row[3])] for row in rows]
    if destination is None:
        destination = [rows[-1][0], rows[-1][1]]
    path.write_text(
        json.dumps(
            {"map": MAP_NAME, "waypoints": rows, "destination": list(destination)},
            separators=(",", ":"),
        ) + "\n",
        encoding="ascii",
    )
    return path


# Routes whose road id changes, on the straight road.  CARLA's planner gives
# 2-4 m between the last waypoint of one road and the first of the next; these
# make the joint wider than the 3.5 m corridor, so a corridor drawn per road
# run without the joint has rows with no corridor pixel.


def road_change_rows():
    """Road 1 up to x=20, road 2 from x=26: a 6 m joint."""
    rows = [[x, 0.0, 0.0, 1] for x in np.arange(0.0, 21.0, 2.0)]
    rows += [[x, 0.0, 0.0, 2] for x in np.arange(26.0, 61.0, 2.0)]
    return rows


def single_point_run_rows():
    """Road 2 is one waypoint, 2.5 m off the line between roads 1 and 3."""
    rows = [[x, 0.0, 0.0, 1] for x in np.arange(0.0, 21.0, 2.0)]
    rows.append([24.0, 2.5, 0.0, 2])
    rows += [[x, 0.0, 0.0, 3] for x in np.arange(28.0, 61.0, 2.0)]
    return rows


def expected_corridor(rows, pose, *, half_width_m=1.75, rear_clip_m=10.0,
                      tie_m=1e-6):
    """route_mask channel 0 of the route drawn as one line, from geometry alone.

    The rule of upstream's ``draw_route_line``, worked out here without the
    route reader or the renderer: a pixel is set when its centre is within
    ``half_width_m`` of the polyline through all waypoints, in their order, and
    no more than ``rear_clip_m`` behind the ego.  Returns ``(mask, decided)``;
    ``decided`` is False for the few centres within ``tie_m`` of either
    threshold, where rounding may go either way.
    """
    x0, y0, yaw = (float(value) for value in pose)
    cosine, sine = math.cos(yaw), math.sin(yaw)
    points = np.asarray([[row[0], row[1]] for row in rows], dtype=np.float64)
    dx = points[:, 0] - x0
    dy = points[:, 1] - y0
    ego_x = cosine * dx + sine * dy
    ego_y = -sine * dx + cosine * dy
    centre_x = np.repeat(
        (120.0 - (np.arange(450) + 0.5) * 0.4)[:, None], 300, axis=1)
    centre_y = np.repeat(
        (60.0 - (np.arange(300) + 0.5) * 0.4)[None, :], 450, axis=0)
    distance = np.full((450, 300), np.inf)
    for index in range(len(points) - 1):
        ax, ay = ego_x[index], ego_y[index]
        vx, vy = ego_x[index + 1] - ax, ego_y[index + 1] - ay
        length_squared = vx * vx + vy * vy
        if length_squared <= 1e-12:
            fraction = 0.0
        else:
            fraction = np.clip(
                ((centre_x - ax) * vx + (centre_y - ay) * vy) / length_squared,
                0.0, 1.0)
        distance = np.minimum(
            distance,
            np.hypot(centre_x - (ax + fraction * vx), centre_y - (ay + fraction * vy)),
        )
    mask = (distance <= half_width_m) & (centre_x >= -rear_clip_m)
    decided = (np.abs(distance - half_width_m) > tie_m) & (
        np.abs(centre_x + rear_clip_m) > tie_m)
    return mask.astype(np.uint8), decided


def poses(kind: str):
    """Ego poses in the map frame: (x, y, yaw) covering yaw, bounds, edges."""
    if kind == "straight":
        return [
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.3),
            (10.0, 1.0, -0.35),
            (37.3, -2.1, 1.1),
            (60.0, 0.0, math.pi),
            (-25.0, 5.0, 0.0),
            (108.0, -9.0, 2.5),
            (0.0, 0.0, math.pi / 2.0),
            (-59.0, 0.0, 0.0),
            (0.0, 0.0, -math.pi),
        ]
    if kind == "l_junction":
        return [
            (0.0, 0.0, 0.0),
            (80.0, 0.0, 0.0),
            (95.0, 0.0, math.pi / 2.0),
            (100.0, 3.0, 1.2),
            (100.0, 30.0, math.pi / 2.0),
            (100.0, 55.0, -1.4),
            (20.0, 0.0, math.pi),
            (0.0, -8.0, 0.7),
        ]
    return [
        (0.0, 20.0, -math.pi / 2.0),
        (20.0, 0.0, 0.0),
        (14.14, 14.14, math.pi / 4.0),
        (-20.0, 0.0, math.pi),
        (0.0, 0.0, 0.0),
        (18.0, -12.0, 2.2),
        (5.0, 5.0, -2.6),
    ]


def dump(path: Path, navigation_map) -> Path:
    import nav_map_json

    nav_map_json.dump_map(path, navigation_map)
    return path
