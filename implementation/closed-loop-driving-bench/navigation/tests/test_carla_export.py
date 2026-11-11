"""The CARLA exporters, exercised against the fake CARLA API.

Nothing here runs on the bench as a test: it pins the conversion, the primitive
groups and the file formats, so the bench run only has to prove that CARLA's
real map has the same shape.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

import carla
import carla_frame
import carla_map_export
import nav_map_json
import route_from_carla

MAP_NAME = "Town10HD_Test"


@pytest.fixture()
def world():
    return carla.make_world()


# ------------------------------------------------------------------ frame math


def test_frame_conversion_negates_y_and_heading():
    assert carla_frame.carla_to_map_xy(3.0, 4.0) == (3.0, -4.0)
    assert carla_frame.carla_to_map_heading(math.pi / 2) == -math.pi / 2
    assert carla_frame.carla_to_map_heading_deg(90.0) == pytest.approx(
        -math.pi / 2
    )
    # A heading of +90 deg in CARLA points to +y (the driver's right); in the
    # map frame +y is the driver's left, so the heading is -90 deg.
    yaw = math.pi / 2
    direction_carla = (math.cos(yaw), math.sin(yaw))
    direction_map = (math.cos(-yaw), math.sin(-yaw))
    assert direction_map == pytest.approx(
        (direction_carla[0], -direction_carla[1])
    )


def test_right_vector_points_to_positive_y_at_zero_yaw():
    right = carla_frame.right_vector(0.0)
    assert right == pytest.approx((0.0, 1.0))
    right = carla_frame.right_vector(math.pi / 2)
    assert right == pytest.approx((-1.0, 0.0))


def test_lane_boundary_offsets_land_on_both_sides():
    centre = [(0.0, 0.0), (10.0, 0.0)]
    yaws = [0.0, 0.0]
    half = [1.75, 1.75]
    left = carla_frame.lane_boundary_points(centre, yaws, half, side="left")
    right = carla_frame.lane_boundary_points(centre, yaws, half, side="right")
    # CARLA left is -y, so the map frame (y negated) shows it at +1.75.
    assert left[0] == pytest.approx([0.0, 1.75, 0.0])
    assert right[0] == pytest.approx([0.0, -1.75, 0.0])


def test_convex_hull_drops_interior_points():
    points = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0], [2.0, 2.0],
              [2.0, 1.0]]
    hull = carla_map_export.convex_hull(points)
    assert len(hull) == 4
    assert [2.0, 2.0, 0.0] not in hull


# ------------------------------------------------------------------- exporter


def test_only_driving_lanes_are_exported():
    class Typed:
        def __init__(self, lane_type):
            self.lane_type = lane_type

    assert carla_map_export.is_drivable(Typed("LaneType.Driving")) is True
    assert carla_map_export.is_drivable(Typed("LaneType.Sidewalk")) is False
    assert carla_map_export.is_drivable(Typed("LaneType.Biking")) is False
    assert carla_map_export.is_drivable(carla.Waypoint(
        road_id=1, section_id=0, lane_id=1, s=0.0, x=0.0, y=0.0, yaw_deg=0.0
    )) is True


def test_export_map_primitive_groups(world, tmp_path):
    navigation_map = carla_map_export.export_map(world.get_map(), world=world)
    assert navigation_map.map_version == MAP_NAME
    assert navigation_map.provider == "carla"
    # Four lanes: two of road 1, two of road 2.
    assert len(navigation_map.lane_centerlines) == 4
    assert len(navigation_map.directed_lane_fields) == 4
    assert len(navigation_map.drivable_polygons) == 4
    # Eight lane sides, six polylines: the two lanes of each road share their
    # divider (road 1 at CARLA y=0, road 2 at x=100), which the exporter
    # de-duplicates.
    assert len(navigation_map.lane_boundaries) == 6
    assert len(navigation_map.intersection_polygons) == 1
    assert len(navigation_map.crosswalk_polygons) == 1
    assert len(navigation_map.stop_lines) == 1
    assert len(navigation_map.static_traffic_signals) == 1
    assert navigation_map.frame.frame_id == f"carla:{MAP_NAME}"
    assert navigation_map.layer_availability["road_level"] is False
    assert navigation_map.layer_availability["traffic_direction"] is True

    path = tmp_path / "map.json"
    digest = nav_map_json.dump_map(path, navigation_map)
    assert len(digest) == 64
    reloaded = nav_map_json.load_map(path)
    assert nav_map_json.map_to_payload(reloaded) == nav_map_json.map_to_payload(
        navigation_map
    )
    # The file is deterministic: writing twice gives the same bytes.
    first = path.read_bytes()
    nav_map_json.dump_map(path, navigation_map)
    assert path.read_bytes() == first


def test_exported_geometry_is_in_the_map_frame(world):
    navigation_map = carla_map_export.export_map(world.get_map(), world=world)
    # Road 1 lane 1 runs at CARLA y=-1.75, so map y=+1.75.
    lane = next(
        field for field in navigation_map.directed_lane_fields
        if field.lane_id.endswith("road1:sec0:lane1")
    )
    assert np.allclose(lane.centerline_enu_m[:, 1], 1.75)
    assert lane.centerline_enu_m[0, 0] == pytest.approx(0.0)
    assert lane.centerline_enu_m[-1, 0] == pytest.approx(100.0)
    # Road 2 lane 1 runs at CARLA x=98.25 heading +y: map x=98.25, y from 0 to
    # -100.
    turn = next(
        field for field in navigation_map.directed_lane_fields
        if field.lane_id.endswith("road2:sec0:lane1")
    )
    assert np.allclose(turn.centerline_enu_m[:, 0], 98.25)
    assert turn.centerline_enu_m[-1, 1] == pytest.approx(-100.0)

    # The drivable polygon of a lane spans its two boundaries, 3.5 m apart.
    polygon = next(
        item for item in navigation_map.drivable_polygons
        if item.primitive_id.endswith("road1:sec0:lane1:drivable")
    )
    ys = polygon.points_enu_m[:, 1]
    assert ys.max() - ys.min() == pytest.approx(3.5)

    bounds = navigation_map.bounds_enu_m
    assert bounds[0] < bounds[2] and bounds[1] < bounds[3]
    for primitive in navigation_map.lane_centerlines:
        assert np.isfinite(primitive.points_enu_m).all()
        assert primitive.points_enu_m[:, 0].min() >= bounds[0]
        assert primitive.points_enu_m[:, 0].max() <= bounds[2]


def test_export_map_matches_the_native_render(world, tmp_path, raster_cli,
                                              cli_runner):
    """Exported map -> JSON -> C++ -> native rasterizer: non-empty channels."""
    navigation_map = carla_map_export.export_map(world.get_map(), world=world)
    map_path = tmp_path / "map.json"
    nav_map_json.dump_map(map_path, navigation_map)
    route_path = tmp_path / "route.json"
    route_from_carla.main([
        "--start", "5,-1.75", "--end", "98.25,50",
        "--out", str(route_path), "--quiet",
    ])
    map_out = tmp_path / "map.f32"
    summary = cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", "5", "1.75", "0",
        "--map-out", str(map_out),
    )
    assert summary["map_valid"] is True
    assert summary["route_valid"] is True
    assert summary["corridor_pixels"] > 0
    assert summary["destination_pixels"] > 0
    raster = np.fromfile(map_out, dtype="<f4").reshape(14, 450, 300)
    assert raster[0].any()      # drivable area
    assert raster[1].any()      # lane boundary
    assert raster[2].any()      # lane centre line
    assert raster[9].any()      # traffic direction valid
    assert raster[10].any()     # known map area


def test_export_map_refuses_a_map_without_geometry():
    class EmptyMap:
        name = "Empty"

        def generate_waypoints(self, distance):
            return []

        def get_topology(self):
            return []

    with pytest.raises(ValueError):
        carla_map_export.export_map(EmptyMap())


def test_export_map_survives_a_missing_crosswalk_api(world):
    class NoCrosswalks:
        name = MAP_NAME

        def __init__(self, carla_map):
            self._map = carla_map

        def generate_waypoints(self, distance):
            return self._map.generate_waypoints(distance)

        def get_topology(self):
            return self._map.get_topology()

    navigation_map = carla_map_export.export_map(NoCrosswalks(world.get_map()))
    assert navigation_map.crosswalk_polygons == ()
    assert navigation_map.layer_availability["crosswalk"] is False


class _Crosswalks(carla.Map):
    """The fake scene with its crosswalks replaced by ``locations``."""

    def __init__(self, locations):
        super().__init__(MAP_NAME)
        self._locations = list(locations)

    def get_crosswalks(self):
        return list(self._locations)


def _closed(rings):
    # CARLA's Map.get_crosswalks: every crosswalk is a closed polygon, its first point repeated at its end.
    return [carla.Location(x, y) for ring in rings for (x, y) in list(ring) + [ring[0]]]


def test_crosswalks_are_read_as_closed_rings_of_any_size(world):
    # On Town10HD_Opt CARLA returned 16 rings of 5 points. Grouped by 4, they became 20 polygons that joined
    # corners of different crosswalks, up to 189 m long.
    rings = [
        [(10.0, -2.0), (14.0, -2.0), (14.0, 2.0), (10.0, 2.0)],
        [(30.0, -2.0), (34.0, -2.0), (34.0, 2.0), (30.0, 2.0)],
        [(50.0, -2.0), (54.0, -2.0), (55.0, 0.0), (54.0, 2.0), (50.0, 2.0)],
    ]
    navigation_map = carla_map_export.export_map(_Crosswalks(_closed(rings)), world=world)
    polygons = navigation_map.crosswalk_polygons
    assert len(polygons) == len(rings)
    for ring, polygon in zip(rings, polygons):
        expected = [carla_frame.carla_to_map_xy(x, y) for x, y in ring]
        assert np.allclose(np.asarray(polygon.points_enu_m)[:, :2], expected)


def test_a_crosswalk_run_that_never_closes_is_left_out(world):
    # Before, a point count that was no multiple of 4 gave one convex hull of every crosswalk of the map.
    ring = [(10.0, -2.0), (14.0, -2.0), (14.0, 2.0), (10.0, 2.0)]
    tail = [carla.Location(70.0, -2.0), carla.Location(74.0, -2.0), carla.Location(74.0, 2.0)]
    navigation_map = carla_map_export.export_map(_Crosswalks(_closed([ring]) + tail), world=world)
    assert len(navigation_map.crosswalk_polygons) == 1
    points = np.asarray(navigation_map.crosswalk_polygons[0].points_enu_m)
    assert points[:, 0].max() == pytest.approx(14.0)


class _TwoWayRoad(carla.Map):
    """One road with a lane each way, as CARLA gives it: s grows along the road's reference line in both
    lanes, and each waypoint faces its lane's driving direction (lane -1 along the reference line, lane +1
    against it, right-hand traffic)."""

    def _build(self):
        self._add_lane(5, 0, -1, (0.0, 1.75), (60.0, 1.75), 0.0)
        self._add_lane(5, 0, 1, (0.0, -1.75), (60.0, -1.75), 180.0)
        self._topology = []

    def get_crosswalks(self):
        return []


def test_directed_lane_fields_run_in_the_driving_direction():
    # On Town10HD_Opt every lane with a positive id ran against its traffic: the lanes were written in s order.
    navigation_map = carla_map_export.export_map(_TwoWayRoad(MAP_NAME))
    fields = {field.lane_id.rsplit(":", 1)[-1]: np.asarray(field.centerline_enu_m)
              for field in navigation_map.directed_lane_fields}
    assert fields["lane-1"][0, 0] == pytest.approx(0.0) and fields["lane-1"][-1, 0] == pytest.approx(60.0)
    assert fields["lane1"][0, 0] == pytest.approx(60.0) and fields["lane1"][-1, 0] == pytest.approx(0.0)
    centre = {item.primitive_id.rsplit(":", 2)[-2]: np.asarray(item.points_enu_m)
              for item in navigation_map.lane_centerlines}
    assert centre["lane1"][0, 0] == pytest.approx(60.0)
    # The two lanes share their left side, now in opposite orders; it is still drawn once.
    assert len(navigation_map.lane_boundaries) == 3


# ------------------------------------------------------------ lane joints

ROAD_10_M = 37.3
ROAD_11_SECTIONS_M = (0.0, 12.3, 13.9, 42.8)


class _ConsecutiveRoads(carla.Map):
    """Two roads end to end, as CARLA gives them with right-hand traffic: lane -1 drives along s, lane +1
    against it.  Road 10 runs from x=0 to 37.3 and road 11 on to 80.1 in three lane sections; the middle
    one (s 12.3 to 13.9 of road 11) lies between two sample positions, so generate_waypoints gives it
    none.  Neither road is a whole number of samples long, so each lane's samples stop short of its road's
    far end: the end of lane -1 and the start of lane +1."""

    def _build(self):
        self._add_lane(10, 0, -1, (0.0, 1.75), (ROAD_10_M, 1.75), 0.0)
        self._add_lane(10, 0, 1, (0.0, -1.75), (ROAD_10_M, -1.75), 180.0)
        sections = ROAD_11_SECTIONS_M
        for section, (s0, s1) in enumerate(zip(sections, sections[1:])):
            for lane_id, y, yaw in ((-1, 1.75, 0.0), (1, -1.75, 180.0)):
                self._add_lane(11, section, lane_id, (ROAD_10_M + s0, y), (ROAD_10_M + s1, y), yaw,
                               s_start=s0)
        self._successors = {
            (10, 0, -1): [(11, 0, -1)], (11, 0, -1): [(11, 1, -1)], (11, 1, -1): [(11, 2, -1)],
            (11, 2, 1): [(11, 1, 1)], (11, 1, 1): [(11, 0, 1)], (11, 0, 1): [(10, 0, 1)],
        }

    def get_crosswalks(self):
        return []


# Where each lane starts and ends in its driving direction (map x; map y is -1.75 for lane -1, +1.75 for
# lane +1).
JOINT_LANES = {
    "road10:sec0:lane-1": (0.0, 37.3),
    "road11:sec0:lane-1": (37.3, 49.6),
    "road11:sec1:lane-1": (49.6, 51.2),
    "road11:sec2:lane-1": (51.2, 80.1),
    "road11:sec2:lane1": (80.1, 51.2),
    "road11:sec1:lane1": (51.2, 49.6),
    "road11:sec0:lane1": (49.6, 37.3),
    "road10:sec0:lane1": (37.3, 0.0),
}


def test_the_fake_samples_lanes_short_of_their_ends_as_carla_does():
    # The fake must give the shortfall CARLA gives, or the joint tests below pass on the defect.
    carla_map = _ConsecutiveRoads(MAP_NAME)
    samples = {}
    for waypoint in carla_map.generate_waypoints(2.0):
        samples.setdefault((waypoint.road_id, waypoint.section_id, waypoint.lane_id), []).append(
            waypoint.transform.location.x)
    # Road 10 is sampled at s = 0, 2, ..., 36: lane -1 ends and lane +1 starts 1.3 m short of x=37.3.
    assert max(samples[(10, 0, -1)]) == pytest.approx(36.0)
    assert max(samples[(10, 0, 1)]) == pytest.approx(36.0)
    assert min(samples[(10, 0, -1)]) == pytest.approx(0.0, abs=1e-9)
    # Road 11's section 1 has no sample; section 2's samples stop 0.8 m short of x=80.1.
    assert (11, 1, -1) not in samples and (11, 1, 1) not in samples
    assert max(samples[(11, 2, -1)]) == pytest.approx(79.3)
    # get_topology: each lane at its start in its driving direction, with the start of its successor.
    pairs = {(entry.road_id, entry.section_id, entry.lane_id): (entry, exit_waypoint)
             for entry, exit_waypoint in carla_map.get_topology()}
    assert pairs[(10, 0, 1)][0].transform.location.x == pytest.approx(37.3)
    assert pairs[(10, 0, -1)][1].road_id == 11
    assert pairs[(10, 0, -1)][1].transform.location.x == pytest.approx(37.3)
    assert pairs[(11, 2, -1)][1].transform.location.x == pytest.approx(80.1)
    # next_until_lane_end ends where the road ends, in the lane itself.
    last = [w for w in carla_map.generate_waypoints(2.0) if (w.road_id, w.lane_id) == (10, -1)][-1]
    tail = last.next_until_lane_end(2.0)[-1]
    assert (tail.road_id, tail.section_id, tail.lane_id) == (10, 0, -1)
    assert tail.transform.location.x == pytest.approx(37.3)


def test_each_lane_runs_from_its_start_to_its_end():
    navigation_map = carla_map_export.export_map(_ConsecutiveRoads(MAP_NAME))
    fields = {field.lane_id.split(":", 2)[2]: np.asarray(field.centerline_enu_m)[:, :2]
              for field in navigation_map.directed_lane_fields}
    assert set(fields) == set(JOINT_LANES)
    for name, (first, last) in JOINT_LANES.items():
        line = fields[name]
        assert (line[0, 0], line[-1, 0]) == (pytest.approx(first, abs=1e-9),
                                             pytest.approx(last, abs=1e-9)), name
        assert np.allclose(line[:, 1], -1.75 if name.endswith("lane-1") else 1.75), name
    polygons = {item.primitive_id.split(":", 2)[2].rsplit(":", 1)[0]: np.asarray(item.points_enu_m)
                for item in navigation_map.drivable_polygons}
    for name, (first, last) in JOINT_LANES.items():
        xs = polygons[name][:, 0]
        assert (xs.min(), xs.max()) == (pytest.approx(min(first, last), abs=1e-9),
                                        pytest.approx(max(first, last), abs=1e-9)), name
    # A map whose lanes reach their ends says so: the first exports stopped them short.
    assert navigation_map.provenance["adapter_version"] == "carla_map_export_v2"


def test_consecutive_lanes_leave_no_gap_in_the_raster(raster_cli, cli_runner, tmp_path):
    navigation_map = carla_map_export.export_map(_ConsecutiveRoads(MAP_NAME))
    map_path = tmp_path / "map.json"
    nav_map_json.dump_map(map_path, navigation_map)
    for pose in ((20.0, 0.0, 0.0), (60.0, 0.5, math.pi - 0.3)):
        map_out = tmp_path / "map.f32"
        cli_runner(raster_cli, "--map", str(map_path),
                   "--pose", repr(pose[0]), repr(pose[1]), repr(pose[2]),
                   "--map-out", str(map_out))
        raster = np.fromfile(map_out, dtype="<f4").reshape(14, 450, 300)
        # The expectation does not come from the export: the two lanes, 3.5 m wide each, cover
        # x 0..80.1 and y -3.5..3.5 of the map without a break.
        ego_x = np.repeat((120.0 - (np.arange(450) + 0.5) * 0.4)[:, None], 300, axis=1)
        ego_y = np.repeat((60.0 - (np.arange(300) + 0.5) * 0.4)[None, :], 450, axis=0)
        cosine, sine = math.cos(pose[2]), math.sin(pose[2])
        x = pose[0] + cosine * ego_x - sine * ego_y
        y = pose[1] + sine * ego_x + cosine * ego_y
        road = (x > 0.0) & (x < ROAD_10_M + ROAD_11_SECTIONS_M[-1]) & (np.abs(y) < 3.5)
        decided = ((np.abs(x) > 1e-6) & (np.abs(x - 80.1) > 1e-6)
                   & (np.abs(np.abs(y) - 3.5) > 1e-6))
        drivable = raster[0] > 0.5
        holes = road & decided & ~drivable
        assert not holes.any(), (
            f"pose {pose}: {int(holes.sum())} road pixels not drivable, at map x "
            f"{sorted(set(np.round(x[holes], 1).tolist()))[:12]}")
        assert not (drivable & decided & ~road).any()
        # The lane centre lines (channel 2) and the traffic direction (channel 9) run through the
        # joints too: along each lane, every pixel within 0.3 m of its centre line is set.
        for lane_y in (-1.75, 1.75):
            near = (np.abs(y - lane_y) < 0.3) & (x > 0.5) & (x < 79.6)
            for channel in (2, 9):
                missing = near & (raster[channel] < 0.5)
                assert not missing.any(), (
                    f"pose {pose}: channel {channel} lane y={lane_y}: gaps at map x "
                    f"{sorted(set(np.round(x[missing], 1).tolist()))[:12]}")
        assert (raster[10][road & decided] == 1.0).all()


class _JunctionAfterRoad10(_ConsecutiveRoads):
    """Road 11 is a junction road, and next_until_lane_end of road 10's lane -1 ends on the first waypoint
    of road 11, as CARLA's does when the remaining length it computes exceeds the lane's own by a rounding
    step: it then returns the start of the successor."""

    def _build(self):
        super()._build()
        for key, piece in self._pieces.items():
            if key[0] == 11:
                piece.junction_from, piece.junction_id = 0.0, 9

    def next_until_lane_end(self, waypoint, distance):
        if (waypoint.road_id, waypoint.lane_id) == (10, -1):
            return [self._start_of(self._pieces[(11, 0, -1)])]
        return super().next_until_lane_end(waypoint, distance)


def test_a_lane_that_ends_where_a_junction_starts_is_not_part_of_it():
    navigation_map = carla_map_export.export_map(_JunctionAfterRoad10(MAP_NAME))
    (junction,) = navigation_map.intersection_polygons
    assert junction.primitive_id.endswith("junction9")
    xs = np.asarray(junction.points_enu_m)[:, 0]
    assert (xs.min(), xs.max()) == (pytest.approx(37.3), pytest.approx(80.1))
    lane = next(field for field in navigation_map.directed_lane_fields
                if field.lane_id.endswith("road10:sec0:lane-1"))
    assert np.asarray(lane.centerline_enu_m)[-1, 0] == pytest.approx(37.3)


# ---------------------------------------------------------------------- route


def test_route_file_schema_and_frame(tmp_path):
    out = tmp_path / "route.json"
    code = route_from_carla.main([
        "--start", "5,-1.75", "--end", "98.25,50",
        "--out", str(out), "--quiet",
    ])
    assert code == 0
    payload = json.loads(out.read_text())
    assert set(payload) == {"map", "waypoints", "destination"}
    assert payload["map"] == MAP_NAME
    rows = payload["waypoints"]
    assert len(rows) >= 2
    assert all(len(row) == 4 for row in rows)
    # Start and end, in the map frame: y negated.
    assert rows[0][0] == pytest.approx(5.0, abs=2.0)
    assert rows[0][1] == pytest.approx(1.75, abs=1e-6)
    assert rows[-1][0] == pytest.approx(98.25, abs=1e-6)
    assert rows[-1][1] == pytest.approx(-50.0, abs=2.0)
    assert payload["destination"] == pytest.approx([98.25, -50.0])

    # Heading: 0 along road 1, -pi/2 along road 2 (CARLA yaw 90 deg).
    straight = [row for row in rows if int(row[3]) == 1]
    turning = [row for row in rows if int(row[3]) == 2]
    assert straight and turning
    assert all(abs(row[2]) < 1e-9 for row in straight)
    assert all(row[2] == pytest.approx(-math.pi / 2) for row in turning)

    # The reader both languages share accepts it.
    loaded = nav_map_json.read_route_file(out)
    assert len(loaded["waypoints"]) == len(rows)


def test_route_segments_split_on_road_id(tmp_path):
    out = tmp_path / "route.json"
    route_from_carla.main([
        "--start", "5,-1.75", "--end", "98.25,50",
        "--out", str(out), "--quiet",
    ])
    route = nav_map_json.load_route(
        out, map_version=MAP_NAME, frame_id=f"carla:{MAP_NAME}"
    )
    assert route.valid is True
    assert len(route.lane_sequence) == 2
    assert [segment.provider_segment_id for segment in route.lane_sequence] == [
        "1", "2",
    ]


def test_route_from_spawn_points(tmp_path):
    out = tmp_path / "route.json"
    code = route_from_carla.main([
        "--start-spawn", "0", "--end-spawn", "1",
        "--out", str(out), "--quiet",
    ])
    assert code == 0
    payload = json.loads(out.read_text())
    assert payload["destination"] == pytest.approx([98.25, -50.0])


def test_route_file_rejects_a_bad_start():
    with pytest.raises(SystemExit):
        route_from_carla.main(["--start", "5", "--end", "1,2", "--out", "/tmp/x"])


def test_route_file_round_trip_renders(tmp_path, raster_cli, cli_runner):
    navigation_map = carla_map_export.export_map(carla.make_world().get_map())
    map_path = tmp_path / "map.json"
    nav_map_json.dump_map(map_path, navigation_map)
    route_path = tmp_path / "route.json"
    route_from_carla.main([
        "--start", "5,-1.75", "--end", "98.25,50",
        "--out", str(route_path), "--quiet",
    ])
    out = tmp_path / "route.u8"
    summary = cli_runner(
        raster_cli,
        "--map", str(map_path),
        "--route", str(route_path),
        "--pose", "20", "1.75", "0",
        "--route-out", str(out),
    )
    assert summary["route_valid"] is True
    assert summary["corridor_pixels"] > 0
    route_mask = np.fromfile(out, dtype=np.uint8).reshape(2, 450, 300)
    # The corridor reaches forward of the ego and is clipped behind it.
    rows_with_corridor = np.flatnonzero(route_mask[0].any(axis=1))
    assert rows_with_corridor.size > 0
    assert rows_with_corridor.max() <= 450
