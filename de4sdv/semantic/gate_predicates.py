"""Generic method-gate predicates and typed increment selectors.

Each predicate is one generic operator over the native model relationships of
one increment (ownership, typing, memberships, connections, feature values,
governed traversal). Phase rules stay model data: which predicate a phase
uses, with which filter, cardinality and prerequisites, is declared by the
gates in the model. A predicate never branches on phase identity.

Filter text decodes against each predicate's closed grammar into typed
target filters; a lineage names a kernel declaration (for example
``StakeholderNeedCandidate``) that resolves through the model-built contract
to its ontology class and ingestion-validated kernel binding (ADR 0011).

Inputs the method itself cannot supply are marked in ``missing`` with a
method-side prefix (``kernel-binding:``, ``governed-relation:``,
``external-relation:``); the agent cannot author those. Malformed engineering
witnesses are marked ``model-witness:``; the agent can author those.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from . import method_evaluator as me
from .kernel_contract import KernelFileMapping
from .increment_scope import (
    INCREMENT_SELECTORS,
    PROBLEM_INVALID,
    SELECTOR_REQUIREMENTS,
    IncrementScope,
    ModelView,
)

#: ``missing`` prefixes of inputs that only a method/kernel change can supply.
METHOD_SIDE_PREFIXES = ("kernel-binding:", "governed-relation:", "external-relation:")
#: ``missing`` prefix of a malformed engineering witness (authorable).
MODEL_WITNESS_PREFIX = "model-witness:"

#: Typed target-filter kinds of the gate predicates.
FILTER_LINEAGE = "kernel-lineage"
FILTER_ANY_LINEAGE = "kernel-lineage-any"
FILTER_IDENTITY = "short-name-identity"
FILTER_CHARTER = "charter-declaration"
FILTER_PACKAGE_REQUIREMENT = "package-requirement-with-increment-subject"
FILTER_PACKAGE_VIEW_FRAMING = "package-view-framing"
FILTER_CHARTER_ATTRIBUTE = "charter-attribute"
FILTER_REQUIRED_CONSTRAINT = "required-constraint"
FILTER_LIBRARY_ATTRIBUTE = "library-attribute"
FILTER_TYPED_CONNECTION = "typed-connection"
FILTER_FRAMED_CONCERN = "framed-concern-with-stakeholder"
FILTER_POPULATION_MEMBER = "population-member"
FILTER_EXTERNAL_EVIDENCE = "external-evidence"

#: The kernel class whose usages are problem statements.
PROBLEM_STATEMENT_DECLARATION = "ProblemStatement"
_IDENTIFIER = r"[A-Z][A-Za-z0-9]*"


@dataclass
class IncrementEvaluationContext(me.EvaluationContext):
    """Evaluation context of one increment: the model view and its scope."""

    model: ModelView | None = None
    increment: IncrementScope | None = None


def is_method_side(result: me.EvaluationResult) -> bool:
    return any(str(item).startswith(METHOD_SIDE_PREFIXES) for item in result.missing)


# ---------------------------------------------------------------------------
# Typed selectors
# ---------------------------------------------------------------------------


def _population(selector: str) -> me.SubjectResolver:
    def resolve(spec: me.ObligationSpec, ctx: me.EvaluationContext) -> tuple[list[str], list[str]]:
        increment = getattr(ctx, "increment", None)
        if increment is None:
            raise me.SubjectResolutionError(
                me.EVALUATOR_FAILURE,
                diagnostics=(f"selector {selector!r} needs an increment evaluation context",),
            )
        problem = increment.population_problems.get(selector)
        if problem is not None:
            kind, detail = problem
            raise me.SubjectResolutionError(
                me.SCOPE_RESOLUTION_ERROR if kind == PROBLEM_INVALID else me.INPUT_UNAVAILABLE,
                diagnostics=(detail,),
                missing=(detail,) if kind != PROBLEM_INVALID else (),
            )
        return list(increment.populations.get(selector, ())), []

    return resolve


GATE_SELECTORS = me.DEFAULT_SELECTORS.with_definitions(
    *(me.SelectorDefinition(kind, _population(kind)) for kind in INCREMENT_SELECTORS)
)


# ---------------------------------------------------------------------------
# Filter grammars (closed, per predicate)
# ---------------------------------------------------------------------------


def _grammar(*forms: tuple[str, Callable[[re.Match[str]], me.TargetFilter]]) -> me.FilterParser:
    compiled = [(re.compile(pattern), build) for pattern, build in forms]

    def parse(text: str) -> me.TargetFilter:
        for pattern, build in compiled:
            match = pattern.fullmatch(text)
            if match:
                filter_ = build(match)
                return me.TargetFilter(kind=filter_.kind, argument=filter_.argument,
                                       values=filter_.values, text=text)
        raise ValueError(f"unsupported target filter {text!r}")

    return parse


def _f(kind: str, argument: str = "", values: Sequence[str] = ()) -> me.TargetFilter:
    return me.TargetFilter(kind=kind, argument=argument, values=tuple(values))


_LINEAGE_FORM = (rf"(?P<d>{_IDENTIFIER}) lineage", lambda m: _f(FILTER_LINEAGE, m["d"]))


def _filters(spec: me.ObligationSpec, kind: str) -> list[me.TargetFilter]:
    return [item for item in spec.filters if item.kind == kind]


# ---------------------------------------------------------------------------
# Outcome helpers
# ---------------------------------------------------------------------------


class _MethodSide(Exception):
    """An input only the method or kernel can supply is missing."""

    def __init__(self, marker: str, detail: str) -> None:
        self.marker = marker
        self.detail = detail
        super().__init__(detail)


def _outcome(status: str, **fields: Any) -> me.PredicateOutcome:
    return me.PredicateOutcome(
        status=status,
        reason_codes=tuple(fields.get("codes", ())),
        targets=tuple(fields.get("targets", ())),
        witnesses=tuple(fields.get("witnesses", ())),
        missing=tuple(fields.get("missing", ())),
        diagnostics=tuple(fields.get("diagnostics", ())),
    )


def _satisfied(targets: Iterable[str], witnesses: Iterable[str] = (), diagnostics: Sequence[str] = ()):
    targets = list(dict.fromkeys(targets))
    return _outcome("satisfied", targets=targets, witnesses=list(dict.fromkeys(witnesses)) or targets,
                    diagnostics=diagnostics)


def _violated(what: str, diagnostics: Sequence[str] = (), witnesses: Iterable[str] = ()):
    return _outcome("violated", codes=(me.REQUIRED_RELATION_MISSING,), missing=(what,),
                    diagnostics=(what, *diagnostics), witnesses=list(witnesses))


def _indeterminate(marker: str, detail: str):
    return _outcome("indeterminate", codes=(me.INPUT_UNAVAILABLE,), missing=(marker,), diagnostics=(detail,))


def _requires_increment(function: Callable[..., me.PredicateOutcome]) -> me.Predicate:
    def predicate(ctx: me.EvaluationContext, spec: me.ObligationSpec, subject_id: str) -> me.PredicateOutcome:
        view = getattr(ctx, "model", None)
        increment = getattr(ctx, "increment", None)
        if view is None or increment is None:
            return _outcome("error", codes=(me.EVALUATOR_FAILURE,),
                            diagnostics=(f"predicate {spec.predicate!r} needs an increment evaluation context",))
        try:
            return function(view, increment, spec, subject_id)
        except _MethodSide as missing:
            return _indeterminate(missing.marker, missing.detail)

    predicate.__name__ = function.__name__
    return predicate


def _class_of(view: ModelView, declaration: str) -> str:
    ontology_class = view.class_of_declaration(declaration)
    if ontology_class is None:
        raise _MethodSide(
            f"kernel-binding:{declaration}",
            f"method side: {declaration} has no kernel class mapping (no ingestion-validated "
            "identity, ADR 0011); the gate cannot be evaluated until the method projects it",
        )
    return ontology_class


def _in(view: ModelView, element: str, declaration: str) -> bool:
    ontology_class = _class_of(view, declaration)
    try:
        return view.in_lineage(element, ontology_class)
    except IdentityNotFoundError as error:
        raise _MethodSide(f"kernel-binding:{ontology_class}",
                          f"method side: no validated kernel binding for {ontology_class}: {error}")


def _name(view: ModelView, element: str | None) -> str:
    return view.index.qualified_name(element) or str(element or "")


def _package_members(view: ModelView, increment: IncrementScope, *types: str) -> list[str]:
    if increment.package_id is None:
        return []
    return view.index.owned_members(increment.package_id, *types)


def _members(view: ModelView, owner: str, membership_type: str) -> list[str]:
    found: list[str] = []
    for relationship in view.index.owned_relationships(owner, membership_type):
        for member in reference_ids(relationship.get("memberElement")):
            if member not in found:
                found.append(member)
    return found


def _subject_typed_by_increment(view: ModelView, increment: IncrementScope, element: str) -> bool:
    wanted = set(increment.definition_ids)
    return any(view.index.typed_by(member) & wanted for member in _members(view, element, "SubjectMembership"))


# ---------------------------------------------------------------------------
# Increment framing predicates
# ---------------------------------------------------------------------------


@_requires_increment
def _increment_identity(view, increment, spec, subject_id):
    (identity,) = _filters(spec, FILTER_IDENTITY) or (_f(FILTER_IDENTITY, "EngineeringIncrement"),)
    holders = view.index.with_short_name(subject_id)
    found = [h for h in holders if str(view.element(h).get("@type")) == "PartUsage"
             and _in(view, h, identity.argument)]
    if not found:
        rejected = [f"{_name(view, h)} carries the identifier but is not a part usage in the "
                    f"{identity.argument} lineage" for h in holders]
        return _violated(f"no part usage in the {identity.argument} lineage carries the declared "
                         f"short name {subject_id!r}", rejected)
    return _satisfied(found)


@_requires_increment
def _charter_declaration(view, increment, spec, subject_id):
    note = ("charter identity: the IncrementTraceObligations-lineage declaration whose increment "
            "value references the increment (IncrementCharter is kernel-internal)")
    try:
        view.traversal.class_lineage("IncrementTraceObligations", view.elements)
    except IdentityNotFoundError as error:
        raise _MethodSide("kernel-binding:IncrementTraceObligations",
                          f"method side: no validated kernel binding for IncrementTraceObligations: {error}")
    if not increment.charters:
        return _violated("no charter declaration (IncrementTraceObligations lineage) references the "
                         "increment", (note,))
    return _satisfied(increment.charters, diagnostics=(note,))


@_requires_increment
def _problem_statement(view, increment, spec, subject_id):
    (rule,) = _filters(spec, FILTER_PACKAGE_REQUIREMENT)
    found = [
        member for member in _package_members(view, increment, "RequirementUsage")
        if _in(view, member, rule.argument) and _subject_typed_by_increment(view, increment, member)
    ]
    if not found:
        return _violated(f"no {rule.argument} owned by {_name(view, increment.package_id)} has a native "
                         "subject typed by the increment definition")
    return _satisfied(found)


@_requires_increment
def _package_typed_member(view, increment, spec, subject_id):
    (lineage,) = _filters(spec, FILTER_LINEAGE)
    found = [m for m in _package_members(view, increment)
             if str(view.element(m).get("@type") or "").endswith("Usage") and _in(view, m, lineage.argument)]
    if not found:
        return _violated(f"{_name(view, increment.package_id)} owns no usage in the "
                         f"{lineage.argument} lineage")
    return _satisfied(found)


@_requires_increment
def _problem_statement_stakeholder(view, increment, spec, subject_id):
    (lineage,) = _filters(spec, FILTER_LINEAGE)
    statements = [
        member for member in _package_members(view, increment, "RequirementUsage")
        if _in(view, member, PROBLEM_STATEMENT_DECLARATION)
        and _subject_typed_by_increment(view, increment, member)
    ]
    members = [m for statement in statements for m in _members(view, statement, "StakeholderMembership")]
    found = [m for m in members if _in(view, m, lineage.argument)]
    if not found:
        return _violated(f"the increment problem statement has no stakeholder member in the "
                         f"{lineage.argument} lineage", witnesses=statements)
    return _satisfied(found, witnesses=statements)


@_requires_increment
def _package_view_framed_concern(view, increment, spec, subject_id):
    concerns = set(_package_members(view, increment, "ConcernUsage"))
    framed: list[str] = []
    witnesses: list[str] = []
    for view_usage in _package_members(view, increment, "ViewUsage"):
        for viewpoint in view.index.owned_members(view_usage, "ViewpointUsage"):
            for relationship in view.index.owned_relationships(viewpoint, "FramedConcernMembership"):
                for member in reference_ids(relationship.get("memberElement")):
                    concern = view.index.declared_of(member)
                    if concern in concerns and concern not in framed:
                        framed.append(concern)
                        witnesses.append(str(relationship.get("@id")))
    if not framed:
        return _violated(f"no concern owned by {_name(view, increment.package_id)} is framed by a "
                         "viewpoint of a view owned by the same package")
    return _satisfied(framed, witnesses)


@_requires_increment
def _charter_attribute(view, increment, spec, subject_id):
    (rule,) = _filters(spec, FILTER_CHARTER_ATTRIBUTE)
    if len(increment.charters) != 1:
        return _indeterminate(MODEL_WITNESS_PREFIX + "charter declaration",
                              f"{len(increment.charters)} charter declarations; the {rule.argument} "
                              "value cannot be read")
    charter = increment.charters[0]
    values = view.index.feature_values(charter, rule.argument)
    if rule.values == ("MethodPhase",):
        try:
            phase_root = view.kernel_element("MethodPhase")
        except IdentityNotFoundError as error:
            raise _MethodSide("kernel-binding:MethodPhase", f"method side: {error}")
        literals = [leaf.value for leaf in values
                    if leaf.kind == "reference" and view.index.owner_of(leaf.value) == phase_root]
        if not literals:
            return _violated(f"the charter declares no {rule.argument} value that is a MethodPhase literal")
        return _satisfied(literals)
    texts = [str(leaf.value) for leaf in values if leaf.kind == "string" and str(leaf.value or "").strip()]
    if not texts:
        return _violated(f"the charter carries no non-empty {rule.argument} value")
    return _satisfied(texts, witnesses=[charter])


# ---------------------------------------------------------------------------
# Needs and requirements predicates
# ---------------------------------------------------------------------------


@_requires_increment
def _required_constraint(view, increment, spec, subject_id):
    found = []
    for relationship in view.index.owned_relationships(subject_id, "RequirementConstraintMembership"):
        if str(relationship.get("kind") or "requirement") != "requirement":
            continue
        found.extend(reference_ids(relationship.get("memberElement")))
    if not found:
        return _violated(f"{_name(view, subject_id)} owns no require constraint (statement)")
    return _satisfied(found)


@_requires_increment
def _stakeholder_membership(view, increment, spec, subject_id):
    (lineage,) = _filters(spec, FILTER_LINEAGE)
    members = _members(view, subject_id, "StakeholderMembership")
    found = [m for m in members if _in(view, m, lineage.argument)]
    if not found:
        return _violated(f"{_name(view, subject_id)} has no stakeholder member in the "
                         f"{lineage.argument} lineage", witnesses=members)
    return _satisfied(found, witnesses=members)


@_requires_increment
def _requirement_attribute(view, increment, spec, subject_id):
    (rule,) = _filters(spec, FILTER_LIBRARY_ATTRIBUTE)
    feature = view.index.feature(subject_id, rule.argument)
    redefined = []
    if feature is not None:
        for relationship in view.index.owned_relationships(feature, "Redefinition"):
            redefined.extend(reference_ids(relationship.get("redefinedFeature")))
    inherited = [r for r in redefined if view.index.name_of(r) == rule.argument
                 and view.index.owner_of(r) != subject_id]
    if feature is None or not inherited:
        return _violated(f"{_name(view, subject_id)} sets no {rule.argument} value "
                         f"(attribute :>> {rule.argument} = ...)")
    texts = [str(leaf.value) for leaf in view.index.feature_values(subject_id, rule.argument)
             if leaf.kind == "string" and str(leaf.value or "").strip()]
    if not texts:
        return _violated(f"{_name(view, subject_id)} {rule.argument} value is empty")
    if rule.values and not set(texts) <= set(rule.values):
        return _violated(f"{_name(view, subject_id)} {rule.argument} value {sorted(set(texts))} is not one "
                         f"of {', '.join(rule.values)}")
    return _satisfied(texts, witnesses=[feature, *inherited])


def _connection_ends(view: ModelView) -> dict[str, tuple[tuple[str, ...], str]]:
    """Connection usage -> (connected usages in end order, problem) per corpus."""

    def build() -> dict[str, tuple[tuple[str, ...], str]]:
        traversal = view.traversal
        index = view.index
        found: dict[str, tuple[tuple[str, ...], str]] = {}
        for connection in index.elements_of_type("ConnectionUsage"):
            element = index.by_id[connection]
            try:
                records = traversal._connection_end_records(element, index.by_id, index.graph)
                ends = tuple(
                    traversal._connected_usage_id(record["end_element_id"], index.graph, index.by_id)[0]
                    for record in records
                )
                found[connection] = (ends, "")
            except IdentityNotFoundError as error:
                found[connection] = ((), str(error))
        return found

    return view.index.memo("connection-ends", build)


@_requires_increment
def _typed_connection(view, increment, spec, subject_id):
    (rule,) = _filters(spec, FILTER_TYPED_CONNECTION)
    carrier_class = _class_of(view, rule.values[0])
    try:
        carriers = view.traversal.class_lineage(carrier_class, view.elements)["explicit_lineage_ids"]
    except IdentityNotFoundError as error:
        raise _MethodSide(f"kernel-binding:{carrier_class}", f"method side: {error}")
    targets: list[str] = []
    witnesses: list[str] = []
    problems: list[str] = []
    for connection, (ends, problem) in sorted(_connection_ends(view).items()):
        if not view.index.typed_by(connection) & carriers:
            continue
        if problem:
            problems.append(f"{_name(view, connection)}: {problem}")
            continue
        if subject_id not in ends:
            continue
        for end in ends:
            if end != subject_id and _in(view, end, rule.argument) and end not in targets:
                targets.append(end)
                witnesses.append(connection)
    if not targets and problems:
        return _indeterminate(MODEL_WITNESS_PREFIX + rule.values[0],
                              f"{rule.values[0]} connections cannot be read: {problems[:3]}")
    if not targets:
        return _violated(f"{_name(view, subject_id)} has no {rule.values[0]} connection to a "
                         f"{rule.argument}")
    return _satisfied(targets, witnesses)


@_requires_increment
def _framed_concern_membership(view, increment, spec, subject_id):
    found, witnesses = [], []
    for relationship in view.index.owned_relationships(subject_id, "FramedConcernMembership"):
        for member in reference_ids(relationship.get("memberElement")):
            concern = view.index.declared_of(member)
            if str(view.element(concern).get("@type")) != "ConcernUsage":
                continue
            if _members(view, concern, "StakeholderMembership") and concern not in found:
                found.append(concern)
                witnesses.append(str(relationship.get("@id")))
    if not found:
        return _violated(f"{_name(view, subject_id)} frames no concern that has a native stakeholder member")
    return _satisfied(found, witnesses)


@_requires_increment
def _subject_membership(view, increment, spec, subject_id):
    found = _members(view, subject_id, "SubjectMembership")
    if not found:
        return _violated(f"{_name(view, subject_id)} declares no subject")
    return _satisfied(found)


def _governed(view: ModelView, relation: str, subject_id: str) -> tuple[list[Any], str]:
    """Hops of one governed relation, or a method-side/model-witness problem."""
    contract = view.contract
    try:
        mapping = contract.relationship_mapping(relation)
    except Exception as error:  # noqa: BLE001 - an unmapped relation is method side
        raise _MethodSide(f"governed-relation:{relation}",
                          f"method side: governed relation {relation} has no SysML mapping ({error})")
    if mapping.strategy == "external":
        raise _MethodSide(f"external-relation:{relation}",
                          f"method side: {relation} is external data; no native relation at this revision")
    config = mapping.configuration or {}
    # Classes the strategy itself resolves through kernel bindings; a
    # missing binding is method side, not a model gap.
    classes = [mapping.domain, config.get("connection_definition"),
               config.get("source_lineage_of"), config.get("target_lineage_of")]
    for ontology_class in [str(c) for c in classes if c]:
        try:
            file_mapped = isinstance(contract.mapping(ontology_class), KernelFileMapping)
        except Exception:  # noqa: BLE001 - not a class of this contract
            file_mapped = False
        if not file_mapped:
            continue
        try:
            view.traversal.class_lineage(ontology_class, view.elements)
        except IdentityNotFoundError as error:
            raise _MethodSide(f"kernel-binding:{ontology_class}", f"method side: {error}")
    traversal = view.traversal
    before = list(getattr(traversal, "unsupported", None) or ())
    try:
        hops = traversal.traverse(relation, view.element(subject_id), view.elements)
    except IdentityNotFoundError as error:
        return [], str(error)
    added = [record for record in (getattr(traversal, "unsupported", None) or ())
             if record not in before and record.get("predicate") == relation]
    if added and not hops:
        return [], "; ".join(str(record.get("reason")) for record in added)
    return hops, ""


def _plain_need_dependencies(view: ModelView, requirement: str, need_class: str) -> int:
    count = 0
    for dependency in view.index.elements_of_type("Dependency"):
        element = view.index.by_id[dependency]
        sources = reference_ids(element.get("client")) or reference_ids(element.get("source"))
        if requirement not in sources:
            continue
        targets = reference_ids(element.get("supplier")) or reference_ids(element.get("target"))
        count += sum(1 for target in targets if view.in_lineage(target, need_class))
    return count


def _governed_relation(relation: str) -> me.Predicate:
    @_requires_increment
    def evaluate(view, increment, spec, subject_id):
        hops, problem = _governed(view, relation, subject_id)
        if problem:
            return _indeterminate(MODEL_WITNESS_PREFIX + relation,
                                  f"{relation} witnesses of {_name(view, subject_id)} cannot be read: {problem}")
        targets, witnesses = [], []
        lineages = _filters(spec, FILTER_LINEAGE)
        types = [f.argument for f in _filters(spec, me.FILTER_ELEMENT_TYPE)]
        for hop in hops:
            target = str(hop.target.get("@id"))
            candidates = [target]
            if types and str(hop.target.get("@type")) not in types:
                # A witness on a definition covers the usages typed by it.
                candidates = [usage for usage in view.index.typed_usages(target)
                              if str(view.element(usage).get("@type")) in types]
            for candidate in candidates:
                if any(not _in(view, candidate, f.argument) for f in lineages):
                    continue
                targets.append(candidate)
                witnesses.append(str(hop.api_object.get("@id")))
        if not targets:
            extra: list[str] = []
            if relation == "derivesRequirementFromNeed" and lineages:
                plain = _plain_need_dependencies(view, subject_id, _class_of(view, lineages[0].argument))
                if plain:
                    extra.append(f"{plain} plain dependency derivation(s) to needs do not count; "
                                 "only a DerivesFromNeed connection does")
            return _violated(f"{_name(view, subject_id)} has no {relation} target", extra)
        return _satisfied(targets, witnesses)

    evaluate.__name__ = f"governed_{relation}"
    return evaluate


@_requires_increment
def _any_governed_lineage(view, increment, spec, subject_id):
    (rule,) = _filters(spec, FILTER_ANY_LINEAGE)
    relations = {"ProductLineFeatureCandidate": "specifiesFeature",
                 "CommonProductLineCapability": "specifiesCommonCapability"}
    chosen = [relations.get(declaration, "") for declaration in rule.values]
    if not all(chosen):
        raise _MethodSide("governed-relation:" + ",".join(rule.values),
                          f"method side: no governed relation reaches {', '.join(rule.values)}")
    targets, witnesses, unmapped = [], [], []
    for relation in chosen:
        try:
            hops, problem = _governed(view, relation, subject_id)
        except _MethodSide as missing:
            unmapped.append(missing.marker)
            continue
        if problem:
            return _indeterminate(MODEL_WITNESS_PREFIX + relation, problem)
        for hop in hops:
            targets.append(str(hop.target.get("@id")))
            witnesses.append(str(hop.api_object.get("@id")))
    if not targets and len(unmapped) == len(chosen):
        raise _MethodSide(",".join(unmapped),
                          "method side: " + " and ".join(chosen) + " have no SysML mapping at this revision")
    if not targets:
        return _violated(f"{_name(view, subject_id)} specifies no {' or '.join(rule.values)}")
    return _satisfied(targets, witnesses)


# ---------------------------------------------------------------------------
# V&V and evidence predicates
# ---------------------------------------------------------------------------


def _verified_requirements(view: ModelView, case: str) -> tuple[list[str], list[str]]:
    """Requirements verified by a case's own or inherited objectives."""
    holders = [case, *sorted(view.index.typed_by(case))]
    targets, witnesses = [], []
    for holder in holders:
        for objective in _members(view, holder, "ObjectiveMembership"):
            for relationship in view.index.owned_relationships(objective, "RequirementVerificationMembership"):
                for member in reference_ids(relationship.get("memberElement")):
                    declared = view.index.declared_of(member)
                    if declared not in targets:
                        targets.append(declared)
                        witnesses.append(str(relationship.get("@id")))
    return targets, witnesses


@_requires_increment
def _verifies(view, increment, spec, subject_id):
    verified, witnesses = _verified_requirements(view, subject_id)
    if not verified:
        return _violated(f"{_name(view, subject_id)} objective verifies no requirement (own or inherited)")
    qualifying = verified
    for rule in _filters(spec, FILTER_POPULATION_MEMBER):
        population = set(increment.populations.get(rule.argument, ()))
        qualifying = [t for t in qualifying if t in population]
    for rule in _filters(spec, FILTER_LINEAGE):
        qualifying = [t for t in qualifying if _in(view, t, rule.argument)]
    if not qualifying:
        names = ", ".join(_name(view, t) for t in verified[:5])
        return _violated(f"{_name(view, subject_id)} verifies no {spec.target_filters[0] if spec.target_filters else 'qualifying requirement'}",
                         (f"verified: {names}",), witnesses=witnesses)
    return _satisfied(qualifying, witnesses)


@_requires_increment
def _external_evidence(view, increment, spec, subject_id):
    hops, problem = _governed(view, "hasEvidence", subject_id)
    if problem:
        return _indeterminate(MODEL_WITNESS_PREFIX + "hasEvidence", problem)
    if not hops:
        return _violated(f"{_name(view, subject_id)} has no evidence record or status")
    return _satisfied([str(h.target.get("@id")) for h in hops], [str(h.api_object.get("@id")) for h in hops])


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

GATE_PREDICATE_DEFINITIONS = (
    me.PredicateDefinition(
        "increment-identity", _increment_identity,
        _grammar((rf"(?P<d>{_IDENTIFIER}) lineage; declared short name equals the increment identifier",
                  lambda m: _f(FILTER_IDENTITY, m["d"]))),
        "declare the increment usage with its identifier as declared short name, typed by a "
        "specialization of {argument}: part <'{increment}'> <usageName> : <IncrementDefinition>;",
    ),
    me.PredicateDefinition(
        "increment-charter-declaration", _charter_declaration,
        _grammar((r"IncrementCharter lineage; increment reference resolves to the increment usage",
                  lambda m: _f(FILTER_CHARTER))),
        "add one charter declaration to {package}: part <name> : IncrementCharter {{ ref part :>> "
        "increment = <incrementUsage>; attribute :>> applicablePhases = (...); ... }}",
    ),
    me.PredicateDefinition(
        "increment-problem-statement", _problem_statement,
        _grammar((rf"(?P<d>{_IDENTIFIER}) lineage; owned by the increment package; native subject typed "
                  r"by the increment definition", lambda m: _f(FILTER_PACKAGE_REQUIREMENT, m["d"]))),
        "add to {package}: requirement <name> : {argument} {{ subject increment : <IncrementDefinition>; }}",
    ),
    me.PredicateDefinition(
        "package-typed-member", _package_typed_member, _grammar(_LINEAGE_FORM),
        "add to {package} a usage typed in the {argument} lineage: part <name> : {argument};",
    ),
    me.PredicateDefinition(
        "problem-statement-stakeholder", _problem_statement_stakeholder, _grammar(_LINEAGE_FORM),
        "add a stakeholder to the increment problem statement: stakeholder <name> : <role :> {argument}>;",
    ),
    me.PredicateDefinition(
        "package-view-framed-concern", _package_view_framed_concern,
        _grammar((r"ConcernUsage owned by the increment package; framed by a viewpoint of a view owned by "
                  r"the same package", lambda m: _f(FILTER_PACKAGE_VIEW_FRAMING))),
        "in {package}, add a view whose viewpoint frames a concern of the package: view <name> {{ "
        "viewpoint <name> : <Viewpoint> {{ frame <concern>; }} }}",
    ),
    me.PredicateDefinition(
        "charter-attribute-value", _charter_attribute,
        _grammar((r"IncrementCharter (?P<a>[a-z][A-Za-z0-9]*); non-empty String",
                  lambda m: _f(FILTER_CHARTER_ATTRIBUTE, m["a"], ("String",))),
                 (r"IncrementCharter (?P<a>[a-z][A-Za-z0-9]*); MethodPhase literal",
                  lambda m: _f(FILTER_CHARTER_ATTRIBUTE, m["a"], ("MethodPhase",)))),
        "set the charter attribute: attribute :>> {argument} = ...;",
    ),
    me.PredicateDefinition(
        "required-constraint", _required_constraint,
        _grammar((r"require constraint; framed concerns excluded", lambda m: _f(FILTER_REQUIRED_CONSTRAINT))),
        "add the statement to {subject}: require constraint statement {{ language \"English\" /* ... */ }}",
    ),
    me.PredicateDefinition(
        "stakeholder-membership", _stakeholder_membership, _grammar(_LINEAGE_FORM),
        "add to {subject}: stakeholder <name> : <role :> {argument}>;",
    ),
    me.PredicateDefinition(
        "requirement-attribute-value", _requirement_attribute,
        _grammar((r"ODE4HERA (?P<a>[a-z][A-Za-z0-9]*); non-empty String",
                  lambda m: _f(FILTER_LIBRARY_ATTRIBUTE, m["a"])),
                 (r"ODE4HERA (?P<a>[a-z][A-Za-z0-9]*); one of (?P<v>[a-z]+(?:, [a-z]+)*)",
                  lambda m: _f(FILTER_LIBRARY_ATTRIBUTE, m["a"], m["v"].split(", ")))),
        "set on {subject}: attribute :>> {argument} = \"...\";{allowed}",
    ),
    me.PredicateDefinition(
        "hasValidationScenario", _typed_connection,
        _grammar((rf"(?P<t>{_IDENTIFIER}) lineage; through a (?P<c>{_IDENTIFIER}) connection",
                  lambda m: _f(FILTER_TYPED_CONNECTION, m["t"], (m["c"],)))),
        "add a scenario and connect it to {subject}: part <scenario> : <:> {argument}>; connection "
        "<name> : <:> {carrier}> connect {subject_name} to <scenario>;",
    ),
    me.PredicateDefinition(
        "framed-concern-membership", _framed_concern_membership,
        _grammar((r"ConcernUsage with at least one native stakeholder member", lambda m: _f(FILTER_FRAMED_CONCERN))),
        "frame a stakeholder concern in {subject}: frame <concern>; (the concern declares a stakeholder)",
    ),
    me.PredicateDefinition(
        "derivesRequirementFromNeed", _governed_relation("derivesRequirementFromNeed"),
        _grammar((rf"(?P<d>{_IDENTIFIER}) lineage; through a DerivesFromNeed connection only; plain "
                  r"dependencies excluded", lambda m: _f(FILTER_LINEAGE, m["d"]))),
        "replace any plain dependency with: connection <name> : DerivesFromNeed connect <need> to "
        "{subject_name};",
    ),
    me.PredicateDefinition(
        "subject-membership", _subject_membership, me._no_filters,
        "declare exactly one subject on {subject}: subject <name> : <Definition>;",
    ),
    me.PredicateDefinition(
        "specifiesFeatureOrCommonCapability", _any_governed_lineage,
        _grammar((rf"(?P<a>{_IDENTIFIER}) or (?P<b>{_IDENTIFIER}) lineage",
                  lambda m: _f(FILTER_ANY_LINEAGE, values=(m["a"], m["b"])))),
        "trace {subject} to a feature or common capability",
    ),
    me.PredicateDefinition(
        "verifies", _verifies,
        _grammar((r"requirement usage in the increment requirements population",
                  lambda m: _f(FILTER_POPULATION_MEMBER, SELECTOR_REQUIREMENTS)), _LINEAGE_FORM),
        "add to the objective of {subject} (or its definition): verify <requirement>;",
    ),
    me.PredicateDefinition(
        "verifiedBy", _governed_relation("verifiedBy"),
        _grammar((r"(?P<t>[A-Z][A-Za-z0-9]*Usage)", lambda m: _f(me.FILTER_ELEMENT_TYPE, m["t"]))),
        "add `verify {subject_name};` to the objective of a verification case",
    ),
    me.PredicateDefinition(
        "evidence-record-or-status", _external_evidence,
        _grammar((r"evidence record referencing the verification case, or an evidence status of the case",
                  lambda m: _f(FILTER_EXTERNAL_EVIDENCE))),
        "record evidence for {subject} (evidence content is external at this revision)",
    ),
)

GATE_PREDICATES = me.DEFAULT_PREDICATES.with_definitions(*GATE_PREDICATE_DEFINITIONS)


def remedy(spec: me.ObligationSpec, *, increment: IncrementScope, view: ModelView,
           subject_id: str | None = None) -> str:
    """What to author for one gate, in model terms (filled from typed filters)."""
    try:
        definition = GATE_PREDICATES.definition(spec.predicate)
    except KeyError:
        return ""
    filters = spec.filters or GATE_PREDICATES.filters(spec)
    primary = filters[0] if filters else me.TargetFilter(kind="")
    allowed = f" (one of {', '.join(primary.values)})" if primary.kind == FILTER_LIBRARY_ATTRIBUTE and primary.values else ""
    values = {
        "argument": primary.argument,
        "carrier": primary.values[0] if primary.values else "",
        "allowed": allowed,
        "increment": increment.increment_id,
        "package": _name(view, increment.package_id) if increment.package_id else "the increment package",
        "subject": _name(view, subject_id) if subject_id else "each subject",
        "subject_name": view.index.name_of(subject_id) if subject_id else "<subject>",
    }
    try:
        return definition.remedy.format(**values)
    except (KeyError, IndexError, ValueError):
        return definition.remedy
