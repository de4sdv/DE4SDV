"""ROS-independent tests for the 009B observer/orchestrator core."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from de4sdv_aebs_009b_bench.scenario_contract import load_scenario_config  # noqa: E402
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind  # noqa: E402
from de4sdv_aebs_009b_bench.scenario_observer_core import (  # noqa: E402
    ObserverCore,
    atomic_write_json,
    closed_constant,
    exception_report,
    plain_json,
    validate_installed_config_path,
)

CONFIG = load_scenario_config(ROOT.parents[1] / "config/scenario-009b-stationary-target.yaml")

def obs(kind, at, **payload):
    return Observation(kind, payload, at)

def snapshot(at):
    return [
        obs(ObservationKind.DIAGNOSTIC, at, node="autonomous_emergency_braking", task="aeb_emergency_stop", level="OK"),
        obs(ObservationKind.AUTONOMOUS_AVAILABILITY, at, available=True),
        obs(ObservationKind.MRM_STATE, at, state="NORMAL", behavior="NONE"),
        obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, at, state="AVAILABLE"),
        obs(ObservationKind.NOMINAL_COMMAND, at, speed_mps=5.0, acceleration_mps2=1.0),
        obs(ObservationKind.GATE_COMMAND, at, path="nominal", acceleration_mps2=1.0),
        obs(ObservationKind.ODOMETRY, at, speed_mps=5.0, acceleration_mps2=0.0),
    ]

class ObserverCoreTests(unittest.TestCase):
    def test_installed_config_accepts_colcon_symlink_but_not_arbitrary_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.yaml"
            source.write_text("scenario: test\n")
            installed = root / "install/config"
            installed.mkdir(parents=True)
            linked = installed / "scenario.yaml"
            linked.symlink_to(source)

            self.assertEqual(
                validate_installed_config_path(
                    str(linked), installed, "scenario.yaml"
                ),
                linked,
            )
            with self.assertRaises(ValueError):
                validate_installed_config_path(
                    str(source), installed, "scenario.yaml"
                )

    def test_closed_constant_supports_byte_valued_ros_enums(self):
        class DiagnosticLevel:
            OK = b"\x00"
            WARN = b"\x01"

        self.assertEqual(
            closed_constant(DiagnosticLevel, b"\x00", ("OK", "WARN")), "OK"
        )
        with self.assertRaises(ValueError):
            closed_constant(DiagnosticLevel, b"\x02", ("OK", "WARN"))

    def test_arms_only_after_evaluator_proves_stable_baseline_and_only_once(self):
        core = ObserverCore(CONFIG, timeout_s=10.0, started_at_s=0.0)
        for at in (0.0, .4, .8, 1.2, 1.6):
            core.extend(snapshot(at))
            self.assertFalse(core.activation_requested)
        core.extend(snapshot(2.0))
        self.assertTrue(core.should_request_activation())
        core.mark_activation_requested(2.01)
        self.assertFalse(core.should_request_activation())
        core.mark_activation_response(2.02, True, "ok")
        self.assertEqual(core.activation_status, "succeeded")

    def test_timeout_finalizes_but_expected_missing_chain_does_not_end_early(self):
        core = ObserverCore(CONFIG, timeout_s=5.0, started_at_s=0.0)
        for at in (0, .4, .8, 1.2, 1.6, 2.0):
            core.extend(snapshot(at))
        core.mark_activation_requested(2.01)
        core.mark_activation_response(2.02, True, "ok")
        core.add(obs(ObservationKind.TARGET_PUBLICATION, 2.1, identity="target-1", frame="map", x=6, y=0, yaw_rad=0))
        self.assertIsNone(core.poll_terminal(2.2))
        self.assertEqual(core.poll_terminal(5.0), "timeout")

    def test_activation_success_waits_for_target_callback_or_timeout(self):
        core = ObserverCore(CONFIG, timeout_s=5.0, started_at_s=0.0)
        for at in (0, .4, .8, 1.2, 1.6, 2.0):
            core.extend(snapshot(at))
        core.mark_activation_requested(2.01)
        core.mark_activation_response(2.02, True, "accepted")

        # The Trigger response and target subscription run as separate ROS
        # callbacks. A successful response may therefore be observed first.
        self.assertIsNone(core.poll_terminal(2.03))
        self.assertEqual(core.poll_terminal(5.0), "timeout")

    def test_activation_rejection_remains_immediately_terminal(self):
        core = ObserverCore(CONFIG, timeout_s=5.0, started_at_s=0.0)
        for at in (0, .4, .8, 1.2, 1.6, 2.0):
            core.extend(snapshot(at))
        core.mark_activation_requested(2.01)
        core.mark_activation_response(2.02, False, "rejected")
        self.assertEqual(core.poll_terminal(2.03), "activation_failed")

    def test_exception_report_is_actionable_without_exception_message_secrets(self):
        error = RuntimeError("token=top-secret-value")
        initialized = exception_report(error, raw_output_available=True)
        startup = exception_report(error, raw_output_available=False)

        self.assertIn("RuntimeError", initialized)
        self.assertIn("raw_output", initialized)
        self.assertIn("before collector initialization", startup)
        self.assertNotIn("top-secret-value", initialized)
        self.assertNotIn("top-secret-value", startup)

    def test_gate_classification_is_fail_closed(self):
        core = ObserverCore(CONFIG, 10, 0)
        self.assertIsNone(core.classify_gate(0.9))
        core.note_gate_emergency(False, 1.0)
        self.assertEqual(core.classify_gate(1.1), "nominal")
        core.note_gate_emergency(True, 1.2)
        self.assertEqual(core.classify_gate(1.3), "emergency")
        self.assertIsNone(core.classify_gate(2.0))
        self.assertFalse(core.errors)

    def test_odometry_requires_fresh_finite_acceleration(self):
        core = ObserverCore(CONFIG, 10, 0)
        core.note_acceleration(-.2, 1.0, "a")
        item = core.make_odometry(4.0, 1.4, "odom")
        self.assertEqual(item.payload["acceleration_mps2"], -.2)
        self.assertEqual(item.source_stamp, "odom")
        self.assertIsNone(core.make_odometry(3.9, 1.6, "odom2"))
        self.assertFalse(core.errors)

    def test_memory_is_bounded_and_cap_is_instrument_failure(self):
        core = ObserverCore(CONFIG, 1, 0, observation_cap=3, error_cap=2)
        for n in range(8):
            core.add(obs(ObservationKind.AUTONOMOUS_AVAILABILITY, n / 10, available=True))
        self.assertLessEqual(len(core.observations), 3)
        self.assertLessEqual(len(core.errors), 2)
        self.assertTrue(any(x.kind is ObservationKind.INSTRUMENT_STATUS and not x.payload["available"] for x in core.observations))

    def test_plain_serialization_and_atomic_safe_output_are_deterministic(self):
        core = ObserverCore(CONFIG, 1, 0)
        core.add(obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 0, available=True))
        document = core.result_document("timeout", 2, ended_at_s=1.0)
        self.assertEqual(document["collector_id"], "de4sdv.scenario_observer.v1")
        self.assertEqual(document["monotonic_start_s"], 0.0)
        self.assertEqual(document["monotonic_end_s"], 1.0)
        self.assertIn("evaluator_result", document)
        self.assertEqual(document["command_exit"], 2)
        encoded = json.dumps(plain_json(document), sort_keys=True, separators=(",", ":"))
        self.assertEqual(encoded, json.dumps(plain_json(document), sort_keys=True, separators=(",", ":")))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.json"
            atomic_write_json(path, document)
            self.assertEqual(json.loads(path.read_text()), plain_json(document))
            link = Path(directory) / "link.json"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                atomic_write_json(link, document)
        with self.assertRaises(ValueError):
            atomic_write_json(Path("relative.json"), document)

if __name__ == "__main__":
    unittest.main()
