"""Ontology-mapped traversal over SysML API semantic objects."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import element_id, reference_ids

from .kernel_binding_index import KernelBindingIndex
from .kernel_contract import KernelContract, RelationshipMapping


@dataclass(frozen=True)
class TraversalHop:
    predicate: str
    strategy: str
    semantic_strength: str
    source: dict[str, Any]
    target: dict[str, Any]
    api_object: dict[str, Any]
    witness: dict[str, Any] = field(default_factory=dict)


class SemanticTraversal:
    """Execute only explicitly configured ontology relationship strategies."""

    def __init__(
        self,
        contract: KernelContract,
        kernel_bindings: KernelBindingIndex | None = None,
    ) -> None:
        self.contract = contract
        self.kernel_bindings = kernel_bindings

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
        if mapping.strategy == "metadata-tagged-dependency":
            return self._metadata_tagged_dependency_hops(
                mapping, source, source_id, elements, by_id
            )
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
        source_types = {
            str(item) for item in config.get("source_types", [])
        }
        target_types = {
            str(item) for item in config.get("target_types", [])
        }
        exclude_root = config.get("exclude_source_specializations_of")
        if exclude_root:
            # Exclusion by specialization lineage is only meaningful for
            # incoming traversal (filtering neighbor sources). For outgoing
            # traversal the queried source is the requirement root itself,
            # which is never a member-product specialization; skip the
            # O(elements) lineage computation there.
            if direction == "incoming":
                excluded_ids = self._excluded_specialization_ids(
                    exclude_root, by_id
                )
            else:
                excluded_ids: set[str] = set()
        else:
            excluded_ids = set()
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
            if direction == "incoming":
                if source_types:
                    neighbor_ids = [
                        neighbor_id
                        for neighbor_id in neighbor_ids
                        if str(by_id.get(neighbor_id, {}).get("@type")) in source_types
                    ]
                if excluded_ids:
                    neighbor_ids = [
                        neighbor_id for neighbor_id in neighbor_ids if neighbor_id not in excluded_ids
                    ]
            else:
                if source_types and str(source.get("@type")) not in source_types:
                    continue
                if excluded_ids and source_id in excluded_ids:
                    continue
                if target_types:
                    neighbor_ids = [
                        neighbor_id
                        for neighbor_id in neighbor_ids
                        if str(by_id.get(neighbor_id, {}).get("@type")) in target_types
                    ]
            for neighbor_id in neighbor_ids:
                target = by_id.get(neighbor_id)
                if target is not None:
                    hops.append(self._hop(mapping, source, target, relationship))
        return self._deduplicate(hops)

    def _metadata_tagged_dependency_hops(
        self,
        mapping: RelationshipMapping,
        source: dict[str, Any],
        source_id: str,
        elements: list[dict[str, Any]],
        by_id: dict[str, dict[str, Any]],
    ) -> list[TraversalHop]:
        """Traverse dependencies discriminated by a kernel metadata marker.

        A generic Dependency is not evidence of a stronger domain predicate,
        even when its endpoint types match (plan §10, UG-05). This strategy
        accepts a dependency only when BOTH hold:

        1. the full discriminator witness is present and consistent:
           the dependency owns an Annotation, the Annotation annotates that
           same dependency, the Annotation owns a MetadataUsage element that
           actually exists with API type ``MetadataUsage``, and that usage is
           typed by the ontology-mapped metadata definition (resolved through
           ingestion-validated kernel identity, never by names); and
        2. both endpoints ground in the declared kernel lineages
           (``source_lineage_of`` / ``target_lineage_of``) through
           typing/specialization witnesses resolved from validated kernel
           UUIDs — endpoint metatypes alone never satisfy the predicate.

        Serialized witness shape (observed in the validated deployed baseline
        for the same metadata mechanism, e.g. the ``#AdapterExchangeExcluded``
        dependencies):

        ``Dependency --ownedRelationship--> Annotation
        --annotatedElement--> that Dependency
        --ownedRelatedElement--> MetadataUsage --FeatureTyping--> MetadataDefinition``

        A relationship that resembles the witness but misses any required
        element, ownership link, or lineage grounding raises
        :class:`IdentityNotFoundError` (incomplete/unsupported closure), so a
        corrupted witness can never degrade into an ordinary empty result
        (UG-06): callers see an explicit error, not an absence-based pass.
        """
        config = mapping.configuration
        allowed_types = {str(item) for item in config.get("relationship_types", [])}
        marker_name = str(config.get("metadata_definition", ""))
        if not marker_name:
            raise ValueError(
                f"metadata-tagged-dependency strategy for {mapping.name} "
                f"requires metadata_definition"
            )
        source_property = str(config.get("source_property", "source"))
        target_property = str(config.get("target_property", "target"))
        direction = str(config.get("direction", "outgoing"))

        marker_definition_ids = self._marker_definition_ids(marker_name, by_id)
        if marker_definition_ids is None:
            # Fail closed: without a validated marker identity the predicate
            # cannot be discriminated in this revision.
            raise IdentityNotFoundError(
                f"no validated kernel binding for metadata definition "
                f"{marker_name!r}; predicate {mapping.name!r} cannot be "
                f"evaluated without ingestion-validated binding metadata"
            )

        # Lineage resolvers for both endpoints (R1): each configured lineage
        # key names an ontology class whose kernel UUID is validated at
        # ingestion. A lineage key that fails to ground is a hard error —
        # silently skipping the check would let out-of-lineage endpoints
        # borrow the predicate.
        lineage_resolvers = {
            key: self._lineage_resolver(str(lineage_class), by_id)
            for key, lineage_class in (
                ("source_lineage_of", config.get("source_lineage_of")),
                ("target_lineage_of", config.get("target_lineage_of")),
            )
            if lineage_class
        }

        # Witness index R2: only MetadataUsage elements that actually exist
        # with the MetadataUsage API type and a FeatureTyping to a marker
        # definition qualify as discriminator instances.
        marker_usage_ids: set[str] = set()
        for element in elements:
            if str(element.get("@type")) != "MetadataUsage":
                continue
            usage_id = element_id(element)
            if usage_id is None:
                continue
            for typing in elements:
                if str(typing.get("@type")) != "FeatureTyping":
                    continue
                typed = element_id(typing.get("type")) or element_id(
                    typing.get("general")
                )
                if typed is None or typed not in marker_definition_ids:
                    continue
                if element_id(typing.get("typedFeature")) or element_id(
                    typing.get("specific")
                ) == usage_id:
                    marker_usage_ids.add(usage_id)
                    break

        # Annotation index R2: (annotated element, annotation owner) pairs.
        # The usage referenced in ownedRelatedElement must itself exist as a
        # qualifying MetadataUsage; a dangling reference never qualifies.
        annotations_by_target: dict[str, dict[str, str]] = {}
        for element in elements:
            if str(element.get("@type")) != "Annotation":
                continue
            owners = reference_ids(element.get("owningRelatedElement"))
            for usage_id in reference_ids(element.get("ownedRelatedElement")):
                if usage_id not in marker_usage_ids:
                    continue
                for annotated_id in reference_ids(
                    element.get("annotatedElement")
                ):
                    for owner_id in owners:
                        annotations_by_target.setdefault(annotated_id, {})[
                            owner_id
                        ] = usage_id

        hops: list[TraversalHop] = []
        for relationship in elements:
            if allowed_types and str(relationship.get("@type")) not in allowed_types:
                continue
            relationship_id = element_id(relationship)
            if relationship_id is None:
                continue
            relationship_sources = reference_ids(relationship.get(source_property))
            relationship_targets = reference_ids(relationship.get(target_property))
            if direction == "incoming" and source_id in relationship_targets:
                neighbor_ids = relationship_sources
            elif direction == "outgoing" and source_id in relationship_sources:
                neighbor_ids = relationship_targets
            else:
                continue
            # Discriminator witness R2: an Annotation owned by THIS
            # relationship, annotating THIS relationship, whose owned
            # MetadataUsage exists and is typed by the marker definition.
            usage_by_owner = annotations_by_target.get(relationship_id, {})
            witness_usage_ids = [
                usage_id
                for usage_id in usage_by_owner.values()
                if usage_id in marker_usage_ids
                and usage_id in {element_id(e) for e in elements}
            ]
            # Ownership consistency on the accept path: every Annotation
            # that annotates this dependency and carries the marker must be
            # owned by this dependency (its @id in ownedRelationship), and
            # the dependency must not own a marker Annotation that annotates
            # something else.
            owned_annotation_ids = set(
                reference_ids(relationship.get("ownedRelationship"))
            )
            annotating_annotation_ids = set()
            for element in by_id.values():
                if str(element.get("@type")) != "Annotation":
                    continue
                if relationship_id not in reference_ids(
                    element.get("annotatedElement")
                ):
                    continue
                if not (
                    set(reference_ids(element.get("ownedRelatedElement")))
                    & marker_usage_ids
                ):
                    continue
                annotating_annotation_ids.add(str(element.get("@id")))
                owner_ids = reference_ids(element.get("owningRelatedElement"))
                if owner_ids and relationship_id not in owner_ids:
                    raise IdentityNotFoundError(
                        f"incomplete discriminator witness for predicate "
                        f"{mapping.name!r} on dependency "
                        f"{str(relationship.get('declaredName') or relationship_id)!r}: "
                        f"annotation {element.get('@id')} is owned by "
                        f"{owner_ids}, not this dependency"
                    )
            if not annotating_annotation_ids <= owned_annotation_ids:
                raise IdentityNotFoundError(
                    f"incomplete discriminator witness for predicate "
                    f"{mapping.name!r} on dependency "
                    f"{str(relationship.get('declaredName') or relationship_id)!r}: "
                    f"annotation ownership contradicts the dependency's "
                    f"ownedRelationship"
                )
            if not witness_usage_ids:
                # Distinguish a dependency with NO marker application at all
                # (quiet absence: not this predicate's business) from a
                # dependency that carries broken marker closure (fail closed
                # with a precise diagnostic, never a silent empty result).
                broken = self._broken_witness_reason(
                    relationship,
                    relationship_id,
                    marker_definition_ids,
                    by_id,
                )
                if broken:
                    raise IdentityNotFoundError(
                        f"incomplete discriminator witness for predicate "
                        f"{mapping.name!r} on dependency "
                        f"{str(relationship.get('declaredName') or relationship_id)!r}: "
                        f"{broken}"
                    )
                continue
            else:
                # Witness present: an out-of-lineage endpoint is a corrupted
                # derivation assertion, not a quiet absence (R1).
                source_ok = self._endpoint_in_lineage(
                    source, lineage_resolvers["source_lineage_of"], by_id
                )
                for neighbor_id in neighbor_ids:
                    neighbor = by_id.get(neighbor_id)
                    if neighbor is None:
                        continue
                    if not self._endpoint_in_lineage(
                        neighbor,
                        lineage_resolvers["target_lineage_of"],
                        by_id,
                    ):
                        raise IdentityNotFoundError(
                            f"discriminator witness on dependency "
                            f"{str(relationship.get('declaredName') or relationship_id)!r} "
                            f"has target {neighbor_id!r} outside the declared "
                            f"{mapping.configuration.get('target_lineage_of')!r} lineage"
                        )
                if not source_ok:
                    raise IdentityNotFoundError(
                        f"discriminator witness on dependency "
                        f"{str(relationship.get('declaredName') or relationship_id)!r} "
                        f"has source outside the declared "
                        f"{mapping.configuration.get('source_lineage_of')!r} lineage"
                    )
            # Endpoint lineage enforcement R1: the traversal-side endpoint
            # (source of the hop) and every neighbor must ground in the
            # declared kernel lineages. Out-of-lineage endpoints invalidate
            # the witness for this predicate.
            if not self._endpoint_in_lineage(
                source, lineage_resolvers["source_lineage_of"], by_id
            ):
                continue
            resolved_neighbors: list[tuple[str, dict[str, Any]]] = []
            for neighbor_id in neighbor_ids:
                neighbor = by_id.get(neighbor_id)
                if neighbor is None:
                    continue
                if not self._endpoint_in_lineage(
                    neighbor, lineage_resolvers["target_lineage_of"], by_id
                ):
                    continue
                resolved_neighbors.append((neighbor_id, neighbor))
            if not resolved_neighbors:
                continue
            for neighbor_id, target in resolved_neighbors:
                hop = self._hop(mapping, source, target, relationship)
                hop = replace(
                    hop,
                    witness={
                        "relationship_id": relationship_id,
                        "marker_usage_ids": sorted(witness_usage_ids),
                        "annotation_owner_ids": sorted(usage_by_owner),
                    },
                )
                hops.append(hop)
        return self._deduplicate(hops)

    def _broken_witness_reason(
        self,
        relationship: dict[str, Any],
        relationship_id: str,
        marker_definition_ids: set[str],
        by_id: dict[str, dict[str, Any]],
    ) -> str | None:
        """Return a diagnostic when a dependency carries partial marker
        closure, or None when the dependency simply has no marker application
        (a bare dependency is quietly skipped — it is another predicate's
        business)."""
        annotations: list[dict[str, Any]] = []
        for reference in reference_ids(relationship.get("ownedRelationship")):
            element = by_id.get(reference)
            if element is not None and str(element.get("@type")) == "Annotation":
                annotations.append(element)
        if not annotations:
            # No annotation is owned by this dependency — but if any
            # annotation elsewhere still references it (dangling witness
            # side), closure is broken too.
            for element in by_id.values():
                if str(element.get("@type")) != "Annotation":
                    continue
                if relationship_id in reference_ids(
                    element.get("annotatedElement")
                ):
                    return (
                        f"annotation {element.get('@id')} references this "
                        f"dependency but is not owned by it "
                        f"(owner={element.get('owningRelatedElement')})"
                    )
            return None
        for annotation in annotations:
            annotation_id = str(annotation.get("@id"))
            annotated_ids = reference_ids(annotation.get("annotatedElement"))
            usage_ids = reference_ids(annotation.get("ownedRelatedElement"))
            owner_ids = reference_ids(annotation.get("owningRelatedElement"))
            problems: list[str] = []
            if relationship_id not in annotated_ids:
                problems.append(
                    f"annotation {annotation_id} does not annotate this "
                    f"dependency"
                )
            if owner_ids and relationship_id not in owner_ids:
                problems.append(
                    f"annotation {annotation_id} is owned by "
                    f"{owner_ids}, not this dependency"
                )
            for usage_id in usage_ids:
                usage = by_id.get(usage_id)
                if usage is None:
                    problems.append(
                        f"metadata usage {usage_id} referenced by annotation "
                        f"{annotation_id} does not exist in the revision"
                    )
                    continue
                if str(usage.get("@type")) != "MetadataUsage":
                    problems.append(
                        f"element {usage_id} has type "
                        f"{str(usage.get('@type'))!r}, not MetadataUsage"
                    )
                    continue
                typed_ok = False
                for element in by_id.values():
                    if str(element.get("@type")) != "FeatureTyping":
                        continue
                    typed = element_id(element.get("type")) or element_id(
                        element.get("general")
                    )
                    feature = element_id(element.get("typedFeature")) or (
                        element_id(element.get("specific"))
                    )
                    if (
                        feature == usage_id
                        and typed is not None
                        and typed in marker_definition_ids
                    ):
                        typed_ok = True
                        break
                if not typed_ok:
                    problems.append(
                        f"metadata usage {usage_id} is not typed by the "
                        f"marker definition"
                    )
            if problems:
                return "; ".join(problems)
        return None

    def _endpoint_in_lineage(
        self,
        endpoint: dict[str, Any],
        resolver: dict[str, Any] | None,
        by_id: dict[str, dict[str, Any]],
    ) -> bool:
        """Return whether one endpoint grounds in the declared lineage.

        The resolver carries the validated kernel UUID and the precomputed
        lineage id set. An endpoint grounds when its own UUID is in the
        lineage or a FeatureTyping/typing witness connects it to a lineage
        member. When no lineage is configured for this side the check is
        vacuous (returns True) — the mapping must configure both sides for
        this strategy, which the ontology contract does.
        """
        if resolver is None:
            return True
        endpoint_id = element_id(endpoint)
        if endpoint_id is None:
            return False
        if endpoint_id in resolver["lineage_ids"]:
            return True
        for typing_id in resolver["typed_by"].get(endpoint_id, ()):
            if typing_id in resolver["lineage_ids"]:
                return True
        return False

    def _lineage_resolver(
        self, lineage_class: str, by_id: dict[str, dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Ground one ontology lineage class and precompute its member ids.

        The root UUID comes from the ingestion-validated kernel binding
        index; lineage membership follows Subclassification witnesses from
        the bound revision and usage typing via FeatureTyping. A class
        without a validated binding fails closed.
        """
        if self.kernel_bindings is None:
            raise IdentityNotFoundError(
                f"no validated kernel binding index is available; lineage "
                f"root {lineage_class!r} cannot be resolved without "
                f"ingestion-validated binding metadata"
            )
        root_id = self.kernel_bindings.element_id_for(lineage_class, by_id)
        specifics_by_general: dict[str, set[str]] = {}
        typed_by: dict[str, set[str]] = {}
        for element in by_id.values():
            element_type = str(element.get("@type"))
            if element_type == "Subclassification":
                general = element_id(element.get("superclassifier")) or (
                    element_id(element.get("general"))
                )
                specific = element_id(element.get("subclassifier")) or (
                    element_id(element.get("specific"))
                )
                if general is not None and specific is not None:
                    specifics_by_general.setdefault(general, set()).add(specific)
            elif element_type == "FeatureTyping":
                usage_id = element_id(element.get("owningRelatedElement"))
                if usage_id is None:
                    continue
                typed = element_id(element.get("type")) or element_id(
                    element.get("general")
                )
                if typed is not None:
                    typed_by.setdefault(usage_id, set()).add(typed)
        lineage_ids: set[str] = set()
        frontier: list[str | None] = [root_id]
        while frontier:
            current = frontier.pop()
            if current is None or current in lineage_ids:
                continue
            lineage_ids.add(current)
            frontier.extend(specifics_by_general.get(current, ()))
        return {"lineage_ids": lineage_ids, "typed_by": typed_by}

    def _marker_definition_ids(
        self, marker_name: str, by_id: dict[str, dict[str, Any]]
    ) -> set[str] | None:
        """Resolve the metadata definition's validated API UUID(s).

        Identity comes from the ingestion-validated kernel binding index (the
        ontology class entry for the marker), never from element names. The
        definition UUID must exist in the bound revision with the expected
        API type.
        """
        if self.kernel_bindings is None:
            return None
        try:
            return {
                self.kernel_bindings.element_id_for(marker_name, by_id)
            }
        except IdentityNotFoundError:
            return None

    def _excluded_specialization_ids(
        self,
        root_class: Any,
        by_id: dict[str, dict[str, Any]],
    ) -> set[str]:
        """Return elements in the specialization lineage of one kernel class.

        ``root_class`` names an ONTOLOGY class (for example ``MemberProduct``).
        The canonical SysML identity is the UUID validated at ingestion time
        and persisted in the revision binding's kernel bindings: the
        ingestion-side ontology validation confirmed the API type/name
        against the serializer-recorded source document. Runtime traversal
        consumes that validated UUID against the API graph and never
        re-derives identity from element names or SysML source text (ADR
        0011: no custom textual parser, no source-derived runtime
        semantics).

        Behavior contract:

        - canonical declaration present (+ any unrelated same-named
          declarations elsewhere): the validated canonical element grounds
          and homonyms cannot borrow the mapping;
        - canonical declaration absent (binding UUID missing from the
          revision, or ingestion never validated the class):
          ``IdentityNotFoundError`` — fail closed even when unrelated
          homonyms survive;
        - more than one genuinely grounded canonical candidate is
          unrepresentable in the binding schema and is rejected as
          ambiguous at ingestion time.

        The result contains two populations, both excluded from incoming
        architecture traversal:

        - definitions in the transitive ``Subclassification`` lineage of the
          validated kernel definition (so specialized product definitions
          cannot pose as architecture sources), and
        - usages whose ``FeatureTyping`` resolves to a lineage definition.
        """
        if not root_class:
            return set()
        if not isinstance(root_class, str):
            raise ValueError(
                "exclude_source_specializations_of must be an ontology class name"
            )
        self.contract.class_mapping(root_class)
        if self.kernel_bindings is None:
            raise IdentityNotFoundError(
                f"no validated kernel binding index is available; exclusion root "
                f"{root_class!r} cannot be resolved without ingestion-validated "
                f"binding metadata"
            )
        root_id = self.kernel_bindings.element_id_for(root_class, by_id)
        # Single-pass Subclassification index: general -> specifics.
        specifics_by_general: dict[str, set[str]] = {}
        for element in by_id.values():
            if str(element.get("@type")) != "Subclassification":
                continue
            general = element_id(element.get("superclassifier")) or element_id(
                element.get("general")
            )
            specific = element_id(element.get("subclassifier")) or element_id(
                element.get("specific")
            )
            if general is not None and specific is not None:
                specifics_by_general.setdefault(general, set()).add(specific)
        lineage: set[str] = set()
        frontier: list[str | None] = [root_id]
        while frontier:
            current = frontier.pop()
            if current is None or current in lineage:
                continue
            lineage.add(current)
            frontier.extend(specifics_by_general.get(current, ()))
        # Single-pass FeatureTyping reverse index: usage -> typed definitions.
        feature_typing: dict[str, set[str]] = {}
        for element in by_id.values():
            if str(element.get("@type")) != "FeatureTyping":
                continue
            usage_id = element_id(element.get("owningRelatedElement"))
            if usage_id is None:
                continue
            typed = element_id(element.get("type")) or element_id(
                element.get("general")
            )
            if typed is not None:
                feature_typing.setdefault(usage_id, set()).add(typed)
        excluded: set[str] = set()
        for candidate_id, element in by_id.items():
            if str(element.get("@type")) not in {
                "PartUsage",
                "PartDefinition",
                "ActionUsage",
                "ActionDefinition",
            }:
                continue
            # Definitions that are themselves in the lineage are product
            # structure, not architecture sources.
            if candidate_id in lineage:
                excluded.add(candidate_id)
                continue
            if feature_typing.get(candidate_id, set()) & lineage:
                excluded.add(candidate_id)
        return excluded

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
        """Reverse-traverse native verification relationships.

        Shapes derived from the SysML v2 2025-02-01 API schema:

        - a ``RequirementVerificationMembership`` references the verified
          requirement as its ``memberElement`` (a Membership's member) or
          through ``verifiedRequirement``, with the verification case resolved
          from its owner; and
        - a ``VerificationCaseUsage``/``VerificationCaseDefinition`` carries
          verified requirement references directly in ``verifiedRequirement``.

        A verifiedBy hop additionally requires the queried requirement to
        participate in the native verification path. A ReferenceSubsetting
        bridges a serialized reference usage (the "shadow") to the declared
        requirement when the shadow, not the declaration, is the RVM member.
        Containment ancestry without an RVM never qualifies (fail closed).
        """
        config = mapping.configuration
        membership_types = {
            str(item)
            for item in config.get(
                "membership_types", ["RequirementVerificationMembership"]
            )
        }
        element_types = {
            str(item) for item in config.get("element_types", [])
        }
        reference_property = str(
            config.get("reference_property", "verifiedRequirement")
        )
        by_id = {
            candidate_id: item
            for item in elements
            if (candidate_id := element_id(item)) is not None
        }

        def anchors_of(membership: dict[str, Any]) -> set[str]:
            return set(
                reference_ids(membership.get(reference_property))
                + reference_ids(membership.get("memberElement"))
            )

        def _owners_of(membership: dict[str, Any]) -> list[str]:
            return reference_ids(membership.get("owningRelatedElement")) + (
                reference_ids(membership.get("owner"))
                + reference_ids(membership.get("owningType"))
            )

        # ReferenceSubsetting reverse index: declared requirement -> shadow
        # reference usage.
        refsub_reverse: dict[str, set[str]] = {}
        for element in elements:
            if str(element.get("@type")) != "ReferenceSubsetting":
                continue
            for target_ref in reference_ids(element.get("referencedFeature")):
                for shadow_ref in reference_ids(
                    element.get("owningRelatedElement")
                ) + reference_ids(element.get("owner")):
                    refsub_reverse.setdefault(target_ref, set()).add(shadow_ref)

        # Membership edges for upward owner walking (containment chain).
        owner_chain_types = {
            str(item)
            for item in config.get(
                "owner_membership_types",
                ["FeatureMembership", "OwningMembership", "ObjectiveMembership"],
            )
        }
        _owners_index: dict[str, set[str]] = {}
        for membership in elements:
            if str(membership.get("@type")) not in owner_chain_types:
                continue
            for member_ref in (
                reference_ids(membership.get("memberElement"))
                + reference_ids(membership.get("ownedMemberElement"))
            ):
                for owner_ref in (
                    reference_ids(membership.get("owningRelatedElement"))
                    + reference_ids(membership.get("owner"))
                    + reference_ids(membership.get("membershipOwningNamespace"))
                ):
                    _owners_index.setdefault(member_ref, set()).add(owner_ref)

        # Start points: the declared requirement and, when a shadow reference
        # usage subsettings it, the shadow (so upward walking can proceed).
        starts: set[str] = {source_id} | refsub_reverse.get(source_id, set())

        hops: list[TraversalHop] = []
        for membership in elements:
            if str(membership.get("@type")) not in membership_types:
                continue
            # Fail-closed: the RVM must anchor on the requirement itself or on
            # a shadow that ReferenceSubsetting ties to it.
            if not (anchors_of(membership) & starts):
                continue
            # Walk owners upward from the RVM; stop at the first case.
            frontier = list(_owners_of(membership))
            seen = set(frontier)
            while frontier:
                current = frontier.pop()
                case = by_id.get(current)
                if case is not None and str(case.get("@type")) in element_types:
                    hops.append(self._hop(mapping, source, case, membership))
                    break
                frontier.extend(_owners_index.get(current, set()) - seen)
                seen |= _owners_index.get(current, set())
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
    def _reachable_members_multi(
        starts: set[str], members_by_owner: dict[str, set[str]]
    ) -> set[str]:
        """Collect member IDs transitively owned by any of ``starts``.

        Walks the ownership direction (owner -> member), so every reached
        element is genuinely below an anchored verification membership.
        """
        reached: set[str] = set()
        frontier = list(starts)
        while frontier:
            owner = frontier.pop()
            for member_id in members_by_owner.get(owner, ()):  # noqa: B905
                if member_id in reached:
                    continue
                reached.add(member_id)
                frontier.append(member_id)
        return reached

    @staticmethod
    def _reachable_members(
        start_id: str, members_by_owner: dict[str, set[str]]
    ) -> set[str]:
        """Collect member element IDs transitively owned by ``start_id``."""
        reached: set[str] = set()
        frontier = [start_id]
        while frontier:
            owner = frontier.pop()
            for member_id in members_by_owner.get(owner, ()):  # noqa: B905
                if member_id in reached:
                    continue
                reached.add(member_id)
                frontier.append(member_id)
        return reached

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
