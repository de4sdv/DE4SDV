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
from case_evaluators_testkit import HERE, MODEL

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


def test_a_missing_visualization_recording_quotes_the_entrys_own_reason(tmp_path):
    # closure review of 44a4be29..86cadee0, R6: the cause is the entry's reason, as da_session.sh write_record
    # writes it, not a Launch Manager configuration that since V-a sets DE4SDV_VISUALIZATION_RECORD
    root = session(tmp_path)
    reason = (f"no visualization_recording.json of this run in the fetched S-CORE output (score/out/score_{RUN}/): "
              "the run's S-CORE stop did not run or wrote none, or the S-CORE host was not fetched")
    _json_edit(root / "session.json", lambda d: d["score_runs"][RUN].__setitem__(
        "visualization_recording", {"path": None, "sha256": None, "bytes": None, "frames": None, "reason": reason}))
    rec = records(root)[RUN]
    assert rec["emptyAttributes"] == ["benchRecordingArtifact"], rec["missing"]
    text = next(m for m in rec["missing"] if m.startswith("benchRecordingArtifact:"))
    assert reason in text, text
    assert "Launch Manager" not in text, text


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
        assert any(n.startswith("observed passBoundedVerification") for n in res["notes"]), (vc, res["notes"])


# The lead's reading of 2026-11-21 (driver_assistance_verification_evidence.sysml:126-127 and :211-212): a run whose
# evidence record is partial gives inconclusive for that run, never pass and never fail. A case's fail stands only
# when at least one run that shows the fail has a complete record.
FAIL = "failObservedBehavior"


def test_a_fail_on_runs_whose_records_are_all_partial_gives_inconclusive(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(**{RUN: dict(warn_at_needed=None)}))
    _session_del("configuration_identity")(root)
    doc = edc.run(root, None)
    res = doc["cases"]["VC-DRIVING-042"]
    assert [e["outcome"] for e in res["measured"]["runs"] if e["run"] == RUN] == [FAIL], "the run must show the fail"
    assert res["outcome"] == INC and res["verdict"] == "inconclusive", res["outcome"]
    assert any("configurationIdentity" in m for m in res["missing"])
    assert any(n.startswith(f"observed {FAIL}") and RUN in n for n in res["notes"]), res["notes"]


def test_a_fail_whose_only_failing_run_has_a_partial_record_gives_inconclusive(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(**{RUN: dict(warn_at_needed=None)}))
    (root / "reproduction_044.json").write_text(json.dumps(DESK))
    _session_del(f"score_runs.{RUN}.runIdentity")(root)
    doc = edc.run(root, None)
    assert [r for r, rec in doc["evidenceRecords"].items() if rec["outcome"] != er.COMPLETE] == [RUN]
    res = doc["cases"]["VC-DRIVING-042"]
    assert res["outcome"] == INC, res["outcome"]
    assert any(n.startswith(f"observed {FAIL}") for n in res["notes"]), res["notes"]


def test_a_fail_stands_when_one_run_that_shows_it_has_a_complete_record(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs(**{RUN: dict(warn_at_needed=None),
                                                                   "012_20_r2": dict(warn_at_needed=None)}))
    (root / "reproduction_044.json").write_text(json.dumps(DESK))
    _session_del(f"score_runs.{RUN}.runIdentity")(root)
    doc = edc.run(root, None)
    assert doc["evidenceRecords"][RUN]["outcome"] == INC
    assert doc["evidenceRecords"]["012_20_r2"]["outcome"] == er.COMPLETE
    res = doc["cases"]["VC-DRIVING-042"]
    assert res["outcome"] == FAIL and res["verdict"] == "fail"
    assert not any(n.startswith("observed ") for n in res["notes"]), res["notes"]


def test_a_fail_of_the_desk_reproduction_stands_on_partial_run_records(tmp_path):
    # the desk reproduction of 044 is no run: a partial run record does not touch its fail
    root = session(tmp_path)
    _session_del("configuration_identity")(root)
    (root / "reproduction_044.json").write_text(json.dumps(dict(DESK, valuesMatch=False)))
    doc = edc.run(root, None)
    assert doc["cases"]["VC-DRIVING-044"]["outcome"] == FAIL


def test_the_campaign_passes_with_complete_records(tmp_path):
    root = session(tmp_path)
    (root / "reproduction_044.json").write_text(json.dumps(DESK))
    doc = edc.run(root, None)
    assert all(r["outcome"] == er.COMPLETE for r in doc["evidenceRecords"].values())
    assert {res["outcome"] for res in doc["cases"].values()} == {"passBoundedVerification"}
    rec = doc["evidenceRecords"][RUN]["attributes"]
    assert rec["criteriaRecordIdentity"] == doc["criteriaRecordIdentity"]
    assert rec["evaluatorRevision"] == doc["evaluatorRevision"]
    # the run's own outcomes, not only the fixed text of what the record does not prove (which names 036 too)
    assert "VC-DRIVING-036 passBoundedVerification" in rec["claimBoundary"]
    assert "VC-DRIVING-038 stop clause" not in rec["claimBoundary"]
    assert "VC-DRIVING-038 stop clause passBoundedVerification" in doc["evidenceRecords"]["stop"]["attributes"][
        "claimBoundary"]


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


def _strip_last_real(p):
    lines = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    ticks = [x for x in lines if x.get("event") == "tick"]
    ticks[-1].pop("t_real_ns")
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def test_wall_clock_span_empty_when_only_the_last_tick_has_no_real_time(tmp_path):
    root = session(tmp_path)
    _run_file("world_{run}/simulator/world.jsonl", _strip_last_real)(root)
    rec = records(root)[RUN]
    assert rec["emptyAttributes"] == ["wallClockSpan"], rec["missing"]


def test_the_claim_boundary_follows_the_repository_wording():
    """The claim boundary goes into the model verbatim (the 10b text generator copies recorded values), so it is
    written as the model is: American spelling, and the regulation named as the framing names it."""
    assert "behaviour" not in er.NOT_PROVED
    assert "behavior outside the settings" in er.NOT_PROVED
    assert "UN R152" not in er.NOT_PROVED.replace("UNECE R152", "")
    assert "approval under UNECE R152" in er.NOT_PROVED


# ------------------------------------------------------------------ R4: each run's own platform, GPU and delay first
# Closure review of 44a4be29..86cadee0, R4: session/evidence_fields.py makes a session-level value absent when any
# started run lacks its line (_agree). The model's record is per run (:150-153), so a run's record reads the run's own
# score_runs.<run>.score_platform and .score_gpu first and the session's value only as the fallback. The session-level
# fields below are the producer's own (evidence_fields.session_fields), with S1's evidence_config.json model_delay
# and guest_images.txt lines (20261121T014447Z).
MODEL_DELAY = {"text": "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 "
                       "ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4",
               "host_gpu": "NVIDIA L4",
               "source": "textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence"
                         ".sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence)"}
GUEST_IMAGES = (
    "GUEST_IMAGE sdv_core serial=0.0.0.0:6521 product=sdv_core_cf build_id=CP2A.260605.016 "
    "fingerprint=google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys vbmeta_digest=df609afc\n"
    "GUEST_IMAGE ivi serial=0.0.0.0:6522 product=sdv_ivi_cf build_id=CP2A.260605.016 "
    "fingerprint=google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys vbmeta_digest=d668fcbb\n")
PLATFORM = {"lifecycle_version": "score_lifecycle@0.10.0", "communication_version": "score_communication@0.6.0",
            "someip_gateway_commit": "d9eac670b7534352749da3d30f52aebf5129f168", "facts": "/opt/da-b2/bundle/facts"}
LACKING = "013_30_r2"
PER_RUN = ["visualizationRecorderDelay", "scoreLifecycleVersion", "scoreCommunicationVersion",
           "scoreSOMEIPGatewayCommit", "executionEnvironmentIdentity"]


def _evidence_fields():
    import importlib.util
    path = HERE.parents[1] / "session" / "evidence_fields.py"
    spec = importlib.util.spec_from_file_location("evidence_fields_of_the_session", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _producer_session(tmp_path, gpu_of=None):
    root = session(tmp_path)
    (root / "evidence_config.json").write_text(json.dumps({
        "configuration_identity": "DRIVING-CONFIG-002", "configuration_receipt_sha256": "0c0ffee0" * 8,
        "configuration_receipt": {}, "model_delay": MODEL_DELAY}))
    (root / "guest_images.txt").write_text(GUEST_IMAGES)
    d = json.loads((root / "session.json").read_text())
    for k in syn.SESSION_PROPOSALS:
        d.pop(k, None)
    for run, e in d["score_runs"].items():
        e["staged"] = {"source.mode": "score"}
        if run != LACKING:    # the start's one-line JSON, as score_runs.tsv carries it
            gpu = (gpu_of or {}).get(run, "NVIDIA L4")
            e["score_platform"] = json.dumps(PLATFORM)
            e["score_gpu"] = json.dumps({"gpus": [{"name": gpu, "driver_version": "580.178.04"}],
                                         "query": "nvidia-smi --query-gpu=name,driver_version --format=csv,noheader"})
    d.update(_evidence_fields().session_fields(str(root), d["score_runs"], "s1", True))
    (root / "session.json").write_text(json.dumps(d))
    return root, d


def test_each_run_reads_its_own_platform_gpu_and_delay_when_one_start_lacks_its_lines(tmp_path):
    root, d = _producer_session(tmp_path)
    # the producer's session-level values are absent: one started run printed no SCORE_PLATFORM or SCORE_GPU line
    assert "absent" in d["score_platform"]["lifecycle_version"], d["score_platform"]
    assert "absent" in d["execution_environment"]["score_gpu"] and "absent" in d["visualization_recorder_delay"]
    recs = records(root)
    for rid, rec in recs.items():
        if rid == LACKING:
            continue
        assert rec["outcome"] == er.COMPLETE, (rid, rec["missing"])
        a = rec["attributes"]
        assert a["scoreLifecycleVersion"] == "score_lifecycle@0.10.0"
        assert a["scoreCommunicationVersion"] == "score_communication@0.6.0"
        assert a["scoreSOMEIPGatewayCommit"] == "d9eac670b7534352749da3d30f52aebf5129f168"
        assert "with NVIDIA L4, driver 580.178.04;" in a["executionEnvironmentIdentity"], a
        assert a["visualizationRecorderDelay"] == f"{MODEL_DELAY['text']} ({MODEL_DELAY['source']})"
    assert recs[LACKING]["emptyAttributes"] == PER_RUN, recs[LACKING]["missing"]


def test_a_run_on_another_gpu_does_not_take_the_models_delay(tmp_path):
    root, _ = _producer_session(tmp_path, gpu_of={RUN: "NVIDIA T4"})
    rec = records(root)[RUN]
    assert rec["emptyAttributes"] == ["visualizationRecorderDelay"], rec["missing"]
    assert any("NVIDIA T4" in m and "states the delay it measures" in m for m in rec["missing"]), rec["missing"]
    assert "with NVIDIA T4, driver 580.178.04;" in rec["attributes"]["executionEnvironmentIdentity"]
