"""Executable local rehearsal for the DE4SDV-owned reference contract."""

from __future__ import annotations

from dataclasses import dataclass
from time import time_ns
from typing import Callable

from de4sdv_vss_vehicle_speed_adapter import (
    SignalQuality,
    VehicleSpeedSample,
    VssVehicleSpeedAdapter,
)


@dataclass(frozen=True)
class ReferenceProvider:
    """Stand-in for the future AAOS VSIDL publisher binding."""

    speed_kmh: float
    timestamp_ns: int
    clock_domain: str = "reference-provider-clock"

    def sample(self) -> VehicleSpeedSample:
        return VehicleSpeedSample(
            value=self.speed_kmh,
            unit="km/h",
            timestamp_ns=self.timestamp_ns,
            clock_domain=self.clock_domain,
            quality=SignalQuality.VALID,
        )


@dataclass(frozen=True)
class ObservedOutput:
    longitudinal_velocity_mps: float
    timestamp_ns: int
    semantic_path: str


@dataclass(frozen=True)
class VelocityReportBoundaryRecord:
    """Record emitted at the Autoware-facing ROS 2 velocity-report boundary.

    Mirrors the modeled ``autowareRos2Boundary`` port contract
    (``adapter.ros2VelocityOut -> autowareRos2Boundary.velocityReportIn``,
    ``VelocityReport`` payload on ``/vehicle/status/velocity_status``). The
    record is VelocityReport-shaped; live ROS 2 runtime publication is not
    claimed by this rehearsal.
    """

    longitudinal_velocity_mps: float
    timestamp_ns: int
    semantic_path: str


class AutowareRos2VelocityReportBoundary:
    """VM-B-facing ROS 2 topic boundary stand-in for the reference slice.

    Consumes adapter-normalized output and emits a VelocityReport-shaped
    record, mirroring the modeled ``autowareRos2Boundary`` usage in
    ``MiddlewarePhysicalSoftwareBoundary``.
    """

    def __init__(self) -> None:
        self.records: list[VelocityReportBoundaryRecord] = []

    def publish(self, output) -> None:
        self.records.append(
            VelocityReportBoundaryRecord(
                longitudinal_velocity_mps=output.longitudinal_velocity_mps,
                timestamp_ns=output.timestamp_ns,
                semantic_path=output.semantic_path,
            )
        )


class IndependentObserver:
    """Observer with expectations independent of adapter output assertions."""

    def __init__(self) -> None:
        self.outputs: list[ObservedOutput] = []

    def observe(self, output) -> None:
        self.outputs.append(
            ObservedOutput(
                longitudinal_velocity_mps=output.longitudinal_velocity_mps,
                timestamp_ns=output.timestamp_ns,
                semantic_path=output.semantic_path,
            )
        )

    def verify(self, *, expected_speed_kmh: float, expected_timestamp_ns: int) -> None:
        if len(self.outputs) != 1:
            raise AssertionError(f"expected one output, got {len(self.outputs)}")
        output = self.outputs[0]
        expected_mps = expected_speed_kmh / 3.6
        if abs(output.longitudinal_velocity_mps - expected_mps) > 1e-12:
            raise AssertionError(
                f"unexpected longitudinal velocity: {output.longitudinal_velocity_mps}"
            )
        if output.timestamp_ns != expected_timestamp_ns:
            raise AssertionError("timestamp was not preserved")
        if output.semantic_path != "Vehicle.Speed":
            raise AssertionError("semantic identity was not preserved")


def run_reference_rehearsal(
    *,
    speed_kmh: float = 36.0,
    timestamp_ns: int | None = None,
    publish: Callable | None = None,
) -> dict:
    timestamp_ns = timestamp_ns if timestamp_ns is not None else time_ns()
    provider = ReferenceProvider(speed_kmh=speed_kmh, timestamp_ns=timestamp_ns)
    observer = IndependentObserver()
    adapter = VssVehicleSpeedAdapter()
    boundary = AutowareRos2VelocityReportBoundary()
    adapter.process(provider.sample(), boundary.publish)
    for record in boundary.records:
        observer.observe(record)
    if publish is not None:
        publish(observer.outputs[0])
    observer.verify(
        expected_speed_kmh=speed_kmh,
        expected_timestamp_ns=timestamp_ns,
    )
    return {
        "claim": "de4sdv_reference_contract_rehearsal",
        "passed": True,
        "provider": "VehicleSpeedProvider reference stand-in",
        "adapter": "VssVehicleSpeedAdapter",
        "velocity_report_boundary": "AutowareRos2VelocityReportBoundary",
        "chain": [
            "aaosProviderStandIn",
            "adapter",
            "autowareRos2VelocityReportBoundary",
            "independentObserver",
        ],
        "semantic_path": "Vehicle.Speed",
        "input_speed_kmh": speed_kmh,
        "output_longitudinal_velocity_mps": speed_kmh / 3.6,
        "timestamp_ns": timestamp_ns,
        "observer": "IndependentObserver",
        "aaos_runtime_interoperability": "not_proven",
        "ros2_runtime_interoperability": "not_proven",
    }
