"""The tests' own process listings read whole command lines, whatever width the environment gives ps.

procps' ps cuts each line to $COLUMNS when that is set, even into a pipe. On the GitHub runner, pytest imports
readline at its start (capture.py, _readline_workaround), and the GNU readline that the runner's Python links sets
COLUMNS=80 and LINES=24 with setenv(3). os.environ does not see that, so the scripts under test (run with copies of
os.environ) list full lines, while a ps the test process starts itself inherits COLUMNS=80. A stage under pytest's
basetemp (/tmp/pytest-of-runner/pytest-N/<test>/de4sdv-da-bench) is longer than 80 columns with its bin/, so a
listing cut there matched no process: every test that asserted a process runs failed in CI, and every test that
asserted none ran passed without looking (CI runs 44851218448, 44857088427 and 44867308248). Test code only.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import fake_bundle  # noqa: E402

BENCH = TESTS.parents[1]


def test_staged_processes_sees_a_long_stage_when_the_environment_narrows_ps(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stage = tmp_path / ("s" * 90) / "de4sdv-da-bench"
    (stage / "bin").mkdir(parents=True)
    stub = stage / "bin" / "gatewayd"
    stub.write_text("#!/bin/bash\nwhile :; do sleep 0.1; done\n")
    stub.chmod(0o755)
    assert len(f"S    /bin/bash {stub}") > 80
    # as readline leaves the runner's pytest process: COLUMNS=80 in the environment a child inherits
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("LINES", "24")
    proc = subprocess.Popen([str(stub)])
    try:
        deadline = time.monotonic() + 10
        while not Path(f"/proc/{proc.pid}/cmdline").read_bytes().startswith(b"/bin/bash"):
            assert time.monotonic() < deadline, "the stub did not exec bash"
            time.sleep(0.05)
        found = fake_bundle.staged_processes(stage)
        assert any(f"{stage}/bin/gatewayd" in line for line in found), found
    finally:
        proc.kill()
        proc.wait()


def test_every_process_listing_of_the_bench_tests_asks_ps_for_unlimited_width() -> None:
    # each test-side ps that reads command lines (args, cmd, command) passes -ww: a line cut to $COLUMNS hides the
    # process the test looks for (a presence check fails) or hides it from a "none left" check (which then passes
    # without looking)
    listings = []
    for path in sorted(BENCH.glob("*/tests/**/*.py")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"\[\s*\"ps\"\s*,", line) and re.search(r"\b(args|cmd|command)\b", line):
                listings.append((path.relative_to(BENCH), number, line.strip()))
    assert len(listings) >= 2, listings  # fake_bundle.staged_processes and test_session_s1's tunnels()
    narrow = [entry for entry in listings if '"-ww"' not in entry[2]]
    assert not narrow, narrow
