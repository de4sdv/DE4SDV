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
REGISTER = REPO_ROOT / "de4sdv/semantic/contract-data/ontology-identity-register.json"

BATCH_ROWS = ("ArchitectureDecisionRecord", "Baseline")
MAPPING = {
    "ArchitectureDecisionRecord": (
        "part def ArchitectureDecisionRecord",
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
    ),
    "Baseline": (
        "part def DE4SDVEvidenceBaseline",
        "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml",
    ),
}

USAGES = {
    "scripts/check_model_sync.py": [
        "(Need, RegulatoryConstraint, ArchitectureDecisionRecord)",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_operational_context.sysml": [
        "actor evidenceBaseline : DE4SDVEvidenceBaseline;",
        "part de4sdvEvidenceBaseline : DE4SDVEvidenceBaseline;",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_visualization_operational_context.sysml": [
        "actor evidenceBaseline : DE4SDVEvidenceBaseline;",
        "part visualizationEvidenceBaseline : DE4SDVEvidenceBaseline;",
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
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


def _model_flat(identity: str) -> str:
    decl, path = MAPPING[identity]
    return _flat(" ".join(_declaration_block((REPO_ROOT / path).read_text(), decl)))


# ---------------------------------------------------------------------------
# 1. Batch scope, mappings, definitions, parity state
# ---------------------------------------------------------------------------


def test_exact_two_row_scope(register_rows):
    for identity in BATCH_ROWS:
        row = register_rows[identity]
        assert row["membership"] == "o4-target"
        assert row["base_wave"] == "W5"
        assert row.get("gate_wave") is None
        assert row.get("migration_class") == "EXTERNAL_BOUNDARY"
        assert not row.get("blockers")
    assert len(BATCH_ROWS) == 2


def test_definitions_have_owned_nonempty_documentation():
    # This cleanup retired copied parity prose; external-reference/non-claim guards remain.
    for identity in BATCH_ROWS:
        declaration, path = MAPPING[identity]
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert owned_definition_documentation(source, declaration).strip(), identity


# ---------------------------------------------------------------------------
# 2. External-boundary preservation
# ---------------------------------------------------------------------------


def test_adr_r003_grounding_kept():
    flat = _model_flat("ArchitectureDecisionRecord")
    assert "Grounds the ontology ArchitectureDecisionRecord class and R003 derivation targets." in flat
    assert "can serve as the semantic origin of a design-input requirement" in flat


def test_baseline_non_claim_boundary_kept():
    flat = _model_flat("Baseline")
    assert "referenced without implying accepted evidence" in flat
    # No rename: the declaration name stays DE4SDVEvidenceBaseline.
    assert "part def DE4SDVEvidenceBaseline :> OperationalEntity {" in (
        REPO_ROOT / MAPPING["Baseline"][1]
    ).read_text()


def test_existing_usages_remain_intact():
    for path, lines in USAGES.items():
        text = (REPO_ROOT / path).read_text()
        for line in lines:
            assert line in text, (path, line)


# ---------------------------------------------------------------------------
# 3. Projections, runtime, frozen O3, prior batches
# ---------------------------------------------------------------------------


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


def test_no_runtime_or_o3_promotion(register_rows):
    for identity in BATCH_ROWS:
        assert identity not in MIGRATED_IDENTITIES
        assert register_rows[identity].get("gate_wave") is None
