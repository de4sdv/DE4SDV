"""Kernel identity grounding from governed source location.

The API element listing carries no per-element source-file provenance, so a
type plus short-name match alone cannot establish that an element IS the
declaration a governed kernel file names: any package can declare the same
name. Two independent grounding mechanisms exist:

- Ingestion-side validation (``de4sdv.semantic.validation``) binds by exact
  file provenance recorded per element UUID by the adapter.
- Runtime binding (``de4sdv.semantic.api_binding`` and the traversal
  specialization exclusion) binds by package ownership chain: the governed
  kernel file fixes the package path of the declaration, and a candidate
  matches only when its ``OwningMembership`` chain reaches the same package
  path.

Both fail closed: missing or ambiguous grounding raises instead of silently
widening. A same-named declaration outside the governed kernel file can
never borrow the mapping, and a missing canonical root fails closed even
when an unrelated homonym survives.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from de4sdv.sysml_api.errors import AmbiguousIdentityError, IdentityNotFoundError
from de4sdv.sysml_api.repository import element_id

from .kernel_contract import KernelFileMapping, declaration_identity

_DECL_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
_EVENT = re.compile(
    r"package\s+(?P<pkg>[A-Za-z_][A-Za-z0-9_]*)|(?P<open>\{)|(?P<close>\})"
)


@lru_cache(maxsize=64)
def kernel_package_path(kernel_file: str, declaration: str) -> tuple[str, ...]:
    """Enclosing package path of one declaration in a kernel file.

    Comments are blanked first, the declaration is located in the active
    code, and the package nesting at its position is returned
    (outermost first). A kernel file whose declaration sits outside any
    braced package, or that does not declare the mapped name at all, fails
    closed: such a mapping cannot ground a runtime identity.
    """
    text = Path(kernel_file).read_text(encoding="utf-8")
    text = re.sub(
        r"/\*.*?\*/", lambda match: " " * len(match.group(0)), text, flags=re.DOTALL
    )
    tokens = _DECL_TOKEN.findall(" ".join(declaration.split()))
    if not tokens:
        raise ValueError(f"unsupported kernel declaration syntax: {declaration!r}")
    declaration_re = re.compile(
        r"\b" + r"\s+".join(re.escape(token) for token in tokens) + r"\b"
    )
    found = declaration_re.search(text)
    if found is None:
        raise IdentityNotFoundError(
            f"kernel file {kernel_file} does not declare {declaration!r} "
            f"in active code"
        )
    stack: list[str] = []
    pushed_depths: list[int] = []
    depth = 0
    for match in _EVENT.finditer(text, 0, found.start()):
        if match.group("pkg"):
            stack.append(match.group("pkg"))
            pushed_depths.append(depth)
        elif match.group("open"):
            depth += 1
        else:
            depth -= 1
            if pushed_depths and pushed_depths[-1] == depth:
                stack.pop()
                pushed_depths.pop()
    if not stack:
        raise IdentityNotFoundError(
            f"declaration {declaration!r} in {kernel_file} sits outside any "
            f"braced package path"
        )
    return tuple(stack)


def _owner_map(by_id: dict[str, dict[str, Any]]) -> dict[str, str]:
    """memberElement id -> owningRelatedElement id from OwningMembership."""
    owner_of: dict[str, str] = {}
    for element in by_id.values():
        if str(element.get("@type")) != "OwningMembership":
            continue
        member = element.get("memberElement")
        owner = element.get("owningRelatedElement")
        member_id = member.get("@id") if isinstance(member, dict) else None
        owner_id = owner.get("@id") if isinstance(owner, dict) else None
        if member_id and owner_id:
            owner_of[member_id] = owner_id
    return owner_of


def _owned_package_path(
    candidate_id: str,
    by_id: dict[str, dict[str, Any]],
    owner_of: dict[str, str],
) -> tuple[str, ...]:
    """Named packages on the ownership chain, nearest owner first."""
    names: list[str] = []
    current = candidate_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        current = owner_of.get(current)
        if current is None:
            break
        parent = by_id.get(current)
        if parent is None:
            break
        if str(parent.get("@type")) == "Package":
            name = parent.get("declaredName") or parent.get("name")
            if name:
                names.append(str(name))
    return tuple(names)


def ground_kernel_declaration(
    kernel: KernelFileMapping, by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Resolve the one API element the governed kernel file declares.

    A candidate must match the declared type and name AND carry governed
    location evidence, in one of two forms (the first is authoritative when
    present):

    - a populated ``qualifiedName`` equal to the kernel file's package path
      joined with the declared name, or
    - an ``OwningMembership`` ownership chain reaching the same package path.

    Zero type/name candidates, zero grounded candidates, and multiple
    grounded candidates all fail closed with distinct diagnostics.
    """
    declaration_name, expected_type = declaration_identity(kernel.declaration)
    candidates = [
        element
        for element in by_id.values()
        if str(element.get("@type")) == expected_type
        and (element.get("declaredName") or element.get("name")) == declaration_name
    ]
    if not candidates:
        raise IdentityNotFoundError(
            f"kernel mapping {kernel.file}::{kernel.declaration} resolved to no "
            f"{expected_type} element"
        )
    expected_path = kernel_package_path(kernel.file, kernel.declaration)
    expected_qualified = "::".join((*expected_path, declaration_name))
    owner_of = _owner_map(by_id)
    grounded: list[tuple[str, dict[str, Any]]] = []
    actual_paths: list[tuple[str, str]] = []
    for element in candidates:
        candidate_id = element_id(element)
        if candidate_id is None:
            continue
        qualified_name = element.get("qualifiedName")
        if qualified_name:
            actual = str(qualified_name)
            actual_paths.append((candidate_id, repr(actual)))
            if actual == expected_qualified:
                grounded.append((candidate_id, element))
            continue
        actual = tuple(reversed(_owned_package_path(candidate_id, by_id, owner_of)))
        actual_paths.append((candidate_id, repr(actual)))
        if actual == expected_path:
            grounded.append((candidate_id, element))
    if not grounded:
        locations = "; ".join(
            f"{candidate_id} at {location}" for candidate_id, location in sorted(actual_paths)
        )
        raise IdentityNotFoundError(
            f"kernel mapping {kernel.file}::{kernel.declaration} has "
            f"{len(candidates)} type/name candidate(s) but none owned by package "
            f"path {expected_path}; candidate locations: {locations}. A same-named "
            f"declaration outside the governed kernel file does not ground the "
            f"mapping."
        )
    if len(grounded) > 1:
        ids = sorted(candidate_id for candidate_id, _ in grounded)
        raise AmbiguousIdentityError(
            f"kernel mapping {kernel.file}::{kernel.declaration} grounded "
            f"ambiguously at package path {expected_path}: {ids}"
        )
    return grounded[0][1]
