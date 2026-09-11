"""K derivation traversal over the post-Lane-B ``include_implied`` graph.

Lane B enabled ``SerializationOptions.include_implied`` for the licensed
export, so the ingested listing carries tool-implied relationships and may
carry references inlined on their elements. These tests pin K's provenance
discipline on that graph shape:

* an AUTHORED discriminator typing is required — a tool-implied typing never
  stands in for an authored derivation assertion;
* representation tolerance: an inlined typing reference still grounds the
  discriminator (object and inlined shapes are both first-class);
* implied library noise (the real ``Subclassification``/``Subsetting``
  objects with inline ``@uri`` anchors that Lane B's fixture shows) neither
  creates nor widens a derivation;
* role classification may fall back to tool-implied lineage and SAYS SO in
  the witness instead of silently reporting an authored fact.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.traversal import SemanticTraversal
from de4sdv.sysml_api.revisions import KernelElementBinding

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

LIB_URI = "https://www.omg.org/spec/SysML/20250201/sysml.library/Systems%20Library/VerificationCases.sysml"
LIB_ANCHOR = "lib-verification-case-anchor"

NEED_DEF_ID = "nd-graph-0001"
REQ_DEF_ID = "rd-graph-0002"
DEF_ID = "conn-def-graph-0003"
NEED_ID = "need-graph-0004"
REQ_ID = "req-graph-0005"
CONN_ID = "conn-graph-0006"
DEF_END_NEED = "def-end-need-graph-0007"
DEF_END_REQ = "def-end-req-graph-0008"



def _contract() -> KernelContract:
    return KernelContract.load(ROOT / CONTRACT_PATH)


def _binding_index() -> KernelBindingIndex:
    class _B:
        kernel_bindings = [
            KernelElementBinding(
                ontology_class="DerivesFromNeed",
                element_id=DEF_ID,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="connection def DerivesFromNeed",
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

    return KernelBindingIndex.from_binding(_B())


def _typing(typing_id: str, feature_id: str, type_id: str, implied: bool = False) -> dict:
    element = {
        "@id": typing_id,
        "@type": "FeatureTyping",
        "owningRelatedElement": {"@id": feature_id},
        "typedFeature": {"@id": feature_id},
        "type": {"@id": type_id},
    }
    if implied:
        element["isImplied"] = True
        element["isImpliedIncluded"] = True
    return element


def _implied_library_noise() -> list[dict]:
    """Lane B's real shape: implied library anchors with inline @uri."""
    return [
        {
            "@id": "implied-subclassification-noise",
            "@type": "Subclassification",
            "isImplied": True,
            "isImpliedIncluded": True,
            "subclassifier": {"@id": REQ_DEF_ID},
            "specific": {"@id": REQ_DEF_ID},
            "owningRelatedElement": {"@id": REQ_DEF_ID},
            "superclassifier": {"@id": LIB_ANCHOR, "@uri": LIB_URI},
            "general": {"@id": LIB_ANCHOR, "@uri": LIB_URI},
        },
        {
            "@id": "implied-subsetting-noise",
            "@type": "Subsetting",
            "isImplied": True,
            "isImpliedIncluded": True,
            "subsettingFeature": {"@id": REQ_ID},
            "specific": {"@id": REQ_ID},
            "owningRelatedElement": {"@id": REQ_ID},
            "subsettedFeature": {"@id": LIB_ANCHOR, "@uri": LIB_URI},
        },
    ]


def _base_elements(
    *,
    discriminator_typing: str = "authored",
    end_typing: str = "authored",
    definition_shape: str = "graph",
) -> list[dict]:
    """Build the slice fixture.

    ``discriminator_typing``: ``authored`` | ``implied`` | ``inlined``
    ``end_typing``: ``authored`` | ``implied``
    ``definition_shape``: ``graph`` (EndFeatureMembership + FeatureTyping) or
    ``owned-member`` (ownedMember + inlined variant).
    """
    elements: list[dict] = [
        {"@id": NEED_DEF_ID, "@type": "RequirementDefinition", "declaredName": "StakeholderNeedCandidate"},
        {"@id": REQ_DEF_ID, "@type": "RequirementDefinition", "declaredName": "RequirementCandidate"},
        {
            "@id": DEF_ID,
            "@type": "ConnectionDefinition",
            "declaredName": "DerivesFromNeed",
            "ownedRelationship": [
                {"@id": "def-end-membership-need"},
                {"@id": "def-end-membership-req"},
            ],
            "documentation": [{"@id": "def-doc-graph"}],
        },
        {
            "@id": "def-end-membership-need",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": {"@id": DEF_ID},
            "ownedRelatedElement": [{"@id": DEF_END_NEED}],
        },
        {
            "@id": "def-end-membership-req",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": {"@id": DEF_ID},
            "ownedRelatedElement": [{"@id": DEF_END_REQ}],
        },
        {"@id": DEF_END_NEED, "@type": "ReferenceUsage", "declaredName": "need"},
        {"@id": DEF_END_REQ, "@type": "ReferenceUsage", "declaredName": "derivedRequirement"},
        _typing("def-end-need-typing", DEF_END_NEED, NEED_DEF_ID),
        _typing("def-end-req-typing", DEF_END_REQ, REQ_DEF_ID),
        {
            "@id": "def-doc-graph",
            "@type": "Documentation",
            "body": "Design-input provenance: the derivedRequirement "
            "originates from the stakeholder need. Provenance/traceability "
            "semantics only: neither satisfaction nor logical implication "
            "between the connected usages is claimed; verification, "
            "evidence, and acceptance claims are out of scope.",
        },
        {"@id": NEED_ID, "@type": "RequirementUsage", "declaredName": "needCommonAEBSCapability"},
        {"@id": REQ_ID, "@type": "RequirementUsage", "declaredName": "reqCommandEmergencyBraking"},
        _typing("need-typing", NEED_ID, NEED_DEF_ID, implied=end_typing == "implied"),
        _typing("req-typing", REQ_ID, REQ_DEF_ID, implied=end_typing == "implied"),
        {
            "@id": CONN_ID,
            "@type": "ConnectionUsage",
            "declaredName": "reqCommandEmergencyBrakingDerivation",
            "ownedRelationship": [{"@id": "conn-end-membership-need"}, {"@id": "conn-end-membership-req"}],
        },
        {
            "@id": "conn-end-membership-need",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": {"@id": CONN_ID},
            "ownedRelatedElement": [{"@id": NEED_ID}],
        },
        {
            "@id": "conn-end-membership-req",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": {"@id": CONN_ID},
            "ownedRelatedElement": [{"@id": REQ_ID}],
        },
    ]
    if discriminator_typing == "authored":
        elements.append(_typing("conn-def-typing", CONN_ID, DEF_ID))
    elif discriminator_typing == "implied":
        elements.append(_typing("conn-def-typing", CONN_ID, DEF_ID, implied=True))
    elif discriminator_typing == "inlined":
        by_id = {element["@id"]: element for element in elements}
        by_id[CONN_ID]["type"] = [{"@id": DEF_ID}]
    if definition_shape == "owned-member":
        elements = [
            element
            for element in elements
            if element["@id"] not in {"def-end-membership-need", "def-end-membership-req"}
        ]
        by_id = {element["@id"]: element for element in elements}
        by_id[DEF_ID]["ownedRelationship"] = [{"@id": "def-doc-graph"}]
        by_id[DEF_ID]["ownedMember"] = [{"@id": DEF_END_NEED}, {"@id": DEF_END_REQ}]
    # Implied library noise is always present, as in the real artifact.
    elements.extend(_implied_library_noise())
    return elements


def _traverse(elements: list[dict]):
    traversal = SemanticTraversal(_contract(), kernel_bindings=_binding_index())
    source = {"@id": REQ_ID, "@type": "RequirementUsage", "declaredName": "reqCommandEmergencyBraking"}
    return traversal.traverse("derivesRequirementFromNeed", source, elements)


def test_authored_typing_with_implied_library_noise_yields_one_edge() -> None:
    hops = _traverse(_base_elements())
    assert len(hops) == 1
    assert hops[0].target["@id"] == NEED_ID
    witness = hops[0].witness
    assert witness["definition_typing_provenance"] == "authored"
    assert witness["role_lineage_provenance"] == "explicit"
    assert witness["need_end_id"] == [NEED_ID]
    assert witness["derived_requirement_end_id"] == [REQ_ID]


def test_implied_only_discriminator_typing_is_quiet_absence() -> None:
    """A tool-implied typing is not an authored derivation assertion."""
    assert _traverse(_base_elements(discriminator_typing="implied")) == []


def test_inlined_typing_reference_still_grounds_the_discriminator() -> None:
    """Representation tolerance: inlined typing carries the same fact."""
    hops = _traverse(_base_elements(discriminator_typing="inlined"))
    assert len(hops) == 1
    assert hops[0].witness["definition_typing_provenance"] == "authored"


def test_implied_only_end_typing_records_the_fallback() -> None:
    hops = _traverse(_base_elements(end_typing="implied"))
    assert len(hops) == 1
    assert hops[0].witness["role_lineage_provenance"] == "implied-fallback"


def test_implied_library_noise_alone_never_creates_a_derivation() -> None:
    """Only implied relationships on an untyped connection: no edge, no error."""
    elements = [
        element
        for element in _base_elements(discriminator_typing="none")
        if element["@id"] != "conn-def-typing"
    ]
    assert _traverse(elements) == []


def test_definition_owned_member_shape_still_resolves() -> None:
    hops = _traverse(_base_elements(definition_shape="owned-member"))
    assert len(hops) == 1


def test_projection_resolves_definition_ends_from_the_graph() -> None:
    """The projection's model authority reads the same graph shapes."""
    from de4sdv.semantic.projection import (
        RevisionIdentity,
        build_projection,
    )

    elements = _base_elements()
    by_id = {element["@id"]: element for element in elements}
    projection = build_projection(
        _contract(),
        _binding_index(),
        RevisionIdentity("0" * 40, "proj", "commit"),
        by_id,
        repository_root=ROOT,
    )
    predicate = projection["predicate"]
    assert predicate["domain"] == "Requirement"
    assert predicate["range"] == "Need"
    authority = projection["revision_binding"]["generated_from"]["model_semantic_authority"]
    assert authority["need_end_type"] == "StakeholderNeedCandidate"
    assert authority["requirement_end_type"] == "RequirementCandidate"
    assert authority["end_type_provenance"] == "explicit"
    assert predicate["support_state"] == "vocabulary-only"


def test_implied_subclassification_cannot_ground_an_unknown_end() -> None:
    """R1 preserved on the implied graph: an end with no Requirement grounding
    still fails closed, and implied library classification of an unrelated
    element does not rescue it."""
    from de4sdv.sysml_api.errors import IdentityNotFoundError

    elements = _base_elements()
    by_id = {element["@id"]: element for element in elements}
    stranger = {"@id": "stranger-usage", "@type": "RequirementUsage", "declaredName": "unrelated"}
    elements.append(stranger)
    by_id["conn-end-membership-req"]["ownedRelatedElement"] = [{"@id": "stranger-usage"}]
    with pytest.raises(IdentityNotFoundError):
        _traverse(elements)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
