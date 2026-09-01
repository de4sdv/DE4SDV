from __future__ import annotations

from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


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
            "@id": "evidence-1",
            "@type": "RequirementUsage",
            "declaredName": "evidenceContract009BNominalBrakingPath",
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
            "declaredName": "nominalMovingVehicleTargetVerification009B",
        },
        {
            "@id": "rvm-1",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": ref("verification-1"),
            "memberElement": ref("evidence-1"),
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
        }
    )
    binder = OntologyApiBinder(
        contract,
        repository,  # type: ignore[arg-type]
        project_id="project-1",
        commit_id="commit-1",
    )
    traversal = SemanticTraversal(contract)
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
    assert result["element_count"] == 9
    assert result["gaps"] == []


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

    assert {edge["predicate"] for edge in result["edges"]} == {
        "hasRelevantEvidenceContract",
        "hasSubject",
    }
    assert {edge["semantic_strength"] for edge in result["edges"]} == {
        "relevance",
        "native-reference",
    }
    assert all(edge["api_object_id"] for edge in result["edges"])


def test_impact_trace_and_verification_coverage_return_compact_provenance(semantic_service) -> None:
    impact = semantic_service.impact("reqCommandEmergencyBraking")
    trace = semantic_service.trace("req-1", "verification-1", max_depth=3)
    coverage = semantic_service.verification_coverage("req-1")

    assert {edge["predicate"] for edge in impact["edges"]} == {
        "hasRelevantEvidenceContract",
        "hasSubject",
        "verifiedBy",
    }
    assert [edge["predicate"] for edge in trace["path"]] == [
        "hasRelevantEvidenceContract",
        "verifiedBy",
    ]
    assert coverage["status"] == "covered"
    assert coverage["verification_cases"][0]["element_id"] == "verification-1"
    assert coverage["gaps"] == []
    assert coverage["revision"]["sysml_commit_id"] == "commit-1"


def test_verification_coverage_is_partial_when_one_evidence_contract_has_no_case(
    semantic_service,
) -> None:
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

    assert coverage["status"] == "partial"
    assert coverage["unverified_evidence_contracts"] == [
        {
            "element_id": "evidence-2",
            "semantic_type": "EvidenceContract",
            "sysml_type": "RequirementUsage",
            "declared_name": "evidenceContractWithoutVerification",
            "qualified_name": None,
            "category": "evidence",
            "source_uri": "sysml://project-1/commit-1/evidence-2",
        }
    ]
    assert coverage["gaps"][0]["category"] == "verification"


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


def test_mcp_surface_exposes_only_seven_read_only_semantic_tools(
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
    assert {edge["predicate"] for edge in result["edges"]} == {
        "hasRelevantEvidenceContract",
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
                }
                result = await session.call_tool(
                    "verification_coverage",
                    {"requirement_identifier": "reqCommandEmergencyBraking"},
                )
                assert not result.isError
                assert result.structuredContent["status"] == "covered"
                assert (
                    result.structuredContent["revision"]["sysml_commit_id"]
                    == "commit-1"
                )
                status = await session.call_tool("model_status", {})
                assert status.structuredContent["current_baseline"] is False
                assert status.structuredContent["revision"]["scope"] == "fixture"

    anyio.run(exercise)


def test_privileged_result_validator_requires_exact_revision_and_native_edges() -> None:
    from scripts.validate_semantic_mcp import validate_semantic_results

    revision = {
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "binding_status": "synchronized",
        "scope": "full-model",
    }
    results = {
        "model_status": {"current_baseline": True, "read_only": True, "revision": revision},
        "resolve_element": {"revision": revision, "element": {"element_id": "req-1"}},
        "inspect_element": {"revision": revision, "element": {"element_id": "req-1"}},
        "semantic_neighbors": {
            "revision": revision,
            "edges": [
                {"predicate": "hasSubject", "semantic_strength": "native-reference"},
                {"predicate": "hasRelevantEvidenceContract", "semantic_strength": "relevance"},
            ],
        },
        "impact": {
            "revision": revision,
            "edges": [
                {"predicate": "hasSubject", "semantic_strength": "native-reference"},
                {"predicate": "verifiedBy", "semantic_strength": "native-verification"},
            ],
            "gaps": [],
        },
        "trace": {"revision": revision, "path": [{"predicate": "verifiedBy"}], "gaps": []},
        "verification_coverage": {
            "revision": revision,
            "status": "covered",
            "verification_cases": [{"element_id": "verification-1"}],
            "gaps": [],
        },
    }

    validate_semantic_results(results, expected_revision=revision)
    results["impact"]["edges"] = [
        edge for edge in results["impact"]["edges"] if edge["predicate"] != "verifiedBy"
    ]
    with pytest.raises(RuntimeError, match="verifiedBy"):
        validate_semantic_results(results, expected_revision=revision)
