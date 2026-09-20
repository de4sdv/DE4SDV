"""O4 accelerated safe-set 2 — W2 batch 7 per-row precision matrix.

Two retained, ungated W2 ``MODEL_AUTHORITY_PARITY`` rows are treated by this
safe set:

* ``ProductLineCharacteristic`` — definitions parity closed normalized-exact:
  the model doc is aligned to the reviewed definition text verbatim (equality
  after cosmetic normalization only); declaration, name and
  classification-root position are unchanged.
* ``Scenario`` — bounded pattern grounding: the existing scenario-identity
  enum + operational-context part pattern is reviewed as the model-side
  representation and is machine-bound to the evaluator by
  ``scripts/check_model_sync.py`` sync point 1. The row claims no native
  semantics (``authority_current`` stays ``legacy-yaml``) and no
  reviewed-equivalent record — there is no model-side declaration to ground
  definition-level text parity, and the reviewed-equivalent state is
  representable only for a differing doc observation
  (``REVIEWED_EQUIVALENT_OBSERVATIONS``).

The inventory artifact is a shared binding owned by the parent; the
artifact-vs-source consistency test at the bottom is the Commit-B gate and is
expected red until the inventory is regenerated from these sources.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_LINE = (
    REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
)
OPERATIONAL_CONTEXT = (
    REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml"
)
ONTOLOGY = REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
INVENTORY = REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS = REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
REGISTER = REPO_ROOT / "docs/method-conformance/o4/o4-execution-register.json"
SCOPE = REPO_ROOT / "docs/method-conformance/o3/o3-equivalence-scope.json"
SYNC_SCRIPT = REPO_ROOT / "scripts/check_model_sync.py"

BATCH_ROWS = ("ProductLineCharacteristic", "Scenario")
DEFINITIONS_PARITY_STAGE = "o4-w2 batch 7 (definitions parity)"
PATTERN_GROUNDING_STAGE = "o4-w2 batch 7 (bounded pattern grounding)"
OBLIGATION = "O2 admission / generated Semantic Projection from the reviewed model representation"
PATTERN_OBLIGATION = (
    "O2 admission / generated Semantic Projection from the reviewed pattern representation"
)

#: Scenario identity enums present in the governed model (representation only).
SCENARIO_IDENTITY_ENUMS = {
    "textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml": (
        "MiddlewareScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml": (
        "OverrideScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_non_activation_verification.sysml": (
        "NonActivationScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_degraded_input_verification.sysml": (
        "DegradedInputScenarioIdentity"
    ),
    "textual-notation-of-model/packages/features/aebs/aebs_regulatory_criterion_verification.sysml": (
        "RegulatoryCriterionScenarioIdentity"
    ),
}

#: Sync point 1 of ``scripts/check_model_sync.py`` — the existing machinery
#: binding the AEB scenario-identity enums to the evaluator enums.
SYNC_POINT1 = {
    ("aebs_override_verification.sysml", "override_matrix.py", "OverrideScenario"),
    ("aebs_non_activation_verification.sysml", "non_activation_matrix.py", "NonActivationScenario"),
    ("aebs_degraded_input_verification.sysml", "degraded_input_matrix.py", "DegradedInputScenario"),
}


@pytest.fixture(scope="module")
def model_text() -> str:
    return PRODUCT_LINE.read_text()


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY.read_text())


@pytest.fixture(scope="module")
def decisions() -> dict:
    return yaml.safe_load(DECISIONS.read_text())["entries"]


@pytest.fixture(scope="module")
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


@pytest.fixture(scope="module")
def ontology() -> dict:
    return yaml.safe_load(ONTOLOGY.read_text())


def _entry(inventory: dict, identity: str) -> dict:
    return next(e for e in inventory["entries"] if e["identity"] == identity)


def _sync_module():
    spec = importlib.util.spec_from_file_location("check_model_sync", SYNC_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. Batch scope, stages, per-row treatment state
# ---------------------------------------------------------------------------


def test_exact_two_row_scope(register_rows):
    for identity in BATCH_ROWS:
        row = register_rows[identity]
        assert row["membership"] == "o4-target"
        assert row["base_wave"] == "W2"
        assert row.get("gate_wave") is None
        assert row.get("migration_class") == "MODEL_AUTHORITY_PARITY"
        assert row.get("blocker") is None
    assert len(BATCH_ROWS) == 2


def test_exactly_the_batch_rows_carry_the_batch_stages(decisions):
    staged = {
        name: row.get("stage")
        for name, row in decisions.items()
        if row.get("stage") in (DEFINITIONS_PARITY_STAGE, PATTERN_GROUNDING_STAGE)
    }
    assert staged == {
        "ProductLineCharacteristic": DEFINITIONS_PARITY_STAGE,
        "Scenario": PATTERN_GROUNDING_STAGE,
    }


def test_product_line_characteristic_definition_parity_is_machine_checked(
    model_text, ontology
):
    definition = ontology["classes"]["ProductLineCharacteristic"]["definition"]
    assert (
        ai.doc_text_observation(model_text, "part def ProductLineCharacteristic", definition)
        == "normalized-exact"
    )
    # The old unaligned wording is gone: parity is carried, not approximated.
    assert "classification concept for common capabilities" not in model_text


def test_product_line_characteristic_row_state(decisions):
    row = decisions["ProductLineCharacteristic"]
    assert row["authority_current"] == "legacy-yaml"
    assert row["authority_target"] == "model-authoritative"
    assert row["evidence_state"] == "repository-evidenced"
    assert row["adoption_status"] == "not-applicable"
    assert row["conditional_target"] is False
    assert row["transition_gate"] is None
    assert row["closure_evidence_ref"] is None
    assert row["semantic_text_equivalence"] is None
    assert row["stage"] == DEFINITIONS_PARITY_STAGE
    assert "batch-7 parity-reviewed" in row["note"]
    assert row["exact_fit_decision"].startswith(
        "exact fit: definition-level parity complete (o4-w2 batch 7)"
    )
    assert row["required_evidence"] == [OBLIGATION]


def test_product_line_characteristic_inventory_mapping_stable(inventory):
    observed = _entry(inventory, "ProductLineCharacteristic")["observed"]
    assert observed["declaration"] == "part def ProductLineCharacteristic"
    assert observed["file"] == (
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
    )
    assert observed["yaml_path"] == "classes:ProductLineCharacteristic"


def test_scenario_row_stays_bounded_no_native_claim(decisions):
    row = decisions["Scenario"]
    assert row["authority_current"] == "legacy-yaml"
    assert row["authority_target"] == "model-authoritative"
    assert row["evidence_state"] == "repository-evidenced"
    assert row["confidence"] == "medium"
    assert row["unknowns"] == []
    assert row["adoption_status"] == "not-applicable"
    assert row["conditional_target"] is False
    assert row["transition_gate"] is None
    assert row["closure_evidence_ref"] is None
    assert row["semantic_text_equivalence"] is None
    assert row["stage"] == PATTERN_GROUNDING_STAGE
    assert "RECLASSIFIED from native-sysml" in row["note"]
    assert "Bounded pattern grounding reviewed (o4-w2 batch 7)" in row["note"]
    assert row["exact_fit_decision"].startswith("not exact-fit native")
    assert "Bounded pattern grounding complete (o4-w2 batch 7)" in row["exact_fit_decision"]


def test_scenario_required_evidence_is_forward_only(decisions):
    evidence = decisions["Scenario"]["required_evidence"]
    assert evidence, "active evidence state requires non-empty required_evidence"
    assert any("O2 admission" in item for item in evidence)
    assert any("definition-level parity stays open" in item for item in evidence)
    assert all("O3" not in item for item in evidence)


# ---------------------------------------------------------------------------
# 2. Scenario: bounded pattern grounding on the existing machinery
# ---------------------------------------------------------------------------


def test_scenario_has_no_model_side_declaration(inventory, ontology):
    observed = _entry(inventory, "Scenario")["observed"]
    assert observed["grounding_kind"] == "native"
    assert "file" not in observed and "declaration" not in observed
    assert "doc_text_observation" not in observed
    assert observed["ref"]
    kernel = ontology["classes"]["Scenario"]["kernel"]
    assert "native" in kernel and "declaration" not in kernel
    # Reviewed-equivalent is representable only for a differing doc
    # observation; with no model-side declaration this row can never claim it.
    assert ai.REVIEWED_EQUIVALENT_OBSERVATIONS == frozenset({"differs"})


def test_scenario_identity_enums_present_in_model():
    for path, enum_name in SCENARIO_IDENTITY_ENUMS.items():
        text = (REPO_ROOT / path).read_text()
        assert f"enum def {enum_name} {{" in text, (path, enum_name)


def test_sync_point1_binds_the_aeb_scenario_enums():
    module = _sync_module()
    assert set(module.SCENARIO_IDENTITY_MAP) == SYNC_POINT1
    errors: list[str] = []
    module.check_scenario_identities(errors)
    assert errors == []


def test_scenario_operational_context_pattern_anchored():
    text = OPERATIONAL_CONTEXT.read_text()
    assert "part def OperationalEntity {" in text
    assert "part def SubjectVehicle :> OperationalEntity {" in text


# ---------------------------------------------------------------------------
# 3. Boundaries: names, classification root, native variation, prior batches
# ---------------------------------------------------------------------------


def test_product_line_characteristic_is_still_the_classification_root(model_text):
    block, bodyless = ai.declaration_block(model_text, "part def ProductLineCharacteristic")
    assert not bodyless
    assert ":>" not in block.split("doc /*")[0]
    for branch in (
        "part def CommonProductLineCapability :> ProductLineCharacteristic {",
        "part def ProductLineFeatureCandidate :> ProductLineCharacteristic {",
        "part def DeferredProductLineScope :> ProductLineCharacteristic {",
        "part def ProductLineVariantChoice :> ProductLineCharacteristic {",
    ):
        assert branch in model_text, branch
    # The native variation mechanism remains present and untouched.
    assert "variation part def DeferredProductLineVariation {" in model_text
    assert "variant part deferredChoice;" in model_text


def test_no_runtime_or_o3_promotion(register_rows):
    scope = json.loads(SCOPE.read_text())
    identities = {row["identity"] for row in scope["identities"]}
    assert identities == set(MIGRATED_IDENTITIES)
    assert len(identities) == 13
    for identity in BATCH_ROWS:
        assert identity not in identities
        assert register_rows[identity].get("gate_wave") is None


def test_no_new_projection_rows():
    expected_rows = {
        "docs/method-conformance/o2/semantic-projection-v1.1.json": (
            ["VerificationCase"],
            ["hasSubject", "verifiedBy"],
        ),
        "docs/method-conformance/o2/semantic-projection-v1.2.json": (
            [],
            ["derivesRequirementFromNeed", "derivedRequirementsOfNeed", "hasRelevantArchitecture"],
        ),
    }
    for artifact, (concepts, predicates) in expected_rows.items():
        data = json.loads((REPO_ROOT / artifact).read_text())
        assert [row["identity"] for row in data.get("concepts", [])] == concepts, artifact
        assert [row["identity"] for row in data.get("predicates", [])] == predicates, artifact
        row_ids = {row["identity"] for row in data.get("concepts", []) + data.get("predicates", [])}
        assert not (row_ids & set(BATCH_ROWS)), artifact


def test_prior_batch_rows_unchanged(decisions):
    expected_stage = {
        "EngineeringIncrement": "o4-w2 pilot 1 (definitions parity)",
        "FeatureIncrement": "o4-w2 pilot 1 (definitions parity)",
        "NeedsRequirementsIncrement": "o4-w2 pilot 1 (definitions parity)",
        "IncrementEngineeringQuestion": "o4-w2 pilot 2 (definitions parity)",
        "IncrementLifecycleDecision": "o4-w2 pilot 2 (definitions parity)",
        "SystemLayer": "o4-w2 pilot 2 (definitions parity)",
        "ProblemStatement": "o4-w2 pilot 2 (definitions parity)",
        "Assumption": "o4-w2 pilot 2 (definitions parity)",
        "Gap": "o4-w2 pilot 2 (definitions parity)",
        "SignalMappingDisposition": "o4-w2 batch 3 (definitions parity)",
        "LogicalToSoftwareSignalMappingRecord": "o4-w2 batch 3 (definitions parity)",
        "SystemToSoftwareSignalMappingCandidate": "o4-w2 batch 3 (definitions parity)",
        "Need": "o4-w2 batch 4 (definitions parity)",
        "Requirement": "o4-w2 batch 4 (definitions parity)",
        "RegulatoryConstraint": "o4-w2 batch 4 (definitions parity)",
        "MissingRealizationRecord": "o4-w2 batch 5 (definitions parity)",
        "BlockedRealizationBranchRecord": "o4-w2 batch 5 (definitions parity)",
        "ProductLine": "o4-w2 batch 6 (definitions parity)",
        "MemberProduct": "o4-w2 batch 6 (definitions parity)",
        "DeferredProductLineScope": "o4-w2 batch 6 (definitions parity)",
        "IncrementSize": "o4-w3 batch 1 (definitions parity)",
        "ArchitectureDecisionRecord": "o4-w5 batch 1 (definitions parity)",
        "Baseline": "o4-w5 batch 1 (definitions parity)",
    }
    for identity, stage in expected_stage.items():
        assert decisions[identity]["stage"] == stage, identity
        assert decisions[identity]["authority_current"] == "legacy-yaml", identity
    # Untreated W2 rows keep their pre-parity stage.
    for identity in ("Feature", "CommonCapability"):
        assert decisions[identity]["stage"] == "batched-parity (post-0a/0b)", identity


# ---------------------------------------------------------------------------
# 4. Commit-B gate: artifact rows reproduce the source decisions
# ---------------------------------------------------------------------------


def test_inventory_artifact_reproduces_source_rows_commit_b_gate(inventory, decisions):
    """Expected RED until the parent regenerates the inventory (Commit B).

    The generated reviewed row must reproduce the decisions row exactly
    (plus the joined ``runtime_consumption`` field); the generated observed
    row must carry the source-recomputed observation. The gate is the
    two-commit binding working, not a defect to fix by regenerating early.
    """
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        expected = dict(decisions[identity])
        expected["runtime_consumption"] = entry["reviewed"].get("runtime_consumption")
        assert entry["reviewed"] == expected, identity
    assert (
        _entry(inventory, "ProductLineCharacteristic")["observed"]["doc_text_observation"]
        == "normalized-exact"
    )


# ---------------------------------------------------------------------------
# 5. Same safe set: W4 carrier-parity and W5 external-reference-design rows
# ---------------------------------------------------------------------------

W4_CARRIER_STAGE = "o4-w4 batch 1 (carrier definitions parity)"
W5_REFERENCE_STAGE = "o4-w5 batch 2 (external-reference design)"
W4_ROWS = (
    "recordsGap",
    "recordsAssumption",
    "addressesConcern",
    "selectedViewpoint",
    "producesView",
)
W5_ROWS = ("EvidenceArtifact", "hasEvidence", "capturedInBaseline")


def test_w4_and_w5_rows_carry_the_safe_set_stages(decisions):
    staged_w4 = {
        name for name, row in decisions.items() if row.get("stage") == W4_CARRIER_STAGE
    }
    staged_w5 = {
        name for name, row in decisions.items() if row.get("stage") == W5_REFERENCE_STAGE
    }
    assert staged_w4 == set(W4_ROWS)
    assert staged_w5 == set(W5_ROWS)


def test_w4_rows_record_carrier_parity_with_forward_closure_evidence(decisions):
    for identity in W4_ROWS:
        row = decisions[identity]
        assert row["authority_current"] == "legacy-yaml", identity
        assert row["authority_target"] == "model-authoritative", identity
        assert "o4-w4 batch 1" in row["exact_fit_decision"], identity
        assert any(
            "O4 closure precondition" in item for item in row["required_evidence"]
        ), identity
        assert any("no traversal" in item for item in row["required_evidence"]), identity


def test_w5_rows_record_the_design_with_forward_closure_evidence(decisions):
    for identity in W5_ROWS:
        row = decisions[identity]
        assert "o4-w5 batch-2" in row["note"], identity
        assert any(
            "O4 closure precondition" in item for item in row["required_evidence"]
        ), identity
    # The design resolves the previous unknown; the boundary row keeps its
    # external-current authority and never claims approval.
    assert decisions["EvidenceArtifact"]["unknowns"] == []
    assert decisions["hasEvidence"]["authority_current"] == "external-reference"
    assert decisions["capturedInBaseline"]["authority_current"] == "legacy-yaml"
    assert (
        "not silently resolved" in decisions["capturedInBaseline"]["note"]
    ), "the recorded classification tension must stay documented"


def test_has_stakeholder_stays_excluded_and_untreated(decisions):
    row = decisions["hasStakeholder"]
    assert row["stage"] == "batched-parity (post-0a/0b)"
    assert row["authority_current"] == "legacy-yaml"
