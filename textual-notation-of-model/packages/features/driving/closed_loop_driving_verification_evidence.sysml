/*
 * DE4SDV closed-loop driving verification and evidence model slice.
 *
 * INC-DRIVING-001, phase 10, first slice: the verification cases. Each
 * case verifies one requirement of DE4SDV_ClosedLoopDrivingNeedsRequirements,
 * checks the success criteria that the requirement states and adds no
 * criterion of its own, and binds the subject of its requirement to the
 * driving software of the configured product DRIVING-CONFIG-001 (phase 9).
 * One case per requirement, thirty-five cases (owner decision of
 * 2026-11-06); the cases of one scenario read the record of the same run.
 *
 * No case has started. No evidence record exists, and each requirement
 * keeps the verification status NotStarted. The doc of each case usage
 * states the scenario and the bench that the case needs, so that the
 * execution slice can plan the runs. The System 2 test environment is the
 * framing's closedLoopVerificationEnvironment; its hosts, their topology
 * and the capture pipeline are fixed by the readiness probes the owner
 * authorized on 2026-11-06, read into phase 8's amendment of 2026-11-09:
 * three hosts and separate real-time recordings per host. The environment's
 * identity in the record stays open (GAP-DRIVING-009). The
 * validation of the needs stays planned in phase 4 (SC-DRIVING-005 to
 * SC-DRIVING-011). This slice adds no validation case.
 *
 * The outcome vocabulary and the verdict map are this increment's own,
 * with the six literals of INC-MW-010's, so that a later lift into the
 * method is a rename (owner decision of 2026-11-06). The evidence record
 * is one record per run: it binds DRIVING-CONFIG-001, the receipt digest,
 * the model revision, the checkpoint and source identities the run record
 * of REQ-DRIVING-033 names, the pins of the S-CORE components and of the
 * simulator, the scenario, the two clock spans and the retained artifacts,
 * among them the bench recordings. The claims of the increment are stated
 * now, one per phase 1 concern this phase answers, each supported by an
 * argument that cites the planned cases; the counter-claims are the
 * framing's non-claims, each tied to the record that keeps it open. A
 * claim stated before its evidence is a claim to be proven, not a result.
 * This slice makes no result, safety, cybersecurity, compliance or
 * certification claim.
 */
package DE4SDV_ClosedLoopDrivingVerificationEvidence {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ClosedLoopDrivingNeedsRequirements::*;
  private import DE4SDV_ClosedLoopDrivingFraming::closedLoopVerificationEnvironment;
  private import DE4SDV_ClosedLoopDrivingFraming::timeDomainHonestyConcern;
  private import DE4SDV_ClosedLoopDrivingFraming::reproducibleClosedLoopEvidenceConcern;
  private import DE4SDV_ClosedLoopDrivingFraming::gapClosedLoopPerformance;
  private import DE4SDV_ClosedLoopDrivingFraming::roadDeploymentOutOfScope;
  private import DE4SDV_ClosedLoopDrivingFraming::gapProductLineAdmission;
  private import DE4SDV_ClosedLoopDrivingFraming::gapAdoptionAndRights;
  private import DE4SDV_ClosedLoopDrivingFraming::gapModelInputAndFeedback;
  private import DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::asmSimulatedSensorsStandForTheVehicles;
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  enum def DrivingScenarioIdentity {
    doc /*
     * The scenario of a run, as the records and the evidence record name
     * it. closedLoopRoute is SC-DRIVING-001, the vehicle driven along the
     * route from the system's own plans; the observation of SC-DRIVING-002
     * is shown by the same run on the IVI display and its recording.
     * degradedInputOrPlan is SC-DRIVING-003 with the fault the case names.
     * aaosUnavailable is SC-DRIVING-004 on replayed inputs.
     * checkpointRefusal is no scenario of phase 2: a start of the driving
     * system with an unpinned checkpoint, the condition of REQ-DRIVING-035.
     */
    closedLoopRoute;
    degradedInputOrPlan;
    aaosUnavailable;
    checkpointRefusal;
  }

  enum def DrivingEvidenceOutcome {
    doc /*
     * The outcome of processing one run's record against the success
     * criteria of one requirement. The six literals of INC-MW-010's
     * vocabulary: a record that meets the criteria gives
     * passBoundedVerification; a record that shows them not met gives
     * failObservedBehavior; a missing or partial record gives
     * inconclusiveMissingEvidence; a run the bench could not perform gives
     * blockedTargetRuntime; a record that cannot be read gives
     * errorEvidence. passBoundedValidation is the outcome of a validation,
     * which no case of this slice performs.
     */
    passBoundedVerification;
    passBoundedValidation;
    failObservedBehavior;
    inconclusiveMissingEvidence;
    blockedTargetRuntime;
    errorEvidence;
  }

  calc def MapDrivingEvidenceOutcomeToVerdict {
    in outcome : DrivingEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == DrivingEvidenceOutcome::passBoundedVerification? VerdictKind::pass
      else if outcome == DrivingEvidenceOutcome::passBoundedValidation? VerdictKind::pass
      else if outcome == DrivingEvidenceOutcome::failObservedBehavior? VerdictKind::fail
      else if outcome == DrivingEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  item def RetainedDrivingRunEvidence {
    doc /*
     * The evidence record of one run; the cases of the run's scenario read
     * it. It binds DRIVING-CONFIG-001 as its configurationIdentity.
     * receiptSha256 is the SHA-256 of the receipt the run ran against, as
     * DRIVING-CONFIG-001 asks of the evidence that binds it; if it differs
     * from the receiptSha256 of DRIVING-CONFIG-001, the verdict holds for
     * DRIVING-CONFIG-001 only if the configuration's own receipt record did
     * not change, which the pull request that rebinds the digest states.
     * modelRevision is the Git commit of the DE4SDV model the run
     * evaluated. checkpointSha256, autoE2ESourceRevision and
     * configurationSha256 are the values of the run record of
     * REQ-DRIVING-033, and runRecordIdentity names that record.
     * scoreFEORevision, scoreCommunicationVersion, scoreLifecycleVersion
     * and scoreSOMEIPGatewayCommit are the pins of the S-CORE components
     * the run built; simulatorBuild is the simulator server's. scenario
     * names the run's scenario. simulationClockSpan and wallClockSpan are
     * the two clocks of the run, kept apart. executionEnvironmentIdentity
     * names the hosts and, where the guests ran, the builds of the SDV Core
     * image and of the IVI image. contractIdentity names the
     * operational-state topic contract. rawObservationArtifact names the
     * retained records: the inputs, plans, commands, publications and
     * S-CORE communication records of the run.
     *
     * benchRecordingArtifact names the bench recordings: separate real-time
     * recordings, one per host, taken while the run runs: the simulator's
     * chase view of the vehicle, rendered and encoded by the simulator
     * host's hardware video encoder (NVENC) after one warm-up lap; the
     * display of the IVI VM with the observer application, recorded on the
     * guest; and the terminal sessions of the bench, recorded as terminal
     * sessions. Each recording shows its clocks. A public cut may place them
     * side by side, aligned by the clocks the run record names; nothing is
     * retimed and nothing is rendered after the run (owner decision of
     * 2026-11-09, which supersedes the single capture of 2026-11-06); the
     * public cut of the increment comes from these recordings and from
     * nothing else.
     * independentObserverIdentity names the observer of the publications
     * and the engineer who re-derived the run identity. claimBoundary
     * states what the record proves and what it does not. A missing or
     * partial record gives inconclusive, never pass. No record exists yet.
     */
    attribute configurationIdentity : ScalarValues::String;
    attribute receiptSha256 : ScalarValues::String;
    attribute modelRevision : ScalarValues::String;
    attribute checkpointSha256 : ScalarValues::String;
    attribute autoE2ESourceRevision : ScalarValues::String;
    attribute configurationSha256 : ScalarValues::String;
    attribute runRecordIdentity : ScalarValues::String;
    attribute scoreFEORevision : ScalarValues::String;
    attribute scoreCommunicationVersion : ScalarValues::String;
    attribute scoreLifecycleVersion : ScalarValues::String;
    attribute scoreSOMEIPGatewayCommit : ScalarValues::String;
    attribute simulatorBuild : ScalarValues::String;
    attribute scenario : DrivingScenarioIdentity;
    attribute simulationClockSpan : ScalarValues::String;
    attribute wallClockSpan : ScalarValues::String;
    attribute executionEnvironmentIdentity : ScalarValues::String;
    attribute contractIdentity : ScalarValues::String;
    attribute rawObservationArtifact : ScalarValues::String;
    attribute benchRecordingArtifact : ScalarValues::String;
    attribute independentObserverIdentity : ScalarValues::String;
    attribute claimBoundary : ScalarValues::String;
  }

  part def ClosedLoopDrivingVerificationBench {
    doc /*
     * The bench of the verification cases of INC-DRIVING-001. System 1 is
     * the configured product DRIVING-CONFIG-001, which the bench refers to
     * and does not own. drivingSoftware is its driving software, the
     * realization of the system of interest: the subject that each verified
     * requirement binds. The System 2 test environment is the framing's
     * closedLoopVerificationEnvironment: three hosts carry the simulator
     * server, the three programs and the guests, and each host records its
     * own part of a run (phase 8's amendment of 2026-11-09); the
     * environment's identity in the record is GAP-DRIVING-009.
     * The bench is not a product selection.
     */
    ref part system1ConfiguredProduct :> DE4SDV_ClosedLoopDrivingVariabilityConfiguration::configuredProduct;
    ref part drivingSoftware :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem = system1ConfiguredProduct.drivingSoftware;
  }

  part closedLoopDrivingVerificationBench : ClosedLoopDrivingVerificationBench;

  part <'GAP-DRIVING-009'> gapDrivingVerificationEnvironmentOpen : IncrementGap {
    doc /*
     * Open: the environment's identity in the evidence record. All of the
     * probes the owner authorized on 2026-11-06 were read from 2026-11-07 to
     * 2026-11-09, and phase 8's amendment of 2026-11-09 fixes the hosts,
     * the topology and the capture: three hosts, the simulator host and the
     * S-CORE host joined by the bench network, the guests on the guest host
     * reached over the VXLAN segment, and separate real-time recordings per
     * host under the recording rule of RetainedDrivingRunEvidence. Still
     * open: the three hosts have not yet run together (GAP-DRIVING-007), and
     * the record does not yet name the hosts, their images and the clocks of
     * the recordings. The next slice adds the environment's identity to the
     * evidence record and closes this gap. Deferred to that slice.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  /* Each case collects the RetainedDrivingRunEvidence record of its run
   * (collectData). processData compares the record with the success
   * criteria of the verified requirement and gives a DrivingEvidenceOutcome.
   * evaluateData maps the outcome to a VerdictKind with
   * MapDrivingEvidenceOutcomeToVerdict. Each objective binds the subject
   * of its requirement to the driving software of DRIVING-CONFIG-001 on the
   * bench. A verify is a planned verification objective, not a verdict. */

  verification def PlanPerStepVerification {
    doc /*
     * Test of REQ-DRIVING-001. collectData records every plan of a run of
     * SC-DRIVING-001 with the simulation time of its step, from the end of
     * priming to the end of the run or to the start of the stop response.
     * processData counts the plans of each 100 ms step of simulation time
     * over that span: a step with two plans, or two consecutive steps
     * without one, gives failObservedBehavior; otherwise, single steps
     * without a plan of their own included, passBoundedVerification.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective planPerStepObjective {
      verify reqPlanEachStep { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PlanByCheckpointInferenceVerification {
    doc /*
     * Test of REQ-DRIVING-002. collectData records every plan of a run of
     * SC-DRIVING-001 with the checkpoint SHA-256 it names and the inputs
     * recorded for it, and an offline inference of the pinned checkpoint by
     * its Python reference on those inputs, on the same host and software.
     * processData checks that every plan names the SHA-256 of the pinned
     * checkpoint and compares every acceleration and curvature of the plan
     * with the offline inference, within 1 % of the largest magnitude of
     * that signal in the plan.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective planByCheckpointInferenceObjective {
      verify reqPlansByCheckpointInference { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def CameraImagesInCheckpointFormVerification {
    doc /*
     * Test of REQ-DRIVING-003. collectData records the inputs recorded for
     * every plan of a run of SC-DRIVING-001. processData checks, per plan,
     * six current images of 512 by 512 pixels in the order front, front
     * left, front right, rear left, rear, rear right, and a current front
     * image of 1024 by 1024 pixels.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective cameraImagesInCheckpointFormObjective {
      verify reqCameraImagesInCheckpointForm { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def CameraHistoryVerification {
    doc /*
     * Test of REQ-DRIVING-004. collectData records the inputs recorded for
     * every plan of a run of SC-DRIVING-001 with the capture times of the
     * history images. processData checks, per plan and per camera, seven
     * earlier images whose capture times lie 0.5 s to 3.5 s before the step
     * at 0.5 s intervals.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective cameraHistoryObjective {
      verify reqCameraHistory { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def ProjectionOperatorsVerification {
    doc /*
     * Test of REQ-DRIVING-005. collectData records the projection operator
     * of every image of a run of SC-DRIVING-001 and, for each camera, the
     * image position of a reference marker that the bench places at a known
     * position in the vehicle frame. processData maps the marker's
     * vehicle-frame position through each camera's operator and compares it
     * with where the marker appears in the image, within 2 pixels.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective projectionOperatorsObjective {
      verify reqProjectionOperators { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def MapContextRasterVerification {
    doc /*
     * Test of REQ-DRIVING-006. collectData records the map_context raster
     * given to the checkpoint for every plan of a run of SC-DRIVING-001,
     * with its geometry tag and the simulation time it was rendered at.
     * processData checks 14 channels, 450 by 300 pixels, the geometry
     * autoe2e-bev-450x300-0p4m-v1 and a render time no more than 500 ms of
     * simulation time before the step.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective mapContextRasterObjective {
      verify reqMapContextRaster { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def RouteMaskRasterVerification {
    doc /*
     * Test of REQ-DRIVING-007. collectData records the route_mask raster
     * given to the checkpoint for every plan of a run of SC-DRIVING-001,
     * with its geometry tag, and the route the route provider gave for the
     * run. processData checks two channels, 450 by 300 pixels, the geometry
     * autoe2e-bev-450x300-0p4m-v1, and that the route corridor covers the
     * route of the run.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective routeMaskRasterObjective {
      verify reqRouteMaskRaster { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def EgoMotionHistoryVerification {
    doc /*
     * Test of REQ-DRIVING-008. collectData records the ego-motion history
     * given to the checkpoint for every plan of a run of SC-DRIVING-001,
     * the poses the simulator records for the commanded vehicle at every
     * step, and the origin of its camera rig. processData moves the poses to
     * that origin, works speed and acceleration out of the 66 that end at the
     * plan's step the source's way, compares the 64 samples, oldest first and
     * the newest 100 ms before the step, with them within 0.05 m/s and
     * 0.1 m/s², and checks that yaw rate and curvature are 0.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective egoMotionHistoryObjective {
      verify reqEgoMotionHistory { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def HoldUntilHistoriesCompleteVerification {
    doc /*
     * Test of REQ-DRIVING-009. collectData records the commands and the
     * capture records of a run of SC-DRIVING-001 that starts with the
     * vehicle at rest. processData checks that the commands hold the
     * vehicle at standstill until the run has recorded eight images of each
     * camera 0.5 s apart and 64 motion samples, and release it afterwards.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective holdUntilHistoriesCompleteObjective {
      verify reqHoldUntilHistoriesComplete { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def HistoriesFromCapturedInputsVerification {
    doc /*
     * Test of REQ-DRIVING-010. collectData records every image and sample
     * given to the checkpoint in a run of SC-DRIVING-001 with the capture
     * record each names, and the capture records of the run. processData
     * checks that every history element names a capture record of the run
     * and that no capture record appears twice in one history.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective historiesFromCapturedInputsObjective {
      verify reqHistoriesFromCapturedInputs { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def CommandsFromNewestValidPlanVerification {
    doc /*
     * Test of REQ-DRIVING-011. collectData records every command that
     * reaches the actuation with the plan it names and the inference that
     * plan names, the simulator's control log for the autopilot, the
     * traffic manager and any scripted control, and the steering commands
     * around a test plan of opposite curvature sign that the bench puts in
     * place of one checkpoint plan. processData checks that every command
     * names its plan and that plan its inference, that no autopilot,
     * traffic-manager, recorded, replayed or scripted control reached the
     * actuation at any time, and that the steering sign reversed within 100
     * ms of simulation time after the test plan.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective commandsFromNewestValidPlanObjective {
      verify reqCommandsFromNewestValidPlan { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def CommandsWithinActuationLimitsVerification {
    doc /*
     * Test of REQ-DRIVING-012. collectData records every command of a run
     * of SC-DRIVING-001 in which the bench puts test plans that exceed the
     * steering and acceleration limits of the configuration in place of
     * checkpoint plans, and the limits the configuration names. processData
     * checks that every command of the run stays within those limits.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective commandsWithinActuationLimitsObjective {
      verify reqCommandsWithinActuationLimits { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PlanWithinPlanningPeriodVerification {
    doc /*
     * Test of REQ-DRIVING-013. collectData records, over a 60 s wall-clock
     * window that starts at the end of priming, the time each plan's newest
     * camera image became available to the driving system and the plan's
     * production time, both on the monotonic clock of the host, and the
     * real-time factor of the simulation. processData checks a real-time
     * factor of at least 0.95, that at least 99 % of the plans were
     * produced within 100 ms after their newest image was available, and
     * that no two consecutive plans missed it.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective planWithinPlanningPeriodObjective {
      verify reqPlanWithinPlanningPeriod { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PlansAndCommandsOverSCOREVerification {
    doc /*
     * Test of REQ-DRIVING-014. collectData records the S-CORE communication
     * records of the host, every command that reaches the actuation with
     * the plan it names, and the commands after the bench stops the S-CORE
     * communication of the driving system in the run. processData matches
     * every command at the actuation to its plan in the S-CORE
     * communication records and checks that no command computed from a plan
     * reached the actuation after the stop.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective plansAndCommandsOverSCOREObjective {
      verify reqPlansAndCommandsOverSCORE { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PublishPlansVerification {
    doc /*
     * Test of REQ-DRIVING-015. collectData records, over a 60 s window of a
     * run of SC-DRIVING-001, every plan in the records of the run and every
     * plan publication the independent observer received, with producer and
     * production time. processData checks that every plan was published
     * once, equal to its record, with its producer and its production time,
     * within 100 ms of wall-clock time after that production time.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective publishPlansObjective {
      verify reqPublishPlans { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PublishVehicleStateVerification {
    doc /*
     * Test of REQ-DRIVING-016. collectData records, over a 60 s window of a
     * run of SC-DRIVING-001, the motion sample of every step with the time
     * the driving system received it, and every motion-sample publication
     * the independent observer received. processData checks that the sample
     * of every step was published once, equal to its record, with its
     * producer and its sample time, within 100 ms of wall-clock time after
     * the driving system received it.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective publishVehicleStateObjective {
      verify reqPublishVehicleState { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PublishHealthPeriodicallyVerification {
    doc /*
     * Test of REQ-DRIVING-017. collectData records, over a 60 s window of a
     * run of SC-DRIVING-001 that includes priming, driving and a stop,
     * every health publication the independent observer received with its
     * arrival time on the monotonic clock of the host. processData checks
     * that no two consecutive health publications are more than 200 ms
     * apart and that each holds the mode, the cause of the stop while
     * stopped and the age of the newest valid plan, with its producer and
     * its production time.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective publishHealthPeriodicallyObjective {
      verify reqPublishHealthPeriodically { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PlansIndependentOfObservationVerification {
    doc /*
     * Test of REQ-DRIVING-018. collectData records the plans and commands
     * of four runs on the same recorded inputs: two reference runs with the
     * SDV Core VM receiving normally, one with it receiving every
     * publication 1 s late and one with it stopped. processData measures
     * how far the plans and commands of the late run and of the stopped run
     * differ from the first reference run and checks that neither differs
     * more than the second reference run does.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective plansIndependentOfObservationObjective {
      verify reqPlansIndependentOfObservation { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PlanningTimeIndependentOfObservationVerification {
    doc /*
     * Test of REQ-DRIVING-019. collectData records the planning time of
     * REQ-DRIVING-013 for every plan of the four runs of VC-DRIVING-018.
     * processData computes the 99th percentile of the planning time per run
     * and checks that it differs by no more than 10 ms between any two of
     * the four.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective planningTimeIndependentOfObservationObjective {
      verify reqPlanningTimeIndependentOfObservation { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopResponseDecelerationVerification {
    doc /*
     * Test of REQ-DRIVING-020. collectData records the acceleration
     * commands of two runs of SC-DRIVING-003 in which the stop response is
     * entered at 10 m/s and at 20 m/s, from the start of the stop response
     * to standstill. processData checks a commanded deceleration of 4 m/s²
     * within 0.2 m/s² over that span in both runs.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopResponseDecelerationObjective {
      verify reqStopResponseDeceleration { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopResponseSteeringHeldVerification {
    doc /*
     * Test of REQ-DRIVING-021. collectData records the steering commands of
     * the two runs of VC-DRIVING-020 and the last steering command computed
     * from a valid plan before the stop response began. processData checks
     * that the steering command stays at that last value from the start of
     * the stop response until standstill.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopResponseSteeringHeldObjective {
      verify reqStopResponseSteeringHeld { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StandstillAfterStopVerification {
    doc /*
     * Test of REQ-DRIVING-022. collectData records the vehicle's motion and
     * the commands of the two runs of VC-DRIVING-020 from standstill to the
     * end of the run, with the plan each command names and the production
     * time of that plan. processData checks that the vehicle stays at
     * standstill to the end of the run and that no command was computed
     * from a plan made after the stop response began.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective standstillAfterStopObjective {
      verify reqStandstillAfterStop { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopOnDegradedCameraImagesVerification {
    doc /*
     * Test of REQ-DRIVING-023. collectData records the start of the stop
     * response in a run of SC-DRIVING-003 in which the bench withholds the
     * images of one camera, in one in which it delivers a corrupt image,
     * and in a run of SC-DRIVING-001 without these faults. processData
     * checks that the stop response began within 100 ms of simulation time
     * after the 200 ms limit was passed or the corrupt image arrived, and
     * that it did not begin in the run without the faults.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopOnDegradedCameraImagesObjective {
      verify reqStopOnDegradedCameraImages { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopOnDegradedMotionVerification {
    doc /*
     * Test of REQ-DRIVING-024. collectData records the start of the stop
     * response in a run of SC-DRIVING-003 in which the bench freezes the
     * motion samples and in one in which it delivers a sample with a value
     * that is not finite. processData checks that the stop response began
     * within 100 ms of simulation time after the 200 ms limit was passed or
     * the invalid sample arrived.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopOnDegradedMotionObjective {
      verify reqStopOnDegradedMotion { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopOnDegradedRouteVerification {
    doc /*
     * Test of REQ-DRIVING-025. collectData records the start of the stop
     * response in a run of SC-DRIVING-003 in which the bench stops the
     * route and in one in which it delivers a route with an empty corridor.
     * processData checks that the stop response began within 100 ms of
     * simulation time after the 1 s limit was passed or the empty route
     * arrived.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopOnDegradedRouteObjective {
      verify reqStopOnDegradedRoute { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopOnStalePlanVerification {
    doc /*
     * Test of REQ-DRIVING-026. collectData records the age of the newest
     * valid plan at each command and the start of the stop response in a
     * run of SC-DRIVING-003 in which the bench stalls planning and in one
     * in which it drops plans. processData checks that the stop response
     * began within 100 ms of simulation time after that age passed 300 ms.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopOnStalePlanObjective {
      verify reqStopOnStalePlan { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopOnInvalidPlanVerification {
    doc /*
     * Test of REQ-DRIVING-027. collectData records the start of the stop
     * response and the commands in a run of SC-DRIVING-003 in which the
     * bench injects a plan with a value that is not finite and in one in
     * which it injects a plan of 63 pairs. processData checks that the stop
     * response began within 100 ms of simulation time after the invalid
     * plan arrived and that no command was computed from it.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopOnInvalidPlanObjective {
      verify reqStopOnInvalidPlan { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StopOnLostCommandsVerification {
    doc /*
     * Test of REQ-DRIVING-028. collectData records the commands at the
     * actuation of a run of SC-DRIVING-001 in which the bench stops the
     * S-CORE communication of the driving system, with the simulation time
     * of the last command that arrived. processData checks that the
     * commands at the actuation follow the stop response from no later than
     * 300 ms of simulation time after the last command arrived.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stopOnLostCommandsObjective {
      verify reqStopOnLostCommands { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PublishStopVerification {
    doc /*
     * Test of REQ-DRIVING-029. collectData records, in each run of
     * VC-DRIVING-023 to VC-DRIVING-028, the start of the stop response, the
     * publication that the driving system is stopped with its cause, and
     * every later health publication, each with its arrival time on the
     * monotonic clock of the host. processData checks that the stop
     * publication with the cause of that run followed within 100 ms of
     * wall-clock time after the stop response began and that every later
     * health publication shows the mode stopped.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective publishStopObjective {
      verify reqPublishStop { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StampInputsVerification {
    doc /*
     * Test of REQ-DRIVING-030. collectData records every camera image and
     * motion sample in the records of a run of SC-DRIVING-001 with its time
     * stamp and the clock the stamp names. processData checks that each
     * carries a capture time marked as simulation time.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stampInputsObjective {
      verify reqStampInputs { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StampPlansVerification {
    doc /*
     * Test of REQ-DRIVING-031. collectData records every plan in the
     * records of a run of SC-DRIVING-001 with its two time stamps and the
     * clock each names. processData checks that each plan carries the
     * capture time of its newest camera image marked as simulation time and
     * a production time marked as the monotonic clock of the host.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stampPlansObjective {
      verify reqStampPlans { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def StampCommandsVerification {
    doc /*
     * Test of REQ-DRIVING-032. collectData records every command in the
     * records of a run of SC-DRIVING-001 with the plan it names, its issue
     * time and its actuation time, and the clock each stamp names.
     * processData computes, from the records alone, the input age at
     * actuation and the planning interval in simulation time and the
     * planning time and the S-CORE transport delay on the monotonic clock
     * of the host; a quantity that cannot be computed without combining
     * times of two domains gives failObservedBehavior.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective stampCommandsObjective {
      verify reqStampCommands { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def RecordRunIdentityVerification {
    doc /*
     * Test of REQ-DRIVING-033. collectData records the run record of a run
     * of SC-DRIVING-001 with the time it was written and the time of the
     * first plan, and the SHA-256 of the checkpoint file, the SHA-256 of
     * the configuration and the source revision that the independent
     * observer derives from the named files and checkout. processData
     * checks that the record precedes the first plan and that the derived
     * values equal the recorded ones.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective recordRunIdentityObjective {
      verify reqRecordRunIdentity { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def PlansNameRunRecordVerification {
    doc /*
     * Test of REQ-DRIVING-034. collectData records every plan in the
     * records of a run of SC-DRIVING-001 with the run record it names.
     * processData checks that every plan names the run record of
     * REQ-DRIVING-033 of that run.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective plansNameRunRecordObjective {
      verify reqPlansNameRunRecord { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def RefuseUnpinnedCheckpointVerification {
    doc /*
     * Test of REQ-DRIVING-035. collectData records the plans, the vehicle's
     * motion and the health publications of a start with a checkpoint file
     * that differs from the named one in a single byte, and of a start with
     * a configuration that names no checkpoint SHA-256. processData checks
     * that no plan was produced, that the vehicle stayed at standstill and
     * that the health names the mismatch, in both starts.
     */
    subject verifiedBench : ClosedLoopDrivingVerificationBench;
    objective refuseUnpinnedCheckpointObjective {
      verify reqRefuseUnpinnedCheckpoint { subject drivingSystem = verifiedBench.drivingSoftware; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedDrivingRunEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedEvidence : RetainedDrivingRunEvidence = collectData.retainedEvidence;
      out evaluatedOutcome : DrivingEvidenceOutcome;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in evaluatedOutcome : DrivingEvidenceOutcome = processData.evaluatedOutcome;
      out verdict : VerdictKind = MapDrivingEvidenceOutcomeToVerdict(evaluatedOutcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification <'VC-DRIVING-001'> planPerStepVerification : PlanPerStepVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-002'> planByCheckpointInferenceVerification : PlanByCheckpointInferenceVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-003'> cameraImagesInCheckpointFormVerification : CameraImagesInCheckpointFormVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-004'> cameraHistoryVerification : CameraHistoryVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-005'> projectionOperatorsVerification : ProjectionOperatorsVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-006'> mapContextRasterVerification : MapContextRasterVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-007'> routeMaskRasterVerification : RouteMaskRasterVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-008'> egoMotionHistoryVerification : EgoMotionHistoryVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-009'> holdUntilHistoriesCompleteVerification : HoldUntilHistoriesCompleteVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-010'> historiesFromCapturedInputsVerification : HistoriesFromCapturedInputsVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-011'> commandsFromNewestValidPlanVerification : CommandsFromNewestValidPlanVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's plan injection on the plan topic; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-012'> commandsWithinActuationLimitsVerification : CommandsWithinActuationLimitsVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's plan injection on the plan topic; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-013'> planWithinPlanningPeriodVerification : PlanWithinPlanningPeriodVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-014'> plansAndCommandsOverSCOREVerification : PlansAndCommandsOverSCOREVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's stop of the S-CORE communication of
     * the driving system in the run; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-015'> publishPlansVerification : PublishPlansVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and an observer of the publications that is
     * independent of the three programs; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-016'> publishVehicleStateVerification : PublishVehicleStateVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and an observer of the publications that is
     * independent of the three programs; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-017'> publishHealthPeriodicallyVerification : PublishHealthPeriodicallyVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and an observer of the publications that is
     * independent of the three programs; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-018'> plansIndependentOfObservationVerification : PlansIndependentOfObservationVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-004
     * (DrivingScenarioIdentity::aaosUnavailable). Bench: the Linux host
     * with the three programs, the recorded inputs of one run of
     * SC-DRIVING-001 replayed to the driving system in place of the
     * simulator, and the AAOS SDV guests under KVM with the SDV Core VM
     * receiving normally, receiving every publication 1 s late and stopped:
     * four runs, two of them references.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-019'> planningTimeIndependentOfObservationVerification : PlanningTimeIndependentOfObservationVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-004
     * (DrivingScenarioIdentity::aaosUnavailable). Bench: the Linux host
     * with the three programs, the recorded inputs of one run of
     * SC-DRIVING-001 replayed to the driving system in place of the
     * simulator, and the AAOS SDV guests under KVM with the SDV Core VM
     * receiving normally, receiving every publication 1 s late and stopped:
     * four runs, two of them references.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-020'> stopResponseDecelerationVerification : StopResponseDecelerationVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults named in the case; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-021'> stopResponseSteeringHeldVerification : StopResponseSteeringHeldVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults named in the case; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-022'> standstillAfterStopVerification : StandstillAfterStopVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults named in the case; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-023'> stopOnDegradedCameraImagesVerification : StopOnDegradedCameraImagesVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan) for the two runs with
     * a camera fault and SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute) for the run without one.
     * Bench: the Linux host with the three programs under the Launch
     * Manager and the S-CORE services, the simulator server with the
     * simulated sensor rig and the route provider, and the bench's input
     * faults named in the case; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-024'> stopOnDegradedMotionVerification : StopOnDegradedMotionVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults named in the case; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-025'> stopOnDegradedRouteVerification : StopOnDegradedRouteVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults named in the case; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-026'> stopOnStalePlanVerification : StopOnStalePlanVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults named in the case; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-027'> stopOnInvalidPlanVerification : StopOnInvalidPlanVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults named in the case; no
     * guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-028'> stopOnLostCommandsVerification : StopOnLostCommandsVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's stop of the S-CORE communication of
     * the driving system in the run; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-029'> publishStopVerification : PublishStopVerification {
    doc /*
     * Not started. Scenarios: SC-DRIVING-003
     * (DrivingScenarioIdentity::degradedInputOrPlan) and SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute), as the runs of
     * VC-DRIVING-023 to VC-DRIVING-028 have them. Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, the simulator server with the simulated sensor rig and the
     * route provider, and the bench's input faults and stop of the S-CORE
     * communication named in those cases; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-030'> stampInputsVerification : StampInputsVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-031'> stampPlansVerification : StampPlansVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-032'> stampCommandsVerification : StampCommandsVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-033'> recordRunIdentityVerification : RecordRunIdentityVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-034'> plansNameRunRecordVerification : PlansNameRunRecordVerification {
    doc /*
     * Not started. Scenario: SC-DRIVING-001
     * (DrivingScenarioIdentity::closedLoopRoute). Bench: the Linux host
     * with the three programs under the Launch Manager and the S-CORE
     * services, and the simulator server with the simulated sensor rig and
     * the route provider; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  verification <'VC-DRIVING-035'> refuseUnpinnedCheckpointVerification : RefuseUnpinnedCheckpointVerification {
    doc /*
     * Not started. Scenario: none (a start condition of REQ-DRIVING-035)
     * (DrivingScenarioIdentity::checkpointRefusal). Bench: the Linux host
     * with the three programs under the Launch Manager, a checkpoint file
     * that differs from the named one in a single byte, a configuration
     * that names no checkpoint SHA-256, and the simulator server for the
     * standstill; no guest.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> closedLoopDrivingVerificationBench;
  }

  part closedLoopDrivingVerificationSystem {
    doc /*
     * The verification system performs the cases: the System 2 performer,
     * the framing's closedLoopVerificationEnvironment, whose hosts and
     * capture GAP-DRIVING-009 leaves open.
     */
    perform planPerStepVerification;
    perform planByCheckpointInferenceVerification;
    perform cameraImagesInCheckpointFormVerification;
    perform cameraHistoryVerification;
    perform projectionOperatorsVerification;
    perform mapContextRasterVerification;
    perform routeMaskRasterVerification;
    perform egoMotionHistoryVerification;
    perform holdUntilHistoriesCompleteVerification;
    perform historiesFromCapturedInputsVerification;
    perform commandsFromNewestValidPlanVerification;
    perform commandsWithinActuationLimitsVerification;
    perform planWithinPlanningPeriodVerification;
    perform plansAndCommandsOverSCOREVerification;
    perform publishPlansVerification;
    perform publishVehicleStateVerification;
    perform publishHealthPeriodicallyVerification;
    perform plansIndependentOfObservationVerification;
    perform planningTimeIndependentOfObservationVerification;
    perform stopResponseDecelerationVerification;
    perform stopResponseSteeringHeldVerification;
    perform standstillAfterStopVerification;
    perform stopOnDegradedCameraImagesVerification;
    perform stopOnDegradedMotionVerification;
    perform stopOnDegradedRouteVerification;
    perform stopOnStalePlanVerification;
    perform stopOnInvalidPlanVerification;
    perform stopOnLostCommandsVerification;
    perform publishStopVerification;
    perform stampInputsVerification;
    perform stampPlansVerification;
    perform stampCommandsVerification;
    perform recordRunIdentityVerification;
    perform plansNameRunRecordVerification;
    perform refuseUnpinnedCheckpointVerification;
  }

  dependency verificationSystemIsTheClosedLoopVerificationEnvironment
    from closedLoopDrivingVerificationSystem to closedLoopVerificationEnvironment;
  dependency environmentGapOnVerificationSystem
    from gapDrivingVerificationEnvironmentOpen to closedLoopDrivingVerificationSystem;

  requirement def ClosedLoopDrivingClaim :> AssuranceClaim;

  requirement def ClosedLoopDrivingArgument :> AssuranceArgument;

  requirement def ClosedLoopDrivingCounterClaim :> AssuranceCounterClaim;

  requirement drivenAlongTheRouteClaim : ClosedLoopDrivingClaim {
    doc /*
     * Answers drivenAlongTheRouteConcern. For DRIVING-CONFIG-001 on the
     * bench, in a run of SC-DRIVING-001, the vehicle is taken along the
     * route navigation gave from the plans the pinned checkpoint infers on
     * the camera images, the ego-motion history and the route of each step,
     * one plan per 100 ms of simulation time, with every command computed
     * from the newest valid plan, after the vehicle was held until its
     * histories were complete. A claim to be proven: no case has started.
     */
    subject claimSubject : ClosedLoopDrivingVerificationBench;
    require constraint {
      doc /*
       * The claim requires retained records of a run of SC-DRIVING-001
       * bound to DRIVING-CONFIG-001 and its receipt, with the checkpoint's
       * own plans; it excludes driving quality beyond following the route,
       * on-road behavior, and any claim about a vehicle's sensors.
       */
    }
  }

  requirement checkpointCommandAuthorityClaim : ClosedLoopDrivingClaim {
    doc /*
     * Answers checkpointCommandAuthorityConcern. Every command at the
     * actuation of the vehicle comes from a plan of the pinned checkpoint
     * and from nothing else: no autopilot, traffic manager, recording,
     * replay, overlay or scripted control reaches the actuation, every
     * command names its plan and every plan its inference and its run
     * record, commands stay within the configured limits, and a checkpoint
     * that is not the pinned one produces no plan. A claim to be proven: no
     * case has started.
     */
    subject claimSubject : ClosedLoopDrivingVerificationBench;
    require constraint {
      doc /*
       * The claim requires the command records, the simulator's control log
       * and the plan injections of the cases it cites; it excludes any
       * claim about the quality of the checkpoint's plans.
       */
    }
  }

  requirement scoreCommandPathClaim : ClosedLoopDrivingClaim {
    doc /*
     * Answers scoreCommandPathConcern. Plans and the commands computed from
     * them travel from planning to the actuation of the vehicle only over
     * Eclipse S-CORE communication: every command at the actuation is
     * matched to its plan in the S-CORE communication records, and when
     * that communication is stopped no further command from a plan reaches
     * the actuation and the stop response applies at the actuation within
     * 300 ms of simulation time. A claim to be proven: no case has started.
     */
    subject claimSubject : ClosedLoopDrivingVerificationBench;
    require constraint {
      doc /*
       * The claim requires the S-CORE communication records of the host and
       * the command records of the runs it cites; it excludes the hops
       * inside the agent, which the owner's reading of REQ-DRIVING-014
       * leaves to the framework's communication layer, and any claim about
       * S-CORE beyond the pinned components.
       */
    }
  }

  requirement observationFidelityClaim : ClosedLoopDrivingClaim {
    doc /*
     * Answers aaosObservationFidelityConcern. What AAOS SDV receives is
     * what the driving system published: each plan, the motion sample of
     * each step, the health at least every 200 ms of wall-clock time and
     * the stop with its cause, each with its producer and its time; and
     * whether AAOS SDV receives the publications on time, late or not at
     * all changes neither the plans and commands nor the planning time
     * beyond the variation of two reference runs. A claim to be proven: no
     * case has started.
     */
    subject claimSubject : ClosedLoopDrivingVerificationBench;
    require constraint {
      doc /*
       * The claim requires the publications an independent observer
       * received and the plans and commands of the four runs on replayed
       * inputs; it excludes the rendering and the latency of the IVI
       * display, which the increment observes and does not claim.
       */
    }
  }

  requirement degradedInputBehaviorClaim : ClosedLoopDrivingClaim {
    doc /*
     * Answers degradedInputBehaviorConcern. When camera images, motion
     * samples, the route or the plans are missing, invalid or stale, or
     * when no command reaches the actuation, the driving system begins the
     * stop response within the stated limit of simulation time, decelerates
     * at 4 m/s² with the steering held until standstill, holds the vehicle
     * at standstill to the end of the run, and publishes the stop with its
     * cause within 100 ms of wall-clock time. A claim to be proven: no case
     * has started.
     */
    subject claimSubject : ClosedLoopDrivingVerificationBench;
    require constraint {
      doc /*
       * The claim requires the runs of SC-DRIVING-003 with the faults the
       * cases name; it excludes any fault the cases do not inject and any
       * safety claim about the stop response.
       */
    }
  }

  requirement timeDomainHonestyClaim : ClosedLoopDrivingClaim {
    doc /*
     * Answers timeDomainHonestyConcern. Every record carries its time in
     * the domain it was measured in, simulation time for captures, steps,
     * plan age and actuation and the host's monotonic clock for production,
     * issue and transport, every limit is met in its own domain and no
     * computation combines the two, and the planning period of 100 ms holds
     * in wall-clock time at a real-time factor of at least 0.95 on the
     * bench host. A claim to be proven: no case has started.
     */
    subject claimSubject : ClosedLoopDrivingVerificationBench;
    require constraint {
      doc /*
       * The claim requires the stamped records of the runs it cites; it
       * excludes real-time operation on target hardware and any claim about
       * the simulation's real-time factor beyond the window measured.
       */
    }
  }

  requirement reproducibleClosedLoopEvidenceClaim : ClosedLoopDrivingClaim {
    doc /*
     * Answers reproducibleClosedLoopEvidenceConcern. Each run is identified
     * before its first plan by the checkpoint, the source revision and the
     * configuration it ran, each plan names that record, another engineer
     * re-derives the identities from the named files and checkout, each
     * plan is reproduced by an offline inference of the pinned checkpoint
     * on the recorded inputs within 1 %, the run's evidence record binds
     * DRIVING-CONFIG-001, its receipt and the pins of the S-CORE components
     * and of the simulator, and the bench recording shows the simulator's
     * view and the IVI display together with both clocks. A claim to be
     * proven: no case has started.
     */
    subject claimSubject : ClosedLoopDrivingVerificationBench;
    require constraint {
      doc /*
       * The claim requires the run records, the retained evidence records
       * and the bench recordings; it excludes the reproduction of a run's
       * trajectory, which the simulator's dynamics and the planning time do
       * not make deterministic.
       */
    }
  }

  requirement drivenAlongTheRouteArgument : ClosedLoopDrivingArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-001,
     * VC-DRIVING-002, VC-DRIVING-003, VC-DRIVING-004, VC-DRIVING-005,
     * VC-DRIVING-006, VC-DRIVING-007, VC-DRIVING-008, VC-DRIVING-009,
     * VC-DRIVING-010, VC-DRIVING-011, VC-DRIVING-012, VC-DRIVING-033,
     * VC-DRIVING-034 verify, each from the retained record of its run; the
     * argument holds once every cited case has a pass verdict and fails
     * with any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement checkpointCommandAuthorityArgument : ClosedLoopDrivingArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-002,
     * VC-DRIVING-011, VC-DRIVING-012, VC-DRIVING-033, VC-DRIVING-034,
     * VC-DRIVING-035 verify, each from the retained record of its run; the
     * argument holds once every cited case has a pass verdict and fails
     * with any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement scoreCommandPathArgument : ClosedLoopDrivingArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-014,
     * VC-DRIVING-028 verify, each from the retained record of its run; the
     * argument holds once every cited case has a pass verdict and fails
     * with any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement observationFidelityArgument : ClosedLoopDrivingArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-015,
     * VC-DRIVING-016, VC-DRIVING-017, VC-DRIVING-018, VC-DRIVING-019,
     * VC-DRIVING-029 verify, each from the retained record of its run; the
     * argument holds once every cited case has a pass verdict and fails
     * with any fail; an inconclusive or error verdict leaves it open.
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement degradedInputBehaviorArgument : ClosedLoopDrivingArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-009,
     * VC-DRIVING-020, VC-DRIVING-021, VC-DRIVING-022, VC-DRIVING-023,
     * VC-DRIVING-024, VC-DRIVING-025, VC-DRIVING-026, VC-DRIVING-027,
     * VC-DRIVING-028, VC-DRIVING-029 verify, each from the retained record
     * of its run; the argument holds once every cited case has a pass
     * verdict and fails with any fail; an inconclusive or error verdict
     * leaves it open.
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement timeDomainHonestyArgument : ClosedLoopDrivingArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-001,
     * VC-DRIVING-013, VC-DRIVING-030, VC-DRIVING-031, VC-DRIVING-032
     * verify, each from the retained record of its run; the argument holds
     * once every cited case has a pass verdict and fails with any fail; an
     * inconclusive or error verdict leaves it open.
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement reproducibleClosedLoopEvidenceArgument : ClosedLoopDrivingArgument {
    doc /*
     * Argues the success criteria of the requirements that VC-DRIVING-002,
     * VC-DRIVING-033, VC-DRIVING-034 verify, each from the retained record
     * of its run; the argument holds once every cited case has a pass
     * verdict and fails with any fail; an inconclusive or error verdict
     * leaves it open.
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement counterClaimSimulatedSensorsAndDynamics : ClosedLoopDrivingCounterClaim {
    doc /*
     * The proof holds for images the simulator renders at the rig's
     * geometry and for the simulator's ground-truth vehicle state; it must
     * not be read as a statement about a vehicle's cameras or motion
     * sensors, about the checkpoint on real images, or about on-road
     * behavior (ASM-DRIVING-004, roadDeploymentOutOfScope).
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement counterClaimNoRealTimeOnTarget : ClosedLoopDrivingCounterClaim {
    doc /*
     * The planning period is met on the bench host at a real-time factor of
     * at least 0.95 in a measured window; it must not be read as 10 Hz
     * real-time operation on target hardware or as a performance promise
     * (gapClosedLoopPerformance).
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement counterClaimNoSafetyOrCertification : ClosedLoopDrivingCounterClaim {
    doc /*
     * No safety, cybersecurity, compliance, certification or
     * production-readiness claim: the stop response is the bench behavior
     * the requirements state, not a safety concept, and the existing AEBS
     * emergency path is neither changed nor reused as driving proof
     * (roadDeploymentOutOfScope, existingAEBSBehaviorOutOfScope).
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement counterClaimNoMembership : ClosedLoopDrivingCounterClaim {
    doc /*
     * DRIVING-CONFIG-001 is a valid, not admitted configuration; a passed
     * case makes no member product and amends no scope decision; the member
     * decision follows the evidence (gapProductLineAdmission).
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement counterClaimCheckpointRightsAndTransfer : ClosedLoopDrivingCounterClaim {
    doc /*
     * The checkpoint's terms and provenance are unresolved; nothing is
     * claimed about its commercial use, and nothing about upstream's
     * AlpaSim results transfers to this bench (gapAdoptionAndRights).
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement counterClaimBoundedFaults : ClosedLoopDrivingCounterClaim {
    doc /*
     * The degraded-input proof covers the faults the cases inject and no
     * other fault model; a fault the cases do not name is not covered
     * (gapModelInputAndFeedback).
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  requirement counterClaimEnvironmentOpenNoVerdict : ClosedLoopDrivingCounterClaim {
    doc /*
     * No case has started and no evidence record exists; the bench's hosts
     * and capture are not fixed; every claim of this slice is a claim to be
     * proven (GAP-DRIVING-009).
     */
    subject bench : ClosedLoopDrivingVerificationBench;
  }

  dependency claimSupportedByDrivenAlongTheRouteArgument
    from drivenAlongTheRouteArgument to drivenAlongTheRouteClaim;
  dependency claimSupportedByCheckpointCommandAuthorityArgument
    from checkpointCommandAuthorityArgument to checkpointCommandAuthorityClaim;
  dependency claimSupportedByScoreCommandPathArgument
    from scoreCommandPathArgument to scoreCommandPathClaim;
  dependency claimSupportedByObservationFidelityArgument
    from observationFidelityArgument to observationFidelityClaim;
  dependency claimSupportedByDegradedInputBehaviorArgument
    from degradedInputBehaviorArgument to degradedInputBehaviorClaim;
  dependency claimSupportedByTimeDomainHonestyArgument
    from timeDomainHonestyArgument to timeDomainHonestyClaim;
  dependency claimSupportedByReproducibleClosedLoopEvidenceArgument
    from reproducibleClosedLoopEvidenceArgument to reproducibleClosedLoopEvidenceClaim;
  dependency drivenAlongTheRouteArgumentCitesCases
    from drivenAlongTheRouteArgument
    to planPerStepVerification,
      planByCheckpointInferenceVerification,
      cameraImagesInCheckpointFormVerification,
      cameraHistoryVerification,
      projectionOperatorsVerification,
      mapContextRasterVerification,
      routeMaskRasterVerification,
      egoMotionHistoryVerification,
      holdUntilHistoriesCompleteVerification,
      historiesFromCapturedInputsVerification,
      commandsFromNewestValidPlanVerification,
      commandsWithinActuationLimitsVerification,
      recordRunIdentityVerification,
      plansNameRunRecordVerification;
  dependency checkpointCommandAuthorityArgumentCitesCases
    from checkpointCommandAuthorityArgument
    to planByCheckpointInferenceVerification,
      commandsFromNewestValidPlanVerification,
      commandsWithinActuationLimitsVerification,
      recordRunIdentityVerification,
      plansNameRunRecordVerification,
      refuseUnpinnedCheckpointVerification;
  dependency scoreCommandPathArgumentCitesCases
    from scoreCommandPathArgument
    to plansAndCommandsOverSCOREVerification,
      stopOnLostCommandsVerification;
  dependency observationFidelityArgumentCitesCases
    from observationFidelityArgument
    to publishPlansVerification,
      publishVehicleStateVerification,
      publishHealthPeriodicallyVerification,
      plansIndependentOfObservationVerification,
      planningTimeIndependentOfObservationVerification,
      publishStopVerification;
  dependency degradedInputBehaviorArgumentCitesCases
    from degradedInputBehaviorArgument
    to holdUntilHistoriesCompleteVerification,
      stopResponseDecelerationVerification,
      stopResponseSteeringHeldVerification,
      standstillAfterStopVerification,
      stopOnDegradedCameraImagesVerification,
      stopOnDegradedMotionVerification,
      stopOnDegradedRouteVerification,
      stopOnStalePlanVerification,
      stopOnInvalidPlanVerification,
      stopOnLostCommandsVerification,
      publishStopVerification;
  dependency timeDomainHonestyArgumentCitesCases
    from timeDomainHonestyArgument
    to planPerStepVerification,
      planWithinPlanningPeriodVerification,
      stampInputsVerification,
      stampPlansVerification,
      stampCommandsVerification;
  dependency reproducibleClosedLoopEvidenceArgumentCitesCases
    from reproducibleClosedLoopEvidenceArgument
    to planByCheckpointInferenceVerification,
      recordRunIdentityVerification,
      plansNameRunRecordVerification;
  dependency counterClaimSimulatedSensorsAndDynamicsBoundTo
    from counterClaimSimulatedSensorsAndDynamics to asmSimulatedSensorsStandForTheVehicles;
  dependency counterClaimNoRealTimeOnTargetBoundTo
    from counterClaimNoRealTimeOnTarget to gapClosedLoopPerformance;
  dependency counterClaimNoSafetyOrCertificationBoundTo
    from counterClaimNoSafetyOrCertification to roadDeploymentOutOfScope;
  dependency counterClaimNoMembershipBoundTo
    from counterClaimNoMembership to gapProductLineAdmission;
  dependency counterClaimCheckpointRightsAndTransferBoundTo
    from counterClaimCheckpointRightsAndTransfer to gapAdoptionAndRights;
  dependency counterClaimBoundedFaultsBoundTo
    from counterClaimBoundedFaults to gapModelInputAndFeedback;
  dependency counterClaimEnvironmentOpenNoVerdictBoundTo
    from counterClaimEnvironmentOpenNoVerdict to gapDrivingVerificationEnvironmentOpen;

  concern drivingArgumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /*
     * Systems engineers, verification engineers and open-source reviewers
     * need the claims of the increment stated before any run, each with the
     * argument that will support it and the cases that argument cites, the
     * record each run retains, and the limits the counter-claims disclose,
     * so that the evidence of phase 10 is judged against claims written
     * first and not fitted to results. Before any run, every case is not
     * started and every claim is open.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view closedLoopDrivingAssuranceView {
    viewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame drivingArgumentationAssuranceConcern;
      frame timeDomainHonestyConcern;
      frame reproducibleClosedLoopEvidenceConcern;
    }
    doc /*
     * The assurance structure of the increment before any run: the seven
     * claims, the argument that supports each and the cases it cites, the
     * thirty-five cases, the evidence record of a run, the bench and the
     * environment gap, and the seven counter-claims with the records that
     * keep them open, those records exposed beside them. It frames the two
     * phase 1 concerns of the Architecture Management domain beside the
     * phase's own concern, so that both are answered in their domain.
     */
    expose drivenAlongTheRouteClaim;
    expose checkpointCommandAuthorityClaim;
    expose scoreCommandPathClaim;
    expose observationFidelityClaim;
    expose degradedInputBehaviorClaim;
    expose timeDomainHonestyClaim;
    expose reproducibleClosedLoopEvidenceClaim;
    expose drivenAlongTheRouteArgument;
    expose checkpointCommandAuthorityArgument;
    expose scoreCommandPathArgument;
    expose observationFidelityArgument;
    expose degradedInputBehaviorArgument;
    expose timeDomainHonestyArgument;
    expose reproducibleClosedLoopEvidenceArgument;
    expose counterClaimSimulatedSensorsAndDynamics;
    expose counterClaimNoRealTimeOnTarget;
    expose counterClaimNoSafetyOrCertification;
    expose counterClaimNoMembership;
    expose counterClaimCheckpointRightsAndTransfer;
    expose counterClaimBoundedFaults;
    expose counterClaimEnvironmentOpenNoVerdict;
    expose planPerStepVerification;
    expose planByCheckpointInferenceVerification;
    expose cameraImagesInCheckpointFormVerification;
    expose cameraHistoryVerification;
    expose projectionOperatorsVerification;
    expose mapContextRasterVerification;
    expose routeMaskRasterVerification;
    expose egoMotionHistoryVerification;
    expose holdUntilHistoriesCompleteVerification;
    expose historiesFromCapturedInputsVerification;
    expose commandsFromNewestValidPlanVerification;
    expose commandsWithinActuationLimitsVerification;
    expose planWithinPlanningPeriodVerification;
    expose plansAndCommandsOverSCOREVerification;
    expose publishPlansVerification;
    expose publishVehicleStateVerification;
    expose publishHealthPeriodicallyVerification;
    expose plansIndependentOfObservationVerification;
    expose planningTimeIndependentOfObservationVerification;
    expose stopResponseDecelerationVerification;
    expose stopResponseSteeringHeldVerification;
    expose standstillAfterStopVerification;
    expose stopOnDegradedCameraImagesVerification;
    expose stopOnDegradedMotionVerification;
    expose stopOnDegradedRouteVerification;
    expose stopOnStalePlanVerification;
    expose stopOnInvalidPlanVerification;
    expose stopOnLostCommandsVerification;
    expose publishStopVerification;
    expose stampInputsVerification;
    expose stampPlansVerification;
    expose stampCommandsVerification;
    expose recordRunIdentityVerification;
    expose plansNameRunRecordVerification;
    expose refuseUnpinnedCheckpointVerification;
    expose RetainedDrivingRunEvidence;
    expose ClosedLoopDrivingVerificationBench;
    expose gapDrivingVerificationEnvironmentOpen;
    expose asmSimulatedSensorsStandForTheVehicles;
    expose gapClosedLoopPerformance;
    expose roadDeploymentOutOfScope;
    expose gapProductLineAdmission;
    expose gapAdoptionAndRights;
    expose gapModelInputAndFeedback;
    expose claimSupportedByDrivenAlongTheRouteArgument;
    expose claimSupportedByCheckpointCommandAuthorityArgument;
    expose claimSupportedByScoreCommandPathArgument;
    expose claimSupportedByObservationFidelityArgument;
    expose claimSupportedByDegradedInputBehaviorArgument;
    expose claimSupportedByTimeDomainHonestyArgument;
    expose claimSupportedByReproducibleClosedLoopEvidenceArgument;
    expose drivenAlongTheRouteArgumentCitesCases;
    expose checkpointCommandAuthorityArgumentCitesCases;
    expose scoreCommandPathArgumentCitesCases;
    expose observationFidelityArgumentCitesCases;
    expose degradedInputBehaviorArgumentCitesCases;
    expose timeDomainHonestyArgumentCitesCases;
    expose reproducibleClosedLoopEvidenceArgumentCitesCases;
    expose counterClaimSimulatedSensorsAndDynamicsBoundTo;
    expose counterClaimNoRealTimeOnTargetBoundTo;
    expose counterClaimNoSafetyOrCertificationBoundTo;
    expose counterClaimNoMembershipBoundTo;
    expose counterClaimCheckpointRightsAndTransferBoundTo;
    expose counterClaimBoundedFaultsBoundTo;
    expose counterClaimEnvironmentOpenNoVerdictBoundTo;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
