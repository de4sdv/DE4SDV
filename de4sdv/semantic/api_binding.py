"""Revision-scoped ontology class to SysML API element binding."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from de4sdv.sysml_api.errors import AmbiguousIdentityError, IdentityNotFoundError
from de4sdv.sysml_api.repository import SysMLRepository, element_id

from .identity_grounding import ground_kernel_declaration
from .kernel_contract import (
    KernelContract,
    KernelFileMapping,
    declaration_identity,
)


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
        self._by_id_cache: dict[str, dict[str, Any]] | None = None

    def _all_elements(self) -> list[dict[str, Any]]:
        if self._elements is None:
            self._elements = self.repository.list_elements(
                self.project_id, self.commit_id
            )
        return self._elements

    def _by_id(self) -> dict[str, dict[str, Any]]:
        if self._by_id_cache is None:
            self._by_id_cache = {
                candidate_id: item
                for item in self._all_elements()
                if (candidate_id := element_id(item)) is not None
            }
        return self._by_id_cache

    def bind_class(self, ontology_class: str) -> OntologyClassBinding:
        kernel = self.contract.class_mapping(ontology_class)
        name, expected_type = declaration_identity(kernel.declaration)
        # Grounding is by governed source location, not type+name: any
        # package can declare the same short name, so the candidate must be
        # owned through the exact package path parsed from the kernel file.
        candidate = ground_kernel_declaration(kernel, self._by_id())
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
