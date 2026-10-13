"""Historical definition records and current model boundaries.

This cleanup retires current-documentation equality with copied or frozen definitions.
Live checks retain owned nonempty documentation, structure and claim boundaries.
Inventory/decision parity fields below describe frozen historical evidence only;
they are not recomputed from, or imposed on, current model wording.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES
from model_contract_fixtures import owned_definition_documentation

REPO_ROOT = Path(__file__).resolve().parents[1]
METHOD_CONTEXT = REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
REGISTER = REPO_ROOT / "docs/method-conformance/o4/o4-execution-register.json"

BATCH_ROWS = ("Need", "Requirement", "RegulatoryConstraint")
MAPPING = {
    "Need": "requirement def StakeholderNeedCandidate",
    "Requirement": "requirement def RequirementCandidate",
    "RegulatoryConstraint": "requirement def RegulatoryConstraintCandidate",
}
DECLARATION_NAME = {
    "Need": "StakeholderNeedCandidate",
    "Requirement": "RequirementCandidate",
    "RegulatoryConstraint": "RegulatoryConstraintCandidate",
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
# 1. Batch scope and mappings
# ---------------------------------------------------------------------------


def test_exact_three_row_scope(register_rows):
    for identity in BATCH_ROWS:
        row = register_rows[identity]
        assert row["membership"] == "o4-target"
        assert row["base_wave"] == "W2"
        assert row.get("gate_wave") is None
        assert row.get("migration_class") == "MODEL_AUTHORITY_PARITY"
        assert row.get("blocker") is None
    assert len(BATCH_ROWS) == 3


def test_definitions_have_owned_nonempty_documentation(model_text):
    # This cleanup retired accepted-definition copied prose, not the declaration homes.
    for identity in BATCH_ROWS:
        assert owned_definition_documentation(model_text, MAPPING[identity]).strip(), identity


# ---------------------------------------------------------------------------
# 2. Honest parity classification and lifecycle state
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Structural lineage boundaries
# ---------------------------------------------------------------------------


def test_sibling_lineages_remain_distinct(model_text):
    need_block = " ".join(_declaration_block(model_text, MAPPING["Need"]))
    requirement_block = " ".join(_declaration_block(model_text, MAPPING["Requirement"]))
    assert "requirement def StakeholderNeedCandidate :> RequirementsManagementAttributeBase {" in need_block
    assert (
        "requirement def RequirementCandidate :> SYSMODRequirementBase, RequirementsManagementAttributeBase {"
        in requirement_block
    )
    # Sibling lineages: neither specializes the other.
    assert "RequirementCandidate" not in need_block.split("doc /*")[0]
    assert "StakeholderNeedCandidate" not in requirement_block.split("doc /*")[0]


def test_requirement_seam_unchanged(model_text):
    block = _declaration_block(model_text, MAPPING["Requirement"])
    header = block[0]
    assert "SYSMODRequirementBase, RequirementsManagementAttributeBase" in header
    joined = _flat(" ".join(block))
    assert "Specializes the SYSMOD requirement seam" in joined
    assert "obligation, stability, and motivation metadata" in joined
    assert "DE4SDV candidate lifecycle semantics remain local." in joined


def test_regulatory_no_compliance_boundary(model_text):
    block = _flat(" ".join(_declaration_block(model_text, MAPPING["RegulatoryConstraint"])))
    assert "with controlled source identity and no compliance claim" in block
    assert "Grounds the ontology RegulatoryConstraint class and R003 derivation targets." in block
    lowered = block.lower()
    for forbidden in ("compliant", "complies", "compliance achieved"):
        assert forbidden not in lowered


def test_no_constrainedby_redesign(model_text):
    assert "constrainedBy" not in model_text


# ---------------------------------------------------------------------------
# 4. Frozen O3, no runtime promotion, prior batches untouched
# ---------------------------------------------------------------------------


def test_no_runtime_or_projection_promotion(register_rows):
    for identity in BATCH_ROWS:
        assert register_rows[identity].get("gate_wave") is None
    # The batch rows are not added as projection rows in this W2 batch; the
    # projection row identity sets remain exactly the accepted O2.2/O2.3 sets
    # (bare class names may still appear as frozen relation domain/range
    # references — that is pre-existing O3 semantics, not a batch-4 row).
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
