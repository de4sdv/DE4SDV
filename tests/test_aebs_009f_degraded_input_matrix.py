"""Pure tests for INC-AEBS-009F degraded-input matrix evidence pipeline.

These tests verify the closed-contract, fail-closed, source-bound, and
compliance-withheld properties of the 009F degraded-input matrix evidence
pipeline without requiring a live runtime or retained evidence files.
"""

from __future__ import annotations

import hashlib
import math
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_ROOT = REPO_ROOT / "implementation" / "aebs-autoware-nominal-vehicle-target-bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
FRAMEWORK_ROOT = REPO_ROOT / "implementation" / "aebs-bench-framework"

for path in (REPO_ROOT, SCRIPTS_ROOT, PACKAGE_ROOT, FRAMEWORK_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_pipeline import build_evidence, load_contract
from de4sdv_aebs_009b_bench.degraded_input_matrix import (
    DegradedInputAuthorization,
    DegradedInputDisposition,
    DegradedInputMatrixContract,
    DegradedInputScenario,
    DegradedInputScenarioResult,
    degraded_input_result_to_json,
    evaluate_degraded_input_scenario,
    evaluate_profile,
    load_matrix_contract,
    terminal_degraded_input_result,
)
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind
from evidence_document import CLOCK_BOUNDARY, canonical_json_bytes

CONFIG_PATH = BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEGRADED_STAMP = "1700000000.000000000"
_AUTH_STAMP = "1700000000.300000000"
_AFFECTED_TOPIC = "/perception/object_recognition/objects"
_NOMINAL_PUBLISHER = "/:de4sdv_aebs_coordinator"

_HEALTH_BY_PROFILE = {
    DegradedInputScenario.STALE_INPUT: "stale",
    DegradedInputScenario.MISSING_INPUT: "missing",
    DegradedInputScenario.MALFORMED_INPUT: "malformed",
    DegradedInputScenario.INCONSISTENT_INPUT: "inconsistent",
    DegradedInputScenario.UNAVAILABLE_INPUT: "unavailable",
}


def _contract() -> DegradedInputMatrixContract:
    return DegradedInputMatrixContract(
        degraded_state_max_age_s=0.2,
        closed_detection_window_s=0.25,
        diagnostic_node="autonomous_emergency_braking",
        diagnostic_task="aeb_emergency_stop",
        diagnostic_level="ERROR",
        diagnostic_message="[AEB]: Emergency Brake",
    )


def _authorization(
    scenario: DegradedInputScenario = DegradedInputScenario.STALE_INPUT,
    disposition: str = DegradedInputDisposition.PASS_BOUNDED_DETECTION.value,
) -> DegradedInputAuthorization:
    return DegradedInputAuthorization(
        degraded_input_profile=scenario.value,
        affected_topic=_AFFECTED_TOPIC,
        input_health=_HEALTH_BY_PROFILE[scenario],
        degraded_state_source_stamp=_DEGRADED_STAMP,
        authorization_diagnostic_source_stamp=_AUTH_STAMP,
        disposition=disposition,
    )


def _auth_observation(
    scenario: DegradedInputScenario = DegradedInputScenario.STALE_INPUT,
    disposition: str = DegradedInputDisposition.PASS_BOUNDED_DETECTION.value,
    receipt: float = 0.0,
) -> Observation:
    return Observation(
        kind=ObservationKind.DEGRADED_INPUT_AUTHORIZATION,
        payload={
            "degraded_input_profile": scenario.value,
            "affected_topic": _AFFECTED_TOPIC,
            "input_health": _HEALTH_BY_PROFILE[scenario],
            "degraded_state_source_stamp": _DEGRADED_STAMP,
            "authorization_diagnostic_source_stamp": _AUTH_STAMP,
            "disposition": disposition,
        },
        receipt_monotonic_s=receipt,
        source_stamp=_AUTH_STAMP,
    )


def _transition_observation(
    scenario: DegradedInputScenario = DegradedInputScenario.STALE_INPUT,
    receipt: float = 0.5,
    previous_state: str = "nominal",
    current_state: str = "degraded",
) -> Observation:
    return Observation(
        kind=ObservationKind.DEGRADED_STATE_TRANSITION,
        payload={
            "affected_topic": _AFFECTED_TOPIC,
            "input_health": _HEALTH_BY_PROFILE[scenario],
            "degraded_state_source_stamp": _DEGRADED_STAMP,
            "previous_state": previous_state,
            "current_state": current_state,
        },
        receipt_monotonic_s=receipt,
        source_stamp=_DEGRADED_STAMP,
    )


def _status_observation(
    receipt: float = 0.6,
    status: str = "degraded",
    indicated_degraded: bool = True,
) -> Observation:
    return Observation(
        kind=ObservationKind.DEGRADED_STATUS_INDICATION,
        payload={
            "affected_topic": _AFFECTED_TOPIC,
            "status": status,
            "indicated_degraded": indicated_degraded,
        },
        receipt_monotonic_s=receipt,
        source_stamp=_DEGRADED_STAMP,
    )


def _graph_observation(receipt: float) -> Observation:
    return Observation(
        kind=ObservationKind.RUNTIME_GRAPH,
        payload={
            "nominal_publisher_count": 1.0,
            "nominal_publishers": _NOMINAL_PUBLISHER,
            "mrm_publisher_count": 0.0,
            "mrm_publishers": "none",
        },
        receipt_monotonic_s=receipt,
        source_stamp=None,
    )


def _graph_observations(
    window_end: float = 1.0, gap: float = 0.1
) -> list[Observation]:
    """Graph observations covering [0, window_end] with no gap > graph_sampling_max_gap_s."""
    # Use gap well below the 0.2 max to avoid floating-point noise pushing
    # consecutive differences above graph_sampling_max_gap_s.
    count = int(window_end / gap) + 1
    points = [round(i * gap, 10) for i in range(count)]
    if points[-1] < window_end - 1e-9:
        points.append(round(window_end, 10))
    return [_graph_observation(t) for t in points]


def _observations(
    scenario: DegradedInputScenario = DegradedInputScenario.STALE_INPUT,
    *,
    window_end: float = 1.0,
    include_auth: bool = True,
    include_transition: bool = True,
    include_status: bool = True,
    include_graph: bool = True,
    auth_disposition: str = DegradedInputDisposition.PASS_BOUNDED_DETECTION.value,
    transition_previous: str = "nominal",
    transition_current: str = "degraded",
    status_value: str = "degraded",
    indicated_degraded: bool = True,
) -> list[Observation]:
    obs: list[Observation] = []
    if include_graph:
        obs.extend(_graph_observations(window_end))
    if include_auth:
        obs.append(_auth_observation(scenario, disposition=auth_disposition, receipt=0.0))
    if include_transition:
        obs.append(
            _transition_observation(
                scenario,
                receipt=0.5,
                previous_state=transition_previous,
                current_state=transition_current,
            )
        )
    if include_status:
        obs.append(
            _status_observation(
                receipt=0.6, status=status_value, indicated_degraded=indicated_degraded
            )
        )
    obs.sort(key=lambda o: o.receipt_monotonic_s)
    return obs


def _matrix():
    return load_matrix_contract(CONFIG_PATH)



def build_degraded_input_evidence(
    raw,
    config_path,
    provenance,
    artifacts,
    *,
    profile,
    bench_root=BENCH_ROOT,
):
    contract = load_contract(BENCH_ROOT / "config" / "contract-009f.yaml")
    if isinstance(profile, str):
        profile = DegradedInputScenario(profile)
    return build_evidence(
        raw,
        profile,
        provenance,
        artifacts,
        contract=contract,
        bench_root=bench_root,
    )


def _obs_to_json(observations: list[Observation]) -> list[dict]:
    from evidence_document import observation_to_json
    return [observation_to_json(item) for item in observations]


def _make_raw(
    observations: list[Observation],
    profile: DegradedInputScenario,
    matrix=None,
) -> dict:
    if matrix is None:
        matrix = _matrix()
    result = evaluate_profile(
        matrix,
        profile,
        observations,
        window_end_receipt_s=1.0,
    )
    serialized = degraded_input_result_to_json(result)
    return {
        "collector_id": "de4sdv.scenario_observer.v1",
        "monotonic_start_s": 0.0,
        "monotonic_end_s": 1.0,
        "clock_boundary": CLOCK_BOUNDARY,
        "observations": _obs_to_json(observations),
        "evaluator_result": serialized,
        "activation": {
            "request_time_s": 0.1,
            "response_time_s": 0.15,
            "status": "succeeded",
            "response_message": "ok",
        },
        "errors": [],
        "terminal_reason": "pass_degraded_input_profile",
        "command_exit": 0,
        "limits": {
            "timeout_s": 45.0,
            "deadline_s": 45.0,
            "observation_cap": min(100_000, max(1_000, math.ceil(45.0 * 1_000))),
            "error_cap": 256,
        },
        "degraded_input_profile": profile.value,
    }


def _make_provenance(bench_root: Path) -> dict:
    from validate_scenario_evidence import _live_provenance_fields
    from execution_identity import execution_manifest_sha256
    from evidence_document import sha256_file

    value = _live_provenance_fields(bench_root)
    head = value.pop("repository_head")
    value["captured_utc"] = "2026-07-28T10:00:00Z"
    value["command_exit_code"] = 0
    value["execution_manifest_sha256"] = execution_manifest_sha256(bench_root)
    value["degraded_input_config_sha256"] = sha256_file(
        bench_root / "config" / "scenario-009f-degraded-input-matrix.yaml"
    )
    value["repository_head"] = head
    return value


def _make_map_runtime(bench_root: Path) -> dict:
    from validate_scenario_evidence import _live_provenance_fields
    from execution_identity import execution_manifest_sha256
    from evidence_document import sha256_file

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


def _make_artifacts(bench_root: Path, profile: str, run_id: str, raw: dict) -> tuple[dict, Path]:
    evidence_dir = bench_root / "evidence" / "009f" / profile / "test_fixtures" / run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_path = evidence_dir / "observer-raw.json"
    raw_path.write_text(canonical_json_bytes(raw).decode("utf-8"), encoding="utf-8")
    metadata_path = evidence_dir / "run-metadata.json"
    metadata = {"observer_exit_code": 0, "raw_output": str(raw_path.relative_to(bench_root))}
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


def _cleanup_fixtures(bench_root: Path, profile: str) -> None:
    shutil.rmtree(
        bench_root / "evidence" / "009f" / profile / "test_fixtures",
        ignore_errors=True,
    )


# ---------------------------------------------------------------------------
# Config loading tests
# ---------------------------------------------------------------------------

class TestDegradedInputMatrixConfig:
    def test_loads_all_five_profiles(self) -> None:
        matrix = load_matrix_contract(CONFIG_PATH)
        assert set(matrix.scenarios) == set(DegradedInputScenario)
        for scenario in DegradedInputScenario:
            entry = matrix.scenarios[scenario]
            assert entry.expected_disposition is DegradedInputDisposition.PASS_BOUNDED_DETECTION
            assert entry.expected_input_health == _HEALTH_BY_PROFILE[scenario]
            assert entry.scenario_id.startswith("SCN-AEBS-009F-")

    def test_contract_fields_match_config(self) -> None:
        matrix = load_matrix_contract(CONFIG_PATH)
        assert matrix.contract.degraded_state_max_age_s == 0.2
        assert matrix.contract.closed_detection_window_s == 0.25
        assert matrix.graph_sampling_max_gap_s == 0.2
        assert matrix.expected_nominal_publisher == _NOMINAL_PUBLISHER

    def test_rejects_unknown_schema(self) -> None:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        raw["schema"] = "de4sdv.unknown.v1"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="identity or inherited runtime"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_rejects_open_root_contract(self) -> None:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        raw["invented_key"] = "bad"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="root does not match the closed contract"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_rejects_duplicate_profile(self) -> None:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        # Duplicate the stale_input entry
        stale_entry = next(e for e in raw["scenarios"] if e["profile"] == "stale_input")
        raw["scenarios"].append(dict(stale_entry))
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="must occur exactly once"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_rejects_missing_profile(self) -> None:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        raw["scenarios"] = [e for e in raw["scenarios"] if e["profile"] != "unavailable_input"]
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="must occur exactly once"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_rejects_wrong_disposition_for_profile(self) -> None:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        entry = next(e for e in raw["scenarios"] if e["profile"] == "stale_input")
        entry["expected_disposition"] = "fail_wrong_disposition"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="contradicts its closed profile"):
                load_matrix_contract(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Pure evaluator (evaluate_degraded_input_scenario) tests
# ---------------------------------------------------------------------------

class TestDegradedInputEvaluator:
    def test_pass_bounded_detection_stale(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        auth = _authorization(scenario)
        transition = _transition_observation(scenario)
        status = _status_observation()
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [transition, status],
            window_end_receipt_s=1.0,
        )
        assert result.passed is True
        assert result.disposition is DegradedInputDisposition.PASS_BOUNDED_DETECTION
        assert result.scenario is scenario
        assert result.transition_observation_index is not None
        assert result.status_observation_index is not None

    def test_pass_bounded_detection_all_five_profiles(self) -> None:
        contract = _contract()
        for scenario in DegradedInputScenario:
            auth = _authorization(scenario)
            transition = _transition_observation(scenario)
            status = _status_observation()
            result = evaluate_degraded_input_scenario(
                contract, scenario, auth, [transition, status],
                window_end_receipt_s=1.0,
            )
            assert result.passed is True, f"{scenario} should pass"
            assert result.disposition is DegradedInputDisposition.PASS_BOUNDED_DETECTION

    def test_missing_transition_is_inconclusive(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        auth = _authorization(scenario)
        status = _status_observation()
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [status],
            window_end_receipt_s=1.0,
        )
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION
        assert "not observed" in result.reason

    def test_wrong_transition_direction_is_fail(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        auth = _authorization(scenario)
        transition = _transition_observation(
            scenario, previous_state="degraded", current_state="nominal"
        )
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [transition],
            window_end_receipt_s=1.0,
        )
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.FAIL_WRONG_DISPOSITION

    def test_missing_status_is_inconclusive(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.MISSING_INPUT
        auth = _authorization(scenario)
        transition = _transition_observation(scenario)
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [transition],
            window_end_receipt_s=1.0,
        )
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION

    def test_window_not_closed_is_inconclusive(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        auth = _authorization(scenario)
        transition = _transition_observation(scenario, receipt=0.5)
        status = _status_observation(receipt=0.6)
        # window_end - status = 0.1 < 0.25 (closed_detection_window_s)
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [transition, status],
            window_end_receipt_s=0.7,
        )
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION
        assert "not closed" in result.reason

    def test_wrong_authorization_disposition_is_fail(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        auth = _authorization(
            scenario, disposition=DegradedInputDisposition.FAIL_WRONG_DISPOSITION.value
        )
        transition = _transition_observation(scenario)
        status = _status_observation()
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [transition, status],
            window_end_receipt_s=1.0,
        )
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.FAIL_WRONG_DISPOSITION

    def test_status_not_degraded_is_inconclusive(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        auth = _authorization(scenario)
        transition = _transition_observation(scenario)
        status = _status_observation(status="nominal", indicated_degraded=False)
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [transition, status],
            window_end_receipt_s=1.0,
        )
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION

    def test_rejects_non_contract_type(self) -> None:
        with pytest.raises(TypeError, match="contract must be"):
            evaluate_degraded_input_scenario(
                "bad", DegradedInputScenario.STALE_INPUT, _authorization(), [],
                window_end_receipt_s=1.0,
            )

    def test_rejects_non_scenario_type(self) -> None:
        with pytest.raises(TypeError, match="scenario must be"):
            evaluate_degraded_input_scenario(
                _contract(), "bad", _authorization(), [],
                window_end_receipt_s=1.0,
            )

    def test_rejects_non_authorization_type(self) -> None:
        with pytest.raises(TypeError, match="authorization must be"):
            evaluate_degraded_input_scenario(
                _contract(), DegradedInputScenario.STALE_INPUT, "bad", [],
                window_end_receipt_s=1.0,
            )

    def test_rejects_negative_window_end(self) -> None:
        with pytest.raises(ValueError, match="finite and nonnegative"):
            evaluate_degraded_input_scenario(
                _contract(), DegradedInputScenario.STALE_INPUT, _authorization(), [],
                window_end_receipt_s=-1.0,
            )

    def test_rejects_non_observation_items(self) -> None:
        with pytest.raises(TypeError, match="observations must contain only"):
            evaluate_degraded_input_scenario(
                _contract(), DegradedInputScenario.STALE_INPUT, _authorization(),
                ["bad"],
                window_end_receipt_s=1.0,
            )


# ---------------------------------------------------------------------------
# evaluate_profile tests (full pipeline including graph)
# ---------------------------------------------------------------------------

class TestEvaluateProfile:
    def test_pass_all_five_profiles(self) -> None:
        matrix = _matrix()
        for scenario in DegradedInputScenario:
            obs = _observations(scenario)
            result = evaluate_profile(
                matrix, scenario, obs, window_end_receipt_s=1.0,
            )
            assert result.passed is True, f"{scenario} should pass"
            assert result.disposition is DegradedInputDisposition.PASS_BOUNDED_DETECTION
            assert result.authorization_observation_index is not None

    def test_missing_authorization_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        obs = _observations(scenario, include_auth=False)
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE

    def test_duplicate_authorization_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        obs = _observations(scenario)
        obs.append(_auth_observation(scenario, receipt=0.05))
        obs.sort(key=lambda o: o.receipt_monotonic_s)
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE

    def test_wrong_input_health_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        # Authorization claims "missing" health but profile is stale_input
        auth = Observation(
            kind=ObservationKind.DEGRADED_INPUT_AUTHORIZATION,
            payload={
                "degraded_input_profile": scenario.value,
                "affected_topic": _AFFECTED_TOPIC,
                "input_health": "missing",
                "degraded_state_source_stamp": _DEGRADED_STAMP,
                "authorization_diagnostic_source_stamp": _AUTH_STAMP,
                "disposition": DegradedInputDisposition.PASS_BOUNDED_DETECTION.value,
            },
            receipt_monotonic_s=0.0,
            source_stamp=_AUTH_STAMP,
        )
        transition = _transition_observation(scenario)
        status = _status_observation()
        graphs = _graph_observations()
        obs = graphs + [auth, transition, status]
        obs.sort(key=lambda o: o.receipt_monotonic_s)
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE

    def test_graph_contamination_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        obs = _observations(scenario)
        # Replace one graph observation with a contaminated one
        for i, o in enumerate(obs):
            if o.kind is ObservationKind.RUNTIME_GRAPH:
                obs[i] = Observation(
                    kind=ObservationKind.RUNTIME_GRAPH,
                    payload={
                        "nominal_publisher_count": 2.0,
                        "nominal_publishers": _NOMINAL_PUBLISHER,
                        "mrm_publisher_count": 0.0,
                        "mrm_publishers": "none",
                    },
                    receipt_monotonic_s=o.receipt_monotonic_s,
                    source_stamp=None,
                )
                break
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE
        assert "contamination" in result.reason

    def test_graph_gap_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        obs = _observations(scenario, include_graph=False)
        # Add graphs with a large gap
        obs.append(_graph_observation(0.0))
        obs.append(_graph_observation(0.8))
        obs.append(_graph_observation(1.0))
        obs.sort(key=lambda o: o.receipt_monotonic_s)
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE
        assert "gap" in result.reason

    def test_graph_missing_terminal_coverage_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        obs = _observations(scenario, include_graph=False)
        # Graphs end at 0.4, but window_end is 1.0 → gap = 0.6 > 0.2
        obs.append(_graph_observation(0.0))
        obs.append(_graph_observation(0.2))
        obs.append(_graph_observation(0.4))
        obs.sort(key=lambda o: o.receipt_monotonic_s)
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE

    def test_no_graph_observations_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        obs = _observations(scenario, include_graph=False)
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE

    def test_wrong_auth_disposition_vs_matrix_is_error(self) -> None:
        matrix = _matrix()
        scenario = DegradedInputScenario.STALE_INPUT
        obs = _observations(
            scenario,
            auth_disposition=DegradedInputDisposition.FAIL_WRONG_DISPOSITION.value,
        )
        result = evaluate_profile(matrix, scenario, obs, window_end_receipt_s=1.0)
        assert result.passed is False
        assert result.disposition is DegradedInputDisposition.ERROR_EVIDENCE


# ---------------------------------------------------------------------------
# Serialization and terminal policy tests
# ---------------------------------------------------------------------------

class TestSerializationAndTerminal:
    def test_result_serialization_round_trips(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.MALFORMED_INPUT
        auth = _authorization(scenario)
        transition = _transition_observation(scenario)
        status = _status_observation()
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth, [transition, status],
            window_end_receipt_s=1.0,
        )
        serialized = degraded_input_result_to_json(result)
        assert serialized["scenario"] == scenario.value
        assert serialized["disposition"] == "pass_bounded_detection"
        assert serialized["passed"] is True
        assert serialized["degraded_input_profile"] == scenario.value
        assert serialized["input_health"] == "malformed"
        assert "reason" in serialized

    def test_terminal_pass_returns_pass_degraded_input_profile(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        result = evaluate_degraded_input_scenario(
            contract, scenario, _authorization(scenario),
            [_transition_observation(scenario), _status_observation()],
            window_end_receipt_s=1.0,
        )
        assert terminal_degraded_input_result(result) == "pass_degraded_input_profile"

    def test_terminal_inconclusive_returns_none(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        result = evaluate_degraded_input_scenario(
            contract, scenario, _authorization(scenario), [],
            window_end_receipt_s=1.0,
        )
        assert terminal_degraded_input_result(result) is None

    def test_terminal_fail_returns_terminal_failure(self) -> None:
        contract = _contract()
        scenario = DegradedInputScenario.STALE_INPUT
        auth = _authorization(
            scenario, disposition=DegradedInputDisposition.FAIL_WRONG_DISPOSITION.value
        )
        result = evaluate_degraded_input_scenario(
            contract, scenario, auth,
            [_transition_observation(scenario), _status_observation()],
            window_end_receipt_s=1.0,
        )
        assert terminal_degraded_input_result(result) == "terminal_degraded_input_failure"


# ---------------------------------------------------------------------------
# Evidence builder tests
# ---------------------------------------------------------------------------

class TestDegradedInputEvidenceBuilder:
    def test_builds_a_closed_evidence_document(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.STALE_INPUT
        obs = _observations(profile)
        raw = _make_raw(obs, profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-build-001", raw)
        try:
            document = build_degraded_input_evidence(
                raw,
                BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                profile=profile.value,
                bench_root=BENCH_ROOT,
            )
            assert document["schema"] == "de4sdv.aebs-009f.scenario-evidence.v1"
            assert document["increment_id"] == "INC-AEBS-009F"
            assert document["degraded_input_profile"] == profile.value
            assert document["scenario_id"] == "SCN-AEBS-009F-STALE-INPUT"
            assert document["evaluation"]["disposition"] == "pass_bounded_detection"
            assert document["evaluation"]["passed"] is True
            assert "no_safety_or_compliance_claim" in document["claim_boundary"]
            assert "collection" in document
            assert "collector_contract" in document
            assert "artifacts" in document
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)

    def test_builds_all_five_profiles(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        for profile in DegradedInputScenario:
            obs = _observations(profile)
            raw = _make_raw(obs, profile)
            artifacts, _ = _make_artifacts(
                BENCH_ROOT, profile.value, f"test-all-{profile.value}", raw
            )
            try:
                document = build_degraded_input_evidence(
                    raw,
                    BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    profile=profile.value,
                    bench_root=BENCH_ROOT,
                )
                assert document["degraded_input_profile"] == profile.value
                assert document["evaluation"]["passed"] is True
            finally:
                _cleanup_fixtures(BENCH_ROOT, profile.value)

    def test_rejects_tampered_evaluator_result(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.MISSING_INPUT
        raw = _make_raw(_observations(profile), profile)
        raw["evaluator_result"]["reason"] = "tampered"
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-tamper-001", raw)
        try:
            with pytest.raises(ValueError, match="differs from independent replay"):
                build_degraded_input_evidence(
                    raw,
                    BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    profile=profile.value,
                    bench_root=BENCH_ROOT,
                )
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)

    def test_rejects_open_raw_contract(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.STALE_INPUT
        raw = _make_raw(_observations(profile), profile)
        raw["invented_field"] = "bad"
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-open-001", raw)
        try:
            with pytest.raises(ValueError, match="do not match the closed contract"):
                build_degraded_input_evidence(
                    raw,
                    BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    profile=profile.value,
                    bench_root=BENCH_ROOT,
                )
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)

    def test_rejects_non_passing_terminal(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.STALE_INPUT
        raw = _make_raw(_observations(profile), profile)
        raw["terminal_reason"] = "timeout"
        raw["command_exit"] = 1
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-terminal-001", raw)
        try:
            with pytest.raises(ValueError):
                build_degraded_input_evidence(
                    raw,
                    BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    profile=profile.value,
                    bench_root=BENCH_ROOT,
                )
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)

    def test_rejects_unknown_profile(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.STALE_INPUT
        raw = _make_raw(_observations(profile), profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-unknown-001", raw)
        try:
            with pytest.raises((ValueError, TypeError)):
                build_degraded_input_evidence(
                    raw,
                    BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    profile="not_a_profile",
                    bench_root=BENCH_ROOT,
                )
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)


# ---------------------------------------------------------------------------
# Evidence shape tests
# ---------------------------------------------------------------------------

class TestDegradedInputEvidenceShape:
    def test_evidence_root_has_exactly_closed_keys(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.STALE_INPUT
        raw = _make_raw(_observations(profile), profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-shape-001", raw)
        try:
            document = build_degraded_input_evidence(
                raw,
                BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                profile=profile.value,
                bench_root=BENCH_ROOT,
            )
            expected = {
                "schema", "increment_id", "scenario_id", "degraded_input_profile",
                "provenance", "collection", "collector_contract",
                "evaluation", "artifacts", "claim_boundary",
            }
            assert set(document) == expected
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)

    def test_evaluation_is_source_bound_not_trust_promoted(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.INCONSISTENT_INPUT
        obs = _observations(profile)
        raw = _make_raw(obs, profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-bound-001", raw)
        try:
            document = build_degraded_input_evidence(
                raw,
                BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                profile=profile.value,
                bench_root=BENCH_ROOT,
            )
            matrix = _matrix()
            expected = degraded_input_result_to_json(
                evaluate_profile(matrix, profile, obs, window_end_receipt_s=1.0)
            )
            assert canonical_json_bytes(document["evaluation"]) == canonical_json_bytes(expected)
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)

    def test_claim_boundary_is_explicit_and_compliance_withheld(self) -> None:
        from evidence_pipeline import build_evidence, load_contract

        profile = DegradedInputScenario.UNAVAILABLE_INPUT
        raw = _make_raw(_observations(profile), profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "test-claim-001", raw)
        try:
            document = build_degraded_input_evidence(
                raw,
                BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                profile=profile.value,
                bench_root=BENCH_ROOT,
            )
            assert "no_safety_or_compliance_claim" in document["claim_boundary"]
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)
