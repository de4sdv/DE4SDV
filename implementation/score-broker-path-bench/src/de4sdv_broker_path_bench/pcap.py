"""Read classic pcap files and reassemble TCP streams (standard library only).

The bench captures with tcpdump, which writes classic pcap. pcapng is
refused, so a capture in another format cannot be read silently wrong.
Supported link types: Ethernet with 802.1Q/802.1ad tags (1), Linux cooked
v1 (113) and v2 (276), raw IP (101, 12, 14, 228, 229) and BSD loopback (0).
"""

from __future__ import annotations

import bisect
import struct
from dataclasses import dataclass, field
from pathlib import Path

_MAGICS = {
    b"\xd4\xc3\xb2\xa1": ("<", 1_000),  # little-endian, microseconds
    b"\xa1\xb2\xc3\xd4": (">", 1_000),
    b"\x4d\x3c\xb2\xa1": ("<", 1),  # little-endian, nanoseconds
    b"\xa1\xb2\x3c\x4d": (">", 1),
}
_PCAPNG = b"\x0a\x0d\x0d\x0a"

TCP_FIN = 0x01
TCP_SYN = 0x02
TCP_RST = 0x04
TCP_ACK = 0x10


class PcapError(ValueError):
    """The file is not a readable classic pcap capture."""


@dataclass(frozen=True)
class Packet:
    ts_ns: int
    linktype: int
    data: bytes
    orig_len: int


@dataclass(frozen=True)
class Capture:
    packets: tuple[Packet, ...]
    linktype: int
    snaplen: int
    truncated: bool  # the last record was cut off (the capture stopped mid-write)


def read_pcap(path: str | Path) -> Capture:
    raw = Path(path).read_bytes()
    if raw[:4] == _PCAPNG:
        raise PcapError(f"{path}: pcapng is not supported; capture with tcpdump -w (classic pcap)")
    if len(raw) < 24 or raw[:4] not in _MAGICS:
        raise PcapError(f"{path}: not a classic pcap file")
    order, unit = _MAGICS[raw[:4]]
    _vmaj, _vmin, _zone, _sig, snaplen, linktype = struct.unpack(order + "HHiIII", raw[4:24])
    linktype &= 0x0FFFFFFF
    packets: list[Packet] = []
    offset = 24
    truncated = False
    while offset < len(raw):
        if offset + 16 > len(raw):
            truncated = True
            break
        sec, frac, incl, orig = struct.unpack(order + "IIII", raw[offset:offset + 16])
        offset += 16
        if offset + incl > len(raw):
            truncated = True
            break
        packets.append(Packet(sec * 1_000_000_000 + frac * unit, linktype, raw[offset:offset + incl], orig))
        offset += incl
    return Capture(tuple(packets), linktype, snaplen, truncated)


@dataclass(frozen=True)
class Datagram:
    """One IP packet with its transport header decoded."""

    ts_ns: int
    protocol: str  # "tcp" or "udp"
    src: str
    dst: str
    sport: int
    dport: int
    payload: bytes
    vlans: tuple[int, ...] = ()
    tcp_seq: int = 0
    tcp_ack: int = 0
    tcp_flags: int = 0


def _ipv4_text(raw: bytes) -> str:
    return ".".join(str(byte) for byte in raw)


def _ipv6_text(raw: bytes) -> str:
    words = struct.unpack(">8H", raw)
    return ":".join(f"{word:x}" for word in words)


def _network_layer(packet: Packet) -> tuple[int, bytes, tuple[int, ...]] | None:
    """(ethertype or 4/6 marker, network bytes, VLAN IDs) of a packet."""
    data, link = packet.data, packet.linktype
    vlans: list[int] = []
    if link == 1:
        if len(data) < 14:
            return None
        ethertype = struct.unpack(">H", data[12:14])[0]
        offset = 14
        while ethertype in (0x8100, 0x88A8) and len(data) >= offset + 4:
            vlans.append(struct.unpack(">H", data[offset:offset + 2])[0] & 0x0FFF)
            ethertype = struct.unpack(">H", data[offset + 2:offset + 4])[0]
            offset += 4
        return ethertype, data[offset:], tuple(vlans)
    if link == 113:
        if len(data) < 16:
            return None
        return struct.unpack(">H", data[14:16])[0], data[16:], ()
    if link == 276:
        if len(data) < 20:
            return None
        return struct.unpack(">H", data[0:2])[0], data[20:], ()
    if link in (101, 12, 14, 228, 229):
        if not data:
            return None
        version = data[0] >> 4
        return (0x0800 if version == 4 else 0x86DD), data, ()
    if link == 0:
        if len(data) < 4:
            return None
        family = struct.unpack("<I", data[:4])[0]
        if family == 2:
            return 0x0800, data[4:], ()
        if family in (24, 28, 30):
            return 0x86DD, data[4:], ()
        return None
    return None


def decode(packet: Packet) -> Datagram | None:
    """The TCP or UDP datagram in ``packet``, or None for anything else."""
    layer = _network_layer(packet)
    if layer is None:
        return None
    ethertype, net, vlans = layer
    if ethertype == 0x0800:
        if len(net) < 20:
            return None
        ihl = (net[0] & 0x0F) * 4
        total = struct.unpack(">H", net[2:4])[0]
        fragment = struct.unpack(">H", net[6:8])[0]
        if fragment & 0x1FFF or fragment & 0x2000:
            return None  # fragments carry no complete transport header here
        protocol = net[9]
        src, dst = _ipv4_text(net[12:16]), _ipv4_text(net[16:20])
        transport = net[ihl:total] if total >= ihl else net[ihl:]
    elif ethertype == 0x86DD:
        if len(net) < 40:
            return None
        protocol = net[6]
        src, dst = _ipv6_text(net[8:24]), _ipv6_text(net[24:40])
        length = struct.unpack(">H", net[4:6])[0]
        transport = net[40:40 + length]
        # Skip hop-by-hop, routing and destination option headers.
        while protocol in (0, 43, 60) and len(transport) >= 8:
            protocol, extra = transport[0], (transport[1] + 1) * 8
            transport = transport[extra:]
    else:
        return None
    if protocol == 6 and len(transport) >= 20:
        sport, dport, seq, ack = struct.unpack(">HHII", transport[:12])
        header = (transport[12] >> 4) * 4
        flags = transport[13]
        return Datagram(packet.ts_ns, "tcp", src, dst, sport, dport, transport[header:], vlans, seq, ack, flags)
    if protocol == 17 and len(transport) >= 8:
        sport, dport, length = struct.unpack(">HHH", transport[:6])
        return Datagram(packet.ts_ns, "udp", src, dst, sport, dport, transport[8:length], vlans)
    return None


def datagrams(capture: Capture) -> list[Datagram]:
    return [item for item in (decode(packet) for packet in capture.packets) if item is not None]


@dataclass
class TcpStream:
    """One TCP connection to a server port: the bytes the server sent, with their delivery times.

    ``chunks`` holds (end offset, time) pairs in offset order: the bytes up to
    an end offset had all arrived by that time (the in-order delivery time).
    ``gaps`` holds (offset, length) of bytes the capture missed.
    """

    client: tuple[str, int]
    server: tuple[str, int]
    syn_ns: int | None = None
    synack_ns: int | None = None
    established_ns: int | None = None
    fin_ns: int | None = None
    rst_ns: int | None = None
    mid_stream_start: bool = False
    data: bytearray = field(default_factory=bytearray)
    chunks: list[tuple[int, int]] = field(default_factory=list)
    gaps: list[tuple[int, int]] = field(default_factory=list)
    first_ns: int | None = None
    last_ns: int | None = None

    def delivery_ns(self, end_offset: int) -> int | None:
        """The time by which every byte before ``end_offset`` had arrived."""
        index = bisect.bisect_left(self.chunks, (end_offset, -(1 << 62)))
        if index >= len(self.chunks):
            return None
        return self.chunks[index][1]


@dataclass
class _Building:
    stream: TcpStream
    client_isn: int | None = None
    server_isn: int | None = None
    segments: list[tuple[int, int, bytes]] = field(default_factory=list)  # (seq, ts, payload)
    closed: bool = False


def tcp_streams(items: list[Datagram], server_port: int) -> list[TcpStream]:
    """Every connection to ``server_port`` in capture order, with its server-to-client bytes."""
    open_by_key: dict[tuple[str, int, str, int], _Building] = {}
    order: list[_Building] = []
    for item in items:
        if item.protocol != "tcp":
            continue
        if item.dport == server_port:
            key = (item.src, item.sport, item.dst, item.dport)
            from_server = False
        elif item.sport == server_port:
            key = (item.dst, item.dport, item.src, item.sport)
            from_server = True
        else:
            continue
        syn_only = item.tcp_flags & TCP_SYN and not item.tcp_flags & TCP_ACK
        building = open_by_key.get(key)
        if syn_only and not from_server and (building is None or building.closed
                                             or building.client_isn not in (None, item.tcp_seq)):
            building = _Building(TcpStream(client=(key[0], key[1]), server=(key[2], key[3])))
            building.client_isn = item.tcp_seq
            building.stream.syn_ns = item.ts_ns
            open_by_key[key] = building
            order.append(building)
        if building is None:
            building = _Building(TcpStream(client=(key[0], key[1]), server=(key[2], key[3])))
            building.stream.mid_stream_start = True
            open_by_key[key] = building
            order.append(building)
        stream = building.stream
        stream.first_ns = item.ts_ns if stream.first_ns is None else stream.first_ns
        stream.last_ns = item.ts_ns
        if from_server:
            if item.tcp_flags & TCP_SYN and item.tcp_flags & TCP_ACK:
                building.server_isn = item.tcp_seq
                stream.synack_ns = item.ts_ns
            if item.payload:
                building.segments.append((item.tcp_seq, item.ts_ns, item.payload))
        else:
            if (stream.synack_ns is not None and stream.established_ns is None
                    and item.tcp_flags & TCP_ACK and not item.tcp_flags & TCP_SYN):
                stream.established_ns = item.ts_ns
        if item.tcp_flags & TCP_FIN and stream.fin_ns is None:
            stream.fin_ns = item.ts_ns
        if item.tcp_flags & TCP_RST and stream.rst_ns is None:
            stream.rst_ns = item.ts_ns
        if item.tcp_flags & (TCP_FIN | TCP_RST):
            building.closed = True
    for building in order:
        _assemble(building)
    return [building.stream for building in order]


def _assemble(building: _Building) -> None:
    stream = building.stream
    if not building.segments:
        return
    if building.server_isn is not None:
        base = (building.server_isn + 1) & 0xFFFFFFFF
    else:
        stream.mid_stream_start = True
        base = building.segments[0][0]
    relative = sorted((((seq - base) & 0xFFFFFFFF), ts, payload) for seq, ts, payload in building.segments)
    cursor = relative[0][0] if stream.mid_stream_start else 0
    if cursor > 0 and not stream.mid_stream_start:
        stream.gaps.append((0, cursor))
    latest = -(1 << 62)
    for start, ts, payload in relative:
        end = start + len(payload)
        if end <= cursor:
            continue  # a retransmission of bytes already placed
        if start > cursor:
            stream.gaps.append((len(stream.data), start - cursor))
            cursor = start
        stream.data.extend(payload[cursor - start:])
        cursor = end
        latest = max(latest, ts)
        stream.chunks.append((len(stream.data), latest))
