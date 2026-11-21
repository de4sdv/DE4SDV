"""INC-DRIVING-002 phase 10: the verification cases of the driver-assistance requirements and the evidence of record.

Lexical pins on ``driver_assistance_verification_evidence.sysml``: one case per requirement, each bound to the
realization of the driver-assistance system in DRIVING-CONFIG-002, each naming the scenarios, settings and runs its
requirement's criteria read; the run-level evidence record and the record of the one analysis; the claims,
arguments and counter-claims the assurance view links; and the evidence decisions of 2026-11-18 by their exact
phrases (the first slice). The second slice: the evidence records of the judged session S1 and the status of each
case, which must be exactly what ``tools/generate_driver_assistance_evidence_text.py`` writes from the files of the
evidence directory, so that no value that comes from a verdict is written by hand; the decisions of 2026-11-21; and
the environment gap as S1 leaves it. The invariants of every verification model are in
``test_verification_model_invariants.py``; the licensed Syside run validates the model.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from sysml_shapes import charter_package_files, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model" / "packages" / "features" / "driving"
SLICE = DRIVING / "driver_assistance_verification_evidence.sysml"
REQUIREMENTS = DRIVING / "driver_assistance_needs_requirements.sysml"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
PHYSICAL = DRIVING / "driver_assistance_physical_software_realization.sysml"
VARIABILITY = DRIVING / "driver_assistance_variability_configuration.sysml"
DRIVING_001_FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
GUIDE = ROOT / "docs" / "guides" / "driver-assistance-increment.md"
WORKFLOW = ROOT / "methodologies" / "sysmod-sysmlv2" / "increment-workflow.md"
MODEL_ROOTS = [ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering"]
EVIDENCE = ROOT / "implementation" / "driver-assistance-bench" / "evidence" / "s1-20261121T014447Z"
GENERATOR = ROOT / "tools" / "generate_driver_assistance_evidence_text.py"
SESSION = "20261121T014447Z"

PACKAGE = "DE4SDV_DriverAssistanceVerificationEvidence"
BENCH_DEF = "DriverAssistanceVerificationBench"
RUN_RECORD = "RetainedAssistanceRunEvidence"
ANALYSIS_RECORD = "RetainedCommandFormAnalysis"
GAP = "GAP-DRIVING-014"
GAP_NAME = "gapAssistanceVerificationEnvironmentOpen"
DECISIONS = "the evidence decisions of 2026-11-18"
NUMBERS = list(range(36, 45))

SC_IDS = {"stationaryTarget": "SC-DRIVING-012", "slowerTarget": "SC-DRIVING-013",
          "curveWithGuardPipes": "SC-DRIVING-014", "vehicleTurningOff": "SC-DRIVING-015"}
SETTINGS = {"stationaryAt20": "stationaryTarget", "stationaryAt42": "stationaryTarget",
            "stationaryAt60": "stationaryTarget", "slowerAt30": "slowerTarget", "slowerAt60": "slowerTarget",
            "curveAt30": "curveWithGuardPipes", "turningOffAt40": "vehicleTurningOff"}
TARGET_SETTINGS = [s for s, scenario in SETTINGS.items() if scenario in ("stationaryTarget", "slowerTarget")]
STOP_RUN = ("the further run of SC-DRIVING-012 in which the Eclipse S-CORE path of the driver-assistance system "
            "is stopped")
APART = ("The runs of SC-DRIVING-014 and SC-DRIVING-015 are reported apart from the runs inside the declared "
         "operating conditions (gapDeclaredOperatingConditions).")
#: the phase 5 terms since the stop-run decision of 2026-11-18: the stop run is no run of a setting and no judged
#: run, and only the stop clauses of REQ-DRIVING-038 and REQ-DRIVING-043 read it
STOP_RUN_DECISION = "the stop-run decision of 2026-11-18"
TERMS_AMENDMENT = ("The further run of SC-DRIVING-012 in which the Eclipse S-CORE path of the driver-assistance system "
                   "is stopped, which REQ-DRIVING-038 and REQ-DRIVING-043 name, is no run of a setting and no judged "
                   f"run, and only the stop clauses of those two requirements read it ({STOP_RUN_DECISION}).")
#: the run scope of each claim, in the words of the cases its argument cites: the fourteen runs of the settings, the
#: ten runs of SC-DRIVING-012 and SC-DRIVING-013, the judged runs, and the stop run only where a stop clause reads it
#: (the stop-run decision of 2026-11-18; review R1 of the 10a review)
CLAIM_RUN_SCOPES = {
    "vehicleTargetResponse": (
        "in the judged runs of every setting of SC-DRIVING-012 and SC-DRIVING-013, the driver-assistance system",
        "run; and in each of the fourteen runs of SC-DRIVING-012 to SC-DRIVING-015 it starts a warning request and "
        "an emergency braking only while a collision with a vehicle ahead is imminent.",
    ),
    # the realization that phase 8 records, and no run
    "emergencyBrakingIndependence": (),
    "driverWarningSequence": (
        "In each judged run of SC-DRIVING-012 and SC-DRIVING-013 in which the collision with the target becomes "
        "imminent,",
        "and in each of the fourteen runs of SC-DRIVING-012 to SC-DRIVING-015 it starts a warning request only while "
        "a collision with a vehicle ahead is imminent.",
    ),
    "scoreCommandAndWarningPath": (
        "In each of the fourteen runs of SC-DRIVING-012 to SC-DRIVING-015 every driving command that reaches the "
        "actuation, and in each of the ten runs of SC-DRIVING-012 and SC-DRIVING-013 every warning request that "
        "reaches the AAOS SDV, is matched",
        "; in those fourteen runs the autopilot and the traffic manager of the simulator have no control of the "
        "vehicle, and no recorded,",
        "; and in the further run of SC-DRIVING-012 with the path stopped neither the command nor the request "
        "arrives after the stop.",
    ),
    "candidateVerdict": (
        "Each verdict that rests on the fourteen runs of SC-DRIVING-012 to SC-DRIVING-015 is bound to the candidate "
        "that ran: the candidate identity record of each of those runs, there before its first driving command",
        "; and the evidence record of each of those runs binds DRIVING-CONFIG-002",
        "The record of the further run of SC-DRIVING-012 with the path stopped carries the candidate identity "
        "values as well, and no case checks them, because only the stop clauses of REQ-DRIVING-038 and "
        "REQ-DRIVING-043 read that run.",
    ),
}
#: the claims that name the further run: the one whose cases read the stop clauses of the path, and the one that
#: states that no case checks the candidate identity values of that run
STOP_RUN_CLAIMS = ("scoreCommandAndWarningPath", "candidateVerdict")
STOP_CLAUSE_ONLY = f"{STOP_RUN}, which only the stop clause reads."
#: in the stop run the candidate keeps running and the path's carriers stop; the next slice names the processes
STOP_RUN_CARRIERS = ("In the further run the candidate's process keeps running, and the path's carriers of the driving "
                     "command and of the warning request are stopped through the Launch Manager; which processes these "
                     "are is fixed in the next slice.")
#: the outcome of a case of the judged runs when a setting is not judged, and of a case over every run
NOT_JUDGED_OUTCOME = "a setting that is not judged gives inconclusiveMissingEvidence, never pass."
EVERY_RUN_OUTCOME = ("A run that is missing, or whose record shows a dropped image within the run, gives "
                     "inconclusiveMissingEvidence, never pass.")
#: what phase 5 asks System 2 to record in each run of SC-DRIVING-014 and SC-DRIVING-015, in phase 5's own words
GUIDANCE = "the speeds and the times to collision that the guidance of the source names for the scenario"
#: the parts of a success criterion that its case must restate: the values, the scenarios and the stop clause
CRITERION_VALUE = re.compile(r"\d+\.\d+ (?:m/s²|s\b)")
CRITERION_SCOPE = re.compile(r"SC-DRIVING-012 (?:to SC-DRIVING-015|and SC-DRIVING-013)")
CRITERION_STOP = re.compile(r"in one further run of (SC-DRIVING-012 in which the Eclipse S-CORE path of the "
                            r"driver-assistance system is stopped), (no [\w ]+? after the stop)")
NUMBER_WORDS = {5: "Five", 7: "Seven", 10: "ten", 12: "Twelve", 14: "fourteen"}

#: requirement number -> (the settings the case reads, the count phrase of its runs, whether it reads the stop run,
#: the requirement's verification method); the criteria of each requirement name them
CASE_RUNS = {
    36: (TARGET_SETTINGS, "ten runs", False, "test"),
    37: (TARGET_SETTINGS, "ten runs", False, "test"),
    38: (list(SETTINGS), "fourteen runs", True, "test"),
    39: ([], None, False, "analyze"),
    40: (list(SETTINGS), "fourteen runs", False, "test"),
    41: (list(SETTINGS), "fourteen runs", False, "test"),
    42: (TARGET_SETTINGS, "ten runs", False, "test"),
    43: (TARGET_SETTINGS, "ten runs", True, "test"),
    44: (list(SETTINGS), "fourteen runs", False, "test"),
}

#: claim -> (the phase 1 concern it answers, the requirement numbers its argument cites)
CLAIMS = {
    "vehicleTargetResponse": ("vehicleTargetResponseConcern", [36, 37, 40, 41, 42]),
    "emergencyBrakingIndependence": ("emergencyBrakingIndependenceConcern", [38, 39]),
    "driverWarningSequence": ("driverWarningSequenceConcern", [40, 42]),
    "scoreCommandAndWarningPath": ("scoreCommandAndWarningPathConcern", [38, 43]),
    "candidateVerdict": ("candidateVerdictConcern", [44]),
}
#: the phase 1 concern whose question no run answers, and so no claim
UNCLAIMED_CONCERN = "vehicleTargetCriteriaConcern"
#: counter-claim -> (the records that keep it open, in the order of its ties, and their file); the first tie of each
#: is named <counter-claim>BoundTo, a further one <counter-claim>BoundTo<suffix>
COUNTER_CLAIMS = {
    "SimulatedConfigurationOnly": (["asmSimulatedConfigurationStandsIn"], FRAMING),
    "RenderedCameraImages": (["gapCameraImageAndGeometry"], FRAMING),
    "NoComplianceOrApproval": (["onRoadOperationOutOfScope", "gapVehicleTargetCriteria"], FRAMING),
    "OutsideDeclaredConditions": (["gapDeclaredOperatingConditions"], FRAMING),
    "NoIndependentEmergencyPath": (["gapNoSeparateEmergencyFunction"], FRAMING),
    "BuildWithUnmergedChanges": (["gapCandidateBehaviorUnverified"], FRAMING),
    "WarningModesNotJudgedHere": (["furtherWarningProvisionsOutOfScope"], FRAMING),
    "NoMemberProduct": (["gapCandidateAdmission"], FRAMING),
    "NoUpstreamEndorsementOrRights": (["gapUpstreamContactAndRights"], FRAMING),
    "NoTuningToPass": (["candidateTuningOutOfScope"], FRAMING),
    "ReusedBenchNotEvidence": (["asmBenchReuse"], FRAMING),
    "BenchOpenNoVerdict": ([GAP_NAME], SLICE),
}
#: the tie names of each counter-claim, in the order of its records
TIE_SUFFIXES = {"NoComplianceOrApproval": ["", "Criteria"]}
RUN_ATTRIBUTES = [
    "configurationIdentity", "receiptSha256", "modelRevision", "candidateRecordIdentity", "upstreamRevision",
    "sourceDifference", "networkFileSha256", "configurationFileSha256", "launchSettings", "candidateBuild",
    "visualizationRecorderDelay", "scoreLifecycleVersion", "scoreCommunicationVersion", "scoreSOMEIPGatewayCommit",
    "simulatorBuild", "scenario", "setting", "runIdentity", "simulatedConfiguration", "simulationClockSpan",
    "wallClockSpan", "executionEnvironmentIdentity", "contractIdentity", "criteriaRecordIdentity", "evaluatorRevision",
    "rawObservationArtifact", "benchRecordingArtifact", "independentEngineerIdentity", "claimBoundary"]
#: GAP-DRIVING-014 as the judged session S1 leaves it (the environment decision of 2026-11-21): each readiness item
#: of phase 8, (its phrase in the model, its phrase in the guide); the model names the session record that shows it
GAP_ITEMS = [
    ("the link of the S-CORE process with the build of ONNX Runtime for CUDA: shown, the candidate's process runs "
     "its networks with ONNX Runtime for CUDA under the Launch Manager in every run of S1 (the Launch Manager log of "
     "each run, score_side/state/launch_manager.log)",
     "the link with the build of ONNX Runtime for CUDA in the S-CORE process: shown"),
    ("whether that process may hold a second C++ standard library: settled by the build that ran, whose files each "
     "run's score_side/state/staging.json lists",
     "a second C++ standard library in that process: settled by the build that ran"),
    ("that the candidate record reaches the vehicle interface, which subscribes after the record was published: "
     "shown, the score-interface record of each run holds the candidate record's arrival (in.candidate_record in "
     "score_side/run/score/score_interface.jsonl)",
     "the candidate record reaching a late subscriber: shown"),
    ("the candidate driving on CARLA 1.0: shown, it drove every run of S1 there (simulatorBuild of each run "
     "record)", "the candidate on CARLA 1.0: shown"),
    ("the typed message of the warning request on the guests: shown, the message type that contractIdentity of "
     "each run record names reached the warning presentation on the IVI guest in every run "
     "(guest/out/capture_<run>/app_record_warning.jsonl)",
     "the typed message of the warning request on the guests: shown"),
    ("the calibration runs of ASM-DRIVING-005 and ASM-DRIVING-006 came before the first judged run "
     "(sim/out/calibrate/calib_decel and the steering calibration run calib_steer); what they show is in the "
     "values of VC-DRIVING-036 and VC-DRIVING-037",
     "the calibration runs of ASM-DRIVING-005 and ASM-DRIVING-006 came before the first judged run"),
    ("whether the S-CORE host's own GPU keeps the candidate's cycle with the S-CORE build: answered no",
     "the S-CORE build's cycle on the host's own GPU: answered no"),
    ("the capture of the start of the sound on the IVI guest: open",
     "the capture of the start of the sound on the IVI guest: open"),
    ("the showing of the draft of the warning output and the interface seam, with the results, to the VisionPilot "
     "maintainers: open, not done; the owner approves any text first (the upstream contact decision of "
     "2026-11-18)",
     "showing the draft and the results to the VisionPilot maintainers: open, not done"),
]
#: the sentence of GAP-DRIVING-014 on the sound, from the guest records of S1
SOUND_CAPTURE = ("The guest records of S1 hold no start of the sound: in every run the warning presentation received "
                 "the warning requests with none requesting a warning, so it prepared its sound and never started "
                 "it; the audio state that each capture records at its start and at its end is no capture of a "
                 "start.")
#: the runs of S1 by their label in the drop counts and by their run identity in the model
RUN_LABELS = {"012_20_r1": "SC-DRIVING-012@20/r1", "012_20_r2": "SC-DRIVING-012@20/r2",
              "012_42_r1": "SC-DRIVING-012@42/r1", "012_42_r2": "SC-DRIVING-012@42/r2",
              "012_60_r1": "SC-DRIVING-012@60/r1", "012_60_r2": "SC-DRIVING-012@60/r2",
              "013_30_r1": "SC-DRIVING-013@30/r1", "013_30_r2": "SC-DRIVING-013@30/r2",
              "013_60_r1": "SC-DRIVING-013@60/r1", "013_60_r2": "SC-DRIVING-013@60/r2",
              "014_30_r1": "SC-DRIVING-014@30/r1", "014_30_r2": "SC-DRIVING-014@30/r2",
              "015_40_r1": "SC-DRIVING-015@40/r1", "015_40_r2": "SC-DRIVING-015@40/r2"}
#: the record usages the generator writes, in their order: one per run of S1, then the analysis
RECORD_USAGES = [f"{setting}{place}RunEvidence" for setting in SETTINGS for place in ("First", "Second")] + [
    "pathStoppedRunEvidence", "commandFormAnalysisEvidence"]
#: B-1, the bench finding of 2026-11-21, as GAP-DRIVING-014 records it: an open bench item for the next session;
#: the world side's code at 508649ba (world-side/da_world_side.py, _run_loop) shows the end check, and the speeds are
#: those of the runs' world.jsonl
B1_STATEMENTS = (
    "Open for the next session, a bench item that S1 shows (B-1, the bench finding of 2026-11-21): the second runs "
    "of SC-DRIVING-013, SC-DRIVING-013@30/r2 and SC-DRIVING-013@60/r2, ended after {ticks} ticks at the speed of the "
    "target, with the vehicle at 1.3 km/h and the target at 20 km/h.",
    "At the first tick of each the target was at rest (8e-08 and 8.5e-05 m/s); in the first runs it already moved "
    "at 5.2 m/s.",
    "The end check of the world side at 508649ba (_run_loop in world-side/da_world_side.py) counts the vehicle as "
    "closing on the target while the closing speed is above 0.0 m/s, and ends the run 3.0 s after the first later "
    "tick at which it is not: at the first tick of the second runs the vehicle closed at 0.0023 m/s on the target "
    "at rest, at the second the target moved at 5.26 m/s, so each run ended 3.05 s after its first tick.",
    "Why the target was at rest at the first tick of the second runs only, the records do not show.",
    "SC-DRIVING-013@60/r1 ended in contact with the target but has no functional part: no tick in the band with a "
    "time to collision of at least 4 s.",
    "So SC-DRIVING-013 has one judged run, SC-DRIVING-013@30/r1.",
    "The bench is not changed for S1: a change would alter a file that ran in S1 and void the condition of record.",
)
#: the decisions of 2026-11-21 that the slice header records, in day order after those of 2026-11-18
DECISIONS_1121 = (
    "On 2026-11-21 the judged session S1 was taken as the evidence of record, on the condition that the bench files "
    "that ran on a host are byte-identical to those that the pull request of the bench merges; the README of the "
    "evidence directory states the check: the evidence-of-record decision of 2026-11-21.",
    "On 2026-11-21 the drop rule of phase 8 was kept: no run whose judged window holds a dropped image is judged, "
    "and a reading that the evaluators give with the rule set aside is diagnosis, never a verdict: the drop-rule "
    "decision of 2026-11-21.",
    "On 2026-11-21 it was recorded that the condition on ASM-DRIVING-005, the calibration of the simulated "
    "deceleration, bears on a pass of VC-DRIVING-036 and VC-DRIVING-037 and not on their fail in S1, in which no run "
    "of SC-DRIVING-012 holds a commanded deceleration beyond 0.53 m/s²: the deceleration calibration decision of "
    "2026-11-21.",
    "On 2026-11-21 the verification status of each requirement was set from S1, as the requirements package "
    "records (the status decision of 2026-11-21).",
)
#: the second slice, as the slice header states it
SECOND_SLICE = (
    "The second slice records the evidence of the judged session S1, session 20261121T014447Z of the bench at "
    "commit 508649ba: one evidence record per run of S1 and the record of the analysis of REQ-DRIVING-039, written "
    "with the status of each case by tools/generate_driver_assistance_evidence_text.py from the records that "
    "implementation/driver-assistance-bench/evidence/s1-20261121T014447Z retains; "
    "tools/refresh_driver_assistance_s1_evidence.py regenerates them in one command, and no value that comes from "
    "a verdict is written by hand.")
#: what the cases of 036 and 037 state of ASM-DRIVING-005 in S1 (the deceleration calibration decision)
ASM005_IN_CASE = (
    "The condition on ASM-DRIVING-005, the calibration of the simulated deceleration, that the claimBoundary of "
    "each run record states bears on a pass of this case and not on its fail in S1: it concerns how the simulated "
    "vehicle achieves a commanded deceleration, and the fails rest on the commanded values. In S1 no driving command "
    "that the actuation adapter accepted in a run of SC-DRIVING-012 holds a deceleration beyond 0.53 m/s²: the "
    "strongest is {decelerations} (rounded to two decimals; commanded_deceleration.json of the evidence directory), "
    "so the condition does not bear on the outcome of this case in S1 (the deceleration calibration decision of "
    "2026-11-21).")


def asm005_in_case(found: dict) -> str:
    """ASM005_IN_CASE with the strongest commanded deceleration of each run of SC-DRIVING-012 from
    commanded_deceleration.json, both runs of a setting together."""
    values = [found[label]["strongestDecelerationMps2"] for label in list(RUN_LABELS)[:6]]
    parts = [f"{a:.2f} and {b:.2f} m/s² {where}" for (a, b), where in zip(
        zip(values[0::2], values[1::2]), ("in the two runs at 20 km/h", "at 42 km/h", "at 60 km/h"))]
    return ASM005_IN_CASE.format(decelerations=", ".join(parts[:-1]) + ", and " + parts[-1])


#: the bounds of the analysis of REQ-DRIVING-039, in the case's doc
ANALYSIS_BOUNDS = (
    "The analysis is bounded, as the claimBoundary of its record states: the actuation recognizes a loss only when "
    "a later command arrives; it does not recognize a delay of up to 0.1 s of simulation time against its newest "
    "world time; and it recognizes a corruption only as far as the check value does: a corruption that the check "
    "value misses counts as valid and, with a higher sequence count, becomes the reference count, so that later "
    "valid commands are rejected as repetitions, which the realization states since the check-value bound decision "
    "of 2026-11-21.")
#: the end of each claim's doc: the verdicts of S1 are the cases', read against the claim as written
CLAIM_STATE = ("Whether the judged session S1 supports the claim follows from the verdicts of the cases its argument "
               "cites, which their docs state; the claim stands as it was written before any run.")
BENCH_COUNTER_CLAIM = (
    "No verdict holds beyond the bench of the judged session S1: a verdict holds for the session, the bench commit "
    "and the candidate build that its records name, and the readiness items that S1 does not show stay open "
    "(GAP-DRIVING-014).")
ANALYSIS_ATTRIBUTES = ["configurationIdentity", "receiptSha256", "modelRevision", "analyzedRealization",
                       "analystIdentity", "claimBoundary"]
OUTCOMES = ["passBoundedVerification", "passBoundedValidation", "failObservedBehavior",
            "inconclusiveMissingEvidence", "blockedTargetRuntime", "errorEvidence"]

_NOT_CODE = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:[^\"\\]|\\.)*\"", re.S)


def _seconds(values) -> str:
    """36.8 and 41.9 s; 36.4, 51.4 and 76.5 s"""
    text = [f"{v:.1f}" for v in values]
    return (", ".join(text[:-1]) + " and " + text[-1] if len(text) > 1 else text[0]) + " s"


def _span(values) -> str:
    low, high = min(values), max(values)
    return f"{low}" if low == high else f"{low} to {high}"


def _either(values) -> str:
    found = sorted(set(values))
    return " or ".join(str(v) for v in found)


def guide_drop_phrase(counts: dict) -> str:
    """The guide's words for where the images drop, each figure read from drop_counts.json."""
    judged = [counts[label] for label in RUN_LABELS]
    return (f"answered no, every run of S1 drops camera images: {_either(c['droppedInFirst5s'] for c in judged)} in "
            f"the first 5 s after its first image, {_span([c['droppedAtStreamEnd'] for c in judged])} in the last "
            f"{max(c['streamEndDropsWithinS'] for c in judged):g} s of its image stream, after the run's end, and "
            f"{_span([len(c['isolatedDropsS']) for c in judged])} isolated ones in between, with no cause shown; the "
            "warm start of D-S1-1 ran before the attach in every run, in "
            f"{min(c['warmStart']['ms'] for c in counts.values()):.1f} to "
            f"{max(c['warmStart']['ms'] for c in counts.values()):.1f} ms, and did not keep the first 5 s free of "
            "dropped images;")


def drop_sentences(counts: dict) -> list[str]:
    """The sentences of GAP-DRIVING-014 on the dropped camera images, each figure read from drop_counts.json."""
    judged = [counts[label] for label in RUN_LABELS]
    isolated = [f"{RUN_LABELS[label]} at {_seconds(counts[label]['isolatedDropsS'])}" for label in RUN_LABELS
                if counts[label]["isolatedDropsS"]]
    without = [RUN_LABELS[label] for label in RUN_LABELS if not counts[label]["isolatedDropsS"]]
    stop, calib = counts["stop"], counts["calib_steer"]
    inside = "; ".join(f"{RUN_LABELS[label]} {counts[label]['wholeRunWindow']['dropped']}" for label in RUN_LABELS)
    return [
        "answered no: the score-interface record of each run of S1 holds dropped camera images, which "
        "drop_counts.json of the evidence directory places by their simulation time.",
        f"Each judged run drops {_either(c['droppedInFirst5s'] for c in judged)} images in the first 5 s after its "
        f"first image; {_span([c['droppedAtStreamEnd'] for c in judged])} in the last "
        f"{max(c['streamEndDropsWithinS'] for c in judged):g} s of its image stream, which goes on after the run's "
        "last world tick until the S-CORE side stops; and "
        f"{_span([len(c['isolatedDropsS']) for c in judged])} isolated images in between: "
        + ", ".join(isolated) + " after the first image, and none in " + ", ".join(without[:-1]) + " or "
        + without[-1] + ".",
        f"The run that stops the path drops {stop['droppedInFirst5s']} in its first 5 s and "
        f"{stop['droppedAtStreamEnd']} in the last {stop['streamEndDropsWithinS']:g} s of its image stream, which "
        f"ends at the stop, and the steering calibration run {calib['droppedInFirst5s']} in its first 5 s, "
        f"{calib['droppedAtStreamEnd']} at the end of its image stream and {len(calib['isolatedDropsS'])} isolated.",
        "The warm start of D-S1-1 (patch 0005 of the bench) ran before the attach in every run: the Launch Manager "
        "log of each run records 2 passes with the result yes, in "
        f"{min(c['warmStart']['ms'] for c in counts.values()):.1f} to "
        f"{max(c['warmStart']['ms'] for c in counts.values()):.1f} ms (score_side/state/launch_manager.log); it "
        "did not keep the first 5 s after the first image free of dropped images.",
        "The records show no cause of the drops.",
        "The evaluators judge a criterion over every run in the window from the run's first to its last world tick "
        "and count each drop.camera_image whose simulation time lies in it: "
        f"{_span([c['wholeRunWindow']['dropped'] for c in judged])} in each judged run ({inside}), the start-up drops "
        "and the isolated drops inside the run and none of the end of the image stream, and "
        f"{stop['wholeRunWindow']['dropped']} in the run that stops the path;",
    ]


def _code(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return _NOT_CODE.sub(lambda match: '""' if match.group().startswith('"') else " ", text)


def _body(text: str, header: str) -> str:
    matches = list(re.finditer(header, text))
    assert len(matches) == 1, f"expected one {header!r}, found {len(matches)}"
    start = matches[0].end() - 1
    assert text[start] == "{", f"{header!r} does not end with an opening brace"
    depth = 0
    for end in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[end], 0)
        if depth == 0:
            return text[start : end + 1]
    raise AssertionError(f"{header!r} has an unbalanced body")


def _flat(text: str) -> str:
    return " ".join(re.sub(r"^\s*\*\s?", "", text, flags=re.M).split())


def _docs(path: Path) -> str:
    return _flat(path.read_text(encoding="utf-8"))


def _requirements() -> dict[int, tuple[str, str]]:
    """Requirement number -> (usage name, verification method), from the phase 5 package."""
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    found = {}
    for match in re.finditer(r"requirement <'REQ-DRIVING-(\d{3})'> (\w+) : \w*RequirementCandidate \{", raw):
        body = _body(raw[match.start():], re.escape(match[0]))
        (method,) = re.findall(r'attribute :>> verificationMethod = "(\w+)";', body)
        found[int(match[1])] = (match[2], method)
    assert sorted(found) == NUMBERS
    return found


def _criteria() -> dict[int, str]:
    """Requirement number -> its success criteria, from the phase 5 package."""
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    found = {}
    for match in re.finditer(r"requirement <'REQ-DRIVING-(\d{3})'> (\w+) : \w*RequirementCandidate \{", raw):
        body = _body(raw[match.start():], re.escape(match[0]))
        (criteria,) = re.findall(r'attribute :>> successCriteria = "([^"]+)";', body)
        found[int(match[1])] = criteria
    assert sorted(found) == NUMBERS
    return found


def _usages() -> dict[int, tuple[str, str, str]]:
    """Case number -> (usage name, definition name, raw usage body with its doc)."""
    raw = SLICE.read_text(encoding="utf-8")
    out = {}
    for match in re.finditer(r"verification <'VC-DRIVING-(\d{3})'> (\w+) : (\w+) \{", raw):
        out[int(match[1])] = (match[2], match[3], _body(raw[match.start():], re.escape(match[0])))
    return out


def _definitions() -> dict[str, str]:
    code = _code(SLICE)
    return {m[1]: _body(code[m.start():], re.escape(m[0])) for m in re.finditer(r"\bverification def (\w+) \{", code)}


def _definition_docs() -> dict[str, str]:
    raw = SLICE.read_text(encoding="utf-8")
    return {m[1]: _flat(_body(raw[m.start():], re.escape(m[0]))) for m in re.finditer(r"\bverification def (\w+) \{", raw)}


# -- the cases ------------------------------------------------------------------------------------


def test_each_requirement_of_the_increment_is_verified_by_exactly_one_case() -> None:
    """Nine requirements, nine cases VC-DRIVING-036 to -044, each objective verifying the requirement of its own
    number with its subject bound to the realization on the bench, by the evidence decisions of 2026-11-18 (one
    case per requirement)."""
    requirements = _requirements()
    usages = _usages()
    definitions = _definitions()
    assert sorted(usages) == NUMBERS
    verified = {}
    for number, (usage, definition, _) in usages.items():
        body = definitions[definition]
        assert len(re.findall(r"\bobjective \w+ \{", body)) == 1, usage
        objective = _body(body, r"\bobjective \w+ \{")
        (target,) = re.findall(
            r"\bverify (\w+) \{ subject driverAssistanceSystem = verifiedBench\.assistanceSoftware; \}", objective)
        assert len(re.findall(r"\bverify\b", objective)) == 1, usage
        verified[number] = target
    assert verified == {n: name for n, (name, _) in requirements.items()}, "each case verifies its own requirement"
    assert len(definitions) == len(set(definitions)) == len(NUMBERS)


def test_the_case_ids_continue_the_series_and_are_unique_in_the_model() -> None:
    ids = []
    for path in sorted((ROOT / "textual-notation-of-model").rglob("*.sysml")):
        ids += re.findall(r"<'(VC-[A-Z0-9-]+)'>", path.read_text(encoding="utf-8"))
    assert len(set(ids)) == len(ids), "a verification-case id is declared once in the model"
    own = re.findall(r"<'(VC-DRIVING-\d{3})'>", SLICE.read_text(encoding="utf-8"))
    assert own == [f"VC-DRIVING-0{n}" for n in NUMBERS]
    increment_files = charter_package_files(FRAMING, "driverAssistanceCharter")
    assert SLICE in increment_files
    elsewhere = [i for path in increment_files if path != SLICE
                 for i in re.findall(r"<'(VC-DRIVING-\d{3})'>", path.read_text(encoding="utf-8"))]
    assert not elsewhere, "a case id belongs to the verification-evidence slice and nowhere else"
    earlier = [int(i[-3:]) for i in ids if i.startswith("VC-DRIVING-") and i not in own]
    assert earlier and max(earlier) + 1 == NUMBERS[0], "the numbers continue the VC-DRIVING series"


def _evidence(name: str) -> dict:
    path = EVIDENCE / name
    assert path.is_file(), f"the evidence directory has no {name}"
    return json.loads(path.read_text(encoding="utf-8"))


def _generator():
    spec = importlib.util.spec_from_file_location("generate_da_evidence_text", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_each_case_states_its_status_from_the_verdict_files_and_its_scenarios_settings_runs_and_bench() -> None:
    """Each usage doc opens with the status that the generator writes from the verdict files: the outcome and the
    verdict of the case in S1, read from verdicts.json (VC-DRIVING-039 from the desk analysis), never written by
    hand; then, as the first slice stated them, the scenarios by SC identity and enum literal, the settings, the runs
    and the bench that its requirement's criteria read."""
    verdicts = _evidence("verdicts.json")
    analysis = _evidence("analysis_039.generator.json")
    for number, (usage, _, body) in _usages().items():
        doc = _flat(body)
        settings, count, stop, method = CASE_RUNS[number]
        assert "Not started." not in doc, usage
        if number == 39:
            outcome = analysis["outcome"]
            verdict = {"passBoundedVerification": "pass", "failObservedBehavior": "fail"}.get(outcome, "inconclusive")
            assert doc.startswith(f"{{ doc /* Outcome: {outcome}; verdict: {verdict}. From the desk analysis, record "
                                  "commandFormAnalysisEvidence"), usage
        else:
            case = verdicts["cases"][f"VC-DRIVING-0{number}"]
            assert doc.startswith(f"{{ doc /* Outcome: {case['outcome']}; verdict: {case['verdict']}. Judged from "
                                  f"the S1 session {SESSION} by the case evaluators, with criteriaRecordIdentity "
                                  f"{case['criteriaRecordIdentity']} and evaluatorRevision "
                                  f"{case['evaluatorRevision']}."), usage
        assert doc.count("Scenarios: ") == 1, usage
        scenarios = sorted({SETTINGS[s] for s in settings})
        tail = doc.split("Scenarios: ", 1)[1]
        assert sorted(set(re.findall(r"AssistanceScenarioIdentity::(\w+)", tail))) == scenarios, usage
        for scenario in scenarios:
            assert f"{SC_IDS[scenario]} (AssistanceScenarioIdentity::{scenario})" in tail, (usage, scenario)
        named = re.search(r"Settings: (.*?)\. Runs:", tail)
        assert (re.findall(r"\b(\w+At\d\d)\b", named[1]) if named else []) == settings, usage
        if count:
            assert f"Runs: the two runs of each setting, {count}" in tail, usage
        assert (STOP_RUN in tail) is stop, usage
        assert (STOP_CLAUSE_ONLY in tail) is stop, usage
        assert "which is a run of SC-DRIVING-012 too" not in doc and "settle whether it is a judged run" not in doc
        assert (STOP_RUN_CARRIERS in tail) is (number in (38, 43)), usage
        assert (APART in tail) is ("curveAt30" in settings), usage
        kinds = "(test, analyze)" if method == "test" else "analyze"
        assert f"@VerificationMethod{{ kind = {kinds}; }}" in body, usage
        assert "subject verifiedBench :> driverAssistanceVerificationBench;" in body, usage
    assert "Scenarios: none; the case reads the realization of phase 8 and no run." in _flat(_usages()[39][2])
    assert "VVStatus::" not in SLICE.read_text(encoding="utf-8"), "this slice sets no status"


def test_the_model_text_is_what_the_generator_writes_from_the_evidence_directory() -> None:
    """The evidence records and the case statuses are generated, never edited: running the generator on the
    committed verdicts.json, records.json and analysis_039.generator.json changes nothing in the slice."""
    generator = _generator()
    text = SLICE.read_text(encoding="utf-8")
    result = generator.generate(text, _evidence("verdicts.json"), _evidence("records.json"),
                                _evidence("analysis_039.generator.json"), repo=ROOT, model_path=SLICE,
                                evidence_dir=EVIDENCE)
    assert result.text == text, ("the slice differs from what the generator writes from the evidence directory: "
                                 "run tools/refresh_driver_assistance_s1_evidence.py")


def test_the_records_are_one_per_run_of_s1_and_one_of_the_analysis_with_consecutive_identities() -> None:
    raw = SLICE.read_text(encoding="utf-8")
    found = re.findall(rf"(?m)^  item (\w+) : ({RUN_RECORD}|{ANALYSIS_RECORD}) \{{", raw)
    assert [name for name, _ in found] == RECORD_USAGES
    assert [kind for _, kind in found] == [RUN_RECORD] * 15 + [ANALYSIS_RECORD]
    prefix = "EVID-" + "DRIVING-"
    identities = []
    for name in RECORD_USAGES:
        body = _flat(_body(raw, rf"(?m)^  item {name} : \w+ \{{"))
        match = re.match(rf"\{{ doc /\* ({prefix}\d{{3}})\. ", body)
        assert match, name
        identities.append(match[1])
    assert identities == [f"{prefix}{n:03d}" for n in range(1, len(RECORD_USAGES) + 1)], \
        "the sequence starts with this slice and is consecutive"
    stop = _body(_code(SLICE), r"(?m)^  item pathStoppedRunEvidence : \w+ \{")
    assert re.search(r"attribute :>> setting;", stop), "the further run is no run of a setting"


def test_the_slice_header_records_the_second_slice_and_the_decisions_of_2026_11_21() -> None:
    header = _flat(SLICE.read_text(encoding="utf-8").split("*/", 1)[0])
    assert SECOND_SLICE in header
    positions = [header.index(decision) for decision in DECISIONS_1121]
    assert positions == sorted(positions), "the decisions of the day in their order"
    assert header.index(STOP_RUN_DECISION) < positions[0], "after the decisions of 2026-11-18"
    assert "No case has started" not in header and "keeps the verification status NotStarted" not in header
    assert ("A verdict of S1 is a verdict of the pinned candidate on this bench in simulation; this slice makes no "
            "acceptance, safety, compliance or certification claim, and no claim about UNECE R152.") in header
    assert "until the probes run" not in header


def test_the_cases_of_036_037_and_039_state_what_their_outcomes_rest_on() -> None:
    usages = _usages()
    expected = asm005_in_case(_evidence("commanded_deceleration.json"))
    for number in (36, 37):
        assert expected in _flat(usages[number][2]), number
    # the precise fact replaces every "no braking" (the correction of 2026-11-21)
    texts = {path.name: _flat(re.sub(r"(?m)^\s*\*\s?", "", path.read_text(encoding="utf-8")))
             for path in DRIVING.glob("driver_assistance_*.sysml")}
    texts["guide"] = _flat(GUIDE.read_text(encoding="utf-8"))
    for where, text in texts.items():
        for retired in ("commands no braking", "commanded no braking", "no braking was commanded", "commanded none",
                        "holds a deceleration of 1.0 m/s² or more"):
            assert retired not in text, (where, retired)
    assert ANALYSIS_BOUNDS in _flat(usages[39][2])
    for number in (38, 40, 41, 42, 43, 44):
        assert "ASM-DRIVING-005, the calibration" not in _flat(usages[number][2]).split("Values of the case")[0], number


def test_each_case_collects_by_its_requirements_method_and_analyzes_against_the_requirement() -> None:
    """Eight requirements state the method test and REQ-DRIVING-039 the method analyze: the eight cases collect
    the run record by test, the case of 039 collects the analysis record by analysis; all process and evaluate by
    analysis, to the increment's own outcome and the standard verdict."""
    requirements = _requirements()
    definitions = _definitions()
    for number, (usage, definition, _) in _usages().items():
        body = definitions[definition]
        method = requirements[number][1]
        assert method == CASE_RUNS[number][3], number
        record = ANALYSIS_RECORD if method == "analyze" else RUN_RECORD
        assert re.search(rf"action collectData \{{\s*@VerificationMethod\{{ kind = {method}; \}}\s*out item "
                         rf"retainedEvidence : {record};", body), usage
        assert re.search(r"action processData \{\s*@VerificationMethod\{ kind = analyze; \}\s*in item retainedEvidence : "
                         rf"{record} = collectData\.retainedEvidence;\s*out evaluatedOutcome : AssistanceEvidenceOutcome;",
                         body), usage
        assert re.search(r"action evaluateData \{\s*@VerificationMethod\{ kind = analyze; \}\s*in evaluatedOutcome : "
                         r"AssistanceEvidenceOutcome = processData\.evaluatedOutcome;", body), usage
        assert "out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);" in body, usage
        assert "return verdict : VerdictKind = evaluateData.verdict;" in body, usage
        assert re.search(rf"\bsubject verifiedBench : {BENCH_DEF};", body), usage
    docs = _definition_docs()
    for number, (_, definition, _) in _usages().items():
        lead = "Analysis" if CASE_RUNS[number][3] == "analyze" else "Test"
        assert f"doc /* {lead} of REQ-DRIVING-0{number}. collectData retains" in docs[definition], definition


def test_each_case_restates_the_values_scenarios_and_stop_clause_of_its_requirements_criteria() -> None:
    """A case checks the criterion its requirement states (the evidence decisions of 2026-11-18, one case per
    requirement): every value of the criterion (5.0 m/s², 1.0 s), its range of scenarios and its stop clause,
    extracted from ``successCriteria``, appear in the case definition's doc as often as in the criterion. The
    cases of the judged runs map a setting that is not judged, and the cases over every run a missing run or one with
    a dropped image, to inconclusiveMissingEvidence; the cases over SC-DRIVING-014 and SC-DRIVING-015 record what
    phase 5 asks System 2 to record there."""
    criteria = _criteria()
    docs = _definition_docs()
    found_values = found_scopes = found_stops = 0
    for number, (usage, definition, _) in _usages().items():
        doc, text = docs[definition], criteria[number]
        values = CRITERION_VALUE.findall(text)
        for value in set(values):
            assert doc.count(value) >= values.count(value), (usage, value)
        scopes = CRITERION_SCOPE.findall(text)
        for scope in scopes:
            assert scope in doc, (usage, scope)
        stop = CRITERION_STOP.search(text)
        assert bool(stop) is (number in (38, 43)), usage
        if stop:
            assert f"the further run of {stop[1]}" in doc, usage
            assert f"checks that in the further run {stop[2]}." in doc, usage
        judged = "SC-DRIVING-013 is judged" in text
        assert (NOT_JUDGED_OUTCOME in doc) is judged, usage
        assert (EVERY_RUN_OUTCOME in doc) is (not judged and CASE_RUNS[number][3] == "test"), usage
        assert (GUIDANCE in doc) is (number in (40, 41)), usage
        found_values += len(values)
        found_scopes += len(scopes)
        found_stops += bool(stop)
    assert (found_values, found_scopes, found_stops) == (3, 8, 2), "the extraction must not be vacuous"
    # by the amended terms, the clauses over every run read the runs of the settings only
    for name in ("WithholdWarningRequestVerification", "WithholdEmergencyBrakingVerification",
                 "RecordCandidateIdentityVerification"):
        assert ("collectData retains the record of each of the fourteen runs of SC-DRIVING-012 to SC-DRIVING-015:"
                in docs[name]), name
    assert "processData matches, in each of the fourteen runs, every driving command" in docs[
        "DrivingCommandOverSCOREVerification"]
    assert "at any time of those runs" in docs["DrivingCommandOverSCOREVerification"]
    assert "processData matches, in each of the ten runs, every warning request" in docs[
        "WarningRequestOverSCOREVerification"]
    assert TERMS_AMENDMENT in _docs(REQUIREMENTS), "the phase 5 terms carry the amendment"
    phase5 = _docs(REQUIREMENTS)
    assert f"System 2 records in each of their runs {GUIDANCE}." in phase5, "phase 5's own words"
    assert ("As phase 5 states, System 2 records in each of the runs of SC-DRIVING-014 and SC-DRIVING-015 "
            f"{GUIDANCE}, and the record holds them.") in docs["WithholdWarningRequestVerification"]


def test_every_case_is_performed_by_the_verification_system_once() -> None:
    system = _body(_code(SLICE), r"\bpart driverAssistanceVerificationSystem \{")
    performed = re.findall(r"\bperform (\w+);", system)
    assert performed == [usage for _, (usage, _, _) in sorted(_usages().items())]
    code = " ".join(_code(SLICE).split())
    assert ("dependency verificationSystemIsTheDriverAssistanceVerificationEnvironment from "
            "driverAssistanceVerificationSystem to driverAssistanceVerificationEnvironment;") in code
    assert (f"dependency assistanceEnvironmentGapOnVerificationSystem from {GAP_NAME} "
            "to driverAssistanceVerificationSystem;") in code
    assert re.search(r"\bpart driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem \{",
                     _code(FRAMING))


def test_no_validation_case_is_added_and_the_phase_4_reviews_stay_planned() -> None:
    code = _code(SLICE)
    assert "ValidationPlanningScenario" not in code and "passBoundedValidation?" in " ".join(code.split())
    assert "validation" not in " ".join(re.findall(r"\bverification <'[^']+'> (\w+)", code)).lower()
    docs = _docs(SLICE)
    assert ("The validation of the needs stays planned in phase 4 (SC-DRIVING-016 to SC-DRIVING-019). This slice "
            "adds no validation case.") in docs
    for plan in ("SC-DRIVING-016", "SC-DRIVING-017", "SC-DRIVING-018", "SC-DRIVING-019"):
        assert re.search(rf"part <'{plan}'> \w+ : ValidationPlanningScenario \{{", REQUIREMENTS.read_text(encoding="utf-8"))


# -- the vocabulary, the records and the bench ------------------------------------------------------------------


def test_the_outcome_vocabulary_is_the_increments_own_with_the_six_shared_literals() -> None:
    """The evidence decisions of 2026-11-18 (the outcome vocabulary): an own enum and verdict map with the
    precedent's six literals; the mapping is total, only the two pass literals give pass, error gives error and every
    other outcome inconclusive."""
    code = _code(SLICE)
    assert re.findall(r"(\w+);", _body(code, r"\benum def AssistanceEvidenceOutcome \{")) == OUTCOMES
    calc = " ".join(_body(code, r"\bcalc def MapAssistanceEvidenceOutcomeToVerdict \{").split())
    assert "in outcome : AssistanceEvidenceOutcome;" in calc
    branches = re.findall(r"outcome == AssistanceEvidenceOutcome::(\w+)\? VerdictKind::(\w+)", calc)
    assert branches == [("passBoundedVerification", "pass"), ("passBoundedValidation", "pass"),
                        ("failObservedBehavior", "fail"), ("errorEvidence", "error")]
    assert calc.rstrip("} ").endswith("else VerdictKind::inconclusive;")
    for foreign in ("DrivingEvidenceOutcome", "MiddlewareEvidenceOutcome", "DE4SDV_ClosedLoopDrivingVerificationEvidence",
                    "DE4SDV_MiddlewareVerificationEvidence"):
        assert foreign not in code, foreign
    assert re.findall(r"(\w+);", _body(code, r"\benum def AssistanceScenarioIdentity \{")) == list(SC_IDS)
    assert re.findall(r"(\w+);", _body(code, r"\benum def AssistanceSettingIdentity \{")) == list(SETTINGS)
    raw = SLICE.read_text(encoding="utf-8")
    assert set(re.findall(r"AssistanceScenarioIdentity::(\w+)", raw)) == set(SC_IDS)
    docs = _docs(SLICE)
    assert "Each setting runs twice and both runs count: fourteen runs." in docs
    assert ("REQ-DRIVING-038 and REQ-DRIVING-043 name, is no run of a setting and no judged run, and only the stop "
            f"clauses of those two requirements read it ({STOP_RUN_DECISION}); the next slice chooses its approach "
            "speed.") in docs
    assert "fifteenth" not in docs and "at one of the three settings" not in docs
    assert "A missing or partial record gives inconclusive, never pass." in docs


def test_the_slice_header_states_the_readings_the_cases_make() -> None:
    """The header lists the readings that the requirements leave to the cases: the inconclusive outcomes, the judged
    window over every run, which cases read the stop run, what the stop run stops, and the warning modes."""
    header = _flat(SLICE.read_text(encoding="utf-8").split("*/", 1)[0])
    for phrase in ("Where the requirements leave a reading to the cases, the cases read them so.",
                   "A setting that is not judged, a run that is missing and a run whose record shows a dropped image "
                   "within the window that a case judges give inconclusiveMissingEvidence, never pass; for a "
                   "criterion over every run, that window is the whole run.",
                   "is no run of a setting and no judged run, and only the stop clauses of REQ-DRIVING-038 and "
                   f"REQ-DRIVING-043 read it, as the terms of the requirements state since {STOP_RUN_DECISION}.",
                   "In that run the candidate's process keeps running and the path's carriers of the driving command "
                   "and of the warning request are stopped.",
                   "No case judges when the display and the sound give the warning "
                   "(counterClaimWarningModesNotJudgedHere)."):
        assert phrase in header, phrase


def test_the_run_record_binds_the_identities_the_decision_names() -> None:
    """The evidence decisions of 2026-11-18 (the evidence record): one retained record per run, read by every case of
    that run, with the candidate identity of REQ-DRIVING-044, the configured product and its receipt digest, the
    model revision, the build and the recorder's delay, the platform, gateway and simulator pins, the scenario, the
    setting and the simulated configuration, both clocks, the hosts and guest images, the warning-request contract,
    and the criteria record with the evaluators' revision."""
    code = _code(SLICE)
    record = _body(code, rf"\bitem def {RUN_RECORD} \{{")
    assert re.findall(r"\battribute (\w+) : ", record) == RUN_ATTRIBUTES
    assert "attribute scenario : AssistanceScenarioIdentity;" in record
    # the further run is no run of a setting: its record has no setting (review R6 of the 10a review)
    assert "attribute setting : AssistanceSettingIdentity[0..1];" in record
    assert "guestImageBuilds" not in code, "the guest images are part of executionEnvironmentIdentity"
    docs = _docs(SLICE)
    for phrase in (f"every case that reads the run reads this record ({DECISIONS})",
                   "It binds DRIVING-CONFIG-002 as its configurationIdentity.",
                   "receiptSha256 is the SHA-256 of the receipt the run ran against, as DRIVING-CONFIG-002 asks of the "
                   "evidence that binds it; if it differs from the receiptSha256 of DRIVING-CONFIG-002, the verdict "
                   "holds for DRIVING-CONFIG-002 only if the configuration's own receipt record did not change, which "
                   "the pull request that rebinds the digest states.",
                   "candidateRecordIdentity names the candidate identity record of REQ-DRIVING-044 of the run",
                   "VisionPilot at 014e0e7a with the DE4SDV S-CORE interface and the DE4SDV visualization recorder",
                   "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms "
                   "more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4; a "
                   "run on another host states the delay it measures",
                   "scenario names the run's scenario; setting names its setting for a run of a setting and is left "
                   "empty for the further run;",
                   "runIdentity names the run: the first or the second run of its setting, or the further run in "
                   "which the Eclipse S-CORE path is stopped, which is no run of a setting.",
                   "simulatedConfiguration names the simulated configuration of the run: the blueprints of the ego "
                   "vehicle and of the other vehicles of the scenario, the map and the road, the weather, the fixed "
                   "step of 0.05 s and synchronous mode, and the camera rig; a digest of the scenario definition that "
                   "fixes them is enough.",
                   "simulationClockSpan and wallClockSpan are the two clocks of the run, kept apart.",
                   "executionEnvironmentIdentity names the three hosts of the run, the simulator host, the S-CORE host "
                   "with its GPU and the guest host, and the builds of the SDV Core image and of the IVI image.",
                   "contractIdentity names the message type of the warning request on the guests, which phase 8 left "
                   "open until phase 10 (GAP-DRIVING-014).",
                   "criteriaRecordIdentity names the criteria record that the evaluators of the run read, and "
                   "evaluatorRevision the revision of those evaluators, so that each verdict names the criteria and "
                   "the evaluators that gave it (gapVehicleTargetCriteria).",
                   "phase 10 judges no run whose judged window holds a dropped image (MAP-DRIVING-DA-CAMERA-IMAGE); "
                   "for a criterion over every run, the judged window is the whole run.",
                   "A missing or partial record gives inconclusive, never pass. The records of the judged session S1 "
                   "follow this definition, one per run."):
        assert phrase in docs, phrase
    physical = _docs(PHYSICAL)
    for source in ("with a new message type for the warning request, open until phase 10", "one NVIDIA L4", "0.05 s"):
        assert source in physical, source
    analysis = _body(code, rf"\bitem def {ANALYSIS_RECORD} \{{")
    assert re.findall(r"\battribute (\w+) : ", analysis) == ANALYSIS_ATTRIBUTES
    assert "The evidence record of the analysis of REQ-DRIVING-039, which reads the realization and no run." in docs
    assert "No record exists yet." not in docs
    assert ("A missing or partial record gives inconclusive, never pass. The record of the analysis in the judged "
            "session S1 follows this definition, commandFormAnalysisEvidence.") in docs
    for name in ("DrivingCommandEventPayload", "MAP-DRIVING-DA-COMMAND", "reqDetectableDrivingCommandRejection"):
        assert name in _flat(_body(SLICE.read_text(encoding="utf-8"), rf"\bitem def {ANALYSIS_RECORD} \{{")), name
        assert name in PHYSICAL.read_text(encoding="utf-8"), name
    # each record is read by a case: the analysis record by the one analysis, the run record by the eight tests
    typed = re.findall(r"out item retainedEvidence : (\w+);", code)
    assert typed.count(ANALYSIS_RECORD) == 1 and typed.count(RUN_RECORD) == len(NUMBERS) - 1


def test_the_bench_refers_to_the_realization_in_driving_config_002() -> None:
    code = " ".join(_code(SLICE).split())
    bench = _body(code, rf"\bpart def {BENCH_DEF} \{{")
    assert ("ref part system1ConfiguredProduct :> DE4SDV_DriverAssistanceVariabilityConfiguration::configuredProduct;"
            in bench)
    assert ("ref part assistanceSoftware :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem = "
            "system1ConfiguredProduct.assistanceSoftware;") in bench
    assert len(re.findall(r"\bpart \w+ :", bench)) == 2 and not re.search(r"(?<!ref )\bpart \w+ :", bench), \
        "the bench owns no System 1 part"
    assert f"part driverAssistanceVerificationBench : {BENCH_DEF};" in code
    variability = _code(VARIABILITY)
    assert re.search(r"\bpart <'DRIVING-CONFIG-002'> configuredProduct : ", variability)
    assert "part assistanceSoftware : DriverAssistanceSoftwareRealization;" in variability
    assert "The bench is not a product selection." in _docs(SLICE)


def test_the_environment_gap_records_what_s1_shows_of_the_readiness_items_and_stays_deferred() -> None:
    """The environment decision of 2026-11-21: S1 shows the readiness items it shows, each with the session record
    that shows it; it answers whether the S-CORE host's own GPU keeps the candidate's cycle with no, with the dropped
    images of each run counted from its score-interface record (drop_counts.json); the capture of the start of the
    sound and the showing to the VisionPilot maintainers stay open; the gap stays a record, deferred to phase 11."""
    raw = SLICE.read_text(encoding="utf-8")
    gap = _body(raw, rf"\bpart <'{GAP}'> {GAP_NAME} : IncrementGap \{{")
    assert "attribute :>> disposition = LifecycleDisposition::deferred;" in gap
    doc = _flat(gap)
    assert doc.startswith("{ doc /* Recorded: the System 2 test environment ran the cases in the judged session "
                          "S1, and what of its readiness S1 does not show stays open."), doc[:120]
    positions = []
    for model, _ in GAP_ITEMS:
        assert doc.count(model) == 1, model
        positions.append(doc.index(model))
    assert positions == sorted(positions), "the items in their order"
    assert f"S1 answers them so (the environment decision of 2026-11-21, continuing {DECISIONS}):" in doc
    # where the images of each run drop, as drop_counts.json counts them in the run's score-interface record: the
    # distribution, never a rate, and no cause (the correction of 2026-11-21)
    for sentence in drop_sentences(_evidence("drop_counts.json")):
        assert doc.count(sentence) == 1, sentence
    for retired in ("of them fall within 5 s of simulation time after its first image and the rest spread over",
                    " of 599;", "in 20", "26 to 30 in each judged run"):
        assert retired not in doc, retired
    assert SOUND_CAPTURE in doc
    counts = _evidence("drop_counts.json")
    ticks = {counts[label]["runEnd"]["ticks"] for label in ("013_30_r2", "013_60_r2")}
    assert ticks == {62} and {counts[label]["runEnd"]["endReason"] for label in ("013_30_r2", "013_60_r2")} == {
        "at the speed of the target"}
    b1 = [statement.format(ticks=62) for statement in B1_STATEMENTS]
    for statement in b1:
        assert doc.count(statement) == 1, statement
    assert [doc.index(s) for s in b1] == sorted(doc.index(s) for s in b1), "B-1 in its order"
    assert doc.index(b1[0]) > doc.index(SOUND_CAPTURE) and doc.index(b1[-1]) < doc.index(
        "The gap stays a record of the environment"), "B-1 after the readiness items, before the disposition"
    assert ("The gap stays a record of the environment; its disposition is phase 11's. Deferred to phase 11.") in doc
    for retired in ("until the probes run (", "Deferred to that slice.", "which it has not done yet",
                    "nothing of phase 10 is built before the probes are read", "which is unmeasured"):
        assert retired not in doc, retired
    physical = _docs(PHYSICAL)
    for source in ("Open before phase 10: the link with the build of ONNX Runtime for CUDA",
                   "The candidate itself has not yet driven on CARLA 1.0",
                   "Whether the S-CORE host's own GPU keeps the cycle with the S-CORE build is not shown yet",
                   "the start of the sound on the guest is unmeasured",
                   "with a new message type for the warning request, open until phase 10",
                   "On 2026-11-18 the owner chose that nothing goes upstream before the scenarios of phase 10 have "
                   "run in CARLA: then the VisionPilot maintainers are shown a draft of the warning output and the "
                   "interface seam"):
        assert source in physical, source
    ids = sorted(set(re.findall(r"GAP-DRIVING-\d{3}", "".join(
        p.read_text(encoding="utf-8") for p in DRIVING.glob("*.sysml")))))
    assert max(ids) == GAP and raw.count(f"<'{GAP}'>") == 1, "the next free gap number of the driving series"
    assert sum(p.read_text(encoding="utf-8").count(f"<'{GAP}'>") for p in DRIVING.glob("*.sysml")) == 1


# -- the assurance structure ----------------------------------------------------------------------


def test_each_claim_answers_one_phase_1_concern_and_its_argument_cites_the_right_cases() -> None:
    """The evidence decisions of 2026-11-18 (claims now): one claim per answered phase 1 concern, each argument
    citing the planned cases; vehicleTargetCriteriaConcern, answered by the phase 5 table, has none. Each claim
    restates every value of the criteria of the requirements its argument cites; only the argument that cites the
    analysis of REQ-DRIVING-039 reads an analysis."""
    code = _code(SLICE)
    raw = SLICE.read_text(encoding="utf-8")
    usages = {n: u for n, (u, _, _) in _usages().items()}
    criteria = _criteria()
    framing = _code(FRAMING)
    phase1 = re.findall(r"\bconcern (\w+) : (\w+Concern) \{", framing)
    assert sorted(c for c, _ in phase1 if c != "driverAssistanceBoundary") == sorted(
        [concern for concern, _ in CLAIMS.values()] + [UNCLAIMED_CONCERN])
    for stem, (concern, numbers) in CLAIMS.items():
        claim = _flat(_body(raw, rf"\brequirement {stem}Claim : DriverAssistanceClaim \{{"))
        assert f"doc /* Answers {concern}. " in claim, stem
        head, tail = claim.split(f"subject claimSubject : {BENCH_DEF}; require constraint {{", 1)
        assert head.rstrip(" /").endswith(CLAIM_STATE), stem
        assert "no case has started" not in claim, stem
        assert tail.startswith(" doc /* The claim requires "), stem
        assert "; it excludes " in tail, stem
        cites = re.search(rf"dependency {stem}ArgumentCitesCases\s+from {stem}Argument\s+to ([^;]+);", code)
        assert cites, stem
        assert re.findall(r"\w+", cites[1]) == [usages[n] for n in numbers], stem
        argument = _flat(_body(raw, rf"\brequirement {stem}Argument : DriverAssistanceArgument \{{"))
        assert re.findall(r"VC-DRIVING-0(\d\d)", argument) == [str(n) for n in numbers], stem
        assert "the argument holds once every cited case has a pass verdict and fails with any fail" in argument
        assert ("or of its analysis" in argument) is (39 in numbers), stem
        for value in {v for n in numbers for v in CRITERION_VALUE.findall(criteria[n])}:
            assert value in head, (stem, value)
        assert re.search(rf"dependency claimSupportedBy{stem[0].upper() + stem[1:]}Argument\s+from {stem}Argument "
                         rf"to {stem}Claim;", code)
    # the run scope of each claim is that of its cases: no claim reads "every run" or "each run" and so takes the
    # stop run in; the stop run comes in only beside a stop clause, and in candidateVerdictClaim as its stated limit
    assert list(CLAIM_RUN_SCOPES) == list(CLAIMS)
    for stem in CLAIMS:
        claim = _flat(_body(raw, rf"\brequirement {stem}Claim : DriverAssistanceClaim \{{"))
        head = claim.split(f"subject claimSubject : {BENCH_DEF};", 1)[0]
        positions = []
        for scope in CLAIM_RUN_SCOPES[stem]:
            assert head.count(scope) == 1, (stem, scope)
            positions.append(head.index(scope))
        assert positions == sorted(positions), stem
        assert not re.search(r"\b(?:every|each|all) runs?\b|\bstop run\b|\bfifteen\b", head), stem
        stop_mentions = head.count("the further run of SC-DRIVING-012 with the path stopped")
        assert stop_mentions == (stem in STOP_RUN_CLAIMS), stem
    vehicle_target = _flat(_body(raw, r"\brequirement vehicleTargetResponseClaim : DriverAssistanceClaim \{"))
    assert ("commands a deceleration of at least 5.0 m/s² at each instant of the functional part at which the "
            "needed deceleration to the target is at least 5.0 m/s²") in vehicle_target
    assert ("gives a warning request at its boundary at least 1.0 s of simulation time before the start of the "
            "first emergency braking of the run") in vehicle_target
    assert re.findall(r"\brequirement (\w+)Claim : DriverAssistanceClaim \{", code) == list(CLAIMS)
    assert UNCLAIMED_CONCERN not in " ".join(re.findall(r"Answers (\w+)\.", raw))
    assert ("vehicleTargetCriteriaConcern is answered by the requirement definition table of phase 5, and no run "
            "answers it.") in _docs(SLICE)
    assert {n for _, numbers in CLAIMS.values() for n in numbers} == set(NUMBERS), "every case is cited"
    for definition, kind in [("DriverAssistanceClaim", "AssuranceClaim"),
                             ("DriverAssistanceArgument", "AssuranceArgument"),
                             ("DriverAssistanceCounterClaim", "AssuranceCounterClaim")]:
        assert f"requirement def {definition} :> {kind};" in code
    assert "RequirementCandidate" not in code, "the assurance elements specialize the kernel's assurance kinds"
    assert not re.search(r"\bsatisfy\b", code)


def test_each_counter_claim_restates_a_non_claim_of_the_framing_and_is_tied_to_its_record() -> None:
    code = _code(SLICE)
    raw = SLICE.read_text(encoding="utf-8")
    for stem, (targets, home) in COUNTER_CLAIMS.items():
        doc = _flat(_body(raw, rf"\brequirement counterClaim{stem} : DriverAssistanceCounterClaim \{{"))
        ties = re.findall(rf"dependency (counterClaim{stem}BoundTo\w*)\s+from counterClaim{stem} to (\w+);", code)
        assert ties == [(f"counterClaim{stem}BoundTo{suffix}", target)
                        for suffix, target in zip(TIE_SUFFIXES.get(stem, [""]), targets)], stem
        for target in targets:
            assert re.search(rf"\bpart (<'[A-Z0-9-]+'> )?{target} : \w+ \{{", _code(home)), (stem, target)
            named = target if home is not SLICE else GAP
            assert f"{named})." in doc or f"{named}, " in doc or f", {named})" in doc or f"names {named}" in doc, \
                (stem, named)
            if home is not SLICE:
                assert f"private import DE4SDV_DriverAssistanceFraming::{target};" in code, target
    assert re.findall(r"\brequirement counterClaim(\w+) : DriverAssistanceCounterClaim \{", code) == list(COUNTER_CLAIMS)
    docs = _docs(SLICE)
    assert ("No on-road, production-readiness, safety-approval, compliance, type-approval or certification claim, and "
            "none about UNECE R152") in docs
    assert "whether and when the display and the sound give the warning is the planned review SC-DRIVING-018" in docs
    assert ("No verdict comes from training the candidate's networks, or from tuning the candidate or a scenario "
            "until a case passes: a fail stays a recorded result (candidateTuningOutOfScope).") in docs
    assert ("their results for that increment's application are no evidence for this candidate, and each case reads "
            "only the records of its own runs (asmBenchReuse).") in docs
    assert BENCH_COUNTER_CLAIM in docs
    assert "No case has started and no evidence record exists" not in docs
    framing = _docs(FRAMING)
    assert "tuning the candidate or a scenario until a case passes" in framing
    assert "Their results for the first application are not evidence for this one." in framing


def test_the_slice_makes_no_compliance_or_regulation_claim_and_reports_runs_only_in_records() -> None:
    """The text written by hand reports no behavior of a run in a past form: what a run shows is in the generated
    records and statuses, whose values are recorded strings and evaluator texts. No text claims an approval, and
    every sentence that names UNECE R152 outside a recorded value states what is not claimed."""
    raw = SLICE.read_text(encoding="utf-8")
    generator = _generator()
    hand = generator.remove_generated(raw)
    for vc in [f"VC-DRIVING-0{n}" for n in NUMBERS]:
        block = _body(hand, rf"verification <'{vc}'> \w+ : \w+ \{{")
        status = re.search(r"doc /\*\s*\*\s*(Outcome: .*?)\n\s*\*\n", block, re.S)
        assert status, vc
        hand = hand.replace(status[1], "", 1)
    hand = re.sub(r'"(?:[^"\\]|\\.)*"', '""', hand)
    assert not re.search(r"(?i)\b(?:braked|warned|collided|avoided|detected|passed|failed)\b", hand)
    assert not re.search(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b", raw)
    sentences = [s for s in re.split(r"(?<=\.)\s+", _flat(hand)) if "R152" in s]
    assert len(sentences) >= 3
    for sentence in sentences:
        assert re.search(r"\b(?:no|none|excludes)\b", sentence), sentence
    assert not re.search(r"(?i)\bthe owner (?:said|wrote|asked|told)\b|[\u201c\u201d]", raw), \
        "the decisions are stated neutrally and dated, never quoted"
    assert _flat(raw).count(DECISIONS) >= 3


def test_the_assurance_view_frames_the_phase_1_assurance_concern_and_links_everything() -> None:
    code = _code(SLICE)
    view = _body(code, r"\bview driverAssistanceAssuranceView \{")
    viewpoint = " ".join(_body(view, r"\bviewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint \{").split())
    assert viewpoint == "{ frame driverAssistanceArgumentationAssuranceConcern; frame candidateVerdictConcern; }"
    assert re.findall(r"\bconcern (\w+) : ArgumentationAssuranceConcern \{", _code(FRAMING)) == ["candidateVerdictConcern"]
    exposed = re.findall(r"\bexpose ([\w:]+);", view)
    usages = [u for _, (u, _, _) in sorted(_usages().items())]
    expected = ([f"{s}Claim" for s in CLAIMS] + [f"{s}Argument" for s in CLAIMS]
                + [f"counterClaim{s}" for s in COUNTER_CLAIMS] + usages
                + [RUN_RECORD, ANALYSIS_RECORD] + RECORD_USAGES + [BENCH_DEF, GAP_NAME]
                + [target for targets, home in COUNTER_CLAIMS.values() if home is not SLICE for target in targets]
                + [f"claimSupportedBy{s[0].upper() + s[1:]}Argument" for s in CLAIMS]
                + [f"{s}ArgumentCitesCases" for s in CLAIMS]
                + [f"counterClaim{s}BoundTo{suffix}" for s in COUNTER_CLAIMS for suffix in TIE_SUFFIXES.get(s, [""])])
    assert exposed == expected
    assert len(exposed) == 86, "the count of exposed elements"
    view_doc = _flat(_body(SLICE.read_text(encoding="utf-8"), r"\bview driverAssistanceAssuranceView \{"))
    assert (f"the {NUMBER_WORDS[len(CLAIMS)].lower()} claims" in view_doc
            and f"the {NUMBER_WORDS[len(COUNTER_CLAIMS)].lower()} counter-claims" in view_doc)
    assert "render asTreeDiagram;" in view and "attribute maxCompartmentEntries = 0;" in view
    assert "before any run" not in view_doc
    assert ("the evidence record of a run and the record of the analysis, the sixteen records of the judged session "
            "S1") in view_doc
    assert len(re.findall(r"\bview \w+", code)) == 1, "one view in the phase"
    concern = _body(code, r"\bconcern driverAssistanceArgumentationAssuranceConcern : ArgumentationAssuranceConcern \{")
    assert re.findall(r"\bstakeholder \w+ : (\w+);", concern) == [
        "ProductLineEngineer", "VerificationEngineer", "OpenSourceReviewer"]
    assert "Product-line engineers, verification engineers and open-source reviewers need" in _docs(SLICE)


def test_the_views_per_phase_list_names_the_assurance_viewpoint_for_phase_10() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"- \*\*Phase 10\*\* — one tree: `ArgumentationAssuranceViewpoint`", text)


def test_the_package_declares_no_name_that_another_model_package_declares() -> None:
    kinds = (r"(?:part def|part|item def|enum def|calc def|verification def|verification|requirement def|requirement|"
             r"concern|view|dependency)")
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(?:<'[^']*'>\s*)?(\w+)", _code(SLICE)))
    assert len(declared) >= 70, "the population of the check must not be vacuous"
    anywhere = re.compile(rf"\b{kinds}\s+(?:<'[^']*'>\s*)?(\w+)")
    taken: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == SLICE:
                continue
            for name in anywhere.findall(strip_comments(path.read_text(encoding="utf-8"))):
                if name in declared:
                    taken.setdefault(name, []).append(path.name)
    assert not taken, f"declared in another package too: {taken}"


# -- the charter and the guide --------------------------------------------------------------------


def test_the_charter_names_the_phase_10_package_last() -> None:
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", FRAMING.read_text(encoding="utf-8"), re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-2:] == [
        "DE4SDV_DriverAssistanceVariabilityConfiguration", PACKAGE]
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", _code(SLICE)) == [PACKAGE], "one global package per file"


def test_the_guide_describes_the_first_phase_10_slice() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    order = [guide.index(heading) for heading in ("## Variability and configuration (Phase 9)",
                                                  "## Verification and evidence (Phase 10)",
                                                  "## What the framing already records as open")]
    assert order == sorted(order)
    raw_section = guide.split("## Verification and evidence (Phase 10)", 1)[1].split("\n## ", 1)[0]
    section = " ".join(raw_section.split())
    for text in ("VC-DRIVING-036", "VC-DRIVING-044", "DRIVING-CONFIG-002", "**One case per requirement.**",
                 "2026-11-18", GAP, "the stop run", "simulation-clock and wall-clock spans",
                 f"{NUMBER_WORDS[len(COUNTER_CLAIMS)]} counter-claims", f"{NUMBER_WORDS[len(CLAIMS)]} claims",
                 "Argumentation Assurance", "**No validation case.**",
                 "`candidateVerdictConcern`", "`vehicleTargetCriteriaConcern` has no claim",
                 "Missing or partial evidence, and a setting whose runs are not judged, is inconclusive, never pass.",
                 "In the cases that read every run, a run that is missing, or whose record shows a dropped image "
                 "within the run, is inconclusive too: for them the judged window is the whole run.",
                 "measured on an S-CORE host with an NVIDIA L4 (a run on another host states its own)",
                 "the simulated configuration (the vehicles, the map and road, the weather, the 0.05 s step in "
                 "synchronous mode and the camera rig)",
                 "the three hosts with the S-CORE host's GPU and the guest images, the message type of the warning "
                 "request, and the criteria record with the revision of the evaluators that read it",
                 "(tied also to `gapVehicleTargetCriteria`)", "no tuning until a case passes",
                 "no evidence from the reused bench's earlier results",
                 "In the stop run the candidate's process keeps running, and the Launch Manager stops the path's "
                 "carriers of the driving command and of the warning request; the next slice fixes which processes "
                 "these are.",
                 f"By the Phase 5 terms, as {STOP_RUN_DECISION} amended them, it is no run of a setting and no "
                 "judged run, and "
                 "only the stop clauses of those two requirements read it, in VC-DRIVING-038 and VC-DRIVING-043; the "
                 "next slice chooses its approach speed.",
                 "(../../textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml)"):
        assert text in section, text
    # the settings and their count, from the enum literals, as the guide and the enum doc state them
    speeds: dict[str, list[str]] = {}
    for setting, scenario in SETTINGS.items():
        speeds.setdefault(SC_IDS[scenario], []).append(re.findall(r"\d+$", setting)[0])
    parts = [f"{sc} at {', '.join(v[:-1]) + ' and ' + v[-1] if len(v) > 1 else v[0]} km/h" for sc, v in speeds.items()]
    setting_doc = _flat(_body(SLICE.read_text(encoding="utf-8"), r"\benum def AssistanceSettingIdentity \{"))
    for part in parts:
        assert part in setting_doc, part
    runs = NUMBER_WORDS[2 * len(SETTINGS)]
    assert (f"**The runs.** {NUMBER_WORDS[len(SETTINGS)]} settings, each run twice, both runs counting: "
            f"{', '.join(parts[:-1])} and {parts[-1]}, {runs} runs.") in section
    # each readiness item of GAP-DRIVING-014 as S1 leaves it, in the guide's words
    gap_bullet = section.split("**The test environment**", 1)[1].split("- **", 1)[0]
    for _, phrase in GAP_ITEMS:
        assert phrase in gap_bullet, phrase
    # where the images drop, from drop_counts.json, never a rate and no cause (the correction of 2026-11-21)
    assert guide_drop_phrase(_evidence("drop_counts.json")) in gap_bullet
    assert ("the end of the second runs of SC-DRIVING-013 after 62 ticks at the speed of the target (B-1): open, a "
            "bench item for the next session") in gap_bullet
    assert "most of them in its first 5 s" not in gap_bullet
    # the second slice: the evidence of record, with no value of a verdict written by hand
    assert "This first slice is model only" not in section and "every requirement keeps `NotStarted`" not in section
    evidence = " ".join(raw_section.split("### Phase 10 evidence", 1)[1].split())
    for text in ("The evidence of record is the judged session S1, session 20261121T014447Z",
                 "(../../implementation/driver-assistance-bench/evidence/s1-20261121T014447Z/README.md)",
                 "the evidence-of-record decision of 2026-11-21", "the drop-rule decision of 2026-11-21",
                 "the deceleration calibration decision of 2026-11-21", "the status decision of 2026-11-21",
                 "the check-value bound decision of 2026-11-21", "the environment decision of 2026-11-21",
                 "`VVStatus::Completed` for REQ-DRIVING-036, REQ-DRIVING-037, REQ-DRIVING-039 and REQ-DRIVING-042",
                 "`VVStatus::CompletedUnsuccessful` for REQ-DRIVING-038, REQ-DRIVING-040, REQ-DRIVING-041, "
                 "REQ-DRIVING-043 and REQ-DRIVING-044",
                 "`tools/refresh_driver_assistance_s1_evidence.py`",
                 "A verdict of S1 is a verdict of the pinned candidate on this bench in simulation"):
        assert text in evidence, text
    for outcome in OUTCOMES:
        assert outcome not in evidence, f"the guide copies no outcome of a verdict: {outcome}"
    assert ("**The deceleration calibration.** The condition on ASM-DRIVING-005 bears on a pass of VC-DRIVING-036 "
            "and VC-DRIVING-037, not on their fail in S1: it concerns how the simulated vehicle achieves a commanded "
            "deceleration, and the fails rest on the commanded values; no run of SC-DRIVING-012 holds a commanded "
            "deceleration beyond 0.53 m/s² (the deceleration calibration decision of 2026-11-21).") in evidence
    criteria = _criteria()
    rows = re.findall(r"^\| (VC-DRIVING-\d{3}) \| (REQ-DRIVING-\d{3}), ([^|]+) \| ([^|]+) \| (\w+) \|$", raw_section,
                      re.M)
    assert [(case, requirement) for case, requirement, _, _, _ in rows] == [
        (f"VC-DRIVING-0{n}", f"REQ-DRIVING-0{n}") for n in NUMBERS]
    for (_, _, title, runs, method), number in zip(rows, NUMBERS):
        settings, count, stop, model_method = CASE_RUNS[number]
        assert method == {"test": "test", "analyze": "analysis"}[model_method], number
        assert (count or "no run") in runs and ("the stop run" in runs) is stop, number
        # a value in the table is its requirement's (the warning request 1.0 s before the emergency braking)
        values = CRITERION_VALUE.findall(title)
        assert all(value in criteria[number] for value in values), number
        assert (values == ["1.0 s"]) is (number == 42), number
    assert "instrument" not in section and "fifteenth" not in section
    assert all(("for the stop clause" in runs) is CASE_RUNS[number][2] for (_, _, _, runs, _), number in zip(rows, NUMBERS))
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_driver_assistance_verification_evidence.py" in check
    flat = " ".join(guide.split())
    assert "The increment ended at its baseline decision." in flat and "The next model obligation is" not in flat
