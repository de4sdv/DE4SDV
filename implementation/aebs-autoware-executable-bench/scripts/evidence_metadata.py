#!/usr/bin/env python3
"""Write a common runtime-gate evidence envelope."""

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


def optional(command: list[str], cwd: Path | None = None) -> str | None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--status", required=True, type=int)
    parser.add_argument("--built", choices=("true", "false", "null"), default="null")
    parser.add_argument("--launched", choices=("true", "false", "null"), default="null")
    parser.add_argument("--ready", choices=("true", "false", "null"), default="null")
    parser.add_argument("--details", type=Path)
    args = parser.parse_args()
    bench = Path(__file__).resolve().parents[1]
    root = bench.parents[1]
    lock_path = bench / "runtime-lock.yaml"
    lock = yaml.safe_load(lock_path.read_text())
    reference = f"{lock['container']['repository']}:{lock['container']['tag']}@{lock['container']['index_digest']}"
    image_id = optional(["docker", "image", "inspect", reference, "--format", "{{.Id}}"])
    convert = {"true": True, "false": False, "null": None}
    document = {
        "utc_time": datetime.now(timezone.utc).isoformat(),
        "host_architecture": platform.machine(),
        "repository_head": optional(["git", "rev-parse", "HEAD"], root),
        "execution_manifest_sha256": execution_manifest_sha256(bench),
        "lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "map_sha256": lock["map"]["sha256"],
        "image_id": image_id,
        "image_digest": lock["container"]["index_digest"],
        "command_exit_status": args.status,
        "built": convert[args.built],
        "launched": convert[args.launched],
        "ready": convert[args.ready],
        "scenario_executed": False,
    }
    runtime_map_path = bench / "evidence/map-runtime.json"
    if runtime_map_path.is_file():
        runtime_map = json.loads(runtime_map_path.read_text())
        if runtime_map.get("lock_sha256") == document["lock_sha256"]:
            document["map_files_verified"] = runtime_map.get("map_files_verified")
            document["extracted_sha256"] = runtime_map.get("extracted_sha256")
    if args.details is not None:
        if args.details.is_file():
            details = json.loads(args.details.read_text())
            document["endpoints"] = details.get("endpoints")
            document["diagnostic_identity"] = details.get("diagnostic_identity")
            document["collection_window_seconds"] = details.get(
                "collection_window_seconds"
            )
        else:
            document["endpoint_evidence_error"] = (
                f"missing details file: {args.details}"
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
