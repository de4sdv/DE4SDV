"""Runtime assembly for revision-bound DE4SDV semantic services."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.repository import SysMLRepository
from de4sdv.sysml_api.revisions import RevisionBinding

from .api_binding import OntologyApiBinder
from .authority_ids import LEGACY_AUTHORITY_ID
from .impact import ImpactService
from .kernel_binding_index import KernelBindingIndex
from .kernel_contract import KernelContract
from .o3_bundle import O3ImpactService
from .query import SemanticQueryService
from .traversal import SemanticTraversal

ROOT = Path(__file__).resolve().parents[2]


def build_semantic_runtime(
    *,
    api_url: str,
    binding_path: Path,
    expected_git_revision: str,
    ontology_path: Path,
    api_timeout: float = 600.0,
    method_conformance: Any = None,
    method_context_provider: Any = None,
    semantic_authority: "dict[str, Any] | str | Path | None" = None,
) -> SemanticQueryService:
    """Assemble the existing API-first semantic architecture for one revision.

    The function creates no model copy and performs no writes. Binding
    validity, expected-Git equality, and the exact full-model or fixture
    scope are enforced by every semantic operation through
    :class:`SemanticQueryService`; only a validated full-model binding can
    make a current-baseline claim. Kernel identity comes exclusively from
    the ingestion-validated kernel bindings carried by the revision binding
    (ADR 0011: no runtime source-text parsing); classes without a validated
    binding fail closed.

    ``method_conformance`` and ``method_context_provider`` optionally attach
    the Lane C method-conformance surfaces; a runtime without them reports
    the method queries as not configured rather than fabricating an
    evaluation.

    ``semantic_authority`` explicitly selects the authority path:

    - ``None`` (production default): the legacy authored ``KernelContract``
      path — behaviorally unchanged;
    - a CLOSED O3 candidate bundle (document dict, str, or path to the
      bundle JSON): the reviewed 13 migrated identities resolve exclusively
      through the verified candidate bundle (Semantic Projection semantics +
      API Representation Profile mechanics), every other identity delegates
      to the legacy contract. The bundle must carry a structured
      exact-revision API closure attestation matching this binding; an
      unclosed or mismatched bundle fails closed. There is no implicit
      fallback between the two paths and never two providers for one
      identity.

    ``semantic_authority_id`` on the returned service labels the authority
    path for provenance and cache/snapshot identity; it never changes query
    semantics.
    """
    binding = RevisionBinding.load(binding_path)
    contract = KernelContract.load(ontology_path)
    binding.require_ontology(contract.identity)
    authority: Any = contract
    authority_id = LEGACY_AUTHORITY_ID
    impact_service: ImpactService
    if semantic_authority is not None:
        from .o3_bundle import load_o3_authority

        o3_authority = load_o3_authority(
            semantic_authority,
            root=ROOT,
            contract=contract,
            binding=binding,
            binding_sha256=(
                "sha256:" + hashlib.sha256(binding_path.read_bytes()).hexdigest()
            ),
            expected_git_revision=expected_git_revision,
        )
        authority = o3_authority.facade
        authority_id = o3_authority.authority_id
    kernel_bindings = KernelBindingIndex.from_binding(binding)
    repository = SysMLRepository(ApiClient(api_url, timeout=api_timeout))
    binder = OntologyApiBinder(
        authority,
        repository,
        project_id=binding.sysml_project_id,
        commit_id=binding.sysml_commit_id,
        kernel_bindings=kernel_bindings,
    )
    traversal = SemanticTraversal(authority, kernel_bindings=kernel_bindings)
    if semantic_authority is None:
        impact_service = ImpactService(
            repository=repository,
            binding=binding,
            contract=authority,
            binder=binder,
            traversal=traversal,
        )
    else:
        impact_service = O3ImpactService(
            repository=repository,
            binding=binding,
            contract=authority,
            binder=binder,
            traversal=traversal,
        )
        impact_service.semantic_authority_id = authority_id
    return SemanticQueryService(
        repository=repository,
        binding=binding,
        contract=authority,
        binder=binder,
        traversal=traversal,
        impact_service=impact_service,
        expected_git_revision=expected_git_revision,
        method_conformance=method_conformance,
        method_context_provider=method_context_provider,
        semantic_authority_id=authority_id,
    )
