from pathlib import Path
import sys

import pytest

BENCH = Path(__file__).parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(BENCH.parents[0] / "vss-vehicle-speed-adapter" / "src"))

from de4sdv_aaos_sdv_reference_bench import (  # noqa: E402
    AutowareRos2VelocityReportBoundary,
    IndependentObserver,
    ReferenceProvider,
    run_reference_rehearsal,
)
from de4sdv_vss_vehicle_speed_adapter import VssVehicleSpeedAdapter  # noqa: E402


def test_reference_rehearsal_produces_independent_pass_evidence():
    evidence = run_reference_rehearsal(speed_kmh=72.0, timestamp_ns=42)

    assert evidence["claim"] == "de4sdv_reference_contract_rehearsal"
    assert evidence["passed"] is True
    assert evidence["output_longitudinal_velocity_mps"] == pytest.approx(20.0)
    assert evidence["observer"] == "IndependentObserver"
    assert evidence["aaos_runtime_interoperability"] == "not_proven"


def test_rehearsal_chain_mirrors_modeled_adapter_boundary():
    evidence = run_reference_rehearsal(speed_kmh=36.0, timestamp_ns=7)

    assert evidence["chain"] == [
        "aaosProviderStandIn",
        "adapter",
        "autowareRos2VelocityReportBoundary",
        "independentObserver",
    ]
    assert evidence["adapter"] == "VssVehicleSpeedAdapter"
    assert evidence["velocity_report_boundary"] == "AutowareRos2VelocityReportBoundary"
    assert evidence["ros2_runtime_interoperability"] == "not_proven"


def test_velocity_report_boundary_emits_velocity_report_shaped_record():
    boundary = AutowareRos2VelocityReportBoundary()
    adapter = VssVehicleSpeedAdapter()
    adapter.process(ReferenceProvider(36.0, 99).sample(), boundary.publish)

    assert len(boundary.records) == 1
    record = boundary.records[0]
    assert record.longitudinal_velocity_mps == pytest.approx(10.0)
    assert record.timestamp_ns == 99
    assert record.semantic_path == "Vehicle.Speed"


def test_provider_emits_vss_sample():
    sample = ReferenceProvider(36.0, 99).sample()

    assert sample.semantic_path == "Vehicle.Speed"
    assert sample.unit == "km/h"
    assert sample.value == 36.0


def test_observer_rejects_missing_output():
    observer = IndependentObserver()

    with pytest.raises(AssertionError, match="expected one output"):
        observer.verify(expected_speed_kmh=36.0, expected_timestamp_ns=1)
