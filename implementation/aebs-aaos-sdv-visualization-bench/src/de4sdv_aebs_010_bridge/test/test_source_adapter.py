"""Tests for the ROS-agnostic source adapter, projection, and frame server."""

from __future__ import annotations

import struct
import types

import pytest

from de4sdv_aebs_010_bridge.frame_assembler import FrameAssembler
from de4sdv_aebs_010_bridge.source_adapter import (
    FrameServer,
    SourceAdapter,
    encode_frame_json,
    project_closest_point_range_bearing,
)

NOW = [1_000_000_100]


def now_ns() -> int:
    NOW[0] += 100
    return NOW[0]


def make_adapter() -> tuple[SourceAdapter, FrameAssembler]:
    assembler = FrameAssembler("de4sdv_aebs_010_bridge@vmB")
    return SourceAdapter(assembler, now_ns), assembler


class Stamp(types.SimpleNamespace):
    pass


def test_rss_handler_populates_native_field() -> None:
    adapter, assembler = make_adapter()
    msg = types.SimpleNamespace(data=13.2, stamp=Stamp(sec=1, nanosec=0))
    adapter.on_rss_distance(msg)
    assert assembler.state.rss_distance["value"] == 13.2
    assert assembler.state.rss_distance["source_kind"] == "nativeAutowareAEB"


def test_rss_without_stamp_is_ignored() -> None:
    adapter, assembler = make_adapter()
    adapter.on_rss_distance(types.SimpleNamespace(data=13.2, stamp=Stamp(sec=0, nanosec=0)))
    assert assembler.state.rss_distance is None


def test_pointcloud_projection_is_display_derived() -> None:
    adapter, assembler = make_adapter()

    # Minimal PointCloud2 stand-in: x at offset 0, y at offset 4, step 8.
    points = struct.pack("<2f", 12.0, 0.5) + struct.pack("<2f", 8.0, -0.25)
    cloud = types.SimpleNamespace(
        fields=[
            types.SimpleNamespace(name="x", offset=0),
            types.SimpleNamespace(name="y", offset=4),
        ],
        point_step=8,
        is_bigendian=False,
        data=points,
        header=types.SimpleNamespace(stamp=Stamp(sec=1, nanosec=0)),
    )
    adapter.on_obstacle_pointcloud(cloud)
    assert assembler.state.target_range["value"] == pytest.approx(8.003904, abs=1e-4)
    assert assembler.state.target_range["source_kind"] == "displayDerived"
    assert assembler.state.target_bearing["source_kind"] == "displayDerived"


def test_pointcloud_without_positive_point_is_skipped() -> None:
    adapter, assembler = make_adapter()
    cloud = types.SimpleNamespace(
        fields=[types.SimpleNamespace(name="x", offset=0), types.SimpleNamespace(name="y", offset=4)],
        point_step=8, is_bigendian=False,
        data=struct.pack("<2f", -5.0, 0.0),
        header=types.SimpleNamespace(stamp=Stamp(sec=1, nanosec=0)),
    )
    adapter.on_obstacle_pointcloud(cloud)
    assert assembler.state.target_range is None


def test_exact_intervention_diagnostic_matches() -> None:
    adapter, assembler = make_adapter()
    status = types.SimpleNamespace(
        name="autonomous_emergency_braking: aeb_emergency_stop",
        level=2, message="[AEB]: Emergency Brake",
    )
    msg = types.SimpleNamespace(status=[status], header=types.SimpleNamespace(stamp=Stamp(sec=2, nanosec=0)))
    adapter.on_diagnostics(msg)
    assert assembler.state.native_intervention["value"] is True


def test_other_diagnostic_names_do_not_match() -> None:
    adapter, assembler = make_adapter()
    status = types.SimpleNamespace(name="other_node: other_task", level=2, message="[AEB]: Emergency Brake")
    msg = types.SimpleNamespace(status=[status], header=types.SimpleNamespace(stamp=Stamp(sec=2, nanosec=0)))
    adapter.on_diagnostics(msg)
    # Non-matching diagnostics are never observed into the frame at all.
    assert assembler.state.native_intervention is None


def test_braking_request_active_on_negative_acceleration() -> None:
    adapter, assembler = make_adapter()
    msg = types.SimpleNamespace(
        longitudinal=types.SimpleNamespace(acceleration=-6.0),
        stamp=Stamp(sec=3, nanosec=0),
    )
    adapter.on_emergency_braking_request(msg)
    assert assembler.state.de4sdv_braking_request["value"] is True


def test_lifecycle_state_round_trip() -> None:
    adapter, assembler = make_adapter()
    msg = types.SimpleNamespace(data="braking_latched", stamp=Stamp(sec=4, nanosec=0))
    adapter.on_coordination_state(msg)
    assert assembler.state.de4sdv_lifecycle_state["value"] == "braking_latched"


def test_frame_server_length_delimited_send() -> None:
    import socket
    import threading

    server = FrameServer("127.0.0.1", 0)
    # Bind a real listener to find the port, then accept in a thread.
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    server._port = port

    received: list[bytes] = []

    def client() -> None:
        c = socket.create_connection(("127.0.0.1", port), timeout=2)
        received.append(c.recv(65536))
        c.close()

    thread = threading.Thread(target=client, daemon=True)
    thread.start()
    conn = server.serve_once()
    thread.join(timeout=2)

    payload = encode_frame_json({"sequence": 1})
    server.send_frame(payload)
    server.close()

    length = struct.unpack("<I", received[0][:4])[0]
    assert length == len(payload)
    assert received[0][4:4 + length] == payload


def test_frame_server_rejects_oversized_frames() -> None:
    server = FrameServer("127.0.0.1", 0)
    with pytest.raises(ValueError):
        server.send_frame(b"x" * 1_048_577)


def test_projection_geometry_on_plain_points() -> None:
    points = struct.pack("<2f", 3.0, 4.0)
    cloud = types.SimpleNamespace(
        fields=[types.SimpleNamespace(name="x", offset=0), types.SimpleNamespace(name="y", offset=4)],
        point_step=8, is_bigendian=False, data=points,
    )
    range_m, bearing = project_closest_point_range_bearing(cloud)
    assert range_m == pytest.approx(5.0)
    assert bearing == pytest.approx(0.9272952, abs=1e-5)
