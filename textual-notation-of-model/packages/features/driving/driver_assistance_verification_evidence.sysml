/*
 * DE4SDV driver-assistance verification and evidence model slice.
 *
 * INC-DRIVING-002, phase 10: the verification cases (the first slice) and the
 * evidence of record (the second slice). Each case verifies one requirement of
 * DE4SDV_DriverAssistanceNeedsRequirements, checks the success criteria that
 * the requirement states and adds no criterion of its own, and binds the
 * subject of its requirement to the realization of the driver-assistance system
 * in the configured product DRIVING-CONFIG-002 (phase 9). One case per
 * requirement, nine cases, VC-DRIVING-036 to VC-DRIVING-044 (the evidence
 * decisions of 2026-11-18). Eight are tests that read the runs of the settings;
 * VC-DRIVING-039 is the analysis of the realization that phase 8 records, which
 * REQ-DRIVING-039 asks for, and reads no run.
 *
 * The second slice records the evidence of the judged session S1, session
 * 20261121T014447Z of the bench at commit 508649ba: one evidence record per run
 * of S1 and the record of the analysis of REQ-DRIVING-039, written with the
 * status of each case by tools/generate_driver_assistance_evidence_text.py from
 * the records that
 * implementation/driver-assistance-bench/evidence/s1-20261121T014447Z retains;
 * tools/refresh_driver_assistance_s1_evidence.py regenerates them in one
 * command, and no value that comes from a verdict is written by hand. The doc
 * of each case usage opens with its status and states the scenarios, the
 * settings and the runs that the case reads and the bench that it needs. The
 * System 2 test environment is the framing's
 * driverAssistanceVerificationEnvironment; GAP-DRIVING-014 records what of its
 * readiness S1 shows. The validation of the needs stays planned in phase 4
 * (SC-DRIVING-016 to SC-DRIVING-019). This slice adds no validation case.
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
 * On 2026-11-21 the judged session S1 was taken as the evidence of record, on
 * the condition that the bench files that ran on a host are byte-identical to
 * those that the pull request of the bench merges; the README of the evidence
 * directory states the check: the evidence-of-record decision of 2026-11-21. On
 * 2026-11-21 the drop rule of phase 8 was kept: no run whose judged window
 * holds a dropped image is judged, and a reading that the evaluators give with
 * the rule set aside is diagnosis, never a verdict: the drop-rule decision of
 * 2026-11-21. On 2026-11-21 it was recorded that the condition on
 * ASM-DRIVING-005, the calibration of the simulated deceleration, bears on a
 * pass of VC-DRIVING-036 and VC-DRIVING-037 and not on their fail in S1, in
 * which no run of SC-DRIVING-012 holds a commanded deceleration stronger than
 * 0.533 m/s² and the commanded decelerations of each run, fully achieved, would
 * have lowered its speed before the contact by at most 2.4 km/h: the
 * deceleration calibration decision of 2026-11-21. On 2026-11-21 the
 * verification status of each requirement was set from S1, as the requirements
 * package records (the status decision of 2026-11-21).
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
 * evaluators. The claims of the increment were stated in the first slice,
 * before any run, one per phase 1 concern whose question the cases answer, each
 * supported by an argument that cites the cases; vehicleTargetCriteriaConcern
 * is answered by the requirement definition table of phase 5, and no run
 * answers it. The counter-claims are the framing's non-claims, each tied to the
 * record that keeps it open. A verdict of S1 is a verdict of the pinned
 * candidate on this bench in simulation; this slice makes no acceptance,
 * safety, compliance or certification claim, and no claim about UNECE R152.
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
     * inconclusive, never pass. The records of the judged session S1 follow
     * this definition, one per run.
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
     * inconclusive, never pass. The record of the analysis in the judged
     * session S1 follows this definition, commandFormAnalysisEvidence.
     */
    attribute configurationIdentity : ScalarValues::String;
    attribute receiptSha256 : ScalarValues::String;
    attribute modelRevision : ScalarValues::String;
    attribute analyzedRealization : ScalarValues::String;
    attribute analystIdentity : ScalarValues::String;
    attribute claimBoundary : ScalarValues::String;
  }

  /* Evidence records: one RetainedAssistanceRunEvidence per run of the judged
   * session and the RetainedCommandFormAnalysis of VC-DRIVING-039, written by
   * tools/generate_driver_assistance_evidence_text.py from the case evaluators'
   * outputs; regenerate them, never edit them by hand. */
  item stationaryAt20FirstRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-001. The evidence record of run SC-DRIVING-012@20/r1, the
     * first run of the setting stationaryAt20, in the S1 session
     * 20261121T014447Z; records.json names it run 012_20_r1. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:e63c5338e0b1af6ce5a34ec407c1cde1c0c6b1e81b8638d21eb8e93deb0c9f18 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:ae60bd5692ddc954901224b50e1293921ab0d847d18db3d64d0875c1ef3243fb; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_012_20_r1/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::stationaryTarget;
    attribute :>> setting = AssistanceSettingIdentity::stationaryAt20;
    attribute :>> runIdentity = "SC-DRIVING-012@20/r1";
    attribute :>> simulatedConfiguration = "sha256:4eae5e47e739017d76b28cef5ca330f60d99f0fd2eb54f30af44758d2255c115 (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "535.249 s to 568.349 s of simulation time (sim/out/world_012_20_r1/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:06:25.261515Z to 2026-11-21T02:06:58.360793Z (the simulator host's real clock, sim/out/world_012_20_r1/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_012_20_r1/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_012_20_r1/score_side/run/score/candidate_record.json sha256:e63c5338e0b1af6ce5a34ec407c1cde1c0c6b1e81b8638d21eb8e93deb0c9f18; identity recorder log: score/out/score_012_20_r1/score_side/run/score/identityRecorder.jsonl sha256:660e1a7510344fef6d0049e078e94a310e115e5018968287f6227389585f1bd2; driving commands, warning requests and dropped images at the boundary: score/out/score_012_20_r1/score_side/run/score/score_interface.jsonl sha256:748ee32cb41cd7642bfe2aa75d0502862f75a2e1e6aa35f3b723fbf32baa8320; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_012_20_r1/score_side/run/score/actuationAdapter.jsonl sha256:badbc72cc8199a8c69cf5bc5fed301f1f4c7014c1af4cb5d72c68026018d006e; simulator ground truth and control of the vehicle: sim/out/world_012_20_r1/simulator/world.jsonl sha256:5a4f598663ef2e58c9a6905c916bf3159a11c695dd32a102325849dc752120ce; warning presentation log: guest/out/capture_012_20_r1/app_record_warning.jsonl sha256:ebba24024cfe44890f624fb2c982c1f35b51ce28d5003f882fc9eb7f76b56f7b; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_012_20_r1/score_side/vision_pilot/visionpilot.rrd sha256:ef178196554ee7bfc6ec7689f820a45555c211bf0e9f01d209747671fdba0a80 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_012_20_r1/chase_view.mp4 sha256:33400ad03aa9931143956aaa3b29571581dd640e203c2a6fa9325abc6ea0647d; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_012_20_r1/score_side/visualization/visualization.mkv sha256:1b7fae34f2531f3ec0c86e2ad4f9c507de34e9bd07a2f9cd554f805e6aa1a0ed";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 012_20_r1 (setting SC-DRIVING-012@20). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 failObservedBehavior; VC-DRIVING-037 failObservedBehavior; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 failObservedBehavior; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item stationaryAt20SecondRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-002. The evidence record of run SC-DRIVING-012@20/r2, the
     * second run of the setting stationaryAt20, in the S1 session
     * 20261121T014447Z; records.json names it run 012_20_r2. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:288255171a366205384eea98e0adb9cbc76a270eaa53d1139e385e0884445b8b (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:ae60bd5692ddc954901224b50e1293921ab0d847d18db3d64d0875c1ef3243fb; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_012_20_r2/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::stationaryTarget;
    attribute :>> setting = AssistanceSettingIdentity::stationaryAt20;
    attribute :>> runIdentity = "SC-DRIVING-012@20/r2";
    attribute :>> simulatedConfiguration = "sha256:4eae5e47e739017d76b28cef5ca330f60d99f0fd2eb54f30af44758d2255c115 (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "731.133 s to 764.083 s of simulation time (sim/out/world_012_20_r2/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:12:26.564297Z to 2026-11-21T02:12:59.513439Z (the simulator host's real clock, sim/out/world_012_20_r2/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_012_20_r2/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_012_20_r2/score_side/run/score/candidate_record.json sha256:288255171a366205384eea98e0adb9cbc76a270eaa53d1139e385e0884445b8b; identity recorder log: score/out/score_012_20_r2/score_side/run/score/identityRecorder.jsonl sha256:2156e0bda0dfa02871e9c19c4baa55cda5ca91632e084b42adfb73a693ea34b5; driving commands, warning requests and dropped images at the boundary: score/out/score_012_20_r2/score_side/run/score/score_interface.jsonl sha256:77e2b499bb96508d6d66d91097ea52d4ce6cdf0b2411043df0df9cbaa9037ee4; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_012_20_r2/score_side/run/score/actuationAdapter.jsonl sha256:15ee027a67ba152dece643585025d01da1e14e58eeb351cbea8883d9a14dd48e; simulator ground truth and control of the vehicle: sim/out/world_012_20_r2/simulator/world.jsonl sha256:b2ecfc85233d80c5dc421489ccbb8f25d3f5af77dff82407ddba7ef519206603; warning presentation log: guest/out/capture_012_20_r2/app_record_warning.jsonl sha256:780ff69be18956f94f6c42dcd884c1affd20d050372a9d4f3e30e63814fa50d0; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_012_20_r2/score_side/vision_pilot/visionpilot.rrd sha256:35bf976234c933ce467e07f969c9cf00a289ef4f1f0d4ba553ac8902c5b294f2 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_012_20_r2/chase_view.mp4 sha256:2a1bf2d27daf34853feaae99d4631576c611cc2104eebb71214b7ad0edee4929; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_012_20_r2/score_side/visualization/visualization.mkv sha256:abc6ea2f536029c83392f6c89c59e5a021a37c905fe3f66526cdcb87c37d7cd0";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 012_20_r2 (setting SC-DRIVING-012@20). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 inconclusiveMissingEvidence; VC-DRIVING-037 inconclusiveMissingEvidence; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 inconclusiveMissingEvidence; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item stationaryAt42FirstRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-003. The evidence record of run SC-DRIVING-012@42/r1, the
     * first run of the setting stationaryAt42, in the S1 session
     * 20261121T014447Z; records.json names it run 012_42_r1. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:9dafbb466bd5c8eb277cde46ba9f4057d0777072035488f6624003e20ea9b3de (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:38d9d3c964856301854d19563ff44483a4d5633adf247a5e40f25ee6fc0434a4; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_012_42_r1/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::stationaryTarget;
    attribute :>> setting = AssistanceSettingIdentity::stationaryAt42;
    attribute :>> runIdentity = "SC-DRIVING-012@42/r1";
    attribute :>> simulatedConfiguration = "sha256:4d8bfd7071bae2ebdbbb0ec897d200bc8a0e9ec3cfa4d5eb0ceef000c859a844 (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "893.638 s to 922.588 s of simulation time (sim/out/world_012_42_r1/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:17:53.981898Z to 2026-11-21T02:18:22.930597Z (the simulator host's real clock, sim/out/world_012_42_r1/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_012_42_r1/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_012_42_r1/score_side/run/score/candidate_record.json sha256:9dafbb466bd5c8eb277cde46ba9f4057d0777072035488f6624003e20ea9b3de; identity recorder log: score/out/score_012_42_r1/score_side/run/score/identityRecorder.jsonl sha256:f057869024c3f875435acd8af1eed2b764173e3906141528e2335778e68e4575; driving commands, warning requests and dropped images at the boundary: score/out/score_012_42_r1/score_side/run/score/score_interface.jsonl sha256:02d7f3e470635a8b59ac496297e61d0e9409e9e3c6e717403f2ba8baad0fb85f; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_012_42_r1/score_side/run/score/actuationAdapter.jsonl sha256:2cf338566ebd64d00243ef51826ced5e4dd9911d360351fdb09d5b604755b748; simulator ground truth and control of the vehicle: sim/out/world_012_42_r1/simulator/world.jsonl sha256:acded502bd40d571aaeb873cfef7e22676ce0d0659a1bd8c13d339d2147b6ae7; warning presentation log: guest/out/capture_012_42_r1/app_record_warning.jsonl sha256:762a3f5a2fc692bb51db8d18c76e57d0afb1303cbdf1628e8f3cc04ac7827255; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_012_42_r1/score_side/vision_pilot/visionpilot.rrd sha256:46c5291ed2e181413726b18ab92b612994e615b514497093a1aae93a20c888f6 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_012_42_r1/chase_view.mp4 sha256:ef985a14d89c8d0533aaa972238dd29d62f293b439b21e017db3551defa85202; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_012_42_r1/score_side/visualization/visualization.mkv sha256:b1f55a871daafa1af5b560b9d057a464409ba9f8ac1a0fe274878706f2dedcde";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 012_42_r1 (setting SC-DRIVING-012@42). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 failObservedBehavior; VC-DRIVING-037 failObservedBehavior; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 failObservedBehavior; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item stationaryAt42SecondRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-004. The evidence record of run SC-DRIVING-012@42/r2, the
     * second run of the setting stationaryAt42, in the S1 session
     * 20261121T014447Z; records.json names it run 012_42_r2. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:b5ca27fc175622ca85413169654e4c29274d2294c3af3cdff18453ea635e17f3 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:38d9d3c964856301854d19563ff44483a4d5633adf247a5e40f25ee6fc0434a4; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_012_42_r2/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::stationaryTarget;
    attribute :>> setting = AssistanceSettingIdentity::stationaryAt42;
    attribute :>> runIdentity = "SC-DRIVING-012@42/r2";
    attribute :>> simulatedConfiguration = "sha256:4d8bfd7071bae2ebdbbb0ec897d200bc8a0e9ec3cfa4d5eb0ceef000c859a844 (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "1059.890 s to 1088.740 s of simulation time (sim/out/world_012_42_r2/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:23:40.149843Z to 2026-11-21T02:24:08.999068Z (the simulator host's real clock, sim/out/world_012_42_r2/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_012_42_r2/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_012_42_r2/score_side/run/score/candidate_record.json sha256:b5ca27fc175622ca85413169654e4c29274d2294c3af3cdff18453ea635e17f3; identity recorder log: score/out/score_012_42_r2/score_side/run/score/identityRecorder.jsonl sha256:6648ce0b408ec5ab006df5af0eaf3b24fa999ced61b08032843a1b84c0868cf2; driving commands, warning requests and dropped images at the boundary: score/out/score_012_42_r2/score_side/run/score/score_interface.jsonl sha256:ee515f9a95e5bfcc893f5991df79daf43a02c4dc7590d91ea8bdd0b24b908899; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_012_42_r2/score_side/run/score/actuationAdapter.jsonl sha256:ae61b893056afcfc8112886432c6cc4f24d98f91e584cb650c65a81be5c664e5; simulator ground truth and control of the vehicle: sim/out/world_012_42_r2/simulator/world.jsonl sha256:65884761a9b7a3973bb7aaba06ea2ebdc29e0a8e21acc3e173255256c9ec4447; warning presentation log: guest/out/capture_012_42_r2/app_record_warning.jsonl sha256:47ee4036978f75fd35337ba432a53a957d1c0fda07b0fc514693bbadd4febc74; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_012_42_r2/score_side/vision_pilot/visionpilot.rrd sha256:62fbc50be65a829f5841b2b9b520bf2b98feae529ebac71892b00aaf0b41573f (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_012_42_r2/chase_view.mp4 sha256:e423f8dbdf0bbd13767970b4617385ab74746fdcc12ee86647efb7c07708f567; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_012_42_r2/score_side/visualization/visualization.mkv sha256:27016132003d5b60cbb3c0261e25dee7280bd24a22a8c970faf18cdc218adc9c";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 012_42_r2 (setting SC-DRIVING-012@42). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 failObservedBehavior; VC-DRIVING-037 failObservedBehavior; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 failObservedBehavior; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item stationaryAt60FirstRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-005. The evidence record of run SC-DRIVING-012@60/r1, the
     * first run of the setting stationaryAt60, in the S1 session
     * 20261121T014447Z; records.json names it run 012_60_r1. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:87b506d65fc0d9cc5a038c7bc8515fdde62aa0bc999fd8291701ce9e640e2112 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:78a27811c978c63dbf5d361b2f02e6942e2dcc43509abb27843695d0ffe5254a; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_012_60_r1/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::stationaryTarget;
    attribute :>> setting = AssistanceSettingIdentity::stationaryAt60;
    attribute :>> runIdentity = "SC-DRIVING-012@60/r1";
    attribute :>> simulatedConfiguration = "sha256:a56b3c6b075fcc12305add006fe1c082fd9f2e2d894401563e63e62dd40f8e4a (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "1228.909 s to 1257.559 s of simulation time (sim/out/world_012_60_r1/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:29:13.076781Z to 2026-11-21T02:29:41.725610Z (the simulator host's real clock, sim/out/world_012_60_r1/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_012_60_r1/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_012_60_r1/score_side/run/score/candidate_record.json sha256:87b506d65fc0d9cc5a038c7bc8515fdde62aa0bc999fd8291701ce9e640e2112; identity recorder log: score/out/score_012_60_r1/score_side/run/score/identityRecorder.jsonl sha256:c8d796e1e58fa1553e977c1011b708f4937aa977f029fca32be3a3b55fd9cfb5; driving commands, warning requests and dropped images at the boundary: score/out/score_012_60_r1/score_side/run/score/score_interface.jsonl sha256:0e866a25b5db84ce7c18d0dab1145470ed624163ec8180d39540ca385093d422; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_012_60_r1/score_side/run/score/actuationAdapter.jsonl sha256:b3b2fc2a9dc8a8525a7925756d788c6bd4eaadd148390ad41b97fff25cc54335; simulator ground truth and control of the vehicle: sim/out/world_012_60_r1/simulator/world.jsonl sha256:c5f7c143986075f9d8ca2b77544f15a013bd83379d73e82ed59a0c0540766f08; warning presentation log: guest/out/capture_012_60_r1/app_record_warning.jsonl sha256:fecbb96d91734017c07c22ce0ddb1f90beee6efa899eeaa0094e7cf54b8f3ca2; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_012_60_r1/score_side/vision_pilot/visionpilot.rrd sha256:93361caef15923c3ff2180e7d27c1e6357900f8a2a15a999a019e8214f77d4d9 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_012_60_r1/chase_view.mp4 sha256:efe4ccbccc8d65fcd9a14f2ec4bf80acdad9626aa3676ce92a67c94561da1d67; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_012_60_r1/score_side/visualization/visualization.mkv sha256:0e1966237c9473baab00b83912b477d92beb8de977cf1ff07259e99b17ecfce3";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 012_60_r1 (setting SC-DRIVING-012@60). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 failObservedBehavior; VC-DRIVING-037 failObservedBehavior; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 failObservedBehavior; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item stationaryAt60SecondRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-006. The evidence record of run SC-DRIVING-012@60/r2, the
     * second run of the setting stationaryAt60, in the S1 session
     * 20261121T014447Z; records.json names it run 012_60_r2. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:87c2e173b12d58da3ea280188f99c0f4787079c62d544fe1979da551a52dda76 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:78a27811c978c63dbf5d361b2f02e6942e2dcc43509abb27843695d0ffe5254a; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_012_60_r2/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::stationaryTarget;
    attribute :>> setting = AssistanceSettingIdentity::stationaryAt60;
    attribute :>> runIdentity = "SC-DRIVING-012@60/r2";
    attribute :>> simulatedConfiguration = "sha256:a56b3c6b075fcc12305add006fe1c082fd9f2e2d894401563e63e62dd40f8e4a (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "1372.040 s to 1400.690 s of simulation time (sim/out/world_012_60_r2/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:34:30.123314Z to 2026-11-21T02:34:58.772193Z (the simulator host's real clock, sim/out/world_012_60_r2/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_012_60_r2/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_012_60_r2/score_side/run/score/candidate_record.json sha256:87c2e173b12d58da3ea280188f99c0f4787079c62d544fe1979da551a52dda76; identity recorder log: score/out/score_012_60_r2/score_side/run/score/identityRecorder.jsonl sha256:2d289589b75dd4b91225a476a69a9ee65e2d270cda176489e8f93075722e3e86; driving commands, warning requests and dropped images at the boundary: score/out/score_012_60_r2/score_side/run/score/score_interface.jsonl sha256:59895e1ce28b70206f5292e5476cff0f294e33d12273ccdf9c2173a372cbad76; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_012_60_r2/score_side/run/score/actuationAdapter.jsonl sha256:1896d7c2057053fa1abe75417a37b5a97048f2611693589fba27c6e25fa1a4b3; simulator ground truth and control of the vehicle: sim/out/world_012_60_r2/simulator/world.jsonl sha256:74805ce5b3a25c8541b3d5957b1cc4b4d3c40f428baee2a161f78326f2846394; warning presentation log: guest/out/capture_012_60_r2/app_record_warning.jsonl sha256:dc96cd8aac7ca8091b7862dd32e7c5b1e0779d2c591c85d40ce680f0e2e8f817; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_012_60_r2/score_side/vision_pilot/visionpilot.rrd sha256:a8252b32d3f4719f1ec95bf33e4a9331ecae16e8c1d7ecf136ae683d8abbe811 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_012_60_r2/chase_view.mp4 sha256:98ab9d734d19a6348bdf59a4f637e19a79498f6068c619bd61b72bb8c322b195; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_012_60_r2/score_side/visualization/visualization.mkv sha256:a81382446a20c5516c1bac8555ce4cf478b480a3baece00325a891b05d21d287";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 012_60_r2 (setting SC-DRIVING-012@60). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 failObservedBehavior; VC-DRIVING-037 failObservedBehavior; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 failObservedBehavior; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item slowerAt30FirstRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-007. The evidence record of run SC-DRIVING-013@30/r1, the
     * first run of the setting slowerAt30, in the S1 session 20261121T014447Z;
     * records.json names it run 013_30_r1. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:aa41f16dea8874c9dc7a690f3976e81a071b9a8720a0bccd43d617deda8bc433 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:7a8ae3e2ca51888130b362d4ac8625afafe86a72af413351c062f3ac5aa63f7a; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_013_30_r1/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::slowerTarget;
    attribute :>> setting = AssistanceSettingIdentity::slowerAt30;
    attribute :>> runIdentity = "SC-DRIVING-013@30/r1";
    attribute :>> simulatedConfiguration = "sha256:f948d31af4137c050559d7823bdb39a7c4db7d785e83ad280a51fc2b72614471 (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "1513.289 s to 1546.639 s of simulation time (sim/out/world_013_30_r1/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:39:40.322771Z to 2026-11-21T02:40:13.632865Z (the simulator host's real clock, sim/out/world_013_30_r1/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_013_30_r1/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_013_30_r1/score_side/run/score/candidate_record.json sha256:aa41f16dea8874c9dc7a690f3976e81a071b9a8720a0bccd43d617deda8bc433; identity recorder log: score/out/score_013_30_r1/score_side/run/score/identityRecorder.jsonl sha256:6d1eb63b73f0091bde2941f0c65f24181b28f6481b8c5e10c95b8f91bf2221a1; driving commands, warning requests and dropped images at the boundary: score/out/score_013_30_r1/score_side/run/score/score_interface.jsonl sha256:340ad7192966fd400612e57d35697b89683e9940db59b0162624a014945a7110; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_013_30_r1/score_side/run/score/actuationAdapter.jsonl sha256:19b9b6e8f82f480cf621687d7b51a6e7c41190495c52a54ffb7f0f7b300ac1a6; simulator ground truth and control of the vehicle: sim/out/world_013_30_r1/simulator/world.jsonl sha256:85d3d71a044ef5cfe2f26815bf73530b4273ada55d07f210b32f0fa795c6bbd1; warning presentation log: guest/out/capture_013_30_r1/app_record_warning.jsonl sha256:efd55a8868e76fb7ef9abbef14a1b49c6895d71bfb92e72ab5dd75ab6c3ba92e; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_013_30_r1/score_side/vision_pilot/visionpilot.rrd sha256:48b19f0f805bf58a42ca6f0422f23f73cc1fefd5ae36ad7ae4ccf9dee9fc1a4a (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_013_30_r1/chase_view.mp4 sha256:104aeece5400f669c77052c85c79af2732b9673f8d35ac046c355e91f7b36959; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_013_30_r1/score_side/visualization/visualization.mkv sha256:0600635ccc7cf8c98c22e286c3a15015a404affb9cd6043dfea14a4278e2bc47";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 013_30_r1 (setting SC-DRIVING-013@30). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 passBoundedVerification; VC-DRIVING-037 passBoundedVerification; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 passBoundedVerification; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item slowerAt30SecondRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-008. The evidence record of run SC-DRIVING-013@30/r2, the
     * second run of the setting slowerAt30, in the S1 session 20261121T014447Z;
     * records.json names it run 013_30_r2. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:009ccfbcbf35a1b6ddc710754a7378a7c36cb5e1e960462368e71e0fe262445b (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:7a8ae3e2ca51888130b362d4ac8625afafe86a72af413351c062f3ac5aa63f7a; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_013_30_r2/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::slowerTarget;
    attribute :>> setting = AssistanceSettingIdentity::slowerAt30;
    attribute :>> runIdentity = "SC-DRIVING-013@30/r2";
    attribute :>> simulatedConfiguration = "sha256:f948d31af4137c050559d7823bdb39a7c4db7d785e83ad280a51fc2b72614471 (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "1701.999 s to 1705.049 s of simulation time (sim/out/world_013_30_r2/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:45:25.432840Z to 2026-11-21T02:45:28.443046Z (the simulator host's real clock, sim/out/world_013_30_r2/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_013_30_r2/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_013_30_r2/score_side/run/score/candidate_record.json sha256:009ccfbcbf35a1b6ddc710754a7378a7c36cb5e1e960462368e71e0fe262445b; identity recorder log: score/out/score_013_30_r2/score_side/run/score/identityRecorder.jsonl sha256:68ffe31889fc69b3a3f9ee9e69e9746defedf773764461318c10b7725b50afbf; driving commands, warning requests and dropped images at the boundary: score/out/score_013_30_r2/score_side/run/score/score_interface.jsonl sha256:f9eb9f46a56d57c58513bcf16eaed5cbb331291428c5451ed271b8cb58a063db; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_013_30_r2/score_side/run/score/actuationAdapter.jsonl sha256:c0e912c959c7c52982fd86916b886dc50093107579cfcb716c8b33d0a43b66af; simulator ground truth and control of the vehicle: sim/out/world_013_30_r2/simulator/world.jsonl sha256:62ea60bd7d438fbb40a2246045cbbdffc70afd14717200e39af3cd5d2061e7bf; warning presentation log: guest/out/capture_013_30_r2/app_record_warning.jsonl sha256:dee1995eac0bafed97df43a0ecfc8080b7e7cef47bd69390ad2b7d0044a56982; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_013_30_r2/score_side/vision_pilot/visionpilot.rrd sha256:af7d5a67476547f0b08bea2673efa313858daf4ad8e4eb7d52d6058cd716c425 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_013_30_r2/chase_view.mp4 sha256:b9ca1fb30409be9bf80ccc159090472aea6684f459344c3ee80183510e2479e1; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_013_30_r2/score_side/visualization/visualization.mkv sha256:2c82cde010377eb3f95670d6c5adc1829441c2e037d28580b62567ef823f5467";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 013_30_r2 (setting SC-DRIVING-013@30). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 inconclusiveMissingEvidence; VC-DRIVING-037 inconclusiveMissingEvidence; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 inconclusiveMissingEvidence; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item slowerAt60FirstRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-009. The evidence record of run SC-DRIVING-013@60/r1, the
     * first run of the setting slowerAt60, in the S1 session 20261121T014447Z;
     * records.json names it run 013_60_r1. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:5ecd2778f1ff87a1cdd16059fbf3d9ab3ec3443b828229b24c3fc880304714e4 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:78a27811c978c63dbf5d361b2f02e6942e2dcc43509abb27843695d0ffe5254a; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_013_60_r1/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::slowerTarget;
    attribute :>> setting = AssistanceSettingIdentity::slowerAt60;
    attribute :>> runIdentity = "SC-DRIVING-013@60/r1";
    attribute :>> simulatedConfiguration = "sha256:f7efdd24c2f39a9943b8770c59a0691802a68b93befda18fb2aa5658879870dd (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "1817.945 s to 1844.595 s of simulation time (sim/out/world_013_60_r1/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:49:51.767753Z to 2026-11-21T02:50:18.378294Z (the simulator host's real clock, sim/out/world_013_60_r1/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_013_60_r1/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_013_60_r1/score_side/run/score/candidate_record.json sha256:5ecd2778f1ff87a1cdd16059fbf3d9ab3ec3443b828229b24c3fc880304714e4; identity recorder log: score/out/score_013_60_r1/score_side/run/score/identityRecorder.jsonl sha256:00b5cddf26f7dd313de4ffa405380b08d820988adfb49cff2a98385f365e5c21; driving commands, warning requests and dropped images at the boundary: score/out/score_013_60_r1/score_side/run/score/score_interface.jsonl sha256:6f8fb3b59e4da212d2e1858e5df28c7b80d963e3596c6d828cb343fd1768d7ba; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_013_60_r1/score_side/run/score/actuationAdapter.jsonl sha256:1d044c1c502a1c1fa89f90634cd5192c54e85105c3ac34c778fb0440955adbde; simulator ground truth and control of the vehicle: sim/out/world_013_60_r1/simulator/world.jsonl sha256:1ddf4e640413280e78fd69fa8b44ed19cf8794e8698f563a6247f8fbbe33bab5; warning presentation log: guest/out/capture_013_60_r1/app_record_warning.jsonl sha256:bf53b98dac2aad51fc85b4edb656690c529d4a6dd83862f8407c70878f8e015b; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_013_60_r1/score_side/vision_pilot/visionpilot.rrd sha256:828a9ccc738147d4025a397a9451e94aa65371a599bfca65b6f2944491e1c347 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_013_60_r1/chase_view.mp4 sha256:af991d2b33b40dd1e03425aa0d8927aa6b17b9bba1fe3f0b70c76961179f6a4c; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_013_60_r1/score_side/visualization/visualization.mkv sha256:e8e77327d865f5bc514d7b505dc215181ed8c89e9978114846ff026109d50efc";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 013_60_r1 (setting SC-DRIVING-013@60). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 inconclusiveMissingEvidence; VC-DRIVING-037 inconclusiveMissingEvidence; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 inconclusiveMissingEvidence; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item slowerAt60SecondRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-010. The evidence record of run SC-DRIVING-013@60/r2, the
     * second run of the setting slowerAt60, in the S1 session 20261121T014447Z;
     * records.json names it run 013_60_r2. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:335fdf3944cff78101ad5bce957139b5af7a945905c9c68a53ffb3900b44102b (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:78a27811c978c63dbf5d361b2f02e6942e2dcc43509abb27843695d0ffe5254a; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_013_60_r2/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::slowerTarget;
    attribute :>> setting = AssistanceSettingIdentity::slowerAt60;
    attribute :>> runIdentity = "SC-DRIVING-013@60/r2";
    attribute :>> simulatedConfiguration = "sha256:f7efdd24c2f39a9943b8770c59a0691802a68b93befda18fb2aa5658879870dd (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "1967.717 s to 1970.767 s of simulation time (sim/out/world_013_60_r2/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:54:53.926869Z to 2026-11-21T02:54:56.937581Z (the simulator host's real clock, sim/out/world_013_60_r2/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_013_60_r2/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_013_60_r2/score_side/run/score/candidate_record.json sha256:335fdf3944cff78101ad5bce957139b5af7a945905c9c68a53ffb3900b44102b; identity recorder log: score/out/score_013_60_r2/score_side/run/score/identityRecorder.jsonl sha256:d1dfcfae8528bf44ecf6cb473860fcd1e3fda8589e9d26eea1313fc64fe538df; driving commands, warning requests and dropped images at the boundary: score/out/score_013_60_r2/score_side/run/score/score_interface.jsonl sha256:c63488576292ee1371e480986b11edd64df2311209b08e726186119d961d6028; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_013_60_r2/score_side/run/score/actuationAdapter.jsonl sha256:2986fe60b6e3cc85f0c2073904c2e604996ce457dd2128ad5d0ca76f71895f2b; simulator ground truth and control of the vehicle: sim/out/world_013_60_r2/simulator/world.jsonl sha256:a05cd8d9788af4d6e31acc2eda046c3f44a8b8100ea4ec1be0adfe5b447fea4c; warning presentation log: guest/out/capture_013_60_r2/app_record_warning.jsonl sha256:5b5521d27827f8d5ca5fc69dc18b47f85db3ecffda4e2ff5d84a92cb3e2d335d; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_013_60_r2/score_side/vision_pilot/visionpilot.rrd sha256:44e4b79911cd49af0f37316af28e40bc4ef53bf75cfc806f2786fbb025a8f7f5 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_013_60_r2/chase_view.mp4 sha256:6f4bb91e179b6fcd4aad8606cb23a62d811b1119f692381532a723d889d626c7; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_013_60_r2/score_side/visualization/visualization.mkv sha256:ee8830845f100aa7fa566dae1c25e965491abb42bc346aacd92c04c0ff48d819";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 013_60_r2 (setting SC-DRIVING-013@60). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-036 inconclusiveMissingEvidence; VC-DRIVING-037 inconclusiveMissingEvidence; VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-042 inconclusiveMissingEvidence; VC-DRIVING-043 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item curveAt30FirstRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-011. The evidence record of run SC-DRIVING-014@30/r1, the
     * first run of the setting curveAt30, in the S1 session 20261121T014447Z;
     * records.json names it run 014_30_r1. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:3d85ec65f38ff2c8c61f15434883129edc51509578ed74f1510c35f86041095e (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:61c8615866031519c3443ba8906094bd323b22494cd6d7831a9623ca96373c85; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_014_30_r1/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::curveWithGuardPipes;
    attribute :>> setting = AssistanceSettingIdentity::curveAt30;
    attribute :>> runIdentity = "SC-DRIVING-014@30/r1";
    attribute :>> simulatedConfiguration = "sha256:df3fdd9e07a8c1dae7e7acc3b6442ac2794a0eeda93866f6c0de9d28d0df59cd (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "2093.691 s to 2118.291 s of simulation time (sim/out/world_014_30_r1/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T02:59:31.565588Z to 2026-11-21T02:59:56.164755Z (the simulator host's real clock, sim/out/world_014_30_r1/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_014_30_r1/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_014_30_r1/score_side/run/score/candidate_record.json sha256:3d85ec65f38ff2c8c61f15434883129edc51509578ed74f1510c35f86041095e; identity recorder log: score/out/score_014_30_r1/score_side/run/score/identityRecorder.jsonl sha256:af1af8141a4319d94df32db1b96ea2e926489df35c8669a004e41a5dcf534f90; driving commands, warning requests and dropped images at the boundary: score/out/score_014_30_r1/score_side/run/score/score_interface.jsonl sha256:f5f6afbdff3d990aa7a79fefcd6fc5ce0cc833e719e3c2551f27e88e354b4169; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_014_30_r1/score_side/run/score/actuationAdapter.jsonl sha256:ae117c76de6a23338d131a6dd9e97218322e1b65b2b83264b6a743e7df4138f1; simulator ground truth and control of the vehicle: sim/out/world_014_30_r1/simulator/world.jsonl sha256:ae838769e2fd7997bf594cdba5d345a609ac215a5c8d813d4e759831aa6de2d5; warning presentation log: guest/out/capture_014_30_r1/app_record_warning.jsonl sha256:85521eaeb0bb0f3cbe8447508a86f8dd3b0ca151bf131b7eadc99e7962aa7dad; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_014_30_r1/score_side/vision_pilot/visionpilot.rrd sha256:3f2d7556aa403dfb4249171243452e9e5ef079487c52d6764c625bbb3f16edab (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_014_30_r1/chase_view.mp4 sha256:2417cb7a6860b4000fe523e089c212c504f08207f23228673ea3d2292388149b; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_014_30_r1/score_side/visualization/visualization.mkv sha256:e70868af3d49a9522378ec7f5881ee1619ed0c7612c4ee4bd15782e66ad5cf18";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 014_30_r1 (setting SC-DRIVING-014@30). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item curveAt30SecondRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-012. The evidence record of run SC-DRIVING-014@30/r2, the
     * second run of the setting curveAt30, in the S1 session 20261121T014447Z;
     * records.json names it run 014_30_r2. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:091e3e0b496dbff9b07deb8fbad5844fe26f55a008e69061d4bf9430f3c76367 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:61c8615866031519c3443ba8906094bd323b22494cd6d7831a9623ca96373c85; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_014_30_r2/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::curveWithGuardPipes;
    attribute :>> setting = AssistanceSettingIdentity::curveAt30;
    attribute :>> runIdentity = "SC-DRIVING-014@30/r2";
    attribute :>> simulatedConfiguration = "sha256:df3fdd9e07a8c1dae7e7acc3b6442ac2794a0eeda93866f6c0de9d28d0df59cd (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "2231.321 s to 2291.321 s of simulation time (sim/out/world_014_30_r2/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T03:04:11.387567Z to 2026-11-21T03:05:11.386772Z (the simulator host's real clock, sim/out/world_014_30_r2/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_014_30_r2/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_014_30_r2/score_side/run/score/candidate_record.json sha256:091e3e0b496dbff9b07deb8fbad5844fe26f55a008e69061d4bf9430f3c76367; identity recorder log: score/out/score_014_30_r2/score_side/run/score/identityRecorder.jsonl sha256:6da32fe226b93dca13a7db92c1b45b77354b4369125968ffe2b687a3724c4cab; driving commands, warning requests and dropped images at the boundary: score/out/score_014_30_r2/score_side/run/score/score_interface.jsonl sha256:3d3eacc792026e7789e4c65667b21ecccef5b8fc0cf72d6219b6464b1dc3af62; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_014_30_r2/score_side/run/score/actuationAdapter.jsonl sha256:28b7c167b0bc4a50b8029a0dc2e7a79dc4d7e57c267e5c133648e4d40c9f8836; simulator ground truth and control of the vehicle: sim/out/world_014_30_r2/simulator/world.jsonl sha256:7a5ea1c3ac95413195739bb25062445c4ef98675e9e7640489037d2d9129341d; warning presentation log: guest/out/capture_014_30_r2/app_record_warning.jsonl sha256:c4300aa84d08fcb2d847f5c8b012ebc93802e6881e905286b320ca485e19ebc9; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_014_30_r2/score_side/vision_pilot/visionpilot.rrd sha256:f0615eec8531a8a2c7395636fa93d6976642a82c65e79f055653383242f24d84 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_014_30_r2/chase_view.mp4 sha256:837761c8e4dcb5193c2605716175263a1315fe0dee6db077a75a5d526e1d4b2a; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_014_30_r2/score_side/visualization/visualization.mkv sha256:99ac5ac4840e8f6abd0b9ac65be96c52bd04da332d8e597ef1dc20cc03c0c844";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 014_30_r2 (setting SC-DRIVING-014@30). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item turningOffAt40FirstRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-013. The evidence record of run SC-DRIVING-015@40/r1, the
     * first run of the setting turningOffAt40, in the S1 session
     * 20261121T014447Z; records.json names it run 015_40_r1. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:21b98369586ff3dd81ffaf6748f3e8a603dbb4b05eef1ddeec969ca04c2087a3 (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:794fb49e1842a1b2f4e1686da012e48247e72bca1756bc1c76f19be5d97f4d21; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_015_40_r1/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::vehicleTurningOff;
    attribute :>> setting = AssistanceSettingIdentity::turningOffAt40;
    attribute :>> runIdentity = "SC-DRIVING-015@40/r1";
    attribute :>> simulatedConfiguration = "sha256:e0bdbd61343b7611ab4cdc9c374896a6b1e8ac0d3aec48974b20eadba96b216d (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "2437.692 s to 2512.692 s of simulation time (sim/out/world_015_40_r1/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T03:10:00.767607Z to 2026-11-21T03:11:15.766158Z (the simulator host's real clock, sim/out/world_015_40_r1/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_015_40_r1/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_015_40_r1/score_side/run/score/candidate_record.json sha256:21b98369586ff3dd81ffaf6748f3e8a603dbb4b05eef1ddeec969ca04c2087a3; identity recorder log: score/out/score_015_40_r1/score_side/run/score/identityRecorder.jsonl sha256:3a05a9e8c0309e178d7e2b745b3762480d15cf071c621a12b55536c41261b258; driving commands, warning requests and dropped images at the boundary: score/out/score_015_40_r1/score_side/run/score/score_interface.jsonl sha256:182bfd7d62bccd62babea87498b1cae5e79123e4202a23128037c7b2b6239cb7; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_015_40_r1/score_side/run/score/actuationAdapter.jsonl sha256:b24c4ed5076e8bf5522b7f00203fa9da8740c3d89b116aa30b1bdc8d96d91a93; simulator ground truth and control of the vehicle: sim/out/world_015_40_r1/simulator/world.jsonl sha256:b4a7b9478178036f2a4023ea2c0a4e985c3f5e40fbbb55a789cc92f9a73bc6f8; warning presentation log: guest/out/capture_015_40_r1/app_record_warning.jsonl sha256:d922910a647285ab3c9e1ba00f25a77768b713517492507db392bca0d827c3e7; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_015_40_r1/score_side/vision_pilot/visionpilot.rrd sha256:4726a6f5043cbf5527e7eb6361f8f2cfe6306e10015e45f00fc457b7d4869a3f (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_015_40_r1/chase_view.mp4 sha256:e4fc5c96517b2bbd80e894af2b87bc64a92b7796a46905214f7046edb4953e78; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_015_40_r1/score_side/visualization/visualization.mkv sha256:74a2a47c51c0c9cc76e0a51c6a967c1e4ceba734c7fadd99181e0aee48185c19";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 015_40_r1 (setting SC-DRIVING-015@40). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item turningOffAt40SecondRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-014. The evidence record of run SC-DRIVING-015@40/r2, the
     * second run of the setting turningOffAt40, in the S1 session
     * 20261121T014447Z; records.json names it run 015_40_r2. The record is
     * complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:fe1c62ee8a1fdb1f1c891ba7d992e0c43d057c12303983e8ae8f315f331a4b6a (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:794fb49e1842a1b2f4e1686da012e48247e72bca1756bc1c76f19be5d97f4d21; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_015_40_r2/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::vehicleTurningOff;
    attribute :>> setting = AssistanceSettingIdentity::turningOffAt40;
    attribute :>> runIdentity = "SC-DRIVING-015@40/r2";
    attribute :>> simulatedConfiguration = "sha256:e0bdbd61343b7611ab4cdc9c374896a6b1e8ac0d3aec48974b20eadba96b216d (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "2645.687 s to 2720.687 s of simulation time (sim/out/world_015_40_r2/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T03:15:51.297749Z to 2026-11-21T03:17:06.295799Z (the simulator host's real clock, sim/out/world_015_40_r2/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_015_40_r2/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_015_40_r2/score_side/run/score/candidate_record.json sha256:fe1c62ee8a1fdb1f1c891ba7d992e0c43d057c12303983e8ae8f315f331a4b6a; identity recorder log: score/out/score_015_40_r2/score_side/run/score/identityRecorder.jsonl sha256:f1c55ebbf2a069b608b53d134a4997f4b006db5896eabc67f1d30a1787d65f54; driving commands, warning requests and dropped images at the boundary: score/out/score_015_40_r2/score_side/run/score/score_interface.jsonl sha256:02f04a24dfc2d18b787339a7e0a271fea4daf3714eb1b05af35c3af09ebcecfe; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_015_40_r2/score_side/run/score/actuationAdapter.jsonl sha256:0c2276afa5c68ef19afe1a578f57b06b0d3ad1b0471dd7dcc2917c4fecf1c6f8; simulator ground truth and control of the vehicle: sim/out/world_015_40_r2/simulator/world.jsonl sha256:a8b710de7c5a8f44e2df9b3309a611bc65923b08e3a9f1bcddc7b78f179869fb; warning presentation log: guest/out/capture_015_40_r2/app_record_warning.jsonl sha256:57ffc540d98f6100286e1004124eb2cae8a693f60052f0c7d1bfd9f890aaf2c9; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_015_40_r2/score_side/vision_pilot/visionpilot.rrd sha256:59c1592c32790855da2adbf24fcd4010523a56832bfcd84d924124e66e9becb7 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_015_40_r2/chase_view.mp4 sha256:b5685516f36136475089c6cba8812499f2b49d141178ef51deee2be9902ac113; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_015_40_r2/score_side/visualization/visualization.mkv sha256:e3c1d298c837325d253ac98d05d1e6acfc4a46ebd3e8b0ab8c70c6ca8490fcc3";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run 015_40_r2 (setting SC-DRIVING-015@40). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-038 inconclusiveMissingEvidence; VC-DRIVING-040 inconclusiveMissingEvidence; VC-DRIVING-041 inconclusiveMissingEvidence; VC-DRIVING-044 inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item pathStoppedRunEvidence : RetainedAssistanceRunEvidence {
    doc /*
     * EVID-DRIVING-015. The evidence record of run stop/further, the further
     * run of SC-DRIVING-012 in which the Eclipse S-CORE path of the
     * driver-assistance system is stopped, which is no run of a setting, so
     * setting is left empty as the record's rule says, in the S1 session
     * 20261121T014447Z; records.json names it run stop. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "508649bae2543c181d3edbe3f63eeeaa3b836d28";
    attribute :>> candidateRecordIdentity = "sha256:7e37b53e8105e852128233401407cca723b40df8962087d2e805d41c7623412a (/tmp/de4sdv-da-bench/run/score/candidate_record.json, 157983 B)";
    attribute :>> upstreamRevision = "014e0e7a56ee8e597c2cab8175233f74edd9b856";
    attribute :>> sourceDifference = "sha256:d55b53c6d4fb12ae604ff882ca8da52cbd9a4ea25ec6b3f55c4aa7d081488cfd, 117845 B: 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff";
    attribute :>> networkFileSha256 = "network autodrive autodrive_fp32.onnx sha256:196a82289ba7d96f574cc4dfa8815dadb9f104397c7c2bec7c98333e5ee8762d; network autosteer autosteer_fp32.onnx sha256:770d26f431467bbcc7fe3e794411cac36d8dfbd1658e4eb4a37d48342db7cbf6; network autospeed autospeed_fp32.onnx sha256:adff7dd9fa9c2d306d9228a87edcf2ae256edbdc9e4b9541fd471880aa5c1451";
    attribute :>> configurationFileSha256 = "vision_pilot.conf vision_pilot.conf sha256:ae60bd5692ddc954901224b50e1293921ab0d847d18db3d64d0875c1ef3243fb; H.yaml H.yaml sha256:89e291df9711abf801b56a1b489b629b7c3ae8fed6b6f8e0e9208869633d4fe2; homography_C_matrix.yaml homography_C_matrix.yaml sha256:fedabc3403d6cdc1644e1073b02ca69b6b8ed591953e3801268db6cf9ebfc149; DE4SDV interface configuration de4sdv_score_interface.conf sha256:d5e9e84b05621971cf3761172f159cd1d8f3191441b1ea8f1fe2c7cf897e4778; mw::com manifest of vision_pilot mw_com_config_vision_pilot.json sha256:b2d589ddbcdce96161cde055f9ceb7f5925b3346ae62b3ae621f583fdb5a94e8; Launch Manager configuration launch_manager_config.json sha256:58398ffbf4ab10f03d1d2dc44b88bbeb5324f14372ef4c3a86fe8b798dafd783; Launch Manager configuration (serialized) launch_manager_config.bin sha256:94de34c8fa0ae6ddb9367860721361eaecc22d3d9f5f2b7388de2e3a3d4b42e0; MW_COM_CONFIG of identity_recorder mw_com_config_identity_recorder.json sha256:eee5c172eb48319f2a438e45a5194af26c2ec92a33ea22cc79b4c36242230e2e; process argument of someipd mw_com_config_someipd_warning.json sha256:6ba889890d6817a6bcdb45ca4276cc003ec1d00887cc439a31553853a4d2d2cb; VSOMEIP_CONFIGURATION of someipd vsomeip_someipd_warning.json sha256:03e0292f639abd9d78025561303156058b0fe7461f6d18262c001e396ea29adc; process argument of gatewayd someip_gateway_config_warning.bin sha256:7c0282216f6a66ca0eb623cb4b620e883abb16108ed187b14f1b86495f063f85; process argument of gatewayd mw_com_config_gatewayd_warning.json sha256:5d0b481d730fde31f19e0279ff2a07b6dad68f138988531da2d1a8a9921e0957; process argument of actuation_adapter adapter.json sha256:924b98c0a2a86138e6eacdf7440c65223034da4056783c361ae3d41cd0a7426b; MW_COM_CONFIG of actuation_adapter mw_com_config_actuation_adapter.json sha256:fcd8bf4156619bd287f7cb1226484d719d263052e70499f23b424ae8bb4bcbfa; ldconfig conf of the GPU runtime de4sdv-cuda-12.8.1.conf sha256:aaccd9d47011ead5d6c995724d56d4618040d4f526e14a0b5a964bc3cf17bef2";
    attribute :>> launchSettings = "sha256:f473223782d52cca76748518430d8f3698be005add1a09c0291d647c564fc79d of candidate_record.json launch_settings (canonical JSON; verbatim in that record): /tmp/de4sdv-da-bench/config/launch_manager_config.json, 5 components";
    attribute :>> candidateBuild = "pin at 014e0e7a56ee8e597c2cab8175233f74edd9b856 with 0001-de4sdv-visualization-recorder.diff, 0002-de4sdv-score-interface.diff, 0003-de4sdv-headless-display.diff, 0005-de4sdv-warm-start.diff; bundle /opt/da-b2/bundle (session.json candidate)";
    attribute :>> visualizationRecorderDelay = "the readiness probe of the recorder on 2026-11-17 measured 2.0 ms more at the median and 5.8 ms more at the 99th percentile from an image to its command, on an S-CORE host with an NVIDIA L4 (textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:170-176 at 508649bae2543c181d3edbe3f63eeeaa3b836d28 (RetainedAssistanceRunEvidence))";
    attribute :>> scoreLifecycleVersion = "score_lifecycle@0.10.0";
    attribute :>> scoreCommunicationVersion = "score_communication@0.6.0";
    attribute :>> scoreSOMEIPGatewayCommit = "d9eac670b7534352749da3d30f52aebf5129f168";
    attribute :>> simulatorBuild = "1.0-14ac3b1a5 (CARLA server, sim/out/world_stop/simulator/setting_record.json simulator.versions.server)";
    attribute :>> scenario = AssistanceScenarioIdentity::stationaryTarget;
    attribute :>> setting;
    attribute :>> runIdentity = "stop/further";
    attribute :>> simulatedConfiguration = "sha256:6844e065726c1749518f22c388c84713d917e53faaf74dd19cf5d54bfa5f3f35 (sha256 of the canonical JSON of {setting: the setting's record, files: {path: sha256}} (session/scenario_digest.py); world-side/da_world_side.py, world-side/scenarios.py, world-side/scripts/common.sh, world-side/sites.py)";
    attribute :>> simulationClockSpan = "2855.010 s to 2897.010 s of simulation time (sim/out/world_stop/simulator/world.jsonl data.simTimeS, first to last tick)";
    attribute :>> wallClockSpan = "2026-11-21T03:21:42.497897Z to 2026-11-21T03:22:24.496792Z (the simulator host's real clock, sim/out/world_stop/simulator/world.jsonl t_real_ns)";
    attribute :>> executionEnvironmentIdentity = "simulator host 10.10.0.2; S-CORE host 10.164.0.5 with NVIDIA L4, driver 580.178.04; guest host 10.164.0.6: SDV Core image sdv_core_cf, build CP2A.260605.016, fingerprint google/sdv_core_cf/sdv_core_cf:17/CP2A.260605.016/eng.mrk:eng/test-keys, vbmeta digest df609afcf639bb3f47d97edf05c5c16c8c92c57c463aff2d5eeadd71cb954299, IVI image sdv_ivi_cf, build CP2A.260605.016, fingerprint google/sdv_ivi_cf/sdv_ivi_cf:17/CP2A.260605.016/eng.mrk:userdebug/test-keys, vbmeta digest d668fcbb41024f3a946e97bd5c05a92d328cc1a11c9ebe408f4d32d938abeef8";
    attribute :>> contractIdentity = "de4sdv.driving.v1.CollisionWarningRequest (unit de4sdv-driving-warning-request, REFLECTION at the SDV Core SOME/IP broker; guest/out/capture_stop/app_record_warning.jsonl lifecycle)";
    attribute :>> criteriaRecordIdentity = "sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136";
    attribute :>> evaluatorRevision = "blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68";
    attribute :>> rawObservationArtifact = "candidate identity record: score/out/score_stop/score_side/run/score/candidate_record.json sha256:7e37b53e8105e852128233401407cca723b40df8962087d2e805d41c7623412a; identity recorder log: score/out/score_stop/score_side/run/score/identityRecorder.jsonl sha256:3077106fe8b4d7d082fce7c48b4081e94293262d040d039e55a23f75f795333e; driving commands, warning requests and dropped images at the boundary: score/out/score_stop/score_side/run/score/score_interface.jsonl sha256:8cb635a687c195da4ff294c079b7c427e835f62c7ff3f871977bcb817b546c05; actuation adapter log (with the boundary records: the communication records of the S-CORE path): score/out/score_stop/score_side/run/score/actuationAdapter.jsonl sha256:6b64334514cfdf65d40dcf72054706b94c6824d5d7843975f35e2ca7bffefc62; simulator ground truth and control of the vehicle: sim/out/world_stop/simulator/world.jsonl sha256:07509332e3178ae62b8cc846e6ece28b9622a6a436eb08e3b229dca5f0f4f8ae; warning presentation log: guest/out/capture_stop/app_record_warning.jsonl sha256:859d975556b415c08538bd5eb71d8c10392f64db67e6f43b1b84c537f97f5411; candidate's data log: /home/mrk/da-kit/20261121T014447Z/out/score_stop/score_side/vision_pilot/visionpilot.rrd sha256:93f9bc26bf97dfe02ae771d72919fc24bff42173cd6a46a2ddde2ebc0c85f662 (kept on the S-CORE host)";
    attribute :>> benchRecordingArtifact = "chase view sim/out/rec_stop/chase_view.mp4 sha256:0df8fd50ba2cba5194879a48f4e0d578cf55b7d4ac78b3b9c46e415b2b53173b; the candidate's visualization recording /home/mrk/da-kit/20261121T014447Z/out/score_stop/score_side/visualization/visualization.mkv sha256:4c21a3959db7e588d8b21d33f6aef025c4217686207bb49f7aee7f2ce11653e3";
    attribute :>> independentEngineerIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's notes";
    attribute :>> claimBoundary = "Run stop (the further run, no run of a setting). The record supports only these outcomes of the run, each under the named criteriaRecordIdentity and evaluatorRevision: VC-DRIVING-038 stop clause inconclusiveMissingEvidence; VC-DRIVING-043 stop clause inconclusiveMissingEvidence. It does not prove: validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; that a driver perceives the warning; the candidate's behavior outside the settings and the runs recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of the simulated deceleration.";
  }

  item commandFormAnalysisEvidence : RetainedCommandFormAnalysis {
    doc /*
     * EVID-DRIVING-016. The record of the desk analysis of REQ-DRIVING-039,
     * written from analysis_039.json. The record is complete.
     */
    attribute :>> configurationIdentity = "DRIVING-CONFIG-002";
    attribute :>> receiptSha256 = "848262167497d033b87d4ae90c6f54d3b0edd4c851f80480cd07d8cd860a34a1";
    attribute :>> modelRevision = "29750f4662035f16259b87303b504d344445bc1e";
    attribute :>> analyzedRealization = "textual-notation-of-model/packages/features/driving/driver_assistance_physical_software_realization.sysml at 29750f4662035f16259b87303b504d344445bc1e: item def DrivingCommandEventPayload (lines 232-248), the mapping record MAP-DRIVING-DA-COMMAND drivingCommandMappingRecord (lines 1065-1084) and the comment reqDetectableDrivingCommandRejection (lines 1273-1289); read with them, because the comment and the mapping refer to them: part def DrivingCommandActuationAdapter (lines 603-652) and the vehicle interface doc of the candidate's process (lines 470-485)";
    attribute :>> analystIdentity = "an independent Claude Code session dispatched by the lead on 2026-11-21, with no access to the lead's reasoning";
    attribute :>> claimBoundary = "The analysis makes no freedom-from-interference claim. It reads the phase 8 realization at the named model revision and no run: it shows the part of the driving command that the model names for each of a loss, a delay, a repetition and a corruption on the Eclipse S-CORE path, and the rule by which the actuation adapter detects each; it shows no built program detecting anything. The detection it shows is bounded: a loss is detected only when a later command arrives; a delay only beyond 0.1 s of simulation time against the adapter's newest world time; a corruption only as far as the CRC-32 detects it, for which the model states no residual rate. The detection and the rejection sit in the actuation adapter, a context realization outside the candidate; the candidate's share is the form of the command.";
  }

  part def DriverAssistanceVerificationBench {
    doc /*
     * The bench of the verification cases of INC-DRIVING-002. System 1 is the
     * configured product DRIVING-CONFIG-002, which the bench refers to and does
     * not own. assistanceSoftware is its realization of the driver-assistance
     * system, the system of interest: the subject that each verified
     * requirement binds. The System 2 test environment is the framing's
     * driverAssistanceVerificationEnvironment, on the three hosts of phase 8;
     * GAP-DRIVING-014 records what of its readiness the judged session S1 shows
     * and what stays open. The bench is not a product selection.
     */
    ref part system1ConfiguredProduct :> DE4SDV_DriverAssistanceVariabilityConfiguration::configuredProduct;
    ref part assistanceSoftware :> DE4SDV_DriverAssistanceFraming::candidateDriverAssistanceSystem = system1ConfiguredProduct.assistanceSoftware;
  }

  part driverAssistanceVerificationBench : DriverAssistanceVerificationBench;

  part <'GAP-DRIVING-014'> gapAssistanceVerificationEnvironmentOpen : IncrementGap {
    doc /*
     * Recorded: the System 2 test environment ran the cases in the judged
     * session S1, and what of its readiness S1 does not show stays open. Phase
     * 8 placed the bench on three hosts: the S-CORE host with its NVIDIA L4,
     * the simulator host with its NVIDIA RTX PRO 6000 and CARLA 1.0 at the
     * fixed step of 0.05 s, and the guest host with the SDV Core VM and the IVI
     * VM. The readiness items that phase 8 left open continued here;
     *
     * S1 answers them so (the environment decision of 2026-11-21, continuing
     * the evidence decisions of 2026-11-18): the link of the S-CORE process
     * with the build of ONNX Runtime for CUDA: shown, the candidate's process
     * runs its networks with ONNX Runtime for CUDA under the Launch Manager in
     * every run of S1 (the Launch Manager log of each run,
     * score_side/state/launch_manager.log); whether that process may hold a
     * second C++ standard library: settled by the build that ran, whose files
     * each run's score_side/state/staging.json lists; that the candidate record
     * reaches the vehicle interface, which subscribes after the record was
     * published: shown, the score-interface record of each run holds the
     * candidate record's arrival (in.candidate_record in
     * score_side/run/score/score_interface.jsonl); the candidate driving on
     * CARLA 1.0: shown, it drove every run of S1 there (simulatorBuild of each
     * run record); the typed message of the warning request on the guests:
     * shown, the message type that contractIdentity of each run record names
     * reached the warning presentation on the IVI guest in every run
     * (guest/out/capture_<run>/app_record_warning.jsonl); the calibration runs
     * of ASM-DRIVING-005 and ASM-DRIVING-006 came before the first judged run
     * (sim/out/calibrate/calib_decel and the steering calibration run
     * calib_steer); what they show is in the values of VC-DRIVING-036 and
     * VC-DRIVING-037; whether the S-CORE host's own GPU keeps the candidate's
     * cycle with the S-CORE build: answered no: the score-interface record of
     * each run of S1 holds dropped camera images, which drop_counts.json of the
     * evidence directory places by their simulation time. Each of the 14 runs
     * of SC-DRIVING-012 to SC-DRIVING-015 drops 23 or 24 images in the first 5
     * s after its first image; 2 to 6 in the last 0.6 s of its image stream,
     * which goes on after the run's last world tick until the S-CORE side
     * stops; and 0 to 3 isolated images in between: SC-DRIVING-012@20/r1 at
     * 36.8 and 41.9 s, SC-DRIVING-012@42/r2 at 26.4 s, SC-DRIVING-012@60/r2 at
     * 15.7 and 32.0 s, SC-DRIVING-013@30/r1 at 31.6 s, SC-DRIVING-014@30/r1 at
     * 21.5 s, SC-DRIVING-014@30/r2 at 26.4 and 61.5 s, SC-DRIVING-015@40/r1 at
     * 36.4, 51.4 and 76.5 s, SC-DRIVING-015@40/r2 at 41.4 and 76.5 s after the
     * first image, and none in SC-DRIVING-012@20/r2, SC-DRIVING-012@42/r1,
     * SC-DRIVING-012@60/r1, SC-DRIVING-013@30/r2, SC-DRIVING-013@60/r1 or
     * SC-DRIVING-013@60/r2. The run that stops the path drops 24 in its first 5
     * s and 8 in the last 0.8 s of its image stream, which ends at the stop,
     * and the steering calibration run 34 in its first 5 s, 3 at the end of its
     * image stream and 6 isolated. The warm start of D-S1-1 (patch 0005 of the
     * bench) ran before the attach in every run: the Launch Manager log of each
     * run records 2 passes with the result yes, in 678.3 to 706.8 ms
     * (score_side/state/launch_manager.log); it did not keep the first 5 s
     * after the first image free of dropped images. The records show no cause
     * of the drops. The evaluators judge a criterion over every run in the
     * window from the run's first to its last world tick and count each
     * drop.camera_image whose simulation time lies in it: 23 to 25 in each of
     * the 14 runs (SC-DRIVING-012@20/r1 24; SC-DRIVING-012@20/r2 24;
     * SC-DRIVING-012@42/r1 23; SC-DRIVING-012@42/r2 24; SC-DRIVING-012@60/r1
     * 23; SC-DRIVING-012@60/r2 24; SC-DRIVING-013@30/r1 25;
     * SC-DRIVING-013@30/r2 24; SC-DRIVING-013@60/r1 24; SC-DRIVING-013@60/r2
     * 24; SC-DRIVING-014@30/r1 25; SC-DRIVING-014@30/r2 24;
     * SC-DRIVING-015@40/r1 25; SC-DRIVING-015@40/r2 24), the start-up drops and
     * the isolated drops inside the run and none of the end of the image
     * stream, and 32 in the run that stops the path;
     *
     * the capture of the start of the sound on the IVI guest: open. The guest
     * records of S1 hold no start of the sound: in every run the warning
     * presentation received the warning requests with none requesting a
     * warning, so it prepared its sound and never started it; the audio state
     * that each capture records at its start and at its end is no capture of a
     * start. And the showing of the draft of the warning output and the
     * interface seam, with the results, to the VisionPilot maintainers: open,
     * not done; the owner approves any text first (the upstream contact
     * decision of 2026-11-18).
     *
     * Open for the next session, a bench item that S1 shows (B1, the bench
     * finding of 2026-11-21): the second runs of SC-DRIVING-013,
     * SC-DRIVING-013@30/r2 and SC-DRIVING-013@60/r2, ended after 62 ticks at
     * the speed of the target, with the vehicle at 1.3 km/h and the target at
     * 20 km/h. At the first tick of each the target was at rest (8e-08 and
     * 8.5e-05 m/s); in the first runs it already moved at 5.2 m/s. The end
     * check of the world side at 508649ba (_run_loop in
     * world-side/da_world_side.py) counts the vehicle as closing on the target
     * while the closing speed is above 0.0 m/s, and ends the run 3.0 s after
     * the first later tick at which it is not: at the first tick of the second
     * runs the vehicle closed at 0.0023 m/s on the target at rest, at the
     * second the target moved at 5.26 m/s, so each run ended 3.05 s after its
     * first tick. Why the target was at rest at the first tick of the second
     * runs only, the records do not show. SC-DRIVING-013@60/r1 ended in contact
     * with the target but has no functional part: no tick in the band with a
     * time to collision of at least 4 s. So SC-DRIVING-013 has one judged run,
     * SC-DRIVING-013@30/r1. The bench is not changed for S1: a change would
     * alter a file that ran in S1 and void the condition of record.
     *
     * The gap stays a record of the environment; its disposition is phase 11's.
     * Deferred to phase 11.
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
     * Outcome: failObservedBehavior; verdict: fail. Judged from the S1 session
     * 20261121T014447Z by the case evaluators, with criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001), failObservedBehavior:
     * instants 11, missedInstants 11, firstMiss.frame 2943639,
     * firstMiss.simTimeS 564.749 s, firstMiss.neededDecelMps2 5.156 m/s²,
     * firstMiss.commandSeq 269, firstMiss.acceleration 0.53, functionalPart
     * 561.099 s to 565.299 s of simulation time; SC-DRIVING-012@20/r2, record
     * stationaryAt20SecondRunEvidence (EVID-DRIVING-002),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r1, record
     * stationaryAt42FirstRunEvidence (EVID-DRIVING-003), failObservedBehavior:
     * instants 23, missedInstants 23, firstMiss.frame 4252726,
     * firstMiss.simTimeS 918.438 s, firstMiss.neededDecelMps2 5.024 m/s²,
     * firstMiss.commandSeq 222, firstMiss.acceleration -0.036, functionalPart
     * 915.538 s to 919.588 s of simulation time; SC-DRIVING-012@42/r2, record
     * stationaryAt42SecondRunEvidence (EVID-DRIVING-004), failObservedBehavior:
     * instants 22, missedInstants 22, firstMiss.frame 5008565,
     * firstMiss.simTimeS 1084.64 s, firstMiss.neededDecelMps2 5.217 m/s²,
     * firstMiss.commandSeq 223, firstMiss.acceleration -0.038, functionalPart
     * 1081.69 s to 1085.74 s of simulation time; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005), failObservedBehavior:
     * instants 33, missedInstants 33, firstMiss.frame 5655268,
     * firstMiss.simTimeS 1252.909 s, firstMiss.neededDecelMps2 5.0 m/s²,
     * firstMiss.commandSeq 215, firstMiss.acceleration 0.02, functionalPart
     * 1250.509 s to 1254.559 s of simulation time; SC-DRIVING-012@60/r2, record
     * stationaryAt60SecondRunEvidence (EVID-DRIVING-006), failObservedBehavior:
     * instants 33, missedInstants 33, firstMiss.frame 6271180,
     * firstMiss.simTimeS 1396.04 s, firstMiss.neededDecelMps2 5.037 m/s²,
     * firstMiss.commandSeq 214, firstMiss.acceleration 0.017, functionalPart
     * 1393.64 s to 1397.69 s of simulation time; SC-DRIVING-013@30/r1, record
     * slowerAt30FirstRunEvidence (EVID-DRIVING-007), passBoundedVerification:
     * instants 0, missedInstants 0, functionalPart 1533.439 s to 1543.639 s of
     * simulation time; SC-DRIVING-013@30/r2, record slowerAt30SecondRunEvidence
     * (EVID-DRIVING-008), inconclusiveMissingEvidence; SC-DRIVING-013@60/r1,
     * record slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence. Values of the case: calibrationDecel
     * worstRatio 0.5258, allFollowWithinProposal false
     * (sim/out/calibrate/calib_decel/simulator/calibration_decel.json);
     * ackermannGains v1 (ackermann_gains.json of the evidence directory, sha256
     * b76da8bd2d1259c7f7a3583f101ef6dd62065be3ff222e9d3522b6aa9470abf6).
     *
     * The condition on ASM-DRIVING-005, the calibration of the simulated
     * deceleration, that the claimBoundary of each run record states bears on a
     * pass of this case and not on its fail in S1: it concerns how the
     * simulated vehicle achieves a commanded deceleration. In S1 no driving
     * command that the actuation adapter accepted in a run of SC-DRIVING-012
     * holds a deceleration stronger than 0.533 m/s²: the strongest is 0.46 and
     * 0.53 m/s² in the two runs at 20 km/h, 0.18 and 0.18 m/s² at 42 km/h, and
     * 0.23 and 0.18 m/s² at 60 km/h (rounded to two decimals), and the last
     * command that holds a deceleration came before the contact by 0.7 and 0.6
     * s in the two runs at 20 km/h, 0.3 and 0.3 s at 42 km/h, and 0.2 and 0.3 s
     * at 60 km/h. The commanded decelerations of each run, fully achieved,
     * would have lowered its speed before the contact by at most 2.4 km/h: 2.1
     * and 2.4 km/h from 19.7 and 19.2 km/h in the two runs at 20 km/h, 0.4 and
     * 0.5 km/h from 40.6 and 40.6 km/h at 42 km/h, and 0.3 and 0.3 km/h from
     * 58.6 and 58.6 km/h at 60 km/h (rounded up to one decimal;
     * commanded_deceleration.json of the evidence directory states the method).
     * So no calibration of the achieved deceleration turns the fail of this
     * case in S1 into a pass, and the condition on ASM-DRIVING-005, which bears
     * on a pass, does not bear on this fail (the deceleration calibration
     * decision of 2026-11-21).
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget)
     * and SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30 and
     * slowerAt60. Runs: the two runs of each setting, ten runs. Bench: the
     * S-CORE host with the candidate's process, the identity recording
     * application and the actuation adapter under the Launch Manager, the
     * simulator host with CARLA 1.0 and the front camera, and the guest host
     * with the SDV Core VM and the IVI VM.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-037'> impactSpeedWithinLimitVerification : ImpactSpeedWithinLimitVerification {
    doc /*
     * Outcome: failObservedBehavior; verdict: fail. Judged from the S1 session
     * 20261121T014447Z by the case evaluators, with criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001), failObservedBehavior:
     * approachKmh 20.69 km/h, firstImminentFrame 2943590, impactKmh 19.747
     * km/h, contact true, contactFrame 2943650, limitKmh 0.0 km/h;
     * SC-DRIVING-012@20/r2, record stationaryAt20SecondRunEvidence
     * (EVID-DRIVING-002), inconclusiveMissingEvidence; SC-DRIVING-012@42/r1,
     * record stationaryAt42FirstRunEvidence (EVID-DRIVING-003),
     * failObservedBehavior: approachKmh 40.97 km/h, firstImminentFrame 4252669,
     * impactKmh 40.633 km/h, contact true, contactFrame 4252749, limitKmh 0.0
     * km/h; SC-DRIVING-012@42/r2, record stationaryAt42SecondRunEvidence
     * (EVID-DRIVING-004), failObservedBehavior: approachKmh 40.968 km/h,
     * firstImminentFrame 5008507, impactKmh 40.615 km/h, contact true,
     * contactFrame 5008587, limitKmh 0.0 km/h; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005), failObservedBehavior:
     * approachKmh 58.335 km/h, firstImminentFrame 5655221, impactKmh 58.553
     * km/h, contact true, contactFrame 5655301, limitKmh 35.0 km/h;
     * SC-DRIVING-012@60/r2, record stationaryAt60SecondRunEvidence
     * (EVID-DRIVING-006), failObservedBehavior: approachKmh 58.399 km/h,
     * firstImminentFrame 6271133, impactKmh 58.572 km/h, contact true,
     * contactFrame 6271213, limitKmh 35.0 km/h; SC-DRIVING-013@30/r1, record
     * slowerAt30FirstRunEvidence (EVID-DRIVING-007), passBoundedVerification:
     * impactKmh 0.0 km/h, contact false; SC-DRIVING-013@30/r2, record
     * slowerAt30SecondRunEvidence (EVID-DRIVING-008),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r1, record
     * slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence. Values of the case: calibrationDecel
     * worstRatio 0.5258, allFollowWithinProposal false
     * (sim/out/calibrate/calib_decel/simulator/calibration_decel.json);
     * ackermannGains v1 (ackermann_gains.json of the evidence directory, sha256
     * b76da8bd2d1259c7f7a3583f101ef6dd62065be3ff222e9d3522b6aa9470abf6).
     *
     * The condition on ASM-DRIVING-005, the calibration of the simulated
     * deceleration, that the claimBoundary of each run record states bears on a
     * pass of this case and not on its fail in S1: it concerns how the
     * simulated vehicle achieves a commanded deceleration. In S1 no driving
     * command that the actuation adapter accepted in a run of SC-DRIVING-012
     * holds a deceleration stronger than 0.533 m/s²: the strongest is 0.46 and
     * 0.53 m/s² in the two runs at 20 km/h, 0.18 and 0.18 m/s² at 42 km/h, and
     * 0.23 and 0.18 m/s² at 60 km/h (rounded to two decimals), and the last
     * command that holds a deceleration came before the contact by 0.7 and 0.6
     * s in the two runs at 20 km/h, 0.3 and 0.3 s at 42 km/h, and 0.2 and 0.3 s
     * at 60 km/h. The commanded decelerations of each run, fully achieved,
     * would have lowered its speed before the contact by at most 2.4 km/h: 2.1
     * and 2.4 km/h from 19.7 and 19.2 km/h in the two runs at 20 km/h, 0.4 and
     * 0.5 km/h from 40.6 and 40.6 km/h at 42 km/h, and 0.3 and 0.3 km/h from
     * 58.6 and 58.6 km/h at 60 km/h (rounded up to one decimal;
     * commanded_deceleration.json of the evidence directory states the method).
     * So no calibration of the achieved deceleration turns the fail of this
     * case in S1 into a pass, and the condition on ASM-DRIVING-005, which bears
     * on a pass, does not bear on this fail (the deceleration calibration
     * decision of 2026-11-21).
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget)
     * and SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30 and
     * slowerAt60. Runs: the two runs of each setting, ten runs. Bench: the
     * S-CORE host with the candidate's process, the identity recording
     * application and the actuation adapter under the Launch Manager, the
     * simulator host with CARLA 1.0 and the front camera, and the guest host
     * with the SDV Core VM and the IVI VM.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-038'> drivingCommandOverSCOREVerification : DrivingCommandOverSCOREVerification {
    doc /*
     * Outcome: inconclusiveMissingEvidence; verdict: inconclusive. Judged from
     * the S1 session 20261121T014447Z by the case evaluators, with
     * criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001),
     * inconclusiveMissingEvidence; SC-DRIVING-012@20/r2, record
     * stationaryAt20SecondRunEvidence (EVID-DRIVING-002),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r1, record
     * stationaryAt42FirstRunEvidence (EVID-DRIVING-003),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r2, record
     * stationaryAt42SecondRunEvidence (EVID-DRIVING-004),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r2, record
     * stationaryAt60SecondRunEvidence (EVID-DRIVING-006),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r1, record
     * slowerAt30FirstRunEvidence (EVID-DRIVING-007),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r2, record
     * slowerAt30SecondRunEvidence (EVID-DRIVING-008),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r1, record
     * slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r1, record
     * curveAt30FirstRunEvidence (EVID-DRIVING-011),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r2, record
     * curveAt30SecondRunEvidence (EVID-DRIVING-012),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r1, record
     * turningOffAt40FirstRunEvidence (EVID-DRIVING-013),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r2, record
     * turningOffAt40SecondRunEvidence (EVID-DRIVING-014),
     * inconclusiveMissingEvidence; and, for the stop clause, stop/further,
     * record pathStoppedRunEvidence (EVID-DRIVING-015),
     * inconclusiveMissingEvidence. Reason: run 012_20_r1 (SC-DRIVING-012@20):
     * score/out/score_012_20_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 535.399, 535.499, 535.599, 535.699, 535.799 ...
     * s inside the judged window 535.249-568.349 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_20_r2
     * (SC-DRIVING-012@20):
     * score/out/score_012_20_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 731.183, 731.283, 731.383, 731.483, 731.583 ...
     * s inside the judged window 731.133-764.083 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r1
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 893.888, 893.988, 894.088, 894.188, 894.288 ...
     * s inside the judged window 893.638-922.588 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r2
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1060.040, 1060.140, 1060.240, 1060.340, 1060.440
     * ... s inside the judged window 1059.890-1088.740 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r1
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 1229.059, 1229.159, 1229.259, 1229.359, 1229.459
     * ... s inside the judged window 1228.909-1257.559 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r2
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1372.190, 1372.290, 1372.390, 1372.490, 1372.590
     * ... s inside the judged window 1372.040-1400.690 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r1
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 1513.439, 1513.539, 1513.639, 1513.739, 1513.839
     * ... s inside the judged window 1513.289-1546.639 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r2
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1702.149, 1702.249, 1702.349, 1702.449, 1702.549
     * ... s inside the judged window 1701.999-1705.049 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r1
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1817.995, 1818.095, 1818.195, 1818.295, 1818.395
     * ... s inside the judged window 1817.945-1844.595 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r2
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1967.867, 1967.967, 1968.067, 1968.167, 1968.267
     * ... s inside the judged window 1967.717-1970.767 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r1
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2093.841, 2093.941, 2094.041, 2094.141, 2094.241
     * ... s inside the judged window 2093.691-2118.291 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r2
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2231.571, 2231.671, 2231.771, 2231.871, 2231.971
     * ... s inside the judged window 2231.321-2291.321 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r1
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2437.842, 2437.942, 2438.042, 2438.142, 2438.242
     * ... s inside the judged window 2437.692-2512.692 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r2
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2645.837, 2645.937, 2646.037, 2646.137, 2646.237
     * ... s inside the judged window 2645.687-2720.687 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); stop clause:
     * score/out/score_stop/score_side/run/score/score_interface.jsonl: 32
     * drop.camera_image at sim 2855.160, 2855.260, 2855.360, 2855.460, 2855.560
     * ... s inside the judged window 2855.010-2897.010 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207).
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget),
     * SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
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
     * Outcome: passBoundedVerification; verdict: pass. From the desk analysis,
     * record commandFormAnalysisEvidence (EVID-DRIVING-016), written from
     * analysis_039.json; the case reads no run.
     *
     * The analysis is bounded, as the claimBoundary of its record states: the
     * actuation recognizes a loss only when a later command arrives; it does
     * not recognize a delay of up to 0.1 s of simulation time against its
     * newest world time; and it recognizes a corruption only as far as the
     * check value does: a corruption that the check value misses counts as
     * valid and, with a higher sequence count, becomes the reference count, so
     * that later valid commands are rejected as repetitions, which the
     * realization states since the check-value bound decision of 2026-11-21.
     *
     * Scenarios: none; the case reads the realization of phase 8 and no run.
     * Bench: the model revision that the record names, read by an analyst; no
     * host.
     */
    @VerificationMethod{ kind = analyze; }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-040'> withholdWarningRequestVerification : WithholdWarningRequestVerification {
    doc /*
     * Outcome: inconclusiveMissingEvidence; verdict: inconclusive. Judged from
     * the S1 session 20261121T014447Z by the case evaluators, with
     * criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001),
     * inconclusiveMissingEvidence; SC-DRIVING-012@20/r2, record
     * stationaryAt20SecondRunEvidence (EVID-DRIVING-002),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r1, record
     * stationaryAt42FirstRunEvidence (EVID-DRIVING-003),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r2, record
     * stationaryAt42SecondRunEvidence (EVID-DRIVING-004),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r2, record
     * stationaryAt60SecondRunEvidence (EVID-DRIVING-006),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r1, record
     * slowerAt30FirstRunEvidence (EVID-DRIVING-007),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r2, record
     * slowerAt30SecondRunEvidence (EVID-DRIVING-008),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r1, record
     * slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r1, record
     * curveAt30FirstRunEvidence (EVID-DRIVING-011),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r2, record
     * curveAt30SecondRunEvidence (EVID-DRIVING-012),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r1, record
     * turningOffAt40FirstRunEvidence (EVID-DRIVING-013),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r2, record
     * turningOffAt40SecondRunEvidence (EVID-DRIVING-014),
     * inconclusiveMissingEvidence. Reason: run 012_20_r1 (SC-DRIVING-012@20):
     * score/out/score_012_20_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 535.399, 535.499, 535.599, 535.699, 535.799 ...
     * s inside the judged window 535.249-568.349 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_20_r2
     * (SC-DRIVING-012@20):
     * score/out/score_012_20_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 731.183, 731.283, 731.383, 731.483, 731.583 ...
     * s inside the judged window 731.133-764.083 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r1
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 893.888, 893.988, 894.088, 894.188, 894.288 ...
     * s inside the judged window 893.638-922.588 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r2
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1060.040, 1060.140, 1060.240, 1060.340, 1060.440
     * ... s inside the judged window 1059.890-1088.740 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r1
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 1229.059, 1229.159, 1229.259, 1229.359, 1229.459
     * ... s inside the judged window 1228.909-1257.559 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r2
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1372.190, 1372.290, 1372.390, 1372.490, 1372.590
     * ... s inside the judged window 1372.040-1400.690 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r1
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 1513.439, 1513.539, 1513.639, 1513.739, 1513.839
     * ... s inside the judged window 1513.289-1546.639 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r2
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1702.149, 1702.249, 1702.349, 1702.449, 1702.549
     * ... s inside the judged window 1701.999-1705.049 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r1
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1817.995, 1818.095, 1818.195, 1818.295, 1818.395
     * ... s inside the judged window 1817.945-1844.595 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r2
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1967.867, 1967.967, 1968.067, 1968.167, 1968.267
     * ... s inside the judged window 1967.717-1970.767 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r1
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2093.841, 2093.941, 2094.041, 2094.141, 2094.241
     * ... s inside the judged window 2093.691-2118.291 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r2
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2231.571, 2231.671, 2231.771, 2231.871, 2231.971
     * ... s inside the judged window 2231.321-2291.321 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r1
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2437.842, 2437.942, 2438.042, 2438.142, 2438.242
     * ... s inside the judged window 2437.692-2512.692 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r2
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2645.837, 2645.937, 2646.037, 2646.137, 2646.237
     * ... s inside the judged window 2645.687-2720.687 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207).
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget),
     * SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
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
     * Outcome: inconclusiveMissingEvidence; verdict: inconclusive. Judged from
     * the S1 session 20261121T014447Z by the case evaluators, with
     * criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001),
     * inconclusiveMissingEvidence; SC-DRIVING-012@20/r2, record
     * stationaryAt20SecondRunEvidence (EVID-DRIVING-002),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r1, record
     * stationaryAt42FirstRunEvidence (EVID-DRIVING-003),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r2, record
     * stationaryAt42SecondRunEvidence (EVID-DRIVING-004),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r2, record
     * stationaryAt60SecondRunEvidence (EVID-DRIVING-006),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r1, record
     * slowerAt30FirstRunEvidence (EVID-DRIVING-007),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r2, record
     * slowerAt30SecondRunEvidence (EVID-DRIVING-008),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r1, record
     * slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r1, record
     * curveAt30FirstRunEvidence (EVID-DRIVING-011),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r2, record
     * curveAt30SecondRunEvidence (EVID-DRIVING-012),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r1, record
     * turningOffAt40FirstRunEvidence (EVID-DRIVING-013),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r2, record
     * turningOffAt40SecondRunEvidence (EVID-DRIVING-014),
     * inconclusiveMissingEvidence. Reason: run 012_20_r1 (SC-DRIVING-012@20):
     * score/out/score_012_20_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 535.399, 535.499, 535.599, 535.699, 535.799 ...
     * s inside the judged window 535.249-568.349 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_20_r2
     * (SC-DRIVING-012@20):
     * score/out/score_012_20_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 731.183, 731.283, 731.383, 731.483, 731.583 ...
     * s inside the judged window 731.133-764.083 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r1
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 893.888, 893.988, 894.088, 894.188, 894.288 ...
     * s inside the judged window 893.638-922.588 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r2
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1060.040, 1060.140, 1060.240, 1060.340, 1060.440
     * ... s inside the judged window 1059.890-1088.740 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r1
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 1229.059, 1229.159, 1229.259, 1229.359, 1229.459
     * ... s inside the judged window 1228.909-1257.559 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r2
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1372.190, 1372.290, 1372.390, 1372.490, 1372.590
     * ... s inside the judged window 1372.040-1400.690 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r1
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 1513.439, 1513.539, 1513.639, 1513.739, 1513.839
     * ... s inside the judged window 1513.289-1546.639 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r2
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1702.149, 1702.249, 1702.349, 1702.449, 1702.549
     * ... s inside the judged window 1701.999-1705.049 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r1
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1817.995, 1818.095, 1818.195, 1818.295, 1818.395
     * ... s inside the judged window 1817.945-1844.595 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r2
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1967.867, 1967.967, 1968.067, 1968.167, 1968.267
     * ... s inside the judged window 1967.717-1970.767 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r1
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2093.841, 2093.941, 2094.041, 2094.141, 2094.241
     * ... s inside the judged window 2093.691-2118.291 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r2
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2231.571, 2231.671, 2231.771, 2231.871, 2231.971
     * ... s inside the judged window 2231.321-2291.321 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r1
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2437.842, 2437.942, 2438.042, 2438.142, 2438.242
     * ... s inside the judged window 2437.692-2512.692 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r2
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2645.837, 2645.937, 2646.037, 2646.137, 2646.237
     * ... s inside the judged window 2645.687-2720.687 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207).
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget),
     * SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
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
     * Outcome: failObservedBehavior; verdict: fail. Judged from the S1 session
     * 20261121T014447Z by the case evaluators, with criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001), failObservedBehavior:
     * imminent true, firstImminentSimS 562.299 s of simulation time,
     * warningStarts 0; SC-DRIVING-012@20/r2, record
     * stationaryAt20SecondRunEvidence (EVID-DRIVING-002),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r1, record
     * stationaryAt42FirstRunEvidence (EVID-DRIVING-003), failObservedBehavior:
     * imminent true, firstImminentSimS 915.588 s of simulation time,
     * warningStarts 0; SC-DRIVING-012@42/r2, record
     * stationaryAt42SecondRunEvidence (EVID-DRIVING-004), failObservedBehavior:
     * imminent true, firstImminentSimS 1081.74 s of simulation time,
     * warningStarts 0; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005), failObservedBehavior:
     * imminent true, firstImminentSimS 1250.559 s of simulation time,
     * warningStarts 0; SC-DRIVING-012@60/r2, record
     * stationaryAt60SecondRunEvidence (EVID-DRIVING-006), failObservedBehavior:
     * imminent true, firstImminentSimS 1393.69 s of simulation time,
     * warningStarts 0; SC-DRIVING-013@30/r1, record slowerAt30FirstRunEvidence
     * (EVID-DRIVING-007), passBoundedVerification: imminent false;
     * SC-DRIVING-013@30/r2, record slowerAt30SecondRunEvidence
     * (EVID-DRIVING-008), inconclusiveMissingEvidence; SC-DRIVING-013@60/r1,
     * record slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence.
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget)
     * and SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30 and
     * slowerAt60. Runs: the two runs of each setting, ten runs. Bench: the
     * S-CORE host with the candidate's process, the identity recording
     * application and the actuation adapter under the Launch Manager, the
     * simulator host with CARLA 1.0 and the front camera, and the guest host
     * with the SDV Core VM and the IVI VM.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-043'> warningRequestOverSCOREVerification : WarningRequestOverSCOREVerification {
    doc /*
     * Outcome: inconclusiveMissingEvidence; verdict: inconclusive. Judged from
     * the S1 session 20261121T014447Z by the case evaluators, with
     * criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001),
     * inconclusiveMissingEvidence; SC-DRIVING-012@20/r2, record
     * stationaryAt20SecondRunEvidence (EVID-DRIVING-002),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r1, record
     * stationaryAt42FirstRunEvidence (EVID-DRIVING-003),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r2, record
     * stationaryAt42SecondRunEvidence (EVID-DRIVING-004),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r2, record
     * stationaryAt60SecondRunEvidence (EVID-DRIVING-006),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r1, record
     * slowerAt30FirstRunEvidence (EVID-DRIVING-007),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r2, record
     * slowerAt30SecondRunEvidence (EVID-DRIVING-008),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r1, record
     * slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence; and, for the stop clause, stop/further,
     * record pathStoppedRunEvidence (EVID-DRIVING-015),
     * inconclusiveMissingEvidence. Reason: run 012_20_r1 (SC-DRIVING-012@20):
     * score/out/score_012_20_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 535.399, 535.499, 535.599, 535.699, 535.799 ...
     * s inside the judged window 535.249-568.349 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_20_r2
     * (SC-DRIVING-012@20):
     * score/out/score_012_20_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 731.183, 731.283, 731.383, 731.483, 731.583 ...
     * s inside the judged window 731.133-764.083 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r1
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 893.888, 893.988, 894.088, 894.188, 894.288 ...
     * s inside the judged window 893.638-922.588 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r2
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1060.040, 1060.140, 1060.240, 1060.340, 1060.440
     * ... s inside the judged window 1059.890-1088.740 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r1
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 1229.059, 1229.159, 1229.259, 1229.359, 1229.459
     * ... s inside the judged window 1228.909-1257.559 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r2
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1372.190, 1372.290, 1372.390, 1372.490, 1372.590
     * ... s inside the judged window 1372.040-1400.690 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r1
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 1513.439, 1513.539, 1513.639, 1513.739, 1513.839
     * ... s inside the judged window 1513.289-1546.639 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r2
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1702.149, 1702.249, 1702.349, 1702.449, 1702.549
     * ... s inside the judged window 1701.999-1705.049 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r1
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1817.995, 1818.095, 1818.195, 1818.295, 1818.395
     * ... s inside the judged window 1817.945-1844.595 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r2
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1967.867, 1967.967, 1968.067, 1968.167, 1968.267
     * ... s inside the judged window 1967.717-1970.767 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); stop clause:
     * score/out/score_stop/score_side/run/score/score_interface.jsonl: 32
     * drop.camera_image at sim 2855.160, 2855.260, 2855.360, 2855.460, 2855.560
     * ... s inside the judged window 2855.010-2897.010 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207).
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget)
     * and SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget). Settings:
     * stationaryAt20, stationaryAt42, stationaryAt60, slowerAt30 and
     * slowerAt60. Runs: the two runs of each setting, ten runs, and the further
     * run of SC-DRIVING-012 in which the Eclipse S-CORE path of the
     * driver-assistance system is stopped, which only the stop clause reads.
     * Bench: the S-CORE host with the candidate's process, the identity
     * recording application and the actuation adapter under the Launch Manager,
     * the simulator host with CARLA 1.0 and the front camera, and the guest
     * host with the SDV Core VM and the IVI VM. In the further run the
     * candidate's process keeps running, and the path's carriers of the driving
     * command and of the warning request are stopped through the Launch
     * Manager; which processes these are is fixed in the next slice.
     */
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> driverAssistanceVerificationBench;
  }

  verification <'VC-DRIVING-044'> recordCandidateIdentityVerification : RecordCandidateIdentityVerification {
    doc /*
     * Outcome: inconclusiveMissingEvidence; verdict: inconclusive. Judged from
     * the S1 session 20261121T014447Z by the case evaluators, with
     * criteriaRecordIdentity
     * sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136
     * and evaluatorRevision
     * blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68.
     * Runs read, each by its run identity with the record it reads, its outcome
     * and the values measured: SC-DRIVING-012@20/r1, record
     * stationaryAt20FirstRunEvidence (EVID-DRIVING-001),
     * inconclusiveMissingEvidence; SC-DRIVING-012@20/r2, record
     * stationaryAt20SecondRunEvidence (EVID-DRIVING-002),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r1, record
     * stationaryAt42FirstRunEvidence (EVID-DRIVING-003),
     * inconclusiveMissingEvidence; SC-DRIVING-012@42/r2, record
     * stationaryAt42SecondRunEvidence (EVID-DRIVING-004),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r1, record
     * stationaryAt60FirstRunEvidence (EVID-DRIVING-005),
     * inconclusiveMissingEvidence; SC-DRIVING-012@60/r2, record
     * stationaryAt60SecondRunEvidence (EVID-DRIVING-006),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r1, record
     * slowerAt30FirstRunEvidence (EVID-DRIVING-007),
     * inconclusiveMissingEvidence; SC-DRIVING-013@30/r2, record
     * slowerAt30SecondRunEvidence (EVID-DRIVING-008),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r1, record
     * slowerAt60FirstRunEvidence (EVID-DRIVING-009),
     * inconclusiveMissingEvidence; SC-DRIVING-013@60/r2, record
     * slowerAt60SecondRunEvidence (EVID-DRIVING-010),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r1, record
     * curveAt30FirstRunEvidence (EVID-DRIVING-011),
     * inconclusiveMissingEvidence; SC-DRIVING-014@30/r2, record
     * curveAt30SecondRunEvidence (EVID-DRIVING-012),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r1, record
     * turningOffAt40FirstRunEvidence (EVID-DRIVING-013),
     * inconclusiveMissingEvidence; SC-DRIVING-015@40/r2, record
     * turningOffAt40SecondRunEvidence (EVID-DRIVING-014),
     * inconclusiveMissingEvidence. Values of the case: desk reproduction
     * valuesMatch true. Reason: run 012_20_r1 (SC-DRIVING-012@20):
     * score/out/score_012_20_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 535.399, 535.499, 535.599, 535.699, 535.799 ...
     * s inside the judged window 535.249-568.349 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_20_r2
     * (SC-DRIVING-012@20):
     * score/out/score_012_20_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 731.183, 731.283, 731.383, 731.483, 731.583 ...
     * s inside the judged window 731.133-764.083 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r1
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 893.888, 893.988, 894.088, 894.188, 894.288 ...
     * s inside the judged window 893.638-922.588 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_42_r2
     * (SC-DRIVING-012@42):
     * score/out/score_012_42_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1060.040, 1060.140, 1060.240, 1060.340, 1060.440
     * ... s inside the judged window 1059.890-1088.740 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r1
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r1/score_side/run/score/score_interface.jsonl: 23
     * drop.camera_image at sim 1229.059, 1229.159, 1229.259, 1229.359, 1229.459
     * ... s inside the judged window 1228.909-1257.559 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 012_60_r2
     * (SC-DRIVING-012@60):
     * score/out/score_012_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1372.190, 1372.290, 1372.390, 1372.490, 1372.590
     * ... s inside the judged window 1372.040-1400.690 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r1
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 1513.439, 1513.539, 1513.639, 1513.739, 1513.839
     * ... s inside the judged window 1513.289-1546.639 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_30_r2
     * (SC-DRIVING-013@30):
     * score/out/score_013_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1702.149, 1702.249, 1702.349, 1702.449, 1702.549
     * ... s inside the judged window 1701.999-1705.049 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r1
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r1/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1817.995, 1818.095, 1818.195, 1818.295, 1818.395
     * ... s inside the judged window 1817.945-1844.595 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 013_60_r2
     * (SC-DRIVING-013@60):
     * score/out/score_013_60_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 1967.867, 1967.967, 1968.067, 1968.167, 1968.267
     * ... s inside the judged window 1967.717-1970.767 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r1
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2093.841, 2093.941, 2094.041, 2094.141, 2094.241
     * ... s inside the judged window 2093.691-2118.291 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 014_30_r2
     * (SC-DRIVING-014@30):
     * score/out/score_014_30_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2231.571, 2231.671, 2231.771, 2231.871, 2231.971
     * ... s inside the judged window 2231.321-2291.321 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r1
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r1/score_side/run/score/score_interface.jsonl: 25
     * drop.camera_image at sim 2437.842, 2437.942, 2438.042, 2438.142, 2438.242
     * ... s inside the judged window 2437.692-2512.692 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207); run 015_40_r2
     * (SC-DRIVING-015@40):
     * score/out/score_015_40_r2/score_side/run/score/score_interface.jsonl: 24
     * drop.camera_image at sim 2645.837, 2645.937, 2646.037, 2646.137, 2646.237
     * ... s inside the judged window 2645.687-2720.687 s
     * (MAP-DRIVING-DA-CAMERA-IMAGE;
     * driver_assistance_verification_evidence.sysml:204-207).
     *
     * Scenarios: SC-DRIVING-012 (AssistanceScenarioIdentity::stationaryTarget),
     * SC-DRIVING-013 (AssistanceScenarioIdentity::slowerTarget), SC-DRIVING-014
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
     * framing's driverAssistanceVerificationEnvironment, whose readiness
     * GAP-DRIVING-014 records as the judged session S1 leaves it.
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
     * collision with a vehicle ahead is imminent. Whether the judged session S1
     * supports the claim follows from the verdicts of the cases its argument
     * cites, which their docs state; the claim stands as it was written before
     * any run.
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
     * four, the part of the command by which the actuation detects it. Whether
     * the judged session S1 supports the claim follows from the verdicts of the
     * cases its argument cites, which their docs state; the claim stands as it
     * was written before any run.
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
     * SC-DRIVING-012 to SC-DRIVING-015 it starts a warning request only while a
     * collision with a vehicle ahead is imminent. Whether the judged session S1
     * supports the claim follows from the verdicts of the cases its argument
     * cites, which their docs state; the claim stands as it was written before
     * any run.
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
     * matched in the communication records of the Eclipse S-CORE path to an
     * output of the driver-assistance system; in those fourteen runs the
     * autopilot and the traffic manager of the simulator have no control of the
     * vehicle, and no recorded, replayed, scripted or overlaid control reaches
     * its actuation; and in the further run of SC-DRIVING-012 with the path
     * stopped neither the command nor the request arrives after the stop.
     * Whether the judged session S1 supports the claim follows from the
     * verdicts of the cases its argument cites, which their docs state; the
     * claim stands as it was written before any run.
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
     * ran: the candidate identity record of each of those runs, there before
     * its first driving command and re-derived by another engineer, names the
     * upstream revision and the difference of the build, which carries the
     * DE4SDV S-CORE interface and the visualization recorder, so that a verdict
     * holds for that build and states the recorder's delay; and the evidence
     * record of each of those runs binds DRIVING-CONFIG-002 and its receipt,
     * the model revision, the pins and the simulated configuration. The record
     * of the further run of SC-DRIVING-012 with the path stopped carries the
     * candidate identity values as well, and no case checks them, because only
     * the stop clauses of REQ-DRIVING-038 and REQ-DRIVING-043 read that run. A
     * fail stays a recorded result. Whether the judged session S1 supports the
     * claim follows from the verdicts of the cases its argument cites, which
     * their docs state; the claim stands as it was written before any run.
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
     * No verdict holds beyond the bench of the judged session S1: a verdict
     * holds for the session, the bench commit and the candidate build that its
     * records name, and the readiness items that S1 does not show stay open
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
     * written first and not fitted to results. The claims were written before
     * any run, and the verdicts of the judged session S1 are read against them.
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
     * The assurance structure of the increment with the evidence of record: the
     * five claims, the argument that supports each and the cases it cites, the
     * nine cases, the evidence record of a run and the record of the analysis,
     * the sixteen records of the judged session S1, the bench and the
     * environment gap, and the twelve counter-claims with the records that keep
     * them open, those records exposed beside them. It frames the phase 1
     * concern of the Architecture Management domain beside the phase's own
     * concern, so that it is answered in its domain.
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
    expose stationaryAt20FirstRunEvidence;
    expose stationaryAt20SecondRunEvidence;
    expose stationaryAt42FirstRunEvidence;
    expose stationaryAt42SecondRunEvidence;
    expose stationaryAt60FirstRunEvidence;
    expose stationaryAt60SecondRunEvidence;
    expose slowerAt30FirstRunEvidence;
    expose slowerAt30SecondRunEvidence;
    expose slowerAt60FirstRunEvidence;
    expose slowerAt60SecondRunEvidence;
    expose curveAt30FirstRunEvidence;
    expose curveAt30SecondRunEvidence;
    expose turningOffAt40FirstRunEvidence;
    expose turningOffAt40SecondRunEvidence;
    expose pathStoppedRunEvidence;
    expose commandFormAnalysisEvidence;
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
