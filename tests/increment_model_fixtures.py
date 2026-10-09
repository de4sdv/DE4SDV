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
    enumerations: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
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

    def adopt(self, elements: Sequence[dict[str, Any]], bindings: Sequence[dict[str, str]]) -> None:
        """Adopt an existing kernel fixture (its roots are reused by declaration)."""
        by_id = {element["@id"]: element for element in elements}
        for element in elements:
            element.setdefault("ownedRelationship", [])
            self.elements.append(element)
            self.sources.setdefault(element["@id"], FEATURE_SOURCE)
        for binding in bindings:
            self.bindings.append(dict(binding))
            root = by_id.get(binding["element_id"])
            if root is not None:
                self.sources[root["@id"]] = binding["source_file"]
                self.kernel.setdefault(binding["ontology_class"], root)

    def kernel_definition(self, ontology_class: str) -> dict[str, Any]:
        """The kernel declaration of one ontology class plus its binding."""
        if ontology_class in self.kernel:
            return self.kernel[ontology_class]
        mapping = model_contract().mapping(ontology_class)
        assert isinstance(mapping, KernelFileMapping), ontology_class
        for binding in self.bindings:
            if (binding["source_file"], binding["declaration"]) == (mapping.file, mapping.declaration):
                existing = next(e for e in self.elements if e["@id"] == binding["element_id"])
                self.kernel[ontology_class] = existing
                return existing
        name, metaclass = declaration_identity(mapping.declaration)
        definition = self.new(metaclass, name=name, source=mapping.file)
        self.kernel[ontology_class] = definition
        self.bindings.append({"ontology_class": ontology_class, "element_id": definition["@id"],
                              "source_file": mapping.file, "declaration": mapping.declaration})
        return definition

    def enumeration(self, ontology_class: str, literals: Sequence[str]) -> dict[str, dict[str, Any]]:
        """The literals of a kernel enumeration (created once per builder)."""
        if ontology_class in self.enumerations:
            return self.enumerations[ontology_class]
        definition = self.kernel_definition(ontology_class)
        found = {}
        for literal in literals:
            usage = self.new("EnumerationUsage", name=literal, source=self.sources[definition["@id"]])
            self.own(definition, usage, kind="VariantMembership", member_name=literal)
            found[literal] = usage
        self.enumerations[ontology_class] = found
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

    def multiplicity(self, feature: dict[str, Any], *bounds: Any) -> dict[str, Any]:
        """A MultiplicityRange owned by ``feature``, in the licensed export's shape.

        ``[n]`` and ``[*]`` own one literal; ``[lower..upper]`` owns an
        OperatorExpression ``..`` whose two parameter features (direction in)
        carry the literal bounds as feature values.
        """
        source = self.sources[feature["@id"]]
        multiplicity = self.new("MultiplicityRange", source=source)
        self.own(feature, multiplicity)
        if len(bounds) == 1:
            self.own(multiplicity, self.value_expression(multiplicity, bounds[0]))
            return multiplicity
        expression = self.new("OperatorExpression", source=source, operator="..")
        self.own(multiplicity, expression)
        for bound in bounds:
            parameter = self.new("Feature", source=source, direction="in")
            self.own(expression, parameter, kind="ParameterMembership")
            self.own(parameter, self.value_expression(parameter, bound), kind="FeatureValue")
        return multiplicity

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
        present = {element["@id"] for element in self.elements}
        return {"schema": "de4sdv-sysml-api-baseline-export/v1", "git_commit": git_commit,
                "elements": list(self.elements),
                "element_sources": {k: v for k, v in self.sources.items() if k in present},
                "external_references": [], "source_manifest": []}

    def feature_of(self, owner: dict[str, Any], member_name: str) -> dict[str, Any]:
        """The feature ``owner`` owns under ``member_name``."""
        by_id = {e["@id"]: e for e in self.elements}
        for reference in owner["ownedRelationship"]:
            relationship = by_id[reference["@id"]]
            if relationship.get("memberName") == member_name:
                return by_id[relationship["memberElement"]["@id"]]
        raise KeyError(member_name)

    def remove(self, *elements: dict[str, Any]) -> None:
        """Remove elements (and the relationships naming them) from the corpus."""
        doomed = {element["@id"] for element in elements}
        for element in list(self.elements):
            if element["@id"] in doomed:
                continue
            for key in ("memberElement", "type", "referencedFeature", "owningRelatedElement"):
                value = element.get(key)
                if isinstance(value, dict) and value.get("@id") in doomed:
                    doomed.add(element["@id"])
        self.elements[:] = [e for e in self.elements if e["@id"] not in doomed]
        for element in self.elements:
            element["ownedRelationship"] = [
                r for r in element.get("ownedRelationship", []) if r["@id"] not in doomed
            ]


@dataclass
class IncrementScenario:
    """Handles to one synthetic increment and its method vocabulary."""

    builder: ModelBuilder
    increment_id: str
    phases: dict[str, dict[str, Any]]
    framing: dict[str, Any]
    definition: dict[str, Any]
    usage: dict[str, Any]
    charter: dict[str, Any]
    problem_statement: dict[str, Any]
    concern: dict[str, Any]
    needs_package: dict[str, Any]
    needs: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    evidence_package: dict[str, Any]
    cases: list[dict[str, Any]]
    stakeholder_role: dict[str, Any]
    scenario_definition: dict[str, Any]
    vocabulary: dict[str, dict[str, Any]] = field(default_factory=dict)


def increment_scenario(
    builder: ModelBuilder | None = None,
    *,
    increment_id: str = "INC-FIXTURE-001",
    applicable_phases: Sequence[str] = (
        "phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence"),
    name: str = "Fixture",
) -> IncrementScenario:
    """A complete synthetic increment whose content satisfies the method rules.

    Framing package: increment definition and usage (declared short name),
    charter declaration, problem statement with subject and stakeholders,
    engineering question, lifecycle decision, assumption, a concern framed by
    a viewpoint of a view. Needs/requirements package: two needs (subject,
    stakeholders, statement, source, rationale, framed concern, planned
    validation scenario) and two requirements (subject, statement, primary
    verification method, DerivesFromNeed connection). Evidence package
    (declares ``references`` to the increment): one verification case
    verifying both requirements.
    """
    b = builder or ModelBuilder(label=name)
    phases = b.enumeration("MethodPhase", PHASE_LITERALS)
    roots = {cls: b.kernel_definition(cls) for cls in (
        "EngineeringIncrement", "IncrementTraceObligations", "ProblemStatement",
        "IncrementEngineeringQuestion", "IncrementLifecycleDecision", "Assumption", "Stakeholder",
        "Need", "Requirement", "EvidenceContract", "DerivesFromNeed",
        "ValidationPlanningAssociation", "ValidationPlanningScenario")}
    source_feature = b.library_feature("source")
    rationale_feature = b.library_feature("rationale")
    method_feature = b.library_feature("verificationMethod")

    framing = b.package(f"DE4SDV_{name}Framing")
    definition = b.definition("PartDefinition", f"{name}Increment", framing, [roots["EngineeringIncrement"]])
    usage = b.usage("PartUsage", f"inc{name}", framing, [definition], short=increment_id)
    role = b.definition("PartDefinition", f"{name}Engineer", framing, [roots["Stakeholder"]])
    problem = b.usage("RequirementUsage", f"{name[0].lower()}{name[1:]}ProblemStatement", framing,
                      [roots["ProblemStatement"]])
    b.subject(problem, definition, name="increment")
    b.stakeholder(problem, "engineer", role)
    b.usage("PartUsage", f"{name[0].lower()}{name[1:]}Question", framing,
            [roots["IncrementEngineeringQuestion"]])
    b.usage("PartUsage", f"{name[0].lower()}{name[1:]}Decision", framing,
            [roots["IncrementLifecycleDecision"]])
    b.usage("PartUsage", f"{name[0].lower()}{name[1:]}Assumption", framing, [roots["Assumption"]])
    concern_def = b.definition("ConcernDefinition", f"{name}Concern", framing)
    concern = b.usage("ConcernUsage", f"{name[0].lower()}{name[1:]}Concern", framing, [concern_def])
    b.stakeholder(concern, "engineer", role)
    view = b.usage("ViewUsage", f"{name[0].lower()}{name[1:]}FramingView", framing)
    viewpoint = b.usage("ViewpointUsage", "selectedViewpoint", view, membership="FeatureMembership")
    b.frame(viewpoint, concern)
    charter_def = b.definition("PartDefinition", f"{name}Charter", framing, [roots["IncrementTraceObligations"]])
    charter = b.usage("PartUsage", f"{name[0].lower()}{name[1:]}Charter", framing, [charter_def])
    b.attribute(charter, "applicablePhases", [phases[p] for p in applicable_phases])
    b.attribute(charter, "increment", usage, kind="PartUsage")
    b.attribute(charter, "owner", "fixture maintainers")
    b.attribute(charter, "expectedArtifacts", [f"DE4SDV_{name}Framing", f"DE4SDV_{name}NeedsRequirements",
                                               f"DE4SDV_{name}VerificationEvidence"])
    b.attribute(charter, "expectedReviewEvidence", ["fixture review evidence"])

    needs_package = b.package(f"DE4SDV_{name}NeedsRequirements")
    need_def = b.definition("RequirementDefinition", f"{name}Need", needs_package, [roots["Need"]])
    requirement_def = b.definition("RequirementDefinition", f"{name}Requirement", needs_package,
                                   [roots["Requirement"]])
    scenario_def = b.definition("PartDefinition", f"{name}ValidationScenario", needs_package,
                                [roots["ValidationPlanningScenario"]])
    association_def = b.definition("ConnectionDefinition", f"{name}ValidationAssociation", needs_package,
                                   [roots["ValidationPlanningAssociation"]])
    needs, requirements = [], []
    for index in range(2):
        need = b.usage("RequirementUsage", f"need{index}", needs_package, [need_def])
        b.subject(need, definition, name="increment")
        b.stakeholder(need, "engineer", role)
        b.statement(need)
        b.attribute(need, "source", "fixture framing", redefines=source_feature)
        b.attribute(need, "rationale", "fixture rationale", redefines=rationale_feature)
        b.frame(need, concern)
        scenario = b.usage("PartUsage", f"scenario{index}", needs_package, [scenario_def])
        b.connection(f"need{index}ValidationPlanning", needs_package, association_def,
                     [("source", need), ("target", scenario)])
        needs.append(need)
    for index in range(2):
        requirement = b.usage("RequirementUsage", f"requirement{index}", needs_package, [requirement_def])
        b.subject(requirement, definition, name="increment")
        b.statement(requirement)
        b.attribute(requirement, "verificationMethod", "test", redefines=method_feature)
        b.connection(f"requirement{index}DerivedFromNeed{index}", needs_package, roots["DerivesFromNeed"],
                     [("need", needs[index]), ("derivedRequirement", requirement)])
        requirements.append(requirement)

    evidence_package = b.package(f"DE4SDV_{name}VerificationEvidence")
    b.references(evidence_package, usage)
    bench = b.definition("PartDefinition", f"{name}Bench", evidence_package)
    case_def = b.definition("VerificationCaseDefinition", f"{name}Verification", evidence_package)
    b.objective(case_def, "fixtureObjective", requirements)
    case = b.usage("VerificationCaseUsage", f"{name[0].lower()}{name[1:]}Verification", evidence_package,
                   [case_def])
    b.subject(case, bench, name="verifiedBench")
    return IncrementScenario(
        builder=b, increment_id=increment_id, phases=phases, framing=framing, definition=definition,
        usage=usage, charter=charter, problem_statement=problem, concern=concern,
        needs_package=needs_package, needs=needs, requirements=requirements,
        evidence_package=evidence_package, cases=[case], stakeholder_role=role,
        scenario_definition=scenario_def, vocabulary=roots)


# ---------------------------------------------------------------------------
# Increment workflow (action def IncrementWorkflow)
# ---------------------------------------------------------------------------

WORKFLOW_SOURCE = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_increment_workflow.sysml"


@dataclass(frozen=True)
class WorkflowParameter:
    """One step parameter: a usage of ``kind`` with a direction, optional type and multiplicity."""

    name: str
    type: Any = None  # a kernel class name, a definition element, or None (untyped)
    kind: str = "PartUsage"
    direction: str = "out"
    bounds: tuple[Any, ...] = (1,)


@dataclass(frozen=True)
class WorkflowCheck:
    """One method check: a MethodCheck metadata usage about one step parameter."""

    name: str
    check: str
    about: str
    minimum: int | None = None  # None: attribute omitted (the default applies)
    advisory: bool | None = None  # None: attribute omitted (the default applies)
    doc: str | None = None


@dataclass(frozen=True)
class WorkflowStep:
    """One workflow step: its phase, parameters and checks."""

    name: str
    phase: str
    parameters: tuple[WorkflowParameter, ...]
    checks: tuple[WorkflowCheck, ...] = ()


def increment_workflow(builder: ModelBuilder, steps: Sequence[WorkflowStep], *,
                       charter: dict[str, Any] | None = None,
                       successions: Sequence[tuple[str, str]] | None = None,
                       package_name: str = "DE4SDV_IncrementWorkflow") -> dict[str, Any]:
    """The increment workflow in export shape.

    ``action def IncrementWorkflow`` owns one step action usage per step (all
    but the first ``[0..1]``), chained ``first start; then ...; then done;``:
    successions from the standard ``start`` action through the steps to
    ``done`` (``start`` and ``done`` are features outside the workflow's own
    steps), unless ``successions`` names ``(first, then)`` step pairs. Each step
    usage is typed by a step action definition with a ``phase`` attribute (a
    MethodPhase literal) and its parameters (usages with a direction, an
    optional type and a multiplicity), and owns ``MethodCheck`` metadata
    usages ``about`` one of those parameters. With a ``charter``, its
    definition owns ``action workflow : IncrementWorkflow``: the native relation
    from the increment's charter to its workflow. No kernel binding is added:
    the model registers the workflow declarations as kernel-internal.
    """
    phases = builder.enumeration("MethodPhase", PHASE_LITERALS)
    package = builder.package(package_name, source=WORKFLOW_SOURCE)
    workflow = builder.definition("ActionDefinition", "IncrementWorkflow", package)
    check_definition = builder.definition("MetadataDefinition", "MethodCheck", package)
    if charter is not None:
        attach_workflow(builder, charter, workflow)
    features = {}
    for name in ("check", "minimum", "advisory"):
        feature = builder.new("AttributeUsage", name=name, source=WORKFLOW_SOURCE)
        builder.own(check_definition, feature, kind="FeatureMembership", member_name=name)
        features[name] = feature
    library = builder.package("Actions", source="sysml-library/Actions.sysml")
    start = builder.usage("ActionUsage", "start", library)
    done = builder.usage("ActionUsage", "done", library)
    usages: dict[str, dict[str, Any]] = {}
    parameters: dict[tuple[str, str], dict[str, Any]] = {}
    checks: dict[str, dict[str, Any]] = {}
    for position, step in enumerate(steps):
        step_definition = builder.definition("ActionDefinition", f"{step.name[0].upper()}{step.name[1:]}Step",
                                             package)
        builder.attribute(step_definition, "phase", phases[step.phase])
        for spec in step.parameters:
            parameter = builder.new(spec.kind, name=spec.name, source=WORKFLOW_SOURCE, direction=spec.direction)
            builder.own(step_definition, parameter, kind="FeatureMembership", member_name=spec.name)
            if spec.type is not None:
                builder.typed(parameter, builder.kernel_definition(spec.type) if isinstance(spec.type, str)
                              else spec.type)
            builder.multiplicity(parameter, *spec.bounds)
            parameters[(step.name, spec.name)] = parameter
        for check in step.checks:
            metadata = builder.new("MetadataUsage", name=check.name, source=WORKFLOW_SOURCE)
            builder.own(step_definition, metadata, kind="FeatureMembership", member_name=check.name)
            builder.typed(metadata, check_definition)
            builder.relationship("Annotation", metadata, annotatedElement=ref(parameters[(step.name, check.about)]),
                                 annotatingElement=ref(metadata))
            builder.attribute(metadata, "check", check.check, redefines=features["check"])
            if check.minimum is not None:
                builder.attribute(metadata, "minimum", check.minimum, redefines=features["minimum"])
            if check.advisory is not None:
                builder.attribute(metadata, "advisory", check.advisory, redefines=features["advisory"])
            if check.doc is not None:
                builder.own(metadata, builder.new("Documentation", source=WORKFLOW_SOURCE, body=check.doc))
            checks[check.name] = metadata
        usage = builder.usage("ActionUsage", step.name, workflow, [step_definition], membership="FeatureMembership")
        if position:
            builder.multiplicity(usage, 0, 1)
        usages[step.name] = usage
    names = [step.name for step in steps]
    if successions is None:
        chain = [start, *(usages[name] for name in names), done]
        pairs = list(zip(chain, chain[1:]))
    else:
        pairs = [(usages[first], usages[then]) for first, then in successions]
    for first, then in pairs:
        succession = builder.new("SuccessionAsUsage", source=WORKFLOW_SOURCE)
        builder.own(workflow, succession, kind="FeatureMembership")
        for target in (first, then):
            end = builder.new("Feature", source=WORKFLOW_SOURCE)
            builder.own(succession, end, kind="EndFeatureMembership")
            builder.reference_subsetting(end, target)
    return {"workflow": workflow, "check_definition": check_definition, "steps": usages,
            "parameters": parameters, "checks": checks}


def attach_workflow(builder: ModelBuilder, charter: dict[str, Any], workflow: dict[str, Any]) -> dict[str, Any]:
    """``action workflow : <workflow>`` owned by the charter's definition."""
    by_id = {e["@id"]: e for e in builder.elements}
    typings = [by_id[r["@id"]] for r in charter["ownedRelationship"]
               if by_id[r["@id"]].get("@type") == "FeatureTyping"]
    definition = by_id[typings[0]["type"]["@id"]]
    feature = builder.new("ActionUsage", name="workflow", source=builder.sources[definition["@id"]])
    builder.own(definition, feature, kind="FeatureMembership", member_name="workflow")
    builder.typed(feature, workflow)
    return feature


def model_workflow_steps(scenario: IncrementScenario, **changes: dict[str, Any]) -> list[WorkflowStep]:
    """The steps, parameters and checks of the model's increment workflow (checked steps in full)."""
    from dataclasses import replace as _replace

    builder, framing = scenario.builder, scenario.framing
    scope = builder.definition("PartDefinition", "IncrementScope", framing)
    out_of_scope = builder.definition("PartDefinition", "OutOfScopeItem", framing)
    builder.usage("PartUsage", "fixtureScope", framing, [scope])
    builder.usage("PartUsage", "fixtureOutOfScopeItem", framing, [out_of_scope])
    p, c = WorkflowParameter, WorkflowCheck
    steps = [
        WorkflowStep("frameIncrement", "phase0_incrementFraming", (
            p("increment", "EngineeringIncrement"), p("charter", "IncrementTraceObligations"),
            p("problemStatement", "ProblemStatement", "RequirementUsage"),
            p("engineeringQuestion", "IncrementEngineeringQuestion"),
            p("lifecycleDecision", "IncrementLifecycleDecision"),
            p("assumptions", "Assumption", bounds=(1, INFINITY)), p("scope", scope),
            p("outOfScopeItems", out_of_scope, bounds=(1, INFINITY)),
            p("framedConcerns", None, "ConcernUsage", bounds=(1, INFINITY)),
        ), (
            c("incrementHasIdentifier", "incrementShortName", "increment"),
            c("incrementHasCharter", "charterReferencesIncrement", "charter"),
            c("incrementHasProblemStatement", "problemStatementSubject", "problemStatement"),
            c("incrementHasEngineeringQuestion", "ownedByIncrementPackage", "engineeringQuestion"),
            c("incrementHasLifecycleDecision", "ownedByIncrementPackage", "lifecycleDecision"),
            c("incrementHasAssumption", "ownedByIncrementPackage", "assumptions"),
            c("incrementHasStakeholder", "stakeholderMember", "problemStatement"),
            c("incrementHasFramedConcern", "framedByIncrementView", "framedConcerns"),
            c("incrementHasScope", "ownedByIncrementPackage", "scope"),
            c("incrementHasOutOfScopeItem", "ownedByIncrementPackage", "outOfScopeItems"),
            c("incrementHasOwner", "charterOwner", "charter"),
            c("incrementDeclaresApplicablePhases", "charterApplicablePhases", "charter"),
            c("incrementDeclaresExpectedArtifacts", "charterExpectedArtifacts", "charter"),
            c("incrementDeclaresExpectedReviewEvidence", "charterExpectedReviewEvidence", "charter"),
        )),
        WorkflowStep("frameConcerns", "phase1_concernFraming", (
            p("problemStatement", "ProblemStatement", "RequirementUsage", "in"),
            p("concerns", None, "ConcernUsage", bounds=(1, INFINITY)),
        )),
        WorkflowStep("elaborateNeeds", "phase4_needs", (
            p("problemStatement", "ProblemStatement", "RequirementUsage", "in"),
            p("concerns", None, "ConcernUsage", "in", (0, INFINITY)),
            p("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),
        ), (
            c("needHasStatement", "requireConstraint", "needs"),
            c("needHasStakeholder", "stakeholderMember", "needs"),
            c("needHasSource", "sourceAttribute", "needs"),
            c("needHasRationale", "rationaleAttribute", "needs"),
            c("needHasValidationScenario", "hasValidationScenario", "needs"),
            c("needFramesConcern", "framesStakeholderConcern", "needs"),
        )),
        WorkflowStep("specifyRequirements", "phase5_requirements", (
            p("needs", "Need", "RequirementUsage", "in", (0, INFINITY)),
            p("requirements", "Requirement", "RequirementUsage", bounds=(1, INFINITY)),
        ), (
            c("requirementDerivesFromNeed", "derivesRequirementFromNeed", "requirements"),
            c("requirementHasOneSubject", "oneNativeSubject", "requirements"),
            c("requirementHasVerificationMethod", "oneVerificationMethodKind", "requirements"),
            c("requirementSpecifiesFeatureOrCapability", "specifiesFeatureOrCommonCapability", "requirements",
              advisory=True),
        )),
        WorkflowStep("defineFunctionalArchitecture", "phase6_functionalArchitecture", (
            p("requirements", "Requirement", "RequirementUsage", "in", (0, INFINITY)),
            p("functions", None, "ActionUsage", bounds=(1, INFINITY)),
        )),
        WorkflowStep("planVerificationAndEvidence", "phase10_vvEvidence", (
            p("requirements", "Requirement", "RequirementUsage", "in", (0, INFINITY)),
            p("verificationCases", None, "VerificationCaseUsage", bounds=(1, INFINITY)),
        ), (
            c("verificationCaseVerifiesRequirement", "verifiesIncrementRequirement", "verificationCases"),
            c("requirementVerifiedByVerificationCase", "verifiedBy", "requirements"),
            c("verificationCaseVerifiesAcceptanceCriterion", "verifiesAcceptanceCriterion", "verificationCases",
              advisory=True),
            c("verificationCaseHasEvidenceRecordOrStatus", "evidenceRecordOrStatus", "verificationCases",
              advisory=True),
        )),
    ]
    return [_replace(step, **changes.get(step.name, {})) for step in steps]


def install_model_workflow(scenario: IncrementScenario, **changes: dict[str, Any]) -> dict[str, Any]:
    """The model's workflow, declared by the scenario's charter."""
    scenario.builder.kernel_definition("AcceptanceCriterion")
    return increment_workflow(scenario.builder, model_workflow_steps(scenario, **changes), charter=scenario.charter)
