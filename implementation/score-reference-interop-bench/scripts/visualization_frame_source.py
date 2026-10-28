#!/usr/bin/env python3
"""VisualizationFrame source for the CI runs of the SOME/IP receiver (never a case of record).

It serves the stream form of the INC-AEBS-010 frame assembler, like
synthetic_frame_source.py: one client at a time on host:port, each frame
behind a 4-byte little-endian length prefix, one frame per period. Each
frame is a VisualizationFrame encoding with sequence and frame_timestamp_ns
(CLOCK_REALTIME at creation), because the receiver reads these two fields
for its discard rule. The sizes cycle through small and large values up to
2044 bytes, the largest frame that fits the 2048-byte sample of the S-CORE
frame event with its prefix.

It sends nothing before --go-file exists and nothing while --pause-file
exists, stops after --frames frames (0: no limit) and keeps the connection
open until SIGTERM. A pause leaves the newest frames in the sample slots of
the S-CORE layer, so the first read of a later subscription in the host
half returns frames from before it, as in the stored-sample cases of the
gateway spike. One JSON line per sent frame records the sequence, the
timestamp, the size and the SHA-256 of prefix plus frame; the bytes sent on
connection k go to <stream-dir>/source-stream-<k>.bin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from de4sdv_score_bench.visualization_frame import encode_frame, length_prefixed  # noqa: E402

SIZES = (64, 200, 800, 1100, 2044, 96, 512)
SOURCE_IDENTITY = "de4sdv-ci-frame-source"


def frame_for(sequence: int, timestamp_ns: int) -> bytes:
    size = SIZES[sequence % len(SIZES)]
    for candidate in (size, size - 1, size + 1):
        try:
            return encode_frame(sequence, timestamp_ns, bridge_receipt_timestamp_ns=timestamp_ns,
                                source_identity=SOURCE_IDENTITY, size=candidate)
        except ValueError:
            continue
    raise ValueError(f"no frame of about {size} bytes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4721)
    parser.add_argument("--period-ms", type=int, default=100)
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--go-file", default="")
    parser.add_argument("--pause-file", default="")
    parser.add_argument("--log", required=True)
    parser.add_argument("--stream-dir", required=True)
    arguments = parser.parse_args()

    stop = {"requested": False}

    def _on_signal(_signum, _frame) -> None:
        stop["requested"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    def go() -> bool:
        started = not arguments.go_file or os.path.exists(arguments.go_file)
        paused = bool(arguments.pause_file) and os.path.exists(arguments.pause_file)
        return started and not paused

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((arguments.host, arguments.port))
    server.listen(1)
    server.settimeout(0.2)
    print(json.dumps({"event": "listening", "host": arguments.host, "port": arguments.port},
                     separators=(",", ":")), flush=True)
    sequence = 0
    connection = 0
    done_logged = False
    sending = False
    with open(arguments.log, "a", encoding="utf-8") as log:
        def record(event: str, **fields) -> None:
            log.write(json.dumps({"event": event, "monotonic_ns": time.monotonic_ns(),
                                  "realtime_ns": time.time_ns(), **fields}) + "\n")
            log.flush()

        while not stop["requested"]:
            try:
                client, _ = server.accept()
            except socket.timeout:
                continue
            connection += 1
            record("client_connected", connection=connection)
            stream = open(Path(arguments.stream_dir) / f"source-stream-{connection}.bin", "ab")
            next_send = None
            try:
                while not stop["requested"]:
                    if not go() or (arguments.frames and sequence >= arguments.frames):
                        if arguments.frames and sequence >= arguments.frames and not done_logged:
                            record("done", frames=sequence)
                            done_logged = True
                        if sending:
                            record("paused", last_sequence=sequence)
                            sending = False
                        time.sleep(0.02)
                        next_send = None
                        continue
                    if not sending:
                        record("sending", next_sequence=sequence + 1)
                        sending = True
                    if next_send is None:
                        next_send = time.monotonic()
                    sequence += 1
                    timestamp_ns = time.time_ns()
                    payload = length_prefixed(frame_for(sequence, timestamp_ns))
                    client.sendall(payload)
                    stream.write(payload)
                    stream.flush()
                    record("sent", seq=sequence, frame_timestamp_ns=timestamp_ns, size=len(payload) - 4,
                           payload_sha256=hashlib.sha256(payload).hexdigest(), connection=connection)
                    next_send += arguments.period_ms / 1000.0
                    time.sleep(max(0.0, next_send - time.monotonic()))
            except OSError as error:
                record("client_lost", connection=connection, error=str(error))
            finally:
                stream.close()
                client.close()
    server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
