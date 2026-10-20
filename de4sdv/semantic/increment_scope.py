"""Increment resolution from the model: identity, charter declaration, scope.

An engineering increment is identified only by its registered identifier
(``INC-<SUBJECT>-<SEQ>``, docs/naming/naming-conventions.md) carried as the
declared short name of a part usage in the EngineeringIncrement lineage.
Lineage is validated kernel identity (ingestion-validated kernel bindings,
ADR 0011); element names never identify anything here.

From the identified usage the resolution reads, through native
relationships only:

- the increment definitions (the usage's typing) and the increment package
  (the usage's owning namespace). The increment's own definitions are the
  ones among them other than the kernel EngineeringIncrement itself
  (:func:`own_increment_definitions`); the method's form declares one,
  specializing the kernel definition, and types the usage by it;
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
  problem), never narrower. Nothing else puts an element in scope: neither
  a subject typed by the increment nor a ``references`` to the increment
  usage. The scope closure (:func:`scope_closure`) adds what those packages
  own at any depth, except parameters, ends and references to other features
  (by their native feature fields): the elements a step parameter typed by an
  architecture class counts;
- the increment's system of interest: the usages the charter references in
  ``systemOfInterest`` (optional), the entity the increment's needs and
  requirements take as subject, and the definitions typing them.

An identity that cannot be established (for example a missing kernel binding
or an ambiguous identifier) is recorded as a problem, never as an empty scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from de4sdv.sysml_api.repository import reference_ids

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
#: Charter feature referencing the increment usage.
INCREMENT_ATTRIBUTE = "increment"
#: Charter attribute listing the MethodPhase literals the increment applies.
PHASES_ATTRIBUTE = "applicablePhases"
#: Charter attribute naming the increment's packages.
SCOPE_ATTRIBUTE = "expectedArtifacts"
#: Charter feature referencing the increment's system of interest (optional).
SYSTEM_OF_INTEREST_ATTRIBUTE = "systemOfInterest"
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
        library_bindings: Mapping[str, str] | None = None,
        library_problems: Mapping[str, str] | None = None,
    ) -> None:
        self.elements = elements
        self.traversal = traversal
        self.sources: Mapping[str, str] = sources or {}
        #: Library pin -> element, bound by the loader's file-mapped rule (an export only).
        self.library_bindings: Mapping[str, str] = library_bindings or {}
        self.library_problems: Mapping[str, str] = library_problems or {}
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

    def library_element(self, pin: str) -> str:
        """The element a library pin is bound to: by the loader of an export, with ADR 0011's file-mapped
        rule (metatype, declared name, serializer-recorded source document). Raises when it is unbound,
        for example over the API, where no pin is bound."""
        element = self.library_bindings.get(pin)
        if element is None or element not in self.index.by_id:
            why = self.library_problems.get(pin) or "no library binding in this evaluation"
            raise IdentityNotFoundError(f"library pin {pin!r} is unbound: {why}")
        return element

    def source_of(self, identifier: str | None) -> str:
        return str(self.sources.get(identifier or "", ""))

    @property
    def names(self) -> QualifiedNameIndex:
        """The corpus's KerML qualified names, computed from ownership (built once per corpus,
        shared with the identity answers, which memoize the same index under the same key)."""
        index = self.index
        return index.memo("qualified-names", lambda: QualifiedNameIndex(index.elements, by_id=index.by_id))

    def qualified_name(self, identifier: str | None) -> str | None:
        """The qualified name an answer prints: computed from ownership, quoted where needed, and
        resolvable by ``resolve_element``/``inspect_element``; ``None`` when the element has no
        complete chain of named owners (it is never guessed)."""
        return self.names.qualified_name(identifier)

    def label(self, identifier: str | None) -> str:
        """The qualified name of an element, else its identifier (which also resolves)."""
        return self.qualified_name(identifier) or str(identifier or "")

    def describe(self, identifier: str | None) -> dict[str, Any]:
        """Display record of one element: name, qualified name, short name.

        Source files are input-dependent (an export records them, an API
        listing does not) and are reported separately as presentation data.
        """
        element = self.element(identifier)
        record = {
            "element_id": str(identifier or ""),
            "name": self.index.name_of(identifier),
            "qualified_name": self.qualified_name(identifier),
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
    #: The usages the charter references in ``systemOfInterest``, in declared order.
    system_of_interest: tuple[str, ...] = ()
    #: The definitions typing the charter's ``systemOfInterest`` feature or the usages it references.
    system_of_interest_types: tuple[str, ...] = ()
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
            f"{view.label(holder)} carries the declared short name "
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
    system_of_interest: tuple[str, ...] = ()
    system_of_interest_types: tuple[str, ...] = ()
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
            usages, types = declared_system_of_interest(view, charters[0])
            system_of_interest, system_of_interest_types = tuple(usages), tuple(types)
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
        usage_id=usage_id,
        definition_ids=definition_ids,
        package_id=package_id,
        charters=charters,
        declared_phases=declared_phases,
        scope_packages=scope_packages,
        scope_elements=scope_elements,
        own_elements=own_elements,
        system_of_interest=system_of_interest,
        system_of_interest_types=system_of_interest_types,
        problems=problems,
        diagnostics=tuple(diagnostics),
    )


def _ordered(view: ModelView, identifiers: Sequence[str]) -> tuple[str, ...]:
    """Distinct identifiers in a corpus-order-independent order.

    An API listing and an export of the same revision may enumerate elements
    differently; the ownership path of named owners, then the element identifier,
    is stable for both. The path is an ordering key only, never a printed name.
    """
    unique = list(dict.fromkeys(identifiers))
    return tuple(sorted(unique, key=lambda item: (view.index.qualified_name(item), item)))


def _charters(view: ModelView, usage_id: str) -> tuple[tuple[str, ...], str]:
    index = view.index
    found: list[str] = []
    try:
        for candidate in index.elements_of_type("PartUsage"):
            values = index.feature_values(candidate, INCREMENT_ATTRIBUTE)
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
    for leaf in view.index.feature_values(charter, PHASES_ATTRIBUTE):
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


#: Memberships whose member is a parameter or a connector end, never an element of the increment.
_PARAMETER_MEMBERSHIPS = ("ParameterMembership", "SubjectMembership", "ActorMembership", "StakeholderMembership",
                          "ReturnParameterMembership", "EndFeatureMembership")


def ordered(view: ModelView, identifiers: Sequence[str]) -> tuple[str, ...]:
    """Distinct identifiers in the corpus-order-independent order the scope uses."""
    return _ordered(view, identifiers)


def declares_no_element(view: ModelView, element: str) -> bool:
    """Whether a feature is a parameter, an end or a reference to another feature, never an element of
    the increment's architecture. The native feature fields decide, not the owning membership: an
    export owns a definition's parameters and ends through FeatureMembership, with ``direction`` set
    or ``isEnd`` true. A usage with an authored ReferenceSubsetting (``perform x;``, a reference to
    another feature) names that feature; it declares none of its own."""
    found = view.index.element(element)
    if found.get("direction") or found.get("isEnd") is True:
        return True
    return any(not relationship.get("isImplied")
               for relationship in view.index.owned_relationships(element, "ReferenceSubsetting"))


def scope_closure(view: ModelView, scope: IncrementScope) -> tuple[str, ...]:
    """Every element the charter's packages own at any depth: nested packages, usages, definitions
    and the features they own, except parameters, ends and references to other features
    (:func:`declares_no_element`), and what those own.

    The scope (:attr:`IncrementScope.scope_elements`) holds what the packages own directly; this
    closure also holds, for example, the action features of a functional-flow definition and the
    parts of a logical system's definition, which a step parameter typed by an architecture class
    counts. Built once per corpus and package set.
    """
    packages = tuple(scope.scope_packages)

    def build() -> tuple[str, ...]:
        index = view.index
        found: list[str] = []
        frontier, seen = list(packages), set(packages)
        while frontier:
            current = frontier.pop()
            for relationship in index.owned_relationships(current):
                if str(relationship.get("@type") or "") in _PARAMETER_MEMBERSHIPS:
                    continue
                for member in reference_ids(relationship.get("ownedRelatedElement")):
                    if member in index.by_id and member not in seen:
                        seen.add(member)
                        if declares_no_element(view, member):
                            continue
                        found.append(member)
                        frontier.append(member)
        return _ordered(view, found)

    return view.index.memo(("scope-closure", packages), build)


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


def declared_system_of_interest(view: ModelView, charter: str) -> tuple[list[str], list[str]]:
    """The usages the charter's ``systemOfInterest`` references, and the definitions typing
    that feature or those usages. Both are empty when the charter declares none."""
    usages: list[str] = []
    for leaf in view.index.feature_values(charter, SYSTEM_OF_INTEREST_ATTRIBUTE):
        if leaf.kind == "reference" and leaf.value in view.index.by_id and leaf.value not in usages:
            usages.append(leaf.value)
    feature = view.index.feature(charter, SYSTEM_OF_INTEREST_ATTRIBUTE)
    types: set[str] = set(view.index.typed_by(feature)) if feature is not None else set()
    for usage in usages:
        types |= view.index.typed_by(usage)
    return usages, sorted(types)


def own_increment_definitions(view: ModelView, types: Iterable[str]) -> tuple[str, ...]:
    """The increment's own definitions among ``types`` (the typing of a usage): the definitions in the
    EngineeringIncrement lineage other than the kernel EngineeringIncrement itself, known by its
    validated kernel binding, never by name (ADR 0011). A usage typed by the kernel definition alone
    has none. Raises :class:`IdentityNotFoundError` when EngineeringIncrement has no validated binding."""
    kernel = view.kernel_element(INCREMENT_CLASS)
    lineage = view.index.specializations(kernel)
    return tuple(sorted(definition for definition in set(types) if definition != kernel and definition in lineage))


def typed_by_the_kernel_itself(view: ModelView, types: Iterable[str]) -> bool:
    """Whether a usage with ``types`` is typed by the kernel EngineeringIncrement itself (validated
    binding) and by no increment definition of its own: the form the increment checks refuse, which
    the remedies answer by teaching the method's form. False when the kernel binds no
    EngineeringIncrement (nothing is known to refuse)."""
    try:
        kernel = view.kernel_element(INCREMENT_CLASS)
    except IdentityNotFoundError:
        return False
    found = set(types)
    return kernel in found and not own_increment_definitions(view, found)
