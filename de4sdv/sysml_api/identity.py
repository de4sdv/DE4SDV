"""Explicit, ambiguity-safe SysML element identity resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .errors import AmbiguousIdentityError, IdentityNotFoundError
from .qualified_names import QualifiedNameIndex
from .repository import element_id

ResolutionLevel = Literal[
    "exact",
    "stable-explicit-id",
    "qualified-name-match",
    "structural-match",
]


@dataclass(frozen=True)
class IdentityResolution:
    level: ResolutionLevel
    element: dict[str, Any]


def _one(
    identifier: str,
    level: ResolutionLevel,
    candidates: list[dict[str, Any]],
    qualified_names: QualifiedNameIndex | None = None,
) -> IdentityResolution | None:
    if len(candidates) > 1:
        ids = sorted(candidate for item in candidates if (candidate := element_id(item)))
        described = ""
        if qualified_names is not None:
            by_id = {element_id(item): item for item in candidates}
            described = " (" + "; ".join(
                f"{candidate}: {by_id[candidate].get('@type') or 'element'} "
                f"{qualified_names.qualified_name(candidate) or '(no qualified name)'}"
                for candidate in ids
            ) + ")"
        raise AmbiguousIdentityError(
            f"ambiguous SysML identity {identifier!r} at {level}: {ids}{described}"
        )
    if candidates:
        return IdentityResolution(level, candidates[0])
    return None


def _qualified(
    identifier: str,
    qualified_names: QualifiedNameIndex | None,
    expected_type: str | None,
) -> IdentityResolution:
    """Resolve a qualified name by the computed names: exact, never a bare-name match."""
    if qualified_names is None:
        raise IdentityNotFoundError(
            f"SysML identity not found: {identifier!r} (a qualified name is matched exactly, "
            "never by a bare name, and no qualified names were computed for this corpus)"
        )
    candidates = list(qualified_names.resolve(identifier))
    if not candidates:
        raise IdentityNotFoundError(
            f"SysML identity not found: {identifier!r} (no element has this qualified name: "
            f"{qualified_names.not_found_reason(identifier)})"
        )
    if expected_type:
        typed = [item for item in candidates if item.get("@type") == expected_type]
        if not typed:
            found = ", ".join(sorted({str(item.get("@type") or "") for item in candidates}))
            raise IdentityNotFoundError(
                f"SysML identity not found: {identifier!r} is a {found}, not a {expected_type}"
            )
        candidates = typed
    if len(candidates) > 1:
        described = ", ".join(sorted(f"{element_id(item)} ({item.get('@type')})" for item in candidates))
        raise AmbiguousIdentityError(
            f"ambiguous SysML identity {identifier!r} at qualified-name-match: "
            f"{len(candidates)} elements share this qualified name: {described}"
        )
    return IdentityResolution("qualified-name-match", candidates[0])  # type: ignore[arg-type]


def resolve_identity(
    identifier: str,
    elements: list[dict[str, Any]],
    *,
    expected_type: str | None = None,
    owner_id: str | None = None,
    qualified_names: QualifiedNameIndex | None = None,
) -> IdentityResolution:
    """Resolve one API element without name-only merging.

    Resolution proceeds from revision-scoped UUID through explicit identifiers
    and qualified identity. A qualified name (``Package::Definition``) is
    matched against the ``qualifiedName`` an element carries, then against
    ``qualified_names``, the names computed from the corpus's ownership graph;
    it is matched exactly, by every segment, and never falls back to a name
    match. A simple-name structural match is accepted only when it is unique
    after optional type/owner constraints.
    """
    exact = [item for item in elements if element_id(item) == identifier]
    if result := _one(identifier, "exact", exact):
        return result

    explicit = [
        item
        for item in elements
        if identifier in {str(alias) for alias in item.get("aliasIds", [])}
        or identifier == str(item.get("reqId") or "")
        # Explicit identity is AUTHORED identity: declared short names only.
        # Resolved `shortName`/`name` fields appear on implied elements the
        # licensed serializer materializes (e.g. an implied PerformActionUsage
        # sharing a verification usage's short name with include_implied);
        # they must not create explicit-identity ambiguity.
        or identifier == str(item.get("declaredShortName") or "")
    ]
    if expected_type:
        # Normative conformance (frozen baseline Section 5): a resolved
        # explicit identifier must be type-compatible; otherwise the binding
        # is incompatible and errors instead of falling through to a
        # weaker match level.
        explicit = [
            item for item in explicit if item.get("@type") == expected_type
        ]
    if result := _one(identifier, "stable-explicit-id", explicit, qualified_names):
        return result

    qualified = [
        item for item in elements if str(item.get("qualifiedName") or "") == identifier
    ]
    if result := _one(identifier, "qualified-name-match", qualified):
        return result
    if "::" in identifier:
        return _qualified(identifier, qualified_names, expected_type)

    structural = []
    for item in elements:
        name = item.get("declaredName") or item.get("name")
        if str(name or "") != identifier:
            continue
        if expected_type and item.get("@type") != expected_type:
            continue
        if owner_id:
            owner = item.get("owner") or item.get("owningNamespace")
            if element_id(owner) != owner_id:
                continue
        structural.append(item)
    if result := _one(identifier, "structural-match", structural, qualified_names):
        return result
    raise IdentityNotFoundError(f"SysML identity not found: {identifier!r}")