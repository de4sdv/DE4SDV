"""Pure wire validation and semantic conversion for the transfer bench."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any

from de4sdv_vss_vehicle_speed_adapter import (
    AdapterConfig,
    NormalizedVehicleSpeed,
    SignalQuality,
    VehicleSpeedSample,
    VssVehicleSpeedAdapter,
)

WIRE_SCHEMA = "de4sdv.reference.vehicle_speed.VehicleSpeed"
WIRE_CLOCK_DOMAIN = "aaos-unix-time-ns"
ROS_VELOCITY_REPORT_TOPIC = "/vehicle/status/velocity_status"
_WIRE_KEYS = frozenset(
    {"schema", "speed_kmh", "timestamp_ns", "quality", "clock_domain"}
)


class WireFormatError(ValueError):
    """Raised when an AAOS wire record is not the closed transfer contract."""


def _require_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WireFormatError(f"{field} must be numeric")
    if not math.isfinite(value):
        raise WireFormatError(f"{field} must be finite")
    return float(value)


def _require_timestamp(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise WireFormatError("timestamp_ns must be a non-negative integer")
    return value


class StalenessWatchdog:
    """Emit an observable degraded disposition when valid samples stop.

    AC-MW-010-03: missing/stale source must produce an observable degraded or
    unavailable disposition — not silent absence. The watchdog fires
    on_degraded once when no valid sample arrives within max_age_ns, and
    on_restored when a valid sample resumes.
    """

    def __init__(
        self,
        *,
        max_age_ns: int = 5_000_000_000,
        on_degraded,
        on_restored,
    ) -> None:
        self._max_age_ns = max_age_ns
        self._on_degraded = on_degraded
        self._on_restored = on_restored
        self._last_valid_ns: int | None = None
        self._degraded = False

    def mark_valid(self, *, now_ns: int) -> None:
        self._last_valid_ns = now_ns

    def tick(self, *, now_ns: int) -> None:
        if self._last_valid_ns is None:
            return
        age_ns = now_ns - self._last_valid_ns
        if age_ns > self._max_age_ns and not self._degraded:
            self._degraded = True
            self._on_degraded(age_ns)
        elif age_ns <= self._max_age_ns and self._degraded:
            self._degraded = False
            self._on_restored()


def parse_vehicle_speed_line(line: bytes | str) -> VehicleSpeedSample:
    """Parse one strict newline-delimited AAOS Vehicle.Speed record."""
    if isinstance(line, bytes):
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError as error:
            raise WireFormatError("wire record must be UTF-8") from error
    if not isinstance(line, str) or not line.strip():
        raise WireFormatError("wire record must be a non-empty JSON object")
    try:
        document = json.loads(line)
    except json.JSONDecodeError as error:
        raise WireFormatError("wire record must be valid JSON") from error
    if type(document) is not dict:
        raise WireFormatError("wire record must be a JSON object")
    if set(document) != _WIRE_KEYS:
        raise WireFormatError("wire record keys do not match the closed contract")
    if document["schema"] != WIRE_SCHEMA:
        raise WireFormatError("wire schema does not match Vehicle.Speed")
    if document["quality"] != "VALID":
        raise WireFormatError("quality must be VALID for the Vehicle.Speed edge")
    if document["clock_domain"] != WIRE_CLOCK_DOMAIN:
        raise WireFormatError("wire clock domain does not match the contract")

    speed_kmh = _require_number(document["speed_kmh"], "speed_kmh")
    if speed_kmh < 0:
        raise WireFormatError("speed_kmh must not be negative")
    timestamp_ns = _require_timestamp(document["timestamp_ns"])
    return VehicleSpeedSample(
        value=speed_kmh,
        unit="km/h",
        timestamp_ns=timestamp_ns,
        clock_domain=WIRE_CLOCK_DOMAIN,
        quality=SignalQuality.VALID,
    )


class VehicleSpeedTcpBridgeCore:
    """Validate, normalize, and publish one AAOS wire record."""

    def __init__(
        self,
        publish: Callable[[NormalizedVehicleSpeed], None],
        *,
        max_age_ns: int = 5_000_000_000,
        max_future_ns: int = 500_000_000,
    ) -> None:
        self._publish = publish
        self._adapter = VssVehicleSpeedAdapter(
            AdapterConfig(
                max_age_ns=max_age_ns,
                max_future_ns=max_future_ns,
                expected_clock_domain=WIRE_CLOCK_DOMAIN,
            )
        )

    def handle_line(
        self,
        line: bytes | str,
        *,
        now_ns: int | None = None,
    ) -> NormalizedVehicleSpeed:
        sample = parse_vehicle_speed_line(line)
        return self._adapter.process(sample, self._publish, now_ns=now_ns)
