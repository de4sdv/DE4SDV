"""ADR 0009 verification-attribute migration consistency.

The ODE4HERA ``NeedsRequirementsAttributes`` base (adopted via ADR 0009 and
extended by its amendment) carries ``verificationMethod`` (NRM A8) and
``verificationStatus`` (NRM A13+A14) natively on every requirement usage.
The AEBS pilot YAML therefore no longer duplicates ``method`` or
``evidence_status`` columns; its records keep only criterion gaps and
bounded-evidence locations.

This gate keeps the migration honest in both directions:

- every controlled AEBS requirement usage states both attributes in SysML,
  with ``verificationMethod`` drawn from the standard VerificationMethodKind
  vocabulary (upstream types it String, so the vocabulary is test-enforced);
- the pilot YAML verification_planning records no longer carry ``method`` or
  ``evidence_status`` keys (no duplicated planning data), and every
  requirement ID in a YAML record exists in the model.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
MODEL = (
    ROOT
    / "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"
)
YAML_PATH = (
    ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml"
)
MD_PATH = (
    ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md"
)

METHOD_VOCABULARY = {"inspect", "demo", "test", "analyze"}

# REQ ID -> usage name (from the model's doc comments).
REQ_TO_USAGE = {
    "REQ-AEBS-001": "reqDetectForwardCollisionRisk",
    "REQ-AEBS-002": "reqProvideCollisionWarning",
    "REQ-AEBS-003": "reqCommandEmergencyBraking",
    "REQ-AEBS-004": "reqAllowDriverOverride",
    "REQ-AEBS-005": "reqDetectAEBSFailureCondition",
    "REQ-AEBS-006": "reqKeepProductLineClassificationExplicit",
    "REQ-AEBS-007": "reqTraceRequirementVVAndGaps",
    "REQ-AEBS-S2-001": "reqTraceEvidenceContractsToControlledBoundary",
    "REQ-AEBS-008": "reqResistFalseReaction",
    "REQ-AEBS-009": "reqHandleDegradedUnavailableInputs",
    "REQ-AEBS-010": "reqPedestrianTargetResponse",
    "REQ-AEBS-011": "reqBicycleTargetResponse",
    "REQ-AEBS-012": "reqResistFalseBrakingCommand",
    "REQ-AEBS-013": "reqIndicateDegradedUnavailableStatus",
    "REQ-AEBS-014": "reqPedestrianTargetControlledResponse",
    "REQ-AEBS-015": "reqBicycleTargetControlledResponse",
}


def _requirement_blocks(model: str) -> dict[str, str]:
    """Map usage name -> block text for every controlled requirement usage."""
    blocks = {}
    for req_id, usage in REQ_TO_USAGE.items():
        m = re.search(
            rf"requirement {re.escape(usage)} : \w+ \{{.*?\n          \}}",
            model,
            re.S,
        )
        assert m, f"model block for {req_id} ({usage}) not found"
        blocks[req_id] = m.group(0)
    return blocks


def test_every_aebs_requirement_states_native_verification_attributes():
    model = MODEL.read_text(encoding="utf-8")
    blocks = _requirement_blocks(model)
    for req_id, block in blocks.items():
        method = re.search(
            r'attribute :>> verificationMethod = "(\w+)";', block
        )
        assert method, f"{req_id}: no verificationMethod attribute"
        assert method.group(1) in METHOD_VOCABULARY, (
            f"{req_id}: verificationMethod '{method.group(1)}' outside the "
            "VerificationMethodKind vocabulary {inspect, demo, test, analyze}"
        )
        assert re.search(
            r"attribute :>> verificationStatus = VVStatus::\w+;", block
        ), f"{req_id}: no verificationStatus attribute"


def test_yaml_verification_planning_no_longer_duplicates_attributes():
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    for record in data["verification_planning"]["records"]:
        assert "method" not in record, record["requirements"]
        assert "evidence_status" not in record, record["requirements"]
        for req_id in record["requirements"]:
            assert req_id in REQ_TO_USAGE, req_id


def test_yaml_records_still_cover_every_controlled_requirement():
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    covered = {
        req_id
        for record in data["verification_planning"]["records"]
        for req_id in record["requirements"]
    }
    assert covered == set(REQ_TO_USAGE), covered ^ set(REQ_TO_USAGE)


def test_markdown_planning_section_documents_the_migration():
    markdown = MD_PATH.read_text(encoding="utf-8")
    assert "verificationMethod" in markdown
    assert "VVStatus" in markdown
