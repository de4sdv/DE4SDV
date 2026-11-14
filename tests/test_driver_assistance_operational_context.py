"""Content pins for the driver-assistance operational context (INC-DRIVING-002 phase 2), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
MODEL = DRIVING / "driver_assistance_operational_context.sysml"
PACKAGE = "DE4SDV_DriverAssistanceOperationalContext"
FRAMING_PACKAGE = "DE4SDV_DriverAssistanceFraming"
CONTEXT = "driverAssistanceOperationalContext"
SOI = "candidateSystem"

#: Context parts around the system of interest and their kernel or reused types. Phase 0 draws the
#: boundary: the Eclipse S-CORE path and the AAOS SDV are System 1 parts outside the candidate.
CONTEXT_PARTS = {
    "vehicle": "SubjectVehicle",
    "roadEnvironment": "RoadEnvironment",
    "stationaryVehicleTarget": "VehicleTarget",
    "movingVehicleTarget": "VehicleTarget",
    "scorePath": "SCORECommandAndWarningPath",
    "aaosSDVGuest": "AAOSSDVGuestExecutionDomain",
    "driver": "Driver",
}

#: The story: one use case per scenario of the scope, with its identity, its target and its condition.
STORY = "driverAssistanceStory"
SCENARIOS = {
    "warnAndBrakeForStationaryVehicle": (
        "SC-DRIVING-012", "stationaryVehicleTarget", "stationary vehicle target ahead in its lane", True),
    "warnAndBrakeForSlowerVehicle": (
        "SC-DRIVING-013", "movingVehicleTarget", "slower moving vehicle target ahead in its lane", True),
    "noReactionToStationaryVehicleBeyondTheCurve": (
        "SC-DRIVING-014", "stationaryVehicleTarget",
        "a stationary vehicle stands just beyond the guard rail, on the extension of the lane", False),
    "noReactionToVehicleAheadTurningOff": (
        "SC-DRIVING-015", "movingVehicleTarget", "turns off at a corner, while the vehicle goes straight on", False),
}
WARNING_ACTORS = {"scorePath", "aaosSDVGuest::warningPresentation", "driver"}


def _code() -> str:
    assert MODEL.is_file(), "phase 2 of INC-DRIVING-002 needs an operational context model"
    return strip_comments(MODEL.read_text(encoding="utf-8"))


def _doc(raw: str, declaration: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(raw, declaration)).split())


def test_the_increment_has_exactly_one_operational_context_named_in_the_charter():
    code = _code()
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", code)
    contexts = re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", code)
    contexts += re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", framing)
    assert contexts == [CONTEXT]
    charter = braced_body(framing, "part driverAssistanceCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and PACKAGE in re.findall(r'"([^"]+)"', artifacts.group(1))


def test_the_system_of_interest_is_the_charter_candidate_as_a_black_box():
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    assert re.search(rf"\bpart\s+{SOI}\s*:\s*DriverAssistanceSystem\s*:>>\s*systemOfInterest\s*;", context)
    assert not re.search(rf"\bpart\s+{SOI}\s*:[^;{{]*\{{", context), "the system of interest declares no parts here"
    parts = dict(re.findall(r"(?m)^ {4}part\s+(\w+)\s*:\s*(\w+)", context))
    assert parts == {SOI: "DriverAssistanceSystem", **CONTEXT_PARTS}


def test_score_path_and_aaos_sdv_are_context_outside_the_candidate():
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    assert re.search(r"(?m)^ {4}part\s+scorePath\s*:\s*SCORECommandAndWarningPath\b", context)
    guest = braced_body(context, "part aaosSDVGuest : AAOSSDVGuestExecutionDomain")
    assert re.search(r"\bpart\s+warningPresentation\s*:\s*DriverWarningPresentation\s*;", guest)
    assert "private import DE4SDV_MiddlewareSCOREOperationalContext::AAOSSDVGuestExecutionDomain;" in code
    assert not re.search(r"\bpart\s+def\s+AAOSSDVGuestExecutionDomain\b", code), "reuse the guest, never redeclare it"
    assert re.search(r"\bpart\s+def\s+SCORECommandAndWarningPath\s*:>\s*OperationalEntity\b", code)
    # The phase 1 concern keeps the path an internal exchange of the realization, not of the candidate.
    framing = FRAMING.read_text(encoding="utf-8")
    assert re.search(r"concern\s+scoreCommandAndWarningPathConcern\s*:\s*PhysicalInternalExchangeConcern\b", framing)


def test_context_and_story_hold_system_one_roles_only():
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    forbidden = (r"\b(?:System2\w*|DE4SDVEvidenceBaseline|OpenSourceReviewer|VerificationEngineer|\w*CARLA\w*"
                 r"|\w*Carla\w*|\w*Bench\w*|\w*Capture\w*|\w*Recorder\w*|\w*Recording\w*|\w*Evaluator\w*"
                 r"|\w*ScenarioRunner\w*|\w*CloudHost\w*|driverAssistanceVerificationEnvironment)\b")
    assert not re.search(forbidden, context), "simulator, bench, capture and evaluator roles belong to System 2"
    for name in (STORY, *SCENARIOS):
        assert not re.search(forbidden, braced_body(code, f"use case {name}")), name
    assert not re.search(
        r"\b(?:part|item|concern|use case) def (?:SubjectVehicle|Driver|RoadEnvironment|VehicleTarget|SystemContext"
        r"|OperationalEntity|DriverAssistanceSystem)\b", code), "kernel and framing names are used, never shadowed"
    assert not re.search(r"\bconcern def\b", code)
    raw = MODEL.read_text(encoding="utf-8")
    assert "driverAssistanceVerificationEnvironment" in _doc(raw, f"part {CONTEXT} : SystemContext"), \
        "the context doc says where System 2 stays"


def test_every_use_case_binds_its_subject_and_actors_to_the_context():
    code = _code()
    usages = re.findall(r"(?m)^ {2}use case\s+(?!def\b)(\w+)", code)
    assert sorted(usages) == sorted([STORY, *SCENARIOS])
    for name in usages:
        body = braced_body(code, f"use case {name}")
        assert re.search(
            rf"\bsubject\s+{SOI}\s*:\s*DriverAssistanceSystem\s*=\s*{CONTEXT}::{SOI}\s*;", body
        ), f"{name}: the subject is the context's system of interest"
        declared = re.findall(r"\bactor\s+(\w+)\s*:", body)
        actors = re.findall(rf"\bactor\s+(\w+)\s*:\s*(\w+)\s*=\s*{CONTEXT}::([\w:]+)\s*;", body)
        assert declared and len(actors) == len(declared), f"{name}: every actor is bound to a context part"
        for _, _, target in actors:
            assert target.split("::")[0] in CONTEXT_PARTS, f"{name}: {target} is not a context part around the system"
    story = braced_body(code, f"use case {STORY} : AssistDriverForVehicleTargetAhead")
    story_actors = {t for _, _, t in re.findall(rf"\bactor\s+(\w+)\s*:\s*(\w+)\s*=\s*{CONTEXT}::([\w:]+)\s*;", story)}
    assert {t.split("::")[0] for t in story_actors} == set(CONTEXT_PARTS)
    assert "use case def AssistDriverForVehicleTargetAhead :> SYSMODSystemUseCaseBase" in code
    use_case_def = braced_body(code, "use case def AssistDriverForVehicleTargetAhead :> SYSMODSystemUseCaseBase")
    for slot in ("ucMotivation", "ucTrigger", "ucResult"):
        assert re.search(rf"\battribute\s+redefines\s+{slot}\s*=\s*\"[^\"]+\"\s*;", use_case_def), slot


def test_the_story_holds_the_four_scenarios_with_their_targets_and_conditions():
    raw = MODEL.read_text(encoding="utf-8")
    code = _code()
    story = braced_body(code, f"use case {STORY} : AssistDriverForVehicleTargetAhead")
    assert re.findall(r"\binclude\s+(\w+)\s*;", story) == list(SCENARIOS)
    for name, (scenario_id, target, condition, reaction) in SCENARIOS.items():
        body = braced_body(code, f"use case {name}")
        targets = set(re.findall(rf"\bactor\s+\w+\s*:\s*VehicleTarget\s*=\s*{CONTEXT}::(\w+)\s*;", body))
        assert targets == {target}, f"{name}: the scenario's target"
        objective = re.search(r"\bdoc\s*/\*(.*?)\*/", braced_body(raw, f"use case {name}"), re.S)
        doc = " ".join(re.sub(r"(?m)^\s*\*\s?", "", objective.group(1)).split()) if objective else ""
        assert doc.startswith(scenario_id + " "), f"{name} carries {scenario_id}"
        assert condition in doc, f"{name}: the scenario's condition"
        bound = set(re.findall(rf"=\s*{CONTEXT}::([\w:]+)\s*;", body))
        if reaction:
            assert "requests the warning" in doc and "brakes the vehicle" in doc, name
            assert WARNING_ACTORS <= bound, f"{name}: the warning reaches the driver"
        else:
            assert "requests no warning and commands no emergency braking" in doc, name
            assert "The regulation lists this situation among its false-reaction scenarios; phase 5 makes the " \
                "selection and states the criterion (gapVehicleTargetCriteria)." in doc, name
            assert not (bound & {"aaosSDVGuest::warningPresentation", "driver"}), f"{name}: no warning is due"
    ids = re.findall(r"SC-DRIVING-\d{3}", raw)
    assert sorted(set(ids)) == sorted(s[0] for s in SCENARIOS.values()), "only the four new scenario identities"


def test_the_boundary_flows_cross_in_the_drawn_directions():
    code = _code()
    operation = braced_body(code, "action def DriverAssistanceOperation")
    flows = re.findall(r"\bflow\s+from\s+(\w+)\.(\w+)\s+to\s+(\w+)\.(\w+)\s*;", operation)
    into_candidate = {(s, i) for s, i, t, _ in flows if t == "assistDriving"}
    out_of_candidate = {(i, t) for s, i, t, _ in flows if s == "assistDriving"}
    assert into_candidate == {("senseScene", "frontCameraImage"), ("senseScene", "vehicleSpeed")}
    assert out_of_candidate == {("drivingCommand", "carryOverSCORE"), ("warningRequest", "carryOverSCORE")}
    assert ("carryOverSCORE", "carriedCommand", "actuateVehicle", "drivingCommand") in flows
    assert ("carryOverSCORE", "carriedWarningRequest", "presentWarning", "warningRequest") in flows
    assert ("presentWarning", "collisionWarning", "receiveWarning", "collisionWarning") in flows
    assert not [f for f in flows if f[0] == "receiveWarning"], "the driver only receives"
    assert not [f for f in flows if f[0] == "presentWarning" and f[2] != "receiveWarning"], \
        "nothing flows from the AAOS SDV back to the candidate"
    assist = braced_body(operation, "action assistDriving")
    assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", assist) == [
        ("in", "frontCameraImage", "FrontCameraImage"), ("in", "vehicleSpeed", "VehicleSpeed"),
        ("out", "drivingCommand", "DrivingCommand"), ("out", "warningRequest", "WarningRequest"),
    ]
    assert re.search(r"\baction\s+driverAssistanceOperation\s*:\s*DriverAssistanceOperation\s*;", code)


def test_operational_views_frame_operational_concerns_and_expose_phase_two():
    code = _code()
    expected = {
        "driverAssistanceOperationalContextView": (
            "OperationalContextDefinitionViewpoint", ["driverAssistanceContextConcern"],
            "OperationalContextConcern", {CONTEXT, f"{CONTEXT}::*", "driverAssistanceOperation"}, "2"),
        "driverAssistanceOperationalStoryView": (
            "OperationalStoryViewpoint", ["driverAssistanceStoryConcern", "vehicleTargetResponseConcern"],
            "OperationalStoryConcern", {STORY, f"{STORY}::*"}, "1"),
    }
    assert re.findall(r"(?m)^ {2}view\s+(\w+)", code) == list(expected)
    for view_name, (viewpoint, frames, concern_type, exposed, depth) in expected.items():
        view = braced_body(code, f"view {view_name}")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*{viewpoint}\s*\{{", view), view_name
        assert re.findall(r"\bframe\s+([\w:]+)\s*;", view) == frames, view_name
        assert set(re.findall(r"\bexpose\s+([\w:*]+)\s*;", view)) == exposed, view_name
        assert re.search(rf"\battribute\s+depth\s*=\s*{depth}\s*;", view), view_name
        concern_body = braced_body(code, f"concern {frames[0]} : {concern_type}")
        lines = [line.strip() for line in concern_body.splitlines() if line.strip() and line.strip() != "doc"]
        assert lines[0] == "subject;", frames[0]
        assert re.findall(r"\bstakeholder\s+\w+\s*:\s*\w+\s*;", concern_body), frames[0]


def test_dependencies_trace_the_story_and_the_context_to_phase_zero():
    code = _code()
    deps = re.findall(r"\bdependency\s+(\w+)\s+from\s+([\w:]+)\s+to\s+([\w:]+)\s*;", code)
    found = {(client, supplier) for _, client, supplier in deps}
    expected = {
        (STORY, f"{FRAMING_PACKAGE}::driverAssistanceProblem"),
        (STORY, f"{FRAMING_PACKAGE}::gapVehicleTargetCriteria"),
        (f"{CONTEXT}::scorePath", f"{FRAMING_PACKAGE}::asmBenchReuse"),
        (f"{CONTEXT}::aaosSDVGuest", f"{FRAMING_PACKAGE}::asmBenchReuse"),
        ("SCORECommandAndWarningPath", f"{FRAMING_PACKAGE}::gapScoreIntegration"),
        ("DriverWarningPresentation", f"{FRAMING_PACKAGE}::gapDriverHmiInProductLine"),
        ("WarningRequest", f"{FRAMING_PACKAGE}::gapWarningOutput"),
    }
    assert found == expected
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    for _, supplier in expected:
        name = supplier.split("::")[-1]
        assert re.search(rf"\b(?:requirement|part)\s+{name}\s*:", framing), f"{name} is a phase 0 record"
