"""Focused tests for the pure 009C scenario contract."""

from __future__ import annotations

import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from de4sdv_aebs_009c_bench.scenario_contract import (  # noqa: E402
    BASELINE_REQUIRED_INPUTS,
    REQUIRED_NON_CLAIMS,
    BaselineContract,
    ClockContract,
    FixtureConstraints,
    ObstacleGeometry,
    Outcome,
    Point3D,
    Pose2D,
    ScenarioConfig,
    anchor_target_pose_map,
    load_scenario_config,
    map_pose_to_base_link,
    rectangular_obstacle_points,
)


class OutcomeTests(unittest.TestCase):
    def test_outcome_vocabulary_is_closed(self) -> None:
        self.assertEqual(
            {outcome.value for outcome in Outcome},
            {
                "pass_observed_chain",
                "fail_scenario",
                "inconclusive_precondition",
                "inconclusive_instrumentation",
                "aborted",
            },
        )
        with self.assertRaises(ValueError):
            Outcome("unknown")


class PoseTransformTests(unittest.TestCase):
    def test_target_is_anchored_once_from_live_ego_pose_then_transformed_back(self) -> None:
        ego_at_injection = Pose2D(x=12.0, y=5.0, yaw_rad=math.pi / 2.0)
        target_in_base = Pose2D(x=6.0, y=0.5, yaw_rad=0.0)

        target_map = anchor_target_pose_map(target_in_base, ego_at_injection)

        self.assertAlmostEqual(target_map.x, 11.5)
        self.assertAlmostEqual(target_map.y, 11.0)
        self.assertAlmostEqual(target_map.yaw_rad, math.pi / 2.0)
        target_back_in_base = map_pose_to_base_link(target_map, ego_at_injection)
        self.assertAlmostEqual(target_back_in_base.x, target_in_base.x)
        self.assertAlmostEqual(target_back_in_base.y, target_in_base.y)
        self.assertAlmostEqual(target_back_in_base.yaw_rad, target_in_base.yaw_rad)

    def test_fixed_map_pose_is_transformed_with_inverse_ego_yaw(self) -> None:
        target_map = Pose2D(x=12.0, y=7.0, yaw_rad=1.75)
        ego_map = Pose2D(x=10.0, y=5.0, yaw_rad=1.5707963267948966)

        target_base = map_pose_to_base_link(target_map, ego_map)

        self.assertAlmostEqual(target_base.x, 2.0)
        self.assertAlmostEqual(target_base.y, -2.0)
        self.assertAlmostEqual(target_base.yaw_rad, 0.17920367320510344)

    def test_pose_is_immutable_and_rejects_non_finite_or_bool_values(self) -> None:
        pose = Pose2D(1.0, 2.0, 0.0)
        with self.assertRaises((AttributeError, TypeError)):
            pose.x = 3.0  # type: ignore[misc]
        for bad in (float("nan"), float("inf"), True, "1"):
            with self.subTest(bad=bad), self.assertRaises((TypeError, ValueError)):
                Pose2D(bad, 0.0, 0.0)  # type: ignore[arg-type]


class ObstacleGeometryTests(unittest.TestCase):
    def test_cluster_is_deterministic_dense_connected_and_tall(self) -> None:
        geometry = ObstacleGeometry(
            length_m=1.0,
            width_m=0.8,
            height_m=0.6,
            point_spacing_m=0.05,
            voxel_size_x_m=0.1,
            voxel_size_y_m=0.1,
            voxel_size_z_m=0.5,
            cluster_tolerance_m=0.15,
            cluster_minimum_height_m=0.1,
            minimum_cluster_size=10,
        )
        pose = Pose2D(8.0, -1.0, 0.25)

        points = rectangular_obstacle_points(pose, geometry)

        self.assertEqual(points, rectangular_obstacle_points(pose, geometry))
        self.assertTrue(all(isinstance(point, Point3D) for point in points))
        voxel_bins: dict[tuple[int, int, int], list[Point3D]] = {}
        for point in points:
            key = (
                math.floor(point.x / geometry.voxel_size_x_m),
                math.floor(point.y / geometry.voxel_size_y_m),
                math.floor(point.z / geometry.voxel_size_z_m),
            )
            voxel_bins.setdefault(key, []).append(point)
        self.assertGreater(len(voxel_bins), geometry.minimum_cluster_size)
        centroids = tuple(
            Point3D(
                sum(point.x for point in voxel) / len(voxel),
                sum(point.y for point in voxel) / len(voxel),
                sum(point.z for point in voxel) / len(voxel),
            )
            for voxel in voxel_bins.values()
        )
        unvisited = set(range(len(centroids)))
        components: list[set[int]] = []
        while unvisited:
            seed = unvisited.pop()
            reached = {seed}
            frontier = [seed]
            while frontier:
                current = frontier.pop()
                origin = centroids[current]
                for candidate in tuple(unvisited):
                    point = centroids[candidate]
                    if math.dist(
                        (origin.x, origin.y, origin.z), (point.x, point.y, point.z)
                    ) <= geometry.cluster_tolerance_m:
                        unvisited.remove(candidate)
                        reached.add(candidate)
                        frontier.append(candidate)
            components.append(reached)
        viable = [
            component
            for component in components
            if len(component) > geometry.minimum_cluster_size
            and max(centroids[index].z for index in component)
            > geometry.cluster_minimum_height_m
        ]
        self.assertTrue(viable)
        for first, second in zip(points, points[1:]):
            distance = (
                (first.x - second.x) ** 2
                + (first.y - second.y) ** 2
                + (first.z - second.z) ** 2
            ) ** 0.5
            self.assertLessEqual(distance, geometry.cluster_tolerance_m)

    def test_geometry_rejects_unsafe_sampling_inputs(self) -> None:
        valid = {
            "length_m": 1.0,
            "width_m": 0.8,
            "height_m": 0.6,
            "point_spacing_m": 0.05,
            "voxel_size_x_m": 0.1,
            "voxel_size_y_m": 0.1,
            "voxel_size_z_m": 0.5,
            "cluster_tolerance_m": 0.15,
            "cluster_minimum_height_m": 0.1,
            "minimum_cluster_size": 10,
        }
        invalid = (
            {"height_m": 0.1},
            {"length_m": 0.1},
            {"width_m": 0.1},
            {"point_spacing_m": 0.11},
            {"point_spacing_m": 0.0},
            {"cluster_tolerance_m": 0.04},
            {"voxel_size_x_m": float("nan")},
            {"minimum_cluster_size": 0},
            {"width_m": "0.8"},
        )
        for override in invalid:
            with self.subTest(override=override), self.assertRaises((TypeError, ValueError)):
                ObstacleGeometry(**(valid | override))  # type: ignore[arg-type]


class ScenarioConfigurationTests(unittest.TestCase):
    CONFIG_PATH = PACKAGE_ROOT.parents[1] / "config" / "scenario-009c-aeb-mrm.yaml"

    def test_fixture_loads_as_an_immutable_complete_contract(self) -> None:
        config = load_scenario_config(self.CONFIG_PATH)

        self.assertIsInstance(config, ScenarioConfig)
        self.assertEqual(config.scenario_id, "SCN-AEBS-009C-AEB-MRM-001")
        self.assertEqual(config.initial_pose_map, Pose2D(0.0, 0.0, 0.0))
        self.assertEqual(config.nominal_command_speed_mps, 5.0)
        self.assertEqual(config.nominal_command_acceleration_mps2, 1.0)
        self.assertEqual(config.target_injection_pose_base_link, Pose2D(6.0, 0.0, 0.0))
        self.assertEqual(config.geometry.voxel_size_x_m, 0.1)
        self.assertEqual(config.geometry.voxel_size_z_m, 0.5)
        self.assertEqual(config.geometry.cluster_tolerance_m, 0.15)
        self.assertEqual(config.geometry.minimum_cluster_size, 10)
        self.assertEqual(
            config.fixture_constraints,
            FixtureConstraints(imu_path_horizon_s=1.5, imu_path_max_length_m=10.0),
        )
        self.assertLess(
            config.target_injection_pose_base_link.x + config.geometry.length_m / 2.0,
            config.fixture_constraints.imu_path_max_length_m,
        )
        self.assertEqual(
            config.baseline,
            BaselineContract(
                stable_duration_s=2.0,
                ego_speed_min_mps=0.1,
                required_input_max_age_s=0.5,
            ),
        )
        self.assertEqual(
            config.baseline.diagnostic_joined_key,
            "autonomous_emergency_braking: aeb_emergency_stop",
        )
        self.assertEqual(config.baseline.required_inputs, BASELINE_REQUIRED_INPUTS)
        self.assertEqual(
            config.clocks,
            ClockContract(
                source_stamp="ros_message_header_when_available",
                receipt_time="collector_monotonic",
                host_utc="optional",
                causal_order="collector_monotonic_within_one_collector",
                cross_domain_comparison="forbidden_without_explicit_rule",
            ),
        )
        self.assertGreater(config.pointcloud_rate_hz, 0.0)
        self.assertGreater(config.ego_state_rate_hz, 0.0)
        self.assertGreater(config.startup_timeout_s, 0.0)
        self.assertGreater(config.scenario_timeout_s, config.startup_timeout_s)
        self.assertEqual(set(config.allowed_outcomes), set(Outcome))
        self.assertEqual(config.non_claims, REQUIRED_NON_CLAIMS)
        with self.assertRaises((AttributeError, TypeError)):
            config.nominal_command_speed_mps = 2.0  # type: ignore[misc]

    def test_mapping_validation_rejects_malformed_contracts(self) -> None:
        mutations = (
            lambda data: data.update(scenario_id="SCN-WRONG"),
            lambda data: data["nominal_control"].update(speed_mps=0.1),
            lambda data: data["nominal_control"].update(speed_mps=True),
            lambda data: data["nominal_control"].update(speed_mps=float("inf")),
            lambda data: data["publication"].update(pointcloud_rate_hz=0),
            lambda data: data["publication"].update(ego_state_rate_hz=float("nan")),
            lambda data: data["timeouts"].update(scenario_s=0),
            lambda data: data["timeouts"].update(startup_s=30.0),
            lambda data: data["target"].update(stationary=False),
            lambda data: data["target"]["injection_pose_base_link"].update(y=5.0),
            lambda data: data["target"]["injection_pose_base_link"].update(yaw_rad=0.2),
            lambda data: data["target"]["geometry"].update(height_m=0.1),
            lambda data: data["target"]["geometry"].update(height_m=0.11),
            lambda data: data["target"]["geometry"].update(length_m=0.11, width_m=0.11),
            lambda data: data["target"]["geometry"].update(voxel_size_x_m=0.2),
            lambda data: data["target"]["geometry"].update(minimum_cluster_size=11),
            lambda data: data["clocks"].update(cross_domain_comparison="allowed"),
            lambda data: data["baseline"].update(stable_duration_s=0.0),
            lambda data: data["baseline"].update(autonomous_available=1),
            lambda data: data["baseline"].update(autonomous_available=0),
            lambda data: data["baseline"].update(autonomous_available="true"),
            lambda data: data["baseline"].update(autonomous_available="false"),
            lambda data: data["baseline"].update(diagnostic_task="wrong"),
            lambda data: data["baseline"].update(
                diagnostic_joined_key="autonomous_emergency_braking:aeb_emergency_stop"
            ),
            lambda data: data["baseline"].update(required_inputs=["/diagnostics"]),
            lambda data: data["fixture_constraints"].update(imu_path_horizon_s=2.0),
            lambda data: data["fixture_constraints"].update(imu_path_max_length_m=11.0),
            lambda data: data.update(allowed_outcomes=["unknown"]),
            lambda data: data.update(non_claims=[]),
            lambda data: data.update(non_claims=["anything"]),
            lambda data: data.update(unexpected="field"),
        )
        for mutate in mutations:
            candidate = load_scenario_config(self.CONFIG_PATH).to_mapping()
            mutate(candidate)
            with self.subTest(candidate=candidate), self.assertRaises(
                (TypeError, ValueError)
            ):
                ScenarioConfig.from_mapping(candidate)

    def test_direct_construction_cannot_bypass_nested_immutability(self) -> None:
        config = load_scenario_config(self.CONFIG_PATH)
        invalid_overrides = (
            {"initial_pose_map": "not-a-pose"},
            {"geometry": "not-geometry"},
            {"baseline": "not-baseline"},
            {"clocks": "not-clocks"},
            {"fixture_constraints": "not-constraints"},
            {"allowed_outcomes": list(Outcome)},
            {"non_claims": ["mutable"]},
        )
        for override in invalid_overrides:
            with self.subTest(override=override), self.assertRaises(TypeError):
                replace(config, **override)


if __name__ == "__main__":
    unittest.main()
