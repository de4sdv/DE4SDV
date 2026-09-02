/*
 * DE4SDV middleware verification and validation/evidence model slice.
 *
 * INC-MW-010 defines the verification cases, validation scenarios, acceptance
 * criteria, retained evidence, bounded assurance claim, deferred counterclaims,
 * and Phase 12 baseline decision for the configured Autoware + AndroidSDV
 * member.
 *
 * The accepted baseline is limited to the observed forward Vehicle.Speed chain,
 * bounded real Autoware consumption, invalid-envelope rejection, and provider-
 * loss health disposition. Full lifecycle ordering, update/OTA behavior, the
 * reverse lifecycle/status path, production deployment, full-stack Autoware,
 * safety, and certification claims remain deferred or not claimed.
 */

package DE4SDV_Middleware010VerificationEvidence {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ExecutionEnvironments::*;
  private import DE4SDV_MiddlewareRequirements::Features::Middleware::Requirements::*;
  private import DE4SDV_MiddlewareFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::*;
  private import DE4SDV_MiddlewarePhysicalSoftwareRealization::*;
  private import DE4SDV_MiddlewareVariabilityConfiguration::*;
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import ScalarValues::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part incMW010 : FeatureIncrement {
    doc /* INC-MW-010: middleware verification, validation, and evidence. */
  }

  enum def MiddlewareScenarioIdentity {
    signalTranslation;
    lifecycleCoordination;
    healthForwarding;
    vehicleStartup;
    updateCoordination;
    faultDetection;
  }

  enum def MiddlewareEvidenceOutcome {
    passBoundedVerification;
    passBoundedValidation;
    failObservedBehavior;
    inconclusiveMissingEvidence;
    blockedTargetRuntime;
    errorEvidence;
  }

  enum def MiddlewareEvidenceDisposition {
    planned;
    observedBounded;
    partial;
    blocked;
    accepted;
    rejected;
  }

  item def VehicleSpeedTranslationObservation {
    attribute inputSpeedKmh : Real;
    attribute expectedVelocityMps : Real;
    attribute observedVelocityMps : Real;
    attribute sourceContractIdentity : String;
    attribute consumerContractIdentity : String;
    attribute independentObservation : Boolean;
  }

  item def MiddlewareLifecycleObservation {
    attribute stateName : String;
    attribute predecessorState : String;
    attribute successorState : String;
    attribute transitionObserved : Boolean;
  }

  item def MiddlewareHealthObservation {
    attribute healthState : String;
    attribute sourceFresh : Boolean;
    attribute forwarded : Boolean;
    attribute faultIdentity : String;
  }

  item def RetainedMiddlewareEvidence {
    attribute configurationIdentity : String;
    attribute executionEnvironmentIdentity : String;
    attribute contractIdentity : String;
    attribute rawObservationArtifact : String;
    attribute independentObserverIdentity : String;
    attribute disposition : MiddlewareEvidenceDisposition;
    attribute claimBoundary : String;
  }

  item def ReplayedMiddlewareEvaluation {
    attribute scenario : MiddlewareScenarioIdentity;
    attribute outcome : MiddlewareEvidenceOutcome;
    attribute acceptanceSummary : String;
  }

  calc def MapEvidenceOutcomeToVerdict {
    in outcome : MiddlewareEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == MiddlewareEvidenceOutcome::passBoundedVerification? VerdictKind::pass
      else if outcome == MiddlewareEvidenceOutcome::passBoundedValidation? VerdictKind::pass
      else if outcome == MiddlewareEvidenceOutcome::failObservedBehavior? VerdictKind::fail
      else if outcome == MiddlewareEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def MiddlewareIntegrationVandVBench {
    doc /*
     * System 1 is the configured member under evaluation. System 2 is the
     * engineering/build/test environment and is not a product selection.
     */
    part system1MemberProduct : MiddlewareAutowareAAOSSDVConfiguredMember;
    part system2TestEnvironment : AOSPAAOSBuildRuntimeEnvironment;
    attribute scenario : MiddlewareScenarioIdentity;
  }

  part signalTranslationBench010 : MiddlewareIntegrationVandVBench {
    attribute :>> scenario = MiddlewareScenarioIdentity::signalTranslation;
  }

  part lifecycleCoordinationBench010 : MiddlewareIntegrationVandVBench {
    attribute :>> scenario = MiddlewareScenarioIdentity::lifecycleCoordination;
  }

  part healthForwardingBench010 : MiddlewareIntegrationVandVBench {
    attribute :>> scenario = MiddlewareScenarioIdentity::healthForwarding;
  }

  part vehicleStartupBench010 : MiddlewareIntegrationVandVBench {
    attribute :>> scenario = MiddlewareScenarioIdentity::vehicleStartup;
  }

  part updateCoordinationBench010 : MiddlewareIntegrationVandVBench {
    attribute :>> scenario = MiddlewareScenarioIdentity::updateCoordination;
  }

  part faultDetectionBench010 : MiddlewareIntegrationVandVBench {
    attribute :>> scenario = MiddlewareScenarioIdentity::faultDetection;
  }

  requirement def MiddlewareAcceptanceCriterion
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement acceptanceCriterion010SignalTranslation : MiddlewareAcceptanceCriterion {
    doc /* AC-MW-010-01; bounded verification of the selected Vehicle.Speed slice. */
    subject bench : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /* The selected contract shall preserve Vehicle.Speed [km/h] semantics, map 36 km/h to 10 m/s and 72 km/h to 20 m/s through division by 3.6, reject invalid/non-finite samples, and expose the resulting VelocityReport field to an independent observer. */
    }
  }

  requirement acceptanceCriterion010LifecycleCoordination : MiddlewareAcceptanceCriterion {
    doc /* AC-MW-010-02; bounded verification of integration lifecycle behavior. */
    subject bench : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /* The integration boundary shall make startup, initializing, operational, degraded, and shutdown behavior observable, preserve the declared transition ordering, and prevent use before required binding/readiness. */
    }
  }

  requirement acceptanceCriterion010HealthForwarding : MiddlewareAcceptanceCriterion {
    doc /* AC-MW-010-03; bounded verification of health forwarding. */
    subject bench : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /* Missing, stale, inconsistent, or unavailable provider/transport/consumer health shall produce an observable degraded or unavailable disposition and shall be forwarded to the application boundary without being relabeled as healthy. */
    }
  }

  requirement acceptanceCriterion010VehicleStartup : MiddlewareAcceptanceCriterion {
    doc /* AC-MW-010-04; validation of vehicle/application startup. */
    subject bench : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /* A configured member startup scenario shall prove provider registration, service discovery/binding, transport readiness, adapter readiness, and ROS 2 consumer readiness in causal order before the signal is accepted. */
    }
  }

  requirement acceptanceCriterion010UpdateCoordination : MiddlewareAcceptanceCriterion {
    doc /* AC-MW-010-05; validation of integration update behavior. */
    subject bench : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /* An update/OTA scenario shall retain pre-update and post-update identities and observations and shall detect, rather than silently accept, loss or incompatible change of the required signal, lifecycle, health, discovery, or consumer contracts. */
    }
  }

  requirement acceptanceCriterion010FaultDetection : MiddlewareAcceptanceCriterion {
    doc /* AC-MW-010-06; validation of fault detection and containment. */
    subject bench : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /* Provider, binding, discovery, transport, adapter, and consumer faults shall be detected and classified at the integration boundary; non-safety middleware failure shall not create an uncontrolled emergency intervention command. */
    }
  }

  requirement acceptanceCriterion010EvidenceIndependence : MiddlewareAcceptanceCriterion {
    doc /* AC-MW-010-07; evidence integrity and claim-boundary criterion. */
    subject bench : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /* Every retained verdict shall bind the configured member, execution environment, contract identities, raw observations, and independent observer evidence. Missing target-runtime evidence shall be inconclusive or blocked, never a runtime pass. */
    }
  }

  part boundedAAOSBootBaseline010 : InspectedExecutionEnvironmentEvidence {
    doc /*
     * implementation/aaos-sdv-reference-interop-bench/evidence/
     * aaos-cuttlefish-cloud-proof.yaml. This is bounded x86_64 AOSP build and
     * Cuttlefish boot evidence; it is not provider, transport, ROS 2, Autoware,
     * lifecycle, update, fault, or vehicle interoperability evidence.
     */
  }

  part contractAndRehearsalEvidence010 : ExecutionEnvironmentEvidenceArtifact {
    doc /*
     * Existing reference-contract and provider-neutral adapter tests support
     * contract and conversion claims only. They are not target-runtime proof.
     */
  }

  part plannedTargetRuntimeEvidence010 : PlannedExecutionEnvironmentEvidence {
    doc /*
     * Planned evidence for provider binding, deployment, discovery, transport,
     * ROS 2 publication, independent Autoware observation, and lifecycle/fault
     * scenarios on the configured member. The campaign-chain subset of this
     * plan is now retained as runtimeCampaignEvidence011; the adapter-chain
     * and lifecycle/update subset remains planned.
     */
  }

  part runtimeCampaignEvidence011 : RetainedMiddlewareEvidence {
    doc /*
     * E-MW-011. Retained runtime campaign evidence (2026-08-20) for the
     * configured member's modeled two-VM campaign deployment:
     *
     *   vmA.cuttlefishGuest (provider+observer bundles, sdv_core_cf,
     *   instance1 bootconfig) -> vmA.hostForwarder (adb_logcat_bridge,
     *   accepts DE4SDV_ADB_LOGCAT_FORWARD_ACCEPTED) -> privateTcpBoundary
     *   (VPC tcp:4711) -> vmB.ros2Ingress (vehicle_speed_tcp_bridge node,
     *   strict envelope validation, publishes VelocityReport) ->
     *   vmB.independentObserver (validates 10.0 m/s).
     *
     * Gates 1-7 pass; gate 8 (reverse lifecycle/status) not claimed.
     * Provider process, registration, discovery agent, forwarder accepts,
     * exact topic/type/field, independent observer, and ingress rejection
     * were all observed on the live hosts.
     */
    attribute :>> configurationIdentity = "MW-CONFIG-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a-de4sdv-aaos-build+de4sdv-ros2-autoware";
    attribute :>> contractIdentity = "de4sdv.reference.vehicle_speed.VehicleSpeed -> autoware_vehicle_msgs/msg/VelocityReport";
    attribute :>> rawObservationArtifact = "implementation/aaos-sdv-reference-interop-bench/evidence/e-mw-011-runtime-campaign.yaml";
    attribute :>> independentObserverIdentity = "de4sdv_velocity_report_independent_observer (vmB)";
    attribute :>> disposition = MiddlewareEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Campaign-chain runtime evidence on the two-VM deployment; not adapter-chain, lifecycle/update, safety, or certification evidence.";
  }

  part runtimeAdapterPathEvidence012 : RetainedMiddlewareEvidence {
    doc /*
     * E-MW-012. Retained direct adapter-path campaign evidence for the same
     * configured member. The AAOS provider and observer service bundles,
     * discovery, direct TCP egress, ROS 2 VelocityReport publication,
     * independent 10.0 m/s observation, and invalid-envelope rejection were
     * observed. Gate 8 remained not claimed.
     */
    attribute :>> configurationIdentity = "MW-CONFIG-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a-de4sdv-aaos-build+de4sdv-ros2-autoware";
    attribute :>> contractIdentity = "de4sdv.reference.vehicle_speed.VehicleSpeed -> autoware_vehicle_msgs/msg/VelocityReport";
    attribute :>> rawObservationArtifact = "implementation/aaos-sdv-reference-interop-bench/evidence/e-mw-012-adapter-path-campaign.yaml";
    attribute :>> independentObserverIdentity = "de4sdv_velocity_report_independent_observer (vmB)";
    attribute :>> disposition = MiddlewareEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Direct campaign adapter path only; not bidirectional, production-deployment, lifecycle/update, safety, or certification evidence.";
  }

  part runtimeAutowareConsumerEvidence013 : RetainedMiddlewareEvidence {
    doc /*
     * E-MW-013. A real autoware_vehicle_velocity_converter instance consumed
     * /vehicle/status/velocity_status and produced
     * /vehicle/status/twist_with_covariance with linear.x = 10.0 m/s and
     * covariance[0] = 0.04. This proves bounded Autoware-side consumption by
     * that node, not operation of the full Autoware stack.
     */
    attribute :>> configurationIdentity = "MW-CONFIG-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a-de4sdv-aaos-build+de4sdv-ros2-autoware";
    attribute :>> contractIdentity = "autoware_vehicle_msgs/msg/VelocityReport -> geometry_msgs/msg/TwistWithCovarianceStamped";
    attribute :>> rawObservationArtifact = "implementation/aaos-sdv-reference-interop-bench/evidence/e-mw-013-autoware-consumer.yaml";
    attribute :>> independentObserverIdentity = "autoware_vehicle_velocity_converter output observation (vmB)";
    attribute :>> disposition = MiddlewareEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "One real Autoware consumer and its converted output; not localization, planning, perception, control, safety, or certification evidence.";
  }

  part runtimeHealthDispositionEvidence014 : RetainedMiddlewareEvidence {
    doc /*
     * E-MW-014. Provider loss produced an observable degraded=stale
     * disposition after the five-second freshness bound; provider restoration
     * produced restored=healthy and resumed 10.0 m/s publication. This closes
     * only the health-disposition subset of GAP-MW-028.
     */
    attribute :>> configurationIdentity = "MW-CONFIG-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a-de4sdv-aaos-build+de4sdv-ros2-autoware";
    attribute :>> contractIdentity = "/vehicle/status/velocity_status provider-loss health disposition";
    attribute :>> rawObservationArtifact = "implementation/aaos-sdv-reference-interop-bench/evidence/e-mw-014-health-disposition.yaml";
    attribute :>> independentObserverIdentity = "retained VM-B bridge log and health-topic observation";
    attribute :>> disposition = MiddlewareEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Provider-loss degraded/restored disposition only; not complete lifecycle ordering, update/OTA, reverse-path, safety, or certification evidence.";
  }

  part boundedBaselineDecision010 : IncrementLifecycleDecision {
    doc /*
     * BL-MW-010-P12. Phase 12 accepts the bounded forward Vehicle.Speed chain,
     * direct adapter path, independent ROS 2 observation, one real Autoware
     * consumer, invalid-envelope rejection, and provider-loss degraded/restored
     * health disposition demonstrated by E-MW-011 through E-MW-014.
     *
     * Complete lifecycle transition ordering (AC-MW-010-02), update/OTA
     * contract preservation (AC-MW-010-05), and the reverse lifecycle/status
     * path (gate 8) are deferred or not claimed. Production deployment, full
     * Autoware-stack, safety, certification, compliance, homologation, and
     * type-approval claims are also excluded. INC-MW-010 closes with these
     * residual counterclaims and gaps still explicit.
     */
  }

  part successorIncrementDecision010 : IncrementLifecycleDecision {
    doc /*
     * Any stakeholder-visible Autoware-to-AAOS visualization and any reverse
     * transport used by it shall be framed as a separate capability increment.
     * It is not added to INC-MW-010 and does not retroactively satisfy gate 8.
     */
  }

  part providerBindingEvidenceGap010 : DeferredProductLineScope {
    doc /* GAP-MW-025: Generated/usable VSIDL binding and deployed provider behavior remain unavailable. Campaign-chain subset observed (E-MW-011 gate 1: VehicleSpeedProvider:instance running); production adapter-chain binding remains open. */
  }

  part crossDomainTransportEvidenceGap010 : DeferredProductLineScope {
    doc /* GAP-MW-026: Android/KVM-to-Linux/ROS 2 transport, discovery, and deployment evidence remain unavailable. Campaign-chain subset observed (E-MW-011 gates 3-5: discovery agent, forwarder accepts, exact topic); production adapter-chain transport remains open. */
  }

  part independentAutowareObservationGap010 : DeferredProductLineScope {
    doc /* GAP-MW-027: Autoware-side provenance for /vehicle/status/velocity_status was unavailable; the campaign-chain subset was observed (E-MW-011 gate 6: independent observer validated 10.0 m/s). A real Autoware node (autoware_vehicle_velocity_converter) now consumes the topic and produces twist_with_covariance with linear.x = 10.0 m/s (E-MW-013); full Autoware stack provenance remains open. */
  }

  part lifecycleUpdateFaultEvidenceGap010 : DeferredProductLineScope {
    doc /* GAP-MW-028: Target-runtime lifecycle, update/OTA, health, and fault evidence was unavailable. Fault subset observed (E-MW-011 gate 7: ingress rejects non-valid envelopes); health disposition now observed (E-MW-014: degraded=stale within 5s of provider loss, restored=healthy on resume — AC-MW-010-03 satisfied); lifecycle/update/OTA and reverse path remain open (gate 8 not claimed). */
  }

  verification def SignalTranslationVerification {
    subject verifiedBench : MiddlewareIntegrationVandVBench;
    objective signalTranslationObjective010 {
      verify acceptanceCriterion010SignalTranslation;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : MiddlewareScenarioIdentity = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def LifecycleCoordinationVerification {
    subject verifiedBench : MiddlewareIntegrationVandVBench;
    objective lifecycleCoordinationObjective010 {
      verify acceptanceCriterion010LifecycleCoordination;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : MiddlewareScenarioIdentity = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def HealthForwardingVerification {
    subject verifiedBench : MiddlewareIntegrationVandVBench;
    objective healthForwardingObjective010 {
      verify acceptanceCriterion010HealthForwarding;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : MiddlewareScenarioIdentity = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VehicleStartupValidation {
    doc /*
     * Modeled as a verification case over System 2 acceptance criteria
     * (SysML v2 provides no native validation-case keyword). Any validation
     * claim against stakeholder needs, intended use, and intended users
     * remains separately scoped and is not made by this case.
     */
    subject verifiedBench : MiddlewareIntegrationVandVBench;
    objective vehicleStartupObjective010 {
      verify acceptanceCriterion010VehicleStartup;
      verify acceptanceCriterion010LifecycleCoordination;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : MiddlewareScenarioIdentity = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def UpdateCoordinationValidation {
    doc /*
     * Modeled as a verification case over System 2 acceptance criteria
     * (SysML v2 provides no native validation-case keyword). Any validation
     * claim against stakeholder needs, intended use, and intended users
     * remains separately scoped and is not made by this case.
     */
    subject verifiedBench : MiddlewareIntegrationVandVBench;
    objective updateCoordinationObjective010 {
      verify acceptanceCriterion010UpdateCoordination;
      verify acceptanceCriterion010LifecycleCoordination;
      verify acceptanceCriterion010HealthForwarding;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : MiddlewareScenarioIdentity = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def FaultDetectionValidation {
    doc /*
     * Modeled as a verification case over System 2 acceptance criteria
     * (SysML v2 provides no native validation-case keyword). Any validation
     * claim against stakeholder needs, intended use, and intended users
     * remains separately scoped and is not made by this case.
     */
    subject verifiedBench : MiddlewareIntegrationVandVBench;
    objective faultDetectionObjective010 {
      verify acceptanceCriterion010FaultDetection;
      verify acceptanceCriterion010HealthForwarding;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : MiddlewareScenarioIdentity = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapEvidenceOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification signalTranslationVerification010 : SignalTranslationVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> signalTranslationBench010;
  }

  verification lifecycleCoordinationVerification010 : LifecycleCoordinationVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> lifecycleCoordinationBench010;
  }

  verification healthForwardingVerification010 : HealthForwardingVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> healthForwardingBench010;
  }

  verification vehicleStartupValidation010 : VehicleStartupValidation {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> vehicleStartupBench010;
  }

  verification updateCoordinationValidation010 : UpdateCoordinationValidation {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> updateCoordinationBench010;
  }

  verification faultDetectionValidation010 : FaultDetectionValidation {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> faultDetectionBench010;
  }

  part verificationSystem010 {
    perform signalTranslationVerification010;
    perform lifecycleCoordinationVerification010;
    perform healthForwardingVerification010;
    perform vehicleStartupValidation010;
    perform updateCoordinationValidation010;
    perform faultDetectionValidation010;
  }

  dependency signalTranslationVerificationToRequirement
    from acceptanceCriterion010SignalTranslation
    to reqProvideMiddlewareSignalAccess;
  dependency lifecycleVerificationToRequirement
    from acceptanceCriterion010LifecycleCoordination
    to reqCoordinateMiddlewareLifecycle;
  dependency healthVerificationToRequirement
    from acceptanceCriterion010HealthForwarding
    to reqMonitorMiddlewareHealth;
  dependency startupValidationToDiscoveryRequirement
    from acceptanceCriterion010VehicleStartup
    to reqProvideServiceDiscovery;
  dependency startupValidationToLifecycleRequirement
    from acceptanceCriterion010VehicleStartup
    to reqCoordinateMiddlewareLifecycle;
  dependency updateValidationToRequirement
    from acceptanceCriterion010UpdateCoordination
    to reqCoordinateMiddlewareUpdates;
  dependency faultValidationToHealthRequirement
    from acceptanceCriterion010FaultDetection
    to reqMonitorMiddlewareHealth;
  dependency faultValidationToSafetyRequirement
    from acceptanceCriterion010FaultDetection
    to reqIsolateSafetyPath;
  dependency evidenceIndependenceToTraceabilityRequirement
    from acceptanceCriterion010EvidenceIndependence
    to reqMaintainMiddlewareBoundaryTraceability;

  dependency verificationConfiguredMemberTrace
    from verificationSystem010
    to DE4SDV_MiddlewareVariabilityConfiguration::configuredMember;
  dependency verificationPhysicalBoundaryTrace
    from verificationSystem010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftware;
  dependency verificationSignalMappingTrace
    from signalTranslationVerification010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftware::adapter::aaosSignal::vehicleSpeed;
  dependency verificationContractTrace
    from signalTranslationVerification010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftwareSources::referenceInteropBenchSource;
  dependency verificationExecutionEnvironmentTrace
    from verificationSystem010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::aaosBuildRuntimeEnvironmentCandidate;
  dependency boundedBootBaselineTrace
    from boundedAAOSBootBaseline010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalEnablingSystemGap;
  dependency providerBindingGapTrace
    from plannedTargetRuntimeEvidence010
    to providerBindingEvidenceGap010;
  dependency transportGapTrace
    from plannedTargetRuntimeEvidence010
    to crossDomainTransportEvidenceGap010;
  dependency independentObserverGapTrace
    from plannedTargetRuntimeEvidence010
    to independentAutowareObservationGap010;
  dependency lifecycleUpdateFaultGapTrace
    from plannedTargetRuntimeEvidence010
    to lifecycleUpdateFaultEvidenceGap010;
  dependency targetRuntimeEvidenceToPhase9Gap
    from plannedTargetRuntimeEvidence010
    to DE4SDV_MiddlewareVariabilityConfiguration::configuredRuntimeEvidenceGap;
  dependency targetRuntimeEvidenceToPhysicalSourceContractGap
    from plannedTargetRuntimeEvidence010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSourceContractGap;
  dependency targetRuntimeEvidenceToPhysicalProcessDeploymentGap
    from plannedTargetRuntimeEvidence010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalProcessDeploymentGap;
  dependency targetRuntimeEvidenceToVelocitySignalContractGap
    from plannedTargetRuntimeEvidence010
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::velocitySignalContractGap;

  /* Claim-argument-evidence layer (INC-MW-010).
   *
   * The claim states what the configured member is asserted to realize within
   * the declared claim boundary. Arguments support the claim per verification
   * dimension. Counter-claims bound the claim where evidence is not yet
   * established (GAP-MW-025..028). Verification cases and evidence items
   * reinforce the arguments they are traced to. Planned or blocked evidence
   * never upgrades a verdict to pass.
   */

  requirement def MiddlewareClaim
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement def MiddlewareAssuranceArgument
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement def MiddlewareCounterClaim
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement mw010ReferenceContractClaim : MiddlewareClaim {
    doc /*
     * CLM-MW-010-01: for MW-CONFIG-001 on the retained two-VM execution
     * environment, the forward Vehicle.Speed slice was observed from the AAOS
     * provider through the direct adapter path to ROS 2, where one real
     * Autoware consumer produced the expected converted output. Invalid
     * envelopes were rejected and provider loss/restoration produced explicit
     * degraded/restored health dispositions.
     */
    subject claimSubject : MiddlewareIntegrationVandVBench;
    require constraint {
      doc /*
       * The claim requires retained E-MW-011 through E-MW-014 evidence bound to
       * the configured member, exact contracts, execution environment, and
       * observer identities. It excludes complete lifecycle ordering,
       * update/OTA, reverse-path, production, full-stack Autoware, safety, and
       * certification claims.
       */
    }
  }

  requirement signalTranslationArgument010 : MiddlewareAssuranceArgument {
    doc /* AGT-MW-010-01: argues that AC-MW-010-01 (bounded signal translation semantics) is satisfied within the accepted claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement lifecycleCoordinationArgument010 : MiddlewareAssuranceArgument {
    doc /* AGT-MW-010-02: records the AC-MW-010-02 verification branch; complete lifecycle transition ordering is deferred and does not support the accepted claim. */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement healthForwardingArgument010 : MiddlewareAssuranceArgument {
    doc /* AGT-MW-010-03: argues that AC-MW-010-03 (provider-loss health disposition without relabeling) is satisfied within the accepted claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement vehicleStartupArgument010 : MiddlewareAssuranceArgument {
    doc /* AGT-MW-010-04: argues that AC-MW-010-04 (bounded provider, registration, and discovery startup observations) is satisfied within the accepted claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement updateCoordinationArgument010 : MiddlewareAssuranceArgument {
    doc /* AGT-MW-010-05: records the AC-MW-010-05 verification branch; update/OTA contract preservation is deferred and does not support the accepted claim. */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement faultDetectionArgument010 : MiddlewareAssuranceArgument {
    doc /* AGT-MW-010-06: argues that AC-MW-010-06 (invalid-envelope rejection) is satisfied within the accepted claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement counterClaim010ProviderBinding : MiddlewareCounterClaim {
    doc /* CCM-MW-010-01: bounds the claim for GAP-MW-025 scope (production adapter-chain provider binding; campaign-chain provider observed by E-MW-011). */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement counterClaim010CrossDomainTransport : MiddlewareCounterClaim {
    doc /* CCM-MW-010-02: bounds the claim for GAP-MW-026 scope (production adapter-chain Android/KVM-to-Linux/ROS 2 transport; campaign-chain transport observed by E-MW-011). */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement counterClaim010IndependentObservation : MiddlewareCounterClaim {
    doc /* CCM-MW-010-03: bounds the claim for GAP-MW-027 scope (full Autoware stack provenance; real consumer node observed by E-MW-013). */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  requirement counterClaim010LifecycleUpdateFault : MiddlewareCounterClaim {
    doc /* CCM-MW-010-04: bounds the claim for GAP-MW-028 scope (lifecycle, update/OTA, reverse path; fault rejection observed by E-MW-011 gate 7, health disposition observed by E-MW-014). */
    subject bench : MiddlewareIntegrationVandVBench;
  }

  dependency claimSupportedBySignalArgument
    from signalTranslationArgument010 to mw010ReferenceContractClaim;
  dependency claimSupportedByHealthArgument
    from healthForwardingArgument010 to mw010ReferenceContractClaim;
  dependency claimSupportedByStartupArgument
    from vehicleStartupArgument010 to mw010ReferenceContractClaim;
  dependency claimSupportedByFaultArgument
    from faultDetectionArgument010 to mw010ReferenceContractClaim;

  dependency signalVerificationReinforcesArgument
    from signalTranslationVerification010 to signalTranslationArgument010;
  dependency lifecycleVerificationReinforcesArgument
    from lifecycleCoordinationVerification010 to lifecycleCoordinationArgument010;
  dependency healthVerificationReinforcesArgument
    from healthForwardingVerification010 to healthForwardingArgument010;
  dependency startupValidationReinforcesArgument
    from vehicleStartupValidation010 to vehicleStartupArgument010;
  dependency updateValidationReinforcesArgument
    from updateCoordinationValidation010 to updateCoordinationArgument010;
  dependency faultValidationReinforcesArgument
    from faultDetectionValidation010 to faultDetectionArgument010;

  dependency contractEvidenceReinforcesArgument
    from contractAndRehearsalEvidence010 to signalTranslationArgument010;
  dependency bootBaselineReinforcesArgument
    from boundedAAOSBootBaseline010 to vehicleStartupArgument010;
  dependency runtimeCampaignReinforcesSignalArgument
    from runtimeCampaignEvidence011 to signalTranslationArgument010;
  dependency runtimeCampaignReinforcesStartupArgument
    from runtimeCampaignEvidence011 to vehicleStartupArgument010;
  dependency runtimeCampaignReinforcesFaultArgument
    from runtimeCampaignEvidence011 to faultDetectionArgument010;
  dependency runtimeAdapterPathReinforcesSignalArgument
    from runtimeAdapterPathEvidence012 to signalTranslationArgument010;
  dependency runtimeAdapterPathReinforcesStartupArgument
    from runtimeAdapterPathEvidence012 to vehicleStartupArgument010;
  dependency runtimeAdapterPathReinforcesFaultArgument
    from runtimeAdapterPathEvidence012 to faultDetectionArgument010;
  dependency runtimeAutowareConsumerReinforcesSignalArgument
    from runtimeAutowareConsumerEvidence013 to signalTranslationArgument010;
  dependency runtimeHealthDispositionReinforcesHealthArgument
    from runtimeHealthDispositionEvidence014 to healthForwardingArgument010;
  dependency runtimeCampaignTraceToClaim
    from runtimeCampaignEvidence011 to mw010ReferenceContractClaim;
  dependency runtimeAdapterPathTraceToClaim
    from runtimeAdapterPathEvidence012 to mw010ReferenceContractClaim;
  dependency runtimeAutowareConsumerTraceToClaim
    from runtimeAutowareConsumerEvidence013 to mw010ReferenceContractClaim;
  dependency runtimeHealthDispositionTraceToClaim
    from runtimeHealthDispositionEvidence014 to mw010ReferenceContractClaim;

  dependency counterClaimProviderBindingCountersClaim
    from counterClaim010ProviderBinding to mw010ReferenceContractClaim;
  dependency counterClaimTransportCountersClaim
    from counterClaim010CrossDomainTransport to mw010ReferenceContractClaim;
  dependency counterClaimObservationCountersClaim
    from counterClaim010IndependentObservation to mw010ReferenceContractClaim;
  dependency counterClaimLifecycleCountersClaim
    from counterClaim010LifecycleUpdateFault to mw010ReferenceContractClaim;

  dependency counterClaimProviderBindingGapTrace
    from counterClaim010ProviderBinding to providerBindingEvidenceGap010;
  dependency counterClaimTransportGapTrace
    from counterClaim010CrossDomainTransport to crossDomainTransportEvidenceGap010;
  dependency counterClaimObservationGapTrace
    from counterClaim010IndependentObservation to independentAutowareObservationGap010;
  dependency counterClaimLifecycleGapTrace
    from counterClaim010LifecycleUpdateFault to lifecycleUpdateFaultEvidenceGap010;

  dependency boundedClaimToBaselineDecision010
    from mw010ReferenceContractClaim to boundedBaselineDecision010;
  dependency runtimeCampaignToBaselineDecision010
    from runtimeCampaignEvidence011 to boundedBaselineDecision010;
  dependency runtimeAdapterPathToBaselineDecision010
    from runtimeAdapterPathEvidence012 to boundedBaselineDecision010;
  dependency runtimeAutowareConsumerToBaselineDecision010
    from runtimeAutowareConsumerEvidence013 to boundedBaselineDecision010;
  dependency runtimeHealthDispositionToBaselineDecision010
    from runtimeHealthDispositionEvidence014 to boundedBaselineDecision010;
  dependency deferredProviderCounterclaimToBaselineDecision010
    from counterClaim010ProviderBinding to boundedBaselineDecision010;
  dependency deferredTransportCounterclaimToBaselineDecision010
    from counterClaim010CrossDomainTransport to boundedBaselineDecision010;
  dependency deferredObservationCounterclaimToBaselineDecision010
    from counterClaim010IndependentObservation to boundedBaselineDecision010;
  dependency deferredLifecycleCounterclaimToBaselineDecision010
    from counterClaim010LifecycleUpdateFault to boundedBaselineDecision010;
  dependency successorIncrementToBaselineDecision010
    from successorIncrementDecision010 to boundedBaselineDecision010;

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims, counterclaims, retained evidence, and the bounded baseline decision. */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view middlewareVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }
    doc /*
     * Positive Phase 12 slice: the bounded claim, retained evidence branches,
     * accepted baseline decision, and separately framed successor decision.
     * Open counterclaims and gaps are published separately.
     */
    expose boundedBaselineDecision010;
    expose successorIncrementDecision010;
    expose mw010ReferenceContractClaim;
    expose runtimeCampaignEvidence011;
    expose runtimeAdapterPathEvidence012;
    expose runtimeAutowareConsumerEvidence013;
    expose runtimeHealthDispositionEvidence014;
    expose signalTranslationArgument010;
    expose healthForwardingArgument010;
    expose vehicleStartupArgument010;
    expose faultDetectionArgument010;
    expose contractAndRehearsalEvidence010;
    expose boundedAAOSBootBaseline010;
    expose boundedClaimToBaselineDecision010;
    expose runtimeCampaignToBaselineDecision010;
    expose runtimeAdapterPathToBaselineDecision010;
    expose runtimeAutowareConsumerToBaselineDecision010;
    expose runtimeHealthDispositionToBaselineDecision010;
    expose successorIncrementToBaselineDecision010;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }

  view middlewareOpenCounterclaimAssuranceView {
    viewpoint selectedOpenCounterclaimAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }
    doc /*
     * Challenge slice: unresolved counterclaims and explicit gaps retained by
     * the bounded Phase 12 decision. They prevent broader production, full-
     * stack, lifecycle/update, and reverse-path assurance.
     */
    expose boundedBaselineDecision010;
    expose mw010ReferenceContractClaim;
    expose counterClaim010ProviderBinding;
    expose counterClaim010CrossDomainTransport;
    expose counterClaim010IndependentObservation;
    expose counterClaim010LifecycleUpdateFault;
    expose providerBindingEvidenceGap010;
    expose crossDomainTransportEvidenceGap010;
    expose independentAutowareObservationGap010;
    expose lifecycleUpdateFaultEvidenceGap010;
    expose counterClaimProviderBindingGapTrace;
    expose counterClaimTransportGapTrace;
    expose counterClaimObservationGapTrace;
    expose counterClaimLifecycleGapTrace;
    expose deferredProviderCounterclaimToBaselineDecision010;
    expose deferredTransportCounterclaimToBaselineDecision010;
    expose deferredObservationCounterclaimToBaselineDecision010;
    expose deferredLifecycleCounterclaimToBaselineDecision010;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
