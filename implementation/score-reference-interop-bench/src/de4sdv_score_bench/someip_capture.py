"""Reader of the link captures of the bench: SOME/IP-SD and SOME/IP over TCP.

It reads classic pcap files (microsecond or nanosecond timestamps) with
Ethernet or Linux cooked frames, IPv4, TCP and UDP. It decodes the
SOME/IP-SD entries and their IPv4 endpoint options, reassembles each TCP
direction by sequence number, and splits the byte stream into SOME/IP
messages; magic cookies are skipped. It is evidence tooling for captures of
a known topology, not a general dissector, and it shares no code with the
receiver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import socket
import struct

SD_PORT = 30490
SD_SERVICE = 0xFFFF
SD_METHOD = 0x8100
HEADER_BYTES = 16

SD_ENTRY_TYPES = {
    0x00: "FindService",
    0x01: "OfferService",
    0x06: "SubscribeEventgroup",
    0x07: "SubscribeEventgroupAck",
}
_EVENTGROUP_ENTRIES = (0x06, 0x07)
_L4 = {0x06: "tcp", 0x11: "udp"}
_LINKTYPE_ETHERNET = 1
_LINKTYPE_LINUX_SLL = 113


@dataclass
class Packet:
    ts_ns: int
    src: str
    dst: str
    proto: int
    sport: int
    dport: int
    seq: int = 0
    flags: int = 0
    payload: bytes = b""


@dataclass
class SdEntry:
    type: int
    type_name: str
    service: int
    instance: int
    major: int
    ttl: int
    eventgroup: int | None
    minor: int | None
    endpoints: list[tuple[str, int, str]] = field(default_factory=list)


@dataclass
class SdMessage:
    ts_ns: int
    src: str
    sport: int
    dst: str
    dport: int
    session: int
    reboot: bool
    unicast_flag: bool
    entries: list[SdEntry]

    @property
    def multicast(self) -> bool:
        return 224 <= int(self.dst.split(".")[0]) <= 239


@dataclass
class SomeipMessage:
    ts_ns: int
    src: str
    sport: int
    dst: str
    dport: int
    service: int
    method: int
    client: int
    session: int
    protocol_version: int
    interface_version: int
    message_type: int
    return_code: int
    payload: bytes = field(repr=False)
    connection: int = 0

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


@dataclass
class TcpStream:
    """One direction of one TCP connection; a new SYN starts a new stream."""

    index: int
    src: str
    sport: int
    dst: str
    dport: int
    syn: bool = False
    fin: bool = False
    rst: bool = False
    fin_ts_ns: int | None = None  # the first FIN of the stream
    rst_ts_ns: int | None = None  # the first RST of the stream
    first_ts_ns: int | None = None
    last_ts_ns: int | None = None
    byte_count: int = 0
    gaps: list[int] = field(default_factory=list)
    trailing_bytes: int = 0
    messages: list[SomeipMessage] = field(default_factory=list)
    _isn: int | None = None
    _segments: list[tuple[int, int, bytes]] = field(default_factory=list, repr=False)

    def key(self) -> str:
        return f"{self.src}:{self.sport}->{self.dst}:{self.dport}#{self.index}"


@dataclass
class CaptureAnalysis:
    packets: int
    sd_messages: list[SdMessage]
    sd_malformed: int
    streams: list[TcpStream]

    def notifications(self, server: str, port: int) -> list[SomeipMessage]:
        """Every SOME/IP message that server:port sent over TCP, in time order."""
        found = [m for s in self.streams if s.src == server and s.sport == port for m in s.messages]
        return sorted(found, key=lambda message: message.ts_ns)


def _ip(raw: bytes) -> str:
    return socket.inet_ntoa(raw)


def read_packets(path: Path | str) -> list[Packet]:
    data = Path(path).read_bytes()
    if len(data) < 24:
        return []
    magic = struct.unpack("<I", data[:4])[0]
    if magic in (0xA1B2C3D4, 0xA1B23C4D):
        endian = "<"
    elif magic in (0xD4C3B2A1, 0x4D3CB2A1):
        endian = ">"
        magic = struct.unpack(">I", data[:4])[0]
    else:
        raise ValueError(f"not a classic pcap file: magic 0x{magic:08x}")
    nano = magic == 0xA1B23C4D
    linktype = struct.unpack(endian + "I", data[20:24])[0] & 0x0FFFFFFF
    if linktype == _LINKTYPE_ETHERNET:
        link_bytes, ethertype_at = 14, 12
    elif linktype == _LINKTYPE_LINUX_SLL:
        link_bytes, ethertype_at = 16, 14
    else:
        raise ValueError(f"unsupported link type {linktype}")
    packets: list[Packet] = []
    offset = 24
    while offset + 16 <= len(data):
        ts_sec, ts_frac, incl, _orig = struct.unpack(endian + "IIII", data[offset:offset + 16])
        frame = data[offset + 16:offset + 16 + incl]
        offset += 16 + incl
        if len(frame) < link_bytes + 20:
            continue
        if struct.unpack("!H", frame[ethertype_at:ethertype_at + 2])[0] != 0x0800:
            continue
        ip = frame[link_bytes:]
        ihl = (ip[0] & 0x0F) * 4
        total = struct.unpack("!H", ip[2:4])[0]
        proto = ip[9]
        body = ip[ihl:total]
        ts_ns = ts_sec * 1_000_000_000 + (ts_frac if nano else ts_frac * 1000)
        src, dst = _ip(ip[12:16]), _ip(ip[16:20])
        if proto == 6 and len(body) >= 20:
            sport, dport, seq = struct.unpack("!HHI", body[:8])
            data_offset = (body[12] >> 4) * 4
            packets.append(Packet(ts_ns, src, dst, proto, sport, dport, seq, body[13], body[data_offset:]))
        elif proto == 17 and len(body) >= 8:
            sport, dport, length = struct.unpack("!HHH", body[:6])
            packets.append(Packet(ts_ns, src, dst, proto, sport, dport, payload=body[8:length]))
    return packets


def parse_sd(packet: Packet) -> SdMessage | None:
    """The SD message of one UDP datagram; None when it is not a well-formed SD message."""
    raw = packet.payload
    if len(raw) < HEADER_BYTES + 12:
        return None
    service, method, length, _client, session = struct.unpack("!HHIHH", raw[:12])
    if service != SD_SERVICE or method != SD_METHOD or length + 8 != len(raw):
        return None
    sd = raw[HEADER_BYTES:]
    flags = sd[0]
    entries_length = struct.unpack("!I", sd[4:8])[0]
    if entries_length % 16 or 8 + entries_length + 4 > len(sd):
        return None
    options_length = struct.unpack("!I", sd[8 + entries_length:12 + entries_length])[0]
    options_raw = sd[12 + entries_length:12 + entries_length + options_length]
    if len(options_raw) != options_length:
        return None
    options: list[tuple[str, int, str] | None] = []
    position = 0
    while position < len(options_raw):
        if position + 3 > len(options_raw):
            return None
        option_length, option_type = struct.unpack("!HB", options_raw[position:position + 3])
        body = options_raw[position + 3:position + 3 + option_length]
        if len(body) != option_length:
            return None
        if option_type == 0x04 and option_length == 9:
            options.append((_ip(body[1:5]), struct.unpack("!H", body[7:9])[0], _L4.get(body[6], str(body[6]))))
        else:
            options.append(None)
        position += 3 + option_length
    entries = []
    for start in range(0, entries_length, 16):
        raw_entry = sd[8 + start:8 + start + 16]
        entry_type = raw_entry[0]
        endpoints = []
        for first, count in ((raw_entry[1], raw_entry[3] >> 4), (raw_entry[2], raw_entry[3] & 0x0F)):
            for index in range(first, first + count):
                if index >= len(options):
                    return None
                if options[index] is not None:
                    endpoints.append(options[index])
        eventgroup_entry = entry_type in _EVENTGROUP_ENTRIES
        entries.append(SdEntry(
            type=entry_type,
            type_name=SD_ENTRY_TYPES.get(entry_type, f"0x{entry_type:02x}"),
            service=struct.unpack("!H", raw_entry[4:6])[0],
            instance=struct.unpack("!H", raw_entry[6:8])[0],
            major=raw_entry[8],
            ttl=int.from_bytes(raw_entry[9:12], "big"),
            eventgroup=struct.unpack("!H", raw_entry[14:16])[0] if eventgroup_entry else None,
            minor=None if eventgroup_entry else struct.unpack("!I", raw_entry[12:16])[0],
            endpoints=endpoints,
        ))
    return SdMessage(packet.ts_ns, packet.src, packet.sport, packet.dst, packet.dport, session,
                     bool(flags & 0x80), bool(flags & 0x40), entries)


def _streams(packets: list[Packet]) -> list[TcpStream]:
    open_streams: dict[tuple, TcpStream] = {}
    streams: list[TcpStream] = []
    for packet in packets:
        if packet.proto != 6:
            continue
        key = (packet.src, packet.sport, packet.dst, packet.dport)
        syn = bool(packet.flags & 0x02)
        stream = open_streams.get(key)
        if stream is None or (syn and (stream._segments or stream.fin or stream.rst)):
            stream = TcpStream(len(streams), packet.src, packet.sport, packet.dst, packet.dport)
            open_streams[key] = stream
            streams.append(stream)
        stream.first_ts_ns = packet.ts_ns if stream.first_ts_ns is None else stream.first_ts_ns
        stream.last_ts_ns = packet.ts_ns
        if syn:
            stream.syn = True
            stream._isn = (packet.seq + 1) & 0xFFFFFFFF
        if packet.flags & 0x01 and stream.fin_ts_ns is None:
            stream.fin_ts_ns = packet.ts_ns
        if packet.flags & 0x04 and stream.rst_ts_ns is None:
            stream.rst_ts_ns = packet.ts_ns
        stream.fin |= bool(packet.flags & 0x01)
        stream.rst |= bool(packet.flags & 0x04)
        if packet.payload:
            if stream._isn is None:
                stream._isn = packet.seq
            relative = (packet.seq - stream._isn) & 0xFFFFFFFF
            stream._segments.append((relative, packet.ts_ns, packet.payload))
    return streams


def _reassemble(stream: TcpStream) -> tuple[bytes, list[tuple[int, int]]]:
    buffer = bytearray()
    marks: list[tuple[int, int]] = []
    for relative, ts_ns, payload in sorted(stream._segments, key=lambda s: (s[0], s[1])):
        end = relative + len(payload)
        if end <= len(buffer):
            continue  # a retransmission of bytes already placed
        if relative > len(buffer):
            stream.gaps.append(len(buffer))
            break  # never guess across a hole
        marks.append((len(buffer), ts_ns))
        buffer.extend(payload[len(buffer) - relative:])
    return bytes(buffer), marks


def _ts_at(marks: list[tuple[int, int]], offset: int) -> int:
    ts = marks[0][1] if marks else 0
    for start, stamp in marks:
        if start <= offset:
            ts = stamp
        else:
            break
    return ts


def split_someip(raw: bytes, *, ts_marks: list[tuple[int, int]], base: dict) -> tuple[list[SomeipMessage], int]:
    """The complete SOME/IP messages of a byte stream and the count of bytes left over.

    A message's time is the time of the segment that held its last byte.
    """
    messages = []
    offset = 0
    while offset + HEADER_BYTES <= len(raw):
        service, method, length = struct.unpack("!HHI", raw[offset:offset + 8])
        if length < 8 or offset + 8 + length > len(raw):
            break
        client, session = struct.unpack("!HH", raw[offset + 8:offset + 12])
        protocol_version, interface_version, message_type, return_code = raw[offset + 12:offset + 16]
        end = offset + 8 + length
        if not (service == SD_SERVICE and method in (0x0000, 0x8000)):  # magic cookies carry no data
            messages.append(SomeipMessage(
                ts_ns=_ts_at(ts_marks, end - 1), service=service, method=method, client=client, session=session,
                protocol_version=protocol_version, interface_version=interface_version, message_type=message_type,
                return_code=return_code, payload=raw[offset + HEADER_BYTES:end],
                src=base.get("src", ""), sport=base.get("sport", 0), dst=base.get("dst", ""),
                dport=base.get("dport", 0), connection=base.get("connection", 0)))
        offset = end
    return messages, len(raw) - offset


def analyse_capture(path: Path | str) -> CaptureAnalysis:
    packets = read_packets(path)
    sd_messages = []
    malformed = 0
    for packet in packets:
        if packet.proto == 17 and SD_PORT in (packet.sport, packet.dport):
            message = parse_sd(packet)
            if message is None:
                malformed += 1
            else:
                sd_messages.append(message)
    streams = _streams(packets)
    for stream in streams:
        raw, marks = _reassemble(stream)
        stream.byte_count = len(raw)
        base = {"src": stream.src, "sport": stream.sport, "dst": stream.dst, "dport": stream.dport,
                "connection": stream.index}
        stream.messages, stream.trailing_bytes = split_someip(raw, ts_marks=marks, base=base)
    return CaptureAnalysis(len(packets), sd_messages, malformed, streams)
