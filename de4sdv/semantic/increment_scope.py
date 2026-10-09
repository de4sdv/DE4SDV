"""Increment resolution from the model: identity, charter declaration, scope.

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
- the increment's own package: the package that owns the increment usage
  (and its charter), whose directly owned elements are the framing step's
  scope;
- the increment's scope: the top-level packages the charter declares in
  ``expectedArtifacts`` (String values matched to the declared names of
  top-level packages, exactly and uniquely), with every element they own
  through nested packages. Features of those elements (for example the
  framed-concern members of a need) are not scope elements. A declared name
  without exactly one top-level package leaves the scope unresolved (a
  problem), never narrower.

An identity that cannot be established (for example a missing kernel binding
or an ambiguous identifier) is recorded as a problem, never as an empty scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from de4sdv.sysml_api.errors import IdentityNotFoundError

from .revision_index import RevisionIndex

#: ``INC-<SUBJECT>-<SEQ>[<letter>][-<SUBSEQ>...]`` (naming conventions §4).
_INCREMENT_ID = re.compile(r"\AINC-[A-Z][A-Z0-9]*-[0-9]+[A-Z]?(?:-[0-9A-Z]+)*\Z")

#: Keys of :attr:`IncrementScope.problems`: the increment's identity, its declared scope.
IDENTITY_PROBLEM = "increment"
SCOPE_PROBLEM = "scope"

#: Kernel classes the resolution grounds in (ontology class names).
INCREMENT_CLASS = "EngineeringIncrement"
CHARTER_CLASS = "IncrementTraceObligations"
PHASE_CLASS = "MethodPhase"
#: Charter attribute naming the increment's packages.
SCOPE_ATTRIBUTE = "expectedArtifacts"
_PACKAGE_TYPES = ("Package", "LibraryPackage")

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

    def source_of(self, identifier: str | None) -> str:
        return str(self.sources.get(identifier or "", ""))

    def describe(self, identifier: str | None) -> dict[str, str]:
        """Display record of one element: name, qualified name, short name.

        Source files are input-dependent (an export records them, an API
        listing does not) and are reported separately as presentation data.
        """
        element = self.element(identifier)
        record = {
            "element_id": str(identifier or ""),
            "name": self.index.name_of(identifier),
            "qualified_name": self.index.qualified_name(identifier),
        }
        short = element.get("declaredShortName")
        if short:
            record["short_name"] = str(short)
        return record

    def top_package(self, identifier: str | None) -> str | None:
        """The outermost owning package of an element (its model module)."""
        current, found, seen = identifier, None, set()
        while current and current not in seen:
            seen.add(current)
            if str(self.element(current).get("@type")) in {"Package", "LibraryPackage"}:
                found = current
            current = self.index.owner_of(current)
        return found


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
    #: The packages the charter declares in ``expectedArtifacts``, in declared order.
    scope_packages: tuple[str, ...] = ()
    #: Every element those packages own through nested packages.
    scope_elements: tuple[str, ...] = ()
    #: The elements the increment's own package (the owner of the increment
    #: usage and its charter) owns directly: the scope of the framing step.
    own_elements: tuple[str, ...] = ()
    problems: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()


def resolve_increment(view: ModelView, increment_id: str) -> IncrementScope:
    """Resolve the increment, its charter and its scope from the model."""
    identifier = parse_increment_id(increment_id)
    index = view.index
    diagnostics: list[str] = []
    problems: dict[str, tuple[str, str]] = {}

    holders = sorted(index.with_short_name(identifier))
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
        problems[IDENTITY_PROBLEM] = (PROBLEM_UNAVAILABLE, f"kernel-binding:{INCREMENT_CLASS}: {error}")
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
        problems[IDENTITY_PROBLEM] = (PROBLEM_INVALID, detail)

    definition_ids: tuple[str, ...] = ()
    package_id: str | None = None
    charters: tuple[str, ...] = ()
    declared_phases: tuple[str, ...] | None = None
    scope_packages: tuple[str, ...] = ()
    scope_elements: tuple[str, ...] = ()
    own_elements: tuple[str, ...] = ()
    if usage_id is not None:
        definition_ids = tuple(sorted(index.typed_by(usage_id)))
        package_id = index.owner_of(usage_id)
        own_elements = _ordered(view, index.owned_members(package_id)) if package_id else ()
        charters, charter_problem = _charters(view, usage_id)
        if charter_problem:
            diagnostics.append(charter_problem)
        scope_problem = ""
        if len(charters) == 1:
            declared_phases, phase_diagnostics = _declared_phases(view, charters[0])
            diagnostics.extend(phase_diagnostics)
            packages, unresolved = declared_artifacts(view, charters[0])
            scope_packages = tuple(packages)
            scope_elements = _ordered(view, [e for package in packages for e in _package_contents(view, package)])
            if unresolved or not packages:
                scope_problem = (f"{SCOPE_ATTRIBUTE} {', '.join(unresolved)} name no single top-level package"
                                 if unresolved else f"the charter declares no {SCOPE_ATTRIBUTE}")
        else:
            scope_problem = (f"{len(charters)} charter declarations reference the increment"
                             if charters else "no charter declaration references the increment")
        if scope_problem:
            detail = f"{scope_problem}; applicable phases and scope beyond the increment's package are unresolved"
            diagnostics.append(detail)
            problems[SCOPE_PROBLEM] = (PROBLEM_UNAVAILABLE, detail)

    if usage_id is None:
        problems.setdefault(
            IDENTITY_PROBLEM,
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
        scope_packages=scope_packages,
        scope_elements=scope_elements,
        own_elements=own_elements,
        problems=problems,
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


def applicable_phase_literals(view: ModelView, charter: str) -> tuple[list[str], list[str]]:
    """The MethodPhase literals a charter declares applicable, and the values that are not literals.

    Raises :class:`IdentityNotFoundError` when MethodPhase has no validated kernel binding.
    """
    phase_root = view.kernel_element(PHASE_CLASS)
    literals: list[str] = []
    foreign: list[str] = []
    for leaf in view.index.feature_values(charter, "applicablePhases"):
        if leaf.kind == "reference" and view.index.owner_of(leaf.value) == phase_root:
            if leaf.value not in literals:
                literals.append(leaf.value)
        else:
            foreign.append(str(leaf.value))
    return literals, foreign


def _declared_phases(view: ModelView, charter: str) -> tuple[tuple[str, ...] | None, list[str]]:
    try:
        literals, foreign = applicable_phase_literals(view, charter)
    except IdentityNotFoundError as error:
        return None, [f"applicable phases cannot be read: kernel-binding:{PHASE_CLASS}: {error}"]
    if not literals and not foreign:
        return None, ["the charter declares no applicable phases"]
    diagnostics = [f"applicable phase value {value!r} is not a MethodPhase literal" for value in foreign]
    return tuple(view.index.name_of(literal) for literal in literals), diagnostics


def _top_level_packages(view: ModelView) -> dict[str, list[str]]:
    """Declared name -> top-level packages (owned by a root namespace, or by nothing)."""

    def build() -> dict[str, list[str]]:
        index = view.index
        found: dict[str, list[str]] = {}
        for package in index.elements_of_type(*_PACKAGE_TYPES):
            owner = index.owner_of(package)
            if owner is not None and str(index.element(owner).get("@type")) != "Namespace":
                continue
            name = str(index.element(package).get("declaredName") or "")
            if name:
                found.setdefault(name, []).append(package)
        return found

    return view.index.memo("top-level-packages", build)


def _package_contents(view: ModelView, package: str) -> list[str]:
    """Every element ``package`` owns, descending into nested packages only."""
    found: list[str] = []
    frontier, seen = [package], set()
    while frontier:
        current = frontier.pop(0)
        if current in seen:
            continue
        seen.add(current)
        for member in view.index.owned_members(current):
            found.append(member)
            if str(view.index.element(member).get("@type")) in _PACKAGE_TYPES:
                frontier.append(member)
    return found


def declared_artifacts(view: ModelView, charter: str) -> tuple[list[str], list[str]]:
    """The top-level packages the charter's ``expectedArtifacts`` name, and the values naming no single one."""
    packages_by_name = _top_level_packages(view)
    packages: list[str] = []
    unresolved: list[str] = []
    for leaf in view.index.feature_values(charter, SCOPE_ATTRIBUTE):
        name = str(leaf.value or "").strip() if leaf.kind == "string" else ""
        matches = packages_by_name.get(name, [])
        if len(matches) != 1:
            unresolved.append(f"{leaf.value!r} ({len(matches)} top-level packages)")
        elif matches[0] not in packages:
            packages.append(matches[0])
    return packages, unresolved
