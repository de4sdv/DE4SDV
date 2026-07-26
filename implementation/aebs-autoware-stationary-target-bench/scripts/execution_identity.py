#!/usr/bin/env python3
"""Canonical identity for every local input that can affect a 009B execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


INHERITED_009A_MANIFEST_SHA256 = (
    "a06657a0a98eea21862ce94bf79a5b49509b1d7f0f7581af6cd3bee9bdcb2e8a"
)
VIRTUAL_INHERITED_INPUT = "@inherited-009a-execution-manifest"
TOP_LEVEL_INPUTS = (
    "runtime-lock.yaml",
    "compose.yaml",
    "cyclonedds.xml",
    "config/scenario-009b-stationary-target.yaml",
    "workspace/.gitkeep",
)
REQUIRED_RECURSIVE_INPUT_ROOTS = ("scripts", "src")
OPTIONAL_RECURSIVE_INPUT_ROOTS = ("schemas",)
IGNORED_INPUT_NAMES = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".hypothesis",
        ".tox",
        ".coverage",
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_authoritative_file(path: Path) -> bool:
    return (
        path.is_file()
        and not any(part in IGNORED_INPUT_NAMES for part in path.parts)
        and path.suffix != ".pyc"
    )


def execution_inputs(bench: Path) -> dict[str, str]:
    """Return path-to-digest inputs, rejecting any missing authoritative input."""
    bench = bench.resolve()
    paths: list[Path] = []
    for relative in TOP_LEVEL_INPUTS:
        path = bench / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing execution input: {relative}")
        paths.append(path)

    for relative in REQUIRED_RECURSIVE_INPUT_ROOTS:
        root = bench / relative
        if not root.is_dir():
            raise FileNotFoundError(
                f"missing execution input directory: {relative}"
            )
        paths.extend(
            path
            for path in root.rglob("*")
            if _is_authoritative_file(path)
        )

    for relative in OPTIONAL_RECURSIVE_INPUT_ROOTS:
        root = bench / relative
        if not root.exists():
            continue
        if not root.is_dir():
            raise FileNotFoundError(f"execution input root is not a directory: {relative}")
        paths.extend(
            path
            for path in root.rglob("*")
            if _is_authoritative_file(path)
        )

    result = {
        path.relative_to(bench).as_posix(): _sha256(path)
        for path in sorted(set(paths))
    }
    result[VIRTUAL_INHERITED_INPUT] = INHERITED_009A_MANIFEST_SHA256
    return result


def execution_manifest_sha256(bench: Path) -> str:
    encoded = json.dumps(
        execution_inputs(bench), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
