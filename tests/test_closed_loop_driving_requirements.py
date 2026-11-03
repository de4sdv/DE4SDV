"""Content pins for the closed-loop driving requirements (phase 5), not semantic validation.

INC-DRIVING-001 phase 5 derives the design-input requirements of the candidate driving system from the seven
needs of phase 4. The SpecifyRequirements rules of the increment workflow are checked by Method Check; these
pins hold what review settled on top of them:

- the requirement set itself, each with its need, its kind and its verification method;
- the form of the pinned checkpoint's inputs, kept as a comment on NEED-DRIVING-001 in phase 4, now stated
  as requirements, each number citing the source at the checkpoint pin;
- every limit stated in its time domain: simulation time for what the vehicle lives through, wall-clock time
  for what the host does;
- the no-autopilot, replay or overlay condition of SC-DRIVING-005 as a success criterion, never as wording
  of a statement;
- no claim the charter excludes, and no feature link before phase 9 adds the feature.
"""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "closed_loop_driving_needs_requirements.sysml"
SYSTEM_OF_INTEREST = "DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem"
CHECKPOINT_PIN = "cb50764b"

NEED_SHORT = {
    "needDrivenAlongTheRoute": "NEED-DRIVING-001",
    "needPlansAndCommandsThroughSCORE": "NEED-DRIVING-002",
    "needLiveStateForAAOS": "NEED-DRIVING-003",
    "needLoopIndependentOfAAOS": "NEED-DRIVING-004",
    "needDefinedResponseToDegradedInputOrPlan": "NEED-DRIVING-005",
    "needTimesMeasurableInTheirOwnDomain": "NEED-DRIVING-006",
    "needRunsIdentifyCheckpointAndConfiguration": "NEED-DRIVING-007",
}

F = "FunctionalRequirementCandidate"
R = "RequirementCandidate"

#: Each requirement, in declaration order: its short name, the need it derives from, its definition, its one
#: verification method, the fragments its statement must carry, and the fragments its rationale must carry
#: (the citations of its numbers at the checkpoint pin).
REQUIREMENTS = {
    "reqPlanEachStepByCheckpointInference": (
        "REQ-DRIVING-012", "needDrivenAlongTheRoute", F, "test",
        ("one plan for each 100 ms step of simulation time", "pinned AutoE2E checkpoint"),
        (CHECKPOINT_PIN, "MODEL_HZ", "kinematics.py")),
    "reqCameraImagesInCheckpointForm": (
        "REQ-DRIVING-013", "needDrivenAlongTheRoute", F, "test",
        ("six cameras", "front, front left, front right, rear left, rear and rear right", "512 by 512 pixels",
         "1024 by 1024 pixels", "0.5 s to 3.5 s", "projection operator"),
        (CHECKPOINT_PIN, "reactive_training_contracts.py", "camera_slots.py")),
    "reqRouteAsNavigationRasters": (
        "REQ-DRIVING-014", "needDrivenAlongTheRoute", F, "test",
        ("map_context", "14 channels", "route_mask", "route corridor and destination",
         "autoe2e-bev-450x300-0p4m-v1", "450 by 300 pixels at 0.4 m per pixel"),
        (CHECKPOINT_PIN, "geometry.py", "256 by 256")),
    "reqEgoMotionHistoryOfCommandedVehicle": (
        "REQ-DRIVING-015", "needDrivenAlongTheRoute", F, "test",
        ("64 motion samples of the vehicle it commands", "100 ms apart", "speed in m/s", "yaw rate in rad/s",
         "curvature in 1/m"),
        (CHECKPOINT_PIN, "temporal_contract.py", "egomotion.py")),
    "reqNoMotionBeforeHistoriesComplete": (
        "REQ-DRIVING-016", "needDrivenAlongTheRoute", F, "test",
        ("no motion until", "a copy or an estimate"),
        (CHECKPOINT_PIN, "reactive_e2e.py", "asmSourceAuthenticity")),
    "reqCommandsOnlyFromNewestPlan": (
        "REQ-DRIVING-017", "needDrivenAlongTheRoute", F, "test",
        ("only from its newest valid plan",),
        ("gapModelInputAndFeedback", "SC-DRIVING-005")),
    "reqPlanWithinPlanningPeriod": (
        "REQ-DRIVING-018", "needDrivenAlongTheRoute", R, "test",
        ("within 100 ms of wall-clock time",),
        ("BENCHMARKS.md", "gapClosedLoopPerformance")),
    "reqPlansAndCommandsOverSCORE": (
        "REQ-DRIVING-019", "needPlansAndCommandsThroughSCORE", F, "test",
        ("only over Eclipse S-CORE communication",),
        ("REQ-DRIVING-026",)),
    "reqPublishPlanStateAndHealth": (
        "REQ-DRIVING-020", "needLiveStateForAAOS", F, "test",
        ("producer", "production time", "within 100 ms of wall-clock time"),
        ()),
    "reqPublishHealthPeriodically": (
        "REQ-DRIVING-021", "needLiveStateForAAOS", F, "test",
        ("priming, driving or stopped", "at least every 200 ms of wall-clock time"),
        ("500 ms", "SC-DRIVING-007")),
    "reqLoopIndependentOfObservation": (
        "REQ-DRIVING-022", "needLoopIndependentOfAAOS", R, "test",
        ("on time, late or not at all",),
        ()),
    "reqDefinedStopResponse": (
        "REQ-DRIVING-023", "needDefinedResponseToDegradedInputOrPlan", F, "test",
        ("4 m/s²", "standstill", "last valid command"),
        (CHECKPOINT_PIN, "-4.05 m/s²", "no safety claim")),
    "reqStopOnDegradedInput": (
        "REQ-DRIVING-024", "needDefinedResponseToDegradedInputOrPlan", F, "test",
        ("more than 200 ms", "more than 1 s old", "no route corridor", "within 100 ms of simulation time"),
        ("RASTER_HZ", "simulation time")),
    "reqStopOnInvalidOrStalePlan": (
        "REQ-DRIVING-025", "needDefinedResponseToDegradedInputOrPlan", F, "test",
        ("more than 300 ms old", "64 finite pairs of acceleration and curvature",
         "within 100 ms of simulation time"),
        ("gru_planner.py", "REQ-DRIVING-018")),
    "reqStopOnLostCommands": (
        "REQ-DRIVING-026", "needDefinedResponseToDegradedInputOrPlan", F, "test",
        ("200 ms of simulation time", "at the actuation"),
        ()),
    "reqPublishStop": (
        "REQ-DRIVING-027", "needDefinedResponseToDegradedInputOrPlan", F, "test",
        ("within 100 ms of wall-clock time", "stopped"),
        ()),
    "reqTimesInTheirOwnDomain": (
        "REQ-DRIVING-028", "needTimesMeasurableInTheirOwnDomain", F, "test",
        ("simulation time for capture, sample and actuation times", "monotonic clock"),
        ("0.1 s",)),
    "reqRecordCheckpointSourceAndConfiguration": (
        "REQ-DRIVING-029", "needRunsIdentifyCheckpointAndConfiguration", F, "test",
        ("SHA-256 of the checkpoint file", "AutoE2E source revision", "complete configuration"),
        ("inference.py", "System 2")),
    "reqRefuseUnpinnedCheckpoint": (
        "REQ-DRIVING-030", "needRunsIdentifyCheckpointAndConfiguration", F, "test",
        ("no plan", "SHA-256"),
        ("UNTRAINED_CHECKPOINT", "asmSourceAuthenticity")),
}

#: Wording that belongs to the review of the answer, carried by the success criteria, not by a statement.
REVIEW_WORDING = ("autopilot", "replay", "overlay")

REQUIREMENT_PATTERN = re.compile(
    r"\brequirement\s+<'(REQ-DRIVING-\d{3})'>\s+(\w+)\s*:\s*(FunctionalRequirementCandidate|RequirementCandidate)\b")


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _requirement(name: str) -> str:
    short, _need, kind, *_rest = REQUIREMENTS[name]
    return braced_body(_raw(), f"requirement <'{short}'> {name} : {kind}")


def _attribute(body: str, attribute: str) -> str:
    match = re.search(rf'\battribute\s+:>>\s+{attribute}\s*=\s*"([^"]*)"\s*;', body)
    assert match, f"missing {attribute}"
    return match.group(1)


def _statement(body: str) -> str:
    match = re.search(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*(.*?)\*/\s*\}', body, re.S)
    assert match, "missing the English require constraint statement"
    return _flat(match.group(1))


def test_the_requirements_are_exactly_the_nineteen_of_phase_5_in_order():
    declared = REQUIREMENT_PATTERN.findall(_code())
    assert declared == [(short, name, kind) for name, (short, _need, kind, *_rest) in REQUIREMENTS.items()]
    # The short names continue past SC-DRIVING-011, the last planned review of phase 4.
    assert [short for short, *_rest in declared] == [f"REQ-DRIVING-{n:03d}" for n in range(12, 31)]
    elsewhere = [path.name for path in DRIVING.glob("*.sysml") if path != MODEL
                 and re.search(r"<'REQ-DRIVING-\d{3}'>", path.read_text(encoding="utf-8"))]
    assert not elsewhere, f"REQ-DRIVING short names are declared only here: {elsewhere}"


def test_each_requirement_has_one_statement_subject_source_rationale_method_criteria_and_status():
    # SpecifyRequirements: requirementHasStatement, requirementHasOneSubject, requirementHasVerificationMethod,
    # and the advisories requirementSubjectIsSystemOfInterest and requirementStatesSuccessCriteria.
    for name, (_short, need, _kind, method, _statement_parts, _rationale_parts) in REQUIREMENTS.items():
        body = _requirement(name)
        code = strip_comments(body)
        subjects = re.findall(r"\bsubject\s+(\w+)\s*:>\s*([\w:]+)\s*;", code)
        assert subjects == [("drivingSystem", SYSTEM_OF_INTEREST)], (name, subjects)
        statement = _statement(body)
        assert len(re.findall(r"\bshall\b", statement)) == 1, (name, "one obligation per statement")
        assert "the driving system" in statement.lower(), name
        assert _attribute(body, "source").startswith(f"{NEED_SHORT[need]};"), name
        assert len(_attribute(body, "rationale")) > 120, name
        assert _attribute(body, "verificationMethod") == method, name
        criteria = _attribute(body, "successCriteria")
        assert criteria.startswith("Met when"), name
        assert re.search(r"\battribute\s+:>>\s+verificationStatus\s*=\s*VVStatus::NotStarted\s*;", code), name


def test_each_requirement_derives_from_its_need_through_derives_from_need_only():
    # requirementDerivesFromNeed counts DerivesFromNeed only; a plain dependency to a need does not count
    # and is not declared.
    code = _code()
    derivations = re.findall(r"\bconnection\s+\w+\s*:\s*DerivesFromNeed\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    expected = [(need, name) for name, (_short, need, *_rest) in REQUIREMENTS.items()]
    assert sorted(derivations) == sorted(expected)
    assert {need for need, _name in derivations} == set(NEED_SHORT), "every need has a requirement"
    plain = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+(\w+)\s*;", code)
    assert not [pair for pair in plain if pair[0] in REQUIREMENTS and pair[1] in NEED_SHORT]


def test_the_statements_carry_their_values_and_the_rationales_cite_the_pinned_source():
    for name, (*_head, statement_parts, rationale_parts) in REQUIREMENTS.items():
        body = _requirement(name)
        statement = _statement(body)
        rationale = _attribute(body, "rationale")
        for part in statement_parts:
            assert part in statement, (name, part)
        for part in rationale_parts:
            assert part in rationale, (name, part)


def test_the_checkpoint_input_contract_is_now_stated_as_requirements_and_its_comment_is_gone():
    # Phase 4 kept the form of the checkpoint's inputs as a comment on NEED-DRIVING-001 for phase 5.
    # Phase 5 states it as REQ-DRIVING-013 to REQ-DRIVING-016, so the comment no longer earns its place.
    assert "checkpointInputContractForPhase5" not in _raw()
    inputs = ("reqCameraImagesInCheckpointForm", "reqRouteAsNavigationRasters",
              "reqEgoMotionHistoryOfCommandedVehicle", "reqNoMotionBeforeHistoriesComplete")
    for name in inputs:
        assert REQUIREMENTS[name][1] == "needDrivenAlongTheRoute"
        assert "gapModelInputAndFeedback" in _attribute(_requirement(name), "source"), name


def test_each_limit_is_stated_in_its_time_domain():
    # NEED-DRIVING-006 and gapClosedLoopPerformance: what the vehicle lives through is counted in simulation
    # time, what the host does in wall-clock time; no limit is stated without its domain.
    simulation = ("reqPlanEachStepByCheckpointInference", "reqStopOnDegradedInput", "reqStopOnInvalidOrStalePlan",
                  "reqStopOnLostCommands")
    wall_clock = ("reqPlanWithinPlanningPeriod", "reqPublishPlanStateAndHealth", "reqPublishHealthPeriodically",
                  "reqPublishStop")
    for name in simulation:
        statement = _statement(_requirement(name))
        assert "simulation time" in statement and "wall-clock" not in statement, name
    for name in wall_clock:
        statement = _statement(_requirement(name))
        assert "wall-clock time" in statement and "simulation time" not in statement, name


def test_the_review_conditions_are_success_criteria_not_statements():
    # SC-DRIVING-005 checks that no autopilot, replay or overlay moves the vehicle; phase 4 left that to
    # phase 5 as a verification criterion. It is a criterion of REQ-DRIVING-017 and wording of no statement.
    for name in REQUIREMENTS:
        statement = _statement(_requirement(name)).lower()
        for wording in REVIEW_WORDING:
            assert wording not in statement, (name, wording)
    criteria = _attribute(_requirement("reqCommandsOnlyFromNewestPlan"), "successCriteria")
    assert "autopilot" in criteria and "replayed" in criteria
    assert "opposite curvature sign" in criteria


def test_the_requirement_texts_make_no_claim_the_charter_excludes():
    text = " ".join(_statement(_requirement(name)) + " " + _attribute(_requirement(name), "rationale") + " "
                    + _attribute(_requirement(name), "successCriteria") for name in REQUIREMENTS)
    assert not re.search(r"\b(certif\w*|homologat\w*|on-road|member product|UNECE|R152|production-ready)\b",
                         text, re.I)


def test_no_requirement_links_a_feature_before_phase_9_adds_it():
    # Phase 3 records AutoE2E as the feature candidate autoE2EDrivingStack; phase 9 adds it to the feature
    # model. Until then no requirement and not the system of interest depends on a feature, and the package
    # says the requirements are not core.
    code = _code()
    assert "DE4SDV_SDVProductLineFeatureModel" not in code
    header = _flat(_raw().split("package DE4SDV_ClosedLoopDrivingNeedsRequirements", 1)[0])
    assert "autoE2EDrivingStack" in header and "not core" in header


def test_the_performance_gap_records_what_phase_5_fixed_and_what_stays_with_the_bench():
    match = re.search(r"comment\s+(\w+)\s+about\s+DE4SDV_ClosedLoopDrivingFraming::gapClosedLoopPerformance\s*"
                      r"/\*(.*?)\*/", _raw(), re.S)
    assert match, "a comment on gapClosedLoopPerformance records what phase 5 fixed"
    text = _flat(match.group(2))
    for item in ("SC-DRIVING-001", "REQ-DRIVING-013", "REQ-DRIVING-018", "REQ-DRIVING-024", "REQ-DRIVING-026",
                 "System 2", "readiness probe"):
        assert item in text, item


def test_two_tables_frame_the_requirement_trace_concern_and_show_statements_and_verification():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*RequirementTraceConcern\b", code)
    assert concerns == ["closedLoopDrivingRequirementTraceConcern"]
    concern = braced_body(code, "concern closedLoopDrivingRequirementTraceConcern : RequirementTraceConcern")
    assert re.search(r"\bsubject\s*;", concern)
    holders = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern))
    assert holders == {"VerificationEngineer", "OpenSourceReviewer"}
    views = {}
    for view in re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code):
        body = braced_body(code, f"view {view} : TVD::TableView")
        if re.search(r"\bframe\s+closedLoopDrivingRequirementTraceConcern\s*;", body):
            assert re.search(r"\bviewpoint\s+\w+\s*:\s*SystemRequirementTraceabilityViewpoint\s*\{", body), view
            assert re.findall(r"\bexpose\s+([^;]+);", body) == list(REQUIREMENTS), view
            assert re.search(r"\bfilter\s+@\s*SysML::RequirementUsage\s*;", body), view
            assert re.search(r"\bview\s+ID\s*:>\s*columnViews\s*\{[^}]*CT::reqId\s*;", body), view
            views[view] = body
    assert sorted(views) == ["closedLoopDrivingRequirementVerificationView", "closedLoopDrivingRequirementsView"]
    statements = views["closedLoopDrivingRequirementsView"]
    assert 'constraintName = "statement"' in statements
    assert re.search(r'attributeName\s*=\s*"source"\s*;', statements)
    verification = views["closedLoopDrivingRequirementVerificationView"]
    assert re.search(r'attributeName\s*=\s*"verificationMethod"\s*;', verification)
    assert re.search(r'attributeName\s*=\s*"successCriteria"\s*;', verification)


def test_no_source_holds_a_token_too_long_to_wrap_in_its_table_column():
    for name in REQUIREMENTS:
        longest = max(re.split(r"[\s(]+", _attribute(_requirement(name), "source")), key=len)
        assert len(longest) <= 40, (name, longest)
