"""Runtime tests for the zonal CAN gateway router (review findings R6, R7).

The router's own pumps run against python-can's `virtual` interface: real
`can.Bus` objects on in-process channels. Like SocketCAN with
`CAN_RAW_RECV_OWN_MSGS` off, a virtual bus does not receive the frames it sent
itself, so a frame the gateway forwards does not come back to the gateway on the
bus it was written to. Where a send error is needed, a VirtualBus subclass
raises the exception python-can's SocketCAN backend raises.

Run:  python -m pytest de4sdv-virtual-ee/checks/tests/test_runtime_gateway.py
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from pathlib import Path

import can
import pytest
from can.interfaces.virtual import VirtualBus

GATEWAY = Path(__file__).resolve().parents[2] / "gateway"
sys.path.insert(0, str(GATEWAY))

import router  # noqa: E402

CONSECUTIVE_FRAME = bytes([0x21, 0, 0, 0, 0, 0, 0, 0])


class Segment:
    """One bus segment: the gateway's own bus and a node on the same channel."""

    def __init__(self, name: str, gateway_bus_cls=VirtualBus) -> None:
        channel = f"{name}-{uuid.uuid4().hex}"
        self.gateway = gateway_bus_cls(channel=channel)
        self.node = VirtualBus(channel=channel)

    def received(self, wait: float = 0.3) -> list[can.Message]:
        out = []
        deadline = time.monotonic() + wait
        while (left := deadline - time.monotonic()) > 0:
            msg = self.node.recv(timeout=left)
            if msg is not None:
                out.append(msg)
        return out

    def close(self) -> None:
        self.gateway.shutdown()
        self.node.shutdown()


@pytest.fixture
def gateway():
    """Front and rear segments with both of the router's pumps running."""
    router.stop.clear()
    router.stats.clear()
    front, rear = Segment("front"), Segment("rear")
    threads = [
        threading.Thread(target=router.pump, args=("front", "rear", front.gateway, rear.gateway, "front->rear"), daemon=True),
        threading.Thread(target=router.pump, args=("rear", "front", rear.gateway, front.gateway, "rear->front"), daemon=True),
    ]
    for t in threads:
        t.start()
    yield front, rear, threads
    router.stop.set()
    for t in threads:
        t.join(timeout=2)
    front.close()
    rear.close()


def test_identical_frames_from_the_same_source_are_all_forwarded(gateway):
    # ISO-TP repeats byte-identical frames legitimately (a consecutive frame whose
    # sequence number wrapped, a repeated flow control, a status that did not change).
    front, rear, _ = gateway
    front.node.send(can.Message(arbitration_id=0x7E0, data=CONSECUTIVE_FRAME, is_extended_id=False))
    time.sleep(0.02)
    front.node.send(can.Message(arbitration_id=0x7E0, data=CONSECUTIVE_FRAME, is_extended_id=False))

    arrived = rear.received()

    assert [bytes(m.data) for m in arrived] == [CONSECUTIVE_FRAME, CONSECUTIVE_FRAME], dict(router.stats)


# --- guards: why the router needs no echo guard. These held before the guard was
# removed; they pin the properties its removal relies on.


def test_directional_allow_lists_are_disjoint():
    assert not router.POLICY["front->rear"] & router.POLICY["rear->front"]


def test_forwarded_frame_does_not_come_back_to_its_source_segment(gateway):
    front, rear, _ = gateway
    front.node.send(can.Message(arbitration_id=0x181, data=b"\x01", is_extended_id=False))

    assert [m.arbitration_id for m in rear.received()] == [0x181]
    assert front.received() == []
    assert not [k for k in router.stats if k.startswith("rear->front")], dict(router.stats)


def test_a_frame_reinjected_on_the_destination_segment_is_refused_not_looped(gateway):
    front, rear, _ = gateway
    rear.node.send(can.Message(arbitration_id=0x181, data=b"\x01", is_extended_id=False))

    assert front.received() == []
    assert router.stats["rear->front.denied.0x181"] == 1, dict(router.stats)
