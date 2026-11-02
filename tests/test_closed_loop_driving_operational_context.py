"""Content pins for the closed-loop driving operational context (phase 2), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
MODEL = DRIVING / "closed_loop_driving_operational_context.sysml"
PACKAGE = "DE4SDV_ClosedLoopDrivingOperationalContext"
CONTEXT = "closedLoopDrivingOperationalContext"

#: Context parts around the system of interest and their kernel or reused types (owner decision of
#: 2026-11-02: AAOS SDV is a context role of the driving system, not part of it).
CONTEXT_PARTS = {
    "vehicle": "SubjectVehicle",
    "roadEnvironment": "RoadEnvironment",
    "aaosSDVGuest": "AAOSSDVGuestExecutionDomain",
    "driver": "Driver",
}

#: The story: one use case per operational scenario, each with the context parts it involves.
STORY = "driveBoundedScenarioClosedLoop"
SCENARIOS = {
    "driveOnCheckpointPlans": ("SC-DRIVING-001", {"vehicle", "roadEnvironment"}),
    "showLiveStateOnAAOS": ("SC-DRIVING-002", {"aaosSDVGuest::stateObserver", "driver"}),
    "respondToDegradedInputOrPlan": ("SC-DRIVING-003", {"vehicle", "aaosSDVGuest::stateObserver"}),
    "continueWithoutAAOS": ("SC-DRIVING-004", {"aaosSDVGuest::stateObserver", "vehicle"}),
}


def _code() -> str:
    assert MODEL.is_file(), "phase 2 of INC-DRIVING-001 needs an operational context model"
    return strip_comments(MODEL.read_text(encoding="utf-8"))


def _doc(raw: str, declaration: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(raw, declaration)).split())


def test_the_increment_has_exactly_one_operational_context():
    code = _code()
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", code)
    contexts = re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", code)
    contexts += re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", strip_comments(FRAMING.read_text(encoding="utf-8")))
    assert contexts == [CONTEXT]
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")), "part closedLoopDrivingCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and PACKAGE in re.findall(r'"([^"]+)"', artifacts.group(1)), \
        "the charter's expected artifacts must name the package that now holds phase 2 content"


def test_context_holds_the_charter_system_of_interest_and_nothing_else_inside_it():
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    # The charter declares candidateDrivingSystem : ClosedLoopDrivingSystem; the context redefines its
    # systemOfInterest by that type, and the system stays a black box until the architecture phases.
    assert re.search(r"\bpart\s+drivingSystem\s*:\s*ClosedLoopDrivingSystem\s*:>>\s*systemOfInterest\s*;", context)
    parts = dict(re.findall(r"(?m)^ {4}part\s+(\w+)\s*:\s*(\w+)", context))
    assert parts == {"drivingSystem": "ClosedLoopDrivingSystem", **CONTEXT_PARTS}


def test_aaos_sdv_is_a_context_role_and_reuses_the_existing_guest():
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    guest = braced_body(context, "part aaosSDVGuest : AAOSSDVGuestExecutionDomain")
    assert re.search(r"\bpart\s+stateObserver\s*:\s*DrivingStateObserverApplication\s*;", guest)
    assert "private import DE4SDV_MiddlewareSCOREOperationalContext::AAOSSDVGuestExecutionDomain;" in code
    assert not re.search(r"\bpart\s+def\s+AAOSSDVGuestExecutionDomain\b", code), "reuse the guest, never redeclare it"
    assert not re.search(r"\bpart\s+drivingSystem\s*:[^;{]*\{", context), "the system of interest declares no parts here"
    assert "dependency" in code and re.search(
        r"dependency\s+\w+\s+from\s+DrivingStateObserverApplication\s+to\s+DE4SDV_ClosedLoopDrivingFraming::gapTransportAndControl\s*;",
        code,
    ), "the observing application is the consumer the transport gap says does not exist yet"


def test_context_and_story_hold_system_one_roles_only():
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    forbidden = r"\b(?:System2\w*|DE4SDVEvidenceBaseline|OpenSourceReviewer|VerificationEngineer|\w*CARLA\w*|\w*Carla\w*|\w*Bench\w*)\b"
    assert not re.search(forbidden, context), "bench, simulator, reviewer and evidence roles belong to System 2"
    for name in (STORY, *SCENARIOS):
        assert not re.search(forbidden, braced_body(code, f"use case {name}")), name
    assert not re.search(r"\b(?:part|item|concern|use case) def (?:SubjectVehicle|Driver|RoadEnvironment|SystemContext|OperationalEntity)\b", code), \
        "kernel roles are used, never shadowed"
    assert not re.search(r"\bconcern def\b|\bpart def \w*(?:Engineer|Expert|Architect|Developer|Maintainer|Reviewer)\b", code)


def test_every_use_case_binds_its_subject_and_actors_to_the_context():
    raw = MODEL.read_text(encoding="utf-8")
    code = _code()
    usages = re.findall(r"(?m)^ {2}use case\s+(?!def\b)(\w+)", code)
    assert sorted(usages) == sorted([STORY, *SCENARIOS])
    for name in usages:
        body = braced_body(code, f"use case {name}")
        assert re.search(
            rf"\bsubject\s+drivingSystem\s*:\s*ClosedLoopDrivingSystem\s*=\s*{CONTEXT}::drivingSystem\s*;", body
        ), f"{name}: the subject is the context's system of interest"
        actors = re.findall(rf"\bactor\s+(\w+)\s*:\s*(\w+)\s*=\s*{CONTEXT}::([\w:]+)\s*;", body)
        assert actors, f"{name} has no actor bound to the context"
        unbound = re.findall(r"\bactor\s+\w+\s*:\s*\w+\s*;", body)
        assert not unbound, f"{name}: every actor is bound to a context part"
        for _, _, target in actors:
            assert target.split("::")[0] in CONTEXT_PARTS, f"{name}: {target} is not a context part around the system"
        if name in SCENARIOS:
            scenario_id, involved = SCENARIOS[name]
            assert {target for _, _, target in actors} == involved, name
            assert scenario_id in _doc(raw, f"use case {name}"), f"{name} carries no scenario identity"
    story = braced_body(code, f"use case {STORY} : DriveBoundedScenarioClosedLoop")
    assert re.findall(r"\binclude\s+(\w+)\s*;", story) == list(SCENARIOS)
    assert "use case def DriveBoundedScenarioClosedLoop :> SYSMODSystemUseCaseBase" in code


def test_aaos_sdv_stays_outside_the_loop_in_the_operational_behavior():
    code = _code()
    operation = braced_body(code, "action def ClosedLoopDrivingOperation")
    flows = re.findall(r"\bflow\s+from\s+(\w+)\.\w+\s+to\s+(\w+)\.\w+\s*;", operation)
    assert ("senseScene", "planAndCommand") in flows
    assert ("planAndCommand", "actuateVehicle") in flows
    assert ("planAndCommand", "presentOperationalState") in flows
    assert not [f for f in flows if f[0] == "presentOperationalState"], "nothing flows from AAOS SDV back into the loop"
    assert re.search(r"\baction\s+closedLoopDrivingOperation\s*:\s*ClosedLoopDrivingOperation\s*;", code)


def test_operational_views_frame_operational_concerns_and_expose_phase_two():
    code = _code()
    expected = {
        "closedLoopDrivingOperationalContextView": (
            "OperationalContextDefinitionViewpoint", "closedLoopDrivingContextConcern", "OperationalContextConcern",
            {CONTEXT, f"{CONTEXT}::*", "closedLoopDrivingOperation"}),
        "closedLoopDrivingOperationalStoryView": (
            "OperationalStoryViewpoint", "closedLoopDrivingStoryConcern", "OperationalStoryConcern",
            {STORY, f"{STORY}::*"}),
    }
    for view_name, (viewpoint, concern, concern_type, exposed) in expected.items():
        view = braced_body(code, f"view {view_name}")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*{viewpoint}\s*\{{\s*frame\s+{concern}\s*;\s*\}}", view), view_name
        assert set(re.findall(r"\bexpose\s+([\w:*]+)\s*;", view)) == exposed, view_name
        concern_body = braced_body(code, f"concern {concern} : {concern_type}")
        lines = [line.strip() for line in concern_body.splitlines() if line.strip() and line.strip() != "doc"]
        assert lines[0] == "subject;", concern
        assert re.findall(r"\bstakeholder\s+\w+\s*:\s*\w+\s*;", concern_body), concern
