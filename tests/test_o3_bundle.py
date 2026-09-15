"""O3 Stage A — candidate authority bundle, façade routing, cache safety.

Locks the reviewed Stage-A invariants:

- bundle integrity fails closed on every identity/digest/revision mismatch;
- an unclosed candidate bundle cannot execute;
- migrated identities resolve through Projection/Profile only (never the
  authored YAML), unmigrated identities delegate to the legacy contract,
  with no fallback and no ambiguous overlap;
- authority-bundle-aware viewer snapshots and the semantic-context cache
  never share answers across authority identities;
- the reviewed cross-pins (13-identity set, chains, K baseline) hold.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from de4sdv.semantic import o3_bundle as ob
from de4sdv.semantic import o3_equivalence as oe
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.sysml_api.revisions import OntologyIdentity

REPO_ROOT = Path(__file__).resolve().parents[1]


def _binding_for(root: Path, revision: str, *, project: str = "pid-1", commit: str = "cid-1"):
    ontology_sha = hashlib.sha256((root / ob.ONTOLOGY_PATH).read_bytes()).hexdigest()
    return SimpleNamespace(
        git_commit=revision,
        semantic_validation="passed",
        sysml_project_id=project,
        sysml_commit_id=commit,
        ontology=OntologyIdentity(ob.ONTOLOGY_PATH, ontology_sha),
        kernel_bindings=(),
        scope="full-model",
    )


def _validation_records():
    """Structured evidence records (paths are placeholders here; digest
    re-verification against real files is exercised separately)."""
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
    root: Path,
    revision: str,
    *,
    grounding: str = "EQUIVALENT",
    binding=None,
):
    binding = binding or _binding_for(root, revision)
    bundle = ob.build_candidate_bundle(root, git_revision=revision)
    attestation = ob.build_closure_attestation(
        bundle,
        binding=binding,
        binding_sha256="sha256:" + "b" * 64,
        element_count=1,
        export_identity_sha256=None,
        validations=_validation_records(),
        verification_case_grounding={"result": grounding},
        generated_at="1970-01-01T00:00:00+00:00",
    )
    return ob.close_bundle(bundle, attestation), binding, "sha256:" + "b" * 64


def _retampered(bundle: dict, mutate) -> dict:
    """Mutate and recompute the bundle id (isolates downstream checks)."""
    tampered = copy.deepcopy(bundle)
    mutate(tampered)
    tampered["bundle_id"] = ob.compute_bundle_id(tampered)
    return tampered


def _verify(closed: dict, binding=None) -> list[str]:
    return ob.verify_bundle_document(
        closed,
        root=REPO_ROOT,
        binding=binding,
        binding_sha256="sha256:" + "b" * 64,
        require_closed=True,
    )


class TestBundleIntegrity:
    def test_core_bundle_verifies_and_unclosed_cannot_execute(self) -> None:
        core = ob.build_candidate_bundle(REPO_ROOT, git_revision="a" * 40)
        assert ob.verify_bundle_document(core, root=REPO_ROOT) == []
        errors = ob.verify_bundle_document(
            core, root=REPO_ROOT, require_closed=True
        )
        assert any("not closed" in error for error in errors)
        with pytest.raises(ob.O3BundleError, match="not closed"):
            ob.load_o3_authority(
                core,
                root=REPO_ROOT,
                contract=KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH),
                binding=_binding_for(REPO_ROOT, "a" * 40),
                binding_sha256="sha256:" + "b" * 64,
            )

    def test_closed_bundle_loads_and_reports_authority(self) -> None:
        closed, binding, digest = _closed_bundle(REPO_ROOT, "a" * 40)
        assert _verify(closed, binding=binding) == []
        authority = ob.load_o3_authority(
            closed,
            root=REPO_ROOT,
            contract=KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH),
            binding=binding,
            binding_sha256=digest,
        )
        assert authority.authority_id == f"o3-candidate:{closed['bundle_id']}"
        assert authority.activation_blocked is False

    def test_partially_grounded_bundle_loads_but_blocks_activation(self) -> None:
        closed, binding, digest = _closed_bundle(
            REPO_ROOT, "a" * 40, grounding="NOT_YET_COMPARABLE"
        )
        authority = ob.load_o3_authority(
            closed,
            root=REPO_ROOT,
            contract=KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH),
            binding=binding,
            binding_sha256=digest,
        )
        assert authority.activation_blocked is True

    def test_grounding_blocking_mismatch_refuses_execution(self) -> None:
        closed, binding, digest = _closed_bundle(
            REPO_ROOT, "a" * 40, grounding="BLOCKING_MISMATCH"
        )
        with pytest.raises(ob.O3BundleError, match="BLOCKING_MISMATCH"):
            ob.load_o3_authority(
                closed,
                root=REPO_ROOT,
                contract=KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH),
                binding=binding,
                binding_sha256=digest,
            )

    def test_wrong_git_revision_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = _retampered(
            closed, lambda bundle: bundle.__setitem__("git_revision", "c" * 40)
        )
        errors = _verify(tampered, binding=binding)
        assert any("git_commit" in error for error in errors)

    def test_wrong_projection_digest_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = _retampered(
            closed, lambda bundle: bundle["projection_chain"][2].__setitem__("sha256", "sha256:" + "0" * 64)
        )
        errors = _verify(tampered, binding=binding)
        assert any("projection chain records differ" in error for error in errors)

    def test_wrong_profile_digest_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = _retampered(
            closed, lambda bundle: bundle["profile_chain"][0].__setitem__("sha256", "sha256:" + "0" * 64)
        )
        errors = _verify(tampered, binding=binding)
        assert any("profile chain records differ" in error for error in errors)

    def test_missing_migrated_identity_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = _retampered(
            closed,
            lambda bundle: bundle["migrated_identities"].remove("hasSubject"),
        )
        errors = _verify(tampered, binding=binding)
        assert any("migrated identity set differs" in error for error in errors)

    def test_extra_migrated_identity_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = _retampered(
            closed,
            lambda bundle: bundle["migrated_identities"].append("realizedBy"),
        )
        errors = _verify(tampered, binding=binding)
        assert any("migrated identity set differs" in error for error in errors)

    def test_wrong_runtime_build_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = _retampered(
            closed, lambda bundle: bundle["runtime_build"].__setitem__("id", "rb-" + "0" * 32)
        )
        errors = _verify(tampered, binding=binding)
        assert any("runtime build identity" in error for error in errors)

    def test_wrong_binding_digest_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = copy.deepcopy(closed)
        tampered["api_closure"]["binding_sha256"] = "sha256:" + "9" * 64
        errors = _verify(tampered, binding=binding)
        assert any("binding digest differs" in error for error in errors)

    def test_wrong_sysml_project_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = copy.deepcopy(closed)
        tampered["api_closure"]["sysml_project_id"] = "other-project"
        errors = _verify(tampered, binding=binding)
        assert any("sysml_project_id" in error for error in errors)

    def test_wrong_sysml_commit_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = copy.deepcopy(closed)
        tampered["api_closure"]["sysml_commit_id"] = "other-commit"
        errors = _verify(tampered, binding=binding)
        assert any("sysml_commit_id" in error for error in errors)

    def test_wrong_ontology_compatibility_digest_fails(self) -> None:
        closed, binding, _digest = _closed_bundle(REPO_ROOT, "a" * 40)
        tampered = _retampered(
            closed,
            lambda bundle: bundle["ontology_compatibility_identity"].__setitem__(
                "sha256", "0" * 64
            ),
        )
        errors = _verify(tampered, binding=binding)
        assert any("ontology compatibility identity" in error for error in errors)


class TestAuthorityRouting:
    def _facade(self, *, contract=None, rows=None, entries=None):
        rows = rows if rows is not None else ob._load_chain_rows(REPO_ROOT)[0]
        entries = entries if entries is not None else ob._load_chain_rows(REPO_ROOT)[1]
        bundle = ob.build_candidate_bundle(REPO_ROOT, git_revision="a" * 40)
        return ob.O3AuthorityFacade(
            legacy=contract or KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH),
            bundle=bundle,
            projection_rows=rows,
            profile_entries=entries,
        )

    def test_migrated_identity_uses_projection_not_yaml(self) -> None:
        rows, entries = ob._load_chain_rows(REPO_ROOT)
        mutated_rows = copy.deepcopy(rows)
        mutated_rows["hasSubject"]["relation"]["semantic_strength"] = "relevance"
        facade = self._facade(rows=mutated_rows, entries=entries)
        mapping = facade.relationship_mapping("hasSubject")
        assert mapping.semantic_strength == "relevance"
        legacy = KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH)
        assert legacy.relationship_mapping("hasSubject").semantic_strength == (
            "native-reference"
        )

    def test_unmigrated_identity_delegates_legacy(self) -> None:
        contract = KernelContract.load(REPO_ROOT / ob.ONTOLOGY_PATH)
        facade = self._facade(contract=contract)
        assert facade.relationship_mapping("realizedBy") == (
            contract.relationship_mapping("realizedBy")
        )
        assert facade.mapping("Requirement") == contract.mapping("Requirement")
        assert facade.class_mapping("Requirement") == contract.class_mapping(
            "Requirement"
        )

    def test_unknown_identity_fails_like_legacy(self) -> None:
        facade = self._facade()
        with pytest.raises(KeyError):
            facade.relationship_mapping("noSuchPredicate")

    def test_unknown_class_fails_like_legacy(self) -> None:
        facade = self._facade()
        with pytest.raises((KeyError, ValueError)):
            facade.class_mapping("NoSuchClass")


class TestAuthorityIndependence:
    """Fixture old-YAML mutations must not change the candidate O3 mapping."""

    @staticmethod
    def _mutated_contract(tmp_path: Path, mutate) -> KernelContract:
        document = yaml.safe_load((REPO_ROOT / ob.ONTOLOGY_PATH).read_text())
        mutate(document)
        path = tmp_path / "ontology.yaml"
        path.write_text(yaml.safe_dump(document))
        return KernelContract.load(path)

    def _check(self, tmp_path: Path, mutate, identity: str, field: str, value):
        contract = self._mutated_contract(tmp_path, mutate)
        rows, entries = ob._load_chain_rows(REPO_ROOT)
        facade = ob.O3AuthorityFacade(
            legacy=contract,
            bundle=ob.build_candidate_bundle(REPO_ROOT, git_revision="a" * 40),
            projection_rows=rows,
            profile_entries=entries,
        )
        # The candidate mapping still comes from Projection/Profile ...
        candidate = facade.relationship_mapping(identity)
        assert candidate.configuration.get(field) != value
        # ... while the legacy contract observes the mutated authored YAML.
        legacy = contract.relationship_mapping(identity)
        assert legacy.configuration.get(field) == value

    def test_hasrelevanarchitecture_direction_mutation_ignored(self, tmp_path) -> None:
        def mutate(document):
            document["relationships"]["hasRelevantArchitecture"]["sysml_mapping"][
                "direction"
            ] = "outgoing"

        self._check(
            tmp_path, mutate, "hasRelevantArchitecture", "direction", "outgoing"
        )

    def test_hassubject_member_property_mutation_ignored(self, tmp_path) -> None:
        def mutate(document):
            document["relationships"]["hasSubject"]["sysml_mapping"][
                "member_property"
            ] = "ownedRelatedElement"

        self._check(
            tmp_path, mutate, "hasSubject", "member_property", "ownedRelatedElement"
        )

    def test_verifiedby_reference_property_mutation_ignored(self, tmp_path) -> None:
        def mutate(document):
            document["relationships"]["verifiedBy"]["sysml_mapping"][
                "reference_property"
            ] = "referencedConstraint"

        self._check(
            tmp_path, mutate, "verifiedBy", "reference_property", "referencedConstraint"
        )

    def test_k_query_direction_mutation_ignored(self, tmp_path) -> None:
        def mutate(document):
            document["relationships"]["derivesRequirementFromNeed"]["sysml_mapping"][
                "query_direction"
            ] = "forward"

        self._check(
            tmp_path,
            mutate,
            "derivesRequirementFromNeed",
            "query_direction",
            "forward",
        )


class TestCrossPins:
    def test_migrated_set_matches_readiness_scope(self) -> None:
        assert ob.MIGRATED_IDENTITIES == oe.O3_SCOPE_IDENTITIES
        assert len(ob.MIGRATED_IDENTITIES) == 13

    def test_chains_match_readiness_chain(self) -> None:
        assert (ob.PROJECTION_CHAIN, ob.PROFILE_CHAIN) == (
            tuple(
                record for record in oe.O2_CHAIN if "projection" in record[0]
            ),
            tuple(record for record in oe.O2_CHAIN if "profile" in record[0]),
        )

    def test_runtime_build_covers_readiness_old_bundle_files(self) -> None:
        assert set(oe.OLD_BUNDLE_RUNTIME_FILES) <= set(ob.RUNTIME_BUILD_FILES)

    def test_k_baseline_constant_matches_reviewed_artifact(self) -> None:
        import importlib.util
        import sys

        sys_path = str(REPO_ROOT / "scripts")
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        spec = importlib.util.spec_from_file_location(
            "run_o3_equivalence",
            REPO_ROOT / "scripts" / "run_o3_equivalence.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        document = json.loads(
            (
                REPO_ROOT
                / "docs/method-conformance/o2/semantic-projection-v1.2.json"
            ).read_text(encoding="utf-8")
        )
        statement = ""
        for row in document["predicates"]:
            if row["identity"] == "derivesRequirementFromNeed":
                statement = (
                    row["relation"]["one_modeled_fact_two_navigations"][
                        "witness_population"
                    ]
                )
        assert (
            f"{module.READINESS_BASELINE_K_WITNESS_COUNT} authored connection usages"
            in statement
        )


class TestAuthorityAwareCaches:
    @pytest.fixture()
    def viewer(self):
        from tools.sysml_html_viewer import ask_model_semantic as ams

        return ams

    @staticmethod
    def _snapshot_service(authority: str):
        class _Binding:
            git_commit = "a" * 40
            sysml_project_id = "pid"
            sysml_commit_id = "cid"

        return SimpleNamespace(
            binding=_Binding(), semantic_authority_id=authority
        )

    def test_snapshot_identity_carries_authority(self, viewer, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(viewer, "_snapshot_dir", lambda: tmp_path)
        service = self._snapshot_service("de4sdv.o0-o1-authored-v1")
        identity = viewer._snapshot_identity(service)
        assert identity["semantic_authority_id"] == "de4sdv.o0-o1-authored-v1"
        assert identity["format"] == 2

    def test_snapshot_paths_do_not_collide_across_authorities(self, viewer, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(viewer, "_snapshot_dir", lambda: tmp_path)
        old_path = viewer._snapshot_path(
            self._snapshot_service("de4sdv.o0-o1-authored-v1")
        )
        new_path = viewer._snapshot_path(
            self._snapshot_service("o3-candidate:o3b-deadbeef")
        )
        assert old_path != new_path

    def test_snapshot_never_loads_across_authorities(self, viewer, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(viewer, "_snapshot_dir", lambda: tmp_path)
        old_service = self._snapshot_service("de4sdv.o0-o1-authored-v1")
        new_service = self._snapshot_service("o3-candidate:o3b-deadbeef")
        viewer._snapshot_write(old_service, [{"@type": "PartUsage", "@id": "e-1"}])
        assert viewer._snapshot_load(old_service) is not None
        assert viewer._snapshot_load(new_service) is None

    def test_semantic_context_cache_is_authority_scoped(self, viewer, monkeypatch) -> None:
        viewer._SEMANTIC_CTX_CACHE.clear()
        elements = [
            {
                "@id": "m1",
                "@type": "SubjectMembership",
                "memberElement": {"@id": "t-1"},
                "owningRelatedElement": {"@id": "r1"},
            },
            {"@id": "t-1", "@type": "PartUsage", "declaredName": "part"},
            {"@id": "r1", "@type": "RequirementUsage", "declaredName": "req"},
        ]
        targets = [{"@id": "t-1"}]

        class _Mapping:
            def __init__(self, configuration):
                self.configuration = configuration

        class _Contract:
            def relationship_mapping(self, name):
                table = {
                    "hasSubject": {
                        "membership_types": ["SubjectMembership"],
                        "member_property": "memberElement",
                    },
                    "verifiedBy": {
                        "membership_types": ["RequirementVerificationMembership"]
                    },
                    "hasRelevantEvidenceContract": {
                        "relationship_types": ["Dependency"],
                        "source_property": "source",
                        "target_property": "target",
                    },
                    "realizedBy": {"relationship_types": ["AllocationUsage"]},
                }
                return _Mapping(dict(table.get(name, {})))

        old_service = SimpleNamespace(
            contract=_Contract(), semantic_authority_id="de4sdv.o0-o1-authored-v1"
        )
        new_service = SimpleNamespace(
            contract=_Contract(), semantic_authority_id="o3-candidate:o3b-deadbeef"
        )
        first = viewer.api_method_context(old_service, targets, elements, max_hops=1)
        assert first, "fixture must produce a non-empty context"
        again = viewer.api_method_context(old_service, targets, elements, max_hops=1)
        assert again is first, "same targets + same authority must hit the cache"
        other = viewer.api_method_context(new_service, targets, elements, max_hops=1)
        assert other is not first, "different authority must miss the cache"
        assert len(viewer._SEMANTIC_CTX_CACHE) == 2
        viewer._SEMANTIC_CTX_CACHE.clear()


class TestClosureEvidenceStrictness:
    """BLOCKER B/C: closure records must be exactly-successful and
    self-verifying — raw status text or a recorded digest string alone can
    never close an executable bundle."""

    def _closed(self, *, grounding="EQUIVALENT"):
        return _closed_bundle(REPO_ROOT, "a" * 40, grounding=grounding)

    def _closure(self, closed):
        return closed["api_closure"]

    def test_validation_status_must_be_exactly_passed(self) -> None:
        for name in ob.REQUIRED_VALIDATIONS:
            for status in ("failed", "error", "unknown", None):
                closed, _binding, _digest = self._closed()
                closure = self._closure(closed)
                if status is None:
                    closure["validation"][name].pop("status", None)
                else:
                    closure["validation"][name]["status"] = status
                errors = ob.verify_bundle_document(closed, root=REPO_ROOT)
                assert any(
                    name in error and "passed" in error for error in errors
                ), (name, status, errors)

    def test_missing_validation_record_blocks(self) -> None:
        closed, _binding, _digest = self._closed()
        self._closure(closed)["validation"].pop("semantic_mcp")
        errors = ob.verify_bundle_document(closed, root=REPO_ROOT)
        assert any("semantic_mcp" in error for error in errors)

    def test_validation_evidence_digest_reverification(self, tmp_path: Path) -> None:
        files = {}
        for name in ob.REQUIRED_VALIDATIONS:
            path = tmp_path / f"{name}.json"
            path.write_text('{"result": "passed"}', encoding="utf-8")
            files[name] = path
        binder = _binding_for(REPO_ROOT, "a" * 40)
        bundle = ob.build_candidate_bundle(REPO_ROOT, git_revision="a" * 40)
        attestation = ob.build_closure_attestation(
            bundle,
            binding=binder,
            binding_sha256="sha256:" + "b" * 64,
            element_count=1,
            export_identity_sha256=None,
            validations={
                name: {
                    "status": "passed",
                    "artifact": name,
                    "path": str(files[name]),
                    "sha256": ob.sha256_file(files[name]),
                }
                for name in ob.REQUIRED_VALIDATIONS
            },
            verification_case_grounding={"result": "EQUIVALENT"},
            generated_at="1970-01-01T00:00:00+00:00",
        )
        closed = ob.close_bundle(bundle, attestation)
        assert (
            ob.verify_bundle_document(
                closed,
                root=REPO_ROOT,
                binding=binder,
                binding_sha256="sha256:" + "b" * 64,
                require_closed=True,
                validation_artifacts=files,
            )
            == []
        )
        files["semantic_mcp"].write_text('{"result": "regressed"}', encoding="utf-8")
        errors = ob.verify_bundle_document(
            closed, root=REPO_ROOT, validation_artifacts=files
        )
        assert any("semantic_mcp" in error and "digest" in error for error in errors)
        files["semantic_mcp"].unlink()
        errors = ob.verify_bundle_document(
            closed, root=REPO_ROOT, validation_artifacts=files
        )
        assert any("semantic_mcp" in error and "missing" in error for error in errors)

    def test_activation_eligibility_is_recomputed(self) -> None:
        closed, _binding, _digest = self._closed(grounding="NOT_YET_COMPARABLE")
        closure = self._closure(closed)
        assert closure["activation_eligible"] is False
        closure["activation_eligible"] = True
        errors = ob.verify_bundle_document(closed, root=REPO_ROOT)
        assert any("activation_eligible" in error for error in errors)

    def test_blocking_grounding_can_never_be_activation_eligible(self) -> None:
        closed, _binding, _digest = self._closed(grounding="BLOCKING_MISMATCH")
        closure = self._closure(closed)
        assert closure["activation_eligible"] is False
        closure["activation_eligible"] = True
        errors = ob.verify_bundle_document(closed, root=REPO_ROOT)
        assert any("BLOCKING_MISMATCH" in error for error in errors)

    def test_eligible_true_requires_equivalent_grounding_and_passed_validations(
        self,
    ) -> None:
        closed, _binding, _digest = self._closed(grounding="EQUIVALENT")
        closure = self._closure(closed)
        assert closure["activation_eligible"] is True
        closure["validation"]["product_line_scope"]["status"] = "failed"
        closure["activation_eligible"] = True
        errors = ob.verify_bundle_document(closed, root=REPO_ROOT)
        assert any("activation_eligible" in error for error in errors)

    def test_closure_digest_must_reproduce_from_structured_fields(self) -> None:
        closed, _binding, _digest = self._closed()
        self._closure(closed)["import_closure_digest"] = "sha256:" + "d" * 64
        errors = ob.verify_bundle_document(closed, root=REPO_ROOT)
        assert any("does not reproduce" in error for error in errors)

    def test_closure_components_are_self_verifying(self) -> None:
        mutations = (
            ("export_identity_sha256", "sha256:" + "e" * 64),
            ("element_count", 2),
            ("binding_sha256", "sha256:" + "f" * 64),
            ("sysml_commit_id", "other-commit"),
            ("sysml_project_id", "other-project"),
        )
        for field, value in mutations:
            closed, _binding, _digest = self._closed()
            self._closure(closed)[field] = value
            errors = ob.verify_bundle_document(closed, root=REPO_ROOT)
            assert any("does not reproduce" in error for error in errors), (
                field,
                errors,
            )
