"""The derived ``appliesToMemberProduct`` fact of the PLEML feature configurations (ADR 0022).

A feature configuration applies to a member product when the member's
definition owns a usage typed by the part definition that the configuration's
product-model projection declares. DE4SDV derives the fact; no PLEML
construct carries it (the S5o classification of ``appliesToMemberProduct``,
ADR 0022 decision 8).

Identity follows ADR 0011, never a name alone:

- the configurations and the projection name each one owns come from the
  evaluator (``pleml_configuration.evaluate``): a configuration by the pinned
  PLEML library definitions, its projection name by the owned
  ``ProductModelProjectionName`` metadata, which ingestion binds to the kernel;
- the generated part definition by its metatype, its declared name (the
  projection name), its document (a generated product model under
  ``PRODUCT_MODELS``) and its specialization of the owner that the feature
  model's projection names; exactly one may match;
- the member products by the kernel binding of ``MemberProduct``
  (``ProductLineMemberProduct``) and their specialization lineage.

Only owned usages count. A definition that inherits the usage from a member
product is no member the configuration applies to: the INC-AEBS-010 test
article inherits the AAOS-integrated member's platform stack. A configuration
that applies to more than one member product is refused.

The derivation reads serializer and API objects only. It is no traversal of
the runtime and no runtime-queryable claim (the forward obligations of the
row stay with the exact-revision evidence of a privileged run).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from . import pleml_configuration

SCHEMA = "de4sdv.applies-to-member-product/v1"
#: The root of the generated product-model documents: the projections that the
#: configurator writes from the receipts (ADR 0022 decision 5).
PRODUCT_MODELS = "model-based-product-line-engineering/product-models/"
#: The roots of the PLEML documents that the evaluator reads.
PLEML_ROOTS = (
    "model-based-product-line-engineering/feature-models/",
    "model-based-product-line-engineering/feature-configurations/",
)
#: The kernel class whose validated binding is the member-product root.
MEMBER_PRODUCT = "MemberProduct"


class MemberProductError(ValueError):
    """The derivation refuses the model: an ambiguous identity or a configuration with several members."""


def _id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        identifier = value.get("@id")
        return identifier if isinstance(identifier, str) and identifier else None
    return None


def _ids(value: Any) -> list[str]:
    if isinstance(value, list):
        return [found for item in value if (found := _id(item))]
    found = _id(value)
    return [found] if found else []


class _Graph:
    def __init__(self, elements: Iterable[Mapping[str, Any]], sources: Mapping[str, str]) -> None:
        self.by_id: dict[str, Mapping[str, Any]] = {}
        for element in elements:
            identifier = _id(element)
            if identifier is None or not isinstance(element.get("@type"), str):
                raise MemberProductError("an element has no API identity or no metatype")
            if identifier in self.by_id:
                raise MemberProductError(f"duplicate API identity {identifier}")
            self.by_id[identifier] = element
        self.sources = sources

    def kind(self, identifier: str) -> str:
        return str(self.by_id[identifier]["@type"]) if identifier in self.by_id else ""

    def name(self, identifier: str) -> str | None:
        element = self.by_id.get(identifier, {})
        name = element.get("declaredName") or element.get("name")
        return name if isinstance(name, str) else None

    def owned(self, owner: str, kind: str) -> list[Mapping[str, Any]]:
        """The owned relationships of ``owner`` of exactly ``kind``."""
        found = []
        for relationship in _ids(self.by_id.get(owner, {}).get("ownedRelationship")):
            element = self.by_id.get(relationship)
            if element is not None and element.get("@type") == kind:
                found.append(element)
        return found

    def generals(self, definition: str) -> list[str]:
        """The direct supertypes of a definition: its owned subclassifications."""
        return [general for relationship in self.owned(definition, "Subclassification")
                if _id(relationship.get("specific") or relationship.get("subclassifier")) == definition
                and (general := _id(relationship.get("general") or relationship.get("superclassifier")))]

    def specializes(self, definition: str, root: str) -> bool:
        seen, pending = set(), [definition]
        while pending:
            current = pending.pop()
            if current == root:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(self.generals(current))
        return False

    def owned_usages_typed_by(self, definition: str, type_id: str) -> list[str]:
        """The usages ``definition`` owns through a feature membership whose own typing is ``type_id``."""
        usages = []
        for membership in self.owned(definition, "FeatureMembership"):
            for usage in _ids(membership.get("ownedRelatedElement")):
                typings = self.owned(usage, "FeatureTyping")
                if any(_id(typing.get("type") or typing.get("general")) == type_id
                       and _id(typing.get("typedFeature") or typing.get("specific")) == usage
                       for typing in typings):
                    usages.append(usage)
        return usages

    def owning_namespace(self, identifier: str) -> str | None:
        membership = _id(self.by_id.get(identifier, {}).get("owningRelationship"))
        return _id(self.by_id.get(membership, {}).get("owningRelatedElement")) if membership else None


def _projection_owner(graph: _Graph, projection: Mapping[str, Any] | None) -> str:
    """The owner definition a feature model's projection names: a part definition of the named package."""
    if not projection:
        raise MemberProductError("a feature model with configurations names no product-model projection")
    owners = [identifier for identifier, element in graph.by_id.items()
              if element.get("@type") == "PartDefinition" and graph.name(identifier) == projection["owner"]
              and graph.name(graph.owning_namespace(identifier) or "") == projection["package"]
              and graph.kind(graph.owning_namespace(identifier) or "") == "Package"]
    if len(owners) != 1:
        raise MemberProductError(f"the projection owner {projection['package']}::{projection['owner']} matches "
                                 f"{len(owners)} part definitions")
    return owners[0]


def _part_definition(graph: _Graph, name: str, owner: str) -> str | None:
    """The generated part definition of a projection name, by metatype, name, document and owner."""
    found = [identifier for identifier, element in graph.by_id.items()
             if element.get("@type") == "PartDefinition" and graph.name(identifier) == name
             and str(graph.sources.get(identifier, "")).startswith(PRODUCT_MODELS)]
    if len(found) > 1:
        raise MemberProductError(f"the projection name {name} matches {len(found)} part definitions of the "
                                 "generated product models")
    if found and owner not in graph.generals(found[0]):
        raise MemberProductError(f"the part definition {name} of the generated product models does not "
                                 "specialize the owner its feature model's projection names")
    return found[0] if found else None


def _projections(
    graph: _Graph,
    elements: Sequence[Mapping[str, Any]],
    element_sources: Mapping[str, str],
    *,
    kernel_bindings: Mapping[str, str],
    external_references: Iterable[Mapping[str, Any]],
    library_source: str,
    governed_scope: Mapping[str, Any] | None,
) -> list[tuple[Mapping[str, Any], Any, str | None]]:
    """(configuration, its projection name, the generated part definition or None) for every PLEML
    feature configuration: the configuration and its name by the evaluator, the part definition by
    validated identity (:func:`_part_definition`)."""
    model_sources = sorted({source for source in element_sources.values() if source.startswith(PLEML_ROOTS)})
    evaluation = pleml_configuration.evaluate(
        elements, element_sources, model_sources=model_sources, library_source=library_source,
        external_references=external_references, kernel_bindings=kernel_bindings,
        governed_scope=governed_scope)
    found = []
    for model in evaluation["feature_models"]:
        configurations = model["configurations"]
        owner = _projection_owner(graph, model.get("projection")) if configurations else None
        for configuration in configurations:
            name = configuration.get("projection_name")
            definition = _part_definition(graph, name, owner) if isinstance(name, str) and owner else None
            found.append((configuration, name, definition))
    return found


def configuration_projections(
    elements: Iterable[Mapping[str, Any]],
    element_sources: Mapping[str, str],
    *,
    kernel_bindings: Mapping[str, str],
    external_references: Iterable[Mapping[str, Any]] = (),
    library_source: str = pleml_configuration.LIBRARY_SOURCE,
    governed_scope: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Every PLEML feature configuration of an export or of API objects with their source documents, with
    the part definition of its product-model projection bound by validated identity (None when no
    generated product model declares it). The derived ``configuredBy`` fact of a configured product
    reads it. ``governed_scope`` is the record of the production scope validator, which the evaluator
    needs to read the feature models' correspondences, as for :func:`member_product_applications`.
    Raises :class:`MemberProductError` on an ambiguous identity, and the evaluator's ``PlemlShapeError``
    on a shape it does not accept."""
    elements = list(elements)
    graph = _Graph(elements, element_sources)
    return [{"configuration": configuration["configuration"], "element_id": configuration["element_id"],
             "valid": configuration["valid"], "projection_name": name, "part_definition": definition}
            for configuration, name, definition in _projections(
                graph, elements, element_sources, kernel_bindings=kernel_bindings,
                external_references=external_references, library_source=library_source,
                governed_scope=governed_scope)]


def member_product_applications(
    elements: Iterable[Mapping[str, Any]],
    element_sources: Mapping[str, str],
    *,
    kernel_bindings: Mapping[str, str],
    external_references: Iterable[Mapping[str, Any]] = (),
    library_source: str = pleml_configuration.LIBRARY_SOURCE,
    governed_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive ``appliesToMemberProduct`` for every PLEML feature configuration of an export.

    ``elements`` and ``element_sources`` are an export or the served model's
    API objects with their source documents; ``kernel_bindings`` maps the
    ontology classes to their validated element identities (ADR 0011), as
    ``pleml_configuration.kernel_bindings`` computes them. ``governed_scope``
    is the record of the production scope validator
    (``product_line_scope.validate_scope_elements``): the evaluator reads the
    feature models' correspondences to the governed scope only with it, as
    the receipts do. Raises :class:`MemberProductError` on an ambiguous
    identity or on a configuration that applies to more than one member
    product.
    """
    elements = list(elements)
    graph = _Graph(elements, element_sources)
    member_root = kernel_bindings.get(MEMBER_PRODUCT)
    if member_root is None or graph.kind(member_root) != "PartDefinition":
        raise MemberProductError("the kernel class MemberProduct is not bound to a part definition")
    projections = _projections(graph, elements, element_sources, kernel_bindings=kernel_bindings,
                               external_references=external_references, library_source=library_source,
                               governed_scope=governed_scope)
    members = [identifier for identifier, element in graph.by_id.items()
               if element.get("@type") == "PartDefinition" and identifier != member_root
               and graph.specializes(identifier, member_root)]
    rows = []
    for configuration, name, definition in projections:
        applied = []
        if definition is not None:
            for member in members:
                usages = graph.owned_usages_typed_by(member, definition)
                if usages:
                    applied.append({"declared_name": graph.name(member), "element_id": member,
                                    "source": element_sources.get(member), "usages": sorted(usages)})
        if len(applied) > 1:
            raise MemberProductError(
                f"the configuration {configuration['configuration']} applies to {len(applied)} member products "
                f"({', '.join(sorted(str(item['declared_name']) for item in applied))}); a configuration "
                "applies to one member product at most")
        rows.append({
            "configuration": configuration["configuration"],
            "element_id": configuration["element_id"],
            "source": element_sources.get(configuration["element_id"]),
            "valid": configuration["valid"],
            "projection_name": name,
            "part_definition": None if definition is None else {
                "element_id": definition, "source": element_sources.get(definition)},
            "member_product": applied[0] if applied else None,
        })
    return {
        "schema": SCHEMA,
        "relation": "appliesToMemberProduct",
        "derived": True,
        "member_product_root": member_root,
        "configurations": sorted(rows, key=lambda row: str(row["source"])),
        "runtime_queryable": False,
    }
