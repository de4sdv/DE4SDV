"""INC-AEBS-010 framing/needs/requirements guard tests.

These guards enforce the Phase 0-5 slice contract for the AEBS visualization
increment: bounded scope, mandated-successor dependency to INC-MW-010, no
technology selection in needs, no requirement-ID collisions with existing AEBS
series, and YAML/SysML index consistency.
"""

import re
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
    return set(re.findall(r"REQ-AEBS-(?:S2-)?\d+", text))


def _existing_aebs_need_ids() -> set[str]:
    text = _read(MODEL_DIR / "aebs_needs_requirements.sysml")
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
    planned = {f"REQ-AEBS-S2-{number:03d}" for number in range(2, 22)}
    for requirement_id in planned:
        assert requirement_id in needs
    collisions = planned & _existing_aebs_requirement_ids()
    assert not collisions


@pytest.mark.parametrize(
    "need_id,requirement_ids",
    [
        (
            "N-AEBS-009",
            {
                "REQ-AEBS-S2-002",
                "REQ-AEBS-S2-003",
                "REQ-AEBS-S2-004",
                "REQ-AEBS-S2-010",
                "REQ-AEBS-S2-012",
                "REQ-AEBS-S2-013",
            },
        ),
        ("N-AEBS-010", {"REQ-AEBS-S2-002", "REQ-AEBS-S2-014"}),
        ("N-AEBS-011", {"REQ-AEBS-S2-006", "REQ-AEBS-S2-007", "REQ-AEBS-S2-008", "REQ-AEBS-S2-009"}),
        ("N-AEBS-012", {"REQ-AEBS-S2-010", "REQ-AEBS-S2-011"}),
        ("N-AEBS-013", {"REQ-AEBS-S2-005"}),
    ],
)
def test_requirement_derivations_present(
    need_id: str, requirement_ids: set[str]
) -> None:
    needs = _read(NEEDS)
    # Method rule 4: a requirement derives from a need only through the
    # governed DerivesFromNeed connection (need -> derivedRequirement); the
    # former plain dependencies were converted under the same names. Usage
    # names carry the semantic target-need stem (e.g.
    # reqNonInterferenceDerivedFromNonInterference for N-AEBS-013); the legacy need ID
    # itself is pinned by each requirement's `source` attribute below.
    need_usage = {
        "N-AEBS-009": "needLiveVisualizationOnAAOS",
        "N-AEBS-010": "needPreservedSourceProvenance",
        "N-AEBS-011": "needFailClosedDegradation",
        "N-AEBS-012": "needCorrelatableEvidence",
        "N-AEBS-013": "needNonInterference",
    }
    for requirement_id in sorted(requirement_ids):
        usage_match = re.search(
            rf"\brequirement\s+(\w+)\s*:[^{{]+\{{\s*"
            rf"doc\s*/\*\s*{re.escape(requirement_id)}\b",
            needs,
        )
        assert usage_match, f"missing requirement usage for {requirement_id}"
        requirement_usage = usage_match.group(1)
        derivation = re.search(
            rf"\bconnection\s+\w+\s*:\s*DerivesFromNeed\s+connect\s+"
            rf"{re.escape(need_usage[need_id])}\s+to\s+{re.escape(requirement_usage)}\s*;",
            needs,
        )
        assert derivation, (
            f"missing DerivesFromNeed derivation for {requirement_id} -> {need_id}"
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


# Obligations moved out of acceptance criteria AC-AEBS-S2-003..006 (owner
# decision 2026-10-09) derive from their needs through the DerivesFromNeed
# application connection, never a plain dependency.
@pytest.mark.parametrize(
    "requirement_id,need_usage",
    [
        ("REQ-AEBS-S2-015", "needNonInterference"),
        ("REQ-AEBS-S2-016", "needPreservedSourceProvenance"),
        ("REQ-AEBS-S2-017", "needPreservedSourceProvenance"),
        ("REQ-AEBS-S2-018", "needPreservedSourceProvenance"),
        ("REQ-AEBS-S2-019", "needFailClosedDegradation"),
        ("REQ-AEBS-S2-020", "needFailClosedDegradation"),
        ("REQ-AEBS-S2-021", "needFailClosedDegradation"),
    ],
)
def test_moved_criterion_obligations_derive_through_derives_from_need(
    requirement_id: str, need_usage: str
) -> None:
    needs = _read(NEEDS)
    usage_match = re.search(
        rf"\brequirement\s+(\w+)\s*:[^{{]+\{{\s*"
        rf"doc\s*/\*\s*{re.escape(requirement_id)}\b",
        needs,
    )
    assert usage_match, f"missing requirement usage for {requirement_id}"
    requirement_usage = usage_match.group(1)
    assert re.search(
        rf"\bconnection\s+\w+\s*:\s*DerivesFromNeed\s+connect\s+"
        rf"{re.escape(need_usage)}\s+to\s+{re.escape(requirement_usage)}\s*;",
        needs,
    ), f"missing DerivesFromNeed derivation for {requirement_id}"


def test_no_plain_dependency_restates_a_requirement_derivation() -> None:
    # A plain dependency from a requirement to a need would be a parallel,
    # non-counting trace next to the DerivesFromNeed connection.
    needs = _read(NEEDS)
    plain = re.findall(r"\bdependency\s+\w+\s+from\s+req\w+\s+to\s+need\w+\s*;", needs)
    assert not plain, plain


def test_soi_definition_types_the_framed_visualization_test_system() -> None:
    framing = _read(FRAMING)
    assert "part def AEBSVisualizationTestSystem :> System2EngineeringAndAssuranceSystem {" in framing
    assert "part system2VisualizationInstrument : AEBSVisualizationTestSystem {" in framing


def test_requirement_subject_is_the_visualization_test_system() -> None:
    needs = _read(NEEDS)
    requirements = needs.split("package VisualizationRequirements")[1].split("public import")[0]
    subjects = re.findall(r"\bsubject\s+([^;]+);", requirements)
    assert len(subjects) == 20
    assert set(subjects) == {"visualizationTestSystem :> system2VisualizationInstrument"}


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
    assert (
        "shall not use a host-side browser page as the AEBS rendering surface"
        in needs
    )


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
        f"REQ-AEBS-S2-{number:03d}" for number in range(2, 22)
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


def test_decision_distance_requirement_matches_the_hmi_contract() -> None:
    """REQ-AEBS-S2-018 follows the HMI contract (VISUALIZATION-CONTRACT.md
    section 13.4): the display presents no native AEB decision distance, and
    the requirement no longer asks for the removed "not visualized" row,
    which tests/test_aebs_visualization_hmi_presentation_contract.py forbids."""
    needs = _read(NEEDS)
    block = re.search(
        r"requirement reqDecisionDistanceExclusionStatement : \w+ \{.*?\n    \}", needs, re.S
    )
    assert block
    statement = re.search(r"require constraint statement \{[^}]*\}", block.group(0)).group(0)
    assert "shall present no native AEB decision distance on its rendered display" in statement
    assert "not visualized" not in statement
    contract = Path(
        "implementation/aebs-aaos-sdv-visualization-bench/VISUALIZATION-CONTRACT.md"
    ).read_text(encoding="utf-8")
    assert "boundary row is\n  removed" in contract or "boundary row is removed" in " ".join(contract.split())


# ---------------------------------------------------------------------------
# S2 validation planning and verification-method vocabulary (mirrors the S1
# guards validation_plan_population in test_w6_trace_allocation_completeness
# and test_aebs_verification_attributes; the Method Check is advisory, so
# these regressions must fail CI).
# ---------------------------------------------------------------------------

VERIFICATION_METHOD_VOCABULARY = {"inspect", "demo", "test", "analyze"}


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _brace_block(text: str, open_index: int) -> str:
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[open_index + 1:index]
    raise AssertionError("unbalanced braces")


def _s2_validation_plan_population():
    raw = _read(NEEDS)
    plans = {}
    for match in re.finditer(r"\bpart\s+(\w+)\s*:\s*ValidationPlanningScenario\s*\{", raw):
        body = _brace_block(raw, match.end() - 1)
        ids = re.match(r"\s*doc\s*/\*\s*(SC-AEBS-010-\d{2}),\s*(N-AEBS-\d{3}):", body)
        assert ids, (match[1], "planning doc must start with the SC and need identifiers")
        plans[match[1]] = (ids[1], ids[2], body)
    code = _strip_comments(raw)
    links = re.findall(
        r"\bconnection\s+(\w+)\s*:\s*ValidationPlanningAssociation\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code
    )
    assert len(links) == len(re.findall(r"\bValidationPlanningAssociation\b", code))
    needs = {}
    for match in re.finditer(r"\brequirement\s+(need\w+)\s*:\s*\w+\s*\{", raw):
        ident = re.match(r"\s*doc\s*/\*\s*(N-AEBS-\d{3})\b", _brace_block(raw, match.end() - 1))
        if ident:
            needs[match[1]] = ident[1]
    return plans, links, needs


def test_every_s2_need_has_exactly_one_planned_validation_scenario() -> None:
    plans, links, needs = _s2_validation_plan_population()
    assert len(needs) == 5 and len(plans) == 5
    data = yaml.safe_load(_read(PILOT_YAML))
    assert {sc for sc, _need, _body in plans.values()} == set(data["validation_scenario_ids"])
    per_plan, per_need = {}, {}
    for _name, need, plan in links:
        assert plan in plans and need in needs, (need, plan)
        assert needs[need] == plans[plan][1], (need, plan, "association must target the planned need")
        per_plan.setdefault(plan, []).append(need)
        per_need.setdefault(need, []).append(plan)
    assert set(per_plan) == set(plans) and all(len(v) == 1 for v in per_plan.values())
    assert set(per_need) == set(needs) and all(len(v) == 1 for v in per_need.values())


def test_s2_validation_planning_docs_claim_no_execution_result_or_acceptance() -> None:
    plans, _links, _needs = _s2_validation_plan_population()
    for name, (_sc, _need, body) in plans.items():
        text = " ".join(re.sub(r"\n\s*\*(?!/)", "\n", body).split())
        assert "No execution, result or acceptance." in text, name
        assert not re.search(r"\b(passed|validated|accepted|verdict)\b", text, re.I), name


def test_every_s2_requirement_states_one_standard_verification_method() -> None:
    """ADR 0009: verificationMethod is typed String upstream, so the
    VerificationMethodKind vocabulary is test-enforced."""
    needs = _read(NEEDS)
    requirements = needs.split("package VisualizationRequirements {", 1)[1]
    blocks = {}
    for match in re.finditer(r"\brequirement\s+(req\w+)\s*:\s*VisualizationInstrumentRequirementCandidate\s*\{", requirements):
        blocks[match[1]] = _brace_block(requirements, match.end() - 1)
    assert len(blocks) == 20
    for usage, body in blocks.items():
        methods = re.findall(r'attribute :>> verificationMethod = "(\w+)";', body)
        assert len(methods) == 1, (usage, methods)
        assert methods[0] in VERIFICATION_METHOD_VOCABULARY, (usage, methods[0])
