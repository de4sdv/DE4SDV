"""Content pins for the framing of the HMI display increment, not semantic validation.

The framing of INC-HMI-001 is Phase 0 only. These tests hold its structure to the method's
Phase 0 shape, pin each decided statement by its own phrase, and hold the guide, the folder's
upstream record and the rows that name the increment elsewhere to the model. They read the model
text; they do not parse SysML.

What they do not hold: a sentence that no pin names can change inside a doc of the model or
inside the record, and a report of a run in words that the scan for past behavior does not list
passes. Those are for the review of the text.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import check_naming  # noqa: E402

MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
FEATURES = ROOT / "textual-notation-of-model/packages/features"
HMI = FEATURES / "hmi"
MODEL = HMI / "hmi_display_framing.sysml"
UPSTREAM_RECORD = HMI / "upstream.md"
DRIVING_FRAMING = FEATURES / "driving/driver_assistance_framing.sysml"
DRIVING_RECORD = FEATURES / "driving/upstream.md"
DRIVING_REALIZATION = FEATURES / "driving/driver_assistance_physical_software_realization.sysml"
MIDDLEWARE_FRAMING = FEATURES / "middleware/middleware_score_framing.sysml"
ADR_0025 = ROOT / "docs/architecture-decisions/0025-end-someip-in-an-sdv-core-vm.md"
AEBS_REQUIREMENTS = FEATURES / "aebs/aebs_needs_requirements.sysml"
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
INDEX = ROOT / "UPSTREAM.md"
GLOSSARY = ROOT / "docs/terminology/glossary.md"
PACKAGE = "DE4SDV_HmiDisplayFraming"
IDENTITY = "INC-HMI-001"
#: the commits of the display safety service and of its device configuration that the framing read
DISPLAY_SAFETY_PIN = "951af0fd68b691a69bab68542c981291ad4cf1c3"
DEVICE_PIN = "0971a46741bd2931c8c506e0afe950348af7c1d4"
#: the VisionPilot commit that the driving record names for INC-DRIVING-002
VISIONPILOT_PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"

DOC = re.compile(r"\bdoc\s*/\*(.*?)\*/", re.DOTALL)
#: a usage declared at package level (two spaces of indent), with an optional short name
PACKAGE_USAGE = re.compile(r"(?m)^  (part|requirement|concern)\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(\w+)")

#: in-scope item -> the statement it makes
IN_SCOPE = {
    "hmiSceneInScope":
        "The scene as the candidate builds it from its own perception: its lane, the path it fits to that lane, the "
        "objects it detects, and the closest object in its path with the distance that its fusion gives.",
    "hmiSpeedInScope": "The vehicle speed that the candidate is given.",
    "hmiCollisionWarningInScope":
        "The collision warning on the display and as a sound, when the candidate's warning request asks for it and "
        "within the time that the driver-assistance increment allots from the request to each mode.",
    "hmiRendererSplitInScope":
        "Which elements the high availability renderer in an SDV Media VM draws and which an app in the IVI VM draws, "
        "and the paths that bring their inputs from the SDV Core VM.",
    "hmiAndroidOutageInScope":
        "What the display shows while the app that draws the scene hangs or ends, and while Android in the IVI VM "
        "hangs, boots or restarts: the speed and the warning, or the fact that the warning is unavailable.",
    "hmiStaleContentInScope":
        "What the display shows when an input is late or missing, so that no element is shown as current when it is "
        "not.",
    "hmiVerdictEvidenceInScope":
        "A pass or a fail for each requirement and scenario, bound to the candidate revision, the display build and "
        "the configuration that ran.",
}
#: out-of-scope item -> the statement it makes
OUT_OF_SCOPE = {
    "hmiSimulatorTruthOutOfScope":
        "Objects that the candidate does not give: the simulator's own record of the scene, and any estimate of "
        "objects that the display would make itself.",
    "hmiPerceptionQualityOutOfScope":
        "How well the candidate perceives: whether it finds an object, and how far its positions and its distances "
        "are from the simulator's. The display shows what the candidate gives, right or wrong.",
    "hmiOtherDrivingApplicationsOutOfScope":
        "The scenes of other driving applications, those of the Autoware-based members and of the closed-loop "
        "driving increment among them, and adapters that would bring them to the display.",
    "hmiDriverInteractionOutOfScope": "Driver interaction: engagement, override, driving modes and controls on the "
                                      "display.",
    "hmiFurtherContentOutOfScope":
        "Gear, set speed, speed limit and the other telltales, unless a need of Phase 4 asks for one; media, "
        "navigation, maps, telephony and camera views.",
    "hmiHumanFactorsOutOfScope":
        "How a driver perceives and reads the display, with glance time, comprehension and distraction, and the "
        "display's visual design.",
    "hmiCandidateChangeOutOfScope":
        "Changing what the candidate perceives, plans, requests or commands, its camera geometry included, and the "
        "criteria and the verdicts of the driver-assistance increment.",
    "hmiStandaloneDisplayOutOfScope":
        "The display of a member product without an AAOS SDV guest, the Linux-side display of the standalone member "
        "among them.",
    "hmiOnRoadOperationOutOfScope":
        "On-road operation, production readiness, a safety approval of the display or of the renderer's monitor, "
        "compliance, type approval or certification.",
}
#: assumption -> the phrases that state its premise and what the framing decided with it
ASSUMPTIONS = {
    "asmHmiDrivingBenchReuse": ("can carry the display", "They are reuse candidates.",
                                "Their results for that increment are not evidence for this one."),
    "asmHmiRendererWithoutGraphicsCard": (
        "draws on a guest host without a graphics card, with the SDV Core, IVI and SDV Media VMs running on it "
        "together", "A readiness probe tests this first.",
        "If it does not hold, the owner decides how the increment goes on."),
    "asmHmiSimulationStandsIn": ("stand in for the road, the vehicle and its speed signal",
                                 "A verdict holds for that simulated configuration only."),
}
#: gap -> the phrase that states what is open
GAPS = {
    "gapHmiSceneOutput": "None of the outputs that the driver-assistance increment realizes for the candidate",
    "gapHmiSceneContent": "not a type of object",
    "gapHmiRendererCollisionWarning": "holds the vehicle speed but no collision warning",
    "gapHmiRendererIntegration": "No high availability renderer has run on the DE4SDV bench.",
    "gapHmiWarningPresentation": "Whether a build of this display replaces that app in the VisionPilot configuration",
    "gapHmiWarningAvailability": "gives no indication that its warning is unavailable",
    "gapHmiMemberGuestLayout": "A renderer in an SDV Media VM adds a third VM to the guest.",
    "gapHmiDisplayInProductLine": "takes effect with a revision of the governed scope that is made outside this "
                                  "increment",
    "gapHmiUpstreamContact": "are not yet involved",
}
#: gap -> the label of its open point in the guide
OPEN_POINTS = {
    "gapHmiSceneOutput": "No scene output",
    "gapHmiSceneContent": "What the scene can carry",
    "gapHmiRendererCollisionWarning": "No collision warning in the renderer",
    "gapHmiRendererIntegration": "The renderer on the bench",
    "gapHmiWarningPresentation": "Two presentations of the warning",
    "gapHmiWarningAvailability": "No indication that the warning is unavailable",
    "gapHmiMemberGuestLayout": "The guest layout of the members",
    "gapHmiDisplayInProductLine": "The HMI display's place in the product line",
    "gapHmiUpstreamContact": "No upstream contact",
}
#: a past form of what a system does in a run: a framing reports no run
PAST_BEHAVIOR = re.compile(r"(?i)\b(?:braked|warned|stopped|collided|avoided|detected|passed|failed|displayed|"
                           r"rendered|showed|crashed|hung)\b")
#: an affirmative claim of approval or admission
APPROVAL = re.compile(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b")


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _doc(declaration: str, source: str | None = None) -> str:
    """The first doc of the declaration's body, without comment leaders and line breaks."""
    match = DOC.search(braced_body(_raw() if source is None else source, declaration))
    assert match, f"{declaration} has no doc"
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", match.group(1)).split())


def _declared(kind: str) -> set[str]:
    """The parts of the kind, with or without a short name."""
    return set(re.findall(rf"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*{kind}\b", _code()))


def _row(path: Path, first_cell: str) -> str:
    """The one table row of the file whose first cell starts with the text."""
    rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith(f"| {first_cell}")]
    assert len(rows) == 1, f"{path.name}: {len(rows)} rows start with {first_cell!r}"
    return rows[0]


def _flat(text: str) -> str:
    return " ".join(text.split())


def _link_text(markdown: str) -> str:
    """The text of a Markdown passage with each link reduced to its words, without line breaks."""
    return _flat(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown))


def _record_section(record: str, heading: str) -> str:
    """The text of the one second-level section of the record with the heading."""
    assert record.count(f"\n## {heading}\n") == 1, heading
    return record.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_increment_declares_the_phase_zero_shape():
    assert MODEL.is_file(), "the increment needs a framing model"
    code = _code()
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", code) == [PACKAGE], "one global package per file"
    assert "part def HmiDisplayIncrement :> EngineeringIncrement;" in code
    assert re.search(rf"part\s+<'{IDENTITY}'>\s+hmiDisplayIncrement\s*:\s*HmiDisplayIncrement\b", code)
    problem = braced_body(code, "requirement hmiDisplayProblem : ProblemStatement")
    assert "subject hmiDisplaySubject : HmiDisplayIncrement;" in problem
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", problem) == [
        "VehicleOccupant", "ProductLineEngineer", "SystemsEngineer", "SafetyExpert", "VerificationEngineer"]
    assert _declared("IncrementEngineeringQuestion") == {"hmiDisplayQuestion"}
    assert _declared("IncrementLifecycleDecision") == {"hmiDisplayDecision"}
    assert _declared("IncrementScope") == {"hmiDisplayScope"}, "exactly one scope"
    assert re.search(r"dependency\s+scopeToHmiDisplayQuestion\s+from\s+hmiDisplayScope\s+to\s+hmiDisplayQuestion\s*;",
                     code)
    assert re.search(
        r"dependency\s+hmiDisplayQuestionToProblem\s+from\s+hmiDisplayQuestion\s+to\s+hmiDisplayProblem\s*;", code)

    charter = braced_body(code, "part hmiDisplayCharter : IncrementCharter")
    assert "ref part :>> increment = hmiDisplayIncrement;" in charter
    assert "ref part :>> systemOfInterest = hmiDisplaySystem;" in charter
    assert 'attribute :>> owner = "Orkun Yilmaz";' in charter
    assert re.findall(r"MethodPhase::(\w+)", charter) == [
        "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
        "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
        "phase6_functionalArchitecture", "phase7_logicalArchitecture",
        "phase8_physicalRealization", "phase9_variabilityConfiguration",
        "phase10_vvEvidence", "phase11_baseline",
    ]
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1)) == [PACKAGE], \
        "the charter names only the package that holds content today"
    evidence = re.search(r"expectedReviewEvidence\s*=\s*\((.*?)\);", charter, re.S)
    assert evidence and re.findall(r'"([^"]+)"', evidence.group(1)) == [
        "owner confirmation of the engineering question and the scope",
        "independent review of the System 1 and System 2 boundary and the nonclaims",
        "repository, smoke and focused regression checks on the reviewed changes",
        "exact-head licensed SysML validation and Syside-generated framing view",
    ]
    assert "part hmiDisplaySystem : HmiDisplaySystem;" in code
    assert "part hmiDisplayVerificationEnvironment : System2EngineeringAndAssuranceSystem" in code


def test_the_question_the_decision_and_the_boundary_say_what_was_agreed():
    increment = _doc(f"part <'{IDENTITY}'> hmiDisplayIncrement : HmiDisplayIncrement")
    for phrase in ("The owner decided on 2026-11-17 that the display of the VisionPilot configuration of the "
                   "driver-assistance increment shows the scene that VisionPilot builds from its own perception, "
                   "beside the speed and the collision warning.",
                   "The same decision gives the speed, the collision warning and the warning's sound to the high "
                   "availability renderer (HAR) of AAOS SDV, in an SDV Media VM, and the scene to an app in the IVI "
                   "VM.",
                   "The increment does not change what the candidate application perceives, plans, requests or "
                   "commands.",
                   "This package holds only Phase 0."):
        assert phrase in increment, phrase
    problem = _doc("requirement hmiDisplayProblem : ProblemStatement")
    for phrase in ("The owner decided on 2026-11-13 that every member product has an HMI display, and left open what "
                   "it shows.",
                   "to make the availability of the AEBS apparent when its inputs or its functions are not healthy",
                   "In the driver-assistance increment the AAOS SDV is to give its candidate's collision warning",
                   "DE4SDV does not know what else the display has to show the driver",
                   "while Android in the IVI VM hangs, boots or restarts"):
        assert phrase in problem, phrase
    question = _doc("part hmiDisplayQuestion : IncrementEngineeringQuestion")
    for phrase in ("the scene that the candidate application perceives, its lane, the path it fits to its lane and "
                   "the objects it detects, together with the speed and the collision warning,",
                   "with the speed and the warning drawn by the high availability renderer of AAOS SDV in an SDV "
                   "Media VM, which also sounds the warning,",
                   "or the fact that the warning is unavailable, stay apparent and correct",
                   "holding what the display shows against what the candidate gives and when.",
                   "A recording of a display that looks right does not."):
        assert phrase in question, phrase
    assert question.count("?") == 1, "an increment answers one engineering question"
    decision = _doc("part hmiDisplayDecision : IncrementLifecycleDecision")
    for phrase in ("which of its content becomes common to the member products and which derives from a member's "
                   "driving application",
                   "whether the high availability renderer or an app in the IVI VM draws the common content",
                   "executed cases with a pass or a fail for each requirement of the increment",
                   "A fail is a result to record.",
                   "no reason to change a scenario or a criterion until the display passes"):
        assert phrase in decision, phrase
    system = _doc("part def HmiDisplaySystem")
    # the sentences that state the boundary are pinned whole: one more item inside is a change of the boundary
    for phrase in ("Candidate System 1 boundary. In: the scene and the warning request that the candidate application "
                   "gives, and the vehicle speed. Inside: what the display shows and where; an app in the IVI VM that "
                   "draws the scene; the high availability renderer in an SDV Media VM that draws the speed and the "
                   "collision warning and gives the warning's sound; and the paths from the SDV Core VM to both. "
                   "Out: the picture on the display and the sound.",
                   "Two parts of System 1 are outside this boundary, and neither is an enabling system: the candidate "
                   "application, which perceives, plans and requests the warning, and the Eclipse S-CORE path that "
                   "carries its outputs to the SDV Core VM.",
                   "Which part of System 1 brings the vehicle speed to the SDV Core VM is for Phases 2 and 3 to place.",
                   "The display belongs to a configuration that is not a member product: this increment admits no "
                   "member to the governed product-line scope."):
        assert phrase in system, phrase
    environment = _doc("part hmiDisplayVerificationEnvironment : System2EngineeringAndAssuranceSystem")
    for phrase in ("CARLA renders the camera image and moves the vehicle and the targets, as on the bench of the "
                   "driver-assistance increment.",
                   "the means that make Android in the IVI VM hang, end and restart, the record of what the candidate "
                   "gives, the capture of the display and of the sound,",
                   "They are not vehicle features and not contents of the System 1 boundary.",
                   "The capture observes the AAOS SDV and is no part of it."):
        assert phrase in environment, phrase
    boundary = _doc("concern hmiDisplayBoundary : IncrementBoundaryConcern")
    for phrase in ("need the framing proposal kept distinct from realized, tested or accepted scope",
                   "the verdicts of Phase 10, which hold what the display shows against what the candidate gives, kept "
                   "distinct from a recording that looks right"):
        assert phrase in boundary, phrase


def test_the_system_definition_declares_nothing_and_system_2_is_one_part_beside_it():
    code = _code()
    assert braced_body(code, "part def HmiDisplaySystem").split() == ["doc"], \
        "phase 0 states the boundary in words; its parts and ports follow in phases 2 and 3"
    assert _declared("System2EngineeringAndAssuranceSystem") == {"hmiDisplayVerificationEnvironment"}
    assert re.search(r"(?m)^  part hmiDisplayVerificationEnvironment : System2EngineeringAndAssuranceSystem\b", code), \
        "the enabling system is a part of the package, not of the display"
    assert _declared("HmiDisplaySystem") == {"hmiDisplaySystem"}


def test_scope_items_are_the_agreed_closed_sets():
    code = _code()
    assert _declared("InScopeItem") == set(IN_SCOPE)
    assert _declared("OutOfScopeItem") == set(OUT_OF_SCOPE)
    for name, statement in IN_SCOPE.items():
        assert _doc(f"part {name} : InScopeItem") == statement, name
    for name, statement in OUT_OF_SCOPE.items():
        assert _doc(f"part {name} : OutOfScopeItem") == statement, name
    scope_body = braced_body(code, "part hmiDisplayScope : IncrementScope")
    assert "InScopeItem" not in scope_body and "OutOfScopeItem" not in scope_body, \
        "scope items are package-level parts: a nested item is not in the scope gate's population"
    scope = _doc("part hmiDisplayScope : IncrementScope")
    for phrase in ("What the HMI display of the VisionPilot configuration shows and which renderer draws each element "
                   "of it: the candidate's scene, the vehicle speed and the collision warning,",
                   "with faults of Android in the IVI VM added to them",
                   "for one configuration and with at most ten requirements",
                   "The warning request is the driver-assistance increment's; this increment takes it as that "
                   "increment defines it.",
                   "Implementation is not part of this framing slice."):
        assert phrase in scope, phrase
    # the requirements that the scope names as the source of the increment's own are requirements of the AEBS model
    named = re.findall(r"REQ-AEBS-\d{3}", scope)
    assert named == ["REQ-AEBS-002", "REQ-AEBS-013"]
    aebs = AEBS_REQUIREMENTS.read_text(encoding="utf-8")
    statements = {
        "REQ-AEBS-002": "providing a collision warning to the driver",
        "REQ-AEBS-013": "shall provide the status indication",
    }
    for identity in named:
        declared = re.findall(rf"requirement\s+(\w+)\s*:\s*\w+\s*\{{\s*doc\s*/\*\s*{identity}\b", aebs)
        assert len(declared) == 1, f"{identity} is one requirement of the AEBS model: {declared}"
        assert statements[identity] in _flat(braced_body(aebs, f"requirement {declared[0]} :")), identity


def test_assumptions_are_premises_and_gaps_are_open_points():
    code = _code()
    assert _declared("IncrementAssumption") == set(ASSUMPTIONS)
    assert _declared("IncrementGap") == set(GAPS)
    for name, phrases in ASSUMPTIONS.items():
        for phrase in phrases:
            assert phrase in _doc(f"part {name} : IncrementAssumption"), (name, phrase)
    for name, phrase in GAPS.items():
        assert phrase in _doc(f"part {name} : IncrementGap"), name
    assert "disposition" not in code, "a gap has no disposition before the baseline decision of phase 11"
    output = _doc("part gapHmiSceneOutput : IncrementGap")
    for phrase in ("At the inspected revision the candidate builds a top-down scene of its lane, its path and its "
                   "detections only inside its own visualization, and only when that visualization is built with it, "
                   "which upstream's build does not do by default.",
                   "Whether the scene can leave the candidate's process without a change to what it perceives and "
                   "plans is open.",
                   "A build of the candidate that adds such an output differs from the build that the "
                   "driver-assistance increment judges.",
                   "The configuration that the driver-assistance increment realizes for the candidate also switches "
                   "the visualization off."):
        assert phrase in output, phrase
    # the configuration of the judged candidate switches the visualization off
    assert "visualization_on = false" in _flat(DRIVING_REALIZATION.read_text(encoding="utf-8"))
    content = _doc("part gapHmiSceneContent : IncrementGap")
    for phrase in ("carries a distance and a speed from the candidate's fusion",
                   "labels the closest object with its projected position instead of the fused distance. Such "
                   "estimates are the display's own, which this increment leaves out."):
        assert phrase in content, phrase
    # the gap that the scene's positions rest on is a gap of the driver-assistance increment, not of this one
    assert "(gapCameraImageAndGeometry of the driver-assistance increment)" in content
    assert re.search(r"(?m)^  part gapCameraImageAndGeometry : IncrementGap\b",
                     strip_comments(DRIVING_FRAMING.read_text(encoding="utf-8")))
    renderer = _doc("part gapHmiRendererCollisionWarning : IncrementGap")
    for phrase in ("Its reference code draws a front-collision mark only in a scripted demonstration of a "
                   "driver-assistance scene, whose state it computes from the time alone, and its reference app has "
                   "no sound for a collision warning.",
                   "how their symbols and their sound are designed and reviewed, is open."):
        assert phrase in renderer, phrase
    assert "editable" not in renderer, "the design documents of the reference app are published"
    integration = _doc("part gapHmiRendererIntegration : IncrementGap")
    for phrase in ("Its path from the SDV Core VM to the SDV Media VM",
                   "the app in the IVI VM that tells it that Android is alive",
                   "its sound output and the capture of that sound", "are not observed."):
        assert phrase in integration, phrase
    availability = _doc("part gapHmiWarningAvailability : IncrementGap")
    assert ("the driver-assistance increment leaves the failure and unavailability signals of the warning out of its "
            "scope") in availability
    # the driver-assistance increment's own out-of-scope item says so
    assert "the failure and unavailability signals" in _doc(
        "part furtherWarningProvisionsOutOfScope : OutOfScopeItem", DRIVING_FRAMING.read_text(encoding="utf-8"))
    presentation = _doc("part gapHmiWarningPresentation : IncrementGap")
    for phrase in ("The driver-assistance increment realizes the collision warning with an app in the IVI VM, a build "
                   "item of its bench, and allots 0.1 s of the 0.2 s from the warning request to each mode to the "
                   "path to that app and 0.1 s to the app.",
                   "The realization and the verdicts of the driver-assistance increment stay as they are."):
        assert phrase in presentation, phrase
    realization = _flat(_doc("part def CollisionWarningPresentationApplication :> DriverWarningPresentation",
                             DRIVING_REALIZATION.read_text(encoding="utf-8")))
    assert "0.1 s is the path's" in realization and "0.1 s is this application's" in realization
    layout = _doc("part gapHmiMemberGuestLayout : IncrementGap")
    for phrase in ("ADR 0025 gives the S-CORE-integrated member of ADR 0023 a guest partition of two VMs, an SDV Core "
                   "VM and an IVI VM that runs the HMI application,",
                   "is an informational display, not the AEBS driver warning (ASM-MW-024)",
                   "it is settled outside this increment."):
        assert phrase in layout, phrase
    assert "a guest partition of two VMs" in _flat(ADR_0025.read_text(encoding="utf-8"))
    assert "It is an informational display, not the AEBS driver warning." in _flat(
        MIDDLEWARE_FRAMING.read_text(encoding="utf-8").replace("*", ""))
    product_line = _doc("part gapHmiDisplayInProductLine : IncrementGap")
    for phrase in ("The feature model holds the HMI display as an optional feature that requires the AAOS SDV guest, "
                   "with no binding time assigned, and neither governed member selects it.",
                   "The owner's decision of 2026-11-13 that every member product has an HMI display",
                   "Phase 3 classifies the content of the display against the scope as it then stands."):
        assert phrase in product_line, phrase
    contact = _doc("part gapHmiUpstreamContact : IncrementGap")
    for phrase in ("show them a result about their project before it is published",
                   "No upstream contact, endorsement or rights clearance is asserted."):
        assert phrase in contact, phrase


def test_the_framing_view_frames_the_boundary_and_exposes_every_usage():
    code = _code()
    boundary = braced_body(code, "concern hmiDisplayBoundary : IncrementBoundaryConcern")
    lines = [line.strip() for line in boundary.splitlines() if line.strip()]
    assert lines[0] == "subject increment : HmiDisplayIncrement;"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", boundary) == ["SystemsEngineer", "VerificationEngineer"]
    assert dict(re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", code)) == {
        "hmiDisplayBoundary": "IncrementBoundaryConcern"}, "Phase 0 frames the boundary concern only"

    view = braced_body(code, "view hmiDisplayFramingView")
    viewpoint = braced_body(view, "viewpoint hmiDisplayFramingViewpoint : IncrementFramingViewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == ["hmiDisplayBoundary"]
    assert "render asTreeDiagram;" in view
    exposed = re.findall(r"\bexpose\s+(\w+)\s*;", view)
    assert len(exposed) == len(set(exposed)), "an element is exposed once"

    usages = {name for _kind, name, _type in PACKAGE_USAGE.findall(code)}
    kinds = {kind for _kind, _name, kind in PACKAGE_USAGE.findall(code)}
    assert len(usages) >= 30, "the population of the exposure check must not be vacuous"
    assert {"InScopeItem", "OutOfScopeItem", "IncrementAssumption", "IncrementGap", "IncrementCharter",
            "IncrementScope", "ProblemStatement", "IncrementBoundaryConcern"} <= kinds
    assert set(exposed) == usages | {"HmiDisplayIncrement"}, \
        f"not exposed: {sorted(usages - set(exposed))}; exposed and not declared: {sorted(set(exposed) - usages)}"


def test_the_framing_claims_no_verification_no_admission_and_no_compliance():
    raw = _raw()
    code = _code()
    assert not re.search(r"\b(?:verify|satisfy)\s+\w+", code)
    assert not re.search(r"\bverification\b", code)
    assert "ProductLineMemberProduct" not in raw, "the display is not typed as a member product"
    # raw source: a claim hidden in a comment is still a claim a reader sees
    assert not APPROVAL.search(raw)
    header = raw.split("package", 1)[0]
    for phrase in ("Phase 0 framing only", "no implementation", "no runtime result", "no product-line",
                   "no compliance"):
        assert phrase in _flat(header.replace("*", "")), phrase
    for word in ("compliance", "type approval", "certification", "production readiness", "safety approval"):
        assert word in OUT_OF_SCOPE["hmiOnRoadOperationOutOfScope"], word


def test_no_text_of_the_framing_reports_a_run_an_approval_or_an_admission():
    texts = {
        MODEL.name: _raw(),
        GUIDE.name: GUIDE.read_text(encoding="utf-8"),
        "upstream record": UPSTREAM_RECORD.read_text(encoding="utf-8"),
        "glossary row HMI display": _row(GLOSSARY, "HMI display |"),
        "glossary row High availability renderer": _row(GLOSSARY, "High availability renderer (HAR) |"),
        "index row": _row(INDEX, "AAOS SDV display safety"),
    }
    for name, text in texts.items():
        assert not PAST_BEHAVIOR.findall(text), f"{name} reports behavior in a run: {PAST_BEHAVIOR.findall(text)}"
        assert not APPROVAL.findall(text), f"{name}: {APPROVAL.findall(text)}"
        # the display shows the warning as part of the system: the increment's texts use the line's own term
        assert "instrument" not in text.lower(), name
    assert "It is System 1 content, not a System 2 visualization of a bench." in texts["glossary row HMI display"]
    assert "Drawing an element with it is no safety approval of that element." in \
        texts["glossary row High availability renderer"]
    assert "It is read for the framing. No bench builds or runs it." in texts["index row"]
    assert "[HMI upstream record](textual-notation-of-model/packages/features/hmi/upstream.md)" in texts["index row"]


def test_the_identity_is_declared_once_and_its_subject_is_registered():
    declarations = []
    for root in MODEL_ROOTS:
        for path in root.rglob("*.sysml"):
            if f"<'{IDENTITY}'>" in path.read_text(encoding="utf-8"):
                declarations.append(path.relative_to(ROOT).as_posix())
    assert declarations == [MODEL.relative_to(ROOT).as_posix()]
    assert _raw().count(f"<'{IDENTITY}'>") == 1
    assert IDENTITY.split("-")[1] in check_naming.REGISTERED_SUBJECTS
    assert check_naming.check_identifier_tokens_in_text(_raw(), display_path=MODEL.name, suffix=".sysml") == []


def test_the_package_declares_no_name_that_another_model_package_declares():
    # Two packages may declare the same name, but a lookup by name then finds two elements, and a check that
    # reads a folder by name sees one increment's element as the other's.
    kinds = r"(?:part def|part|requirement def|requirement|concern def|concern|view def|view|dependency)"
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(?:<'[^']*'>\s*)?(\w+)", _code()))
    assert len(declared) >= 35, "the population of the check must not be vacuous"
    anywhere = re.compile(rf"\b{kinds}\s+(?:<'[^']*'>\s*)?(\w+)")
    taken: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == MODEL:
                continue
            for name in anywhere.findall(strip_comments(path.read_text(encoding="utf-8"))):
                if name in declared:
                    taken.setdefault(name, []).append(path.name)
    assert not taken, f"declared in another package too: {taken}"


def test_the_guide_states_the_models_question_and_scope_and_no_more():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "**Status: Phase 0 framing proposal.**" in guide
    quoted = _flat(" ".join(line[1:].strip() for line in guide.splitlines() if line.startswith(">")))
    assert quoted == _doc("part hmiDisplayQuestion : IncrementEngineeringQuestion"), \
        "the guide quotes the model's engineering question word for word"
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in guide.split("## What the increment judges", 1)[1].split("\n\n", 2)[1].splitlines()]
    assert rows[0] == ["In scope", "Out of scope"]
    cells_in = [row[0] for row in rows[2:] if row[0]]
    cells_out = [row[1] for row in rows[2:] if row[1]]
    assert cells_in == list(IN_SCOPE.values()), "the table's in-scope column is the model's in-scope items"
    assert cells_out == list(OUT_OF_SCOPE.values()), "the table's out-of-scope column is the model's items"
    for target in ("../../textual-notation-of-model/packages/features/hmi/hmi_display_framing.sysml",
                   "../../textual-notation-of-model/packages/features/hmi/VIEWS.md",
                   "../../textual-notation-of-model/packages/features/hmi/upstream.md",
                   "../../textual-notation-of-model/packages/features/hmi/upstream.md"
                   "#questions-requiring-upstream-engagement",
                   "driver-assistance-increment.md",
                   "../architecture-decisions/0026-hmi-display-in-every-member-product.md",
                   "../../textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"):
        assert f"]({target})" in guide, target
    flat = _flat(guide)
    for phrase in ("No implementation, run, result, product-line admission or compliance is claimed.",
                   "It takes the warning request as that increment defines it and changes none of its criteria or "
                   "verdicts.",
                   "A fail is a result to record.",
                   "Starting this increment launches no compute and authorizes no spend.",
                   "The framing's boundary concern does not open Phase 1.",
                   "The owner decided on 2026-11-17 that Phase 1 starts after Phase 10 of the driver-assistance "
                   "increment,"):
        assert phrase in flat, phrase
    boundaries = _flat(guide.split("## Boundaries", 1)[1].split("\n## ", 1)[0])
    for phrase in ("The HMI display of the VisionPilot configuration is a proposed **System 1** subject",
                   "Two parts of **System 1** are outside its boundary, and neither is an enabler: the candidate "
                   "application, which perceives, plans and requests the warning, and the Eclipse S-CORE path that "
                   "carries its outputs to the SDV Core VM.",
                   "are **System 2** enablers, not vehicle features.",
                   "The capture observes the AAOS SDV and is no part of it.",
                   "It is no safety claim"):
        assert phrase in boundaries, phrase
    assert boundaries.count("**System 1**") == 2 and boundaries.count("**System 2**") == 1


def test_the_guide_lists_each_gap_as_an_open_point_in_the_models_own_words():
    order = re.findall(r"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*IncrementGap\b", _code())
    assert order == list(OPEN_POINTS) == list(GAPS), "one open point for each gap, in the model's order"
    guide = GUIDE.read_text(encoding="utf-8")
    open_points = guide.split("## What the framing already records as open", 1)[1].split("\n## ", 1)[0]
    bullets = re.findall(r"(?ms)^- \*\*(.+?)\*\*\s+\(`(\w+)`\)\.\s+(.*?)(?=^- \*\*|\n\n)", open_points)
    assert len(re.findall(r"(?m)^- ", open_points)) == len(bullets), "every bullet has a label and names its gap"
    assert [(name, label) for label, name, _body in bullets] == list(OPEN_POINTS.items())
    for _label, name, body in bullets:
        assert len(body.split()) >= 8, f"{name}: an open point says what is open"
        assert _flat(body) in _doc(f"part {name} : IncrementGap"), \
            f"{name}: the open point is not a passage of the gap's own text"


def test_the_upstream_record_pins_what_the_framing_read():
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    assert record.startswith("# HMI display: upstream provenance\n")
    assert [line[3:] for line in record.splitlines() if line.startswith("## ")] == [
        "High availability renderer", "VisionPilot scene", "Questions requiring upstream engagement",
        "Upstream contact"]
    # every link into the display safety projects is at the commit that the framing read
    service = re.findall(r"android\.googlesource\.com/platform/packages/services/display_safety(?:/\+/([^/)\s]+))?",
                         record)
    assert len(service) == 11 and set(service) == {DISPLAY_SAFETY_PIN}, service
    device = re.findall(r"android\.googlesource\.com/device/google/sdv_display_safety(?:/\+/([^/)\s]+))?", record)
    assert device == [DEVICE_PIN]
    # every VisionPilot link is at the commit that the driving record names for INC-DRIVING-002
    pinned = re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/([^/)\s]+)", record)
    assert len(pinned) == 7 and set(pinned) == {VISIONPILOT_PIN}
    assert f"commit `{VISIONPILOT_PIN}`" in DRIVING_RECORD.read_text(encoding="utf-8")
    assert "(../driving/upstream.md#visionpilot)" in record
    renderer = _link_text(_record_section(record, "High availability renderer"))
    for phrase in (f"commit `{DISPLAY_SAFETY_PIN}` of the branch `android17-release`",
                   "The pages carry no revision; they were read on the same day.",
                   "Which revision a bench runs is a decision of phase 8.",
                   "HAR renders the display elements that must be present quickly after a cold boot, and placeholder "
                   "elements when Android is unavailable.",
                   "Google's reference implementation of the safety monitor carries no ASIL certification.",
                   "include `adas` and no collision warning, forward-collision warning or emergency braking signal.",
                   "the telltales have no such variant.",
                   "holds no collision chime.",
                   "Design documents of the reference app, in the design tool's own format, are in",
                   "it computes from the time alone. Between 25 s and 30 s of its loop it draws a front-collision mark "
                   "on the lead car. Whether the app on the SDV Media VM runs that scene is not traced.",
                   "DE4SDV has not run HAR."):
        assert phrase in renderer, phrase
    scene = _link_text(_record_section(record, "VisionPilot scene"))
    for phrase in ("is built only when the option `ENABLE_OCCUPANCY` is on, and the option is off by default.",
                   "the path that the candidate's lateral fusion fits to them",
                   "The bridge takes the plan as an argument and does not read it.",
                   "places each detection on the road through the same homography.",
                   "labels the closest object with its projected position.",
                   "hands the scene to the panel inside the application's process.",
                   "a detection's class is a level relative to the path, not a type of object.",
                   "The fusion reads level 1 as the same lane and level 2 as the adjacent lane;",
                   "a fused distance and a fused speed."):
        assert phrase in scene, phrase
    questions = _record_section(record, "Questions requiring upstream engagement")
    assert questions.count("\nDisplay safety of AAOS SDV:\n") == 1 and questions.count("\nVisionPilot:\n") == 1
    assert len(re.findall(r"(?m)^- ", questions)) == 5, "four questions for display safety and one for VisionPilot"
    contact = _flat(_record_section(record, "Upstream contact"))
    assert contact.startswith("DE4SDV has posted nothing about this increment in the display safety project or in "
                              "the VisionPilot repository.")
    exchange = re.compile(r"(?i)\bDE4SDV (?:has )?(?:confirmed|agreed|asked|contacted|told|informed|reported|"
                          r"discussed|opened|sent)\b")
    assert not exchange.findall(_flat(record)), exchange.findall(_flat(record))
