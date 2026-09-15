#!/usr/bin/env python3
"""O3 same-revision runtime equivalence runner and closure-evidence builder.

Stage A machinery (evidence tooling; NOT activation):

- ``bundle`` mode builds the candidate authority bundle CORE at an exact Git
  revision, runs the executable VerificationCase standard-library grounding
  proof against the bound API revision, and writes the closed executable
  bundle + the structured closure attestation;
- ``compare`` mode instantiates the OLD authority path (legacy authored
  ``KernelContract``) and the NEW candidate authority path (verified closed
  bundle) over the SAME engineering inputs and produces the same-revision
  runtime equivalence report (``de4sdv.o3-runtime-equivalence-report/v1``).

The only semantic variable between the two paths is the authority path.
Any basis difference (revision, SysML project/commit, import closure,
subject population, runtime build, completeness boundary) blocks; any
semantic difference blocks; support publication and runtime support are
compared as SEPARATE dimensions. Nothing here activates O3 in production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import o3_bundle as ob  # noqa: E402
from de4sdv.semantic import o3_equivalence as oe  # noqa: E402
from de4sdv.sysml_api.repository import element_id  # noqa: E402

RUNTIME_EQUIVALENCE_REPORT_SCHEMA = "de4sdv.o3-runtime-equivalence-report/v1"
VERIFICATION_CASE_GROUNDING_SCHEMA = "de4sdv.o3-verification-case-grounding/v1"

#: Reviewed anchors of the pinned standard library document.
VERIFICATIONCASE_LIBRARY_DOCUMENT_SUFFIX = "Systems Library/VerificationCases.sysml"
VERIFICATIONCASE_DEFINITION_ANCHOR = "VerificationCase"
VERIFICATIONCASE_USAGE_ANCHOR = "verificationCases"
VERIFICATIONCASE_DEFINITION_TYPE = "VerificationCaseDefinition"
VERIFICATIONCASE_USAGE_TYPE = "VerificationCaseUsage"

#: Reviewed O2.3 K-pair baseline: the v1.2 artifact records "5 authored
#: connection usages" as the reviewed witness population. The runner compares
#: the exact same-revision population old-vs-new (must be equal) and flags a
#: drift from this reviewed baseline separately for review. (Test-locked
#: against the artifact statement.)
READINESS_BASELINE_K_WITNESS_COUNT = 5

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


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit(f"git rev-parse HEAD failed: {result.stderr.strip()}")
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# VerificationCase exact-revision standard-library grounding proof
# ---------------------------------------------------------------------------


def prove_verification_case_grounding(
    elements: list[dict[str, Any]],
    *,
    element_sources: dict[str, str] | None = None,
    library_document_suffix: str = VERIFICATIONCASE_LIBRARY_DOCUMENT_SUFFIX,
) -> dict[str, Any]:
    """Prove the governed standard-library grounding of VerificationCase.

    Identity is finished by STRUCTURE, never by qualified-name text: for each
    governed verification definition/usage, an IMPLIED Subclassification
    (definition role) / Subsetting (usage role) edge must resolve to exactly
    one candidate whose provenance lives in the pinned
    ``Systems Library/VerificationCases.sysml`` document — evidenced by the
    serializer-recorded source document (when supplied) or the serialized
    reference URI. The candidate's name must match the reviewed anchor name
    (an additional check, not the proof). Names may locate candidates; they
    never finish identity.

    Results: ``EQUIVALENT`` when every governed element proves its role
    anchor with a single consistent anchor identity; ``BLOCKING_MISMATCH``
    when structure/anchors/roles disagree; ``NOT_YET_COMPARABLE`` when the
    imported representation cannot establish the proof (missing implied
    edges, missing library provenance signals).
    """
    from de4sdv.semantic.relationships import build_relationship_graph

    by_id: dict[str, dict[str, Any]] = {}
    for element in elements:
        candidate = element_id(element)
        if candidate is not None:
            by_id[candidate] = element
    graph = build_relationship_graph(elements)

    governed_definitions = [
        element
        for element in elements
        if str(element.get("@type")) == VERIFICATIONCASE_DEFINITION_TYPE
    ]
    governed_usages = [
        element
        for element in elements
        if str(element.get("@type")) == VERIFICATIONCASE_USAGE_TYPE
    ]
    result: dict[str, Any] = {
        "schema": VERIFICATION_CASE_GROUNDING_SCHEMA,
        "result": "NOT_YET_COMPARABLE",
        "anchors": {
            "definition_role": {
                "library_identity": VERIFICATIONCASE_DEFINITION_ANCHOR,
                "mechanism": "implied Subclassification",
                "applies_to": VERIFICATIONCASE_DEFINITION_TYPE,
            },
            "usage_role": {
                "library_identity": VERIFICATIONCASE_USAGE_ANCHOR,
                "mechanism": "implied Subsetting",
                "applies_to": VERIFICATIONCASE_USAGE_TYPE,
            },
        },
        "governed_population": {
            "definitions": len(governed_definitions),
            "usages": len(governed_usages),
        },
        "proved": {"definition_role": [], "usage_role": []},
        "missing": [],
        "conflicts": [],
    }
    if not governed_definitions or not governed_usages:
        result["missing"].append(
            "governed VerificationCaseDefinition/Usage population is empty in "
            "the imported revision"
        )
        return result

    def _library_provenance(hop_target: str, hop_uri: str | None) -> str | None:
        if element_sources:
            source = element_sources.get(hop_target)
            if source and str(source).endswith(library_document_suffix):
                return "serializer-recorded-source-document"
        if hop_uri and library_document_suffix in str(hop_uri):
            return "serialized-reference-uri"
        return None

    def _prove(
        governed: list[dict[str, Any]],
        *,
        families: tuple[str, ...],
        expected_anchor_name: str,
        role: str,
    ) -> None:
        anchor_ids: set[str] = set()
        for element in governed:
            governed_id = element_id(element)
            if governed_id is None:
                result["missing"].append(f"{role}: governed element without id")
                continue
            proved_here: list[dict[str, Any]] = []
            for hop in graph.outgoing(governed_id, families):
                if not hop.is_implied:
                    continue
                if hop.kind[:1].isupper() and not any(
                    family.lower() in hop.kind.lower() for family in families
                ):
                    continue
                target = by_id.get(hop.target)
                if target is None:
                    continue
                provenance = _library_provenance(hop.target, hop.target_uri)
                if provenance is None:
                    continue
                target_name = str(
                    target.get("declaredName") or target.get("name") or ""
                )
                if target_name != expected_anchor_name:
                    result["conflicts"].append(
                        f"{role}: implied {hop.kind} from {governed_id} targets "
                        f"library-document element named {target_name!r}, not "
                        f"the reviewed anchor {expected_anchor_name!r}"
                    )
                    continue
                anchor_ids.add(hop.target)
                proved_here.append(
                    {
                        "governed_element_id": governed_id,
                        "anchor_element_id": hop.target,
                        "mechanism": hop.kind,
                        "provenance": provenance,
                        "witness_hop_id": hop.witness_id,
                    }
                )
            if not proved_here:
                result["missing"].append(
                    f"{role}: no implied library-grounding proof for governed "
                    f"element {governed_id}"
                )
            result["proved"][role].extend(proved_here)
        if len(anchor_ids) > 1:
            result["conflicts"].append(
                f"{role}: multiple distinct anchor identities "
                f"{sorted(anchor_ids)}; library identity is ambiguous"
            )

    _prove(
        governed_definitions,
        families=("Subclassification",),
        expected_anchor_name=VERIFICATIONCASE_DEFINITION_ANCHOR,
        role="definition_role",
    )
    _prove(
        governed_usages,
        families=("Subsetting",),
        expected_anchor_name=VERIFICATIONCASE_USAGE_ANCHOR,
        role="usage_role",
    )

    if result["conflicts"]:
        result["result"] = "BLOCKING_MISMATCH"
        return result
    if result["missing"]:
        result["result"] = "NOT_YET_COMPARABLE"
        result["note"] = (
            "the imported representation cannot establish the full "
            "standard-library grounding; O3 activation is blocked until the "
            "proof step succeeds at the exact cutover revision"
        )
        return result
    result["result"] = "EQUIVALENT"
    return result


# ---------------------------------------------------------------------------
# Deterministic subject populations and per-predicate sweeps
# ---------------------------------------------------------------------------


def _elements_of(service) -> list[dict[str, Any]]:
    return service._elements()


def _collect_refs(element: dict[str, Any], keys: tuple[str, ...]) -> set[str]:
    from de4sdv.sysml_api.repository import reference_ids

    found: set[str] = set()
    for key in keys:
        for candidate in reference_ids(element.get(key)):
            found.add(candidate)
    return found


def subject_population(
    elements: list[dict[str, Any]], predicate: str
) -> list[str]:
    """Complete witness-derived eligible-subject coverage (deterministic).

    Every element that participates in any governed witness of the predicate
    — owners, members, referenced endpoints — is a comparison subject, so
    both qualifying hops and quiet-absence boundaries are exercised. Sorted
    by UUID; identity is authoritative, names are never used.
    """
    subjects: set[str] = set()
    if predicate == "hasSubject":
        for element in elements:
            if str(element.get("@type")) != "SubjectMembership":
                continue
            subjects |= _collect_refs(
                element, ("owningRelatedElement", "owner", "memberElement")
            )
    elif predicate == "verifiedBy":
        for element in elements:
            if str(element.get("@type")) != "RequirementVerificationMembership":
                continue
            subjects |= _collect_refs(
                element,
                (
                    "owningRelatedElement",
                    "owner",
                    "memberElement",
                    "ownedMemberElement",
                    "verifiedRequirement",
                ),
            )
    elif predicate in ("derivesRequirementFromNeed", "derivedRequirementsOfNeed"):
        for element in elements:
            if str(element.get("@type")) != "ConnectionUsage":
                continue
            subjects |= _collect_refs(
                element,
                (
                    "owningRelatedElement",
                    "owner",
                    "ownedRelationship",
                    "ownedElement",
                    "ownedMember",
                ),
            )
            for key in ("ownedRelationship", "ownedElement", "ownedMember"):
                for child in element.get(key) or []:
                    if not isinstance(child, dict):
                        continue
                    subjects |= _collect_refs(
                        child,
                        (
                            "memberElement",
                            "ownedRelatedElement",
                            "owningRelatedElement",
                            "referencedFeature",
                        ),
                    )
    elif predicate == "hasRelevantArchitecture":
        for element in elements:
            if str(element.get("@type")) != "Dependency":
                continue
            subjects |= _collect_refs(
                element, ("source", "target", "owningRelatedElement", "owner")
            )
    else:
        raise ValueError(f"no subject population rule for predicate {predicate!r}")
    return sorted(subjects)


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
    return {
        "source_revision": str(service.binding.git_commit),
        "sysml_project_id": str(service.binding.sysml_project_id),
        "sysml_commit_id": str(service.binding.sysml_commit_id),
        "predicate": predicate,
        "subject_id": subject_id,
        "direction": f"{mapping.domain} -> {mapping.range}",
        "semantic_strength": str(mapping.semantic_strength),
        # Runtime surfaces carry no claim TEXT; the compared claim CLASS is
        # the authority-declared strength class (the artifact-level claim
        # text was compared statically by the readiness package). Structural
        # claim drift is caught by the strength comparison.
        "claim_boundary": str(mapping.semantic_strength),
        "strategy": ",".join(sorted(strategies)),
        "support_state": "runtime-blocked" if blocked else "runtime-queryable",
        "completeness": "complete",
        "unsupported": [],
        "targets": sorted(targets),
        "witnesses": sorted(witnesses),
    }


def collect_predicate(
    service, predicate: str, elements: list[dict[str, Any]]
) -> dict[str, Any]:
    """Sweep one predicate over the complete witness-derived population.

    Returns per-subject result records (deterministic; UUID-ordered).
    """
    by_id = {
        candidate: element
        for element in elements
        if (candidate := element_id(element)) is not None
    }
    subjects = subject_population(elements, predicate)
    records: dict[str, dict[str, Any]] = {}
    for subject in subjects:
        element = by_id[subject]
        hops = service.traversal.traverse(predicate, element, elements)
        records[subject] = _result_record(service, predicate, subject, hops)
    return {"subjects": subjects, "records": records}


def compare_collected(
    old_collected: dict[str, Any], new_collected: dict[str, Any]
) -> dict[str, Any]:
    """Compare two collected sweeps of the SAME predicate."""
    subjects = sorted(
        set(old_collected["subjects"]) | set(new_collected["subjects"])
    )
    results: dict[str, dict[str, Any]] = {}
    mismatches: list[dict[str, Any]] = []
    for subject in subjects:
        old_result = old_collected["records"].get(subject)
        new_result = new_collected["records"].get(subject)
        if old_result is None or new_result is None:
            comparison = {
                "classification": "BLOCKING_MISMATCH",
                "mismatches": ["subject-population-mismatch"],
            }
        else:
            comparison = oe.compare_semantic_results(old_result, new_result)
        results[subject] = {
            "classification": comparison["classification"],
            "old": old_result,
            "new": new_result,
            "mismatches": comparison["mismatches"],
        }
        if comparison["classification"] != "EQUIVALENT":
            mismatch: dict[str, Any] = {
                "subject_id": subject,
                "mismatches": comparison["mismatches"],
            }
            if old_result is not None and new_result is not None:
                mismatch.update(
                    {
                        "old_targets": old_result["targets"],
                        "new_targets": new_result["targets"],
                        "old_witnesses": old_result["witnesses"],
                        "new_witnesses": new_result["witnesses"],
                    }
                )
            mismatches.append(mismatch)
    classification = "EQUIVALENT" if not mismatches else "BLOCKING_MISMATCH"
    return {
        "classification": classification,
        "subject_count": len(subjects),
        "subjects": results,
        "mismatches": mismatches[:50],
        "mismatch_count": len(mismatches),
    }


# ---------------------------------------------------------------------------
# K pair, class identity, support preservation
# ---------------------------------------------------------------------------


def k_pair_evidence(
    old_collected: dict[str, dict[str, Any]],
    new_collected: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """ONE modeled fact / TWO navigations, compared at the same revision."""
    def _witnesses(collected: dict[str, Any], predicate: str, side: str) -> set[str]:
        found: set[str] = set()
        for record in collected[predicate]["records"].values():
            found |= set(record["witnesses"])
        return found

    old_navigations = {
        name: {"witnesses": sorted(_witnesses(old_collected, name, "old"))}
        for name in oe.K_PAIR
    }
    new_navigations = {
        name: {"witnesses": sorted(_witnesses(new_collected, name, "new"))}
        for name in oe.K_PAIR
    }
    errors = oe.check_k_pair_witness_consistency(old_navigations, new_navigations)
    population = sorted(set(old_navigations[oe.K_PAIR[0]]["witnesses"]))
    evidence: dict[str, Any] = {
        "classification": "BLOCKING_MISMATCH" if errors else "EQUIVALENT",
        "errors": errors,
        "old_witness_population": population,
        "new_witness_population": sorted(
            set(new_navigations[oe.K_PAIR[0]]["witnesses"])
        ),
        "reviewed_baseline_statement": None,
        "drift_from_readiness_baseline": None,
    }
    artifact = ROOT / "docs/method-conformance/o2/semantic-projection-v1.2.json"
    try:
        document = json.loads(artifact.read_text(encoding="utf-8"))
        for row in document.get("predicates", []):
            if row.get("identity") == "derivesRequirementFromNeed":
                evidence["reviewed_baseline_statement"] = str(
                    (row.get("relation") or {})
                    .get("one_modeled_fact_two_navigations", {})
                    .get("witness_population")
                    or ""
                )
    except (OSError, ValueError):
        pass
    if evidence["classification"] == "EQUIVALENT":
        evidence["drift_from_readiness_baseline"] = (
            len(population) != READINESS_BASELINE_K_WITNESS_COUNT
        )
    return evidence


def compare_class_identities(old_service, new_service) -> dict[str, Any]:
    """Class identity resolution under both authority paths (UUID-based)."""
    results: dict[str, Any] = {}
    classification = "EQUIVALENT"
    for name in CLASS_IDENTITIES:
        old_binding = old_service.binder.bind_class(name)
        new_binding = new_service.binder.bind_class(name)
        old_mapping = old_service.contract.mapping(name)
        new_mapping = new_service.contract.mapping(name)
        entry: dict[str, Any] = {
            "old_element_id": old_binding.sysml.element_id,
            "new_element_id": new_binding.sysml.element_id,
            "old_sysml_type": old_binding.sysml.type,
            "new_sysml_type": new_binding.sysml.type,
        }
        ok = (
            entry["old_element_id"] == entry["new_element_id"]
            and entry["old_sysml_type"] == entry["new_sysml_type"]
        )
        if name != "VerificationCase":
            entry["old_declaration"] = getattr(old_mapping, "declaration", None)
            entry["new_declaration"] = getattr(new_mapping, "declaration", None)
            entry["old_source_file"] = getattr(old_mapping, "file", None)
            entry["new_source_file"] = getattr(new_mapping, "file", None)
            ok = ok and (
                entry["old_declaration"] == entry["new_declaration"]
                and entry["old_source_file"] == entry["new_source_file"]
            )
        else:
            entry["grounding"] = (
                "native construct; the standard-library grounding proof is "
                "reported separately"
            )
        entry["classification"] = "EQUIVALENT" if ok else "BLOCKING_MISMATCH"
        if not ok:
            classification = "BLOCKING_MISMATCH"
        results[name] = entry
    return {"classification": classification, "identities": results}


def support_preservation_evidence(
    old_collected: dict[str, dict[str, Any]],
    new_collected: dict[str, dict[str, Any]],
    projection_documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Two SEPARATE dimensions: artifact publication vs runtime behavior.

    ``artifact_support_preservation`` proves publication caused no support
    promotion (every migrated Projection row stays vocabulary-only); the
    runtime dimension compares the old/new runtime behavior states per
    predicate (runtime-queryable / runtime-blocked) at the same revision.
    """
    artifact_rows: dict[str, str] = {}
    for document in projection_documents:
        for section in ("concepts", "predicates"):
            for row in document.get(section, []):
                identity = row.get("identity") or row.get("for_concept")
                if identity in ob.MIGRATED_IDENTITIES:
                    artifact_rows[identity] = str(row.get("support_state") or "")
    promotion = sorted(
        identity
        for identity, state in artifact_rows.items()
        if state != "vocabulary-only"
    )
    artifact = {
        "classification": "EQUIVALENT" if not promotion else "BLOCKING_MISMATCH",
        "rows": artifact_rows,
        "promoted": promotion,
        "note": "artifact publication never promotes support (vocabulary-only)",
    }
    runtime: dict[str, Any] = {"predicates": {}}
    runtime_classification = "EQUIVALENT"
    for predicate in RELATIONSHIP_PREDICATES:
        old_states = {
            record["support_state"]
            for record in old_collected[predicate]["records"].values()
        }
        new_states = {
            record["support_state"]
            for record in new_collected[predicate]["records"].values()
        }
        ok = old_states == new_states
        runtime["predicates"][predicate] = {
            "old_states": sorted(old_states),
            "new_states": sorted(new_states),
            "classification": "EQUIVALENT" if ok else "BLOCKING_MISMATCH",
        }
        if not ok:
            runtime_classification = "BLOCKING_MISMATCH"
    runtime["classification"] = runtime_classification
    return {"artifact_support_preservation": artifact, "runtime_behavior": runtime}


# ---------------------------------------------------------------------------
# Same-revision report assembly
# ---------------------------------------------------------------------------


def build_runtime_equivalence_report(
    old_service,
    new_service,
    *,
    root: Path,
    bundle: dict[str, Any],
    binding: Any,
    binding_sha256: str,
    import_closure_digest: str,
    git_revision: str,
    verification_case_grounding: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """The full same-revision equivalence report over both authority paths."""
    elements = _elements_of(new_service)
    runtime_build = ob.compute_runtime_build(root)
    old_collected: dict[str, dict[str, Any]] = {}
    new_collected: dict[str, dict[str, Any]] = {}
    compared: dict[str, dict[str, Any]] = {}
    subject_ids: set[str] = set()
    for predicate in RELATIONSHIP_PREDICATES:
        old_collected[predicate] = collect_predicate(old_service, predicate, elements)
        new_collected[predicate] = collect_predicate(new_service, predicate, elements)
        compared[predicate] = compare_collected(
            old_collected[predicate], new_collected[predicate]
        )
        subject_ids |= set(old_collected[predicate]["subjects"])
        subject_ids |= set(new_collected[predicate]["subjects"])
    subject_ids_sorted = sorted(subject_ids)

    manifests = {
        "old": {
            "schema": oe.COMPARISON_MANIFEST_SCHEMA,
            "authority_path": "legacy-authored",
            "git_revision": str(binding.git_commit),
            "sysml_project_id": str(binding.sysml_project_id),
            "sysml_commit_id": str(binding.sysml_commit_id),
            "import_closure_digest": import_closure_digest,
            "subject_ids": subject_ids_sorted,
            "evaluation_scope": str(binding.scope),
            "runtime_build": runtime_build["id"],
            "completeness_boundary": "validated-full-model",
        },
        "new": {
            "schema": oe.COMPARISON_MANIFEST_SCHEMA,
            "authority_path": "o3-candidate",
            "git_revision": str(binding.git_commit),
            "sysml_project_id": str(binding.sysml_project_id),
            "sysml_commit_id": str(binding.sysml_commit_id),
            "import_closure_digest": import_closure_digest,
            "subject_ids": subject_ids_sorted,
            "evaluation_scope": str(binding.scope),
            "runtime_build": runtime_build["id"],
            "completeness_boundary": "validated-full-model",
        },
    }
    manifest_errors = oe.validate_manifest_pair(manifests["old"], manifests["new"])

    k_evidence = k_pair_evidence(old_collected, new_collected)
    classes = compare_class_identities(old_service, new_service)
    projection_documents = [
        json.loads((root / rel).read_text(encoding="utf-8"))
        for rel, _schema in ob.PROJECTION_CHAIN
    ]
    support = support_preservation_evidence(
        old_collected, new_collected, projection_documents
    )

    per_identity: dict[str, Any] = {}
    for predicate in RELATIONSHIP_PREDICATES:
        per_identity[predicate] = {
            "kind": "relationship",
            "classification": compared[predicate]["classification"],
            "subject_count": compared[predicate]["subject_count"],
            "mismatch_count": compared[predicate]["mismatch_count"],
        }
        if predicate in oe.K_PAIR and k_evidence["classification"] != "EQUIVALENT":
            per_identity[predicate]["classification"] = "BLOCKING_MISMATCH"
    for name, entry in classes["identities"].items():
        per_identity[name] = {
            "kind": "class",
            "classification": entry["classification"],
        }
    grounding_blocked = verification_case_grounding.get("result") != "EQUIVALENT"
    if grounding_blocked:
        per_identity["VerificationCase"]["grounding"] = str(
            verification_case_grounding.get("result")
        )

    classifications = [entry["classification"] for entry in per_identity.values()]
    overall = "EQUIVALENT"
    if manifest_errors or "BLOCKING_MISMATCH" in classifications:
        overall = "BLOCKING_MISMATCH"
    elif grounding_blocked:
        overall = "NOT_YET_COMPARABLE"
    if "NOT_YET_COMPARABLE" in classifications and overall == "EQUIVALENT":
        overall = "NOT_YET_COMPARABLE"

    report = {
        "schema": RUNTIME_EQUIVALENCE_REPORT_SCHEMA,
        "bundle_id": str(bundle.get("bundle_id") or ""),
        "git_revision": git_revision,
        "binding_sha256": binding_sha256,
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "import_closure_digest": import_closure_digest,
        "runtime_build": runtime_build["id"],
        "authority_ids": {
            "old": str(getattr(old_service, "semantic_authority_id", "")),
            "new": str(getattr(new_service, "semantic_authority_id", "")),
        },
        "subject_coverage": {
            predicate: {
                "selection": "complete witness-derived eligible population",
                "count": compared[predicate]["subject_count"],
            }
            for predicate in RELATIONSHIP_PREDICATES
        },
        "manifests": manifests,
        "manifest_validation": {
            "classification": "EQUIVALENT" if not manifest_errors else "BLOCKING_MISMATCH",
            "errors": manifest_errors,
        },
        "per_identity": per_identity,
        "k_pair": k_evidence,
        "verification_case_grounding": verification_case_grounding,
        "support_preservation": support,
        "overall": overall,
        "diagnostics": [],
        "generated_at": generated_at,
    }
    if k_evidence.get("drift_from_readiness_baseline"):
        report["diagnostics"].append(
            "k-population-drift-vs-readiness-baseline: the same-revision "
            "witness population differs from the reviewed O2.3 baseline "
            "count; review the change explicitly"
        )
    return report


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------


def _load_elements(api_url: str, binding: Any) -> list[dict[str, Any]]:
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository

    repository = SysMLRepository(ApiClient(api_url, timeout=1800.0))
    return repository.list_elements(binding.sysml_project_id, binding.sysml_commit_id)


def _binding_sha256(binding_path: Path) -> str:
    return "sha256:" + hashlib.sha256(binding_path.read_bytes()).hexdigest()


def _require_exact_revision(requested: str, root: Path) -> str:
    head = _git_head(root)
    if requested != head:
        raise SystemExit(
            f"requested revision {requested!r} does not match the checked-out "
            f"revision {head!r}; exact-revision evidence refuses moving refs"
        )
    return head


def run_bundle(args: argparse.Namespace) -> int:
    """Build the candidate bundle core, run the grounding proof, close it."""
    from de4sdv.sysml_api.revisions import RevisionBinding

    revision = _require_exact_revision(args.git_revision, ROOT)
    binding = RevisionBinding.load(args.binding)
    elements = _load_elements(args.api_url, binding)
    element_sources = None
    if args.element_sources:
        element_sources = json.loads(
            Path(args.element_sources).read_text(encoding="utf-8")
        )
    grounding = prove_verification_case_grounding(
        elements, element_sources=element_sources
    )
    bundle = ob.build_candidate_bundle(ROOT, git_revision=revision)
    export_identity_sha256 = None
    if args.export:
        export_identity_sha256 = "sha256:" + hashlib.sha256(
            Path(args.export).read_bytes()
        ).hexdigest()
    validations = dict(validation.split("=", 1) for validation in args.validation)
    attestation = ob.build_closure_attestation(
        bundle,
        binding=binding,
        binding_sha256=_binding_sha256(args.binding),
        element_count=len(elements),
        export_identity_sha256=export_identity_sha256,
        validations=validations,
        verification_case_grounding=grounding,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    closed = ob.close_bundle(bundle, attestation)
    errors = ob.verify_bundle_document(
        closed,
        root=ROOT,
        binding=binding,
        binding_sha256=_binding_sha256(args.binding),
        require_closed=True,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "de4sdv-o3-candidate-bundle.json").write_text(
        ob.canonical_json(closed), encoding="utf-8"
    )
    (output_dir / "de4sdv-o3-api-closure-attestation.json").write_text(
        ob.canonical_json(attestation), encoding="utf-8"
    )
    (output_dir / "de4sdv-o3-verification-case-grounding.json").write_text(
        ob.canonical_json(grounding), encoding="utf-8"
    )
    print(f"bundle id: {closed['bundle_id']}")
    print(f"git revision: {revision}")
    print(f"grounding proof: {grounding['result']}")
    print(f"closure verification errors: {errors or 'none'}")
    return 1 if errors else 0


def run_compare(args: argparse.Namespace) -> int:
    """Same-revision old-vs-new runtime equivalence comparison."""
    from de4sdv.sysml_api.revisions import RevisionBinding
    from de4sdv.semantic.runtime import build_semantic_runtime

    revision = _require_exact_revision(args.git_revision, ROOT)
    binding = RevisionBinding.load(args.binding)
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    binding_digest = _binding_sha256(args.binding)
    common = dict(
        api_url=args.api_url,
        binding_path=args.binding,
        expected_git_revision=revision,
        ontology_path=args.ontology,
    )
    old_service = build_semantic_runtime(**common)
    new_service = build_semantic_runtime(**common, semantic_authority=bundle)
    elements = _load_elements(args.api_url, binding)
    grounding = prove_verification_case_grounding(
        elements,
        element_sources=(
            json.loads(Path(args.element_sources).read_text(encoding="utf-8"))
            if args.element_sources
            else None
        ),
    )
    import_closure_digest = ob.compute_import_closure_digest(
        git_revision=revision,
        binding_sha256=binding_digest,
        sysml_project_id=str(binding.sysml_project_id),
        sysml_commit_id=str(binding.sysml_commit_id),
        element_count=len(elements),
        export_identity_sha256=None,
    )
    report = build_runtime_equivalence_report(
        old_service,
        new_service,
        root=ROOT,
        bundle=bundle,
        binding=binding,
        binding_sha256=binding_digest,
        import_closure_digest=import_closure_digest,
        git_revision=revision,
        verification_case_grounding=grounding,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(ob.canonical_json(report), encoding="utf-8")
    print(f"overall: {report['overall']}")
    print(f"bundle id: {report['bundle_id']}")
    for name, entry in sorted(report["per_identity"].items()):
        print(f"  {name}: {entry['classification']}")
    if report["diagnostics"]:
        for diagnostic in report["diagnostics"]:
            print(f"  diagnostic: {diagnostic}")
    return 1 if report["overall"] == "BLOCKING_MISMATCH" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    bundle_parser = subparsers.add_parser(
        "bundle", help="build + close the candidate bundle for the checkout"
    )
    bundle_parser.add_argument("--api-url", required=True)
    bundle_parser.add_argument("--binding", required=True, type=Path)
    bundle_parser.add_argument("--git-revision", required=True)
    bundle_parser.add_argument("--output-dir", required=True)
    bundle_parser.add_argument("--element-sources", default=None)
    bundle_parser.add_argument("--export", default=None)
    bundle_parser.add_argument("--validation", action="append", default=[])

    compare_parser = subparsers.add_parser(
        "compare", help="same-revision old-vs-new runtime equivalence report"
    )
    compare_parser.add_argument("--api-url", required=True)
    compare_parser.add_argument("--binding", required=True, type=Path)
    compare_parser.add_argument("--ontology", required=True, type=Path)
    compare_parser.add_argument("--git-revision", required=True)
    compare_parser.add_argument("--bundle", required=True)
    compare_parser.add_argument("--output", required=True)
    compare_parser.add_argument("--element-sources", default=None)

    args = parser.parse_args(argv)
    if args.mode == "bundle":
        return run_bundle(args)
    return run_compare(args)


if __name__ == "__main__":
    raise SystemExit(main())


