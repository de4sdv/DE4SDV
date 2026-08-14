/*
 * DE4SDV AEBS physical software realization model slice.
 *
 * This package implements INC-AEBS-007: a source-backed mapping from the
 * accepted technology-neutral AEBS system architecture to Autoware software.
 * Runtime deployment, vehicle-platform integration, brake actuation, and
 * executable evidence remain INC-AEBS-008/009 responsibilities.
 *
 * Pinned upstream source:
 * - repository: https://github.com/autowarefoundation/autoware_universe
 * - commit: f603d8759c92fb2f423f1544844e13086d79ad09
 * - package: control/autoware_autonomous_emergency_braking
 * - package version: 0.52.0
 * - license: Apache-2.0
 *
 * The pinned source contains two unresolved blockers recorded in the companion
 * YAML/Markdown control artifacts:
 * - predicted-trajectory path generation calls path.back() before the first
 *   element is inserted; that branch is not accepted as a realization;
 * - the launch file remaps an undeclared input_odometry argument although the
 *   current node has no odometry subscriber.
 *
 * This model makes no requirement satisfaction, compliance, certification,
 * production-readiness, real-vehicle, or brake-actuation claim.
 */

package DE4SDV_AEBSPhysicalSoftwareRealization {
  private import DE4SDV_AEBSConceptualArchitecture::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ROS2Types::*;
  private import Views::*;

  /* ──────────────────────────────────────────
   * Concrete Autoware ROS 2 message definitions
   * ────────────────────────────────────────── */

  item def PointCloud2Message :> ROS2TopicMessage {
    doc /* ROS 2 sensor_msgs/msg/PointCloud2. */
  }

  item def VelocityReportMessage :> ROS2TopicMessage {
    doc /* ROS 2 autoware_vehicle_msgs/msg/VelocityReport. */
  }

  item def ImuMessage :> ROS2TopicMessage {
    doc /* ROS 2 sensor_msgs/msg/Imu. */
  }

  item def TrajectoryMessage :> ROS2TopicMessage {
    doc /* ROS 2 autoware_planning_msgs/msg/Trajectory. */
  }

  item def PredictedObjectsMessage :> ROS2TopicMessage {
    doc /* ROS 2 autoware_perception_msgs/msg/PredictedObjects. */
  }

  item def AutowareStateMessage :> ROS2TopicMessage {
    doc /* ROS 2 autoware_system_msgs/msg/AutowareState. */
  }

  item def DiagnosticArrayMessage :> ROS2TopicMessage {
    doc /*
     * ROS 2 diagnostic_msgs/msg/DiagnosticArray transport used by
     * diagnostic_updater. The AEB task name is aeb_emergency_stop.
     */
  }

  item def MetricArrayMessage :> ROS2TopicMessage {
    doc /* ROS 2 tier4_metric_msgs/msg/MetricArray. */
  }

  item def DebugPointCloudMessage :> ROS2TopicMessage {
    doc /* ROS 2 sensor_msgs/msg/PointCloud2 debug output. */
  }

  item def MarkerArrayMessage :> ROS2TopicMessage {
    doc /* ROS 2 visualization_msgs/msg/MarkerArray. */
  }

  item def Float32StampedMessage :> ROS2TopicMessage {
    doc /* ROS 2 tier4_debug_msgs/msg/Float32Stamped. */
  }

  item def ProcessingTimeDetailMessage :> ROS2TopicMessage {
    doc /* ROS 2 autoware_utils/ProcessingTimeDetail debug output. */
  }

  /*
   * Reusable ROS 2 topic protocol roles. Concrete message-specific port
   * definitions specialize these roles. The interface captures publish/
   * subscribe compatibility without selecting an RMW/DDS implementation.
   */
  interface def ROS2PublishSubscribeTopicInterface {
    doc /*
     * Application-level ROS 2 topic protocol. The publisher and subscriber
     * roles are compatible through a common topic and a matching concrete
     * message type; QoS and RMW/DDS selection are deferred.
     */
    end publisher : ROS2TopicPublication;
    end subscriber : ROS2TopicSubscription;
    flow of ROS2TopicMessage from publisher.payload to subscriber.payload;
  }

  port def PointCloud2Subscription :> ROS2TopicSubscription {
    in item pointCloud : PointCloud2Message redefines payload;
  }

  port def VelocityReportSubscription :> ROS2TopicSubscription {
    in item velocityReport : VelocityReportMessage redefines payload;
  }

  port def ImuSubscription :> ROS2TopicSubscription {
    in item imu : ImuMessage redefines payload;
  }

  port def TrajectorySubscription :> ROS2TopicSubscription {
    in item trajectory : TrajectoryMessage redefines payload;
  }

  port def PredictedObjectsSubscription :> ROS2TopicSubscription {
    in item predictedObjects : PredictedObjectsMessage redefines payload;
  }

  port def AutowareStateSubscription :> ROS2TopicSubscription {
    in item autowareState : AutowareStateMessage redefines payload;
  }

  port def DiagnosticPublication :> ROS2TopicPublication {
    out item diagnostics : DiagnosticArrayMessage redefines payload;
  }

  port def MetricPublication :> ROS2TopicPublication {
    out item metrics : MetricArrayMessage redefines payload;
  }

  port def DebugPointCloudPublication :> ROS2TopicPublication {
    out item debugPointCloud : DebugPointCloudMessage redefines payload;
  }

  port def MarkerPublication :> ROS2TopicPublication {
    out item markers : MarkerArrayMessage redefines payload;
  }

  port def DebugDistancePublication :> ROS2TopicPublication {
    out item rssDistance : Float32StampedMessage redefines payload;
  }

  port def ProcessingTimePublication :> ROS2TopicPublication {
    out item processingTime : ProcessingTimeDetailMessage redefines payload;
  }

  /* ──────────────────────────────────────────
   * Source-backed physical software elements
   * ────────────────────────────────────────── */

  part def AutowareAEBSourceArtifact {
    doc /*
     * Build/source artifact at
     * control/autoware_autonomous_emergency_braking, version 0.52.0, pinned to
     * Autoware Universe commit f603d8759c92fb2f423f1544844e13086d79ad09.
     */
  }

  part def AutowareAutonomousEmergencyBrakingNode {
    doc /*
     * Concrete rclcpp node class AEB from include/autoware/
     * autonomous_emergency_braking/node.hpp and src/node.cpp.
     *
     * Source-backed behavior includes input polling/transformation, IMU and
     * control-trajectory path branches, target extraction from point clouds or
     * predicted objects, RSS-distance collision checking, and an ERROR-level
     * diagnostic when collision state is active. Branch acceptance and conceptual
     * coverage are represented separately below.
     */

    port pointCloudIn : PointCloud2Subscription {
      doc /* ~/input/pointcloud; default /perception/obstacle_segmentation/pointcloud. */
    }
    port velocityIn : VelocityReportSubscription {
      doc /* ~/input/velocity; default /vehicle/status/velocity_status. */
    }
    port imuIn : ImuSubscription {
      doc /* ~/input/imu; default /sensing/imu/imu_data. */
    }
    port predictedTrajectoryIn : TrajectorySubscription {
      doc /*
       * ~/input/predicted_trajectory; default /control/trajectory_follower/
       * lateral/predicted_trajectory. Blocked at the pinned source revision.
       */
    }
    port predictedObjectsIn : PredictedObjectsSubscription {
      doc /* ~/input/objects; default /perception/object_recognition/objects. */
    }
    port autowareStateIn : AutowareStateSubscription {
      doc /* Absolute topic /autoware/state. */
    }

    port diagnosticsOut : DiagnosticPublication {
      doc /* /diagnostics via diagnostic_updater task aeb_emergency_stop. */
    }
    port metricsOut : MetricPublication {
      doc /* ~/metrics. */
    }
    port debugPointCloudOut : DebugPointCloudPublication {
      doc /* ~/debug/obstacle_pointcloud. */
    }
    port debugMarkersOut : MarkerPublication {
      doc /* ~/debug/markers. */
    }
    port virtualWallOut : MarkerPublication {
      doc /* ~/virtual_wall. */
    }
    port rssDistanceOut : DebugDistancePublication {
      doc /* ~/debug/rss_distance. */
    }
    port processingTimeOut : ProcessingTimePublication {
      doc /* ~/debug/processing_time_detail_ms. */
    }
  }

  part def RequiredROS2ApplicationRuntimeBoundary {
    doc /*
     * Required rclcpp, executor, RMW/DDS, TF, diagnostic_updater, message, and
     * process-lifecycle environment. Concrete runtime and deployment choices
     * are intentionally deferred to INC-AEBS-008.
     */
  }

  part def RequiredDriverWarningProviderBoundary {
    doc /*
     * Required physical HMI/warning realization. The pinned Autoware AEB node
     * does not realize DriverWarningManagement. The proposed realization is a
     * separate HMI warning adapter that consumes a typed AEBS warning request
     * produced before emergency intervention and presents the selected visual,
     * audible, or haptic warning. Do not derive this warning from the AEB ERROR
     * diagnostic: that diagnostic reports emergency-stop activation and is too
     * late and too coarse to represent the warning contract. A typed warning
     * output or upstream AEB extension remains required.
     */
  }

  part def RequiredDiagnosticFailureBridgeBoundary {
    doc /*
     * Required bridge from the AEB ERROR diagnostic to the failure-state or
     * operation-mode input expected by an emergency Minimum Risk Manoeuvre
     * (MRM) handler. The pinned
     * diagnostic graph aggregator is a candidate mechanism, but no active
     * repository configuration routing aeb_emergency_stop into MRM selection
     * was verified for INC-AEBS-007.
     */
  }

  part def RequiredEmergencyMRMHandlerBoundary {
    doc /*
     * Required emergency Minimum Risk Manoeuvre (MRM) state owner. Autoware's
     * pinned mrm_handler consumes
     * OperationModeAvailability and MRM status inputs, not the AEB diagnostic
     * directly. No concrete provider or accepted route is selected here.
     */
  }

  part def RequiredVehicleCommandGateBoundary {
    doc /*
     * Required downstream arbitration and safety gate. The pinned AEB node does
     * not publish a vehicle actuation command.
     */
  }

  part def RequiredVehicleInterfaceBoundary {
    doc /* Required adapter from gated vehicle command to the selected vehicle platform. */
  }

  part def RequiredBrakeECUAndActuatorBoundary {
    doc /* Required brake-controller and physical actuator boundary; deferred to INC-AEBS-008. */
  }

  part def RequiredHealthSupervisorBoundary {
    doc /*
     * Required owner of explicit AEBS valid/degraded/unavailable state and
     * failure indication. Input waiting/logging in the pinned node is not a
     * complete realization of that conceptual responsibility.
     */
  }

  part def RequiredEvidenceServiceBoundary {
    doc /*
     * Required recorder/collector for accepted AEBS evidence. Diagnostics,
     * metrics, markers, and timing debug outputs are observable source data but
     * do not by themselves implement evidence retention or acceptance.
     */
  }

  part def VehicleTargetAEBSPhysicalSoftwareBoundary {
    doc /*
     * INC-AEBS-007 physical software boundary. Only the Autoware source artifact
     * and AEB node are selected realizations. Runtime, HMI, emergency handling,
     * vehicle control, actuation, health, and evidence services remain external
     * required boundaries for later increments.
     */

    part sourceArtifact : AutowareAEBSourceArtifact;
    part aebNode : AutowareAutonomousEmergencyBrakingNode;

    // These are the public ports of the selected physical-software boundary.
    // The bindings below delegate each public port to the matching endpoint on
    // the contained AEB node. A bind is equality/delegation, not another ROS
    // topic flow: it lets external connections use this boundary without
    // bypassing the internal node. Ports are declared first so both bound usages
    // exist before the delegation relationships are stated.
    port pointCloudIn : PointCloud2Subscription;
    port velocityIn : VelocityReportSubscription;
    port imuIn : ImuSubscription;
    port predictedTrajectoryIn : TrajectorySubscription;
    port predictedObjectsIn : PredictedObjectsSubscription;
    port autowareStateIn : AutowareStateSubscription;
    port diagnosticsOut : DiagnosticPublication;
    port metricsOut : MetricPublication;
    port debugPointCloudOut : DebugPointCloudPublication;
    port debugMarkersOut : MarkerPublication;
    port virtualWallOut : MarkerPublication;
    port rssDistanceOut : DebugDistancePublication;
    port processingTimeOut : ProcessingTimePublication;

    bind pointCloudIn = aebNode.pointCloudIn;
    bind velocityIn = aebNode.velocityIn;
    bind imuIn = aebNode.imuIn;
    bind predictedTrajectoryIn = aebNode.predictedTrajectoryIn;
    bind predictedObjectsIn = aebNode.predictedObjectsIn;
    bind autowareStateIn = aebNode.autowareStateIn;
    bind diagnosticsOut = aebNode.diagnosticsOut;
    bind metricsOut = aebNode.metricsOut;
    bind debugPointCloudOut = aebNode.debugPointCloudOut;
    bind debugMarkersOut = aebNode.debugMarkersOut;
    bind virtualWallOut = aebNode.virtualWallOut;
    bind rssDistanceOut = aebNode.rssDistanceOut;
    bind processingTimeOut = aebNode.processingTimeOut;
  }

  part physicalSoftware : VehicleTargetAEBSPhysicalSoftwareBoundary;
  part requiredRuntime : RequiredROS2ApplicationRuntimeBoundary;
  part requiredWarningProvider : RequiredDriverWarningProviderBoundary;
  part requiredDiagnosticBridge : RequiredDiagnosticFailureBridgeBoundary;
  part requiredEmergencyHandler : RequiredEmergencyMRMHandlerBoundary;
  part requiredCommandGate : RequiredVehicleCommandGateBoundary;
  part requiredVehicleInterface : RequiredVehicleInterfaceBoundary;
  part requiredBrakeActuation : RequiredBrakeECUAndActuatorBoundary;
  part requiredHealthSupervisor : RequiredHealthSupervisorBoundary;
  part requiredEvidenceService : RequiredEvidenceServiceBoundary;

  /* ──────────────────────────────────────────
   * Logical-to-physical realization coverage
   * ──────────────────────────────────────────
   *
   * Native SysML allocation follows the logical-responsibility-to-physical-
   * realization pattern used by the authoritative Allocation validation
   * example. SAF P8_PLOM asks which physical role implements each logical role;
   * it does not require reversing native allocation semantics.
   */

  allocation def AvailableLogicalToPhysicalSoftwareRealization {
    doc /*
     * At the pinned source and selected configuration, inspected source behavior
     * exists for the mapped conceptual responsibility. Typing an allocation with
     * this definition lets the SAF physical-logical mapping view distinguish a
     * source-available candidate from a partial or missing realization. It does
     * not imply complete requirement satisfaction, scenario evidence, runtime
     * execution, or acceptance.
     */
  }

  allocation def PartialLogicalToPhysicalSoftwareRealization {
    doc /*
     * Inspected source behavior covers only part of the mapped logical
     * responsibility. The allocation is retained because the physical element
     * genuinely contributes, while the companion control artifacts identify the
     * uncovered obligations. This prevents both false full-coverage claims and
     * loss of useful traceability.
     */
  }

  allocation stateAcquisitionPartial : PartialLogicalToPhysicalSoftwareRealization
    allocate DE4SDV_AEBSConceptualArchitecture::system::stateAcquisition
    to physicalSoftware.aebNode;

  allocation egoPathPredictionPartial : PartialLogicalToPhysicalSoftwareRealization
    allocate DE4SDV_AEBSConceptualArchitecture::system::egoPathPrediction
    to physicalSoftware.aebNode;

  allocation targetProcessingAvailable : AvailableLogicalToPhysicalSoftwareRealization
    allocate DE4SDV_AEBSConceptualArchitecture::system::targetProcessing
    to physicalSoftware.aebNode;

  allocation collisionRiskEvaluationAvailable : AvailableLogicalToPhysicalSoftwareRealization
    allocate DE4SDV_AEBSConceptualArchitecture::system::collisionRiskEvaluation
    to physicalSoftware.aebNode;

  allocation interventionDecisionPartial : PartialLogicalToPhysicalSoftwareRealization
    allocate DE4SDV_AEBSConceptualArchitecture::system::interventionDecision
    to physicalSoftware.aebNode;

  allocation healthSupervisionPartial : PartialLogicalToPhysicalSoftwareRealization
    allocate DE4SDV_AEBSConceptualArchitecture::system::healthSupervision
    to physicalSoftware.aebNode;

  allocation evidenceRecordingPartial : PartialLogicalToPhysicalSoftwareRealization
    allocate DE4SDV_AEBSConceptualArchitecture::system::evidenceRecording
    to physicalSoftware.aebNode;

  /*
   * Coverage records are first-class typed model elements. They distinguish an
   * absent realization, a blocked source branch, and an observable source
   * contribution from a true logical-to-physical allocation.
   */
  part def MissingPhysicalRealizationRecord :> MissingRealizationRecord;
  part def BlockedPhysicalRealizationBranchRecord :> BlockedRealizationBranchRecord;
  part def PhysicalSourceContributionRecord :> SourceContributionRecord;

  part driverWarningRealizationGap : MissingPhysicalRealizationRecord {
    doc /* DriverWarningManagement has no selected physical owner in INC-AEBS-007. */
    ref part systemRole = DE4SDV_AEBSConceptualArchitecture::system::warningManagement;
    ref part requiredPhysicalRole = requiredWarningProvider;
  }

  part predictedTrajectoryBranchBlocked : BlockedPhysicalRealizationBranchRecord {
    doc /*
     * The predicted-trajectory input/path branch is blocked by DEF-AEBS-PHY-001.
     * The IMU branch remains the source-available contribution to the partial
     * EgoPathPrediction allocation. Resolve this by either moving to a reviewed
     * upstream revision where the empty-path access is fixed, or by proposing an
     * upstream patch that initializes the path before path.back() and adds a
     * regression test. Until that fix is reviewed, the simulation configuration
     * keeps use_predicted_trajectory false; disabling the branch is containment,
     * not resolution.
     */
    ref part systemRole = DE4SDV_AEBSConceptualArchitecture::system::egoPathPrediction;
    ref part physicalCandidate = physicalSoftware.aebNode;
    ref part pinnedSource = physicalSoftware.sourceArtifact;
  }

  part emergencyDiagnosticContribution : PhysicalSourceContributionRecord {
    doc /*
     * The AEB node contributes an ERROR diagnostic only. It does not realize
     * the conceptual EmergencyInterventionCoordination contract or emit the
     * conceptual EmergencyInterventionRequest.
     */
    ref part conceptualConcern = DE4SDV_AEBSConceptualArchitecture::system::emergencyCoordination;
    ref part physicalSource = physicalSoftware.aebNode;
    ref part requiredPhysicalRole = requiredDiagnosticBridge;
  }

  part healthCoverageGap : MissingPhysicalRealizationRecord {
    doc /* Complete valid/degraded/unavailable state ownership remains missing. */
    ref part systemRole = DE4SDV_AEBSConceptualArchitecture::system::healthSupervision;
    ref part requiredPhysicalRole = requiredHealthSupervisor;
  }

  part evidenceCoverageGap : MissingPhysicalRealizationRecord {
    doc /* Evidence persistence, provenance, retention, and acceptance remain missing. */
    ref part systemRole = DE4SDV_AEBSConceptualArchitecture::system::evidenceRecording;
    ref part requiredPhysicalRole = requiredEvidenceService;
  }

  dependency aebNodeTracesToPinnedSource from physicalSoftware::aebNode to physicalSoftware::sourceArtifact;

  /*
   * Required emergency chain. These dependencies expose missing downstream
   * owners without inventing message schemas, deployments, or actuation claims.
   */
  dependency aebDiagnosticNeedsFailureBridge from physicalSoftware::aebNode to requiredDiagnosticBridge;
  dependency failureBridgeNeedsEmergencyHandler from requiredDiagnosticBridge to requiredEmergencyHandler;
  dependency emergencyHandlerNeedsCommandGate from requiredEmergencyHandler to requiredCommandGate;
  dependency commandGateNeedsVehicleInterface from requiredCommandGate to requiredVehicleInterface;
  /*
   * This final dependency records the still-missing handoff from the generic
   * vehicle-platform adapter to the brake ECU and actuator. It is an integration
   * obligation for a later member-product realization, not a modeled command
   * flow and not evidence that physical braking exists in this increment.
   */
  dependency vehicleInterfaceNeedsBrakeActuation from requiredVehicleInterface to requiredBrakeActuation;

  dependency nodeNeedsRuntime from physicalSoftware::aebNode to requiredRuntime;

  /* ──────────────────────────────────────────
   * SAF physical-domain concerns and views
   * ────────────────────────────────────────── */

  concern physicalStructureConcern : PhysicalStructureConcern {
    doc /*
     * Reviewers need the selected Autoware software elements and every required
     * external physical boundary to be visible without implying deployment.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern physicalInterfaceConcern : PhysicalInterfaceConcern {
    doc /*
     * Reviewers need the reusable ROS 2 message and port definitions plus the
     * exact typed topic usages on the pinned Autoware AEB node. Concrete
     * RMW/DDS protocol selection remains an explicit runtime obligation.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern physicalLogicalMappingConcern : PhysicalLogicalMappingConcern {
    doc /*
     * Reviewers need available and partial mappings separated from blocked and
     * missing responsibilities; no mapping may imply requirement satisfaction.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsPhysicalSoftwareStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame physicalStructureConcern;
    }

    expose physicalSoftware;
    expose physicalSoftware::sourceArtifact;
    expose physicalSoftware::aebNode;
    expose requiredRuntime;
    expose requiredWarningProvider;
    expose requiredDiagnosticBridge;
    expose requiredEmergencyHandler;
    expose requiredCommandGate;
    expose requiredVehicleInterface;
    expose requiredBrakeActuation;
    expose requiredHealthSupervisor;
    expose requiredEvidenceService;
    render asTreeDiagram;
  }

  view aebsPhysicalSoftwareInterfaceView {
    viewpoint selectedPhysicalInterfaceViewpoint : PhysicalInterfaceDefinitionViewpoint {
      frame physicalInterfaceConcern;
    }

    /*
     * P5_PIFD is a definition view, so expose the reusable port and exchanged
     * item definitions as well as the node's typed port usages. ROS 2 topic
     * transport is the inspected application-level protocol; the concrete
     * RMW/DDS protocol and deployment remain requiredRuntime obligations.
     */
    expose PointCloud2Message;
    expose VelocityReportMessage;
    expose ImuMessage;
    expose TrajectoryMessage;
    expose PredictedObjectsMessage;
    expose AutowareStateMessage;
    expose DiagnosticArrayMessage;
    expose MetricArrayMessage;
    expose DebugPointCloudMessage;
    expose MarkerArrayMessage;
    expose Float32StampedMessage;
    expose ProcessingTimeDetailMessage;
    expose ROS2TopicEndpoint;
    expose ROS2TopicSubscription;
    expose ROS2TopicPublication;
    expose ROS2PublishSubscribeTopicInterface;
    expose PointCloud2Subscription;
    expose VelocityReportSubscription;
    expose ImuSubscription;
    expose TrajectorySubscription;
    expose PredictedObjectsSubscription;
    expose AutowareStateSubscription;
    expose DiagnosticPublication;
    expose MetricPublication;
    expose DebugPointCloudPublication;
    expose MarkerPublication;
    expose DebugDistancePublication;
    expose ProcessingTimePublication;
    expose physicalSoftware::*;
    expose physicalSoftware::aebNode::*;
    expose requiredRuntime;
    render asTreeDiagram;
  }

  view aebsPhysicalLogicalMappingView {
    viewpoint selectedPhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame physicalLogicalMappingConcern;
    }

    /*
     * P8_PLOM requires both endpoint breakdowns and logical-to-physical
     * realization relationships. The allocations below are the authoritative
     * mapping; the tree renderer may list them without drawing allocation edges.
     */
    expose physicalSoftware;
    expose physicalSoftware::aebNode;
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
    expose stateAcquisitionPartial;
    expose egoPathPredictionPartial;
    expose targetProcessingAvailable;
    expose collisionRiskEvaluationAvailable;
    expose interventionDecisionPartial;
    expose healthSupervisionPartial;
    expose evidenceRecordingPartial;
    expose driverWarningRealizationGap;
    expose predictedTrajectoryBranchBlocked;
    expose emergencyDiagnosticContribution;
    expose healthCoverageGap;
    expose evidenceCoverageGap;
    expose aebNodeTracesToPinnedSource;
    expose aebDiagnosticNeedsFailureBridge;
    expose failureBridgeNeedsEmergencyHandler;
    expose emergencyHandlerNeedsCommandGate;
    expose commandGateNeedsVehicleInterface;
    expose vehicleInterfaceNeedsBrakeActuation;
    expose nodeNeedsRuntime;
    render asTreeDiagram;
  }
}
