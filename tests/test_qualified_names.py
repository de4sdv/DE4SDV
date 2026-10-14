"""Qualified names computed from the export's ownership graph, and resolution by them.

The licensed export and the API listing carry no ``qualifiedName``, ``owner`` or
``owningNamespace`` value. A qualified name is computed the KerML way: the owning
memberships from the element up to an anonymous root namespace. These unit tests
build corpora in the genuine export's shapes (an anonymous root ``Namespace``
per document, ``OwningMembership``/``FeatureMembership`` with ``memberName``,
``owningRelationship`` on the member); the genuine-export cut covers the real
model in ``test_inspect_definitions.py``.
"""

from __future__ import annotations

import pytest

from de4sdv.sysml_api.errors import AmbiguousIdentityError, IdentityNotFoundError
from de4sdv.sysml_api.identity import resolve_identity
from de4sdv.sysml_api.qualified_names import (
    QualifiedNameIndex,
    format_qualified_name,
    parse_qualified_name,
)
from increment_model_fixtures import ModelBuilder


def _corpus():
    """root namespace -> package P -> part def D, package Inner -> part def D, enum def E."""
    builder = ModelBuilder("qualified-names")
    root = builder.new("Namespace")
    package = builder.package("P", owner=root)
    definition = builder.definition("PartDefinition", "D", package)
    inner = builder.package("Inner", owner=package)
    nested = builder.definition("PartDefinition", "D", inner)
    feature = builder.usage("AttributeUsage", "size", definition, membership="FeatureMembership")
    return builder, {"root": root, "P": package, "P::D": definition, "P::Inner": inner,
                     "P::Inner::D": nested, "P::D::size": feature}


def _index(builder):
    return QualifiedNameIndex(builder.elements)


def test_members_are_named_by_their_owning_memberships_up_to_the_root_namespace() -> None:
    builder, named = _corpus()
    index = _index(builder)
    for name, element in named.items():
        if name == "root":
            continue
        assert index.qualified_name(element["@id"]) == name
        assert [found["@id"] for found in index.resolve(name)] == [element["@id"]]


def test_the_root_namespace_and_unnamed_elements_have_no_qualified_name() -> None:
    builder, named = _corpus()
    anonymous = builder.usage("PartUsage", None, named["P"])
    under_anonymous = builder.usage("AttributeUsage", "x", anonymous, membership="FeatureMembership")
    index = _index(builder)
    assert index.qualified_name(named["root"]["@id"]) is None
    assert index.qualified_name(anonymous["@id"]) is None
    # KerML: no complete chain of named namespaces, so no qualified name, never "P::x".
    assert index.qualified_name(under_anonymous["@id"]) is None
    assert index.resolve("P::x") == ()


def test_documentation_never_shares_the_qualified_name_of_what_it_documents() -> None:
    builder, named = _corpus()
    doc = builder.new("Documentation", body="A definition.")
    builder.own(named["P::D"], doc)
    index = _index(builder)
    assert index.qualified_name(doc["@id"]) is None
    assert [found["@id"] for found in index.resolve("P::D")] == [named["P::D"]["@id"]]


def test_an_owner_outside_the_corpus_leaves_no_qualified_name() -> None:
    """A named element without an owning relationship lost its owner to the export
    boundary (a library anchor such as VerificationMethodKind): neither it nor its
    members get a qualified name, and its members never become root-level names."""
    builder = ModelBuilder("outside-owner")
    anchor = builder.new("EnumerationDefinition", name="Kind")
    literal = builder.usage("EnumerationUsage", "inspect", anchor, membership="VariantMembership")
    dangling = builder.new("PartDefinition", name="Lost")
    dangling["owningRelationship"] = {"@id": "not-in-this-corpus"}
    index = _index(builder)
    assert index.qualified_name(anchor["@id"]) is None
    assert index.qualified_name(literal["@id"]) is None
    assert index.qualified_name(dangling["@id"]) is None
    assert index.resolve("Kind::inspect") == ()


def test_a_member_owned_through_a_non_membership_relationship_has_no_qualified_name() -> None:
    builder, named = _corpus()
    feature = builder.new("ReferenceUsage", name="end1")
    builder.own(named["P::D"], feature, kind="ReferenceSubsetting")
    assert _index(builder).qualified_name(feature["@id"]) is None


def test_names_that_are_not_basic_names_are_quoted_and_both_spellings_resolve() -> None:
    builder, named = _corpus()
    spaced = builder.usage("UseCaseUsage", "exchange vehicle signals", named["P"])
    quoted = builder.usage("PartUsage", "it's", named["P"])
    index = _index(builder)
    assert index.qualified_name(spaced["@id"]) == "P::'exchange vehicle signals'"
    assert index.qualified_name(quoted["@id"]) == "P::'it\\'s'"
    for spelling in ("P::'exchange vehicle signals'", "P::exchange vehicle signals"):
        assert [found["@id"] for found in index.resolve(spelling)] == [spaced["@id"]]
    assert [found["@id"] for found in index.resolve("P::'it\\'s'")] == [quoted["@id"]]


def test_a_short_name_stands_in_for_a_missing_name() -> None:
    builder, named = _corpus()
    short_only = builder.usage("PartUsage", None, named["P"], short="INC-EXAMPLE-001")
    index = _index(builder)
    assert index.qualified_name(short_only["@id"]) == "P::'INC-EXAMPLE-001'"
    assert [found["@id"] for found in index.resolve("P::INC-EXAMPLE-001")] == [short_only["@id"]]


@pytest.mark.parametrize("text", ["", " ", "A::", "::A", "A::::B", "A::'b", "A::'b'c", "A:: ", "A::'\\q'"])
def test_text_that_is_not_a_qualified_name_parses_to_nothing(text: str) -> None:
    assert parse_qualified_name(text) is None


def test_parsing_inverts_formatting() -> None:
    path = ("DE4SDV_X", "exchange vehicle signals", "it's", "a\\b", "plain_1")
    assert parse_qualified_name(format_qualified_name(path)) == path
    assert parse_qualified_name(" P :: D ") == ("P", "D")
    assert parse_qualified_name("P") == ("P",)  # a member of a root namespace


def test_the_api_listing_padding_changes_no_qualified_name() -> None:
    """The pinned API pads every element with valueless fields (qualifiedName,
    owner, owningNamespace, name, ... as null or empty)."""
    builder, named = _corpus()
    padded = [{"qualifiedName": None, "owner": None, "owningNamespace": None, "owningMembership": None,
               "name": None, "shortName": None, "declaredShortName": None, "documentation": [],
               "ownedMember": [], "member": [], **element} for element in builder.elements]
    index = QualifiedNameIndex(padded)
    for name, element in named.items():
        assert index.qualified_name(element["@id"]) == (None if name == "root" else name)


def test_resolution_by_qualified_name_is_exact_and_never_falls_back_to_a_bare_name() -> None:
    builder, named = _corpus()
    elements, index = builder.elements, _index(builder)
    resolved = resolve_identity("P::Inner::D", elements, qualified_names=index)
    assert (resolved.level, resolved.element["@id"]) == ("qualified-name-match", named["P::Inner::D"]["@id"])
    # "size" is a unique bare name, but a qualified name never falls back to it.
    assert resolve_identity("size", elements).element["@id"] == named["P::D::size"]["@id"]
    with pytest.raises(IdentityNotFoundError, match=r"'P' is Package .*no owned member named 'size'"):
        resolve_identity("P::size", elements, qualified_names=index)
    with pytest.raises(IdentityNotFoundError, match="no root-level member is named 'Other'"):
        resolve_identity("Other::D", elements, qualified_names=index)
    # Without the computed names, a qualified identifier still never reaches the name match.
    with pytest.raises(IdentityNotFoundError, match="qualified name"):
        resolve_identity("P::D::size", elements)


def test_a_qualified_name_shared_by_two_elements_is_ambiguous_with_its_candidates() -> None:
    builder, named = _corpus()
    twin = builder.usage("PartUsage", "D", named["P"])
    index = _index(builder)
    with pytest.raises(AmbiguousIdentityError) as raised:
        resolve_identity("P::D", builder.elements, qualified_names=index)
    message = str(raised.value)
    assert "qualified-name-match" in message
    assert named["P::D"]["@id"] in message and "PartDefinition" in message
    assert twin["@id"] in message and "PartUsage" in message


def test_an_ambiguous_bare_name_describes_its_candidates() -> None:
    """In production, ``Stakeholder`` names a part definition and a library alias
    membership; the error says which is which instead of listing bare UUIDs."""
    builder, named = _corpus()
    alias = builder.relationship("Membership", named["P::Inner"], memberElement={"@id": named["P::D"]["@id"]},
                                 declaredName="D", memberName="D")
    with pytest.raises(AmbiguousIdentityError) as raised:
        resolve_identity("D", builder.elements, qualified_names=_index(builder))
    message = str(raised.value)
    assert f"{named['P::D']['@id']}: PartDefinition P::D" in message
    assert f"{named['P::Inner::D']['@id']}: PartDefinition P::Inner::D" in message
    assert f"{alias['@id']}: Membership (no qualified name)" in message


def test_the_expected_type_must_match_the_element_a_qualified_name_names() -> None:
    builder, named = _corpus()
    index = _index(builder)
    resolved = resolve_identity("P::D", builder.elements, expected_type="PartDefinition",
                                qualified_names=index)
    assert resolved.element["@id"] == named["P::D"]["@id"]
    with pytest.raises(IdentityNotFoundError, match="is a PartDefinition, not a PartUsage"):
        resolve_identity("P::D", builder.elements, expected_type="PartUsage", qualified_names=index)


def test_a_served_qualified_name_still_resolves_first() -> None:
    """Corpora that serve ``qualifiedName`` (API fixtures) keep their behavior."""
    elements = [{"@id": "req-a", "@type": "RequirementUsage", "declaredName": "reqX",
                 "qualifiedName": "PackageA::reqX"}]
    resolved = resolve_identity("PackageA::reqX", elements, qualified_names=QualifiedNameIndex(elements))
    assert (resolved.level, resolved.element["@id"]) == ("qualified-name-match", "req-a")
