"""O1 c1 — bounded method-conformance class parity batch (PR #249).

Tests the c1 parity claim for exactly eight identities:

1.  exactly the eight named identities comprise c1 (no ninth entry);
2.  successful rows: evidence_state = parity-reviewed, authority_current =
    legacy-yaml preserved, authority_target = model-authoritative, no closure
    evidence, no supported-promotion, no conditional target;
3.  definition-level documentation is extracted independently from member
    (attribute / enum-literal) documentation per the SysML v2 spec ownership
    rule (a doc comment is owned by the element whose body it sits in);
4.  strict normalized-exact parity is machine-checked for all eight;
5.  structural exact-fit facts: declaration kinds, required typed members,
    required enum literals, and the external-reference / no-approval /
    exclusions-carried-elsewhere boundaries that justified each decision;
6.  no runtime/query/K/projection semantics changed: the inventory generator
    is runtime-inert and the c1 rows carry no Semantic Projection rows.

Adversarial cases prove the parity machinery rejects member-doc confusion,
missing docs, extra semantic text, and substring containment.
"""

from __future__ import annotations

import json
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

    def test_no_ninth_entry_promoted(self, inventory):
        parity_rows = [
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "parity-reviewed"
        ]
        assert sorted(parity_rows) == sorted(C1_IDENTITIES)

    def test_authority_current_remains_legacy_yaml(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["authority_current"] == "legacy-yaml"

    def test_authority_target_is_model_authoritative(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["authority_target"] == "model-authoritative"

    def test_successful_rows_are_parity_reviewed(self, inventory):
        for entry in _entries(inventory, C1_IDENTITIES).values():
            assert entry["reviewed"]["evidence_state"] == "parity-reviewed"

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

    def test_c2_to_c5_entries_unchanged(self, inventory):
        """Spot-check the other batch stages stay on their own stages."""
        stages = {
            entry["identity"]: entry["reviewed"]["stage"]
            for entry in inventory["entries"]
        }
        assert stages["VerificationCase"] == "c2"
        assert stages["hasSubject"] == "c3"
        assert stages["derivesNeedFromConcern"] == "c4"
        assert stages["realizedBy"] == "c5"

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
        text = _file_text("MethodContractObligation")
        block, _ = ai.declaration_block(text, "item def MethodContractObligation")
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

    def test_scope_exclusions_boundary_recorded_not_model_resident(self):
        """The exclusions half of the MethodEvaluationScope meaning is carried
        by the runtime typed input, not by a model field — the reviewed
        boundary must be recorded in the decision and the model must NOT
        carry an exclusions attribute (no overclaim)."""
        decisions = yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))
        row = decisions["entries"]["MethodEvaluationScope"]
        assert "exclusions" in row["exact_fit_decision"]
        text = _file_text("MethodEvaluationScope")
        block, _ = ai.declaration_block(text, "part def MethodEvaluationScope")
        assert "attribute exclusions" not in block

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
