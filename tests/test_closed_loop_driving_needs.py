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

#: Each need: its short name, the stakeholder roles that hold it, and the FIRST phase 1 concern its
#: source names. A need is held by the parties it serves, so each role set is a subset of the
#: stakeholders of that concern; the roles that check the answer stay on the planned reviews.
NEEDS = {
    "needDrivenAlongTheRoute": (
        "NEED-DRIVING-001", {"VehicleOccupant"}, "drivenAlongTheRouteConcern"),
    "needPlansAndCommandsThroughSCORE": (
        "NEED-DRIVING-002", {"SystemArchitect", "SoftwareDeveloper", "Maintainer"}, "scoreCommandPathConcern"),
    "needLiveStateForAAOS": (
        "NEED-DRIVING-003", {"VehicleOccupant", "VerificationEngineer"}, "aaosObservationFidelityConcern"),
    "needLoopIndependentOfAAOS": (
        "NEED-DRIVING-004", {"VehicleOccupant"}, "aaosObservationFidelityConcern"),
    "needDefinedResponseToDegradedInputOrPlan": (
        "NEED-DRIVING-005", {"VehicleOccupant", "RoadUser"}, "degradedInputBehaviorConcern"),
    "needTimesMeasurableInTheirOwnDomain": (
        "NEED-DRIVING-006", {"VerificationEngineer", "SystemsEngineer"}, "timeDomainHonestyConcern"),
    "needRunsIdentifyCheckpointAndConfiguration": (
        "NEED-DRIVING-007", {"VerificationEngineer", "Maintainer", "OpenSourceReviewer"},
        "reproducibleClosedLoopEvidenceConcern"),
}

#: The validation plan of each need and the phase 2 use case whose run the planned review watches.
VALIDATION = {
    "needDrivenAlongTheRoute": ("SC-DRIVING-005", "driveOnCheckpointPlans"),
    "needPlansAndCommandsThroughSCORE": ("SC-DRIVING-006", "driveOnCheckpointPlans"),
    "needLiveStateForAAOS": ("SC-DRIVING-007", "showLiveStateOnAAOS"),
    "needLoopIndependentOfAAOS": ("SC-DRIVING-008", "continueWithoutAAOS"),
    "needDefinedResponseToDegradedInputOrPlan": ("SC-DRIVING-009", "respondToDegradedInputOrPlan"),
    "needTimesMeasurableInTheirOwnDomain": ("SC-DRIVING-010", "driveOnCheckpointPlans"),
    "needRunsIdentifyCheckpointAndConfiguration": ("SC-DRIVING-011", "driveBoundedScenarioClosedLoop"),
}

#: Wording that belongs to the review of the answer, not to the statement of what a holder expects.
REVIEW_WORDING = ("autopilot", "replay", "undisclosed", "cannot pass", "wall-clock")


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


def test_the_needs_are_exactly_the_seven_of_phase_4_with_unique_short_names():
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


def test_every_non_boundary_concern_of_phase_1_is_named_by_a_need():
    # The reviewers' command-authority question is no longer held by a need of its own: it is answered by
    # the phase 8 mapping, checked by SC-DRIVING-005, and named by NEED-DRIVING-001's source. Every other
    # non-boundary concern of phase 1 is the first-named concern of a need and is held by that need's roles.
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    concerns = {name for name, kind in re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", framing)
                if kind != "IncrementBoundaryConcern"}
    assert len(concerns) == 7
    named = set()
    for name, (_short, roles, concern) in NEEDS.items():
        source = _attribute(_need(name), "source")
        named.update(re.findall(r"\b(\w+Concern)\b", source))
        holders = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;",
                                 braced_body(framing, f"concern {concern} :")))
        assert roles <= holders, (name, roles - holders)
    assert concerns <= named, sorted(concerns - named)
    assert "checkpointCommandAuthorityConcern" in _attribute(_need("needDrivenAlongTheRoute"), "source")


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
        assert f"For {NEEDS[need][0]}, a planned stakeholder review" in doc, plan
        assert (plan, f"{CONTEXT_PACKAGE}::{use_case}") in dependencies, (plan, use_case)
        assert re.search(rf"\buse\s+case\s+{use_case}\b", context), use_case
    assert len(associations) == len(NEEDS), "one planned review per need"
    # Phase 2 owns SC-DRIVING-001 to SC-DRIVING-004; the planned reviews continue the numbering.
    assert not re.search(r"<'SC-DRIVING-00[1-4]'>", code)


def test_the_need_statements_state_what_the_holders_expect_not_how_it_is_reviewed():
    # The no-autopilot/replay/overlay condition is a check on the answer, carried by SC-DRIVING-005 and
    # turned into a verification criterion in phase 5; it is not part of what a holder states.
    for name in NEEDS:
        statement = _statement(_need(name)).lower()
        for wording in REVIEW_WORDING:
            assert wording not in statement, (name, wording)
    plan = _flat(braced_body(_raw(), "part <'SC-DRIVING-005'> checkpointAuthorityValidationPlan : ValidationPlanningScenario"))
    assert "no autopilot, replay or overlay" in plan


def test_the_route_review_names_the_checkpoint_limits_that_bear_on_its_answer():
    # The owner's decision of 2026-11-10: SC-DRIVING-005 points to the known limits of the pinned checkpoint that bear
    # on its answer, the route (GAP-DRIVING-011) and the lane (GAP-DRIVING-012). It still asks its question and does
    # not state the answer.
    plan = _flat(braced_body(_raw(), "part <'SC-DRIVING-005'> checkpointAuthorityValidationPlan : ValidationPlanningScenario"))
    assert "does the vehicle follow the route the driver chose" in plan
    assert ("Known limits that bear on the answer: the pinned checkpoint takes no turn from the route "
            "(GAP-DRIVING-011) and does not keep the vehicle in its lane (GAP-DRIVING-012).") in plan
    for verdict in ("will find", "does not follow the route", "is not met", "fails"):
        assert verdict not in plan, verdict


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
    # Phase 5 adds the requirement tables to this package; they frame the requirement trace concern.
    views = [view for view in re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
             if re.search(rf"\bframe\s+{concerns[0]}\s*;", braced_body(code, f"view {view} : TVD::TableView"))]
    assert len(views) == 2
    exposed = {}
    for view in views:
        body = braced_body(code, f"view {view} : TVD::TableView")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*StakeholderRequirementDefinitionViewpoint\s*\{{\s*frame\s+{concerns[0]}\s*;",
                         body), view
        exposed[view] = re.findall(r"\bexpose\s+([^;]+);", body)
    plan_names = [name for _short, name in re.findall(r"\bpart\s+<'(SC-DRIVING-\d{3})'>\s+(\w+)\s*:", code)]
    assert sorted(exposed.values()) == sorted([list(NEEDS), plan_names])
    needs_view = next(view for view, names in exposed.items() if names == list(NEEDS))
    plans_view = next(view for view, names in exposed.items() if names == plan_names)
    needs_body = braced_body(code, f"view {needs_view} : TVD::TableView")
    assert re.search(r'CT::attributeValue\s*\{\s*attribute\s+attributeName\s*=\s*"source"\s*;', needs_body), \
        "the needs table shows each source"
    assert re.search(r"\bview\s+ID\s*:>\s*columnViews\s*\{[^}]*CT::reqId\s*;", needs_body)
    # The licensed render of the first push left CT::reqId empty for the planned reviews, which are part
    # usages, so that table has no ID column. scripts/render_grid_csv.py sizes columns from their text and
    # never reads columnWidth, so no width is pinned here.
    assert "CT::reqId" not in braced_body(code, f"view {plans_view} : TVD::TableView")


def test_no_source_holds_a_path_too_long_to_wrap_in_its_table_column():
    # The first render ran Model/data_parsing/nvidia_physical_ai/egomotion.py past the Source column edge.
    for name in NEEDS:
        longest = max(re.split(r"[\s(]+", _attribute(_need(name), "source")), key=len)
        assert len(longest) <= 40, (name, longest)


def test_the_route_from_navigation_enters_the_route_need_and_the_degraded_response():
    # Phase 2 correction of 2026-11-02 (#476): navigation gives the route. NEED-DRIVING-001 names that
    # context role as the source of the route, and a degraded route triggers the same defined response as
    # degraded camera images or motion (SC-DRIVING-003 now names the route, reviewed by SC-DRIVING-009).
    assert "the route from the navigation context role" in _attribute(_need("needDrivenAlongTheRoute"), "source")
    degraded = _statement(_need("needDefinedResponseToDegradedInputOrPlan"))
    assert "the camera images, the motion of the vehicle or the route become invalid, lost or stale" in degraded
    plan = _flat(braced_body(_raw(), "part <'SC-DRIVING-009'> degradedResponseValidationPlan : ValidationPlanningScenario"))
    assert "camera images, motion or route" in plan


def test_the_route_need_states_the_occupants_expectation_without_naming_the_solution():
    # Owner correction of 2026-11-02: NEED-DRIVING-001 is the vehicle occupants' expectation. It names the
    # driving system's own plans, not the checkpoint that is the candidate solution, and no review wording.
    statement = _statement(_need("needDrivenAlongTheRoute"))
    assert statement.startswith("Vehicle occupants need the vehicle to take them along the route"), statement
    assert "the driving system's own plans" in statement
    assert "checkpoint" not in statement.lower() and "AutoE2E" not in statement
