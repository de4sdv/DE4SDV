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


def _feature_or_common_capability(request: _Request) -> Remedy:
    remedies = [_relation_remedy(replace(request, check=relation))
                for relation in ("specifiesFeature", "specifiesCommonCapability")]
    authorable = [remedy for remedy in remedies if remedy.declarations]
    if not authorable:
        return Remedy(f"nothing to author in the model for {_subject_phrase(request)}: specifiesFeature and "
                      "specifiesCommonCapability have no SysML mapping at this revision (method side: only a "
                      "method or kernel change can supply it)")
    return authorable[0]


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
    "specifiesFeatureOrCommonCapability": _feature_or_common_capability,
    "verifiesIncrementRequirement": _verifies(REQUIREMENT_CLASS, "requirement of the increment"),
    "evidenceRecordOrStatus": _evidence_record_or_status,
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
    row = rows[0]
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
        instruction = f"allocate {source} to {target}"
    else:
        return _unsupported(request, f"{mapping.strategy}/{mechanism}")
    return lines.remedy(f"{instruction}, {_where(request) or 'in a package of the increment'}")


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
