#!/usr/bin/env python3
"""Shared campaign finalizer parameterized by a contract + profile set.

This module replaces the per-increment finalizers
(finalize_override_campaign, finalize_non_activation_campaign,
finalize_degraded_input_campaign, finalize_crossing_target_campaign) with a
single :func:`finalize_campaign` function.

Two campaign shapes are supported, selected by ``contract["campaign_shape"]``:

* ``"multi_profile"`` (009D, 009E) — the manifest lists one entry per closed
  profile under the ``profiles`` key.
* ``"single_scenario"`` (009F, 009G, 009H) — the manifest lists one entry
  under the ``scenario`` key; ``profiles`` receives a single-element list.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from evidence_document import load_strict_json, sha256_file


def _ensure_import_paths(bench_root: str | Path) -> None:
    """Add the bench ``src`` package and ``scripts`` to ``sys.path``."""
    root = Path(bench_root).resolve()
    package = root / "src" / "de4sdv_aebs_009b_bench"
    scripts = root / "scripts"
    for path in (package, scripts):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _evidence_relative(
    contract: Mapping[str, Any], profile_value: str | None
) -> str:
    """Return the canonical evidence path relative to the bench root."""
    evidence_dir = contract["evidence_dir"]
    shape = contract.get("campaign_shape", "multi_profile")
    if shape == "multi_profile":
        return f"{evidence_dir}/profiles/{profile_value}/scenario-evidence.json"
    return f"{evidence_dir}/scenario-evidence.json"


def _build_manifest_entry(
    relative: str, canonical: Path
) -> dict[str, str]:
    document = load_strict_json(canonical)
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("canonical document is incomplete")
    run_ids = {
        Path(record["path"]).parent.name
        for record in artifacts.values()
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    if len(run_ids) != 1:
        raise ValueError("canonical artifacts do not identify one run")
    return {
        "path": relative,
        "run_id": run_ids.pop(),
        "sha256": sha256_file(canonical),
    }


def _write_manifest_atomic(
    manifest: Mapping[str, Any], manifest_path: Path
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".campaign-manifest.", dir=manifest_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                manifest, stream, sort_keys=True, separators=(",", ":"),
                allow_nan=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, manifest_path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def finalize_campaign(
    bench_root: str | Path,
    *,
    contract: Mapping[str, Any],
    profiles: Iterable[Any],
) -> Path:
    """Finalize one closed retained campaign and return the manifest path.

    Parameters
    ----------
    bench_root:
        The bench directory.
    contract:
        The increment contract dict.
    profiles:
        Iterable of profile Enum members.  For multi-profile campaigns this is
        the full closed set (e.g. ``OverrideScenario``); for single-scenario
        campaigns it should contain one element (the profile or a sentinel).
    """
    root = Path(bench_root).resolve()
    increment_id = contract["increment_id"]
    campaign_schema = contract["campaign_manifest_schema"]
    shape = contract.get("campaign_shape", "multi_profile")
    evidence_dir = contract["evidence_dir"]
    manifest_path = root / evidence_dir / "campaign-manifest.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise ValueError(
            f"refusing to overwrite existing {increment_id} campaign manifest"
        )

    execution_heads: set[str] = set()

    if shape == "multi_profile":
        members: dict[str, dict[str, str]] = {}
        for profile in profiles:
            relative = _evidence_relative(contract, profile.value)
            canonical = root / relative
            if canonical.is_symlink() or not canonical.is_file():
                raise ValueError(
                    f"missing or unsafe canonical {increment_id} profile: "
                    f"{profile.value}"
                )
            document = load_strict_json(canonical)
            if document.get("profile") != profile.value:
                raise ValueError(
                    f"{increment_id} canonical profile differs from manifest slot"
                )
            provenance = document.get("provenance")
            if not isinstance(provenance, dict):
                raise ValueError(
                    f"{increment_id} canonical document is incomplete"
                )
            execution_head = provenance.get("repository_head")
            if not isinstance(execution_head, str):
                raise ValueError(
                    f"{increment_id} canonical execution head is malformed"
                )
            execution_heads.add(execution_head)
            members[profile.value] = _build_manifest_entry(relative, canonical)
        if len(execution_heads) != 1:
            raise ValueError(
                f"{increment_id} canonical profiles are not bound to one "
                f"execution head"
            )
        manifest = {
            "schema": campaign_schema,
            "increment_id": increment_id,
            "execution_head": execution_heads.pop(),
            "profiles": members,
        }
    elif shape == "single_scenario":
        profile_list = list(profiles)
        if len(profile_list) != 1:
            raise ValueError(
                f"{increment_id} single-scenario campaign expects one profile"
            )
        profile_value = (
            profile_list[0].value
            if hasattr(profile_list[0], "value")
            else str(profile_list[0])
        )
        relative = _evidence_relative(contract, profile_value)
        canonical = root / relative
        if canonical.is_symlink() or not canonical.is_file():
            raise ValueError(
                f"missing or unsafe canonical {increment_id} evidence"
            )
        document = load_strict_json(canonical)
        profile_field = contract["profile_field"]
        if document.get("increment_id") != increment_id:
            raise ValueError(
                f"{increment_id} canonical evidence increment differs from "
                f"manifest slot"
            )
        if profile_field in document and document.get(profile_field) != profile_value:
            raise ValueError(
                f"{increment_id} canonical evidence profile differs from "
                f"manifest slot"
            )
        provenance = document.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(f"canonical {increment_id} document is incomplete")
        execution_head = provenance.get("repository_head")
        if not isinstance(execution_head, str):
            raise ValueError(
                f"canonical {increment_id} execution head is malformed"
            )
        entry = _build_manifest_entry(relative, canonical)
        manifest = {
            "schema": campaign_schema,
            "increment_id": increment_id,
            "execution_head": execution_head,
            "scenario": entry,
        }
    else:
        raise ValueError(f"unknown campaign_shape: {shape}")

    _write_manifest_atomic(manifest, manifest_path)
    return manifest_path


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--bench-root", required=True, type=Path)
    arguments = parser.parse_args(argv)
    _ensure_import_paths(arguments.bench_root)

    from evidence_pipeline import load_contract, resolve_profile

    contract = load_contract(arguments.contract)
    # Profiles come from the contract's profile enum.
    profile_enum_module = contract["profile_enum_module"]
    profile_enum_name = contract["profile_enum_name"]
    import importlib

    enum_module = importlib.import_module(profile_enum_module)
    enum_cls = getattr(enum_module, profile_enum_name)
    profiles = list(enum_cls)

    shape = contract.get("campaign_shape", "multi_profile")
    if shape == "single_scenario":
        # Single-scenario finalizers take an explicit --profile argument in
        # the per-increment scripts; here we require the contract to name it.
        profile_value = contract.get("default_profile")
        if profile_value is None:
            print(
                f"{contract['increment_id']} single-scenario finalization "
                f"requires contract['default_profile']",
                file=sys.stderr,
            )
            return 1
        profiles = [resolve_profile(contract, profile_value)]

    try:
        manifest = finalize_campaign(
            arguments.bench_root, contract=contract, profiles=profiles
        )
        from evidence_validator import validate_evidence

        for profile in profiles:
            relative = _evidence_relative(contract, getattr(profile, "value", profile))
            validate_evidence(
                arguments.bench_root / relative,
                contract=contract,
                bench_root=arguments.bench_root,
            )
    except (OSError, TypeError, ValueError, KeyError) as error:
        increment_id = contract["increment_id"]
        print(
            f"{increment_id} campaign finalization rejected: {error}",
            file=sys.stderr,
        )
        return 1
    increment_id = contract["increment_id"]
    print(
        f"Finalized and replay-validated {increment_id} campaign manifest: {manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
