"""Content pins for the framing of the HMI display increment, not semantic validation.

The framing of INC-HMI-001 holds Phase 0 and the Phase 1 concerns. These tests hold its structure
to the method's Phase 0 and Phase 1 shapes, pin each decided statement by its own phrase, and hold
the guide, the folder's upstream record and the rows that name the increment elsewhere to the model.
They read the model text; they do not parse SysML.

What they do not hold: a sentence that no pin names can change inside a doc of the model or
inside the record, and a report of a run in words that the scan for past behavior does not list
passes. Those are for the review of the text.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sysml_shapes import braced_body, strip_comments
from test_saf_domains import SAF_FILE, _domains
from test_views_per_phase import _canonical_list

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
MIDDLEWARE_CONFIGURATION = FEATURES / "middleware/middleware_variability_configuration.sysml"
ADR_0025 = ROOT / "docs/architecture-decisions/0025-end-someip-in-an-sdv-core-vm.md"
AEBS_REQUIREMENTS = FEATURES / "aebs/aebs_needs_requirements.sysml"
DE4SDV_CATALOGUE = ROOT / \
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml"
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
    "gapHmiStandaloneLinuxDisplay": "the standalone member selects a display that has no realization",
    "gapHmiAAOSIntegratedGuestDisplay": "Its guest now needs a display.",
    "gapHmiDisplayInProductLine": "No shared asset implements the display yet",
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
    "gapHmiStandaloneLinuxDisplay": "No Linux-side display",
    "gapHmiAAOSIntegratedGuestDisplay": "A headless guest with a display",
    "gapHmiDisplayInProductLine": "The HMI display's place in the product line",
    "gapHmiUpstreamContact": "No upstream contact",
}
#: The correction of the answer of hmiContentVarianceConcern in Phase 3: Phase 1 named a classification view of
#: Phase 3 as its answer, and a Phase 3 that records no characteristic publishes no view (increment-workflow,
#: views per phase). The concern states the fact instead, in the model's words, and names no later view.
CONTENT_VARIANCE_FACT = (
    "The framing view frames it.",
    "Phase 3 gives each content item its reason in its classification and records no characteristic, since the "
    "increment adds none that tells the member products apart, so phase 3 has no view; which content becomes common "
    "is for the lifecycle decision.")
#: the one concern that no view of a later phase answers, and why: its phase records no characteristic
NO_LATER_VIEW = {"hmiContentVarianceConcern": CONTENT_VARIANCE_FACT[1]}
#: Phase 1: concern -> (its concern definition, the in-scope items its doc names first, the part of them it asks
#: about or None, its native stakeholders in order, the sentences that state its question, and the views that answer
#: it as (phase, viewpoint definition) pairs, read from the doc's answer). One concern per question; a concern is held
#: by the parties whose interest it states, not only by the roles that check it.
PHASE1_CONCERNS = {
    "hmiDriverSupervisionConcern": (
        "OperationalCapabilityConcern",
        ("hmiSceneInScope", "hmiSpeedInScope", "hmiCollisionWarningInScope", "hmiAndroidOutageInScope"), "operational",
        [("occupant", "VehicleOccupant")],
        ("The driver, a vehicle occupant, needs to see on the HMI display what the driving application perceives, its "
         "lane, the path it fits to that lane and the objects it detects, beside the vehicle speed, to get a warning "
         "of an imminent collision on the display and as a sound, and to see the speed and the warning, or the fact "
         "that the warning is unavailable, also while Android in the IVI VM hangs, boots or restarts.",
         "It states what the driver expects to see, not how a driver reads it: no human-factors, safety or on-road "
         "claim follows from it."),
        ((2, "OperationalStoryViewpoint"),)),
    "hmiDisplayInputsConcern": (
        "SystemContextExchangeConcern", ("hmiSceneInScope", "hmiSpeedInScope", "hmiCollisionWarningInScope"), None,
        [("systemsEngineer", "SystemsEngineer"), ("safetyExpert", "SafetyExpert")],
        ("Systems engineers and safety experts need to see which items cross into the HMI display from outside its "
         "boundary: the lane of the candidate application, the path it fits to that lane, the objects it detects with "
         "their level relative to its path, the closest object in its path with the distance and the speed that its "
         "fusion gives, the vehicle speed that the candidate is given, and the candidate's warning request.",
         "Each item reaches the display as its source gives it.",
         "The display takes no object that the candidate does not give: neither the simulator's own record of the "
         "scene nor an estimate of its own (hmiSimulatorTruthOutOfScope), so it shows what the candidate perceives, "
         "right or wrong.",
         "Whether the scene can leave the candidate's process is open (gapHmiSceneOutput), and what the scene carries "
         "bounds what the display can show of it (gapHmiSceneContent)."),
        ((6, "SystemProcessViewpoint"),)),
    "hmiContentVarianceConcern": (
        "ProductLineCapabilityClassificationConcern",
        ("hmiSceneInScope", "hmiSpeedInScope", "hmiCollisionWarningInScope"), "product-line",
        [("productLineEngineer", "ProductLineEngineer")],
        ("Product-line engineers need to see which content of the HMI display is common to the member products and "
         "which derives from a member's driving application.",
         "The scene is what one driving application perceives, and the scenes of the other driving applications of "
         "the product line are out of scope (hmiOtherDrivingApplicationsOutOfScope).",
         "The classification is made against the governed scope as its revision leaves it "
         "(gapHmiDisplayInProductLine).",
         *CONTENT_VARIANCE_FACT),
        ()),
    "hmiWarningSequenceConcern": (
        "SystemProcessConcern", ("hmiCollisionWarningInScope",), None,
        [("safetyExpert", "SafetyExpert"), ("systemsEngineer", "SystemsEngineer")],
        ("Safety experts and systems engineers need to see the sequence from the candidate's warning request to the "
         "collision warning on the display and to its sound, and the time of each step within the time that the "
         "driver-assistance increment allots from the request to each mode, independent of the elements that realize "
         "it.",
         "The warning request is taken as the driver-assistance increment defines it, and how that time divides on a "
         "path to the SDV Media VM is open (gapHmiWarningPresentation)."),
        ((6, "SystemProcessViewpoint"),)),
    "hmiContentCurrencyConcern": (
        "SystemStateConcern", ("hmiStaleContentInScope",), None,
        [("safetyExpert", "SafetyExpert"), ("verificationEngineer", "VerificationEngineer")],
        ("Safety experts and verification engineers need to see the states that each element of the HMI display can "
         "be in, current, late or missing, and what the display shows in each, so that no element is shown as current "
         "when it is not: late data is never shown as live.",
         "The warning can also be unavailable, and whether the display learns that from the age of its inputs or from "
         "a signal of its own is open (gapHmiWarningAvailability).",
         "From which age an element counts as late is for phase 5 to state."),
        ((6, "SystemStateViewpoint"),)),
    "hmiAndroidOutageConcern": (
        "SystemProcessConcern", ("hmiAndroidOutageInScope",), None,
        [("safetyExpert", "SafetyExpert"), ("systemsEngineer", "SystemsEngineer")],
        ("Safety experts and systems engineers need to see the sequence from each outage of the drawing of the scene "
         "and of the environment that hosts it, the drawing hanging or ending and its host hanging, booting or "
         "restarting, to its detection and to what the display shows then: the speed and the warning, or the fact that "
         "the warning is unavailable, independent of the elements that realize it.",
         "Phase 6 treats each outage as an event of an element inside the boundary of the HMI display.",
         "It rests on the product line's need that the availability of the AEBS be apparent when its inputs or its "
         "functions are not healthy (N-AEBS-008) and on the status indication of REQ-AEBS-013.",
         "No safety argument follows from it."),
        ((6, "SystemProcessViewpoint"),)),
    "hmiRendererAllocationConcern": (
        "PhysicalFunctionalMappingConcern", ("hmiRendererSplitInScope",), "drawing",
        [("productLineEngineer", "ProductLineEngineer"), ("safetyExpert", "SafetyExpert")],
        ("Product-line engineers and safety experts need to see which renderer realizes the drawing of each element of "
         "the HMI display: the high availability renderer in an SDV Media VM the speed, the collision warning and its "
         "sound, and an app in the IVI VM the scene, as the owner decided on 2026-11-17.",
         "The split rests on what the driver sees while Android in the IVI VM hangs, boots or restarts (N-AEBS-008, "
         "REQ-AEBS-013), not on an end of the app that draws the scene.",
         "The renderer's vehicle data holds no collision warning (gapHmiRendererCollisionWarning), and drawing an "
         "element with it is no safety approval of that element.",
         "The lifecycle decision is whether the renderer or an app in the IVI VM draws the common content where a "
         "member has an AAOS SDV guest."),
        ((8, "PhysicalLogicalMappingViewpoint"),)),
    "hmiRendererPathConcern": (
        "PhysicalInternalExchangeConcern", ("hmiRendererSplitInScope",), "paths",
        [("systemArchitect", "SystemArchitect"), ("systemsEngineer", "SystemsEngineer")],
        ("System architects and systems engineers need to see which elements exchange each input of the HMI display on "
         "its way from the SDV Core VM to the high availability renderer in the SDV Media VM and to the app in the IVI "
         "VM that draws the scene, the exchange by which that app tells the renderer that Android is alive, and the "
         "boundary interface by which each input enters the display.",
         "A renderer in an SDV Media VM adds a third VM to the guest (gapHmiMemberGuestLayout), and the renderer's "
         "path from the SDV Core VM is not observed (gapHmiRendererIntegration)."),
        ((8, "PhysicalInternalExchangeViewpoint"),)),
    "hmiDisplayVerdictConcern": (
        "ArgumentationAssuranceConcern", ("hmiVerdictEvidenceInScope",), None,
        [("productLineEngineer", "ProductLineEngineer"), ("verificationEngineer", "VerificationEngineer")],
        ("Product-line engineers and verification engineers need the lifecycle decision to rest on a pass or a fail "
         "for each requirement and scenario, each bound to the candidate revision, the display build and the "
         "configuration that ran, holding what the display shows against what the candidate gives and when.",
         "A recording of a display that looks right is no verdict, a verdict holds for the simulated configuration "
         "only (asmHmiSimulationStandsIn), and a fail stays a recorded result."),
        ((10, "ArgumentationAssuranceViewpoint"),)),
}
#: Phase 1 concern -> (the label of its bullet in the guide, the nonclaim or boundary sentences the bullet keeps).
#: The bullet's concern definition and holders are read from the model's concern, not from this table.
GUIDE_CONCERNS = {
    "hmiDriverSupervisionConcern": ("What the driver sees",
                                    ("No human-factors, safety or on-road claim follows from it.",)),
    "hmiDisplayInputsConcern": ("What the display takes in",
                                ("The display takes no object that the candidate does not give: neither the "
                                 "simulator's own record of the scene nor an estimate of its own.",)),
    "hmiContentVarianceConcern": ("Common or derived content",
                                  ("The scenes of the other driving applications are out of scope.",
                                   "The framing view frames it.",
                                   "Phase 3 gives each content item its reason in its classification and records no "
                                   "characteristic, since the increment adds none that tells the member products "
                                   "apart, so Phase 3 has no view; which content becomes common is for the lifecycle "
                                   "decision.")),
    "hmiWarningSequenceConcern": ("The warning's sequence",
                                  ("The warning request is taken as the driver-assistance increment defines it.",)),
    "hmiContentCurrencyConcern": ("Late and missing content",
                                  ("No element is shown as current when it is not: late data is never shown as "
                                   "live.",)),
    "hmiAndroidOutageConcern": ("Outages of the scene's drawing",
                                ("Phase 6 treats each outage as an event of an element inside the display's "
                                 "boundary.",
                                 "It rests on N-AEBS-008 and REQ-AEBS-013.", "No safety argument follows from it.")),
    "hmiRendererAllocationConcern": ("Which renderer draws what",
                                     ("The split rests on what the driver sees while Android in the IVI VM hangs, "
                                      "boots or restarts, not on an end of the app that draws the scene.",
                                      "Drawing an element with the renderer is no safety approval of that element.")),
    "hmiRendererPathConcern": ("The paths to the renderers", ()),
    "hmiDisplayVerdictConcern": ("Verdicts", ("A recording of a display that looks right is no verdict.",)),
}
#: the words by which a concern's doc names a view that answers it -> the viewpoint definition of that view
VIEW_PHRASES = {
    "operational story": "OperationalStoryViewpoint",
    "product-line classification view": "ProductLineClassificationViewpoint",
    "system process": "SystemProcessViewpoint",
    "system state": "SystemStateViewpoint",
    "physical-logical mapping": "PhysicalLogicalMappingViewpoint",
    "view of the claimed path": "PhysicalInternalExchangeViewpoint",
    "argumentation assurance view": "ArgumentationAssuranceViewpoint",
}
#: a sentence of a concern's doc that says by which views the concern is answered
ANSWER_SENTENCE = re.compile(r"[^.]*\banswered\b[^.]*\.", re.I)
#: the owner's decision of 2026-11-21 on the timing of the increment, and the end of the wait for the scope revision,
#: in the model's words
GO_ON_NOW = (
    "The owner decided on 2026-11-21 that the increment goes on without waiting for Phase 10 of the "
    "driver-assistance increment.",
    "Phase 3 and later phases waited for the revision of the governed scope (gapHmiDisplayInProductLine), which the "
    "model now holds, so they go on.")
#: the text that said Phase 3 waits for the scope revision, which the scope revision ended
STILL_WAITS = "Phase 3 and later phases wait for the revision of the governed scope"
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


def _prose(text: str) -> str:
    """The text without block-comment leaders and line breaks, so that a wrapped sentence reads as one."""
    return _flat(re.sub(r"(?m)^\s*\*\s?", "", text))


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
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1)) == [
        PACKAGE, "DE4SDV_HmiDisplayOperationalContext", "DE4SDV_HmiDisplayCapabilityClassification",
        "DE4SDV_HmiDisplayNeedsRequirements", "DE4SDV_HmiDisplayFunctionalArchitecture",
        "DE4SDV_HmiDisplayLogicalArchitecture", "DE4SDV_HmiDisplayPhysicalSoftwareRealization"], \
        "the charter names only the packages that hold content"
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
                   *GO_ON_NOW,
                   "This package holds Phase 0 and the Phase 1 concerns."):
        assert phrase in increment, phrase
    assert "This package holds only Phase 0." not in increment
    assert STILL_WAITS not in increment, "the scope revision ended the wait"
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
                   "Which part of System 1 brings the vehicle speed to the SDV Core VM is for the architecture phases "
                   "to place.",
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
                   "The configuration that the driver-assistance increment realizes for the candidate keeps the "
                   "visualization in the candidate's loop off.",
                   "That increment's visualization recorder, an observer of System 2 in the candidate's process, draws "
                   "upstream's visualization into the bench's recording only, from a copy that a second hand-off in "
                   "the loop gives it.",
                   "With the recorder the candidate gives its command a few milliseconds later "
                   "(phase8VisualizationRecorderPlaced)."):
        assert phrase in output, phrase
    # the judged configuration keeps the visualization in the loop off, and the driver-assistance increment's
    # recorder draws it from a second hand-off into the bench's recording only, a few milliseconds later
    driving_realization = _prose(DRIVING_REALIZATION.read_text(encoding="utf-8"))
    for phrase in ("The configuration keeps visualization_on = false, so upstream's drawing in the loop stays off.",
                   "It is not the driver's display: it goes only into the bench's recording.",
                   "from a second hand-off in the loop after vision_pilot.cpp:174",
                   "an observer of System 2 that carries no logical element",
                   "With the recorder running the candidate gives its command a few milliseconds later"):
        assert phrase in driving_realization, phrase
    assert re.search(r"(?m)^  comment phase8VisualizationRecorderPlaced about ",
                     DRIVING_REALIZATION.read_text(encoding="utf-8"))
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
                   "Its realization records the high availability renderer for that warning as an alternative that "
                   "the owner did not select for it on 2026-11-17 (ALT-DRIVING-HARWARNING-001).",
                   "The realization and the verdicts of the driver-assistance increment stay as they are."):
        assert phrase in presentation, phrase
    # the driver-assistance increment's realization records that alternative as not selected for it
    item = re.search(r"(?m)^ \* - ALT-DRIVING-HARWARNING-001:(.*\n(?: \*   .*\n)*)",
                     DRIVING_REALIZATION.read_text(encoding="utf-8"))
    assert item, "the driver-assistance realization records the renderer as an alternative"
    alternative = _prose(item.group(1))
    assert "the High Availability Renderer of Android SDV's display safety shows the collision warning" in alternative
    assert "Not selected by the owner on 2026-11-17 for this increment." in alternative
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
    for phrase in ("The owner decided on 2026-11-13 that every member product has an HMI display (ADR 0026).",
                   "The governed scope holds the HMI display as common content of every planned member, bound "
                   "during Development, and every member configuration selects the feature hmiDisplay, which "
                   "corresponds to that common content.",
                   "Where the display runs follows the integration mode: in the AAOS SDV guest of the two integrated "
                   "members, and on the Linux side of the standalone member.",
                   "No shared asset implements the display yet, and what it shows in each member is open.",
                   "The owner decided on 2026-11-21 that this increment records the two gaps that the scope revision "
                   "leaves in the members (gapHmiStandaloneLinuxDisplay, gapHmiAAOSIntegratedGuestDisplay).",
                   "Phase 3 classifies the content of the display against the scope as it now stands."):
        assert phrase in product_line, phrase
    for stale in ("an optional feature that requires the AAOS SDV guest", "neither governed member selects it",
                  "takes effect with a revision of the governed scope"):
        assert stale not in product_line, stale
    standalone = _doc("part gapHmiStandaloneLinuxDisplay : IncrementGap")
    for phrase in ("The standalone member selects the HMI display, common content of every member product (ADR 0026).",
                   "It has no AAOS SDV guest, so its display is a Linux-side display, and no such display exists: no "
                   "shared asset implements one, and the standalone member selects a display that has no "
                   "realization.",
                   "That the display is common is a scope classification, not evidence about the display.",
                   "This increment leaves the Linux-side display out of its scope (hmiStandaloneDisplayOutOfScope), "
                   "and its design is open."):
        assert phrase in standalone, phrase
    guest = _doc("part gapHmiAAOSIntegratedGuestDisplay : IncrementGap")
    for phrase in ("The AAOS-integrated member, MW-CONFIG-001, selects the HMI display, which it holds in its AAOS SDV "
                   "guest (ADR 0026).",
                   "Its configured member models a headless guest: its guest middleware is a headless SDV Core "
                   "boundary, and its retained evidence names the headless sdv_core_cf image.",
                   "Which VM of the guest holds the display is realization content, as ADR 0025 says for the S-CORE "
                   "member, and it is open.",
                   "The records of INC-MW-010 stay retained against the earlier content and are not edited."):
        assert phrase in guest, phrase
    # the configured member that models the headless guest names this gap
    assert "(gapHmiAAOSIntegratedGuestDisplay of INC-HMI-001)" in _flat(
        MIDDLEWARE_CONFIGURATION.read_text(encoding="utf-8").replace("*", ""))
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
        "hmiDisplayBoundary": "IncrementBoundaryConcern",
        **{name: spec[0] for name, spec in PHASE1_CONCERNS.items()}}, \
        "the boundary concern of Phase 0 and the concerns of Phase 1, no other"

    view = braced_body(code, "view hmiDisplayFramingView")
    viewpoint = braced_body(view, "viewpoint hmiDisplayFramingViewpoint : IncrementFramingViewpoint")
    frames = re.findall(r"\bframe\s+(\w+)\s*;", viewpoint)
    assert frames == ["hmiDisplayBoundary", *PHASE1_CONCERNS], \
        "the one framing viewpoint frames every concern of the increment once, in the model's order"
    assert "render asTreeDiagram;" in view
    exposed = re.findall(r"\bexpose\s+(\w+)\s*;", view)
    assert len(exposed) == len(set(exposed)), "an element is exposed once"

    usages = {name for _kind, name, _type in PACKAGE_USAGE.findall(code)}
    kinds = {kind for _kind, _name, kind in PACKAGE_USAGE.findall(code)}
    assert len(usages) >= 30, "the population of the exposure check must not be vacuous"
    assert {"InScopeItem", "OutOfScopeItem", "IncrementAssumption", "IncrementGap", "IncrementCharter",
            "IncrementScope", "ProblemStatement", "IncrementBoundaryConcern"} <= kinds
    assert set(PHASE1_CONCERNS) <= set(exposed), "the framing view shows every Phase 1 concern"
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
    for phrase in ("Phase 0 framing and the Phase 1 concerns only", "no implementation", "no runtime result",
                   "no product-line", "no compliance"):
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
    assert ("**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability "
            "classification, Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 "
            "logical architecture and Phase 8 physical and software realization, proposal.**") in _flat(guide)
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
                   "open gaps and Phase 1 concerns.",
                   "Phase 3, the capability classification, records no feature-model delta, and review judges it: "
                   "its one blocking check has nothing to evaluate",
                   "The next model obligation is **Phase 9**: the configuration, which makes the realization of the "
                   "increment a configured product; its first gate is `incrementHasConfiguredProduct`.",
                   "On 2026-11-21 the owner decided that the increment goes on without waiting for Phase 10 of the "
                   "driver-assistance increment.",
                   "Phase 3 and later phases waited for the revision of the governed scope, which the model now "
                   "holds, so they go on.",
                   "On 2026-11-17 the owner decided that the readiness probe of the high availability renderer runs "
                   "with its cost put to him first."):
        assert phrase in flat, phrase
    for stale in ("The framing's boundary concern does not open Phase 1.", "**Phase 1 concern framing**",
                  "that Phase 1 starts after Phase 10 of the driver-assistance increment", STILL_WAITS,
                  "The next model obligation is **Phase 3**", "The next model obligation is **Phase 4**",
                  "The next model obligation is **Phase 5**", "The next model obligation is **Phase 6**",
                  "The next model obligation is **Phase 7**"):
        assert stale not in flat, f"Phase 1 is framed and goes on now: {stale}"
    boundaries = _flat(guide.split("## Boundaries", 1)[1].split("\n## ", 1)[0])
    for phrase in ("The HMI display of the VisionPilot configuration is a proposed **System 1** subject",
                   "Two parts of **System 1** are outside its boundary, and neither is an enabler: the candidate "
                   "application, which perceives, plans and requests the warning, and the Eclipse S-CORE path that "
                   "carries its outputs to the SDV Core VM.",
                   "Which part of System 1 brings the vehicle speed to the SDV Core VM is for the architecture phases "
                   "to place.",
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
    # every VisionPilot link is at the commit that the driving record names for INC-DRIVING-002: seven of the
    # framing and ten of phase 5, one for each line range that a rationale cites
    pinned = re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/([^/)\s]+)", record)
    assert len(pinned) == 17 and set(pinned) == {VISIONPILOT_PIN}
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


def _answers(doc: str) -> set[tuple[int, str]]:
    """The (phase, viewpoint definition) pairs that the answer sentences of a concern's doc name."""
    phrases = "|".join(re.escape(phrase) for phrase in VIEW_PHRASES)
    found = set()
    for sentence in ANSWER_SENTENCE.findall(doc):
        pairs = re.findall(rf"\b({phrases}) (?:of|in) phase (\d+)\b", sentence)
        assert pairs, f"an answer that names no view of the method: {sentence.strip()}"
        found.update((int(phase), VIEW_PHRASES[phrase]) for phrase, phase in pairs)
    return found


def _concern_doc(name: str, kind: str) -> str:
    return _doc(f"concern {name} : {kind}")


def _lead(items: tuple[str, ...], part: str | None) -> str:
    """The in-scope items a concern's doc opens with, and the part of them it asks about."""
    lead = ", ".join(items[:-1]) + (" and " if len(items) > 1 else "") + items[-1]
    return lead + (f", {part} part." if part else ".")


def test_phase_one_frames_one_concern_for_each_question_of_the_scope():
    code = _code()
    assert "private import SAF_Viewpoints::*;" in code, "the SAF concern definitions come from the catalogue"
    assert not re.search(r"\b(?:concern|viewpoint) def\b", code), \
        "concern types come from the catalogues, never the slice"
    assert re.findall(r"\bpart def (\w+)", code) == ["HmiDisplayIncrement", "HmiDisplaySystem"], \
        "stakeholder roles come from the kernel, never the slice"
    saf = SAF_FILE.read_text(encoding="utf-8")
    de4sdv = DE4SDV_CATALOGUE.read_text(encoding="utf-8")
    answered = set()
    for name, (kind, items, part, holders, sentences, answer) in PHASE1_CONCERNS.items():
        # an SAF definition where one asks the question; the method's own definition only for the product line,
        # which the SAF grid has no row for
        in_saf = len(re.findall(rf"\bconcern def {kind} :> \w+DomainConcern\s*\{{", saf)) == 1
        in_de4sdv = len(re.findall(rf"\bconcern def {kind}\s*\{{", de4sdv)) == 1
        assert in_saf != in_de4sdv, f"{name}: {kind} is a concern definition of exactly one catalogue"
        assert in_saf or kind == "ProductLineCapabilityClassificationConcern", \
            f"{name}: only the product-line question takes the method's own definition"
        body = braced_body(code, f"concern {name} : {kind}")
        parameters = [line.strip() for line in body.splitlines() if line.strip() and line.strip() != "doc"]
        assert parameters[0] == "subject;", f"{name}: the subject is the first parameter"
        assert re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body) == holders, name
        doc = _concern_doc(name, kind)
        lead = _lead(items, part)
        assert doc.startswith(lead), f"{name}: the doc opens with the in-scope items it answers: {doc[:80]}"
        for sentence in sentences:
            assert sentence in doc, (name, sentence)
        rest = ANSWER_SENTENCE.sub("", doc[len(lead):])
        assert rest.split() == " ".join(sentences).split(), \
            f"{name}: the doc holds only its pinned sentences and its answer"
        assert doc.index(sentences[0]) == len(lead) + 1, f"{name}: the holders' need follows the in-scope items"
        assert _answers(doc) == set(answer), (name, sorted(_answers(doc)))
        answered.update(items)
    in_scope = _declared("InScopeItem")
    assert answered == in_scope, f"in-scope items without a concern: {sorted(in_scope - answered)}"
    # incrementHasNonBoundaryConcern: no Phase 1 concern lies in the boundary-concern lineage
    assert not {kind for kind, *_rest in PHASE1_CONCERNS.values()} & {"IncrementBoundaryConcern"}
    assert "IncrementBoundaryConcern" not in braced_body(
        de4sdv, "concern def ProductLineCapabilityClassificationConcern")


def test_every_in_scope_item_has_a_concern_for_each_question_the_increment_asks_of_it():
    # The split of the renderers asks two questions, answered from different evidence: which renderer draws what,
    # and the paths that bring their inputs. The scene asks what the driver sees, what crosses into the display and
    # whether it is common content.
    asked: dict[str, list[str]] = {}
    for name, (_kind, items, _part, *_rest) in PHASE1_CONCERNS.items():
        for item in items:
            asked.setdefault(item, []).append(name)
    assert asked["hmiRendererSplitInScope"] == ["hmiRendererAllocationConcern", "hmiRendererPathConcern"]
    assert asked["hmiSceneInScope"] == ["hmiDriverSupervisionConcern", "hmiDisplayInputsConcern",
                                        "hmiContentVarianceConcern"]
    parts = [(name, spec[2]) for name, spec in PHASE1_CONCERNS.items() if spec[2]]
    assert parts == [("hmiDriverSupervisionConcern", "operational"), ("hmiContentVarianceConcern", "product-line"),
                     ("hmiRendererAllocationConcern", "drawing"), ("hmiRendererPathConcern", "paths")]


def test_every_stakeholder_of_the_problem_holds_a_phase_one_concern_and_the_driver_holds_their_own():
    # The concerns' holders are the parties whose interest each states: the five roles of the problem statement and
    # the system architects. The driver, a vehicle occupant, holds the operational concern alone.
    code = _code()
    problem = braced_body(code, "requirement hmiDisplayProblem : ProblemStatement")
    roles = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", problem))
    # the holders as the model declares them, not as this file lists them
    declared = {name: set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;",
                                     braced_body(code, f"concern {name} : {kind}")))
                for name, (kind, *_rest) in PHASE1_CONCERNS.items()}
    held = set().union(*declared.values())
    assert roles <= held, f"problem stakeholders that hold no Phase 1 concern: {sorted(roles - held)}"
    assert held - roles == {"SystemArchitect"}, sorted(held - roles)
    beneficiaries = [name for name, holders in declared.items() if "VehicleOccupant" in holders]
    assert beneficiaries == ["hmiDriverSupervisionConcern"]
    assert declared["hmiDriverSupervisionConcern"] == {"VehicleOccupant"}, "the driver holds the operational concern"
    assert PHASE1_CONCERNS["hmiDriverSupervisionConcern"][0] == "OperationalCapabilityConcern"
    operational = _concern_doc("hmiDriverSupervisionConcern", "OperationalCapabilityConcern")
    assert "Reviewers need" not in operational and "engineers" not in operational
    # within the charter: what the driver expects to see, with no claim the scope leaves out
    assert not re.search(r"(?i)\b(?:glance|comprehension|distraction|safely|safer|compliance|reliab\w*|"
                         r"performs?)\b", operational)
    for item in PHASE1_CONCERNS["hmiDriverSupervisionConcern"][1]:
        assert item in _declared("InScopeItem")


def test_the_display_shows_perception_only_and_no_late_element_as_current():
    # Two decided statements of the scope, each held by its own concern: the display shows no object that the
    # candidate does not give, and it shows no late element as current. The inputs are the boundary's: the scene, the
    # speed and the warning request, so the closed list leaves out no input and no open option of a signal of its own.
    inputs = _concern_doc("hmiDisplayInputsConcern", "SystemContextExchangeConcern")
    assert "the vehicle speed that the candidate is given, and the candidate's warning request." in inputs
    assert "The display takes no object that the candidate does not give:" in inputs
    assert "takes no other item" not in inputs, "the closed list is of objects, not of every input"
    system = _prose(braced_body(_raw(), "part def HmiDisplaySystem"))
    assert "the warning request that the candidate application gives" in system, "the boundary takes the request"
    assert "neither the simulator's own record of the scene nor an estimate of its own" in inputs
    assert "so it shows what the candidate perceives, right or wrong." in inputs
    assert "(hmiSimulatorTruthOutOfScope)" in inputs and "hmiSimulatorTruthOutOfScope" in _declared("OutOfScopeItem")
    currency = _concern_doc("hmiContentCurrencyConcern", "SystemStateConcern")
    assert "so that no element is shown as current when it is not: late data is never shown as live." in currency
    assert "current, late or missing" in currency


def test_the_split_rests_on_android_and_on_the_aebs_status_need_not_on_an_end_of_the_scene_app():
    allocation = _concern_doc("hmiRendererAllocationConcern", "PhysicalFunctionalMappingConcern")
    assert ("The split rests on what the driver sees while Android in the IVI VM hangs, boots or restarts (N-AEBS-008, "
            "REQ-AEBS-013), not on an end of the app that draws the scene.") in allocation
    assert "no safety approval" in allocation
    outage = _concern_doc("hmiAndroidOutageConcern", "SystemProcessConcern")
    assert "(N-AEBS-008)" in outage and "REQ-AEBS-013" in outage
    # a conceptual sequence: past its in-scope item the doc names no platform; the paths concern names them
    trigger = outage.removeprefix("hmiAndroidOutageInScope.")
    assert not re.search(r"\bAndroid\b|\bIVI VM\b|\bapp\b", trigger), trigger
    assert "an event of an element inside the boundary of the HMI display" in trigger
    assert "Android is alive" in _concern_doc("hmiRendererPathConcern", "PhysicalInternalExchangeConcern")
    # the need and the requirement are those of the AEBS model, with the text the concerns rely on
    aebs = AEBS_REQUIREMENTS.read_text(encoding="utf-8")
    need = braced_body(aebs, "requirement needBoundedDegradationAndAvailability : ProductSafetyAvailabilityNeed")
    assert "N-AEBS-008" in need and "AEBS availability is apparent when required inputs or AEBS functions are not " \
        "healthy" in _flat(need)
    requirement = braced_body(aebs, "requirement reqIndicateDegradedUnavailableStatus :")
    assert "REQ-AEBS-013" in requirement and "shall provide the status indication" in _flat(requirement)
    for name, (kind, *_rest) in PHASE1_CONCERNS.items():
        assert not re.search(r"(?i)\bcrash\w*\b", _concern_doc(name, kind)), \
            f"{name}: the split is no claim about a crash of the scene's app"


def test_the_phase_one_concerns_claim_no_result_and_name_no_unread_record():
    names = set(re.findall(r"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(?:IncrementGap|IncrementAssumption|InScopeItem|"
                           r"OutOfScopeItem)\b", _code()))
    for name, (kind, *_rest) in PHASE1_CONCERNS.items():
        doc = _concern_doc(name, kind)
        named = set(re.findall(r"\b((?:gap|asm)[A-Z]\w+|\w+InScope|\w+OutOfScope)\b", doc))
        assert named <= names, f"{name} names a record the framing does not declare: {sorted(named - names)}"
        assert not PAST_BEHAVIOR.findall(doc) and not APPROVAL.findall(doc), name
        assert not re.search(r"\b\d+(?:\.\d+)?\s*(?:s|ms|m|km/h|m/s|Hz)\b", doc), \
            f"{name}: a criterion value is phase 5's"
        assert not re.search(r"\bmust\b", doc), f"{name}: a concern states a need, not an obligation"


def _words(name: str) -> str:
    """The words of a CamelCase name, in lower case."""
    return " ".join(re.findall(r"[A-Z][a-z]*", name)).lower()


def _definition_and_holders(name: str) -> str:
    """'Definition; holders.' of a Phase 1 concern, read from its typing and its stakeholder lines in the model.

    Hyphens are spaces here: the guide may write a compound such as product-line with a hyphen.
    """
    code = _code()
    kind = re.search(rf"\bconcern {name}\s*:\s*(\w+)\s*\{{", code).group(1)
    roles = re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", braced_body(code, f"concern {name} : {kind}"))
    definition = _words(kind.removesuffix("Concern")).capitalize()
    return f"{definition}; " + " and ".join(_words(role) + "s" for role in roles) + "."


def test_the_guide_lists_the_phase_one_concerns_with_their_holders():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## What the increment judges") < guide.index("## Concerns (Phase 1)") \
        < guide.index("## What the framing already records as open")
    section = guide.split("## Concerns (Phase 1)", 1)[1].split("\n## ", 1)[0]
    bullets = re.findall(r"(?ms)^- \*\*([^*]+):\*\* `(\w+)`\.\s+(.*?)(?=^- \*\*|\n\n)", section)
    assert len(re.findall(r"(?m)^- ", section)) == len(bullets), "every bullet has a label and names its concern"
    model_order = re.findall(r"\bconcern\s+(\w+)\s*:", _code())
    assert model_order == ["hmiDisplayBoundary", *PHASE1_CONCERNS], "the model declares the concerns in this order"
    assert [name for _label, name, _body in bullets] == model_order[1:], \
        "one bullet for each Phase 1 concern, in the model's order"
    for label, name, body in bullets:
        expected_label, kept = GUIDE_CONCERNS[name]
        assert label == expected_label, (name, label)
        kind_and_holders = _definition_and_holders(name)
        assert kind_and_holders in _flat(body).replace("-", " "), (name, kind_and_holders)
        for sentence in kept:
            assert sentence in _flat(body), (name, sentence)
        # the bullet names each view that answers the concern and its phase, as the model's doc does, and every
        # answer sentence it holds has that form
        answers = set()
        for sentence in ANSWER_SENTENCE.findall(_flat(body)):
            strict = re.fullmatch(r"\s*Answered by the ([^.]*?) (?:of|in) Phase (\d+)\.", sentence)
            assert strict and strict.group(1) in VIEW_PHRASES, (name, sentence.strip())
            answers.add((VIEW_PHRASES[strict.group(1)], int(strict.group(2))))
        assert answers == {(viewpoint, phase) for phase, viewpoint in PHASE1_CONCERNS[name][5]}, (name, answers)
    outage = _flat(next(body for _label, name, body in bullets if name == "hmiAndroidOutageConcern"))
    assert not re.search(r"\bAndroid\b|\bIVI VM\b|\bapp\b", outage), \
        "the outage bullet states its trigger without naming a platform, as the model's doc does"
    flat = _flat(section)
    assert not re.search(r"(?i)\bcrash\w*\b|\bmust\b", flat)
    for phrase in ("held by the parties whose interest it states.",
                   "The driver, a vehicle occupant, holds the operational concern beside the engineering roles.",
                   "its text names the view of a later phase that answers it, save the product-line question: Phase 3 "
                   "records no characteristic and has no view.",
                   "The framing viewpoint frames all nine, and a view of a later phase that answers a concern "
                   "frames it as well.",
                   "They do not judge whether the stakeholder, risk and viewpoint coverage is adequate; review does."):
        assert phrase in flat, phrase


def test_each_phase_one_concern_is_answered_by_a_view_of_its_phase_in_its_domain():
    # The views that answer a concern are views the method lists for their phase, in the SAF domain of the
    # concern's definition: rule 15's domain advisory reads that property once the views exist. The product-line
    # concern and its view are the method's own, outside the SAF grid.
    listed = _canonical_list()
    domains = _domains(SAF_FILE.read_text(encoding="utf-8"))
    assert {name for name, spec in PHASE1_CONCERNS.items() if not spec[5]} == set(NO_LATER_VIEW), \
        "only the product-line concern names no view of a later phase"
    for name, fact in NO_LATER_VIEW.items():
        kind = PHASE1_CONCERNS[name][0]
        assert fact in _concern_doc(name, kind), f"{name} states why no view of a later phase answers it"
        assert not ANSWER_SENTENCE.search(_concern_doc(name, kind)), f"{name} claims an answering view"
        assert re.search(rf"\bframe\s+{name}\s*;", braced_body(_code(), "view hmiDisplayFramingView")), \
            f"{name}: the framing view frames it"
    # the Phase 1 note of the model says the same
    assert ("names the view of a later phase that answers it, save the product-line question, for which phase 3 "
            "has no view;") in _prose(_raw())
    assert "classification view of phase 3" not in _prose(_raw()).lower()
    for name, (kind, _items, _part, _holders, _sentences, answers) in PHASE1_CONCERNS.items():
        if name in NO_LATER_VIEW:
            continue
        assert answers, f"{name} names no view that answers it"
        for phase, viewpoint in answers:
            assert viewpoint in listed[phase], f"{name}: {viewpoint} is not a view the method lists for phase {phase}"
            assert domains.get(viewpoint) == domains.get(kind), \
                f"{name}: {kind} is in the {domains.get(kind)} domain, {viewpoint} in {domains.get(viewpoint)}"
            assert (domains.get(kind) is None) == (kind == "ProductLineCapabilityClassificationConcern"), name
