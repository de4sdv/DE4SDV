"""The Data Tunnel capture on VLAN 2 (VC-MW-020: the time of the subscription).

VC-MW-020 runs its check a second time with the time of the subscription in
the Data Tunnel capture as the start (``middleware_score_verification_evidence.sysml``
at main 4bcfe628). The bench captures Data Tunnel on VLAN 2 in the IVI VM
(``data-tunnel-vlan2.pcap``). In the UNLOCKED mode it is gRPC over cleartext
HTTP/2: the IVI VM's agent opens a connection to the SDV Core VM's agent with
the HTTP/2 preface, opens a stream with a HEADERS frame, and the core sends
the publication's messages back as DATA frames on that stream. A message
carries the frame bytes that the relay later serves to the ingress, so a frame
is found in the capture by its bytes. (This is design data from the spike's
VLAN 2 captures; S1 confirms it on the bench.)

This module reassembles each TCP connection of the capture in both
directions and answers three questions, without decoding the Data Tunnel
messages themselves:

- ``locate``: where and when did a frame's bytes cross Data Tunnel?
- ``stream_open_ns``: when did the HTTP/2 stream that carried them open (its
  first HEADERS frame)? That is the subscription time. It is None when the
  capture cannot show it: it joined the connection after its start, or it
  lost bytes before the frame.
- ``arrivals``: when did a list of frames cross on the same carrier?

It reads only raw capture bytes and never opens a socket.
"""

from __future__ import annotations

import bisect
import struct
from dataclasses import dataclass, field

from .pcap import TCP_ACK, TCP_SYN, Capture, datagrams

H2_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
H2_DATA, H2_HEADERS = 0x0, 0x1
H2_FLAG_PADDED = 0x8
H2_FRAME_HEADER = 9


@dataclass
class Direction:
    """The bytes one side sent on a connection, in TCP order, with their capture times."""

    src: tuple[str, int]
    dst: tuple[str, int]
    from_start: bool = False                  # the capture holds this side's SYN, so offset 0 is its first byte
    data: bytearray = field(default_factory=bytearray)
    chunks: list = field(default_factory=list)  # (start offset, end offset, capture time), in offset order
    gaps: list = field(default_factory=list)    # (start, end) of bytes the capture missed

    def time_at(self, offset: int) -> int | None:
        """The capture time of the segment that carried the byte at ``offset``."""
        index = bisect.bisect_right(self.chunks, (offset, float("inf"), float("inf"))) - 1
        if index < 0:
            return None
        start, end, ts = self.chunks[index]
        return ts if start <= offset < end else None

    def has_gap_before(self, offset: int) -> bool:
        return any(start < offset for start, _end in self.gaps)

    def offset_at(self, since_ns: int) -> int:
        """The first offset whose segment the capture saw at or after ``since_ns`` (the end when none)."""
        for start, _end, ts in self.chunks:
            if ts >= since_ns:
                return start
        return len(self.data)


@dataclass
class Connection:
    client: Direction | None   # the side that sent the SYN; None when the capture holds no SYN
    sides: list                # every Direction of the connection with bytes or a SYN


@dataclass(frozen=True)
class Located:
    connection: int
    from_client: bool | None   # whether the client (the SYN sender) sent it; None when no SYN was captured
    side: int                  # the index of the Direction in the connection
    offset: int
    arrival_ns: int


def _assemble(direction: Direction, isn: int | None, segments: list) -> None:
    if not segments:
        return
    base = ((isn + 1) & 0xFFFFFFFF) if isn is not None else min(seq for seq, _ts, _payload in segments)
    ordered = sorted((((seq - base) & 0xFFFFFFFF), ts, payload) for seq, ts, payload in segments)
    if isn is None:
        direction.from_start = False
    cursor = 0
    for offset, ts, payload in ordered:
        if offset >= 1 << 31:  # before the base: a retransmission of bytes before the capture's first
            continue
        end = offset + len(payload)
        if end <= cursor:
            continue  # a full retransmission of bytes already held
        if offset > cursor:
            direction.gaps.append((cursor, offset))
            direction.data.extend(bytes(offset - cursor))  # placeholder bytes keep the offsets aligned
            cursor = offset
        direction.data.extend(payload[cursor - offset:])
        direction.chunks.append((cursor, end, ts))
        cursor = end


def read(capture: Capture) -> "DataTunnel":
    """Every TCP connection of a Data Tunnel capture, reassembled in both directions."""
    by_key: dict[tuple, dict] = {}
    order: list[tuple] = []
    for item in datagrams(capture):
        if item.protocol != "tcp":
            continue
        a, b = (item.src, item.sport), (item.dst, item.dport)
        key = (min(a, b), max(a, b))
        entry = by_key.get(key)
        if entry is None:
            entry = {"sides": {}, "isn": {}, "client": None}
            by_key[key] = entry
            order.append(key)
        side = entry["sides"].setdefault(a, [])
        if item.tcp_flags & TCP_SYN:
            entry["isn"].setdefault(a, item.tcp_seq)
            if not item.tcp_flags & TCP_ACK and entry["client"] is None:
                entry["client"] = a
        if item.payload:
            side.append((item.tcp_seq, item.ts_ns, item.payload))
    connections = []
    for key in order:
        entry = by_key[key]
        sides = []
        client = None
        for src in (key[0], key[1]):
            if src not in entry["sides"]:
                continue
            dst = key[1] if src == key[0] else key[0]
            direction = Direction(src, dst, from_start=src in entry["isn"])
            _assemble(direction, entry["isn"].get(src), entry["sides"][src])
            sides.append(direction)
            if src == entry["client"]:
                client = direction
        connections.append(Connection(client, sides))
    return DataTunnel(connections)


@dataclass
class DataTunnel:
    connections: list

    def locate(self, payload: bytes) -> list[Located]:
        """Every place the capture holds ``payload``'s bytes (the first in each direction), in capture order."""
        found = []
        if not payload:
            return found
        for index, connection in enumerate(self.connections):
            for side_index, direction in enumerate(connection.sides):
                offset = direction.data.find(payload)
                if offset < 0 or any(start < offset + len(payload) and offset < end for start, end in direction.gaps):
                    continue
                arrival = direction.time_at(offset + len(payload) - 1)
                if arrival is None:
                    continue
                from_client = None if connection.client is None else direction is connection.client
                found.append(Located(index, from_client, side_index, offset, arrival))
        return sorted(found, key=lambda item: item.arrival_ns)

    def arrivals(self, carrier: Located, payloads: list[bytes], since_ns: int | None = None) -> list[int]:
        """The arrival times of ``payloads`` on the carrier's direction, for those it holds, in capture order.

        ``since_ns`` starts the search at the bytes the capture saw from that
        time on, so a long capture is not searched from its start for each frame.
        """
        direction = self.connections[carrier.connection].sides[carrier.side]
        begin = direction.offset_at(since_ns) if since_ns is not None else 0
        times = []
        for payload in payloads:
            offset = direction.data.find(payload, begin) if payload else -1
            if offset < 0:
                continue
            arrival = direction.time_at(offset + len(payload) - 1)
            if arrival is not None:
                times.append(arrival)
        return sorted(times)

    def stream_open_ns(self, located: Located) -> int | None:
        """The time the HTTP/2 stream carrying ``located`` opened (its first HEADERS frame), or None.

        None when the capture cannot show it: the connection's start (its SYN
        and, for the client, the preface) is not in the capture, the bytes
        before the frame have a gap, or no HEADERS frame opened that stream.
        """
        connection = self.connections[located.connection]
        if connection.client is None:
            return None
        carrier = connection.sides[located.side]
        stream_id = _stream_at(carrier, connection.client is carrier, located.offset)
        if stream_id is None:
            return None
        opened = []
        for direction in connection.sides:
            for frame_offset, frame_type, _flags, sid, _start, _end in _walk(direction, direction is connection.client):
                if frame_type == H2_HEADERS and sid == stream_id:
                    when = direction.time_at(frame_offset)
                    if when is not None:
                        opened.append(when)
                    break
        return min(opened) if opened else None


def _walk(direction: Direction, is_client: bool):
    """The HTTP/2 frames of one direction from its first byte, up to the first gap or incomplete frame.

    Each is (offset, type, flags, stream id, payload start, payload end). A
    direction the capture did not hold from its start yields nothing: its
    frame boundaries are unknown.
    """
    if not direction.from_start:
        return
    data = direction.data
    offset = 0
    if is_client:
        if not data.startswith(H2_PREFACE):
            return
        offset = len(H2_PREFACE)
    while offset + H2_FRAME_HEADER <= len(data):
        length = int.from_bytes(data[offset:offset + 3], "big")
        frame_type, flags = data[offset + 3], data[offset + 4]
        stream_id = struct.unpack(">I", data[offset + 5:offset + 9])[0] & 0x7FFFFFFF
        end = offset + H2_FRAME_HEADER + length
        if end > len(data) or any(start < end and offset < gap_end for start, gap_end in direction.gaps):
            return
        start = offset + H2_FRAME_HEADER
        if frame_type == H2_DATA and flags & H2_FLAG_PADDED and length:
            pad = data[start]
            start, end_payload = start + 1, end - pad
        else:
            end_payload = end
        yield offset, frame_type, flags, stream_id, start, end_payload
        offset = end


def _stream_at(direction: Direction, is_client: bool, offset: int) -> int | None:
    """The stream id of the DATA frame whose payload holds the byte at ``offset``, or None."""
    for _frame_offset, frame_type, _flags, sid, start, end in _walk(direction, is_client):
        if frame_type == H2_DATA and start <= offset < end:
            return sid
        if start > offset:
            return None
    return None
