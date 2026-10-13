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
MODEL_PATH = (
    REPO / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)

#: identity -> model declaration (the doc-text observation target).
PILOT_ROWS: dict[str, str] = {
    "IncrementEngineeringQuestion": "part def IncrementEngineeringQuestion",
    "IncrementLifecycleDecision": "part def IncrementLifecycleDecision",
    "SystemLayer": "part def SystemLayer",
    "ProblemStatement": "requirement def ProblemStatement",
    "Assumption": "part def IncrementAssumption",
    "Gap": "part def IncrementGap",
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


def _declaration_block(text: str, declaration: str) -> list[str]:
    lines = text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.strip() == f"{declaration} {{"
    )
    block = [lines[start]]
    for line in lines[start + 1 :]:
        block.append(line)
        if line.strip() == "}":
            break
    return block


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
        assert "parity complete (o4-w2 pilot 2)" in reviewed["exact_fit_decision"], identity
        assert "no authority cutover implied" in reviewed["exact_fit_decision"], identity
        assert "authority_current remains legacy-yaml until" in reviewed["note"], identity
        assert "under O4" in reviewed["note"], identity


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
    assert len(MIGRATED_IDENTITIES) == 13
    assert set(PILOT_ROWS).isdisjoint(set(MIGRATED_IDENTITIES))


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
        assert row["membership"] == "o4-target", identity
        assert row["base_wave"] == "W2", identity
        assert row["gate_wave"] is None, identity
        assert row["migration_class"] == "MODEL_AUTHORITY_PARITY", identity
        assert row["final_disposition"] == "KEEP_DE4SDV_APPLICATION_SEMANTIC", identity
        assert (
            row["required_runtime_or_consumer_change"]["traversal_required"] is False
        ), identity


def test_boundary_increment_engineering_question_stays_bounded_framing() -> None:
    inventory = _inventory()
    note = _entries(inventory, PILOT_ROWS)["IncrementEngineeringQuestion"]["reviewed"][
        "note"
    ]
    assert "bounded framing vocabulary" in note
    assert "no rename" in note


def test_boundary_increment_lifecycle_decision_has_no_state_model() -> None:
    # The parity edit restores the reviewed value-boundary wording only: the
    # declaration stays a doc-only part definition and no enum/state
    # machinery is introduced for it.
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    block = _declaration_block(file_text, "part def IncrementLifecycleDecision")
    inner = [line for line in block[1:-1] if line.strip()]
    assert all(
        line.strip().startswith("doc /*") and line.strip().endswith("*/")
        for line in inner
    )
    assert "enum def IncrementLifecycleDecision" not in file_text
    assert "state def IncrementLifecycleDecision" not in file_text


def test_boundary_system_layer_leaves_adr_0004_framing_intact() -> None:
    inventory = _inventory()
    note = _entries(inventory, PILOT_ROWS)["SystemLayer"]["reviewed"]["note"]
    assert "ADR 0004 remains the framing authority" in note
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    for specialization in (
        "System1SDVProductLine",
        "System2EngineeringAndAssuranceSystem",
        "System3OpenSourceGovernanceEcosystem",
    ):
        assert f"part def {specialization} :> SystemLayer" in file_text, specialization


def test_boundary_problem_statement_remains_a_requirement_definition() -> None:
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    assert "requirement def ProblemStatement {" in file_text
    block = _declaration_block(file_text, "requirement def ProblemStatement")
    inner = [line for line in block[1:-1] if line.strip()]
    assert all(
        line.strip().startswith("doc /*") and line.strip().endswith("*/")
        for line in inner
    )


def test_boundary_gap_stays_distinct_from_realization_records() -> None:
    inventory = _inventory()
    note = _entries(inventory, PILOT_ROWS)["Gap"]["reviewed"]["note"]
    assert "distinct from realization-record classes" in note
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    for realization_class in ("MissingRealizationRecord", "BlockedRealizationBranchRecord"):
        assert f"part def {realization_class}" in file_text, realization_class
    block = _declaration_block(file_text, "part def IncrementGap")
    inner = [line for line in block[1:-1] if line.strip()]
    assert all(
        line.strip().startswith("doc /*") and line.strip().endswith("*/")
        for line in inner
    )


def test_all_six_blocks_are_doc_only() -> None:
    # The batch changed documentation only: every pilot declaration keeps a
    # single doc statement and no other members.
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    for identity, declaration in PILOT_ROWS.items():
        block = _declaration_block(file_text, declaration)
        inner = [line for line in block[1:-1] if line.strip()]
        assert len(inner) == 1, identity
        assert inner[0].strip().startswith("doc /*"), identity


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
    # Pilot 1 rows keep their closed parity records.
    for identity in ("EngineeringIncrement", "FeatureIncrement", "NeedsRequirementsIncrement"):
        assert entries[identity]["observed"]["doc_text_observation"] == (
            "normalized-exact"
        ), identity
        # later-batch convention (definition admission batch 1): prior rows now
        # carry the shared admission stage.
        assert entries[identity]["reviewed"]["stage"] == TREATED_STAGE, identity
    # The W1-corrected demoted row keeps its bounded-vocabulary record.
    assert entries["IncrementSize"]["reviewed"]["disposition"] == "keep-as-is"
    # The K row keeps its review-required state.
    assert entries["DerivesFromNeed"]["reviewed"]["semantic_text_equivalence"] == (
        "review-required"
    )
