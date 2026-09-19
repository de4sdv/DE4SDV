"""O4 W2 batch 4 — requirements-lineage definitions parity (three rows).

Batch scope (exactly three retained, ungated ``MODEL_AUTHORITY_PARITY`` rows
grounded in ``de4sdv_method_context.sysml``):

* ``Need``                 -> ``requirement def StakeholderNeedCandidate``
* ``Requirement``          -> ``requirement def RequirementCandidate``
* ``RegulatoryConstraint`` -> ``requirement def RegulatoryConstraintCandidate``

All three close their definition-level parity by explicit reviewed-equivalence
records: the model doc carries the accepted definition verbatim plus preserved
reviewed content (NRM/ADR-0009 lineage; SYSMOD seam/candidate context; R003
derivation grounding).  The tests below machine-pin the batch scope, the
mappings, the accepted definitions, the honest classification, the lifecycle
state, and the structural boundaries that must remain unchanged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

REPO_ROOT = Path(__file__).resolve().parents[1]
METHOD_CONTEXT = REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
INVENTORY = REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS = REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
REGISTER = REPO_ROOT / "docs/method-conformance/o4/o4-execution-register.json"
SCOPE = REPO_ROOT / "docs/method-conformance/o3/o3-equivalence-scope.json"

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
ACCEPTED_DEFINITION = {
    "Need": "Stakeholder-expressed problem-space intent, before conversion into design-input requirements.",
    "Requirement": (
        "A verifiable design input obligation or constraint derived from needs, standards, "
        "or architecture decisions."
    ),
    "RegulatoryConstraint": (
        "A constraint or reference derived from a standard, regulation, or "
        "homologation-relevant source, with controlled source identity and no compliance claim."
    ),
}
STAGE = "o4-w2 batch 4 (definitions parity)"
OBLIGATION = "O2 admission / generated Semantic Projection from the reviewed model representation"


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
def inventory() -> dict:
    return json.loads(INVENTORY.read_text())


@pytest.fixture(scope="module")
def decisions() -> dict:
    return yaml.safe_load(DECISIONS.read_text())["entries"]


@pytest.fixture(scope="module")
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


def _entry(inventory: dict, identity: str) -> dict:
    return next(e for e in inventory["entries"] if e["identity"] == identity)


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


def test_exactly_the_batch_rows_carry_the_batch_stage(decisions):
    staged = [name for name, row in decisions.items() if row.get("stage") == STAGE]
    assert sorted(staged) == sorted(BATCH_ROWS)


def test_declaration_mapping(inventory):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        observed = entry["observed"]
        assert observed["declaration"] == MAPPING[identity]
        assert observed["file"] == "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
        assert observed["yaml_path"] == f"classes:{identity}"


def test_accepted_definitions_are_carried(model_text):
    for identity in BATCH_ROWS:
        block = _flat(" ".join(_declaration_block(model_text, MAPPING[identity])))
        assert ACCEPTED_DEFINITION[identity] in block, identity


# ---------------------------------------------------------------------------
# 2. Honest parity classification and lifecycle state
# ---------------------------------------------------------------------------


def test_honest_parity_classification(inventory, decisions):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        assert entry["observed"]["doc_text_observation"] == "differs", identity
        assert entry["reviewed"]["semantic_text_equivalence"] == "reviewed-equivalent", identity
        row = decisions[identity]
        assert row["semantic_text_equivalence"] == "reviewed-equivalent"
        assert row["stage"] == STAGE
        assert "batch-4 parity-reviewed" in row["note"]
        assert row["exact_fit_decision"].startswith(
            "reviewed-equivalence: definition-level parity closed (o4-w2 batch 4)"
        )


def test_legacy_yaml_authority_remains(decisions, inventory):
    for identity in BATCH_ROWS:
        row = decisions[identity]
        assert row["authority_current"] == "legacy-yaml"
        assert row["authority_target"] == "model-authoritative"
        assert row["conditional_target"] is False
        assert row["transition_gate"] is None
        assert row["closure_evidence_ref"] is None
        assert row["adoption_status"] == "not-applicable"
        assert row["evidence_state"] == "repository-evidenced"
        assert _entry(inventory, identity)["reviewed"]["authority_current"] == "legacy-yaml"


def test_remaining_obligation_is_o4_o2_only(decisions):
    for identity in BATCH_ROWS:
        evidence = decisions[identity]["required_evidence"]
        assert evidence == [OBLIGATION], identity
        assert all("O3" not in item for item in evidence)


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


def test_external_sources_remain_external(decisions):
    note = decisions["RegulatoryConstraint"]["note"]
    assert "external semantic and content authority" in note
    assert "asserts no compliance" in note
    assert "constrainedBy relationship redesign remains out of scope and unimplemented" in note


def test_no_constrainedby_redesign(model_text):
    assert "constrainedBy" not in model_text


# ---------------------------------------------------------------------------
# 4. Frozen O3, no runtime promotion, prior batches untouched
# ---------------------------------------------------------------------------


def test_frozen_o3_relations_unchanged():
    scope = json.loads(SCOPE.read_text())
    identities = {row["identity"] for row in scope["identities"]}
    assert identities == set(MIGRATED_IDENTITIES)
    assert len(identities) == 13
    for relation in (
        "derivesRequirementFromNeed",
        "derivedRequirementsOfNeed",
        "hasSubject",
        "verifiedBy",
        "hasRelevantArchitecture",
    ):
        assert relation in identities
    for identity in BATCH_ROWS:
        assert identity not in identities


def test_no_runtime_or_projection_promotion(inventory, register_rows):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        assert entry["reviewed"]["evidence_state"] == "repository-evidenced"
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
    }
    for identity, stage in expected_stage.items():
        assert decisions[identity]["stage"] == stage, identity
        assert decisions[identity]["authority_current"] == "legacy-yaml", identity
