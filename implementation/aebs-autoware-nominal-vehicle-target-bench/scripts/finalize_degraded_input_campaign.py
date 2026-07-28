#!/usr/bin/env python3
"""Finalize one closed single-profile INC-AEBS-009F degraded-input campaign."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
for path in (PACKAGE_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_document import load_strict_json, sha256_file
from degraded_input_evidence import INCREMENT_CONFIG, INCREMENT_ID
from de4sdv_aebs_009b_bench.degraded_input_matrix import DegradedInputScenario


def _profile_subdir(profile: str) -> str:
    return f"{INCREMENT_CONFIG['evidence_dir']}/{profile}"


def finalize_degraded_input_campaign(
    profile: str,
    bench_root: str | Path = BENCH_ROOT,
) -> Path:
    root = Path(bench_root).resolve()
    try:
        scenario = DegradedInputScenario(profile)
    except (TypeError, ValueError) as error:
        raise ValueError(f"unknown degraded-input profile: {profile}") from error
    subdir = _profile_subdir(scenario.value)
    evidence_dir = root / subdir
    manifest_path = evidence_dir / "campaign-manifest.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise ValueError(
            f"refusing to overwrite existing 009F/{scenario.value} campaign manifest"
        )
    relative = f"{subdir}/scenario-evidence.json"
    canonical = root / relative
    if canonical.is_symlink() or not canonical.is_file():
        raise ValueError(f"missing or unsafe canonical 009F/{scenario.value} evidence")
    document = load_strict_json(canonical)
    if document.get("increment_id") != INCREMENT_ID:
        raise ValueError("canonical evidence increment differs from manifest slot")
    if document.get("degraded_input_profile") != scenario.value:
        raise ValueError("canonical evidence profile differs from manifest slot")
    provenance = document.get("provenance")
    artifacts = document.get("artifacts")
    if not isinstance(provenance, dict) or not isinstance(artifacts, dict):
        raise ValueError(f"canonical 009F/{scenario.value} document is incomplete")
    execution_head = provenance.get("repository_head")
    if not isinstance(execution_head, str):
        raise ValueError(f"canonical 009F/{scenario.value} execution head is malformed")
    run_ids = {
        Path(record["path"]).parent.name
        for record in artifacts.values()
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    if len(run_ids) != 1:
        raise ValueError(f"canonical 009F/{scenario.value} artifacts do not identify one run")
    manifest = {
        "schema": INCREMENT_CONFIG["campaign_schema"],
        "increment_id": INCREMENT_ID,
        "execution_head": execution_head,
        "scenario": {
            "path": relative,
            "run_id": run_ids.pop(),
            "sha256": sha256_file(canonical),
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".campaign-manifest.", dir=manifest_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(manifest, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, manifest_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return manifest_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        required=True,
        choices=[s.value for s in DegradedInputScenario],
    )
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    try:
        manifest = finalize_degraded_input_campaign(
            arguments.profile, arguments.bench_root
        )
        from validate_degraded_input_evidence import validate_degraded_input_evidence

        validate_degraded_input_evidence(
            arguments.bench_root / _profile_subdir(arguments.profile) / "scenario-evidence.json",
            profile=arguments.profile,
            bench_root=arguments.bench_root,
        )
    except (OSError, TypeError, ValueError, KeyError) as error:
        print(f"009F/{arguments.profile} campaign finalization rejected: {error}", file=sys.stderr)
        return 1
    print(f"Finalized and replay-validated 009F/{arguments.profile} campaign manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
