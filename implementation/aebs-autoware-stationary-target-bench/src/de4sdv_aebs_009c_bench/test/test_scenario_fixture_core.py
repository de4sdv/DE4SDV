"""Focused host tests for the ROS-independent stationary-target fixture state."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from de4sdv_aebs_009c_bench.scenario_contract import (  # noqa: E402
    Pose2D,
    anchor_target_pose_map,
    load_scenario_config,
)
from de4sdv_aebs_009c_bench.scenario_fixture_core import (  # noqa: E402
    FLOAT32_MAX,
    ScenarioFixtureState,
    pack_xyz_float32,
    quaternion_to_yaw,
)

CONFIG_PATH = PACKAGE_ROOT.parents[1] / "config" / "scenario-009c-aeb-mrm.yaml"


class ScenarioFixtureActivationTests(unittest.TestCase):
    def test_target_absent_until_activation_requires_current_ego(self) -> None:
        state = ScenarioFixtureState(load_scenario_config(CONFIG_PATH))

        self.assertEqual(state.target_points(), ())
        self.assertIsNone(state.anchored_target_pose_map)
        with self.assertRaises(RuntimeError):
            state.activate()
        self.assertEqual(state.target_points(), ())

        ego = Pose2D(4.0, -2.0, math.pi / 2.0)
        state.update_ego(ego)
        anchored = state.activate()

        self.assertEqual(
            anchored,
            anchor_target_pose_map(state.config.target_injection_pose_base_link, ego),
        )
        self.assertIs(state.anchored_target_pose_map, anchored)
        self.assertGreater(len(state.target_points()), 0)

    def test_activation_is_one_shot_and_map_anchor_stays_fixed_during_ego_motion(self) -> None:
        state = ScenarioFixtureState(load_scenario_config(CONFIG_PATH))
        injection_ego = Pose2D(10.0, 3.0, math.pi / 3.0)
        state.update_ego(injection_ego)
        anchored = state.activate()
        points_at_injection = state.target_points()

        state.update_ego(Pose2D(12.0, -1.0, -math.pi / 4.0))
        moved_points = state.target_points()

        self.assertIs(state.anchored_target_pose_map, anchored)
        self.assertEqual(
            anchored,
            anchor_target_pose_map(state.config.target_injection_pose_base_link, injection_ego),
        )
        self.assertNotEqual(moved_points, points_at_injection)
        with self.assertRaises(RuntimeError):
            state.activate()
        self.assertIs(state.anchored_target_pose_map, anchored)

    def test_geometry_is_deterministic_and_ego_updates_enforce_pose_contract(self) -> None:
        state = ScenarioFixtureState(load_scenario_config(CONFIG_PATH))
        for wrong in (None, (0.0, 0.0, 0.0), object()):
            with self.subTest(wrong=wrong), self.assertRaises(TypeError):
                state.update_ego(wrong)  # type: ignore[arg-type]

        state.update_ego(Pose2D(1.0, 2.0, 0.2))
        state.activate()
        first = state.target_points()

        self.assertEqual(first, state.target_points())
        self.assertIsInstance(first, tuple)
        self.assertTrue(first)

    def test_oversized_odometry_and_quaternion_values_are_rejected(self) -> None:
        state = ScenarioFixtureState(load_scenario_config(CONFIG_PATH))

        with self.assertRaises(ValueError):
            state.update_ego(Pose2D(FLOAT32_MAX * 2.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            quaternion_to_yaw(1.0e308, 1.0e308, 1.0e308, 1.0e308)

        self.assertAlmostEqual(quaternion_to_yaw(0.0, 0.0, 2.0, 2.0), math.pi / 2.0)

    def test_xyz_packing_rejects_non_float32_coordinates(self) -> None:
        state = ScenarioFixtureState(load_scenario_config(CONFIG_PATH))
        state.update_ego(Pose2D(0.0, 0.0, 0.0))
        state.activate()
        points = state.target_points()

        packed = pack_xyz_float32(points)
        self.assertEqual(len(packed), len(points) * 12)
        with self.assertRaises(ValueError):
            pack_xyz_float32((type(points[0])(FLOAT32_MAX * 2.0, 0.0, 0.0),))


if __name__ == "__main__":
    unittest.main()
