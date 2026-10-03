"""Offline supplied-record checks, never truth, technical pass or acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
import zipfile
from pathlib import Path
from typing import Any

from .external_reference_contract import EvidenceReferenceError, validate_typed_reference

SCHEMA = "de4sdv.scoped-assurance-records/v1"
MODEL_PATH = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_scoped_assurance.sysml"
_NO_CLAIMS = {
    "implies_pass": False, "claims_established": False,
    "implies_acceptance": False, "production_activation": False,
}
_MODEL_ATTRIBUTES = {
    "EvidenceSupportCitation": {
        "id", "claim", "subjectIdentity", "configuration", "conditions",
        "evidenceRef", "rationale", "limitations",
    },
    "ScopedVVActivityRecord": {
        "id", "subjectIdentity", "configuration", "conditions", "activityKind",
        "lifecycleContext", "comparisonBasis", "criteria", "status", "caseIdentity",
        "resultRefs", "evidenceRefs", "responsibleActor", "resultApprovalRequired",
        "resultApprovalRef",
    },
    "ScopedEvidenceAdequacyAssessment": {
        "id", "claim", "subjectIdentity", "configuration", "conditions", "comparisonBasis",
        "criteria", "agreementRef", "coverageBasis", "confidenceBasis", "rigorBasis",
        "evidenceRefs", "resultRefs", "activityRefs", "caseRefs", "limitations",
        "contraryResultRefs", "discrepancyRefs", "gapRefs", "assessor", "adequateForScope",
        "supportsClaim", "conclusion", "reasoning",
    },
}


class ScopedAssuranceError(ValueError):
    """A supplied record does not meet the scoped structural contract."""


def _shape(record: Any, fields: set[str], context: str) -> dict:
    if not isinstance(record, dict) or set(record) != fields:
        raise ScopedAssuranceError(f"{context}: fields must be exactly {sorted(fields)}")
    return record


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ScopedAssuranceError(f"{context}: nonblank unpadded identity/text required")
    return value


def _texts(value: Any, context: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ScopedAssuranceError(f"{context}: explicit list required")
    values = [_text(v, context) for v in value]
    if len(set(values)) != len(values):
        raise ScopedAssuranceError(f"{context}: duplicate identities")
    return values


def _index(records: Any, context: str) -> dict[str, dict]:
    if not isinstance(records, list):
        raise ScopedAssuranceError(f"{context}: list required")
    result = {}
    for record in records:
        if not isinstance(record, dict):
            raise ScopedAssuranceError(f"{context}: mapping required")
        identity = _text(record.get("id"), f"{context}.id")
        if identity in result:
            raise ScopedAssuranceError(f"{context}: duplicate id {identity}")
        result[identity] = record
    return result


def _scope(record: dict) -> tuple[str, str, frozenset[str]]:
    subject = _text(record.get("subject"), "subject")
    configuration = _text(record.get("configuration"), "configuration")
    conditions = _texts(record.get("conditions"), "conditions", nonempty=True)
    scope = [subject, configuration, *conditions]
    if len(set(scope)) != len(scope):
        raise ScopedAssuranceError("scope: duplicate subject/configuration/condition identities")
    return subject, configuration, frozenset(conditions)


def _external_scope(record: dict) -> set[str]:
    # The existing external-reference contract has unlabelled tested_scope.
    # Flatten only at that seam, never when comparing role-labelled records.
    subject, configuration, conditions = _scope(record)
    return {subject, configuration, *conditions}


def _owned_native_block(owner: str, header: str) -> str:
    """One direct-owned body in the supported offline source-check subset."""
    from .relationship_successor_contract import _mask_strings, _owned_matches

    # Inventory the identity before admitting the supported header/body shape:
    # a bodiless or unsupported duplicate must not borrow a live sibling body.
    matches, code = _owned_matches(owner, header + r"[^;{}]*[;{]")
    if (len(matches) != 1 or not re.fullmatch(header + r"\s*\{",
            code[matches[0].start():matches[0].end()])):
        raise ScopedAssuranceError("native source missing or ambiguous owned declaration: " + header)
    start = matches[0].end() - 1
    structure = _mask_strings(code)
    depth = 0
    for index in range(start, len(structure)):
        depth += (structure[index] == "{") - (structure[index] == "}")
        if depth == 0:
            return code[start:index + 1]
    raise ScopedAssuranceError("native source unterminated owned declaration: " + header)


def _native_package(root: Path) -> str:
    text = (root / MODEL_PATH).read_text(encoding="utf-8")
    return _owned_native_block("{" + text + "}", r"\bpackage\s+DE4SDV_ScopedAssurance\b")


def _constraint_vocabulary(activity: str, name: str, comparison: str) -> set[str]:
    block = _owned_native_block(activity, r"\bassert\s+constraint\s+" + re.escape(name) + r"\b")
    expression = block[1:-1].strip()
    # Consume the entire disjunction: quoted decoys, extra expressions and
    # descendants cannot supply an executable vocabulary comparison.
    if not re.fullmatch(comparison + r"(?:\s+or\s+" + comparison + r")*", expression):
        raise ScopedAssuranceError("native unsupported vocabulary constraint: " + name)
    values = re.findall(comparison, expression)
    if len(values) != len(set(values)):
        raise ScopedAssuranceError("native duplicate vocabulary literal: " + name)
    return set(values)


# Bounded direct-owned same-identity inventory: a definition/alias header may
# carry one optional short-name token before the declared name. This is not a
# general SysML name resolver; it only refuses a direct same-name shadow of the
# adopted VVStatus identity before the supported import/header grammar applies.
# Whitespace, including newlines, may appear inside the short-name token.
_STATUS_SHADOW = r"\b(?:def|alias)\s+(?:<[^<>{};]*>\s+)?VVStatus\b"


def _status_shadows(owner: str) -> list:
    """Direct-owned VVStatus definition/alias headers, short-name form included."""
    from .relationship_successor_contract import _owned_matches

    return _owned_matches(owner, _STATUS_SHADOW)[0]


def _require_status_import(owner: str, path: str, visibility: str) -> None:
    from .relationship_successor_contract import _owned_matches

    # Inventory the direct-owned same identity before admitting the supported
    # import header: a short-name or otherwise unsupported shadow declaration
    # must refuse, not borrow the adopted identity.
    if _status_shadows(owner):
        raise ScopedAssuranceError("native direct-owned VVStatus declaration shadows adopted import: " + path)
    matches, code = _owned_matches(owner, r"\b(?:(?:public|private|protected)\s+)?import\s+[^;{}]*;")
    imports = [code[m.start():m.end()] for m in matches
               if re.search(r"\bVVStatus\s*;", code[m.start():m.end()])]
    expected = visibility + r"\s+import\s+" + re.escape(path) + r"\s*;"
    if len(imports) != 1 or not re.fullmatch(expected, imports[0]):
        raise ScopedAssuranceError("native activity must reuse exact adopted VVStatus import: " + path)


def _adopted_library_pin(root: Path) -> tuple[dict, dict]:
    lock = tomllib.loads((root / "sysand-lock.toml").read_text(encoding="utf-8"))
    projects = [p for p in lock.get("project", [])
                if "pkg:sysand/ode4hera/requirements-management" in p.get("identifiers", [])]
    if len(projects) != 1 or len(projects[0].get("sources", [])) != 1:
        raise ScopedAssuranceError("adopted status library requires one exact archive pin")
    return projects[0], projects[0]["sources"][0]


def _adopted_enum_population(upstream: str) -> set[str]:
    from .relationship_successor_contract import _owned_matches

    package = _owned_native_block("{" + upstream + "}", r"\b(?:library\s+)?package\s+RequirementsManagement\b")
    enum = _owned_native_block(package, r"\benum\s+def\s+VVStatus\b")
    matches, code = _owned_matches(enum, r"\b([A-Za-z]\w*)\b")
    literals = []
    for match in matches:
        name = match.group(1)
        if name == "doc":
            continue
        # Every direct code identifier must be a literal header, not a name
        # substring inside another declaration; compact duplicates also count.
        if not re.match(r"\s*[{;]", code[match.end():]):
            raise ScopedAssuranceError("unsupported adopted VVStatus enum member")
        literals.append(name)
    if not literals or len(literals) != len(set(literals)):
        raise ScopedAssuranceError("adopted VVStatus enum population missing or ambiguous")
    return set(literals)


def _installed_adopted_statuses(root: Path) -> set[str]:
    """Inspect already-synced adopted source; archive byte verification is separate."""
    project, pin = _adopted_library_pin(root)
    try:
        env = tomllib.loads((root / ".sysand/env.toml").read_text(encoding="utf-8"))
        installed = [p for p in env.get("project", [])
                     if "pkg:sysand/ode4hera/requirements-management" in p.get("identifiers", [])]
        if (len(installed) != 1 or installed[0].get("version") != project["version"]
                or installed[0].get("kpar_cksum") != pin["kpar_digest"]):
            raise ScopedAssuranceError("synced adopted status library does not match lock identity")
        path = installed[0].get("path")
        if not isinstance(path, str) or not path.strip():
            raise ScopedAssuranceError("synced adopted status library source path missing")
        source = root / ".sysand" / path / "RequirementsManagement.sysml"
        return _adopted_enum_population(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScopedAssuranceError("already-synced adopted VVStatus source required; no fetching") from exc


def _native_vocabulary() -> tuple[set[str], set[str]]:
    # Offline supplied-record admission, not production runtime semantic authority.
    root = Path(__file__).resolve().parents[2]
    from .relationship_successor_contract import _owned_matches

    package = _native_package(root)
    activity = _owned_native_block(package, r"\bitem\s+def\s+ScopedVVActivityRecord\b")
    _require_status_import(package, "DE4SDV_SYSMODAdapter::VVStatus", "private")
    adapter = (root / MODEL_PATH).with_name("de4sdv_sysmod_adapter.sysml").read_text(encoding="utf-8")
    seam = _owned_native_block("{" + adapter + "}", r"\bpackage\s+DE4SDV_SYSMODAdapter\b")
    _require_status_import(seam, "RequirementsManagement::VVStatus", "public")
    if _status_shadows(activity):
        raise ScopedAssuranceError("native direct-owned VVStatus declaration shadows adopted status type")
    declarations, code = _owned_matches(activity, r"\battribute\s+status\b[^;{}]*;")
    if (len(declarations) != 1 or not re.fullmatch(r"attribute\s+status\s*:\s*VVStatus\s*;",
            code[declarations[0].start():declarations[0].end()])):
        raise ScopedAssuranceError("native activity must reuse imported VVStatus")
    statuses = _constraint_vocabulary(activity, "adoptedStatusVocabulary",
                                      r"status\s*==\s*VVStatus::([A-Za-z]\w*)")
    kinds = _constraint_vocabulary(activity, "activityKindVocabulary",
                                   r'activityKind\s*==\s*"([a-z]+)"')
    if statuses != _installed_adopted_statuses(root):
        raise ScopedAssuranceError("native status references differ from adopted enum declaration")
    return statuses, kinds


def verify_native_sources(archive_path: Path | None = None) -> dict[str, Any]:
    """Offline lexical parity and optional archive pin check, not SysML validation.

    Reuse the repository's bounded lexical ownership scan, not a SysML validator.
    The mandatory guard checks directly owned constraints against already-synced
    adopted enum source. Only an explicit archive verifies upstream archive bytes;
    no library is fetched and no native semantic validation is claimed.
    """
    from .relationship_successor_contract import _owned_matches

    root = Path(__file__).resolve().parents[2]
    source = _native_package(root)
    # The admitted field-check subset is lexical; Syside owns full semantics.
    matches, _ = _owned_matches(source, r"\bitem\s+def\s+([A-Za-z]\w*)")
    declarations = [match.group(1) for match in matches]
    if declarations != list(_MODEL_ATTRIBUTES):
        raise ScopedAssuranceError("native model declaration population mismatch")
    for name, expected in _MODEL_ATTRIBUTES.items():
        block = _owned_native_block(source, r"\bitem\s+def\s+" + re.escape(name) + r"\b")
        matches, _ = _owned_matches(block, r"\battribute\s+([A-Za-z]\w*)\s*:")
        attributes = [match.group(1) for match in matches]
        if len(attributes) != len(set(attributes)) or set(attributes) != expected:
            raise ScopedAssuranceError(f"native {name}: adapter field parity mismatch")
    statuses, kinds = _native_vocabulary()
    _, pin = _adopted_library_pin(root)
    verified = False
    if archive_path is not None:
        archive_path = Path(archive_path)
        payload = archive_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != pin["kpar_digest"]:
            raise ScopedAssuranceError("upstream archive digest mismatch")
        if len(payload) != pin["kpar_size"]:
            raise ScopedAssuranceError("upstream archive size mismatch")
        with zipfile.ZipFile(archive_path) as archive:
            upstream = archive.read("RequirementsManagement.sysml").decode("utf-8")
        if _adopted_enum_population(upstream) != statuses:
            raise ScopedAssuranceError("native status references differ from pinned enum declaration")
        verified = True
    return {
        "model_declarations": declarations,
        "adopted_statuses": sorted(statuses), "activity_kinds": sorted(kinds),
        "upstream_archive_verified": verified,
        "upstream_archive_digest": pin["kpar_digest"],
        "validation_scope": "lexical adapter parity and optional pinned archive identity only",
        "native_semantic_validation": False, **_NO_CLAIMS,
    }


def _basis(record: dict) -> tuple:
    return (_scope(record), _text(record.get("kind"), "kind"),
            _text(record.get("comparison_basis"), "comparison_basis"),
            frozenset(_texts(record.get("criteria"), "criteria", nonempty=True)))


def _evidence_refs(record: dict, key: str, evidence: dict, *, case: str | None = None,
                   nonempty: bool = False) -> list[str]:
    refs = _texts(record.get(key), key, nonempty=nonempty)
    for identity in refs:
        ref = evidence.get(identity)
        if ref is None or set(ref["tested_scope"]) != _external_scope(record):
            raise ScopedAssuranceError(f"{key}: missing reference or exact scope mismatch")
        if case is not None and ref["case_identity"] != case:
            raise ScopedAssuranceError(f"{key}: case mismatch")
    return refs


def _activities(document: dict, evidence: dict) -> tuple[dict, dict, list]:
    statuses, kinds = _native_vocabulary()
    activities = _index(document.get("activities", []), "activities")
    results = _index(document.get("results", []), "results")
    basis_fields = {"subject", "configuration", "conditions", "kind", "comparison_basis", "criteria"}
    for result in results.values():
        _shape(result, {"id", "activity_id", "execution_ref", "completed", "verdict", "reasoning"} | basis_fields, "result")
        for key in ("activity_id", "execution_ref", "reasoning"):
            _text(result[key], key)
        if type(result["completed"]) is not bool:
            raise ScopedAssuranceError("result.completed: boolean required")
        if result["completed"]:
            if result["verdict"] not in ("pass", "fail", "inconclusive"):
                raise ScopedAssuranceError("completed result: native VerdictKind required")
        elif result["verdict"] is not None:
            raise ScopedAssuranceError("incomplete result cannot carry completed technical verdict")
        if result["activity_id"] not in activities:
            raise ScopedAssuranceError("result: orphan activity reference")
    views = []
    used_results = set()
    for activity in activities.values():
        _shape(activity, {"id", "lifecycle_context", "status", "case_identity", "responsible_actor",
                          "result_refs", "evidence_refs", "result_approval"} | basis_fields, "activity")
        basis = _basis(activity)
        for key in ("lifecycle_context", "status", "case_identity", "responsible_actor"):
            _text(activity[key], key)
        status = activity["status"]
        if status not in statuses or activity["kind"] not in kinds:
            raise ScopedAssuranceError("activity: unknown native status or activity kind")
        refs = _texts(activity["result_refs"], "result_refs")
        evidence_refs = _evidence_refs(activity, "evidence_refs", evidence, case=activity["case_identity"])
        retained = []
        for identity in refs:
            result = results.get(identity)
            if result is None or result["activity_id"] != activity["id"] or _basis(result) != basis:
                raise ScopedAssuranceError("activity: result scope/comparison basis mismatch")
            if result["execution_ref"] not in evidence_refs:
                raise ScopedAssuranceError("activity: result missing retained execution evidence")
            retained.append(result)
            used_results.add(identity)
        if status.startswith("Completed") and not retained:
            raise ScopedAssuranceError("completed activity requires retained result")
        if status == "NotStarted" and retained:
            raise ScopedAssuranceError("NotStarted cannot carry execution results")
        if status in ("Completed", "CompletedPassed", "CompletedFailed") and not all(r["completed"] for r in retained):
            raise ScopedAssuranceError("completed activity cannot carry incomplete execution")
        if status == "CompletedPassed" and not all(r["verdict"] == "pass" for r in retained):
            raise ScopedAssuranceError("CompletedPassed requires passing results against its basis")
        if status == "CompletedFailed" and not any(r["verdict"] == "fail" for r in retained):
            raise ScopedAssuranceError("CompletedFailed requires completed technical failure")
        if status == "CompletedUnsuccessful" and not any(not r["completed"] for r in retained):
            raise ScopedAssuranceError("CompletedUnsuccessful requires could-not-complete result")
        approval = _shape(activity["result_approval"], {"required", "reference"}, "result_approval")
        if type(approval["required"]) is not bool:
            raise ScopedAssuranceError("result_approval.required: boolean required")
        if approval["reference"] is not None:
            _evidence_refs({**activity, "approval_refs": [approval["reference"]]}, "approval_refs", evidence,
                           case=activity["case_identity"])
        if status in ("Completed", "CompletedPassed", "CompletedFailed") and approval["required"] and approval["reference"] is None:
            raise ScopedAssuranceError("completed activity requires necessary result approval reference")
        views.append({"id": activity["id"], "kind": activity["kind"], "reported_status": status,
                      "result_refs": refs, "implies_acceptance": False})
    if used_results != set(results):
        raise ScopedAssuranceError("result: unreferenced retained execution")
    return activities, results, views


def _claim_scope(record: dict) -> tuple:
    return (_text(record.get("claim"), "claim"), _scope(record))


def _assessments(document: dict, evidence: dict, supports: dict, activities: dict, results: dict) -> tuple[dict, list]:
    assessments = _index(document.get("assessments", []), "assessments")
    exception_fields = ("limitations", "contrary_result_refs", "discrepancy_refs", "gap_refs")
    for assessment in assessments.values():
        _shape(assessment, {"id", "claim", "subject", "configuration", "conditions", "comparison_basis", "criteria",
            "agreement_ref", "coverage_basis", "confidence_basis", "rigor_basis", "evidence_refs", "result_refs",
            "activity_refs", "case_refs", "assessor", "adequate_for_scope", "supports_claim", "conclusion", "reasoning"}
            | set(exception_fields), "assessment")
        scope = _claim_scope(assessment)
        criteria = set(_texts(assessment["criteria"], "assessment.criteria", nonempty=True))
        for key in ("comparison_basis", "agreement_ref", "coverage_basis", "confidence_basis", "rigor_basis",
                    "assessor", "conclusion", "reasoning"):
            _text(assessment[key], key)
        for key in ("adequate_for_scope", "supports_claim"):
            if type(assessment[key]) is not bool:
                raise ScopedAssuranceError(f"{key}: boolean required")
        for key in exception_fields:
            _texts(assessment[key], key)
        ev = set(_evidence_refs(assessment, "evidence_refs", evidence))
        rs = set(_texts(assessment["result_refs"], "assessment.result_refs"))
        ars = _texts(assessment["activity_refs"], "assessment.activity_refs")
        cases = set(_texts(assessment["case_refs"], "case_refs"))
        relevant_activities = {
            identity for identity, activity in activities.items()
            if _scope(activity) == scope[1]
            and activity["comparison_basis"] == assessment["comparison_basis"]
            and set(activity["criteria"]) & criteria
        }
        if not relevant_activities <= set(ars):
            raise ScopedAssuranceError("assessment: relevant supplied activities omitted")
        covered = set()
        expected_results = set()
        expected_cases = set()
        expected_evidence = set()
        for identity in ars:
            activity = activities.get(identity)
            if activity is None or _scope(activity) != scope[1] or activity["comparison_basis"] != assessment["comparison_basis"]:
                raise ScopedAssuranceError("assessment: activity scope/comparison mismatch")
            if not set(activity["criteria"]) <= criteria:
                raise ScopedAssuranceError("assessment: activity criteria mismatch")
            covered.update(activity["criteria"])
            expected_results.update(activity["result_refs"])
            expected_cases.add(activity["case_identity"])
            expected_evidence.update(activity["evidence_refs"])
        if not expected_evidence <= ev:
            raise ScopedAssuranceError("assessment: activity evidence omitted")
        if rs != expected_results or cases != expected_cases:
            raise ScopedAssuranceError("assessment: result/case population mismatch")
        negative = set()
        for identity in rs:
            result = results[identity]
            if result["execution_ref"] not in ev:
                raise ScopedAssuranceError("assessment: result evidence omitted")
            if not result["completed"] or result["verdict"] != "pass":
                negative.add(identity)
        contrary = set(assessment["contrary_result_refs"])
        if not negative <= contrary or not contrary <= rs:
            raise ScopedAssuranceError("assessment: contrary/nonpass results omitted or foreign")
        citations = [s for s in supports.values() if _claim_scope(s) == scope and s["evidence_ref"] in ev]
        cited_limits = {limit for citation in citations for limit in citation["limitations"]}
        if not cited_limits <= set(assessment["limitations"]):
            raise ScopedAssuranceError("assessment: cited support limitations omitted")
        if assessment["adequate_for_scope"] and (not ev or not rs or covered != criteria or not citations):
            raise ScopedAssuranceError("assessment: inadequate structural coverage for positive adequacy conclusion")
        if not assessment["adequate_for_scope"] and not assessment["gap_refs"]:
            raise ScopedAssuranceError("assessment: inadequate set requires explicit gap references")
    views = []
    for request in _index(document.get("requests", []), "requests").values():
        _shape(request, {"id", "claim", "subject", "configuration", "conditions", "purpose", "assessment_ref",
                         "unqualified", "acceptance_reference"}, "request")
        purpose = _text(request["purpose"], "purpose")
        if purpose not in ("establish-claim", "seek-acceptance") or type(request["unqualified"]) is not bool:
            raise ScopedAssuranceError("request: unknown purpose or nonboolean unqualified flag")
        assessment = assessments.get(_text(request["assessment_ref"], "assessment_ref"))
        if assessment is None or _claim_scope(request) != _claim_scope(assessment):
            raise ScopedAssuranceError("request: missing exact claim-level adequacy assessment")
        if not assessment["adequate_for_scope"]:
            raise ScopedAssuranceError("request: evidence-set adequacy not recorded positively")
        if purpose == "establish-claim" and not assessment["supports_claim"]:
            raise ScopedAssuranceError("request: assessor conclusion does not support claim")
        exceptions = {key: list(assessment[key]) for key in exception_fields}
        qualified = any(exceptions.values()) or not assessment["supports_claim"]
        acceptance = request["acceptance_reference"]
        if acceptance is not None:
            _shape(acceptance, {"claim", "subject", "configuration", "conditions", "policy_ref", "decision_registry_path",
                                "attestation_ref", "designated_authority", "exceptions"}, "acceptance_reference")
            if _claim_scope(acceptance) != _claim_scope(request):
                raise ScopedAssuranceError("acceptance_reference: exact scoped claim mismatch")
            for key in ("policy_ref", "decision_registry_path", "attestation_ref", "designated_authority"):
                _text(acceptance[key], key)
            supplied_exceptions = set(_texts(acceptance["exceptions"], "acceptance.exceptions"))
            required_exceptions = {v for values in exceptions.values() for v in values}
            if not required_exceptions <= supplied_exceptions:
                raise ScopedAssuranceError("acceptance_reference: exceptions hidden")
            _evidence_refs({**request, "attestation_refs": [acceptance["attestation_ref"]]}, "attestation_refs", evidence)
            if acceptance["attestation_ref"] in assessment["evidence_refs"]:
                raise ScopedAssuranceError("acceptance_reference: assessment/execution evidence is not a separate attestation")
            qualified = qualified or bool(supplied_exceptions)
        if request["unqualified"] and qualified:
            raise ScopedAssuranceError("request: exceptions/negative results cannot become unqualified technical satisfaction")
        views.append({"id": request["id"], "claim": request["claim"], "purpose": purpose,
                      "assessment_ref": assessment["id"], "structural_presentation_eligible": True,
                      "qualification_required": qualified, "exceptions": exceptions,
                      "acceptance_reference": acceptance, "technical_satisfaction": False,
                      "acceptance_authority_verified": False})
    return assessments, views


def validate_records(document: Any) -> dict[str, Any]:
    """Validate actual supplied records; external bytes/authority are not checked."""
    if not isinstance(document, dict) or not {"schema", "evidence", "supports"} <= set(document) or set(document) - {"schema", "evidence", "supports", "activities", "results", "assessments", "requests"}:
        raise ScopedAssuranceError("document: missing or unknown fields")
    if document["schema"] != SCHEMA:
        raise ScopedAssuranceError("schema mismatch")
    record_ids = set()
    for family in ("supports", "activities", "results", "assessments", "requests"):
        identities = set(_index(document.get(family, []), family))
        if record_ids & identities:
            raise ScopedAssuranceError("document: record identities overlap across families")
        record_ids.update(identities)
    if not isinstance(document["evidence"], list):
        raise ScopedAssuranceError("evidence: list required")
    evidence = {}
    for reference in document["evidence"]:
        _shape(reference, {"case_identity", "artifact_identity", "artifact_revision", "digest", "run", "tested_scope"}, "evidence")
        for key in ("case_identity", "artifact_identity", "artifact_revision", "run"):
            _text(reference[key], key)
        _texts(reference["tested_scope"], "tested_scope", nonempty=True)
        digest = reference["digest"]
        if isinstance(digest, dict):
            _shape(digest, {"algorithm", "value"}, "digest")
        raw = digest.get("value") if isinstance(digest, dict) else digest
        if not isinstance(raw, str) or not re.fullmatch(r"[0-9a-f]{64}", raw):
            raise ScopedAssuranceError("digest: exact lowercase sha256 required")
        try:
            normalized = validate_typed_reference(reference)
        except EvidenceReferenceError as exc:
            raise ScopedAssuranceError(str(exc)) from exc
        identity = normalized["version_identity"]
        if identity in evidence:
            raise ScopedAssuranceError(f"evidence: duplicate version identity {identity}")
        evidence[identity] = normalized
    supports = _index(document["supports"], "supports")
    for support in supports.values():
        _shape(support, {"id", "claim", "subject", "configuration", "conditions", "evidence_ref", "rationale", "limitations"}, "support")
        for key in ("claim", "evidence_ref", "rationale"):
            _text(support[key], key)
        _texts(support["limitations"], "limitations")
        ref = evidence.get(support["evidence_ref"])
        if ref is None or _external_scope(support) != set(ref["tested_scope"]):
            raise ScopedAssuranceError("support: missing evidence or exact scope mismatch")
    activities, results, views = _activities(document, evidence)
    assessments, requests = _assessments(document, evidence, supports, activities, results)
    return {"schema": "de4sdv.scoped-assurance-report/v1", "structurally_valid": True,
            "activity_count": len(activities), "activities": views,
            "assessment_count": len(assessments), "requests": requests,
            "support_count": len(supports), **_NO_CLAIMS,
            "validation_scope": "supplied-record structural eligibility only"}


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScopedAssuranceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="?", help="Supplied JSON record package; read only")
    parser.add_argument("--check-native-sources", action="store_true",
                        help="Check lexical adapter parity; never invokes a semantic validator")
    parser.add_argument("--upstream-archive", type=Path,
                        help="Optional already-retained archive for the source check; no fetching")
    args = parser.parse_args(argv)
    if (args.records is not None) == args.check_native_sources:
        parser.error("choose exactly one: a records path or --check-native-sources")
    if args.upstream_archive is not None and not args.check_native_sources:
        parser.error("--upstream-archive requires --check-native-sources")
    try:
        if args.check_native_sources:
            report = verify_native_sources(args.upstream_archive)
        else:
            report = validate_records(json.loads(args.records.read_text(encoding="utf-8"),
                                                object_pairs_hook=_unique_json_object))
    except (OSError, ValueError) as exc:
        print(json.dumps({"structurally_valid": False, "error": str(exc),
                          **_NO_CLAIMS}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
