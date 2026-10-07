"""Non-production bootstrap verification; live query code receives constructed authority.

This is construction machinery, not a query-time source of reviewed decisions.
It preserves the frozen O3 build and binds current sidecar implementation bytes
separately. Entrypoints opt in through arguments; production activation refuses.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Any

from . import definition_candidate, definition_migration, runtime_composition
from .authority_selection import AuthoritySelectionError, build_selected_semantic_runtime, resolve_authority_selection
from .kernel_contract import KernelContract
from .o3_bundle import load_o3_authority
from .runtime_composition import COMPOSITION, CompositeAuthority, CompositeImpactService, CompositeQueryService, composition_identity
from de4sdv.sysml_api import client, repository
from . import model_edges, relationships

ROOT = Path(__file__).resolve().parents[2]
SIDECAR_FILES = (
    "de4sdv/semantic/composition_construction.py",
    "de4sdv/semantic/runtime_composition.py",
    "de4sdv/semantic/definition_candidate.py",
    "de4sdv/semantic/definition_migration.py",
    "de4sdv/semantic/definition_candidate_provider.py",
    "de4sdv/sysml_api/client.py",
    "de4sdv/sysml_api/repository.py",
    "de4sdv/semantic/model_edges.py",
    "de4sdv/semantic/relationships.py",
)


def implementation_manifest(provider) -> dict:
    """Bind the executed sidecar sources, refusing externally substituted code.

    Candidate generation inputs and the frozen O3 implementation are verified
    by their own components. These current construction/provider/transport/graph
    sources are bound separately, never added to the frozen O3 input set.
    """
    sources = {
        SIDECAR_FILES[0]: __file__,
        SIDECAR_FILES[1]: runtime_composition.__file__,
        SIDECAR_FILES[2]: inspect.getsourcefile(definition_candidate.load_definition_candidate),
        SIDECAR_FILES[3]: inspect.getsourcefile(definition_migration.load_definition_migration_authority),
        SIDECAR_FILES[4]: inspect.getsourcefile(type(provider)),
        SIDECAR_FILES[5]: inspect.getsourcefile(client.ApiClient),
        SIDECAR_FILES[6]: inspect.getsourcefile(repository.SysMLRepository),
        SIDECAR_FILES[7]: model_edges.__file__,
        SIDECAR_FILES[8]: relationships.__file__,
    }
    files = {}
    for relative in SIDECAR_FILES:
        actual = sources[relative]
        expected = ROOT / relative
        if actual is None or Path(actual).resolve() != expected.resolve():
            raise AuthoritySelectionError(f"unexpected implementation source for {relative}")
        files[relative] = "sha256:" + hashlib.sha256(expected.read_bytes()).hexdigest()
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return {"schema": "de4sdv.o4-composition-implementation/v1", "files": files,
            "id": "o4-runtime-" + hashlib.sha256(encoded).hexdigest()}


def build_composed_semantic_runtime(*, api_url: str, binding_path: Path,
        expected_git_revision: str, ontology_path: Path, semantic_authority: Any,
        api_timeout: float = 600.0, method_conformance: Any = None,
        method_context_provider: Any = None, require_activation_eligible: bool = False,
        production: bool = False, root: Path = ROOT):
    """Verify both authorities once, before assembling any live query service."""
    from de4sdv.sysml_api.revisions import RevisionBinding
    from .api_binding import OntologyApiBinder
    from .kernel_binding_index import KernelBindingIndex
    from .traversal import SemanticTraversal

    raw_binding = Path(binding_path).read_bytes()
    binding = RevisionBinding.from_dict(json.loads(raw_binding))
    binding.require_current(expected_git_revision)
    legacy = KernelContract.load(ontology_path)
    binding.require_ontology(legacy.identity)
    binding_digest = "sha256:" + hashlib.sha256(raw_binding).hexdigest()
    o3 = load_o3_authority(semantic_authority, root=root, contract=legacy,
        binding=binding, binding_sha256=binding_digest,
        expected_git_revision=expected_git_revision,
        require_activation_eligible=require_activation_eligible or production)
    candidate = definition_candidate.load_definition_candidate(root)
    definitions = definition_migration.load_definition_migration_authority(root,
        contract=legacy, binding=binding, candidate=candidate,
        require_activation_eligible=True, expected_git_revision=expected_git_revision)
    if production or require_activation_eligible:
        raise AuthoritySelectionError("O4 composition is non-production; activation remains blocked")
    manifest = implementation_manifest(definitions.provider)
    authority_id = composition_identity(bundle_id=o3.bundle_id, candidate=candidate,
        binding_digest=binding_digest, implementation_manifest=manifest)
    authority = CompositeAuthority(o3=o3, definitions=definitions, legacy=legacy,
        authority_id=authority_id, implementation_manifest=manifest)
    index = KernelBindingIndex.from_binding(binding)
    model_repository = repository.SysMLRepository(client.ApiClient(api_url, timeout=api_timeout))
    binder = OntologyApiBinder(authority, model_repository, project_id=binding.sysml_project_id,
        commit_id=binding.sysml_commit_id, kernel_bindings=index)
    traversal = SemanticTraversal(authority, kernel_bindings=index)
    impact = CompositeImpactService(repository=model_repository, binding=binding,
        contract=authority, binder=binder, traversal=traversal)
    impact.semantic_authority_id = authority_id
    service = CompositeQueryService(repository=model_repository, binding=binding,
        contract=authority, binder=binder, traversal=traversal, impact_service=impact,
        expected_git_revision=expected_git_revision, semantic_authority_id=authority_id,
        method_conformance=method_conformance, method_context_provider=method_context_provider)
    return service, authority


def build_successor_service(*, base_contract, contract, binding, repository,
                            expected_git_revision, root, production=False):
    """Verify source inputs once at bootstrap, before live service assembly."""
    if production:
        raise AuthoritySelectionError("relationship successor is non-production; activation refused")
    from .relationship_successor_contract import verify_contract
    from .relationship_successor import assemble_successor_service
    verify_contract(contract, root)
    return assemble_successor_service(base_contract=base_contract, contract=contract,
        binding=binding, repository=repository,
        expected_git_revision=expected_git_revision)


def build_relationship_successor_runtime(*, contract, production=False,
        require_activation_eligible=False, root=ROOT, predecessor="o3+definitions", **kwargs):
    """Argument-only successor; predecessor choice never reads environment.

    The legacy path is an explicit non-production supplied-API consumer, not a
    fallback when an O3 composition fails. Both paths keep global defaults intact.
    """
    if production or require_activation_eligible:
        raise AuthoritySelectionError("relationship successor is non-production; activation refused")
    if predecessor == "o3+definitions":
        prior, authority = build_composed_semantic_runtime(root=root, **kwargs)
        binding, model_repository = prior.binding, prior.repository
        expected = prior.expected_git_revision
    elif predecessor == "legacy":
        from de4sdv.sysml_api.revisions import RevisionBinding
        binding = RevisionBinding.load(Path(kwargs["binding_path"]))
        authority = KernelContract.load(kwargs["ontology_path"])
        expected = kwargs["expected_git_revision"]
        model_repository = repository.SysMLRepository(client.ApiClient(
            kwargs["api_url"], timeout=kwargs.get("api_timeout", 600.0)))
    else:
        raise AuthoritySelectionError(f"unknown successor predecessor: {predecessor!r}")
    service = build_successor_service(base_contract=authority, contract=contract,
        binding=binding, repository=model_repository,
        expected_git_revision=expected, root=root)
    return service, service.contract


_AUTHORITY_ENV = "DE4SDV_SEMANTIC_AUTHORITY"
_MODEL_KEYS = ("model_bundle_path", "model_bundle_id", "production", "require_activation_eligible",
               "validation_artifacts")


def build_explicit_semantic_runtime(*, composition: str | None = None, **kwargs) -> tuple[Any, Any]:
    """Shared bootstrap contract for every semantic consumer.

    Without a composition, ``authority``/``DE4SDV_SEMANTIC_AUTHORITY`` =
    ``model`` routes to the model-authority bundle
    (:mod:`model_authority_runtime`). Every other selection reaches the frozen
    ``authority_selection`` path with exactly the arguments it received
    before, so legacy and o3 (the rollback path) stay byte-identical.
    The selector is read inline and the model-authority runtime is imported
    only inside the ``model`` branch, so legacy/O3 construction never depends
    on it. Model-only arguments are refused outside a model selection. The
    explicit ``o3+definitions`` composition path is unchanged.
    """
    if composition is None:
        authority = kwargs.get("authority")
        environ = kwargs.get("environ")
        if authority is None:
            authority = (os.environ if environ is None else environ).get(_AUTHORITY_ENV, "")
        if str(authority or "").strip().lower() == "model":
            from . import model_authority_runtime as model

            if kwargs.get("bundle_path") is not None or kwargs.get("bundle_id") is not None:
                raise AuthoritySelectionError(
                    "model authority takes model_bundle_path/model_bundle_id, not O3 bundle arguments")
            runtime_args = {key: value for key, value in kwargs.items()
                            if key not in {"authority", "bundle_path", "bundle_id",
                                           "model_bundle_path", "model_bundle_id"}}
            service = model.build_model_authority_runtime(
                runtime_args.pop("root", model.ROOT), kwargs.get("model_bundle_path"),
                kwargs.get("model_bundle_id"), **runtime_args)
            return service, service.selection
        supplied = sorted(key for key in _MODEL_KEYS if kwargs.get(key) not in (None, False))
        if supplied:
            raise AuthoritySelectionError(
                f"model-authority arguments require authority='model': {supplied}")
        kwargs = {key: value for key, value in kwargs.items() if key not in _MODEL_KEYS}
        return build_selected_semantic_runtime(**kwargs)
    if composition != COMPOSITION:
        raise AuthoritySelectionError(f"unknown explicit runtime composition: {composition!r}")
    if kwargs.get("authority") != "o3":
        raise AuthoritySelectionError("composition requires explicit authority='o3'")
    selection = resolve_authority_selection(authority="o3", bundle_path=kwargs.get("bundle_path"),
        bundle_id=kwargs.get("bundle_id"), environ={})
    runtime_args = {key: value for key, value in kwargs.items()
                    if key not in {"authority", "bundle_path", "bundle_id", "environ"}}
    return build_composed_semantic_runtime(semantic_authority=selection.bundle_document,
                                          **runtime_args)
