"""Tests for the O1 Semantic Authority Inventory (Wave 0a + corrections R1–R3).

Covers the accepted Phase-1 review test matrix and the three bounded review
corrections:

- coverage, layer provenance, classification closure, runtime-strategy
  completeness, the K precedent and closure evidence, PLEML gating;
- R1: source-revision binding (stale revisions fail, changed inputs fail,
  correct bindings pass, artifacts cannot self-authorize);
- R2: text parity is exact equality after cosmetic normalization (containment
  is not parity; material differences stay review-required);
- R3: reviewed consumer associations live in Layer B; Layer A reports only
  mechanically witnessed evidence.

All repository-level assertions run against the committed generated
artifacts; synthetic fixtures and temporary Git repositories are used for
fail-closed behavior.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
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

#: The seven rows that passed only via normalized containment in the accepted
#: Phase-1 draft. Under exact-equality parity they are honestly `differs`.
CONTAINMENT_ONLY_ROWS = {
    "EngineeringIncrement",
    "NeedsRequirementsIncrement",
    "IncrementEngineeringQuestion",
    "IncrementLifecycleDecision",
    "IncrementTraceabilityShell",
    "DeferredProductLineScope",
    "ProblemStatement",
}

CLASS_OBSERVED_KEYS = {
    "yaml_path",
    "grounding_kind",
    "file",
    "declaration",
    "doc_text_observation",
    "ref",
    "consumer_evidence",
}
RELATIONSHIP_OBSERVED_KEYS = {
    "yaml_path",
    "domain",
    "range",
    "grounding_kind",
    "strategy",
    "semantic_strength",
    "query_direction",
    "runtime_support",
}
ENTRY_REVIEWED_KEYS = set(ai.REVIEWED_FIELDS) | set(ai.REVIEWED_JOIN_FIELDS)


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


def _entry_support(entry: dict) -> str | None:
    if entry["kind"] == "relationship":
        return entry["observed"].get("runtime_support")
    consumption = entry["reviewed"].get("runtime_consumption")
    return consumption["support"] if consumption else "vocabulary-only"


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
        # The cross-slice mapping is NOT part of the governed-directory
        # equation: 39 + 71 = 110 holds without it.
        kernel = inventory["kernel_accounting"]
        assert kernel["mapped_in_directory"] != 40
        counts = inventory["counts"]
        assert counts["kernel_mapped_in_dir"] == kernel["mapped_in_directory"]
        assert counts["kernel_mapped_out_of_dir"] == kernel["mapped_out_of_directory"]

    def test_reviewed_row_per_entry(self, inventory, decisions):
        entries = _entries(inventory)
        assert set(decisions["entries"]) == set(entries)
        for identity, entry in entries.items():
            assert set(entry["reviewed"]) == ENTRY_REVIEWED_KEYS

    def test_governance_rules_accounted(self, inventory):
        rules = inventory["governance_rules"]
        assert len(rules) == 10
        assert inventory["counts"]["governance_rules"] == 10
        assert all(rule["identity"] for rule in rules)
        assert all(rule["kind"] == "validation-rule" for rule in rules)


# ---------------------------------------------------------------------------
# Layers
# ---------------------------------------------------------------------------


class TestLayers:
    def test_every_field_attributable_to_one_layer(self, inventory):
        for entry in inventory["entries"]:
            assert set(entry) == {"identity", "kind", "observed", "reviewed"}
            if entry["kind"] == "class":
                assert set(entry["observed"]) <= CLASS_OBSERVED_KEYS
                # Consumer support is reviewed provenance; a class entry must
                # never assert it under observed facts.
                assert "runtime_support" not in entry["observed"]
            else:
                assert set(entry["observed"]) <= RELATIONSHIP_OBSERVED_KEYS
                assert "consumer_evidence" not in entry["observed"]
                assert entry["reviewed"]["runtime_consumption"] is None
            assert set(entry["reviewed"]) == ENTRY_REVIEWED_KEYS
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

    def test_observed_facts_reproducible_from_contract(self, contract, decisions):
        observed = ai.observed_entries(REPO_ROOT, contract, decisions)
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
                assert _entry_support(entry) != "supported (closure-verified)"

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
        # DerivesFromNeed is a connection definition: no class-level consumer
        # association and no observed support claim (reviewed absence only).
        k_class = entries["DerivesFromNeed"]
        assert "runtime_support" not in k_class["observed"]
        assert k_class["reviewed"]["runtime_consumption"] is None
        assert k_class["observed"]["consumer_evidence"] == []

    def test_only_the_k_triple_carries_closure_evidence(self, inventory):
        for entry in inventory["entries"]:
            ref = entry["reviewed"]["closure_evidence_ref"]
            if ref:
                assert entry["identity"] in self.K_TRIPLE
                assert ref == "r6-3"

    def test_bare_boolean_is_insufficient_closure_evidence(self):
        """A closure record whose only evidence is a bare boolean fails."""
        observed = {"Thing": _observed_class()}
        reviewed = {
            "Thing": _valid_reviewed(
                evidence_state="privileged-closure-proven",
                closure_evidence_ref="bare",
            )
        }
        bare_record = {
            "id": "bare",
            "subject_identities": ["Thing"],
            "proof": {"result": "pass", "closure_verified": True},
        }
        problems = _validate(observed, reviewed, closure_records=[bare_record])
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
# Text parity (R2)
# ---------------------------------------------------------------------------


class TestTextParity:
    def _file(self, body: str) -> str:
        return f"package T {{\n  {body}\n}}\n"

    def test_equal_after_cosmetic_normalization_is_exact(self):
        file_text = self._file(
            "part def Widget {\n    doc /* A WIDGET does one thing, cleanly. */\n  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "normalized-exact"
        )

    def test_model_text_with_extra_semantic_sentence_is_not_parity(self):
        file_text = self._file(
            "part def Widget {\n"
            "    doc /* A widget does one thing cleanly. It also implies acceptance. */\n"
            "  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "differs"
        )

    def test_yaml_text_with_extra_semantic_sentence_is_not_parity(self):
        file_text = self._file(
            "part def Widget {\n    doc /* A widget does one thing cleanly. */\n  }"
        )
        assert (
            ai.doc_text_observation(
                file_text,
                "part def Widget",
                "a widget does one thing cleanly and implies acceptance",
            )
            == "differs"
        )

    def test_containment_in_either_direction_is_not_parity(self):
        file_text = self._file(
            "part def Widget {\n"
            "    doc /* A widget does one thing cleanly, in the approved style. */\n"
            "  }"
        )
        # Definition contained in the doc (doc adds text) — not parity.
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "differs"
        )
        # Doc contained in the definition (definition adds text) — not parity.
        assert (
            ai.doc_text_observation(
                file_text,
                "part def Widget",
                "a widget does one thing cleanly in the approved style, always",
            )
            == "differs"
        )

    def test_material_wording_difference_remains_review_required(self):
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

    def test_doc_observations_recomputed_from_source(self, contract, inventory):
        """Every file-declaration observation recomputes to the artifact value."""
        entries = _entries(inventory)
        counts: dict[str, int] = {}
        for name, spec in contract.classes.items():
            kernel = spec.get("kernel") or {}
            if "file" not in kernel:
                continue
            text = (REPO_ROOT / kernel["file"]).read_text(encoding="utf-8")
            observation = ai.doc_text_observation(
                text, kernel["declaration"], str(spec.get("definition", ""))
            )
            assert (
                entries[name]["observed"]["doc_text_observation"] == observation
            ), name
            counts[observation] = counts.get(observation, 0) + 1
        # Exact-equality parity: no row is normalized-exact any more, and the
        # seven containment-only rows honestly report material difference.
        assert counts == {"differs": 37, "doc-absent": 2, "doc-absent (bodyless declaration)": 1}

    def test_containment_only_rows_reclassified(self, inventory):
        entries = _entries(inventory)
        for identity in CONTAINMENT_ONLY_ROWS:
            entry = entries[identity]
            assert entry["observed"]["doc_text_observation"] == "differs", identity
            assert entry["reviewed"]["semantic_text_equivalence"] == (
                "review-required"
            ), identity
            assert entry["reviewed"]["required_evidence"], identity


# ---------------------------------------------------------------------------
# Revision binding (R1)
# ---------------------------------------------------------------------------

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    import os

    env = dict(os.environ)
    env.update(_GIT_ENV)
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = subprocess.run(
        ["git", "init", "-q"], cwd=repo, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return repo


def _write(repo: Path, relative: str, content: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit_all(repo: Path, message: str = "commit") -> str:
    _git(repo, "add", "-A")
    result = _git(repo, "commit", "-q", "-m", message)
    assert result.returncode == 0, result.stderr
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _digest(repo: Path, relative: str) -> str:
    return (
        "sha256:"
        + hashlib.sha256((repo / relative).read_bytes()).hexdigest()
    )


def _binding(repo: Path, revision: str, paths: list[str]) -> dict:
    return {
        "source_revision": revision,
        "bound_inputs": {path: _digest(repo, path) for path in sorted(paths)},
    }


class TestRevisionBinding:
    FILES = {"src/module.py": "x = 1\n", "data/input.yaml": "a: 1\n"}

    def _repo_with_commit(self, tmp_path: Path) -> tuple[Path, str]:
        repo = _init_repo(tmp_path)
        for relative, content in self.FILES.items():
            _write(repo, relative, content)
        revision = _commit_all(repo)
        return repo, revision

    def test_correct_source_revision_with_matching_digests_passes(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        assert ai.validate_source_binding(repo, binding) == []

    def test_changed_bound_input_with_unchanged_recorded_revision_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        # Uncommitted change to a bound input.
        _write(repo, "src/module.py", "x = 2\n")
        errors = ai.validate_source_binding(repo, binding)
        assert any("differs from its content at source_revision" in e for e in errors)
        # Committed change without rebinding is equally stale.
        _commit_all(repo, "change")
        errors = ai.validate_source_binding(repo, binding)
        assert any("differs from its content at source_revision" in e for e in errors)

    def test_generation_refuses_uncommitted_input_changes(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        bound_inputs = {
            path: _digest(repo, path) for path in sorted(self.FILES)
        }
        _write(repo, "data/input.yaml", "a: 2\n")
        with pytest.raises(ai.InventoryError, match="Commit the input changes first"):
            ai.verify_source_revision_contains_inputs(repo, revision, bound_inputs)

    def test_arbitrary_revision_string_cannot_self_authorize(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        binding["source_revision"] = "a" * 40
        errors = ai.validate_source_binding(repo, binding)
        assert any("not a commit in this repository" in e for e in errors)
        binding["source_revision"] = "not-a-sha"
        errors = ai.validate_source_binding(repo, binding)
        assert any("40-hex" in e for e in errors)

    def test_missing_bound_input_at_revision_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        _write(repo, "src/extra.py", "y = 1\n")
        _commit_all(repo, "add extra")
        paths = sorted(list(self.FILES) + ["src/extra.py"])
        binding = _binding(repo, revision, paths)
        errors = ai.validate_source_binding(repo, binding)
        assert any(
            "src/extra.py does not exist at source_revision" in e for e in errors
        )

    def test_digest_mismatch_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        binding["bound_inputs"]["src/module.py"] = "sha256:" + "0" * 64
        errors = ai.validate_source_binding(repo, binding)
        assert any("does not match the recorded digest" in e for e in errors)

    def test_non_ancestor_revision_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        branch = _git(repo, "symbolic-ref", "--short", "HEAD").stdout.strip()
        # Create an orphan history whose commit is not an ancestor of HEAD.
        _git(repo, "checkout", "-q", "--orphan", "other")
        _git(repo, "rm", "-rf", "-q", ".")
        _write(repo, "src/module.py", "z = 9\n")
        side_revision = _commit_all(repo, "side")
        _git(repo, "checkout", "-q", branch)
        binding = _binding(repo, revision, list(self.FILES))
        # HEAD moved back to the original branch; its binding still validates.
        assert ai.validate_source_binding(repo, binding) == []
        side_binding = {
            "source_revision": side_revision,
            "bound_inputs": {"src/module.py": _digest(repo, "src/module.py")},
        }
        errors = ai.validate_source_binding(repo, side_binding)
        assert any(
            "not an ancestor of the checked-out revision" in e for e in errors
        ), errors

    def test_real_repo_binding_is_valid(self, inventory):
        assert ai.validate_source_binding(REPO_ROOT, inventory["binding"]) == []

    def test_bound_inputs_cover_program_and_data_sources(self, inventory):
        bound = inventory["binding"]["bound_inputs"]
        for path in (
            "de4sdv/semantic/authority_inventory.py",
            "scripts/generate_semantic_authority_inventory.py",
            "scripts/check_model_sync.py",
            ai.ONTOLOGY_PATH,
            ai.DECISIONS_PATH,
            ai.CLOSURE_PATH,
            ai.TRAVERSAL_SOURCE_PATH,
        ):
            assert path in bound, path
        # Governed kernel model files and consumer-evidence files are bound too.
        assert (
            "textual-notation-of-model/packages/methods/de4sdv/"
            "de4sdv_method_context.sysml" in bound
        )
        assert "de4sdv/semantic/projection.py" in bound

    def test_named_input_digests_match_bound_inputs(self, inventory):
        binding = inventory["binding"]
        for key in (
            "ontology_contract",
            "reviewed_decisions",
            "closure_evidence",
            "runtime_strategy_source",
        ):
            record = binding[key]
            assert binding["bound_inputs"][record["path"]] == record["digest"]

    def test_artifact_commit_is_explicitly_unclaimed(self, inventory):
        assert inventory["binding"]["artifact_commit"] is None
        assert "cannot be known" in inventory["binding"]["artifact_commit_note"]


# ---------------------------------------------------------------------------
# Consumer-association provenance (R3)
# ---------------------------------------------------------------------------


class TestConsumerProvenance:
    def test_reviewed_associations_stored_as_layer_b(self, inventory, decisions):
        consumption = decisions["runtime_consumption"]
        assert len(consumption) == 14
        for identity, block in consumption.items():
            assert set(block) == set(ai.CONSUMER_ASSOCIATION_FIELDS), identity
            assert block["support"]
            assert block["consumer"]
            assert block["consumer_role"]
            assert block["evidence"]
            entry = _entries(inventory)[identity]
            assert entry["kind"] == "class"
            assert entry["reviewed"]["runtime_consumption"] == block

    def test_layer_a_records_only_witnessed_evidence(self, inventory):
        associated = 0
        for entry in inventory["entries"]:
            if entry["kind"] != "class":
                continue
            evidence = entry["observed"]["consumer_evidence"]
            block = entry["reviewed"]["runtime_consumption"]
            if block is None:
                assert evidence == []
                continue
            associated += 1
            assert evidence, entry["identity"]
            recorded = {
                (item["path"], item["kind"], item["expect"])
                for item in block["evidence"]
            }
            witnessed = {
                (item["path"], item["kind"], item["expect"])
                for item in evidence
            }
            assert witnessed == recorded, entry["identity"]
            for item in evidence:
                assert set(item) == {"path", "kind", "expect", "result"}
                assert item["result"] == "witnessed"
        assert associated == 14

    def test_support_strings_have_no_python_authority(self, decisions):
        source = (REPO_ROOT / "de4sdv/semantic/authority_inventory.py").read_text(
            encoding="utf-8"
        )
        for block in decisions["runtime_consumption"].values():
            assert block["support"] not in source
            assert block["consumer"] not in source
        assert not hasattr(ai, "CLASS_RUNTIME_CONSUMPTION")

    def test_missing_evidence_fails(self, tmp_path):
        association = {
            "support": "consumed",
            "consumer": "x",
            "consumer_role": "y",
            "evidence": [
                {"path": "missing.py", "kind": "exact-token", "expect": "Need"}
            ],
        }
        with pytest.raises(ai.InventoryError, match="evidence file missing"):
            ai.evaluate_consumer_evidence(tmp_path, "Thing", association)
        _write(tmp_path, "present.py", "nothing here\n")
        association["evidence"] = [
            {"path": "present.py", "kind": "exact-token", "expect": "Need"}
        ]
        with pytest.raises(ai.InventoryError, match="not witnessed"):
            ai.evaluate_consumer_evidence(tmp_path, "Thing", association)

    def test_token_occurrence_alone_cannot_create_association(self, inventory):
        """A class with no reviewed association gets no evidence, ever."""
        entries = _entries(inventory)
        # Scenario occurs across repository sources but carries no association.
        assert "Scenario" in (REPO_ROOT / "scripts/check_model_sync.py").read_text(
            encoding="utf-8"
        ) or "Scenario" in (REPO_ROOT / "de4sdv/semantic/projection.py").read_text(
            encoding="utf-8"
        )
        assert entries["Scenario"]["observed"]["consumer_evidence"] == []
        assert entries["Scenario"]["reviewed"]["runtime_consumption"] is None

    def test_evidence_kind_python_string_constant_excludes_docstrings(self, tmp_path):
        _write(tmp_path, "docstring_only.py", '"""Mentions Need in prose."""\nx = 1\n')
        _write(tmp_path, "code_string.py", 'value = "Need"\n')
        good = {"evidence": [
            {"path": "code_string.py", "kind": "python-string-constant", "expect": "Need"}
        ]}
        bad = {"evidence": [
            {"path": "docstring_only.py", "kind": "python-string-constant", "expect": "Need"}
        ]}
        assert ai.evaluate_consumer_evidence(tmp_path, "T", good)[0]["result"] == (
            "witnessed"
        )
        with pytest.raises(ai.InventoryError):
            ai.evaluate_consumer_evidence(tmp_path, "T", bad)

    def test_evidence_kind_sysml_type_usage_requires_typed_usage(self, tmp_path):
        _write(
            tmp_path,
            "usage.sysml",
            "package P {\n  attribute phase : MethodPhase;\n}\n",
        )
        _write(
            tmp_path,
            "import_only.sysml",
            "package P {\n  public import MethodPhase::*;\n}\n",
        )
        good = {"evidence": [
            {"path": "usage.sysml", "kind": "sysml-type-usage", "expect": "MethodPhase"}
        ]}
        bad = {"evidence": [
            {"path": "import_only.sysml", "kind": "sysml-type-usage", "expect": "MethodPhase"}
        ]}
        assert ai.evaluate_consumer_evidence(tmp_path, "T", good)[0]["result"] == (
            "witnessed"
        )
        with pytest.raises(ai.InventoryError):
            ai.evaluate_consumer_evidence(tmp_path, "T", bad)

    def test_evidence_kind_sysml_code_token_ignores_comments(self, tmp_path):
        _write(
            tmp_path,
            "commented.sysml",
            "package P {\n  /* import VVStatus mentions */\n}\n",
        )
        _write(
            tmp_path,
            "code.sysml",
            "package P {\n  public import VVStatus;\n}\n",
        )
        good = {"evidence": [
            {"path": "code.sysml", "kind": "sysml-code-token", "expect": "VVStatus"}
        ]}
        bad = {"evidence": [
            {"path": "commented.sysml", "kind": "sysml-code-token", "expect": "VVStatus"}
        ]}
        assert ai.evaluate_consumer_evidence(tmp_path, "T", good)[0]["result"] == (
            "witnessed"
        )
        with pytest.raises(ai.InventoryError):
            ai.evaluate_consumer_evidence(tmp_path, "T", bad)

    def test_evidence_kind_python_identifier(self, tmp_path):
        _write(tmp_path, "defs.py", "class MethodEvaluationScope:\n    pass\n")
        good = {"evidence": [
            {"path": "defs.py", "kind": "python-identifier", "expect": "MethodEvaluationScope"}
        ]}
        assert ai.evaluate_consumer_evidence(tmp_path, "T", good)[0]["result"] == (
            "witnessed"
        )

    def test_association_shape_is_validated(self, decisions):
        problems = ai._validate_consumer_association(
            "X", {"support": "s", "consumer": "c"}
        )
        joined = "\n".join(problems)
        assert "consumer_role" in joined
        assert "evidence" in joined


# ---------------------------------------------------------------------------
# Determinism and the committed-artifact check (R1 gate)
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

    def test_check_fails_on_stale_source_revision_claim(self, tmp_path):
        """Reusing a stored revision string cannot pass: the revision must
        actually contain the bound inputs."""
        tampered = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        tampered["binding"]["source_revision"] = (
            "976e1d3571b3706cd6b487535efb35f3df00e50d"  # real ancestor, wrong inputs
        )
        json_copy = tmp_path / "stale.json"
        json_copy.write_text(json.dumps(tampered), encoding="utf-8")
        md_copy = tmp_path / "stale.md"
        md_copy.write_text(MD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(
            generator, "INVENTORY_JSON_PATH", str(json_copy)
        ), mock.patch.object(generator, "INVENTORY_MD_PATH", str(md_copy)):
            errors = generator.run_check_errors(REPO_ROOT)
        assert errors
        assert any("does not exist at source_revision" in e for e in errors)

    def test_check_fails_on_arbitrary_source_revision(self, tmp_path):
        tampered = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        tampered["binding"]["source_revision"] = "a" * 40
        json_copy = tmp_path / "arbitrary.json"
        json_copy.write_text(json.dumps(tampered), encoding="utf-8")
        md_copy = tmp_path / "arbitrary.md"
        md_copy.write_text(MD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(
            generator, "INVENTORY_JSON_PATH", str(json_copy)
        ), mock.patch.object(generator, "INVENTORY_MD_PATH", str(md_copy)):
            errors = generator.run_check_errors(REPO_ROOT)
        assert any("not a commit in this repository" in e for e in errors)

    def test_check_fails_on_tampered_input_digest(self, tmp_path):
        tampered = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        tampered["binding"]["reviewed_decisions"]["digest"] = "sha256:" + "0" * 64
        json_copy = tmp_path / "digest.json"
        json_copy.write_text(json.dumps(tampered), encoding="utf-8")
        md_copy = tmp_path / "digest.md"
        md_copy.write_text(MD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(
            generator, "INVENTORY_JSON_PATH", str(json_copy)
        ), mock.patch.object(generator, "INVENTORY_MD_PATH", str(md_copy)):
            errors = generator.run_check_errors(REPO_ROOT)
        assert any("does not match" in e for e in errors)


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


def _observed_class() -> dict:
    return {
        "kind": "class",
        "observed": {
            "yaml_path": "classes:Thing",
            "grounding_kind": "native",
            "ref": "x",
            "consumer_evidence": [],
        },
    }


def _validate(
    observed: dict,
    reviewed_rows: dict,
    closure_records: list | None = None,
    consumption: dict | None = None,
    strategy_rows: list | None = None,
) -> list[str]:
    return ai.validate_inventory(
        observed,
        {
            "runtime_strategies": {},
            "entries": reviewed_rows,
            "runtime_consumption": consumption or {},
        },
        closure_records if closure_records is not None else [],
        strategy_rows if strategy_rows is not None else [],
    )


def _problems_for(reviewed: dict, observation=None, closure_records=None) -> list[str]:
    observed = {"Thing": _observed_class()}
    if observation is not None:
        observed["Thing"]["observed"].pop("ref", None)
        observed["Thing"]["observed"].update(
            {
                "grounding_kind": "file-declaration",
                "file": "f.sysml",
                "declaration": "part def Thing",
                "doc_text_observation": observation,
            }
        )
    return _validate(
        observed, {"Thing": reviewed}, closure_records=closure_records
    )


class TestDuplicatesAndIncompatibility:
    def test_duplicate_closure_id_fails(self):
        record = _valid_closure_record()
        problems = _validate(
            {"Thing": _observed_class()},
            {
                "Thing": _valid_reviewed(
                    evidence_state="privileged-closure-proven",
                    closure_evidence_ref="r6-3",
                )
            },
            closure_records=[record, dict(record)],
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
        problems = _validate({"Thing": _observed_class()}, {})
        assert any("missing reviewed decision row" in p for p in problems)

    def test_unknown_decision_row_fails(self):
        problems = _validate(
            {"Thing": _observed_class()},
            {"Thing": _valid_reviewed(), "Ghost": _valid_reviewed()},
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

    def test_consumer_association_requires_layer_a_evidence(self):
        consumption = {
            "Thing": {
                "support": "consumed",
                "consumer": "c",
                "consumer_role": "r",
                "evidence": [
                    {"path": "f.py", "kind": "exact-token", "expect": "Thing"}
                ],
            }
        }
        problems = _validate(
            {"Thing": _observed_class()},
            {"Thing": _valid_reviewed()},
            consumption=consumption,
        )
        assert any("without mechanically witnessed evidence" in p for p in problems)

    def test_consumer_association_is_class_only(self):
        observed = {
            "Rel": {
                "kind": "relationship",
                "observed": {
                    "yaml_path": "relationships:Rel",
                    "domain": "A",
                    "range": "B",
                    "grounding_kind": "yaml-vocabulary",
                    "runtime_support": "vocabulary-only",
                },
            }
        }
        consumption = {
            "Rel": {
                "support": "consumed",
                "consumer": "c",
                "consumer_role": "r",
                "evidence": [{"path": "f.py", "kind": "exact-token", "expect": "Rel"}],
            }
        }
        problems = _validate(
            observed, {"Rel": _valid_reviewed()}, consumption=consumption
        )
        assert any("class-only" in p for p in problems)

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
