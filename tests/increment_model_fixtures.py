"""Synthetic, export-shaped SysML model content for increment-evaluation tests.

Elements follow the shapes of the licensed full-model JSON export (owning
memberships, FeatureTyping/Subclassification objects, FeatureMembership ->
AttributeUsage -> FeatureValue -> literal or FeatureReferenceExpression,
EndFeatureMembership -> Feature -> ReferenceSubsetting connection ends, and
so on). Kernel definitions carry the model-built contract's declarations and
source files, so ingestion-shaped kernel bindings resolve them by identity.

Nothing here copies a model file: every element is synthetic and built in
code. Element identifiers are deterministic per builder.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from de4sdv.semantic.kernel_contract import KernelFileMapping, declaration_identity
from model_contract_fixtures import model_contract

ODE4HERA_SOURCE = ".sysand/lib/ode4hera-requirements-management_2.0.1/RequirementsManagement.sysml"
GATES_SOURCE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_gates.sysml"
FEATURE_SOURCE = "textual-notation-of-model/packages/features/fixture/fixture_increment.sysml"
_NAMESPACE = uuid.UUID("0b8f6a0e-6a39-5c43-9d4e-5d2c1f3c9a11")

PHASE_LITERALS = (
    "phase0_incrementFraming",
    "phase1_concernFraming",
    "phase2_operationalContext",
    "phase3_capabilityClassification",
    "phase4_needs",
    "phase5_requirements",
    "phase6_functionalArchitecture",
    "phase7_logicalArchitecture",
    "phase8_physicalRealization",
    "phase9_variabilityConfiguration",
    "phase10_vvEvidence",
    "phase11_publication",
    "phase12_baselineNextSlice",
)
SOURCE_KIND_LITERALS = ("pinnedModelRecord", "pinnedRepositoryArtifact", "liveDeliveryAdapter")
DISPOSITION_LITERALS = ("noEligibleSubjects", "explicitDisposition")
OBLIGATION_FIELDS = (
    "obligationId", "phase", "subjectSelector", "applicability", "minimumPopulation",
    "permittedEmpty", "predicate", "targetFilter", "cardinalityMinimum",
    "cardinalityMaximum", "required", "evaluationSource", "attestationPolicyRef",
    "claimBoundary",
)
INFINITY = object()


def ref(element: dict[str, Any] | str) -> dict[str, str]:
    return {"@id": element if isinstance(element, str) else element["@id"]}


@dataclass
class ModelBuilder:
    """Builds one export-shaped element corpus plus its kernel bindings."""

    label: str = "fixture"
    elements: list[dict[str, Any]] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    bindings: list[dict[str, str]] = field(default_factory=list)
    kernel: dict[str, dict[str, Any]] = field(default_factory=dict)
    library: dict[str, dict[str, Any]] = field(default_factory=dict)
    _counter: Any = field(default_factory=itertools.count, repr=False)

    # -- primitives ----------------------------------------------------------

    def new(self, kind: str, *, name: str | None = None, short: str | None = None,
            source: str = FEATURE_SOURCE, declared: bool = True, **extra: Any) -> dict[str, Any]:
        identifier = str(uuid.uuid5(_NAMESPACE, f"{self.label}/{next(self._counter)}/{kind}/{name}"))
        element: dict[str, Any] = {"@id": identifier, "@type": kind, "elementId": identifier,
                                   "ownedRelationship": []}
        if name is not None:
            element["declaredName" if declared else "name"] = name
        if short is not None:
            element["declaredShortName"] = short
        element.update(extra)
        self.elements.append(element)
        self.sources[identifier] = source
        return element

    def relationship(self, kind: str, owner: dict[str, Any], **keys: Any) -> dict[str, Any]:
        relation = self.new(kind, source=self.sources[owner["@id"]])
        relation["owningRelatedElement"] = ref(owner)
        relation.update(keys)
        owner["ownedRelationship"].append(ref(relation))
        return relation

    def own(self, owner: dict[str, Any], member: dict[str, Any], kind: str = "OwningMembership",
            member_name: str | None = None, **extra: Any) -> dict[str, Any]:
        membership = self.relationship(kind, owner, memberElement=ref(member),
                                       ownedRelatedElement=[ref(member)], **extra)
        if member_name is not None:
            membership["memberName"] = member_name
        member["owningRelationship"] = ref(membership)
        return membership

    def typed(self, usage: dict[str, Any], definition: dict[str, Any]) -> None:
        self.relationship("FeatureTyping", usage, type=ref(definition), general=ref(definition),
                          specific=ref(usage), typedFeature=ref(usage))

    def specializes(self, definition: dict[str, Any], general: dict[str, Any]) -> None:
        self.relationship("Subclassification", definition, general=ref(general),
                          superclassifier=ref(general), specific=ref(definition),
                          subclassifier=ref(definition))

    def reference_subsetting(self, holder: dict[str, Any], target: dict[str, Any]) -> None:
        self.relationship("ReferenceSubsetting", holder, general=ref(target), specific=ref(holder),
                          subsettedFeature=ref(target), subsettingFeature=ref(holder),
                          referencedFeature=ref(target))

    # -- containers ---------------------------------------------------------

    def package(self, name: str, owner: dict[str, Any] | None = None,
                source: str = FEATURE_SOURCE) -> dict[str, Any]:
        package = self.new("Package", name=name, source=source)
        if owner is not None:
            self.own(owner, package, member_name=name)
        return package

    def definition(self, kind: str, name: str, owner: dict[str, Any],
                   specializes: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
        definition = self.new(kind, name=name, source=self.sources[owner["@id"]])
        self.own(owner, definition, member_name=name)
        for general in specializes:
            self.specializes(definition, general)
        return definition

    def usage(self, kind: str, name: str | None, owner: dict[str, Any],
              typed_by: Iterable[dict[str, Any]] = (), short: str | None = None,
              membership: str = "OwningMembership", **extra: Any) -> dict[str, Any]:
        usage = self.new(kind, name=name, short=short, source=self.sources[owner["@id"]], **extra)
        self.own(owner, usage, kind=membership, member_name=name)
        for definition in typed_by:
            self.typed(usage, definition)
        return usage

    # -- kernel and library declarations ------------------------------------

    def kernel_definition(self, ontology_class: str) -> dict[str, Any]:
        """The kernel declaration of one ontology class plus its binding."""
        if ontology_class in self.kernel:
            return self.kernel[ontology_class]
        mapping = model_contract().mapping(ontology_class)
        assert isinstance(mapping, KernelFileMapping), ontology_class
        name, metaclass = declaration_identity(mapping.declaration)
        definition = self.new(metaclass, name=name, source=mapping.file)
        self.kernel[ontology_class] = definition
        self.bindings.append({"ontology_class": ontology_class, "element_id": definition["@id"],
                              "source_file": mapping.file, "declaration": mapping.declaration})
        return definition

    def enumeration(self, ontology_class: str, literals: Sequence[str]) -> dict[str, dict[str, Any]]:
        definition = self.kernel_definition(ontology_class)
        found = {}
        for literal in literals:
            usage = self.new("EnumerationUsage", name=literal, source=self.sources[definition["@id"]])
            self.own(definition, usage, kind="VariantMembership", member_name=literal)
            found[literal] = usage
        return found

    def library_feature(self, name: str) -> dict[str, Any]:
        if name not in self.library:
            holder = self.library.get("__holder__")
            if holder is None:
                holder = self.new("RequirementDefinition", name="ExtendedRequirement",
                                  source=ODE4HERA_SOURCE)
                self.library["__holder__"] = holder
            feature = self.new("AttributeUsage", name=name, source=ODE4HERA_SOURCE)
            self.own(holder, feature, kind="FeatureMembership", member_name=name)
            self.library[name] = feature
        return self.library[name]

    # -- values -------------------------------------------------------------

    def value_expression(self, owner_relation_holder: dict[str, Any], value: Any) -> dict[str, Any]:
        """One value expression element for ``value`` (owned by a FeatureValue)."""
        source = self.sources[owner_relation_holder["@id"]]
        if value is INFINITY:
            return self.new("LiteralInfinity", source=source)
        if isinstance(value, bool):
            return self.new("LiteralBoolean", source=source, value=value)
        if isinstance(value, int):
            return self.new("LiteralInteger", source=source, value=value)
        if isinstance(value, str):
            return self.new("LiteralString", source=source, value=value)
        if isinstance(value, dict):  # an element reference
            expression = self.new("FeatureReferenceExpression", source=source)
            self.relationship("Membership", expression, memberElement=ref(value))
            return expression
        if isinstance(value, (list, tuple)):
            expression = self.new("OperatorExpression", source=source, operator=",")
            for item in value:
                parameter = self.new("Feature", source=source)
                self.own(expression, parameter, kind="ParameterMembership")
                inner = self.value_expression(parameter, item)
                self.own(parameter, inner, kind="FeatureValue")
            return expression
        raise TypeError(value)

    def attribute(self, owner: dict[str, Any], name: str, value: Any,
                  redefines: dict[str, Any] | None = None, kind: str = "AttributeUsage") -> dict[str, Any]:
        feature = self.new(kind, name=name, declared=False, source=self.sources[owner["@id"]])
        self.own(owner, feature, kind="FeatureMembership", member_name=name)
        if redefines is not None:
            self.relationship("Redefinition", feature, general=ref(redefines), specific=ref(feature),
                              subsettedFeature=ref(redefines), subsettingFeature=ref(feature),
                              redefinedFeature=ref(redefines), redefiningFeature=ref(feature))
        expression = self.value_expression(feature, value)
        self.own(feature, expression, kind="FeatureValue")
        return feature

    # -- requirement memberships -------------------------------------------

    def subject(self, requirement: dict[str, Any], typed_by: dict[str, Any],
                name: str = "subj") -> dict[str, Any]:
        subject = self.new("ReferenceUsage", name=name, source=self.sources[requirement["@id"]],
                           direction="in")
        self.own(requirement, subject, kind="SubjectMembership", member_name=name)
        self.typed(subject, typed_by)
        return subject

    def stakeholder(self, owner: dict[str, Any], name: str, typed_by: dict[str, Any]) -> dict[str, Any]:
        part = self.new("PartUsage", name=name, source=self.sources[owner["@id"]], direction="in")
        self.own(owner, part, kind="StakeholderMembership", member_name=name)
        self.typed(part, typed_by)
        return part

    def statement(self, requirement: dict[str, Any]) -> dict[str, Any]:
        constraint = self.new("ConstraintUsage", name="statement", source=self.sources[requirement["@id"]],
                              isComposite=True)
        membership = self.own(requirement, constraint, kind="RequirementConstraintMembership",
                              member_name="statement")
        membership["kind"] = "requirement"
        return constraint

    def frame(self, owner: dict[str, Any], concern: dict[str, Any]) -> dict[str, Any]:
        shadow = self.new("ConcernUsage", name=concern.get("declaredName"), declared=False,
                          source=self.sources[owner["@id"]], isComposite=True)
        membership = self.own(owner, shadow, kind="FramedConcernMembership",
                              member_name=concern.get("declaredName"))
        membership["kind"] = "requirement"
        self.reference_subsetting(shadow, concern)
        return shadow

    # -- connections --------------------------------------------------------

    def connection(self, name: str, owner: dict[str, Any], typed_by: dict[str, Any],
                   ends: Sequence[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
        connection = self.usage("ConnectionUsage", name, owner, typed_by=[typed_by])
        for end_name, target in ends:
            end = self.new("Feature", name=end_name, declared=False, source=self.sources[owner["@id"]])
            self.own(connection, end, kind="EndFeatureMembership", member_name=end_name)
            self.reference_subsetting(end, target)
        connection["target"] = [ref(ends[-1][1])]
        return connection

    def references(self, package: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
        holder = self.new("ReferenceUsage", source=self.sources[package["@id"]])
        self.own(package, holder)
        self.reference_subsetting(holder, target)
        return holder

    # -- verification -------------------------------------------------------

    def objective(self, owner: dict[str, Any], name: str, verifies: Iterable[dict[str, Any]]) -> dict[str, Any]:
        objective = self.new("RequirementUsage", name=name, source=self.sources[owner["@id"]], isComposite=True)
        self.own(owner, objective, kind="ObjectiveMembership", member_name=name)
        for requirement in verifies:
            shadow = self.new("RequirementUsage", name=requirement.get("declaredName"), declared=False,
                              source=self.sources[owner["@id"]], isComposite=True)
            membership = self.own(objective, shadow, kind="RequirementVerificationMembership",
                                  member_name=requirement.get("declaredName"))
            membership["kind"] = "requirement"
            self.reference_subsetting(shadow, requirement)
        return objective

    # -- export -------------------------------------------------------------

    def export(self, git_commit: str = "a" * 40) -> dict[str, Any]:
        return {"schema": "de4sdv-sysml-api-baseline-export/v1", "git_commit": git_commit,
                "elements": list(self.elements), "element_sources": dict(self.sources),
                "external_references": [], "source_manifest": []}
