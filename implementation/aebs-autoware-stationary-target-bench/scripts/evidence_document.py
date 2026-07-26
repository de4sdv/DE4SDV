#!/usr/bin/env python3
"""Deterministic construction of replayable 009B evidence documents.

This module deliberately contains no process execution.  The run wrapper supplies
explicit, already measured provenance and artifact hashes; the independent
validator subsequently recomputes and checks them.
"""
from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence


def _add_source_checkout_imports() -> Path:
    bench = Path(__file__).resolve().parents[1]
    package = bench / "src" / "de4sdv_aebs_009b_bench"
    import sys
    if str(package) not in sys.path:
        sys.path.insert(0, str(package))
    return bench

BENCH_ROOT = _add_source_checkout_imports()

from de4sdv_aebs_009b_bench.scenario_contract import ScenarioConfig, load_scenario_config  # noqa: E402
from de4sdv_aebs_009b_bench.scenario_evaluator import (  # noqa: E402
    EvaluationResult,
    Observation,
    ObservationKind,
    evaluate_scenario,
)

SCHEMA_ID = "de4sdv.aebs-009b.scenario-evidence.v1"
INCREMENT_ID = "INC-AEBS-009B"
CLOCK_BOUNDARY = (
    "Order and causality use only collector monotonic receipt timestamps; preserved source "
    "stamps and host UTC are provenance only, and DDS/network order is not independently proved."
)


def to_plain_json(value: object) -> Any:
    """Return fresh JSON-native values while preserving tuple/list order."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: to_plain_json(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON mapping keys must be strings")
        return {key: to_plain_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_plain_json(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are forbidden in evidence")
        return value
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")


def observation_to_json(item: Observation) -> dict[str, Any]:
    if not isinstance(item, Observation):
        raise TypeError("item must be Observation")
    return {
        "kind": item.kind.value,
        "receipt_monotonic_s": item.receipt_monotonic_s,
        "source_stamp": item.source_stamp,
        "host_utc": item.host_utc,
        "payload": to_plain_json(item.payload),
    }


def evaluation_to_json(result: EvaluationResult) -> dict[str, Any]:
    if not isinstance(result, EvaluationResult):
        raise TypeError("result must be EvaluationResult")
    return {
        "outcome": result.outcome.value,
        "accepted_events": [to_plain_json(event) for event in result.accepted_events],
        "reasons": list(result.reasons),
        "details": to_plain_json(result.details),
    }


def observation_from_json(value: object) -> Observation:
    if not isinstance(value, Mapping) or set(value) != {
        "kind", "receipt_monotonic_s", "source_stamp", "host_utc", "payload"
    }:
        raise ValueError("observation has incorrect fields")
    try:
        kind = ObservationKind(value["kind"])
    except (TypeError, ValueError) as error:
        raise ValueError("unknown observation kind") from error
    return Observation(
        kind=kind,
        payload=value["payload"],
        receipt_monotonic_s=value["receipt_monotonic_s"],
        source_stamp=value["source_stamp"],
        host_utc=value["host_utc"],
    )


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(
        to_plain_json(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ) + "\n").encode("utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_strict_json(path: str | Path) -> Any:
    def pairs(items: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(constant: str) -> None:
        raise ValueError(f"non-finite JSON number: {constant}")
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=pairs, parse_constant=invalid)


def _number(value: object, name: str, *, nonnegative: bool = True) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise TypeError(f"raw observer {name} must be a finite number")
    result = float(value)
    if nonnegative and result < 0:
        raise ValueError(f"raw observer {name} must be nonnegative")
    return result


def validate_raw_semantics(
    raw: Mapping[str, Any], config: ScenarioConfig, evaluation: Mapping[str, Any]
) -> None:
    """Validate collector controls and termination, not just observations."""
    if raw["collector_id"] != "de4sdv.scenario_observer.v1":
        raise ValueError("raw observer collector_id is not the closed collector")
    if raw["clock_boundary"] != CLOCK_BOUNDARY:
        raise ValueError("raw observer clock_boundary differs from the closed contract")
    start = _number(raw["monotonic_start_s"], "monotonic_start_s")
    end = _number(raw["monotonic_end_s"], "monotonic_end_s")
    if end < start:
        raise ValueError("raw observer monotonic interval is reversed")

    limits = raw["limits"]
    if not isinstance(limits, Mapping) or set(limits) != {
        "timeout_s", "deadline_s", "observation_cap", "error_cap"
    }:
        raise ValueError("raw observer limits do not match the closed contract")
    timeout = _number(limits["timeout_s"], "limits.timeout_s", nonnegative=False)
    deadline = _number(limits["deadline_s"], "limits.deadline_s")
    if timeout <= 0 or not math.isclose(
        timeout, config.scenario_timeout_s, rel_tol=0, abs_tol=1e-9
    ):
        raise ValueError("raw observer timeout differs from authoritative scenario timeout")
    if not math.isclose(deadline, start + timeout, rel_tol=0, abs_tol=1e-9):
        raise ValueError("raw observer deadline is inconsistent with start and timeout")
    expected_cap = min(100_000, max(1_000, math.ceil(timeout * 1_000)))
    for name, expected in (("observation_cap", expected_cap), ("error_cap", 256)):
        value = limits[name]
        if isinstance(value, bool) or not isinstance(value, int) or value != expected:
            raise ValueError(f"raw observer {name} differs from the collector limit")
    if len(raw["observations"]) > limits["observation_cap"]:
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
        "request_time_s", "response_time_s", "status", "response_message"
    }:
        raise ValueError("raw observer activation does not match the closed contract")
    status = activation["status"]
    if status not in {"not_requested", "pending", "succeeded", "failed"}:
        raise ValueError("raw observer activation status is unknown")
    request = activation["request_time_s"]
    response = activation["response_time_s"]
    message = activation["response_message"]
    request_time: float | None = None
    if status == "not_requested":
        if any(value is not None for value in (request, response, message)):
            raise ValueError("not-requested activation contains request/response data")
    else:
        request_time = _number(request, "activation.request_time_s")
        if not start <= request_time <= end:
            raise ValueError("activation request is outside the collection interval")
        if status == "pending":
            if response is not None or message is not None:
                raise ValueError("pending activation contains response data")
        else:
            response_time = _number(response, "activation.response_time_s")
            if (
                not request_time <= response_time <= end
                or not isinstance(message, str)
            ):
                raise ValueError(
                    "activation response is inconsistent with collection time"
                )

    target_times = [
        _number(
            item["receipt_monotonic_s"],
            "target_publication.receipt_monotonic_s",
        )
        for item in raw["observations"]
        if isinstance(item, Mapping) and item.get("kind") == "target_publication"
    ]
    if target_times and status == "not_requested":
        raise ValueError("target publication exists without an activation request")
    if request_time is not None and any(item < request_time for item in target_times):
        raise ValueError("target publication precedes activation request")

    command_exit = raw["command_exit"]
    if (
        isinstance(command_exit, bool)
        or not isinstance(command_exit, int)
        or not 0 <= command_exit <= 255
    ):
        raise TypeError("raw observer command_exit must be an exit-status integer")
    terminal = raw["terminal_reason"]
    allowed_terminal = {
        "pass_observed_chain", "activation_failed", "timeout", "operator_abort",
        "observer_exception", "inconclusive_instrumentation",
        "terminal_scenario_failure",
    }
    if terminal not in allowed_terminal:
        raise ValueError("raw observer terminal_reason is unknown")
    outcome = evaluation["outcome"]
    if outcome == "pass_observed_chain":
        if (
            terminal != outcome
            or command_exit != 0
            or status != "succeeded"
            or errors
        ):
            raise ValueError(
                "passing result is inconsistent with collector terminal semantics"
            )
    elif command_exit == 0:
        raise ValueError("non-passing result cannot have successful command_exit")
    if terminal == "operator_abort" and command_exit != 130:
        raise ValueError("operator abort must use command exit 130")
    if terminal == "activation_failed" and status != "failed":
        raise ValueError(
            "activation_failed terminal reason requires failed activation"
        )


def build_evidence_document(
    raw_collection: Mapping[str, Any],
    config: ScenarioConfig,
    provenance: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, str]],
    *,
    increment_id: str = INCREMENT_ID,
) -> dict[str, Any]:
    """Replay raw observations and construct evidence with exactly that result."""
    required_raw = {
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
    }
    if set(raw_collection) != required_raw:
        raise ValueError("raw observer fields do not match the closed collector contract")
    raw_observations = raw_collection["observations"]
    if not isinstance(raw_observations, list):
        raise TypeError("observations must be a list")
    observations = tuple(observation_from_json(item) for item in raw_observations)
    evaluation = evaluate_scenario(config, observations)
    serialized_evaluation = evaluation_to_json(evaluation)
    if canonical_json_bytes(raw_collection["evaluator_result"]) != canonical_json_bytes(
        serialized_evaluation
    ):
        raise ValueError("raw observer evaluation differs from evaluator replay")
    validate_raw_semantics(raw_collection, config, serialized_evaluation)
    return {
        "schema": SCHEMA_ID,
        "scenario_id": config.scenario_id,
        "increment_id": increment_id,
        "provenance": to_plain_json(provenance),
        "collection": {
            "collector_id": raw_collection["collector_id"],
            "monotonic_start_s": raw_collection["monotonic_start_s"],
            "monotonic_end_s": raw_collection["monotonic_end_s"],
            "clock_boundary": raw_collection["clock_boundary"],
            "observations": [observation_to_json(item) for item in observations],
        },
        "collector_contract": {
            "activation": to_plain_json(raw_collection["activation"]),
            "limits": to_plain_json(raw_collection["limits"]),
            "terminal_reason": raw_collection["terminal_reason"],
            "errors": to_plain_json(raw_collection["errors"]),
            "command_exit": raw_collection["command_exit"],
        },
        "evaluation": serialized_evaluation,
        "artifacts": to_plain_json(artifacts),
    }


def _safe_evidence_destination(destination: Path, bench_root: Path) -> None:
    evidence_root = bench_root.resolve() / "evidence"
    if destination.is_symlink():
        raise ValueError("evidence destination must not be a symlink")
    parent = destination.parent.resolve(strict=True)
    if not parent.is_relative_to(evidence_root):
        raise ValueError("evidence destination must remain under bench/evidence")
    if destination.exists() and not destination.is_file():
        raise ValueError("evidence destination must be a regular file")


def write_evidence_atomic(document: object, destination: str | Path, bench_root: str | Path) -> None:
    """Atomically replace a safe regular destination below bench/evidence."""
    destination_path = Path(destination)
    root = Path(bench_root)
    _safe_evidence_destination(destination_path, root)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination_path.name}.", suffix=".tmp", dir=destination_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_json_bytes(document))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def publish_validated_evidence(
    candidate: str | Path, destination: str | Path, bench_root: str | Path
) -> None:
    """Atomically publish one validated regular file without following its target."""
    source = Path(candidate)
    target = Path(destination)
    root = Path(bench_root)
    _safe_evidence_destination(source, root)
    _safe_evidence_destination(target, root)
    if source.is_symlink() or not source.is_file():
        raise ValueError("validated evidence candidate must be a regular file")
    # os.replace has rename(2) no-target-directory semantics: a symlink target is
    # replaced as a directory entry rather than followed.  Still reject it before
    # publication so a pre-existing unsafe canonical is never silently accepted.
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError("canonical evidence destination is unsafe")
    os.replace(source, target)
    directory_fd = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=BENCH_ROOT / "config" / "scenario-009b-stationary-target.yaml")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bench-root", type=Path, default=BENCH_ROOT)
    arguments = parser.parse_args(argv)
    document = build_evidence_document(
        load_strict_json(arguments.raw), load_scenario_config(arguments.config),
        load_strict_json(arguments.provenance), load_strict_json(arguments.artifacts),
    )
    write_evidence_atomic(document, arguments.output, arguments.bench_root)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
