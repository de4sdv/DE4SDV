"""Synthetic record fixtures; no real engineering pass/acceptance is asserted."""
import copy
import json
import subprocess
import sys

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return {
        "schema": "de4sdv.scoped-assurance-records/v1",
        "evidence": [{"case_identity": "synthetic-case", "artifact_identity": "synthetic://report",
                      "artifact_revision": "r1", "digest": "a" * 64, "run": "synthetic-run",
                      "tested_scope": ["synthetic-subject", "synthetic-config", "synthetic-condition"]}],
        "supports": [{"id": "support-1", "claim": "synthetic-claim", "subject": "synthetic-subject",
                      "configuration": "synthetic-config", "conditions": ["synthetic-condition"],
                      "evidence_ref": "synthetic://report@r1", "rationale": "Synthetic scoped relevance",
                      "limitations": ["Synthetic evidence only"]}],
    }


def activity_fixture(status="CompletedPassed", kind="verification", verdict="pass", completed=True):
    data = fixture()
    scope = {"subject": "synthetic-subject", "configuration": "synthetic-config",
             "conditions": ["synthetic-condition"], "kind": kind,
             "comparison_basis": "synthetic-baseline", "criteria": ["synthetic-criterion"]}
    data["activities"] = [{"id": "activity-1", **scope, "lifecycle_context": "synthetic-design-review",
                           "status": status, "case_identity": "synthetic-case",
                           "responsible_actor": "synthetic-reviewer", "result_refs": ["result-1"],
                           "evidence_refs": ["synthetic://report@r1"],
                           "result_approval": {"required": False, "reference": None}}]
    data["results"] = [{"id": "result-1", **scope, "activity_id": "activity-1",
                        "execution_ref": "synthetic://report@r1", "completed": completed,
                        "verdict": verdict, "reasoning": "Synthetic result"}]
    return data


@pytest.mark.parametrize("kind", ["verification", "validation"])
@pytest.mark.parametrize("subject", ["need", "requirement", "design", "production-output",
                                    "system-element", "integrated-system", "artifact"])
def test_reusable_activity_for_both_kinds_and_lifecycle_subjects(kind, subject):
    from de4sdv.semantic.scoped_assurance import validate_records
    data = activity_fixture(kind=kind)
    for rec in [data["activities"][0], data["results"][0], data["supports"][0]]:
        rec["subject"] = subject
    data["evidence"][0]["tested_scope"][0] = subject
    report = validate_records(data)
    assert report["activity_count"] == 1
    assert report["activities"][0]["reported_status"] == "CompletedPassed"
    assert report["activities"][0]["kind"] == kind
    assert report["implies_pass"] is False


@pytest.mark.parametrize("status,verdict,completed", [
    ("Completed", "fail", True), ("CompletedFailed", "fail", True),
    ("CompletedUnsuccessful", None, False), ("InProgress", None, False)])
def test_status_retains_distinct_upstream_meanings(status, verdict, completed):
    from de4sdv.semantic.scoped_assurance import validate_records
    report = validate_records(activity_fixture(status=status, verdict=verdict, completed=completed))
    assert report["activities"][0]["reported_status"] == status
    assert report["claims_established"] is False


@pytest.mark.parametrize("mutation", [
    lambda d: d["activities"][0].update(status="accepted"),
    lambda d: d["activities"][0].update(status="CompletedFailed"),
    lambda d: d["activities"][0].update(status="CompletedUnsuccessful"),
    lambda d: d["activities"][0].update(result_refs=[]),
    lambda d: d["activities"][0].update(result_approval={"required": True, "reference": None}),
    lambda d: d["results"][0].update(kind="validation"),
    lambda d: d["results"][0].update(configuration="other-config"),
    lambda d: d["results"][0].update(comparison_basis="other-baseline"),
    lambda d: d["results"][0].update(verdict="fail"),
    lambda d: d["results"][0].update(completed=False),
    lambda d: d["results"][0].update(verdict="accepted"),
    lambda d: d["evidence"][0].update(case_identity="other-case"),
])
def test_activity_result_mismatch_fails_closed(mutation):
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = activity_fixture()
    mutation(data)
    with pytest.raises(ScopedAssuranceError):
        validate_records(data)



def assessment_fixture(*, adequate=True, supports_claim=True, unqualified=False):
    data = activity_fixture()
    scope = {k: data["supports"][0][k] for k in ("claim", "subject", "configuration", "conditions")}
    data["assessments"] = [{"id": "assessment-1", **scope, "comparison_basis": "synthetic-baseline",
        "criteria": ["synthetic-criterion"], "agreement_ref": "synthetic://criteria-agreement/r1",
        "coverage_basis": "Synthetic complete criterion coverage", "confidence_basis": "Synthetic confidence justification",
        "rigor_basis": "Synthetic risk-proportionate review", "evidence_refs": ["synthetic://report@r1"],
        "result_refs": ["result-1"], "activity_refs": ["activity-1"], "case_refs": ["synthetic-case"],
        "limitations": ["Synthetic evidence only"], "contrary_result_refs": [], "discrepancy_refs": [],
        "gap_refs": [], "assessor": "synthetic-assessor", "adequate_for_scope": adequate,
        "supports_claim": supports_claim, "conclusion": "Synthetic scoped conclusion", "reasoning": "Synthetic assessor reasoning"}]
    data["requests"] = [{"id": "request-1", **scope, "purpose": "establish-claim", "assessment_ref": "assessment-1",
                         "unqualified": unqualified, "acceptance_reference": None}]
    return data


def test_adequacy_assesses_evidence_set_not_individual_artifact_sufficiency():
    from de4sdv.semantic.scoped_assurance import validate_records
    report = validate_records(assessment_fixture())
    assert report["assessment_count"] == 1
    assert report["requests"][0]["structural_presentation_eligible"] is True
    assert report["requests"][0]["qualification_required"] is True
    assert report["claims_established"] is False
    assert report["implies_acceptance"] is False


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(assessments=[]),
    lambda d: d["assessments"][0].update(configuration="other-config"),
    lambda d: d["assessments"][0].update(agreement_ref=""),
    lambda d: d["assessments"][0].update(coverage_basis=""),
    lambda d: d["assessments"][0].update(confidence_basis=""),
    lambda d: d["assessments"][0].update(rigor_basis=""),
    lambda d: d["assessments"][0].update(assessor=""),
    lambda d: d["assessments"][0].update(reasoning=""),
    lambda d: d["assessments"][0].update(authority="synthetic-assessor"),
    lambda d: d["assessments"][0].update(adequate_for_scope=False),
    lambda d: d["assessments"][0].update(result_refs=[]),
    lambda d: d["assessments"][0].update(case_refs=["wrong-case"]),
    lambda d: d["assessments"][0].update(criteria=["uncovered-criterion"]),
    lambda d: d["requests"][0].update(claim="other-claim"),
    lambda d: d["requests"][0].update(unqualified=True),
    lambda d: d["requests"][0].update(assessment_ref=None),
])
def test_positive_claim_requires_complete_exact_scoped_adequacy(mutation):
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = assessment_fixture()
    mutation(data)
    with pytest.raises(ScopedAssuranceError):
        validate_records(data)


def test_contrary_results_and_gaps_remain_visible_before_seeking_acceptance():
    from de4sdv.semantic.scoped_assurance import validate_records
    data = assessment_fixture(supports_claim=False)
    data["requests"][0]["purpose"] = "seek-acceptance"
    data["activities"][0]["status"] = "CompletedFailed"
    data["results"][0]["verdict"] = "fail"
    data["assessments"][0].update(contrary_result_refs=["result-1"], gap_refs=["synthetic-gap"])
    report = validate_records(data)
    assert report["requests"][0]["exceptions"]["contrary_result_refs"] == ["result-1"]
    assert report["requests"][0]["exceptions"]["gap_refs"] == ["synthetic-gap"]
    assert report["requests"][0]["technical_satisfaction"] is False


def test_designated_authority_reference_is_separate_from_assessor_and_never_acceptance():
    from de4sdv.semantic.scoped_assurance import validate_records
    data = assessment_fixture()
    data["requests"][0]["purpose"] = "seek-acceptance"
    data["evidence"].append({**data["evidence"][0], "artifact_identity": "synthetic://attestation"})
    data["requests"][0]["acceptance_reference"] = {
        **{k: data["requests"][0][k] for k in ("claim", "subject", "configuration", "conditions")},
        "policy_ref": "synthetic-policy", "decision_registry_path": "synthetic://registry",
        "attestation_ref": "synthetic://attestation@r1", "designated_authority": "synthetic-authority",
        "exceptions": ["Synthetic evidence only"]}
    report = validate_records(data)
    assert report["requests"][0]["acceptance_reference"]["designated_authority"] == "synthetic-authority"
    assert report["implies_acceptance"] is False


def test_generic_completed_cannot_establish_unqualified_technical_satisfaction():
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = assessment_fixture(unqualified=True)
    data["supports"][0]["limitations"] = []
    data["assessments"][0]["limitations"] = []
    data["activities"][0]["status"] = "Completed"
    data["results"][0]["verdict"] = "fail"
    with pytest.raises(ScopedAssuranceError):
        validate_records(data)



@pytest.mark.parametrize("mutation", [
    lambda d: d["supports"][0].update(id="activity-1"),
    lambda d: d["evidence"][0].update(digest={"algorithm": "sha256", "value": "a" * 64, "ignored": True}),
])
def test_ambiguous_ids_and_overloaded_digests_fail_closed(mutation):
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = activity_fixture()
    mutation(data)
    with pytest.raises(ScopedAssuranceError):
        validate_records(data)


def test_supplied_known_contrary_activity_cannot_be_omitted_from_adequacy():
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = assessment_fixture()
    activity = copy.deepcopy(data["activities"][0])
    activity.update(id="other-activity", status="CompletedFailed", result_refs=["other-result"])
    result = copy.deepcopy(data["results"][0])
    result.update(id="other-result", activity_id="other-activity", verdict="fail")
    data["activities"].append(activity)
    data["results"].append(result)
    with pytest.raises(ScopedAssuranceError):
        validate_records(data)


def test_cli_duplicate_json_keys_fail_closed(tmp_path):
    path = tmp_path / "synthetic-duplicate.json"
    path.write_text(json.dumps(fixture()).replace('"supports":', '"supports": [], "supports":'))
    run = subprocess.run([sys.executable, "-m", "de4sdv.semantic.scoped_assurance", str(path)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 2
    assert "duplicate JSON key" in json.loads(run.stdout)["error"]
    assert "Traceback" not in run.stderr


def test_native_source_check_binds_enum_declaration_to_pinned_archive(tmp_path):
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, verify_native_sources
    # Deliberately synthetic source: must not pass as adopted upstream authority.
    path = tmp_path / "synthetic-library.kpar"
    path.write_text("synthetic-not-the-pinned-library")
    with pytest.raises(ScopedAssuranceError, match="digest"):
        verify_native_sources(path)


def test_model_and_validator_keep_record_fields_synchronized():
    from de4sdv.semantic.scoped_assurance import verify_native_sources
    report = verify_native_sources()
    assert report["model_declarations"] == ["EvidenceSupportCitation", "ScopedVVActivityRecord", "ScopedEvidenceAdequacyAssessment"]
    assert report["adopted_statuses"] == ["Completed", "CompletedFailed", "CompletedPassed", "CompletedUnsuccessful", "InProgress", "NotStarted"]
    assert report["upstream_archive_verified"] is False


def test_citation_cli_checks_supplied_records_without_elevating_claim(tmp_path):
    path = tmp_path / "synthetic-records.json"
    path.write_text(json.dumps(fixture()))
    run = subprocess.run([sys.executable, "-m", "de4sdv.semantic.scoped_assurance", str(path)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["structurally_valid"] is True
    assert report["support_count"] == 1
    assert report["implies_pass"] is False
    assert report["implies_acceptance"] is False
    assert report["claims_established"] is False


def test_native_source_cli_reports_unverified_archive_without_claiming_semantics():
    run = subprocess.run([sys.executable, "-m", "de4sdv.semantic.scoped_assurance",
                          "--check-native-sources"],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report["upstream_archive_verified"] is False
    assert report["native_semantic_validation"] is False
    assert report["implies_acceptance"] is False


def test_native_source_cli_refuses_mixed_record_validation_mode(tmp_path):
    path = tmp_path / "synthetic-records.json"
    path.write_text(json.dumps(fixture()))
    run = subprocess.run([sys.executable, "-m", "de4sdv.semantic.scoped_assurance",
                          str(path), "--check-native-sources"],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 2
    assert "exactly one" in run.stderr


@pytest.mark.parametrize("family", ["requests", "activities", "results", "acceptance"])
def test_scope_identity_roles_cannot_be_swapped(family):
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = assessment_fixture()
    if family == "acceptance":
        request = data["requests"][0]
        data["evidence"].append({**data["evidence"][0], "artifact_identity": "synthetic://attestation"})
        request["acceptance_reference"] = {
            **{k: request[k] for k in ("claim", "subject", "configuration", "conditions")},
            "policy_ref": "synthetic-policy", "decision_registry_path": "synthetic://registry",
            "attestation_ref": "synthetic://attestation@r1", "designated_authority": "synthetic-authority",
            "exceptions": ["Synthetic evidence only"]}
        target = request["acceptance_reference"]
    else:
        target = data[family][0]
    if family == "results":
        target["subject"], target["conditions"] = target["conditions"][0], [target["subject"]]
    else:
        target["subject"], target["configuration"] = target["configuration"], target["subject"]
    with pytest.raises(ScopedAssuranceError):
        validate_records(data)


def test_condition_order_does_not_change_role_aware_scope():
    from de4sdv.semantic.scoped_assurance import validate_records
    data = assessment_fixture()
    for family in ("supports", "activities", "results", "assessments", "requests"):
        data[family][0]["conditions"] = ["synthetic-condition", "synthetic-second-condition"]
    data["requests"][0]["conditions"].reverse()
    data["evidence"][0]["tested_scope"].append("synthetic-second-condition")
    assert validate_records(data)["structurally_valid"] is True


def limited_input_fixture():
    data = assessment_fixture()
    data["supports"][0]["limitations"] = []
    data["assessments"][0]["limitations"] = []
    data["evidence"].append({**data["evidence"][0], "artifact_identity": "synthetic://limited-input"})
    support = copy.deepcopy(data["supports"][0])
    support.update(id="limited-support", evidence_ref="synthetic://limited-input@r1",
                   limitations=["Known unresolved boundary-condition gap"])
    data["supports"].append(support)
    data["activities"][0]["evidence_refs"].append("synthetic://limited-input@r1")
    return data


@pytest.mark.parametrize("adequate", [True, False])
def test_assessment_cannot_omit_activity_input_and_its_known_limit(adequate):
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = limited_input_fixture()
    data["assessments"][0]["adequate_for_scope"] = adequate
    if not adequate:
        data["assessments"][0]["gap_refs"] = ["synthetic-gap"]
        data["requests"] = []
    with pytest.raises(ScopedAssuranceError, match="activity evidence omitted"):
        validate_records(data)


def test_retained_activity_input_limit_requires_visible_qualification():
    from de4sdv.semantic.scoped_assurance import ScopedAssuranceError, validate_records
    data = limited_input_fixture()
    data["assessments"][0]["evidence_refs"].append("synthetic://limited-input@r1")
    with pytest.raises(ScopedAssuranceError, match="limitations omitted"):
        validate_records(data)
    data["assessments"][0]["limitations"] = ["Known unresolved boundary-condition gap"]
    report = validate_records(data)
    assert report["requests"][0]["qualification_required"] is True
    assert report["requests"][0]["exceptions"]["limitations"] == ["Known unresolved boundary-condition gap"]
    data["requests"][0]["unqualified"] = True
    with pytest.raises(ScopedAssuranceError, match="unqualified"):
        validate_records(data)


@pytest.mark.parametrize("mode", ["record", "malformed", "rejected", "native", "bad-archive"])
def test_every_json_cli_report_has_all_no_claim_flags(tmp_path, mode):
    path = tmp_path / "synthetic-records.json"
    data = fixture()
    if mode == "rejected":
        data["supports"][0]["evidence_ref"] = "synthetic://missing@r1"
    path.write_text("{" if mode == "malformed" else json.dumps(data))
    args = [str(path)]
    expected = 2 if mode in ("malformed", "rejected", "bad-archive") else 0
    if mode in ("native", "bad-archive"):
        args = ["--check-native-sources"]
        if mode == "bad-archive":
            args += ["--upstream-archive", str(path)]
    run = subprocess.run([sys.executable, "-m", "de4sdv.semantic.scoped_assurance", *args],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == expected, run.stderr
    report = json.loads(run.stdout)
    for flag in ("implies_pass", "claims_established", "implies_acceptance", "production_activation"):
        assert report.get(flag) is False, (mode, flag, report)
