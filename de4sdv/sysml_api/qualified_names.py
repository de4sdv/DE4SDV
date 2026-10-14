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
  name that is not a basic name is written as an unrestricted name, in single
  quotes with ``\\`` escapes;
- an element without a complete chain of named namespaces up to a root has no
  qualified name: an unnamed element or owner, an element owned through a
  relationship that is not an owning membership, or an owner outside the
  corpus. A root namespace is an unnamed element without an owner that is not a
  relationship. A named element without an owner lost its owner to the export
  boundary (the export removes references to elements it does not carry), so
  neither it nor its members are named from it.

Where several elements share a qualified name (KerML names only the first),
each keeps it and resolving the name reports the ambiguity.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from .repository import element_id, reference_ids

_BASIC_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
#: KerML escape sequences of an unrestricted name, by the character after ``\``.
_UNESCAPE = {"'": "'", '"': '"', "\\": "\\", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
_ESCAPE = {"'": "\\'", "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_BLANKS = " \t"


def escape_name(name: str) -> str:
    """``name`` as written in a qualified name: as is when basic, else quoted."""
    if _BASIC_NAME.match(name):
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
    return element_name(element) is None and not reference_ids(element.get("owningRelatedElement"))


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
        """Why no element has the qualified name: the longest prefix that names one element."""
        path = parse_qualified_name(identifier)
        if path is None:
            return "not a qualified name"
        for length in range(len(path) - 1, 0, -1):
            found = self._named.get(path[:length], [])
            if len(found) == 1:
                namespace = self._by_id[found[0]]
                return (f"{format_qualified_name(path[:length])!r} is {namespace.get('@type') or 'an element'} "
                        f"{found[0]}, which has no owned member named {path[length]!r}")
            if found:
                return f"{format_qualified_name(path[:length])!r} names {len(found)} elements"
        return f"no root-level member is named {path[0]!r}"


__all__ = ["QualifiedNameIndex", "element_name", "escape_name", "format_qualified_name",
           "parse_qualified_name"]
