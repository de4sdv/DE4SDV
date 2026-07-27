#!/usr/bin/env python3
"""Fail-closed verification of the immutable 009A runtime inherited by 009C."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


EXPECTED_SCHEMA = "de4sdv.aebs-009c.runtime-lock.v1"
EXPECTED_INCREMENT = "INC-AEBS-009C"
EXPECTED_SCENARIO = "SCN-AEBS-009C-AEB-MRM-001"
EXPECTED_DISPOSITION = "runtime_verified_009a_readiness_only"
EXPECTED_STATUS = "retained_replay_validated_partial_native_intervention_to_mrm_gate_evidence"
EXPECTED_REPOSITORY_HISTORY = {
    "pull_request": 66,
    "retained_run_head": "a6234b572659ad052ecd647585552ded98bca569",
    "reviewed_head": "871ef95bbdf3b865d5761d692065674fc0b4e196",
    "delivery_commit": "81e043386251118b302bafbed91922f8fa821522",
}
INHERITED_TOP_LEVEL_INPUTS = (
    "autoware-009a.repos",
    "compose.yaml",
    "cyclonedds.xml",
    "runtime-lock.yaml",
    "workspace/.gitkeep",
)


class ClosedLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: ClosedLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


ClosedLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing YAML input: {path}")
    value = yaml.load(path.read_text(), Loader=ClosedLoader)
    if not isinstance(value, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inherited_execution_manifest_sha256(bench: Path) -> str:
    """Independently reproduce the maintained 009A execution identity algorithm."""
    paths: list[Path] = []
    for relative in INHERITED_TOP_LEVEL_INPUTS:
        path = bench / relative
        if not path.is_file():
            raise ValueError(f"missing inherited execution input: {path}")
        paths.append(path)
    for root in (bench / "scripts", bench / "src"):
        if not root.is_dir():
            raise ValueError(f"missing inherited execution input directory: {root}")
        paths.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        )
    inputs = {
        path.relative_to(bench).as_posix(): sha256(path)
        for path in sorted(set(paths))
    }
    encoded = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def git_value(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(
            f"cannot inspect inherited source {repository}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def verify_sources(inherited_bench: Path, sources: list[dict[str, Any]]) -> None:
    source_root = inherited_bench / "workspace/src"
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("source lock entry must be a mapping")
        name = source.get("name")
        if not isinstance(name, str):
            raise ValueError("source lock entry has no string name")
        repository = source_root / name
        if not repository.is_dir():
            raise ValueError(f"missing inherited source tree: {repository}")
        if git_value(repository, "status", "--porcelain"):
            raise ValueError(f"inherited source tree is mutated: {name}")
        if git_value(repository, "rev-parse", "HEAD") != source.get("commit"):
            raise ValueError(f"inherited source commit mismatch: {name}")
        if git_value(repository, "rev-parse", "HEAD^{tree}") != source.get("tree"):
            raise ValueError(f"inherited source tree mismatch: {name}")


def verify(bench: Path, inherited_bench: Path) -> None:
    lock_path = bench / "runtime-lock.yaml"
    inherited_lock_path = inherited_bench / "runtime-lock.yaml"
    lock = load_yaml(lock_path)
    inherited_lock = load_yaml(inherited_lock_path)

    expected_scalars = {
        "schema": EXPECTED_SCHEMA,
        "increment": EXPECTED_INCREMENT,
        "scenario_id": EXPECTED_SCENARIO,
        "status": EXPECTED_STATUS,
    }
    for key, expected in expected_scalars.items():
        if lock.get(key) != expected:
            raise ValueError(f"009C {key} mismatch: expected {expected!r}")
    if lock.get("repository_history") != EXPECTED_REPOSITORY_HISTORY:
        raise ValueError("009C reviewed squash-history relation mismatch")

    inheritance = lock.get("inherited_009a")
    if not isinstance(inheritance, dict):
        raise ValueError("missing inherited_009a lock mapping")
    expected_inherited_paths = {
        "execution_manifest_path": (
            "implementation/aebs-autoware-executable-bench/evidence/readiness.json"
        ),
        "runtime_lock_path": (
            "implementation/aebs-autoware-executable-bench/runtime-lock.yaml"
        ),
        "install_setup_path": (
            "implementation/aebs-autoware-executable-bench/workspace/install/setup.bash"
        ),
    }
    for key, expected in expected_inherited_paths.items():
        if inheritance.get(key) != expected:
            raise ValueError(f"inherited 009A {key} mismatch")
    observed_lock_hash = sha256(inherited_lock_path)
    if inheritance.get("runtime_lock_sha256") != observed_lock_hash:
        raise ValueError(
            "inherited 009A runtime lock hash mismatch: "
            f"pinned {inheritance.get('runtime_lock_sha256')}, observed {observed_lock_hash}"
        )
    observed_manifest_hash = inherited_execution_manifest_sha256(inherited_bench)
    if inheritance.get("execution_manifest_sha256") != observed_manifest_hash:
        raise ValueError(
            "inherited 009A execution manifest hash mismatch: "
            f"pinned {inheritance.get('execution_manifest_sha256')}, "
            f"observed {observed_manifest_hash}"
        )
    if inheritance.get("disposition") != EXPECTED_DISPOSITION:
        raise ValueError("inherited 009A disposition mismatch")

    reference = inherited_bench / "evidence/readiness.json"
    if not reference.is_file():
        raise ValueError(f"missing inherited execution manifest reference: {reference}")
    try:
        retained_manifest_hash = json.loads(reference.read_text()).get(
            "execution_manifest_sha256"
        )
    except (json.JSONDecodeError, AttributeError) as exc:
        raise ValueError(f"invalid inherited manifest reference: {reference}") from exc
    if retained_manifest_hash != observed_manifest_hash:
        raise ValueError("retained 009A manifest reference does not match current inputs")

    if lock.get("container") != inherited_lock.get("container"):
        raise ValueError("009C container pins differ from inherited 009A runtime lock")
    if lock.get("sources") != inherited_lock.get("sources"):
        raise ValueError("009C source pins differ from inherited 009A runtime lock")
    if lock.get("map") != inherited_lock.get("map"):
        raise ValueError("009C map pins differ from inherited 009A runtime lock")

    setup = inherited_bench / "workspace/install/setup.bash"
    if not setup.is_file():
        raise ValueError(f"missing inherited 009A install setup: {setup}")
    sources = lock.get("sources")
    if not isinstance(sources, list):
        raise ValueError("009C sources must be a list")
    verify_sources(inherited_bench, sources)

    if lock.get("selected_ros_packages") != ["de4sdv_aebs_009c_bench"]:
        raise ValueError("009C selected package set is not overlay-only")
    if lock.get("authoritative_scenario_config") != (
        "config/scenario-009c-aeb-mrm.yaml"
    ):
        raise ValueError("009C authoritative scenario config path mismatch")
    scenario = load_yaml(bench / "config/scenario-009c-aeb-mrm.yaml")
    if lock.get("timeouts") != scenario.get("timeouts"):
        raise ValueError("009C lock timeouts differ from authoritative scenario config")

    compose = load_yaml(bench / "compose.yaml")
    try:
        service = compose["services"]["bench"]
        container = lock["container"]
        expected_image = (
            f"{container['repository']}:{container['tag']}@{container['index_digest']}"
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("compose runtime shape is incomplete") from exc
    if service.get("image") != expected_image:
        raise ValueError("compose image differs from runtime lock")
    if service.get("platform") != container["platform"]:
        raise ValueError("compose platform differs from runtime lock")
    if service.get("privileged") is True:
        raise ValueError("privileged compose runtime is forbidden")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", type=Path)
    parser.add_argument("--inherited-bench", type=Path)
    args = parser.parse_args()
    bench = (args.bench or Path(__file__).resolve().parents[1]).resolve()
    inherited = (
        args.inherited_bench or bench.parent / "aebs-autoware-executable-bench"
    ).resolve()
    try:
        verify(bench, inherited)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"runtime inheritance verification failed: {exc}", file=sys.stderr)
        return 1
    print(
        "009C inherited 009A runtime inputs verified; retained evidence remains "
        "limited to the partial intervention-to-MRM/gate claim boundary."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
