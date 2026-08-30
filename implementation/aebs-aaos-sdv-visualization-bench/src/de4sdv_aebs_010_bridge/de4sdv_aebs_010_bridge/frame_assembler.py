"""Pure, dependency-free core for the DE4SDV AEBS 010 visualization bridge.

The frame assembler, validation rules, and staleness watchdog live here so
they can be tested without ROS 2, network, or protobuf dependencies. The ROS
node layer (``source_adapter``, ``frame_server``) only wires this core to
live inputs.

Field provenance rule (REQ-AEBS-S2-003): the coordinator's combined
risk-assessment ``object_distance_m`` is DE4SDV-derived and is never emitted
as a native-Autoware field. Native fields are populated only from the pinned
native AEB topics.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

SCHEMA_MAJOR = 1
SCHEMA_MINOR = 1

# Frame schema fields. The wire serialization (protobuf) encodes exactly
# these; adding a field requires a schema-major bump or a documented minor.
FRAME_FIELDS = (
    "schema_major",
    "schema_minor",
    "sequence",
    "frame_timestamp_ns",
    "bridge_receipt_timestamp_ns",
    "source_identity",
    "rss_distance",
    "target_range",
    "target_bearing",
    "target_points",
    "ego_speed",
    "native_intervention",
    "de4sdv_warning_request",
    "de4sdv_braking_request",
    "de4sdv_lifecycle_state",
)

FIELD_VALUE_KEYS = ("source_kind", "source_timestamp_ns", "units", "coordinate_frame", "value")

SOURCE_KINDS = ("nativeAutowareAEB", "de4sdvAebsCoordinator", "displayDerived")

SUPPORTED_SOURCE_TOPICS = (
    "/control/autonomous_emergency_braking/debug/rss_distance",
    "/control/autonomous_emergency_braking/debug/obstacle_pointcloud",
    "/localization/kinematic_state",
    "/diagnostics",
    "/de4sdv/aebs_009b/warning_request",
    "/de4sdv/aebs_009b/emergency_braking_request",
    "/de4sdv/aebs_009b/coordination_state",
)

# Controlled dispositions (aligned with the model's VisualizationHealthKind).
HEALTH_UNAVAILABLE = "unavailable"
HEALTH_INVALID = "invalid"
HEALTH_STALE = "stale"
HEALTH_RESTORED = "restored"
HEALTH_HEALTHY = "healthy"


class FrameError(ValueError):
    """Raised when a frame cannot be assembled or validated."""


def _field_value(
    value: Any,
    source_kind: str,
    source_timestamp_ns: int,
    units: str,
    coordinate_frame: str,
) -> dict[str, Any]:
    if source_kind not in SOURCE_KINDS:
        raise FrameError(f"unknown source kind: {source_kind!r}")
    if type(source_timestamp_ns) is not int or source_timestamp_ns <= 0:
        raise FrameError("source timestamp must be a positive integer")
    return {
        "source_kind": source_kind,
        "source_timestamp_ns": source_timestamp_ns,
        "units": units,
        "coordinate_frame": coordinate_frame,
        "value": value,
    }


@dataclass
class SourceObservation:
    """One accepted source-side observation feeding frame assembly."""

    topic: str
    payload: Mapping[str, Any]
    receipt_timestamp_ns: int

    def __post_init__(self) -> None:
        if self.topic not in SUPPORTED_SOURCE_TOPICS:
            raise FrameError(f"unsupported source topic: {self.topic!r}")
        if type(self.receipt_timestamp_ns) is not int or self.receipt_timestamp_ns <= 0:
            raise FrameError("receipt timestamp must be a positive integer")


@dataclass
class FrameAssemblerState:
    """Mutable assembly state between frames."""

    last_sequence: int = 0
    last_frame_timestamp_ns: int = 0
    rss_distance: dict[str, Any] | None = None
    target_range: dict[str, Any] | None = None
    target_bearing: dict[str, Any] | None = None
    target_points: list[tuple[float, float]] | None = None
    ego_speed: dict[str, Any] | None = None
    native_intervention: dict[str, Any] | None = None
    de4sdv_warning_request: dict[str, Any] | None = None
    de4sdv_braking_request: dict[str, Any] | None = None
    de4sdv_lifecycle_state: dict[str, Any] | None = None


class FrameAssembler:
    """Assembles a versioned visualization frame from source observations.

    Provenance is decided per topic here, so downstream consumers can trust
    ``source_kind`` without re-deriving it:

    - ``rss_distance``: native Autoware AEB debug metric.
    - ``target_range``/``target_bearing``: DE4SDV display projection derived
      from the native AEB filtered obstacle point cloud. The point cloud is
      native, the projected value is display-derived; recorded honestly as
      ``displayDerived`` with the native topic in ``coordinate_frame``-adjacent
      provenance metadata kept out of the frame payload.
    - ``native_intervention``: exact native AEB diagnostic tuple.
    - warning/braking/lifecycle: DE4SDV coordinator outputs.
    """

    def __init__(self, source_identity: str) -> None:
        if not source_identity:
            raise FrameError("source_identity must be non-empty")
        self._source_identity = source_identity
        self.state = FrameAssemblerState()

    # -- ingestion ---------------------------------------------------------

    def observe_rss_distance(self, observation: SourceObservation, value: Any) -> None:
        # The native AEB node publishes a signed RSS stopping distance: during
        # an active intervention the required stopping distance can legitimately
        # exceed the object distance and the debug value stays positive, but the
        # formula (ego_stopping + obj_braking + margin) is signed, so clamp
        # physically meaningless negatives to zero while preserving the value's
        # native provenance. NaN/inf remain hard rejections (fail closed).
        numeric = self._require_finite_number(value, "rss_distance")
        self.state.rss_distance = _field_value(
            max(numeric, 0.0), "nativeAutowareAEB",
            self._require_positive_int(observation.payload.get("source_timestamp_ns"), "source_timestamp_ns"),
            "m", "base_link",
        )

    def observe_obstacle_projection(self, observation: SourceObservation, range_m: Any, bearing_rad: Any) -> None:
        # Native cloud in, projected values out: display-derived provenance.
        numeric_range = self._require_finite_number(range_m, "target_range")
        numeric_bearing = self._require_finite_number(bearing_rad, "target_bearing")
        if numeric_range < 0.0:
            raise FrameError("target_range must be non-negative")
        stamp = self._require_positive_int(observation.payload.get("source_timestamp_ns"), "source_timestamp_ns")
        self.state.target_range = _field_value(
            numeric_range, "displayDerived", stamp, "m", "map",
        )
        self.state.target_bearing = _field_value(
            numeric_bearing, "displayDerived", stamp, "rad", "map",
        )

    def observe_ego_speed(self, observation: SourceObservation, value: Any) -> None:
        # Bench kinematic-state derived ego speed; display-presentational only.
        numeric = self._require_finite_number(value, "ego_speed")
        self.state.ego_speed = _field_value(
            max(numeric, 0.0), "displayDerived",
            self._require_positive_int(observation.payload.get("source_timestamp_ns"), "source_timestamp_ns"),
            "m/s", "base_link",
        )

    def observe_target_points(self, observation: SourceObservation, points: Any) -> None:
        # Downsampled filtered-obstacle cluster projection (bounded 24 points).
        if not isinstance(points, list) or len(points) > 24:
            raise FrameError("target_points must be a list of at most 24 points")
        clean: list[tuple[float, float]] = []
        for point in points:
            if not isinstance(point, (tuple, list)) or len(point) != 2:
                raise FrameError("each target point must be (forward_m, lateral_m)")
            fwd, lat = float(point[0]), float(point[1])
            if not math.isfinite(fwd) or not math.isfinite(lat):
                raise FrameError("target point must be finite")
            clean.append((fwd, lat))
        self.state.target_points = clean

    def observe_native_intervention(self, observation: SourceObservation, diagnostic_name: str, level: str, message: str) -> None:
        expected = (
            diagnostic_name == "autonomous_emergency_braking: aeb_emergency_stop"
            and level == "ERROR"
            and message == "[AEB]: Emergency Brake"
        )
        self.state.native_intervention = _field_value(
            expected, "nativeAutowareAEB",
            self._require_positive_int(observation.payload.get("source_timestamp_ns"), "source_timestamp_ns"),
            "boolean", "none",
        )

    def observe_warning_request(self, observation: SourceObservation, active: Any) -> None:
        if type(active) is not bool:
            raise FrameError("warning request must be boolean")
        self.state.de4sdv_warning_request = _field_value(
            active, "de4sdvAebsCoordinator",
            self._require_positive_int(observation.payload.get("source_timestamp_ns"), "source_timestamp_ns"),
            "boolean", "none",
        )

    def observe_braking_request(self, observation: SourceObservation, active: Any) -> None:
        if type(active) is not bool:
            raise FrameError("braking request must be boolean")
        self.state.de4sdv_braking_request = _field_value(
            active, "de4sdvAebsCoordinator",
            self._require_positive_int(observation.payload.get("source_timestamp_ns"), "source_timestamp_ns"),
            "boolean", "none",
        )

    def observe_lifecycle_state(self, observation: SourceObservation, state: Any) -> None:
        if state not in ("armed", "braking_latched", "released_verified_stop"):
            raise FrameError(f"unknown lifecycle state: {state!r}")
        self.state.de4sdv_lifecycle_state = _field_value(
            state, "de4sdvAebsCoordinator",
            self._require_positive_int(observation.payload.get("source_timestamp_ns"), "source_timestamp_ns"),
            "enum", "none",
        )

    # -- assembly ----------------------------------------------------------

    def assemble(self, now_ns: int) -> dict[str, Any]:
        if type(now_ns) is not int or now_ns <= 0:
            raise FrameError("now_ns must be a positive integer")
        frame = {
            "schema_major": SCHEMA_MAJOR,
            "schema_minor": SCHEMA_MINOR,
            "sequence": self.state.last_sequence + 1,
            "frame_timestamp_ns": now_ns,
            "bridge_receipt_timestamp_ns": now_ns,
            "source_identity": self._source_identity,
        }
        for name in (
            "rss_distance", "target_range", "target_bearing",
            "ego_speed", "native_intervention", "de4sdv_warning_request",
            "de4sdv_braking_request", "de4sdv_lifecycle_state",
        ):
            frame[name] = getattr(self.state, name)
        frame["target_points"] = list(self.state.target_points or [])
        self.state.last_sequence = frame["sequence"]
        self.state.last_frame_timestamp_ns = now_ns
        return frame

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _require_finite_number(value: Any, name: str) -> float:
        if type(value) not in (int, float) or not math.isfinite(float(value)):
            raise FrameError(f"{name} must be a finite number")
        return float(value)

    @staticmethod
    def _require_positive_int(value: Any, name: str) -> int:
        if type(value) is not int or value <= 0:
            raise FrameError(f"{name} must be a positive integer")
        return value


class FrameValidator:
    """Sink-side validation: schema, finiteness, range, timestamps, sequence."""

    def __init__(self, *, max_frame_age_ns: int, stale_timeout_ns: int) -> None:
        if max_frame_age_ns <= 0 or stale_timeout_ns <= 0:
            raise FrameError("age and timeout bounds must be positive")
        self._max_frame_age_ns = max_frame_age_ns
        self._stale_timeout_ns = stale_timeout_ns

    def validate(self, frame: Mapping[str, Any], *, last_accepted_sequence: int, now_ns: int) -> tuple[bool, str]:
        """Return (accepted, reason). Never raises for invalid input."""
        for key in FRAME_FIELDS:
            if key not in frame:
                return False, f"missing field {key}"
        extra = set(frame) - set(FRAME_FIELDS)
        if extra:
            return False, f"unknown fields {sorted(extra)}"
        if frame["schema_major"] != SCHEMA_MAJOR:
            return False, f"unsupported schema major {frame['schema_major']!r}"
        sequence = frame["sequence"]
        if type(sequence) is not int or sequence <= last_accepted_sequence:
            return False, f"non-monotonic sequence {sequence!r}"
        if frame["frame_timestamp_ns"] > now_ns + self._max_frame_age_ns:
            return False, "frame timestamp in the future"
        if now_ns - frame["frame_timestamp_ns"] > self._stale_timeout_ns:
            return False, "frame timestamp older than stale timeout"
        for name in ("rss_distance", "target_range", "target_bearing"):
            value = frame.get(name)
            if value is None:
                continue
            inner = value.get("value")
            if not isinstance(inner, (int, float)) or not math.isfinite(float(inner)):
                return False, f"{name} value not finite"
            if float(inner) < 0.0:
                return False, f"{name} value negative"
        return True, "ok"


class PresentationWatchdog:
    """Fail-closed presentation disposition (REQ-AEBS-S2-006..009).

    Pure state machine mirroring the model's VisualizationPresentationMachine:
    healthy after N consecutive valid frames, stale after the no-valid-frame
    timeout, restored transient after recovery, invalid on rejection.
    """

    def __init__(
        self,
        *,
        stale_timeout_ns: int,
        restore_consecutive_frames: int,
        restored_hold_ns: int,
        now_ns: int,
        on_disposition: Callable[[str], None],
    ) -> None:
        if stale_timeout_ns <= 0 or restore_consecutive_frames <= 0 or restored_hold_ns <= 0:
            raise FrameError("watchdog bounds must be positive")
        self._stale_timeout_ns = stale_timeout_ns
        self._restore_required = restore_consecutive_frames
        self._restored_hold_ns = restored_hold_ns
        self._on_disposition = on_disposition
        self._last_valid_ns: int | None = None
        self._valid_streak = 0
        self._restored_until_ns: int | None = None
        self._disposition = HEALTH_UNAVAILABLE
        self._now_ns = now_ns

    @property
    def disposition(self) -> str:
        return self._disposition

    def mark_valid(self, now_ns: int) -> None:
        self._now_ns = now_ns
        self._last_valid_ns = now_ns
        if self._disposition == HEALTH_UNAVAILABLE:
            # First valid frames: streak counts toward becoming healthy.
            self._valid_streak += 1
            if self._valid_streak >= self._restore_required:
                self._set(HEALTH_HEALTHY)
                self._valid_streak = 0
            return
        if self._disposition in (HEALTH_STALE, HEALTH_INVALID):
            self._valid_streak += 1
            if self._valid_streak >= self._restore_required:
                self._set(HEALTH_RESTORED)
                self._restored_until_ns = now_ns + self._restored_hold_ns
                self._valid_streak = 0
            return
        # Already healthy/restored: refresh freshness only.
        self._valid_streak = 0

    def mark_invalid(self, now_ns: int) -> None:
        self._now_ns = now_ns
        self._valid_streak = 0
        self._set(HEALTH_INVALID)

    def tick(self, now_ns: int) -> None:
        self._now_ns = now_ns
        if self._restored_until_ns is not None:
            if now_ns >= self._restored_until_ns:
                self._restored_until_ns = None
                self._set(HEALTH_HEALTHY)
            return
        if (
            self._disposition in (HEALTH_HEALTHY, HEALTH_RESTORED)
            and self._last_valid_ns is not None
            and now_ns - self._last_valid_ns > self._stale_timeout_ns
        ):
            self._set(HEALTH_STALE)

    def _set(self, disposition: str) -> None:
        if disposition != self._disposition:
            self._disposition = disposition
            self._on_disposition(disposition)
