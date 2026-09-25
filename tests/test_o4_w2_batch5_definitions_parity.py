"""O4 W2 batch 5 — realization-gap record definitions parity (two rows).

Batch scope (exactly two retained, ungated ``MODEL_AUTHORITY_PARITY`` rows
grounded in ``de4sdv_method_context.sysml``):

* ``MissingRealizationRecord``      -> ``part def MissingRealizationRecord``
* ``BlockedRealizationBranchRecord`` -> ``part def BlockedRealizationBranchRecord``

Both close definition-level parity normalized-exact: the model doc carries
the reviewed definition text verbatim under cosmetic normalization only.  The
records remain bounded gap/blockage records — distinct from the ``Gap``
identity and from the c5 realization relationships — and are not authority
for realization semantics.
"""

from __future__ import annotations

import json
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

BATCH_ROWS = ("MissingRealizationRecord", "BlockedRealizationBranchRecord")
MAPPING = {
    "MissingRealizationRecord": "part def MissingRealizationRecord",
    "BlockedRealizationBranchRecord": "part def BlockedRealizationBranchRecord",
}
ACCEPTED_DEFINITION = {
    "MissingRealizationRecord": (
        "A record of a missing or blocked realization allocation for a conceptual element."
    ),
    "BlockedRealizationBranchRecord": (
        "A record of a realization branch blocked by a source defect or gap."
    ),
}
# later-batch convention (definition admission batch 1): the parity stage
# is superseded by the shared admission stage.
STAGE = "o4 definition admission batch 1 (projection + profile)"
OBLIGATION = "runtime-queryable support (post-migration) requires exact-revision traversal evidence; support remains vocabulary-only"

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


def test_exactly_the_batch_rows_carry_the_batch_stage(decisions):
    # later-batch convention (definition admission batch 1): the stage label
    # is now shared by the admitted family; this batch must be inside it and
    # the full staged set must equal the governed admitted set.
    staged = [name for name, row in decisions.items() if row.get("stage") == STAGE]
    assert set(BATCH_ROWS) <= set(staged)
    manifest = yaml.safe_load(
        (REPO_ROOT / "docs/method-conformance/o4/definition-admission.yaml").read_text()
    )
    admitted = sorted(row["identity"] for row in manifest["admitted"])
    assert sorted(staged) == admitted


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


def test_honest_parity_state(inventory, decisions):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        assert entry["observed"]["doc_text_observation"] == "normalized-exact", identity
        assert entry["reviewed"]["semantic_text_equivalence"] is None, identity
        row = decisions[identity]
        assert row["semantic_text_equivalence"] is None
        assert row["stage"] == STAGE
        assert "batch-5 parity-reviewed" in row["note"]
        assert row["exact_fit_decision"].startswith(
            "exact fit: definition-level parity complete (o4-w2 batch 5)"
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


def test_no_authority_cutover(decisions):
    for identity in BATCH_ROWS:
        row = decisions[identity]
        assert row["closure_evidence_ref"] is None
        assert row["conditional_target"] is False


# ---------------------------------------------------------------------------
# 2. Bounded-record boundaries (no realization authority, distinct identities)
# ---------------------------------------------------------------------------


def test_records_are_bounded_not_realization_authority(decisions):
    for identity in BATCH_ROWS:
        note = decisions[identity]["note"]
        assert "bounded" in note
        assert "not authority for realization semantics" in note


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


def test_no_new_projection_rows(inventory):
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
    scope = json.loads(SCOPE.read_text())
    identities = {row["identity"] for row in scope["identities"]}
    assert identities == set(MIGRATED_IDENTITIES)
    assert len(identities) == 13
    for identity in BATCH_ROWS:
        assert identity not in identities
        assert register_rows[identity].get("gate_wave") is None


def test_prior_batch_rows_unchanged(decisions):
    # later-batch convention (definition admission batch 1): prior parity rows now
    # carry the shared admission stage.
    expected_stage = {
        "EngineeringIncrement": "o4 definition admission batch 1 (projection + profile)",
        "FeatureIncrement": "o4 definition admission batch 1 (projection + profile)",
        "NeedsRequirementsIncrement": "o4 definition admission batch 1 (projection + profile)",
        "IncrementEngineeringQuestion": "o4 definition admission batch 1 (projection + profile)",
        "IncrementLifecycleDecision": "o4 definition admission batch 1 (projection + profile)",
        "SystemLayer": "o4 definition admission batch 1 (projection + profile)",
        "ProblemStatement": "o4 definition admission batch 1 (projection + profile)",
        "Assumption": "o4 definition admission batch 1 (projection + profile)",
        "Gap": "o4 definition admission batch 1 (projection + profile)",
        "SignalMappingDisposition": "o4 definition admission batch 1 (projection + profile)",
        "LogicalToSoftwareSignalMappingRecord": "o4 definition admission batch 1 (projection + profile)",
        "SystemToSoftwareSignalMappingCandidate": "o4 definition admission batch 1 (projection + profile)",
        "Need": "o4 definition admission batch 1 (projection + profile)",
        "Requirement": "o4 definition admission batch 1 (projection + profile)",
        "RegulatoryConstraint": "o4 definition admission batch 1 (projection + profile)",
    }
    for identity, stage in expected_stage.items():
        assert decisions[identity]["stage"] == stage, identity
        assert decisions[identity]["authority_current"] == "legacy-yaml", identity
