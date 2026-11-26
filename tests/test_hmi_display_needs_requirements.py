"""Content pins for the HMI display stakeholder needs (INC-HMI-001, phase 4), not semantic validation.

Each need is held by the parties the HMI display serves, leads its source with the phase 1 concern it derives
from, and has one planned stakeholder review on the phase 2 use cases it covers. The roles that check the answer
stay on the reviews. Seven phase 1 concerns are reviewer questions: a need's source names each, its review asks
the concern's question, led by the concern's own roles, and its rationale hands the concern's requirements to
phase 5. Each reviewed text is pinned whole, and the rule guards stay beside the pins: no digit outside the
identifiers, no number with a unit, no clause number, no positive safety or timing claim, no anti-cheating
clause, no drawing, no renderer in a statement, and the simulator and stale content named only in the listed
sentences. The guards match the words they list; a claim in other words is for review. The tests read the model
text; they do not parse SysML. The requirements of phase 5 in the same package have their own module,
test_hmi_display_requirements.py; this one keeps the needs, the reviews and the rules over every sentence of
the package.
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
#: stale content and its synonyms, outdated content among them (hmiStaleContentInScope)
CURRENCY_TERMS = re.compile(r"(?i)\b(?:current\w*|live\w*|last frames?|stale\w*|froz\w*|freez\w*|up[- ]to[- ]date|"
                            r"outdat\w*)\b")

#: the purpose of the scene on the display, a purpose and no claim of how a driver supervises
SCENE_PURPOSE = (
    "The display shows the driver what the driver-assistance system perceives, right or wrong, with the object "
    "that the system acts on marked, so that the driver can supervise the system with it, and it shows the scene "
    "that the system gives and no other (the display-rule decision of 2026-11-22).")

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

#: the purpose of keeping the speed and the warning through the outages: the driver-assistance system drives on
OUTAGE_PURPOSE = (
    "While the drawing of the scene or Android in the IVI VM is out, the driver-assistance system goes on driving "
    "the vehicle, and the driver still needs the speed and the warning then, or to know that the warning cannot "
    "come.")

#: the first question of the outage review: the unavailability only where the warning cannot be given
OUTAGE_REVIEW = (
    "While the app that draws the scene is out and while Android in the IVI VM boots, hangs and restarts "
    "(SC-HMI-003 to SC-HMI-006), can verification engineers and safety experts confirm whether the driver saw the "
    "vehicle speed throughout and got the collision warning for each warning request, or, where the warning could "
    "not be given, saw that it was unavailable?")

#: the one sentence of a need that names the simulation
SIMULATED_ONLY = (
    "A verdict holds for the simulated configuration only (asmHmiSimulationStandsIn).")

#: the one sentence of a review that names the simulator: no object that the system did not give
SCENE_NO_ESTIMATE = (
    "While the warning scenarios and the no-reaction scenarios of the driver-assistance increment run on the "
    "display (SC-HMI-001 and SC-HMI-002), can verification engineers and systems engineers confirm whether the "
    "lane, the path, the objects with their level and the closest object in the path with its distance and its "
    "speed that the display shows are those that the driver-assistance system gave, whether the display marked the "
    "closest object in the path apart from the other objects, and whether the display showed any object that the "
    "system did not give, from the simulator's record of the scene or from an estimate of the display's own?")

#: the review sentence on the states of each element
CURRENCY_REVIEW = (
    "While the app that draws the scene is out, while Android in the IVI VM boots, hangs and restarts, and while the "
    "warning request stops reaching the display (SC-HMI-003 to SC-HMI-007), can safety experts and verification "
    "engineers tell the states that each element of the HMI display can be in, current, late or missing, and the "
    "state in which the collision warning is unavailable, what the display shows in each, and whether the display "
    "showed any element as current when it was not, or the warning as available when it could not be given?")

#: the sentences of the requirements of phase 5, their terms, the header and the comments that name the simulation:
#: each counts a time or a limit in simulation time, or keeps the simulator's record off the display
PHASE_FIVE_TRUTH_SENTENCES = (
    (
        "A display that shows the simulator's record of the scene or an estimate of its own shows another scene "
        "(hmiSimulatorTruthOutOfScope)."),
    (
        "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-004 and SC-HMI-006 has "
        "the end of its outage in the IVI VM before its own end, and in each run every scene that reaches the HMI "
        "display outside an outage in the IVI VM, or a newer scene, is on the display less than 0.1 s of wall-clock "
        "time after it arrives, with its lane points, its path and each of its objects with its level, as many "
        "objects as the scene gives and at the positions that it gives, read within the drawing tolerance that phase "
        "8 states; and when no frame on the display shows a lane, a path or an object that no scene of the run gives, "
        "from the simulator's record of the scene or from an estimate of the display's own."),
    (
        "In the realization of the driver-assistance increment the vehicle speed enters the system with its sample "
        "time in simulation time, typed by COVESA VSS in km/h (VehicleSpeedSamplePayload and "
        "MAP-DRIVING-DA-VEHICLE-SPEED), and the system reads it once in each result pass."),
    (
        "The warning request is the output that the driver-assistance increment realizes from the warnings of each "
        "plan: one event for each plan, which asks for the collision warning when the plan holds the "
        "forward-collision warning or the emergency braking and carries the capture time in simulation time of the "
        "frame that the plan came from, with no value changed on its path (CollisionWarningRequestOutput and "
        "MAP-DRIVING-DA-WARNING-REQUEST)."),
    (
        "The limit counts in wall-clock time while the simulation runs no faster than wall-clock time, which is the "
        "obligation of System 2, and makes no timing claim for a vehicle."),
    (
        "The scene and the warning request share one period of 0.1 s of simulation time in the realization of the "
        "driver-assistance increment: one camera image, one result pass, one plan and one event of the warning "
        "request each 0.1 s; the vehicle speed comes with each world snapshot at the input of the system, every step "
        "of 0.05 s."),
    (
        "The vehicle speed brings the newest time to the display with each world snapshot, so the limit in simulation "
        "time also counts the time from the capture of a frame to the arrival of its scene and its event at the "
        "display, and the time that the display takes to show the scene."),
    (
        "The limit in simulation time counts against the newest time that has reached the display, so it catches a "
        "delay before the display, which an age taken from the arrival would hide, and a value whose time the display "
        "changes."),
    (
        "At 014e0e7a VisionPilot makes one pass for each camera image that it takes, and the bench of the "
        "driver-assistance increment gives it one each 0.1 s of simulation time."),
    (
        "- Vehicle speed: the speed of the vehicle in km/h, with its sample time in simulation time, as the vehicle "
        "gives it to the driver-assistance system at its input."),
    (
        "- Warning request: the input by which the HMI display is asked for the collision warning, in the form that "
        "the driver-assistance increment gives it at its boundary: one event for each plan of the driver-assistance "
        "system, telling whether it requests the collision warning, with its issue time in simulation time."),
    (
        "- Time of a value: the time in simulation time that a value of an input carries as its source gives it: for "
        "a scene, the capture time of the camera image of its result pass; for a vehicle speed, its sample time; for "
        "an event of the warning request, its issue time."),
    (
        "- Current: a value of an input is current while the time of the value is at most 0.2 s of simulation time "
        "older than the newest time of a value that has reached the HMI display, and the newest value of the same "
        "input reached it at most 0.2 s of wall-clock time before."),
    "- Simulation time: the time of the simulated world.",
    (
        "Set here, each with its reason in a rationale: the speed of the closest object as its fusion gives it; the "
        "object that the system acts on; distances to the whole metre and speeds to the whole km/h; the vehicle speed "
        "at the input of the driver-assistance system; the share of the HMI display in the time that the "
        "driver-assistance increment allots from the warning request to each mode, 0.1 s of wall-clock time, which "
        "every change of what the display shows takes as its presentation time; the limits of 0.2 s of simulation "
        "time and of 0.2 s of wall-clock time beyond which an element is outdated; the warning unavailable while the "
        "warning request is outdated; and the split of the renderers, by the owner's decision of 2026-11-17."),
    (
        "Whether the time from the capture of a frame to the arrival of its scene and its event at the HMI display, "
        "with the time to show the scene, stays within one period of 0.1 s, as the limit in simulation time of the "
        "term current needs, is open until a readiness probe measures it; a longer time revises that limit."),
    "The bench runs the simulation no faster than wall-clock time.",
    (
        "The records hold each value of each input as its source gives it, with its simulation time, and where it "
        "reaches the HMI display, with the wall-clock time of its arrival; each frame on the display and the start of "
        "each sound, with their wall-clock times; and the files and the settings that the display identity names."),
)

#: the sentences that may name the simulator: each keeps the simulator's record off the display, binds a
#: verdict to the simulated configuration, or counts in simulation time
TRUTH_SENTENCES = (SCENE_NO_ESTIMATE, SIMULATED_ONLY, *PHASE_FIVE_TRUTH_SENTENCES)

#: the statement that no element is shown as current when it is not
CURRENCY_STATEMENT = (
    "Vehicle occupants need the HMI display to show the driver no element as current when it is not, and to show the "
    "driver when the collision warning is unavailable.")

#: the sentences of the requirements of phase 5, their terms, the header and the comments that name current or outdated
#: content: each states when an element or the warning request is current, or what the display shows while it is
#: outdated
PHASE_FIVE_CURRENCY_SENTENCES = (
    (
        "During an outage in the IVI VM the app that draws the scene cannot show it; REQ-HMI-006 then shows the scene "
        "as outdated, and once the app gives its first frame again this requirement holds again."),
    (
        "Before the first vehicle speed of a run reaches the display there is no speed to show, and REQ-HMI-006 shows "
        "the element as outdated."),
    (
        "The request carries no end, so the warning lasts while the request asks: a continuing request continues the "
        "warning, and the warning ends once the request asks for none or is outdated, when REQ-HMI-007 shows that it "
        "is unavailable."),
    (
        "The HMI display shall show each element as outdated while, and only while, the element is outdated, "
        "following each change of its state within the presentation time."),
    (
        "The display shows no element as current when it is not, so that the driver supervises the driver-assistance "
        "system on what it perceives now (NEED-HMI-005)."),
    "The limits of the term current take two periods, so that one late value is tolerated.",
    (
        "While those times stay within one period together, a scene stays current until the next one is shown, and "
        "the warning request until its next event; with longer times an element can turn outdated before its next "
        "value comes, and the limit is revisited once a readiness probe measures them "
        "(warningPresentationFixedInPhase5)."),
    (
        "Late and missing values give one state, outdated, and phase 8 states how an outdated element looks; the "
        "visual design stays out of scope (hmiHumanFactorsOutOfScope)."),
    (
        "An element is shown as current again once it is current, which is the validity rule of the display; the "
        "converse, current while it is current, keeps a display from showing everything as outdated."),
    "The state of each element counts on its own, so a late scene leaves the vehicle speed current.",
    (
        "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-003 to SC-HMI-006 has its "
        "outage in the IVI VM and each run of SC-HMI-007 the stop of the Eclipse S-CORE path, and in each run each "
        "frame on the display shows each element as outdated, in the form that phase 8 states for it, from less than "
        "0.1 s of wall-clock time after the element turns outdated until less than 0.1 s of wall-clock time after it "
        "turns current again, and as current at every other time; an element is outdated from the start of the run "
        "until a first current value of its input reaches the HMI display."),
    (
        "The HMI display shall show that the collision warning is unavailable while, and only while, the warning "
        "request is outdated, following each change of the state of the warning request within the presentation time."),
    (
        "The warning request carries no indication of its own availability (gapHmiWarningAvailability), and one of "
        "its events comes for each plan, telling whether it asks, so the display learns from their age that the "
        "warning cannot come: the warning is unavailable while the warning request is outdated."),
    (
        "The warning shows as available again once the warning request is current, which is the validity rule; the "
        "converse keeps a display from showing the warning as unavailable at all times."),
    (
        "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-007 has the stop of the "
        "Eclipse S-CORE path at least 0.3 s of wall-clock time before its end, and in each run the display shows that "
        "the collision warning is unavailable from less than 0.1 s of wall-clock time after the warning request turns "
        "outdated until less than 0.1 s of wall-clock time after it turns current again, and at no other time, so "
        "that the warning shows as available again only once an event of the warning request is current."),
    (
        "Throughout each outage in the IVI VM, the HMI display shall show the vehicle speed, give the collision "
        "warning while the warning request asks for it, and show that the warning is unavailable while the warning "
        "request is outdated."),
    (
        "The speed and the warning hold throughout, the scene returns under REQ-HMI-001 once the app gives frames "
        "again, and until then REQ-HMI-006 shows it as outdated, within the limits of the term current and the "
        "presentation time from the last scene that the app has shown."),
    (
        "- Ask: the warning request asks while its newest event that has reached the HMI display is current and "
        "requests the collision warning."),
    (
        "- Current: a value of an input is current while the time of the value is at most 0.2 s of simulation time "
        "older than the newest time of a value that has reached the HMI display, and the newest value of the same "
        "input reached it at most 0.2 s of wall-clock time before."),
    (
        "An element is current while it shows a current value, and the warning request is current while its newest "
        "event is current."),
    (
        "- Outdated: an element or the warning request is outdated at each instant at which it is other than current: "
        "a value that comes late and a value that never comes count alike, and so does the time before the first "
        "value of its input reaches the HMI display."),
    (
        "Set here, each with its reason in a rationale: the speed of the closest object as its fusion gives it; the "
        "object that the system acts on; distances to the whole metre and speeds to the whole km/h; the vehicle speed "
        "at the input of the driver-assistance system; the share of the HMI display in the time that the "
        "driver-assistance increment allots from the warning request to each mode, 0.1 s of wall-clock time, which "
        "every change of what the display shows takes as its presentation time; the limits of 0.2 s of simulation "
        "time and of 0.2 s of wall-clock time beyond which an element is outdated; the warning unavailable while the "
        "warning request is outdated; and the split of the renderers, by the owner's decision of 2026-11-17."),
    (
        "Whether the time from the capture of a frame to the arrival of its scene and its event at the HMI display, "
        "with the time to show the scene, stays within one period of 0.1 s, as the limit in simulation time of the "
        "term current needs, is open until a readiness probe measures it; a longer time revises that limit."),
    (
        "Fixed: the HMI display learns that the collision warning is unavailable from the age of the events of the "
        "warning request, with no signal of its own: the warning is unavailable while the warning request is "
        "outdated, and available again once it is current (REQ-HMI-007 and the term current)."),
    (
        "It leaves at least 0.3 s of wall-clock time before the end of the run, the longest response that the "
        "criteria judge: 0.2 s to turn outdated and 0.1 s to show it."),
)

#: the sentences that may name current, live, stale or outdated content: each shows no late element as current
CURRENCY_SENTENCES = (CURRENCY_STATEMENT, CURRENCY_PURPOSE, CURRENCY_STATES, CURRENCY_REVIEW,
                      *PHASE_FIVE_CURRENCY_SENTENCES)

# The reviewed texts, pinned whole (whitespace flattened). A change to a need, a review or a contract comment is a
# change of the reviewed content: update the pin in the same commit, on purpose.

#: need -> its statement
STATEMENTS = {
    "needPerceivedSceneOnTheDisplay": (
        "Vehicle occupants need the HMI display to show the driver the scene as the driver-assistance system gives "
        "it from its own perception: its lane, the path it fits to that lane, the objects it detects with their "
        "level relative to that path, and, marked apart from the other objects, the closest object in its path, "
        "which the system acts on, with the distance and the speed that its fusion gives."),
    "needVehicleSpeedOnTheDisplay": (
        "Vehicle occupants need the HMI display to show the driver the vehicle speed that the driver-assistance "
        "system is given."),
    "needCollisionWarningOnRequest": (
        "Vehicle occupants need the HMI display to give the driver the collision warning on the display and as a "
        "sound when the warning request of the driver-assistance system asks for it, and no collision warning without "
        "such a request."),
    "needSpeedAndWarningThroughOutages": (
        "Vehicle occupants need the HMI display to show the driver the vehicle speed and to give the collision "
        "warning when it is requested, or, when the warning cannot be given, to show that it is unavailable, also "
        "while the app that draws the scene hangs or ends and while Android in the IVI VM hangs, boots or "
        "restarts."),
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
    "needSpeedAndWarningThroughOutages": " ".join((
        OUTAGE_PURPOSE,
        ("NEED-HMI-002 and NEED-HMI-003 state the speed and the warning; this need adds that they stay through "
         "each outage. It rests on N-AEBS-008, the need of the product line that the availability of the AEBS be "
         "apparent, and on the status indication of REQ-AEBS-013. Each outage is an event inside the boundary of "
         "the display, whose detection phases 6 to 8 decide. The need names no renderer and carries no safety "
         "claim. Phase 5 derives its requirements and their limits. Phase 5 also derives from this need the "
         "requirements on the sequence from each outage to what the display shows, on which renderer draws each "
         "element and on the paths of the inputs to the renderers: its source names their concerns, and SC-HMI-011 "
         "asks their questions."))),
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
        "For NEED-HMI-004, a planned stakeholder review.", OUTAGE_REVIEW,
        _ask("hmiAndroidOutageConcern"), _ask("hmiRendererAllocationConcern"), _ask("hmiRendererPathConcern"))),
    "SC-HMI-012": "For NEED-HMI-005, a planned stakeholder review. " + CURRENCY_REVIEW,
    "SC-HMI-013": (
        "For NEED-HMI-006, a planned stakeholder review. While the seven scenarios run (SC-HMI-001 to SC-HMI-007), "
        "can verification engineers and product-line engineers tell from each run which build and which configuration "
        "of the HMI display ran and which candidate revision the run of the driver-assistance system identifies, "
        "whether each verdict is bound to them, and whether a display with a changed build or setting identifies "
        "itself as a different one?"),
}
#: the comments of phase 4 on the input contracts, which phase 5 states as requirements and rationales
REMOVED_CONTRACTS = ("perceivedSceneContract", "warningRequestContract")
#: the named comments of the package: the terms of the requirements and the three comments on the gaps
PHASE_FIVE_COMMENTS = ["termsHmiDisplayRequirements", "warningPresentationFixedInPhase5",
                       "warningAvailabilityFixedInPhase5", "hmiTestbedObligationsOfPhase5"]
#: the count sentence of the header
HEADER_COUNT = (
    "Seven concerns are reviewer questions: a need's source names them and its review checks them.")

#: the title of the header
HEADER_TITLE = "DE4SDV HMI display stakeholder needs and requirements."

#: the header's first paragraph, pinned whole: who holds the needs and who carries out the reviews
HEADER_INTRO = " ".join((
    "INC-HMI-001, phase 4: the stakeholder needs of the HMI display, the system of interest the charter "
    "declares. Each need is held by the parties the display serves and leads its source with the phase 1 concern "
    "it derives from. Each has one planned stakeholder review on the scenarios of phase 2 it covers, carried out "
    "by the roles that check the answer.", HEADER_COUNT))

#: the header paragraph that gives the reason of each reviewer question, pinned whole
HEADER_REASONS = (
    "Each of these seven concerns asks to see an answer that the model gives elsewhere, the view of a later phase "
    "or, for the common content, the classification of phase 3 and the lifecycle decision, and the HMI display "
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

#: the name of the display rule of 2026-11-22, one wording wherever the rule is named
DISPLAY_RULE = "the display-rule decision of 2026-11-22"

#: the dated record of the display rule, the header paragraph after the drawing paragraph
DISPLAY_RULE_RECORD = (
    "The owner decided on 2026-11-22 that the display shows what the driver-assistance system perceives, right or "
    "wrong, with the object that the system acts on marked, and not only what reaches the control of the vehicle: "
    "the display-rule decision of 2026-11-22. NEED-HMI-001 and its review carry it.")

#: the header paragraph of phase 4 that handed the requirements to phase 5, which phase 5 replaces
HEADER_PHASE_FIVE = "Phase 5 adds to this package the requirements derived from these needs."
#: the two header paragraphs of phase 5, pinned whole: the requirement set and its values, and their variability
HEADER_PHASE_FIVE_SET = (
    "Phase 5: the requirements derived from these needs, each with one subject, the HMI display, one verification "
    "method and its success criteria. They derive from the needs and rest on REQ-AEBS-002 and REQ-AEBS-013, and the "
    "scope of the increment caps them at ten. From the driver-assistance increment the terms take the form of the "
    "warning request and the start of each mode; from the files of VisionPilot at 014e0e7a they take the levels, the "
    "fixed distance of 150 m and the sign that the fusion declares for the speed of the closest object. The "
    "rationales name those files by their file names, and upstream.md gives each with its path. Set here, each with "
    "its reason in a rationale: the speed of the closest object as its fusion gives it; the object that the system "
    "acts on; distances to the whole metre and speeds to the whole km/h; the vehicle speed at the input of the "
    "driver-assistance system; the share of the HMI display in the time that the driver-assistance increment allots "
    "from the warning request to each mode, 0.1 s of wall-clock time, which every change of what the display shows "
    "takes as its presentation time; the limits of 0.2 s of simulation time and of 0.2 s of wall-clock time beyond "
    "which an element is outdated; the warning unavailable while the warning request is outdated; and the split of "
    "the renderers, by the owner's decision of 2026-11-17. The comments on gapHmiWarningPresentation and "
    "gapHmiWarningAvailability give what phase 5 fixes of those gaps and what stays open, and the comment on "
    "gapHmiRendererIntegration gives what the criteria ask of System 2.")
HEADER_PHASE_FIVE_VARIABILITY = (
    "Rule 5 of the increment workflow makes a requirement core when its subject has no link and it has none of its "
    "own. Phase 3 classes the HMI display as content of every member of the governed scope and leaves open which of "
    "its content is common, so phase 9 claims no member."
    # the links of the system of interest
    " In the framing, phase 9 makes the system of interest depend on the features visionPilot and guestAndroidSDV. "
    "Every requirement follows it, and none carries a link of its own. REQ-HMI-003 to REQ-HMI-007 name no variant "
    "beyond their subject.")

#: the non-claim sentence of the header
#: The record of the identity-term amendment of phase 10, before the non-claims.
HEADER_IDENTITY_TERM = (
    "The identity-term amendment of phase 10 makes the term display identity name the builds of the vehicle data "
    "publisher in the SDV Core VM, of the identity recording service and of the composition of the display on the "
    "central computer, and the image of the SDV Core VM, which phase 8 places inside the display. It changes no "
    "statement and no success criterion.")
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
        "the display shows the driver the scene as the driver-assistance system gives it from its own perception, "
        "with the object that the system acts on marked. Vehicle occupants. Reviewed by `SC-HMI-008` on "
        "`SC-HMI-001` and `SC-HMI-002`."),
    "NEED-HMI-002": (
        "the display shows the driver the vehicle speed that the driver-assistance system is given. Vehicle "
        "occupants. Reviewed by `SC-HMI-009` on `SC-HMI-001` and `SC-HMI-002`."),
    "NEED-HMI-003": (
        "the display gives the collision warning on the display and as a sound when the warning request asks for it, "
        "and none without a request. Vehicle occupants. Reviewed by `SC-HMI-010` on `SC-HMI-001` and `SC-HMI-002`."),
    "NEED-HMI-004": (
        "the speed and the warning, or, when the warning cannot be given, the fact that it is unavailable, stay on "
        "the display while the app that draws the scene or Android in the IVI VM is out. Vehicle occupants. "
        "Reviewed by `SC-HMI-011` on `SC-HMI-003` to `SC-HMI-006`."),
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
    "On 2026-11-22 the owner decided that the display shows what the driver-assistance system perceives, right or "
    "wrong, with the object that the system acts on marked, and not only what reaches the control of the vehicle: "
    "the display-rule decision of 2026-11-22. `NEED-HMI-001` and `SC-HMI-008` carry it.",
    "Seven concerns get no need of their own: the items that cross into the display, its common content, the "
    "warning's sequence, the outages of the scene's drawing, which renderer draws what, the paths to the renderers, "
    "and the late and missing content. Their roles check the answer rather than use it, as in the stakeholder needs "
    "of the driver-assistance and the E/E architecture increments, so each is a question for a planned review: "
    "`NEED-HMI-001` names the first two in its source and `SC-HMI-008` asks them, `NEED-HMI-003` names the third and "
    "`SC-HMI-010` asks it, `NEED-HMI-004` names the next three and `SC-HMI-011` asks them, and `NEED-HMI-005` names "
    "the last and `SC-HMI-012` asks it.",
    "No need states a number or names a drawing: Phase 5 derives the requirements and their limits, how the app in "
    "the IVI VM draws the scene is a choice of Phase 8, and no need asks for gear, set speed, speed limit or "
    "another telltale. Phase 5 states in its requirements what the scene of the pinned driver-assistance system "
    "carries and what the warning request asks for and carries.",
    "`SC-DRIVING-018` of the driver-assistance increment watches the collision warning in `SC-DRIVING-012` and "
    "`SC-DRIVING-013`, which `SC-HMI-010` watches too, for another subject: its need, `NEED-DRIVING-010`, asks the "
    "candidate to give the warning request, and `NEED-HMI-003` asks the display to give the warning from it.",
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
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 logical "
    "architecture, Phase 8 physical and software realization and Phase 9 variability and configuration, "
    "proposal.**")

#: the guide's next obligation
NEXT_OBLIGATION = (
    "The next model obligation is **Phase 10**: the verification cases, one or more for each requirement of the "
    "increment; its first gate is `verificationCaseVerifiesRequirement`.")



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
    # the links of rule 5 to features (phase 9) are pinned by tests/test_hmi_display_variability_configuration.py
    dependencies = [(source, target) for source, target in
                    re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
                    if not target.startswith("DE4SDV_SDVProductLineFeatureModel::")]
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


def test_the_input_contracts_of_phase_4_are_stated_by_the_requirements():
    # Phase 4 kept two input contracts as comments about NEED-HMI-001 and NEED-HMI-003; phase 5 states them in
    # the requirements and their rationales (test_hmi_display_requirements.py pins those), so the comments go.
    raw = _raw()
    for name in REMOVED_CONTRACTS:
        assert name not in raw, name
    assert re.findall(r"\bcomment\s+(\w+)\s+about\s+(\w+)\s*/\*", raw) == [], \
        "no comment is about a need: the comments of phase 5 are about qualified gaps or their package"
    # the package names its comments of phase 5 and no other comment: a free comment is no reviewed text
    assert re.findall(r"(?m)^\s*comment\s+(\w+)", _code()) == PHASE_FIVE_COMMENTS


def test_two_tables_frame_the_needs_concern_and_show_needs_and_planned_reviews():
    code = _code()
    concerns = re.findall(r"\bconcern\s+(\w+)\s*:\s*StakeholderNeedsConcern\b", code)
    assert concerns == ["hmiDisplayNeedsConcern"], "one needs concern"
    # phase 5 adds the requirement trace concern; test_hmi_display_requirements.py pins it
    assert re.findall(r"\bconcern\s+(\w+)\s*:", code) == [*concerns, "hmiDisplayRequirementTraceConcern"]
    concern = braced_body(code, f"concern {concerns[0]} : StakeholderNeedsConcern")
    lines = [line.strip() for line in concern.splitlines() if line.strip() and line.strip() != "doc"]
    assert lines[0] == "subject;", "the subject is the first parameter"
    holders = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern))
    assert holders == {"SystemsEngineer", "ProductLineEngineer"}
    doc = re.search(r"\bdoc\s*/\*(.*?)\*/", braced_body(_raw(), f"concern {concerns[0]} : StakeholderNeedsConcern"),
                    re.S)
    assert doc and _flat(doc.group(1)) == NEEDS_CONCERN_DOC
    tables = re.findall(r"\bview\s+(\w+)\s*:\s*TVD::TableView\b", code)
    assert re.findall(r"(?m)^  view\s+(\w+)", code) == tables == [
        "hmiDisplayNeedsView", "hmiDisplayNeedValidationView", "hmiDisplayRequirementsView"], "three table views"
    # the tables that frame the needs concern: two, the needs and the planned reviews
    views = [view for view in tables
             if re.search(rf"\bframe\s+{concerns[0]}\s*;", braced_body(code, f"view {view} : TVD::TableView"))]
    assert len(views) == 2, "two table views frame the needs concern"
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


def test_the_guide_has_a_phase_4_section_and_names_the_next_obligation():
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
    listed = [line for line in raw_section.splitlines() if line.startswith("- ")]
    assert len(listed) == len(NEEDS) and all(line.startswith("- `NEED-HMI-") for line in listed), \
        "the Phase 4 list holds one bullet per need and no other"
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
    assert "The next model obligation is **Phase 5**" not in flat
    assert "The next model obligation is **Phase 6**" not in flat
    assert "The next model obligation is **Phase 7**" not in flat
    assert "The next model obligation is **Phase 8**" not in flat


def test_the_guide_ends_with_exactly_one_newline():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.endswith("\n") and not guide.endswith("\n\n"), "the guide ends with exactly one newline"


def test_the_header_states_its_non_claims_and_names_no_drawing():
    header = _flat(_header())
    assert HEADER_NON_CLAIM in header, "the header keeps its non-claims"
    assert HEADER_DRAWING in _header_paragraphs(), "the header paragraph on the drawing, pinned whole"
    assert HEADER_PHASE_FIVE not in header, "phase 5 replaced the paragraph that handed it the requirements"
    paragraphs = _header_paragraphs()
    paragraphs = [paragraphs[0].removeprefix("/*").strip(), *paragraphs[1:-1],
                  paragraphs[-1].removesuffix("/").strip()]
    assert paragraphs == [HEADER_TITLE, HEADER_INTRO, HEADER_REASONS, HEADER_DRAWING, DISPLAY_RULE_RECORD,
                          HEADER_PHASE_FIVE_SET, HEADER_PHASE_FIVE_VARIABILITY, HEADER_IDENTITY_TERM,
                          HEADER_NON_CLAIM], \
        "the header, paragraph by paragraph, whole"


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


#: the columns of the two tables, in order: (column, the feature it renders)
NEEDS_COLUMNS = [("ID", "CT::reqId"), ("Need", "CT::declaredName"), ("Statement", "CT::constraintLanguage"),
                 ("Source", "CT::attributeValue")]
PLANS_COLUMNS = [("Plan", "CT::declaredName"), ("Review", "CT::documentation")]
COLUMN = re.compile(r"\bview\s+(\w+)\s*:>\s*columnViews\s*\{\s*attribute\s+:>>\s+featureToRender\s*=\s*(CT::\w+)")


def test_the_two_tables_show_their_columns_in_order():
    code = _code()
    needs = braced_body(code, "view hmiDisplayNeedsView : TVD::TableView")
    assert COLUMN.findall(needs) == NEEDS_COLUMNS, "the needs table: ID, need, statement and source, in order"
    assert len(re.findall(r"\bview\s+\w+\s*:>\s*columnViews\b", needs)) == len(NEEDS_COLUMNS)
    assert re.findall(r"\battribute\s+constraintType\s*=\s*([\w:]+)\s*;", needs) == ["CL::ConT::required"], \
        "the statement column shows the required constraint"
    plans = braced_body(code, "view hmiDisplayNeedValidationView : TVD::TableView")
    assert COLUMN.findall(plans) == PLANS_COLUMNS, "the plans table: plan and review, in order"
    assert len(re.findall(r"\bview\s+\w+\s*:>\s*columnViews\b", plans)) == len(PLANS_COLUMNS)
    # the renderer reads no column width, so the attribute earns no place
    assert "columnWidth" not in code


def test_each_need_body_holds_its_subject_first_then_its_holders_statement_source_and_rationale():
    # The subject comes first, the accepted form; no doc or other member sits in a need body.
    member = re.compile(r"subject\b|stakeholder\b|require constraint statement\b|attribute :>> source\b"
                        r"|attribute :>> rationale\b")
    for name, (_short, roles, _concern) in NEEDS.items():
        lines = [line.strip() for line in strip_comments(_need(name)).splitlines() if line.strip()]
        kinds = [member.match(line) for line in lines]
        assert all(kinds), (name, "a need body holds only its subject, holders, statement, source and rationale",
                            lines)
        assert [kind.group(0) for kind in kinds] == ["subject", *["stakeholder"] * len(roles),
                                                     "require constraint statement", "attribute :>> source",
                                                     "attribute :>> rationale"], name


#: the sentences that may carry excluded wording, a safety word or a timing word: the header's non-claims and the
#: product-line question that names the member products
CLAIM_SENTENCES = (HEADER_NON_CLAIM, _ask("hmiContentVarianceConcern"))


def test_no_sentence_of_the_model_makes_a_claim_outside_the_listed_sentences():
    # Whatever text a sentence is added to (a doc, a comment or a string): when it holds excluded wording, a positive
    # safety word or a timing word, once the role words ("safety experts") are set aside, it is one of
    # CLAIM_SENTENCES. A claim in other words is for review.
    roles = re.compile("|".join(re.escape(words) for words in ALL_ROLE_WORDS), re.I)
    sentences = _model_sentences()
    assert len(sentences) >= 80, "the population of the check must not be vacuous"
    flagged = []
    for sentence in sentences:
        text = roles.sub("", sentence)
        if any(guard.search(text) for guard in (EXCLUDED, SAFETY_CLAIM, TIMING_CLAIM)):
            assert sentence in CLAIM_SENTENCES, f"a claim outside the listed sentences: {sentence}"
            flagged.append(sentence)
    assert set(CLAIM_SENTENCES) <= set(flagged), "every listed sentence is in the model"


def test_the_display_rule_decision_is_recorded_once_and_named_by_one_name():
    paragraphs = _header_paragraphs()
    assert paragraphs.index(DISPLAY_RULE_RECORD) == paragraphs.index(HEADER_DRAWING) + 1, \
        "the dated record follows the drawing paragraph"
    assert _flat(_raw()).count(DISPLAY_RULE) == 2, "the record and the rationale of NEED-HMI-001 name the rule"
    assert DISPLAY_RULE in _attribute(_need("needPerceivedSceneOnTheDisplay"), "rationale")
    section = " ".join(_guide_section().split())
    guide = GUIDE.read_text(encoding="utf-8")
    assert section.count(DISPLAY_RULE) == 1 and " ".join(guide.split()).count(DISPLAY_RULE) == 1
    # one wording of the rule: no other wording dates an amendment or a correction
    texts = _flat(_raw()) + " " + " ".join(guide.split())
    assert not re.search(r"(?i)\b(?:amend\w*|correct\w*) (?:on|of) 2026-11-22", texts)
