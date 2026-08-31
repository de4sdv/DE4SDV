"""Explicit, ambiguity-safe SysML element identity resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .errors import AmbiguousIdentityError, IdentityNotFoundError
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
) -> IdentityResolution | None:
    if len(candidates) > 1:
        ids = sorted(candidate for item in candidates if (candidate := element_id(item)))
        raise AmbiguousIdentityError(
            f"ambiguous SysML identity {identifier!r} at {level}: {ids}"
        )
    if candidates:
        return IdentityResolution(level, candidates[0])
    return None


def resolve_identity(
    identifier: str,
    elements: list[dict[str, Any]],
    *,
    expected_type: str | None = None,
    owner_id: str | None = None,
) -> IdentityResolution:
    """Resolve one API element without name-only merging.

    Resolution proceeds from revision-scoped UUID through explicit identifiers
    and qualified identity. A simple-name structural match is accepted only
    when it is unique after optional type/owner constraints.
    """
    exact = [item for item in elements if element_id(item) == identifier]
    if result := _one(identifier, "exact", exact):
        return result

    explicit = [
        item
        for item in elements
        if identifier in {str(alias) for alias in item.get("aliasIds", [])}
        or identifier == str(item.get("reqId") or "")
        or identifier == str(item.get("declaredShortName") or item.get("shortName") or "")
    ]
    if result := _one(identifier, "stable-explicit-id", explicit):
        return result

    qualified = [
        item for item in elements if str(item.get("qualifiedName") or "") == identifier
    ]
    if result := _one(identifier, "qualified-name-match", qualified):
        return result

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
    if result := _one(identifier, "structural-match", structural):
        return result
    raise IdentityNotFoundError(f"SysML identity not found: {identifier!r}")