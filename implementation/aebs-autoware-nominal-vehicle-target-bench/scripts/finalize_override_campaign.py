#!/usr/bin/env python3
"""Finalize one closed six-profile INC-AEBS-009D retained campaign."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src/de4sdv_aebs_009b_bench"
for path in (PACKAGE_ROOT, Path(__file__).resolve().parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from de4sdv_aebs_009b_bench.override_matrix import OverrideScenario
from evidence_document import load_strict_json, sha256_file


def finalize_campaign(bench_root: str | Path = BENCH_ROOT) -> Path:
    root = Path(bench_root).resolve()
    manifest_path = root / "evidence/009d/campaign-manifest.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise ValueError("refusing to overwrite existing 009D campaign manifest")
    profiles: dict[str, dict[str, str]] = {}
    execution_heads: set[str] = set()
    for profile in OverrideScenario:
        relative = f"evidence/009d/profiles/{profile.value}/scenario-evidence.json"
        canonical = root / relative
        if canonical.is_symlink() or not canonical.is_file():
            raise ValueError(f"missing or unsafe canonical 009D profile: {profile.value}")
        document = load_strict_json(canonical)
        if document.get("profile") != profile.value:
            raise ValueError("009D canonical profile differs from manifest slot")
        provenance = document.get("provenance")
        artifacts = document.get("artifacts")
        if not isinstance(provenance, dict) or not isinstance(artifacts, dict):
            raise ValueError("009D canonical document is incomplete")
        execution_head = provenance.get("repository_head")
        if not isinstance(execution_head, str):
            raise ValueError("009D canonical execution head is malformed")
        execution_heads.add(execution_head)
        run_ids = {
            Path(record["path"]).parent.name
            for record in artifacts.values()
            if isinstance(record, dict) and isinstance(record.get("path"), str)
        }
        if len(run_ids) != 1:
            raise ValueError("009D canonical artifacts do not identify one run")
        profiles[profile.value] = {
            "path": relative,
            "run_id": run_ids.pop(),
            "sha256": sha256_file(canonical),
        }
    if len(execution_heads) != 1 or not isinstance(next(iter(execution_heads)), str):
        raise ValueError("009D canonical profiles are not bound to one execution head")
    document = {
        "schema": "de4sdv.aebs-009d.campaign-manifest.v1",
        "increment_id": "INC-AEBS-009D",
        "execution_head": execution_heads.pop(),
        "profiles": profiles,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".campaign-manifest.", dir=manifest_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(document, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, manifest_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return manifest_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    try:
        manifest = finalize_campaign(arguments.bench_root)
        from validate_override_evidence import validate_override_evidence

        for profile in OverrideScenario:
            validate_override_evidence(
                arguments.bench_root
                / f"evidence/009d/profiles/{profile.value}/scenario-evidence.json",
                bench_root=arguments.bench_root,
            )
    except (OSError, TypeError, ValueError, KeyError) as error:
        print(f"009D campaign finalization rejected: {error}", file=sys.stderr)
        return 1
    print(f"Finalized and replay-validated 009D campaign manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
