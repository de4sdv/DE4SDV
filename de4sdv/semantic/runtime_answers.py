"""Runtime answer reports and their comparison (O4 Wave C2).

Collects what one semantic runtime answers over the complete witness-derived
subject population of the predicates the O3 cutover migrated (now served from
the frozen O2-chain layer), the class identity resolution of the migrated
classes, and the K pair (one modeled fact, two navigations); and compares two
such reports.

Extracted from the retired O3 equivalence runner (``scripts/run_o3_equivalence.py``,
deleted with the authored ontology). Two changes:

- an answer report is produced by ONE runtime; two reports are compared
  offline (:func:`compare_answer_reports`), so the runtimes may come from
  different revisions or processes;
- the comparison manifests carry the caller's real authority labels (the
  O3 runner hard-coded ``legacy-authored``/``o3-authority`` for every pair,
  mislabelling the Wave B model pairs; owner amendment 2026-10-08). Equal
  labels are refused: the authority path is the one intended variable.

A comparison is meaningful only over the same SysML API elements: both
reports must have read the same SysML project/commit with the same subject
populations, otherwise the basis mismatch blocks. Element ids are never
mapped by name.
"""
from __future__ import annotations

import json
from typing import Any

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import element_id, reference_ids

from .relationships import build_relationship_graph

ANSWER_REPORT_SCHEMA = "de4sdv.runtime-answer-report/v1"
COMPARISON_REPORT_SCHEMA = "de4sdv.runtime-answer-comparison/v1"
COMPARISON_MANIFEST_SCHEMA = "de4sdv.runtime-comparison-manifest/v1"

RELATIONSHIP_PREDICATES = (
    "hasSubject",
    "verifiedBy",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
    "hasRelevantArchitecture",
)
CLASS_IDENTITIES = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
    "VerificationCase",
)
#: ``VerificationCase`` is native-grounded: it never passes through the
#: file-mapped binder; its identity is the standard-library grounding proof.
NATIVE_CLASS_IDENTITY = "VerificationCase"
FILE_MAPPED_CLASSES = tuple(name for name in CLASS_IDENTITIES if name != NATIVE_CLASS_IDENTITY)
K_PAIR = ("derivesRequirementFromNeed", "derivedRequirementsOfNeed")
#: Reviewed O2.3 K-pair baseline: 5 authored DerivesFromNeed connection usages.
READINESS_BASELINE_K_WITNESS_COUNT = 5

#: Result fields compared as canonical SETS; trace paths stay ordered.
SET_FIELDS = ("targets", "witnesses", "nodes", "diagnostics", "unsupported_predicates")
ORDERED_FIELDS = ("path",)

_CLASSIFICATION_SEVERITY = {
    "EQUIVALENT": 0,
    "UNSUPPORTED_BOTH": 1,
    "NOT_YET_COMPARABLE": 2,
    "INTENTIONAL_MIGRATION_REVIEW_REQUIRED": 3,
    "BLOCKING_MISMATCH": 4,
}


def worst_classification(*classifications: str) -> str:
    """Severity-ordered merge of comparison classifications."""
    return max(classifications, key=lambda value: _CLASSIFICATION_SEVERITY.get(value, 4))


# ---------------------------------------------------------------------------
# Subject populations
# ---------------------------------------------------------------------------


def _collect_refs(element: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    found: set[str] = set()
    for key in keys:
        for candidate in reference_ids(element.get(key)):
            found.add(candidate)
    return found


def subject_population(elements: list[dict[str, Any]], predicate: str) -> list[str]:
    """Complete witness-derived eligible-subject coverage (deterministic, by UUID)."""
    subjects: set[str] = set()
    if predicate == "hasSubject":
        for element in elements:
            if str(element.get("@type")) == "SubjectMembership":
                subjects |= _collect_refs(element, ("owningRelatedElement", "owner", "memberElement"))
    elif predicate == "verifiedBy":
        for element in elements:
            if str(element.get("@type")) == "RequirementVerificationMembership":
                subjects |= _collect_refs(element, (
                    "owningRelatedElement", "owner", "memberElement", "ownedMemberElement",
                    "verifiedRequirement"))
    elif predicate in K_PAIR:
        for element in elements:
            if str(element.get("@type")) != "ConnectionUsage":
                continue
            subjects |= _collect_refs(element, (
                "owningRelatedElement", "owner", "ownedRelationship", "ownedElement", "ownedMember"))
            for key in ("ownedRelationship", "ownedElement", "ownedMember"):
                for child in element.get(key) or []:
                    if isinstance(child, dict):
                        subjects |= _collect_refs(child, (
                            "memberElement", "ownedRelatedElement", "owningRelatedElement",
                            "referencedFeature"))
    elif predicate == "hasRelevantArchitecture":
        for element in elements:
            if str(element.get("@type")) == "Dependency":
                subjects |= _collect_refs(element, ("source", "target", "owningRelatedElement", "owner"))
    else:
        raise ValueError(f"no subject population rule for predicate {predicate!r}")
    return sorted(subjects)


def k_subject_population(service, elements: list[dict[str, Any]]) -> list[str]:
    """K query subjects: the connected usages at the typed ends of every
    ``ConnectionUsage``, through the runtime's own end-resolution helpers.
    Role identity is decided by the traversal, never here."""
    traversal = service.traversal
    by_id = {candidate: element for element in elements
             if (candidate := element_id(element)) is not None}
    graph = build_relationship_graph(list(by_id.values()))
    subjects: list[str] = []
    seen: set[str] = set()
    for element in elements:
        if str(element.get("@type")) != "ConnectionUsage":
            continue
        try:
            records = traversal._connection_end_records(element, by_id, graph)
        except (IdentityNotFoundError, ValueError):
            continue
        for record in records:
            try:
                connected, _subsetting_id, _kind = traversal._connected_usage_id(
                    record["end_element_id"], graph, by_id)
            except (IdentityNotFoundError, ValueError, KeyError):
                continue
            if connected and connected in by_id and connected not in seen:
                seen.add(connected)
                subjects.append(connected)
    return sorted(subjects)


# ---------------------------------------------------------------------------
# Collection (one runtime)
# ---------------------------------------------------------------------------


def _result_record(service, predicate: str, subject_id: str, hops: list[Any]) -> dict[str, Any]:
    mapping = service.contract.relationship_mapping(predicate)
    blocked = predicate in service.traversal.blocked_predicates()
    targets: set[str] = set()
    witnesses: set[str] = set()
    strategies: set[str] = set()
    for hop in hops:
        target = element_id(hop.target)
        witness = element_id(hop.api_object)
        if target:
            targets.add(target)
        if witness:
            witnesses.add(witness)
        strategies.add(str(hop.strategy))
    k_witness: dict[str, Any] | None = None
    if predicate in K_PAIR and hops:
        hop_witness = getattr(hops[0], "witness", None)
        if isinstance(hop_witness, dict):
            k_witness = {key: hop_witness.get(key) for key in (
                "connection_id", "need_end_id", "derived_requirement_end_id",
                "role_lineage_provenance")}
    return {
        "source_revision": str(service.binding.git_commit),
        "sysml_project_id": str(service.binding.sysml_project_id),
        "sysml_commit_id": str(service.binding.sysml_commit_id),
        "predicate": predicate,
        "subject_id": subject_id,
        "direction": f"{mapping.domain} -> {mapping.range}",
        "query_direction": str(mapping.configuration.get("query_direction") or ""),
        "semantic_strength": str(mapping.semantic_strength),
        "claim_boundary": str(mapping.semantic_strength),
        "strategy": ",".join(sorted(strategies)),
        "support_state": "runtime-blocked" if blocked else "runtime-queryable",
        "completeness": "complete",
        "unsupported": [],
        "targets": sorted(targets),
        "witnesses": sorted(witnesses),
        "k_witness": k_witness,
    }


def collect_predicate(service, predicate: str, elements: list[dict[str, Any]]) -> dict[str, Any]:
    """Sweep one predicate over the complete witness-derived population."""
    by_id = {candidate: element for element in elements
             if (candidate := element_id(element)) is not None}
    subjects = (k_subject_population(service, elements) if predicate in K_PAIR
                else subject_population(elements, predicate))
    records: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, str]] = []
    for subject in subjects:
        try:
            hops = service.traversal.traverse(predicate, by_id[subject], elements)
        except IdentityNotFoundError as exc:
            if predicate not in K_PAIR:
                raise
            unresolved.append({"subject_id": subject, "error": str(exc)})
            continue
        records[subject] = _result_record(service, predicate, subject, hops)
    return {"subjects": subjects, "records": records, "unresolved": unresolved}


def class_identities(service, *, verification_case_grounding: dict[str, Any] | None = None
                     ) -> dict[str, Any]:
    """Class identity resolution of the migrated classes under one runtime."""
    identities: dict[str, Any] = {}
    for name in FILE_MAPPED_CLASSES:
        bound = service.binder.bind_class(name)
        mapping = service.contract.mapping(name)
        identities[name] = {"element_id": bound.sysml.element_id, "sysml_type": bound.sysml.type,
                            "declaration": getattr(mapping, "declaration", None),
                            "source_file": getattr(mapping, "file", None)}
    grounding = verification_case_grounding or {}
    result = str(grounding.get("result") or "")
    if result not in ("EQUIVALENT", "NOT_YET_COMPARABLE", "BLOCKING_MISMATCH"):
        result = "NOT_YET_COMPARABLE"
    identities[NATIVE_CLASS_IDENTITY] = {"grounding_result": result,
                                         "mechanism": "exact-revision standard-library grounding proof"}
    return identities


def k_self_evidence(collected: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """One runtime's K pair: forward and inverse share one witness population
    of the reviewed size, each fact appears once per navigation, no unresolved
    subject. Insufficient coverage is never equivalence."""
    forward_predicate, inverse_predicate = "derivedRequirementsOfNeed", "derivesRequirementFromNeed"

    def witnesses(predicate: str) -> list[str]:
        return sorted({w for record in collected[predicate]["records"].values()
                       for w in record["witnesses"]})

    def duplicates(predicate: str) -> list[str]:
        per_witness: dict[str, list[str]] = {}
        for subject, record in collected[predicate]["records"].items():
            for witness in record["witnesses"]:
                per_witness.setdefault(witness, []).append(subject)
        return sorted(w for w, subjects in per_witness.items() if len(subjects) > 1)

    forward, inverse = witnesses(forward_predicate), witnesses(inverse_predicate)
    unresolved = [entry for p in K_PAIR for entry in collected[p].get("unresolved", [])]
    errors, missing = [], []
    for direction, population in (("forward", forward), ("inverse", inverse)):
        if len(population) != READINESS_BASELINE_K_WITNESS_COUNT:
            missing.append(f"{direction} witness population is {len(population)}; the reviewed "
                           f"baseline is {READINESS_BASELINE_K_WITNESS_COUNT}")
    if not unresolved and forward != inverse:
        errors.append("forward and inverse navigations do not share one witness population")
    for predicate in K_PAIR:
        if duplicates(predicate):
            errors.append(f"{predicate} duplicates modeled facts {duplicates(predicate)}")
    if unresolved:
        missing.append(f"{len(unresolved)} unresolved K subject(s): "
                       + "; ".join(f"{e['subject_id']}: {e['error']}" for e in unresolved[:3]))
    classification = ("BLOCKING_MISMATCH" if errors else "NOT_YET_COMPARABLE" if missing
                      else "EQUIVALENT")
    return {"classification": classification, "forward_witness_population": forward,
            "inverse_witness_population": inverse, "population_complete": not errors and not missing,
            "errors": errors, "missing": missing}


def collect_answers(service, elements: list[dict[str, Any]], *, label: str,
                    verification_case_grounding: dict[str, Any] | None = None) -> dict[str, Any]:
    """One runtime's answer report over the migrated identity set."""
    if not str(label or "").strip():
        raise ValueError("an answer report needs the runtime's authority label")
    collected = {predicate: collect_predicate(service, predicate, elements)
                 for predicate in RELATIONSHIP_PREDICATES}
    binding = service.binding
    return {
        "schema": ANSWER_REPORT_SCHEMA,
        "label": label,
        "authority_id": str(getattr(service, "semantic_authority_id", "")),
        "git_revision": str(binding.git_commit),
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "evaluation_scope": str(binding.scope),
        "element_count": len(elements),
        "predicates": collected,
        "classes": class_identities(service, verification_case_grounding=verification_case_grounding),
        "k_pair": k_self_evidence(collected),
    }


# ---------------------------------------------------------------------------
# Comparison (two reports)
# ---------------------------------------------------------------------------


def comparison_manifest(report: dict[str, Any], subject_ids: list[str]) -> dict[str, Any]:
    """The comparison basis of one side; ``authority_path`` is its real label."""
    return {
        "schema": COMPARISON_MANIFEST_SCHEMA,
        "authority_path": str(report.get("label") or ""),
        "authority_id": str(report.get("authority_id") or ""),
        "git_revision": str(report.get("git_revision") or ""),
        "sysml_project_id": str(report.get("sysml_project_id") or ""),
        "sysml_commit_id": str(report.get("sysml_commit_id") or ""),
        "subject_ids": list(subject_ids),
        "evaluation_scope": str(report.get("evaluation_scope") or ""),
        "element_count": report.get("element_count"),
    }


def validate_manifest_pair(old: dict[str, Any], new: dict[str, Any], *,
                           allow_revision_change: bool = False) -> list[str]:
    """The only intended variable is the authority path (and, when allowed,
    the Git revision whose runtime produced the answers). Any other basis
    difference blocks; equal or empty labels block."""
    errors: list[str] = []
    for manifest in (old, new):
        if manifest.get("schema") != COMPARISON_MANIFEST_SCHEMA:
            errors.append(f"manifest-schema:{manifest.get('schema')!r}")
        if not manifest.get("authority_path"):
            errors.append("authority-path-missing")
    fields = ["sysml_project_id", "sysml_commit_id", "subject_ids", "evaluation_scope", "element_count"]
    if not allow_revision_change:
        fields.insert(0, "git_revision")
    for field_name in fields:
        if old.get(field_name) != new.get(field_name):
            errors.append(f"basis-mismatch:{field_name}")
    if old.get("authority_path") == new.get("authority_path"):
        errors.append("authority-path-not-distinct")
    return errors


def _canonicalize(value: Any, *, ordered: bool) -> Any:
    if isinstance(value, list):
        if ordered:
            return value
        try:
            return sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
        except TypeError:
            return sorted(str(item) for item in value)
    return value


def compare_semantic_results(old_result: dict[str, Any], new_result: dict[str, Any], *,
                             allow_revision_change: bool = False) -> dict[str, Any]:
    """Compare two per-subject results over the same SysML API elements."""
    mismatches: list[str] = []
    basis = [("sysml_project_id", "sysml-project"), ("sysml_commit_id", "sysml-commit")]
    if not allow_revision_change:
        basis.insert(0, ("source_revision", "revision"))
    for key, label in basis:
        if old_result.get(key) != new_result.get(key):
            mismatches.append(f"basis-mismatch:{label}")
    for key, label in (("predicate", "predicate-mismatch"), ("subject_id", "subject-mismatch"),
                       ("direction", "canonical-direction-mismatch"),
                       ("semantic_strength", "semantic-strength-mismatch"),
                       ("claim_boundary", "claim-boundary-mismatch"),
                       ("support_state", "support-state-mismatch"),
                       ("completeness", "completeness-mismatch"),
                       ("unsupported", "unsupported-state-mismatch")):
        if old_result.get(key) != new_result.get(key):
            mismatches.append(label)
    for field_name in SET_FIELDS + ORDERED_FIELDS:
        if field_name not in old_result and field_name not in new_result:
            continue
        ordered = field_name in ORDERED_FIELDS
        if (_canonicalize(old_result.get(field_name), ordered=ordered)
                != _canonicalize(new_result.get(field_name), ordered=ordered)):
            mismatches.append(f"{field_name}-mismatch")
    return {"classification": "EQUIVALENT" if not mismatches else "BLOCKING_MISMATCH",
            "mismatches": mismatches}


def compare_collected(old: dict[str, Any], new: dict[str, Any], *,
                      allow_revision_change: bool = False) -> dict[str, Any]:
    subjects = sorted(set(old["subjects"]) | set(new["subjects"]))
    mismatches: list[dict[str, Any]] = []
    for subject in subjects:
        old_result, new_result = old["records"].get(subject), new["records"].get(subject)
        if old_result is None or new_result is None:
            comparison = {"classification": "BLOCKING_MISMATCH",
                          "mismatches": ["subject-population-mismatch"]}
        else:
            comparison = compare_semantic_results(old_result, new_result,
                                                  allow_revision_change=allow_revision_change)
        if comparison["classification"] != "EQUIVALENT":
            entry = {"subject_id": subject, "mismatches": comparison["mismatches"]}
            if old_result is not None and new_result is not None:
                entry.update(old_targets=old_result["targets"], new_targets=new_result["targets"])
            mismatches.append(entry)
    return {"classification": "EQUIVALENT" if not mismatches else "BLOCKING_MISMATCH",
            "subject_count": len(subjects), "mismatch_count": len(mismatches),
            "mismatches": mismatches[:50]}


def compare_answer_reports(old: dict[str, Any], new: dict[str, Any], *,
                           allow_revision_change: bool = False) -> dict[str, Any]:
    """Compare two answer reports; manifests carry each report's own label."""
    for report in (old, new):
        if report.get("schema") != ANSWER_REPORT_SCHEMA:
            raise ValueError(f"not an answer report: {report.get('schema')!r}")
    subject_ids = {side: sorted({s for p in RELATIONSHIP_PREDICATES
                                 for s in report["predicates"][p]["subjects"]})
                   for side, report in (("old", old), ("new", new))}
    manifests = {"old": comparison_manifest(old, subject_ids["old"]),
                 "new": comparison_manifest(new, subject_ids["new"])}
    manifest_errors = validate_manifest_pair(manifests["old"], manifests["new"],
                                             allow_revision_change=allow_revision_change)
    per_identity: dict[str, Any] = {}
    for predicate in RELATIONSHIP_PREDICATES:
        compared = compare_collected(old["predicates"][predicate], new["predicates"][predicate],
                                     allow_revision_change=allow_revision_change)
        per_identity[predicate] = {"kind": "relationship", **compared}
    for predicate in K_PAIR:
        k_states = [old["k_pair"]["classification"], new["k_pair"]["classification"]]
        same_population = (old["k_pair"]["forward_witness_population"]
                           == new["k_pair"]["forward_witness_population"])
        k_class = worst_classification(*k_states, "EQUIVALENT" if same_population
                                       else "BLOCKING_MISMATCH")
        per_identity[predicate]["classification"] = worst_classification(
            per_identity[predicate]["classification"], k_class)
        per_identity[predicate]["k_pair"] = {"old": old["k_pair"]["classification"],
                                             "new": new["k_pair"]["classification"],
                                             "same_witness_population": same_population}
    for name in CLASS_IDENTITIES:
        a, b = old["classes"].get(name), new["classes"].get(name)
        if name == NATIVE_CLASS_IDENTITY:
            results = [str((a or {}).get("grounding_result")), str((b or {}).get("grounding_result"))]
            classification = worst_classification(*results)
        else:
            classification = "EQUIVALENT" if a == b and a is not None else "BLOCKING_MISMATCH"
        per_identity[name] = {"kind": "class", "classification": classification,
                              "old": a, "new": b}
    classifications = [entry["classification"] for entry in per_identity.values()]
    overall = ("BLOCKING_MISMATCH" if manifest_errors
               else worst_classification(*classifications))
    return {
        "schema": COMPARISON_REPORT_SCHEMA,
        "labels": {"old": old.get("label"), "new": new.get("label")},
        "manifests": manifests,
        "manifest_validation": {"classification": "EQUIVALENT" if not manifest_errors
                                else "BLOCKING_MISMATCH", "errors": manifest_errors},
        "per_identity": per_identity,
        "overall": overall,
    }


__all__ = ["ANSWER_REPORT_SCHEMA", "COMPARISON_MANIFEST_SCHEMA", "COMPARISON_REPORT_SCHEMA",
           "CLASS_IDENTITIES", "K_PAIR", "RELATIONSHIP_PREDICATES", "collect_answers",
           "collect_predicate", "compare_answer_reports", "compare_collected",
           "compare_semantic_results", "comparison_manifest", "k_self_evidence",
           "subject_population", "validate_manifest_pair", "worst_classification"]
