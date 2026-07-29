#!/usr/bin/env python3
"""Shared evidence builder parameterized by a contract definition.

This module replaces the per-increment evidence builders (override_evidence,
non_activation_evidence, degraded_input_evidence, crossing_target_evidence)
with a single :func:`build_evidence` function driven by a *contract* — a plain
Python dict (typically loaded from YAML) that describes the increment-specific
schema, evaluator wiring, and raw-observer field contract.

The builder follows the same fail-closed replay discipline as the per-increment
builders: it recomputes the evaluator result from raw observations and never
promotes a stored verdict by trust.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from evidence_document import (
    canonical_json_bytes,
    evaluation_to_json,
    observation_from_json,
    validate_raw_semantics,
    write_evidence_atomic,
)
from evidence_document import load_strict_json  # noqa: F401  (re-exported for CLI use)


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


def _load_profile_enum(contract: Mapping[str, Any]):
    """Return the profile Enum class named in the contract."""
    module = importlib.import_module(contract["profile_enum_module"])
    return getattr(module, contract["profile_enum_name"])


def _load_matrix(bench_root: Path, contract: Mapping[str, Any]):
    """Load the matrix contract using the contract's loader function."""
    loader = _import_function(
        contract["evaluator_module"],
        contract.get("matrix_loader_function", "load_matrix_contract"),
    )
    matrix_path = bench_root / "config" / contract["matrix_config"]
    return loader(matrix_path), matrix_path


def _evaluate_crossing_target(
    bench_root: Path,
    contract: Mapping[str, Any],
    raw: Mapping[str, Any],
    observations: tuple,
    evaluate_fn,
):
    """Evaluate a crossing-target scenario (009G/009H).

    The crossing-target evaluator has a different signature from the matrix
    profile evaluators: it takes the config's contract, target_type, geometry,
    ego_footprint, sample, authorization, and observations.
    """
    config_loader = _import_function(
        contract["evaluator_module"], "load_crossing_target_config"
    )
    config_path = bench_root / "config" / contract["matrix_config"]
    config = config_loader(config_path)

    if config.increment_id != contract["increment_id"]:
        raise ValueError(
            "crossing-target config increment does not match selected increment"
        )

    # Parse the sample and authorization from raw using the per-increment helpers.
    parser_module = contract.get("parser_module", contract["evaluator_module"])
    sample_parser = _import_function(
        parser_module, "_sample_from_json"
    )
    auth_parser = _import_function(
        parser_module, "_authorization_from_json"
    )
    sample = sample_parser(raw["crossing_target_sample"])
    authorization = auth_parser(raw["authorization_diagnostic"])

    result = evaluate_fn(
        config.contract,
        config.target_type,
        config.geometry,
        config.ego_footprint,
        sample,
        authorization,
        observations,
        window_end_receipt_s=raw["monotonic_end_s"],
    )
    return result, config.scenario_id


def build_evidence(
    raw: Mapping[str, Any],
    profile: Any,
    provenance: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, str]],
    *,
    contract: Mapping[str, Any],
    bench_root: str | Path,
) -> dict[str, Any]:
    """Recompute the evaluator result; never promote a stored verdict by trust.

    Parameters
    ----------
    raw:
        The raw observer document (closed-contract JSON from the collector).
    profile:
        The profile Enum member for this evidence document (e.g.
        ``OverrideScenario.fresh_false_control``).
    provenance:
        Execution-identity provenance fields captured by the run wrapper.
    artifacts:
        Mapping of artifact-role → ``{"path": …, "sha256": …}`` records.
    contract:
        The increment contract dict (see module docstring and README).
    bench_root:
        The bench directory containing ``config/``, ``src/``, ``scripts/``.
    """
    _ensure_import_paths(bench_root)
    root = Path(bench_root).resolve()

    # --- 1. Closed raw-contract check ----------------------------------------
    required = set(contract["raw_contract_fields"])
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError(
            f"{contract['increment_id']} raw observer fields do not match "
            f"the closed contract"
        )
    profile_field = contract["profile_field"]
    if profile_field in raw:
        profile_value = profile.value if hasattr(profile, "value") else profile
        if raw[profile_field] != profile_value:
            raise ValueError(f"raw {profile_field} differs from selected profile")

    # --- 2. Parse observations -----------------------------------------------
    observations = tuple(observation_from_json(item) for item in raw["observations"])

    # --- 3. Optional inherited 009B evaluation -------------------------------
    scenario_config_name = contract.get("scenario_config")
    scenario_config = None
    inherited_evaluation: Mapping[str, Any] | None = None
    if scenario_config_name:
        from de4sdv_aebs_009b_bench.scenario_contract import load_scenario_config
        from de4sdv_aebs_009b_bench.scenario_evaluator import evaluate_scenario

        scenario_config = load_scenario_config(
            root / "config" / scenario_config_name
        )
        inherited_evaluation = evaluation_to_json(
            evaluate_scenario(scenario_config, observations)
        )
        if canonical_json_bytes(inherited_evaluation) != canonical_json_bytes(
            raw["evaluator_result"]
        ):
            raise ValueError(
                f"raw inherited result differs from independent replay"
            )

    # --- 4. Profile-specific evaluation --------------------------------------
    evaluate_fn = _import_function(
        contract["evaluator_module"], contract["evaluator_function"]
    )
    serialize_fn = _import_function(
        contract["evaluator_module"], contract["result_serializer"]
    )

    evaluator_mode = contract.get("evaluator_mode", "matrix_profile")
    if evaluator_mode == "crossing_target":
        result, scenario_id = _evaluate_crossing_target(
            root, contract, raw, observations, evaluate_fn
        )
    else:
        matrix, matrix_path = _load_matrix(root, contract)
        result = evaluate_fn(
            matrix,
            profile,
            observations,
            window_end_receipt_s=raw["monotonic_end_s"],
        )
        scenario_id = matrix.scenarios[profile].scenario_id

    serialized = serialize_fn(result)

    evaluator_result_key = contract["evaluator_result_key"]
    if canonical_json_bytes(serialized) != canonical_json_bytes(
        raw[evaluator_result_key]
    ):
        raise ValueError(
            f"raw stored {evaluator_result_key} differs from independent replay"
        )

    # --- 5. Raw-semantics validation -----------------------------------------
    success_terminal = contract["success_terminal"]
    additional_reasons = set(contract.get("additional_terminal_reasons", ()))

    if scenario_config_name:
        # 009D-style: use the shared validate_raw_semantics with the scenario
        # config and inherited evaluation.
        validate_raw_semantics(
            raw,
            scenario_config,
            inherited_evaluation,
            success_terminal=success_terminal,
            success_evaluation_outcome=contract.get(
                "success_evaluation_outcome", None
            ),
            additional_terminal_reasons=additional_reasons,
        )
    else:
        # 009E/009F-style: use a contract-named standalone validator.
        validator_name = contract.get("raw_semantics_validator")
        if validator_name:
            validator = _import_function(
                contract.get("raw_semantics_module", contract["evaluator_module"]),
                validator_name,
            )
            validator(raw, serialized)

    # --- 6. Closed success verdict -------------------------------------------
    if (
        not result.passed
        or raw["terminal_reason"] != success_terminal
        or raw["command_exit"] != 0
    ):
        raise ValueError(
            f"{contract['increment_id']} profile did not end in one closed "
            f"successful verdict"
        )

    # --- 7. Assemble canonical evidence document -----------------------------
    document: dict[str, Any] = {
        "schema": contract["schema_id"],
        "increment_id": contract["increment_id"],
    }

    # The profile key in the output document.  Most increments use "profile",
    # but 009F uses "degraded_input_profile" and 009G/009H omit it entirely.
    document_profile_key = contract.get("document_profile_key", "profile")
    if document_profile_key:
        document[document_profile_key] = profile.value

    document["scenario_id"] = scenario_id
    document["provenance"] = dict(provenance)
    document["collection"] = {
        "collector_id": raw["collector_id"],
        "monotonic_start_s": raw["monotonic_start_s"],
        "monotonic_end_s": raw["monotonic_end_s"],
        "clock_boundary": raw["clock_boundary"],
        "observations": raw["observations"],
    }
    document["collector_contract"] = {
        "activation": raw["activation"],
        "errors": raw["errors"],
        "terminal_reason": raw["terminal_reason"],
        "command_exit": raw["command_exit"],
        "limits": raw["limits"],
    }

    # Extra root fields specific to certain increments (e.g. crossing_target_sample
    # and authorization_diagnostic for 009G/009H).
    extra_fields_fn_name = contract.get("extra_document_fields_function")
    if extra_fields_fn_name:
        extra_fields_fn = _import_function(
            contract.get("extra_document_fields_module", contract["evaluator_module"]),
            extra_fields_fn_name,
        )
        document.update(extra_fields_fn(raw))

    # For crossing-target increments, inject target_type from the profile value.
    if evaluator_mode == "crossing_target":
        document["target_type"] = profile.value

    document["evaluation"] = serialized
    document["artifacts"] = dict(artifacts)
    document["claim_boundary"] = contract["claim_boundary"]
    return document


# ---------------------------------------------------------------------------
# Contract loading helpers
# ---------------------------------------------------------------------------

def load_contract(path: str | Path) -> dict[str, Any]:
    """Load a contract definition from a YAML file."""
    import yaml

    with Path(path).open("r", encoding="utf-8") as stream:
        contract: dict[str, Any] = dict(yaml.safe_load(stream))  # type: ignore[arg-type]
    if not isinstance(contract, Mapping):
        raise TypeError("contract YAML must be a mapping")
    # YAML loads sets as lists; normalise.
    fields = contract.get("raw_contract_fields")
    if isinstance(fields, list):
        contract["raw_contract_fields"] = set(fields)
    elif fields is not None and not isinstance(fields, set):
        raise TypeError("raw_contract_fields must be a list or set")
    additional = contract.get("additional_terminal_reasons")
    if isinstance(additional, list):
        contract["additional_terminal_reasons"] = set(additional)
    # Normalise metadata_fields to a set for the validator.
    metadata_fields = contract.get("metadata_fields")
    if isinstance(metadata_fields, list):
        contract["metadata_fields"] = set(metadata_fields)
    evidence_fields = contract.get("evidence_root_fields")
    if isinstance(evidence_fields, list):
        contract["evidence_root_fields"] = set(evidence_fields)
    # Build profile_value_set for the validator (multi-profile campaigns).
    profile_values = contract.get("profile_values")
    if isinstance(profile_values, list):
        contract["profile_value_set"] = set(profile_values)
    return contract


def resolve_profile(contract: Mapping[str, Any], profile_value: str):
    """Construct a profile Enum member from its string value."""
    _ensure_import_paths_from_contract(contract)
    enum_cls = _load_profile_enum(contract)
    return enum_cls(profile_value)


def _ensure_import_paths_from_contract(contract: Mapping[str, Any]) -> None:
    """Add the bench src package to sys.path based on the evaluator module."""
    # The evaluator module lives under src/de4sdv_aebs_009b_bench which must
    # already be on sys.path when contracts are used in practice.  This helper
    # is a no-op fallback; callers are expected to have called
    # _ensure_import_paths first.
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bench-root", required=True, type=Path)
    arguments = parser.parse_args(argv)

    _ensure_import_paths(arguments.bench_root)
    contract = load_contract(arguments.contract)
    profile = resolve_profile(contract, arguments.profile)
    document = build_evidence(
        load_strict_json(arguments.raw),
        profile,
        load_strict_json(arguments.provenance),
        load_strict_json(arguments.artifacts),
        contract=contract,
        bench_root=arguments.bench_root,
    )
    write_evidence_atomic(document, arguments.output, arguments.bench_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
