"""Ontology-mapped traversal over SysML API semantic objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from de4sdv.sysml_api.repository import element_id, reference_ids

from .kernel_contract import KernelContract, RelationshipMapping


@dataclass(frozen=True)
class TraversalHop:
    predicate: str
    strategy: str
    semantic_strength: str
    source: dict[str, Any]
    target: dict[str, Any]
    api_object: dict[str, Any]


class SemanticTraversal:
    """Execute only explicitly configured ontology relationship strategies."""

    def __init__(self, contract: KernelContract) -> None:
        self.contract = contract

    def traverse(
        self,
        predicate: str,
        source: dict[str, Any],
        elements: list[dict[str, Any]],
    ) -> list[TraversalHop]:
        mapping = self.contract.relationship_mapping(predicate)
        by_id = {
            candidate_id: item
            for item in elements
            if (candidate_id := element_id(item)) is not None
        }
        source_id = element_id(source)
        if source_id is None:
            return []
        if mapping.strategy in {"dependency", "allocation"}:
            return self._relationship_hops(mapping, source, source_id, elements, by_id)
        if mapping.strategy == "subject-membership":
            return self._subject_membership_hops(mapping, source, source_id, elements)
        if mapping.strategy == "verification-membership":
            return self._verification_membership_hops(
                mapping, source, source_id, elements
            )
        if mapping.strategy == "verification":
            return self._reverse_reference_hops(
                mapping, source, source_id, elements
            )
        if mapping.strategy == "property-reference":
            return self._property_reference_hops(mapping, source, by_id)
        if mapping.strategy == "external":
            return []
        raise ValueError(
            f"unsupported SysML traversal strategy {mapping.strategy!r} "
            f"for {predicate}"
        )

    def _relationship_hops(
        self,
        mapping: RelationshipMapping,
        source: dict[str, Any],
        source_id: str,
        elements: list[dict[str, Any]],
        by_id: dict[str, dict[str, Any]],
    ) -> list[TraversalHop]:
        config = mapping.configuration
        allowed_types = {str(item) for item in config.get("relationship_types", [])}
        source_property = str(config.get("source_property", "source"))
        target_property = str(config.get("target_property", "target"))
        direction = str(config.get("direction", "outgoing"))
        hops: list[TraversalHop] = []
        for relationship in elements:
            if allowed_types and str(relationship.get("@type")) not in allowed_types:
                continue
            relationship_sources = reference_ids(relationship.get(source_property))
            relationship_targets = reference_ids(relationship.get(target_property))
            if direction == "incoming" and source_id in relationship_targets:
                neighbor_ids = relationship_sources
            elif direction == "outgoing" and source_id in relationship_sources:
                neighbor_ids = relationship_targets
            else:
                continue
            for neighbor_id in neighbor_ids:
                target = by_id.get(neighbor_id)
                if target is not None:
                    hops.append(self._hop(mapping, source, target, relationship))
        return self._deduplicate(hops)

    def _reverse_reference_hops(
        self,
        mapping: RelationshipMapping,
        source: dict[str, Any],
        source_id: str,
        elements: list[dict[str, Any]],
    ) -> list[TraversalHop]:
        config = mapping.configuration
        allowed_types = {str(item) for item in config.get("element_types", [])}
        reference_property = str(config["reference_property"])
        hops = [
            self._hop(mapping, source, candidate, candidate)
            for candidate in elements
            if (not allowed_types or str(candidate.get("@type")) in allowed_types)
            and source_id in reference_ids(candidate.get(reference_property))
        ]
        return self._deduplicate(hops)

    def _subject_membership_hops(
        self,
        mapping: RelationshipMapping,
        source: dict[str, Any],
        source_id: str,
        elements: list[dict[str, Any]],
    ) -> list[TraversalHop]:
        """Traverse native SubjectMembership objects owned by the requirement.

        Shape derived from the SysML v2 2025-02-01 API schema: a
        SubjectMembership references its subject through ``memberElement`` and
        its owner through ``owningRelatedElement``.
        """
        config = mapping.configuration
        membership_types = {
            str(item)
            for item in config.get("membership_types", ["SubjectMembership"])
        }
        member_property = str(config.get("member_property", "memberElement"))
        owner_types = {str(item) for item in config.get("owner_types", [])}
        if owner_types and str(source.get("@type")) not in owner_types:
            return []
        by_id = {
            candidate_id: item
            for item in elements
            if (candidate_id := element_id(item)) is not None
        }
        hops: list[TraversalHop] = []
        for membership in elements:
            if str(membership.get("@type")) not in membership_types:
                continue
            owners = reference_ids(membership.get("owningRelatedElement"))
            if source_id not in owners:
                continue
            for member_id in reference_ids(membership.get(member_property)):
                target = by_id.get(member_id)
                if target is not None:
                    hops.append(self._hop(mapping, source, target, membership))
        return self._deduplicate(hops)

    def _verification_membership_hops(
        self,
        mapping: RelationshipMapping,
        source: dict[str, Any],
        source_id: str,
        elements: list[dict[str, Any]],
    ) -> list[TraversalHop]:
        """Reverse-traverse native RequirementVerificationMembership objects.

        Shape derived from the SysML v2 2025-02-01 API schema: a
        RequirementVerificationMembership references the verified requirement
        through ``verifiedRequirement``; the verification case is resolved
        from the membership's owner.
        """
        config = mapping.configuration
        membership_types = {
            str(item)
            for item in config.get(
                "membership_types", ["RequirementVerificationMembership"]
            )
        }
        reference_property = str(
            config.get("reference_property", "verifiedRequirement")
        )
        by_id = {
            candidate_id: item
            for item in elements
            if (candidate_id := element_id(item)) is not None
        }
        hops: list[TraversalHop] = []
        for membership in elements:
            if str(membership.get("@type")) not in membership_types:
                continue
            verified_ids = reference_ids(membership.get(reference_property))
            if source_id not in verified_ids:
                continue
            owner_ids = reference_ids(membership.get("owningRelatedElement"))
            owner_ids += reference_ids(membership.get("owner"))
            owner_ids += reference_ids(membership.get("owningType"))
            for owner_id in owner_ids:
                verification = by_id.get(owner_id)
                if verification is not None:
                    hops.append(self._hop(mapping, source, verification, membership))
        return self._deduplicate(hops)

    def _property_reference_hops(
        self,
        mapping: RelationshipMapping,
        source: dict[str, Any],
        by_id: dict[str, dict[str, Any]],
    ) -> list[TraversalHop]:
        config = mapping.configuration
        allowed_types = {str(item) for item in config.get("owner_types", [])}
        if allowed_types and str(source.get("@type")) not in allowed_types:
            return []
        reference_property = str(config["reference_property"])
        return self._deduplicate(
            [
                self._hop(mapping, source, target, source)
                for target_id in reference_ids(source.get(reference_property))
                if (target := by_id.get(target_id)) is not None
            ]
        )

    @staticmethod
    def _hop(
        mapping: RelationshipMapping,
        source: dict[str, Any],
        target: dict[str, Any],
        api_object: dict[str, Any],
    ) -> TraversalHop:
        return TraversalHop(
            predicate=mapping.name,
            strategy=mapping.strategy,
            semantic_strength=mapping.semantic_strength,
            source=source,
            target=target,
            api_object=api_object,
        )

    @staticmethod
    def _deduplicate(hops: list[TraversalHop]) -> list[TraversalHop]:
        unique: dict[tuple[str | None, str | None, str | None], TraversalHop] = {}
        for hop in hops:
            key = (
                element_id(hop.source),
                element_id(hop.target),
                element_id(hop.api_object),
            )
            unique[key] = hop
        return list(unique.values())
