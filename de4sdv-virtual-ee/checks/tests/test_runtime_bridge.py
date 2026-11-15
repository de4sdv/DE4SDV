"""Runtime tests for the DE4SDV CAN-over-UDP bridge (review finding R4).

The bridge runs as a real process (`bridge.main()`), with real UDP sockets on
the loopback. Only SocketCAN is replaced: `open_can` returns an AF_UNIX datagram
socket connected to the test, which has the same send/recv/select surface. So
the source address the bridge sees is the one the kernel reports for a real UDP
datagram, and a frame "on the bus" is a datagram the test receives.

Run:  python -m pytest de4sdv-virtual-ee/checks/tests/test_runtime_bridge.py
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

TRANSPORT = Path(__file__).resolve().parents[2] / "transport"
sys.path.insert(0, str(TRANSPORT))

import bridge  # noqa: E402

LAUNCH = """
import socket, sys
sys.path.insert(0, sys.argv[1])
import bridge
bridge_path, test_path = sys.argv[2], sys.argv[3]

def fake_open_can(interface):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(bridge_path)
    sock.connect(test_path)
    sock.setblocking(False)
    return sock

bridge.open_can = fake_open_can
sys.argv = ["bridge.py"] + sys.argv[4:]
sys.exit(bridge.main())
"""

COMMAND_ON = bytes([0x01, 0, 0, 0, 0, 0, 0, 0])  # 0x180 headlamp command, ON


def free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class RunningBridge:
    """One bridge process, its fake CAN end, and its configured UDP peer."""

    def __init__(self, remote_host: str = "127.0.0.1") -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.bridge_path = bridge_path = os.path.join(self.dir.name, "bridge.sock")
        test_path = os.path.join(self.dir.name, "test.sock")
        self.can = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.can.bind(test_path)
        self.can.settimeout(1.0)
        self.peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.peer.bind(("127.0.0.1", 0))
        self.peer.settimeout(1.0)
        self.listen = free_udp_port()
        remote = f"{remote_host}:{self.peer.getsockname()[1]}"
        self.proc = subprocess.Popen(
            [sys.executable, "-c", LAUNCH, str(TRANSPORT), bridge_path, test_path,
             "--can", "vcan-test", "--remote", remote, "--listen", str(self.listen)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.banner = self.proc.stdout.readline()
        assert self.banner.startswith("[bridge]"), self.banner

    def send_from(self, sock: socket.socket, can_id: int, data: bytes) -> None:
        sock.sendto(bridge.encode_frame(can_id, data), ("127.0.0.1", self.listen))

    def bus_frame(self, timeout: float = 1.0):
        """The next frame the bridge wrote to the (fake) bus, or None."""
        self.can.settimeout(timeout)
        try:
            raw = self.can.recv(64)
        except socket.timeout:
            return None
        can_id, dlc, data = bridge.CAN_FRAME.unpack(raw)
        return can_id, data[:dlc]

    def stop(self) -> str:
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
        out, _ = self.proc.communicate(timeout=5)
        self.can.close()
        self.peer.close()
        self.dir.cleanup()
        return out


@pytest.fixture
def running_bridge():
    instance = RunningBridge()
    yield instance
    if instance.proc.poll() is None:
        instance.stop()


def test_datagram_from_unconfigured_udp_source_never_reaches_the_bus(running_bridge):
    rogue = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rogue.bind(("127.0.0.1", 0))  # same host, different port: not the configured peer
    try:
        running_bridge.send_from(rogue, 0x180, COMMAND_ON)
        injected = running_bridge.bus_frame(timeout=0.5)
    finally:
        rogue.close()
    report = running_bridge.stop()

    assert injected is None, f"foreign sender injected {injected} onto the bus"
    assert "foreign_peer" in report, report


@pytest.mark.parametrize("remote_host", ["127.0.0.1", "localhost"])
def test_datagram_from_configured_peer_reaches_the_bus(remote_host):
    running = RunningBridge(remote_host)
    try:
        running.send_from(running.peer, 0x181, bytes([0x01]))
        delivered = running.bus_frame()
    finally:
        report = running.stop()

    assert delivered == (0x181, bytes([0x01])), report
    assert "udp->can 1," in report, report


@pytest.mark.parametrize(
    "wire_id",
    [
        0x40000181,  # remote-transmission-request flag on a standard id
        0x20000181,  # error-frame flag: not a frame a peer may inject
        0x00000800,  # standard (11-bit) frame whose id needs 12 bits
        0xC0000181,  # extended + RTR
    ],
    ids=["rtr", "err", "std-id-over-11-bits", "ext-rtr"],
)
def test_unsupported_id_or_flag_from_configured_peer_never_reaches_the_bus(wire_id):
    running = RunningBridge()
    try:
        datagram = bridge.HEADER.pack(bridge.MAGIC, wire_id, 1, b"\x01".ljust(8, b"\x00"))
        running.peer.sendto(datagram, ("127.0.0.1", running.listen))
        injected = running.bus_frame(timeout=0.5)
    finally:
        report = running.stop()

    assert injected is None, f"wire id {wire_id:#010x} reached the bus as {injected}"
    assert "dropped 1" in report, report


def test_remote_frame_read_from_the_bus_is_not_sent_as_data():
    # guard: an RTR frame on the bus has no data to carry; it must not leave as one
    running = RunningBridge()
    try:
        running.can.sendto(bridge.CAN_FRAME.pack(0x181 | 0x40000000, 0, bytes(8)), running.bridge_path)
        running.peer.settimeout(0.5)
        try:
            leaked = running.peer.recv(64)
        except socket.timeout:
            leaked = None
    finally:
        report = running.stop()

    assert leaked is None, f"remote frame left as {leaked!r}"
    assert "can->udp 0," in report, report


def test_full_bus_queue_drops_and_counts_frames_and_the_bridge_keeps_running():
    # The fake bus stops reading, so its queue fills and the bridge's non-blocking
    # write fails with EAGAIN, the same errno family a full SocketCAN tx queue gives.
    running = RunningBridge()
    try:
        for n in range(600):
            running.send_from(running.peer, 0x181, bytes([n & 0xFF]))
        time.sleep(0.5)
        while running.bus_frame(timeout=0.2) is not None:
            pass  # drain, then show the bridge still delivers
        running.send_from(running.peer, 0x181, bytes([0xAA]))
        after = running.bus_frame()
        alive = running.proc.poll() is None
    finally:
        report = running.stop()

    assert alive, f"bridge exited on a full bus queue:\n{report}"
    assert after == (0x181, bytes([0xAA])), report
    assert "can_send_failed" in report, report
