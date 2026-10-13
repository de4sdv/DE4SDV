"""Connection-end reader: minimized fixtures reproducing the real serializer shapes.

The privileged R6 run (34597175486, head 77e3c42) exposed reader defects,
all now repaired. This module pins the connection-end reader of the live
traversal against minimized fixtures that mirror the real serialized
representation:

* connection ends: ``EndFeatureMembership`` (memberName = role) -> synthesized
  end ``Feature`` (``isEnd``) -> authored ``ReferenceSubsetting`` -> connected
  engineering usage -> authored ``FeatureTyping`` -> candidate definition ->
  ``Subclassification*`` -> governed Need/Requirement lineage.

The definition-end and documentation readers belonged to the retired
derivation projection and are archived with it.

The model-side semantics are unchanged: this module tests READERS only.
"""

from __future__ import annotations

import sys

import pytest

from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.traversal import SemanticTraversal
from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.revisions import KernelElementBinding
from model_contract_fixtures import model_contract  # noqa: E402


NEED_DEF = "r6-needdef"
REQ_DEF = "r6-reqdef"
NEED_CAND = "r6-need-candidate"
REQ_CAND = "r6-req-candidate"
DEF = "r6-def"
DEF_END_NEED = "r6-def-end-need"
DEF_END_REQ = "r6-def-end-req"
DOC = "r6-doc"
DOC_MEMBERSHIP = "r6-doc-membership"

CLAIM_DOC = (
    "Design-input provenance: the derivedRequirement originates from the "
    "stakeholder need. Native direction: need -> derivedRequirement. "
    "Claim strength: derivation (provenance only: neither satisfaction nor "
    "logical implication between the connected usages; no allocation, "
    "verification, evidence, or acceptance claim)."
)

CASES: dict[str, dict[str, str]] = {
    "reqDetectForwardCollisionRisk": {
        "need": "needCommonAEBSCapability",
        "req": "reqDetectForwardCollisionRisk",
    },
    "reqProvideCollisionWarning": {
        "need": "needCommonAEBSCapability",
        "req": "reqProvideCollisionWarning",
    },
    "reqCommandEmergencyBraking": {
        "need": "needCommonAEBSCapability",
        "req": "reqCommandEmergencyBraking",
    },
    "reqPedestrianTargetResponse": {
        "need": "needPedestrianCollisionRiskReduction",
        "req": "reqPedestrianTargetResponse",
    },
    "reqBicycleTargetResponse": {
        "need": "needBicycleCollisionRiskReduction",
        "req": "reqBicycleTargetResponse",
    },
}


def _contract() -> KernelContract:
    return model_contract()


def _binding_index() -> KernelBindingIndex:
    class _B:
        kernel_bindings = [
            KernelElementBinding(
                ontology_class="DerivesFromNeed",
                element_id=DEF,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="connection def DerivesFromNeed",
            ),
            KernelElementBinding(
                ontology_class="Need",
                element_id=NEED_DEF,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="requirement def StakeholderNeedCandidate",
            ),
            KernelElementBinding(
                ontology_class="Requirement",
                element_id=REQ_DEF,
                source_file=(
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                declaration="requirement def RequirementCandidate",
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
        "general": {"@id": type_id},
    }
    if implied:
        element["isImplied"] = True
        element["isImpliedIncluded"] = True
    return element


def _reference_subsetting(
    rs_id: str, end_id: str, connected_id: str, implied: bool = False
) -> dict:
    """The real serialized ReferenceSubsetting, with its alias keys."""
    element = {
        "@id": rs_id,
        "@type": "ReferenceSubsetting",
        "elementId": rs_id,
        "specific": {"@id": end_id},
        "owningRelatedElement": {"@id": end_id},
        "subsettingFeature": {"@id": end_id},
        "general": {"@id": connected_id},
        "subsettedFeature": {"@id": connected_id},
        "referencedFeature": {"@id": connected_id},
    }
    if implied:
        element["isImplied"] = True
        element["isImpliedIncluded"] = True
    return element


def real_shape_elements() -> list[dict]:
    """Minimized mirror of the real serialized witnesses."""
    elements: list[dict] = [
        {"@id": NEED_DEF, "@type": "RequirementDefinition", "declaredName": "StakeholderNeedCandidate"},
        {"@id": REQ_DEF, "@type": "RequirementDefinition", "declaredName": "RequirementCandidate"},
        {"@id": NEED_CAND, "@type": "RequirementDefinition", "declaredName": "ProductLineCommonCapabilityNeed"},
        {"@id": REQ_CAND, "@type": "RequirementDefinition", "declaredName": "FunctionalRequirementCandidate"},
        {
            "@id": "r6-sub-need",
            "@type": "Subclassification",
            "subclassifier": {"@id": NEED_CAND},
            "specific": {"@id": NEED_CAND},
            "superclassifier": {"@id": NEED_DEF},
            "general": {"@id": NEED_DEF},
        },
        {
            "@id": "r6-sub-req",
            "@type": "Subclassification",
            "subclassifier": {"@id": REQ_CAND},
            "specific": {"@id": REQ_CAND},
            "superclassifier": {"@id": REQ_DEF},
            "general": {"@id": REQ_DEF},
        },
        # Definition: FeatureMembership ends (real shape) + owned Documentation
        {
            "@id": DEF,
            "@type": "ConnectionDefinition",
            "declaredName": "DerivesFromNeed",
            "ownedRelationship": [
                {"@id": "r6-fm-need"},
                {"@id": "r6-fm-req"},
                {"@id": DOC_MEMBERSHIP},
            ],
        },
        {
            "@id": "r6-fm-need",
            "@type": "FeatureMembership",
            "memberName": "need",
            "memberElement": {"@id": DEF_END_NEED},
            "ownedRelatedElement": [{"@id": DEF_END_NEED}],
        },
        {
            "@id": "r6-fm-req",
            "@type": "FeatureMembership",
            "memberName": "derivedRequirement",
            "memberElement": {"@id": DEF_END_REQ},
            "ownedRelatedElement": [{"@id": DEF_END_REQ}],
        },
        {
            "@id": DEF_END_NEED,
            "@type": "ReferenceUsage",
            "declaredName": "need",
            "isEnd": True,
            "ownedRelationship": [{"@id": "r6-def-end-need-typing"}],
        },
        {
            "@id": DEF_END_REQ,
            "@type": "ReferenceUsage",
            "declaredName": "derivedRequirement",
            "isEnd": True,
            "ownedRelationship": [{"@id": "r6-def-end-req-typing"}],
        },
        _typing("r6-def-end-need-typing", DEF_END_NEED, NEED_DEF),
        _typing("r6-def-end-req-typing", DEF_END_REQ, REQ_DEF),
        {
            "@id": DOC_MEMBERSHIP,
            "@type": "OwningMembership",
            "memberElement": {"@id": DOC},
            "ownedRelatedElement": [{"@id": DOC}],
        },
        {"@id": DOC, "@type": "Documentation", "body": CLAIM_DOC},
    ]
    # Shared need usages
    for name in ("needCommonAEBSCapability", "needPedestrianCollisionRiskReduction",
                 "needBicycleCollisionRiskReduction"):
        elements.append({"@id": f"r6-usage-{name}", "@type": "RequirementUsage", "declaredName": name})
    for name in ("reqDetectForwardCollisionRisk", "reqProvideCollisionWarning",
                 "reqCommandEmergencyBraking", "reqPedestrianTargetResponse",
                 "reqBicycleTargetResponse"):
        elements.append({"@id": f"r6-usage-{name}", "@type": "RequirementUsage", "declaredName": name})
    elements.extend(
        [
            _typing("r6-usage-typing-needCommonAEBSCapability", "r6-usage-needCommonAEBSCapability", NEED_CAND),
            _typing("r6-usage-typing-needPedestrianCollisionRiskReduction", "r6-usage-needPedestrianCollisionRiskReduction", NEED_CAND),
            _typing("r6-usage-typing-needBicycleCollisionRiskReduction", "r6-usage-needBicycleCollisionRiskReduction", NEED_CAND),
            _typing("r6-usage-typing-reqDetectForwardCollisionRisk", "r6-usage-reqDetectForwardCollisionRisk", REQ_CAND),
            _typing("r6-usage-typing-reqProvideCollisionWarning", "r6-usage-reqProvideCollisionWarning", REQ_CAND),
            _typing("r6-usage-typing-reqCommandEmergencyBraking", "r6-usage-reqCommandEmergencyBraking", REQ_CAND),
            _typing("r6-usage-typing-reqPedestrianTargetResponse", "r6-usage-reqPedestrianTargetResponse", REQ_CAND),
            _typing("r6-usage-typing-reqBicycleTargetResponse", "r6-usage-reqBicycleTargetResponse", REQ_CAND),
        ]
    )
    for case, spec in CASES.items():
        conn = f"r6-conn-{case}"
        elements.append(
            {
                "@id": conn,
                "@type": "ConnectionUsage",
                "declaredName": f"{case}DerivedFrom{spec['need'][4:].capitalize()}",
                "ownedRelationship": [
                    {"@id": f"r6-em-{case}-need"},
                    {"@id": f"r6-em-{case}-req"},
                    {"@id": f"r6-conn-typing-{case}"},
                ],
            }
        )
        elements.extend(
            [
                _typing(f"r6-conn-typing-{case}", conn, DEF),
                {
                    "@id": f"r6-em-{case}-need",
                    "@type": "EndFeatureMembership",
                    "owningRelatedElement": {"@id": conn},
                    "memberName": "need",
                    "memberElement": {"@id": f"r6-endf-{case}-need"},
                    "ownedRelatedElement": [{"@id": f"r6-endf-{case}-need"}],
                },
                {
                    "@id": f"r6-em-{case}-req",
                    "@type": "EndFeatureMembership",
                    "owningRelatedElement": {"@id": conn},
                    "memberName": "derivedRequirement",
                    "memberElement": {"@id": f"r6-endf-{case}-req"},
                    "ownedRelatedElement": [{"@id": f"r6-endf-{case}-req"}],
                },
                {
                    "@id": f"r6-endf-{case}-need",
                    "@type": "Feature",
                    "name": "need",
                    "isEnd": True,
                    "ownedRelationship": [{"@id": f"r6-rs-{case}-need"}],
                },
                {
                    "@id": f"r6-endf-{case}-req",
                    "@type": "Feature",
                    "name": "derivedRequirement",
                    "isEnd": True,
                    "ownedRelationship": [{"@id": f"r6-rs-{case}-req"}],
                },
                _reference_subsetting(
                    f"r6-rs-{case}-need", f"r6-endf-{case}-need",
                    f"r6-usage-{spec['need']}",
                ),
                _reference_subsetting(
                    f"r6-rs-{case}-req", f"r6-endf-{case}-req",
                    f"r6-usage-{spec['req']}",
                ),
            ]
        )
    return elements


def _by_id(elements: list[dict]) -> dict[str, dict]:
    return {element["@id"]: element for element in elements}


def _traversal() -> SemanticTraversal:
    return SemanticTraversal(_contract(), kernel_bindings=_binding_index())


def _traverse(predicate: str, source_name: str, elements: list[dict]):
    source = next(
        element
        for element in elements
        if element.get("declaredName") == source_name
        and str(element.get("@type")) == "RequirementUsage"
    )
    return _traversal().traverse(predicate, source, elements)


# ---------------------------------------------------------------------------
# A. connection-usage end role grounding
# ---------------------------------------------------------------------------


def test_real_style_end_classifies_via_reference_subsetting() -> None:
    elements = real_shape_elements()
    hops = _traverse("derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements)
    assert len(hops) == 1
    end = hops[0].witness["need_end"]
    assert end["connected_usage_id"] == "r6-usage-needCommonAEBSCapability"
    assert end["reference_subsetting_id"] == "r6-rs-reqCommandEmergencyBraking-need"
    assert end["end_feature_is_end"] is True
    assert end["end_membership_id"] == "r6-em-reqCommandEmergencyBraking-need"
    assert end["role"] == "need"
    assert end["role_source"] == "end-membership-name"


def test_end_feature_without_reference_subsetting_is_insufficient() -> None:
    """The synthesized end Feature alone (a name, no grounding) must NOT be
    classified: without its ReferenceSubsetting the witness is corrupted."""
    elements = real_shape_elements()
    i = next(
        idx for idx, e in enumerate(elements)
        if e["@id"] == "r6-endf-reqCommandEmergencyBraking-need"
    )
    elements[i] = {**elements[i], "ownedRelationship": []}
    elements = [
        e for e in elements if e["@id"] != "r6-rs-reqCommandEmergencyBraking-need"
    ]
    with pytest.raises(IdentityNotFoundError):
        _traverse(
            "derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements
        )


def test_implied_only_reference_subsetting_fails_closed() -> None:
    elements = real_shape_elements()
    i = next(
        idx for idx, e in enumerate(elements)
        if e["@id"] == "r6-rs-reqCommandEmergencyBraking-need"
    )
    elements[i] = _reference_subsetting(
        "r6-rs-reqCommandEmergencyBraking-need",
        "r6-endf-reqCommandEmergencyBraking-need",
        "r6-usage-needCommonAEBSCapability",
        implied=True,
    )
    with pytest.raises(IdentityNotFoundError, match="implied"):
        _traverse(
            "derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements
        )


def test_multiple_distinct_reference_subsetting_targets_fail_closed() -> None:
    elements = real_shape_elements()
    elements.append(
        _reference_subsetting(
            "r6-rs-extra",
            "r6-endf-reqCommandEmergencyBraking-need",
            "r6-usage-needBicycleCollisionRiskReduction",
        )
    )
    i = next(
        idx for idx, e in enumerate(elements)
        if e["@id"] == "r6-endf-reqCommandEmergencyBraking-need"
    )
    elements[i]["ownedRelationship"] = [
        {"@id": "r6-rs-reqCommandEmergencyBraking-need"},
        {"@id": "r6-rs-extra"},
    ]
    with pytest.raises(IdentityNotFoundError, match="ambiguous"):
        _traverse(
            "derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements
        )


def test_dangling_reference_subsetting_target_fails_closed() -> None:
    elements = real_shape_elements()
    for element in elements:
        if element["@id"] == "r6-rs-reqCommandEmergencyBraking-need":
            element["referencedFeature"] = {"@id": "r6-missing-usage"}
            element["general"] = {"@id": "r6-missing-usage"}
            element["subsettedFeature"] = {"@id": "r6-missing-usage"}
    with pytest.raises(IdentityNotFoundError, match="does not exist"):
        _traverse(
            "derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements
        )


def test_connected_usage_outside_lineage_fails_closed() -> None:
    elements = real_shape_elements()
    elements.append({"@id": "r6-stranger", "@type": "PartUsage", "declaredName": "unrelated"})
    for element in elements:
        if element["@id"] == "r6-rs-reqCommandEmergencyBraking-req":
            element["referencedFeature"] = {"@id": "r6-stranger"}
            element["general"] = {"@id": "r6-stranger"}
            element["subsettedFeature"] = {"@id": "r6-stranger"}
    with pytest.raises(IdentityNotFoundError, match="grounds in neither"):
        _traverse(
            "derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements
        )


def test_role_name_contradicting_lineage_fails_closed() -> None:
    """The modeled end role must agree with the connected usage's lineage."""
    elements = real_shape_elements()
    for element in elements:
        if element["@id"] == "r6-em-reqCommandEmergencyBraking-need":
            element["memberName"] = "derivedRequirement"
    with pytest.raises(IdentityNotFoundError, match="contradictory"):
        _traverse(
            "derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements
        )


def test_implied_only_definition_typing_is_not_the_predicate() -> None:
    elements = real_shape_elements()
    i = next(
        idx for idx, e in enumerate(elements)
        if e["@id"] == "r6-conn-typing-reqCommandEmergencyBraking"
    )
    elements[i] = _typing(
        "r6-conn-typing-reqCommandEmergencyBraking",
        "r6-conn-reqCommandEmergencyBraking",
        DEF,
        implied=True,
    )
    hops = _traverse(
        "derivesRequirementFromNeed", "reqCommandEmergencyBraking", elements
    )
    assert hops == []


def test_forward_and_inverse_share_the_same_witness_for_all_five() -> None:
    """Each case's forward edge is found in the inverse navigation from its
    need, carrying the SAME connection witness (shared needs legitimately
    yield one inverse edge per derived requirement)."""
    elements = real_shape_elements()
    for case, spec in CASES.items():
        forward = _traverse("derivesRequirementFromNeed", spec["req"], elements)
        assert len(forward) == 1, case
        f = forward[0]
        inverse = _traverse("derivedRequirementsOfNeed", spec["need"], elements)
        matching = [hop for hop in inverse if hop.api_object["@id"] == f.api_object["@id"]]
        assert len(matching) == 1, case
        i = matching[0]
        assert f.target["@id"] == i.source["@id"], case
        assert f.source["@id"] == i.target["@id"], case
        assert f.witness["need_end"] == i.witness["need_end"], case
        assert f.witness["derived_requirement_end"] == i.witness["derived_requirement_end"], case
        assert f.witness["definition_typing_id"] == i.witness["definition_typing_id"], case
