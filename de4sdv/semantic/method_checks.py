"""Method checks: a check id maps to an implementation over the model.

A method declares checks about the elements its steps produce. Each check
names, by its id, what must hold for every subject element; this registry maps
the id to the implementation that decides it for one subject:

- **named checks** state one rule, for example ``framesStakeholderConcern``
  (the need frames a concern that declares a stakeholder), ``oneNativeSubject``
  (exactly one subject), ``oneVerificationMethodKind`` (one standard
  verification method kind is recorded) or ``ownedByIncrementPackage``;
- **relation names**, for example ``derivesRequirementFromNeed``,
  ``hasValidationScenario`` or ``verifiedBy``: the subject reaches targets
  through that relation (see :mod:`de4sdv.semantic.relation_checks`).

An implementation takes the model view, the increment and one subject; it
reads no method-representation field (no selector, filter or phase text). How
many distinct targets a subject needs is the method's ``minimum``; a check may
bound the maximum itself (``requirementHasOneSubject``: one). A check id the
registry does not know is not registered, so a method naming it fails
contract validation: unknown checks fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from de4sdv.sysml_api.repository import reference_ids

from . import method_evaluator as me
from .increment_scope import IncrementScope, ModelView
from .relation_checks import (
    MethodSideInput,
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
        result = relation_checks(view).check(relation, view, subject_id)
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
    if str(view.element(subject_id).get("declaredShortName") or "") != increment.increment_id:
        return violated(f"{_name(view, subject_id)} does not carry the increment identifier "
                        f"{increment.increment_id!r} as its declared short name")
    return satisfied([subject_id])


def _charter_references_increment(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    references = [leaf.value for leaf in view.index.feature_values(subject_id, "increment") if leaf.kind == "reference"]
    if increment.usage_id is None or increment.usage_id not in references:
        return violated(f"{_name(view, subject_id)} does not reference the increment {increment.increment_id} "
                        "through its increment value")
    return satisfied([increment.usage_id], witnesses=[subject_id])


def _problem_statement_subject(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    wanted = set(increment.definition_ids)
    subjects = [member for member in membership_members(view, subject_id, "SubjectMembership")
                if view.index.typed_by(member) & wanted]
    if increment.package_id is None or view.index.owner_of(subject_id) != increment.package_id or not subjects:
        return violated(f"{_name(view, subject_id)} is not a problem statement of the increment package with a "
                        "native subject typed by the increment definition")
    return satisfied(subjects)


def _owned_by_increment_package(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    if increment.package_id is None or view.index.owner_of(subject_id) != increment.package_id:
        package = _name(view, increment.package_id) if increment.package_id else "the increment package"
        return violated(f"{_name(view, subject_id)} is not owned by {package}")
    return satisfied([increment.package_id], witnesses=[subject_id])


def _stakeholder_member(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    found = relation_checks(view).check("stakeholder", view, subject_id).targets
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

    return check


def _charter_applicable_phases(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    try:
        phase_root = view.kernel_element("MethodPhase")
    except Exception as error:  # noqa: BLE001 - an unbound enumeration is method side
        return indeterminate("kernel-binding:MethodPhase", f"method side: {error}")
    literals = [leaf.value for leaf in view.index.feature_values(subject_id, "applicablePhases")
                if leaf.kind == "reference" and view.index.owner_of(leaf.value) == phase_root]
    if not literals:
        return violated(f"{_name(view, subject_id)} declares no applicablePhases value that is a MethodPhase literal")
    return satisfied(literals, witnesses=[subject_id])


def _require_constraint(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    found = []
    for relationship in view.index.owned_relationships(subject_id, "RequirementConstraintMembership"):
        if str(relationship.get("kind") or "requirement") == "requirement":
            found.extend(reference_ids(relationship.get("memberElement")))
    if not found:
        return violated(f"{_name(view, subject_id)} owns no require constraint (statement)")
    return satisfied(found)


def _library_attribute(attribute: str, *, allowed: Sequence[str] = ()) -> CheckFunction:
    """Non-empty values of an inherited (library) attribute, each from ``allowed`` when given.

    How many values a subject may carry is the check's cardinality (for
    example exactly one verification method kind).
    """

    def check(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
        feature = view.index.feature(subject_id, attribute)
        redefined: list[str] = []
        if feature is not None:
            for relationship in view.index.owned_relationships(feature, "Redefinition"):
                redefined.extend(reference_ids(relationship.get("redefinedFeature")))
        inherited = [r for r in redefined
                     if view.index.name_of(r) == attribute and view.index.owner_of(r) != subject_id]
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

    return check


def _frames_stakeholder_concern(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    hops = [(concern, witness) for concern, witness in relation_checks(view).check("frame", view, subject_id).hops
            if membership_members(view, concern, "StakeholderMembership")]
    if not hops:
        return violated(f"{_name(view, subject_id)} frames no concern that has a native stakeholder member")
    return satisfied([c for c, _w in hops], [w for _c, w in hops])


def _one_native_subject(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    found = relation_checks(view).check("subject", view, subject_id).targets
    if not found:
        return violated(f"{_name(view, subject_id)} declares no subject")
    return satisfied(found)


def _feature_or_common_capability(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    targets, witnesses, method_side = [], [], []
    for relation in ("specifiesFeature", "specifiesCommonCapability"):
        result = relation_checks(view).check(relation, view, subject_id)
        if result.method_side:
            method_side.append(result.problem)
            continue
        if result.problem:
            return indeterminate(result.problem, result.detail)
        targets.extend(t for t, _w in result.hops)
        witnesses.extend(w for _t, w in result.hops)
    if not targets and len(method_side) == 2:
        return indeterminate(",".join(method_side), "method side: specifiesFeature and specifiesCommonCapability "
                                                    "have no SysML mapping at this revision")
    if not targets:
        return violated(f"{_name(view, subject_id)} specifies no feature or common capability")
    return satisfied(targets, witnesses)


def _verifies_increment_requirement(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The case verifies a requirement of the increment: a Requirement-lineage element of its scope."""
    result = relation_checks(view).check("verify", view, subject_id)
    scope = set(increment.scope_elements)
    hops = [(target, witness) for target, witness in result.hops
            if target in scope and in_class(view, target, "Requirement")]
    if not hops:
        verified = ", ".join(_name(view, t) for t in result.targets[:5]) or "nothing"
        return violated(f"{_name(view, subject_id)} verifies no requirement of the increment",
                        (f"verified: {verified}",), witnesses=result.witnesses)
    return satisfied([t for t, _w in hops], [w for _t, w in hops])


def _verifies_acceptance_criterion(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    result = relation_checks(view).check("verify", view, subject_id)
    hops = [(target, witness) for target, witness in result.hops if in_class(view, target, "AcceptanceCriterion")]
    if not hops:
        return violated(f"{_name(view, subject_id)} verifies no acceptance criterion")
    return satisfied([t for t, _w in hops], [w for _t, w in hops])


def _evidence_record_or_status(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    result = relation_checks(view).check("hasEvidence", view, subject_id)
    if result.problem:
        return indeterminate(result.problem, result.detail)
    if not result.hops:
        return violated(f"{_name(view, subject_id)} has no evidence record or status")
    return satisfied([t for t, _w in result.hops], [w for _t, w in result.hops])


@dataclass(frozen=True)
class CheckDefinition:
    """One check id, its implementation and what a subject needs to satisfy it."""

    check_id: str
    evaluate: CheckFunction
    #: The most distinct targets the check accepts (``None``: unbounded).
    maximum: int | None = None
    #: What to author when the check fails, in model terms ({subject}, {subject_name}).
    remedy: str = ""
    #: The claim boundary used when the method gives none.
    claim: str = ""


_KINDS = ", ".join(STANDARD_VERIFICATION_METHOD_KINDS)

NAMED_CHECKS = (
    CheckDefinition("incrementShortName", _increment_short_name, maximum=1,
                    remedy="declare the increment usage with its identifier as declared short name: "
                           "part <'INC-...'> <usageName> : <IncrementDefinition>;"),
    CheckDefinition("charterReferencesIncrement", _charter_references_increment, maximum=1,
                    remedy="reference the increment from {subject}: ref part :>> increment = <incrementUsage>;"),
    CheckDefinition("problemStatementSubject", _problem_statement_subject,
                    remedy="in the increment package: requirement <name> : ProblemStatement "
                           "{{ subject increment : <IncrementDefinition>; }}"),
    CheckDefinition("ownedByIncrementPackage", _owned_by_increment_package, maximum=1,
                    remedy="declare {subject} in the increment package"),
    CheckDefinition("stakeholderMember", _stakeholder_member,
                    remedy="add to {subject}: stakeholder <name> : <role>;"),
    CheckDefinition("framedByIncrementView", _framed_by_increment_view,
                    remedy="in the increment package, frame {subject_name} by a viewpoint of a view: view <name> "
                           "{{ viewpoint <name> : <Viewpoint> {{ frame {subject_name}; }} }}"),
    CheckDefinition("charterOwner", _charter_text("owner"), maximum=1,
                    remedy="set on {subject}: attribute :>> owner = \"...\";"),
    CheckDefinition("charterApplicablePhases", _charter_applicable_phases,
                    remedy="set on {subject}: attribute :>> applicablePhases = (MethodPhase::...);"),
    CheckDefinition("charterExpectedArtifacts", _charter_text("expectedArtifacts"),
                    remedy="set on {subject}: attribute :>> expectedArtifacts = (\"...\");"),
    CheckDefinition("charterExpectedReviewEvidence", _charter_text("expectedReviewEvidence"),
                    remedy="set on {subject}: attribute :>> expectedReviewEvidence = (\"...\");"),
    CheckDefinition("requireConstraint", _require_constraint,
                    remedy="add the statement to {subject}: require constraint statement "
                           "{{ language \"English\" /* ... */ }}"),
    CheckDefinition("sourceAttribute", _library_attribute("source"), maximum=1,
                    remedy="set on {subject}: attribute :>> source = \"...\";"),
    CheckDefinition("rationaleAttribute", _library_attribute("rationale"), maximum=1,
                    remedy="set on {subject}: attribute :>> rationale = \"...\";"),
    CheckDefinition("framesStakeholderConcern", _frames_stakeholder_concern,
                    remedy="frame a stakeholder concern in {subject}: frame <concern>; (the concern declares a "
                           "stakeholder)"),
    CheckDefinition("oneNativeSubject", _one_native_subject, maximum=1,
                    remedy="declare exactly one subject on {subject}: subject <name> : <Definition>;"),
    CheckDefinition("oneVerificationMethodKind",
                    _library_attribute("verificationMethod", allowed=STANDARD_VERIFICATION_METHOD_KINDS), maximum=1,
                    remedy="set on {subject}: attribute :>> verificationMethod = \"<kind>\"; (one of " + _KINDS + ")"),
    CheckDefinition("specifiesFeatureOrCommonCapability", _feature_or_common_capability,
                    remedy="trace {subject} to a feature or common capability"),
    CheckDefinition("verifiesIncrementRequirement", _verifies_increment_requirement,
                    remedy="add to the objective of {subject} (or its definition): verify <increment requirement>;"),
    CheckDefinition("verifiesAcceptanceCriterion", _verifies_acceptance_criterion,
                    remedy="add to the objective of {subject}: verify <acceptance criterion>;"),
    CheckDefinition("evidenceRecordOrStatus", _evidence_record_or_status,
                    remedy="record evidence for {subject} (evidence content is external at this revision)"),
)

#: What to author for a relation, where the relation needs more than its name.
_RELATION_REMEDIES = {
    "derivesRequirementFromNeed": "replace any plain dependency with: connection <name> : DerivesFromNeed "
                                  "connect <need> to {subject_name};",
    "hasValidationScenario": "add a scenario and connect it to {subject}: connection <name> : "
                             "ValidationPlanningAssociation connect {subject_name} to <scenario>;",
    "frame": "add to {subject}: frame <concern>;",
    "stakeholder": "add to {subject}: stakeholder <name> : <role>;",
    "subject": "declare a subject on {subject}: subject <name> : <Definition>;",
    "verify": "add to the objective of {subject} (or its definition): verify <requirement>;",
}


class MethodCheckRegistry:
    """Immutable map from check id to check definition."""

    def __init__(self, definitions: Iterable[CheckDefinition]) -> None:
        table: dict[str, CheckDefinition] = {}
        for definition in definitions:
            if definition.check_id in table:
                raise ValueError(f"check {definition.check_id!r} is registered twice")
            table[definition.check_id] = definition
        self._table = table
        self._predicates = me.PredicateRegistry(
            me.PredicateDefinition(d.check_id, with_increment(d.check_id, d.evaluate), remedy=d.remedy)
            for d in table.values()
        )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._table))

    def __contains__(self, check_id: object) -> bool:
        return check_id in self._table

    def definition(self, check_id: str) -> CheckDefinition:
        try:
            return self._table[check_id]
        except KeyError:
            raise KeyError(f"no method check is registered for {check_id!r}") from None

    def predicates(self) -> me.PredicateRegistry:
        """The evaluator registry: one predicate per check id."""
        return self._predicates

    def remedy(self, spec: me.ObligationSpec, *, increment: IncrementScope, view: ModelView,
               subject_id: str | None = None) -> str:
        """What to author for one check, in model terms."""
        definition = self._table.get(spec.predicate)
        if definition is None or not definition.remedy:
            return ""
        values = {
            "subject": element_name(view, subject_id) if subject_id else "each subject",
            "subject_name": view.index.name_of(subject_id) if subject_id else "<subject>",
        }
        try:
            return definition.remedy.format(**values)
        except (KeyError, IndexError, ValueError):
            return definition.remedy

    @classmethod
    def for_relations(cls, relations: Iterable[str]) -> "MethodCheckRegistry":
        """The named checks plus one relation check per relation name."""
        named = {d.check_id for d in NAMED_CHECKS}
        definitions = list(NAMED_CHECKS)
        for relation in sorted(set(relations) - named):
            definitions.append(CheckDefinition(
                relation, relation_holds(relation),
                remedy=_RELATION_REMEDIES.get(relation, f"add a {relation} relation from {{subject}}"),
                claim=f"each subject reaches the declared minimum of distinct targets through {relation}; "
                      "model content only, no acceptance, compliance or evidence claim",
            ))
        return cls(definitions)


def method_checks(view: ModelView) -> MethodCheckRegistry:
    """The method checks of the view's contract (built once per contract)."""
    return view.index.memo_bound(
        ("method-checks",), (view.contract,),
        lambda: MethodCheckRegistry.for_relations(relation_checks(view).names()),
    )
