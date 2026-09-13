"""O1 c1 — bounded method-conformance class parity batch (PR #249).

Covers the c1 claim after the independent review: **seven of the eight
identities are accepted as parity-reviewed; `MethodEvaluationScope` remains
incomplete** (R1 correction) because the model does not yet structurally
carry explicit exclusions with rationale — text parity (normalized-exact
definition-level doc) is NOT structural semantic parity.

The batch tests:

1.  exactly the eight named identities comprise c1 (no ninth entry);
2.  the seven accepted rows: evidence_state = parity-reviewed,
    authority_current = legacy-yaml preserved, authority_target =
    model-authoritative, no closure evidence, no supported-promotion, no
    conditional target;
3.  `MethodEvaluationScope`: authority stays legacy-yaml / model-authoritative,
    evidence stays repository-evidenced, the structural gap names exclusions
    with rationale, and normalized-exact text never promotes evidence;
4.  definition-level documentation is extracted independently from member
    (attribute / enum-literal) documentation per the SysML v2 spec ownership
    rule (a doc comment is owned by the element whose body it sits in);
5.  text parity is machine-checked (normalized-exact) for all eight, while
    evidence maturity is a separate reviewed dimension;
6.  structural exact-fit facts: declaration kinds, required typed members,
    required enum literals, the frozen Section 7 field coverage (12 schema
    fields -> 14 attribute declarations), and the external-reference /
    no-approval boundaries that justified each decision;
7.  no runtime/query/K/projection semantics changed: the inventory generator
    is runtime-inert and the c1 rows carry no Semantic Projection rows.

Adversarial cases prove the parity machinery rejects member-doc confusion,
missing docs, extra semantic text, and substring containment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import authority_inventory as ai

REPO_ROOT = Path(__file__).resolve().parents[1]

INVENTORY_PATH = REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS_PATH = REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"

CONFORMANCE_FILE = (
    REPO_ROOT
    / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml"
)
PROCESS_FILE = (
    REPO_ROOT
    / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml"
)

#: The c1 batch is exactly these eight identities — no ninth entry.
C1_IDENTITIES: tuple[str, ...] = (
    "MethodPhase",
    "MethodContractObligation",
    "MethodEvaluationScope",
    "EvaluationScopeMembership",
    "EvaluationSourceKind",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
)

#: The one c1 identity that is NOT yet parity-reviewed (R1 review correction):
#: the model carries increment identity and eligible subject types, but not the
#: explicit exclusions with rationale that the YAML definition requires.
C1_INCOMPLETE: tuple[str, ...] = ("MethodEvaluationScope",)

#: The seven c1 identities accepted as parity-reviewed after the review.
C1_ACCEPTED: tuple[str, ...] = tuple(
    name for name in C1_IDENTITIES if name not in C1_INCOMPLETE
)

#: YAML definition location + text of the eight (the O1 semantic authority for c1).
_C1_YAML: dict[str, tuple[Path, str]] = {
    "MethodPhase": (
        PROCESS_FILE,
        "One of the 13 phases of the DE4SDV increment workflow.",
    ),
    "MethodContractObligation": (
        CONFORMANCE_FILE,
        "A typed model-resident method-contract obligation: stable explicit "
        "identifier, phase reference, typed subject selector, restricted "
        "applicability, population policy, pinned predicate with declared "
        "input/output types, target filters, per-subject cardinality bounds, "
        "requiredness, evaluation source, optional attestation-policy "
        "reference, and exact claim boundary. Model materialization of the "
        "frozen baseline Section 7 schema.",
    ),
    "EvaluationSourceKind": (
        CONFORMANCE_FILE,
        "The kind of input an obligation reads: a pinned model record, a pinned "
        "repository artifact, or a live delivery adapter (outside deterministic "
        "V1 evaluation).",
    ),
    "MethodEvaluationScope": (
        CONFORMANCE_FILE,
        "An evaluation scope binding increment identity, eligible subject types, "
        "and explicit exclusions. Contribution set and evaluation scope are "
        "distinct sets; membership in evaluation scope is a reviewed scope "
        "decision, not an inferred impact claim.",
    ),
    "EvaluationScopeMembership": (
        CONFORMANCE_FILE,
        "Explicit membership of one subject in an evaluation scope, carrying the "
        "contributes flag that separates the contribution set from reused "
        "evaluation-scope members.",
    ),
    "TestedScopeDeclaration": (
        CONFORMANCE_FILE,
        "A candidate evaluation's declaration of the tested scope it compares "
        "retained evidence against: execution head and pinned profile "
        "identities (conservative scope-equality inputs).",
    ),
    "RetainedExecutionRecordReference": (
        CONFORMANCE_FILE,
        "A model-resident reference to one retained execution record with "
        "explicit external identity, artifact path, digest, and run identity; "
        "record bytes stay external.",
    ),
    "AcceptanceAttestationReference": (
        CONFORMANCE_FILE,
        "A model-resident reference to the authorization policy and the "
        "machine-declared decision-registry location. Policy status (proposed "
        "vs approved) is carried by the policy document, not by this reference; "
        "a missing registry and a known-empty registry are different states.",
    ),
}


def _declaration(name: str) -> str:
    contract = ai.KernelContract.load(REPO_ROOT / ai.ONTOLOGY_PATH)
    return str(contract.classes[name]["kernel"]["declaration"])


def _definition(name: str) -> str:
    contract = ai.KernelContract.load(REPO_ROOT / ai.ONTOLOGY_PATH)
    return str(contract.classes[name]["definition"])


def _file_text(name: str) -> str:
    path, _ = _C1_YAML[name]
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# c1 scope
# ---------------------------------------------------------------------------


class TestC1Scope:
    def test_exactly_eight_identities(self):
        assert len(C1_IDENTITIES) == 8
        assert len(set(C1_IDENTITIES)) == 8

    def test_all_eight_are_ontology_classes(self):
        contract = ai.KernelContract.load(REPO_ROOT / ai.ONTOLOGY_PATH)
        for name in C1_IDENTITIES:
            assert name in contract.classes, name
            assert name not in contract.relationships, name

    def test_the_seven_accepted_rows_are_parity_reviewed(self, inventory):
        """The seven accepted c1 identities are parity-reviewed and the
        incomplete MethodEvaluationScope is not. The GLOBAL parity set is
        owned by the executing batch's test file: after c2 it is these seven
        plus VerificationCase and verifiedBy — asserted exactly in
        tests/test_o1_c2_verification_grounding.py."""
        entries = _entries(inventory)
        for name in C1_ACCEPTED:
            assert (
                entries[name]["reviewed"]["evidence_state"] == "parity-reviewed"
            ), name
        for name in C1_INCOMPLETE:
            assert (
                entries[name]["reviewed"]["evidence_state"]
                == "repository-evidenced"
            ), name

    def test_authority_current_remains_legacy_yaml(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["authority_current"] == "legacy-yaml"

    def test_authority_target_is_model_authoritative(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["authority_target"] == "model-authoritative"

    def test_accepted_rows_are_parity_reviewed(self, inventory):
        for name in C1_ACCEPTED:
            entry = _entries(inventory, (name,))[name]
            assert entry["reviewed"]["evidence_state"] == "parity-reviewed", name

    def test_no_c1_row_receives_closure_evidence(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["closure_evidence_ref"] is None
            assert entry["reviewed"]["evidence_state"] != "privileged-closure-proven"

    def test_no_c1_row_is_marked_supported(self, inventory):
        """No support-state promotion: adoption stays not-applicable and no
        consumer support claim changes."""
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["adoption_status"] == "not-applicable"
            consumption = entry["reviewed"].get("runtime_consumption") or {}
            assert consumption.get("support") != "supported (closure-verified)"

    def test_no_c1_row_is_conditional(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["conditional_target"] is False
            assert entry["reviewed"]["transition_gate"] is None

    def test_no_c1_row_becomes_a_semantic_projection_row(self):
        """The Semantic Projection consumer de4sdv/semantic/projection.py is
        bound to the K-slice classes only; c1 rows are governance rows in the
        inventory, not generated projection rows."""
        source = (REPO_ROOT / "de4sdv/semantic/projection.py").read_text(
            encoding="utf-8"
        )
        for name in C1_IDENTITIES:
            assert f'"{name}"' not in source, name

    def test_later_batch_entries_stay_pinned(self, inventory):
        """Later-batch entries stay pinned to their reviewed states. The c2
        batch has since executed (PR #249 c2): its two rows advanced exactly
        as recorded there — current authority unchanged, evidence maturity
        advanced to parity-reviewed, stage renamed to the executed batch. The
        c3-c5 rows remain untouched by c2."""
        entries = _entries(inventory)
        expected = {
            "VerificationCase": (
                "c2 (verification batch)",
                "native-sysml",
                "parity-reviewed",
            ),
            "verifiedBy": (
                "c2 (verification batch)",
                "legacy-yaml",
                "parity-reviewed",
            ),
            "hasSubject": ("c3", "legacy-yaml", "repository-evidenced"),
            "derivesNeedFromConcern": ("c4", "legacy-yaml", "blocked"),
            "realizedBy": ("c5", "legacy-yaml", "repository-evidenced"),
            "specifiesFunction": ("c5", "legacy-yaml", "repository-evidenced"),
            "hasRelevantArchitecture": ("c5", "legacy-yaml", "repository-evidenced"),
            "hasRelevantEvidenceContract": ("c5", "legacy-yaml", "repository-evidenced"),
        }
        for identity, (stage, authority, evidence) in expected.items():
            row = entries[identity]["reviewed"]
            assert row["stage"] == stage, identity
            assert row["authority_current"] == authority, identity
            assert row["evidence_state"] == evidence, identity

    def test_ple_classifications_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in (
            "FeatureConfiguration",
            "specifiesFeature",
            "specifiesCommonCapability",
            "appliesToMemberProduct",
            "selectsFeature",
            "includesCommonCapability",
            "variesAt",
            "selectsVariant",
        ):
            entry = entries[identity]
            assert entry["reviewed"]["evidence_state"] == "blocked"
            assert entry["reviewed"]["adoption_status"] == "pinned-not-adopted"
            assert entry["reviewed"]["conditional_target"] is True

    def test_k_triple_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in (
            "DerivesFromNeed",
            "derivesRequirementFromNeed",
            "derivedRequirementsOfNeed",
        ):
            entry = entries[identity]
            assert entry["reviewed"]["authority_current"] == "model-authoritative"
            assert entry["reviewed"]["evidence_state"] == "privileged-closure-proven"
            assert entry["reviewed"]["closure_evidence_ref"] == "r6-3"


def _entries(
    inventory: dict, names: list[str] | tuple[str, ...] | None = None
) -> dict[str, dict]:
    by_identity = {entry["identity"]: entry for entry in inventory["entries"]}
    if names is None:
        return by_identity
    return {name: by_identity[name] for name in names}


def _probe_observed(observation: str) -> dict:
    return {
        "yaml_path": "classes:Thing",
        "grounding_kind": "file-declaration",
        "file": "f.sysml",
        "declaration": "part def Thing",
        "doc_text_observation": observation,
        "consumer_evidence": [],
    }


def _probe_reviewed(**overrides) -> dict:
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
        "required_evidence": ["model-side representation decision"],
        "exact_fit_decision": None,
        "closure_evidence_ref": None,
        "semantic_text_equivalence": None,
        "runtime_consumption": None,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# R1 review correction: MethodEvaluationScope stays incomplete
# ---------------------------------------------------------------------------


class TestMethodEvaluationScopeIncomplete:
    """Text parity and structural semantic parity are separate dimensions.

    The independent review corrected the first c1 pass: the definition-level
    doc is normalized-exact text, but the model does not yet structurally
    carry explicit exclusions with rationale, so MethodEvaluationScope must
    NOT be claimed parity-reviewed. The runtime exclusions input is
    implementation evidence for the delivered A–D execution, not
    model-authority parity.
    """

    def _row(self, inventory: dict) -> dict:
        return _entries(inventory, ("MethodEvaluationScope",))["MethodEvaluationScope"]

    def test_authority_current_is_legacy_yaml(self, inventory):
        assert self._row(inventory)["reviewed"]["authority_current"] == "legacy-yaml"

    def test_authority_target_is_model_authoritative(self, inventory):
        assert (
            self._row(inventory)["reviewed"]["authority_target"]
            == "model-authoritative"
        )

    def test_evidence_state_is_repository_evidenced(self, inventory):
        reviewed = self._row(inventory)["reviewed"]
        assert reviewed["evidence_state"] == "repository-evidenced"
        assert reviewed["evidence_state"] != "parity-reviewed"

    def test_text_observation_and_evidence_are_separate(self, inventory):
        """Text parity may be normalized-exact; evidence maturity stays
        repository-evidenced because structural parity is incomplete."""
        entry = self._row(inventory)
        assert entry["observed"]["doc_text_observation"] == "normalized-exact"
        assert entry["reviewed"]["evidence_state"] == "repository-evidenced"

    def test_normalized_exact_text_does_not_promote_evidence(self):
        """Test-lock: exact text parity never auto-promotes evidence maturity —
        the exact-text + repository-evidenced combination is an admissible
        honest state in the validator."""
        problems = ai._entry_problems(
            "Thing",
            "class",
            _probe_observed("normalized-exact"),
            _probe_reviewed(),
            {},
        )
        assert problems == []

    def test_validator_still_rejects_manual_equivalence_on_exact_text(self):
        problems = ai._entry_problems(
            "Thing",
            "class",
            _probe_observed("normalized-exact"),
            _probe_reviewed(semantic_text_equivalence="review-required"),
            {},
        )
        assert any("no automatic upgrade" in problem for problem in problems)

    def test_structural_gap_names_exclusions_and_rationale(self):
        """The reviewed decision explicitly records the structural gap: the
        model does not yet carry explicit exclusions with rationale."""
        decisions = yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))
        row = decisions["entries"]["MethodEvaluationScope"]
        decision = row["exact_fit_decision"]
        assert "not exact structural fit" in decision
        assert "exclusions" in decision
        unknowns = " ".join(row["unknowns"])
        assert "exclusions" in unknowns
        assert "rationale" in unknowns
        assert "model-authority parity" in unknowns
        # No approval-style promotion: evidence state lives in the dataset too.
        assert row["evidence_state"] == "repository-evidenced"

    def test_required_evidence_sequence_starts_with_representation_decision(self):
        """O2 cannot close this gap alone: the sequence starts with a reviewed
        semantic/model representation decision, then implementation + parity
        review, then O2 generation, then the O3 transition."""
        decisions = yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))
        row = decisions["entries"]["MethodEvaluationScope"]
        required = row["required_evidence"]
        assert required
        assert "representation decision" in required[0]
        joined = " ".join(required)
        assert "parity review" in joined
        assert "O2" in joined and "O3" in joined

    def test_runtime_exclusions_are_not_model_authority(self, inventory):
        """The runtime exclusions input is implementation evidence for the
        delivered A–D execution; it is neither removed nor treated as
        model-resident authority, and the model must NOT carry an exclusions
        field (no redesign in this correction pass)."""
        decision = self._row(inventory)["reviewed"]["exact_fit_decision"]
        assert "implementation evidence" in decision
        assert "not model-authority parity" in decision
        # The runtime input still exists (unchanged by this correction) ...
        runtime = (REPO_ROOT / "de4sdv/semantic/method_contract.py").read_text(
            encoding="utf-8"
        )
        assert "exclusions" in runtime
        # ... and the model does not gain an exclusions field.
        text = _file_text("MethodEvaluationScope")
        block, _ = ai.declaration_block(text, "part def MethodEvaluationScope")
        assert "attribute exclusions" not in block


# ---------------------------------------------------------------------------
# Definition-level documentation extraction (adversarial)
# ---------------------------------------------------------------------------


class TestDefinitionDocExtraction:
    def _wrap(self, body: str) -> str:
        return f"package T {{\n{body}\n}}\n"

    def test_attribute_docs_are_not_definition_docs(self):
        """The MethodContractObligation shape: docs that follow attribute
        declarations must not contaminate the class definition text."""
        file_text = self._wrap(
            "item def Widget {\n"
            "    doc /* CLASS DEFINITION TEXT. */\n"
            "    attribute a : String;\n"
            "    doc /* attribute a doc. */\n"
            "    attribute b : Natural;\n"
            "    doc /* attribute b doc. */\n"
            "  }"
        )
        block, _ = ai.declaration_block(file_text, "item def Widget")
        docs = ai._leading_owned_doc_bodies(block)
        assert [d.strip() for d in docs] == ["CLASS DEFINITION TEXT."]

    def test_enum_literal_docs_are_not_definition_docs(self):
        """The MethodPhase shape: per-literal docs (inside literal bodies) and
        docs following literals must not contaminate the enum definition."""
        file_text = self._wrap(
            "enum def Widget {\n"
            "    doc /* ENUM DEFINITION TEXT. */\n"
            "    lit1 {\n"
            "      doc /* lit1 doc. */\n"
            "    }\n"
            "    lit2;\n"
            "    doc /* lit2-position doc. */\n"
            "  }"
        )
        block, _ = ai.declaration_block(file_text, "enum def Widget")
        docs = ai._leading_owned_doc_bodies(block)
        assert [d.strip() for d in docs] == ["ENUM DEFINITION TEXT."]

    def test_adding_member_doc_does_not_alter_class_parity(self):
        base = self._wrap(
            "part def Widget {\n"
            "    doc /* The widget meaning. */\n"
            "    attribute a : String;\n"
            "  }"
        )
        changed = self._wrap(
            "part def Widget {\n"
            "    doc /* The widget meaning. */\n"
            "    attribute a : String;\n"
            "    doc /* A BRAND NEW MEMBER DOC. */\n"
            "    attribute b : Natural;\n"
            "  }"
        )
        definition = "The widget meaning."
        assert (
            ai.doc_text_observation(base, "part def Widget", definition)
            == ai.doc_text_observation(changed, "part def Widget", definition)
            == "normalized-exact"
        )

    def test_changing_member_doc_does_not_alter_class_parity(self):
        base = self._wrap(
            "item def Widget {\n"
            "    doc /* The widget meaning. */\n"
            "    attribute a : String;\n"
            "    doc /* old member doc. */\n"
            "    attribute b : Natural;\n"
            "  }"
        )
        changed = self._wrap(
            "item def Widget {\n"
            "    doc /* The widget meaning. */\n"
            "    attribute a : String;\n"
            "    doc /* member doc completely rewritten. */\n"
            "    attribute b : Natural;\n"
            "  }"
        )
        definition = "The widget meaning."
        assert (
            ai.doc_text_observation(base, "item def Widget", definition)
            == ai.doc_text_observation(changed, "item def Widget", definition)
            == "normalized-exact"
        )

    def test_missing_definition_doc_does_not_pass(self):
        file_text = self._wrap(
            "item def Widget {\n    attribute a : String;\n  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "item def Widget", "The widget meaning."
            )
            == "doc-absent"
        )
        assert ai.doc_text_observation(
            file_text, "item def Widget", "The widget meaning."
        ) in ai.REVIEW_REQUIRED_OBSERVATIONS

    def test_only_member_docs_present_is_doc_absent(self):
        """A class with attribute docs but no definition doc reports doc-absent
        — member docs cannot stand in for the definition (the pre-c1 state of
        the seven conformance classes)."""
        file_text = self._wrap(
            "item def Widget {\n"
            "    attribute a : String;\n"
            "    doc /* attribute a doc. */\n"
            "  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "item def Widget", "The widget meaning."
            )
            == "doc-absent"
        )

    def test_extra_semantic_text_in_definition_doc_fails(self):
        file_text = self._wrap(
            "part def Widget {\n"
            "    doc /* The widget meaning. It also implies acceptance. */\n"
            "    attribute a : String;\n"
            "  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "The widget meaning."
            )
            == "differs"
        )

    def test_substring_parity_remains_rejected(self):
        contained = self._wrap(
            "part def Widget {\n"
            "    doc /* The widget meaning. */\n"
            "    attribute a : String;\n"
            "  }"
        )
        containing = self._wrap(
            "part def Widget {\n"
            "    doc /* The widget meaning, in the approved style, always. */\n"
            "    attribute a : String;\n"
            "  }"
        )
        short = "The widget meaning."
        assert ai.doc_text_observation(contained, "part def Widget", short) == (
            "normalized-exact"
        )
        # doc contains definition (definition is a substring): rejected.
        assert (
            ai.doc_text_observation(containing, "part def Widget", short) == "differs"
        )
        # definition contains doc (doc is a substring): rejected.
        assert (
            ai.doc_text_observation(contained, "part def Widget", short + " always")
            == "differs"
        )

    def test_plain_comments_are_skipped_not_collected(self):
        """Presentation comments (/* */ without doc, //) before the definition
        doc are not model elements and must not join the owned text."""
        file_text = self._wrap(
            "part def Widget {\n"
            "    /* presentation comment. */\n"
            "    // line comment.\n"
            "    doc /* The widget meaning. */\n"
            "    attribute a : String;\n"
            "  }"
        )
        block, _ = ai.declaration_block(file_text, "part def Widget")
        docs = ai._leading_owned_doc_bodies(block)
        assert [d.strip() for d in docs] == ["The widget meaning."]

    def test_no_c1_definitions_hardcoded_in_python(self):
        """The parity machinery must not embed the eight definitions as
        Python constants; the comparison inputs come from the ontology YAML
        through KernelContract at test time."""
        source = (REPO_ROOT / "de4sdv/semantic/authority_inventory.py").read_text(
            encoding="utf-8"
        )
        for name in C1_IDENTITIES:
            definition = _definition(name)
            first_clause = " ".join(definition.split())[:40]
            assert first_clause not in source, name


# ---------------------------------------------------------------------------
# Machine-checked normalized-exact parity for the eight committed rows
# ---------------------------------------------------------------------------


class TestC1TextParity:
    def test_all_eight_normalized_exact_from_source(self):
        contract = ai.KernelContract.load(REPO_ROOT / ai.ONTOLOGY_PATH)
        for name in C1_IDENTITIES:
            spec = contract.classes[name]
            file_text = _file_text(name)
            observation = ai.doc_text_observation(
                file_text,
                str(spec["kernel"]["declaration"]),
                str(spec["definition"]),
            )
            assert observation == "normalized-exact", name

    def test_inventory_rows_carry_the_exact_observation(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["observed"]["doc_text_observation"] == "normalized-exact"
            # No manual equivalence value when exact parity is machine-checked.
            assert entry["reviewed"]["semantic_text_equivalence"] is None

    def test_equivalence_consistent_with_observation(self, inventory):
        for entry in inventory["entries"]:
            observation = entry["observed"].get("doc_text_observation")
            equivalence = entry["reviewed"]["semantic_text_equivalence"]
            if observation in ai.REVIEW_REQUIRED_OBSERVATIONS:
                assert equivalence == "review-required", entry["identity"]
            elif observation == "normalized-exact":
                # No manual equivalence when exact parity is machine-checked.
                assert equivalence is None, entry["identity"]

    def test_member_docs_of_c1_classes_unchanged_and_isolated(self):
        """Adding/changing a member doc in the real files cannot move the
        eight class observations: they are computed from the leading owned
        doc only. Re-derive each observation with member docs stripped."""
        for name in C1_IDENTITIES:
            spec = ai.KernelContract.load(REPO_ROOT / ai.ONTOLOGY_PATH).classes[name]
            declaration = str(spec["kernel"]["declaration"])
            file_text = _file_text(name)
            base = ai.doc_text_observation(file_text, declaration, str(spec["definition"]))
            # Perturb: append a synthetic member doc after the last attribute.
            block, _ = ai.declaration_block(file_text, declaration)
            perturbed = file_text.replace(
                block, block[:-1] + 'doc /* SYNTHETIC MEMBER DOC. */\n  }', 1
            ) if block.endswith("}") else file_text
            after = ai.doc_text_observation(
                perturbed, declaration, str(spec["definition"])
            )
            assert base == after == "normalized-exact", name


# ---------------------------------------------------------------------------
# Structural exact-fit facts per reviewed decision
# ---------------------------------------------------------------------------


class TestC1StructuralFit:
    def test_method_phase_enum_with_thirteen_literals(self):
        text = _file_text("MethodPhase")
        block, bodyless = ai.declaration_block(text, "enum def MethodPhase")
        assert not bodyless and block
        literals = [
            name
            for name in (
                "phase0_incrementFraming",
                "phase1_concernFraming",
                "phase2_operationalContext",
                "phase3_capabilityClassification",
                "phase4_needs",
                "phase5_requirements",
                "phase6_functionalArchitecture",
                "phase7_logicalArchitecture",
                "phase8_physicalRealization",
                "phase9_variabilityConfiguration",
                "phase10_vvEvidence",
                "phase11_publication",
                "phase12_baselineNextSlice",
            )
            if f"{name} {{" in block or f"{name}{{" in block
        ]
        assert len(literals) == 13, literals

    def test_method_contract_obligation_schema_fields(self):
        """Every frozen Section 7 schema field is carried by typed attributes.

        The frozen schema (docs/method-conformance/conformance-baseline.md
        Section 7) lists 12 semantic fields; the model materializes them as 14
        attribute declarations because population policy and cardinality each
        require two attributes. The earlier "15 fields" figure was wrong and is
        corrected here and in the reviewed decision (review R2).
        """
        text = _file_text("MethodContractObligation")
        block, _ = ai.declaration_block(text, "item def MethodContractObligation")
        declared = [
            line.strip()
            for line in block.splitlines()
            if line.strip().startswith("attribute ")
        ]
        assert len(declared) == 14, declared
        for field in (
            "obligationId",
            "phase : MethodPhase",
            "subjectSelector",
            "applicability",
            "minimumPopulation",
            "permittedEmpty",
            "predicate",
            "targetFilter",
            "cardinalityMinimum",
            "cardinalityMaximum",
            "required : Boolean",
            "evaluationSource : EvaluationSourceKind",
            "attestationPolicyRef",
            "claimBoundary",
        ):
            assert f"attribute {field}" in block, field

    def test_method_contract_obligation_covers_frozen_schema(self):
        """Cross-check the frozen Section 7 field list against the model: all
        12 schema fields are represented and no field is absent."""
        baseline = (
            REPO_ROOT / "docs/method-conformance/conformance-baseline.md"
        ).read_text(encoding="utf-8")
        start = baseline.index("## 7. Minimal typed method-contract schema")
        end = baseline.index("## 8.", start)
        section = baseline[start:end]
        schema_fields = re.findall(r"^\|\s*`([^`]+)`\s*\|", section, re.MULTILINE)
        assert len(schema_fields) == 12, schema_fields
        text = _file_text("MethodContractObligation")
        block, _ = ai.declaration_block(text, "item def MethodContractObligation")
        coverage = {
            "obligation_id": ["obligationId"],
            "phase": ["phase"],
            "subject_selector": ["subjectSelector"],
            "applicability": ["applicability"],
            "population_policy": ["minimumPopulation", "permittedEmpty"],
            "predicate": ["predicate"],
            "target_filters": ["targetFilter"],
            "cardinality": ["cardinalityMinimum", "cardinalityMaximum"],
            "required": ["required"],
            "evaluation_source": ["evaluationSource"],
            "attestation_policy_ref": ["attestationPolicyRef"],
            "claim_boundary": ["claimBoundary"],
        }
        assert set(coverage) == set(schema_fields)
        for field, attributes in coverage.items():
            for attribute in attributes:
                assert f"attribute {attribute}" in block, (field, attribute)
        assert sum(len(attrs) for attrs in coverage.values()) == 14

    def test_evaluation_source_kind_three_literals(self):
        text = _file_text("EvaluationSourceKind")
        block, _ = ai.declaration_block(text, "enum def EvaluationSourceKind")
        for literal in (
            "pinnedModelRecord",
            "pinnedRepositoryArtifact",
            "liveDeliveryAdapter",
        ):
            assert f"{literal} {{" in block, literal

    def test_method_evaluation_scope_fields(self):
        text = _file_text("MethodEvaluationScope")
        block, _ = ai.declaration_block(text, "part def MethodEvaluationScope")
        assert "attribute incrementId : String" in block
        assert "attribute subjectType : String" in block

    def test_evaluation_scope_membership_fields(self):
        text = _file_text("EvaluationScopeMembership")
        block, _ = ai.declaration_block(text, "item def EvaluationScopeMembership")
        assert "attribute scopeId : String" in block
        assert "attribute subjectId : String" in block
        assert "attribute contributes : Boolean" in block

    def test_contribution_set_distinct_from_evaluation_scope_in_pilot(self):
        """The pilot memberships instantiate contributes=false for reused
        usages — the contribution/scope separation is demonstrated, not just
        declared."""
        pilot = (
            REPO_ROOT
            / "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml"
        ).read_text(encoding="utf-8")
        assert ':>> contributes = false' in pilot
        assert pilot.count(':>> contributes = false') >= 6

    def test_tested_scope_declaration_fields(self):
        text = _file_text("TestedScopeDeclaration")
        block, _ = ai.declaration_block(text, "item def TestedScopeDeclaration")
        assert "attribute executionHead : String" in block
        assert "attribute profileIdentities : String" in block

    def test_retained_execution_record_reference_is_reference_only(self):
        text = _file_text("RetainedExecutionRecordReference")
        block, _ = ai.declaration_block(
            text, "item def RetainedExecutionRecordReference"
        )
        for field in ("recordId", "artifactPath", "sha256", "runId"):
            assert f"attribute {field} : String" in block, field
        # External boundary: no byte-ownership field exists.
        for forbidden in ("bytes", "content", "blob", "payload"):
            assert f"attribute {forbidden}" not in block.lower(), forbidden

    def test_acceptance_attestation_reference_cannot_imply_approval(self):
        text = _file_text("AcceptanceAttestationReference")
        block, _ = ai.declaration_block(
            text, "item def AcceptanceAttestationReference"
        )
        assert "attribute policyRef : String" in block
        assert "attribute decisionRegistryPath : String" in block
        # Reference-only: the declared attributes are reference fields; no
        # decision-outcome/approval field exists (attribute declaration lines
        # only — doc text mentioning the registry is not a field).
        declared = [
            line.strip().split("(")[0]
            for line in block.splitlines()
            if line.strip().startswith("attribute ")
        ]
        assert sorted(declared) == [
            "attribute decisionRegistryPath : String;",
            "attribute policyRef : String;",
        ]


# ---------------------------------------------------------------------------
# Runtime invariants untouched
# ---------------------------------------------------------------------------


class TestRuntimeUnchanged:
    def test_traversal_and_projection_sources_do_not_reference_c1(self):
        """No runtime module consumes the c1 classes (runtime behavior is
        unchanged by c1; the YAML remains the semantic authority)."""
        for module in (
            "de4sdv/semantic/traversal.py",
            "de4sdv/semantic/projection.py",
        ):
            source = (REPO_ROOT / module).read_text(encoding="utf-8")
            for name in C1_IDENTITIES:
                assert name not in source, (module, name)

    def test_inventory_generator_is_runtime_inert(self):
        """The runtime does not read the generated inventory."""
        source = (REPO_ROOT / "de4sdv/semantic/authority_inventory.py").read_text(
            encoding="utf-8"
        )
        assert "runtime" in source  # sanity: file readable
        # The runtime kernel contract loader does not read the generated JSON.
        kernel = (REPO_ROOT / "de4sdv/semantic/kernel_contract.py").read_text(
            encoding="utf-8"
        )
        assert "semantic-authority-inventory.json" not in kernel

    def test_no_new_traversal_strategy(self, inventory):
        """The runtime strategy registry is unchanged by c1 (no runtime
        change): same eight strategies with the same associations."""
        strategies = {
            row["strategy"]: row
            for row in inventory["runtime_strategy_registry"]["strategies"]
        }
        assert set(strategies) == {
            "allocation",
            "dependency",
            "derivation-connection",
            "external",
            "property-reference",
            "subject-membership",
            "verification",
            "verification-membership",
        }
        assert strategies["verification"]["association"] == "unassociated-capability"
        assert (
            strategies["property-reference"]["association"]
            == "unassociated-capability"
        )
        for associated in (
            "allocation",
            "dependency",
            "derivation-connection",
            "external",
            "subject-membership",
            "verification-membership",
        ):
            assert strategies[associated]["association"] == "ontology-mapping"
