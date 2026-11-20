"""B2: VC-DRIVING-036, -037 and -042 on synthetic S1 sessions (one pass, one fail, one inconclusive each, and a
dropped image in the judged window giving inconclusive)."""

import pytest

import cases_da
import make_da_synthetic_run as syn
import runio_da
import terms

PASS, FAIL, INC, ERR = ("passBoundedVerification", "failObservedBehavior", "inconclusiveMissingEvidence",
                        "errorEvidence")


def judge(tmp_path, specs, **kw):
    root = syn.write_session(tmp_path / "session", specs, **kw)
    return cases_da.evaluate(runio_da.discover(root))


def run_entry(res, run_id):
    return next(r for r in res["measured"]["runs"] if r["run"] == run_id)


def window_of(spec):
    ticks = syn.simulate(spec)["ticks"]
    return terms.judged_run(ticks, terms.SETTINGS[spec.setting_id])["windowS"], ticks[0]["simTimeS"]


def test_all_pass_on_the_synthetic_s1(tmp_path):
    specs = syn.s1_specs(**{"012_20_r1": dict(eb_at_needed=4.8, lag_ticks=6, eb_accel=-12.0)})
    out = judge(tmp_path, specs)
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037", "VC-DRIVING-042"):
        assert out[vc]["outcome"] == PASS, (vc, out[vc]["missing"], out[vc]["notes"])
        assert out[vc]["verdict"] == "pass"
        assert len(out[vc]["measured"]["runs"]) == 10      # the two runs of the five judged settings
    # 036 is not met vacuously: the run with a late, hard braking has instants at a needed 5.0 m/s2 or more
    assert run_entry(out["VC-DRIVING-036"], "012_20_r1")["measured"]["instants"] > 0


def test_036_fail_when_the_last_command_brakes_less_than_5(tmp_path):
    specs = syn.s1_specs(**{"012_60_r1": dict(eb_at_needed=4.5, eb_accel=-4.0)})
    out = judge(tmp_path, specs)
    res = out["VC-DRIVING-036"]
    assert res["outcome"] == FAIL and res["verdict"] == "fail"
    e = run_entry(res, "012_60_r1")
    assert e["outcome"] == FAIL and e["measured"]["missedInstants"] > 0
    assert e["measured"]["firstMiss"]["acceleration"] == pytest.approx(-4.0)
    assert e["measured"]["firstMiss"]["neededDecelMps2"] >= 5.0


def test_036_fail_on_the_boundary_minus_4_99(tmp_path):
    specs = syn.s1_specs(**{"012_60_r1": dict(eb_at_needed=4.9, eb_accel=-4.99, lag_ticks=6)})
    assert judge(tmp_path, specs)["VC-DRIVING-036"]["outcome"] == FAIL


def test_036_inconclusive_when_a_setting_has_one_run(tmp_path):
    specs = [s for s in syn.s1_specs() if s.run_id != "013_60_r2"]
    res = judge(tmp_path, specs)["VC-DRIVING-036"]
    assert res["outcome"] == INC and res["verdict"] == "inconclusive"
    assert any("SC-DRIVING-013@60" in m and "1 run" in m for m in res["missing"])


def test_036_inconclusive_when_a_run_is_not_judged(tmp_path):
    specs = syn.s1_specs(**{"012_42_r2": dict(center_offset_m=0.3)})
    res = judge(tmp_path, specs)["VC-DRIVING-036"]
    assert res["outcome"] == INC
    e = run_entry(res, "012_42_r2")
    assert e["outcome"] == INC and any("center line" in m for m in e["missing"])
    assert any(m.startswith("setting SC-DRIVING-012@42 not judged: run 012_42_r2") for m in res["missing"])


def test_036_037_042_inconclusive_with_a_dropped_image_in_the_judged_window(tmp_path):
    spec = syn.s1_specs()[0]
    (w0, w1), base = window_of(spec)
    specs = syn.s1_specs(**{"012_20_r1": dict(drops_at_s=[round(w0 - base + 0.5, 2)])})
    out = judge(tmp_path, specs)
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037", "VC-DRIVING-042"):
        e = run_entry(out[vc], "012_20_r1")
        assert e["outcome"] == INC, vc
        assert any("drop.camera_image" in m and "judged window" in m for m in e["missing"]), e["missing"]
        assert out[vc]["outcome"] == INC


def test_a_drop_outside_the_judged_window_leaves_036_judged(tmp_path):
    specs = syn.s1_specs(**{"012_20_r1": dict(drops_at_s=[0.1, 0.2])})
    out = judge(tmp_path, specs)
    assert run_entry(out["VC-DRIVING-036"], "012_20_r1")["outcome"] == PASS
    assert out["VC-DRIVING-036"]["outcome"] == PASS


def test_a_failing_judged_run_gives_fail_even_with_a_setting_missing(tmp_path):
    specs = [s for s in syn.s1_specs(**{"012_20_r1": dict(warn_at_needed=None, eb_at_needed=None)})
             if not s.run_id.startswith("013_60")]
    out = judge(tmp_path, specs)
    assert out["VC-DRIVING-037"]["outcome"] == FAIL
    assert out["VC-DRIVING-042"]["outcome"] == FAIL
    assert any("SC-DRIVING-013@60" in m for m in out["VC-DRIVING-037"]["missing"])


def test_037_fail_on_contact_at_20(tmp_path):
    specs = syn.s1_specs(**{"012_20_r1": dict(warn_at_needed=None, eb_at_needed=None)})
    res = judge(tmp_path, specs)["VC-DRIVING-037"]
    assert res["outcome"] == FAIL
    m = run_entry(res, "012_20_r1")["measured"]
    assert m["contact"] is True and m["limitKmh"] == 0.0
    assert m["impactKmh"] == pytest.approx(21.0, abs=0.1)
    assert m["approachKmh"] == pytest.approx(21.0, abs=0.1)


def test_037_pass_on_contact_at_60_within_its_limit(tmp_path):
    # 60 km/h approach: limit 35 km/h (:263-267). A late braking that touches at about 20 km/h is within it.
    specs = syn.s1_specs(**{"012_60_r1": dict(eb_at_needed=6.5, eb_accel=-6.0, lag_ticks=6)})
    res = judge(tmp_path, specs)["VC-DRIVING-037"]
    m = run_entry(res, "012_60_r1")["measured"]
    assert m["contact"] is True and m["limitKmh"] == 35.0 and 0.0 < m["impactKmh"] <= 35.0
    assert res["outcome"] == PASS


def test_037_inconclusive_without_world_record(tmp_path):
    specs = syn.s1_specs(**{"012_42_r1": dict(no_world=True)})
    res = judge(tmp_path, specs)["VC-DRIVING-037"]
    assert res["outcome"] == INC
    assert any("world.jsonl" in m for m in run_entry(res, "012_42_r1")["missing"]) or \
        any("SC-DRIVING-012@42" in m for m in res["missing"])


def test_042_fail_without_a_warning(tmp_path):
    specs = syn.s1_specs(**{"012_42_r1": dict(warn_at_needed=None)})
    res = judge(tmp_path, specs)["VC-DRIVING-042"]
    assert res["outcome"] == FAIL
    assert run_entry(res, "012_42_r1")["measured"]["warningStarts"] == 0


def test_042_fail_when_the_warning_leads_the_braking_by_less_than_1_s(tmp_path):
    # REQ-DRIVING-042 (:338): at least 1.0 s; a lead between 0.5 and 1.0 s fails
    specs = syn.s1_specs(**{"012_20_r2": dict(warn_at_needed=2.0)})
    res = judge(tmp_path, specs)["VC-DRIVING-042"]
    assert res["outcome"] == FAIL
    m = run_entry(res, "012_20_r2")["measured"]
    assert 0.5 < m["leadS"] < 1.0


def test_042_inconclusive_when_a_run_is_missing(tmp_path):
    specs = [s for s in syn.s1_specs() if s.run_id != "012_60_r1"]
    res = judge(tmp_path, specs)["VC-DRIVING-042"]
    assert res["outcome"] == INC
    assert any("SC-DRIVING-012@60" in m for m in res["missing"])


def test_unreadable_world_gives_error_evidence(tmp_path):
    specs = syn.s1_specs(**{"012_20_r1": dict(broken_world_line=True)})
    out = judge(tmp_path, specs)
    assert run_entry(out["VC-DRIVING-036"], "012_20_r1")["outcome"] == ERR
    assert out["VC-DRIVING-036"]["outcome"] == ERR and out["VC-DRIVING-036"]["verdict"] == "error"
