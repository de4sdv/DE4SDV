#!/usr/bin/env python3
"""DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.

Summarises the per-target results of the gateway's own Bazel test runs from
the logs ci_upstream_tests.sh kept (Bazel's end-of-run target table), as
Markdown on stdout and tests_summary.json next to the logs.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROW = re.compile(r"^((?://|@)\S+)\s+(PASSED|FAILED TO BUILD|FAILED|SKIPPED|NO STATUS|TIMEOUT|FLAKY|INCOMPLETE)\b(.*)$")
EXECUTED = re.compile(r"^(Executed \d+ out of \d+ tests?:.*)$")


def main() -> int:
    out = Path(sys.argv[1])
    summary = {}
    lines = []
    for status_file in sorted(out.glob("*.status.json")):
        status = json.loads(status_file.read_text())
        log = out / f"{status['name']}.log"
        text = log.read_text(errors="replace") if log.exists() else ""
        rows = []
        executed = None
        build_ok = None
        for line in text.splitlines():
            match = ROW.match(line.strip())
            if match:
                rows.append({"target": match.group(1), "status": match.group(2), "detail": match.group(3).strip()})
            ex = EXECUTED.match(line.strip())
            if ex:
                executed = ex.group(1)
            if "Build completed successfully" in line:
                build_ok = True
            if "Build did NOT complete successfully" in line:
                build_ok = False
        counts = Counter(r["status"] for r in rows)
        summary[status["name"]] = {**status, "build_completed": build_ok, "executed_line": executed,
                                   "counts": dict(counts), "targets": rows}
        lines.append(f"### {status['name']}: `{status['command']}`")
        lines.append(f"exit {status['exit_code']}, {status['wall_s']} s, build completed: {build_ok}; "
                     f"{executed or 'no executed line'}; counts {dict(counts)}")
        lines.append("")
        for row in rows:
            lines.append(f"- `{row['target']}` {row['status']} {row['detail']}")
        lines.append("")
    (out / "tests_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
