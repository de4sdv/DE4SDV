"""Content pins for the driver-assistance stakeholder needs (INC-DRIVING-002, phase 4), not semantic validation.

Each need is held by the parties it serves, leads its source with the phase 1 concern it derives from, and has
one planned stakeholder review on the phase 2 use cases it covers. The roles that check the answer stay on the
reviews. The tests read the model text; they do not parse SysML.
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
    "needRunsIdentifyTheCandidate": (
        "NEED-DRIVING-011", {"VerificationEngineer", "ProductLineEngineer"}, "candidateVerdictConcern"),
}

#: need -> (the short name of its planned review, the phase 2 use cases the review depends on: each scenario its
#: need's source names)
VALIDATION = {
    "needWarnAndBrakeForVehicleAhead": ("SC-DRIVING-016", ("warnAndBrakeForStationaryVehicle",
                                                           "warnAndBrakeForSlowerVehicle")),
    "needNoReactionWithoutImminentCollision": ("SC-DRIVING-017", ("noReactionToStationaryVehicleBeyondTheCurve",
                                                                  "noReactionToVehicleAheadTurningOff")),
    "needWarningRequestForTheDriver": ("SC-DRIVING-018", ("warnAndBrakeForStationaryVehicle",
                                                          "warnAndBrakeForSlowerVehicle")),
    "needRunsIdentifyTheCandidate": ("SC-DRIVING-019", ("warnAndBrakeForStationaryVehicle", "warnAndBrakeForSlowerVehicle",
                                                        "noReactionToStationaryVehicleBeyondTheCurve",
                                                        "noReactionToVehicleAheadTurningOff")),
}
#: phase 2 use case -> its scenario identity
SCENARIOS = {
    "warnAndBrakeForStationaryVehicle": "SC-DRIVING-012",
    "warnAndBrakeForSlowerVehicle": "SC-DRIVING-013",
    "noReactionToStationaryVehicleBeyondTheCurve": "SC-DRIVING-014",
    "noReactionToVehicleAheadTurningOff": "SC-DRIVING-015",
}

#: reviewer-question concerns: their roles check the answer rather than use it, so they lead no need; a need's
#: source names them and its planned review asks their question, carried out by their roles
#: concern -> (the need whose source names it, the phrase of its review that names the asking roles, the question)
REVIEWED_CONCERNS = {
    "emergencyBrakingIndependenceConcern": (
        "needWarnAndBrakeForVehicleAhead",
        "can safety experts and product-line engineers tell which element of the candidate gave the braking command,",
        "whether it left the candidate in the driving command or apart from it, and whether that command keeps the "
        "independence of the protected emergency command path?"),
    "scoreCommandAndWarningPathConcern": (
        "needWarnAndBrakeForVehicleAhead",
        "Can systems engineers and product-line engineers confirm",
        "that every driving command passed through Eclipse S-CORE to the actuation and every warning request through "
        "S-CORE to the AAOS SDV, and that no other exchange carried them?"),
    "vehicleTargetCriteriaConcern": (
        "needWarnAndBrakeForVehicleAhead",
        "can verification engineers and compliance engineers confirm, by the criteria for a vehicle target that "
        "phase 5 derives,",
        "Can they trace each of those criteria to the provision of UNECE R152 it is derived from, to the "
        "product-line requirement it judges and whose obligation it is, and name what the runs cannot show of it?"),
}
#: a stakeholder definition -> how a review question or the guide names its members
ROLE_WORDS = {
    "SafetyExpert": "safety experts", "ProductLineEngineer": "product-line engineers",
    "SystemsEngineer": "systems engineers", "ComplianceEngineer": "compliance engineers",
    "VerificationEngineer": "verification engineers", "VehicleOccupant": "vehicle occupants",
    "RoadUser": "road users",
}
#: every role word a review question could name
ALL_ROLE_WORDS = (*ROLE_WORDS.values(), "system architects", "software developers", "maintainers")
#: plan -> the roles that carry out the review: the roles that check the answer
REVIEWERS = {
    "SC-DRIVING-016": {"verification engineers", "compliance engineers", "systems engineers", "product-line engineers",
                       "safety experts"},
    "SC-DRIVING-017": {"verification engineers", "compliance engineers"},
    "SC-DRIVING-018": {"safety experts", "verification engineers"},
    "SC-DRIVING-019": {"verification engineers", "product-line engineers"},
}
#: the parties who hold the operational needs never check them
NOT_CHECKERS = {"vehicle occupants", "road users"}
#: the anti-cheating question of each review that watches a run
ANTI_CHEATING_QUESTIONS = {
    "SC-DRIVING-016": "and that no autopilot, replay or overlay acts instead of the candidate?",
    "SC-DRIVING-017": "and that the candidate's own driving command moved the vehicle throughout each run?",
    "SC-DRIVING-018": "with no recording or overlay in place of either mode?",
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
#: the digits a need's statement or rationale may carry: phase numbers, System 2, ROS 2 and identifiers
ALLOWED_DIGITS = re.compile(r"\b(?:[Pp]hases? \d+(?: to \d+)?|System 2|ROS 2|[A-Z]+-[A-Z]+-\d{3})\b")
#: a number in words with a unit: a limit in disguise
NUMBER_WORDS = re.compile(r"(?i)\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|half)\s+(?:a\s+)?"
                          r"(?:seconds?|milliseconds?|metres?|meters?|kilometres?|kilometers?|km/h)\b")
#: a clause or section number of an external source: the repository names its source records only
CLAUSE_NUMBER = re.compile(r"(?i)\b(?:annex|paragraph|clause|appendix|section)\s+\d|§\s*\d|\b\d+(?:\.\d+){2,}\b")
#: a positive safety claim; "no safety claim" is the non-claim
SAFETY_CLAIM = re.compile(r"(?i)(?<!no )\bsaf(?:e|ety|ely)\b")
#: the non-claim sentence of the header
HEADER_NON_CLAIM = "No safety, on-road or production-readiness claim is made, and no member product is claimed."
#: need -> how the guide's bullet names its holders
GUIDE_HOLDERS = {
    "NEED-DRIVING-008": "Vehicle occupants and road users.",
    "NEED-DRIVING-009": "Vehicle occupants and road users.",
    "NEED-DRIVING-010": "Vehicle occupants.",
    "NEED-DRIVING-011": "Verification engineers and product-line engineers, who use the run identity in their own work.",
}

# The reviewed texts, pinned whole (whitespace flattened). A change to a need, a review or the contract comment is a
# change of the reviewed content: update the pin in the same commit, on purpose.
#: need -> its statement
STATEMENTS = {
    "needWarnAndBrakeForVehicleAhead": (
        "Vehicle occupants and road users need the driver-assistance system to request the "
        "collision warning and to command the braking of the vehicle when a collision with a "
        "stationary or a slower moving vehicle ahead in its lane is imminent."),
    "needNoReactionWithoutImminentCollision": (
        "Vehicle occupants and road users need the driver-assistance system to request no "
        "collision warning and to command no emergency braking when no collision with a vehicle "
        "ahead is imminent, as when a stationary vehicle stands beyond a curve or a vehicle ahead "
        "turns off."),
    "needWarningRequestForTheDriver": (
        "Vehicle occupants need the driver-assistance system to give a warning request at its "
        "boundary when a collision with a vehicle ahead in its lane is imminent, so that the AAOS "
        "SDV warns the driver on its display and as a sound."),
    "needRunsIdentifyTheCandidate": (
        "Verification engineers and product-line engineers need each run of the driver-assistance "
        "system to identify the candidate revision and the configuration it ran with, so that "
        "each verdict is bound to what ran."),
}
#: need -> its source
SOURCES = {
    "needWarnAndBrakeForVehicleAhead": (
        "INC-DRIVING-002 vehicleTargetResponseConcern, emergencyBrakingIndependenceConcern, "
        "scoreCommandAndWarningPathConcern, vehicleTargetCriteriaConcern, scope items "
        "vehicleTargetResponseInScope, scoreCommandPathInScope and vehicleTargetCriteriaInScope, "
        "gaps gapNoSeparateEmergencyFunction, gapScoreIntegration, gapVehicleTargetCriteria and "
        "gapCameraImageAndGeometry, assumption asmBenchReuse, scenarios SC-DRIVING-012 and "
        "SC-DRIVING-013"),
    "needNoReactionWithoutImminentCollision": (
        "INC-DRIVING-002 vehicleTargetResponseConcern, vehicleTargetCriteriaConcern, scope item "
        "noReactionInScope, gap gapVehicleTargetCriteria, scenarios SC-DRIVING-014 and "
        "SC-DRIVING-015"),
    "needWarningRequestForTheDriver": (
        "INC-DRIVING-002 driverWarningSequenceConcern, scope item driverWarningInScope, gap "
        "gapWarningOutput, scenarios SC-DRIVING-012 and SC-DRIVING-013"),
    "needRunsIdentifyTheCandidate": (
        "INC-DRIVING-002 candidateVerdictConcern, scope item verdictEvidenceInScope, gap "
        "gapCandidateBehaviorUnverified, scenarios SC-DRIVING-012 to SC-DRIVING-015"),
}
#: need -> its rationale
RATIONALES = {
    "needWarnAndBrakeForVehicleAhead": (
        "The warning lets the driver act, and the braking is meant to avoid or lessen the "
        "collision when the driver does not act in time. The need states what they expect, not "
        "how well the candidate meets it, and carries no safety claim. Phase 5 derives the "
        "criteria for a vehicle target and their limits (gapVehicleTargetCriteria). Phase 5 also "
        "derives from this need the requirements on the Eclipse S-CORE path of the warning "
        "request and the braking command, and on the independence of that command: its source "
        "names their concerns, and SC-DRIVING-016 asks their questions."),
    "needNoReactionWithoutImminentCollision": (
        "An emergency braking with no collision imminent puts the traffic behind the vehicle at "
        "risk, and a needless warning teaches the driver to ignore the next one. Phase 5 confirms "
        "the two scenarios and states their criterion (gapVehicleTargetCriteria)."),
    "needWarningRequestForTheDriver": (
        "The driver can act on a warning only if it reaches the display and the sound of the AAOS "
        "SDV. NEED-DRIVING-008 needs the candidate to request the warning; this need adds that "
        "the request leaves the candidate at its boundary, where the AAOS SDV takes it. At the "
        "inspected revision the application has no warning output at its boundary; its warnings "
        "go to its own visualization and data log (gapWarningOutput). Phase 5 states when each "
        "mode is due relative to the warning request and to the start of the emergency braking. "
        "Whether a driver perceives the warning is out of scope."),
    "needRunsIdentifyTheCandidate": (
        "The lifecycle decision rests on a verdict for each requirement and scenario, and a "
        "verdict holds only for the candidate that ran. A build with a change that upstream has "
        "not merged is a different candidate. The candidate's configuration includes its run-time "
        "settings, such as its source mode. The scenario and the simulated configuration belong "
        "to System 2 and are pinned there, so this need covers only what the candidate itself "
        "runs."),
}
#: plan -> its review question
PLAN_DOCS = {
    "SC-DRIVING-016": (
        "For NEED-DRIVING-008, a planned stakeholder review. While the stationary and the slower "
        "moving vehicle target scenarios run (SC-DRIVING-012 and SC-DRIVING-013), can "
        "verification engineers and compliance engineers confirm, by the criteria for a vehicle "
        "target that phase 5 derives, that the candidate requests the warning and that its "
        "driving command brakes the vehicle, and that no autopilot, replay or overlay acts "
        "instead of the candidate? Can they trace each of those criteria to the provision of "
        "UNECE R152 it is derived from, to the product-line requirement it judges and whose "
        "obligation it is, and name what the runs cannot show of it? Can systems engineers and "
        "product-line engineers confirm that every driving command passed through Eclipse S-CORE "
        "to the actuation and every warning request through S-CORE to the AAOS SDV, and that no "
        "other exchange carried them? And can safety experts and product-line engineers tell "
        "which element of the candidate gave the braking command, whether it left the candidate "
        "in the driving command or apart from it, and whether that command keeps the independence "
        "of the protected emergency command path?"),
    "SC-DRIVING-017": (
        "For NEED-DRIVING-009, a planned stakeholder review. While the vehicle drives through the "
        "curve past the stationary vehicle beyond the guard pipes (SC-DRIVING-014), and while it "
        "follows the vehicle ahead that turns off (SC-DRIVING-015), can verification engineers "
        "and compliance engineers confirm, by the criterion that phase 5 states for each "
        "scenario, that the candidate requests no warning and commands no emergency braking, and "
        "that the candidate's own driving command moved the vehicle throughout each run?"),
    "SC-DRIVING-018": (
        "For NEED-DRIVING-010, a planned stakeholder review. While the stationary and the slower "
        "moving vehicle target scenarios run (SC-DRIVING-012 and SC-DRIVING-013), can safety "
        "experts and verification engineers confirm that the AAOS SDV gave each warning that the "
        "candidate requested on its display and as a sound, and when each mode began relative to "
        "the warning request and to the start of the emergency braking, with no recording or "
        "overlay in place of either mode?"),
    "SC-DRIVING-019": (
        "For NEED-DRIVING-011, a planned stakeholder review. After each run of the four scenarios "
        "(SC-DRIVING-012, SC-DRIVING-013, SC-DRIVING-014 and SC-DRIVING-015), can verification "
        "engineers and product-line engineers bind its verdict to the candidate revision and the "
        "configuration that the run identifies, and confirm that a build with a change that "
        "upstream has not merged identifies itself as a different candidate?"),
}
#: the pinned runtime contract of VisionPilot, kept for phase 5
CONTRACT = (
    "The runtime contract of VisionPilot at commit 014e0e7a56ee8e597c2cab8175233f74edd9b856, kept "
    "for phase 5. - The application reads one camera frame and the vehicle speed, and writes "
    "steering and acceleration (VisionPilot/app/vision_pilot.cpp:117, 142, 174). - The ROS 2 "
    "build (ENABLE_ROS2_INTERFACE, VisionPilot/app/vision_pilot.cpp:59-64) reads the camera image "
    "and the speed from topics and writes the commands to topics. Its vehicle interface publishes "
    "steering and acceleration, and no warning "
    "(VisionPilot/modules/middleware_interfaces/ros2_interface/vehicle_ros2_interface/src/vehicle_ros2_interface.cpp:25-26). "
    "- The build without ROS 2 has two source modes, which the configuration key source.mode "
    "chooses at run time (VisionPilot/app/vision_pilot.cpp:65-78). The video mode reads a video "
    "and a speed file, and its vehicle write does nothing "
    "(VisionPilot/modules/sensing/vehicle_interface/src/file_interface.cpp:37-61). The V4L2 mode "
    "pairs a live camera with a CAN vehicle interface whose read returns zero and whose write "
    "does nothing (VisionPilot/modules/sensing/vehicle_interface/src/can_interface.cpp:4-12; "
    "VisionPilot/app/vision_pilot.cpp:73-78). So at the pin only the ROS 2 build reads a live "
    "speed and commands a vehicle. - The forward-collision warning and the emergency braking are "
    "two ranges of the acceleration that one speed planner computes "
    "(VisionPilot/modules/safety_guardian/planning/src/planning.cpp:113-121). One planning cycle "
    "flags at most one of the two, and nothing in the code orders the warning before the braking. "
    "- The two flags command nothing. The planned acceleration is written to the vehicle in every "
    "cycle, with no limit or latch between the planner and the write "
    "(VisionPilot/modules/safety_guardian/planning/src/longitudinal_planning.cpp:36; "
    "VisionPilot/app/vision_pilot.cpp:157, 174), so the vehicle already decelerates in a warning "
    "cycle. The flags reach only the application's own visualization and log, each when it is "
    "switched on (VisionPilot/app/vision_pilot.cpp:177-185). - Phase 5 derives the criterion for "
    "the time between the warning and the emergency braking, and what marks the start of the "
    "emergency braking.")


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
        assert _statement(body) == STATEMENTS[name], (name, "statement")
        assert source == SOURCES[name], (name, "source")
        assert _attribute(body, "rationale") == RATIONALES[name], (name, "rationale")


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
    for concern, (need, asked_by, question) in REVIEWED_CONCERNS.items():
        assert concern not in leading, f"{concern} is a reviewer question and leads no need"
        assert concern in _attribute(_need(need), "source"), (concern, need)
        doc = _plan_doc(VALIDATION[need][0])
        assert asked_by in doc and question in doc, (concern, "its review asks the concern's question")
        assert doc.index(asked_by) < doc.index(question), concern
        for role in _framing_holders(concern):
            assert ROLE_WORDS[role] in asked_by.lower(), (concern, role, "the concern's own roles ask its question")
    assert "Three concerns are reviewer questions: a need's source names them and its review checks them." \
        in _flat(_raw()), "the header counts the reviewer questions"


def test_each_need_has_one_planned_review_on_a_phase_2_use_case():
    code = _code()
    context = strip_comments(CONTEXT.read_text(encoding="utf-8"))
    plans = _plans()
    assert sorted(plans) == sorted(short for short, _use_cases in VALIDATION.values())
    associations = re.findall(
        r"\bconnection\s+\w+\s*:\s*ValidationPlanningAssociation\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    dependencies = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
    for need, (plan_short, use_cases) in VALIDATION.items():
        plan = plans[plan_short]
        assert associations.count((need, plan)) == 1, (need, plan)
        assert _plan_doc(plan_short).startswith(f"For {NEEDS[need][0]}, a planned stakeholder review."), plan
        assert sorted(target for source, target in dependencies if source == plan) == \
            sorted(f"{CONTEXT_PACKAGE}::{use_case}" for use_case in use_cases), (plan, use_cases)
        for use_case in use_cases:
            assert re.search(rf"\buse\s+case\s+{use_case}\s*\{{", context), use_case
        source = _attribute(_need(need), "source")
        named = set(SCENARIOS.values()) if "SC-DRIVING-012 to SC-DRIVING-015" in source \
            else set(re.findall(r"SC-DRIVING-01[2-5]", source))
        assert named == {SCENARIOS[use_case] for use_case in use_cases}, \
            (need, "its review watches exactly the scenarios its source names")
    assert len(associations) == len(NEEDS), "one planned review per need"
    # Phase 2 owns SC-DRIVING-012 to SC-DRIVING-015; the planned reviews continue the numbering.
    assert not re.search(r"<'SC-DRIVING-0(?:0\d|1[0-5])'>", code)


def test_each_planned_review_names_the_scenario_it_watches():
    for plan_short, use_cases in VALIDATION.values():
        doc = _plan_doc(plan_short)
        for use_case in use_cases:
            assert SCENARIOS[use_case] in doc, (plan_short, use_case)
        assert set(re.findall(r"SC-DRIVING-01[2-5]", doc)) == {SCENARIOS[use_case] for use_case in use_cases}, \
            f"{plan_short} names exactly the scenarios it watches"
        assert doc.count("?") >= 1, f"{plan_short} asks its question"
        assert doc == PLAN_DOCS[plan_short], (plan_short, "the reviewed question")
        reviewers = {words for words in ALL_ROLE_WORDS if words in doc.lower()}
        assert reviewers == REVIEWERS[plan_short], (plan_short, reviewers)
        assert not reviewers & NOT_CHECKERS, (plan_short, "the holders of an operational need never check it")
    assert set(REVIEWERS) == {plan_short for plan_short, _use_cases in VALIDATION.values()}


def test_no_need_uses_excluded_wording_an_unjudged_function_or_an_anti_cheating_clause():
    for name in NEEDS:
        text = _need_text(name)
        assert not EXCLUDED.findall(text), (name, EXCLUDED.findall(text))
        assert not UNJUDGED.findall(text), (name, UNJUDGED.findall(text))
        assert not ANTI_CHEATING.findall(text), (name, ANTI_CHEATING.findall(text))
        assert not SAFETY_CLAIM.findall(text), (name, SAFETY_CLAIM.findall(text))
    raw = _raw()
    assert not CLAUSE_NUMBER.findall(raw), CLAUSE_NUMBER.findall(raw)
    # the clause is a question of each planned review that watches a run
    for plan_short, question in ANTI_CHEATING_QUESTIONS.items():
        assert question in _plan_doc(plan_short), plan_short


def test_no_need_states_a_number():
    # The thresholds, the timing of the warning before the braking and the other limits are phase 5's.
    for name in NEEDS:
        body = _need(name)
        text = _flat(body)
        assert not NUMBER_WITH_UNIT.findall(text), (name, NUMBER_WITH_UNIT.findall(text))
        for part in (_statement(body), _attribute(body, "rationale")):
            assert not re.search(r"\d", ALLOWED_DIGITS.sub("", part)), (name, "a digit outside the identifiers", part)
            assert not NUMBER_WORDS.findall(part), (name, NUMBER_WORDS.findall(part))
    for name in ("needWarnAndBrakeForVehicleAhead", "needNoReactionWithoutImminentCollision",
                 "needWarningRequestForTheDriver"):
        assert "Phase 5" in _attribute(_need(name), "rationale"), f"{name}: the rationale leaves its limits to phase 5"


def test_the_input_contract_is_a_comment_for_phase_5_not_a_need():
    raw = _raw()
    match = re.search(r"\bcomment\s+(\w+)\s+about\s+([\w,\s]+?)\s*/\*(.*?)\*/", raw, re.S)
    assert match, "the pinned input contract is kept as a comment about the needs it serves"
    targets = [target.strip() for target in match.group(2).split(",")]
    assert targets == ["needWarnAndBrakeForVehicleAhead", "needWarningRequestForTheDriver"], targets
    comment = _flat(match.group(3))
    assert comment == CONTRACT, "the runtime contract at the pin, as reviewed"
    assert f"commit {VISIONPILOT_PIN}" in comment
    assert not re.search(r"-?\d+\.\d+\s*(?:m/s|<|<=)", comment), "the comment states no threshold of the planner"
    assert not re.search(r"(?i)\bneed not\b", comment)


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
    assert re.search(r'attribute\s+constraintLanguage\s*=\s*"English"\s*;', needs_body)
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
    for plan_short, _use_cases in VALIDATION.values():
        assert plan_short in section, plan_short
    assert "tests/test_driver_assistance_needs_requirements.py" in section
    raw_section = guide.split("## Stakeholder needs (Phase 4)", 1)[1].split("\n## ", 1)[0]
    bullets = {match[1]: " ".join(match[2].split())
               for match in re.finditer(r"(?ms)^- `(NEED-DRIVING-\d{3})`:(.*?)(?=^- `|^\s*$)", raw_section)}
    assert sorted(bullets) == sorted(short for short, _roles, _concern in NEEDS.values())
    for name, (short, roles, _concern) in NEEDS.items():
        assert GUIDE_HOLDERS[short] in bullets[short], (short, "the guide names the holders")
        named = {words for words in ALL_ROLE_WORDS if words in bullets[short].lower()}
        assert named == {ROLE_WORDS[role] for role in roles}, (short, named)
    assert "Three concerns get no need of their own" in section and len(REVIEWED_CONCERNS) == 3
    assert "only its ROS 2 build reads a live speed and commands a vehicle" in section
    assert not CLAUSE_NUMBER.findall(raw_section), CLAUSE_NUMBER.findall(raw_section)
    flat = " ".join(guide.split())  # Markdown: a line may open with bold text, which _flat would strip
    assert "The next model obligation is **Phase 5**: the requirements" in flat
    assert "its first gate is `requirementHasStatement`" in flat


def test_the_header_states_its_non_claims():
    header = _flat(_raw().split("\npackage ", 1)[0])
    assert HEADER_NON_CLAIM in header, "the header keeps its non-claims"
