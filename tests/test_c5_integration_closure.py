"""c5 integration closure: service-to-validator shape contract (R1+R2).

Guards against the recurrence of the contradiction
``unit fixture passes but real service output makes validate_semantic_mcp.py
impossible``: every result shape consumed by the MCP validator's two proofs
is produced here by the REAL ``SemanticQueryService`` (offline fixture
runtime — the same runtime the stdio MCP server wraps), never handcrafted.

Proof A — blocked EvidenceContract state: the service must expose the
governed blocked predicate as unsupported with the reviewed missing-identity
reason, emit zero EvidenceContract edges, and refuse plain "uncovered with
empty explanation" coverage while the range is blocked.

Proof B — native verification: ``verifiedBy`` must remain discoverable from
the root requirement's own ``RequirementVerificationMembership`` (independent
of the blocked EvidenceContract route), with ``native-verification`` strength
and a real VerificationCase; the validator's native-subject selection must
accept exactly that membership fact, must return only subjects with
machine-proven governed DE4SDV Requirement identity (direct
Requirement-lineage grounding or the reviewed ReferenceSubsetting shadow
bridge — c5 R2 verifiedBy-domain consistency review), and must refuse every
ungrounded / wrong-lineage subject. The hasSubject / native-reference
subject surface is asserted on the Proof-A requirement (the retained model
carries member-product subject hops on requirements without native
verification; verified subjects carry none), never on the Proof-B subject.

The same shapes flow through the validator entry point
``validate_semantic_results`` unchanged.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.validate_semantic_mcp import (
    _select_native_verification_subject,
    validate_semantic_results,
)

from test_semantic_mcp import (
    FixtureRepository,
    ontology_identity,
)
from test_semantic_mcp import ref  # noqa: F401  (fixture parity)

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _service_elements() -> list[dict[str, Any]]:
    """The c5-correction fixture population (see test_semantic_mcp.py).

    req-1 is natively verified by rvm-1 anchored directly on it; evidence-1
    is a verified-in-name-only requirement-usage source whose Dependency is a
    blocked-range candidate and must never be emitted.
    """
    return [
        {
            "@id": "kernel-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
            "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
        },
        {
            "@id": "kernel-need",
            "@type": "RequirementDefinition",
            "declaredName": "StakeholderNeedCandidate",
            "qualifiedName": "DE4SDV_MethodContext::StakeholderNeedCandidate",
        },
        {
            "@id": "kernel-derivation",
            "@type": "ConnectionDefinition",
            "declaredName": "DerivesFromNeed",
            "qualifiedName": "DE4SDV_MethodContext::DerivesFromNeed",
        },
        {
            "@id": "kernel-member-product",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
            "qualifiedName": "DE4SDV_ProductLine::ProductLineMemberProduct",
        },
        {
            "@id": "req-1",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
            "qualifiedName": "DE4SDV_AEBSNeedsRequirements::reqCommandEmergencyBraking",
        },
        {
            "@id": "product-1",
            "@type": "PartUsage",
            "declaredName": "memberProduct",
        },
        {
            "@id": "product-1-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("product-1"),
            "type": ref("kernel-member-product"),
            "typedFeature": ref("product-1"),
        },
        {
            "@id": "subject-membership",
            "@type": "SubjectMembership",
            "owningRelatedElement": ref("req-1"),
            "memberElement": ref("product-1"),
        },
        {
            "@id": "evidence-1",
            "@type": "RequirementUsage",
            "declaredName": "evidenceContractNominalBrakingPath",
        },
        {
            "@id": "dependency-1",
            "@type": "Dependency",
            "source": [ref("evidence-1")],
            "target": [ref("req-1")],
        },
        {
            "@id": "verification-1",
            "@type": "VerificationCaseUsage",
            "declaredName": "nominalMovingVehicleTargetVerification",
        },
        {
            "@id": "rvm-1",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": ref("verification-1"),
            "memberElement": ref("req-1"),
        },
        {
            "@id": "req-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("req-1"),
            "type": ref("kernel-requirement"),
            "typedFeature": ref("req-1"),
        },
        # ----- two-subject fixture (Proof A / Proof B separation) -----------
        # Requirement A ("req-no-verification"): the blocked-EvidenceContract
        # review subject with NO native verifiedBy membership — the production
        # shape of reqCommandEmergencyBraking on the retained export. The
        # Dependency below gives the blocked range a candidate to (correctly)
        # refuse. Requirement B ("req-verified-2") is the independent
        # native-verification subject with its own RVM and case.
        {
            "@id": "req-a",
            "@type": "RequirementUsage",
            "declaredName": "reqNoNativeVerification",
        },
        {
            "@id": "req-a-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("req-a"),
            "type": ref("kernel-requirement"),
            "typedFeature": ref("req-a"),
        },
        # Requirement A carries its member-product subject surface (the
        # retained braking requirement does: reqCommandEmergencyBraking ->
        # its member-product subject). The Proof-A surface assertion
        # (hasSubject + native-reference) lives here, never on Proof B.
        {
            "@id": "product-a",
            "@type": "PartUsage",
            "declaredName": "memberProductForReqA",
        },
        {
            "@id": "product-a-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("product-a"),
            "type": ref("kernel-member-product"),
            "typedFeature": ref("product-a"),
        },
        {
            "@id": "subject-membership-a",
            "@type": "SubjectMembership",
            "owningRelatedElement": ref("req-a"),
            "memberElement": ref("product-a"),
        },
        {
            "@id": "evidence-a",
            "@type": "RequirementUsage",
            "declaredName": "evidenceContractForReqA",
        },
        {
            "@id": "dependency-a",
            "@type": "Dependency",
            "source": [ref("evidence-a")],
            "target": [ref("req-a")],
        },
        {
            "@id": "req-b",
            "@type": "RequirementUsage",
            "declaredName": "reqVerifiedTwo",
        },
        {
            "@id": "req-b-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("req-b"),
            "type": ref("kernel-requirement"),
            "typedFeature": ref("req-b"),
        },
        {
            "@id": "verification-b",
            "@type": "VerificationCaseUsage",
            "declaredName": "subjectBVerification",
        },
        {
            "@id": "rvm-b",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": ref("verification-b"),
            "memberElement": ref("req-b"),
        },
    ]


def _kernel_bindings() -> list[dict[str, str]]:
    return [
        {
            "ontology_class": "Requirement",
            "element_id": "kernel-requirement",
            "source_file": (
                "textual-notation-of-model/packages/methods/de4sdv/"
                "de4sdv_method_context.sysml"
            ),
            "declaration": "requirement def RequirementCandidate",
        },
        {
            "ontology_class": "Need",
            "element_id": "kernel-need",
            "source_file": (
                "textual-notation-of-model/packages/methods/de4sdv/"
                "de4sdv_method_context.sysml"
            ),
            "declaration": "requirement def StakeholderNeedCandidate",
        },
        {
            "ontology_class": "DerivesFromNeed",
            "element_id": "kernel-derivation",
            "source_file": (
                "textual-notation-of-model/packages/methods/de4sdv/"
                "de4sdv_method_context.sysml"
            ),
            "declaration": "connection def DerivesFromNeed",
        },
        {
            "ontology_class": "MemberProduct",
            "element_id": "kernel-member-product",
            "source_file": (
                "textual-notation-of-model/packages/methods/de4sdv/"
                "de4sdv_product_line.sysml"
            ),
            "declaration": "part def ProductLineMemberProduct",
        },
    ]


@pytest.fixture
def integration_service():
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.impact import ImpactService
    from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.query import SemanticQueryService
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.revisions import RevisionBinding

    elements = _service_elements()
    repository = FixtureRepository(elements)
    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    binding = RevisionBinding.from_dict(
        {
            "git_repository": "de4sdv/DE4SDV",
            "git_commit": "a" * 40,
            "sysml_project_id": "project-1",
            "sysml_commit_id": "commit-1",
            "import_timestamp": "2026-09-01T00:00:00Z",
            "import_tool_version": "fixture/1",
            "semantic_validation": "passed",
            "scope": "full-model",
            "ontology": ontology_identity(),
            "kernel_bindings": _kernel_bindings(),
        }
    )
    kernel_index = KernelBindingIndex.from_binding(binding)
    binder = OntologyApiBinder(
        contract,
        repository,  # type: ignore[arg-type]
        project_id="project-1",
        commit_id="commit-1",
        kernel_bindings=kernel_index,
    )
    traversal = SemanticTraversal(contract, kernel_bindings=kernel_index)
    impact = ImpactService(
        repository=repository,  # type: ignore[arg-type]
        binding=binding,
        contract=contract,
        binder=binder,
        traversal=traversal,
    )
    service = SemanticQueryService(
        repository=repository,  # type: ignore[arg-type]
        binding=binding,
        contract=contract,
        binder=binder,
        traversal=traversal,
        impact_service=impact,
        expected_git_revision="a" * 40,
    )
    return service, repository, contract, traversal


def _expected_revision() -> dict[str, Any]:
    return {
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "binding_status": "synchronized",
        "scope": "full-model",
        "ontology": ontology_identity(),
    }


def test_real_service_output_passes_the_corrected_validator(
    integration_service,
) -> None:
    """The exact shapes the runtime produces satisfy validate_semantic_results."""
    service, repository, contract, traversal = integration_service
    elements = repository.elements

    model_status = service.model_status()
    resolve_element = service.resolve_element("reqCommandEmergencyBraking")
    root_id = resolve_element["element"]["element_id"]
    inspect_element = service.inspect_element(root_id)
    neighbors = service.semantic_neighbors(root_id)
    impact = service.impact("reqCommandEmergencyBraking")
    coverage = service.verification_coverage(root_id)
    case_ids = sorted(
        edge["target"]
        for edge in impact["edges"]
        if edge["predicate"] == "verifiedBy"
    )
    assert case_ids, "runtime produced no native verification case"
    trace = service.trace(root_id, case_ids[0], max_depth=4)

    results = {
        "model_status": model_status,
        "resolve_element": resolve_element,
        "inspect_element": inspect_element,
        "semantic_neighbors": neighbors,
        "impact": impact,
        "trace": trace,
        "verification_coverage": coverage,
    }
    validate_semantic_results(results, expected_revision=_expected_revision())


def test_blocked_predicate_is_unsupported_not_ordinary_absence(
    integration_service,
) -> None:
    service, _, _, _ = integration_service
    neighbors = service.semantic_neighbors("req-1")
    assert neighbors["semantic_status"] == "incomplete"
    blocked = [
        record
        for record in neighbors["unsupported_predicates"]
        if record["predicate"] == "hasRelevantEvidenceContract"
    ]
    assert len(blocked) == 1
    assert blocked[0]["authority_state"] == "blocked"
    assert "EvidenceContract-specific identity is not machine-resolvable" in (
        blocked[0]["reason"]
    )
    # Mixed outcome: supported predicates are still evaluated normally.
    assert {
        edge["predicate"] for edge in neighbors["edges"]
    } >= {"hasSubject", "verifiedBy"}
    assert all(
        gap["category"] != "hasRelevantEvidenceContract" for gap in neighbors["gaps"]
    )
    # Zero false EvidenceContract edges.
    assert not any(
        edge["predicate"] == "hasRelevantEvidenceContract"
        for edge in neighbors["edges"]
    )


def test_supported_predicate_zero_matches_remains_ordinary_absence(
    integration_service,
) -> None:
    """A supported predicate with no qualifying fact keeps ordinary absence
    behavior: an ordinary gap, no unsupported record (blocked != absent)."""
    service, _, _, _ = integration_service
    neighbors = service.semantic_neighbors(
        "req-1", predicates=["hasRelevantArchitecture"]
    )
    assert neighbors["semantic_status"] == "complete"
    assert neighbors["unsupported_predicates"] == []
    assert neighbors["edges"] == []
    assert [gap["category"] for gap in neighbors["gaps"]] == [
        "hasRelevantArchitecture"
    ]


def test_coverage_never_plain_uncovered_while_blocked(integration_service) -> None:
    service, _, _, _ = integration_service
    coverage = service.verification_coverage("req-1")
    assert coverage["status"] in {"incomplete", "partial"}
    assert coverage["semantic_status"] == "incomplete"
    assert [
        record["predicate"] for record in coverage["unsupported_predicates"]
    ] == ["hasRelevantEvidenceContract"]
    assert any(
        gap["category"] == "verification-unsupported" for gap in coverage["gaps"]
    )
    assert coverage["evidence_contracts"] == []


def test_native_verification_remains_independently_queryable(
    integration_service,
) -> None:
    service, repository, contract, traversal = integration_service
    impact = service.impact("reqCommandEmergencyBraking")
    verification_edges = [
        edge for edge in impact["edges"] if edge["predicate"] == "verifiedBy"
    ]
    assert verification_edges
    assert all(
        edge["semantic_strength"] == "native-verification"
        for edge in verification_edges
    )
    assert all(edge["target"] == "verification-1" for edge in verification_edges)
    coverage = service.verification_coverage("req-1")
    assert [
        case["element_id"] for case in coverage["verification_cases"]
    ] == ["verification-1"]


def test_native_subject_selection_accepts_membership_fact_and_fails_closed(
    integration_service,
) -> None:
    """The validator's Proof-B subject selection works on the runtime's own
    elements: it returns the subject only with its machine-proven governed
    Requirement identity recorded, and fails closed without a native
    membership anchor."""
    service, repository, contract, traversal = integration_service
    subject = _select_native_verification_subject(repository.elements, traversal)
    assert subject["sysml_type"] == "RequirementUsage"
    # The selected subject must be the root requirement that the runtime's
    # own impact surface proves verifiedBy from.
    assert subject["element_id"] == "req-1"
    # The declared verifiedBy source domain is asserted explicitly: the
    # selected subject carries machine-proven governed Requirement identity
    # and the identity record names the validated lineage root.
    identity = subject["requirement_identity"]
    assert identity["basis"] == "direct-requirement-lineage"
    assert identity["grounding_provenance"] == "explicit"
    assert identity["requirement_lineage_root_id"] == "kernel-requirement"
    assert identity["rvm_anchor_id"] == "req-1"

    # Remove the RVM: selection must fail closed (no name-based fallback).
    stripped = [
        element
        for element in repository.elements
        if element.get("@type") != "RequirementVerificationMembership"
    ]
    with pytest.raises(RuntimeError, match="native RequirementVerificationMembership"):
        _select_native_verification_subject(stripped, traversal)


def test_validator_rejects_service_output_that_loses_the_blocked_state(
    integration_service,
) -> None:
    """A degraded runtime (blocked state dropped from neighbors) cannot pass:
    the validator fails closed on exactly the real output shape."""
    service, repository, contract, traversal = integration_service
    neighbors = service.semantic_neighbors("req-1")
    impact = service.impact("reqCommandEmergencyBraking")
    coverage = service.verification_coverage("req-1")

    degraded = json.loads(
        json.dumps(
            {
                "model_status": service.model_status(),
                "resolve_element": service.resolve_element("req-1"),
                "inspect_element": service.inspect_element("req-1"),
                "semantic_neighbors": neighbors,
                "impact": impact,
                "trace": {
                    "revision": impact["revision"],
                    "path": [{"predicate": "verifiedBy"}],
                    "gaps": [],
                },
                "verification_coverage": coverage,
            }
        )
    )
    degraded["semantic_neighbors"]["unsupported_predicates"] = []
    with pytest.raises(RuntimeError, match="blocked"):
        validate_semantic_results(degraded, expected_revision=_expected_revision())


# ---------------------------------------------------------------------------
# Two-subject Proof-A / Proof-B separation (integration-closure correction)
# ---------------------------------------------------------------------------


def _run_two_subject_validation(service, repository, traversal):
    """Mirror of run_mcp_validation() over the real service (offline).

    Proof A: req-a — the blocked-EvidenceContract review subject with NO
    native verifiedBy. Proof B: the independently selected
    RequirementVerificationMembership subject (req-b). Same selection and
    validation logic as the production validator.
    """
    from scripts.validate_semantic_mcp import _select_native_verification_subject

    proof_a_root = service.resolve_element("reqNoNativeVerification")[
        "element"
    ]["element_id"]
    proof_a_neighbors = service.semantic_neighbors(proof_a_root)
    proof_a_coverage = service.verification_coverage(proof_a_root)

    subject = _select_native_verification_subject(repository.elements, traversal)
    subject_id = subject["element_id"]
    proof_b_impact = service.impact(subject_id)
    case_ids = sorted(
        edge["target"]
        for edge in proof_b_impact["edges"]
        if edge["predicate"] == "verifiedBy"
    )
    assert case_ids, "Proof-B subject produced no native verifiedBy edge"
    proof_b_coverage = service.verification_coverage(subject_id)
    proof_b_trace = service.trace(subject_id, case_ids[0], max_depth=4)

    surface_results = {
        "model_status": service.model_status(),
        "resolve_element": service.resolve_element("reqNoNativeVerification"),
        "inspect_element": service.inspect_element(proof_a_root),
        "semantic_neighbors": proof_a_neighbors,
        "impact": proof_b_impact,
        "trace": proof_b_trace,
        "verification_coverage": proof_a_coverage,
    }
    return {
        "proof_a_root": proof_a_root,
        "proof_a_neighbors": proof_a_neighbors,
        "proof_a_coverage": proof_a_coverage,
        "subject": subject,
        "subject_id": subject_id,
        "proof_b_impact": proof_b_impact,
        "proof_b_coverage": proof_b_coverage,
        "proof_b_trace": proof_b_trace,
        "case_ids": case_ids,
        "surface_results": surface_results,
    }


def test_two_subject_validation_separates_proof_a_and_proof_b(
    integration_service,
) -> None:
    """Production shape: Requirement A carries the blocked EvidenceContract
    review (and NO native verification); Requirement B independently carries
    the native-verification proof. The validator must pass with the explicit
    Proof-B results, and Proof A / Proof B must use different requirements."""
    service, repository, _, traversal = integration_service
    r = _run_two_subject_validation(service, repository, traversal)

    # Proof A uses Requirement A; A has NO native verifiedBy.
    assert r["proof_a_root"] == "req-a"
    assert r["proof_a_root"] != r["subject_id"]
    impact_a = service.impact(r["proof_a_root"])
    assert not any(
        edge["predicate"] == "verifiedBy" for edge in impact_a["edges"]
    ), "fixture invariant broken: Proof-A subject has native verification"
    # Proof A proves the blocked state on Requirement A.
    assert r["proof_a_neighbors"]["root"]["element_id"] == "req-a"
    assert r["proof_a_coverage"]["requirement"]["element_id"] == "req-a"
    assert [
        record["predicate"]
        for record in r["proof_a_coverage"]["unsupported_predicates"]
    ] == ["hasRelevantEvidenceContract"]

    # Proof B uses Requirement B — one coherent subject across all three.
    assert r["proof_b_impact"]["root"]["element_id"] == r["subject_id"]
    assert r["proof_b_coverage"]["requirement"]["element_id"] == r["subject_id"]
    assert r["proof_b_trace"]["source"]["element_id"] == r["subject_id"]
    # The selected subject carries its machine-proven governed Requirement
    # identity (the declared verifiedBy source domain).
    assert r["subject"]["requirement_identity"]["basis"] == (
        "direct-requirement-lineage"
    )
    assert r["subject"]["requirement_identity"]["requirement_lineage_root_id"] == (
        "kernel-requirement"
    )
    # The coverage/trace/impact chain proves the SAME case.
    assert r["proof_b_coverage"]["verification_cases"][0]["element_id"] in (
        r["case_ids"]
    )
    assert [step["predicate"] for step in r["proof_b_trace"]["path"]] == [
        "verifiedBy"
    ]

    # The validator passes with explicit, aligned Proof-B results.
    validate_semantic_results(
        r["surface_results"],
        expected_revision=_expected_revision(),
        proof_b_impact=r["proof_b_impact"],
        proof_b_coverage=r["proof_b_coverage"],
        proof_b_trace=r["proof_b_trace"],
        proof_b_subject=r["subject"],
    )


def test_validator_rejects_cross_subject_coverage_combination(
    integration_service,
) -> None:
    """Mandatory negative regression: the pre-correction bug shape —
    impact_B + coverage_A + trace_B — must fail validation."""
    service, repository, _, traversal = integration_service
    r = _run_two_subject_validation(service, repository, traversal)

    mixed = json.loads(json.dumps(r["surface_results"]))
    # Simulate the old bug: Proof-B impact/trace kept, but coverage left at
    # the Proof-A subject (coverage_A) instead of coverage_B.
    mixed["verification_coverage"] = json.loads(
        json.dumps(r["proof_a_coverage"])
    )
    with pytest.raises(RuntimeError, match="subject-coherent"):
        validate_semantic_results(
            mixed,
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=mixed["verification_coverage"],
            proof_b_trace=r["proof_b_trace"],
            proof_b_subject=r["subject"],
        )


def test_validator_rejects_unaligned_proof_b_results(
    integration_service,
) -> None:
    """Fail closed on any Proof-B triple whose members disagree about the
    subject — even without the Proof-A comparison."""
    service, repository, _, traversal = integration_service
    r = _run_two_subject_validation(service, repository, traversal)

    # Swap in the Proof-A subject's coverage for the Proof-B coverage.
    with pytest.raises(RuntimeError, match="subject-coherent"):
        validate_semantic_results(
            r["surface_results"],
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=r["proof_a_coverage"],
            proof_b_trace=r["proof_b_trace"],
            proof_b_subject=r["subject"],
        )

    # A Proof-B trace sourced from a different requirement also fails.
    forged_trace = json.loads(json.dumps(r["proof_b_trace"]))
    forged_trace["source"] = {"element_id": "req-a"}
    with pytest.raises(RuntimeError, match="subject-coherent"):
        validate_semantic_results(
            r["surface_results"],
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=r["proof_b_coverage"],
            proof_b_trace=forged_trace,
            proof_b_subject=r["subject"],
        )


# ---------------------------------------------------------------------------
# verifiedBy source-domain enforcement (c5 R2 verifiedBy-domain consistency
# review). Non-vacuous laws: RequirementUsage != Requirement automatically;
# RequirementVerificationMembership != Requirement identity; Need !=
# Requirement; AcceptanceCriterion-role qualifies only when independently a
# Requirement under the reviewed ontology model; unresolved identity fails
# closed; names never steer.
# ---------------------------------------------------------------------------


def _selection_traversal():
    """A traversal with the same kernel bindings the integration fixture uses."""
    from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.revisions import RevisionBinding

    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    binding = RevisionBinding.from_dict(
        {
            "git_repository": "de4sdv/DE4SDV",
            "git_commit": "a" * 40,
            "sysml_project_id": "project-1",
            "sysml_commit_id": "commit-1",
            "import_timestamp": "2026-09-01T00:00:00Z",
            "import_tool_version": "fixture/1",
            "semantic_validation": "passed",
            "scope": "full-model",
            "ontology": ontology_identity(),
            "kernel_bindings": _kernel_bindings(),
        }
    )
    return SemanticTraversal(
        contract, kernel_bindings=KernelBindingIndex.from_binding(binding)
    )


def _kernel_requirement_element() -> dict[str, Any]:
    return {
        "@id": "kernel-requirement",
        "@type": "RequirementDefinition",
        "declaredName": "RequirementCandidate",
        "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
    }


def _rvm_anchored(rvm_id: str, anchor_id: str, case_id: str) -> dict[str, Any]:
    return {
        "@id": rvm_id,
        "@type": "RequirementVerificationMembership",
        "owningRelatedElement": ref(case_id),
        "memberElement": ref(anchor_id),
    }


def _case(case_id: str) -> dict[str, Any]:
    return {
        "@id": case_id,
        "@type": "VerificationCaseUsage",
        "declaredName": case_id,
    }


def test_selection_skips_ungrounded_usage_and_keeps_proven_subject() -> None:
    """RequirementUsage != Requirement automatically, and names never steer:
    an ungrounded usage with a requirement-looking name (earlier in export
    order) is skipped; the Requirement-grounded subject is selected."""
    traversal = _selection_traversal()
    elements = [
        _kernel_requirement_element(),
        # Ungrounded, misleadingly named, earlier in export order.
        {
            "@id": "req-looks-grounded",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        },
        _case("verification-u"),
        _rvm_anchored("rvm-u", "req-looks-grounded", "verification-u"),
        # Grounded, plainly named, later in export order.
        {
            "@id": "designInputTwo",
            "@type": "RequirementUsage",
            "declaredName": "designInputTwo",
        },
        {
            "@id": "designInputTwo-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("designInputTwo"),
            "type": ref("kernel-requirement"),
            "typedFeature": ref("designInputTwo"),
        },
        _case("verification-p"),
        _rvm_anchored("rvm-p", "designInputTwo", "verification-p"),
    ]
    subject = _select_native_verification_subject(elements, traversal)
    assert subject["element_id"] == "designInputTwo"
    assert subject["verification_case_id"] == "verification-p"
    assert subject["requirement_identity"]["basis"] == (
        "direct-requirement-lineage"
    )
    assert subject["requirement_identity"]["rvm_anchor_id"] == "designInputTwo"

    # Renaming the proven subject does not change the selection (no names).
    renamed = json.loads(json.dumps(elements))
    for element in renamed:
        if element.get("@id") == "designInputTwo":
            element["declaredName"] = "completelyUnrelatedName"
    again = _select_native_verification_subject(renamed, traversal)
    assert again["element_id"] == "designInputTwo"


def test_selection_rejects_ungrounded_requirement_usage() -> None:
    """A bare API RequirementUsage with an RVM anchor is not a Requirement:
    unresolved identity fails closed, even with a requirement-looking name."""
    traversal = _selection_traversal()
    elements = [
        _kernel_requirement_element(),
        {
            "@id": "req-unresolved",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        },
        _case("verification-x"),
        _rvm_anchored("rvm-x", "req-unresolved", "verification-x"),
    ]
    with pytest.raises(RuntimeError, match="governed DE4SDV Requirement"):
        _select_native_verification_subject(elements, traversal)


def test_selection_rejects_need_role_usage() -> None:
    """Need != Requirement: a stakeholder-need candidate usage (sibling
    lineage, also serialized as RequirementUsage) never qualifies, even
    though it is natively verified."""
    traversal = _selection_traversal()
    elements = [
        _kernel_requirement_element(),
        {
            "@id": "kernel-need",
            "@type": "RequirementDefinition",
            "declaredName": "StakeholderNeedCandidate",
            "qualifiedName": "DE4SDV_MethodContext::StakeholderNeedCandidate",
        },
        {
            "@id": "need-one",
            "@type": "RequirementUsage",
            "declaredName": "needCommandEmergencyBraking",
        },
        {
            "@id": "need-one-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("need-one"),
            "type": ref("kernel-need"),
            "typedFeature": ref("need-one"),
        },
        _case("verification-n"),
        _rvm_anchored("rvm-n", "need-one", "verification-n"),
    ]
    with pytest.raises(RuntimeError, match="governed DE4SDV Requirement"):
        _select_native_verification_subject(elements, traversal)


def test_selection_acceptance_criterion_role_requires_requirement_lineage() -> None:
    """AcceptanceCriterion != Requirement automatically: an
    acceptance-criterion-role usage qualifies only when it independently
    grounds in the reviewed Requirement lineage (through the validated
    classification chain); a same-shaped usage outside that lineage fails
    closed."""
    traversal = _selection_traversal()

    def elements_for(definition_id: str, *, chained: bool) -> list[dict[str, Any]]:
        elements = [
            _kernel_requirement_element(),
            {
                "@id": definition_id,
                "@type": "RequirementDefinition",
                "declaredName": definition_id,
            },
            {
                "@id": "ac-one",
                "@type": "RequirementUsage",
                "declaredName": "acceptanceCriterionOne",
            },
            {
                "@id": "ac-one-typing",
                "@type": "FeatureTyping",
                "owningRelatedElement": ref("ac-one"),
                "type": ref(definition_id),
                "typedFeature": ref("ac-one"),
            },
            _case("verification-ac"),
            _rvm_anchored("rvm-ac", "ac-one", "verification-ac"),
        ]
        if chained:
            elements.append(
                {
                    "@id": "ac-def-subclassification",
                    "@type": "Subclassification",
                    "subclassifier": ref(definition_id),
                    "superclassifier": ref("kernel-requirement"),
                }
            )
        return elements

    # In the Requirement lineage through the classification chain: allowed.
    subject = _select_native_verification_subject(
        elements_for("acceptanceCriterionRoot", chained=True), traversal
    )
    assert subject["element_id"] == "ac-one"
    assert subject["requirement_identity"]["basis"] == (
        "direct-requirement-lineage"
    )

    # Same role shape, no Requirement grounding: fail closed.
    with pytest.raises(RuntimeError, match="governed DE4SDV Requirement"):
        _select_native_verification_subject(
            elements_for("outsideLineageCriterionRoot", chained=False), traversal
        )


def test_selection_resolves_reviewed_shadow_bridge() -> None:
    """The reviewed ReferenceSubsetting bridge (c2 Section 2.2) is the second
    reviewed discriminator: an RVM anchored on a serialized shadow returns
    the DECLARED usage as the proven subject; a shadow whose declared usage
    is ungrounded fails closed."""
    traversal = _selection_traversal()
    elements = [
        _kernel_requirement_element(),
        {
            "@id": "declared-one",
            "@type": "RequirementUsage",
            "declaredName": "acceptanceCriterionEvidenceIntegrity",
        },
        {
            "@id": "declared-one-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("declared-one"),
            "type": ref("kernel-requirement"),
            "typedFeature": ref("declared-one"),
        },
        # Serialized shadow reference usage anchored by the RVM.
        {
            "@id": "shadow-one",
            "@type": "RequirementUsage",
            "declaredName": None,
        },
        {
            "@id": "refsub-one",
            "@type": "ReferenceSubsetting",
            "owningRelatedElement": ref("shadow-one"),
            "referencedFeature": ref("declared-one"),
        },
        _case("verification-s"),
        _rvm_anchored("rvm-s", "shadow-one", "verification-s"),
    ]
    subject = _select_native_verification_subject(elements, traversal)
    # The PROVEN subject is the declared usage; the shadow only anchors.
    assert subject["element_id"] == "declared-one"
    assert subject["verification_case_id"] == "verification-s"
    identity = subject["requirement_identity"]
    assert identity["basis"] == "reference-subsetting-shadow"
    assert identity["grounding_provenance"] == "explicit"
    assert identity["rvm_anchor_id"] == "shadow-one"

    # Same shadow shape, declared usage ungrounded: fail closed.
    ungrounded = json.loads(json.dumps(elements))
    ungrounded = [
        element
        for element in ungrounded
        if element.get("@id") != "declared-one-typing"
    ]
    with pytest.raises(RuntimeError, match="governed DE4SDV Requirement"):
        _select_native_verification_subject(ungrounded, traversal)


def test_validator_requires_proof_b_subject_identity(integration_service) -> None:
    """Proof-B subject selection cannot bypass domain enforcement: the
    validated proof asserts the machine-proven Requirement identity of the
    selected subject whenever the production record is supplied."""
    service, repository, _, traversal = integration_service
    r = _run_two_subject_validation(service, repository, traversal)

    # Valid production shape passes with the identity record.
    validate_semantic_results(
        r["surface_results"],
        expected_revision=_expected_revision(),
        proof_b_impact=r["proof_b_impact"],
        proof_b_coverage=r["proof_b_coverage"],
        proof_b_trace=r["proof_b_trace"],
        proof_b_subject=r["subject"],
    )

    # A record without identity evidence fails closed.
    forged = json.loads(json.dumps(r["subject"]))
    forged.pop("requirement_identity")
    with pytest.raises(RuntimeError, match="source domain"):
        validate_semantic_results(
            r["surface_results"],
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=r["proof_b_coverage"],
            proof_b_trace=r["proof_b_trace"],
            proof_b_subject=forged,
        )

    # An unreviewed identity basis fails closed.
    forged = json.loads(json.dumps(r["subject"]))
    forged["requirement_identity"]["basis"] = "name-match"
    with pytest.raises(RuntimeError, match="reviewed discriminators"):
        validate_semantic_results(
            r["surface_results"],
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=r["proof_b_coverage"],
            proof_b_trace=r["proof_b_trace"],
            proof_b_subject=forged,
        )

    # A subject that is not the proof-triple root fails closed.
    forged = json.loads(json.dumps(r["subject"]))
    forged["element_id"] = "req-a"
    with pytest.raises(RuntimeError, match="does not match the proof triple"):
        validate_semantic_results(
            r["surface_results"],
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=r["proof_b_coverage"],
            proof_b_trace=r["proof_b_trace"],
            proof_b_subject=forged,
        )


def test_proof_a_surface_assertion_is_located_on_proof_a(
    integration_service,
) -> None:
    """The hasSubject / native-reference subject surface is asserted on the
    Proof-A requirement: it must hold there, and it is no longer demanded
    from the Proof-B subject (the retained model carries it only on
    requirements without native verification)."""
    service, repository, _, traversal = integration_service
    r = _run_two_subject_validation(service, repository, traversal)

    # Proof-B impact reduced to its native-verification edges still passes:
    # the subject surface belongs to Proof A.
    stripped_b = json.loads(json.dumps(r["proof_b_impact"]))
    stripped_b["edges"] = [
        edge for edge in stripped_b["edges"] if edge["predicate"] == "verifiedBy"
    ]
    validate_semantic_results(
        r["surface_results"],
        expected_revision=_expected_revision(),
        proof_b_impact=stripped_b,
        proof_b_coverage=r["proof_b_coverage"],
        proof_b_trace=r["proof_b_trace"],
        proof_b_subject=r["subject"],
    )

    # The Proof-A surface must expose hasSubject; removing it fails closed.
    degraded = json.loads(json.dumps(r["surface_results"]))
    degraded["semantic_neighbors"]["edges"] = [
        edge
        for edge in degraded["semantic_neighbors"]["edges"]
        if edge["predicate"] != "hasSubject"
    ]
    with pytest.raises(
        RuntimeError, match="Proof-A surface did not expose hasSubject"
    ):
        validate_semantic_results(
            degraded,
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=r["proof_b_coverage"],
            proof_b_trace=r["proof_b_trace"],
            proof_b_subject=r["subject"],
        )

    # native-reference strength on the Proof-A surface is load-bearing.
    degraded = json.loads(json.dumps(r["surface_results"]))
    for edge in degraded["semantic_neighbors"]["edges"]:
        if edge["predicate"] == "hasSubject":
            edge["semantic_strength"] = "relevance"
    with pytest.raises(RuntimeError, match="lost native-reference strength"):
        validate_semantic_results(
            degraded,
            expected_revision=_expected_revision(),
            proof_b_impact=r["proof_b_impact"],
            proof_b_coverage=r["proof_b_coverage"],
            proof_b_trace=r["proof_b_trace"],
            proof_b_subject=r["subject"],
        )
