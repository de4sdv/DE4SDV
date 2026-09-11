"""Tests for the O1 Semantic Authority Inventory (Wave 0a).

Covers the accepted Phase-1 review test matrix: coverage, layer provenance,
classification closure, runtime-strategy completeness, the K precedent and
closure evidence, PLEML gating, text-parity rules, determinism, and
duplicate/incompatibility refusal. All repository-level assertions run
against the committed generated artifacts; synthetic fixtures are used for
fail-closed behavior.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest import mock

import pytest
import yaml

from de4sdv.semantic import authority_inventory as ai
from scripts import check_repo
from scripts import generate_semantic_authority_inventory as generator

REPO_ROOT = Path(__file__).resolve().parents[1]

INVENTORY_PATH = REPO_ROOT / ai.INVENTORY_JSON_PATH
MD_PATH = REPO_ROOT / ai.INVENTORY_MD_PATH
DRAFT_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.draft.json"
)
R0_README = REPO_ROOT / "docs/method-conformance/r0-handoff/README.md"

K_GIT_SHA = "72926c958d2bd3b1001088fa657ec906dffd53e7"
K_PROJECT = "ea96301d-343a-4592-bad4-5dd997ca906a"
K_COMMIT = "82ef02df-94fe-4100-94c9-2f961f314a28"
K_RUN = "34630102233"
K_ARTIFACT_ID = "10281038294"
K_ARTIFACT_NAME = f"full-model-api-ingestion-{K_GIT_SHA}"
K_ARCHIVE_DIGEST = (
    "sha256:70d37f39798114ceb9fbdb7e975e9ba9959bcae7a298164e204b12fa59d65a93"
)

PLEML_IDENTITIES = {
    "FeatureConfiguration",
    "specifiesFeature",
    "specifiesCommonCapability",
    "appliesToMemberProduct",
    "selectsFeature",
    "includesCommonCapability",
    "variesAt",
    "selectsVariant",
}
PLEML_GATE = "PLE-R -> PLE-Q -> PLE-S -> PLE-A"


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contract() -> ai.KernelContract:
    return ai.KernelContract.load(REPO_ROOT / ai.ONTOLOGY_PATH)


@pytest.fixture(scope="module")
def decisions() -> dict:
    return ai.load_reviewed_decisions(REPO_ROOT / ai.DECISIONS_PATH)


def _entries(inventory: dict) -> dict[str, dict]:
    return {entry["identity"]: entry for entry in inventory["entries"]}


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_exact_counts_from_generated_inventory(self, inventory):
        counts = inventory["counts"]
        assert counts["classes"] == 59
        assert counts["relationships"] == 34
        assert counts["total_entries"] == 93
        assert len(inventory["entries"]) == 93

    def test_exact_counts_recounted_from_contract(self, contract, inventory):
        assert len(contract.classes) == 59
        assert len(contract.relationships) == 34
        assert len(contract.classes) + len(contract.relationships) == 93
        assert inventory["counts"]["classes"] == len(contract.classes)
        assert inventory["counts"]["relationships"] == len(contract.relationships)

    def test_class_mapping_partition(self, contract, inventory):
        kinds = {"file": 0, "native": 0, "external": 0}
        for spec in contract.classes.values():
            kernel = spec["kernel"]
            present = [kind for kind in kinds if kind in kernel]
            assert len(present) == 1, spec
            kinds[present[0]] += 1
        assert kinds == {"file": 40, "native": 15, "external": 4}
        assert kinds == inventory["counts"]["class_mappings"]
        assert sum(kinds.values()) == len(contract.classes)

    def test_relationship_mapping_partition(self, contract, inventory):
        mapped = sum(
            1 for spec in contract.relationships.values() if "sysml_mapping" in spec
        )
        vocabulary = sum(
            1 for spec in contract.relationships.values() if "sysml_mapping" not in spec
        )
        assert mapped == 9
        assert vocabulary == 25
        assert mapped + vocabulary == len(contract.relationships) == 34
        assert inventory["counts"]["relationship_mappings"] == 9
        assert inventory["counts"]["relationship_vocabulary_only"] == 25

    def test_kernel_equation_and_cross_slice(self, inventory):
        kernel = inventory["kernel_accounting"]
        assert kernel["governed_declarations"] == 110
        assert kernel["mapped_in_directory"] == 39
        assert kernel["exclusions"] == 71
        assert (
            kernel["mapped_in_directory"] + kernel["exclusions"]
            == kernel["governed_declarations"]
        )
        assert kernel["mapped_out_of_directory"] == 1
        assert kernel["cross_slice_mappings"] == [
            {
                "identity": "AcceptanceCriterion",
                "file": (
                    "textual-notation-of-model/packages/features/middleware/"
                    "middleware_verification_evidence.sysml"
                ),
                "declaration": "requirement def MiddlewareAcceptanceCriterion",
            }
        ]

    def test_cross_slice_accounted_separately_from_governed_equation(self, inventory):
        kernel = inventory["kernel_accounting"]
        # The cross-slice mapping is NOT part of the governed-directory
        # equation: 39 + 71 = 110 holds without it.
        assert kernel["mapped_in_directory"] != 40
        counts = inventory["counts"]
        assert counts["kernel_mapped_in_dir"] == kernel["mapped_in_directory"]
        assert counts["kernel_mapped_out_of_dir"] == kernel["mapped_out_of_directory"]

    def test_reviewed_row_per_entry(self, inventory, decisions):
        entries = _entries(inventory)
        assert set(decisions["entries"]) == set(entries)
        for identity, entry in entries.items():
            assert set(entry["reviewed"]) == set(ai.REVIEWED_FIELDS)

    def test_governance_rules_accounted(self, inventory):
        rules = inventory["governance_rules"]
        assert len(rules) == 10
        assert inventory["counts"]["governance_rules"] == 10
        assert all(rule["identity"] for rule in rules)
        assert all(rule["kind"] == "validation-rule" for rule in rules)


# ---------------------------------------------------------------------------
# Layers
# ---------------------------------------------------------------------------

OBSERVED_KEYS = {
    "yaml_path",
    "grounding_kind",
    "file",
    "declaration",
    "doc_text_observation",
    "runtime_support",
    "ref",
    "domain",
    "range",
    "strategy",
    "semantic_strength",
    "query_direction",
}


class TestLayers:
    def test_every_field_attributable_to_one_layer(self, inventory):
        for entry in inventory["entries"]:
            assert set(entry) == {"identity", "kind", "observed", "reviewed"}
            assert set(entry["observed"]) <= OBSERVED_KEYS
            assert set(entry["reviewed"]) == set(ai.REVIEWED_FIELDS)
            overlap = set(entry["observed"]) & set(entry["reviewed"])
            assert not overlap, (entry["identity"], overlap)

    def test_reviewed_decisions_not_runtime_values(self):
        """The runtime never reads the inventory or the decisions dataset."""
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / "de4sdv").rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if path.name == "authority_inventory.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "authority_inventory" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))
            if "authority-review-decisions" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))
            if "semantic-authority-inventory" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))
        assert offenders == []

    def test_decisions_dataset_is_layer_b_only(self, decisions):
        assert decisions["schema"] == ai.DECISIONS_SCHEMA_ID
        entries = decisions["entries"]
        assert len(entries) == 93
        for identity, row in entries.items():
            assert set(row) == set(ai.REVIEWED_FIELDS), identity

    def test_observed_facts_reproducible_from_contract(self, contract):
        observed = ai.observed_entries(REPO_ROOT, contract)
        assert len(observed) == 93
        for identity, entry in observed.items():
            assert entry["kind"] in {"class", "relationship"}
            assert entry["observed"]["yaml_path"] in (
                f"classes:{identity}",
                f"relationships:{identity}",
            )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassification:
    def test_authority_vocabulary_closed(self, inventory, decisions):
        for entry in inventory["entries"]:
            assert entry["reviewed"]["authority_current"] in ai.AUTHORITY_SOURCES
            assert entry["reviewed"]["authority_target"] in ai.AUTHORITY_SOURCES
        assert list(ai.AUTHORITY_SOURCES) == decisions["dimensions"]["authority_source"]

    def test_evidence_vocabulary_closed(self, inventory, decisions):
        for entry in inventory["entries"]:
            assert entry["reviewed"]["evidence_state"] in ai.EVIDENCE_STATES
        assert list(ai.EVIDENCE_STATES) == decisions["dimensions"]["evidence_state"]

    def test_adoption_vocabulary_closed(self, inventory, decisions):
        for entry in inventory["entries"]:
            assert entry["reviewed"]["adoption_status"] in ai.ADOPTION_STATUSES
        assert list(ai.ADOPTION_STATUSES) == decisions["dimensions"]["adoption_status"]

    def test_no_combined_authority_evidence_category(self, inventory):
        """Authority and evidence remain separate dimensions."""
        for entry in inventory["entries"]:
            assert "model-authoritative-proven" != entry["reviewed"]["evidence_state"]
            assert "model-authoritative-proven" != entry["reviewed"]["authority_current"]
        text = INVENTORY_PATH.read_text(encoding="utf-8")
        assert "model-authoritative-proven" not in text

    def test_conditional_targets_are_not_current_authority(self, inventory):
        conditional = [
            entry
            for entry in inventory["entries"]
            if entry["reviewed"]["conditional_target"]
        ]
        assert len(conditional) == 9
        for entry in conditional:
            reviewed = entry["reviewed"]
            assert reviewed["transition_gate"], entry["identity"]
            assert reviewed["authority_target"] != reviewed["authority_current"]
        tally = inventory["authority_target_conditional_counts"]
        assert sum(tally.values()) == len(conditional)
        assert tally.get("accepted-library-grounded") == 8
        assert tally.get("de4sdv-application-semantic") == 1

    def test_blocked_and_unknown_cannot_become_supported(self, inventory):
        for entry in inventory["entries"]:
            reviewed = entry["reviewed"]
            if reviewed["evidence_state"] in {"blocked", "unknown"}:
                assert reviewed["closure_evidence_ref"] is None
                assert entry["observed"]["runtime_support"] != (
                    "supported (closure-verified)"
                )

    def test_unknown_requires_bounded_question(self, inventory):
        unknown = [
            entry
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "unknown"
        ]
        assert [entry["identity"] for entry in unknown] == ["AssuranceClaim"]
        assert unknown[0]["reviewed"]["unknowns"]


# ---------------------------------------------------------------------------
# Runtime completeness
# ---------------------------------------------------------------------------


class TestRuntimeCompleteness:
    def test_every_strategy_associated_or_explicitly_unassociated(self, inventory):
        rows = inventory["runtime_strategy_registry"]["strategies"]
        assert [row["strategy"] for row in rows] == [
            "allocation",
            "dependency",
            "derivation-connection",
            "external",
            "property-reference",
            "subject-membership",
            "verification",
            "verification-membership",
        ]
        associated = [row for row in rows if row["association"] == "ontology-mapping"]
        unassociated = [
            row for row in rows if row["association"] == "unassociated-capability"
        ]
        assert len(associated) == 6
        assert len(unassociated) == 2
        for row in associated:
            assert row["entries"], row["strategy"]
        for row in unassociated:
            assert row["classification"] == ai.UNASSOCIATED_STRATEGY_CLASSIFICATION
            assert row["note"]
        # The two known unassociated strategies are never silently dropped.
        assert {row["strategy"] for row in unassociated} == {
            "verification",
            "property-reference",
        }

    def test_associated_strategies_cover_every_mapped_relationship(
        self, inventory, contract
    ):
        rows = inventory["runtime_strategy_registry"]["strategies"]
        covered = {
            entry for row in rows for entry in row["entries"]
        }
        mapped = {
            name
            for name, spec in contract.relationships.items()
            if "sysml_mapping" in spec
        }
        assert covered == mapped

    def test_strategy_registry_matches_dispatch_source(self, inventory):
        source = (REPO_ROOT / ai.TRAVERSAL_SOURCE_PATH).read_text(encoding="utf-8")
        implemented = ai.implemented_traversal_strategies(source)
        rows = inventory["runtime_strategy_registry"]["strategies"]
        assert implemented == [row["strategy"] for row in rows]

    def test_dispatch_owned_by_single_module(self):
        assert ai.strategy_dispatch_sources(REPO_ROOT) == [ai.TRAVERSAL_SOURCE_PATH]

    def _fake_root(self, tmp_path: Path, traversal_source: str) -> Path:
        target = tmp_path / ai.TRAVERSAL_SOURCE_PATH
        target.parent.mkdir(parents=True)
        target.write_text(traversal_source, encoding="utf-8")
        return tmp_path

    def test_new_strategy_requires_inventory_treatment(self, tmp_path):
        """A new dispatch branch fails generation until it is treated."""
        root = self._fake_root(
            tmp_path,
            "def traverse(mapping):\n"
            "    if mapping.strategy == 'brand-new-capability':\n"
            "        return []\n",
        )
        contract = mock.Mock()
        contract.relationships = {}
        with pytest.raises(ai.InventoryError, match="brand-new-capability"):
            ai.strategy_accounting(root, contract, {"runtime_strategies": {}})
        # Explicit reviewed treatment passes; unsupported classification fails.
        treated = ai.strategy_accounting(
            root,
            contract,
            {
                "runtime_strategies": {
                    "brand-new-capability": {
                        "classification": ai.UNASSOCIATED_STRATEGY_CLASSIFICATION,
                        "note": "reviewed disposition",
                    }
                }
            },
        )
        assert treated[0]["association"] == "unassociated-capability"
        with pytest.raises(ai.InventoryError):
            ai.strategy_accounting(
                root,
                contract,
                {"runtime_strategies": {"brand-new-capability": {"note": "x"}}},
            )

    def test_mapping_to_unimplemented_strategy_fails(self, tmp_path):
        root = self._fake_root(
            tmp_path, "def traverse(mapping):\n    raise ValueError()\n"
        )
        contract = mock.Mock()
        contract.relationships = {
            "someRelationship": {"sysml_mapping": {"strategy": "not-implemented"}}
        }
        with pytest.raises(ai.InventoryError, match="not-implemented"):
            ai.strategy_accounting(root, contract, {"runtime_strategies": {}})

    def test_stale_unassociated_row_fails(self, tmp_path):
        root = self._fake_root(
            tmp_path, "def traverse(mapping):\n    raise ValueError()\n"
        )
        contract = mock.Mock()
        contract.relationships = {}
        with pytest.raises(ai.InventoryError, match="not implemented"):
            ai.strategy_accounting(
                root,
                contract,
                {
                    "runtime_strategies": {
                        "retired-strategy": {
                            "classification": ai.UNASSOCIATED_STRATEGY_CLASSIFICATION,
                            "note": "x",
                        }
                    }
                },
            )


# ---------------------------------------------------------------------------
# K precedent
# ---------------------------------------------------------------------------


class TestKPrecedent:
    K_TRIPLE = ("DerivesFromNeed", "derivesRequirementFromNeed", "derivedRequirementsOfNeed")

    def test_k_triple_remains_model_authoritative(self, inventory):
        entries = _entries(inventory)
        for identity in self.K_TRIPLE:
            assert entries[identity]["reviewed"]["authority_current"] == (
                "model-authoritative"
            )
            assert entries[identity]["reviewed"]["authority_target"] == (
                "model-authoritative"
            )

    def test_k_evidence_state_remains_privileged_closure_proven(self, inventory):
        entries = _entries(inventory)
        for identity in self.K_TRIPLE:
            assert entries[identity]["reviewed"]["evidence_state"] == (
                "privileged-closure-proven"
            )
            assert entries[identity]["reviewed"]["closure_evidence_ref"] == "r6-3"

    def test_closure_record_revision_matches_historical_r6_candidate(self, inventory):
        records = inventory["closure_evidence"]
        assert len(records) == 1
        record = records[0]
        assert record["id"] == "r6-3"
        assert record["git_sha"] == K_GIT_SHA
        assert record["sysml_project_id"] == K_PROJECT
        assert record["sysml_commit_id"] == K_COMMIT
        assert record["evidence_source"]["workflow_run"] == K_RUN
        assert record["evidence_source"]["run_result"] == "success"

    def test_closure_artifact_identity_is_the_known_artifact(self, inventory):
        artifact = inventory["closure_evidence"][0]["artifact"]
        assert artifact["github_artifact_id"] == K_ARTIFACT_ID
        assert artifact["name"] == K_ARTIFACT_NAME
        assert artifact["archive_content_digest"] == K_ARCHIVE_DIGEST
        assert artifact["archive_size_bytes"] == 41862182

    def test_archive_digest_is_named_as_archive_digest_not_internal(self, inventory):
        artifact = inventory["closure_evidence"][0]["artifact"]
        # The GitHub archive digest must never be presented as the internal
        # export/semantic/binding digest.
        assert "archive_content_digest" in artifact
        assert artifact["internal_export_digest"] is None
        assert "archive" in artifact["archive_digest_scope"].lower()
        assert "NOT the internal" in artifact["archive_digest_scope"]

    def test_k_support_semantics_unchanged(self, inventory):
        entries = _entries(inventory)
        assert entries["derivesRequirementFromNeed"]["observed"]["runtime_support"] == (
            "supported (closure-verified)"
        )
        assert entries["derivedRequirementsOfNeed"]["observed"]["runtime_support"] == (
            "supported (closure-verified)"
        )
        assert entries["DerivesFromNeed"]["observed"]["runtime_support"] == (
            "vocabulary-only"
        )

    def test_only_the_k_triple_carries_closure_evidence(self, inventory):
        for entry in inventory["entries"]:
            ref = entry["reviewed"]["closure_evidence_ref"]
            if ref:
                assert entry["identity"] in self.K_TRIPLE
                assert ref == "r6-3"

    def test_bare_boolean_is_insufficient_closure_evidence(self):
        """A closure record whose only evidence is a bare boolean fails."""
        observed = {
            "Thing": {
                "kind": "class",
                "observed": {
                    "yaml_path": "classes:Thing",
                    "grounding_kind": "native",
                    "ref": "x",
                    "runtime_support": "vocabulary-only",
                },
            }
        }
        reviewed = {
            "Thing": _valid_reviewed(evidence_state="privileged-closure-proven",
                                     closure_evidence_ref="bare")
        }
        bare_record = {
            "id": "bare",
            "subject_identities": ["Thing"],
            "proof": {"result": "pass", "closure_verified": True},
        }
        problems = ai.validate_inventory(
            observed, {"runtime_strategies": {}, "entries": reviewed},
            [bare_record], [],
        )
        joined = "\n".join(problems)
        assert "git_sha" in joined
        assert "workflow_run" in joined
        assert "artifact" in joined

    def test_privileged_without_record_fails(self):
        problems = _problems_for(
            _valid_reviewed(evidence_state="privileged-closure-proven",
                            closure_evidence_ref=None)
        )
        assert any("without a closure evidence record" in p for p in problems)

    def test_closure_ref_without_privileged_evidence_fails(self):
        problems = _problems_for(
            _valid_reviewed(
                evidence_state="repository-evidenced", closure_evidence_ref="r6-3"
            ),
            closure_records=[_valid_closure_record()],
        )
        assert any("closure_evidence_ref present" in p for p in problems)


# ---------------------------------------------------------------------------
# PLE gating
# ---------------------------------------------------------------------------


class TestPLE:
    def test_pleml_remains_pinned_not_adopted(self, inventory):
        entries = _entries(inventory)
        for identity in PLEML_IDENTITIES:
            reviewed = entries[identity]["reviewed"]
            assert reviewed["adoption_status"] == "pinned-not-adopted", identity
            assert reviewed["conditional_target"] is True, identity

    def test_all_eight_conditional_ple_targets_remain_gated(self, inventory):
        entries = _entries(inventory)
        gated = {
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["transition_gate"] == PLEML_GATE
        }
        assert gated == PLEML_IDENTITIES
        for identity in PLEML_IDENTITIES:
            reviewed = entries[identity]["reviewed"]
            assert reviewed["authority_target"] == "accepted-library-grounded"
            assert reviewed["authority_target"] != reviewed["authority_current"]

    def test_pinned_not_adopted_is_never_counted_as_accepted(self, inventory):
        accepted = inventory["adoption_status_counts"].get("accepted", 0)
        pinned = inventory["adoption_status_counts"]["pinned-not-adopted"]
        assert pinned == 8
        assert accepted == 4
        for identity in PLEML_IDENTITIES:
            assert _entries(inventory)[identity]["reviewed"]["adoption_status"] != (
                "accepted"
            )


# ---------------------------------------------------------------------------
# Text parity
# ---------------------------------------------------------------------------


class TestTextParity:
    def _file(self, body: str) -> str:
        return f"package T {{\n  {body}\n}}\n"

    def test_normalized_exact_after_cosmetic_normalization(self):
        file_text = self._file(
            "part def Widget {\n    doc /* A WIDGET does one thing, cleanly. */\n  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "normalized-exact"
        )

    def test_normalized_containment_is_exact(self):
        file_text = self._file(
            "part def Widget {\n"
            "    doc /* A widget does one thing cleanly, in the approved style. */\n"
            "  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "normalized-exact"
        )

    def test_material_wording_difference_remains_review_required(self):
        # High word overlap but no containment: must not be treated as parity
        # and must not be silently upgraded.
        file_text = self._file(
            "part def Widget {\n"
            "    doc /* A widget does one thing carefully and intentionally. */\n"
            "  }"
        )
        observation = ai.doc_text_observation(
            file_text, "part def Widget", "a widget does one thing cleanly"
        )
        assert observation == "differs"
        problems = _problems_for(_valid_reviewed(), observation=observation)
        assert any("review-required" in p for p in problems)

    def test_doc_absent_and_bodyless_observations(self):
        bodyless = self._file("part def Empty;")
        assert (
            ai.doc_text_observation(bodyless, "part def Empty", "definition")
            == "doc-absent (bodyless declaration)"
        )
        no_doc = self._file("part def Silent {\n  }")
        assert (
            ai.doc_text_observation(no_doc, "part def Silent", "definition")
            == "doc-absent"
        )

    def test_no_automatic_upgrade_of_evidence(self):
        # normalized-exact + review-required is contradictory.
        problems = _problems_for(
            _valid_reviewed(semantic_text_equivalence="review-required"),
            observation="normalized-exact",
        )
        assert any("no automatic upgrade" in p for p in problems)

    def test_review_required_requires_evidence(self):
        problems = _problems_for(
            _valid_reviewed(
                semantic_text_equivalence="review-required", required_evidence=[]
            ),
            observation="differs",
        )
        assert any("required_evidence" in p for p in problems)

    def test_no_fuzzy_matching_code_path(self):
        """The module exposes exactly one text comparator; no similarity API."""
        source = (REPO_ROOT / "de4sdv/semantic/authority_inventory.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("difflib", "SequenceMatcher", "cosine", "levenshtein"):
            assert forbidden not in source
        assert ai.normalize_text("A-b  c!") == "a b c"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeat_generation_byte_identical(self):
        first = generator.generate(REPO_ROOT)
        second = generator.generate(REPO_ROOT)
        assert ai.canonical_json(first) == ai.canonical_json(second)
        assert ai.render_markdown(first) == ai.render_markdown(second)

    def test_committed_artifacts_match_regeneration(self):
        assert generator.run_check_errors(REPO_ROOT) == []

    def test_check_fails_on_tampered_committed_artifact(self, tmp_path):
        tampered = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        tampered["counts"]["classes"] = 58
        json_copy = tmp_path / "tampered.json"
        json_copy.write_text(json.dumps(tampered), encoding="utf-8")
        md_copy = tmp_path / "tampered.md"
        md_copy.write_text(MD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(
            generator, "INVENTORY_JSON_PATH", str(json_copy)
        ), mock.patch.object(generator, "INVENTORY_MD_PATH", str(md_copy)):
            errors = generator.run_check_errors(REPO_ROOT)
        assert errors and "differs from" in errors[0]

    def test_check_fails_on_missing_artifact(self, tmp_path):
        with mock.patch.object(
            generator, "INVENTORY_JSON_PATH", str(tmp_path / "missing.json")
        ), mock.patch.object(
            generator, "INVENTORY_MD_PATH", str(tmp_path / "missing.md")
        ):
            errors = generator.run_check_errors(REPO_ROOT)
        assert len(errors) == 2

    def test_check_fails_when_inputs_changed_without_regeneration(self, tmp_path):
        # Simulate a changed decisions dataset: regeneration from the current
        # inputs no longer matches the committed artifact.
        committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        committed["binding"]["reviewed_decisions"]["digest"] = "sha256:" + "0" * 64
        json_copy = tmp_path / "drifted.json"
        json_copy.write_text(json.dumps(committed), encoding="utf-8")
        md_copy = tmp_path / "drifted.md"
        md_copy.write_text(MD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(
            generator, "INVENTORY_JSON_PATH", str(json_copy)
        ), mock.patch.object(generator, "INVENTORY_MD_PATH", str(md_copy)):
            errors = generator.run_check_errors(REPO_ROOT)
        assert any("differs from" in error for error in errors)


# ---------------------------------------------------------------------------
# Duplicates and incompatible classifications
# ---------------------------------------------------------------------------


def _valid_reviewed(**overrides) -> dict:
    row = {
        "authority_current": "legacy-yaml",
        "authority_target": "model-authoritative",
        "evidence_state": "repository-evidenced",
        "adoption_status": "not-applicable",
        "transition_gate": None,
        "conditional_target": False,
        "disposition": "move-meaning-into-model",
        "confidence": "high",
        "stage": "test-stage",
        "note": "",
        "unknowns": [],
        "required_evidence": ["model-side definition parity"],
        "exact_fit_decision": None,
        "closure_evidence_ref": None,
        "semantic_text_equivalence": None,
    }
    row.update(overrides)
    return row


def _valid_closure_record() -> dict:
    return {
        "id": "r6-3",
        "schema": ai.CLOSURE_SCHEMA_ID,
        "subject_identities": ["Thing"],
        "git_sha": K_GIT_SHA,
        "sysml_project_id": K_PROJECT,
        "sysml_commit_id": K_COMMIT,
        "evidence_source": {"workflow_run": K_RUN},
        "artifact": {"name": "artifact"},
        "proof": {"result": "pass"},
        "status": "historical",
    }


def _problems_for(reviewed: dict, observation=None, closure_records=None) -> list[str]:
    observed = {
        "Thing": {
            "kind": "class",
            "observed": {
                "yaml_path": "classes:Thing",
                "grounding_kind": "native",
                "ref": "x",
                "runtime_support": "vocabulary-only",
            },
        }
    }
    if observation is not None:
        observed["Thing"]["observed"].pop("ref", None)
        observed["Thing"]["observed"]["grounding_kind"] = "file-declaration"
        observed["Thing"]["observed"]["file"] = "f.sysml"
        observed["Thing"]["observed"]["declaration"] = "part def Thing"
        observed["Thing"]["observed"]["doc_text_observation"] = observation
    return ai.validate_inventory(
        observed,
        {"runtime_strategies": {}, "entries": {"Thing": reviewed}},
        closure_records if closure_records is not None else [],
        [],
    )


class TestDuplicatesAndIncompatibility:
    def test_duplicate_closure_id_fails(self):
        record = _valid_closure_record()
        problems = ai.validate_inventory(
            {
                "Thing": {
                    "kind": "class",
                    "observed": {
                        "yaml_path": "classes:Thing",
                        "grounding_kind": "native",
                        "ref": "x",
                        "runtime_support": "vocabulary-only",
                    },
                }
            },
            {
                "runtime_strategies": {},
                "entries": {
                    "Thing": _valid_reviewed(
                        evidence_state="privileged-closure-proven",
                        closure_evidence_ref="r6-3",
                    )
                },
            },
            [record, dict(record)],
            [],
        )
        assert any("duplicate closure record id" in p for p in problems)

    def test_duplicate_yaml_identity_fails(self, tmp_path):
        path = tmp_path / "decisions.yaml"
        path.write_text(
            textwrap.dedent(
                """\
                schema: de4sdv.semantic-authority-reviews/v1
                dimensions:
                  authority_source: []
                  evidence_state: []
                  adoption_status: []
                entries:
                  Thing:
                    authority_current: legacy-yaml
                  Thing:
                    authority_current: native-sysml
                """
            ),
            encoding="utf-8",
        )
        with pytest.raises(ai.InventoryError, match="duplicate key"):
            ai.load_reviewed_decisions(path)

    def test_missing_decision_row_fails(self):
        problems = ai.validate_inventory(
            {
                "Thing": {
                    "kind": "class",
                    "observed": {
                        "yaml_path": "classes:Thing",
                        "grounding_kind": "native",
                        "ref": "x",
                        "runtime_support": "vocabulary-only",
                    },
                }
            },
            {"runtime_strategies": {}, "entries": {}},
            [],
            [],
        )
        assert any("missing reviewed decision row" in p for p in problems)

    def test_unknown_decision_row_fails(self):
        problems = ai.validate_inventory(
            {
                "Thing": {
                    "kind": "class",
                    "observed": {
                        "yaml_path": "classes:Thing",
                        "grounding_kind": "native",
                        "ref": "x",
                        "runtime_support": "vocabulary-only",
                    },
                }
            },
            {
                "runtime_strategies": {},
                "entries": {
                    "Thing": _valid_reviewed(),
                    "Ghost": _valid_reviewed(),
                },
            },
            [],
            [],
        )
        assert any("has no ontology entry" in p for p in problems)

    def test_incompatible_classifications_fail(self):
        cases = [
            (_valid_reviewed(conditional_target=True, transition_gate=None),
             "conditional target without a transition gate"),
            (_valid_reviewed(conditional_target=True,
                             transition_gate="gate",
                             authority_target="legacy-yaml"),
             "conditional target equals the current authority"),
            (_valid_reviewed(adoption_status="pinned-not-adopted"),
             "pinned-not-adopted requires a conditional target"),
            (_valid_reviewed(adoption_status="accepted"),
             "adoption_status accepted requires"),
            (_valid_reviewed(authority_current="bogus"),
             "outside the accepted authority vocabulary"),
            (_valid_reviewed(evidence_state="proven"),
             "outside the accepted evidence-state vocabulary"),
            (_valid_reviewed(adoption_status="adopted"),
             "outside the accepted adoption vocabulary"),
        ]
        for reviewed, message in cases:
            problems = _problems_for(reviewed)
            assert any(message in p for p in problems), (reviewed, problems)

    def test_vocabulary_dimensions_pinned_in_code(self, decisions):
        assert decisions["dimensions"]["authority_source"] == list(
            ai.AUTHORITY_SOURCES
        )
        assert decisions["dimensions"]["evidence_state"] == list(ai.EVIDENCE_STATES)
        assert decisions["dimensions"]["adoption_status"] == list(
            ai.ADOPTION_STATUSES
        )


# ---------------------------------------------------------------------------
# Supersession and gate integration
# ---------------------------------------------------------------------------


class TestSupersessionAndGate:
    def test_draft_carries_supersession_pointer(self):
        draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
        pointer = draft["superseded_by"]
        assert pointer["artifact"] == ai.INVENTORY_JSON_PATH
        assert pointer["generated_by"] == (
            "scripts/generate_semantic_authority_inventory.py"
        )

    def test_generated_inventory_declares_supersession(self, inventory):
        supersession = inventory["supersession"]
        assert (
            "docs/method-conformance/r0-handoff/semantic-authority-inventory.csv"
            in supersession["supersedes"]
        )
        assert "current migration inventory" in supersession["note"]

    def test_r0_readme_points_to_generated_inventory(self):
        text = R0_README.read_text(encoding="utf-8")
        assert "Supersession pointer" in text
        assert "semantic-authority-inventory.json" in text

    def test_runtime_registry_lists_draft_as_superseded(self, inventory):
        # The draft ceases to be the canonical inventory once the generated
        # artifact exists; the generated artifact says so explicitly.
        assert (
            "docs/method-conformance/o1/semantic-authority-inventory.draft.json"
            in inventory["supersession"]["supersedes"]
        )

    def test_check_repo_runs_inventory_gate(self):
        with mock.patch.object(
            check_repo, "find_duplicate_global_packages", return_value={}
        ), mock.patch.object(
            check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]
        ), mock.patch.object(
            check_repo.check_model_sync, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]
        ), mock.patch.object(
            check_repo.check_naming, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_semantic_authority_inventory,
            "run_check_errors",
            return_value=["sentinel inventory error"],
        ):
            assert check_repo.main() == 1

    def test_check_repo_passes_when_inventory_gate_passes(self):
        with mock.patch.object(
            check_repo, "find_duplicate_global_packages", return_value={}
        ), mock.patch.object(
            check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]
        ), mock.patch.object(
            check_repo.check_model_sync, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]
        ), mock.patch.object(
            check_repo.check_naming, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_semantic_authority_inventory,
            "run_check_errors",
            return_value=[],
        ):
            assert check_repo.main() == 0

