"""Pure evaluation of the 009C collector's observed event chain.

Only collector monotonic receipt times establish freshness and order.  Source
stamps and optional host UTC strings are retained as provenance and are never
compared with each other or with receipt time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .scenario_contract import BASELINE_REQUIRED_INPUTS, Outcome, ScenarioConfig


class ObservationKind(str, Enum):
    DIAGNOSTIC = "diagnostic"
    AEB_INTERVENTION = "aeb_intervention"
    AUTONOMOUS_AVAILABILITY = "autonomous_availability"
    MRM_STATE = "mrm_state"
    EMERGENCY_OPERATOR_STATUS = "emergency_operator_status"
    NOMINAL_COMMAND = "nominal_command"
    EMERGENCY_COMMAND = "emergency_command"
    GATE_EMERGENCY_STATUS = "gate_emergency_status"
    GATE_COMMAND = "gate_command"
    ODOMETRY = "odometry"
    TARGET_PUBLICATION = "target_publication"
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
        ObservationKind.MRM_STATE,
        ObservationKind.EMERGENCY_OPERATOR_STATUS,
        ObservationKind.NOMINAL_COMMAND,
        ObservationKind.GATE_COMMAND,
        ObservationKind.ODOMETRY,
    ), strict=True))
)

_SCHEMAS: Mapping[ObservationKind, Mapping[str, str]] = {
    ObservationKind.DIAGNOSTIC: {"node": "str", "task": "str", "level": "str"},
    ObservationKind.AEB_INTERVENTION: {
        "message": "str",
        "rss_distance_m": "number",
        "object_distance_m": "number",
        "object_speed_mps": "number",
    },
    ObservationKind.AUTONOMOUS_AVAILABILITY: {"available": "bool"},
    ObservationKind.MRM_STATE: {"state": "str", "behavior": "str"},
    ObservationKind.EMERGENCY_OPERATOR_STATUS: {"state": "str"},
    ObservationKind.NOMINAL_COMMAND: {"speed_mps": "number", "acceleration_mps2": "number"},
    ObservationKind.EMERGENCY_COMMAND: {"speed_mps": "number", "acceleration_mps2": "number"},
    ObservationKind.GATE_EMERGENCY_STATUS: {"emergency": "bool"},
    ObservationKind.GATE_COMMAND: {"path": "str", "acceleration_mps2": "number"},
    ObservationKind.ODOMETRY: {"speed_mps": "number", "acceleration_mps2": "number"},
    ObservationKind.TARGET_PUBLICATION: {
        "identity": "str", "frame": "str", "x": "number", "y": "number", "yaw_rad": "number"
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


def _result(outcome: Outcome, reasons: Iterable[str], accepted: Iterable[EventReference] = (), **details: object) -> EvaluationResult:
    accepted_tuple = tuple(sorted(accepted, key=lambda event: (event.receipt_monotonic_s, event.observation_index)))
    return EvaluationResult(outcome, accepted_tuple, tuple(reasons) + (_CLOCK_BOUNDARY,), {
        "clock_order_domain": "collector_monotonic_within_one_collector",
        "source_stamp_comparison": "forbidden",
        "accepted_receipt_times_s": tuple(event.receipt_monotonic_s for event in accepted_tuple),
        "clock_provenance": tuple((event.source_stamp, event.host_utc) for event in accepted_tuple),
        **details,
    }, _token=_RESULT_TOKEN)


def _baseline_good(latest: Mapping[ObservationKind, tuple[int, Observation]], config: ScenarioConfig) -> bool:
    b = config.baseline
    p = {kind: latest[kind][1].payload for kind in REQUIRED_INPUT_KIND.values()}
    diagnostic = p[ObservationKind.DIAGNOSTIC]
    return (
        diagnostic["node"] == b.diagnostic_node and diagnostic["task"] == b.diagnostic_task
        and diagnostic["level"] == "OK"
        and p[ObservationKind.AUTONOMOUS_AVAILABILITY]["available"] is True
        and p[ObservationKind.MRM_STATE]["state"] == "NORMAL"
        and p[ObservationKind.MRM_STATE]["behavior"] == "NONE"
        and p[ObservationKind.EMERGENCY_OPERATOR_STATUS]["state"] == "AVAILABLE"
        and p[ObservationKind.NOMINAL_COMMAND]["speed_mps"] > 0.0
        and p[ObservationKind.NOMINAL_COMMAND]["acceleration_mps2"] > 0.0
        and p[ObservationKind.GATE_COMMAND]["path"] == "nominal"
        and p[ObservationKind.GATE_COMMAND]["acceleration_mps2"] > 0.0
        and p[ObservationKind.ODOMETRY]["speed_mps"] > b.ego_speed_min_mps
    )


def _baseline_observation_good(item: Observation, config: ScenarioConfig) -> bool:
    """Check one required observation without allowing a same-time duplicate to hide it."""
    payload = item.payload
    if item.kind is ObservationKind.DIAGNOSTIC:
        return (
            payload["node"] == config.baseline.diagnostic_node
            and payload["task"] == config.baseline.diagnostic_task
            and payload["level"] == "OK"
        )
    if item.kind is ObservationKind.AUTONOMOUS_AVAILABILITY:
        return payload["available"] is True
    if item.kind is ObservationKind.MRM_STATE:
        return payload["state"] == "NORMAL" and payload["behavior"] == "NONE"
    if item.kind is ObservationKind.EMERGENCY_OPERATOR_STATUS:
        return payload["state"] == "AVAILABLE"
    if item.kind is ObservationKind.NOMINAL_COMMAND:
        return payload["speed_mps"] > 0.0 and payload["acceleration_mps2"] > 0.0
    if item.kind is ObservationKind.GATE_COMMAND:
        return payload["path"] == "nominal" and payload["acceleration_mps2"] > 0.0
    if item.kind is ObservationKind.ODOMETRY:
        return payload["speed_mps"] > config.baseline.ego_speed_min_mps
    return False


def _latest_instrument_statuses(
    ordered: Iterable[tuple[int, Observation]],
    through_time: float,
) -> dict[str, tuple[int, Observation]]:
    """Select by receipt time, treating an equal-time false/true tie as false."""
    latest: dict[str, tuple[int, Observation]] = {}
    for pair in ordered:
        item = pair[1]
        if item.receipt_monotonic_s > through_time:
            break
        if item.kind is not ObservationKind.INSTRUMENT_STATUS:
            continue
        topic = item.payload["topic"]
        previous = latest.get(topic)
        if previous is None or item.receipt_monotonic_s > previous[1].receipt_monotonic_s:
            latest[topic] = pair
        elif (
            item.receipt_monotonic_s == previous[1].receipt_monotonic_s
            and item.payload["available"] is False
            and previous[1].payload["available"] is True
        ):
            latest[topic] = pair
    return latest


def evaluate_scenario(config: ScenarioConfig, observations: Iterable[Observation]) -> EvaluationResult:
    """Evaluate observations without accepting any caller-supplied verdict."""
    if not isinstance(config, ScenarioConfig):
        raise TypeError("config must be ScenarioConfig")
    items = tuple(observations)
    if not all(isinstance(item, Observation) for item in items):
        raise TypeError("observations must contain only Observation values")
    if not items:
        return _result(Outcome.INCONCLUSIVE_INSTRUMENTATION, ("No observations were collected.",))
    ordered = sorted(enumerate(items), key=lambda pair: (pair[1].receipt_monotonic_s, pair[0]))
    abort = next(((index, item) for index, item in ordered if item.kind is ObservationKind.OPERATOR_ABORT), None)
    if abort:
        return _result(Outcome.ABORTED, (f"Operator abort: {abort[1].payload['reason']}.",), (_reference("operator_abort", *abort),))
    present = {item.kind for _, item in ordered}
    missing = [topic for topic, kind in REQUIRED_INPUT_KIND.items() if kind not in present]
    if missing:
        return _result(Outcome.INCONCLUSIVE_INSTRUMENTATION, (
            f"Required instruments have absent observations: {missing}.",
        ), unavailable_inputs=(), missing_inputs=tuple(missing))
    required_kinds = set(REQUIRED_INPUT_KIND.values())
    latest: dict[ObservationKind, tuple[int, Observation]] = {}
    good_since: float | None = None
    candidate_start_support: dict[ObservationKind, tuple[int, Observation]] | None = None
    baseline_at: tuple[int, Observation] | None = None
    baseline_start_support: dict[ObservationKind, tuple[int, Observation]] | None = None
    baseline_final_support: dict[ObservationKind, tuple[int, Observation]] | None = None
    groups: dict[float, list[tuple[int, Observation]]] = {}
    for pair in ordered:
        groups.setdefault(pair[1].receipt_monotonic_s, []).append(pair)
    previous_required_time: float | None = None
    for receipt_time, group in groups.items():
        required_group = [pair for pair in group if pair[1].kind in required_kinds]
        if not required_group:
            continue
        if good_since is not None and any(
            receipt_time - value[1].receipt_monotonic_s > config.baseline.required_input_max_age_s
            for value in latest.values()
        ):
            good_since = None
            candidate_start_support = None
        for pair in required_group:
            latest[pair[1].kind] = pair
        complete = len(latest) == len(required_kinds)
        fresh = complete and all(
            receipt_time - value[1].receipt_monotonic_s <= config.baseline.required_input_max_age_s
            for value in latest.values()
        )
        group_consistent = all(_baseline_observation_good(pair[1], config) for pair in required_group)
        continuity_gap = (
            previous_required_time is not None
            and receipt_time - previous_required_time > config.baseline.required_input_max_age_s
        )
        previous_required_time = receipt_time
        if not fresh or not group_consistent or not _baseline_good(latest, config):
            good_since = None
            candidate_start_support = None
            continue
        if good_since is None or continuity_gap:
            good_since = receipt_time
            candidate_start_support = dict(latest)
        if receipt_time - good_since >= config.baseline.stable_duration_s:
            baseline_at = required_group[-1]
            baseline_start_support = candidate_start_support
            baseline_final_support = dict(latest)
            break
    if baseline_at is None:
        instrument_status_at_end = _latest_instrument_statuses(
            ordered, ordered[-1][1].receipt_monotonic_s
        )
        unavailable = sorted(
            topic for topic, (_, item) in instrument_status_at_end.items()
            if item.payload["available"] is False
        )
        if unavailable:
            return _result(Outcome.INCONCLUSIVE_INSTRUMENTATION, (
                f"Required instruments unavailable before an evaluable baseline: {unavailable}.",
            ), unavailable_inputs=tuple(unavailable), missing_inputs=())
        return _result(Outcome.INCONCLUSIVE_PRECONDITION, ("Complete instrumentation was present, but the exact fresh baseline never remained stable for the configured duration.",))
    instrument_status_at_baseline = _latest_instrument_statuses(
        ordered, baseline_at[1].receipt_monotonic_s
    )
    unavailable_before_baseline = sorted(
        topic for topic, (_, item) in instrument_status_at_baseline.items()
        if item.payload["available"] is False
    )
    if unavailable_before_baseline:
        return _result(Outcome.INCONCLUSIVE_INSTRUMENTATION, (
            f"Required instruments unavailable before the stable baseline: {unavailable_before_baseline}.",
        ), unavailable_inputs=tuple(unavailable_before_baseline), missing_inputs=())
    assert baseline_start_support is not None and baseline_final_support is not None and good_since is not None
    accepted = [
        _reference(f"baseline_candidate_start:{topic}", *baseline_start_support[kind])
        for topic, kind in REQUIRED_INPUT_KIND.items()
    ]
    accepted.extend(
        _reference(f"baseline_final_support:{topic}", *baseline_final_support[kind])
        for topic, kind in REQUIRED_INPUT_KIND.items()
    )
    target_events = [(index, item) for index, item in ordered if item.kind is ObservationKind.TARGET_PUBLICATION]
    if any(item.receipt_monotonic_s <= baseline_at[1].receipt_monotonic_s for _, item in target_events):
        return _result(Outcome.FAIL_SCENARIO, ("Target injection occurred before the stable baseline was established.",), accepted, failed_event="target_injection", baseline_stable_at_s=baseline_at[1].receipt_monotonic_s)
    injection = target_events[0] if target_events else None
    if injection is None:
        return _result(Outcome.FAIL_SCENARIO, ("No map target injection occurred after stable baseline.",), accepted, failed_event="target_injection", baseline_stable_at_s=baseline_at[1].receipt_monotonic_s)
    accepted.append(_reference("target_injection", *injection))
    instrument_status_at_injection = _latest_instrument_statuses(
        ordered, injection[1].receipt_monotonic_s
    )
    unavailable_after_baseline = [
        pair for pair in instrument_status_at_injection.values()
        if pair[1].receipt_monotonic_s > baseline_at[1].receipt_monotonic_s
        and pair[1].payload["available"] is False
    ]
    if unavailable_after_baseline:
        unavailable_pair = min(
            unavailable_after_baseline,
            key=lambda pair: (pair[1].receipt_monotonic_s, pair[0]),
        )
        topic = unavailable_pair[1].payload["topic"]
        accepted.append(_reference(f"instrument_unavailable_after_baseline:{topic}", *unavailable_pair))
        return _result(
            Outcome.FAIL_SCENARIO,
            (f"Required instrument {topic} became unavailable after stable baseline and before or at target injection.",),
            accepted,
            failed_event="instrument_unavailable_after_baseline",
            baseline_stable_at_s=baseline_at[1].receipt_monotonic_s,
        )
    late_unavailable = next((
        pair for pair in ordered
        if pair[1].kind is ObservationKind.INSTRUMENT_STATUS
        and pair[1].payload["available"] is False
        and pair[1].receipt_monotonic_s > injection[1].receipt_monotonic_s
    ), None)
    if late_unavailable is not None:
        topic = late_unavailable[1].payload["topic"]
        accepted.append(_reference(f"instrument_unavailable_after_injection:{topic}", *late_unavailable))
        return _result(
            Outcome.FAIL_SCENARIO,
            (f"Required instrument {topic} became unavailable after stable baseline and target injection.",),
            accepted,
            failed_event="instrument_unavailable_after_injection",
            baseline_stable_at_s=baseline_at[1].receipt_monotonic_s,
        )
    target_signature = tuple(injection[1].payload[key] for key in ("identity", "frame", "x", "y", "yaw_rad"))
    if injection[1].payload["frame"] != "map" or any(
        tuple(item.payload[key] for key in ("identity", "frame", "x", "y", "yaw_rad")) != target_signature
        for _, item in target_events[1:]
    ):
        return _result(Outcome.FAIL_SCENARIO, ("Every target publication must preserve one identical identity and map pose.",), accepted, failed_event="stationary_map_target", baseline_stable_at_s=baseline_at[1].receipt_monotonic_s)

    stage_specs = (
        (
            "native_aeb_intervention",
            ObservationKind.AEB_INTERVENTION,
            lambda p: p["message"] == "[AEB]: Emergency Brake",
            lambda p: p["object_distance_m"] <= p["rss_distance_m"],
            lambda p: False,
        ),
        (
            "autonomous_unavailable",
            ObservationKind.AUTONOMOUS_AVAILABILITY,
            lambda p: True,
            lambda p: p["available"] is False,
            lambda p: p["available"] is True,
        ),
        (
            "mrm_emergency_stop",
            ObservationKind.MRM_STATE,
            lambda p: True,
            lambda p: p["state"] == "MRM_OPERATING" and p["behavior"] == "EMERGENCY_STOP",
            lambda p: p["state"] == "NORMAL" and p["behavior"] == "NONE",
        ),
        (
            "emergency_operator_operating",
            ObservationKind.EMERGENCY_OPERATOR_STATUS,
            lambda p: True,
            lambda p: p["state"] == "OPERATING",
            lambda p: p["state"] == "AVAILABLE",
        ),
        (
            "emergency_command_negative",
            ObservationKind.EMERGENCY_COMMAND,
            lambda p: True,
            lambda p: p["acceleration_mps2"] < 0.0,
            lambda p: p["acceleration_mps2"] >= 0.0,
        ),
        (
            "gate_selection_negative",
            ObservationKind.GATE_COMMAND,
            lambda p: True,
            lambda p: p["path"] == "emergency" and p["acceleration_mps2"] < 0.0,
            lambda p: p["acceleration_mps2"] >= 0.0,
        ),
    )
    stage_by_kind = {kind: position for position, (_, kind, _, _, _) in enumerate(stage_specs)}
    for pair in ordered:
        item = pair[1]
        if not (
            baseline_at[1].receipt_monotonic_s < item.receipt_monotonic_s
            <= injection[1].receipt_monotonic_s
        ):
            continue
        position = stage_by_kind.get(item.kind)
        if position is None:
            continue
        label, _, relevant, transition, steady_before = stage_specs[position]
        if not relevant(item.payload) or steady_before(item.payload):
            continue
        state = "transition" if transition(item.payload) else "contradiction"
        accepted.append(_reference(f"pre_injection_nonsteady:{label}", *pair))
        return _result(
            Outcome.FAIL_SCENARIO,
            (f"A {state} for stage {label} occurred after stable baseline and before or at target injection.",),
            accepted,
            failed_event="pre_injection_chain_state",
            baseline_stable_at_s=baseline_at[1].receipt_monotonic_s,
        )
    matched: list[tuple[int, Observation]] = []
    prior_stage_time = injection[1].receipt_monotonic_s
    failure_reason: str | None = None
    failed_event_override: str | None = None
    for pair in ordered:
        index, item = pair
        if item.receipt_monotonic_s <= injection[1].receipt_monotonic_s:
            continue
        position = stage_by_kind.get(item.kind)
        if position is None:
            continue
        label, _, relevant, transition, steady_before = stage_specs[position]
        if not relevant(item.payload):
            continue
        expected = len(matched)
        state = (
            _StageObservation.TRANSITION if transition(item.payload)
            else _StageObservation.STEADY_BEFORE if steady_before(item.payload)
            else _StageObservation.CONTRADICTION
        )
        if position > expected:
            if state is _StageObservation.TRANSITION:
                failure_reason = f"Later-stage event {label} was observed before {stage_specs[expected][0]}."
                break
            if state is _StageObservation.CONTRADICTION:
                failure_reason = f"Contradictory later-stage observation {label} was observed before {stage_specs[expected][0]}."
                break
            continue
        if position < expected:
            if state is not _StageObservation.TRANSITION:
                failure_reason = f"Contradictory observation invalidated completed stage {label}."
                failed_event_override = "completed_stage_regression"
                accepted.append(_reference(f"completed_stage_regression:{label}", *pair))
                break
            continue
        if state is _StageObservation.STEADY_BEFORE:
            continue
        if state is _StageObservation.CONTRADICTION:
            failure_reason = f"Contradictory observation was seen for expected stage {label}."
            break
        if item.receipt_monotonic_s <= prior_stage_time:
            failure_reason = f"Event {label} did not occur strictly after the prior stage."
            break
        matched.append(pair)
        prior_stage_time = item.receipt_monotonic_s
        accepted.append(_reference(label, *pair))
    if failure_reason is not None or len(matched) != len(stage_specs):
        failed_label = stage_specs[min(len(matched), len(stage_specs) - 1)][0]
        return _result(
            Outcome.FAIL_SCENARIO,
            (failure_reason or f"Required event {failed_label} was missing after injection.",),
            accepted,
            failed_event=failed_event_override or failed_label,
            baseline_stable_at_s=baseline_at[1].receipt_monotonic_s,
        )

    emergency = matched[4]
    gate = matched[5]
    gate_status_candidates = [
        pair for pair in ordered
        if pair[1].kind is ObservationKind.GATE_EMERGENCY_STATUS
        and injection[1].receipt_monotonic_s < pair[1].receipt_monotonic_s
        and pair[1].receipt_monotonic_s < gate[1].receipt_monotonic_s
        and gate[1].receipt_monotonic_s - pair[1].receipt_monotonic_s
        <= config.baseline.required_input_max_age_s
    ]
    gate_status = gate_status_candidates[-1] if gate_status_candidates else None
    if (
        gate_status is None
        or gate_status[1].payload["emergency"] is not True
        or gate[1].payload["path"] != "emergency"
    ):
        return _result(
            Outcome.FAIL_SCENARIO,
            ("The accepted negative gate command lacked a fresh preceding gate emergency-status assertion.",),
            accepted,
            failed_event="gate_emergency_status",
            baseline_stable_at_s=baseline_at[1].receipt_monotonic_s,
        )
    accepted.append(_reference("gate_emergency_status_asserted", *gate_status))
    nominal_candidates = [
        pair for pair in ordered
        if pair[1].kind is ObservationKind.NOMINAL_COMMAND
        and pair[1].receipt_monotonic_s <= gate[1].receipt_monotonic_s
    ]
    nominal = nominal_candidates[-1] if nominal_candidates else None
    contradictory_nominal = next((
        pair for pair in nominal_candidates
        if emergency[1].receipt_monotonic_s <= pair[1].receipt_monotonic_s <= gate[1].receipt_monotonic_s
        and (pair[1].payload["speed_mps"] <= 0.0 or pair[1].payload["acceleration_mps2"] <= 0.0)
    ), None)
    nominal_is_valid = (
        nominal is not None
        and gate[1].receipt_monotonic_s - nominal[1].receipt_monotonic_s <= config.baseline.required_input_max_age_s
        and nominal[1].payload["speed_mps"] > 0.0
        and nominal[1].payload["acceleration_mps2"] > 0.0
        and contradictory_nominal is None
    )
    if not nominal_is_valid:
        return _result(Outcome.FAIL_SCENARIO, ("The latest nominal command at the gate was stale/nonpositive, or the emergency-to-gate interval contained a contradictory nominal command.",), accepted, failed_event="nominal_gate_correlation", baseline_stable_at_s=baseline_at[1].receipt_monotonic_s)
    assert nominal is not None
    accepted.append(_reference("latest_fresh_positive_nominal_at_gate", *nominal))
    pre_speed_candidates = [
        pair for pair in ordered
        if pair[1].kind is ObservationKind.ODOMETRY
        and injection[1].receipt_monotonic_s < pair[1].receipt_monotonic_s
        and pair[1].receipt_monotonic_s < gate[1].receipt_monotonic_s
        and gate[1].receipt_monotonic_s - pair[1].receipt_monotonic_s
        <= config.baseline.required_input_max_age_s
    ]
    pre_selection = pre_speed_candidates[-1] if pre_speed_candidates else None
    pre_speed = pre_selection[1].payload["speed_mps"] if pre_selection else None
    post_selection = [
        pair for pair in ordered
        if pair[1].kind is ObservationKind.ODOMETRY
        and pair[1].receipt_monotonic_s > gate[1].receipt_monotonic_s
    ]
    negative_response = next((pair for pair in post_selection if pair[1].payload["acceleration_mps2"] < 0.0), None)
    lower_speed_response = next((
        pair
        for pair in post_selection
        if pre_speed is not None
        and pair[1].payload["speed_mps"] < pre_speed
        and negative_response is not None
        and (
            pair == negative_response
            or pair[1].receipt_monotonic_s > negative_response[1].receipt_monotonic_s
        )
    ), None)
    correlation_details = {
        "emergency_acceleration_mps2": emergency[1].payload["acceleration_mps2"],
        "gate_acceleration_mps2": gate[1].payload["acceleration_mps2"],
    }
    if pre_selection is None or negative_response is None or lower_speed_response is None:
        return _result(Outcome.FAIL_SCENARIO, ("No strictly pre-selection speed, post-selection negative acceleration, and later lower-speed response were all observed.",), accepted, failed_event="directional_response", baseline_stable_at_s=baseline_at[1].receipt_monotonic_s, pre_selection_speed_mps=pre_speed, **correlation_details)
    accepted.append(_reference("pre_selection_odometry", *pre_selection))
    if negative_response == lower_speed_response:
        accepted.append(_reference("negative_acceleration_and_lower_speed_response", *negative_response))
    else:
        accepted.append(_reference("negative_acceleration_response", *negative_response))
        accepted.append(_reference("lower_speed_response", *lower_speed_response))
    return _result(Outcome.PASS_OBSERVED_CHAIN, ("The partial 009C native-AEB-intervention to MRM/gate observed chain was accepted; no OperateMrm service invocation is claimed.", "The native AEB ERROR diagnostic is an intentional intervention signal, not evidence of a component fault.", "This is not nominal AEBS evidence: warning, override evaluation, direct AEBS braking request, and collision outcome are outside this fixture.", "Directional simulator/test-double response is not physical braking evidence."), accepted, baseline_interval_start_s=good_since, baseline_stable_at_s=baseline_at[1].receipt_monotonic_s, target_identity=injection[1].payload["identity"], target_map_pose=target_signature[2:], pre_selection_speed_mps=pre_speed, response_speed_mps=lower_speed_response[1].payload["speed_mps"], **correlation_details)
