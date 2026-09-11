"""Tests for the v1.1 reconciliation: native Derivation connection representation.

The predicate is carried by a ConnectionUsage typed by the pinned library's
DerivesFromNeed application definition. Ends are identified by role:
need (the Need side) vs derivedRequirement (the derived
Requirement side). DE4SDV's Requirement -> Need query is inverse navigation
over the same witness. All fail-closed contracts from the R1-R5 repair are
preserved.

Shapes follow the SysML v2 abstract syntax: ConnectionUsage with
`connectionEnd` references (ConnectorEnd members), owned by the enclosing
namespace, typed by the Derivation ConnectionDefinition.
"""

from __future__ import annotations

import pytest

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.traversal import SemanticTraversal

ROOT = None  # set in _contract via package path below

CONTRACT_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

REQ_ID = "req-uuid-0001"
NEED_ID = "need-uuid-0002"
CONN_ID = "conn-uuid-0003"
DEF_DERIV_ID = "lib-derivation-def-0006"
END_ORIG_ID = "end-original-0007"
END_DERIVED_ID = "end-derived-0008"
NEED_DEF_ID = "needdef-uuid-0022"
REQ_DEF_ID = "reqdef-uuid-0021"


def _contract() -> KernelContract:
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    return KernelContract.load(root / CONTRACT_PATH)


def _binding_entry(ontology_class, element_id, declaration):
    from de4sdv.sysml_api.revisions import KernelElementBinding

    return KernelElementBinding(
        ontology_class=ontology_class,
        element_id=element_id,
        source_file="textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
        declaration=declaration,
    )


def _default_binding_entries() -> list:
    return [
        _binding_entry(
            "DerivesFromNeed", DEF_DERIV_ID,
            "connection def DerivesFromNeed",
        ),
        _binding_entry(
            "Requirement", REQ_DEF_ID,
            "requirement def RequirementCandidate",
        ),
        _binding_entry(
            "Need", NEED_DEF_ID,
            "requirement def StakeholderNeedCandidate",
        ),
    ]


class _Binding:
    def __init__(self, entries) -> None:
        self.kernel_bindings = entries


def _binding_index(entries=None) -> KernelBindingIndex:
    if entries is None:
        entries = _default_binding_entries()
    return KernelBindingIndex.from_binding(_Binding(entries))


def _requirement() -> dict:
    return {
        "@id": REQ_ID,
        "@type": "RequirementUsage",
        "declaredName": "reqCommandEmergencyBraking",
        "ownedRelationship": [{"@id": "req-typing"}],
    }


def _need() -> dict:
    return {
        "@id": NEED_ID,
        "@type": "RequirementUsage",
        "declaredName": "needCommonAEBSCapability",
        "ownedRelationship": [{"@id": "need-typing"}],
    }


def _requirement_typing() -> dict:
    return {
        "@id": "req-typing",
        "@type": "FeatureTyping",
        "owningRelatedElement": {"@id": REQ_ID},
        "typedFeature": {"@id": REQ_ID},
        "type": {"@id": REQ_DEF_ID},
    }


def _need_typing() -> dict:
    return {
        "@id": "need-typing",
        "@type": "FeatureTyping",
        "owningRelatedElement": {"@id": NEED_ID},
        "typedFeature": {"@id": NEED_ID},
        "type": {"@id": NEED_DEF_ID},
    }


def _definition_elements() -> list:
    return [
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
    ]


def _derivation_connection() -> dict:
    """Native Derivation ConnectionUsage: need = original end, req = derived end."""
    return {
        "@id": CONN_ID,
        "@type": "ConnectionUsage",
        "declaredName": "reqCommandEmergencyBrakingDerivation",
        "ownedRelationship": [
            {"@id": END_ORIG_ID},
            {"@id": END_DERIVED_ID},
            {"@id": "conn-typing"},
        ],
    }


def _connection_typing() -> dict:
    return {
        "@id": "conn-typing",
        "@type": "FeatureTyping",
        "owningRelatedElement": {"@id": CONN_ID},
        "typedFeature": {"@id": CONN_ID},
        "type": {"@id": DEF_DERIV_ID},
    }


def _end_original() -> dict:
    return {
        "@id": END_ORIG_ID,
        "@type": "EndFeatureMembership",
        "owningRelatedElement": {"@id": CONN_ID},
        "ownedRelatedElement": [{"@id": NEED_ID}],
    }


def _end_derived() -> dict:
    return {
        "@id": END_DERIVED_ID,
        "@type": "EndFeatureMembership",
        "owningRelatedElement": {"@id": CONN_ID},
        "ownedRelatedElement": [{"@id": REQ_ID}],
    }


def _definition_library_elements() -> list:
    """Model-resident authority: DerivesFromNeed definition with typed ends
    (need : StakeholderNeedCandidate, derivedRequirement : RequirementCandidate)
    and the role-binding/claim-boundary doc."""
    return [
        {
            "@id": DEF_DERIV_ID,
            "@type": "ConnectionDefinition",
            "declaredName": "DerivesFromNeed",
            "ownedMember": [
                {"@id": "def-end-need"},
                {"@id": "def-end-derived"},
            ],
            "documentation": [{"@id": "def-doc"}],
        },
        {
            "@id": "def-end-need",
            "@type": "ReferenceUsage",
            "declaredName": "need",
            "variant": {"@id": NEED_DEF_ID},
        },
        {
            "@id": "def-end-derived",
            "@type": "ReferenceUsage",
            "declaredName": "derivedRequirement",
            "variant": {"@id": REQ_DEF_ID},
        },
        {
            "@id": "def-doc",
            "@type": "Documentation",
            "body": "Design-input provenance: the derivedRequirement originates from "
            "the stakeholder need. Native direction: need -> "
            "derivedRequirement. Claim strength: derivation "
            "(provenance only: neither satisfaction nor logical "
            "implication between the connected usages; no "
            "allocation, verification, evidence, or acceptance claim).",
        },
    ]


def _elements() -> list:
    return [
        _requirement(),
        _need(),
        _requirement_typing(),
        _need_typing(),
        *_definition_elements(),
        *_definition_library_elements(),
        _derivation_connection(),
        _connection_typing(),
        _end_original(),
        _end_derived(),
    ]


def test_ontology_declares_native_derivation_connection_strategy() -> None:
    mapping = _contract().relationship_mapping("derivesRequirementFromNeed")
    assert mapping.strategy == "derivation-connection"
    assert mapping.semantic_strength == "derivation"
    assert mapping.configuration["connection_definition"] == "DerivesFromNeed"
    # Canonical DE4SDV query: Requirement -> Need = inverse of the native
    # need -> derivedRequirement direction.
    assert mapping.configuration["query_direction"] == "inverse"


def test_derivation_traversal_returns_requirement_to_need_edge() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    hops = traversal.traverse(
        "derivesRequirementFromNeed", _requirement(), _elements()
    )
    assert len(hops) == 1
    hop = hops[0]
    assert hop.target["@id"] == NEED_ID
    assert hop.api_object["@id"] == CONN_ID
    # Witness carries the model-native end-role identities.
    assert hop.witness["connection_definition"] == "DerivesFromNeed"
    assert hop.witness["need_end_id"] == [NEED_ID]
    assert hop.witness["derived_requirement_end_id"] == [REQ_ID]


def test_inverse_navigation_over_the_same_witness() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    inverse = traversal.traverse(
        "derivedRequirementsOfNeed", _need(), _elements()
    )
    assert len(inverse) == 1
    assert inverse[0].target["@id"] == REQ_ID
    assert inverse[0].api_object["@id"] == CONN_ID


def test_untyped_connection_is_not_a_derivation() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    elements = [e for e in _elements() if e["@id"] != "conn-typing"]
    assert traversal.traverse(
        "derivesRequirementFromNeed", _requirement(), elements
    ) == []


def test_generic_dependency_is_not_a_derivation() -> None:
    """UG-05: a generic Dependency with identical endpoint types is not
    satisfied by the native derivation predicate."""
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    generic = {
        "@id": "generic-dep",
        "@type": "Dependency",
        "declaredName": "someRelevanceTrace",
        "source": [{"@id": REQ_ID}],
        "target": [{"@id": NEED_ID}],
    }
    hops = traversal.traverse(
        "derivesRequirementFromNeed",
        _requirement(),
        [*_elements(), generic],
    )
    assert [h.api_object["@id"] for h in hops] == [CONN_ID]


def test_connection_typed_by_other_definition_is_quiet_absence() -> None:
    """A ConnectionUsage typed by a DIFFERENT definition never claimed this
    predicate: quiet absence (like an unmarked dependency), not a corrupted
    witness."""
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    wrong_type = _connection_typing()
    wrong_type["type"] = {"@id": "some-other-definition"}
    elements = [
        e if e["@id"] != "conn-typing" else wrong_type for e in _elements()
    ]
    assert traversal.traverse(
        "derivesRequirementFromNeed", _requirement(), elements
    ) == []


def test_missing_end_fails_closed() -> None:
    """A derivation connection missing the originalRequirement end has
    incomplete closure (UG-06): fail closed, never a quiet absence."""
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    elements = [
        e
        for e in _elements()
        if not (e["@id"] == CONN_ID and e is _derivation_connection())
    ]
    broken_connection = {
        "@id": CONN_ID,
        "@type": "ConnectionUsage",
        "declaredName": "brokenDerivation",
        "ownedRelationship": [
            {"@id": END_DERIVED_ID},
            {"@id": "conn-typing"},
        ],
    }
    elements = [
        broken_connection if e.get("@id") == CONN_ID else e for e in elements
    ]
    with pytest.raises(IdentityNotFoundError):
        traversal.traverse("derivesRequirementFromNeed", _requirement(), elements)


def test_out_of_lineage_derived_end_fails_closed() -> None:
    """R1 preserved: the derived end must ground in the Requirement lineage."""
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    stranger = {
        "@id": "stranger-req",
        "@type": "RequirementUsage",
        "declaredName": "someOtherRequirement",
    }
    swapped_end = {
        "@id": END_DERIVED_ID,
        "@type": "EndFeatureMembership",
        "owningRelatedElement": {"@id": CONN_ID},
        "ownedRelatedElement": [{"@id": "stranger-req"}],
    }
    elements = [
        e if e["@id"] != END_DERIVED_ID else swapped_end for e in _elements()
    ]
    elements.append(stranger)
    with pytest.raises(IdentityNotFoundError):
        traversal.traverse("derivesRequirementFromNeed", _requirement(), elements)


def test_missing_validated_library_binding_fails_closed() -> None:
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index([]))
    with pytest.raises(IdentityNotFoundError):
        traversal.traverse(
            "derivesRequirementFromNeed", _requirement(), _elements()
        )
