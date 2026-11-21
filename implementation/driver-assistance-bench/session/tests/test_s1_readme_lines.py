"""The s1 command lines of session/README.md carry the owner's gains and the rehearsal's cap.

- D-S1-2, the owner's decision of 2026-11-21 (option A): the judged runs use the v1 Ackermann gains, applied and read
  back for every hero. The rehearsal runs as S1 does, so all four lines (the dry run and the run of both blocks) give
  `--ackermann-gains v1`; without it the session keeps CARLA's own gains (`default`).
- Closure review of 44a4be29, J3: the rehearsal's decision names a cap of EUR 2.50 and the code's default
  (CAP_EUR_S1_REHEARSAL) is EUR 2.00, so both rehearsal lines give `--cap-eur 2.50`. The judged lines keep CAP_EUR_S1.
- D-S1-3, the owner's decision of 2026-11-21: the judged runs use an on-demand L4. hosts.env's SCORE_EUR_H (0.483)
  is the Spot rate, so the cost watchdog would count about EUR 0.32 an hour low (closure review J8); both judged
  lines give `SCORE_EUR_H=0.806`, the on-demand rate, and the rehearsal (on Spot) gives none.
- Closure review of 44a4be29..86cadee0, R3: the visualization fetch after s1 (`da-vis`) runs the same on-demand L4,
  and fetch_chase.sh --role score records SCORE_EUR_H in fetch_visualization.json, so its line gives
  `SCORE_EUR_H=0.806` as well.
"""

from __future__ import annotations

import re
from pathlib import Path

SESSION = Path(__file__).resolve().parents[1]
README = SESSION / "README.md"


def _s1_lines() -> list[str]:
    # each command whole: a line continued with a backslash is joined to the next, so `env -i ...` is part of it
    text = README.read_text(encoding="utf-8")
    return [re.sub(r"\s+", " ", ln.strip()) for b in re.findall(r"```bash\n(.*?)```", text, re.S)
            for ln in b.replace("\\\n", " ").splitlines() if "da_session.sh --kind s1 " in ln]


def test_the_readme_has_the_dry_run_and_the_run_of_s1_and_of_its_rehearsal() -> None:
    lines = _s1_lines()
    assert len(lines) == 4, lines
    assert sum("--rehearsal" in ln for ln in lines) == 2, lines
    assert sum("--dry-run" in ln for ln in lines) == 2, lines


def test_every_s1_line_gives_the_v1_gains_of_d_s1_2() -> None:
    assert [ln for ln in _s1_lines() if "--ackermann-gains v1" not in ln] == []


def test_the_rehearsal_lines_give_the_cap_their_decision_names_and_the_judged_lines_none() -> None:
    lines = _s1_lines()
    assert [ln for ln in lines if "--rehearsal" in ln and "--cap-eur 2.50" not in ln] == []
    assert [ln for ln in lines if "--rehearsal" not in ln and "--cap-eur" in ln] == []


def test_the_judged_lines_give_the_on_demand_l4_rate_and_the_rehearsal_lines_none() -> None:
    lines = _s1_lines()
    judged = [ln for ln in lines if "--rehearsal" not in ln]
    assert len(judged) == 2, judged
    assert [ln for ln in judged if not re.search(r"env -i .*\bSCORE_EUR_H=0\.806 .*da_session\.sh", ln)] == []
    assert [ln for ln in lines if "--rehearsal" in ln and "SCORE_EUR_H" in ln] == []


def test_the_visualization_fetch_after_s1_gives_the_on_demand_l4_rate() -> None:
    text = README.read_text(encoding="utf-8")
    lines = [re.sub(r"\s+", " ", ln.strip()) for b in re.findall(r"```bash\n(.*?)```", text, re.S)
             for ln in b.replace("\\\n", " ").splitlines() if "fetch_chase.sh --role score " in ln]
    assert len(lines) == 1, lines
    assert "--unit=da-vis-$SID" in lines[0], lines
    assert re.search(r"env -i .*\bSCORE_EUR_H=0\.806 .*fetch_chase\.sh --role score", lines[0]), lines
