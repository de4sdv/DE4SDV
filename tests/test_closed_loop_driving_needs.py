"""Content pins for the closed-loop driving stakeholder needs (phase 4), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
CONTEXT = DRIVING / "closed_loop_driving_operational_context.sysml"
MODEL = DRIVING / "closed_loop_driving_needs_requirements.sysml"
PACKAGE = "DE4SDV_ClosedLoopDrivingNeedsRequirements"
CONTEXT_PACKAGE = "DE4SDV_ClosedLoopDrivingOperationalContext"
SYSTEM_OF_INTEREST = "DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem"
CHECKPOINT_PIN = "cb50764b"

#: Each need: its short name, the stakeholder roles that hold it, and the phase 1 concern its source
#: names. The stakeholders are those of that concern, so the need traces to the concern through both.
NEEDS = {
    "needCheckpointPlansMoveTheVehicle": (
        "NEED-DRIVING-001", {"SystemsEngineer", "VerificationEngineer", "OpenSourceReviewer"},
        "checkpointCommandAuthorityConcern"),
    "needCheckpointInputsAsTrained": (
        "NEED-DRIVING-002", {"SystemsEngineer", "VerificationEngineer"}, "checkpointCommandAuthorityConcern"),
    "needPlansAndCommandsThroughSCORE": (
        "NEED-DRIVING-003", {"SystemArchitect", "SoftwareDeveloper", "Maintainer"}, "scoreCommandPathConcern"),
    "needLiveStateForAAOS": (
        "NEED-DRIVING-004", {"VerificationEngineer", "OpenSourceReviewer"}, "aaosObservationFidelityConcern"),
    "needLoopIndependentOfAAOS": (
        "NEED-DRIVING-005", {"VerificationEngineer", "OpenSourceReviewer"}, "aaosObservationFidelityConcern"),
    "needDefinedResponseToDegradedInputOrPlan": (
        "NEED-DRIVING-006", {"SafetyExpert", "SystemArchitect"}, "degradedInputBehaviorConcern"),
    "needTimesMeasurableInTheirOwnDomain": (
        "NEED-DRIVING-007", {"VerificationEngineer", "SystemsEngineer"}, "timeDomainHonestyConcern"),
    "needRunsIdentifyCheckpointAndConfiguration": (
        "NEED-DRIVING-008", {"VerificationEngineer", "Maintainer", "OpenSourceReviewer"},
        "reproducibleClosedLoopEvidenceConcern"),
}

#: The validation plan of each need and the phase 2 use case whose run the planned review watches.
VALIDATION = {
    "needCheckpointPlansMoveTheVehicle": ("SC-DRIVING-005", "driveOnCheckpointPlans"),
    "needCheckpointInputsAsTrained": ("SC-DRIVING-006", "driveOnCheckpointPlans"),
    "needPlansAndCommandsThroughSCORE": ("SC-DRIVING-007", "driveOnCheckpointPlans"),
    "needLiveStateForAAOS": ("SC-DRIVING-008", "showLiveStateOnAAOS"),
    "needLoopIndependentOfAAOS": ("SC-DRIVING-009", "continueWithoutAAOS"),
    "needDefinedResponseToDegradedInputOrPlan": ("SC-DRIVING-010", "respondToDegradedInputOrPlan"),
    "needTimesMeasurableInTheirOwnDomain": ("SC-DRIVING-011", "driveOnCheckpointPlans"),
    "needRunsIdentifyCheckpointAndConfiguration": ("SC-DRIVING-012", "driveBoundedScenarioClosedLoop"),
}


def _raw() -> str:
    assert MODEL.is_file(), "phase 4 of INC-DRIVING-001 needs a stakeholder needs model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _need(name: str) -> str:
    short = NEEDS[name][0]
    return braced_body(_raw(), f"requirement <'{short}'> {name} : StakeholderNeedCandidate")


def _attribute(body: str, attribute: str) -> str:
    match = re.search(rf'\battribute\s+:>>\s+{attribute}\s*=\s*"([^"]*)"\s*;', body)
    assert match, f"missing {attribute}"
    return match.group(1)


def _statement(body: str) -> str:
    match = re.search(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*(.*?)\*/\s*\}', body, re.S)
    assert match, "missing the English require constraint statement"
    return _flat(match.group(1))


def test_the_needs_are_exactly_the_eight_of_phase_4_with_unique_short_names():
    code = _code()
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", code)
    declared = re.findall(r"\brequirement\s+<'([^']+)'>\s+(\w+)\s*:\s*StakeholderNeedCandidate\b", code)
    assert declared == [(short, name) for name, (short, _roles, _concern) in NEEDS.items()]
    elsewhere = [path.name for path in DRIVING.glob("*.sysml") if path != MODEL
                 and re.search(r"<'NEED-DRIVING-\d{3}'>", path.read_text(encoding="utf-8"))]
    assert not elsewhere, f"NEED-DRIVING short names are declared only here: {elsewhere}"


def test_each_need_has_statement_stakeholders_source_rationale_and_the_system_of_interest():
    # The ElaborateNeeds rules: needHasStatement, needHasStakeholder, needHasSource, needHasRationale,
    # and the advisory needSubjectIsSystemOfInterest (the charter's systemOfInterest, never the increment).
    for name, (short, roles, concern) in NEEDS.items():
        body = _need(name)
        assert re.search(rf"\bsubject\s+\w+\s*:>\s*{re.escape(SYSTEM_OF_INTEREST)}\s*;", body), name
        assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", strip_comments(body))) == roles, name
        assert len(_statement(body)) > 80, name
        source = _attribute(body, "source")
        assert source.startswith(f"INC-DRIVING-001 {concern}"), (name, source)
        assert len(_attribute(body, "rationale")) > 60, name


def test_every_non_boundary_concern_of_phase_1_has_a_need():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    concerns = {name for name, kind in re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", framing)
                if kind != "IncrementBoundaryConcern"}
    assert len(concerns) == 6
    assert {concern for _short, _roles, concern in NEEDS.values()} == concerns
    for name, (_short, roles, concern) in NEEDS.items():
        holders = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", braced_body(framing, f"concern {concern} :")))
        assert roles <= holders, (name, roles - holders)


def test_each_need_has_a_planned_review_on_a_phase_2_scenario():
    code = _code()
    raw = _raw()
    context = strip_comments(CONTEXT.read_text(encoding="utf-8"))
    associations = re.findall(r"\bconnection\s+\w+\s*:\s*ValidationPlanningAssociation\s+connect\s+(\w+)\s+to\s+(\w+)\s*;",
                              code)
    plans = dict(re.findall(r"\bpart\s+<'(SC-DRIVING-\d{3})'>\s+(\w+)\s*:\s*ValidationPlanningScenario\b", code))
    assert sorted(plans) == sorted(short for short, _use_case in VALIDATION.values())
    dependencies = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
    for need, (plan_short, use_case) in VALIDATION.items():
        plan = plans[plan_short]
        assert associations.count((need, plan)) == 1, (need, plan)
        doc = _flat(braced_body(raw, f"part <'{plan_short}'> {plan} : ValidationPlanningScenario"))
        assert f"For {NEEDS[need][0]}, a planned stakeholder review." in doc, plan
        assert (plan, f"{CONTEXT_PACKAGE}::{use_case}") in dependencies, (plan, use_case)
        assert re.search(rf"\buse\s+case\s+{use_case}\b", context), use_case
    assert len(associations) == len(NEEDS), "one planned review per need"
    # Phase 2 owns SC-DRIVING-001 to SC-DRIVING-004; the planned reviews continue the numbering.
    assert not re.search(r"<'SC-DRIVING-00[1-4]'>", code)


def test_the_inputs_need_names_the_runtime_contract_of_the_pinned_checkpoint():
    body = _need("needCheckpointInputsAsTrained")
    statement = _statement(body)
    for item in ("camera images", "calibration", "ego-motion history", "map", "route", "aligned in time"):
        assert item in statement, item
    source = _attribute(body, "source")
    assert CHECKPOINT_PIN in source and "Model/README.md" in source and "egomotion.py" in source
    assert "gapModelInputAndFeedback" in source and "asmSourceAuthenticity" in source


def test_the_need_texts_make_no_claim_the_charter_excludes():
    # roadDeploymentOutOfScope and the phase 3 boundary: no safety, certification or on-road claim, and
    # no member product. The degraded-input need says the response carries no safety claim.
    text = " ".join(_statement(_need(name)) + " " + _attribute(_need(name), "rationale") for name in NEEDS)
    assert not re.search(r"\b(certif\w*|homologat\w*|on-road|member product|UNECE|R152)\b", text, re.I)
    assert "no safety claim" in _attribute(_need("needDefinedResponseToDegradedInputOrPlan"), "rationale")


def test_two_tables_frame_the_needs_concern_and_show_needs_and_planned_reviews():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*StakeholderNeedsConcern\b", code)
    assert len(concerns) == 1
    concern = braced_body(code, f"concern {concerns[0]} : StakeholderNeedsConcern")
    assert re.search(r"\bsubject\s*;", concern)
    views = re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
    assert len(views) == 2
    exposed = {}
    for view in views:
        body = braced_body(code, f"view {view} : TVD::TableView")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*StakeholderRequirementDefinitionViewpoint\s*\{{\s*frame\s+{concerns[0]}\s*;",
                         body), view
        exposed[view] = re.findall(r"\bexpose\s+([^;]+);", body)
    plans = [plan for plan in re.findall(r"\bpart\s+<'SC-DRIVING-\d{3}'>\s+(\w+)\s*:", code)]
    assert sorted(exposed.values()) == sorted([list(NEEDS), plans])
    needs_view = next(view for view, names in exposed.items() if names == list(NEEDS))
    plans_view = next(view for view, names in exposed.items() if names == plans)
    needs_body = braced_body(code, f"view {needs_view} : TVD::TableView")
    assert re.search(r'CT::attributeValue\s*\{\s*attribute\s+attributeName\s*=\s*"source"\s*;', needs_body), \
        "the needs table shows each source"
    # The licensed render of the first push clipped every ID to "NEED-DRIVING-00" at the default width.
    id_column = re.search(r"\bview\s+ID\s*:>\s*columnViews\s*\{([^}]*)\}", needs_body)
    assert id_column and "CT::reqId" in id_column.group(1)
    width = re.search(r"columnWidth\s*=\s*(\d+)\s*;", id_column.group(1))
    assert width and int(width.group(1)) >= 150, "the ID column must fit NEED-DRIVING-001"
    # The same render left CT::reqId empty for the planned reviews, which are part usages: no ID column there.
    assert "CT::reqId" not in braced_body(code, f"view {plans_view} : TVD::TableView")


def test_no_source_holds_a_path_too_long_to_wrap_in_its_table_column():
    # The first render ran Model/data_parsing/nvidia_physical_ai/egomotion.py past the Source column edge.
    for name in NEEDS:
        longest = max(re.split(r"[\s(]+", _attribute(_need(name), "source")), key=len)
        assert len(longest) <= 40, (name, longest)
