#!/usr/bin/env python3
"""Independently replay and validate one INC-AEBS-009F degraded-input evidence document."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
for path in (PACKAGE_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_document import (
    canonical_json_bytes,
    load_strict_json,
    sha256_file,
)
from execution_identity import execution_manifest_sha256_at_revision
from degraded_input_evidence import (
    INCREMENT_CONFIG,
    INCREMENT_ID,
    build_degraded_input_evidence,
)
from validate_scenario_evidence import (
    ValidationError,
    _live_provenance_fields,
    _repository_commit_is_ancestor,
    _repository_root,
    _verify_artifacts,
    _verify_map_runtime,
)
from de4sdv_aebs_009b_bench.degraded_input_matrix import DegradedInputScenario


def _profile_subdir(profile: str) -> str:
    return f"{INCREMENT_CONFIG['evidence_dir']}/{profile}"


def _verify_degraded_artifact_paths(
    document: Mapping[str, Any], profile: str
) -> None:
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValidationError("degraded-input artifacts must be an object")
    paths = [
        record.get("path")
        for record in artifacts.values()
        if isinstance(record, Mapping)
    ]
    if len(paths) != len(artifacts) or len(set(paths)) != len(paths):
        raise ValidationError("degraded-input artifact roles require distinct paths")
    prefix = f"{_profile_subdir(profile)}/runs/"
    if any(not isinstance(path, str) or not path.startswith(prefix) for path in paths):
        raise ValidationError("degraded-input artifact path is not scenario-specific")
    run_parents = {str(Path(path).parent) for path in paths}
    if len(run_parents) != 1:
        raise ValidationError("degraded-input artifacts must belong to one isolated run bundle")


def _verify_provenance_degraded(
    stored: Mapping[str, Any],
    bench_root: Path,
    expected_execution_head: str,
) -> None:
    live = _live_provenance_fields(bench_root)
    repository = _repository_root(bench_root)
    live_head = live.pop("repository_head")
    stored_head = stored.get("repository_head")
    if stored_head != expected_execution_head:
        raise ValidationError(
            "recorded degraded-input repository head differs from exact campaign head"
        )
    if not _repository_commit_is_ancestor(repository, expected_execution_head, live_head):
        raise ValidationError(
            "exact degraded-input campaign head is not an ancestor of live HEAD"
        )
    live["execution_manifest_sha256"] = execution_manifest_sha256_at_revision(
        bench_root, expected_execution_head
    )
    live["degraded_input_config_sha256"] = sha256_file(
        bench_root / INCREMENT_CONFIG["config_path"]
    )
    for key, value in live.items():
        if stored.get(key) != value:
            raise ValidationError(f"degraded-input provenance mismatch for {key}")
    required = set(live) | {
        "repository_head",
        "captured_utc",
        "command_exit_code",
        "degraded_input_config_sha256",
    }
    if set(stored) != required:
        raise ValidationError("degraded-input provenance has an open or incomplete shape")
    if stored["command_exit_code"] != 0:
        raise ValidationError("degraded-input observer command did not exit successfully")


def _campaign_execution_head(
    evidence_path: Path,
    document: Mapping[str, Any],
    root: Path,
    profile: str,
    *,
    candidate: bool,
) -> str:
    subdir = _profile_subdir(profile)
    if candidate:
        live_head = _live_provenance_fields(root)["repository_head"]
        if document["provenance"].get("repository_head") != live_head:
            raise ValidationError("degraded-input candidate is not bound to exact live HEAD")
        return live_head
    manifest_path = root / subdir / "campaign-manifest.json"
    try:
        manifest = load_strict_json(manifest_path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(f"cannot parse degraded-input campaign manifest: {error}") from error
    if not isinstance(manifest, Mapping) or set(manifest) != {
        "schema", "increment_id", "execution_head", "scenario",
    }:
        raise ValidationError("degraded-input campaign manifest has an open or incomplete shape")
    scenario = manifest.get("scenario")
    if (
        manifest.get("schema") != INCREMENT_CONFIG["campaign_schema"]
        or manifest.get("increment_id") != INCREMENT_ID
        or not isinstance(scenario, Mapping)
        or set(scenario) != {"path", "run_id", "sha256"}
    ):
        raise ValidationError("degraded-input campaign manifest identity or scenario entry is incorrect")
    relative = f"{subdir}/scenario-evidence.json"
    canonical = (root / relative).resolve(strict=True)
    if evidence_path.resolve(strict=True) != canonical or scenario.get("path") != relative:
        raise ValidationError("degraded-input retained replay path differs from campaign manifest")
    if scenario.get("sha256") != sha256_file(canonical):
        raise ValidationError("degraded-input canonical evidence hash differs from campaign manifest")
    artifact_paths = [record["path"] for record in document["artifacts"].values()]
    run_ids = {Path(path).parent.name for path in artifact_paths}
    if len(run_ids) != 1 or scenario.get("run_id") not in run_ids:
        raise ValidationError("degraded-input run identity differs from campaign manifest")
    execution_head = manifest.get("execution_head")
    if not isinstance(execution_head, str):
        raise ValidationError("degraded-input campaign execution head is malformed")
    return execution_head


def validate_degraded_input_evidence(
    evidence_path: str | Path,
    *,
    profile: str,
    bench_root: str | Path = BENCH_ROOT,
    candidate: bool = False,
) -> Mapping[str, Any]:
    """Independently replay and validate one degraded-input evidence document."""
    try:
        scenario = DegradedInputScenario(profile)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"unknown degraded-input profile: {profile}") from error
    root = Path(bench_root).resolve()
    try:
        document = load_strict_json(evidence_path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(f"cannot parse degraded-input evidence: {error}") from error
    required = {
        "schema",
        "increment_id",
        "scenario_id",
        "degraded_input_profile",
        "provenance",
        "collection",
        "collector_contract",
        "evaluation",
        "artifacts",
        "claim_boundary",
    }
    if not isinstance(document, Mapping) or set(document) != required:
        raise ValidationError("degraded-input evidence root has an open or incomplete shape")
    if document["schema"] != INCREMENT_CONFIG["schema"] or document["increment_id"] != INCREMENT_ID:
        raise ValidationError("degraded-input evidence identity is incorrect")
    if document["degraded_input_profile"] != scenario.value:
        raise ValidationError("degraded-input evidence profile does not match selected profile")
    execution_head = _campaign_execution_head(
        Path(evidence_path), document, root, scenario.value, candidate=candidate
    )
    _verify_degraded_artifact_paths(document, scenario.value)
    artifacts = _verify_artifacts(document, root)
    raw = load_strict_json(artifacts["observer_raw"])
    metadata = load_strict_json(artifacts["run_metadata"])
    if not isinstance(metadata, Mapping) or set(metadata) != {
        "observer_exit_code",
        "raw_output",
    }:
        raise ValidationError("degraded-input run metadata has an open or incomplete shape")
    if metadata["observer_exit_code"] != 0:
        raise ValidationError("hash-bound observer did not exit successfully")
    if metadata["raw_output"] != document["artifacts"]["observer_raw"]["path"]:
        raise ValidationError("run metadata raw path differs from hash-bound artifact")
    rebuilt = build_degraded_input_evidence(
        raw,
        root / INCREMENT_CONFIG["config_path"],
        document["provenance"],
        document["artifacts"],
        profile=scenario.value,
        bench_root=root,
    )
    if canonical_json_bytes(rebuilt) != canonical_json_bytes(document):
        raise ValidationError(
            "canonical degraded-input evidence differs from raw replay reconstruction"
        )
    _verify_map_runtime(document, artifacts, root)
    _verify_provenance_degraded(
        document["provenance"], root, execution_head
    )
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument(
        "--profile",
        required=True,
        choices=[s.value for s in DegradedInputScenario],
    )
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    parser.add_argument("--candidate", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        validate_degraded_input_evidence(
            arguments.evidence,
            profile=arguments.profile,
            bench_root=arguments.bench_root,
            candidate=arguments.candidate,
        )
    except (ValidationError, TypeError, ValueError, KeyError) as error:
        print(f"degraded-input evidence rejected: {error}", file=sys.stderr)
        return 1
    print(f"degraded-input evidence independently replay-validated: {arguments.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
