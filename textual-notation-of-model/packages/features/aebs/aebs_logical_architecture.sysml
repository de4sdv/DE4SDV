/*
 * DE4SDV AEBS logical architecture model slice.
 *
 * This package mirrors INC-AEBS-006 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-logical-architecture.yaml.
 *
 * Domain boundary: logical architecture only. Autoware, ROS 2/DDS,
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

package DE4SDV_AEBSLogicalArchitecture {
  private import ScalarValues::*;
  private import DE4SDV::Features::AEBS::FunctionalBehavior::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_MethodViewpoints::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;

  part incAEBS006 : FeatureIncrement;
  part sdvProductLine : SDVProductLine;
  part memberProduct : ProductLineMemberProduct;
  part aebsCommonCapability : CommonProductLineCapability;

  /* ──────────────────────────────────────────
   * Logical information definitions
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
     * supplied to the logical decision boundary. Concrete providers and
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
     * establishes the logical producer-consumer boundary without inventing
     * a physical or software schema.
     */
  }

  item def InterventionDecision {
    doc /*
     * Logical emergency-intervention intent after considering collision risk,
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
     * Logical valid/degraded/unavailable result from health supervision.
     * Concrete diagnostic codes and middleware health services are deferred.
     */
    attribute availability : AEBSAvailabilityKind;
  }

  item def ObservationHealthStatus {
    doc /*
     * Logical freshness, consistency, and validity status produced while
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
   * Logical port definitions
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
   * Logical component definitions
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
    doc /* Produces a logical driver-warning request without prescribing HMI technology. */
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
     * Issues and retains a logical emergency-intervention request only from an
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
     * Sole logical owner of valid, degraded, and unavailable AEBS operation;
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
     * events and emits a logical evidence event. Storage technology, retention,
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
   * Logical system composition and exchanges
   * ────────────────────────────────────────── */

  part def VehicleTargetAEBSLogicalSystem {
    doc /*
     * Technology-neutral logical realization of the vehicle-target AEBS
     * functional baseline. Logical elements own responsibilities and exchange
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

    // Boundary delegation binds external ports to their logical owners.
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
  part logicalSystem : VehicleTargetAEBSLogicalSystem;

  /*
   * Functional-to-logical responsibility allocation. One functional action may
   * allocate to multiple logical elements when the logical decomposition makes
   * previously combined responsibilities explicit.
   */
  allocation def FunctionalToLogicalResponsibility;

  allocation acquireStateAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.acquireState
    to logicalSystem.stateAcquisition;

  allocation assessRiskPathAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.assessRisk
    to logicalSystem.egoPathPrediction;
  allocation assessRiskTargetAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.assessRisk
    to logicalSystem.targetProcessing;
  allocation assessRiskEvaluationAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.assessRisk
    to logicalSystem.collisionRiskEvaluation;

  allocation requestWarningAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.requestWarning
    to logicalSystem.warningManagement;

  allocation evaluateOverrideAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.evaluateOverride
    to logicalSystem.interventionDecision;

  allocation requestBrakingDecisionAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.requestBraking
    to logicalSystem.interventionDecision;
  allocation requestBrakingCoordinationAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.requestBraking
    to logicalSystem.emergencyCoordination;

  allocation monitorFailureAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.monitorFailure
    to logicalSystem.healthSupervision;

  allocation recordEvidenceAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow.recordEvidence
    to logicalSystem.evidenceRecording;

  /* ──────────────────────────────────────────
   * Concerns and human-reviewable views
   * ────────────────────────────────────────── */

  concern logicalStructureConcern : LogicalStructureConcern {
    doc /*
     * Reviewers need the logical AEBS boundary, decomposition, responsibility
     * ownership, and logical/physical separation to be explicit.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern logicalInternalExchangeConcern : LogicalInternalExchangeConcern {
    doc /*
     * Reviewers need typed boundary and internal exchanges, direction, and
     * delegation to logical owners without middleware leakage.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern logicalFunctionalMappingConcern : LogicalFunctionalMappingConcern {
    doc /*
     * Reviewers need every AEBS functional action allocated to one or more
     * logical elements without implying physical realization.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsLogicalStructureView {
    viewpoint selectedLogicalStructureViewpoint : LogicalStructureDefinitionViewpoint {
      frame logicalStructureConcern;
    }

    expose logicalSystem;
    expose logicalSystem::stateAcquisition;
    expose logicalSystem::egoPathPrediction;
    expose logicalSystem::targetProcessing;
    expose logicalSystem::collisionRiskEvaluation;
    expose logicalSystem::interventionDecision;
    expose logicalSystem::warningManagement;
    expose logicalSystem::emergencyCoordination;
    expose logicalSystem::healthSupervision;
    expose logicalSystem::evidenceRecording;
    render asTreeDiagram;
  }

  view aebsLogicalInternalExchangeView {
    viewpoint selectedLogicalInternalExchangeViewpoint : LogicalInternalExchangeViewpoint {
      frame logicalInternalExchangeConcern;
    }

    /*
     * Current tree rendering cannot filter direct port, binding, and flow
     * usages without tool-specific queries. Exposing direct logical-system
     * members keeps this view bounded to the exchange-owning context.
     */
    expose logicalSystem::*;
    render asTreeDiagram;
  }

  view aebsLogicalFunctionalMappingView {
    viewpoint selectedLogicalFunctionalMappingViewpoint : LogicalFunctionalMappingViewpoint {
      frame logicalFunctionalMappingConcern;
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
