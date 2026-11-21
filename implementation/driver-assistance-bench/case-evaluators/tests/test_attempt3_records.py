"""B7: the evaluators on attempt 3's real records (session 20261120T092051Z, run1 and run2 of SC-DRIVING-012@20).

The records are not in the repository. Set DA_ATTEMPT3_ROOT to the incoming session tree
(`outputs/inc-driving-002/phase10/sessions/incoming_20261120T092051Z`) to run these; otherwise they skip.
Expected at the pin (plan section 5, B7; DECISIONS.md:2128): 036, 037 and 042 fail on 012@20; 038, 040, 041, 043
and 044 are inconclusive while D-S1-1 (dropped images at start-up) is open.
"""

import os
from pathlib import Path

import pytest

import evaluate_da_campaign as edc

ROOT = os.environ.get("DA_ATTEMPT3_ROOT")
pytestmark = pytest.mark.skipif(not ROOT or not Path(ROOT).is_dir(), reason="DA_ATTEMPT3_ROOT not set")


@pytest.fixture(scope="module")
def doc():
    return edc.run(Path(ROOT), None)


def runs(doc, vc):
    return {e["run"]: e for e in doc["cases"][vc]["measured"]["runs"]}


def test_two_runs_of_012_at_20_and_no_stop_run(doc):
    assert [(r["run"], r["setting"], r["repetition"]) for r in doc["runs"]] == [
        ("run1", "SC-DRIVING-012@20", 1), ("run2", "SC-DRIVING-012@20", 2)]


def test_036_037_042_fail_on_both_runs(doc):
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037", "VC-DRIVING-042"):
        assert doc["cases"][vc]["outcome"] == "failObservedBehavior", vc
        assert {e["outcome"] for e in runs(doc, vc).values()} == {"failObservedBehavior"}, vc
    r36 = runs(doc, "VC-DRIVING-036")
    assert r36["run1"]["measured"]["instants"] == 11 and r36["run1"]["measured"]["missedInstants"] == 11
    assert r36["run1"]["measured"]["firstMiss"]["frame"] == 2962386
    r37 = runs(doc, "VC-DRIVING-037")
    assert r37["run1"]["measured"]["contactFrame"] == 2962397
    assert r37["run1"]["measured"]["impactKmh"] == pytest.approx(18.93, abs=0.01)
    assert r37["run2"]["measured"]["impactKmh"] == pytest.approx(17.69, abs=0.01)
    assert {e["measured"]["warningStarts"] for e in runs(doc, "VC-DRIVING-042").values()} == {0}


def test_every_run_cases_inconclusive_by_the_start_up_drops(doc):
    for vc in ("VC-DRIVING-038", "VC-DRIVING-040", "VC-DRIVING-041", "VC-DRIVING-043", "VC-DRIVING-044"):
        assert doc["cases"][vc]["outcome"] == "inconclusiveMissingEvidence", vc
        for e in runs(doc, vc).values():
            assert e["outcome"] == "inconclusiveMissingEvidence"
            assert "drop.camera_image" in e["missing"][0] and "judged window" in e["missing"][0]
            assert e["measured"]["withoutDropRule"]["outcome"] == "passBoundedVerification", (vc, e["run"])


# attempt 3 is a p10-2 session of 2026-11-20: session.json has no s1 run identities or scenario digests (C5), and no
# producer writes the fields OBSERVABLES.md proposes for lane D, nor the candidate's visualization recording
ATTEMPT3_EMPTY = ["configurationIdentity", "receiptSha256", "visualizationRecorderDelay", "scoreLifecycleVersion",
                  "scoreCommunicationVersion", "scoreSOMEIPGatewayCommit", "runIdentity", "simulatedConfiguration",
                  "executionEnvironmentIdentity", "benchRecordingArtifact", "independentEngineerIdentity"]


def test_evidence_records_name_every_missing_attribute(doc):
    recs = doc["evidenceRecords"]
    assert sorted(recs) == ["run1", "run2"]
    for rid, rec in recs.items():
        assert rec["outcome"] == "inconclusiveMissingEvidence"
        assert rec["emptyAttributes"] == ATTEMPT3_EMPTY, (rid, rec["emptyAttributes"])
        assert [m.split(":")[0] for m in rec["missing"]] == ATTEMPT3_EMPTY
        a = rec["attributes"]
        assert a["upstreamRevision"] == "014e0e7a56ee8e597c2cab8175233f74edd9b856"
        assert a["contractIdentity"].startswith("de4sdv.driving.v1.CollisionWarningRequest")
        assert a["simulatorBuild"].startswith("1.0-14ac3b1a5")
        assert a["modelRevision"] == "39a964a2276a9fd80963dd540649f8dd9d7440a7"


def test_036_037_report_the_gains_unrecorded(doc):
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
        assert doc["cases"][vc]["measured"]["ackermannGains"] == {"requested": "unrecorded", "readBack": "unrecorded"}
