from __future__ import annotations

from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
BINDING_SCHEMA = "de4sdv.revision-binding/v2"


def semantic_authority() -> dict[str, Any]:
    """The model-built kernel contract's semantic-authority identity."""
    from model_contract_fixtures import semantic_authority_dict

    return semantic_authority_dict()


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


#: Under the model authority (owner decision 5) the hasRelevantEvidenceContract
#: discriminator fails closed without a validated EvidenceContract kernel root
#: (the fixture has none): zero edges, an explicit ``incomplete`` record with
#: this reason, never an ordinary absence. The successor relations are
#: incomplete over this fixture (its ConnectionUsages carry no successor
#: carrier endpoints).
EVIDENCE_CLOSURE_REASON = "EvidenceContract type closure is not established"
FIXTURE_UNSUPPORTED = {
    "hasRegulatorySource",
    "hasRelevantEvidenceContract",
    "hasValidationScenario",
    "validationScenarioFor",
}


def _evidence_record(records):
    matches = [r for r in records if r["predicate"] == "hasRelevantEvidenceContract"]
    assert len(matches) == 1, records
    return matches[0]


def ref(value: str) -> dict[str, str]:
    return {"@id": value}


@pytest.fixture
def semantic_service():
    from de4sdv.semantic.kernel_contract import KernelContract
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
    from model_contract_fixtures import model_contract

    contract = model_contract()
    assert isinstance(contract, KernelContract)
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
            "schema": BINDING_SCHEMA,
                "semantic_authority": semantic_authority(),
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
    from model_contract_fixtures import model_service

    # The production assembly (model-authority facade + successor traversal)
    # over the synthetic fixture repository.
    return model_service(binding, repository, expected_git_revision="a" * 40)


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
        "semantic_authority": semantic_authority(),
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


def test_model_status_and_queries_fail_closed_for_stale_semantic_authority(
    semantic_service,
) -> None:
    from dataclasses import replace

    from model_contract_fixtures import synthetic_identity
    from de4sdv.sysml_api.errors import RevisionMismatchError

    semantic_service.binding = replace(
        semantic_service.binding,
        scope="full-model",
        semantic_authority=synthetic_identity("stale"),
    )

    status = semantic_service.model_status()
    assert status["current_baseline"] is False
    assert status["gaps"] == [
        {
            "category": "runtime-binding",
            "reason": (
                "semantic authority does not match the identity recorded in the binding"
            ),
        }
    ]
    with pytest.raises(RevisionMismatchError, match="semantic authority mismatch"):
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
    # Integration closure R1: the fail-closed predicate is reported as
    # unsupported - mixed outcome alongside the evaluated predicates - and
    # never as an ordinary "no relationship found" gap.
    assert result["semantic_status"] == "incomplete"
    assert {
        record["predicate"] for record in result["unsupported_predicates"]
    } == FIXTURE_UNSUPPORTED
    record = _evidence_record(result["unsupported_predicates"])
    assert record["authority_state"] == "incomplete"
    assert EVIDENCE_CLOSURE_REASON in record["reason"]
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
    # Model impact is bounded witnessed reachability over every mapped
    # predicate: the K pair over the fixture's DerivesFromNeed witness also
    # appears; no EvidenceContract edge and no retired label is emitted.
    assert {edge["predicate"] for edge in impact["edges"]} == {
        "hasSubject",
        "verifiedBy",
        "derivesRequirementFromNeed",
        "derivedRequirementsOfNeed",
    }
    assert not {edge["predicate"] for edge in impact["edges"]} & {
        "hasRelevantEvidenceContract", "realizedBy", "deployedTo"}
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
    record = _evidence_record(coverage["unsupported_predicates"])
    assert record["authority_state"] == "incomplete"
    assert EVIDENCE_CLOSURE_REASON in record["reason"]
    # Native verifiedBy is independent of the blocked route (R2): the case is
    # still discovered through the root requirement's own membership.
    assert [case["element_id"] for case in coverage["verification_cases"]] == [
        "verification-1"
    ]
    assert coverage["evidence_contracts"] == []
    assert coverage["revision"]["sysml_commit_id"] == "commit-1"
    assert coverage["revision"]["semantic_authority"] == semantic_authority()
    assert any(
        entry.get("source") == f"semantic-authority://{semantic_authority()['id']}"
        for entry in coverage["provenance"]
    )


def test_verification_coverage_claims_no_evidence_contracts_while_unresolved(
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
    assert {
        record["predicate"] for record in coverage["unsupported_predicates"]
    } == FIXTURE_UNSUPPORTED
    record = _evidence_record(coverage["unsupported_predicates"])
    assert record["authority_state"] == "incomplete"
    assert EVIDENCE_CLOSURE_REASON in record["reason"]
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
    # The fail-closed EvidenceContract discriminator emits no edge.
    # Integration closure R2: native verifiedBy is discovered from the root
    # requirement's own RequirementVerificationMembership.
    assert {edge["predicate"] for edge in result["edges"]} == {
        "hasSubject",
        "verifiedBy",
        "derivesRequirementFromNeed",
        "derivedRequirementsOfNeed",
    }


def _placeholder_bundle(tmp_path: Path) -> tuple[Path, str]:
    """A schema-valid bundle file so selection passes and the binding is reached."""
    from de4sdv.semantic import model_authority_runtime as mar

    bundle_id = "mab-" + "1" * 32
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps({"schema": mar.MODEL_BUNDLE_SCHEMA, "bundle_id": bundle_id}),
                    encoding="utf-8")
    return path, bundle_id


def test_runtime_builder_requires_explicit_api_binding_and_expected_git(
    tmp_path: Path,
) -> None:
    from de4sdv.semantic import model_authority_runtime as mar
    from de4sdv.sysml_api.errors import RevisionMismatchError

    bundle_path, bundle_id = _placeholder_bundle(tmp_path)
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
                "schema": BINDING_SCHEMA,
                "semantic_authority": semantic_authority(),
            }
        ),
        encoding="utf-8",
    )
    # The runtime contract is keyword-only and explicit: no API URL, binding
    # or expected Git revision is ever defaulted.
    with pytest.raises(TypeError):
        mar.build_model_authority_runtime(ROOT, bundle_path, bundle_id,  # type: ignore[call-arg]
                                          binding_path=binding, expected_git_revision="a" * 40)
    # A stale binding (expected Git differs) is refused before any assembly.
    with pytest.raises(RevisionMismatchError, match="stale"):
        mar.build_model_authority_runtime(
            ROOT, bundle_path, bundle_id, api_url="http://127.0.0.1:9",
            binding_path=binding, expected_git_revision="b" * 40,
        )


def test_binding_refuses_a_different_semantic_authority() -> None:
    from model_contract_fixtures import model_contract, synthetic_identity
    from de4sdv.sysml_api.errors import RevisionMismatchError
    from de4sdv.sysml_api.revisions import RevisionBinding

    document = {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-01T00:00:00Z",
        "import_tool_version": "fixture/1",
        "semantic_validation": "passed",
        "scope": "full-model",
        "schema": BINDING_SCHEMA,
        "semantic_authority": synthetic_identity("other-contract").to_dict(),
    }
    binding = RevisionBinding.from_dict(document)
    with pytest.raises(RevisionMismatchError, match="semantic authority mismatch"):
        binding.require_semantic_authority(model_contract().identity)


def test_revision_binding_requires_explicit_semantic_authority_identity() -> None:
    from de4sdv.sysml_api.revisions import RevisionBinding

    base = {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-01T00:00:00Z",
        "import_tool_version": "fixture/1",
        "semantic_validation": "passed",
        "scope": "fixture",
    }
    with pytest.raises(ValueError, match="semantic_authority"):
        RevisionBinding.from_dict({**base, "schema": BINDING_SCHEMA})
    # A v1 binding (authored ontology identity) is refused as retired.
    with pytest.raises(ValueError, match="retired by O4 Wave C2"):
        RevisionBinding.from_dict(
            {**base, "ontology": {"path": "x.yaml", "sha256": "a" * 64}})
    with pytest.raises(ValueError, match="retired by O4 Wave C2"):
        RevisionBinding.from_dict({**base, "semantic_authority": semantic_authority()})


def test_mcp_server_over_the_service_exposes_the_read_only_tools(semantic_service) -> None:
    """The MCP surface built over the revision-bound service (in process)."""
    import anyio

    from de4sdv.semantic.mcp_server import create_mcp_server

    server = create_mcp_server(semantic_service)

    async def exercise() -> None:
        tools = await server.list_tools()
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
        _content, coverage = await server.call_tool(
            "verification_coverage",
            {"requirement_identifier": "reqCommandEmergencyBraking"},
        )
        # The fail-closed EvidenceContract discriminator emits nothing and its
        # state is exposed; the native root-requirement case is still proven,
        # so the status is partial (R2).
        assert coverage["status"] == "partial"
        assert coverage["semantic_status"] == "incomplete"
        assert {record["predicate"] for record in coverage["unsupported_predicates"]} == (
            FIXTURE_UNSUPPORTED)
        assert EVIDENCE_CLOSURE_REASON in _evidence_record(
            coverage["unsupported_predicates"])["reason"]
        assert coverage["evidence_contracts"] == []
        assert [case["element_id"] for case in coverage["verification_cases"]] == [
            "verification-1"
        ]
        assert coverage["revision"]["sysml_commit_id"] == "commit-1"
        _content, status = await server.call_tool("model_status", {})
        assert status["current_baseline"] is False
        assert status["revision"]["scope"] == "fixture"

    anyio.run(exercise)


def test_stdio_mcp_server_refuses_an_unset_semantic_authority(
    tmp_path: Path, semantic_api_server: str
) -> None:
    """Owner decision D6: the real server process never selects an authority
    implicitly; an unset selector refuses to start."""
    import os
    import subprocess
    import sys

    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps({
        "git_repository": "de4sdv/DE4SDV", "git_commit": "a" * 40,
        "sysml_project_id": "project-1", "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-01T00:00:00Z", "import_tool_version": "fixture/1",
        "semantic_validation": "passed", "scope": "fixture", "schema": BINDING_SCHEMA,
        "semantic_authority": semantic_authority(),
    }), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "DE4SDV_SEMANTIC_AUTHORITY"}
    result = subprocess.run(
        [sys.executable, "scripts/semantic_mcp_server.py", "--api-url", semantic_api_server,
         "--binding", str(binding), "--expected-git-revision", "a" * 40],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
    )
    assert result.returncode != 0
    assert "DE4SDV_SEMANTIC_AUTHORITY is unset" in result.stderr
    assert "Traceback" not in result.stderr


def test_privileged_result_validator_requires_exact_revision_and_native_edges() -> None:
    """The validator proves BOTH the resolved EvidenceContract range (model
    authority, owner decision 5) and the independent native verification
    path, and fails closed when either degrades."""
    from scripts.validate_semantic_mcp import validate_semantic_results

    revision = {
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "binding_status": "synchronized",
        "scope": "full-model",
        "semantic_authority": semantic_authority(),
    }
    evidence_edge = {
        "predicate": "hasRelevantEvidenceContract",
        "semantic_strength": "relevance",
        "target": "evidence-1",
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
            "semantic_status": "complete",
            "unsupported_predicates": [],
            "edges": [
                {"predicate": "hasSubject", "semantic_strength": "native-reference"},
                dict(evidence_edge),
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
            "status": "covered",
            "semantic_status": "complete",
            "unsupported_predicates": [],
            "verification_cases": [{"element_id": "verification-1"}],
            "evidence_contracts": [{"element_id": "evidence-1"}],
            "gaps": [],
        },
    }

    validate_semantic_results(results, expected_revision=revision)

    def corrupted(mutate) -> None:
        value = json.loads(json.dumps(results))
        mutate(value)
        validate_semantic_results(value, expected_revision=revision)

    def drop_verified_by(value):
        value["impact"]["edges"] = [
            edge for edge in value["impact"]["edges"] if edge["predicate"] != "verifiedBy"
        ]

    with pytest.raises(RuntimeError, match="verifiedBy"):
        corrupted(drop_verified_by)

    def drop_evidence_edge(value):
        value["semantic_neighbors"]["edges"] = [
            edge for edge in value["semantic_neighbors"]["edges"]
            if edge["predicate"] != "hasRelevantEvidenceContract"
        ]

    with pytest.raises(RuntimeError, match="no hasRelevantEvidenceContract edge"):
        corrupted(drop_evidence_edge)

    def still_blocked(value):
        value["verification_coverage"]["unsupported_predicates"] = [
            {"predicate": "hasRelevantEvidenceContract", "authority_state": "blocked"}
        ]

    with pytest.raises(RuntimeError, match="unsupported/blocked"):
        corrupted(still_blocked)

    def no_evidence_contracts(value):
        value["verification_coverage"]["evidence_contracts"] = []

    with pytest.raises(RuntimeError, match="evidence_contracts"):
        corrupted(no_evidence_contracts)

    def stale_revision(value):
        value["trace"]["revision"] = dict(revision, git_commit="b" * 40)

    with pytest.raises(RuntimeError, match="revision mismatch"):
        corrupted(stale_revision)
