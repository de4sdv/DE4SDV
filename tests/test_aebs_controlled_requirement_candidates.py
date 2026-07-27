import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
YAML_PATH = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml"
MARKDOWN_PATH = ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md"
MODEL_PATH = ROOT / "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"

EXPECTED_SYSTEM1_PRODUCT_LINE_NEEDS = {
    "N-AEBS-001",
    "N-AEBS-006",
    "N-AEBS-007",
}
EXPECTED_SYSTEM1_MEMBER_NEEDS = {
    "N-AEBS-008",
}
EXPECTED_SYSTEM1_NEEDS = EXPECTED_SYSTEM1_PRODUCT_LINE_NEEDS | EXPECTED_SYSTEM1_MEMBER_NEEDS
EXPECTED_SYSTEM1_REQUIREMENTS = {
    "REQ-AEBS-001",
    "REQ-AEBS-002",
    "REQ-AEBS-003",
    "REQ-AEBS-004",
    "REQ-AEBS-005",
    "REQ-AEBS-008",
    "REQ-AEBS-009",
    "REQ-AEBS-010",
    "REQ-AEBS-011",
    "REQ-AEBS-012",
    "REQ-AEBS-013",
    "REQ-AEBS-014",
    "REQ-AEBS-015",
}
EXPECTED_SYSTEM2_NEEDS = {
    "N-AEBS-002",
    "N-AEBS-003",
    "N-AEBS-004",
    "N-AEBS-005",
}
EXPECTED_SYSTEM2_REQUIREMENTS = {
    "REQ-AEBS-006",
    "REQ-AEBS-007",
    "REQ-AEBS-S2-001",
}


def _load():
    return yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))


def test_system_sets_are_aligned_across_control_artifacts():
    data = _load()
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    model = MODEL_PATH.read_text(encoding="utf-8")

    need_ids = {item["id"] for item in data["needs"]}
    requirement_ids = {item["id"] for item in data["requirements"]}
    expected_needs = EXPECTED_SYSTEM1_NEEDS | EXPECTED_SYSTEM2_NEEDS
    expected_requirements = EXPECTED_SYSTEM1_REQUIREMENTS | EXPECTED_SYSTEM2_REQUIREMENTS
    assert expected_needs <= need_ids
    assert expected_requirements <= requirement_ids

    sets = {item["id"]: item for item in data["controlled_sets"]}
    assert set(sets["SET-AEBS-S1-NEEDS"]["members"]) == EXPECTED_SYSTEM1_PRODUCT_LINE_NEEDS
    assert sets["SET-AEBS-S1-NEEDS"]["entity"] == "SDV product line"
    assert set(sets["SET-AEBS-S1-MEMBER-NEEDS"]["members"]) == EXPECTED_SYSTEM1_MEMBER_NEEDS
    assert sets["SET-AEBS-S1-MEMBER-NEEDS"]["entity"] == "SDV product-line member product"
    assert set(sets["SET-AEBS-S1-REQS"]["members"]) == EXPECTED_SYSTEM1_REQUIREMENTS
    assert set(sets["SET-AEBS-S2-NEEDS"]["members"]) == EXPECTED_SYSTEM2_NEEDS
    assert set(sets["SET-AEBS-S2-REQS"]["members"]) == EXPECTED_SYSTEM2_REQUIREMENTS
    assert sets["SET-AEBS-S2-NEEDS"]["entity"] == "DE4SDV AEBS increment"
    assert sets["SET-AEBS-S2-REQS"]["entity"] == "DE4SDV AEBS increment"

    for record_id in expected_needs | expected_requirements:
        assert f"`{record_id}`" in markdown
        assert record_id in model
    assert "package System1Product" in model
    assert "package System2EngineeringAssurance" in model


def test_product_requirements_have_only_system1_need_parents():
    data = _load()
    requirements = {item["id"]: item for item in data["requirements"]}
    for record_id in EXPECTED_SYSTEM1_REQUIREMENTS:
        assert set(requirements[record_id]["derived_from"]) <= EXPECTED_SYSTEM1_NEEDS
    assert requirements["REQ-AEBS-004"]["derived_from"] == ["N-AEBS-001"]
    assert requirements["REQ-AEBS-009"]["derived_from"] == ["N-AEBS-008"]
    assert requirements["REQ-AEBS-013"]["derived_from"] == ["N-AEBS-008"]
    assert requirements["REQ-AEBS-S2-001"]["derived_from"] == ["N-AEBS-002"]


def test_split_candidates_each_contain_one_normative_response():
    requirements = {item["id"]: item for item in _load()["requirements"]}
    split_pairs = {
        "REQ-AEBS-008": ("warning", "braking"),
        "REQ-AEBS-012": ("braking", "warning"),
        "REQ-AEBS-009": ("state", "indication"),
        "REQ-AEBS-013": ("indication", "enter"),
        "REQ-AEBS-010": ("detect", "apply"),
        "REQ-AEBS-014": ("response", "detect"),
        "REQ-AEBS-011": ("detect", "apply"),
        "REQ-AEBS-015": ("response", "detect"),
    }
    for record_id, (included, excluded) in split_pairs.items():
        statement = requirements[record_id]["statement"].lower()
        assert included in statement, record_id
        assert excluded not in statement, record_id
        assert requirements[record_id]["maturity"] == "draft_requirement_with_gap"


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


def test_regulatory_source_aggregate_exactly_matches_explicit_record_links():
    data = _load()
    linked = {
        record["id"]
        for section in ("needs", "requirements")
        for record in data[section]
        if "SRC-UNECE-R152" in record.get("source_links", [])
    }
    aggregates = [
        trace
        for trace in data["traceability"]
        if trace["from"] == "SRC-UNECE-R152"
        and trace["relation"] == "constrains_scope_of"
    ]
    assert len(aggregates) == 1
    targets = aggregates[0]["to"]
    assert len(targets) == len(set(targets))
    assert set(targets) == linked
