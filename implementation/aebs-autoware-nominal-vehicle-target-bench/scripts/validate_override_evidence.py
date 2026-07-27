#!/usr/bin/env python3
"""Independently replay and validate one hash-bound INC-AEBS-009D profile."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src/de4sdv_aebs_009b_bench"
for path in (PACKAGE_ROOT, Path(__file__).resolve().parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from de4sdv_aebs_009b_bench.override_matrix import OverrideScenario
from evidence_document import (
    canonical_json_bytes,
    load_strict_json,
    sha256_file,
)
from execution_identity import override_execution_manifest_sha256
from override_evidence import build_override_evidence
from validate_scenario_evidence import (
    ValidationError,
    _live_provenance_fields,
    _repository_commit_is_ancestor,
    _repository_root,
    _verify_artifacts,
    _verify_map_runtime,
)


def _verify_009d_artifact_paths(
    document: Mapping[str, Any], profile: OverrideScenario
) -> None:
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValidationError("009D artifacts must be an object")
    paths = [
        record.get("path")
        for record in artifacts.values()
        if isinstance(record, Mapping)
    ]
    if len(paths) != len(artifacts) or len(set(paths)) != len(paths):
        raise ValidationError("009D artifact roles require distinct paths")
    prefix = f"evidence/009d/profiles/{profile.value}/runs/"
    if any(not isinstance(path, str) or not path.startswith(prefix) for path in paths):
        raise ValidationError("009D artifact path is not profile-specific")
    run_parents = {str(Path(path).parent) for path in paths}
    if len(run_parents) != 1:
        raise ValidationError("009D artifacts must belong to one isolated run bundle")


def _verify_provenance_009d(
    stored: Mapping[str, Any], bench_root: Path, profile: OverrideScenario
) -> None:
    live = _live_provenance_fields(bench_root)
    repository = _repository_root(bench_root)
    live_head = live.pop("repository_head")
    stored_head = stored.get("repository_head")
    if not isinstance(stored_head, str) or not _repository_commit_is_ancestor(
        repository, stored_head, live_head
    ):
        raise ValidationError(
            "recorded 009D repository head is not an ancestor of live HEAD"
        )
    for key, value in live.items():
        if stored.get(key) != value:
            raise ValidationError(f"009D provenance mismatch for {key}")
    expected_extra = {
        "override_profile": profile.value,
        "override_execution_manifest_sha256": override_execution_manifest_sha256(
            bench_root, profile.value
        ),
        "override_matrix_sha256": sha256_file(
            bench_root / "config/scenario-009d-conscious-override-matrix.yaml"
        ),
    }
    for key, value in expected_extra.items():
        if stored.get(key) != value:
            raise ValidationError(f"009D provenance mismatch for {key}")
    required = set(live) | {
        "repository_head",
        "captured_utc",
        "command_exit_code",
        *expected_extra,
    }
    if set(stored) != required:
        raise ValidationError("009D provenance has an open or incomplete shape")
    if stored["command_exit_code"] != 0:
        raise ValidationError("009D observer command did not exit successfully")


def validate_override_evidence(
    evidence_path: str | Path, *, bench_root: str | Path = BENCH_ROOT
) -> Mapping[str, Any]:
    root = Path(bench_root).resolve()
    try:
        document = load_strict_json(evidence_path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(f"cannot parse 009D evidence: {error}") from error
    required = {
        "schema",
        "increment_id",
        "profile",
        "scenario_id",
        "provenance",
        "collection",
        "collector_contract",
        "evaluation",
        "artifacts",
        "claim_boundary",
    }
    if not isinstance(document, Mapping) or set(document) != required:
        raise ValidationError("009D evidence root has an open or incomplete shape")
    if (
        document["schema"] != "de4sdv.aebs-009d.override-evidence.v1"
        or document["increment_id"] != "INC-AEBS-009D"
    ):
        raise ValidationError("009D evidence identity is incorrect")
    try:
        profile = OverrideScenario(document["profile"])
    except (TypeError, ValueError) as error:
        raise ValidationError("009D evidence profile is unknown") from error
    _verify_009d_artifact_paths(document, profile)
    artifacts = _verify_artifacts(document, root)
    raw = load_strict_json(artifacts["observer_raw"])
    metadata = load_strict_json(artifacts["run_metadata"])
    if not isinstance(metadata, Mapping) or set(metadata) != {
        "observer_exit_code",
        "raw_output",
        "override_profile",
    }:
        raise ValidationError("009D run metadata has an open or incomplete shape")
    if metadata["override_profile"] != profile.value:
        raise ValidationError("run metadata profile differs from canonical profile")
    if metadata["observer_exit_code"] != 0:
        raise ValidationError("hash-bound observer did not exit successfully")
    if metadata["raw_output"] != document["artifacts"]["observer_raw"]["path"]:
        raise ValidationError("run metadata raw path differs from hash-bound artifact")
    rebuilt = build_override_evidence(
        raw,
        profile,
        document["provenance"],
        document["artifacts"],
        matrix_path=root / "config/scenario-009d-conscious-override-matrix.yaml",
    )
    if canonical_json_bytes(rebuilt) != canonical_json_bytes(document):
        raise ValidationError(
            "canonical 009D evidence differs from raw replay reconstruction"
        )
    _verify_map_runtime(document, artifacts, root)
    _verify_provenance_009d(document["provenance"], root, profile)
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    try:
        validate_override_evidence(arguments.evidence, bench_root=arguments.bench_root)
    except (ValidationError, TypeError, ValueError, KeyError) as error:
        print(f"009D evidence rejected: {error}", file=sys.stderr)
        return 1
    print(f"009D profile evidence independently replay-validated: {arguments.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
