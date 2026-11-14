#!/usr/bin/env python3
"""DE4SDV CAN-over-UDP bridge.

Carries one SocketCAN bus across the vehicle Ethernet. This replaces the
third-party tunnel the testbed used first: the payload is plain CAN frames, so a
fixed 17-byte datagram is enough, and owning it keeps the whole distributed stack
under DE4SDV's Apache-2.0 licence instead of pulling a GPL-2.0 binary into every
image we would ever publish.

Design decisions worth stating:

* **No buffering, no batching.** One CAN frame becomes one datagram the moment it
  is read. The tunnel this replaced held frames for 100 ms by default, which made
  a 3 ms path read as 78 ms until the timeout was noticed.
* **No echo suppression needed.** A SocketCAN socket does not receive the frames
  it sends itself (`CAN_RAW_RECV_OWN_MSGS` is off), so a frame delivered from the
  network is never re-transmitted by the same bridge.
* **Fixed-size framing.** A magic + version prefix, a 32-bit CAN id with the
  extended flag in bit 31, the DLC and eight data bytes. No length prefix, no
  parser state, and a malformed datagram is dropped and counted rather than
  resynchronised.
* **It is a wire, not a router.** Filtering belongs to the gateway policy; this
  moves bytes.
"""

from __future__ import annotations

import argparse
import select
import signal
import socket
import struct
import sys
import time
from dataclasses import dataclass, field

MAGIC = b"D4E1"  # version 1 of the DE4SDV CAN-over-UDP framing
HEADER = struct.Struct("!4sIB8s")  # magic, can_id (bit31 = extended), dlc, data
CAN_EFF_FLAG = 0x80000000
CAN_FRAME = struct.Struct("=IB3x8s")  # Linux struct can_frame: id, dlc, pad, data
MAX_DLC = 8


class FramingError(ValueError):
    """The datagram is not a DE4SDV CAN frame."""


def encode_frame(can_id: int, data: bytes, extended: bool = False) -> bytes:
    if len(data) > MAX_DLC:
        raise FramingError(f"dlc {len(data)} exceeds {MAX_DLC}")
    if not 0 <= can_id <= 0x1FFFFFFF:
        raise FramingError(f"can_id {can_id:#x} out of range")
    wire_id = can_id | (CAN_EFF_FLAG if extended else 0)
    return HEADER.pack(MAGIC, wire_id, len(data), data.ljust(MAX_DLC, b"\x00"))


def decode_frame(packet: bytes) -> tuple[int, bytes, bool]:
    if len(packet) != HEADER.size:
        raise FramingError(f"expected {HEADER.size} bytes, got {len(packet)}")
    magic, wire_id, dlc, data = HEADER.unpack(packet)
    if magic != MAGIC:
        raise FramingError(f"bad magic {magic!r}")
    if dlc > MAX_DLC:
        raise FramingError(f"dlc {dlc} exceeds {MAX_DLC}")
    extended = bool(wire_id & CAN_EFF_FLAG)
    return wire_id & ~CAN_EFF_FLAG, data[:dlc], extended


@dataclass
class Counters:
    can_to_udp: int = 0
    udp_to_can: int = 0
    dropped: int = 0
    by_reason: dict[str, int] = field(default_factory=dict)

    def drop(self, reason: str) -> None:
        self.dropped += 1
        self.by_reason[reason] = self.by_reason.get(reason, 0) + 1


def open_can(interface: str) -> socket.socket:
    sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    sock.bind((interface,))
    sock.setblocking(False)
    return sock


def open_udp(listen_port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", listen_port))
    sock.setblocking(False)
    return sock


def run(interface: str, remote: tuple[str, int], listen_port: int) -> int:
    can_sock = open_can(interface)
    udp_sock = open_udp(listen_port)
    counters = Counters()
    running = True

    def stop(signum, frame):  # noqa: ARG001
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(
        f"[bridge] {interface} <-> udp {remote[0]}:{remote[1]} (listen {listen_port})",
        flush=True,
    )

    while running:
        readable, _, _ = select.select([can_sock, udp_sock], [], [], 1.0)
        for sock in readable:
            if sock is can_sock:
                try:
                    raw = can_sock.recv(CAN_FRAME.size)
                except BlockingIOError:
                    continue
                if len(raw) != CAN_FRAME.size:
                    counters.drop("short_can_frame")
                    continue
                can_id, dlc, data = CAN_FRAME.unpack(raw)
                extended = bool(can_id & CAN_EFF_FLAG)
                try:
                    udp_sock.sendto(
                        encode_frame(can_id & ~CAN_EFF_FLAG, data[:dlc], extended), remote
                    )
                    counters.can_to_udp += 1
                except FramingError as exc:
                    counters.drop(f"encode:{exc}")
                except OSError:
                    # remote not up yet; the frame is gone, and the count says so
                    counters.drop("udp_send_failed")
            else:
                try:
                    packet, _ = udp_sock.recvfrom(HEADER.size * 2)
                except BlockingIOError:
                    continue
                try:
                    can_id, data, extended = decode_frame(packet)
                except FramingError as exc:
                    counters.drop(f"decode:{exc}")
                    continue
                wire_id = can_id | (CAN_EFF_FLAG if extended else 0)
                can_sock.send(CAN_FRAME.pack(wire_id, len(data), data))
                counters.udp_to_can += 1

    print(
        f"[bridge] stopped: can->udp {counters.can_to_udp}, udp->can {counters.udp_to_can}, "
        f"dropped {counters.dropped} {counters.by_reason or ''}",
        flush=True,
    )
    can_sock.close()
    udp_sock.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--can", required=True, help="CAN interface to bridge, e.g. vcan0")
    ap.add_argument("--remote", required=True, help="peer as host:port")
    ap.add_argument("--listen", type=int, required=True, help="UDP port to listen on")
    args = ap.parse_args()

    host, _, port = args.remote.rpartition(":")
    if not host:
        print("--remote must be host:port", file=sys.stderr)
        return 2
    return run(args.can, (host, int(port)), args.listen)


if __name__ == "__main__":
    sys.exit(main())
