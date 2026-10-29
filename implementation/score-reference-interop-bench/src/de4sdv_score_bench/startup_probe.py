"""Evaluator of the startup probe of the one-process adapter (design data).

Each case starts the adapter under one ROS 2 middleware setup, optionally
with other ROS 2 participants on the host before or after it, and states
what it expects:

- ``runs``: the adapter gets ready, stays up for the hold time and stops
  with 0 on SIGTERM; every other participant gets ready; a participant that
  counts the adapter's VelocityReports receives at least one.
- ``does_not_start``: a control of the setup. The adapter does not get
  ready, however it ends. With other participants, fewer of them get ready
  than were started, so the host ran out of what the setup gives (for
  CycloneDDS without multicast: the participant indices). A control can also
  name a text that the adapter's log must hold, the error of the setup.

The report names how the adapter ended: ``aborts_at_override`` when it ended
with SIGABRT and its core shows abort, then ``__cxa_allocate_exception`` at
an address in the executable. A case passes when what happened is what it
expects; the probe passes when every case passes.
"""

from __future__ import annotations

import signal
from typing import Any

EXPECTATIONS = ("runs", "does_not_start")

_RECORD_KEYS = {
    "case",
    "binary",
    "expected",
    "ros_environment",
    "peers_before",
    "peers_after",
    "peers_ready",
    "peer_velocity_reports",
    "ready",
    "survived_hold",
    "end_returncode",
    "stop_returncode",
    "core",
    "override_check_passed",
    "first_named_frame_below_override",
    "required_log_text",
    "required_log_text_found",
}


def _shape_errors(record: Any) -> list[str]:
    if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
        return ["the case record does not have the closed key set"]
    errors = []
    if record["expected"] not in EXPECTATIONS:
        errors.append("unknown expectation")
    for key in ("peers_before", "peers_after", "peers_ready"):
        if type(record[key]) is not int or record[key] < 0:
            errors.append(f"{key} is not a count")
    for key in ("ready", "survived_hold", "core"):
        if type(record[key]) is not bool:
            errors.append(f"{key} is not a boolean")
    for key in ("end_returncode", "stop_returncode", "peer_velocity_reports"):
        if record[key] is not None and type(record[key]) is not int:
            errors.append(f"{key} is not an integer")
    if record["override_check_passed"] is not None and type(record["override_check_passed"]) is not bool:
        errors.append("override_check_passed is not a boolean")
    if (record["required_log_text"] is None) != (record["required_log_text_found"] is None) or (
        record["required_log_text_found"] is not None and type(record["required_log_text_found"]) is not bool
    ):
        errors.append("required_log_text and required_log_text_found do not go together")
    return errors


def observed_behavior(record: dict[str, Any]) -> str:
    if record["ready"] and record["survived_hold"] and record["stop_returncode"] == 0:
        return "runs"
    if record["end_returncode"] == -signal.SIGABRT and record["core"] and record["override_check_passed"]:
        return "aborts_at_override"
    if not record["ready"]:
        return "does_not_start"
    return "other"


def evaluate_case(record: Any) -> dict[str, Any]:
    errors = _shape_errors(record)
    if errors:
        return {"case": record.get("case") if isinstance(record, dict) else None, "observed": None,
                "as_expected": False, "reasons": errors}
    observed = observed_behavior(record)
    reasons = []
    peers = record["peers_before"] + record["peers_after"]
    if record["expected"] == "does_not_start":
        # A control: how the adapter ends is reported, not judged.
        if record["ready"]:
            reasons.append(f"expected does_not_start, observed {observed}")
    elif observed != record["expected"]:
        reasons.append(f"expected {record['expected']}, observed {observed}")
    if record["expected"] == "runs":
        if record["peers_ready"] != peers:
            reasons.append(f"{record['peers_ready']} of {peers} other participants got ready")
        if record["peer_velocity_reports"] is not None and record["peer_velocity_reports"] <= 0:
            reasons.append("the counting participant received no VelocityReport")
    if record["expected"] == "does_not_start" and peers and record["peers_ready"] >= peers:
        reasons.append(f"all {peers} other participants got ready, so the control does not show the limit")
    if record["required_log_text_found"] is False:
        reasons.append(f"the adapter log lacks: {record['required_log_text']}")
    return {"case": record["case"], "observed": observed, "as_expected": not reasons, "reasons": reasons}


def summarize_probe(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(evaluations),
        "as_expected": sum(1 for evaluation in evaluations if evaluation["as_expected"]),
        "gate": "pass" if evaluations and all(evaluation["as_expected"] for evaluation in evaluations) else "fail",
    }
