"""Pure tests for INC-AEBS-009E non-activation matrix evidence pipeline.

These tests verify the closed-contract, fail-closed, source-bound, and
compliance-withheld properties of the 009E non-activation matrix evaluator
and evidence pipeline without requiring a live runtime or retained evidence.
"""

from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_ROOT = REPO_ROOT / "implementation" / "aebs-autoware-nominal-vehicle-target-bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"

for path in (REPO_ROOT, SCRIPTS_ROOT, PACKAGE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from de4sdv_aebs_009b_bench.non_activation_matrix import (
    MatrixConfig,
    NonActivationMatrixContract,
    NonActivationOutcome,
    NonActivationScenario,
    NonActivationScenarioResult,
    evaluate_non_activation_scenario,
    evaluate_profile,
    load_matrix_contract,
    non_activation_result_to_json,
    terminal_non_activation_result,
)
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind
from evidence_document import CLOCK_BOUNDARY, canonical_json_bytes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SOURCE_STAMP = "1700000000.000000000"


def _graph_payload() -> dict:
    return {
        "nominal_publisher_count": 1.0,
        "nominal_publishers": "/:de4sdv_aebs_coordinator",
        "mrm_publisher_count": 0.0,
        "mrm_publishers": "none",
    }


def _graph_observation(receipt_s: float) -> Observation:
    return Observation(
        kind=ObservationKind.RUNTIME_GRAPH,
        payload=_graph_payload(),
        receipt_monotonic_s=receipt_s,
        source_stamp=_SOURCE_STAMP,
    )


def _passing_observations() -> list[Observation]:
    """Nine graph observations from t=0.0 to t=4.0, every 0.5 s."""
    return [_graph_observation(t) for t in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)]


def _contract() -> NonActivationMatrixContract:
    return NonActivationMatrixContract(
        observation_duration_s=4.0,
        sample_max_gap_s=0.75,
        required_input_max_age_s=0.5,
    )


def _load_matrix() -> MatrixConfig:
    return load_matrix_contract(
        BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml"
    )


_WINDOW_END = 4.5


# ---------------------------------------------------------------------------
# Matrix config loading tests
# ---------------------------------------------------------------------------


class TestNonActivationMatrixConfig:
    def test_loads_closed_four_scenario_matrix(self) -> None:
        matrix = _load_matrix()
        assert matrix.graph_sampling_max_gap_s == 1.0
        assert matrix.expected_nominal_publisher == "/:de4sdv_aebs_coordinator"
        assert set(matrix.scenarios) == set(NonActivationScenario)
        for scenario in NonActivationScenario:
            entry = matrix.scenarios[scenario]
            assert entry.expected_outcome is NonActivationOutcome.PASS_BOUNDED_SILENCE
            assert entry.scenario_id.startswith("SCN-AEBS-009E-")

    def test_contract_values_match_config(self) -> None:
        matrix = _load_matrix()
        c = matrix.contract
        assert c.observation_duration_s == 4.0
        assert c.sample_max_gap_s == 0.75
        assert c.required_input_max_age_s == 0.5
        assert c.diagnostic_node == "autonomous_emergency_braking"
        assert c.diagnostic_task == "aeb_emergency_stop"
        assert c.diagnostic_level == "OK"

    def test_scenario_config_paths_match_closed_mapping(self) -> None:
        matrix = _load_matrix()
        expected = {
            NonActivationScenario.CLEAR_PATH: "config/scenario-009e-clear-path.yaml",
            NonActivationScenario.ADJACENT_OBJECT: "config/scenario-009e-adjacent-object.yaml",
            NonActivationScenario.NON_CLOSING_TARGET: "config/scenario-009e-non-closing-target.yaml",
            NonActivationScenario.BELOW_TRIGGER: "config/scenario-009e-below-trigger.yaml",
        }
        for scenario, path in expected.items():
            assert matrix.scenarios[scenario].scenario_config == path

    def test_rejects_open_root_contract(self) -> None:
        import yaml
        path = BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw["extra_field"] = "bad"
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="closed contract"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_rejects_missing_scenario(self) -> None:
        import yaml
        path = BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        # Remove one scenario entry
        raw["scenarios"] = raw["scenarios"][:3]
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="exactly once"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_rejects_wrong_outcome_for_profile(self) -> None:
        import yaml
        path = BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw["scenarios"][0]["expected_outcome"] = "fail_unexpected_activation"
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="contradicts"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_contract_rejects_non_positive_duration(self) -> None:
        with pytest.raises(ValueError, match="finite and positive"):
            NonActivationMatrixContract(
                observation_duration_s=0.0,
                sample_max_gap_s=0.75,
                required_input_max_age_s=0.5,
            )

    def test_contract_rejects_non_number_duration(self) -> None:
        with pytest.raises(TypeError, match="must be a number"):
            NonActivationMatrixContract(
                observation_duration_s="bad",
                sample_max_gap_s=0.75,
                required_input_max_age_s=0.5,
            )


# ---------------------------------------------------------------------------
# Evaluator contract tests
# ---------------------------------------------------------------------------


class TestNonActivationEvaluator:
    def test_clear_path_passes_bounded_silence(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            _passing_observations(),
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is True
        assert result.outcome is NonActivationOutcome.PASS_BOUNDED_SILENCE
        assert result.scenario is NonActivationScenario.CLEAR_PATH
        assert result.warning_observation_index is None
        assert result.intervention_observation_index is None
        assert result.braking_request_observation_index is None

    def test_adjacent_object_passes_bounded_silence(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.ADJACENT_OBJECT,
            _passing_observations(),
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is True
        assert result.outcome is NonActivationOutcome.PASS_BOUNDED_SILENCE
        assert result.scenario is NonActivationScenario.ADJACENT_OBJECT

    def test_non_closing_target_passes_bounded_silence(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.NON_CLOSING_TARGET,
            _passing_observations(),
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is True
        assert result.outcome is NonActivationOutcome.PASS_BOUNDED_SILENCE
        assert result.scenario is NonActivationScenario.NON_CLOSING_TARGET

    def test_below_trigger_passes_bounded_silence(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.BELOW_TRIGGER,
            _passing_observations(),
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is True
        assert result.outcome is NonActivationOutcome.PASS_BOUNDED_SILENCE
        assert result.scenario is NonActivationScenario.BELOW_TRIGGER

    def test_warning_activation_fails(self) -> None:
        obs = list(_passing_observations())
        obs.insert(
            2,
            Observation(
                kind=ObservationKind.WARNING_REQUEST,
                payload={"active": True},
                receipt_monotonic_s=1.0,
                source_stamp=_SOURCE_STAMP,
            ),
        )
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION
        assert result.warning_observation_index == 2

    def test_intervention_fails(self) -> None:
        obs = list(_passing_observations())
        obs.insert(
            3,
            Observation(
                kind=ObservationKind.AEB_INTERVENTION,
                payload={
                    "node": "autonomous_emergency_braking",
                    "task": "aeb_emergency_stop",
                    "level": "ERROR",
                    "message": "[AEB]: Emergency Brake",
                    "rss_distance_m": 5.0,
                    "object_distance_m": 3.0,
                    "object_speed_mps": 1.5,
                },
                receipt_monotonic_s=1.5,
                source_stamp=_SOURCE_STAMP,
            ),
        )
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION
        assert result.intervention_observation_index == 3

    def test_braking_request_fails(self) -> None:
        obs = list(_passing_observations())
        obs.insert(
            4,
            Observation(
                kind=ObservationKind.BRAKING_REQUEST,
                payload={"speed_mps": 0.0, "acceleration_mps2": -5.0},
                receipt_monotonic_s=2.0,
                source_stamp=_SOURCE_STAMP,
            ),
        )
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION
        assert result.braking_request_observation_index == 4

    def test_error_diagnostic_fails(self) -> None:
        obs = list(_passing_observations())
        obs.insert(
            2,
            Observation(
                kind=ObservationKind.DIAGNOSTIC,
                payload={
                    "node": "autonomous_emergency_braking",
                    "task": "aeb_emergency_stop",
                    "level": "ERROR",
                },
                receipt_monotonic_s=1.0,
                source_stamp=_SOURCE_STAMP,
            ),
        )
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION

    def test_no_observations_is_inconclusive(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            [],
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE

    def test_short_duration_is_inconclusive(self) -> None:
        obs = [_graph_observation(0.0), _graph_observation(0.5)]
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=1.0,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE

    def test_no_runtime_graph_is_inconclusive(self) -> None:
        obs = [
            Observation(
                kind=ObservationKind.COORDINATION_STATE,
                payload={"state": "armed"},
                receipt_monotonic_s=t,
                source_stamp=_SOURCE_STAMP,
            )
            for t in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)
        ]
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE

    def test_graph_sampling_gap_is_inconclusive(self) -> None:
        obs = [
            _graph_observation(0.0),
            _graph_observation(1.0),  # gap = 1.0 > sample_max_gap_s = 0.75
            _graph_observation(2.0),
        ]
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=4.5,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE

    def test_publisher_contamination_is_inconclusive(self) -> None:
        obs = list(_passing_observations())
        bad = dict(_graph_payload())
        bad["mrm_publisher_count"] = 1.0
        obs[3] = Observation(
            kind=ObservationKind.RUNTIME_GRAPH,
            payload=bad,
            receipt_monotonic_s=1.5,
            source_stamp=_SOURCE_STAMP,
        )
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE

    def test_stale_terminal_graph_is_inconclusive(self) -> None:
        obs = [_graph_observation(t) for t in (0.0, 0.5, 1.0, 1.5, 2.0)]
        # window_end - last_graph = 4.5 - 2.0 = 2.5 > sample_max_gap_s = 0.75
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=4.5,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE

    def test_result_serialization_round_trips(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            _passing_observations(),
            window_end_receipt_s=_WINDOW_END,
        )
        serialized = non_activation_result_to_json(result)
        assert serialized["scenario"] == "clear_path"
        assert serialized["outcome"] == "pass_bounded_silence"
        assert serialized["passed"] is True
        assert "reason" in serialized
        assert serialized["warning_observation_index"] is None
        assert serialized["intervention_observation_index"] is None
        assert serialized["braking_request_observation_index"] is None

    def test_terminal_policy_pass(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            _passing_observations(),
            window_end_receipt_s=_WINDOW_END,
        )
        assert terminal_non_activation_result(result) == "pass_bounded_silence"

    def test_terminal_policy_inconclusive_keeps_collecting(self) -> None:
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            [],
            window_end_receipt_s=_WINDOW_END,
        )
        assert terminal_non_activation_result(result) is None

    def test_terminal_policy_failure(self) -> None:
        obs = list(_passing_observations())
        obs.insert(
            0,
            Observation(
                kind=ObservationKind.WARNING_REQUEST,
                payload={"active": True},
                receipt_monotonic_s=0.0,
                source_stamp=_SOURCE_STAMP,
            ),
        )
        result = evaluate_non_activation_scenario(
            _contract(),
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert terminal_non_activation_result(result) == "terminal_non_activation_failure"


# ---------------------------------------------------------------------------
# Evaluate-profile (runtime policy) tests
# ---------------------------------------------------------------------------


class TestEvaluateProfile:
    def test_all_four_profiles_pass_via_evaluate_profile(self) -> None:
        matrix = _load_matrix()
        for scenario in NonActivationScenario:
            result = evaluate_profile(
                matrix,
                scenario,
                _passing_observations(),
                window_end_receipt_s=_WINDOW_END,
            )
            assert result.passed is True
            assert result.outcome is NonActivationOutcome.PASS_BOUNDED_SILENCE

    def test_evaluate_profile_rejects_publisher_contamination(self) -> None:
        matrix = _load_matrix()
        obs = list(_passing_observations())
        bad = dict(_graph_payload())
        bad["nominal_publishers"] = "wrong_publisher"
        obs[3] = Observation(
            kind=ObservationKind.RUNTIME_GRAPH,
            payload=bad,
            receipt_monotonic_s=1.5,
            source_stamp=_SOURCE_STAMP,
        )
        result = evaluate_profile(
            matrix,
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.ERROR_EVIDENCE

    def test_evaluate_profile_rejects_mrm_publishers_contamination(self) -> None:
        matrix = _load_matrix()
        obs = list(_passing_observations())
        bad = dict(_graph_payload())
        bad["mrm_publishers"] = "some_mrm"
        obs[3] = Observation(
            kind=ObservationKind.RUNTIME_GRAPH,
            payload=bad,
            receipt_monotonic_s=1.5,
            source_stamp=_SOURCE_STAMP,
        )
        result = evaluate_profile(
            matrix,
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.ERROR_EVIDENCE

    def test_evaluate_profile_rejects_graph_gap(self) -> None:
        matrix = _load_matrix()
        obs = [
            _graph_observation(0.0),
            _graph_observation(2.0),  # gap = 2.0 > graph_sampling_max_gap_s = 1.0
            _graph_observation(3.0),
            _graph_observation(4.0),
        ]
        result = evaluate_profile(
            matrix,
            NonActivationScenario.CLEAR_PATH,
            obs,
            window_end_receipt_s=_WINDOW_END,
        )
        assert result.passed is False
        assert result.outcome is NonActivationOutcome.ERROR_EVIDENCE


# ---------------------------------------------------------------------------
# Evidence builder tests
# ---------------------------------------------------------------------------


def _obs_to_json(observations: list[Observation]) -> list[dict]:
    from evidence_document import observation_to_json
    return [observation_to_json(item) for item in observations]


def _make_raw(
    observations: list[Observation],
    profile: NonActivationScenario,
) -> dict:
    matrix = _load_matrix()
    result = evaluate_profile(
        matrix,
        profile,
        observations,
        window_end_receipt_s=_WINDOW_END,
    )
    serialized = non_activation_result_to_json(result)
    return {
        "collector_id": "de4sdv.scenario_observer.v1",
        "monotonic_start_s": 0.0,
        "monotonic_end_s": _WINDOW_END,
        "clock_boundary": CLOCK_BOUNDARY,
        "observations": _obs_to_json(observations),
        "evaluator_result": serialized,
        "activation": {
            "request_time_s": 1.0,
            "response_time_s": 1.5,
            "status": "succeeded",
            "response_message": "ok",
        },
        "errors": [],
        "terminal_reason": "pass_bounded_silence",
        "command_exit": 0,
        "limits": {
            "timeout_s": 45.0,
            "deadline_s": 45.0,
            "observation_cap": min(100_000, max(1_000, math.ceil(45.0 * 1_000))),
            "error_cap": 256,
        },
        "non_activation_profile": profile.value,
    }


def _make_provenance(bench_root: Path, profile: str) -> dict:
    from validate_scenario_evidence import _live_provenance_fields
    from execution_identity import non_activation_execution_manifest_sha256
    from evidence_document import sha256_file

    value = _live_provenance_fields(bench_root)
    head = value.pop("repository_head")
    value["captured_utc"] = "2026-07-28T10:00:00Z"
    value["command_exit_code"] = 0
    value["non_activation_profile"] = profile
    value["non_activation_execution_manifest_sha256"] = (
        non_activation_execution_manifest_sha256(bench_root, profile)
    )
    value["non_activation_matrix_sha256"] = sha256_file(
        bench_root / "config" / "scenario-009e-non-activation-matrix.yaml"
    )
    value["repository_head"] = head
    return value


def _make_map_runtime(bench_root: Path) -> dict:
    from validate_scenario_evidence import _live_provenance_fields
    from execution_identity import execution_manifest_sha256
    from evidence_document import sha256_file
    import yaml

    value = _live_provenance_fields(bench_root)
    lock = yaml.safe_load((bench_root / "runtime-lock.yaml").read_text(encoding="utf-8"))
    return {
        "command_exit_status": 0,
        "error": None,
        "execution_manifest_sha256": execution_manifest_sha256(bench_root),
        "extracted_sha256": lock["map"]["extracted_sha256"],
        "host_architecture": value["host_arch"],
        "image_digest": value["image_digest"],
        "image_id": lock["container"]["index_digest"],
        "lock_sha256": value["runtime_lock_sha256"],
        "map_files_verified": True,
        "map_sha256": value["map_digest"].removeprefix("sha256:"),
        "repository_head": value["repository_head"],
        "utc_time": "2026-07-28T10:00:00Z",
    }


def _make_artifacts(
    bench_root: Path, profile: str, run_id: str, raw: dict
) -> tuple[dict, Path]:
    import hashlib

    evidence_dir = bench_root / "evidence" / "009e" / "test_fixtures" / profile / run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_path = evidence_dir / "observer-raw.json"
    raw_path.write_text(canonical_json_bytes(raw).decode("utf-8"), encoding="utf-8")
    metadata_path = evidence_dir / "run-metadata.json"
    metadata = {
        "observer_exit_code": 0,
        "raw_output": str(raw_path.relative_to(bench_root)),
        "non_activation_profile": profile,
    }
    metadata_path.write_text(canonical_json_bytes(metadata).decode("utf-8"), encoding="utf-8")
    log_path = evidence_dir / "observer.log"
    log_path.write_text("test log\n", encoding="utf-8")
    launch_path = evidence_dir / "launch.log"
    launch_path.write_text("test launch\n", encoding="utf-8")
    map_path = evidence_dir / "map-runtime.json"
    map_content = _make_map_runtime(bench_root)
    map_path.write_text(canonical_json_bytes(map_content).decode("utf-8"), encoding="utf-8")
    artifacts = {}
    for name, path in (
        ("observer_raw", raw_path),
        ("observer_log", log_path),
        ("launch_log", launch_path),
        ("run_metadata", metadata_path),
        ("map_runtime", map_path),
    ):
        rel = str(path.relative_to(bench_root))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        artifacts[name] = {"path": rel, "sha256": sha}
    return artifacts, evidence_dir


class TestNonActivationEvidenceBuilder:
    def test_builds_a_closed_evidence_document(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-build-001", raw
        )
        try:
            document = build_non_activation_evidence(
                raw,
                profile,
                _make_provenance(BENCH_ROOT, profile.value),
                artifacts,
                matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
            )
            assert document["schema"] == "de4sdv.aebs-009e.non-activation-evidence.v1"
            assert document["increment_id"] == "INC-AEBS-009E"
            assert document["profile"] == "clear_path"
            assert document["scenario_id"] == "SCN-AEBS-009E-CLEAR-PATH-001"
            assert document["evaluation"]["outcome"] == "pass_bounded_silence"
            assert document["evaluation"]["passed"] is True
            assert "no_safety_or_compliance_claim" in document["claim_boundary"]
            assert "collection" in document
            assert "collector_contract" in document
            assert "artifacts" in document
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)

    def test_builds_all_four_profiles(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        for profile in NonActivationScenario:
            raw = _make_raw(_passing_observations(), profile)
            artifacts, _ = _make_artifacts(
                BENCH_ROOT, profile.value, f"test-build-{profile.value}", raw
            )
            try:
                document = build_non_activation_evidence(
                    raw,
                    profile,
                    _make_provenance(BENCH_ROOT, profile.value),
                    artifacts,
                    matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
                )
                assert document["profile"] == profile.value
                assert document["evaluation"]["outcome"] == "pass_bounded_silence"
            finally:
                shutil.rmtree(
                    BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True
                )

    def test_rejects_profile_mismatch(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        raw["non_activation_profile"] = "adjacent_object"
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-mismatch-001", raw
        )
        try:
            with pytest.raises(ValueError, match="differs from selected profile"):
                build_non_activation_evidence(
                    raw,
                    profile,
                    _make_provenance(BENCH_ROOT, profile.value),
                    artifacts,
                    matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)

    def test_rejects_tampered_evaluator_result(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        raw["evaluator_result"]["reason"] = "tampered"
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-tamper-001", raw
        )
        try:
            with pytest.raises(ValueError, match="differs from independent replay"):
                build_non_activation_evidence(
                    raw,
                    profile,
                    _make_provenance(BENCH_ROOT, profile.value),
                    artifacts,
                    matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)

    def test_rejects_open_raw_contract(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        raw["invented_field"] = "bad"
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-open-001", raw
        )
        try:
            with pytest.raises(ValueError, match="do not match the closed contract"):
                build_non_activation_evidence(
                    raw,
                    profile,
                    _make_provenance(BENCH_ROOT, profile.value),
                    artifacts,
                    matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)

    def test_rejects_non_passing_terminal(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        raw["terminal_reason"] = "timeout"
        raw["command_exit"] = 1
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-terminal-001", raw
        )
        try:
            with pytest.raises(ValueError):
                build_non_activation_evidence(
                    raw,
                    profile,
                    _make_provenance(BENCH_ROOT, profile.value),
                    artifacts,
                    matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)


# ---------------------------------------------------------------------------
# Evidence shape tests
# ---------------------------------------------------------------------------


class TestNonActivationEvidenceShape:
    def test_evidence_root_has_exactly_closed_keys(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-shape-001", raw
        )
        try:
            document = build_non_activation_evidence(
                raw,
                profile,
                _make_provenance(BENCH_ROOT, profile.value),
                artifacts,
                matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
            )
            expected = {
                "schema", "increment_id", "profile", "scenario_id",
                "provenance", "collection", "collector_contract",
                "evaluation", "artifacts", "claim_boundary",
            }
            assert set(document) == expected
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)

    def test_evaluation_is_source_bound_not_trust_promoted(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        obs = _passing_observations()
        raw = _make_raw(obs, profile)
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-bound-001", raw
        )
        try:
            document = build_non_activation_evidence(
                raw,
                profile,
                _make_provenance(BENCH_ROOT, profile.value),
                artifacts,
                matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
            )
            matrix = _load_matrix()
            expected = non_activation_result_to_json(
                evaluate_profile(
                    matrix,
                    profile,
                    obs,
                    window_end_receipt_s=_WINDOW_END,
                )
            )
            assert canonical_json_bytes(document["evaluation"]) == canonical_json_bytes(expected)
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)

    def test_claim_boundary_is_explicit_and_compliance_withheld(self) -> None:
        from non_activation_evidence import build_non_activation_evidence

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        artifacts, _ = _make_artifacts(
            BENCH_ROOT, profile.value, "test-claim-001", raw
        )
        try:
            document = build_non_activation_evidence(
                raw,
                profile,
                _make_provenance(BENCH_ROOT, profile.value),
                artifacts,
                matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
            )
            assert "no_safety_or_compliance_claim" in document["claim_boundary"]
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)
