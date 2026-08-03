#!/usr/bin/env python3
"""Run the local reference-contract rehearsal and retain JSON evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "vss-vehicle-speed-adapter" / "src"))

from de4sdv_aaos_sdv_reference_bench import run_reference_rehearsal  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--speed-kmh", type=float, default=36.0)
    parser.add_argument("--timestamp-ns", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    evidence = run_reference_rehearsal(
        speed_kmh=args.speed_kmh,
        timestamp_ns=args.timestamp_ns,
    )
    rendered = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
