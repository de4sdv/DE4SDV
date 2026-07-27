#!/usr/bin/env python3
"""Canonical identity for every local input that can affect a 009B execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

INHERITED_009A_MANIFEST_SHA256 = (
    "a06657a0a98eea21862ce94bf79a5b49509b1d7f0f7581af6cd3bee9bdcb2e8a"
)
VIRTUAL_INHERITED_INPUT = "@inherited-009a-execution-manifest"
TOP_LEVEL_INPUTS = (
    "runtime-lock.yaml",
    "compose.yaml",
    "cyclonedds.xml",
    "config/scenario-009b-moving-vehicle-target.yaml",
    "config/scenario-009d-conscious-override-matrix.yaml",
    "config/scenario-009d-moving-vehicle-target.yaml",
    "config/aebs-009b.param.yaml",
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
            raise FileNotFoundError(f"missing execution input directory: {relative}")
        paths.extend(path for path in root.rglob("*") if _is_authoritative_file(path))

    for relative in OPTIONAL_RECURSIVE_INPUT_ROOTS:
        root = bench / relative
        if not root.exists():
            continue
        if not root.is_dir():
            raise FileNotFoundError(
                f"execution input root is not a directory: {relative}"
            )
        paths.extend(path for path in root.rglob("*") if _is_authoritative_file(path))

    result = {
        path.relative_to(bench).as_posix(): _sha256(path) for path in sorted(set(paths))
    }
    result[VIRTUAL_INHERITED_INPUT] = INHERITED_009A_MANIFEST_SHA256
    return result


def execution_manifest_sha256(bench: Path) -> str:
    encoded = json.dumps(
        execution_inputs(bench), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def override_execution_manifest_sha256(bench: Path, profile: str) -> str:
    """Bind the selected closed 009D profile in addition to file inputs."""
    allowed = {
        "fresh_false_control",
        "fresh_true_conscious_override",
        "stale",
        "missing",
        "malformed",
        "future_stamped",
    }
    if profile not in allowed:
        raise ValueError("profile is not one of the six closed 009D profiles")
    inputs = execution_inputs(bench)
    inputs["@009d-override-profile"] = profile
    encoded = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def execution_inputs_at_revision(bench: Path, revision: str) -> dict[str, str]:
    """Reconstruct execution inputs from one exact repository tree."""

    bench = bench.resolve()
    repository = Path(
        subprocess.run(
            ["git", "-C", str(bench), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    bench_relative = bench.relative_to(repository)
    completed = subprocess.run(
        [
            "git", "-C", str(repository), "ls-tree", "-r", "--name-only",
            revision, "--", str(bench_relative),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = {Path(line) for line in completed.stdout.splitlines() if line}
    selected: set[Path] = set()
    for relative in TOP_LEVEL_INPUTS:
        path = bench_relative / relative
        if path not in tracked:
            raise FileNotFoundError(f"missing execution input at {revision}: {relative}")
        selected.add(path)
    roots = REQUIRED_RECURSIVE_INPUT_ROOTS + OPTIONAL_RECURSIVE_INPUT_ROOTS
    for path in tracked:
        try:
            relative = path.relative_to(bench_relative)
        except ValueError:
            continue
        if (
            relative.parts
            and relative.parts[0] in roots
            and not any(part in IGNORED_INPUT_NAMES for part in relative.parts)
            and relative.suffix != ".pyc"
        ):
            selected.add(path)
    result: dict[str, str] = {}
    for path in sorted(selected):
        blob = subprocess.run(
            ["git", "-C", str(repository), "show", f"{revision}:{path.as_posix()}"],
            check=True,
            capture_output=True,
        ).stdout
        result[path.relative_to(bench_relative).as_posix()] = hashlib.sha256(blob).hexdigest()
    result[VIRTUAL_INHERITED_INPUT] = INHERITED_009A_MANIFEST_SHA256
    return result


def execution_manifest_sha256_at_revision(bench: Path, revision: str) -> str:
    encoded = json.dumps(
        execution_inputs_at_revision(bench, revision),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def override_execution_manifest_sha256_at_revision(
    bench: Path, profile: str, revision: str
) -> str:
    inputs = execution_inputs_at_revision(bench, revision)
    inputs["@009d-override-profile"] = profile
    encoded = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
