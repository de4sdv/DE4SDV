#!/usr/bin/env python3
"""Independently schema-check and replay one 009B evidence document."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
from typing import Any, Mapping, Sequence

import jsonschema
import yaml

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from de4sdv_aebs_009b_bench.scenario_contract import load_scenario_config  # noqa: E402
from de4sdv_aebs_009b_bench.scenario_evaluator import evaluate_scenario  # noqa: E402
from evidence_document import (  # noqa: E402
    canonical_json_bytes,
    evaluation_to_json,
    load_strict_json,
    observation_from_json,
    sha256_file,
    validate_raw_semantics,
)
from execution_identity import execution_manifest_sha256  # noqa: E402

class ValidationError(ValueError):
    """A fail-closed evidence rejection with a user-facing reason."""


def _strict_json(path: Path) -> Any:
    def pairs(items: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValidationError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result
    def invalid(value: str) -> None:
        raise ValidationError(f"non-finite JSON number {value}")
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=pairs, parse_constant=invalid)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot parse evidence JSON: {error}") from error


def _finite_tree(value: object, location: str = "evidence") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError(f"{location} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _finite_tree(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _finite_tree(item, f"{location}[{index}]")


def _schema_validate(document: object, schema_path: Path) -> None:
    schema = _strict_json(schema_path)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path))
    except jsonschema.SchemaError as error:
        raise ValidationError(f"invalid evidence schema: {error.message}") from error
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "root"
        raise ValidationError(f"schema rejection at {location}: {error.message}")


def _regular_nonsymlink_under(root: Path, relative_text: str) -> Path:
    relative = PurePosixPath(relative_text)
    if relative.is_absolute() or not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise ValidationError(f"unsafe artifact path {relative_text!r}")
    candidate = root.joinpath(*relative.parts)
    current = root
    try:
        for part in relative.parts:
            current = current / part
            mode = os.lstat(current).st_mode
            if stat.S_ISLNK(mode):
                raise ValidationError(f"artifact path contains symlink: {relative_text}")
        if not stat.S_ISREG(os.lstat(candidate).st_mode):
            raise ValidationError(f"artifact is not a regular file: {relative_text}")
    except FileNotFoundError as error:
        raise ValidationError(f"artifact is missing: {relative_text}") from error
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValidationError(f"artifact escapes bench root: {relative_text}")
    return candidate


def _verify_artifacts(
    document: Mapping[str, Any], bench_root: Path
) -> dict[str, Path]:
    required = {
        "observer_raw",
        "observer_log",
        "launch_log",
        "run_metadata",
        "map_runtime",
    }
    if set(document["artifacts"]) != required:
        raise ValidationError("canonical artifacts do not match the closed run set")
    verified: dict[str, Path] = {}
    for name, record in document["artifacts"].items():
        candidate = _regular_nonsymlink_under(bench_root, record["path"])
        actual = sha256_file(candidate)
        if actual != record["sha256"]:
            raise ValidationError(f"artifact {name!r} SHA-256 mismatch")
        verified[name] = candidate
    return verified


def _verify_raw_contract(
    document: Mapping[str, Any], config: Any, artifacts: Mapping[str, Path]
) -> None:
    if "observer_raw" not in artifacts or "run_metadata" not in artifacts:
        raise ValidationError("observer_raw and run_metadata must be hash-bound artifacts")
    try:
        raw = load_strict_json(artifacts["observer_raw"])
        metadata = load_strict_json(artifacts["run_metadata"])
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(f"cannot parse hash-bound collector artifact: {error}") from error
    if not isinstance(raw, Mapping):
        raise ValidationError("hash-bound observer_raw is not an object")
    required_raw = {
        "collector_id", "monotonic_start_s", "monotonic_end_s", "clock_boundary",
        "observations", "evaluator_result", "activation", "errors", "terminal_reason",
        "command_exit", "limits",
    }
    if set(raw) != required_raw:
        raise ValidationError("hash-bound observer_raw has an open or incomplete contract")
    raw_collection = {
        key: raw[key]
        for key in (
            "collector_id", "monotonic_start_s", "monotonic_end_s",
            "clock_boundary", "observations",
        )
    }
    raw_contract = {
        key: raw[key]
        for key in ("activation", "limits", "terminal_reason", "errors", "command_exit")
    }
    if canonical_json_bytes(raw_collection) != canonical_json_bytes(document["collection"]):
        raise ValidationError("canonical collection differs from hash-bound observer_raw")
    if canonical_json_bytes(raw_contract) != canonical_json_bytes(document["collector_contract"]):
        raise ValidationError("canonical collector contract differs from observer_raw")
    if canonical_json_bytes(raw["evaluator_result"]) != canonical_json_bytes(document["evaluation"]):
        raise ValidationError("canonical evaluation differs from hash-bound observer_raw")
    try:
        validate_raw_semantics(raw, config, document["evaluation"])
    except (TypeError, ValueError, KeyError) as error:
        raise ValidationError(f"hash-bound observer contract rejected: {error}") from error
    if not isinstance(metadata, Mapping) or set(metadata) != {
        "observer_exit_code", "raw_output"
    }:
        raise ValidationError("run_metadata does not match the closed wrapper contract")
    if metadata["observer_exit_code"] != raw["command_exit"]:
        raise ValidationError("run_metadata exit differs from raw command_exit")
    if metadata["raw_output"] != document["artifacts"]["observer_raw"]["path"]:
        raise ValidationError("run_metadata raw path differs from hash-bound observer_raw")
    if document["provenance"]["command_exit_code"] != raw["command_exit"]:
        raise ValidationError("provenance exit differs from raw command_exit")


def _git_head(repository: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode != 0:
        raise ValidationError(f"cannot determine repository HEAD: {result.stderr.strip()}")
    return result.stdout.strip()


def _repository_commit_is_ancestor(
    repository: Path, ancestor: str, descendant: str
) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise ValidationError(
        f"cannot verify repository ancestry: {result.stderr.decode().strip()}"
    )


def _repository_root(bench_root: Path) -> Path:
    for candidate in (bench_root, *bench_root.parents):
        if (candidate / ".git").exists():
            return candidate
    raise ValidationError("bench root is not inside a Git repository")


def _load_lock(path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValidationError(f"cannot load runtime lock: {error}") from error
    if not isinstance(value, Mapping):
        raise ValidationError("runtime lock is not a mapping")
    return value


def _live_provenance_fields(bench_root: Path) -> dict[str, Any]:
    """Recompute identity fields; never derive a verdict from stored provenance."""
    import hashlib

    repository = _repository_root(bench_root)
    lock_path = bench_root / "runtime-lock.yaml"
    if lock_path.is_symlink() or not lock_path.is_file():
        raise ValidationError("live 009B runtime lock is missing or unsafe")
    lock = _load_lock(lock_path)
    try:
        inherited = lock["inherited_009a"]
        container = lock["container"]
        map_pin = lock["map"]
        inherited_bench = repository / "implementation/aebs-autoware-executable-bench"
        inherited_reference = repository / inherited["execution_manifest_path"]
        inherited_lock = repository / inherited["runtime_lock_path"]
        image_digest = container["index_digest"]
        map_digest = "sha256:" + map_pin["sha256"]
    except (KeyError, TypeError) as error:
        raise ValidationError(f"runtime lock lacks required provenance pin: {error}") from error
    for label, path in (("inherited manifest reference", inherited_reference), ("inherited lock", inherited_lock)):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(repository.resolve()):
            raise ValidationError(f"{label} path is missing or unsafe")
    inherited_inputs = [
        inherited_bench / relative for relative in (
            "autoware-009a.repos", "compose.yaml", "cyclonedds.xml",
            "runtime-lock.yaml", "workspace/.gitkeep",
        )
    ]
    for recursive in (inherited_bench / "scripts", inherited_bench / "src"):
        inherited_inputs.extend(
            path for path in recursive.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    for path in inherited_inputs:
        if not path.is_file():
            raise ValidationError(f"inherited execution input is missing: {path}")
    inherited_map = {
        path.relative_to(inherited_bench).as_posix(): sha256_file(path)
        for path in sorted(set(inherited_inputs))
    }
    inherited_manifest_sha = hashlib.sha256(
        json.dumps(inherited_map, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    inherited_lock_sha = sha256_file(inherited_lock)
    if inherited_manifest_sha != inherited.get("execution_manifest_sha256"):
        raise ValidationError("inherited 009A execution manifest differs from 009B lock pin")
    if inherited_lock_sha != inherited.get("runtime_lock_sha256"):
        raise ValidationError("inherited 009A runtime lock differs from 009B lock pin")
    return {
        "host_arch": platform.machine(),
        "repository_head": _git_head(repository),
        "execution_manifest_sha256": execution_manifest_sha256(bench_root),
        "runtime_lock_sha256": sha256_file(lock_path),
        "inherited_009a": {
            "execution_manifest_sha256": inherited_manifest_sha,
            "runtime_lock_sha256": inherited_lock_sha,
        },
        "image_digest": image_digest,
        "map_digest": map_digest,
    }


def _verify_provenance(
    stored: Mapping[str, Any], bench_root: Path, expected: Mapping[str, Any] | None
) -> None:
    if expected is not None:
        if canonical_json_bytes(stored) != canonical_json_bytes(expected):
            raise ValidationError("provenance differs from expected fixture/live identity")
        return
    live = _live_provenance_fields(bench_root)
    repository = _repository_root(bench_root)
    live_head = live.pop("repository_head")
    stored_head = stored.get("repository_head")
    if not isinstance(stored_head, str) or not _repository_commit_is_ancestor(
        repository, stored_head, live_head
    ):
        raise ValidationError(
            "recorded run repository head is not an ancestor of live HEAD"
        )
    for key, value in live.items():
        if stored.get(key) != value:
            raise ValidationError(f"provenance mismatch for {key}")
    if stored["command_exit_code"] != 0:
        raise ValidationError("observer command did not exit successfully")


def validate_evidence(
    evidence_path: str | Path,
    *,
    bench_root: str | Path = BENCH_ROOT,
    scenario_config: str | Path | None = None,
    schema_path: str | Path | None = None,
    expected_provenance: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Validate structure, raw ordering, evaluator replay, artifacts, and identity."""
    evidence = Path(evidence_path)
    root = Path(bench_root).resolve()
    config_path = Path(scenario_config) if scenario_config else root / "config" / "scenario-009b-stationary-target.yaml"
    schema = Path(schema_path) if schema_path else BENCH_ROOT / "schemas" / "scenario-evidence.schema.json"
    document = _strict_json(evidence)
    if not isinstance(document, Mapping):
        raise ValidationError("evidence root must be an object")
    _finite_tree(document)
    _schema_validate(document, schema)
    config = load_scenario_config(config_path)
    if document["scenario_id"] != config.scenario_id:
        raise ValidationError("scenario ID does not match authoritative config")
    collection = document["collection"]
    start = collection["monotonic_start_s"]
    end = collection["monotonic_end_s"]
    if end < start:
        raise ValidationError("collection monotonic interval is reversed")
    observations = []
    previous = start
    for index, raw in enumerate(collection["observations"]):
        try:
            item = observation_from_json(raw)
        except (TypeError, ValueError) as error:
            raise ValidationError(f"observation {index} cannot be reconstructed: {error}") from error
        receipt = item.receipt_monotonic_s
        if receipt < start or receipt > end:
            raise ValidationError(f"observation {index} receipt is outside collection interval")
        if receipt < previous:
            raise ValidationError(f"observation {index} is not in collector receipt order")
        previous = receipt
        observations.append(item)
    replayed = evaluation_to_json(evaluate_scenario(config, observations))
    if canonical_json_bytes(replayed) != canonical_json_bytes(document["evaluation"]):
        raise ValidationError("stored evaluation differs from independent evaluator replay")
    artifacts = _verify_artifacts(document, root)
    _verify_raw_contract(document, config, artifacts)
    _verify_provenance(document["provenance"], root, expected_provenance)
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--schema", type=Path)
    arguments = parser.parse_args(argv)
    try:
        validate_evidence(
            arguments.evidence, bench_root=arguments.bench_root,
            scenario_config=arguments.config, schema_path=arguments.schema,
        )
    except (ValidationError, TypeError, ValueError) as error:
        print(f"009B evidence rejected: {error}", file=sys.stderr)
        return 1
    print(f"009B evidence validated by schema and evaluator replay: {arguments.evidence}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
