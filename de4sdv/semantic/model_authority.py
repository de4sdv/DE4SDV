"""Model-authority extraction for the K projection (plan v1.1 §16).

Every semantic field the projection publishes is read here from the validated
model: the ``DerivesFromNeed`` connection definition's typed ends (domain,
range, roles), the authored end order (native direction), the predicate
identity matched against those end classes (canonical direction, query
direction), and the ingested definition documentation (meaning, claim
strength, claim boundary).

Nothing in this module defines semantics. The patterns below only LOCATE the
statement the model already makes; the values they return are model text.
Missing or ambiguous model authority raises — a projection is never generated
from Python-restated meaning.
"""

from __future__ import annotations

import re
from typing import Any

from de4sdv.sysml_api.errors import IdentityNotFoundError

from .model_edges import (
    DEFINITION_END_FAMILIES,
    end_feature_ids,
    is_typing_hop,
    typing_index,
)
from .relationships import build_relationship_graph

#: Locator for the predicate identity's subject/object vocabulary names
#: (``derivesRequirementFromNeed`` -> ``Requirement`` / ``Need``). The names
#: are matched against the model's end classes; they are not domain/range
#: values themselves.
PREDICATE_SHAPE = re.compile(
    r"derives(?P<subject>[A-Z][A-Za-z0-9]*)From(?P<object>[A-Z][A-Za-z0-9]*)"
)

#: Locator for the claim-strength statement inside ingested definition
#: documentation. Both the strength token and the claim boundary come from the
#: model text; this only finds them.
CLAIM_STRENGTH = re.compile(
    r"Claim strength:\s*(?P<strength>[A-Za-z][A-Za-z0-9_-]*)\s*\((?P<boundary>[^()]*)\)"
)


def _reference_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        item_id = value.get("@id")
        return [str(item_id)] if item_id else []
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(_reference_ids(item))
        return found
    return []


def _documentation_candidates(
    definition: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    """Documentation/comment elements OWNED by the definition.

    Two serializer representations are supported:

    * the real one: an owned membership (``OwningMembership`` or a feature
      membership) whose member element is a ``Documentation``/``Comment``;
    * the direct ``documentation`` reference array (compatible variant).

    Only elements owned by / attributable to this definition are returned —
    the text is never found by scanning the model globally, and never by name
    matching. Each candidate records its exact model-resident origin.
    """
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for reference in _reference_ids(definition.get("ownedRelationship")):
        member = by_id.get(reference)
        if member is None:
            continue
        if str(member.get("@type")) not in {
            "OwningMembership",
            "FeatureMembership",
            "EndFeatureMembership",
            "Membership",
        }:
            continue
        for target in _reference_ids(member.get("memberElement")) + _reference_ids(
            member.get("ownedRelatedElement")
        ):
            element = by_id.get(target)
            if element is None or target in seen:
                continue
            if str(element.get("@type")) not in {"Documentation", "Comment"}:
                continue
            body = element.get("body") or element.get("bodyText")
            if not body:
                continue
            seen.add(target)
            candidates.append(
                {
                    "element_id": target,
                    "membership_id": reference,
                    "element_type": str(element.get("@type")),
                    "body": str(body),
                }
            )
    for reference in _reference_ids(definition.get("documentation")):
        element = by_id.get(reference)
        if element is None or reference in seen:
            continue
        body = element.get("body") or element.get("bodyText")
        if not body:
            continue
        seen.add(reference)
        candidates.append(
            {
                "element_id": reference,
                "membership_id": "",
                "element_type": str(element.get("@type") or "Documentation"),
                "body": str(body),
            }
        )
    return candidates


def _normalized_documentation(
    definition: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> str:
    """Ingested documentation of the definition element, as one text block."""
    bodies = [
        candidate["body"]
        for candidate in _documentation_candidates(definition, by_id)
    ]
    return " ".join(bodies)


def _membership_end_records(
    definition: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    """Definition end features reached through their authored memberships.

    The real serialized shape is ``ConnectionDefinition -> FeatureMembership
    -> memberElement -> end Feature (isEnd=true)``; object-shape
    ``EndFeatureMembership`` remains a compatible variant. Only actual end
    features (``isEnd`` true) count — ordinary owned features are ignored.
    Authored membership order is preserved as serialized.
    """
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for reference in _reference_ids(definition.get("ownedRelationship")):
        member = by_id.get(reference)
        if member is None:
            continue
        type_name = str(member.get("@type") or "")
        if not any(family in type_name for family in DEFINITION_END_FAMILIES):
            continue
        targets = _reference_ids(member.get("memberElement")) + _reference_ids(
            member.get("ownedRelatedElement")
        )
        for target in targets:
            element = by_id.get(target)
            if element is None or target in seen:
                continue
            if element.get("isEnd") is not True:
                continue
            seen.add(target)
            records.append(
                {
                    "membership_id": reference,
                    "membership_kind": type_name,
                    "end_feature_id": target,
                    "role_name": str(
                        element.get("declaredName")
                        or member.get("memberName")
                        or element.get("name")
                        or ""
                    ),
                }
            )
    return records


def definition_ends(
    definition_id: str,
    by_id: dict[str, dict[str, Any]],
    kernel_bindings: Any,
) -> list[dict[str, str]]:
    """Resolve the definition's ends: role name, ontology class, provenance.

    End discovery, in descending authority order:

    1. the definition's AUTHORED membership order — ``ownedRelationship``
       memberships (``FeatureMembership`` / ``EndFeatureMembership``) whose
       member element is an actual end feature (``isEnd=true``); this is the
       representation the real serializer produces and the source of the
       authored end order (the model-native direction);
    2. graph ``EndFeatureMembership`` hops (compatible variant);
    3. declared owned members with inlined ``variant`` typing (compatible
       variant).

    Each end's TYPE is resolved through the relationship graph to its
    governed ontology class via the ingestion-validated binding index, so
    ``Need`` / ``Requirement`` come from the model's end typing, never from a
    Python literal. Authored typing is preferred; an implied-only typing is
    reported as such rather than silently promoted.
    """
    definition = by_id.get(definition_id)
    if definition is None:
        raise ValueError(
            f"model authority missing: definition {definition_id!r} is not in "
            f"the bound revision"
        )
    graph = build_relationship_graph(list(by_id.values()))
    typed_explicit, typed_implied = typing_index(graph, list(by_id))

    records = _membership_end_records(definition, by_id)
    order_source = "authored-membership-order"
    if not records:
        end_ids = end_feature_ids(graph, definition_id)
        if end_ids:
            order_source = "graph-listing-fallback"
            records = [
                {
                    "membership_id": "",
                    "membership_kind": "EndFeatureMembership",
                    "end_feature_id": end_id,
                    "role_name": str(
                        (by_id.get(end_id) or {}).get("declaredName") or ""
                    ),
                }
                for end_id in end_ids
            ]
    if not records:
        declared = _reference_ids(definition.get("ownedMember"))
        if declared:
            order_source = "declared-owned-member-order"
            records = [
                {
                    "membership_id": "",
                    "membership_kind": "ownedMember",
                    "end_feature_id": end_id,
                    "role_name": str(
                        (by_id.get(end_id) or {}).get("declaredName") or ""
                    ),
                }
                for end_id in declared
            ]

    ends: list[dict[str, str]] = []
    for record in records:
        end_id = record["end_feature_id"]
        end = by_id.get(end_id)
        if end is None:
            continue
        role = record["role_name"]
        if not role:
            continue
        type_id: str | None = None
        provenance = "explicit"
        for candidate in sorted(typed_explicit.get(end_id, ())):
            if by_id.get(candidate) is not None:
                type_id, provenance = candidate, "explicit"
                break
        if type_id is None:
            for candidate in sorted(typed_implied.get(end_id, ())):
                if by_id.get(candidate) is not None:
                    type_id, provenance = candidate, "implied-fallback"
                    break
        if type_id is None:
            variant_ids = _reference_ids(end.get("variant"))
            type_id = variant_ids[0] if variant_ids else None
            provenance = "inlined"
        if type_id is None:
            raise IdentityNotFoundError(
                f"end {role!r} of definition {definition_id!r} carries no "
                f"resolvable type; the model does not ground domain/range"
            )
        ends.append(
            {
                "role": role,
                "ontology_class": kernel_bindings.ontology_class_for(
                    type_id, by_id
                ),
                "declaration": str(
                    (by_id.get(type_id) or {}).get("declaredName") or ""
                ),
                "element_id": type_id,
                "end_feature_id": end_id,
                "membership_id": record["membership_id"],
                "provenance": provenance,
                "order_source": order_source,
            }
        )
    return ends


def model_semantics(
    definition_id: str,
    by_id: dict[str, dict[str, Any]],
    kernel_bindings: Any,
    predicate: str,
    need_role: str,
    requirement_role: str,
) -> dict[str, Any]:
    """Derive the projection's semantic fields from the validated model."""
    ends = definition_ends(definition_id, by_id, kernel_bindings)
    by_role = {end["role"]: end for end in ends}
    if set(by_role) != {need_role, requirement_role}:
        raise ValueError(
            f"model authority ambiguous: the definition declares ends "
            f"{sorted(by_role)} but the K slice requires exactly "
            f"{sorted([need_role, requirement_role])}"
        )
    definition_name = str(
        (by_id.get(definition_id) or {}).get("declaredName") or ""
    )
    if not definition_name:
        raise ValueError(
            f"model authority missing: definition {definition_id!r} declares "
            f"no name; the model does not identify the relation"
        )
    declared_order = [end["role"] for end in ends]
    classes = {role: by_role[role]["ontology_class"] for role in by_role}

    # Native direction: the authored end order in the model.
    native_direction = (
        f"{classes[declared_order[0]]} -> {classes[declared_order[1]]}"
    )

    # Canonical (consumer) direction: the predicate identity's subject/object
    # vocabulary names matched against the model's end classes.
    match = PREDICATE_SHAPE.fullmatch(predicate)
    if match is None:
        raise ValueError(
            f"predicate identity {predicate!r} does not expose subject/object "
            f"vocabulary names; canonical direction cannot be derived from the "
            f"model"
        )
    subject, obj = match.group("subject"), match.group("object")
    if {subject, obj} != set(classes.values()):
        raise IdentityNotFoundError(
            f"model authority ambiguous: predicate {predicate!r} names "
            f"{sorted([subject, obj])} but the definition's typed ends ground "
            f"{sorted(classes.values())}; domain/range cannot be derived"
        )
    canonical_direction = f"{subject} -> {obj}"
    # Query mechanics follow from the model: traversing the canonical
    # direction is inverse navigation exactly when it is not the native one.
    query_direction = (
        "forward" if canonical_direction == native_direction else "inverse"
    )

    # Meaning, claim strength, claim boundary: documentation OWNED by the
    # validated definition (real shape: OwningMembership -> Documentation).
    candidates = _documentation_candidates(by_id.get(definition_id, {}), by_id)
    if not candidates:
        raise ValueError(
            "model authority missing: the validated definition carries no "
            "owned documentation; meaning and claim strength must come from "
            "the model"
        )
    statements: list[tuple[str, str, dict[str, str]]] = []
    for candidate in candidates:
        match = CLAIM_STRENGTH.search(
            " ".join(candidate["body"].replace("*", " ").split())
        )
        if match is not None:
            statements.append(
                (
                    match.group("strength"),
                    match.group("boundary").strip(),
                    candidate,
                )
            )
    distinct = {(strength, boundary) for strength, boundary, _ in statements}
    if len(distinct) > 1:
        raise ValueError(
            "model authority ambiguous: the definition owns "
            f"{len(distinct)} conflicting claim-strength statements; refusing "
            "to pick one"
        )
    if not statements:
        raise ValueError(
            "model authority missing: the validated definition documentation "
            "does not state 'Claim strength: <token> (<claim boundary>)'; the "
            "model does not carry the predicate's claim strength"
        )
    strength, claim_boundary, statement_witness = statements[0]
    documentation_witness = [
        {
            "element_id": candidate["element_id"],
            "membership_id": candidate["membership_id"],
            "element_type": candidate["element_type"],
        }
        for candidate in candidates
    ]

    return {
        "connection_definition": definition_name,
        "ends": ends,
        "need_role": need_role,
        "requirement_role": requirement_role,
        "need_end_type": classes[need_role],
        "requirement_end_type": classes[requirement_role],
        "need_end_type_declaration": by_role[need_role]["declaration"],
        "requirement_end_type_declaration": by_role[requirement_role]["declaration"],
        "end_order_source": ends[0]["order_source"] if ends else "",
        "end_type_provenance": (
            "implied-fallback"
            if any(end["provenance"] == "implied-fallback" for end in ends)
            else "explicit"
        ),
        "native_direction": native_direction,
        "canonical_direction": canonical_direction,
        "query_direction": query_direction,
        "domain": subject,
        "range": obj,
        "semantic_strength": strength,
        "claim_boundary": claim_boundary,
        "claim_strength_witness": {
            "element_id": statement_witness["element_id"],
            "membership_id": statement_witness["membership_id"],
        },
        "documentation_witness": documentation_witness,
        "meaning": " ".join(
            candidate["body"] for candidate in candidates
        ),
        "authority_provenance": (
            "validated model: typed definition ends (domain/range, roles), "
            "authored end order (native direction), predicate identity matched "
            "to end classes (canonical direction), ingested definition "
            "documentation (meaning, claim strength, claim boundary); ontology "
            "YAML compared as O0/O1 parity oracle only"
        ),
    }
