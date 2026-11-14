"""Content pins for the driver-assistance stakeholder needs (INC-DRIVING-002, phase 4), not semantic validation.

Each need is held by the parties it serves, leads its source with the phase 1 concern it derives from, and has
one planned stakeholder review on a phase 2 use case. The roles that check the answer stay on the reviews. The
tests read the model text; they do not parse SysML.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import braced_body, charter_package_files, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
CONTEXT = DRIVING / "driver_assistance_operational_context.sysml"
MODEL = DRIVING / "driver_assistance_needs_requirements.sysml"
GUIDE = ROOT / "docs/guides/driver-assistance-increment.md"
PACKAGE = "DE4SDV_DriverAssistanceNeedsRequirements"
CONTEXT_PACKAGE = "DE4SDV_DriverAssistanceOperationalContext"
SYSTEM_OF_INTEREST = "DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem"
INCREMENT = "INC-DRIVING-002"
VISIONPILOT_PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"

#: need -> (short name, the roles that hold it, the phase 1 concern that leads its source)
NEEDS = {
    "needWarnAndBrakeForVehicleAhead": (
        "NEED-DRIVING-008", {"VehicleOccupant", "RoadUser"}, "vehicleTargetResponseConcern"),
    "needNoReactionWithoutImminentCollision": (
        "NEED-DRIVING-009", {"VehicleOccupant", "RoadUser"}, "vehicleTargetResponseConcern"),
    "needWarningRequestForTheDriver": (
        "NEED-DRIVING-010", {"VehicleOccupant"}, "driverWarningSequenceConcern"),
    "needCommandsAndWarningThroughSCORE": (
        "NEED-DRIVING-011", {"SystemsEngineer", "ProductLineEngineer"}, "scoreCommandAndWarningPathConcern"),
    "needRunsIdentifyTheCandidate": (
        "NEED-DRIVING-012", {"VerificationEngineer", "ProductLineEngineer"}, "candidateVerdictConcern"),
}

#: need -> (the short name of its planned review, the phase 2 use case the review depends on)
VALIDATION = {
    "needWarnAndBrakeForVehicleAhead": ("SC-DRIVING-016", "warnAndBrakeForStationaryVehicle"),
    "needNoReactionWithoutImminentCollision": ("SC-DRIVING-017", "noReactionToStationaryVehicleBeyondTheCurve"),
    "needWarningRequestForTheDriver": ("SC-DRIVING-018", "warnAndBrakeForSlowerVehicle"),
    "needCommandsAndWarningThroughSCORE": ("SC-DRIVING-019", "warnAndBrakeForStationaryVehicle"),
    "needRunsIdentifyTheCandidate": ("SC-DRIVING-020", "noReactionToVehicleAheadTurningOff"),
}

#: reviewer-question concerns: no need of their own; a need's source names them and its planned review checks them
#: concern -> (the need whose source names it, a phrase of that need's review that checks it)
REVIEWED_CONCERNS = {
    "emergencyBrakingIndependenceConcern": (
        "needWarnAndBrakeForVehicleAhead",
        "can safety experts and product-line engineers tell which element of the candidate gave the braking "
        "command, and whether it left the candidate in the driving command or apart from it?"),
    "vehicleTargetCriteriaConcern": (
        "needWarnAndBrakeForVehicleAhead",
        "by the criteria for a vehicle target that phase 5 derives"),
}

#: the phase 1 concerns this phase reads: every non-boundary concern of the framing
PHASE1_CONCERNS = {
    "vehicleTargetResponseConcern", "emergencyBrakingIndependenceConcern", "driverWarningSequenceConcern",
    "scoreCommandAndWarningPathConcern", "vehicleTargetCriteriaConcern", "candidateVerdictConcern",
}

#: wording the charter excludes from a need: approval, admission, a member product, on-road use, a result
EXCLUDED = re.compile(r"(?i)\b(?:certif\w*|homologat\w*|complian\w*|complies|approv\w*|type.approv\w*|admi(?:t|ss)\w*|"
                      r"on-road|member products?|UNECE|R152|passe[sd]|fail(?:s|ed))\b")
#: functions that run but that no case judges: no need of their own and no words in a need
UNJUDGED = re.compile(r"(?i)\b(?:speed-following|lane-keeping|lane keeping|lane-departure|cruise)\b")
#: an anti-cheating clause belongs to a planned review's question, not to a need
ANTI_CHEATING = re.compile(r"(?i)\b(?:autopilot|replay\w*|overlay\w*|recording|acts? instead|stands? in)\b")
#: a value with a unit is phase 5's, derived with its provenance; a need states none
NUMBER_WITH_UNIT = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:ms|s|m|km/h|m/s|m/s2|m/s²|g|Hz|%|px|mm|°)(?![\w/])")


def _raw() -> str:
    assert MODEL.is_file(), "phase 4 of INC-DRIVING-002 needs a stakeholder needs model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _need(name: str) -> str:
    return braced_body(_raw(), f"requirement <'{NEEDS[name][0]}'> {name} : StakeholderNeedCandidate")


def _attribute(body: str, attribute: str) -> str:
    match = re.search(rf'\battribute\s+:>>\s+{attribute}\s*=\s*"([^"]*)"\s*;', body)
    assert match, f"missing {attribute}"
    return match.group(1)


def _statement(body: str) -> str:
    match = re.search(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*(.*?)\*/\s*\}', body, re.S)
    assert match, "missing the English require constraint statement"
    return _flat(match.group(1))


def _plans() -> dict[str, str]:
    return dict(re.findall(r"\bpart\s+<'(SC-DRIVING-\d{3})'>\s+(\w+)\s*:\s*ValidationPlanningScenario\b", _code()))


def _plan_doc(short: str) -> str:
    body = braced_body(_raw(), f"part <'{short}'> {_plans()[short]} : ValidationPlanningScenario")
    match = re.search(r"\bdoc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{short} has no doc"
    return _flat(match.group(1))


def _need_text(name: str) -> str:
    body = _need(name)
    return " ".join((_statement(body), _attribute(body, "source"), _attribute(body, "rationale")))


def _framing_holders(concern: str) -> set[str]:
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    return set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", braced_body(framing, f"concern {concern} :")))


def test_the_package_declares_exactly_the_needs_of_phase_4_with_unique_short_names():
    code = _code()
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", code) == [PACKAGE], "one global package per file"
    declared = re.findall(r"\brequirement\s+<'([^']+)'>\s+(\w+)\s*:\s*StakeholderNeedCandidate\b", code)
    assert declared == [(short, name) for name, (short, _roles, _concern) in NEEDS.items()]
    others = [path.name for path in charter_package_files(FRAMING, "driverAssistanceCharter") if path != MODEL
              and re.search(r"<'NEED-DRIVING-\d{3}'>", path.read_text(encoding="utf-8"))]
    assert not others, f"the needs of the increment are declared only here: {others}"
    # NEED-DRIVING-001 to 007 belong to INC-DRIVING-001; this increment continues the numbering.
    assert not re.search(r"<'NEED-DRIVING-00[1-7]'>", code)


def test_each_need_has_a_statement_its_holders_a_source_a_rationale_and_the_system_of_interest():
    # The ElaborateNeeds gates: needHasStatement, needHasStakeholder, needHasSource, needHasRationale, and the
    # advisory needSubjectIsSystemOfInterest (the charter's systemOfInterest, never the increment).
    for name, (_short, roles, concern) in NEEDS.items():
        body = _need(name)
        assert re.search(rf"\bsubject\s+\w+\s*:>\s*{re.escape(SYSTEM_OF_INTEREST)}\s*;", body), name
        assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", strip_comments(body))) == roles, name
        assert len(_statement(body)) > 80, name
        source = _attribute(body, "source")
        assert source.startswith(f"{INCREMENT} {concern},"), (name, source)
        assert len(_attribute(body, "rationale")) > 60, name


def test_each_need_is_held_by_holders_of_its_first_source_concern():
    for name, (_short, roles, concern) in NEEDS.items():
        first = re.findall(r"\b(\w+Concern)\b", _attribute(_need(name), "source"))[0]
        assert first == concern, (name, first)
        assert roles <= _framing_holders(concern), (name, roles - _framing_holders(concern))


def test_every_non_boundary_concern_of_phase_1_is_named_in_a_source():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    concerns = {name for name, kind in re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", framing)
                if kind != "IncrementBoundaryConcern"}
    assert concerns == PHASE1_CONCERNS
    named = set()
    for name in NEEDS:
        named.update(re.findall(r"\b(\w+Concern)\b", _attribute(_need(name), "source")))
    assert concerns <= named, sorted(concerns - named)
    assert named <= concerns, sorted(named - concerns)


def test_a_reviewer_question_concern_is_named_by_a_need_and_checked_by_its_review():
    leading = {concern for _short, _roles, concern in NEEDS.values()}
    for concern, (need, phrase) in REVIEWED_CONCERNS.items():
        assert concern not in leading, f"{concern} is a reviewer question and leads no need"
        assert concern in _attribute(_need(need), "source"), (concern, need)
        assert phrase in _plan_doc(VALIDATION[need][0]), (concern, phrase)


def test_each_need_has_one_planned_review_on_a_phase_2_use_case():
    code = _code()
    context = strip_comments(CONTEXT.read_text(encoding="utf-8"))
    plans = _plans()
    assert sorted(plans) == sorted(short for short, _use_case in VALIDATION.values())
    associations = re.findall(
        r"\bconnection\s+\w+\s*:\s*ValidationPlanningAssociation\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    dependencies = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
    for need, (plan_short, use_case) in VALIDATION.items():
        plan = plans[plan_short]
        assert associations.count((need, plan)) == 1, (need, plan)
        assert _plan_doc(plan_short).startswith(f"For {NEEDS[need][0]}, a planned stakeholder review."), plan
        assert [target for source, target in dependencies if source == plan] == [f"{CONTEXT_PACKAGE}::{use_case}"], \
            (plan, use_case)
        assert re.search(rf"\buse\s+case\s+{use_case}\s*\{{", context), use_case
    assert len(associations) == len(NEEDS), "one planned review per need"
    # Phase 2 owns SC-DRIVING-012 to SC-DRIVING-015; the planned reviews continue the numbering.
    assert not re.search(r"<'SC-DRIVING-0(?:0\d|1[0-5])'>", code)


def test_each_planned_review_names_the_scenario_it_watches():
    scenarios = {
        "warnAndBrakeForStationaryVehicle": "SC-DRIVING-012",
        "warnAndBrakeForSlowerVehicle": "SC-DRIVING-013",
        "noReactionToStationaryVehicleBeyondTheCurve": "SC-DRIVING-014",
        "noReactionToVehicleAheadTurningOff": "SC-DRIVING-015",
    }
    for plan_short, use_case in VALIDATION.values():
        doc = _plan_doc(plan_short)
        assert f"({scenarios[use_case]})" in doc, (plan_short, use_case)
        assert doc.count("?") >= 1, f"{plan_short} asks its question"


def test_no_need_uses_excluded_wording_an_unjudged_function_or_an_anti_cheating_clause():
    for name in NEEDS:
        text = _need_text(name)
        assert not EXCLUDED.findall(text), (name, EXCLUDED.findall(text))
        assert not UNJUDGED.findall(text), (name, UNJUDGED.findall(text))
        assert not ANTI_CHEATING.findall(_statement(_need(name))), (name, ANTI_CHEATING.findall(text))
    # the clause is a question of the planned reviews that watch the warning and the braking
    assert "and that no autopilot, replay or overlay acts instead of the candidate?" in _plan_doc("SC-DRIVING-016")
    assert "with no recording or overlay in place of either mode?" in _plan_doc("SC-DRIVING-018")


def test_no_need_states_a_number_with_a_unit():
    # The thresholds, the timing of the warning before the braking and the other limits are phase 5's.
    for name in NEEDS:
        text = _flat(_need(name))
        assert not NUMBER_WITH_UNIT.findall(text), (name, NUMBER_WITH_UNIT.findall(text))
    for name in ("needWarnAndBrakeForVehicleAhead", "needNoReactionWithoutImminentCollision",
                 "needWarningRequestForTheDriver"):
        assert "Phase 5" in _attribute(_need(name), "rationale"), f"{name}: the rationale leaves its limits to phase 5"


def test_the_need_statements_say_what_their_holders_expect():
    statements = {name: _statement(_need(name)) for name in NEEDS}
    for phrase, name in (
            ("Vehicle occupants and road users need the driver-assistance system to request the collision warning "
             "and to command the braking of the vehicle when a collision with a stationary or a slower moving "
             "vehicle ahead in its lane is imminent.", "needWarnAndBrakeForVehicleAhead"),
            ("Vehicle occupants and road users need the driver-assistance system to request no collision warning "
             "and to command no emergency braking when no collision with a vehicle ahead is imminent",
             "needNoReactionWithoutImminentCollision"),
            ("so that the AAOS SDV warns the driver on its display and as a sound", "needWarningRequestForTheDriver"),
            ("through Eclipse S-CORE, with no exchange on either path that goes around it",
             "needCommandsAndWarningThroughSCORE"),
            ("to identify the candidate revision and the configuration it ran with", "needRunsIdentifyTheCandidate")):
        assert phrase in statements[name], (name, phrase)


def test_the_input_contract_is_a_comment_for_phase_5_not_a_need():
    raw = _raw()
    match = re.search(r"\bcomment\s+(\w+)\s+about\s+([\w,\s]+?)\s*/\*(.*?)\*/", raw, re.S)
    assert match, "the pinned input contract is kept as a comment about the needs it serves"
    targets = [target.strip() for target in match.group(2).split(",")]
    assert targets == ["needWarnAndBrakeForVehicleAhead", "needWarningRequestForTheDriver"], targets
    comment = _flat(match.group(3))
    for phrase in (f"commit {VISIONPILOT_PIN}",
                   "VisionPilot/app/vision_pilot.cpp:117, 142, 174",
                   "ENABLE_ROS2_INTERFACE, VisionPilot/app/vision_pilot.cpp:59-64",
                   "VisionPilot/modules/sensing/vehicle_interface/src/file_interface.cpp:37-61",
                   "VisionPilot/modules/sensing/vehicle_interface/src/can_interface.cpp:4-12",
                   "only the ROS 2 build gives a real speed and commands a vehicle",
                   "VisionPilot/modules/safety_guardian/planning/src/planning.cpp:113-121"):
        assert phrase in comment, phrase
    assert not re.search(r"-?\d+\.\d+\s*(?:m/s|<|<=)", comment), "the comment states no threshold of the planner"


def test_two_tables_frame_the_needs_concern_and_show_needs_and_planned_reviews():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*StakeholderNeedsConcern\b", code)
    assert len(concerns) == 1
    concern = braced_body(code, f"concern {concerns[0]} : StakeholderNeedsConcern")
    assert re.search(r"\bsubject\s*;", concern)
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == {"SystemsEngineer", "ProductLineEngineer"}
    views = re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
    assert len(views) == 2
    exposed = {}
    for view in views:
        body = braced_body(code, f"view {view} : TVD::TableView")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*StakeholderRequirementDefinitionViewpoint\s*\{{\s*frame\s+"
                         rf"{concerns[0]}\s*;\s*\}}", body), view
        assert "attribute :>> includeReferenceElements = true;" in body, view
        exposed[view] = re.findall(r"\bexpose\s+([^;]+);", body)
    plan_names = list(_plans().values())
    needs_view = next(view for view, names in exposed.items() if names == list(NEEDS))
    plans_view = next(view for view, names in exposed.items() if names == plan_names)
    needs_body = braced_body(code, f"view {needs_view} : TVD::TableView")
    assert "filter @ SysML::RequirementUsage;" in needs_body
    assert re.search(r"\bview\s+ID\s*:>\s*columnViews\s*\{[^}]*CT::reqId\s*;", needs_body)
    assert re.search(r'CT::constraintLanguage\s*\{\s*attribute\s+constraintName\s*=\s*"statement"\s*;', needs_body)
    assert re.search(r'CT::attributeValue\s*\{\s*attribute\s+attributeName\s*=\s*"source"\s*;', needs_body)
    plans_body = braced_body(code, f"view {plans_view} : TVD::TableView")
    assert "filter @ SysML::PartUsage;" in plans_body
    assert "CT::documentation;" in plans_body and "CT::reqId" not in plans_body


def test_the_charter_lists_the_needs_package():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    charter = braced_body(framing, "part driverAssistanceCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-1] == PACKAGE
    assert MODEL in charter_package_files(FRAMING, "driverAssistanceCharter")


def test_the_guide_has_a_phase_4_section_and_names_phase_5_next():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## Capability classification (Phase 3)") < guide.index("## Stakeholder needs (Phase 4)") \
        < guide.index("## What the framing already records as open")
    section = " ".join(guide.split("## Stakeholder needs (Phase 4)", 1)[1].split("\n## ", 1)[0].split())
    for short, _roles, _concern in NEEDS.values():
        assert short in section, short
    for plan_short, _use_case in VALIDATION.values():
        assert plan_short in section, plan_short
    assert "tests/test_driver_assistance_needs_requirements.py" in section
    flat = " ".join(guide.split())  # Markdown: a line may open with bold text, which _flat would strip
    assert "The next model obligation is **Phase 5**: the requirements" in flat
    assert "its first gate is `requirementHasStatement`" in flat
