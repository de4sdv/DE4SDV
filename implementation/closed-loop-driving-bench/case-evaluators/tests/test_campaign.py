"""The multi-run cases: the campaign on its four runs, and what happens when a
run is missing or a planning time drifts."""

from __future__ import annotations

import json

import cases
import evaluate_campaign
import evaluate_run
import strip
from conftest import edit_jsonl


def campaign_copy(fixture_root, tmp_path, names, tag):
    root = tmp_path / f"campaign-{tag}"
    root.mkdir()
    for n in names:
        strip.copy_run(fixture_root / n, root / n)
    return root


def test_campaign_passes_on_the_fixture(fixture_root):
    report = evaluate_campaign.evaluate_campaign(fixture_root)
    outcomes = {vc: v["outcome"] for vc, v in report["cases"].items()}
    assert outcomes == {
        "VC-DRIVING-018": cases.PASS, "VC-DRIVING-019": cases.PASS,
        "VC-DRIVING-020": cases.PASS, "VC-DRIVING-021": cases.PASS,
        "VC-DRIVING-022": cases.PASS, "VC-DRIVING-035": cases.PASS,
    }, outcomes
    v18 = report["cases"]["VC-DRIVING-018"]["measured"]
    assert v18["reference_spread"]["plan_acceleration"] == 0.0
    assert v18["late_vs_reference"]["plan_acceleration"] == 0.0


def test_missing_run_makes_the_observation_campaign_inconclusive(fixture_root, tmp_path):
    root = campaign_copy(fixture_root, tmp_path,
                         ["aaos-ref1", "aaos-ref2", "aaos-late"], "no-stopped")
    report = evaluate_campaign.evaluate_campaign(root)
    for vc in ("VC-DRIVING-018", "VC-DRIVING-019"):
        v = report["cases"][vc]
        assert v["outcome"] == cases.INCONCL, v
        assert v["icd_changes"] == ["C4"]


def test_planning_p99_drifting_15_ms_fails_vc019(fixture_root, tmp_path):
    root = campaign_copy(fixture_root, tmp_path,
                         ["aaos-ref1", "aaos-ref2", "aaos-late", "aaos-stopped"],
                         "p99")

    def fn(data):
        data["productionTime"] = round(data["productionTime"] + 0.015, 6)
        return data
    assert edit_jsonl(root / "aaos-late/score/drivingAgent.jsonl", "out.plan", fn) > 0
    report = evaluate_campaign.evaluate_campaign(root)
    v = report["cases"]["VC-DRIVING-019"]
    assert v["outcome"] == cases.FAIL, v
    assert v["measured"]["largest_difference_s"] > 0.010
    # and the plans themselves are unchanged, so VC-018 still passes
    assert report["cases"]["VC-DRIVING-018"]["outcome"] == cases.PASS


def test_refusal_campaign_needs_both_starts(fixture_root, tmp_path):
    root = campaign_copy(fixture_root, tmp_path, ["refusal-mismatch"], "one-start")
    report = evaluate_campaign.evaluate_campaign(root)
    v = report["cases"]["VC-DRIVING-035"]
    assert v["outcome"] == cases.INCONCL
    assert "unpinned" in v["missing"][0]


# ---------------------------------------------------------------- the CLI contract
def test_evaluate_run_writes_verdicts_json(fixture_root, tmp_path):
    out = tmp_path / "v.json"
    report = evaluate_run.evaluate(fixture_root / "nominal")
    report_path = out
    report_path.write_text(json.dumps(report))
    loaded = json.loads(report_path.read_text())
    assert loaded["schema"] == "de4sdv.driving.case-verdicts.v1"
    assert loaded["run"]["scenario"] == "closedLoopRoute"
    assert loaded["summary"]["pass"] > 0
    assert isinstance(loaded["skipped"], dict)
    assert "VC-DRIVING-018" not in loaded["cases"]   # a campaign case, not a run case
    first = next(iter(loaded["cases"].values()))
    for key in ("vc", "outcome", "verdict", "measured", "thresholds", "evidence",
                "missing", "notes", "icd_changes"):
        assert key in first


def test_fault_run_does_not_judge_the_other_scenarios(fixture_root):
    report = evaluate_run.evaluate(fixture_root / "fault-camera_missing")
    assert report["run"]["scenario"] == "degradedInputOrPlan"
    assert all(vc.startswith("VC-DRIVING-02") or vc == "VC-DRIVING-029"
               for vc in report["cases"])
    assert "VC-DRIVING-001" not in report["cases"]
    assert "VC-DRIVING-018" not in report["cases"]


def test_unreadable_run_record_errors_everything(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    (d / "run_record.json").write_text("{not json")
    report = evaluate_run.evaluate(d)
    assert report["run"]["readable"] is False
    assert len(report["cases"]) == 33        # 35 minus the two campaign cases
    assert all(v["outcome"] == cases.ERROR for v in report["cases"].values())
