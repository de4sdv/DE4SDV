"""Round-F3 regression tests: requirement-to-function and reverse architecture
relevance traversal with typed dependency filters.

Fixture shapes mirror the serialized SysML v2 2025-02-01 API model observed in
the full-model baseline (Subclassification/FeatureTyping shapes verified against
the 57k-element semantic snapshot).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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


def _f3_elements():
    """Minimal API-shaped fixture covering both new predicates.

    Shapes: Dependency with source/target reference lists; Subclassification
    with subclassifier/superclassifier; FeatureTyping with
    owningRelatedElement/type.
    """
    ref = lambda value: {"@id": value}
    return [
        {
            "@id": "kernel-member-product",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
        },
        {
            "@id": "configured-member-def",
            "@type": "PartDefinition",
            "declaredName": "ConfiguredMember",
        },
        {
            "@id": "sub-membership",
            "@type": "Subclassification",
            "subclassifier": ref("configured-member-def"),
            "superclassifier": ref("kernel-member-product"),
        },
        {
            "@id": "req-1",
            "@type": "RequirementUsage",
            "declaredName": "reqExample",
        },
        # Outgoing req -> ActionUsage: specifiesFunction edge.
        {
            "@id": "action-translate",
            "@type": "ActionUsage",
            "declaredName": "translateSignal",
        },
        {
            "@id": "dep-specifies-function",
            "@type": "Dependency",
            "source": [ref("req-1")],
            "target": [ref("action-translate")],
        },
        # Outgoing req -> need-shaped RequirementUsage: NOT a function edge
        # (target type filter rejects RequirementUsage).
        {
            "@id": "need-1",
            "@type": "RequirementUsage",
            "declaredName": "needExample",
        },
        {
            "@id": "dep-derives-from-need",
            "@type": "Dependency",
            "source": [ref("req-1")],
            "target": [ref("need-1")],
        },
        # Incoming PartUsage -> req: hasRelevantArchitecture edge.
        {
            "@id": "part-translator",
            "@type": "PartUsage",
            "declaredName": "signalTranslator",
        },
        {
            "@id": "dep-from-part",
            "@type": "Dependency",
            "source": [ref("part-translator")],
            "target": [ref("req-1")],
        },
        # Incoming ActionDefinition -> req: also architecture relevance.
        {
            "@id": "action-def-flow",
            "@type": "ActionDefinition",
            "declaredName": "ForwardServiceFlow",
        },
        {
            "@id": "dep-from-action-def",
            "@type": "Dependency",
            "source": [ref("action-def-flow")],
            "target": [ref("req-1")],
        },
        # Incoming dependency from a configured-member-typed PartUsage:
        # product-line relationship, must be EXCLUDED from architecture.
        {
            "@id": "configured-member-usage",
            "@type": "PartUsage",
            "declaredName": "configuredMember",
        },
        {
            "@id": "ft-configured-member",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("configured-member-usage"),
            "type": ref("configured-member-def"),
        },
        {
            "@id": "dep-from-configured-member",
            "@type": "Dependency",
            "source": [ref("configured-member-usage")],
            "target": [ref("req-1")],
        },
        # Incoming dependency from an untyped requirement usage: excluded by
        # the source_types filter (acceptance-criterion shape).
        {
            "@id": "acceptance-criterion",
            "@type": "RequirementUsage",
            "declaredName": "acceptanceCriterionExample",
        },
        {
            "@id": "dep-from-criterion",
            "@type": "Dependency",
            "source": [ref("acceptance-criterion")],
            "target": [ref("req-1")],
        },
    ]


def test_ontology_declares_function_and_reverse_architecture_mappings() -> None:
    contract = _contract()
    function_mapping = contract.relationship_mapping("specifiesFunction")
    assert function_mapping.strategy == "dependency"
    assert function_mapping.semantic_strength == "relevance"
    assert function_mapping.configuration["direction"] == "outgoing"
    assert function_mapping.configuration["target_types"] == [
        "ActionUsage",
        "ActionDefinition",
    ]
    architecture_mapping = contract.relationship_mapping("hasRelevantArchitecture")
    assert architecture_mapping.strategy == "dependency"
    assert architecture_mapping.semantic_strength == "relevance"
    assert architecture_mapping.configuration["direction"] == "incoming"
    assert (
        architecture_mapping.configuration["exclude_source_specializations_of"]
        == "ProductLineMemberProduct"
    )


def test_specifies_function_traverses_only_action_typed_targets() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    by_id = {item["@id"]: item for item in _f3_elements()}
    requirement = by_id["req-1"]
    hops = SemanticTraversal(_contract()).traverse(
        "specifiesFunction", requirement, _f3_elements()
    )
    assert [hop.target["@id"] for hop in hops] == ["action-translate"]
    hop = hops[0]
    assert hop.predicate == "specifiesFunction"
    assert hop.semantic_strength == "relevance"
    assert hop.api_object["@id"] == "dep-specifies-function"


def test_has_relevant_architecture_excludes_member_product_sources() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    by_id = {item["@id"]: item for item in _f3_elements()}
    requirement = by_id["req-1"]
    hops = SemanticTraversal(_contract()).traverse(
        "hasRelevantArchitecture", requirement, _f3_elements()
    )
    targets = sorted(hop.target["@id"] for hop in hops)
    # PartUsage + ActionDefinition sources pass; the configured-member-typed
    # PartUsage (product-line) and the requirement-typed criterion are
    # excluded.
    assert targets == ["action-def-flow", "part-translator"]
    for hop in hops:
        assert hop.predicate == "hasRelevantArchitecture"
        assert hop.semantic_strength == "relevance"
        assert hop.target["@id"] != "configured-member-usage"


def test_member_product_exclusion_follows_transitive_lineage() -> None:
    from de4sdv.semantic.traversal import SemanticTraversal

    ref = lambda value: {"@id": value}
    elements = [
        {
            "@id": "kernel-member-product",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
        },
        # Two-level lineage: intermediate def specializes the kernel, the
        # usage's def specializes the intermediate.
        {
            "@id": "intermediate-def",
            "@type": "PartDefinition",
            "declaredName": "IntermediateMember",
        },
        {
            "@id": "sub-intermediate",
            "@type": "Subclassification",
            "subclassifier": ref("intermediate-def"),
            "superclassifier": ref("kernel-member-product"),
        },
        {
            "@id": "leaf-def",
            "@type": "PartDefinition",
            "declaredName": "LeafMember",
        },
        {
            "@id": "sub-leaf",
            "@type": "Subclassification",
            "subclassifier": ref("leaf-def"),
            "superclassifier": ref("intermediate-def"),
        },
        {
            "@id": "req-1",
            "@type": "RequirementUsage",
            "declaredName": "reqExample",
        },
        {
            "@id": "leaf-usage",
            "@type": "PartUsage",
            "declaredName": "leafMemberUsage",
        },
        {
            "@id": "ft-leaf",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("leaf-usage"),
            "type": ref("leaf-def"),
        },
        {
            "@id": "dep-from-leaf",
            "@type": "Dependency",
            "source": [ref("leaf-usage")],
            "target": [ref("req-1")],
        },
        {
            "@id": "plain-usage",
            "@type": "PartUsage",
            "declaredName": "plainPart",
        },
        {
            "@id": "dep-from-plain",
            "@type": "Dependency",
            "source": [ref("plain-usage")],
            "target": [ref("req-1")],
        },
    ]
    hops = SemanticTraversal(_contract()).traverse(
        "hasRelevantArchitecture", {"@id": "req-1"}, elements
    )
    assert [hop.target["@id"] for hop in hops] == ["plain-usage"]


def test_exclusion_fails_closed_on_unknown_root_class(monkeypatch) -> None:
    import yaml

    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.traversal import SemanticTraversal

    raw = yaml.safe_load(
        (ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml").read_text()
    )
    raw["relationships"]["hasRelevantArchitecture"]["sysml_mapping"][
        "exclude_source_specializations_of"
    ] = "NoSuchKernelClass"
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        yaml.safe_dump(raw, handle)
        broken_path = Path(handle.name)
    try:
        contract = KernelContract.load(broken_path)
        by_id = {item["@id"]: item for item in _f3_elements()}
        with pytest.raises(ValueError, match="names no model element"):
            SemanticTraversal(contract).traverse(
                "hasRelevantArchitecture", by_id["req-1"], _f3_elements()
            )
    finally:
        broken_path.unlink(missing_ok=True)


def test_impact_reports_function_category_and_split_architecture_gaps(
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
            "@id": "kernel-member-product",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
        },
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
        {
            "@id": "action-request-braking",
            "@type": "ActionUsage",
            "declaredName": "requestBraking",
        },
        {
            "@id": "dep-specifies-function",
            "@type": "Dependency",
            "source": [ref("req-braking")],
            "target": [ref("action-request-braking")],
        },
        {
            "@id": "part-aeb-node",
            "@type": "PartUsage",
            "declaredName": "aebNode",
        },
        {
            "@id": "dep-from-architecture",
            "@type": "Dependency",
            "source": [ref("part-aeb-node")],
            "target": [ref("req-braking")],
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
            "ontology": _contract().identity.to_dict(),
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
    assert "specifiesFunction" in predicates
    assert "hasRelevantArchitecture" in predicates
    categories = {node["category"] for node in result["nodes"]}
    assert "function" in categories
    assert "architecture" in categories
    gap_categories = {gap["category"] for gap in result["gaps"]}
    # Relevance edges exist, so the full architecture gap is absent...
    assert "architecture" not in gap_categories
    # ...but missing allocation is still reported honestly as its own gap.
    assert "architecture-allocation" in gap_categories
    # Function relevance exists, so no function gap.
    assert "function" not in gap_categories


def test_impact_reports_function_gap_when_no_function_relevance(
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
            "@id": "kernel-member-product",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
        },
        {
            "@id": "kernel-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
        },
        {
            "@id": "req-lonely",
            "@type": "RequirementUsage",
            "declaredName": "reqNoFunctionTrace",
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
            "ontology": _contract().identity.to_dict(),
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
    result = service.impact("reqNoFunctionTrace", git_revision="a" * 40)

    gap_categories = {gap["category"] for gap in result["gaps"]}
    assert "function" in gap_categories
    assert "architecture" in gap_categories