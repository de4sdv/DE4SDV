"""Historical definition records and current model boundaries.

This cleanup retires current-documentation equality with copied or frozen definitions.
Live checks retain owned nonempty documentation, structure and claim boundaries.
Inventory/decision parity fields below describe frozen historical evidence only;
they are not recomputed from, or imposed on, current model wording.
"""

from __future__ import annotations

import json
from pathlib import Path


from model_contract_fixtures import admission_row, owned_definition_documentation
from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES

REPO = Path(__file__).resolve().parents[1]
REGISTER_PATH = REPO / "docs/method-conformance/o4/o4-execution-register.json"
MODEL_PATH = (
    REPO / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)

PILOT_ROWS: dict[str, str] = {
    "EngineeringIncrement": "part def EngineeringIncrement",
    "FeatureIncrement": "part def FeatureIncrement",
    "NeedsRequirementsIncrement": "part def NeedsRequirementsIncrement",
}


def test_live_model_definitions_have_owned_nonempty_documentation() -> None:
    # This cleanup retired live normalized-exact prose parity; keep the real owned homes.
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    for identity, declaration in PILOT_ROWS.items():
        assert owned_definition_documentation(file_text, declaration).strip(), identity


def test_register_rows_stay_ungated_w2_parity_rows() -> None:
    register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in PILOT_ROWS:
        row = rows[identity]
        assert row["base_wave"] == "W2", identity
        assert row["gate_wave"] is None, identity
        assert row["migration_class"] == "MODEL_AUTHORITY_PARITY", identity
        assert row["final_disposition"] == "KEEP_DE4SDV_APPLICATION_SEMANTIC", identity
        assert (
            row["required_runtime_or_consumer_change"]["traversal_required"] is False
        ), identity


def test_register_retirement_still_requires_o2_admission() -> None:
    register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in PILOT_ROWS:
        condition = rows[identity]["retirement_condition"]
        assert "O2 admission" in condition, identity
        assert "O3" not in condition, identity


def test_admission_manifest_has_locators_not_copied_definition_oracles() -> None:
    # This cleanup retired the unchanged copied-definition subject, not admission scope.
    for identity, declaration in PILOT_ROWS.items():
        row = admission_row(identity)
        assert row["declaration"] == {
            "file": MODEL_PATH.relative_to(REPO).as_posix(),
            "declaration": declaration,
        }, identity
        assert not {
            "reviewed_definition", "expected_documentation_observation",
            "semantic_text_equivalence",
        } & set(row), identity
