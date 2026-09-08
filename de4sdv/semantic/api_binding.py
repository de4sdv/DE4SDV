"""Revision-scoped ontology class to SysML API element binding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import SysMLRepository, element_id

from .kernel_binding_index import KernelBindingIndex
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
    """Bind file-mapped ontology classes to API elements via validated UUIDs.

    Identity is never re-derived at runtime: the revision binding carries
    ingestion-validated kernel bindings (API type/name confirmed against
    serializer-recorded source-document provenance), and this binder pins
    those exact UUIDs against the bound API revision. A class without a
    validated binding fails closed.
    """

    def __init__(
        self,
        contract: KernelContract,
        repository: SysMLRepository,
        *,
        project_id: str,
        commit_id: str,
        kernel_bindings: KernelBindingIndex | None = None,
    ) -> None:
        self.contract = contract
        self.repository = repository
        self.project_id = project_id
        self.commit_id = commit_id
        self.kernel_bindings = kernel_bindings
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
        _, expected_type = declaration_identity(kernel.declaration)
        if self.kernel_bindings is None:
            raise IdentityNotFoundError(
                f"no validated kernel binding index is available; ontology class "
                f"{ontology_class!r} cannot be resolved without ingestion-validated "
                f"binding metadata"
            )
        # Runtime identity comes exclusively from ingestion-validated
        # binding metadata: no name matching, no source-text parsing.
        candidate_id = self.kernel_bindings.element_id_for(
            ontology_class, self._by_id()
        )
        candidate = self._by_id()[candidate_id]
        actual_type = str(candidate.get("@type"))
        if actual_type != expected_type:
            raise IdentityNotFoundError(
                f"validated binding for {ontology_class!r} points at element "
                f"{candidate_id!r} of type {actual_type!r}, contradicting "
                f"governed declaration {kernel.declaration!r} "
                f"(expected {expected_type})"
            )
        return OntologyClassBinding(
            ontology_class=ontology_class,
            kernel=kernel,
            sysml=BoundSysMLElement(
                project_id=self.project_id,
                commit_id=self.commit_id,
                element_id=candidate_id,
                type=actual_type,
                qualified_name=(
                    str(candidate["qualifiedName"])
                    if candidate.get("qualifiedName") is not None
                    else None
                ),
            ),
        )
