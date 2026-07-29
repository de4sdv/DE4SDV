#!/usr/bin/env python3
"""Construct one configuration-bounded INC-AEBS-009I criterion measurement document.

This module derives regulatory measurements from retained 009G/009H evidence
and evaluates them through the controlled criterion evaluator.  It never
produces a compliance, homologation, certification, or type-approval conclusion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCH_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"

for path in (REPO_ROOT, SCRIPTS_ROOT, PACKAGE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import yaml  # noqa: E402
from evidence_document import canonical_json_bytes, load_strict_json, sha256_file, write_evidence_atomic  # noqa: E402

CRITERIA_PATH = REPO_ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-criteria.yaml"
SOURCE_PATH = REPO_ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml"
EVALUATOR_PATH = REPO_ROOT / "scripts" / "aebs_regulatory_criteria.py"


def _load_yaml(path: Path) -> Any:
    """Load a YAML file with duplicate-key rejection."""
    def _pairs(items):
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate YAML key: {key}")
            result[key] = value
        return result
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)

SCHEMA_ID = "de4sdv.aebs-009i.criterion-measurement-evidence.v1"
INCREMENT_ID = "INC-AEBS-009I"


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _validate_measurement(measurement: Mapping[str, Any]) -> None:
    """Validate the closed measurement shape before evaluation."""
    required_keys = {
        "scenario_family",
        "vehicle_category",
        "load_condition",
        "subject_speed_kmh",
        "target_speed_kmh",
        "warning_time_s",
        "braking_start_time_s",
        "minimum_braking_demand_mps2",
        "impact_speed_kmh",
        "successful_repetitions",
        "failed_repetitions",
        "conditions",
    }
    if not isinstance(measurement, Mapping):
        raise TypeError("measurement must be a mapping")
    actual = set(measurement)
    if actual != required_keys:
        missing = sorted(required_keys - actual)
        extra = sorted(actual - required_keys)
        raise ValueError(
            f"measurement keys mismatch: missing={missing}, extra={extra}"
        )
    for key in ("scenario_family", "vehicle_category", "load_condition"):
        if not isinstance(measurement[key], str) or not measurement[key]:
            raise TypeError(f"{key} must be a nonempty string")
    for key in (
        "subject_speed_kmh",
        "target_speed_kmh",
        "warning_time_s",
        "braking_start_time_s",
        "minimum_braking_demand_mps2",
        "impact_speed_kmh",
    ):
        _finite_number(f"measurement.{key}", measurement[key])
    for key in ("successful_repetitions", "failed_repetitions"):
        if isinstance(measurement[key], bool) or not isinstance(measurement[key], int):
            raise TypeError(f"measurement.{key} must be an integer")
        if measurement[key] < 0:
            raise ValueError(f"measurement.{key} must be non-negative")
    conditions = measurement["conditions"]
    if not isinstance(conditions, Mapping):
        raise TypeError("measurement.conditions must be a mapping")
    if not all(isinstance(v, bool) for v in conditions.values()):
        raise TypeError("all condition values must be boolean")


def _validate_source_identity(source: Mapping[str, Any]) -> None:
    """Validate the controlled source metadata is hash-bound and closed."""
    required = {
        "schema", "source_id", "document_date", "series",
        "original_sha256", "extraction_sha256", "acquisition",
        "extraction", "selected_clause_anchors", "criterion_provenance",
        "applicability", "claim_boundary",
    }
    if not isinstance(source, Mapping) or set(source) != required:
        raise ValueError("regulatory source metadata has an open or incomplete shape")
    if source["schema"] != "de4sdv.aebs-regulatory-source.v2":
        raise ValueError("regulatory source schema mismatch")
    if source["source_id"] != "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2":
        raise ValueError("regulatory source identity mismatch")
    boundary = source["claim_boundary"]
    if not isinstance(boundary, Mapping):
        raise TypeError("claim_boundary must be a mapping")
    if boundary.get("compliance_claim_permitted") is not False:
        raise ValueError("compliance claim must be forbidden")
    if boundary.get("allowed_result") != "configuration-bounded criterion and evidence-fitness result":
        raise ValueError("allowed result mismatch")


def _validate_criteria(criteria: Mapping[str, Any]) -> None:
    """Validate the criterion mapping is closed and source-bound."""
    required = {
        "schema", "source_id", "source_original_sha256",
        "result_vocabulary", "common", "families",
        "required_conditions", "claim_boundary",
    }
    if not isinstance(criteria, Mapping) or set(criteria) != required:
        raise ValueError("regulatory criteria has an open or incomplete shape")
    if criteria["schema"] != "de4sdv.aebs-regulatory-criteria.v1":
        raise ValueError("criterion mapping schema mismatch")
    if criteria["source_id"] != "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2":
        raise ValueError("criterion mapping source identity mismatch")
    if criteria["result_vocabulary"] != ["pass", "fail", "inconclusive"]:
        raise ValueError("result vocabulary mismatch")


def _validate_retained_evidence_reference(
    evidence_ref: Mapping[str, Any],
    bench_root: Path,
) -> None:
    """Validate that a retained evidence reference points to a real file with matching hash."""
    required = {"path", "sha256", "increment_id"}
    if not isinstance(evidence_ref, Mapping) or set(evidence_ref) != required:
        raise ValueError("retained evidence reference has an open shape")
    path = evidence_ref["path"]
    if not isinstance(path, str) or not path:
        raise ValueError("retained evidence path must be a nonempty string")
    resolved = bench_root / path
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"retained evidence file is missing or unsafe: {path}")
    actual = sha256_file(resolved)
    if actual != evidence_ref["sha256"]:
        raise ValueError(f"retained evidence SHA-256 mismatch for {path}")


def build_criterion_measurement_evidence(
    measurement: Mapping[str, Any],
    retained_evidence: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, Any],
    *,
    bench_root: Path = BENCH_ROOT,
) -> dict[str, Any]:
    """Build one configuration-bounded criterion measurement document.

    The evaluator always withholds compliance.  The evidence fitness is
    inconclusive until a separate retained-evidence evaluator derives
    measurements from immutable, pairwise-distinct run artifacts.
    """
    _validate_measurement(measurement)

    source = _load_yaml(SOURCE_PATH)
    _validate_source_identity(source)

    criteria = _load_yaml(CRITERIA_PATH)
    _validate_criteria(criteria)

    # Validate all retained evidence references
    if not isinstance(retained_evidence, list) or len(retained_evidence) == 0:
        raise ValueError("at least one retained evidence reference is required")
    for ref in retained_evidence:
        _validate_retained_evidence_reference(ref, bench_root)

    # Check pairwise-distinct run IDs
    run_ids = set()
    for ref in retained_evidence:
        path_parts = Path(ref["path"]).parts
        if len(path_parts) < 2:
            raise ValueError("retained evidence path is too short")
        run_id = path_parts[-2] if path_parts[-1].startswith("scenario-evidence") else path_parts[-1]
        if run_id in run_ids:
            raise ValueError(f"retained evidence run IDs are not pairwise distinct: {run_id}")
        run_ids.add(run_id)

    # Import and run the evaluator
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.aebs_regulatory_criteria import evaluate_regulatory_measurement  # noqa: E402

    result = evaluate_regulatory_measurement(measurement)

    # Build the provenance hash chain
    source_metadata_hash = sha256_file(SOURCE_PATH)
    criteria_hash = sha256_file(CRITERIA_PATH)
    evaluator_hash = sha256_file(EVALUATOR_PATH)

    # Verify provenance consistency
    if result["source_id"] != source["source_id"]:
        raise ValueError("evaluator source identity mismatch")
    if result["source_original_sha256"] != source["original_sha256"]:
        raise ValueError("evaluator source hash mismatch")

    # The evaluator always returns inconclusive for evidence_fitness
    # because it cannot verify retained-evidence provenance from caller-supplied values.
    if result["criterion_result"] != "inconclusive":
        raise ValueError("criterion result must be inconclusive from the evaluator API")

    return {
        "schema": SCHEMA_ID,
        "increment_id": INCREMENT_ID,
        "measurement": dict(measurement),
        "retained_evidence": list(retained_evidence),
        "provenance": {
            **dict(provenance),
            "source_metadata_path": str(SOURCE_PATH.relative_to(REPO_ROOT)),
            "source_metadata_sha256": source_metadata_hash,
            "criteria_path": str(CRITERIA_PATH.relative_to(REPO_ROOT)),
            "criteria_sha256": criteria_hash,
            "evaluator_path": str(EVALUATOR_PATH.relative_to(REPO_ROOT)),
            "evaluator_sha256": evaluator_hash,
            "source_original_sha256": source["original_sha256"],
            "source_id": source["source_id"],
        },
        "evaluation": {
            "threshold_result": result["threshold_result"],
            "evidence_fitness": result["evidence_fitness"],
            "criterion_result": result["criterion_result"],
            "failed_thresholds": result["failed_thresholds"],
            "unestablished_conditions": result["unestablished_conditions"],
            "maximum_impact_speed_kmh": result["maximum_impact_speed_kmh"],
            "regulatory_conclusion": result["regulatory_conclusion"],
        },
        "claim_boundary": "configuration_bounded_criterion_only_no_compliance_or_type_approval_claim",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", required=True, type=Path)
    parser.add_argument("--retained-evidence", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)

    measurement = load_strict_json(arguments.measurement)
    retained = load_strict_json(arguments.retained_evidence)
    provenance = load_strict_json(arguments.provenance)

    document = build_criterion_measurement_evidence(
        measurement,
        retained,
        provenance,
        bench_root=arguments.bench_root,
    )
    write_evidence_atomic(document, arguments.output, arguments.bench_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
