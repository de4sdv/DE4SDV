#!/usr/bin/env python3
"""Construct one INC-AEBS-009F degraded-input profile scenario evidence document.

This module replays the degraded-input matrix evaluator over raw 009B
observations and never promotes a stored verdict by trust.  Each of the five
matrix profiles (stale_input, missing_input, malformed_input,
inconsistent_input, unavailable_input) requires a separate pinned-runtime
execution and verdict.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
for path in (PACKAGE_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from de4sdv_aebs_009b_bench.degraded_input_matrix import (
    DegradedInputDisposition,
    DegradedInputScenario,
    degraded_input_result_to_json,
    evaluate_profile,
    load_matrix_contract,
)
from evidence_document import (
    CLOCK_BOUNDARY,
    canonical_json_bytes,
    load_strict_json,
    observation_from_json,
    observation_to_json,
    sha256_file,
    write_evidence_atomic,
)

INCREMENT_ID = "INC-AEBS-009F"

INCREMENT_CONFIG: Mapping[str, str] = {
    "schema": "de4sdv.aebs-009f.scenario-evidence.v1",
    "campaign_schema": "de4sdv.aebs-009f.campaign-manifest.v1",
    "config_path": "config/scenario-009f-degraded-input-matrix.yaml",
    "evidence_dir": "evidence/009f",
}

CLAIM_BOUNDARY = (
    "one_degraded_input_profile_verdict_only_no_safety_or_compliance_claim"
)

_RAW_REQUIRED = {
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
    "degraded_input_profile",
}


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _profile_subdir(profile: str) -> str:
    return f"{INCREMENT_CONFIG['evidence_dir']}/{profile}"


def _validate_degraded_raw_semantics(
    raw: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> None:
    """Validate collector controls and termination for a degraded-input profile."""
    if raw["collector_id"] != "de4sdv.scenario_observer.v1":
        raise ValueError("raw observer collector_id is not the closed collector")
    if raw["clock_boundary"] != CLOCK_BOUNDARY:
        raise ValueError("raw observer clock_boundary differs from the closed contract")
    start = _finite_number("monotonic_start_s", raw["monotonic_start_s"])
    end = _finite_number("monotonic_end_s", raw["monotonic_end_s"])
    if end < start:
        raise ValueError("raw observer monotonic interval is reversed")
    observations = raw["observations"]
    if not isinstance(observations, list):
        raise TypeError("raw observer observations must be a list")
    receipt_times: list[float] = []
    for item in observations:
        if not isinstance(item, Mapping):
            raise TypeError("raw observer observation must be an object")
        receipt = _finite_number(
            "observation.receipt_monotonic_s", item.get("receipt_monotonic_s")
        )
        if not start <= receipt <= end:
            raise ValueError("raw observer observation is outside the collection interval")
        receipt_times.append(receipt)
    if receipt_times != sorted(receipt_times):
        raise ValueError("raw observer observations are not in monotonic receipt order")

    limits = raw["limits"]
    if not isinstance(limits, Mapping) or set(limits) != {
        "timeout_s", "deadline_s", "observation_cap", "error_cap",
    }:
        raise ValueError("raw observer limits do not match the closed contract")
    timeout = _finite_number("limits.timeout_s", limits["timeout_s"])
    deadline = _finite_number("limits.deadline_s", limits["deadline_s"])
    if timeout <= 0:
        raise ValueError("raw observer timeout must be positive")
    if not math.isclose(deadline, start + timeout, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("raw observer deadline is inconsistent with start and timeout")
    expected_cap = min(100_000, max(1_000, math.ceil(timeout * 1_000)))
    for name, expected in (("observation_cap", expected_cap), ("error_cap", 256)):
        value = limits[name]
        if isinstance(value, bool) or not isinstance(value, int) or value != expected:
            raise ValueError(f"raw observer {name} differs from the collector limit")
    if len(observations) > limits["observation_cap"]:
        raise ValueError("raw observer observation cap was exceeded")

    errors = raw["errors"]
    if not isinstance(errors, list) or not all(
        isinstance(item, str) and item for item in errors
    ):
        raise TypeError("raw observer errors must be a list of nonempty strings")
    if len(errors) > limits["error_cap"]:
        raise ValueError("raw observer error cap was exceeded")

    activation = raw["activation"]
    if not isinstance(activation, Mapping) or set(activation) != {
        "request_time_s", "response_time_s", "status", "response_message",
    }:
        raise ValueError("raw observer activation does not match the closed contract")
    status = activation["status"]
    if status not in {"not_requested", "pending", "succeeded", "failed"}:
        raise ValueError("raw observer activation status is unknown")
    request = activation["request_time_s"]
    response = activation["response_time_s"]
    message = activation["response_message"]
    if status == "not_requested":
        if any(value is not None for value in (request, response, message)):
            raise ValueError("not-requested activation contains request/response data")
    else:
        request_time = _finite_number("activation.request_time_s", request)
        if not start <= request_time <= end:
            raise ValueError("activation request is outside the collection interval")
        if status == "pending":
            if response is not None or message is not None:
                raise ValueError("pending activation contains response data")
        else:
            response_time = _finite_number("activation.response_time_s", response)
            if not request_time <= response_time <= end or not isinstance(message, str):
                raise ValueError(
                    "activation response is inconsistent with collection time"
                )

    command_exit = raw["command_exit"]
    if (
        isinstance(command_exit, bool)
        or not isinstance(command_exit, int)
        or not 0 <= command_exit <= 255
    ):
        raise TypeError("raw observer command_exit must be an exit-status integer")
    terminal = raw["terminal_reason"]
    allowed_terminal = {
        "pass_degraded_input_profile", "activation_failed", "timeout",
        "operator_abort", "observer_exception", "inconclusive_instrumentation",
        "terminal_degraded_input_failure",
    }
    if terminal not in allowed_terminal:
        raise ValueError("raw observer terminal_reason is unknown")
    disposition = evaluation["disposition"]
    passed = evaluation["passed"]
    if terminal == "pass_degraded_input_profile":
        if command_exit != 0 or status != "succeeded" or errors:
            raise ValueError(
                "passing result is inconsistent with collector terminal semantics"
            )
        if disposition != DegradedInputDisposition.PASS_BOUNDED_DETECTION.value:
            raise ValueError(
                "passing collector terminal contradicts evaluator disposition"
            )
    elif command_exit == 0:
        raise ValueError("non-passing result cannot have successful command_exit")
    if passed is True and terminal != "pass_degraded_input_profile":
        raise ValueError("passing evaluator result contradicts collector terminal")
    if terminal == "operator_abort" and command_exit != 130:
        raise ValueError("operator abort must use command exit 130")
    if terminal == "activation_failed" and status != "failed":
        raise ValueError("activation_failed terminal reason requires failed activation")


def build_degraded_input_evidence(
    raw: Mapping[str, Any],
    config_path: str | Path,
    provenance: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, str]],
    *,
    profile: str,
    bench_root: str | Path = BENCH_ROOT,
) -> dict[str, Any]:
    """Recompute the degraded-input evaluator result; never promote a stored verdict by trust."""
    try:
        scenario = DegradedInputScenario(profile)
    except (TypeError, ValueError) as error:
        raise ValueError(f"unknown degraded-input profile: {profile}") from error
    if not isinstance(raw, Mapping) or set(raw) != _RAW_REQUIRED:
        raise ValueError("degraded-input raw observer fields do not match the closed contract")
    if raw["degraded_input_profile"] != scenario.value:
        raise ValueError("raw degraded_input_profile contradicts the selected profile")
    observations = tuple(observation_from_json(item) for item in raw["observations"])
    matrix = load_matrix_contract(config_path)
    if scenario not in matrix.scenarios:
        raise ValueError("degraded-input profile is not part of the closed matrix")
    result = evaluate_profile(
        matrix,
        scenario,
        observations,
        window_end_receipt_s=raw["monotonic_end_s"],
    )
    serialized = degraded_input_result_to_json(result)
    if canonical_json_bytes(serialized) != canonical_json_bytes(raw["evaluator_result"]):
        raise ValueError("raw degraded-input evaluator result differs from independent replay")
    _validate_degraded_raw_semantics(raw, serialized)
    if (
        not result.passed
        or raw["terminal_reason"] != "pass_degraded_input_profile"
        or raw["command_exit"] != 0
    ):
        raise ValueError("degraded-input scenario did not end in one closed successful verdict")
    scenario_id = matrix.scenarios[scenario].scenario_id
    return {
        "schema": INCREMENT_CONFIG["schema"],
        "increment_id": INCREMENT_ID,
        "scenario_id": scenario_id,
        "degraded_input_profile": scenario.value,
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
        "claim_boundary": CLAIM_BOUNDARY,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument(
        "--profile",
        required=True,
        choices=[s.value for s in DegradedInputScenario],
    )
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    document = build_degraded_input_evidence(
        load_strict_json(arguments.raw),
        arguments.bench_root / INCREMENT_CONFIG["config_path"],
        load_strict_json(arguments.provenance),
        load_strict_json(arguments.artifacts),
        profile=arguments.profile,
        bench_root=arguments.bench_root,
    )
    write_evidence_atomic(document, arguments.output, arguments.bench_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
