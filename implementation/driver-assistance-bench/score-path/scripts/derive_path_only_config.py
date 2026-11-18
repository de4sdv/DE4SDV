#!/usr/bin/env python3
"""Derives the S-CORE host's path-only Launch Manager configuration from the Launch Manager lane's file.

The P10-3 probe and the path-only part of P10-1 run the warning path (identity recorder, someipd, gatewayd) without
the candidate's process and the actuation adapter: the test publisher of ivi-warning/injector offers the same
mw::com event as the candidate (de4sdv/driver_assistance/warning_request), so the candidate must not run, and
without a simulator neither could it. The derived file keeps every component, so the identity recorder still reads
the candidate's launch settings from it (its record then holds this file verbatim, which shows the mode), and
changes only the run target: supervised_path loses vision_pilot and actuation_adapter.

Usage:
  derive_path_only_config.py [--source <launch_manager_config.json>] [--out <file>] [--check]
--check compares the derivation with the committed file and exits 1 when they differ.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[2]
SOURCE = BENCH / "launch-manager" / "config" / "launch_manager_config.json"
OUT = BENCH / "score-path" / "config" / "launch_manager_config_path_only.json"
DROPPED = ("vision_pilot", "actuation_adapter")
DESCRIPTION = ("The warning path without the candidate (score-path/scripts/derive_path_only_config.py): the "
               "identity recorder first, then someipd and gatewayd. The candidate's process and the actuation "
               "adapter stay defined and are started by no run target, so the test publisher of the warning "
               "request can offer the candidate's event.")


def derive(source: dict) -> dict:
    config = copy.deepcopy(source)
    target = config["run_targets"]["supervised_path"]
    target["depends_on"] = [name for name in target["depends_on"] if name not in DROPPED]
    target["description"] = DESCRIPTION
    return config


def render(config: dict) -> str:
    return json.dumps(config, indent=4) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render(derive(json.loads(args.source.read_text(encoding="utf-8"))))
    if args.check:
        same = args.out.is_file() and args.out.read_text(encoding="utf-8") == text
        print(f"{args.out}: {'up to date' if same else 'STALE: rerun derive_path_only_config.py'}")
        return 0 if same else 1
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
