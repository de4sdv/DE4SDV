#!/usr/bin/env python3
"""Probe a traffic gate: send paced datagrams, timestamp arrival at the far end.

The point is to see a schedule, not to measure a network. If a gate closes a
class for part of its cycle, paced packets of that class arrive in two groups:
those sent while the gate was open (immediate) and those sent while it was shut
(held until it opens). A bimodal distribution with a ceiling near the closed
interval is the gate; a tight single mode is no gate.

Both ends must sit in different namespaces, or a packet to a local address never
leaves through the qdisc under test. `checks/gate_probe.sh` sets that up on the
gateway uplink; this file only sends and receives.

    receiver (in the peer namespace):
        gate_probe.py --serve --address 192.0.2.2 --port 9999 --count 4000

    sender (in the gateway's namespace):
        gate_probe.py --send --to 192.0.2.2:9999 --interval-ms 1 --count 3000

The sender stamps `time.time_ns()` into the payload; the receiver subtracts it.
One host, one clock, so the difference is the delay the path added.
"""

from __future__ import annotations

import argparse
import json
import select
import socket
import statistics
import struct
import sys
import time

MAGIC = b"GATE"
FMT = "!4sQ"  # magic, t_send_ns


def serve(address: str, port: int, count: int) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((address, port))
    sock.settimeout(30.0)
    delays = []
    print(json.dumps({"serving": f"{address}:{port}", "expect": count}), flush=True)
    deadline = time.monotonic() + 60.0
    last_packet = None
    while len(delays) < count and time.monotonic() < deadline:
        try:
            ready, _, _ = select.select([sock], [], [], 1.0)
            if not ready:
                # The sender may send fewer probes than the receiver was told to
                # expect; a quiet second after traffic started means it is done.
                if last_packet and time.monotonic() - last_packet > 2.0:
                    break
                continue
            payload, _peer = sock.recvfrom(128)
        except OSError:
            break
        if len(payload) != struct.calcsize(FMT):
            continue
        magic, t_send = struct.unpack(FMT, payload)
        if magic != MAGIC:
            continue
        delays.append(time.time_ns() - t_send)
        last_packet = time.monotonic()

    if not delays:
        print(json.dumps({"ok": False, "error": "nothing arrived"}))
        return 1
    ordered = sorted(delays)
    p50 = ordered[len(ordered) // 2]
    p95 = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
    # The two groups a gate produces: held (>= 1 ms) and immediate.
    held = sum(1 for d in delays if d >= 1_000_000)
    result = {
        "ok": True,
        "n": len(delays),
        "median_ms": round(p50 / 1e6, 3),
        "p95_ms": round(p95 / 1e6, 3),
        "max_ms": round(max(delays) / 1e6, 3),
        "min_ms": round(min(delays) / 1e6, 3),
        "held_at_least_1ms": held,
        "held_fraction": round(held / len(delays), 3),
        "stdev_ms": round(statistics.stdev(delays) / 1e6, 3) if len(delays) > 1 else None,
    }
    print(json.dumps(result, indent=2))
    return 0


def send(to: str, port: int, interval_ms: float, count: int) -> int:
    host, _, port_text = to.rpartition(":")
    host = host or "127.0.0.1"
    port = int(port_text or port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = interval_ms / 1000.0
    sent = 0
    next_at = time.monotonic()
    for _ in range(count):
        payload = struct.pack(FMT, MAGIC, time.time_ns())
        try:
            sock.sendto(payload, (host, port))
            sent += 1
        except OSError as exc:
            print(json.dumps({"send_error": str(exc)}), file=sys.stderr)
            break
        next_at += interval
        wait = next_at - time.monotonic()
        if wait > 0:
            time.sleep(wait)
    sock.close()
    print(json.dumps({"sent": sent, "interval_ms": interval_ms, "to": f"{host}:{port}"}))
    return 0 if sent else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--address", default="0.0.0.0")
    ap.add_argument("--to", default="")
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--count", type=int, default=3000)
    ap.add_argument("--interval-ms", type=float, default=1.0)
    args = ap.parse_args()
    if args.serve:
        return serve(args.address, args.port, args.count)
    if args.send:
        return send(args.to, args.port, args.interval_ms, args.count)
    ap.error("one of --serve or --send is required")
    return 2


if __name__ == "__main__":
    sys.exit(main())
