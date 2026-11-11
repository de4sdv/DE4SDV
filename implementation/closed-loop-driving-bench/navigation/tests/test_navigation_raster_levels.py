"""Parity for the road-level channels (11-13) on a level-carrying map.

The real CARLA export has no road levels, so ``ROAD_LEVEL``,
``ROAD_LEVEL_VALID`` and ``OVERLAPPING_LEVEL_AMBIGUITY`` stay zero there.  This
test builds a map whose overlapping primitives carry different levels, so the
level writes and the ambiguity flag are exercised, and checks the optimised
path against the reference path and upstream's renderer bit for bit.
"""

from __future__ import annotations

import numpy as np
import pytest

import autoe2e_bridge
import nav_map_json

MAP_CHANNELS = autoe2e_bridge.geometry().MAP_CHANNEL_COUNT
ROUTE_CHANNELS = autoe2e_bridge.geometry().ROUTE_CHANNEL_COUNT
HEIGHT = 450
WIDTH = 300

ROAD_LEVEL = autoe2e_bridge.geometry().MapChannel.ROAD_LEVEL
ROAD_LEVEL_VALID = autoe2e_bridge.geometry().MapChannel.ROAD_LEVEL_VALID
AMBIGUITY = autoe2e_bridge.geometry().MapChannel.OVERLAPPING_LEVEL_AMBIGUITY

POSES = [
    (0.0, 0.0, 0.0),
    (5.0, -2.0, 0.4),
    (-8.0, 3.0, -1.1),
    (12.0, 1.0, 2.7),
    (0.0, 0.0, 3.141592653589793),
]


def _levels_map():
    """Two overlapping areas, one lane line, all carrying road levels."""
    contracts = autoe2e_bridge.contracts()
    frame = contracts.MapFrame(
        frame_id="synthetic:levels",
        origin_latitude_deg=0.0,
        origin_longitude_deg=0.0,
        projection="synthetic right-handed metric frame",
    )

    def rect(x0, y0, x1, y1):
        return np.asarray(
            [[x0, y0, 0.0], [x1, y0, 0.0], [x1, y1, 0.0], [x0, y1, 0.0]]
        )

    def line(points):
        return np.asarray([[x, y, 0.0] for x, y in points], dtype=np.float64)

    return contracts.NavigationMap(
        map_version="Town10HD_Levels",
        provider="synthetic",
        frame=frame,
        bounds_enu_m=(-30.0, -30.0, 40.0, 30.0),
        drivable_polygons=(
            contracts.PolygonPrimitive("lower", rect(-20.0, -12.0, 30.0, 4.0),
                                       level=0),
            contracts.PolygonPrimitive("upper", rect(-20.0, -4.0, 30.0, 12.0),
                                       level=1),
            contracts.PolygonPrimitive("ramp", rect(-20.0, 2.0, 30.0, 8.0),
                                       level=-3),
            contracts.PolygonPrimitive("clamped", rect(-20.0, 6.0, 30.0, 11.0),
                                       level=40),
        ),
        lane_boundaries=(
            contracts.PolylinePrimitive(
                "kerb", line([(-20.0, -12.0), (30.0, -12.0)]), level=1
            ),
        ),
        lane_centerlines=(
            contracts.PolylinePrimitive(
                "centre", line([(-20.0, -6.0), (30.0, -6.0)]), level=-3
            ),
        ),
        intersection_polygons=(),
        crosswalk_polygons=(),
        stop_lines=(),
        static_traffic_signals=(),
        directed_lane_fields=(),
        layer_availability={"road_level": True},
        provenance={"fixture": "levels"},
    )


@pytest.mark.parametrize("pose", POSES)
def test_level_channels_match_reference(
    pose, tmp_path, native_library, raster_cli, cli_runner
):
    navigation_map = _levels_map()
    map_path = tmp_path / "levels.map.json"
    nav_map_json.dump_map(map_path, navigation_map)

    rasterizer_module = autoe2e_bridge.rasterizer()
    geometry = autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY
    engine = rasterizer_module.NativeNavigationRasterizer(
        geometry, library_path=str(native_library)
    )
    reference = engine.render(
        navigation_map,
        None,
        rasterizer_module.EgoPose(
            x_enu_m=pose[0], y_enu_m=pose[1], yaw_rad=pose[2], timestamp_ns=0
        ),
    )

    map_out = tmp_path / "map.f32"
    route_out = tmp_path / "route.u8"
    cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--pose", repr(pose[0]), repr(pose[1]), repr(pose[2]),
        "--map-out", str(map_out),
        "--route-out", str(route_out),
    )
    cpp_map = np.fromfile(map_out, dtype="<f4").reshape(MAP_CHANNELS, HEIGHT, WIDTH)
    cpp_route = np.fromfile(route_out, dtype=np.uint8).reshape(
        ROUTE_CHANNELS, HEIGHT, WIDTH
    )

    assert np.array_equal(cpp_map, reference.map_context), (
        f"pose {pose}: max abs diff per channel = "
        f"{[float(np.abs(cpp_map[c].astype(np.float64) - reference.map_context[c]).max()) for c in range(MAP_CHANNELS)]}"
    )
    assert np.array_equal(cpp_route, reference.route_mask)
    # The fixture must actually exercise the level channels.
    assert cpp_map[ROAD_LEVEL].any()
    assert cpp_map[ROAD_LEVEL_VALID].any()
    assert cpp_map[AMBIGUITY].any()
