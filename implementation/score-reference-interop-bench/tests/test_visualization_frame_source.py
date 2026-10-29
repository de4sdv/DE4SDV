"""Tests of the VisualizationFrame source for plumbing tests of the relay chain.

The relay drops every frame that is no VisualizationFrame with a positive
sequence and frame_timestamp_ns, so its plumbing tests need this source, not
synthetic_frame_source.py. The test runs the source on a free loopback port,
reads its first frames as the frame assembler's client does, and checks the
sequence, the host-clock stamps and the variable sizes.
"""

from pathlib import Path
import json
import socket
import struct
import subprocess
import sys
import time

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.visualization_frame import read_fields  # noqa: E402

SOURCE = BENCH / "scripts" / "visualization_frame_source.py"
FRAMES = 8


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _read_exactly(connection: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        assert chunk, "the source closed the stream"
        data += chunk
    return data


def _connect(port: int, deadline: float) -> socket.socket:
    while True:
        try:
            return socket.create_connection(("127.0.0.1", port), timeout=5)
        except OSError:
            assert time.monotonic() < deadline, "the source did not listen"
            time.sleep(0.05)


def test_the_source_sends_visualization_frames_with_positive_fields_and_variable_sizes(tmp_path):
    port = _free_port()
    log = tmp_path / "source.jsonl"
    process = subprocess.Popen(
        [sys.executable, str(SOURCE), "--port", str(port), "--period-ms", "5", "--frames", str(FRAMES),
         "--log", str(log), "--stream-dir", str(tmp_path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        before_ns = time.time_ns()
        connection = _connect(port, time.monotonic() + 10)
        frames = []
        with connection:
            for _ in range(FRAMES):
                (length,) = struct.unpack("<I", _read_exactly(connection, 4))
                frames.append(_read_exactly(connection, length))
        after_ns = time.time_ns()
    finally:
        process.terminate()
        process.wait(timeout=10)
    fields = [read_fields(frame) for frame in frames]
    assert [field.sequence for field in fields] == list(range(1, FRAMES + 1))
    for field in fields:
        assert before_ns - 1_000_000_000 <= field.frame_timestamp_ns <= after_ns
    sizes = [len(frame) for frame in frames]
    assert len(set(sizes)) >= 4
    assert max(sizes) == 2044
    assert any(later < earlier for earlier, later in zip(sizes, sizes[1:])), "a shorter frame after a longer one"
    sent = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
            if json.loads(line)["event"] == "sent"]
    assert [record["seq"] for record in sent] == list(range(1, FRAMES + 1))
    assert [record["frame_timestamp_ns"] for record in sent] == [field.frame_timestamp_ns for field in fields]
