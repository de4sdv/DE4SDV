#!/usr/bin/env python3
"""Summarise gate-2 records into the table the report needs.

Percentiles without sample counts are not results, so every cell carries n.
Segments are reported separately: S1 (app write -> command frame), S2 (frame ->
acknowledgement), S3 (acknowledgement -> app sees the value). T1 and T4 happen
inside kuksa-can-provider and are not claimed.

Usage: python summarize_gate2.py /tmp/gate2.jsonl
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict


def pct(values, q):
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gate2.jsonl"
    recs = [json.loads(line) for line in open(path) if line.strip()]

    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in recs:
        groups[(r.get("label") or "?", r.get("arm") or "?", "all")].append(r)

    print("| scenario | arm | n | converged | S1 ms med / p95 | S2 ms med / p95 | S3 ms med / p95 | total ms med / p95 |")
    print("|---|---|---:|---:|---|---|---|---|")
    for (label, arm, _), rs in sorted(groups.items()):
        n = len(rs)
        ok = sum(1 for r in rs if r.get("ok"))
        cells = []
        for seg in ("s1", "s2", "s3", "total"):
            vals = [r[seg] for r in rs if r.get(seg) is not None]
            if vals:
                cells.append(f"{statistics.median(vals)*1000:.2f} / {pct(vals,0.95)*1000:.2f} (n={len(vals)})")
            else:
                cells.append("—")
        print(f"| {label} | {arm} | {n} | {ok}/{n} | " + " | ".join(cells) + " |")

    leaks = sum(sum((r.get("leaks") or {}).values()) for r in recs)
    print(f"\ncross-zone frames observed on the wrong bus: {leaks}")

    failed = [r for r in recs if not r.get("ok")]
    if failed:
        print("\nnon-converged records:")
        for r in failed:
            print(
                f"  {r.get('label')} {r.get('arm')} idx={r.get('idx')} "
                f"cmd_seen={r.get('cmd_seen')} ack_seen={r.get('ack_seen')} "
                f"error={(r.get('error') or '')[:80]}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
