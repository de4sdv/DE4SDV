"""Tests for review findings on VC-DRIVING-001, -003, -004, -010 and -014.

Each test builds its synthetic run with make_synthetic_run.py in a pytest
temporary directory and edits a hard-linked copy of it, the way the review's
probes edited theirs. A test fails on the evaluator the review found.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cases
import make_synthetic_run
import strip
from conftest import verdict
from runio import Run

AGENT = "score/drivingAgent.jsonl"
C2 = "score/checkpointInputs.jsonl"
WORLD = "simulator/world.jsonl"


def rewrite(path: Path, fn) -> int:
    """Stream a JSONL file through fn(record), which returns the record (edited
    or not) or None to drop it. The file is replaced, never written into, so the
    hard-linked original keeps its bytes. Returns the records changed or dropped."""
    out, changed = [], 0
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            before = json.dumps(rec, sort_keys=True)
            new = fn(rec)
            if new is None:
                changed += 1
                continue
            if json.dumps(new, sort_keys=True) != before:
                changed += 1
            out.append(json.dumps(new, separators=(",", ":")))
    strip._replace(path, "\n".join(out) + "\n")
    return changed


@pytest.fixture(scope="module")
def straight(tmp_path_factory) -> Path:
    """A run of SC-DRIVING-001 without a fault: 400 steps, primed at frame 65,
    a plan at every step from 65 to 399, no stop response."""
    return make_synthetic_run.build(tmp_path_factory.mktemp("fixes-a") / "straight",
                                    scenario="closedLoopRoute", frames=400)


# ------------------------------------------------------------------ VC-DRIVING-001
# REQ-DRIVING-001: "... no two consecutive steps without one, from the end of
# priming to the end of the run or the start of the stop response." The run
# goes on while the world ticks. An agent that stops planning in mid-run
# (it hangs, crashes or is killed) leaves the steps after it without a plan.
VC001 = "VC-DRIVING-001"
CUT = 300


def agent_stops_after(d: Path, cut: int) -> None:
    """The agent writes no plan and no C2 record after step `cut`; the world
    ticks on to frame 399 and no stop response is recorded."""
    def fn(rec):
        data = rec["data"]
        f = data.get("frame", data.get("frameIndex"))
        if rec["event"] in ("out.checkpoint_inputs", "out.plan") and isinstance(f, int) \
                and f > cut:
            return None
        return rec
    assert rewrite(d / C2, fn) == 399 - cut
    assert rewrite(d / AGENT, fn) == 399 - cut


def test_vc001_an_agent_that_stops_planning_while_the_world_ticks_on_fails(straight, tmp_path):
    d = strip.copy_run(straight, tmp_path / "agent-stops")
    agent_stops_after(d, CUT)
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    m = res.measured
    assert m["last_step"] == 399, m                  # the world's last tick
    assert m["steps_without_a_new_plan"] == 399 - CUT, m
    assert m["failing_pairs"][0] == [CUT + 1, CUT + 2], m


def test_vc001_the_unedited_run_passes_to_the_worlds_last_tick(straight):
    res = verdict(Run(straight), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["first_step"] == 65 and res.measured["last_step"] == 399, res.measured
    assert res.measured["steps_without_a_new_plan"] == 0, res.measured


def test_vc001_a_shorter_world_record_does_not_shorten_the_window(straight, tmp_path):
    # the world record ends at frame 300; the agent's steps go on to 399
    d = strip.copy_run(straight, tmp_path / "short-world")
    assert rewrite(d / WORLD, lambda r: None if r["data"]["frame"] > CUT else r) == 399 - CUT
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["last_step"] == 399, res.measured


def test_vc001_without_a_world_record_the_window_ends_at_the_agents_last_step(straight,
                                                                           tmp_path):
    # as before the fix: with no world record the run's end is the agent's last
    # C2 record, and the verdict says so
    d = strip.copy_run(straight, tmp_path / "agent-stops-no-world")
    agent_stops_after(d, CUT)
    (d / WORLD).unlink()
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["last_step"] == CUT, res.measured
    assert any(WORLD in n for n in res.notes), res.notes
