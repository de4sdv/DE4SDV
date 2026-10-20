"""Read the method of an increment, its workflow, into a method contract.

This module is the only place that knows the representation of the method
(``DE4SDV_IncrementWorkflow``), so a change of that representation is a local
change here.

The workflow is reached from the increment's charter through native relations
only, starting at ingestion-validated identity (ADR 0011); no element is
looked up by name:

- the charter is the increment's IncrementTraceObligations-lineage declaration
  whose ``increment`` value references the increment (bound kernel lineage);
- charter -> its definition (or a definition it specializes) -> the
  ``workflow`` action feature -> that feature's type: the workflow definition;
- workflow definition -> its owned step actions -> their step definitions,
  ordered by the successions between the steps (successions to the standard
  ``start`` and ``done`` actions are not steps);
- step definition -> its ``phase`` (a MethodPhase literal, bound kernel
  enumeration), parameters (direction, multiplicity, usually a type) and
  metadata usages whose metadata definition declares or inherits ``check``:
  ``check`` (the check id), ``minimum`` (default 1), ``advisory`` (default
  false: blocking), ``about`` one parameter of the step. Members, phase and
  attribute values are own or inherited through the definitions' generals
  (nearest first); a redefinition replaces what it redefines, so a tailored
  step keeps the checks it does not redefine.

Element names never identify anything; member names (``workflow``,
``phase``, ``check``, ``minimum``, ``advisory``) select features of elements
reached through native relations from validated identity.

Contract, one obligation per check:

- subjects: the elements that conform to the parameter (typed by its type
  or a specialization of it, or, for an untyped parameter such as
  ``out verification cases[1..*]``, of its usage kind) in the framing step's
  scope, the increment's own package (the mandatory step: framing always
  applies), or in a later step's scope, the packages the charter names in
  ``expectedArtifacts``. A parameter typed by a class that an end pair of a
  native-allocation relation reaches (a function, logical or physical
  element) counts those packages at any depth, and the elements of that
  type that the allocations owned there name (one hop): the increment's
  architecture elements include what it reuses through its own
  allocations;
- population: within the parameter's multiplicity (no multiplicity: exactly
  one); a lower bound of 0 permits an empty population;
- cardinality: ``minimum`` distinct targets, bounded above where the check
  states a maximum;
- applicability: a mandatory step always applies; an optional step
  (``[0..1]``) applies when the charter declares its phase;
- every check is evaluated: the successions order the steps, which ranks
  ``next``, and never block a check.

An unknown check id, a check about anything but a parameter of its step, an
undecodable multiplicity or cyclic successions make the method invalid.
Without exactly one charter (a new or ambiguous increment) the method is the
one workflow the revision's charters declare, so the framing step still says
what to author.

Beside the contract, the method lists every step in method order, with or
without checks: its phase, its parameters (direction, kind, type,
multiplicity), its documentation and the obligations of its checks. A step
without checks has no obligation, so only this list says what it requires;
it never enters the contract or its digest.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from . import method_evaluator as me
from .element_description import USAGE_KEYWORDS
from .increment_scope import (
    CHARTER_CLASS,
    IDENTITY_PROBLEM,
    PHASE_CLASS,
    PROBLEM_INVALID,
    SCOPE_PROBLEM,
    IncrementScope,
    ModelView,
    ordered,
    scope_closure,
)
from .method_checks import ALLOCATION_CHECKS, CHECK_MAXIMUM, default_claim, method_checks
from .relation_checks import MethodSideInput, allocation_ends, allocation_pairs, native_allocation_rows
from .revision_index import MultiplicityError

#: The governed ``MethodPhase`` literals of the method kernel, by phase number.
CANONICAL_PHASE_LITERALS = {
    0: "phase0_incrementFraming",
    1: "phase1_concernFraming",
    2: "phase2_operationalContext",
    3: "phase3_capabilityClassification",
    4: "phase4_needs",
    5: "phase5_requirements",
    6: "phase6_functionalArchitecture",
    7: "phase7_logicalArchitecture",
    8: "phase8_physicalRealization",
    9: "phase9_variabilityConfiguration",
    10: "phase10_vvEvidence",
    11: "phase11_publication",
    12: "phase12_baselineNextSlice",
}
#: Upper cardinality bound standing for "unbounded" (``*``).
UNBOUNDED = 1_000_000
PHASE_ORDER = {literal: number for number, literal in CANONICAL_PHASE_LITERALS.items()}
METHOD_ID = "de4sdv.increment-workflow"
#: The charter's feature whose type is the increment workflow.
WORKFLOW_FEATURE = "workflow"
#: The metadata attribute that makes a metadata usage a method check.
CHECK_ATTRIBUTE = "check"
#: Selector kind of a check's subjects: the increment's elements conforming to a parameter.
PARAMETER_SELECTOR = "workflow-step-parameter"
#: Selector kind of a framing check's subjects: elements of the increment's own package.
OWN_PACKAGE_SELECTOR = "workflow-framing-parameter"
#: Subject selector of an untyped parameter: ``kind:<usage metaclass>``.
KIND_PREFIX = "kind:"
APPLICABILITY_ALWAYS = "unconditional"
APPLICABILITY_DECLARED = "increment declares the step phase"
#: Where the subjects of a later step's parameter come from.
SCOPE_LABEL = "packages named in the charter's expectedArtifacts"
#: ... and of a parameter typed by a class an allocation end pair reaches.
ARCHITECTURE_SCOPE_LABEL = ("packages named in the charter's expectedArtifacts, at any depth, and the elements "
                            "their allocations name")
DEFAULT_MINIMUM = 1
_DIRECTIONS = {"in", "out", "inout"}
_SUCCESSION_TYPES = ("SuccessionAsUsage", "Succession")


@dataclass(frozen=True)
class IncrementMethod:
    """The method read for an increment: its contract and the checks it dispatches to."""

    method_identity: Mapping[str, Any]
    contract: me.MethodContract | None
    phases: tuple[str, ...] = ()
    problems: tuple[str, ...] = ()
    reason: str = ""
    #: Check id -> evaluator predicate.
    predicates: Mapping[str, me.Predicate] = field(default_factory=dict)
    #: Display labels per obligation (step, parameter, subject type, check id).
    labels: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    #: Every step of the workflow in method order, with or without checks: step, definition,
    #: phase, optional, applicability, documentation, inputs, outputs and the obligation ids
    #: of its checks (``checks``). Description only: no step enters the contract through it.
    steps: tuple[Mapping[str, Any], ...] = ()

    @property
    def available(self) -> bool:
        return self.contract is not None

    @property
    def parameter_ids(self) -> tuple[str, ...]:
        """Every step parameter the checks are about, once each, in check order."""
        return tuple(dict.fromkeys(str(label["parameter_element_id"]) for label in self.labels.values()
                                   if label.get("parameter_element_id")))


class _Invalid(ValueError):
    pass


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------


def _scoped_subjects(spec: me.ObligationSpec, ctx: me.EvaluationContext, *,
                     own_package: bool) -> tuple[list[str], list[str]]:
    view = getattr(ctx, "model", None)
    increment = getattr(ctx, "increment", None)
    if view is None or increment is None:
        raise me.SubjectResolutionError(
            me.EVALUATOR_FAILURE, diagnostics=(f"selector {PARAMETER_SELECTOR!r} needs an increment evaluation context",))
    for key in (IDENTITY_PROBLEM,) if own_package else (IDENTITY_PROBLEM, SCOPE_PROBLEM):
        if key in increment.problems:
            kind, detail = increment.problems[key]
            raise me.SubjectResolutionError(
                me.SCOPE_RESOLUTION_ERROR if kind == PROBLEM_INVALID else me.INPUT_UNAVAILABLE,
                diagnostics=(detail,), missing=(detail,) if kind != PROBLEM_INVALID else ())
    elements = increment.own_elements if own_package else increment.scope_elements
    if spec.subject_selector.startswith(KIND_PREFIX):
        kind = spec.subject_selector[len(KIND_PREFIX):]
        return [element for element in elements if str(view.element(element).get("@type")) == kind], []
    types = view.index.specializations(spec.subject_selector)
    return [element for element in elements if view.index.typed_by(element) & types], []


def allocation_rows_entering(view: ModelView, definition: str) -> list[tuple[str, Mapping[str, Any]]]:
    """The native-allocation end pairs whose target class lineage holds ``definition`` (validated kernel
    bindings): the end pairs that reach an element typed by it. A target class without a validated
    binding reaches nothing (an export whose bindings fail validation is refused before evaluation)."""
    entering = []
    for relation, row in native_allocation_rows(view):
        try:
            kernel = view.kernel_element(str(row["targetClass"]))
        except IdentityNotFoundError:
            continue
        if definition in view.index.specializations(kernel):
            entering.append((relation, row))
    return entering


def _architecture_subjects(view: ModelView, increment: IncrementScope, definition: str,
                           rows: list[tuple[str, Mapping[str, Any]]]) -> list[str]:
    """The increment's elements typed by ``definition`` (or a specialization): owned at any depth by the
    charter's packages, plus the targets of the allocations owned there that ground one of ``rows``."""
    lineage = view.index.specializations(definition)
    closure = scope_closure(view, increment)
    inside = set(closure)
    found = [element for element in closure if view.index.typed_by(element) & lineage]
    wanted = [row for _relation, row in rows]
    relations = sorted({relation for relation, _row in rows})
    for allocation, (ends, problem) in sorted(allocation_ends(view).items()):
        if problem or len(ends) != 2 or allocation not in inside:
            continue
        source, target = ends
        if target in found or not view.index.typed_by(target) & lineage:
            continue
        grounded = [row for relation in relations for row in allocation_pairs(view, relation, source, target)]
        if any(row in wanted for row in grounded):
            found.append(target)
    return list(ordered(view, found))


def increment_architecture_elements(view: ModelView, increment: IncrementScope, ontology_class: str) -> list[str]:
    """The increment's elements of an architecture class (``PhysicalElement``), as a step parameter typed
    by the class's pinned definition counts them: at any depth in the charter's packages, plus what the
    increment's allocations name. Raises :class:`MethodSideInput` when the class has no validated kernel
    binding."""
    try:
        definition = view.kernel_element(ontology_class)
    except IdentityNotFoundError as error:
        raise MethodSideInput(f"kernel-binding:{ontology_class}",
                              f"method side: no validated kernel binding for {ontology_class}: {error}")
    rows = allocation_rows_entering(view, definition)
    return _architecture_subjects(view, increment, definition, rows) if rows else []


#: The revision scope of an export evaluated alone, such as a pull-request head (the Method Check).
EXPORT_SNAPSHOT_SCOPE = "export-snapshot"
ROOT = Path(__file__).resolve().parents[2]


#: The kernel-vocabulary admission: a governed contract input, deployed with the code (read, never generated).
ADMISSION_PATH = "de4sdv/semantic/contract-data/kernel-vocabulary-admission.yaml"


@functools.lru_cache(maxsize=None)
def open_forward_obligations(relation: str) -> tuple[str, ...]:
    """The forward obligations this checkout's kernel-vocabulary admission lists for ``relation``. An
    admission that cannot be read, or has no row for it, counts as one open obligation (fail closed)."""
    import yaml

    try:
        document = yaml.safe_load((ROOT / ADMISSION_PATH).read_text(encoding="utf-8"))
        rows = [row for row in document["admitted"] if row.get("identity") == relation]
    except Exception as error:  # noqa: BLE001 - an unreadable admission leaves the obligations open
        return (f"the kernel-vocabulary admission cannot be read: {error}",)
    if not rows:
        return (f"the kernel-vocabulary admission has no row for {relation}",)
    return tuple(str(item) for row in rows for item in row.get("forward_obligations") or ())


def allocations_withheld(ctx: me.EvaluationContext, view: ModelView) -> str:
    """Why the checks that read native allocations are withheld ('' when they are evaluated): on any
    revision but an export snapshot (an API revision binding), while a relation the allocations carry
    has open forward obligations. The guard lifts once the admission lists none."""
    if getattr(getattr(ctx, "revision", None), "scope", None) == EXPORT_SNAPSHOT_SCOPE:
        return ""
    found = [f"{relation}: {item}" for relation in sorted({name for name, _row in native_allocation_rows(view)})
             for item in open_forward_obligations(relation)]
    if not found:
        return ""
    return ("method side: an API revision binding withholds the checks that read native allocations while "
            f"forward obligations are open ({'; '.join(found)}); the pull-request Method Check evaluates them "
            "on the export")


def _parameter_subjects(spec: me.ObligationSpec, ctx: me.EvaluationContext) -> tuple[list[str], list[str]]:
    """Subjects of a later step's check: the charter-declared scope; for a parameter typed by a class an
    allocation end pair reaches, that scope at any depth plus what its allocations name (one hop). A
    check that reads native allocations, or counts such a parameter, is method side while
    :func:`allocations_withheld` holds."""
    subjects, diagnostics = _scoped_subjects(spec, ctx, own_package=False)
    view, increment = ctx.model, ctx.increment  # type: ignore[attr-defined]  # checked by _scoped_subjects
    kind = spec.subject_selector.startswith(KIND_PREFIX)
    rows = [] if kind else allocation_rows_entering(view, spec.subject_selector)
    allocated = {name for name, _row in native_allocation_rows(view)}
    if rows or spec.predicate in allocated | ALLOCATION_CHECKS:
        withheld = allocations_withheld(ctx, view)
        if withheld:
            raise me.SubjectResolutionError(me.INPUT_UNAVAILABLE, diagnostics=(withheld,),
                                            missing=tuple(f"governed-relation:{name}" for name in sorted(allocated)))
    if not rows:
        return subjects, diagnostics
    try:
        return _architecture_subjects(view, increment, spec.subject_selector, rows), diagnostics
    except MethodSideInput as missing:
        raise me.SubjectResolutionError(me.INPUT_UNAVAILABLE, diagnostics=(missing.detail,),
                                        missing=(missing.marker,))


def _framing_subjects(spec: me.ObligationSpec, ctx: me.EvaluationContext) -> tuple[list[str], list[str]]:
    """Subjects of a framing check: the increment's own package."""
    return _scoped_subjects(spec, ctx, own_package=True)


#: Selector kind -> subject resolution of the workflow's checks.
WORKFLOW_SELECTORS: Mapping[str, me.SubjectResolver] = {
    PARAMETER_SELECTOR: _parameter_subjects, OWN_PACKAGE_SELECTOR: _framing_subjects}


# ---------------------------------------------------------------------------
# Finding the workflow from a charter
# ---------------------------------------------------------------------------


def workflow_of(view: ModelView, charter: str) -> tuple[str | None, str]:
    """The workflow definition a charter declares, or why there is none."""
    index = view.index
    holders = [charter]
    for definition in sorted(index.typed_by(charter)):
        holders.extend(general for general in index.generals(definition) if general not in holders)
    for holder in holders:
        feature = index.feature(holder, WORKFLOW_FEATURE)
        if feature is None:
            continue
        types = sorted(index.typed_by(feature))
        if len(types) != 1 or str(index.element(types[0]).get("@type")) != "ActionDefinition":
            return None, (f"the charter's {WORKFLOW_FEATURE} feature is typed by {len(types)} definitions; "
                          "exactly one action definition is required")
        return types[0], ""
    return None, f"the charter declares no {WORKFLOW_FEATURE} feature (charter definition -> workflow)"


def _all_charters(view: ModelView) -> list[str]:
    """Every charter declaration of the revision: an IncrementTraceObligations-lineage part usage
    declared in a package (never, for example, a step's ``charter`` parameter)."""
    found: list[str] = []
    for candidate in view.index.elements_of_type("PartUsage"):
        if str(view.element(view.index.owner_of(candidate)).get("@type")) not in ("Package", "LibraryPackage"):
            continue
        try:
            if view.in_lineage(candidate, CHARTER_CLASS):
                found.append(candidate)
        except IdentityNotFoundError:
            return []
    return sorted(found)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _unavailable(view: ModelView, identity: dict[str, Any], reason: str) -> IncrementMethod:
    return IncrementMethod(method_identity=identity, contract=None, reason=reason, predicates=method_checks(view))


def read_increment_method(view: ModelView, scope: IncrementScope, *, revision_label: str) -> IncrementMethod:
    """The method of one increment: the workflow its charter declares (else the revision's one workflow)."""
    if len(scope.charters) != 1:
        return read_revision_method(view, revision_label=revision_label)
    identity = {"method_id": METHOD_ID, "method_revision": revision_label}
    workflow, problem = workflow_of(view, scope.charters[0])
    if workflow is None:
        return _unavailable(view, identity, problem)
    return read_workflow(view, workflow, revision_label=revision_label)


def read_revision_method(view: ModelView, *, revision_label: str) -> IncrementMethod:
    """The method the revision's charters declare, when they declare exactly one workflow."""
    identity = {"method_id": METHOD_ID, "method_revision": revision_label}
    workflows = sorted({workflow for charter in _all_charters(view)
                        if (workflow := workflow_of(view, charter)[0]) is not None})
    if len(workflows) != 1:
        return _unavailable(view, identity, f"the revision's charters declare {len(workflows)} workflows; exactly "
                                            "one is read without a single charter of the increment")
    return read_workflow(view, workflows[0], revision_label=revision_label)


def read_workflow(view: ModelView, workflow: str, *, revision_label: str) -> IncrementMethod:
    """One workflow definition as a method contract."""
    checks = method_checks(view)
    identity = {"method_id": METHOD_ID, "method_revision": revision_label,
                "workflow": view.label(workflow)}
    common: dict[str, Any] = {"predicates": checks}
    try:
        phase_root = view.kernel_element(PHASE_CLASS)
    except IdentityNotFoundError as error:
        return IncrementMethod(method_identity=identity, contract=None,
                               reason=f"the increment workflow cannot be read: {error}", **common)
    index = view.index
    problems: list[str] = []
    steps = index.owned_members(workflow, "ActionUsage")
    order = _step_order(view, workflow, steps, problems)
    decoded: list[tuple[str, me.ObligationSpec, dict[str, Any]]] = []
    phases: list[str] = []
    described: list[tuple[str, dict[str, Any]]] = []
    for step in order:
        step_name = index.name_of(step) or step
        try:
            optional = _bounds(view, step)[0] == 0
            phase, step_checks = _step_checks(view, step, step_name, phase_root, checks, problems,
                                              optional=optional)
        except _Invalid as error:
            problems.append(f"step {step_name}: {error}")
            continue
        if step_checks and phase not in phases:
            phases.append(phase)
        decoded.extend((step, spec, label) for spec, label in step_checks)
        described.append((step, _describe_step(view, step, phase, optional=optional)))
    if not decoded and not problems:
        return IncrementMethod(method_identity=identity, contract=None, steps=_listed_steps(described, ()),
                               reason="the increment workflow declares no checks", **common)
    decoded = _unique_identifiers(view, decoded)
    common["steps"] = _listed_steps(described, decoded)
    specs = [spec for _step, spec, _label in decoded]
    labels = {spec.obligation_id: label for _step, spec, label in decoded}
    contract = me.MethodContract(method_id=METHOD_ID, contract_id=f"{METHOD_ID}@{revision_label}",
                                 phase=",".join(phases), obligations=tuple(specs))
    try:
        me.validate_contract(contract, checks, selector_kinds=WORKFLOW_SELECTORS)
    except me.ContractValidationError as error:
        problems.extend(error.violations)
    if problems:
        return IncrementMethod(method_identity=identity, contract=None, phases=tuple(phases),
                               labels=labels, problems=tuple(problems),
                               reason="the increment workflow is invalid", **common)
    return IncrementMethod(
        method_identity={**identity, "contract_id": contract.contract_id, "contract_digest": contract.digest()},
        contract=contract, phases=tuple(phases), labels=labels, **common,
    )


def _step_order(view: ModelView, workflow: str, steps: list[str], problems: list[str]) -> list[str]:
    """Steps in succession order (ties: declaration order)."""
    index = view.index
    predecessors: dict[str, list[str]] = {step: [] for step in steps}
    for succession in index.owned_members(workflow, *_SUCCESSION_TYPES):
        ends = _succession_ends(view, succession)
        if len(ends) != 2 or not set(ends) <= set(steps):
            continue  # for example the successions from start and to done
        first, then = ends
        if first not in predecessors[then]:
            predecessors[then].append(first)
    position = {step: number for number, step in enumerate(steps)}
    remaining = {step: set(predecessors[step]) for step in steps}
    order: list[str] = []
    while remaining:
        ready = sorted((step for step, before in remaining.items() if not before), key=position.__getitem__)
        if not ready:
            names = ", ".join(sorted(index.name_of(step) or step for step in remaining))
            problems.append(f"the successions form a cycle among the steps {names}")
            order.extend(sorted(remaining, key=position.__getitem__))
            break
        step = ready[0]
        order.append(step)
        del remaining[step]
        for before in remaining.values():
            before.discard(step)
    return order


def _succession_ends(view: ModelView, succession: str) -> list[str]:
    """The connected steps of a succession, first end first."""
    index = view.index
    ends: list[str] = []
    for relationship in index.owned_relationships(succession, "EndFeatureMembership"):
        for member in reference_ids(relationship.get("memberElement")):
            ends.append(index.declared_of(member))
    if not ends:
        element = index.element(succession)
        ends = reference_ids(element.get("source"))[:1] + reference_ids(element.get("target"))[:1]
    return ends


def _is_method_check(view: ModelView, metadata: str) -> bool:
    """A metadata usage whose metadata definition declares or inherits the ``check`` attribute."""
    return any(view.index.feature(general, CHECK_ATTRIBUTE) is not None
               for definition in view.index.typed_by(metadata) for general in view.index.generals(definition))


def _step_members(view: ModelView, step_definition: str) -> tuple[list[str], dict[str, str]]:
    """Own and inherited members of a step definition (nearest definition first), and
    redefined member -> the member that redefines it."""
    index = view.index
    members: list[str] = []
    replaced: dict[str, str] = {}
    for definition in index.generals(step_definition):
        for member in index.owned_members(definition):
            if member not in replaced and member not in members:
                members.append(member)
                replaced.update((target, member) for target in index.redefined(member))
    return [member for member in members if member not in replaced], replaced


def _step_checks(view: ModelView, step: str, step_name: str, phase_root: str, checks: Mapping[str, Any],
                 problems: list[str], *, optional: bool):
    index = view.index
    definitions = sorted(index.typed_by(step))
    if len(definitions) != 1:
        raise _Invalid(f"typed by {len(definitions)} definitions; one step action definition is required")
    step_definition = definitions[0]
    phase = _phase(view, step_definition, phase_root)
    members, replaced = _step_members(view, step_definition)
    parameters = {member: index.name_of(member) or member for member in members
                  if str(index.element(member).get("direction") or "") in _DIRECTIONS}
    found = []
    for metadata in members:
        if str(index.element(metadata).get("@type")) != "MetadataUsage" or not _is_method_check(view, metadata):
            continue
        try:
            found.append(_check(view, metadata, step_name, phase, parameters, replaced, checks, optional=optional))
        except _Invalid as error:
            problems.append(f"step {step_name}, check {index.name_of(metadata) or metadata}: {error}")
    return phase, found


def _phase(view: ModelView, step_definition: str, phase_root: str) -> str:
    index = view.index
    leaves = next((found for general in index.generals(step_definition)
                   if (found := index.feature_values(general, "phase"))), ())
    if len(leaves) != 1 or leaves[0].kind != "reference" or index.owner_of(leaves[0].value) != phase_root:
        raise _Invalid("the step definition's phase is not exactly one MethodPhase literal")
    name = index.name_of(leaves[0].value)
    if name not in PHASE_ORDER:
        raise _Invalid(f"phase {name!r} is not a MethodPhase literal")
    return name


def _check(view: ModelView, metadata: str, step_name: str, phase: str, parameters: dict[str, str],
           replaced: dict[str, str], checks: Mapping[str, Any], *,
           optional: bool) -> tuple[me.ObligationSpec, dict[str, Any]]:
    index = view.index
    about = _annotated(view, metadata)
    while len(about) == 1 and about[0] in replaced:  # a check about a redefined parameter
        about = [replaced[about[0]]]
    if len(about) != 1 or about[0] not in parameters:
        named = ", ".join(view.label(target) for target in about) or "nothing"
        raise _Invalid(f"the check is about {named}, which is not a parameter of the step")
    parameter = about[0]
    types = sorted(index.typed_by(parameter))
    if len(types) > 1:
        raise _Invalid(f"parameter {parameters[parameter]} is typed by {len(types)} definitions; at most one is allowed")
    kind = str(index.element(parameter).get("@type") or "")
    selector = types[0] if types else KIND_PREFIX + kind
    check_id = _text(view, metadata, CHECK_ATTRIBUTE)
    minimum = _natural(view, metadata, "minimum", DEFAULT_MINIMUM)
    advisory = _boolean(view, metadata, "advisory", False)
    lower, upper = _bounds(view, parameter)
    maximum = CHECK_MAXIMUM.get(check_id, UNBOUNDED)
    claim = _documentation(view, metadata) or default_claim(check_id, view)
    spec = me.ObligationSpec(
        obligation_id=index.name_of(metadata) or check_id,
        phase=phase,
        subject_selector=selector,
        # The framing step (the mandatory step) reads the increment's own
        # package; the later, optional steps read the charter-declared scope.
        selector_kind=PARAMETER_SELECTOR if optional else OWN_PACKAGE_SELECTOR,
        applicability=APPLICABILITY_DECLARED if optional else APPLICABILITY_ALWAYS,
        applicability_kind=me.APPLICABILITY_DECLARED_PHASE if optional else me.APPLICABILITY_UNCONDITIONAL,
        minimum_population=lower,
        permitted_empty=lower == 0,
        permitted_empty_disposition=me.NO_ELIGIBLE_SUBJECTS if lower == 0 else None,
        predicate=check_id,
        target_filters=(),
        cardinality=(minimum, maximum),
        required=not advisory,
        evaluation_source=me.EVALUATION_SOURCE_MODEL,
        attestation_policy_ref="",
        claim_boundary=claim,
        maximum_population=upper,
    )
    keyword = USAGE_KEYWORDS.get(kind, "")
    architecture = bool(types) and optional and bool(allocation_rows_entering(view, types[0]))
    scope = (ARCHITECTURE_SCOPE_LABEL if architecture else SCOPE_LABEL) if optional else "increment package"
    label = {"step": step_name, "parameter": parameters[parameter],
             "scope": scope,
             "direction": str(index.element(parameter).get("direction") or ""),
             "subject_type": view.label(types[0]) if types else kind, "check": check_id,
             "check_definition": view.label(sorted(index.typed_by(metadata))[0]),
             "parameter_element_id": parameter, "subject_keyword": keyword,
             "subject_type_kind": "definition" if types else "metaclass"}
    if not types:
        label["subject_type_note"] = (f"{kind} is the SysML metaclass of the untyped parameter (any {keyword} "
                                      "usage), not a model element; inspect_element does not resolve it")
    return spec, label


def _describe_step(view: ModelView, step: str, phase: str, *, optional: bool) -> dict[str, Any]:
    """What one step declares: its definition, phase, documentation and parameters (no checks yet)."""
    index = view.index
    (definition,) = sorted(index.typed_by(step))  # exactly one: _step_checks requires it
    members, _replaced = _step_members(view, definition)
    parameters = [_describe_parameter(view, member) for member in members
                  if str(index.element(member).get("direction") or "") in _DIRECTIONS]
    return {
        "step": index.name_of(step) or step,
        "definition": view.label(definition),
        "phase": phase,
        "optional": optional,
        "applicability": APPLICABILITY_DECLARED if optional else APPLICABILITY_ALWAYS,
        "documentation": " ".join(_documentation(view, definition).split()),
        "inputs": [parameter for parameter in parameters if parameter["direction"] == "in"],
        "outputs": [parameter for parameter in parameters if parameter["direction"] != "in"],
    }


def _describe_parameter(view: ModelView, parameter: str) -> dict[str, Any]:
    """One step parameter: direction, usage kind, type and multiplicity (none declared: exactly one)."""
    index = view.index
    element = index.element(parameter)
    types = sorted(index.typed_by(parameter))
    try:
        lower, upper = index.multiplicity(parameter) or (1, 1)
        multiplicity: list[Any] | None = [lower, "*" if upper is None else upper]
    except MultiplicityError:
        multiplicity = None  # a check about this parameter makes the method invalid; a description does not
    return {
        "parameter": index.name_of(parameter) or parameter,
        "direction": str(element.get("direction") or ""),
        "sysml_type": str(element.get("@type") or ""),
        "type": ", ".join(view.label(item) for item in types) or None,
        "multiplicity": multiplicity,
    }


def _listed_steps(described: list[tuple[str, dict[str, Any]]], decoded) -> tuple[dict[str, Any], ...]:
    """The described steps, each with the obligation ids of its checks (after unique naming)."""
    checks: dict[str, list[str]] = {}
    for step, spec, _label in decoded:
        checks.setdefault(step, []).append(spec.obligation_id)
    return tuple({**record, "checks": checks.get(step, [])} for step, record in described)


def _bounds(view: ModelView, feature: str) -> tuple[int, int | None]:
    """The feature's multiplicity (none declared: exactly one); undecodable is invalid."""
    try:
        return view.index.multiplicity(feature) or (1, 1)
    except MultiplicityError as error:
        raise _Invalid(f"{view.index.name_of(feature) or feature}: {error}") from None


def _unique_identifiers(view: ModelView, decoded):
    """Check names qualified by their step where two steps reuse one name."""
    counts: dict[str, int] = {}
    for _step, spec, _label in decoded:
        counts[spec.obligation_id] = counts.get(spec.obligation_id, 0) + 1
    unique = []
    for step, spec, label in decoded:
        if counts[spec.obligation_id] > 1:
            spec = replace(spec, obligation_id=f"{view.index.name_of(step) or step}.{spec.obligation_id}")
        unique.append((step, spec, label))
    return unique


def _annotated(view: ModelView, metadata: str) -> list[str]:
    found = list(reference_ids(view.index.element(metadata).get("annotatedElement")))
    for relationship in view.index.owned_relationships(metadata, "Annotation"):
        for target in reference_ids(relationship.get("annotatedElement")):
            if target not in found:
                found.append(target)
    return found


def _documentation(view: ModelView, metadata: str) -> str:
    texts = [str(view.index.element(doc).get("body") or "").strip()
             for doc in view.index.owned_members(metadata, "Documentation")]
    return " ".join(text for text in texts if text)


def _values(view: ModelView, metadata: str, name: str):
    """The check's value of ``name``, else the nearest value (a default) its definition lineage binds."""
    holders = [metadata, *(general for definition in sorted(view.index.typed_by(metadata))
                           for general in view.index.generals(definition))]
    return next((leaves for holder in holders if (leaves := view.index.feature_values(holder, name))), ())


def _text(view: ModelView, metadata: str, name: str) -> str:
    leaves = _values(view, metadata, name)
    if len(leaves) != 1 or leaves[0].kind != "string" or not str(leaves[0].value or "").strip():
        raise _Invalid(f"{name} is not exactly one non-empty String value")
    return str(leaves[0].value).strip()


def _natural(view: ModelView, metadata: str, name: str, default: int) -> int:
    leaves = _values(view, metadata, name)
    if not leaves:
        return default
    leaf = leaves[0]
    if len(leaves) != 1 or leaf.kind != "integer" or isinstance(leaf.value, bool) or int(leaf.value) < 0:
        raise _Invalid(f"{name} is not one Natural value")
    return int(leaf.value)


def _boolean(view: ModelView, metadata: str, name: str, default: bool) -> bool:
    leaves = _values(view, metadata, name)
    if not leaves:
        return default
    if len(leaves) != 1 or leaves[0].kind != "boolean":
        raise _Invalid(f"{name} is not one Boolean value")
    return bool(leaves[0].value)
