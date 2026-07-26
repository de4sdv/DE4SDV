#!/usr/bin/env python3
"""Verify the locked OCI index and record the pulled platform image identity."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import platform
import re
import subprocess

import yaml

from execution_identity import execution_manifest_sha256

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    bench = Path(__file__).resolve().parents[1]
    root = bench.parents[1]
    lock_path = bench / "runtime-lock.yaml"
    lock = yaml.safe_load(lock_path.read_text())
    image = lock["container"]
    reference = f"{image['repository']}:{image['tag']}@{image['index_digest']}"
    status = 1
    image_id = None
    platform_digest = None
    image_architecture = None
    image_os = None
    repo_digests = []
    try:
        raw = run(["docker", "buildx", "imagetools", "inspect", "--raw", reference])
        if raw.returncode != 0:
            raise RuntimeError(raw.stderr.strip())
        index = json.loads(raw.stdout)
        wanted_arch = image["platform"].split("/", 1)[1]
        matches = [
            item for item in index.get("manifests", [])
            if item.get("platform", {}).get("os") == "linux"
            and item.get("platform", {}).get("architecture") == wanted_arch
        ]
        if len(matches) != 1:
            raise RuntimeError(f"expected one linux/{wanted_arch} manifest, got {len(matches)}")
        platform_digest = matches[0]["digest"]
        if platform_digest != image["platform_digest"]:
            raise RuntimeError(
                f"platform digest mismatch: expected {image['platform_digest']}, "
                f"observed {platform_digest}"
            )
        pulled = run(["docker", "pull", "--platform", image["platform"], reference])
        if pulled.returncode != 0:
            raise RuntimeError(pulled.stderr.strip())
        inspected = run(["docker", "image", "inspect", reference, "--format", "{{json .}}"])
        if inspected.returncode != 0:
            raise RuntimeError(inspected.stderr.strip())
        inspected_image = json.loads(inspected.stdout)
        image_id = inspected_image["Id"]
        repo_digests = inspected_image.get("RepoDigests") or []
        image_architecture = inspected_image["Architecture"]
        image_os = inspected_image["Os"]
        locked_repo_digest = f"{image['repository']}@{image['index_digest']}"
        if DIGEST.fullmatch(str(image_id)) is None:
            raise RuntimeError(f"invalid local image ID: {image_id}")
        if locked_repo_digest not in repo_digests:
            raise RuntimeError(
                f"pulled image lacks locked RepoDigest {locked_repo_digest}: {repo_digests}"
            )
        if image_architecture != wanted_arch or image_os != "linux":
            raise RuntimeError(
                f"pulled image platform mismatch: expected linux/{wanted_arch}, "
                f"observed {image_os}/{image_architecture}"
            )
        status = 0
        print(f"OCI identity verified: index={image['index_digest']} platform={platform_digest}")
        return 0
    finally:
        head = run(["git", "rev-parse", "HEAD"])
        evidence = {
            "utc_time": datetime.now(timezone.utc).isoformat(),
            "host_architecture": platform.machine(),
            "repository_head": head.stdout.strip() if head.returncode == 0 else None,
            "execution_manifest_sha256": execution_manifest_sha256(bench),
            "lock_sha256": digest(lock_path),
            "map_sha256": lock["map"]["sha256"],
            "image_id": image_id,
            "image_digest": image["index_digest"],
            "platform_digest": platform_digest,
            "image_architecture": image_architecture,
            "image_os": image_os,
            "repo_digests": repo_digests,
            "command_exit_status": status,
        }
        path = bench / "evidence/container-identity.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
