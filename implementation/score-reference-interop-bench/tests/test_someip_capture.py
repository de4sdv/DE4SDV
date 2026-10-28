"""Tests of the capture reader of the bench: classic pcap, IPv4, TCP and UDP;
SOME/IP-SD entries with their options; SOME/IP messages of each TCP
connection after reassembly.

The fixture is a compact cut of a retained guest capture of the gateway
spike (someip-receiver/test/fixtures/README.md): someipd with vsomeip 3.6.1
and a vsomeip 3.7.6 client, across a restart of the gateway pair. The
expected values below were read from the same packets with the spike's own
reader.
"""

from pathlib import Path
import struct
import sys

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.someip_capture import analyse_capture, read_packets, split_someip  # noqa: E402

PCAP = BENCH / "someip-receiver" / "test" / "fixtures" / "someip_guest_wire_pair_restart.pcap"
HOST = "10.250.0.1"
GUEST = "10.250.0.2"


@pytest.fixture(scope="module")
def capture():
    return analyse_capture(PCAP)


def test_packets_are_read_with_nanosecond_timestamps():
    packets = read_packets(PCAP)
    assert len(packets) == 45
    assert packets[0].ts_ns == 1793116443934013818
    assert all(packet.ts_ns >= packets[0].ts_ns for packet in packets)


def test_sd_entries_by_type(capture):
    kinds = [(entry.type_name, entry.ttl) for message in capture.sd_messages for entry in message.entries]
    assert kinds.count(("OfferService", 3)) == 4
    assert kinds.count(("SubscribeEventgroup", 3)) == 5
    assert kinds.count(("SubscribeEventgroupAck", 3)) == 4
    assert kinds.count(("SubscribeEventgroupAck", 0)) == 1  # the Nack
    assert kinds.count(("SubscribeEventgroup", 0)) == 1  # the StopSubscribe
    assert len(kinds) == 15


def test_offer_carries_flags_session_and_tcp_endpoint(capture):
    offer = capture.sd_messages[0]
    assert (offer.src, offer.dst, offer.multicast) == (HOST, "224.244.224.245", True)
    assert offer.session == 1 and offer.reboot and offer.unicast_flag
    entry = offer.entries[0]
    assert (entry.service, entry.instance, entry.major) == (0x4DEE, 0x0001, 1)
    assert entry.endpoints == [(HOST, 30509, "tcp")]


def test_subscribe_names_the_local_tcp_endpoint_of_the_client(capture):
    subscribes = [m for m in capture.sd_messages if m.entries[0].type_name == "SubscribeEventgroup"]
    first = subscribes[0]
    assert (first.src, first.dst, first.multicast) == (GUEST, HOST, False)
    assert first.entries[0].eventgroup == 0x0001
    assert first.entries[0].endpoints == [(GUEST, 35005, "tcp")]
    # After the pair restart the client subscribes from its new connection.
    assert subscribes[-1].entries[0].endpoints == [(GUEST, 46707, "tcp")]


def test_nack_comes_from_the_restarted_someipd_with_session_one(capture):
    nacks = [m for m in capture.sd_messages
             if m.entries[0].type_name == "SubscribeEventgroupAck" and m.entries[0].ttl == 0]
    assert len(nacks) == 1
    assert nacks[0].session == 1 and nacks[0].reboot


def test_tcp_connections_and_their_notifications(capture):
    server_streams = [s for s in capture.streams if s.src == HOST and s.sport == 30509 and s.messages]
    assert [(s.dport, len(s.messages), s.byte_count, s.gaps) for s in server_streams] == [
        (35005, 3, 3616, []), (46707, 5, 5548, [])]
    first = server_streams[0]
    assert first.fin and first.rst
    sizes = [len(message.payload) for message in first.messages]
    assert sizes == [2048, 20, 1500]
    message = first.messages[0]
    assert (message.service, message.method, message.message_type, message.session) == (0x4DEE, 0x8001, 0x02, 1)


def test_notifications_are_in_time_order_with_the_time_of_their_segment(capture):
    notifications = capture.notifications(HOST, 30509)
    assert len(notifications) == 8
    assert [n.ts_ns for n in notifications] == sorted(n.ts_ns for n in notifications)
    packets = read_packets(PCAP)
    carrying = [p for p in packets if p.proto == 6 and p.sport == 30509 and p.payload]
    assert [n.ts_ns for n in notifications] == [p.ts_ns for p in carrying]


def _pcap(segments: list[tuple[int, int, bytes, int]]) -> bytes:
    """A nanosecond pcap of TCP segments (ts_ns, seq, payload, flags) from 10.250.0.1:30509 to 10.250.0.2:40000."""
    out = struct.pack("<IHHiIII", 0xA1B23C4D, 2, 4, 0, 0, 262144, 1)
    for ts_ns, seq, payload, flags in segments:
        tcp = struct.pack("!HHIIBBHHH", 30509, 40000, seq, 0, 5 << 4, flags, 65535, 0, 0) + payload
        ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp), 0, 0, 64, 6, 0, bytes([10, 250, 0, 1]),
                         bytes([10, 250, 0, 2])) + tcp
        frame = b"\x00" * 12 + b"\x08\x00" + ip
        out += struct.pack("<IIII", ts_ns // 1_000_000_000, ts_ns % 1_000_000_000, len(frame), len(frame)) + frame
    return out


def _message(session: int, payload: bytes) -> bytes:
    return struct.pack("!HHIHHBBBB", 0x4DEE, 0x8001, 8 + len(payload), 0, session, 1, 1, 2, 0) + payload


def test_retransmitted_and_reordered_segments_give_each_message_once(tmp_path):
    one, two = _message(1, b"\x11" * 30), _message(2, b"\x22" * 30)
    stream = one + two
    path = tmp_path / "retransmission.pcap"
    path.write_bytes(_pcap([
        (1_000, 0, b"", 0x02),                       # SYN, sequence 0 -> data starts at 1
        (2_000, 1 + 20, stream[20:50], 0x18),        # arrives before the bytes in front of it
        (3_000, 1, stream[:20], 0x18),
        (4_000, 1, stream[:50], 0x18),               # retransmission of bytes already placed
        (5_000, 1 + 50, stream[50:], 0x18),
    ]))
    analysis = analyse_capture(path)
    messages = analysis.notifications("10.250.0.1", 30509)
    assert [m.session for m in messages] == [1, 2]
    assert analysis.streams[0].gaps == []


def test_a_hole_in_the_stream_stops_the_reassembly(tmp_path):
    stream = _message(1, b"\x11" * 30) + _message(2, b"\x22" * 30)
    path = tmp_path / "hole.pcap"
    path.write_bytes(_pcap([(1_000, 0, b"", 0x02), (2_000, 1, stream[:46], 0x18), (3_000, 1 + 50, stream[50:], 0x18)]))
    analysis = analyse_capture(path)
    assert [m.session for m in analysis.notifications("10.250.0.1", 30509)] == [1]
    assert analysis.streams[0].gaps == [46]


def test_split_keeps_trailing_bytes_of_a_cut_message():
    message = struct.pack("!HHIHHBBBB", 0x4DEE, 0x8001, 8 + 4, 0, 7, 1, 1, 2, 0) + b"\x01\x02\x03\x04"
    messages, trailing = split_someip(message + message[:10], ts_marks=[(0, 5)], base={})
    assert len(messages) == 1 and trailing == 10
    assert messages[0].payload == b"\x01\x02\x03\x04"


def test_magic_cookies_are_skipped():
    cookie = struct.pack("!HHIHHBBBB", 0xFFFF, 0x8000, 8, 0xDEAD, 0xBEEF, 1, 1, 2, 0)
    message = struct.pack("!HHIHHBBBB", 0x4DEE, 0x8001, 8 + 1, 0, 7, 1, 1, 2, 0) + b"\x09"
    messages, trailing = split_someip(cookie + message, ts_marks=[(0, 5)], base={})
    assert [m.payload for m in messages] == [b"\x09"] and trailing == 0
