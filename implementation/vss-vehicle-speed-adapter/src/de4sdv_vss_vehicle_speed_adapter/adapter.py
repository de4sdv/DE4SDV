"""Provider-neutral VSS Vehicle.Speed adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Callable, Protocol


class SignalQuality(str, Enum):
    VALID = "valid"
    STALE = "stale"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class SampleValidationError(ValueError):
    """Raised when a provider sample cannot support a normalized output."""


@dataclass(frozen=True)
class VehicleSpeedSample:
    """Canonical provider input for VSS ``Vehicle.Speed``.

    ``timestamp_ns`` and ``now_ns`` must use the same declared clock domain.
    The adapter deliberately accepts only the VSS speed unit (km/h); provider-
    specific unit conversion belongs in the provider binding, not hidden here.
    """

    value: float
    unit: str
    timestamp_ns: int
    clock_domain: str
    quality: SignalQuality
    semantic_path: str = "Vehicle.Speed"


@dataclass(frozen=True)
class NormalizedVehicleSpeed:
    """Provider-neutral output suitable for a ROS 2 VelocityReport adapter."""

    longitudinal_velocity_mps: float
    timestamp_ns: int
    clock_domain: str
    quality: SignalQuality
    semantic_path: str = "Vehicle.Speed"


@dataclass(frozen=True)
class AdapterConfig:
    """Validation limits in the provider sample's declared clock domain."""

    max_age_ns: int | None = None
    max_future_ns: int = 0
    expected_clock_domain: str | None = None


class VehicleSpeedProvider(Protocol):
    def read_vehicle_speed(self) -> VehicleSpeedSample:
        ...


class VelocityConsumer(Protocol):
    def __call__(self, output: NormalizedVehicleSpeed) -> None:
        """Consume one normalized output."""


class VssVehicleSpeedAdapter:
    """Normalize VSS Vehicle.Speed without selecting a transport or provider."""

    def __init__(self, config: AdapterConfig | None = None) -> None:
        self.config = config or AdapterConfig()

    def translate(
        self,
        sample: VehicleSpeedSample,
        *,
        now_ns: int | None = None,
    ) -> NormalizedVehicleSpeed:
        self._validate(sample, now_ns=now_ns)
        return NormalizedVehicleSpeed(
            longitudinal_velocity_mps=sample.value / 3.6,
            timestamp_ns=sample.timestamp_ns,
            clock_domain=sample.clock_domain,
            quality=sample.quality,
            semantic_path=sample.semantic_path,
        )

    def process(
        self,
        sample: VehicleSpeedSample,
        publish: VelocityConsumer,
        *,
        now_ns: int | None = None,
    ) -> NormalizedVehicleSpeed:
        """Translate then publish; invalid samples are never published."""
        output = self.translate(sample, now_ns=now_ns)
        publish(output)
        return output

    def _validate(self, sample: VehicleSpeedSample, *, now_ns: int | None) -> None:
        if sample.semantic_path != "Vehicle.Speed":
            raise SampleValidationError(
                "semantic path must be Vehicle.Speed"
            )
        if sample.unit != "km/h":
            raise SampleValidationError(
                f"Vehicle.Speed must use km/h, got {sample.unit!r}"
            )
        if not isinstance(sample.value, (int, float)) or isinstance(sample.value, bool):
            raise SampleValidationError("Vehicle.Speed must be numeric")
        if not isfinite(sample.value):
            raise SampleValidationError("Vehicle.Speed must be finite")
        if sample.value < 0:
            raise SampleValidationError("Vehicle.Speed must not be negative")
        if type(sample.timestamp_ns) is not int or sample.timestamp_ns < 0:
            raise SampleValidationError("timestamp_ns must be a non-negative integer")
        if not sample.clock_domain:
            raise SampleValidationError("clock domain must be non-empty")
        if sample.quality is not SignalQuality.VALID:
            raise SampleValidationError(
                f"sample quality must be valid, got {sample.quality.value!r}"
            )
        if self.config.expected_clock_domain is not None and sample.clock_domain != self.config.expected_clock_domain:
            raise SampleValidationError("sample clock domain does not match adapter clock domain")
        if now_ns is None:
            return
        if type(now_ns) is not int or now_ns < 0:
            raise SampleValidationError("now_ns must be a non-negative integer")
        age_ns = now_ns - sample.timestamp_ns
        if age_ns < -self.config.max_future_ns:
            raise SampleValidationError("sample is from the future")
        if self.config.max_age_ns is not None and age_ns > self.config.max_age_ns:
            raise SampleValidationError("sample is stale")
