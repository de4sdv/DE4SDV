"""Pure tests for INC-AEBS-009G/009H crossing-target evidence pipeline.

These tests verify the closed-contract, fail-closed, source-bound, and
compliance-withheld properties of the 009G/009H crossing-target evidence
pipeline without requiring a live runtime or retained evidence files.
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_ROOT = REPO_ROOT / "implementation" / "aebs-autoware-nominal-vehicle-target-bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
FRAMEWORK_ROOT = REPO_ROOT / "implementation" / "aebs-bench-framework"

for path in (REPO_ROOT, SCRIPTS_ROOT, PACKAGE_ROOT, FRAMEWORK_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_pipeline import build_evidence, load_contract
from de4sdv_aebs_009b_bench.crossing_target_matrix import (
    CrossingEvidenceOutcome,
    CrossingTargetContract,
    CrossingTargetGeometry,
    CrossingTargetSample,
    CrossingTargetScenarioConfig,
    DiagnosticAuthorization,
    EXPECTED_GEOMETRY,
    TargetType,
    crossing_target_result_to_json,
    evaluate_crossing_target_scenario,
    load_crossing_target_config,
)
from de4sdv_aebs_009b_bench.scenario_contract import Pose2D, VehicleFootprint
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind
from evidence_document import CLOCK_BOUNDARY, canonical_json_bytes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SOURCE_STAMP = "1700000000.000000000"
_AUTH_STAMP = "1700000000.300000000"  # age = 0.3 s, within max_source_age_s = 0.5


def _ego_footprint() -> VehicleFootprint:
    return VehicleFootprint(front_offset_m=3.74, rear_offset_m=1.03, width_m=1.83)


def _pedestrian_geometry() -> CrossingTargetGeometry:
    return EXPECTED_GEOMETRY[TargetType.PEDESTRIAN]


def _bicycle_geometry() -> CrossingTargetGeometry:
    return EXPECTED_GEOMETRY[TargetType.BICYCLE]


def _contract(crossing_speed: float = 1.5) -> CrossingTargetContract:
    return CrossingTargetContract(
        max_source_age_s=0.5,
        closed_window_s=2.0,
        crossing_speed_mps=crossing_speed,
    )


def _sample(
    *,
    target_x: float = 10.0,
    target_y: float = 5.0,
    target_yaw: float = math.pi / 2.0,
    ego_x: float = 10.0,
    ego_y: float = 0.0,
    ego_yaw: float = 0.0,
    source_stamp: str = _SOURCE_STAMP,
) -> CrossingTargetSample:
    return CrossingTargetSample(
        received=True,
        target_pose_map=Pose2D(target_x, target_y, target_yaw),
        ego_pose_map=Pose2D(ego_x, ego_y, ego_yaw),
        source_stamp=source_stamp,
    )


def _authorization() -> DiagnosticAuthorization:
    return DiagnosticAuthorization(
        source_stamp=_AUTH_STAMP,
        node="autonomous_emergency_braking",
        task="aeb_emergency_stop",
        level="ERROR",
        message="[AEB]: Emergency Brake",
    )


def _observations(
    *,
    intervention_receipt: float = 5.0,
    footprint_receipt: float = 6.0,
    brake_receipt: float = 7.0,
    ego_x: float = 10.0,
    ego_y: float = 0.0,
    ego_yaw: float = 0.0,
    target_x: float = 10.0,
    target_y: float = 5.0,
    target_yaw: float = math.pi / 2.0,
    separation_m: float = 3.935,  # pedestrian default; bicycle uses 3.185
) -> list[Observation]:
    """Construct a valid observation chain that produces PASS_BOUNDED_TARGET_RESPONSE.

    The diagnostic and AEB intervention must share the same receipt_monotonic_s
    and source_stamp, per the evaluator's authorization-exact-match contract.
    """
    risk_payload = {"rss_distance_m": 5.0, "object_distance_m": 3.0, "warning": True, "intervention": False}
    warning_payload = {"active": True}
    diagnostic_payload = {"node": "autonomous_emergency_braking", "task": "aeb_emergency_stop", "level": "ERROR"}
    intervention_payload = {
        "node": "autonomous_emergency_braking",
        "task": "aeb_emergency_stop",
        "level": "ERROR",
        "message": "[AEB]: Emergency Brake",
        "rss_distance_m": 5.0,
        "object_distance_m": 3.0,
        "object_speed_mps": 1.5,
    }
    footprint_payload = {
        "ego_x": ego_x, "ego_y": ego_y, "ego_yaw_rad": ego_yaw,
        "target_x": target_x, "target_y": target_y, "target_yaw_rad": target_yaw,
        "sample_skew_s": 0.0,
        "separation_m": separation_m,
        "overlap": False,
    }
    brake_payload = {"speed_mps": 0.0, "acceleration_mps2": -5.0}
    # diagnostic and intervention share the same receipt_monotonic_s
    diag_receipt = intervention_receipt
    return [
        Observation(
            kind=ObservationKind.RISK_ASSESSMENT,
            payload=risk_payload,
            receipt_monotonic_s=intervention_receipt - 2.0,
            source_stamp=_SOURCE_STAMP,
        ),
        Observation(
            kind=ObservationKind.WARNING_REQUEST,
            payload=warning_payload,
            receipt_monotonic_s=intervention_receipt - 1.0,
            source_stamp=_SOURCE_STAMP,
        ),
        Observation(
            kind=ObservationKind.DIAGNOSTIC,
            payload=diagnostic_payload,
            receipt_monotonic_s=diag_receipt,
            source_stamp=_AUTH_STAMP,
        ),
        Observation(
            kind=ObservationKind.AEB_INTERVENTION,
            payload=intervention_payload,
            receipt_monotonic_s=diag_receipt,
            source_stamp=_AUTH_STAMP,
        ),
        Observation(
            kind=ObservationKind.FOOTPRINT_STATE,
            payload=footprint_payload,
            receipt_monotonic_s=footprint_receipt,
            source_stamp=_AUTH_STAMP,
        ),
        Observation(
            kind=ObservationKind.BRAKING_REQUEST,
            payload=brake_payload,
            receipt_monotonic_s=brake_receipt,
            source_stamp=_AUTH_STAMP,
        ),
    ]


def _obs_to_json(observations: list[Observation]) -> list[dict]:
    from evidence_document import observation_to_json
    return [observation_to_json(item) for item in observations]


def _make_raw(
    observations: list[Observation],
    sample: CrossingTargetSample,
    authorization: DiagnosticAuthorization,
    config: CrossingTargetScenarioConfig,
) -> dict:
    obs_json = _obs_to_json(observations)
    result = evaluate_crossing_target_scenario(
        config.contract,
        config.target_type,
        config.geometry,
        config.ego_footprint,
        sample,
        authorization,
        observations,
        window_end_receipt_s=10.0,
    )
    serialized = crossing_target_result_to_json(result)
    return {
        "collector_id": "de4sdv.scenario_observer.v1",
        "monotonic_start_s": 0.0,
        "monotonic_end_s": 10.0,
        "clock_boundary": CLOCK_BOUNDARY,
        "observations": obs_json,
        "evaluator_result": serialized,
        "activation": {
            "request_time_s": 1.0,
            "response_time_s": 1.5,
            "status": "succeeded",
            "response_message": "ok",
        },
        "errors": [],
        "terminal_reason": "pass_bounded_target_response",
        "command_exit": 0,
        "limits": {
            "timeout_s": 45.0,
            "deadline_s": 45.0,
            "observation_cap": min(100_000, max(1_000, math.ceil(45.0 * 1_000))),
            "error_cap": 256,
        },
        "crossing_target_sample": {
            "received": sample.received,
            "target_pose_map": (
                {"x": sample.target_pose_map.x, "y": sample.target_pose_map.y, "yaw_rad": sample.target_pose_map.yaw_rad}
                if sample.target_pose_map is not None
                else None
            ),
            "ego_pose_map": (
                {"x": sample.ego_pose_map.x, "y": sample.ego_pose_map.y, "yaw_rad": sample.ego_pose_map.yaw_rad}
                if sample.ego_pose_map is not None
                else None
            ),
            "source_stamp": sample.source_stamp,
        },
        "authorization_diagnostic": {
            "source_stamp": authorization.source_stamp,
            "node": authorization.node,
            "task": authorization.task,
            "level": authorization.level,
            "message": authorization.message,
        },
    }


def _make_provenance(bench_root: Path, config_path: str = "config/scenario-009g-pedestrian-crossing.yaml") -> dict:
    from validate_scenario_evidence import _live_provenance_fields
    from execution_identity import execution_manifest_sha256
    from evidence_document import sha256_file

    value = _live_provenance_fields(bench_root)
    head = value.pop("repository_head")
    value["captured_utc"] = "2026-07-28T10:00:00Z"
    value["command_exit_code"] = 0
    value["execution_manifest_sha256"] = execution_manifest_sha256(bench_root)
    value["crossing_config_sha256"] = sha256_file(bench_root / config_path)
    value["repository_head"] = head
    return value



def build_crossing_target_evidence(
    raw,
    config_path,
    provenance,
    artifacts,
    *,
    increment_id,
    bench_root=BENCH_ROOT,
):
    config = load_crossing_target_config(config_path)
    contract = load_contract(bench_root / f"config/contract-{increment_id[-4:].lower()}.yaml")
    return build_evidence(
        raw,
        config.target_type,
        provenance,
        artifacts,
        contract=contract,
        bench_root=bench_root,
    )




def _make_artifacts(bench_root: Path, subdir: str, run_id: str, raw: dict) -> tuple[dict, Path]:
    """Create real artifact files and return the artifacts dict and evidence dir."""
    evidence_dir = bench_root / "evidence" / subdir / "test_fixtures" / run_id
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
    import hashlib
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
        "image_id": lock["container"]["index_digest"],  # use index_digest as image_id
        "lock_sha256": value["runtime_lock_sha256"],
        "map_files_verified": True,
        "map_sha256": value["map_digest"].removeprefix("sha256:"),
        "repository_head": value["repository_head"],
        "utc_time": "2026-07-28T10:00:00Z",
    }


# ---------------------------------------------------------------------------
# Config loading tests
# ---------------------------------------------------------------------------

class TestCrossingTargetConfig:
    def test_loads_009g_pedestrian_config(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        assert config.increment_id == "INC-AEBS-009G"
        assert config.scenario_id == "SCN-AEBS-009G-PEDESTRIAN-CROSSING-001"
        assert config.target_type is TargetType.PEDESTRIAN
        assert config.geometry == EXPECTED_GEOMETRY[TargetType.PEDESTRIAN]
        assert config.geometry == CrossingTargetGeometry(0.3, 0.5, 1.8)

    def test_loads_009h_bicycle_config(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009h-bicycle-crossing.yaml"
        )
        assert config.increment_id == "INC-AEBS-009H"
        assert config.scenario_id == "SCN-AEBS-009H-BICYCLE-CROSSING-001"
        assert config.target_type is TargetType.BICYCLE
        assert config.geometry == EXPECTED_GEOMETRY[TargetType.BICYCLE]
        assert config.geometry == CrossingTargetGeometry(1.8, 0.6, 1.2)

    def test_config_rejects_wrong_schema_for_target_type(self) -> None:
        """A pedestrian config with a bicycle schema must be rejected."""
        import yaml
        path = BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw["schema"] = "de4sdv.aebs-009h-bicycle-crossing.v1"
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, dir=str(BENCH_ROOT)
        )
        yaml.dump(raw, tmp)
        tmp.close()
        try:
            with pytest.raises(ValueError, match="schema does not match target_type"):
                load_crossing_target_config(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_config_has_closed_non_claims(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        assert len(config.non_claims) >= 5
        assert all(isinstance(item, str) and item for item in config.non_claims)


# ---------------------------------------------------------------------------
# Evaluator contract tests
# ---------------------------------------------------------------------------

class TestCrossingTargetEvaluator:
    def test_pedestrian_pass_bounded_target_response(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        sample = _sample()
        auth = _authorization()
        obs = _observations()
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, sample, auth, obs,
            window_end_receipt_s=10.0,
        )
        assert result.passed is True
        assert result.outcome is CrossingEvidenceOutcome.PASS_BOUNDED_TARGET_RESPONSE
        assert result.target_type is TargetType.PEDESTRIAN

    def test_bicycle_pass_bounded_target_response(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009h-bicycle-crossing.yaml"
        )
        sample = _sample()
        auth = _authorization()
        obs = _observations(separation_m=3.185)  # bicycle geometry yields 3.185 m
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, sample, auth, obs,
            window_end_receipt_s=10.0,
        )
        assert result.passed is True
        assert result.outcome is CrossingEvidenceOutcome.PASS_BOUNDED_TARGET_RESPONSE
        assert result.target_type is TargetType.BICYCLE

    def test_missing_sample_is_inconclusive(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        sample = CrossingTargetSample(
            received=False, target_pose_map=None, ego_pose_map=None, source_stamp=None
        )
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, sample, _authorization(), _observations(),
            window_end_receipt_s=10.0,
        )
        assert result.passed is False
        assert result.outcome is CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE

    def test_non_perpendicular_trajectory_fails(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        # Target yaw = 0 (parallel to ego, not perpendicular)
        sample = _sample(target_yaw=0.0)
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, sample, _authorization(), _observations(),
            window_end_receipt_s=10.0,
        )
        assert result.passed is False
        assert result.outcome is CrossingEvidenceOutcome.FAIL_CONFIGURED_OUTCOME

    def test_stale_source_stamp_is_inconclusive(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        # source stamp far in the past → age > max_source_age_s
        stale_sample = _sample(source_stamp="1699999990.000000000")
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, stale_sample, _authorization(), _observations(),
            window_end_receipt_s=10.0,
        )
        assert result.passed is False
        assert result.outcome is CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE

    def test_malformed_stamp_is_error_evidence(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        malformed_sample = _sample(source_stamp="not-a-stamp")
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, malformed_sample, _authorization(), _observations(),
            window_end_receipt_s=10.0,
        )
        assert result.passed is False
        assert result.outcome is CrossingEvidenceOutcome.ERROR_EVIDENCE

    def test_missing_braking_request_fails_after_closed_window(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        obs = _observations(brake_receipt=100.0)  # far beyond window
        # Remove the braking request
        obs = [o for o in obs if o.kind is not ObservationKind.BRAKING_REQUEST]
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, _sample(), _authorization(), obs,
            window_end_receipt_s=100.0,
        )
        assert result.passed is False
        assert result.outcome is CrossingEvidenceOutcome.FAIL_CONFIGURED_OUTCOME

    def test_result_serialization_round_trips(self) -> None:
        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        result = evaluate_crossing_target_scenario(
            config.contract, config.target_type, config.geometry,
            config.ego_footprint, _sample(), _authorization(), _observations(),
            window_end_receipt_s=10.0,
        )
        serialized = crossing_target_result_to_json(result)
        assert serialized["target_type"] == "pedestrian"
        assert serialized["outcome"] == "passBoundedTargetResponse"
        assert serialized["passed"] is True
        assert "reason" in serialized


# ---------------------------------------------------------------------------
# Evidence builder tests
# ---------------------------------------------------------------------------

class TestCrossingTargetEvidenceBuilder:
    def test_builds_a_closed_evidence_document(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        sample = _sample()
        auth = _authorization()
        obs = _observations()
        raw = _make_raw(obs, sample, auth, config)
        artifacts, evidence_dir = _make_artifacts(
            BENCH_ROOT, "009g", "test-build-001", raw
        )
        try:
            document = build_crossing_target_evidence(
                raw,
                BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                increment_id="INC-AEBS-009G",
                bench_root=BENCH_ROOT,
            )
            assert document["schema"] == "de4sdv.aebs-009g.scenario-evidence.v1"
            assert document["increment_id"] == "INC-AEBS-009G"
            assert document["scenario_id"] == "SCN-AEBS-009G-PEDESTRIAN-CROSSING-001"
            assert document["target_type"] == "pedestrian"
            assert "evaluation" in document
            assert document["evaluation"]["outcome"] == "passBoundedTargetResponse"
            assert document["claim_boundary"] == (
                "one_crossing_target_scenario_verdict_only_no_safety_or_compliance_claim"
            )
            assert "crossing_target_sample" in document
            assert "authorization_diagnostic" in document
            assert "collection" in document
            assert "collector_contract" in document
            assert "artifacts" in document
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)

    def test_rejects_unknown_increment(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        raw = _make_raw(_observations(), _sample(), _authorization(), config)
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009g", "test-inc-001", raw)
        try:
            with pytest.raises((ValueError, FileNotFoundError)):
                contract = load_contract(BENCH_ROOT / "config/contract-009z.yaml")
                build_evidence(
                    raw,
                    TargetType.PEDESTRIAN,
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    contract=contract,
                    bench_root=BENCH_ROOT,
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)

    def test_rejects_tampered_evaluator_result(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        raw = _make_raw(_observations(), _sample(), _authorization(), config)
        # Tamper with the stored evaluator result
        raw["evaluator_result"]["reason"] = "tampered"
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009g", "test-tamper-001", raw)
        try:
            with pytest.raises(ValueError, match="differs from independent replay"):
                build_crossing_target_evidence(
                    raw,
                    BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    increment_id="INC-AEBS-009G",
                    bench_root=BENCH_ROOT,
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)

    def test_rejects_open_raw_contract(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        raw = _make_raw(_observations(), _sample(), _authorization(), config)
        raw["invented_field"] = "bad"
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009g", "test-open-001", raw)
        try:
            with pytest.raises(ValueError, match="do not match the closed contract"):
                build_crossing_target_evidence(
                    raw,
                    BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    increment_id="INC-AEBS-009G",
                    bench_root=BENCH_ROOT,
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)

    def test_rejects_non_passing_terminal(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        raw = _make_raw(_observations(), _sample(), _authorization(), config)
        raw["terminal_reason"] = "timeout"
        raw["command_exit"] = 1
        # The evaluator result still says pass, but terminal says timeout —
        # _validate_crossing_raw_semantics will reject the inconsistency.
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009g", "test-terminal-001", raw)
        try:
            with pytest.raises((ValueError,)):
                build_crossing_target_evidence(
                    raw,
                    BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    increment_id="INC-AEBS-009G",
                    bench_root=BENCH_ROOT,
                )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)

    def test_builds_009h_bicycle_evidence(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009h-bicycle-crossing.yaml"
        )
        sample = _sample()
        auth = _authorization()
        obs = _observations(separation_m=3.185)  # bicycle geometry
        raw = _make_raw(obs, sample, auth, config)
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009h", "test-build-001", raw)
        try:
            document = build_crossing_target_evidence(
                raw,
                BENCH_ROOT / "config/scenario-009h-bicycle-crossing.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                increment_id="INC-AEBS-009H",
                bench_root=BENCH_ROOT,
            )
            assert document["schema"] == "de4sdv.aebs-009h.scenario-evidence.v1"
            assert document["increment_id"] == "INC-AEBS-009H"
            assert document["target_type"] == "bicycle"
            assert document["evaluation"]["outcome"] == "passBoundedTargetResponse"
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009h" / "test_fixtures", ignore_errors=True)


# ---------------------------------------------------------------------------
# Evidence shape tests
# ---------------------------------------------------------------------------

class TestCrossingTargetEvidenceShape:
    def test_evidence_root_has_exactly_closed_keys(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        raw = _make_raw(_observations(), _sample(), _authorization(), config)
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009g", "test-shape-001", raw)
        try:
            document = build_crossing_target_evidence(
                raw,
                BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                increment_id="INC-AEBS-009G",
                bench_root=BENCH_ROOT,
            )
            expected = {
                "schema", "increment_id", "scenario_id", "target_type",
                "provenance", "collection", "collector_contract",
                "crossing_target_sample", "authorization_diagnostic",
                "evaluation", "artifacts", "claim_boundary",
            }
            assert set(document) == expected
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)

    def test_evaluation_is_source_bound_not_trust_promoted(self, tmp_path: Path) -> None:
        """The evaluation in the evidence must match the independently replayed result."""
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        obs = _observations()
        sample = _sample()
        auth = _authorization()
        raw = _make_raw(obs, sample, auth, config)
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009g", "test-bound-001", raw)
        try:
            document = build_crossing_target_evidence(
                raw,
                BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                increment_id="INC-AEBS-009G",
                bench_root=BENCH_ROOT,
            )
            # The evaluation must match the independently computed result
            expected = crossing_target_result_to_json(
                evaluate_crossing_target_scenario(
                    config.contract, config.target_type, config.geometry,
                    config.ego_footprint, sample, auth, obs,
                    window_end_receipt_s=10.0,
                )
            )
            assert canonical_json_bytes(document["evaluation"]) == canonical_json_bytes(expected)
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)

    def test_claim_boundary_is_explicit_and_compliance_withheld(self, tmp_path: Path) -> None:
        from evidence_pipeline import build_evidence, load_contract
        import shutil

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        raw = _make_raw(_observations(), _sample(), _authorization(), config)
        artifacts, _ = _make_artifacts(BENCH_ROOT, "009g", "test-claim-001", raw)
        try:
            document = build_crossing_target_evidence(
                raw,
                BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                _make_provenance(BENCH_ROOT),
                artifacts,
                increment_id="INC-AEBS-009G",
                bench_root=BENCH_ROOT,
            )
            assert "no_safety_or_compliance_claim" in document["claim_boundary"]
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "test_fixtures", ignore_errors=True)


# ---------------------------------------------------------------------------
# Increment config / schema tests
# ---------------------------------------------------------------------------

class TestIncrementConfig:
    def test_009g_and_009h_have_distinct_schemas(self) -> None:
        from de4sdv_aebs_009b_bench.crossing_target_matrix import INCREMENT_CONFIG
        g = INCREMENT_CONFIG["INC-AEBS-009G"]
        h = INCREMENT_CONFIG["INC-AEBS-009H"]
        assert g["schema"] != h["schema"]
        assert g["campaign_schema"] != h["campaign_schema"]
        assert g["target_type"] != h["target_type"]

    def test_evidence_dirs_match_increment_lowercase(self) -> None:
        from de4sdv_aebs_009b_bench.crossing_target_matrix import INCREMENT_CONFIG
        assert INCREMENT_CONFIG["INC-AEBS-009G"]["evidence_dir"] == "evidence/009g"
        assert INCREMENT_CONFIG["INC-AEBS-009H"]["evidence_dir"] == "evidence/009h"
