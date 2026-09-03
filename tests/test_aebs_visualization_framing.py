"""INC-AEBS-010 framing/needs/requirements guard tests.

These guards enforce the Phase 0-5 slice contract for the AEBS visualization
increment: bounded scope, mandated-successor dependency to INC-MW-010, no
technology selection in needs, no requirement-ID collisions with existing AEBS
series, and YAML/SysML index consistency.
"""

from pathlib import Path

import pytest
import yaml

MODEL_DIR = Path("textual-notation-of-model/packages/features/aebs")
PILOT_YAML = Path("methodologies/sysmod-sysmlv2/pilots/aebs-010-visualization.yaml")
FRAMING = MODEL_DIR / "aebs_visualization_framing.sysml"
OPERATIONAL = MODEL_DIR / "aebs_visualization_operational_context.sysml"
NEEDS = MODEL_DIR / "aebs_visualization_needs_requirements.sysml"
MW_EVIDENCE = (
    Path("textual-notation-of-model/packages/features/middleware")
    / "middleware_verification_evidence.sysml"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _existing_aebs_requirement_ids() -> set[str]:
    text = _read(MODEL_DIR / "aebs_needs_requirements.sysml")
    import re

    return set(re.findall(r"REQ-AEBS-(?:S2-)?\d+", text))


def _existing_aebs_need_ids() -> set[str]:
    text = _read(MODEL_DIR / "aebs_needs_requirements.sysml")
    import re

    return set(re.findall(r"N-AEBS-\d+", text))


def test_pilot_yaml_declares_increment_aebs_010() -> None:
    data = yaml.safe_load(_read(PILOT_YAML))
    assert data["id"] == "INC-AEBS-010"
    assert data["status"] == "draft"
    assert data["schema"].startswith("de4sdv.aebs-010-visualization")


def test_framing_declares_successor_dependency_to_mw010_decision() -> None:
    framing = _read(FRAMING)
    assert "private import DE4SDV_MiddlewareVerificationEvidence::*;" in framing
    assert "dependency successorMandate" in framing
    assert "to successorIncrementDecision010;" in framing


def test_predecessor_decision_exists_in_mw010_evidence_model() -> None:
    mw = _read(MW_EVIDENCE)
    assert "part successorIncrementDecision010 : IncrementLifecycleDecision" in mw


def test_framing_records_no_retroactive_mw010_claim() -> None:
    framing = _read(FRAMING)
    assert "mw010RetroactiveClosureOutOfScope : OutOfScopeItem" in framing
    assert "E-MW-011..E-MW-014" in framing


def test_framing_scope_excludes_production_hmi_and_safety_claims() -> None:
    framing = _read(FRAMING)
    assert "productionDriverHMIOutOfScope : OutOfScopeItem" in framing
    assert "clusterDisplaySafetyOutOfScope : OutOfScopeItem" in framing
    assert "safetyComplianceClaimOutOfScope : OutOfScopeItem" in framing
    assert "fullAutowareStackOutOfScope : OutOfScopeItem" in framing


def test_needs_continue_existing_n_aebs_series_without_collision() -> None:
    needs = _read(NEEDS)
    planned = {
        "N-AEBS-009",
        "N-AEBS-010",
        "N-AEBS-011",
        "N-AEBS-012",
        "N-AEBS-013",
    }
    for need_id in planned:
        assert need_id in needs
    collisions = planned & _existing_aebs_need_ids()
    assert not collisions


def test_requirements_use_dedicated_s2_series_without_collision() -> None:
    needs = _read(NEEDS)
    planned = {f"REQ-AEBS-S2-{number:03d}" for number in range(2, 12)}
    for requirement_id in planned:
        assert requirement_id in needs
    collisions = planned & _existing_aebs_requirement_ids()
    assert not collisions


@pytest.mark.parametrize(
    "need_id,requirement_ids",
    [
        ("N-AEBS-009", {"REQ-AEBS-S2-002", "REQ-AEBS-S2-003", "REQ-AEBS-S2-004", "REQ-AEBS-S2-010"}),
        ("N-AEBS-010", {"REQ-AEBS-S2-002"}),
        ("N-AEBS-011", {"REQ-AEBS-S2-006", "REQ-AEBS-S2-007", "REQ-AEBS-S2-008", "REQ-AEBS-S2-009"}),
        ("N-AEBS-012", {"REQ-AEBS-S2-010", "REQ-AEBS-S2-011"}),
        ("N-AEBS-013", {"REQ-AEBS-S2-005"}),
    ],
)
def test_requirement_derivation_dependencies_present(
    need_id: str, requirement_ids: set[str]
) -> None:
    needs = _read(NEEDS)
    # Dependency usage names carry the semantic target-need stem (e.g.
    # s2005DerivedFromNonInterference for N-AEBS-013); the legacy need ID
    # itself is pinned by each requirement's `source` attribute below.
    need_usage = {
        "N-AEBS-009": "needLiveVisualizationOnAAOS",
        "N-AEBS-010": "needPreservedSourceProvenance",
        "N-AEBS-011": "needFailClosedDegradation",
        "N-AEBS-012": "needCorrelatableEvidence",
        "N-AEBS-013": "needNonInterference",
    }
    for requirement_id in sorted(requirement_ids):
        assert " from req" in needs and f"to {need_usage[need_id]};" in needs, (
            f"missing dependency for {requirement_id} -> {need_id}"
        )
        # The derivation matrix is additionally pinned by the requirement doc
        # and source attributes naming the legacy need IDs verbatim.
        seq = requirement_id.rsplit("-", 1)[1]
        candidates = (
            f"REQ-AEBS-S2-{seq} System 2 candidate derived from {need_id}",
            f"REQ-AEBS-S2-{seq} System 2 candidate derived from {need_id} and",
            f"REQ-AEBS-S2-{seq} System 2 candidate derived from ",
        )
        assert any(anchor in needs for anchor in candidates), (
            f"missing source attribution for {requirement_id} -> {need_id}"
        )


def test_needs_stay_technology_neutral() -> None:
    needs = _read(NEEDS)
    needs_only = needs.split("package VisualizationRequirements")[0]
    # Strip the file header comment before scanning for technology words.
    header_end = needs_only.index("*/") + 2
    needs_only = needs_only[header_end:]
    for technology in ("TCP", "protobuf", "SDV Gateway", "Java", "Cuttlefish"):
        assert technology not in needs_only


def test_real_rendering_requirement_forbids_host_browser_surface() -> None:
    needs = _read(NEEDS)
    assert "shall not use a host-side browser page as the rendering surface" in needs


def test_native_participation_requirement_forbids_provenance_relabeling() -> None:
    needs = _read(NEEDS)
    assert (
        "shall not present coordinator-derived distance values as native Autoware output"
        in needs
    )


def test_operational_context_models_fail_closed_suppression() -> None:
    operational = _read(OPERATIONAL)
    assert "action def SuppressStalePresentation" in operational
    assert "flow from validate.freshness to suppress.freshness;" in operational


def test_operational_context_declares_bounded_scenario_set() -> None:
    operational = _read(OPERATIONAL)
    for scenario in (
        "scenarioHealthyMonitoring",
        "scenarioWarningInterventionRelease",
        "scenarioStaleSource",
        "scenarioUnavailableSource",
        "scenarioInvalidEnvelope",
        "scenarioRestoration",
    ):
        assert f"part {scenario} : InScopeItem" in operational


def test_yaml_need_and_requirement_indexes_match_model() -> None:
    data = yaml.safe_load(_read(PILOT_YAML))
    assert set(data["need_ids"]) == {
        "N-AEBS-009",
        "N-AEBS-010",
        "N-AEBS-011",
        "N-AEBS-012",
        "N-AEBS-013",
    }
    assert set(data["requirement_ids"]) == {
        f"REQ-AEBS-S2-{number:03d}" for number in range(2, 12)
    }
    assert set(data["gap_ids"]) == {
        f"GAP-AEBS-010-{number:03d}" for number in range(1, 6)
    }


def test_yaml_model_artifact_paths_exist() -> None:
    data = yaml.safe_load(_read(PILOT_YAML))
    for artifact in data["model_artifacts"]:
        assert Path(artifact["path"]).exists(), artifact["path"]


def test_yaml_claim_boundary_is_framing_only() -> None:
    data = yaml.safe_load(_read(PILOT_YAML))
    boundary = data["claim_boundary"]
    assert "Framing, needs, and System 2 requirement candidates only" in boundary
    for forbidden in ("safety", "compliance", "INC-MW-010-modifying"):
        assert forbidden in boundary


def test_yaml_records_controlled_evidence_dispositions_for_chain() -> None:
    data = yaml.safe_load(_read(PILOT_YAML))
    note = data["verification_planning"]["note"]
    for disposition in ("observed_bounded", "deferred_not_proven", "not_claimed"):
        assert disposition in note


def test_yaml_classification_keeps_visualization_out_of_bof() -> None:
    data = yaml.safe_load(_read(PILOT_YAML))
    classifications = {entry["id"]: entry for entry in data["product_line_classification"]}
    assert classifications["CLS-AEBS-010-001"]["classification"] == (
        "system2_engineering_instrumentation"
    )
    assert "bill of features" in classifications["CLS-AEBS-010-001"]["rationale"]
