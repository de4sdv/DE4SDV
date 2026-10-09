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
  applies), or in a later step's scope, the packages the charter declares;
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
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from . import method_evaluator as me
from .increment_scope import (
    CHARTER_CLASS,
    IDENTITY_PROBLEM,
    PHASE_CLASS,
    PROBLEM_INVALID,
    SCOPE_PROBLEM,
    IncrementScope,
    ModelView,
)
from .method_checks import CHECK_MAXIMUM, default_claim, method_checks
from .method_trace_adapter import CANONICAL_PHASE_LITERALS
from .revision_index import MultiplicityError

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

    @property
    def available(self) -> bool:
        return self.contract is not None


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


def _parameter_subjects(spec: me.ObligationSpec, ctx: me.EvaluationContext) -> tuple[list[str], list[str]]:
    """Subjects of a later step's check: the charter-declared scope."""
    return _scoped_subjects(spec, ctx, own_package=False)


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
                "workflow": view.index.qualified_name(workflow) or workflow}
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
    for step in order:
        step_name = index.name_of(step) or step
        try:
            phase, step_checks = _step_checks(view, step, step_name, phase_root, checks, problems,
                                              optional=_bounds(view, step)[0] == 0)
        except _Invalid as error:
            problems.append(f"step {step_name}: {error}")
            continue
        if step_checks and phase not in phases:
            phases.append(phase)
        decoded.extend((step, spec, label) for spec, label in step_checks)
    if not decoded and not problems:
        return IncrementMethod(method_identity=identity, contract=None,
                               reason="the increment workflow declares no checks", **common)
    decoded = _unique_identifiers(view, decoded)
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
        named = ", ".join(index.qualified_name(target) or target for target in about) or "nothing"
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
    label = {"step": step_name, "parameter": parameters[parameter],
             "scope": "declared packages" if optional else "increment package",
             "direction": str(index.element(parameter).get("direction") or ""),
             "subject_type": (index.qualified_name(types[0]) or types[0]) if types else kind, "check": check_id,
             "check_definition": index.qualified_name(sorted(index.typed_by(metadata))[0])}
    return spec, label


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
