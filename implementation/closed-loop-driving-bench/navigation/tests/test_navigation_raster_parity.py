"""Bit-exact parity: C++ navigation_raster vs upstream's Python path.

For every synthetic map (straight road, L junction, roundabout arc), every ego
pose and with/without a route, upstream
``navigation.rasterizer.NativeNavigationRasterizer.render`` and the C++ library
must produce identical rasters -- zero difference per channel.  The C++ library
packs the same primitives, culls them to the pose's window and rasterizes them
itself, so these fixtures (including the concave ring polygon and the direction
channels) are the regression net for that rasterizer.

The comparison is a byte comparison of the arrays (float32 bit patterns and
uint8 pixels), not an approximate one.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

import autoe2e_bridge
import nav_map_json
import synthetic

MAP_CHANNELS = autoe2e_bridge.geometry().MAP_CHANNEL_COUNT
ROUTE_CHANNELS = autoe2e_bridge.geometry().ROUTE_CHANNEL_COUNT
HEIGHT = autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY.height_px
WIDTH = autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY.width_px

CASE_IDS = [
    (kind, index)
    for kind in synthetic.MAPS
    for index in range(len(synthetic.poses(kind)))
]


def _reference_rasterizer(native_library: Path):
    rasterizer_module = autoe2e_bridge.rasterizer()
    geometry = autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY
    return rasterizer_module.NativeNavigationRasterizer(
        geometry, library_path=str(native_library)
    )


def _prepare(tmp_path: Path, kind: str, *, with_route: bool):
    navigation_map = synthetic.MAPS[kind]()
    map_path = synthetic.dump(tmp_path / f"{kind}.map.json", navigation_map)
    route_path = None
    route_object = None
    if with_route:
        route_path = synthetic.write_route(tmp_path / f"{kind}.route.json", kind)
        route_object = nav_map_json.load_route(
            route_path,
            map_version=navigation_map.map_version,
            frame_id=navigation_map.frame.frame_id,
        )
    return navigation_map, map_path, route_path, route_object


@pytest.mark.parametrize("kind,pose_index", CASE_IDS,
                         ids=[f"{kind}-pose{index}" for kind, index in CASE_IDS])
def test_render_matches_upstream(
    kind, pose_index, tmp_path, native_library, raster_cli, cli_runner
):
    navigation_map, map_path, route_path, route_object = _prepare(
        tmp_path, kind, with_route=True
    )
    x, y, yaw = synthetic.poses(kind)[pose_index]

    reference = _reference_rasterizer(native_library).render(
        navigation_map,
        route_object,
        autoe2e_bridge.rasterizer().EgoPose(
            x_enu_m=x, y_enu_m=y, yaw_rad=yaw, timestamp_ns=0
        ),
    )
    map_out = tmp_path / "map.f32"
    route_out = tmp_path / "route.u8"
    summary = cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", repr(x), repr(y), repr(yaw),
        "--map-out", str(map_out),
        "--route-out", str(route_out),
    )

    cpp_map = np.fromfile(map_out, dtype="<f4").reshape(MAP_CHANNELS, HEIGHT, WIDTH)
    cpp_route = np.fromfile(route_out, dtype=np.uint8).reshape(
        ROUTE_CHANNELS, HEIGHT, WIDTH
    )

    assert cpp_map.shape == reference.map_context.shape
    assert cpp_route.shape == reference.route_mask.shape
    assert summary["map_valid"] is True
    assert summary["route_valid"] is True

    map_diff = np.abs(
        cpp_map.astype(np.float64) - reference.map_context.astype(np.float64)
    )
    per_channel = [float(map_diff[channel].max()) for channel in range(MAP_CHANNELS)]
    mismatched_map = int((cpp_map != reference.map_context).sum())
    mismatched_route = int((cpp_route != reference.route_mask).sum())

    assert mismatched_map == 0, (
        f"{kind} pose {pose_index}: {mismatched_map} map pixels differ; "
        f"max abs difference per channel = {per_channel}"
    )
    assert mismatched_route == 0, (
        f"{kind} pose {pose_index}: {mismatched_route} route pixels differ"
    )
    assert max(per_channel) == 0.0


@pytest.mark.parametrize("kind,pose_index", CASE_IDS,
                         ids=[f"{kind}-pose{index}" for kind, index in CASE_IDS])
def test_corridor_is_the_route_drawn_as_one_line(
    kind, pose_index, tmp_path, native_library, raster_cli, cli_runner
):
    """An expectation that does not come from the route reader.

    The parity test above compares two paths fed the same centre lines, so both
    agree on whatever the reader makes of a road change.  Here the corridor of
    both paths is held against the route drawn as one line through all its
    waypoints, worked out from geometry: the L junction's route changes road
    across a 10 m joint, wider than the 3.5 m corridor.
    """
    navigation_map, map_path, route_path, route_object = _prepare(
        tmp_path, kind, with_route=True
    )
    pose = synthetic.poses(kind)[pose_index]
    expected, decided = synthetic.expected_corridor(synthetic.route_waypoints(kind), pose)
    reference = _reference_rasterizer(native_library).render(
        navigation_map,
        route_object,
        autoe2e_bridge.rasterizer().EgoPose(
            x_enu_m=pose[0], y_enu_m=pose[1], yaw_rad=pose[2], timestamp_ns=0
        ),
    )
    route_out = tmp_path / "route.u8"
    cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", repr(pose[0]), repr(pose[1]), repr(pose[2]),
        "--route-out", str(route_out),
    )
    cpp_corridor = np.fromfile(route_out, dtype=np.uint8).reshape(
        ROUTE_CHANNELS, HEIGHT, WIDTH
    )[0]
    assert decided.sum() > HEIGHT * WIDTH - 10
    for name, corridor in (("upstream", reference.route_mask[0]), ("C++", cpp_corridor)):
        wrong = int((corridor[decided] != expected[decided]).sum())
        assert wrong == 0, f"{kind} pose {pose_index}: {name} corridor differs in {wrong} pixels"


@pytest.mark.parametrize("kind", list(synthetic.MAPS))
def test_render_without_route_matches_upstream(
    kind, tmp_path, native_library, raster_cli, cli_runner
):
    """No route file: the map is rendered, the route raster stays zero."""
    navigation_map, map_path, _, _ = _prepare(tmp_path, kind, with_route=False)
    x, y, yaw = synthetic.poses(kind)[0]
    reference = _reference_rasterizer(native_library).render(
        navigation_map,
        None,
        autoe2e_bridge.rasterizer().EgoPose(
            x_enu_m=x, y_enu_m=y, yaw_rad=yaw, timestamp_ns=0
        ),
    )
    map_out = tmp_path / "map.f32"
    route_out = tmp_path / "route.u8"
    summary = cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--pose", repr(x), repr(y), repr(yaw),
        "--map-out", str(map_out),
        "--route-out", str(route_out),
    )
    cpp_map = np.fromfile(map_out, dtype="<f4").reshape(MAP_CHANNELS, HEIGHT, WIDTH)
    cpp_route = np.fromfile(route_out, dtype=np.uint8).reshape(
        ROUTE_CHANNELS, HEIGHT, WIDTH
    )
    assert np.array_equal(cpp_map, reference.map_context)
    assert np.array_equal(cpp_route, reference.route_mask)
    assert not cpp_route.any()
    assert summary["route_valid"] is False


@pytest.mark.parametrize("kind", list(synthetic.MAPS))
def test_route_of_another_map_renders_zero_corridor(
    kind, tmp_path, raster_cli, cli_runner
):
    """A route naming another map is not used, exactly as upstream decides."""
    navigation_map, map_path, route_path, _ = _prepare(tmp_path, kind, with_route=True)
    payload = json.loads(route_path.read_text())
    payload["map"] = "SomeOtherMap"
    route_path.write_text(json.dumps(payload))
    x, y, yaw = synthetic.poses(kind)[0]
    summary = cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", repr(x), repr(y), repr(yaw),
        "--route-out", str(tmp_path / "route.u8"),
    )
    assert summary["route_valid"] is False
    assert summary["corridor_pixels"] == 0
    assert summary["destination_pixels"] == 0


def test_channels_are_exercised(tmp_path, native_library, raster_cli, cli_runner):
    """The fixtures really fill the channels they claim to (no silent zeros)."""
    _, map_path, route_path, _ = _prepare(tmp_path, "l_junction", with_route=True)
    x, y, yaw = 85.0, 0.0, 0.0
    map_out = tmp_path / "map.f32"
    route_out = tmp_path / "route.u8"
    cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", repr(x), repr(y), repr(yaw),
        "--map-out", str(map_out),
        "--route-out", str(route_out),
    )
    map_context = np.fromfile(map_out, dtype="<f4").reshape(MAP_CHANNELS, HEIGHT, WIDTH)
    route_mask = np.fromfile(route_out, dtype=np.uint8).reshape(
        ROUTE_CHANNELS, HEIGHT, WIDTH
    )
    names = [channel.name for channel in autoe2e_bridge.geometry().MapChannel]
    non_empty = {
        names[channel]: float(map_context[channel].sum())
        for channel in range(MAP_CHANNELS)
        if map_context[channel].any()
    }
    assert set(non_empty) == {
        "DRIVABLE_AREA",
        "LANE_BOUNDARY",
        "LANE_CENTERLINE",
        "INTERSECTION",
        "CROSSWALK",
        "STOP_LINE",
        "STATIC_TRAFFIC_SIGNAL",
        "TRAFFIC_DIRECTION_SIN",
        "TRAFFIC_DIRECTION_COS",
        "TRAFFIC_DIRECTION_VALID",
        "KNOWN_MAP_AREA",
    }
    # Road level channels stay zero: the map has no levels.
    assert not map_context[autoe2e_bridge.geometry().MapChannel.ROAD_LEVEL].any()
    assert not map_context[
        autoe2e_bridge.geometry().MapChannel.ROAD_LEVEL_VALID
    ].any()
    assert not map_context[
        autoe2e_bridge.geometry().MapChannel.OVERLAPPING_LEVEL_AMBIGUITY
    ].any()
    assert route_mask[0].any()
    assert route_mask[1].any()


def test_map_json_round_trips_through_python(tmp_path):
    """The exported JSON rebuilds the same contract object upstream renders."""
    for kind, factory in synthetic.MAPS.items():
        navigation_map = factory()
        path = synthetic.dump(tmp_path / f"{kind}.json", navigation_map)
        reloaded = nav_map_json.load_map(path)
        assert nav_map_json.map_to_payload(reloaded) == nav_map_json.map_to_payload(
            navigation_map
        )


def test_geometry_contract_is_the_pinned_one():
    geometry = autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY
    assert geometry.geometry_id == "autoe2e-bev-450x300-0p4m-v1"
    assert (geometry.height_px, geometry.width_px) == (450, 300)
    assert geometry.meters_per_pixel == 0.4
    assert (geometry.x_min_m, geometry.x_max_m) == (-60.0, 120.0)
    assert (geometry.y_min_m, geometry.y_max_m) == (-60.0, 60.0)
    assert (geometry.route_corridor_width_m, geometry.destination_marker_radius_m,
            geometry.route_rear_clip_m) == (3.5, 2.0, 10.0)
    assert math.isclose(HEIGHT * geometry.meters_per_pixel, 180.0)
