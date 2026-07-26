"""Static ROS adapter contract tests; these do not claim a ROS runtime test."""
from __future__ import annotations
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "de4sdv_aebs_009b_bench/scenario_observer.py"

class RosObserverContractTests(unittest.TestCase):
    def test_exact_subscription_topics_and_types_and_no_publishers_or_services(self):
        text = SOURCE.read_text()
        expected = {
            "/diagnostics": "DiagnosticArray",
            "/system/operation_mode/availability": "OperationModeAvailability",
            "/system/fail_safe/mrm_state": "MrmState",
            "/system/mrm/emergency_stop/status": "MrmBehaviorStatus",
            "/control/trajectory_follower/control_cmd": "Control",
            "/system/emergency/control_cmd": "Control",
            "/control/command/emergency_cmd": "VehicleEmergencyStamped",
            "/control/command/control_cmd": "Control",
            "/localization/kinematic_state": "Odometry",
            "/localization/acceleration": "AccelWithCovarianceStamped",
            "/de4sdv/aebs_009b/target_pose_map": "PoseStamped",
        }
        tree = ast.parse(text)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        subscriptions = [c for c in calls if isinstance(c.func, ast.Attribute) and c.func.attr == "create_subscription"]
        actual = {c.args[1].value: c.args[0].id for c in subscriptions}
        self.assertEqual(actual, expected)
        self.assertNotIn("create_publisher", text)
        self.assertNotIn("create_service", text)

    def test_one_trigger_client_exact_service_monotonic_and_safe_main(self):
        text = SOURCE.read_text()
        tree = ast.parse(text)
        self.assertEqual(text.count("create_client("), 1)
        self.assertIn('Trigger, "/de4sdv/aebs_009b/inject_target"', text)
        self.assertIn("time.monotonic()", text)
        self.assertIn("rclpy.spin_once", text)
        self.assertIn("except KeyboardInterrupt", text)
        self.assertIn('declare_parameter("scenario_config"', text)
        self.assertIn('declare_parameter("raw_output"', text)
        self.assertIn('declare_parameter("timeout_s"', text)
        operator = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_operator"
        )
        operator_source = ast.unparse(operator)
        self.assertIn(
            "('NOT_AVAILABLE', 'AVAILABLE', 'OPERATING')", operator_source
        )
        self.assertNotIn("'SUCCEEDED'", operator_source)
        self.assertNotIn("'FAILED'", operator_source)

    def test_unrelated_diagnostic_arrays_do_not_refresh_or_fail_aeb_instrument(self):
        tree = ast.parse(SOURCE.read_text())
        diagnostics = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_diagnostics"
        )
        safe = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_safe"
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Return)
                and isinstance(node.value, ast.Constant)
                and node.value.value is False
                for node in ast.walk(diagnostics)
            )
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Compare)
                and any(isinstance(operator, ast.IsNot) for operator in node.ops)
                and any(
                    isinstance(comparator, ast.Constant)
                    and comparator.value is False
                    for comparator in node.comparators
                )
                for node in ast.walk(safe)
            )
        )

    def test_main_reports_fatal_exceptions_to_stderr(self):
        tree = ast.parse(SOURCE.read_text())
        main = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        main_source = ast.unparse(main)
        self.assertIn("exception_report(error", main_source)
        self.assertIn("file=sys.stderr", main_source)
        self.assertIn("node.finish()", main_source)

    def test_packaging_contract(self):
        setup = (ROOT / "setup.py").read_text()
        package = (ROOT / "package.xml").read_text()
        self.assertIn("scenario_observer = de4sdv_aebs_009b_bench.scenario_observer:main", setup)
        for dependency in ("diagnostic_msgs", "tier4_system_msgs", "tier4_vehicle_msgs", "autoware_adapi_v1_msgs", "autoware_control_msgs", "geometry_msgs", "nav_msgs", "std_srvs"):
            self.assertIn(f"<exec_depend>{dependency}</exec_depend>", package)

if __name__ == "__main__":
    unittest.main()
