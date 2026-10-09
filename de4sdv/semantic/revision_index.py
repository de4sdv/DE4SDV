"""Revision-scoped index over one immutable SysML element corpus.

A SysML API commit (and an export of one Git revision) is immutable, so every
structure derived from its element corpus can be built once and reused by all
queries over that corpus: element lookup, ownership, short-name lookup,
feature values, the representation-tolerant relationship graph, and its
lineage and typing indexes. The governed traversal and the increment
evaluation share one index per corpus instead of rebuilding the graph on
every call.

Boundaries:

- the index is keyed by the corpus object itself (``index.elements is
  elements``); a different corpus never reuses another corpus's index;
- it derives representation structure only. Semantic identity still comes
  from ingestion-validated kernel bindings (ADR 0011); names here are
  display and value data, never identity;
- derived values are memoized lazily and must be treated as read-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, NamedTuple, Sequence

from de4sdv.sysml_api.repository import element_id, reference_ids

from .model_edges import lineage_index, typing_index
from .relationships import RelationshipGraph, build_relationship_graph

#: Literal metaclasses and the value kinds they decode to.
_LITERAL_KINDS = {
    "LiteralString": "string",
    "LiteralInteger": "integer",
    "LiteralRational": "rational",
    "LiteralBoolean": "boolean",
    "LiteralInfinity": "infinity",
}
#: Bounded nesting of value expressions decoded by :meth:`feature_values`.
_MAX_VALUE_DEPTH = 8


class MultiplicityError(ValueError):
    """A feature declares a multiplicity whose bounds cannot be decoded."""


class GraphIndexes(NamedTuple):
    """Lineage (``general -> {specific}``) and typing (``feature -> {type}``) maps."""

    explicit_specifics: dict[str, set[str]]
    implied_specifics: dict[str, set[str]]
    typed_by: dict[str, set[str]]
    typed_by_implied: dict[str, set[str]]


@dataclass(frozen=True)
class ValueLeaf:
    """One decoded value of a feature: a literal or an element reference."""

    kind: str  # string | integer | rational | boolean | infinity | reference
    value: Any


class RevisionIndex:
    """Lazily built, memoized structure over one element corpus."""

    def __init__(
        self,
        elements: Sequence[Mapping[str, Any]],
        *,
        sources: Mapping[str, str] | None = None,
    ) -> None:
        self.elements = elements
        self.sources: Mapping[str, str] = sources or {}
        self._memo: dict[Any, Any] = {}

    # -- memo ---------------------------------------------------------------

    def memo(self, key: Any, factory: Callable[[], Any]) -> Any:
        """The value derived under ``key``, built once by ``factory``.

        A factory that raises stores nothing, so the next call raises again.
        """
        try:
            return self._memo[key]
        except KeyError:
            value = factory()
            self._memo[key] = value
            return value

    def memo_bound(self, key: Any, inputs: tuple[Any, ...], factory: Callable[[], Any]) -> Any:
        """Like :meth:`memo`, but valid only for the identical ``inputs`` objects.

        Used for values that also depend on objects outside the corpus (a
        kernel binding index, a caller-built graph): a different input object
        under the same key rebuilds the value.
        """
        entry = self._memo.get(("bound", key))
        if entry is not None and len(entry[0]) == len(inputs) and all(
            held is given for held, given in zip(entry[0], inputs)
        ):
            return entry[1]
        value = factory()
        self._memo[("bound", key)] = (inputs, value)
        return value

    def owns_lookup(self, by_id: Mapping[str, Any]) -> bool:
        """True when ``by_id`` is this index's element lookup object."""
        return self._memo.get("by-id") is by_id

    # -- core structures ----------------------------------------------------

    @property
    def by_id(self) -> dict[str, Mapping[str, Any]]:
        def build() -> dict[str, Mapping[str, Any]]:
            return {
                identifier: item
                for item in self.elements
                if (identifier := element_id(item)) is not None
            }

        return self.memo("by-id", build)

    @property
    def graph(self) -> RelationshipGraph:
        return self.memo("graph", lambda: build_relationship_graph(list(self.by_id.values())))

    def graph_indexes(self, graph: RelationshipGraph | None = None) -> GraphIndexes:
        """Lineage and typing indexes of ``graph`` (default: the corpus graph).

        Keyed by the graph object; a caller-built graph (for example one that
        adds projected witnesses) gets its own entry while it is alive.
        """
        target = self.graph if graph is None else graph
        entry = self._memo.get(("graph-indexes", id(target)))
        if entry is not None and entry[0] is target:
            return entry[1]
        node_ids = list(self.by_id)
        explicit, implied = lineage_index(target, node_ids)
        typed, typed_implied = typing_index(target, node_ids)
        value = GraphIndexes(explicit, implied, typed, typed_implied)
        self._memo[("graph-indexes", id(target))] = (target, value)
        return value

    # -- structural accessors -----------------------------------------------

    def element(self, identifier: str | None) -> Mapping[str, Any]:
        return self.by_id.get(identifier or "", {})

    def owned_relationships(self, identifier: str, *types: str) -> list[Mapping[str, Any]]:
        found: list[Mapping[str, Any]] = []
        for reference in reference_ids(self.element(identifier).get("ownedRelationship")):
            relationship = self.by_id.get(reference)
            if relationship is None:
                continue
            if types and str(relationship.get("@type") or "") not in types:
                continue
            found.append(relationship)
        return found

    def owned_members(self, identifier: str, *types: str) -> list[str]:
        """Members of ``identifier`` through its owned memberships, in order."""
        members: list[str] = []
        for relationship in self.owned_relationships(identifier):
            if not str(relationship.get("@type") or "").endswith("Membership"):
                continue
            for member in reference_ids(relationship.get("memberElement")):
                element = self.by_id.get(member)
                if element is None:
                    continue
                if types and str(element.get("@type") or "") not in types:
                    continue
                if member not in members:
                    members.append(member)
        return members

    def owner_of(self, identifier: str) -> str | None:
        """The owning element (namespace) of ``identifier``, via its owning relationship."""

        def build() -> dict[str, str]:
            owners: dict[str, str] = {}
            for element in self.elements:
                own_id = element_id(element)
                relationship = self.by_id.get(element_id(element.get("owningRelationship")) or "")
                if own_id is None or relationship is None:
                    continue
                parents = reference_ids(relationship.get("owningRelatedElement"))
                if parents:
                    owners[own_id] = parents[0]
            return owners

        return self.memo("owners", build).get(identifier)

    def with_short_name(self, short_name: str) -> tuple[str, ...]:
        def build() -> dict[str, tuple[str, ...]]:
            found: dict[str, list[str]] = {}
            for element in self.elements:
                short = element.get("declaredShortName")
                identifier = element_id(element)
                if short and identifier:
                    found.setdefault(str(short), []).append(identifier)
            return {key: tuple(value) for key, value in found.items()}

        return self.memo("short-names", build).get(short_name, ())

    def name_of(self, identifier: str | None) -> str:
        element = self.element(identifier)
        return str(element.get("declaredName") or element.get("name") or "")

    def qualified_name(self, identifier: str | None) -> str:
        parts: list[str] = []
        current = identifier
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            name = self.name_of(current)
            if name:
                parts.append(name)
            current = self.owner_of(current)
        return "::".join(reversed(parts))

    def source_of(self, identifier: str | None) -> str:
        """Serializer-recorded source document, when the corpus provides it."""
        return str(self.sources.get(identifier or "", ""))

    def typed_by(self, identifier: str, *, include_implied: bool = False) -> frozenset[str]:
        indexes = self.graph_indexes()
        typed = set(indexes.typed_by.get(identifier, ()))
        if include_implied:
            typed |= set(indexes.typed_by_implied.get(identifier, ()))
        return frozenset(typed)

    def typed_usages(self, definition: str) -> tuple[str, ...]:
        """Elements explicitly typed by ``definition`` (reverse typing index)."""

        def build() -> dict[str, tuple[str, ...]]:
            found: dict[str, list[str]] = {}
            for feature, types in self.graph_indexes().typed_by.items():
                for typed in types:
                    found.setdefault(typed, []).append(feature)
            return {key: tuple(sorted(value)) for key, value in found.items()}

        return self.memo("typed-usages", build).get(definition, ())

    def declared_of(self, identifier: str) -> str:
        """The declared original of a serialized reference shadow (else itself)."""

        def build() -> dict[str, list[str]]:
            shadows: dict[str, list[str]] = {}
            for element in self.elements:
                if str(element.get("@type")) != "ReferenceSubsetting":
                    continue
                declared = reference_ids(element.get("referencedFeature"))
                for shadow in reference_ids(element.get("owningRelatedElement")) + reference_ids(
                    element.get("owner")
                ):
                    for target in declared:
                        bucket = shadows.setdefault(shadow, [])
                        if target not in bucket:
                            bucket.append(target)
            return shadows

        targets = self.memo("reference-shadows", build).get(identifier) or []
        return targets[0] if len(targets) == 1 else identifier

    def elements_of_type(self, *types: str) -> tuple[str, ...]:
        key = ("of-type", tuple(sorted(types)))

        def build() -> tuple[str, ...]:
            wanted = set(types)
            return tuple(
                identifier
                for element in self.elements
                if str(element.get("@type")) in wanted and (identifier := element_id(element))
            )

        return self.memo(key, build)

    # -- lineage and multiplicity -------------------------------------------

    def specializations(self, definition: str) -> frozenset[str]:
        """``definition`` and every definition that specializes it (explicit lineage)."""
        cache: dict[str, frozenset[str]] = self.memo("specializations", dict)
        if definition not in cache:
            specifics = self.graph_indexes().explicit_specifics
            found: set[str] = set()
            frontier = [definition]
            while frontier:
                current = frontier.pop()
                if current in found:
                    continue
                found.add(current)
                frontier.extend(specifics.get(current, ()))
            cache[definition] = frozenset(found)
        return cache[definition]

    def generals(self, definition: str) -> tuple[str, ...]:
        """``definition`` and the definitions it specializes (explicit lineage), nearest first."""

        def build() -> dict[str, list[str]]:
            table: dict[str, list[str]] = {}
            for general, specifics in self.graph_indexes().explicit_specifics.items():
                for specific in specifics:
                    table.setdefault(specific, []).append(general)
            return {specific: sorted(found) for specific, found in table.items()}

        table = self.memo("generals", build)
        found: list[str] = []
        frontier = [definition]
        while frontier:
            current = frontier.pop(0)
            if current not in found:
                found.append(current)
                frontier.extend(table.get(current, ()))
        return tuple(found)

    def redefined(self, feature: str) -> list[str]:
        """The features ``feature`` redefines."""
        return [target for relationship in self.owned_relationships(feature, "Redefinition")
                for target in reference_ids(relationship.get("redefinedFeature"))]

    def multiplicity(self, feature: str) -> tuple[int, int | None] | None:
        """Declared multiplicity of a feature as ``(lower, upper)``; upper ``None`` is unbounded.

        Decodes the export's MultiplicityRange shapes: ``[n]`` and ``[*]`` own
        one literal; ``[lower..upper]`` owns an OperatorExpression ``..`` whose
        two parameter features carry the literal bounds as feature values.
        ``None`` when the feature declares no multiplicity. A declared
        multiplicity that cannot be decoded raises :class:`MultiplicityError`;
        it is never read as a default.
        """
        ranges = self.owned_members(feature, "MultiplicityRange")
        if not ranges:
            return None
        bounds = self.owned_members(ranges[0]) if len(ranges) == 1 else []
        if len(bounds) == 1 and self.element(bounds[0]).get("@type") == "OperatorExpression":
            operator = self.element(bounds[0]).get("operator")
            if operator != "..":
                raise MultiplicityError(f"multiplicity operator {operator!r} is not '..'")
            bounds = [value for parameter in self.owned_members(bounds[0])
                      for relationship in self.owned_relationships(parameter, "FeatureValue")
                      for value in reference_ids(relationship.get("memberElement"))]
        values = [self._bound(bound) for bound in bounds]
        if len(values) == 1:
            return (0, None) if values[0] is None else (values[0], values[0])
        if len(values) == 2 and values[0] is not None and (values[1] is None or values[1] >= values[0]):
            return values[0], values[1]
        raise MultiplicityError(f"multiplicity of {self.qualified_name(feature) or feature} has no decodable bounds")

    def _bound(self, identifier: str) -> int | None:
        element = self.element(identifier)
        kind, value = element.get("@type"), element.get("value")
        if kind == "LiteralInfinity":
            return None
        if kind == "LiteralInteger" and isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        raise MultiplicityError(f"multiplicity bound {kind} {value!r} is not a natural number or *")

    # -- feature values -----------------------------------------------------

    def feature(self, owner: str, member_name: str) -> str | None:
        """The owned feature of ``owner`` declared under ``member_name``."""
        for relationship in self.owned_relationships(owner):
            if not str(relationship.get("@type") or "").endswith("Membership"):
                continue
            if str(relationship.get("memberName") or "") != member_name:
                continue
            members = reference_ids(relationship.get("memberElement"))
            if members:
                return members[0]
        return None

    def feature_values(self, owner: str, member_name: str) -> tuple[ValueLeaf, ...]:
        """Decoded value leaves of ``owner``'s feature ``member_name``."""
        feature = self.feature(owner, member_name)
        if feature is None:
            return ()
        leaves: list[ValueLeaf] = []
        for relationship in self.owned_relationships(feature, "FeatureValue"):
            for value in reference_ids(relationship.get("memberElement")) or reference_ids(
                relationship.get("value")
            ):
                leaves.extend(self._decode(value, 0))
        return tuple(leaves)

    def _decode(self, identifier: str, depth: int) -> Iterable[ValueLeaf]:
        element = self.by_id.get(identifier)
        if element is None or depth > _MAX_VALUE_DEPTH:
            return ()
        kind = str(element.get("@type") or "")
        if kind in _LITERAL_KINDS:
            return (ValueLeaf(_LITERAL_KINDS[kind], element.get("value")),)
        if kind == "FeatureReferenceExpression":
            for relationship in self.owned_relationships(identifier):
                if str(relationship.get("@type") or "") != "Membership":
                    continue
                members = reference_ids(relationship.get("memberElement"))
                if members:
                    return (ValueLeaf("reference", members[0]),)
            return ()
        leaves: list[ValueLeaf] = []
        for relationship in self.owned_relationships(identifier):
            relationship_type = str(relationship.get("@type") or "")
            if relationship_type == "FeatureValue" or (
                relationship_type == "ParameterMembership" and kind.endswith("Expression")
            ):
                for member in reference_ids(relationship.get("memberElement")):
                    leaves.extend(self._decode(member, depth + 1))
        return tuple(leaves)
