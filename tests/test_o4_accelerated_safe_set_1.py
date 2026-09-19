"""O4 accelerated safe-set 1 — per-row precision matrix.

One accelerated PR (the expansion of the W5 batch-1 PR) carrying:

* W3 ``IncrementSize`` definitions parity (normalized-exact, enum-level doc);
* the O2+ native/library grounding + projection layer for the reviewed safe
  subset (see ``tests/test_semantic_projection_o2p.py`` for the layer locks);
* the previously accepted W5 boundary-record parity
  (``ArchitectureDecisionRecord``, ``Baseline`` — locked in
  ``tests/test_o4_w5_batch1_definitions_parity.py``).

Every considered-but-excluded row is recorded in the admission manifest with
its concrete reason. These tests keep per-row precision: no aggregate
assertions that would let a row slip in or out silently.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

INVENTORY = ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS = ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
ADMISSION = ROOT / "docs/method-conformance/o2plus/o2p-admission.yaml"

#: W3 parity row closed by this safe-set.
W3_PARITY_ROWS: dict[str, dict[str, str | None]] = {
    "IncrementSize": {
        "stage": "o4-w3 batch 1 (definitions parity)",
        "observation": "normalized-exact",
        "equivalence": None,
    },
}

#: O2+ grounding/projection rows closed by this safe-set (stage in O1).
O2P_ROWS: tuple[str, ...] = (
    "VariationPoint",
    "Variant",
    "Concern",
    "Viewpoint",
    "View",
    "VerificationMethod",
    "usesVerificationMethod",
)
O2P_STAGE = "o2+ safe-set 1 (grounding + projection)"
O2P_STAGE_RECORD = "o2+ safe-set 1 (grounding record)"

#: Excluded rows pinned with a reason keyword (from the admission manifest).
EXCLUDED_REASON_KEYWORDS: dict[str, str] = {
    "EvidenceStatus": "decision-4",
    "hasEvidenceStatus": "decision-4",
    "allocatedTo": "W7-held",
    "variesAt": "PLE-Q/S",
    "FeatureConfiguration": "decision-9",
    "selectsFeature": "decision-9",
    "appliesToMemberProduct": "decision-9",
    "includesCommonCapability": "decision-9",
    "selectsVariant": "decision-9",
    "instantiatesCanonicalArchitecture": "decision-10",
    "Interface": "decision-5",
    "ValidationScenario": "validatedBy",
    "hasStakeholder": "decision-11",
    "specifiesFeature": "PLE-Q/S",
    "specifiesCommonCapability": "PLE-Q/S",
    "recordsGap": "definition-carrier",
    "recordsAssumption": "definition-carrier",
    "addressesConcern": "definition-carrier",
    "selectedViewpoint": "definition-carrier",
    "producesView": "definition-carrier",
    "EvidenceArtifact": "T/E evidence-reference",
    "hasEvidence": "T/E evidence-reference",
    "capturedInBaseline": "T/E evidence-reference",
    "Scenario": "no model-side declaration",
    "CommonCapability": "decision-14",
    "Feature": "decision-14",
    "MethodEvaluationScope": "decision-7",
    "ProductLineCharacteristic": "decision-bound",
    "Stakeholder": "decision-11",
    "AssuranceClaim": "decision-3",
    "ArchitectureElement": "decision-5",
    "Function": "decision-5",
    "LogicalElement": "decision-5",
    "PhysicalElement": "decision-5",
    "AcceptanceCriterion": "decision-6",
    "hasAcceptanceCriterion": "decision-6",
    "EvidenceContract": "evidence-lineage",
    "hasRelevantEvidenceContract": "evidence-lineage",
    "constrainedBy": "decision-2",
    "realizedBy": "decision-1",
    "deployedTo": "decision-1",
    "validatedBy": "decision-1",
    "supportedByEvidence": "decision-3",
    "TraceLink": "decision-8",
    "RequiredTraceChain": "decision-8",
}


@pytest.fixture(scope="module")
def inventory() -> dict:
    import json

    return json.loads(INVENTORY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def decisions() -> dict:
    return yaml.safe_load(DECISIONS.read_text(encoding="utf-8"))["entries"]


@pytest.fixture(scope="module")
def admission() -> dict:
    return yaml.safe_load(ADMISSION.read_text(encoding="utf-8"))


def _entry(inventory: dict, identity: str) -> dict:
    return next(e for e in inventory["entries"] if e["identity"] == identity)


# --- included rows ----------------------------------------------------------


@pytest.mark.parametrize("identity", sorted(W3_PARITY_ROWS))
def test_w3_parity_rows_are_closed(
    inventory: dict, decisions: dict, identity: str
) -> None:
    expected = W3_PARITY_ROWS[identity]
    entry = _entry(inventory, identity)
    assert entry["observed"]["doc_text_observation"] == expected["observation"]
    assert (
        entry["reviewed"]["semantic_text_equivalence"] == expected["equivalence"]
    )
    assert decisions[identity]["stage"] == expected["stage"]


@pytest.mark.parametrize("identity", O2P_ROWS)
def test_o2p_rows_carry_their_recorded_stage(
    decisions: dict, identity: str
) -> None:
    stage = decisions[identity]["stage"]
    assert stage in (O2P_STAGE, O2P_STAGE_RECORD), identity
    if identity in ("VerificationMethod", "usesVerificationMethod"):
        assert stage == O2P_STAGE_RECORD
    else:
        assert stage == O2P_STAGE


@pytest.mark.parametrize("identity", O2P_ROWS)
def test_o2p_rows_keep_vocabulary_only_residual(decisions: dict, identity: str) -> None:
    required = decisions[identity]["required_evidence"]
    assert required, identity
    assert any("exact-revision traversal evidence" in item for item in required), identity
    assert decisions[identity]["closure_evidence_ref"] is None, identity


def test_increment_size_residual_is_bounded_vocabulary(decisions: dict) -> None:
    required = decisions["IncrementSize"]["required_evidence"]
    assert required == [
        "none beyond bounded vocabulary: model-resident guidance labels; never promoted to semantic authority"
    ]


def test_w5_boundary_rows_stage_unchanged_by_this_safe_set(decisions: dict) -> None:
    # The W5 boundary-record parity carried by the same PR keeps its own stage.
    assert decisions["ArchitectureDecisionRecord"]["stage"] == (
        "o4-w5 batch 1 (definitions parity)"
    )
    assert decisions["Baseline"]["stage"] == "o4-w5 batch 1 (definitions parity)"


# --- excluded rows ----------------------------------------------------------


def test_excluded_matrix_matches_the_admission_manifest(admission: dict) -> None:
    manifest_excluded = {row["identity"]: row["reason"] for row in admission["excluded"]}
    assert set(manifest_excluded) == set(EXCLUDED_REASON_KEYWORDS)
    for identity, keyword in EXCLUDED_REASON_KEYWORDS.items():
        assert keyword in manifest_excluded[identity], identity


def test_excluded_rows_were_not_treated(decisions: dict, admission: dict) -> None:
    excluded = {row["identity"] for row in admission["excluded"]}
    for identity in excluded:
        stage = decisions[identity]["stage"]
        assert "safe-set" not in stage, f"{identity} was silently treated: {stage!r}"
        assert stage != "o4-w3 batch 1 (definitions parity)", identity


def test_admitted_rows_are_disjoint_from_excluded(admission: dict) -> None:
    admitted = {row["identity"] for row in admission["admitted"]}
    excluded = {row["identity"] for row in admission["excluded"]}
    assert admitted == set(O2P_ROWS) | {"IncrementSize"}
    assert admitted & excluded == set()
