"""O3 readiness — equivalence machinery and no-activation locks.

Covers the read-only O3 readiness tooling:

1. the committed scope document regenerates byte-identically, declares all
   13 reviewed identities EQUIVALENT, and carries the reviewed contract
   checks (K pair one-fact/two-navigations, hasSubject/verifiedBy
   restrictions, bounded hasRelevantArchitecture, vocabulary-only honesty,
   projection/profile separation);
2. the same-revision comparison harness blocks every basis and semantic
   difference and canonicalizes only semantically irrelevant ordering;
3. the tooling cannot activate runtime authority: it is absent from the
   runtime import graph, its write guard allows exactly one path, and
   running the generator changes no protected file.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from de4sdv.semantic import o3_equivalence as o3

REPO_ROOT = Path(__file__).resolve().parents[1]

RUNTIME_MODULES = (
    "de4sdv/semantic/runtime.py",
    "de4sdv/semantic/query.py",
    "de4sdv/semantic/traversal.py",
    "de4sdv/semantic/impact.py",
    "de4sdv/semantic/api_binding.py",
    "de4sdv/semantic/kernel_binding_index.py",
    "de4sdv/semantic/mcp_server.py",
    "de4sdv/semantic/method_evaluator.py",
    "de4sdv/semantic/method_contract.py",
)

PROTECTED_FILES = (
    "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    "de4sdv/semantic/traversal.py",
    "de4sdv/semantic/runtime.py",
    "docs/method-conformance/o2/semantic-projection-v1.2.json",
    "docs/method-conformance/o2/api-representation-profile-v1.2.json",
    "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml",
)


def _fingerprint(root: Path) -> dict[str, str]:
    return {
        rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()
        for rel in PROTECTED_FILES
    }


def _manifest(**overrides: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema": o3.COMPARISON_MANIFEST_SCHEMA,
        "authority_path": "old",
        "git_revision": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_closure_digest": "sha256:" + "b" * 64,
        "subject_ids": ["req-1", "req-2"],
        "evaluation_scope": "full-model",
        "runtime_build": "build-1",
        "completeness_boundary": "strict",
    }
    manifest.update(overrides)
    return manifest


def _result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "source_revision": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "predicate": "verifiedBy",
        "subject_id": "req-1",
        "direction": "Requirement -> VerificationCase",
        "semantic_strength": "native-verification",
        "claim_boundary": "coverage only",
        "support_state": "vocabulary-only",
        "completeness": "complete",
        "unsupported": [],
        "targets": ["case-1", "case-2"],
        "witnesses": ["w-1"],
        "path": ["req-1", "case-1"],
    }
    result.update(overrides)
    return result


class TestDeclaredScope:
    def test_static_parity_dimensions(self) -> None:
        document = o3.build_scope_document(REPO_ROOT)
        static = document["summary"]["static_parity"]
        assert static["identities_with_mismatch"] == []
        assert static["identities_with_pending_dimension"] == ["VerificationCase"]
        fully = static["identities_fully_equivalent"]
        assert len(fully) == 12
        assert "VerificationCase" not in fully
        dimensions = static["dimensions"]
        for dimension in ("declared_semantic_core", "representation_contract",
                          "claim_boundary", "scope_exclusions"):
            assert len(dimensions[dimension]["equivalent"]) == 13, dimension
            assert dimensions[dimension]["mismatch"] == [], dimension
        grounding = dimensions["grounding_identity"]
        assert len(grounding["equivalent"]) == 12
        assert grounding["not_yet_comparable"] == ["VerificationCase"]
        assert document["summary"]["contract_check_failures"] == []
        runtime = document["summary"]["runtime"]
        assert runtime["completed"] == []
        assert runtime["equivalent"] == []
        assert len(runtime["not_yet_comparable"]) == 13

    def test_verificationcase_grounding_is_not_rubber_stamped(self) -> None:
        """Grounding is not `native == native`: the construct leg is compared
        and the standard-library proof stays honestly pending."""
        document = o3.build_scope_document(REPO_ROOT)
        item = [
            entry
            for entry in document["identities"]
            if entry["identity"] == "VerificationCase"
        ][0]
        grounding = item["comparison"]["dimensions"]["grounding_identity"]
        assert grounding["classification"] == "NOT_YET_COMPARABLE"
        assert "standard-library grounding proof" in grounding["missing_evidence"]
        fields = grounding["fields"]
        assert fields["construct_kind"]["ok"] is True
        assert fields["library_anchors"]["ok"] is True
        assert fields["grounded_type_population"]["ok"] is True
        assert fields["grounded_type_population"]["new"] == sorted(
            ["VerificationCaseUsage", "VerificationCaseDefinition"]
        )

    def test_committed_scope_matches_regeneration(self) -> None:
        assert o3.check_scope_document(
            REPO_ROOT,
            json.loads((REPO_ROOT / o3.O3_SCOPE_PATH).read_text(encoding="utf-8")),
        ) == []

    def test_scope_surface_is_exactly_the_reviewed_thirteen(self) -> None:
        document = o3.build_scope_document(REPO_ROOT)
        scope = document["scope"]
        assert scope["reviewed_surface_count"] == 13
        assert scope["o2_1"] == list(o3.O2_SURFACE_O21)
        assert scope["o2_2"] == list(o3.O2_SURFACE_O22)
        assert scope["o2_3"] == list(o3.O2_SURFACE_O23)
        moved = set(scope["o2_1"]) | set(scope["o2_2"]) | set(scope["o2_3"])
        for identity in o3.EXCLUDED_IDENTITIES:
            assert identity not in moved

    def test_support_matrix_preserves_every_gap(self) -> None:
        document = o3.build_scope_document(REPO_ROOT)
        rows = document["support_preservation"]
        assert len(rows) == 13
        for row in rows:
            assert row["promotion"] == "none"
            assert row["readiness_verdict"] == "NO_PROMOTION"
            assert row["runtime_preservation"] == "NOT_YET_COMPARABLE"
            assert row["new_support_state"] == "vocabulary-only"

    def test_comparison_base_revision_is_ancestor(self) -> None:
        document = o3.build_scope_document(REPO_ROOT)
        base = document["basis"]["comparison_base_revision"]
        assert o3._git(REPO_ROOT, "merge-base", "--is-ancestor", base, "HEAD") == ""

    def test_runtime_behavior_is_not_yet_comparable(self) -> None:
        document = o3.build_scope_document(REPO_ROOT)
        for item in document["identities"]:
            assert item["runtime_behavior"]["classification"] == (
                "NOT_YET_COMPARABLE"
            )
            assert (
                item["runtime_behavior"]["required_harness"]
                == o3.COMPARISON_MANIFEST_SCHEMA
            )


class TestComparatorBlocks:
    """Every basis/semantic difference blocks; only ordering canonicalizes."""

    def test_different_revisions_cannot_compare_as_equivalent(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(source_revision="c" * 40)
        )
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert "basis-mismatch:revision" in report["mismatches"]

    def test_different_api_project_cannot_compare_as_equivalent(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(sysml_project_id="project-2")
        )
        assert "basis-mismatch:sysml-project" in report["mismatches"]

    def test_different_api_commit_cannot_compare_as_equivalent(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(sysml_commit_id="commit-2")
        )
        assert "basis-mismatch:sysml-commit" in report["mismatches"]

    def test_predicate_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(_result(), _result(predicate="hasSubject"))
        assert "predicate-mismatch" in report["mismatches"]

    def test_subject_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(_result(), _result(subject_id="req-9"))
        assert "subject-mismatch" in report["mismatches"]

    def test_canonical_direction_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(direction="Requirement -> Need")
        )
        assert "canonical-direction-mismatch" in report["mismatches"]

    def test_semantic_strength_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(semantic_strength="derivation")
        )
        assert "semantic-strength-mismatch" in report["mismatches"]

    def test_claim_boundary_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(claim_boundary="satisfaction")
        )
        assert "claim-boundary-mismatch" in report["mismatches"]

    def test_supported_vs_vocabulary_only_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(
            _result(support_state="supported"), _result()
        )
        assert "support-state-mismatch" in report["mismatches"]

    def test_completeness_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(completeness="incomplete")
        )
        assert "completeness-mismatch" in report["mismatches"]

    def test_unsupported_state_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(
            _result(), _result(unsupported=[{"predicate": "p", "authority_state": "blocked"}])
        )
        assert "unsupported-state-mismatch" in report["mismatches"]

    def test_target_set_mismatch_blocks(self) -> None:
        report = o3.compare_semantic_results(_result(), _result(targets=["case-1"]))
        assert "targets-mismatch" in report["mismatches"]

    def test_irrelevant_ordering_differences_compare_equivalent(self) -> None:
        report = o3.compare_semantic_results(
            _result(targets=["case-2", "case-1"]),
            _result(targets=["case-1", "case-2"]),
        )
        assert report["classification"] == "EQUIVALENT"
        assert report["mismatches"] == []

    def test_meaningful_sysml_ordering_stays_meaningful(self) -> None:
        report = o3.compare_semantic_results(
            _result(path=["req-1", "case-1"]),
            _result(path=["case-1", "req-1"]),
        )
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert "path-mismatch" in report["mismatches"]

    def test_domain_mismatch_blocks_declared_comparison(self) -> None:
        old = {
            "kind": "relationship",
            "declared": {"domain": "Requirement", "range": "Need", "semantic_strength": "derivation"},
            "runtime_status": {"old_canonical_direction": "Requirement -> Need"},
        }
        new = {
            "kind": "relationship",
            "declared": {
                "domain": "MemberProduct",
                "range": "Need",
                "canonical_direction": "Requirement -> Need",
                "semantic_strength": "derivation",
            },
        }
        report = o3.compare_declared("derivesRequirementFromNeed", old, new)
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert report["reasons"] == ["domain"]

    def test_range_mismatch_blocks_declared_comparison(self) -> None:
        old = {
            "kind": "relationship",
            "declared": {"domain": "Requirement", "range": "Need", "semantic_strength": "derivation"},
            "runtime_status": {"old_canonical_direction": "Requirement -> Need"},
        }
        new = {
            "kind": "relationship",
            "declared": {
                "domain": "Requirement",
                "range": "Requirement",
                "canonical_direction": "Requirement -> Need",
                "semantic_strength": "derivation",
            },
        }
        assert o3.compare_declared("x", old, new)["reasons"] == ["range"]

    def test_direction_mismatch_blocks_declared_comparison(self) -> None:
        old = {
            "kind": "relationship",
            "declared": {"domain": "Requirement", "range": "Need", "semantic_strength": "derivation"},
            "runtime_status": {"old_canonical_direction": "Requirement -> Need"},
        }
        new = {
            "kind": "relationship",
            "declared": {
                "domain": "Requirement",
                "range": "Need",
                "canonical_direction": "Need -> Requirement",
                "semantic_strength": "derivation",
            },
        }
        assert o3.compare_declared("x", old, new)["reasons"] == ["canonical_direction"]

    def test_strength_mismatch_blocks_declared_comparison(self) -> None:
        old = {
            "kind": "relationship",
            "declared": {"domain": "Requirement", "range": "Need", "semantic_strength": "derivation"},
            "runtime_status": {"old_canonical_direction": "Requirement -> Need"},
        }
        new = {
            "kind": "relationship",
            "declared": {
                "domain": "Requirement",
                "range": "Need",
                "canonical_direction": "Requirement -> Need",
                "semantic_strength": "relevance",
            },
        }
        assert o3.compare_declared("x", old, new)["reasons"] == ["semantic_strength"]

    def test_missing_identity_blocks(self) -> None:
        report = o3.compare_declared("hasSubject", None, None)
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert report["reasons"] == ["missing-identity"]

    def test_missing_identity_in_chain_raises(self) -> None:
        chain = o3.load_o2_chain(REPO_ROOT)
        broken = copy.deepcopy(chain)
        for rel in broken:
            for section in ("concepts", "predicates"):
                document = broken[rel]["document"]
                document[section] = [
                    row
                    for row in document.get(section, [])
                    if (row.get("identity") or row.get("for_concept")) != "hasSubject"
                ]
        with pytest.raises(ValueError, match="identity missing"):
            o3._relationship_new_record(broken, "hasSubject")

    def test_profile_semantic_contract_drift_blocks(self) -> None:
        chain = o3.load_o2_chain(REPO_ROOT)
        drifted = copy.deepcopy(chain)
        for entry in drifted[
            "docs/method-conformance/o2/api-representation-profile-v1.2.json"
        ]["document"]["profiles"]:
            if entry.get("for_identity") == "hasRelevantArchitecture":
                entry["semantic_contract_echo"]["semantic_strength"] = "allocation"
        checks = o3.run_contract_checks(drifted)
        drift = [
            check
            for check in checks
            if check["check"] == "profile-contract-echo"
            and check["identity"] == "hasRelevantArchitecture"
        ]
        assert drift and drift[0]["result"] == "FAIL"

    def test_manifest_pair_requires_identical_basis(self) -> None:
        assert o3.validate_manifest_pair(_manifest(), _manifest(authority_path="new")) == []
        errors = o3.validate_manifest_pair(
            _manifest(), _manifest(authority_path="new", git_revision="c" * 40)
        )
        assert errors == ["basis-mismatch:git_revision"]

    def test_manifest_pair_requires_distinct_authority_paths(self) -> None:
        errors = o3.validate_manifest_pair(_manifest(), _manifest())
        assert "authority-path-not-distinct" in errors

    def test_manifest_subject_set_mismatch_blocks(self) -> None:
        errors = o3.validate_manifest_pair(
            _manifest(), _manifest(authority_path="new", subject_ids=["req-1"])
        )
        assert errors == ["basis-mismatch:subject_ids"]

    def test_k_pair_duplication_blocks(self) -> None:
        old = {
            "derivesRequirementFromNeed": {"witnesses": ["w-1", "w-2"]},
            "derivedRequirementsOfNeed": {"witnesses": ["w-1", "w-2"]},
        }
        new = {
            "derivesRequirementFromNeed": {"witnesses": ["w-1", "w-2"]},
            "derivedRequirementsOfNeed": {"witnesses": ["w-9"]},
        }
        errors = o3.check_k_pair_witness_consistency(old, new)
        assert any("k-pair-duplication" in error for error in errors)

    def test_k_pair_population_change_blocks(self) -> None:
        old = {
            "derivesRequirementFromNeed": {"witnesses": ["w-1"]},
            "derivedRequirementsOfNeed": {"witnesses": ["w-1"]},
        }
        new = {
            "derivesRequirementFromNeed": {"witnesses": ["w-1", "w-2"]},
            "derivedRequirementsOfNeed": {"witnesses": ["w-1", "w-2"]},
        }
        errors = o3.check_k_pair_witness_consistency(old, new)
        assert "k-pair-witness-population-mismatch" in errors

    def test_k_pair_shared_witness_passes(self) -> None:
        old = {
            "derivesRequirementFromNeed": {"witnesses": ["w-1", "w-2"]},
            "derivedRequirementsOfNeed": {"witnesses": ["w-1", "w-2"]},
        }
        new = {
            "derivesRequirementFromNeed": {"witnesses": ["w-2", "w-1"]},
            "derivedRequirementsOfNeed": {"witnesses": ["w-1", "w-2"]},
        }
        assert o3.check_k_pair_witness_consistency(old, new) == []


class TestRepresentationContractDrift:
    """Static readiness must block when ONLY old-side mechanics drift.

    Each fixture keeps domain/range/canonical direction/semantic strength
    untouched — the semantic core still compares EQUIVALENT — proving the
    expanded comparison catches what the four-field check missed.
    """

    @staticmethod
    def _bundles() -> tuple[dict, dict]:
        contract = o3.KernelContract.load(REPO_ROOT / o3.ONTOLOGY_PATH)
        chain = o3.load_o2_chain(REPO_ROOT)
        return (
            o3.extract_old_bundle(REPO_ROOT, contract),
            o3.extract_new_bundle(chain),
        )

    def _assert_mechanics_drift_blocks(
        self, identity: str, mutate
    ) -> dict:
        old, new = self._bundles()
        old_identity = old["identities"][identity]
        new_identity = new["identities"][identity]
        mutate(old_identity["declared"])
        # The semantic core is untouched on purpose: the old four-field
        # comparison cannot see this drift.
        core = o3.compare_declared(identity, old_identity, new_identity)
        assert core["classification"] == "EQUIVALENT", identity
        report = o3.compare_representation_contract(
            identity, old_identity, new_identity
        )
        assert report["classification"] == "BLOCKING_MISMATCH", identity
        return report

    def test_hasrelevanarchitecture_direction_drift_blocks(self) -> None:
        def mutate(declared):
            assert declared["configuration"]["direction"] == "incoming"
            declared["configuration"]["direction"] = "outgoing"

        report = self._assert_mechanics_drift_blocks(
            "hasRelevantArchitecture", mutate
        )
        assert "direction" in report["reasons"]

    def test_hasrelevanarchitecture_exclusion_removed_blocks(self) -> None:
        def mutate(declared):
            del declared["configuration"]["exclude_source_specializations_of"]

        report = self._assert_mechanics_drift_blocks(
            "hasRelevantArchitecture", mutate
        )
        assert (
            "missing-old-mechanics:exclude_source_specializations_of"
            in report["reasons"]
        )

    def test_hasrelevanarchitecture_exclusion_class_change_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["exclude_source_specializations_of"] = (
                "Function"
            )

        report = self._assert_mechanics_drift_blocks(
            "hasRelevantArchitecture", mutate
        )
        assert "exclude_source_specializations_of" in report["reasons"]

    def test_hasrelevanarchitecture_source_types_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["source_types"] = ["PartUsage"]

        report = self._assert_mechanics_drift_blocks(
            "hasRelevantArchitecture", mutate
        )
        assert "source_types" in report["reasons"]

    def test_hassubject_membership_types_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["membership_types"] = ["Subsetting"]

        report = self._assert_mechanics_drift_blocks("hasSubject", mutate)
        assert "membership_types" in report["reasons"]

    def test_hassubject_member_property_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["member_property"] = "ownedRelatedElement"

        report = self._assert_mechanics_drift_blocks("hasSubject", mutate)
        assert "member_property" in report["reasons"]

    def test_verifiedby_direction_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["direction"] = "forward"

        report = self._assert_mechanics_drift_blocks("verifiedBy", mutate)
        assert "direction" in report["reasons"]

    def test_verifiedby_reference_property_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["reference_property"] = (
                "referencedConstraint"
            )

        report = self._assert_mechanics_drift_blocks("verifiedBy", mutate)
        assert "reference_property" in report["reasons"]

    def test_verifiedby_membership_types_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["membership_types"] = [
                "RequirementConstraintMembership"
            ]

        report = self._assert_mechanics_drift_blocks("verifiedBy", mutate)
        assert "membership_types" in report["reasons"]

    def test_k_query_direction_swapped_blocks(self) -> None:
        def mutate(declared):
            assert declared["configuration"]["query_direction"] == "inverse"
            declared["configuration"]["query_direction"] = "forward"

        report = self._assert_mechanics_drift_blocks(
            "derivesRequirementFromNeed", mutate
        )
        assert "query_direction" in report["reasons"]

    def test_k_connection_definition_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["connection_definition"] = (
                "SomeOtherConnection"
            )

        report = self._assert_mechanics_drift_blocks(
            "derivedRequirementsOfNeed", mutate
        )
        assert "connection_definition" in report["reasons"]

    def test_k_need_role_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["need_role"] = "sourceNeed"

        report = self._assert_mechanics_drift_blocks(
            "derivesRequirementFromNeed", mutate
        )
        assert "need_role" in report["reasons"]

    def test_k_requirement_role_changed_blocks(self) -> None:
        def mutate(declared):
            declared["configuration"]["requirement_role"] = "targetRequirement"

        report = self._assert_mechanics_drift_blocks(
            "derivedRequirementsOfNeed", mutate
        )
        assert "requirement_role" in report["reasons"]

    def test_dimension_assembly_never_equivalent_on_mechanics_drift(self) -> None:
        old, new = self._bundles()
        old["identities"]["hasSubject"]["declared"]["configuration"][
            "member_property"
        ] = "ownedRelatedElement"
        result = o3.compare_identity_dimensions(
            "hasSubject",
            old["identities"]["hasSubject"],
            new["identities"]["hasSubject"],
        )
        assert result["classifications"]["declared_semantic_core"] == "EQUIVALENT"
        assert (
            result["classifications"]["representation_contract"]
            == "BLOCKING_MISMATCH"
        )
        assert result["overall_static"] == "BLOCKING_MISMATCH"

    def test_verificationcase_grounding_identity_changed_blocks(self) -> None:
        old, new = self._bundles()
        mutated = copy.deepcopy(new)
        record = mutated["identities"]["VerificationCase"]
        assert record["declared"]["kernel_mapping_kind"] == "native"
        record["declared"]["native_grounding"] = (
            "native construct (SomeOtherThing)"
        )
        report = o3.compare_grounding_identity(
            "VerificationCase",
            old["identities"]["VerificationCase"],
            record,
        )
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert "construct-identity" in report["reasons"]

    def test_verificationcase_library_anchor_change_blocks(self) -> None:
        old, new = self._bundles()
        mutated = copy.deepcopy(new)
        record = mutated["identities"]["VerificationCase"]
        record["library_grounding_mechanics"]["definition_role"][
            "library_identity"
        ] = "VerificationCases::SomethingElse"
        report = o3.compare_grounding_identity(
            "VerificationCase",
            old["identities"]["VerificationCase"],
            record,
        )
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert "library-anchors" in report["reasons"]

    def test_verificationcase_type_population_change_blocks(self) -> None:
        old, new = self._bundles()
        mutated = copy.deepcopy(new)
        record = mutated["identities"]["VerificationCase"]
        record["library_grounding_mechanics"]["usage_role"][
            "applies_to"
        ] = "SomeOtherUsage"
        report = o3.compare_grounding_identity(
            "VerificationCase",
            old["identities"]["VerificationCase"],
            record,
        )
        assert report["classification"] == "BLOCKING_MISMATCH"
        assert "grounded-type-population" in report["reasons"]


class TestScopeDocumentFailures:
    def test_edited_scope_document_fails_the_check(self) -> None:
        document = json.loads((REPO_ROOT / o3.O3_SCOPE_PATH).read_text(encoding="utf-8"))
        tampered = copy.deepcopy(document)
        tampered["identities"][0]["new_authority"]["support_state"] = "supported"
        errors = o3.check_scope_document(REPO_ROOT, tampered)
        assert any("differs from regeneration" in error for error in errors)

    def test_stale_comparison_base_revision_fails(self) -> None:
        document = json.loads((REPO_ROOT / o3.O3_SCOPE_PATH).read_text(encoding="utf-8"))
        stale = copy.deepcopy(document)
        stale["basis"]["comparison_base_revision"] = "0" * 40
        errors = o3.check_scope_document(REPO_ROOT, stale)
        assert errors, "an unresolvable comparison base must fail closed"
        assert any(
            "regeneration failed" in error or "not a valid ancestor" in error
            for error in errors
        )

    def test_later_runtime_commits_cannot_rewrite_the_old_bundle_baseline(
        self,
    ) -> None:
        """The merged readiness record stays evidence about its recorded
        comparison base: old-bundle digests verify against THAT revision's
        Git objects, never the working tree of a later feature branch."""
        document = json.loads((REPO_ROOT / o3.O3_SCOPE_PATH).read_text(encoding="utf-8"))
        base = document["basis"]["comparison_base_revision"]
        recorded = document["basis"]["runtime_files"]["de4sdv/semantic/runtime.py"]
        frozen = "sha256:" + hashlib.sha256(
            subprocess.run(
                ["git", "show", f"{base}:de4sdv/semantic/runtime.py"],
                cwd=REPO_ROOT,
                capture_output=True,
                check=True,
            ).stdout
        ).hexdigest()
        assert recorded == frozen
        # The check stays green even when the working tree has moved on
        # (Stage-A edits the runtime implementation); it must never rewrite
        # the recorded baseline.
        assert o3.check_scope_document(REPO_ROOT, document) == []
        assert o3.recorded_basis_revision(REPO_ROOT) == base

    def test_tampered_recorded_digest_fails(self) -> None:
        document = json.loads((REPO_ROOT / o3.O3_SCOPE_PATH).read_text(encoding="utf-8"))
        tampered = copy.deepcopy(document)
        tampered["basis"]["runtime_files"]["de4sdv/semantic/runtime.py"] = (
            "sha256:" + "0" * 64
        )
        errors = o3.check_scope_document(REPO_ROOT, tampered)
        assert any("differs from regeneration" in error for error in errors)

    def test_missing_scope_document_is_a_hard_error(self, tmp_path: Path) -> None:
        from scripts import generate_o3_equivalence_scope

        errors = generate_o3_equivalence_scope.run_check_errors(tmp_path)
        assert errors == [
            f"O3 scope document missing: {o3.O3_SCOPE_PATH}"
        ]


class TestNoActivation:
    """The readiness tooling cannot switch, route, or activate authority."""

    def test_o3_equivalence_absent_from_runtime_import_graph(self) -> None:
        for rel in RUNTIME_MODULES:
            source = (REPO_ROOT / rel).read_text(encoding="utf-8")
            assert "o3_equivalence" not in source, rel

    def test_o3_equivalence_does_not_import_runtime_modules(self) -> None:
        module_path = REPO_ROOT / "de4sdv/semantic/o3_equivalence.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        banned = {
            "runtime",
            "query",
            "traversal",
            "impact",
            "api_binding",
            "kernel_binding_index",
            "mcp_server",
            "de4sdv.semantic.runtime",
            "de4sdv.semantic.query",
            "de4sdv.semantic.traversal",
            "de4sdv.semantic.impact",
            "de4sdv.semantic.api_binding",
            "de4sdv.semantic.kernel_binding_index",
            "de4sdv.semantic.mcp_server",
        }
        assert not (set(imported) & banned)

    def test_write_guard_allows_only_the_scope_document(self) -> None:
        allowed = REPO_ROOT / o3.O3_SCOPE_PATH
        o3.assert_writable(allowed, REPO_ROOT)
        for rel in PROTECTED_FILES:
            with pytest.raises(ValueError, match="refusing to write"):
                o3.assert_writable(REPO_ROOT / rel, REPO_ROOT)

    def test_running_the_generator_changes_no_protected_file(self) -> None:
        from scripts import generate_o3_equivalence_scope

        before = _fingerprint(REPO_ROOT)
        assert generate_o3_equivalence_scope.main(["--check"]) == 0
        assert generate_o3_equivalence_scope.main([]) == 0
        after = _fingerprint(REPO_ROOT)
        assert before == after

    def test_scope_document_is_labelled_planning_evidence(self) -> None:
        document = json.loads((REPO_ROOT / o3.O3_SCOPE_PATH).read_text(encoding="utf-8"))
        assert document["read_only"] is True
        assert "NOT activation authority" in document["note"]
