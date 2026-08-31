"""Revision-scoped ontology class to SysML API element binding."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from de4sdv.sysml_api.errors import AmbiguousIdentityError, IdentityNotFoundError
from de4sdv.sysml_api.repository import SysMLRepository, element_id

from .kernel_contract import KernelContract, KernelFileMapping

_DECLARATION = re.compile(r"^(.+?)\s+def\s+([A-Za-z][A-Za-z0-9_]*)$")


@dataclass(frozen=True)
class BoundSysMLElement:
    project_id: str
    commit_id: str
    element_id: str
    type: str
    qualified_name: str | None


@dataclass(frozen=True)
class OntologyClassBinding:
    ontology_class: str
    kernel: KernelFileMapping
    sysml: BoundSysMLElement


def declaration_identity(declaration: str) -> tuple[str, str]:
    match = _DECLARATION.fullmatch(" ".join(declaration.split()))
    if not match:
        raise ValueError(f"unsupported kernel declaration syntax: {declaration!r}")
    kind, name = match.groups()
    kind_words = kind.split()
    if kind_words and kind_words[0] == "variation":
        kind_words = kind_words[1:]
    special = {"enum": "Enumeration", "use case": "UseCase"}
    normalized_kind = " ".join(kind_words)
    type_stem = special.get(
        normalized_kind,
        "".join(word[:1].upper() + word[1:] for word in kind_words),
    )
    return name, f"{type_stem}Definition"


class OntologyApiBinder:
    """Resolve exact file/declaration mappings against one API revision."""

    def __init__(
        self,
        contract: KernelContract,
        repository: SysMLRepository,
        *,
        project_id: str,
        commit_id: str,
    ) -> None:
        self.contract = contract
        self.repository = repository
        self.project_id = project_id
        self.commit_id = commit_id
        self._elements: list[dict[str, Any]] | None = None

    def _all_elements(self) -> list[dict[str, Any]]:
        if self._elements is None:
            self._elements = self.repository.list_elements(
                self.project_id, self.commit_id
            )
        return self._elements

    def bind_class(self, ontology_class: str) -> OntologyClassBinding:
        kernel = self.contract.class_mapping(ontology_class)
        name, expected_type = declaration_identity(kernel.declaration)
        candidates = [
            item
            for item in self._all_elements()
            if item.get("@type") == expected_type
            and (item.get("declaredName") or item.get("name")) == name
        ]
        if not candidates:
            raise IdentityNotFoundError(
                f"{ontology_class} mapping {kernel.file}::{kernel.declaration} "
                f"did not resolve to a {expected_type} in project "
                f"{self.project_id} commit {self.commit_id}"
            )
        if len(candidates) > 1:
            ids = sorted(str(element_id(item)) for item in candidates)
            raise AmbiguousIdentityError(
                f"{ontology_class} mapping {kernel.file}::{kernel.declaration} "
                f"resolved ambiguously: {ids}"
            )
        candidate = candidates[0]
        candidate_id = element_id(candidate)
        if candidate_id is None:
            raise IdentityNotFoundError(
                f"resolved {ontology_class} element has no API identifier"
            )
        return OntologyClassBinding(
            ontology_class=ontology_class,
            kernel=kernel,
            sysml=BoundSysMLElement(
                project_id=self.project_id,
                commit_id=self.commit_id,
                element_id=candidate_id,
                type=str(candidate["@type"]),
                qualified_name=(
                    str(candidate["qualifiedName"])
                    if candidate.get("qualifiedName") is not None
                    else None
                ),
            ),
        )
