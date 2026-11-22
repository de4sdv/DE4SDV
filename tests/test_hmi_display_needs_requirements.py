"""Content pins for the HMI display stakeholder needs (INC-HMI-001, phase 4), not semantic validation.

Each need is held by the parties the HMI display serves, leads its source with the phase 1 concern it derives
from, and has one planned stakeholder review on the phase 2 use cases it covers. The roles that check the answer
stay on the reviews. Seven phase 1 concerns are reviewer questions: a need's source names each, its review asks
the concern's question, led by the concern's own roles, and its rationale hands the concern's requirements to
phase 5. Each reviewed text is pinned whole, and the rule guards stay beside the pins: no digit outside the
identifiers, no number with a unit, no clause number, no positive safety or timing claim, no anti-cheating
clause, no drawing, no renderer in a statement, and the simulator and stale content named only in the listed
sentences. The guards match the words they list; a claim in other words is for review. The tests read the model
text; they do not parse SysML.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import braced_body, charter_package_files, strip_comments

ROOT = Path(__file__).resolve().parents[1]
HMI = ROOT / "textual-notation-of-model/packages/features/hmi"
FRAMING = HMI / "hmi_display_framing.sysml"
CONTEXT = HMI / "hmi_display_operational_context.sysml"
MODEL = HMI / "hmi_display_needs_requirements.sysml"
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_HmiDisplayNeedsRequirements"
CONTEXT_PACKAGE = "DE4SDV_HmiDisplayOperationalContext"
SYSTEM_OF_INTEREST = "DE4SDV_HmiDisplayFraming::hmiDisplaySystem"
INCREMENT = "INC-HMI-001"


#: need -> (short name, the roles that hold it, the phase 1 concern that leads its source)
NEEDS = {
    "needPerceivedSceneOnTheDisplay": (
        "NEED-HMI-001", {"VehicleOccupant"}, "hmiDriverSupervisionConcern"),
    "needVehicleSpeedOnTheDisplay": (
        "NEED-HMI-002", {"VehicleOccupant"}, "hmiDriverSupervisionConcern"),
    "needCollisionWarningOnRequest": (
        "NEED-HMI-003", {"VehicleOccupant"}, "hmiDriverSupervisionConcern"),
    "needSpeedAndWarningThroughOutages": (
        "NEED-HMI-004", {"VehicleOccupant"}, "hmiDriverSupervisionConcern"),
    "needNoElementShownAsCurrentWhenItIsNot": (
        "NEED-HMI-005", {"VehicleOccupant"}, "hmiDriverSupervisionConcern"),
    "needRunsIdentifyTheDisplay": (
        "NEED-HMI-006", {"VerificationEngineer", "ProductLineEngineer"}, "hmiDisplayVerdictConcern"),
}

#: the phase 2 use cases, by the scenarios they show
WARNING_SCENARIOS = ("showWarningInTheWarningScenarios", "showNoWarningInTheNoReactionScenarios")
OUTAGE_SCENARIOS = ("keepSpeedAndWarningWhenTheSceneAppIsOut", "showSpeedAndWarningWhileAndroidBoots",
                    "keepSpeedAndWarningWhileAndroidHangs", "keepSpeedAndWarningThroughAndroidRestart")
MISSING_INPUT_SCENARIOS = ("showWarningUnavailableWhenTheRequestStops",)

#: need -> (the short name of its planned review, the phase 2 use cases the review depends on: each scenario its
#: need's source names)
VALIDATION = {
    "needPerceivedSceneOnTheDisplay": ("SC-HMI-008", WARNING_SCENARIOS),
    "needVehicleSpeedOnTheDisplay": ("SC-HMI-009", WARNING_SCENARIOS),
    "needCollisionWarningOnRequest": ("SC-HMI-010", WARNING_SCENARIOS),
    "needSpeedAndWarningThroughOutages": ("SC-HMI-011", OUTAGE_SCENARIOS),
    "needNoElementShownAsCurrentWhenItIsNot": ("SC-HMI-012", (*OUTAGE_SCENARIOS, *MISSING_INPUT_SCENARIOS)),
    "needRunsIdentifyTheDisplay": ("SC-HMI-013", (*WARNING_SCENARIOS, *OUTAGE_SCENARIOS, *MISSING_INPUT_SCENARIOS)),
}
#: phase 2 use case -> its scenario identity
SCENARIOS = {
    "showWarningInTheWarningScenarios": "SC-HMI-001",
    "showNoWarningInTheNoReactionScenarios": "SC-HMI-002",
    "keepSpeedAndWarningWhenTheSceneAppIsOut": "SC-HMI-003",
    "showSpeedAndWarningWhileAndroidBoots": "SC-HMI-004",
    "keepSpeedAndWarningWhileAndroidHangs": "SC-HMI-005",
    "keepSpeedAndWarningThroughAndroidRestart": "SC-HMI-006",
    "showWarningUnavailableWhenTheRequestStops": "SC-HMI-007",
}

#: reviewer-question concerns: their roles check the answer rather than use it, so they lead no need; a need's
#: source names them and its planned review asks their question, carried out by their roles
#: concern -> (the need whose source names it, the phrase of its review that names the asking roles, the question)
REVIEWED_CONCERNS = {
    "hmiDisplayInputsConcern": (
        "needPerceivedSceneOnTheDisplay",
        "Can systems engineers and safety experts tell",
        "which items cross into the HMI display from outside its boundary, the lane of the driver-assistance system, "
        "the path it fits to that lane, the objects it detects with their level relative to its path, the closest "
        "object in its path with the distance and the speed that its fusion gives, the vehicle speed that the system "
        "is given and its warning request, and whether each reaches the display as its source gives it?"),
    "hmiContentVarianceConcern": (
        "needPerceivedSceneOnTheDisplay",
        "And can product-line engineers tell",
        "which content of the HMI display is common to the member products and which derives from a member's driving "
        "application?"),
    "hmiWarningSequenceConcern": (
        "needCollisionWarningOnRequest",
        "And can safety experts and systems engineers follow",
        "the sequence from the warning request of the driver-assistance system to the collision warning on the "
        "display and to its sound, and the time of each step within the time that the driver-assistance increment "
        "allots from the request to each mode, independent of the elements that realize it?"),
    "hmiAndroidOutageConcern": (
        "needSpeedAndWarningThroughOutages",
        "Can safety experts and systems engineers follow",
        "the sequence from each outage of the drawing of the scene and of the environment that hosts it, the drawing "
        "hanging or ending and its host hanging, booting or restarting, to its detection and to what the display "
        "shows then, independent of the elements that realize it?"),
    "hmiRendererAllocationConcern": (
        "needSpeedAndWarningThroughOutages",
        "Can product-line engineers and safety experts tell",
        "which renderer realizes the drawing of each element of the HMI display, and whether the split that the owner "
        "decided on 2026-11-17, the high availability renderer in an SDV Media VM for the speed, the collision "
        "warning and its sound and an app in the IVI VM for the scene, keeps what the driver sees while Android in "
        "the IVI VM hangs, boots or restarts?"),
    "hmiRendererPathConcern": (
        "needSpeedAndWarningThroughOutages",
        "And can system architects and systems engineers tell",
        "which elements exchange each input of the HMI display on its way from the SDV Core VM to the high "
        "availability renderer in the SDV Media VM and to the app in the IVI VM that draws the scene, by which "
        "exchange that app tells the renderer that Android is alive, and by which boundary interface each input "
        "enters the display?"),
    "hmiContentCurrencyConcern": (
        "needNoElementShownAsCurrentWhenItIsNot",
        "can safety experts and verification engineers tell",
        "the states that each element of the HMI display can be in, current, late or missing, and the state in which "
        "the collision warning is unavailable, what the display shows in each, and whether the display showed any "
        "element as current when it was not, or the warning as available when it could not be given?"),
}
#: a stakeholder definition -> how a review question or the guide names its members
ROLE_WORDS = {
    "SafetyExpert": "safety experts", "ProductLineEngineer": "product-line engineers",
    "SystemsEngineer": "systems engineers", "SystemArchitect": "system architects",
    "VerificationEngineer": "verification engineers", "VehicleOccupant": "vehicle occupants",
    "RoadUser": "road users",
}
#: every role word a review question could name
ALL_ROLE_WORDS = (*ROLE_WORDS.values(), "compliance engineers", "software developers", "maintainers",
                  "open-source reviewers")
#: plan -> the roles that carry out the review: the roles that check the answer
REVIEWERS = {
    "SC-HMI-008": {"verification engineers", "systems engineers", "safety experts", "product-line engineers"},
    "SC-HMI-009": {"verification engineers", "systems engineers"},
    "SC-HMI-010": {"verification engineers", "safety experts", "systems engineers"},
    "SC-HMI-011": {"verification engineers", "safety experts", "systems engineers", "product-line engineers",
                   "system architects"},
    "SC-HMI-012": {"safety experts", "verification engineers"},
    "SC-HMI-013": {"verification engineers", "product-line engineers"},
}
#: the parties who hold the operational needs never check them
NOT_CHECKERS = {"vehicle occupants", "road users"}

#: the phase 1 concerns this phase reads: every non-boundary concern of the framing
PHASE1_CONCERNS = {
    "hmiDriverSupervisionConcern", "hmiDisplayInputsConcern", "hmiContentVarianceConcern", "hmiWarningSequenceConcern",
    "hmiContentCurrencyConcern", "hmiAndroidOutageConcern", "hmiRendererAllocationConcern", "hmiRendererPathConcern",
    "hmiDisplayVerdictConcern",
}

#: wording the charter excludes from a need: approval, admission, a member product, on-road use, a result
EXCLUDED = re.compile(r"(?i)\b(?:certif\w*|homologat\w*|complian\w*|complies|approv\w*|type.approv\w*|admi(?:t|ss)\w*|"
                      r"on-road|member products?|passe[sd]|fail(?:s|ed))\b")
#: an anti-cheating clause belongs to a planned review's question, not to a need
ANTI_CHEATING = re.compile(r"(?i)\b(?:autopilot|replay\w*|overlay\w*|recording|acts? instead|stands? in)\b")
#: a value with a unit is phase 5's, derived with its provenance; a need states none
NUMBER_WITH_UNIT = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:ms|s|m|km/h|m/s|m/s2|m/s²|g|Hz|%|px|mm|°)(?![\w/])")
#: the digits a need's statement or rationale may carry: phase numbers, System 2, identifiers and decision dates
ALLOWED_DIGITS = re.compile(r"\b(?:[Pp]hases? \d+(?: to \d+)?|System 2|[A-Z]+-[A-Z]+-\d{3}|\d{4}-\d{2}-\d{2})\b")
#: a number in words with a unit: a limit in disguise
NUMBER_WORDS = re.compile(r"(?i)\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|half)\s+(?:a\s+)?"
                          r"(?:seconds?|milliseconds?|metres?|meters?|kilometres?|kilometers?|km/h)\b")
#: a clause or section number of an external source: the repository names its source records only
CLAUSE_NUMBER = re.compile(r"(?i)\b(?:annex|paragraph|clause|appendix|section)\s+\d|§\s*\d|\b\d+(?:\.\d+){2,}\b")
#: a positive safety claim; "no safety claim" is the non-claim
SAFETY_CLAIM = re.compile(r"(?i)(?<!no )\bsaf(?:e|ety|ely)\b")
#: a positive timing claim; "no timing claim" is the non-claim
TIMING_CLAIM = re.compile(r"(?i)(?<!no )\b(?:timing|latency|jitter|in time|real[- ]time|deadline)\b")
#: a drawing: the needs hold whichever drawing phase 8 picks, so no need text and no review names one
DRAWING = re.compile(r"(?i)\b(?:camera\w*|pictures?|images?|video\w*|backdrops?|reality|bird\w*|top-down|"
                     r"colou?rs?|icons?|symbols?|chimes?)\b")
#: content that hmiFurtherContentOutOfScope leaves out unless a need asks for it: no need asks for it
FURTHER_CONTENT = re.compile(r"(?i)\b(?:gears?|set speed|speed limits?|telltales?)\b")
#: a renderer in a statement: which renderer draws what is phase 8's
RENDERER = re.compile(r"(?i)high availability renderer|\bHAR\b|SDV Media")
#: the simulator, its record and the truth of the scene (hmiSimulatorTruthOutOfScope)
TRUTH_TERMS = re.compile(r"(?i)\b(?:simulat\w*|carla|ground[- ]truth|truth)\b")
#: stale content and its synonyms (hmiStaleContentInScope)
CURRENCY_TERMS = re.compile(r"(?i)\b(?:current\w*|live\w*|last frames?|stale\w*|froz\w*|freez\w*|up[- ]to[- ]date)\b")

#: the purpose of the scene on the display, a purpose and no claim of how a driver supervises
SCENE_PURPOSE = (
    "The display shows the driver what the driver-assistance system perceives, right or wrong, so that the driver can "
    "supervise the system with it, and it shows the scene that the system gives and no other.")

#: the purpose of the warning and of no warning without a request, with no claim on how a driver reads it
WARNING_PURPOSE = (
    "The warning lets the driver act on an imminent collision, and the display gives none without a request, so that "
    "each collision warning that the driver gets stands for a request of the driver-assistance system.")

#: the purpose of no element shown as current when it is not
CURRENCY_PURPOSE = (
    "The display shows no element as current when it is not, so that the driver supervises the driver-assistance "
    "system on what it perceives now, and it shows when the warning is unavailable, so that the driver can tell a "
    "warning that cannot come from one that is not due.")

#: the sentence that hands the states of each element to phase 5
CURRENCY_STATES = (
    "Phase 5 also derives from this need the requirements on the states of each element, current, late or missing, "
    "and on what the display shows in each: its source names its concern, and SC-HMI-012 asks its question.")

#: the one sentence of a need that names the simulation
SIMULATED_ONLY = (
    "A verdict holds for the simulated configuration only (asmHmiSimulationStandsIn).")

#: the one sentence of a review that names the simulator: no object that the system did not give
SCENE_NO_ESTIMATE = (
    "While the warning scenarios and the no-reaction scenarios of the driver-assistance increment run on the display "
    "(SC-HMI-001 and SC-HMI-002), can verification engineers and systems engineers confirm whether the lane, the "
    "path, the objects with their level and the closest object in the path with its distance and its speed that the "
    "display shows are those that the driver-assistance system gave, and whether the display showed any object that "
    "the system did not give, from the simulator's record of the scene or from an estimate of the display's own?")

#: the review sentence on the states of each element
CURRENCY_REVIEW = (
    "While the app that draws the scene is out, while Android in the IVI VM boots, hangs and restarts, and while the "
    "warning request stops reaching the display (SC-HMI-003 to SC-HMI-007), can safety experts and verification "
    "engineers tell the states that each element of the HMI display can be in, current, late or missing, and the "
    "state in which the collision warning is unavailable, what the display shows in each, and whether the display "
    "showed any element as current when it was not, or the warning as available when it could not be given?")

#: the sentences that may name the simulator: each keeps the simulator's record off the display or binds a
#: verdict to the simulated configuration
TRUTH_SENTENCES = (SCENE_NO_ESTIMATE, SIMULATED_ONLY)

#: the statement that no element is shown as current when it is not
CURRENCY_STATEMENT = (
    "Vehicle occupants need the HMI display to show the driver no element as current when it is not, and to show the "
    "driver when the collision warning is unavailable.")

#: the sentences that may name current, live or stale content: each shows no late element as current
CURRENCY_SENTENCES = (CURRENCY_STATEMENT, CURRENCY_PURPOSE, CURRENCY_STATES, CURRENCY_REVIEW)

# The reviewed texts, pinned whole (whitespace flattened). A change to a need, a review or a contract comment is a
# change of the reviewed content: update the pin in the same commit, on purpose.

#: need -> its statement
STATEMENTS = {
    "needPerceivedSceneOnTheDisplay": (
        "Vehicle occupants need the HMI display to show the driver the scene as the driver-assistance system gives it "
        "from its own perception: its lane, the path it fits to that lane, the objects it detects with their level "
        "relative to that path, and the closest object in its path with the distance and the speed that its fusion "
        "gives."),
    "needVehicleSpeedOnTheDisplay": (
        "Vehicle occupants need the HMI display to show the driver the vehicle speed that the driver-assistance "
        "system is given."),
    "needCollisionWarningOnRequest": (
        "Vehicle occupants need the HMI display to give the driver the collision warning on the display and as a "
        "sound when the warning request of the driver-assistance system asks for it, and no collision warning without "
        "such a request."),
    "needSpeedAndWarningThroughOutages": (
        "Vehicle occupants need the HMI display to show the driver the vehicle speed and to give the collision "
        "warning when it is requested, or to show that the warning is unavailable, also while the app that draws the "
        "scene hangs or ends and while Android in the IVI VM hangs, boots or restarts."),
    "needNoElementShownAsCurrentWhenItIsNot": CURRENCY_STATEMENT,
    "needRunsIdentifyTheDisplay": (
        "Verification engineers and product-line engineers need each run of the HMI display to identify the build and "
        "the configuration of the display that ran, so that each verdict is bound to what ran."),
}
#: need -> its source
SOURCES = {
    "needPerceivedSceneOnTheDisplay": (
        "INC-HMI-001 hmiDriverSupervisionConcern, hmiDisplayInputsConcern, hmiContentVarianceConcern, scope item "
        "hmiSceneInScope, gaps gapHmiSceneOutput and gapHmiSceneContent, scenarios SC-HMI-001 and SC-HMI-002"),
    "needVehicleSpeedOnTheDisplay": (
        "INC-HMI-001 hmiDriverSupervisionConcern, scope item hmiSpeedInScope, scenarios SC-HMI-001 and SC-HMI-002"),
    "needCollisionWarningOnRequest": (
        "INC-HMI-001 hmiDriverSupervisionConcern, hmiWarningSequenceConcern, scope item hmiCollisionWarningInScope, "
        "gaps gapHmiRendererCollisionWarning and gapHmiWarningPresentation, scenarios SC-HMI-001 and SC-HMI-002"),
    "needSpeedAndWarningThroughOutages": (
        "INC-HMI-001 hmiDriverSupervisionConcern, hmiAndroidOutageConcern, hmiRendererAllocationConcern, "
        "hmiRendererPathConcern, scope items hmiAndroidOutageInScope and hmiRendererSplitInScope, gaps "
        "gapHmiRendererIntegration and gapHmiMemberGuestLayout, scenarios SC-HMI-003 to SC-HMI-006"),
    "needNoElementShownAsCurrentWhenItIsNot": (
        "INC-HMI-001 hmiDriverSupervisionConcern, hmiContentCurrencyConcern, scope item hmiStaleContentInScope, gap "
        "gapHmiWarningAvailability, scenarios SC-HMI-003 to SC-HMI-007"),
    "needRunsIdentifyTheDisplay": (
        "INC-HMI-001 hmiDisplayVerdictConcern, scope item hmiVerdictEvidenceInScope, assumption "
        "asmHmiSimulationStandsIn, scenarios SC-HMI-001 to SC-HMI-007"),
}

#: need -> its rationale
RATIONALES = {
    "needPerceivedSceneOnTheDisplay": " ".join((
        SCENE_PURPOSE,
        ("At the inspected revision the system gives no such output (gapHmiSceneOutput), and what the scene carries "
         "bounds what the display can show of it (gapHmiSceneContent). The need states what the driver expects to "
         "see, not how a driver reads it, and carries no safety claim. Phase 5 derives its requirements. Phase 5 also "
         "derives from this need the requirements on the items that cross into the display, and states which "
         "requirements on the content of the display are core and which follow the driving application: its source "
         "names their concerns, and SC-HMI-008 asks their questions."))),
    "needVehicleSpeedOnTheDisplay": (
        "The display shows the driver the speed that the driver-assistance system is given, so that the driver can "
        "supervise the system with the same speed that the system acts on. The vehicle gives it, and which element "
        "brings it to the display is for the architecture phases (vehicleSpeedSourceComment). The need carries no "
        "safety claim. Phase 5 derives its requirements. NEED-HMI-004 adds that the speed stays on the display "
        "through the outages of the drawing of the scene and of Android in the IVI VM."),
    "needCollisionWarningOnRequest": " ".join((
        WARNING_PURPOSE,
        ("The warning request is the driver-assistance increment's, taken as that increment defines it, and whether a "
         "warning is due is the decision of the driver-assistance system, which that increment judges. "
         "NEED-DRIVING-010 of that increment needs the system to give the request at its boundary; this need adds "
         "that the display gives the warning from it. The need rests on REQ-AEBS-002, the collision warning that the "
         "product line asks for. The vehicle data of the renderer holds no collision warning yet "
         "(gapHmiRendererCollisionWarning). The need carries no safety claim. Phase 5 derives its requirements and "
         "states when each mode is due within the time that the driver-assistance increment allots from the request "
         "to each mode (gapHmiWarningPresentation). Phase 5 also derives from this need the requirements on the "
         "sequence from the request to the warning on the display and to its sound: its source names its concern, and "
         "SC-HMI-010 asks its question."))),
    "needSpeedAndWarningThroughOutages": (
        "The driver keeps driving while the drawing of the scene or Android in the IVI VM is out, and still needs the "
        "speed and the warning then, or to know that the warning cannot come. NEED-HMI-002 and NEED-HMI-003 state the "
        "speed and the warning; this need adds that they stay through each outage. It rests on N-AEBS-008, the need "
        "of the product line that the availability of the AEBS be apparent, and on the status indication of "
        "REQ-AEBS-013. Each outage is an event inside the boundary of the display, whose detection phases 6 to 8 "
        "decide. The need names no renderer and carries no safety claim. Phase 5 derives its requirements and their "
        "limits. Phase 5 also derives from this need the requirements on the sequence from each outage to what the "
        "display shows, on which renderer draws each element and on the paths of the inputs to the renderers: its "
        "source names their concerns, and SC-HMI-011 asks their questions."),
    "needNoElementShownAsCurrentWhenItIsNot": " ".join((
        CURRENCY_PURPOSE,
        ("From which age an element counts as late is for Phase 5 to state, and whether the display learns that the "
         "warning is unavailable from the age of its inputs or from a signal of its own is open "
         "(gapHmiWarningAvailability). The second part rests on N-AEBS-008 and REQ-AEBS-013. NEED-HMI-004 states what "
         "the display keeps through the outages in the IVI VM; this need holds for every element at any time, also "
         "when an input of the display is late or missing. The need carries no safety claim. Phase 5 derives its "
         "requirements and their limits."),
        CURRENCY_STATES)),
    "needRunsIdentifyTheDisplay": " ".join((
        ("The lifecycle decision rests on a pass or a fail for each requirement and scenario, and a verdict holds "
         "only for the display that ran. The configuration of the display is every setting that it reads at its "
         "start. The candidate revision is bound by the run of the driver-assistance system (NEED-DRIVING-011 of the "
         "driver-assistance increment), and the record of what that system gives, the captures and the evaluators "
         "belong to System 2 and are bound there, so this need covers only what the display itself runs."),
        SIMULATED_ONLY)),
}


def _ask(concern: str) -> str:
    """The question of a reviewer-question concern as its review asks it: the asking roles, then the question."""
    _need, asked_by, question = REVIEWED_CONCERNS[concern]
    return f"{asked_by} {question}"


#: plan -> its review question, pinned whole
PLAN_DOCS = {
    "SC-HMI-008": " ".join((
        "For NEED-HMI-001, a planned stakeholder review.", SCENE_NO_ESTIMATE, _ask("hmiDisplayInputsConcern"),
        _ask("hmiContentVarianceConcern"))),
    "SC-HMI-009": (
        "For NEED-HMI-002, a planned stakeholder review. While the warning scenarios and the no-reaction scenarios of "
        "the driver-assistance increment run on the display (SC-HMI-001 and SC-HMI-002), can verification engineers "
        "and systems engineers confirm whether the speed that the display shows is the vehicle speed that the "
        "driver-assistance system was given, and whether any other source of the speed reached the display?"),
    "SC-HMI-010": " ".join((
        ("For NEED-HMI-003, a planned stakeholder review. While the warning scenarios and the no-reaction scenarios "
         "of the driver-assistance increment run on the display (SC-HMI-001 and SC-HMI-002), can verification "
         "engineers and safety experts confirm whether the display gave the collision warning on the display and as a "
         "sound for each warning request of the driver-assistance system, whether it gave one without a request, and "
         "when each mode began relative to the request, with no recording or overlay in place of either mode?"),
        _ask("hmiWarningSequenceConcern"))),
    "SC-HMI-011": " ".join((
        ("For NEED-HMI-004, a planned stakeholder review. While the app that draws the scene is out and while Android "
         "in the IVI VM boots, hangs and restarts (SC-HMI-003 to SC-HMI-006), can verification engineers and safety "
         "experts confirm whether the driver saw the vehicle speed throughout and got the collision warning for each "
         "warning request, or saw that the warning was unavailable?"),
        _ask("hmiAndroidOutageConcern"), _ask("hmiRendererAllocationConcern"), _ask("hmiRendererPathConcern"))),
    "SC-HMI-012": "For NEED-HMI-005, a planned stakeholder review. " + CURRENCY_REVIEW,
    "SC-HMI-013": (
        "For NEED-HMI-006, a planned stakeholder review. While the seven scenarios run (SC-HMI-001 to SC-HMI-007), "
        "can verification engineers and product-line engineers tell from each run which build and which configuration "
        "of the HMI display ran and which candidate revision the run of the driver-assistance system identifies, "
        "whether each verdict is bound to them, and whether a display with a changed build or setting identifies "
        "itself as a different one?"),
}
#: comment -> (the need it is about, its text): the input contracts kept for phase 5, pinned whole
CONTRACTS = {
    "perceivedSceneContract": ("needPerceivedSceneOnTheDisplay", (
        "At the inspected revision the driver-assistance system builds a scene only inside its own visualization. The "
        "bridge of its panel builds it from the path that the lateral fusion fits, the offset and the heading of the "
        "vehicle in its lane, the lane points of AutoSteer placed on the road through the homography that the system "
        "loads, the detections of AutoSpeed as boxes with a score and a class, which is a level relative to the path, "
        "and the validity and the distance of the closest object, and it does not read the plan. The scene of the "
        "panel carries no speed of the closest object and no time, and the inference result carries a frame identity "
        "and no capture time. The fusion gives the closest object a distance and a speed, and its comment reads a "
        "negative speed as approaching, so whether the speed that its fusion gives is the speed of the object or the "
        "speed at which it closes is open. The fusion reads the first level as the same lane and the second as the "
        "adjacent lane. Where AutoDrive flags an object in the path and AutoSpeed gives no box for it, the "
        "visualization draws a mark for the closest object with a distance that it derives from the network output "
        "itself; the planner does not use it, it is an estimate of the display's own, and NEED-HMI-001 leaves it out "
        "by its words. Phase 5 states as requirements what the display takes from the scene.")),
    "warningRequestContract": ("needCollisionWarningOnRequest", (
        "The warning request is the output that the driver-assistance increment realizes from the warnings of each "
        "plan: it asks for the collision warning when the plan holds the forward-collision warning or the emergency "
        "braking, and it carries the capture time of the frame that the plan came from. One plan holds at most one of "
        "the two. The request does not tell them apart, and the system's own visualization does. Phase 5 states as "
        "requirements what the display takes from it.")),
}
#: the count sentence of the header
HEADER_COUNT = (
    "Seven concerns are reviewer questions: a need's source names them and its review checks them.")

#: the header paragraph that gives the reason of each reviewer question, pinned whole
HEADER_REASONS = (
    "Each of these seven concerns asks to see the answer that the view of a later phase gives, and the HMI display "
    "gives its roles nothing that they use in their own work: hmiDisplayInputsConcern, held by systems engineers and "
    "safety experts, and hmiContentVarianceConcern, held by product-line engineers, ask about the items that cross "
    "into the display and about its common content, and NEED-HMI-001 names them; hmiWarningSequenceConcern, held by "
    "safety experts and systems engineers, asks about the sequence of the warning, and NEED-HMI-003 names it; "
    "hmiAndroidOutageConcern, held by safety experts and systems engineers, hmiRendererAllocationConcern, held by "
    "product-line engineers and safety experts, and hmiRendererPathConcern, held by system architects and systems "
    "engineers, ask about the outages, the renderers and their paths, and NEED-HMI-004 names them; "
    "hmiContentCurrencyConcern, held by safety experts and verification engineers, asks about the states of each "
    "element, and NEED-HMI-005 names it. The stakeholder needs of the driver-assistance increment and of the E/E "
    "architecture increment keep such concerns as reviewer questions in the same way.")

#: the header paragraph on the drawing and on the content that no need asks for
HEADER_DRAWING = (
    "The needs name no drawing: how the app in the IVI VM draws the scene is a choice of phase 8, and the visual "
    "design stays out of scope (hmiHumanFactorsOutOfScope). No need asks for gear, set speed, speed limit or another "
    "telltale (hmiFurtherContentOutOfScope).")

#: the non-claim sentence of the header
HEADER_NON_CLAIM = (
    "No safety, timing, on-road or production-readiness claim is made, and no member product is claimed.")

#: the doc of the concern that the two tables frame
NEEDS_CONCERN_DOC = (
    "Systems engineers and product-line engineers need the stakeholder needs of the HMI display with their statements "
    "and sources, and the planned stakeholder review of each, to judge whether the needs cover the concerns of phase "
    "1.")

#: the guide's link to the model
GUIDE_LINK = (
    "../../textual-notation-of-model/packages/features/hmi/hmi_display_needs_requirements.sysml")

#: need -> the guide's Phase 4 bullet, pinned whole (whitespace flattened)
GUIDE_BULLETS = {
    "NEED-HMI-001": (
        "the display shows the driver the scene as the driver-assistance system gives it from its own perception. "
        "Vehicle occupants. Reviewed by `SC-HMI-008` on `SC-HMI-001` and `SC-HMI-002`."),
    "NEED-HMI-002": (
        "the display shows the driver the vehicle speed that the driver-assistance system is given. Vehicle "
        "occupants. Reviewed by `SC-HMI-009` on `SC-HMI-001` and `SC-HMI-002`."),
    "NEED-HMI-003": (
        "the display gives the collision warning on the display and as a sound when the warning request asks for it, "
        "and none without a request. Vehicle occupants. Reviewed by `SC-HMI-010` on `SC-HMI-001` and `SC-HMI-002`."),
    "NEED-HMI-004": (
        "the speed and the warning, or the fact that the warning is unavailable, stay on the display while the app "
        "that draws the scene or Android in the IVI VM is out. Vehicle occupants. Reviewed by `SC-HMI-011` on "
        "`SC-HMI-003` to `SC-HMI-006`."),
    "NEED-HMI-005": (
        "the display shows no element as current when it is not, and shows when the collision warning is unavailable. "
        "Vehicle occupants. Reviewed by `SC-HMI-012` on `SC-HMI-003` to `SC-HMI-007`."),
    "NEED-HMI-006": (
        "each run identifies the build and the configuration of the display that ran. Verification engineers and "
        "product-line engineers, who use the run identity in their own work. Reviewed by `SC-HMI-013` on all seven "
        "scenarios."),
}

#: the paragraphs of the guide's Phase 4 section besides its bullets, in order, pinned whole
GUIDE_PARAGRAPHS = (
    "The [stakeholder needs](" + GUIDE_LINK + ") "
    "say what the parties of the Phase 1 concerns expect of the HMI display. Each need is held by the parties it "
    "serves and leads its source with the concern it comes from. Each has one planned stakeholder review on the Phase "
    "2 scenarios it covers, carried out by the roles that check the answer.",
    "Seven concerns get no need of their own: the items that cross into the display, its common content, the "
    "warning's sequence, the outages of the scene's drawing, which renderer draws what, the paths to the renderers, "
    "and the late and missing content. Their roles check the answer rather than use it, as in the stakeholder needs "
    "of the driver-assistance and the E/E architecture increments, so each is a question for a planned review: "
    "`NEED-HMI-001` names the first two in its source and `SC-HMI-008` asks them, `NEED-HMI-003` names the third and "
    "`SC-HMI-010` asks it, `NEED-HMI-004` names the next three and `SC-HMI-011` asks them, and `NEED-HMI-005` names "
    "the last and `SC-HMI-012` asks it.",
    "No need states a number or names a drawing: Phase 5 derives the requirements and their limits, how the app in "
    "the IVI VM draws the scene is a choice of Phase 8, and no need asks for gear, set speed, speed limit or another "
    "telltale. Comments about `NEED-HMI-001` and `NEED-HMI-003` keep for Phase 5 what the driver-assistance system "
    "gives at the pinned revision: what its scene carries, and what its warning request asks for and carries.",
    "`SC-DRIVING-018` of the driver-assistance increment watches the collision warning on the same runs as "
    "`SC-HMI-010` for another subject: its need, `NEED-DRIVING-010`, asks the candidate to give the warning request, "
    "and `NEED-HMI-003` asks the display to give the warning from it.",
    "`tests/test_hmi_display_needs_requirements.py` pins the needs, their holders and sources, the planned reviews "
    "and their scenarios, and the wording a need may not use. The Phase 4 gates check that each need has a statement, "
    "a stakeholder, a source, a rationale and a planned review. Review judges whether the needs are the right ones.",
)
#: need -> how the guide's bullet names its holders
GUIDE_HOLDERS = {
    "NEED-HMI-001": "Vehicle occupants.",
    "NEED-HMI-002": "Vehicle occupants.",
    "NEED-HMI-003": "Vehicle occupants.",
    "NEED-HMI-004": "Vehicle occupants.",
    "NEED-HMI-005": "Vehicle occupants.",
    "NEED-HMI-006": "Verification engineers and product-line engineers, who use the run identity in their own work.",
}
#: the guide's status line
STATUS = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification and "
    "Phase 4 stakeholder needs, proposal.**")

#: the guide's next obligation
NEXT_OBLIGATION = (
    "The next model obligation is **Phase 5**, the requirements.")



def _raw() -> str:
    assert MODEL.is_file(), "phase 4 of INC-HMI-001 needs a stakeholder needs model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _sentences(text: str) -> list[str]:
    return [sentence for sentence in re.split(r"(?<=[.?!])\s+", text) if sentence]


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
    return dict(re.findall(r"\bpart\s+<'(SC-HMI-\d{3})'>\s+(\w+)\s*:\s*ValidationPlanningScenario\b", _code()))


def _plan_doc(short: str) -> str:
    body = braced_body(_raw(), f"part <'{short}'> {_plans()[short]} : ValidationPlanningScenario")
    match = re.search(r"\bdoc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{short} has no doc"
    return _flat(match.group(1))


def _need_text(name: str) -> str:
    body = _need(name)
    return " ".join((_statement(body), _attribute(body, "source"), _attribute(body, "rationale")))


def _header() -> str:
    return _raw().split("\npackage ", 1)[0]


def _header_paragraphs() -> list[str]:
    return [_flat(part) for part in re.split(r"\n\s*\*\s*\n", _header())]


def _framing_holders(concern: str) -> set[str]:
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    return set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", braced_body(framing, f"concern {concern} :")))


def _scenarios_of(text: str) -> set[str]:
    """The phase 2 scenarios a text names: each identity, and each range "SC-HMI-00a to SC-HMI-00b" in full."""
    named = set(re.findall(r"SC-HMI-00[1-7]\b", text))
    for first, last in re.findall(r"SC-HMI-(\d{3}) to SC-HMI-(\d{3})\b", text):
        named.update(f"SC-HMI-{number:03d}" for number in range(int(first), int(last) + 1))
    return named


def _model_sentences() -> list[str]:
    """Every sentence of the model's prose: its comments and docs, and its string values."""
    raw = _raw()
    texts = [_flat(match.group(1)) for match in re.finditer(r"/\*(.*?)\*/", raw, re.S)]
    texts += [match.group(1) for match in re.finditer(r'=\s*"([^"]*)"', raw)]
    return [sentence for text in texts for sentence in _sentences(text)]


def _guide_section() -> str:
    guide = GUIDE.read_text(encoding="utf-8")
    return guide.split("## Stakeholder needs (Phase 4)", 1)[1].split("\n## ", 1)[0]


def test_the_package_declares_exactly_the_needs_of_phase_4_with_unique_short_names():
    code = _code()
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", code) == [PACKAGE], "one global package per file"
    declared = re.findall(r"\brequirement\s+<'([^']+)'>\s+(\w+)\s*:\s*StakeholderNeedCandidate\b", code)
    assert declared == [(short, name) for name, (short, _roles, _concern) in NEEDS.items()]
    others = [path.name for path in charter_package_files(FRAMING, "hmiDisplayCharter") if path != MODEL
              and re.search(r"<'NEED-HMI-\d{3}'>", path.read_text(encoding="utf-8"))]
    assert not others, f"the needs of the increment are declared only here: {others}"
    assert not re.search(r"\b(?:part|item|action|requirement|concern|viewpoint|view|use case|attribute|enum|port"
                         r"|connection|interface|state|constraint|calc|occurrence)\s+def\b", code), \
        "the slice declares no definition: method types come from the kernel"


def test_each_need_has_a_statement_its_holders_a_source_and_a_rationale():
    # The ElaborateNeeds gates: needHasStatement, needHasStakeholder, needHasSource and needHasRationale; the
    # subject has its own test.
    for name, (_short, roles, concern) in NEEDS.items():
        body = _need(name)
        assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", strip_comments(body))) == roles, name
        source = _attribute(body, "source")
        assert source.startswith(f"{INCREMENT} {concern},"), (name, source)
        assert _statement(body) == STATEMENTS[name], (name, "statement")
        assert source == SOURCES[name], (name, "source")
        assert _attribute(body, "rationale") == RATIONALES[name], (name, "rationale")


def test_the_subject_of_each_need_is_the_system_of_interest():
    # The advisory needSubjectIsSystemOfInterest: the charter's systemOfInterest, never the increment.
    for name in NEEDS:
        subjects = re.findall(r"\bsubject\s+\w+\s*:>\s*([\w:]+)\s*;", strip_comments(_need(name)))
        assert subjects == [SYSTEM_OF_INTEREST], (name, subjects)


def _declared_holders(name: str) -> set[str]:
    return set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", strip_comments(_need(name))))


def test_each_need_is_held_by_holders_of_its_first_source_concern():
    # The rule reads the model: each declared holder holds the need's first source concern in the framing.
    for name, (_short, roles, concern) in NEEDS.items():
        first = re.findall(r"\b(\w+Concern)\b", _attribute(_need(name), "source"))[0]
        assert first == concern, (name, first)
        declared = _declared_holders(name)
        assert declared, (name, "a need has its holders")
        holders = _framing_holders(first)
        assert declared <= holders, (name, sorted(declared - holders), "a holder holds the first source concern")
        assert declared == roles, (name, sorted(declared ^ roles))
        # the statement names its holders, and no other role
        named = {words for words in ALL_ROLE_WORDS if words in _statement(_need(name)).lower()}
        assert named == {ROLE_WORDS[role] for role in roles}, (name, named)


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
    assert "hmiDisplayBoundary" not in " ".join(_need_text(name) for name in NEEDS)


def test_a_reviewer_question_concern_is_named_by_a_need_and_checked_by_its_review():
    leading = {concern for _short, _roles, concern in NEEDS.values()}
    assert len(REVIEWED_CONCERNS) == 7 and set(REVIEWED_CONCERNS) == PHASE1_CONCERNS - leading
    for concern, (need, asked_by, question) in REVIEWED_CONCERNS.items():
        assert concern not in leading, f"{concern} is a reviewer question and leads no need"
        assert concern in _attribute(_need(need), "source"), (concern, need)
        others = [name for name in NEEDS if name != need and concern in _attribute(_need(name), "source")]
        assert not others, (concern, "one need's source names it", others)
        plan_short = VALIDATION[need][0]
        doc = _plan_doc(plan_short)
        assert f"{asked_by} {question}" in doc, (concern, "the asking roles lead the concern's whole question")
        for role in _framing_holders(concern):
            assert ROLE_WORDS[role] in asked_by.lower(), (concern, role, "the concern's own roles ask its question")
        rationale = _attribute(_need(need), "rationale")
        handover = [sentence for sentence in _sentences(rationale)
                    if sentence.startswith("Phase 5 also derives from this need")]
        assert len(handover) == 1 and plan_short in handover[0], \
            (concern, "the rationale hands the concern's requirements to phase 5 and names the review")
    header = _flat(_header())
    assert HEADER_COUNT in header, "the header counts the reviewer questions"
    for concern in REVIEWED_CONCERNS:
        assert concern in header, (concern, "the header gives the reason of each reviewer question")
    assert HEADER_REASONS in _header_paragraphs(), "the header paragraph of the reasons, pinned whole"


def test_each_need_has_one_planned_review_on_its_phase_2_use_cases():
    code = _code()
    context_raw = CONTEXT.read_text(encoding="utf-8")
    context = strip_comments(context_raw)
    plans = _plans()
    assert sorted(plans) == sorted(short for short, _use_cases in VALIDATION.values())
    associations = re.findall(
        r"\bconnection\s+\w+\s*:\s*ValidationPlanningAssociation\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    dependencies = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
    for need, (plan_short, use_cases) in VALIDATION.items():
        plan = plans[plan_short]
        assert associations.count((need, plan)) == 1, (need, plan)
        assert [pair for pair in associations if pair[1] == plan] == [(need, plan)], (plan, "its one need")
        assert _plan_doc(plan_short).startswith(f"For {NEEDS[need][0]}, a planned stakeholder review."), plan
        assert sorted(target for source, target in dependencies if source == plan) == \
            sorted(f"{CONTEXT_PACKAGE}::{use_case}" for use_case in use_cases), (plan, use_cases)
        for use_case in use_cases:
            # the bound target exists in the operational context and carries its scenario identity
            assert re.search(rf"\buse\s+case\s+{use_case}\s*\{{", context), use_case
            assert SCENARIOS[use_case] in braced_body(context_raw, f"use case {use_case}"), use_case
        named = _scenarios_of(_attribute(_need(need), "source"))
        assert named == {SCENARIOS[use_case] for use_case in use_cases}, \
            (need, "its review watches exactly the scenarios its source names")
    assert len(associations) == len(NEEDS), "one planned review per need"
    assert len(dependencies) == sum(len(use_cases) for _plan, use_cases in VALIDATION.values())
    # Phase 2 owns SC-HMI-001 to SC-HMI-007; the planned reviews continue the numbering.
    assert not re.search(r"<'SC-HMI-00[1-7]'>", code)
    assert set(SCENARIOS.values()) == set(re.findall(r"SC-HMI-\d{3}", context_raw)), "the phase 2 scenarios"


def test_each_planned_review_names_the_scenarios_it_watches_and_its_reviewers():
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
        assert not re.search(r"(?i)\b(?:confirm|tell|follow) that\b", doc), (plan_short, "whether, not that")
    assert set(REVIEWERS) == {plan_short for plan_short, _use_cases in VALIDATION.values()}


def test_no_need_uses_excluded_wording_an_anti_cheating_clause_or_a_claim():
    for name in NEEDS:
        text = _need_text(name)
        for guard in (EXCLUDED, ANTI_CHEATING, SAFETY_CLAIM, TIMING_CLAIM, DRAWING, FURTHER_CONTENT):
            assert not guard.findall(text), (name, guard.pattern[:30], guard.findall(text))
        assert not RENDERER.findall(_statement(_need(name))), (name, "a statement names no renderer")
    for plan_short in PLAN_DOCS:
        assert not DRAWING.findall(_plan_doc(plan_short)), (plan_short, DRAWING.findall(_plan_doc(plan_short)))
    raw = _raw()
    assert not CLAUSE_NUMBER.findall(raw), CLAUSE_NUMBER.findall(raw)


def test_no_need_states_a_number():
    # The limits and the time from the request to each mode are phase 5's.
    for name in NEEDS:
        body = _need(name)
        text = _flat(body)
        assert not NUMBER_WITH_UNIT.findall(text), (name, NUMBER_WITH_UNIT.findall(text))
        statement = _statement(body)
        for part in (statement, _attribute(body, "rationale")):
            assert not re.search(r"\d", ALLOWED_DIGITS.sub("", part)), (name, "a digit outside the identifiers", part)
            assert not NUMBER_WORDS.findall(part), (name, NUMBER_WORDS.findall(part))
        assert not re.search(r"\d", statement), (name, "a statement has no digit")
        if NEEDS[name][1] == {"VehicleOccupant"}:
            # the needs of the driver leave their requirements to phase 5; the run identity states none of its own
            assert "Phase 5 derives its requirements" in _attribute(body, "rationale"), \
                f"{name}: the rationale leaves its requirements to phase 5"


def test_the_simulator_and_stale_content_appear_only_in_the_listed_sentences():
    # Whatever text a sentence is added to (a doc, a comment or a string): when it names the simulator, the
    # simulation, CARLA or the truth of the scene, it is a sentence of TRUTH_SENTENCES, and when it names current,
    # live or stale content, a last frame, frozen content or up-to-date content, it is one of CURRENCY_SENTENCES.
    sentences = _model_sentences()
    assert len(sentences) >= 80, "the population of the check must not be vacuous"
    for terms, allowed in ((TRUTH_TERMS, TRUTH_SENTENCES), (CURRENCY_TERMS, CURRENCY_SENTENCES)):
        named = [sentence for sentence in sentences if terms.search(sentence)]
        for sentence in named:
            assert sentence in allowed, f"names {terms.pattern[10:40]} outside the listed sentences: {sentence}"
        assert set(allowed) <= set(named), "every listed sentence is in the model"


def test_the_input_contracts_are_comments_for_phase_5():
    raw = _raw()
    found = re.findall(r"\bcomment\s+(\w+)\s+about\s+(\w+)\s*/\*", raw)
    assert found == [(name, need) for name, (need, _text) in CONTRACTS.items()]
    for name, (need, text) in CONTRACTS.items():
        match = re.search(rf"\bcomment\s+{name}\s+about\s+{need}\s*/\*(.*?)\*/", raw, re.S)
        assert match, f"the input contract {name} is a comment about {need}"
        assert _flat(match.group(1)) == text, name
        assert not re.search(r"\d", ALLOWED_DIGITS.sub("", text)), (name, "a contract states no number")
    scene = CONTRACTS["perceivedSceneContract"][1]
    assert "it is an estimate of the display's own, and NEED-HMI-001 leaves it out by its words." in scene
    assert "whether the speed that its fusion gives is the speed of the object or the speed at which it closes is " \
        "open." in scene
    assert "One plan holds at most one of the two." in CONTRACTS["warningRequestContract"][1]


def test_two_tables_frame_the_needs_concern_and_show_needs_and_planned_reviews():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*StakeholderNeedsConcern\b", code)
    assert len(concerns) == 1 and re.findall(r"\bconcern\s+(\w+)\s*:", code) == concerns
    concern = braced_body(code, f"concern {concerns[0]} : StakeholderNeedsConcern")
    lines = [line.strip() for line in concern.splitlines() if line.strip() and line.strip() != "doc"]
    assert lines[0] == "subject;", "the subject is the first parameter"
    holders = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern))
    assert holders == {"SystemsEngineer", "ProductLineEngineer"}
    doc = re.search(r"\bdoc\s*/\*(.*?)\*/", braced_body(_raw(), f"concern {concerns[0]} : StakeholderNeedsConcern"),
                    re.S)
    assert doc and _flat(doc.group(1)) == NEEDS_CONCERN_DOC
    views = re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
    assert len(views) == 2 and re.findall(r"(?m)^  view\s+(\w+)", code) == views, "two table views, no other"
    exposed = {}
    for view in views:
        body = braced_body(code, f"view {view} : TVD::TableView")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*StakeholderRequirementDefinitionViewpoint\s*\{{\s*frame\s+"
                         rf"{concerns[0]}\s*;\s*\}}", body), view
        assert "attribute :>> includeReferenceElements = true;" in body, view
        exposed[view] = re.findall(r"\bexpose\s+([^;]+);", body)
    plan_names = list(_plans().values())
    assert sorted(exposed.values()) == sorted([list(NEEDS), plan_names]), exposed
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


def test_the_charter_lists_the_needs_package_after_the_classification():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    charter = braced_body(framing, "part hmiDisplayCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    # the framing test owns the exact list; later phases append their packages after this one
    assert names.index(PACKAGE) == names.index("DE4SDV_HmiDisplayCapabilityClassification") + 1
    assert MODEL in charter_package_files(FRAMING, "hmiDisplayCharter")


def test_the_guide_has_a_phase_4_section_and_names_phase_5_next():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## Capability classification (Phase 3)") < guide.index("## Stakeholder needs (Phase 4)") \
        < guide.index("## What the framing already records as open")
    assert guide.count("## Stakeholder needs (Phase 4)") == 1
    raw_section = _guide_section()
    section = " ".join(raw_section.split())
    for short, _roles, _concern in NEEDS.values():
        assert short in section, short
    for plan_short, _use_cases in VALIDATION.values():
        assert plan_short in section, plan_short
    bullets = {match[1]: " ".join(match[2].split())
               for match in re.finditer(r"(?ms)^- `(NEED-HMI-\d{3})`:(.*?)(?=^- `|^\s*$)", raw_section)}
    assert list(bullets) == [short for short, _roles, _concern in NEEDS.values()]
    assert bullets == GUIDE_BULLETS, "the guide's Phase 4 bullets, pinned whole"
    paragraphs = [" ".join(part.split()) for part in re.split(r"\n\s*\n", raw_section.strip())
                  if not part.lstrip().startswith("- ")]
    assert tuple(paragraphs) == GUIDE_PARAGRAPHS, "the guide's Phase 4 paragraphs, pinned whole"
    for _name, (short, roles, _concern) in NEEDS.items():
        assert GUIDE_HOLDERS[short] in bullets[short], (short, "the guide names the holders")
        named = {words for words in ALL_ROLE_WORDS if words in bullets[short].lower()}
        assert named == {ROLE_WORDS[role] for role in roles}, (short, named)
    assert "Seven concerns get no need of their own" in section and len(REVIEWED_CONCERNS) == 7
    assert not CLAUSE_NUMBER.findall(raw_section), CLAUSE_NUMBER.findall(raw_section)
    assert all(len(line) <= 79 or "](" in line for line in raw_section.splitlines()), "the guide wraps at 79"
    flat = " ".join(guide.split())
    assert STATUS in flat
    frame = " ".join(guide.split("## Authoritative frame", 1)[1].split("\n## ", 1)[0].split())
    assert f"]({GUIDE_LINK}): the Phase 4 needs of the HMI display and their planned reviews." in frame
    nxt = " ".join(guide.split("## Next obligation and execution limits", 1)[1].split("\n## ", 1)[0].split())
    assert nxt.count(NEXT_OBLIGATION) == 1
    assert "The next model obligation is **Phase 4**" not in flat


def test_the_guide_ends_with_exactly_one_newline():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.endswith("\n") and not guide.endswith("\n\n"), "the guide ends with exactly one newline"


def test_the_header_states_its_non_claims_and_names_no_drawing():
    header = _flat(_header())
    assert HEADER_NON_CLAIM in header, "the header keeps its non-claims"
    assert HEADER_DRAWING in _header_paragraphs(), "the header paragraph on the drawing, pinned whole"
    assert "Phase 5 adds to this package the requirements derived from these needs." in header


def test_the_package_declares_no_name_that_another_model_package_declares():
    kinds = r"(?:part|requirement|concern|view|dependency|connection|comment)"
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(?:<'[^']*'>\s*)?(\w+)", _raw()))
    assert len(declared) >= 40, "the population of the check must not be vacuous"
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
