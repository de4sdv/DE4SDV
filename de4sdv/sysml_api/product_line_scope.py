"""Revision-bound API validation for the governed AEBS product-line scope.

The validator consumes official SysML API element objects and their export source
map. Descriptive names are used only to resolve the governed schema anchors once;
all membership, typing, variant, mapping, derivation, and binding checks then use
API UUID relationships.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .repository import element_id, reference_ids


SCOPE_SOURCE = (
    "model-based-product-line-engineering/scoping/"
    "de4sdv_aebs_product_line_scope.sysml"
)


class ScopeSemanticError(ValueError):
    """The imported scope graph is missing, ambiguous, or outside governance."""


class _ScopeGraph:
    def __init__(
        self,
        elements: Iterable[dict[str, Any]],
        element_sources: dict[str, str],
    ) -> None:
        self.elements = tuple(elements)
        self.by_id: dict[str, dict[str, Any]] = {}
        for element in self.elements:
            identifier = element_id(element)
            if not identifier:
                raise ScopeSemanticError("scope graph contains an element without API identity")
            if identifier in self.by_id:
                raise ScopeSemanticError(f"duplicate API identity in scope graph: {identifier}")
            self.by_id[identifier] = element
        self.element_sources = element_sources
        for identifier in element_sources:
            if identifier not in self.by_id:
                raise ScopeSemanticError(
                    f"element source map references an absent element: {identifier}"
                )

    def require(self, identifier: str) -> dict[str, Any]:
        try:
            return self.by_id[identifier]
        except KeyError as exc:
            raise ScopeSemanticError(f"referenced API identity is absent: {identifier}") from exc

    def unique_named(self, name: str, element_type: str) -> tuple[str, dict[str, Any]]:
        matches = [
            (identifier, element)
            for identifier, element in self.by_id.items()
            if element.get("@type") == element_type
            and (element.get("declaredName") or element.get("name")) == name
        ]
        if len(matches) != 1:
            raise ScopeSemanticError(
                f"expected one {element_type} named {name}, found {len(matches)}"
            )
        identifier, element = matches[0]
        self.require_scope_source(identifier)
        return identifier, element

    def require_scope_source(self, identifier: str) -> str:
        source = self.element_sources.get(identifier)
        if source != SCOPE_SOURCE:
            raise ScopeSemanticError(
                f"scope element {identifier} has wrong source provenance: {source!r}"
            )
        return source

    def _relationship_scope_source(self, relationship: dict[str, Any]) -> None:
        identifier = element_id(relationship) or ""
        if not identifier or self.element_sources.get(identifier) != SCOPE_SOURCE:
            raise ScopeSemanticError(
                f"scope relationship {identifier} has wrong source provenance: "
                f"{self.element_sources.get(identifier)!r}"
            )

    def owned_member_ids(self, owner_id: str) -> tuple[str, ...]:
        members: list[str] = []
        for relationship in self.elements:
            if relationship.get("@type") not in {
                "FeatureMembership",
                "OwningMembership",
                "Membership",
            }:
                continue
            if element_id(relationship.get("owningRelatedElement")) != owner_id:
                continue
            self._relationship_scope_source(relationship)
            member_id = element_id(
                relationship.get("memberElement")
                or relationship.get("ownedRelatedElement")
            )
            if member_id:
                self.require(member_id)
                members.append(member_id)
        return tuple(sorted(members))

    def type_ids(self, usage_id: str) -> frozenset[str]:
        types: set[str] = set()
        for relationship in self.elements:
            if relationship.get("@type") != "FeatureTyping":
                continue
            typed = element_id(
                relationship.get("typedFeature") or relationship.get("specific")
            )
            if typed != usage_id:
                continue
            self._relationship_scope_source(relationship)
            target = element_id(relationship.get("type") or relationship.get("general"))
            if target:
                self.require(target)
                types.add(target)
        return frozenset(types)

    def typed_usages(self, definition_id: str) -> frozenset[str]:
        result = {
            identifier
            for identifier in self.by_id
            if definition_id in self.type_ids(identifier)
        }
        return frozenset(result)

    def outgoing_dependency_targets(self, source_id: str) -> frozenset[str]:
        targets: set[str] = set()
        for relationship in self.elements:
            if relationship.get("@type") != "Dependency":
                continue
            source_ids = set(
                reference_ids(relationship.get("source"))
                + reference_ids(relationship.get("client"))
            )
            if source_id not in source_ids:
                continue
            self._relationship_scope_source(relationship)
            target_ids = set(
                reference_ids(relationship.get("target"))
                + reference_ids(relationship.get("supplier"))
            )
            for target in target_ids:
                self.require(target)
                targets.add(target)
        return frozenset(targets)

    def variant_ids(self, variation_id: str) -> frozenset[str]:
        variants: list[str] = []
        for relationship in self.elements:
            if relationship.get("@type") != "Subsetting":
                continue
            general = element_id(
                relationship.get("subsettedFeature") or relationship.get("general")
            )
            if general != variation_id:
                continue
            specific = element_id(
                relationship.get("subsettingFeature") or relationship.get("specific")
            )
            if specific:
                self.require(specific)
                variants.append(specific)
        return frozenset(variants)

    def variant_occurrences(self, variation_id: str) -> list[str]:
        occurrences: list[str] = []
        for relationship in self.elements:
            if relationship.get("@type") != "Subsetting":
                continue
            general = element_id(
                relationship.get("subsettedFeature") or relationship.get("general")
            )
            if general != variation_id:
                continue
            self._relationship_scope_source(relationship)
            specific = element_id(
                relationship.get("subsettingFeature") or relationship.get("specific")
            )
            if specific:
                self.require(specific)
                occurrences.append(specific)
        return occurrences


def _declared_name(element: dict[str, Any]) -> str:
    name = element.get("declaredName") or element.get("name")
    if not isinstance(name, str) or not name:
        raise ScopeSemanticError(
            f"element {element_id(element)} has no descriptive declared name"
        )
    return name


def _typed_owned_set(
    graph: _ScopeGraph,
    *,
    owner_name: str,
    member_type_name: str,
    expected_names: frozenset[str],
) -> dict[str, str]:
    owner_id, _ = graph.unique_named(owner_name, "PartDefinition")
    member_type_id, _ = graph.unique_named(member_type_name, "PartDefinition")
    members = graph.owned_member_ids(owner_id)
    if len(members) != len(expected_names):
        raise ScopeSemanticError(
            f"{owner_name} member count differs: expected {len(expected_names)}, "
            f"found {len(members)}"
        )
    actual: dict[str, str] = {}
    for member_id in members:
        member = graph.require(member_id)
        name = _declared_name(member)
        if graph.type_ids(member_id) != frozenset({member_type_id}):
            raise ScopeSemanticError(
                f"{owner_name}.{name} is not typed solely by {member_type_name}"
            )
        graph.require_scope_source(member_id)
        actual[name] = member_id
    if frozenset(actual) != expected_names:
        raise ScopeSemanticError(
            f"{owner_name} members differ: expected {sorted(expected_names)}, "
            f"got {sorted(actual)}"
        )
    return dict(sorted(actual.items()))


def validate_scope_elements(
    elements: Iterable[dict[str, Any]],
    element_sources: dict[str, str],
) -> dict[str, Any]:
    """Validate the ratified scope over official serializer/API objects."""

    graph = _ScopeGraph(elements, element_sources)

    decision_definition_id, _ = graph.unique_named(
        "ProductLineScopeDecisionRecord", "PartDefinition"
    )
    decision_id, _ = graph.unique_named(
        "initialAEBSProductLineScopeDecision", "PartUsage"
    )
    if graph.type_ids(decision_id) != frozenset({decision_definition_id}):
        raise ScopeSemanticError("scope decision occurrence has the wrong API type identity")
    scope_definition_id, _ = graph.unique_named(
        "GovernedDE4SDVAEBSReferenceProductLineScope", "PartDefinition"
    )
    governed_scope_id, _ = graph.unique_named(
        "governedDE4SDVAEBSReferenceProductLineScope", "PartUsage"
    )
    if graph.type_ids(governed_scope_id) != frozenset({scope_definition_id}):
        raise ScopeSemanticError("governed scope occurrence has the wrong API type identity")
    if governed_scope_id not in graph.outgoing_dependency_targets(decision_id):
        raise ScopeSemanticError("scope decision does not govern the scope by API UUID")

    portfolio_id, _ = graph.unique_named(
        "InitialPlannedReferenceMemberPortfolio", "PartDefinition"
    )
    member_ids = graph.owned_member_ids(portfolio_id)
    if len(member_ids) != 2:
        raise ScopeSemanticError(
            f"expected exactly two planned reference members, found {len(member_ids)}"
        )

    expected_members = {
        "standaloneAutowareAEBSReferenceMember": "StandaloneAutowareAEBSReferenceMember",
        "aaosIntegratedAutowareAEBSReferenceMember": (
            "AAOSIntegratedAutowareAEBSReferenceMember"
        ),
    }
    member_by_name = {
        _declared_name(graph.require(identifier)): identifier for identifier in member_ids
    }
    for member_id in member_ids:
        if graph.require(member_id).get("@type") != "PartUsage":
            raise ScopeSemanticError(
                f"planned reference member {member_id} is not a PartUsage occurrence"
            )
        graph.require_scope_source(member_id)
    if set(member_by_name) != set(expected_members):
        raise ScopeSemanticError(
            "planned reference member names differ from the governed portfolio: "
            f"{sorted(member_by_name)}"
        )

    integration_id, integration = graph.unique_named(
        "vehiclePlatformIntegrationMode", "PartUsage"
    )
    if integration.get("@type") != "PartUsage":
        raise ScopeSemanticError("Vehicle Platform Integration Mode is not a PartUsage")
    if integration.get("isVariation") is not True:
        raise ScopeSemanticError("Vehicle Platform Integration Mode is not a native variation")

    expected_modes = {
        "standalone": "StandaloneVehiclePlatformIntegration",
        "aaosIntegrated": "AAOSIntegratedVehiclePlatformIntegration",
    }
    common = _typed_owned_set(
        graph,
        owner_name="InitialCommonCoreEngineeringContent",
        member_type_name="CommonCurrentScopeEngineeringContent",
        expected_names=frozenset(
            {
                "vehicleTargetAEBS",
                "autowareApplication",
                "linuxROS2AutowareRuntime",
                "currentSensingBaseline",
                "protectedEmergencyCommandPathIndependence",
            }
        ),
    )
    derived = _typed_owned_set(
        graph,
        owner_name="DerivedArchitectureAndTechnicalRealization",
        member_type_name="DerivedTechnicalRealization",
        expected_names=frozenset(
            {
                "standaloneExecutionDomainTopology",
                "aaosIntegratedExecutionDomainTopology",
                "androidKVMTopology",
                "adapterRealization",
            }
        ),
    )
    variant_occurrences = graph.variant_occurrences(integration_id)
    common_and_derived = set(common.values()) | set(derived.values())
    if set(variant_occurrences) & common_and_derived:
        raise ScopeSemanticError(
            "common/core or derived realization is selectable product variability"
        )
    if len(variant_occurrences) != len(expected_modes):
        raise ScopeSemanticError(
            "Vehicle Platform Integration Mode alternative count differs: "
            f"expected {len(expected_modes)}, found {len(variant_occurrences)}"
        )
    variants = {_declared_name(graph.require(identifier)): identifier for identifier in variant_occurrences}
    missing_modes = set(expected_modes) - set(variants)
    if missing_modes:
        raise ScopeSemanticError(
            "Vehicle Platform Integration Mode is missing alternatives: "
            f"{sorted(missing_modes)}"
        )
    for name, definition_name in expected_modes.items():
        definition_id, _ = graph.unique_named(definition_name, "PartDefinition")
        if graph.require(variants[name]).get("@type") != "PartUsage":
            raise ScopeSemanticError(
                f"integration alternative {name} is not a PartUsage occurrence"
            )
        if graph.type_ids(variants[name]) != frozenset({definition_id}):
            raise ScopeSemanticError(
                f"integration alternative {name} is not typed by {definition_name}"
            )
        graph.require_scope_source(variants[name])

    member_modes = {
        "standaloneAutowareAEBSReferenceMember": variants["standalone"],
        "aaosIntegratedAutowareAEBSReferenceMember": variants["aaosIntegrated"],
    }
    planned_reference_members = []
    for member_name, member_id in sorted(member_by_name.items()):
        member_definition_id, _ = graph.unique_named(
            expected_members[member_name], "PartDefinition"
        )
        if graph.type_ids(member_id) != frozenset({member_definition_id}):
            raise ScopeSemanticError(
                f"planned member {member_name} has the wrong API type identity"
            )
        mode_id = member_modes[member_name]
        if mode_id not in graph.outgoing_dependency_targets(member_id):
            raise ScopeSemanticError(
                f"planned member {member_name} has no UUID relationship to its mode"
            )
        planned_reference_members.append(
            {
                "declared_name": member_name,
                "element_id": member_id,
                "integration_mode_element_id": mode_id,
                "source": graph.require_scope_source(member_id),
            }
        )

    reference_only = _typed_owned_set(
        graph,
        owner_name="ReferenceOnlyAlternativeSet",
        member_type_name="ReferenceOnlyAlternative",
        expected_names=frozenset(
            {
                "apollo",
                "openpilot",
                "eclipseSCORE",
                "autosarAdaptive",
                "automotiveGradeLinux",
                "qnxQVM",
                "acrn",
            }
        ),
    )
    deferred = _typed_owned_set(
        graph,
        owner_name="DeferredVariabilitySet",
        member_type_name="DeferredCurrentScopeVariability",
        expected_names=frozenset(
            {
                "drivingStackVariability",
                "sensingVariability",
                "expandedAEBSCapabilityVariability",
                "vehicleRuntimeVariability",
                "laterLifecycleBinding",
            }
        ),
    )
    excluded = _typed_owned_set(
        graph,
        owner_name="ExcludedSystem2ConcernSet",
        member_type_name="ExcludedSystem2Concern",
        expected_names=frozenset(
            {
                "engineeringExecutionEnvironments",
                "simulationBenchmarkConfigurations",
                "ciEvidenceCampaigns",
                "visualizationInstrumentation",
            }
        ),
    )

    if set(variants) != set(expected_modes):
        raise ScopeSemanticError(
            "Vehicle Platform Integration Mode alternatives differ: "
            f"expected {sorted(expected_modes)}, got {sorted(variants)}"
        )

    if set(member_ids) & (
        set(reference_only.values()) | set(deferred.values()) | set(excluded.values())
    ):
        raise ScopeSemanticError("non-member scope content is a planned reference member")

    development_definition_id, _ = graph.unique_named(
        "DevelopmentProductDecisionBindingStage", "PartDefinition"
    )
    development_usages = graph.typed_usages(development_definition_id)
    if len(development_usages) != 1:
        raise ScopeSemanticError(
            f"expected one Development binding stage usage, found {len(development_usages)}"
        )
    development_id = next(iter(development_usages))
    development = graph.require(development_id)
    graph.require_scope_source(development_id)

    if development_id not in graph.outgoing_dependency_targets(integration_id):
        raise ScopeSemanticError(
            "Vehicle Platform Integration Mode is not bound to Development by UUID"
        )

    expected_derivation_targets = {
        variants["standalone"]: {
            derived["standaloneExecutionDomainTopology"],
        },
        variants["aaosIntegrated"]: {
            derived["aaosIntegratedExecutionDomainTopology"],
            derived["androidKVMTopology"],
            derived["adapterRealization"],
        },
    }
    for mode_id, targets in expected_derivation_targets.items():
        if not targets.issubset(graph.outgoing_dependency_targets(mode_id)):
            raise ScopeSemanticError(
                f"integration alternative {mode_id} lacks its derived realization UUIDs"
            )

    for identifier, element in graph.by_id.items():
        if element.get("@type") != "PartDefinition":
            continue
        name = element.get("declaredName") or element.get("name")
        if (
            isinstance(name, str)
            and name != "DevelopmentProductDecisionBindingStage"
            and name.endswith("ProductDecisionBindingStage")
        ):
            raise ScopeSemanticError(
                f"unsupported product-decision binding stage is modeled: {name}"
            )

    return {
        "schema": "de4sdv-aebs-product-line-scope-validation/v1",
        "scope_source": SCOPE_SOURCE,
        "scope_decision": {
            "decision_element_id": decision_id,
            "governed_scope_element_id": governed_scope_id,
            "source": graph.require_scope_source(decision_id),
        },
        "planned_reference_members": planned_reference_members,
        "vehicle_platform_integration_mode": {
            "element_id": integration_id,
            "source": graph.require_scope_source(integration_id),
            "alternatives": dict(sorted(variants.items())),
        },
        "common_core": common,
        "derived_realization": derived,
        "reference_only": reference_only,
        "deferred": deferred,
        "excluded_system2": excluded,
        "binding_stage": {
            "declared_name": _declared_name(development),
            "element_id": development_id,
            "source": graph.require_scope_source(development_id),
        },
    }
