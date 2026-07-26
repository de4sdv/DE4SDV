#!/usr/bin/env python3
"""Fetch the locked map, verify SHA-256, and safely extract its allowlist."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import urllib.request
import zipfile

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


def download(url: str, archive: Path) -> None:
    temporary = archive.with_suffix(archive.suffix + ".part")
    temporary.unlink(missing_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            output.write(block)
    temporary.replace(archive)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    bench = Path(__file__).resolve().parents[1]
    root = bench.parents[1]
    lock_path = bench / "runtime-lock.yaml"
    lock = yaml.safe_load(lock_path.read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    archive = args.cache / "sample-map-planning.zip"
    status = 1
    observed = None
    extracted_sha256: dict[str, str] = {}
    try:
        if not archive.exists():
            download(lock["map"]["url"], archive)
        observed = sha256(archive)
        if observed != lock["map"]["sha256"]:
            archive.unlink()
            download(lock["map"]["url"], archive)
            observed = sha256(archive)
        if observed != lock["map"]["sha256"]:
            raise ValueError(f"map checksum mismatch after redownload: {observed}")

        destination = args.cache / lock["map"]["extracted_directory"]
        allowed = {f"{destination.name}/{name}" for name in lock["map"]["extracted_files"]}
        with zipfile.ZipFile(archive) as bundle:
            members = [item for item in bundle.infolist() if not item.is_dir()]
            names = {PurePosixPath(item.filename).as_posix() for item in members}
            if names != allowed:
                raise ValueError(f"archive members differ from allowlist: {sorted(names)}")
            for item in members:
                path = PurePosixPath(item.filename)
                mode = item.external_attr >> 16 & 0o170000
                if path.is_absolute() or ".." in path.parts or mode == 0o120000:
                    raise ValueError(f"unsafe archive member: {item.filename}")
                target = args.cache.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(item) as source, target.open("wb") as output:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(block)

        extracted_sha256 = {
            name: sha256(destination / name) for name in lock["map"]["extracted_files"]
        }
        if extracted_sha256 != lock["map"]["extracted_sha256"]:
            raise ValueError("extracted map file checksums differ from the lock")
        status = 0
        print(f"Map verified and extracted: {destination}")
        return 0
    finally:
        evidence = {
            "utc_time": datetime.now(timezone.utc).isoformat(),
            "host_architecture": platform.machine(),
            "repository_head": git_head(root),
            "execution_manifest_sha256": execution_manifest_sha256(bench),
            "lock_sha256": sha256(lock_path),
            "map_sha256": observed,
            "extracted_sha256": extracted_sha256,
            "image_id": None,
            "image_digest": lock["container"]["index_digest"],
            "command_exit_status": status,
        }
        evidence_path = bench / "evidence/map-acquisition.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
