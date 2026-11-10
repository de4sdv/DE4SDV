"""Content pins for the closed-loop driving requirements (phase 5), not semantic validation.

INC-DRIVING-001 phase 5 derives the design-input requirements of the candidate driving system from the seven
needs of phase 4. The SpecifyRequirements rules of the increment workflow are checked by Method Check; these
pins hold what review settled on top of them:

- the requirement set itself, each with its need, its kind and its verification method; design constraints
  (the checkpoint, its input form, the S-CORE path) and performance limits are RequirementCandidate, so that
  the phase 6 gate asks a function only of the functional requirements;
- requirement-writing rules: one obligation per statement (one `shall`, at most 60 words), the positive form
  where one exists, a tolerance instead of "the same" where the criteria accept a measured spread, and the
  terms the statements use defined once in the package;
- the form of the pinned checkpoint's inputs, kept as a comment on NEED-DRIVING-001 in phase 4, now stated
  as requirements, each number taken from the source citing it at the checkpoint pin;
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
N1, N2, N3, N4, N5, N6, N7 = NEED_SHORT.values()

#: Each requirement, in declaration order: the need it derives from, its definition, the fragments its
#: statement must carry, and the fragments its rationale must carry (the citations of values taken from the
#: source at the checkpoint pin, and the reasons of values set here). Short names run REQ-DRIVING-001 on.
REQUIREMENTS = {
    "reqPlanEachStep": (
        N1, F, ("one plan for each 100 ms step of simulation time, leaving a step without a plan of its own only when "
                "the step before it has one",), (CHECKPOINT_PIN, "MODEL_HZ", "REQ-DRIVING-013", "REQ-DRIVING-026")),
    "reqPlansByCheckpointInference": (
        N1, R, ("by inference of the pinned AutoE2E checkpoint",), (CHECKPOINT_PIN, "kinematics.py", "design constraint")),
    "reqCameraImagesInCheckpointForm": (
        N1, R, ("six cameras", "front, front left, front right, rear left, rear and rear right", "512 by 512 pixels",
                "1024 by 1024 pixels"), (CHECKPOINT_PIN, "reactive_training_contracts.py", "camera_slots.py")),
    "reqCameraHistory": (N1, R, ("seven earlier images", "0.5 s to 3.5 s"), (CHECKPOINT_PIN, "reactive_training_contracts.py")),
    "reqProjectionOperators": (N1, R, ("projection operator", "vehicle frame of the step"), (CHECKPOINT_PIN, "auto_e2e.py")),
    "reqMapContextRaster": (
        N1, R, ("map_context", "14 channels", "autoe2e-bev-450x300-0p4m-v1", "450 by 300 pixels at 0.4 m per pixel"),
        (CHECKPOINT_PIN, "geometry.py", "256 by 256")),
    "reqRouteMaskRaster": (
        N1, R, ("route_mask", "route corridor and destination", "autoe2e-bev-450x300-0p4m-v1"),
        (CHECKPOINT_PIN, "RouteChannel")),
    "reqEgoMotionHistory": (
        N1, R, ("64 motion samples of the vehicle it commands", "100 ms apart", "speed in m/s",
                "longitudinal acceleration in m/s²", "yaw rate and curvature given as 0 rad/s and 0 1/m"),
        (CHECKPOINT_PIN, "temporal_contract.py", "egomotion.py", "GAP-DRIVING-010", "experiment/closed-loop/RESULTS.md")),
    "reqHoldUntilHistoriesComplete": (N1, F, ("hold the vehicle at standstill until",), ("REQ-DRIVING-004", "6.3 s")),
    "reqHistoriesFromCapturedInputs": (
        N1, R, ("only from images and samples captured in the run",), (CHECKPOINT_PIN, "reactive_e2e.py", "asmSourceAuthenticity")),
    "reqCommandsFromNewestValidPlan": (N1, F, ("only from its newest valid plan",), ("gapModelInputAndFeedback", "SC-DRIVING-005")),
    "reqCommandsWithinActuationLimits": (N1, F, ("limits of the vehicle that its configuration names",), (CHECKPOINT_PIN, "gru_planner.py")),
    "reqPlanWithinPlanningPeriod": (
        N1, R, ("within 100 ms of wall-clock time",), ("BENCHMARKS.md", "gapClosedLoopPerformance", "owner decision of 2026-11-03")),
    "reqPlansAndCommandsOverSCORE": (N2, R, ("only over Eclipse S-CORE communication",), ("design constraint", "REQ-DRIVING-028")),
    "reqPublishPlans": (N3, F, ("each plan", "producer", "production time", "within 100 ms of wall-clock time"), ()),
    "reqPublishVehicleState": (N3, F, ("motion sample of each step", "sample time", "within 100 ms of wall-clock time"), ()),
    "reqPublishHealthPeriodically": (N3, F, ("health at least every 200 ms of wall-clock time",), ("500 ms", "SC-DRIVING-007")),
    "reqPlansIndependentOfObservation": (N4, R, ("on time, late or not at all", "differ by no more than"), ("not bit-exact",)),
    "reqPlanningTimeIndependentOfObservation": (
        N4, R, ("on time, late or not at all", "99th percentile", "10 ms of wall-clock time"), ("REQ-DRIVING-013",)),
    "reqStopResponseDeceleration": (N5, F, ("While in the stop response", "4 m/s²", "standstill"),
                                    (CHECKPOINT_PIN, "-4.05 m/s²", "no safety claim")),
    "reqStopResponseSteeringHeld": (N5, F, ("While in the stop response", "last value computed from a valid plan"), ()),
    "reqStandstillAfterStop": (N5, F, ("hold the vehicle at standstill until the run ends",), ("validity rule",)),
    "reqStopOnDegradedCameraImages": (
        N5, F, ("any camera", "more than 200 ms of simulation time", "within 100 ms of simulation time"), ("two periods",)),
    "reqStopOnDegradedMotion": (
        N5, F, ("newest motion sample", "more than 200 ms of simulation time", "within 100 ms of simulation time"),
        ("REQ-DRIVING-008",)),
    "reqStopOnDegradedRoute": (
        N5, F, ("more than 1 s of simulation time", "no route corridor", "within 100 ms of simulation time"),
        (CHECKPOINT_PIN, "RASTER_HZ")),
    "reqStopOnStalePlan": (
        N5, F, ("more than 300 ms of simulation time", "within 100 ms of simulation time"), ("REQ-DRIVING-013",)),
    "reqStopOnInvalidPlan": (
        N5, F, ("64 finite pairs of acceleration and curvature", "within 100 ms of simulation time"),
        (CHECKPOINT_PIN, "gru_planner.py", "REQ-DRIVING-012")),
    "reqStopOnLostCommands": (N5, F, ("200 ms of simulation time", "at the actuation"), ()),
    "reqPublishStop": (N5, F, ("within 100 ms of wall-clock time", "stopped"), ("REQ-DRIVING-017",)),
    "reqStampInputs": (N6, F, ("capture time in simulation time",), ("simulation time",)),
    "reqStampPlans": (N6, F, ("in simulation time", "monotonic clock of the host"), ("0.1 s",)),
    "reqStampCommands": (N6, F, ("monotonic clock of the host", "actuation time in simulation time"), ("transport delay",)),
    "reqRecordRunIdentity": (
        N7, F, ("SHA-256 of the checkpoint file", "AutoE2E source revision", "complete configuration"),
        ("inference.py", "System 2")),
    "reqPlansNameRunRecord": (N7, F, ("in each plan", "run record"), ()),
    "reqRefuseUnpinnedCheckpoint": (
        N7, F, ("refuse to plan", "SHA-256"), ("UNTRAINED_CHECKPOINT", "MOCK_CHECKPOINT", "asmSourceAuthenticity")),
}

SHORT = {name: f"REQ-DRIVING-{n:03d}" for n, name in enumerate(REQUIREMENTS, start=1)}

#: Every term the statements use in a sense of their own, each defined once in termsOfTheDrivingRequirements.
TERMS = ("Run", "Step", "Motion sample", "Camera history and ego-motion history", "Priming", "Plan", "Valid plan",
         "Command", "Actuation", "Health", "Stop response", "Capture record")

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
    return braced_body(_raw(), f"requirement <'{SHORT[name]}'> {name} : {REQUIREMENTS[name][1]}")


def _attribute(body: str, attribute: str) -> str:
    match = re.search(rf'\battribute\s+:>>\s+{attribute}\s*=\s*"([^"]*)"\s*;', body)
    assert match, f"missing {attribute}"
    return match.group(1)


def _statement(body: str) -> str:
    match = re.search(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*(.*?)\*/\s*\}', body, re.S)
    assert match, "missing the English require constraint statement"
    return _flat(match.group(1))


def test_the_requirements_are_exactly_the_thirty_five_of_phase_5_in_order():
    declared = REQUIREMENT_PATTERN.findall(_code())
    assert declared == [(SHORT[name], name, kind) for name, (_need, kind, *_rest) in REQUIREMENTS.items()]
    elsewhere = [path.name for path in DRIVING.glob("*.sysml") if path != MODEL
                 and re.search(r"<'REQ-DRIVING-\d{3}'>", path.read_text(encoding="utf-8"))]
    assert not elsewhere, f"REQ-DRIVING short names are declared only here: {elsewhere}"


def test_each_requirement_has_one_statement_subject_source_rationale_method_criteria_and_status():
    # SpecifyRequirements: requirementHasStatement, requirementHasOneSubject, requirementHasVerificationMethod,
    # and the advisories requirementSubjectIsSystemOfInterest and requirementStatesSuccessCriteria.
    for name, (need, *_rest) in REQUIREMENTS.items():
        body = _requirement(name)
        code = strip_comments(body)
        subjects = re.findall(r"\bsubject\s+(\w+)\s*:>\s*([\w:]+)\s*;", code)
        assert subjects == [("drivingSystem", SYSTEM_OF_INTEREST)], (name, subjects)
        assert "the driving system" in _statement(body).lower(), name
        assert _attribute(body, "source").startswith(f"{need};"), name
        assert len(_attribute(body, "rationale")) > 100, name
        assert _attribute(body, "verificationMethod") == "test", name
        assert _attribute(body, "successCriteria").startswith("Met when"), name
        assert re.search(r"\battribute\s+:>>\s+verificationStatus\s*=\s*VVStatus::NotStarted\s*;", code), name


def test_each_statement_holds_one_obligation_in_the_positive_form():
    # Singularity: one `shall` and at most 60 words, so that a statement does not bundle obligations a
    # verifier checks separately. The positive form where one exists: hold, refuse, keep.
    for name in REQUIREMENTS:
        statement = _statement(_requirement(name))
        assert len(re.findall(r"\bshall\b", statement)) == 1, (name, "one obligation per statement")
        assert len(statement.split()) <= 60, (name, len(statement.split()))
        assert not re.search(r"\bshall\s+(command|produce|give|make)\s+no\b", statement), name


def test_the_ego_motion_history_gives_yaw_rate_and_curvature_as_zero_under_the_bounded_deviation():
    # The history-mask decision of 2026-11-09: fed back closed loop, the checkpoint's own yaw history turned its
    # plans off the lane (upstream's closed-loop results at the pin, and the readiness probe in CARLA). The history
    # keeps the measured speed and acceleration and gives yaw rate and curvature as zero.
    requirement = _requirement("reqEgoMotionHistory")
    criteria = _attribute(requirement, "successCriteria")
    assert "each within 0.05 m/s and 0.1 m/s² of the speed and acceleration that the simulator reports" in criteria
    assert "and each with a yaw rate of 0 rad/s and a curvature of 0 1/m" in criteria
    for gone in ("0.01 rad/s", "0.001 1/m"):
        assert gone not in criteria, gone
    assert "GAP-DRIVING-010" in _attribute(requirement, "source")
    rationale = _attribute(requirement, "rationale")
    assert "the bounded deviation of asmSourceAuthenticity (owner decision of 2026-11-09)" in rationale
    assert "This closes the loop: the motion the commands produce is what the next plan is made from." not in rationale


def test_the_history_rationale_says_what_the_readiness_probe_showed_with_the_two_columns_zero():
    # The readiness probe's own record: with the two columns zero the plans no longer turned off the lane within
    # seconds, but the vehicle drifted to one side with no correction back. It did not keep its lane.
    rationale = " ".join(_attribute(_requirement("reqEgoMotionHistory"), "rationale").split())
    assert ("with the two columns zero, the plans in the readiness probe no longer turned off the lane within "
            "seconds, though the vehicle still drifted to one side without steering back.") in rationale
    assert "kept its lane" not in rationale


def test_one_step_without_a_plan_of_its_own_is_tolerated_and_two_in_a_row_are_not():
    # The cadence decision of 2026-11-09: a plan that runs long, or a camera image too late to plan on, leaves a step
    # without a plan of its own while the vehicle stays on the newest valid plan. One such step is tolerated, as one
    # late plan is in REQ-DRIVING-013; two in a row are not.
    requirement = _requirement("reqPlanEachStep")
    criteria = _attribute(requirement, "successCriteria")
    assert "at most one plan for each 100 ms step of simulation time and no two consecutive steps without one" in criteria
    assert "the records hold one plan for each 100 ms of simulation time" not in criteria
    assert "(owner decision of 2026-11-09)" in _attribute(requirement, "rationale")


def test_a_measured_spread_is_stated_as_a_tolerance_not_as_sameness():
    # Inference on a GPU is not bit-exact: a statement that asks for "the same" plans contradicts criteria
    # that accept the spread between two reference runs.
    for name in REQUIREMENTS:
        assert "the same plans" not in _statement(_requirement(name)), name
    assert "differ by no more than" in _statement(_requirement("reqPlansIndependentOfObservation"))


def test_the_terms_of_the_statements_are_defined_once_in_the_package():
    match = re.search(r"\bcomment\s+termsOfTheDrivingRequirements\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, "one comment defines the terms of the requirements"
    text = _flat(match.group(1))
    for term in TERMS:
        assert f"{term}:" in text, term
    assert "REQ-DRIVING-020 to REQ-DRIVING-022" in text, "the stop response is the behavior of those three"


def test_each_requirement_derives_from_its_need_through_derives_from_need_only():
    # requirementDerivesFromNeed counts DerivesFromNeed only; a plain dependency to a need does not count
    # and is not declared.
    code = _code()
    derivations = re.findall(r"\bconnection\s+\w+\s*:\s*DerivesFromNeed\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    names = {short: name for name, short in NEED_SHORT.items()}
    expected = [(names[need], name) for name, (need, *_rest) in REQUIREMENTS.items()]
    assert sorted(derivations) == sorted(expected)
    assert {need for need, _name in derivations} == set(NEED_SHORT), "every need has a requirement"
    plain = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+(\w+)\s*;", code)
    assert not [pair for pair in plain if pair[0] in REQUIREMENTS and pair[1] in NEED_SHORT]


def test_the_statements_carry_their_values_and_the_rationales_give_their_reasons():
    for name, (_need, _kind, statement_parts, rationale_parts) in REQUIREMENTS.items():
        body = _requirement(name)
        statement = _statement(body)
        rationale = _attribute(body, "rationale")
        for part in statement_parts:
            assert part in statement, (name, part)
        for part in rationale_parts:
            assert part in rationale, (name, part)


def test_the_checkpoint_input_contract_is_now_stated_as_requirements_and_its_comment_is_gone():
    # Phase 4 kept the form of the checkpoint's inputs as a comment on NEED-DRIVING-001 for phase 5.
    # Phase 5 states it as requirements, so the comment no longer earns its place.
    assert "checkpointInputContractForPhase5" not in _raw()
    inputs = ("reqCameraImagesInCheckpointForm", "reqCameraHistory", "reqProjectionOperators", "reqMapContextRaster",
              "reqRouteMaskRaster", "reqEgoMotionHistory", "reqHoldUntilHistoriesComplete")
    for name in inputs:
        assert REQUIREMENTS[name][0] == "NEED-DRIVING-001"
        assert "gapModelInputAndFeedback" in _attribute(_requirement(name), "source"), name


def test_each_limit_is_stated_in_its_time_domain():
    # NEED-DRIVING-006 and gapClosedLoopPerformance: what the vehicle lives through is counted in simulation
    # time, what the host does in wall-clock time; no limit is stated without its domain.
    simulation = ("reqPlanEachStep", "reqStopOnDegradedCameraImages", "reqStopOnDegradedMotion",
                  "reqStopOnDegradedRoute", "reqStopOnStalePlan", "reqStopOnInvalidPlan", "reqStopOnLostCommands")
    wall_clock = ("reqPlanWithinPlanningPeriod", "reqPublishPlans", "reqPublishVehicleState",
                  "reqPublishHealthPeriodically", "reqPlanningTimeIndependentOfObservation", "reqPublishStop")
    for name in simulation:
        statement = _statement(_requirement(name))
        assert "simulation time" in statement and "wall-clock" not in statement, name
    for name in wall_clock:
        statement = _statement(_requirement(name))
        assert "wall-clock time" in statement and "simulation time" not in statement, name


def test_the_review_conditions_are_success_criteria_not_statements():
    # SC-DRIVING-005 checks that no autopilot, replay or overlay moves the vehicle; phase 4 left that to
    # phase 5 as a verification criterion. It is a criterion of REQ-DRIVING-011 and wording of no statement.
    for name in REQUIREMENTS:
        statement = _statement(_requirement(name)).lower()
        for wording in REVIEW_WORDING:
            assert wording not in statement, (name, wording)
    criteria = _attribute(_requirement("reqCommandsFromNewestValidPlan"), "successCriteria")
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
    for item in ("SC-DRIVING-001", "REQ-DRIVING-003", "REQ-DRIVING-013", "REQ-DRIVING-023", "REQ-DRIVING-028",
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
