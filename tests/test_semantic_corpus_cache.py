"""Persistent exact-revision corpus cache: Ask + MCP cold-start regressions.

Root cause (verified): the viewer snapshot path populated only
``service._element_cache``, leaving the shared repository empty, so impact
and the ontology binder refetched the full model; the MCP server had no
snapshot path at all.

These tests lock the shared mechanism in ``de4sdv/semantic/corpus_cache.py``
plus the explicit validated adoption method on the shared repository
(``SysMLRepository.adopt_elements``):

- cold miss performs exactly one retrieval and writes an identity-bound,
  checksum-verified snapshot;
- a restart (fresh process/service) serves ``model_status``, ``impact`` and
  the ontology binder with ZERO retrieval, for the viewer warmup path and
  for the lazy MCP hook (which never blocks the stdio handshake);
- any doubt (checksum mismatch, identity drift, malformed/duplicate/missing
  element UUIDs, partial cache, old format) fails safely to the exact API
  load — a snapshot is never a governing authority;
- tool output contracts are unchanged.

Transport counting uses the actual classes (``SysMLRepository``,
``ImpactService``, ``OntologyApiBinder``, ``SemanticQueryService``) over a
counting client stub; the MCP end-to-end test runs the real stdio server
script twice against a counting HTTP fixture.

``mcp.client.stdio`` is imported at collection time: it binds ``sys.stderr``
as the default errlog at import time, and importing it later while a pytest
capture fixture owns stderr poisons the default stream (see the semantic-MCP
pitfalls).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import mcp.client.stdio  # noqa: F401  (collection-time import; see module docstring)
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ONTOLOGY_PATH = REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"


def ontology_identity() -> dict[str, str]:
    return {
        "path": ONTOLOGY_PATH.relative_to(REPO_ROOT).as_posix(),
        "sha256": hashlib.sha256(ONTOLOGY_PATH.read_bytes()).hexdigest(),
    }


def ref(value: str) -> dict[str, str]:
    return {"@id": value}


def element_corpus() -> list[dict[str, Any]]:
    """The proven semantic fixture corpus (same shape as the MCP surface
    tests): a requirement with a native subject, a verification membership,
    a need-derivation connection and the kernel bindings they ground on."""
    return [
        {
            "@id": "kernel-requirement",
            "@type": "RequirementDefinition",
            "declaredName": "RequirementCandidate",
            "qualifiedName": "DE4SDV_MethodContext::RequirementCandidate",
        },
        {
            "@id": "kernel-requirement-derivation",
            "@type": "ConnectionDefinition",
            "declaredName": "DerivesFromNeed",
            "qualifiedName": "DE4SDV_MethodContext::DerivesFromNeed",
        },
        {
            "@id": "kernel-need",
            "@type": "RequirementDefinition",
            "declaredName": "StakeholderNeedCandidate",
            "qualifiedName": "DE4SDV_MethodContext::StakeholderNeedCandidate",
        },
        {
            "@id": "kernel-member-product",
            "@type": "PartDefinition",
            "declaredName": "ProductLineMemberProduct",
            "qualifiedName": "DE4SDV_ProductLine::ProductLineMemberProduct",
        },
        {
            "@id": "req-1",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
            "qualifiedName": "DE4SDV_AEBSNeedsRequirements::reqCommandEmergencyBraking",
            "documentation": [ref("doc-1")],
        },
        {
            "@id": "doc-1",
            "@type": "Documentation",
            "body": "Command emergency braking when the decision is active.",
        },
        {
            "@id": "subject-membership",
            "@type": "SubjectMembership",
            "owningRelatedElement": ref("req-1"),
            "memberElement": ref("product-1"),
        },
        {
            "@id": "product-1",
            "@type": "PartUsage",
            "declaredName": "memberProduct",
        },
        {
            "@id": "product-1-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("product-1"),
            "type": ref("kernel-member-product"),
            "typedFeature": ref("product-1"),
        },
        {
            "@id": "evidence-1",
            "@type": "RequirementUsage",
            "declaredName": "evidenceContractNominalBrakingPath",
        },
        {
            "@id": "dependency-1",
            "@type": "Dependency",
            "source": [ref("evidence-1")],
            "target": [ref("req-1")],
        },
        {
            "@id": "need-1",
            "@type": "RequirementUsage",
            "declaredName": "needCommonAEBSCapability",
            "qualifiedName": "DE4SDV_AEBSNeedsRequirements::needCommonAEBSCapability",
        },
        {
            "@id": "req-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("req-1"),
            "type": ref("kernel-requirement"),
            "typedFeature": ref("req-1"),
        },
        {
            "@id": "need-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("need-1"),
            "type": ref("kernel-need"),
            "typedFeature": ref("need-1"),
        },
        {
            "@id": "derivation-conn",
            "@type": "ConnectionUsage",
            "declaredName": "reqCommandEmergencyBrakingDerivation",
            "ownedRelationship": [
                ref("derivation-end-need"),
                ref("derivation-end-req"),
                ref("derivation-conn-typing"),
            ],
        },
        {
            "@id": "derivation-end-need",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": ref("derivation-conn"),
            "ownedRelatedElement": [ref("need-1")],
        },
        {
            "@id": "derivation-end-req",
            "@type": "EndFeatureMembership",
            "owningRelatedElement": ref("derivation-conn"),
            "ownedRelatedElement": [ref("req-1")],
        },
        {
            "@id": "derivation-conn-typing",
            "@type": "FeatureTyping",
            "owningRelatedElement": ref("derivation-conn"),
            "type": ref("kernel-requirement-derivation"),
            "typedFeature": ref("derivation-conn"),
        },
        {
            "@id": "verification-1",
            "@type": "VerificationCaseUsage",
            "declaredName": "nominalMovingVehicleTargetVerification",
        },
        {
            "@id": "rvm-1",
            "@type": "RequirementVerificationMembership",
            "owningRelatedElement": ref("verification-1"),
            "memberElement": ref("req-1"),
        },
    ]


class CountingClient:
    """Duck-typed ApiClient stand-in: counts element-listing retrievals."""

    def __init__(
        self,
        elements: list[dict[str, Any]] | None = None,
        *,
        base_url: str = "http://127.0.0.1:9",
    ) -> None:
        self.base_url = base_url
        self.elements = elements if elements is not None else element_corpus()
        self.element_retrievals = 0

    def get_all(self, path: str) -> list[dict[str, Any]]:
        assert "/elements?" in path, path
        self.element_retrievals += 1
        return list(self.elements)

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        raise AssertionError(f"unexpected request: {method} {path}")


def binding_dict(
    *,
    git_commit: str = "a" * 40,
    scope: str = "full-model",
    kernel_bindings: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if kernel_bindings is None:
        kernel_bindings = [
            {
                "ontology_class": "Requirement",
                "element_id": "kernel-requirement",
                "source_file": (
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                "declaration": "requirement def RequirementCandidate",
            },
            {
                "ontology_class": "MemberProduct",
                "element_id": "kernel-member-product",
                "source_file": (
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_product_line.sysml"
                ),
                "declaration": "part def ProductLineMemberProduct",
            },
            {
                "ontology_class": "Need",
                "element_id": "kernel-need",
                "source_file": (
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                "declaration": "requirement def StakeholderNeedCandidate",
            },
            {
                "ontology_class": "DerivesFromNeed",
                "element_id": "kernel-requirement-derivation",
                "source_file": (
                    "textual-notation-of-model/packages/methods/de4sdv/"
                    "de4sdv_method_context.sysml"
                ),
                "declaration": "connection def DerivesFromNeed",
            },
        ]
    return {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": git_commit,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-01T00:00:00Z",
        "import_tool_version": "fixture/1",
        "semantic_validation": "passed",
        "scope": scope,
        "ontology": ontology_identity(),
        "kernel_bindings": kernel_bindings,
    }


def build_service(
    client: CountingClient,
    *,
    scope: str = "full-model",
    expected_git_revision: str = "a" * 40,
    authority_id: str | None = None,
    binding_overrides: dict[str, Any] | None = None,
):
    """A real-class semantic runtime over the counting transport."""
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.impact import ImpactService
    from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.query import SemanticQueryService
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.repository import SysMLRepository
    from de4sdv.sysml_api.revisions import RevisionBinding

    payload = binding_dict(scope=scope)
    if binding_overrides:
        payload.update(binding_overrides)
    binding = RevisionBinding.from_dict(payload)
    contract = KernelContract.load(ONTOLOGY_PATH)
    repository = SysMLRepository(client)  # type: ignore[arg-type]
    kernel_index = KernelBindingIndex.from_binding(binding)
    binder = OntologyApiBinder(
        contract,
        repository,
        project_id="project-1",
        commit_id="commit-1",
        kernel_bindings=kernel_index,
    )
    traversal = SemanticTraversal(contract, kernel_bindings=kernel_index)
    impact = ImpactService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=binder,
        traversal=traversal,
    )
    service = SemanticQueryService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=binder,
        traversal=traversal,
        impact_service=impact,
        expected_git_revision=expected_git_revision,
    )
    if authority_id is not None:
        service.semantic_authority_id = authority_id
    return service


@pytest.fixture()
def snapshot_dir(tmp_path, monkeypatch):
    """A private corpus-snapshot directory for the process under test.

    Set through the deployment environment variable (not module state) so
    the stdio subprocess in the end-to-end test resolves the same location.
    """
    directory = tmp_path / "corpus-snapshots"
    monkeypatch.setenv("DE4SDV_SEMANTIC_SNAPSHOT_DIR", str(directory))
    return directory


# ---------------------------------------------------------------------------
# Slice 1: explicit validated repository adoption (the missing hydration path)
# ---------------------------------------------------------------------------


def test_repository_adopt_elements_serves_listings_without_retrieval():
    from de4sdv.sysml_api.repository import SysMLRepository

    client = CountingClient()
    repository = SysMLRepository(client)  # type: ignore[arg-type]
    corpus = element_corpus()

    adopted = repository.adopt_elements("project-1", "commit-1", corpus)

    assert adopted is True
    assert repository.list_elements("project-1", "commit-1") == corpus
    assert client.element_retrievals == 0


def test_repository_adopt_rejects_malformed_duplicate_and_missing_ids():
    from de4sdv.sysml_api.repository import SysMLRepository

    client = CountingClient()
    repository = SysMLRepository(client)  # type: ignore[arg-type]

    duplicates = [dict(item) for item in element_corpus()]
    duplicates.append({"@id": "req-1", "@type": "RequirementUsage"})
    missing_id = [{"@type": "RequirementUsage", "declaredName": "no-id"}]

    for bad in ([], "not-a-list", [42], missing_id, duplicates):
        with pytest.raises(ValueError):
            repository.adopt_elements("project-1", "commit-1", bad)

    # nothing was adopted: the repository still retrieves from the transport
    repository.list_elements("project-1", "commit-1")
    assert client.element_retrievals == 1


def test_repository_adopt_never_displaces_an_authoritative_listing():
    from de4sdv.sysml_api.repository import SysMLRepository

    client = CountingClient()
    repository = SysMLRepository(client)  # type: ignore[arg-type]
    authoritative = repository.list_elements("project-1", "commit-1")
    assert client.element_retrievals == 1

    other = [{"@id": "other-1", "@type": "PartUsage"}]
    adopted = repository.adopt_elements("project-1", "commit-1", other)

    assert adopted is False
    assert repository.list_elements("project-1", "commit-1") is authoritative
    assert client.element_retrievals == 1


# ---------------------------------------------------------------------------
# Slice 2: shared corpus-cache identity + persistent snapshot roundtrip
# ---------------------------------------------------------------------------


def _rewrite_snapshot(path: Path, mutate) -> None:
    """Mutate the snapshot payload and re-stamp the sidecar checksum.

    Re-stamping is what makes identity/shape checks the deciding gate —
    otherwise the checksum check would mask them.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")
    path.with_suffix(".json.sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest(), encoding="utf-8"
    )


def test_corpus_identity_binds_endpoint_binding_ontology_and_authority():
    from de4sdv.semantic import corpus_cache as cc

    service = build_service(CountingClient(base_url="http://sysml2-api:9000"))
    identity = cc.corpus_identity(service)

    assert identity["format"] == cc.CORPUS_SNAPSHOT_FORMAT
    assert identity["git_commit"] == "a" * 40
    assert identity["sysml_project_id"] == "project-1"
    assert identity["sysml_commit_id"] == "commit-1"
    assert identity["semantic_authority_id"] == service.semantic_authority_id
    assert identity["ontology"] == ontology_identity()
    assert len(identity["api_endpoint_digest"]) == 64
    assert len(identity["binding_digest"]) == 64

    # endpoint identity is a digest, and it changes with the endpoint
    other_endpoint = build_service(
        CountingClient(base_url="http://sysml2-api-other:9000")
    )
    assert (
        cc.corpus_identity(other_endpoint)["api_endpoint_digest"]
        != identity["api_endpoint_digest"]
    )

    # the binding digest covers the ingestion-validated kernel bindings
    reduced = build_service(
        CountingClient(),
        binding_overrides={"kernel_bindings": binding_dict()["kernel_bindings"][:1]},
    )
    assert (
        cc.corpus_identity(reduced)["binding_digest"]
        != cc.corpus_identity(build_service(CountingClient()))["binding_digest"]
    )

    # the semantic authority id is bound explicitly
    o3 = build_service(CountingClient(), authority_id="o3:o3b-deadbeef")
    assert cc.corpus_identity(o3)["semantic_authority_id"] == "o3:o3b-deadbeef"


def test_snapshot_roundtrip_never_exposes_credentials(snapshot_dir):
    from de4sdv.semantic import corpus_cache as cc

    service = build_service(
        CountingClient(base_url="http://deploy-user:secret-password@host:9000")
    )
    path = cc.write_corpus_snapshot(service, element_corpus())

    assert path.parent == snapshot_dir
    raw = path.read_text(encoding="utf-8")
    assert "secret-password" not in raw
    assert "deploy-user" not in raw
    # sidecar checksum of the main file
    assert path.with_suffix(".json.sha256").read_text().strip() == (
        hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert cc.load_corpus_snapshot(service) == element_corpus()


def test_snapshot_miss_on_checksum_identity_drift_and_malformed_payload(
    snapshot_dir,
):
    from de4sdv.semantic import corpus_cache as cc

    service = build_service(CountingClient())
    path = cc.write_corpus_snapshot(service, element_corpus())
    assert cc.load_corpus_snapshot(service) == element_corpus()

    # tampered content with a stale sidecar: checksum mismatch -> miss
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "reqCommandEmergencyBraking", "reqCommandEmergencyBrakingX"
        ),
        encoding="utf-8",
    )
    assert cc.load_corpus_snapshot(service) is None

    # identity drift inside a checksum-valid payload -> miss (never
    # reinterpretation). The old format (2) and payloads without the new
    # identity fields are old identity.
    cc.write_corpus_snapshot(service, element_corpus())
    for key, value in (
        ("git_commit", "b" * 40),
        ("sysml_project_id", "other-project"),
        ("sysml_commit_id", "other-commit"),
        ("format", cc.CORPUS_SNAPSHOT_FORMAT - 1),
        ("semantic_authority_id", "o3:o3b-deadbeef"),
        ("api_endpoint_digest", "0" * 64),
        ("binding_digest", "0" * 64),
        ("ontology", {"path": "other.yaml", "sha256": "0" * 64}),
    ):
        _rewrite_snapshot(path, lambda data, k=key, v=value: data.__setitem__(k, v))
        assert cc.load_corpus_snapshot(service) is None, key

    # old-format payloads simply lack the new fields
    _rewrite_snapshot(
        path, lambda data: [data.pop(k) for k in ("api_endpoint_digest",)]
    )
    assert cc.load_corpus_snapshot(service) is None

    # malformed / partial element payloads with valid checksums -> miss
    duplicates = element_corpus() + [{"@id": "req-1", "@type": "RequirementUsage"}]
    missing_id = element_corpus() + [{"@type": "RequirementUsage"}]
    for mutate in (
        lambda data: data.__setitem__("elements", duplicates),
        lambda data: data.__setitem__("elements", missing_id),
        lambda data: data.__setitem__("elements", "not-a-list"),
        lambda data: data.__setitem__("elements", []),
        lambda data: data.__setitem__("element_count", 999),
    ):
        _rewrite_snapshot(path, mutate)
        assert cc.load_corpus_snapshot(service) is None

    # a different endpoint (same authority/revision filename) never loads it
    cc.write_corpus_snapshot(service, element_corpus())
    other_endpoint = build_service(
        CountingClient(base_url="http://sysml2-api-other:9000")
    )
    assert cc.load_corpus_snapshot(other_endpoint) is None

    # a different semantic authority writes/reads a different file
    o3 = build_service(CountingClient(), authority_id="o3:o3b-deadbeef")
    assert cc.load_corpus_snapshot(o3) is None

    # truncated JSON -> miss
    path.write_text(path.read_text(encoding="utf-8")[:100], encoding="utf-8")
    assert cc.load_corpus_snapshot(service) is None


# ---------------------------------------------------------------------------
# Slice 3: snapshot-first load, explicit hydration, lazy hook
# ---------------------------------------------------------------------------


def test_cold_miss_retrieves_once_and_writes_snapshot(snapshot_dir):
    from de4sdv.semantic import corpus_cache as cc

    client = CountingClient()
    service = build_service(client)

    elements = cc.load_elements_with_snapshot(service)

    assert elements == element_corpus()
    assert client.element_retrievals == 1
    assert cc.load_corpus_snapshot(service) == element_corpus()
    # same process: no further retrieval, same corpus object served
    assert cc.load_elements_with_snapshot(service) == elements
    assert client.element_retrievals == 1


def test_restart_snapshot_hit_serves_status_impact_and_binder_with_zero_retrieval(
    snapshot_dir,
):
    """The verified root cause: on a snapshot hit the shared repository must
    be hydrated (not only ``service._element_cache``), otherwise impact and
    the ontology binder refetch the full model."""
    from de4sdv.semantic import corpus_cache as cc

    cold = build_service(CountingClient())
    cc.load_elements_with_snapshot(cold)
    assert cold.repository.client.element_retrievals == 1

    client = CountingClient()
    warm = build_service(client)
    loaded = cc.load_elements_with_snapshot(warm)

    assert client.element_retrievals == 0
    assert loaded == element_corpus()
    # the repository itself serves the revision (the missing hydration path)
    assert warm.repository.list_elements("project-1", "commit-1") == element_corpus()

    status = warm.model_status()
    impact = warm.impact("reqCommandEmergencyBraking")
    binder_binding = warm.binder.bind_class("Requirement")

    assert status["element_count"] == len(element_corpus())
    assert impact["root"]["element_id"] == "req-1"
    assert binder_binding.sysml.element_id == "kernel-requirement"
    assert client.element_retrievals == 0

    # output contracts are unchanged: snapshot-served results equal the
    # exact-API-served results for the same binding
    api_client = CountingClient()
    api_served = build_service(api_client)
    assert api_client.element_retrievals == 0
    assert warm.model_status() == api_served.model_status()
    assert warm.impact("reqCommandEmergencyBraking") == api_served.impact(
        "reqCommandEmergencyBraking"
    )
    assert api_client.element_retrievals == 1


def test_viewer_helper_hydrates_shared_repository(snapshot_dir, monkeypatch):
    """Root-cause regression on the viewer entry point itself."""
    from de4sdv.semantic import corpus_cache as cc  # noqa: F401
    from tools.sysml_html_viewer import ask_model_semantic as ams

    monkeypatch.setattr(ams, "_snapshot_dir", lambda: snapshot_dir)

    cold = build_service(CountingClient())
    ams._load_elements_with_snapshot(cold)  # cold: network load + snapshot write

    client = CountingClient()
    warm = build_service(client)
    loaded = ams._load_elements_with_snapshot(warm)

    assert client.element_retrievals == 0
    assert loaded == element_corpus()
    assert warm.repository.list_elements("project-1", "commit-1") == element_corpus()
    assert warm.impact("reqCommandEmergencyBraking")["root"]["element_id"] == "req-1"
    assert (
        warm.binder.bind_class("Requirement").sysml.element_id
        == "kernel-requirement"
    )
    assert client.element_retrievals == 0


def test_lazy_hook_install_does_not_block_and_serves_every_entry_point(
    snapshot_dir,
):
    """MCP wiring: installing the hook performs no I/O (handshake never
    blocks); the first listing of each fresh process is snapshot-served with
    zero retrieval, independently for status, impact and binder."""
    from de4sdv.semantic import corpus_cache as cc

    cold = build_service(CountingClient())
    cc.load_elements_with_snapshot(cold)

    client = CountingClient()
    service = build_service(client)
    cc.install_corpus_snapshot(service)
    assert client.element_retrievals == 0  # install is lazy

    exercises = (
        ("model_status", lambda s: s.model_status()["element_count"]),
        ("impact", lambda s: s.impact("reqCommandEmergencyBraking")["root"]),
        ("binder", lambda s: s.binder.bind_class("Requirement").sysml.element_id),
    )
    for name, exercise in exercises:
        client = CountingClient()
        fresh = build_service(client)
        cc.install_corpus_snapshot(fresh)
        result = exercise(fresh)
        assert result, name
        assert client.element_retrievals == 0, name


def test_invalidation_identity_drift_forces_exact_api_load(snapshot_dir):
    from de4sdv.semantic import corpus_cache as cc

    cold = build_service(CountingClient())
    cc.load_elements_with_snapshot(cold)

    drifted = (
        ("endpoint", dict(), "http://sysml2-api-other:9000", "a" * 40),
        (
            "kernel-bindings",
            {"binding_overrides": {"kernel_bindings": binding_dict()["kernel_bindings"][:1]}},
            "http://127.0.0.1:9",
            "a" * 40,
        ),
        (
            "git-commit",
            {
                "binding_overrides": {"git_commit": "b" * 40},
                "expected_git_revision": "b" * 40,
            },
            "http://127.0.0.1:9",
            "b" * 40,
        ),
    )
    for name, kwargs, base_url, _revision in drifted:
        client = CountingClient(base_url=base_url)
        service = build_service(client, **kwargs)
        loaded = cc.load_elements_with_snapshot(service)
        assert loaded == element_corpus(), name
        assert client.element_retrievals == 1, name  # exact API load, not the stale snapshot

    # a different semantic authority is a different snapshot file entirely
    client = CountingClient()
    o3 = build_service(client, authority_id="o3:o3b-deadbeef")
    assert cc.load_elements_with_snapshot(o3) == element_corpus()
    assert client.element_retrievals == 1


def test_malformed_snapshot_falls_back_to_exact_api_load_and_repairs(
    snapshot_dir,
):
    from de4sdv.semantic import corpus_cache as cc

    service = build_service(CountingClient())
    cc.load_elements_with_snapshot(service)
    path = cc.corpus_snapshot_path(service)
    path.write_text("{not json", encoding="utf-8")

    client = CountingClient()
    fresh = build_service(client)
    assert cc.load_elements_with_snapshot(fresh) == element_corpus()
    assert client.element_retrievals == 1  # malformed cache -> exact API load
    assert cc.load_corpus_snapshot(fresh) == element_corpus()  # repaired write-back


# ---------------------------------------------------------------------------
# Slice 4: the lazy hook is bound to the requested revision (critical fix)
# ---------------------------------------------------------------------------


def test_lazy_hook_source_never_serves_bound_snapshot_for_other_revision(
    snapshot_dir,
):
    """A snapshot is bound to ONE exact (project, commit): the installed
    source must never hand the bound snapshot to a listing of a different
    revision, and the sink must never write a different revision's corpus
    as the bound one."""
    from de4sdv.semantic import corpus_cache as cc

    cold = build_service(CountingClient())
    cc.load_elements_with_snapshot(cold)
    bound_snapshot = cc.corpus_snapshot_path(cold)

    other_revision_corpus = [
        {"@id": "other-1", "@type": "PartUsage", "declaredName": "otherRevision"},
    ]
    client = CountingClient(elements=other_revision_corpus)
    service = build_service(client)
    cc.install_corpus_snapshot(service)

    # another revision of the same repository: exact API load, never the
    # bound snapshot
    assert (
        service.repository.list_elements("project-2", "commit-1")
        == other_revision_corpus
    )
    assert (
        service.repository.list_elements("project-1", "commit-2")
        == other_revision_corpus
    )
    assert client.element_retrievals == 2

    # the bound revision still serves the identity-bound snapshot
    assert service.repository.list_elements("project-1", "commit-1") == element_corpus()
    assert client.element_retrievals == 2

    # the sink never wrote the other revision's corpus as the bound one
    assert cc.load_corpus_snapshot(service) == element_corpus()
    assert sorted(p.name for p in snapshot_dir.glob("*.json")) == [
        bound_snapshot.name
    ]


def test_lazy_hook_revision_gate_precedes_cache_io_and_sink(snapshot_dir):
    """``service._require_valid_revision`` runs BEFORE any source/cache IO
    and BEFORE the sink write: a stale runtime fails closed instead of
    serving or writing cached data."""
    from de4sdv.semantic import corpus_cache as cc
    from de4sdv.sysml_api.errors import RevisionMismatchError

    cold = build_service(CountingClient())
    cc.load_elements_with_snapshot(cold)
    bound_snapshot = cc.corpus_snapshot_path(cold)
    before = bound_snapshot.read_bytes()

    client = CountingClient()
    stale = build_service(client, expected_git_revision="b" * 40)
    cc.install_corpus_snapshot(stale)

    # source: revision gate before snapshot IO — stale runtime fails closed
    with pytest.raises(RevisionMismatchError):
        stale.repository.list_elements("project-1", "commit-1")
    assert client.element_retrievals == 0
    assert bound_snapshot.read_bytes() == before

    # sink: revision gate before the write — a stale runtime never writes
    sink = stale.repository._corpus_sink
    assert sink is not None
    sink("project-1", "commit-1", [{"@id": "other-1", "@type": "PartUsage"}])
    assert bound_snapshot.read_bytes() == before
    assert cc.load_corpus_snapshot(cold) == element_corpus()

    # and neither closure ever serves/writes a non-bound revision
    source = stale.repository._corpus_source
    assert source is not None
    assert source("project-2", "commit-1") is None
    sink("project-2", "commit-1", [{"@id": "other-2", "@type": "PartUsage"}])
    assert sorted(p.name for p in snapshot_dir.glob("*.json")) == [
        bound_snapshot.name
    ]


# ---------------------------------------------------------------------------
# Slice 5: real MCP stdio server, counting transport, restart-hit e2e
# ---------------------------------------------------------------------------


class _CountingApiHandler(BaseHTTPRequestHandler):
    """Minimal SysML API fixture that counts element-listing retrievals."""

    elements: list[dict[str, Any]] = []
    element_retrievals = 0

    def do_GET(self) -> None:  # noqa: N802
        if self.path.endswith("/elements?page[size]=1000"):
            type(self).element_retrievals += 1
            payload: object = list(self.elements)
        elif self.path == "/projects/project-1":
            payload = {"@id": "project-1", "@type": "Project"}
        elif self.path == "/projects/project-1/commits/commit-1":
            payload = {"@id": "commit-1", "@type": "Commit"}
        else:
            self.send_error(404)
            return
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@pytest.fixture()
def counting_api_server():
    handler = _CountingApiHandler
    handler.elements = element_corpus()
    handler.element_retrievals = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield handler, f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join()


def test_stdio_mcp_restart_serves_bound_revision_with_zero_listing(
    snapshot_dir, counting_api_server, tmp_path
):
    """End-to-end: the real stdio server script, run twice against a counting
    HTTP fixture. The handshake never blocks on the corpus; the cold run
    retrieves once and writes the identity-bound snapshot; the restart run
    lists ZERO elements while serving model_status and impact."""
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    handler, api_url = counting_api_server
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps(binding_dict(scope="full-model")), encoding="utf-8")

    def params() -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable,
            args=[
                "scripts/semantic_mcp_server.py",
                "--api-url",
                api_url,
                "--binding",
                str(binding),
                "--expected-git-revision",
                "a" * 40,
            ],
            cwd=str(REPO_ROOT),
            # the stdio default environment is minimal: pass the deployment
            # environment through so the subprocess resolves the same
            # snapshot directory as the test (DE4SDV_SEMANTIC_SNAPSHOT_DIR)
            env=dict(os.environ),
        )

    async def exercise(session):
        status = await session.call_tool("model_status", {})
        impact = await session.call_tool("impact", {"identifier": "reqCommandEmergencyBraking"})
        return status, impact

    async def run_session():
        async with stdio_client(params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                during_handshake = handler.element_retrievals
                status, impact = await exercise(session)
                return names, during_handshake, status, impact

    # cold run: handshake performs no listing; one retrieval for the corpus
    names, during_handshake, status, impact = anyio.run(run_session)
    assert names == {
        "model_status",
        "resolve_element",
        "inspect_element",
        "semantic_neighbors",
        "impact",
        "trace",
        "verification_coverage",
        "phase_contract",
        "increment_status",
        "method_gaps",
        "next_obligation",
    }
    assert during_handshake == 0
    assert handler.element_retrievals == 1
    assert status.structuredContent["current_baseline"] is True
    assert status.structuredContent["element_count"] == len(element_corpus())
    assert impact.structuredContent["root"]["element_id"] == "req-1"

    # the cold run wrote exactly one identity-bound snapshot for this revision
    snapshots = sorted(snapshot_dir.glob("*.json"))
    assert len(snapshots) == 1
    payload = json.loads(snapshots[0].read_text(encoding="utf-8"))
    assert payload["format"] == 3
    assert payload["git_commit"] == "a" * 40
    assert payload["sysml_project_id"] == "project-1"
    assert payload["sysml_commit_id"] == "commit-1"
    assert payload["element_count"] == len(element_corpus())

    # restart run (fresh stdio process): zero additional listings, identical
    # tool output contracts
    warm_names, warm_during_handshake, warm_status, warm_impact = anyio.run(run_session)
    assert warm_names == names
    assert warm_during_handshake == 1  # handshake: no new listing
    assert handler.element_retrievals == 1  # snapshot hit: zero listing
    assert warm_status.structuredContent == status.structuredContent
    assert warm_impact.structuredContent == impact.structuredContent
