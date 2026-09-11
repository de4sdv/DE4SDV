"""Representation-tolerant relationship graph over a validated element set.

The SysML v2 API serializes specialization/typing/subsetting/membership either
as relationship objects appearing in the flat element listing (``@type`` such as
``Subclassification``, ``FeatureTyping``, ``SubjectMembership``) or as inlined
reference properties on the related elements. This module discovers those edges
instead of hard-coding one metaclass: it records every edge together with the
relationship family (metaclass name) or property name that carried it, and lets
callers compute closure and report exact witness identities.

Callers must still fail closed when a required witness is absent: tolerance is
about representation shape, never about accepting missing semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from de4sdv.sysml_api.repository import element_id, reference_ids

#: Relationship families that establish specialization/typing/subsetting
#: lineage in SysML v2 / KerML. Matched by substring so that serializer
#: variants (``Subclassification``, ``OwnedSubclassification``, ...) are all
#: recognised without enumerating the schema.
LINEAGE_FAMILIES: tuple[str, ...] = (
    "Specialization",
    "Subclassification",
    "Subsetting",
    "FeatureTyping",
    "Typing",
    "Generalization",
)

#: Membership families that establish containment/ownership lineage.
MEMBERSHIP_FAMILIES: tuple[str, ...] = (
    "Membership",
    "MembershipImport",
    "ReferenceSubsetting",
)

#: Property names that may carry a reference in an inlined representation.
_REFERENCE_KEYS: tuple[str, ...] = (
    "general",
    "specific",
    "superclassifier",
    "subclassifier",
    "supertype",
    "subtype",
    "type",
    "declaredType",
    "typedFeature",
    "definingFeature",
    "subsettedFeature",
    "redefinedFeature",
    "target",
    "memberElement",
    "relatedElement",
    "source",
    "owningRelatedElement",
    "ownedRelatedElement",
    "ownedMemberElement",
    "feature",
    "definition",
)


def is_family(type_name: str, families: Iterable[str]) -> bool:
    """True when a metaclass name belongs to one of the given families."""
    lowered = type_name.lower()
    return any(family.lower() in lowered for family in families)


@dataclass(frozen=True)
class Hop:
    """One relationship edge with its exact witness identity."""

    source: str
    target: str
    kind: str
    witness_id: str | None
    is_implied: bool = False
    target_uri: str | None = None

    @property
    def provenance(self) -> str:
        """Relationship provenance.

        ``implied`` when the licensed serialization marked the relationship
        object as implied (``isImplied``/``isImpliedIncluded``,
        materialized by ``SerializationOptions.include_implied``) or when it
        came from an inlined reference property that SysML semantics imply;
        ``explicit`` for authored relationship objects.
        """
        if self.is_implied:
            return "implied"
        return "explicit" if self.kind[:1].isupper() else "implied"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "witness_id": self.witness_id,
            "provenance": self.provenance,
        }
        if self.is_implied:
            payload["is_implied"] = True
        if self.target_uri:
            payload["target_uri"] = self.target_uri
        return payload


class RelationshipGraph:
    """Directed graph of discovered relationship edges."""

    def __init__(self, elements: Iterable[dict[str, Any]]) -> None:
        self._elements = list(elements)
        self._by_id = {
            str(element["@id"]): element
            for element in self._elements
            if element.get("@id")
        }
        self._edges: dict[str, list[Hop]] = {}
        for element in self._elements:
            self._collect(element, parent_id=None)
        self._families = sorted({hop.kind for hops in self._edges.values() for hop in hops})

    # -- construction ---------------------------------------------------
    def _collect(self, node: dict[str, Any], parent_id: str | None) -> None:
        node_id = element_id(node)
        type_name = str(node.get("@type") or "")
        if type_name and self._is_relationship(type_name):
            sources = [
                element_id(node.get("subclassifier")),
                element_id(node.get("specific")),
                element_id(node.get("owningRelatedElement")),
                element_id(node.get("owner")),
                element_id(node.get("source")),
                element_id(node.get("subsettingFeature")),
                element_id(node.get("redefiningFeature")),
                element_id(node.get("typedFeature")),
                element_id(node.get("memberElement")),
            ]
            targets = [
                element_id(node.get("superclassifier")),
                element_id(node.get("general")),
                element_id(node.get("supertype")),
                element_id(node.get("type")),
                element_id(node.get("declaredType")),
                element_id(node.get("subsettedFeature")),
                element_id(node.get("redefinedFeature")),
                element_id(node.get("target")),
                element_id(node.get("owningRelatedElement")),
            ]
            source_ids = [candidate for candidate in sources if candidate]
            if not source_ids and parent_id:
                source_ids = [parent_id]
            target_ids = [candidate for candidate in targets if candidate]
            for extra in reference_ids(node.get("ownedRelatedElement")):
                if extra != node_id and extra not in target_ids:
                    target_ids.append(extra)
            # ``isImplied`` marks a relationship the toolchain materialized as
            # semantically implied. ``isImpliedIncluded`` is only the
            # serialization setting flag (present on nearly every element) and
            # is NOT a provenance marker.
            implied = node.get("isImplied") is True
            target_uris: dict[str, str] = {}
            for key in ("superclassifier", "general", "type", "subsettedFeature",
                        "redefinedFeature", "target", "declaredType"):
                value = node.get(key)
                for item in (value if isinstance(value, list) else [value]):
                    if isinstance(item, dict) and item.get("@id") and item.get("@uri"):
                        target_uris[str(item["@id"])] = str(item["@uri"])
            for source in source_ids:
                for target in target_ids:
                    if source == target:
                        continue
                    self._add(
                        Hop(
                            source,
                            target,
                            type_name,
                            node_id,
                            is_implied=implied,
                            target_uri=target_uris.get(target),
                        )
                    )
        elif node_id:
            # Inlined reference properties: the containing element references
            # another element directly (serializer-dependent shape).
            for key in _REFERENCE_KEYS:
                if key not in node:
                    continue
                for target in reference_ids(node.get(key)):
                    if target != node_id:
                        self._add(Hop(node_id, target, key, node_id))
        for child_key in ("ownedRelationship", "ownedElement", "ownedMember"):
            for child in node.get(child_key) or []:
                if isinstance(child, dict):
                    self._collect(child, parent_id=node_id or parent_id)

    @staticmethod
    def _is_relationship(type_name: str) -> bool:
        return is_family(type_name, LINEAGE_FAMILIES + MEMBERSHIP_FAMILIES)

    def _add(self, hop: Hop) -> None:
        self._edges.setdefault(hop.source, []).append(hop)

    # -- queries --------------------------------------------------------
    @property
    def families_seen(self) -> list[str]:
        return list(self._families)

    def element(self, element_id_value: str) -> dict[str, Any] | None:
        return self._by_id.get(element_id_value)

    def outgoing(self, source: str, families: Iterable[str] | None = None) -> list[Hop]:
        hops = self._edges.get(source, [])
        if families is None:
            return list(hops)
        return [
            hop
            for hop in hops
            if not hop.kind[:1].isupper() or is_family(hop.kind, families)
        ]

    def witness(
        self, source: str, target: str, families: Iterable[str] | None = None
    ) -> Hop | None:
        """The exact witness hop for a direct source->target edge, if any."""
        for hop in self.outgoing(source, families):
            if hop.target == target:
                return hop
        return None

    def path(
        self, source: str, target: str, families: Iterable[str] | None = None
    ) -> list[Hop] | None:
        """Shortest witness path source->target, or None when unreachable."""
        if source == target:
            return []
        frontier: list[tuple[str, list[Hop]]] = [(source, [])]
        visited = {source}
        while frontier:
            current, trail = frontier.pop(0)
            for hop in self.outgoing(current, families):
                if hop.target in visited:
                    continue
                extended = trail + [hop]
                if hop.target == target:
                    return extended
                visited.add(hop.target)
                frontier.append((hop.target, extended))
        return None


def build_relationship_graph(elements: Iterable[dict[str, Any]]) -> RelationshipGraph:
    """Build the relationship graph for a validated element listing."""
    return RelationshipGraph(elements)
