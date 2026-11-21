"""The rehearsal block of session/README.md runs a committed run list (closure review of 44a4be29, J2).

The block named a file under the lead's outputs, which no checkout holds, so its dry run as written was refused
with rc 2 ('refused: no run list'). The list now lives beside s1_runs.tsv, and every line of it is a line of the
judged list, so the rehearsal runs what S1 runs.
"""

from __future__ import annotations

import re
from pathlib import Path

SESSION = Path(__file__).resolve().parents[1]
README = SESSION / "README.md"
REHEARSAL_RUNS = SESSION / "s1_rehearsal_runs.tsv"
S1_RUNS = SESSION / "s1_runs.tsv"


def _rows(path: Path) -> list[tuple[str, ...]]:
    return [tuple(line.split("\t")) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def _rehearsal_block() -> str:
    text = README.read_text(encoding="utf-8")
    blocks = [b for b in re.findall(r"```bash\n(.*?)```", text, re.S) if "--rehearsal --runs" in b]
    assert len(blocks) == 1, f"{len(blocks)} bash blocks with --rehearsal --runs"
    return blocks[0]


def test_the_rehearsal_block_names_the_committed_run_list() -> None:
    lines = [ln for ln in _rehearsal_block().splitlines() if ln.startswith("R=")]
    assert lines == ['R="$PWD/$S/s1_rehearsal_runs.tsv"'], lines


def test_the_rehearsal_runs_are_012_at_20_r1_then_the_stop_run_each_a_line_of_the_judged_list() -> None:
    assert REHEARSAL_RUNS.is_file(), f"{REHEARSAL_RUNS.name} is not committed"
    rows = _rows(REHEARSAL_RUNS)
    assert rows == [("SC-DRIVING-012@20", "r1"), ("stop", "further")], rows
    judged = set(_rows(S1_RUNS))
    assert all(r in judged for r in rows), [r for r in rows if r not in judged]
