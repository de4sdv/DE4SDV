"""Content pins for the driver-assistance requirements (INC-DRIVING-002, phase 5), not semantic validation.

Phase 5 derives the design-input requirements of the candidate driver-assistance system from the four needs of
phase 4. The SpecifyRequirements rules of the increment workflow are checked by Method Check; these pins hold what
review settled on top of them:

- the requirement set itself, each with its need, its kind and its verification method, within the charter's
  scope cap of at most ten requirements;
- requirement-writing rules: one obligation per statement (one `shall`, at most 60 words), the positive form, and
  the terms the statements use defined once in the package;
- the criteria for a vehicle target, each derived from the source regulation and a product-line requirement, with
  whose obligation it is and what a simulation cannot show of it;
- the no-autopilot, replay or overlay condition of the planned reviews as a success criterion, never as wording of
  a statement;
- the time of the warning request before the emergency braking in simulation time, its share for the path and the
  AAOS SDV in wall-clock time;
- the phase 4 comment on the VisionPilot contract replaced by the rationales;
- one requirement definition table, the one view the method names for phase 5, which answers the criteria
  concern of the framing;
- the guide's phase 5 section and the next obligation, phase 6;
- the upstream record, which gives each file that a rationale cites with its path at the pin;
- no claim the charter excludes, and no feature link before phase 9 adds the feature.

The tests read the model text; they do not parse SysML. They state their own constants.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guides/driver-assistance-increment.md"
UPSTREAM_RECORD = ROOT / "textual-notation-of-model/packages/features/driving/upstream.md"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "driver_assistance_needs_requirements.sysml"
SUBJECT_LINE = "subject driverAssistanceSystem :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem;"

NEED_SHORT = {
    "needWarnAndBrakeForVehicleAhead": "NEED-DRIVING-008",
    "needNoReactionWithoutImminentCollision": "NEED-DRIVING-009",
    "needWarningRequestForTheDriver": "NEED-DRIVING-010",
    "needRunsIdentifyTheCandidate": "NEED-DRIVING-011",
}

F = "FunctionalRequirementCandidate"
R = "RequirementCandidate"

#: Each requirement, in declaration order: its short name, the need it derives from, its definition and its
#: verification method.
REQUIREMENTS = {
    "reqEmergencyBrakingForImminentCollision": ("REQ-DRIVING-036", "needWarnAndBrakeForVehicleAhead", F, "test"),
    "reqImpactSpeedWithinLimit": ("REQ-DRIVING-037", "needWarnAndBrakeForVehicleAhead", R, "test"),
    "reqDrivingCommandOverSCORE": ("REQ-DRIVING-038", "needWarnAndBrakeForVehicleAhead", R, "test"),
    "reqIsolateEmergencyBrakingFromSCORE": ("REQ-DRIVING-039", "needWarnAndBrakeForVehicleAhead", R, "analyze"),
    "reqWithholdWarningRequest": ("REQ-DRIVING-040", "needNoReactionWithoutImminentCollision", F, "test"),
    "reqWithholdEmergencyBraking": ("REQ-DRIVING-041", "needNoReactionWithoutImminentCollision", F, "test"),
    "reqWarningRequestBeforeEmergencyBraking": ("REQ-DRIVING-042", "needWarningRequestForTheDriver", F, "test"),
    "reqWarningRequestOverSCORE": ("REQ-DRIVING-043", "needWarningRequestForTheDriver", R, "test"),
    "reqRecordCandidateIdentity": ("REQ-DRIVING-044", "needRunsIdentifyTheCandidate", F, "test"),
}

#: The charter's scope: one configuration and at most ten requirements.
SCOPE_CAP = 10

#: requirement -> its source, exactly: what it derives from is a decision of phase 5
SOURCES = {
    "reqEmergencyBrakingForImminentCollision": "NEED-DRIVING-008; SRC-UNECE-R152 emergency braking; REQ-AEBS-003; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-012 and SC-DRIVING-013",
    "reqImpactSpeedWithinLimit": "NEED-DRIVING-008; SRC-UNECE-R152 speed reduction by braking demand; REQ-AEBS-003; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-012 and SC-DRIVING-013",
    "reqDrivingCommandOverSCORE": "NEED-DRIVING-008; scope item scoreCommandPathInScope; gap gapScoreIntegration; scenarios SC-DRIVING-012 to SC-DRIVING-015",
    "reqIsolateEmergencyBrakingFromSCORE": "NEED-DRIVING-008; REQ-MW-006; gap gapNoSeparateEmergencyFunction; emergencyBrakingIndependenceConcern",
    "reqWithholdWarningRequest": "NEED-DRIVING-009; SRC-UNECE-R152 false reaction avoidance; REQ-AEBS-008; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-014 and SC-DRIVING-015",
    "reqWithholdEmergencyBraking": "NEED-DRIVING-009; SRC-UNECE-R152 false reaction avoidance; REQ-AEBS-012; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-014 and SC-DRIVING-015",
    "reqWarningRequestBeforeEmergencyBraking": "NEED-DRIVING-010; SRC-UNECE-R152 collision warning; REQ-AEBS-002; gap gapWarningOutput; scenarios SC-DRIVING-012 and SC-DRIVING-013",
    "reqWarningRequestOverSCORE": "NEED-DRIVING-010; scope item scoreCommandPathInScope; gaps gapWarningOutput and gapScoreIntegration; scenarios SC-DRIVING-012 and SC-DRIVING-013",
    "reqRecordCandidateIdentity": "NEED-DRIVING-011; gap gapCandidateBehaviorUnverified; scenarios SC-DRIVING-012 to SC-DRIVING-015",
}

#: requirement -> the fragments its statement, its rationale and its success criteria must carry
FRAGMENTS = {
    "reqEmergencyBrakingForImminentCollision": {
        "statement": ("imminent", "shall command a deceleration of at least 5.0 m/s²"),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-003", "014e0e7a", "planning.cpp:118", "longitudinal_planning.cpp:36",
                      "vision_pilot.cpp:138, 157, 174", "The obligation is the candidate's", "A simulation cannot show"),
        "criteria": ("at least 5.0 m/s²", "functional part", "each judged run"),
    },
    "reqImpactSpeedWithinLimit": {
        "statement": ("maximum relative impact speed", "relative approach speed"),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-003", "car in running order", "asmSimulatedConfigurationStandsIn",
                      "The obligation is the candidate's", "A simulation cannot show"),
        "criteria": ("0 km/h", "SC-DRIVING-012 at 20 km/h and at 42 km/h", "SC-DRIVING-013 at 30 km/h and at 60 km/h",
                     "at most 35 km/h", "SC-DRIVING-012 at 60 km/h"),
    },
    "reqDrivingCommandOverSCORE": {
        "statement": ("only over the Eclipse S-CORE path",),
        "rationale": ("design constraint", "vision_pilot.cpp:59-78", "vehicle_ros2_interface.cpp:25-26",
                      "gapScoreIntegration"),
        "criteria": ("autopilot", "traffic manager", "replayed", "overlaid", "is stopped",
                     "SC-DRIVING-012 to SC-DRIVING-015"),
    },
    "reqIsolateEmergencyBrakingFromSCORE": {
        "statement": ("prevent each failure of the Eclipse S-CORE path", "uncommanded emergency braking"),
        "rationale": ("REQ-MW-006", "protected emergency command path", "vision_pilot.cpp:157, 174",
                      "no freedom-from-interference claim"),
        "criteria": ("a loss, a delay, a repetition and a corruption", "phase 8"),
    },
    "reqWithholdWarningRequest": {
        "statement": ("While no collision with a vehicle ahead is imminent", "shall withhold its warning request"),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-008", "guidance, not as a test", "The obligation is the candidate's",
                      "A simulation cannot show"),
        "criteria": ("no warning request", "SC-DRIVING-014", "SC-DRIVING-015", "times to collision"),
    },
    "reqWithholdEmergencyBraking": {
        "statement": ("While no collision with a vehicle ahead is imminent", "shall withhold emergency braking"),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-012", "longitudinal_planning.cpp:13-14, 34",
                      "The obligation is the candidate's", "A simulation cannot show"),
        "criteria": ("no deceleration of 5.0 m/s² or more", "SC-DRIVING-014", "SC-DRIVING-015"),
    },
    "reqWarningRequestBeforeEmergencyBraking": {
        "statement": ("at its boundary", "at least 1.0 s of simulation time before the start of its emergency braking"),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-002", "0.8 s", "Of the 1.0 s, 0.2 s is allotted",
                      "each mode is due within 0.2 s of wall-clock time after the request", "AAOS SDV",
                      "planning.cpp:113-121", "The obligation is the candidate's", "A simulation cannot show"),
        "criteria": ("1.0 s of simulation time", "first emergency braking", "each judged run"),
    },
    "reqWarningRequestOverSCORE": {
        "statement": ("to the AAOS SDV only over the Eclipse S-CORE path",),
        "rationale": ("design constraint", "vision_pilot.cpp:177-185", "gapWarningOutput"),
        "criteria": ("is stopped", "AAOS SDV", "communication records of the Eclipse S-CORE path"),
    },
    "reqRecordCandidateIdentity": {
        "statement": ("before its first driving command of each run", "upstream revision",
                      "the difference between its source and that revision", "SHA-256 of each network file",
                      "SHA-256 of its configuration"),
        "rationale": ("source.mode", "vision_pilot.cpp:65-78", "speed_limit", "vision_pilot.conf:20", "System 2"),
        "criteria": ("another engineer", "non-empty difference"),
    },
}

#: Every term the requirements use in a sense of their own, each defined once in the terms comment.
TERM_HEADS = ("Vehicle", "Vehicle ahead", "Run", "Setting", "Functional part", "Judged run", "Time to collision",
              "Imminent collision", "Driving command", "Actuation", "Warning request", "Emergency braking",
              "Uncommanded emergency braking", "Eclipse S-CORE path", "Configuration", "Relative approach speed",
              "Relative impact speed", "Maximum relative impact speed", "Simulation time")
#: The values the terms fix: the settings, the functional part, the judged run, the emergency braking and the limits.
TERM_VALUES = ("20 to 22 km/h", "40 to 42 km/h", "58 to 60 km/h", "30 to 32 km/h", "18 to 20 km/h", "28 to 30 km/h",
               "38 to 40 km/h", "at most 25 m radius", "at least 4 s", "within 0.2 m", "at least 2 s",
               "at least 5.0 m/s²", "35 km/h at 60 km/h", "0 km/h up to 42 km/h", "run twice, and both runs count",
               "Wall-clock time")
#: The rules the terms fix, each a decision of phase 5.
TERM_RULES = ("It starts with the first such command after a command for less.",
              "take a collision as imminent in every judged run",
              "and in no run of SC-DRIVING-014 or SC-DRIVING-015",
              "until the vehicle hits the target or comes to the speed of the target",
              "is reported with what it missed and is not judged",
              "that is not the newest command of the driver-assistance system",
              "a loss, a delay, a repetition or a corruption of a message on it",
              "Between two of these speeds, the limit of the higher one applies.")
#: What the gap comment on gapVehicleTargetCriteria must name: the requirements, the obligations and what stays open.
GAP_FRAGMENTS = ("REQ-DRIVING-036", "REQ-DRIVING-037", "REQ-DRIVING-040", "REQ-DRIVING-041", "REQ-DRIVING-042",
                 "System 2", "AAOS SDV", "0.2 s", "SC-DRIVING-014", "SC-DRIVING-015", "Open:")
GAP_COMMENT = "comment vehicleTargetCriteriaFixedInPhase5 about DE4SDV_DriverAssistanceFraming::gapVehicleTargetCriteria"
#: What the package header must say of phase 5.
HEADER_FRAGMENTS = ("Phase 5: the requirements derived from these needs", "SRC-UNECE-R152", "REQ-AEBS-012",
                    "The requirements are not core", "visionPilotDrivingStack",
                    "phase 9 adds that feature to the feature model", "upstream.md gives each with its path")

#: Wording that belongs to the review of the answer, carried by a statement of none.
STATEMENT_REVIEW_WORDING = ("autopilot", "replay", "overlay")
#: The review wording that the success criteria of the authority requirement carry.
CRITERIA_REVIEW_WORDING = ("autopilot", "traffic manager", "replayed", "overlaid")
#: Claims the charter excludes.
EXCLUDED = re.compile(r"(?i)\b(certif\w*|homologat\w*|complian\w*|type approval|on-road|production-ready|member product)\b")

CONCERN = "driverAssistanceRequirementTraceConcern"
#: Owner decision of 2026-11-04 (the workflow's views per phase): phase 5 has one table, typed by
#: SystemRequirementDefinitionViewpoint, never a second form of the same requirements.
VIEW = "driverAssistanceRequirementsView"
COLUMNS = ["ID", "Requirement", "Statement", "Source", "Rationale", "Method", "Criteria"]
#: a clause or section number of an external source: the repository names its source records only
CLAUSE_NUMBER = re.compile(r"(?i)\b(?:annex|paragraph|clause|appendix|section)\s+\d|§\s*\d|\b\d+(?:\.\d+){2,}\b")

REQUIREMENT_PATTERN = re.compile(
    r"\brequirement\s+<'([^']+)'>\s+(\w+)\s*:\s*(FunctionalRequirementCandidate|RequirementCandidate)\b")


def _raw() -> str:
    assert MODEL.is_file(), "phase 5 of INC-DRIVING-002 adds its requirements to the needs model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _requirement(name: str) -> str:
    short, _need, kind, _method = REQUIREMENTS[name]
    return braced_body(_raw(), f"requirement <'{short}'> {name} : {kind}")


def _attribute(body: str, attribute: str) -> str:
    match = re.search(rf'\battribute\s+:>>\s+{attribute}\s*=\s*"([^"]*)"\s*;', body)
    assert match, f"missing {attribute}"
    return match.group(1)


def _statement(body: str) -> str:
    match = re.search(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*(.*?)\*/\s*\}', body, re.S)
    assert match, "missing the English require constraint statement"
    return _flat(match.group(1))


def _texts(name: str) -> dict[str, str]:
    body = _requirement(name)
    return {"statement": _statement(body), "rationale": _attribute(body, "rationale"),
            "criteria": _attribute(body, "successCriteria")}


def test_the_requirements_are_exactly_the_nine_of_phase_5_in_order():
    declared = REQUIREMENT_PATTERN.findall(_code())
    assert declared == [(short, name, kind) for name, (short, _need, kind, _method) in REQUIREMENTS.items()]
    assert len(declared) == 9
    assert len(declared) <= SCOPE_CAP, "the charter's scope cap: at most ten requirements"
    assert [short for short, _name, _kind in declared] == [f"REQ-DRIVING-{n:03d}" for n in range(36, 45)], \
        "REQ-DRIVING-036 to REQ-DRIVING-044, contiguous, in order"


def test_each_requirement_has_its_subject_one_statement_and_its_attributes():
    # SpecifyRequirements: requirementHasStatement, requirementHasOneSubject, requirementHasVerificationMethod,
    # and the advisories requirementSubjectIsSystemOfInterest and requirementStatesSuccessCriteria.
    for name, (_short, _need, _kind, method) in REQUIREMENTS.items():
        body = _requirement(name)
        code = strip_comments(body)
        assert SUBJECT_LINE in body, name
        assert len(re.findall(r"\bsubject\b", code)) == 1, (name, "one subject")
        assert len(re.findall(r"\brequire\s+constraint\s+statement\s*\{\s*language\s+\"English\"\s*/\*", body)) == 1, \
            (name, "one English statement")
        assert len(re.findall(r"\brequire\b", code)) == 1, (name, "one require constraint")
        for attribute in ("source", "rationale", "verificationMethod", "successCriteria"):
            assert _attribute(body, attribute), (name, attribute)
        assert _attribute(body, "verificationMethod") == method, name
        assert _attribute(body, "successCriteria").startswith("Met when"), name
        assert "attribute :>> verificationStatus = VVStatus::NotStarted;" in body, name


def test_each_statement_holds_one_obligation_in_the_positive_form():
    for name in REQUIREMENTS:
        statement = _statement(_requirement(name))
        assert statement.count(" shall ") == 1, (name, "one obligation per statement")
        assert len(statement.split()) <= 60, (name, len(statement.split()))
        assert not re.search(r"\bnot\b", statement), (name, "the positive form")
        assert "n't" not in statement, (name, "the positive form")
        for wording in STATEMENT_REVIEW_WORDING:
            assert wording not in statement.lower(), (name, wording)


def test_each_source_leads_with_its_need_and_wraps_in_its_column():
    for name, (_short, need, _kind, _method) in REQUIREMENTS.items():
        source = _attribute(_requirement(name), "source")
        assert source.startswith(NEED_SHORT[need]), (name, source)
        assert source == SOURCES[name], (name, source)
        longest = max(source.split(), key=len)
        assert len(longest) <= 40, (name, longest)


def test_the_rationale_and_the_criteria_wrap_in_their_columns():
    # The table shows both; a path longer than its column runs past the edge, so upstream.md holds the full paths.
    for name in REQUIREMENTS:
        texts = _texts(name)
        for field in ("rationale", "criteria"):
            longest = max(texts[field].split(), key=len)
            assert len(longest) <= 40, (name, field, longest)
        assert "VisionPilot/" not in texts["rationale"], name


def test_the_statements_rationales_and_criteria_carry_their_fragments():
    assert list(FRAGMENTS) == list(REQUIREMENTS)
    for name, fields in FRAGMENTS.items():
        texts = _texts(name)
        for field, fragments in fields.items():
            for fragment in fragments:
                assert fragment in texts[field], (name, field, fragment)


def test_the_requirement_texts_make_no_claim_the_charter_excludes():
    for name in REQUIREMENTS:
        for field, text in _texts(name).items():
            assert not EXCLUDED.findall(text), (name, field, EXCLUDED.findall(text))


def test_the_review_conditions_are_success_criteria_not_statements():
    # SC-DRIVING-016 asks that no autopilot, replay or overlay acts instead of the candidate; it is a criterion
    # of the authority requirement and wording of no statement.
    criteria = _attribute(_requirement("reqDrivingCommandOverSCORE"), "successCriteria")
    for wording in CRITERIA_REVIEW_WORDING:
        assert wording in criteria, wording
    for name in REQUIREMENTS:
        statement = _statement(_requirement(name)).lower()
        for wording in CRITERIA_REVIEW_WORDING:
            assert wording not in statement, (name, wording)


def test_the_warning_lead_is_in_simulation_time_and_its_share_in_wall_clock_time():
    body = _requirement("reqWarningRequestBeforeEmergencyBraking")
    assert "simulation time" in _statement(body)
    assert "wall-clock time" in _attribute(body, "rationale")


def test_each_requirement_derives_from_its_need_through_derives_from_need_only():
    # requirementDerivesFromNeed counts DerivesFromNeed only; a plain dependency to a need does not count
    # and is not declared.
    code = _code()
    derivations = re.findall(r"\bconnection\s+\w+\s*:\s*DerivesFromNeed\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    assert len(derivations) == 9
    expected = [(need, name) for name, (_short, need, _kind, _method) in REQUIREMENTS.items()]
    assert sorted(derivations) == sorted(expected)
    assert {need for need, _name in derivations} == set(NEED_SHORT), "every need of phase 4 has a requirement"
    plain = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
    assert not [pair for pair in plain if pair[0] in REQUIREMENTS and pair[1].split("::")[-1] in NEED_SHORT]


def test_the_terms_of_the_requirements_are_defined_once_in_the_package():
    match = re.search(r"\bcomment\s+termsOfTheDriverAssistanceRequirements\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, "one comment defines the terms of the requirements"
    text = _flat(match.group(1))
    for head in TERM_HEADS:
        assert f"- {head}:" in text, head
    for value in TERM_VALUES:
        assert value in text, value
    for rule in TERM_RULES:
        assert rule in text, rule


def test_the_vehicle_target_criteria_gap_records_what_phase_5_fixed_and_what_stays_open():
    match = re.search(rf"{re.escape(GAP_COMMENT)}\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, "a comment on gapVehicleTargetCriteria records what phase 5 fixed"
    text = _flat(match.group(1))
    for fragment in GAP_FRAGMENTS:
        assert fragment in text, fragment


def test_the_header_states_phase_5():
    match = re.search(r"/\*(.*?)\*/", _raw(), re.S)
    assert match, "the package header"
    header = _flat(match.group(1))
    for fragment in HEADER_FRAGMENTS:
        assert fragment in header, fragment


def test_the_phase_4_contract_comment_is_now_stated_in_the_rationales():
    # Phase 4 kept the runtime contract of VisionPilot at the pin as a comment for phase 5. Phase 5 states its
    # facts in the rationales, so the comment no longer earns its place.
    assert "visionPilotContractAtPin" not in _raw()


def test_no_requirement_links_a_feature_before_phase_9_adds_it():
    # Phase 3 records VisionPilot as the feature candidate visionPilotDrivingStack; phase 9 adds it to the feature
    # model. Until then no requirement and not the system of interest depends on a feature.
    code = _code()
    assert not re.search(r"\bimport\s+DE4SDV_ProductLine\w*", code)
    assert "DE4SDV_SDVProductLineFeatureModel" not in code
    assert "visionPilotDrivingStack" not in code


def _columns(body: str) -> list[str]:
    return re.findall(r"\bview\s+(\w+)\s*:>\s*columnViews\s*\{", body)


def _column(body: str, column: str) -> str:
    return braced_body(body, f"view {column} :> columnViews")


def _attribute_column(body: str, column: str, attribute: str) -> bool:
    return bool(re.search(rf'CT::attributeValue\s*\{{\s*attribute\s+attributeName\s*=\s*"{attribute}"\s*;\s*\}}',
                          _column(body, column)))


def test_one_table_defines_each_requirement_with_its_verification_and_frames_the_trace_concern():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*RequirementTraceConcern\b", code)
    assert concerns == [CONCERN]
    concern = braced_body(code, f"concern {CONCERN} : RequirementTraceConcern")
    assert re.search(r"\bsubject\s*;", concern)
    holders = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern))
    assert holders == {"ComplianceEngineer", "VerificationEngineer"}
    doc = re.search(r"\bdoc\s*/\*(.*?)\*/", braced_body(_raw(), f"concern {CONCERN} : RequirementTraceConcern"), re.S)
    assert doc and "vehicleTargetCriteriaConcern" in _flat(doc.group(1)), "the table answers the criteria concern"

    framing = []
    for view in re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code):
        body = braced_body(code, f"view {view} : TVD::TableView")
        if re.search(rf"\bframe\s+{CONCERN}\s*;", body):
            framing.append(view)
    assert framing == [VIEW], "one table for phase 5, not two forms of the same requirements"
    body = braced_body(code, f"view {VIEW} : TVD::TableView")
    assert re.search(rf"\bviewpoint\s+\w+\s*:\s*SystemRequirementDefinitionViewpoint\s*\{{\s*frame\s+{CONCERN}\s*;"
                     r"\s*\}", body)
    assert re.findall(r"\bexpose\s+([^;]+);", body) == list(REQUIREMENTS)
    assert "filter @ SysML::RequirementUsage;" in body
    assert "attribute :>> includeReferenceElements = true;" in body
    assert "attribute :>> maxRowHeight = 500;" in body
    assert _columns(body) == COLUMNS
    assert re.search(r"featureToRender\s*=\s*CT::reqId\s*;", _column(body, "ID"))
    assert re.search(r"featureToRender\s*=\s*CT::declaredName\s*;", _column(body, "Requirement"))
    statement = _column(body, "Statement")
    assert re.search(r'CT::constraintLanguage\s*\{\s*attribute\s+constraintName\s*=\s*"statement"\s*;', statement)
    assert re.search(r'attribute\s+constraintLanguage\s*=\s*"English"\s*;', statement)
    assert "attribute :>> columnWidth = 360;" in statement
    for column, attribute in (("Source", "source"), ("Rationale", "rationale"), ("Method", "verificationMethod"),
                              ("Criteria", "successCriteria")):
        assert _attribute_column(body, column, attribute), column
    assert "attribute :>> columnWidth = 420;" in _column(body, "Rationale")
    assert "attribute :>> columnWidth = 360;" in _column(body, "Criteria")


def test_the_guide_states_phase_5_and_the_next_obligation():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Requirements (Phase 5)" in guide
    raw_section = guide.split("## Requirements (Phase 5)", 1)[1].split("\n## ", 1)[0]
    for short, _need, _kind, _method in REQUIREMENTS.values():
        assert f"`{short}`" in raw_section, short
    assert "](../../textual-notation-of-model/packages/features/driving/driver_assistance_needs_requirements.sysml)" \
        in raw_section
    assert not CLAUSE_NUMBER.findall(raw_section), CLAUSE_NUMBER.findall(raw_section)
    assert "VisionPilot/" not in raw_section, "the guide carries no upstream paths"
    flat = " ".join(guide.split())  # Markdown: a line may open with bold text
    assert "The next model obligation is **Phase 6**: the functional architecture" in flat
    assert "its first gate is `functionalRequirementAllocatedToFunction`" in flat


def test_the_upstream_record_gives_each_cited_file_with_its_path():
    # The header says so: the rationales name the files of VisionPilot by file name, upstream.md by path and line.
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    paths = re.findall(r"\[VisionPilot/([^\]]+)\]\(https://github\.com/autowarefoundation/vision_pilot/blob/"
                       rf"{PIN}/VisionPilot/\1#L\d+(?:-L\d+)?\)", record)
    cited = set()
    for name in REQUIREMENTS:
        cited |= set(re.findall(r"\b([\w.]+\.(?:cpp|hpp|conf)):\d", _texts(name)["rationale"]))
    assert len(cited) == 5, cited
    assert sorted(cited) == sorted(path.rsplit("/", 1)[-1] for path in paths), (cited, paths)
