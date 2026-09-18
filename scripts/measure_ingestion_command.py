#!/usr/bin/env python3
"""Monotonic stage-timing wrapper for the privileged ingestion workflow.

Runs one command (or a shell script supplied on stdin) as a child process,
measures its wall-clock duration with ``time.monotonic()``, appends one JSONL
record with the exit status and the child resource usage
(``resource.RUSAGE_CHILDREN`` max RSS), and exits with the child's own exit
status. The wrapper never changes a stage's outcome: a failing command keeps
its exit code, a signal-terminated command is reported as ``128 + signal``
(the shell convention), and a timing-record write failure only warns.

Records never contain the command's arguments or the environment: callers
pass an explicit, non-sensitive ``--label`` and the record holds only that
stage label plus timing, resource, and exit facts.

Usage::

    python scripts/measure_ingestion_command.py --label export-baseline -- \
        python scripts/export_sysml_api_baseline.py --output /tmp/out.json

    python scripts/measure_ingestion_command.py --label build-api \
        --stdin-script <<'DE4SDV_MEASURE'
    git clone ...
    DE4SDV_MEASURE

The JSONL destination comes from ``--jsonl`` or the
``DE4SDV_INGESTION_TIMINGS`` environment variable — the same variable the
``de4sdv.sysml_api.performance.timing`` context manager uses, so workflow
stages and API-internal stages share one artifact. When neither is set the
command still runs and only the record is skipped (with a stderr notice), so
timing collection can never block the pipeline.

The stdin-script mode executes the script with the GitHub Actions default
bash invocation for ``run`` steps (``bash --noprofile --norc -eo pipefail``),
materializing it to a temporary file first so a stdin-reading command inside
the script (git, pip prompts) can never consume the remaining script lines;
the wrapped workflow bodies keep their original failure semantics.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "de4sdv.ingestion.command-timing.v1"
TIMINGS_ENV_VAR = "DE4SDV_INGESTION_TIMINGS"
DEFAULT_STDIN_SHELL: tuple[str, ...] = (
    "bash",
    "--noprofile",
    "--norc",
    "-eo",
    "pipefail",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def child_max_rss_kb() -> int:
    # Linux reports ru_maxrss in kilobytes; the workflow runs on
    # ubuntu-latest. RUSAGE_CHILDREN includes already-reaped descendants
    # (Linux aggregates grandchildren when their parents waited on them).
    return int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)


def build_record(
    *,
    stage: str,
    started_at: str,
    finished_at: str,
    duration_ns: int,
    exit_code: int,
    signal_number: int | None,
    rss_before_kb: int,
    rss_after_kb: int,
) -> dict:
    return {
        "schema": SCHEMA,
        "stage": stage,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ns": duration_ns,
        "duration_s": round(duration_ns / 1_000_000_000, 6),
        "exit_code": exit_code,
        "signal": signal_number,
        "child_max_rss_kb_before": rss_before_kb,
        "child_max_rss_kb_after": rss_after_kb,
        "child_max_rss_kb_delta": max(0, rss_after_kb - rss_before_kb),
    }


def append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def execute(command: list[str], stdin_script: bytes | None, stage: str) -> tuple[dict, int]:
    rss_before_kb = child_max_rss_kb()
    started_at = utc_now()
    started_ns = time.monotonic_ns()
    signal_number: int | None = None
    try:
        completed = subprocess.run(command, input=stdin_script, check=False)
        returncode = completed.returncode
    except OSError as exc:
        print(
            f"measure_ingestion_command: cannot run {command[0]!r}: {exc}",
            file=sys.stderr,
        )
        returncode = 127
    duration_ns = time.monotonic_ns() - started_ns
    finished_at = utc_now()
    rss_after_kb = child_max_rss_kb()
    if returncode < 0:
        signal_number = -returncode
        returncode = 128 + signal_number
    record = build_record(
        stage=stage,
        started_at=started_at,
        finished_at=finished_at,
        duration_ns=duration_ns,
        exit_code=returncode,
        signal_number=signal_number,
        rss_before_kb=rss_before_kb,
        rss_after_kb=rss_after_kb,
    )
    return record, returncode


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    if "--" in argv:
        separator = argv.index("--")
        option_tokens, command = argv[:separator], argv[separator + 1 :]
    else:
        option_tokens, command = argv, []
    parser = argparse.ArgumentParser(
        description="Run a command, record monotonic stage timing as JSONL, "
        "and exit with the command's exit status."
    )
    parser.add_argument("--label", required=True, help="non-sensitive stage label")
    parser.add_argument(
        "--jsonl",
        default=None,
        help=f"JSONL destination (default: ${TIMINGS_ENV_VAR})",
    )
    parser.add_argument(
        "--stdin-script",
        action="store_true",
        dest="stdin_script",
        help="execute the script read from stdin with the GitHub Actions "
        "default bash invocation; the command tokens after '--' (if any) "
        "override the default interpreter invocation",
    )
    options = parser.parse_args(option_tokens)
    return options, command


def main(argv: list[str] | None = None) -> int:
    options, command = parse_args(list(sys.argv[1:] if argv is None else argv))

    if options.stdin_script:
        script_bytes = sys.stdin.buffer.read()
        # Run the script from a real file, never from the shell's stdin: a
        # command inside the script that reads stdin (git, pip prompts) must
        # not be able to consume the remaining script lines. stdin stays
        # attached to the wrapper's own stdin for normal command behavior.
        if command:
            interpreter = list(command)
        else:
            interpreter = ["bash", "--noprofile", "--norc", "-eo", "pipefail"]
        with tempfile.TemporaryDirectory(prefix="de4sdv-measure-") as scratch:
            script_path = Path(scratch) / "stage.sh"
            script_path.write_bytes(script_bytes)
            record, returncode = execute(
                [*interpreter, str(script_path)], None, options.label
            )
    else:
        record, returncode = execute(command, None, options.label)

    timings_path = options.jsonl or os.environ.get(TIMINGS_ENV_VAR) or ""
    if timings_path:
        try:
            append_record(Path(timings_path), record)
        except OSError as exc:
            # Timing collection must never change a stage's outcome.
            print(
                f"measure_ingestion_command: cannot append timing record to "
                f"{timings_path!r}: {exc}",
                file=sys.stderr,
            )
    else:
        print(
            f"measure_ingestion_command: {TIMINGS_ENV_VAR} is not set; stage "
            f"'{options.label}' ran unmeasured",
            file=sys.stderr,
        )
    return returncode


if __name__ == "__main__":
    sys.exit(main())
