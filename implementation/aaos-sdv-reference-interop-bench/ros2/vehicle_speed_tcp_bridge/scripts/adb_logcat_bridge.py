#!/usr/bin/env python3
"""Forward validated AAOS Vehicle.Speed log records to the ROS 2 VM.

The VSIDL service-bundle process is intentionally not granted a network socket
permission by the AAOS reference image. This host-side process is therefore
the explicit campaign transport boundary:

    Cuttlefish observer -> ADB/logcat -> AAOS host -> private TCP -> ROS 2 VM

It is a development/evidence transport, not a production vehicle binding.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from de4sdv_vehicle_speed_tcp_bridge.bridge_core import (  # noqa: E402
    parse_vehicle_speed_line,
)

WIRE_MARKER = "DE4SDV_VEHICLE_SPEED_WIRE "


def extract_wire_payload(log_line: str) -> str | None:
    """Return a canonical validated wire line from one logcat line."""
    marker_index = log_line.find(WIRE_MARKER)
    if marker_index < 0:
        return None
    payload = log_line[marker_index + len(WIRE_MARKER) :].strip()
    if not payload:
        raise ValueError("wire marker has no JSON payload")
    document = json.loads(payload)
    parse_vehicle_speed_line(payload)
    return json.dumps(document, separators=(",", ":"), sort_keys=True) + "\n"


class TcpForwarder:
    """Reconnect and forward one validated line at a time."""

    def __init__(self, host: str, port: int, retry_s: float) -> None:
        self._address = (host, port)
        self._retry_s = retry_s
        self._stream: socket.socket | None = None

    def send(self, line: str) -> None:
        while True:
            if self._stream is None:
                try:
                    self._stream = socket.create_connection(self._address, timeout=5)
                    self._stream.settimeout(None)
                    print(
                        "DE4SDV_ADB_LOGCAT_FORWARD_CONNECTED "
                        f"target={self._address[0]}:{self._address[1]}",
                        flush=True,
                    )
                except OSError as error:
                    print(
                        "DE4SDV_ADB_LOGCAT_FORWARD_CONNECT_FAILED "
                        f"target={self._address[0]}:{self._address[1]} error={error}",
                        file=sys.stderr,
                        flush=True,
                    )
                    time.sleep(self._retry_s)
                    continue
            try:
                self._stream.sendall(line.encode("utf-8"))
                return
            except OSError as error:
                print(
                    f"DE4SDV_ADB_LOGCAT_FORWARD_WRITE_FAILED error={error}",
                    file=sys.stderr,
                    flush=True,
                )
                self._stream.close()
                self._stream = None

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="0.0.0.0:6520")
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, default=4711)
    parser.add_argument("--retry-s", type=float, default=0.5)
    parser.add_argument(
        "--clear-logcat",
        action="store_true",
        help="clear the guest log before subscribing to new records",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=0,
        help="exit after this many forwarded records; zero means continuous",
    )
    return parser


def _run_adb(adb: str, serial: str, *args: str) -> None:
    subprocess.run([adb, "-s", serial, *args], check=True)


def _logcat_command(adb: str, serial: str) -> list[str]:
    return [adb, "-s", serial, "logcat", "-v", "raw", "-T", "1"]


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.max_records < 0:
        raise SystemExit("--max-records must be non-negative")
    if args.retry_s <= 0:
        raise SystemExit("--retry-s must be positive")

    if args.clear_logcat:
        _run_adb(args.adb, args.serial, "logcat", "-c")

    forwarder = TcpForwarder(args.target_host, args.target_port, args.retry_s)
    process = subprocess.Popen(
        _logcat_command(args.adb, args.serial),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    forwarded = 0
    try:
        assert process.stdout is not None
        for log_line in process.stdout:
            try:
                wire_line = extract_wire_payload(log_line)
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                print(
                    f"DE4SDV_ADB_LOGCAT_MALFORMED error={error}",
                    file=sys.stderr,
                    flush=True,
                )
                continue
            if wire_line is None:
                continue
            forwarder.send(wire_line)
            forwarded += 1
            print(
                "DE4SDV_ADB_LOGCAT_FORWARD_ACCEPTED "
                f"count={forwarded} payload={wire_line.rstrip()}",
                flush=True,
            )
            if args.max_records and forwarded >= args.max_records:
                break
    finally:
        forwarder.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    return 0 if forwarded else 1


if __name__ == "__main__":
    raise SystemExit(main())
