"""The route corridor where the route changes road: continuous, as upstream's is.

A CARLA route changes road id where two lanes join, and GlobalRoutePlanner's
waypoints there are 2-4 m apart.  Upstream draws the corridor (route_mask
channel 0, 3.5 m wide) from the centre lines of its connected lane sequence,
whose lanelets share their end points, so the corridor has no break at a lane
joint.  The route readers (C++ ``ParseRouteJson`` and Python
``nav_map_json.load_route``) must therefore start each road run at the previous
run's last waypoint, and keep a road run of a single waypoint.

The expected corridors do not come from either reader: they are the route
drawn as one line through all waypoints, worked out from geometry
(``synthetic.expected_corridor``).
"""

from __future__ import annotations

import numpy as np
import pytest

import autoe2e_bridge
import nav_map_json
import synthetic

HEIGHT = 450
WIDTH = 300


def _cpp_corridor(raster_cli, cli_runner, tmp_path, rows, pose):
    map_path = synthetic.dump(tmp_path / "straight.map.json", synthetic.straight_road())
    route_path = synthetic.write_route_rows(tmp_path / "route.json", rows)
    route_out = tmp_path / "route.u8"
    summary = cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", repr(pose[0]), repr(pose[1]), repr(pose[2]),
        "--route-out", str(route_out),
    )
    assert summary["route_valid"] is True
    mask = np.fromfile(route_out, dtype=np.uint8).reshape(2, HEIGHT, WIDTH)
    return mask[0], summary


def _python_corridor(native_library, tmp_path, rows, pose):
    navigation_map = synthetic.straight_road()
    route_path = synthetic.write_route_rows(tmp_path / "route-py.json", rows)
    route = nav_map_json.load_route(
        route_path,
        map_version=navigation_map.map_version,
        frame_id=navigation_map.frame.frame_id,
    )
    rasterizer = autoe2e_bridge.rasterizer()
    engine = rasterizer.NativeNavigationRasterizer(
        autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY,
        library_path=str(native_library),
    )
    raster = engine.render(
        navigation_map,
        route,
        rasterizer.EgoPose(x_enu_m=pose[0], y_enu_m=pose[1], yaw_rad=pose[2],
                           timestamp_ns=0),
    )
    return raster.route_mask[0]


def _rows_of_ego_x(low_m, high_m):
    """Raster rows whose pixel centres lie strictly between two ego x values."""
    centres = 120.0 - (np.arange(HEIGHT) + 0.5) * 0.4
    return [int(row) for row in np.flatnonzero((centres > low_m) & (centres < high_m))]


def test_corridor_has_no_gap_where_the_road_changes(raster_cli, cli_runner, tmp_path):
    rows = synthetic.road_change_rows()
    # The ego at the middle of the 6 m joint between road 1 (x=20) and road 2 (x=26).
    pose = (23.0, 0.0, 0.0)
    corridor, _ = _cpp_corridor(raster_cli, cli_runner, tmp_path, rows, pose)
    joint_rows = _rows_of_ego_x(-2.9, 2.9)
    assert joint_rows == list(range(293, 307))
    empty = [row for row in joint_rows if not corridor[row].any()]
    assert empty == [], f"rows without a corridor pixel across the joint: {empty}"
    expected, decided = synthetic.expected_corridor(rows, pose)
    assert decided.sum() > HEIGHT * WIDTH - 10
    assert np.array_equal(corridor[decided], expected[decided])


def test_a_road_run_of_one_waypoint_is_kept(raster_cli, cli_runner, tmp_path):
    rows = synthetic.single_point_run_rows()
    pose = (24.0, 0.0, 0.0)
    corridor, _ = _cpp_corridor(raster_cli, cli_runner, tmp_path, rows, pose)
    # The waypoint of road 2, (24, 2.5), is 2.5 m left of the ego: column 143.
    assert corridor[299, 143] == 1 and corridor[300, 143] == 1
    expected, decided = synthetic.expected_corridor(rows, pose)
    assert np.array_equal(corridor[decided], expected[decided])


@pytest.mark.parametrize("name", ["road_change", "single_point_run"])
def test_python_reference_corridor_is_the_route_drawn_as_one_line(
    name, native_library, raster_cli, cli_runner, tmp_path
):
    rows = getattr(synthetic, f"{name}_rows")()
    pose = (23.0, 0.0, 0.0) if name == "road_change" else (24.0, 0.0, 0.0)
    reference = _python_corridor(native_library, tmp_path, rows, pose)
    expected, decided = synthetic.expected_corridor(rows, pose)
    assert np.array_equal(reference[decided], expected[decided])
    corridor, _ = _cpp_corridor(raster_cli, cli_runner, tmp_path, rows, pose)
    assert np.array_equal(corridor, reference)


def test_each_road_run_starts_at_the_previous_runs_last_waypoint(tmp_path):
    navigation_map = synthetic.straight_road()
    route = nav_map_json.load_route(
        synthetic.write_route_rows(tmp_path / "route.json", synthetic.single_point_run_rows()),
        map_version=navigation_map.map_version,
        frame_id=navigation_map.frame.frame_id,
    )
    segments = route.lane_sequence
    # The road ids name the segments as before; road 2 is kept although it has one waypoint.
    assert [segment.provider_segment_id for segment in segments] == ["1", "2", "3"]
    assert [segment.lane_id for segment in segments] == [
        "route:road1:0", "route:road2:1", "route:road3:2"]
    lines = [np.asarray(segment.centerline_enu_m)[:, :2] for segment in segments]
    assert np.allclose(lines[0][[0, -1]], [[0.0, 0.0], [20.0, 0.0]])
    assert np.allclose(lines[1], [[20.0, 0.0], [24.0, 2.5]])
    assert np.allclose(lines[2][[0, 1, -1]], [[24.0, 2.5], [28.0, 0.0], [60.0, 0.0]])
    for previous, current in zip(lines, lines[1:]):
        assert np.array_equal(current[0], previous[-1])


def test_a_first_road_run_of_one_waypoint_starts_the_next_run(tmp_path):
    # Two waypoints on two roads: the first run alone is no line (upstream needs two points),
    # so its waypoint begins the second run's line, and the route is valid.
    navigation_map = synthetic.straight_road()
    route = nav_map_json.load_route(
        synthetic.write_route_rows(tmp_path / "route.json",
                                   [[0.0, 0.0, 0.0, 7], [2.0, 0.0, 0.0, 8]]),
        map_version=navigation_map.map_version,
        frame_id=navigation_map.frame.frame_id,
    )
    assert route.valid is True
    assert [segment.provider_segment_id for segment in route.lane_sequence] == ["8"]
    assert np.allclose(np.asarray(route.lane_sequence[0].centerline_enu_m)[:, :2],
                       [[0.0, 0.0], [2.0, 0.0]])


def test_two_waypoints_on_two_roads_render_a_corridor(raster_cli, cli_runner, tmp_path):
    rows = [[22.0, 0.0, 0.0, 7], [24.0, 0.0, 0.0, 8]]
    corridor, summary = _cpp_corridor(raster_cli, cli_runner, tmp_path, rows, (23.0, 0.0, 0.0))
    assert summary["corridor_pixels"] > 0
    expected, decided = synthetic.expected_corridor(rows, (23.0, 0.0, 0.0))
    assert np.array_equal(corridor[decided], expected[decided])


def test_waypoints_counted_for_a16_are_those_of_the_road_runs(raster_cli, cli_runner, tmp_path):
    # ICD A16's waypointsInWindow counts the points of RouteData::centerlines (agent/cc/navigation_input.cpp),
    # and VC-DRIVING-007 recounts them from the route file with the same rule (case-evaluators/cases.py,
    # route_centre_line_points): each road run of two or more waypoints, once.  The corridor is drawn
    # from other lines, so drawing the joints must change neither count.
    rows = synthetic.single_point_run_rows()
    _, summary = _cpp_corridor(raster_cli, cli_runner, tmp_path, rows, (24.0, 0.0, 0.0))
    assert summary["route_centerline_points"] == 11 + 17
