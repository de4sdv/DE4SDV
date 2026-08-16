/*
 * DE4SDV middleware verification and validation/evidence model slice.
 *
 * INC-MW-010 defines the verification cases, validation scenarios, acceptance
 * criteria, evidence roles, and explicit claim boundary for the configured
 * Autoware + AndroidSDV member. It may be planned and exercised incrementally;
 * planned cases are not runtime passes.
 *
 * Contract tests and the bounded Cuttlefish boot record support lower-level
 * claims. Target-runtime provider, transport, ROS 2, Autoware, lifecycle,
 * update, and fault evidence remain blocked until the executable realization
 * and independent observation path exist.
 */

package DE4SDV_MW010VerificationEvidence {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ExecutionEnvironments::*;
  private import DE4SDV_MWRequirements::Features::Middleware::Requirements::*;
  private import DE4SDV_MWFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::*;
  private import DE4SDV_MWPhysicalSoftwareRealization::*;
  private import DE4SDV_MWVariabilityConfiguration::*;
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import ScalarValues::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part incMW010 : FeatureIncrement {
    doc /* INC-MW-010: middleware verification, validation, and evidence. */
  }

  enum def ScenarioIdentity010 {
    signalTranslation;
    lifecycleCoordination;
    healthForwarding;
    vehicleStartup;
    updateCoordination;
    faultDetection;
  }

  enum def EvidenceOutcome010 {
    passBoundedVerification;
    passBoundedValidation;
    failObservedBehavior;
    inconclusiveMissingEvidence;
    blockedTargetRuntime;
    errorEvidence;
  }

  enum def EvidenceDisposition010 {
    planned;
    observedBounded;
    partial;
    blocked;
    accepted;
    rejected;
  }

  item def VehicleSpeedTranslationObservation010 {
    attribute inputSpeedKmh : Real;
    attribute expectedVelocityMps : Real;
    attribute observedVelocityMps : Real;
    attribute sourceContractIdentity : String;
    attribute consumerContractIdentity : String;
    attribute independentObservation : Boolean;
  }

  item def LifecycleObservation010 {
    attribute stateName : String;
    attribute predecessorState : String;
    attribute successorState : String;
    attribute transitionObserved : Boolean;
  }

  item def HealthObservation010 {
    attribute healthState : String;
    attribute sourceFresh : Boolean;
    attribute forwarded : Boolean;
    attribute faultIdentity : String;
  }

  item def RetainedMiddlewareEvidence010 {
    attribute configurationIdentity : String;
    attribute executionEnvironmentIdentity : String;
    attribute contractIdentity : String;
    attribute rawObservationArtifact : String;
    attribute independentObserverIdentity : String;
    attribute disposition : EvidenceDisposition010;
    attribute claimBoundary : String;
  }

  item def ReplayedMiddlewareEvaluation010 {
    attribute scenario : ScenarioIdentity010;
    attribute outcome : EvidenceOutcome010;
    attribute acceptanceSummary : String;
  }

  calc def Map010OutcomeToVerdict {
    in outcome : EvidenceOutcome010;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome010::passBoundedVerification? VerdictKind::pass
      else if outcome == EvidenceOutcome010::passBoundedValidation? VerdictKind::pass
      else if outcome == EvidenceOutcome010::failObservedBehavior? VerdictKind::fail
      else if outcome == EvidenceOutcome010::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def MiddlewareIntegrationVandVBench010 {
    doc /*
     * System 1 is the configured member under evaluation. System 2 is the
     * engineering/build/test environment and is not a product selection.
     */
    part system1MemberProduct : MWAutowareAAOSSDVConfiguredMember;
    part system2TestEnvironment : AOSPAAOSBuildRuntimeEnvironment;
    attribute scenario : ScenarioIdentity010;
  }

  part signalTranslationBench010 : MiddlewareIntegrationVandVBench010 {
    attribute :>> scenario = ScenarioIdentity010::signalTranslation;
  }

  part lifecycleCoordinationBench010 : MiddlewareIntegrationVandVBench010 {
    attribute :>> scenario = ScenarioIdentity010::lifecycleCoordination;
  }

  part healthForwardingBench010 : MiddlewareIntegrationVandVBench010 {
    attribute :>> scenario = ScenarioIdentity010::healthForwarding;
  }

  part vehicleStartupBench010 : MiddlewareIntegrationVandVBench010 {
    attribute :>> scenario = ScenarioIdentity010::vehicleStartup;
  }

  part updateCoordinationBench010 : MiddlewareIntegrationVandVBench010 {
    attribute :>> scenario = ScenarioIdentity010::updateCoordination;
  }

  part faultDetectionBench010 : MiddlewareIntegrationVandVBench010 {
    attribute :>> scenario = ScenarioIdentity010::faultDetection;
  }

  requirement def MiddlewareAcceptanceCriterion010
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement acceptanceCriterion010SignalTranslation : MiddlewareAcceptanceCriterion010 {
    doc /* AC-MW-010-01; bounded verification of the selected Vehicle.Speed slice. */
    subject bench : MiddlewareIntegrationVandVBench010;
    require constraint {
      doc /* The selected contract shall preserve Vehicle.Speed [km/h] semantics, map 36 km/h to 10 m/s and 72 km/h to 20 m/s through division by 3.6, reject invalid/non-finite samples, and expose the resulting VelocityReport field to an independent observer. */
    }
  }

  requirement acceptanceCriterion010LifecycleCoordination : MiddlewareAcceptanceCriterion010 {
    doc /* AC-MW-010-02; bounded verification of integration lifecycle behavior. */
    subject bench : MiddlewareIntegrationVandVBench010;
    require constraint {
      doc /* The integration boundary shall make startup, initializing, operational, degraded, and shutdown behavior observable, preserve the declared transition ordering, and prevent use before required binding/readiness. */
    }
  }

  requirement acceptanceCriterion010HealthForwarding : MiddlewareAcceptanceCriterion010 {
    doc /* AC-MW-010-03; bounded verification of health forwarding. */
    subject bench : MiddlewareIntegrationVandVBench010;
    require constraint {
      doc /* Missing, stale, inconsistent, or unavailable provider/transport/consumer health shall produce an observable degraded or unavailable disposition and shall be forwarded to the application boundary without being relabeled as healthy. */
    }
  }

  requirement acceptanceCriterion010VehicleStartup : MiddlewareAcceptanceCriterion010 {
    doc /* AC-MW-010-04; validation of vehicle/application startup. */
    subject bench : MiddlewareIntegrationVandVBench010;
    require constraint {
      doc /* A configured member startup scenario shall prove provider registration, service discovery/binding, transport readiness, adapter readiness, and ROS 2 consumer readiness in causal order before the signal is accepted. */
    }
  }

  requirement acceptanceCriterion010UpdateCoordination : MiddlewareAcceptanceCriterion010 {
    doc /* AC-MW-010-05; validation of integration update behavior. */
    subject bench : MiddlewareIntegrationVandVBench010;
    require constraint {
      doc /* An update/OTA scenario shall retain pre-update and post-update identities and observations and shall detect, rather than silently accept, loss or incompatible change of the required signal, lifecycle, health, discovery, or consumer contracts. */
    }
  }

  requirement acceptanceCriterion010FaultDetection : MiddlewareAcceptanceCriterion010 {
    doc /* AC-MW-010-06; validation of fault detection and containment. */
    subject bench : MiddlewareIntegrationVandVBench010;
    require constraint {
      doc /* Provider, binding, discovery, transport, adapter, and consumer faults shall be detected and classified at the integration boundary; non-safety middleware failure shall not create an uncontrolled emergency intervention command. */
    }
  }

  requirement acceptanceCriterion010EvidenceIndependence : MiddlewareAcceptanceCriterion010 {
    doc /* AC-MW-010-07; evidence integrity and claim-boundary criterion. */
    subject bench : MiddlewareIntegrationVandVBench010;
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
     * scenarios on the configured member.
     */
  }

  part providerBindingEvidenceGap010 : DeferredProductLineScope {
    doc /* GAP-MW-025: Generated/usable VSIDL binding and deployed provider behavior remain unavailable. */
  }

  part crossDomainTransportEvidenceGap010 : DeferredProductLineScope {
    doc /* GAP-MW-026: Android/KVM-to-Linux/ROS 2 transport, discovery, and deployment evidence remain unavailable. */
  }

  part independentAutowareObservationGap010 : DeferredProductLineScope {
    doc /* GAP-MW-027: An independent observation of /vehicle/status/velocity_status and Autoware-side provenance remains unavailable. */
  }

  part lifecycleUpdateFaultEvidenceGap010 : DeferredProductLineScope {
    doc /* GAP-MW-028: Target-runtime lifecycle, update/OTA, health, and fault evidence remains unavailable. */
  }

  verification def SignalTranslationVerification010 {
    subject verifiedBench : MiddlewareIntegrationVandVBench010;
    objective signalTranslationObjective010 {
      verify acceptanceCriterion010SignalTranslation;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence010;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity010 = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence010 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation010;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation010 = processData.replayedEvaluation;
      out verdict : VerdictKind = Map010OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def LifecycleCoordinationVerification010 {
    subject verifiedBench : MiddlewareIntegrationVandVBench010;
    objective lifecycleCoordinationObjective010 {
      verify acceptanceCriterion010LifecycleCoordination;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence010;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity010 = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence010 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation010;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation010 = processData.replayedEvaluation;
      out verdict : VerdictKind = Map010OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def HealthForwardingVerification010 {
    subject verifiedBench : MiddlewareIntegrationVandVBench010;
    objective healthForwardingObjective010 {
      verify acceptanceCriterion010HealthForwarding;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence010;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity010 = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence010 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation010;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation010 = processData.replayedEvaluation;
      out verdict : VerdictKind = Map010OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VehicleStartupValidation010 {
    subject verifiedBench : MiddlewareIntegrationVandVBench010;
    objective vehicleStartupObjective010 {
      verify acceptanceCriterion010VehicleStartup;
      verify acceptanceCriterion010LifecycleCoordination;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence010;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity010 = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence010 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation010;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation010 = processData.replayedEvaluation;
      out verdict : VerdictKind = Map010OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def UpdateCoordinationValidation010 {
    subject verifiedBench : MiddlewareIntegrationVandVBench010;
    objective updateCoordinationObjective010 {
      verify acceptanceCriterion010UpdateCoordination;
      verify acceptanceCriterion010LifecycleCoordination;
      verify acceptanceCriterion010HealthForwarding;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence010;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity010 = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence010 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation010;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation010 = processData.replayedEvaluation;
      out verdict : VerdictKind = Map010OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def FaultDetectionValidation010 {
    subject verifiedBench : MiddlewareIntegrationVandVBench010;
    objective faultDetectionObjective010 {
      verify acceptanceCriterion010FaultDetection;
      verify acceptanceCriterion010HealthForwarding;
      verify acceptanceCriterion010EvidenceIndependence;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedMiddlewareEvidence010;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity010 = verifiedBench.scenario;
      in item retainedEvidence : RetainedMiddlewareEvidence010 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedMiddlewareEvaluation010;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedMiddlewareEvaluation010 = processData.replayedEvaluation;
      out verdict : VerdictKind = Map010OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification signalTranslationVerification010 : SignalTranslationVerification010 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> signalTranslationBench010;
  }

  verification lifecycleCoordinationVerification010 : LifecycleCoordinationVerification010 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> lifecycleCoordinationBench010;
  }

  verification healthForwardingVerification010 : HealthForwardingVerification010 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> healthForwardingBench010;
  }

  verification vehicleStartupValidation010 : VehicleStartupValidation010 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> vehicleStartupBench010;
  }

  verification updateCoordinationValidation010 : UpdateCoordinationValidation010 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> updateCoordinationBench010;
  }

  verification faultDetectionValidation010 : FaultDetectionValidation010 {
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
    to DE4SDV_MWVariabilityConfiguration::configuredMember;
  dependency verificationPhysicalBoundaryTrace
    from verificationSystem010
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSoftware;
  dependency verificationSignalMappingTrace
    from signalTranslationVerification010
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSoftware::adapter::aaosSignal::vehicleSpeed;
  dependency verificationContractTrace
    from signalTranslationVerification010
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSoftware::referenceInteropBenchSource;
  dependency verificationExecutionEnvironmentTrace
    from verificationSystem010
    to DE4SDV_MWPhysicalSoftwareRealization::aaosBuildRuntimeEnvironmentCandidate;
  dependency boundedBootBaselineTrace
    from boundedAAOSBootBaseline010
    to DE4SDV_MWPhysicalSoftwareRealization::physicalEnablingSystemGap;
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
    to DE4SDV_MWVariabilityConfiguration::configuredRuntimeEvidenceGap;
  dependency targetRuntimeEvidenceToPhysicalSourceContractGap
    from plannedTargetRuntimeEvidence010
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSourceContractGap;
  dependency targetRuntimeEvidenceToPhysicalProcessDeploymentGap
    from plannedTargetRuntimeEvidence010
    to DE4SDV_MWPhysicalSoftwareRealization::physicalProcessDeploymentGap;
  dependency targetRuntimeEvidenceToVelocitySignalContractGap
    from plannedTargetRuntimeEvidence010
    to DE4SDV_MWPhysicalSoftwareRealization::velocitySignalContractGap;

  /* Claim-argument-evidence layer (INC-MW-010).
   *
   * The claim states what the configured member is asserted to realize within
   * the declared claim boundary. Arguments support the claim per verification
   * dimension. Counter-claims bound the claim where evidence is not yet
   * established (GAP-MW-025..028). Verification cases and evidence items
   * reinforce the arguments they are traced to. Planned or blocked evidence
   * never upgrades a verdict to pass.
   */

  requirement def MiddlewareClaim010
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement def MiddlewareArgument010
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement def MiddlewareCounterClaim010
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement mw010ReferenceContractClaim : MiddlewareClaim010 {
    doc /*
     * CLM-MW-010-01: the configured Autoware + AndroidSDV member realizes the
     * Vehicle.Speed reference contract within the declared claim boundary:
     * signal translation semantics, lifecycle coordination, health forwarding,
     * startup and update coordination, and fault containment are observable,
     * replayable, and independently observed.
     */
    subject claimSubject : MiddlewareIntegrationVandVBench010;
    require constraint {
      doc /* The claim is bounded by retained, replayable, independently
        observed evidence bound to the configured member, execution
        environment, and contract identities. It is not target-runtime proof. */
    }
  }

  requirement signalTranslationArgument010 : MiddlewareArgument010 {
    doc /* AGT-MW-010-01: argues that AC-MW-010-01 (bounded signal translation semantics) is satisfied within the claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement lifecycleCoordinationArgument010 : MiddlewareArgument010 {
    doc /* AGT-MW-010-02: argues that AC-MW-010-02 (observable integration lifecycle coordination) is satisfied within the claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement healthForwardingArgument010 : MiddlewareArgument010 {
    doc /* AGT-MW-010-03: argues that AC-MW-010-03 (health forwarding without relabeling) is satisfied within the claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement vehicleStartupArgument010 : MiddlewareArgument010 {
    doc /* AGT-MW-010-04: argues that AC-MW-010-04 (causally ordered startup readiness) is satisfied within the claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement updateCoordinationArgument010 : MiddlewareArgument010 {
    doc /* AGT-MW-010-05: argues that AC-MW-010-05 (update coordination with identity retention) is satisfied within the claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement faultDetectionArgument010 : MiddlewareArgument010 {
    doc /* AGT-MW-010-06: argues that AC-MW-010-06 (fault detection and containment) is satisfied within the claim boundary. */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement counterClaim010ProviderBinding : MiddlewareCounterClaim010 {
    doc /* CCM-MW-010-01: bounds the claim for GAP-MW-025 scope (provider binding and deployed provider behavior). */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement counterClaim010CrossDomainTransport : MiddlewareCounterClaim010 {
    doc /* CCM-MW-010-02: bounds the claim for GAP-MW-026 scope (Android/KVM-to-Linux/ROS 2 transport, discovery, deployment). */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement counterClaim010IndependentObservation : MiddlewareCounterClaim010 {
    doc /* CCM-MW-010-03: bounds the claim for GAP-MW-027 scope (independent Autoware observation). */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  requirement counterClaim010LifecycleUpdateFault : MiddlewareCounterClaim010 {
    doc /* CCM-MW-010-04: bounds the claim for GAP-MW-028 scope (target-runtime lifecycle, update/OTA, health, fault). */
    subject bench : MiddlewareIntegrationVandVBench010;
  }

  dependency claimSupportedBySignalArgument
    from signalTranslationArgument010 to mw010ReferenceContractClaim;
  dependency claimSupportedByLifecycleArgument
    from lifecycleCoordinationArgument010 to mw010ReferenceContractClaim;
  dependency claimSupportedByHealthArgument
    from healthForwardingArgument010 to mw010ReferenceContractClaim;
  dependency claimSupportedByStartupArgument
    from vehicleStartupArgument010 to mw010ReferenceContractClaim;
  dependency claimSupportedByUpdateArgument
    from updateCoordinationArgument010 to mw010ReferenceContractClaim;
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

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view mw010VerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }
    expose mw010ReferenceContractClaim;
    expose signalTranslationArgument010;
    expose lifecycleCoordinationArgument010;
    expose healthForwardingArgument010;
    expose vehicleStartupArgument010;
    expose updateCoordinationArgument010;
    expose faultDetectionArgument010;
    expose contractAndRehearsalEvidence010;
    expose boundedAAOSBootBaseline010;
    expose counterClaim010ProviderBinding;
    expose counterClaim010CrossDomainTransport;
    expose counterClaim010IndependentObservation;
    expose counterClaim010LifecycleUpdateFault;
    expose providerBindingEvidenceGap010;
    expose crossDomainTransportEvidenceGap010;
    expose independentAutowareObservationGap010;
    expose lifecycleUpdateFaultEvidenceGap010;
    expose claimSupportedBySignalArgument;
    expose claimSupportedByLifecycleArgument;
    expose claimSupportedByHealthArgument;
    expose claimSupportedByStartupArgument;
    expose claimSupportedByUpdateArgument;
    expose claimSupportedByFaultArgument;
    expose contractEvidenceReinforcesArgument;
    expose bootBaselineReinforcesArgument;
    expose counterClaimProviderBindingCountersClaim;
    expose counterClaimTransportCountersClaim;
    expose counterClaimObservationCountersClaim;
    expose counterClaimLifecycleCountersClaim;
    expose counterClaimProviderBindingGapTrace;
    expose counterClaimTransportGapTrace;
    expose counterClaimObservationGapTrace;
    expose counterClaimLifecycleGapTrace;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
