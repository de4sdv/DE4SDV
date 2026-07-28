#!/usr/bin/env python3
"""Shared evidence validator parameterized by a contract definition.

This module replaces the per-increment validators (validate_override_evidence,
validate_non_activation_evidence, validate_degraded_input_evidence,
validate_crossing_target_evidence) with a single :func:`validate_evidence`
function driven by the same contract dict used by the builder.

The validator independently replays the builder from the hash-bound raw artifact
and rejects any document whose canonical JSON differs from the replay.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from evidence_document import (
    canonical_json_bytes,
    load_strict_json,
    sha256_file,
)
from evidence_pipeline import build_evidence, load_contract, resolve_profile


class ValidationError(ValueError):
    """A fail-closed evidence rejection with a user-facing reason."""


def _ensure_import_paths(bench_root: str | Path) -> None:
    """Add the bench ``src`` package and ``scripts`` to ``sys.path``."""
    root = Path(bench_root).resolve()
    package = root / "src" / "de4sdv_aebs_009b_bench"
    scripts = root / "scripts"
    for path in (package, scripts):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _import_function(module_name: str, function_name: str):
    module = importlib.import_module(module_name)
    return getattr(module, function_name)


def _verify_artifact_paths(
    document: Mapping[str, Any],
    artifact_prefix: str,
    increment_id: str,
) -> None:
    """Check artifact paths are distinct, profile-specific, and in one run bundle."""
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValidationError(f"{increment_id} artifacts must be an object")
    paths = [
        record.get("path")
        for record in artifacts.values()
        if isinstance(record, Mapping)
    ]
    if len(paths) != len(artifacts) or len(set(paths)) != len(paths):
        raise ValidationError(
            f"{increment_id} artifact roles require distinct paths"
        )
    prefix = f"{artifact_prefix}/runs/"
    if any(not isinstance(path, str) or not path.startswith(prefix) for path in paths):
        raise ValidationError(
            f"{increment_id} artifact path is not profile-specific"
        )
    run_parents = {str(Path(path).parent) for path in paths}
    if len(run_parents) != 1:
        raise ValidationError(
            f"{increment_id} artifacts must belong to one isolated run bundle"
        )


def _live_provenance_fields(bench_root: Path) -> dict[str, Any]:
    """Recompute live provenance fields using the shared helper."""
    from validate_scenario_evidence import _live_provenance_fields as _impl

    return _impl(bench_root)


def _repository_root(bench_root: Path) -> Path:
    from validate_scenario_evidence import _repository_root as _impl

    return _impl(bench_root)


def _repository_commit_is_ancestor(
    repository: Path, ancestor: str, descendant: str
) -> bool:
    from validate_scenario_evidence import (
        _repository_commit_is_ancestor as _impl,
    )

    return _impl(repository, ancestor, descendant)


def _verify_artifacts(document: Mapping[str, Any], bench_root: Path) -> dict[str, Path]:
    from validate_scenario_evidence import _verify_artifacts as _impl

    return _impl(document, bench_root)


def _verify_map_runtime(
    document: Mapping[str, Any], artifacts: Mapping[str, Path], bench_root: Path
) -> None:
    from validate_scenario_evidence import _verify_map_runtime as _impl

    _impl(document, artifacts, bench_root)


def _campaign_execution_head(
    evidence_path: Path,
    document: Mapping[str, Any],
    root: Path,
    contract: Mapping[str, Any],
    profile_value: str,
    *,
    candidate: bool,
) -> str:
    """Resolve the execution head from a campaign manifest (or live HEAD)."""
    increment_id = contract["increment_id"]
    evidence_dir = contract["evidence_dir"]
    campaign_schema = contract["campaign_manifest_schema"]
    manifest_member_key = contract.get(
        "campaign_manifest_member_key", "profiles"
    )  # "profiles" or "scenario"
    profile_key_field = contract.get("profile_key_field", "profile")
    if candidate:
        live_head = _live_provenance_fields(root)["repository_head"]
        if document["provenance"].get("repository_head") != live_head:
            raise ValidationError(
                f"{increment_id} candidate is not bound to exact live HEAD"
            )
        return live_head
    manifest_path = root / evidence_dir / "campaign-manifest.json"
    try:
        manifest = load_strict_json(manifest_path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(
            f"cannot parse {increment_id} campaign manifest: {error}"
        ) from error
    if not isinstance(manifest, Mapping):
        raise ValidationError(
            f"{increment_id} campaign manifest is not an object"
        )
    if manifest_member_key == "profiles":
        required_manifest_keys = {
            "schema", "increment_id", "execution_head", "profiles",
        }
    else:
        required_manifest_keys = {
            "schema", "increment_id", "execution_head", "scenario",
        }
    if set(manifest) != required_manifest_keys:
        raise ValidationError(
            f"{increment_id} campaign manifest has an open or incomplete shape"
        )
    members = manifest.get(manifest_member_key)
    if manifest.get("schema") != campaign_schema or manifest.get(
        "increment_id"
    ) != increment_id or not isinstance(members, Mapping):
        raise ValidationError(
            f"{increment_id} campaign manifest identity is incorrect"
        )
    if manifest_member_key == "profiles":
        # Multi-profile: validate exact profile-set and locate this profile.
        if set(members) != contract["profile_value_set"]:
            raise ValidationError(
                f"{increment_id} campaign manifest profile set is incorrect"
            )
        entry = members.get(profile_value)
        relative = f"{evidence_dir}/profiles/{profile_value}/scenario-evidence.json"
    else:
        # Single-scenario: validate entry shape.
        entry = members
        relative = f"{evidence_dir}/scenario-evidence.json"
    if not isinstance(entry, Mapping) or set(entry) != {
        "path", "run_id", "sha256",
    }:
        raise ValidationError(
            f"{increment_id} campaign entry has an open or incomplete shape"
        )
    canonical = (root / relative).resolve(strict=True)
    if evidence_path.resolve(strict=True) != canonical or entry.get("path") != relative:
        raise ValidationError(
            f"{increment_id} retained replay path differs from campaign manifest"
        )
    if entry.get("sha256") != sha256_file(canonical):
        raise ValidationError(
            f"{increment_id} canonical evidence hash differs from campaign manifest"
        )
    artifact_paths = [record["path"] for record in document["artifacts"].values()]
    run_ids = {Path(path).parent.name for path in artifact_paths}
    if len(run_ids) != 1 or entry.get("run_id") not in run_ids:
        raise ValidationError(
            f"{increment_id} run identity differs from campaign manifest"
        )
    execution_head = manifest.get("execution_head")
    if not isinstance(execution_head, str):
        raise ValidationError(
            f"{increment_id} campaign execution head is malformed"
        )
    return execution_head


def _verify_provenance(
    stored: Mapping[str, Any],
    bench_root: Path,
    contract: Mapping[str, Any],
    profile_value: str,
    expected_execution_head: str,
) -> None:
    """Recompute live provenance and compare against stored fields."""
    increment_id = contract["increment_id"]
    live = _live_provenance_fields(bench_root)
    repository = _repository_root(bench_root)
    live_head = live.pop("repository_head")
    stored_head = stored.get("repository_head")
    if stored_head != expected_execution_head:
        raise ValidationError(
            f"recorded {increment_id} repository head differs from exact "
            f"campaign head"
        )
    if not _repository_commit_is_ancestor(
        repository, expected_execution_head, live_head
    ):
        raise ValidationError(
            f"exact {increment_id} campaign head is not an ancestor of live HEAD"
        )
    # Execution manifest at the pinned revision.
    identity_module = importlib.import_module("execution_identity")
    manifest_fn = getattr(
        identity_module,
        contract["execution_manifest_function"],
    )
    live["execution_manifest_sha256"] = manifest_fn(
        bench_root, profile_value, expected_execution_head
    )

    # Extra provenance fields specific to this increment.
    extra: dict[str, Any] = {}
    profile_field = contract["profile_field"]
    extra[profile_field] = profile_value
    extra[contract["profile_manifest_key"]] = manifest_fn(
        bench_root, profile_value, expected_execution_head
    )
    config_sha_key = contract.get("config_sha256_key")
    if config_sha_key:
        extra[config_sha_key] = sha256_file(
            bench_root / "config" / contract["matrix_config"]
        )
    for key, value in {**live, **extra}.items():
        if stored.get(key) != value:
            raise ValidationError(
                f"{increment_id} provenance mismatch for {key}"
            )
    required = set(live) | {
        "repository_head",
        "captured_utc",
        "command_exit_code",
        *extra,
    }
    if set(stored) != required:
        raise ValidationError(
            f"{increment_id} provenance has an open or incomplete shape"
        )
    if stored["command_exit_code"] != 0:
        raise ValidationError(
            f"{increment_id} observer command did not exit successfully"
        )


def validate_evidence(
    evidence_path: str | Path,
    *,
    contract: Mapping[str, Any],
    bench_root: str | Path,
    candidate: bool = False,
) -> Mapping[str, Any]:
    """Independently replay and validate one hash-bound evidence document.

    Parameters
    ----------
    evidence_path:
        Path to the canonical evidence JSON.
    contract:
        The increment contract dict.
    bench_root:
        The bench directory.
    candidate:
        If ``True``, bind the evidence to live HEAD instead of a campaign
        manifest (used during the run wrapper before finalization).
    """
    _ensure_import_paths(bench_root)
    root = Path(bench_root).resolve()
    increment_id = contract["increment_id"]
    profile_field = contract["profile_field"]
    try:
        document = load_strict_json(evidence_path)
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise ValidationError(
            f"cannot parse {increment_id} evidence: {error}"
        ) from error

    # --- 1. Root shape -------------------------------------------------------
    required = set(contract["evidence_root_fields"])
    if not isinstance(document, Mapping) or set(document) != required:
        raise ValidationError(
            f"{increment_id} evidence root has an open or incomplete shape"
        )
    if (
        document["schema"] != contract["schema_id"]
        or document["increment_id"] != increment_id
    ):
        raise ValidationError(f"{increment_id} evidence identity is incorrect")

    # --- 2. Profile resolution -----------------------------------------------
    profile = resolve_profile(contract, document[profile_key(document, profile_field)])
    profile_value = profile.value

    # --- 3. Campaign execution head ------------------------------------------
    execution_head = _campaign_execution_head(
        Path(evidence_path), document, root, contract, profile_value,
        candidate=candidate,
    )

    # --- 4. Artifact paths ---------------------------------------------------
    artifact_prefix = contract["artifact_path_prefix_template"].format(
        evidence_dir=contract["evidence_dir"],
        profile=profile_value,
    )
    _verify_artifact_paths(document, artifact_prefix, increment_id)

    # --- 5. Verify artifacts & metadata --------------------------------------
    artifacts = _verify_artifacts(document, root)
    raw = load_strict_json(artifacts["observer_raw"])
    metadata = load_strict_json(artifacts["run_metadata"])
    metadata_required = set(contract["metadata_fields"])
    if not isinstance(metadata, Mapping) or set(metadata) != metadata_required:
        raise ValidationError(
            f"{increment_id} run metadata has an open or incomplete shape"
        )
    metadata_profile_field = contract.get("metadata_profile_field")
    if metadata_profile_field and metadata.get(metadata_profile_field) != profile_value:
        raise ValidationError(
            f"{increment_id} run metadata profile differs from canonical profile"
        )
    if metadata["observer_exit_code"] != 0:
        raise ValidationError(
            f"{increment_id} hash-bound observer did not exit successfully"
        )
    if metadata["raw_output"] != document["artifacts"]["observer_raw"]["path"]:
        raise ValidationError(
            f"{increment_id} run metadata raw path differs from hash-bound artifact"
        )

    # --- 6. Replay reconstruction --------------------------------------------
    rebuilt = build_evidence(
        raw,
        profile,
        document["provenance"],
        document["artifacts"],
        contract=contract,
        bench_root=root,
    )
    if canonical_json_bytes(rebuilt) != canonical_json_bytes(document):
        raise ValidationError(
            f"canonical {increment_id} evidence differs from raw replay "
            f"reconstruction"
        )

    # --- 7. Map runtime & provenance -----------------------------------------
    _verify_map_runtime(document, artifacts, root)
    _verify_provenance(
        document["provenance"], root, contract, profile_value, execution_head
    )
    return document


def profile_key(document: Mapping[str, Any], profile_field: str) -> str:
    """Return the document key holding the profile value."""
    return profile_field


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--bench-root", required=True, type=Path)
    parser.add_argument("--candidate", action="store_true")
    arguments = parser.parse_args(argv)
    _ensure_import_paths(arguments.bench_root)
    contract = load_contract(arguments.contract)
    try:
        validate_evidence(
            arguments.evidence,
            contract=contract,
            bench_root=arguments.bench_root,
            candidate=arguments.candidate,
        )
    except (ValidationError, TypeError, ValueError, KeyError) as error:
        increment_id = contract["increment_id"]
        print(f"{increment_id} evidence rejected: {error}", file=sys.stderr)
        return 1
    increment_id = contract["increment_id"]
    print(
        f"{increment_id} evidence independently replay-validated: {arguments.evidence}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
