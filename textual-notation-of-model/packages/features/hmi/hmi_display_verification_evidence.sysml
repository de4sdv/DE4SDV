/*
 * DE4SDV HMI display verification and evidence model slice.
 *
 * INC-HMI-001, phase 10, first slice: the verification cases. Each case
 * verifies one requirement of DE4SDV_HmiDisplayNeedsRequirements, checks the
 * success criteria that the requirement states and adds no criterion of its
 * own, and binds the subject of its requirement to the realization of the HMI
 * display in the configured product HMI-CONFIG-001 (phase 9). One case per
 * requirement, ten cases, VC-HMI-001 to VC-HMI-010. Nine are tests that read
 * runs of the scenarios among SC-HMI-001 to SC-HMI-007 that their criteria
 * name; VC-HMI-009 is the inspection of the realization that phase 8 records,
 * which REQ-HMI-009 asks for, and reads no run.
 *
 * The five choices of this slice are the owner decision of 2026-11-26, as
 * INC-DRIVING-002 took them: one case per requirement; an outcome vocabulary
 * and a verdict map of the increment's own, with the six literals of
 * INC-DRIVING-002; the claims, their arguments and the counter-claims now, the
 * counter-claims from the non-claims of the framing; one evidence record per
 * run, read by every case of that run; and the test environment as a gap that
 * continues the gaps of phase 8 until the readiness probes fix its host and its
 * topology.
 *
 * No case has started. No evidence record exists, and each requirement keeps
 * the verification status NotStarted. The doc of each case usage states the
 * scenarios that the case reads. The System 2 test environment is the framing's
 * hmiDisplayVerificationEnvironment; the readiness questions that phase 8
 * leaves open continue as GAP-HMI-005 until the probes fix its host and its
 * topology. The validation of the needs stays planned in phase 4 (SC-HMI-008 to
 * SC-HMI-013). This slice adds no validation case.
 *
 * Where the requirements leave a reading to the cases, the cases read them so.
 * A run that is missing, or whose record is partial, gives
 * inconclusiveMissingEvidence, never pass. While the tolerance of a drawn
 * position is not set (GAP-HMI-003), VC-HMI-001 gives
 * inconclusiveMissingEvidence for evidence that meets every other clause of its
 * criterion. The display with one changed build, image, sound file,
 * configuration file or start setting that the criterion of REQ-HMI-010 names
 * records its display identity outside a run, so that no criterion over each
 * run reads it. The scene that the cases read is the one that the context
 * stand-in of phase 8 publishes, since the candidate gives no scene at its
 * boundary (gapHmiSceneOutput).
 *
 * The outcome vocabulary and the verdict map are this increment's own, with the
 * six literals that INC-DRIVING-002 uses. The evidence record is one record per
 * run, read by every case of that run: it binds HMI-CONFIG-001 and the receipt
 * digest, the model revision, the run and its scenario, the display identity
 * record of REQ-HMI-010 and the engineer who hashes the named files again, the
 * candidate identity record of the driver-assistance increment, the two clock
 * spans, and the observations that phase 5 asks of System 2. The inspection of
 * REQ-HMI-009 keeps a record of its own. The claims of the increment are stated
 * now, one for each phase 1 concern whose question the cases answer, eight in
 * all, each with an argument that cites the planned cases that answer it. The
 * counter-claims restate the non-claims of the framing and of the open gaps,
 * each tied to the record that keeps it open. A claim stated before its
 * evidence is a claim to be proven, not a result. This slice makes no result,
 * evidence, acceptance, safety, compliance or certification claim.
 */
package DE4SDV_HmiDisplayVerificationEvidence {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_HmiDisplayNeedsRequirements::*;
  private import DE4SDV_HmiDisplayFraming::asmHmiDrivingBenchReuse;
  private import DE4SDV_HmiDisplayFraming::asmHmiRendererWithoutGraphicsCard;
  private import DE4SDV_HmiDisplayFraming::asmHmiSimulationStandsIn;
  private import DE4SDV_HmiDisplayFraming::gapHmiDisplayInProductLine;
  private import DE4SDV_HmiDisplayFraming::gapHmiRendererIntegration;
  private import DE4SDV_HmiDisplayFraming::gapHmiSceneOutput;
  private import DE4SDV_HmiDisplayFraming::gapHmiUpstreamContact;
  private import DE4SDV_HmiDisplayFraming::hmiDisplayQuestion;
  private import DE4SDV_HmiDisplayFraming::hmiDisplayVerdictConcern;
  private import DE4SDV_HmiDisplayFraming::hmiDisplayVerificationEnvironment;
  private import DE4SDV_HmiDisplayFraming::hmiOnRoadOperationOutOfScope;
  private import DE4SDV_HmiDisplayFraming::hmiPerceptionQualityOutOfScope;
  private import DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiBenchSpeedFeed;
  private import DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiDrawingToleranceUnset;
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  enum def HmiDisplayScenarioIdentity {
    doc /*
     * The scenario of a run, by its phase 2 identity, as the evidence record
     * names it. warningScenarios is SC-HMI-001, the warning scenarios of the
     * driver-assistance increment on the display; noReactionScenarios is
     * SC-HMI-002, its no-reaction scenarios on the display; sceneAppOut is
     * SC-HMI-003, the app that draws the scene is out; androidBoots is
     * SC-HMI-004, Android in the IVI VM boots; androidHangs is SC-HMI-005,
     * Android in the IVI VM hangs; androidRestarts is SC-HMI-006, Android in
     * the IVI VM restarts; warningRequestStops is SC-HMI-007, the warning
     * request stops reaching the display.
     */
    warningScenarios;
    noReactionScenarios;
    sceneAppOut;
    androidBoots;
    androidHangs;
    androidRestarts;
    warningRequestStops;
  }

  enum def HmiDisplayEvidenceOutcome {
    doc /*
     * The outcome of processing the evidence of a case against the success
     * criteria of its requirement. The six literals that INC-DRIVING-002 uses:
     * evidence that meets the criteria gives passBoundedVerification; evidence
     * that shows them not met gives failObservedBehavior; missing or partial
     * evidence gives inconclusiveMissingEvidence; a run that the test
     * environment could not perform gives blockedTargetRuntime; evidence that
     * cannot be read gives errorEvidence. passBoundedValidation is the outcome
     * of a validation, which no case of this slice performs.
     */
    passBoundedVerification;
    passBoundedValidation;
    failObservedBehavior;
    inconclusiveMissingEvidence;
    blockedTargetRuntime;
    errorEvidence;
  }

  calc def MapHmiDisplayEvidenceOutcomeToVerdict {
    in outcome : HmiDisplayEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == HmiDisplayEvidenceOutcome::passBoundedVerification? VerdictKind::pass
      else if outcome == HmiDisplayEvidenceOutcome::passBoundedValidation? VerdictKind::pass
      else if outcome == HmiDisplayEvidenceOutcome::failObservedBehavior? VerdictKind::fail
      else if outcome == HmiDisplayEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  item def RetainedHmiDisplayRunEvidence {
    doc /*
     * The evidence record of one run; every case that reads the run reads this
     * record. It binds HMI-CONFIG-001 as its configurationIdentity.
     * receiptSha256 is the SHA-256 of the receipt the run ran against, as
     * HMI-CONFIG-001 asks of the evidence that binds it; if it differs from the
     * receiptSha256 of HMI-CONFIG-001, the verdict holds for HMI-CONFIG-001
     * only if the configuration's own receipt record did not change, which the
     * pull request that rebinds the digest states. modelRevision is the Git
     * commit of the DE4SDV model the run evaluated.
     *
     * runIdentity names the run, one execution of the HMI display on one
     * scenario from its start to its end, and scenario names that scenario.
     * displayIdentityRecord names the record of the display identity that the
     * identity recording service makes before the first frame on the display
     * (REQ-HMI-010), and independentEngineerIdentity names the engineer who
     * hashes the named files again. candidateRecordIdentity names the candidate
     * identity record that the driver-assistance system records in the run
     * (REQ-DRIVING-044). simulationClockSpan and wallClockSpan are the two
     * clocks of the run, kept apart. retainedObservations names the records
     * that phase 5 asks of System 2 (hmiTestbedObligationsOfPhase5): each value
     * of each input as its source gives it, with its simulation time, and where
     * it reaches the HMI display, with the wall-clock time of its arrival; each
     * frame on the display and the start of each sound, with their wall-clock
     * times; and the files and the settings that the display identity names. It
     * also names the times of the outage in the IVI VM and of the stop of the
     * Eclipse S-CORE path that the fault injection of the run makes, which the
     * criteria of REQ-HMI-001 and REQ-HMI-006 to REQ-HMI-008 read.
     * claimBoundary states what the record proves and what it does not. A
     * missing or partial record gives inconclusive, never pass. No record
     * exists.
     */
    attribute configurationIdentity : ScalarValues::String;
    attribute receiptSha256 : ScalarValues::String;
    attribute modelRevision : ScalarValues::String;
    attribute runIdentity : ScalarValues::String;
    attribute scenario : HmiDisplayScenarioIdentity;
    attribute displayIdentityRecord : ScalarValues::String;
    attribute independentEngineerIdentity : ScalarValues::String;
    attribute candidateRecordIdentity : ScalarValues::String;
    attribute simulationClockSpan : ScalarValues::String;
    attribute wallClockSpan : ScalarValues::String;
    attribute retainedObservations : ScalarValues::String;
    attribute claimBoundary : ScalarValues::String;
  }

  item def RetainedHmiDisplayRealizationInspection {
    doc /*
     * The evidence record of the inspection of REQ-HMI-009, which reads the
     * realization and no run. It binds HMI-CONFIG-001 and its receipt as the
     * run record does. modelRevision is the Git commit of the DE4SDV model
     * whose phase 8 realization the inspection read. inspectedRealization names
     * what it read: HmiDisplayPhysicalSystem with its parts and its
     * connections, the allocations of phase 8, and the comment
     * phase8WarningPresentationSettled, by which the IVI VM runs no other
     * warning presentation in the display's runs. inspectorIdentity names who
     * made the inspection. claimBoundary states what the inspection proves and
     * what it does not. A missing or partial record gives inconclusive, never
     * pass. No record exists.
     */
    attribute configurationIdentity : ScalarValues::String;
    attribute receiptSha256 : ScalarValues::String;
    attribute modelRevision : ScalarValues::String;
    attribute inspectedRealization : ScalarValues::String;
    attribute inspectorIdentity : ScalarValues::String;
    attribute claimBoundary : ScalarValues::String;
  }

  part def HmiDisplayVerificationBench {
    doc /*
     * The bench of the verification cases of INC-HMI-001. System 1 is the
     * configured product HMI-CONFIG-001, which the bench refers to and does not
     * own. displayRealization is its realization of the HMI display, the system
     * of interest: the subject that each verified requirement binds. The System
     * 2 test environment is the framing's hmiDisplayVerificationEnvironment,
     * whose readiness stays open as GAP-HMI-005. The bench is not a product
     * selection.
     */
    ref part system1ConfiguredProduct :> DE4SDV_HmiDisplayVariabilityConfiguration::configuredProduct;
    ref part displayRealization :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem
      = system1ConfiguredProduct.displayRealization;
  }

  part hmiDisplayVerificationBench : HmiDisplayVerificationBench;

  part <'GAP-HMI-005'> gapHmiVerificationEnvironmentOpen : IncrementGap {
    doc /*
     * Open: the System 2 test environment is not shown to run the cases. It
     * continues the readiness questions that phase 8 leaves open until the
     * probes fix its host and its topology: whether the high availability
     * renderer draws on the guest host with the SDV Core, IVI and SDV Media VMs
     * running on it together, with the heartbeats, the composition and the
     * renderer's judging of the scene by the term current
     * (asmHmiRendererWithoutGraphicsCard); which transport carries the
     * renderer's topics between the VMs, whether the bench composes the two
     * planes, which IVI image runs the app, and how the sound is captured
     * (gapHmiRendererIntegration); which element of the bench feeds the
     * simulator's speed into the vehicle data of the SDV Core VM (GAP-HMI-002);
     * and what stands in for the source of the scene, and how, which is decided
     * with the scene's way out of the candidate (gapHmiSceneOutput). The
     * records, the faults and the lengths of the runs that the criteria ask of
     * System 2 are those that phase 5 states (hmiTestbedObligationsOfPhase5).
     * Each probe runs only on the owner's word, and nothing of the next slice
     * is built before the probes are read. The next slice fills the evidence
     * record, plans the runs and closes this gap.
     */
  }

  /* Each case collects the evidence record of its runs, or of its inspection
   * (collectData). processData compares the record with the success criteria of
   * the verified requirement and gives a HmiDisplayEvidenceOutcome.
   * evaluateData maps the outcome to a VerdictKind with
   * MapHmiDisplayEvidenceOutcomeToVerdict. Each objective binds the subject of
   * its requirement to the realization of the HMI display in HMI-CONFIG-001. A
   * verify is a planned verification objective, not a verdict.
   */

  verification def ShowTheSceneAsGivenVerification {
    doc /*
     * Test of REQ-HMI-001. collectData retains the record of each run of
     * SC-HMI-001 to SC-HMI-007: each scene with its time as its source gives it
     * and the wall-clock time at which it reaches the HMI display, the outages
     * in the IVI VM, and each frame on the display with its wall-clock time.
     * processData checks that each of SC-HMI-001 to SC-HMI-007 has at least one
     * run, each run of SC-HMI-004 and SC-HMI-006 has the end of its outage in
     * the IVI VM before its own end, and in each run every scene that reaches
     * the HMI display outside an outage in the IVI VM, or a newer scene, is on
     * the display less than 0.1 s of wall-clock time after it arrives, with its
     * lane points, its path and each of its objects with its level, as many
     * objects as the scene gives and at the positions that it gives, read
     * within the drawing tolerance that phase 8 states; and that no frame on
     * the display shows a lane, a path or an object that no scene of the run
     * gives, from the simulator's record of the scene or from an estimate of
     * the display's own. Every clause met gives passBoundedVerification; a
     * clause not met gives failObservedBehavior. A run that is missing, or
     * whose record is partial, gives inconclusiveMissingEvidence, never pass.
     * While the tolerance of a drawn position is not set (GAP-HMI-003),
     * evidence that meets every other clause gives inconclusiveMissingEvidence,
     * never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective showTheSceneAsGivenObjective {
      verify reqShowTheSceneAsGiven { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def MarkTheObjectTheSystemActsOnVerification {
    doc /*
     * Test of REQ-HMI-002. collectData retains the record of each run of
     * SC-HMI-001 to SC-HMI-007: each scene with the object that the system acts
     * on, its distance and the speed of the closest object, as its source gives
     * them, and each frame on the display with its wall-clock time. processData
     * checks that each of SC-HMI-001 and SC-HMI-002 has at least one run whose
     * scenes give an object that the system acts on, and in each run of
     * SC-HMI-001 to SC-HMI-007 each frame on the display that shows a scene
     * shows, as an element of its own, the object that the system acts on of
     * that scene when it has one and no such element when it has none, the
     * fixed distance of 150 m included; marks none of the marks that the
     * criterion of REQ-HMI-002 excludes as that object; and shows its distance
     * as the distance of the scene rounded to the whole metre and its speed as
     * the speed of the closest object of the scene times 3.6, rounded to the
     * whole km/h, with its sign. Every clause met gives
     * passBoundedVerification; a clause not met gives failObservedBehavior. A
     * run that is missing, or whose record is partial, gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective markTheObjectTheSystemActsOnObjective {
      verify reqMarkTheObjectTheSystemActsOn { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def ShowTheVehicleSpeedVerification {
    doc /*
     * Test of REQ-HMI-003. collectData retains the record of each run of
     * SC-HMI-001, SC-HMI-002 and SC-HMI-007: each vehicle speed with its sample
     * time as its source gives it and the wall-clock time at which it reaches
     * the HMI display, and each frame on the display with its wall-clock time.
     * processData checks that each of SC-HMI-001, SC-HMI-002 and SC-HMI-007 has
     * at least one run, and in each of their runs each speed on a frame on the
     * display is the value of a vehicle speed of the run that has reached the
     * HMI display, rounded to the whole km/h; each vehicle speed that reaches
     * the HMI display, or a newer one, is on the display less than 0.1 s of
     * wall-clock time after it arrives; and no frame shows a speed from another
     * source, a fixed value of the display's own, or a speed before the first
     * vehicle speed of the run reaches the HMI display. Every clause met gives
     * passBoundedVerification; a clause not met gives failObservedBehavior. A
     * run that is missing, or whose record is partial, gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective showTheVehicleSpeedObjective {
      verify reqShowTheVehicleSpeed { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def CollisionWarningWhileRequestedVerification {
    doc /*
     * Test of REQ-HMI-004. collectData retains the record of each run of
     * SC-HMI-001, SC-HMI-002 and SC-HMI-007: each event of the warning request
     * with its issue time as its source gives it and the wall-clock time at
     * which it reaches the HMI display, each frame on the display and the start
     * and the end of each sound, with their wall-clock times. processData
     * checks that each run of SC-HMI-001 has at least one start of a request
     * that reaches the HMI display, and in each run of SC-HMI-001, SC-HMI-002
     * and SC-HMI-007 each mode of the collision warning is on from less than
     * 0.1 s of wall-clock time after each start of a request reaches the HMI
     * display until less than 0.1 s of wall-clock time after the warning
     * request ends its asking, and at no other time, with no recording or
     * overlay in place of either mode. Every clause met gives
     * passBoundedVerification; a clause not met gives failObservedBehavior. A
     * run that is missing, or whose record is partial, gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective collisionWarningWhileRequestedObjective {
      verify reqCollisionWarningWhileRequested { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StartEachWarningModeWithinLimitVerification {
    doc /*
     * Test of REQ-HMI-005. collectData retains the record of each run of
     * SC-HMI-001 and SC-HMI-002: each event of the warning request with its
     * issue time as its source gives it and the wall-clock time at which it
     * reaches the HMI display, each frame on the display and the start of each
     * sound, with their wall-clock times. processData checks that each run of
     * SC-HMI-001 has at least one start of a request that reaches the HMI
     * display, and for each start of a request that reaches the HMI display in
     * a run of SC-HMI-001 or SC-HMI-002, the first frame on the display with
     * the warning and the start of the sound each come less than 0.1 s of
     * wall-clock time after it arrives, with no recording or overlay in place
     * of either mode. Every clause met gives passBoundedVerification; a clause
     * not met gives failObservedBehavior. A run that is missing, or whose
     * record is partial, gives inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective startEachWarningModeWithinLimitObjective {
      verify reqStartEachWarningModeWithinLimit { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def ShowOutdatedElementsAsOutdatedVerification {
    doc /*
     * Test of REQ-HMI-006. collectData retains the record of each run of
     * SC-HMI-001 to SC-HMI-007: each value of each input with its time as its
     * source gives it and the wall-clock time at which it reaches the HMI
     * display, the outages in the IVI VM and the stop of the Eclipse S-CORE
     * path, and each frame on the display with its wall-clock time. processData
     * checks that each of SC-HMI-001 to SC-HMI-007 has at least one run, each
     * run of SC-HMI-003 to SC-HMI-006 has its outage in the IVI VM and each run
     * of SC-HMI-007 the stop of the Eclipse S-CORE path, and in each run each
     * frame on the display shows each element as outdated, in the form that
     * phase 8 states for it, from less than 0.1 s of wall-clock time after the
     * element turns outdated until less than 0.1 s of wall-clock time after it
     * turns current again, and as current at every other time; an element is
     * outdated from the start of the run until a first current value of its
     * input reaches the HMI display. Every clause met gives
     * passBoundedVerification; a clause not met gives failObservedBehavior. A
     * run that is missing, or whose record is partial, gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective showOutdatedElementsAsOutdatedObjective {
      verify reqShowOutdatedElementsAsOutdated { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def ShowWarningUnavailableWhileRequestOutdatedVerification {
    doc /*
     * Test of REQ-HMI-007. collectData retains the record of each run of
     * SC-HMI-001 to SC-HMI-007: each event of the warning request with its
     * issue time as its source gives it and the wall-clock time at which it
     * reaches the HMI display, the stop of the Eclipse S-CORE path, the end of
     * the run, and each frame on the display with its wall-clock time.
     * processData checks that each of SC-HMI-001 to SC-HMI-007 has at least one
     * run, each run of SC-HMI-007 has the stop of the Eclipse S-CORE path at
     * least 0.3 s of wall-clock time before its end, and in each run the
     * display shows that the collision warning is unavailable from less than
     * 0.1 s of wall-clock time after the warning request turns outdated until
     * less than 0.1 s of wall-clock time after it turns current again, and at
     * no other time, so that the warning shows as available again only once an
     * event of the warning request is current. Every clause met gives
     * passBoundedVerification; a clause not met gives failObservedBehavior. A
     * run that is missing, or whose record is partial, gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective showWarningUnavailableWhileRequestOutdatedObjective {
      verify reqShowWarningUnavailableWhileRequestOutdated { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def SpeedAndWarningThroughOutagesVerification {
    doc /*
     * Test of REQ-HMI-008. collectData retains the record of each run of
     * SC-HMI-003 to SC-HMI-006: each vehicle speed and each event of the
     * warning request with its time as its source gives it and the wall-clock
     * time at which it reaches the HMI display, the outage in the IVI VM, each
     * frame on the display and the start and the end of each sound, with their
     * wall-clock times. processData checks that each of SC-HMI-003 to
     * SC-HMI-006 has at least one run, each run has its outage in the IVI VM
     * with at least one start of a request reaching the HMI display during it,
     * and throughout the outage of each run each frame on the display and each
     * mode of the collision warning meet what the criteria of REQ-HMI-003,
     * REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 ask of them. Every clause met
     * gives passBoundedVerification; a clause not met gives
     * failObservedBehavior. A run that is missing, or whose record is partial,
     * gives inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective speedAndWarningThroughOutagesObjective {
      verify reqSpeedAndWarningThroughOutages { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def RendererSplitAndInputPathsVerification {
    doc /*
     * Inspection of REQ-HMI-009. collectData retains the
     * RetainedHmiDisplayRealizationInspection record: the realization that
     * phase 8 records, at the model revision that the record names. processData
     * checks that the inspection of the realization that phase 8 records shows
     * the vehicle speed, the collision warning on the display and its sound in
     * the high availability renderer in an SDV Media VM, the scene in an app in
     * the IVI VM, and for each input the elements that carry it from the SDV
     * Core VM to the renderer or to the app, all inside the boundary of the HMI
     * display, with no other element drawing the vehicle speed or the collision
     * warning. An inspection that finds each of these gives
     * passBoundedVerification; one that finds an element or a path missing,
     * outside the boundary of the HMI display, or another element drawing the
     * vehicle speed or the collision warning gives failObservedBehavior. A
     * record that is missing or partial gives inconclusiveMissingEvidence,
     * never pass. The case reads no run.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective rendererSplitAndInputPathsObjective {
      verify reqRendererSplitAndInputPaths { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = inspect; }
      out item retainedEvidence : RetainedHmiDisplayRealizationInspection;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRealizationInspection = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def RecordDisplayIdentityVerification {
    doc /*
     * Test of REQ-HMI-010. collectData retains the record of each run of
     * SC-HMI-001 to SC-HMI-007: the record of the display identity with its
     * wall-clock time, the wall-clock time of the first frame on the display,
     * and the values that another engineer obtains who hashes the named files;
     * and, outside the runs, the display identity that the identity recording
     * service records for a display with one changed build, image, sound file,
     * configuration file or start setting. processData checks that every run of
     * SC-HMI-001 to SC-HMI-007 has the record of its display identity before
     * its first frame on the display; that another engineer who hashes the
     * named files obtains the recorded values; and that a display with one
     * changed build, image, sound file, configuration file or start setting
     * records a different display identity. Every clause met gives
     * passBoundedVerification; a clause not met gives failObservedBehavior. A
     * run that is missing, or whose record is partial, gives
     * inconclusiveMissingEvidence, never pass. The display identity is the one
     * that the term of the requirements names since the identity-term amendment
     * of phase 10.
     */
    subject verifiedBench : HmiDisplayVerificationBench;
    objective recordDisplayIdentityObjective {
      verify reqRecordDisplayIdentity { subject hmiDisplay = verifiedBench.displayRealization; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedHmiDisplayRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedHmiDisplayRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : HmiDisplayEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : HmiDisplayEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapHmiDisplayEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification <'VC-HMI-001'> showTheSceneAsGivenVerification : ShowTheSceneAsGivenVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003
     * (HmiDisplayScenarioIdentity::sceneAppOut), SC-HMI-004
     * (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005
     * (HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006
     * (HmiDisplayScenarioIdentity::androidRestarts) and SC-HMI-007
     * (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-002'> markTheObjectTheSystemActsOnVerification : MarkTheObjectTheSystemActsOnVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003
     * (HmiDisplayScenarioIdentity::sceneAppOut), SC-HMI-004
     * (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005
     * (HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006
     * (HmiDisplayScenarioIdentity::androidRestarts) and SC-HMI-007
     * (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-003'> showTheVehicleSpeedVerification : ShowTheVehicleSpeedVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios) and SC-HMI-007
     * (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-004'> collisionWarningWhileRequestedVerification : CollisionWarningWhileRequestedVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios) and SC-HMI-007
     * (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-005'> startEachWarningModeWithinLimitVerification
    : StartEachWarningModeWithinLimitVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios) and SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-006'> showOutdatedElementsAsOutdatedVerification : ShowOutdatedElementsAsOutdatedVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003
     * (HmiDisplayScenarioIdentity::sceneAppOut), SC-HMI-004
     * (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005
     * (HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006
     * (HmiDisplayScenarioIdentity::androidRestarts) and SC-HMI-007
     * (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-007'> showWarningUnavailableWhileRequestOutdatedVerification
    : ShowWarningUnavailableWhileRequestOutdatedVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003
     * (HmiDisplayScenarioIdentity::sceneAppOut), SC-HMI-004
     * (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005
     * (HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006
     * (HmiDisplayScenarioIdentity::androidRestarts) and SC-HMI-007
     * (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-008'> speedAndWarningThroughOutagesVerification : SpeedAndWarningThroughOutagesVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-003
     * (HmiDisplayScenarioIdentity::sceneAppOut), SC-HMI-004
     * (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005
     * (HmiDisplayScenarioIdentity::androidHangs) and SC-HMI-006
     * (HmiDisplayScenarioIdentity::androidRestarts). Runs: the runs of these
     * scenarios that the criterion of its requirement names; the next slice
     * plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-009'> rendererSplitAndInputPathsVerification : RendererSplitAndInputPathsVerification {
    doc /*
     * Not started. Scenarios: none; the case reads the realization that phase 8
     * records, at the model revision that its record names, and no run.
     */
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  verification <'VC-HMI-010'> recordDisplayIdentityVerification : RecordDisplayIdentityVerification {
    doc /*
     * Not started. Scenarios: SC-HMI-001
     * (HmiDisplayScenarioIdentity::warningScenarios), SC-HMI-002
     * (HmiDisplayScenarioIdentity::noReactionScenarios), SC-HMI-003
     * (HmiDisplayScenarioIdentity::sceneAppOut), SC-HMI-004
     * (HmiDisplayScenarioIdentity::androidBoots), SC-HMI-005
     * (HmiDisplayScenarioIdentity::androidHangs), SC-HMI-006
     * (HmiDisplayScenarioIdentity::androidRestarts) and SC-HMI-007
     * (HmiDisplayScenarioIdentity::warningRequestStops). Runs: the runs of
     * these scenarios that the criterion of its requirement names; the next
     * slice plans them. Test environment: open (GAP-HMI-005).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> hmiDisplayVerificationBench;
  }

  part hmiDisplayVerificationSystem {
    doc /*
     * The verification system performs the cases: the System 2 performer, the
     * framing's hmiDisplayVerificationEnvironment, whose readiness GAP-HMI-005
     * leaves open.
     */
    perform showTheSceneAsGivenVerification;
    perform markTheObjectTheSystemActsOnVerification;
    perform showTheVehicleSpeedVerification;
    perform collisionWarningWhileRequestedVerification;
    perform startEachWarningModeWithinLimitVerification;
    perform showOutdatedElementsAsOutdatedVerification;
    perform showWarningUnavailableWhileRequestOutdatedVerification;
    perform speedAndWarningThroughOutagesVerification;
    perform rendererSplitAndInputPathsVerification;
    perform recordDisplayIdentityVerification;
  }

  dependency hmiVerificationSystemIsTheVerificationEnvironment
    from hmiDisplayVerificationSystem to hmiDisplayVerificationEnvironment;
  dependency hmiEnvironmentGapOnVerificationSystem
    from gapHmiVerificationEnvironmentOpen to hmiDisplayVerificationSystem;
  dependency hmiEnvironmentGapContinuesRendererIntegration
    from gapHmiVerificationEnvironmentOpen to gapHmiRendererIntegration;
  dependency hmiEnvironmentGapContinuesRendererAssumption
    from gapHmiVerificationEnvironmentOpen to asmHmiRendererWithoutGraphicsCard;
  dependency hmiEnvironmentGapContinuesBenchSpeedFeed
    from gapHmiVerificationEnvironmentOpen to gapHmiBenchSpeedFeed;

  requirement def HmiDisplayClaim :> AssuranceClaim;

  requirement def HmiDisplayArgument :> AssuranceArgument;

  requirement def HmiDisplayCounterClaim :> AssuranceCounterClaim;

  requirement hmiDisplayInputsClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiDisplayInputsConcern. For HMI-CONFIG-001 in the simulated
     * configuration, in the runs of SC-HMI-001 to SC-HMI-007 that the criterion
     * of REQ-HMI-001 names, the HMI display shows each scene that reaches it
     * outside an outage in the IVI VM, or a newer scene, as its source gives
     * it, with its lane points, its path and each of its objects with its
     * level, and no lane, path or object that no scene of the run gives. A
     * claim to be proven: no case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the retained records of the runs that its argument
       * cites, bound to HMI-CONFIG-001 and its receipt; it excludes the
       * simulator's own record of the scene and an estimate of the display's
       * own as a source of the scene, and how well the candidate perceives.
       */
    }
  }

  requirement hmiContentVarianceClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiContentVarianceConcern. For HMI-CONFIG-001, the scene that the
     * HMI display shows in the runs that the criterion of REQ-HMI-001 names is
     * the scene of the one source of the scene in that configuration, as that
     * source gives it, and no scene of another driving application; while the
     * candidate gives no scene, that source is the context stand-in of phase 8
     * (gapHmiSceneOutput). A claim to be proven: no case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the retained records of the runs that its argument
       * cites, bound to HMI-CONFIG-001 and its receipt; it excludes the scenes
       * of the other driving applications of the product line, and which
       * content becomes common to the member products, which is for the
       * lifecycle decision.
       */
    }
  }

  requirement hmiWarningSequenceClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiWarningSequenceConcern. For HMI-CONFIG-001 in the simulated
     * configuration, in the runs that the criteria of REQ-HMI-004 and
     * REQ-HMI-005 name, each mode of the collision warning is on from less than
     * 0.1 s of wall-clock time after each start of a request reaches the HMI
     * display until less than 0.1 s of wall-clock time after the warning
     * request ends its asking, and at no other time, and the first frame with
     * the warning and the start of the sound each come less than 0.1 s of
     * wall-clock time after each start of a request reaches the HMI display. A
     * claim to be proven: no case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the retained records of the runs that its argument
       * cites, bound to HMI-CONFIG-001 and its receipt; it excludes the time
       * that the driver-assistance increment takes to its warning request, and
       * whether a driver perceives the warning.
       */
    }
  }

  requirement hmiContentCurrencyClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiContentCurrencyConcern. For HMI-CONFIG-001 in the simulated
     * configuration, in the runs of SC-HMI-001 to SC-HMI-007 that the criteria
     * of REQ-HMI-006 and REQ-HMI-007 name, the HMI display shows each element
     * as outdated, in the form that phase 8 states for it, while it is outdated
     * and as current at every other time, and shows that the collision warning
     * is unavailable while the warning request is outdated and at no other
     * time, each within 0.1 s of wall-clock time of the change. A claim to be
     * proven: no case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the retained records of the runs that its argument
       * cites, bound to HMI-CONFIG-001 and its receipt; it excludes the visual
       * design of an outdated element (hmiHumanFactorsOutOfScope).
       */
    }
  }

  requirement hmiAndroidOutageClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiAndroidOutageConcern. For HMI-CONFIG-001 in the simulated
     * configuration, throughout the outage in the IVI VM of each run of
     * SC-HMI-003 to SC-HMI-006 that the criterion of REQ-HMI-008 names, each
     * frame on the display and each mode of the collision warning meet what the
     * criteria of REQ-HMI-003, REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 ask of
     * them. A claim to be proven: no case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the retained records of the runs that its argument
       * cites, bound to HMI-CONFIG-001 and its receipt; it excludes any safety
       * argument.
       */
    }
  }

  requirement hmiRendererAllocationClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiRendererAllocationConcern. The realization that phase 8
     * records, at the model revision that the record of the inspection names,
     * draws the vehicle speed, the collision warning on the display and its
     * sound in the high availability renderer in an SDV Media VM and the scene
     * in an app in the IVI VM, with no other element drawing the vehicle speed
     * or the collision warning, as the criterion of REQ-HMI-009 asks. A claim
     * to be proven: no case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the record of the inspection that its argument
       * cites, bound to HMI-CONFIG-001 and its receipt; it excludes a run, and
       * any safety approval of an element that the renderer draws.
       */
    }
  }

  requirement hmiRendererPathClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiRendererPathConcern. The realization that phase 8 records, at
     * the model revision that the record of the inspection names, places for
     * each input of the HMI display the elements that carry it from the SDV
     * Core VM to the renderer or to the app, all inside the boundary of the HMI
     * display, as the criterion of REQ-HMI-009 asks. A claim to be proven: no
     * case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the record of the inspection that its argument
       * cites, bound to HMI-CONFIG-001 and its receipt; it excludes an
       * observation of the renderer's path on the bench
       * (gapHmiRendererIntegration).
       */
    }
  }

  requirement hmiDisplayVerdictClaim : HmiDisplayClaim {
    doc /*
     * Answers hmiDisplayVerdictConcern. For HMI-CONFIG-001 in the simulated
     * configuration, the HMI display meets the success criteria of REQ-HMI-001
     * to REQ-HMI-008 and of REQ-HMI-010 in the runs of SC-HMI-001 to SC-HMI-007
     * that those criteria name, and the realization that phase 8 records meets
     * those of REQ-HMI-009. Each verdict is a pass or a fail for its
     * requirement and its scenarios, bound to the candidate revision, the
     * display identity and HMI-CONFIG-001 with its receipt, and holds what the
     * display shows against what the candidate gives and when. A fail stays a
     * recorded result. A claim to be proven: no case has started.
     */
    subject claimSubject : HmiDisplayVerificationBench;
    require constraint {
      doc /*
       * The claim requires the retained records of the runs and the record of
       * the inspection that its argument cites, bound to HMI-CONFIG-001 and its
       * receipt; it excludes a recording of a display that looks right, the
       * vehicle and the road that the simulation stands in for, and the results
       * of the bench of the driver-assistance increment.
       */
    }
  }

  requirement hmiDisplayInputsArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirement that VC-HMI-001 verifies,
     * from the retained record of its runs; the argument holds once every cited
     * case has a pass verdict and fails with any fail; an inconclusive or error
     * verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiContentVarianceArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirement that VC-HMI-001 verifies,
     * from the retained record of its runs; the argument holds once every cited
     * case has a pass verdict and fails with any fail; an inconclusive or error
     * verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiWarningSequenceArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-HMI-004 and
     * VC-HMI-005 verify, each from the retained records of its runs; the
     * argument holds once every cited case has a pass verdict and fails with
     * any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiContentCurrencyArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-HMI-006 and
     * VC-HMI-007 verify, each from the retained records of its runs; the
     * argument holds once every cited case has a pass verdict and fails with
     * any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiAndroidOutageArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirement that VC-HMI-008 verifies,
     * from the retained record of its runs; the argument holds once every cited
     * case has a pass verdict and fails with any fail; an inconclusive or error
     * verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiRendererAllocationArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirement that VC-HMI-009 verifies,
     * from the retained record of its inspection; the argument holds once every
     * cited case has a pass verdict and fails with any fail; an inconclusive or
     * error verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiRendererPathArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirement that VC-HMI-009 verifies,
     * from the retained record of its inspection; the argument holds once every
     * cited case has a pass verdict and fails with any fail; an inconclusive or
     * error verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiDisplayVerdictArgument : HmiDisplayArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-HMI-001 to
     * VC-HMI-010 verify, each from the retained records of its runs or of its
     * inspection; the argument holds once every cited case has a pass verdict
     * and fails with any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimRecordingIsNoVerdict : HmiDisplayCounterClaim {
    doc /*
     * A recording of a display that looks right is no verdict: a verdict holds
     * what the display shows against what the candidate gives and when, from
     * the retained records of its runs (hmiDisplayQuestion).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimSimulatedConfigurationOnly : HmiDisplayCounterClaim {
    doc /*
     * The simulated road, vehicle and targets, and the vehicle speed that the
     * simulator gives, stand in for the road, the vehicle and its speed signal;
     * a verdict holds for that simulated configuration only
     * (asmHmiSimulationStandsIn).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimDrivingBenchResultsNoEvidence : HmiDisplayCounterClaim {
    doc /*
     * The bench of the driver-assistance increment, its candidate build and its
     * path into the AAOS SDV are reuse candidates; their results for that
     * increment are no evidence for this one, and each case reads only the
     * records of its own runs (asmHmiDrivingBenchReuse).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimSceneFromAStandIn : HmiDisplayCounterClaim {
    doc /*
     * The candidate gives no scene at its boundary, so the scene that the cases
     * read is the one that a context stand-in publishes
     * (phase8SceneOutputHeld); a verdict of REQ-HMI-001 or REQ-HMI-002 holds
     * for the scenes of that stand-in, not for an output of the candidate
     * (gapHmiSceneOutput).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimPerceptionNotJudged : HmiDisplayCounterClaim {
    doc /*
     * The display shows what the candidate gives, right or wrong; no case
     * judges how well the candidate perceives, and a pass says nothing of how
     * far its positions and its distances are from the simulator's
     * (hmiPerceptionQualityOutOfScope).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimNoComplianceOrApproval : HmiDisplayCounterClaim {
    doc /*
     * No on-road, production-readiness, safety-approval, compliance,
     * type-approval or certification claim, for the display or for the
     * renderer's monitor (hmiOnRoadOperationOutOfScope).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimNoMemberProduct : HmiDisplayCounterClaim {
    doc /*
     * HMI-CONFIG-001 is no member product; a case with a pass verdict makes
     * none and changes no scope decision, and what the display shows in each
     * member stays open (gapHmiDisplayInProductLine).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimNoUpstreamEndorsement : HmiDisplayCounterClaim {
    doc /*
     * No upstream contact, endorsement or rights clearance is asserted: the
     * changes to the projects of the renderer and of the candidate stay gaps,
     * and a result about a project is shown to its maintainers before it is
     * published (gapHmiUpstreamContact).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimDrawingToleranceUnset : HmiDisplayCounterClaim {
    doc /*
     * The tolerance of a drawn position is not set, so VC-HMI-001 gives no pass
     * while the gap is open, whatever its frames show (GAP-HMI-003).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  requirement hmiCounterClaimEnvironmentOpenNoVerdict : HmiDisplayCounterClaim {
    doc /*
     * No case has started and no evidence record exists; the test environment
     * is open; every claim of this slice is a claim to be proven (GAP-HMI-005).
     */
    subject bench : HmiDisplayVerificationBench;
  }

  dependency claimSupportedByHmiDisplayInputsArgument
    from hmiDisplayInputsArgument to hmiDisplayInputsClaim;
  dependency claimSupportedByHmiContentVarianceArgument
    from hmiContentVarianceArgument to hmiContentVarianceClaim;
  dependency claimSupportedByHmiWarningSequenceArgument
    from hmiWarningSequenceArgument to hmiWarningSequenceClaim;
  dependency claimSupportedByHmiContentCurrencyArgument
    from hmiContentCurrencyArgument to hmiContentCurrencyClaim;
  dependency claimSupportedByHmiAndroidOutageArgument
    from hmiAndroidOutageArgument to hmiAndroidOutageClaim;
  dependency claimSupportedByHmiRendererAllocationArgument
    from hmiRendererAllocationArgument to hmiRendererAllocationClaim;
  dependency claimSupportedByHmiRendererPathArgument
    from hmiRendererPathArgument to hmiRendererPathClaim;
  dependency claimSupportedByHmiDisplayVerdictArgument
    from hmiDisplayVerdictArgument to hmiDisplayVerdictClaim;
  dependency hmiDisplayInputsArgumentCitesCases
    from hmiDisplayInputsArgument
    to showTheSceneAsGivenVerification;
  dependency hmiContentVarianceArgumentCitesCases
    from hmiContentVarianceArgument
    to showTheSceneAsGivenVerification;
  dependency hmiWarningSequenceArgumentCitesCases
    from hmiWarningSequenceArgument
    to collisionWarningWhileRequestedVerification,
      startEachWarningModeWithinLimitVerification;
  dependency hmiContentCurrencyArgumentCitesCases
    from hmiContentCurrencyArgument
    to showOutdatedElementsAsOutdatedVerification,
      showWarningUnavailableWhileRequestOutdatedVerification;
  dependency hmiAndroidOutageArgumentCitesCases
    from hmiAndroidOutageArgument
    to speedAndWarningThroughOutagesVerification;
  dependency hmiRendererAllocationArgumentCitesCases
    from hmiRendererAllocationArgument
    to rendererSplitAndInputPathsVerification;
  dependency hmiRendererPathArgumentCitesCases
    from hmiRendererPathArgument
    to rendererSplitAndInputPathsVerification;
  dependency hmiDisplayVerdictArgumentCitesCases
    from hmiDisplayVerdictArgument
    to showTheSceneAsGivenVerification,
      markTheObjectTheSystemActsOnVerification,
      showTheVehicleSpeedVerification,
      collisionWarningWhileRequestedVerification,
      startEachWarningModeWithinLimitVerification,
      showOutdatedElementsAsOutdatedVerification,
      showWarningUnavailableWhileRequestOutdatedVerification,
      speedAndWarningThroughOutagesVerification,
      rendererSplitAndInputPathsVerification,
      recordDisplayIdentityVerification;
  dependency hmiCounterClaimRecordingIsNoVerdictBoundTo
    from hmiCounterClaimRecordingIsNoVerdict to hmiDisplayQuestion;
  dependency hmiCounterClaimSimulatedConfigurationOnlyBoundTo
    from hmiCounterClaimSimulatedConfigurationOnly to asmHmiSimulationStandsIn;
  dependency hmiCounterClaimDrivingBenchResultsNoEvidenceBoundTo
    from hmiCounterClaimDrivingBenchResultsNoEvidence to asmHmiDrivingBenchReuse;
  dependency hmiCounterClaimSceneFromAStandInBoundTo
    from hmiCounterClaimSceneFromAStandIn to gapHmiSceneOutput;
  dependency hmiCounterClaimPerceptionNotJudgedBoundTo
    from hmiCounterClaimPerceptionNotJudged to hmiPerceptionQualityOutOfScope;
  dependency hmiCounterClaimNoComplianceOrApprovalBoundTo
    from hmiCounterClaimNoComplianceOrApproval to hmiOnRoadOperationOutOfScope;
  dependency hmiCounterClaimNoMemberProductBoundTo
    from hmiCounterClaimNoMemberProduct to gapHmiDisplayInProductLine;
  dependency hmiCounterClaimNoUpstreamEndorsementBoundTo
    from hmiCounterClaimNoUpstreamEndorsement to gapHmiUpstreamContact;
  dependency hmiCounterClaimDrawingToleranceUnsetBoundTo
    from hmiCounterClaimDrawingToleranceUnset to gapHmiDrawingToleranceUnset;
  dependency hmiCounterClaimEnvironmentOpenNoVerdictBoundTo
    from hmiCounterClaimEnvironmentOpenNoVerdict to gapHmiVerificationEnvironmentOpen;

  view hmiDisplayAssuranceView {
    viewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame hmiDisplayVerdictConcern;
    }
    doc /*
     * The assurance structure of the increment before any run: the eight
     * claims, the arguments that support them and the cases they cite, the ten
     * cases, the evidence record of a run and the record of the inspection, the
     * bench and the environment gap, and the ten counter-claims with the
     * records that keep them open, those records exposed beside them. It frames
     * the phase 1 concern hmiDisplayVerdictConcern, so that it is answered in
     * its domain.
     */
    expose hmiDisplayInputsClaim;
    expose hmiContentVarianceClaim;
    expose hmiWarningSequenceClaim;
    expose hmiContentCurrencyClaim;
    expose hmiAndroidOutageClaim;
    expose hmiRendererAllocationClaim;
    expose hmiRendererPathClaim;
    expose hmiDisplayVerdictClaim;
    expose hmiDisplayInputsArgument;
    expose hmiContentVarianceArgument;
    expose hmiWarningSequenceArgument;
    expose hmiContentCurrencyArgument;
    expose hmiAndroidOutageArgument;
    expose hmiRendererAllocationArgument;
    expose hmiRendererPathArgument;
    expose hmiDisplayVerdictArgument;
    expose hmiCounterClaimRecordingIsNoVerdict;
    expose hmiCounterClaimSimulatedConfigurationOnly;
    expose hmiCounterClaimDrivingBenchResultsNoEvidence;
    expose hmiCounterClaimSceneFromAStandIn;
    expose hmiCounterClaimPerceptionNotJudged;
    expose hmiCounterClaimNoComplianceOrApproval;
    expose hmiCounterClaimNoMemberProduct;
    expose hmiCounterClaimNoUpstreamEndorsement;
    expose hmiCounterClaimDrawingToleranceUnset;
    expose hmiCounterClaimEnvironmentOpenNoVerdict;
    expose showTheSceneAsGivenVerification;
    expose markTheObjectTheSystemActsOnVerification;
    expose showTheVehicleSpeedVerification;
    expose collisionWarningWhileRequestedVerification;
    expose startEachWarningModeWithinLimitVerification;
    expose showOutdatedElementsAsOutdatedVerification;
    expose showWarningUnavailableWhileRequestOutdatedVerification;
    expose speedAndWarningThroughOutagesVerification;
    expose rendererSplitAndInputPathsVerification;
    expose recordDisplayIdentityVerification;
    expose RetainedHmiDisplayRunEvidence;
    expose RetainedHmiDisplayRealizationInspection;
    expose HmiDisplayVerificationBench;
    expose gapHmiVerificationEnvironmentOpen;
    expose hmiDisplayQuestion;
    expose asmHmiSimulationStandsIn;
    expose asmHmiDrivingBenchReuse;
    expose gapHmiSceneOutput;
    expose hmiPerceptionQualityOutOfScope;
    expose hmiOnRoadOperationOutOfScope;
    expose gapHmiDisplayInProductLine;
    expose gapHmiUpstreamContact;
    expose gapHmiDrawingToleranceUnset;
    expose claimSupportedByHmiDisplayInputsArgument;
    expose claimSupportedByHmiContentVarianceArgument;
    expose claimSupportedByHmiWarningSequenceArgument;
    expose claimSupportedByHmiContentCurrencyArgument;
    expose claimSupportedByHmiAndroidOutageArgument;
    expose claimSupportedByHmiRendererAllocationArgument;
    expose claimSupportedByHmiRendererPathArgument;
    expose claimSupportedByHmiDisplayVerdictArgument;
    expose hmiDisplayInputsArgumentCitesCases;
    expose hmiContentVarianceArgumentCitesCases;
    expose hmiWarningSequenceArgumentCitesCases;
    expose hmiContentCurrencyArgumentCitesCases;
    expose hmiAndroidOutageArgumentCitesCases;
    expose hmiRendererAllocationArgumentCitesCases;
    expose hmiRendererPathArgumentCitesCases;
    expose hmiDisplayVerdictArgumentCitesCases;
    expose hmiCounterClaimRecordingIsNoVerdictBoundTo;
    expose hmiCounterClaimSimulatedConfigurationOnlyBoundTo;
    expose hmiCounterClaimDrivingBenchResultsNoEvidenceBoundTo;
    expose hmiCounterClaimSceneFromAStandInBoundTo;
    expose hmiCounterClaimPerceptionNotJudgedBoundTo;
    expose hmiCounterClaimNoComplianceOrApprovalBoundTo;
    expose hmiCounterClaimNoMemberProductBoundTo;
    expose hmiCounterClaimNoUpstreamEndorsementBoundTo;
    expose hmiCounterClaimDrawingToleranceUnsetBoundTo;
    expose hmiCounterClaimEnvironmentOpenNoVerdictBoundTo;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
