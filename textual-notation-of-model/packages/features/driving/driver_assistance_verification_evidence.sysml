/*
 * DE4SDV driver-assistance verification and evidence model slice.
 *
 * INC-DRIVING-002, phase 10, first slice: the verification cases. Each case
 * verifies one requirement of DE4SDV_DriverAssistanceNeedsRequirements, checks
 * the success criteria that the requirement states and adds no criterion of its
 * own, and binds the subject of its requirement to the realization of the
 * driver-assistance system in the configured product DRIVING-CONFIG-002 (phase
 * 9). One case per requirement, nine cases, VC-DRIVING-036 to VC-DRIVING-044
 * (the evidence decisions of 2026-11-18). Eight are tests that read the runs of
 * the settings; VC-DRIVING-039 is the analysis of the realization that phase 8
 * records, which REQ-DRIVING-039 asks for, and reads no run.
 *
 * No case has started. No evidence record exists, and each requirement keeps
 * the verification status NotStarted. The doc of each case usage states the
 * scenarios, the settings and the runs that the case reads and the bench that
 * it needs. The System 2 test environment is the framing's
 * driverAssistanceVerificationEnvironment; the readiness items that phase 8
 * left open continue as GAP-DRIVING-014 until the probes run. The validation of
 * the needs stays planned in phase 4 (SC-DRIVING-016 to SC-DRIVING-019). This
 * slice adds no validation case.
 *
 * Where the requirements leave a reading to the cases, the cases read them so.
 * A setting that is not judged, a run that is missing and a run whose record
 * shows a dropped image within the window that a case judges give
 * inconclusiveMissingEvidence, never pass; for a criterion over every run, that
 * window is the whole run. The further run of SC-DRIVING-012 in which the
 * Eclipse S-CORE path of the driver-assistance system is stopped is no run of a
 * setting and no judged run, and only the stop clauses of REQ-DRIVING-038 and
 * REQ-DRIVING-043 read it, as the terms of the requirements state since the
 * stop-run decision of 2026-11-18. In that run the candidate's process keeps
 * running and the path's carriers of the driving command and of the warning
 * request are stopped. No case judges when the display and the sound give the
 * warning (counterClaimWarningModesNotJudgedHere).
 *
 * The outcome vocabulary and the verdict map are this increment's own, with the
 * six literals of INC-DRIVING-001's. The evidence record is one record per run,
 * read by every case of that run: it binds DRIVING-CONFIG-002 and the receipt
 * digest, the model revision, the candidate identity record of REQ-DRIVING-044,
 * the candidate build with the stated delay of the visualization recorder, the
 * pins of the S-CORE platform and of the SOME/IP gateway, the simulator build,
 * the scenario, the setting and the simulated configuration, the two clock
 * spans, the hosts with the S-CORE host's GPU and the guest images, the message
 * type of the warning request, and the criteria record and the revision of the
 * evaluators. The claims of the increment are stated now, one per phase 1
 * concern whose question the cases answer, each supported by an argument that
 * cites the planned cases; vehicleTargetCriteriaConcern is answered by the
 * requirement definition table of phase 5, and no run answers it. The
 * counter-claims are the framing's non-claims, each tied to the record that
 * keeps it open. A claim stated before its evidence is a claim to be proven,
 * not a result. This slice makes no result, evidence, acceptance, safety,
 * compliance or certification claim, and no claim about UNECE R152.
 */
package DE4SDV_DriverAssistanceVerificationEvidence {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_DriverAssistanceNeedsRequirements::*;
  private import DE4SDV_DriverAssistanceFraming::driverAssistanceVerificationEnvironment;
  private import DE4SDV_DriverAssistanceFraming::candidateVerdictConcern;
  private import DE4SDV_DriverAssistanceFraming::asmSimulatedConfigurationStandsIn;
  private import DE4SDV_DriverAssistanceFraming::gapCameraImageAndGeometry;
  private import DE4SDV_DriverAssistanceFraming::onRoadOperationOutOfScope;
  private import DE4SDV_DriverAssistanceFraming::gapDeclaredOperatingConditions;
  private import DE4SDV_DriverAssistanceFraming::gapNoSeparateEmergencyFunction;
  private import DE4SDV_DriverAssistanceFraming::gapCandidateBehaviorUnverified;
  private import DE4SDV_DriverAssistanceFraming::furtherWarningProvisionsOutOfScope;
  private import DE4SDV_DriverAssistanceFraming::gapCandidateAdmission;
  private import DE4SDV_DriverAssistanceFraming::gapUpstreamContactAndRights;
  private import DE4SDV_DriverAssistanceFraming::gapVehicleTargetCriteria;
  private import DE4SDV_DriverAssistanceFraming::candidateTuningOutOfScope;
  private import DE4SDV_DriverAssistanceFraming::asmBenchReuse;
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  enum def AssistanceScenarioIdentity {
    doc /*
     * The scenario of a run, by its phase 2 identity, as the evidence record
     * names it. stationaryTarget is SC-DRIVING-012, a stationary vehicle target
     * ahead; slowerTarget is SC-DRIVING-013, a slower moving vehicle target
     * ahead; curveWithGuardPipes is SC-DRIVING-014, a stationary vehicle beyond
     * a curve with guard pipes; vehicleTurningOff is SC-DRIVING-015, a vehicle
     * ahead that turns off. The runs of curveWithGuardPipes and
     * vehicleTurningOff lie outside the operating conditions that the
     * candidate's documentation declares and are reported apart from the runs
     * inside them (gapDeclaredOperatingConditions).
     */
    stationaryTarget;
    slowerTarget;
    curveWithGuardPipes;
    vehicleTurningOff;
  }

  enum def AssistanceSettingIdentity {
    doc /*
     * The setting of a run, as the terms of the requirements define it: a
     * scenario with an approach speed and its tolerance. stationaryAt20,
     * stationaryAt42 and stationaryAt60 are SC-DRIVING-012 at 20, 42 and 60
     * km/h; slowerAt30 and slowerAt60 are SC-DRIVING-013 at 30 and 60 km/h
     * behind a target at 20 km/h; curveAt30 is SC-DRIVING-014 at 30 km/h toward
     * a curve of at most 25 m radius; turningOffAt40 is SC-DRIVING-015 at 40
     * km/h behind the vehicle ahead. Each setting runs twice and both runs
     * count: fourteen runs. The further run of SC-DRIVING-012 in which the
     * Eclipse S-CORE path of the driver-assistance system is stopped, which
     * REQ-DRIVING-038 and REQ-DRIVING-043 name, is no run of a setting and no
     * judged run, and only the stop clauses of those two requirements read it
     * (the stop-run decision of 2026-11-18); the next slice
     * chooses its approach speed.
     */
    stationaryAt20;
    stationaryAt42;
    stationaryAt60;
    slowerAt30;
    slowerAt60;
    curveAt30;
    turningOffAt40;
  }

  enum def AssistanceEvidenceOutcome {
    doc /*
     * The outcome of processing the evidence of a case against the success
     * criteria of its requirement. The six literals of INC-DRIVING-001's
     * vocabulary: evidence that meets the criteria gives
     * passBoundedVerification; evidence that shows them not met gives
     * failObservedBehavior; missing or partial evidence gives
     * inconclusiveMissingEvidence; a run the bench could not perform gives
     * blockedTargetRuntime; evidence that cannot be read gives errorEvidence.
     * passBoundedValidation is the outcome of a validation, which no case of
     * this slice performs.
     */
    passBoundedVerification;
    passBoundedValidation;
    failObservedBehavior;
    inconclusiveMissingEvidence;
    blockedTargetRuntime;
    errorEvidence;
  }

  calc def MapAssistanceEvidenceOutcomeToVerdict {
    in outcome : AssistanceEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == AssistanceEvidenceOutcome::passBoundedVerification? VerdictKind::pass
      else if outcome == AssistanceEvidenceOutcome::passBoundedValidation? VerdictKind::pass
      else if outcome == AssistanceEvidenceOutcome::failObservedBehavior? VerdictKind::fail
      else if outcome == AssistanceEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  item def RetainedAssistanceRunEvidence {
    doc /*
     * The evidence record of one run; every case that reads the run reads this
     * record (the evidence decisions of 2026-11-18). It binds
     * DRIVING-CONFIG-002 as its configurationIdentity. receiptSha256 is the
     * SHA-256 of the receipt the run ran against, as DRIVING-CONFIG-002 asks of
     * the evidence that binds it; if it differs from the receiptSha256 of
     * DRIVING-CONFIG-002, the verdict holds for DRIVING-CONFIG-002 only if the
     * configuration's own receipt record did not change, which the pull request
     * that rebinds the digest states. modelRevision is the Git commit of the
     * DE4SDV model the run evaluated.
     *
     * candidateRecordIdentity names the candidate identity record of
     * REQ-DRIVING-044 of the run, and upstreamRevision, sourceDifference,
     * networkFileSha256, configurationFileSha256 and launchSettings are its
     * values: the upstream revision, the difference of the built source against
     * it, the SHA-256 of each network file, the SHA-256 of each configuration
     * file and the settings of the launch, verbatim. candidateBuild names the
     * build that ran: VisionPilot at 014e0e7a with the DE4SDV S-CORE interface
     * and the DE4SDV visualization recorder, changes that upstream has not
     * merged (gapCandidateBehaviorUnverified). visualizationRecorderDelay is
     * the delay of the recorder that every verdict of the run states: the
     * readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the
     * median and 5.8 ms more at the 99th percentile from an image to its
     * command, on an S-CORE host with an NVIDIA L4; a run on another host
     * states the delay it measures, and so does a run that measures its own
     * delay.
     *
     * scoreLifecycleVersion, scoreCommunicationVersion and
     * scoreSOMEIPGatewayCommit are the pins of the S-CORE platform and of the
     * SOME/IP gateway that the run built; simulatorBuild is the simulator
     * server's. scenario names the run's scenario; setting names its setting
     * for a run of a setting and is left empty for the further run; runIdentity
     * names the run: the first or the second run of its setting, or the further
     * run in which the Eclipse S-CORE path is stopped, which is no run of a
     * setting. simulatedConfiguration names the simulated configuration of the
     * run: the blueprints of the ego vehicle and of the other vehicles of the
     * scenario, the map and the road, the weather, the fixed step of 0.05 s and
     * synchronous mode, and the camera rig; a digest of the scenario definition
     * that fixes them is enough. simulationClockSpan and wallClockSpan are the
     * two clocks of the run, kept apart. executionEnvironmentIdentity names the
     * three hosts of the run, the simulator host, the S-CORE host with its GPU
     * and the guest host, and the builds of the SDV Core image and of the IVI
     * image. contractIdentity names the message type of the warning request on
     * the guests, which phase 8 left open until phase 10 (GAP-DRIVING-014).
     * criteriaRecordIdentity names the criteria record that the evaluators of
     * the run read, and evaluatorRevision the revision of those evaluators, so
     * that each verdict names the criteria and the evaluators that gave it
     * (gapVehicleTargetCriteria). rawObservationArtifact names the retained
     * records: the candidate identity record, the driving commands and the
     * warning requests at the boundary, the communication records of the
     * Eclipse S-CORE path, the log of the actuation adapter, the simulator's
     * ground truth of the vehicle and of each vehicle ahead and its record of
     * the control of the vehicle, the images that the camera interface dropped,
     * the log of the warning presentation and the candidate's data log. By the
     * rule of phase 8, phase 10 judges no run whose judged window holds a
     * dropped image (MAP-DRIVING-DA-CAMERA-IMAGE); for a criterion over every
     * run, the judged window is the whole run. benchRecordingArtifact names the
     * bench's recording of the run with the candidate's visualization that the
     * recorder draws. independentEngineerIdentity names the engineer who
     * re-derived the candidate identity. claimBoundary states what the record
     * proves and what it does not. A missing or partial record gives
     * inconclusive, never pass. No record exists yet.
     */
    attribute configurationIdentity : ScalarValues::String;
    attribute receiptSha256 : ScalarValues::String;
    attribute modelRevision : ScalarValues::String;
    attribute candidateRecordIdentity : ScalarValues::String;
    attribute upstreamRevision : ScalarValues::String;
    attribute sourceDifference : ScalarValues::String;
    attribute networkFileSha256 : ScalarValues::String;
    attribute configurationFileSha256 : ScalarValues::String;
    attribute launchSettings : ScalarValues::String;
    attribute candidateBuild : ScalarValues::String;
    attribute visualizationRecorderDelay : ScalarValues::String;
    attribute scoreLifecycleVersion : ScalarValues::String;
    attribute scoreCommunicationVersion : ScalarValues::String;
    attribute scoreSOMEIPGatewayCommit : ScalarValues::String;
    attribute simulatorBuild : ScalarValues::String;
    attribute scenario : AssistanceScenarioIdentity;
    attribute setting : AssistanceSettingIdentity[0..1];
    attribute runIdentity : ScalarValues::String;
    attribute simulatedConfiguration : ScalarValues::String;
    attribute simulationClockSpan : ScalarValues::String;
    attribute wallClockSpan : ScalarValues::String;
    attribute executionEnvironmentIdentity : ScalarValues::String;
    attribute contractIdentity : ScalarValues::String;
    attribute criteriaRecordIdentity : ScalarValues::String;
    attribute evaluatorRevision : ScalarValues::String;
    attribute rawObservationArtifact : ScalarValues::String;
    attribute benchRecordingArtifact : ScalarValues::String;
    attribute independentEngineerIdentity : ScalarValues::String;
    attribute claimBoundary : ScalarValues::String;
  }

  item def RetainedCommandFormAnalysis {
    doc /*
     * The evidence record of the analysis of REQ-DRIVING-039, which reads the
     * realization and no run. It binds DRIVING-CONFIG-002 and its receipt as
     * the run record does. modelRevision is the Git commit of the DE4SDV model
     * whose phase 8 realization the analysis read. analyzedRealization names
     * what it read: the driving command payload DrivingCommandEventPayload, its
     * mapping record MAP-DRIVING-DA-COMMAND and the comment
     * reqDetectableDrivingCommandRejection. analystIdentity names the engineer
     * who made the analysis. claimBoundary states that the analysis makes no
     * freedom-from-interference claim. A missing or partial record gives
     * inconclusive, never pass. No record exists yet.
     */
    attribute configurationIdentity : ScalarValues::String;
    attribute receiptSha256 : ScalarValues::String;
    attribute modelRevision : ScalarValues::String;
    attribute analyzedRealization : ScalarValues::String;
    attribute analystIdentity : ScalarValues::String;
    attribute claimBoundary : ScalarValues::String;
  }

  part def DriverAssistanceVerificationBench {
    doc /*
     * The bench of the verification cases of INC-DRIVING-002. System 1 is the
     * configured product DRIVING-CONFIG-002, which the bench refers to and does
     * not own. assistanceSoftware is its realization of the driver-assistance
     * system, the system of interest: the subject that each verified
     * requirement binds. The System 2 test environment is the framing's
     * driverAssistanceVerificationEnvironment, on the three hosts of phase 8;
     * its readiness items stay open as GAP-DRIVING-014. The bench is not a
     * product selection.
     */
    ref part system1ConfiguredProduct :> DE4SDV_DriverAssistanceVariabilityConfiguration::configuredProduct;
    ref part assistanceSoftware :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem = system1ConfiguredProduct.assistanceSoftware;
  }

  part driverAssistanceVerificationBench : DriverAssistanceVerificationBench;

  part <'GAP-DRIVING-014'> gapAssistanceVerificationEnvironmentOpen : IncrementGap {
    doc /*
     * Open: the System 2 test environment is not shown to run the cases. Phase
     * 8 placed the bench on three hosts: the S-CORE host with its NVIDIA L4,
     * the simulator host with its NVIDIA RTX PRO 6000 and CARLA 1.0 at the
     * fixed step of 0.05 s, and the guest host with the SDV Core VM and the IVI
     * VM. The readiness items that phase 8 left open continue here until the
     * probes run (the evidence decisions of 2026-11-18): the link of the S-CORE
     * process with the build of ONNX Runtime for CUDA; whether that process may
     * hold a second C++ standard library or builds ONNX Runtime with the S-CORE
     * toolchain; that the candidate record reaches the vehicle interface, which
     * subscribes after the record was published; the candidate driving on CARLA
     * 1.0, which it has not done yet; whether the S-CORE host's own GPU keeps
     * the candidate's cycle with the S-CORE build; the capture of the start of
     * the sound on the IVI guest, which is unmeasured; and the typed message of
     * the warning request on the guests, open until phase 10. The calibration
     * runs of ASM-DRIVING-005 and ASM-DRIVING-006 come before the first judged
     * run. The draft of the warning output and the interface seam is shown to
     * the VisionPilot maintainers after the scenarios of phase 10 have run in
     * CARLA, with the results (the upstream contact decision of 2026-11-18).
     * Each probe runs only on the owner's word, and nothing of phase 10 is
     * built before the probes are read.
     *
     * The evidence record already holds executionEnvironmentIdentity and
     * contractIdentity; the next slice fills them, plans the runs and closes
     * this gap. Deferred to that slice.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  /* Each case collects the evidence record of its runs, or of its analysis
   * (collectData). processData compares the record with the success criteria of
   * the verified requirement and gives an AssistanceEvidenceOutcome.
   * evaluateData maps the outcome to a VerdictKind with
   * MapAssistanceEvidenceOutcomeToVerdict. Each objective binds the subject of
   * its requirement to the realization of the driver-assistance system in
   * DRIVING-CONFIG-002 on the bench. A verify is a planned verification
   * objective, not a verdict.
   */

  verification def EmergencyBrakingDemandVerification {
    doc /*
     * Test of REQ-DRIVING-036. collectData retains the record of each run of
     * the five settings of SC-DRIVING-012 and SC-DRIVING-013: the driving
     * commands of the driver-assistance system with their simulation times, and
     * the simulator's ground truth of the vehicle and the target. processData
     * judges each run by the terms of the requirements and, in each judged run,
     * checks that the last driving command holds a deceleration of at least 5.0
     * m/s² at each instant of the functional part at which the needed
     * deceleration to the target is at least 5.0 m/s². Every setting judged and
     * every instant met gives passBoundedVerification; an instant not met gives
     * failObservedBehavior; a setting that is not judged gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective emergencyBrakingDemandObjective {
      verify reqEmergencyBrakingForImminentCollision { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def ImpactSpeedWithinLimitVerification {
    doc /*
     * Test of REQ-DRIVING-037. collectData retains the record of each run of
     * the five settings of SC-DRIVING-012 and SC-DRIVING-013: the simulator's
     * ground truth of the vehicle and the target. processData judges each run
     * by the terms of the requirements and, in each judged run, takes the
     * relative approach speed when the collision becomes imminent and the
     * relative impact speed, and checks that the impact speed is at most the
     * maximum relative impact speed for that approach speed. Every setting
     * judged and every judged run within the limit gives
     * passBoundedVerification; a judged run above it gives
     * failObservedBehavior; a setting that is not judged gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective impactSpeedWithinLimitObjective {
      verify reqImpactSpeedWithinLimit { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def DrivingCommandOverSCOREVerification {
    doc /*
     * Test of REQ-DRIVING-038. collectData retains the record of each of the
     * fourteen runs of the seven settings of SC-DRIVING-012 to SC-DRIVING-015
     * and of the further run of SC-DRIVING-012 in which the Eclipse S-CORE path
     * of the driver-assistance system is stopped: the driving commands at the
     * boundary and at the actuation, the communication records of the Eclipse
     * S-CORE path and the simulator's record of the control of the vehicle.
     * processData matches, in each of the fourteen runs, every driving command
     * that reaches the actuation to a driving command of the driver-assistance
     * system in the communication records, checks that the autopilot and the
     * traffic manager of the simulator have no control of the vehicle at any
     * time of those runs and that no recorded, replayed, scripted or overlaid
     * control reaches its actuation, and checks that in the further run no
     * driving command reaches the actuation after the stop. Every criterion met
     * gives passBoundedVerification; a criterion not met gives
     * failObservedBehavior. A run that is missing, or whose record shows a
     * dropped image within the run, gives inconclusiveMissingEvidence, never
     * pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective drivingCommandOverSCOREObjective {
      verify reqDrivingCommandOverSCORE { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def DetectableDrivingCommandVerification {
    doc /*
     * Analysis of REQ-DRIVING-039. collectData retains the
     * RetainedCommandFormAnalysis record: the realization of the driving
     * command that phase 8 records at the model revision. processData names,
     * for a loss, a delay, a repetition and a corruption of a driving command
     * on the Eclipse S-CORE path, the part of the command by which the
     * actuation detects it. A part named for each of the four gives
     * passBoundedVerification; a failure with no such part gives
     * failObservedBehavior. The case reads no run and makes no
     * freedom-from-interference claim.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective detectableDrivingCommandObjective {
      verify reqDetectableDrivingCommand { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = analyze; }
      out item retainedEvidence : RetainedCommandFormAnalysis;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedCommandFormAnalysis = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def WithholdWarningRequestVerification {
    doc /*
     * Test of REQ-DRIVING-040. collectData retains the record of each of the
     * fourteen runs of SC-DRIVING-012 to SC-DRIVING-015: the warning requests
     * of the driver-assistance system at its boundary with their simulation
     * times, and the simulator's ground truth of the vehicle and of each
     * vehicle ahead. As phase 5 states, System 2 records in each of the runs of
     * SC-DRIVING-014 and SC-DRIVING-015 the speeds and the times to collision
     * that the guidance of the source names for the scenario, and the record
     * holds them. processData finds the start of each warning request and
     * checks, by the terms of the requirements, that a collision with a vehicle
     * ahead is imminent at it. Every start at an imminent collision gives
     * passBoundedVerification; a start without one gives failObservedBehavior.
     * A run that is missing, or whose record shows a dropped image within the
     * run, gives inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective withholdWarningRequestObjective {
      verify reqWithholdWarningRequest { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def WithholdEmergencyBrakingVerification {
    doc /*
     * Test of REQ-DRIVING-041. collectData retains the record of each of the
     * fourteen runs of SC-DRIVING-012 to SC-DRIVING-015: the driving commands
     * of the driver-assistance system with their simulation times, and the
     * simulator's ground truth of the vehicle and of each vehicle ahead. As
     * phase 5 states, System 2 records in each of the runs of SC-DRIVING-014
     * and SC-DRIVING-015 the speeds and the times to collision that the
     * guidance of the source names for the scenario, and the record holds them.
     * processData finds the start of each emergency braking, the first command
     * for a deceleration of at least 5.0 m/s² after a command for less, and
     * checks, by the terms of the requirements, that a collision with a vehicle
     * ahead is imminent at it. Every start at an imminent collision gives
     * passBoundedVerification; a start without one gives failObservedBehavior.
     * A run that is missing, or whose record shows a dropped image within the
     * run, gives inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective withholdEmergencyBrakingObjective {
      verify reqWithholdEmergencyBraking { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def WarningRequestBeforeEmergencyBrakingVerification {
    doc /*
     * Test of REQ-DRIVING-042. collectData retains the record of each run of
     * the five settings of SC-DRIVING-012 and SC-DRIVING-013: the warning
     * requests at the boundary and the driving commands of the
     * driver-assistance system with their simulation times, and the simulator's
     * ground truth of the vehicle and the target. processData judges each run
     * by the terms of the requirements and, in each judged run in which the
     * collision with the target becomes imminent, checks that the
     * driver-assistance system gives a warning request at its boundary, at
     * least 1.0 s of simulation time before the start of the first emergency
     * braking of the run when the run has one. Every setting judged and every
     * judged run met gives passBoundedVerification; a judged run not met gives
     * failObservedBehavior; a setting that is not judged gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective warningRequestBeforeEmergencyBrakingObjective {
      verify reqWarningRequestBeforeEmergencyBraking { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def WarningRequestOverSCOREVerification {
    doc /*
     * Test of REQ-DRIVING-043. collectData retains the record of each run of
     * SC-DRIVING-012 and SC-DRIVING-013 and of the further run of
     * SC-DRIVING-012 in which the Eclipse S-CORE path of the driver-assistance
     * system is stopped: the warning requests at the boundary and at their
     * receipt by the warning presentation on the IVI VM, and the communication
     * records of the Eclipse S-CORE path. processData matches, in each of the
     * ten runs, every warning request that reaches the AAOS SDV to a warning
     * request of the driver-assistance system in the communication records, and
     * checks that in the further run no warning request reaches the AAOS SDV
     * after the stop. Every criterion met gives passBoundedVerification; a
     * criterion not met gives failObservedBehavior. A run that is missing, or
     * whose record shows a dropped image within the run, gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective warningRequestOverSCOREObjective {
      verify reqWarningRequestOverSCORE { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def RecordCandidateIdentityVerification {
    doc /*
     * Test of REQ-DRIVING-044. collectData retains the record of each of the
     * fourteen runs of SC-DRIVING-012 to SC-DRIVING-015: the candidate identity
     * record with its time and the time of the first driving command, the
     * values that another engineer obtains who checks out the named revision,
     * applies the recorded difference and hashes the named network files and
     * configuration files, and the record of a build with one change that
     * upstream has not merged. processData checks that every run has the record
     * before its first driving command, that the values obtained equal the
     * recorded ones, and that the record of that build holds a non-empty
     * difference. Every criterion met gives passBoundedVerification; a
     * criterion not met gives failObservedBehavior. A run that is missing, or
     * whose record shows a dropped image within the run, gives
     * inconclusiveMissingEvidence, never pass.
     */
    subject verifiedBench : DriverAssistanceVerificationBench;
    objective recordCandidateIdentityObjective {
      verify reqRecordCandidateIdentity { subject driverAssistanceSystem = verifiedBench.assistanceSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedAssistanceRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedAssistanceRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : AssistanceEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : AssistanceEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapAssistanceEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification <'VC-DRIVING-036'> emergencyBrakingDemandVerification : EmergencyBrakingDemandVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget) and SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget). Settings: stationaryAt20,
     * stationaryAt42, stationaryAt60, slowerAt30 and slowerAt60. Runs: the two
     * runs of each setting, ten runs. Bench: the S-CORE host with the
     * candidate's process, the identity recording application and the actuation
     * adapter under the Launch Manager, the simulator host with CARLA 1.0 and
     * the front camera, and the guest host with the SDV Core VM and the IVI VM.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-037'> impactSpeedWithinLimitVerification : ImpactSpeedWithinLimitVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget) and SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget). Settings: stationaryAt20,
     * stationaryAt42, stationaryAt60, slowerAt30 and slowerAt60. Runs: the two
     * runs of each setting, ten runs. Bench: the S-CORE host with the
     * candidate's process, the identity recording application and the actuation
     * adapter under the Launch Manager, the simulator host with CARLA 1.0 and
     * the front camera, and the guest host with the SDV Core VM and the IVI VM.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-038'> drivingCommandOverSCOREVerification : DrivingCommandOverSCOREVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget), SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
     * (AssistanceScenarioIdentity::curveWithGuardPipes) and SC-DRIVING-015
     * (AssistanceScenarioIdentity::vehicleTurningOff). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30, slowerAt60,
     * curveAt30 and turningOffAt40. Runs: the two runs of each setting,
     * fourteen runs, and the further run of SC-DRIVING-012 in which the Eclipse
     * S-CORE path of the driver-assistance system is stopped, which only the
     * stop clause reads. Bench: the S-CORE host with the candidate's process,
     * the identity recording application and the actuation adapter under the
     * Launch Manager, the simulator host with CARLA 1.0 and the front camera,
     * and the guest host with the SDV Core VM and the IVI VM. In the further
     * run the candidate's process keeps running, and the path's carriers of the
     * driving command and of the warning request are stopped through the Launch
     * Manager; which processes these are is fixed in the next slice. The runs
     * of SC-DRIVING-014 and SC-DRIVING-015 are reported apart from the runs
     * inside the declared operating conditions
     * (gapDeclaredOperatingConditions).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-039'> detectableDrivingCommandVerification : DetectableDrivingCommandVerification {
    doc /*
     * Not started. Scenarios: none; the case reads the realization of phase 8
     * and no run. Bench: the model revision that the record names, read by an
     * analyst; no host.
     */
    @VerificationMethod{ kind = analyze; }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-040'> withholdWarningRequestVerification : WithholdWarningRequestVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget), SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
     * (AssistanceScenarioIdentity::curveWithGuardPipes) and SC-DRIVING-015
     * (AssistanceScenarioIdentity::vehicleTurningOff). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30, slowerAt60,
     * curveAt30 and turningOffAt40. Runs: the two runs of each setting,
     * fourteen runs. Bench: the S-CORE host with the candidate's process, the
     * identity recording application and the actuation adapter under the Launch
     * Manager, the simulator host with CARLA 1.0 and the front camera, and the
     * guest host with the SDV Core VM and the IVI VM. The runs of
     * SC-DRIVING-014 and SC-DRIVING-015 are reported apart from the runs inside
     * the declared operating conditions (gapDeclaredOperatingConditions).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-041'> withholdEmergencyBrakingVerification : WithholdEmergencyBrakingVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget), SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
     * (AssistanceScenarioIdentity::curveWithGuardPipes) and SC-DRIVING-015
     * (AssistanceScenarioIdentity::vehicleTurningOff). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30, slowerAt60,
     * curveAt30 and turningOffAt40. Runs: the two runs of each setting,
     * fourteen runs. Bench: the S-CORE host with the candidate's process, the
     * identity recording application and the actuation adapter under the Launch
     * Manager, the simulator host with CARLA 1.0 and the front camera, and the
     * guest host with the SDV Core VM and the IVI VM. The runs of
     * SC-DRIVING-014 and SC-DRIVING-015 are reported apart from the runs inside
     * the declared operating conditions (gapDeclaredOperatingConditions).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-042'> warningRequestBeforeEmergencyBrakingVerification : WarningRequestBeforeEmergencyBrakingVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget) and SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget). Settings: stationaryAt20,
     * stationaryAt42, stationaryAt60, slowerAt30 and slowerAt60. Runs: the two
     * runs of each setting, ten runs. Bench: the S-CORE host with the
     * candidate's process, the identity recording application and the actuation
     * adapter under the Launch Manager, the simulator host with CARLA 1.0 and
     * the front camera, and the guest host with the SDV Core VM and the IVI VM.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-043'> warningRequestOverSCOREVerification : WarningRequestOverSCOREVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget) and SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget). Settings: stationaryAt20,
     * stationaryAt42, stationaryAt60, slowerAt30 and slowerAt60. Runs: the two
     * runs of each setting, ten runs, and the further run of SC-DRIVING-012 in
     * which the Eclipse S-CORE path of the driver-assistance system is stopped,
     * which only the stop clause reads. Bench: the S-CORE host with the
     * candidate's process, the identity recording application and the actuation
     * adapter under the Launch Manager, the simulator host with CARLA 1.0 and
     * the front camera, and the guest host with the SDV Core VM and the IVI VM.
     * In the further run the candidate's process keeps running, and the path's
     * carriers of the driving command and of the warning request are stopped
     * through the Launch Manager; which processes these are is fixed in the
     * next slice.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-044'> recordCandidateIdentityVerification : RecordCandidateIdentityVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-012
     * (AssistanceScenarioIdentity::stationaryTarget), SC-DRIVING-013
     * (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
     * (AssistanceScenarioIdentity::curveWithGuardPipes) and SC-DRIVING-015
     * (AssistanceScenarioIdentity::vehicleTurningOff). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30, slowerAt60,
     * curveAt30 and turningOffAt40. Runs: the two runs of each setting,
     * fourteen runs. Bench: the S-CORE host with the candidate's process, the
     * identity recording application and the actuation adapter under the Launch
     * Manager, the simulator host with CARLA 1.0 and the front camera, and the
     * guest host with the SDV Core VM and the IVI VM, and another engineer with
     * a checkout of the named revision. The runs of SC-DRIVING-014 and
     * SC-DRIVING-015 are reported apart from the runs inside the declared
     * operating conditions (gapDeclaredOperatingConditions).
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  part driverAssistanceVerificationSystem {
    doc /*
     * The verification system performs the cases: the System 2 performer, the
     * framing's driverAssistanceVerificationEnvironment, whose readiness items
     * GAP-DRIVING-014 leaves open.
     */
    perform emergencyBrakingDemandVerification;
    perform impactSpeedWithinLimitVerification;
    perform drivingCommandOverSCOREVerification;
    perform detectableDrivingCommandVerification;
    perform withholdWarningRequestVerification;
    perform withholdEmergencyBrakingVerification;
    perform warningRequestBeforeEmergencyBrakingVerification;
    perform warningRequestOverSCOREVerification;
    perform recordCandidateIdentityVerification;
  }

  dependency verificationSystemIsTheDriverAssistanceVerificationEnvironment
    from driverAssistanceVerificationSystem to driverAssistanceVerificationEnvironment;
  dependency assistanceEnvironmentGapOnVerificationSystem
    from gapAssistanceVerificationEnvironmentOpen to driverAssistanceVerificationSystem;

  requirement def DriverAssistanceClaim :> AssuranceClaim;

  requirement def DriverAssistanceArgument :> AssuranceArgument;

  requirement def DriverAssistanceCounterClaim :> AssuranceCounterClaim;

  requirement vehicleTargetResponseClaim : DriverAssistanceClaim {
    doc /*
     * Answers vehicleTargetResponseConcern. For DRIVING-CONFIG-002 on the
     * bench, in the judged runs of every setting of SC-DRIVING-012 and
     * SC-DRIVING-013, the driver-assistance system commands a deceleration of
     * at least 5.0 m/s² at each instant of the functional part at which the
     * needed deceleration to the target is at least 5.0 m/s², brakes the
     * vehicle to a relative impact speed of at most the maximum for its
     * relative approach speed and, when the collision with the target becomes
     * imminent, gives a warning request at its boundary at least 1.0 s of
     * simulation time before the start of the first emergency braking of the
     * run; and in each of the fourteen runs of SC-DRIVING-012 to SC-DRIVING-015
     * it starts a warning request and an emergency braking only while a
     * collision with a vehicle ahead is imminent. A claim to be proven: no case
     * has started.
     */
    subject claimSubject : DriverAssistanceVerificationBench;
    require constraint {
      doc /*
       * The claim requires the retained records of the runs it cites, bound to
       * DRIVING-CONFIG-002 and its receipt; it excludes on-road behavior, the
       * test targets that the source regulation prescribes, and any statement
       * about compliance with UNECE R152.
       */
    }
  }

  requirement emergencyBrakingIndependenceClaim : DriverAssistanceClaim {
    doc /*
     * Answers emergencyBrakingIndependenceConcern. The emergency braking of the
     * driver-assistance system leaves it in its one driving command, which
     * reaches the actuation only over the Eclipse S-CORE path and in a form
     * that lets the actuation detect its loss, delay, repetition or corruption
     * on that path: the realization that phase 8 records names, for each of the
     * four, the part of the command by which the actuation detects it. A claim
     * to be proven: no case has started.
     */
    subject claimSubject : DriverAssistanceVerificationBench;
    require constraint {
      doc /*
       * The claim requires the records of the runs and the analysis record it
       * cites; it excludes the independence of a protected emergency command
       * path, which the candidate does not realize, any
       * freedom-from-interference claim, and the rejection of a failure that
       * the actuation detects, which is the share of the S-CORE path and which
       * no case of this increment verifies.
       */
    }
  }

  requirement driverWarningSequenceClaim : DriverAssistanceClaim {
    doc /*
     * Answers driverWarningSequenceConcern. In each judged run of
     * SC-DRIVING-012 and SC-DRIVING-013 in which the collision with the target
     * becomes imminent, the driver-assistance system gives a warning request at
     * its boundary at least 1.0 s of simulation time before the start of the
     * first emergency braking of the run, and in each of the fourteen runs of
     * SC-DRIVING-012 to SC-DRIVING-015 it starts a warning
     * request only while a collision with a vehicle ahead is imminent. A claim
     * to be proven: no case has started.
     */
    subject claimSubject : DriverAssistanceVerificationBench;
    require constraint {
      doc /*
       * The claim requires the records of the runs it cites; it excludes the
       * 0.2 s of wall-clock time from the request to each mode of the warning,
       * the share of the S-CORE path and the AAOS SDV, which no case of this
       * slice verifies and the planned review SC-DRIVING-018 observes, and
       * whether a driver perceives the warning.
       */
    }
  }

  requirement scoreCommandAndWarningPathClaim : DriverAssistanceClaim {
    doc /*
     * Answers scoreCommandAndWarningPathConcern. In each of the fourteen runs
     * of SC-DRIVING-012 to SC-DRIVING-015 every driving command that reaches
     * the actuation, and in each of the ten runs of SC-DRIVING-012 and
     * SC-DRIVING-013 every warning request that reaches the AAOS SDV, is
     * matched in the communication records of the
     * Eclipse S-CORE path to an output of the driver-assistance system; in
     * those fourteen runs the autopilot and the traffic manager of the
     * simulator have no control of the vehicle, and no recorded, replayed,
     * scripted or overlaid control reaches its actuation; and in the further
     * run of SC-DRIVING-012 with the path stopped neither the command nor the
     * request arrives after the stop. A claim to be proven: no case has
     * started.
     */
    subject claimSubject : DriverAssistanceVerificationBench;
    require constraint {
      doc /*
       * The claim requires the communication records of the Eclipse S-CORE path
       * and the records of the runs it cites; it excludes the hand-offs inside
       * the candidate's process and any claim about S-CORE beyond the pinned
       * components.
       */
    }
  }

  requirement candidateVerdictClaim : DriverAssistanceClaim {
    doc /*
     * Answers candidateVerdictConcern. Each verdict that rests on the fourteen
     * runs of SC-DRIVING-012 to SC-DRIVING-015 is bound to the candidate that
     * ran: the candidate identity record of each of those runs,
     * there before its first driving command and re-derived by another
     * engineer, names the upstream revision and the difference of the build,
     * which carries the DE4SDV S-CORE interface and the visualization recorder,
     * so that a verdict holds for that build and states the recorder's delay;
     * and the evidence record of each of those runs binds DRIVING-CONFIG-002
     * and its receipt, the model revision, the pins and the simulated
     * configuration. The record of the further run of SC-DRIVING-012 with the
     * path stopped carries the candidate identity values as well, and no case
     * checks them, because only the stop clauses of REQ-DRIVING-038 and
     * REQ-DRIVING-043 read that run. A fail stays a recorded result. A claim to
     * be proven: no case has started.
     */
    subject claimSubject : DriverAssistanceVerificationBench;
    require constraint {
      doc /*
       * The claim requires the candidate identity records and the retained
       * evidence records of the runs; it excludes a verdict for upstream's
       * revision without the changes, which is a different candidate, and the
       * reproduction of a run's trajectory.
       */
    }
  }

  requirement vehicleTargetResponseArgument : DriverAssistanceArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-036,
     * VC-DRIVING-037, VC-DRIVING-040, VC-DRIVING-041 and VC-DRIVING-042 verify,
     * each from the retained record of its runs; the argument holds once every
     * cited case has a pass verdict and fails with any fail; an inconclusive or
     * error verdict leaves it open.
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement emergencyBrakingIndependenceArgument : DriverAssistanceArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-038 and
     * VC-DRIVING-039 verify, each from the retained record of its runs or of
     * its analysis; the argument holds once every cited case has a pass verdict
     * and fails with any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement driverWarningSequenceArgument : DriverAssistanceArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-040 and
     * VC-DRIVING-042 verify, each from the retained record of its runs; the
     * argument holds once every cited case has a pass verdict and fails with
     * any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement scoreCommandAndWarningPathArgument : DriverAssistanceArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-038 and
     * VC-DRIVING-043 verify, each from the retained record of its runs; the
     * argument holds once every cited case has a pass verdict and fails with
     * any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement candidateVerdictArgument : DriverAssistanceArgument {
    doc /*
     * Argues the success criteria of the requirement that VC-DRIVING-044
     * verifies, from the retained records of its runs; the argument holds once
     * every cited case has a pass verdict and fails with any fail; an
     * inconclusive or error verdict leaves it open.
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimSimulatedConfigurationOnly : DriverAssistanceCounterClaim {
    doc /*
     * A verdict holds for the simulated vehicle, its brakes, the road surface
     * and the simulated target only; it must not be read as a statement about a
     * vehicle, its service brakes and anti-lock function, or the test target
     * that the source regulation prescribes
     * (asmSimulatedConfigurationStandsIn).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimRenderedCameraImages : DriverAssistanceCounterClaim {
    doc /*
     * The candidate sees rendered images, not images of the dataset its
     * object-detection network is trained on, and estimates distances through a
     * calibration that has to match the simulated camera; a fail that a
     * mismatch of the image or of the calibration may explain stays a fail and
     * names gapCameraImageAndGeometry, and a pass says nothing of the candidate
     * on a real camera.
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimNoComplianceOrApproval : DriverAssistanceCounterClaim {
    doc /*
     * No on-road, production-readiness, safety-approval, compliance,
     * type-approval or certification claim, and none about UNECE R152: a
     * criterion derived from it and met in simulation holds for the simulated
     * configuration only, and the applicability of the source regulation to the
     * candidate and its interpretation stay open with their owners
     * (onRoadOperationOutOfScope, gapVehicleTargetCriteria).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimOutsideDeclaredConditions : DriverAssistanceCounterClaim {
    doc /*
     * The runs of SC-DRIVING-014 and SC-DRIVING-015 lie outside the operating
     * conditions that the candidate's documentation declares; their verdicts
     * are reported apart from those of the runs inside them
     * (gapDeclaredOperatingConditions).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimNoIndependentEmergencyPath : DriverAssistanceCounterClaim {
    doc /*
     * The candidate has no emergency function apart from its speed planner, and
     * its braking leaves in the one driving command; a pass of VC-DRIVING-039
     * shows a detectable command, not the independence of a protected emergency
     * command path; whether the candidate's braking can stand for the common
     * capability stays with the member decision
     * (gapNoSeparateEmergencyFunction).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimBuildWithUnmergedChanges : DriverAssistanceCounterClaim {
    doc /*
     * The verdicts hold for VisionPilot at 014e0e7a with the DE4SDV S-CORE
     * interface and the visualization recorder, changes that upstream has not
     * merged, with the recorder's delay stated in each; they are no verdicts of
     * upstream's revision (gapCandidateBehaviorUnverified).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimWarningModesNotJudgedHere : DriverAssistanceCounterClaim {
    doc /*
     * The cases judge the warning request at the boundary and at the AAOS SDV;
     * whether and when the display and the sound give the warning is the
     * planned review SC-DRIVING-018 of phase 4, and the haptic mode, the
     * further rules on the warning signals and whether a driver perceives the
     * warning are not judged (furtherWarningProvisionsOutOfScope).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimNoMemberProduct : DriverAssistanceCounterClaim {
    doc /*
     * DRIVING-CONFIG-002 is a valid configuration that the governed scope does
     * not admit; a case with a pass verdict makes no member product and amends
     * no scope decision; the member decision follows the evidence
     * (gapCandidateAdmission).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimNoUpstreamEndorsementOrRights : DriverAssistanceCounterClaim {
    doc /*
     * No upstream contact, endorsement or rights clearance is asserted: the
     * terms of the network weights and of the data they were trained on are not
     * read, and a result about the project is shown to its maintainers before
     * it is published (gapUpstreamContactAndRights).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimNoTuningToPass : DriverAssistanceCounterClaim {
    doc /*
     * No verdict comes from training the candidate's networks, or from
     * tuning the candidate or a scenario until a case passes: a fail stays a
     * recorded result (candidateTuningOutOfScope).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimReusedBenchNotEvidence : DriverAssistanceCounterClaim {
    doc /*
     * The bench reuses the Eclipse S-CORE command path, the actuation adapter,
     * the path to the AAOS SDV display and the evaluator structure of
     * INC-DRIVING-001; their results for that increment's application are no
     * evidence for this candidate, and each case reads only the records of
     * its own runs (asmBenchReuse).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  requirement counterClaimBenchOpenNoVerdict : DriverAssistanceCounterClaim {
    doc /*
     * No case has started and no evidence record exists; the readiness items of
     * the bench are open; every claim of this slice is a claim to be proven
     * (GAP-DRIVING-014).
     */
    subject bench : DriverAssistanceVerificationBench;
  }

  dependency claimSupportedByVehicleTargetResponseArgument
    from vehicleTargetResponseArgument to vehicleTargetResponseClaim;
  dependency claimSupportedByEmergencyBrakingIndependenceArgument
    from emergencyBrakingIndependenceArgument to emergencyBrakingIndependenceClaim;
  dependency claimSupportedByDriverWarningSequenceArgument
    from driverWarningSequenceArgument to driverWarningSequenceClaim;
  dependency claimSupportedByScoreCommandAndWarningPathArgument
    from scoreCommandAndWarningPathArgument to scoreCommandAndWarningPathClaim;
  dependency claimSupportedByCandidateVerdictArgument
    from candidateVerdictArgument to candidateVerdictClaim;
  dependency vehicleTargetResponseArgumentCitesCases
    from vehicleTargetResponseArgument
    to emergencyBrakingDemandVerification,
      impactSpeedWithinLimitVerification,
      withholdWarningRequestVerification,
      withholdEmergencyBrakingVerification,
      warningRequestBeforeEmergencyBrakingVerification;
  dependency emergencyBrakingIndependenceArgumentCitesCases
    from emergencyBrakingIndependenceArgument
    to drivingCommandOverSCOREVerification,
      detectableDrivingCommandVerification;
  dependency driverWarningSequenceArgumentCitesCases
    from driverWarningSequenceArgument
    to withholdWarningRequestVerification,
      warningRequestBeforeEmergencyBrakingVerification;
  dependency scoreCommandAndWarningPathArgumentCitesCases
    from scoreCommandAndWarningPathArgument
    to drivingCommandOverSCOREVerification,
      warningRequestOverSCOREVerification;
  dependency candidateVerdictArgumentCitesCases
    from candidateVerdictArgument
    to recordCandidateIdentityVerification;
  dependency counterClaimSimulatedConfigurationOnlyBoundTo
    from counterClaimSimulatedConfigurationOnly to asmSimulatedConfigurationStandsIn;
  dependency counterClaimRenderedCameraImagesBoundTo
    from counterClaimRenderedCameraImages to gapCameraImageAndGeometry;
  dependency counterClaimNoComplianceOrApprovalBoundTo
    from counterClaimNoComplianceOrApproval to onRoadOperationOutOfScope;
  dependency counterClaimNoComplianceOrApprovalBoundToCriteria
    from counterClaimNoComplianceOrApproval to gapVehicleTargetCriteria;
  dependency counterClaimOutsideDeclaredConditionsBoundTo
    from counterClaimOutsideDeclaredConditions to gapDeclaredOperatingConditions;
  dependency counterClaimNoIndependentEmergencyPathBoundTo
    from counterClaimNoIndependentEmergencyPath to gapNoSeparateEmergencyFunction;
  dependency counterClaimBuildWithUnmergedChangesBoundTo
    from counterClaimBuildWithUnmergedChanges to gapCandidateBehaviorUnverified;
  dependency counterClaimWarningModesNotJudgedHereBoundTo
    from counterClaimWarningModesNotJudgedHere to furtherWarningProvisionsOutOfScope;
  dependency counterClaimNoMemberProductBoundTo
    from counterClaimNoMemberProduct to gapCandidateAdmission;
  dependency counterClaimNoUpstreamEndorsementOrRightsBoundTo
    from counterClaimNoUpstreamEndorsementOrRights to gapUpstreamContactAndRights;
  dependency counterClaimNoTuningToPassBoundTo
    from counterClaimNoTuningToPass to candidateTuningOutOfScope;
  dependency counterClaimReusedBenchNotEvidenceBoundTo
    from counterClaimReusedBenchNotEvidence to asmBenchReuse;
  dependency counterClaimBenchOpenNoVerdictBoundTo
    from counterClaimBenchOpenNoVerdict to gapAssistanceVerificationEnvironmentOpen;

  concern driverAssistanceArgumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /*
     * Product-line engineers, verification engineers and open-source reviewers
     * need the claims of the increment stated before any run, each with the
     * argument that will support it and the cases that argument cites, the
     * record each run retains, and the limits the counter-claims disclose, so
     * that the lifecycle decision rests on verdicts judged against claims
     * written first and not fitted to results. Before any run, every case is
     * not started and every claim is open.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view driverAssistanceAssuranceView {
    viewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame driverAssistanceArgumentationAssuranceConcern;
      frame candidateVerdictConcern;
    }
    doc /*
     * The assurance structure of the increment before any run: the five claims,
     * the argument that supports each and the cases it cites, the nine cases,
     * the evidence record of a run and the record of the analysis, the bench
     * and the environment gap, and the twelve counter-claims with the records
     * that keep them open, those records exposed beside them. It frames the
     * phase 1 concern of the Architecture Management domain beside the phase's
     * own concern, so that it is answered in its domain.
     */
    expose vehicleTargetResponseClaim;
    expose emergencyBrakingIndependenceClaim;
    expose driverWarningSequenceClaim;
    expose scoreCommandAndWarningPathClaim;
    expose candidateVerdictClaim;
    expose vehicleTargetResponseArgument;
    expose emergencyBrakingIndependenceArgument;
    expose driverWarningSequenceArgument;
    expose scoreCommandAndWarningPathArgument;
    expose candidateVerdictArgument;
    expose counterClaimSimulatedConfigurationOnly;
    expose counterClaimRenderedCameraImages;
    expose counterClaimNoComplianceOrApproval;
    expose counterClaimOutsideDeclaredConditions;
    expose counterClaimNoIndependentEmergencyPath;
    expose counterClaimBuildWithUnmergedChanges;
    expose counterClaimWarningModesNotJudgedHere;
    expose counterClaimNoMemberProduct;
    expose counterClaimNoUpstreamEndorsementOrRights;
    expose counterClaimNoTuningToPass;
    expose counterClaimReusedBenchNotEvidence;
    expose counterClaimBenchOpenNoVerdict;
    expose emergencyBrakingDemandVerification;
    expose impactSpeedWithinLimitVerification;
    expose drivingCommandOverSCOREVerification;
    expose detectableDrivingCommandVerification;
    expose withholdWarningRequestVerification;
    expose withholdEmergencyBrakingVerification;
    expose warningRequestBeforeEmergencyBrakingVerification;
    expose warningRequestOverSCOREVerification;
    expose recordCandidateIdentityVerification;
    expose RetainedAssistanceRunEvidence;
    expose RetainedCommandFormAnalysis;
    expose DriverAssistanceVerificationBench;
    expose gapAssistanceVerificationEnvironmentOpen;
    expose asmSimulatedConfigurationStandsIn;
    expose gapCameraImageAndGeometry;
    expose onRoadOperationOutOfScope;
    expose gapVehicleTargetCriteria;
    expose gapDeclaredOperatingConditions;
    expose gapNoSeparateEmergencyFunction;
    expose gapCandidateBehaviorUnverified;
    expose furtherWarningProvisionsOutOfScope;
    expose gapCandidateAdmission;
    expose gapUpstreamContactAndRights;
    expose candidateTuningOutOfScope;
    expose asmBenchReuse;
    expose claimSupportedByVehicleTargetResponseArgument;
    expose claimSupportedByEmergencyBrakingIndependenceArgument;
    expose claimSupportedByDriverWarningSequenceArgument;
    expose claimSupportedByScoreCommandAndWarningPathArgument;
    expose claimSupportedByCandidateVerdictArgument;
    expose vehicleTargetResponseArgumentCitesCases;
    expose emergencyBrakingIndependenceArgumentCitesCases;
    expose driverWarningSequenceArgumentCitesCases;
    expose scoreCommandAndWarningPathArgumentCitesCases;
    expose candidateVerdictArgumentCitesCases;
    expose counterClaimSimulatedConfigurationOnlyBoundTo;
    expose counterClaimRenderedCameraImagesBoundTo;
    expose counterClaimNoComplianceOrApprovalBoundTo;
    expose counterClaimNoComplianceOrApprovalBoundToCriteria;
    expose counterClaimOutsideDeclaredConditionsBoundTo;
    expose counterClaimNoIndependentEmergencyPathBoundTo;
    expose counterClaimBuildWithUnmergedChangesBoundTo;
    expose counterClaimWarningModesNotJudgedHereBoundTo;
    expose counterClaimNoMemberProductBoundTo;
    expose counterClaimNoUpstreamEndorsementOrRightsBoundTo;
    expose counterClaimNoTuningToPassBoundTo;
    expose counterClaimReusedBenchNotEvidenceBoundTo;
    expose counterClaimBenchOpenNoVerdictBoundTo;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
