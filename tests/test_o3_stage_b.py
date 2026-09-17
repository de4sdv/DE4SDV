"""O3 Stage B — production semantic-authority selection, startup refusal,
rollback, and authority-scoped caches.

Locks the Stage-B invariants:

- one explicit selector distinguishes legacy authority from exactly one
  accepted closed O3 bundle; the default is legacy; unknown or incomplete
  selections fail closed (no latest-bundle discovery, no silent legacy
  fallback);
- production O3 startup verifies the closed bundle against the exact
  revision and revision binding (schema, bundle id, runtime build,
  Projection/Profile chains, binding digest, SysML project/commit,
  validation evidence, grounding) and requires recomputed activation
  eligibility; every mismatch refuses startup;
- provider routing is unchanged: the migrated 13 resolve through the O3
  provider only, unmigrated identities delegate to the authored contract,
  unknown identities fail exactly like legacy;
- rollback (O3 -> legacy -> O3) is a selector change only: provenance and
  authority-keyed caches follow the selector and never cross authorities,
  and migrated-identity runtime answers stay equal to the reviewed
  equivalence boundary (the privileged same-revision comparison owns the
  full runtime proof);
- the production entry points (viewer service, MCP CLI) carry the
  selection and expose its provenance.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.semantic import authority_selection as sel
from de4sdv.semantic import o3_bundle as ob
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.sysml_api.revisions import OntologyIdentity

# ``mcp.client.stdio`` binds ``sys.stderr`` as its default ``errlog`` at
# IMPORT time. Importing it for the first time while a pytest fixture-level
# capture (capsys/capfd) is active binds a stream that pytest closes again
# after that fixture, which breaks every later stdio end-to-end test in the
# same process (``ValueError: I/O operation on closed file``). Binding it
# here — during collection, against the session-global capture stream that
# stays alive for the whole run — keeps the process healthy for
# ``tests/test_semantic_mcp.py`` regardless of file order.
import mcp.client.stdio  # noqa: F401  (import-time binding guard)

REPO_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_PATH = REPO_ROOT / ob.ONTOLOGY_PATH
REVISION = "a" * 40

LEGACY_ID = ob.LEGACY_AUTHORITY_ID


# ---------------------------------------------------------------------------
# Fixtures: exact-revision closed bundles over the real checkout
# ---------------------------------------------------------------------------


def _ontology_identity() -> dict[str, str]:
    return {
        "path": ob.ONTOLOGY_PATH,
        "sha256": hashlib.sha256(ONTOLOGY_PATH.read_bytes()).hexdigest(),
    }


def _binding_document(
    *,
    git_commit: str = REVISION,
    project: str = "pid-1",
    commit: str = "cid-1",
    scope: str = "fixture",
) -> dict[str, object]:
    return {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": git_commit,
        "sysml_project_id": project,
        "sysml_commit_id": commit,
        "import_timestamp": "2026-09-17T00:00:00Z",
        "import_tool_version": "fixture/1",
        "semantic_validation": "passed",
        "scope": scope,
        "ontology": _ontology_identity(),
        "kernel_bindings": [],
    }


def _write_binding(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _binding_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _binding_namespace(
    *, git_commit: str = REVISION, project: str = "pid-1", commit: str = "cid-1"
) -> SimpleNamespace:
    return SimpleNamespace(
        git_commit=git_commit,
        semantic_validation="passed",
        sysml_project_id=project,
        sysml_commit_id=commit,
        ontology=OntologyIdentity.from_dict(_ontology_identity()),
        kernel_bindings=(),
        scope="full-model",
    )


def _validation_records() -> dict[str, dict[str, str]]:
    return {
        name: {
            "status": "passed",
            "artifact": name,
            "path": f"/tmp/test-{name}.json",
            "sha256": "sha256:" + "c" * 64,
        }
        for name in ob.REQUIRED_VALIDATIONS
    }


def _closed_bundle(
    *,
    revision: str = REVISION,
    grounding: str = "EQUIVALENT",
    project: str = "pid-1",
    commit: str = "cid-1",
    binding_sha256: str | None = None,
    validation_mutate=None,
) -> dict:
    records = _validation_records()
    if validation_mutate is not None:
        validation_mutate(records)
    bundle = ob.build_candidate_bundle(REPO_ROOT, git_revision=revision)
    attestation = ob.build_closure_attestation(
        bundle,
        binding=_binding_namespace(
            git_commit=revision, project=project, commit=commit
        ),
        binding_sha256=binding_sha256 if binding_sha256 is not None else "sha256:" + "b" * 64,
        element_count=1,
        export_identity_sha256=None,
        validations=records,
        verification_case_grounding={"result": grounding},
        generated_at="1970-01-01T00:00:00+00:00",
    )
    return ob.close_bundle(bundle, attestation)


def _retampered(bundle: dict, mutate) -> dict:
    """Mutate and recompute the bundle id (isolates downstream checks)."""
    tampered = copy.deepcopy(bundle)
    mutate(tampered)
    tampered["bundle_id"] = ob.compute_bundle_id(tampered)
    return tampered


def _write_bundle(tmp_path: Path, bundle: dict) -> Path:
    path = tmp_path / "de4sdv-o3-authority-bundle.json"
    path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _environ(
    bundle_path: Path | None,
    bundle_id: str | None = None,
    *,
    authority: str = "o3",
) -> dict[str, str]:
    env: dict[str, str] = {"DE4SDV_SEMANTIC_AUTHORITY": authority}
    if bundle_path is not None:
        env["DE4SDV_O3_AUTHORITY_BUNDLE"] = str(bundle_path)
    if bundle_id is not None:
        env["DE4SDV_O3_AUTHORITY_BUNDLE_ID"] = bundle_id
    return env


def _start(
    binding_path: Path,
    bundle_path: Path | None,
    *,
    expected_git_revision: str = REVISION,
    environ: dict[str, str] | None = None,
    authority: str = "o3",
):
    """Build the production runtime through the explicit selector."""
    if environ is None:
        bundle_id = None
        if bundle_path is not None:
            bundle_id = json.loads(bundle_path.read_text(encoding="utf-8")).get(
                "bundle_id"
            )
        environ = _environ(bundle_path, bundle_id, authority=authority)
    return sel.build_selected_semantic_runtime(
        api_url="http://127.0.0.1:9",
        binding_path=binding_path,
        expected_git_revision=expected_git_revision,
        ontology_path=ONTOLOGY_PATH,
        environ=environ,
    )


def _activated_o3(tmp_path: Path):
    """(binding_path, bundle_path, bundle) for one activation-eligible bundle."""
    binding_path = _write_binding(tmp_path, _binding_document())
    bundle = _closed_bundle(binding_sha256=_binding_digest(binding_path))
    bundle_path = _write_bundle(tmp_path, bundle)
    return binding_path, bundle_path, bundle


# ---------------------------------------------------------------------------
# 1. Explicit selector semantics
# ---------------------------------------------------------------------------


class TestSelector:
    def test_default_and_empty_selector_are_legacy(self) -> None:
        empty_environments = (
            {},
            {"DE4SDV_SEMANTIC_AUTHORITY": ""},
            {"DE4SDV_SEMANTIC_AUTHORITY": "  "},
        )
        for environ in empty_environments:
            selection = sel.resolve_authority_selection(environ=environ)
            assert selection.kind == sel.LEGACY_AUTHORITY
            assert selection.is_o3 is False
            assert selection.bundle_document is None
            assert selection.provenance()["authority_id"] == LEGACY_ID

    def test_explicit_legacy_value(self) -> None:
        selection = sel.resolve_authority_selection(
            environ={"DE4SDV_SEMANTIC_AUTHORITY": "legacy"}
        )
        assert selection.kind == sel.LEGACY_AUTHORITY

    @pytest.mark.parametrize("value", ["latest", "auto", "true", "o4", "candidate"])
    def test_unknown_selector_value_fails_closed(self, value: str) -> None:
        with pytest.raises(sel.AuthoritySelectionError, match="unknown"):
            sel.resolve_authority_selection(
                environ={"DE4SDV_SEMANTIC_AUTHORITY": value}
            )

    def test_no_automatic_latest_bundle_discovery(self, tmp_path: Path) -> None:
        """A bundle on disk is never discovered: the exact path is required."""
        _write_bundle(tmp_path, _closed_bundle())
        with pytest.raises(sel.AuthoritySelectionError, match="DE4SDV_O3_AUTHORITY_BUNDLE"):
            sel.resolve_authority_selection(
                environ={"DE4SDV_SEMANTIC_AUTHORITY": "o3"}
            )

    def test_o3_requires_exact_bundle_id(self, tmp_path: Path) -> None:
        bundle_path = _write_bundle(tmp_path, _closed_bundle())
        with pytest.raises(sel.AuthoritySelectionError, match="BUNDLE_ID"):
            sel.resolve_authority_selection(
                environ=_environ(bundle_path)
            )

    def test_nonexistent_bundle_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(sel.AuthoritySelectionError, match="not found"):
            sel.resolve_authority_selection(
                environ=_environ(tmp_path / "missing.json", "o3b-" + "0" * 32)
            )

    def test_wrong_bundle_id_fails_closed(self, tmp_path: Path) -> None:
        bundle = _closed_bundle()
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(sel.AuthoritySelectionError, match="does not"):
            sel.resolve_authority_selection(
                environ=_environ(bundle_path, "o3b-" + "0" * 32)
            )

    def test_unparsable_bundle_fails_closed(self, tmp_path: Path) -> None:
        path = tmp_path / "bundle.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(sel.AuthoritySelectionError, match="JSON"):
            sel.resolve_authority_selection(
                environ=_environ(path, "o3b-" + "0" * 32)
            )

    def test_wrong_schema_fails_closed(self, tmp_path: Path) -> None:
        bundle = _closed_bundle()
        bundle["schema"] = "de4sdv.o3-authority-bundle/v2"
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(sel.AuthoritySelectionError, match="schema"):
            sel.resolve_authority_selection(
                environ=_environ(bundle_path, bundle["bundle_id"])
            )

    def test_core_bundle_cannot_be_selected(self, tmp_path: Path) -> None:
        core = ob.build_candidate_bundle(REPO_ROOT, git_revision=REVISION)
        bundle_path = _write_bundle(tmp_path, core)
        with pytest.raises(sel.AuthoritySelectionError, match="not closed"):
            sel.resolve_authority_selection(
                environ=_environ(bundle_path, core["bundle_id"])
            )

    def test_valid_closed_selection_carries_provenance(self, tmp_path: Path) -> None:
        bundle = _closed_bundle()
        bundle_path = _write_bundle(tmp_path, bundle)
        selection = sel.resolve_authority_selection(
            environ=_environ(bundle_path, bundle["bundle_id"])
        )
        assert selection.kind == sel.O3_AUTHORITY
        assert selection.bundle_id == bundle["bundle_id"]
        assert selection.bundle_document == bundle
        provenance = selection.provenance()
        assert provenance["kind"] == "o3"
        assert provenance["bundle_id"] == bundle["bundle_id"]
        assert provenance["authority_id"] == ob.o3_authority_id(bundle["bundle_id"])
        assert provenance["git_revision"] == REVISION


# ---------------------------------------------------------------------------
# 2. Production startup verification (fail closed through the real seam)
# ---------------------------------------------------------------------------


class TestProductionStartup:
    def test_valid_bundle_starts_service_under_o3(self, tmp_path: Path) -> None:
        binding_path, bundle_path, bundle = _activated_o3(tmp_path)
        service, selection = _start(binding_path, bundle_path)
        assert selection.kind == sel.O3_AUTHORITY
        assert service.semantic_authority_id == ob.o3_authority_id(
            bundle["bundle_id"]
        )
        assert isinstance(service.contract, ob.O3AuthorityFacade)
        block = service.model_status()["semantic_authority"]
        assert block["kind"] == "o3"
        assert block["id"] == service.semantic_authority_id

    def test_default_selector_starts_legacy_service_unchanged(
        self, tmp_path: Path
    ) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        service, selection = _start(binding_path, None, authority="legacy")
        assert selection.kind == sel.LEGACY_AUTHORITY
        assert service.semantic_authority_id == LEGACY_ID
        assert isinstance(service.contract, KernelContract)
        assert service.model_status()["semantic_authority"]["kind"] == "legacy"

    def test_wrong_git_revision_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(
            tmp_path, _binding_document(git_commit="b" * 40)
        )
        bundle = _closed_bundle(revision=REVISION)
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="git revision"):
            _start(
                binding_path,
                bundle_path,
                expected_git_revision="b" * 40,
            )

    def test_expected_revision_mismatch_refuses(self, tmp_path: Path) -> None:
        binding_path, bundle_path, bundle = _activated_o3(tmp_path)
        with pytest.raises(ob.O3BundleError, match="expected runtime revision"):
            _start(
                binding_path,
                bundle_path,
                expected_git_revision="c" * 40,
            )

    def test_wrong_runtime_build_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = _closed_bundle(binding_sha256=_binding_digest(binding_path))
        tampered = _retampered(
            bundle,
            lambda item: item["runtime_build"].__setitem__("id", "rb-" + "0" * 32),
        )
        bundle_path = _write_bundle(tmp_path, tampered)
        with pytest.raises(ob.O3BundleError, match="runtime build"):
            _start(binding_path, bundle_path)

    def test_modified_semantic_projection_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = _closed_bundle(binding_sha256=_binding_digest(binding_path))
        tampered = _retampered(
            bundle,
            lambda item: item["projection_chain"][0].__setitem__(
                "sha256", "sha256:" + "0" * 64
            ),
        )
        bundle_path = _write_bundle(tmp_path, tampered)
        with pytest.raises(ob.O3BundleError, match="projection chain"):
            _start(binding_path, bundle_path)

    def test_modified_representation_profile_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = _closed_bundle(binding_sha256=_binding_digest(binding_path))
        tampered = _retampered(
            bundle,
            lambda item: item["profile_chain"][2].__setitem__(
                "sha256", "sha256:" + "0" * 64
            ),
        )
        bundle_path = _write_bundle(tmp_path, tampered)
        with pytest.raises(ob.O3BundleError, match="profile chain"):
            _start(binding_path, bundle_path)

    def test_stale_revision_binding_refuses(self, tmp_path: Path) -> None:
        """The closure must be bound to THIS binding file's exact bytes."""
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = _closed_bundle(binding_sha256="sha256:" + "9" * 64)
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="binding digest"):
            _start(binding_path, bundle_path)

    def test_wrong_sysml_project_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(
            tmp_path, _binding_document(project="other-project")
        )
        bundle = _closed_bundle(binding_sha256=_binding_digest(binding_path))
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="sysml_project_id"):
            _start(binding_path, bundle_path)

    def test_wrong_sysml_commit_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(
            tmp_path, _binding_document(commit="other-commit")
        )
        bundle = _closed_bundle(binding_sha256=_binding_digest(binding_path))
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="sysml_commit_id"):
            _start(binding_path, bundle_path)

    def test_failed_validation_evidence_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())

        def fail_one(records) -> None:
            records["semantic_mcp"]["status"] = "failed"

        bundle = _closed_bundle(
            binding_sha256=_binding_digest(binding_path),
            validation_mutate=fail_one,
        )
        assert bundle["api_closure"]["activation_eligible"] is False
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="passed"):
            _start(binding_path, bundle_path)

    def test_not_yet_comparable_grounding_refuses_production(
        self, tmp_path: Path
    ) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = _closed_bundle(
            binding_sha256=_binding_digest(binding_path),
            grounding="NOT_YET_COMPARABLE",
        )
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="activation_eligible=true"):
            _start(binding_path, bundle_path)

    def test_blocking_grounding_refuses_production(self, tmp_path: Path) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = _closed_bundle(
            binding_sha256=_binding_digest(binding_path),
            grounding="BLOCKING_MISMATCH",
        )
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="BLOCKING_MISMATCH"):
            _start(binding_path, bundle_path)

    def test_tampered_activation_eligibility_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = copy.deepcopy(
            _closed_bundle(
                binding_sha256=_binding_digest(binding_path),
                grounding="NOT_YET_COMPARABLE",
            )
        )
        bundle["api_closure"]["activation_eligible"] = True
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="does not reproduce"):
            _start(binding_path, bundle_path)

    def test_tampered_bundle_id_refuses(self, tmp_path: Path) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = copy.deepcopy(_closed_bundle(binding_sha256=_binding_digest(binding_path)))
        forged_id = "o3b-" + "0" * 32
        bundle["bundle_id"] = forged_id
        bundle_path = _write_bundle(tmp_path, bundle)
        with pytest.raises(ob.O3BundleError, match="recomputed content digest"):
            _start(binding_path, bundle_path)

    def test_comparison_path_can_still_load_ineligible_bundle(
        self, tmp_path: Path
    ) -> None:
        """The same-revision comparison keeps loading closed-but-ineligible
        bundles; only the production selection requires eligibility."""
        binding_path = _write_binding(tmp_path, _binding_document())
        bundle = _closed_bundle(
            binding_sha256=_binding_digest(binding_path),
            grounding="NOT_YET_COMPARABLE",
        )
        authority = ob.load_o3_authority(
            bundle,
            root=REPO_ROOT,
            contract=KernelContract.load(ONTOLOGY_PATH),
            binding=_binding_namespace(),
            binding_sha256=_binding_digest(binding_path),
        )
        assert authority.activation_blocked is True
        with pytest.raises(ob.O3BundleError, match="activation_eligible"):
            ob.load_o3_authority(
                bundle,
                root=REPO_ROOT,
                contract=KernelContract.load(ONTOLOGY_PATH),
                binding=_binding_namespace(),
                binding_sha256=_binding_digest(binding_path),
                require_activation_eligible=True,
            )


# ---------------------------------------------------------------------------
# 3. Provider routing (migrated -> O3 only; unmigrated -> legacy)
# ---------------------------------------------------------------------------


def _facade(tmp_path: Path) -> ob.O3AuthorityFacade:
    rows, entries = ob._load_chain_rows(REPO_ROOT)
    bundle = ob.build_candidate_bundle(REPO_ROOT, git_revision=REVISION)
    return ob.O3AuthorityFacade(
        legacy=KernelContract.load(ONTOLOGY_PATH),
        bundle=bundle,
        projection_rows=rows,
        profile_entries=entries,
    )


class _PoisonedLegacy:
    """A legacy provider that refuses every migrated-identity lookup."""

    def __init__(self, contract: KernelContract) -> None:
        self._contract = contract
        self.relationships = contract.relationships
        self.classes = contract.classes
        self.identity = contract.identity
        self.accessed: list[str] = []

    def _forbid(self, name: str) -> None:
        self.accessed.append(name)
        raise AssertionError(
            f"migrated identity {name!r} consulted the legacy (authored YAML) provider"
        )

    def relationship_mapping(self, name: str):
        if name in ob.MIGRATED_RELATIONSHIPS:
            self._forbid(name)
        return self._contract.relationship_mapping(name)

    def mapping(self, name: str):
        if name in ob.MIGRATED_CLASSES:
            self._forbid(name)
        return self._contract.mapping(name)

    def class_mapping(self, name: str):
        if name in ob.MIGRATED_CLASSES:
            self._forbid(name)
        return self._contract.class_mapping(name)


class TestRouting:
    def test_migrated_identity_never_consults_authored_yaml(self) -> None:
        rows, entries = ob._load_chain_rows(REPO_ROOT)
        bundle = ob.build_candidate_bundle(REPO_ROOT, git_revision=REVISION)
        poisoned = _PoisonedLegacy(KernelContract.load(ONTOLOGY_PATH))
        facade = ob.O3AuthorityFacade(
            legacy=poisoned,
            bundle=bundle,
            projection_rows=rows,
            profile_entries=entries,
        )
        for name in ob.MIGRATED_RELATIONSHIPS:
            mapping = facade.relationship_mapping(name)
            assert mapping is facade._relationship_mappings[name]
        for name in ob.MIGRATED_CLASSES:
            facade.mapping(name)
        assert poisoned.accessed == []

    def test_every_unmigrated_identity_delegates_to_legacy(self, tmp_path: Path) -> None:
        legacy = KernelContract.load(ONTOLOGY_PATH)
        facade = _facade(tmp_path)
        for name in legacy.relationships:
            if name in ob.MIGRATED_RELATIONSHIPS:
                continue
            try:
                expected = legacy.relationship_mapping(name)
            except KeyError:
                # Vocabulary-only relationship: the facade fails exactly
                # like the legacy contract (no invented mapping).
                with pytest.raises(KeyError):
                    facade.relationship_mapping(name)
                continue
            assert facade.relationship_mapping(name) == expected
        for name in legacy.classes:
            if name in ob.MIGRATED_CLASSES:
                continue
            assert facade.mapping(name) == legacy.mapping(name)

    def test_unknown_identity_fails_like_legacy(self, tmp_path: Path) -> None:
        facade = _facade(tmp_path)
        with pytest.raises(KeyError):
            facade.relationship_mapping("noSuchPredicate")
        with pytest.raises((KeyError, ValueError)):
            facade.mapping("NoSuchClass")

    def test_service_routing_prefers_the_selected_provider(
        self, tmp_path: Path
    ) -> None:
        binding_path, bundle_path, bundle = _activated_o3(tmp_path)
        o3_service, _ = _start(binding_path, bundle_path)
        legacy_service, _ = _start(binding_path, None, authority="legacy")
        facade = o3_service.contract
        legacy = legacy_service.contract
        for name in ob.MIGRATED_RELATIONSHIPS:
            assert facade.relationship_mapping(name) is facade._relationship_mappings[name]
        for name in ob.MIGRATED_CLASSES:
            facade.mapping(name)
        assert facade.relationship_mapping("realizedBy") == legacy.relationship_mapping(
            "realizedBy"
        )
        assert facade.mapping("Requirement") == legacy.mapping("Requirement")


# ---------------------------------------------------------------------------
# 4. Rollback: O3 -> legacy -> O3 is a selector change only
# ---------------------------------------------------------------------------


class TestRollback:
    def test_provenance_follows_the_rollback_sequence(self, tmp_path: Path) -> None:
        binding_path, bundle_path, bundle = _activated_o3(tmp_path)
        first, _ = _start(binding_path, bundle_path)
        legacy, _ = _start(binding_path, None, authority="legacy")
        again, _ = _start(binding_path, bundle_path)
        expected_id = ob.o3_authority_id(bundle["bundle_id"])
        assert first.semantic_authority_id == expected_id
        assert legacy.semantic_authority_id == LEGACY_ID
        assert again.semantic_authority_id == expected_id
        assert first.model_status()["semantic_authority"]["kind"] == "o3"
        assert legacy.model_status()["semantic_authority"]["kind"] == "legacy"
        assert again.model_status()["semantic_authority"]["kind"] == "o3"
        # Same engineering binding throughout: only authority changed.
        assert (
            first.model_status()["revision"]
            == legacy.model_status()["revision"]
            == again.model_status()["revision"]
        )

    def test_migrated_identity_answers_equal_across_all_phases(
        self, tmp_path: Path
    ) -> None:
        """The reviewed equivalence boundary at mapping level: the O3
        provider and the authored contract carry equal runtime mappings for
        every migrated identity, in every rollback phase (the privileged
        same-revision comparison owns the full runtime proof)."""
        binding_path, bundle_path, _bundle = _activated_o3(tmp_path)
        first, _ = _start(binding_path, bundle_path)
        legacy, _ = _start(binding_path, None, authority="legacy")
        again, _ = _start(binding_path, bundle_path)
        for service in (first, again):
            for name in ob.MIGRATED_RELATIONSHIPS:
                o3_mapping = service.contract.relationship_mapping(name)
                legacy_mapping = legacy.contract.relationship_mapping(name)
                assert o3_mapping.strategy == legacy_mapping.strategy
                assert o3_mapping.domain == legacy_mapping.domain
                assert o3_mapping.range == legacy_mapping.range
                assert o3_mapping.semantic_strength == legacy_mapping.semantic_strength
                assert o3_mapping.configuration == legacy_mapping.configuration

    def test_migrated_traversal_answers_equal_across_authorities(
        self, tmp_path: Path
    ) -> None:
        """A real hasSubject traversal over the governed fixture shape
        answers identically under the O3 facade and the authored contract."""
        from de4sdv.semantic.kernel_binding_index import KernelBindingIndex
        from de4sdv.semantic.traversal import SemanticTraversal
        from de4sdv.sysml_api.revisions import RevisionBinding

        facade = _facade(tmp_path)
        legacy = KernelContract.load(ONTOLOGY_PATH)
        index = KernelBindingIndex.from_binding(
            RevisionBinding.from_dict(
                {
                    **_binding_document(scope="fixture"),
                    "kernel_bindings": [
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
                    ],
                }
            )
        )
        requirement = {
            "@id": "req-1",
            "@type": "RequirementUsage",
            "declaredName": "reqCommandEmergencyBraking",
        }
        elements = [
            {
                "@id": "kernel-requirement",
                "@type": "RequirementDefinition",
                "declaredName": "RequirementCandidate",
            },
            {
                "@id": "kernel-member-product",
                "@type": "PartDefinition",
                "declaredName": "ProductLineMemberProduct",
            },
            requirement,
            {"@id": "member-1", "@type": "PartUsage", "declaredName": "memberProduct"},
            {
                "@id": "sm-1",
                "@type": "SubjectMembership",
                "owningRelatedElement": {"@id": "req-1"},
                "memberElement": {"@id": "member-1"},
            },
            {
                "@id": "ft-req",
                "@type": "FeatureTyping",
                "owningRelatedElement": {"@id": "req-1"},
                "type": {"@id": "kernel-requirement"},
                "typedFeature": {"@id": "req-1"},
            },
            {
                "@id": "ft-member",
                "@type": "FeatureTyping",
                "owningRelatedElement": {"@id": "member-1"},
                "type": {"@id": "kernel-member-product"},
                "typedFeature": {"@id": "member-1"},
            },
        ]

        def _summary(contract):
            hops = SemanticTraversal(contract, kernel_bindings=index).traverse(
                "hasSubject", requirement, elements
            )
            return [
                (hop.predicate, hop.target["@id"], hop.api_object["@id"], hop.strategy)
                for hop in hops
            ]

        o3_answer = _summary(facade)
        legacy_answer = _summary(legacy)
        assert o3_answer == legacy_answer == [
            ("hasSubject", "member-1", "sm-1", "subject-membership")
        ]

    def test_authority_scoped_caches_never_cross_authorities(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from tools.sysml_html_viewer import ask_model_semantic as ams

        binding_path, bundle_path, bundle = _activated_o3(tmp_path)
        first, _ = _start(binding_path, bundle_path)
        legacy, _ = _start(binding_path, None, authority="legacy")
        again, _ = _start(binding_path, bundle_path)

        monkeypatch.setattr(ams, "_snapshot_dir", lambda: tmp_path / "snaps")
        elements = [{"@type": "PartUsage", "@id": "e-1"}]
        # A snapshot written under O3 must never load under legacy ...
        ams._snapshot_write(first, elements)
        assert ams._snapshot_load(first) is not None
        assert ams._snapshot_load(legacy) is None
        # ... and re-activation reuses only the O3-keyed snapshot.
        assert ams._snapshot_load(again) is not None
        assert ams._snapshot_path(first) == ams._snapshot_path(again)
        assert ams._snapshot_path(first) != ams._snapshot_path(legacy)

        # The semantic-context cache is authority-scoped: rollback cannot
        # serve O3-served context answers and vice versa.
        ams._SEMANTIC_CTX_CACHE.clear()
        targets = [{"@id": "e-1"}]
        o3_context = ams.api_method_context(first, targets, elements, max_hops=1)
        legacy_context = ams.api_method_context(legacy, targets, elements, max_hops=1)
        assert o3_context == legacy_context
        o3_again = ams.api_method_context(again, targets, elements, max_hops=1)
        assert o3_again is ams._SEMANTIC_CTX_CACHE[
            next(key for key in ams._SEMANTIC_CTX_CACHE if key.startswith("o3:"))
        ]
        assert len(ams._SEMANTIC_CTX_CACHE) == 2
        ams._SEMANTIC_CTX_CACHE.clear()


# ---------------------------------------------------------------------------
# 5. Production entry points
# ---------------------------------------------------------------------------


@pytest.fixture()
def viewer(monkeypatch):
    from tools.sysml_html_viewer import ask_model_semantic as ams

    monkeypatch.setattr(ams, "_SEMANTIC_RUNTIME", None)
    monkeypatch.setattr(ams, "_SEMANTIC_ERROR", None)
    monkeypatch.setattr(ams, "_AUTHORITY_SELECTION", None)
    ams._SEMANTIC_CTX_CACHE.clear()
    return ams


def _viewer_env(monkeypatch, binding_path: Path, **extra: str) -> None:
    monkeypatch.setenv("DE4SDV_SYSML_API_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("DE4SDV_REVISION_BINDING", str(binding_path))
    monkeypatch.setenv("DE4SDV_EXPECTED_GIT_SHA", REVISION)
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")
    for name, value in extra.items():
        monkeypatch.setenv(name, value)


class TestViewerEntryPoint:
    def test_viewer_runtime_selects_o3_and_reports_provenance(
        self, viewer, tmp_path: Path, monkeypatch
    ) -> None:
        binding_path, bundle_path, bundle = _activated_o3(tmp_path)
        _viewer_env(
            monkeypatch,
            binding_path,
            DE4SDV_SEMANTIC_AUTHORITY="o3",
            DE4SDV_O3_AUTHORITY_BUNDLE=str(bundle_path),
            DE4SDV_O3_AUTHORITY_BUNDLE_ID=bundle["bundle_id"],
        )
        service = viewer._runtime()
        assert service.semantic_authority_id == ob.o3_authority_id(
            bundle["bundle_id"]
        )
        status = viewer.semantic_authority_status()
        assert status["kind"] == "o3"
        assert status["bundle_id"] == bundle["bundle_id"]
        assert status["git_revision"] == REVISION
        assert status["semantic_authority_id"] == service.semantic_authority_id

    def test_viewer_default_reports_legacy(self, viewer, tmp_path: Path, monkeypatch) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        _viewer_env(monkeypatch, binding_path)
        monkeypatch.delenv("DE4SDV_SEMANTIC_AUTHORITY", raising=False)
        service = viewer._runtime()
        assert service.semantic_authority_id == LEGACY_ID
        assert viewer.semantic_authority_status()["kind"] == "legacy"

    def test_viewer_fails_closed_on_invalid_o3(self, viewer, tmp_path: Path, monkeypatch) -> None:
        binding_path = _write_binding(tmp_path, _binding_document())
        _viewer_env(
            monkeypatch,
            binding_path,
            DE4SDV_SEMANTIC_AUTHORITY="o3",
            DE4SDV_O3_AUTHORITY_BUNDLE=str(tmp_path / "missing.json"),
            DE4SDV_O3_AUTHORITY_BUNDLE_ID="o3b-" + "0" * 32,
        )
        with pytest.raises(RuntimeError, match="semantic runtime unavailable"):
            viewer._runtime()
        assert viewer._SEMANTIC_RUNTIME is None
        status = viewer.semantic_authority_status()
        assert status["kind"] == "invalid"
        assert "not found" in status["error"]

        # The explicit non-semantic fallback remains, and no semantic
        # authority answer is served in this state.
        ref = SimpleNamespace(name="reqCommandEmergencyBraking")
        monkeypatch.setattr(
            viewer, "_regex_fallback", lambda r, f: {"fallback": r.name}
        )
        context, path = viewer.build_method_context_api(ref, [])
        assert path == "regex:fallback:RuntimeError"
        assert context == {"fallback": "reqCommandEmergencyBraking"}


def _load_mcp_module():
    spec = importlib.util.spec_from_file_location(
        "semantic_mcp_server_stage_b_under_test",
        REPO_ROOT / "scripts" / "semantic_mcp_server.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ServerStub:
    def __init__(self) -> None:
        self.transport: str | None = None

    def run(self, transport: str | None = None) -> None:
        self.transport = transport


class TestMcpEntryPoint:
    def test_mcp_cli_rejects_invalid_o3_selection(
        self, tmp_path: Path, monkeypatch, capfd
    ) -> None:
        # capfd (fd-level capture), never capsys: the collection-time
        # pre-import above already binds the stdio errlog to a session-long
        # stream, and keeping fixture-level captures at fd level means no
        # import here can ever receive a soon-to-be-closed sys.stderr.
        module = _load_mcp_module()
        binding_path = _write_binding(tmp_path, _binding_document())
        monkeypatch.setenv("DE4SDV_SYSML_API_URL", "http://127.0.0.1:9")
        monkeypatch.setenv("DE4SDV_REVISION_BINDING", str(binding_path))
        monkeypatch.setenv("DE4SDV_EXPECTED_GIT_SHA", REVISION)
        monkeypatch.setenv("DE4SDV_SEMANTIC_AUTHORITY", "o3")
        monkeypatch.setenv("DE4SDV_O3_AUTHORITY_BUNDLE", str(tmp_path / "missing.json"))
        monkeypatch.setenv("DE4SDV_O3_AUTHORITY_BUNDLE_ID", "o3b-" + "0" * 32)
        monkeypatch.setattr(sys, "argv", ["semantic_mcp_server.py"])
        with pytest.raises(SystemExit) as excinfo:
            module.main()
        assert excinfo.value.code == 2
        assert "semantic authority selection failed" in capfd.readouterr().err

    def test_mcp_cli_flags_select_o3_over_legacy_env(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        module = _load_mcp_module()
        binding_path, bundle_path, bundle = _activated_o3(tmp_path)
        captured: dict = {}
        monkeypatch.setattr(
            module,
            "create_mcp_server",
            lambda service: (captured.setdefault("service", service), _ServerStub())[1],
        )
        monkeypatch.setenv("DE4SDV_SEMANTIC_AUTHORITY", "legacy")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "semantic_mcp_server.py",
                "--api-url",
                "http://127.0.0.1:9",
                "--binding",
                str(binding_path),
                "--expected-git-revision",
                REVISION,
                "--semantic-authority",
                "o3",
                "--o3-authority-bundle",
                str(bundle_path),
                "--o3-authority-bundle-id",
                bundle["bundle_id"],
            ],
        )
        assert module.main() == 0
        service = captured["service"]
        assert service.semantic_authority_id == ob.o3_authority_id(
            bundle["bundle_id"]
        )
        assert service.model_status()["semantic_authority"]["kind"] == "o3"

    def test_mcp_cli_defaults_to_legacy_without_selector(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        module = _load_mcp_module()
        binding_path = _write_binding(tmp_path, _binding_document())
        captured: dict = {}
        monkeypatch.setattr(
            module,
            "create_mcp_server",
            lambda service: (captured.setdefault("service", service), _ServerStub())[1],
        )
        for name in (
            "DE4SDV_SEMANTIC_AUTHORITY",
            "DE4SDV_O3_AUTHORITY_BUNDLE",
            "DE4SDV_O3_AUTHORITY_BUNDLE_ID",
        ):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "semantic_mcp_server.py",
                "--api-url",
                "http://127.0.0.1:9",
                "--binding",
                str(binding_path),
                "--expected-git-revision",
                REVISION,
            ],
        )
        assert module.main() == 0
        assert captured["service"].semantic_authority_id == LEGACY_ID
