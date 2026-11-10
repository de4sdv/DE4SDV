"""Fixes to the campaign cases and to VC-DRIVING-029 and VC-DRIVING-035.

Most runs here are stubs that offer only what the case under test reads, so
each test names the one behaviour it pins; one test per fix repeats it on the
synthetic runs of make_synthetic_run.py through the real run reader.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import cases
import evaluate_campaign as ec
import strip
from conftest import edit_jsonl


# ------------------------------------------------------------------ every run of a role
# A campaign judges every run it holds. Two runs with the same runRole (ICD C4)
# are both judged: a role passes only if each of its runs passes, and every
# run is listed in measured.runs. Before, the last run of a role in directory
# order replaced the others, so a failing run next to a passing re-run with the
# same label gave a campaign pass.
class RoleRun:
    """A campaign run whose case outcome is fixed by the test."""

    def __init__(self, role: str, outcome: str, name: str):
        self._role, self.outcome, self._name = role, outcome, name
        self.root = Path("campaign") / name

    def role(self):
        return self._role

    def identity(self):
        return self._name


def fixed_outcome(run, vc):
    if run.outcome == cases.FAIL:
        return cases.bad(vc, {"run": run.identity()}, {}, [],
                         ["the deceleration is off by 1.5 m/s^2"])
    if run.outcome == cases.INCONCL:
        return cases.inconclusive(vc, "stop_response.standstill", None,
                                  "the stop never reached standstill")
    return cases.ok(vc, {"run": run.identity()}, {}, [])


@pytest.fixture
def outcome_by_run(monkeypatch):
    monkeypatch.setattr(cases, "evaluate_case", fixed_outcome)


STOP_ROLES = ec.REQUIRED_ROLES["stop-response"]


def test_campaign_fails_when_one_of_two_runs_of_a_role_fails(outcome_by_run):
    runs = [RoleRun("entry10", cases.FAIL, "entry10-a"),
            RoleRun("entry10", cases.PASS, "entry10-b"),
            RoleRun("entry20", cases.PASS, "entry20-a")]
    res = ec.aggregate("VC-DRIVING-020", runs, STOP_ROLES)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured)
    assert any("entry10" in n and "entry10-a" in n for n in res.notes), res.notes


def test_campaign_is_inconclusive_when_one_of_two_runs_of_a_role_is(outcome_by_run):
    runs = [RoleRun("entry10", cases.INCONCL, "entry10-a"),
            RoleRun("entry10", cases.PASS, "entry10-b"),
            RoleRun("entry20", cases.PASS, "entry20-a")]
    res = ec.aggregate("VC-DRIVING-022", runs, STOP_ROLES)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured)
    assert "entry10" in res.missing[0] and "entry10-a" in res.missing[0], res.missing


def test_campaign_lists_every_run_of_a_role(outcome_by_run):
    runs = [RoleRun("mismatch", cases.PASS, "mismatch-a"),
            RoleRun("mismatch", cases.PASS, "mismatch-b"),
            RoleRun("unpinned", cases.PASS, "unpinned-a")]
    res = ec.aggregate("VC-DRIVING-035", runs, ec.REQUIRED_ROLES["checkpoint-refusal"])
    assert res.outcome == cases.PASS, (res.outcome, res.notes)
    listed = res.measured["runs"]
    assert [(r["run_record_identity"], r["outcome"]) for r in listed["mismatch"]] == \
        [("mismatch-a", cases.PASS), ("mismatch-b", cases.PASS)], listed
    assert [r["path"] for r in listed["unpinned"]] == [str(Path("campaign") / "unpinned-a")]


# The observation campaign compares one run of each role with the first
# reference run; with two runs of a role the case cannot tell which of them is
# the campaign's, so it is inconclusive, names the role and lists its runs.
def plan(frame: int) -> dict:
    return {"frame": frame, "reference": f"id/{frame}", "file": "score/drivingAgent.jsonl",
            "rec": {"seq": frame}, "production_mono": 0.05 + 0.1 * frame,
            "samples": [{"acceleration": 0.1 * frame, "curvature": 0.0}] * 64}


class ReplayRun:
    """A run of SC-DRIVING-004 on the replayed inputs: its plans, its commands
    (one per plan frame unless `command_frames` names others; None: the run
    holds no command record, which the run reader reports as missing evidence)
    and the camera arrivals of its steps."""

    def __init__(self, role: str, frames, name: str | None = None, command_frames=()):
        self._role, self._frames = role, list(frames)
        self._command_frames = self._frames if command_frames == () else command_frames
        self._name = name or role
        self.root = Path("campaign") / self._name
        self.record = {"inputReplay": {"digest": "replay-digest"}}

    def role(self):
        return self._role

    def identity(self):
        return self._name

    def plans(self, required=True):
        return [plan(f) for f in self._frames]

    def commands(self):
        if self._command_frames is None:
            from runio import MissingEvidence
            raise MissingEvidence("score/drivingAgent.jsonl:out.command", None,
                                  "no record of this event in the file")
        return [{"reference": f"id/{f}", "production_mono": float(f), "accel": 0.1 * f,
                 "steer": 0.0} for f in self._command_frames]

    def input_steps(self):
        return [{"frame": f, "cameras": [{"arrival_mono_ns": int(round(f * 0.1 * 1e9))}]}
                for f in self._frames]


FULL = range(100, 200)


def test_observation_campaign_with_two_runs_of_a_role_is_inconclusive():
    runs = [ReplayRun("ref1", FULL), ReplayRun("ref2", FULL),
            ReplayRun("late", FULL, name="late-a"), ReplayRun("late", FULL[:10], name="late-b"),
            ReplayRun("stopped", FULL)]
    for case in (ec.vc018, ec.vc019):
        res = case(runs)
        assert res.outcome == cases.INCONCL, (res.vc, res.outcome, res.notes)
        assert "late" in res.missing[0], (res.vc, res.missing)
        assert [r["run_record_identity"] for r in res.measured["runs"]["late"]] == \
            ["late-a", "late-b"], (res.vc, res.measured)


# The same on the synthetic stop-response runs, through the run reader: a copy
# of the 10 m/s run whose deceleration is 3 m/s^2 sits next to an intact copy
# that comes later in directory order.
def test_stop_campaign_with_a_failing_copy_of_a_run_fails(run_for, tmp_path):
    root = tmp_path / "stop-campaign"
    root.mkdir()
    broken = strip.copy_run(run_for("stop-entry10").root, root / "a-entry10")
    strip.copy_run(run_for("stop-entry10").root, root / "b-entry10")
    strip.copy_run(run_for("stop-entry20").root, root / "c-entry20")

    def fn(data):
        if data.get("actuationTime", 0) >= 25.0:
            data["acceleration"] = -3.0
        return data
    assert edit_jsonl(broken / "score/actuationAdapter.jsonl", "out.actuation_state", fn) > 0
    v = ec.evaluate_campaign(root)["cases"]["VC-DRIVING-020"]
    assert v["outcome"] == cases.FAIL, v
    entry10 = v["measured"]["runs"]["entry10"]
    assert [(Path(r["path"]).name, r["outcome"]) for r in entry10] == \
        [("a-entry10", cases.FAIL), ("b-entry10", cases.PASS)], entry10


# ------------------------------------------------------------------ VC-DRIVING-018
# REQ-DRIVING-018: the plans and commands of the late and of the stopped run
# each differ from those of the first reference run by no more than the second
# reference run differs from the first. A plan (command) present in one run of
# a pair and not in the other is a difference: their number is compared with
# the reference pair's number, like every other signal. A signal whose records
# a run does not hold cannot be compared and leaves the case inconclusive; a
# difference measured on another signal still fails it.
def test_vc018_fails_when_the_stopped_run_lost_plans():
    res = ec.vc018([ReplayRun("ref1", FULL), ReplayRun("ref2", FULL), ReplayRun("late", FULL),
                    ReplayRun("stopped", FULL[:10])])
    assert res.outcome == cases.FAIL, (res.outcome, res.notes)
    s = res.measured["stopped_vs_reference"]
    assert (s["frames_only_in_b"], s["plans_compared"]) == (90, 10), s
    over = res.measured["over_the_spread"]["plans_in_one_run_only"]
    assert (over["reference_spread"], over["late"], over["stopped"]) == (0, 0, 90), over


def test_vc018_fails_when_the_late_run_lost_commands():
    res = ec.vc018([ReplayRun("ref1", FULL), ReplayRun("ref2", FULL),
                    ReplayRun("late", FULL, command_frames=FULL[:50]), ReplayRun("stopped", FULL)])
    assert res.outcome == cases.FAIL, (res.outcome, res.notes)
    over = res.measured["over_the_spread"]
    assert list(over) == ["commands_in_one_run_only"], over
    assert over["commands_in_one_run_only"]["late"] == 50, over


def test_vc018_counts_missing_plans_against_the_reference_pair():
    # the second reference run lacks the last ten plans; a stopped run that lacks
    # ten differs from the first reference run no more than the second one does
    res = ec.vc018([ReplayRun("ref1", FULL), ReplayRun("ref2", FULL[:90]), ReplayRun("late", FULL),
                    ReplayRun("stopped", FULL[:90])])
    assert res.outcome == cases.PASS, (res.outcome, res.notes, res.measured["over_the_spread"])
    assert res.measured["reference_spread"]["plans_in_one_run_only"] == 10


@pytest.mark.parametrize("absent", [[], None], ids=["no-command", "reader-missing-evidence"])
def test_vc018_without_command_records_is_inconclusive(absent):
    runs = [ReplayRun(role, FULL, command_frames=absent)
            for role in ("ref1", "ref2", "late", "stopped")]
    res = ec.vc018(runs)
    assert res.outcome == cases.INCONCL, (res.outcome, res.notes)
    assert "out.command" in res.missing[0], res.missing
    assert res.measured["late_vs_reference"]["plan_acceleration"] == 0.0, res.measured


def test_vc018_is_inconclusive_when_one_run_holds_no_command_record():
    res = ec.vc018([ReplayRun("ref1", FULL), ReplayRun("ref2", FULL), ReplayRun("late", FULL),
                    ReplayRun("stopped", FULL, command_frames=None)])
    assert res.outcome == cases.INCONCL, (res.outcome, res.notes)
    assert "out.command" in res.missing[0] and "stopped" in res.missing[0], res.missing


def test_vc018_fails_on_lost_plans_even_when_the_commands_cannot_be_compared():
    res = ec.vc018([ReplayRun("ref1", FULL), ReplayRun("ref2", FULL), ReplayRun("late", FULL[:50]),
                    ReplayRun("stopped", FULL, command_frames=None)])
    assert res.outcome == cases.FAIL, (res.outcome, res.notes)
    assert "plans_in_one_run_only" in res.measured["over_the_spread"], res.measured


# The same on the synthetic replay campaign, through the run reader.
def replay_campaign(run_for, tmp_path, tag):
    root = tmp_path / f"replay-{tag}"
    root.mkdir()
    for role in ("ref1", "ref2", "late", "stopped"):
        strip.copy_run(run_for(f"aaos-{role}").root, root / f"aaos-{role}")
    return root


def test_vc018_on_the_synthetic_replay_fails_when_the_stopped_run_lost_plans(run_for, tmp_path):
    root = replay_campaign(run_for, tmp_path, "lost")
    dropped = edit_jsonl(root / "aaos-stopped/score/drivingAgent.jsonl", "out.plan",
                         lambda d: None if 200 <= d.get("frameIndex", -1) < 250 else d)
    assert dropped == 50
    v = ec.evaluate_campaign(root)["cases"]["VC-DRIVING-018"]
    assert v["outcome"] == cases.FAIL, v
    assert v["measured"]["stopped_vs_reference"]["frames_only_in_b"] == 50, v["measured"]


def test_vc018_on_the_synthetic_replay_without_command_records_is_inconclusive(run_for, tmp_path):
    root = replay_campaign(run_for, tmp_path, "no-commands")
    for role in ("ref1", "ref2", "late", "stopped"):
        assert edit_jsonl(root / f"aaos-{role}/score/drivingAgent.jsonl", "out.command",
                          lambda d: None) > 0
    v = ec.evaluate_campaign(root)["cases"]["VC-DRIVING-018"]
    assert v["outcome"] == cases.INCONCL, v
    assert "out.command" in v["missing"][0], v["missing"]
