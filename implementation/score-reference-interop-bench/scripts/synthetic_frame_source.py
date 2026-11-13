#!/usr/bin/env python3
"""Synthetic frame source for CI runs of the adapter (never a case of record).

It serves the stream form of the INC-AEBS-010 frame assembler: one client at
a time on host:port, each frame behind a 4-byte little-endian length prefix,
one frame per period. The frame bytes are a deterministic pattern with the
sequence number in front; their sizes cycle through small and large values up
to the largest frame that fits a 2048-byte sample (2044 bytes). One JSON line
per sent frame records the sequence, the size and the SHA-256 of the frame.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import socket
import struct
import time

SIZES = (16, 200, 800, 1100, 2044, 64, 512)


def frame_bytes(sequence: int, size: int) -> bytes:
    head = struct.pack("<Q", sequence)
    body = bytes((sequence * 31 + index * 7) & 0xFF for index in range(max(0, size - len(head))))
    return (head + body)[:size]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4721)
    parser.add_argument("--period-ms", type=int, default=100)
    parser.add_argument("--log", required=True)
    arguments = parser.parse_args()

    stop = {"requested": False}

    def _on_signal(_signum, _frame) -> None:
        stop["requested"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((arguments.host, arguments.port))
    server.listen(1)
    server.settimeout(0.2)
    print(json.dumps({"event": "listening", "host": arguments.host, "port": arguments.port}), flush=True)
    sequence = 0
    with open(arguments.log, "a", encoding="utf-8") as log:
        while not stop["requested"]:
            try:
                client, _ = server.accept()
            except socket.timeout:
                continue
            log.write(json.dumps({"event": "client_connected", "monotonic_ns": time.monotonic_ns()}) + "\n")
            next_send = time.monotonic()
            try:
                while not stop["requested"]:
                    sequence += 1
                    frame = frame_bytes(sequence, SIZES[sequence % len(SIZES)])
                    client.sendall(struct.pack("<I", len(frame)) + frame)
                    log.write(json.dumps({"seq": sequence, "size": len(frame), "monotonic_ns": time.monotonic_ns(),
                                          "sha256": hashlib.sha256(frame).hexdigest()}) + "\n")
                    log.flush()
                    next_send += arguments.period_ms / 1000.0
                    time.sleep(max(0.0, next_send - time.monotonic()))
            except OSError:
                log.write(json.dumps({"event": "client_lost", "monotonic_ns": time.monotonic_ns()}) + "\n")
            finally:
                client.close()
    server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
