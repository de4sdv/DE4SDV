#!/usr/bin/env python3
"""Independently replay and validate one INC-AEBS-009I criterion measurement document."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCH_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"

for path in (REPO_ROOT, SCRIPTS_ROOT, PACKAGE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_document import load_strict_json, sha256_file  # noqa: E402

CRITERIA_PATH = REPO_ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-criteria.yaml"
SOURCE_PATH = REPO_ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml"
EVALUATOR_PATH = REPO_ROOT / "scripts" / "aebs_regulatory_criteria.py"

SCHEMA_ID = "de4sdv.aebs-009i.criterion-measurement-evidence.v1"


class ValidationError(ValueError):
    """A fail-closed evidence rejection with a user-facing reason."""


def _validate_retained_evidence_reference(
    evidence_ref: Mapping[str, Any],
    bench_root: Path,
) -> None:
    required = {"path", "sha256", "increment_id"}
    if not isinstance(evidence_ref, Mapping) or set(evidence_ref) != required:
        raise ValidationError("retained evidence reference has an open shape")
    path = evidence_ref["path"]
    if not isinstance(path, str) or not path:
        raise ValidationError("retained evidence path must be a nonempty string")
    resolved = bench_root / path
    if not resolved.is_file() or resolved.is_symlink():
        raise ValidationError(f"retained evidence file is missing or unsafe: {path}")
    actual = sha256_file(resolved)
    if actual != evidence_ref["sha256"]:
        raise ValidationError(f"retained evidence SHA-256 mismatch for {path}")


def validate_criterion_measurement_evidence(
    evidence_path: str | Path,
    *,
    bench_root: str | Path = BENCH_ROOT,
) -> Mapping[str, Any]:
    root = Path(bench_root).resolve()
    repo_root = root.parents[1]  # BENCH_ROOT/implementation/aebs-autoware-nominal-vehicle-target-bench -> repo root
    try:
        document = load_strict_json(evidence_path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(f"cannot parse 009I evidence: {error}") from error

    required = {
        "schema", "increment_id", "measurement", "retained_evidence",
        "provenance", "evaluation", "claim_boundary",
    }
    if not isinstance(document, Mapping) or set(document) != required:
        raise ValidationError("009I evidence root has an open or incomplete shape")
    if document["schema"] != SCHEMA_ID:
        raise ValidationError("009I evidence schema mismatch")
    if document["increment_id"] != "INC-AEBS-009I":
        raise ValidationError("009I evidence increment mismatch")

    provenance = document["provenance"]
    if not isinstance(provenance, Mapping):
        raise ValidationError("009I provenance must be a mapping")

    # Source metadata, criteria, and evaluator paths are relative to repo root
    for key, label in (
        ("source_metadata_path", "source metadata"),
        ("criteria_path", "criteria"),
        ("evaluator_path", "evaluator"),
    ):
        rel_path = provenance.get(key)
        if not isinstance(rel_path, str):
            raise ValidationError(f"{key} must be a string")
        resolved = repo_root / rel_path
        if not resolved.is_file():
            raise ValidationError(f"{label} file missing: {rel_path}")
        hash_key = key.replace("_path", "_sha256")
        if sha256_file(resolved) != provenance.get(hash_key):
            raise ValidationError(f"{label} SHA-256 mismatch")

    # Verify retained evidence references (relative to bench root)
    retained = document["retained_evidence"]
    if not isinstance(retained, list) or len(retained) == 0:
        raise ValidationError("at least one retained evidence reference is required")
    for ref in retained:
        _validate_retained_evidence_reference(ref, root)

    # Check pairwise-distinct run IDs
    run_ids = set()
    for ref in retained:
        path_parts = Path(ref["path"]).parts
        if len(path_parts) < 2:
            raise ValidationError("retained evidence path is too short")
        run_id = path_parts[-2] if path_parts[-1].startswith("scenario-evidence") else path_parts[-1]
        if run_id in run_ids:
            raise ValidationError(f"retained evidence run IDs are not pairwise distinct: {run_id}")
        run_ids.add(run_id)

    # Re-run the evaluator independently
    sys.path.insert(0, str(root))
    from scripts.aebs_regulatory_criteria import evaluate_regulatory_measurement  # noqa: E402

    measurement = document["measurement"]
    result = evaluate_regulatory_measurement(measurement)

    evaluation = document["evaluation"]
    if not isinstance(evaluation, Mapping):
        raise ValidationError("evaluation must be a mapping")

    # Verify evaluator result matches
    for key in (
        "threshold_result", "evidence_fitness", "criterion_result",
        "failed_thresholds", "unestablished_conditions",
        "maximum_impact_speed_kmh", "regulatory_conclusion",
    ):
        if evaluation.get(key) != result.get(key):
            raise ValidationError(f"evaluator result mismatch for {key}")

    # The regulatory conclusion must always be withheld
    if evaluation.get("regulatory_conclusion") != "withheld":
        raise ValidationError("regulatory conclusion must be withheld")

    # The criterion result must be inconclusive from the evaluator API
    if evaluation.get("criterion_result") != "inconclusive":
        raise ValidationError("criterion result must be inconclusive")

    # Claim boundary must be explicit
    if document.get("claim_boundary") != "configuration_bounded_criterion_only_no_compliance_or_type_approval_claim":
        raise ValidationError("claim boundary mismatch")

    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_path", type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    try:
        validate_criterion_measurement_evidence(
            arguments.evidence_path, bench_root=arguments.bench_root
        )
    except ValidationError as error:
        print(f"009I criterion measurement evidence rejected: {error}", file=sys.stderr)
        return 1
    print(f"009I criterion measurement evidence validated: {arguments.evidence_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
