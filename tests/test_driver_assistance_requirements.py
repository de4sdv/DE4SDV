"""Content pins for the driver-assistance requirements (INC-DRIVING-002, phase 5), not semantic validation.

Phase 5 derives the design-input requirements of the candidate driver-assistance system from the four needs of
phase 4. The SpecifyRequirements rules of the increment workflow are checked by Method Check; these pins hold what
review settled on top of them:

- the requirement set itself, each with its need, its kind and its verification method, within the charter's
  scope cap of at most ten requirements;
- requirement-writing rules: one obligation per statement (one `shall`, at most 60 words), the positive form, and
  the terms the statements use defined once in the package, exactly these terms;
- the imminence of a collision quantified in the terms, by a time to collision and a needed deceleration (owner
  decision of 2026-11-14), never by a list of test runs;
- the criteria for a vehicle target, each derived from the source regulation and a product-line requirement, with
  whose obligation it is and what a simulation cannot show of it; a setting counts only when both of its runs are
  judged;
- the further run with the S-CORE path stopped, no run of a setting and no judged run, read only by the stop clauses
  of REQ-DRIVING-038 and REQ-DRIVING-043 (the stop-run decision of 2026-11-18, recorded in the package head);
- the no-autopilot, replay or overlay condition of the planned reviews as a success criterion, never as wording of
  a statement;
- the time of the warning request before the emergency braking in simulation time, its share for the path and the
  AAOS SDV in wall-clock time;
- the phase 4 comment on the VisionPilot contract replaced by the rationales;
- one requirement definition table, the one view the method names for phase 5, which answers the criteria
  concern of the framing;
- the guide's phase 5 section, its numbers, the kinds it names and the next obligation, phase 6;
- the upstream record, which gives each file that a rationale cites with its path, the cited lines inside its
  link, and what each of those lines does;
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
    "reqDetectableDrivingCommand": ("REQ-DRIVING-039", "needWarnAndBrakeForVehicleAhead", R, "analyze"),
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
    "reqDetectableDrivingCommand": "NEED-DRIVING-008; REQ-MW-006; gap gapNoSeparateEmergencyFunction; emergencyBrakingIndependenceConcern",
    "reqWithholdWarningRequest": "NEED-DRIVING-009; SRC-UNECE-R152 false reaction avoidance; REQ-AEBS-008; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-012 to SC-DRIVING-015",
    "reqWithholdEmergencyBraking": "NEED-DRIVING-009; SRC-UNECE-R152 false reaction avoidance; REQ-AEBS-012; gap gapVehicleTargetCriteria; scenarios SC-DRIVING-012 to SC-DRIVING-015",
    "reqWarningRequestBeforeEmergencyBraking": "NEED-DRIVING-010; SRC-UNECE-R152 collision warning; REQ-AEBS-002; gap gapWarningOutput; scenarios SC-DRIVING-012 and SC-DRIVING-013",
    "reqWarningRequestOverSCORE": "NEED-DRIVING-010; scope item scoreCommandPathInScope; gaps gapWarningOutput and gapScoreIntegration; scenarios SC-DRIVING-012 and SC-DRIVING-013",
    "reqRecordCandidateIdentity": "NEED-DRIVING-011; gap gapCandidateBehaviorUnverified; scenarios SC-DRIVING-012 to SC-DRIVING-015",
}

#: requirement -> the fragments its statement, its rationale and its success criteria must carry
FRAGMENTS = {
    "reqEmergencyBrakingForImminentCollision": {
        "statement": ("While the needed deceleration to a vehicle ahead is at least 5.0 m/s²",
                       "shall command a deceleration of at least 5.0 m/s²"),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-003", "014e0e7a", "planning.cpp:118",
                       "longitudinal_planning.cpp:36", "vision_pilot.cpp:138, 157, 174",
                       "Up to a closing speed of 144 km/h a needed deceleration of 5.0 m/s² comes with a time to collision of at most 4.0 s",
                       "REQ-DRIVING-041 lets the braking start", "The obligation is the candidate's",
                       "A simulation cannot show"),
        "criteria": ("Met when every setting of SC-DRIVING-012 and SC-DRIVING-013 is judged", "each judged run",
                      "at least 5.0 m/s²", "functional part",
                      "the needed deceleration to the target is at least 5.0 m/s²"),
    },
    "reqImpactSpeedWithinLimit": {
        "statement": ("When a collision with a vehicle ahead is imminent", "maximum relative impact speed",
                       "relative approach speed"),
        "rationale": ("This is a performance requirement", "SRC-UNECE-R152", "REQ-AEBS-003", "car in running order",
                       "asmSimulatedConfigurationStandsIn", "with the centre lines at most 0.2 m apart",
                       "The relative approach speed is taken when the collision becomes imminent",
                       "a limit of 0 km/h in each setting except SC-DRIVING-012 at 60 km/h, where it is 35 km/h",
                       "The obligation is the candidate's", "A simulation cannot show"),
        "criteria": ("Met when every setting of SC-DRIVING-012 and SC-DRIVING-013 is judged", "each judged run",
                      "at most the maximum relative impact speed for its relative approach speed"),
    },
    "reqDrivingCommandOverSCORE": {
        "statement": ("only over the Eclipse S-CORE path",),
        "rationale": ("design constraint", "vision_pilot.cpp:59-64", "vehicle_ros2_interface.cpp:25-26",
                       "vision_pilot.cpp:65-78", "reads a speed of zero and writes nothing (can_interface.cpp:4-12)",
                       "reads recorded speeds and writes nothing (file_interface.cpp:37-61)", "gapScoreIntegration"),
        "criteria": ("autopilot", "traffic manager", "replayed", "overlaid", "is stopped",
                      "SC-DRIVING-012 to SC-DRIVING-015"),
    },
    "reqDetectableDrivingCommand": {
        "statement": ("give each driving command in a form that lets the actuation detect",
                       "its loss, delay, repetition or corruption on the Eclipse S-CORE path"),
        "rationale": ("This is a design constraint", "REQ-MW-006", "protected emergency command path",
                       "The candidate cannot keep a path outside itself from failing",
                       "the share of the product that holds the path", "vision_pilot.cpp:157, 174",
                       "no freedom-from-interference claim"),
        "criteria": ("a loss, a delay, a repetition and a corruption", "phase 8",
                      "the part of the command by which the actuation detects it"),
    },
    "reqWithholdWarningRequest": {
        "statement": ("shall start its warning request only while a collision with a vehicle ahead is imminent",),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-008", "guidance, not as a test",
                       "binds the start of each warning request in every run",
                       "braking can end the imminence while the warning goes on, which the source allows",
                       "The obligation is the candidate's", "A simulation cannot show"),
        "criteria": ("in every run of SC-DRIVING-012 to SC-DRIVING-015",
                      "imminent at the start of each warning request"),
    },
    "reqWithholdEmergencyBraking": {
        "statement": ("shall start an emergency braking only while a collision with a vehicle ahead is imminent",),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-012", "longitudinal_planning.cpp:13-14, 34",
                      "only a command for 5.0 m/s² or more is an emergency braking",
                       "binds the start of each emergency braking in every run",
                       "lowers it below 1.0 m/s² before the vehicle stops", "The obligation is the candidate's",
                       "A simulation cannot show"),
        "criteria": ("in every run of SC-DRIVING-012 to SC-DRIVING-015",
                      "imminent at the start of each emergency braking"),
    },
    "reqWarningRequestBeforeEmergencyBraking": {
        "statement": ("When a collision with a vehicle ahead is imminent", "at its boundary",
                       "at least 1.0 s of simulation time before the start of its emergency braking"),
        "rationale": ("SRC-UNECE-R152", "REQ-AEBS-002",
                       "at the latest 0.8 s before the start of the emergency braking",
                       "Of the 1.0 s, 0.2 s is allotted",
                       "each mode is due within 0.2 s of wall-clock time after the request",
                       "which is the obligation of System 2", "and the requirement follows the need",
                       "at least 1.11 s before a needed deceleration of 5.0 m/s², so the exception is not taken",
                       "AAOS SDV", "planning.cpp:113-121", "The obligation is the candidate's",
                       "A simulation cannot show"),
        "criteria": ("Met when every setting of SC-DRIVING-012 and SC-DRIVING-013 is judged",
                      "in each judged run in which the collision with the target becomes imminent",
                      "1.0 s of simulation time", "first emergency braking"),
    },
    "reqWarningRequestOverSCORE": {
        "statement": ("to the AAOS SDV only over the Eclipse S-CORE path",),
        "rationale": ("design constraint", "vision_pilot.cpp:177-185", "gapWarningOutput"),
        "criteria": ("is stopped", "AAOS SDV", "communication records of the Eclipse S-CORE path"),
    },
    "reqRecordCandidateIdentity": {
        "statement": ("shall record its candidate identity before its first driving command of each run",),
        "rationale": ("in a build without ROS 2, the key source.mode", "vision_pilot.cpp:65-78",
                       "the highest speed that the candidate's planner drives toward", "vision_pilot.conf:20",
                       "REQ-DRIVING-033", "System 2"),
        "criteria": ("another engineer", "configuration files", "non-empty difference"),
    },
}

#: Every term the requirements use in a sense of their own, each defined once in the terms comment, in its order, with
#: the sentence that defines it.
TERM_DEFINITIONS = {
    "Vehicle": "the vehicle that the driver-assistance system drives.",
    "Vehicle ahead": "a vehicle ahead of the vehicle in its lane.",
    "Target": "the vehicle ahead in a run of SC-DRIVING-012 or SC-DRIVING-013.",
    "Run": "one execution of the driver-assistance system on one scenario, from its start to its end.",
    "Setting": "a scenario with an approach speed and its tolerance.",
    "Functional part": "the part of a run of SC-DRIVING-012 or SC-DRIVING-013 from the latest instant at which the vehicle travels at its approach speed within the tolerance with a time to collision of at least 4 s, until the vehicle hits the target or comes to the speed of the target.",
    "Judged run": "a run of SC-DRIVING-012 or SC-DRIVING-013 in which the vehicle travels straight, with its centre line within 0.2 m of that of the target, for at least 2 s before its functional part.",
    "Time to collision": "the distance from the vehicle to the vehicle ahead in the direction of travel, divided by the speed at which the vehicle closes on it.",
    "Needed deceleration": "the constant deceleration at which the vehicle, from its present speed, would come to the speed of the vehicle ahead just as it reaches it, the vehicle ahead keeping its present speed: the square of the speed at which the vehicle closes on it, divided by twice the distance from the vehicle to it in the direction of travel.",
    "Imminent collision": "a collision with a vehicle ahead to which the vehicle has a time to collision of at most 4.0 s and a needed deceleration of at least 1.0 m/s².",
    "Driving command": "the steering and acceleration command that the driver-assistance system gives the actuation of the vehicle.",
    "Actuation": "the interface at which the vehicle takes the driving commands.",
    "Boundary": "the interface at which the outputs of the driver-assistance system leave it for the Eclipse S-CORE path.",
    "Warning request": "the output by which the driver-assistance system asks the AAOS SDV to give the driver the collision warning.",
    "Emergency braking": "a command of the driver-assistance system for a deceleration of at least 5.0 m/s², in its driving command or apart from it.",
    "Eclipse S-CORE path": "the part of System 1 outside the driver-assistance system that carries its driving command to the actuation and its warning request to the AAOS SDV.",
    "Communication record": "the record that System 2 keeps of each message on the Eclipse S-CORE path, with its simulation time.",
    "Configuration": "every setting that the driver-assistance system reads at its start, from its files and its launch.",
    "Network file": "a file of trained weights or of the structure of a network that the driver-assistance system loads.",
    "Upstream revision": "the commit of the upstream repository from which the source of the driver-assistance system is built.",
    "Candidate identity": "the upstream revision, the difference between the source of the driver-assistance system and that revision, the SHA-256 of each network file it loads, the SHA-256 of each file of its configuration and the settings of its launch, verbatim.",
    "Relative approach speed": "the speed at which the vehicle closes on the vehicle ahead when the collision becomes imminent.",
    "Relative impact speed": "the speed at which the vehicle closes on the vehicle ahead when they touch; 0 km/h when they do not touch.",
    "Maximum relative impact speed": "the limit of the source regulation for a car in running order, by relative approach speed: 0 km/h up to 42 km/h, 15 km/h at 45 km/h, 25 km/h at 50 km/h, 30 km/h at 55 km/h and 35 km/h at 60 km/h.",
    "Simulation time": "the time of the simulated world.",
}
TERM_HEADS = tuple(TERM_DEFINITIONS)
#: The values the terms fix: the settings, the functional part, the judged run, the imminence, the emergency braking
#: and the whole limit table of the speed at impact.
TERM_VALUES = ("20 to 22 km/h", "40 to 42 km/h", "58 to 60 km/h", "30 to 32 km/h", "18 to 20 km/h", "28 to 30 km/h",
                "38 to 40 km/h", "at most 25 m radius", "at least 4 s", "within 0.2 m", "at least 2 s",
                "at least 5.0 m/s²", "Wall-clock time",
                "a time to collision of at most 4.0 s and a needed deceleration of at least 1.0 m/s²",
                "the square of the speed at which the vehicle closes on it, divided by twice the distance",
                "0 km/h up to 42 km/h, 15 km/h at 45 km/h, 25 km/h at 50 km/h, 30 km/h at 55 km/h and 35 km/h at 60 km/h",
                "Each setting is run twice, and both runs count.")
#: The rules the terms fix, each a decision of phase 5.
TERM_RULES = ("It starts with the first such command after a command for less.",
               "The source regulation calls any braking demand of the system an emergency braking",
               "It starts when the output begins to ask.", "the vehicle ahead keeping its present speed",
               "It has no value while the vehicle does not close on the vehicle ahead.",
               "until the vehicle hits the target or comes to the speed of the target",
               "is reported with what it missed and is not judged",
               "A setting of SC-DRIVING-012 or SC-DRIVING-013 is judged when both of its runs are judged runs.",
               "The further run of SC-DRIVING-012 in which the Eclipse S-CORE path of the driver-assistance system is "
               "stopped, which REQ-DRIVING-038 and REQ-DRIVING-043 name, is no run of a setting and no judged run, and "
               "only the stop clauses of those two requirements read it (the stop-run decision of 2026-11-18).",
               "a loss, a delay, a repetition or a corruption of a message on it",
               "the SHA-256 of each file of its configuration and the settings of its launch, verbatim",
               "the speed at which the vehicle closes on the vehicle ahead when the collision becomes imminent",
               "Between two of these speeds, the limit of the higher one applies.")
#: Owner decision of 2026-11-14: the imminence of a collision is quantified, not defined by a list of test runs.
IMMINENT_TERM = "- Imminent collision: a collision with a vehicle ahead to which the vehicle has a time to collision of at most 4.0 s and a needed deceleration of at least 1.0 m/s². The source regulation gives the word no value; the comment on gapVehicleTargetCriteria below gives the reasons for these two."
#: The definitions that the imminence rests on, whole.
IMMINENCE_TERMS = (
    "- Time to collision: the distance from the vehicle to the vehicle ahead in the direction of travel, divided by the speed at which the vehicle closes on it. It has no value while the vehicle does not close on the vehicle ahead.",
    "- Needed deceleration: the constant deceleration at which the vehicle, from its present speed, would come to the speed of the vehicle ahead just as it reaches it, the vehicle ahead keeping its present speed: the square of the speed at which the vehicle closes on it, divided by twice the distance from the vehicle to it in the direction of travel.",
)
#: What the gap comment on gapVehicleTargetCriteria must name: the requirements, the obligations, the reasons for the
#: values of the imminence and what stays open, each with its owner.
GAP_FRAGMENTS = ("REQ-DRIVING-036", "REQ-DRIVING-037", "REQ-DRIVING-040", "REQ-DRIVING-041", "REQ-DRIVING-042",
                  "System 2", "AAOS SDV", "0.2 s", "SC-DRIVING-014", "SC-DRIVING-015",
                  "a time to collision of at most 4.0 s and a needed deceleration of at least 1.0 m/s², as the owner decided on 2026-11-14",
                  "at least 1.11 s before a needed deceleration of 5.0 m/s²", "needs 0.47 to 0.67 m/s²",
                  "stands outside the lane", "A setting whose two runs are not both judged meets no criterion",
                  "A simulation that runs no faster than wall-clock time, on which that share rests, is the obligation of System 2.",
                  "System 2 records in each of their runs the speeds and the times to collision",
                  "Open, each with its owner:", "(the owner of the project)", "(the evaluators of phase 10)",
                  "(System 2)")
GAP_COMMENT = "comment vehicleTargetCriteriaFixedInPhase5 about DE4SDV_DriverAssistanceFraming::gapVehicleTargetCriteria"
#: What the package header must say of phase 5.
HEADER_FRAGMENTS = ("Phase 5: the requirements derived from these needs", "SRC-UNECE-R152", "REQ-AEBS-012",
                     "The requirements are not core", "visionPilotDrivingStack",
                     "phase 9 adds that feature to the feature model", "upstream.md gives each with its path",
                     "The terms quantify when a collision is imminent")

#: The guide's numbers, from the counts to the values of the terms and the decisions of phase 5.
GUIDE_FACTS = (
    "There are nine, within the scope's cap of ten.",
    "Five are functional; Phase 6 allocates each of those to a function.",
    "when the vehicle is at most 4.0 s from a vehicle ahead in its lane",
    "would have to brake at 1.0 m/s² or more",
    "both values are the owner's decision of 2026-11-14",
    "at least 1.11 s before 5.0 m/s² is needed",
    "needs 0.47 to 0.67 m/s²",
    "the stationary target of `SC-DRIVING-012` at 20, 42 and 60 km/h",
    "the target of `SC-DRIVING-013`, moving at 20 km/h, at 30 and 60 km/h",
    "the curve of `SC-DRIVING-014` at 30 km/h",
    "the vehicle ahead of `SC-DRIVING-015` at 40 km/h",
    "its centre line within 0.2 m of that of the target, for at least 2 s",
    "with a time to collision of at least 4 s",
    "A setting is judged when both of its runs are",
    "The further run of `SC-DRIVING-012` that stops the Eclipse S-CORE path, which `REQ-DRIVING-038` and "
    "`REQ-DRIVING-043` name, is no run of a setting and no judged run; only the stop clauses of those two requirements "
    "read it (the stop-run decision of 2026-11-18).",
    "and so at least 0.8 s before the start of the emergency braking",
    "0.2 s of the lead of 1.0 s is the share of the S-CORE path and the AAOS SDV",
    "the regulation asks for the warning to the driver at the latest 0.8 s before the start of the emergency braking",
    "the regulation would count the lead from it",
    "the regulation takes the test speed",
    "the requirement follows the need",
    "the regulation allows one repeat",
)
#: The decisions of phase 5 that the guide lists, one item each.
GUIDE_DECISIONS = 12
#: The kind that the guide names for a requirement that is not functional; its rationale opens with it.
GUIDE_KINDS = ("performance", "design constraint")
#: The lines that the upstream record links for each cited file.
RECORD_ANCHORS = {
    "vision_pilot.cpp": (59, 185),
    "planning.cpp": (113, 121),
    "longitudinal_planning.cpp": (13, 36),
    "vision_pilot.conf": (20, 20),
    "vehicle_ros2_interface.cpp": (25, 26),
    "can_interface.cpp": (4, 12),
    "file_interface.cpp": (37, 61),
}
#: What the upstream record says that each cited line does, whole.
RECORD_FACTS = (
    "lines 59 to 64 build the ROS 2 interfaces",
    "in a build without ROS 2, lines 65 to 78 choose the source of the camera image and the speed from the key `source.mode` at run time",
    "Line 138 lets a pass of the loop plan only when the inference gives a result",
    "line 157 plans and line 174 writes the steering and the acceleration",
    "Lines 177 to 185 pass the plan to the visualization and to the data log, each when it is switched on",
    "lines 113 to 121 add to the plan the forward-collision warning for a planned acceleration from -5.0 to -3.0 m/s² and the emergency braking for one below -5.0 m/s²",
    "lines 13 and 14 lower the speed limit in curves",
    "line 34 adds the car-following term only while an object in the path is tracked",
    "line 36 returns the configured acceleration times one less the free-road term and the car-following term; both terms are zero or more, so the result is at most the configured acceleration",
    "line 20 sets a speed limit of 33.3 m/s",
    "lines 25 and 26 create its only two publishers, for the steering and the acceleration",
    "lines 4 to 8 return a speed of 0.0, and lines 10 to 12 take the steering and the acceleration in a function with an empty body",
    "lines 37 to 57 return the next speed read from a file, and lines 59 to 61 take the steering and the acceleration in a function with an empty body",
)

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
    heads = tuple(re.findall(r"(?m)^\s*\*\s+- ([^:\n]+):", match.group(1)))
    assert heads == TERM_HEADS, heads
    text = _flat(match.group(1))
    for head, definition in TERM_DEFINITIONS.items():
        assert f"- {head}: {definition}" in text, head
    for value in TERM_VALUES:
        assert value in text, value
    for rule in TERM_RULES:
        assert rule in text, rule


def test_the_imminence_of_a_collision_is_quantified_in_the_terms():
    # Owner decision of 2026-11-14: "imminent" carries a time to collision and a needed deceleration. A definition by a
    # list of test runs said nothing outside the scenarios, and failed a candidate whose speed control defused the
    # approach before the demand value was needed.
    text = _flat(re.search(r"\bcomment\s+termsOfTheDriverAssistanceRequirements\s*/\*(.*?)\*/", _raw(), re.S).group(1))
    assert IMMINENT_TERM in text
    for term in IMMINENCE_TERMS:
        assert term in text, term
    assert "as the tests of the source regulation do" not in _raw()
    assert "Uncommanded emergency braking" not in _raw()
    # the demand of REQ-DRIVING-036 follows the needed deceleration, the trigger of the others the defined term
    assert _statement(_requirement("reqEmergencyBrakingForImminentCollision")).startswith(
        "While the needed deceleration to a vehicle ahead is at least 5.0 m/s²")
    for name in ("reqImpactSpeedWithinLimit", "reqWithholdWarningRequest", "reqWithholdEmergencyBraking",
                 "reqWarningRequestBeforeEmergencyBraking"):
        assert "collision with a vehicle ahead is imminent" in _statement(_requirement(name)), name


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


#: The stop-run decision of 2026-11-18, the amendment of the terms, as the package head records it.
STOP_RUN_DECISION = ("On 2026-11-18 the owner amended the terms: the further run of SC-DRIVING-012 in which the "
                     "Eclipse S-CORE path of the driver-assistance system is stopped is no run of a setting and no "
                     "judged run, and only the stop clauses of REQ-DRIVING-038 and REQ-DRIVING-043 read it: the "
                     "stop-run decision of 2026-11-18.")
#: The names the amendment had before it was recorded as a decision; one name stays (review R2 of the 10a review).
RETIRED_STOP_RUN_NAMES = ("an amendment of the terms of 2026-11-18", "since their amendment of 2026-11-18",
                          "amended on 2026-11-18")


def test_the_package_head_records_the_stop_run_decision():
    """The amendment of the accepted phase 5 terms is a dated decision of the package head, after the account of
    phase 5, and the model and the guide call it by one name."""
    match = re.search(r"/\*(.*?)\*/", _raw(), re.S)
    header = _flat(match.group(1))
    assert header.count(STOP_RUN_DECISION) == 1
    assert header.index("Phase 5: the requirements derived from these needs") < header.index(STOP_RUN_DECISION) < \
        header.index("No safety, on-road or production-readiness claim is made"), "after phase 5, before the limits"
    assert not re.search(r"(?i)\bthe owner (?:said|answered|wrote)\b", header), "a decision, never a quote"
    driving = ROOT / "textual-notation-of-model" / "packages" / "features" / "driving"
    texts = {path.name: _flat(path.read_text(encoding="utf-8"))
             for path in (driving / "driver_assistance_needs_requirements.sysml",
                          driving / "driver_assistance_verification_evidence.sysml")}
    texts["guide"] = " ".join((ROOT / "docs" / "guides" / "driver-assistance-increment.md").read_text(
        encoding="utf-8").split())
    for name, text in texts.items():
        for retired in RETIRED_STOP_RUN_NAMES:
            assert retired not in text, (name, retired)
    # the decision's name: in the head and the term of phase 5, the slice header and the setting doc, and the guide
    assert texts["driver_assistance_needs_requirements.sysml"].count("the stop-run decision of 2026-11-18") == 2
    assert texts["driver_assistance_verification_evidence.sysml"].count("the stop-run decision of 2026-11-18") == 2
    assert texts["guide"].count("the stop-run decision of 2026-11-18") == 2


def test_the_phase_4_contract_comment_is_now_stated_in_the_rationales():
    # Phase 4 kept the runtime contract of VisionPilot at the pin as a comment for phase 5. Phase 5 states its
    # facts in the rationales, so the comment no longer earns its place.
    assert "visionPilotContractAtPin" not in _raw()


def test_the_requirements_name_features_only_in_their_rule_5_dependencies():
    # Phase 3 records VisionPilot as the feature candidate visionPilotDrivingStack; phase 9 added it to the feature
    # model and links the system of interest to it in the framing. The requirements follow their subject, so none
    # names visionPilot; a requirement names a feature only in a dependency declared with it, for what its subject
    # does not bring. tests/test_driver_assistance_variability_configuration.py pins each link.
    code = _code()
    assert not re.search(r"\bimport\s+DE4SDV_ProductLine\w*", code)
    assert "visionPilotDrivingStack" not in code
    feature = "DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::"
    links = re.findall(rf"\bdependency\s+(\w+)\s+from\s+(\w+)\s+to\s+{re.escape(feature)}(\w+)\s*;", code)
    assert links and len(links) == code.count("DE4SDV_SDVProductLineFeatureModel")
    for name, client, target in links:
        assert client in REQUIREMENTS, client
        assert name == f"{client}On{target[0].upper()}{target[1:]}", name
        assert target != "visionPilot", "the requirements follow their subject to visionPilot"


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
    assert "The increment ended at its baseline decision." in flat
    assert "`verificationCaseVerifiesRequirement` and `requirementVerifiedByVerificationCase` read" in flat
    section = " ".join(raw_section.split())
    for fact in GUIDE_FACTS:
        assert fact in section, fact
    # each requirement with its name, need, kind and method; a kind other than functional only where the model says it
    items = re.findall(r"- `(REQ-DRIVING-\d{3})` `(\w+)`, from `(NEED-DRIVING-\d{3})`, ([a-z ]+), (test|analyze|inspect|demo):",
                       section)
    assert [item[1] for item in items] == list(REQUIREMENTS)
    for short, name, need, kind, method in items:
        expected_short, expected_need, definition, expected_method = REQUIREMENTS[name]
        assert (short, need, method) == (expected_short, NEED_SHORT[expected_need], expected_method), name
        if definition == F:
            assert kind == "functional", name
        else:
            assert kind in GUIDE_KINDS, (name, kind)
            assert _attribute(_requirement(name), "rationale").startswith(f"This is a {kind}"), (name, kind)
    decisions = raw_section.split("**Values set in Phase 5.**", 1)[1].split("\n\n", 2)[1]
    assert re.findall(r"(?m)^(\d+)\. ", decisions) == [str(n) for n in range(1, GUIDE_DECISIONS + 1)]


def test_the_upstream_record_gives_each_cited_file_with_its_path():
    # The header says so: the rationales name the files of VisionPilot by file name, upstream.md by path and line.
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    paths = re.findall(r"\[VisionPilot/([^\]]+)\]\(https://github\.com/autowarefoundation/vision_pilot/blob/"
                       rf"{PIN}/VisionPilot/\1#L\d+(?:-L\d+)?\)", record)
    cited = set()
    for name in REQUIREMENTS:
        cited |= set(re.findall(r"\b([\w.]+\.(?:cpp|hpp|conf)):\d", _texts(name)["rationale"]))
    assert len(cited) == 7, cited
    assert sorted(cited) == sorted(path.rsplit("/", 1)[-1] for path in paths), (cited, paths)
    # each line that a rationale cites lies inside the lines that the record links for its file
    anchors = {path.rsplit("/", 1)[-1]: (int(first), int(last or first)) for path, first, last in re.findall(
        r"\[VisionPilot/([^\]]+)\]\([^)]*#L(\d+)(?:-L(\d+))?\)", record)}
    assert anchors == RECORD_ANCHORS, anchors
    for name in REQUIREMENTS:
        for file, lines in re.findall(r"\b([\w.]+\.(?:cpp|hpp|conf)):(\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*)",
                                      _texts(name)["rationale"]):
            first, last = anchors[file]
            for part in lines.split(", "):
                low, _, high = part.partition("-")
                assert first <= int(low) <= int(high or low) <= last, (name, file, part, anchors[file])
    flat = " ".join(record.split())
    for fact in RECORD_FACTS:
        assert fact in flat, fact
