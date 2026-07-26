#!/usr/bin/env python3
"""Verify locked extracted map files and write evidence only inside the 009C bench."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import tempfile

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
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def reject_symlink_components(path: Path) -> None:
    """Reject every existing symlink component, including the named path."""
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError(f"path contains symlink component: {current}")


def verify(cache: Path, bench: Path) -> tuple[Path, dict[str, str]]:
    lock_path = bench / "runtime-lock.yaml"
    if lock_path.is_symlink() or not lock_path.is_file():
        raise ValueError("runtime lock must be a regular non-symlink file")
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    destination = cache / lock["map"]["extracted_directory"]
    reject_symlink_components(destination)
    expected_files = lock["map"]["extracted_sha256"]
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError(f"missing extracted map directory: {destination}")
    entries = list(destination.rglob("*"))
    symlinks = [str(path) for path in entries if path.is_symlink()]
    if symlinks:
        raise ValueError(f"map directory contains symlinks: {symlinks}")
    special = [
        str(path) for path in entries
        if not (stat.S_ISREG(path.lstat().st_mode) or stat.S_ISDIR(path.lstat().st_mode))
    ]
    if special:
        raise ValueError(f"map directory contains nonregular paths: {special}")
    observed_files = {
        path.relative_to(destination).as_posix(): sha256(path)
        for path in entries
        if path.is_file()
    }
    if observed_files != expected_files:
        raise ValueError(
            f"extracted map differs from lock: expected {expected_files}, "
            f"observed {observed_files}"
        )
    return destination, observed_files


def atomic_evidence_write(path: Path, document: object, bench: Path) -> None:
    """Publish map evidence without following or replacing an unsafe destination."""
    unresolved_root = bench / "evidence" / "009c"
    reject_symlink_components(unresolved_root)
    if unresolved_root.is_symlink() or not unresolved_root.is_dir():
        raise ValueError("009C evidence root must be a real directory")
    evidence_root = unresolved_root.resolve(strict=True)
    if not evidence_root.is_relative_to(bench.resolve(strict=True)):
        raise ValueError("009C evidence root escapes resolved bench")
    reject_symlink_components(path.parent)
    parent = path.parent.resolve(strict=True)
    if not parent.is_relative_to(evidence_root):
        raise ValueError("map evidence output must remain inside resolved 009C evidence")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("map evidence destination must be a regular non-symlink file")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("map evidence destination became unsafe")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--bench", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    bench = args.bench.resolve() if args.bench else Path(__file__).resolve().parents[1]
    root = bench.parents[1]
    lock_path = bench / "runtime-lock.yaml"
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    observed_files: dict[str, str] = {}
    status = 1
    error: str | None = None
    try:
        destination, observed_files = verify(args.cache, bench)
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
        evidence_path = args.output if args.output else bench / "evidence/009c/map-runtime.json"
        if not evidence_path.is_absolute():
            evidence_path = bench / evidence_path
        atomic_evidence_write(evidence_path, evidence, bench)


if __name__ == "__main__":
    raise SystemExit(main())
