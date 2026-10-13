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

ADMISSION = ROOT / "docs/method-conformance/o2plus/o2p-admission.yaml"


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
    "recordsGap": "W4 batch 1 treated",
    "recordsAssumption": "W4 batch 1 treated",
    "addressesConcern": "W4 batch 1 treated",
    "selectedViewpoint": "W4 batch 1 treated",
    "producesView": "W4 batch 1 treated",
    "EvidenceArtifact": "W5 batch 3 treated",
    "hasEvidence": "W5 batch 3 treated",
    "capturedInBaseline": "W5 batch 3 treated",
    # Definition admission batch 1 treated these two rows after this manifest
    # was written; the reasons were refreshed to record the treatment while
    # the rows remain outside the O2+ admission (their representation belongs
    # to the definition-admission layer).
    "Scenario": "Definition admission batch 1 treated",
    "CommonCapability": "decision-14",
    "Feature": "decision-14",
    "MethodEvaluationScope": "decision-7",
    "ProductLineCharacteristic": "Definition admission batch 1 treated",
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
def admission() -> dict:
    return yaml.safe_load(ADMISSION.read_text(encoding="utf-8"))


# --- included rows ----------------------------------------------------------


# --- excluded rows ----------------------------------------------------------


def test_excluded_matrix_matches_the_admission_manifest(admission: dict) -> None:
    manifest_excluded = {row["identity"]: row["reason"] for row in admission["excluded"]}
    assert set(manifest_excluded) == set(EXCLUDED_REASON_KEYWORDS)
    for identity, keyword in EXCLUDED_REASON_KEYWORDS.items():
        assert keyword in manifest_excluded[identity], identity


def test_admitted_rows_are_disjoint_from_excluded(admission: dict) -> None:
    admitted = {row["identity"] for row in admission["admitted"]}
    excluded = {row["identity"] for row in admission["excluded"]}
    assert admitted == set(O2P_ROWS) | {"IncrementSize"}
    assert admitted & excluded == set()
