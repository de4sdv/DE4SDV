"""Historical definition records and current model boundaries.

This cleanup retires current-documentation equality with copied or frozen definitions.
Live checks retain owned nonempty documentation, structure and claim boundaries.
Inventory/decision parity fields below describe frozen historical evidence only;
they are not recomputed from, or imposed on, current model wording.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from model_contract_fixtures import admission_row, owned_definition_documentation
from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES

REPO = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS_PATH = REPO / "docs/method-conformance/o1/authority-review-decisions.yaml"
REGISTER_PATH = REPO / "docs/method-conformance/o4/o4-execution-register.json"
SCOPE_PATH = REPO / "docs/method-conformance/o3/o3-equivalence-scope.json"
MODEL_PATH = (
    REPO / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)

PILOT_ROWS: dict[str, str] = {
    "EngineeringIncrement": "part def EngineeringIncrement",
    "FeatureIncrement": "part def FeatureIncrement",
    "NeedsRequirementsIncrement": "part def NeedsRequirementsIncrement",
}


#: The remaining forward obligation under O4 for a parity-closed W2 row: O2
#: admission / generated projection from the reviewed model representation.
#: O3 is frozen throughout O4 and these rows must never carry an O3
#: transition requirement.
# later-batch convention (definition admission batch 1): the O2-admission
# obligation of these rows is discharged by the generated definition
# projection/profile pair; the remaining forward obligation is the runtime
# one (support stays vocabulary-only).
REMAINING_OBLIGATION = [
    "runtime-queryable support (post-migration) requires exact-revision traversal evidence; support remains vocabulary-only",
]
# later-batch convention: re-stated at the current treatment stage.
TREATED_STAGE = "o4 definition admission batch 1 (projection + profile)"


def _inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _decisions() -> dict:
    return yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))["entries"]


def _entries(inventory: dict, identities=None) -> dict:
    entries = {entry["identity"]: entry for entry in inventory["entries"]}
    if identities is None:
        return entries
    return {identity: entries[identity] for identity in identities}


def test_live_model_definitions_have_owned_nonempty_documentation() -> None:
    # This cleanup retired live normalized-exact prose parity; keep the real owned homes.
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    for identity, declaration in PILOT_ROWS.items():
        assert owned_definition_documentation(file_text, declaration).strip(), identity


def test_inventory_records_the_closed_parity() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        observed = entry["observed"]
        reviewed = entry["reviewed"]
        assert observed["doc_text_observation"] == "normalized-exact", identity
        assert reviewed["semantic_text_equivalence"] is None, identity
        assert reviewed["required_evidence"] == REMAINING_OBLIGATION, identity
        assert reviewed["stage"] == TREATED_STAGE, identity
        assert "parity-reviewed" in reviewed["note"], identity
        assert "parity complete (o4-w2 pilot 1)" in reviewed["exact_fit_decision"], identity
        assert "no authority cutover implied" in reviewed["exact_fit_decision"], identity
        # The note states parity is closed but does not claim retirement:
        # authority_current stays legacy-yaml until O2 admission completes.
        assert "authority_current remains legacy-yaml until" in reviewed["note"], identity
        assert "under O4" in reviewed["note"], identity
        assert "retires as semantic authority" not in reviewed["note"], identity


def test_decisions_source_records_the_closed_parity() -> None:
    entries = _decisions()
    for identity in PILOT_ROWS:
        reviewed = entries[identity]
        assert reviewed["stage"] == TREATED_STAGE, identity
        assert reviewed["semantic_text_equivalence"] is None, identity
        assert reviewed["required_evidence"] == REMAINING_OBLIGATION, identity


def test_no_o3_transition_requirement_or_membership() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        evidence = entry["reviewed"]["required_evidence"]
        assert not any("O3" in item for item in evidence), identity

    # O3 stays frozen at exactly the thirteen migrated identities, and no
    # pilot row may be added to it.
    assert len(MIGRATED_IDENTITIES) == 13
    assert set(PILOT_ROWS).isdisjoint(set(MIGRATED_IDENTITIES))

    # No O3 scope/semantic membership expansion: the equivalence scope keeps
    # exactly its frozen thirteen identities, none of them a pilot row.
    scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    scope_identities = {entry["identity"] for entry in scope["identities"]}
    assert len(scope_identities) == 13
    assert set(PILOT_ROWS).isdisjoint(scope_identities)


def test_no_support_promotion_and_no_traversal_change() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        reviewed = entry["reviewed"]
        assert reviewed["authority_current"] == "legacy-yaml", identity
        assert reviewed["authority_target"] == "model-authoritative", identity
        assert reviewed["evidence_state"] == "repository-evidenced", identity
        assert reviewed["conditional_target"] is False, identity
        assert reviewed["closure_evidence_ref"] is None, identity
        assert reviewed["adoption_status"] == "not-applicable", identity
        assert reviewed["disposition"] == "move-meaning-into-model", identity


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


def test_feature_increment_note_preserves_ple_qualification() -> None:
    inventory = _inventory()
    reviewed = _entries(inventory, PILOT_ROWS)["FeatureIncrement"]["reviewed"]
    note = reviewed["note"]
    assert "variation/variant semantics remain the reference" in note
    assert "does not decide configurator authority or decision-9" in note


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


def test_unrelated_reviewed_rows_are_unchanged() -> None:
    inventory = _inventory()
    entries = _entries(inventory)
    # The W1-corrected demoted row keeps its bounded-vocabulary record; its
    # W3 parity requirement was closed by O4 accelerated safe-set 1, so the
    # residual is the no-promotion boundary (updated when that batch landed).
    increment_size = entries["IncrementSize"]["reviewed"]
    assert increment_size["disposition"] == "keep-as-is"
    assert increment_size["required_evidence"] == [
        "none beyond bounded vocabulary: model-resident guidance labels; never promoted to semantic authority"
    ]
    # c1's incomplete row still carries its structural gap, and c1's closed
    # rows keep their recorded outcomes.
    assert entries["MethodEvaluationScope"]["reviewed"]["evidence_state"] == (
        "repository-evidenced"
    )
    assert entries["MethodPhase"]["observed"]["doc_text_observation"] == (
        "normalized-exact"
    )
    assert entries["MethodContractObligation"]["reviewed"][
        "semantic_text_equivalence"
    ] == "reviewed-equivalent"
    # The K row keeps its review-required state.
    assert entries["DerivesFromNeed"]["reviewed"]["semantic_text_equivalence"] == (
        "review-required"
    )
