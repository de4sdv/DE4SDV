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
and a real VerificationCase, and the validator's native-subject selection
must accept exactly that membership fact.

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
    elements and fails closed without a native membership anchor."""
    service, repository, contract, traversal = integration_service
    subject = _select_native_verification_subject(repository.elements, traversal)
    assert subject["sysml_type"] == "RequirementUsage"
    # The selected subject must be the root requirement that the runtime's
    # own impact surface proves verifiedBy from.
    assert subject["element_id"] == "req-1"

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
