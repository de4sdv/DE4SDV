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
from de4sdv.semantic import verification_grounding as vg  # noqa: E402
from de4sdv.semantic.relationships import build_relationship_graph  # noqa: E402
from de4sdv.sysml_api.errors import IdentityNotFoundError  # noqa: E402
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

#: ``VerificationCase`` is native-grounded. It must NEVER pass through the
#: file-mapped binder (``OntologyApiBinder.bind_class`` rejects native
#: mappings by design); its runtime-equivalence identity consumes the
#: structured standard-library grounding proof instead.
NATIVE_CLASS_IDENTITY = "VerificationCase"

#: The seven file-mapped migrated classes: their runtime identity resolves
#: through the file-mapped kernel binder (declaration + source file +
#: API metaclass + ingestion-validated kernel UUID).
FILE_MAPPED_CLASSES = tuple(
    name for name in CLASS_IDENTITIES if name != NATIVE_CLASS_IDENTITY
)


_CLASSIFICATION_SEVERITY = {
    "EQUIVALENT": 0,
    "UNSUPPORTED_BOTH": 1,
    "NOT_YET_COMPARABLE": 2,
    "INTENTIONAL_MIGRATION_REVIEW_REQUIRED": 3,
    "BLOCKING_MISMATCH": 4,
}


def _worst_classification(*classifications: str) -> str:
    """Severity-ordered merge of comparison classifications."""
    return max(
        classifications, key=lambda value: _CLASSIFICATION_SEVERITY.get(value, 4)
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


def _load_export_grounding(export_path: "Path | None", *, revision: str) -> dict[str, Any]:
    """Prove the VerificationCase grounding from the exact-revision export.

    Fail-closed: the export artifact is required (exporter-resolved anchors +
    split external references); a missing artifact, a missing git_commit, or a
    git_commit that does not match the checked-out revision refuses the proof.
    The predicate itself is the ONE shared reviewed mechanism
    (de4sdv.semantic.verification_grounding).
    """
    if export_path is None or not Path(export_path).is_file():
        raise SystemExit(
            "the export artifact is required for the VerificationCase "
            "grounding proof (--export); the proof is fail-closed without it"
        )
    export = json.loads(Path(export_path).read_text(encoding="utf-8"))
    export_revision = str(export.get("git_commit") or "")
    if not export_revision:
        raise SystemExit(
            "export artifact records no git_commit; exact-revision grounding "
            "evidence is refused"
        )
    if export_revision != revision:
        raise SystemExit(
            f"export git_commit {export_revision!r} does not match the "
            f"checked-out revision {revision!r}"
        )
    return vg.prove_verification_case_grounding(
        elements=export.get("elements") or [],
        external_references=export.get("external_references") or [],
        library_anchors=export.get("library_anchors") or {},
    )


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


def k_subject_population(service, elements: list[dict[str, Any]]) -> list[str]:
    """Query subjects for the K pair: the connected usages at the typed ends
    of every ``ConnectionUsage`` in the corpus.

    Representation/coverage mechanics ONLY: candidate ends are discovered
    through the runtime's own reviewed end-resolution helpers
    (``_connection_end_records`` / ``_connected_usage_id`` — the serialized
    EndFeatureMembership -> end feature -> ReferenceSubsetting -> connected
    usage chain). Role identity (need vs derivedRequirement) is NEVER decided
    here: the runtime traversal types the roles against the governed lineages
    during the sweep, and :func:`k_pair_evidence` proves the reviewed
    five-witness population from the resulting hop witnesses. No connection
    owner ids, no names, no declaration order, no source text.
    """
    traversal = service.traversal
    by_id = {
        candidate: element
        for element in elements
        if (candidate := element_id(element)) is not None
    }
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
                connected, _subsetting_id, _kind = (
                    traversal._connected_usage_id(
                        record["end_element_id"], graph, by_id
                    )
                )
            except (IdentityNotFoundError, ValueError, KeyError):
                continue
            if connected and connected in by_id and connected not in seen:
                seen.add(connected)
                subjects.append(connected)
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
    k_witness: dict[str, Any] | None = None
    if predicate in oe.K_PAIR and hops:
        hop_witness = getattr(hops[0], "witness", None)
        if isinstance(hop_witness, dict):
            k_witness = {
                "connection_id": hop_witness.get("connection_id"),
                "need_end_id": hop_witness.get("need_end_id"),
                "derived_requirement_end_id": hop_witness.get(
                    "derived_requirement_end_id"
                ),
                "role_lineage_provenance": hop_witness.get(
                    "role_lineage_provenance"
                ),
            }
    return {
        "source_revision": str(service.binding.git_commit),
        "sysml_project_id": str(service.binding.sysml_project_id),
        "sysml_commit_id": str(service.binding.sysml_commit_id),
        "predicate": predicate,
        "subject_id": subject_id,
        "direction": f"{mapping.domain} -> {mapping.range}",
        "query_direction": str(mapping.configuration.get("query_direction") or ""),
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
        "k_witness": k_witness,
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
    if predicate in oe.K_PAIR:
        subjects = k_subject_population(service, elements)
    else:
        subjects = subject_population(elements, predicate)
    records: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, str]] = []
    for subject in subjects:
        element = by_id[subject]
        try:
            hops = service.traversal.traverse(predicate, element, elements)
        except IdentityNotFoundError as exc:
            if predicate not in oe.K_PAIR:
                raise
            # Role typing/provenance failure on a governed K end: fail closed
            # (the coverage gate classifies this as insufficient evidence —
            # never as vacuous equality).
            unresolved.append({"subject_id": subject, "error": str(exc)})
            continue
        records[subject] = _result_record(service, predicate, subject, hops)
    return {"subjects": subjects, "records": records, "unresolved": unresolved}


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
    """ONE modeled fact / TWO navigations — with a fail-closed coverage gate.

    The reviewed exact-revision baseline is ``READINESS_BASELINE_K_WITNESS_COUNT``
    governed ``DerivesFromNeed`` connection witnesses. Vacuous or partial
    equality is NEVER semantic-equivalence evidence: insufficient coverage
    classifies ``NOT_YET_COMPARABLE`` (never EQUIVALENT); real old/new or
    forward/inverse disagreements and duplicated modeled facts classify
    ``BLOCKING_MISMATCH``. A zero-vs-zero equality is rejected outright.
    """
    expected = READINESS_BASELINE_K_WITNESS_COUNT
    forward_predicate = "derivedRequirementsOfNeed"
    inverse_predicate = "derivesRequirementFromNeed"

    def _witnesses(collected: dict[str, Any], predicate: str) -> list[str]:
        return sorted(
            {
                witness
                for record in collected[predicate]["records"].values()
                for witness in record["witnesses"]
            }
        )

    def _duplicates(collected: dict[str, Any], predicate: str) -> list[str]:
        per_witness: dict[str, list[str]] = {}
        for subject, record in collected[predicate]["records"].items():
            for witness in record["witnesses"]:
                per_witness.setdefault(witness, []).append(subject)
        return sorted(
            witness for witness, subjects in per_witness.items() if len(subjects) > 1
        )

    errors: list[str] = []
    missing: list[str] = []
    sides: dict[str, dict[str, list[str]]] = {}
    unresolved_counts: dict[str, int] = {}
    for side, collected in (("old", old_collected), ("new", new_collected)):
        forward = _witnesses(collected, forward_predicate)
        inverse = _witnesses(collected, inverse_predicate)
        sides[side] = {"forward": forward, "inverse": inverse}
        unresolved = [
            entry
            for predicate in (forward_predicate, inverse_predicate)
            for entry in collected[predicate].get("unresolved", [])
        ]
        unresolved_counts[side] = len(unresolved)
        for direction, population in (("forward", forward), ("inverse", inverse)):
            if len(population) != expected:
                missing.append(
                    f"{side} {direction} witness population is "
                    f"{len(population)}; the reviewed governed baseline is "
                    f"{expected} authored DerivesFromNeed connection usages"
                )
        # Forward/inverse identity is a hard contradiction only when this
        # side was fully measurable; unresolved ends are insufficiency.
        if not unresolved and forward != inverse:
            errors.append(
                f"{side} forward and inverse navigations do not share the "
                "same witness population (one modeled fact / two navigations "
                "violated)"
            )
        for predicate in (forward_predicate, inverse_predicate):
            duplicates = _duplicates(collected, predicate)
            if duplicates:
                errors.append(
                    f"{side} {predicate} duplicates modeled facts "
                    f"{duplicates}; each fact must appear once per navigation"
                )
        if unresolved:
            missing.append(
                f"{side} has {len(unresolved)} unresolved K subject(s): "
                + "; ".join(
                    f"{entry['subject_id']}: {entry['error']}"
                    for entry in unresolved[:3]
                )
            )
    both_measured = unresolved_counts["old"] == 0 and unresolved_counts["new"] == 0
    if both_measured:
        if sides["old"]["forward"] != sides["new"]["forward"]:
            errors.append("old/new forward witness populations differ")
        if sides["old"]["inverse"] != sides["new"]["inverse"]:
            errors.append("old/new inverse witness populations differ")
    elif (
        sides["old"]["forward"] != sides["new"]["forward"]
        or sides["old"]["inverse"] != sides["new"]["inverse"]
    ):
        missing.append(
            "old/new K witness populations differ while unresolved subjects "
            "remain; coverage is insufficient for a semantic comparison"
        )

    population_complete = not errors and not missing
    if errors:
        classification = "BLOCKING_MISMATCH"
    elif missing:
        classification = "NOT_YET_COMPARABLE"
    else:
        classification = "EQUIVALENT"
    evidence: dict[str, Any] = {
        "classification": classification,
        "expected_witness_population": expected,
        "old_witness_population": sides["old"]["forward"],
        "new_witness_population": sides["new"]["forward"],
        "old_witness_count": len(sides["old"]["forward"]),
        "new_witness_count": len(sides["new"]["forward"]),
        "forward_witness_population": sorted(
            set(sides["old"]["forward"]) | set(sides["new"]["forward"])
        ),
        "inverse_witness_population": sorted(
            set(sides["old"]["inverse"]) | set(sides["new"]["inverse"])
        ),
        "population_complete": population_complete,
        "drift_from_readiness_baseline": not population_complete,
        "errors": errors,
        "missing": missing,
        "reviewed_baseline_statement": None,
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
    return evidence


def compare_class_identities(
    old_service,
    new_service,
    *,
    verification_case_grounding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Class identity resolution under both authority paths.

    Seven file-mapped classes resolve through the file-mapped kernel binder
    and are compared on declaration identity, source file, API metaclass and
    ingestion-validated kernel UUID.

    ``VerificationCase`` is native-grounded and NEVER touches the file-mapped
    binder (``OntologyApiBinder.bind_class`` rejects native mappings by
    design). Its per-identity runtime result consumes the structured
    standard-library grounding proof:

    grounding EQUIVALENT         -> EQUIVALENT
    grounding NOT_YET_COMPARABLE -> NOT_YET_COMPARABLE
    grounding BLOCKING_MISMATCH  -> BLOCKING_MISMATCH
    grounding absent/unknown     -> NOT_YET_COMPARABLE
    """
    results: dict[str, Any] = {}
    classification = "EQUIVALENT"
    for name in FILE_MAPPED_CLASSES:
        old_binding = old_service.binder.bind_class(name)
        new_binding = new_service.binder.bind_class(name)
        old_mapping = old_service.contract.mapping(name)
        new_mapping = new_service.contract.mapping(name)
        entry: dict[str, Any] = {
            "old_element_id": old_binding.sysml.element_id,
            "new_element_id": new_binding.sysml.element_id,
            "old_sysml_type": old_binding.sysml.type,
            "new_sysml_type": new_binding.sysml.type,
            "old_declaration": getattr(old_mapping, "declaration", None),
            "new_declaration": getattr(new_mapping, "declaration", None),
            "old_source_file": getattr(old_mapping, "file", None),
            "new_source_file": getattr(new_mapping, "file", None),
        }
        ok = (
            entry["old_element_id"] == entry["new_element_id"]
            and entry["old_sysml_type"] == entry["new_sysml_type"]
            and entry["old_declaration"] == entry["new_declaration"]
            and entry["old_source_file"] == entry["new_source_file"]
        )
        entry["classification"] = "EQUIVALENT" if ok else "BLOCKING_MISMATCH"
        if not ok:
            classification = _worst_classification(classification, "BLOCKING_MISMATCH")
        results[name] = entry

    grounding = verification_case_grounding or {}
    grounding_result = str(grounding.get("result") or "")
    if grounding_result not in ("EQUIVALENT", "NOT_YET_COMPARABLE", "BLOCKING_MISMATCH"):
        grounding_result = "NOT_YET_COMPARABLE"
    results[NATIVE_CLASS_IDENTITY] = {
        "classification": grounding_result,
        "mechanism": (
            "native construct identity + governed type population "
            "(VerificationCaseDefinition / VerificationCaseUsage) + "
            "exact-revision standard-library grounding proof "
            "(VerificationCases::VerificationCase implied Subclassification; "
            "VerificationCases::verificationCases implied Subsetting); "
            "no file-mapped binder, no manufactured ingestion kernel UUID"
        ),
        "grounding_result": grounding_result,
        "grounding": grounding or None,
    }
    if grounding_result != "EQUIVALENT":
        classification = _worst_classification(classification, grounding_result)
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
    attested_closure = str(
        (bundle.get("api_closure") or {}).get("import_closure_digest") or ""
    )
    if not attested_closure:
        raise ob.O3BundleError(
            "report requires the bundle-attested import/export closure digest"
        )
    if import_closure_digest != attested_closure:
        raise ob.O3BundleError(
            "report import_closure_digest differs from the bundle-attested "
            "closure; exactly ONE closure identity is permitted"
        )
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
    classes = compare_class_identities(
        old_service,
        new_service,
        verification_case_grounding=verification_case_grounding,
    )
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
    for predicate in oe.K_PAIR:
        entry = per_identity[predicate]
        entry["classification"] = _worst_classification(
            entry["classification"], k_evidence["classification"]
        )
        entry["k_coverage"] = {
            "expected_witness_population": k_evidence[
                "expected_witness_population"
            ],
            "old_witness_count": k_evidence["old_witness_count"],
            "new_witness_count": k_evidence["new_witness_count"],
            "population_complete": k_evidence["population_complete"],
        }
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
    if manifest_errors:
        overall = "BLOCKING_MISMATCH"
    elif classifications:
        overall = _worst_classification(*classifications)
    else:
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
        "activation_eligible": (
            bool((bundle.get("api_closure") or {}).get("activation_eligible"))
            and overall == "EQUIVALENT"
            and bool(k_evidence["population_complete"])
        ),
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


def bundle_validation_records(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    """Structured validation evidence records for the closure attestation.

    Each required validation must be exactly ``passed`` AND bound to the
    sha256 of its exact produced output file — raw CLI status text alone can
    never close an executable bundle.
    """
    statuses = dict(item.split("=", 1) for item in args.validation)
    artifacts = dict(item.split("=", 1) for item in args.validation_artifact)
    records: dict[str, dict[str, Any]] = {}
    for name in ob.REQUIRED_VALIDATIONS:
        status = statuses.get(name)
        if status != "passed":
            raise SystemExit(
                f"validation {name} status must be exactly 'passed' "
                f"(got {status!r}); unresolved evidence cannot close an "
                "executable bundle"
            )
        path = artifacts.get(name)
        if not path:
            raise SystemExit(
                f"validation {name} requires --validation-artifact "
                f"{name}=<path> evidence binding"
            )
        artifact_path = Path(path)
        if not artifact_path.is_file():
            raise SystemExit(f"validation {name} evidence artifact is missing: {path}")
        records[name] = {
            "status": "passed",
            "artifact": name,
            "path": str(artifact_path),
            "sha256": ob.sha256_file(artifact_path),
        }
    return records


def resolve_attested_closure(
    bundle: dict[str, Any],
    *,
    binding: Any,
    binding_sha256: str,
    element_count: int,
) -> str:
    """THE one import/export closure identity for the comparison run.

    Independently verifies the bundle-attested closure (digest self-
    reproduction, binding digest, SysML project/commit, git revision, chain
    and runtime identities, strict validation evidence re-verified against
    the produced outputs) and the live element count; returns the attested
    digest. Fails closed on any divergence.
    """
    closure = bundle.get("api_closure") if isinstance(bundle, dict) else None
    if not isinstance(closure, dict):
        raise ob.O3BundleError(
            "runtime comparison requires the bundle-attested API closure"
        )
    artifacts: dict[str, Path] = {}
    records = closure.get("validation")
    if isinstance(records, dict):
        for name in ob.REQUIRED_VALIDATIONS:
            record = records.get(name)
            if isinstance(record, dict) and record.get("path"):
                artifacts[name] = Path(str(record["path"]))
    errors = ob.verify_bundle_document(
        bundle,
        root=ROOT,
        binding=binding,
        binding_sha256=binding_sha256,
        require_closed=True,
        validation_artifacts=artifacts or None,
    )
    if errors:
        raise ob.O3BundleError(
            "bundle-attested closure failed verification: " + "; ".join(errors)
        )
    recorded_count = closure.get("element_count")
    if not isinstance(recorded_count, int) or isinstance(recorded_count, bool):
        raise ob.O3BundleError("bundle closure element count is not an integer")
    if recorded_count != int(element_count):
        raise ob.O3BundleError(
            "bundle closure element count differs from the live validated "
            "boundary; the import/export closure cannot be reproduced"
        )
    return str(closure["import_closure_digest"])


def compare_exit_code(report: dict[str, Any]) -> int:
    """Only a fully EQUIVALENT privileged comparison run is successful.

    NOT_YET_COMPARABLE, INTENTIONAL_MIGRATION_REVIEW_REQUIRED,
    UNSUPPORTED_BOTH and BLOCKING_MISMATCH all fail the privileged evidence
    gate; the structured report is written before exiting either way.
    """
    return 0 if report.get("overall") == "EQUIVALENT" else 2


def bundle_exit_code(*, closure_errors: list[str], grounding_result: str) -> int:
    """Bundle mode exit: a BLOCKING grounding or closure error is non-green.

    A NOT_YET_COMPARABLE grounding may still produce a comparison-capable
    closed bundle (activation_eligible stays false) so the comparison
    machinery can run; the compare step owns final success.
    """
    if closure_errors:
        return 1
    if grounding_result == "BLOCKING_MISMATCH":
        return 2
    return 0


def run_bundle(args: argparse.Namespace) -> int:
    """Build the candidate bundle core, run the grounding proof, close it."""
    from de4sdv.sysml_api.revisions import RevisionBinding

    revision = _require_exact_revision(args.git_revision, ROOT)
    binding = RevisionBinding.load(args.binding)
    elements = _load_elements(args.api_url, binding)
    grounding = _load_export_grounding(args.export, revision=revision)
    bundle = ob.build_candidate_bundle(ROOT, git_revision=revision)
    export_identity_sha256 = None
    if args.export:
        export_identity_sha256 = "sha256:" + hashlib.sha256(
            Path(args.export).read_bytes()
        ).hexdigest()
    validations = bundle_validation_records(args)
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
    validation_artifacts = {
        name: Path(str(record["path"])) for name, record in validations.items()
    }
    errors = ob.verify_bundle_document(
        closed,
        root=ROOT,
        binding=binding,
        binding_sha256=_binding_sha256(args.binding),
        require_closed=True,
        validation_artifacts=validation_artifacts,
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
    print(f"activation_eligible: {attestation['activation_eligible']}")
    print(f"closure verification errors: {errors or 'none'}")
    return bundle_exit_code(
        closure_errors=errors, grounding_result=str(grounding["result"])
    )


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
    grounding = _load_export_grounding(args.export, revision=revision)
    import_closure_digest = resolve_attested_closure(
        bundle,
        binding=binding,
        binding_sha256=binding_digest,
        element_count=len(elements),
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
    print(f"activation_eligible: {report['activation_eligible']}")
    k_pair = report["k_pair"]
    print(
        "k pair: "
        f"{k_pair['classification']} "
        f"(old={k_pair['old_witness_count']} "
        f"new={k_pair['new_witness_count']} "
        f"expected={k_pair['expected_witness_population']} "
        f"complete={k_pair['population_complete']})"
    )
    print(f"bundle id: {report['bundle_id']}")
    for name, entry in sorted(report["per_identity"].items()):
        print(f"  {name}: {entry['classification']}")
    if report["diagnostics"]:
        for diagnostic in report["diagnostics"]:
            print(f"  diagnostic: {diagnostic}")
    return compare_exit_code(report)


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
    bundle_parser.add_argument(
        "--export",
        required=True,
        help=(
            "exact-revision export artifact (elements + library_anchors + "
            "external_references); required for the grounding proof"
        ),
    )
    bundle_parser.add_argument(
        "--validation",
        action="append",
        default=[],
        help="name=status (must be exactly 'passed' for all required validations)",
    )
    bundle_parser.add_argument(
        "--validation-artifact",
        action="append",
        default=[],
        help="name=path of the exact produced validation output (sha256-bound)",
    )

    compare_parser = subparsers.add_parser(
        "compare", help="same-revision old-vs-new runtime equivalence report"
    )
    compare_parser.add_argument("--api-url", required=True)
    compare_parser.add_argument("--binding", required=True, type=Path)
    compare_parser.add_argument("--ontology", required=True, type=Path)
    compare_parser.add_argument("--git-revision", required=True)
    compare_parser.add_argument("--bundle", required=True)
    compare_parser.add_argument("--output", required=True)
    compare_parser.add_argument(
        "--export",
        required=True,
        help="exact-revision export artifact; required for the grounding proof",
    )

    args = parser.parse_args(argv)
    if args.mode == "bundle":
        return run_bundle(args)
    return run_compare(args)


if __name__ == "__main__":
    raise SystemExit(main())


