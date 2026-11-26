"""INC-HMI-001 phase 10, first slice: the verification cases of the HMI display requirements.

Lexical pins on ``hmi_display_verification_evidence.sysml``: one case per requirement, each bound to the realization
of the HMI display in HMI-CONFIG-001, not started, each naming the scenarios that its requirement's criteria read;
the run-level evidence record and the record of the one inspection; the environment gap that continues the
readiness questions of phase 8; one claim per phase 1 concern whose question the cases answer, their arguments and
the counter-claims, which the assurance view links; the code of the package whole, as a skeleton, and every doc of
the package by its text; the guide's Phase 10 section, block by block; and the three amendments of earlier phases
that the slice carries. The invariants of every verification model are in ``test_verification_model_invariants.py``;
the licensed Syside run validates the model.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import charter_package_files, strip_comments

ROOT = Path(__file__).resolve().parents[1]
HMI = ROOT / "textual-notation-of-model" / "packages" / "features" / "hmi"
SLICE = HMI / "hmi_display_verification_evidence.sysml"
REQUIREMENTS = HMI / "hmi_display_needs_requirements.sysml"
FRAMING = HMI / "hmi_display_framing.sysml"
PHYSICAL = HMI / "hmi_display_physical_software_realization.sysml"
VARIABILITY = HMI / "hmi_display_variability_configuration.sysml"
GUIDE = ROOT / "docs" / "guides" / "hmi-display-increment.md"
MODEL_ROOTS = [ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering"]

PACKAGE = "DE4SDV_HmiDisplayVerificationEvidence"
BENCH_DEF = "HmiDisplayVerificationBench"
RUN_RECORD = "RetainedHmiDisplayRunEvidence"
INSPECTION_RECORD = "RetainedHmiDisplayRealizationInspection"
OUTCOME = "HmiDisplayEvidenceOutcome"
VERDICT_MAP = "MapHmiDisplayEvidenceOutcomeToVerdict"
GAP = "GAP-HMI-005"
NEXT_OBLIGATION = ("The next model obligation is **Phase 10**: verification and evidence, its second slice, which "
                   "follows the readiness probes and adds the bench, the runs, the retained records and the statuses. "
                   "The first slice holds the cases that `verificationCaseVerifiesRequirement` and "
                   "`requirementVerifiedByVerificationCase` read; `verificationCaseHasEvidenceRecordOrStatus` stays "
                   "advisory until runs exist. With those two checks met, the first open blocking check of the Method "
                   "Check is Phase 11's `incrementHasBaselineDecision`. Do not jump from the cases to implementation "
                   "before the probes, and claim no runtime gate.")
GAP_NAME = "gapHmiVerificationEnvironmentOpen"
IDENTITY_TERM = "the identity-term amendment of phase 10"
SCENE_FORM = "the scene-form amendment of phase 10"
NUMBERS = list(range(1, 11))
INSPECTED = 9

SC_IDS = {"warningScenarios": "SC-HMI-001", "noReactionScenarios": "SC-HMI-002", "sceneAppOut": "SC-HMI-003",
          "androidBoots": "SC-HMI-004", "androidHangs": "SC-HMI-005", "androidRestarts": "SC-HMI-006",
          "warningRequestStops": "SC-HMI-007"}
ALL = list(SC_IDS)
OUTAGES = ["sceneAppOut", "androidBoots", "androidHangs", "androidRestarts"]
#: requirement number -> the scenarios its criterion names, in the order of the enum
CASE_SCENARIOS = {
    1: ALL, 2: ALL, 3: ["warningScenarios", "noReactionScenarios", "warningRequestStops"],
    4: ["warningScenarios", "noReactionScenarios", "warningRequestStops"],
    5: ["warningScenarios", "noReactionScenarios"], 6: ALL, 7: ALL, 8: OUTAGES, 9: [], 10: ALL,
}
SC_REFERENCE = re.compile(r"SC-HMI-(\d{3})(?: to SC-HMI-(\d{3}))?")
OUTCOMES = ["passBoundedVerification", "passBoundedValidation", "failObservedBehavior",
            "inconclusiveMissingEvidence", "blockedTargetRuntime", "errorEvidence"]
RUN_ATTRIBUTES = [
    ("configurationIdentity", "ScalarValues::String"), ("receiptSha256", "ScalarValues::String"),
    ("modelRevision", "ScalarValues::String"), ("runIdentity", "ScalarValues::String"),
    ("scenario", "HmiDisplayScenarioIdentity"), ("displayIdentityRecord", "ScalarValues::String"),
    ("independentEngineerIdentity", "ScalarValues::String"), ("candidateRecordIdentity", "ScalarValues::String"),
    ("simulationClockSpan", "ScalarValues::String"), ("wallClockSpan", "ScalarValues::String"),
    ("retainedObservations", "ScalarValues::String"), ("claimBoundary", "ScalarValues::String")]
INSPECTION_ATTRIBUTES = [
    ("configurationIdentity", "ScalarValues::String"), ("receiptSha256", "ScalarValues::String"),
    ("modelRevision", "ScalarValues::String"), ("inspectedRealization", "ScalarValues::String"),
    ("inspectorIdentity", "ScalarValues::String"), ("claimBoundary", "ScalarValues::String")]
#: counter-claim -> (the record that keeps it open, its file)
COUNTER_CLAIMS = {
    "RecordingIsNoVerdict": ("hmiDisplayQuestion", FRAMING),
    "SimulatedConfigurationOnly": ("asmHmiSimulationStandsIn", FRAMING),
    "DrivingBenchResultsNoEvidence": ("asmHmiDrivingBenchReuse", FRAMING),
    "SceneFromAStandIn": ("gapHmiSceneOutput", FRAMING),
    "PerceptionNotJudged": ("hmiPerceptionQualityOutOfScope", FRAMING),
    "NoComplianceOrApproval": ("hmiOnRoadOperationOutOfScope", FRAMING),
    "NoMemberProduct": ("gapHmiDisplayInProductLine", FRAMING),
    "NoUpstreamEndorsement": ("gapHmiUpstreamContact", FRAMING),
    "DrawingToleranceUnset": ("gapHmiDrawingToleranceUnset", PHYSICAL),
    "EnvironmentOpenNoVerdict": (GAP_NAME, SLICE),
}
#: what GAP-HMI-005 continues: its dependency name -> (target, the package that declares the target)
GAP_CONTINUES = {
    "hmiEnvironmentGapContinuesRendererIntegration": ("gapHmiRendererIntegration", FRAMING),
    "hmiEnvironmentGapContinuesRendererAssumption": ("asmHmiRendererWithoutGraphicsCard", FRAMING),
    "hmiEnvironmentGapContinuesBenchSpeedFeed": ("gapHmiBenchSpeedFeed", PHYSICAL),
}
#: the term of the display identity names these elements of phase 8 since the identity-term amendment
IDENTITY_ELEMENTS = ["of the files of the build of the vehicle data publisher in the SDV Core VM",
                     "of the builds of the identity recording service and of the composition of the display on the "
                     "central computer", "of the image of the SDV Core VM"]
#: the fields that the scene-form amendment types: (owner, attribute, type)
SCENE_FIELDS = [("DisplaySceneMessage", "lanePoints", "DisplayScenePoint[0..*] ordered"),
                ("DisplaySceneMessage", "pathPoints", "DisplayScenePoint[0..*] ordered"),
                ("DisplaySceneMessage", "sceneObjects", "DisplaySceneObject[0..*]"),
                ("DisplayScenePoint", "ahead", "ISQ::LengthValue"), ("DisplayScenePoint", "left", "ISQ::LengthValue"),
                ("DisplaySceneObject", "objectPosition", "DisplayScenePoint"),
                ("DisplaySceneObject", "level", "ScalarValues::Integer")]
SCENE_UNITS = ("capture time in simulation seconds; positions and distance in m; speed of the closest object in m/s, "
               "negative while it approaches; level an integer, 1 for the same lane and 2 for the adjacent lane")
AUTODRIVE_CLAUSE = "marks no box of the objects and no mark of AutoDrive alone as that object"
BY_REFERENCE = "marks none of the marks that the criterion of REQ-HMI-002 excludes as that object"
#: claim stem -> the phase 1 concern it answers, in the order in which the Source lines of the requirements name them
CLAIMS = {"DisplayInputs": "hmiDisplayInputsConcern", "ContentVariance": "hmiContentVarianceConcern",
          "WarningSequence": "hmiWarningSequenceConcern", "ContentCurrency": "hmiContentCurrencyConcern",
          "AndroidOutage": "hmiAndroidOutageConcern", "RendererAllocation": "hmiRendererAllocationConcern",
          "RendererPath": "hmiRendererPathConcern", "DisplayVerdict": "hmiDisplayVerdictConcern"}
VERDICT_CONCERN = "hmiDisplayVerdictConcern"
OWNER_CHOICES = ("The five choices of this slice are the owner decision of 2026-11-26, as INC-DRIVING-002 took them: "
                 "one case per requirement; an outcome vocabulary and a verdict map of the increment's own, with the "
                 "six literals of INC-DRIVING-002; the claims, their arguments and the counter-claims now, the "
                 "counter-claims from the non-claims of the framing; one evidence record per run, read by every case "
                 "of that run; and the test environment as a gap that continues the gaps of phase 8 until the "
                 "readiness probes fix its host and its topology.")
GUIDE_CHOICES = ("The five choices of the slice are the owner decision of 2026-11-26, as INC-DRIVING-002 took them: "
                 "one case per requirement, an outcome vocabulary of the increment's own, the claims now, one evidence "
                 "record per run and the test environment as a gap.")
GUIDE_CORRECTIONS = ("Phase 8 also takes two corrections in place: COVESA VSS types the distance to the "
                     "object that the system acts on in the scene message, and GAP-HMI-003 is carried "
                     "open.")
BANNED_FORMS = re.compile(r"\b(?:flow|bind|binding|interface|message|succession|satisfy)\b")
PAST_BEHAVIOR = re.compile(r"(?i)\b(?:braked|warned|stopped|collided|avoided|detected|passed|failed|displayed|"
                           r"rendered|showed|crashed|hung)\b")
APPROVAL = re.compile(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b")

#: The text of each claim and of its constraint, whitespace collapsed (generated from the head).
CLAIM_TEXTS = {
    "DisplayInputs": (
        "Answers hmiDisplayInputsConcern. For HMI-CONFIG-001 in the simulated configuration, in the runs of "
        "SC-HMI-001 to SC-HMI-007 that the criterion of REQ-HMI-001 names, the HMI display shows each scene that "
        "reaches it outside an outage in the IVI VM, or a newer scene, as its source gives it, with its lane points, "
        "its path and each of its objects with its level, and no lane, path or object that no scene of the run gives. "
        "A claim to be proven: no case has started.",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes the simulator's own record of the scene and an estimate of the display's own as a "
        "source of the scene, and how well the candidate perceives."),
    "ContentVariance": (
        "Answers hmiContentVarianceConcern. For HMI-CONFIG-001, the scene that the HMI display shows in the runs that "
        "the criterion of REQ-HMI-001 names is the scene of the one source of the scene in that configuration, as "
        "that source gives it, and no scene of another driving application; while the candidate gives no scene, that "
        "source is the context stand-in of phase 8 (gapHmiSceneOutput). A claim to be proven: no case has started.",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes the scenes of the other driving applications of the product line, and which content "
        "becomes common to the member products, which is for the lifecycle decision."),
    "WarningSequence": (
        "Answers hmiWarningSequenceConcern. For HMI-CONFIG-001 in the simulated configuration, in the runs that the "
        "criteria of REQ-HMI-004 and REQ-HMI-005 name, each mode of the collision warning is on from less than 0.1 s "
        "of wall-clock time after each start of a request reaches the HMI display until less than 0.1 s of wall-clock "
        "time after the warning request ends its asking, and at no other time, and the first frame with the warning "
        "and the start of the sound each come less than 0.1 s of wall-clock time after each start of a request "
        "reaches the HMI display. A claim to be proven: no case has started.",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes the time that the driver-assistance increment takes to its warning request, and whether "
        "a driver perceives the warning."),
    "ContentCurrency": (
        "Answers hmiContentCurrencyConcern. For HMI-CONFIG-001 in the simulated configuration, in the runs of "
        "SC-HMI-001 to SC-HMI-007 that the criteria of REQ-HMI-006 and REQ-HMI-007 name, the HMI display shows each "
        "element as outdated, in the form that phase 8 states for it, while it is outdated and as current at every "
        "other time, and shows that the collision warning is unavailable while the warning request is outdated and at "
        "no other time, each within 0.1 s of wall-clock time of the change. A claim to be proven: no case has started.",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes the visual design of an outdated element (hmiHumanFactorsOutOfScope)."),
    "AndroidOutage": (
        "Answers hmiAndroidOutageConcern. For HMI-CONFIG-001 in the simulated configuration, throughout the outage in "
        "the IVI VM of each run of SC-HMI-003 to SC-HMI-006 that the criterion of REQ-HMI-008 names, each frame on "
        "the display and each mode of the collision warning meet what the criteria of REQ-HMI-003, REQ-HMI-004, "
        "REQ-HMI-005 and REQ-HMI-007 ask of them. A claim to be proven: no case has started.",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes any safety argument."),
    "RendererAllocation": (
        "Answers hmiRendererAllocationConcern. The realization that phase 8 records, at the model revision that the "
        "record of the inspection names, draws the vehicle speed, the collision warning on the display and its sound "
        "in the high availability renderer in an SDV Media VM and the scene in an app in the IVI VM, with no other "
        "element drawing the vehicle speed or the collision warning, as the criterion of REQ-HMI-009 asks. A claim to "
        "be proven: no case has started.",
        "The claim requires the record of the inspection that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes a run, and any safety approval of an element that the renderer draws."),
    "RendererPath": (
        "Answers hmiRendererPathConcern. The realization that phase 8 records, at the model revision that the record "
        "of the inspection names, places for each input of the HMI display the elements that carry it from the SDV "
        "Core VM to the renderer or to the app, all inside the boundary of the HMI display, as the criterion of "
        "REQ-HMI-009 asks. A claim to be proven: no case has started.",
        "The claim requires the record of the inspection that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes an observation of the renderer's path on the bench (gapHmiRendererIntegration)."),
    "DisplayVerdict": (
        "Answers hmiDisplayVerdictConcern. For HMI-CONFIG-001 in the simulated configuration, the HMI display meets "
        "the success criteria of REQ-HMI-001 to REQ-HMI-008 and of REQ-HMI-010 in the runs of SC-HMI-001 to "
        "SC-HMI-007 that those criteria name, and the realization that phase 8 records meets those of REQ-HMI-009. "
        "Each verdict is a pass or a fail for its requirement and its scenarios, bound to the candidate revision, the "
        "display identity and HMI-CONFIG-001 with its receipt, and holds what the display shows against what its "
        "sources give and when, the scene of the context stand-in of phase 8 while the candidate gives no scene "
        "(gapHmiSceneOutput). A fail stays a recorded result. A claim to be proven: no case has started.",
        "The claim requires the retained records of the runs and the record of the inspection that its argument "
        "cites, bound to HMI-CONFIG-001 and its receipt; it excludes a recording of a display that looks right, the "
        "vehicle and the road that the simulation stands in for, and the results of the bench of the "
        "driver-assistance increment."),
}
#: The skeleton of the package (generated from the head by build/gen_test.py with the test's own _skeleton).
SKELETON = [
    "/*…*/",
    "package DE4SDV_HmiDisplayVerificationEvidence {",
    "  private import DE4SDV_MethodContext::*;",
    "  private import DE4SDV_HmiDisplayNeedsRequirements::*;",
    "  private import DE4SDV_HmiDisplayFraming::asmHmiDrivingBenchReuse;",
    "  private import DE4SDV_HmiDisplayFraming::asmHmiRendererWithoutGraphicsCard;",
    "  private import DE4SDV_HmiDisplayFraming::asmHmiSimulationStandsIn;",
    "  private import DE4SDV_HmiDisplayFraming::gapHmiDisplayInProductLine;",
    "  private import DE4SDV_HmiDisplayFraming::gapHmiRendererIntegration;",
    "  private import DE4SDV_HmiDisplayFraming::gapHmiSceneOutput;",
    "  private import DE4SDV_HmiDisplayFraming::gapHmiUpstreamContact;",
    "  private import DE4SDV_HmiDisplayFraming::hmiDisplayQuestion;",
    "  private import DE4SDV_HmiDisplayFraming::hmiDisplayVerdictConcern;",
    "  private import DE4SDV_HmiDisplayFraming::hmiDisplayVerificationEnvironment;",
    "  private import DE4SDV_HmiDisplayFraming::hmiOnRoadOperationOutOfScope;",
    "  private import DE4SDV_HmiDisplayFraming::hmiPerceptionQualityOutOfScope;",
    "  private import DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiBenchSpeedFeed;",
    "  private import DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiDrawingToleranceUnset;",
    "  private import VerificationCases::*;",
    "  private import VerificationMethodKind::*;",
    "  private import SAF_Viewpoints::*;",
    "  private import Views::*;",
    "  enum def HmiDisplayScenarioIdentity {",
    "    doc /*…*/",
    "    warningScenarios;",
    "    noReactionScenarios;",
    "    sceneAppOut;",
    "    androidBoots;",
    "    androidHangs;",
    "    androidRestarts;",
    "    warningRequestStops;",
    "  enum def HmiDisplayEvidenceOutcome {",
    "    doc /*…*/",
    "    passBoundedVerification;",
    "    passBoundedValidation;",
    "    failObservedBehavior;",
    "    inconclusiveMissingEvidence;",
    "    blockedTargetRuntime;",
    "    errorEvidence;",
    "  calc def MapHmiDisplayEvidenceOutcomeToVerdict {",
    "    in outcome : HmiDisplayEvidenceOutcome;",
    "    return verdict : VerdictKind = if outcome == HmiDisplayEvidenceOutcome::passBoundedVerification? "
    "VerdictKind::pass else if outcome == HmiDisplayEvidenceOutcome::passBoundedValidation? VerdictKind::pass else if "
    "outcome == HmiDisplayEvidenceOutcome::failObservedBehavior? VerdictKind::fail else if outcome == "
    "HmiDisplayEvidenceOutcome::errorEvidence? VerdictKind::error else VerdictKind::inconclusive;",
    "  item def RetainedHmiDisplayRunEvidence {",
    "    doc /*…*/",
    "    attribute configurationIdentity : ScalarValues::String;",
    "    attribute receiptSha256 : ScalarValues::String;",
    "    attribute modelRevision : ScalarValues::String;",
    "    attribute runIdentity : ScalarValues::String;",
    "    attribute scenario : HmiDisplayScenarioIdentity;",
    "    attribute displayIdentityRecord : ScalarValues::String;",
    "    attribute independentEngineerIdentity : ScalarValues::String;",
    "    attribute candidateRecordIdentity : ScalarValues::String;",
    "    attribute simulationClockSpan : ScalarValues::String;",
    "    attribute wallClockSpan : ScalarValues::String;",
    "    attribute retainedObservations : ScalarValues::String;",
    "    attribute claimBoundary : ScalarValues::String;",
    "  item def RetainedHmiDisplayRealizationInspection {",
    "    doc /*…*/",
    "    attribute configurationIdentity : ScalarValues::String;",
    "    attribute receiptSha256 : ScalarValues::String;",
    "    attribute modelRevision : ScalarValues::String;",
    "    attribute inspectedRealization : ScalarValues::String;",
    "    attribute inspectorIdentity : ScalarValues::String;",
    "    attribute claimBoundary : ScalarValues::String;",
    "  part def HmiDisplayVerificationBench {",
    "    doc /*…*/",
    "    ref part system1ConfiguredProduct :> DE4SDV_HmiDisplayVariabilityConfiguration::configuredProduct;",
    "    ref part displayRealization :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem = "
    "system1ConfiguredProduct.displayRealization;",
    "  part hmiDisplayVerificationBench : HmiDisplayVerificationBench;",
    "  part <'GAP-HMI-005'> gapHmiVerificationEnvironmentOpen : IncrementGap {",
    "    doc /*…*/",
    "  /*…*/",
    "  verification def ShowTheSceneAsGivenVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective showTheSceneAsGivenObjective {",
    "      verify reqShowTheSceneAsGiven {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def MarkTheObjectTheSystemActsOnVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective markTheObjectTheSystemActsOnObjective {",
    "      verify reqMarkTheObjectTheSystemActsOn {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def ShowTheVehicleSpeedVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective showTheVehicleSpeedObjective {",
    "      verify reqShowTheVehicleSpeed {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def CollisionWarningWhileRequestedVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective collisionWarningWhileRequestedObjective {",
    "      verify reqCollisionWarningWhileRequested {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def StartEachWarningModeWithinLimitVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective startEachWarningModeWithinLimitObjective {",
    "      verify reqStartEachWarningModeWithinLimit {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def ShowOutdatedElementsAsOutdatedVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective showOutdatedElementsAsOutdatedObjective {",
    "      verify reqShowOutdatedElementsAsOutdated {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def ShowWarningUnavailableWhileRequestOutdatedVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective showWarningUnavailableWhileRequestOutdatedObjective {",
    "      verify reqShowWarningUnavailableWhileRequestOutdated {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def SpeedAndWarningThroughOutagesVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective speedAndWarningThroughOutagesObjective {",
    "      verify reqSpeedAndWarningThroughOutages {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def RendererSplitAndInputPathsVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective rendererSplitAndInputPathsObjective {",
    "      verify reqRendererSplitAndInputPaths {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = inspect;",
    "      out item retainedEvidence : RetainedHmiDisplayRealizationInspection;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRealizationInspection = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification def RecordDisplayIdentityVerification {",
    "    doc /*…*/",
    "    subject verifiedBench : HmiDisplayVerificationBench;",
    "    objective recordDisplayIdentityObjective {",
    "      verify reqRecordDisplayIdentity {",
    "        subject hmiDisplay = verifiedBench.displayRealization;",
    "    action collectData {",
    "      @VerificationMethod {",
    "        kind = test;",
    "      out item retainedEvidence : RetainedHmiDisplayRunEvidence;",
    "    action processData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;",
    "      out evaluatedOutcome : HmiDisplayEvidenceOutcome;",
    "    action evaluateData {",
    "      @VerificationMethod {",
    "        kind = analyze;",
    "      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;",
    "      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);",
    "    return verdict : VerdictKind = evaluateData.verdict;",
    "  verification <'VC-HMI-001'> showTheSceneAsGivenVerification : ShowTheSceneAsGivenVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-002'> markTheObjectTheSystemActsOnVerification : "
    "MarkTheObjectTheSystemActsOnVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-003'> showTheVehicleSpeedVerification : ShowTheVehicleSpeedVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-004'> collisionWarningWhileRequestedVerification : "
    "CollisionWarningWhileRequestedVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-005'> startEachWarningModeWithinLimitVerification : "
    "StartEachWarningModeWithinLimitVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-006'> showOutdatedElementsAsOutdatedVerification : "
    "ShowOutdatedElementsAsOutdatedVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-007'> showWarningUnavailableWhileRequestOutdatedVerification : "
    "ShowWarningUnavailableWhileRequestOutdatedVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-008'> speedAndWarningThroughOutagesVerification : "
    "SpeedAndWarningThroughOutagesVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-009'> rendererSplitAndInputPathsVerification : RendererSplitAndInputPathsVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (inspect, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  verification <'VC-HMI-010'> recordDisplayIdentityVerification : RecordDisplayIdentityVerification {",
    "    doc /*…*/",
    "    @VerificationMethod {",
    "      kind = (test, analyze);",
    "    subject verifiedBench :> hmiDisplayVerificationBench;",
    "  part hmiDisplayVerificationSystem {",
    "    doc /*…*/",
    "    perform showTheSceneAsGivenVerification;",
    "    perform markTheObjectTheSystemActsOnVerification;",
    "    perform showTheVehicleSpeedVerification;",
    "    perform collisionWarningWhileRequestedVerification;",
    "    perform startEachWarningModeWithinLimitVerification;",
    "    perform showOutdatedElementsAsOutdatedVerification;",
    "    perform showWarningUnavailableWhileRequestOutdatedVerification;",
    "    perform speedAndWarningThroughOutagesVerification;",
    "    perform rendererSplitAndInputPathsVerification;",
    "    perform recordDisplayIdentityVerification;",
    "  dependency hmiVerificationSystemIsTheVerificationEnvironment from hmiDisplayVerificationSystem to "
    "hmiDisplayVerificationEnvironment;",
    "  dependency hmiEnvironmentGapOnVerificationSystem from gapHmiVerificationEnvironmentOpen to "
    "hmiDisplayVerificationSystem;",
    "  dependency hmiEnvironmentGapContinuesRendererIntegration from gapHmiVerificationEnvironmentOpen to "
    "gapHmiRendererIntegration;",
    "  dependency hmiEnvironmentGapContinuesRendererAssumption from gapHmiVerificationEnvironmentOpen to "
    "asmHmiRendererWithoutGraphicsCard;",
    "  dependency hmiEnvironmentGapContinuesBenchSpeedFeed from gapHmiVerificationEnvironmentOpen to "
    "gapHmiBenchSpeedFeed;",
    "  requirement def HmiDisplayClaim :> AssuranceClaim;",
    "  requirement def HmiDisplayArgument :> AssuranceArgument;",
    "  requirement def HmiDisplayCounterClaim :> AssuranceCounterClaim;",
    "  requirement hmiDisplayInputsClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiContentVarianceClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiWarningSequenceClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiContentCurrencyClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiAndroidOutageClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiRendererAllocationClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiRendererPathClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiDisplayVerdictClaim : HmiDisplayClaim {",
    "    doc /*…*/",
    "    subject claimSubject : HmiDisplayVerificationBench;",
    "    require constraint {",
    "      doc /*…*/",
    "  requirement hmiDisplayInputsArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiContentVarianceArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiWarningSequenceArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiContentCurrencyArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiAndroidOutageArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiRendererAllocationArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiRendererPathArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiDisplayVerdictArgument : HmiDisplayArgument {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimRecordingIsNoVerdict : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimSimulatedConfigurationOnly : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimDrivingBenchResultsNoEvidence : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimSceneFromAStandIn : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimPerceptionNotJudged : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimNoComplianceOrApproval : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimNoMemberProduct : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimNoUpstreamEndorsement : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimDrawingToleranceUnset : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  requirement hmiCounterClaimEnvironmentOpenNoVerdict : HmiDisplayCounterClaim {",
    "    doc /*…*/",
    "    subject bench : HmiDisplayVerificationBench;",
    "  dependency claimSupportedByHmiDisplayInputsArgument from hmiDisplayInputsArgument to hmiDisplayInputsClaim;",
    "  dependency claimSupportedByHmiContentVarianceArgument from hmiContentVarianceArgument to "
    "hmiContentVarianceClaim;",
    "  dependency claimSupportedByHmiWarningSequenceArgument from hmiWarningSequenceArgument to "
    "hmiWarningSequenceClaim;",
    "  dependency claimSupportedByHmiContentCurrencyArgument from hmiContentCurrencyArgument to "
    "hmiContentCurrencyClaim;",
    "  dependency claimSupportedByHmiAndroidOutageArgument from hmiAndroidOutageArgument to hmiAndroidOutageClaim;",
    "  dependency claimSupportedByHmiRendererAllocationArgument from hmiRendererAllocationArgument to "
    "hmiRendererAllocationClaim;",
    "  dependency claimSupportedByHmiRendererPathArgument from hmiRendererPathArgument to hmiRendererPathClaim;",
    "  dependency claimSupportedByHmiDisplayVerdictArgument from hmiDisplayVerdictArgument to hmiDisplayVerdictClaim;",
    "  dependency hmiDisplayInputsArgumentCitesCases from hmiDisplayInputsArgument to showTheSceneAsGivenVerification;",
    "  dependency hmiContentVarianceArgumentCitesCases from hmiContentVarianceArgument to "
    "showTheSceneAsGivenVerification;",
    "  dependency hmiWarningSequenceArgumentCitesCases from hmiWarningSequenceArgument to "
    "collisionWarningWhileRequestedVerification, startEachWarningModeWithinLimitVerification;",
    "  dependency hmiContentCurrencyArgumentCitesCases from hmiContentCurrencyArgument to "
    "showOutdatedElementsAsOutdatedVerification, showWarningUnavailableWhileRequestOutdatedVerification;",
    "  dependency hmiAndroidOutageArgumentCitesCases from hmiAndroidOutageArgument to "
    "speedAndWarningThroughOutagesVerification;",
    "  dependency hmiRendererAllocationArgumentCitesCases from hmiRendererAllocationArgument to "
    "rendererSplitAndInputPathsVerification;",
    "  dependency hmiRendererPathArgumentCitesCases from hmiRendererPathArgument to "
    "rendererSplitAndInputPathsVerification;",
    "  dependency hmiDisplayVerdictArgumentCitesCases from hmiDisplayVerdictArgument to "
    "showTheSceneAsGivenVerification, markTheObjectTheSystemActsOnVerification, showTheVehicleSpeedVerification, "
    "collisionWarningWhileRequestedVerification, startEachWarningModeWithinLimitVerification, "
    "showOutdatedElementsAsOutdatedVerification, showWarningUnavailableWhileRequestOutdatedVerification, "
    "speedAndWarningThroughOutagesVerification, rendererSplitAndInputPathsVerification, "
    "recordDisplayIdentityVerification;",
    "  dependency hmiCounterClaimRecordingIsNoVerdictBoundTo from hmiCounterClaimRecordingIsNoVerdict to "
    "hmiDisplayQuestion;",
    "  dependency hmiCounterClaimSimulatedConfigurationOnlyBoundTo from hmiCounterClaimSimulatedConfigurationOnly to "
    "asmHmiSimulationStandsIn;",
    "  dependency hmiCounterClaimDrivingBenchResultsNoEvidenceBoundTo from "
    "hmiCounterClaimDrivingBenchResultsNoEvidence to asmHmiDrivingBenchReuse;",
    "  dependency hmiCounterClaimSceneFromAStandInBoundTo from hmiCounterClaimSceneFromAStandIn to gapHmiSceneOutput;",
    "  dependency hmiCounterClaimPerceptionNotJudgedBoundTo from hmiCounterClaimPerceptionNotJudged to "
    "hmiPerceptionQualityOutOfScope;",
    "  dependency hmiCounterClaimNoComplianceOrApprovalBoundTo from hmiCounterClaimNoComplianceOrApproval to "
    "hmiOnRoadOperationOutOfScope;",
    "  dependency hmiCounterClaimNoMemberProductBoundTo from hmiCounterClaimNoMemberProduct to "
    "gapHmiDisplayInProductLine;",
    "  dependency hmiCounterClaimNoUpstreamEndorsementBoundTo from hmiCounterClaimNoUpstreamEndorsement to "
    "gapHmiUpstreamContact;",
    "  dependency hmiCounterClaimDrawingToleranceUnsetBoundTo from hmiCounterClaimDrawingToleranceUnset to "
    "gapHmiDrawingToleranceUnset;",
    "  dependency hmiCounterClaimEnvironmentOpenNoVerdictBoundTo from hmiCounterClaimEnvironmentOpenNoVerdict to "
    "gapHmiVerificationEnvironmentOpen;",
    "  view hmiDisplayAssuranceView {",
    "    viewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint {",
    "      frame hmiDisplayVerdictConcern;",
    "    doc /*…*/",
    "    expose hmiDisplayInputsClaim;",
    "    expose hmiContentVarianceClaim;",
    "    expose hmiWarningSequenceClaim;",
    "    expose hmiContentCurrencyClaim;",
    "    expose hmiAndroidOutageClaim;",
    "    expose hmiRendererAllocationClaim;",
    "    expose hmiRendererPathClaim;",
    "    expose hmiDisplayVerdictClaim;",
    "    expose hmiDisplayInputsArgument;",
    "    expose hmiContentVarianceArgument;",
    "    expose hmiWarningSequenceArgument;",
    "    expose hmiContentCurrencyArgument;",
    "    expose hmiAndroidOutageArgument;",
    "    expose hmiRendererAllocationArgument;",
    "    expose hmiRendererPathArgument;",
    "    expose hmiDisplayVerdictArgument;",
    "    expose hmiCounterClaimRecordingIsNoVerdict;",
    "    expose hmiCounterClaimSimulatedConfigurationOnly;",
    "    expose hmiCounterClaimDrivingBenchResultsNoEvidence;",
    "    expose hmiCounterClaimSceneFromAStandIn;",
    "    expose hmiCounterClaimPerceptionNotJudged;",
    "    expose hmiCounterClaimNoComplianceOrApproval;",
    "    expose hmiCounterClaimNoMemberProduct;",
    "    expose hmiCounterClaimNoUpstreamEndorsement;",
    "    expose hmiCounterClaimDrawingToleranceUnset;",
    "    expose hmiCounterClaimEnvironmentOpenNoVerdict;",
    "    expose showTheSceneAsGivenVerification;",
    "    expose markTheObjectTheSystemActsOnVerification;",
    "    expose showTheVehicleSpeedVerification;",
    "    expose collisionWarningWhileRequestedVerification;",
    "    expose startEachWarningModeWithinLimitVerification;",
    "    expose showOutdatedElementsAsOutdatedVerification;",
    "    expose showWarningUnavailableWhileRequestOutdatedVerification;",
    "    expose speedAndWarningThroughOutagesVerification;",
    "    expose rendererSplitAndInputPathsVerification;",
    "    expose recordDisplayIdentityVerification;",
    "    expose RetainedHmiDisplayRunEvidence;",
    "    expose RetainedHmiDisplayRealizationInspection;",
    "    expose HmiDisplayVerificationBench;",
    "    expose gapHmiVerificationEnvironmentOpen;",
    "    expose hmiDisplayQuestion;",
    "    expose asmHmiSimulationStandsIn;",
    "    expose asmHmiDrivingBenchReuse;",
    "    expose gapHmiSceneOutput;",
    "    expose hmiPerceptionQualityOutOfScope;",
    "    expose hmiOnRoadOperationOutOfScope;",
    "    expose gapHmiDisplayInProductLine;",
    "    expose gapHmiUpstreamContact;",
    "    expose gapHmiDrawingToleranceUnset;",
    "    expose claimSupportedByHmiDisplayInputsArgument;",
    "    expose claimSupportedByHmiContentVarianceArgument;",
    "    expose claimSupportedByHmiWarningSequenceArgument;",
    "    expose claimSupportedByHmiContentCurrencyArgument;",
    "    expose claimSupportedByHmiAndroidOutageArgument;",
    "    expose claimSupportedByHmiRendererAllocationArgument;",
    "    expose claimSupportedByHmiRendererPathArgument;",
    "    expose claimSupportedByHmiDisplayVerdictArgument;",
    "    expose hmiDisplayInputsArgumentCitesCases;",
    "    expose hmiContentVarianceArgumentCitesCases;",
    "    expose hmiWarningSequenceArgumentCitesCases;",
    "    expose hmiContentCurrencyArgumentCitesCases;",
    "    expose hmiAndroidOutageArgumentCitesCases;",
    "    expose hmiRendererAllocationArgumentCitesCases;",
    "    expose hmiRendererPathArgumentCitesCases;",
    "    expose hmiDisplayVerdictArgumentCitesCases;",
    "    expose hmiCounterClaimRecordingIsNoVerdictBoundTo;",
    "    expose hmiCounterClaimSimulatedConfigurationOnlyBoundTo;",
    "    expose hmiCounterClaimDrivingBenchResultsNoEvidenceBoundTo;",
    "    expose hmiCounterClaimSceneFromAStandInBoundTo;",
    "    expose hmiCounterClaimPerceptionNotJudgedBoundTo;",
    "    expose hmiCounterClaimNoComplianceOrApprovalBoundTo;",
    "    expose hmiCounterClaimNoMemberProductBoundTo;",
    "    expose hmiCounterClaimNoUpstreamEndorsementBoundTo;",
    "    expose hmiCounterClaimDrawingToleranceUnsetBoundTo;",
    "    expose hmiCounterClaimEnvironmentOpenNoVerdictBoundTo;",
    "    attribute maxCompartmentEntries = 0;",
    "    attribute showAnnotationRows = false;",
    "    render asTreeDiagram;",
]
#: Every comment of the package, in order: (its owner, its text whitespace collapsed), generated from the head
#: with the test's own _doc_texts.
DOC_TEXTS = [
    (
        "header",
        "DE4SDV HMI display verification and evidence model slice. INC-HMI-001, phase 10, first slice: the "
        "verification cases. Each case verifies one requirement of DE4SDV_HmiDisplayNeedsRequirements, checks the "
        "success criteria that the requirement states and adds no criterion of its own, and binds the subject of its "
        "requirement to the realization of the HMI display in the configured product HMI-CONFIG-001 (phase 9). One "
        "case per requirement, ten cases, VC-HMI-001 to VC-HMI-010. Nine are tests that read runs of the scenarios "
        "among SC-HMI-001 to SC-HMI-007 that their criteria name; VC-HMI-009 is the inspection of the realization "
        "that phase 8 records, which REQ-HMI-009 asks for, and reads no run. The five choices of this slice are the "
        "owner decision of 2026-11-26, as INC-DRIVING-002 took them: one case per requirement; an outcome vocabulary "
        "and a verdict map of the increment's own, with the six literals of INC-DRIVING-002; the claims, their "
        "arguments and the counter-claims now, the counter-claims from the non-claims of the framing; one evidence "
        "record per run, read by every case of that run; and the test environment as a gap that continues the gaps "
        "of phase 8 until the readiness probes fix its host and its topology. No case has started. No evidence "
        "record exists, and each requirement keeps the verification status NotStarted. The doc of each case usage "
        "states the scenarios that the case reads. The System 2 test environment is the framing's "
        "hmiDisplayVerificationEnvironment; the readiness questions that phase 8 leaves open continue as GAP-HMI-005 "
        "until the probes fix its host and its topology. The validation of the needs stays planned in phase 4 "
        "(SC-HMI-008 to SC-HMI-013). This slice adds no validation case. Where the requirements leave a reading to "
        "the cases, the cases read them so. A run that is missing, or whose record is partial, gives "
        "inconclusiveMissingEvidence, never pass. While the tolerance of a drawn position is not set (GAP-HMI-003), "
        "VC-HMI-001 gives inconclusiveMissingEvidence for evidence that meets every other clause of its criterion. "
        "The display with one changed build, image, sound file, configuration file or start setting that the "
        "criterion of REQ-HMI-010 names records its display identity outside a run, so that no criterion over each "
        "run reads it. The scene that the cases read is the one that the context stand-in of phase 8 publishes, "
        "since the candidate gives no scene at its boundary (gapHmiSceneOutput). The outcome vocabulary and the "
        "verdict map are this increment's own, with the six literals that INC-DRIVING-002 uses. The evidence record "
        "is one record per run, read by every case of that run: it binds HMI-CONFIG-001 and the receipt digest, the "
        "model revision, the run and its scenario, the display identity record of REQ-HMI-010 and the engineer who "
        "hashes the named files again, the candidate identity record of the driver-assistance increment, the two "
        "clock spans, and the observations that phase 5 asks of System 2. The inspection of REQ-HMI-009 keeps a "
        "record of its own. The claims of the increment are stated now, one for each phase 1 concern whose question "
        "the cases answer, eight in all, each with an argument that cites the planned cases that answer it. The "
        "counter-claims restate the non-claims of the framing and of the open gaps, each tied to the record that "
        "keeps it open. A claim stated before its evidence is a claim to be proven, not a result. This slice makes "
        "no result, evidence, acceptance, safety, compliance or certification claim."),
    (
        "enum def HmiDisplayScenarioIdentity",
        "The scenario of a run, by its phase 2 identity, as the evidence record names it. warningScenarios is "
        "SC-HMI-001, the warning scenarios of the driver-assistance increment on the display; noReactionScenarios is "
        "SC-HMI-002, its no-reaction scenarios on the display; sceneAppOut is SC-HMI-003, the app that draws the "
        "scene is out; androidBoots is SC-HMI-004, Android in the IVI VM boots; androidHangs is SC-HMI-005, Android "
        "in the IVI VM hangs; androidRestarts is SC-HMI-006, Android in the IVI VM restarts; warningRequestStops is "
        "SC-HMI-007, the warning request stops reaching the display."),
    (
        "enum def HmiDisplayEvidenceOutcome",
        "The outcome of processing the evidence of a case against the success criteria of its requirement. The six "
        "literals that INC-DRIVING-002 uses: evidence that meets the criteria gives passBoundedVerification; "
        "evidence that shows them not met gives failObservedBehavior; missing or partial evidence gives "
        "inconclusiveMissingEvidence; a run that the test environment could not perform gives blockedTargetRuntime; "
        "evidence that cannot be read gives errorEvidence. passBoundedValidation is the outcome of a validation, "
        "which no case of this slice performs."),
    (
        "item def RetainedHmiDisplayRunEvidence",
        "The evidence record of one run; every case that reads the run reads this record. It binds HMI-CONFIG-001 as "
        "its configurationIdentity. receiptSha256 is the SHA-256 of the receipt the run ran against, as "
        "HMI-CONFIG-001 asks of the evidence that binds it; if it differs from the receiptSha256 of HMI-CONFIG-001, "
        "the verdict holds for HMI-CONFIG-001 only if the configuration's own receipt record did not change, which "
        "the pull request that rebinds the digest states. modelRevision is the Git commit of the DE4SDV model the "
        "run evaluated. runIdentity names the run, one execution of the HMI display on one scenario from its start "
        "to its end, and scenario names that scenario. displayIdentityRecord names the record of the display "
        "identity that the identity recording service makes before the first frame on the display (REQ-HMI-010), and "
        "independentEngineerIdentity names the engineer who hashes the named files again. candidateRecordIdentity "
        "names the candidate identity record that the driver-assistance system records in the run (REQ-DRIVING-044). "
        "simulationClockSpan and wallClockSpan are the two clocks of the run, kept apart. retainedObservations names "
        "the records that phase 5 asks of System 2 (hmiTestbedObligationsOfPhase5): each value of each input as its "
        "source gives it, with its simulation time, and where it reaches the HMI display, with the wall-clock time "
        "of its arrival; each frame on the display and the start of each sound, with their wall-clock times; and the "
        "files and the settings that the display identity names. It also names the times of the outage in the IVI VM "
        "and of the stop of the Eclipse S-CORE path that the fault injection of the run makes, which the criteria of "
        "REQ-HMI-001 and REQ-HMI-006 to REQ-HMI-008 read. claimBoundary states what the record proves and what it "
        "does not. A missing or partial record gives inconclusive, never pass. No record exists."),
    (
        "item def RetainedHmiDisplayRealizationInspection",
        "The evidence record of the inspection of REQ-HMI-009, which reads the realization and no run. It binds "
        "HMI-CONFIG-001 and its receipt as the run record does. modelRevision is the Git commit of the DE4SDV model "
        "whose phase 8 realization the inspection read. inspectedRealization names what it read: "
        "HmiDisplayPhysicalSystem with its parts and its connections, the allocations of phase 8, and the comment "
        "phase8WarningPresentationSettled, by which the IVI VM runs no other warning presentation in the display's "
        "runs. inspectorIdentity names who made the inspection. claimBoundary states what the inspection proves and "
        "what it does not. A missing or partial record gives inconclusive, never pass. No record exists."),
    (
        "part def HmiDisplayVerificationBench",
        "The bench of the verification cases of INC-HMI-001. System 1 is the configured product HMI-CONFIG-001, "
        "which the bench refers to and does not own. displayRealization is its realization of the HMI display, the "
        "system of interest: the subject that each verified requirement binds. The System 2 test environment is the "
        "framing's hmiDisplayVerificationEnvironment, whose readiness stays open as GAP-HMI-005. The bench is not a "
        "product selection."),
    (
        "part <'GAP-HMI-005'> gapHmiVerificationEnvironmentOpen : IncrementGap",
        "Open: the System 2 test environment is not shown to run the cases. It continues the readiness questions "
        "that phase 8 leaves open until the probes fix its host and its topology: whether the high availability "
        "renderer draws on the guest host with the SDV Core, IVI and SDV Media VMs running on it together, with the "
        "heartbeats, the composition and the renderer's judging of the scene by the term current "
        "(asmHmiRendererWithoutGraphicsCard); which transport carries the renderer's topics between the VMs, whether "
        "the bench composes the two planes, which IVI image runs the app, and how the sound is captured "
        "(gapHmiRendererIntegration); which element of the bench feeds the simulator's speed into the vehicle data "
        "of the SDV Core VM (GAP-HMI-002); and what stands in for the source of the scene, and how, which is decided "
        "with the scene's way out of the candidate (gapHmiSceneOutput). The records, the faults and the lengths of "
        "the runs that the criteria ask of System 2 are those that phase 5 states (hmiTestbedObligationsOfPhase5). "
        "Each probe runs only on the owner's word, and nothing of the next slice is built before the probes are "
        "read. The next slice fills the evidence record, plans the runs and closes this gap."),
    (
        "comment in package",
        "Each case collects the evidence record of its runs, or of its inspection (collectData). processData "
        "compares the record with the success criteria of the verified requirement and gives a "
        "HmiDisplayEvidenceOutcome. evaluateData maps the outcome to a VerdictKind with "
        "MapHmiDisplayEvidenceOutcomeToVerdict. Each objective binds the subject of its requirement to the "
        "realization of the HMI display in HMI-CONFIG-001. A verify is a planned verification objective, not a "
        "verdict."),
    (
        "verification def ShowTheSceneAsGivenVerification",
        "Test of REQ-HMI-001. collectData retains the record of each run of SC-HMI-001 to SC-HMI-007: each scene "
        "with its time as its source gives it and the wall-clock time at which it reaches the HMI display, the "
        "outages in the IVI VM, and each frame on the display with its wall-clock time. processData checks that each "
        "of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-004 and SC-HMI-006 has the end of its "
        "outage in the IVI VM before its own end, and in each run every scene that reaches the HMI display outside "
        "an outage in the IVI VM, or a newer scene, is on the display less than 0.1 s of wall-clock time after it "
        "arrives, with its lane points, its path and each of its objects with its level, as many objects as the "
        "scene gives and at the positions that it gives, read within the drawing tolerance that phase 8 states; and "
        "that no frame on the display shows a lane, a path or an object that no scene of the run gives, from the "
        "simulator's record of the scene or from an estimate of the display's own. Every clause met gives "
        "passBoundedVerification; a clause not met gives failObservedBehavior. A run that is missing, or whose "
        "record is partial, gives inconclusiveMissingEvidence, never pass. While the tolerance of a drawn position "
        "is not set (GAP-HMI-003), evidence that meets every other clause gives inconclusiveMissingEvidence, never "
        "pass."),
    (
        "verification def MarkTheObjectTheSystemActsOnVerification",
        "Test of REQ-HMI-002. collectData retains the record of each run of SC-HMI-001 to SC-HMI-007: each scene "
        "with the object that the system acts on, its distance and the speed of the closest object, as its source "
        "gives them, and each frame on the display with its wall-clock time. processData checks that each of "
        "SC-HMI-001 and SC-HMI-002 has at least one run whose scenes give an object that the system acts on, and in "
        "each run of SC-HMI-001 to SC-HMI-007 each frame on the display that shows a scene shows, as an element of "
        "its own, the object that the system acts on of that scene when it has one and no such element when it has "
        "none, the fixed distance of 150 m included; marks none of the marks that the criterion of REQ-HMI-002 "
        "excludes as that object; and shows its distance as the distance of the scene rounded to the whole metre and "
        "its speed as the speed of the closest object of the scene times 3.6, rounded to the whole km/h, with its "
        "sign. Every clause met gives passBoundedVerification; a clause not met gives failObservedBehavior. A run "
        "that is missing, or whose record is partial, gives inconclusiveMissingEvidence, never pass."),
    (
        "verification def ShowTheVehicleSpeedVerification",
        "Test of REQ-HMI-003. collectData retains the record of each run of SC-HMI-001, SC-HMI-002 and SC-HMI-007: "
        "each vehicle speed with its sample time as its source gives it and the wall-clock time at which it reaches "
        "the HMI display, and each frame on the display with its wall-clock time. processData checks that each of "
        "SC-HMI-001, SC-HMI-002 and SC-HMI-007 has at least one run, and in each of their runs each speed on a frame "
        "on the display is the value of a vehicle speed of the run that has reached the HMI display, rounded to the "
        "whole km/h; each vehicle speed that reaches the HMI display, or a newer one, is on the display less than "
        "0.1 s of wall-clock time after it arrives; and no frame shows a speed from another source, a fixed value of "
        "the display's own, or a speed before the first vehicle speed of the run reaches the HMI display. Every "
        "clause met gives passBoundedVerification; a clause not met gives failObservedBehavior. A run that is "
        "missing, or whose record is partial, gives inconclusiveMissingEvidence, never pass."),
    (
        "verification def CollisionWarningWhileRequestedVerification",
        "Test of REQ-HMI-004. collectData retains the record of each run of SC-HMI-001, SC-HMI-002 and SC-HMI-007: "
        "each event of the warning request with its issue time as its source gives it and the wall-clock time at "
        "which it reaches the HMI display, each frame on the display and the start and the end of each sound, with "
        "their wall-clock times. processData checks that each run of SC-HMI-001 has at least one start of a request "
        "that reaches the HMI display, and in each run of SC-HMI-001, SC-HMI-002 and SC-HMI-007 each mode of the "
        "collision warning is on from less than 0.1 s of wall-clock time after each start of a request reaches the "
        "HMI display until less than 0.1 s of wall-clock time after the warning request ends its asking, and at no "
        "other time, with no recording or overlay in place of either mode. Every clause met gives "
        "passBoundedVerification; a clause not met gives failObservedBehavior. A run that is missing, or whose "
        "record is partial, gives inconclusiveMissingEvidence, never pass."),
    (
        "verification def StartEachWarningModeWithinLimitVerification",
        "Test of REQ-HMI-005. collectData retains the record of each run of SC-HMI-001 and SC-HMI-002: each event of "
        "the warning request with its issue time as its source gives it and the wall-clock time at which it reaches "
        "the HMI display, each frame on the display and the start of each sound, with their wall-clock times. "
        "processData checks that each run of SC-HMI-001 has at least one start of a request that reaches the HMI "
        "display, and for each start of a request that reaches the HMI display in a run of SC-HMI-001 or SC-HMI-002, "
        "the first frame on the display with the warning and the start of the sound each come less than 0.1 s of "
        "wall-clock time after it arrives, with no recording or overlay in place of either mode. Every clause met "
        "gives passBoundedVerification; a clause not met gives failObservedBehavior. A run that is missing, or whose "
        "record is partial, gives inconclusiveMissingEvidence, never pass."),
    (
        "verification def ShowOutdatedElementsAsOutdatedVerification",
        "Test of REQ-HMI-006. collectData retains the record of each run of SC-HMI-001 to SC-HMI-007: each value of "
        "each input with its time as its source gives it and the wall-clock time at which it reaches the HMI "
        "display, the outages in the IVI VM and the stop of the Eclipse S-CORE path, and each frame on the display "
        "with its wall-clock time. processData checks that each of SC-HMI-001 to SC-HMI-007 has at least one run, "
        "each run of SC-HMI-003 to SC-HMI-006 has its outage in the IVI VM and each run of SC-HMI-007 the stop of "
        "the Eclipse S-CORE path, and in each run each frame on the display shows each element as outdated, in the "
        "form that phase 8 states for it, from less than 0.1 s of wall-clock time after the element turns outdated "
        "until less than 0.1 s of wall-clock time after it turns current again, and as current at every other time; "
        "an element is outdated from the start of the run until a first current value of its input reaches the HMI "
        "display. Every clause met gives passBoundedVerification; a clause not met gives failObservedBehavior. A run "
        "that is missing, or whose record is partial, gives inconclusiveMissingEvidence, never pass."),
    (
        "verification def ShowWarningUnavailableWhileRequestOutdatedVerification",
        "Test of REQ-HMI-007. collectData retains the record of each run of SC-HMI-001 to SC-HMI-007: each event of "
        "the warning request with its issue time as its source gives it and the wall-clock time at which it reaches "
        "the HMI display, the stop of the Eclipse S-CORE path, the end of the run, and each frame on the display "
        "with its wall-clock time. processData checks that each of SC-HMI-001 to SC-HMI-007 has at least one run, "
        "each run of SC-HMI-007 has the stop of the Eclipse S-CORE path at least 0.3 s of wall-clock time before its "
        "end, and in each run the display shows that the collision warning is unavailable from less than 0.1 s of "
        "wall-clock time after the warning request turns outdated until less than 0.1 s of wall-clock time after it "
        "turns current again, and at no other time, so that the warning shows as available again only once an event "
        "of the warning request is current. Every clause met gives passBoundedVerification; a clause not met gives "
        "failObservedBehavior. A run that is missing, or whose record is partial, gives inconclusiveMissingEvidence, "
        "never pass."),
    (
        "verification def SpeedAndWarningThroughOutagesVerification",
        "Test of REQ-HMI-008. collectData retains the record of each run of SC-HMI-003 to SC-HMI-006: each vehicle "
        "speed and each event of the warning request with its time as its source gives it and the wall-clock time at "
        "which it reaches the HMI display, the outage in the IVI VM, each frame on the display and the start and the "
        "end of each sound, with their wall-clock times. processData checks that each of SC-HMI-003 to SC-HMI-006 "
        "has at least one run, each run has its outage in the IVI VM with at least one start of a request reaching "
        "the HMI display during it, and throughout the outage of each run each frame on the display and each mode of "
        "the collision warning meet what the criteria of REQ-HMI-003, REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 ask "
        "of them. Every clause met gives passBoundedVerification; a clause not met gives failObservedBehavior. A run "
        "that is missing, or whose record is partial, gives inconclusiveMissingEvidence, never pass."),
    (
        "verification def RendererSplitAndInputPathsVerification",
        "Inspection of REQ-HMI-009. collectData retains the RetainedHmiDisplayRealizationInspection record: the "
        "realization that phase 8 records, at the model revision that the record names. processData checks that the "
        "inspection of the realization that phase 8 records shows the vehicle speed, the collision warning on the "
        "display and its sound in the high availability renderer in an SDV Media VM, the scene in an app in the IVI "
        "VM, and for each input the elements that carry it from the SDV Core VM to the renderer or to the app, all "
        "inside the boundary of the HMI display, with no other element drawing the vehicle speed or the collision "
        "warning. An inspection that finds each of these gives passBoundedVerification; one that finds an element or "
        "a path missing, outside the boundary of the HMI display, or another element drawing the vehicle speed or "
        "the collision warning gives failObservedBehavior. A record that is missing or partial gives "
        "inconclusiveMissingEvidence, never pass. The case reads no run."),
    (
        "verification def RecordDisplayIdentityVerification",
        "Test of REQ-HMI-010. collectData retains the record of each run of SC-HMI-001 to SC-HMI-007: the record of "
        "the display identity with its wall-clock time, the wall-clock time of the first frame on the display, and "
        "the values that another engineer obtains who hashes the named files; and, outside the runs, the display "
        "identity that the identity recording service records for a display with one changed build, image, sound "
        "file, configuration file or start setting. processData checks that every run of SC-HMI-001 to SC-HMI-007 "
        "has the record of its display identity before its first frame on the display; that another engineer who "
        "hashes the named files obtains the recorded values; and that a display with one changed build, image, sound "
        "file, configuration file or start setting records a different display identity. Every clause met gives "
        "passBoundedVerification; a clause not met gives failObservedBehavior. A run that is missing, or whose "
        "record is partial, gives inconclusiveMissingEvidence, never pass. The display identity is the one that the "
        "term of the requirements names since the identity-term amendment of phase 10."),
    (
        "verification <'VC-HMI-001'> showTheSceneAsGivenVerification : ShowTheSceneAsGivenVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003 (HmiDisplayScenarioIdentity::sceneAppOut), "
        "SC-HMI-004 (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005 "
        "(HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006 (HmiDisplayScenarioIdentity::androidRestarts) and "
        "SC-HMI-007 (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of these scenarios that the "
        "criterion of its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-002'> markTheObjectTheSystemActsOnVerification : "
        "MarkTheObjectTheSystemActsOnVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003 (HmiDisplayScenarioIdentity::sceneAppOut), "
        "SC-HMI-004 (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005 "
        "(HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006 (HmiDisplayScenarioIdentity::androidRestarts) and "
        "SC-HMI-007 (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of these scenarios that the "
        "criterion of its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-003'> showTheVehicleSpeedVerification : ShowTheVehicleSpeedVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios) and SC-HMI-007 "
        "(HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of these scenarios that the criterion of "
        "its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-004'> collisionWarningWhileRequestedVerification : "
        "CollisionWarningWhileRequestedVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios) and SC-HMI-007 "
        "(HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of these scenarios that the criterion of "
        "its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-005'> startEachWarningModeWithinLimitVerification : "
        "StartEachWarningModeWithinLimitVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios) and SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios). Runs: the runs of these scenarios that the criterion of "
        "its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-006'> showOutdatedElementsAsOutdatedVerification : "
        "ShowOutdatedElementsAsOutdatedVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003 (HmiDisplayScenarioIdentity::sceneAppOut), "
        "SC-HMI-004 (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005 "
        "(HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006 (HmiDisplayScenarioIdentity::androidRestarts) and "
        "SC-HMI-007 (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of these scenarios that the "
        "criterion of its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-007'> showWarningUnavailableWhileRequestOutdatedVerification : "
        "ShowWarningUnavailableWhileRequestOutdatedVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003 (HmiDisplayScenarioIdentity::sceneAppOut), "
        "SC-HMI-004 (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005 "
        "(HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006 (HmiDisplayScenarioIdentity::androidRestarts) and "
        "SC-HMI-007 (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of these scenarios that the "
        "criterion of its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-008'> speedAndWarningThroughOutagesVerification : "
        "SpeedAndWarningThroughOutagesVerification",
        "Not started. Scenarios: SC-HMI-003 (HmiDisplayScenarioIdentity::sceneAppOut), SC-HMI-004 "
        "(HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005 (HmiDisplayScenarioIdentity::androidHangs) and "
        "SC-HMI-006 (HmiDisplayScenarioIdentity::androidRestarts). Runs: the runs of these scenarios that the "
        "criterion of its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "verification <'VC-HMI-009'> rendererSplitAndInputPathsVerification : RendererSplitAndInputPathsVerification",
        "Not started. Scenarios: none; the case reads the realization that phase 8 records, at the model revision "
        "that its record names, and no run."),
    (
        "verification <'VC-HMI-010'> recordDisplayIdentityVerification : RecordDisplayIdentityVerification",
        "Not started. Scenarios: SC-HMI-001 (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002 "
        "(HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003 (HmiDisplayScenarioIdentity::sceneAppOut), "
        "SC-HMI-004 (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005 "
        "(HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006 (HmiDisplayScenarioIdentity::androidRestarts) and "
        "SC-HMI-007 (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of these scenarios that the "
        "criterion of its requirement names; the next slice plans them. Test environment: open (GAP-HMI-005)."),
    (
        "part hmiDisplayVerificationSystem",
        "The verification system performs the cases: the System 2 performer, the framing's "
        "hmiDisplayVerificationEnvironment, whose readiness GAP-HMI-005 leaves open."),
    (
        "requirement hmiDisplayInputsClaim : HmiDisplayClaim",
        "Answers hmiDisplayInputsConcern. For HMI-CONFIG-001 in the simulated configuration, in the runs of "
        "SC-HMI-001 to SC-HMI-007 that the criterion of REQ-HMI-001 names, the HMI display shows each scene that "
        "reaches it outside an outage in the IVI VM, or a newer scene, as its source gives it, with its lane points, "
        "its path and each of its objects with its level, and no lane, path or object that no scene of the run "
        "gives. A claim to be proven: no case has started."),
    (
        "requirement hmiDisplayInputsClaim : HmiDisplayClaim / require constraint",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and "
        "its receipt; it excludes the simulator's own record of the scene and an estimate of the display's own as a "
        "source of the scene, and how well the candidate perceives."),
    (
        "requirement hmiContentVarianceClaim : HmiDisplayClaim",
        "Answers hmiContentVarianceConcern. For HMI-CONFIG-001, the scene that the HMI display shows in the runs "
        "that the criterion of REQ-HMI-001 names is the scene of the one source of the scene in that configuration, "
        "as that source gives it, and no scene of another driving application; while the candidate gives no scene, "
        "that source is the context stand-in of phase 8 (gapHmiSceneOutput). A claim to be proven: no case has "
        "started."),
    (
        "requirement hmiContentVarianceClaim : HmiDisplayClaim / require constraint",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and "
        "its receipt; it excludes the scenes of the other driving applications of the product line, and which "
        "content becomes common to the member products, which is for the lifecycle decision."),
    (
        "requirement hmiWarningSequenceClaim : HmiDisplayClaim",
        "Answers hmiWarningSequenceConcern. For HMI-CONFIG-001 in the simulated configuration, in the runs that the "
        "criteria of REQ-HMI-004 and REQ-HMI-005 name, each mode of the collision warning is on from less than 0.1 s "
        "of wall-clock time after each start of a request reaches the HMI display until less than 0.1 s of "
        "wall-clock time after the warning request ends its asking, and at no other time, and the first frame with "
        "the warning and the start of the sound each come less than 0.1 s of wall-clock time after each start of a "
        "request reaches the HMI display. A claim to be proven: no case has started."),
    (
        "requirement hmiWarningSequenceClaim : HmiDisplayClaim / require constraint",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and "
        "its receipt; it excludes the time that the driver-assistance increment takes to its warning request, and "
        "whether a driver perceives the warning."),
    (
        "requirement hmiContentCurrencyClaim : HmiDisplayClaim",
        "Answers hmiContentCurrencyConcern. For HMI-CONFIG-001 in the simulated configuration, in the runs of "
        "SC-HMI-001 to SC-HMI-007 that the criteria of REQ-HMI-006 and REQ-HMI-007 name, the HMI display shows each "
        "element as outdated, in the form that phase 8 states for it, while it is outdated and as current at every "
        "other time, and shows that the collision warning is unavailable while the warning request is outdated and "
        "at no other time, each within 0.1 s of wall-clock time of the change. A claim to be proven: no case has "
        "started."),
    (
        "requirement hmiContentCurrencyClaim : HmiDisplayClaim / require constraint",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and "
        "its receipt; it excludes the visual design of an outdated element (hmiHumanFactorsOutOfScope)."),
    (
        "requirement hmiAndroidOutageClaim : HmiDisplayClaim",
        "Answers hmiAndroidOutageConcern. For HMI-CONFIG-001 in the simulated configuration, throughout the outage "
        "in the IVI VM of each run of SC-HMI-003 to SC-HMI-006 that the criterion of REQ-HMI-008 names, each frame "
        "on the display and each mode of the collision warning meet what the criteria of REQ-HMI-003, REQ-HMI-004, "
        "REQ-HMI-005 and REQ-HMI-007 ask of them. A claim to be proven: no case has started."),
    (
        "requirement hmiAndroidOutageClaim : HmiDisplayClaim / require constraint",
        "The claim requires the retained records of the runs that its argument cites, bound to HMI-CONFIG-001 and "
        "its receipt; it excludes any safety argument."),
    (
        "requirement hmiRendererAllocationClaim : HmiDisplayClaim",
        "Answers hmiRendererAllocationConcern. The realization that phase 8 records, at the model revision that the "
        "record of the inspection names, draws the vehicle speed, the collision warning on the display and its sound "
        "in the high availability renderer in an SDV Media VM and the scene in an app in the IVI VM, with no other "
        "element drawing the vehicle speed or the collision warning, as the criterion of REQ-HMI-009 asks. A claim "
        "to be proven: no case has started."),
    (
        "requirement hmiRendererAllocationClaim : HmiDisplayClaim / require constraint",
        "The claim requires the record of the inspection that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes a run, and any safety approval of an element that the renderer draws."),
    (
        "requirement hmiRendererPathClaim : HmiDisplayClaim",
        "Answers hmiRendererPathConcern. The realization that phase 8 records, at the model revision that the record "
        "of the inspection names, places for each input of the HMI display the elements that carry it from the SDV "
        "Core VM to the renderer or to the app, all inside the boundary of the HMI display, as the criterion of "
        "REQ-HMI-009 asks. A claim to be proven: no case has started."),
    (
        "requirement hmiRendererPathClaim : HmiDisplayClaim / require constraint",
        "The claim requires the record of the inspection that its argument cites, bound to HMI-CONFIG-001 and its "
        "receipt; it excludes an observation of the renderer's path on the bench (gapHmiRendererIntegration)."),
    (
        "requirement hmiDisplayVerdictClaim : HmiDisplayClaim",
        "Answers hmiDisplayVerdictConcern. For HMI-CONFIG-001 in the simulated configuration, the HMI display meets "
        "the success criteria of REQ-HMI-001 to REQ-HMI-008 and of REQ-HMI-010 in the runs of SC-HMI-001 to "
        "SC-HMI-007 that those criteria name, and the realization that phase 8 records meets those of REQ-HMI-009. "
        "Each verdict is a pass or a fail for its requirement and its scenarios, bound to the candidate revision, "
        "the display identity and HMI-CONFIG-001 with its receipt, and holds what the display shows against what its "
        "sources give and when, the scene of the context stand-in of phase 8 while the candidate gives no scene "
        "(gapHmiSceneOutput). A fail stays a recorded result. A claim to be proven: no case has started."),
    (
        "requirement hmiDisplayVerdictClaim : HmiDisplayClaim / require constraint",
        "The claim requires the retained records of the runs and the record of the inspection that its argument "
        "cites, bound to HMI-CONFIG-001 and its receipt; it excludes a recording of a display that looks right, the "
        "vehicle and the road that the simulation stands in for, and the results of the bench of the "
        "driver-assistance increment."),
    (
        "requirement hmiDisplayInputsArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirement that VC-HMI-001 verifies, from the retained record of its "
        "runs; the argument holds once every cited case has a pass verdict and fails with any fail; an inconclusive "
        "or error verdict leaves it open."),
    (
        "requirement hmiContentVarianceArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirement that VC-HMI-001 verifies, from the retained record of its "
        "runs; the argument holds once every cited case has a pass verdict and fails with any fail; an inconclusive "
        "or error verdict leaves it open."),
    (
        "requirement hmiWarningSequenceArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirements that VC-HMI-004 and VC-HMI-005 verify, each from the "
        "retained records of its runs; the argument holds once every cited case has a pass verdict and fails with "
        "any fail; an inconclusive or error verdict leaves it open."),
    (
        "requirement hmiContentCurrencyArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirements that VC-HMI-006 and VC-HMI-007 verify, each from the "
        "retained records of its runs; the argument holds once every cited case has a pass verdict and fails with "
        "any fail; an inconclusive or error verdict leaves it open."),
    (
        "requirement hmiAndroidOutageArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirement that VC-HMI-008 verifies, from the retained record of its "
        "runs; the argument holds once every cited case has a pass verdict and fails with any fail; an inconclusive "
        "or error verdict leaves it open."),
    (
        "requirement hmiRendererAllocationArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirement that VC-HMI-009 verifies, from the retained record of its "
        "inspection; the argument holds once every cited case has a pass verdict and fails with any fail; an "
        "inconclusive or error verdict leaves it open."),
    (
        "requirement hmiRendererPathArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirement that VC-HMI-009 verifies, from the retained record of its "
        "inspection; the argument holds once every cited case has a pass verdict and fails with any fail; an "
        "inconclusive or error verdict leaves it open."),
    (
        "requirement hmiDisplayVerdictArgument : HmiDisplayArgument",
        "Argues the success criteria of the requirements that VC-HMI-001 to VC-HMI-010 verify, each from the "
        "retained records of its runs or of its inspection; the argument holds once every cited case has a pass "
        "verdict and fails with any fail; an inconclusive or error verdict leaves it open."),
    (
        "requirement hmiCounterClaimRecordingIsNoVerdict : HmiDisplayCounterClaim",
        "A recording of a display that looks right is no verdict: a verdict holds what the display shows against "
        "what the candidate gives and when, from the retained records of its runs (hmiDisplayQuestion)."),
    (
        "requirement hmiCounterClaimSimulatedConfigurationOnly : HmiDisplayCounterClaim",
        "The simulated road, vehicle and targets, and the vehicle speed that the simulator gives, stand in for the "
        "road, the vehicle and its speed signal; a verdict holds for that simulated configuration only "
        "(asmHmiSimulationStandsIn)."),
    (
        "requirement hmiCounterClaimDrivingBenchResultsNoEvidence : HmiDisplayCounterClaim",
        "The bench of the driver-assistance increment, its candidate build and its path into the AAOS SDV are reuse "
        "candidates; their results for that increment are no evidence for this one, and each case reads only the "
        "records of its own runs (asmHmiDrivingBenchReuse)."),
    (
        "requirement hmiCounterClaimSceneFromAStandIn : HmiDisplayCounterClaim",
        "The candidate gives no scene at its boundary, so the scene that the cases read is the one that a context "
        "stand-in publishes (phase8SceneOutputHeld); a verdict of REQ-HMI-001 or REQ-HMI-002 holds for the scenes of "
        "that stand-in, not for an output of the candidate (gapHmiSceneOutput)."),
    (
        "requirement hmiCounterClaimPerceptionNotJudged : HmiDisplayCounterClaim",
        "The display shows what the candidate gives, right or wrong; no case judges how well the candidate "
        "perceives, and a pass says nothing of how far its positions and its distances are from the simulator's "
        "(hmiPerceptionQualityOutOfScope)."),
    (
        "requirement hmiCounterClaimNoComplianceOrApproval : HmiDisplayCounterClaim",
        "No on-road, production-readiness, safety-approval, compliance, type-approval or certification claim, for "
        "the display or for the renderer's monitor (hmiOnRoadOperationOutOfScope)."),
    (
        "requirement hmiCounterClaimNoMemberProduct : HmiDisplayCounterClaim",
        "HMI-CONFIG-001 is no member product; a case with a pass verdict makes none and changes no scope decision, "
        "and what the display shows in each member stays open (gapHmiDisplayInProductLine)."),
    (
        "requirement hmiCounterClaimNoUpstreamEndorsement : HmiDisplayCounterClaim",
        "No upstream contact, endorsement or rights clearance is asserted: the changes to the projects of the "
        "renderer and of the candidate stay gaps, and a result about a project is shown to its maintainers before it "
        "is published (gapHmiUpstreamContact)."),
    (
        "requirement hmiCounterClaimDrawingToleranceUnset : HmiDisplayCounterClaim",
        "The tolerance of a drawn position is not set, so VC-HMI-001 gives no pass while the gap is open, whatever "
        "its frames show (GAP-HMI-003)."),
    (
        "requirement hmiCounterClaimEnvironmentOpenNoVerdict : HmiDisplayCounterClaim",
        "No case has started and no evidence record exists; the test environment is open; every claim of this slice "
        "is a claim to be proven (GAP-HMI-005)."),
    (
        "view hmiDisplayAssuranceView",
        "The assurance structure of the increment before any run: the eight claims, the arguments that support them "
        "and the cases they cite, the ten cases, the evidence record of a run and the record of the inspection, the "
        "bench and the environment gap, and the ten counter-claims with the records that keep them open, those "
        "records exposed beside them. It frames the phase 1 concern hmiDisplayVerdictConcern, so that it is answered "
        "in its domain."),
]
#: The guide's Phase 10 section: each paragraph, bullet and table row, whitespace collapsed, in order
#: (generated from the head with the test's own _guide_blocks).
GUIDE_SECTION_BLOCKS = [
    "[`hmi_display_verification_evidence.sysml`](../../textual-notation-of-model/packages/features/hmi/hmi_display_veri"
    "fication_evidence.sysml) states how each requirement will be judged before any run, so that each verdict is read "
    "against a case written first. This first slice is model only: no case has started, no evidence record exists, "
    "and every requirement keeps `NotStarted`. The five choices of the slice are the owner decision of 2026-11-26, as "
    "INC-DRIVING-002 took them: one case per requirement, an outcome vocabulary of the increment's own, the claims "
    "now, one evidence record per run and the test environment as a gap.",
    "- **One case per requirement.** VC-HMI-001 to VC-HMI-010 verify REQ-HMI-001 to REQ-HMI-010. Each binds the "
    "subject of its requirement to the realization of the HMI display in HMI-CONFIG-001 on the bench, checks the "
    "success criteria of its requirement and adds none. The bench refers to the configured product, owns nothing and "
    "is no product selection.",
    "| Case | Requirement | What it reads | Method |",
    "|---|---|---|---|",
    "| VC-HMI-001 | REQ-HMI-001, the scene as given | the runs of SC-HMI-001 to SC-HMI-007 | test |",
    "| VC-HMI-002 | REQ-HMI-002, the object that the system acts on | the runs of SC-HMI-001 to SC-HMI-007 | test |",
    "| VC-HMI-003 | REQ-HMI-003, the vehicle speed | the runs of SC-HMI-001, SC-HMI-002 and SC-HMI-007 | test |",
    "| VC-HMI-004 | REQ-HMI-004, the collision warning while requested | the runs of SC-HMI-001, SC-HMI-002 and "
    "SC-HMI-007 | test |",
    "| VC-HMI-005 | REQ-HMI-005, each warning mode within its limit | the runs of SC-HMI-001 and SC-HMI-002 | test |",
    "| VC-HMI-006 | REQ-HMI-006, outdated elements | the runs of SC-HMI-001 to SC-HMI-007 | test |",
    "| VC-HMI-007 | REQ-HMI-007, the warning unavailable | the runs of SC-HMI-001 to SC-HMI-007 | test |",
    "| VC-HMI-008 | REQ-HMI-008, the speed and the warning through outages | the runs of SC-HMI-003 to SC-HMI-006 | "
    "test |",
    "| VC-HMI-009 | REQ-HMI-009, the split of the renderers and the input paths | no run: the Phase 8 realization | "
    "inspection |",
    "| VC-HMI-010 | REQ-HMI-010, the display identity | the runs of SC-HMI-001 to SC-HMI-007, and outside them a "
    "display with one changed part | test |",
    "- **Outcome and verdict.** The increment's own `HmiDisplayEvidenceOutcome` has the six literals of the "
    "driver-assistance increment. `MapHmiDisplayEvidenceOutcomeToVerdict` maps the two pass outcomes to pass, "
    "`failObservedBehavior` to fail, `errorEvidence` to error and the rest to inconclusive. A run that is missing, or "
    "whose record is partial, is inconclusive, never pass. While the tolerance of a drawn position is not set "
    "(GAP-HMI-003), VC-HMI-001 gives `inconclusiveMissingEvidence` for evidence that meets every other clause of its "
    "criterion.",
    "- **One evidence record per run.** Every case that reads a run reads its `RetainedHmiDisplayRunEvidence`: "
    "HMI-CONFIG-001 and the receipt digest, the model revision, the run and its scenario, the display identity record "
    "of REQ-HMI-010 and the engineer who hashes the named files again, the candidate identity record of the "
    "driver-assistance increment, the simulation-clock and wall-clock spans, kept apart, the observations that Phase "
    "5 asks of System 2, and the claim boundary of the record. The inspection of REQ-HMI-009 keeps its own record, "
    "`RetainedHmiDisplayRealizationInspection`.",
    "- **Claims before evidence.** Eight claims, one for each Phase 1 concern whose question the ten cases answer: "
    "`hmiDisplayInputsConcern`, `hmiContentVarianceConcern`, `hmiWarningSequenceConcern`, "
    "`hmiContentCurrencyConcern`, `hmiAndroidOutageConcern`, `hmiRendererAllocationConcern`, `hmiRendererPathConcern` "
    "and `hmiDisplayVerdictConcern`. Each has an argument that cites the cases whose requirements name its concern; "
    "the argument for `hmiDisplayVerdictConcern` cites all ten. Ten counter-claims restate the non-claims of the "
    "framing and of the open gaps, each tied to its record: a recording of a display that looks right is no verdict, "
    "the simulated configuration only, no evidence from the results of the driver-assistance bench, the scene from a "
    "stand-in, no judgment of the candidate's perception, no compliance or approval, no member product, no upstream "
    "endorsement, the drawing tolerance not set, and the open test environment. The claims, the arguments and the "
    "counter-claims specialize the kernel's assurance kinds; nothing is satisfied.",
    "- **The test environment** stays open as GAP-HMI-005, which continues the readiness questions of Phase 8 until "
    "the probes fix its host and its topology: the renderer on the guest host with the three VMs, the transport of "
    "the renderer's topics, the composition of the two planes, the IVI image, the capture of the sound, the feed of "
    "the simulator's speed (GAP-HMI-002) and what stands in for the source of the scene. Each probe runs only on the "
    "owner's word.",
    "- **No validation case.** The validation of the needs stays planned in Phase 4 (SC-HMI-008 to SC-HMI-013).",
    "Three amendments of earlier phases come with this slice. The identity-term amendment of Phase 10 makes the "
    "display identity name the elements that Phase 8 places inside the display, and so retires GAP-HMI-004. The "
    "scene-form amendment of Phase 10 types `DisplaySceneMessage` in a form of the display's own, under the owner "
    "direction of 2026-11-26: each driving application gives its scene in that form through a translation of its own. "
    "`HmiDisplayPhysicalSystem` specializes the framing's `HmiDisplaySystem`, so the realization in HMI-CONFIG-001 "
    "can be the subject that the cases bind. Phase 8 also takes two corrections in place: COVESA VSS types the "
    "distance to the object that the system acts on in the scene message, and GAP-HMI-003 is carried open.",
    "One view answers the phase's question, a tree of the Argumentation Assurance viewpoint: the claims with their "
    "arguments and the cases they cite, the evidence records, the bench, the counter-claims, the records they are "
    "tied to and the gaps. It frames `hmiDisplayVerdictConcern`. Its diagram comes from the licensed Syside run; "
    "[`VIEWS.md`](../../textual-notation-of-model/packages/features/hmi/VIEWS.md) lists the views.",
]

_NOT_CODE = re.compile(r"/\*.*?\*/|//[^\n]*|\"(?:[^\"\\]|\\.)*\"", re.S)


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
            return text[start: end + 1]
    raise AssertionError(f"{header!r} has an unbalanced body")


def _flat(text: str) -> str:
    return " ".join(re.sub(r"^\s*\*\s?", "", text, flags=re.M).split())


def _docs(path: Path) -> str:
    return _flat(path.read_text(encoding="utf-8"))


def _requirements() -> dict[int, tuple[str, str, str]]:
    """Requirement number -> (usage name, verification method, success criteria), from the phase 5 package."""
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    found = {}
    for match in re.finditer(r"requirement <'REQ-HMI-(\d{3})'> (\w+) : \w*RequirementCandidate \{", raw):
        body = _body(raw[match.start():], re.escape(match[0]))
        (method,) = re.findall(r'verificationMethod = "(\w+)";', body)
        (criteria,) = re.findall(r'successCriteria = "([^"]+)";', body)
        found[int(match[1])] = (match[2], method, criteria)
    assert sorted(found) == NUMBERS
    return found


def _usages() -> dict[int, tuple[str, str, str]]:
    """Case number -> (usage name, definition name, raw usage body with its doc)."""
    raw = SLICE.read_text(encoding="utf-8")
    return {int(m[1]): (m[2], m[3], _body(raw[m.start():], re.escape(m[0])))
            for m in re.finditer(r"verification <'VC-HMI-(\d{3})'>\s+(\w+)\s*:\s*(\w+)\s*\{", raw)}


def _definitions() -> dict[str, str]:
    code = _code(SLICE)
    return {m[1]: _body(code[m.start():], re.escape(m[0])) for m in re.finditer(r"\bverification def (\w+) \{", code)}


def _definition_docs() -> dict[str, str]:
    raw = SLICE.read_text(encoding="utf-8")
    return {m[1]: _flat(_body(raw[m.start():], re.escape(m[0])))
            for m in re.finditer(r"\bverification def (\w+) \{", raw)}


def _scenarios_named(text: str) -> list[str]:
    """The enum literals of the SC-HMI identities that a text names, ranges expanded, in the order of the enum."""
    numbers = set()
    for first, last in SC_REFERENCE.findall(text):
        numbers |= set(range(int(first), int(last or first) + 1))
    return [literal for literal, sc in SC_IDS.items() if int(sc[-3:]) in numbers]


def _doc_texts(raw: str) -> list[tuple[str, str]]:
    """Every comment of the package in order, as (its owner, its text whitespace collapsed). The owner is the path of
    the declarations that enclose it below the package, each up to its {, joined by " / "; the file's header comment is
    "header", and a comment that is no doc is marked "comment in"."""
    found: list[tuple[str, str]] = []
    stack: list[str] = []
    statement, i = "", 0
    while i < len(raw):
        if raw.startswith("/*", i):
            end = raw.index("*/", i + 2)
            owner = "header"
            if stack:
                owner = " / ".join(stack[1:]) or "package"
                if statement.split()[-1:] != ["doc"]:
                    owner = f"comment in {owner}"
            found.append((owner, _flat(raw[i + 2:end])))
            statement, i = "", end + 2
            continue
        if raw.startswith("//", i):
            i = raw.index("\n", i)
            continue
        if raw[i] == '"':
            string = re.compile(r'"(?:[^"\\]|\\.)*"').match(raw, i)
            assert string, "an unclosed string"
            statement, i = statement + '""', string.end()
            continue
        if raw[i] in "{;}":
            if raw[i] == "{":
                stack.append(" ".join(statement.split()))
            elif raw[i] == "}":
                stack.pop()
            statement = ""
        else:
            statement += raw[i]
        i += 1
    assert not stack, "the braces of the package balance"
    return found


def _guide_blocks(raw_section: str) -> list[str]:
    """The paragraphs, bullets and table rows of a guide section, in order, each whitespace collapsed."""
    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", raw_section.strip()):
        if block.startswith("|"):
            blocks += [" ".join(row.split()) for row in block.splitlines()]
        elif block.startswith("- "):
            blocks += [" ".join(item.split()) for item in re.split(r"(?m)^(?=- )", block) if item.strip()]
        else:
            blocks.append(" ".join(block.split()))
    return blocks


# -- the cases ------------------------------------------------------------------------------------


def test_each_requirement_of_the_increment_is_verified_by_exactly_one_case() -> None:
    """Ten requirements, ten cases VC-HMI-001 to -010, each objective verifying the requirement of its own number
    with its subject bound to the realization of the HMI display on the bench."""
    requirements = _requirements()
    usages = _usages()
    definitions = _definitions()
    assert sorted(usages) == NUMBERS
    verified = {}
    for number, (usage, definition, _) in usages.items():
        body = definitions[definition]
        assert len(re.findall(r"\bobjective \w+ \{", body)) == 1, usage
        objective = _body(body, r"\bobjective \w+ \{")
        (target,) = re.findall(r"\bverify (\w+) \{ subject hmiDisplay = verifiedBench\.displayRealization; \}",
                               objective)
        assert len(re.findall(r"\bverify\b", objective)) == 1, usage
        verified[number] = target
    assert verified == {n: name for n, (name, _, _) in requirements.items()}, "each case verifies its own requirement"
    assert len(definitions) == len(NUMBERS)
    assert len(re.findall(r"\bverify\b", _code(SLICE))) == len(NUMBERS), "no second case on one requirement"


def test_the_case_ids_open_the_series_and_are_unique_in_the_model() -> None:
    ids = []
    for path in sorted((ROOT / "textual-notation-of-model").rglob("*.sysml")):
        ids += re.findall(r"<'(VC-[A-Z0-9-]+)'>", path.read_text(encoding="utf-8"))
    assert len(set(ids)) == len(ids), "a verification-case id is declared once in the model"
    own = re.findall(r"<'(VC-HMI-\d{3})'>", SLICE.read_text(encoding="utf-8"))
    assert own == [f"VC-HMI-{n:03d}" for n in NUMBERS]
    increment_files = charter_package_files(FRAMING, "hmiDisplayCharter")
    assert SLICE in increment_files
    elsewhere = [i for path in increment_files if path != SLICE
                 for i in re.findall(r"<'(VC-HMI-\d{3})'>", path.read_text(encoding="utf-8"))]
    assert not elsewhere, "a case id belongs to the verification-evidence slice and nowhere else"


def test_no_case_has_started_and_each_states_its_scenarios() -> None:
    """Each usage doc opens with Not started and names the scenarios by SC identity and enum literal that its
    requirement's criteria read; the inspection names none; every requirement keeps NotStarted."""
    requirements = _requirements()
    for number, (usage, _, body) in _usages().items():
        doc = _flat(body)
        assert "doc /* Not started. Scenarios: " in doc, usage
        scenarios = CASE_SCENARIOS[number]
        assert _scenarios_named(requirements[number][2]) == scenarios, (usage, "the criterion names them")
        assert re.findall(r"HmiDisplayScenarioIdentity::(\w+)", doc) == scenarios, usage
        for scenario in scenarios:
            assert f"{SC_IDS[scenario]} (HmiDisplayScenarioIdentity::{scenario})" in doc, (usage, scenario)
        kinds = "(inspect, analyze)" if number == INSPECTED else "(test, analyze)"
        assert f"@VerificationMethod{{ kind = {kinds}; }}" in body, usage
        assert "subject verifiedBench :> hmiDisplayVerificationBench;" in body, usage
        assert ("Test environment: open (GAP-HMI-005)." in doc) is (number != INSPECTED), usage
    assert ("Scenarios: none; the case reads the realization that phase 8 records, at the model revision that its "
            "record names, and no run.") in _flat(_usages()[INSPECTED][2])
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    assert raw.count("verificationStatus = VVStatus::NotStarted") == len(NUMBERS)
    assert "VVStatus::" not in SLICE.read_text(encoding="utf-8"), "this slice sets no status"


def test_each_case_collects_by_its_requirements_method_and_analyzes_against_the_requirement() -> None:
    """Nine requirements state the method test and REQ-HMI-009 the method inspect: the nine cases collect the run
    record by test, the case of 009 collects the inspection record by inspection; all process and evaluate by
    analysis, to the increment's own outcome and the standard verdict."""
    requirements = _requirements()
    definitions = _definitions()
    docs = _definition_docs()
    for number, (usage, definition, _) in _usages().items():
        body = definitions[definition]
        method = requirements[number][1]
        assert method == ("inspect" if number == INSPECTED else "test"), number
        record = INSPECTION_RECORD if method == "inspect" else RUN_RECORD
        assert re.search(rf"action collectData \{{\s*@VerificationMethod\{{ kind = {method}; \}}\s*out item "
                         rf"retainedEvidence : {record};", body), usage
        assert re.search(r"action processData \{\s*@VerificationMethod\{ kind = analyze; \}\s*"
                         r"in item retainedEvidence : "
                         rf"{record} = collectData\.retainedEvidence;\s*out evaluatedOutcome : {OUTCOME};", body), usage
        assert re.search(r"action evaluateData \{\s*@VerificationMethod\{ kind = analyze; \}\s*in evaluatedOutcome : "
                         rf"{OUTCOME} = processData\.evaluatedOutcome;", body), usage
        assert f"out verdict : VerdictKind = {VERDICT_MAP}(evaluatedOutcome);" in body, usage
        assert "return verdict : VerdictKind = evaluateData.verdict;" in body, usage
        assert re.search(rf"\bsubject verifiedBench : {BENCH_DEF};", body), usage
        lead = "Inspection" if method == "inspect" else "Test"
        assert f"doc /* {lead} of REQ-HMI-{number:03d}. collectData retains" in docs[definition], definition


def test_each_case_restates_its_requirements_criterion_and_adds_none() -> None:
    """processData checks the criterion as the requirement states it: 'Met when' becomes 'processData checks that',
    each further 'when' becomes 'that', and nothing else changes."""
    requirements = _requirements()
    docs = _definition_docs()
    for number, (_, definition, _) in _usages().items():
        criteria = requirements[number][2]
        checked = ("processData checks that " + criteria.removeprefix("Met when ")
                   .replace("; and when ", "; and that ").replace("; when ", "; that "))
        if number == 2:
            # the one exception: the clause that names a module of the application is restated by reference
            assert AUTODRIVE_CLAUSE in checked
            checked = checked.replace(AUTODRIVE_CLAUSE, BY_REFERENCE)
        assert checked in docs[definition], number
        assert docs[definition].count("processData checks that") == 1, number
    assert ("While the tolerance of a drawn position is not set (GAP-HMI-003), evidence that meets every other clause "
            "gives inconclusiveMissingEvidence, never pass.") in docs["ShowTheSceneAsGivenVerification"]
    assert IDENTITY_TERM in docs["RecordDisplayIdentityVerification"]
    raw = SLICE.read_text(encoding="utf-8")
    assert "AutoDrive" not in raw and BY_REFERENCE in _docs(SLICE), "new texts name no module of the application"


def test_every_case_is_performed_by_the_verification_system_once() -> None:
    system = _body(_code(SLICE), r"\bpart hmiDisplayVerificationSystem \{")
    assert re.findall(r"\bperform (\w+);", system) == [usage for _, (usage, _, _) in sorted(_usages().items())]
    code = " ".join(_code(SLICE).split())
    assert ("dependency hmiVerificationSystemIsTheVerificationEnvironment from hmiDisplayVerificationSystem to "
            "hmiDisplayVerificationEnvironment;") in code
    assert f"dependency hmiEnvironmentGapOnVerificationSystem from {GAP_NAME} to hmiDisplayVerificationSystem;" in code
    assert re.search(r"\bpart hmiDisplayVerificationEnvironment : System2EngineeringAndAssuranceSystem \{",
                     _code(FRAMING))


def test_no_validation_case_is_added_and_the_phase_4_reviews_stay_planned() -> None:
    code = _code(SLICE)
    assert "ValidationPlanningScenario" not in code and "passBoundedValidation?" in " ".join(code.split())
    assert ("The validation of the needs stays planned in phase 4 (SC-HMI-008 to SC-HMI-013). This slice adds no "
            "validation case.") in _docs(SLICE)
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    for number in range(8, 14):
        assert re.search(rf"part <'SC-HMI-{number:03d}'> \w+ : ValidationPlanningScenario \{{", raw), number


# -- the vocabulary, the records and the bench ------------------------------------------------------------------


def test_the_outcome_vocabulary_is_the_increments_own_with_the_six_shared_literals() -> None:
    code = _code(SLICE)
    assert re.findall(r"(\w+);", _body(code, rf"\benum def {OUTCOME} \{{")) == OUTCOMES
    calc = " ".join(_body(code, rf"\bcalc def {VERDICT_MAP} \{{").split())
    assert f"in outcome : {OUTCOME};" in calc
    branches = re.findall(rf"outcome == {OUTCOME}::(\w+)\? VerdictKind::(\w+)", calc)
    assert branches == [("passBoundedVerification", "pass"), ("passBoundedValidation", "pass"),
                        ("failObservedBehavior", "fail"), ("errorEvidence", "error")]
    assert calc.rstrip("} ").endswith("else VerdictKind::inconclusive;")
    for foreign in ("AssistanceEvidenceOutcome", "DrivingEvidenceOutcome", "MiddlewareEvidenceOutcome"):
        assert foreign not in code, foreign
    assert re.findall(r"(\w+);", _body(code, r"\benum def HmiDisplayScenarioIdentity \{")) == ALL
    assert "A missing or partial record gives inconclusive, never pass." in _docs(SLICE)


def test_the_slice_header_states_the_readings_the_cases_make() -> None:
    header = _flat(SLICE.read_text(encoding="utf-8").split("*/", 1)[0])
    for phrase in ("Where the requirements leave a reading to the cases, the cases read them so.",
                   "A run that is missing, or whose record is partial, gives inconclusiveMissingEvidence, never pass.",
                   "While the tolerance of a drawn position is not set (GAP-HMI-003), VC-HMI-001 gives "
                   "inconclusiveMissingEvidence for evidence that meets every other clause of its criterion.",
                   "records its display identity outside a run, so that no criterion over each run reads it.",
                   "the context stand-in of phase 8 publishes, since the candidate gives no scene at its boundary "
                   "(gapHmiSceneOutput).",
                   "A claim stated before its evidence is a claim to be proven, not a result.",
                   "The claims of the increment are stated now, one for each phase 1 concern whose question the cases "
                   "answer, eight in all, each with an argument that cites the planned cases that answer it.",
                   OWNER_CHOICES):
        assert phrase in header, phrase
    assert _docs(SLICE).count("owner decision of 2026-11-26") == 1, "the choices are recorded once, in the header"


def test_the_run_record_binds_the_identities_the_configuration_and_the_requirements_name() -> None:
    code = _code(SLICE)
    record = _body(code, rf"\bitem def {RUN_RECORD} \{{")
    assert re.findall(r"\battribute (\w+) : ([\w:]+);", record) == RUN_ATTRIBUTES
    docs = _docs(SLICE)
    for phrase in ("every case that reads the run reads this record.",
                   "It binds HMI-CONFIG-001 as its configurationIdentity.",
                   "receiptSha256 is the SHA-256 of the receipt the run ran against, as HMI-CONFIG-001 asks of the "
                   "evidence that binds it; if it differs from the receiptSha256 of HMI-CONFIG-001, the verdict holds "
                   "for HMI-CONFIG-001 only if the configuration's own receipt record did not change, which the pull "
                   "request that rebinds the digest states.",
                   "runIdentity names the run, one execution of the HMI display on one scenario from its start to its "
                   "end, and scenario names that scenario.",
                   "(REQ-HMI-010), and independentEngineerIdentity names the engineer who hashes the named files "
                   "again.",
                   "candidate identity record that the driver-assistance system records in the run (REQ-DRIVING-044).",
                   "and the files and the settings that the display identity names.",
                   "simulationClockSpan and wallClockSpan are the two clocks of the run, kept apart.",
                   "(hmiTestbedObligationsOfPhase5)"):
        assert phrase in docs, phrase
    variability = _docs(VARIABILITY)
    assert "Evidence that binds HMI-CONFIG-001 also records the receipt SHA-256 it ran against." in variability
    requirements = _docs(REQUIREMENTS)
    assert "- Run: one execution of the HMI display on one scenario of SC-HMI-001 to SC-HMI-007, from its start to " \
           "its end." in requirements
    assert "comment hmiTestbedObligationsOfPhase5 about" in REQUIREMENTS.read_text(encoding="utf-8")
    inspection = _body(code, rf"\bitem def {INSPECTION_RECORD} \{{")
    assert re.findall(r"\battribute (\w+) : ([\w:]+);", inspection) == INSPECTION_ATTRIBUTES
    assert "The evidence record of the inspection of REQ-HMI-009, which reads the realization and no run." in docs
    for name in ("HmiDisplayPhysicalSystem", "phase8WarningPresentationSettled"):
        assert name in _flat(_body(SLICE.read_text(encoding="utf-8"), rf"\bitem def {INSPECTION_RECORD} \{{")), name
        assert name in PHYSICAL.read_text(encoding="utf-8"), name
    typed = re.findall(r"out item retainedEvidence : (\w+);", code)
    assert typed.count(INSPECTION_RECORD) == 1 and typed.count(RUN_RECORD) == len(NUMBERS) - 1
    assert not re.search(rf"(?<!in )(?<!out )\bitem \w+ : (?:{RUN_RECORD}|{INSPECTION_RECORD})\b", code), \
        "no record exists"


def test_the_bench_refers_to_the_realization_in_hmi_config_001() -> None:
    code = " ".join(_code(SLICE).split())
    bench = _body(code, rf"\bpart def {BENCH_DEF} \{{")
    assert ("ref part system1ConfiguredProduct :> DE4SDV_HmiDisplayVariabilityConfiguration::configuredProduct;"
            in bench)
    assert ("ref part displayRealization :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem = "
            "system1ConfiguredProduct.displayRealization;") in bench
    assert len(re.findall(r"\bpart \w+ :", bench)) == 2 and not re.search(r"(?<!ref )\bpart \w+ :", bench), \
        "the bench owns no System 1 part"
    assert not re.search(r"\b(?:item|attribute|port|action)\b", bench), "the bench owns nothing"
    assert f"part hmiDisplayVerificationBench : {BENCH_DEF};" in code
    variability = _code(VARIABILITY)
    assert re.search(r"\bpart <'HMI-CONFIG-001'> configuredProduct : ", variability)
    assert "part displayRealization : HmiDisplayPhysicalSystem;" in variability
    assert re.search(r"\bpart def HmiDisplayPhysicalSystem :> DE4SDV_HmiDisplayFraming::HmiDisplaySystem \{",
                     _code(PHYSICAL)), "the realization conforms to the subject of the requirements"
    assert "The bench is not a product selection." in _docs(SLICE)


def test_the_environment_gap_continues_the_readiness_questions_of_phase_8() -> None:
    raw = SLICE.read_text(encoding="utf-8")
    gap = _body(raw, rf"\bpart <'{GAP}'> {GAP_NAME} : IncrementGap \{{")
    assert "disposition" not in _code(SLICE), "a gap has no disposition before phase 11"
    doc = _flat(gap)
    for phrase in ("Open: the System 2 test environment is not shown to run the cases.",
                   "(asmHmiRendererWithoutGraphicsCard)", "(gapHmiRendererIntegration)", "(GAP-HMI-002)",
                   "(gapHmiSceneOutput)", "(hmiTestbedObligationsOfPhase5)",
                   "Each probe runs only on the owner's word, and nothing of the next slice is built before the probes "
                   "are read.", "The next slice fills the evidence record, plans the runs and closes this gap."):
        assert phrase in doc, phrase
    code = " ".join(_code(SLICE).split())
    for name, (target, home) in GAP_CONTINUES.items():
        assert f"dependency {name} from {GAP_NAME} to {target};" in code, name
        assert re.search(rf"\b(?:part|comment) (?:<'[A-Z0-9-]+'> )?{target}\b", _code(home)), target
    physical = _docs(PHYSICAL)
    assert "Which transport carries the renderer's topics between the VMs" in physical
    assert "no readiness probe has measured the renderer drawing on the guest host" in physical
    ids = sorted(set(re.findall(r"GAP-HMI-\d{3}", "".join(p.read_text(encoding="utf-8") for p in HMI.glob("*.sysml")))))
    assert max(ids) == GAP and raw.count(f"<'{GAP}'>") == 1, "the next free gap number of the HMI series"


# -- the assurance structure ----------------------------------------------------------------------


def _answered_concerns() -> list[str]:
    """The phase 1 concerns that the Source lines of REQ-HMI-001 to REQ-HMI-010 name, in order, from the raw text."""
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    named: list[str] = []
    for match in re.finditer(r"requirement <'REQ-HMI-(\d{3})'> (\w+) : \w*RequirementCandidate \{", raw):
        body = _body(raw[match.start():], re.escape(match[0]))
        (source,) = re.findall(r'source = "([^"]+)";', body)
        named += [c for c in re.findall(r"\b(hmi\w+Concern)\b", source) if c not in named]
    return named


def _concern_cases() -> dict[str, list[int]]:
    """Concern -> the case numbers whose requirement's Source line names it; every case answers the verdict concern."""
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    cases: dict[str, list[int]] = {}
    for match in re.finditer(r"requirement <'REQ-HMI-(\d{3})'> (\w+) : \w*RequirementCandidate \{", raw):
        body = _body(raw[match.start():], re.escape(match[0]))
        (source,) = re.findall(r'source = "([^"]+)";', body)
        for concern in re.findall(r"\b(hmi\w+Concern)\b", source):
            cases.setdefault(concern, []).append(int(match[1]))
    cases[VERDICT_CONCERN] = list(NUMBERS)
    return cases


def test_one_claim_answers_each_phase_1_concern_whose_question_the_cases_answer() -> None:
    """The answered concerns are those that the Source lines of the requirements name (hmiDisplayVerdictConcern among
    them); each has one claim and one argument, and the argument cites the cases whose requirements name it."""
    code = _code(SLICE)
    raw = SLICE.read_text(encoding="utf-8")
    usages = {n: u for n, (u, _, _) in _usages().items()}
    assert list(CLAIMS.values()) == _answered_concerns() and VERDICT_CONCERN in CLAIMS.values()
    framing = _code(FRAMING)
    for concern in CLAIMS.values():
        assert re.search(rf"\bconcern {concern} : \w+Concern \{{", framing), concern
    assert re.findall(r"\bconcern (\w+) : ArgumentationAssuranceConcern \{", framing) == [VERDICT_CONCERN]
    assert re.findall(r"\brequirement (\w+) : HmiDisplayClaim \{", code) == [f"hmi{s}Claim" for s in CLAIMS]
    assert re.findall(r"\brequirement (\w+) : HmiDisplayArgument \{", code) == [f"hmi{s}Argument" for s in CLAIMS]
    cases = _concern_cases()
    for stem, concern in CLAIMS.items():
        claim = _flat(_body(raw, rf"\brequirement hmi{stem}Claim : HmiDisplayClaim \{{"))
        assert f"doc /* Answers {concern}. " in claim, stem
        head, tail = claim.split(f"subject claimSubject : {BENCH_DEF}; require constraint {{", 1)
        assert head.rstrip(" /").endswith("A claim to be proven: no case has started."), stem
        assert tail.startswith(" doc /* The claim requires the re") and "; it excludes " in tail, stem
        assert CLAIM_TEXTS[stem] == (head.removeprefix("{ doc /* ").rstrip(" */"),
                                     tail.removeprefix(" doc /* ").removesuffix(" / } }")), stem
        cites = re.findall(rf"\bdependency hmi{stem}ArgumentCitesCases\s+from hmi{stem}Argument\s+to ([^;]+);", code)
        assert len(cites) == 1 and re.findall(r"\w+", cites[0]) == [usages[n] for n in cases[concern]], stem
        assert re.findall(rf"\bdependency claimSupportedByHmi{stem}Argument\s+from hmi{stem}Argument\s+to (\w+);",
                          code) == [f"hmi{stem}Claim"], stem
        argument = _flat(_body(raw, rf"\brequirement hmi{stem}Argument : HmiDisplayArgument \{{"))
        named = ["VC-HMI-001 to VC-HMI-010"] if concern == VERDICT_CONCERN else \
            [f"VC-HMI-{n:03d}" for n in cases[concern]]
        assert re.findall(r"VC-HMI-\d{3}(?: to VC-HMI-\d{3})?", argument) == named, stem
        assert "the argument holds once every cited case has a pass verdict and fails with any fail" in argument, stem
    assert len(re.findall(r"\bdependency \w+ArgumentCitesCases\b", code)) == len(CLAIMS)
    assert len(re.findall(r"\bdependency claimSupportedBy\w+\b", code)) == len(CLAIMS)
    for definition, kind in [("HmiDisplayClaim", "AssuranceClaim"), ("HmiDisplayArgument", "AssuranceArgument"),
                             ("HmiDisplayCounterClaim", "AssuranceCounterClaim")]:
        assert f"requirement def {definition} :> {kind};" in code
    assert "RequirementCandidate" not in code and not re.search(r"\bsatisfy\b", code)


def test_each_counter_claim_restates_a_non_claim_of_the_framing_and_is_tied_to_its_record() -> None:
    code = _code(SLICE)
    raw = SLICE.read_text(encoding="utf-8")
    for stem, (target, home) in COUNTER_CLAIMS.items():
        doc = _flat(_body(raw, rf"\brequirement hmiCounterClaim{stem} : HmiDisplayCounterClaim \{{"))
        ties = re.findall(rf"dependency (hmiCounterClaim{stem}BoundTo)\s+from hmiCounterClaim{stem} to (\w+);", code)
        assert ties == [(f"hmiCounterClaim{stem}BoundTo", target)], stem
        assert re.search(rf"\bpart (?:<'[A-Z0-9-]+'> )?{target} : \w+ \{{", _code(home)), (stem, target)
        named = {SLICE: GAP, PHYSICAL: "GAP-HMI-003"}.get(home, target)
        assert doc.split(" / subject bench : ", 1)[0].endswith(f"({named})."), (stem, named)
        if home is FRAMING:
            assert f"private import DE4SDV_HmiDisplayFraming::{target};" in code, target
    assert re.findall(r"\brequirement hmiCounterClaim(\w+) : HmiDisplayCounterClaim \{", code) == list(COUNTER_CLAIMS)
    framing = _docs(FRAMING)
    for source in ("A recording of a display that looks right does not.",
                   "Their results for that increment are not evidence for this one.",
                   "The display shows what the candidate gives, right or wrong.",
                   "No upstream contact, endorsement or rights clearance is asserted.",
                   "A verdict holds for that simulated configuration only."):
        assert source in framing, source


def test_the_slice_makes_no_result_or_approval_claim() -> None:
    raw = SLICE.read_text(encoding="utf-8")
    assert not PAST_BEHAVIOR.search(raw) and not APPROVAL.search(raw)
    assert not re.search(r"(?i)\bthe owner (?:said|wrote|asked|told)\b|[\u201c\u201d]", raw), \
        "the decisions are stated neutrally and dated, never quoted"
    assert ("This slice makes no result, evidence, acceptance, safety, compliance or certification claim."
            in _docs(SLICE))


def test_the_assurance_view_frames_the_phase_1_assurance_concern_and_links_everything() -> None:
    code = _code(SLICE)
    view = _body(code, r"\bview hmiDisplayAssuranceView \{")
    viewpoint = " ".join(_body(view, r"\bviewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint \{")
                         .split())
    assert viewpoint == "{ frame hmiDisplayVerdictConcern; }"
    exposed = re.findall(r"\bexpose ([\w:]+);", view)
    usages = [u for _, (u, _, _) in sorted(_usages().items())]
    expected = ([f"hmi{s}Claim" for s in CLAIMS] + [f"hmi{s}Argument" for s in CLAIMS]
                + [f"hmiCounterClaim{s}" for s in COUNTER_CLAIMS] + usages
                + [RUN_RECORD, INSPECTION_RECORD, BENCH_DEF, GAP_NAME]
                + [target for target, home in COUNTER_CLAIMS.values() if home is not SLICE]
                + [f"claimSupportedByHmi{s}Argument" for s in CLAIMS] + [f"hmi{s}ArgumentCitesCases" for s in CLAIMS]
                + [f"hmiCounterClaim{s}BoundTo" for s in COUNTER_CLAIMS])
    assert exposed == expected, "every claim, argument and tie is exposed"
    assert len(exposed) == 75, "the count of exposed elements"
    assert not re.search(r"\b(?:filter|depth)\b", view), "no filter or depth changes the tree"
    assert "render asTreeDiagram;" in view and "attribute maxCompartmentEntries = 0;" in view
    assert len(re.findall(r"\bview \w+", code)) == 1, "one view in the phase"
    assert not re.search(r"\bconcern \w+ :", code), "the phase 1 concern is framed; the slice adds none"


def test_the_package_declares_no_name_that_another_model_package_declares() -> None:
    kinds = (r"(?:part def|part|item def|enum def|calc def|verification def|verification|requirement def|requirement|"
             r"concern|view|dependency)")
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(?:<'[^']*'>\s*)?(\w+)", _code(SLICE)))
    assert len(declared) >= 50, "the population of the check must not be vacuous"
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


# -- the amendments of earlier phases -------------------------------------------------------------


def test_the_identity_term_amendment_names_the_phase_8_elements_and_retires_gap_hmi_004() -> None:
    requirements = _docs(REQUIREMENTS)
    term = requirements.split("- Display identity: ", 1)[1].split(" - Run: ", 1)[0]
    for element in IDENTITY_ELEMENTS:
        assert element in term, element
    assert "of the image of the SDV Core VM, of the IVI VM and of the SDV Media VM" in term
    assert requirements.count("identity-term amendment of phase 10") == 1, \
        "the requirements head records the amendment once"
    physical = _docs(PHYSICAL)
    assert "GAP-HMI-004" in physical and "GAP-HMI-004 is retired." in physical
    for path in HMI.glob("*.sysml"):
        text = path.read_text(encoding="utf-8")
        assert "<'GAP-HMI-004'>" not in text and "gapHmiIdentityMissesPhase8Elements" not in text, path.name
    assert "configuredProductDisplayIdentityGap" not in VARIABILITY.read_text(encoding="utf-8")
    service = _flat(_body(PHYSICAL.read_text(encoding="utf-8"),
                          r"\bpart def DisplayIdentityRecordingService :> PhysicalAllocationElement \{"))
    assert "of the files of the builds of the vehicle data publisher, of this service and of the composition" in service


def test_the_scene_form_amendment_types_the_scene_message_in_a_form_of_the_displays_own() -> None:
    code = _code(PHYSICAL)
    for owner, attribute, kind in SCENE_FIELDS:
        header = rf"\b(?:item|attribute) def {owner} (?::> \w+ )?\{{"
        assert f"attribute {attribute} : {kind};" in " ".join(_body(code, header).split()), (owner, attribute)
    functional = _code(HMI / "hmi_display_functional_architecture.sysml")
    for inherited in ("attribute captureTime : ISQ::DurationValue;", "attribute actedOnObjectDistance : "
                      "ISQ::LengthValue[0..1];", "attribute actedOnObjectSpeed : ISQ::SpeedValue[0..1];"):
        assert inherited in functional, inherited
    raw = PHYSICAL.read_text(encoding="utf-8")
    assert f'attribute :>> dataTypeAndUnit = "{SCENE_UNITS}";' in raw
    assert "open until phase 10" not in raw and "before phase 10" not in raw
    assert "translation of its own" in _docs(PHYSICAL) and SCENE_FORM in _docs(PHYSICAL)
    framing = _docs(FRAMING)
    assert SCENE_FORM in framing and "stays open until phase 10" not in framing


def test_gap_hmi_003_stays_open_until_the_drawing_sets_it() -> None:
    gap = _flat(_body(PHYSICAL.read_text(encoding="utf-8"), r"\bpart <'GAP-HMI-003'> gapHmiDrawingToleranceUnset : "
                                                             r"IncrementGap \{"))
    assert ("It is set with the app's drawing; until then the gap stays open, and it goes to the baseline open if the "
            "drawing does not set it before.") in gap
    assert "before phase 10" not in gap
    assert "inherits two open gaps of phase 8" in _docs(VARIABILITY)


# -- the charter and the guide --------------------------------------------------------------------


def test_the_charter_names_the_phase_10_package_last() -> None:
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", FRAMING.read_text(encoding="utf-8"), re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-2:] == [
        "DE4SDV_HmiDisplayVariabilityConfiguration", PACKAGE]
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", _code(SLICE)) == [PACKAGE], "one global package per file"


def test_the_guide_describes_the_first_phase_10_slice() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    order = [guide.index(heading) for heading in ("## Variability and configuration (Phase 9)",
                                                  "## Verification and evidence (Phase 10)",
                                                  "## What the framing already records as open")]
    assert order == sorted(order)
    raw_section = guide.split("## Verification and evidence (Phase 10)", 1)[1].split("\n## ", 1)[0]
    section = " ".join(raw_section.split())
    for text in ("VC-HMI-001", "VC-HMI-010", "HMI-CONFIG-001", "**One case per requirement.**", "`NotStarted`", GAP,
                 "simulation-clock and wall-clock spans", "Ten counter-claims",
                 "**Claims before evidence.** Eight claims, one for each Phase 1 concern whose question the ten cases "
                 "answer:", GUIDE_CHOICES,
                 "the argument for `hmiDisplayVerdictConcern` cites all ten.", "the claim boundary of the record.",
                 "Argumentation Assurance", "**No validation case.**", "`hmiDisplayVerdictConcern`",
                 "A run that is missing, or whose record is partial, is inconclusive, never pass.",
                 "identity-term amendment of Phase 10", "scene-form amendment of Phase 10", GUIDE_CORRECTIONS,
                 "(../../textual-notation-of-model/packages/features/hmi/hmi_display_verification_evidence.sysml)"):
        assert text in section, text
    rows = re.findall(r"^\| (VC-HMI-\d{3}) \| (REQ-HMI-\d{3}), ([^|]+) \| ([^|]+) \| (\w+) \|$", raw_section, re.M)
    assert [(case, requirement) for case, requirement, _, _, _ in rows] == [
        (f"VC-HMI-{n:03d}", f"REQ-HMI-{n:03d}") for n in NUMBERS]
    for (_, _, _, reads, method), number in zip(rows, NUMBERS):
        assert method == ("inspection" if number == INSPECTED else "test"), number
        assert _scenarios_named(reads) == CASE_SCENARIOS[number], number
    assert not PAST_BEHAVIOR.search(section) and not APPROVAL.search(section) and "instrument" not in section
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_hmi_display_verification_evidence.py" in check
    flat = " ".join(guide.split())
    assert NEXT_OBLIGATION in flat and flat.count("The next model obligation is") == 1
    for concern in CLAIMS.values():
        assert f"`{concern}`" in section, concern
    assert "One claim answers" not in section and "the claim with its argument" not in section


def test_the_guide_states_the_phase_10_section_block_by_block() -> None:
    """Every paragraph, bullet and table row of the section, whole and in order, as the slice states it."""
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.count("\n## Verification and evidence (Phase 10)\n") == 1
    raw_section = guide.split("\n## Verification and evidence (Phase 10)\n", 1)[1].split("\n## ", 1)[0]
    assert _guide_blocks(raw_section) == GUIDE_SECTION_BLOCKS, "every paragraph, bullet and table row, in order"
    assert all(len(line) <= 79 or line.startswith("|") or "](" in line for line in raw_section.splitlines()), \
        "the guide wraps at 79"


# -- the code of the package whole ------------------------------------------------------------------------------


def _skeleton(raw: str) -> list[str]:
    """One line per declaration, up to its own { or ;, whitespace collapsed, two spaces per brace depth; each doc and
    comment as /*…*/ and each string as \"\"; line notes dropped (pinned apart)."""
    text = re.sub(r"//[^\n]*", " ", raw)
    text = re.sub(r"/\*.*?\*/", " \x00 ", text, flags=re.S)
    text = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
    lines: list[str] = []
    depth, statement = 0, ""
    for char in text:
        if char not in "{;}\x00":
            statement += char
            continue
        words = " ".join(statement.split())
        if char == "{":
            lines.append("  " * depth + (words + " {").strip())
            depth += 1
        elif char == ";":
            lines.append("  " * depth + words + ";")
        elif char == "\x00":
            lines.append("  " * depth + (words + " /*…*/").strip())
        else:
            if words:
                lines.append("  " * depth + words)
            depth -= 1
            assert depth >= 0, "a stray closing brace"
        statement = ""
    assert depth == 0 and not statement.strip(), "the braces of the package balance"
    return lines


def test_the_code_of_the_package_is_pinned_whole_as_its_skeleton() -> None:
    """Every declaration at its own brace depth, as its whole normalized text up to its { or ;: a member, a relation,
    a modifier or a body kind that the design does not hold changes a line. Every doc is pinned by its text in
    test_each_doc_of_the_package_states_its_text_of_record."""
    raw = SLICE.read_text(encoding="utf-8")
    skeleton = _skeleton(raw)
    for number, (expected, found) in enumerate(zip(SKELETON, skeleton), 1):
        assert found == expected, f"skeleton line {number}"
    assert len(skeleton) == len(SKELETON)
    assert re.findall(r"//[^\n]*", raw) == [], "the package carries no line note"


def test_the_package_holds_no_flow_bind_interface_message_succession_or_satisfy() -> None:
    """Read over the whole comment-stripped file, at every nesting level."""
    found = BANNED_FORMS.findall(_code(SLICE))
    assert not found, found


def test_each_doc_of_the_package_states_its_text_of_record() -> None:
    """Every doc and comment of the package, the header among them, whole and in order: a text that changes, moves,
    appears or goes changes the list. Each declaration that owns a doc at the package level is declared once."""
    found = _doc_texts(SLICE.read_text(encoding="utf-8"))
    assert len({owner for owner, _ in found}) == len(found), "each comment has an owner of its own"
    assert [owner for owner, _ in found] == [owner for owner, _ in DOC_TEXTS], "every doc, in order"
    for (owner, text), (_, expected) in zip(found, DOC_TEXTS):
        assert text == expected, owner
    code = " ".join(_code(SLICE).split())
    for owner, _ in DOC_TEXTS:
        if owner not in ("header", "package") and " / " not in owner and not owner.startswith("comment in "):
            assert code.count(f"{owner} {{") == 1, owner
