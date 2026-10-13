"""Historical definition records and current model boundaries.

This cleanup retires current-documentation equality with copied or frozen definitions.
Live checks retain owned nonempty documentation, structure and claim boundaries.
Inventory/decision parity fields below describe frozen historical evidence only;
they are not recomputed from, or imposed on, current model wording.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES
from model_contract_fixtures import owned_definition_documentation

REPO_ROOT = Path(__file__).resolve().parents[1]
METHOD_CONTEXT = REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
REGISTER = REPO_ROOT / "docs/method-conformance/o4/o4-execution-register.json"

BATCH_ROWS = ("MissingRealizationRecord", "BlockedRealizationBranchRecord")
MAPPING = {
    "MissingRealizationRecord": "part def MissingRealizationRecord",
    "BlockedRealizationBranchRecord": "part def BlockedRealizationBranchRecord",
}

USAGES = {
    "textual-notation-of-model/packages/features/middleware/middleware_variability_configuration.sysml": [
        "part directVSIDLToROS2Realization : MissingRealizationRecord {",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_physical_software_realization.sysml": [
        "part def MissingPhysicalRealizationRecord :> MissingRealizationRecord;",
        "part def BlockedPhysicalRealizationBranchRecord :> BlockedRealizationBranchRecord;",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_visualization_physical_software_realization.sysml": [
        "part blockedPredictedTrajectoryRemainsDeferred : BlockedRealizationBranchRecord {",
    ],
}


def _flat(text: str) -> str:
    return " ".join(text.replace("*", " ").split())


def _declaration_block(text: str, decl_start: str) -> list[str]:
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().startswith(decl_start))
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for line in lines[start + 1 :]:
        block.append(line)
        if line.strip() == "}" and (len(line) - len(line.lstrip())) == base_indent:
            break
    return block


@pytest.fixture(scope="module")
def model_text() -> str:
    return METHOD_CONTEXT.read_text()


@pytest.fixture(scope="module")
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


# ---------------------------------------------------------------------------
# 1. Batch scope, mappings, definitions, parity state
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


def test_definitions_have_owned_nonempty_documentation(model_text):
    # This cleanup retired accepted-definition copied prose, not the declaration homes.
    for identity in BATCH_ROWS:
        assert owned_definition_documentation(model_text, MAPPING[identity]).strip(), identity


# ---------------------------------------------------------------------------
# 2. Bounded-record boundaries (no realization authority, distinct identities)
# ---------------------------------------------------------------------------


def test_missing_record_distinct_from_gap(model_text):
    block = " ".join(_declaration_block(model_text, MAPPING["MissingRealizationRecord"]))
    assert "part def MissingRealizationRecord {" in block
    assert ":>" not in block.split("doc /*")[0]
    assert "IncrementGap" not in block
    assert "part def IncrementGap {" in model_text


def test_blocked_record_distinct_from_gap(model_text):
    block = " ".join(_declaration_block(model_text, MAPPING["BlockedRealizationBranchRecord"]))
    assert "part def BlockedRealizationBranchRecord {" in block
    assert ":>" not in block.split("doc /*")[0]
    assert "IncrementGap" not in block


def test_records_distinct_from_one_another(model_text):
    for identity in BATCH_ROWS:
        block = " ".join(_declaration_block(model_text, MAPPING[identity]))
        assert ":>" not in block.split("doc /*")[0], identity
    assert "MissingRealizationRecord" not in _declaration_block(model_text, MAPPING["BlockedRealizationBranchRecord"])[0]
    assert "BlockedRealizationBranchRecord" not in _declaration_block(model_text, MAPPING["MissingRealizationRecord"])[0]


def test_no_realizedby_redesign_or_allocated_to_architecture(model_text):
    assert "realizedBy" not in model_text
    assert "allocatedToArchitecture" not in model_text


# ---------------------------------------------------------------------------
# 3. Existing usages, projections, runtime, prior batches
# ---------------------------------------------------------------------------


def test_existing_usages_remain_intact():
    for path, lines in USAGES.items():
        text = (REPO_ROOT / path).read_text()
        for line in lines:
            assert line in text, (path, line)


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


def test_no_runtime_or_o3_promotion(register_rows):
    for identity in BATCH_ROWS:
        assert identity not in MIGRATED_IDENTITIES
        assert register_rows[identity].get("gate_wave") is None
