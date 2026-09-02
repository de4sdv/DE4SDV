from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

import pytest

ROOT = Path(__file__).resolve().parents[1]


def ontology_identity() -> dict[str, str]:
    from de4sdv.sysml_api.revisions import OntologyIdentity

    return OntologyIdentity.from_file(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
        repository_root=ROOT,
    ).to_dict()


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
        return


@pytest.fixture
def api_server() -> Iterator[tuple[str, type[_ApiHandler]]]:
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


def test_api_client_follows_link_pagination(api_server: tuple[str, type[_ApiHandler]]) -> None:
    from de4sdv.sysml_api.client import ApiClient

    base_url, handler = api_server
    handler.response_map = {
        "/projects?page%5Bafter%5D=first": (
            200,
            [{"@id": "project-1"}],
            {"Link": f'<{base_url}/projects?page%5Bafter%5D=second>; rel="next"'},
        ),
        "/projects?page%5Bafter%5D=second": (200, [{"@id": "project-2"}], {}),
    }

    client = ApiClient(base_url)

    assert client.get_all("/projects?page%5Bafter%5D=first") == [
        {"@id": "project-1"},
        {"@id": "project-2"},
    ]


def test_repository_returns_api_relationship_objects_for_exact_revision(
    api_server: tuple[str, type[_ApiHandler]],
) -> None:
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository

    base_url, handler = api_server
    handler.response_map = {
        "/projects/project-1/commits/commit-1/elements?page[size]=1000": (
            200,
            [
                {"@id": "req-1", "@type": "RequirementUsage", "declaredName": "reqX"},
                {
                    "@id": "dep-1",
                    "@type": "Dependency",
                    "source": [{"@id": "evidence-1"}],
                    "target": [{"@id": "req-1"}],
                },
                {
                    "@id": "verification-1",
                    "@type": "VerificationCaseUsage",
                    "verifiedRequirement": [{"@id": "evidence-1"}],
                },
            ],
            {},
        ),
    }
    repository = SysMLRepository(ApiClient(base_url))

    incoming = repository.relationships(
        "project-1", "commit-1", "req-1", direction="incoming"
    )

    assert [relationship["@id"] for relationship in incoming] == ["dep-1"]
    assert incoming[0]["@type"] == "Dependency"


def test_repository_capability_check_exercises_required_read_contract(
    api_server: tuple[str, type[_ApiHandler]],
) -> None:
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository

    base_url, handler = api_server
    handler.response_map = {
        "/projects/project-1": (200, {"@id": "project-1", "@type": "Project"}, {}),
        "/projects/project-1/commits/commit-1": (
            200,
            {"@id": "commit-1", "@type": "Commit"},
            {},
        ),
        "/projects/project-1/commits/commit-1/elements?page[size]=1000": (
            200,
            [
                {"@id": "req-1", "@type": "RequirementUsage"},
                {"@id": "dep-1", "@type": "Dependency"},
            ],
            {},
        ),
    }

    capabilities = SysMLRepository(ApiClient(base_url)).check_capabilities(
        "project-1", "commit-1"
    )

    assert capabilities == {
        "project_read": True,
        "commit_read": True,
        "element_read": True,
        "semantic_types": ["Dependency", "RequirementUsage"],
    }


def test_revision_binding_refuses_current_baseline_claim_when_git_is_stale() -> None:
    from de4sdv.sysml_api.errors import RevisionMismatchError
    from de4sdv.sysml_api.revisions import RevisionBinding

    binding = RevisionBinding.from_dict(
        {
            "git_repository": "de4sdv/DE4SDV",
            "git_commit": "a" * 40,
            "sysml_project_id": "project-1",
            "sysml_commit_id": "commit-1",
            "import_timestamp": "2026-08-31T00:00:00Z",
            "import_tool_version": "de4sdv-semantic-fixture/1",
            "semantic_validation": "passed",
            "ontology": ontology_identity(),
        }
    )

    assert binding.status("a" * 40) == "synchronized"
    assert binding.status("b" * 40) == "stale"
    with pytest.raises(RevisionMismatchError, match="stale"):
        binding.require_current("b" * 40)


def test_identity_resolution_never_silently_selects_an_ambiguous_name() -> None:
    from de4sdv.sysml_api.errors import AmbiguousIdentityError
    from de4sdv.sysml_api.identity import resolve_identity

    elements = [
        {
            "@id": "req-a",
            "@type": "RequirementUsage",
            "declaredName": "reqX",
            "qualifiedName": "PackageA::reqX",
        },
        {
            "@id": "req-b",
            "@type": "RequirementUsage",
            "declaredName": "reqX",
            "qualifiedName": "PackageB::reqX",
        },
    ]

    resolved = resolve_identity("PackageA::reqX", elements)
    assert resolved.level == "qualified-name-match"
    assert resolved.element["@id"] == "req-a"
    with pytest.raises(AmbiguousIdentityError, match="reqX"):
        resolve_identity("reqX", elements)


def test_ontology_requirement_binds_through_exact_kernel_mapping_to_api_uuid(
    api_server: tuple[str, type[_ApiHandler]],
) -> None:
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository

    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    mapping = contract.class_mapping("Requirement")
    assert mapping.file.endswith("de4sdv_method_context.sysml")
    assert mapping.declaration == "requirement def RequirementCandidate"

    base_url, handler = api_server
    handler.response_map = {
        "/projects/project-1/commits/commit-1/elements?page[size]=1000": (
            200,
            [
                {
                    "@id": "kernel-requirement-uuid",
                    "@type": "RequirementDefinition",
                    "declaredName": "RequirementCandidate",
                    "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
                }
            ],
            {},
        )
    }
    binder = OntologyApiBinder(
        contract,
        SysMLRepository(ApiClient(base_url)),
        project_id="project-1",
        commit_id="commit-1",
    )

    binding = binder.bind_class("Requirement")

    assert binding.sysml.element_id == "kernel-requirement-uuid"
    assert binding.sysml.type == "RequirementDefinition"
    assert binding.kernel.declaration == "requirement def RequirementCandidate"


def test_first_milestone_relationships_define_machine_traversal_strategies() -> None:
    from de4sdv.semantic.kernel_contract import KernelContract

    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )

    assert contract.relationship_mapping("realizedBy").strategy == "allocation"
    assert (
        contract.relationship_mapping("verifiedBy").strategy
        == "verification-membership"
    )
    relevance = contract.relationship_mapping("hasRelevantEvidenceContract")
    assert relevance.strategy == "dependency"
    assert relevance.semantic_strength == "relevance"
    assert (
        contract.relationship_mapping("hasSubject").strategy == "subject-membership"
    )


def test_allocation_strategy_traverses_native_api_relationship_object() -> None:
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.traversal import SemanticTraversal

    requirement = {"@id": "req-1", "@type": "RequirementUsage"}
    architecture = {"@id": "logical-1", "@type": "PartUsage"}
    allocation = {
        "@id": "allocation-1",
        "@type": "AllocationUsage",
        "source": [{"@id": "req-1"}],
        "target": [{"@id": "logical-1"}],
    }
    traversal = SemanticTraversal(
        KernelContract.load(
            ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        )
    )

    hops = traversal.traverse(
        "realizedBy", requirement, [requirement, architecture, allocation]
    )

    assert len(hops) == 1
    assert hops[0].target == architecture
    assert hops[0].api_object == allocation
    assert hops[0].semantic_strength == "allocation"


def test_api_impact_returns_revision_pinned_compact_aebs_subgraph(
    api_server: tuple[str, type[_ApiHandler]],
) -> None:
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.impact import ImpactService
    from de4sdv.semantic.kernel_contract import KernelContract
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
            "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
        },
        {
            "@id": "req-braking",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
            "qualifiedName": "DE4SDV_AEBSNeedsRequirements::reqCommandEmergencyBraking",
        },
        {
            "@id": "subject-membership",
            "@type": "SubjectMembership",
            "owningRelatedElement": {"@id": "req-braking"},
            "memberElement": {"@id": "member-product"},
        },
        {
            "@id": "member-product",
            "@type": "PartUsage",
            "declaredName": "memberProduct",
            "qualifiedName": "DE4SDV_AEBSNeedsRequirements::memberProduct",
        },
        *[
            {
                "@id": evidence_id,
                "@type": "RequirementUsage",
                "declaredName": name,
                "qualifiedName": f"DE4SDV_AEBSEvidence::{name}",
            }
            for evidence_id, name in (
                ("ev-override", "evidenceContractFreshOverrideClear"),
                ("ev-braking", "evidenceContractNominalBrakingPath"),
                ("ev-mrm", "evidenceContractMRMGateChain"),
            )
        ],
        {
            "@id": "dep-override",
            "@type": "Dependency",
            "source": [ref("ev-override")],
            "target": [ref("req-braking")],
        },
        {
            "@id": "dep-braking",
            "@type": "Dependency",
            "source": [ref("ev-braking")],
            "target": [ref("req-braking")],
        },
        {
            "@id": "dep-mrm",
            "@type": "Dependency",
            "source": [ref("ev-mrm")],
            "target": [ref("req-braking")],
        },
        {
            "@id": "verify-009b",
            "@type": "VerificationCaseUsage",
            "declaredName": "nominalMovingVehicleTargetVerification",
        },
        {
            "@id": "rvm-override",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": {"@id": "verify-009b"},
            "verifiedRequirement": {"@id": "ev-override"},
        },
        {
            "@id": "rvm-braking",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": {"@id": "verify-009b"},
            "verifiedRequirement": {"@id": "ev-braking"},
        },
        {
            "@id": "verify-009c",
            "@type": "VerificationCaseUsage",
            "declaredName": "nativeInterventionToMRMVerification",
        },
        {
            "@id": "rvm-mrm",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": {"@id": "verify-009c"},
            "verifiedRequirement": {"@id": "ev-mrm"},
        },
    ]
    base_url, handler = api_server
    handler.response_map = {
        "/projects/project-1/commits/commit-1/elements?page[size]=1000": (200, elements, {})
    }
    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    repository = SysMLRepository(ApiClient(base_url))
    binding = RevisionBinding.from_dict(
        {
            "git_repository": "de4sdv/DE4SDV",
            "git_commit": "a" * 40,
            "sysml_project_id": "project-1",
            "sysml_commit_id": "commit-1",
            "import_timestamp": "2026-08-31T00:00:00Z",
            "import_tool_version": "de4sdv-semantic-fixture/1",
            "semantic_validation": "passed",
            "scope": "AEBS impact pilot",
            "ontology": contract.identity.to_dict(),
        }
    )
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

    assert result["root"]["element_id"] == "req-braking"
    assert result["revision"]["sysml_project_id"] == "project-1"
    assert result["revision"]["sysml_commit_id"] == "commit-1"
    assert result["ontology_bindings"]["Requirement"]["element_id"] == "kernel-requirement"
    assert {node["element_id"] for node in result["nodes"] if node["category"] == "evidence"} == {
        "ev-override",
        "ev-braking",
        "ev-mrm",
    }
    assert {node["element_id"] for node in result["nodes"] if node["category"] == "verification"} == {
        "verify-009b",
        "verify-009c",
    }
    assert {node["element_id"] for node in result["nodes"] if node["category"] == "product-line"} == {
        "member-product"
    }
    assert not [node for node in result["nodes"] if node["category"] == "architecture"]
    assert any(gap["category"] == "architecture" for gap in result["gaps"])
    assert {edge["strategy"] for edge in result["edges"]} >= {
        "dependency",
        "verification-membership",
        "subject-membership",
    }
    assert all(edge["api_object_id"] for edge in result["edges"])
    assert result["provenance"]

    from scripts import query_model_impact as text_backend

    text_report = text_backend.query_impact("reqCommandEmergencyBraking")
    assert {
        node["declared_name"]
        for node in result["nodes"]
        if node["category"] == "evidence"
    } == {edge.source for edge in text_report.edges}
    assert {
        node["declared_name"]
        for node in result["nodes"]
        if node["category"] == "verification"
    } == {edge.verification_usage for edge in text_report.edges}


def test_aebs_api_fixture_reuses_pr36_payload_pattern_for_known_model_slice() -> None:
    from de4sdv.sysml_api.fixture import aebs_impact_fixture

    fixture = aebs_impact_fixture()
    by_name = {
        element.get("declaredName"): element for element in fixture.elements.values()
    }

    assert by_name["RequirementCandidate"]["@type"] == "RequirementDefinition"
    assert by_name["reqCommandEmergencyBraking"]["@type"] == "RequirementUsage"
    assert by_name["evidenceContractFreshOverrideClear"]["@type"] == "RequirementUsage"
    assert by_name["nominalMovingVehicleTargetVerification"]["@type"] == "VerificationCaseUsage"
    assert sum(
        element["@type"] == "Dependency" for element in fixture.elements.values()
    ) == 3
    assert all((ROOT / path).is_file() for path in fixture.source_files)
