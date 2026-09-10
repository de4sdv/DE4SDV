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

from de4sdv.sysml_api.errors import IdentityNotFoundError

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
REQ_DEF_ID = "reqdef-uuid-0021"
NEED_DEF_ID = "needdef-uuid-0022"


def _element_listing() -> list[dict]:
    """Realistic deployed-baseline shapes for the derivation slice.

    Includes the Requirement/Need definition groundings and FeatureTyping
    lineage witnesses the predicate enforces (R1), plus the full discriminator
    witness chain (R2).
    """
    return [
        {
            "@id": REQ_ID,
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
            "ownedRelationship": [{"@id": "req-typing"}],
        },
        {
            "@id": "req-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": {"@id": REQ_ID},
            "typedFeature": {"@id": REQ_ID},
            "type": {"@id": REQ_DEF_ID},
        },
        {
            "@id": NEED_ID,
            "@type": "RequirementUsage",
            "declaredName": "needCommonAEBSCapability",
            "ownedRelationship": [{"@id": "need-typing"}],
        },
        {
            "@id": "need-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": {"@id": NEED_ID},
            "typedFeature": {"@id": NEED_ID},
            "type": {"@id": NEED_DEF_ID},
        },
        {
            "@id": OTHER_REQ_ID,
            "@type": "RequirementUsage",
            "declaredName": "reqAllowDriverOverride",
            "ownedRelationship": [{"@id": "other-typing"}],
        },
        {
            "@id": "other-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": {"@id": OTHER_REQ_ID},
            "typedFeature": {"@id": OTHER_REQ_ID},
            "type": {"@id": REQ_DEF_ID},
        },
        {
            "@id": REQ_DEF_ID,
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
        },
        {
            "@id": NEED_DEF_ID,
            "@type": "RequirementDefinition",
            "declaredName": "StakeholderNeedCandidate",
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
            ),
            KernelElementBinding(
                ontology_class="Requirement",
                element_id=REQ_DEF_ID,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="requirement def RequirementCandidate",
            ),
            KernelElementBinding(
                ontology_class="Need",
                element_id=NEED_DEF_ID,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="requirement def StakeholderNeedCandidate",
            ),
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


# ---------------------------------------------------------------------------
# R1/R2 adversarial service-level tests: every broken witness / out-of-lineage
# endpoint must fail closed (IdentityNotFoundError), never yield a quiet edge.
# ---------------------------------------------------------------------------


def _mutated_listing(mutate) -> list[dict]:
    import copy

    listing = copy.deepcopy(_element_listing())
    by_id = {item["@id"]: item for item in listing}
    mutate(listing, by_id)
    return listing


def _service_with_listing(elements: list[dict]) -> SemanticQueryService:
    """Build the service around one specific element listing."""
    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    binding = _BindingStub(contract.identity)
    kernel_bindings = KernelBindingIndex.from_binding(binding)
    repository = _RepositoryStub(elements)
    binder = OntologyApiBinder(
        contract,
        repository,  # type: ignore[arg-type]
        project_id=PROJECT_ID,
        commit_id=COMMIT_ID,
        kernel_bindings=kernel_bindings,
    )
    traversal = SemanticTraversal(contract, kernel_bindings=kernel_bindings)
    return SemanticQueryService(
        repository=repository,  # type: ignore[arg-type]
        binding=binding,  # type: ignore[arg-type]
        contract=contract,
        binder=binder,
        traversal=traversal,
        impact_service=ImpactService(
            repository=repository,  # type: ignore[arg-type]
            binding=binding,  # type: ignore[arg-type]
            contract=contract,
            binder=binder,
            traversal=traversal,
        ),
        expected_git_revision=GIT_COMMIT,
    )


def _assert_fail_closed(mutate, case: str) -> None:
    service = _service_with_listing(_mutated_listing(mutate))
    with pytest.raises(IdentityNotFoundError):
        service.semantic_neighbors(
            "reqCommandEmergencyBraking",
            predicates=["derivesRequirementFromNeed"],
        )


def test_missing_metadata_usage_fails_closed() -> None:
    def mutate(listing, by_id):
        listing[:] = [e for e in listing if e["@id"] != MARKER_USAGE_ID]

    _assert_fail_closed(mutate, "missing_metadata_usage")


def test_wrong_metadata_usage_type_fails_closed() -> None:
    def mutate(listing, by_id):
        by_id[MARKER_USAGE_ID]["@type"] = "PartUsage"

    _assert_fail_closed(mutate, "wrong_metadata_type")


def test_missing_dependency_ownership_fails_closed() -> None:
    def mutate(listing, by_id):
        by_id[DEP_ID]["ownedRelationship"] = []

    _assert_fail_closed(mutate, "missing_dependency_ownership")


def test_contradictory_annotation_owner_fails_closed() -> None:
    def mutate(listing, by_id):
        by_id[ANN_ID]["owningRelatedElement"] = {"@id": BARE_DEP_ID}

    _assert_fail_closed(mutate, "contradictory_annotation_owner")


def test_out_of_lineage_target_fails_closed() -> None:
    """R1: an unrelated RequirementUsage target does not satisfy the Need
    range even though the marker witness is intact."""
    import copy

    def mutate(listing, by_id):
        # The target loses its Need lineage typing and points at an
        # unrelated requirement definition instead.
        by_id["need-typing"]["type"] = {"@id": REQ_DEF_ID}
        by_id[NEED_ID]["ownedRelationship"] = [{"@id": "out-typing"}]
        listing.append(
            {
                "@id": "out-typing",
                "@type": "FeatureTyping",
                "owningRelatedElement": {"@id": NEED_ID},
                "typedFeature": {"@id": NEED_ID},
                "type": {"@id": REQ_DEF_ID},
            }
        )

    _assert_fail_closed(mutate, "out_of_lineage_target")


def test_valid_witness_alongside_broken_one_still_proves_valid() -> None:
    """A valid witness must survive when an unrelated dependency's witness
    is broken: fail-closed applies to the corrupted edge, not the whole
    predicate (per-edge closure, not global denial)."""
    import copy

    listing = copy.deepcopy(_element_listing())
    by_id = {item["@id"]: item for item in listing}
    # Break nothing on DEP_ID; the empty result for the unrelated bare
    # dependency remains a quiet absence (no witness to corrupt).
    service = _service()
    result = service.semantic_neighbors(
        "reqCommandEmergencyBraking",
        predicates=["derivesRequirementFromNeed"],
    )
    assert [edge["api_object_id"] for edge in result["edges"]] == [DEP_ID]
    assert result["edges"][0]["witness"]["marker_usage_ids"] == [
        MARKER_USAGE_ID
    ]
