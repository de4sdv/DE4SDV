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

from .model_edges import end_feature_ids, typing_index
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


def _normalized_documentation(
    definition: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> str:
    """Ingested documentation of the definition element, as one text block."""
    bodies = []
    for document_id in _reference_ids(definition.get("documentation")):
        document = by_id.get(document_id, {})
        body = document.get("body") or document.get("bodyText")
        if body:
            bodies.append(str(body))
    return " ".join(bodies)


def definition_ends(
    definition_id: str,
    by_id: dict[str, dict[str, Any]],
    kernel_bindings: Any,
) -> list[dict[str, str]]:
    """Resolve the definition's ends: role name, ontology class, provenance.

    End discovery and typing are representation-tolerant (object membership /
    typing shapes or inlined references), following the post-Lane-B
    relationship graph. Each end's TYPE is resolved to its governed ontology
    class through the ingestion-validated binding index — so ``Need`` /
    ``Requirement`` come from the model's end typing, never from a Python
    literal. Authored typing is preferred; an implied-only typing is reported
    as such rather than silently promoted.
    """
    definition = by_id.get(definition_id)
    if definition is None:
        raise ValueError(
            f"model authority missing: definition {definition_id!r} is not in "
            f"the bound revision"
        )
    graph = build_relationship_graph(list(by_id.values()))
    # End discovery, in descending authority order:
    #   1. the definition's AUTHORED membership order (ownedRelationship ->
    #      EndFeatureMembership -> end), which is what the authored end order —
    #      and therefore the model's native direction — is declared in;
    #   2. declared owned members (legacy serializer shape);
    #   3. graph membership hops (representation fallback; listing order only,
    #      reported as such because the order is then not authored).
    end_ids = _authored_membership_end_ids(definition, by_id)
    order_source = "authored-membership-order"
    if not end_ids:
        end_ids = _reference_ids(definition.get("ownedMember"))
        order_source = "declared-owned-member-order"
    if not end_ids:
        end_ids = end_feature_ids(graph, definition_id)
        order_source = "graph-listing-fallback"
    typed_explicit, typed_implied = typing_index(graph, list(by_id))

    ends: list[dict[str, str]] = []
    for end_id in end_ids:
        end = by_id.get(end_id)
        if end is None:
            continue
        role = str(end.get("declaredName") or "")
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
            # Inlined `variant` reference (legacy serializer shape).
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
                "provenance": provenance,
            }
        )
    for end in ends:
        end["order_source"] = order_source
    return ends


def _authored_membership_end_ids(
    definition: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> list[str]:
    """End ids in the definition's authored membership order."""
    end_ids: list[str] = []
    for reference in _reference_ids(definition.get("ownedRelationship")):
        member = by_id.get(reference)
        if member is None:
            continue
        if str(member.get("@type")) == "EndFeatureMembership":
            end_ids.extend(_reference_ids(member.get("ownedRelatedElement")))
    return end_ids


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

    # Meaning, claim strength, claim boundary: ingested model documentation.
    documentation = _normalized_documentation(
        by_id.get(definition_id, {}), by_id
    )
    if not documentation.strip():
        raise ValueError(
            "model authority missing: the validated definition carries no "
            "documentation; meaning and claim strength must come from the model"
        )
    strength_match = CLAIM_STRENGTH.search(
        " ".join(documentation.replace("*", " ").split())
    )
    if strength_match is None:
        raise ValueError(
            "model authority missing: the validated definition documentation "
            "does not state 'Claim strength: <token> (<claim boundary>)'; the "
            "model does not carry the predicate's claim strength"
        )

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
        "semantic_strength": strength_match.group("strength"),
        "claim_boundary": strength_match.group("boundary").strip(),
        "meaning": " ".join(documentation.split()),
        "authority_provenance": (
            "validated model: typed definition ends (domain/range, roles), "
            "authored end order (native direction), predicate identity matched "
            "to end classes (canonical direction), ingested definition "
            "documentation (meaning, claim strength, claim boundary); ontology "
            "YAML compared as O0/O1 parity oracle only"
        ),
    }
