"""Increment resolution from the model: identity, charter declaration, populations.

An engineering increment is identified only by its registered identifier
(``INC-<SUBJECT>-<SEQ>``, docs/naming/naming-conventions.md) carried as the
declared short name of a part usage in the EngineeringIncrement lineage.
Lineage is validated kernel identity (ingestion-validated kernel bindings,
ADR 0011); element names never identify anything here.

From the identified usage the resolution reads, through native
relationships only:

- the increment definitions (the usage's typing) and the increment package
  (the usage's owning namespace);
- the charter declaration: the IncrementTraceObligations-lineage usage whose
  ``increment`` value references the usage, and its declared applicable
  phases (MethodPhase literals);
- the populations the method gates select: needs and requirements whose
  native subject is typed by an increment definition, and verification cases
  owned by the increment package or by a package that declares
  ``references`` to the increment usage.

A population that cannot be established (for example a missing kernel
binding) is recorded as a population problem, never as an empty population.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from .revision_index import RevisionIndex

#: ``INC-<SUBJECT>-<SEQ>[<letter>][-<SUBSEQ>...]`` (naming conventions §4).
_INCREMENT_ID = re.compile(r"\AINC-[A-Z][A-Z0-9]*-[0-9]+[A-Z]?(?:-[0-9A-Z]+)*\Z")

#: Typed population selectors of an increment.
SELECTOR_INCREMENT_IDENTIFIER = "incrementIdentifier"
SELECTOR_INCREMENT = "increment"
SELECTOR_NEEDS = "incrementNeeds"
SELECTOR_REQUIREMENTS = "incrementRequirements"
SELECTOR_VERIFICATION_CASES = "incrementVerificationCases"
INCREMENT_SELECTORS = (
    SELECTOR_INCREMENT_IDENTIFIER,
    SELECTOR_INCREMENT,
    SELECTOR_NEEDS,
    SELECTOR_REQUIREMENTS,
    SELECTOR_VERIFICATION_CASES,
)

#: Kernel classes the resolution grounds in (ontology class names).
INCREMENT_CLASS = "EngineeringIncrement"
CHARTER_CLASS = "IncrementTraceObligations"
NEED_CLASS = "Need"
REQUIREMENT_CLASS = "Requirement"
EVIDENCE_CONTRACT_CLASS = "EvidenceContract"
PHASE_CLASS = "MethodPhase"

PROBLEM_UNAVAILABLE = "unavailable"
PROBLEM_INVALID = "invalid"


class IncrementIdentifierError(ValueError):
    """The requested value is not an increment identifier."""


def parse_increment_id(value: str) -> str:
    """The identifier itself, or :class:`IncrementIdentifierError`."""
    text = value if isinstance(value, str) else ""
    if not _INCREMENT_ID.fullmatch(text):
        raise IncrementIdentifierError(
            f"{value!r} is not an increment identifier: expected the registered "
            "form INC-<SUBJECT>-<SEQ> (for example INC-AEBS-010), read from the "
            "increment usage's declared short name"
        )
    return text


class ModelView:
    """One evaluated element corpus with validated kernel lineage.

    Structure comes from the corpus's revision index (shared with the
    traversal); lineage comes from the traversal's ingestion-validated
    kernel binding index.
    """

    def __init__(
        self,
        elements: Sequence[Mapping[str, Any]],
        traversal: Any,
        *,
        sources: Mapping[str, str] | None = None,
    ) -> None:
        self.elements = elements
        self.traversal = traversal
        self.sources: Mapping[str, str] = sources or {}
        self.index: RevisionIndex = traversal.revision_index(elements)

    @property
    def contract(self) -> Any:
        return self.traversal.contract

    def element(self, identifier: str | None) -> Mapping[str, Any]:
        return self.index.element(identifier)

    def grounding(self, identifier: str, ontology_class: str) -> str | None:
        """Lineage grounding of one element (raises when the class is unbound)."""
        element = self.index.by_id.get(identifier)
        if element is None:
            return None
        return self.traversal.grounding(element, ontology_class, self.elements)

    def in_lineage(self, identifier: str, ontology_class: str) -> bool:
        return self.grounding(identifier, ontology_class) is not None

    def kernel_element(self, ontology_class: str) -> str:
        """The validated kernel element of a class (raises when unbound)."""
        bindings = self.traversal.kernel_bindings
        if bindings is None:
            raise IdentityNotFoundError(
                f"no validated kernel binding index; {ontology_class!r} cannot be resolved"
            )
        return bindings.element_id_for(ontology_class, self.index.by_id)

    def class_of_declaration(self, declaration_name: str) -> str | None:
        """The kernel-index class holding the validated binding of a declaration.

        Resolution goes through the ingestion-validated kernel bindings
        themselves (their recorded declaration), so a binding the runtime
        files under a routed profile name still resolves. Exactly one binding
        must carry the declaration; otherwise the declaration has no identity.
        """
        bindings = getattr(self.traversal.kernel_bindings, "bindings", ()) or ()

        def build() -> dict[str, list[str]]:
            found: dict[str, list[str]] = {}
            for binding in bindings:
                name = str(binding.declaration).split()[-1] if binding.declaration else ""
                if name:
                    found.setdefault(name, []).append(binding.ontology_class)
            return found

        table = self.index.memo_bound(("declaration-classes",), (self.traversal.kernel_bindings,), build)
        classes = table.get(declaration_name) or []
        return classes[0] if len(classes) == 1 else None

    def source_of(self, identifier: str | None) -> str:
        return str(self.sources.get(identifier or "", ""))

    def describe(self, identifier: str | None) -> dict[str, str]:
        """Display record of one element: name, qualified name, short name, source."""
        element = self.element(identifier)
        record = {
            "element_id": str(identifier or ""),
            "name": self.index.name_of(identifier),
            "qualified_name": self.index.qualified_name(identifier),
        }
        short = element.get("declaredShortName")
        if short:
            record["short_name"] = str(short)
        source = self.source_of(identifier)
        if source:
            record["source"] = source
        return record


@dataclass(frozen=True)
class IncrementScope:
    """The model-resolved scope of one requested increment."""

    increment_id: str
    candidates: tuple[str, ...]
    rejected_candidates: tuple[str, ...]
    usage_id: str | None
    definition_ids: tuple[str, ...]
    package_id: str | None
    charters: tuple[str, ...]
    declared_phases: tuple[str, ...] | None
    verification_packages: tuple[str, ...]
    populations: Mapping[str, tuple[str, ...]]
    population_problems: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()


def resolve_increment(view: ModelView, increment_id: str) -> IncrementScope:
    """Resolve the increment and its populations from the model."""
    identifier = parse_increment_id(increment_id)
    index = view.index
    diagnostics: list[str] = []
    problems: dict[str, tuple[str, str]] = {}

    holders = index.with_short_name(identifier)
    candidates: list[str] = []
    rejected: list[str] = []
    try:
        for holder in holders:
            if str(index.element(holder).get("@type")) == "PartUsage" and view.in_lineage(
                holder, INCREMENT_CLASS
            ):
                candidates.append(holder)
            else:
                rejected.append(holder)
    except IdentityNotFoundError as error:
        problems[SELECTOR_INCREMENT] = (PROBLEM_UNAVAILABLE, f"kernel-binding:{INCREMENT_CLASS}: {error}")
        diagnostics.append(f"the EngineeringIncrement lineage cannot be established: {error}")
    for holder in rejected:
        diagnostics.append(
            f"{index.qualified_name(holder) or holder} carries the declared short name "
            f"{identifier!r} but is not a part usage in the EngineeringIncrement lineage"
        )
    if not holders:
        diagnostics.append(
            f"no part usage in the EngineeringIncrement lineage carries the declared "
            f"short name {identifier!r}"
        )
    usage_id = candidates[0] if len(candidates) == 1 else None
    if len(candidates) > 1:
        detail = (f"ambiguous increment identity: {len(candidates)} part usages carry the "
                  f"declared short name {identifier!r}")
        diagnostics.append(detail)
        problems[SELECTOR_INCREMENT] = (PROBLEM_INVALID, detail)

    definition_ids: tuple[str, ...] = ()
    package_id: str | None = None
    charters: tuple[str, ...] = ()
    declared_phases: tuple[str, ...] | None = None
    if usage_id is not None:
        definition_ids = tuple(sorted(index.typed_by(usage_id)))
        package_id = index.owner_of(usage_id)
        charters, charter_problem = _charters(view, usage_id)
        if charter_problem:
            diagnostics.append(charter_problem)
        if len(charters) == 1:
            declared_phases, phase_diagnostics = _declared_phases(view, charters[0])
            diagnostics.extend(phase_diagnostics)
        elif len(charters) > 1:
            diagnostics.append(
                f"{len(charters)} charter declarations reference the increment; applicable "
                "phases are unresolved"
            )
        else:
            diagnostics.append("no charter declaration references the increment")

    populations: dict[str, tuple[str, ...]] = {
        SELECTOR_INCREMENT_IDENTIFIER: (identifier,),
        SELECTOR_INCREMENT: (usage_id,) if usage_id else (),
    }
    needs, requirements = _requirement_populations(view, definition_ids, problems)
    populations[SELECTOR_NEEDS] = _ordered(view, needs)
    populations[SELECTOR_REQUIREMENTS] = _ordered(view, requirements)
    verification_packages = _verification_packages(view, usage_id, package_id)
    populations[SELECTOR_VERIFICATION_CASES] = _ordered(view, [
        case
        for package in verification_packages
        for case in index.owned_members(package, "VerificationCaseUsage")
    ])
    if usage_id is None:
        for selector in (SELECTOR_NEEDS, SELECTOR_REQUIREMENTS, SELECTOR_VERIFICATION_CASES):
            problems.setdefault(
                selector,
                (PROBLEM_UNAVAILABLE, f"the increment {identifier!r} is not identified in the model"),
            )
    return IncrementScope(
        increment_id=identifier,
        candidates=tuple(candidates),
        rejected_candidates=tuple(rejected),
        usage_id=usage_id,
        definition_ids=definition_ids,
        package_id=package_id,
        charters=charters,
        declared_phases=declared_phases,
        verification_packages=verification_packages,
        populations=populations,
        population_problems=problems,
        diagnostics=tuple(diagnostics),
    )


def _ordered(view: ModelView, identifiers: Sequence[str]) -> tuple[str, ...]:
    """Distinct identifiers in a corpus-order-independent order.

    An API listing and an export of the same revision may enumerate elements
    differently; qualified name then element identifier is stable for both.
    """
    unique = list(dict.fromkeys(identifiers))
    return tuple(sorted(unique, key=lambda item: (view.index.qualified_name(item), item)))


def _charters(view: ModelView, usage_id: str) -> tuple[tuple[str, ...], str]:
    index = view.index
    found: list[str] = []
    try:
        for candidate in index.elements_of_type("PartUsage"):
            values = index.feature_values(candidate, "increment")
            if not any(leaf.kind == "reference" and leaf.value == usage_id for leaf in values):
                continue
            if view.in_lineage(candidate, CHARTER_CLASS):
                found.append(candidate)
    except IdentityNotFoundError as error:
        return (), f"charter declarations cannot be established: kernel-binding:{CHARTER_CLASS}: {error}"
    return _ordered(view, found), ""


def _declared_phases(view: ModelView, charter: str) -> tuple[tuple[str, ...] | None, list[str]]:
    index = view.index
    diagnostics: list[str] = []
    try:
        phase_root = view.kernel_element(PHASE_CLASS)
    except IdentityNotFoundError as error:
        return None, [f"applicable phases cannot be read: kernel-binding:{PHASE_CLASS}: {error}"]
    values = index.feature_values(charter, "applicablePhases")
    if not values:
        return None, ["the charter declares no applicable phases"]
    phases: list[str] = []
    for leaf in values:
        literal = leaf.value if leaf.kind == "reference" else None
        if literal is None or index.owner_of(literal) != phase_root:
            diagnostics.append(f"applicable phase value {leaf.value!r} is not a MethodPhase literal")
            continue
        name = index.name_of(literal)
        if name and name not in phases:
            phases.append(name)
    return tuple(phases), diagnostics


def _subject_types(view: ModelView, requirement: str) -> set[str]:
    types: set[str] = set()
    for relationship in view.index.owned_relationships(requirement, "SubjectMembership"):
        for member in reference_ids(relationship.get("memberElement")):
            types |= view.index.typed_by(member)
    return types


def _requirement_populations(
    view: ModelView, definition_ids: Sequence[str], problems: dict[str, tuple[str, str]]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not definition_ids:
        return (), ()
    wanted = set(definition_ids)
    subjects = [
        candidate
        for candidate in view.index.elements_of_type("RequirementUsage")
        if _subject_types(view, candidate) & wanted
    ]
    needs: list[str] = []
    requirements: list[str] = []
    try:
        needs = [candidate for candidate in subjects if view.in_lineage(candidate, NEED_CLASS)]
    except IdentityNotFoundError as error:
        problems[SELECTOR_NEEDS] = (PROBLEM_UNAVAILABLE, f"kernel-binding:{NEED_CLASS}: {error}")
    try:
        requirements = [
            candidate
            for candidate in subjects
            if candidate not in needs
            and view.in_lineage(candidate, REQUIREMENT_CLASS)
            and not view.in_lineage(candidate, EVIDENCE_CONTRACT_CLASS)
        ]
    except IdentityNotFoundError as error:
        problems[SELECTOR_REQUIREMENTS] = (PROBLEM_UNAVAILABLE, f"kernel-binding: {error}")
    return tuple(needs), tuple(requirements)


def _verification_packages(
    view: ModelView, usage_id: str | None, package_id: str | None
) -> tuple[str, ...]:
    if usage_id is None or package_id is None:
        return ()
    index = view.index
    referencing = []
    for holder in index.referencing_holders(usage_id):
        owner = index.owner_of(holder)
        if owner and str(index.element(owner).get("@type")) in {"Package", "LibraryPackage"}:
            if owner != package_id:
                referencing.append(owner)
    return (package_id, *_ordered(view, referencing))
