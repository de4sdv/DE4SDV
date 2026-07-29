"""Framework parity tests — verify the shared evidence pipeline produces
byte-identical evidence documents to the per-increment builders.

These tests prove that the framework (implementation/aebs-bench-framework/)
can safely replace the per-increment evidence builders without changing any
output. If parity holds, the per-increment builders can be deleted and the
framework can become the sole evidence pipeline.

Covers 009D/009E/009F plus the existing 009G/009H crossing-target cases.
"""

from __future__ import annotations

import json
import math
import shutil
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

from de4sdv_aebs_009b_bench.crossing_target_matrix import (  # noqa: E402
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
from de4sdv_aebs_009b_bench.scenario_contract import Pose2D, VehicleFootprint  # noqa: E402
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind  # noqa: E402
from evidence_document import (  # noqa: E402
    CLOCK_BOUNDARY,
    canonical_json_bytes,
    load_strict_json,
)

_SOURCE_STAMP = "1700000000.000000000"
_AUTH_STAMP = "1700000000.300000000"


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
    separation_m: float = 3.935,
) -> list[Observation]:
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
        "ego_x": 10.0, "ego_y": 0.0, "ego_yaw_rad": 0.0,
        "target_x": 10.0, "target_y": 5.0, "target_yaw_rad": math.pi / 2.0,
        "sample_skew_s": 0.0,
        "separation_m": separation_m,
        "overlap": False,
    }
    brake_payload = {"speed_mps": 0.0, "acceleration_mps2": -5.0}
    diag_receipt = 5.0
    return [
        Observation(ObservationKind.RISK_ASSESSMENT, risk_payload, 3.0, _SOURCE_STAMP),
        Observation(ObservationKind.WARNING_REQUEST, warning_payload, 4.0, _SOURCE_STAMP),
        Observation(ObservationKind.DIAGNOSTIC, diagnostic_payload, diag_receipt, _AUTH_STAMP),
        Observation(ObservationKind.AEB_INTERVENTION, intervention_payload, diag_receipt, _AUTH_STAMP),
        Observation(ObservationKind.FOOTPRINT_STATE, footprint_payload, 6.0, _AUTH_STAMP),
        Observation(ObservationKind.BRAKING_REQUEST, brake_payload, 7.0, _AUTH_STAMP),
    ]


def _obs_to_json(observations: list[Observation]) -> list[dict]:
    from evidence_document import observation_to_json
    return [observation_to_json(item) for item in observations]


def _make_raw(observations, sample, authorization, config) -> dict:
    from crossing_target_evidence import build_crossing_target_evidence as _  # just ensure import works
    obs_json = _obs_to_json(observations)
    result = evaluate_crossing_target_scenario(
        config.contract, config.target_type, config.geometry,
        config.ego_footprint, sample, authorization, observations,
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
                if sample.target_pose_map is not None else None
            ),
            "ego_pose_map": (
                {"x": sample.ego_pose_map.x, "y": sample.ego_pose_map.y, "yaw_rad": sample.ego_pose_map.yaw_rad}
                if sample.ego_pose_map is not None else None
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


def _make_artifacts(bench_root: Path, subdir: str, run_id: str, raw: dict) -> tuple[dict, Path]:
    from validate_scenario_evidence import _live_provenance_fields
    from execution_identity import execution_manifest_sha256
    import hashlib
    import yaml

    evidence_dir = bench_root / "evidence" / subdir / "parity_test" / run_id
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
    value = _live_provenance_fields(bench_root)
    lock = yaml.safe_load((bench_root / "runtime-lock.yaml").read_text(encoding="utf-8"))
    map_content = {
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


def _make_provenance(bench_root: Path, config_path: str) -> dict:
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


def _assert_byte_identical(label: str, per_increment_doc: dict, framework_doc: dict) -> None:
    per_bytes = canonical_json_bytes(per_increment_doc)
    framework_bytes = canonical_json_bytes(framework_doc)
    assert per_bytes == framework_bytes, (
        f"{label} evidence differs between per-increment and framework builders.\n"
        f"Per-increment keys: {sorted(per_increment_doc.keys())}\n"
        f"Framework keys: {sorted(framework_doc.keys())}\n"
    )


def _load_009d_fixture(profile) -> tuple[dict, dict, dict]:
    manifest = load_strict_json(BENCH_ROOT / "evidence" / "009d" / "campaign-manifest.json")
    entry = manifest["profiles"][profile.value]
    run_dir = (
        BENCH_ROOT
        / "evidence"
        / "009d"
        / "profiles"
        / profile.value
        / "runs"
        / entry["run_id"]
    )
    return (
        load_strict_json(run_dir / "observer-raw.json"),
        load_strict_json(run_dir / "provenance.json"),
        load_strict_json(run_dir / "artifacts.json"),
    )


class TestFrameworkParity009D:
    def test_override_evidence_is_byte_identical(self) -> None:
        from evidence_pipeline import build_evidence, load_contract
        from de4sdv_aebs_009b_bench.override_matrix import OverrideScenario
        from override_evidence import build_override_evidence

        profile = OverrideScenario.FRESH_FALSE_CONTROL
        raw, provenance, artifacts = _load_009d_fixture(profile)
        contract = load_contract(BENCH_ROOT / "config/contract-009d.yaml")

        per_increment_doc = build_override_evidence(
            raw,
            profile,
            provenance,
            artifacts,
            matrix_path=BENCH_ROOT / "config" / "scenario-009d-conscious-override-matrix.yaml",
        )
        framework_doc = build_evidence(
            raw,
            profile,
            provenance,
            artifacts,
            contract=contract,
            bench_root=BENCH_ROOT,
        )
        _assert_byte_identical("009D", per_increment_doc, framework_doc)


class TestFrameworkParity009E:
    def test_non_activation_evidence_is_byte_identical(self) -> None:
        from de4sdv_aebs_009b_bench.non_activation_matrix import NonActivationScenario
        from evidence_pipeline import build_evidence, load_contract
        from non_activation_evidence import build_non_activation_evidence
        from tests.test_aebs_009e_non_activation_matrix import (
            _make_artifacts,
            _make_provenance,
            _make_raw,
            _passing_observations,
        )

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "parity-009e-001", raw)
        provenance = _make_provenance(BENCH_ROOT, profile.value)
        contract = load_contract(BENCH_ROOT / "config/contract-009e.yaml")

        try:
            per_increment_doc = build_non_activation_evidence(
                raw,
                profile,
                provenance,
                artifacts,
                matrix_path=BENCH_ROOT / "config" / "scenario-009e-non-activation-matrix.yaml",
            )
            framework_doc = build_evidence(
                raw,
                profile,
                provenance,
                artifacts,
                contract=contract,
                bench_root=BENCH_ROOT,
            )
            _assert_byte_identical("009E", per_increment_doc, framework_doc)
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)


class TestFrameworkParity009F:
    def test_degraded_input_evidence_is_byte_identical(self) -> None:
        from de4sdv_aebs_009b_bench.degraded_input_matrix import DegradedInputScenario
        from evidence_pipeline import build_evidence, load_contract
        from degraded_input_evidence import build_degraded_input_evidence
        from tests.test_aebs_009f_degraded_input_matrix import (
            _cleanup_fixtures,
            _make_artifacts,
            _make_provenance,
            _make_raw,
            _observations,
        )

        profile = DegradedInputScenario.STALE_INPUT
        raw = _make_raw(_observations(profile), profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "parity-009f-001", raw)
        provenance = _make_provenance(BENCH_ROOT)
        contract = load_contract(BENCH_ROOT / "config/contract-009f.yaml")

        try:
            per_increment_doc = build_degraded_input_evidence(
                raw,
                BENCH_ROOT / "config" / "scenario-009f-degraded-input-matrix.yaml",
                provenance,
                artifacts,
                profile=profile.value,
                bench_root=BENCH_ROOT,
            )
            framework_doc = build_evidence(
                raw,
                profile,
                provenance,
                artifacts,
                contract=contract,
                bench_root=BENCH_ROOT,
            )
            _assert_byte_identical("009F", per_increment_doc, framework_doc)
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)


class TestFrameworkParity009G:
    """Verify the framework produces the same evidence as the per-increment builder for 009G."""

    def test_pedestrian_evidence_is_byte_identical(self, tmp_path: Path) -> None:
        from crossing_target_evidence import build_crossing_target_evidence

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml"
        )
        sample = _sample()
        auth = _authorization()
        obs = _observations(separation_m=3.935)
        raw = _make_raw(obs, sample, auth, config)
        artifacts, evidence_dir = _make_artifacts(BENCH_ROOT, "009g", "parity-009g-001", raw)
        provenance = _make_provenance(BENCH_ROOT, "config/scenario-009g-pedestrian-crossing.yaml")

        try:
            # Per-increment builder
            per_increment_doc = build_crossing_target_evidence(
                raw,
                BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                provenance,
                artifacts,
                increment_id="INC-AEBS-009G",
                bench_root=BENCH_ROOT,
            )

            # Framework builder
            from evidence_pipeline import build_evidence, load_contract
            contract = load_contract(BENCH_ROOT / "config/contract-009g.yaml")
            framework_doc = build_evidence(
                raw,
                TargetType.PEDESTRIAN,
                provenance,
                artifacts,
                contract=contract,
                bench_root=BENCH_ROOT,
            )

            # Byte-identical comparison
            per_bytes = canonical_json_bytes(per_increment_doc)
            framework_bytes = canonical_json_bytes(framework_doc)
            assert per_bytes == framework_bytes, (
                f"009G evidence differs between per-increment and framework builders.\n"
                f"Per-increment keys: {sorted(per_increment_doc.keys())}\n"
                f"Framework keys: {sorted(framework_doc.keys())}\n"
            )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009g" / "parity_test", ignore_errors=True)


class TestFrameworkParity009H:
    """Verify the framework produces the same evidence as the per-increment builder for 009H."""

    def test_bicycle_evidence_is_byte_identical(self, tmp_path: Path) -> None:
        from crossing_target_evidence import build_crossing_target_evidence

        config = load_crossing_target_config(
            BENCH_ROOT / "config/scenario-009h-bicycle-crossing.yaml"
        )
        sample = _sample()
        auth = _authorization()
        obs = _observations(separation_m=3.185)
        raw = _make_raw(obs, sample, auth, config)
        artifacts, evidence_dir = _make_artifacts(BENCH_ROOT, "009h", "parity-009h-001", raw)
        provenance = _make_provenance(BENCH_ROOT, "config/scenario-009h-bicycle-crossing.yaml")

        try:
            # Per-increment builder
            per_increment_doc = build_crossing_target_evidence(
                raw,
                BENCH_ROOT / "config/scenario-009h-bicycle-crossing.yaml",
                provenance,
                artifacts,
                increment_id="INC-AEBS-009H",
                bench_root=BENCH_ROOT,
            )

            # Framework builder
            from evidence_pipeline import build_evidence, load_contract
            contract = load_contract(BENCH_ROOT / "config/contract-009h.yaml")
            framework_doc = build_evidence(
                raw,
                TargetType.BICYCLE,
                provenance,
                artifacts,
                contract=contract,
                bench_root=BENCH_ROOT,
            )

            # Byte-identical comparison
            per_bytes = canonical_json_bytes(per_increment_doc)
            framework_bytes = canonical_json_bytes(framework_doc)
            assert per_bytes == framework_bytes, (
                f"009H evidence differs between per-increment and framework builders.\n"
                f"Per-increment keys: {sorted(per_increment_doc.keys())}\n"
                f"Framework keys: {sorted(framework_doc.keys())}\n"
            )
        finally:
            shutil.rmtree(BENCH_ROOT / "evidence" / "009h" / "parity_test", ignore_errors=True)
