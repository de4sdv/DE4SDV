#!/usr/bin/env python3
"""Measure the clock offset between two hosts, over the network they share.

Why this exists: every latency claim this project makes is a difference of two
timestamps. On one host those timestamps come from one clock, so the difference
is real. Across hosts they come from two clocks, and the difference carries the
offset. This tool measures that offset so the error is stated instead of
assumed.

The exchange is the classic four-timestamp one, and its assumption is symmetric
delay:

    A: t1 = now()      send  ──▶  B: t2 = now()      (receive)
    A: t4 = now()      recv  ◀──  B: t3 = now()      (send reply)

    offset = ((t2 - t1) + (t3 - t4)) / 2      how far B's clock is ahead of A's
    delay  =  (t4 - t1) - (t3 - t2)           round trip minus B's own work

If the path is asymmetric the offset is wrong by half the asymmetry, which is
the standard NTP caveat and the reason a disciplined clock beats a computed
correction.

Usage:
    on B:  timesync_probe.py --serve --port 9999
    on A:  timesync_probe.py --host <B> --port 9999 --count 200

Exit code is 0 when the exchange succeeded for at least 90 % of samples.
"""

from __future__ import annotations

import argparse
import json
import socket
import statistics
import struct
import sys
import time

MAGIC = b"TSYN"
FMT = "!4sdd"  # magic, t2, t3


def serve(host: str, port: int, count: int) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.settimeout(120.0)
    served = 0
    print(json.dumps({"serving": f"{host}:{port}"}), flush=True)
    while served < count:
        try:
            payload, peer = sock.recvfrom(64)
        except socket.timeout:
            break
        if payload != MAGIC:
            continue
        t2 = time.time()
        t3 = time.time()
        sock.sendto(struct.pack(FMT, MAGIC, t2, t3), peer)
        served += 1
    sock.close()
    print(json.dumps({"served": served}), flush=True)
    return 0


def measure(host: str, port: int, count: int, interval: float) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    offsets, delays, failed = [], [], 0
    for _ in range(count):
        t1 = time.time()
        sock.sendto(MAGIC, (host, port))
        try:
            payload, _peer = sock.recvfrom(64)
        except socket.timeout:
            failed += 1
            continue
        t4 = time.time()
        _magic, t2, t3 = struct.unpack(FMT, payload)
        offsets.append(((t2 - t1) + (t3 - t4)) / 2.0)
        delays.append((t4 - t1) - (t3 - t2))
        time.sleep(interval)
    sock.close()

    if not offsets:
        print(json.dumps({"ok": False, "error": "no replies", "failed": failed}))
        return 1

    def ms(v):
        return round(v * 1000, 3)

    ordered = sorted(offsets)
    p95 = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
    result = {
        "ok": len(offsets) >= 0.9 * count,
        "n": len(offsets),
        "failed": failed,
        "offset_ms": {
            "median": ms(statistics.median(offsets)),
            "p95": ms(p95),
            "min": ms(min(offsets)),
            "max": ms(max(offsets)),
            "mean": ms(statistics.fmean(offsets)),
            "stdev": ms(statistics.stdev(offsets)) if len(offsets) > 1 else None,
        },
        "rtt_ms": {
            "median": ms(statistics.median(delays)),
            "max": ms(max(delays)),
        },
        "reading": "offset is how far the server's clock is ahead of this host's",
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--interval", type=float, default=0.01)
    args = ap.parse_args()
    if args.serve:
        return serve(args.host, args.port, args.count + 20)
    return measure(args.host, args.port, args.count, args.interval)


if __name__ == "__main__":
    sys.exit(main())
