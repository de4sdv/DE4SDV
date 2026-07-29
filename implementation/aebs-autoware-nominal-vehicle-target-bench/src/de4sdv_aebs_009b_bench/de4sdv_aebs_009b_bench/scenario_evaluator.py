"""Pure evaluation of the 009B collector's observed event chain.

Only collector monotonic receipt times establish freshness and order.  Source stamps and optional host UTC strings are retained as provenance and are
never compared with receipt time. Odometry source freshness is replayed only
against a collector ROS-clock stamp captured in the same ROS clock domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .footprint_geometry import footprint_relation
from .scenario_contract import BASELINE_REQUIRED_INPUTS, Outcome, Pose2D, ScenarioConfig


class ObservationKind(str, Enum):
    DIAGNOSTIC = "diagnostic"
    AEB_INTERVENTION = "aeb_intervention"
    RISK_ASSESSMENT = "risk_assessment"
    WARNING_REQUEST = "warning_request"
    OVERRIDE_EVALUATION = "override_evaluation"
    OVERRIDE_AUTHORIZATION = "override_authorization"
    BRAKING_REQUEST = "braking_request"
    COORDINATION_STATE = "coordination_state"
    RUNTIME_GRAPH = "runtime_graph"
    RELATIVE_STATE = "relative_state"
    FOOTPRINT_STATE = "footprint_state"
    AUTONOMOUS_AVAILABILITY = "autonomous_availability"
    MRM_STATE = "mrm_state"
    EMERGENCY_OPERATOR_STATUS = "emergency_operator_status"
    NOMINAL_COMMAND = "nominal_command"
    EMERGENCY_COMMAND = "emergency_command"
    GATE_EMERGENCY_STATUS = "gate_emergency_status"
    GATE_COMMAND = "gate_command"
    ODOMETRY = "odometry"
    TARGET_PUBLICATION = "target_publication"
    DEGRADED_INPUT_AUTHORIZATION = "degraded_input_authorization"
    DEGRADED_STATE_TRANSITION = "degraded_state_transition"
    DEGRADED_STATUS_INDICATION = "degraded_status_indication"
    INSTRUMENT_STATUS = "instrument_status"
    OPERATOR_ABORT = "operator_abort"


class _StageObservation(Enum):
    TRANSITION = "transition"
    STEADY_BEFORE = "steady_before"
    CONTRADICTION = "contradiction"


REQUIRED_INPUT_KIND: Mapping[str, ObservationKind] = MappingProxyType(
    dict(zip(BASELINE_REQUIRED_INPUTS, (
        ObservationKind.DIAGNOSTIC,
        ObservationKind.AUTONOMOUS_AVAILABILITY,
        ObservationKind.NOMINAL_COMMAND,
        ObservationKind.GATE_COMMAND,
        ObservationKind.ODOMETRY,
    ), strict=True))
)

_SCHEMAS: Mapping[ObservationKind, Mapping[str, str]] = {
    ObservationKind.DIAGNOSTIC: {"node": "str", "task": "str", "level": "str"},
    ObservationKind.AEB_INTERVENTION: {
        "node": "str", "task": "str", "level": "str", "message": "str",
        "rss_distance_m": "number", "object_distance_m": "number", "object_speed_mps": "number",
    },
    ObservationKind.RISK_ASSESSMENT: {"rss_distance_m": "number", "object_distance_m": "number", "warning": "bool", "intervention": "bool"},
    ObservationKind.WARNING_REQUEST: {"active": "bool"},
    ObservationKind.OVERRIDE_EVALUATION: {
        "clear": "bool", "source_value": "bool", "source_age_s": "number", "context": "str",
 "diagnostic_source_stamp": "str",
    },
    ObservationKind.OVERRIDE_AUTHORIZATION: {
        "override_source_value": "str",
        "override_source_stamp": "str",
        "authorization_diagnostic_source_stamp": "str",
        "disposition": "str",
    },
    ObservationKind.BRAKING_REQUEST: {"speed_mps": "number", "acceleration_mps2": "number"},
    ObservationKind.COORDINATION_STATE: {"state": "str"},
    ObservationKind.RUNTIME_GRAPH: {
        "nominal_publisher_count": "number", "nominal_publishers": "str",
        "mrm_publisher_count": "number", "mrm_publishers": "str",
    },
    ObservationKind.RELATIVE_STATE: {"gap_m": "number", "ego_speed_mps": "number", "target_speed_mps": "number", "closing_speed_mps": "number"},
    ObservationKind.FOOTPRINT_STATE: {
        "ego_x": "number", "ego_y": "number", "ego_yaw_rad": "number",
        "target_x": "number", "target_y": "number", "target_yaw_rad": "number",
        "sample_skew_s": "number", "separation_m": "number", "overlap": "bool",
    },
    ObservationKind.AUTONOMOUS_AVAILABILITY: {"available": "bool"},
    ObservationKind.MRM_STATE: {"state": "str", "behavior": "str"},
    ObservationKind.EMERGENCY_OPERATOR_STATUS: {"state": "str"},
    ObservationKind.NOMINAL_COMMAND: {"speed_mps": "number", "acceleration_mps2": "number"},
    ObservationKind.EMERGENCY_COMMAND: {"speed_mps": "number", "acceleration_mps2": "number"},
    ObservationKind.GATE_EMERGENCY_STATUS: {"emergency": "bool"},
    ObservationKind.GATE_COMMAND: {"path": "str", "acceleration_mps2": "number"},
    ObservationKind.ODOMETRY: {
        "speed_mps": "number",
        "acceleration_mps2": "number",
        "collector_ros_stamp": "str",
    },
    ObservationKind.TARGET_PUBLICATION: {
        "identity": "str", "frame": "str", "x": "number", "y": "number", "yaw_rad": "number"
    },
    ObservationKind.DEGRADED_INPUT_AUTHORIZATION: {
        "degraded_input_profile": "str",
        "affected_topic": "str",
        "input_health": "str",
        "degraded_state_source_stamp": "str",
        "authorization_diagnostic_source_stamp": "str",
        "disposition": "str",
    },
    ObservationKind.DEGRADED_STATE_TRANSITION: {
        "affected_topic": "str",
        "input_health": "str",
        "degraded_state_source_stamp": "str",
        "previous_state": "str",
        "current_state": "str",
    },
    ObservationKind.DEGRADED_STATUS_INDICATION: {
        "affected_topic": "str",
        "status": "str",
        "indicated_degraded": "bool",
    },
    ObservationKind.INSTRUMENT_STATUS: {"topic": "str", "available": "bool"},
    ObservationKind.OPERATOR_ABORT: {"reason": "str"},
}

_ALLOWED_PAYLOAD_VALUES: Mapping[tuple[ObservationKind, str], frozenset[str]] = {
    (ObservationKind.DIAGNOSTIC, "level"): frozenset({"OK", "WARN", "ERROR", "STALE"}),
    (ObservationKind.MRM_STATE, "state"): frozenset({"NORMAL", "MRM_OPERATING", "MRM_SUCCEEDED", "MRM_FAILED"}),
    (ObservationKind.MRM_STATE, "behavior"): frozenset({"NONE", "EMERGENCY_STOP"}),
    (ObservationKind.EMERGENCY_OPERATOR_STATUS, "state"): frozenset({"NOT_AVAILABLE", "AVAILABLE", "OPERATING", "SUCCEEDED", "FAILED"}),
    (ObservationKind.GATE_COMMAND, "path"): frozenset({"nominal", "emergency"}),
    (ObservationKind.COORDINATION_STATE, "state"): frozenset({
        "armed", "braking_latched", "released_verified_stop",
    }),
    (ObservationKind.OVERRIDE_AUTHORIZATION, "override_source_value"): frozenset({
        "true", "false", "none",
    }),
    (ObservationKind.OVERRIDE_AUTHORIZATION, "disposition"): frozenset({
        "control_clear", "conscious_override", "degraded_stale_source",
        "inconclusive_missing_source", "error_malformed_source",
        "error_future_source",
    }),
    (ObservationKind.DEGRADED_INPUT_AUTHORIZATION, "input_health"): frozenset({
        "stale", "missing", "malformed", "inconsistent", "unavailable",
    }),
    (ObservationKind.DEGRADED_INPUT_AUTHORIZATION, "disposition"): frozenset({
        "pass_bounded_detection",
        "fail_wrong_disposition",
        "inconclusive_instrumentation",
        "error_evidence",
    }),
    (ObservationKind.DEGRADED_STATE_TRANSITION, "input_health"): frozenset({
        "stale", "missing", "malformed", "inconsistent", "unavailable",
    }),
    (ObservationKind.DEGRADED_STATE_TRANSITION, "previous_state"): frozenset({
        "nominal", "degraded", "unavailable",
    }),
    (ObservationKind.DEGRADED_STATE_TRANSITION, "current_state"): frozenset({
        "nominal", "degraded", "unavailable",
    }),
    (ObservationKind.DEGRADED_STATUS_INDICATION, "status"): frozenset({
        "nominal", "degraded", "unavailable",
    }),
}


def _finite_nonnegative(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("payload keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Observation:
    """Validated immutable collector observation in distinct clock domains."""

    kind: ObservationKind
    payload: Mapping[str, Any]
    receipt_monotonic_s: float
    source_stamp: str | None = None
    host_utc: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ObservationKind):
            raise TypeError("kind must be an ObservationKind")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        schema = _SCHEMAS[self.kind]
        if set(self.payload) != set(schema):
            raise ValueError(f"{self.kind.value} payload requires exactly {sorted(schema)}")
        for key, expected in schema.items():
            value = self.payload[key]
            if expected == "bool" and not isinstance(value, bool):
                raise TypeError(f"payload {key} must be bool")
            if expected == "str" and (not isinstance(value, str) or not value):
                raise TypeError(f"payload {key} must be a nonempty string")
            if expected == "number":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise TypeError(f"payload {key} must be a number")
                if not math.isfinite(float(value)):
                    raise ValueError(f"payload {key} must be finite")
            allowed = _ALLOWED_PAYLOAD_VALUES.get((self.kind, key))
            if allowed is not None and value not in allowed:
                raise ValueError(f"payload {key} must be one of {sorted(allowed)}")
        if self.kind is ObservationKind.INSTRUMENT_STATUS and self.payload["topic"] not in BASELINE_REQUIRED_INPUTS:
            raise ValueError("instrument status topic must be one of the seven required inputs")
        object.__setattr__(self, "payload", _freeze(dict(self.payload)))
        object.__setattr__(self, "receipt_monotonic_s", _finite_nonnegative("receipt_monotonic_s", self.receipt_monotonic_s))
        for name in ("source_stamp", "host_utc"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise TypeError(f"{name} must be a nonempty string or None")
        if self.host_utc is not None:
            try:
                parsed_host = datetime.fromisoformat(self.host_utc.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError("host_utc must be an ISO-8601 UTC timestamp") from error
            if parsed_host.utcoffset() != timedelta(0):
                raise ValueError("host_utc must carry a UTC offset")


@dataclass(frozen=True)
class EventReference:
    label: str
    observation_index: int
    kind: ObservationKind
    receipt_monotonic_s: float
    source_stamp: str | None
    host_utc: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise TypeError("label must be a nonempty string")
        if isinstance(self.observation_index, bool) or not isinstance(self.observation_index, int):
            raise TypeError("observation_index must be an integer")
        if self.observation_index < 0:
            raise ValueError("observation_index must be nonnegative")
        if not isinstance(self.kind, ObservationKind):
            raise TypeError("kind must be an ObservationKind")
        object.__setattr__(self, "receipt_monotonic_s", _finite_nonnegative("receipt_monotonic_s", self.receipt_monotonic_s))
        for name in ("source_stamp", "host_utc"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise TypeError(f"{name} must be a nonempty string or None")
        if self.host_utc is not None:
            try:
                parsed_host = datetime.fromisoformat(self.host_utc.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError("host_utc must be an ISO-8601 UTC timestamp") from error
            if parsed_host.utcoffset() != timedelta(0):
                raise ValueError("host_utc must carry a UTC offset")


_RESULT_TOKEN = object()


@dataclass(frozen=True, init=False)
class EvaluationResult:
    outcome: Outcome
    accepted_events: tuple[EventReference, ...]
    reasons: tuple[str, ...]
    details: Mapping[str, Any]

    def __init__(
        self,
        outcome: Outcome,
        accepted_events: tuple[EventReference, ...],
        reasons: tuple[str, ...],
        details: Mapping[str, Any],
        *,
        _token: object,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise PermissionError("EvaluationResult values can only be created by evaluate_scenario")
        if not isinstance(outcome, Outcome):
            raise TypeError("outcome must be Outcome")
        if not isinstance(accepted_events, tuple) or not all(isinstance(event, EventReference) for event in accepted_events):
            raise TypeError("accepted_events must be a tuple of EventReference values")
        if not isinstance(reasons, tuple) or not reasons or not all(isinstance(reason, str) and reason for reason in reasons):
            raise TypeError("reasons must be a nonempty tuple of nonempty strings")
        if not isinstance(details, Mapping):
            raise TypeError("details must be a mapping")
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "accepted_events", tuple(accepted_events))
        object.__setattr__(self, "reasons", tuple(reasons))
        object.__setattr__(self, "details", _freeze(dict(details)))


_CLOCK_BOUNDARY = (
    "Order and causality use only collector monotonic receipt timestamps; preserved source stamps "
    "and host UTC are provenance only, and DDS/network order is not independently proved."
)


def _reference(label: str, index: int, item: Observation) -> EventReference:
    return EventReference(label, index, item.kind, item.receipt_monotonic_s, item.source_stamp, item.host_utc)


def _result(outcome: Outcome, events: list[EventReference], reason: str, details: Mapping[str, Any]) -> EvaluationResult:
    closed_details = {
        **details,
        "clock_order_domain": "collector_monotonic_within_one_collector",
        "source_stamp_comparison": "forbidden",
        "accepted_receipt_times_s": tuple(event.receipt_monotonic_s for event in events),
        "clock_provenance": tuple((event.source_stamp, event.host_utc) for event in events),
    }
    return EvaluationResult(outcome, tuple(events), (reason, _CLOCK_BOUNDARY), closed_details, _token=_RESULT_TOKEN)


def _baseline_ok(config: ScenarioConfig, item: Observation) -> bool:
    p = item.payload
    if item.kind is ObservationKind.DIAGNOSTIC:
        return (
            p["node"] == config.baseline.diagnostic_node
            and p["task"] == config.baseline.diagnostic_task
            and p["level"] == config.baseline.diagnostic_level
        )
    if item.kind is ObservationKind.AUTONOMOUS_AVAILABILITY:
        return p["available"] is True
    if item.kind is ObservationKind.NOMINAL_COMMAND:
        return p["speed_mps"] > 0.0 and p["acceleration_mps2"] >= 0.0
    if item.kind is ObservationKind.GATE_COMMAND:
        return p["path"] == "nominal" and p["acceleration_mps2"] >= 0.0
    if item.kind is ObservationKind.ODOMETRY:
        return p["speed_mps"] >= config.baseline.ego_speed_min_mps
    return False


def _source_is_fresh_in_collector_ros_clock(
    observation: Observation, max_age_s: float
) -> bool:
    if observation.source_stamp is None:
        return False
    try:
        age = Decimal(observation.payload["collector_ros_stamp"]) - Decimal(
            observation.source_stamp
        )
    except (InvalidOperation, KeyError):
        return False
    return Decimal(0) <= age <= Decimal(str(max_age_s))


def evaluate_scenario(config: ScenarioConfig, observations: Iterable[Observation]) -> EvaluationResult:
    items = list(observations)
    if any(not isinstance(item, Observation) for item in items):
        raise TypeError("observations must contain only Observation values")
    events: list[EventReference] = []
    times = [item.receipt_monotonic_s for item in items]
    if any(later < earlier for earlier, later in zip(times, times[1:])):
        return _result(Outcome.FAIL_SCENARIO, events, "Observation receipt times are not monotonic.", {"failed_event": "observation_order"})
    forbidden = {
        ObservationKind.MRM_STATE,
        ObservationKind.EMERGENCY_OPERATOR_STATUS,
        ObservationKind.EMERGENCY_COMMAND,
    }
    if any(
        item.kind in forbidden
        or (item.kind is ObservationKind.GATE_EMERGENCY_STATUS and item.payload["emergency"] is True)
        for item in items
    ):
        return _result(Outcome.FAIL_SCENARIO, events, "Nominal 009B evidence contains an MRM/emergency-path observation.", {"failed_event": "nominal_path_isolation"})
    for index, item in enumerate(items):
        if item.kind is ObservationKind.OPERATOR_ABORT:
            return _result(Outcome.ABORTED, events, "Operator abort observed.", {"failed_event": "operator_abort"})
        if item.kind is ObservationKind.INSTRUMENT_STATUS and item.payload["available"] is False:
            return _result(Outcome.INCONCLUSIVE_INSTRUMENTATION, events, "Required instrumentation became unavailable.", {"failed_event": "instrumentation"})

    by_kind: dict[ObservationKind, list[tuple[int, Observation]]] = {}
    for index, item in enumerate(items):
        by_kind.setdefault(item.kind, []).append((index, item))
    supports: list[tuple[str, tuple[int, Observation], tuple[int, Observation]]] = []
    for topic, kind in REQUIRED_INPUT_KIND.items():
        candidates = [(i, o) for i, o in by_kind.get(kind, []) if _baseline_ok(config, o)]
        if not candidates:
            return _result(Outcome.FAIL_SCENARIO, events, f"Required stable baseline input missing: {topic}.", {"failed_event": "baseline_precondition"})
        supports.append((topic, candidates[0], candidates[-1]))
    start = max(first[1].receipt_monotonic_s for _, first, _ in supports)
    end = start + config.baseline.stable_duration_s
    final_supports: list[tuple[str, tuple[int, Observation], tuple[int, Observation]]] = []
    for topic, first_support, _ in supports:
        kind = REQUIRED_INPUT_KIND[topic]
        interval = [
            (i, o) for i, o in by_kind.get(kind, [])
            if start <= o.receipt_monotonic_s <= end
        ]
        eligible = [(i, o) for i, o in interval if _baseline_ok(config, o)]
        if any(not _baseline_ok(config, o) for _, o in interval):
            return _result(Outcome.FAIL_SCENARIO, events, "Stable baseline contains a contradictory sample.", {"failed_event": "baseline_precondition"})
        if not eligible or end - eligible[-1][1].receipt_monotonic_s > config.baseline.required_input_max_age_s:
            return _result(Outcome.FAIL_SCENARIO, events, "Stable baseline duration/freshness not yet established.", {"failed_event": "baseline_precondition"})
        final_supports.append((topic, first_support, eligible[-1]))
    for topic, first_support, final_support in final_supports:
        events.append(_reference(f"baseline_candidate_start:{topic}", first_support[0], first_support[1]))
        events.append(_reference(f"baseline_final_support:{topic}", final_support[0], final_support[1]))
    details: dict[str, Any] = {"baseline_stable_at_s": end}

    def first(kind: ObservationKind, label: str, after: float, predicate=lambda _p: True):
        for index, item in by_kind.get(kind, []):
            if item.receipt_monotonic_s > after and predicate(item.payload):
                events.append(_reference(label, index, item))
                return index, item
        return None

    target = first(ObservationKind.TARGET_PUBLICATION, "target_injection", end)
    if target is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required event target_injection not observed.", {**details, "failed_event": "target_injection"})
    _, target_item = target
    risk = first(ObservationKind.RISK_ASSESSMENT, "native_risk_assessment", target_item.receipt_monotonic_s, lambda p: p["warning"] is True and p["intervention"] is False)
    if risk is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required event native_risk_assessment not observed.", {**details, "failed_event": "native_risk_assessment"})
    _, risk_item = risk
    warning = first(ObservationKind.WARNING_REQUEST, "warning_request", risk_item.receipt_monotonic_s, lambda p: p["active"] is True)
    if warning is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required event warning_request not observed.", {**details, "failed_event": "warning_request"})
    _, warning_item = warning
    override = next((
        (i, o) for i, o in by_kind.get(ObservationKind.OVERRIDE_EVALUATION, [])
        if warning_item.receipt_monotonic_s < o.receipt_monotonic_s
        and o.payload["context"] == "intervention"
    ), None)
    if override is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required event intervention override authorization not observed.", {**details, "failed_event": "override_evaluated_clear"})
    intervention = next((
        (i, o) for i, o in by_kind.get(ObservationKind.AEB_INTERVENTION, [])
        if o.receipt_monotonic_s > warning_item.receipt_monotonic_s
        and o.source_stamp == override[1].payload["diagnostic_source_stamp"]
        and abs(o.receipt_monotonic_s - override[1].receipt_monotonic_s) <= 0.2
        and o.payload["node"] == "autonomous_emergency_braking"
        and o.payload["task"] == "aeb_emergency_stop"
        and o.payload["level"] == "ERROR"
        and o.payload["message"] == "[AEB]: Emergency Brake"
        and o.payload["object_distance_m"] <= o.payload["rss_distance_m"]
    ), None)
    if intervention is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required exact native_aeb_intervention paired to authorization not observed.", {**details, "failed_event": "native_aeb_intervention"})
    intervention_index, intervention_item = intervention
    graph_items = list(by_kind.get(ObservationKind.RUNTIME_GRAPH, []))
    pre_intervention_graph_items = [
        (i, o) for i, o in graph_items
        if o.receipt_monotonic_s <= intervention_item.receipt_monotonic_s
    ]
    def expected_graph(item: Observation) -> bool:
        return (
            item.payload["nominal_publisher_count"] == 1.0
            and item.payload["nominal_publishers"] == "/:de4sdv_aebs_coordinator"
            and item.payload["mrm_publisher_count"] == 0.0
            and item.payload["mrm_publishers"] == "none"
        )
    accepted_graph_position = next(
        (position for position in range(len(pre_intervention_graph_items) - 1, -1, -1)
         if expected_graph(pre_intervention_graph_items[position][1])),
        None,
    )
    if accepted_graph_position is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Runtime graph does not prove the sole coordinator/no-MRM publisher boundary.", {**details, "failed_event": "runtime_graph_isolation"})
    graph_index, graph_item = pre_intervention_graph_items[accepted_graph_position]
    events.append(_reference("runtime_graph_isolation", graph_index, graph_item))
    # The authorization was selected above by exact diagnostic source stamp.
    if (
        override[1].payload["clear"] is not True
        or override[1].payload["source_value"] is not False
        or override[1].source_stamp is None
        or not 0.0 <= override[1].payload["source_age_s"] <= config.baseline.override_max_age_s
        or abs(intervention_item.receipt_monotonic_s - override[1].receipt_monotonic_s) > config.baseline.override_max_age_s
    ):
        return _result(Outcome.FAIL_SCENARIO, events, "No fresh source-stamped false override sample is clear at intervention.", {**details, "failed_event": "override_evaluated_clear"})
    override_index, override_item = override
    paired_diagnostic = next((
        (i, o) for i, o in by_kind.get(ObservationKind.DIAGNOSTIC, [])
        if o.receipt_monotonic_s == intervention_item.receipt_monotonic_s
        and o.source_stamp == intervention_item.source_stamp
        and o.payload == {
            "node": "autonomous_emergency_braking",
            "task": "aeb_emergency_stop",
            "level": "ERROR",
        }
    ), None)
    if paired_diagnostic is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Exact native intervention lacks its paired ERROR diagnostic.", {**details, "failed_event": "native_aeb_intervention"})
    events.append(_reference("override_evaluated_clear", override_index, override_item))
    events.append(_reference("native_aeb_intervention_diagnostic", paired_diagnostic[0], paired_diagnostic[1]))
    events.append(_reference("native_aeb_intervention", intervention_index, intervention_item))
    lead = intervention_item.receipt_monotonic_s - warning_item.receipt_monotonic_s
    details["warning_lead_s"] = lead
    if lead < config.outcome_contract.warning_lead_min_s:
        return _result(Outcome.FAIL_SCENARIO, events, "Warning lead is below the configured scenario acceptance threshold.", {**details, "failed_event": "warning_lead"})
    brake = first(
        ObservationKind.BRAKING_REQUEST,
        "emergency_braking_request",
        intervention_item.receipt_monotonic_s,
        lambda p: p["acceleration_mps2"] <= config.outcome_contract.braking_acceleration_max_mps2,
    )
    if brake is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required event emergency_braking_request not observed.", {**details, "failed_event": "emergency_braking_request"})
    _, brake_item = brake
    gate = first(ObservationKind.GATE_COMMAND, "normal_path_gate_command", brake_item.receipt_monotonic_s, lambda p: p["path"] == "nominal" and p["acceleration_mps2"] < 0.0)
    if gate is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required normal-path negative gate command not observed.", {**details, "failed_event": "normal_path_gate_command"})
    _, gate_item = gate
    initial_rel = next(((i,o) for i,o in by_kind.get(ObservationKind.RELATIVE_STATE, []) if target_item.receipt_monotonic_s <= o.receipt_monotonic_s < warning_item.receipt_monotonic_s and o.payload["closing_speed_mps"] > 0.0), None)
    if initial_rel:
        details["initial_ttc_s"] = initial_rel[1].payload["gap_m"] / initial_rel[1].payload["closing_speed_mps"]
    post = []
    for i, o in by_kind.get(ObservationKind.FOOTPRINT_STATE, []):
        if o.receipt_monotonic_s <= gate_item.receipt_monotonic_s:
            continue
        if o.payload["sample_skew_s"] > config.outcome_contract.pose_pair_max_age_s:
            continue
        relation = footprint_relation(
            Pose2D(o.payload["ego_x"], o.payload["ego_y"], o.payload["ego_yaw_rad"]),
            config.ego_footprint,
            Pose2D(o.payload["target_x"], o.payload["target_y"], o.payload["target_yaw_rad"]),
            config.geometry,
        )
        if relation.overlap is not o.payload["overlap"] or not math.isclose(
            relation.separation_m, o.payload["separation_m"], rel_tol=0.0, abs_tol=1e-6
        ):
            events.append(_reference("invalid_footprint_relation", i, o))
            return _result(Outcome.FAIL_SCENARIO, events, "Recorded footprint relation does not replay from preserved map poses.", {**details, "failed_event": "footprint_integrity"})
        post.append((i, o, relation))
    if not post:
        return _result(Outcome.FAIL_SCENARIO, events, "Required post-braking map-pose footprint evidence not observed.", {**details, "failed_event": "footprint_outcome"})
    overlap = next(((i, o, r) for i, o, r in post if r.overlap), None)
    if overlap is not None:
        events.append(_reference("footprint_overlap", overlap[0], overlap[1]))
        return _result(Outcome.FAIL_SCENARIO, events, "Independent map-pose footprints overlap.", {**details, "failed_event": "footprint_outcome", "minimum_footprint_separation_m": 0.0})
    min_i, min_o, min_relation = min(post, key=lambda item: item[2].separation_m)
    details["minimum_footprint_separation_m"] = min_relation.separation_m
    details["footprint_relation_method"] = "oriented_rectangle_sat_map_pose_replay"
    opening = next((
        (i, o, r) for i, o, r in post
        if o.receipt_monotonic_s > min_o.receipt_monotonic_s
        and r.separation_m >= min_relation.separation_m + 0.05
    ), None)
    if opening is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Positive footprint separation was not followed by an opening map-pose separation.", {**details, "failed_event": "footprint_outcome"})
    events.append(_reference("positive_minimum_footprint_separation", min_i, min_o))
    events.append(_reference("opening_footprint_separation", opening[0], opening[1]))
    baseline_speed = config.nominal_command_speed_mps
    speed = next(((i,o) for i,o in by_kind.get(ObservationKind.ODOMETRY, []) if o.receipt_monotonic_s > gate_item.receipt_monotonic_s and o.payload["speed_mps"] <= baseline_speed - 1.0), None)
    if speed is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Required ego speed reduction not observed.", {**details, "failed_event": "speed_reduction"})
    events.append(_reference("ego_speed_reduction", speed[0], speed[1]))
    stop_pair = None
    stop_samples = [(i, o) for i, o in by_kind.get(ObservationKind.ODOMETRY, []) if o.receipt_monotonic_s > gate_item.receipt_monotonic_s]
    for start_pos, (start_i, start_o) in enumerate(stop_samples):
        if abs(start_o.payload["speed_mps"]) > config.outcome_contract.ego_stop_speed_max_mps:
            continue
        for end_i, end_o in stop_samples[start_pos + 1:]:
            if end_o.receipt_monotonic_s - start_o.receipt_monotonic_s < config.outcome_contract.ego_stop_hold_s:
                continue
            between = [sample for _, sample in stop_samples[start_pos:] if sample.receipt_monotonic_s <= end_o.receipt_monotonic_s]
            gaps = [
                later.receipt_monotonic_s - earlier.receipt_monotonic_s
                for earlier, later in zip(between, between[1:])
            ]
            if (
                all(
                    _source_is_fresh_in_collector_ros_clock(
                        sample, config.outcome_contract.odometry_max_age_s
                    )
                    for sample in between
                )
                and all(abs(sample.payload["speed_mps"]) <= config.outcome_contract.ego_stop_speed_max_mps for sample in between)
                and all(gap <= config.outcome_contract.odometry_max_age_s for gap in gaps)
            ):
                stop_pair = ((start_i, start_o), (end_i, end_o))
                break
        if stop_pair is not None:
            break
    if stop_pair is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Fresh ego stop was not continuously observed for the configured hold duration.", {**details, "failed_event": "verified_ego_stop"})
    events.append(_reference("verified_ego_stop_start", stop_pair[0][0], stop_pair[0][1]))
    events.append(_reference("verified_ego_stop", stop_pair[1][0], stop_pair[1][1]))
    release = next((
        (i, o) for i, o in by_kind.get(ObservationKind.COORDINATION_STATE, [])
        if o.receipt_monotonic_s > stop_pair[1][1].receipt_monotonic_s
        and o.payload["state"] == "released_verified_stop"
    ), None)
    if release is None:
        return _result(Outcome.FAIL_SCENARIO, events, "Explicit verified-stop intervention release not observed.", {**details, "failed_event": "intervention_release"})
    _, release_item = release
    interval_graph_items = [
        (i, o) for i, o in graph_items
        if graph_item.receipt_monotonic_s <= o.receipt_monotonic_s
        <= release_item.receipt_monotonic_s
    ]
    graph_contamination = next(
        ((i, o) for i, o in interval_graph_items if not expected_graph(o)),
        None,
    )
    if graph_contamination is not None:
        events.append(_reference(
            "invalid_runtime_graph_after_intervention",
            graph_contamination[0],
            graph_contamination[1],
        ))
        return _result(
            Outcome.FAIL_SCENARIO,
            events,
            "Runtime publisher isolation was lost before verified-stop release.",
            {**details, "failed_event": "runtime_graph_isolation"},
        )
    graph_times = [item.receipt_monotonic_s for _, item in interval_graph_items]
    maximum_graph_gap = config.outcome_contract.runtime_graph_max_gap_s
    graph_gaps = [later - earlier for earlier, later in zip(graph_times, graph_times[1:])]
    if (
        not graph_times
        or intervention_item.receipt_monotonic_s - graph_times[0] > maximum_graph_gap
        or any(gap > maximum_graph_gap for gap in graph_gaps)
        or release_item.receipt_monotonic_s - graph_times[-1] > maximum_graph_gap
    ):
        return _result(
            Outcome.FAIL_SCENARIO,
            events,
            "Runtime graph coverage is not fresh and continuous through verified-stop release.",
            {**details, "failed_event": "runtime_graph_isolation"},
        )
    last_intervention = next((
        (i, o) for i, o in reversed(by_kind.get(ObservationKind.AEB_INTERVENTION, []))
        if o.receipt_monotonic_s <= release_item.receipt_monotonic_s
        and o.payload["message"] == "[AEB]: Emergency Brake"
    ), None)
    if last_intervention is None:
        return _result(Outcome.FAIL_SCENARIO, events, "No exact native intervention diagnostic precedes release.", {**details, "failed_event": "diagnostic_release_independence"})
    diagnostic_to_release_s = release_item.receipt_monotonic_s - last_intervention[1].receipt_monotonic_s
    latched_beyond_diagnostic = None
    if diagnostic_to_release_s <= config.outcome_contract.diagnostic_expiry_guard_s:
        details["diagnostic_release_relation"] = "release_while_native_diagnostic_retained"
    else:
        latched_beyond_diagnostic = next((
            (i, o) for i, o in by_kind.get(ObservationKind.COORDINATION_STATE, [])
            if o.payload["state"] == "braking_latched"
            and o.receipt_monotonic_s >= last_intervention[1].receipt_monotonic_s + config.outcome_contract.diagnostic_expiry_guard_s
            and o.receipt_monotonic_s < release_item.receipt_monotonic_s
        ), None)
        if latched_beyond_diagnostic is None:
            return _result(Outcome.FAIL_SCENARIO, events, "Braking latch was not observed beyond the diagnostic-expiry guard before held-stop release.", {**details, "failed_event": "diagnostic_release_independence"})
        details["diagnostic_release_relation"] = "release_after_native_diagnostic_expiry"
    details["diagnostic_to_release_s"] = diagnostic_to_release_s
    release_footprint = next((
        (i, o, r) for i, o, r in reversed(post)
        if abs(o.receipt_monotonic_s - release_item.receipt_monotonic_s) <= config.outcome_contract.pose_pair_max_age_s
    ), None)
    if release_footprint is None:
        return _result(Outcome.FAIL_SCENARIO, events, "No fresh independent footprint relation covers braking release.", {**details, "failed_event": "release_footprint"})
    events.append(_reference("last_native_intervention_diagnostic", last_intervention[0], last_intervention[1]))
    if latched_beyond_diagnostic is not None:
        events.append(_reference("braking_latched_beyond_diagnostic_expiry", latched_beyond_diagnostic[0], latched_beyond_diagnostic[1]))
    events.append(_reference("release_footprint_separation", release_footprint[0], release_footprint[1]))
    events.append(_reference("verified_stop_release", release[0], release[1]))
    details["release_footprint_separation_m"] = release_footprint[2].separation_m
    return _result(Outcome.PASS_OBSERVED_CHAIN, events, "Observed nominal 009B warning-to-braking-to-verified-stop-release noncollision chain.", details)
