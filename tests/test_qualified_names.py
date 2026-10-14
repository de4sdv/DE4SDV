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
    escape_name,
    format_qualified_name,
    parse_qualified_name,
)
from increment_model_fixtures import ModelBuilder, ref


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


def test_only_an_owner_less_namespace_is_a_root() -> None:
    """KerML: a root namespace is a Namespace without an owner. An unnamed element of
    another metaclass without an owner lost its owner to the export boundary, so its
    members have no complete chain of named namespaces and no qualified name."""
    builder = ModelBuilder("orphan")
    orphan = builder.new("PartUsage")  # unnamed, no owning relationship
    speed = builder.usage("AttributeUsage", "speed", orphan, membership="FeatureMembership")
    unit = builder.usage("AttributeUsage", "unit", speed, membership="FeatureMembership")
    root = builder.new("Namespace")
    package = builder.package("P", owner=root)
    index = _index(builder)
    assert index.qualified_name(speed["@id"]) is None
    assert index.qualified_name(unit["@id"]) is None
    assert index.resolve("speed::unit") == ()
    assert index.qualified_name(package["@id"]) == "P"


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


@pytest.mark.parametrize("keyword", ["end", "part", "ref", "def", "import", "about", "xor"])
def test_reserved_words_are_quoted_and_both_spellings_resolve(keyword: str) -> None:
    """SysML v2: a reserved word may not be used as a name although it has the form of
    a basic name. The keywords here are taken from the SysML v2 reserved-keyword list."""
    builder, named = _corpus()
    element = builder.definition("PartDefinition", keyword, named["P"])
    index = _index(builder)
    assert escape_name(keyword) == f"'{keyword}'"
    assert index.qualified_name(element["@id"]) == f"P::'{keyword}'"
    for spelling in (f"P::'{keyword}'", f"P::{keyword}"):
        assert [found["@id"] for found in index.resolve(spelling)] == [element["@id"]]


def test_names_that_only_resemble_reserved_words_stay_basic() -> None:
    for name in ("End", "endpoint", "part_", "Ref", "_def"):
        assert escape_name(name) == name


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


def test_a_declared_name_that_contains_double_colons_must_be_quoted() -> None:
    builder, named = _corpus()
    element = builder.definition("PartDefinition", "A::B", named["P"])
    index = _index(builder)
    assert index.qualified_name(element["@id"]) == "P::'A::B'"
    resolved = resolve_identity("P::'A::B'", builder.elements, qualified_names=index)
    assert resolved.element["@id"] == element["@id"]
    with pytest.raises(IdentityNotFoundError) as raised:
        resolve_identity("A::B", builder.elements, qualified_names=index)
    message = str(raised.value)
    assert f"'A::B' is the declared name of PartDefinition {element['@id']}" in message
    assert "quote it as one segment: P::'A::B'" in message


def _reachable_corpus():
    """Names SysML reaches through more than ownership, in the genuine export's shapes.

    P owns incX (short name INC-X-001), Base (owning feature f), Sub :> Base,
    Sub2 :> Base (owning g, which redefines f) and an alias BaseAlias for Base (a
    non-owning Membership). Q imports P's membership of Base (a MembershipImport),
    R imports P::* (a NamespaceImport).
    """
    builder = ModelBuilder("reachable")
    root = builder.new("Namespace")
    package = builder.package("P", owner=root)
    increment = builder.usage("PartUsage", "incX", package, short="INC-X-001")
    increment_membership = next(item for item in builder.elements
                                if item["@id"] == increment["owningRelationship"]["@id"])
    increment_membership["memberShortName"] = "INC-X-001"
    base = builder.definition("PartDefinition", "Base", package)
    feature = builder.usage("AttributeUsage", "f", base, membership="FeatureMembership")
    sub = builder.definition("PartDefinition", "Sub", package, specializes=[base])
    sub2 = builder.definition("PartDefinition", "Sub2", package, specializes=[base])
    redefining = builder.usage("AttributeUsage", "g", sub2, membership="FeatureMembership")
    builder.relationship("Redefinition", redefining, redefinedFeature=ref(feature),
                         redefiningFeature=ref(redefining), general=ref(feature), specific=ref(redefining))
    builder.relationship("Membership", package, memberElement=ref(base), memberName="BaseAlias",
                         declaredName="BaseAlias")
    importer = builder.package("Q", owner=root)
    builder.relationship("MembershipImport", importer, importedMembership=ref(base["owningRelationship"]["@id"]),
                         visibility="public")
    namespace_importer = builder.package("R", owner=root)
    builder.relationship("NamespaceImport", namespace_importer, importedNamespace=ref(package))
    return builder, {"incX": increment, "Base": base, "f": feature, "Sub": sub, "Sub2": sub2, "g": redefining}


@pytest.mark.parametrize(("identifier", "reason"), [
    ("P::'INC-X-001'", "'INC-X-001' is the short name of an owned member of P; its qualified name is P::incX"),
    ("P::INC-X-001", "'INC-X-001' is the short name of an owned member of P; its qualified name is P::incX"),
    ("P::BaseAlias", "'BaseAlias' is an alias in P; the aliased element's qualified name is P::Base"),
    ("P::Sub::f", "'f' is inherited by P::Sub from P::Base; its qualified name is P::Base::f"),
    ("P::Sub2::f", "'f' is a feature of P::Base that P::Sub2 redefines (P::Sub2::g); its qualified name is P::Base::f"),
    ("Q::Base", "'Base' is imported into Q (public import); its qualified name is P::Base"),
    ("R::incX", "'incX' is imported into R (private import of P::*); its qualified name is P::incX"),
])
def test_a_refusal_names_the_canonical_name_of_a_member_reached_another_way(identifier: str, reason: str) -> None:
    """Only ownership-qualified element names resolve. A short name, an alias, an
    inherited feature or an imported membership is refused, never resolved; the
    refusal says which it is and gives the canonical qualified name."""
    builder, _named = _reachable_corpus()
    with pytest.raises(IdentityNotFoundError) as raised:
        resolve_identity(identifier, builder.elements, qualified_names=_index(builder))
    assert reason in str(raised.value)


def test_a_segment_reachable_no_other_way_keeps_the_plain_refusal() -> None:
    builder, _named = _reachable_corpus()
    with pytest.raises(IdentityNotFoundError) as raised:
        resolve_identity("P::Sub::nothing", builder.elements, qualified_names=_index(builder))
    assert "'P::Sub' is PartDefinition" in str(raised.value)
    assert "has no owned member named 'nothing'" in str(raised.value)


def _same_names_corpus():
    """B1 and B2 each declare a feature x, and S1 and S2 each own a member y.

    D :> B1, B2 inherits two features named x. E :> B1, B2 owns z, which redefines
    B1::x. F :> C, B1 with C :> B1 reaches the one B1::x twice. R imports S1::* and S2::*.
    (RequirementCandidate inherits priority from both NeedsRequirementsAttributes and
    SYSMOD's ExtendedConcern in the release export.)
    """
    builder = ModelBuilder("same names")
    root = builder.new("Namespace")
    package = builder.package("P", owner=root)
    b1 = builder.definition("PartDefinition", "B1", package)
    x1 = builder.usage("AttributeUsage", "x", b1, membership="FeatureMembership")
    b2 = builder.definition("PartDefinition", "B2", package)
    builder.usage("AttributeUsage", "x", b2, membership="FeatureMembership")
    builder.definition("PartDefinition", "D", package, specializes=[b1, b2])
    e = builder.definition("PartDefinition", "E", package, specializes=[b1, b2])
    z = builder.usage("AttributeUsage", "z", e, membership="FeatureMembership")
    builder.relationship("Redefinition", z, redefinedFeature=ref(x1), redefiningFeature=ref(z),
                         general=ref(x1), specific=ref(z))
    c = builder.definition("PartDefinition", "C", package, specializes=[b1])
    builder.definition("PartDefinition", "F", package, specializes=[c, b1])
    importer = builder.package("R", owner=root)
    for name in ("S1", "S2"):
        source = builder.package(name, owner=root)
        builder.usage("PartUsage", "y", source)
        builder.relationship("NamespaceImport", importer, importedNamespace=ref(source))
    return builder


@pytest.mark.parametrize(("identifier", "reason"), [
    ("P::D::x", "'x' is ambiguous in P::D, where it names 2 elements: "
                "inherited from P::B1 (its qualified name is P::B1::x), "
                "inherited from P::B2 (its qualified name is P::B2::x)"),
    ("R::y", "'y' is ambiguous in R, where it names 2 elements: "
             "imported by a private import of S1::* (its qualified name is S1::y), "
             "imported by a private import of S2::* (its qualified name is S2::y)"),
    ("P::E::x", "'x' is inherited by P::E from P::B2; its qualified name is P::B2::x"),
    ("P::F::x", "'x' is inherited by P::F from P::B1; its qualified name is P::B1::x"),
])
def test_a_name_that_reaches_several_elements_is_refused_as_ambiguous_with_every_canonical_name(
        identifier: str, reason: str) -> None:
    """SysML reaches two elements through the segment: the refusal says the name is
    ambiguous there and names each. A match a feature of the type redefines is not one
    of them, and one element reached twice is one name, not an ambiguity."""
    builder = _same_names_corpus()
    with pytest.raises(IdentityNotFoundError) as raised:
        resolve_identity(identifier, builder.elements, qualified_names=_index(builder))
    assert reason in str(raised.value)
