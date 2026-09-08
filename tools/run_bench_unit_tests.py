#!/usr/bin/env python3
"""Run tracked implementation-bench unit/contract suites in isolated processes.

The benches use same-named bare imports (e.g. ``evidence_document``) with
per-bench module shapes, so their test directories must not share one Python
process. This runner executes each suite separately, records required import
paths, and fails on any suite failure. It covers only repository-tracked
unit/contract tests; it does not build containers, run ROS, or produce
runtime evidence.

Usage:
    python tools/run_bench_unit_tests.py            # run all suites
    python tools/run_bench_unit_tests.py --dry-run  # list suites only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GitInventoryError(RuntimeError):
    """The git file inventory could not be read (fail closed)."""


# One entry per isolated suite: test paths plus required PYTHONPATH entries
# (bench packages imported as bare modules by their tests).
SUITES: list[dict[str, object]] = [
    {
        "name": "aaos-sdv-reference-interop-bench",
        "tests": [
            "implementation/aaos-sdv-reference-interop-bench/tests",
            "implementation/aaos-sdv-reference-interop-bench/ros2"
            "/vehicle_speed_tcp_bridge/tests",
        ],
        "pythonpath": [],
    },
    {
        "name": "aebs-aaos-sdv-visualization-bench (010 bridge)",
        "tests": [
            "implementation/aebs-aaos-sdv-visualization-bench/src"
            "/de4sdv_aebs_010_bridge/test",
        ],
        "pythonpath": [],
    },
    {
        "name": "aebs-autoware-nominal-vehicle-target-bench (009B/009D)",
        "tests": [
            "implementation/aebs-autoware-nominal-vehicle-target-bench/src"
            "/de4sdv_aebs_009b_bench/test",
        ],
        "pythonpath": [
            "implementation/aebs-autoware-nominal-vehicle-target-bench/src"
            "/de4sdv_aebs_009b_bench",
            "implementation/aebs-bench-framework",
        ],
    },
    {
        "name": "aebs-autoware-stationary-target-bench (009C)",
        "tests": [
            "implementation/aebs-autoware-stationary-target-bench/src"
            "/de4sdv_aebs_009c_bench/test",
        ],
        "pythonpath": ["implementation/aebs-bench-framework"],
    },
    {
        "name": "vss-vehicle-speed-adapter",
        "tests": ["implementation/vss-vehicle-speed-adapter/tests"],
        "pythonpath": [],
    },
]


def _tracked_test_paths(paths: list[str]) -> list[str]:
    """Keep only test paths that contain tracked test files.

    Raises :class:`GitInventoryError` when git itself fails: an unreadable
    inventory must fail the run, never shrink it to zero suites.
    """
    existing: list[str] = []
    for rel in paths:
        absolute = ROOT / rel
        if not absolute.is_dir():
            continue
        completed = subprocess.run(
            ["git", "ls-files", "--", rel],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise GitInventoryError(
                f"git ls-files -- {rel} failed: {completed.stderr.strip()}"
            )
        if not completed.stdout.strip():
            continue
        existing.append(rel)
    return existing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="list suites without running"
    )
    arguments = parser.parse_args()

    if not arguments.dry_run:
        # Verify the git inventory is readable BEFORE running any suite: a
        # broken inventory would otherwise silently shrink the run to zero
        # suites and report success.
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=ROOT,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            print(
                "Bench unit/contract runner failed: git inventory is "
                f"unreadable ({error})",
                file=sys.stderr,
            )
            return 1

    failures: list[str] = []
    for suite in SUITES:
        try:
            tests = _tracked_test_paths(suite["tests"])  # type: ignore[arg-type]
        except GitInventoryError as error:
            print(
                "Bench unit/contract runner failed: unreadable git inventory "
                f"({error})",
                file=sys.stderr,
            )
            return 1
        if not tests:
            print(f"[skip] {suite['name']}: no tracked test paths")
            continue
        if arguments.dry_run:
            print(f"[suite] {suite['name']}: {', '.join(tests)}")
            continue
        environment = os.environ.copy()
        pythonpath = [str(ROOT / entry) for entry in suite["pythonpath"]]  # type: ignore[arg-type]
        if pythonpath:
            existing = environment.get("PYTHONPATH", "")
            environment["PYTHONPATH"] = os.pathsep.join([*pythonpath, existing]).rstrip(
                os.pathsep
            )
        command = [sys.executable, "-m", "pytest", "-q", "--tb=short", *tests]
        print(f"[run] {suite['name']}")
        completed = subprocess.run(command, cwd=ROOT, env=environment)
        if completed.returncode != 0:
            failures.append(str(suite["name"]))

    if arguments.dry_run:
        return 0
    if failures:
        print(f"\nBench unit/contract suites FAILED: {', '.join(failures)}")
        return 1
    print("\nAll bench unit/contract suites passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
