"""Pure observation collection and orchestration policy for scenario 009B.

This module deliberately has no ROS imports.  Receipt times are supplied by the
adapter and must all come from its single ``time.monotonic`` clock.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from .scenario_contract import BASELINE_REQUIRED_INPUTS, Outcome, ScenarioConfig
from .scenario_evaluator import (
    EvaluationResult,
    Observation,
    ObservationKind,
    evaluate_scenario,
)


def normalize_risk_payload(value: Any) -> dict[str, Any]:
    """Fail closed when the native risk telemetry JSON shape or types drift."""
    required = {
        "rss_distance_m", "object_distance_m", "warning", "intervention"
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError("risk telemetry requires exact keys")
    if type(value["warning"]) is not bool or type(value["intervention"]) is not bool:
        raise ValueError("risk warning and intervention must be JSON booleans")
    numeric: dict[str, float] = {}
    for key in ("rss_distance_m", "object_distance_m"):
        if type(value[key]) not in (int, float):
            raise ValueError(f"risk {key} must be a JSON number")
        numeric[key] = float(value[key])
        if not math.isfinite(numeric[key]):
            raise ValueError(f"risk {key} must be finite")
    return {
        **numeric,
        "warning": value["warning"],
        "intervention": value["intervention"],
    }


_PENDING_AFTER_ACTIVATION = {
    "target_injection", "native_risk_assessment", "warning_request",
    "override_evaluated_clear", "native_aeb_intervention",
    "emergency_braking_request", "normal_path_gate_command",
    "footprint_outcome", "speed_reduction", "verified_ego_stop", "intervention_release",
    "diagnostic_release_independence", "release_footprint",
}

COLLECTOR_ID = "de4sdv.scenario_observer.v1"
CLOCK_BOUNDARY = (
    "Order and causality use only collector monotonic receipt timestamps; preserved source "
    "stamps and host UTC are provenance only, and DDS/network order is not independently proved."
)


def failure_is_pending(result: EvaluationResult) -> bool:
    """Distinguish absent future evidence from an observed terminal counterexample."""

    if result.outcome is not Outcome.FAIL_SCENARIO:
        return False
    failed = result.details.get("failed_event")
    if failed == "footprint_outcome":
        return not result.reasons[0].startswith("Independent map-pose footprints overlap.")
    return failed in {"speed_reduction", "verified_ego_stop", "intervention_release", "release_footprint"}



def validate_installed_config_path(
    config_path: str, installed_config: Path, expected_name: str
) -> Path:
    """Accept the exact installed entry, including colcon's file symlink."""
    candidate = Path(config_path)
    expected = installed_config / expected_name
    if candidate != expected or not candidate.is_file():
        raise ValueError(
            "scenario_config must name the authoritative installed package config"
        )
    return candidate


def exception_report(error: BaseException, *, raw_output_available: bool) -> str:
    """Describe a fatal observer error without exposing its arbitrary message."""
    error_type = type(error).__name__
    if raw_output_available:
        return (
            f"scenario_observer: fatal {error_type}; details recorded in atomic "
            "raw_output"
        )
    return (
        f"scenario_observer: fatal {error_type} before collector initialization; "
        "verify required ROS parameters and package installation"
    )


def closed_constant(
    message_type: type, value: object, names: tuple[str, ...]
) -> str:
    """Map an exact ROS constant without coercing byte-valued uint8 enums."""
    matches = [
        name
        for name in names
        if hasattr(message_type, name) and value == getattr(message_type, name)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"unknown or ambiguous {message_type.__name__} constant {value!r}"
        )
    return matches[0]


def plain_json(value: Any) -> Any:
    """Recursively produce only deterministic JSON-compatible values."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: plain_json(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): plain_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"value of type {type(value).__name__} is not JSON-compatible")


def _safe_absolute_output(path: str | Path) -> Path:
    output = Path(path)
    if not output.is_absolute():
        raise ValueError("raw_output must be absolute")
    if output.exists() and output.is_symlink():
        raise ValueError("raw_output must not be a symlink")
    parent = output.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError("raw_output parent must be an existing directory")
    current = parent
    while current != current.parent:
        if current.is_symlink():
            raise ValueError("raw_output parent must not contain symlinks")
        current = current.parent
    return output


def atomic_write_json(path: str | Path, document: Mapping[str, Any]) -> None:
    """Write one raw result without following destination/parent symlinks."""
    output = _safe_absolute_output(path)
    encoded = json.dumps(plain_json(document), sort_keys=True, indent=2, allow_nan=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if output.exists() and output.is_symlink():
            raise ValueError("raw_output became a symlink")
        os.replace(temporary_name, output)
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


class ObserverCore:
    """Bounded collector plus explicit activation and terminal-state policy."""

    def __init__(
        self, config: ScenarioConfig, timeout_s: float, started_at_s: float,
        *, observation_cap: int | None = None, error_cap: int = 256,
    ) -> None:
        if not isinstance(config, ScenarioConfig):
            raise TypeError("config must be ScenarioConfig")
        for name, value in (("timeout_s", timeout_s), ("started_at_s", started_at_s)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if timeout_s <= 0 or started_at_s < 0:
            raise ValueError("timeout_s must be positive and started_at_s nonnegative")
        self.config = config
        self.timeout_s = float(timeout_s)
        self.started_at_s = float(started_at_s)
        self.deadline_s = self.started_at_s + self.timeout_s
        derived_cap = min(100_000, max(1_000, math.ceil(self.timeout_s * 1_000)))
        self.observation_cap = observation_cap if observation_cap is not None else derived_cap
        if self.observation_cap <= 0 or error_cap <= 0:
            raise ValueError("memory caps must be positive")
        self.error_cap = error_cap
        self.observations: list[Observation] = []
        self.errors: list[str] = []
        self.activation_requested = False
        self.activation_request_time_s: float | None = None
        self.activation_response_time_s: float | None = None
        self.activation_status = "not_requested"
        self.activation_response_message: str | None = None
        self._latest_gate_emergency: tuple[bool, float] | None = None
        self._latest_acceleration: tuple[float, float, str | None] | None = None
        self._cap_failed = False

    def error(self, message: object) -> None:
        text = str(message).strip() or "unspecified collector error"
        if len(self.errors) < self.error_cap:
            self.errors.append(text[:1000])
        elif not self._cap_failed:
            at = self.observations[-1].receipt_monotonic_s if self.observations else self.started_at_s
            self._cap_failure(at, "collector error memory cap reached; instrumentation failed")

    def _cap_failure(self, at: float, reason: str = "observation memory cap reached; instrumentation failed") -> None:
        if self._cap_failed:
            return
        self._cap_failed = True
        if len(self.errors) < self.error_cap:
            self.errors.append(reason)
        statuses = [Observation(
            ObservationKind.INSTRUMENT_STATUS,
            {"topic": topic, "available": False}, at,
        ) for topic in BASELINE_REQUIRED_INPUTS]
        # Preserve the bound.  A tiny caller cap retains at least one explicit failure.
        keep = max(0, self.observation_cap - min(len(statuses), self.observation_cap))
        self.observations[:] = self.observations[:keep] + statuses[: self.observation_cap - keep]

    def add(self, item: Observation) -> bool:
        if not isinstance(item, Observation):
            raise TypeError("item must be Observation")
        if self._cap_failed or len(self.observations) >= self.observation_cap:
            self._cap_failure(item.receipt_monotonic_s)
            return False
        self.observations.append(item)
        return True

    def extend(self, items: Iterable[Observation]) -> None:
        for item in items:
            self.add(item)

    def evaluate(self) -> EvaluationResult:
        return evaluate_scenario(self.config, self.observations)

    def should_request_activation(self) -> bool:
        if self.activation_requested or self._cap_failed:
            return False
        result = self.evaluate()
        labels = {event.label for event in result.accepted_events}
        baseline_support = {
            f"baseline_candidate_start:{topic}" for topic in BASELINE_REQUIRED_INPUTS
        } | {f"baseline_final_support:{topic}" for topic in BASELINE_REQUIRED_INPUTS}
        at = result.details.get("baseline_stable_at_s")
        return (
            result.outcome is Outcome.FAIL_SCENARIO
            and result.details.get("failed_event") == "target_injection"
            and isinstance(at, (int, float)) and not isinstance(at, bool)
            and math.isfinite(float(at))
            and baseline_support.issubset(labels)
        )

    def mark_activation_requested(self, at: float) -> None:
        if self.activation_requested:
            raise RuntimeError("activation may be requested exactly once")
        if not self.should_request_activation():
            raise RuntimeError("activation requested before an accepted stable baseline")
        self.activation_requested = True
        self.activation_request_time_s = float(at)
        self.activation_status = "pending"

    def mark_activation_response(self, at: float, success: bool, message: str = "") -> None:
        if not self.activation_requested or self.activation_status != "pending":
            raise RuntimeError("activation response without one pending request")
        self.activation_response_time_s = float(at)
        self.activation_response_message = str(message)
        self.activation_status = "succeeded" if success else "failed"
        if not success:
            self.error(f"target activation failed: {message}")

    def note_gate_emergency(self, emergency: bool, at: float) -> None:
        if not isinstance(emergency, bool) or not math.isfinite(float(at)):
            raise ValueError("gate emergency status must be boolean with finite receipt time")
        self._latest_gate_emergency = (emergency, float(at))
        self.add(Observation(
            ObservationKind.GATE_EMERGENCY_STATUS, {"emergency": emergency}, at
        ))

    def classify_gate(self, at: float) -> str | None:
        """Classify from the gate's own fresh emergency-status output."""
        status = self._latest_gate_emergency
        if (
            status is None
            or at < status[1]
            or at - status[1] > self.config.baseline.required_input_max_age_s
        ):
            return None
        return "emergency" if status[0] else "nominal"

    def note_acceleration(self, acceleration: float, at: float, source_stamp: str | None) -> None:
        if not math.isfinite(float(acceleration)):
            raise ValueError("acceleration must be finite")
        self._latest_acceleration = (float(acceleration), float(at), source_stamp)

    def make_odometry(
        self,
        speed: float,
        at: float,
        source_stamp: str | None,
        collector_ros_stamp: str,
    ) -> Observation | None:
        if not math.isfinite(float(speed)):
            self.error("non-finite odometry speed")
            return None
        acceleration = self._latest_acceleration
        if acceleration is None or at - acceleration[1] > self.config.baseline.required_input_max_age_s or at < acceleration[1]:
            return None
        return Observation(ObservationKind.ODOMETRY, {
            "speed_mps": float(speed),
            "acceleration_mps2": acceleration[0],
            "collector_ros_stamp": collector_ros_stamp,
        }, at, source_stamp=source_stamp)

    def poll_terminal(self, now_s: float) -> str | None:
        if self.activation_status == "failed":
            return "activation_failed"
        if now_s >= self.deadline_s:
            return "timeout"
        result = self.evaluate()
        if result.outcome is Outcome.ABORTED:
            return "operator_abort"
        if self.activation_status != "succeeded":
            return None
        if result.outcome is Outcome.PASS_OBSERVED_CHAIN:
            return "pass_observed_chain"
        if result.outcome in (Outcome.INCONCLUSIVE_INSTRUMENTATION, Outcome.ABORTED):
            return result.outcome.value
        if result.outcome is Outcome.FAIL_SCENARIO:
            failed = result.details.get("failed_event")
            target_not_observed = failed == "target_injection" and not any(
                item.kind is ObservationKind.TARGET_PUBLICATION
                and self.activation_request_time_s is not None
                and item.receipt_monotonic_s >= self.activation_request_time_s
                for item in self.observations
            )
            missing = (
                result.reasons[0].startswith(("Required event ", "Required exact "))
                or failed == "directional_response"
                or target_not_observed
                or failure_is_pending(result)
            )
            if failed in _PENDING_AFTER_ACTIVATION and missing:
                return None
            return "terminal_scenario_failure"
        return None

    def result_document(
        self, terminal_reason: str, command_exit: int, *, ended_at_s: float
    ) -> dict[str, Any]:
        if (
            isinstance(ended_at_s, bool)
            or not isinstance(ended_at_s, (int, float))
            or not math.isfinite(ended_at_s)
            or ended_at_s < self.started_at_s
        ):
            raise ValueError("ended_at_s must be finite and not precede collection start")
        result = self.evaluate()
        # Hard evidence gates: surface the authoritative source-side warning-lead
        # timing at the top level so campaign evidence can be gated without
        # re-deriving it from video or frame logs. first_warning_timestamp_s /
        # first_intervention_timestamp_s / warning_lead_s come from the
        # evaluator's details when it reached the warning-lead check; missing
        # values mean the run did not reach that gate (campaign ineligible for
        # the full lifecycle claim).
        detail_keys = (
            "warning_lead_s",
            "baseline_stable_at_s",
        )
        evidence = {
            key: result.details[key]
            for key in detail_keys
            if key in result.details
        }
        warning_lead = result.details.get("warning_lead_s")
        first_warning_ts = None
        first_intervention_ts = None
        for event in result.accepted_events:
            if event.label == "warning_request" and first_warning_ts is None:
                first_warning_ts = event.receipt_monotonic_s
            if event.label in ("native_aeb_intervention", "native_aeb_intervention_diagnostic") and first_intervention_ts is None:
                first_intervention_ts = event.receipt_monotonic_s
        return {
            "collector_id": COLLECTOR_ID,
            "monotonic_start_s": self.started_at_s,
            "monotonic_end_s": float(ended_at_s),
            "clock_boundary": CLOCK_BOUNDARY,
            "observations": list(self.observations),
            "evaluator_result": result,
            "lifecycle_gate": {
                "warning_lead_min_s": self.config.outcome_contract.warning_lead_min_s,
                "first_warning_timestamp_s": first_warning_ts,
                "first_intervention_timestamp_s": first_intervention_ts,
                "warning_lead_s": warning_lead,
                "warning_lead_gate": (
                    "pass"
                    if warning_lead is not None
                    and warning_lead >= self.config.outcome_contract.warning_lead_min_s
                    else "not_reached_or_failed"
                ),
                **evidence,
            },
            "activation": {
                "request_time_s": self.activation_request_time_s,
                "response_time_s": self.activation_response_time_s,
                "status": self.activation_status,
                "response_message": self.activation_response_message,
            },
            "errors": list(self.errors),
            "terminal_reason": terminal_reason,
            "command_exit": int(command_exit),
            "limits": {
                "timeout_s": self.timeout_s,
                "deadline_s": self.deadline_s,
                "observation_cap": self.observation_cap,
                "error_cap": self.error_cap,
            },
        }
