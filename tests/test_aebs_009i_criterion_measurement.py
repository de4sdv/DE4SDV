"""Pure tests for INC-AEBS-009I criterion measurement evidence builder and validator.

These tests verify the closed-contract, fail-closed, source-bound, and
compliance-withheld properties of the 009I measurement evidence pipeline
without requiring a live runtime or retained evidence files.
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

for path in (REPO_ROOT, SCRIPTS_ROOT, BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _fit_measurement() -> dict:
    return {
        "scenario_family": "pedestrian",
        "vehicle_category": "M1",
        "load_condition": "mass_in_running_order",
        "subject_speed_kmh": 20.0,
        "target_speed_kmh": 5.0,
        "warning_time_s": 1.0,
        "braking_start_time_s": 1.1,
        "minimum_braking_demand_mps2": -5.0,
        "impact_speed_kmh": 0.0,
        "successful_repetitions": 2,
        "failed_repetitions": 0,
        "conditions": {
            "flat_dry_high_adhesion_surface": True,
            "pbc_at_least_0_9": True,
            "slope_between_0_and_1_percent": True,
            "temperature_between_0_and_45_c": True,
            "visibility_complete": True,
            "wind_not_result_affecting": True,
            "illumination_at_least_2000_lux": True,
            "prescribed_mass_controlled": True,
            "prescribed_soft_target_fidelity": True,
            "straight_approach_at_least_2_s": True,
            "functional_start_ttc_at_least_4_s": True,
            "impact_offset_within_0_1_m": True,
            "no_disallowed_driver_adjustment": True,
            "measurement_uncertainty_controlled": True,
        },
    }


def _make_retained_evidence_ref(bench_root: Path) -> tuple[Path, dict]:
    """Create a temporary evidence file and return its path and reference dict."""
    evidence_dir = bench_root / "evidence" / "009i" / "test_fixtures"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    run_dir = evidence_dir / "test-run-001"
    run_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = run_dir / "scenario-evidence.json"
    content = {"schema": "test", "increment_id": "INC-AEBS-009G"}
    evidence_file.write_text(json.dumps(content) + "\n", encoding="utf-8")
    relative = str(evidence_file.relative_to(bench_root))
    import hashlib
    sha = hashlib.sha256(evidence_file.read_bytes()).hexdigest()
    return evidence_file, {
        "path": relative,
        "sha256": sha,
        "increment_id": "INC-AEBS-009G",
    }


def _make_provenance() -> dict:
    return {
        "repository_head": "abc123def456",
        "captured_utc": "2026-07-28T10:00:00Z",
        "host_arch": "aarch64",
        "runtime_lock_sha256": "fake_lock_hash",
        "image_digest": "sha256:fake_digest",
        "execution_manifest_sha256": "fake_manifest_hash",
        "map_digest": "sha256:fake_map",
    }


class TestCriterionMeasurementEvidenceBuilder:
    def test_builds_a_closed_evidence_document(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence

        measurement = _fit_measurement()
        evidence_file, ref = _make_retained_evidence_ref(BENCH_ROOT)
        try:
            document = build_criterion_measurement_evidence(
                measurement, [ref], _make_provenance(), bench_root=BENCH_ROOT,
            )
            assert document["schema"] == "de4sdv.aebs-009i.criterion-measurement-evidence.v1"
            assert document["increment_id"] == "INC-AEBS-009I"
            assert "measurement" in document
            assert "retained_evidence" in document
            assert "provenance" in document
            assert "evaluation" in document
            assert document["claim_boundary"] == (
                "configuration_bounded_criterion_only_no_compliance_or_type_approval_claim"
            )
        finally:
            import shutil
            shutil.rmtree(BENCH_ROOT / "evidence" / "009i" / "test_fixtures", ignore_errors=True)

    def test_evaluator_result_is_always_inconclusive(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence

        measurement = _fit_measurement()
        evidence_file, ref = _make_retained_evidence_ref(BENCH_ROOT)
        try:
            document = build_criterion_measurement_evidence(
                measurement, [ref], _make_provenance(), bench_root=BENCH_ROOT,
            )
            assert document["evaluation"]["criterion_result"] == "inconclusive"
            assert document["evaluation"]["evidence_fitness"] == "inconclusive"
            assert document["evaluation"]["regulatory_conclusion"] == "withheld"
        finally:
            import shutil
            shutil.rmtree(BENCH_ROOT / "evidence" / "009i" / "test_fixtures", ignore_errors=True)

    def test_source_identity_is_hash_bound(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence

        measurement = _fit_measurement()
        evidence_file, ref = _make_retained_evidence_ref(BENCH_ROOT)
        try:
            document = build_criterion_measurement_evidence(
                measurement, [ref], _make_provenance(), bench_root=BENCH_ROOT,
            )
            provenance = document["provenance"]
            assert provenance["source_id"] == "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2"
            assert provenance["source_original_sha256"] == (
                "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de"
            )
            assert provenance["source_metadata_sha256"] is not None
            assert provenance["criteria_sha256"] is not None
            assert provenance["evaluator_sha256"] is not None
        finally:
            import shutil
            shutil.rmtree(BENCH_ROOT / "evidence" / "009i" / "test_fixtures", ignore_errors=True)

    def test_missing_retained_evidence_rejected(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence

        measurement = _fit_measurement()
        fake_ref = {
            "path": "evidence/nonexistent/scenario-evidence.json",
            "sha256": "0" * 64,
            "increment_id": "INC-AEBS-009G",
        }
        with pytest.raises(ValueError, match="missing or unsafe"):
            build_criterion_measurement_evidence(
                measurement, [fake_ref], _make_provenance(), bench_root=BENCH_ROOT,
            )

    def test_malformed_measurement_rejected(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence

        measurement = _fit_measurement()
        measurement["invented_field"] = "bad"
        evidence_file, ref = _make_retained_evidence_ref(BENCH_ROOT)
        try:
            with pytest.raises(ValueError, match="measurement keys"):
                build_criterion_measurement_evidence(
                    measurement, [ref], _make_provenance(), bench_root=BENCH_ROOT,
                )
        finally:
            import shutil
            shutil.rmtree(BENCH_ROOT / "evidence" / "009i" / "test_fixtures", ignore_errors=True)

    def test_empty_retained_evidence_rejected(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence

        measurement = _fit_measurement()
        with pytest.raises(ValueError, match="at least one retained evidence"):
            build_criterion_measurement_evidence(
                measurement, [], _make_provenance(), bench_root=BENCH_ROOT,
            )


class TestCriterionMeasurementEvidenceValidator:
    def test_validates_a_well_formed_document(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence
        from validate_criterion_measurement_evidence import validate_criterion_measurement_evidence

        measurement = _fit_measurement()
        evidence_file, ref = _make_retained_evidence_ref(BENCH_ROOT)
        try:
            document = build_criterion_measurement_evidence(
                measurement, [ref], _make_provenance(), bench_root=BENCH_ROOT,
            )
            # Write the evidence to a temp file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, dir=str(BENCH_ROOT)
            ) as tmp:
                json.dump(document, tmp, sort_keys=True, separators=(",", ":"))
                tmp.write("\n")
                tmp_path = Path(tmp.name)
            try:
                result = validate_criterion_measurement_evidence(tmp_path, bench_root=BENCH_ROOT)
                assert result["schema"] == "de4sdv.aebs-009i.criterion-measurement-evidence.v1"
            finally:
                tmp_path.unlink(missing_ok=True)
        finally:
            import shutil
            shutil.rmtree(BENCH_ROOT / "evidence" / "009i" / "test_fixtures", ignore_errors=True)

    def test_rejects_missing_compliance_boundary(self) -> None:
        from criterion_measurement_evidence import build_criterion_measurement_evidence
        from validate_criterion_measurement_evidence import ValidationError, validate_criterion_measurement_evidence

        measurement = _fit_measurement()
        evidence_file, ref = _make_retained_evidence_ref(BENCH_ROOT)
        try:
            document = build_criterion_measurement_evidence(
                measurement, [ref], _make_provenance(), bench_root=BENCH_ROOT,
            )
            document["claim_boundary"] = "wrong_boundary"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, dir=str(BENCH_ROOT)
            ) as tmp:
                json.dump(document, tmp, sort_keys=True, separators=(",", ":"))
                tmp.write("\n")
                tmp_path = Path(tmp.name)
            try:
                with pytest.raises(ValidationError, match="claim boundary"):
                    validate_criterion_measurement_evidence(tmp_path, bench_root=BENCH_ROOT)
            finally:
                tmp_path.unlink(missing_ok=True)
        finally:
            import shutil
            shutil.rmtree(BENCH_ROOT / "evidence" / "009i" / "test_fixtures", ignore_errors=True)
