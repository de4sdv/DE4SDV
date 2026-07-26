"""Strict tests for the ROS-independent 009C observed event-chain evaluator."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from de4sdv_aebs_009c_bench.scenario_contract import Outcome, load_scenario_config  # noqa: E402
from de4sdv_aebs_009c_bench.scenario_evaluator import (  # noqa: E402
    EvaluationResult,
    EventReference,
    Observation,
    ObservationKind,
    REQUIRED_INPUT_KIND,
    evaluate_scenario,
)

CONFIG_PATH = PACKAGE_ROOT.parents[1] / "config" / "scenario-009c-aeb-mrm.yaml"
CONFIG = load_scenario_config(CONFIG_PATH)


def obs(kind: ObservationKind, time: float, **payload: object) -> Observation:
    return Observation(kind, payload, time)


def baseline_snapshot(time: float, *, diagnostic: str = "OK") -> list[Observation]:
    return [
        obs(ObservationKind.DIAGNOSTIC, time, node="autonomous_emergency_braking", task="aeb_emergency_stop", level=diagnostic),
        obs(ObservationKind.AUTONOMOUS_AVAILABILITY, time, available=True),
        obs(ObservationKind.MRM_STATE, time, state="NORMAL", behavior="NONE"),
        obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, time, state="AVAILABLE"),
        obs(ObservationKind.NOMINAL_COMMAND, time, speed_mps=5.0, acceleration_mps2=1.0),
        obs(ObservationKind.GATE_COMMAND, time, path="nominal", acceleration_mps2=1.0),
        obs(ObservationKind.ODOMETRY, time, speed_mps=5.0, acceleration_mps2=0.0),
    ]


def stable_baseline() -> list[Observation]:
    observations: list[Observation] = []
    for time in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0):
        observations += baseline_snapshot(time)
    return observations


def injection(time: float = 2.1) -> Observation:
    return obs(ObservationKind.TARGET_PUBLICATION, time, identity="target-1", frame="map", x=6.0, y=0.0, yaw_rad=0.0)


def intervention(time: float = 2.2, *, distance_m: float = 5.8) -> Observation:
    return obs(
        ObservationKind.AEB_INTERVENTION,
        time,
        message="[AEB]: Emergency Brake",
        rss_distance_m=6.1,
        object_distance_m=distance_m,
        object_speed_mps=0.0,
    )


def chain_through_gate() -> list[Observation]:
    return stable_baseline() + [
        injection(),
        obs(
            ObservationKind.AEB_INTERVENTION,
            2.2,
            message="[AEB]: Emergency Brake",
            rss_distance_m=6.1,
            object_distance_m=5.8,
            object_speed_mps=0.0,
        ),
        obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.3, available=False),
        obs(ObservationKind.MRM_STATE, 2.4, state="MRM_OPERATING", behavior="EMERGENCY_STOP"),
        obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, 2.45, state="OPERATING"),
        obs(ObservationKind.EMERGENCY_COMMAND, 2.5, speed_mps=0.0, acceleration_mps2=-1.2),
        obs(ObservationKind.NOMINAL_COMMAND, 2.55, speed_mps=5.0, acceleration_mps2=0.4),
        obs(ObservationKind.ODOMETRY, 2.56, speed_mps=4.8, acceleration_mps2=0.0),
        obs(ObservationKind.GATE_EMERGENCY_STATUS, 2.58, emergency=True),
        obs(ObservationKind.GATE_COMMAND, 2.6, path="emergency", acceleration_mps2=-0.7),
    ]


class DirectionalResponseTests(unittest.TestCase):
    def test_completed_stages_cannot_regress_after_final_gate(self) -> None:
        regressions = (
            intervention(2.65, distance_m=6.2),
            obs(ObservationKind.GATE_COMMAND, 2.65, path="nominal", acceleration_mps2=0.4),
        )
        for regression in regressions:
            with self.subTest(kind=regression.kind):
                observations = chain_through_gate() + [
                    regression,
                    obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
                ]

                result = evaluate_scenario(CONFIG, observations)

                self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
                self.assertEqual(result.details["failed_event"], "completed_stage_regression")
                references = [
                    event for event in result.accepted_events
                    if event.label.startswith("completed_stage_regression:")
                ]
                self.assertEqual(len(references), 1)
                self.assertEqual(references[0].observation_index, observations.index(regression))

    def test_passing_evidence_contains_complete_baseline_chain_and_response_support(self) -> None:
        observations = chain_through_gate() + [
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.8, acceleration_mps2=-0.2),
            obs(ObservationKind.ODOMETRY, 2.8, speed_mps=4.2, acceleration_mps2=0.0),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.PASS_OBSERVED_CHAIN)
        labels = {event.label for event in result.accepted_events}
        self.assertEqual(
            {label for label in labels if label.startswith("baseline_final_support:")},
            {f"baseline_final_support:{topic}" for topic in REQUIRED_INPUT_KIND},
        )
        self.assertEqual(
            {label for label in labels if label.startswith("baseline_candidate_start:")},
            {f"baseline_candidate_start:{topic}" for topic in REQUIRED_INPUT_KIND},
        )
        self.assertTrue({
            "target_injection",
            "native_aeb_intervention",
            "autonomous_unavailable",
            "mrm_emergency_stop",
            "emergency_operator_operating",
            "emergency_command_negative",
            "gate_selection_negative",
            "latest_fresh_positive_nominal_at_gate",
            "pre_selection_odometry",
            "negative_acceleration_response",
            "lower_speed_response",
        }.issubset(labels))
        self.assertEqual(result.details["baseline_interval_start_s"], 0.0)
        ordering = [(event.receipt_monotonic_s, event.observation_index) for event in result.accepted_events]
        self.assertEqual(ordering, sorted(ordering))

    def test_negative_acceleration_and_later_lower_speed_may_be_separate_samples(self) -> None:
        observations = chain_through_gate() + [
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.8, acceleration_mps2=-0.2),
            obs(ObservationKind.ODOMETRY, 2.8, speed_mps=4.2, acceleration_mps2=0.0),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.PASS_OBSERVED_CHAIN)
        labels = [event.label for event in result.accepted_events]
        self.assertIn("negative_acceleration_response", labels)
        self.assertIn("lower_speed_response", labels)

    def test_lower_speed_before_negative_acceleration_does_not_prove_directional_response(self) -> None:
        observations = chain_through_gate() + [
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=0.0),
            obs(ObservationKind.ODOMETRY, 2.8, speed_mps=4.8, acceleration_mps2=-0.2),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "directional_response")

    def test_same_time_gate_odometry_is_not_pre_selection(self) -> None:
        observations = chain_through_gate() + [
            obs(ObservationKind.ODOMETRY, 2.6, speed_mps=0.5, acceleration_mps2=0.0),
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.7, acceleration_mps2=-0.2),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.PASS_OBSERVED_CHAIN)
        self.assertEqual(result.details["pre_selection_speed_mps"], 4.8)

    def test_stale_pre_injection_odometry_cannot_support_directional_pass(self) -> None:
        observations = [
            item
            for item in chain_through_gate()
            if not (
                item.kind is ObservationKind.ODOMETRY
                and item.receipt_monotonic_s == 2.56
            )
        ]
        observations += [
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.8, acceleration_mps2=-0.2),
            obs(ObservationKind.ODOMETRY, 2.8, speed_mps=4.2, acceleration_mps2=0.0),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "directional_response")

    def test_pass_requires_later_lower_speed_and_post_selection_negative_acceleration(self) -> None:
        no_negative = chain_through_gate() + [obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.0, acceleration_mps2=0.0)]
        self.assertEqual(evaluate_scenario(CONFIG, no_negative).outcome, Outcome.FAIL_SCENARIO)
        no_lower = chain_through_gate() + [obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.8, acceleration_mps2=-0.2)]
        self.assertEqual(evaluate_scenario(CONFIG, no_lower).outcome, Outcome.FAIL_SCENARIO)

        passing = chain_through_gate() + [obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2)]
        result = evaluate_scenario(CONFIG, passing)
        self.assertEqual(result.outcome, Outcome.PASS_OBSERVED_CHAIN)
        self.assertEqual(result.details["pre_selection_speed_mps"], 4.8)
        self.assertEqual(result.details["response_speed_mps"], 4.2)
        self.assertEqual(result.details["accepted_receipt_times_s"], tuple(event.receipt_monotonic_s for event in result.accepted_events))
        self.assertTrue(any("not physical braking evidence" in reason for reason in result.reasons))


class TargetAndClockTests(unittest.TestCase):
    def test_target_must_keep_identical_map_identity_and_pose(self) -> None:
        moving = chain_through_gate() + [
            obs(ObservationKind.TARGET_PUBLICATION, 2.15, identity="target-1", frame="map", x=6.1, y=0.0, yaw_rad=0.0),
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
        ]
        result = evaluate_scenario(CONFIG, moving)
        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "stationary_map_target")

    def test_source_and_host_clocks_are_preserved_but_never_used_for_order(self) -> None:
        observations = chain_through_gate()
        observations[42] = replace(observations[42], source_stamp="source-999", host_utc="2026-07-26T12:00:09Z")
        observations[43] = replace(observations[43], source_stamp="source-001", host_utc="2026-07-26T12:00:01Z")
        observations.append(obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2))
        result = evaluate_scenario(CONFIG, observations)
        self.assertEqual(result.outcome, Outcome.PASS_OBSERVED_CHAIN)
        provenance = result.details["clock_provenance"]
        self.assertIn(("source-999", "2026-07-26T12:00:09Z"), provenance)
        self.assertIn(("source-001", "2026-07-26T12:00:01Z"), provenance)
        self.assertEqual(result.details["source_stamp_comparison"], "forbidden")


class EmergencyGateCorrelationTests(unittest.TestCase):
    def test_equal_time_emergency_and_contradictory_nominal_is_conservative(self) -> None:
        contradictory = obs(
            ObservationKind.NOMINAL_COMMAND,
            2.5,
            speed_mps=0.0,
            acceleration_mps2=-0.1,
        )
        after_emergency = chain_through_gate() + [
            contradictory,
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
        ]
        before_emergency = chain_through_gate()
        emergency_index = next(
            index
            for index, item in enumerate(before_emergency)
            if item.kind is ObservationKind.EMERGENCY_COMMAND
            and item.receipt_monotonic_s == 2.5
        )
        before_emergency.insert(emergency_index, contradictory)
        before_emergency.append(
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2)
        )

        for observations in (before_emergency, after_emergency):
            with self.subTest(contradiction_before_emergency=observations is before_emergency):
                result = evaluate_scenario(CONFIG, observations)
                self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
                self.assertEqual(result.details["failed_event"], "nominal_gate_correlation")

    def test_latest_nominal_at_gate_must_be_fresh_positive_and_uncontradicted(self) -> None:
        latest_negative = chain_through_gate() + [
            obs(ObservationKind.NOMINAL_COMMAND, 2.57, speed_mps=0.0, acceleration_mps2=-0.1),
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
        ]
        result = evaluate_scenario(CONFIG, latest_negative)
        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "nominal_gate_correlation")

        contradicted_then_positive = chain_through_gate() + [
            obs(ObservationKind.NOMINAL_COMMAND, 2.52, speed_mps=0.0, acceleration_mps2=-0.1),
            obs(ObservationKind.NOMINAL_COMMAND, 2.58, speed_mps=5.0, acceleration_mps2=0.2),
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
        ]
        result = evaluate_scenario(CONFIG, contradicted_then_positive)
        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "nominal_gate_correlation")

    def test_directional_negative_correlation_does_not_require_exact_minus_2_5(self) -> None:
        result = evaluate_scenario(CONFIG, chain_through_gate())
        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)  # response intentionally absent
        self.assertEqual(result.details["failed_event"], "directional_response")
        self.assertEqual(result.details["emergency_acceleration_mps2"], -1.2)
        self.assertEqual(result.details["gate_acceleration_mps2"], -0.7)


class MissingAndReorderedChainTests(unittest.TestCase):
    def test_gate_status_must_strictly_precede_selected_gate_command(self) -> None:
        observations = chain_through_gate()
        original = next(
            item
            for item in observations
            if item.kind is ObservationKind.GATE_EMERGENCY_STATUS
        )
        gate = next(
            item
            for item in observations
            if item.kind is ObservationKind.GATE_COMMAND
            and item.payload["path"] == "emergency"
        )
        observations.remove(original)
        observations.insert(
            observations.index(gate) + 1,
            obs(
                ObservationKind.GATE_EMERGENCY_STATUS,
                gate.receipt_monotonic_s,
                emergency=True,
            ),
        )
        observations.append(
            obs(
                ObservationKind.ODOMETRY,
                2.7,
                speed_mps=4.2,
                acceleration_mps2=-0.2,
            )
        )

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "gate_emergency_status")

    def test_chain_state_must_remain_steady_through_injection_boundary(self) -> None:
        for offending_time in (2.05, 2.1):
            with self.subTest(offending_time=offending_time):
                offending = intervention(offending_time)
                observations = chain_through_gate() + [
                    offending,
                    obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
                ]

                result = evaluate_scenario(CONFIG, observations)

                self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
                self.assertEqual(result.details["failed_event"], "pre_injection_chain_state")
                references = [
                    event for event in result.accepted_events
                    if event.label == "pre_injection_nonsteady:native_aeb_intervention"
                ]
                self.assertEqual(len(references), 1)
                self.assertEqual(references[0].observation_index, observations.index(offending))

    def test_continuous_steady_publications_before_each_transition_are_ignored(self) -> None:
        observations = stable_baseline() + [
            injection(),
            obs(ObservationKind.DIAGNOSTIC, 2.11, node="autonomous_emergency_braking", task="aeb_emergency_stop", level="OK"),
            obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.12, available=True),
            obs(ObservationKind.MRM_STATE, 2.13, state="NORMAL", behavior="NONE"),
            obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, 2.14, state="AVAILABLE"),
            obs(ObservationKind.EMERGENCY_COMMAND, 2.15, speed_mps=5.0, acceleration_mps2=0.0),
            obs(ObservationKind.GATE_COMMAND, 2.16, path="nominal", acceleration_mps2=0.4),
            intervention(2.2),
            obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.3, available=False),
            obs(ObservationKind.MRM_STATE, 2.4, state="MRM_OPERATING", behavior="EMERGENCY_STOP"),
            obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, 2.45, state="OPERATING"),
            obs(ObservationKind.EMERGENCY_COMMAND, 2.5, speed_mps=0.0, acceleration_mps2=-1.2),
            obs(ObservationKind.NOMINAL_COMMAND, 2.55, speed_mps=5.0, acceleration_mps2=0.4),
            obs(ObservationKind.ODOMETRY, 2.56, speed_mps=4.8, acceleration_mps2=0.0),
            obs(ObservationKind.GATE_EMERGENCY_STATUS, 2.58, emergency=True),
            obs(ObservationKind.GATE_COMMAND, 2.6, path="emergency", acceleration_mps2=-0.7),
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.PASS_OBSERVED_CHAIN)

    def test_later_stage_before_expected_cannot_be_hidden_by_repeat(self) -> None:
        observations = stable_baseline() + [
            injection(),
            obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.2, available=False),
            intervention(2.3),
            obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.4, available=False),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "native_aeb_intervention")

    def test_contradictory_expected_stage_cannot_be_hidden_by_later_match(self) -> None:
        observations = stable_baseline() + [
            injection(),
            intervention(2.2, distance_m=6.2),
            intervention(2.3),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "native_aeb_intervention")

    def test_equal_receipt_times_cannot_prove_stage_order(self) -> None:
        observations = stable_baseline() + [
            injection(),
            intervention(2.2),
            obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.2, available=False),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "autonomous_unavailable")

    def test_missing_or_reordered_post_injection_event_is_scenario_failure(self) -> None:
        missing = stable_baseline() + [injection()]
        missing_result = evaluate_scenario(CONFIG, missing)
        self.assertEqual(missing_result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(missing_result.details["failed_event"], "native_aeb_intervention")

        reordered = stable_baseline() + [
            injection(),
            obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.2, available=False),
            intervention(2.3),
        ]
        reordered_result = evaluate_scenario(CONFIG, reordered)
        self.assertEqual(reordered_result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(reordered_result.details["failed_event"], "native_aeb_intervention")


class InstrumentationAndPreconditionTests(unittest.TestCase):
    def test_equal_time_instrument_conflicts_are_conservative_in_both_orders(self) -> None:
        false_status = obs(ObservationKind.INSTRUMENT_STATUS, 1.9, topic="/diagnostics", available=False)
        true_status = obs(ObservationKind.INSTRUMENT_STATUS, 1.9, topic="/diagnostics", available=True)
        for statuses in ((false_status, true_status), (true_status, false_status)):
            with self.subTest(boundary="baseline", false_first=statuses[0] is false_status):
                result = evaluate_scenario(CONFIG, stable_baseline() + list(statuses))
                self.assertEqual(result.outcome, Outcome.INCONCLUSIVE_INSTRUMENTATION)
                self.assertEqual(result.details["unavailable_inputs"], ("/diagnostics",))

        for false_first in (True, False):
            with self.subTest(boundary="injection", false_first=false_first):
                false_after = obs(ObservationKind.INSTRUMENT_STATUS, 2.05, topic="/diagnostics", available=False)
                true_after = obs(ObservationKind.INSTRUMENT_STATUS, 2.05, topic="/diagnostics", available=True)
                statuses = [false_after, true_after] if false_first else [true_after, false_after]
                observations = chain_through_gate() + statuses + [
                    obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
                ]

                result = evaluate_scenario(CONFIG, observations)

                self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
                self.assertEqual(result.details["failed_event"], "instrument_unavailable_after_baseline")
                reference = next(
                    event for event in result.accepted_events
                    if event.label == "instrument_unavailable_after_baseline:/diagnostics"
                )
                self.assertEqual(reference.observation_index, observations.index(false_after))

    def test_false_instrument_after_baseline_before_injection_is_scenario_failure(self) -> None:
        observations = stable_baseline() + [
            obs(ObservationKind.INSTRUMENT_STATUS, 2.05, topic="/diagnostics", available=False),
            injection(),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "instrument_unavailable_after_baseline")
        self.assertIn("instrument_unavailable_after_baseline:/diagnostics", [event.label for event in result.accepted_events])

    def test_instrument_recovery_before_injection_does_not_block_valid_chain(self) -> None:
        observations = chain_through_gate() + [
            obs(ObservationKind.INSTRUMENT_STATUS, 2.02, topic="/diagnostics", available=False),
            obs(ObservationKind.INSTRUMENT_STATUS, 2.06, topic="/diagnostics", available=True),
            obs(ObservationKind.ODOMETRY, 2.7, speed_mps=4.2, acceleration_mps2=-0.2),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.PASS_OBSERVED_CHAIN)

    def test_late_false_instrument_after_baseline_and_injection_is_scenario_failure(self) -> None:
        observations = stable_baseline() + [
            injection(),
            obs(ObservationKind.INSTRUMENT_STATUS, 2.15, topic="/diagnostics", available=False),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "instrument_unavailable_after_injection")
        self.assertIn("instrument_unavailable_after_injection:/diagnostics", [event.label for event in result.accepted_events])

    def test_absent_or_explicitly_unavailable_required_input_is_instrumentation_failure(self) -> None:
        self.assertEqual(evaluate_scenario(CONFIG, []).outcome, Outcome.INCONCLUSIVE_INSTRUMENTATION)
        missing_odometry = [item for item in baseline_snapshot(0.0) if item.kind is not ObservationKind.ODOMETRY]
        self.assertEqual(evaluate_scenario(CONFIG, missing_odometry).outcome, Outcome.INCONCLUSIVE_INSTRUMENTATION)
        self.assertEqual(tuple(REQUIRED_INPUT_KIND), CONFIG.baseline.required_inputs)
        observations = baseline_snapshot(0.0)
        observations.append(obs(ObservationKind.INSTRUMENT_STATUS, 0.1, topic="/diagnostics", available=False))
        result = evaluate_scenario(CONFIG, observations)
        self.assertEqual(result.outcome, Outcome.INCONCLUSIVE_INSTRUMENTATION)
        self.assertEqual(result.details["unavailable_inputs"], ("/diagnostics",))

        with self.assertRaises(ValueError):
            obs(ObservationKind.INSTRUMENT_STATUS, 0.2, topic="/silently/inferred", available=False)

    def test_recovered_instrument_status_without_stable_baseline_is_precondition_failure(self) -> None:
        observations: list[Observation] = []
        for time in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4):
            observations += baseline_snapshot(time, diagnostic="WARN")
        observations += [
            obs(ObservationKind.INSTRUMENT_STATUS, 0.1, topic="/diagnostics", available=False),
            obs(ObservationKind.INSTRUMENT_STATUS, 0.2, topic="/diagnostics", available=True),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.INCONCLUSIVE_PRECONDITION)

    def test_complete_instrumentation_without_stable_exact_baseline_is_precondition_failure(self) -> None:
        observations: list[Observation] = []
        for time in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4):
            observations += baseline_snapshot(time, diagnostic="WARN")
        self.assertEqual(evaluate_scenario(CONFIG, observations).outcome, Outcome.INCONCLUSIVE_PRECONDITION)

    def test_runtime_not_available_operator_state_is_precondition_not_instrumentation(self) -> None:
        observations: list[Observation] = []
        for time in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4):
            snapshot = baseline_snapshot(time)
            snapshot[3] = obs(
                ObservationKind.EMERGENCY_OPERATOR_STATUS,
                time,
                state="NOT_AVAILABLE",
            )
            observations += snapshot

        self.assertEqual(
            evaluate_scenario(CONFIG, observations).outcome,
            Outcome.INCONCLUSIVE_PRECONDITION,
        )


class StableBaselineTests(unittest.TestCase):
    def test_full_snapshots_cannot_bridge_expired_required_input_intervals(self) -> None:
        observations: list[Observation] = []
        for time in (0.0, 0.8, 1.6):
            observations += baseline_snapshot(time)
        for time in (0.4, 1.2, 2.0):
            observations.append(obs(
                ObservationKind.DIAGNOSTIC,
                time,
                node="autonomous_emergency_braking",
                task="aeb_emergency_stop",
                level="OK",
            ))
        observations.append(injection(2.1))

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.INCONCLUSIVE_PRECONDITION)

    def test_same_time_bad_observation_invalidates_baseline_candidate(self) -> None:
        observations = stable_baseline() + [
            obs(ObservationKind.DIAGNOSTIC, 2.0, node="autonomous_emergency_braking", task="aeb_emergency_stop", level="WARN"),
            injection(),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.INCONCLUSIVE_PRECONDITION)

    def test_sparse_single_topic_refresh_remains_precondition_inconclusive(self) -> None:
        observations = baseline_snapshot(0.0)
        for time in (0.4, 0.8, 1.2, 1.6, 2.0):
            observations.append(obs(ObservationKind.DIAGNOSTIC, time, node="autonomous_emergency_braking", task="aeb_emergency_stop", level="OK"))

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.INCONCLUSIVE_PRECONDITION)

    def test_startup_transient_is_rejected_and_exact_baseline_must_hold_for_duration(self) -> None:
        observations: list[Observation] = []
        observations += baseline_snapshot(0.0, diagnostic="WARN")
        for time in (1.0, 1.4, 1.8, 2.2, 2.6, 3.0):
            observations += baseline_snapshot(time)
        observations.append(obs(ObservationKind.TARGET_PUBLICATION, 3.1, identity="target-1", frame="map", x=6.0, y=0.0, yaw_rad=0.0))

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)  # chain is intentionally absent
        self.assertEqual(result.details["baseline_stable_at_s"], 3.0)
        self.assertNotEqual(result.details["baseline_stable_at_s"], 2.0)
        self.assertIn("baseline_candidate_start:/diagnostics", [event.label for event in result.accepted_events])
        self.assertIn("baseline_final_support:/diagnostics", [event.label for event in result.accepted_events])


class ValidationAndImmutabilityTests(unittest.TestCase):
    def test_malformed_event_references_and_manufactured_results_are_rejected(self) -> None:
        malformed_references = (
            lambda: EventReference("", 0, ObservationKind.ODOMETRY, 1.0, None, None),
            lambda: EventReference("label", True, ObservationKind.ODOMETRY, 1.0, None, None),
            lambda: EventReference("label", -1, ObservationKind.ODOMETRY, 1.0, None, None),
            lambda: EventReference("label", 0, "odometry", 1.0, None, None),
            lambda: EventReference("label", 0, ObservationKind.ODOMETRY, float("nan"), None, None),
            lambda: EventReference("label", 0, ObservationKind.ODOMETRY, 1.0, "", None),
            lambda: EventReference("label", 0, ObservationKind.ODOMETRY, 1.0, None, "not-utc"),
        )
        for call in malformed_references:
            with self.subTest(call=call), self.assertRaises((TypeError, ValueError)):
                call()

        with self.assertRaises((TypeError, PermissionError)):
            EvaluationResult(Outcome.PASS_OBSERVED_CHAIN, (), ("manufactured",), {})

    def test_enum_like_payload_vocabularies_are_closed(self) -> None:
        invalid = (
            lambda: obs(ObservationKind.DIAGNOSTIC, 1.0, node="n", task="t", level="BROKEN"),
            lambda: obs(ObservationKind.MRM_STATE, 1.0, state="GARBAGE", behavior="NONE"),
            lambda: obs(ObservationKind.MRM_STATE, 1.0, state="NORMAL", behavior="BRAKE"),
            lambda: obs(ObservationKind.EMERGENCY_OPERATOR_STATUS, 1.0, state="GARBAGE"),
            lambda: obs(ObservationKind.GATE_COMMAND, 1.0, path="other", acceleration_mps2=0.0),
        )
        for call in invalid:
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()

    def test_non_operating_valid_mrm_state_cannot_pass_transition(self) -> None:
        observations = stable_baseline() + [
            injection(),
            intervention(2.2),
            obs(ObservationKind.AUTONOMOUS_AVAILABILITY, 2.3, available=False),
            obs(ObservationKind.MRM_STATE, 2.4, state="MRM_SUCCEEDED", behavior="EMERGENCY_STOP"),
            obs(ObservationKind.MRM_STATE, 2.5, state="MRM_OPERATING", behavior="EMERGENCY_STOP"),
        ]

        result = evaluate_scenario(CONFIG, observations)

        self.assertEqual(result.outcome, Outcome.FAIL_SCENARIO)
        self.assertEqual(result.details["failed_event"], "mrm_emergency_stop")

    def test_malformed_numbers_boole_timestamps_and_payloads_are_rejected(self) -> None:
        invalid_calls = (
            lambda: Observation(ObservationKind.ODOMETRY, {"speed_mps": True, "acceleration_mps2": 0.0}, 1.0),
            lambda: Observation(ObservationKind.ODOMETRY, {"speed_mps": float("nan"), "acceleration_mps2": 0.0}, 1.0),
            lambda: Observation(ObservationKind.AUTONOMOUS_AVAILABILITY, {"available": 1}, 1.0),
            lambda: Observation(ObservationKind.AUTONOMOUS_AVAILABILITY, {"available": True, "extra": False}, 1.0),
            lambda: Observation(ObservationKind.AUTONOMOUS_AVAILABILITY, {"available": True}, -0.1),
            lambda: Observation(ObservationKind.AUTONOMOUS_AVAILABILITY, {"available": True}, float("inf")),
            lambda: Observation(ObservationKind.AUTONOMOUS_AVAILABILITY, {"available": True}, 1.0, host_utc="not-a-time"),
        )
        for call in invalid_calls:
            with self.subTest(call=call), self.assertRaises((TypeError, ValueError)):
                call()

    def test_observation_payload_and_result_are_deeply_immutable(self) -> None:
        payload = {"available": True}
        observation = Observation(ObservationKind.AUTONOMOUS_AVAILABILITY, payload, 1.0)
        payload["available"] = False
        self.assertIs(observation.payload["available"], True)
        with self.assertRaises(TypeError):
            observation.payload["available"] = False  # type: ignore[index]
        with self.assertRaises((AttributeError, TypeError)):
            observation.receipt_monotonic_s = 2.0  # type: ignore[misc]
        result = evaluate_scenario(CONFIG, [])
        with self.assertRaises(TypeError):
            result.details["outcome"] = "pass_observed_chain"  # type: ignore[index]
        with self.assertRaises((AttributeError, TypeError)):
            result.outcome = Outcome.PASS_OBSERVED_CHAIN  # type: ignore[misc]

    def test_explicit_operator_abort_has_closed_aborted_outcome(self) -> None:
        observations = baseline_snapshot(0.0) + [obs(ObservationKind.OPERATOR_ABORT, 0.1, reason="operator requested stop")]
        self.assertEqual(evaluate_scenario(CONFIG, observations).outcome, Outcome.ABORTED)


if __name__ == "__main__":
    unittest.main()
