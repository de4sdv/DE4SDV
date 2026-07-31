#!/usr/bin/env python3
"""Throwaway feasibility spike for the VSS Vehicle.Speed boundary."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


KMH_PER_MS = 3.6


@dataclass(frozen=True)
class VssVehicleSpeed:
    value: float
    unit: str
    timestamp_ns: int


@dataclass(frozen=True)
class RosVelocityReportProjection:
    longitudinal_velocity: float
    timestamp_ns: int


def normalize_to_ros(sample: VssVehicleSpeed) -> RosVelocityReportProjection:
    if sample.unit != "km/h":
        raise ValueError(f"Vehicle.Speed must be expressed in km/h, got {sample.unit!r}")
    if not isfinite(sample.value):
        raise ValueError("Vehicle.Speed must be finite")
    if sample.value < 0:
        raise ValueError("Vehicle.Speed must not be negative")
    if sample.timestamp_ns < 0:
        raise ValueError("timestamp_ns must not be negative")
    return RosVelocityReportProjection(
        longitudinal_velocity=sample.value / KMH_PER_MS,
        timestamp_ns=sample.timestamp_ns,
    )


def expect_error(sample: VssVehicleSpeed, expected: str) -> None:
    try:
        normalize_to_ros(sample)
    except ValueError as exc:
        assert expected in str(exc), (str(exc), expected)
    else:
        raise AssertionError(f"expected ValueError containing {expected!r}")


def main() -> None:
    cases = [
        (VssVehicleSpeed(0.0, "km/h", 100), 0.0),
        (VssVehicleSpeed(36.0, "km/h", 200), 10.0),
        (VssVehicleSpeed(90.0, "km/h", 300), 25.0),
    ]
    for sample, expected_ms in cases:
        result = normalize_to_ros(sample)
        assert abs(result.longitudinal_velocity - expected_ms) < 1e-12
        assert result.timestamp_ns == sample.timestamp_ns

    expect_error(VssVehicleSpeed(10.0, "m/s", 1), "km/h")
    expect_error(VssVehicleSpeed(float("nan"), "km/h", 1), "finite")
    expect_error(VssVehicleSpeed(float("inf"), "km/h", 1), "finite")
    expect_error(VssVehicleSpeed(-1.0, "km/h", 1), "negative")
    expect_error(VssVehicleSpeed(1.0, "km/h", -1), "timestamp")

    print("VSS Vehicle.Speed boundary spike: PASS")
    print("  semantic input: Vehicle.Speed [km/h]")
    print("  normalized output: VelocityReport.longitudinal_velocity [m/s]")
    print("  transport binding: intentionally not tested")
    print("  runtime AAOS communication: intentionally not claimed")


if __name__ == "__main__":
    main()
