"""B6: the campaign rule, the criteria record and evaluatorRevision; the CLI over a synthetic session."""

import hashlib
import json
import re
import shutil
import subprocess
import sys

import cases_da
import evaluate_da_campaign as edc
import make_da_synthetic_run as syn
from case_evaluators_testkit import HERE, MODEL, REPO

NR = MODEL / "driver_assistance_needs_requirements.sysml"
VE = MODEL / "driver_assistance_verification_evidence.sysml"
VCS = ("VC-DRIVING-036", "VC-DRIVING-037", "VC-DRIVING-038", "VC-DRIVING-040", "VC-DRIVING-041", "VC-DRIVING-042",
       "VC-DRIVING-043", "VC-DRIVING-044")


def test_the_six_outcome_literals_and_their_verdicts():
    # driver_assistance_verification_evidence.sysml:156-161 and :164-172
    text = VE.read_text()
    block = text[text.index("enum def AssistanceEvidenceOutcome"):text.index("calc def MapAssistanceEvidence")]
    literals = re.findall(r"^\s+(\w+);", block, re.M)
    assert tuple(literals) == cases_da.OUTCOMES
    assert {o: cases_da.verdict(o) for o in cases_da.OUTCOMES} == {
        "passBoundedVerification": "pass", "passBoundedValidation": "pass", "failObservedBehavior": "fail",
        "inconclusiveMissingEvidence": "inconclusive", "blockedTargetRuntime": "inconclusive",
        "errorEvidence": "error"}


def test_campaign_rule_order():
    P, F, I, B, E = (cases_da.PASS, cases_da.FAIL, cases_da.INCONCLUSIVE, cases_da.BLOCKED, cases_da.ERROR)
    assert cases_da.combine([P, P], []) == P
    assert cases_da.combine([P, P], ["setting x: 1 run of 2"]) == I
    assert cases_da.combine([P, I], []) == I
    assert cases_da.combine([P, B, I], []) == B
    assert cases_da.combine([E, B, I], ["m"]) == E
    assert cases_da.combine([F, E, B, I], ["m"]) == F
    assert cases_da.combine([], []) == I            # nothing judged is never pass


def _model_success_criteria():
    lines = NR.read_text().splitlines()
    out, req = {}, None
    for n, line in enumerate(lines, 1):
        m = re.search(r"requirement <'(REQ-DRIVING-0\d\d)'>", line)
        if m:
            req = m.group(1)
        m = re.search(r'attribute :>> successCriteria = "(.*)";', line)
        if m and req:
            out[req] = (n, m.group(1))
    return out


def test_criteria_record_quotes_the_model_and_the_evaluators_thresholds():
    rec = json.loads(edc.CRITERIA_FILE.read_text())
    model = _model_success_criteria()
    assert rec["schema"] == "de4sdv.driving.da-criteria-record.v1"
    assert sorted(rec["cases"]) == sorted(VCS)
    for vc, c in rec["cases"].items():
        req, clause = cases_da.REQUIREMENT[vc]
        line, text = model[req]
        assert c["requirement"] == req
        assert c["successClause"] == clause and clause.endswith(f":{line}")
        assert c["successCriteria"] == text
        assert c["thresholds"] == json.loads(json.dumps(cases_da.THRESHOLDS[vc]))


def test_criteria_record_is_the_one_build_criteria_record_writes():
    # the readings too, not only the thresholds: regenerate with --write-criteria after a change of either
    assert json.loads(edc.CRITERIA_FILE.read_text()) == json.loads(json.dumps(edc.build_criteria_record(REPO)))


def test_criteria_record_identity_is_the_sha256_of_its_bytes():
    want = "sha256:" + hashlib.sha256(edc.CRITERIA_FILE.read_bytes()).hexdigest()
    assert edc.criteria_record_identity() == want


def test_evaluator_revision_from_git_blobs(tmp_path):
    rev, blobs = edc.evaluator_revision()
    # rule 30: the blobs of the folder's own .py and .json files
    assert rev.startswith("blobs:") and set(blobs) == set(edc.EVALUATOR_FILES)
    assert {"cases_da.py", "terms.py", "runio_da.py", "evaluate_da_campaign.py",
            "da_criteria_record.json"} <= set(blobs)
    assert set(blobs) == {p.name for p in HERE.parent.iterdir() if p.suffix in (".py", ".json")}
    git = shutil.which("git")
    if git:
        for name, blob in blobs.items():
            got = subprocess.run([git, "hash-object", str(HERE.parent / name)], capture_output=True, text=True,
                                 check=True).stdout.strip()
            assert blob == got, name
    # one changed byte in one evaluator file changes the revision
    copy = tmp_path / "ce"
    copy.mkdir()
    for name in edc.EVALUATOR_FILES:
        shutil.copy(HERE.parent / name, copy / name)
    assert edc.evaluator_revision(copy)[0] == rev
    (copy / "terms.py").write_text((copy / "terms.py").read_text() + "\n")
    assert edc.evaluator_revision(copy)[0] != rev


def test_cli_writes_every_case_with_the_criteria_and_the_revision(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    (root / "reproduction_044.json").write_text(json.dumps(
        {"engineer": "second engineer", "valuesMatch": True, "recordSha256": ["5ff680b0" * 8]}))
    out = tmp_path / "verdicts.json"
    p = subprocess.run([sys.executable, "-B", str(HERE.parent / "evaluate_da_campaign.py"), "--session", str(root),
                        "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    doc = json.loads(out.read_text())
    assert doc["criteriaRecordIdentity"] == edc.criteria_record_identity()
    assert doc["evaluatorRevision"] == edc.evaluator_revision()[0]
    assert sorted(doc["cases"]) == sorted(VCS)
    for vc, res in doc["cases"].items():
        assert res["outcome"] == "passBoundedVerification", (vc, res["missing"])
        assert res["criteriaRecordIdentity"] == doc["criteriaRecordIdentity"]
        assert res["evaluatorRevision"] == doc["evaluatorRevision"]
    assert len(doc["runs"]) == 15 and doc["runs"][-1]["kind"] == "stop"
    assert [r["repetition"] for r in doc["runs"][:2]] == [1, 2]
    assert "VC-DRIVING-036 passBoundedVerification" in p.stdout


def test_036_037_name_the_deceleration_calibration(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    cal = root / "sim" / "x" / "out" / "calibrate" / "calib_decel" / "simulator"
    cal.mkdir(parents=True)
    (cal / "calibration_decel.json").write_text(json.dumps({"summary": {"allFollowWithinProposal": False,
                                                                        "worstRatio": 0.4}}))
    doc = edc.run(root, None)
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
        assert doc["cases"][vc]["measured"]["calibrationDecel"]["worstRatio"] == 0.4
        # the condition itself, not only a note that names the assumption (the gains note names it too)
        assert any(n.startswith("conditional on ASM-DRIVING-005") for n in doc["cases"][vc]["notes"])
    assert "calibrationDecel" not in doc["cases"]["VC-DRIVING-042"]["measured"]


def test_cli_without_desk_record_leaves_044_inconclusive(tmp_path):
    root = syn.write_session(tmp_path / "session", syn.s1_specs())
    doc = edc.run(root, None)
    assert doc["cases"]["VC-DRIVING-044"]["outcome"] == "inconclusiveMissingEvidence"


def _calib(root, worst, follow):
    cal = root / "sim" / "x" / "out" / "calibrate" / "calib_decel" / "simulator"
    cal.mkdir(parents=True)
    (cal / "calibration_decel.json").write_text(json.dumps({"summary": {"allFollowWithinProposal": follow,
                                                                        "worstRatio": worst}}))


def _condition_notes(doc, vc):
    return [n for n in doc["cases"][vc]["notes"] if n.startswith("conditional on ASM-DRIVING-005")]


def test_036_037_condition_note_carries_the_calibration_and_the_gains_on_pass_and_on_fail(tmp_path):
    # While ASM-DRIVING-005 is unproven, a verdict of 036/037 is conditional on it
    # (driver_assistance_verification_evidence.sysml:916-917): the note states the condition with the session's
    # calib-decel summary and the Ackermann gains, whatever the outcome.
    passing = syn.write_session(tmp_path / "pass", syn.s1_specs())
    (passing / "reproduction_044.json").write_text(json.dumps(
        {"engineer": "second engineer", "valuesMatch": True, "recordSha256": ["5ff680b0" * 8]}))
    _calib(passing, 0.4038, False)
    failing = syn.write_session(tmp_path / "fail", syn.s1_specs(**{"012_20_r1": dict(warn_at_needed=None,
                                                                                    eb_at_needed=None)}),
                                session_extra={"ackermann_gains": "v1"})
    # complete records: a fail on partial records gives inconclusive (the lead's reading of 2026-11-21)
    (failing / "reproduction_044.json").write_text((passing / "reproduction_044.json").read_text())
    _calib(failing, 0.99, True)
    for root, outcome, worst, follow, requested in (
            (passing, "passBoundedVerification", "0.4038", "false", "unrecorded"),
            (failing, "failObservedBehavior", "0.99", "true", "session.json ackermann_gains = \"v1\"")):
        doc = edc.run(root, None)
        for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
            assert doc["cases"][vc]["outcome"] == outcome, (vc, doc["cases"][vc]["missing"])
            notes = _condition_notes(doc, vc)
            assert len(notes) == 1, (vc, doc["cases"][vc]["notes"])
            note = notes[0]
            assert f"worstRatio {worst}" in note and f"allFollowWithinProposal {follow}" in note, note
            assert f"Ackermann gains: requested {requested}, read back unrecorded" in note, note
        assert _condition_notes(doc, "VC-DRIVING-042") == []


def test_036_037_condition_note_without_a_calibration_record(tmp_path):
    doc = edc.run(syn.write_session(tmp_path / "session", syn.s1_specs()), None)
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
        note = _condition_notes(doc, vc)[0]
        assert "calib-decel summary unrecorded" in note, note
        assert "Ackermann gains: requested unrecorded, read back unrecorded" in note, note
