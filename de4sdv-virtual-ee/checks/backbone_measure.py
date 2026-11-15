#!/usr/bin/env python3
"""Read the backbone run's logs and state what happened — with sample counts.

Inputs are the two containers' JSON lines: the provider's `event_sent` and
`method_served`, the client's `event_recv` and `method_rtt`. Everything is
timestamped with `time.time_ns()` on one host, so the differences are real; the
report states that domain rather than implying a distributed clock.

    method   round trip of a request/response, measured at the client
    event    one-way latency from the provider's send stamp to the client's
             receive stamp (both in the application payload — see the service)
    jitter   standard deviation of the inter-arrival gaps
    misses   events later than the declared deadline, and gaps longer than 1.5
             periods (a gap that large is a scheduling or delivery failure, not
             jitter)

Exit code is 0 when the method answered and events arrived at all; the numbers
themselves are for a human to judge.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path


def load(path: Path) -> list[dict]:
    records = []
    if not path.exists():
        return records
    for line in path.read_text(errors="replace").splitlines():
        line = re.sub(r"^\[[^\]]+\]\s*", "", line.strip())
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and "kind" in record:
            records.append(record)
    return records


def ms(value_ns: float) -> float:
    return round(value_ns / 1e6, 3)


def summary(values_ns: list[float]) -> dict:
    if not values_ns:
        return {"n": 0}
    ordered = sorted(values_ns)
    p95 = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
    return {
        "n": len(values_ns),
        "median_ms": ms(statistics.median(values_ns)),
        "p95_ms": ms(p95),
        "min_ms": ms(min(values_ns)),
        "max_ms": ms(max(values_ns)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider-log", required=True)
    ap.add_argument("--client-log", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    provider = load(Path(args.provider_log))
    client = load(Path(args.client_log))

    up = next((r for r in client if r.get("kind") == "client_up"), {})
    deadline_ms = up.get("deadline_ms")
    period_ms = up.get("call_period_ms")  # not the event period; provider reports that
    provider_up = next((r for r in provider if r.get("kind") == "provider_up"), {})
    event_period_ms = provider_up.get("period_ms")

    rtts = [r["rtt_ns"] for r in client if r.get("kind") == "method_rtt" and "rtt_ns" in r]
    received = [r for r in client if r.get("kind") == "event_recv"]
    latencies = [r["t_recv_ns"] - r["t_send_ns"] for r in received if {"t_recv_ns", "t_send_ns"} <= r.keys()]
    stamps = sorted(r["t_recv_ns"] for r in received if "t_recv_ns" in r)
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]

    seqs = sorted(r["seq"] for r in received if "seq" in r)
    # The two container logs are cut at different instants, so counting the
    # provider's lines against the client's receipts compares two windows. The
    # sequence span of what the client actually holds is the honest measure: it
    # says whether anything inside the observed window went missing.
    span = None
    if seqs:
        span = {
            "first": seqs[0],
            "last": seqs[-1],
            "distinct": len(set(seqs)),
            "missing": (seqs[-1] - seqs[0] + 1) - len(set(seqs)),
        }

    deadline_misses = sum(1 for value in latencies if deadline_ms and value / 1e6 > deadline_ms)
    period_misses = sum(1 for gap in gaps if event_period_ms and gap / 1e6 > 1.5 * event_period_ms)

    window_s = round((max(stamps) - min(stamps)) / 1e9, 1) if len(stamps) > 1 else 0.0
    result = {
        "clock": "one host, one CLOCK_REALTIME: the service stamps and the reader share it",
        "window_s": window_s,
        "declared": {
            "event_period_ms": event_period_ms,
            "deadline_ms": deadline_ms,
            "method_period_ms": period_ms,
        },
        "method": summary(rtts),
        "events": {
            "provider_events_logged": sum(1 for r in provider if r.get("kind") == "event_sent"),
            "received": len(received),
            "span": span,
            **{k: v for k, v in summary(latencies).items() if k != "n"},
            "jitter_ms": round(statistics.stdev(gaps) / 1e6, 3) if len(gaps) > 1 else None,
            "deadline_misses": deadline_misses,
            "period_misses": period_misses,
        },
        "served": sum(1 for r in provider if r.get("kind") == "method_served"),
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")

    print(json.dumps(result["declared"], indent=2))
    print(json.dumps({"method": result["method"]}, indent=2))
    print(json.dumps({"events": result["events"]}, indent=2))

    if not rtts:
        print("FAILED: no method round trips", file=sys.stderr)
        return 1
    if not received:
        print("FAILED: no events received", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
