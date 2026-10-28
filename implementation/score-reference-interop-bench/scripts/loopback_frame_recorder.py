#!/usr/bin/env python3
"""Loopback client of the SOME/IP receiver in the CI runs: it stands where the HMI ingress connects.

It connects to host:port (127.0.0.1:4731), reads the stream the way the
ingress reads it (a 4-byte little-endian length prefix, then the frame) and
records every frame as one JSON line: receipt times, size, SHA-256 of prefix
plus frame, and sequence and frame_timestamp_ns read with the bench's own
wire reader. The bytes of connection k go to <stream-dir>/recorder-stream-<k>.bin.
With --reconnect it connects again after the stream ends, every 100 ms,
until SIGTERM. It never writes to the receiver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import signal
import socket
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from de4sdv_score_bench.visualization_frame import read_payload  # noqa: E402

MAX_FRAME_BYTES = 1 << 20


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4731)
    parser.add_argument("--log", required=True)
    parser.add_argument("--stream-dir", required=True)
    parser.add_argument("--reconnect", action="store_true")
    arguments = parser.parse_args()

    stop = {"requested": False}

    def _on_signal(_signum, _frame) -> None:
        stop["requested"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    connection = 0
    with open(arguments.log, "a", encoding="utf-8") as log:
        def record(event: str, **fields) -> None:
            log.write(json.dumps({"event": event, **fields}) + "\n")
            log.flush()

        record("recorder_start", host=arguments.host, port=arguments.port, reconnect=arguments.reconnect,
               monotonic_ns=time.monotonic_ns(), realtime_ns=time.time_ns())
        while not stop["requested"]:
            try:
                client = socket.create_connection((arguments.host, arguments.port), timeout=0.5)
            except OSError:
                time.sleep(0.1)
                continue
            connection += 1
            record("connected", connection=connection, monotonic_ns=time.monotonic_ns(), realtime_ns=time.time_ns())
            print(json.dumps({"event": "connected", "connection": connection}, separators=(",", ":")), flush=True)
            client.settimeout(0.2)
            stream = open(Path(arguments.stream_dir) / f"recorder-stream-{connection}.bin", "ab")
            buffer = b""
            index = 0
            reason = "closed"
            try:
                while not stop["requested"]:
                    try:
                        chunk = client.recv(65536)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    receipt_monotonic, receipt_realtime = time.monotonic_ns(), time.time_ns()
                    stream.write(chunk)
                    stream.flush()
                    buffer += chunk
                    while len(buffer) >= 4:
                        length = struct.unpack("<I", buffer[:4])[0]
                        if length > MAX_FRAME_BYTES:
                            raise ValueError(f"length prefix {length}")
                        if len(buffer) < 4 + length:
                            break
                        payload, buffer = buffer[:4 + length], buffer[4 + length:]
                        ok, fields = read_payload(payload)
                        index += 1
                        record("frame", connection=connection, index=index, receipt_monotonic_ns=receipt_monotonic,
                               receipt_realtime_ns=receipt_realtime, payload_bytes=len(payload), prefix_ok=ok,
                               sequence=fields.sequence if fields else None,
                               frame_timestamp_ns=fields.frame_timestamp_ns if fields else None,
                               payload_sha256=hashlib.sha256(payload).hexdigest())
            except (OSError, ValueError) as error:
                reason = f"error: {error}"
            finally:
                stream.close()
                client.close()
            record("disconnected", connection=connection, reason=reason, partial_bytes=len(buffer),
                   monotonic_ns=time.monotonic_ns(), realtime_ns=time.time_ns())
            if not arguments.reconnect:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
