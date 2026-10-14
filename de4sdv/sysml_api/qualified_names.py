"""Qualified names computed from an element corpus's ownership graph.

The licensed export, and the API listing that serves it, carry no
``qualifiedName``, ``owner`` or ``owningNamespace`` value (the pinned API pads
them as null). This module computes the KerML ``qualifiedName`` of each element
from what the corpus does carry: the member's ``owningRelationship`` (an owning
membership) and that membership's ``owningRelatedElement`` (the owning
namespace), up to an anonymous root namespace. It reads no ``.sysml`` text and
guesses no name (ADR 0011).

Rules (KerML ``Element::qualifiedName`` and ``escapedName``):

- a member of a root namespace is named by its own name; a deeper member by its
  owning namespace's qualified name, ``::`` and its own name;
- an element's name is its declared or effective name, else its short name; a
  name that is not a basic name, or is a SysML reserved word, is written as an
  unrestricted name, in single quotes with ``\\`` escapes;
- an element without a complete chain of named namespaces up to a root has no
  qualified name: an unnamed element or owner, an element owned through a
  relationship that is not an owning membership, or an owner outside the
  corpus. A root namespace is a ``Namespace`` without an owner. Any other
  element without an owner lost its owner to the export boundary (the export
  removes references to elements it does not carry), so neither it nor its
  members are named from it.

Where several elements share a qualified name (KerML names only the first),
each keeps it and resolving the name reports the ambiguity.

Only these ownership-qualified names resolve. SysML also reaches a member
through a short name, an alias, an import or inheritance; a name that takes
such a path is refused, never resolved, and the refusal says which path it
takes and gives the canonical qualified name, or every one when the name
reaches several elements (it is ambiguous there). That explanation is an exact
lookup over the serialized memberships, imports and specializations: one import
level, and inheritance through authored specializations only.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from .repository import element_id, reference_ids

_BASIC_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
#: The SysML v2 reserved keywords. A reserved word is never a basic name, though it has the form of one.
RESERVED_KEYWORDS = frozenset({
    "about", "abstract", "accept", "action", "actor", "after", "alias", "all", "allocate",
    "allocation", "analysis", "and", "as", "assert", "assign", "assume", "at", "attribute", "bind",
    "binding", "by", "calc", "case", "comment", "concern", "connect", "connection", "constant",
    "constraint", "crosses", "decide", "def", "default", "defined", "dependency", "derived", "do",
    "doc", "else", "end", "entry", "enum", "event", "exhibit", "exit", "expose", "false", "filter",
    "first", "flow", "for", "fork", "frame", "from", "hastype", "if", "implies", "import", "in",
    "include", "individual", "inout", "interface", "istype", "item", "join", "language", "library",
    "locale", "loop", "merge", "message", "meta", "metadata", "nonunique", "not", "null",
    "objective", "occurrence", "of", "or", "ordered", "out", "package", "parallel", "part",
    "perform", "port", "private", "protected", "public", "redefines", "ref", "references", "render",
    "rendering", "rep", "require", "requirement", "return", "satisfy", "send", "snapshot",
    "specializes", "stakeholder", "standard", "state", "subject", "subsets", "succession",
    "terminate", "then", "timeslice", "to", "transition", "true", "until", "use", "variant",
    "variation", "verification", "verify", "via", "view", "viewpoint", "when", "while", "xor",
})
#: KerML escape sequences of an unrestricted name, by the character after ``\``.
_UNESCAPE = {"'": "'", '"': '"', "\\": "\\", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
_ESCAPE = {"'": "\\'", "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_BLANKS = " \t"
#: Specializations a type inherits members through (authored ones are followed), and the
#: key that names the general element in each.
_SPECIALIZATIONS = ("Subclassification", "Specialization", "FeatureTyping", "ConjugatedPortTyping",
                    "Subsetting", "ReferenceSubsetting", "CrossSubsetting", "Redefinition")
_GENERAL_KEYS = ("general", "superclassifier", "type", "subsettedFeature", "redefinedFeature",
                 "referencedFeature")


def escape_name(name: str) -> str:
    """``name`` as written in a qualified name: as is when basic, else quoted."""
    if _BASIC_NAME.match(name) and name not in RESERVED_KEYWORDS:
        return name
    return "'" + "".join(_ESCAPE.get(character, character) for character in name) + "'"


def format_qualified_name(path: Iterable[str]) -> str:
    return "::".join(escape_name(segment) for segment in path)


def parse_qualified_name(text: str) -> tuple[str, ...] | None:
    """The unescaped segments of a qualified name; ``None`` when ``text`` is not one.

    Segments are separated by ``::`` (a member of a root namespace has one). A
    segment is an unrestricted name in single quotes (with ``\\`` escapes) or,
    as answers and reports print it, the name itself; blanks around a segment
    are ignored.
    """
    segments: list[str] = []
    position, end = 0, len(text)
    while True:
        while position < end and text[position] in _BLANKS:
            position += 1
        if position < end and text[position] == "'":
            position += 1
            characters: list[str] = []
            while True:
                if position >= end:
                    return None  # unterminated unrestricted name
                character = text[position]
                if character == "\\":
                    escaped = _UNESCAPE.get(text[position + 1:position + 2])
                    if escaped is None:
                        return None
                    characters.append(escaped)
                    position += 2
                    continue
                position += 1
                if character == "'":
                    break
                characters.append(character)
            segment = "".join(characters)
            while position < end and text[position] in _BLANKS:
                position += 1
            if position < end and not text.startswith("::", position):
                return None  # text after an unrestricted name
        else:
            separator = text.find("::", position)
            stop = end if separator == -1 else separator
            segment = text[position:stop].strip(_BLANKS)
            position = stop
        if not segment:
            return None
        segments.append(segment)
        if position >= end:
            break
        position += 2  # the "::" separator
        if position >= end:
            return None  # a trailing separator
    return tuple(segments)


def element_name(element: Mapping[str, Any]) -> str | None:
    """The name a qualified name uses: declared or effective name, else short name."""
    for key in ("declaredName", "name", "declaredShortName", "shortName"):
        value = element.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _is_owning_membership(relationship: Mapping[str, Any]) -> bool:
    kind = str(relationship.get("@type") or "")
    return kind.endswith("Membership") or kind == "FeatureValue"  # FeatureValue is an OwningMembership


def _is_root_namespace(element: Mapping[str, Any]) -> bool:
    """A ``Namespace`` without an owner (called for elements without an owning relationship)."""
    return element.get("@type") == "Namespace" and not reference_ids(element.get("owningRelatedElement"))


class QualifiedNameIndex:
    """Every element's qualified name in one corpus, and the reverse lookup (built once)."""

    def __init__(self, elements: Iterable[Mapping[str, Any]], *,
                 by_id: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self._by_id: Mapping[str, Mapping[str, Any]] = (
            by_id if by_id is not None
            else {identifier: item for item in elements if (identifier := element_id(item)) is not None}
        )
        #: element id -> name path; ``()`` marks a root namespace, ``None`` no qualified name.
        self._paths: dict[str, tuple[str, ...] | None] = {}
        for identifier in self._by_id:
            self._path(identifier)
        self._named: dict[tuple[str, ...], list[str]] = {}
        for identifier, path in self._paths.items():
            if path:
                self._named.setdefault(path, []).append(identifier)

    def _path(self, identifier: str) -> tuple[str, ...] | None:
        pending: list[str] = []  # members whose owner's path is not known yet
        current: str | None = identifier
        while True:
            if current is None:
                base = None
                break
            if current in self._paths:
                base = self._paths[current]
                break
            if current in pending:
                base = None  # an ownership cycle has no root
                break
            element = self._by_id.get(current)
            if element is None:
                base = None  # the owner is outside the corpus
                break
            owning = reference_ids(element.get("owningRelationship"))
            if not owning:
                base = () if _is_root_namespace(element) else None
                self._paths[current] = base
                break
            relationship = self._by_id.get(owning[0])
            if relationship is None or not _is_owning_membership(relationship):
                base = self._paths[current] = None
                break
            pending.append(current)
            owners = reference_ids(relationship.get("owningRelatedElement"))
            current = owners[0] if owners else None
        for member in reversed(pending):
            name = element_name(self._by_id[member])
            base = base + (name,) if base is not None and name else None
            self._paths[member] = base
        return self._paths.get(identifier)

    def path(self, identifier: str | None) -> tuple[str, ...] | None:
        """The unescaped name path of an element, or ``None``."""
        return self._paths.get(identifier or "") or None

    def qualified_name(self, identifier: str | None) -> str | None:
        path = self.path(identifier)
        return format_qualified_name(path) if path else None

    def resolve(self, identifier: str) -> tuple[Mapping[str, Any], ...]:
        """Every element whose qualified name is ``identifier`` (exact, all segments)."""
        path = parse_qualified_name(identifier)
        if path is None:
            return ()
        return tuple(self._by_id[found] for found in self._named.get(path, ()))

    def not_found_reason(self, identifier: str) -> str:
        """Why no element has the qualified name, and the canonical name where SysML reaches it.

        Gives the longest prefix that names one element. When that element reaches the
        next segment through a short name, an alias, an import or inheritance, says so
        and names the canonical qualified name; when an element's declared name is the
        identifier itself, says to quote it. Nothing here resolves the identifier.
        """
        path = parse_qualified_name(identifier)
        reasons = ["not a qualified name" if path is None else self._unmatched(path)]
        for found in self._declared_as(identifier)[:3]:
            kind = self._by_id[found].get("@type") or "element"
            canonical = self.qualified_name(found)
            reasons.append(f"{identifier!r} is the declared name of {kind} {found}; "
                           + (f"quote it as one segment: {canonical}" if canonical
                              else "it has no qualified name; resolve it by its UUID"))
        return "; ".join(reasons)

    def _unmatched(self, path: tuple[str, ...]) -> str:
        for length in range(len(path) - 1, 0, -1):
            found = self._named.get(path[:length], [])
            if len(found) == 1:
                namespace = self._by_id[found[0]]
                reason = (f"{format_qualified_name(path[:length])!r} is {namespace.get('@type') or 'an element'} "
                          f"{found[0]}, which has no owned member named {path[length]!r}")
                hint = self._reached_otherwise(found[0], path[length])
                return f"{reason}; {hint}" if hint else reason
            if found:
                return f"{format_qualified_name(path[:length])!r} names {len(found)} elements"
        return f"no root-level member is named {path[0]!r}"

    # -- how SysML reaches a segment other than by ownership (explanations only) --

    def _named_text(self, identifier: str) -> str:
        return self.qualified_name(identifier) or f"{identifier} (no qualified name)"

    def _relationships(self, identifier: str) -> list[Mapping[str, Any]]:
        owned = reference_ids(self._by_id.get(identifier, {}).get("ownedRelationship"))
        return [relationship for reference in owned if (relationship := self._by_id.get(reference)) is not None]

    def _owned_members(self, identifier: str) -> list[tuple[Mapping[str, Any], str]]:
        """(owning membership, member id) of what ``identifier`` owns; an alias owns nothing."""
        found = []
        for relationship in self._relationships(identifier):
            if relationship.get("@type") == "Membership" or not _is_owning_membership(relationship):
                continue
            found.extend((relationship, member) for member in reference_ids(relationship.get("memberElement"))
                         if member in self._by_id)
        return found

    def _members_named(self, identifier: str, segment: str) -> list[str]:
        """Every owned member of ``identifier`` named ``segment``, in order."""
        return [member for relationship, member in self._owned_members(identifier)
                if segment in (relationship.get("memberName"), element_name(self._by_id[member]))]

    def _reached_otherwise(self, namespace: str, segment: str) -> str | None:
        """How SysML reaches ``segment`` in ``namespace`` when no owned member has that name.

        Every way is collected: the short name of an owned member, an alias, a membership
        or namespace import (one level), a feature inherited through authored
        specializations. When they reach more than one element, the name is ambiguous
        there and the refusal lists each element's qualified name.
        """
        here = self._named_text(namespace)
        #: (element key, its qualified-name text, the clause for one path, the fragment in a list)
        paths: list[tuple[str, str, str, str]] = []
        for relationship, member in self._owned_members(namespace):
            element = self._by_id[member]
            if segment in (relationship.get("memberShortName"), element.get("declaredShortName"),
                           element.get("shortName")):
                paths.append((member, self._named_text(member),
                              f"is the short name of an owned member of {here}", "the short name of an owned member"))
        for relationship in self._relationships(namespace):
            if relationship.get("@type") == "Membership" and segment in (
                    relationship.get("memberName"), relationship.get("declaredName")):
                targets = [target for target in reference_ids(relationship.get("memberElement"))
                           if target in self._by_id]
                key = targets[0] if targets else f"alias {element_id(relationship)}"
                paths.append((key, self._named_text(targets[0]) if targets else "outside this corpus",
                              f"is an alias in {here}", "an alias"))
        for relationship in self._relationships(namespace):
            visibility = "public" if relationship.get("visibility") == "public" else "private"
            if relationship.get("@type") == "MembershipImport":
                for imported in reference_ids(relationship.get("importedMembership")):
                    membership = self._by_id.get(imported, {})
                    for member in reference_ids(membership.get("memberElement")):
                        if member in self._by_id and segment in (membership.get("memberName"),
                                                                 element_name(self._by_id[member])):
                            paths.append((member, self._named_text(member),
                                          f"is imported into {here} ({visibility} import)",
                                          f"imported by a {visibility} import"))
            elif relationship.get("@type") == "NamespaceImport":
                for imported in reference_ids(relationship.get("importedNamespace")):
                    if imported not in self._by_id:
                        continue
                    source = f"{self._named_text(imported)}::*"
                    paths.extend((member, self._named_text(member),
                                  f"is imported into {here} ({visibility} import of {source})",
                                  f"imported by a {visibility} import of {source}")
                                 for member in self._members_named(imported, segment))
        inherited, redefined = self._inherited(namespace, segment)
        paths.extend(inherited)
        reached: dict[str, tuple[str, str]] = {}
        for key, text, _clause, fragment in paths:
            reached.setdefault(key, (text, fragment))  # the first path to an element names it
        if len(reached) > 1:
            return (f"{segment!r} is ambiguous in {here}, where it names {len(reached)} elements: "
                    + ", ".join(f"{fragment} (its qualified name is {text})" for text, fragment in reached.values()))
        if paths:
            _key, text, clause, _fragment = paths[0]
            named = "the aliased element's qualified name" if clause.startswith("is an alias") else "its qualified name"
            return f"{segment!r} {clause}; {named} is {text}"
        return "; ".join(redefined) or None

    def _generals(self, identifier: str) -> list[str]:
        """The elements ``identifier`` specializes by authored specializations, in order."""
        found: list[str] = []
        for relationship in self._relationships(identifier):
            if relationship.get("@type") not in _SPECIALIZATIONS or relationship.get("isImplied"):
                continue
            for key in _GENERAL_KEYS:
                targets = reference_ids(relationship.get(key))
                if targets:
                    found.extend(target for target in targets if target in self._by_id and target != identifier)
                    break
        return found

    def _inherited(self, namespace: str, segment: str) -> tuple[list[tuple[str, str, str, str]], list[str]]:
        """The features named ``segment`` that ``namespace`` inherits through authored
        specializations, nearest general first, as paths; and those a feature of the type
        or of a general redefines, as explanations (they are not inherited)."""
        order: list[str] = []
        seen, frontier = {namespace}, [namespace]
        while frontier:  # nearest generals first
            for general in self._generals(frontier.pop(0)):
                if general not in seen:
                    seen.add(general)
                    order.append(general)
                    frontier.append(general)
        here = self._named_text(namespace)
        paths: list[tuple[str, str, str, str]] = []
        redefined: list[str] = []
        for general in order:
            for member in self._members_named(general, segment):
                canonical = self._named_text(member)
                redefiner = next(((owner, redefining) for owner in (namespace, *order)
                                  for _relationship, redefining in self._owned_members(owner)
                                  if redefining != member and member in self._redefined(redefining)), None)
                if redefiner is None:
                    paths.append((member, canonical, f"is inherited by {here} from {self._named_text(general)}",
                                  f"inherited from {self._named_text(general)}"))
                else:
                    owner, redefining = redefiner
                    redefined.append(f"{segment!r} is a feature of {self._named_text(general)} that "
                                     f"{self._named_text(owner)} redefines ({self._named_text(redefining)}); "
                                     f"its qualified name is {canonical}")
        return paths, redefined

    def _redefined(self, feature: str) -> set[str]:
        """Every feature ``feature`` redefines, directly or through what it redefines."""
        found: set[str] = set()
        frontier = [feature]
        while frontier:
            for relationship in self._relationships(frontier.pop()):
                if relationship.get("@type") != "Redefinition":
                    continue
                for target in reference_ids(relationship.get("redefinedFeature")):
                    if target not in found:
                        found.add(target)
                        frontier.append(target)
        return found

    def _declared_as(self, identifier: str) -> list[str]:
        """Elements whose declared name contains ``::`` and is ``identifier`` itself."""
        verbatim = getattr(self, "_verbatim", None)
        if verbatim is None:
            verbatim = {}
            for found, element in self._by_id.items():
                name = element.get("declaredName") or element.get("name")
                if isinstance(name, str) and "::" in name:
                    verbatim.setdefault(name, []).append(found)
            self._verbatim = verbatim
        return sorted(verbatim.get(identifier, ()))


__all__ = ["QualifiedNameIndex", "RESERVED_KEYWORDS", "element_name", "escape_name",
           "format_qualified_name", "parse_qualified_name"]
