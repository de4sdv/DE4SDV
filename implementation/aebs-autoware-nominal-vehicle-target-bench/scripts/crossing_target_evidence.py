#!/usr/bin/env python3
"""Construct one INC-AEBS-009G/009H crossing-target scenario evidence document.

This module replays the crossing-target evaluator over raw 009B observations and
never promotes a stored verdict by trust.  009G is a pedestrian crossing target;
009H is a bicycle crossing target.  Both share the crossing_target_matrix
evaluator and this evidence pipeline.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

BENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
for path in (PACKAGE_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from de4sdv_aebs_009b_bench.crossing_target_matrix import (
    CrossingTargetSample,
    DiagnosticAuthorization,
    TargetType,
    crossing_target_result_to_json,
    evaluate_crossing_target_scenario,
    load_crossing_target_config,
)
from de4sdv_aebs_009b_bench.scenario_contract import Pose2D
from evidence_document import (
    CLOCK_BOUNDARY,
    canonical_json_bytes,
    load_strict_json,
    observation_from_json,
    observation_to_json,
    sha256_file,
    write_evidence_atomic,
)

INCREMENT_CONFIG: Mapping[str, Mapping[str, str]] = {
    "INC-AEBS-009G": {
        "schema": "de4sdv.aebs-009g.scenario-evidence.v1",
        "campaign_schema": "de4sdv.aebs-009g.campaign-manifest.v1",
        "config_path": "config/scenario-009g-pedestrian-crossing.yaml",
        "evidence_dir": "evidence/009g",
        "target_type": TargetType.PEDESTRIAN.value,
    },
    "INC-AEBS-009H": {
        "schema": "de4sdv.aebs-009h.scenario-evidence.v1",
        "campaign_schema": "de4sdv.aebs-009h.campaign-manifest.v1",
        "config_path": "config/scenario-009h-bicycle-crossing.yaml",
        "evidence_dir": "evidence/009h",
        "target_type": TargetType.BICYCLE.value,
    },
}

CLAIM_BOUNDARY = (
    "one_crossing_target_scenario_verdict_only_no_safety_or_compliance_claim"
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
    "crossing_target_sample",
    "authorization_diagnostic",
}


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _pose_from_json(value: object, name: str) -> Pose2D:
    if not isinstance(value, Mapping) or set(value) != {"x", "y", "yaw_rad"}:
        raise ValueError(f"{name} must be a mapping with x, y, yaw_rad")
    return Pose2D(value["x"], value["y"], value["yaw_rad"])


def _sample_from_json(value: object) -> CrossingTargetSample:
    if not isinstance(value, Mapping) or set(value) != {
        "received",
        "target_pose_map",
        "ego_pose_map",
        "source_stamp",
    }:
        raise ValueError("crossing_target_sample has an open or incomplete shape")
    received = value["received"]
    if not isinstance(received, bool):
        raise TypeError("crossing_target_sample.received must be boolean")
    target_pose = value["target_pose_map"]
    ego_pose = value["ego_pose_map"]
    source_stamp = value["source_stamp"]
    if received:
        target_pose_map = _pose_from_json(target_pose, "target_pose_map")
        ego_pose_map = _pose_from_json(ego_pose, "ego_pose_map")
        if source_stamp is not None and not isinstance(source_stamp, str):
            raise TypeError("source_stamp must be a string or None")
    else:
        if target_pose is not None or ego_pose is not None or source_stamp is not None:
            raise ValueError("a missing sample cannot carry a pose or source stamp")
        target_pose_map = None
        ego_pose_map = None
    return CrossingTargetSample(
        received=received,
        target_pose_map=target_pose_map,
        ego_pose_map=ego_pose_map,
        source_stamp=source_stamp,
    )


def _authorization_from_json(value: object) -> DiagnosticAuthorization:
    if not isinstance(value, Mapping) or set(value) != {
        "source_stamp",
        "node",
        "task",
        "level",
        "message",
    }:
        raise ValueError("authorization_diagnostic has an open or incomplete shape")
    for key in ("source_stamp", "node", "task", "level", "message"):
        if not isinstance(value[key], str) or not value[key]:
            raise TypeError(f"authorization_diagnostic.{key} must be a nonempty string")
    return DiagnosticAuthorization(
        source_stamp=value["source_stamp"],
        node=value["node"],
        task=value["task"],
        level=value["level"],
        message=value["message"],
    )


def _sample_to_json(sample: CrossingTargetSample) -> dict[str, Any]:
    result: dict[str, Any] = {"received": sample.received, "source_stamp": sample.source_stamp}
    if sample.target_pose_map is not None:
        result["target_pose_map"] = {"x": sample.target_pose_map.x, "y": sample.target_pose_map.y, "yaw_rad": sample.target_pose_map.yaw_rad}
    else:
        result["target_pose_map"] = None
    if sample.ego_pose_map is not None:
        result["ego_pose_map"] = {"x": sample.ego_pose_map.x, "y": sample.ego_pose_map.y, "yaw_rad": sample.ego_pose_map.yaw_rad}
    else:
        result["ego_pose_map"] = None
    return result


def _authorization_to_json(auth: DiagnosticAuthorization) -> dict[str, Any]:
    return {
        "source_stamp": auth.source_stamp,
        "node": auth.node,
        "task": auth.task,
        "level": auth.level,
        "message": auth.message,
    }


def _crossing_target_extra_document_fields(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Extract crossing_target_sample and authorization_diagnostic for the evidence document.

    This helper is referenced by the framework contract to produce the extra
    root fields specific to 009G/009H evidence documents.  The ``target_type``
    field is injected separately by the framework using the profile value.
    """
    sample = _sample_from_json(raw["crossing_target_sample"])
    authorization = _authorization_from_json(raw["authorization_diagnostic"])
    return {
        "crossing_target_sample": _sample_to_json(sample),
        "authorization_diagnostic": _authorization_to_json(authorization),
    }


def _validate_crossing_raw_semantics(
    raw: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> None:
    """Validate collector controls and termination for a crossing-target scenario."""
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
        "pass_bounded_target_response", "activation_failed", "timeout",
        "operator_abort", "observer_exception", "inconclusive_instrumentation",
        "terminal_scenario_failure",
    }
    if terminal not in allowed_terminal:
        raise ValueError("raw observer terminal_reason is unknown")
    outcome = evaluation["outcome"]
    if terminal == "pass_bounded_target_response":
        if command_exit != 0 or status != "succeeded" or errors:
            raise ValueError(
                "passing result is inconsistent with collector terminal semantics"
            )
        if outcome != "passBoundedTargetResponse":
            raise ValueError(
                "passing collector terminal contradicts evaluator outcome"
            )
    elif command_exit == 0:
        raise ValueError("non-passing result cannot have successful command_exit")
    if outcome == "passBoundedTargetResponse" and terminal != "pass_bounded_target_response":
        raise ValueError("passing evaluator outcome contradicts collector terminal")
    if terminal == "operator_abort" and command_exit != 130:
        raise ValueError("operator abort must use command exit 130")
    if terminal == "activation_failed" and status != "failed":
        raise ValueError("activation_failed terminal reason requires failed activation")


def build_crossing_target_evidence(
    raw: Mapping[str, Any],
    config_path: str | Path,
    provenance: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, str]],
    *,
    increment_id: str,
    bench_root: str | Path = BENCH_ROOT,
) -> dict[str, Any]:
    """Recompute the crossing-target evaluator result; never promote a stored verdict by trust."""
    if increment_id not in INCREMENT_CONFIG:
        raise ValueError(f"unknown crossing-target increment: {increment_id}")
    meta = INCREMENT_CONFIG[increment_id]
    if not isinstance(raw, Mapping) or set(raw) != _RAW_REQUIRED:
        raise ValueError("crossing-target raw observer fields do not match the closed contract")
    observations = tuple(observation_from_json(item) for item in raw["observations"])
    sample = _sample_from_json(raw["crossing_target_sample"])
    authorization = _authorization_from_json(raw["authorization_diagnostic"])
    config = load_crossing_target_config(config_path)
    if config.increment_id != increment_id:
        raise ValueError("crossing-target config increment does not match selected increment")
    if config.target_type.value != meta["target_type"]:
        raise ValueError("crossing-target config target_type does not match increment")
    result = evaluate_crossing_target_scenario(
        config.contract,
        config.target_type,
        config.geometry,
        config.ego_footprint,
        sample,
        authorization,
        observations,
        window_end_receipt_s=raw["monotonic_end_s"],
    )
    serialized = crossing_target_result_to_json(result)
    if canonical_json_bytes(serialized) != canonical_json_bytes(raw["evaluator_result"]):
        raise ValueError("raw crossing-target evaluator result differs from independent replay")
    _validate_crossing_raw_semantics(raw, serialized)
    if (
        not result.passed
        or raw["terminal_reason"] != "pass_bounded_target_response"
        or raw["command_exit"] != 0
    ):
        raise ValueError("crossing-target scenario did not end in one closed successful verdict")
    return {
        "schema": meta["schema"],
        "increment_id": increment_id,
        "scenario_id": config.scenario_id,
        "target_type": config.target_type.value,
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
        "crossing_target_sample": _sample_to_json(sample),
        "authorization_diagnostic": _authorization_to_json(authorization),
        "evaluation": serialized,
        "artifacts": dict(artifacts),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument(
        "--increment",
        required=True,
        choices=list(INCREMENT_CONFIG),
    )
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    meta = INCREMENT_CONFIG[arguments.increment]
    document = build_crossing_target_evidence(
        load_strict_json(arguments.raw),
        arguments.bench_root / meta["config_path"],
        load_strict_json(arguments.provenance),
        load_strict_json(arguments.artifacts),
        increment_id=arguments.increment,
        bench_root=arguments.bench_root,
    )
    write_evidence_atomic(document, arguments.output, arguments.bench_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
