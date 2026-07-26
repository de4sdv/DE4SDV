"""Host-side AST and metadata contracts for the separate 009C ROS package."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "de4sdv_aebs_009c_bench"


class RosPackageMetadataTests(unittest.TestCase):
    def test_ament_metadata_installs_entrypoint_launch_and_external_config(self) -> None:
        setup_tree = ast.parse((PACKAGE_ROOT / "setup.py").read_text(encoding="utf-8"))
        setup_call = next(
            node
            for node in ast.walk(setup_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setup"
        )
        keywords = {keyword.arg: keyword.value for keyword in setup_call.keywords}
        self.assertEqual(ast.literal_eval(keywords["name"]), PACKAGE_NAME)
        data_files_source = ast.unparse(keywords["data_files"])
        self.assertIn("launch/aebs_009c_bench.launch.py", data_files_source)
        self.assertIn("../../config/scenario-009c-aeb-mrm.yaml", data_files_source)
        entry_points = ast.literal_eval(keywords["entry_points"])
        self.assertEqual(
            entry_points["console_scripts"],
            [
                "scenario_fixture = de4sdv_aebs_009c_bench.scenario_fixture:main",
                "scenario_observer = de4sdv_aebs_009c_bench.scenario_observer:main",
            ],
        )

        root = ET.parse(PACKAGE_ROOT / "package.xml").getroot()
        self.assertEqual(root.findtext("name"), PACKAGE_NAME)
        self.assertEqual(root.findtext("export/build_type"), "ament_python")
        dependencies = {node.text for node in root.findall("exec_depend")}
        self.assertTrue(
            {
                "rclpy",
                "python3-yaml",
                "geometry_msgs",
                "nav_msgs",
                "sensor_msgs",
                "std_srvs",
                "autoware_adapi_v1_msgs",
                "autoware_control_msgs",
                "autoware_system_msgs",
                "autoware_vehicle_msgs",
            }.issubset(dependencies)
        )
        self.assertEqual((PACKAGE_ROOT / "resource" / PACKAGE_NAME).read_text(), "")
        self.assertTrue((PACKAGE_ROOT / "setup.cfg").is_file())


class FixtureAdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (PACKAGE_ROOT / PACKAGE_NAME / "scenario_fixture.py").read_text(
            encoding="utf-8"
        )
        self.tree = ast.parse(self.source)

    def _calls(self, method: str) -> list[ast.Call]:
        return [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == method
        ]

    def test_ros_interfaces_are_exact_and_fixture_has_no_claim_outputs(self) -> None:
        publishers = {
            ast.literal_eval(call.args[1]) for call in self._calls("create_publisher")
        }
        self.assertEqual(
            publishers,
            {
                "/initialpose3d",
                "/autoware/engage",
                "/api/operation_mode/state",
                "/system/operation_mode/state",
                "/autoware/state",
                "/control/trajectory_follower/control_cmd",
                "/control/shift_decider/gear_cmd",
                "/planning/turn_indicators_cmd",
                "/planning/hazard_lights_cmd",
                "/perception/obstacle_segmentation/pointcloud",
                "/de4sdv/aebs_009c/target_pose_map",
            },
        )
        subscriptions = self._calls("create_subscription")
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(ast.literal_eval(subscriptions[0].args[1]), "/localization/kinematic_state")
        services = self._calls("create_service")
        self.assertEqual(len(services), 1)
        self.assertEqual(ast.literal_eval(services[0].args[1]), "/de4sdv/aebs_009c/inject_target")
        forbidden = {
            "/system/fail_safe/mrm_state",
            "/system/driving_mode/mrm_state",
            "/system/emergency/control_cmd",
            "/control/command/control_cmd",
            "/diagnostics",
        }
        self.assertTrue(forbidden.isdisjoint(publishers))
        self.assertNotIn("verdict", self.source.lower())
        self.assertNotIn("braking", self.source.lower())

    def test_cloud_layout_rates_config_commands_and_activation_are_explicit(self) -> None:
        assignments = {
            ast.unparse(node.targets[0]): ast.unparse(node.value)
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Assign) and len(node.targets) == 1
        }
        self.assertEqual(assignments["cloud.point_step"], "POINT_STEP")
        self.assertEqual(assignments["cloud.is_bigendian"], "False")
        self.assertEqual(assignments["cloud.is_dense"], "True")
        constants = {
            target.id: ast.literal_eval(node.value)
            for node in self.tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertEqual(constants["POINT_STEP"], 12)
        self.assertEqual(constants["XYZ_FIELDS"], (("x", 0), ("y", 4), ("z", 8)))
        self.assertIn("config.pointcloud_rate_hz", self.source)
        self.assertIn("config.ego_state_rate_hz", self.source)
        self.assertIn("config.nominal_command_speed_mps", self.source)
        self.assertIn("config.nominal_command_acceleration_mps2", self.source)
        self.assertIn("config.initial_pose_map", self.source)
        self.assertIn("declare_parameter(\"scenario_config\")", self.source)
        self.assertIn("pack_xyz_float32(points)", self.source)
        self.assertIn("quaternion_to_yaw(", self.source)
        self.assertNotIn("source_stamp", self.source)

    def test_cloud_timer_contains_transform_and_packing_failures(self) -> None:
        fixture_class = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ScenarioFixture"
        )
        callback = next(
            node
            for node in fixture_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "_publish_cloud"
        )
        callback_source = ast.unparse(callback)

        self.assertIn("except (TypeError, ValueError, OverflowError)", callback_source)
        self.assertLess(
            callback_source.index("except (TypeError, ValueError, OverflowError)"),
            callback_source.index("self.cloud_pub.publish(cloud)"),
        )

    def test_odometry_must_be_explicitly_map_framed_before_state_update(self) -> None:
        fixture_class = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ScenarioFixture"
        )
        callback = next(
            node
            for node in fixture_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "_on_odometry"
        )
        callback_source = ast.unparse(callback)

        self.assertIn("message.header.frame_id != 'map'", callback_source)
        self.assertLess(
            callback_source.index("message.header.frame_id != 'map'"),
            callback_source.index("self._state.update_ego(ego)"),
        )

    def test_initial_pose_is_published_once_outside_the_periodic_nominal_loop(self) -> None:
        methods = {
            node.name: node
            for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ScenarioFixture"
            for node in node.body
            if isinstance(node, ast.FunctionDef)
        }
        nominal_source = ast.unparse(methods["_publish_nominal_inputs"])
        initial_source = ast.unparse(methods["_publish_initial_pose"])
        init_source = ast.unparse(methods["__init__"])

        self.assertNotIn("initial_pose_pub.publish", nominal_source)
        self.assertEqual(initial_source.count("initial_pose_pub.publish"), 1)
        self.assertEqual(init_source.count("self._publish_initial_pose()"), 1)


class LaunchCompositionContractTests(unittest.TestCase):
    def test_launch_is_separate_but_preserves_pinned_composition_and_remaps(self) -> None:
        path = PACKAGE_ROOT / "launch" / "aebs_009c_bench.launch.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Node"
        ]
        node_pairs = {
            (
                ast.literal_eval(next(k.value for k in node.keywords if k.arg == "package")),
                ast.literal_eval(next(k.value for k in node.keywords if k.arg == "executable")),
            )
            for node in nodes
        }
        self.assertEqual(
            node_pairs,
            {
                (
                    "autoware_mrm_emergency_stop_operator",
                    "autoware_mrm_emergency_stop_operator_node",
                ),
                ("autoware_vehicle_cmd_gate", "vehicle_cmd_gate_exe"),
                (
                    "autoware_autonomous_emergency_braking",
                    "autoware_autonomous_emergency_braking",
                ),
                (PACKAGE_NAME, "scenario_fixture"),
            },
        )
        self.assertIn('get_package_share_directory("de4sdv_aebs_bench")', source)
        self.assertIn('get_package_share_directory("autoware_simple_planning_simulator")', source)
        for included in (
            '"tier4_map_launch"',
            '"autoware_diagnostic_graph_aggregator"',
            '"autoware_mrm_handler"',
        ):
            self.assertIn(included, source)
        for remap in (
            '("~/input/pointcloud", "/perception/obstacle_segmentation/pointcloud")',
            '("input/operation_mode", "/system/operation_mode/state")',
            '("input/kinematics", "/localization/kinematic_state")',
            '("output/operation_mode", "/control/vehicle_cmd_gate/operation_mode")',
            '("~/input/control/control_cmd", "/control/command/control_cmd")',
        ):
            self.assertIn(remap, source)
        self.assertIn('DeclareLaunchArgument("map_path"', source)
        self.assertIn("scenario-009c-aeb-mrm.yaml", source)
        self.assertNotIn("nominal_fixture", source)
        self.assertIn("no runtime or scenario evidence claim", ast.get_docstring(tree).lower())


if __name__ == "__main__":
    unittest.main()
