"""Replay the evaluators over a run directory and print the outcomes as JSON.

    python -m de4sdv_broker_path_bench.run <run-dir> [--case VC-MW-015 ...]

It reads only the raw artifacts of the directory. It prints one JSON object
with a result per case; it writes no verdict into any record and makes no
claim beyond the bounded outcome of each evaluator. The exit code is 0 only
when every requested case gives a pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evaluators import EVALUATORS, load_run
from .outcome import PASS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="the run directory with the raw artifacts")
    parser.add_argument("--case", action="append", choices=sorted(EVALUATORS),
                        help="a case to evaluate (default: every case the directory supports)")
    parser.add_argument("--out", help="write the JSON report to this file as well as stdout")
    arguments = parser.parse_args(argv)

    run = load_run(arguments.run_dir)
    cases = arguments.case or sorted(EVALUATORS)
    results = {case: EVALUATORS[case](run).as_dict() for case in cases}
    report = {"run_dir": str(Path(arguments.run_dir)), "results": results}
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if arguments.out:
        Path(arguments.out).write_text(text + "\n")
    return 0 if all(result["outcome"] == PASS for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
