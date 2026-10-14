"""What ``inspect_element`` says about one element beyond its identity.

Everything is read from the corpus's ownership graph, in the shapes of the
licensed export (which the API serves unchanged, padded with valueless fields):
owned memberships and their members, typing, specialization and redefinition
relationships, multiplicity ranges and feature values. No ``.sysml`` text is
read and no element is found by its name (ADR 0011).

For every element: its SysML v2 ``keyword`` (the textual-notation keyword that
declares it, such as ``part def``, ``attribute``, ``ref`` or ``subject``), its
owning package and its documentation. For a definition also:

- ``supertypes``: the definitions it specializes by authored specialization,
  nearest first (``direct`` marks its own);
- ``owned_features``: the features it owns through feature memberships, in the
  order the export lists them;
- ``inherited_features``: the features of its supertypes it does not redefine,
  each with the supertype it comes from (``inherited_from``);
- ``enumerated_values`` for an enumeration definition (SysML v2 ``enumeratedValue``).

A feature gives its name, keyword, metaclass (``sysml_type``), declared type
and multiplicity, and when present its direction, ``end``, the features it
redefines and its value. A declared type outside the export (a standard library
type such as ``ScalarValues::String``) is named as such per feature: the export
keeps the typing relationship but not its type. Implied relationships the
serializer adds (default library supertypes and typings) are not described.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from de4sdv.sysml_api.qualified_names import QualifiedNameIndex, element_name
from de4sdv.sysml_api.repository import element_id, reference_ids

from .revision_index import MultiplicityError, RevisionIndex

OUTSIDE_EXPORT = "an element outside this export"

#: Definition metaclasses and the keywords that declare them (SysML v2 textual notation).
DEFINITION_KEYWORDS = {
    "AttributeDefinition": "attribute def", "EnumerationDefinition": "enum def",
    "OccurrenceDefinition": "occurrence def", "ItemDefinition": "item def", "PartDefinition": "part def",
    "PortDefinition": "port def", "ConnectionDefinition": "connection def",
    "InterfaceDefinition": "interface def", "AllocationDefinition": "allocation def",
    "FlowDefinition": "flow def", "ActionDefinition": "action def", "StateDefinition": "state def",
    "CalculationDefinition": "calc def", "ConstraintDefinition": "constraint def",
    "RequirementDefinition": "requirement def", "ConcernDefinition": "concern def",
    "CaseDefinition": "case def", "AnalysisCaseDefinition": "analysis def",
    "VerificationCaseDefinition": "verification def", "UseCaseDefinition": "use case def",
    "ViewDefinition": "view def", "ViewpointDefinition": "viewpoint def",
    "RenderingDefinition": "rendering def", "MetadataDefinition": "metadata def",
}
#: Usage metaclasses and the keywords that declare them.
USAGE_KEYWORDS = {
    "ReferenceUsage": "ref", "AttributeUsage": "attribute", "EnumerationUsage": "enum",
    "OccurrenceUsage": "occurrence", "EventOccurrenceUsage": "event", "ItemUsage": "item",
    "PartUsage": "part", "PortUsage": "port", "ConnectionUsage": "connection",
    "InterfaceUsage": "interface", "AllocationUsage": "allocation", "FlowUsage": "flow",
    "SuccessionFlowUsage": "succession flow", "BindingConnectorAsUsage": "binding",
    "SuccessionAsUsage": "succession", "ActionUsage": "action", "PerformActionUsage": "perform",
    "AcceptActionUsage": "accept", "SendActionUsage": "send", "AssignmentActionUsage": "assign",
    "TerminateActionUsage": "terminate", "IfActionUsage": "if", "ForLoopActionUsage": "for",
    "MergeNode": "merge", "DecisionNode": "decide", "JoinNode": "join", "ForkNode": "fork",
    "StateUsage": "state", "ExhibitStateUsage": "exhibit", "TransitionUsage": "transition",
    "CalculationUsage": "calc", "ConstraintUsage": "constraint", "AssertConstraintUsage": "assert",
    "RequirementUsage": "requirement", "SatisfyRequirementUsage": "satisfy", "ConcernUsage": "concern",
    "CaseUsage": "case", "AnalysisCaseUsage": "analysis", "VerificationCaseUsage": "verification",
    "UseCaseUsage": "use case", "IncludeUseCaseUsage": "include", "ViewUsage": "view",
    "ViewpointUsage": "viewpoint", "RenderingUsage": "rendering", "MetadataUsage": "metadata",
}
#: Memberships whose member the textual notation declares with the membership's keyword.
MEMBERSHIP_KEYWORDS = {
    "SubjectMembership": "subject", "ActorMembership": "actor", "StakeholderMembership": "stakeholder",
    "ObjectiveMembership": "objective", "ReturnParameterMembership": "return",
    "FramedConcernMembership": "frame", "RequirementVerificationMembership": "verify",
    "ViewRenderingMembership": "render",
}
PACKAGE_KEYWORDS = {"Package": "package", "LibraryPackage": "library package"}
#: Feature memberships (KerML and SysML): their members are a type's owned features.
FEATURE_MEMBERSHIPS = frozenset({
    "FeatureMembership", "EndFeatureMembership", "ParameterMembership", "ReturnParameterMembership",
    "ResultExpressionMembership", "SubjectMembership", "ActorMembership", "StakeholderMembership",
    "ObjectiveMembership", "RequirementConstraintMembership", "FramedConcernMembership",
    "RequirementVerificationMembership", "StateSubactionMembership", "TransitionFeatureMembership",
    "ViewRenderingMembership",
})
_TYPINGS = ("FeatureTyping", "ConjugatedPortTyping")
_SPECIALIZATIONS = ("Subclassification", "Specialization")
_LITERALS = ("LiteralString", "LiteralInteger", "LiteralRational", "LiteralBoolean")
_MAX_VALUE_DEPTH = 8


def is_definition(element: Mapping[str, Any]) -> bool:
    return str(element.get("@type") or "").endswith("Definition")


class ElementDescriber:
    """Describes elements of one corpus (its revision index and qualified names)."""

    def __init__(self, index: RevisionIndex, names: QualifiedNameIndex) -> None:
        self.index = index
        self.names = names

    # -- naming ---------------------------------------------------------------

    def _name(self, identifier: str) -> str:
        """The qualified name of an element, else its name, else its id."""
        return (self.names.qualified_name(identifier)
                or element_name(self.index.element(identifier)) or identifier)

    def keyword(self, identifier: str) -> str | None:
        """The SysML v2 keyword that declares the element, when it has one."""
        element = self.index.element(identifier)
        kind = str(element.get("@type") or "")
        if kind in DEFINITION_KEYWORDS:
            return DEFINITION_KEYWORDS[kind]
        if kind in PACKAGE_KEYWORDS:
            standard = kind == "LibraryPackage" and element.get("isStandard") is True
            return ("standard " if standard else "") + PACKAGE_KEYWORDS[kind]
        membership = self.index.element(element_id(element.get("owningRelationship")))
        return self._usage_keyword(element, membership)

    @staticmethod
    def _usage_keyword(element: Mapping[str, Any], membership: Mapping[str, Any]) -> str | None:
        kind = str(element.get("@type") or "")
        relation = str(membership.get("@type") or "")
        if relation in MEMBERSHIP_KEYWORDS:
            return MEMBERSHIP_KEYWORDS[relation]
        if relation == "RequirementConstraintMembership":
            return "assume" if membership.get("kind") == "assumption" else "require"
        if relation == "VariantMembership" and kind != "EnumerationUsage":
            return "variant"
        return USAGE_KEYWORDS.get(kind)

    def owning_package(self, identifier: str) -> dict[str, Any] | None:
        """The nearest package that owns the element, directly or through its owners."""
        seen = {identifier}
        current = self.index.owner_of(identifier)
        while current and current not in seen:
            seen.add(current)
            if str(self.index.element(current).get("@type") or "") in PACKAGE_KEYWORDS:
                return {"element_id": current, "qualified_name": self.names.qualified_name(current)}
            current = self.index.owner_of(current)
        return None

    def documentation(self, identifier: str) -> list[tuple[str, str]]:
        """The element's owned documentation, in order: (documentation id, body)."""
        found = []
        for doc in self.index.owned_members(identifier, "Documentation"):
            body = self.index.element(doc).get("body")
            if isinstance(body, str) and body:
                found.append((doc, body))
        return found

    # -- definitions -----------------------------------------------------------

    def definition(self, identifier: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
        """The description of one definition and the gaps of that description."""
        gaps: list[dict[str, str]] = []
        described = [identifier]  # every element whose owned relationships the description reads
        owned, hidden = [], set()
        for membership, feature in self._features(identifier):
            entry, redefined = self._feature(membership, feature, gaps)
            owned.append(entry)
            described.append(feature)
            hidden |= redefined
        supertypes, outside = self._supertypes(identifier)
        inherited: list[dict[str, Any]] = []
        listed = {entry["element_id"] for entry in owned}
        for supertype in supertypes:
            described.append(supertype["element_id"])
            for membership, feature in self._features(supertype["element_id"]):
                entry, redefined = self._feature(membership, feature, gaps)
                if feature not in hidden and feature not in listed:
                    inherited.append({**entry, "inherited_from": supertype["qualified_name"]})
                    listed.add(feature)
                    described.append(feature)
                hidden |= redefined
        missing = {owner: found for owner in described if (found := self._missing_owned(owner))}
        description: dict[str, Any] = {
            "supertypes": supertypes + outside,
            "owned_features": owned,
            "inherited_features": inherited,
        }
        if str(self.index.element(identifier).get("@type")) == "EnumerationDefinition":
            description["enumerated_values"] = self._enumerated_values(identifier)
        if outside:
            gaps.append({"category": "definition-outside-export", "reason": (
                f"{self._name(identifier)} specializes {OUTSIDE_EXPORT}; features inherited from it are "
                "not listed (the export keeps only the specialization "
                + ", ".join(entry["relationship_id"] for entry in outside) + ").")})
        if missing:
            gaps.append({"category": "definition-incomplete", "reason": (
                "owned relationships of these elements are not in this corpus, so their features, types, "
                "multiplicities, values, enumerated values or documentation may be incomplete: "
                + "; ".join(f"{self._name(owner)} ({', '.join(found)})" for owner, found in missing.items()))})
        return description, gaps

    def _missing_owned(self, identifier: str) -> list[str]:
        owned = reference_ids(self.index.element(identifier).get("ownedRelationship"))
        return [found for found in owned if found not in self.index.by_id]

    def _features(self, owner: str) -> Iterator[tuple[Mapping[str, Any], str]]:
        """(membership, feature id) of the features ``owner`` owns, in order."""
        for membership in self.index.owned_relationships(owner):
            if str(membership.get("@type") or "") not in FEATURE_MEMBERSHIPS:
                continue
            for feature in reference_ids(membership.get("memberElement")):
                if feature in self.index.by_id:
                    yield membership, feature

    def _feature(self, membership: Mapping[str, Any], feature: str,
                 gaps: list[dict[str, str]]) -> tuple[dict[str, Any], set[str]]:
        element = self.index.element(feature)
        types, outside = self._types(feature)
        entry: dict[str, Any] = {
            "name": element_name(element),
            "keyword": self._usage_keyword(element, membership),
            "sysml_type": str(element.get("@type") or ""),
            "element_id": feature,
            "type": ", ".join(types) or None,
            "multiplicity": self._multiplicity(feature, gaps),
        }
        if outside:
            entry["type_outside_export"] = (
                "typed by an element outside this export; the export keeps only the typing relationship "
                + ", ".join(outside))
        direction = element.get("direction")
        if isinstance(direction, str) and direction:
            entry["direction"] = direction
        if element.get("isEnd") is True:
            entry["end"] = True
        redefines, redefined = self._redefinitions(feature)
        if redefines:
            entry["redefines"] = redefines
        value = self._value(feature)
        if value is not None:
            entry["value"] = value
        return entry, redefined

    def _types(self, feature: str) -> tuple[list[str], list[str]]:
        """Declared types (qualified names) and the typing relationships whose type is outside the export."""
        named, outside = [], []
        for typing in self.index.owned_relationships(feature, *_TYPINGS):
            if typing.get("isImplied"):
                continue
            targets = [t for t in reference_ids(typing.get("type")) if t in self.index.by_id]
            if targets:
                named.extend(self._name(target) for target in targets)
            elif (relationship := element_id(typing)) is not None:
                outside.append(relationship)
        return named, outside

    def _multiplicity(self, feature: str, gaps: list[dict[str, str]]) -> list[Any] | None:
        try:
            bounds = self.index.multiplicity(feature)
        except MultiplicityError as error:
            gaps.append({"category": "multiplicity", "reason": str(error)})
            return None
        if bounds is None:
            return None
        lower, upper = bounds
        return [lower, "*" if upper is None else upper]

    def _redefinitions(self, feature: str) -> tuple[list[str], set[str]]:
        """Authored redefinitions (named) and every redefined feature (authored or implied)."""
        named: list[str] = []
        redefined: set[str] = set()
        for relationship in self.index.owned_relationships(feature, "Redefinition"):
            targets = reference_ids(relationship.get("redefinedFeature"))
            redefined.update(targets)
            if relationship.get("isImplied"):
                continue
            named.extend(self._name(t) if t in self.index.by_id else OUTSIDE_EXPORT for t in targets)
            if not targets:
                named.append(OUTSIDE_EXPORT)
        return named, redefined

    def _value(self, feature: str) -> dict[str, Any] | None:
        values = self.index.owned_relationships(feature, "FeatureValue")
        if not values:
            return None
        relationship = values[0]
        expressions = (reference_ids(relationship.get("memberElement"))
                       or reference_ids(relationship.get("ownedRelatedElement")))
        return {"default": relationship.get("isDefault") is True,
                "values": [leaf for expression in expressions for leaf in self._leaves(expression, 0)]}

    def _leaves(self, expression: str, depth: int) -> list[dict[str, Any]]:
        element = self.index.by_id.get(expression)
        if element is None:
            return [{"element_id": expression, "note": "not in this corpus"}]
        kind = str(element.get("@type") or "")
        if kind in _LITERALS:
            return [{"literal": element.get("value")}]
        if kind == "LiteralInfinity":
            return [{"literal": "*"}]
        if kind == "FeatureReferenceExpression":
            for membership in self.index.owned_relationships(expression, "Membership"):
                for target in reference_ids(membership.get("memberElement")):
                    if target in self.index.by_id:
                        return [{"reference": self._name(target), "element_id": target}]
            return [{"reference": OUTSIDE_EXPORT}]
        if kind == "OperatorExpression" and element.get("operator") == "," and depth < _MAX_VALUE_DEPTH:
            leaves = []  # a sequence (a, b, ...): each operand is a parameter bound to a value
            for parameter in self.index.owned_members(expression):
                for bound in self.index.owned_relationships(parameter, "FeatureValue"):
                    for inner in reference_ids(bound.get("memberElement")):
                        leaves.extend(self._leaves(inner, depth + 1))
            return leaves
        return [{"expression": kind, "element_id": expression}]

    def _supertypes(self, identifier: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Authored supertypes, nearest first, and the specializations of elements outside the export."""
        found: list[dict[str, Any]] = []
        outside: list[dict[str, Any]] = []
        seen = {identifier}
        frontier = [identifier]
        while frontier:
            current = frontier.pop(0)
            for relationship in self.index.owned_relationships(current, *_SPECIALIZATIONS):
                if relationship.get("isImplied"):
                    continue
                targets = (reference_ids(relationship.get("general"))
                           or reference_ids(relationship.get("superclassifier")))
                general = targets[0] if targets else None
                if general is None or general not in self.index.by_id:
                    outside.append({"outside_export": OUTSIDE_EXPORT, "direct": current == identifier,
                                    "relationship_id": element_id(relationship)})
                    continue
                if general in seen:
                    continue
                seen.add(general)
                frontier.append(general)
                found.append({"element_id": general, "qualified_name": self._name(general),
                              "sysml_type": str(self.index.element(general).get("@type") or ""),
                              "direct": current == identifier})
        return found, outside

    def _enumerated_values(self, identifier: str) -> list[dict[str, Any]]:
        values = []
        for membership in self.index.owned_relationships(identifier, "VariantMembership"):
            for literal in reference_ids(membership.get("memberElement")):
                element = self.index.by_id.get(literal)
                if element is not None and element.get("@type") == "EnumerationUsage":
                    values.append({"name": element_name(element),
                                     "qualified_name": self.names.qualified_name(literal),
                                     "element_id": literal})
        return values


__all__ = ["DEFINITION_KEYWORDS", "ElementDescriber", "FEATURE_MEMBERSHIPS", "MEMBERSHIP_KEYWORDS",
           "OUTSIDE_EXPORT", "USAGE_KEYWORDS", "is_definition"]
