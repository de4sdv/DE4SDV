"""Read the increment workflow of one model revision into a method contract.

The method model is being reworked; this module is the only place that knows
its representation, so the final details are a local change here.

Representation (provisional):

- the method is the action definition bound to the kernel class
  ``IncrementWorkflow``; its step actions (owned action usages) are ordered
  by the successions between them;
- each step is typed by one step action definition with a ``phase``
  attribute (a MethodPhase literal) and typed ``in`` / ``out`` parameters
  with multiplicities;
- checks are metadata usages typed by the kernel class ``MethodCheck`` (or a
  specialization), owned by the step definition and ``about`` one of its
  ``out`` parameters: ``check`` (the check id), ``minimum`` (default 1) and
  ``advisory`` (default false: blocking).

Contract, one obligation per check:

- subjects: the increment's elements (members of the increment package and
  of packages that declare ``references`` to the increment, and requirement
  usages whose native subject is typed by the increment definition) whose
  type is the output parameter's type or a specialization of it;
- minimum population: the output parameter's lower multiplicity bound (no
  multiplicity: 1); a lower bound of 0 permits an empty population;
- cardinality: ``minimum`` distinct targets, bounded above only where the
  check states a maximum;
- applicability: the increment charter declares the step's phase;
- prerequisites: the blocking checks of the nearest preceding steps, by the
  successions, that declare blocking checks.

Identity is validated kernel identity (ADR 0011). Without a kernel binding for
``IncrementWorkflow`` the revision declares no workflow and the caller reads
the method gates instead. A missing ``MethodCheck`` or ``MethodPhase`` binding
leaves the workflow unavailable. An unknown check id, a check about anything
but an output parameter, or cyclic successions make the contract invalid.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from . import method_evaluator as me
from .gate_reader import PHASE_ORDER, UNBOUNDED, GateSet
from .increment_scope import (
    PROBLEM_INVALID,
    SELECTOR_INCREMENT,
    IncrementScope,
    ModelView,
    ordered_elements,
    subject_scoped_requirements,
)
from .method_checks import MethodCheckRegistry, method_checks

WORKFLOW_CLASS = "IncrementWorkflow"
CHECK_CLASS = "MethodCheck"
PHASE_CLASS = "MethodPhase"
METHOD_ID = "de4sdv.increment-workflow"
REPRESENTATION = "increment-workflow"
#: Selector kind of a check's subjects: the increment's elements of the output type.
OUTPUT_SELECTOR = "workflow-step-output"
APPLICABILITY = "increment declares the step phase"
DEFAULT_MINIMUM = 1
_OUTPUT_DIRECTIONS = {"out", "inout"}
_SUCCESSION_TYPES = ("SuccessionAsUsage", "Succession")


class _Invalid(ValueError):
    pass


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------


def scope_elements(view: ModelView, increment: IncrementScope) -> tuple[str, ...]:
    """The increment's elements a check's subjects are drawn from."""

    def build() -> tuple[str, ...]:
        members = [member for package in increment.verification_packages
                   for member in view.index.owned_members(package)]
        members.extend(subject_scoped_requirements(view, increment.definition_ids))
        return ordered_elements(view, members)

    key = ("workflow-scope", increment.usage_id, increment.definition_ids, increment.verification_packages)
    return view.index.memo(key, build)


def _output_subjects(spec: me.ObligationSpec, ctx: me.EvaluationContext) -> tuple[list[str], list[str]]:
    view = getattr(ctx, "model", None)
    increment = getattr(ctx, "increment", None)
    if view is None or increment is None:
        raise me.SubjectResolutionError(
            me.EVALUATOR_FAILURE, diagnostics=(f"selector {OUTPUT_SELECTOR!r} needs an increment evaluation context",))
    problem = increment.population_problems.get(SELECTOR_INCREMENT)
    if problem is not None:
        kind, detail = problem
        raise me.SubjectResolutionError(
            me.SCOPE_RESOLUTION_ERROR if kind == PROBLEM_INVALID else me.INPUT_UNAVAILABLE,
            diagnostics=(detail,), missing=(detail,) if kind != PROBLEM_INVALID else ())
    if increment.usage_id is None:
        detail = f"the increment {increment.increment_id!r} is not identified in the model"
        raise me.SubjectResolutionError(me.INPUT_UNAVAILABLE, diagnostics=(detail,), missing=(detail,))
    types = view.index.specializations(spec.subject_selector)
    return [element for element in scope_elements(view, increment) if view.index.typed_by(element) & types], []


WORKFLOW_SELECTORS = me.DEFAULT_SELECTORS.with_definitions(me.SelectorDefinition(OUTPUT_SELECTOR, _output_subjects))


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def read_increment_workflow(view: ModelView, *, revision_label: str) -> GateSet | None:
    """The workflow of ``view`` as one contract; ``None`` when the revision declares none."""
    try:
        workflow = view.kernel_element(WORKFLOW_CLASS)
    except IdentityNotFoundError:
        return None
    checks = method_checks(view)
    identity = {"method_id": METHOD_ID, "method_revision": revision_label, "representation": REPRESENTATION}
    common: dict[str, Any] = {"predicates": checks.predicates(), "selectors": WORKFLOW_SELECTORS,
                              "remedy": checks.remedy, "representation": REPRESENTATION}
    try:
        check_root = view.kernel_element(CHECK_CLASS)
        phase_root = view.kernel_element(PHASE_CLASS)
    except IdentityNotFoundError as error:
        return GateSet(method_identity=identity, contract=None,
                       reason=f"the increment workflow cannot be read: {error}", **common)
    index = view.index
    problems: list[str] = []
    steps = index.owned_members(workflow, "ActionUsage")
    order, predecessors = _step_order(view, workflow, steps, problems)
    check_types = index.specializations(check_root)
    decoded: list[tuple[str, me.ObligationSpec, dict[str, Any], str]] = []
    phases: list[str] = []
    for step in order:
        step_name = index.name_of(step) or step
        try:
            phase, step_checks = _step_checks(view, step, step_name, phase_root, check_types, checks, problems)
        except _Invalid as error:
            problems.append(f"step {step_name}: {error}")
            continue
        if step_checks and phase not in phases:
            phases.append(phase)
        decoded.extend((step, spec, label, element) for spec, label, element in step_checks)
    if not decoded and not problems:
        return GateSet(method_identity=identity, contract=None,
                       reason="the increment workflow declares no checks", **common)
    decoded = _unique_identifiers(view, decoded)
    blocking: dict[str, list[str]] = {}
    for step, spec, _label, _element in decoded:
        if spec.required:
            blocking.setdefault(step, []).append(spec.obligation_id)
    specs = [replace(spec, depends_on=tuple(sorted(_prerequisites(step, predecessors, blocking))))
             for step, spec, _label, _element in decoded]
    labels = {spec.obligation_id: label for _step, spec, label, _element in decoded}
    elements = {spec.obligation_id: element for _step, spec, _label, element in decoded}
    contract = me.MethodContract(method_id=METHOD_ID, contract_id=f"{METHOD_ID}@{revision_label}",
                                 phase=",".join(phases), obligations=tuple(specs))
    try:
        me.validate_contract(contract, predicates=checks.predicates(), selectors=WORKFLOW_SELECTORS)
    except me.ContractValidationError as error:
        problems.extend(error.violations)
    if problems:
        return GateSet(method_identity=identity, contract=None, phases=tuple(phases), gate_elements=elements,
                       labels=labels, problems=tuple(problems), reason="the increment workflow is invalid",
                       **common)
    return GateSet(
        method_identity={**identity, "contract_id": contract.contract_id, "contract_digest": contract.digest()},
        contract=contract, phases=tuple(phases), gate_elements=elements, labels=labels, **common,
    )


def _step_order(view: ModelView, workflow: str, steps: list[str],
                problems: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Steps in succession order (ties: declaration order) and each step's predecessors."""
    index = view.index
    predecessors: dict[str, list[str]] = {step: [] for step in steps}
    for succession in index.owned_members(workflow, *_SUCCESSION_TYPES):
        ends = _succession_ends(view, succession)
        if len(ends) != 2 or not set(ends) <= set(steps):
            problems.append(f"succession {index.qualified_name(succession) or succession} does not connect "
                            "two steps of the workflow")
            continue
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
    return order, predecessors


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


def _prerequisites(step: str, predecessors: dict[str, list[str]], blocking: dict[str, list[str]],
                   trail: frozenset[str] = frozenset()) -> set[str]:
    """Blocking checks of the nearest preceding steps that declare blocking checks."""
    found: set[str] = set()
    for previous in predecessors.get(step, ()):
        if previous in trail:
            continue
        if blocking.get(previous):
            found |= set(blocking[previous])
        else:
            found |= _prerequisites(previous, predecessors, blocking, trail | {step})
    return found


def _step_checks(view: ModelView, step: str, step_name: str, phase_root: str, check_types: frozenset[str],
                 checks: MethodCheckRegistry, problems: list[str]):
    index = view.index
    definitions = sorted(index.typed_by(step))
    if len(definitions) != 1:
        raise _Invalid(f"typed by {len(definitions)} definitions; one step action definition is required")
    step_definition = definitions[0]
    phase = _phase(view, step_definition, phase_root)
    outputs = {member: index.name_of(member) or member for member in index.owned_members(step_definition)
               if str(index.element(member).get("direction") or "") in _OUTPUT_DIRECTIONS}
    found = []
    for metadata in index.owned_members(step_definition, "MetadataUsage"):
        if not index.typed_by(metadata) & check_types:
            continue
        try:
            found.append(_check(view, metadata, step_name, phase, outputs, checks))
        except _Invalid as error:
            problems.append(f"step {step_name}, check {index.name_of(metadata) or metadata}: {error}")
    return phase, found


def _phase(view: ModelView, step_definition: str, phase_root: str) -> str:
    index = view.index
    leaves = index.feature_values(step_definition, "phase")
    if len(leaves) != 1 or leaves[0].kind != "reference" or index.owner_of(leaves[0].value) != phase_root:
        raise _Invalid("the step definition's phase is not exactly one MethodPhase literal")
    name = index.name_of(leaves[0].value)
    if name not in PHASE_ORDER:
        raise _Invalid(f"phase {name!r} is not a MethodPhase literal")
    return name


def _check(view: ModelView, metadata: str, step_name: str, phase: str, outputs: dict[str, str],
           checks: MethodCheckRegistry) -> tuple[me.ObligationSpec, dict[str, Any], str]:
    index = view.index
    about = _annotated(view, metadata)
    if len(about) != 1 or about[0] not in outputs:
        named = ", ".join(index.qualified_name(target) or target for target in about) or "nothing"
        raise _Invalid(f"the check is about {named}, which is not an output parameter of the step")
    output = about[0]
    types = sorted(index.typed_by(output))
    if len(types) != 1:
        raise _Invalid(f"output {outputs[output]} is typed by {len(types)} definitions; one is required")
    check_id = _text(view, metadata, "check")
    minimum = _natural(view, metadata, "minimum", DEFAULT_MINIMUM)
    advisory = _boolean(view, metadata, "advisory", False)
    lower = (index.multiplicity(output) or (1, 1))[0]
    definition = checks.definition(check_id) if check_id in checks else None
    maximum = definition.maximum if definition is not None and definition.maximum is not None else UNBOUNDED
    claim = (_documentation(view, metadata) or (definition.claim if definition is not None else "")
             or f"model-content check {check_id}; no acceptance, compliance, certification or "
                "evidence-adequacy claim")
    spec = me.ObligationSpec(
        obligation_id=index.name_of(metadata) or check_id,
        phase=phase,
        subject_selector=types[0],
        selector_kind=OUTPUT_SELECTOR,
        applicability=APPLICABILITY,
        applicability_kind=me.APPLICABILITY_DECLARED_PHASE,
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
    )
    label = {"step": step_name, "output": outputs[output],
             "subject_type": index.qualified_name(types[0]) or types[0], "check": check_id}
    return spec, label, metadata


def _unique_identifiers(view: ModelView, decoded):
    """Check names qualified by their step where two steps reuse one name."""
    counts: dict[str, int] = {}
    for _step, spec, _label, _element in decoded:
        counts[spec.obligation_id] = counts.get(spec.obligation_id, 0) + 1
    unique = []
    for step, spec, label, element in decoded:
        if counts[spec.obligation_id] > 1:
            spec = replace(spec, obligation_id=f"{view.index.name_of(step) or step}.{spec.obligation_id}")
        unique.append((step, spec, label, element))
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


def _text(view: ModelView, metadata: str, name: str) -> str:
    leaves = view.index.feature_values(metadata, name)
    if len(leaves) != 1 or leaves[0].kind != "string" or not str(leaves[0].value or "").strip():
        raise _Invalid(f"{name} is not exactly one non-empty String value")
    return str(leaves[0].value).strip()


def _natural(view: ModelView, metadata: str, name: str, default: int) -> int:
    leaves = view.index.feature_values(metadata, name)
    if not leaves:
        return default
    leaf = leaves[0]
    if len(leaves) != 1 or leaf.kind != "integer" or isinstance(leaf.value, bool) or int(leaf.value) < 0:
        raise _Invalid(f"{name} is not one Natural value")
    return int(leaf.value)


def _boolean(view: ModelView, metadata: str, name: str, default: bool) -> bool:
    leaves = view.index.feature_values(metadata, name)
    if not leaves:
        return default
    if len(leaves) != 1 or leaves[0].kind != "boolean":
        raise _Invalid(f"{name} is not one Boolean value")
    return bool(leaves[0].value)
