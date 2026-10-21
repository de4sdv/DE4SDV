"""DE4SDV evaluation and derivation of PLEML feature configurations (ADR 0022).

PLEML defines feature models, feature configurations and constraints, but no
derivation, and the pinned serializer does not evaluate constraint bodies. This
module owns both semantics for DE4SDV. It reads serializer and API element
objects only (ADR 0011): no textual SysML is parsed, nothing is inferred from a
name alone, and anything outside the accepted shapes is refused.

Identity. A PLEML library element is recognised by its metatype, its declared
name and the serializer-recorded source document of the library; a kernel
definition by its metatype, declared name and the reviewed kernel document, or
by a validated binding. Never by a name alone or by a name in another document.
The production export's options and its element order change nothing: implied
relationships carry nothing authored, and document order comes from the ordered
ownership properties.

What one evaluation decides, per feature tree:

* the tree: every feature carries the ``#feature`` keyword and an explicit
  multiplicity; a feature that sibling features subset is a group whose
  multiplicity bounds the number of its selected members;
* every configuration: its settings (``[1]`` selected, ``[0]`` deselected),
  omitted optional features (deselected) and implied mandatory ones
  (selected); the bounds of every feature and group; that it owns only
  features; the Development binding time; the requires, XOR and implies
  constraints with the library's semantics;
* the feature bindings: one feature per shared-asset variant, every variant of
  a bound variation bound, one exactly-one group per variation, Development
  binding time, the projection owner, and no binding to a derived variant;
* the DE4SDV derivation rules: well-formedness, a total agreement of rules and
  pair exclusions over every source pair, and, for a valid configuration,
  exactly one matching rule per derived variation;
* with the governed scope, the admission authority (ADR 0014): whether each
  configuration is admitted, read from the correspondences of its features.
  Admission requires validity: an invalid configuration is never admitted.

Nothing here executes a PLEML expression natively, qualifies anything or
grants authority: every report says ``native_expression_executed: false``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import product
from typing import Any, Iterable, Mapping, Sequence

from de4sdv.semantic import pleml_package
from de4sdv.sysml_api.repository import element_id, reference_ids

SCHEMA = "de4sdv.pleml-configuration-evaluation/v1"

# -- dependencies on the other steps (one place) ------------------------------------------
#
# The library is the pinned PLEML package of the production Sysand lock:
# ``pleml_package`` owns its path. The kernel metadata definitions come from step S2k: five
# plain metadata definitions of DE4SDV_ProductLineDerivation, each an
# ontology class of the same name that ``validate_ontology_bindings`` binds by
# metatype, declared name and the source file below. Only this block names
# them.

#: Serializer source label of the pinned PLEML library (Sysand ``=1.1.1``).
LIBRARY_SOURCE = pleml_package.LIBRARY_PATH.as_posix()
#: The reviewed kernel document declaring the derivation and projection metadata.
KERNEL_SOURCE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line_derivation.sysml"


@dataclass(frozen=True)
class KernelVocabulary:
    """The kernel metadata definitions the evaluator reads, by declared name, with their attributes.

    ``derived_variation`` and ``derivation_rule`` annotate dependencies (the
    client is the derived variation or the derived variant, the suppliers the
    source features or the premises); the others annotate a feature model, a
    configuration or a feature.
    """

    derived_variation: str
    derivation_rule: str
    projection: str
    projection_fields: tuple[tuple[str, str], ...]  # (kernel attribute, receipt key)
    projection_name: str
    projection_name_field: str
    unassigned_binding_time: str
    metatype: str = "MetadataDefinition"

    def definitions(self) -> dict[str, tuple[str, str, tuple[str, ...]]]:
        """Role -> (metatype, declared name, attribute names)."""
        return {
            "derived_variation": (self.metatype, self.derived_variation, ()),
            "derivation_rule": (self.metatype, self.derivation_rule, ()),
            "projection": (self.metatype, self.projection, tuple(field for field, _ in self.projection_fields)),
            "projection_name": (self.metatype, self.projection_name, (self.projection_name_field,)),
            "unassigned_binding_time": (self.metatype, self.unassigned_binding_time, ()),
        }


KERNEL = KernelVocabulary(
    derived_variation="DerivedVariation",
    derivation_rule="DerivationRule",
    projection="ProductModelProjection",
    projection_fields=(("packageName", "package"), ("ownerName", "owner"), ("label", "label")),
    projection_name="ProductModelProjectionName",
    projection_name_field="partDefinitionName",
    unassigned_binding_time="UnassignedBindingTime",
)

# -- reasons -----------------------------------------------------------------------------

#: Every rejection reason this module reports and its reason class, which a receipt records.
REASON_CLASSES: dict[str, str] = {
    "upper-bound": "upper-bound",
    "lower-bound": "lower-bound",
    "unknown-feature": "unknown-feature",
    "not-a-feature": "unknown-feature",
    "derived-variant-not-selectable": "derived-variant-not-selectable",
    "constraint": "constraint",
    "pair-exclusion": "pair-exclusion",
    "derivation-no-rule": "derivation-no-rule",
    "derivation-ambiguous": "derivation-ambiguous",
    "binding-time": "binding-time",
    "orphan-selection": "selection-structure",
    "configuration-metadata": "configuration-metadata",
    "model-integrity": "model-integrity",
}

LIFE_CYCLE = {"Development": 1, "Production": 2, "Operation": 3}
IDENTIFIER = re.compile(r"[A-Za-z_]\w*")

#: The governed-scope sets a correspondence may name, with the class each confers (ADR 0014). The
#: integration-mode alternatives confer ``admitted-alternative``. A derived realization corresponds to
#: its alternative, never to a feature.
SCOPE_SCHEMA = "de4sdv-aebs-product-line-scope-validation/v1"
SCOPE_CLASSES = (("common_core", "common"), ("reference_only", "reference-only"), ("deferred", "deferred"),
                 ("excluded_system2", "excluded"))
ADMISSIBLE = frozenset({"admitted-alternative", "common"})

_SPECIALIZATIONS = {"Subsetting", "Redefinition", "ReferenceSubsetting", "FeatureTyping"}
_SKIPPED = _SPECIALIZATIONS | {"Subclassification", "Import", "NamespaceImport", "MembershipImport"}
_LITERALS = {"LiteralString": str, "LiteralBoolean": bool, "LiteralInteger": int}
_STRUCTURE = {"MultiplicityRange", "Documentation", "Comment"}


class PlemlShapeError(ValueError):
    """The element graph is missing, ambiguous or outside the accepted shapes (refused)."""


@dataclass(frozen=True)
class Multiplicity:
    lower: int
    upper: int | None

    def text(self) -> str:
        return f"[{self.lower}..{'*' if self.upper is None else self.upper}]"

    def to_dict(self) -> dict[str, Any]:
        return {"lower": self.lower, "upper": self.upper}


EXACTLY_ONE = Multiplicity(1, 1)
OPTIONAL = Multiplicity(0, 1)
NONE = Multiplicity(0, 0)


@dataclass(frozen=True)
class _Outside:
    """A referent outside the element set (pruned, or in the standard library)."""

    identifier: str


class _GovernedScope:
    """The governed product-line scope, the admission authority, as the production scope validator reads it."""

    def __init__(self, record: Mapping[str, Any], graph: "_Graph") -> None:
        if record.get("schema") != SCOPE_SCHEMA:
            raise PlemlShapeError("the governed scope is not a validated product-line scope record")
        self.source = str(record["scope_source"])
        self.classes: dict[str, tuple[str, str]] = {}
        sets = [("admitted-alternative", record["vehicle_platform_integration_mode"]["alternatives"])]
        sets += [(kind, record[key]) for key, kind in SCOPE_CLASSES]
        for kind, members in sets:
            for name, identifier in sorted(members.items()):
                if identifier in self.classes:
                    raise PlemlShapeError(f"the governed scope classifies {name} twice")
                if graph.sources.get(identifier) != self.source:
                    raise PlemlShapeError(f"governed-scope element {name} is not in {self.source}")
                self.classes[identifier] = (kind, name)
        self.derived = {identifier: name for name, identifier in record["derived_realization"].items()}
        self.common = dict(sorted(record["common_core"].items()))


# -- the element graph -------------------------------------------------------------------


class _Graph:
    """Indexes over one element set: identity, ownership, specializations and pruned references.

    Relationships the language implies (``isImplied``), other than memberships,
    stay out of the ownership and specialization indexes. They follow from the
    implicit specializations of KerML, carry nothing authored, and an export
    carries them or not depending on its options.

    Document order comes from the ordered ``ownedRelationship`` and
    ``ownedRelatedElement`` properties, never from the order of the element
    list: an API export lists elements in no document order.
    """

    def __init__(self, elements: Iterable[dict[str, Any]], sources: Mapping[str, str],
                 external_references: Iterable[Mapping[str, Any]] = ()) -> None:
        self.by_id: dict[str, dict[str, Any]] = {}
        listed: dict[str, int] = {}
        for index, element in enumerate(elements):
            identifier = element_id(element)
            if not identifier or not isinstance(element.get("@type"), str):
                raise PlemlShapeError("every element requires @id and @type")
            if identifier in self.by_id:
                raise PlemlShapeError(f"duplicate element identity {identifier}")
            self.by_id[identifier] = element
            listed[identifier] = index
        missing = sorted(identifier for identifier in self.by_id if identifier not in sources)
        if missing:
            raise PlemlShapeError(f"elements without a source document: {missing[:3]}")
        self.sources = {identifier: sources[identifier] for identifier in self.by_id}
        self.order = self._document_order(listed)
        self.external: dict[tuple[str, str], str] = {}
        for record in external_references:
            source, path, target = (record.get("source_element_id"), record.get("property_path"),
                                    record.get("target_id"))
            if isinstance(source, str) and isinstance(path, str) and isinstance(target, str):
                self.external[(source, path)] = target
        self.owned: dict[str, list[str]] = {}
        self.specializations: dict[str, list[str]] = {}
        for identifier, element in self.by_id.items():
            if element.get("isImplied") is True and not element["@type"].endswith("Membership"):
                continue
            owner = self.target(element, "owningRelatedElement")
            if owner is not None:
                self.owned.setdefault(owner, []).append(identifier)
            if element["@type"] in _SPECIALIZATIONS:
                specific = self.target(element, "specific") or owner
                if specific is not None:
                    self.specializations.setdefault(specific, []).append(identifier)
        for index in (self.owned, self.specializations):
            for items in index.values():
                items.sort(key=self.order.__getitem__)

    def _document_order(self, listed: Mapping[str, int]) -> dict[str, tuple[Any, ...]]:
        """Each element's position: its document and root, then its index under each owner.

        An element its owner does not list comes after the listed ones. The
        element list orders only the roots of a document.
        """
        index_of: dict[tuple[str, str], int] = {}
        for identifier, element in self.by_id.items():
            for key in ("ownedRelationship", "ownedRelatedElement"):
                value = element.get(key)
                for position, item in enumerate(reference_ids(value) if isinstance(value, list) else []):
                    index_of.setdefault((identifier, item), position)
        unlisted = len(self.by_id)
        order: dict[str, tuple[Any, ...]] = {}
        for start in self.by_id:
            chain: list[tuple[str, int]] = []
            current = start
            while current not in order:
                if any(item == current for item, _ in chain):
                    raise PlemlShapeError(f"the ownership of {current} is cyclic")
                element = self.by_id[current]
                container = element_id(element.get("owningRelationship"))
                if container not in self.by_id:
                    container = element_id(element.get("owningRelatedElement"))
                if container not in self.by_id:
                    order[current] = (self.sources[current], listed[current])
                    break
                chain.append((current, index_of.get((container, current), unlisted + listed[current])))
                current = container
            position = order[current]
            for item, index in reversed(chain):
                position = (*position, index)
                order[item] = position
        return order

    def kind(self, identifier: str) -> str:
        element = self.by_id.get(identifier)
        if element is None:
            raise PlemlShapeError(f"{identifier} is not in the element set")
        return str(element["@type"])

    def name(self, identifier: str | None) -> str | None:
        element = self.by_id.get(identifier or "") or {}
        value = element.get("declaredName") or element.get("name")
        return value if isinstance(value, str) else None

    def short_name(self, identifier: str) -> str | None:
        value = (self.by_id.get(identifier) or {}).get("declaredShortName")
        return value if isinstance(value, str) else None

    def label(self, identifier: str | None) -> str:
        return self.name(identifier) or str(identifier)

    def target(self, element: Mapping[str, Any], key: str) -> str | None:
        """The one referent of ``key``, in the set or recorded as pruned (``None`` when absent)."""
        value = element.get(key)
        if isinstance(value, list):
            ids = reference_ids(value)
            if len(ids) > 1:
                raise PlemlShapeError(f"{element.get('@id')}.{key} has {len(ids)} referents")
            return ids[0] if ids else self.external.get((str(element.get("@id")), f"{key}[0]"))
        if value is not None:
            return element_id(value)
        return self.external.get((str(element.get("@id")), key))

    def targets(self, element: Mapping[str, Any], key: str) -> list[str]:
        value = element.get(key)
        found = reference_ids(value) if isinstance(value, list) else (
            [element_id(value)] if isinstance(value, dict) and element_id(value) else [])
        prefix = f"{key}["
        found += [target for (source, path), target in self.external.items()
                  if source == element.get("@id") and (path == key or path.startswith(prefix))]
        return list(dict.fromkeys(item for item in found if item))

    def owner(self, identifier: str | None) -> str | None:
        relationship = element_id((self.by_id.get(identifier or "") or {}).get("owningRelationship"))
        if relationship is None or relationship not in self.by_id:
            return None
        return self.target(self.by_id[relationship], "owningRelatedElement")

    def owning_relationship_kind(self, identifier: str) -> str | None:
        relationship = element_id(self.by_id.get(identifier, {}).get("owningRelationship"))
        return self.by_id[relationship]["@type"] if relationship in self.by_id else None

    def relationships(self, owner: str, *kinds: str) -> list[str]:
        """Relationships owned by ``owner`` in document order, optionally of the given metatypes."""
        return [item for item in self.owned.get(owner, []) if not kinds or self.by_id[item]["@type"] in kinds]

    def endpoints(self, dependency: str, primary: str, alias: str) -> list[str]:
        """One endpoint list of a dependency, whether the serializer emits it under one name or both."""
        element = self.by_id[dependency]
        first, second = self.targets(element, primary), self.targets(element, alias)
        if first and second and set(first) != set(second):
            raise PlemlShapeError(f"dependency {self.label(dependency)} has different {primary} and {alias} lists")
        return first or second

    def member_of(self, relationship: str) -> str | None:
        element = self.by_id[relationship]
        member = self.target(element, "memberElement")
        if member is None:
            owned = reference_ids(element.get("ownedRelatedElement"))
            member = owned[0] if len(owned) == 1 else None
        return member

    def members(self, owner: str, kind: str, *kinds: str, member_name: str | None = None) -> list[str]:
        """Members of ``owner`` through memberships of the given metatypes, in document order."""
        result = []
        for relationship in self.relationships(owner, kind, *kinds):
            if member_name is not None and self.by_id[relationship].get("memberName") != member_name:
                continue
            member = self.member_of(relationship)
            if member is None:
                raise PlemlShapeError(f"a membership of {self.label(owner)} has no member")
            result.append(member)
        return result

    def one_member(self, owner: str, kind: str, *, member_name: str | None = None, what: str) -> str:
        found = self.members(owner, kind, member_name=member_name)
        if len(found) != 1:
            raise PlemlShapeError(f"{what}: expected one, found {len(found)}")
        return found[0]

    def generals(self, specific: str, *kinds: str) -> list[str]:
        result = []
        for relationship in self.specializations.get(specific, []):
            element = self.by_id[relationship]
            if kinds and element["@type"] not in kinds:
                continue
            general = self.target(element, "general")
            if general is None:
                raise PlemlShapeError(f"{element['@type']} {relationship} of {self.label(specific)} has no general")
            result.append(general)
        return result

    def metadata_usages(self, annotated: str) -> list[str]:
        """Metadata usages owned by ``annotated`` (keyword form) or by an annotation of it."""
        found = [member for member in self.members(annotated, "OwningMembership")
                 if self.by_id.get(member, {}).get("@type") == "MetadataUsage"]
        for relationship in self.relationships(annotated, "Annotation"):
            found += [usage for usage in reference_ids(self.by_id[relationship].get("ownedRelatedElement"))
                      if self.by_id.get(usage, {}).get("@type") == "MetadataUsage"]
        return found

    # -- values ----------------------------------------------------------------------------

    def value_expression(self, owner: str) -> tuple[str, dict[str, Any]] | None:
        relationships = self.relationships(owner, "FeatureValue")
        if not relationships:
            return None
        if len(relationships) != 1:
            raise PlemlShapeError(f"{self.label(owner)} has {len(relationships)} feature values")
        expression = self.member_of(relationships[0])
        if expression is None or expression not in self.by_id:
            raise PlemlShapeError(f"the value of {self.label(owner)} has no expression in the set")
        return expression, self.by_id[relationships[0]]

    def referents(self, expression: str) -> list[str | _Outside]:
        """Referents of a reference or of a ``(a, b, ...)`` sequence, in order."""
        kind = self.kind(expression)
        if kind == "FeatureReferenceExpression":
            memberships = self.relationships(expression, "Membership")
            if len(memberships) != 1:
                raise PlemlShapeError(f"reference expression {expression} has {len(memberships)} referents")
            target = self.target(self.by_id[memberships[0]], "memberElement")
            if target is None:
                raise PlemlShapeError(f"reference expression {expression} has no referent")
            return [target] if target in self.by_id else [_Outside(target)]
        if kind == "OperatorExpression" and self.by_id[expression].get("operator") == ",":
            result: list[str | _Outside] = []
            for parameter in self.members(expression, "ParameterMembership"):
                value = self.value_expression(parameter)
                if value is None:
                    raise PlemlShapeError(f"sequence parameter {parameter} has no value")
                result += self.referents(value[0])
            return result
        raise PlemlShapeError(f"unsupported value expression {kind} ({expression})")

    def value_referents(self, owner: str) -> list[str | _Outside]:
        value = self.value_expression(owner)
        return self.referents(value[0]) if value else []

    def literal(self, owner: str) -> Any:
        value = self.value_expression(owner)
        if value is None:
            raise PlemlShapeError(f"{self.label(owner)} has no value")
        element = self.by_id[value[0]]
        expected = _LITERALS.get(element["@type"])
        if expected is None or not isinstance(element.get("value"), expected):
            raise PlemlShapeError(f"{self.label(owner)} carries no literal value")
        return element["value"]

    def multiplicity(self, usage: str) -> Multiplicity | None:
        """The explicit ``[lower..upper]`` of a usage, order-independent over both serializer shapes."""
        ranges = [member for member in self.members(usage, "OwningMembership")
                  if self.by_id.get(member, {}).get("@type") == "MultiplicityRange"]
        if not ranges:
            return None
        if len(ranges) != 1:
            raise PlemlShapeError(f"{self.label(usage)} has {len(ranges)} multiplicity ranges")
        bounds: list[int | None] = []
        for bound in self.members(ranges[0], "OwningMembership"):
            if self.kind(bound) == "OperatorExpression" and self.by_id[bound].get("operator") == "..":
                for parameter in self.members(bound, "ParameterMembership"):
                    value = self.value_expression(parameter)
                    if value is None:
                        raise PlemlShapeError(f"a range bound of {self.label(usage)} has no value")
                    bounds.append(self._bound(value[0], usage))
            else:
                bounds.append(self._bound(bound, usage))
        integers = [bound for bound in bounds if bound is not None]
        infinities = len(bounds) - len(integers)
        if len(bounds) == 1:
            return Multiplicity(0, None) if infinities else Multiplicity(integers[0], integers[0])
        if len(bounds) == 2 and infinities == 1:
            return Multiplicity(integers[0], None)
        if len(bounds) == 2 and not infinities:
            return Multiplicity(min(integers), max(integers))
        raise PlemlShapeError(f"the multiplicity of {self.label(usage)} has an ambiguous bound set")

    def _bound(self, bound: str, usage: str) -> int | None:
        element = self.by_id.get(bound) or {}
        if element.get("@type") == "LiteralInfinity":
            return None
        if element.get("@type") == "LiteralInteger" and isinstance(element.get("value"), int) and element["value"] >= 0:
            return element["value"]
        raise PlemlShapeError(f"a multiplicity bound of {self.label(usage)} is no natural or infinity literal")


# -- identity ----------------------------------------------------------------------------


class _Identity:
    """PLEML library and kernel elements by metatype, declared name and source document."""

    LIBRARY_DEFINITIONS = {
        "FeatureModelMetadata": "MetadataDefinition", "FeatureTreeMetadata": "MetadataDefinition",
        "FeatureMetadata": "MetadataDefinition", "FeatureConfigurationMetadata": "MetadataDefinition",
        "FeatureBinding": "MetadataDefinition", "FeatureConfigurationBinding": "MetadataDefinition",
        "FeatureModel": "OccurrenceDefinition", "FeatureConfiguration": "OccurrenceDefinition",
        "FeatureTree": "OccurrenceDefinition", "Feature": "OccurrenceDefinition",
        "FeatureOperand": "OccurrenceDefinition", "LifeCycleKind": "EnumerationDefinition",
        "RequiresConstraint": "ConstraintDefinition", "XORConstraint": "ConstraintDefinition",
        "ImpliesConstraint": "ConstraintDefinition",
    }
    CONSTRAINT_DEFINITIONS = {"requires": "RequiresConstraint", "xor": "XORConstraint", "implies": "ImpliesConstraint"}

    def __init__(self, graph: _Graph, library_source: str, kernel_source: str, vocabulary: KernelVocabulary,
                 kernel_bindings: Mapping[str, str] | None) -> None:
        self.graph = graph
        self.vocabulary = vocabulary
        self.library_source, self.kernel_source = library_source, kernel_source
        declared: dict[tuple[str, str], list[str]] = {}
        for identifier, element in graph.by_id.items():
            if graph.sources[identifier] == library_source and isinstance(element.get("declaredName"), str):
                declared.setdefault((element["@type"], element["declaredName"]), []).append(identifier)
        self.lib: dict[str, str] = {}
        for name, kind in self.LIBRARY_DEFINITIONS.items():
            found = declared.get((kind, name), [])
            if len(found) != 1:
                raise PlemlShapeError(f"the PLEML library ({library_source}) declares {len(found)} {kind} {name}")
            self.lib[name] = found[0]
        self.library_usages = {name: set(declared.get(("OccurrenceUsage", name), []))
                               for name in ("featureTrees", "featureConfigurations", "features", "featureModels")}
        self.binding_time = self._library_member("Feature", "bindingTime", "AttributeUsage")
        self.constraint_bases = {kind: self._library_member("Feature", f"{kind}Features", "AssertConstraintUsage")
                                 for kind in ("requires", "xor", "implies")}
        self.life_cycle = {literal: str(graph.name(literal))
                           for literal in graph.members(self.lib["LifeCycleKind"], "VariantMembership")
                           if graph.name(literal) in LIFE_CYCLE}
        if sorted(self.life_cycle.values()) != sorted(LIFE_CYCLE):
            raise PlemlShapeError("the library's LifeCycleKind literals are not Development, Production, Operation")
        constraints = graph.one_member(self.lib["FeatureConfiguration"], "FeatureMembership",
                                       member_name="featureConstraints",
                                       what="FeatureConfiguration::featureConstraints in the library")
        parameter = graph.one_member(constraints, "FeatureMembership", member_name="featureConfiguration",
                                     what="featureConstraints::featureConfiguration in the library")
        that = graph.value_referents(parameter)
        if len(that) != 1 or not isinstance(that[0], _Outside):
            raise PlemlShapeError("the library's own `featureConfiguration = that` is not one out-of-set referent")
        self.that = that[0].identifier
        self.metadata_names = {identifier: name for name, identifier in self.lib.items()}
        self.kernel: dict[str, str] = {}
        self.kernel_fields: dict[str, dict[str, str]] = {}
        for role, (kind, name, fields) in vocabulary.definitions().items():
            # Kernel identity is the validated binding only (ADR 0011): no name is matched here.
            identifier = (kernel_bindings or {}).get(name)
            if identifier is None:
                continue  # unbound: a model use of this definition is refused as a homonym
            if graph.kind(identifier) != kind:
                raise PlemlShapeError(f"the validated binding of {name} is a {graph.kind(identifier)}, not {kind}")
            self.kernel[role] = identifier
            self.metadata_names[identifier] = f"kernel:{role}"
            self.kernel_fields[role] = {}
            for field_name in fields:
                owned = [member for member in graph.members(identifier, "FeatureMembership")
                         if graph.name(member) == field_name]
                if len(owned) != 1:
                    raise PlemlShapeError(f"kernel definition {name} has {len(owned)} features named {field_name}")
                self.kernel_fields[role][field_name] = owned[0]

    def refuse_homonyms(self, model_sources: Sequence[str]) -> None:
        """A model usage typed by a same-named definition of another document is refused, never ignored."""
        graph = self.graph
        recognised = {name: identifier for name, identifier in self.lib.items() if name in self.LIBRARY_DEFINITIONS}
        definitions = self.vocabulary.definitions()
        for role, (_, name, _) in definitions.items():
            recognised.setdefault(name, self.kernel.get(role, ""))
        kernel_names = {name for _, name, _ in definitions.values()}
        for usage, element in graph.by_id.items():
            if graph.sources[usage] not in model_sources:
                continue
            for definition in graph.generals(usage, "FeatureTyping"):
                name = graph.name(definition)
                if name in recognised and definition != recognised[name]:
                    owner = "kernel" if name in kernel_names else "PLEML library"
                    raise PlemlShapeError(f"{graph.label(usage)} is typed by a homonym of the {owner} definition "
                                          f"{name} ({graph.sources.get(definition, 'outside the set')})")

    def refuse_about_metadata(self, model_sources: Sequence[str]) -> None:
        """Consumed metadata is read only where its annotated element owns it; ``about`` placement is refused."""
        graph = self.graph
        consumed = set(self.metadata_names)
        for usage, element in graph.by_id.items():
            if element["@type"] != "MetadataUsage" or graph.sources[usage] not in model_sources:
                continue
            definitions = [item for item in self.typings(usage) if item in consumed]
            if not definitions:
                continue
            name = graph.label(definitions[0])
            owner = graph.owner(usage)  # the element itself, or the annotated owner of a prefix annotation
            if owner is None:
                raise PlemlShapeError(f"{name} metadata usage {usage} has no owner among the evaluated elements")
            annotated = {graph.target(graph.by_id[relationship], "annotatedElement")
                         for relationship in graph.relationships(usage, "Annotation")}
            if annotated - {owner} or graph.kind(owner or "") in {"Package", "LibraryPackage", "Namespace"}:
                raise PlemlShapeError(f"{name} metadata is applied through an `about` annotation in "
                                      f"{graph.label(owner)}; apply it inside the body of the element it annotates")

    def _library_member(self, owner: str, name: str, kind: str) -> str:
        found = [member for member in self.graph.members(self.lib[owner], "FeatureMembership")
                 if self.graph.name(member) == name and self.graph.kind(member) == kind]
        if len(found) != 1:
            raise PlemlShapeError(f"the PLEML library declares {len(found)} {owner}::{name}")
        return found[0]

    def typings(self, usage: str) -> list[str]:
        return self.graph.generals(usage, "FeatureTyping")

    def metadata_kind(self, metadata: str) -> str:
        typings = self.typings(metadata)
        if len(typings) != 1:
            raise PlemlShapeError(f"metadata usage {metadata} has {len(typings)} types")
        return self.metadata_names.get(typings[0], f"other:{typings[0]}")

    def metadata_kinds(self, usage: str) -> list[str]:
        return [self.metadata_kind(metadata) for metadata in self.graph.metadata_usages(usage)]

    def is_typed(self, usage: str, role: str) -> bool:
        return self.kernel.get(role) is not None and self.kernel[role] in self.typings(usage)

    def record_fields(self, usage: str, role: str) -> tuple[dict[str, str], list[str]]:
        """(field name -> the usage's feature redefining it, the usage's other owned features)."""
        reverse = {feature: name for name, feature in self.kernel_fields.get(role, {}).items()}
        fields: dict[str, str] = {}
        others = []
        for member in self.graph.members(usage, "FeatureMembership"):
            redefined = [general for general in self.graph.generals(member, "Redefinition") if general in reverse]
            if len(redefined) > 1:
                raise PlemlShapeError(f"{self.graph.label(member)} redefines several kernel fields")
            if not redefined:
                others.append(member)
                continue
            name = reverse[redefined[0]]
            if name in fields:
                raise PlemlShapeError(f"{self.graph.label(usage)} sets {name} twice")
            fields[name] = member
        return fields, others


# -- the feature model -------------------------------------------------------------------


@dataclass
class _Feature:
    identifier: str
    name: str
    short_name: str | None
    owner: str  # the tree or an owning feature
    path: str
    multiplicity: Multiplicity
    order: tuple[Any, ...]
    group: str | None = None
    members: tuple[str, ...] = ()
    binding_time: str = "Development"
    binding_time_redefined: bool = False
    unassigned: bool = False

    @property
    def is_group(self) -> bool:
        return bool(self.members)


@dataclass
class _Constraint:
    identifier: str
    kind: str  # requires | xor | implies
    short_name: str | None
    owner: str | None  # None when the tree root owns it
    operand_a: tuple[str, ...]
    operand_b: tuple[str, ...]
    pair_exclusion: bool = False


@dataclass
class _Derivation:
    identifier: str
    name: str | None
    short_name: str | None
    variation: str
    rules: list[dict[str, Any]] = field(default_factory=list)
    source_groups: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.short_name or self.name or self.identifier


class _FeatureModel:
    """One feature tree with its features, constraints, bindings, rules and integrity errors."""

    def __init__(self, identity: _Identity, model_sources: Sequence[str], tree: str, definition: str | None,
                 scope: _GovernedScope | None = None) -> None:
        self.identity = identity
        self.scope = scope
        self.graph = identity.graph
        self.model_sources = set(model_sources)
        self.tree, self.definition = tree, definition
        self.features: dict[str, _Feature] = {}
        self.constraints: list[_Constraint] = []
        self.errors: list[str] = []
        self.consumed: set[str] = set()  # the dependencies this tree reads; evaluate() refuses any other
        for kind in identity.metadata_kinds(tree):
            if kind != "FeatureTreeMetadata":
                raise PlemlShapeError(f"unsupported metadata on the feature tree: {kind}")
        self._walk(tree, "")
        for feature in self.features.values():
            if feature.unassigned and feature.binding_time_redefined:
                raise PlemlShapeError(f"feature {feature.path} carries UnassignedBindingTime and redefines bindingTime")
        self._groups()
        for constraint in self.constraints:
            for feature in (*constraint.operand_a, *constraint.operand_b):
                if feature not in self.features:
                    raise PlemlShapeError(f"constraint {self.constraint_label(constraint)} references "
                                          f"{self.graph.label(feature)}, which is no feature of its tree")
        self.projection = self._projection()
        dependencies = self._dependencies()
        self.bindings = self._bindings(dependencies["binding"])
        self.derivations = self._derivations(dependencies["derived-variation"], dependencies["rule"])
        self._classify_pair_exclusions()
        self.agreement = self._agreement()
        self._binding_integrity()
        self.correspondences = self._correspondences() if scope is not None else {}

    def path(self, feature: str | None) -> str | None:
        return self.features[feature].path if feature in self.features else None

    def constraint_label(self, constraint: _Constraint) -> str:
        return constraint.short_name or self.graph.label(constraint.identifier)

    # -- tree ------------------------------------------------------------------------------

    def _walk(self, owner: str, prefix: str) -> None:
        graph, identity = self.graph, self.identity
        for relationship in graph.relationships(owner):
            kind = graph.kind(relationship)
            if kind in _SKIPPED:
                continue
            if kind == "Annotation":
                if owner != self.tree:
                    for metadata in reference_ids(graph.by_id[relationship].get("ownedRelatedElement")):
                        self._feature_metadata(owner, metadata)
                continue
            if not kind.endswith("Membership") and kind != "FeatureValue":
                raise PlemlShapeError(f"unsupported {kind} relationship of {graph.label(owner)} in the feature tree")
            member = graph.member_of(relationship)
            if member is None or member not in graph.by_id:
                raise PlemlShapeError(f"a membership of {graph.label(owner)} has no member in the set")
            member_kind = graph.kind(member)
            if member_kind in _STRUCTURE:
                continue
            if member_kind == "MetadataUsage":
                if owner != self.tree:
                    self._feature_metadata(owner, member)
                continue
            if kind == "FeatureValue":
                if owner == self.tree or not graph.by_id[relationship].get("isDefault") or member_kind != "NullExpression":
                    raise PlemlShapeError(f"{graph.label(owner)} has a value other than `default null`")
                continue
            if member_kind == "AssertConstraintUsage":
                self.constraints.append(self._constraint(member, None if owner == self.tree else owner))
                continue
            if member_kind == "AttributeUsage" and identity.binding_time in graph.generals(member, "Redefinition"):
                if owner == self.tree:
                    raise PlemlShapeError("the feature tree redefines its binding time")
                self.features[owner].binding_time = self._life_cycle(member)
                self.features[owner].binding_time_redefined = True
                continue
            if kind != "FeatureMembership" or member_kind not in {"OccurrenceUsage", "PartUsage"}:
                raise PlemlShapeError(f"unsupported {member_kind} {graph.label(member)} in the feature tree")
            if "FeatureMetadata" not in identity.metadata_kinds(member):
                raise PlemlShapeError(f"tree occurrence {graph.label(member)} lacks the #feature keyword")
            name = graph.name(member)
            multiplicity = graph.multiplicity(member)
            if not name or multiplicity is None:
                raise PlemlShapeError(f"tree feature {graph.label(member)} needs a name and an explicit multiplicity")
            path = f"{prefix}.{name}" if prefix else name
            if any(item.path == path for item in self.features.values()):
                raise PlemlShapeError(f"duplicate feature path {path}")
            for typing in identity.typings(member):
                if typing != identity.lib["Feature"]:
                    raise PlemlShapeError(f"tree feature {path} is typed by {graph.label(typing)}; a PLEML feature is "
                                          "typed by the library's Feature only, never by a product-line "
                                          "characteristic")
            self.features[member] = _Feature(member, name, graph.short_name(member), owner, path, multiplicity,
                                             graph.order[member])
            self._walk(member, path)

    def _feature_metadata(self, feature: str, metadata: str) -> None:
        kind = self.identity.metadata_kind(metadata)
        if kind == "kernel:unassigned_binding_time":
            self.features[feature].unassigned = True
        elif kind != "FeatureMetadata":
            raise PlemlShapeError(f"unsupported metadata on feature {self.graph.label(feature)}: {kind}")

    def _life_cycle(self, attribute: str) -> str:
        referents = self.graph.value_referents(attribute)
        if len(referents) != 1 or referents[0] not in self.identity.life_cycle:
            raise PlemlShapeError(f"binding time {attribute} is not one LifeCycleKind literal of the library")
        return self.identity.life_cycle[referents[0]]  # type: ignore[index]

    def _groups(self) -> None:
        graph = self.graph
        library_bases = set().union(*self.identity.library_usages.values())
        for feature in self.features.values():
            for general in graph.generals(feature.identifier, "Subsetting"):
                if general in self.features:
                    if feature.group is not None:
                        raise PlemlShapeError(f"feature {feature.path} subsets more than one tree feature")
                    feature.group = general
                elif general not in library_bases:
                    raise PlemlShapeError(f"feature {feature.path} subsets {graph.label(general)}, outside its tree")
            if graph.generals(feature.identifier, "Redefinition", "ReferenceSubsetting"):
                raise PlemlShapeError(f"tree feature {feature.path} redefines a feature; only settings redefine")
        members: dict[str, list[str]] = {}
        for feature in self.features.values():
            if feature.group is None:
                continue
            parent = self.features[feature.group]
            if parent.owner != feature.owner:
                raise PlemlShapeError(f"group member {feature.path} is not a sibling of its group {parent.path}")
            if feature.multiplicity != OPTIONAL:
                raise PlemlShapeError(f"group member {feature.path} is {feature.multiplicity.text()}, not [0..1]")
            members.setdefault(parent.identifier, []).append(feature.identifier)
        for parent, items in members.items():
            self.features[parent].members = tuple(sorted(items, key=lambda item: self.features[item].order))
        for feature in self.features.values():
            if feature.group is not None and feature.is_group:
                raise PlemlShapeError(f"{feature.path} is a group member and a group (nested specialization)")

    def _constraint(self, usage: str, owner: str | None) -> _Constraint:
        graph, identity = self.graph, self.identity
        generals = graph.generals(usage, "Redefinition", "Subsetting")
        kinds = [kind for kind, base in identity.constraint_bases.items() if base in generals]
        if len(kinds) != 1 or len(generals) != 1:
            raise PlemlShapeError(f"constraint {graph.label(usage)} must subset or redefine exactly one of the "
                                  "requiresFeatures, xorFeatures and impliesFeatures bases")
        kind = kinds[0]
        allowed_types = {identity.lib[identity.CONSTRAINT_DEFINITIONS[kind]]}
        if not set(identity.typings(usage)) <= allowed_types:
            raise PlemlShapeError(f"constraint {graph.label(usage)} is typed other than by its library definition")
        parameter = graph.one_member(usage, "FeatureMembership", member_name="constrainedFeatures",
                                     what=f"constrainedFeatures of constraint {graph.label(usage)}")
        value = graph.value_expression(parameter)
        if value is None or graph.kind(value[0]) != "ConstructorExpression":
            raise PlemlShapeError(f"constraint {graph.label(usage)} does not construct a FeatureOperand")
        constructor = value[0]
        instantiated = [graph.target(graph.by_id[item], "memberElement")
                        for item in graph.relationships(constructor, "Membership")]
        if instantiated != [identity.lib["FeatureOperand"]]:
            raise PlemlShapeError(f"constraint {graph.label(usage)} does not instantiate the library's FeatureOperand")
        result = graph.one_member(constructor, "ReturnParameterMembership", what=f"result of {graph.label(usage)}")
        operands: dict[str, tuple[str, ...]] = {}
        for operand in ("operandA", "operandB"):
            argument = graph.one_member(result, "ParameterMembership", member_name=operand,
                                        what=f"{operand} of constraint {graph.label(usage)}")
            resolved = []
            for referent in graph.value_referents(argument):
                if isinstance(referent, _Outside):
                    if referent.identifier != identity.that or operand != "operandA" or owner is None:
                        raise PlemlShapeError(f"constraint {graph.label(usage)} references "
                                              f"{referent.identifier}, outside the set")
                    resolved.append(owner)
                else:
                    resolved.append(referent)
            operands[operand] = tuple(resolved)
        if kind in {"requires", "xor"}:
            if owner is None or operands["operandA"] != (owner,):
                raise PlemlShapeError(f"{kind} constraint {graph.label(usage)}: operand A must be its owner (that)")
            if not operands["operandB"]:
                raise PlemlShapeError(f"{kind} constraint {graph.label(usage)} names no feature in operand B")
        return _Constraint(usage, kind, graph.short_name(usage), owner, operands["operandA"], operands["operandB"])

    # -- metadata, bindings, rules ---------------------------------------------------------

    def _kernel_record(self, owner: str, role: str) -> str | None:
        identity = self.identity
        records = [usage for usage in self.graph.metadata_usages(owner) if identity.is_typed(usage, role)]
        if len(records) > 1:
            raise PlemlShapeError(f"{self.graph.label(owner)} carries {len(records)} {role} records")
        return records[0] if records else None

    def _projection(self) -> dict[str, Any] | None:
        if self.definition is None:
            return None
        record = self._kernel_record(self.definition, "projection")
        if record is None:
            return None
        fields, others = self.identity.record_fields(record, "projection")
        if others:
            raise PlemlShapeError("the projection metadata owns features outside its definition")
        projection = {}
        for attribute, key in self.identity.vocabulary.projection_fields:
            if attribute not in fields:
                raise PlemlShapeError(f"the projection metadata lacks {attribute}")
            projection[key] = self.graph.literal(fields[attribute])
        return projection

    def variation_of(self, element: str) -> str | None:
        """The variation usage that owns ``element`` through a variant membership."""
        if self.graph.owning_relationship_kind(element) != "VariantMembership":
            return None
        owner = self.graph.owner(element)
        return owner if owner and self.graph.by_id.get(owner, {}).get("isVariation") is True else None

    _ROLES = {"FeatureBinding": "binding", "kernel:derived_variation": "derived-variation",
              "kernel:derivation_rule": "rule", "FeatureConfigurationBinding": "configuration-binding"}

    #: What each role names as its client and supplier, for the refusal of an empty endpoint list.
    _ENDPOINTS = {"binding": ("binding", "variant", "feature"),
                  "derived-variation": ("derived variation", "variation", "source feature"),
                  "rule": ("derivation rule", "resulting variant", "premise")}

    def _endpoints(self, dependency: str, primary: str, alias: str) -> list[str]:
        return self.graph.endpoints(dependency, primary, alias)

    def _dependencies(self) -> dict[str, list[tuple[str, list[str], list[str]]]]:
        """The model's binding, derived-variation and rule dependencies: (dependency, clients, suppliers)."""
        graph = self.graph
        found: dict[str, list[tuple[str, list[str], list[str]]]] = {role: [] for role in self._ROLES.values()}
        for dependency in sorted(graph.by_id, key=graph.order.__getitem__):
            if graph.kind(dependency) != "Dependency" or graph.sources[dependency] not in self.model_sources:
                continue
            kinds = self.identity.metadata_kinds(dependency)
            roles = [self._ROLES[kind] for kind in kinds if kind in self._ROLES]
            if not roles:
                continue  # a plain dependency, such as a correspondence, is not consumed here
            if len(kinds) != 1:
                raise PlemlShapeError(f"dependency {graph.label(dependency)} carries {kinds}; one role per dependency")
            if roles[0] == "configuration-binding":
                raise PlemlShapeError(f"FeatureConfigurationBinding {graph.label(dependency)} is not read: the "
                                      "projection name metadata names a configuration's product")
            clients = self._endpoints(dependency, "client", "source")
            suppliers = self._endpoints(dependency, "supplier", "target")
            what, client, supplier = self._ENDPOINTS[roles[0]]
            if not clients or not suppliers:
                raise PlemlShapeError(f"{what} {graph.label(dependency)} names no {client if not clients else supplier}")
            found[roles[0]].append((dependency, clients, suppliers))
        return found

    def _here(self, features: Sequence[str], what: str) -> bool:
        """Whether ``features`` belong to this tree; a mix of trees is refused."""
        inside = [item in self.features for item in features]
        if any(inside) and not all(inside):
            raise PlemlShapeError(f"{what} names features of this tree and elements outside it")
        return bool(inside) and all(inside)

    def _bindings(self, dependencies: list[tuple[str, list[str], list[str]]]) -> list[dict[str, Any]]:
        graph = self.graph
        bindings = []
        for dependency, clients, suppliers in dependencies:
            if len(clients) != 1 or len(suppliers) != 1:
                raise PlemlShapeError(f"binding {graph.label(dependency)} has {len(clients)} clients and "
                                      f"{len(suppliers)} suppliers; one asset and one feature per binding")
            client, supplier = clients[0], suppliers[0]
            if not self._here([supplier], f"binding {graph.label(dependency)}"):
                continue  # it binds a feature of another tree
            self.consumed.add(dependency)
            variation = self.variation_of(client)
            if variation is None:
                raise PlemlShapeError(f"binding {graph.label(dependency)} binds {graph.label(client)}, which is no "
                                      "variant of a shared-asset variation")
            bindings.append({"binding": graph.name(dependency), "element_id": dependency,
                             "variation": graph.name(variation), "variation_id": variation,
                             "variant": graph.name(client), "variant_id": client,
                             "feature": self.features[supplier].path, "feature_id": supplier,
                             "feature_short_name": self.features[supplier].short_name})
        return sorted(bindings, key=lambda item: (self.features[item["feature_id"]].order, item["variation"]))

    def _derivations(self, derived: list[tuple[str, list[str], list[str]]],
                     rules: list[tuple[str, list[str], list[str]]]) -> list[_Derivation]:
        graph = self.graph
        derivations: dict[str, _Derivation] = {}
        for dependency, clients, suppliers in derived:
            if not self._here(suppliers, f"derived variation {graph.label(dependency)}"):
                continue
            self.consumed.add(dependency)
            if len(clients) != 1:
                raise PlemlShapeError(f"derived variation {graph.label(dependency)} must have exactly one client, "
                                      f"not {len(clients)}")
            if graph.by_id.get(clients[0], {}).get("isVariation") is not True:
                raise PlemlShapeError(f"derived variation {graph.label(dependency)} names no variation")
            if clients[0] in derivations:
                raise PlemlShapeError(f"variation {graph.label(clients[0])} is declared derived more than once")
            derivations[clients[0]] = _Derivation(
                dependency, graph.name(dependency), graph.short_name(dependency), clients[0],
                source_groups=sorted(suppliers, key=lambda item: self.features[item].order))
        for dependency, clients, suppliers in rules:
            if not self._here(suppliers, f"derivation rule {graph.label(dependency)}"):
                continue
            self.consumed.add(dependency)
            if len(clients) != 1:
                raise PlemlShapeError(f"derivation rule {graph.label(dependency)} must have exactly one client, "
                                      f"not {len(clients)}")
            variation = self.variation_of(clients[0])
            if variation is None or variation not in derivations:
                raise PlemlShapeError(f"derivation rule {graph.label(dependency)} does not yield one variant of a "
                                      "derived variation")
            derivations[variation].rules.append({
                "rule": graph.name(dependency) or graph.short_name(dependency) or dependency,
                "element_id": dependency, "result": clients[0],
                "premises": tuple(sorted(suppliers, key=lambda item: self.features[item].order))})
        for derivation in derivations.values():
            for group in derivation.source_groups:
                if not self.features[group].is_group:
                    self.errors.append(f"{derivation.label}: source feature {self.path(group)} is no group")
            for rule in derivation.rules:
                for premise in rule["premises"]:
                    if self.features[premise].group not in derivation.source_groups:
                        self.errors.append(f"rule {rule['rule']}: premise {self.path(premise)} is no alternative of "
                                           f"a source feature of {derivation.label}")
                groups = [self.features[premise].group for premise in rule["premises"]]
                if len(set(groups)) != len(groups):
                    self.errors.append(f"rule {rule['rule']}: its premises are no sub-features of distinct source "
                                       f"features of {derivation.label}")
        return sorted(derivations.values(), key=lambda item: graph.order[item.identifier])

    def _classify_pair_exclusions(self) -> None:
        pairs = set()
        for derivation in self.derivations:
            if len(derivation.source_groups) == 2:
                left, right = derivation.source_groups
                pairs |= {(left, right), (right, left)}
        for constraint in self.constraints:
            if constraint.kind != "xor" or constraint.owner is None:
                continue
            excluded_groups = {self.features[item].group for item in constraint.operand_b}
            owner_group = self.features[constraint.owner].group
            if len(excluded_groups) == 1 and (owner_group, next(iter(excluded_groups))) in pairs:
                constraint.pair_exclusion = True

    def _agreement(self) -> list[dict[str, Any]]:
        """Total over every source pair: exactly one rule or exactly one exclusion (R10)."""
        graph = self.graph
        results = []
        for derivation in self.derivations:
            groups = derivation.source_groups
            if len(groups) != 2:
                self.errors.append(f"{derivation.label}: the agreement check needs two source groups, found "
                                   f"{len(groups)}")
                continue
            for group in groups:
                if self.features[group].multiplicity != EXACTLY_ONE:
                    self.errors.append(f"{derivation.label}: source group {self.path(group)} is not exactly-one")
            seen: dict[frozenset[str], str] = {}
            for rule in derivation.rules:
                premise_groups = [self.features[item].group for item in rule["premises"]]
                if len(rule["premises"]) != 2 or set(premise_groups) != set(groups):
                    self.errors.append(f"rule {rule['rule']}: one premise from each source group is required")
                key = frozenset(rule["premises"])
                if key in seen:
                    self.errors.append(f"rule {rule['rule']} repeats the premises of rule {seen[key]}")
                seen.setdefault(key, rule["rule"])
            rows = []
            for left, right in product(self.features[groups[0]].members, self.features[groups[1]].members):
                rules = [rule["rule"] for rule in derivation.rules if set(rule["premises"]) == {left, right}]
                exclusions = [self.constraint_label(item) for item in self.constraints if item.kind == "xor" and (
                    (item.owner == left and right in item.operand_b) or (item.owner == right and left in item.operand_b))]
                pair = [self.path(left), self.path(right)]
                if len(rules) + len(exclusions) != 1:
                    self.errors.append(f"{derivation.label}: pair {pair[0]} x {pair[1]} has {len(rules)} rules and "
                                       f"{len(exclusions)} exclusions; exactly one of either is required")
                rows.append({"pair": pair, "rules": rules, "exclusions": exclusions})
            results.append({"derivation": derivation.label, "derived_variation": graph.name(derivation.variation),
                            "source_groups": [self.path(group) for group in groups], "pairs": len(rows),
                            "with_rule": sum(1 for row in rows if row["rules"]),
                            "with_exclusion": sum(1 for row in rows if row["exclusions"]), "rows": rows})
        return results

    def _binding_integrity(self) -> None:
        """Every variant bound, one feature per variant, one exactly-one group per variation, Development."""
        graph = self.graph
        derived = {derivation.variation for derivation in self.derivations}
        seen_variants: dict[str, str] = {}
        by_variation: dict[str, list[dict[str, Any]]] = {}
        for binding in self.bindings:
            if binding["variation_id"] in derived:
                self.errors.append(f"binding {binding['binding']} binds a variant of the derived variation "
                                   f"{binding['variation']}: derived variants are not selectable")
                continue
            if binding["variant_id"] in seen_variants:
                self.errors.append(f"variant {binding['variation']}::{binding['variant']} is bound by "
                                   f"{seen_variants[binding['variant_id']]} and {binding['binding']}")
            seen_variants.setdefault(binding["variant_id"], binding["binding"])
            by_variation.setdefault(binding["variation_id"], []).append(binding)
        for variation in [*by_variation, *derived]:
            owner = graph.owner(variation)
            if self.projection is not None and (graph.name(owner) != self.projection["owner"]
                                                or graph.name(graph.owner(owner)) != self.projection["package"]):
                self.errors.append(f"variation {graph.name(variation)} is not owned by the projection owner "
                                   f"{self.projection['package']}::{self.projection['owner']}")
        bound_groups: dict[str, str] = {}
        for variation, items in by_variation.items():
            name = graph.name(variation)
            variants = set(graph.members(variation, "VariantMembership"))
            unbound = sorted(graph.label(item) for item in variants - {item["variant_id"] for item in items})
            if unbound:
                self.errors.append(f"variation {name} has unbound variants: {unbound}")
            groups = {self.features[item["feature_id"]].group for item in items}
            if len(groups) != 1 or None in groups:
                self.errors.append(f"variation {name} is bound to features outside one group of alternatives")
                continue
            group = self.features[next(iter(groups))]  # type: ignore[index]
            if group.identifier in bound_groups:
                self.errors.append(f"group {group.path} is bound to {bound_groups[group.identifier]} and {name}")
            bound_groups.setdefault(group.identifier, str(name))
            if group.multiplicity != EXACTLY_ONE:
                self.errors.append(f"variation {name} is bound to {group.path}, which is not exactly-one")
            features = [item["feature_id"] for item in items]
            if len(features) != len(set(features)) or set(features) != set(group.members):
                self.errors.append(f"variation {name} and group {group.path} are not bound one variant per member")
            for feature in (group, *(self.features[item] for item in dict.fromkeys(features))):
                if feature.binding_time != "Development" or feature.unassigned:
                    self.errors.append(f"bound feature {feature.path} must stay at the Development binding time")
        for derivation in self.derivations:
            named = set(derivation.source_groups) | {item for rule in derivation.rules for item in rule["premises"]}
            for feature in sorted((self.features[item] for item in named), key=lambda item: item.order):
                if feature.binding_time != "Development" or feature.unassigned:
                    self.errors.append(f"{derivation.label} names {feature.path}, which must stay at the "
                                       "Development binding time")
        if (self.bindings or self.derivations) and self.projection is None:
            self.errors.append("the feature model resolves shared assets but carries no projection metadata")
        if self.projection is not None:
            for name in ("package", "owner"):
                value = self.projection[name]
                if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
                    self.errors.append(f"the projection {name} must be a valid unquoted SysML identifier")
            label = self.projection["label"]
            if not isinstance(label, str) or not label.strip():
                self.errors.append("the projection label must be a non-empty string")
        for constraint in self.constraints:
            if len(set(constraint.operand_b)) != len(constraint.operand_b):
                self.errors.append(f"constraint {self.constraint_label(constraint)} repeats a feature")
        short_names = [feature.short_name for feature in self.features.values() if feature.short_name]
        duplicates = sorted({name for name in short_names if short_names.count(name) > 1})
        if duplicates:
            self.errors.append(f"duplicate feature short names: {duplicates}")

    # -- admission (ADR 0014: the governed scope stays the admission authority) ---------------

    def role(self, feature: _Feature) -> str:
        """``group`` (a variation point), ``choice`` (a group member), ``grouping`` or ``leaf``."""
        if feature.is_group:
            return "group"
        if feature.group is not None:
            return "choice"
        if any(item.owner == feature.identifier for item in self.features.values()):
            return "grouping"
        return "leaf"

    def _correspondences(self) -> dict[str, list[dict[str, Any]]]:
        """Feature, or the tree for the whole family, to its correspondences with the governed scope.

        A correspondence is a dependency of this tree that carries none of the
        consumed roles. Its one client is a feature or the tree, and each
        supplier is an element the governed scope classifies.
        """
        graph, scope = self.graph, self.scope
        assert scope is not None
        found: dict[str, list[dict[str, Any]]] = {}
        for dependency in sorted(graph.by_id, key=graph.order.__getitem__):
            if graph.kind(dependency) != "Dependency" or graph.sources[dependency] not in self.model_sources:
                continue
            if set(self._ROLES) & set(self.identity.metadata_kinds(dependency)):
                continue
            clients = self._endpoints(dependency, "client", "source")
            if not any(item == self.tree or item in self.features for item in clients):
                continue
            label = graph.label(dependency)
            if len(clients) != 1:
                raise PlemlShapeError(f"correspondence {label} has {len(clients)} clients; one feature per "
                                      "correspondence")
            client = clients[0]
            if client in self.features and self.role(self.features[client]) == "grouping":
                raise PlemlShapeError(f"correspondence {label}: the grouping feature {self.path(client)} carries no "
                                      "admission")
            suppliers = self._endpoints(dependency, "supplier", "target")
            if not suppliers:
                raise PlemlShapeError(f"correspondence {label} names no governed-scope element")
            for supplier in suppliers:
                if supplier in scope.derived:
                    raise PlemlShapeError(f"correspondence {label} names the derived realization "
                                          f"{scope.derived[supplier]}; a derived realization corresponds to its "
                                          "alternative")
                if supplier not in scope.classes:
                    raise PlemlShapeError(f"correspondence {label} names {graph.label(supplier)}, which the governed "
                                          "scope does not classify")
                kind, name = scope.classes[supplier]
                found.setdefault(client, []).append({"correspondence": graph.name(dependency), "element_id": dependency,
                                                     "governed": name, "governed_id": supplier,
                                                     "classification": kind})
            self.consumed.add(dependency)
        return found

    def _corresponds(self, feature: str, kind: str, governed: str) -> bool:
        return any(item["classification"] == kind and item["governed"] == governed
                   for item in self.correspondences.get(feature, []))

    def admission(self, selected: set[str]) -> dict[str, Any]:
        """Whether the governed scope admits a selection, by the correspondences of its features.

        A configuration is admitted only when it is also valid, which its
        decision adds. Grouping features carry no admission. A group feature's correspondence
        classifies its variation point and never blocks. Each selected choice
        or leaf blocks unless one of its correspondences is admissible, and
        one without a correspondence is not in the governed scope; a family
        correspondence applies to every configuration of the tree. The
        selection must realize exactly one admitted alternative, select its
        derived realization in every group that has one, and represent every
        common element that features correspond to.
        """
        if self.scope is None:
            return {"evaluated": False, "admitted": None, "reasons": ["no governed scope among the evaluated elements"]}

        def described(items: Sequence[Mapping[str, Any]]) -> str:
            return "; ".join(f"{item['classification']} {item['governed']}" for item in items)

        considered: list[tuple[str, list[dict[str, Any]]]] = []
        if self.tree in self.correspondences:
            considered.append(("the feature family", self.correspondences[self.tree]))
        notes: list[str] = []
        for feature in sorted(self.features.values(), key=lambda item: item.order):
            if feature.identifier not in selected or self.role(feature) == "grouping":
                continue
            items = self.correspondences.get(feature.identifier, [])
            if self.role(feature) == "group":
                if items:
                    notes.append(f"{feature.path} is a variation point; governed: {described(items)}")
                continue
            considered.append((feature.path, items))
        blocking: list[str] = []
        realized: dict[str, list[str]] = {}
        for label, items in considered:
            if not items:
                blocking.append(f"{label}: not in the governed scope")
                continue
            for item in items:
                if item["classification"] == "admitted-alternative":
                    realized.setdefault(item["governed"], []).append(label)
            if not {item["classification"] for item in items} & ADMISSIBLE:
                blocking.append(f"{label}: {described(items)}")
        reasons = []
        if blocking:
            reasons.append("selects content the governed scope does not admit: " + " | ".join(blocking))
        alternative = next(iter(realized)) if len(realized) == 1 else None
        if not realized:
            reasons.append("realizes no admitted alternative")
        elif alternative is None:
            reasons.append("realizes more than one admitted alternative: " + ", ".join(sorted(realized)))
        else:
            missing = self._unrealized(alternative, selected)
            if missing:
                reasons.append(f"misses derived realizations of {alternative}: {', '.join(missing)}")
        common = self._common_content(alternative, selected)
        incomplete = [item for item in common if item["complete"] is False]
        if incomplete:
            reasons.append("does not represent the common content: " + "; ".join(
                f"{item['asset']} (missing {', '.join(item['missing'])})" for item in incomplete))
        return {"evaluated": True, "admitted": not reasons, "alternative": alternative,
                "alternatives_realized": {name: paths for name, paths in sorted(realized.items())},
                "reasons": reasons, "notes": notes, "common_content": common}

    def _unrealized(self, alternative: str, selected: set[str]) -> list[str]:
        """The derived realizations of ``alternative`` a selection leaves out, by group or leaf."""
        missing = []
        for feature in sorted(self.features.values(), key=lambda item: item.order):
            if feature.is_group:
                realizing = [item for item in feature.members if self._corresponds(item, "admitted-alternative",
                                                                                   alternative)]
                if realizing and not any(item in selected for item in realizing):
                    missing.append(f"{feature.path} = {' or '.join(str(self.path(item)) for item in realizing)}")
            elif (self.role(feature) == "leaf" and feature.identifier not in selected
                  and self._corresponds(feature.identifier, "admitted-alternative", alternative)):
                missing.append(feature.path)
        return missing

    def _common_content(self, alternative: str | None, selected: set[str]) -> list[dict[str, Any]]:
        """How a selection represents each common element of the governed scope.

        Every choice or leaf that corresponds to a common element must be
        selected. A choice is exempt where the realized alternative's derived
        realization selects another member of its group: the feature model has
        one slot there. A common element no feature corresponds to is common
        content outside the selection surface.
        """
        assert self.scope is not None
        result = []
        for name in self.scope.common:
            representing = [feature for feature in sorted(self.features.values(), key=lambda item: item.order)
                            if self.role(feature) in {"choice", "leaf"}
                            and self._corresponds(feature.identifier, "common", name)]
            missing, exempted = [], []
            for feature in representing:
                if feature.identifier in selected:
                    continue
                displaced = alternative is not None and feature.group is not None and any(
                    item in selected and self._corresponds(item, "admitted-alternative", alternative)
                    for item in self.features[feature.group].members)
                (exempted if displaced else missing).append(feature.path)
            result.append({"asset": name, "represented_by": [feature.path for feature in representing],
                           "missing": missing, "exempted": exempted,
                           "complete": (not missing) if representing else None})
        return result

    def derived_targets(self) -> set[str]:
        found = set()
        for derivation in self.derivations:
            found.add(derivation.variation)
            found.update(self.graph.members(derivation.variation, "VariantMembership"))
        return found

    # -- report ----------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        graph = self.graph
        return {
            "tree": {"name": graph.name(self.tree), "short_name": graph.short_name(self.tree),
                     "element_id": self.tree, "source": graph.sources[self.tree]},
            "projection": self.projection,
            "features": [
                {"path": item.path, "name": item.name, "short_name": item.short_name, "element_id": item.identifier,
                 "owner": self.path(item.owner), "multiplicity": item.multiplicity.to_dict(),
                 "group": self.path(item.group), "members": [self.path(member) for member in item.members],
                 "binding_time": item.binding_time, "unassigned": item.unassigned}
                for item in sorted(self.features.values(), key=lambda feature: feature.order)
            ],
            "constraints": [
                {"kind": item.kind, "short_name": item.short_name, "element_id": item.identifier,
                 "owner": self.path(item.owner), "operand_a": [self.path(feature) for feature in item.operand_a],
                 "operand_b": [self.path(feature) for feature in item.operand_b],
                 "pair_exclusion": item.pair_exclusion}
                for item in sorted(self.constraints, key=lambda constraint: graph.order[constraint.identifier])
            ],
            "bindings": self.bindings,
            "derivations": [
                {"derivation": item.name, "short_name": item.short_name, "element_id": item.identifier,
                 "derived_variation": graph.name(item.variation), "derived_variation_id": item.variation,
                 "source_groups": [self.path(group) for group in item.source_groups],
                 "rules": [{"rule": rule["rule"], "element_id": rule["element_id"],
                            "premises": [self.path(premise) for premise in rule["premises"]],
                            "result": graph.name(rule["result"]), "result_id": rule["result"]}
                           for rule in item.rules]}
                for item in self.derivations
            ],
            "agreement": self.agreement,
            "correspondences": [
                {"feature": self.path(client), **item}
                for client in sorted(self.correspondences, key=graph.order.__getitem__)
                for item in self.correspondences[client]
            ],
            "integrity_errors": list(self.errors),
        }


# -- configurations ----------------------------------------------------------------------


@dataclass
class _Setting:
    usage: str
    multiplicity: Multiplicity
    listed: list[str] | None  # the tree features a group setting lists as its value


class _Configuration:
    """One feature configuration of a tree, decided against its feature model."""

    def __init__(self, model: _FeatureModel, identifier: str) -> None:
        self.model, self.identifier = model, identifier
        self.graph, self.identity = model.graph, model.identity
        self.settings: dict[str, _Setting] = {}
        self.reasons: list[dict[str, Any]] = []
        self.description: str | None = None
        self.projection_name: str | None = None
        self.derived = model.derived_targets()
        self._read(identifier, None)

    def reason(self, code: str, detail: str, *, features: Iterable[str] = (), **extra: Any) -> None:
        """Record a rejection with the tree features it applies to (their paths), as data beside its prose."""
        self.reasons.append({"code": code, "class": REASON_CLASSES[code], "detail": detail,
                             "features": sorted(features), **extra})

    def _variations(self, elements: Iterable[str]) -> list[str]:
        """The derived variations that ``elements`` (derived variations or their variants) belong to, by name."""
        return sorted({str(self.graph.name(self.model.variation_of(item) or item)) for item in elements})

    def _read(self, owner: str, scope: str | None) -> None:
        """The members of the configuration (``scope`` None) or of the setting of tree feature ``scope``."""
        graph, identity, model = self.graph, self.identity, self.model
        top = scope is None
        for relationship in graph.relationships(owner):
            kind = graph.kind(relationship)
            if kind in _SKIPPED:
                continue
            if kind == "Annotation":
                for metadata in reference_ids(graph.by_id[relationship].get("ownedRelatedElement")):
                    self._metadata(metadata, top)
                continue
            if kind == "FeatureValue":
                if top:
                    raise PlemlShapeError(f"configuration {graph.label(owner)} carries a value")
                continue  # read with the setting
            member = graph.member_of(relationship)
            if member is None or member not in graph.by_id:
                raise PlemlShapeError(f"a membership of configuration {graph.label(self.identifier)} has no member")
            member_kind = graph.kind(member)
            if member_kind in {"MultiplicityRange", "Comment"}:
                continue
            if member_kind == "Documentation":
                if top:
                    if self.description is not None:
                        raise PlemlShapeError(f"configuration {graph.label(owner)} has more than one doc")
                    self.description = str(graph.by_id[member].get("body") or "")
                continue
            if member_kind == "MetadataUsage":
                self._metadata(member, top)
                continue
            if member_kind == "AttributeUsage" and identity.binding_time in graph.generals(member, "Redefinition"):
                if not top:
                    raise PlemlShapeError("a feature setting redefines the binding time")
                if model._life_cycle(member) != "Development":
                    raise PlemlShapeError(f"configuration {graph.label(owner)} binds later than Development; "
                                          "stage-aware evaluation is not supported")
                continue
            references = set(graph.generals(member))
            try:
                references |= {item for item in graph.value_referents(member) if isinstance(item, str)}
            except PlemlShapeError:
                pass
            is_feature = (member_kind in {"OccurrenceUsage", "PartUsage"}
                          and "FeatureMetadata" in identity.metadata_kinds(member))
            if not is_feature:
                if references & self.derived:
                    self.reason("derived-variant-not-selectable", f"{graph.label(member)} chooses a derived variant; "
                                "derived variants are never configured",
                                variations=self._variations(references & self.derived))
                else:
                    self.reason("not-a-feature", f"{graph.label(member)} is no feature: a feature configuration owns "
                                "only features")
                continue
            for typing in identity.typings(member):
                if typing != identity.lib["Feature"]:
                    raise PlemlShapeError(f"setting {graph.label(member)} is typed by {graph.label(typing)}; a PLEML "
                                          "feature is typed by the library's Feature only, never by a product-line "
                                          "characteristic")
            redefined = graph.generals(member, "Redefinition")
            if len(redefined) != 1:
                raise PlemlShapeError(f"setting {graph.label(member)} redefines {len(redefined)} features")
            feature = redefined[0]
            expected_owner = model.tree if top else scope
            if feature not in model.features or model.features[feature].owner != expected_owner:
                if feature in self.derived:
                    self.reason("derived-variant-not-selectable", f"{graph.label(member)} redefines a derived variant",
                                variations=self._variations([feature]))
                else:
                    self.reason("unknown-feature", f"{graph.label(member)} redefines {graph.label(feature)}, which is "
                                "no feature of the tree at this place")
                continue
            if feature in self.settings:
                raise PlemlShapeError(f"configuration {graph.label(self.identifier)} sets {model.path(feature)} twice")
            multiplicity = graph.multiplicity(member)
            if multiplicity is None:
                raise PlemlShapeError(f"the setting of {model.path(feature)} states no multiplicity")
            listed = None
            if graph.value_expression(member) is not None:
                listed = []
                for referent in graph.value_referents(member):
                    if isinstance(referent, _Outside):
                        raise PlemlShapeError(f"the setting of {model.path(feature)} lists an element outside the set")
                    mapped = [referent] if referent in model.features else graph.generals(referent, "Redefinition")
                    if len(mapped) != 1 or mapped[0] not in model.features:
                        raise PlemlShapeError(f"the setting of {model.path(feature)} lists no tree feature")
                    listed.append(mapped[0])
            self.settings[feature] = _Setting(member, multiplicity, listed)
            self._read(member, feature)

    def _metadata(self, metadata: str, top: bool) -> None:
        identity = self.identity
        kind = identity.metadata_kind(metadata)
        if (kind == "FeatureConfigurationMetadata" and top) or (kind == "FeatureMetadata" and not top):
            return
        if kind == "kernel:projection_name" and top:
            if self.projection_name is not None:
                raise PlemlShapeError("the configuration carries more than one projection name")
            fields, others = identity.record_fields(metadata, "projection_name")
            name_field = fields.get(identity.vocabulary.projection_name_field)
            if others or name_field is None:
                raise PlemlShapeError("the configuration projection metadata is not one projection name")
            value = self.graph.literal(name_field)
            self.projection_name = value if isinstance(value, str) else str(value)
            if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
                self.reason("configuration-metadata", "the projection name must be a valid unquoted SysML identifier")
            return
        raise PlemlShapeError(f"unsupported metadata {kind} in configuration {self.graph.label(self.identifier)}")

    def decide(self) -> dict[str, Any]:
        model, graph = self.model, self.graph
        states: dict[str, str] = {}
        selected: set[str] = set()
        for feature in sorted(model.features.values(), key=lambda item: item.order):
            parent_on = feature.owner == model.tree or feature.owner in selected
            setting = self.settings.get(feature.identifier)
            if setting is not None:
                multiplicity = setting.multiplicity
                if feature.is_group and multiplicity != NONE and multiplicity.lower < 1:
                    raise PlemlShapeError(f"the group setting of {feature.path} must be [0] or have a lower bound of "
                                          "at least 1")
                if not feature.is_group and multiplicity not in (EXACTLY_ONE, NONE):
                    raise PlemlShapeError(f"the setting of {feature.path} is neither [0] nor [1]")
                on = multiplicity != NONE
                state = "enabled" if on else "disabled"
                if on and not parent_on:
                    self.reason("orphan-selection", f"{feature.path} is selected, its owner "
                                                    f"{model.path(feature.owner)} is not", features=[feature.path])
                elif not on and feature.multiplicity.lower >= 1 and parent_on:
                    self.reason("lower-bound", f"mandatory {feature.path} is deselected", features=[feature.path])
                if on and feature.multiplicity.upper == 0:
                    self.reason("upper-bound", f"{feature.path} admits no selection", features=[feature.path])
            elif not parent_on:
                on, state = False, "absent"
            elif feature.multiplicity.lower >= 1:
                on, state = True, "implied"
            else:
                on, state = False, "omitted"
            states[feature.path] = state
            if on:
                selected.add(feature.identifier)

        for feature in model.features.values():
            if not feature.is_group:
                continue
            members = [item for item in feature.members if item in selected]
            setting = self.settings.get(feature.identifier)
            if setting is not None and setting.listed is not None and set(setting.listed) != set(members):
                raise PlemlShapeError(f"group {feature.path} lists {sorted(str(model.path(item)) for item in setting.listed)}"
                                      f" but selects {sorted(str(model.path(item)) for item in members)}")
            if feature.identifier not in selected:
                if members:
                    self.reason("upper-bound", f"group {feature.path} is not selected but selects members",
                                features=[feature.path])
                continue
            for bound in [feature.multiplicity] + ([setting.multiplicity] if setting else []):
                if len(members) < bound.lower:
                    self.reason("lower-bound", f"group {feature.path} selects {len(members)} of {bound.text()}",
                                features=[feature.path])
                    break
                if bound.upper is not None and len(members) > bound.upper:
                    self.reason("upper-bound", f"group {feature.path} selects {len(members)} of {bound.text()}",
                                features=[feature.path])
                    break

        # PLEML's nodeFeaturesAreSet compares the binding time of each suboccurrence of the configuration,
        # that is of each feature it selects, with the configuration's own (PLEML.sysml:95-104).
        for feature in model.features.values():
            if feature.identifier in selected and LIFE_CYCLE[feature.binding_time] > LIFE_CYCLE["Development"]:
                self.reason("binding-time", f"{feature.path} binds at {feature.binding_time}, later than the "
                                            "Development configuration", features=[feature.path])

        for constraint in model.constraints:
            label = {"constraint": constraint.short_name, "kind": constraint.kind}
            operand_b = set(constraint.operand_b)
            if constraint.kind == "requires" and constraint.owner in selected and not operand_b <= selected:
                self.reason("constraint", f"{model.path(constraint.owner)} requires "
                            f"{sorted(str(model.path(item)) for item in operand_b - selected)}",
                            features=[str(model.path(item)) for item in {constraint.owner} | (operand_b - selected)],
                            **label)
            elif constraint.kind == "xor" and constraint.owner in selected and operand_b & selected:
                code = "pair-exclusion" if constraint.pair_exclusion else "constraint"
                self.reason(code, f"{model.path(constraint.owner)} excludes "
                            f"{sorted(str(model.path(item)) for item in operand_b & selected)}",
                            features=[str(model.path(item)) for item in {constraint.owner} | (operand_b & selected)],
                            **label)
            elif (constraint.kind == "implies" and set(constraint.operand_a) <= selected
                  and not operand_b <= selected):
                self.reason("constraint", f"{sorted(str(model.path(item)) for item in constraint.operand_a)} implies "
                            f"{sorted(str(model.path(item)) for item in operand_b - selected)}",
                            features=[str(model.path(item))
                                      for item in set(constraint.operand_a) | (operand_b - selected)], **label)

        if model.errors:
            self.reason("model-integrity", f"the feature model fails {len(model.errors)} integrity checks")

        derived_variants: list[dict[str, Any]] = []
        if not self.reasons:
            for binding in model.bindings:
                if binding["feature_id"] in selected:
                    derived_variants.append({"variation": binding["variation"], "variant": binding["variant"],
                                             "variant_id": binding["variant_id"], "binding": binding["binding"]})
            for derivation in model.derivations:
                matches = [rule for rule in derivation.rules if set(rule["premises"]) <= selected]
                if not matches:
                    self.reason("derivation-no-rule", f"{derivation.label} has no rule for the selected features",
                                derivation=derivation.label)
                elif len(matches) > 1:
                    self.reason("derivation-ambiguous", f"{derivation.label} has {len(matches)} matching rules: "
                                f"{sorted(rule['rule'] for rule in matches)}", derivation=derivation.label)
                else:
                    derived_variants.append({"variation": graph.name(derivation.variation),
                                             "variant": graph.name(matches[0]["result"]),
                                             "variant_id": matches[0]["result"], "rule": matches[0]["rule"],
                                             "derivation": derivation.label})
            if self.reasons:
                derived_variants = []
        # Admission requires validity: the governed members are valid configurations, as a derivation applies
        # to a valid configuration only. An invalid one keeps the rest of its admission record.
        admission = model.admission(selected)
        if self.reasons:
            classes = ", ".join(sorted({reason["class"] for reason in self.reasons}))
            admission = {**admission, "admitted": False,
                         "reasons": [f"invalid configuration: {classes}", *admission["reasons"]]}
        return {
            "configuration": graph.name(self.identifier),
            "element_id": self.identifier,
            "source": graph.sources[self.identifier],
            "projection_name": self.projection_name,
            "description": self.description,
            "valid": not self.reasons,
            "reasons": sorted(self.reasons, key=lambda item: (item["class"], item.get("constraint") or "",
                                                              item["detail"])),
            "admission": admission,
            "selected": sorted(str(model.path(item)) for item in selected),
            "states": states,
            "derived_variants": sorted(derived_variants, key=lambda item: item["variation"]),
        }


# -- entry point -------------------------------------------------------------------------


def _refuse_unread_dependencies(graph: _Graph, identity: _Identity, model_sources: Sequence[str],
                                models: Sequence[_FeatureModel], scope: _GovernedScope | None) -> None:
    """Every dependency of the model documents is read by exactly one tree; none is ever skipped silently.

    A binding, derived variation, rule or correspondence that names no feature of
    a tree (a premise or source that is no feature, a binding of a derived variant,
    a correspondence from an element that is no feature) is refused.
    """
    readers: dict[str, int] = {}
    for model in models:
        for dependency in model.consumed:
            readers[dependency] = readers.get(dependency, 0) + 1
    derived = set().union(*(model.derived_targets() for model in models))
    roles = {"FeatureBinding": "binding", "kernel:derived_variation": "derived variation",
             "kernel:derivation_rule": "derivation rule"}
    for dependency in sorted(graph.by_id, key=graph.order.__getitem__):
        if graph.kind(dependency) != "Dependency" or graph.sources[dependency] not in model_sources:
            continue
        count = readers.get(dependency, 0)
        if count == 1:
            continue
        label = graph.label(dependency)
        kinds = [roles[kind] for kind in identity.metadata_kinds(dependency) if kind in roles]
        what = kinds[0] if kinds else "correspondence"
        if count > 1:
            raise PlemlShapeError(f"{what} {label} is read by {count} feature trees")
        if what == "correspondence" and scope is None:
            raise PlemlShapeError(f"correspondence {label} cannot be read: the governed scope is not among the "
                                  "evaluated elements, so admission cannot be decided")
        suppliers = graph.endpoints(dependency, "supplier", "target")
        if what == "binding" and set(suppliers) & derived:
            raise PlemlShapeError(f"binding {label} targets the derived variant "
                                  f"{', '.join(graph.label(item) for item in suppliers)}; derived variants are never "
                                  "bound")
        ends = graph.endpoints(dependency, "client", "source") if what == "correspondence" else suppliers
        raise PlemlShapeError(f"{what} {label} names no feature of a feature tree: "
                              f"{', '.join(graph.label(item) for item in ends) or 'nothing'}")


def _trees_and_configurations(graph: _Graph, identity: _Identity,
                              model_sources: Sequence[str]) -> tuple[dict[str, str | None], dict[str, str]]:
    """The feature trees, each with the feature model that names it, and the tree of each configuration.

    A tree is a ``#featureTree`` definition, whose features the definition
    owns, or a tree usage with a body. A tree usage typed by a tree
    definition and without a body names that definition, and its owner is
    the tree's feature model. A configuration is typed by its tree
    definition, or subsets its tree usage.
    """
    definitions, usages, configurations = [], [], []
    for identifier, element in graph.by_id.items():
        if graph.sources[identifier] not in model_sources:
            continue
        kind = element["@type"]
        if kind not in {"OccurrenceUsage", "PartUsage", "OccurrenceDefinition", "PartDefinition"}:
            continue
        kinds = identity.metadata_kinds(identifier)
        if kind.endswith("Definition"):
            if "FeatureTreeMetadata" in kinds:
                definitions.append(identifier)
            continue
        generals = set(graph.generals(identifier, "Subsetting"))
        if "FeatureConfigurationMetadata" in kinds or generals & identity.library_usages["featureConfigurations"]:
            configurations.append(identifier)
        elif "FeatureTreeMetadata" in kinds or generals & identity.library_usages["featureTrees"]:
            usages.append(identifier)
    roots: dict[str, str | None] = {definition: None for definition in definitions}
    usage_root: dict[str, str] = {}
    for usage in usages:
        typed = [item for item in identity.typings(usage) if item in roots]
        body = [member for member in graph.members(usage, "FeatureMembership")
                if graph.kind(member) in {"OccurrenceUsage", "PartUsage", "AssertConstraintUsage"}]
        if typed and (len(typed) != 1 or body):
            raise PlemlShapeError(f"tree usage {graph.label(usage)} must be typed by one tree definition and have "
                                  "no body")
        root = typed[0] if typed else usage
        roots.setdefault(root, None)
        usage_root[usage] = root
        owner = graph.owner(usage)
        if owner is not None and graph.kind(owner) in {"OccurrenceDefinition", "OccurrenceUsage"}:
            if "FeatureModelMetadata" not in identity.metadata_kinds(owner):
                raise PlemlShapeError(f"{graph.label(owner)} owns a feature tree but is no #featureModel")
            if roots[root] not in (None, owner):
                raise PlemlShapeError(f"tree {graph.label(root)} is named by two feature models")
            roots[root] = owner
    if not roots:
        raise PlemlShapeError("the model documents declare no feature tree")
    tree_of = {}
    for configuration in configurations:
        candidates = {item for item in identity.typings(configuration) if item in definitions}
        candidates |= {usage_root[item] for item in graph.generals(configuration, "Subsetting") if item in usage_root}
        if len(candidates) != 1:
            raise PlemlShapeError(f"configuration {graph.label(configuration)} is typed by "
                                  f"{'no' if not candidates else len(candidates)} feature tree"
                                  f"{'s' if len(candidates) > 1 else ''}")
        tree_of[configuration] = candidates.pop()
    for configuration in configurations:
        if not set(identity.typings(configuration)) & set(definitions):
            continue  # the library's form, owned by its feature model
        document = graph.sources[configuration]
        sharing = [item for item in configurations if graph.sources[item] == document]
        if len(sharing) != 1 or any(graph.sources[root] == document for root in roots):
            raise PlemlShapeError(f"{document} holds {len(sharing)} configurations; a configuration typed by its tree "
                                  "definition has a file of its own")
    ordered = dict(sorted(roots.items(), key=lambda item: graph.order[item[0]]))
    return ordered, tree_of


def kernel_bindings(contract: Any, elements: Iterable[dict[str, Any]], element_sources: Mapping[str, str], *,
                    vocabulary: KernelVocabulary = KERNEL) -> dict[str, str]:
    """The vocabulary's kernel classes as ingestion binds them (``validate_ontology_bindings``, ADR 0011).

    ``contract`` is the model-built kernel contract of the tree. A class that
    is not ``mapped`` stays unbound; an ambiguous one is refused.
    """
    from .validation import validate_ontology_bindings

    names = {name for _, name, _ in vocabulary.definitions().values()}
    report = validate_ontology_bindings(contract, list(elements), dict(element_sources))
    bindings = {}
    for entry in report.entries:
        if entry.ontology_class not in names:
            continue
        if entry.status == "ambiguous":
            raise PlemlShapeError(f"the kernel class {entry.ontology_class} binds {len(entry.element_ids)} elements")
        if entry.status == "mapped":
            bindings[entry.ontology_class] = entry.element_ids[0]
    return bindings


def evaluate(
    elements: Iterable[dict[str, Any]],
    element_sources: Mapping[str, str],
    *,
    model_sources: Sequence[str],
    library_source: str = LIBRARY_SOURCE,
    kernel_source: str = KERNEL_SOURCE,
    external_references: Iterable[Mapping[str, Any]] = (),
    kernel_bindings: Mapping[str, str] | None = None,
    kernel: KernelVocabulary = KERNEL,
    governed_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate every feature tree and configuration declared in ``model_sources``.

    ``elements`` holds the model documents, the pinned library document and
    every document the models reference (the kernel and the shared assets).
    ``kernel_bindings`` maps the kernel classes to their validated element
    identities (see :func:`kernel_bindings`); an unbound kernel definition
    that a model uses is refused. ``governed_scope`` is the record of the
    production scope validator
    (:func:`de4sdv.sysml_api.product_line_scope.validate_scope_elements`);
    with it, every configuration is also decided for admission. Raises
    :class:`PlemlShapeError` on any shape it does not accept.
    """
    graph = _Graph(elements, element_sources, external_references)
    absent = sorted(set(model_sources) - set(graph.sources.values()))
    if absent:
        raise PlemlShapeError(f"model documents absent from the element set: {absent}")
    identity = _Identity(graph, library_source, kernel_source, kernel, kernel_bindings)
    identity.refuse_homonyms(model_sources)
    identity.refuse_about_metadata(model_sources)
    scope = _GovernedScope(governed_scope, graph) if governed_scope is not None else None
    roots, tree_of = _trees_and_configurations(graph, identity, model_sources)
    feature_models = []
    models = []
    for root, owner in roots.items():
        model = _FeatureModel(identity, model_sources, root, owner, scope)
        models.append(model)
        decided = [_Configuration(model, item).decide()
                   for item in sorted((item for item, tree in tree_of.items() if tree == root),
                                      key=graph.order.__getitem__)]
        feature_models.append({"feature_model": graph.name(owner), "element_id": owner,
                               **model.to_dict(), "configurations": decided})
    _refuse_unread_dependencies(graph, identity, model_sources, models, scope)
    return {
        "schema": SCHEMA,
        "library_source": library_source,
        "kernel_source": kernel_source,
        "kernel_bindings": {name: identity.kernel[role] for role, (_, name, _) in kernel.definitions().items()
                            if role in identity.kernel},
        "model_sources": sorted(model_sources),
        "admission_authority": scope.source if scope is not None else None,
        "feature_models": feature_models,
        "binding_time_scope": "Development-only",
        "native_expression_executed": False,
        "qualified": False,
    }
