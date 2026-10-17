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
  increment) or ``charterExpectedArtifactsCoverContent`` (no package
  holding increment content is missing from the charter's
  ``expectedArtifacts``, the scope the checks evaluate);
- **relation names**, for example ``derivesRequirementFromNeed``,
  ``hasValidationScenario`` or ``verifiedBy``: the subject reaches targets
  through that relation (see :mod:`de4sdv.semantic.relation_checks`).

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
)
from .relation_checks import (
    MethodSideInput,
    check_relation,
    connection_ends,
    element_name,
    in_class,
    membership_members,
    relation_checks,
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


#: Declared (never implied) relations from a usage to the usages it narrows.
_NARROWING = (("Subsetting", "subsettedFeature"), ("Redefinition", "redefinedFeature"),
              ("ReferenceSubsetting", "referencedFeature"))


def _narrowed_usages(view: ModelView, usage: str) -> list[str]:
    """``usage`` and every usage it subsets, redefines or references, transitively."""
    found: list[str] = []
    frontier = [usage]
    while frontier:
        current = frontier.pop(0)
        if current in found:
            continue
        found.append(current)
        for relationship_type, key in _NARROWING:
            for relationship in view.index.owned_relationships(current, relationship_type):
                if relationship.get("isImplied"):
                    continue
                frontier.extend(reference_ids(relationship.get(key)))
    return found


def _usage_reaches(view: ModelView, usage: str, usages: set[str], types: set[str]) -> bool:
    """The usage is, or narrows, one of ``usages``, or is typed (itself or through what it
    narrows) by one of ``types``."""
    narrowed = _narrowed_usages(view, usage)
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
    verification case in scope, and an element referencing the increment
    usage (only the usage: a reference to another increment element is not
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


#: The member each of these checks reads, which a remedy sets (de4sdv.semantic.remedies).
_charter_references_increment.member = INCREMENT_ATTRIBUTE  # type: ignore[attr-defined]
_charter_applicable_phases.member = PHASES_ATTRIBUTE  # type: ignore[attr-defined]
_charter_expected_artifacts.member = SCOPE_ATTRIBUTE  # type: ignore[attr-defined]
_expected_artifacts_cover_content.member = SCOPE_ATTRIBUTE  # type: ignore[attr-defined]
_subject_is_system_of_interest.member = SYSTEM_OF_INTEREST_ATTRIBUTE  # type: ignore[attr-defined]


#: Check id -> implementation (named checks; relation names join per contract).
NAMED_CHECKS: Mapping[str, CheckFunction] = MappingProxyType({
    "incrementShortName": _increment_short_name,
    "charterReferencesIncrement": _charter_references_increment,
    "problemStatementSubject": _problem_statement_subject,
    "ownedByIncrementPackage": _owned_by_increment_package,
    "stakeholderMember": _stakeholder_member,
    "framedByIncrementView": _framed_by_increment_view,
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
})

#: Check id -> the most distinct targets the check accepts (absent: unbounded).
CHECK_MAXIMUM: Mapping[str, int] = MappingProxyType({
    check: 1 for check in ("incrementShortName", "charterReferencesIncrement", "ownedByIncrementPackage",
                           "charterOwner", "sourceAttribute", "rationaleAttribute", "oneNativeSubject",
                           "oneVerificationMethodKind", "successCriteriaAttribute")
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
