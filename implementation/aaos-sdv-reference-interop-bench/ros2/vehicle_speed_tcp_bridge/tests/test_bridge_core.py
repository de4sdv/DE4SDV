import json
from pathlib import Path
import sys

import pytest

BENCH = Path(__file__).parents[3]
sys.path.insert(0, str(BENCH / "ros2" / "vehicle_speed_tcp_bridge" / "src"))
sys.path.insert(0, str(BENCH / "ros2" / "vehicle_speed_tcp_bridge" / "scripts"))
sys.path.insert(0, str(BENCH.parent / "vss-vehicle-speed-adapter" / "src"))

from adb_logcat_bridge import extract_wire_payload  # noqa: E402
from de4sdv_vehicle_speed_tcp_bridge.bridge_core import (  # noqa: E402
    WIRE_CLOCK_DOMAIN,
    WIRE_SCHEMA,
    VehicleSpeedTcpBridgeCore,
    WireFormatError,
    parse_vehicle_speed_line,
)


def wire(speed_kmh=36.0, timestamp_ns=1_000, **overrides):
    value = {
        "schema": WIRE_SCHEMA,
        "speed_kmh": speed_kmh,
        "timestamp_ns": timestamp_ns,
        "quality": "VALID",
        "clock_domain": WIRE_CLOCK_DOMAIN,
    }
    value.update(overrides)
    return json.dumps(value) + "\n"


def test_parses_aaos_wire_record_and_preserves_metadata():
    sample = parse_vehicle_speed_line(wire())

    assert sample.value == 36.0
    assert sample.unit == "km/h"
    assert sample.timestamp_ns == 1_000
    assert sample.clock_domain == WIRE_CLOCK_DOMAIN
    assert sample.quality.value == "valid"


def test_converts_and_publishes_36_kmh_as_10_mps():
    published = []
    bridge = VehicleSpeedTcpBridgeCore(published.append)

    output = bridge.handle_line(wire(), now_ns=1_000)

    assert output.longitudinal_velocity_mps == pytest.approx(10.0)
    assert published == [output]


def test_rejects_wire_shape_and_quality_mutations():
    with pytest.raises(WireFormatError, match="keys"):
        parse_vehicle_speed_line(wire(extra="reject"))
    with pytest.raises(WireFormatError, match="quality"):
        parse_vehicle_speed_line(wire(quality="STALE"))
    with pytest.raises(WireFormatError, match="schema"):
        parse_vehicle_speed_line(wire(schema="other.VehicleSpeed"))


@pytest.mark.parametrize(
    "payload",
    [wire(speed_kmh=True), wire(speed_kmh=float("inf")), wire(speed_kmh=-1.0)],
)
def test_rejects_invalid_speed_values(payload):
    with pytest.raises(WireFormatError):
        parse_vehicle_speed_line(payload)


def test_rejects_stale_source_sample_before_ros_publication():
    published = []
    bridge = VehicleSpeedTcpBridgeCore(published.append, max_age_ns=100)

    with pytest.raises(ValueError, match="stale"):
        bridge.handle_line(wire(timestamp_ns=800), now_ns=1_000)
    assert published == []


def test_adb_logcat_forwarder_extracts_and_recanonicalizes_wire_record():
    line = "de4sdv_reference_vehicle_speed: I DE4SDV_VEHICLE_SPEED_WIRE " + wire().strip()

    forwarded = extract_wire_payload(line)

    assert json.loads(forwarded) == json.loads(wire())


def test_adb_logcat_forwarder_rejects_unmarked_or_mutated_records():
    assert extract_wire_payload("unrelated log line") is None
    with pytest.raises(WireFormatError):
        extract_wire_payload(
            "DE4SDV_VEHICLE_SPEED_WIRE " + wire(extra="reject").strip()
        )
