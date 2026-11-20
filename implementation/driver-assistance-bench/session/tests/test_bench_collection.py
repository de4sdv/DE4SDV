"""The bench's tests collect as one pytest run, which is how the gcc13 gate collects them.

The gate's one pytest call takes `implementation/driver-assistance-bench` whole. pytest imports every test
directory's conftest.py under the one module name `conftest`. With pytest 7.4 (the gcc13 image's) a test module
that imports `from conftest import ...` then gets whichever conftest is bound at that moment. Its own directory
run alone passes. Together with another directory's conftest it can fail to import, or silently take that
directory's values.

At 44a4be29 three case-evaluators modules failed to import that way (they got world-side's conftest), and the
gate ended at collection with rc 2. Helpers that tests import by name live in modules with a unique name
(world_side_testkit, case_evaluators_testkit).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[2]
REPO = BENCH.parents[1]
CONFTEST_IMPORT = re.compile(r"^[ \t]*(from[ \t]+conftest[ \t]+import|import[ \t]+conftest\b)", re.M)


def test_no_test_module_imports_a_conftest_by_name() -> None:
    offenders = []
    for f in sorted(BENCH.rglob("*.py")):
        if "tests" not in f.relative_to(BENCH).parts:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in CONFTEST_IMPORT.finditer(text):
            offenders.append(f"{f.relative_to(BENCH)}:{text.count(chr(10), 0, m.start()) + 1}")
    assert not offenders, ("import shared test helpers from a module with a unique name, never from conftest: "
                           + ", ".join(offenders))


def test_the_whole_bench_collects_in_one_run() -> None:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--collect-only",
                        str(BENCH.relative_to(REPO))], cwd=REPO, capture_output=True, text=True, timeout=900,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    tail = "\n".join((p.stdout + p.stderr).splitlines()[-25:])
    assert p.returncode == 0, tail
    assert " error" not in tail.splitlines()[-1], tail
