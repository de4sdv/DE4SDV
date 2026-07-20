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
    available;
  }

  enum def AEBSInterventionKind {
    none;
    interventionRequested;
    inhibited;
  }

  item def AEBSOperatingContext {
    doc /*
     * Technology-neutral lifecycle and operating context supplied to the
     * logical decision boundary. Concrete mode providers and middleware are
     * deferred to physical realization.
     */
    attribute availability : AEBSAvailabilityKind;
  }

  item def PredictedEgoPath {
    doc /*
     * Technology-neutral predicted subject-vehicle path used for target
     * relevance and collision-risk evaluation. No trajectory message,
     * geometry representation, or prediction mechanism is selected here.
     */
  }

  item def InterventionDecision {
    doc /*
     * Logical emergency-intervention intent after considering collision risk,
     * operating context, driver override, degradation, and inhibiting
     * conditions.
     */
    attribute intervention : AEBSInterventionKind;
  }

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
     */
    attribute availability : AEBSAvailabilityKind;
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
    in item emergencyInterventionRequest : EmergencyBrakingCommand;
  }

  port def EmergencyInterventionOutput {
    doc /*
     * Logical intervention request port. Its item type reuses the existing
     * functional EmergencyBrakingCommand for traceability; actuator-command
     * ownership is explicitly outside this logical boundary.
     */
    out item emergencyInterventionRequest : EmergencyBrakingCommand;
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
     * Decides emergency-intervention intent while considering operating context,
     * driver override, degradation, and inhibiting conditions.
     */
    port collisionRiskIn : CollisionRiskInput;
    port driverOverrideIn : DriverOverrideInputPort;
    port operatingContextIn : OperatingContextInput;
    port degradationStateIn : DegradationStateInput;
    port interventionDecisionOut : InterventionDecisionOutput;
  }

  part def DriverWarningManagement {
    doc /* Produces a logical driver-warning request without prescribing HMI technology. */
    port collisionRiskIn : CollisionRiskInput;
    port driverWarningRequestOut : DriverWarningRequestOutput;
  }

  part def EmergencyInterventionCoordination {
    doc /*
     * Issues and retains a logical emergency-intervention request. Physical
     * emergency supervision, command gating, vehicle interfacing, and brake
     * actuation are outside INC-AEBS-006.
     */
    port collisionRiskIn : CollisionRiskInput;
    port interventionDecisionIn : InterventionDecisionInput;
    port emergencyInterventionOut : EmergencyInterventionOutput;
  }

  part def HealthAndDegradationSupervision {
    doc /*
     * Determines valid, degraded, and unavailable operation and requests
     * failure indication from input and subsystem health.
     */
    port failureStatusIn : AEBSFailureStatusInput;
    port observationHealthIn : ObservationHealthInput;
    port degradationStateOut : DegradationStateOutput;
    port failureIndicationOut : FailureIndicationOutput;
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

    exhibit state operatingStates {
      doc /*
       * State ownership is modeled now; numeric transition guards, release
       * authority, and timing criteria remain explicit requirements gaps.
       */
      state unavailable;
      state standby;
      state monitoring;
      state warningRequested;
      state interventionRequested;
      state emergencyActive;
      state degraded;
      state overrideAccepted;
    }

    // Boundary delegation to logical owners.
    flow from vehicleMotionObservationIn.vehicleMotionState
      to stateAcquisition.vehicleMotionIn.vehicleMotionState;
    flow from targetObservationIn.forwardTargetState
      to stateAcquisition.targetObservationIn.forwardTargetState;
    flow from driverOverrideObservationIn.driverOverrideInput
      to interventionDecision.driverOverrideIn.driverOverrideInput;
    flow from operatingContextIn.operatingContext
      to interventionDecision.operatingContextIn.operatingContext;
    flow from subsystemHealthIn.aebsFailureStatus
      to healthSupervision.failureStatusIn.aebsFailureStatus;

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
      to emergencyCoordination.collisionRiskIn.collisionRiskAssessment;
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

    flow from warningManagement.driverWarningRequestOut.driverWarningRequest
      to driverWarningRequestOut.driverWarningRequest;
    flow from warningManagement.driverWarningRequestOut.driverWarningRequest
      to evidenceRecording.driverWarningRequestIn.driverWarningRequest;

    flow from emergencyCoordination.emergencyInterventionOut.emergencyInterventionRequest
      to emergencyInterventionRequestOut.emergencyInterventionRequest;
    flow from emergencyCoordination.emergencyInterventionOut.emergencyInterventionRequest
      to evidenceRecording.emergencyInterventionIn.emergencyInterventionRequest;

    flow from healthSupervision.failureIndicationOut.failureIndicationRequest
      to failureIndicationRequestOut.failureIndicationRequest;
    flow from healthSupervision.failureIndicationOut.failureIndicationRequest
      to evidenceRecording.failureIndicationIn.failureIndicationRequest;

    flow from evidenceRecording.evidenceEventOut.aebsEvidenceEvent
      to evidenceEventOut.aebsEvidenceEvent;
  }

  action functionalFlow : VehicleTargetAEBSFunctionalFlow;
  part logicalSystem : VehicleTargetAEBSLogicalSystem;

  /*
   * Functional-to-logical responsibility allocation. One functional action may
   * allocate to multiple logical elements when the logical decomposition makes
   * previously combined responsibilities explicit.
   */
  allocate functionalFlow.acquireState
    to logicalSystem.stateAcquisition;

  allocate functionalFlow.assessRisk
    to logicalSystem.egoPathPrediction;
  allocate functionalFlow.assessRisk
    to logicalSystem.targetProcessing;
  allocate functionalFlow.assessRisk
    to logicalSystem.collisionRiskEvaluation;

  allocate functionalFlow.requestWarning
    to logicalSystem.warningManagement;

  allocate functionalFlow.evaluateOverride
    to logicalSystem.interventionDecision;

  allocate functionalFlow.requestBraking
    to logicalSystem.interventionDecision;
  allocate functionalFlow.requestBraking
    to logicalSystem.emergencyCoordination;

  allocate functionalFlow.monitorFailure
    to logicalSystem.healthSupervision;

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

    expose DE4SDV_AEBSLogicalArchitecture::*;
    render asTreeDiagram;
  }

  view aebsLogicalInternalExchangeView {
    viewpoint selectedLogicalInternalExchangeViewpoint : LogicalInternalExchangeViewpoint {
      frame logicalInternalExchangeConcern;
    }

    expose DE4SDV_AEBSLogicalArchitecture::*;
    render asTreeDiagram;
  }

  view aebsLogicalFunctionalMappingView {
    viewpoint selectedLogicalFunctionalMappingViewpoint : LogicalFunctionalMappingViewpoint {
      frame logicalFunctionalMappingConcern;
    }

    expose DE4SDV_AEBSLogicalArchitecture::*;
    render asTreeDiagram;
  }
}
