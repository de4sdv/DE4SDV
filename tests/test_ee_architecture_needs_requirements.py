"""Content pins for the E/E architecture stakeholder needs (INC-EE-001, phase 4), not semantic validation.

Each need is held by the parties the vehicle network serves, leads its source with the phase 1 concern it
derives from, and has one planned stakeholder review on the phase 2 use cases it covers. The roles that check
the answer stay on the reviews. The tests read the model text; they do not parse SysML.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import braced_body, charter_package_files, strip_comments

ROOT = Path(__file__).resolve().parents[1]
EE = ROOT / "textual-notation-of-model/packages/features/ee"
FRAMING = EE / "ee_architecture_framing.sysml"
CONTEXT = EE / "ee_architecture_operational_context.sysml"
MODEL = EE / "ee_architecture_needs_requirements.sysml"
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
PACKAGE = "DE4SDV_EEArchitectureNeedsRequirements"
CONTEXT_PACKAGE = "DE4SDV_EEArchitectureOperationalContext"
SYSTEM_OF_INTEREST = "DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem"
INCREMENT = "INC-EE-001"

#: need -> (short name, the roles that hold it, the phase 1 concern that leads its source)
NEEDS = {
    "needDrivingCommandReachesActuationOnEachRoute": (
        "NEED-EE-001", {"VehicleOccupant", "RoadUser"}, "eeVehicleCommandConcern"),
    "needNoInvalidCommandApplied": (
        "NEED-EE-002", {"VehicleOccupant", "RoadUser"}, "eeVehicleCommandConcern"),
    "needRunsIdentifyRouteAndNetwork": (
        "NEED-EE-003", {"VerificationEngineer", "ProductLineEngineer"}, "eeRouteVerdictConcern"),
}

#: need -> (the short name of its planned review, the phase 2 use cases the review depends on: each scenario its
#: need's source names)
VALIDATION = {
    "needDrivingCommandReachesActuationOnEachRoute": (
        "SC-EE-005", ("carryCommandThroughZoneController", "carryCommandOverDirectLink")),
    "needNoInvalidCommandApplied": (
        "SC-EE-006", ("rejectFaultyCommandOnTheRoute", "respondToLinkDownOnTheRoute")),
    "needRunsIdentifyRouteAndNetwork": (
        "SC-EE-007", ("carryCommandThroughZoneController", "carryCommandOverDirectLink",
                      "rejectFaultyCommandOnTheRoute", "respondToLinkDownOnTheRoute")),
}
#: phase 2 use case -> its scenario identity
SCENARIOS = {
    "carryCommandThroughZoneController": "SC-EE-001",
    "carryCommandOverDirectLink": "SC-EE-002",
    "rejectFaultyCommandOnTheRoute": "SC-EE-003",
    "respondToLinkDownOnTheRoute": "SC-EE-004",
}

#: reviewer-question concerns: their roles check the answer rather than use it, so they lead no need; a need's
#: source names them and its planned review asks their question, carried out by their roles
#: concern -> (the need whose source names it, the phrase of its review that names the asking roles, the question)
REVIEWED_CONCERNS = {
    "eeCommandRouteExchangeConcern": (
        "needDrivingCommandReachesActuationOnEachRoute",
        "Can system architects and systems engineers tell",
        "which elements of the vehicle network exchange the command on each route, and by which boundary "
        "interface it enters the network from the Eclipse S-CORE path?"),
    "eeTopologyStructureConcern": (
        "needDrivingCommandReachesActuationOnEachRoute",
        "And can system architects and product-line engineers tell",
        "which elements make up the one topology that holds both routes, and in which role each is used?"),
    "eeNetworkFaultResponseConcern": (
        "needNoInvalidCommandApplied",
        "Can safety experts and systems engineers follow,",
        "for each fault, the sequence from the fault to its detection at the actuation and to the response "
        "that follows there?"),
    "eeCommandItemConcern": (
        "needNoInvalidCommandApplied",
        "And can systems engineers and safety experts tell",
        "which exchange item carries the command on each part of its way, and whether each keeps the parts by "
        "which the actuation detects such a fault, including where a zone controller repacks it from Ethernet "
        "to CAN?"),
}
#: a stakeholder definition -> how a review question or the guide names its members
ROLE_WORDS = {
    "SafetyExpert": "safety experts", "ProductLineEngineer": "product-line engineers",
    "SystemsEngineer": "systems engineers", "SystemArchitect": "system architects",
    "VerificationEngineer": "verification engineers", "VehicleOccupant": "vehicle occupants",
    "RoadUser": "road users",
}
#: every role word a review question could name
ALL_ROLE_WORDS = (*ROLE_WORDS.values(), "compliance engineers", "software developers", "maintainers")
#: plan -> the roles that carry out the review: the roles that check the answer
REVIEWERS = {
    "SC-EE-005": {"systems engineers", "verification engineers", "system architects", "product-line engineers"},
    "SC-EE-006": {"verification engineers", "safety experts", "systems engineers"},
    "SC-EE-007": {"verification engineers", "product-line engineers"},
}
#: the parties who hold the operational needs never check them
NOT_CHECKERS = {"vehicle occupants", "road users"}

#: the phase 1 concerns this phase reads: every non-boundary concern of the framing
PHASE1_CONCERNS = {
    "eeVehicleCommandConcern", "eeTopologyStructureConcern", "eeCommandItemConcern",
    "eeCommandRouteExchangeConcern", "eeNetworkFaultResponseConcern", "eeRouteVerdictConcern",
}

#: wording the charter excludes from a need: approval, admission, a member product, on-road use, a result
EXCLUDED = re.compile(r"(?i)\b(?:certif\w*|homologat\w*|complian\w*|complies|approv\w*|type.approv\w*|admi(?:t|ss)\w*|"
                      r"on-road|member products?|UNECE|R152|passe[sd]|fail(?:s|ed))\b")
#: an anti-cheating clause belongs to a planned review's question, not to a need
ANTI_CHEATING = re.compile(r"(?i)\b(?:autopilot|replay\w*|overlay\w*|recording|acts? instead|stands? in)\b")
#: a value with a unit is phase 5's, derived with its provenance; a need states none
NUMBER_WITH_UNIT = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:ms|s|m|km/h|m/s|m/s2|m/s²|g|Hz|%|px|mm|°)(?![\w/])")
#: the digits a need's statement or rationale may carry: phase numbers, System 2, identifiers and decision dates
ALLOWED_DIGITS = re.compile(r"\b(?:[Pp]hases? \d+(?: to \d+)?|System 2|[A-Z]+-[A-Z]+-\d{3}|\d{4}-\d{2}-\d{2})\b")
#: a number in words with a unit: a limit in disguise
NUMBER_WORDS = re.compile(r"(?i)\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|half)\s+(?:a\s+)?"
                          r"(?:seconds?|milliseconds?|metres?|meters?|kilometres?|kilometers?|km/h)\b")
#: a count of the routes in a statement: the statement says "either route", the scenarios name them
ROUTE_COUNT = re.compile(r"(?i)\b(?:two|both)\b")
#: a clause or section number of an external source: the repository names its source records only
CLAUSE_NUMBER = re.compile(r"(?i)\b(?:annex|paragraph|clause|appendix|section)\s+\d|§\s*\d|\b\d+(?:\.\d+){2,}\b")
#: a positive safety claim; "no safety claim" is the non-claim
SAFETY_CLAIM = re.compile(r"(?i)(?<!no )\bsaf(?:e|ety|ely)\b")
#: the fields of the command are INC-DRIVING-002's, stated in phase 5 and phase 8: a need names none
COMMAND_FIELD = re.compile(r"(?i)\b(?:sequence counts?|check values?|issue times?|frames?|CRC\w*|payload\w*)\b")
#: sensor data, the AEBS command and the brake hand-off are outside the increment
OUTSIDE = re.compile(r"(?i)\b(?:sensor\w*|camera\w*|AEBS|hand-off|speed)\b")
#: route hardware stays out of a statement: the source scenarios and the review name the routes
ROUTE_HARDWARE = re.compile(r"(?i)\b(?:Ethernet|backbone|zone controllers?|direct link|CAN)\b")
#: the non-claim sentence of the header
HEADER_NON_CLAIM = ("No safety, timing, on-road or production-readiness claim is made, and no member product is "
                    "claimed.")
#: the count sentence of the header
HEADER_COUNT = "Four concerns are reviewer questions: a need's source names them and its review checks them."
#: need -> how the guide's bullet names its holders
GUIDE_HOLDERS = {
    "NEED-EE-001": "Vehicle occupants and road users.",
    "NEED-EE-002": "Vehicle occupants and road users.",
    "NEED-EE-003": "Verification engineers and product-line engineers, who use the run identity in their own work.",
}

# The reviewed texts, pinned whole (whitespace flattened). A change to a need, a review or the contract comment is a
# change of the reviewed content: update the pin in the same commit, on purpose.
#: need -> its statement
STATEMENTS = {
    "needDrivingCommandReachesActuationOnEachRoute": (
        "Vehicle occupants and road users need the vehicle network to carry the driving command "
        "that the central computer gives to the actuation ECU on either route of the command, so "
        "that the actuation ECU applies that command to the vehicle."),
    "needNoInvalidCommandApplied": (
        "Vehicle occupants and road users need the vehicle network to apply to the vehicle no "
        "driving command that a fault of the network has made invalid on its way, on either route "
        "of the command."),
    "needRunsIdentifyRouteAndNetwork": (
        "Verification engineers and product-line engineers need each run of the vehicle network to "
        "identify the route that carried the driving command and the topology and the revision of "
        "the network that ran, so that each verdict is bound to what ran."),
}
#: need -> its source
SOURCES = {
    "needDrivingCommandReachesActuationOnEachRoute": (
        "INC-EE-001 eeVehicleCommandConcern, eeCommandRouteExchangeConcern, eeTopologyStructureConcern, "
        "scope items eeCommandFlowInScope, eeCommandRouteInScope and eeTopologyInScope, assumptions "
        "asmEECommandFromDrivingBaseline and asmEEScoreCommandSource, gaps gapEEZoneRouteInVehicles and "
        "gapEEStackAndNetworkBoundary, scenarios SC-EE-001 and SC-EE-002"),
    "needNoInvalidCommandApplied": (
        "INC-EE-001 eeVehicleCommandConcern, eeNetworkFaultResponseConcern, eeCommandItemConcern, scope "
        "items eeNetworkFaultsInScope and eeCommandFlowInScope, assumption asmEECommandFromDrivingBaseline, "
        "gap gapEEActuationEnd, scenarios SC-EE-003 and SC-EE-004"),
    "needRunsIdentifyRouteAndNetwork": (
        "INC-EE-001 eeRouteVerdictConcern, scope item eeVerdictEvidenceInScope, assumption "
        "asmEESoftwareTestbedStandsIn, gap gapEERecordedCommandStream, scenarios SC-EE-001 to SC-EE-004"),
}
#: need -> its rationale
RATIONALES = {
    "needDrivingCommandReachesActuationOnEachRoute": (
        "The vehicle can act on the driving command only if the command reaches the actuation ECU, "
        "and the increment takes neither route as given (gapEEZoneRouteInVehicles), so the need "
        "holds on each. The form of the command is the one that the driver-assistance increment "
        "fixes at its baseline; that baseline states no cadence of the command as such. The need "
        "states what the occupants and road users expect, not how well the network meets it, and "
        "carries no safety claim and no timing claim. Phase 5 derives its limits. Phase 5 also "
        "derives from this need the requirements on the elements that exchange the command on each "
        "route and on the topology that holds both routes: its source names their concerns, and "
        "SC-EE-005 asks their questions."),
    "needNoInvalidCommandApplied": (
        "A command that is lost, delayed, repeated or corrupted on its way no longer stands for what "
        "the central computer gave, so the vehicle is not to act on it. When a link of the route "
        "goes down, the last command to arrive ages, and a lost command is a fault of the network. "
        "The driver-assistance increment places at the actuation the share of applying no command "
        "that the actuation rejects: its actuation end, DrivingCommandActuationAdapter, rejects a "
        "command whose fault the form of REQ-DRIVING-039 lets it detect, and has no stop response. "
        "That actuation detects only the corruptions that the form of the command lets it detect "
        "(the check-value bound decision of 2026-11-21 of that increment), so this need states the "
        "expectation and Phase 5 states the requirement within that bound. Which element detects a "
        "fault, rejects a command and gives a response is open (gapEEActuationEnd). The need "
        "carries no safety claim and no claim of freedom from interference. Phase 5 derives the "
        "detection and the rejection with their limits, and the share of the network in the "
        "response when no valid command reaches the actuation ECU, after REQ-DRIVING-028 of "
        "INC-DRIVING-001. A time limit counts on the clock of the virtual vehicle. Phase 5 also "
        "derives from this need the requirements on the exchange items that carry the command and "
        "on the sequence from each fault to its response: its source names their concerns, and "
        "SC-EE-006 asks their questions."),
    "needRunsIdentifyRouteAndNetwork": (
        "The lifecycle decision rests on a pass or a fail for each requirement on each route, and a "
        "verdict holds only for the route, the topology and the revision that ran. The recorded "
        "command stream, its binding to the revision that made it and the testbed belong to System "
        "2 and are bound there (gapEERecordedCommandStream, asmEESoftwareTestbedStandsIn), so this "
        "need covers only what the vehicle network itself runs. A verdict holds for the software "
        "testbed only and is no timing claim for a vehicle network."),
}
#: plan -> its review question
PLAN_DOCS = {
    "SC-EE-005": (
        "For NEED-EE-001, a planned stakeholder review. While the route through a zone controller "
        "and the direct link run (SC-EE-001 and SC-EE-002), can systems engineers and verification "
        "engineers confirm whether the command that the actuation ECU applies on each route is the "
        "command that the central computer gave? Can system architects and systems engineers tell "
        "which elements of the vehicle network exchange the command on each route, and by which "
        "boundary interface it enters the network from the Eclipse S-CORE path? And can system "
        "architects and product-line engineers tell which elements make up the one topology that "
        "holds both routes, and in which role each is used?"),
    "SC-EE-006": (
        "For NEED-EE-002, a planned stakeholder review. While a command fault on the route and a "
        "link that goes down run (SC-EE-003 and SC-EE-004), can verification engineers and safety "
        "experts confirm whether the actuation ECU applied any command that was lost, delayed, "
        "repeated or corrupted on its way, or kept applying a command after a link of its route went "
        "down, and whether a response followed when no valid command reached it, and which? Can "
        "safety experts and systems engineers follow, for each fault, the sequence from the fault to "
        "its detection at the actuation and to the response that follows there? And can systems "
        "engineers and safety experts tell which exchange item carries the command on each part of "
        "its way, and whether each keeps the parts by which the actuation detects such a fault, "
        "including where a zone controller repacks it from Ethernet to CAN?"),
    "SC-EE-007": (
        "For NEED-EE-003, a planned stakeholder review. While the route through a zone controller, "
        "the direct link, a command fault on the route and a link that goes down run (SC-EE-001 to "
        "SC-EE-004), can verification engineers and product-line engineers tell from each run which "
        "route carried the command and which topology and revision of the vehicle network ran, and "
        "whether each verdict is bound to them?"),
}
#: the input contract kept for phase 5 as a comment about the first need, pinned whole
CONTRACT = (
    "The vehicle network takes the driving command, DrivingCommand of INC-DRIVING-002, in the form "
    "that that increment fixes at its baseline, from the Eclipse S-CORE path "
    "(asmEEScoreCommandSource). Phase 5 states it as requirements and derives the cadence that the "
    "vehicle network carries.")
#: Phase 0 to 2 text that said the baseline of INC-DRIVING-002 fixes the cadence, and the hold of Phase 4
OLD_TEXTS = (
    "Until that baseline, both can change.", "Phase 4 onward", "form and the cadence", "form and cadence",
    "its form and its cadence", "The next model obligation is **Phase 4**",
)


def _raw() -> str:
    assert MODEL.is_file(), "phase 4 of INC-EE-001 needs a stakeholder needs model"
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
    return dict(re.findall(r"\bpart\s+<'(SC-EE-\d{3})'>\s+(\w+)\s*:\s*ValidationPlanningScenario\b", _code()))


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


def _scenarios_of(text: str) -> set[str]:
    if "SC-EE-001 to SC-EE-004" in text:
        return set(SCENARIOS.values())
    return set(re.findall(r"SC-EE-00[1-4]", text))


def test_the_package_declares_exactly_the_needs_of_phase_4_with_unique_short_names():
    code = _code()
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", code) == [PACKAGE], "one global package per file"
    declared = re.findall(r"\brequirement\s+<'([^']+)'>\s+(\w+)\s*:\s*StakeholderNeedCandidate\b", code)
    assert declared == [(short, name) for name, (short, _roles, _concern) in NEEDS.items()]
    others = [path.name for path in charter_package_files(FRAMING, "eeArchitectureCharter") if path != MODEL
              and re.search(r"<'NEED-EE-\d{3}'>", path.read_text(encoding="utf-8"))]
    assert not others, f"the needs of the increment are declared only here: {others}"


def test_each_need_has_a_statement_its_holders_a_source_a_rationale_and_the_system_of_interest():
    # The ElaborateNeeds gates: needHasStatement, needHasStakeholder, needHasSource, needHasRationale, and the
    # advisory needSubjectIsSystemOfInterest (the charter's systemOfInterest, never the increment).
    for name, (_short, roles, concern) in NEEDS.items():
        body = _need(name)
        assert re.search(rf"\bsubject\s+\w+\s*:>\s*{re.escape(SYSTEM_OF_INTEREST)}\s*;", body), name
        assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", strip_comments(body))) == roles, name
        source = _attribute(body, "source")
        assert source.startswith(f"{INCREMENT} {concern},"), (name, source)
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
    assert "eeArchitectureBoundary" not in " ".join(_need_text(name) for name in NEEDS)


def test_a_reviewer_question_concern_is_named_by_a_need_and_checked_by_its_review():
    leading = {concern for _short, _roles, concern in NEEDS.values()}
    for concern, (need, asked_by, question) in REVIEWED_CONCERNS.items():
        assert concern not in leading, f"{concern} is a reviewer question and leads no need"
        assert concern in _attribute(_need(need), "source"), (concern, need)
        doc = _plan_doc(VALIDATION[need][0])
        assert asked_by in doc and question in doc, (concern, "its review asks the concern's question")
        assert doc.index(asked_by) < doc.index(question), concern
        assert f"{asked_by} {question}" in doc, (concern, "the asking roles lead the question")
        for role in _framing_holders(concern):
            assert ROLE_WORDS[role] in asked_by.lower(), (concern, role, "the concern's own roles ask its question")
    header = _flat(_raw().split("\npackage ", 1)[0])
    assert HEADER_COUNT in header, "the header counts the reviewer questions"
    for concern in REVIEWED_CONCERNS:
        assert concern in header, (concern, "the header gives the reason of each reviewer question")


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
            # the bound target exists in the operational context and carries its scenario identity
            assert re.search(rf"\buse\s+case\s+{use_case}\s*\{{", context), use_case
            assert SCENARIOS[use_case] in braced_body(CONTEXT.read_text(encoding="utf-8"),
                                                      f"use case {use_case}"), use_case
        named = _scenarios_of(_attribute(_need(need), "source"))
        assert named == {SCENARIOS[use_case] for use_case in use_cases}, \
            (need, "its review watches exactly the scenarios its source names")
    assert len(associations) == len(NEEDS), "one planned review per need"
    assert len(dependencies) == sum(len(use_cases) for _plan, use_cases in VALIDATION.values())
    # Phase 2 owns SC-EE-001 to SC-EE-004; the planned reviews continue the numbering.
    assert not re.search(r"<'SC-EE-00[1-4]'>", code)


def test_each_planned_review_names_the_scenario_it_watches():
    for need, (plan_short, use_cases) in VALIDATION.items():
        doc = _plan_doc(plan_short)
        watched = {SCENARIOS[use_case] for use_case in use_cases}
        assert _scenarios_of(doc) == watched, f"{plan_short} names exactly the scenarios it watches"
        assert _scenarios_of(doc) == _scenarios_of(_attribute(_need(need), "source")), \
            (plan_short, "the review and its need's source name the same scenarios")
        assert doc.count("?") >= 1, f"{plan_short} asks its question"
        assert doc == PLAN_DOCS[plan_short], (plan_short, "the reviewed question")
        reviewers = {words for words in ALL_ROLE_WORDS if words in doc.lower()}
        assert reviewers == REVIEWERS[plan_short], (plan_short, reviewers)
        assert not reviewers & NOT_CHECKERS, (plan_short, "the holders of an operational need never check it")
        assert not re.search(r"(?i)\bcan [\w\s-]+ (?:confirm|tell|follow),? how\b", doc), \
            (plan_short, "a question does not presuppose its answer")
    assert set(REVIEWERS) == {plan_short for plan_short, _use_cases in VALIDATION.values()}


def test_no_need_uses_excluded_wording_or_an_anti_cheating_clause():
    for name in NEEDS:
        text = _need_text(name)
        assert not EXCLUDED.findall(text), (name, EXCLUDED.findall(text))
        assert not ANTI_CHEATING.findall(text), (name, ANTI_CHEATING.findall(text))
        assert not SAFETY_CLAIM.findall(text), (name, SAFETY_CLAIM.findall(text))
        assert not OUTSIDE.findall(text), (name, OUTSIDE.findall(text))
    raw = _raw()
    assert not CLAUSE_NUMBER.findall(raw), CLAUSE_NUMBER.findall(raw)


def test_no_need_states_a_number_or_names_a_field_of_the_command():
    # The limits, the cadence and the fields of the command are phase 5's and phase 8's.
    for name in NEEDS:
        body = _need(name)
        text = _flat(body)
        assert not NUMBER_WITH_UNIT.findall(text), (name, NUMBER_WITH_UNIT.findall(text))
        statement = _statement(body)
        for part in (statement, _attribute(body, "rationale")):
            assert not re.search(r"\d", ALLOWED_DIGITS.sub("", part)), (name, "a digit outside the identifiers", part)
            assert not NUMBER_WORDS.findall(part), (name, NUMBER_WORDS.findall(part))
            assert not COMMAND_FIELD.findall(part), (name, COMMAND_FIELD.findall(part))
        assert not re.search(r"\d", statement), (name, "a statement has no digit")
        assert not ROUTE_COUNT.findall(statement), (name, ROUTE_COUNT.findall(statement))
        assert not ROUTE_HARDWARE.findall(statement), (name, ROUTE_HARDWARE.findall(statement))
    for name in ("needDrivingCommandReachesActuationOnEachRoute", "needNoInvalidCommandApplied"):
        assert "Phase 5" in _attribute(_need(name), "rationale"), f"{name}: the rationale leaves its limits to phase 5"


def test_the_stop_response_stays_on_the_review_and_comes_from_the_closed_loop_increment():
    statement = _statement(_need("needNoInvalidCommandApplied"))
    assert "stop" not in statement and "response" not in statement, "the need states one obligation"
    rationale = _attribute(_need("needNoInvalidCommandApplied"), "rationale")
    assert "after REQ-DRIVING-028 of INC-DRIVING-001" in rationale
    assert "and has no stop response" in rationale, "the driver-assistance adapter gives no stop response"
    assert "the check-value bound decision of 2026-11-21 of that increment" in rationale
    assert "DrivingCommandActuationAdapter" in rationale and "REQ-DRIVING-039" in rationale
    assert "and whether a response followed when no valid command reached it, and which?" in \
        _plan_doc("SC-EE-006")


def test_the_command_form_contract_is_a_comment_for_phase_5():
    raw = _raw()
    match = re.search(r"\bcomment\s+commandFormContract\s+about\s+needDrivingCommandReachesActuationOnEachRoute\s*"
                      r"/\*(.*?)\*/", raw, re.S)
    assert match, "the input contract is a comment about the first need"
    assert _flat(match.group(1)) == CONTRACT
    assert not COMMAND_FIELD.findall(CONTRACT) and not re.search(r"\d", ALLOWED_DIGITS.sub("", CONTRACT))


def test_two_tables_frame_the_needs_concern_and_show_needs_and_planned_reviews():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*StakeholderNeedsConcern\b", code)
    assert len(concerns) == 1
    concern = braced_body(code, f"concern {concerns[0]} : StakeholderNeedsConcern")
    assert re.search(r"\bsubject\s*;", concern)
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == {"SystemsEngineer", "ProductLineEngineer"}
    views = [view for view in re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
             if re.search(rf"\bframe\s+{concerns[0]}\s*;", braced_body(code, f"view {view} : TVD::TableView"))]
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
    charter = braced_body(framing, "part eeArchitectureCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index("DE4SDV_EEArchitectureCapabilityClassification") + 1
    assert MODEL in charter_package_files(FRAMING, "eeArchitectureCharter")


def test_the_guide_has_a_phase_4_section_and_names_phase_5_next():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## Capability classification (Phase 3)") < guide.index("## Stakeholder needs (Phase 4)") \
        < guide.index("## What the framing already records as open")
    raw_section = guide.split("## Stakeholder needs (Phase 4)", 1)[1].split("\n## ", 1)[0]
    section = " ".join(raw_section.split())
    for short, _roles, _concern in NEEDS.values():
        assert short in section, short
    for plan_short, _use_cases in VALIDATION.values():
        assert plan_short in section, plan_short
    assert "tests/test_ee_architecture_needs_requirements.py" in section
    bullets = {match[1]: " ".join(match[2].split())
               for match in re.finditer(r"(?ms)^- `(NEED-EE-\d{3})`:(.*?)(?=^- `|^\s*$)", raw_section)}
    assert sorted(bullets) == sorted(short for short, _roles, _concern in NEEDS.values())
    for _name, (short, roles, _concern) in NEEDS.items():
        assert GUIDE_HOLDERS[short] in bullets[short], (short, "the guide names the holders")
        named = {words for words in ALL_ROLE_WORDS if words in bullets[short].lower()}
        assert named == {ROLE_WORDS[role] for role in roles}, (short, named)
    assert "Four concerns get no need of their own" in section and len(REVIEWED_CONCERNS) == 4
    assert "after REQ-DRIVING-028 of INC-DRIVING-001" in section
    assert not CLAUSE_NUMBER.findall(raw_section), CLAUSE_NUMBER.findall(raw_section)
    flat = " ".join(guide.split())
    assert "After that baseline, the owner decided on 2026-11-21 to start Phase 4. The next model obligation is " \
        "**Phase 5**, the requirements. The testbed with its readiness probe waits for a further decision of the " \
        "owner." in flat
    assert "Phase 5 waits" not in flat and "Phase 5 and the testbed" not in flat, "no hold of Phase 5 is written"
    assert "Phase 3 capability classification and Phase 4 stakeholder needs, proposal." in flat


def test_the_header_states_its_non_claims():
    header = _flat(_raw().split("\npackage ", 1)[0])
    assert HEADER_NON_CLAIM in header, "the header keeps its non-claims"


def test_no_text_says_the_baseline_of_the_driver_assistance_increment_fixes_the_cadence():
    # Phases 0 to 2 said so; that baseline states no cadence of the command as such.
    for path in (FRAMING, CONTEXT, GUIDE, *sorted(EE.glob("*.sysml"))):
        flat = _flat(path.read_text(encoding="utf-8"))
        for old in OLD_TEXTS:
            assert old not in flat, (path.name, old)
    framing = _flat(FRAMING.read_text(encoding="utf-8"))
    assert "After that baseline, the owner decided on 2026-11-21 to start Phase 4. The testbed with its readiness " \
        "probe waits for a further decision of the owner." in framing
    assert "That baseline states no cadence of the command as such;" in framing
