"""The readers against the producers' own names (lead contracts of 2026-11-20, DECISIONS.md, the S1 integration lanes'
entry), and the boundary of VC-DRIVING-042.

1. guidance: setting_record.json["site"] = SiteSpec.as_record() (world-side/sites.py:625-630 at b9938fe9), the
   guidance of 014 and 015 under ["site"]["guidance"] with the keys of GUIDANCE_014 and GUIDANCE_015 (:39-48).
2. stop run: run id `stop`, setting `stop` (world-side/scenarios.py STOP_RUN at db6bf573); its setting record says
   kind "run" (da_world_side.py cmd_run).
3. stop instant: session.json s1.stop_instant and s1.path_stop, as session/da_session.sh writes them (a0bd4bd7).
4. rehearsal: a session.json with rehearsal true is never judged.
5. Ackermann gains: optional; reported in VC-DRIVING-036 and -037 beside the calib-decel summary, "unrecorded" when
   absent.
"""

import json
import subprocess
import sys

import pytest

import cases_da
import evaluate_da_campaign as edc
import make_da_synthetic_run as syn
import runio_da
from conftest import HERE

PASS, FAIL, INC = "passBoundedVerification", "failObservedBehavior", "inconclusiveMissingEvidence"
DESK = {"engineer": "second engineer", "valuesMatch": True, "recordSha256": ["5ff680b0" * 8]}


def judge(tmp_path, specs=None, **kw):
    root = syn.write_session(tmp_path / "session", specs or syn.s1_specs(), **kw)
    return cases_da.evaluate(runio_da.discover(root), {"VC-DRIVING-044": DESK})


def run_entry(res, run_id):
    return next(r for r in res["measured"]["runs"] if r["run"] == run_id)


# ------------------------------------------------------------------ contract 1: the site record's guidance
def test_040_reads_the_guidance_from_the_site_record(tmp_path):
    out = judge(tmp_path)
    for rid, key, value in (("014_30_r1", "ttcAtTurnInMaxS", 1.6), ("015_40_r2", "egoAtTurnBeginMinKmh", 26.0)):
        e = run_entry(out["VC-DRIVING-040"], rid)
        assert e["outcome"] == PASS, e["missing"]
        assert e["measured"]["guidance"][key] == value


def test_a_top_level_guidance_is_not_the_site_record(tmp_path):
    # the old proposal (setting_record.json["guidance"]) is no longer read
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    p = next(root.rglob("world_014_30_r1/simulator/setting_record.json"))
    rec = json.loads(p.read_text())
    rec["guidance"] = rec.pop("site")["guidance"]
    p.write_text(json.dumps(rec))
    out = cases_da.evaluate(runio_da.discover(root), {"VC-DRIVING-044": DESK})
    e = run_entry(out["VC-DRIVING-040"], "014_30_r1")
    assert e["outcome"] == INC
    assert any("site.guidance" in m for m in e["missing"]), e["missing"]


@pytest.mark.parametrize("rid,key", [("014_30_r2", "ttcAtOverlapZeroMaxS"), ("014_30_r1", "atCurveEntryMinKmh"),
                                     ("015_40_r1", "ttcAtTurnBeginMaxS"), ("015_40_r2", "egoAfterMinKmh")])
def test_040_inconclusive_when_the_guidance_lacks_a_speed_or_a_time_to_collision(tmp_path, rid, key):
    g = dict(syn.GUIDANCE_014 if rid.startswith("014") else syn.GUIDANCE_015)
    del g[key]
    out = judge(tmp_path, syn.s1_specs(**{rid: dict(guidance=g)}))
    e = run_entry(out["VC-DRIVING-040"], rid)
    assert e["outcome"] == INC
    assert any(key in m for m in e["missing"]), e["missing"]


# ------------------------------------------------------------------ contract 2: the stop run
def test_the_stop_run_in_the_producers_shape(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    rec = json.loads(next(root.rglob("world_stop/simulator/setting_record.json")).read_text())
    assert rec["kind"] == "run" and rec["setting"]["setting_id"] == "stop"
    sess = runio_da.discover(root)
    assert sess.stop_run is not None and sess.stop_run.run_id == "stop"
    assert "stop" not in [r.run_id for r in sess.runs] and len(sess.runs) == 14


def test_a_run_of_setting_stop_under_another_label_is_the_stop_run(tmp_path):
    # contract 2: the setting is `stop`; a stop run whose label differs is still no run of a setting
    specs = syn.s1_specs()
    specs[-1].run_id = "further"
    sess = runio_da.discover(syn.write_session(tmp_path / "session", specs))
    assert sess.stop_run is not None and sess.stop_run.run_id == "further"
    assert all(r.setting_id != "stop" for r in sess.runs)


# ------------------------------------------------------------------ contract 4: rehearsals
def test_the_campaign_refuses_a_rehearsal(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(), session_extra={"rehearsal": True})
    doc = edc.run(root, None)
    assert doc["cases"] == {}
    assert "rehearsal" in doc["refused"] and "session.json" in doc["refused"]
    out = tmp_path / "verdicts.json"
    p = subprocess.run([sys.executable, "-B", str(HERE.parent / "evaluate_da_campaign.py"), "--session", str(root),
                        "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 3, (p.stdout, p.stderr)
    assert "rehearsal" in p.stdout + p.stderr
    assert json.loads(out.read_text())["refused"] == doc["refused"]


def test_a_session_with_rehearsal_false_is_judged(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(), session_extra={"rehearsal": False})
    doc = edc.run(root, None)
    assert "refused" not in doc and len(doc["cases"]) == 8


# ------------------------------------------------------------------ contract 5: the Ackermann gains
def test_036_037_report_the_gains_unrecorded_when_absent(tmp_path):
    doc = edc.run(syn.write_session(tmp_path / "session", syn.s1_specs()), None)
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
        assert doc["cases"][vc]["measured"]["ackermannGains"] == {"requested": "unrecorded",
                                                                  "readBack": "unrecorded"}
        assert any("Ackermann" in n and "unrecorded" in n for n in doc["cases"][vc]["notes"])
    assert "ackermannGains" not in doc["cases"]["VC-DRIVING-042"]["measured"]


def test_036_037_report_the_requested_and_the_read_back_gains(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(), session_extra={"ackermann_gains": "v1"})
    cal = root / "sim-lead-fetch" / "x" / "out" / "calibrate" / "calib_decel" / "simulator"
    cal.mkdir(parents=True)
    read_back = {"speed_kp": 0.3, "accel_kp": 0.1}
    (cal / "calibration_decel.json").write_text(json.dumps({"summary": {"allFollowWithinProposal": True,
                                                                        "worstRatio": 0.99},
                                                            "ackermannGainsReadBack": read_back}))
    doc = edc.run(root, None)
    g = doc["cases"]["VC-DRIVING-036"]["measured"]["ackermannGains"]
    assert g["requested"] == [{"file": "session.json", "key": "ackermann_gains", "value": "v1"}]
    assert g["readBack"] == [{"file": "sim-lead-fetch/x/out/calibrate/calib_decel/simulator/calibration_decel.json",
                              "key": "ackermannGainsReadBack", "value": read_back}]
    assert doc["cases"]["VC-DRIVING-037"]["measured"]["ackermannGains"] == g
    assert doc["cases"]["VC-DRIVING-036"]["measured"]["calibrationDecel"]["worstRatio"] == 0.99


# ------------------------------------------------------------------ VC-DRIVING-042: the 1.0 s boundary
def _042(tmp_path, **kw):
    # a warning start set at an exact lead before the first emergency braking start; the policy's own warning off
    specs = syn.s1_specs(**{"012_42_r1": dict({"warn_at_needed": None}, **kw)})
    return run_entry(judge(tmp_path, specs)["VC-DRIVING-042"], "012_42_r1")


def test_042_fails_at_a_lead_of_0_99_s(tmp_path):
    # REQ-DRIVING-042 (needs_requirements.sysml:338): "at least 1.0 s of simulation time before"
    e = _042(tmp_path, warn_lead_s=0.99)
    assert e["measured"]["leadS"] == pytest.approx(0.99, abs=1e-9)
    assert e["outcome"] == FAIL


def test_042_passes_at_a_lead_of_1_0_s(tmp_path):
    e = _042(tmp_path, warn_lead_s=1.0)
    assert e["measured"]["leadS"] == pytest.approx(1.0, abs=1e-9)
    assert e["outcome"] == PASS


def test_042_passes_with_a_warning_and_no_emergency_braking(tmp_path):
    # "... before the start of the first emergency braking of the run when the run has one"
    e = _042(tmp_path, eb_at_needed=None, warn_at_needed=1.0)
    m = e["measured"]
    assert m["imminent"] is True and m["warningStarts"] >= 1 and m["firstEmergencyBrakingSimS"] is None
    assert e["outcome"] == PASS


def test_042_fails_without_a_warning_and_without_emergency_braking(tmp_path):
    e = _042(tmp_path, eb_at_needed=None)
    assert e["measured"]["imminent"] is True and e["measured"]["warningStarts"] == 0
    assert e["outcome"] == FAIL
