from __future__ import annotations

import hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_PATH = ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"


def ontology_identity(path: Path = ONTOLOGY_PATH) -> dict[str, str]:
    return {
        "path": ONTOLOGY_PATH.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


class FixtureRepository:
    def __init__(self, elements: list[dict[str, Any]]) -> None:
        self.elements = elements

    def get_project(self, project_id: str) -> dict[str, Any]:
        assert project_id == "project-1"
        return {"@id": project_id, "@type": "Project"}

    def get_commit(self, project_id: str, commit_id: str) -> dict[str, Any]:
        assert (project_id, commit_id) == ("project-1", "commit-1")
        return {"@id": commit_id, "@type": "Commit"}

    def list_elements(self, project_id: str, commit_id: str) -> list[dict[str, Any]]:
        assert (project_id, commit_id) == ("project-1", "commit-1")
        return self.elements


class _ApiHandler(BaseHTTPRequestHandler):
    elements: list[dict[str, Any]] = []

    def do_GET(self) -> None:  # noqa: N802
        if self.path.endswith("/elements?page[size]=1000"):
            payload: object = self.elements
        elif self.path == "/projects/project-1":
            payload = {"@id": "project-1", "@type": "Project"}
        elif self.path == "/projects/project-1/commits/commit-1":
            payload = {"@id": "commit-1", "@type": "Commit"}
        else:
            self.send_error(404)
            return
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@pytest.fixture
def semantic_api_server(semantic_service):
    _ApiHandler.elements = semantic_service.repository.elements
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ApiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join()
        _ApiHandler.elements = []


def ref(value: str) -> dict[str, str]:
    return {"@id": value}


@pytest.fixture
def semantic_service():
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.impact import ImpactService
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.query import SemanticQueryService
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.revisions import RevisionBinding

    elements = [
        {
            "@id": "kernel-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
            "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
        },
        {
            "@id": "kernel-requirement-derivation",
            "@type": "ConnectionDefinition",
            "declaredName": "DerivesFromNeed",
            "qualifiedName": "DE4SDV_MethodContext::DerivesFromNeed",
        },
        {
            "@id": "kernel-need",
            "@type": "RequirementDefinition",
            "declaredName": "StakeholderNeedCandidate",
            "qualifiedName": "DE4SDV_MethodContext::StakeholderNeedCandidate",
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
            "documentation": [ref("doc-1")],
        },
        {
            "@id": "doc-1",
            "@type": "Documentation",
            "body": "Command emergency braking when the decision is active.",
        },
        {
            "@id": "subject-membership",
            "@type": "SubjectMembership",
            "owningRelatedElement": ref("req-1"),
            "memberElement": ref("product-1"),
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
            "@id": "need-1",
            "@type": "RequirementUsage",
            "declaredName": "needCommonAEBSCapability",
            "qualifiedName": "DE4SDV_AEBSNeedsRequirements::needCommonAEBSCapability",
        },
        {
            "@id": "req-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("req-1"),
            "type": ref("kernel-requirement"),
            "typedFeature": ref("req-1"),
        },
        {
            "@id": "need-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("need-1"),
            "type": ref("kernel-need"),
            "typedFeature": ref("need-1"),
        },
        {
            "@id": "derivation-conn",
            "@type": "ConnectionUsage",
            "declaredName": "reqCommandEmergencyBrakingDerivation",
            "ownedRelationship": [
                ref("derivation-end-need"),
                ref("derivation-end-req"),
                ref("derivation-conn-typing"),
            ],
        },
        {
            "@id": "derivation-end-need",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": ref("derivation-conn"),
            "ownedRelatedElement": [ref("need-1")],
        },
        {
            "@id": "derivation-end-req",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": ref("derivation-conn"),
            "ownedRelatedElement": [ref("req-1")],
        },
        {
            "@id": "derivation-conn-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("derivation-conn"),
            "type": ref("kernel-requirement-derivation"),
            "typedFeature": ref("derivation-conn"),
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
    ]
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
            "scope": "fixture",
            "ontology": ontology_identity(),
            "kernel_bindings": [
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
                    "ontology_class": "MemberProduct",
                    "element_id": "kernel-member-product",
                    "source_file": (
                        "textual-notation-of-model/packages/methods/de4sdv/"
                        "de4sdv_product_line.sysml"
                    ),
                    "declaration": "part def ProductLineMemberProduct",
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
                    "element_id": "kernel-requirement-derivation",
                    "source_file": (
                        "textual-notation-of-model/packages/methods/de4sdv/"
                        "de4sdv_method_context.sysml"
                    ),
                    "declaration": "connection def DerivesFromNeed",
                },
            ],
        }
    )
    from de4sdv.semantic.kernel_binding_index import KernelBindingIndex

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
    return SemanticQueryService(
        repository=repository,  # type: ignore[arg-type]
        binding=binding,
        contract=contract,
        binder=binder,
        traversal=traversal,
        impact_service=impact,
        expected_git_revision="a" * 40,
    )


def test_model_status_does_not_present_fixture_as_current_baseline(semantic_service) -> None:
    result = semantic_service.model_status()

    assert result["current_baseline"] is False
    assert result["read_only"] is True
    assert result["revision"] == {
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "binding_status": "synchronized",
        "scope": "fixture",
        "ontology": ontology_identity(),
    }
    assert result["element_count"] is None
    assert result["gaps"] == [
        {
            "category": "runtime-binding",
            "reason": "binding scope is fixture, not full-model",
        }
    ]


def test_model_status_reports_exact_validated_full_model_binding(semantic_service) -> None:
    from dataclasses import replace

    semantic_service.binding = replace(semantic_service.binding, scope="full-model")

    result = semantic_service.model_status()

    assert result["current_baseline"] is True
    # 20 fixture elements: the c3 subject-membership fixture carries the
    # authored FeatureTyping for the member product in addition to the
    # membership shape.
    assert result["element_count"] == 20
    assert result["gaps"] == []


def test_model_status_and_queries_fail_closed_for_stale_ontology_identity(
    semantic_service,
) -> None:
    from dataclasses import replace

    from de4sdv.sysml_api.errors import RevisionMismatchError
    from de4sdv.sysml_api.revisions import OntologyIdentity

    semantic_service.binding = replace(
        semantic_service.binding,
        scope="full-model",
        ontology=OntologyIdentity(
            path=semantic_service.binding.ontology.path,
            sha256="b" * 64,
        ),
    )

    status = semantic_service.model_status()
    assert status["current_baseline"] is False
    assert status["gaps"] == [
        {
            "category": "runtime-binding",
            "reason": (
                "ontology contract does not match the identity recorded in the binding"
            ),
        }
    ]
    with pytest.raises(RevisionMismatchError, match="ontology contract"):
        semantic_service.resolve_element("req-1")


def test_model_status_reports_api_unavailability_as_runtime_gap(
    semantic_service, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from de4sdv.sysml_api.errors import ApiError

    semantic_service.binding = replace(semantic_service.binding, scope="full-model")

    def unavailable(project_id: str, commit_id: str) -> list[dict[str, Any]]:
        del project_id, commit_id
        raise ApiError("GET", "/elements", "connection refused")

    monkeypatch.setattr(semantic_service.repository, "list_elements", unavailable)

    result = semantic_service.model_status()

    assert result["current_baseline"] is False
    assert result["element_count"] is None
    assert result["gaps"] == [
        {
            "category": "runtime-api",
            "reason": "Bound SysML API revision is unavailable: GET /elements failed: connection refused",
        }
    ]


def test_resolve_and_inspect_preserve_uuid_revision_and_documentation(semantic_service) -> None:
    resolved = semantic_service.resolve_element("reqCommandEmergencyBraking")
    inspected = semantic_service.inspect_element("req-1")

    assert resolved["element"]["element_id"] == "req-1"
    assert resolved["element"]["source_uri"].endswith("/req-1")
    assert resolved["resolution_level"] == "structural-match"
    assert resolved["revision"]["git_commit"] == "a" * 40
    assert inspected["element"]["documentation"] == [
        "Command emergency braking when the decision is active."
    ]
    assert inspected["element"]["element_id"] == "req-1"


def test_semantic_neighbors_only_use_ontology_declared_predicates(semantic_service) -> None:
    result = semantic_service.semantic_neighbors("req-1")

    # c5 correction: the EvidenceContract range is blocked and emits nothing,
    # so no hasRelevantEvidenceContract edge is produced for this fixture.
    # Integration closure R2: native verifiedBy is discovered from the root
    # requirement's own RequirementVerificationMembership, independent of the
    # blocked EvidenceContract route.
    assert {edge["predicate"] for edge in result["edges"]} == {
        "derivesRequirementFromNeed",
        "hasSubject",
        "verifiedBy",
    }
    assert {edge["semantic_strength"] for edge in result["edges"]} == {
        "derivation",
        "native-reference",
        "native-verification",
    }
    assert all(edge["api_object_id"] for edge in result["edges"])
    # Integration closure R1: the blocked predicate is reported as
    # unsupported - mixed outcome alongside the evaluated predicates - and
    # never as an ordinary "no relationship found" gap.
    assert result["semantic_status"] == "incomplete"
    assert [
        record["predicate"] for record in result["unsupported_predicates"]
    ] == ["hasRelevantEvidenceContract"]
    assert result["unsupported_predicates"][0]["authority_state"] == "blocked"
    assert "EvidenceContract-specific identity is not machine-resolvable" in (
        result["unsupported_predicates"][0]["reason"]
    )
    assert all(gap["category"] != "hasRelevantEvidenceContract" for gap in result["gaps"])


def test_impact_trace_and_verification_coverage_return_compact_provenance(semantic_service) -> None:
    impact = semantic_service.impact("reqCommandEmergencyBraking")
    trace = semantic_service.trace("req-1", "verification-1", max_depth=3)
    coverage = semantic_service.verification_coverage("req-1")

    # c5 correction: the evidence-chain route (req-1 -> evidence-1 ->
    # verification-1) no longer exists because the EvidenceContract range is
    # blocked. Integration closure R2: a supported native path DOES exist —
    # the root requirement's own RequirementVerificationMembership anchors
    # verification-1 directly — so the trace proves native verifiedBy while
    # the blocked predicate is recorded as unavailable (R1: no claim of a
    # fully-evaluated absence).
    assert {edge["predicate"] for edge in impact["edges"]} == {
        "hasSubject",
        "verifiedBy",
    }
    assert [step["predicate"] for step in trace["path"]] == ["verifiedBy"]
    assert trace["semantic_status"] == "incomplete"
    assert any(
        record["predicate"] == "hasRelevantEvidenceContract"
        for record in trace["unsupported_predicates"]
    )
    # A found path is proven; the blocked predicate is exposed through
    # unsupported_predicates without attributing anything to it.
    assert trace["gaps"] == []
    # R1: the blocked EvidenceContract range must not be silently folded into
    # the status. The native case is proven (partial coverage), and the
    # missing-identity reason survives as an explicit unsupported record.
    assert coverage["status"] == "partial"
    assert coverage["semantic_status"] == "incomplete"
    assert any(
        record["predicate"] == "hasRelevantEvidenceContract"
        and record["authority_state"] == "blocked"
        for record in coverage["unsupported_predicates"]
    )
    assert any(
        gap["category"] == "verification-unsupported"
        and "EvidenceContract" in gap["reason"]
        for gap in coverage["gaps"]
    )
    # Native verifiedBy is independent of the blocked route (R2): the case is
    # still discovered through the root requirement's own membership.
    assert [case["element_id"] for case in coverage["verification_cases"]] == [
        "verification-1"
    ]
    assert coverage["evidence_contracts"] == []
    assert coverage["revision"]["sysml_commit_id"] == "commit-1"
    assert coverage["revision"]["ontology"] == ontology_identity()
    assert any(
        entry.get("sha256") == ontology_identity()["sha256"]
        for entry in coverage["provenance"]
    )


def test_verification_coverage_claims_no_evidence_contracts_while_blocked(
    semantic_service,
) -> None:
    """c5 correction: the EvidenceContract range gate emits nothing — both a
    verified requirement-usage source (evidence-1) and an unverified one
    (evidence-2) are quiet absence, so no evidence contract enters coverage
    and no coverage claim is derived from either. Integration closure R1:
    the blocked range still makes the assessment INCOMPLETE (not ordinary
    "uncovered") and its reason survives; the native root-requirement
    verifiedBy case remains discoverable and is reported (R2)."""
    semantic_service.repository.elements.extend(
        [
            {
                "@id": "evidence-2",
                "@type": "RequirementUsage",
                "declaredName": "evidenceContractWithoutVerification",
            },
            {
                "@id": "dependency-2",
                "@type": "Dependency",
                "source": [ref("evidence-2")],
                "target": [ref("req-1")],
            },
        ]
    )

    coverage = semantic_service.verification_coverage("req-1")

    # R1: blocked range -> semantic_status incomplete with the reason; the
    # native root-requirement case is still proven, so the status is partial
    # (native part proven, evidence part not assessable), never plain
    # "uncovered" with an empty explanation.
    assert coverage["status"] == "partial"
    assert coverage["semantic_status"] == "incomplete"
    assert [
        record["predicate"] for record in coverage["unsupported_predicates"]
    ] == ["hasRelevantEvidenceContract"]
    assert coverage["unsupported_predicates"][0]["authority_state"] == "blocked"
    assert "EvidenceContract-specific identity is not machine-resolvable" in (
        coverage["unsupported_predicates"][0]["reason"]
    )
    assert any(
        gap["category"] == "verification-unsupported" for gap in coverage["gaps"]
    )
    assert coverage["evidence_contracts"] == []
    assert coverage["unverified_evidence_contracts"] == []
    # Native verification through the root requirement is unaffected.
    assert [case["element_id"] for case in coverage["verification_cases"]] == [
        "verification-1"
    ]


def test_semantic_queries_refuse_stale_but_allow_explicit_fixture_scope(semantic_service) -> None:
    from de4sdv.sysml_api.errors import RevisionMismatchError

    semantic_service.expected_git_revision = "b" * 40
    with pytest.raises(RevisionMismatchError, match="stale"):
        semantic_service.resolve_element("req-1")

    semantic_service.expected_git_revision = "a" * 40
    result = semantic_service.impact("req-1")
    assert result["revision"]["scope"] == "fixture"


def test_ambiguous_identity_fails_closed(semantic_service) -> None:
    from de4sdv.sysml_api.errors import AmbiguousIdentityError

    semantic_service.repository.elements.append(
        {
            "@id": "req-2",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        }
    )
    with pytest.raises(AmbiguousIdentityError):
        semantic_service.resolve_element("reqCommandEmergencyBraking")


def test_mcp_surface_exposes_only_the_declared_read_only_semantic_tools(
    semantic_service,
) -> None:
    import asyncio

    from de4sdv.semantic.mcp_server import create_mcp_server

    server = create_mcp_server(semantic_service)
    tools = server._tool_manager.list_tools()

    assert {tool.name for tool in tools} == {
        "model_status",
        "resolve_element",
        "inspect_element",
        "semantic_neighbors",
        "impact",
        "trace",
        "verification_coverage",
        # Lane C method-conformance surfaces (frozen baseline Section 13)
        "phase_contract",
        "increment_status",
        "method_gaps",
        "next_obligation",
    }
    assert all(tool.annotations.readOnlyHint for tool in tools)
    assert all(not tool.annotations.destructiveHint for tool in tools)
    assert all(tool.annotations.idempotentHint for tool in tools)
    assert all(not tool.annotations.openWorldHint for tool in tools)

    result = asyncio.run(
        server._tool_manager.call_tool(
            "impact", {"identifier": "reqCommandEmergencyBraking"}
        )
    )
    assert result["revision"]["git_commit"] == "a" * 40
    # c5 correction: the blocked EvidenceContract range emits no edge.
    # Integration closure R2: native verifiedBy is discovered from the root
    # requirement's own RequirementVerificationMembership.
    assert {edge["predicate"] for edge in result["edges"]} == {
        "hasSubject",
        "verifiedBy",
    }


def test_runtime_builder_requires_explicit_api_binding_and_expected_git(
    tmp_path: Path,
) -> None:
    import json

    from de4sdv.semantic.runtime import build_semantic_runtime

    binding = tmp_path / "binding.json"
    binding.write_text(
        json.dumps(
            {
                "git_repository": "de4sdv/DE4SDV",
                "git_commit": "a" * 40,
                "sysml_project_id": "project-1",
                "sysml_commit_id": "commit-1",
                "import_timestamp": "2026-09-01T00:00:00Z",
                "import_tool_version": "fixture/1",
                "semantic_validation": "passed",
                "scope": "fixture",
                "ontology": ontology_identity(),
                "kernel_bindings": [
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
                        "ontology_class": "MemberProduct",
                        "element_id": "kernel-member-product",
                        "source_file": (
                            "textual-notation-of-model/packages/methods/de4sdv/"
                            "de4sdv_product_line.sysml"
                        ),
                        "declaration": "part def ProductLineMemberProduct",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    service = build_semantic_runtime(
        api_url="http://127.0.0.1:9",
        binding_path=binding,
        expected_git_revision="b" * 40,
        ontology_path=ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    )

    assert service.model_status()["current_baseline"] is False
    assert service.model_status()["gaps"][0]["category"] == "runtime-binding"


def test_runtime_refuses_binding_with_different_ontology_contract(
    tmp_path: Path,
) -> None:
    from de4sdv.semantic.runtime import build_semantic_runtime
    from de4sdv.sysml_api.errors import RevisionMismatchError

    altered_ontology = tmp_path / "de4sdv-basic-ontology.yaml"
    altered_ontology.write_bytes(ONTOLOGY_PATH.read_bytes() + b"\n# altered contract\n")
    binding = tmp_path / "binding.json"
    binding.write_text(
        json.dumps(
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
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RevisionMismatchError, match="ontology contract"):
        build_semantic_runtime(
            api_url="http://127.0.0.1:9",
            binding_path=binding,
            expected_git_revision="a" * 40,
            ontology_path=altered_ontology,
        )


def test_revision_binding_requires_explicit_ontology_identity() -> None:
    from de4sdv.sysml_api.revisions import RevisionBinding

    with pytest.raises(ValueError, match="ontology"):
        RevisionBinding.from_dict(
            {
                "git_repository": "de4sdv/DE4SDV",
                "git_commit": "a" * 40,
                "sysml_project_id": "project-1",
                "sysml_commit_id": "commit-1",
                "import_timestamp": "2026-09-01T00:00:00Z",
                "import_tool_version": "fixture/1",
                "semantic_validation": "passed",
                "scope": "fixture",
            }
        )


def test_stdio_mcp_end_to_end_uses_revision_bound_fixture_runtime(
    tmp_path: Path, semantic_api_server: str
) -> None:
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    binding = tmp_path / "binding.json"
    binding.write_text(
        json.dumps(
            {
                "git_repository": "de4sdv/DE4SDV",
                "git_commit": "a" * 40,
                "sysml_project_id": "project-1",
                "sysml_commit_id": "commit-1",
                "import_timestamp": "2026-09-01T00:00:00Z",
                "import_tool_version": "fixture/1",
                "semantic_validation": "passed",
                "scope": "fixture",
                "ontology": ontology_identity(),
                "kernel_bindings": [
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
                        "ontology_class": "MemberProduct",
                        "element_id": "kernel-member-product",
                        "source_file": (
                            "textual-notation-of-model/packages/methods/de4sdv/"
                            "de4sdv_product_line.sysml"
                        ),
                        "declaration": "part def ProductLineMemberProduct",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    async def exercise() -> None:
        params = StdioServerParameters(
            command="python",
            args=[
                "scripts/semantic_mcp_server.py",
                "--api-url",
                semantic_api_server,
                "--binding",
                str(binding),
                "--expected-git-revision",
                "a" * 40,
            ],
            cwd=ROOT,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "model_status",
                    "resolve_element",
                    "inspect_element",
                    "semantic_neighbors",
                    "impact",
                    "trace",
                    "verification_coverage",
                    # Lane C method-conformance surfaces (frozen baseline Section 13)
                    "phase_contract",
                    "increment_status",
                    "method_gaps",
                    "next_obligation",
                }
                result = await session.call_tool(
                    "verification_coverage",
                    {"requirement_identifier": "reqCommandEmergencyBraking"},
                )
                assert not result.isError
                # c5 correction + integration closure R1: the blocked
                # EvidenceContract range emits nothing, and its blocked state
                # is exposed - the assessment is never plain "uncovered" with
                # an empty explanation. The native root-requirement case is
                # still proven, so the status is partial (R2).
                assert result.structuredContent["status"] == "partial"
                assert result.structuredContent["semantic_status"] == "incomplete"
                assert [
                    record["predicate"]
                    for record in result.structuredContent["unsupported_predicates"]
                ] == ["hasRelevantEvidenceContract"]
                assert (
                    result.structuredContent["evidence_contracts"] == []
                )
                # R2: native verification through the root requirement's own
                # RequirementVerificationMembership remains discoverable.
                assert [
                    case["element_id"]
                    for case in result.structuredContent["verification_cases"]
                ] == ["verification-1"]
                assert (
                    result.structuredContent["revision"]["sysml_commit_id"]
                    == "commit-1"
                )
                status = await session.call_tool("model_status", {})
                assert status.structuredContent["current_baseline"] is False
                assert status.structuredContent["revision"]["scope"] == "fixture"

    anyio.run(exercise)


def test_privileged_result_validator_requires_exact_revision_and_native_edges() -> None:
    """c5 integration closure (R1+R2): the validator proves BOTH the blocked
    EvidenceContract state and the independent native verification path, and
    fails closed when either degrades."""
    from scripts.validate_semantic_mcp import validate_semantic_results

    revision = {
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "binding_status": "synchronized",
        "scope": "full-model",
        "ontology": ontology_identity(),
    }
    blocked_record = {
        "predicate": "hasRelevantEvidenceContract",
        "authority_state": "blocked",
        "reason": (
            "EvidenceContract-specific identity is not machine-resolvable at "
            "the reviewed revision; native verification membership also "
            "admits AcceptanceCriterion and therefore cannot establish the "
            "declared EvidenceContract range."
        ),
    }
    verified_by_edge = {
        "predicate": "verifiedBy",
        "semantic_strength": "native-verification",
        "target": "verification-1",
    }
    results = {
        "model_status": {"current_baseline": True, "read_only": True, "revision": revision},
        "resolve_element": {"revision": revision, "element": {"element_id": "req-1"}},
        "inspect_element": {"revision": revision, "element": {"element_id": "req-1"}},
        "semantic_neighbors": {
            "revision": revision,
            "root": {"element_id": "req-1"},
            "semantic_status": "incomplete",
            "unsupported_predicates": [dict(blocked_record)],
            "edges": [
                {"predicate": "hasSubject", "semantic_strength": "native-reference"},
            ],
        },
        "impact": {
            "revision": revision,
            "root": {"element_id": "req-1"},
            "edges": [
                {"predicate": "hasSubject", "semantic_strength": "native-reference"},
                dict(verified_by_edge),
            ],
            "nodes": [
                {"element_id": "req-1"},
                {"element_id": "verification-1"},
            ],
            "gaps": [],
        },
        "trace": {
            "revision": revision,
            "source": {"element_id": "req-1"},
            "path": [{"predicate": "verifiedBy"}],
            "gaps": [],
        },
        "verification_coverage": {
            "revision": revision,
            "requirement": {"element_id": "req-1"},
            "status": "partial",
            "semantic_status": "incomplete",
            "unsupported_predicates": [dict(blocked_record)],
            "verification_cases": [{"element_id": "verification-1"}],
            "gaps": [
                {
                    "category": "verification-unsupported",
                    "reason": "blocked hasRelevantEvidenceContract range: "
                    "EvidenceContract identity unresolved",
                }
            ],
        },
    }

    validate_semantic_results(results, expected_revision=revision)

    def without_verified_by() -> None:
        stripped = json.loads(json.dumps(results))
        stripped["impact"]["edges"] = [
            edge
            for edge in stripped["impact"]["edges"]
            if edge["predicate"] != "verifiedBy"
        ]
        validate_semantic_results(stripped, expected_revision=revision)

    with pytest.raises(RuntimeError, match="verifiedBy"):
        without_verified_by()

    def without_blocked_state() -> None:
        stripped = json.loads(json.dumps(results))
        stripped["semantic_neighbors"]["unsupported_predicates"] = []
        validate_semantic_results(stripped, expected_revision=revision)

    with pytest.raises(RuntimeError, match="blocked"):
        without_blocked_state()

    def with_false_evidence_edge() -> None:
        corrupted = json.loads(json.dumps(results))
        corrupted["semantic_neighbors"]["edges"].append(
            {"predicate": "hasRelevantEvidenceContract"}
        )
        validate_semantic_results(corrupted, expected_revision=revision)

    with pytest.raises(RuntimeError, match="false EvidenceContract edges"):
        with_false_evidence_edge()

    def with_plain_uncovered() -> None:
        corrupted = json.loads(json.dumps(results))
        coverage = corrupted["verification_coverage"]
        coverage["status"] = "uncovered"
        coverage["semantic_status"] = "complete"
        coverage["unsupported_predicates"] = []
        coverage["gaps"] = []
        validate_semantic_results(corrupted, expected_revision=revision)

    with pytest.raises(RuntimeError, match="incomplete"):
        with_plain_uncovered()
