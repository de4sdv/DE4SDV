#!/usr/bin/env python3
"""Verify the exact extracted map files immediately before runtime launch."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import yaml

from execution_identity import execution_manifest_sha256


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--bench", type=Path)
    args = parser.parse_args()

    bench = args.bench.resolve() if args.bench else Path(__file__).resolve().parents[1]
    root = bench.parents[1]
    lock_path = bench / "runtime-lock.yaml"
    lock = yaml.safe_load(lock_path.read_text())
    destination = args.cache / lock["map"]["extracted_directory"]
    expected_files = lock["map"]["extracted_sha256"]
    observed_files: dict[str, str] = {}
    status = 1
    error = None
    try:
        if not destination.is_dir():
            raise ValueError(f"missing extracted map directory: {destination}")
        entries = list(destination.rglob("*"))
        symlinks = [str(path) for path in entries if path.is_symlink()]
        if symlinks:
            raise ValueError(f"map directory contains symlinks: {symlinks}")
        observed_files = {
            path.relative_to(destination).as_posix(): sha256(path)
            for path in entries
            if path.is_file()
        }
        if not observed_files == expected_files:
            raise ValueError(
                f"extracted map differs from lock: expected {expected_files}, "
                f"observed {observed_files}"
            )
        status = 0
        print(f"Extracted map files verified: {destination}")
        return 0
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        evidence = {
            "utc_time": datetime.now(timezone.utc).isoformat(),
            "host_architecture": platform.machine(),
            "repository_head": git_head(root),
            "execution_manifest_sha256": execution_manifest_sha256(bench),
            "lock_sha256": sha256(lock_path),
            "map_sha256": lock["map"]["sha256"],
            "image_id": None,
            "image_digest": lock["container"]["index_digest"],
            "extracted_sha256": observed_files,
            "map_files_verified": status == 0,
            "error": error,
            "command_exit_status": status,
        }
        evidence_path = bench / "evidence/map-runtime.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
