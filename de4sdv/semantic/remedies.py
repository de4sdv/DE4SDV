"""What to author when a method check fails, built from the parameter the check is about.

A workflow step declares typed parameters (``out part charter :
IncrementCharter;``), and each method check is about one of them. The remedy
of a check is built from that parameter in the bound view, never from
``.sysml`` text and never from a type or package name written here (ADR 0011):

- the subject is declared with the parameter's SysML v2 keyword (``part``,
  ``requirement``, ``concern``, ``verification``); an untyped parameter's kind
  is a SysML metaclass, so the keyword alone declares it;
- a type is named by its qualified name, computed from ownership
  (:mod:`de4sdv.sysml_api.qualified_names`), with the ``private import
  <package>::*;`` of the package that owns it (none for the increment's own
  package);
- the types a check admits come from the check's own type test: the
  parameter's type or a definition specializing it, the classes a relation's
  contract mapping names (resolved through the validated kernel bindings), or,
  for a check that tests no type, any type, said as such;
- a member a check reads (``owner``, ``increment``, ``source`` ...) is the
  member the check itself names, declared with the keyword of the feature it
  redefines (``attribute``, ``ref part``);
- what something references is declared first: the charter holds its
  ``increment`` reference, a scenario precedes its connection, a concern its
  frame; a requirement, concern or viewpoint with stakeholder members declares
  its subject first;
- only an element that doesn't exist yet is declared, with its members in its
  block (a new charter's ``systemOfInterest``, a new need's subject); a line
  for an existing element stands alone and never declares it again: the
  instruction names the element, or the text puts "in the existing <qualified
  name>:" before it, or "replace the subject of <qualified name> with:" for a
  subject (SysML allows one per requirement);
- a population remedy declares the element the check counts first and
  complete, then the lines its check needs besides it (``then:``).

Placeholders in angle brackets are names or text the author chooses, or a
value from a list the remedy gives; never a type. A remedy says what to
author, never that authoring it proves anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Mapping, Sequence

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from .element_description import ElementDescriber, USAGE_KEYWORDS
from .increment_scope import (
    CHARTER_CLASS,
    INCREMENT_CLASS,
    PHASE_CLASS,
    IncrementScope,
    ModelView,
    declared_artifacts,
    own_increment_definitions,
    typed_by_the_kernel_itself,
)
from .model_edges import DEFINITION_END_FAMILIES, END_FAMILIES
from de4sdv.sysml_api.qualified_names import escape_name

from .relation_checks import (
    NEXT_ACTION_PLACEHOLDER,
    OWNER_PLACEHOLDER,
    REASON_PLACEHOLDER,
    SEMANTIC_SOURCE_PLACEHOLDER,
    SIGNAL_CARRIERS,
    SIGNAL_MAPPING,
    SIGNAL_MAPPING_DISPOSITION,
    SIGNAL_MAPPING_RECORD,
    MethodSideInput,
    mapping_records,
    signal_mappings,
    stated_texts,
)

#: Ontology classes whose validated kernel bindings name a type a remedy needs (binding keys).
STAKEHOLDER_CLASS = "Stakeholder"
PROBLEM_STATEMENT_CLASS = "ProblemStatement"
NEED_CLASS = "Need"
REQUIREMENT_CLASS = "Requirement"
_PACKAGES = ("Package", "LibraryPackage")

#: The name the author gives the increment's own definition (declared by the remedy that uses it).
INCREMENT_DEFINITION = "<IncrementDefinitionName>"
_OWN_DEFINITION = "the increment's own definition specializes it"
SUBJECT_FIRST = ("Subject first: a requirement, concern or viewpoint with stakeholder or actor members declares "
                 "its subject before them (Syside: requirement-usage-subject-parameter-position).")
_SPECIALIZING = "this definition or a definition specializing it"


@dataclass(frozen=True)
class Remedy:
    """What to author for one check: an instruction, the SysML lines in declaration order, the imports
    those lines need, the types they name (with what the check admits), and notes."""

    instruction: str
    declarations: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()
    types: tuple[Mapping[str, Any], ...] = ()
    notes: tuple[str, ...] = ()
    #: The MethodPhase literals, for a remedy that sets applicable phases.
    phases: tuple[Mapping[str, Any], ...] = ()
    #: For a population remedy: the index of the first line after the counted element, which the
    #: text introduces with "then:".
    then_from: int | None = None
    #: Lines that go into an element that already exists, each with the phrase the text puts before
    #: it ("in the existing <qualified name>:", "replace the subject of <qualified name> with:").
    placed: tuple[tuple[str, str], ...] = ()
    #: Bookkeeping, not part of ``authoring``: the subject's own declaration among the lines, or the
    #: name the lines give the subject when they refer to it without declaring it.
    subject_line: str | None = field(default=None, compare=False, repr=False)
    subject_name: str | None = field(default=None, compare=False, repr=False)

    @property
    def text(self) -> str:
        """The one-line ``what_to_author``: instruction, lines, imports and notes."""
        placed, lines = dict(self.placed), []
        for index, line in enumerate(self.declarations):
            if self.then_from and index == self.then_from:
                lines.append("then:")
            lines.extend([placed[line], line] if line in placed else [line])
        parts = [self.instruction + (": " + " ".join(lines) if lines else "")]
        if self.imports:
            parts.append("Import: " + " ".join(self.imports))
        parts.extend(self.notes)
        return " ".join(part for part in parts if part)

    def authoring(self) -> dict[str, Any]:
        """The structured form of the remedy (the answers' ``authoring`` field)."""
        record: dict[str, Any] = {
            "declarations": list(self.declarations),
            "imports": list(self.imports),
            "types": [dict(item) for item in self.types],
            "notes": list(self.notes),
        }
        if self.phases:
            record["phases"] = [dict(item) for item in self.phases]
        return record


EMPTY = Remedy("")


@dataclass(frozen=True)
class _Request:
    view: ModelView
    check: str
    subject: str | None
    parameter: str | None
    framing: bool | None
    scope: IncrementScope | None
    checked_phases: tuple[str, ...]
    #: Every step parameter the workflow's checks are about (a new charter is typed like the charter's).
    parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Type:
    """A type a remedy names: by its qualified name (else its name), with its owning package."""

    element: str
    qualified_name: str | None
    name: str
    package: str | None  # the owning package's element id
    package_name: str | None  # its qualified name

    @property
    def ref(self) -> str:
        return self.qualified_name or self.name


@dataclass
class _Lines:
    """Remedy lines being assembled, with the types they name."""

    request: _Request
    declarations: list[str]
    types: list[tuple[_Type, str]]  # (type, what the check admits)
    notes: list[str]
    subject_line: str | None = None  # the subject's own declaration, when the lines declare it
    subject_name: str | None = None  # the name the lines give the subject without declaring it
    placed: dict[str, str] = field(default_factory=dict)  # line -> the existing element it goes into

    def type(self, element: str | None, admits: str = "") -> str:
        """The reference to a type in a line (recorded for the imports and the types list)."""
        if element is None:
            return ""
        named = _type(self.request.view, element)
        if all(named.element != seen.element for seen, _admits in self.types):
            self.types.append((named, admits))
            if named.qualified_name is None:
                self.notes.append(f"{named.name} has no qualified name in this revision (an owner outside it), "
                                  "so no import is named for it.")
        return named.ref

    def remedy(self, instruction: str, *, phases: Sequence[Mapping[str, Any]] = ()) -> Remedy:
        own = self.request.scope.package_id if self.request.scope else None
        first = _one_type(self.request.view, self.request.parameter)  # the subject's type leads
        ordered = sorted(self.types, key=lambda item: item[0].element != first)
        imports = list(dict.fromkeys(
            f"private import {named.package_name}::*;" for named, _admits in ordered
            if named.package_name and named.package != own))
        types = tuple({"qualified_name": named.qualified_name, "name": named.name, "element_id": named.element,
                       **({"admits": admits} if admits else {})} for named, admits in self.types)
        return Remedy(instruction, tuple(self.declarations), tuple(imports), types,
                      tuple(dict.fromkeys(self.notes)), tuple(phases), placed=tuple(self.placed.items()),
                      subject_line=self.subject_line, subject_name=self.subject_name)


# ---------------------------------------------------------------------------
# Reading the view
# ---------------------------------------------------------------------------


def _describer(view: ModelView) -> ElementDescriber:
    return ElementDescriber(view.index, view.names)


def _owning_package(view: ModelView, element: str) -> str | None:
    seen = {element}
    current = view.index.owner_of(element)
    while current and current not in seen:
        seen.add(current)
        if str(view.element(current).get("@type") or "") in _PACKAGES:
            return current
        current = view.index.owner_of(current)
    return None


def _type(view: ModelView, element: str) -> _Type:
    package = _owning_package(view, element)
    return _Type(element, view.qualified_name(element), view.index.name_of(element) or element,
                 package, view.qualified_name(package) if package else None)


def _kernel(view: ModelView, ontology_class: str) -> str | None:
    """The validated kernel element of an ontology class (None when it has no binding)."""
    try:
        return view.kernel_element(ontology_class)
    except IdentityNotFoundError:
        return None


def _one_type(view: ModelView, usage: str | None) -> str | None:
    types = sorted(view.index.typed_by(usage)) if usage else []
    return types[0] if len(types) == 1 else None


def _keyword(view: ModelView, element: str | None) -> str | None:
    """The SysML v2 keyword that declares ``element``, as ``inspect_element`` reports it (``ref part``
    for a referential part usage)."""
    return _describer(view).keyword(element) if element else None


def _parameter_keyword(request: _Request, container: str = "part") -> str:
    """The keyword that declares a subject: the parameter's usage keyword (``part``, ``concern`` ...);
    without a parameter, ``container``, the kind of element that can hold the members a remedy gives."""
    if not request.parameter:
        return container
    return USAGE_KEYWORDS.get(str(request.view.element(request.parameter).get("@type") or ""), container)


def _holders(request: _Request) -> list[str]:
    """The definitions whose features a subject has: the subject's types, else the parameter's type."""
    view = request.view
    if request.subject is not None:
        types = sorted(view.index.typed_by(request.subject))
    else:
        types = [t for t in [_one_type(view, request.parameter)] if t]
    found: list[str] = []
    for definition in types:
        found.extend(general for general in view.index.generals(definition) if general not in found)
    return found


def _member(request: _Request, name: str, definitions: Sequence[str] | None = None) -> tuple[str | None, list[str]]:
    """The feature named ``name`` the subject's definitions (or ``definitions``) declare, nearest first,
    and every distinct one of that name that no other redefines (more than one: the name is ambiguous)."""
    view = request.view
    found: list[str] = []
    for definition in (_holders(request) if definitions is None else definitions):
        feature = view.index.feature(definition, name)
        if feature is not None and feature not in found:
            found.append(feature)
    redefined = {target for feature in found for target in view.index.redefined(feature)}
    distinct = [feature for feature in found if feature not in redefined]
    return (distinct[0] if distinct else None), distinct


def _in_lineage(view: ModelView, definitions: Iterable[str], ontology_class: str) -> bool:
    kernel = _kernel(view, ontology_class)
    if kernel is None:
        return False
    lineage = view.index.specializations(kernel)
    return any(definition in lineage for definition in definitions)


def _subject_types(request: _Request) -> list[str]:
    view = request.view
    if request.subject is not None:
        return sorted(view.index.typed_by(request.subject))
    return [t for t in [_one_type(view, request.parameter)] if t]


def _label(request: _Request, element: str | None, placeholder: str) -> str:
    return request.view.label(element) if element else placeholder


def _where(request: _Request) -> str:
    """Where the subject belongs: the increment's own package, or a package the charter names."""
    view, scope = request.view, request.scope
    if request.framing:
        package = scope.package_id if scope else None
        return f"in the increment's package {view.label(package)}" if package else "in the increment's package"
    if request.framing is False:
        packages = scope.scope_packages if scope else ()
        named = f" ({', '.join(view.label(p) for p in packages)})" if packages else ""
        return f"in a package named in the charter's expectedArtifacts{named}"
    return ""


def _subject_phrase(request: _Request) -> str:
    return request.view.label(request.subject) if request.subject else _parameter_phrase(request)


def _lines(request: _Request) -> _Lines:
    return _Lines(request, [], [], [])


def _declaration(lines: _Lines, members: Sequence[str] = (), *, name: str = "<name>",
                 short: str | None = None, doc: bool = False, container: str = "part") -> str:
    """``<keyword> [<'short'>] <name> [: <type>] { <members> }`` for the parameter's subject (without
    a parameter, a ``container`` that can hold the members)."""
    request = lines.request
    keyword = _parameter_keyword(request, container)
    parameter_type = _one_type(request.view, request.parameter)
    typed = f" : {lines.type(parameter_type, _SPECIALIZING)}" if parameter_type else ""
    body = [*(["doc /* <text> */"] if doc else []), *members]
    head = f"{keyword} {f'<{short}> ' if short else ''}{name}{typed}"
    lines.subject_line = f"{head} {{ {' '.join(body)} }}" if body else f"{head};"
    return lines.subject_line


def _subject_ref(lines: _Lines, placeholder: str) -> str:
    """How a line names the subject it does not declare: its qualified name, else ``placeholder``
    (recorded, so that a remedy declaring the subject first gives it that name)."""
    request = lines.request
    if request.subject is not None:
        return request.view.label(request.subject)
    lines.subject_name = placeholder
    return placeholder


# ---------------------------------------------------------------------------
# Subjects first
# ---------------------------------------------------------------------------


def _subjects(view: ModelView, element: str | None) -> int:
    """How many subjects an element declares (SubjectMemberships)."""
    return len(view.index.owned_relationships(element, "SubjectMembership")) if element else 0


def _has_subject(view: ModelView, element: str | None) -> bool:
    return _subjects(view, element) > 0


def _existing_member(lines: _Lines, element: str, member: str) -> str:
    """``member`` for an element that exists: the line alone, which the text puts "in the existing"
    element (never a second declaration of it)."""
    lines.placed[member] = f"in the existing {lines.request.view.label(element)}:"
    return member


def _subject_line(lines: _Lines, line: str) -> str:
    """A subject line for the existing element the remedy is about. When it has a subject, the line
    replaces it (SysML allows one; a second fails oneNativeSubject); without one, it is added."""
    request = lines.request
    count = _subjects(request.view, request.subject)
    if count:
        lines.placed[line] = f"replace the subject{'s' if count > 1 else ''} of {request.view.label(request.subject)} with:"
    return line


def _direct_note(view: ModelView, usage: str, kernel: str) -> str:
    return (f"{view.label(usage)} is typed by {view.label(kernel)} itself, which the checks refuse (the method's "
            f"form is the increment's own definition): retype the existing {view.label(usage)} to "
            f"`: {INCREMENT_DEFINITION}`, the increment's own definition that specializes it.")


def _increment_definition(lines: _Lines, general: str | None = None) -> str:
    """The increment's own definition, as the method declares it: the definition typing the resolved
    increment usage (qualified); else a part def the author names, declared first in the remedy and
    specializing ``general`` (the kernel's EngineeringIncrement, by its validated binding). A usage typed
    by the kernel definition itself fails the checks: for one, the remedy teaches the method's form, with
    a note that says to retype the existing usage."""
    request = lines.request
    view, scope = request.view, request.scope
    direct = scope is not None and bool(scope.definition_ids) and typed_by_the_kernel_itself(
        view, scope.definition_ids)
    if scope is not None and scope.definition_ids and not direct:
        # The increment's own definitions, as the checks read them (the lineage without the kernel
        # definition); the usage's definitions when that reading is empty or the kernel is unbound.
        try:
            own = list(own_increment_definitions(view, scope.definition_ids))
        except IdentityNotFoundError:
            own = []
        return lines.type((own or list(scope.definition_ids))[0], "the definition typing the increment usage")
    general = general or _kernel(view, INCREMENT_CLASS)
    if general is None:
        lines.notes.append("The kernel binds no EngineeringIncrement definition at this revision.")
        return INCREMENT_DEFINITION
    declaration = f"{_keyword(view, general)} {INCREMENT_DEFINITION} :> {lines.type(general, _OWN_DEFINITION)};"
    if declaration not in lines.declarations:
        lines.declarations.insert(0, declaration)
    if direct and scope is not None and scope.usage_id:
        lines.notes.append(_direct_note(view, scope.usage_id, _kernel(view, INCREMENT_CLASS) or general))
    return INCREMENT_DEFINITION


def _increment_subject(lines: _Lines) -> str:
    """``subject increment : <the increment's own definition>;`` (for a usage typed by the kernel
    definition itself, a note says to retype the existing usage)."""
    return f"subject increment : {_increment_definition(lines)};"


def _system_of_interest_subject(lines: _Lines) -> str:
    """``subject <name> :> <the declared system of interest>;`` (or by its type)."""
    scope = lines.request.scope
    if scope is not None and scope.system_of_interest:
        return f"subject <subjectName> :> {lines.request.view.label(scope.system_of_interest[0])};"
    if scope is not None and scope.system_of_interest_types:
        return f"subject <subjectName> : {lines.type(scope.system_of_interest_types[0])};"
    lines.notes.append("<systemUsage> is the system of interest the charter declares in systemOfInterest.")
    return "subject <subjectName> :> <systemUsage>;"


def _subject_first(lines: _Lines) -> str:
    """The subject an element declares first, by what the method's subject rules ask of its kind."""
    request = lines.request
    types = _subject_types(request)
    if _in_lineage(request.view, types, PROBLEM_STATEMENT_CLASS):
        return _increment_subject(lines)
    if _in_lineage(request.view, types, NEED_CLASS) or _in_lineage(request.view, types, REQUIREMENT_CLASS):
        return _system_of_interest_subject(lines)
    return "subject;"


def _stakeholder_line(lines: _Lines) -> str:
    stakeholder = _kernel(lines.request.view, STAKEHOLDER_CLASS)
    if stakeholder is None:
        lines.notes.append("The kernel binds no Stakeholder definition at this revision.")
        return "stakeholder <stakeholderName>;"
    reference = lines.type(stakeholder, _SPECIALIZING + "; the check tests no stakeholder type")
    return f"stakeholder <stakeholderName> : {reference};"


# ---------------------------------------------------------------------------
# Named checks
# ---------------------------------------------------------------------------


def _increment_short_name(request: _Request) -> Remedy:
    lines = _lines(request)
    identifier = request.scope.increment_id if request.scope else "INC-<SUBJECT>-<SEQ>"
    if request.subject is not None:
        view = request.view
        typed = sorted(view.index.typed_by(request.subject))
        kernel = _kernel(view, INCREMENT_CLASS)
        direct = kernel is not None and typed_by_the_kernel_itself(view, typed)
        label = view.label(request.subject)
        identified = f"with the increment identifier as its declared short name, <'{identifier}'>"
        if direct:  # the refused form: the increment's own definition, declared first, and the retyping
            lines.declarations.append(f"{_keyword(view, kernel)} {INCREMENT_DEFINITION} :> "
                                      f"{lines.type(kernel, _OWN_DEFINITION)};")
            lines.notes.append(_direct_note(view, request.subject, kernel))
            short = str(view.element(request.subject).get("declaredShortName") or "")
            return lines.remedy(f"declare the increment's own definition and retype the existing {label} by it"
                                + (f", {identified}" if short != identifier else ""))
        return lines.remedy(f"declare the existing {label} {identified}")
    definition = _increment_definition(lines, _one_type(request.view, request.parameter))
    lines.subject_line = f"{_parameter_keyword(request)} <'{identifier}'> <usageName> : {definition};"
    lines.declarations.append(lines.subject_line)
    return lines.remedy(f"declare the increment usage with its identifier as declared short name, typed by the "
                        f"increment's own definition, {_where(request)}")


def _member_line(lines: _Lines, member: str, value: str, *,
                 definitions: Sequence[str] | None = None) -> str | None:
    """``<keyword> :>> <member> = <value>;`` with the keyword of the feature ``member`` redefines. When
    the subject inherits several features of that name, none is picked (no rule here orders them): no
    line, and a note lists each one's qualified name."""
    request = lines.request
    feature, distinct = _member(request, member, definitions)
    if feature is None:
        lines.notes.append(f"No definition of the subject declares {member} in this revision's model "
                           "(method side), so its declaring keyword is unknown.")
        return None
    if len(distinct) > 1:
        view = request.view
        named = [view.qualified_name(candidate) or f"{view.index.name_of(candidate)} (no qualified name)"
                 for candidate in distinct]
        lines.notes.append(f"{member!r} is ambiguous here, where it names {len(distinct)} inherited features: "
                           f"{', '.join(named)}. No line redefines it, as no rule picks one: redefine the one "
                           "meant by its qualified name.")
        return None
    return f"{_keyword(request.view, feature)} :>> {member} = {value};"


def _sequence(request: _Request, member: str, values: Sequence[str]) -> str:
    feature, _distinct = _member(request, member)
    upper = None
    if feature is not None:
        try:
            bounds = request.view.index.multiplicity(feature)
        except Exception:  # noqa: BLE001 - an undecodable multiplicity is the workflow reader's finding
            bounds = None
        upper = bounds[1] if bounds else 1
    many = upper is None or (upper or 1) > 1
    return f"({', '.join(values)})" if many else values[0]


def _set_member(request: _Request, member: str, value: str, instruction: str = "set on") -> Remedy:
    """A check that reads one member value of its subject."""
    lines = _lines(request)
    line = _member_line(lines, member, value)
    if request.subject is not None:
        if line:
            lines.declarations.append(line)
        return lines.remedy(f"{instruction} {request.view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, [line] if line else [], name=_subject_name(request)))
    return lines.remedy(f"{instruction} {_parameter_phrase(request)} {_where(request)}".rstrip())


def _parameter_name(request: _Request) -> str:
    return request.view.index.name_of(request.parameter) if request.parameter else "subject"


def _single(request: _Request) -> bool:
    """Whether the parameter allows at most one subject."""
    if request.parameter is None:
        return False
    try:
        bounds = request.view.index.multiplicity(request.parameter) or (1, 1)
    except Exception:  # noqa: BLE001 - an undecodable multiplicity is the workflow reader's finding
        return False
    return bounds[1] == 1


def _parameter_phrase(request: _Request) -> str:
    """``the charter`` for a parameter of one subject, ``each of the needs`` for one of many."""
    name = _parameter_name(request)
    if request.parameter is None:
        return "each subject"
    return f"the {name}" if _single(request) else f"each of the {name}"


def _subject_name(request: _Request) -> str:
    """``<charterName>`` for a parameter of one subject (several remedies name the same element),
    ``<name>`` for a parameter of many."""
    return f"<{_parameter_name(request)}Name>" if _single(request) else "<name>"


def _check_member(check: Callable[..., Any] | None) -> str | None:
    return getattr(check, "member", None)


def _charter_references_increment(request: _Request) -> Remedy:
    member = _named_member(request)
    scope = request.scope
    usage = _label(request, scope.usage_id if scope else None, "<usageName>")
    lines = _lines(request)
    line = _member_line(lines, member, usage)
    if request.subject is not None:
        lines.declarations.extend([line] if line else [])
        return lines.remedy(f"reference the increment from {request.view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, [line] if line else [], name=_subject_name(request)))
    return lines.remedy(f"declare the charter {_where(request)}, after the increment usage, and reference the "
                        "increment from it")


def _named_member(request: _Request) -> str:
    from .method_checks import NAMED_CHECKS  # the member the check itself reads

    member = _check_member(NAMED_CHECKS.get(request.check))
    if member is None:
        raise KeyError(f"check {request.check!r} names no member")
    return member


def _value_of(request: _Request, member: str) -> str:
    """The value a remedy writes for a member the check reads."""
    if member == _member_of("charterExpectedArtifacts"):
        scope = request.scope
        own = scope and scope.usage_id and request.view.top_package(scope.usage_id)
        own_name = f'"{request.view.index.name_of(own)}"' if own else '"<the increment\'s package name>"'
        return _sequence(request, member, [own_name, '"<each other top-level package holding increment content>"'])
    if member == _member_of("charterExpectedReviewEvidence"):
        return _sequence(request, member, ['"<review evidence>"'])
    return _sequence(request, member, [f'"<{member}>"'])


def _member_of(check: str) -> str | None:
    from .method_checks import NAMED_CHECKS

    return _check_member(NAMED_CHECKS.get(check))


def _charter_value(request: _Request) -> Remedy:
    member = _named_member(request)
    return _set_member(request, member, _value_of(request, member))


def _library_value(request: _Request) -> Remedy:
    from .method_checks import NAMED_CHECKS

    check = NAMED_CHECKS[request.check]
    member = _check_member(check)
    allowed = tuple(getattr(check, "allowed", ()) or ())
    if allowed:
        value = '"<kind>"'
    elif member == _member_of("successCriteriaAttribute"):
        value = '"<the observable conditions under which verification shows the requirement is met>"'
    else:
        value = f'"<{member}>"'
    remedy = _set_member(request, str(member), value)
    if allowed:
        remedy = _with_note(remedy, f"<kind> is one of {', '.join(allowed)}.")
    return remedy


def _with_note(remedy: Remedy, note: str) -> Remedy:
    return replace(remedy, notes=(*remedy.notes, note))


def _applicable_phases(request: _Request) -> Remedy:
    view = request.view
    member = _named_member(request)
    lines = _lines(request)
    root = _kernel(view, PHASE_CLASS)
    literals = view.index.owned_members(root, "EnumerationUsage") if root else []
    phases = [{"literal": view.label(literal), "name": view.index.name_of(literal),
               "executable_checks": view.index.name_of(literal) in request.checked_phases}
              for literal in literals]
    line = _member_line(lines, member, "(<each phase the increment applies, from the literals below>)")
    if request.subject is not None:
        lines.declarations.extend([line] if line else [])
        instruction = f"set on {view.label(request.subject)}"
    else:
        lines.declarations.append(_declaration(lines, [line] if line else [], name=_subject_name(request)))
        instruction = f"set on {_parameter_phrase(request)} {_where(request)}"
    if root is not None:
        lines.type(root, "its literals, listed below")
    if phases:
        lines.notes.append("The MethodPhase literals in method order (* = executable checks at this revision): "
                           + ", ".join(f"{p['literal']}{' *' if p['executable_checks'] else ''}" for p in phases)
                           + ". A declared phase without executable checks is reported, never evaluated.")
    return lines.remedy(instruction, phases=phases)


def _expected_artifacts_cover_content(request: _Request) -> Remedy:
    from .method_checks import increment_content_outside_scope

    view, scope = request.view, request.scope
    member = _named_member(request)
    if request.subject is not None and scope is not None and scope.usage_id:
        try:
            outside = increment_content_outside_scope(view, scope)
        except Exception:  # noqa: BLE001 - a method-side input: the generic remedy below
            outside = {}
        if outside:
            packages, _unresolved = declared_artifacts(view, request.subject)
            names = [view.index.name_of(p) for p in packages] + sorted(view.index.name_of(p) for p in outside)
            lines = _lines(request)
            line = _member_line(lines, member, _sequence(request, member, [f'"{name}"' for name in names]))
            lines.declarations.extend([line] if line else [])
            return lines.remedy(f"add to the {member} of {view.label(request.subject)} every top-level package "
                                "holding increment content, or move that content into a named package")
    remedy = _set_member(request, member, _value_of(request, member))
    target = request.view.label(request.subject) if request.subject else f"{_parameter_phrase(request)}"
    return replace(remedy, instruction=(
        f"name in the {member} of {target} every top-level package holding increment content (elements "
        "connected by DerivesFromNeed to, verifying, or verified by the increment's elements, or referencing "
        "the increment usage), or move that content into a named package"))


def _problem_statement_subject(request: _Request) -> Remedy:
    lines = _lines(request)
    subject = _increment_subject(lines)
    lines.notes.append(SUBJECT_FIRST)
    if request.subject is not None:
        lines.declarations.append(_subject_line(lines, subject))
        return lines.remedy(f"keep {request.view.label(request.subject)} in the increment's package, its subject "
                            "first and typed by the increment definition")
    lines.declarations.append(_declaration(lines, [subject], name="<problemStatementName>", container="requirement"))
    return lines.remedy(f"declare the problem statement {_where(request)}, its subject typed by the increment's "
                        "own definition")


def _owned_by_increment_package(request: _Request) -> Remedy:
    lines = _lines(request)
    if request.subject is not None:
        return lines.remedy(f"declare {request.view.label(request.subject)} in the increment's package")
    lines.declarations.append(_declaration(lines, name=_subject_name(request), doc=True))
    return lines.remedy(f"declare {_where(request) or 'in the increment package'}")


def _stakeholder_member(request: _Request) -> Remedy:
    lines = _lines(request)
    view = request.view
    members = [] if _has_subject(view, request.subject) else [_subject_first(lines)]
    members.append(_stakeholder_line(lines))
    lines.notes.append(SUBJECT_FIRST)
    if request.subject is not None:
        lines.declarations.extend(members)
        after = ", after its subject" if _has_subject(view, request.subject) else ""
        return lines.remedy(f"add to {view.label(request.subject)}{after}")
    lines.declarations.append(_declaration(lines, members, name=_subject_name(request), container="requirement"))
    return lines.remedy(f"declare {_parameter_phrase(request)} with a stakeholder member, its subject first, "
                        f"{_where(request)}".rstrip(", "))


def _concern_declaration(lines: _Lines, name: str = "<concernName>") -> str:
    return f"concern {name} {{ subject; {_stakeholder_line(lines)} }}"


def _framed_by_increment_view(request: _Request) -> Remedy:
    lines = _lines(request)
    concern = request.view.label(request.subject) if request.subject else "<concernName>"
    if request.subject is None:
        lines.subject_line = _concern_declaration(lines)  # the concern is the subject
        lines.declarations.append(lines.subject_line)
        lines.notes.append(SUBJECT_FIRST)
    lines.declarations.append("viewpoint def <ViewpointName> { doc /* <what the view shows> */ }")
    lines.declarations.append(f"view <viewName> {{ viewpoint <viewpointName> : <ViewpointName> "
                              f"{{ frame {concern}; }} }}")
    lines.notes.append("The check reads the view, its viewpoint and the frame; it tests no viewpoint or concern "
                       "type.")
    if request.subject is not None:
        return lines.remedy(f"frame {concern} by a viewpoint of a view {_where(request) or 'in its package'}")
    return lines.remedy(f"declare a concern and frame it by a viewpoint of a view, {_where(request)}".rstrip(", "))


def _require_constraint(request: _Request) -> Remedy:
    lines = _lines(request)
    statement = 'require constraint statement { language "English" /* <the statement> */ }'
    if request.subject is not None:
        lines.declarations.append(statement)
        return lines.remedy(f"add the statement to {request.view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, [statement], name=_subject_name(request), container="requirement"))
    return lines.remedy(f"declare {_parameter_phrase(request)} with its statement {_where(request)}".rstrip())


def _one_native_subject(request: _Request) -> Remedy:
    lines = _lines(request)
    subject = _subject_first(lines)
    if request.subject is not None:
        lines.declarations.append(_subject_line(lines, subject))
        several = _subjects(request.view, request.subject) > 1
        return lines.remedy(f"{'keep' if several else 'declare'} exactly one subject on "
                            f"{request.view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, [subject], name=_subject_name(request), container="requirement"))
    return lines.remedy(f"declare {_parameter_phrase(request)} with exactly one subject {_where(request)}".rstrip())


def _subject_is_system_of_interest(request: _Request) -> Remedy:
    """The system of interest as the subject. Each line sits in its container: the charter's
    systemOfInterest in the charter's block, the subject in the need's or requirement's block (on its
    own only for an existing one, which the instruction names)."""
    lines = _lines(request)
    scope = request.scope
    declared = scope is not None and bool(scope.system_of_interest or scope.system_of_interest_types)
    if not declared:
        lines.declarations.extend(["part def <SystemName> { doc /* <the system of interest> */ }",
                                   "part <systemUsage> : <SystemName>;"])
        line = _member_line(lines, _named_member(request), "<systemUsage>", definitions=_charter_definitions(request))
        if line:
            lines.declarations.append(_in_charter(lines, line))
    subject = _system_of_interest_subject(lines)
    if request.subject is not None:
        lines.declarations.append(_subject_line(lines, subject))
    else:
        lines.declarations.append(_declaration(lines, [subject], name=_subject_name(request), container="requirement"))
    target = request.view.label(request.subject) if request.subject else _parameter_phrase(request)
    if declared:
        return lines.remedy(f"take the system of interest the charter declares as the subject of {target}, never "
                            "the increment")
    return lines.remedy(f"declare the system of interest in the increment's package, reference it from the charter "
                        f"and take it as the subject of {target}, never the increment")


def _in_charter(lines: _Lines, member: str) -> str:
    """``member`` in the charter: in the increment's own charter, which exists (the line alone, "in the
    existing" charter), else in the block of a new charter declared as the workflow's charter
    parameter types it."""
    request = lines.request
    view, scope = request.view, request.scope
    if scope is not None and len(scope.charters) == 1:
        return _existing_member(lines, scope.charters[0], member)
    parameter, definition = _new_charter(request)
    keyword = _parameter_keyword(replace(request, parameter=parameter))
    head = f"{keyword} <charterName>" + (f" : {lines.type(definition, _SPECIALIZING)}" if definition else "")
    return f"{head} {{ {member} }}"


def _new_charter(request: _Request) -> tuple[str | None, str | None]:
    """The workflow's charter parameter and the definition typing it, which a new charter is declared
    with: the one step parameter typed by the charter class (validated binding) or a definition
    specializing it. Without exactly one such definition, no parameter and the charter class itself."""
    view = request.view
    kernel = _kernel(view, CHARTER_CLASS)
    if kernel is None:
        return None, None
    lineage = view.index.specializations(kernel)
    typed = {parameter: types for parameter in request.parameters
             if (types := sorted(view.index.typed_by(parameter) & lineage))}
    definitions = {definition for types in typed.values() for definition in types}
    if len(definitions) != 1:
        return None, kernel
    (definition,) = definitions
    return next(parameter for parameter, types in typed.items() if definition in types), definition


def _charter_definitions(request: _Request) -> list[str]:
    """The definitions whose features the increment's charter has, nearest first: its own charter's
    definitions, else the one a new charter is declared with (:func:`_new_charter`), each with its
    generals. Never other charter definitions of the model, which a charter does not inherit from."""
    view, scope = request.view, request.scope
    if scope is not None and len(scope.charters) == 1:
        holders = sorted(view.index.typed_by(scope.charters[0]))
    else:
        holders = [definition for definition in [_new_charter(request)[1]] if definition]
    found: list[str] = []
    for definition in holders:
        found.extend(general for general in view.index.generals(definition) if general not in found)
    return found


def _verifies(ontology_class: str, what: str) -> Callable[[_Request], Remedy]:
    def build(request: _Request) -> Remedy:
        lines = _lines(request)
        kernel = _kernel(request.view, ontology_class)
        verified = f"<{what}>"
        if kernel is not None:
            lines.notes.append(f"{verified} is a usage of {lines.type(kernel, _SPECIALIZING)} or a definition "
                               "specializing it, in a package named in the charter's expectedArtifacts.")
        objective = f"objective {{ verify {verified}; }}"
        if request.subject is not None:
            lines.declarations.append(f"verify {verified};")
            return lines.remedy(f"add to the objective of {request.view.label(request.subject)} (or of its "
                                "definition)")
        lines.declarations.append(_declaration(lines, [objective], name=_subject_name(request),
                                               container="verification"))
        return lines.remedy(f"declare {_parameter_phrase(request)} {_where(request)}, its objective verifying "
                            f"a {what}".replace("  ", " "))

    return build


def _method_side(reason: str) -> Callable[[_Request], Remedy]:
    def build(request: _Request) -> Remedy:
        return Remedy(f"nothing to author in the model for {_subject_phrase(request)}: {reason} (method side: only "
                      "a method or kernel change can supply it)")

    return build


def _evidence_record_or_status(request: _Request) -> Remedy:
    return _relation_remedy(replace(request, check="hasEvidence"))


_NAMED: Mapping[str, Callable[[_Request], Remedy]] = {
    "incrementShortName": _increment_short_name,
    "charterReferencesIncrement": _charter_references_increment,
    "problemStatementSubject": _problem_statement_subject,
    "ownedByIncrementPackage": _owned_by_increment_package,
    "stakeholderMember": _stakeholder_member,
    "framedByIncrementView": _framed_by_increment_view,
    "charterOwner": _charter_value,
    "charterApplicablePhases": _applicable_phases,
    "charterExpectedArtifacts": _charter_value,
    "charterExpectedReviewEvidence": _charter_value,
    "requireConstraint": _require_constraint,
    "sourceAttribute": _library_value,
    "rationaleAttribute": _library_value,
    "oneNativeSubject": _one_native_subject,
    "subjectIsSystemOfInterest": _subject_is_system_of_interest,
    "charterExpectedArtifactsCoverContent": _expected_artifacts_cover_content,
    "oneVerificationMethodKind": _library_value,
    "successCriteriaAttribute": _library_value,
    "verifiesIncrementRequirement": _verifies(REQUIREMENT_CLASS, "requirement of the increment"),
    "evidenceRecordOrStatus": _evidence_record_or_status,
    "receivesAllocation": lambda request: _receives_allocation(request),
    "carriedByArchitecture": lambda request: _carried_by_architecture(request),
    "populationMember": lambda request: _population_member(request),
    "signalMappingRecorded": lambda request: _signal_mapping_recorded(request),
    "semanticSourceNamed": lambda request: _semantic_source_named(request),
    "framedByViewpoint": _framed_by_increment_view,
    "contextSystemOfInterest": lambda request: _context_system_of_interest(request),
    "storySubjectBound": lambda request: _story_subject_bound(request),
    "storyActorsBound": lambda request: _story_actors_bound(request),
    "featureDeltaOnly": lambda request: _feature_delta_only(request),
    "viewpointFramesConcern": lambda request: _viewpoint_frames_concern(request),
    "exposesModelContent": lambda request: _exposes_model_content(request),
    "configuredByOneConfiguration": lambda request: _configured_by_one_configuration(request),
    "dispositionStated": lambda request: _disposition_stated(request),
}


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------


def _placeholder(ontology_class: str | None) -> str:
    """A name placeholder for an element of a class (``ValidationScenario`` -> ``<validationScenario>``)."""
    name = str(ontology_class or "target")
    return f"<{name[:1].lower()}{name[1:]}>"


def _native_frame(request: _Request) -> Remedy:
    lines = _lines(request)
    if request.subject is not None:
        lines.declarations.append("frame <concern>;")
        return lines.remedy(f"add to {request.view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, ["frame <concern>;"], name=_subject_name(request),
                                           container="requirement"))
    return lines.remedy(f"declare {_parameter_phrase(request)} with the concern it frames {_where(request)}".rstrip())


def _native_stakeholder(request: _Request) -> Remedy:
    return _stakeholder_member(request)


def _native_subject(request: _Request) -> Remedy:
    return _one_native_subject(request)


def _native_verify(request: _Request) -> Remedy:
    lines = _lines(request)
    if request.subject is not None:
        lines.declarations.append("verify <requirement>;")
        return lines.remedy(f"add to the objective of {request.view.label(request.subject)} (or of its definition)")
    lines.declarations.append(_declaration(lines, ["objective { verify <requirement>; }"], name=_subject_name(request),
                                           container="verification"))
    return lines.remedy(f"declare {_parameter_phrase(request)}, its objective verifying the requirement "
                        f"{_where(request)}".rstrip())


_NATIVE: Mapping[str, Callable[[_Request], Remedy]] = {
    "frame": _native_frame, "stakeholder": _native_stakeholder, "subject": _native_subject,
    "verify": _native_verify,
}


def _end_order(view: ModelView, carrier: str | None, first: str, second: str) -> tuple[str, str]:
    """The ends ``first`` and ``second`` in the order the carrier declares them (as given when it
    declares neither). A definition's ends are its EndFeatureMemberships and, as the export serializes
    a connection definition's ends, its FeatureMemberships of an ``isEnd`` feature."""
    if carrier is None:
        return first, second
    names = [str(relationship.get("memberName") or view.index.name_of(member))
             for relationship in view.index.owned_relationships(carrier, *DEFINITION_END_FAMILIES)
             for member in reference_ids(relationship.get("memberElement"))
             if str(relationship.get("@type") or "") in END_FAMILIES
             or view.index.by_id.get(member, {}).get("isEnd") is True]
    if first in names and second in names and names.index(second) < names.index(first):
        return second, first
    return first, second


def _derivation_connection(request: _Request, mapping: Any) -> Remedy:
    view = request.view
    config = mapping.configuration or {}
    lines = _lines(request)
    carrier = _kernel(view, str(config.get("connection_definition") or ""))
    if carrier is None:  # as the relation check reads it: method side
        return _method_side(f"the connection definition carrying {request.check} has no validated kernel binding "
                            "at this revision")(request)
    carrier_ref = lines.type(carrier, _SPECIALIZING)
    source_class = str(config.get("source_lineage_of") or mapping.domain or "")
    target_class = str(config.get("target_lineage_of") or mapping.range or "")
    subject = _subject_ref(lines, _placeholder(source_class))
    other = _placeholder(target_class)
    need_role, requirement_role = str(config.get("need_role") or ""), str(config.get("requirement_role") or "")
    by_role = {need_role: subject if source_class == _need_class(config) else other,
               requirement_role: other if source_class == _need_class(config) else subject}
    first, second = _end_order(view, carrier, need_role, requirement_role)
    lines.declarations.append(f"connection <name> : {carrier_ref} connect {by_role[first]} to {by_role[second]};")
    kernel = _kernel(view, target_class)
    if kernel is not None:
        lines.notes.append(f"{other} is a usage of {lines.type(kernel, _SPECIALIZING)} or a definition "
                           "specializing it.")
    return lines.remedy(f"replace any plain dependency with a {view.index.name_of(carrier)} connection, "
                        f"{_where(request) or 'in a package of the increment'}")


def _need_class(config: Mapping[str, Any]) -> str:
    """The class of the need end of a derivation connection (the end its query starts from forward)."""
    if str(config.get("query_direction") or "") == "forward":
        return str(config.get("source_lineage_of") or "")
    return str(config.get("target_lineage_of") or "")


def _successor(request: _Request, mapping: Any) -> Remedy:
    view = request.view
    profile = getattr(view.contract, "profile", None) or {}
    relations = profile.get("relations") or {}
    rows = list(relations.get(request.check) or ())
    inverse = False
    if not rows:
        rows = [row for name, found in relations.items() for row in found if row.get("inverse") == request.check]
        inverse = bool(rows)
    if not rows:
        return _unsupported(request, mapping.strategy)
    row = _end_pair(request, rows, inverse=inverse)
    lines = _lines(request)
    source_class, target_class = str(row.get("sourceClass") or ""), str(row.get("targetClass") or "")
    subject_class, other_class = (target_class, source_class) if inverse else (source_class, target_class)
    other_usage = str(row.get("targetUsage") if not inverse else row.get("sourceUsage") or "")
    other = _placeholder(other_class)
    subject = _subject_ref(lines, _placeholder(subject_class))
    other_kernel = _kernel(view, other_class)
    if other_kernel is not None:
        keyword = USAGE_KEYWORDS.get(other_usage, "part")
        lines.declarations.append(f"{keyword} {other} : {lines.type(other_kernel, _SPECIALIZING)};")
    source, target = (other, subject) if inverse else (subject, other)
    mechanism = str(row.get("mechanism") or "")
    if mechanism == "typed-connection":
        try:
            carrier = view.traversal.class_lineage(str(row.get("predicate") or request.check),
                                                  view.elements)["root_id"]
        except (IdentityNotFoundError, KeyError):
            carrier = None
        if carrier is None:  # as the relation check reads it: method side
            return _method_side(f"the connection definition carrying {request.check} has no validated kernel "
                                "binding at this revision")(request)
        lines.declarations.append(f"connection <name> : {lines.type(carrier, _SPECIALIZING)} connect {source} "
                                  f"to {target};")
        instruction = f"declare {other} and connect {subject} to it"
    elif mechanism == "native-allocation":
        lines.declarations.append(f"allocation <name> allocate {source} to {target};")
        lines.notes.append(_ALLOCATION_NOTE.format(other=other))
        instruction = f"allocate {source} to {target}"
    else:
        return _unsupported(request, f"{mapping.strategy}/{mechanism}")
    return lines.remedy(f"{instruction}, {_where(request) or 'in a package of the increment'}")


#: How the other end of an allocation remedy may be given.
_ALLOCATION_NOTE = ("{other} may also be an existing element, of this increment or a baseline; an end written as a "
                    "feature chain (a.b) is read as its last feature, and the allocation needs no type.")


def _end_pair(request: _Request, rows: Sequence[Mapping[str, Any]], *, inverse: bool) -> Mapping[str, Any]:
    """The end pair a remedy writes: the one whose subject-side class the subject (else the parameter's
    type) grounds in, through the validated kernel bindings; the first when none does."""
    key = "targetClass" if inverse else "sourceClass"
    types = _subject_types(request)
    return next((row for row in rows if _in_lineage(request.view, types, str(row.get(key) or ""))), rows[0])


def _receives_allocation(request: _Request) -> Remedy:
    """An allocation to the subject from an existing element of the end pair's source class. The check
    is advisory: an element without one is allowed, and no source is declared just to close the note."""
    from .method_checks import allocation_relation

    view = request.view
    relation = allocation_relation(view)
    profile = getattr(view.contract, "profile", None) or {}
    rows = list((profile.get("relations") or {}).get(relation or "") or ())
    if relation is None or not rows:
        return _method_side("the served contract has not exactly one relation carried by native allocations")(request)
    row = _end_pair(request, rows, inverse=True)
    lines = _lines(request)
    other = _placeholder(str(row.get("sourceClass") or ""))
    subject = _subject_ref(lines, _placeholder(str(row.get("targetClass") or "")))
    other_kernel = _kernel(view, str(row.get("sourceClass") or ""))
    lines.declarations.append(f"allocation <name> allocate {other} to {subject};")
    if other_kernel is not None:
        lines.notes.append(f"{other} is an existing usage of {lines.type(other_kernel, _SPECIALIZING)} or a "
                           "definition specializing it, of this increment or a baseline; an end written as a feature "
                           "chain (a.b) is read as its last feature, and the allocation needs no type.")
    lines.notes.append(f"Leaving {subject} without one is allowed: the check is advisory and only reports it for "
                       f"review; declare no new {other} just to close the note.")
    return lines.remedy(f"allocate {other} to {subject}, {_where(request) or 'in a package of the increment'}")


def _carried_by_architecture(request: _Request) -> Remedy:
    """An allocation of the requirement to a function; the alternative, a dependency to it from an
    architecture element relevant to it (``hasRelevantArchitecture``, relevance only), is a note. The
    check is advisory: a requirement neither carries is allowed."""
    from .method_checks import allocation_relation

    view = request.view
    relation = allocation_relation(view)
    profile = getattr(view.contract, "profile", None) or {}
    rows = list((profile.get("relations") or {}).get(relation or "") or ())
    if relation is None or not rows:
        return _method_side("the served contract has not exactly one relation carried by native allocations")(request)
    row = _end_pair(request, rows, inverse=False)
    lines = _lines(request)
    subject = _subject_ref(lines, _placeholder(str(row.get("sourceClass") or "")))
    function = _placeholder(str(row.get("targetClass") or ""))
    kernel = _kernel(view, str(row.get("targetClass") or ""))
    lines.declarations.append(f"allocation <name> allocate {subject} to {function};")
    if kernel is not None:
        lines.notes.append(f"{function} is a usage of {lines.type(kernel, _SPECIALIZING)} or a definition "
                           "specializing it, of this increment or a baseline.")
    lines.notes.append(f"Instead of the allocation, when a part or action usage or definition is relevant to {subject} "
                       "without being a function that carries it, a dependency from that element to it records the "
                       f"relevance (hasRelevantArchitecture, relevance only): dependency <name> from <element> to "
                       f"{subject};")
    lines.notes.append(f"Leaving {subject} carried by neither is allowed: the check is advisory, and only its "
                       "verification (phase 10) covers it then.")
    return lines.remedy(f"allocate {subject} to {function}, {_where(request) or 'in a package of the increment'}")


def _population_member(request: _Request) -> Remedy:
    """One more element the step parameter counts: its gate states only the parameter's multiplicity."""
    lines = _lines(request)
    lines.declarations.append(_declaration(lines, name=_subject_name(request)))
    return lines.remedy(f"declare {_parameter_phrase(request)} {_where(request)}".rstrip())


#: The text a remedy gives a record that states its semantic source.
_SEMANTIC_SOURCE = f'attribute :>> semanticSource = "{SEMANTIC_SOURCE_PLACEHOLDER}";'
_MAPPING_NOTES = (
    "<ID> is the mapping ID, the record's short name (naming: MAP); the mapping's target, the typed ports and the "
    "connections give the endpoints and the direction.",
    "The target is the port where the item enters the software contract the record is about. A port the element "
    "inherits from its definition is written as a chain through the element (<element>.<port>), so the mapping "
    "names this element's port and not that of every usage of the definition. One mapping per logical element "
    "may cover the processes of its chain; the record's softwareContractArtifact, softwareContractMessage and "
    "softwareContractField name the further contracts. The mapping counts once a package of the increment owns "
    "it, not nested in a definition.",
    "The disposition is mapped, candidate, deferred, or notApplicable when the item crosses no software contract "
    "(evidenceOrGap says why); the record also states the data type and unit, timing, the transformation rule and "
    "the evidence or gap. A member states nothing while it holds a placeholder (<...>) or only TBD, TBC or TODO. A "
    "mapping is no runtime-interoperability claim.",
)
_VSS_NOTE = (
    "If the item is a vehicle signal, type it with COVESA VSS instead of stating it: private import COVESA_VSS::**; "
    "and an attribute typed by the VSS signal in the item at the mapping's target, as INC-MW-008's "
    "DE4SDVReferenceVehicleSpeedPayload types speed_kmh with Vehicle_Speed. A signal the pinned VSS snapshot lacks "
    "goes into DE4SDV_VSS_Extensions with @VssSignalMetadata (path, kind, datatype, sourceDescription, "
    "sourceComment); proposing it to COVESA needs the owner's approval. A VSS path in a doc or a string is no VSS "
    "typing; data that is no vehicle signal (a ROS 2 message, a diagnostic, a display frame) says so here."
)
_ELEMENT_TARGET_NOTE = (
    "VSS typing is read only at a port, or an item or attribute in one: a mapping to an element states its "
    "semantic source in the record, or names the port as <element>.<port>."
)


def _record_members(lines: _Lines, kernel: dict[str, str]) -> dict[str, str]:
    """The line a remedy gives each record member a check asks for."""
    return {
        "disposition": f"attribute :>> disposition = {lines.type(kernel[SIGNAL_MAPPING_DISPOSITION])}::candidate;",
        "owner": f'attribute :>> owner = "{OWNER_PLACEHOLDER}";',
        "nextAction": f'attribute :>> nextAction = "{NEXT_ACTION_PLACEHOLDER}";',
        "evidenceOrGap": f'attribute :>> evidenceOrGap = "{REASON_PLACEHOLDER}";',
    }


def _record_line(lines: _Lines, kernel: dict[str, str], members: Sequence[str]) -> str:
    return f"item <'MAP-<ID>'> <record> : {lines.type(kernel[SIGNAL_MAPPING_RECORD])} {{ {' '.join(members)} }}"


def _mapping_line(lines: _Lines, kernel: dict[str, str], source: str, target: str, members: Sequence[str]) -> str:
    """``allocation <name> : <mapping> allocate <source> to <target> { item <'MAP-<ID>'> <record> : <record
    def> { <members> } }``: a system-to-software signal mapping owning its record."""
    return (f"allocation <name> : {lines.type(kernel[SIGNAL_MAPPING])} allocate {source} to {target} "
            f"{{ {_record_line(lines, kernel, members)} }}")


def _signal_mapping_kernel(view: ModelView) -> dict[str, str] | None:
    kernel = {name: _kernel(view, name) for name in (SIGNAL_MAPPING, SIGNAL_MAPPING_RECORD, SIGNAL_MAPPING_DISPOSITION)}
    return None if None in kernel.values() else kernel  # type: ignore[return-value]


def _port_target(view: ModelView, subject: str, ports: Sequence[str]) -> str:
    """The mapping target for a crossing: a port the subject owns, by its qualified name; else the first
    information port as a chain through the subject (``<subject>.<port>``), which names this usage's port
    where the port's qualified name would name the definition's, shared by every usage."""
    owned = [port for port in ports if view.index.owner_of(port) == subject]
    if owned:
        return view.label(owned[0])
    name = view.index.name_of(ports[0]) if ports else ""
    return f"{view.label(subject)}.{escape_name(name)}" if name else "<port>"


def _signal_mapping_recorded(request: _Request) -> Remedy:
    """A signal mapping owning its record, from a logical element the physical element realizes to the
    port of that element where the item enters its software contract; or, for a mapping of the increment
    whose record is missing or incomplete, what that record lacks."""
    from .method_checks import crossing_coverage

    view = request.view
    kernel = _signal_mapping_kernel(view)
    if kernel is None:
        return _method_side("the signal-mapping classes have no validated kernel binding")(request)
    lines = _lines(request)
    members = _record_members(lines, kernel)
    source, target, where = "<logical element>", "<port>", ""
    if request.subject is not None and request.scope is not None:
        try:
            found = crossing_coverage(view, request.scope, request.subject)
        except MethodSideInput as missing:
            return _method_side(missing.detail)(request)
        uncovered = [logical for logical, covering in found.coverage.items() if not covering]
        pending = found.incomplete.get(uncovered[0]) if uncovered else None
        if pending:
            mapping, record, gaps = pending[0]
            lines.notes.extend(_MAPPING_NOTES)
            if record is None:
                line = _record_line(lines, kernel, [members[m] for m in ("disposition", "owner", "nextAction")])
                lines.declarations.append(line)
                lines.placed[line] = f"in the existing {view.label(mapping)}:"
                return lines.remedy(f"give {view.label(mapping)} its mapping record")
            for gap in gaps:
                lines.declarations.append(members[gap])
                lines.placed[members[gap]] = f"in the existing {view.label(record)}:"
            return lines.remedy(f"state the {', '.join(gaps)} of {view.label(record)}")
        source = view.label(uncovered[0]) if uncovered else source
        target = _port_target(view, request.subject, found.ports)
        where = f" of {view.label(request.subject)}"
    lines.declarations.append(_mapping_line(lines, kernel, source, target, [
        members[m] for m in ("disposition", "owner", "nextAction")]))
    lines.notes.extend(_MAPPING_NOTES)
    return lines.remedy(f"record the crossing{where} with a system-to-software signal mapping, "
                        f"{_where(request) or 'in a package of the increment'}")


def _semantic_source_named(request: _Request) -> Remedy:
    """The records of a mapping state the semantic source of an item that is no VSS signal; a vehicle
    signal is typed with COVESA VSS instead (a note)."""
    from .method_checks import NOT_APPLICABLE, SEMANTIC_SOURCE, _disposition

    view = request.view
    kernel = _signal_mapping_kernel(view)
    if kernel is None:
        return _method_side("the signal-mapping classes have no validated kernel binding")(request)
    lines = _lines(request)
    if request.subject is not None:
        try:
            records = mapping_records(view, request.subject)
            lacking = [record for record in records if _disposition(view, record) != NOT_APPLICABLE
                       and not stated_texts(view, record, SEMANTIC_SOURCE)]
            ends, _problem = signal_mappings(view).get(request.subject, ((), ""))
        except MethodSideInput as missing:
            return _method_side(missing.detail)(request)
        if lacking:
            lines.declarations.append(_SEMANTIC_SOURCE)
            lines.placed[_SEMANTIC_SOURCE] = f"in the existing {view.label(lacking[0])}:"
            if len(lacking) > 1:
                lines.notes.append(f"Likewise in {', '.join(view.label(record) for record in lacking[1:])}.")
            instruction = f"state the semantic source of {view.label(request.subject)}"
        else:
            record = _record_line(lines, kernel, [_SEMANTIC_SOURCE])
            lines.declarations.append(record)
            lines.placed[record] = f"in the existing {view.label(request.subject)}:"
            instruction = f"give {view.label(request.subject)} its mapping record, with the semantic source"
            lines.notes.extend(_MAPPING_NOTES)
        if len(ends) == 2 and str(view.element(ends[1]).get("@type")) not in SIGNAL_CARRIERS:
            lines.notes.append(_ELEMENT_TARGET_NOTE)
    else:
        lines.declarations.append(_mapping_line(lines, kernel, "<logical element>", "<port>", (_SEMANTIC_SOURCE,)))
        instruction = f"state the semantic source in the record, {_where(request) or 'in a package of the increment'}"
    lines.notes.append(_VSS_NOTE)
    return lines.remedy(instruction)


# ---------------------------------------------------------------------------
# Operational context and story (phase 2), classification (phase 3), views (phase 11)
# ---------------------------------------------------------------------------

_SYSTEM_NAME = "<systemName>"
_CONTEXT_PART = "<contextPart>"
_VIEWPOINT_DEF = "viewpoint def <ViewpointName> { doc /* <what the view shows> */ }"
_VIEWPOINT_NOTE = ("<ViewpointName> may instead be an existing SAF or DE4SDV method viewpoint definition; the "
                   "check reads the viewpoint and its frame and tests no viewpoint or concern type.")


def _declared_system_of_interest(lines: _Lines) -> str:
    """The definition of the system of interest the charter declares (qualified), or, when it declares
    none, ``<SystemName>``: declared first, with its usage and the charter's reference to it."""
    from .method_checks import CONTEXT_SYSTEM_OF_INTEREST

    request = lines.request
    scope = request.scope
    if scope is not None and scope.system_of_interest_types:
        return lines.type(scope.system_of_interest_types[0],
                          "the system of interest the charter declares, or a definition specializing it")
    lines.declarations.extend(["part def <SystemName> { doc /* <the system of interest> */ }",
                               "part <systemUsage> : <SystemName>;"])
    line = _member_line(lines, CONTEXT_SYSTEM_OF_INTEREST, "<systemUsage>", definitions=_charter_definitions(request))
    if line:
        lines.declarations.append(_in_charter(lines, line))
    return "<SystemName>"


def _context_system_line(lines: _Lines) -> str:
    """``part <systemName> : <the system of interest's definition> :>> systemOfInterest;``: the context's
    own system of interest, typed like the charter's."""
    from .method_checks import CONTEXT_SYSTEM_OF_INTEREST

    return f"part {_SYSTEM_NAME} : {_declared_system_of_interest(lines)} :>> {CONTEXT_SYSTEM_OF_INTEREST};"


def _context_system_of_interest(request: _Request) -> Remedy:
    """The context redefines its systemOfInterest with the system of interest the charter declares."""
    lines = _lines(request)
    line = _context_system_line(lines)
    if request.subject is not None:
        lines.declarations.append(_existing_member(lines, request.subject, line))
        return lines.remedy(f"give {request.view.label(request.subject)} the system of interest the charter "
                            "declares as its own systemOfInterest")
    lines.declarations.append(_declaration(lines, [line], name=_subject_name(request)))
    where = _where(request)
    return lines.remedy(f"declare {_parameter_phrase(request)}{' ' + where if where else ''}, its systemOfInterest "
                        "the system of interest the charter declares")


def _story_subject_bound(request: _Request) -> Remedy:
    """Each use case binds its subject to the context's system of interest: the line for the first one
    that does not, which replaces its subject (a use case has one)."""
    from .method_checks import context_system_of_interest, story_subject_problems, use_case_parameters

    view, scope = request.view, request.scope
    lines = _lines(request)
    instruction = "bind the subject of each use case of the increment to the system of interest of its operational context"
    if request.subject is None:
        lines.declarations.append("use case <useCaseName> { subject <subjectName> = <systemOfInterestPart>; }")
        lines.notes.append("<systemOfInterestPart> is the part of the increment's operational context that redefines "
                           "its systemOfInterest.")
        return lines.remedy(instruction)
    context = request.subject
    systems = context_system_of_interest(view, context)[1]
    if systems:
        target = view.label(systems[0])
    else:
        lines.declarations.append(_existing_member(lines, context, _context_system_line(lines)))
        target = _SYSTEM_NAME
    line = f"subject <subjectName> = {target};"
    problems = story_subject_problems(view, scope, context) if scope is not None else []
    if problems:
        use_case = problems[0][0]
        own = [p for p in use_case_parameters(view, use_case, "SubjectMembership") if view.index.owner_of(p) == use_case]
        lines.placed[line] = (f"replace the subject of {view.label(use_case)} with:" if own
                              else f"in the existing {view.label(use_case)}:")
        if len(problems) > 1:
            lines.notes.append(f"Likewise in {', '.join(view.label(found) for found, _why in problems[1:])}.")
    lines.declarations.append(line)
    lines.notes.append("A use case's definition may declare its subject with another type; change that subject too "
                       "when it is not the system of interest.")
    return lines.remedy(instruction)


def _story_actors_bound(request: _Request) -> Remedy:
    """Each actor binds to a part of the context around its system of interest: the lines for the first
    actor that does not, a context part and the actor's binding in its use case."""
    from .method_checks import story_actor_problems

    view, scope = request.view, request.scope
    lines = _lines(request)
    instruction = "bind each actor of each use case of the increment to a part of its operational context"
    context = request.subject
    problems = story_actor_problems(view, scope, context) if context is not None and scope is not None else []
    if not problems:
        lines.declarations.append(f"use case <useCaseName> {{ actor <actorName> = {_CONTEXT_PART}; }}")
        lines.notes.append(f"{_CONTEXT_PART} is a part of the increment's operational context, around its system of "
                           "interest, not inside it.")
        return lines.remedy(instruction)
    use_case, actor, _why = problems[0]
    actor_type = _one_type(view, actor)
    typed = lines.type(actor_type, "the type of the actor it binds") if actor_type else None
    part = f"part {_CONTEXT_PART} : {typed};" if typed else f"part {_CONTEXT_PART};"
    lines.declarations.append(_existing_member(lines, context, part))
    binding = f"actor {view.index.name_of(actor) or '<actorName>'} = {_CONTEXT_PART};"
    lines.declarations.append(_existing_member(lines, use_case, binding))
    lines.notes.append(f"Bind an existing part of {view.label(context)} instead where it has one, by its qualified "
                       "name; a part around the system of interest, not inside it.")
    if view.index.owner_of(actor) == use_case:
        lines.notes.append(f"The binding replaces the actor's own declaration in {view.label(use_case)}.")
    if len(problems) > 1:
        lines.notes.append("Likewise for " + ", ".join(
            f"{view.label(found)} (actor {view.index.name_of(other) or other})" for found, other, _why in problems[1:])
            + ".")
    return lines.remedy(instruction)


def _feature_delta_only(request: _Request) -> Remedy:
    """A phase-3 record that is no feature candidate: no record for a core element; a candidate when it
    distinguishes member products (a note, as a retyping of an existing element is)."""
    from .method_checks import DEFERRED_SCOPE_CLASS, FEATURE_CLASS

    view = request.view
    lines = _lines(request)
    feature, deferred = _kernel(view, FEATURE_CLASS), _kernel(view, DEFERRED_SCOPE_CLASS)
    if feature is None or deferred is None:
        return _method_side("the product-line characteristic classes have no validated kernel binding")(request)
    candidate = lines.type(feature, "the feature-model delta: a characteristic that distinguishes member products")
    deferring = lines.type(deferred, "product-line scope the increment defers")
    if request.subject is None:
        lines.declarations.append(f"part <name> : {candidate};")
        lines.notes.append(f"Scope the increment defers is typed by {deferring}.")
        where = _where(request)
        return lines.remedy(f"record only the feature candidates the increment adds{' ' + where if where else ''}")
    target = view.label(request.subject)
    lines.notes.append(f"Core elements are common by default and get no record: remove {target} and what only "
                       "restates it.")
    lines.notes.append(f"When {target} distinguishes member products, retype the existing {target} to "
                       f"`: {candidate}` instead; scope the increment defers is typed by {deferring}.")
    return lines.remedy(f"remove {target}, a record of common content, or retype it as a feature candidate")


def _viewpoint_frames_concern(request: _Request) -> Remedy:
    view = request.view
    lines = _lines(request)
    lines.declarations.append(_VIEWPOINT_DEF)
    line = "viewpoint <viewpointName> : <ViewpointName> { frame <concern>; }"
    if request.subject is not None:
        lines.declarations.append(_existing_member(lines, request.subject, line))
        instruction = f"give {view.label(request.subject)} a viewpoint that frames the concern it presents"
    else:
        lines.declarations.append(f"view <viewName> {{ {line} expose <element>; }}")
        where = _where(request)
        instruction = f"declare the view{' ' + where if where else ''} with a viewpoint that frames a concern"
    lines.notes.append(_VIEWPOINT_NOTE)
    return lines.remedy(instruction)


def _exposes_model_content(request: _Request) -> Remedy:
    view = request.view
    lines = _lines(request)
    line = "expose <element>;"
    if request.subject is not None:
        lines.declarations.append(_existing_member(lines, request.subject, line))
        instruction = f"expose the model content {view.label(request.subject)} presents"
    else:
        lines.declarations.append(_VIEWPOINT_DEF)
        lines.declarations.append(f"view <viewName> {{ viewpoint <viewpointName> : <ViewpointName> "
                                  f"{{ frame <concern>; }} {line} }}")
        lines.notes.append(_VIEWPOINT_NOTE)
        where = _where(request)
        instruction = f"declare the view{' ' + where if where else ''}, exposing model content"
    lines.notes.append("A table or matrix view may expose through the views it owns instead "
                       "(view :>> rowView { expose <element>; }); expose <package>::*; exposes a package's members.")
    return lines.remedy(instruction)


def _verification_membership(request: _Request, mapping: Any) -> Remedy:
    lines = _lines(request)
    verified = _subject_ref(lines, "<requirement>")
    lines.declarations.append(f"verification <name> {{ objective {{ verify {verified}; }} }}")
    return lines.remedy(f"verify {verified} in the objective of a verification case in a package named in the "
                        "charter's expectedArtifacts")


def _subject_membership(request: _Request, mapping: Any) -> Remedy:
    lines = _lines(request)
    kernel = _kernel(request.view, str(mapping.range or ""))
    if kernel is None:  # as the relation check reads it: method side
        return _method_side(f"{mapping.range}, the class of {request.check}'s subject, has no validated kernel "
                            "binding at this revision")(request)
    member = f"subject <subjectName> : {lines.type(kernel, _SPECIALIZING)};"
    lines.notes.append(SUBJECT_FIRST)
    if request.subject is not None:
        lines.declarations.append(_subject_line(lines, member))
        return lines.remedy(f"declare the subject of {request.view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, [member], name=_subject_name(request), container="requirement"))
    return lines.remedy(f"declare {_parameter_phrase(request)} with its subject {_where(request)}".rstrip())


def _dependency(request: _Request, mapping: Any) -> Remedy:
    lines = _lines(request)
    config = mapping.configuration or {}
    subject = _subject_ref(lines, _placeholder(mapping.domain))
    other = _placeholder(mapping.range)
    kernel = _kernel(request.view, str(mapping.range or ""))
    if kernel is not None:
        lines.notes.append(f"{other} is a {lines.type(kernel, _SPECIALIZING)} or a definition specializing it.")
    if str(config.get("direction") or "") == "incoming":
        lines.declarations.append(f"dependency <name> from {other} to {subject};")
    else:
        lines.declarations.append(f"dependency <name> from {subject} to {other};")
    return lines.remedy(f"declare the dependency, {_where(request) or 'in a package of the increment'}")


def _unsupported(request: _Request, strategy: str) -> Remedy:
    return Remedy(f"no SysML line is derived for {request.check} (mapping {strategy}); author what its contract "
                  f"mapping names for {_subject_phrase(request)}")


_STRATEGIES: Mapping[str, Callable[[_Request, Any], Remedy]] = {
    "derivation-connection": _derivation_connection, "successor": _successor,
    "verification-membership": _verification_membership, "subject-membership": _subject_membership,
    "dependency": _dependency,
}


def _relation_remedy(request: _Request) -> Remedy:
    """What to author for a relation check: the native SysML construct of its contract mapping."""
    if request.check in _NATIVE:
        return _NATIVE[request.check](request)
    try:
        mapping = request.view.contract.relationship_mapping(request.check)
    except Exception:  # noqa: BLE001 - an unmapped relation is method side
        return _method_side(f"{request.check} has no SysML mapping at this revision")(request)
    if mapping.strategy == "external":
        return _method_side(f"{request.check} is external data at this revision; its evidence is recorded "
                            "outside the model")(request)
    build = _STRATEGIES.get(mapping.strategy)
    return build(request, mapping) if build else _unsupported(request, mapping.strategy)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def subject_declaration(view: ModelView, check: str, *, parameter: str | None, framing: bool | None,
                        scope: IncrementScope | None, name: str | None = None) -> Remedy:
    """How one subject of ``parameter`` is declared (as ``name``), without what ``check`` asks of it."""
    request = _Request(view, check, None, parameter, framing, scope, ())
    lines = _lines(request)
    lines.declarations.append(_declaration(lines, name=name or _subject_name(request)))
    return lines.remedy(f"declare {_parameter_phrase(request)} {_where(request)}".rstrip())


def population_remedy(view: ModelView, check: str, *, keep: str, parameter: str | None, framing: bool | None,
                      scope: IncrementScope | None, checked_phases: Sequence[str] = (),
                      parameters: Sequence[str] = ()) -> Remedy:
    """What to author when the number of subjects of ``parameter`` is outside its bounds: ``keep`` (how
    many to keep, and where), then how one is declared. The element the check counts comes first and
    complete, with what ``check`` asks of it inside it; the lines the check needs besides it (a
    scenario and its connection, a connection, the system of interest) follow it ("then:") and name it
    as it is declared. When the check's own remedy is method side, the element alone."""
    own = check_remedy(view, check, parameter=parameter, framing=framing, scope=scope,
                       checked_phases=checked_phases, parameters=parameters)
    if own.subject_line is not None and own.subject_line in own.declarations:
        lead, first = own, own.subject_line
        follow = [line for line in own.declarations if line != first]
    else:
        lead = subject_declaration(view, check, parameter=parameter, framing=framing, scope=scope,
                                   name=own.subject_name)
        first, follow = (lead.declarations or (None,))[0], list(own.declarations)
    if first is None:
        return Remedy(keep)
    types: dict[str, Mapping[str, Any]] = {}
    for named in (*lead.types, *own.types):  # the subject's type first
        types.setdefault(str(named["element_id"]), named)
    return Remedy(f"{keep}; one is declared as", (first, *follow),
                  tuple(dict.fromkeys((*lead.imports, *own.imports))), tuple(types.values()),
                  tuple(dict.fromkeys((*own.notes, *lead.notes))), own.phases, then_from=1 if follow else None,
                  placed=tuple({**dict(lead.placed), **dict(own.placed)}.items()))


def check_remedy(view: ModelView, check: str, *, subject: str | None = None, parameter: str | None = None,
                 framing: bool | None = None, scope: IncrementScope | None = None,
                 checked_phases: Sequence[str] = (), parameters: Sequence[str] = ()) -> Remedy:
    """What to author for one check: about ``parameter`` of its step (its keyword and type), for
    ``subject`` (the first failing element) or, without one, the subject to declare, ``framing`` in
    the increment's own package or in a package the charter names, for the increment ``scope``.
    ``checked_phases`` are the phases with executable checks; ``parameters`` every step parameter the
    workflow's checks are about. An unknown check has no remedy."""
    from .method_checks import NAMED_CHECKS
    from .relation_checks import relation_checks

    request = _Request(view, check, subject if subject and subject in view.index.by_id else None, parameter,
                       framing, scope, tuple(checked_phases), tuple(parameters))
    if check in _NAMED and check in NAMED_CHECKS:
        return _NAMED[check](request)
    if check in relation_checks(view):
        return _relation_remedy(request)
    return EMPTY


__all__ = ["Remedy", "SUBJECT_FIRST", "check_remedy", "population_remedy", "subject_declaration"]


# ---------------------------------------------------------------------------
# Configured product (phase 9), baseline decision and open gaps (phase 12)


def _projection_note(view: ModelView) -> str:
    """Which part definitions the configurator generated: the product-model projections a configured product
    composes, by qualified name."""
    from .method_checks import configuration_part_definitions

    projections, _problem = configuration_part_definitions(view)
    names = sorted(view.label(definition) for definition in projections)
    listed = f": {', '.join(names)}" if names else ""
    return ("The part is typed by the part definition that the configurator generates from the receipt of its feature "
            "configuration, in model-based-product-line-engineering/product-models/; the configuration's "
            f"ProductModelProjectionName annotation names it{listed}. A specialization that adds System 2 "
            "instrumentation inherits that part and is configured through it.")


def _configured_by_one_configuration(request: _Request) -> Remedy:
    """A configured product that no feature configuration, or more than one, configures: the part that
    composes its configuration's product-model projection, or one such part only."""
    from .method_checks import configured_by

    view = request.view
    lines = _lines(request)
    if request.subject is None:
        product = _kernel(view, "ConfiguredProduct")
        if product is None:
            return _method_side("the configured product has no validated kernel binding")(request)
        typed = lines.type(product, "a product that one feature configuration configures")
        lines.declarations.append(f"part def <ConfiguredProductName> :> {typed};")
        lines.declarations.append("part <configuredProductName> : <ConfiguredProductName>;")
        lines.notes.append("Give <ConfiguredProductName> a part that composes its configuration's product-model "
                           "projection. " + _projection_note(view))
        where = _where(request)
        return lines.remedy(f"declare the configured product{' ' + where if where else ''}")
    target = view.label(request.subject)
    configurations, usages = configured_by(view, request.subject)
    if configurations:
        lines.notes.append(f"{target} composes the projections of {len(configurations)} feature configurations, through "
                           + ", ".join(f"{view.label(u)} ({view.label(c)})" for c, u in zip(configurations, usages))
                           + ". Exactly one configuration configures a configured product.")
        return lines.remedy(f"keep the part of {target} that composes its own configuration's projection, and "
                            "remove the others")
    definition = _one_type(view, request.subject)
    holder = view.label(definition) if definition else target
    lines.notes.append(_projection_note(view))
    return lines.remedy(f"in {holder}, add a part typed by the part definition of its feature configuration's "
                        "product-model projection")


def _disposition_stated(request: _Request) -> Remedy:
    """A baseline decision or an open gap without its disposition: the redefinition that states it."""
    view = request.view
    lines = _lines(request)
    enum = _kernel(view, "LifecycleDisposition")
    if enum is None:
        return _method_side("the lifecycle disposition has no validated kernel binding")(request)
    literals = view.qualified_name(enum) or view.index.name_of(enum) or "LifecycleDisposition"
    line = "attribute :>> disposition = <disposition>;"
    lines.notes.append(f"<disposition> is {literals}::accepted, ::deferred or ::invalidated: what the baseline "
                       "decision does with the result of the increment, or with the open gap. An accepted gap stays "
                       "open as a known limit; the record of a resolved gap leaves the model instead.")
    if request.subject is not None:
        lines.declarations.append(_existing_member(lines, request.subject, line))
        return lines.remedy(f"state the disposition of {view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, [line], name=_subject_name(request)))
    return lines.remedy(f"declare {_parameter_phrase(request)} with its disposition {_where(request)}".rstrip())
