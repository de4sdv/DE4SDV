"""Definition descriptions in shapes the genuine-export cut doesn't hold.

These corpora are built in the genuine export's shapes (owning memberships with
``memberName``, ``owningRelationship`` on the member, relationships owned by
their source). The cut covers the real model in ``test_inspect_definitions.py``;
here: multiple inheritance with a redefinition, and feature values whose
referent is an owned expression, a parameter, or outside the corpus.
"""

from __future__ import annotations

import pytest

from de4sdv.semantic.element_description import OUTSIDE_EXPORT, ElementDescriber
from de4sdv.semantic.revision_index import RevisionIndex
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import ModelBuilder, ref


def _describe(builder: ModelBuilder, definition: dict) -> dict:
    index = RevisionIndex(builder.elements)
    describer = ElementDescriber(index, QualifiedNameIndex(builder.elements, by_id=index.by_id))
    description, _gaps = describer.definition(definition["@id"])
    return description


def _package(builder: ModelBuilder) -> dict:
    return builder.package("P", owner=builder.new("Namespace"))


def _redefine(builder: ModelBuilder, feature: dict, target: dict) -> None:
    builder.relationship("Redefinition", feature, redefinedFeature=ref(target), redefiningFeature=ref(feature),
                         general=ref(target), specific=ref(feature))


def _inherited(description: dict) -> list[tuple]:
    return [(entry["name"], entry["inherited_from"], entry.get("redefines"))
            for entry in description["inherited_features"]]


@pytest.mark.parametrize("order", ["B, C", "C, B"])
def test_a_feature_a_sibling_supertype_redefines_is_not_inherited_in_either_order(order: str) -> None:
    """D :> B, C and C :> B, where C::g2 redefines B::g (a diamond). KerML removes a
    feature that another inherited feature redefines, whatever the supertype order."""
    builder = ModelBuilder("diamond " + order)
    package = _package(builder)
    b = builder.definition("PartDefinition", "B", package)
    g = builder.usage("AttributeUsage", "g", b, membership="FeatureMembership")
    c = builder.definition("PartDefinition", "C", package, specializes=[b])
    g2 = builder.usage("AttributeUsage", "g2", c, membership="FeatureMembership")
    _redefine(builder, g2, g)
    d = builder.definition("PartDefinition", "D", package, specializes=[b, c] if order == "B, C" else [c, b])
    assert _inherited(_describe(builder, d)) == [("g2", "P::C", ["P::B::g"])]


def test_a_redefinition_hides_what_it_redefines_through_a_chain() -> None:
    """A::h, B :> A with g :>> h, C :> B with g2 :>> g, and D :> A, C: D inherits g2 only."""
    builder = ModelBuilder("redefinition chain")
    package = _package(builder)
    a = builder.definition("PartDefinition", "A", package)
    h = builder.usage("AttributeUsage", "h", a, membership="FeatureMembership")
    b = builder.definition("PartDefinition", "B", package, specializes=[a])
    g = builder.usage("AttributeUsage", "g", b, membership="FeatureMembership")
    _redefine(builder, g, h)
    c = builder.definition("PartDefinition", "C", package, specializes=[b])
    g2 = builder.usage("AttributeUsage", "g2", c, membership="FeatureMembership")
    _redefine(builder, g2, g)
    d = builder.definition("PartDefinition", "D", package, specializes=[a, c])
    assert _inherited(_describe(builder, d)) == [("g2", "P::C", ["P::B::g"])]


def _valued(builder: ModelBuilder) -> tuple[dict, dict, dict]:
    """calc def V { attribute x = <a feature reference expression>; }"""
    package = _package(builder)
    calc = builder.definition("CalculationDefinition", "V", package)
    x = builder.usage("AttributeUsage", "x", calc, membership="FeatureMembership")
    expression = builder.new("FeatureReferenceExpression")
    builder.own(x, expression, kind="FeatureValue")
    builder.own(expression, builder.new("Feature", name="result"), kind="ReturnParameterMembership")
    return package, calc, expression


def test_a_reference_to_an_owned_expression_is_reported_as_that_expression() -> None:
    """The referent of a FeatureReferenceExpression is its first non-parameter membership's
    member, of any kind: here a body expression owned through a FeatureMembership, as in
    the export's if/else operands. It is in the corpus, so it is not "outside"."""
    builder = ModelBuilder("owned referent")
    _package_, calc, expression = _valued(builder)
    body = builder.new("OperatorExpression", operator="+")
    builder.own(expression, body, kind="FeatureMembership")
    value = _describe(builder, calc)["owned_features"][0]["value"]
    assert value == {"default": False, "values": [{"expression": "OperatorExpression", "element_id": body["@id"]}]}


def test_a_reference_names_its_referent_or_says_it_is_outside_only_when_absent() -> None:
    builder = ModelBuilder("referents")
    package, calc, expression = _valued(builder)
    target = builder.usage("AttributeUsage", "speed", package)
    builder.relationship("Membership", expression, memberElement=ref(target))
    value = _describe(builder, calc)["owned_features"][0]["value"]
    assert value["values"] == [{"reference": "P::speed", "element_id": target["@id"]}]

    builder = ModelBuilder("absent referent")
    _package_, calc, expression = _valued(builder)
    builder.relationship("Membership", expression, memberElement={"@id": "not-in-this-corpus"})
    assert _describe(builder, calc)["owned_features"][0]["value"]["values"] == [{"reference": OUTSIDE_EXPORT}]

    builder = ModelBuilder("removed referent")  # the export removed the reference itself
    _package_, calc, expression = _valued(builder)
    builder.relationship("Membership", expression)
    assert _describe(builder, calc)["owned_features"][0]["value"]["values"] == [{"reference": OUTSIDE_EXPORT}]
