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
  its subject first.

Placeholders in angle brackets are names or text the author chooses, or a
value from a list the remedy gives; never a type. A remedy says what to
author, never that authoring it proves anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from .element_description import ElementDescriber, USAGE_KEYWORDS
from .increment_scope import (
    INCREMENT_CLASS,
    PHASE_CLASS,
    IncrementScope,
    ModelView,
    declared_artifacts,
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

    @property
    def text(self) -> str:
        """The one-line ``what_to_author``: instruction, lines, imports and notes."""
        parts = [self.instruction + (": " + " ".join(self.declarations) if self.declarations else "")]
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
                      tuple(dict.fromkeys(self.notes)), tuple(phases))


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


def _parameter_keyword(request: _Request) -> str:
    """The keyword that declares a subject: the parameter's usage keyword (``part``, ``concern`` ...)."""
    element = request.view.element(request.parameter) if request.parameter else {}
    return USAGE_KEYWORDS.get(str(element.get("@type") or ""), "part")


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
                 short: str | None = None, doc: bool = False) -> str:
    """``<keyword> [<'short'>] <name> [: <type>] { <members> }`` for the parameter's subject."""
    request = lines.request
    keyword = _parameter_keyword(request)
    parameter_type = _one_type(request.view, request.parameter)
    typed = f" : {lines.type(parameter_type, _SPECIALIZING)}" if parameter_type else ""
    body = [*(["doc /* <text> */"] if doc else []), *members]
    head = f"{keyword} {f'<{short}> ' if short else ''}{name}{typed}"
    return f"{head} {{ {' '.join(body)} }}" if body else f"{head};"


# ---------------------------------------------------------------------------
# Subjects first
# ---------------------------------------------------------------------------


def _has_subject(view: ModelView, element: str | None) -> bool:
    return bool(element) and any(view.index.owned_relationships(element, "SubjectMembership"))


def _increment_definition(lines: _Lines, general: str | None = None) -> str:
    """The increment's own definition, as the method declares it: the definition typing the resolved
    increment usage (qualified); else a part def the author names, declared first in the remedy and
    specializing ``general`` (the kernel's EngineeringIncrement, by its validated binding). The checks
    also accept a usage typed by the kernel definition itself; the remedy teaches the method's form."""
    request = lines.request
    scope = request.scope
    if scope is not None and scope.definition_ids:
        return lines.type(scope.definition_ids[0], "the definition typing the increment usage")
    general = general or _kernel(request.view, INCREMENT_CLASS)
    if general is None:
        lines.notes.append("The kernel binds no EngineeringIncrement definition at this revision.")
        return INCREMENT_DEFINITION
    declaration = (f"{_keyword(request.view, general)} {INCREMENT_DEFINITION} :> "
                   f"{lines.type(general, _OWN_DEFINITION)};")
    if declaration not in lines.declarations:
        lines.declarations.insert(0, declaration)
    return INCREMENT_DEFINITION


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
        return f"subject increment : {_increment_definition(lines)};"
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
        types = ", ".join(lines.type(t) for t in typed)
        lines.declarations.append(f"part <'{identifier}'> {view.index.name_of(request.subject) or '<usageName>'}"
                                  + (f" : {types};" if types else ";"))
        return lines.remedy(f"declare {view.label(request.subject)} with the increment identifier as its "
                            "declared short name")
    definition = _increment_definition(lines, _one_type(request.view, request.parameter))
    lines.declarations.append(f"{_parameter_keyword(request)} <'{identifier}'> <usageName> : {definition};")
    return lines.remedy(f"declare the increment usage with its identifier as declared short name, typed by the "
                        f"increment's own definition, {_where(request)}")


def _member_line(lines: _Lines, member: str, value: str, *,
                 definitions: Sequence[str] | None = None) -> str | None:
    """``<keyword> :>> <member> = <value>;`` with the keyword of the feature ``member`` redefines."""
    request = lines.request
    feature, distinct = _member(request, member, definitions)
    if feature is None:
        lines.notes.append(f"No definition of the subject declares {member} in this revision's model "
                           "(method side), so its declaring keyword is unknown.")
        return None
    target = member
    if len(distinct) > 1:
        target = request.view.label(feature)
        lines.notes.append(f"{member} names {len(distinct)} inherited features; the line redefines the nearest "
                           "by its qualified name.")
    return f"{_keyword(request.view, feature)} :>> {target} = {value};"


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
    return Remedy(remedy.instruction, remedy.declarations, remedy.imports, remedy.types,
                  (*remedy.notes, note), remedy.phases)


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
    return Remedy(f"name in the {member} of {target} every top-level package holding increment content "
                  "(elements connected by DerivesFromNeed to, verifying, or verified by the increment's elements, "
                  "or referencing the increment usage), or move that content into a named package",
                  remedy.declarations, remedy.imports, remedy.types, remedy.notes)


def _problem_statement_subject(request: _Request) -> Remedy:
    lines = _lines(request)
    subject = f"subject increment : {_increment_definition(lines)};"
    lines.notes.append(SUBJECT_FIRST)
    if request.subject is not None:
        lines.declarations.append(subject)
        return lines.remedy(f"keep {request.view.label(request.subject)} in the increment's package, its subject "
                            "first and typed by the increment definition")
    lines.declarations.append(_declaration(lines, [subject], name="<problemStatementName>"))
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
    lines.declarations.append(_declaration(lines, members, name=_subject_name(request)))
    return lines.remedy(f"declare {_parameter_phrase(request)} with a stakeholder member, its subject first, "
                        f"{_where(request)}".rstrip(", "))


def _concern_declaration(lines: _Lines, name: str = "<concernName>") -> str:
    return f"concern {name} {{ subject; {_stakeholder_line(lines)} }}"


def _framed_by_increment_view(request: _Request) -> Remedy:
    lines = _lines(request)
    concern = request.view.label(request.subject) if request.subject else "<concernName>"
    if request.subject is None:
        lines.declarations.append(_concern_declaration(lines))
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
    lines.declarations.append(_declaration(lines, [statement], name=_subject_name(request)))
    return lines.remedy(f"declare {_parameter_phrase(request)} with its statement {_where(request)}".rstrip())


def _one_native_subject(request: _Request) -> Remedy:
    lines = _lines(request)
    subject = _subject_first(lines)
    if request.subject is not None:
        lines.declarations.append(subject)
        return lines.remedy(f"declare exactly one subject on {request.view.label(request.subject)}")
    lines.declarations.append(_declaration(lines, [subject], name=_subject_name(request)))
    return lines.remedy(f"declare {_parameter_phrase(request)} with exactly one subject {_where(request)}".rstrip())


def _subject_is_system_of_interest(request: _Request) -> Remedy:
    lines = _lines(request)
    scope = request.scope
    declared = scope is not None and bool(scope.system_of_interest or scope.system_of_interest_types)
    if not declared:
        line = _member_line(lines, _named_member(request), "<systemUsage>", definitions=_charter_definitions(request))
        lines.declarations.extend(["part def <SystemName> { doc /* <the system of interest> */ }",
                                   "part <systemUsage> : <SystemName>;", *([line] if line else [])])
    lines.declarations.append(_system_of_interest_subject(lines))
    target = request.view.label(request.subject) if request.subject else _parameter_phrase(request)
    if declared:
        return lines.remedy(f"take the system of interest the charter declares as the subject of {target}, never "
                            "the increment")
    return lines.remedy(f"declare the system of interest in the increment's package, reference it from the charter "
                        f"and take it as the subject of {target}, never the increment")


def _charter_definitions(request: _Request) -> list[str]:
    """The definitions whose features a charter has: the increment's charter's own definitions, else
    every definition of the charter class lineage (validated kernel identity)."""
    from .increment_scope import CHARTER_CLASS

    view, scope = request.view, request.scope
    if scope is not None and len(scope.charters) == 1:
        found: list[str] = []
        for definition in sorted(view.index.typed_by(scope.charters[0])):
            found.extend(general for general in view.index.generals(definition) if general not in found)
        return found
    kernel = _kernel(view, CHARTER_CLASS)
    return sorted(view.index.specializations(kernel)) if kernel else []


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
        lines.declarations.append(_declaration(lines, [objective], name=_subject_name(request)))
        return lines.remedy(f"declare {_parameter_phrase(request)} {_where(request)}, its objective verifying "
                            f"a {what}".replace("  ", " "))

    return build


def _method_side(reason: str) -> Callable[[_Request], Remedy]:
    def build(request: _Request) -> Remedy:
        return Remedy(f"nothing to author in the model for {_subject_phrase(request)}: {reason} (method side: only "
                      "a method or kernel change can supply it)")

    return build


def _feature_or_common_capability(request: _Request) -> Remedy:
    remedies = [_relation_remedy(_Request(request.view, relation, request.subject, request.parameter,
                                          request.framing, request.scope, request.checked_phases))
                for relation in ("specifiesFeature", "specifiesCommonCapability")]
    authorable = [remedy for remedy in remedies if remedy.declarations]
    if not authorable:
        return Remedy(f"nothing to author in the model for {_subject_phrase(request)}: specifiesFeature and "
                      "specifiesCommonCapability have no SysML mapping at this revision (method side: only a "
                      "method or kernel change can supply it)")
    return authorable[0]


def _evidence_record_or_status(request: _Request) -> Remedy:
    return _relation_remedy(_Request(request.view, "hasEvidence", request.subject, request.parameter,
                                     request.framing, request.scope, request.checked_phases))


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
    lines.declarations.append("frame <concern>;")
    return lines.remedy(f"add to {_subject_phrase(request)}")


def _native_stakeholder(request: _Request) -> Remedy:
    return _stakeholder_member(request)


def _native_subject(request: _Request) -> Remedy:
    return _one_native_subject(request)


def _native_verify(request: _Request) -> Remedy:
    lines = _lines(request)
    lines.declarations.append("verify <requirement>;")
    return lines.remedy(f"add to the objective of {_subject_phrase(request)} (or of its definition)")


_NATIVE: Mapping[str, Callable[[_Request], Remedy]] = {
    "frame": _native_frame, "stakeholder": _native_stakeholder, "subject": _native_subject,
    "verify": _native_verify,
}


def _end_order(view: ModelView, carrier: str | None, first: str, second: str) -> tuple[str, str]:
    """The ends ``first`` and ``second`` in the order the carrier declares them (as given otherwise)."""
    if carrier is None:
        return first, second
    names = [str(relationship.get("memberName") or view.index.name_of(member))
             for relationship in view.index.owned_relationships(carrier, "EndFeatureMembership")
             for member in reference_ids(relationship.get("memberElement"))]
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
    subject = _label(request, request.subject, _placeholder(source_class))
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
    subject = _label(request, request.subject, _placeholder(subject_class))
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
    verified = _label(request, request.subject, "<requirement>")
    lines.declarations.append(f"verification <name> {{ objective {{ verify {verified}; }} }}")
    return lines.remedy(f"verify {verified} in the objective of a verification case in a package named in the "
                        "charter's expectedArtifacts")


def _subject_membership(request: _Request, mapping: Any) -> Remedy:
    lines = _lines(request)
    kernel = _kernel(request.view, str(mapping.range or ""))
    if kernel is None:  # as the relation check reads it: method side
        return _method_side(f"{mapping.range}, the class of {request.check}'s subject, has no validated kernel "
                            "binding at this revision")(request)
    lines.declarations.append(f"subject <subjectName> : {lines.type(kernel, _SPECIALIZING)};")
    lines.notes.append(SUBJECT_FIRST)
    return lines.remedy(f"declare the subject of {_subject_phrase(request)}")


def _dependency(request: _Request, mapping: Any) -> Remedy:
    lines = _lines(request)
    config = mapping.configuration or {}
    subject = _label(request, request.subject, _placeholder(mapping.domain))
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
                        scope: IncrementScope | None) -> Remedy:
    """How one subject of ``parameter`` is declared, without what ``check`` asks of it."""
    request = _Request(view, check, None, parameter, framing, scope, ())
    lines = _lines(request)
    lines.declarations.append(_declaration(lines, name=_subject_name(request)))
    return lines.remedy(f"declare {_parameter_phrase(request)} {_where(request)}".rstrip())


def check_remedy(view: ModelView, check: str, *, subject: str | None = None, parameter: str | None = None,
                 framing: bool | None = None, scope: IncrementScope | None = None,
                 checked_phases: Sequence[str] = ()) -> Remedy:
    """What to author for one check: about ``parameter`` of its step (its keyword and type), for
    ``subject`` (the first failing element) or, without one, the subject to declare, ``framing`` in
    the increment's own package or in a package the charter names, for the increment ``scope``.
    ``checked_phases`` are the phases with executable checks. An unknown check has no remedy."""
    from .method_checks import NAMED_CHECKS
    from .relation_checks import relation_checks

    request = _Request(view, check, subject if subject and subject in view.index.by_id else None, parameter,
                       framing, scope, tuple(checked_phases))
    if check in _NAMED and check in NAMED_CHECKS:
        return _NAMED[check](request)
    if check in relation_checks(view):
        return _relation_remedy(request)
    return EMPTY


__all__ = ["Remedy", "SUBJECT_FIRST", "check_remedy", "subject_declaration"]
