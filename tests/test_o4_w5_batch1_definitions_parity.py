"""O4 W5 batch 1 — external-boundary reference record definitions parity.

First bounded W5 (review Deliverable 8 wave 4) definitions-parity sub-step.
Exactly two retained, ungated ``MODEL_AUTHORITY_PARITY`` rows:

* ``ArchitectureDecisionRecord`` -> ``part def ArchitectureDecisionRecord``
  (``de4sdv_method_context.sysml``)
* ``Baseline`` -> ``part def DE4SDVEvidenceBaseline``
  (``de4sdv_operational_context.sysml``)

Both close definition-level parity by explicit reviewed-equivalence records:
the model docs carry the reviewed definitional text plus model-resident
reviewed content (the R003 derivation-grounding sentence; the non-claim
boundary) that the review requires to stay carried.  Both remain external
**reference identities** — content authority stays external; the model never
mirrors ADR or baseline contents.  This is the parity sub-step only; the wave
exit (governed external-authority contract docs) remains outstanding.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY = REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS = REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
REGISTER = REPO_ROOT / "docs/method-conformance/o4/o4-execution-register.json"
SCOPE = REPO_ROOT / "docs/method-conformance/o3/o3-equivalence-scope.json"

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
ACCEPTED_DEFINITION = {
    "ArchitectureDecisionRecord": (
        "A reviewed architecture or method decision recorded as an ADR in Git that can "
        "serve as the semantic origin of a design-input requirement."
    ),
    "Baseline": (
        "A reviewed and controlled state of model, evidence, configuration, or "
        "publication artifacts, referenced without implying accepted evidence."
    ),
}
STAGE = "o4-w5 batch 1 (definitions parity)"
OBLIGATION = "O2 admission / generated Semantic Projection from the reviewed model representation"

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


def test_exactly_the_batch_rows_carry_the_batch_stage(decisions):
    staged = [name for name, row in decisions.items() if row.get("stage") == STAGE]
    assert sorted(staged) == sorted(BATCH_ROWS)


def test_declaration_mapping(inventory):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        observed = entry["observed"]
        assert observed["declaration"] == MAPPING[identity][0]
        assert observed["file"] == MAPPING[identity][1]
        assert observed["yaml_path"] == f"classes:{identity}"


def test_accepted_definitions_are_carried():
    for identity in BATCH_ROWS:
        assert ACCEPTED_DEFINITION[identity] in _model_flat(identity), identity


def test_honest_parity_state(inventory, decisions):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        assert entry["observed"]["doc_text_observation"] == "differs", identity
        assert entry["reviewed"]["semantic_text_equivalence"] == "reviewed-equivalent", identity
        row = decisions[identity]
        assert row["semantic_text_equivalence"] == "reviewed-equivalent"
        assert row["stage"] == STAGE
        assert "batch-1 parity-reviewed" in row["note"]
        assert row["exact_fit_decision"].startswith(
            "reviewed-equivalence: definition-level parity closed (o4-w5 batch 1)"
        )


def test_legacy_yaml_authority_remains(decisions, inventory):
    for identity in BATCH_ROWS:
        row = decisions[identity]
        assert row["authority_current"] == "legacy-yaml"
        assert row["authority_target"] == "model-authoritative"
        assert row["conditional_target"] is False
        assert row["transition_gate"] is None
        assert row["closure_evidence_ref"] is None
        assert _entry(inventory, identity)["reviewed"]["authority_current"] == "legacy-yaml"


def test_remaining_obligation_is_o4_o2_only(decisions):
    for identity in BATCH_ROWS:
        evidence = decisions[identity]["required_evidence"]
        assert evidence == [OBLIGATION], identity
        assert all("O3" not in item for item in evidence)


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


def test_external_content_never_mirrored(decisions):
    # The records stay reference identities: review notes pin that content
    # authority stays external for both rows.
    assert "ADR content stays external" in decisions["ArchitectureDecisionRecord"]["note"]
    assert "must not mirror baseline contents" in decisions["Baseline"]["note"]


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
        "MissingRealizationRecord": "o4 definition admission batch 1 (projection + profile)",
        "BlockedRealizationBranchRecord": "o4 definition admission batch 1 (projection + profile)",
        "ProductLine": "o4 definition admission batch 1 (projection + profile)",
        "MemberProduct": "o4 definition admission batch 1 (projection + profile)",
        "DeferredProductLineScope": "o4 definition admission batch 1 (projection + profile)",
    }
    for identity, stage in expected_stage.items():
        assert decisions[identity]["stage"] == stage, identity
        assert decisions[identity]["authority_current"] == "legacy-yaml", identity
