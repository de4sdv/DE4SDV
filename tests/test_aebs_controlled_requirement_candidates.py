import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
YAML_PATH = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml"
MARKDOWN_PATH = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md"
MODEL_PATH = ROOT / "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"

EXPECTED_NEW_NEEDS = {"N-AEBS-006", "N-AEBS-007"}
EXPECTED_NEW_REQUIREMENTS = {
    "REQ-AEBS-008",
    "REQ-AEBS-009",
    "REQ-AEBS-010",
    "REQ-AEBS-011",
}


def _load():
    return yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))


def test_new_system1_candidates_are_aligned_across_control_artifacts():
    data = _load()
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    model = MODEL_PATH.read_text(encoding="utf-8")

    need_ids = {item["id"] for item in data["needs"]}
    requirement_ids = {item["id"] for item in data["requirements"]}
    assert EXPECTED_NEW_NEEDS <= need_ids
    assert EXPECTED_NEW_REQUIREMENTS <= requirement_ids
    for record_id in EXPECTED_NEW_NEEDS | EXPECTED_NEW_REQUIREMENTS:
        assert f"`{record_id}`" in markdown
        assert record_id in model


def test_pedestrian_and_bicycle_candidates_are_distinct_and_source_controlled():
    data = _load()
    needs = {item["id"]: item for item in data["needs"]}
    requirements = {item["id"]: item for item in data["requirements"]}

    assert "pedestrian" in needs["N-AEBS-006"]["statement"].lower()
    assert "bicycle" in needs["N-AEBS-007"]["statement"].lower()
    assert requirements["REQ-AEBS-010"]["derived_from"] == ["N-AEBS-006"]
    assert requirements["REQ-AEBS-011"]["derived_from"] == ["N-AEBS-007"]
    for record_id in ("REQ-AEBS-010", "REQ-AEBS-011"):
        record = requirements[record_id]
        assert record["status"] == "draft"
        assert record["maturity"] == "draft_requirement_with_gap"
        assert record["source_links"]
        assert record["applicability"]
        assert record["known_gaps"]


def test_override_false_reaction_and_degraded_candidates_keep_open_criteria_visible():
    requirements = {item["id"]: item for item in _load()["requirements"]}

    override = requirements["REQ-AEBS-004"]
    assert "valid" in override["statement"].lower()
    assert "fresh" in override["statement"].lower()
    assert override["maturity"] == "draft_requirement_with_gap"

    false_reaction = requirements["REQ-AEBS-008"]
    assert "shall not" in false_reaction["statement"].lower()
    assert false_reaction["maturity"] == "draft_requirement_with_gap"

    degraded = requirements["REQ-AEBS-009"]
    for condition in ("stale", "missing", "malformed", "inconsistent"):
        assert condition in degraded["statement"].lower()
    assert degraded["maturity"] == "draft_requirement_with_gap"


def test_quantified_regulatory_candidates_distinguish_controlled_source_from_open_applicability():
    data = _load()
    regulatory = data["regulatory_candidate_control"]

    assert regulatory["source_id"] == "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2"
    assert regulatory["source_identity_status"] == "controlled_public_safe_metadata"
    assert regulatory["source_metadata_artifact"] == (
        "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml"
    )
    assert regulatory["source_original_sha256"] == (
        "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de"
    )
    assert regulatory["applicability_status"] == "candidate_not_authoritatively_determined"
    assert regulatory["quantified_candidate_status"] == "derivation_deferred"
    assert regulatory["quantified_candidates"] == []
    assert regulatory["gap_ids"]

    forbidden_claim = re.compile(
        r"\b(?:compliant|certified|homologated|type[- ]approved)\b", re.IGNORECASE
    )
    for requirement in data["requirements"]:
        assert not forbidden_claim.search(requirement["statement"])
