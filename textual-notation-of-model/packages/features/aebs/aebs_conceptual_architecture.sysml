/*
 * DE4SDV AEBS system architecture model slice.
 *
 * This package mirrors INC-AEBS-006 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-conceptual-architecture.yaml.
 *
 * Domain boundary: system architecture only. Autoware, ROS 2/DDS,
 * Eclipse S-CORE, Android SDV/AAOS, middleware adapters, processes, ECUs,
 * sensors, networks, actuators, calibrated thresholds, and compliance claims
 * are intentionally excluded.
 *
 * Semantic basis:
 * - SysML v2 specification section 7.15: allocation assigns responsibility
 *   for realizing features of one element to another element.
 * - Systems-Modeling/SysML-v2-Release commit 3f895b73265276bff92c6f67ac407486e49ffe6d,
 *   validation/12-Dependency Relationships/12b-Allocation-1.sysml.
 * - State decomposition follows the same release's validation/05-State-based
 *   Behavior/5-State-based Behavior-1.sysml.
 */

package DE4SDV_AEBSConceptualArchitecture {
  private import DE4SDV_AEBSFunctionalBehavior::Features::AEBS::FunctionalBehavior::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;

  /* ──────────────────────────────────────────
   * Conceptual information definitions
   * ────────────────────────────────────────── */

  enum def AEBSAvailabilityKind {
    unavailable;
    degraded;
    valid;
  }

  enum def AEBSInterventionKind {
    none;
    interventionRequested;
    inhibited;
  }

  item def AEBSOperatingContext {
    doc /*
     * Technology-neutral intervention-eligibility and inhibition context
     * supplied to the conceptual decision boundary. Concrete providers and
     * middleware are deferred to physical realization. System lifecycle and
     * AEBS availability are intentionally excluded; they have separate owners.
     *
     * This is intentionally a nominal, opaque contract in INC-AEBS-006. The
     * eligibility and inhibition facts carried by the item are not yet defined
     * as attributes because their source requirements and value domains remain
     * open. The item name establishes an exchange boundary, not a complete
     * data schema.
     */
  }

  item def PredictedEgoPath {
    doc /*
     * Technology-neutral predicted subject-vehicle path used for target
     * relevance and collision-risk evaluation. No trajectory message,
     * geometry representation, or prediction mechanism is selected here.
     *
     * This is intentionally a nominal, opaque contract in INC-AEBS-006.
     * Horizon, coordinate frame, validity, timing, uncertainty, and path
     * representation remain requirements/interface gaps. The item name
     * establishes the conceptual producer-consumer boundary without inventing
     * a physical or software schema.
     */
  }

  item def InterventionDecision {
    doc /*
     * Conceptual emergency-intervention intent after considering collision risk,
     * intervention eligibility/inhibition context, driver override, degradation,
     * and other inhibiting conditions.
     */
    attribute intervention : AEBSInterventionKind;
  }

  item def EmergencyInterventionRequest {
    doc /*
     * Technology-neutral request for emergency intervention after arbitration.
     * It expresses AEBS intent only. Brake-command values, lighting status,
     * vehicle-control arbitration, and actuator engagement are physical-domain
     * responsibilities deferred to INC-AEBS-007/008.
     */
    attribute intervention : AEBSInterventionKind;
  }

  dependency emergencyRequestFunctionalTrace
    from EmergencyInterventionRequest to EmergencyBrakingCommand;

  item def AEBSDegradationState {
    doc /*
     * Conceptual valid/degraded/unavailable result from health supervision.
     * Concrete diagnostic codes and middleware health services are deferred.
     */
    attribute availability : AEBSAvailabilityKind;
  }

  item def ObservationHealthStatus {
    doc /*
     * Conceptual freshness, consistency, and validity status produced while
     * acquiring vehicle-motion and target observations.
     *
     * This is intentionally a nominal, opaque contract in INC-AEBS-006.
     * The observation-specific status dimensions, timing, and aggregation
     * semantics remain requirements/interface gaps. AEBS availability is not
     * carried by this item; it is carried by AEBSDegradationState and solely
     * owned and produced by HealthAndDegradationSupervision.
     */
  }

  /* ──────────────────────────────────────────
   * Conceptual port definitions
   * ────────────────────────────────────────── */

  port def VehicleMotionInput {
    in item vehicleMotionState : VehicleMotionState;
  }

  port def VehicleMotionOutput {
    out item vehicleMotionState : VehicleMotionState;
  }

  port def ForwardTargetInput {
    in item forwardTargetState : ForwardTargetState;
  }

  port def ForwardTargetOutput {
    out item forwardTargetState : ForwardTargetState;
  }

  port def PredictedEgoPathInput {
    in item predictedEgoPath : PredictedEgoPath;
  }

  port def PredictedEgoPathOutput {
    out item predictedEgoPath : PredictedEgoPath;
  }

  port def CollisionRiskInput {
    in item collisionRiskAssessment : CollisionRiskAssessment;
  }

  port def CollisionRiskOutput {
    out item collisionRiskAssessment : CollisionRiskAssessment;
  }

  port def DriverOverrideInputPort {
    in item driverOverrideInput : DriverOverrideInput;
  }

  port def OperatingContextInput {
    in item operatingContext : AEBSOperatingContext;
  }

  port def InterventionDecisionInput {
    in item interventionDecision : InterventionDecision;
  }

  port def InterventionDecisionOutput {
    out item interventionDecision : InterventionDecision;
  }

  port def AEBSFailureStatusInput {
    in item aebsFailureStatus : AEBSFailureStatus;
  }

  port def DegradationStateInput {
    in item degradationState : AEBSDegradationState;
  }

  port def DegradationStateOutput {
    out item degradationState : AEBSDegradationState;
  }

  port def ObservationHealthInput {
    in item observationHealthStatus : ObservationHealthStatus;
  }

  port def ObservationHealthOutput {
    out item observationHealthStatus : ObservationHealthStatus;
  }

  port def DriverWarningRequestInput {
    in item driverWarningRequest : DriverWarningRequest;
  }

  port def DriverWarningRequestOutput {
    out item driverWarningRequest : DriverWarningRequest;
  }

  port def EmergencyInterventionInput {
    in item emergencyInterventionRequest : EmergencyInterventionRequest;
  }

  port def EmergencyInterventionOutput {
    out item emergencyInterventionRequest : EmergencyInterventionRequest;
  }

  port def FailureIndicationInput {
    in item failureIndicationRequest : FailureIndicationRequest;
  }

  port def FailureIndicationOutput {
    out item failureIndicationRequest : FailureIndicationRequest;
  }

  port def AEBSEvidenceEventOutput {
    out item aebsEvidenceEvent : AEBSEvidenceEvent;
  }

  /* ──────────────────────────────────────────
   * Conceptual component definitions
   * ────────────────────────────────────────── */

  part def StateAcquisitionAndNormalization {
    doc /*
     * Validates and normalizes vehicle-motion and target observations without
     * selecting a concrete sensor, service provider, or middleware.
     */
    port vehicleMotionIn : VehicleMotionInput;
    port targetObservationIn : ForwardTargetInput;
    port normalizedVehicleStateOut : VehicleMotionOutput;
    port normalizedTargetStateOut : ForwardTargetOutput;
    port observationHealthOut : ObservationHealthOutput;
  }

  part def EgoPathPrediction {
    doc /* Produces a technology-neutral predicted ego path from normalized vehicle motion. */
    port vehicleMotionIn : VehicleMotionInput;
    port predictedEgoPathOut : PredictedEgoPathOutput;
  }

  part def TargetProcessing {
    doc /* Selects and characterizes targets relevant to the predicted ego path. */
    port targetStateIn : ForwardTargetInput;
    port predictedEgoPathIn : PredictedEgoPathInput;
    port relevantTargetStateOut : ForwardTargetOutput;
  }

  part def CollisionRiskEvaluation {
    doc /*
     * Assesses forward collision risk from vehicle state, relevant target
     * state, predicted path, and explicitly open braking assumptions.
     */
    port vehicleMotionIn : VehicleMotionInput;
    port relevantTargetStateIn : ForwardTargetInput;
    port predictedEgoPathIn : PredictedEgoPathInput;
    port collisionRiskOut : CollisionRiskOutput;
  }

  part def InterventionDecisionAndArbitration {
    doc /*
     * Decides emergency-intervention intent while considering intervention
     * eligibility/inhibition context, driver override, degradation, and other
     * inhibiting conditions.
     */
    port collisionRiskIn : CollisionRiskInput;
    port driverOverrideIn : DriverOverrideInputPort;
    port operatingContextIn : OperatingContextInput;
    port degradationStateIn : DegradationStateInput;
    port interventionDecisionOut : InterventionDecisionOutput;

    exhibit state overrideStates {
      state noOverride;
      state overrideAccepted;
    }
  }

  part def DriverWarningManagement {
    doc /* Produces a conceptual driver-warning request without prescribing HMI technology. */
    port collisionRiskIn : CollisionRiskInput;
    port driverWarningRequestOut : DriverWarningRequestOutput;

    exhibit state warningStates {
      doc /* Warning state remains independent from override and intervention state. */
      state inactive;
      state warningRequested;
    }
  }

  part def EmergencyInterventionCoordination {
    doc /*
     * Issues and retains a conceptual emergency-intervention request only from an
     * affirmative arbitrated decision. Physical emergency supervision, command
     * gating, vehicle interfacing, and brake actuation are outside INC-AEBS-006.
     */
    port interventionDecisionIn : InterventionDecisionInput;
    port emergencyInterventionOut : EmergencyInterventionOutput;

    exhibit state interventionStates {
      doc /*
       * Emergency-state ownership is explicit. Numeric retention and release
       * guards remain open requirements and are not invented here.
       */
      state inactive;
      state interventionRequested;
      state emergencyActive;
    }
  }

  part def HealthAndDegradationSupervision {
    doc /*
     * Sole conceptual owner of valid, degraded, and unavailable AEBS operation;
     * reconciles input and subsystem health and requests failure indication.
     */
    port failureStatusIn : AEBSFailureStatusInput;
    port observationHealthIn : ObservationHealthInput;
    port degradationStateOut : DegradationStateOutput;
    port failureIndicationOut : FailureIndicationOutput;

    exhibit state availabilityStates {
      state valid;
      state degraded;
      state unavailable;
    }
  }

  part def EvidenceRecording {
    doc /*
     * Observes risk, decision, degradation, warning, intervention, and failure
     * events and emits a conceptual evidence event. Storage technology, retention,
     * and evidence acceptance criteria remain open.
     */
    port collisionRiskIn : CollisionRiskInput;
    port interventionDecisionIn : InterventionDecisionInput;
    port degradationStateIn : DegradationStateInput;
    port driverWarningRequestIn : DriverWarningRequestInput;
    port emergencyInterventionIn : EmergencyInterventionInput;
    port failureIndicationIn : FailureIndicationInput;
    port evidenceEventOut : AEBSEvidenceEventOutput;
  }

  /* ──────────────────────────────────────────
   * Conceptual system composition and exchanges
   * ────────────────────────────────────────── */

  part def VehicleTargetAEBSSystem {
    doc /*
     * Technology-neutral conceptual realization of the vehicle-target AEBS
     * functional baseline. Conceptual elements own responsibilities and exchange
     * typed information; no physical software or hardware realization is
     * implied.
     */

    port vehicleMotionObservationIn : VehicleMotionInput;
    port targetObservationIn : ForwardTargetInput;
    port driverOverrideObservationIn : DriverOverrideInputPort;
    port operatingContextIn : OperatingContextInput;
    port subsystemHealthIn : AEBSFailureStatusInput;

    port driverWarningRequestOut : DriverWarningRequestOutput;
    port emergencyInterventionRequestOut : EmergencyInterventionOutput;
    port failureIndicationRequestOut : FailureIndicationOutput;
    port evidenceEventOut : AEBSEvidenceEventOutput;

    part stateAcquisition : StateAcquisitionAndNormalization;
    part egoPathPrediction : EgoPathPrediction;
    part targetProcessing : TargetProcessing;
    part collisionRiskEvaluation : CollisionRiskEvaluation;
    part interventionDecision : InterventionDecisionAndArbitration;
    part warningManagement : DriverWarningManagement;
    part emergencyCoordination : EmergencyInterventionCoordination;
    part healthSupervision : HealthAndDegradationSupervision;
    part evidenceRecording : EvidenceRecording;

    exhibit state lifecycleStates {
      doc /*
       * System lifecycle is independent from component-owned warning,
       * intervention, and availability state machines.
       */
      state standby;
      state monitoring;
    }

    // Boundary delegation binds external ports to their conceptual owners.
    bind vehicleMotionObservationIn = stateAcquisition.vehicleMotionIn;
    bind targetObservationIn = stateAcquisition.targetObservationIn;
    bind driverOverrideObservationIn = interventionDecision.driverOverrideIn;
    bind operatingContextIn = interventionDecision.operatingContextIn;
    bind subsystemHealthIn = healthSupervision.failureStatusIn;

    // State, path, target, and risk exchanges.
    flow from stateAcquisition.normalizedVehicleStateOut.vehicleMotionState
      to egoPathPrediction.vehicleMotionIn.vehicleMotionState;
    flow from stateAcquisition.normalizedVehicleStateOut.vehicleMotionState
      to collisionRiskEvaluation.vehicleMotionIn.vehicleMotionState;
    flow from stateAcquisition.normalizedTargetStateOut.forwardTargetState
      to targetProcessing.targetStateIn.forwardTargetState;
    flow from stateAcquisition.observationHealthOut.observationHealthStatus
      to healthSupervision.observationHealthIn.observationHealthStatus;
    flow from egoPathPrediction.predictedEgoPathOut.predictedEgoPath
      to targetProcessing.predictedEgoPathIn.predictedEgoPath;
    flow from egoPathPrediction.predictedEgoPathOut.predictedEgoPath
      to collisionRiskEvaluation.predictedEgoPathIn.predictedEgoPath;
    flow from targetProcessing.relevantTargetStateOut.forwardTargetState
      to collisionRiskEvaluation.relevantTargetStateIn.forwardTargetState;

    // Risk, decision, warning, intervention, health, and evidence exchanges.
    flow from collisionRiskEvaluation.collisionRiskOut.collisionRiskAssessment
      to interventionDecision.collisionRiskIn.collisionRiskAssessment;
    flow from collisionRiskEvaluation.collisionRiskOut.collisionRiskAssessment
      to warningManagement.collisionRiskIn.collisionRiskAssessment;
    flow from collisionRiskEvaluation.collisionRiskOut.collisionRiskAssessment
      to evidenceRecording.collisionRiskIn.collisionRiskAssessment;

    flow from healthSupervision.degradationStateOut.degradationState
      to interventionDecision.degradationStateIn.degradationState;
    flow from healthSupervision.degradationStateOut.degradationState
      to evidenceRecording.degradationStateIn.degradationState;

    flow from interventionDecision.interventionDecisionOut.interventionDecision
      to emergencyCoordination.interventionDecisionIn.interventionDecision;
    flow from interventionDecision.interventionDecisionOut.interventionDecision
      to evidenceRecording.interventionDecisionIn.interventionDecision;

    bind driverWarningRequestOut = warningManagement.driverWarningRequestOut;
    flow from warningManagement.driverWarningRequestOut.driverWarningRequest
      to evidenceRecording.driverWarningRequestIn.driverWarningRequest;

    bind emergencyInterventionRequestOut = emergencyCoordination.emergencyInterventionOut;
    flow from emergencyCoordination.emergencyInterventionOut.emergencyInterventionRequest
      to evidenceRecording.emergencyInterventionIn.emergencyInterventionRequest;

    bind failureIndicationRequestOut = healthSupervision.failureIndicationOut;
    flow from healthSupervision.failureIndicationOut.failureIndicationRequest
      to evidenceRecording.failureIndicationIn.failureIndicationRequest;

    bind evidenceEventOut = evidenceRecording.evidenceEventOut;
  }

  action functionalFlow : VehicleTargetAEBSFunctionalFlow;
  part system : VehicleTargetAEBSSystem;

  /*
   * Functional-to-conceptual responsibility allocation. One functional action may
   * allocate to multiple conceptual elements when the conceptual decomposition makes
   * previously combined responsibilities explicit.
   */
  allocation def FunctionalToSystemResponsibility;

  allocation acquireStateAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.acquireState
    to system.stateAcquisition;

  allocation assessRiskPathAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.assessRisk
    to system.egoPathPrediction;
  allocation assessRiskTargetAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.assessRisk
    to system.targetProcessing;
  allocation assessRiskEvaluationAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.assessRisk
    to system.collisionRiskEvaluation;

  allocation requestWarningAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.requestWarning
    to system.warningManagement;

  allocation evaluateOverrideAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.evaluateOverride
    to system.interventionDecision;

  allocation requestBrakingDecisionAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.requestBraking
    to system.interventionDecision;
  allocation requestBrakingCoordinationAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.requestBraking
    to system.emergencyCoordination;

  allocation monitorFailureAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.monitorFailure
    to system.healthSupervision;

  allocation recordEvidenceAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow.recordEvidence
    to system.evidenceRecording;

  /* ──────────────────────────────────────────
   * Concerns and human-reviewable views
   * ────────────────────────────────────────── */

  concern conceptualStructureConcern : ConceptualStructureConcern {
    doc /*
     * Reviewers need the conceptual AEBS boundary, decomposition, responsibility
     * ownership, and conceptual/physical separation to be explicit.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern conceptualInternalExchangeConcern : ConceptualInternalExchangeConcern {
    doc /*
     * Reviewers need typed boundary and internal exchanges, direction, and
     * delegation to conceptual owners without middleware leakage.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern conceptualFunctionMappingConcern : ConceptualFunctionMappingConcern {
    doc /*
     * Reviewers need every AEBS functional action allocated to one or more
     * conceptual elements without implying physical realization.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsSystemStructureView {
    viewpoint selectedSystemStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame conceptualStructureConcern;
    }

    expose system;
    expose system::stateAcquisition;
    expose system::egoPathPrediction;
    expose system::targetProcessing;
    expose system::collisionRiskEvaluation;
    expose system::interventionDecision;
    expose system::warningManagement;
    expose system::emergencyCoordination;
    expose system::healthSupervision;
    expose system::evidenceRecording;
    /*
     * This is a decomposition view. The tree renderer may list ports owned by
     * the exposed parts, but it does not render the bind and flow edges below.
     * Port connectivity is defined in VehicleTargetAEBSSystem and
     * selected by aebsSystemInternalExchangeView.
     */
    render asTreeDiagram;
  }

  view aebsSystemInternalExchangeView {
    viewpoint selectedSystemInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame conceptualInternalExchangeConcern;
    }

    /*
     * Exposing direct conceptual-system members selects the boundary ports,
     * bindings, flows, and component usages that define connectivity. The
     * current tree renderer is not relationship-complete: it may list ports
     * without drawing bind or flow edges. Review the textual bind/flow usages
     * as the authoritative exchange topology.
     */
    expose system::*;
    render asTreeDiagram;
  }

  view aebsSystemFunctionMappingView {
    viewpoint selectedSystemFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame conceptualFunctionMappingConcern;
    }

    expose acquireStateAllocation;
    expose assessRiskPathAllocation;
    expose assessRiskTargetAllocation;
    expose assessRiskEvaluationAllocation;
    expose requestWarningAllocation;
    expose evaluateOverrideAllocation;
    expose requestBrakingDecisionAllocation;
    expose requestBrakingCoordinationAllocation;
    expose monitorFailureAllocation;
    expose recordEvidenceAllocation;
    render asTreeDiagram;
  }
}
