"""DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.

Minimal, dependency-free reader for the guest-side capture: classic pcap
(micro- or nanosecond), Ethernet II, IPv4, TCP and UDP. It reassembles each
TCP direction by sequence number and splits the byte stream into SOME/IP
messages (16-byte header, no magic cookies), and decodes the SOME/IP-SD
entries of UDP port 30490. It is evidence tooling for one capture of a
known topology, not a general dissector.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

SD_PORT = 30490
SD_SERVICE = 0xFFFF
SD_METHOD = 0x8100

SD_ENTRY_TYPES = {
    0x00: "FindService",
    0x01: "OfferService",
    0x06: "SubscribeEventgroup",
    0x07: "SubscribeEventgroupAck",
}

MESSAGE_TYPES = {
    0x00: "REQUEST",
    0x01: "REQUEST_NO_RETURN",
    0x02: "NOTIFICATION",
    0x80: "RESPONSE",
    0x81: "ERROR",
}


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
class SomeipMessage:
    ts_ns: int
    src: str
    dst: str
    transport: str
    sport: int
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

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    def describe(self) -> dict:
        return {
            "ts_ns": self.ts_ns,
            "src": f"{self.src}:{self.sport}",
            "dst": f"{self.dst}:{self.dport}",
            "transport": self.transport,
            "service": f"0x{self.service:04x}",
            "method": f"0x{self.method:04x}",
            "message_type": MESSAGE_TYPES.get(self.message_type, f"0x{self.message_type:02x}"),
            "return_code": self.return_code,
            "payload_len": len(self.payload),
        }


def _ip(raw: bytes) -> str:
    return ".".join(str(b) for b in raw)


def read_packets(path: Path) -> list[Packet]:
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
    linktype = struct.unpack(endian + "I", data[20:24])[0]
    if linktype != 1:
        raise ValueError(f"unsupported link type {linktype}")
    packets = []
    offset = 24
    while offset + 16 <= len(data):
        ts_sec, ts_frac, incl, _orig = struct.unpack(endian + "IIII", data[offset:offset + 16])
        frame = data[offset + 16:offset + 16 + incl]
        offset += 16 + incl
        ts_ns = ts_sec * 1_000_000_000 + (ts_frac if nano else ts_frac * 1000)
        if len(frame) < 14:
            continue
        ethertype = struct.unpack("!H", frame[12:14])[0]
        if ethertype != 0x0800:
            continue
        ip = frame[14:]
        if len(ip) < 20:
            continue
        ihl = (ip[0] & 0x0F) * 4
        total = struct.unpack("!H", ip[2:4])[0]
        proto = ip[9]
        src, dst = _ip(ip[12:16]), _ip(ip[16:20])
        body = ip[ihl:total]
        if proto == 6 and len(body) >= 20:
            sport, dport, seq, _ack = struct.unpack("!HHII", body[:12])
            data_offset = (body[12] >> 4) * 4
            flags = body[13]
            packets.append(Packet(ts_ns, src, dst, proto, sport, dport, seq, flags, body[data_offset:]))
        elif proto == 17 and len(body) >= 8:
            sport, dport, length = struct.unpack("!HHH", body[:6])
            packets.append(Packet(ts_ns, src, dst, proto, sport, dport, payload=body[8:length]))
    return packets


@dataclass
class TcpStream:
    src: str
    sport: int
    dst: str
    dport: int
    isn: int | None = None
    segments: list = field(default_factory=list)  # (relative offset, ts_ns, bytes)
    syn_seen: bool = False
    fin_seen: bool = False
    rst_seen: bool = False

    def key(self) -> str:
        return f"{self.src}:{self.sport}->{self.dst}:{self.dport}"


def tcp_streams(packets: list[Packet]) -> list[TcpStream]:
    """One stream per direction and connection; a new SYN starts a new stream."""
    open_streams: dict[tuple, TcpStream] = {}
    streams: list[TcpStream] = []
    for packet in packets:
        if packet.proto != 6:
            continue
        key = (packet.src, packet.sport, packet.dst, packet.dport)
        syn = bool(packet.flags & 0x02)
        stream = open_streams.get(key)
        if stream is None or (syn and stream.segments):
            stream = TcpStream(packet.src, packet.sport, packet.dst, packet.dport)
            open_streams[key] = stream
            streams.append(stream)
        if syn:
            stream.syn_seen = True
            stream.isn = (packet.seq + 1) & 0xFFFFFFFF
        if packet.flags & 0x01:
            stream.fin_seen = True
        if packet.flags & 0x04:
            stream.rst_seen = True
        if packet.payload:
            if stream.isn is None:
                stream.isn = packet.seq
            relative = (packet.seq - stream.isn) & 0xFFFFFFFF
            stream.segments.append((relative, packet.ts_ns, packet.payload))
    return streams


def reassemble(stream: TcpStream) -> tuple[bytes, list[tuple[int, int]], list[int]]:
    """Returns the contiguous byte stream, (offset, ts_ns) marks and the gap offsets."""
    buffer = bytearray()
    marks: list[tuple[int, int]] = []
    gaps: list[int] = []
    for relative, ts_ns, payload in sorted(stream.segments, key=lambda s: (s[0], s[1])):
        end = relative + len(payload)
        if end <= len(buffer):
            continue  # retransmission of bytes already placed
        if relative > len(buffer):
            gaps.append(len(buffer))
            break  # do not guess across a hole
        buffer.extend(payload[len(buffer) - relative:])
        marks.append((relative, ts_ns))
    return bytes(buffer), marks, gaps


def _ts_at(marks: list[tuple[int, int]], offset: int) -> int:
    ts = marks[0][1] if marks else 0
    for start, stamp in marks:
        if start <= offset:
            ts = stamp
        else:
            break
    return ts


def split_someip(raw: bytes, base: dict, marks: list[tuple[int, int]]) -> tuple[list[SomeipMessage], int]:
    messages = []
    offset = 0
    while offset + 16 <= len(raw):
        service, method, length = struct.unpack("!HHI", raw[offset:offset + 8])
        if length < 8 or offset + 8 + length > len(raw):
            break
        client, session = struct.unpack("!HH", raw[offset + 8:offset + 12])
        proto_v, iface_v, msg_type, rc = raw[offset + 12:offset + 16]
        payload = raw[offset + 16:offset + 8 + length]
        messages.append(SomeipMessage(_ts_at(marks, offset + 8 + length - 1), payload=payload, service=service,
                                      method=method, client=client, session=session, protocol_version=proto_v,
                                      interface_version=iface_v, message_type=msg_type, return_code=rc, **base))
        offset += 8 + length
    return messages, len(raw) - offset


def sd_entries(packet: Packet) -> list[dict]:
    raw = packet.payload
    if len(raw) < 28:
        return []
    service, method = struct.unpack("!HH", raw[:4])
    if service != SD_SERVICE or method != SD_METHOD:
        return []
    sd = raw[16:]
    entries_len = struct.unpack("!I", sd[4:8])[0]
    entries = sd[8:8 + entries_len]
    result = []
    for i in range(0, len(entries) - 15, 16):
        entry = entries[i:i + 16]
        entry_type = entry[0]
        svc, inst = struct.unpack("!HH", entry[4:8])
        major = entry[8]
        ttl = int.from_bytes(entry[9:12], "big")
        item = {
            "ts_ns": packet.ts_ns,
            "src": f"{packet.src}:{packet.sport}",
            "dst": f"{packet.dst}:{packet.dport}",
            "type": SD_ENTRY_TYPES.get(entry_type, f"0x{entry_type:02x}"),
            "service": f"0x{svc:04x}",
            "instance": f"0x{inst:04x}",
            "major": major,
            "ttl": ttl,
        }
        if entry_type in (0x06, 0x07):
            item["eventgroup"] = f"0x{struct.unpack('!H', entry[14:16])[0]:04x}"
            item["stop"] = ttl == 0
        elif entry_type == 0x01:
            item["stop"] = ttl == 0
        result.append(item)
    return result


def analyse(path: Path) -> dict:
    """Everything the spike needs from one capture."""
    packets = read_packets(path)
    result: dict = {"packets": len(packets), "streams": [], "messages": [], "sd": [], "udp_other": 0}
    for stream in tcp_streams(packets):
        raw, marks, gaps = reassemble(stream)
        base = {"src": stream.src, "dst": stream.dst, "sport": stream.sport, "dport": stream.dport,
                "transport": "tcp"}
        messages, trailing = split_someip(raw, base, marks)
        result["streams"].append({
            "key": stream.key(), "bytes": len(raw), "messages": len(messages), "gaps": gaps,
            "trailing_bytes": trailing, "syn": stream.syn_seen, "fin": stream.fin_seen, "rst": stream.rst_seen,
            "first_ts_ns": marks[0][1] if marks else None,
        })
        result["messages"].extend(messages)
    for packet in packets:
        if packet.proto != 17:
            continue
        if SD_PORT in (packet.sport, packet.dport):
            result["sd"].extend(sd_entries(packet))
        else:
            result["udp_other"] += 1
            base = {"src": packet.src, "dst": packet.dst, "sport": packet.sport, "dport": packet.dport,
                    "transport": "udp"}
            messages, _ = split_someip(packet.payload, base, [(0, packet.ts_ns)])
            result["messages"].extend(messages)
    result["messages"].sort(key=lambda m: m.ts_ns)
    return result
