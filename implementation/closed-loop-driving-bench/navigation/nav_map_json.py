"""The JSON form of AutoE2E's navigation map and route, shared by Python and C++.

Two artefacts cross the language boundary:

* **map JSON** -- the serialized upstream ``navigation.contracts.NavigationMap``
  (schema ``v1``): the same field names, the same primitive groups, points in
  the map frame as ``[x, y, z]`` triplets.  ``load_map`` rebuilds the exact
  upstream ``NavigationMap`` object, so the Python reference path and the C++
  library consume identical numbers.
* **route file** -- the ICD section 9 route file, unchanged:
  ``{"map": <name>, "waypoints": [[x, y, heading_rad, road_id], ...],
  "destination": [x, y]}``.  ``load_route`` turns it into the upstream
  ``NavigationRoute`` the reference rasterizer takes.

Frame: the map frame is right-handed, CARLA's y negated, heading measured
counter-clockwise from +x in radians.  See ``carla_map_export.py``.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import autoe2e_bridge

SCHEMA_VERSION = "v1"

MAP_SEQUENCE_FIELDS = (
    "drivable_polygons",
    "lane_boundaries",
    "lane_centerlines",
    "intersection_polygons",
    "crosswalk_polygons",
    "stop_lines",
    "static_traffic_signals",
    "directed_lane_fields",
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _value(value: Any) -> Any:
    """Plain JSON value of a contract object (same rule as upstream's)."""
    import dataclasses
    import enum

    if dataclasses.is_dataclass(value):
        return {
            field.name: _value(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Mapping):
        return {
            str(key): _value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return [_value(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def map_to_payload(navigation_map: Any) -> dict[str, Any]:
    """The deterministic JSON payload of a ``NavigationMap``."""
    return _value(navigation_map)


def dump_map(path: str | Path, navigation_map: Any) -> str:
    """Write the map JSON; returns its SHA-256."""
    payload = map_to_payload(navigation_map)
    text = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n", encoding="ascii")
    return sha256_file(target)


def _points(payload: Any, *, name: str, minimum: int) -> np.ndarray:
    array = np.asarray(payload, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] not in (2, 3):
        raise ValueError(f"{name}: expected [N,2] or [N,3], got {array.shape}")
    if array.shape[0] < minimum:
        raise ValueError(f"{name}: needs at least {minimum} points")
    if not np.isfinite(array).all():
        raise ValueError(f"{name}: non-finite coordinates")
    return array


def load_map(path: str | Path) -> Any:
    """Rebuild the upstream ``NavigationMap`` from its JSON form."""
    contracts = autoe2e_bridge.contracts()
    payload = json.loads(Path(path).read_text(encoding="ascii"))
    if not isinstance(payload, dict):
        raise ValueError("map JSON root must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported navigation map schema {payload.get('schema_version')!r}"
        )
    frame_payload = payload["frame"]
    frame = contracts.MapFrame(
        frame_id=str(frame_payload["frame_id"]),
        origin_latitude_deg=float(frame_payload["origin_latitude_deg"]),
        origin_longitude_deg=float(frame_payload["origin_longitude_deg"]),
        projection=str(frame_payload["projection"]),
    )

    def polygons(name: str):
        return tuple(
            contracts.PolygonPrimitive(
                primitive_id=str(item["primitive_id"]),
                points_enu_m=_points(
                    item["points_enu_m"], name=f"{name}.{item['primitive_id']}",
                    minimum=3,
                ),
                level=None if item.get("level") is None else int(item["level"]),
            )
            for item in payload.get(name, [])
        )

    def polylines(name: str):
        return tuple(
            contracts.PolylinePrimitive(
                primitive_id=str(item["primitive_id"]),
                points_enu_m=_points(
                    item["points_enu_m"], name=f"{name}.{item['primitive_id']}",
                    minimum=2,
                ),
                level=None if item.get("level") is None else int(item["level"]),
            )
            for item in payload.get(name, [])
        )

    signals = tuple(
        contracts.StaticTrafficSignal(
            signal_id=str(item["signal_id"]),
            position_enu_m=_points(
                [item["position_enu_m"]], name="signal", minimum=1
            )[0],
            level=None if item.get("level") is None else int(item["level"]),
        )
        for item in payload.get("static_traffic_signals", [])
    )
    directed = tuple(
        contracts.DirectedLaneField(
            lane_id=str(item["lane_id"]),
            centerline_enu_m=_points(
                item["centerline_enu_m"], name=f"lane.{item['lane_id']}",
                minimum=2,
            ),
            level=None if item.get("level") is None else int(item["level"]),
        )
        for item in payload.get("directed_lane_fields", [])
    )

    bounds = payload["bounds_enu_m"]
    return contracts.NavigationMap(
        map_version=str(payload["map_version"]),
        provider=str(payload["provider"]),
        frame=frame,
        bounds_enu_m=tuple(float(value) for value in bounds),
        drivable_polygons=polygons("drivable_polygons"),
        lane_boundaries=polylines("lane_boundaries"),
        lane_centerlines=polylines("lane_centerlines"),
        intersection_polygons=polygons("intersection_polygons"),
        crosswalk_polygons=polygons("crosswalk_polygons"),
        stop_lines=polylines("stop_lines"),
        static_traffic_signals=signals,
        directed_lane_fields=directed,
        layer_availability={
            str(key): bool(value)
            for key, value in payload.get("layer_availability", {}).items()
        },
        provenance=dict(payload.get("provenance", {})),
    )


# --------------------------------------------------------------------------- route

ROUTE_REQUIRED_KEYS = ("map", "waypoints", "destination")


def read_route_file(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("route file root must be an object")
    missing = [key for key in ROUTE_REQUIRED_KEYS if key not in payload]
    if missing:
        raise ValueError(f"route file misses keys: {', '.join(missing)}")
    waypoints = np.asarray(payload["waypoints"], dtype=np.float64)
    if waypoints.ndim != 2 or waypoints.shape[1] != 4:
        raise ValueError(
            "route waypoints must be [[x, y, heading_rad, road_id], ...]"
        )
    if not np.isfinite(waypoints).all():
        raise ValueError("route waypoints contain non-finite values")
    destination = np.asarray(payload["destination"], dtype=np.float64)
    if destination.shape != (2,) or not np.isfinite(destination).all():
        raise ValueError("route destination must be [x, y]")
    if not str(payload["map"]):
        raise ValueError("route map name must not be empty")
    payload["waypoints"] = waypoints
    payload["destination"] = destination
    return payload


def load_route(
    path: str | Path,
    *,
    map_version: str,
    frame_id: str,
    origin_latitude_deg: float = 0.0,
    origin_longitude_deg: float = 0.0,
    projection: str = "CARLA world frame, y negated (right-handed)",
) -> Any:
    """The upstream ``NavigationRoute`` of an ICD section 9 route file.

    ``valid`` follows upstream's rule: the route names the map's version and
    carries at least one lane segment.  A file with zero waypoints is the
    route provider's "no route corridor" case and yields an invalid route.
    """
    contracts = autoe2e_bridge.contracts()
    payload = read_route_file(path)
    waypoints = payload["waypoints"]
    frame = contracts.MapFrame(
        frame_id=frame_id,
        origin_latitude_deg=origin_latitude_deg,
        origin_longitude_deg=origin_longitude_deg,
        projection=projection,
    )
    segments = []
    if len(waypoints) >= 2:
        # One lane segment per run of constant road_id, the shape the
        # rasterizer packs as one centreline polyline per segment.  Each run
        # after the first starts at the previous run's last waypoint, so the
        # corridor has no break where the road changes, as upstream's lane
        # sequence has none (its lanelet centre lines share their end points).
        # A run of one waypoint therefore still makes a segment.  A first run
        # of one waypoint makes none (upstream needs two points): its waypoint
        # starts the next segment.  Each segment keeps its own run's road id.
        start = 0
        for index in range(1, len(waypoints) + 1):
            boundary = index == len(waypoints) or (
                index < len(waypoints)
                and int(waypoints[index][3]) != int(waypoints[start][3])
            )
            if not boundary:
                continue
            road = int(waypoints[start][3])
            run = waypoints[max(start - 1, 0):index]
            if len(run) >= 2:
                segments.append(
                    contracts.RouteLaneSegment(
                        lane_id=f"route:road{road}:{len(segments)}",
                        provider_segment_id=str(road),
                        centerline_enu_m=run[:, :2],
                        level=None,
                    )
                )
            start = index
    valid = bool(len(waypoints) >= 2 and str(payload["map"]) == map_version)
    quality = contracts.RouteQuality(
        matched_pose_ratio=1.0 if valid else 0.0,
        median_lateral_distance_m=0.0,
        p95_lateral_distance_m=0.0,
        median_heading_error_rad=0.0,
        p95_heading_error_rad=0.0,
        failure_reasons=() if valid else ("no_route",),
    )
    provenance = contracts.RouteProvenance(
        source_revision="carla:GlobalRoutePlanner",
        matcher_version="carla_route_v1",
        matcher_config_sha256=sha256_file(path),
        map_sha256="none",
        trace_sha256="none",
    )
    return contracts.NavigationRoute(
        route_id=f"carla-route:{payload['map']}",
        revision=1,
        provider="carla",
        timestamp_ns=0,
        valid_from_ns=0,
        map_version=str(payload["map"]),
        frame=frame,
        lane_sequence=tuple(segments) if valid else (),
        destination=contracts.Destination(payload["destination"], "route_file"),
        confidence=1.0 if valid else 0.0,
        valid=valid,
        quality=quality,
        estimated_destination=False,
        provenance=provenance,
    )


def route_corridor_point_count(path: str | Path) -> int:
    """``corridorPoints`` of a route file: its waypoint count."""
    return int(len(read_route_file(path)["waypoints"]))


def route_sha256(path: str | Path) -> str:
    return sha256_file(path)


def metres_per_pixel_geometry():
    """The geometry the checkpoint is pinned to (upstream's constant)."""
    return autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY


def geometry_contract() -> dict[str, Any]:
    return metres_per_pixel_geometry().contract()


def yaw_normalise(angle: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    return math.atan2(math.sin(angle), math.cos(angle))
