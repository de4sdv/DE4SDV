"""Builders of synthetic classic pcap captures and frames for the evaluator tests.

No binary fixture is committed: each test builds exactly the bytes it needs,
so the inputs stay diffable and reviewable. The builders write Ethernet +
IPv4 + TCP/UDP, the shapes the bench captures.
"""

from __future__ import annotations

import json
import struct

PCAP_MAGIC_NS = b"\x4d\x3c\xb2\xa1"  # little-endian, nanosecond
LINKTYPE_ETHERNET = 1


def _global_header(linktype: int = LINKTYPE_ETHERNET) -> bytes:
    return PCAP_MAGIC_NS + struct.pack("<HHiIII", 2, 4, 0, 0, 262144, linktype)


def _record(ts_ns: int, data: bytes) -> bytes:
    return struct.pack("<IIII", ts_ns // 1_000_000_000, ts_ns % 1_000_000_000, len(data), len(data)) + data


def _ipv4(src: str, dst: str, protocol: int, payload: bytes) -> bytes:
    def addr(text: str) -> bytes:
        return bytes(int(part) for part in text.split("."))

    total = 20 + len(payload)
    header = struct.pack(">BBHHHBBH", 0x45, 0, total, 0, 0x4000, 64, protocol, 0) + addr(src) + addr(dst)
    return header + payload


DEFAULT_SRC_MAC = "02:00:00:00:00:01"


def _mac(text: str) -> bytes:
    return bytes(int(part, 16) for part in text.split(":"))


def _ethernet(payload: bytes, ethertype: int = 0x0800, vlans: tuple[int, ...] = (),
              src_mac: str = DEFAULT_SRC_MAC) -> bytes:
    frame = b"\x02\x00\x00\x00\x00\x02" + _mac(src_mac)
    for vlan in vlans:
        frame += struct.pack(">HH", 0x8100, vlan)
    frame += struct.pack(">H", ethertype) + payload
    return frame


def tcp_segment(src: str, dst: str, sport: int, dport: int, seq: int, ack: int, flags: int,
                payload: bytes = b"", src_mac: str = DEFAULT_SRC_MAC) -> bytes:
    header = struct.pack(">HHIIBBHHH", sport, dport, seq, ack, 0x50, flags, 65535, 0, 0)
    return _ethernet(_ipv4(src, dst, 6, header + payload), src_mac=src_mac)


def udp_datagram(src: str, dst: str, sport: int, dport: int, payload: bytes, vlans: tuple[int, ...] = (),
                 src_mac: str = DEFAULT_SRC_MAC) -> bytes:
    header = struct.pack(">HHHH", sport, dport, 8 + len(payload), 0)
    return _ethernet(_ipv4(src, dst, 17, header + payload), vlans=vlans, src_mac=src_mac)


def pcap(records: list[tuple[int, bytes]], linktype: int = LINKTYPE_ETHERNET) -> bytes:
    return _global_header(linktype) + b"".join(_record(ts_ns, data) for ts_ns, data in records)


FIN, SYN, RST, PSH, ACK = 0x01, 0x02, 0x04, 0x08, 0x10


class TcpSender:
    """Builds the records of one server-to-client TCP stream, with a SYN handshake."""

    def __init__(self, client: str, server: str, cport: int, sport: int, t0_ns: int = 1_000_000_000) -> None:
        self.client, self.server, self.cport, self.sport = client, server, cport, sport
        self.cseq, self.sseq = 1000, 5000
        self.t = t0_ns
        self.records: list[tuple[int, bytes]] = []

    def _tick(self, step_ns: int = 10_000_000) -> int:
        self.t += step_ns
        return self.t

    def handshake(self) -> "TcpSender":
        self.records.append((self._tick(), tcp_segment(self.client, self.server, self.cport, self.sport,
                                                        self.cseq, 0, SYN)))
        self.cseq += 1
        self.records.append((self._tick(), tcp_segment(self.server, self.client, self.sport, self.cport,
                                                        self.sseq, self.cseq, SYN | ACK)))
        self.sseq += 1
        self.records.append((self._tick(), tcp_segment(self.client, self.server, self.cport, self.sport,
                                                        self.cseq, self.sseq, ACK)))
        return self

    def send(self, payload: bytes, step_ns: int = 10_000_000) -> "TcpSender":
        self.records.append((self._tick(step_ns), tcp_segment(self.server, self.client, self.sport, self.cport,
                                                              self.sseq, self.cseq, PSH | ACK, payload)))
        self.sseq += len(payload)
        return self

    def raw(self, seq: int, payload: bytes, step_ns: int = 10_000_000) -> "TcpSender":
        """A server segment at an explicit sequence, for gaps and retransmissions."""
        self.records.append((self._tick(step_ns), tcp_segment(self.server, self.client, self.sport, self.cport,
                                                              seq, self.cseq, PSH | ACK, payload)))
        return self

    def fin(self) -> "TcpSender":
        """The server (relay) closes the stream: a FIN from the server port."""
        self.records.append((self._tick(), tcp_segment(self.server, self.client, self.sport, self.cport,
                                                        self.sseq, self.cseq, FIN | ACK)))
        return self

    def client_fin(self) -> "TcpSender":
        """The client (ingress) closes the stream: a FIN from the client port."""
        self.records.append((self._tick(), tcp_segment(self.client, self.server, self.cport, self.sport,
                                                        self.cseq, self.sseq, FIN | ACK)))
        return self


def _varint(value: int) -> bytes:
    if value < 0:  # protobuf encodes a negative int64 as its 64-bit two's complement
        value &= (1 << 64) - 1
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _field(number: int, wire: int, body: bytes) -> bytes:
    prefix = _varint((number << 3) | wire)
    if wire == 2:  # length-delimited: the length comes before the body
        return prefix + _varint(len(body)) + body
    return prefix + body


def _field_value(number: int, source_kind: int, *, boolean: bool | None = None, enum: str | None = None,
                 numeric: float | None = None) -> bytes:
    body = _field(1, 0, _varint(source_kind)) + _field(2, 0, _varint(1_000)) + _field(3, 2, b"m") + _field(4, 2, b"")
    if boolean is not None:
        body += _field(6, 0, _varint(1 if boolean else 0))
    if enum is not None:
        body += _field(7, 2, enum.encode())
    if numeric is not None:
        body += _field(5, 1, struct.pack("<d", numeric))
    return _field(number, 2, body)


def frame(sequence: int, timestamp_ns: int, *, stage: str = "MONITORING") -> bytes:
    """A VisualizationFrame with the fields the evaluators read, and correct source kinds."""
    body = _field(1, 0, _varint(1)) + _field(2, 0, _varint(1)) + _field(3, 0, _varint(sequence))
    body += _field(4, 0, _varint(timestamp_ns)) + _field(6, 2, b"bench")
    body += _field_value(7, 1, numeric=12.0)  # rss_distance, native
    body += _field_value(9, 3, numeric=20.0)  # target_range, display-derived
    warning = stage == "WARNING"
    intervention = stage == "INTERVENTION"
    body += _field_value(11, 2, boolean=warning or intervention)       # warning request
    body += _field_value(12, 2, boolean=intervention)                  # braking request
    body += _field_value(8, 1, boolean=intervention)                   # native intervention
    lifecycle = "released_verified_stop" if stage == "RELEASED" else "armed"
    body += _field_value(13, 2, enum=lifecycle)
    return body


def delimited(payload: bytes) -> bytes:
    return struct.pack("<I", len(payload)) + payload


def stream_records(port: int, payloads, *, t0: int, step: int = 100_000_000, cport: int | None = None,
                   drop_index: int | None = None, client: str = "127.0.0.1", server: str = "127.0.0.1",
                   close: str | None = "client"):
    """The pcap records of one length-delimited stream of frames.

    ``drop_index`` drops the Nth data segment (the capture missed it); the
    three handshake records come first. ``close`` names who closes the stream
    at the end: "client" (the ingress, the default: a cleanly closed stream
    that no relay close ends), "server" (the relay, from its port) or None
    (the capture is cut while the stream is open).
    """
    sender = TcpSender(client, server, cport or port + 1000, port, t0).handshake()
    for payload in payloads:
        sender.send(delimited(payload), step_ns=step)
    if close == "server":
        sender.fin()
    elif close == "client":
        sender.client_fin()
    records = sender.records
    if drop_index is not None:
        records = records[:3 + drop_index] + records[4 + drop_index:]
    return records


# A neutral tag for the evaluator tests: the evaluators read the tag from the
# run settings, so any tag shows that they do not depend on the real one.
RELAY_TAG = "relay_under_test"


def logcat_line(ts_ns: int, event: dict, tag: str = RELAY_TAG, pid: int = 1234) -> str:
    sec, frac = divmod(ts_ns, 1_000_000_000)
    body = dict(event)
    body.setdefault("monotonic_ns", ts_ns)
    body.setdefault("realtime_ns", ts_ns)
    return f"{sec}.{frac // 1000:06d}  1000  {pid}  1250 I {tag}: {json.dumps(body, separators=(',', ':'))}"


def phase_start_line(at_ns: int, phase: int = 1, pid: int = 1234, cause: str = "client_connected") -> str:
    return logcat_line(at_ns, {"event": "phase_start", "cause": cause, "phase": phase,
                               "phase_start_realtime_ns": at_ns, "subscription": phase}, pid=pid)


def phase_end_line(at_ns: int, start_ns: int, *, phase: int = 1, pid: int = 1234, layer_caused: bool,
                   client_connected: bool, cause: str, clock_steps: int = 0) -> str:
    return logcat_line(at_ns, {"event": "phase_end", "cause": cause, "layer_caused": layer_caused,
                               "client_connected": client_connected, "phase": phase,
                               "phase_start_realtime_ns": start_ns, "subscription": phase,
                               "clock_steps_in_phase": clock_steps}, pid=pid)


def clock_step_line(at_ns: int, *, in_phase: bool, step_ns: int = 250_000_000, pid: int = 1234) -> str:
    return logcat_line(at_ns, {"event": "clock_step", "step_ns": step_ns,
                               "realtime_minus_monotonic_ns": 5, "in_phase": in_phase}, pid=pid)


def data_loss_line(at_ns: int, *, subscription: int = 1, pid: int = 1234) -> str:
    return logcat_line(at_ns, {"event": "data_loss", "subscription": subscription, "data_loss_reads": 1}, pid=pid)


_NTP_TO_UNIX_S = 2_208_988_800


def _ntp_ts(unix_ns: int) -> bytes:
    seconds = unix_ns // 1_000_000_000 + _NTP_TO_UNIX_S
    fraction = (unix_ns % 1_000_000_000) * (1 << 32) // 1_000_000_000
    return struct.pack(">II", seconds, fraction)


def clock_pcap(offset_ns: int, at_ns: int, marker: int = 0x1234, one_way_ns: int = 500_000) -> bytes:
    """A guest NTP capture with a known offset (guest - host) and symmetric delay."""
    t1 = at_ns
    t2 = t1 - offset_ns + one_way_ns
    t4 = t1 + 2 * one_way_ns
    request = bytes([0x23]) + bytes(39) + struct.pack(">Q", marker)
    response = bytes([0x24]) + bytes(23) + struct.pack(">Q", marker) + _ntp_ts(t2) + _ntp_ts(t2)
    return pcap([(t1, udp_datagram("192.168.98.118", "192.168.98.1", 40000, 123, request)),
                 (t4, udp_datagram("192.168.98.1", "192.168.98.118", 123, 40000, response))])


# ------------------------------------------------------------ SOME/IP-SD

SD_PORT = 30490
SD_OFFER, SD_SUBSCRIBE = 0x01, 0x06


def sd_entry(entry_type: int, service: int, instance: int, *, major: int = 1, ttl: int = 3,
             eventgroup: int | None = None, first_option: int = 0, options: int = 0) -> bytes:
    """One 16-byte SOME/IP-SD entry: a service entry, or an eventgroup entry when eventgroup is set."""
    head = struct.pack(">BBBBHHB", entry_type, first_option, 0, (options & 0x0F) << 4, service, instance, major)
    head += ttl.to_bytes(3, "big")
    tail = struct.pack(">I", 0) if eventgroup is None else struct.pack(">HH", 0, eventgroup)
    return head + tail


def sd_ipv4_endpoint(address: str, port: int, protocol: int = 0x06) -> bytes:
    """An IPv4 Endpoint option (type 0x04)."""
    raw = bytes(int(part) for part in address.split("."))
    return struct.pack(">HBB", 9, 0x04, 0) + raw + struct.pack(">BBH", 0, protocol, port)


def sd_message(entries: list[bytes], options: list[bytes] = (), *, session: int = 1, flags: int = 0xC0) -> bytes:
    """A SOME/IP-SD message: the SOME/IP header (service 0xFFFF, method 0x8100) and the SD payload."""
    entries_raw, options_raw = b"".join(entries), b"".join(options)
    payload = struct.pack(">B3x", flags) + struct.pack(">I", len(entries_raw)) + entries_raw
    payload += struct.pack(">I", len(options_raw)) + options_raw
    header = struct.pack(">HHI", 0xFFFF, 0x8100, 8 + len(payload)) + struct.pack(">HHBBBB", 0, session, 1, 1, 2, 0)
    return header + payload


# ------------------------------------------------------------ Data Tunnel on VLAN 2 (cleartext HTTP/2)
#
# In the UNLOCKED mode Data Tunnel runs as gRPC over cleartext HTTP/2 on VLAN
# 2: the IVI VM's agent opens the connection to the SDV Core VM's agent with
# the HTTP/2 preface and a HEADERS frame per stream, and the core streams the
# publication's messages back as DATA frames on that stream (design data from
# the spike's VLAN 2 captures). A message carries the frame bytes as the
# ingress later receives them, so the evaluator finds a frame by its bytes.

H2_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
H2_DATA, H2_HEADERS, H2_SETTINGS = 0x0, 0x1, 0x4
DT_IVI, DT_CORE = ("192.168.100.4", 7490), ("192.168.100.3", 6335)


def h2_frame(frame_type: int, flags: int, stream_id: int, payload: bytes) -> bytes:
    return len(payload).to_bytes(3, "big") + bytes([frame_type, flags]) + struct.pack(">I", stream_id) + payload


def grpc_message(body: bytes) -> bytes:
    return b"\x00" + struct.pack(">I", len(body)) + body


def dt_message(frame_payload: bytes) -> bytes:
    """A Data Tunnel message: some protobuf framing around the frame bytes (as the slot carries them)."""
    return grpc_message(b"\x0a\x04topic\x12" + _varint(len(frame_payload) + 4) + delimited(frame_payload))


class DtConnection:
    """One VLAN 2 TCP connection, IVI agent (client) to core agent (server), both directions."""

    def __init__(self, t0_ns: int, *, client=DT_IVI, server=DT_CORE) -> None:
        self.client, self.server = client, server
        self.cseq, self.sseq = 7000, 9000
        self.t = t0_ns
        self.records: list[tuple[int, bytes]] = []

    def _segment(self, from_client: bool, flags: int, payload: bytes, at_ns: int | None) -> "DtConnection":
        self.t = at_ns if at_ns is not None else self.t + 1_000_000
        src, dst = (self.client, self.server) if from_client else (self.server, self.client)
        seq, ack = (self.cseq, self.sseq) if from_client else (self.sseq, self.cseq)
        self.records.append((self.t, tcp_segment(src[0], dst[0], src[1], dst[1], seq, ack, flags, payload)))
        if from_client:
            self.cseq += len(payload) + (1 if flags & (SYN | FIN) else 0)
        else:
            self.sseq += len(payload) + (1 if flags & (SYN | FIN) else 0)
        return self

    def handshake(self) -> "DtConnection":
        self._segment(True, SYN, b"", None)
        self._segment(False, SYN | ACK, b"", None)
        return self._segment(True, ACK, b"", None)

    def open_stream(self, stream_id: int, at_ns: int | None = None, *, preface: bool = False) -> "DtConnection":
        """The client's request: the preface and SETTINGS on the first stream, then HEADERS."""
        head = (H2_PREFACE + h2_frame(H2_SETTINGS, 0, 0, b"")) if preface else b""
        headers = h2_frame(H2_HEADERS, 0x04, stream_id, b"\x40\x05:path\x0aSdvDtAgent")
        return self._segment(True, PSH | ACK, head + headers, at_ns)

    def server_settings(self) -> "DtConnection":
        return self._segment(False, PSH | ACK, h2_frame(H2_SETTINGS, 0, 0, b""), None)

    def data(self, stream_id: int, frame_payload: bytes, at_ns: int) -> "DtConnection":
        """The core sends one message of the stream, carrying one frame."""
        return self._segment(False, PSH | ACK, h2_frame(H2_DATA, 0, stream_id, dt_message(frame_payload)), at_ns)


def dt_capture(connections: list[DtConnection]) -> bytes:
    records = sorted(record for connection in connections for record in connection.records)
    return pcap(records)
