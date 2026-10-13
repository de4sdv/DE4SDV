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
REGISTER_PATH = REPO / "de4sdv/semantic/contract-data/ontology-identity-register.json"
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
