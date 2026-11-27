"""Content pins for the HMI display operational context (INC-HMI-001 phase 2), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
FEATURES = ROOT / "textual-notation-of-model/packages/features"
HMI = FEATURES / "hmi"
FRAMING = HMI / "hmi_display_framing.sysml"
MODEL = HMI / "hmi_display_operational_context.sysml"
DA_CONTEXT = FEATURES / "driving/driver_assistance_operational_context.sysml"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_HmiDisplayOperationalContext"
FRAMING_PACKAGE = "DE4SDV_HmiDisplayFraming"
DA_PACKAGE = "DE4SDV_DriverAssistanceOperationalContext"
DA_FRAMING_PACKAGE = "DE4SDV_DriverAssistanceFraming"
DA_USE_CASE_DEF = "AssistDriverForVehicleTargetAhead"
DA_STORY = "driverAssistanceStory"
CONTEXT = "hmiDisplayOperationalContext"
SOI = "hmiDisplay"
SOI_TYPE = "HmiDisplaySystem"

#: Context parts around the system of interest and their types. Phase 0 draws the boundary: the candidate
#: application and the Eclipse S-CORE path are System 1 parts outside the display; the vehicle gives its speed;
#: the driver only receives. The road, the vehicle targets and the simulator have no part: the display takes
#: them only as the candidate perceives them.
CONTEXT_PARTS = {
    "candidate": "DriverAssistanceSystem",
    "scorePath": "SCORECommandAndWarningPath",
    "vehicle": "SubjectVehicle",
    "driver": "Driver",
}

#: Names of the driver-assistance increment that the context reuses by reference, each imported singly.
REUSED = {
    DA_FRAMING_PACKAGE: ["DriverAssistanceSystem"],
    DA_PACKAGE: ["VehicleSpeed", "WarningRequest", "CollisionWarning", "SCORECommandAndWarningPath"],
}

#: The story: one use case per scenario, with its identity and its actors. SCENARIO_DOCS pins what the driver sees.
STORY = "hmiDisplayStory"
USE_CASE_DEF = "SuperviseDriverAssistanceOnHmiDisplay"
ALL_ACTORS = ("candidate", "scorePath", "vehicle", "driver")
SCENARIOS = {
    "showWarningInTheWarningScenarios": ("SC-HMI-001", ALL_ACTORS),
    "showNoWarningInTheNoReactionScenarios": ("SC-HMI-002", ("candidate", "vehicle", "driver")),
    "keepSpeedAndWarningWhenTheSceneAppIsOut": ("SC-HMI-003", ALL_ACTORS),
    "showSpeedAndWarningWhileAndroidBoots": ("SC-HMI-004", ALL_ACTORS),
    "keepSpeedAndWarningWhileAndroidHangs": ("SC-HMI-005", ALL_ACTORS),
    "keepSpeedAndWarningThroughAndroidRestart": ("SC-HMI-006", ALL_ACTORS),
    "showWarningUnavailableWhenTheRequestStops": ("SC-HMI-007", ALL_ACTORS),
}
#: The scenarios of the driver-assistance increment that each HMI scenario shows, by reference.
DRIVING_SCENARIOS = {
    "showWarningInTheWarningScenarios": {
        "SC-DRIVING-012": "warnAndBrakeForStationaryVehicle", "SC-DRIVING-013": "warnAndBrakeForSlowerVehicle"},
    "showNoWarningInTheNoReactionScenarios": {
        "SC-DRIVING-014": "noReactionToStationaryVehicleBeyondTheCurve",
        "SC-DRIVING-015": "noReactionToVehicleAheadTurningOff"},
    # the further run of SC-DRIVING-012 in which the Eclipse S-CORE path is stopped (the stop-run decision of
    # 2026-11-18 of the driver-assistance increment), named by reference
    "showWarningUnavailableWhenTheRequestStops": {"SC-DRIVING-012": "warnAndBrakeForStationaryVehicle"},
}

#: The operation: every action with its parameters, in order, and every flow between them.
OPERATION = "HmiDisplayOperation"
ACTIONS = {
    "giveSceneAndWarningRequest": [("out", "perceivedScene", "PerceivedScene"),
                                   ("out", "warningRequest", "WarningRequest")],
    "carryWarningRequestOverSCORE": [("in", "warningRequest", "WarningRequest"),
                                     ("out", "carriedWarningRequest", "WarningRequest")],
    "giveVehicleSpeed": [("out", "vehicleSpeed", "VehicleSpeed")],
    "showOnDisplay": [("in", "perceivedScene", "PerceivedScene"), ("in", "warningRequest", "WarningRequest"),
                      ("in", "vehicleSpeed", "VehicleSpeed"), ("out", "shownContent", "HmiDisplayContent"),
                      ("out", "collisionWarning", "CollisionWarning")],
    "superviseOnDisplay": [("in", "shownContent", "HmiDisplayContent"),
                           ("in", "collisionWarning", "CollisionWarning")],
}
FLOWS = [
    ("giveSceneAndWarningRequest", "warningRequest", "carryWarningRequestOverSCORE", "warningRequest"),
    ("giveSceneAndWarningRequest", "perceivedScene", "showOnDisplay", "perceivedScene"),
    ("carryWarningRequestOverSCORE", "carriedWarningRequest", "showOnDisplay", "warningRequest"),
    ("giveVehicleSpeed", "vehicleSpeed", "showOnDisplay", "vehicleSpeed"),
    ("showOnDisplay", "shownContent", "superviseOnDisplay", "shownContent"),
    ("showOnDisplay", "collisionWarning", "superviseOnDisplay", "collisionWarning"),
]

#: The docs that state the owner's rules (perception only; no element shown as current when it is not) and the aims
#: of the story, pinned whole: a sentence added beside a pinned phrase changes what the slice says.
ITEM_DOCS = {
    "PerceivedScene": (
        "The scene as the candidate gives it from its own perception: its lane, the path it fits to that lane, the "
        "objects it detects with their level relative to its path, and the closest object in its path with the "
        "distance and the speed that its fusion gives. The scene carries its time, as the vehicle speed and the "
        "warning request carry theirs (the scene-time decision of 2026-11-22). It holds nothing that the candidate "
        "does not give: neither the simulator's record of the scene nor an estimate of the display's own "
        "(hmiSimulatorTruthOutOfScope). At the inspected revision the candidate gives no such output "
        "(gapHmiSceneOutput)."),
    "HmiDisplayContent": (
        "What the HMI display shows the driver beside the collision warning: the scene as the candidate gives it, "
        "the vehicle speed, and the fact that the warning is unavailable when it is, with no element shown as "
        "current when it is not (hmiStaleContentInScope). The collision warning itself, on the display and as a "
        "sound, is the collision warning of the driver-assistance increment."),
}
#: The use case definition's doc, its motivation, its trigger and its result, whole: a sentence that adds the
#: simulator's record, or hands this increment the time from the warning request to each mode, fails here.
USE_CASE_DEF_DOC = (
    "The HMI display in operation: in the scenarios of the driver-assistance increment it shows the driver what "
    "the candidate perceives beside the speed and gives the collision warning when the candidate requests it, also "
    "while the app that draws the scene or Android in the IVI VM is out, or while the warning request stops "
    "reaching the display.")
USE_CASE_DEF_MOTIVATION = (
    "The driver, a vehicle occupant, needs to see on the HMI display what the driving application perceives beside the "
    "vehicle speed, to get the collision warning on the display and as a sound, and to see the speed and the warning, "
    "or the fact that the warning is unavailable, also while Android in the IVI VM hangs, boots or restarts.")
USE_CASE_DEF_TRIGGER = (
    "The vehicle drives with the candidate active in a scenario of the driver-assistance increment: the candidate "
    "gives its scene and, when it decides on a warning, its warning request, and the vehicle gives its speed; at "
    "times the app that draws the scene ends or hangs, Android in the IVI VM boots, hangs or restarts, or the warning "
    "request stops reaching the display.")
USE_CASE_DEF_RESULT = (
    "The display shows the scene as the candidate gives it and the speed, gives the collision warning on the "
    "display and as a sound when the warning request arrives, shows no element as current when it is not, and "
    "keeps the speed and the warning, or the fact that the warning is unavailable, apparent while the app that "
    "draws the scene or Android in the IVI VM is out or the warning request stops reaching the display.")
#: The objective of the use case definition. The driver-assistance increment allots the time from the request to
#: each mode; only how that time divides on a path to this display is open (gapHmiWarningPresentation).
USE_CASE_DEF_OBJECTIVE = (
    "Frame what the driver sees in the scenarios of the driver-assistance increment, in each outage in the IVI VM "
    "and while the warning request stops reaching the display, only. How the display detects an outage is for the "
    "system process of phase 6; the criteria, the age from which an element counts as late and how the time that "
    "the driver-assistance increment allots from the warning request to each mode divides "
    "(gapHmiWarningPresentation) are fixed with the requirements (phase 5).")
STORY_OBJECTIVE = (
    "Operate the HMI display without selecting the realization of an element or of a path, and without any "
    "human-factors, safety, on-road, compliance or production-readiness claim.")
#: Each scenario's objective, whole. In every outage the driver sees the speed and the warning, or the fact that the
#: warning is unavailable (hmiAndroidOutageInScope and the story's result), and a last frame is never shown as current.
SCENARIO_DOCS = {
    "showWarningInTheWarningScenarios": (
        "SC-HMI-001 (the warning scenarios of the driver-assistance increment on the display): in SC-DRIVING-012 "
        "and SC-DRIVING-013 the display shows the driver the candidate's lane, the path it fits to that lane and "
        "the objects it detects, the closest object in its path among them with the distance that its fusion "
        "gives, beside the vehicle speed. When the candidate's warning request arrives, the driver gets the "
        "collision warning on the display and as a sound. The display shows the vehicle target as the candidate "
        "perceives it, right or wrong, never as the simulator places it (hmiSimulatorTruthOutOfScope, "
        "hmiPerceptionQualityOutOfScope). No human-factors or safety claim is made."),
    "showNoWarningInTheNoReactionScenarios": (
        "SC-HMI-002 (the no-reaction scenarios of the driver-assistance increment on the display): in "
        "SC-DRIVING-014 and SC-DRIVING-015 the display shows the scene as the candidate gives it, with the objects "
        "that it detects outside its path, beside the vehicle speed, and no warning request arrives, so the driver "
        "gets no collision warning. The display gives a warning only on the candidate's request; whether one is "
        "due is the candidate's decision, which the driver-assistance increment judges "
        "(hmiCandidateChangeOutOfScope). No human-factors or safety claim is made."),
    "keepSpeedAndWarningWhenTheSceneAppIsOut": (
        "SC-HMI-003 (the app that draws the scene is out): during a scenario of the driver-assistance increment "
        "the app that draws the scene ends, or hangs with its last frame on the display. The display shows that "
        "the scene is not current, never the last frame as current (hmiStaleContentInScope), and the driver still "
        "sees the vehicle speed and gets the collision warning on the display and as a sound when the candidate "
        "requests it, or the fact that the warning is unavailable. No human-factors or safety claim is made."),
    "showSpeedAndWarningWhileAndroidBoots": (
        "SC-HMI-004 (Android in the IVI VM boots): during a scenario of the driver-assistance increment, before "
        "Android in the IVI VM gives its first frame, and so before the scene appears, the driver sees the vehicle "
        "speed and the collision warning when the candidate requests it, or the fact that the warning is "
        "unavailable. The scene appears once the app that draws it gives its first frame. Whether the display "
        "learns that the warning is unavailable from the age of its inputs or from a signal of its own is open "
        "(gapHmiWarningAvailability). No human-factors or safety claim is made."),
    "keepSpeedAndWarningWhileAndroidHangs": (
        "SC-HMI-005 (Android in the IVI VM hangs): during a scenario of the driver-assistance increment Android in "
        "the IVI VM hangs and its last frame stays on the display. The display shows that the scene is not "
        "current, never the last frame as current (hmiStaleContentInScope), and the driver sees the vehicle speed "
        "and the collision warning when the candidate requests it, or the fact that the warning is unavailable. No "
        "human-factors or safety claim is made."),
    "keepSpeedAndWarningThroughAndroidRestart": (
        "SC-HMI-006 (Android in the IVI VM restarts): during a scenario of the driver-assistance increment Android "
        "in the IVI VM ends and boots again. From its end until its first frame the display shows no scene as "
        "current, and the driver sees the vehicle speed and the collision warning when the candidate requests it, "
        "or the fact that the warning is unavailable; then the scene appears again. No human-factors or safety "
        "claim is made."),
    "showWarningUnavailableWhenTheRequestStops": (
        "SC-HMI-007 (the warning request stops reaching the display): SC-DRIVING-012 is played once more with the "
        "Eclipse S-CORE path stopped, so the warning request stops reaching the display (the missing-request "
        "decision of 2026-11-22). The display shows that the warning is unavailable and shows no element as "
        "current when it is not (hmiStaleContentInScope), and the driver still sees the vehicle speed. Whether the "
        "display learns that the warning is unavailable from the age of its inputs or from a signal of its own is "
        "open (gapHmiWarningAvailability). No human-factors or safety claim is made."),
}
#: The header's sentence that names the further run of SC-DRIVING-012 and the decision that sets it apart, by
#: reference: the use case itself names neither a run nor the decision.
STOP_RUN_REFERENCE = (
    "The last is the further run of SC-DRIVING-012 in which the Eclipse S-CORE path is stopped, which the stop-run "
    "decision of 2026-11-18 of the driver-assistance increment names.")
#: The guide's sentence on what Phase 5 fixes, and the wording it replaces, which hands Phase 5 a time that the
#: driver-assistance increment allots.
WARNING_TIME_SENTENCE = (
    "The criteria, the age from which an element counts as late and how the time that the driver-assistance "
    "increment allots from the warning request to each mode divides (`gapHmiWarningPresentation`) are fixed with "
    "the requirements in Phase 5.")
WRONG_WARNING_TIME = "time from the warning request to each mode"
#: Any wording of that time, and the form that says whose it is: every mention names the increment that allots it.
WARNING_TIME = re.compile(r"(?i)\bfrom the (?:warning )?request to each mode\b")
ALLOTTED_WARNING_TIME = re.compile(
    r"(?i)\bthe driver-assistance increment allots from the (?:warning )?request to each mode\b")
#: The two content rules over all of the model's prose (its docs, comments and strings). The simulator or the
#: simulation, CARLA and the truth of the scene appear only in sentences that keep them off the display
#: (hmiSimulatorTruthOutOfScope); "current", "live", "stale", "frozen" or "freezes", "up to date" and a last frame
#: only in sentences that never show stale content as current (hmiStaleContentInScope). A claim that uses none of
#: these words is not caught here. The pinned texts give most of these sentences; RULE_SENTENCES are those of the
#: file's header, which is pinned paragraph by paragraph, and of the context's doc and the display's doc.
RULE_TERMS = re.compile(r"(?i)\b(?:simulat\w*|carla|ground[- ]truth|truth|current\w*|live\w*|last frames?|stale\w*"
                        r"|froz\w*|freez\w*|up[- ]to[- ]date)\b")
#: The context doc's sentence on the world outside the display: it reaches the display only through the candidate.
CONTEXT_WORLD_SENTENCE = (
    "The road, the vehicle targets and the simulator reach the display only as the candidate perceives them, so the "
    "context holds no part for them.")
RULE_SENTENCES = (
    "CARLA, the cloud hosts, the scenario runner, the means that make Android in the IVI VM hang, end and restart, the "
    "captures, the evaluators and the recordings are System 2 and stay out of this context.",
    CONTEXT_WORLD_SENTENCE,
    "System 1 roles only: CARLA, the cloud hosts, the scenario runner, the means that make Android in the IVI VM hang, "
    "end and restart, the record of what the candidate gives, the capture of the display and of the sound, the "
    "evaluators and the recordings stay in hmiDisplayVerificationEnvironment.",
    "The HMI display: shows the scene as the candidate gives it and the speed, shows no element as current when it is "
    "not, and gives the collision warning on the display and as a sound when the warning request arrives, or shows "
    "that the warning is unavailable.",
)
#: The names of the two corrections of Phase 2 that come with Phase 4, one wording each wherever it is named.
MISSING_REQUEST = "the missing-request decision of 2026-11-22"
SCENE_TIME = "the scene-time decision of 2026-11-22"
#: Their dated records, the last two paragraphs of the header, in day order.
MISSING_REQUEST_RECORD = (
    "The owner decided on 2026-11-22 that the story gains SC-HMI-007, in which the warning request stops reaching "
    "the display, as a correction of phase 2 that comes with phase 4: the missing-request decision of 2026-11-22.")
SCENE_TIME_RECORD = (
    "The owner decided on 2026-11-22 that the scene carries its time, as the vehicle speed and the warning request "
    "carry theirs, as a correction of phase 2 that comes with phase 4: the scene-time decision of 2026-11-22.")
#: The header's title and the paragraph of the phase, which the two dated records follow.
HEADER_TITLE = "DE4SDV HMI display: Phase 2 operational context."
HEADER_SCOPE = (
    "INC-HMI-001, phase 2: what happens in the world of the HMI display. The candidate application of the "
    "driver-assistance increment gives its scene and its warning request, the Eclipse S-CORE path carries the request, "
    "the vehicle gives its speed, and the display shows the driver the scene and the speed and gives the collision "
    "warning on the display and as a sound. The candidate and the S-CORE path are System 1 parts outside the display, "
    "as phase 0 draws the boundary. The story is the driver-assistance increment's scenarios as the driver sees them "
    "on the display, with the outages in the IVI VM and a warning request that stops reaching the display added to "
    "them; it names those scenarios and restates none of them. The last is the further run of SC-DRIVING-012 in which "
    "the Eclipse S-CORE path is stopped, which the stop-run decision of 2026-11-18 of the driver-assistance increment "
    "names. CARLA, the cloud hosts, the scenario runner, the means that make Android in the IVI VM hang, end and "
    "restart, the captures, the evaluators and the recordings are System 2 and stay out of this context. No "
    "human-factors, timing, safety, compliance or production-readiness claim is made.")
#: The guide's paragraph on the two corrections, after the story of its Phase 2 section, sentence by sentence.
PHASE_TWO_CORRECTIONS = (
    "Two corrections of Phase 2 come with Phase 4.",
    "On 2026-11-22 the owner decided that the story gains `SC-HMI-007`: the missing-request decision of "
    "2026-11-22.",
    "On 2026-11-22 the owner decided that the scene carries its time, as the vehicle speed and the warning request "
    "carry theirs: the scene-time decision of 2026-11-22.",
)
#: The guide's Phase 2 section, whole, sentence by sentence.
GUIDE_PHASE_TWO = (
    "Phase 2 draws the boundary that Phase 0 states and does not move it.",
    "One operational context holds the HMI display as a black box: what it shows and where, the app in the IVI VM "
    "that draws the scene, the high availability renderer in an SDV Media VM, and the paths from the SDV Core VM "
    "to both.",
    "Around it: the candidate application of the driver-assistance increment, which gives its scene and its "
    "warning request; the Eclipse S-CORE path, which carries the warning request; the vehicle, which gives its "
    "speed; and the driver, who only receives.",
    "Nothing flows back to the candidate.",
    "The road, the vehicle targets and the simulator reach the display only as the candidate perceives them, so "
    "the context draws no part for them.",
    "The AAOS SDV guest lies across the boundary, so the context draws no part for it either, and an outage of "
    "Android in the IVI VM is an event inside the black box.",
    "CARLA, the cloud hosts, the scenario runner, the means that make Android in the IVI VM hang, end and restart, "
    "the record of what the candidate gives, the captures, the evaluators and the recordings stay in "
    "`hmiDisplayVerificationEnvironment`.",
    "The context reuses the elements of the driver-assistance increment by reference: it types its parts and items "
    "with `DriverAssistanceSystem`, `SCORECommandAndWarningPath`, `VehicleSpeed`, `WarningRequest` and "
    "`CollisionWarning`, each imported singly, and declares only the scene (`PerceivedScene`) and what the display "
    "shows (`HmiDisplayContent`).",
    "Phase 2 places the source of the vehicle speed at the vehicle; which element of System 1 carries it to the "
    "SDV Core VM, and on which path the scene leaves the candidate's process (`gapHmiSceneOutput`), stay open.",
    "The story holds seven scenarios.",
    "Two are the scenarios of the driver-assistance increment as the driver sees them on the display, each tied to "
    "them by a dependency and none restating them: `SC-HMI-001` the warning scenarios `SC-DRIVING-012` and "
    "`SC-DRIVING-013`, with the scene, the speed and the collision warning on the display and as a sound, and "
    "`SC-HMI-002` the no-reaction scenarios `SC-DRIVING-014` and `SC-DRIVING-015`, with the scene and the speed "
    "and no warning.",
    "Four add an outage in the IVI VM to them: `SC-HMI-003` the app that draws the scene ends or hangs, "
    "`SC-HMI-004` Android in the IVI VM boots, `SC-HMI-005` it hangs with its last frame on the display, and "
    "`SC-HMI-006` it restarts.",
    "One adds a missing input: in `SC-HMI-007` the warning request stops reaching the display during the further run "
    "of `SC-DRIVING-012` that stops the Eclipse S-CORE path, which the stop-run decision of 2026-11-18 of the "
    "driver-assistance increment names, and the display shows that the warning is unavailable.",
    "In each the driver sees the speed and the warning, or the fact that the warning is unavailable, and the "
    "display shows no element as current when it is not.",
    "The display shows what the candidate perceives, never the simulator's record of the scene.",
    "The story states the aim of the engineering question; whether the display achieves it is the verdict of Phase "
    "10.",
    WARNING_TIME_SENTENCE,
    "No human-factors, timing, safety or compliance claim is made.",
    *PHASE_TWO_CORRECTIONS,
    "The context view frames `hmiDisplayContextConcern`.",
    "The story view frames `hmiDisplayStoryConcern` and the Phase 1 concern `hmiDriverSupervisionConcern`, which "
    "the story answers.",
)
#: The one sentence of the next-obligation paragraph that may name the classification of Phase 3: it records no
#: feature-model delta, so the next obligation after Phase 2 is Phase 4.
NEXT_OBLIGATION_PHASE_THREE = (
    "Phase 3, the capability classification, records no feature-model delta, and review judges it: its one blocking "
    "check has nothing to evaluate, so the Method Check lists Phase 3 as vacuous, with a prompt for review.")
#: A Phase 3 classification or record, claimed outside that sentence.
PHASE_THREE_CLAIM = re.compile(r"(?i)\bcommon\b|\bderives? from a member|feature candidate|classif|\bvariant|variab")

#: An affirmative timing, safety or approval claim in words, and an obligation word with no model element behind it.
CLAIM = re.compile(r"(?i)\b(?:deadline|latency|real-time|meets|guarantee[sd]?|ASIL|safe|freedom from interference"
                   r"|must|shall)\b")
#: A number of the driver-assistance increment's interface or timing: its form stays that increment's.
NUMBER = re.compile(r"\d")
#: identities, phase and system numbers and view depths, which are no number of an interface
IDENTITY = re.compile(r"\b(?:SC|INC|REQ|N)-[A-Z]+-\d{3}\b|\b[Pp]hases? \d+(?: (?:to|and) \d+)?\b|\bSystem [12]\b"
                      r"|\battribute depth = [12];|DE4SDV|\b(?:2026-11-\d\d|ADR 00\d\d)\b")


def _raw() -> str:
    assert MODEL.is_file(), "phase 2 of INC-HMI-001 needs an operational context model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _top(body: str) -> str:
    """The text of a body at its own depth: the contents of nested blocks are dropped, whatever the indentation."""
    kept, depth = [], 0
    for char in body:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif depth == 0:
            kept.append(char)
    return "".join(kept)


def _package() -> str:
    return _top(braced_body(_code(), f"package {PACKAGE}"))


def _flat(text: str) -> str:
    return " ".join(text.split())


def _prose(text: str) -> str:
    return _flat(re.sub(r"(?m)^\s*\*\s?", "", text))


def _doc(raw: str, declaration: str) -> str:
    body = braced_body(raw, declaration)
    match = re.search(r"\bdoc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration} has a doc"
    return _prose(match.group(1))


def _objective(raw: str, declaration: str) -> str:
    body = braced_body(braced_body(raw, declaration), "objective")
    match = re.search(r"\bdoc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"the objective of {declaration} has a doc"
    return _prose(match.group(1))


def _comment(raw: str, name: str) -> str:
    match = re.search(rf"comment {name} about [\w:]+\s*/\*(.*?)\*/", raw, re.S)
    assert match, f"the comment {name}"
    return _prose(match.group(1))


def _model_sentences() -> list:
    raw = _raw()
    texts = [_prose(match.group(1)) for match in re.finditer(r"/\*(.*?)\*/", raw, re.S)]
    texts += [match.group(1) for match in re.finditer(r'=\s*"([^"]*)"', raw)]
    return [sentence for text in texts for sentence in re.split(r"(?<=[.?!])\s+", text) if sentence]


def _guide_section() -> str:
    section = re.search(r"(?ms)^## Operational context and story \(Phase 2\)\n(.*?)(?=^## )",
                        GUIDE.read_text(encoding="utf-8"))
    assert section, "the guide has a Phase 2 section"
    return _flat(section.group(1))


def test_the_increment_has_exactly_one_operational_context_named_in_the_charter():
    code = _code()
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", code) == [PACKAGE], "one global package per file"
    contexts = re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", code)
    contexts += re.findall(r"\bpart\s+(\w+)\s*:\s*SystemContext\b", framing)
    assert contexts == [CONTEXT]
    charter = braced_body(framing, "part hmiDisplayCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    # the framing test pins the whole list; later phases append their packages after this one
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[:2] == [FRAMING_PACKAGE, PACKAGE]


def test_the_system_of_interest_is_the_charter_display_as_a_black_box():
    code = _code()
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    charter = braced_body(framing, "part hmiDisplayCharter : IncrementCharter")
    soi_usage = re.search(r"systemOfInterest\s*=\s*(\w+)\s*;", charter).group(1)
    assert re.search(rf"\bpart\s+{soi_usage}\s*:\s*{SOI_TYPE}\s*;", framing), "the charter's system is the display"
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    assert re.search(rf"\bpart\s+{SOI}\s*:\s*{SOI_TYPE}\s*:>>\s*systemOfInterest\s*;", context)
    assert not re.search(rf"\bpart\s+{SOI}\s*:[^;{{]*\{{", context), "the system of interest declares no parts here"
    parts = dict(re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)", _top(context)))
    assert parts == {SOI: SOI_TYPE, **CONTEXT_PARTS}
    for name in CONTEXT_PARTS:
        assert not re.search(r"\bpart\b", braced_body(context, f"part {name} :").split("*/", 1)[-1]), \
            f"{name} owns no nested part"


def test_the_boundary_drawn_in_phase_zero_holds():
    raw = _raw()
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    for name, type_name in re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)", context):
        if name == SOI:
            continue
        assert not re.search(r"(?i)renderer|\bhar\b|ivi|media|android|guest|aaos|scene|app\b|display",
                             f"{name} {type_name}"), f"{name}: an element of the display is drawn in the context"
        assert not re.search(r"(?i)target|road|carla|simulat|truth", f"{name} {type_name}"), \
            f"{name}: the display takes the world only as the candidate perceives it"
    doc = _doc(raw, f"part {CONTEXT} : SystemContext")
    for phrase in ("Inside the system of interest, as phase 0 draws it: what the display shows and where, the app "
                   "in the IVI VM that draws the scene, the high availability renderer in an SDV Media VM",
                   "The candidate and the S-CORE path are System 1 parts outside the display and no enabling "
                   "systems.",
                   "the driver, who only receives",
                   CONTEXT_WORLD_SENTENCE,
                   "This is the operational environment, not a deployment decomposition."):
        assert phrase in doc, phrase
    for package, names in REUSED.items():
        for name in names:
            assert f"private import {package}::{name};" in code, f"{name} is imported singly"
            assert not re.search(rf"\b(?:part|item)\s+def\s+{name}\b", code), f"reuse {name}, never redeclare it"
        assert not re.search(rf"\bprivate\s+import\s+{package}::\*", code), f"only single names of {package}"
    assert not re.search(r"\bDE4SDV_DriverAssistance(?:CapabilityClassification|NeedsRequirements|"
                         r"FunctionalArchitecture|LogicalArchitecture|PhysicalSoftwareRealization|"
                         r"VariabilityConfiguration|VerificationEvidence)\b", code), \
        "phase 2 reads no later phase of INC-DRIVING-002"
    assert re.findall(r"\b(?:part|item|action|use case)\s+def\s+(\w+)", code) == [
        "PerceivedScene", "HmiDisplayContent", OPERATION, USE_CASE_DEF], \
        "two new items, the operation and the use case definition; every role is reused"
    assert not re.search(r"\bconcern def\b|\bviewpoint def\b|\bpart def\b", code)


def test_the_scene_is_perception_only_and_nothing_flows_back_to_the_candidate():
    raw = _raw()
    # whole docs: a sentence that adds the simulator's record, or a late element shown as current, fails here
    for name, expected in ITEM_DOCS.items():
        assert _doc(raw, f"item def {name}") == expected, name
    candidate = _doc(raw, "part candidate : DriverAssistanceSystem")
    assert "the display sends it nothing (hmiCandidateChangeOutOfScope)." in candidate
    assert "the speed that the candidate is given" in _doc(raw, "part vehicle : SubjectVehicle")
    assert "carries the candidate's warning request to the SDV Core VM" in \
        _doc(raw, "part scorePath : SCORECommandAndWarningPath")


def test_context_and_story_hold_system_one_roles_only():
    raw = _raw()
    code = _code()
    context = braced_body(code, f"part {CONTEXT} : SystemContext")
    forbidden = (r"\b(?:System2\w*|DE4SDVEvidenceBaseline|OpenSourceReviewer|VerificationEngineer|\w*Capture\w*"
                 r"|\w*Recorder\w*|\w*Recording\w*|\w*Evaluator\w*|\w*Host\w*|\w*Injector\w*|\w*Runner\w*"
                 r"|\w*Carla\w*|\w*CARLA\w*|hmiDisplayVerificationEnvironment)\b")
    assert not re.search(forbidden, context), "capture, recording and evaluator roles belong to System 2"
    for name in (STORY, *SCENARIOS):
        assert not re.search(forbidden, braced_body(code, f"use case {name}")), name
        assert not re.search(r"(?i)\b(?:carla|recording|recorded|capture[sd]?|injection|injected|runs?)\b",
                             braced_body(raw, f"use case {name}")), f"{name}: no System 2 term in the scenario"
    assert not re.search(
        r"\b(?:part|item|concern|use case) def (?:SubjectVehicle|Driver|SystemContext|OperationalEntity"
        r"|HmiDisplaySystem|DriverAssistanceSystem)\b", code), "kernel and framing names are used, never shadowed"
    assert "hmiDisplayVerificationEnvironment" in _doc(raw, f"part {CONTEXT} : SystemContext"), \
        "the context doc says where System 2 stays"


def test_every_use_case_binds_its_subject_and_actors_to_the_context():
    code = _code()
    #: the context's top-level parts, name -> type, read from the model: a bound part must exist there with its type
    context_parts = dict(re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)",
                                    _top(braced_body(code, f"part {CONTEXT} : SystemContext"))))
    usages = re.findall(r"\buse case\s+(?!def\b)(\w+)", _package())
    assert sorted(usages) == sorted([STORY, *SCENARIOS])
    expected_actors = {STORY: ALL_ACTORS, **{name: actors for name, (_id, actors) in SCENARIOS.items()}}
    for name in usages:
        body = braced_body(code, f"use case {name}")
        assert re.search(rf"\bsubject\s+{SOI}\s*:\s*{SOI_TYPE}\s*=\s*{CONTEXT}::{SOI}\s*;", body), \
            f"{name}: the subject is the context's system of interest"
        declared = re.findall(r"\bactor\s+(\w+)\s*:", body)
        actors = re.findall(rf"\bactor\s+(\w+)\s*:\s*(\w+)\s*=\s*{CONTEXT}::(\w+)\s*;", body)
        assert len(actors) == len(declared), f"{name}: every actor is bound to a context part"
        assert [a for a, _t, _p in actors] == list(expected_actors[name]), f"{name}: its actors, in order"
        for actor, type_name, part in actors:
            assert actor == part and context_parts.get(part) == type_name == CONTEXT_PARTS[part], \
                f"{name}: actor {actor} is bound to the top-level context part of its own type"
    assert context_parts.get(SOI) == SOI_TYPE
    assert f"use case def {USE_CASE_DEF} :> SYSMODSystemUseCaseBase" in code
    use_case_def = braced_body(code, f"use case def {USE_CASE_DEF} :> SYSMODSystemUseCaseBase")
    for slot in ("ucMotivation", "ucTrigger", "ucResult"):
        assert re.search(rf"\battribute\s+redefines\s+{slot}\s*=\s*\"[^\"]+\"\s*;", use_case_def), slot
    motivation = re.search(r'ucMotivation\s*=\s*"([^"]+)"', use_case_def).group(1)
    assert motivation == USE_CASE_DEF_MOTIVATION, "the story states the driver's need of phase 1's operational concern"
    # the trigger and the result whole: perception only, and no element shown as current when it is not
    assert re.search(r'ucTrigger\s*=\s*"([^"]+)"', use_case_def).group(1) == USE_CASE_DEF_TRIGGER
    assert re.search(r'ucResult\s*=\s*"([^"]+)"', use_case_def).group(1) == USE_CASE_DEF_RESULT
    assert re.search(rf"\buse case\s+{STORY}\s*:\s*{USE_CASE_DEF}\s*\{{", code)
    raw = _raw()
    assert _doc(raw, f"use case def {USE_CASE_DEF}") == USE_CASE_DEF_DOC
    assert _objective(raw, f"use case def {USE_CASE_DEF}") == USE_CASE_DEF_OBJECTIVE
    assert _objective(raw, f"use case {STORY} :") == STORY_OBJECTIVE


def test_the_story_holds_the_seven_scenarios():
    raw = _raw()
    code = _code()
    story = braced_body(code, f"use case {STORY} : {USE_CASE_DEF}")
    assert re.findall(r"\binclude\s+(\w+)\s*;", story) == list(SCENARIOS)
    assert re.search(r"\bfirst\s+start\s*;", story) and re.search(r"\bthen\s+done\s*;", story)
    for name, (scenario_id, _actors) in SCENARIOS.items():
        # the objective whole: its identity, what the driver sees, the alternative of every outage and the nonclaim
        assert _doc(raw, f"use case {name}") == SCENARIO_DOCS[name], f"{name} ({scenario_id}): the whole objective"
    ids = re.findall(r"SC-HMI-\d{3}", raw)
    assert sorted(set(ids)) == sorted(s[0] for s in SCENARIOS.values()), "only the seven new scenario identities"
    # the further run of SC-DRIVING-012 is named in the header, by reference, never restated
    header = _prose(raw.split("\npackage ", 1)[0])
    assert STOP_RUN_REFERENCE in header
    assert "with the outages in the IVI VM and a warning request that stops reaching the display added to them; it " \
        "names those scenarios and restates none of them." in header
    frame = GUIDE.read_text(encoding="utf-8").split("## Authoritative frame", 1)[1].split("\n## ", 1)[0]
    assert "its story of seven scenarios." in _flat(frame), "the guide's frame counts the scenarios"
    da_ids = set(re.findall(r"SC-DRIVING-\d{3}", raw))
    assert da_ids == {i for refs in DRIVING_SCENARIOS.values() for i in refs}, "the four reused scenarios only"


def test_the_driving_scenarios_are_reused_by_reference_never_restated():
    raw = _raw()
    code = _code()
    da = DA_CONTEXT.read_text(encoding="utf-8")
    deps = re.findall(r"\bdependency\s+(\w+)\s+from\s+([\w:]+)\s+to\s+([\w:]+)\s*;", code)
    for name, references in DRIVING_SCENARIOS.items():
        doc = _doc(raw, f"use case {name}")
        for scenario_id, use_case in references.items():
            assert scenario_id in doc, f"{name} names {scenario_id}"
            assert scenario_id in _doc(da, f"use case {use_case}"), f"{use_case} is {scenario_id}"
            assert [d for d in deps if d[1] == name and d[2] == f"{DA_PACKAGE}::{use_case}"], \
                f"{name} depends on {use_case}"
    assert [d for d in deps if d[1] == STORY and d[2] == f"{DA_PACKAGE}::driverAssistanceStory"], \
        "the story plays in the driver-assistance story"
    # no sentence of a driving scenario is copied: its conditions stay that increment's. A span that this
    # increment's own framing already says (the warning "on the display and as a sound") is its own wording.
    # The driving story's own texts are scanned too: the definition's doc, its slots and objective, and the
    # story's objective.
    # The comparison ignores case, both for a copy and for the framing's own wording.
    own = _prose(FRAMING.read_text(encoding="utf-8")).lower()
    prose = _prose(raw).lower()
    da_def = f"use case def {DA_USE_CASE_DEF} :> SYSMODSystemUseCaseBase"
    reused = sorted({u for refs in DRIVING_SCENARIOS.values() for u in refs.values()})
    da_texts = [_doc(da, f"use case {u}") for u in reused]
    da_texts.append(_doc(da, da_def))
    for slot in ("ucMotivation", "ucTrigger", "ucResult"):
        da_texts.append(re.search(rf'\b{slot}\s*=\s*"([^"]+)"', braced_body(da, da_def)).group(1))
    da_texts += [_objective(da, da_def), _objective(da, f"use case {DA_STORY} :")]
    assert len(da_texts) == 10, "four scenarios, the definition's doc, three slots and two objectives"
    for da_doc in da_texts:
        for sentence in re.split(r"(?<=[.;:])\s+", da_doc):
            words = sentence.split()
            for start in range(max(0, len(words) - 7)):
                span = " ".join(words[start:start + 8]).lower()
                assert span not in prose or span in own, f"copied from the driving story: {span}"
    for phrase in ("highway", "guard pipes", "fair weather", "roadwork", "turns off", "regulation"):
        assert phrase not in raw, f"a condition of the driving scenarios is restated: {phrase}"


def test_the_boundary_flows_cross_in_the_drawn_directions():
    raw = _raw()
    code = _code()
    operation = braced_body(code, f"action def {OPERATION}")
    flows = re.findall(r"\bflow\s+from\s+(\w+)\.(\w+)\s+to\s+(\w+)\.(\w+)\s*;", operation)
    assert not [f for f in flows if f[2] == "giveSceneAndWarningRequest"], "nothing flows back to the candidate"
    assert not [f for f in flows if f[2] == "giveVehicleSpeed"], "nothing flows back to the vehicle"
    assert not [f for f in flows if f[0] == "superviseOnDisplay"], "the driver only receives"
    assert {(s, i) for s, i, t, _ in flows if t == "showOnDisplay"} == {
        ("giveSceneAndWarningRequest", "perceivedScene"), ("carryWarningRequestOverSCORE", "carriedWarningRequest"),
        ("giveVehicleSpeed", "vehicleSpeed")}, "the display takes the scene, the request and the speed, no other"
    assert sorted(flows) == sorted(FLOWS), "exactly the flows of the drawn boundary"
    assert re.findall(r"\baction\s+(\w+)\s*\{", operation) == list(ACTIONS)
    for action, parameters in ACTIONS.items():
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", braced_body(operation, f"action {action}")) == \
            parameters, action
    assert re.search(rf"\baction\s+hmiDisplayOperation\s*:\s*{OPERATION}\s*;", code)
    assert "Nothing flows back to the candidate, to the path or to the vehicle." in \
        _doc(raw, f"action def {OPERATION}")


def test_operational_views_frame_operational_concerns_and_expose_phase_two():
    raw = _raw()
    code = _code()
    framing = FRAMING.read_text(encoding="utf-8")
    expected = {
        "hmiDisplayOperationalContextView": (
            "OperationalContextDefinitionViewpoint", ["hmiDisplayContextConcern"],
            "OperationalContextConcern", {CONTEXT, f"{CONTEXT}::*", "hmiDisplayOperation"}, "2"),
        "hmiDisplayOperationalStoryView": (
            "OperationalStoryViewpoint", ["hmiDisplayStoryConcern", "hmiDriverSupervisionConcern"],
            "OperationalStoryConcern", {STORY, f"{STORY}::*"}, "1"),
    }
    assert re.findall(r"\bview\s+(\w+)", _package()) == list(expected)
    assert re.search(r"\bconcern\s+hmiDriverSupervisionConcern\s*:\s*OperationalCapabilityConcern\b",
                     strip_comments(framing)), "the story view's second frame is phase 1's operational concern"
    assert "Answered by the operational story of phase 2." in " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(
        framing, "concern hmiDriverSupervisionConcern : OperationalCapabilityConcern")).split())
    for view_name, (viewpoint, frames, concern_type, exposed, depth) in expected.items():
        view = braced_body(code, f"view {view_name}")
        assert re.search(rf"\bviewpoint\s+\w+\s*:\s*{viewpoint}\s*\{{", view), view_name
        assert re.findall(r"\bframe\s+([\w:]+)\s*;", view) == frames, view_name
        assert set(re.findall(r"\bexpose\s+([\w:*]+)\s*;", view)) == exposed, view_name
        assert re.search(rf"\battribute\s+depth\s*=\s*{depth}\s*;", view), view_name
        assert re.search(r"\battribute\s+showAnnotationRows\s*=\s*false\s*;", view), view_name
        assert re.search(r"\brender\s+asTreeDiagram\s*;", view), view_name
        concern_body = braced_body(code, f"concern {frames[0]} : {concern_type}")
        lines = [line.strip() for line in concern_body.splitlines() if line.strip() and line.strip() != "doc"]
        assert lines[0] == "subject;", frames[0]
    holders = {
        "hmiDisplayContextConcern": [("systemArchitect", "SystemArchitect"), ("systemsEngineer", "SystemsEngineer"),
                                     ("reviewer", "OpenSourceReviewer")],
        "hmiDisplayStoryConcern": [("systemsEngineer", "SystemsEngineer"),
                                   ("verificationEngineer", "VerificationEngineer"),
                                   ("reviewer", "OpenSourceReviewer")],
    }
    concern_types = {"hmiDisplayContextConcern": "OperationalContextConcern",
                     "hmiDisplayStoryConcern": "OperationalStoryConcern"}
    assert re.findall(r"\bconcern\s+(\w+)\s*:", code) == list(holders)
    for concern, stakeholders in holders.items():
        body = braced_body(code, f"concern {concern} : {concern_types[concern]}")
        assert re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body) == stakeholders, concern
    # each concern doc holds only its pinned sentences
    assert _doc(raw, "concern hmiDisplayContextConcern : OperationalContextConcern") == (
        "System architects, systems engineers and open-source reviewers need to see what is inside the HMI "
        "display and what is around it: the candidate application, the Eclipse S-CORE path, the vehicle and the "
        "driver, and which item crosses the boundary in which direction. The candidate and the S-CORE path are "
        "outside; the driver only receives; nothing flows back to the candidate.")
    assert _doc(raw, "concern hmiDisplayStoryConcern : OperationalStoryConcern") == (
        "Systems engineers, verification engineers and open-source reviewers need the HMI display told in "
        "stakeholder language: what the driver sees in the scenarios of the driver-assistance increment, with and "
        "without a warning, while the app that draws the scene or Android in the IVI VM is out, and while the "
        "warning request stops reaching the display.")


def test_dependencies_trace_the_story_and_the_context_to_phase_zero():
    raw = _raw()
    code = _code()
    deps = re.findall(r"\bdependency\s+(\w+)\s+from\s+([\w:]+)\s+to\s+([\w:]+)\s*;", code)
    phase_zero = {(name, client, supplier) for name, client, supplier in deps
                  if supplier.startswith(FRAMING_PACKAGE + "::")}
    assert phase_zero == {
        ("hmiDisplayStoryAnswersProblem", STORY, f"{FRAMING_PACKAGE}::hmiDisplayProblem"),
        ("candidateOnDrivingBenchReuse", f"{CONTEXT}::candidate", f"{FRAMING_PACKAGE}::asmHmiDrivingBenchReuse"),
        ("scorePathOnDrivingBenchReuse", f"{CONTEXT}::scorePath", f"{FRAMING_PACKAGE}::asmHmiDrivingBenchReuse"),
        ("perceivedSceneOnSceneOutputGap", "PerceivedScene", f"{FRAMING_PACKAGE}::gapHmiSceneOutput"),
        ("perceivedSceneOnSceneContentGap", "PerceivedScene", f"{FRAMING_PACKAGE}::gapHmiSceneContent"),
        ("outageScenariosOnWarningAvailabilityGap", STORY, f"{FRAMING_PACKAGE}::gapHmiWarningAvailability"),
        # what the display shows carries the fact that the warning is unavailable, which the gap leaves open
        ("hmiDisplayContentOnWarningAvailabilityGap", "HmiDisplayContent",
         f"{FRAMING_PACKAGE}::gapHmiWarningAvailability"),
    }
    driving = [d for d in deps if d[2].startswith(DA_PACKAGE + "::")]
    assert len(deps) == len(phase_zero) + len(driving) == 7 + 6, "seven phase 0 traces and six scenario references"
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    for _, _, supplier in phase_zero:
        name = supplier.split("::")[-1]
        assert re.search(rf"\b(?:requirement|part)\s+{name}\s*:", framing), f"{name} is a phase 0 record"
    abouts = re.findall(r"\bcomment\s+(\w+)\s+about\s+([\w:]+)", raw)
    assert abouts == [("vehicleSpeedSourceComment", f"{FRAMING_PACKAGE}::hmiSpeedInScope"),
                      ("sceneOutputComment", f"{FRAMING_PACKAGE}::gapHmiSceneOutput"),
                      ("guestAcrossBoundaryComment", f"{FRAMING_PACKAGE}::gapHmiMemberGuestLayout")]
    speed = _comment(raw, "vehicleSpeedSourceComment")
    for phrase in ("Phase 2 places the source of the vehicle speed: the vehicle gives the display the speed that "
                   "it gives the candidate; phase 3 places no element, so the carrier, a platform element of System 1 "
                   "that brings the speed to the SDV Core VM, goes to the architecture phases.",
                   "this context draws no path for the speed."):
        assert phrase in speed, phrase
    scene = _comment(raw, "sceneOutputComment")
    for phrase in ("which the candidate does not give at the inspected revision",
                   "this context changes nothing of what the candidate perceives, plans, requests or commands."):
        assert phrase in scene, phrase
    guest = _comment(raw, "guestAcrossBoundaryComment")
    for phrase in ("The AAOS SDV guest lies across the boundary",
                   "an outage of Android in the IVI VM is an event inside the black box",
                   "This context changes neither the guest layout nor"):
        assert phrase in guest, phrase


def test_the_package_declares_no_name_that_another_model_package_declares():
    kinds = (r"(?:part def|item def|action def|use case def|part|item|action|use case|concern|view|dependency"
             r"|comment)")
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(\w+)", _code()))
    assert len(declared) >= 25, "the population of the check must not be vacuous"
    anywhere = re.compile(rf"\b{kinds}\s+(\w+)")
    taken: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == MODEL:
                continue
            for name in anywhere.findall(strip_comments(path.read_text(encoding="utf-8"))):
                if name in declared:
                    taken.setdefault(name, []).append(path.name)
    assert not taken, f"declared in another package too: {taken}"


def test_phase_two_makes_no_timing_safety_or_approval_claim_and_names_no_number():
    from test_hmi_display_framing import APPROVAL
    texts = {MODEL.name: _raw(), "the guide's Phase 2 section": _guide_section()}
    for name, text in texts.items():
        for sentence in re.split(r"(?<=[.;:])\s+", _flat(re.sub(r"(?m)^\s*\*\s?", " ", text))):
            # only the precedent's nonclaims are skipped: a sentence that begins "No timing" or says "without any
            # timing"; a guard test gets no broader phrase exemption
            if sentence.startswith("No timing") or "without any timing" in sentence:
                continue
            assert not APPROVAL.search(sentence), f"{name} makes an approval claim: {sentence}"
            assert not CLAIM.search(sentence), f"{name} makes a timing, safety or obligation claim: {sentence}"
            assert not NUMBER.search(re.sub(IDENTITY, "", sentence)), f"{name} names a number: {sentence}"


def test_the_guide_has_a_phase_two_section():
    guide = GUIDE.read_text(encoding="utf-8")
    assert ("**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability "
            "classification, Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase "
            "7 logical architecture, Phase 8 physical and software realization, Phase 9 variability and configuration "
            "and the first slice of Phase 10 verification and evidence, proposal.**") in _flat(guide)
    assert "](../../textual-notation-of-model/packages/features/hmi/hmi_display_operational_context.sysml)" in guide
    assert guide.index("## Concerns (Phase 1)") < guide.index("## Operational context and story (Phase 2)") \
        < guide.index("## What the framing already records as open")
    flat = _guide_section()
    # the section whole: a Phase 3 claim or a ground-truth claim added between pinned phrases fails here
    assert flat == " ".join(GUIDE_PHASE_TWO)
    # the time from the warning request to each mode is the driver-assistance increment's; only its division on
    # the path to this display waits for Phase 5
    assert WARNING_TIME_SENTENCE in flat
    assert WRONG_WARNING_TIME not in _flat(guide) and WRONG_WARNING_TIME not in _prose(_raw())


def test_every_mention_of_the_warning_time_says_that_the_driver_assistance_increment_allots_it():
    # whatever the wording: a sentence of the model (its docs, comments and strings) or of the guide's Phase 2 section
    # that speaks of the time from the (warning) request to each mode says, at each mention, whose time it is
    texts = {MODEL.name: _prose(_raw()), "the guide's Phase 2 section": _guide_section()}
    for name, text in texts.items():
        mentions = 0
        for sentence in re.split(r"(?<=[.?!])\s+", text):
            found = len(WARNING_TIME.findall(sentence))
            mentions += found
            assert found == len(ALLOTTED_WARNING_TIME.findall(sentence)), \
                f"{name}: the time from the request to each mode is the driver-assistance increment's: {sentence}"
        assert mentions >= 1, f"{name} names the time, so the check is not vacuous"


def test_the_simulator_and_stale_content_appear_only_in_the_rule_sentences():
    # whatever text a sentence is added to (a doc, a comment or a string): when it names the simulator or the
    # simulation, CARLA, the truth of the scene, stale content or a last frame, it is a pinned sentence that keeps
    # them off the display
    pinned = (*ITEM_DOCS.values(), *SCENARIO_DOCS.values(), USE_CASE_DEF_DOC, USE_CASE_DEF_MOTIVATION,
              USE_CASE_DEF_TRIGGER, USE_CASE_DEF_RESULT, USE_CASE_DEF_OBJECTIVE, STORY_OBJECTIVE, *RULE_SENTENCES)
    allowed = {sentence for text in pinned for sentence in re.split(r"(?<=[.?!])\s+", text)}
    named = [sentence for sentence in _model_sentences() if RULE_TERMS.search(sentence)]
    for sentence in named:
        assert sentence in allowed, f"names the simulator or stale content outside the rule sentences: {sentence}"
    assert set(RULE_SENTENCES) <= set(named), "every listed rule sentence is in the model"


def test_the_guide_names_the_next_obligation_after_phase_two():
    flat = _flat(GUIDE.read_text(encoding="utf-8").split("## Next obligation and execution limits", 1)[1]
                 .split("\n## ", 1)[0])
    # Phase 3 is judged by review and has nothing to evaluate: only its one sentence names the classification, and
    # nothing in the section claims it or names the simulator
    assert flat.count(NEXT_OBLIGATION_PHASE_THREE) == 1
    rest = flat.replace(NEXT_OBLIGATION_PHASE_THREE, "")
    assert not PHASE_THREE_CLAIM.search(rest), PHASE_THREE_CLAIM.search(rest)
    assert "simulator" not in rest
    for phrase in ("The next model obligation is **Phase 10**: verification and evidence, its second slice, which "
                   "follows the readiness probes and adds the bench, the runs, the retained records and the statuses. "
                   "The first slice holds the cases that `verificationCaseVerifiesRequirement` and "
                   "`requirementVerifiedByVerificationCase` read; `verificationCaseHasEvidenceRecordOrStatus` stays "
                   "advisory until runs exist. With those two checks met, the first open blocking check of the Method "
                   "Check is Phase 11's `incrementHasBaselineDecision`. Do not jump from the cases to implementation "
                   "before the probes, and claim no runtime gate.",
                   "Phase 3 and later phases waited for the revision of the governed scope, which the model now "
                   "holds"):
        assert phrase in flat, phrase
    assert "The next model obligation is **Phase 2**" not in flat
    assert "The next model obligation is **Phase 3**" not in flat
    assert "The next model obligation is **Phase 4**" not in flat
    assert "The next model obligation is **Phase 5**" not in flat
    assert "The next model obligation is **Phase 6**" not in flat
    assert "The next model obligation is **Phase 7**" not in flat
    assert "The next model obligation is **Phase 8**" not in flat
    assert "Phase 3 and later phases wait for the revision" not in flat, "the scope revision ended the wait"


def test_the_two_corrections_of_phase_2_are_recorded_in_day_order_under_one_name_each():
    raw = _raw()
    header = _prose(raw.split("\npackage ", 1)[0]).removesuffix("/").strip()
    assert header.endswith(f"{MISSING_REQUEST_RECORD} {SCENE_TIME_RECORD}"), \
        "the two dated records close the header, the missing-request decision first"
    assert header.count(MISSING_REQUEST_RECORD) == 1 and header.count(SCENE_TIME_RECORD) == 1
    prose = _prose(raw)
    assert prose.count(MISSING_REQUEST) == 2, "the record and the objective of SC-HMI-007 name it"
    assert prose.count(SCENE_TIME) == 2, "the record and the doc of PerceivedScene name it"
    assert MISSING_REQUEST in SCENARIO_DOCS["showWarningUnavailableWhenTheRequestStops"]
    assert SCENE_TIME in ITEM_DOCS["PerceivedScene"]
    guide = _flat(GUIDE.read_text(encoding="utf-8"))
    section = _guide_section()
    for name in (MISSING_REQUEST, SCENE_TIME):
        assert section.count(name) == 1 and guide.count(name) == 1, name
    # one wording of each correction: no other wording dates an amendment or a correction
    assert not re.search(r"(?i)\b(?:amend\w*|correct\w*) (?:on|of) 2026-11-22", prose + " " + guide)


def _header_paragraphs(raw: str) -> list[str]:
    head = raw.split("\npackage ", 1)[0].strip()
    assert head.startswith("/*") and head.endswith("*/"), "the file opens with its header"
    return [_prose(part) for part in re.split(r"\n\s*\*\s*\n", head[2:-2])]


def test_the_header_is_pinned_paragraph_by_paragraph():
    # The title, the paragraph of the phase and the two dated records, each whole and in this order. Prose added to
    # the header in other words, a quotation or another dating of a correction, fails here and is for review.
    assert _header_paragraphs(_raw()) == [HEADER_TITLE, HEADER_SCOPE, MISSING_REQUEST_RECORD, SCENE_TIME_RECORD]
