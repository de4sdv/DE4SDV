"""Tests of the Data Tunnel reader (dt.py): the subscription time in the VLAN 2 capture.

VC-MW-020 (main 4bcfe628) runs its check a second time with the time of the
subscription in the Data Tunnel capture as the start. In the UNLOCKED mode
Data Tunnel is gRPC over cleartext HTTP/2: the IVI agent opens a stream with a
HEADERS frame and the core streams the publication's messages back as DATA.
The reader finds a frame by its bytes and gives the opening time of the
stream that carries it; where the capture cannot show that (it joined the
connection mid-stream, or lost bytes before the frame), it says so.
"""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
from de4sdv_broker_path_bench import dt  # noqa: E402
from de4sdv_broker_path_bench.pcap import read_pcap  # noqa: E402

T = 1_793_000_000_000_000_000
MS = 1_000_000


def _read(tmp_path, connections):
    path = tmp_path / "data-tunnel-vlan2.pcap"
    path.write_bytes(b.dt_capture(connections))
    return dt.read(read_pcap(path))


def test_a_frame_is_found_by_its_bytes_with_its_arrival_and_its_stream_open_time(tmp_path):
    f1, f2 = b.frame(1, T), b.frame(2, T + 100 * MS)
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    conn.data(1, f1, T + 10 * MS).data(1, f2, T + 110 * MS)
    tunnel = _read(tmp_path, [conn])
    found = tunnel.locate(f2)
    assert len(found) == 1
    assert found[0].arrival_ns == T + 110 * MS and found[0].from_client is False
    assert tunnel.stream_open_ns(found[0]) == T - 300 * MS


def test_the_second_stream_of_a_connection_has_its_own_open_time(tmp_path):
    f1, f2 = b.frame(1, T), b.frame(2, T + 100 * MS)
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    conn.data(1, f1, T + 10 * MS).open_stream(3, T + 50 * MS).data(3, f2, T + 110 * MS)
    tunnel = _read(tmp_path, [conn])
    assert tunnel.stream_open_ns(tunnel.locate(f1)[0]) == T - 300 * MS
    assert tunnel.stream_open_ns(tunnel.locate(f2)[0]) == T + 50 * MS


def test_a_capture_that_joined_the_connection_mid_stream_has_no_open_time(tmp_path):
    f1 = b.frame(1, T)
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    conn.data(1, f1, T + 10 * MS)
    conn.records = conn.records[-1:]  # the capture started after the handshake and the HEADERS
    tunnel = _read(tmp_path, [conn])
    found = tunnel.locate(f1)
    assert found and found[0].arrival_ns == T + 10 * MS
    assert tunnel.stream_open_ns(found[0]) is None


def test_lost_bytes_before_the_frame_give_no_open_time(tmp_path):
    f1, f2 = b.frame(1, T), b.frame(2, T + 100 * MS)
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    conn.data(1, f1, T + 10 * MS).data(1, f2, T + 110 * MS)
    del conn.records[-2]  # the capture lost the segment with f1
    tunnel = _read(tmp_path, [conn])
    found = tunnel.locate(f2)
    assert found and tunnel.stream_open_ns(found[0]) is None


def test_a_retransmitted_segment_does_not_break_the_walk(tmp_path):
    f1, f2 = b.frame(1, T), b.frame(2, T + 100 * MS)
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    conn.data(1, f1, T + 10 * MS)
    ts, raw = conn.records[-1]
    conn.records.append((ts + 2 * MS, raw))  # the same segment again
    conn.data(1, f2, T + 110 * MS)
    tunnel = _read(tmp_path, [conn])
    assert tunnel.stream_open_ns(tunnel.locate(f2)[0]) == T - 300 * MS


def test_a_frame_the_tunnel_never_carried_is_not_found(tmp_path):
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    conn.data(1, b.frame(1, T), T + 10 * MS)
    assert _read(tmp_path, [conn]).locate(b.frame(99, T + 900 * MS)) == []


def test_the_arrivals_of_many_frames_come_in_capture_order(tmp_path):
    frames = [b.frame(i, T + i * 100 * MS) for i in range(1, 6)]
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    for i, payload in enumerate(frames, start=1):
        conn.data(1, payload, T + i * 100 * MS + 5 * MS)
    tunnel = _read(tmp_path, [conn])
    carrier = tunnel.locate(frames[0])[0]
    arrivals = tunnel.arrivals(carrier, frames)
    assert arrivals == [T + i * 100 * MS + 5 * MS for i in range(1, 6)]


def test_arrivals_can_start_the_search_at_a_time(tmp_path):
    frames = [b.frame(i, T + i * 100 * MS) for i in range(1, 6)]
    conn = b.DtConnection(T - 500 * MS).handshake().open_stream(1, T - 300 * MS, preface=True).server_settings()
    for i, payload in enumerate(frames, start=1):
        conn.data(1, payload, T + i * 100 * MS + 5 * MS)
    tunnel = _read(tmp_path, [conn])
    carrier = tunnel.locate(frames[0])[0]
    # Only the frames that crossed at or after the given time are searched for.
    assert tunnel.arrivals(carrier, frames, since_ns=T + 300 * MS) == [T + i * 100 * MS + 5 * MS for i in (3, 4, 5)]
