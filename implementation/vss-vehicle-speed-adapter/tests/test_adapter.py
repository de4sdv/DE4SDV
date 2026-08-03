import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from de4sdv_vss_vehicle_speed_adapter.adapter import (  # noqa: E402
    AdapterConfig,
    SampleValidationError,
    SignalQuality,
    VehicleSpeedSample,
    VssVehicleSpeedAdapter,
)


def sample(value=36.0, **kwargs):
    fields = {
        "value": value,
        "unit": "km/h",
        "timestamp_ns": 1_000,
        "clock_domain": "test-clock",
        "quality": SignalQuality.VALID,
    }
    fields.update(kwargs)
    return VehicleSpeedSample(**fields)


def test_translates_vss_speed_to_ros_longitudinal_velocity():
    result = VssVehicleSpeedAdapter().translate(sample(36.0))

    assert result.longitudinal_velocity_mps == pytest.approx(10.0)
    assert result.timestamp_ns == 1_000
    assert result.clock_domain == "test-clock"
    assert result.semantic_path == "Vehicle.Speed"


def test_rejects_non_vss_unit():
    with pytest.raises(SampleValidationError, match="km/h"):
        VssVehicleSpeedAdapter().translate(sample(unit="m/s"))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_rejects_non_finite_speed(value):
    with pytest.raises(SampleValidationError, match="finite"):
        VssVehicleSpeedAdapter().translate(sample(value))


def test_rejects_negative_vss_vehicle_speed():
    with pytest.raises(SampleValidationError, match="negative"):
        VssVehicleSpeedAdapter().translate(sample(-1.0))


def test_rejects_non_valid_quality():
    with pytest.raises(SampleValidationError, match="quality"):
        VssVehicleSpeedAdapter().translate(sample(quality=SignalQuality.STALE))


def test_rejects_stale_and_future_samples_in_declared_clock_domain():
    adapter = VssVehicleSpeedAdapter(
        AdapterConfig(max_age_ns=100, max_future_ns=10)
    )
    with pytest.raises(SampleValidationError, match="stale"):
        adapter.translate(sample(timestamp_ns=800), now_ns=1_000)
    with pytest.raises(SampleValidationError, match="future"):
        adapter.translate(sample(timestamp_ns=1_020), now_ns=1_000)


def test_rejects_clock_domain_mismatch():
    adapter = VssVehicleSpeedAdapter(
        AdapterConfig(max_age_ns=100, expected_clock_domain="test-clock")
    )
    with pytest.raises(SampleValidationError, match="clock domain"):
        adapter.translate(sample(clock_domain="other-clock"), now_ns=1_000)


def test_publishes_only_after_successful_translation():
    published = []
    adapter = VssVehicleSpeedAdapter()

    output = adapter.process(sample(72.0), published.append)

    assert output.longitudinal_velocity_mps == pytest.approx(20.0)
    assert published == [output]

    with pytest.raises(SampleValidationError):
        adapter.process(sample(-1.0), published.append)
    assert published == [output]
