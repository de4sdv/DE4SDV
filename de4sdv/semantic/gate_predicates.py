"""Method-gate predicates and typed increment selectors (the MethodGate adapter).

This module adapts one representation of the method gates (a ``MethodGate``
usage per rule clause, carrying a predicate name and filter text) to the
evaluator. Relation-shaped predicates delegate to the relation checks
(:mod:`de4sdv.semantic.relation_checks`), which map a relation name to an
implementation over the model and take no gate field; here a gate's filter
text only narrows the targets its rule accepts. The other predicates check
increment framing content (identity, charter, package members, attribute
values) and belong to this gate representation. Phase rules stay model data:
which predicate a phase uses, with which filter, cardinality and
prerequisites, is declared by the gates in the model. A predicate never
branches on phase identity.

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
from .increment_scope import (
    INCREMENT_SELECTORS,
    PROBLEM_INVALID,
    SELECTOR_REQUIREMENTS,
    IncrementScope,
    ModelView,
)
from .relation_checks import (
    METHOD_SIDE_PREFIXES,
    MODEL_WITNESS_PREFIX,
    MethodSideInput,
    RelationResult,
    element_name,
    membership_members,
    plain_dependency_near_misses,
    relation_checks,
)

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


_MethodSide = MethodSideInput


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
    return _outcome("violated", codes=(me.REQUIRED_RELATION_MISSING,),
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


_name = element_name
_members = membership_members


def _relation(view: ModelView, relation: str, subject_id: str) -> RelationResult:
    """The relation check named ``relation`` for one subject (no gate fields)."""
    return relation_checks(view).check(relation, view, subject_id)


def _package_members(view: ModelView, increment: IncrementScope, *types: str) -> list[str]:
    if increment.package_id is None:
        return []
    return view.index.owned_members(increment.package_id, *types)


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
    members = _relation(view, "stakeholder", subject_id).targets
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


def _connection_relation(relation: str) -> me.Predicate:
    """A connection-carried relation; the gate filter narrows the accepted targets.

    The relation's pinned connection carrier decides which connections count;
    the filter names that carrier and the target lineage the rule accepts.
    """

    @_requires_increment
    def evaluate(view, increment, spec, subject_id):
        (rule,) = _filters(spec, FILTER_TYPED_CONNECTION)
        result = _relation(view, relation, subject_id)
        if result.problem:
            return _indeterminate(result.problem, result.detail)
        hops = [(target, witness) for target, witness in result.hops if _in(view, target, rule.argument)]
        if not hops:
            return _violated(result.absent)
        return _satisfied([t for t, _w in hops], [w for _t, w in hops])

    evaluate.__name__ = f"connection_{relation}"
    return evaluate


@_requires_increment
def _framed_concern_membership(view, increment, spec, subject_id):
    hops = [(concern, witness) for concern, witness in _relation(view, "frame", subject_id).hops
            if _members(view, concern, "StakeholderMembership")]
    if not hops:
        return _violated(f"{_name(view, subject_id)} frames no concern that has a native stakeholder member")
    return _satisfied([c for c, _w in hops], [w for _c, w in hops])


@_requires_increment
def _subject_membership(view, increment, spec, subject_id):
    found = _relation(view, "subject", subject_id).targets
    if not found:
        return _violated(f"{_name(view, subject_id)} declares no subject")
    return _satisfied(found)


def _governed_relation(relation: str) -> me.Predicate:
    @_requires_increment
    def evaluate(view, increment, spec, subject_id):
        result = _relation(view, relation, subject_id)
        if result.problem:
            return _indeterminate(result.problem, result.detail)
        targets, witnesses = [], []
        lineages = _filters(spec, FILTER_LINEAGE)
        types = [f.argument for f in _filters(spec, me.FILTER_ELEMENT_TYPE)]
        for target, witness in result.hops:
            candidates = [target]
            if types and str(view.element(target).get("@type")) not in types:
                # A witness on a definition covers the usages typed by it.
                candidates = [usage for usage in view.index.typed_usages(target)
                              if str(view.element(usage).get("@type")) in types]
            for candidate in candidates:
                if any(not _in(view, candidate, f.argument) for f in lineages):
                    continue
                targets.append(candidate)
                witnesses.append(witness)
        if not targets:
            near = plain_dependency_near_misses(view, relation, subject_id) if lineages else ()
            return _violated(result.absent, near)
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
        result = _relation(view, relation, subject_id)
        if result.method_side:
            unmapped.append(result.problem)
            continue
        if result.problem:
            return _indeterminate(result.problem, result.reason)
        for target, witness in result.hops:
            targets.append(target)
            witnesses.append(witness)
    if not targets and len(unmapped) == len(chosen):
        raise _MethodSide(",".join(unmapped),
                          "method side: " + " and ".join(chosen) + " have no SysML mapping at this revision")
    if not targets:
        return _violated(f"{_name(view, subject_id)} specifies no {' or '.join(rule.values)}")
    return _satisfied(targets, witnesses)


# ---------------------------------------------------------------------------
# V&V and evidence predicates
# ---------------------------------------------------------------------------


@_requires_increment
def _verifies(view, increment, spec, subject_id):
    result = _relation(view, "verify", subject_id)
    verified, witnesses = [t for t, _w in result.hops], [w for _t, w in result.hops]
    if not verified:
        return _violated(result.absent)
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
    result = _relation(view, "hasEvidence", subject_id)
    if result.problem:
        return _indeterminate(result.problem, result.detail if result.method_side else result.reason)
    if not result.hops:
        return _violated(f"{_name(view, subject_id)} has no evidence record or status")
    return _satisfied([t for t, _w in result.hops], [w for _t, w in result.hops])


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
        "hasValidationScenario", _connection_relation("hasValidationScenario"),
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
