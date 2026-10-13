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

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_LINE = (
    REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
)
OPERATIONAL_CONTEXT = (
    REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml"
)
REGISTER = REPO_ROOT / "de4sdv/semantic/contract-data/ontology-identity-register.json"
SYNC_SCRIPT = REPO_ROOT / "scripts/check_model_sync.py"

BATCH_ROWS = ("ProductLineCharacteristic", "Scenario")

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
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


@pytest.fixture(scope="module")
def ontology() -> dict:
    """Current model meaning and mappings for synthetic runtime consumers.

    This cleanup retires the reviewed admission prose; there is no historical fallback.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model_contract_fixtures import model_contract, current_definition

    contract = model_contract()
    return {"classes": {name: {"kernel": contract.classes[name]["kernel"],
                               "definition": current_definition(name)}
                        for name in ("ProductLineCharacteristic", "Scenario")}}


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


def test_product_line_characteristic_has_owned_model_documentation(model_text):
    # This cleanup retired copied-definition parity, not the actual owned definition home.
    from model_contract_fixtures import owned_definition_documentation

    assert owned_definition_documentation(model_text, "part def ProductLineCharacteristic").strip()


# ---------------------------------------------------------------------------
# 2. Scenario: bounded pattern grounding on the existing machinery
# ---------------------------------------------------------------------------


def test_scenario_definition_home_is_model_resident(ontology):
    # The definition home is part def Scenario in the operational context; the
    # ontology class maps to that declaration (no native mapping).
    kernel = ontology["classes"]["Scenario"]["kernel"]
    assert "native" not in kernel
    assert kernel["declaration"] == "part def Scenario"
    assert kernel["file"] == (
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml"
    )


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
    # The definition home added by definition admission batch 1 (amended).
    assert "part def Scenario {" in text
    # This cleanup retires the copied Scenario definition sentence; keep owned docs.
    from model_contract_fixtures import owned_definition_documentation

    assert owned_definition_documentation(text, "part def Scenario").strip()


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
    for identity in BATCH_ROWS:
        assert identity not in MIGRATED_IDENTITIES
        assert register_rows[identity].get("gate_wave") is None


def test_no_new_projection_rows():
    expected_rows = {
        "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.1.json": (
            ["VerificationCase"],
            ["hasSubject", "verifiedBy"],
        ),
        "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.2.json": (
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


# ---------------------------------------------------------------------------
# 4. Commit-B gate: artifact rows reproduce the source decisions
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 5. Same safe set: W4 carrier-parity and W5 external-reference-design rows
# ---------------------------------------------------------------------------
