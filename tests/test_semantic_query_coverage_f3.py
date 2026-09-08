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


def _kernel_ownership():
    """OwningMembership evidence placing kernel definitions in their packages.

    Real SysML API exports carry no populated owner fields; ownership is the
    OwningMembership graph. Kernel definitions used by runtime binding must
    be owned by the package path the governed kernel file declares.
    """
    ref = lambda value: {"@id": value}
    return [
        {
            "@id": "pkg-product-line",
            "@type": "Package",
            "declaredName": "DE4SDV_ProductLine",
        },
        {
            "@id": "om-kernel-member-product",
            "@type": "OwningMembership",
            "memberElement": ref("kernel-member-product"),
            "owningRelatedElement": ref("pkg-product-line"),
        },
        {
            "@id": "pkg-method-context",
            "@type": "Package",
            "declaredName": "DE4SDV_MethodContext",
        },
        {
            "@id": "om-kernel-requirement",
            "@type": "OwningMembership",
            "memberElement": ref("kernel-requirement"),
            "owningRelatedElement": ref("pkg-method-context"),
        },
    ]


def _f3_elements():
    """Minimal API-shaped fixture covering both new predicates.

    Shapes: Dependency with source/target reference lists; Subclassification
    with subclassifier/superclassifier; FeatureTyping with
    owningRelatedElement/type.
    """
    ref = lambda value: {"@id": value}
    return [
        *_kernel_ownership(),
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
    # The exclusion names the governed ONTOLOGY class; traversal resolves its
    # canonical SysML identity through the kernel mapping, never by bare name.
    assert (
        architecture_mapping.configuration["exclude_source_specializations_of"]
        == "MemberProduct"
    )
    kernel = contract.class_mapping("MemberProduct")
    assert kernel.declaration == "part def ProductLineMemberProduct"
    assert kernel.file.endswith("de4sdv_product_line.sysml")


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
        *_kernel_ownership(),
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
        with pytest.raises(KeyError, match="no kernel mapping"):
            SemanticTraversal(contract).traverse(
                "hasRelevantArchitecture", by_id["req-1"], _f3_elements()
            )
    finally:
        broken_path.unlink(missing_ok=True)


def test_exclusion_fails_closed_on_unrelated_homonym_definition() -> None:
    """An unrelated same-named definition must not widen the exclusion.

    With the canonical kernel definition present, the homonym is rejected
    by package-path grounding (not by ambiguity): exactly one candidate is
    owned by the governed package, so the canonical element grounds and the
    unrelated-homonym-typed usage keeps flowing as architecture.
    """
    from de4sdv.semantic.traversal import SemanticTraversal

    ref = lambda value: {"@id": value}
    elements = _f3_elements() + [
        # Unrelated package's definition with the kernel's declared name.
        {
            "@id": "pkg-other",
            "@type": "Package",
            "declaredName": "OtherPackage",
        },
        {
            "@id": "om-homonym",
            "@type": "OwningMembership",
            "memberElement": ref("homonym-def"),
            "owningRelatedElement": ref("pkg-other"),
        },
        {
            "@id": "homonym-def",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
            "qualifiedName": "OtherPackage::ProductLineMemberProduct",
        },
        # A legitimate architecture element typed by that unrelated homonym.
        {
            "@id": "legit-typed-by-homonym",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("plain-homonym-usage"),
            "type": ref("homonym-def"),
        },
        {
            "@id": "plain-homonym-usage",
            "@type": "PartUsage",
            "declaredName": "legitPart",
        },
        {
            "@id": "dep-from-homonym-usage",
            "@type": "Dependency",
            "source": [ref("plain-homonym-usage")],
            "target": [ref("req-1")],
        },
    ]
    requirement = next(item for item in elements if item["@id"] == "req-1")
    hops = SemanticTraversal(_contract()).traverse(
        "hasRelevantArchitecture", requirement, elements
    )
    targets = sorted(hop.target["@id"] for hop in hops)
    # The canonical kernel element still grounds (the unrelated homonym in
    # another package cannot borrow the mapping), so the homonym-typed
    # legitimate usage is NOT excluded.
    assert "plain-homonym-usage" in targets
    assert "configured-member-usage" not in targets


def test_exclusion_fails_closed_when_kernel_definition_is_absent() -> None:
    """A model lacking the kernel definition must fail closed, not pass open."""
    from de4sdv.semantic.traversal import SemanticTraversal

    ref = lambda value: {"@id": value}
    elements = [item for item in _f3_elements() if item["@id"] != "kernel-member-product"]
    # Keep a Subclassification pointing at the now-missing kernel so the
    # failure is not simply an empty lineage.
    elements.append(
        {
            "@id": "orphan-sub",
            "@type": "Subclassification",
            "subclassifier": ref("configured-member-def"),
            "superclassifier": ref("kernel-member-product"),
        }
    )
    requirement = next(item for item in elements if item["@id"] == "req-1")
    with pytest.raises(Exception, match="resolved to no"):
        SemanticTraversal(_contract()).traverse(
            "hasRelevantArchitecture", requirement, elements
        )


def test_exclusion_fails_closed_when_canonical_missing_but_homonym_survives() -> None:
    """The decisive combined case: no canonical root, one unrelated homonym.

    Removing the governed kernel definition while an unrelated
    OtherPackage::ProductLineMemberProduct (which legitimately types a
    real architecture element) remains must fail closed. It must NOT
    borrow the homonym as the exclusion root: that would suppress the
    legitimate architecture trace and admit configured-product usages.
    """
    from de4sdv.semantic.traversal import SemanticTraversal

    ref = lambda value: {"@id": value}
    elements = [
        item for item in _f3_elements() if item["@id"] != "kernel-member-product"
    ]
    elements += [
        # Unrelated package's same-named definition that genuinely types a
        # legitimate architecture element.
        {
            "@id": "pkg-other",
            "@type": "Package",
            "declaredName": "OtherPackage",
        },
        {
            "@id": "om-homonym",
            "@type": "OwningMembership",
            "memberElement": ref("homonym-def"),
            "owningRelatedElement": ref("pkg-other"),
        },
        {
            "@id": "homonym-def",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
            "qualifiedName": "OtherPackage::ProductLineMemberProduct",
        },
        {
            "@id": "ft-legit",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("part-translator"),
            "type": ref("homonym-def"),
        },
        # Subclassification chain pointing at the missing canonical root.
        {
            "@id": "orphan-sub",
            "@type": "Subclassification",
            "subclassifier": ref("configured-member-def"),
            "superclassifier": ref("kernel-member-product"),
        },
    ]
    requirement = next(item for item in elements if item["@id"] == "req-1")
    # The homonym is the only type/name candidate, but it is owned by
    # OtherPackage, not the governed DE4SDV_ProductLine package: fail
    # closed with the grounding diagnostic instead of silently borrowing.
    with pytest.raises(Exception, match="none owned by package path"):
        SemanticTraversal(_contract()).traverse(
            "hasRelevantArchitecture", requirement, elements
        )


def test_bind_class_fails_closed_when_canonical_missing_but_homonym_survives(
    api_server_fixture,
) -> None:
    """The binder shares the grounding contract: a surviving homonym in
    another package must not substitute for the missing canonical root."""
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository

    ref = lambda value: {"@id": value}
    elements = [
        {
            "@id": "pkg-other",
            "@type": "Package",
            "declaredName": "OtherPackage",
        },
        {
            "@id": "om-homonym",
            "@type": "OwningMembership",
            "memberElement": ref("homonym-def"),
            "owningRelatedElement": ref("pkg-other"),
        },
        {
            "@id": "homonym-def",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
            "qualifiedName": "OtherPackage::ProductLineMemberProduct",
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
    binder = OntologyApiBinder(
        _contract(), SysMLRepository(ApiClient(base_url)), project_id="project-1", commit_id="commit-1"
    )
    with pytest.raises(Exception, match="none owned by package path"):
        binder.bind_class("MemberProduct")


def test_member_product_definition_sources_are_excluded() -> None:
    """A dependency sourced by a lineage definition is product structure."""
    from de4sdv.semantic.traversal import SemanticTraversal

    ref = lambda value: {"@id": value}
    elements = _f3_elements() + [
        {
            "@id": "dep-from-configured-member-def",
            "@type": "Dependency",
            "source": [ref("configured-member-def")],
            "target": [ref("req-1")],
        },
        # A definition specialized only through the (already excluded)
        # intermediate definition is also product structure.
        {
            "@id": "leaf-member-def",
            "@type": "PartDefinition",
            "declaredName": "LeafMember",
        },
        {
            "@id": "sub-leaf-def",
            "@type": "Subclassification",
            "subclassifier": ref("leaf-member-def"),
            "superclassifier": ref("configured-member-def"),
        },
        {
            "@id": "dep-from-leaf-def",
            "@type": "Dependency",
            "source": [ref("leaf-member-def")],
            "target": [ref("req-1")],
        },
    ]
    requirement = next(item for item in elements if item["@id"] == "req-1")
    hops = SemanticTraversal(_contract()).traverse(
        "hasRelevantArchitecture", requirement, elements
    )
    targets = sorted(hop.target["@id"] for hop in hops)
    # Only the legitimate part/action sources remain; both lineage
    # definitions (direct and transitive) are excluded.
    assert targets == ["action-def-flow", "part-translator"]


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
        *_kernel_ownership(),
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
        *_kernel_ownership(),
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


def test_impact_preserves_function_role_on_shared_architecture_node(
    api_server_fixture,
) -> None:
    """One element with both function and architecture roles keeps both."""
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.impact import ImpactService
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository
    from de4sdv.sysml_api.revisions import RevisionBinding

    ref = lambda value: {"@id": value}
    elements = [
        *_kernel_ownership(),
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
        # The same action is BOTH the outgoing function target and the
        # incoming architecture source (distinct dependency objects).
        {
            "@id": "dep-specifies-function",
            "@type": "Dependency",
            "source": [ref("req-braking")],
            "target": [ref("action-request-braking")],
        },
        {
            "@id": "dep-from-architecture",
            "@type": "Dependency",
            "source": [ref("action-request-braking")],
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
    assert predicates == {"specifiesFunction", "hasRelevantArchitecture"}
    action_nodes = [
        node
        for node in result["nodes"]
        if node["element_id"] == "action-request-braking"
    ]
    assert len(action_nodes) == 1
    node = action_nodes[0]
    # Both roles survive on the single shared node; the first-seen category
    # stays stable and the role list records the second.
    assert node["category"] == "function"
    assert sorted(node["categories"]) == ["architecture", "function"]


def test_impact_text_output_includes_function_category() -> None:
    """The public CLI formatter must render the function category."""
    from scripts import query_model_impact as qmi

    report = {
        "revision": {
            "git_commit": "a" * 40,
            "sysml_project_id": "project-1",
            "sysml_commit_id": "commit-1",
            "binding_status": "synchronized",
        },
        "root": {
            "qualified_name": None,
            "declared_name": "reqExample",
            "element_id": "req-1",
        },
        "nodes": [
            {
                "element_id": "action-translate",
                "qualified_name": None,
                "declared_name": "translateSignal",
                "category": "function",
                "categories": ["function"],
            }
        ],
        "gaps": [],
    }
    text = qmi._render_api_text(report)
    assert "function: 1" in text
    assert "translateSignal" in text