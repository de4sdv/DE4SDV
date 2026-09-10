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
        self._current_by_id: dict[str, dict[str, Any]] = {}

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
        if mapping.strategy == "derivation-connection":
            return self._derivation_connection_hops(
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

    def _derivation_connection_hops(
        self,
        mapping: RelationshipMapping,
        source: dict[str, Any],
        source_id: str,
        elements: list[dict[str, Any]],
        by_id: dict[str, dict[str, Any]],
    ) -> list[TraversalHop]:
        """Traverse the DE4SDV ``DerivesFromNeed`` application connections
        (plan v1.1 §16 final representation decision).

        The discriminator is the DE4SDV application connection definition:
        only a ConnectionUsage typed by the validated
        ``connection def DerivesFromNeed`` (an ontology-mapped kernel
        declaration) carries the predicate. The definition's typed ends —
        ``need : StakeholderNeedCandidate`` and
        ``derivedRequirement : RequirementCandidate`` — are the
        model-resident role carrier; the runtime identifies each witness
        end by its own typing against the Need/Requirement kernel lineages
        (R1), NOT by end order and NOT by the query direction. The native
        modeled direction is ``need -> derivedRequirement``; DE4SDV's
        canonical ``derivesRequirementFromNeed`` query traverses the same
        witness inversely (``query_direction: inverse``).

        Fail-closed contracts (plan v1.1 UG-05/06/28/29/30, R1/R2 of the
        independent review):

        - a generic Dependency with identical endpoint types is never a
          derivation (the ConnectionUsage metaclass + validated definition
          typing is the discriminator, never names);
        - a connection typed by anything other than the validated
          definition, or missing an end, or with an end outside the declared
          kernel lineages, raises :class:`IdentityNotFoundError` — corrupted
          witnesses cannot degrade into quiet absences;
        - definition identity comes from the ingestion-validated kernel
          binding index, never from element names.
        """
        config = mapping.configuration
        definition_name = str(config.get("connection_definition", ""))
        if not definition_name:
            raise ValueError(
                f"derivation-connection strategy for {mapping.name} requires "
                f"connection_definition"
            )
        query_direction = str(config.get("query_direction", "inverse"))

        # Validated application-definition identity (kernel binding; no
        # names). Missing validated identity fails closed: without it the
        # predicate has no model-resident discriminator at all.
        definition_ids = self._bound_definition_ids(definition_name, by_id)
        if definition_ids is None:
            raise IdentityNotFoundError(
                f"no validated kernel binding for the application "
                f"connection definition {definition_name!r}; predicate "
                f"{mapping.name!r} cannot be evaluated without "
                f"ingestion-validated binding metadata"
            )

        # Role resolvers from the declared kernel lineages (R1 preserved):
        # Need lineage and Requirement lineage from validated kernel UUIDs.
        lineage_resolvers = {
            key: self._lineage_resolver(str(lineage_class), by_id)
            for key, lineage_class in (
                ("source_lineage_of", config.get("source_lineage_of")),
                ("target_lineage_of", config.get("target_lineage_of")),
            )
            if lineage_class
        }

        def _grounded(element: dict[str, Any], resolver: dict[str, Any]) -> bool:
            return self._endpoint_in_lineage(element, resolver, by_id)

        definition_closure = self._definition_lineage_ids(definition_ids, by_id)

        hops: list[TraversalHop] = []
        for element in elements:
            # Discriminator: metaclass ConnectionUsage (an API metaclass is
            # representation evidence; the validated definition typing below
            # is the semantic grounding — UG-28).
            if str(element.get("@type")) != "ConnectionUsage":
                continue
            connection_id = element_id(element)
            if connection_id is None:
                continue

            # Validated definition typing: a FeatureTyping from this
            # connection to the bound DerivesFromNeed definition (the
            # subclassification closure of the definition also grounds).
            typed_by_definition = False
            for candidate in elements:
                if str(candidate.get("@type")) != "FeatureTyping":
                    continue
                if element_id(candidate.get("typedFeature")) != connection_id:
                    continue
                typed = element_id(candidate.get("type")) or element_id(
                    candidate.get("general")
                )
                if typed is not None and typed in definition_closure:
                    typed_by_definition = True
                    break
            if not typed_by_definition:
                # A ConnectionUsage NOT typed by the application definition
                # is simply another connection (quiet absence). A connection
                # that owns a BROKEN typing reference (dangling FeatureTyping
                # id) also stays quiet here — it never claimed derivation.
                continue

            # Collect the connection's ends in declared order. Ends are the
            # connection's owned ReferenceUsage members (ConnectorEnd
            # members) reachable via EndFeatureMembership ownedRelationships
            # or direct ownedMember references.
            end_ids = self._connection_end_ids(element, by_id)
            if len(end_ids) < 2:
                raise IdentityNotFoundError(
                    f"incomplete derivation witness for predicate "
                    f"{mapping.name!r} on connection "
                    f"{str(element.get('declaredName') or connection_id)!r}: "
                    f"a DerivesFromNeed connection must have a {definition_name}.need "
                    f"end and a {definition_name}.derivedRequirement end"
                )

            # Role resolution: each end must ground in exactly one of the
            # declared kernel lineages — Need lineage (the definition's
            # `need` end role) versus Requirement lineage
            # (`derivedRequirement`). Identification is by the end's own
            # typing against the lineage, direction-independent. An end
            # grounding in neither lineage is a corrupted witness.
            need_resolver = self._role_resolver(mapping, config, "need")
            requirement_resolver = self._role_resolver(
                mapping, config, "requirement"
            )
            need_end_ids: list[str] = []
            derived_end_ids: list[str] = []
            for end_id in end_ids:
                end = by_id.get(end_id)
                if end is None:
                    raise IdentityNotFoundError(
                        f"incomplete derivation witness for predicate "
                        f"{mapping.name!r} on connection "
                        f"{str(element.get('declaredName') or connection_id)!r}: "
                        f"end {end_id!r} does not exist in the bound revision"
                    )
                in_need = _grounded(end, need_resolver)
                in_requirement = _grounded(end, requirement_resolver)
                if in_need and in_requirement:
                    # Ambiguous end grounding: a usage grounded in both
                    # lineages cannot be assigned a role safely (plan §17
                    # ambiguous identity).
                    raise IdentityNotFoundError(
                        f"ambiguous derivation witness for predicate "
                        f"{mapping.name!r} on connection "
                        f"{str(element.get('declaredName') or connection_id)!r}: "
                        f"end {end_id!r} grounds in both the "
                        f"{config.get('source_lineage_of')!r} and "
                        f"{config.get('target_lineage_of')!r} lineages"
                    )
                if in_need:
                    need_end_ids.append(end_id)
                elif in_requirement:
                    derived_end_ids.append(end_id)
                else:
                    raise IdentityNotFoundError(
                        f"corrupted derivation witness for predicate "
                        f"{mapping.name!r} on connection "
                        f"{str(element.get('declaredName') or connection_id)!r}: "
                        f"end {end_id!r} grounds in neither the "
                        f"{config.get('source_lineage_of')!r} nor the "
                        f"{config.get('target_lineage_of')!r} lineage"
                    )
            if not need_end_ids or not derived_end_ids:
                raise IdentityNotFoundError(
                    f"incomplete derivation witness for predicate "
                    f"{mapping.name!r} on connection "
                    f"{str(element.get('declaredName') or connection_id)!r}: "
                    f"missing "
                    f"{'need' if not need_end_ids else 'derivedRequirement'} "
                    f"role end"
                )

            # Query-direction mapping over the SAME witness. Native model
            # direction: need -> derivedRequirement.
            if query_direction == "inverse":
                # DE4SDV derivesRequirementFromNeed: query source is the
                # derived requirement; target is the need.
                if source_id not in derived_end_ids:
                    continue
                targets = need_end_ids
            else:
                # derivedRequirementsOfNeed: query source is the need;
                # targets are the derived requirements.
                if source_id not in need_end_ids:
                    continue
                targets = derived_end_ids

            for target_id in targets:
                if target_id == source_id:
                    continue
                target = by_id.get(target_id)
                if target is None:
                    continue
                hop = self._hop(mapping, source, target, element)
                hop = replace(
                    hop,
                    witness={
                        "connection_id": connection_id,
                        "connection_definition": definition_name,
                        "connection_definition_id": sorted(definition_ids)[0],
                        "need_end_id": sorted(need_end_ids),
                        "derived_requirement_end_id": sorted(derived_end_ids),
                    },
                )
                hops.append(hop)
        return self._deduplicate(hops)

    def _role_resolver(
        self,
        mapping: RelationshipMapping,
        config: dict[str, Any],
        role: str,
    ) -> dict[str, Any]:
        """Return the lineage resolver for one derivation role.

        The Need role resolves through the lineage that the mapping declares
        for the Need side (``target_lineage_of`` when the query direction is
        inverse, ``source_lineage_of`` when forward) and the Requirement
        role through the opposite side. Role RESOLVERS are direction-keyed
        for lineage lookup only; end identification is by the end's own
        typing, never by witness end order. Raises when the declared lineage
        class cannot be grounded.
        """
        inverse = str(config.get("query_direction", "inverse")) == "inverse"
        if role == "need":
            key = "target_lineage_of" if inverse else "source_lineage_of"
        else:
            key = "source_lineage_of" if inverse else "target_lineage_of"
        lineage_class = config.get(key)
        if not lineage_class:
            raise IdentityNotFoundError(
                f"mapping for {mapping.name!r} declares no {key} lineage; "
                f"derivation roles cannot be resolved"
            )
        return self._lineage_resolver(str(lineage_class), self._current_by_id)

    def _definition_lineage_ids(
        self, definition_ids: set[str], by_id: dict[str, dict[str, Any]]
    ) -> set[str]:
        """Subclassification closure of the application definition ids."""
        specifics: dict[str, set[str]] = {}
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
                specifics.setdefault(general, set()).add(specific)
        closure: set[str] = set()
        frontier = list(definition_ids)
        while frontier:
            current = frontier.pop()
            if current in closure:
                continue
            closure.add(current)
            frontier.extend(specifics.get(current, ()))
        return closure

    def _connection_end_ids(
        self, connection: dict[str, Any], by_id: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Collect the connection usage's end element ids in declared order.

        Ends appear as EndFeatureMembership ownedRelationships (each owning a
        reference to the connected usage) or as direct owned member
        references on the connection usage.
        """
        end_ids: list[str] = []
        for reference in reference_ids(connection.get("ownedRelationship")):
            member = by_id.get(reference)
            if member is None:
                continue
            if str(member.get("@type")) == "EndFeatureMembership":
                end_ids.extend(reference_ids(member.get("ownedRelatedElement")))
        if not end_ids:
            end_ids.extend(reference_ids(connection.get("ownedMember")))
        return end_ids

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
        self._current_by_id = by_id
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

    def _bound_definition_ids(
        self, ontology_class: str, by_id: dict[str, dict[str, Any]]
    ) -> set[str] | None:
        """Resolve the application definition's validated API UUID(s).

        Identity comes from the ingestion-validated kernel binding index
        (ontology class entry whose kernel mapping grounds the definition),
        never from element names. The UUID must exist in the bound revision
        with the expected API type.
        """
        if self.kernel_bindings is None:
            return None
        try:
            return {
                self.kernel_bindings.element_id_for(ontology_class, by_id)
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
