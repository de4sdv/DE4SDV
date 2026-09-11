"""Edge classification over the post-Lane-B relationship graph.

Lane B enables ``SerializationOptions.include_implied`` for the licensed
export (``scripts/export_sysml_api_baseline.py``), so the ingested element
listing carries tool-implied relationships alongside authored ones, and
references may be inlined (``@id`` + ``@uri``) rather than serialized as
separate relationship objects. ``de4sdv.semantic.relationships`` discovers
those edges representation-tolerantly; this module classifies them by the
semantic role K's derivation predicate needs, and keeps explicit vs implied
provenance separable.

Nothing here decides semantics: callers still fail closed on missing
witnesses. The split exists so a witness can state WHICH provenance carried
the fact, and so an implied relationship can never silently stand in for an
authored derivation assertion.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .relationships import RelationshipGraph, is_family

#: Capitalized relationship families that establish subsumption
#: (``specific -> general``) lineage.
SUBSUMPTION_FAMILIES: tuple[str, ...] = (
    "Subclassification",
    "Specialization",
    "Generalization",
)

#: Inlined reference keys that carry subsumption in serializer-dependent
#: shapes (lowercase keys are inlined references, not relationship objects).
SUBSUMPTION_INLINE_KEYS: tuple[str, ...] = (
    "general",
    "superclassifier",
    "supertype",
)

#: Capitalized families that establish typing lineage (``feature -> type``).
TYPING_FAMILIES: tuple[str, ...] = ("FeatureTyping", "Typing")

#: Inlined reference keys that carry typing lineage.
TYPING_INLINE_KEYS: tuple[str, ...] = (
    "type",
    "declaredType",
    "definingFeature",
)

#: Membership family that owns connection ends.
END_FAMILIES: tuple[str, ...] = ("EndFeatureMembership",)

#: Membership families that own definition ends (the real serializer uses a
#: plain ``FeatureMembership`` on a ConnectionDefinition; object-shape
#: ``EndFeatureMembership`` remains valid as a compatible variant).
DEFINITION_END_FAMILIES: tuple[str, ...] = (
    "EndFeatureMembership",
    "FeatureMembership",
)

#: Relationship family that binds a synthesized end Feature to the connected
#: engineering usage (the real serialized witness path).
REFERENCE_SUBSETTING_FAMILIES: tuple[str, ...] = ("ReferenceSubsetting",)

#: Inlined reference keys that can carry the reference-subsetting target.
REFERENCE_SUBSETTING_INLINE_KEYS: tuple[str, ...] = ("referencedFeature",)


def is_reference_subsetting_hop(hop: Any) -> bool:
    """True when a hop carries a reference-subsetting (object or inlined)."""
    return is_family(hop.kind, REFERENCE_SUBSETTING_FAMILIES) or (
        hop.kind in REFERENCE_SUBSETTING_INLINE_KEYS
    )


def is_subsumption_hop(hop: Any) -> bool:
    """True when a hop carries subsumption lineage (object or inlined)."""
    return is_family(hop.kind, SUBSUMPTION_FAMILIES) or hop.kind in (
        SUBSUMPTION_INLINE_KEYS
    )


def is_typing_hop(hop: Any) -> bool:
    """True when a hop carries typing lineage (object or inlined)."""
    return is_family(hop.kind, TYPING_FAMILIES) or hop.kind in TYPING_INLINE_KEYS


def lineage_index(
    graph: RelationshipGraph, node_ids: Iterable[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return explicit and implied ``general -> {specific}`` maps.

    Hops follow the serializer's ``specific -> general`` direction; the
    returned maps are inverted so callers can walk DOWNWARD from a validated
    kernel root to the definitions that ground in it (the direction K's role
    classification needs).
    """
    explicit: dict[str, set[str]] = {}
    implied: dict[str, set[str]] = {}
    for node_id in node_ids:
        for hop in graph.outgoing(node_id):
            if not is_subsumption_hop(hop):
                continue
            bucket = implied if hop.is_implied else explicit
            bucket.setdefault(hop.target, set()).add(node_id)
    return explicit, implied


def typing_index(
    graph: RelationshipGraph, node_ids: Iterable[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return explicit and implied ``feature -> {type}`` maps."""
    explicit: dict[str, set[str]] = {}
    implied: dict[str, set[str]] = {}
    for node_id in node_ids:
        for hop in graph.outgoing(node_id):
            if not is_typing_hop(hop):
                continue
            bucket = implied if hop.is_implied else explicit
            bucket.setdefault(node_id, set()).add(hop.target)
    return explicit, implied


def closure(roots: Iterable[str], specifics: dict[str, set[str]]) -> set[str]:
    """Downward closure: the roots plus everything that specializes them."""
    found: set[str] = set()
    frontier = [root for root in roots if root]
    while frontier:
        current = frontier.pop()
        if current in found:
            continue
        found.add(current)
        frontier.extend(specifics.get(current, ()))
    return found


def end_feature_ids(graph: RelationshipGraph, node_id: str) -> list[str]:
    """Connection/definition end ids via EndFeatureMembership hops."""
    return [
        hop.target
        for hop in graph.outgoing(node_id)
        if is_family(hop.kind, END_FAMILIES)
    ]
