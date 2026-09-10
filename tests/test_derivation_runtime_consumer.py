"""Runtime consumer proof for the derivation slice (in-process service).

The consumer is the real ``SemanticQueryService.semantic_neighbors`` path —
ontology contract, binder, traversal, revision binding, provenance echo —
exercised against realistic deployed-baseline shapes with a local HTTP stub
for the API element listing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from de4sdv.sysml_api.revisions import KernelElementBinding, OntologyIdentity
from de4sdv.semantic.api_binding import OntologyApiBinder
from de4sdv.semantic.impact import ImpactService
from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.query import SemanticQueryService
from de4sdv.semantic.traversal import SemanticTraversal

ROOT = Path(__file__).resolve().parents[1]

GIT_COMMIT = "a" * 40
PROJECT_ID = "proj-live-0001"
COMMIT_ID = "commit-live-0001"

REQ_ID = "req-uuid-0001"
NEED_ID = "need-uuid-0002"
DEP_ID = "dep-uuid-0003"
ANN_ID = "ann-uuid-0004"
MARKER_USAGE_ID = "meta-uuid-0005"
MARKER_DEF_ID = "metadef-uuid-0006"
OTHER_REQ_ID = "req-uuid-0030"
BARE_DEP_ID = "dep-uuid-0031"


def _element_listing() -> list[dict]:
    """Realistic deployed-baseline shapes for the derivation slice."""
    return [
        {
            "@id": REQ_ID,
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        },
        {
            "@id": NEED_ID,
            "@type": "RequirementUsage",
            "declaredName": "needCommonAEBSCapability",
        },
        {
            "@id": OTHER_REQ_ID,
            "@type": "RequirementUsage",
            "declaredName": "reqAllowDriverOverride",
        },
        {
            # UG-05 adversarial element: relevance dependency whose endpoints
            # are both RequirementUsage, carrying NO derivation marker.
            "@id": BARE_DEP_ID,
            "@type": "Dependency",
            "declaredName": "overrideEvidenceRelevantToOverrideCandidate",
            "source": [{"@id": OTHER_REQ_ID}],
            "target": [{"@id": NEED_ID}],
        },
        {
            "@id": DEP_ID,
            "@type": "Dependency",
            "declaredName": "reqCommandEmergencyBrakingDerivedFromCommonAEBSCapability",
            "source": [{"@id": REQ_ID}],
            "target": [{"@id": NEED_ID}],
            "ownedRelationship": [{"@id": ANN_ID}],
        },
        {
            "@id": ANN_ID,
            "@type": "Annotation",
            "annotatedElement": {"@id": DEP_ID},
            "owningRelatedElement": {"@id": DEP_ID},
            "ownedRelatedElement": [{"@id": MARKER_USAGE_ID}],
        },
        {
            "@id": MARKER_USAGE_ID,
            "@type": "MetadataUsage",
            "ownedRelationship": [{"@id": "ft-uuid-0007"}],
        },
        {
            "@id": "ft-uuid-0007",
            "@type": "FeatureTyping",
            "typedFeature": {"@id": MARKER_USAGE_ID},
            "type": {"@id": MARKER_DEF_ID},
        },
        {
            "@id": MARKER_DEF_ID,
            "@type": "MetadataDefinition",
            "declaredName": "RequirementDerivation",
        },
    ]


class _StubClient:
    """API client stub serving one element listing (no network)."""

    def __init__(self, elements: list[dict]) -> None:
        self._elements = elements

    def get(self, path: str, **kwargs):  # noqa: ANN003 - stub
        if "/elements" in path:
            return list(self._elements)
        raise AssertionError(f"unexpected API path {path!r}")


def _service() -> SemanticQueryService:
    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    binding = _BindingStub(contract.identity)
    kernel_bindings = KernelBindingIndex.from_binding(binding)
    binder = OntologyApiBinder(
        contract,
        _RepositoryStub(_element_listing()),  # type: ignore[arg-type]
        project_id=PROJECT_ID,
        commit_id=COMMIT_ID,
        kernel_bindings=kernel_bindings,
    )
    traversal = SemanticTraversal(contract, kernel_bindings=kernel_bindings)
    return SemanticQueryService(
        repository=binder.repository,  # type: ignore[arg-type]
        binding=binding,  # type: ignore[arg-type]
        contract=contract,
        binder=binder,
        traversal=traversal,
        impact_service=ImpactService(
            repository=binder.repository,  # type: ignore[arg-type]
            binding=binding,  # type: ignore[arg-type]
            contract=contract,
            binder=binder,
            traversal=traversal,
        ),
        expected_git_revision=GIT_COMMIT,
    )


class _BindingStub:
    """Revision binding stub carrying the validated kernel bindings."""

    def __init__(self, ontology_identity: OntologyIdentity) -> None:
        self.git_repository = "de4sdv/DE4SDV"
        self.git_commit = GIT_COMMIT
        self.sysml_project_id = PROJECT_ID
        self.sysml_commit_id = COMMIT_ID
        self.scope = "full-model"
        self.ontology = ontology_identity
        self.kernel_bindings = [
            KernelElementBinding(
                ontology_class="RequirementDerivation",
                element_id=MARKER_DEF_ID,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="metadata def RequirementDerivation",
            )
        ]

    def status(self, expected_git_revision: str) -> str:
        if expected_git_revision != self.git_commit:
            return "stale"
        return "synchronized"

    def require_current(self, git_revision: str) -> None:
        assert self.status(git_revision) == "synchronized"

    def require_ontology(self, ontology: OntologyIdentity) -> None:
        assert ontology == self.ontology


class _RepositoryStub:
    def __init__(self, elements: list[dict]) -> None:
        self._elements = elements

    def list_elements(self, project_id: str, commit_id: str) -> list[dict]:
        assert project_id == PROJECT_ID and commit_id == COMMIT_ID
        return self._elements


def test_runtime_consumer_returns_discriminated_derivation_edge() -> None:
    service = _service()
    result = service.semantic_neighbors(
        "reqCommandEmergencyBraking",
        predicates=["derivesRequirementFromNeed"],
    )
    assert result["edges"], "runtime consumer returned no derivation edge"
    edge = result["edges"][0]
    assert edge["predicate"] == "derivesRequirementFromNeed"
    assert edge["semantic_strength"] == "derivation"
    assert edge["api_object_type"] == "Dependency"
    assert edge["api_object_id"] == DEP_ID
    assert edge["source"] == REQ_ID
    assert edge["target"] == NEED_ID
    assert edge["provenance"].startswith(f"sysml://{PROJECT_ID}/{COMMIT_ID}/")
    # No gaps for the positive case.
    assert result["gaps"] == []


def test_runtime_consumer_does_not_fire_on_unmarked_dependency() -> None:
    service = _service()
    result = service.semantic_neighbors(
        "reqAllowDriverOverride",
        predicates=["derivesRequirementFromNeed"],
    )
    # The requirement exists and has a Requirement->Requirement dependency,
    # but without the marker the result must be an explicit gap, not an edge.
    assert result["edges"] == []
    assert result["gaps"], "absence was reported without an explicit gap"
    assert result["gaps"][0]["category"] == "derivesRequirementFromNeed"


def test_runtime_consumer_reports_unsupported_predicate_as_error() -> None:
    service = _service()
    with pytest.raises(KeyError, match="nonexistentPredicate"):
        service.semantic_neighbors(
            "reqCommandEmergencyBraking",
            predicates=["nonexistentPredicate"],
        )
