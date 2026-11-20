"""Lane D: the evidence record of each run, RetainedAssistanceRunEvidence
(textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:150-243).

Every attribute is filled from the fetched session tree; an empty attribute gives inconclusiveMissingEvidence and the
record names it ("A missing or partial record gives inconclusive, never pass", :211-212).
"""

import json
import re
import subprocess
import sys

import pytest

import evaluate_da_campaign as edc
import evidence_record as er
import make_da_synthetic_run as syn
import runio_da
from conftest import HERE, MODEL

INC = "inconclusiveMissingEvidence"
DESK = {"engineer": "second engineer", "valuesMatch": True, "recordSha256": ["5ff680b0" * 8]}
RUN = "012_20_r1"


def records(root, desk=DESK, criteria="sha256:c", revision="blobs:r"):
    sess = runio_da.discover(root)
    return er.build_all(sess, criteria=criteria, revision=revision, desk=desk)


def session(tmp_path, **kw):
    return syn.write_session(tmp_path / "session", syn.s1_specs(), **kw)


def test_the_attributes_are_the_models():
    text = (MODEL / "driver_assistance_verification_evidence.sysml").read_text()
    block = text[text.index("item def RetainedAssistanceRunEvidence"):text.index("item def RetainedCommandFormAnalysis")]
    assert tuple(re.findall(r"^\s+attribute (\w+) :", block, re.M)) == er.ATTRIBUTES
    assert len(er.ATTRIBUTES) == 29


def test_every_attribute_filled_on_the_synthetic_session(tmp_path):
    recs = records(session(tmp_path))
    assert sorted(recs) == sorted([s.run_id for s in syn.s1_specs()])
    for rid, rec in recs.items():
        assert rec["outcome"] == er.COMPLETE, (rid, rec["missing"])
        assert rec["missing"] == [] and rec["emptyAttributes"] == []
        for name in er.ATTRIBUTES:
            if name == "setting" and rid == "stop":
                continue
            assert isinstance(rec["attributes"][name], str) and rec["attributes"][name], (rid, name)
    r = recs[RUN]["attributes"]
    assert r["setting"] == "SC-DRIVING-012@20" and r["scenario"] == "SC-DRIVING-012"
    assert r["runIdentity"] == "SC-DRIVING-012@20/r1" and r["upstreamRevision"].startswith("014e0e7a")
    assert r["contractIdentity"].startswith("de4sdv.driving.v1.CollisionWarningRequest")
    assert r["criteriaRecordIdentity"] == "sha256:c" and r["evaluatorRevision"] == "blobs:r"
    assert r["independentEngineerIdentity"] == "second engineer"


def test_the_stop_run_has_no_setting_and_is_complete(tmp_path):
    rec = records(session(tmp_path))["stop"]
    # setting: AssistanceSettingIdentity[0..1], "left empty for the further run"
    assert rec["attributes"]["setting"] is None and rec["outcome"] == er.COMPLETE
    assert rec["attributes"]["runIdentity"] == "stop/further"


def _json_edit(path, fn):
    d = json.loads(path.read_text())
    fn(d)
    path.write_text(json.dumps(d))


def _session_del(*keys):
    def fn(root):
        def edit(d):
            for k in keys:
                cur = d
                for part in k.split(".")[:-1]:
                    cur = cur[part]
                del cur[k.split(".")[-1]]
        _json_edit(root / "session.json", edit)
    return fn


def _run_file(pattern, fn):
    def edit(root):
        p = next(root.rglob(pattern.format(run=RUN)))
        fn(p)
    return edit


def _cand(key, value=None):
    def fn(p):
        _json_edit(p, lambda d: d.pop(key) if value is None else d.__setitem__(key, value))
    return _run_file("score_{run}/score_side/run/score/candidate_record.json", fn)


def _strip_real(p):
    lines = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    for x in lines:
        x.pop("t_real_ns", None)
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def _no_message(p):
    lines = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    p.write_text("\n".join(json.dumps({k: v for k, v in x.items() if k != "message"}) for x in lines) + "\n")


def _drop_candidate_and_bundle(root):
    _session_del("candidate")(root)
    _json_edit(next(root.rglob(f"score_{RUN}/staging.json")), lambda d: d.pop("bundle"))


EMPTIED = {
    "configurationIdentity": _session_del("configuration_identity"),
    "receiptSha256": _session_del("configuration_receipt_sha256"),
    "modelRevision": _session_del("bench_commit"),
    "candidateRecordIdentity": _run_file("score_{run}/score_side/run/score/identityRecorder.jsonl",
                                         lambda p: p.write_text("")),
    "upstreamRevision": _cand("upstream_revision"),
    "sourceDifference": _cand("source_difference"),
    "networkFileSha256": _cand("network_files", []),
    "configurationFileSha256": _cand("configuration_files", []),
    "launchSettings": _cand("launch_settings"),
    "candidateBuild": _drop_candidate_and_bundle,
    "visualizationRecorderDelay": _session_del("visualization_recorder_delay"),
    "scoreLifecycleVersion": _session_del("score_platform.lifecycle_version"),
    "scoreCommunicationVersion": _session_del("score_platform.communication_version"),
    "scoreSOMEIPGatewayCommit": _session_del("score_platform.someip_gateway_commit"),
    "simulatorBuild": _run_file("world_{run}/simulator/setting_record.json",
                                lambda p: _json_edit(p, lambda d: d.pop("simulator"))),
    "runIdentity": _session_del(f"score_runs.{RUN}.runIdentity"),
    "simulatedConfiguration": _session_del(f"score_runs.{RUN}.simulatedConfiguration"),
    "wallClockSpan": _run_file("world_{run}/simulator/world.jsonl", _strip_real),
    "executionEnvironmentIdentity": _session_del("execution_environment.ivi_image"),
    "contractIdentity": _run_file("capture_{run}/app_record_warning.jsonl", _no_message),
    "rawObservationArtifact": _run_file("score_{run}/score_side/run/score/actuationAdapter.jsonl",
                                        lambda p: p.unlink()),
    "benchRecordingArtifact": _run_file("rec_{run}/chase_view.mp4", lambda p: p.unlink()),
}


@pytest.mark.parametrize("attribute", sorted(EMPTIED))
def test_one_empty_attribute_gives_inconclusive_and_names_it(tmp_path, attribute):
    root = session(tmp_path)
    EMPTIED[attribute](root)
    rec = records(root)[RUN]
    assert rec["outcome"] == INC
    assert rec["emptyAttributes"] == [attribute], rec["missing"]
    assert any(m.startswith(f"{attribute}:") for m in rec["missing"]), rec["missing"]


def test_the_visualization_recording_is_part_of_the_bench_recording(tmp_path):
    root = session(tmp_path)
    _session_del(f"score_runs.{RUN}.visualization_recording")(root)
    rec = records(root)[RUN]
    assert rec["emptyAttributes"] == ["benchRecordingArtifact"]
    assert any("visualization" in m for m in rec["missing"])


def test_scenario_falls_back_to_the_session_entry(tmp_path):
    root = session(tmp_path)
    _run_file("world_{run}/simulator/setting_record.json",
              lambda p: _json_edit(p, lambda d: d["setting"].pop("scenario")))(root)
    assert records(root)[RUN]["attributes"]["scenario"] == "SC-DRIVING-012"
    _session_del(f"score_runs.{RUN}.scenario")(root)
    assert records(root)[RUN]["emptyAttributes"] == ["scenario"]


def test_identities_and_desk_named_when_absent(tmp_path):
    rec = records(session(tmp_path), desk=None, criteria=None, revision=None)[RUN]
    assert rec["emptyAttributes"] == ["criteriaRecordIdentity", "evaluatorRevision", "independentEngineerIdentity"]


def test_the_campaign_turns_a_pass_inconclusive_on_a_partial_record(tmp_path):
    root = session(tmp_path)
    (root / "reproduction_044.json").write_text(json.dumps(DESK))
    _session_del("configuration_identity")(root)
    doc = edc.run(root, None)
    assert set(doc["evidenceRecords"]) == {s.run_id for s in syn.s1_specs()}
    for vc, res in doc["cases"].items():
        assert res["outcome"] == INC, vc
        assert any("configurationIdentity" in m and "RetainedAssistanceRunEvidence" in m for m in res["missing"]), vc


def test_the_campaign_keeps_a_fail_on_a_partial_record(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(**{RUN: dict(warn_at_needed=None)}))
    _session_del("configuration_identity")(root)
    doc = edc.run(root, None)
    assert doc["cases"]["VC-DRIVING-042"]["outcome"] == "failObservedBehavior"
    assert any("configurationIdentity" in m for m in doc["cases"]["VC-DRIVING-042"]["missing"])


def test_the_campaign_passes_with_complete_records(tmp_path):
    root = session(tmp_path)
    (root / "reproduction_044.json").write_text(json.dumps(DESK))
    doc = edc.run(root, None)
    assert all(r["outcome"] == er.COMPLETE for r in doc["evidenceRecords"].values())
    assert {res["outcome"] for res in doc["cases"].values()} == {"passBoundedVerification"}
    rec = doc["evidenceRecords"][RUN]["attributes"]
    assert rec["criteriaRecordIdentity"] == doc["criteriaRecordIdentity"]
    assert rec["evaluatorRevision"] == doc["evaluatorRevision"]
    assert "VC-DRIVING-036" in rec["claimBoundary"]


def test_cli_writes_the_records(tmp_path):
    root = session(tmp_path)
    _session_del("configuration_identity")(root)
    out = tmp_path / "records.json"
    p = subprocess.run([sys.executable, "-B", str(HERE.parent / "evidence_record.py"), "--session", str(root),
                        "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    doc = json.loads(out.read_text())
    assert doc["records"][RUN]["emptyAttributes"] == ["configurationIdentity", "independentEngineerIdentity"]
    assert f"{RUN} {INC} configurationIdentity independentEngineerIdentity" in p.stdout


def test_a_partial_record_of_the_stop_run_alone_leaves_only_its_clauses_inconclusive(tmp_path):
    root = session(tmp_path)
    (root / "reproduction_044.json").write_text(json.dumps(DESK))
    _session_del("score_runs.stop.runIdentity")(root)
    doc = edc.run(root, None)
    assert doc["evidenceRecords"]["stop"]["emptyAttributes"] == ["runIdentity"]
    for vc in ("VC-DRIVING-038", "VC-DRIVING-043"):
        assert doc["cases"][vc]["outcome"] == INC, vc
    assert doc["cases"]["VC-DRIVING-040"]["outcome"] == "passBoundedVerification"


def test_candidate_build_from_the_staging_record_without_session_candidate(tmp_path):
    # attempt 3's session.json has candidate null; the S-CORE start's staging.json names the bundle
    root = session(tmp_path)
    _session_del("candidate")(root)
    rec = records(root)[RUN]
    assert rec["outcome"] == er.COMPLETE
    assert "/opt/da-b2/bundle" in rec["attributes"]["candidateBuild"]


def test_the_candidates_data_log_is_part_of_the_raw_artifacts(tmp_path):
    root = session(tmp_path)
    _run_file("score_{run}/candidate_rrd.json", lambda p: p.unlink())(root)
    rec = records(root)[RUN]
    assert rec["emptyAttributes"] == ["rawObservationArtifact"]
    assert any("candidate's data log" in m for m in rec["missing"])
