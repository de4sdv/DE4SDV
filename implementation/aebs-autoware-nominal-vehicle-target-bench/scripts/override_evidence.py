#!/usr/bin/env python3
"""Construct one profile-specific INC-AEBS-009D replay document."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src/de4sdv_aebs_009b_bench"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from de4sdv_aebs_009b_bench.override_matrix import OverrideScenario
from de4sdv_aebs_009b_bench.override_runtime import (
    evaluate_profile,
    load_matrix_contract,
    override_result_to_json,
)
from evidence_document import (
    canonical_json_bytes,
    load_strict_json,
    observation_from_json,
    write_evidence_atomic,
)

SCHEMA_ID = "de4sdv.aebs-009d.override-evidence.v1"
INCREMENT_ID = "INC-AEBS-009D"


def build_override_evidence(
    raw: Mapping[str, Any],
    profile: OverrideScenario,
    provenance: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, str]],
    *,
    matrix_path: str | Path,
) -> dict[str, Any]:
    """Recompute the evaluator result; never promote a stored verdict by trust."""
    required = {
        "collector_id",
        "monotonic_start_s",
        "monotonic_end_s",
        "clock_boundary",
        "observations",
        "evaluator_result",
        "activation",
        "errors",
        "terminal_reason",
        "command_exit",
        "limits",
        "override_profile",
        "override_evaluator_result",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("009D raw observer fields do not match the closed contract")
    if raw["override_profile"] != profile.value:
        raise ValueError("raw override profile differs from selected profile")
    observations = tuple(observation_from_json(item) for item in raw["observations"])
    result = evaluate_profile(
        load_matrix_contract(matrix_path),
        profile,
        observations,
        window_end_receipt_s=raw["monotonic_end_s"],
    )
    serialized = override_result_to_json(result)
    if canonical_json_bytes(serialized) != canonical_json_bytes(
        raw["override_evaluator_result"]
    ):
        raise ValueError("raw stored override result differs from independent replay")
    if (
        not result.passed
        or raw["terminal_reason"] != "pass_override_profile"
        or raw["command_exit"] != 0
    ):
        raise ValueError("009D profile did not end in one closed successful verdict")
    return {
        "schema": SCHEMA_ID,
        "increment_id": INCREMENT_ID,
        "profile": profile.value,
        "scenario_id": load_matrix_contract(matrix_path).scenarios[profile].scenario_id,
        "provenance": dict(provenance),
        "collection": {
            "collector_id": raw["collector_id"],
            "monotonic_start_s": raw["monotonic_start_s"],
            "monotonic_end_s": raw["monotonic_end_s"],
            "clock_boundary": raw["clock_boundary"],
            "observations": raw["observations"],
        },
        "collector_contract": {
            "activation": raw["activation"],
            "errors": raw["errors"],
            "terminal_reason": raw["terminal_reason"],
            "command_exit": raw["command_exit"],
            "limits": raw["limits"],
        },
        "evaluation": serialized,
        "artifacts": dict(artifacts),
        "claim_boundary": "one_profile_runtime_verdict_only_no_safety_or_compliance_claim",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument(
        "--profile", required=True, choices=[item.value for item in OverrideScenario]
    )
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument(
        "--matrix",
        type=Path,
        default=BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    document = build_override_evidence(
        load_strict_json(arguments.raw),
        OverrideScenario(arguments.profile),
        load_strict_json(arguments.provenance),
        load_strict_json(arguments.artifacts),
        matrix_path=arguments.matrix,
    )
    write_evidence_atomic(document, arguments.output, arguments.bench_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
