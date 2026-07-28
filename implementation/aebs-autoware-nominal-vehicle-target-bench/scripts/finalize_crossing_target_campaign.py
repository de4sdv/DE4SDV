#!/usr/bin/env python3
"""Finalize one closed single-scenario INC-AEBS-009G/009H crossing-target campaign."""

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
from crossing_target_evidence import INCREMENT_CONFIG


def finalize_crossing_target_campaign(
    increment_id: str,
    bench_root: str | Path = BENCH_ROOT,
) -> Path:
    root = Path(bench_root).resolve()
    if increment_id not in INCREMENT_CONFIG:
        raise ValueError(f"unknown crossing-target increment: {increment_id}")
    meta = INCREMENT_CONFIG[increment_id]
    evidence_dir = root / meta["evidence_dir"]
    manifest_path = evidence_dir / "campaign-manifest.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise ValueError(
            f"refusing to overwrite existing {increment_id} campaign manifest"
        )
    relative = f"{meta['evidence_dir']}/scenario-evidence.json"
    canonical = root / relative
    if canonical.is_symlink() or not canonical.is_file():
        raise ValueError(f"missing or unsafe canonical {increment_id} evidence")
    document = load_strict_json(canonical)
    if document.get("increment_id") != increment_id:
        raise ValueError("canonical evidence increment differs from manifest slot")
    provenance = document.get("provenance")
    artifacts = document.get("artifacts")
    if not isinstance(provenance, dict) or not isinstance(artifacts, dict):
        raise ValueError(f"canonical {increment_id} document is incomplete")
    execution_head = provenance.get("repository_head")
    if not isinstance(execution_head, str):
        raise ValueError(f"canonical {increment_id} execution head is malformed")
    run_ids = {
        Path(record["path"]).parent.name
        for record in artifacts.values()
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    if len(run_ids) != 1:
        raise ValueError(f"canonical {increment_id} artifacts do not identify one run")
    manifest = {
        "schema": meta["campaign_schema"],
        "increment_id": increment_id,
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
        "--increment",
        required=True,
        choices=list(INCREMENT_CONFIG),
    )
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    try:
        manifest = finalize_crossing_target_campaign(
            arguments.increment, arguments.bench_root
        )
        from validate_crossing_target_evidence import validate_crossing_target_evidence

        meta = INCREMENT_CONFIG[arguments.increment]
        validate_crossing_target_evidence(
            arguments.bench_root / meta["evidence_dir"] / "scenario-evidence.json",
            increment_id=arguments.increment,
            bench_root=arguments.bench_root,
        )
    except (OSError, TypeError, ValueError, KeyError) as error:
        print(f"{arguments.increment} campaign finalization rejected: {error}", file=sys.stderr)
        return 1
    print(f"Finalized and replay-validated {arguments.increment} campaign manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
