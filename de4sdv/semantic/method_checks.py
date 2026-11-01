"""Method checks: a check id maps to an implementation over the model.

A method declares checks about the elements its steps produce. Each check
names, by its id, what must hold for every subject element; :func:`method_checks`
maps the id to the implementation that decides it for one subject:

- **named checks** state one rule, for example ``incrementShortName`` (the
  increment usage carries the identifier as its declared short name and is
  typed by an increment definition of its own, never by the kernel
  ``EngineeringIncrement`` alone), ``problemStatementSubject`` (the problem
  statement's native subject is typed by that definition),
  ``framedByIncrementView`` (a viewpoint of a view in the increment package
  frames a concern of that package), ``oneNativeSubject`` (exactly one subject),
  ``oneVerificationMethodKind`` (one standard verification method kind is
  recorded), ``ownedByIncrementPackage``, ``subjectIsSystemOfInterest``
  (the subject is the system of interest the charter declares, never the
  increment), ``charterExpectedArtifactsCoverContent`` (no package
  holding increment content is missing from the charter's
  ``expectedArtifacts``, the scope the checks evaluate),
  ``receivesAllocation`` (the subject is the target end of an allocation
  that grounds an end pair of the relation native allocations carry),
  ``carriedByArchitecture`` (a requirement is allocated to a function or
  named as relevant by an architecture element), ``populationMember``
  (every subject the step parameter counts satisfies it, so its gate states
  only the parameter's multiplicity, such as at least one function),
  ``signalMappingRecorded`` (a physical element that realizes a logical
  element and exchanges information items through a port has a
  system-to-software signal mapping the increment owns, with complete
  records), ``semanticSourceNamed`` (a signal mapping's records state the
  semantic source, or its port's item is VSS-typed by the bound VSS signal
  metadata), ``framedByViewpoint`` (a viewpoint of a view in a package of
  the increment frames the concern), ``contextSystemOfInterest`` (the
  operational context redefines its system of interest with the one the
  charter declares), ``storySubjectBound`` and ``storyActorsBound`` (each use
  case of the increment binds its subject to that system of interest and each
  actor to a part of the context around it), ``featureDeltaOnly`` (a
  product-line characteristic of the increment is a feature candidate or
  deferred product-line scope), ``viewpointFramesConcern`` (a view has a
  viewpoint that frames a concern) or ``exposesModelContent`` (a view, or a
  view it owns, exposes model content);
- **relation names**, for example ``derivesRequirementFromNeed``,
  ``hasValidationScenario``, ``verifiedBy`` or ``allocatedTo``: the subject
  reaches targets through that relation (see
  :mod:`de4sdv.semantic.relation_checks`).

An implementation takes the model view, the increment and one subject; it
reads no method-representation field (no selector, filter or phase text). How
many distinct targets a subject needs is the method's ``minimum``; a check may
bound the maximum itself (``oneNativeSubject``: one). A check id without an
implementation fails contract validation: unknown checks fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence

from de4sdv.sysml_api.repository import reference_ids

from . import method_evaluator as me
from de4sdv.sysml_api.errors import IdentityNotFoundError

from .increment_scope import (
    INCREMENT_ATTRIBUTE,
    INCREMENT_CLASS,
    PHASES_ATTRIBUTE,
    SCOPE_ATTRIBUTE,
    SCOPE_PROBLEM,
    SYSTEM_OF_INTEREST_ATTRIBUTE,
    IncrementScope,
    ModelView,
    applicable_phase_literals,
    declared_artifacts,
    own_increment_definitions,
    scope_closure,
)
from .relation_checks import (
    EVALUATION_INPUT_PREFIX,
    MODEL_WITNESS_PREFIX,
    SIGNAL_CARRIERS,
    SIGNAL_MAPPING,
    SIGNAL_MAPPING_DISPOSITION,
    SIGNAL_MAPPING_RECORD,
    MethodSideInput,
    allocation_classes,
    allocation_end_chains,
    allocation_ends,
    allocation_hops,
    carried_vss_paths,
    chained_feature,
    check_relation,
    class_declaration,
    connection_ends,
    element_name,
    in_class,
    kernel_lineage,
    mapping_records,
    member_features,
    membership_members,
    narrowed_features,
    native_allocation_rows,
    port_reading,
    relation_checks,
    signal_mappings,
    stated_texts,
    type_lineage,
    ungrounded_allocations,
    unreadable_allocations,
)

#: Standard verification method kinds: the SysML Systems Library
#: ``VerificationCases::VerificationMethodKind`` literals, the vocabulary the
#: method context adopts for the ODE4HERA ``verificationMethod`` attribute.
STANDARD_VERIFICATION_METHOD_KINDS = ("inspect", "analyze", "demo", "test")


# ---------------------------------------------------------------------------
# Outcomes and the increment evaluation context
# ---------------------------------------------------------------------------


@dataclass
class IncrementEvaluationContext(me.EvaluationContext):
    """Evaluation context of one increment: the model view and its scope."""

    model: ModelView | None = None
    increment: IncrementScope | None = None


def outcome(status: str, **fields: Any) -> me.PredicateOutcome:
    return me.PredicateOutcome(
        status=status,
        reason_codes=tuple(fields.get("codes", ())),
        targets=tuple(fields.get("targets", ())),
        witnesses=tuple(fields.get("witnesses", ())),
        missing=tuple(fields.get("missing", ())),
        diagnostics=tuple(fields.get("diagnostics", ())),
    )


def satisfied(targets: Iterable[str], witnesses: Iterable[str] = (), diagnostics: Sequence[str] = ()):
    targets = list(dict.fromkeys(targets))
    return outcome("satisfied", targets=targets, witnesses=list(dict.fromkeys(witnesses)) or targets,
                   diagnostics=diagnostics)


def violated(what: str, diagnostics: Sequence[str] = (), witnesses: Iterable[str] = ()):
    return outcome("violated", codes=(me.REQUIRED_RELATION_MISSING,),
                   diagnostics=(what, *diagnostics), witnesses=list(witnesses))


def indeterminate(marker: str, detail: str):
    return outcome("indeterminate", codes=(me.INPUT_UNAVAILABLE,), missing=(marker,), diagnostics=(detail,))


CheckFunction = Callable[[ModelView, IncrementScope, str], me.PredicateOutcome]


def with_increment(name: str, function: CheckFunction) -> me.Predicate:
    """The evaluator predicate of a check that reads the increment context."""

    def predicate(ctx: me.EvaluationContext, spec: me.ObligationSpec, subject_id: str) -> me.PredicateOutcome:
        view = getattr(ctx, "model", None)
        increment = getattr(ctx, "increment", None)
        if view is None or increment is None:
            return outcome("error", codes=(me.EVALUATOR_FAILURE,),
                           diagnostics=(f"check {spec.predicate!r} needs an increment evaluation context",))
        try:
            return function(view, increment, subject_id)
        except MethodSideInput as missing:
            return indeterminate(missing.marker, missing.detail)

    predicate.__name__ = f"check_{name}"
    return predicate


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def relation_holds(relation: str) -> CheckFunction:
    """The subject reaches targets through ``relation`` (a relation check)."""

    def check(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
        result = check_relation(view, relation, subject_id)
        if result.problem:
            return indeterminate(result.problem, result.detail)
        if not result.hops:
            return violated(result.absent, result.near_misses)
        return satisfied([t for t, _w in result.hops], [w for _t, w in result.hops])

    return check


def _name(view: ModelView, element: str | None) -> str:
    return element_name(view, element)


def _texts(view: ModelView, owner: str, attribute: str) -> list[str]:
    return [str(leaf.value) for leaf in view.index.feature_values(owner, attribute)
            if leaf.kind == "string" and str(leaf.value or "").strip()]


def _increment_short_name(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The usage carries the increment identifier as its declared short name and is typed by an increment
    definition of its own, never by the kernel EngineeringIncrement alone: the method's form declares the
    increment's own definition specializing the kernel definition and types the usage by it."""
    name = _name(view, subject_id)
    if str(view.element(subject_id).get("declaredShortName") or "") != increment.increment_id:
        return violated(f"{name} does not carry the increment identifier {increment.increment_id!r} as its "
                        "declared short name")
    try:
        own = own_increment_definitions(view, view.index.typed_by(subject_id))
    except IdentityNotFoundError as error:  # an unbound kernel definition is method side
        return indeterminate(f"kernel-binding:{INCREMENT_CLASS}", f"method side: {error}")
    if not own:
        return violated(f"{name} is typed by {_name(view, view.kernel_element(INCREMENT_CLASS))} itself and by no "
                        "increment definition of its own; declare the increment's own definition specializing it "
                        "and type the usage by it")
    return satisfied([subject_id])


def _charter_references_increment(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    references = [leaf.value for leaf in view.index.feature_values(subject_id, INCREMENT_ATTRIBUTE)
                  if leaf.kind == "reference"]
    if increment.usage_id is None or increment.usage_id not in references:
        return violated(f"{_name(view, subject_id)} does not reference the increment {increment.increment_id} "
                        "through its increment value")
    return satisfied([increment.usage_id], witnesses=[subject_id])


def _problem_statement_subject(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The problem statement is owned by the increment package and declares a native subject typed by the
    increment's own definition: one of the definitions typing the increment usage other than the kernel
    EngineeringIncrement itself (a usage typed by the kernel definition alone offers none)."""
    name = _name(view, subject_id)
    wanted: set[str] = set()
    if increment.definition_ids:
        try:
            wanted = set(own_increment_definitions(view, increment.definition_ids))
        except IdentityNotFoundError as error:  # an unbound kernel definition is method side
            return indeterminate(f"kernel-binding:{INCREMENT_CLASS}", f"method side: {error}")
        if not wanted:
            return violated(f"{name} has no increment definition to type its subject by: the increment usage "
                            f"{_name(view, increment.usage_id)} is typed by "
                            f"{_name(view, view.kernel_element(INCREMENT_CLASS))} itself and by no increment "
                            "definition of its own; declare the increment's own definition specializing it, and "
                            "type the usage and the problem statement's subject by it")
    subjects = [member for member in membership_members(view, subject_id, "SubjectMembership")
                if view.index.typed_by(member) & wanted]
    if increment.package_id is None or view.index.owner_of(subject_id) != increment.package_id or not subjects:
        return violated(f"{name} is not a problem statement of the increment package with a native subject typed "
                        "by the increment's own definition")
    return satisfied(subjects)


def _owned_by_increment_package(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    if increment.package_id is None or view.index.owner_of(subject_id) != increment.package_id:
        package = _name(view, increment.package_id) if increment.package_id else "the increment package"
        return violated(f"{_name(view, subject_id)} is not owned by {package}")
    return satisfied([increment.package_id], witnesses=[subject_id])


def _stakeholder_member(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    found = check_relation(view, "stakeholder", subject_id).targets
    if not found:
        return violated(f"{_name(view, subject_id)} has no native stakeholder member")
    return satisfied(found)


def _framed_by_increment_view(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """At least one concern of the increment package is framed by a viewpoint of a view of that package.

    The rule is about the package: every concern subject reports the
    package-level result (the framed concerns and their framing memberships).
    """
    framed, witnesses = [], []
    if increment.package_id is not None:
        concerns = set(view.index.owned_members(increment.package_id, "ConcernUsage"))
        for view_usage in view.index.owned_members(increment.package_id, "ViewUsage"):
            for viewpoint in view.index.owned_members(view_usage, "ViewpointUsage"):
                for relationship in view.index.owned_relationships(viewpoint, "FramedConcernMembership"):
                    for member in reference_ids(relationship.get("memberElement")):
                        concern = view.index.declared_of(member)
                        if concern in concerns and concern not in framed:
                            framed.append(concern)
                            witnesses.append(str(relationship.get("@id")))
    if not framed:
        package = _name(view, increment.package_id) if increment.package_id else "the increment package"
        return violated(f"no concern of {package} is framed by a viewpoint of a view of that package")
    return satisfied(framed, witnesses)


def _charter_text(attribute: str) -> CheckFunction:
    """Non-empty String values of a charter attribute (how many: the check's cardinality)."""

    def check(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
        texts = _texts(view, subject_id, attribute)
        if not texts:
            return violated(f"{_name(view, subject_id)} carries no non-empty {attribute} value")
        return satisfied(texts, witnesses=[subject_id])

    check.member = attribute  # type: ignore[attr-defined]  # what a remedy sets (de4sdv.semantic.remedies)
    return check


def _charter_applicable_phases(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    try:
        literals, _foreign = applicable_phase_literals(view, subject_id)
    except IdentityNotFoundError as error:  # an unbound enumeration is method side
        return indeterminate("kernel-binding:MethodPhase", f"method side: {error}")
    if not literals:
        return violated(f"{_name(view, subject_id)} declares no applicablePhases value that is a MethodPhase literal")
    return satisfied(literals, witnesses=[subject_id])


def _charter_expected_artifacts(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """Every expectedArtifacts value names exactly one top-level package."""
    packages, unresolved = declared_artifacts(view, subject_id)
    if unresolved or not packages:
        return violated(f"{_name(view, subject_id)} expectedArtifacts "
                        f"{', '.join(unresolved) if unresolved else 'are empty'}: every value must name "
                        "exactly one top-level package")
    return satisfied(packages, witnesses=[subject_id])


def _require_constraint(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    found = []
    for relationship in view.index.owned_relationships(subject_id, "RequirementConstraintMembership"):
        if str(relationship.get("kind") or "requirement") == "requirement":
            found.extend(reference_ids(relationship.get("memberElement")))
    if not found:
        return violated(f"{_name(view, subject_id)} owns no require constraint (statement)")
    return satisfied(found)


def _library_attribute(attribute: str, *, allowed: Sequence[str] = ()) -> CheckFunction:
    """Non-empty values of an inherited attribute, each from ``allowed`` when given.

    The subject's feature must redefine a feature owned by a definition in the
    subject's own type lineage (in the model: the ODE4HERA
    ``RequirementsManagement`` attribute bases, and ``RequirementCandidate`` for
    ``successCriteria``). The contract binds no library declaration, so the
    library itself is reached through that lineage, not by kernel identity. How
    many values a subject may carry is the check's cardinality (for example
    exactly one verification method kind).
    """

    def check(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
        feature = view.index.feature(subject_id, attribute)
        lineage = {general for definition in view.index.typed_by(subject_id)
                   for general in view.index.generals(definition)}
        inherited = [r for r in (view.index.redefined(feature) if feature is not None else ())
                     if view.index.owner_of(r) in lineage]
        name = _name(view, subject_id)
        if feature is None or not inherited:
            return violated(f"{name} sets no {attribute} value (attribute :>> {attribute} = ...)")
        texts = _texts(view, subject_id, attribute)
        if not texts:
            return violated(f"{name} {attribute} value is empty")
        outside = sorted({text for text in texts if allowed and text not in allowed})
        if outside:
            return violated(f"{name} {attribute} value {outside} is not one of {', '.join(allowed)}")
        return satisfied(texts, witnesses=[feature, *inherited])

    check.member = attribute  # type: ignore[attr-defined]  # what a remedy sets (de4sdv.semantic.remedies)
    check.allowed = tuple(allowed)  # type: ignore[attr-defined]
    return check


def _one_native_subject(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    found = check_relation(view, "subject", subject_id).targets
    if not found:
        return violated(f"{_name(view, subject_id)} declares no subject")
    return satisfied(found)


def _usage_reaches(view: ModelView, usage: str, usages: set[str], types: set[str]) -> bool:
    """The usage is, or narrows (subsets, redefines or references, transitively), one of ``usages``, or
    is typed (itself or through what it narrows) by one of ``types``."""
    narrowed = narrowed_features(view, usage)
    if usages & set(narrowed):
        return True
    return any(view.index.typed_by(candidate) & types for candidate in narrowed)


def _lineage_types(view: ModelView, definitions: Iterable[str]) -> set[str]:
    """The definitions and every definition specializing them."""
    found: set[str] = set()
    for definition in definitions:
        found |= view.index.specializations(definition)
    return found


def _subject_is_system_of_interest(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The subject of a need or requirement is the system of interest the charter declares, never the increment.

    A subject that is, or narrows, the increment usage or is typed by the
    increment definition (or a specialization) violates the rule whatever the
    charter declares. Otherwise the subject must be, or narrow, a usage the
    charter references in ``systemOfInterest``, or be typed by one of its
    types (or a specialization); the charter may also declare the system of
    interest by type alone. The match is type-level: another usage of the
    same definition passes too. Without that declaration the comparison is
    an open input, not a violation.
    """
    name = _name(view, subject_id)
    subjects = check_relation(view, "subject", subject_id).targets
    if not subjects:
        return violated(f"{name} declares no subject; needs and requirements take the system of interest "
                        "as subject")
    increment_usages = {increment.usage_id} if increment.usage_id else set()
    offending = [s for s in subjects
                 if _usage_reaches(view, s, increment_usages, _lineage_types(view, increment.definition_ids))]
    if offending:
        named = ", ".join(view.index.name_of(s) or s for s in offending)
        return violated(f"{name} takes the increment as its subject ({named}); the subject is the system of "
                        "interest the charter declares, never the increment")
    if not increment.system_of_interest and not increment.system_of_interest_types:
        return indeterminate(f"charter:{SYSTEM_OF_INTEREST_ATTRIBUTE}",
                             f"the charter declares no {SYSTEM_OF_INTEREST_ATTRIBUTE}; the subject of {name} "
                             "cannot be compared with it")
    declared_types = _lineage_types(view, increment.system_of_interest_types)
    matched = [s for s in subjects if _usage_reaches(view, s, set(increment.system_of_interest), declared_types)]
    if not matched:
        named = ", ".join(view.index.name_of(s) or s for s in subjects)
        wanted = ", ".join(_name(view, u) for u in (increment.system_of_interest
                                                     or increment.system_of_interest_types))
        return violated(f"{name} subject ({named}) is not the declared system of interest ({wanted})")
    return satisfied(matched, witnesses=list(increment.charters) or matched)


#: Elements named per package when the expected artifacts omit content (the diagnostics carry all).
_CONTENT_EXAMPLES = 3


def _named_holder(view: ModelView, element: str | None) -> str | None:
    """The element, or its nearest owner, that carries a declared name."""
    current, seen = element, set()
    while current and current not in seen:
        seen.add(current)
        if view.element(current).get("declaredName"):
            return current
        current = view.index.owner_of(current)
    return element


def increment_content_outside_scope(view: ModelView, increment: IncrementScope) -> dict[str, dict[str, str]]:
    """Top-level package -> {element: why} of increment content outside the charter's expectedArtifacts.

    Increment content is the increment usage itself, a requirement or need
    connected by DerivesFromNeed to an element in scope, a verification case
    verifying a requirement in scope, a requirement verified by a
    verification case in scope, an allocation from an element of the scope
    packages (at any depth), and an element referencing the increment usage
    (only the usage: a reference to another increment element is not
    content). Such content in a package the charter does not name is never
    evaluated by the checks, so it is reported here. Raises
    :class:`MethodSideInput` when the DerivesFromNeed lineage is unbound.
    """
    packages = set(increment.scope_packages)
    scope = set(increment.scope_elements)
    found: dict[str, dict[str, str]] = {}

    def note(element: str | None, why: str) -> None:
        holder = _named_holder(view, element)
        top = view.top_package(holder) if holder else None
        if holder is None or top is None or top in packages:
            return
        found.setdefault(top, {}).setdefault(holder, why)

    if increment.usage_id and increment.package_id and increment.package_id not in packages:
        note(increment.usage_id, "declares the increment")
    index = view.index
    for connection, (ends, problem) in sorted(connection_ends(view).items()):
        if problem or not in_class(view, connection, "DerivesFromNeed"):
            continue
        inside = [end for end in ends if end in scope]
        if not inside:
            continue
        for end in ends:
            if end not in scope:
                note(end, f"derives through {_name(view, connection)} with {_name(view, inside[0])}")
    for case in index.elements_of_type("VerificationCaseUsage", "VerificationCaseDefinition"):
        verified = check_relation(view, "verify", case).targets
        if case in scope:
            for target in verified:
                if target not in scope:
                    note(target, f"verified by {_name(view, case)}")
            continue
        inside = [target for target in verified if target in scope]
        if inside:
            note(case, f"verifies {_name(view, inside[0])}")
    for allocation, (ends, problem) in sorted(allocation_ends(view).items()):
        if not problem and len(ends) == 2 and view.top_package(ends[0]) in packages:
            note(allocation, f"allocates {_name(view, ends[0])}")
    if increment.usage_id:
        for relationship in index.elements_of_type("ReferenceSubsetting"):
            element = index.element(relationship)
            if increment.usage_id in reference_ids(element.get("referencedFeature")):
                for holder in reference_ids(element.get("owningRelatedElement")) + reference_ids(element.get("owner")):
                    note(holder, "references the increment")
        for expression in index.elements_of_type("FeatureReferenceExpression"):
            for relationship in index.owned_relationships(expression, "Membership"):
                if increment.usage_id in reference_ids(relationship.get("memberElement")):
                    note(expression, "references the increment")
    return found


def _expected_artifacts_cover_content(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """Every package holding increment content is named in the charter's expectedArtifacts."""
    if SCOPE_PROBLEM in increment.problems:
        return indeterminate(f"charter:{SCOPE_ATTRIBUTE}", increment.problems[SCOPE_PROBLEM][1])
    outside = increment_content_outside_scope(view, increment)
    if outside:
        details = []
        for package, elements in sorted(outside.items(), key=lambda item: _name(view, item[0])):
            shown = ", ".join(f"{_name(view, element)} ({why})" for element, why in list(elements.items())[:_CONTENT_EXAMPLES])
            more = f" and {len(elements) - _CONTENT_EXAMPLES} more" if len(elements) > _CONTENT_EXAMPLES else ""
            details.append(f"{_name(view, package)}: {shown}{more}")
        return violated(f"{_name(view, subject_id)} {SCOPE_ATTRIBUTE} omit {len(outside)} package(s) holding "
                        "increment content, which the checks never evaluate", details, witnesses=[subject_id])
    return satisfied(list(increment.scope_packages), witnesses=[subject_id])


def _verifies_increment_requirement(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The case verifies a requirement of the increment: a Requirement-lineage element of its scope."""
    result = check_relation(view, "verify", subject_id)
    scope = set(increment.scope_elements)
    hops = [(target, witness) for target, witness in result.hops
            if target in scope and in_class(view, target, "Requirement")]
    if not hops:
        verified = ", ".join(_name(view, t) for t in result.targets[:5]) or "nothing"
        return violated(f"{_name(view, subject_id)} verifies no requirement of the increment",
                        (f"verified: {verified}",), witnesses=result.witnesses)
    return satisfied([t for t, _w in hops], [w for _t, w in hops])


def _evidence_record_or_status(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    result = check_relation(view, "hasEvidence", subject_id)
    if result.problem:
        return indeterminate(result.problem, result.detail)
    if not result.hops:
        return violated(f"{_name(view, subject_id)} has no evidence record or status")
    return satisfied([t for t, _w in result.hops], [w for _t, w in result.hops])


def allocation_relation(view: ModelView) -> str | None:
    """The one relation of the served contract that native allocations carry (None: none or several)."""
    relations = sorted({name for name, _row in native_allocation_rows(view)})
    return relations[0] if len(relations) == 1 else None


def _receives_allocation(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The subject is the target end of an allocation that grounds an end pair of the relation native
    allocations carry (``allocatedTo``): a function from a requirement, a logical element from a
    function, a physical element from a logical element."""
    relation = allocation_relation(view)
    if relation is None:
        return indeterminate("governed-relation:native-allocation",
                             "method side: the served contract has not exactly one relation carried by native "
                             "allocations")
    hops, problems = allocation_hops(view, relation, subject_id, incoming=True)
    if not hops:
        if problems:
            return indeterminate(MODEL_WITNESS_PREFIX + relation, unreadable_allocations(problems))
        sources = " or ".join(class_declaration(view, c)
                              for c in allocation_classes(view, relation, subject_id, incoming=True))
        sources = sources or "source class of its end pairs"
        return violated(f"{_name(view, subject_id)} receives no {relation} allocation from "
                        f"{'an' if sources[:1] in 'AEIOUaeiou' else 'a'} {sources}")
    return satisfied([s for s, _a in hops], [a for _s, a in hops])


#: The relevance relation through which an architecture element names a requirement it carries.
RELEVANT_ARCHITECTURE = "hasRelevantArchitecture"
#: The relation phase 10 checks every in-scope requirement against.
VERIFIED_BY = "verifiedBy"
#: The named checks that read native allocations (besides the relation they carry).
ALLOCATION_CHECKS = frozenset({"receivesAllocation", "carriedByArchitecture", "signalMappingRecorded",
                               "semanticSourceNamed"})


def _carried_by_architecture(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The requirement is allocated to a function (the relation native allocations carry), or an
    architecture element names it as relevant (``hasRelevantArchitecture``: an incoming dependency
    from a part or action usage or definition, member-product lineage excluded). A requirement that is
    neither is reported with what else holds it: an allocation that grounds in no end pair, or else its
    verification (``verifiedBy``, as phase 10 reads it), which then alone covers it."""
    relation = allocation_relation(view)
    allocated, problems = allocation_hops(view, relation, subject_id) if relation else ([], [])
    if allocated:
        return satisfied([t for t, _a in allocated], [a for _t, a in allocated])
    relevant = check_relation(view, RELEVANT_ARCHITECTURE, subject_id)
    if relevant.hops:
        return satisfied(relevant.targets, relevant.witnesses)
    if relation is None:
        return indeterminate("governed-relation:native-allocation",
                             "method side: the served contract has not exactly one relation carried by native "
                             "allocations")
    if problems:
        return indeterminate(MODEL_WITNESS_PREFIX + relation, unreadable_allocations(problems))
    if relevant.problem:
        return indeterminate(relevant.problem, relevant.detail)
    name = _name(view, subject_id)
    others = [_name(view, other) for other in ungrounded_allocations(view, relation, subject_id)]
    if others:
        return violated(f"{name} is allocated to no function and named as relevant by no architecture element "
                        f"({RELEVANT_ARCHITECTURE}); its allocation(s) with {', '.join(others[:3])} ground in no "
                        f"{relation} end pair")
    verify = relation_checks(view).get(VERIFIED_BY)
    verified = verify(view, subject_id) if verify is not None else None
    if verified is not None and verified.hops:
        return violated(f"{name} is carried by no architecture element and is covered by verification only")
    if verified is None or verified.problem:
        detail = verified.detail if verified is not None else f"no {VERIFIED_BY} relation in the served contract"
        return violated(f"{name} is carried by no architecture element; whether a verification case verifies it "
                        f"cannot be read ({detail})")
    return violated(f"{name} is carried by no architecture element and has no verification case yet")


#: What a mapping record must state for its crossing: the members of the kernel record.
RECORD_STATEMENTS = ("owner", "nextAction")
#: The disposition of a record whose item crosses no software contract, and the member that says why.
NOT_APPLICABLE = "notApplicable"
REASON = "evidenceOrGap"
#: The record member that states the semantic source of an item that is no VSS-typed vehicle signal.
SEMANTIC_SOURCE = "semanticSource"


def record_gaps(view: ModelView, record: str) -> list[str]:
    """What a mapping record does not state among its disposition, owner and next action, and, when it is
    notApplicable, the reason (``evidenceOrGap``). A value still holding a remedy placeholder or only a
    to-be-determined marker states nothing (:func:`~de4sdv.semantic.relation_checks.stated_texts`)."""
    disposition = _disposition(view, record)
    missing = [] if disposition else ["disposition"]
    missing += [member for member in RECORD_STATEMENTS if not stated_texts(view, record, member)]
    if disposition == NOT_APPLICABLE and not stated_texts(view, record, REASON):
        missing.append(REASON)
    return missing


def _disposition(view: ModelView, record: str) -> str:
    """The record's disposition: the name of a literal of the kernel's mapping disposition ('' when unset).
    Raises :class:`MethodSideInput` when the disposition has no validated kernel binding."""
    enums = kernel_lineage(view, SIGNAL_MAPPING_DISPOSITION)
    literals = [leaf.value for leaf in view.index.feature_values(record, "disposition")
                if leaf.kind == "reference" and view.index.owner_of(leaf.value) in enums]
    return view.index.name_of(literals[0]) if literals else ""


def _within(view: ModelView, element: str, roots: set[str]) -> bool:
    """Whether ``element`` is one of ``roots`` or owned by one of them, at any depth."""
    current, seen = element, set()
    while current and current not in seen:
        if current in roots:
            return True
        seen.add(current)
        current = view.index.owner_of(current)
    return False


@dataclass(frozen=True)
class CrossingCoverage:
    """What ``signalMappingRecorded`` reads for one physical element."""

    #: (logical element, allocation): the logical elements it realizes (allocatedTo).
    realized: list[tuple[str, str]]
    #: Its information ports, and why its other ports cannot be read.
    ports: list[str]
    unreadable: list[str]
    #: Logical element -> (mapping, its records) that cover it.
    coverage: dict[str, list[tuple[str, tuple[str, ...]]]]
    #: Logical element -> (mapping, record or None, gaps) of the increment's mappings to a realizing element
    #: whose records are missing or incomplete.
    incomplete: dict[str, list[tuple[str, str | None, tuple[str, ...]]]]
    #: Why the other mappings from a realized logical element do not count.
    notes: list[str]
    #: The allocations that cannot be read.
    problems: list[str]


def crossing_coverage(view: ModelView, increment: IncrementScope, subject_id: str) -> CrossingCoverage:
    """For a physical element: the logical elements it realizes (allocatedTo), its information ports, and
    per realized logical element the mappings that cover it, with the notes on the mappings that do not
    count. A mapping covers a logical element when a package of the increment owns it (as the
    ``signalMappings`` parameter counts it), it is allocated from the logical element to a physical element
    of the increment that realizes it, or to a feature of one (a port, written directly or as a chain
    through the element), and each record it owns states a disposition, an owner and a next action (and,
    when notApplicable, why)."""
    from .increment_workflow import increment_architecture_elements  # the workflow reader imports this module

    relation = allocation_relation(view)
    if relation is None:
        raise MethodSideInput("governed-relation:native-allocation",
                              "method side: the served contract has not exactly one relation carried by native "
                              "allocations")
    realized, problems = allocation_hops(view, relation, subject_id, incoming=True)
    ports, unreadable = port_reading(view, subject_id)
    physical = set(increment_architecture_elements(view, increment, "PhysicalElement"))
    in_scope = set(increment.scope_elements)
    mappings, chains = signal_mappings(view), allocation_end_chains(view)
    coverage: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    incomplete: dict[str, list[tuple[str, str | None, tuple[str, ...]]]] = {}
    notes: list[str] = []
    for logical, _allocation in realized:
        realizing = {target for target, _a in allocation_hops(view, relation, logical)[0] if target in physical}
        found: list[tuple[str, tuple[str, ...]]] = []
        pending: list[tuple[str, str | None, tuple[str, ...]]] = []
        for mapping, (ends, problem) in mappings.items():
            if problem or len(ends) != 2 or ends[0] != logical:
                continue
            target_chain = chains[mapping][0][1]
            if not any(_within(view, feature, realizing) for feature in target_chain):
                notes.append(f"{_name(view, mapping)} is allocated to {_name(view, ends[1])}, in no physical element "
                             f"of the increment that realizes {_name(view, logical)}")
                continue
            if mapping not in in_scope:
                notes.append(f"{_name(view, mapping)} is owned by no package of the increment (or is nested in a "
                             "definition), so it does not count for this increment")
                continue
            records = mapping_records(view, mapping)
            if not records:
                notes.append(f"{_name(view, mapping)} owns no {class_declaration(view, SIGNAL_MAPPING_RECORD)}")
                pending.append((mapping, None, ()))
                continue
            gaps = [(record, tuple(record_gaps(view, record))) for record in records]
            if any(missing for _record, missing in gaps):
                for record, missing in gaps:
                    if missing:
                        notes.append(f"{_name(view, record)} states no {', '.join(missing)}")
                        pending.append((mapping, record, missing))
                continue
            found.append((mapping, tuple(records)))
        coverage[logical] = found
        incomplete[logical] = pending
    return CrossingCoverage(realized, ports, unreadable, coverage, incomplete, notes, problems)


def _signal_mapping_recorded(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """A crossing has a system-to-software signal mapping. The crossing: the subject, a physical element
    of the increment, realizes a logical element (allocatedTo) and has an information port (see
    :func:`~de4sdv.semantic.relation_checks.port_reading`). Each logical element it realizes is covered by
    a SystemToSoftwareSignalMappingCandidate allocation that a package of the increment owns, from it to a
    physical element of the increment that realizes it (or a port of one, directly or as a chain through
    it), whose LogicalToSoftwareSignalMappingRecords each state a disposition, an owner and a next action,
    and when notApplicable why; one mapping may cover the processes of a chain. A physical element without
    an information port, or realizing no logical element, is no crossing. Absence is not established while
    any allocation, a port of the subject or a connector cannot be read."""
    name = _name(view, subject_id)
    found = crossing_coverage(view, increment, subject_id)
    if not found.ports and not found.unreadable:
        return outcome("not-applicable", diagnostics=(f"{name} declares no port with a directed feature: no "
                                                       "crossing",))
    if not found.realized:
        if found.problems:
            return indeterminate(MODEL_WITNESS_PREFIX + "allocatedTo", unreadable_allocations(found.problems))
        return outcome("not-applicable", diagnostics=(f"{name} realizes no logical element: no crossing",))
    if not found.ports:
        return indeterminate(MODEL_WITNESS_PREFIX + "port",
                             f"{len(found.unreadable)} port reading(s) of {name} fail, so whether it exchanges an "
                             f"information item cannot be established: {'; '.join(found.unreadable[:3])}")
    uncovered = [logical for logical, covering in found.coverage.items() if not covering]
    if uncovered and found.problems:
        return indeterminate(MODEL_WITNESS_PREFIX + "allocatedTo", unreadable_allocations(found.problems))
    if uncovered:
        names = ", ".join(_name(view, logical) for logical in uncovered)
        return violated(f"{name} realizes {names} and exchanges information items through {len(found.ports)} "
                        f"port(s), but the increment owns no {class_declaration(view, SIGNAL_MAPPING)} from {names} "
                        "to a physical element of the increment that realizes it whose mapping records each state "
                        "a disposition, an owner and a next action", tuple(found.notes))
    covered = [pair for covering in found.coverage.values() for pair in covering]
    return satisfied([record for _mapping, records in covered for record in records],
                     [mapping for mapping, _records in covered])


def _semantic_source_named(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """A signal mapping names its semantic source: each record that maps an item (any disposition but
    notApplicable) states it (``semanticSource``: what the item is and why no VSS signal applies), or the
    item at the mapping's target is VSS-typed: the target is a port, or an item or attribute in one
    (written directly or as a chain), typed by a definition the bound VSS signal metadata of COVESA_VSS
    annotates (DE4SDV_VSS_Extensions declares its signals the same way; the VSS paths are reported). A
    mapping to an element states the source in its records. Whether the item is a vehicle signal is the
    author's judgment; the check reads what is declared."""
    name = _name(view, subject_id)
    ends, problem = signal_mappings(view).get(subject_id, ((), "not a signal mapping"))
    if problem or len(ends) != 2:
        return indeterminate(MODEL_WITNESS_PREFIX + SIGNAL_MAPPING,
                             f"the ends of {name} cannot be read: {problem or f'{len(ends)} ends'}")
    records = mapping_records(view, subject_id)
    mapping_items = [record for record in records if _disposition(view, record) != NOT_APPLICABLE]
    if records and not mapping_items:
        return outcome("not-applicable", diagnostics=(
            f"{', '.join(_name(view, record) for record in records)} is notApplicable: no item crosses",))
    stated = {record: stated_texts(view, record, SEMANTIC_SOURCE) for record in mapping_items}
    lacking = [record for record, texts in stated.items() if not texts]
    if mapping_items and not lacking:
        return satisfied(mapping_items, [subject_id], diagnostics=tuple(
            f"semantic source stated: {texts[0]}" for texts in stated.values()))
    target = ends[1]
    if str(view.element(target).get("@type")) not in SIGNAL_CARRIERS:
        where = (f"{name} is allocated to the element {_name(view, target)}: VSS typing is read only at a port, or "
                 "an item or attribute in one")
        if not mapping_items:
            return violated(f"{where}, and it owns no mapping record that states its semantic source")
        return violated(f"{where}, and {', '.join(_name(view, record) for record in lacking)} states no semantic "
                        "source")
    paths = carried_vss_paths(view, target)
    if paths:
        return satisfied([target], [subject_id], diagnostics=(f"VSS-typed: {', '.join(paths)}",))
    if not mapping_items:
        return violated(f"{name} carries no VSS-typed item at {_name(view, target)} and owns no mapping record "
                        "that states its semantic source")
    return violated(f"{name} carries no VSS-typed item at {_name(view, target)}, and "
                    f"{', '.join(_name(view, record) for record in lacking)} states no semantic source")


def _population_member(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """Every subject the step parameter counts satisfies this check, so a gate with it states only the
    parameter's multiplicity: an empty population below its lower bound fails, as for any gate."""
    return satisfied([subject_id])


# ---------------------------------------------------------------------------
# Concern framing (phase 1) and publication (phase 11): concerns, viewpoints, views
# ---------------------------------------------------------------------------


#: The metaclass of the views the publication step counts (``out view publishedViews``).
VIEW_KIND = "ViewUsage"
#: The model-projected class whose validated kernel identity distinguishes phase-boundary concerns.
BOUNDARY_CONCERN_CLASS = "IncrementBoundaryConcern"


def _non_boundary_concern_present(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """At least one package-owned concern in scope is outside the canonical boundary-concern lineage.

    Like the framing-package existence check, every subject reports the same
    scope-level presence result. The other gates still judge every concern's
    native stakeholder and frame, including the boundary concerns. No name,
    phase marker or second concern/reference list determines membership.
    Resolving the excluded lineage first is essential: an unavailable kernel
    identity is method side, never evidence that every concern is non-boundary.
    """
    boundary = kernel_lineage(view, BOUNDARY_CONCERN_CLASS)
    concerns, unreadable = [], []
    for element in increment.scope_elements:
        if view.element(element).get("@type") != "ConcernUsage":
            continue
        # A concern keeps the types of features it subsets, redefines or
        # references, even when the serializer writes no typing of its own.
        features = narrowed_features(view, element)
        lineage = {definition for feature in features for definition in type_lineage(view, feature)}
        if boundary.intersection(lineage):
            continue
        missing = [target for target in (*features, *sorted(lineage)) if not view.element(target)]
        if missing:
            unreadable.append(f"{_name(view, element)} has unavailable narrowed features or type ancestors: "
                              + ", ".join(missing))
        else:
            concerns.append(element)
    if concerns:
        return satisfied(concerns)
    if unreadable:
        return indeterminate(EVALUATION_INPUT_PREFIX + "concern-lineage",
                             "non-boundary membership cannot be established: " + "; ".join(unreadable))
    return violated("the increment has no concern outside the canonical increment-boundary concern "
                    "lineage; declare a concern of its engineering scope, not another boundary specialization")


def increment_views(view: ModelView, increment: IncrementScope) -> list[str]:
    """The views the increment's packages own (nested packages included): the population of the
    publication step's ``publishedViews``, and the views whose viewpoints frame the concerns of phase 1.
    A view owned by a part or by another view (a matrix view's row view) is none of them."""
    return [element for element in increment.scope_elements if str(view.element(element).get("@type")) == VIEW_KIND]


def view_viewpoints(view: ModelView, subject_id: str) -> list[str]:
    """The viewpoint usages of a view: its own, then those of the view definitions it is typed by."""
    found: list[str] = []
    for holder in (subject_id, *type_lineage(view, subject_id)):
        found.extend(viewpoint for viewpoint in view.index.owned_members(holder, "ViewpointUsage")
                     if viewpoint not in found)
    return found


def viewpoint_frames(view: ModelView, viewpoint: str) -> list[tuple[str, str]]:
    """(concern, framing membership) for each concern a viewpoint usage frames: its own frames, then those
    of the viewpoint definitions it is typed by, which it inherits. A frame's member is a shadow of the
    declared concern (``declared_of``)."""
    found: list[tuple[str, str]] = []
    for holder in (viewpoint, *type_lineage(view, viewpoint)):
        for relationship in view.index.owned_relationships(holder, "FramedConcernMembership"):
            for member in reference_ids(relationship.get("memberElement")):
                pair = (view.index.declared_of(member), str(relationship.get("@id")))
                if pair not in found:
                    found.append(pair)
    return found


def framing_views(view: ModelView, increment: IncrementScope) -> Mapping[str, tuple[tuple[str, str], ...]]:
    """Concern -> ((view, framing membership), ...): the concerns that a viewpoint of a view frames
    (:func:`view_viewpoints`, :func:`viewpoint_frames`), for the views the increment's packages own
    (:func:`increment_views`). Built once per corpus and package set."""
    packages = tuple(increment.scope_packages)

    def build() -> Mapping[str, tuple[tuple[str, str], ...]]:
        found: dict[str, list[tuple[str, str]]] = {}
        for element in increment_views(view, increment):
            for viewpoint in view_viewpoints(view, element):
                for concern, membership in viewpoint_frames(view, viewpoint):
                    bucket = found.setdefault(concern, [])
                    if (element, membership) not in bucket:
                        bucket.append((element, membership))
        return MappingProxyType({concern: tuple(pairs) for concern, pairs in found.items()})

    return view.index.memo(("framing-views", packages), build)


def _frames_elsewhere(view: ModelView, concern: str) -> list[str]:
    """Why the other frames of ``concern`` do not count: a frame owned by no viewpoint (a need or a
    requirement that frames it), by a viewpoint definition no viewpoint of a view of the increment is typed
    by, or by a viewpoint of another view."""
    index = view.index
    notes: list[str] = []
    for relationship in index.elements_of_type("FramedConcernMembership"):
        element = index.element(relationship)
        if not any(index.declared_of(member) == concern for member in reference_ids(element.get("memberElement"))):
            continue
        holder = (reference_ids(element.get("owningRelatedElement")) or [None])[0]
        if holder is None:
            continue
        kind = str(index.element(holder).get("@type"))
        if kind == "ViewpointDefinition":
            notes.append(f"the viewpoint definition {_name(view, holder)} frames it, but no viewpoint of a view of "
                         "the increment is typed by it")
        elif kind != "ViewpointUsage":
            notes.append(f"{_name(view, holder)} frames it but is no viewpoint; only a viewpoint, or the viewpoint "
                         "definition it is typed by, frames a concern for a view")
        else:
            notes.append(f"{_name(view, holder)} frames it but is no viewpoint of a view of the increment")
    return notes


def _framed_by_viewpoint(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """A viewpoint of a view of the increment (:func:`increment_views`) frames the concern: the viewpoint
    usage, or a viewpoint definition it is typed by."""
    framing = framing_views(view, increment).get(subject_id, ())
    if framing:
        return satisfied([found for found, _membership in framing], [membership for _view, membership in framing])
    return violated(f"{_name(view, subject_id)} is framed by no viewpoint of a view of the increment",
                    _frames_elsewhere(view, subject_id))


def _viewpoint_frames_concern(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The view has a viewpoint, of its own or of its definition, that frames a concern, by its own frame or
    by a frame of the viewpoint definition it is typed by."""
    name = _name(view, subject_id)
    viewpoints = view_viewpoints(view, subject_id)
    if not viewpoints:
        return violated(f"{name} has no viewpoint, so no concern governs it")
    concerns, witnesses = [], []
    for viewpoint in viewpoints:
        for concern, membership in viewpoint_frames(view, viewpoint):
            if concern not in concerns:
                concerns.append(concern)
                witnesses.append(membership)
    if not concerns:
        return violated(f"{name}'s viewpoint {', '.join(_name(view, v) for v in viewpoints)} frames no concern")
    return satisfied(concerns, witnesses)


#: The relationships through which a view exposes model content.
EXPOSE_RELATIONSHIPS = ("MembershipExpose", "NamespaceExpose")


def owned_views(view: ModelView, subject_id: str) -> list[str]:
    """The view and the views it owns at any depth (a table or matrix view's row, column and cell views)."""
    found, frontier = [], [subject_id]
    while frontier:
        current = frontier.pop(0)
        if current in found:
            continue
        found.append(current)
        frontier.extend(view.index.owned_members(current, "ViewUsage"))
    return found


def _exposes_model_content(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The view, or a view it owns at any depth, exposes model content (an ``expose`` of a member or of a
    namespace). The exposed element is the target; an expose whose element is outside the revision counts
    as itself."""
    index = view.index
    targets, witnesses = [], []
    for holder in owned_views(view, subject_id):
        for relationship in index.owned_relationships(holder, *EXPOSE_RELATIONSHIPS):
            exposed = [member for membership in reference_ids(relationship.get("importedMembership"))
                       for member in reference_ids(index.element(membership).get("memberElement"))]
            exposed += reference_ids(relationship.get("importedNamespace"))
            target = next((found for found in exposed if found in index.by_id), str(relationship.get("@id")))
            if target not in targets:
                targets.append(target)
                witnesses.append(str(relationship.get("@id")))
    if not targets:
        return violated(f"{_name(view, subject_id)} exposes no model content, nor does a view it owns")
    return satisfied(targets, witnesses)


# ---------------------------------------------------------------------------
# Operational context and story (phase 2)
# ---------------------------------------------------------------------------

#: The feature of a context definition that holds its system of interest (SystemContext::systemOfInterest),
#: selected by member name on the definition the subject is typed by, as the charter's are.
CONTEXT_SYSTEM_OF_INTEREST = "systemOfInterest"


def context_system_of_interest(view: ModelView, context: str) -> tuple[str | None, list[str]]:
    """(the systemOfInterest feature the context's nearest definition declares, the features of the
    context or of its definitions that narrow it, at any depth). The first is None when no definition
    typing the context declares one."""
    declared = next((feature for general in type_lineage(view, context)
                     if (feature := view.index.feature(general, CONTEXT_SYSTEM_OF_INTEREST)) is not None), None)
    if declared is None:
        return None, []
    systems = [feature for feature in member_features(view, context)
               if feature != declared and declared in narrowed_features(view, feature)]
    return declared, systems


def bound_targets(view: ModelView, feature: str) -> tuple[list[str], list[str]]:
    """(the usages a feature's own value references, ``= <usage>``, a chain read as its last feature;
    why a referenced value cannot be read)."""
    targets, problems = [], []
    for leaf in view.index.value_leaves(feature):
        if leaf.kind != "reference":
            continue
        try:
            target = chained_feature(view, str(leaf.value))
        except IdentityNotFoundError as error:
            problems.append(f"{_name(view, feature)}: {error}")
            continue
        if target in view.index.by_id and target not in targets:
            targets.append(target)
    return targets, problems


def _system_of_interest_declared(increment: IncrementScope) -> bool:
    return bool(increment.system_of_interest or increment.system_of_interest_types)


def reaches_system_of_interest(view: ModelView, increment: IncrementScope, usage: str) -> bool:
    """The usage is, narrows or is bound to a usage the charter declares as system of interest, or is
    typed (itself or through what it narrows) by its definition or a specialization."""
    usages = set(increment.system_of_interest)
    types = _lineage_types(view, increment.system_of_interest_types)
    candidates = [usage, *bound_targets(view, usage)[0]]
    return any(_usage_reaches(view, candidate, usages, types) for candidate in candidates)


def _undeclared_system_of_interest(name: str) -> me.PredicateOutcome:
    return indeterminate(f"charter:{SYSTEM_OF_INTEREST_ATTRIBUTE}",
                         f"the charter declares no {SYSTEM_OF_INTEREST_ATTRIBUTE}; the system of interest of {name} "
                         "cannot be compared with it")


def _context_system_of_interest(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The operational context redefines its systemOfInterest with the system of interest the charter
    declares: a feature of the context that narrows the systemOfInterest its definition declares is, narrows,
    or is bound to the declared usage, or is typed by its definition or a specialization."""
    name = _name(view, subject_id)
    if not _system_of_interest_declared(increment):
        return _undeclared_system_of_interest(name)
    declared, systems = context_system_of_interest(view, subject_id)
    if declared is None:
        return indeterminate(MODEL_WITNESS_PREFIX + CONTEXT_SYSTEM_OF_INTEREST,
                             f"no definition typing {name} declares a {CONTEXT_SYSTEM_OF_INTEREST} feature")
    if not systems:
        return violated(f"{name} does not redefine its {CONTEXT_SYSTEM_OF_INTEREST} ({_name(view, declared)})")
    matched = [system for system in systems if reaches_system_of_interest(view, increment, system)]
    if not matched:
        wanted = ", ".join(_name(view, u) for u in (increment.system_of_interest or increment.system_of_interest_types))
        return violated(f"{name}'s system of interest {', '.join(_name(view, s) for s in systems)} is not the "
                        f"system of interest the charter declares ({wanted})")
    return satisfied(matched, witnesses=list(increment.charters) or matched)


def increment_use_cases(view: ModelView, increment: IncrementScope) -> list[str]:
    """The use case usages the increment's packages own at any depth, also in the context or another part:
    the story. An ``include use case`` is no use case of the story: its metaclass is IncludeUseCaseUsage,
    and it references the use case it includes."""
    return [element for element in scope_closure(view, increment)
            if str(view.element(element).get("@type")) == "UseCaseUsage"]


def redefined_parameters(view: ModelView, parameter: str) -> list[str]:
    """``parameter`` and the parameters it stands for, transitively: those it subsets, redefines or
    references, and those it redefines by the language rule. The language makes an owned parameter of a
    use case redefine a parameter of its definition without a declared ``:>>`` (``actor reviewer = ...;``
    in a use case whose definition declares ``actor reviewer``); the serializer writes that Redefinition
    as implied, and only implied Redefinitions are read here, no implied subsetting."""
    found: list[str] = []
    frontier = [parameter]
    while frontier:
        current = frontier.pop(0)
        if current in found:
            continue
        found.append(current)
        frontier.extend(narrowed_features(view, current)[1:])
        for relationship in view.index.owned_relationships(current, "Redefinition"):
            if relationship.get("isImplied"):
                frontier.extend(reference_ids(relationship.get("redefinedFeature")))
    return found


def use_case_parameters(view: ModelView, use_case: str, membership: str) -> list[str]:
    """The use case's parameters of one membership kind (``SubjectMembership``, ``ActorMembership``): its
    own, then those of its definitions (nearest first) that none of the ones before redefines
    (:func:`redefined_parameters`). A use case has one subject: its own, else its nearest definition's."""
    found = list(membership_members(view, use_case, membership))
    for definition in type_lineage(view, use_case):
        if membership == "SubjectMembership" and found:
            break
        narrowed = {target for parameter in found for target in redefined_parameters(view, parameter)}
        found.extend(parameter for parameter in membership_members(view, definition, membership)
                     if parameter not in narrowed and parameter not in found)
    return found


def _owned_within(view: ModelView, element: str, roots: set[str]) -> bool:
    """Whether one of ``roots`` owns ``element`` at any depth (``element`` itself excluded)."""
    current, seen = view.index.owner_of(element), {element}
    while current and current not in seen:
        if current in roots:
            return True
        seen.add(current)
        current = view.index.owner_of(current)
    return False


def _context_systems(view: ModelView, increment: IncrementScope, context: str) -> tuple[list[str], me.PredicateOutcome | None]:
    """The context's system-of-interest features, or the outcome when the story cannot be judged: no use
    case (not applicable), or a context that declares no system of interest to bind to."""
    name = _name(view, context)
    if not increment_use_cases(view, increment):
        return [], outcome("not-applicable", diagnostics=(f"the increment's packages own no use case at any depth, "
                                                          f"so {name} has no story to bind",))
    declared, systems = context_system_of_interest(view, context)
    if declared is None:
        return [], indeterminate(MODEL_WITNESS_PREFIX + CONTEXT_SYSTEM_OF_INTEREST,
                                 f"no definition typing {name} declares a {CONTEXT_SYSTEM_OF_INTEREST} feature")
    if not systems:
        return [], violated(f"{name} does not redefine its {CONTEXT_SYSTEM_OF_INTEREST}, so no use case can bind "
                            "its subject to it")
    return systems, None


def story_subject_problems(view: ModelView, increment: IncrementScope, context: str) -> list[tuple[str, str]]:
    """(use case, what is wrong) for each use case of the increment whose subject is not bound to the
    context's system of interest (a usage that is or narrows one of its system-of-interest features)."""
    systems = set(context_system_of_interest(view, context)[1])
    problems: list[tuple[str, str]] = []
    for use_case in increment_use_cases(view, increment):
        subjects = use_case_parameters(view, use_case, "SubjectMembership")
        if not subjects:
            problems.append((use_case, "declares no subject"))
            continue
        targets, unreadable = bound_targets(view, subjects[0])
        if not targets:
            problems.append((use_case, f"binds its subject {_name(view, subjects[0])} to no usage"
                             + (f" that can be read ({'; '.join(unreadable)})" if unreadable else "")))
        elif not any(systems & set(narrowed_features(view, target)) for target in targets):
            problems.append((use_case, f"binds its subject to {', '.join(_name(view, t) for t in targets)}, not to "
                             f"the system of interest of {_name(view, context)}"))
    return problems


def _story_subject_bound(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """Each use case of the increment binds its subject (``subject <name> = <usage>;``) to the operational
    context's system of interest. A use case has one subject, its own or its definition's."""
    systems, early = _context_systems(view, increment, subject_id)
    if early is not None:
        return early
    problems = story_subject_problems(view, increment, subject_id)
    if problems:
        return violated(f"{len(problems)} use case(s) of the increment do not bind their subject to the system of "
                        f"interest of {_name(view, subject_id)}",
                        [f"{_name(view, use_case)} {why}" for use_case, why in problems])
    return satisfied(increment_use_cases(view, increment), systems)


def context_part_owners(view: ModelView, context: str, declared: str | None) -> set[str]:
    """What may own a part around the system of interest: the context usage and the definitions it is typed
    by, never the definition that first declares ``systemOfInterest`` (the kernel's SystemContext) or what
    that definition specializes. Their features (``SystemContext::actors``) are generic slots, no part of
    this context. The first declaration is the systemOfInterest feature that narrows no other feature."""
    generic: set[str] = set()
    if declared is not None:
        for feature in narrowed_features(view, declared):
            owner = view.index.owner_of(feature)
            if owner and len(narrowed_features(view, feature)) == 1:
                generic.update(view.index.generals(owner))
    return {context, *type_lineage(view, context)} - generic


def story_actor_problems(view: ModelView, increment: IncrementScope, context: str) -> list[tuple[str, str, str]]:
    """(use case, actor, what is wrong) for each actor of each use case of the increment that is not bound
    to a part the context owns at any depth, around its system of interest: the part is not one of the
    context's system-of-interest features, and none of them owns it."""
    declared, found = context_system_of_interest(view, context)
    systems = {*found, *([declared] if declared else [])}  # the system of interest, never a part around it
    roots = context_part_owners(view, context, declared)
    problems: list[tuple[str, str, str]] = []
    for use_case in increment_use_cases(view, increment):
        for actor in use_case_parameters(view, use_case, "ActorMembership"):
            targets, unreadable = bound_targets(view, actor)
            if not targets:
                problems.append((use_case, actor, "is bound to no usage"
                                 + (f" that can be read ({'; '.join(unreadable)})" if unreadable else "")))
                continue
            around = [target for target in targets if _owned_within(view, target, roots)
                      and not systems & set(narrowed_features(view, target))
                      and not _owned_within(view, target, systems)]
            if not around:
                problems.append((use_case, actor, f"is bound to {', '.join(_name(view, t) for t in targets)}, no "
                                 f"part of {_name(view, context)} around its system of interest"))
    return problems


def _story_actors_bound(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """Each actor of each use case of the increment is bound (``actor <name> = <part>;``) to a part the
    operational context owns at any depth, around its system of interest. A use case's actors are its own
    and those of its definitions that no own actor redefines."""
    _systems, early = _context_systems(view, increment, subject_id)
    if early is not None:
        return early
    actors = [(use_case, actor) for use_case in increment_use_cases(view, increment)
              for actor in use_case_parameters(view, use_case, "ActorMembership")]
    if not actors:
        return outcome("not-applicable", diagnostics=("no use case of the increment declares an actor",))
    problems = story_actor_problems(view, increment, subject_id)
    if problems:
        return violated(f"{len(problems)} actor(s) of the increment's use cases are not bound to a part of "
                        f"{_name(view, subject_id)} around its system of interest",
                        [f"{_name(view, use_case)}: actor {view.index.name_of(actor) or actor} {why}"
                         for use_case, actor, why in problems])
    return satisfied([actor for _use_case, actor in actors])


# ---------------------------------------------------------------------------
# Capability classification (phase 3)
# ---------------------------------------------------------------------------

#: The kernel classes a phase-3 record may be: the feature-model delta, and deferred product-line scope.
FEATURE_CLASS = "Feature"
DEFERRED_SCOPE_CLASS = "DeferredProductLineScope"
COMMON_CAPABILITY_CLASS = "CommonCapability"


def _feature_delta_only(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """A product-line characteristic the increment records is a feature candidate (the feature-model
    delta) or product-line scope it defers (a gap among it). A common-capability record is none: core
    elements are common by default and get no record. Kernel lineage through validated bindings; an
    unbound class is method side."""
    name = _name(view, subject_id)
    if in_class(view, subject_id, FEATURE_CLASS):
        return satisfied([subject_id])
    if in_class(view, subject_id, DEFERRED_SCOPE_CLASS):
        return satisfied([subject_id], diagnostics=(f"{name} records deferred product-line scope",))
    if in_class(view, subject_id, COMMON_CAPABILITY_CLASS):
        return violated(f"{name} records a common capability; core elements are common by default and get no "
                        "record, so it is no feature-model delta")
    types = ", ".join(_name(view, t) for t in sorted(view.index.typed_by(subject_id))) or "no type"
    return violated(f"{name} ({types}) is neither a feature candidate nor deferred product-line scope, so it is no "
                    "feature-model delta")


#: The member each of these checks reads, which a remedy sets (de4sdv.semantic.remedies).
_charter_references_increment.member = INCREMENT_ATTRIBUTE  # type: ignore[attr-defined]
_charter_applicable_phases.member = PHASES_ATTRIBUTE  # type: ignore[attr-defined]
_charter_expected_artifacts.member = SCOPE_ATTRIBUTE  # type: ignore[attr-defined]
# ---------------------------------------------------------------------------
# Variability and configuration (phase 9)
# ---------------------------------------------------------------------------

#: The derived relationship whose derivation rule the phase-9 check applies (vocabulary role in the kernel).
CONFIGURED_BY = "configuredBy"
#: What an evaluation lacks to derive it: the source documents and external references of the export (an
#: evaluation over an API revision binding that records no export documents has neither), or a validated
#: kernel binding index. Only a change to the evaluation supplies them, so they are method side
#: (``METHOD_SIDE_PREFIXES``), never authoring work.
EXPORT_DOCUMENTS = EVALUATION_INPUT_PREFIX + "export-documents"
KERNEL_BINDING_INDEX = EVALUATION_INPUT_PREFIX + "kernel-binding-index"
#: The memo key of the derivation. Its value holds only for the inputs :func:`configuration_inputs` names.
CONFIGURATION_MEMO = "configuration-part-definitions"


def configuration_inputs(view: ModelView) -> tuple[Any, ...]:
    """What the derivation of the configurations reads besides the corpus: the view's source documents,
    its external references and its kernel binding index. Two views over one element list share their
    index, so the derived value is bound to these objects."""
    return (view.sources, view.external_references, view.traversal.kernel_bindings)


def configuration_part_definitions(
    view: ModelView,
) -> tuple[Mapping[str, tuple[str, ...]], str | None, str | None]:
    """(generated part definition -> the feature configurations whose product-model projection it is; the
    marker of what keeps them from being read, or None; why, or None). The configurations and the
    projections come from the derivation of the member products
    (``applies_to_member_product.configuration_projections``): a configuration by the pinned PLEML
    library, its projection by its ProductModelProjectionName annotation, and the part definition by
    validated identity (metatype, name, generated document and owner), never by the name alone. The
    derivation needs the source documents and the external references of the export, and a kernel binding
    index. An export view has them; over the API they come from the export documents that the revision
    binding records. Without them the marker is method side (``evaluation-input:``). A refused derivation
    is a model witness that cannot be read. Built once per corpus and inputs."""
    if not view.sources or view.external_references is None:
        return MappingProxyType({}), EXPORT_DOCUMENTS, (
            "the derivation of the feature configurations needs the source documents and the external "
            "references of the export, and this evaluation has neither (an evaluation over an API revision "
            "binding that records no export documents)")
    if view.traversal.kernel_bindings is None:
        return MappingProxyType({}), KERNEL_BINDING_INDEX, "this evaluation has no validated kernel binding index"

    def build() -> tuple[Mapping[str, tuple[str, ...]], str | None]:
        from de4sdv.sysml_api.product_line_scope import validate_scope_elements

        from .applies_to_member_product import MemberProductError, configuration_projections
        from .pleml_configuration import PlemlShapeError

        bindings = view.traversal.kernel_bindings
        try:
            rows = configuration_projections(
                view.elements, view.sources,
                kernel_bindings={binding.ontology_class: binding.element_id for binding in bindings.bindings},
                external_references=view.external_references,
                governed_scope=validate_scope_elements(view.elements, view.sources))
        except (MemberProductError, PlemlShapeError, IdentityNotFoundError, ValueError) as error:
            return MappingProxyType({}), f"the feature configurations cannot be read: {error}"
        found: dict[str, list[str]] = {}
        for row in rows:
            if row["part_definition"]:
                found.setdefault(str(row["part_definition"]), []).append(str(row["element_id"]))
        return MappingProxyType({definition: tuple(found[definition]) for definition in found}), None

    projections, problem = view.index.memo_bound(CONFIGURATION_MEMO, configuration_inputs(view), build)
    return projections, (MODEL_WITNESS_PREFIX + CONFIGURED_BY if problem else None), problem


def _direct_redefinitions(view: ModelView, feature: str) -> list[str]:
    """The features ``feature`` redefines directly, declared or by the language rule (an implied
    Redefinition)."""
    return [target for relationship in view.index.owned_relationships(feature, "Redefinition")
            for target in reference_ids(relationship.get("redefinedFeature"))]


def _redefined_features(view: ModelView, feature: str) -> set[str]:
    """The features ``feature`` redefines, declared or by the language rule, transitively; subsetting
    replaces nothing."""
    found: set[str] = set()
    frontier = [feature]
    while frontier:
        for target in _direct_redefinitions(view, frontier.pop()):
            if target not in found:
                found.add(target)
                frontier.append(target)
    return found


def effective_part_usages(view: ModelView, product: str) -> list[str]:
    """The effective part usages of a configured product: its own part usages, then those of the definitions
    it is typed by and that they specialize (nearest first), less the inherited usages that a nearer usage
    redefines."""
    found: list[str] = []
    redefined: set[str] = set()
    for holder in (product, *type_lineage(view, product)):
        for usage in view.index.owned_members(holder, "PartUsage"):
            if usage not in found and usage not in redefined:
                found.append(usage)
                redefined.update(_redefined_features(view, usage))
    return [usage for usage in found if usage not in redefined]


def effective_types(view: ModelView, usage: str, _seen: set[str] | None = None) -> set[str]:
    """The definitions that type a usage for the derivation. A usage without a type of its own keeps the
    effective types of the features it redefines, transitively: the serializer writes no typing for it. A
    usage with its own types keeps those, and also the types it redefines when both fall in projection
    lineages: a redefinition into another configuration's projection then counts both configurations,
    as the redefining usage keeps the redefined type (a specialization is configured by the same
    configuration). A type of its own outside every projection hides the projection it redefines."""
    seen = set() if _seen is None else _seen
    if usage in seen:
        return set()
    seen.add(usage)
    own = set(view.index.typed_by(usage))
    inherited: set[str] = set()
    for redefined in _direct_redefinitions(view, usage):
        inherited |= effective_types(view, redefined, seen)
    if not own:
        return inherited
    projections, _marker, _problem = configuration_part_definitions(view)
    if (inherited and _configurations_of_types(view, projections, own)
            and _configurations_of_types(view, projections, inherited)):
        return own | inherited
    return own


def _configurations_of_types(view: ModelView, projections: Mapping[str, tuple[str, ...]],
                             types: Iterable[str]) -> list[str]:
    """The configurations whose projection part definition each type is, or specializes. A general of a
    projection part definition, such as its owner, never counts."""
    found: list[str] = []
    for definition, configurations in projections.items():
        lineage = view.index.specializations(definition)
        if any(typed in lineage for typed in types):
            found.extend(configuration for configuration in configurations if configuration not in found)
    return found


def configured_by(view: ModelView, product: str) -> tuple[list[str], list[str]]:
    """(the feature configurations that configure a configured product, the effective part usages through
    which they do): a configuration configures it when one of its effective part usages is typed
    (:func:`effective_types`) by the part definition of that configuration's product-model projection, or
    by a specialization of it."""
    projections, _marker, _problem = configuration_part_definitions(view)
    configurations: list[str] = []
    usages: list[str] = []
    for usage in effective_part_usages(view, product):
        for configuration in _configurations_of_types(view, projections, sorted(effective_types(view, usage))):
            if configuration not in configurations:
                configurations.append(configuration)
                usages.append(usage)
    return configurations, usages


def _nearest_typed_link(view: ModelView, usage: str) -> str | None:
    """The nearest link of a redefinition chain that has a type of its own: the usage itself, else the
    nearest feature it redefines (breadth first)."""
    seen: set[str] = set()
    frontier = [usage]
    while frontier:
        current = frontier.pop(0)
        if current in seen:
            continue
        seen.add(current)
        if view.index.typed_by(current):
            return current
        frontier.extend(_direct_redefinitions(view, current))
    return None


def projection_redefinitions(view: ModelView, product: str) -> list[tuple[str, str]]:
    """(the link that hides a projection, the redefined feature typed by it) for each effective part usage
    of a configured product that no configuration types: the nearest link of its redefinition chain with
    a type of its own outside every projection, and a projection-typed feature that link redefines."""
    projections, _marker, _problem = configuration_part_definitions(view)
    found = []
    for usage in effective_part_usages(view, product):
        if _configurations_of_types(view, projections, effective_types(view, usage)):
            continue
        link = _nearest_typed_link(view, usage)
        if link is None:
            continue
        for redefined in sorted(_redefined_features(view, link)):
            if _configurations_of_types(view, projections, effective_types(view, redefined)):
                found.append((link, redefined))
                break
    return found


def _configured_by_one_configuration(view: ModelView, increment: IncrementScope,
                                     subject_id: str) -> me.PredicateOutcome:
    """Exactly one feature configuration configures the configured product (the derivation rule of
    configuredBy): one of its effective part usages, its own or inherited and not redefined, is typed by the
    part definition of that configuration's product-model projection or by a specialization of it. A
    redefining usage without a type of its own keeps the type it redefines. A specialization that adds
    System 2 instrumentation is configured through what it inherits; no member follows from it. Without
    the export's documents (over an API revision binding that records none) the derivation is method side,
    never authoring work."""
    name = _name(view, subject_id)
    _projections, marker, problem = configuration_part_definitions(view)
    if marker is not None:
        return indeterminate(marker, f"{name}: {problem}")
    configurations, usages = configured_by(view, subject_id)
    if len(configurations) == 1:
        return satisfied(configurations, usages)
    if not configurations:
        hidden = [f"{_name(view, usage)} redefines {_name(view, redefined)} with a type that is no projection's"
                  for usage, redefined in projection_redefinitions(view, subject_id)]
        return violated(f"{name} is configured by no feature configuration: none of its part usages, its own "
                        "or inherited, is typed by the part definition of a configuration's product-model "
                        "projection, or by a specialization of it", hidden)
    return violated(f"{name} is configured by {len(configurations)} feature configurations "
                    f"({', '.join(_name(view, c) for c in configurations)}); exactly one configures a configured "
                    "product", [f"{_name(view, c)} through {_name(view, u)}" for c, u in zip(configurations, usages)])


# ---------------------------------------------------------------------------
# Baseline decision and open gaps (phase 12)
# ---------------------------------------------------------------------------

#: The kernel enumeration of a disposition (accepted, deferred, invalidated), the feature that holds it, and
#: the kernel classes whose ``disposition`` a record redefines.
LIFECYCLE_DISPOSITION = "LifecycleDisposition"
DISPOSITION_FEATURE = "disposition"
DISPOSITION_HOLDERS = ("IncrementBaselineDecision", "Gap")


def lifecycle_disposition(view: ModelView, subject_id: str) -> str | None:
    """The literal of the kernel's LifecycleDisposition that the subject's own disposition states, or None.
    The subject owns exactly one feature that redefines the ``disposition`` of a kernel holder
    (IncrementBaselineDecision, IncrementGap) in its own type lineage, as library attributes do, and its
    value is exactly one leaf: a literal that the bound
    LifecycleDisposition itself owns through a VariantMembership. A value that only a definition sets is
    not the record's own. Raises :class:`MethodSideInput` when a kernel class has no validated binding."""
    try:
        enum = view.kernel_element(LIFECYCLE_DISPOSITION)
        holders = [view.kernel_element(holder) for holder in DISPOSITION_HOLDERS]
    except IdentityNotFoundError as error:
        raise MethodSideInput(f"kernel-binding:{LIFECYCLE_DISPOSITION}",
                              f"method side: no validated kernel binding for the disposition: {error}")
    lineage = {general for definition in view.index.typed_by(subject_id) for general in view.index.generals(definition)}
    kernel_features = {feature for holder in holders if holder in lineage
                       if (feature := view.index.feature(holder, DISPOSITION_FEATURE)) is not None}
    own = [feature for feature in view.index.owned_members(subject_id)
           if kernel_features & _redefined_features(view, feature)]
    if len(own) != 1:
        return None
    leaves = view.index.value_leaves(own[0])
    if len(leaves) != 1 or leaves[0].kind != "reference":
        return None
    literal = str(leaves[0].value)
    membership = view.element(str((view.element(literal).get("owningRelationship") or {}).get("@id") or ""))
    if (view.element(literal).get("@type") != "EnumerationUsage"
            or membership.get("@type") != "VariantMembership"
            or (membership.get("owningRelatedElement") or {}).get("@id") != enum):
        return None
    return literal


def _disposition_stated(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The baseline decision, or an open gap of the increment, states its own disposition
    (:func:`lifecycle_disposition`): accepted, deferred or invalidated. A resolved gap's record leaves the
    model, so every gap in scope is open."""
    literal = lifecycle_disposition(view, subject_id)
    if literal is not None:
        return satisfied([literal], [subject_id])
    return violated(f"{_name(view, subject_id)} states no disposition of its own: it owns no single redefinition "
                    "of disposition whose one value is a literal of LifecycleDisposition (accepted, deferred or "
                    "invalidated)")


_expected_artifacts_cover_content.member = SCOPE_ATTRIBUTE  # type: ignore[attr-defined]
_subject_is_system_of_interest.member = SYSTEM_OF_INTEREST_ATTRIBUTE  # type: ignore[attr-defined]
_context_system_of_interest.member = CONTEXT_SYSTEM_OF_INTEREST  # type: ignore[attr-defined]


#: Check id -> implementation (named checks; relation names join per contract).
NAMED_CHECKS: Mapping[str, CheckFunction] = MappingProxyType({
    "incrementShortName": _increment_short_name,
    "charterReferencesIncrement": _charter_references_increment,
    "problemStatementSubject": _problem_statement_subject,
    "ownedByIncrementPackage": _owned_by_increment_package,
    "stakeholderMember": _stakeholder_member,
    "framedByIncrementView": _framed_by_increment_view,
    "nonBoundaryConcernPresent": _non_boundary_concern_present,
    "charterOwner": _charter_text("owner"),
    "charterApplicablePhases": _charter_applicable_phases,
    "charterExpectedArtifacts": _charter_expected_artifacts,
    "charterExpectedReviewEvidence": _charter_text("expectedReviewEvidence"),
    "requireConstraint": _require_constraint,
    "sourceAttribute": _library_attribute("source"),
    "rationaleAttribute": _library_attribute("rationale"),
    "oneNativeSubject": _one_native_subject,
    "subjectIsSystemOfInterest": _subject_is_system_of_interest,
    "charterExpectedArtifactsCoverContent": _expected_artifacts_cover_content,
    "oneVerificationMethodKind": _library_attribute("verificationMethod", allowed=STANDARD_VERIFICATION_METHOD_KINDS),
    "successCriteriaAttribute": _library_attribute("successCriteria"),
    "verifiesIncrementRequirement": _verifies_increment_requirement,
    "evidenceRecordOrStatus": _evidence_record_or_status,
    "receivesAllocation": _receives_allocation,
    "carriedByArchitecture": _carried_by_architecture,
    "populationMember": _population_member,
    "signalMappingRecorded": _signal_mapping_recorded,
    "semanticSourceNamed": _semantic_source_named,
    "framedByViewpoint": _framed_by_viewpoint,
    "contextSystemOfInterest": _context_system_of_interest,
    "storySubjectBound": _story_subject_bound,
    "storyActorsBound": _story_actors_bound,
    "featureDeltaOnly": _feature_delta_only,
    "viewpointFramesConcern": _viewpoint_frames_concern,
    "exposesModelContent": _exposes_model_content,
    "configuredByOneConfiguration": _configured_by_one_configuration,
    "dispositionStated": _disposition_stated,
})

#: Check id -> the most distinct targets the check accepts (absent: unbounded).
CHECK_MAXIMUM: Mapping[str, int] = MappingProxyType({
    check: 1 for check in ("incrementShortName", "charterReferencesIncrement", "ownedByIncrementPackage",
                           "charterOwner", "sourceAttribute", "rationaleAttribute", "oneNativeSubject",
                           "oneVerificationMethodKind", "successCriteriaAttribute", "configuredByOneConfiguration",
                           "dispositionStated")
})


def method_checks(view: ModelView) -> Mapping[str, me.Predicate]:
    """Check id -> evaluator predicate: the named checks and one check per relation of the
    view's contract (read-only, built once per contract)."""

    def build() -> Mapping[str, me.Predicate]:
        functions = {relation: relation_holds(relation) for relation in relation_checks(view)}
        functions.update(NAMED_CHECKS)
        return MappingProxyType({check: with_increment(check, f) for check, f in functions.items()})

    return view.index.memo_bound(("method-checks",), (view.contract,), build)


def remedy(check_id: str, view: ModelView, subject_id: str | None = None) -> str:
    """What to author for one check, in model terms (without the step parameter it is about; the
    answers build it with the parameter: :func:`de4sdv.semantic.remedies.check_remedy`)."""
    from .remedies import check_remedy  # the remedies read this module's checks

    return check_remedy(view, check_id, subject=subject_id).text


def default_claim(check_id: str, view: ModelView) -> str:
    """The claim boundary of a check whose declaration states none."""
    if check_id in relation_checks(view) and check_id not in NAMED_CHECKS:
        return (f"each subject reaches the declared minimum of distinct targets through {check_id}; "
                "model content only, no acceptance, compliance or evidence claim")
    return f"model-content check {check_id}; no acceptance, compliance, certification or evidence-adequacy claim"
