#!/usr/bin/env python3
"""Canonical identity for every local input that can affect the 009A execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


TOP_LEVEL_INPUTS = (
    "autoware-009a.repos",
    "compose.yaml",
    "cyclonedds.xml",
    "runtime-lock.yaml",
    "workspace/.gitkeep",
)


def execution_inputs(bench: Path) -> dict[str, str]:
    paths = [bench / relative for relative in TOP_LEVEL_INPUTS]
    paths.extend(
        path
        for root in (bench / "scripts", bench / "src")
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )
    result: dict[str, str] = {}
    for path in sorted(set(paths)):
        relative = path.relative_to(bench).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def execution_manifest_sha256(bench: Path) -> str:
    encoded = json.dumps(
        execution_inputs(bench), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
