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

The status lines of the READMEs state what the session records show (closure review of 86cadee0..87cc3ec8):

- P1: the drops of S1's camera images, from each run's `score_interface.jsonl` (`drop.camera_image`) inside the
  run's ticks (`world.jsonl`): each of the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 drops 23 or 24 in its first
  5 s and 0 to 2 later; the steering calibration run 34 and 4; the stop run 24 and then the 8 images of sim 2870.36 to
  2871.06 s, after `path_stop.json`'s stop instant (no `pass.camera_image` after it).
- P2: every `session.json` of phase 10: eleven sessions have started bench hosts; the results of four stand (p10-3
  run 2, p10-1 try 4, p10-2 attempt 3, S1); the seven others are listed with SID, kind, exit code and the step they
  ended at (`exit_code`, `failed_step` or `ended_by`).
- P5: the 16 `launch_manager.log` files of S1, line `[DE4SDV] warm start before the attach`: 2 passes each, 678.3 to
  706.8 ms. No Markdown file of the bench gives the warm start another duration.
"""

from __future__ import annotations

import re
from pathlib import Path

SESSION = Path(__file__).resolve().parents[1]
BENCH = SESSION.parent
README = SESSION / "README.md"
BENCH_README = BENCH / "README.md"
INTERFACE_README = BENCH / "score-interface" / "README.md"

# P5: from the 16 launch_manager.log files of S1
WARM_START = "2 passes, 678.3 to 706.8 ms"
# P1: the stop run's drops after the stop instant, as both READMEs give them (bench README in the present tense)
STOP_RUN_DROPS = ("drops 24 in its first 5 s and then 8 in a row right after the stop instant (sim 2870.36 to "
                  "2871.06 s): the interface keeps receiving images and drops them, because the candidate that takes "
                  "them is stopped.")
FOURTEEN_RUNS = "the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 (10 of them meet their entry conditions)"
# P2: (SID, the bullet's opening, its exit code and step) of each session.json under phase10/sessions
STANDING = [
    ("20261119T130414Z", "p10-3 run 2", "exit 0;"),
    ("20261119T160111Z", "p10-1 try 4", "exit 0;"),
    ("20261120T092051Z", "p10-2 attempt 3", "exit 5 on the simulator host's fetch"),
    ("20261121T014447Z", "The judged session S1", "exit 0;"),
]
OTHERS = [
    ("20261119T094924Z", "p10-3 run 1", "`7b940dc8`): exit 5 at the step `unit_inject`."),
    ("20261119T123015Z", "p10-1 try 1", "`0a1d83c3`): exit 5 at the step `port_test`."),
    ("20261119T123937Z", "p10-1 try 2", "`0a1d83c3`): exit 5 at the step `warmup`."),
    ("20261119T134840Z", "p10-1 try 3", "`14b77ecb`): exit 12 after its steps: the p10_1 check FAILed (C2 to C4 "
                                        "failed, C5 and C8 not run)."),
    ("20261119T174606Z", "p10-2 attempt 1", "`414fff5f`): exit 5 at the step `rec_run1`."),
    ("20261119T203947Z", "p10-2 attempt 2", "`39a964a2`): exit 5 at the step `app_restart_run1`."),
    ("20261121T011350Z", "The `s1` rehearsal", "`f03e3af9`): exit 6 at the S-CORE host's start: the simulator host "
                                               "started, the S-CORE host did not (no capacity in 8 rounds, then a "
                                               "quota error on NVIDIA_L4_GPUS), and no step ran."),
]


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


# ── the status lines (closure review of 86cadee0..87cc3ec8, P1, P2 and P5) ─────────────────────────────────────────────

def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def _session_status() -> tuple[str, list[str]]:
    # session/README.md's status: the text before its first section; each bullet joined with its continuation lines
    raw = README.read_text(encoding="utf-8").split("\n## ", 1)[0]
    bullets = [re.sub(r"\s+", " ", b).strip() for b in re.split(r"\n(?=- )", raw) if b.startswith("- ")]
    return re.sub(r"\s+", " ", raw), bullets


def test_p2_the_session_readme_lists_every_session_that_started_bench_hosts() -> None:
    status, bullets = _session_status()
    assert "these sessions have run on the cloud hosts" not in status
    assert ("Status: draft, not yet validated. Beyond the dry runs below, eleven sessions have started bench hosts "
            "(each session's `session.json`). The results of these four stand:") in status
    sids = [sid for sid, _, _ in STANDING + OTHERS]
    assert len(set(sids)) == 11
    assert sorted(re.findall(r"\b\d{8}T\d{6}Z\b", status)) == sorted(sids)
    assert len(bullets) == 11, bullets
    for sid, label, outcome in STANDING + OTHERS:
        [bullet] = [b for b in bullets if sid in b]
        assert bullet.startswith(f"- {label} (SID {sid}, "), bullet
        assert outcome in bullet, (outcome, bullet)
    others = status.index("The seven others, each at the bench commit named:")
    assert all(status.index(sid) < others for sid, _, _ in STANDING)
    assert all(status.index(sid) > others for sid, _, _ in OTHERS)


def test_p2_the_bench_readme_counts_the_sessions_that_started_bench_hosts() -> None:
    text = _flat(BENCH_README)
    assert "Four sessions have run" not in text
    assert ("Status: under construction, not yet validated. Eleven sessions have started bench hosts; "
            "`session/README.md` lists them all. The results of these four stand, each at the bench commit "
            "named:") in text


def test_p1_the_bench_readme_scopes_the_drops_to_the_runs_they_hold_for() -> None:
    text = _flat(BENCH_README)
    assert "each run drops" not in text
    assert f"(SID 20261121T014447Z, 2026-11-21, `508649ba`): {FOURTEEN_RUNS} and the stop run, exit 0." in text
    assert ("VC-DRIVING-038, -040, -041, -043 and -044 are inconclusive, although the warm start of D-S1-1 ran in all "
            f"16 runs, the steering calibration run among them ({WARM_START}): each of the 14 runs drops 23 or 24 "
            "camera images in its first 5 s and 0 to 2 isolated images later. The stop run " + STOP_RUN_DROPS) in text


def test_p1_the_interface_readme_states_the_calibration_and_the_stop_run_apart() -> None:
    text = _flat(INTERFACE_README)
    assert "each run still dropped" not in text
    assert (f"In S1 the warm start of patch 0005 ran in all 16 runs ({WARM_START}). Each of {FOURTEEN_RUNS} still "
            "drops 23 or 24 camera images in its first 5 s and 0 to 2 isolated images later. The steering "
            "calibration run drops 34 in its first 5 s and 4 later. The stop run " + STOP_RUN_DROPS) in text


def test_p5_every_bench_markdown_file_gives_the_warm_start_s1_logged() -> None:
    files = sorted(BENCH.rglob("*.md"))
    assert len(files) >= 18, files  # the bench's 18 Markdown files of 2026-11-21: a walk that stops early fails
    carriers = []
    for path in files:
        text = _flat(path)
        assert not re.search(r"warm start[^.]*\babout 0\.\d+ s\b", text), path
        for sentence in re.split(r"(?<=[.:])\s", text):
            if "warm start" in sentence and re.search(r"\b\d+ passes\b", sentence):
                assert WARM_START in sentence, (path, sentence)
        if WARM_START in text:
            carriers.append(path.relative_to(BENCH).as_posix())
    assert carriers == ["README.md", "score-interface/README.md"], carriers
