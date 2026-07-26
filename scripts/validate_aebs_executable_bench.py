#!/usr/bin/env python3
"""Deterministically validate the static INC-AEBS-009A scaffold (no ROS needed)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import hashlib
import json
import math
import re
import sys

import yaml

BENCH_REL = Path("implementation/aebs-autoware-executable-bench")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_INDEX = "sha256:03f6e177d507504a26710041674a1386b1a63fe964870cb5ff48b5e59c635c17"
EXPECTED_PLATFORM = "sha256:0bcf71e1c7b45da5787f10def7cfcb2e26d5a25906d2af538ae7db167766136f"
EXPECTED_MAP_URL = "https://autoware-files.s3.us-west-2.amazonaws.com/maps/demos/sample-map-planning.zip"
EXPECTED_MAP_SHA = "5536fce7bb8db7688fdf94ec004118b898637ad0d5b6175108b10989dd6e93b9"
EXPECTED_COMMITS = {
    "autoware_universe": "f603d8759c92fb2f423f1544844e13086d79ad09",
    "autoware_launch": "f05c4b1f83e0b0e4a01ade34d5199bd5571873f1",
    "autoware_simple_planning_simulator": "82d2c93a28a25f8802e8f5a21b4ec850beea9080",
}
EXPECTED_TREES = {
    "autoware_universe": "021a78ba31a6c2a43a7af06c4c201e0f50c2f48e",
    "autoware_launch": "1456364b31390921f8d2e6ac7f2878c902972ede",
    "autoware_simple_planning_simulator": "d0985e96562c71a38ca40697013e0922e42e5aa6",
}
REQUIRED = (
    "README.md",
    "increments.yaml",
    "runtime-lock.yaml",
    "autoware-009a.repos",
    "compose.yaml",
    "cyclonedds.xml",
    ".gitignore",
    "scripts/evidence_metadata.py",
    "scripts/execution_identity.py",
    "scripts/fetch_map.py",
    "scripts/verify_container.py",
    "scripts/verify_map.py",
    "scripts/prepare_workspace.sh",
    "scripts/build.sh",
    "scripts/launch.sh",
    "scripts/smoke.sh",
    "src/de4sdv_aebs_bench/package.xml",
    "src/de4sdv_aebs_bench/setup.py",
    "src/de4sdv_aebs_bench/config/aebs.param.yaml",
    "src/de4sdv_aebs_bench/config/diagnostic-graph.yaml",
    "src/de4sdv_aebs_bench/launch/aebs_bench.launch.py",
    "src/de4sdv_aebs_bench/de4sdv_aebs_bench/readiness_collector.py",
    "src/de4sdv_aebs_bench/de4sdv_aebs_bench/nominal_fixture.py",
    "evidence/container-identity.json",
    "evidence/map-acquisition.json",
    "evidence/map-runtime.json",
    "evidence/source-import.json",
    "evidence/build-status.json",
    "evidence/launch-status.json",
    "evidence/readiness.json",
)


def _load(path: Path, errors: list[str]) -> dict:
    try:
        value = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"cannot load {path.as_posix()}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"expected mapping in {path.as_posix()}")
        return {}
    return value


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _bounded_number(value: object, upper: object, *, allow_zero: bool) -> bool:
    if not _finite_number(value) or not _finite_number(upper):
        return False
    numeric = float(value)  # type: ignore[arg-type]
    ceiling = float(upper)  # type: ignore[arg-type]
    return (numeric >= 0 if allow_zero else numeric > 0) and numeric <= ceiling


def validate_runtime_lock(lock: dict) -> list[str]:
    errors: list[str] = []
    container = lock.get("container", {})
    if container.get("index_digest") != EXPECTED_INDEX or not DIGEST.fullmatch(
        str(container.get("index_digest", ""))
    ):
        errors.append("container index digest is not the required immutable sha256")
    if container.get("tag") != "universe-devel-humble-20260722":
        errors.append("container acquisition tag changed")
    if container.get("platform_digest") != EXPECTED_PLATFORM:
        errors.append("container ARM64 platform digest is not the acquired immutable sha256")

    sources = lock.get("sources", [])
    identities = [(item.get("repository"), item.get("commit")) for item in sources]
    for item in sources:
        if not SHA40.fullmatch(str(item.get("commit", ""))):
            errors.append(f"source {item.get('name')} commit must be a full 40-character SHA")
        expected = EXPECTED_COMMITS.get(item.get("name"))
        if expected is None or item.get("commit") != expected:
            errors.append(f"source {item.get('name')} is not at the selected exact commit")
        expected_tree = EXPECTED_TREES.get(item.get("name"))
        if expected_tree is None or item.get("tree") != expected_tree:
            errors.append(f"source {item.get('name')} is not at the selected exact tree")
    for identity, count in sorted(Counter(identities).items(), key=lambda pair: str(pair[0])):
        if count > 1:
            errors.append(f"duplicate source identity: {identity[0]}@{identity[1]}")
    if set(EXPECTED_COMMITS) != {item.get("name") for item in sources}:
        errors.append("source set does not exactly match the selected overlays")

    map_lock = lock.get("map", {})
    if map_lock.get("url") != EXPECTED_MAP_URL:
        errors.append("official map URL is missing or changed")
    if map_lock.get("sha256") != EXPECTED_MAP_SHA:
        errors.append("official map checksum is missing or changed")
    expected_files = {
        "lanelet2_map.osm", "map_config.yaml", "map_projector_info.yaml", "pointcloud_map.pcd"
    }
    if set(map_lock.get("extracted_files", [])) != expected_files:
        errors.append("map extracted file allowlist is incomplete or changed")

    readiness = lock.get("readiness", {})
    if readiness.get("collection_timeout_seconds") != 30:
        errors.append("readiness collection timeout must remain pinned at 30 seconds")
    if readiness.get("diagnostic_identity") != {
        "node": "autonomous_emergency_braking",
        "task": "aeb_emergency_stop",
        "joined_key": "autonomous_emergency_braking: aeb_emergency_stop",
    }:
        errors.append("AEB diagnostic identity differs from the INC-AEBS-008 contract")

    evidence = lock.get("evidence", {})
    if evidence.get("status_fields") != ["built", "launched", "ready", "scenario_executed"]:
        errors.append("evidence status fields must distinguish built/launched/ready/scenario_executed")
    if evidence.get("009a_required_values", {}).get("scenario_executed") is not False:
        errors.append("009A must require scenario_executed false")
    required_metadata = {
        "utc_time", "host_architecture", "repository_head", "execution_manifest_sha256",
        "lock_sha256", "map_sha256",
        "image_id", "image_digest", "command_exit_status",
    }
    if set(evidence.get("required_metadata", [])) != required_metadata:
        errors.append("evidence metadata contract is incomplete")
    blockers = {item.get("id"): item for item in lock.get("runtime_blockers", [])}
    for blocker_id in ("BLK-AEBS-009A-001", "BLK-AEBS-009A-002"):
        if blockers.get(blocker_id, {}).get("status") != "closed_runtime_verified":
            errors.append(f"{blocker_id} must record its runtime-verified closure")
    claims = " ".join(lock.get("claim_boundaries", [])).lower()
    for phrase in ("braking", "safety", "compliance", "production readiness"):
        if phrase not in claims:
            errors.append(f"claim boundary does not exclude {phrase}")
    return errors


def validate_increments(document: dict) -> list[str]:
    errors: list[str] = []
    items = document.get("increments", [])
    by_id = {item.get("id"): item for item in items if isinstance(item, dict)}
    if set(by_id) != {"INC-AEBS-009A", "INC-AEBS-009B", "INC-AEBS-009C"}:
        errors.append("increments must contain exactly 009A, 009B, and 009C")
    for future in ("INC-AEBS-009B", "INC-AEBS-009C"):
        if by_id.get(future, {}).get("status") != "planned":
            errors.append(f"{future} must remain planned")
    boundaries = [
        tuple(item.get("acceptance_boundary", []))
        for item in items
        if isinstance(item, dict)
    ]
    if len(boundaries) != len(set(boundaries)) or any(not boundary for boundary in boundaries):
        errors.append("increment acceptance boundaries must be non-empty and distinct")

    b_scope = " ".join(
        by_id.get("INC-AEBS-009B", {}).get("acceptance_boundary", [])
    ).lower()
    if not all(
        term in b_scope
        for term in ("stationary-target", "diagnostic-to-mrm-to-gate", "simulated deceleration")
    ):
        errors.append("009B stationary-target chain contract is incomplete")
    c_scope = " ".join(
        by_id.get("INC-AEBS-009C", {}).get("acceptance_boundary", [])
    ).lower()
    if not all(
        term in c_scope
        for term in ("non-collision and fault", "stale and missing", "emergency-state")
    ):
        errors.append("009C negative/fault matrix contract is incomplete")
    return errors


def execution_manifest_sha256(bench: Path) -> str:
    paths = [
        bench / relative
        for relative in (
            "autoware-009a.repos",
            "compose.yaml",
            "cyclonedds.xml",
            "runtime-lock.yaml",
            "workspace/.gitkeep",
        )
    ]
    paths.extend(
        path
        for root in (bench / "scripts", bench / "src")
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )
    inputs = {
        path.relative_to(bench).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(paths))
    }
    encoded = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_evidence(bench: Path, lock: dict) -> list[str]:
    errors: list[str] = []
    lock_sha256 = hashlib.sha256((bench / "runtime-lock.yaml").read_bytes()).hexdigest()
    execution_sha256 = execution_manifest_sha256(bench)
    documents = {}
    for name in (
        "container-identity.json",
        "map-acquisition.json",
        "map-runtime.json",
        "source-import.json",
        "build-status.json",
        "launch-status.json",
        "readiness.json",
    ):
        try:
            documents[name] = json.loads((bench / "evidence" / name).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load retained evidence {name}: {exc}")
            continue
        if documents[name].get("lock_sha256") != lock_sha256:
            errors.append(f"retained evidence {name} does not match the current lock")
        if documents[name].get("execution_manifest_sha256") != execution_sha256:
            errors.append(f"retained evidence {name} does not match current execution inputs")
        if documents[name].get("image_digest") != lock.get("container", {}).get("index_digest"):
            errors.append(f"retained evidence {name} has the wrong image digest")
        if documents[name].get("map_sha256") != lock.get("map", {}).get("sha256"):
            errors.append(f"retained evidence {name} has the wrong map archive digest")

    repository_heads = {document.get("repository_head") for document in documents.values()}
    if len(repository_heads) != 1 or not all(
        isinstance(head, str) and SHA40.fullmatch(head) for head in repository_heads
    ):
        errors.append("retained evidence repository identities are missing or inconsistent")
    host_architectures = {document.get("host_architecture") for document in documents.values()}
    if len(host_architectures) != 1 or not host_architectures <= {"aarch64", "arm64"}:
        errors.append("retained evidence host architectures are missing or inconsistent")

    container = documents.get("container-identity.json", {})
    image_id = container.get("image_id")
    locked_repo_digest = (
        f"{lock.get('container', {}).get('repository')}@"
        f"{lock.get('container', {}).get('index_digest')}"
    )
    repo_digests = container.get("repo_digests")
    if not (
        container.get("command_exit_status") == 0
        and container.get("image_digest") == lock.get("container", {}).get("index_digest")
        and container.get("platform_digest") == lock.get("container", {}).get("platform_digest")
        and isinstance(image_id, str)
        and DIGEST.fullmatch(image_id)
        and isinstance(repo_digests, list)
        and locked_repo_digest in repo_digests
        and container.get("image_architecture") == "arm64"
        and container.get("image_os") == "linux"
    ):
        errors.append("retained container evidence does not prove the locked ARM64 image")
    for name, document in documents.items():
        if document.get("image_id") is not None and document.get("image_id") != image_id:
            errors.append(f"retained evidence {name} has an inconsistent local image ID")

    expected_map = lock.get("map", {}).get("extracted_sha256")
    acquisition = documents.get("map-acquisition.json", {})
    runtime_map = documents.get("map-runtime.json", {})
    if not (
        acquisition.get("command_exit_status") == 0
        and acquisition.get("map_sha256") == lock.get("map", {}).get("sha256")
        and acquisition.get("extracted_sha256") == expected_map
        and runtime_map.get("command_exit_status") == 0
        and runtime_map.get("map_files_verified") is True
        and runtime_map.get("extracted_sha256") == expected_map
    ):
        errors.append("retained evidence does not prove the extracted runtime map files")

    manifest = _load(bench / "autoware-009a.repos", errors).get("repositories", {})
    expected_sources = {
        item.get("name"): {
            "url": item.get("repository"),
            "revision": item.get("commit"),
            "tree": item.get("tree"),
        }
        for item in lock.get("sources", [])
    }
    source = documents.get("source-import.json", {})
    source_items = source.get("repositories", [])
    keyed_sources = {
        item.get("name"): item for item in source_items if isinstance(item, dict)
    }
    if len(keyed_sources) != len(source_items) or set(keyed_sources) != set(expected_sources):
        errors.append("retained source evidence does not contain the exact locked source set")
    elif set(manifest) != set(expected_sources):
        errors.append("source import manifest does not contain the exact locked source set")
    else:
        for name, expected in expected_sources.items():
            item = keyed_sources[name]
            manifest_item = manifest.get(name, {})
            submodule_status = item.get("submodule_status", [])
            if not (
                item.get("url") == expected["url"] == manifest_item.get("url")
                and manifest_item.get("type") == "git"
                and item.get("expected_revision") == expected["revision"] == manifest_item.get("version")
                and item.get("actual_revision") == expected["revision"]
                and item.get("expected_tree") == expected["tree"] == EXPECTED_TREES.get(name)
                and item.get("actual_tree") == expected["tree"]
                and item.get("manifest_matches_lock") is True
                and item.get("matches") is True
                and item.get("worktree_clean") is True
                and item.get("worktree_status") == []
                and isinstance(submodule_status, list)
                and not any(str(line).startswith(("-", "+", "U")) for line in submodule_status)
            ):
                errors.append(f"retained source evidence is false or incomplete for {name}")
    if source.get("command_exit_status") != 0 or source.get("all_revisions_match") is not True:
        errors.append("retained source gate is not successful")

    build = documents.get("build-status.json", {})
    launch = documents.get("launch-status.json", {})
    readiness = documents.get("readiness.json", {})
    if build.get("command_exit_status") != 0 or build.get("built") is not True:
        errors.append("retained build evidence is not successful")
    if launch.get("command_exit_status") != 0 or launch.get("launched") is not True:
        errors.append("retained launch evidence is not successful")
    expected_endpoints = {
        endpoint.get("name"): endpoint.get("type")
        for endpoint in lock.get("readiness", {}).get("endpoints", [])
    }
    endpoint_items = readiness.get("endpoints", [])
    keyed_endpoints = {
        endpoint.get("name"): endpoint
        for endpoint in endpoint_items
        if isinstance(endpoint, dict)
    }
    endpoint_valid = (
        len(keyed_endpoints) == len(endpoint_items)
        and set(keyed_endpoints) == set(expected_endpoints)
    )
    collection_window = readiness.get("collection_window_seconds")
    configured_timeout = lock.get("readiness", {}).get("collection_timeout_seconds")
    timing_valid = _bounded_number(
        collection_window, configured_timeout, allow_zero=False
    )
    if endpoint_valid:
        for name, expected_type in expected_endpoints.items():
            endpoint = keyed_endpoints[name]
            message_age = endpoint.get("last_message_age_seconds")
            if not (
                endpoint.get("expected_type") == expected_type
                and endpoint.get("actual_types") == [expected_type]
                and endpoint.get("ready") is True
                and endpoint.get("message_received") is True
                and endpoint.get("received_after_start") is True
                and _bounded_number(message_age, collection_window, allow_zero=True)
            ):
                endpoint_valid = False
                break
    expected_identity = lock.get("readiness", {}).get("diagnostic_identity", {}).get("joined_key")
    diagnostic = readiness.get("diagnostic_identity", {})
    if not (
        readiness.get("command_exit_status") == 0
        and readiness.get("ready") is True
        and readiness.get("scenario_executed") is False
        and endpoint_valid
        and timing_valid
        and diagnostic.get("expected") == expected_identity
        and diagnostic.get("matched") is True
        and expected_identity in diagnostic.get("observed_names", [])
    ):
        errors.append("retained readiness evidence does not satisfy the exact 009A boundary")

    sequence = [
        "container-identity.json",
        "map-acquisition.json",
        "source-import.json",
        "build-status.json",
        "map-runtime.json",
        "launch-status.json",
        "readiness.json",
    ]
    try:
        times = [datetime.fromisoformat(documents[name]["utc_time"]) for name in sequence]
        if times != sorted(times):
            errors.append("retained evidence timestamps are not in execution order")
    except (KeyError, TypeError, ValueError):
        errors.append("retained evidence timestamps are missing or invalid")
    return errors


def validate_bench(root: Path) -> list[str]:
    bench = root / BENCH_REL
    errors = [f"missing required artifact: {rel}" for rel in REQUIRED if not (bench / rel).is_file()]
    if errors:
        return errors

    lock = _load(bench / "runtime-lock.yaml", errors)
    errors.extend(validate_runtime_lock(lock))
    errors.extend(validate_evidence(bench, lock))
    increments = _load(bench / "increments.yaml", errors)
    errors.extend(validate_increments(increments))

    repos = _load(bench / "autoware-009a.repos", errors).get("repositories", {})
    versions = [entry.get("version") for entry in repos.values()]
    if len(versions) != 3 or any(not SHA40.fullmatch(str(version)) for version in versions):
        errors.append("repos manifest must contain only three exact 40-character commits")
    if set(versions) != set(EXPECTED_COMMITS.values()):
        errors.append("repos manifest commits differ from the runtime lock")

    launch = (bench / "src/de4sdv_aebs_bench/launch/aebs_bench.launch.py").read_text()
    if 'package="autoware_autonomous_emergency_braking"' not in launch:
        errors.append("launch wrapper must directly instantiate the AEB package")
    if 'executable="autoware_autonomous_emergency_braking"' not in launch:
        errors.append("launch wrapper must select the pinned AEB executable")
    forbidden = "input" + "_odometry"
    if forbidden in launch:
        errors.append("launch wrapper contains the invalid undeclared odometry remap")
    if "autoware_simple_planning_simulator" not in launch or "map_path" not in launch:
        errors.append("launch wrapper must expose simulator and verified map composition inputs")

    setup = (bench / "src/de4sdv_aebs_bench/setup.py").read_text()
    for control in ("aebs.param.yaml", "diagnostic-graph.yaml"):
        if control not in setup:
            errors.append(f"package does not install authoritative {control}")
        packaged = bench / "src/de4sdv_aebs_bench/config" / control
        authoritative = (
            root
            / "methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment"
            / control
        )
        if packaged.read_bytes() != authoritative.read_bytes():
            errors.append(f"packaged runtime control differs from authoritative {control}")

    compose = (bench / "compose.yaml").read_text()
    if EXPECTED_INDEX not in compose or "network_mode: host" not in compose:
        errors.append("compose service must use host networking and pinned OCI index")
    return sorted(set(errors))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_bench(root)
    if errors:
        print("AEBS executable bench validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("AEBS executable bench structural validation passed; inspect evidence for runtime proof.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
