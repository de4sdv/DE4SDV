"""Tests for native-shape traversal: subject membership and verify relationships.

Shapes are derived from the official SysML v2 2025-02-01 API schema, not from
the PR #171 fixture approximations:
- ``SubjectMembership`` owned by a RequirementUsage with ``memberElement`` ->
  subject part;
- ``RequirementVerificationMembership`` with ``verifiedRequirement`` ->
  evidence contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator

import pytest


ROOT = Path(__file__).resolve().parents[1]


class _ApiHandler(BaseHTTPRequestHandler):
    response_map: dict[str, tuple[int, object, dict[str, str]]] = {}

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        status, payload, headers = self.response_map[self.path]
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@pytest.fixture
def api_server_fixture() -> Iterator[tuple[str, type[_ApiHandler]]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ApiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}", _ApiHandler
    finally:
        server.shutdown()
        thread.join()
        _ApiHandler.response_map = {}


def _contract():
    from de4sdv.semantic.kernel_contract import KernelContract

    return KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )


def test_ontology_declares_native_subject_membership_strategy() -> None:
    mapping = _contract().relationship_mapping("hasSubject")
    assert mapping.strategy == "subject-membership"
    assert mapping.semantic_strength == "native-reference"
    assert mapping.configuration["membership_types"] == ["SubjectMembership"]
    assert mapping.configuration["member_property"] == "memberElement"
    assert mapping.configuration["owner_types"] == ["RequirementUsage"]


def test_ontology_declares_native_verification_membership_strategy() -> None:
    mapping = _contract().relationship_mapping("verifiedBy")
    assert mapping.strategy == "verification-membership"
    assert mapping.semantic_strength == "native-verification"
    assert mapping.configuration["membership_types"] == [
        "RequirementVerificationMembership"
    ]
    assert mapping.configuration["element_types"] == [
        "VerificationCaseUsage",
        "VerificationCaseDefinition",
    ]
    assert mapping.configuration["reference_property"] == "verifiedRequirement"
    assert mapping.configuration["direction"] == "reverse"


def test_subject_membership_traversal_resolves_native_api_shape() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    requirement = {
        "@id": "req-1",
        "@type": "RequirementUsage",
        "declaredName": "reqCommandEmergencyBraking",
    }
    subject_part = {
        "@id": "member-1",
        "@type": "PartUsage",
        "declaredName": "memberProduct",
    }
    subject_membership = {
        "@id": "sm-1",
        "@type": "SubjectMembership",
        "owningRelatedElement": {"@id": "req-1"},
        "memberElement": {"@id": "member-1"},
    }
    hops = SemanticTraversal(_contract()).traverse(
        "hasSubject", requirement, [requirement, subject_part, subject_membership]
    )
    assert len(hops) == 1
    hop = hops[0]
    assert hop.predicate == "hasSubject"
    assert hop.strategy == "subject-membership"
    assert hop.semantic_strength == "native-reference"
    assert hop.target["@id"] == "member-1"
    assert hop.api_object["@id"] == "sm-1"


def test_verification_membership_traversal_resolves_native_api_shape() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    evidence = {
        "@id": "ev-1",
        "@type": "RequirementUsage",
        "declaredName": "evidenceContract009BFreshOverrideClear",
    }
    verification = {
        "@id": "vc-1",
        "@type": "VerificationCaseUsage",
        "declaredName": "nominalMovingVehicleTargetVerification009B",
    }
    verify_membership = {
        "@id": "rvm-1",
        "@type": "RequirementVerificationMembership",
        "owningRelatedElement": {"@id": "vc-1"},
        "memberElement": {"@id": "ev-1"},
    }
    hops = SemanticTraversal(_contract()).traverse(
        "verifiedBy", evidence, [evidence, verification, verify_membership]
    )
    assert len(hops) >= 1
    hop = next(h for h in hops if h.api_object["@id"] == "rvm-1")
    assert hop.predicate == "verifiedBy"
    assert hop.strategy == "verification-membership"
    assert hop.semantic_strength == "native-verification"
    assert hop.target["@id"] == "vc-1"
    assert hop.api_object["@id"] == "rvm-1"


def _verification_chain_elements() -> tuple[dict, dict, dict]:
    return (
        {
            "@id": "vc-1",
            "@type": "VerificationCaseDefinition",
            "declaredName": "nominalMovingVehicleTargetVerification009B",
        },
        {
            "@id": "objective-1",
            "@type": "RequirementUsage",
            "declaredName": "nominalEvidenceObjective",
        },
        {
            "@id": "om-1",
            "@type": "ObjectiveMembership",
            "owningRelatedElement": {"@id": "vc-1"},
            "memberElement": {"@id": "objective-1"},
        },
    )


def test_verification_traversal_resolves_objective_ownership_chain() -> None:
    """Real imported shape: an RVM anchored under the objective verifies the
    contract; traversal walks the membership owner chain to the case."""
    from de4sdv.semantic.traversal import SemanticTraversal

    evidence = {
        "@id": "ev-1",
        "@type": "RequirementUsage",
        "declaredName": "evidenceContract009BFreshOverrideClear",
    }
    verification, _objective, objective_membership = _verification_chain_elements()
    elements = [
        evidence,
        verification,
        _objective,
        objective_membership,
        {
            "@id": "rvm-obj-1",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": {"@id": "objective-1"},
            "memberElement": {"@id": "ev-1"},
        },
    ]
    hops = SemanticTraversal(_contract()).traverse(
        "verifiedBy", evidence, elements
    )
    assert len(hops) >= 1
    hop = next(h for h in hops if h.target["@id"] == "vc-1")
    assert hop.semantic_strength == "native-verification"


def test_verification_traversal_rejects_containment_without_rvm() -> None:
    """Negative regression: a RequirementUsage structurally owned below a
    VerificationCase with NO RequirementVerificationMembership must yield no
    verifiedBy hop — containment alone is not native verification semantics."""
    from de4sdv.semantic.traversal import SemanticTraversal

    evidence = {
        "@id": "ev-1",
        "@type": "RequirementUsage",
        "declaredName": "someContractOwnedBelowVerification",
    }
    verification, _objective, objective_membership = _verification_chain_elements()
    elements = [
        evidence,
        verification,
        _objective,
        objective_membership,
        {
            "@id": "fm-1",
            "@type": "FeatureMembership",
            "owningRelatedElement": {"@id": "objective-1"},
            "ownedMemberElement": {"@id": "ev-1"},
        },
    ]
    assert SemanticTraversal(_contract()).traverse("verifiedBy", evidence, elements) == []


def test_verification_traversal_resolves_shadow_only_reference_subsetting() -> None:
    """Shadow-only shape: the ownership/RVM path reaches only the shadow
    reference usage; the queried source is the referenced original. The
    ReferenceSubsetting is the only semantic bridge."""
    from de4sdv.semantic.traversal import SemanticTraversal

    declared = {
        "@id": "ev-1",
        "@type": "RequirementUsage",
        "declaredName": "evidenceContract009BFreshOverrideClear",
    }
    verification, _objective, objective_membership = _verification_chain_elements()
    shadow = {
        "@id": "shadow-1",
        "@type": "RequirementUsage",
        "declaredName": "evidenceContract009BFreshOverrideClear",
    }
    elements = [
        declared,
        verification,
        _objective,
        objective_membership,
        {
            "@id": "rvm-obj-1",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": {"@id": "objective-1"},
            "memberElement": {"@id": "shadow-1"},
        },
        shadow,
        {
            "@id": "rs-1",
            "@type": "ReferenceSubsetting",
            "owningRelatedElement": {"@id": "shadow-1"},
            "referencedFeature": {"@id": "ev-1"},
        },
    ]
    hops = SemanticTraversal(_contract()).traverse("verifiedBy", declared, elements)
    assert len(hops) >= 1
    hop = next(h for h in hops if h.target["@id"] == "vc-1")
    assert hop.semantic_strength == "native-verification"


def test_verification_membership_traversal_honors_member_element_form() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    evidence = {
        "@id": "ev-1",
        "@type": "RequirementUsage",
        "declaredName": "evidenceContract009BFreshOverrideClear",
    }
    verification = {
        "@id": "vc-1",
        "@type": "VerificationCaseDefinition",
        "declaredName": "nominalMovingVehicleTargetVerification009B",
    }
    membership = {
        "@id": "rvm-1",
        "@type": "RequirementVerificationMembership",
        "owningRelatedElement": {"@id": "vc-1"},
        "memberElement": {"@id": "ev-1"},
    }
    hops = SemanticTraversal(_contract()).traverse(
        "verifiedBy", evidence, [evidence, verification, membership]
    )
    assert len(hops) >= 1
    hop = next(h for h in hops if h.api_object["@id"] == "rvm-1")
    assert hop.target["@id"] == "vc-1"
    assert hop.api_object["@id"] == "rvm-1"


def test_subject_membership_ignores_memberships_of_other_owners() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    requirement = {"@id": "req-1", "@type": "RequirementUsage"}
    other_part = {"@id": "member-2", "@type": "PartUsage"}
    foreign_membership = {
        "@id": "sm-2",
        "@type": "SubjectMembership",
        "owningRelatedElement": {"@id": "req-other"},
        "memberElement": {"@id": "member-2"},
    }
    hops = SemanticTraversal(_contract()).traverse(
        "hasSubject", requirement, [requirement, other_part, foreign_membership]
    )
    assert hops == []


def test_traversal_still_fails_closed_for_unsupported_strategy() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    from de4sdv.semantic.kernel_contract import RelationshipMapping

    mapping = RelationshipMapping(
        name="synthetic",
        strategy="time-travel",
        semantic_strength="native",
        configuration={},
    )

    class _SyntheticContract:
        def relationship_mapping(self, name):
            return mapping

    synthetic = SemanticTraversal(_SyntheticContract())
    with pytest.raises(ValueError, match="unsupported SysML traversal strategy"):
        synthetic.traverse("synthetic", {"@id": "x"}, [])


def test_external_strategy_returns_no_hops_without_error() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    hops = SemanticTraversal(_contract()).traverse(
        "hasEvidence", {"@id": "evidence-artifact-x"}, []
    )
    assert hops == []


def test_impact_service_reports_native_edges_against_real_shapes(
    api_server_fixture,
) -> None:
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.impact import ImpactService
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository
    from de4sdv.sysml_api.revisions import RevisionBinding

    ref = lambda value: {"@id": value}
    elements = [
        {
            "@id": "kernel-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
        },
        {
            "@id": "req-braking",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        },
        {"@id": "member-product", "@type": "PartUsage", "declaredName": "memberProduct"},
        {
            "@id": "subject-membership",
            "@type": "SubjectMembership",
            "owningRelatedElement": {"@id": "req-braking"},
            "memberElement": {"@id": "member-product"},
        },
        {
            "@id": "ev-override",
            "@type": "RequirementUsage",
            "declaredName": "evidenceContract009BFreshOverrideClear",
        },
        {
            "@id": "dep-override",
            "@type": "Dependency",
            "source": [ref("ev-override")],
            "target": [ref("req-braking")],
        },
        {
            "@id": "verify-009b",
            "@type": "VerificationCaseUsage",
            "declaredName": "nominalMovingVehicleTargetVerification009B",
        },
        {
            "@id": "rvm-override",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": {"@id": "verify-009b"},
            "verifiedRequirement": {"@id": "ev-override"},
        },
    ]
    response_map = {
        "/projects/project-1/commits/commit-1/elements?page[size]=1000": (
            200,
            elements,
            {},
        )
    }
    base_url, handler = api_server_fixture
    handler.response_map = response_map
    repository = SysMLRepository(ApiClient(base_url))
    binding = RevisionBinding.from_dict(
        {
            "git_repository": "de4sdv/DE4SDV",
            "git_commit": "a" * 40,
            "sysml_project_id": "project-1",
            "sysml_commit_id": "commit-1",
            "import_timestamp": "2026-08-31T00:00:00Z",
            "import_tool_version": "test",
            "semantic_validation": "passed",
            "scope": "full-model",
        }
    )
    contract = _contract()
    service = ImpactService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=OntologyApiBinder(
            contract, repository, project_id="project-1", commit_id="commit-1"
        ),
        traversal=SemanticTraversal(contract),
    )
    result = service.impact("reqCommandEmergencyBraking", git_revision="a" * 40)

    predicates = {edge["predicate"] for edge in result["edges"]}
    assert "hasSubject" in predicates
    assert "verifiedBy" in predicates
    categories = {node["category"] for node in result["nodes"]}
    assert "product-line" in categories
    assert "verification" in categories
    gap_categories = {gap["category"] for gap in result["gaps"]}
    assert "product-line" not in gap_categories
    assert "verification" not in gap_categories
    assert "architecture" in gap_categories  # still honest: no allocation exists
