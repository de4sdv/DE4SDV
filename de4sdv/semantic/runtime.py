"""Runtime assembly for revision-bound DE4SDV semantic services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.repository import SysMLRepository
from de4sdv.sysml_api.revisions import RevisionBinding

from .api_binding import OntologyApiBinder
from .impact import ImpactService
from .kernel_binding_index import KernelBindingIndex
from .kernel_contract import KernelContract
from .query import SemanticQueryService
from .traversal import SemanticTraversal


def build_semantic_runtime(
    *,
    api_url: str,
    binding_path: Path,
    expected_git_revision: str,
    ontology_path: Path,
    api_timeout: float = 600.0,
    method_conformance: Any = None,
    method_context_provider: Any = None,
) -> SemanticQueryService:
    """Assemble the existing API-first semantic architecture for one revision.

    The function creates no model copy and performs no writes. Binding validity,
    expected-Git equality, and the exact full-model or fixture scope are
    enforced by every semantic operation through
    :class:`SemanticQueryService`; only a validated full-model binding can make
    a current-baseline claim. Kernel identity comes exclusively from the
    ingestion-validated kernel bindings carried by the revision binding
    (ADR 0011: no runtime source-text parsing); classes without a validated
    binding fail closed.

    ``method_conformance`` and ``method_context_provider`` optionally attach
    the Lane C method-conformance surfaces; a runtime without them reports the
    method queries as not configured rather than fabricating an evaluation.
    """
    binding = RevisionBinding.load(binding_path)
    contract = KernelContract.load(ontology_path)
    binding.require_ontology(contract.identity)
    kernel_bindings = KernelBindingIndex.from_binding(binding)
    repository = SysMLRepository(ApiClient(api_url, timeout=api_timeout))
    binder = OntologyApiBinder(
        contract,
        repository,
        project_id=binding.sysml_project_id,
        commit_id=binding.sysml_commit_id,
        kernel_bindings=kernel_bindings,
    )
    traversal = SemanticTraversal(contract, kernel_bindings=kernel_bindings)
    impact_service = ImpactService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=binder,
        traversal=traversal,
    )
    return SemanticQueryService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=binder,
        traversal=traversal,
        impact_service=impact_service,
        expected_git_revision=expected_git_revision,
        method_conformance=method_conformance,
        method_context_provider=method_context_provider,
    )
