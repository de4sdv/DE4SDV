#!/usr/bin/env python3
"""Summarise gate-2 records into the table the report needs, and judge them.

Percentiles without sample counts are not results, so every cell carries n.
Segments are reported separately: S1 (app write -> command frame), S2 (frame ->
acknowledgement), S3 (acknowledgement -> app sees the value). T1 and T4 happen
inside kuksa-can-provider and are not claimed.

Isolation comes from the `"kind": "isolation"` records gate2.py writes, one per
capture of the other zone's bus, so each capture is counted once. Routed status
must be present in every such capture and forbidden commands absent; a file
without isolation records has no isolation evidence. Command records are judged
against their scenario's expectation (`-down` records must not converge). The
exit code is 1 when anything is unmet or missing.

Usage: python summarize_gate2.py /tmp/gate2.jsonl
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate2 import command_problem, isolation_problem  # noqa: E402


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
    isolation = [r for r in recs if r.get("kind") == "isolation"]
    commands = [r for r in recs if r.get("kind") != "isolation"]

    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in commands:
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

    forbidden = sum(r.get("denied_command_frames") or 0 for r in isolation)
    routed = sum(r.get("routed_status_frames") or 0 for r in isolation)
    with_route = sum(1 for r in isolation if r.get("routed_status_frames"))
    print(f"\nforbidden command frames on the other bus: {forbidden}")
    print(f"routed status frames on the other bus: {routed} "
          f"(required, present in {with_route}/{len(isolation)} captures)")

    problems = []
    if not commands:
        problems.append("no command records")
    if not isolation:
        problems.append("missing evidence: no isolation records")
    for r in isolation:
        p = isolation_problem(r)
        if p:
            problems.append(f"isolation {r.get('label')} rep{r.get('rep')} {r.get('arm')}: {p}")
    for r in commands:
        p = command_problem(r)
        if p:
            problems.append(
                f"{r.get('label')} {r.get('arm')} idx={r.get('idx')}: {p} "
                f"(cmd_seen={r.get('cmd_seen')} ack_seen={r.get('ack_seen')} "
                f"error={(r.get('error') or '')[:80]})"
            )
    if problems:
        print("\nunmet expectations:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("\nevery record met its expectation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
