"""B3, B4, B5: VC-DRIVING-040, -041 (every warning or braking start at an imminent collision), -038 and -043 (over
the S-CORE path, with the stop clauses) and -044 (the record before the first command), on synthetic S1 sessions."""

import json

import cases_da
import make_da_synthetic_run as syn
import runio_da

PASS, FAIL, INC, BLOCKED = ("passBoundedVerification", "failObservedBehavior", "inconclusiveMissingEvidence",
                            "blockedTargetRuntime")
DESK = {"engineer": "second engineer", "valuesMatch": True, "recordSha256": ["5ff680b0" * 8]}


def judge(tmp_path, specs=None, desk=DESK, **kw):
    root = syn.write_session(tmp_path / "session", specs or syn.s1_specs(), **kw)
    return cases_da.evaluate(runio_da.discover(root), {"VC-DRIVING-044": desk} if desk else None)


def run_entry(res, run_id):
    return next(r for r in res["measured"]["runs"] if r["run"] == run_id)


# ------------------------------------------------------------------ B3: 040, 041
def test_040_041_pass_on_the_synthetic_s1(tmp_path):
    out = judge(tmp_path)
    for vc in ("VC-DRIVING-040", "VC-DRIVING-041"):
        assert out[vc]["outcome"] == PASS, (vc, out[vc]["missing"])
        assert len(out[vc]["measured"]["runs"]) == 14
        assert "stop" not in [r["run"] for r in out[vc]["measured"]["runs"]]
    e = run_entry(out["VC-DRIVING-040"], "012at20r1")
    assert e["measured"]["starts"] == 1 and e["measured"]["startsAtImminent"] == 1
    assert run_entry(out["VC-DRIVING-040"], "014at30r1")["measured"]["guidance"]["ttcAtTurnInS"] == 1.5


def test_040_fail_on_a_warning_start_before_imminence(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"012at20r1": dict(false_warning_at_s=1.0)}))
    res = out["VC-DRIVING-040"]
    assert res["outcome"] == FAIL
    e = run_entry(res, "012at20r1")
    assert e["outcome"] == FAIL and e["measured"]["firstStartNotImminent"]["scenarioTimeS"] < 1.1


def test_040_041_fail_on_starts_at_a_vehicle_outside_the_lane(tmp_path):
    # SC-DRIVING-014: the stationary vehicle stands outside the lane; a start there fails even when the gap and
    # closing speed would make it imminent (VC-040 doc; needs_requirements.sysml:183 "in its lane").
    out = judge(tmp_path, syn.s1_specs(**{"014at30r2": dict(brake_window_s=None, warn_at_needed=1.0,
                                                             eb_at_needed=4.0)}))
    for vc in ("VC-DRIVING-040", "VC-DRIVING-041"):
        assert out[vc]["outcome"] == FAIL, vc
        assert run_entry(out[vc], "014at30r2")["outcome"] == FAIL


def test_040_inconclusive_without_vehicles_ahead(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"013at30r2": dict(vehicles_ahead=False)}))
    res = out["VC-DRIVING-040"]
    assert res["outcome"] == INC
    assert any("vehiclesAhead" in m and "shared contract 1" in m for m in run_entry(res, "013at30r2")["missing"])


def test_040_without_any_start_needs_no_vehicles_ahead(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"015at40r1": dict(vehicles_ahead=False)}))
    assert run_entry(out["VC-DRIVING-040"], "015at40r1")["outcome"] == PASS


def test_040_041_inconclusive_with_a_drop_anywhere_in_the_run(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"015at40r2": dict(drops_at_s=[0.1])}))
    for vc in ("VC-DRIVING-040", "VC-DRIVING-041", "VC-DRIVING-038", "VC-DRIVING-044"):
        e = run_entry(out[vc], "015at40r2")
        assert e["outcome"] == INC, vc
        assert any("drop.camera_image" in m and "judged window" in m for m in e["missing"]), vc
        assert out[vc]["outcome"] == INC


def test_040_inconclusive_without_the_guidance_of_014(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"014at30r1": dict(guidance=None)}))
    res = out["VC-DRIVING-040"]
    assert res["outcome"] == INC
    assert any("guidance" in m for m in run_entry(res, "014at30r1")["missing"])
    assert out["VC-DRIVING-041"]["outcome"] == INC


def test_040_inconclusive_when_a_run_is_missing(tmp_path):
    out = judge(tmp_path, [s for s in syn.s1_specs() if s.run_id != "015at40r2"])
    assert out["VC-DRIVING-040"]["outcome"] == INC
    assert any("SC-DRIVING-015@40" in m and "1 run" in m for m in out["VC-DRIVING-040"]["missing"])


def test_041_fail_on_an_emergency_braking_start_before_imminence(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"013at30r1": dict(false_eb_at_s=1.0)}))
    res = out["VC-DRIVING-041"]
    assert res["outcome"] == FAIL
    e = run_entry(res, "013at30r1")
    assert e["measured"]["starts"] == 2 and e["measured"]["startsAtImminent"] == 1


def test_a_false_start_in_the_stop_run_is_not_read_by_040(tmp_path):
    out = judge(tmp_path, syn.s1_specs(stop=dict(false_warning_at_s=1.0, false_eb_at_s=1.5)))
    assert out["VC-DRIVING-040"]["outcome"] == PASS
    assert out["VC-DRIVING-041"]["outcome"] == PASS


# ------------------------------------------------------------------ B4: 038, 043
def test_038_043_pass_with_their_stop_clauses(tmp_path):
    out = judge(tmp_path)
    r38, r43 = out["VC-DRIVING-038"], out["VC-DRIVING-043"]
    assert r38["outcome"] == PASS, r38["missing"]
    assert r43["outcome"] == PASS, r43["missing"]
    assert len(r38["measured"]["runs"]) == 14 and len(r43["measured"]["runs"]) == 10
    assert r38["measured"]["stopClause"]["outcome"] == PASS
    assert r43["measured"]["stopClause"]["outcome"] == PASS
    assert run_entry(r38, "012at20r1")["measured"]["matched"] > 0
    assert run_entry(r43, "012at20r1")["measured"]["receipts"] > 0


def test_038_fail_on_an_actuation_without_its_command(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"012at42r1": dict(unmatched_ackermann=True)}))
    e = run_entry(out["VC-DRIVING-038"], "012at42r1")
    assert out["VC-DRIVING-038"]["outcome"] == FAIL and e["outcome"] == FAIL
    assert e["measured"]["unmatched"][0]["seq"] == 99999


def test_038_fail_on_a_check_value_that_differs_from_the_crc(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"013at60r1": dict(bad_crc_at_adapter=True)}))
    assert out["VC-DRIVING-038"]["outcome"] == FAIL
    assert run_entry(out["VC-DRIVING-038"], "013at60r1")["measured"]["unmatched"][0]["seq"] == 3


def test_038_fail_on_an_actuation_from_another_control_source(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"013at30r2": dict(foreign_control_source=True)}))
    e = run_entry(out["VC-DRIVING-038"], "013at30r2")
    assert out["VC-DRIVING-038"]["outcome"] == FAIL and e["outcome"] == FAIL
    assert e["measured"]["unmatched"] == [{"seq": 3, "frame": e["measured"]["unmatched"][0]["frame"],
                                           "controlSource": "replay",
                                           "adapterCheckValue": e["measured"]["unmatched"][0]["scoreCrc"],
                                           "scoreCrc": e["measured"]["unmatched"][0]["adapterCheckValue"]}]


def test_038_fail_on_a_world_side_control_call(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"015at40r1": dict(world_side_control_calls=1)}))
    assert out["VC-DRIVING-038"]["outcome"] == FAIL
    assert run_entry(out["VC-DRIVING-038"], "015at40r1")["measured"]["worldSideControlCallsMax"] == 1


def test_038_fail_on_control_applied_after_the_stop(tmp_path):
    out = judge(tmp_path, syn.s1_specs(stop=dict(commands_after_stop=True, brake_window_s=(3.0, 4.0))))
    res = out["VC-DRIVING-038"]
    assert res["outcome"] == FAIL
    assert res["measured"]["stopClause"]["outcome"] == FAIL
    assert res["measured"]["stopClause"]["measured"]["controlsAfterStop"] > 0


def test_038_fail_on_a_world_control_change_after_the_stop(tmp_path):
    out = judge(tmp_path, syn.s1_specs(stop=dict(world_control_change_after_stop=True)))
    sc = out["VC-DRIVING-038"]["measured"]["stopClause"]
    assert sc["outcome"] == FAIL and out["VC-DRIVING-038"]["outcome"] == FAIL
    assert sc["measured"]["controlsAfterStop"] == 0 and sc["measured"]["controlChangesAfterStop"] > 0


def test_038_fail_on_an_actuation_after_the_stop_that_changes_nothing(tmp_path):
    out = judge(tmp_path, syn.s1_specs(stop=dict(commands_after_stop=True)))
    sc = out["VC-DRIVING-038"]["measured"]["stopClause"]
    assert sc["outcome"] == FAIL
    assert sc["measured"]["controlsAfterStop"] > 0 and sc["measured"]["controlChangesAfterStop"] == 0


def test_038_inconclusive_without_the_worlds_statement(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"012at60r2": dict(control_of_the_hero=False)}))
    assert out["VC-DRIVING-038"]["outcome"] == INC
    assert any("controlOfTheHero" in m for m in run_entry(out["VC-DRIVING-038"], "012at60r2")["missing"])


def test_038_043_inconclusive_without_the_stop_run(tmp_path):
    out = judge(tmp_path, [s for s in syn.s1_specs() if s.run_id != "stop"])
    for vc in ("VC-DRIVING-038", "VC-DRIVING-043"):
        assert out[vc]["outcome"] == INC
        assert any("stop run" in m for m in out[vc]["missing"]), out[vc]["missing"]


def test_038_043_inconclusive_without_the_stop_record(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    sj = json.loads((root / "session.json").read_text())
    del sj["score_runs"]["stop"]["pathStop"]
    (root / "session.json").write_text(json.dumps(sj))
    out = cases_da.evaluate(runio_da.discover(root), {"VC-DRIVING-044": DESK})
    for vc in ("VC-DRIVING-038", "VC-DRIVING-043"):
        assert out[vc]["outcome"] == INC
        assert any("runTarget path_stopped" in m for m in out[vc]["measured"]["stopClause"]["missing"])


def test_038_blocked_when_the_path_stop_failed(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    sj = json.loads((root / "session.json").read_text())
    sj["score_runs"]["stop"]["pathStop"]["rc"] = 3
    (root / "session.json").write_text(json.dumps(sj))
    out = cases_da.evaluate(runio_da.discover(root), {"VC-DRIVING-044": DESK})
    assert out["VC-DRIVING-038"]["measured"]["stopClause"]["outcome"] == BLOCKED
    assert out["VC-DRIVING-038"]["outcome"] == BLOCKED and out["VC-DRIVING-038"]["verdict"] == "inconclusive"


def test_043_fail_on_a_receipt_with_no_request(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"013at30r2": dict(forged_receipt=True)}))
    res = out["VC-DRIVING-043"]
    assert res["outcome"] == FAIL
    assert run_entry(res, "013at30r2")["measured"]["unmatched"]


def test_043_reads_no_run_of_014_or_015(tmp_path):
    out = judge(tmp_path, syn.s1_specs(**{"014at30r1": dict(forged_receipt=True)}))
    assert out["VC-DRIVING-043"]["outcome"] == PASS


def test_043_fail_on_a_receipt_after_the_stop(tmp_path):
    out = judge(tmp_path, syn.s1_specs(stop=dict(receipt_after_stop=True)))
    res = out["VC-DRIVING-043"]
    assert res["outcome"] == FAIL and res["measured"]["stopClause"]["outcome"] == FAIL
    assert res["measured"]["stopClause"]["measured"]["receiptsAfterStop"] > 0


def test_043_fail_on_a_receipt_read_after_the_stop(tmp_path):
    out = judge(tmp_path, syn.s1_specs(stop=dict(late_receipt_after_stop=True)))
    sc = out["VC-DRIVING-043"]["measured"]["stopClause"]
    assert sc["outcome"] == FAIL
    assert sc["measured"]["receiptsReadAfterStop"] == 1 and sc["measured"]["receiptsIssuedAfterStop"] == 0


def test_043_sim_time_check_alone_without_the_clock(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(stop=dict(receipt_after_stop=True)))
    (root / "guest" / "out" / "ivi_clock_stop" / "clock.jsonl").unlink()
    out = cases_da.evaluate(runio_da.discover(root), {"VC-DRIVING-044": DESK})
    sc = out["VC-DRIVING-043"]["measured"]["stopClause"]
    assert sc["outcome"] == FAIL and sc["measured"]["receiptsReadAfterStop"] == 0
    assert sc["measured"]["receiptsIssuedAfterStop"] > 0
    assert any("no IVI clock mark" in n for n in sc["measured"]["notes"])


def test_043_inconclusive_without_the_app_record(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    (root / "guest" / "out" / "capture_012at42r2" / "app_record_warning.jsonl").unlink()
    out = cases_da.evaluate(runio_da.discover(root), {"VC-DRIVING-044": DESK})
    assert out["VC-DRIVING-043"]["outcome"] == INC
    assert any("app_record_warning.jsonl" in m for m in run_entry(out["VC-DRIVING-043"], "012at42r2")["missing"])


def test_038_043_inconclusive_with_a_drop_in_the_stop_run(tmp_path):
    out = judge(tmp_path, syn.s1_specs(stop=dict(drops_at_s=[0.5])))
    for vc in ("VC-DRIVING-038", "VC-DRIVING-043"):
        assert out[vc]["measured"]["stopClause"]["outcome"] == INC
        assert out[vc]["outcome"] == INC


# ------------------------------------------------------------------ B5: 044
def test_044_pass_with_the_desk_reproduction(tmp_path):
    out = judge(tmp_path)
    res = out["VC-DRIVING-044"]
    assert res["outcome"] == PASS, res["missing"]
    assert len(res["measured"]["runs"]) == 14
    assert run_entry(res, "012at20r1")["measured"]["recordBeforeFirstCommandNs"] > 0


def test_044_inconclusive_without_the_desk_reproduction(tmp_path):
    res = judge(tmp_path, desk=None)["VC-DRIVING-044"]
    assert res["outcome"] == INC
    assert any("reproduction_044.json" in m and "lane F2" in m for m in res["missing"])


def test_044_fail_when_the_record_comes_after_the_first_command(tmp_path):
    res = judge(tmp_path, syn.s1_specs(**{"013at60r2": dict(record_after_first_command=True)}))["VC-DRIVING-044"]
    assert res["outcome"] == FAIL
    assert run_entry(res, "013at60r2")["measured"]["recordBeforeFirstCommandNs"] < 0


def test_044_fail_on_an_empty_difference(tmp_path):
    res = judge(tmp_path, syn.s1_specs(**{"012at42r2": dict(diff_bytes=0)}))["VC-DRIVING-044"]
    assert res["outcome"] == FAIL


def test_044_fail_when_the_desk_values_differ(tmp_path):
    res = judge(tmp_path, desk=dict(DESK, valuesMatch=False))["VC-DRIVING-044"]
    assert res["outcome"] == FAIL


def test_044_inconclusive_when_the_desk_did_not_reproduce_a_record(tmp_path):
    res = judge(tmp_path, desk=dict(DESK, recordSha256=["0" * 64]))["VC-DRIVING-044"]
    assert res["outcome"] == INC
    assert any("5ff680b0" in m for m in res["missing"])
