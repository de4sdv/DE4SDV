"""B7 support: a run made inconclusive by a dropped image still reports what the criterion would read without the
dropped-image rule, as a measured value that never changes the outcome (attempt 3 holds drops in every run)."""

import cases_da
import make_da_synthetic_run as syn
import runio_da

INC, FAIL, PASS = "inconclusiveMissingEvidence", "failObservedBehavior", "passBoundedVerification"


def run_entry(res, run_id):
    return next(r for r in res["measured"]["runs"] if r["run"] == run_id)


def test_a_dropped_image_run_reports_its_reading_without_the_rule(tmp_path):
    specs = syn.s1_specs(**{"012_42_r1": dict(drops_at_s=[0.1], unmatched_ackermann=True),
                            "012_42_r2": dict(drops_at_s=[0.1])})
    out = cases_da.evaluate(runio_da.discover(syn.write_session(tmp_path / "s", specs)))
    e1 = run_entry(out["VC-DRIVING-038"], "012_42_r1")
    assert e1["outcome"] == INC
    assert e1["measured"]["withoutDropRule"]["outcome"] == FAIL
    assert e1["measured"]["withoutDropRule"]["measured"]["unmatched"][0]["seq"] == 99999
    e2 = run_entry(out["VC-DRIVING-038"], "012_42_r2")
    assert e2["outcome"] == INC and e2["measured"]["withoutDropRule"]["outcome"] == PASS
    # the reading never turns into the case's outcome
    assert out["VC-DRIVING-038"]["outcome"] == INC


def test_no_reading_without_the_rule_for_other_missing_evidence(tmp_path):
    specs = syn.s1_specs(**{"012_60_r2": dict(control_of_the_hero=False)})
    out = cases_da.evaluate(runio_da.discover(syn.write_session(tmp_path / "s", specs)))
    assert "withoutDropRule" not in run_entry(out["VC-DRIVING-038"], "012_60_r2")["measured"]
