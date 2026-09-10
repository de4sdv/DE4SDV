"""Tests for the derivesRequirementFromNeed metadata-tagged-dependency slice.

Shapes are taken from the validated deployed baseline, where the same metadata
mechanism (``#AdapterExchangeExcluded`` dependencies) round-trips as
``Dependency -> Annotation -> MetadataUsage -> FeatureTyping -> MetadataDefinition``
with preserved UUIDs. The marker definition identity is consumed from an
ingestion-validated kernel binding, never from element names.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.revisions import KernelElementBinding
from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.traversal import SemanticTraversal

ROOT = Path(__file__).resolve().parents[1]

REQ_ID = "req-uuid-0001"
NEED_ID = "need-uuid-0002"
DEP_ID = "dep-uuid-0003"
ANN_ID = "ann-uuid-0004"
MARKER_USAGE_ID = "meta-uuid-0005"
MARKER_DEF_ID = "metadef-uuid-0006"


def _contract() -> KernelContract:
    return KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )


def _requirement() -> dict:
    return {
        "@id": REQ_ID,
        "@type": "RequirementUsage",
        "declaredName": "reqCommandEmergencyBraking",
    }


def _need() -> dict:
    return {
        "@id": NEED_ID,
        "@type": "RequirementUsage",
        "declaredName": "needCommonAEBSCapability",
    }


def _tagged_dependency() -> dict:
    """Dependency carrying the #RequirementDerivation marker witness."""
    return {
        "@id": DEP_ID,
        "@type": "Dependency",
        "declaredName": "reqCommandEmergencyBrakingDerivedFromCommonAEBSCapability",
        "source": [{"@id": REQ_ID}],
        "target": [{"@id": NEED_ID}],
        "ownedRelationship": [{"@id": ANN_ID}],
    }


def _annotation() -> dict:
    return {
        "@id": ANN_ID,
        "@type": "Annotation",
        "annotatedElement": {"@id": DEP_ID},
        "owningRelatedElement": {"@id": DEP_ID},
        "ownedRelatedElement": [{"@id": MARKER_USAGE_ID}],
    }


def _marker_usage() -> dict:
    return {
        "@id": MARKER_USAGE_ID,
        "@type": "MetadataUsage",
        "ownedRelationship": [{"@id": "ft-uuid-0007"}],
    }


def _marker_typing() -> dict:
    return {
        "@id": "ft-uuid-0007",
        "@type": "FeatureTyping",
        "typedFeature": {"@id": MARKER_USAGE_ID},
        "type": {"@id": MARKER_DEF_ID},
    }


def _marker_definition() -> dict:
    return {
        "@id": MARKER_DEF_ID,
        "@type": "MetadataDefinition",
        "declaredName": "RequirementDerivation",
    }


def _elements() -> list[dict]:
    return [
        _requirement(),
        _need(),
        _tagged_dependency(),
        _annotation(),
        _marker_usage(),
        _marker_typing(),
        _marker_definition(),
    ]


class _Binding:
    """Minimal revision binding carrying validated kernel bindings."""

    def __init__(self, entries: list[KernelElementBinding]) -> None:
        self.kernel_bindings = entries


def _binding_entry(
    ontology_class: str = "RequirementDerivation",
    declaration: str = "metadata def RequirementDerivation",
    element_id: str = MARKER_DEF_ID,
) -> KernelElementBinding:
    return KernelElementBinding(
        ontology_class=ontology_class,
        element_id=element_id,
        source_file=(
            "textual-notation-of-model/packages/methods/de4sdv/"
            "de4sdv_method_context.sysml"
        ),
        declaration=declaration,
    )


def _default_binding_entries() -> list[KernelElementBinding]:
    return [
        _binding_entry(),
    ]


def _binding_index(
    entries: list[KernelElementBinding] | None = None,
) -> KernelBindingIndex:
    if entries is None:
        entries = _default_binding_entries()
    return KernelBindingIndex.from_binding(_Binding(entries))


def test_ontology_declares_metadata_tagged_dependency_strategy() -> None:
    mapping = _contract().relationship_mapping("derivesRequirementFromNeed")
    assert mapping.strategy == "metadata-tagged-dependency"
    assert mapping.semantic_strength == "derivation"
    assert mapping.configuration["relationship_types"] == ["Dependency"]
    assert mapping.configuration["metadata_definition"] == "RequirementDerivation"
    assert mapping.configuration["direction"] == "outgoing"


def test_ontology_maps_marker_definition_to_kernel_metadata() -> None:
    mapping = _contract().class_mapping("RequirementDerivation")
    assert isinstance(mapping, object)
    assert mapping.declaration == "metadata def RequirementDerivation"


def test_derivation_traversal_resolves_tagged_dependency() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    hops = traversal.traverse(
        "derivesRequirementFromNeed", _requirement(), _elements()
    )
    assert len(hops) == 1
    hop = hops[0]
    assert hop.predicate == "derivesRequirementFromNeed"
    assert hop.semantic_strength == "derivation"
    assert hop.target["@id"] == NEED_ID
    assert hop.api_object["@id"] == DEP_ID


def test_unmarked_dependency_with_identical_endpoints_is_not_a_derivation() -> None:
    """UG-05: endpoint types alone never satisfy the stronger predicate."""
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    bare_dependency = {
        "@id": "bare-uuid-0009",
        "@type": "Dependency",
        "declaredName": "bicycleCriterionRelevantToBicycleResponseCandidate",
        "source": [{"@id": REQ_ID}],
        "target": [{"@id": NEED_ID}],
    }
    hops = traversal.traverse(
        "derivesRequirementFromNeed",
        _requirement(),
        [*_elements(), bare_dependency],
    )
    assert [hop.api_object["@id"] for hop in hops] == [DEP_ID]


def test_wrong_type_annotation_does_not_discriminate() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    untyped = list(_elements())
    # The marker usage is no longer typed by the marker definition.
    stale_typing = {
        "@id": "ft-uuid-0007",
        "@type": "FeatureTyping",
        "typedFeature": {"@id": MARKER_USAGE_ID},
        "type": {"@id": "some-other-definition"},
    }
    replaced = [
        stale_typing if item.get("@id") == "ft-uuid-0007" else item
        for item in untyped
    ]
    assert traversal.traverse("derivesRequirementFromNeed", _requirement(), replaced) == []


def test_missing_validated_marker_binding_fails_closed() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index([]))
    with pytest.raises(IdentityNotFoundError, match="RequirementDerivation"):
        traversal.traverse(
            "derivesRequirementFromNeed", _requirement(), _elements()
        )


def test_no_binding_index_at_all_fails_closed() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=None)
    with pytest.raises(IdentityNotFoundError):
        traversal.traverse(
            "derivesRequirementFromNeed", _requirement(), _elements()
        )


def test_missing_derivation_returns_empty_not_error() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    # A requirement with no derivation dependency at all: no tagged witness
    # exists for it, so the result is empty (an explicit gap, not a pass).
    other_requirement = {
        "@id": "req-other-0010",
        "@type": "RequirementUsage",
        "declaredName": "reqUnrelatedCandidate",
    }
    hops = traversal.traverse(
        "derivesRequirementFromNeed", other_requirement, _elements()
    )
    assert hops == []


def test_multiple_distinct_derivation_witnesses_are_all_returned() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    second_dep = {
        "@id": "dep-uuid-0011",
        "@type": "Dependency",
        "declaredName": "reqCommandEmergencyBrakingDerivedFromBoundedDegradation",
        "source": [{"@id": REQ_ID}],
        "target": [{"@id": "need-uuid-0012"}],
        "ownedRelationship": [{"@id": "ann-uuid-0013"}],
    }
    second_ann = {
        "@id": "ann-uuid-0013",
        "@type": "Annotation",
        "annotatedElement": {"@id": "dep-uuid-0011"},
        "owningRelatedElement": {"@id": "dep-uuid-0011"},
        "ownedRelatedElement": [{"@id": "meta-uuid-0014"}],
    }
    second_usage = {
        "@id": "meta-uuid-0014",
        "@type": "MetadataUsage",
        "ownedRelationship": [{"@id": "ft-uuid-0015"}],
    }
    second_typing = {
        "@id": "ft-uuid-0015",
        "@type": "FeatureTyping",
        "typedFeature": {"@id": "meta-uuid-0014"},
        "type": {"@id": MARKER_DEF_ID},
    }
    second_need = {
        "@id": "need-uuid-0012",
        "@type": "RequirementUsage",
        "declaredName": "needBoundedDegradationAndAvailability",
    }
    hops = traversal.traverse(
        "derivesRequirementFromNeed",
        _requirement(),
        [
            *_elements(),
            second_need,
            second_dep,
            second_ann,
            second_usage,
            second_typing,
        ],
    )
    assert sorted(hop.api_object["@id"] for hop in hops) == sorted([
        "dep-uuid-0011",
        DEP_ID,
    ])


def test_wrong_endpoint_type_is_filtered() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    # Supplier is a PartUsage (wrong type for the Need range).
    wrong_dependency = {
        "@id": "dep-uuid-0016",
        "@type": "Dependency",
        "declaredName": "taggedButWrongTypes",
        "source": [{"@id": REQ_ID}],
        "target": [{"@id": "part-uuid-0017"}],
        "ownedRelationship": [{"@id": "ann-uuid-0018"}],
    }
    wrong_ann = {
        "@id": "ann-uuid-0018",
        "@type": "Annotation",
        "annotatedElement": {"@id": "dep-uuid-0016"},
        "owningRelatedElement": {"@id": "dep-uuid-0016"},
        "ownedRelatedElement": [{"@id": "meta-uuid-0019"}],
    }
    wrong_usage = {
        "@id": "meta-uuid-0019",
        "@type": "MetadataUsage",
        "ownedRelationship": [{"@id": "ft-uuid-0020"}],
    }
    wrong_typing = {
        "@id": "ft-uuid-0020",
        "@type": "FeatureTyping",
        "typedFeature": {"@id": "meta-uuid-0019"},
        "type": {"@id": MARKER_DEF_ID},
    }
    wrong_target = {
        "@id": "part-uuid-0017",
        "@type": "PartUsage",
        "declaredName": "somePart",
    }
    hops = traversal.traverse(
        "derivesRequirementFromNeed",
        _requirement(),
        [
            *_elements(),
            wrong_target,
            wrong_dependency,
            wrong_ann,
            wrong_usage,
            wrong_typing,
        ],
    )
    assert [hop.api_object["@id"] for hop in hops] == [DEP_ID]


def test_kernel_binding_type_contradiction_is_detected() -> None:
    """A validated binding whose UUID has the wrong API type must fail closed."""
    index = _binding_index([_binding_entry(declaration="part def RequirementDerivation")])
    by_id = {item["@id"]: item for item in _elements()}
    with pytest.raises(IdentityNotFoundError, match="contradicting"):
        index.element_id_for("RequirementDerivation", by_id)
