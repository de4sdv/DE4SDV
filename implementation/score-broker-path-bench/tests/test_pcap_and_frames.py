"""Tests of the pcap reader, the TCP reassembler and the frame decoder."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
from de4sdv_broker_path_bench import frames  # noqa: E402
from de4sdv_broker_path_bench.pcap import PcapError, read_pcap, tcp_streams  # noqa: E402


def _streams(records, port):
    from de4sdv_broker_path_bench.pcap import datagrams
    capture = read_pcap(_write(b.pcap(records)))
    return capture, tcp_streams(datagrams(capture), port)


_TMP = []


def _write(data: bytes) -> str:
    import tempfile
    handle = tempfile.NamedTemporaryFile(suffix=".pcap", delete=False)
    handle.write(data)
    handle.close()
    _TMP.append(handle.name)
    return handle.name


def test_pcapng_is_refused() -> None:
    path = _write(b"\x0a\x0d\x0d\x0a" + b"\x00" * 40)
    with pytest.raises(PcapError):
        read_pcap(path)


def test_a_short_global_header_is_refused() -> None:
    path = _write(b"\x4d\x3c\xb2\xa1\x00\x00")
    with pytest.raises(PcapError):
        read_pcap(path)


def test_a_truncated_record_is_reported_not_raised() -> None:
    full = b.pcap([(1_000_000_000, b.udp_datagram("192.168.98.3", "192.168.98.1", 4790, 30490, b"x"))])
    capture = read_pcap(_write(full + b"\x00\x00\x00\x00\x05"))
    assert capture.truncated
    assert len(capture.packets) == 1


def test_tcp_stream_reassembles_server_bytes_in_order() -> None:
    sender = b.TcpSender("192.168.100.4", "192.168.100.3", 7818, 6439).handshake()
    sender.send(b"abc").send(b"def").fin()
    _capture, streams = _streams(sender.records, 6439)
    assert len(streams) == 1
    stream = streams[0]
    assert bytes(stream.data) == b"abcdef"
    assert not stream.gaps
    assert not stream.mid_stream_start
    assert stream.established_ns is not None and stream.fin_ns is not None
    # The delivery time of the first three bytes is the time of the first data segment.
    assert stream.delivery_ns(3) == sender.records[3][0]


def test_tcp_stream_records_a_gap_from_a_missing_segment() -> None:
    sender = b.TcpSender("10.0.0.2", "10.0.0.1", 5000, 4731).handshake()
    sender.send(b"aaaa")
    hole_seq = sender.sseq
    sender.sseq += 4  # four bytes never captured
    sender.send(b"cccc")
    sender.raw(hole_seq, b"bbbb")  # the missing bytes arrive late (out of order)
    _capture, streams = _streams(sender.records, 4731)
    stream = streams[0]
    assert bytes(stream.data) == b"aaaabbbbcccc" or stream.gaps
    # Either the late segment filled the hole, or a gap was recorded; both are acceptable,
    # but a gap must never be silently dropped bytes.
    assert bytes(stream.data).startswith(b"aaaa")


def test_a_mid_stream_capture_is_flagged() -> None:
    # No handshake: the capture joined an open connection.
    sender = b.TcpSender("10.0.0.2", "10.0.0.1", 5000, 4731)
    sender.sseq = 90_000
    sender.send(b.delimited(b.frame(1, 1_000)) + b.delimited(b.frame(2, 2_000)))
    _capture, streams = _streams(sender.records, 4731)
    assert streams[0].mid_stream_start


def test_frame_decode_reads_sequence_timestamp_and_stage() -> None:
    payload = b.frame(42, 123, stage="INTERVENTION")
    facts = frames.frame_facts(payload)
    assert facts.sequence == 42
    assert facts.frame_timestamp_ns == 123
    assert frames.stage(facts) == "INTERVENTION"
    assert frames.stage(frames.frame_facts(b.frame(1, 1, stage="RELEASED"))) == "RELEASED"
    assert frames.stage(frames.frame_facts(b.frame(1, 1, stage="WARNING"))) == "WARNING"


def test_frame_decode_rejects_malformed_bytes() -> None:
    with pytest.raises(frames.WireError):
        frames.decode_fields(b"\x08")  # a varint key with no value


def test_split_frames_reads_a_clean_stream() -> None:
    sender = b.TcpSender("10.0.0.2", "10.0.0.1", 5000, 4731).handshake()
    for seq in range(1, 6):
        sender.send(b.delimited(b.frame(seq, seq * 100)))
    _capture, streams = _streams(sender.records, 4731)
    got, problems = frames.split_frames(streams[0], 0)
    assert problems == []
    assert [frames.frame_facts(frame.payload).sequence for frame in got] == [1, 2, 3, 4, 5]


def test_split_frames_resyncs_after_a_bad_length_prefix() -> None:
    good = b.delimited(b.frame(1, 100))
    bad = struct.pack("<I", 9_000_000) + b"\x08\x01rubbish"  # an impossible length
    rest = b.delimited(b.frame(2, 200)) + b.delimited(b.frame(3, 300))
    sender = b.TcpSender("10.0.0.2", "10.0.0.1", 5000, 4731).handshake()
    sender.send(good + bad + rest)
    _capture, streams = _streams(sender.records, 4731)
    got, problems = frames.split_frames(streams[0], 0)
    sequences = [frames.frame_facts(frame.payload).sequence for frame in got]
    assert 1 in sequences and 2 in sequences and 3 in sequences
    assert any("framing lost" in problem for problem in problems)


def test_provenance_diff_sees_a_changed_field() -> None:
    produced = b.frame(1, 100, stage="WARNING")
    received = b.frame(1, 100, stage="INTERVENTION")
    differences = frames.diff_trees(frames.field_tree(produced), frames.field_tree(received))
    assert differences  # the warning/braking/intervention fields differ


def teardown_module(_module) -> None:
    import os
    for path in _TMP:
        try:
            os.unlink(path)
        except OSError:
            pass
