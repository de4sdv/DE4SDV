#!/usr/bin/env python3
"""Independently schema-check and replay one 009C evidence document."""
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
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009c_bench"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from de4sdv_aebs_009c_bench.scenario_contract import load_scenario_config  # noqa: E402
from de4sdv_aebs_009c_bench.scenario_evaluator import evaluate_scenario  # noqa: E402
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
    physical_files: dict[tuple[int, int], str] = {}
    for name, record in document["artifacts"].items():
        candidate = _regular_nonsymlink_under(bench_root, record["path"])
        file_stat = candidate.stat()
        physical_identity = (file_stat.st_dev, file_stat.st_ino)
        if physical_identity in physical_files:
            other = physical_files[physical_identity]
            raise ValidationError(
                f"artifact roles {other!r} and {name!r} must resolve to distinct files"
            )
        physical_files[physical_identity] = name
        actual = sha256_file(candidate)
        if actual != record["sha256"]:
            raise ValidationError(f"artifact {name!r} SHA-256 mismatch")
        verified[name] = candidate
    return verified


def _verify_map_runtime(
    document: Mapping[str, Any], artifacts: Mapping[str, Path], bench_root: Path
) -> None:
    try:
        runtime = load_strict_json(artifacts["map_runtime"])
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(f"cannot parse hash-bound map runtime: {error}") from error
    required = {
        "command_exit_status", "error", "execution_manifest_sha256",
        "extracted_sha256", "host_architecture", "image_digest", "image_id",
        "lock_sha256", "map_files_verified", "map_sha256",
        "repository_head", "utc_time",
    }
    if not isinstance(runtime, Mapping) or set(runtime) != required:
        raise ValidationError("map-runtime does not match the closed runtime contract")
    provenance = document["provenance"]
    expected = {
        "command_exit_status": 0,
        "error": None,
        "execution_manifest_sha256": provenance["execution_manifest_sha256"],
        "host_architecture": provenance["host_arch"],
        "image_digest": provenance["image_digest"],
        "lock_sha256": provenance["runtime_lock_sha256"],
        "map_sha256": provenance["map_digest"].removeprefix("sha256:"),
        "repository_head": provenance["repository_head"],
        "map_files_verified": True,
    }
    for key, value in expected.items():
        if runtime[key] != value:
            raise ValidationError(f"map-runtime mismatch for {key}")
    extracted = runtime["extracted_sha256"]
    required_maps = {
        "lanelet2_map.osm", "map_config.yaml",
        "map_projector_info.yaml", "pointcloud_map.pcd",
    }
    if not isinstance(extracted, Mapping) or set(extracted) != required_maps:
        raise ValidationError("map-runtime extracted map set is incomplete or open")
    if any(
        not isinstance(digest, str) or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        for digest in extracted.values()
    ):
        raise ValidationError("map-runtime extracted map digest is not lowercase SHA-256")
    try:
        lock = _load_lock(bench_root / "runtime-lock.yaml")
        locked_extracted = lock["map"]["extracted_sha256"]
    except (KeyError, TypeError) as error:
        raise ValidationError(
            f"cannot read extracted-map identities from runtime lock: {error}"
        ) from error
    if not isinstance(locked_extracted, Mapping) or dict(extracted) != dict(locked_extracted):
        raise ValidationError("map-runtime extracted map digests do not match runtime lock")


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


def _git_revision(repository: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", revision], cwd=repository, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode != 0:
        raise ValidationError(f"cannot resolve repository revision {revision!r}")
    return result.stdout.strip()


def _repository_head_is_accepted(
    repository: Path,
    stored_head: str,
    live_head: str,
    history: Mapping[str, Any],
) -> bool:
    """Accept ancestry or one exact, tree-preserving reviewed squash relation."""
    try:
        if _repository_commit_is_ancestor(repository, stored_head, live_head):
            return True
    except ValidationError:
        return False
    required = {
        "pull_request", "retained_run_head", "reviewed_head", "delivery_commit"
    }
    if set(history) != required:
        return False
    pull_request = history.get("pull_request")
    revisions = [
        history.get("retained_run_head"), history.get("reviewed_head"),
        history.get("delivery_commit"),
    ]
    if (
        type(pull_request) is not int or pull_request <= 0
        or any(
            not isinstance(revision, str) or len(revision) != 40
            or any(character not in "0123456789abcdef" for character in revision)
            for revision in revisions
        )
        or stored_head != history["retained_run_head"]
    ):
        return False
    try:
        if not _repository_commit_is_ancestor(
            repository, history["retained_run_head"], history["reviewed_head"]
        ):
            return False
        reviewed_tree = _git_revision(repository, history["reviewed_head"] + "^{tree}")
        delivery_tree = _git_revision(repository, history["delivery_commit"] + "^{tree}")
        if reviewed_tree != delivery_tree:
            return False
        if not _repository_commit_is_ancestor(
            repository, history["delivery_commit"], live_head
        ):
            return False
        subject = subprocess.run(
            ["git", "show", "-s", "--format=%s", history["delivery_commit"]],
            cwd=repository, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        return subject.returncode == 0 and subject.stdout.strip().endswith(
            f"(#{pull_request})"
        )
    except ValidationError:
        return False


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
        raise ValidationError("live 009C runtime lock is missing or unsafe")
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
        raise ValidationError("inherited 009A execution manifest differs from 009C lock pin")
    if inherited_lock_sha != inherited.get("runtime_lock_sha256"):
        raise ValidationError("inherited 009A runtime lock differs from 009C lock pin")
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
    lock = _load_lock(bench_root / "runtime-lock.yaml")
    history = lock.get("repository_history")
    if (
        not isinstance(stored_head, str)
        or not isinstance(history, Mapping)
        or not _repository_head_is_accepted(repository, stored_head, live_head, history)
    ):
        raise ValidationError(
            "recorded run repository head is neither an ancestor nor the exact reviewed squash relation"
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
    config_path = Path(scenario_config) if scenario_config else root / "config" / "scenario-009c-aeb-mrm.yaml"
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
    _verify_map_runtime(document, artifacts, root)
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
        print(f"009C evidence rejected: {error}", file=sys.stderr)
        return 1
    print(f"009C evidence validated by schema and evaluator replay: {arguments.evidence}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
