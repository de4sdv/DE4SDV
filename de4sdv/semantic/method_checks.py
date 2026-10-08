"""Method checks: a check id maps to an implementation over the model.

A method declares checks about the elements its steps produce. Each check
names, by its id, what must hold for every subject element; this registry maps
the id to the implementation that decides it for one subject:

- **named checks** state one rule, for example ``needFramesConcern`` (the need
  frames a concern that declares a stakeholder), ``requirementHasOneSubject``
  (exactly one subject), ``hasVerificationMethod`` (a standard verification
  method kind is recorded) or ``verifiedByVerificationCase`` (a verification
  case usage verifies the requirement);
- **relation names**, for example ``derivesRequirementFromNeed`` or
  ``frame``: the subject reaches targets through that relation (see
  :mod:`de4sdv.semantic.relation_checks`).

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


def _need_frames_concern(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    hops = [(concern, witness) for concern, witness in relation_checks(view).check("frame", view, subject_id).hops
            if membership_members(view, concern, "StakeholderMembership")]
    if not hops:
        return violated(f"{element_name(view, subject_id)} frames no concern that has a native stakeholder member")
    return satisfied([c for c, _w in hops], [w for _c, w in hops])


def _requirement_subject(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    found = relation_checks(view).check("subject", view, subject_id).targets
    if not found:
        return violated(f"{element_name(view, subject_id)} declares no subject")
    return satisfied(found)


def _verification_method(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """The requirement sets the library ``verificationMethod`` to a standard kind."""
    attribute = "verificationMethod"
    feature = view.index.feature(subject_id, attribute)
    redefined: list[str] = []
    if feature is not None:
        for relationship in view.index.owned_relationships(feature, "Redefinition"):
            redefined.extend(reference_ids(relationship.get("redefinedFeature")))
    inherited = [r for r in redefined if view.index.name_of(r) == attribute and view.index.owner_of(r) != subject_id]
    name = element_name(view, subject_id)
    if feature is None or not inherited:
        return violated(f"{name} sets no {attribute} value (attribute :>> {attribute} = ...)")
    texts = [str(leaf.value) for leaf in view.index.feature_values(subject_id, attribute)
             if leaf.kind == "string" and str(leaf.value or "").strip()]
    if not texts:
        return violated(f"{name} {attribute} value is empty")
    if not set(texts) <= set(STANDARD_VERIFICATION_METHOD_KINDS):
        return violated(f"{name} {attribute} value {sorted(set(texts))} is not one of "
                        f"{', '.join(STANDARD_VERIFICATION_METHOD_KINDS)}")
    return satisfied(texts, witnesses=[feature, *inherited])


def _verified_by_case(view: ModelView, increment: IncrementScope, subject_id: str) -> me.PredicateOutcome:
    """A verification case usage verifies the requirement (a definition's objective covers its usages)."""
    result = relation_checks(view).check("verifiedBy", view, subject_id)
    if result.problem:
        return indeterminate(result.problem, result.detail)
    targets, witnesses = [], []
    for target, witness in result.hops:
        candidates = [target]
        if str(view.element(target).get("@type")) != "VerificationCaseUsage":
            candidates = [usage for usage in view.index.typed_usages(target)
                          if str(view.element(usage).get("@type")) == "VerificationCaseUsage"]
        for candidate in candidates:
            targets.append(candidate)
            witnesses.append(witness)
    if not targets:
        return violated(f"{element_name(view, subject_id)} is verified by no verification case usage")
    return satisfied(targets, witnesses)


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


NAMED_CHECKS = (
    CheckDefinition(
        "needFramesConcern", _need_frames_concern,
        remedy="frame a stakeholder concern in {subject}: frame <concern>; (the concern declares a stakeholder)",
        claim="each need natively frames at least one stakeholder concern; framing only, no concern "
              "satisfaction or derivation claim",
    ),
    CheckDefinition(
        "requirementHasOneSubject", _requirement_subject, maximum=1,
        remedy="declare exactly one subject on {subject}: subject <name> : <Definition>;",
        claim="each requirement declares exactly one native subject; subject declaration only",
    ),
    CheckDefinition(
        "hasVerificationMethod", _verification_method,
        remedy="set on {subject}: attribute :>> verificationMethod = \"<kind>\"; (one of "
               + ", ".join(STANDARD_VERIFICATION_METHOD_KINDS) + ")",
        claim="each requirement records a standard verification method kind (planning data); no "
              "verification result or evidence claim",
    ),
    CheckDefinition(
        "verifiedByVerificationCase", _verified_by_case,
        remedy="add `verify {subject_name};` to the objective of a verification case",
        claim="each requirement is verified by the objective of at least one verification case; "
              "verification planning only, no verification result or evidence claim",
    ),
)

#: What to author for a relation, where the relation needs more than its name.
_RELATION_REMEDIES = {
    "derivesRequirementFromNeed": "replace any plain dependency with: connection <name> : DerivesFromNeed "
                                  "connect <need> to {subject_name};",
    "hasValidationScenario": "add a scenario and connect it to {subject}: connection <name> : "
                             "<:> ValidationPlanningAssociation> connect {subject_name} to <scenario>;",
    "frame": "frame <concern> in {subject};",
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
