/*
 * INC-AEBS-008 simulation-only deployment of the INC-AEBS-007 Autoware
 * physical software realization. Textual bindings and flows are authoritative.
 *
 * Pinned sources:
 * - Autoware Universe f603d8759c92fb2f423f1544844e13086d79ad09
 * - Autoware Launch   f05c4b1f83e0b0e4a01ade34d5199bd5571873f1
 *
 * This is a review model, not execution evidence. It makes no requirement
 * satisfaction, compliance, certification, production, real-vehicle, brake ECU,
 * actuator, or accepted-performance claim. S-CORE, a real vehicle interface,
 * autoware_raw_vehicle_cmd_converter, and HardwareLayer realization are absent.
 */
package DE4SDV_AEBSSimulationDeployment {
  private import DE4SDV_AEBSLogicalArchitecture::*;
  private import DE4SDV_AEBSFunctionalBehavior::Features::AEBS::FunctionalBehavior::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;

  /* Physical exchange types. Adjacent stages are deliberately distinct. */
  item def AEBEmergencyStopDiagnosticStatus {
    doc /* Exact identity /control/autonomous_emergency_braking: aeb_emergency_stop. */
  }
  item def AEBEmergencyStopDiagnosticArrayMessage :> DiagnosticArrayMessage {
    doc /*
     * diagnostic_msgs/msg/DiagnosticArray on /diagnostics containing the exact
     * DiagnosticStatus identity
     * /control/autonomous_emergency_braking: aeb_emergency_stop.
     * This is neither EmergencyInterventionRequest nor a brake command.
     */
    item aebEmergencyStopStatus : AEBEmergencyStopDiagnosticStatus;
  }
  item def CommandModeAvailabilityMessage :> ROS2TopicMessage {
    doc /* Aggregator output; autonomous is unavailable while emergency stop remains available. */
  }
  item def OperationModeAvailabilityMessage :> ROS2TopicMessage {
    doc /* Converter output. emergency_stop denotes fallback availability, not the AEB trigger or current mode. */
  }
  item def OperationModeStateMessage :> ROS2TopicMessage {
    doc /* Shared schema used at distinct /api/operation_mode/state and /system/operation_mode/state endpoints. */
  }
  item def ControlModeReportMessage :> ROS2TopicMessage {
    doc /* /vehicle/status/control_mode; the simulator must report AUTONOMOUS. */
  }
  item def GearCommandMessage :> ROS2TopicMessage {
    doc /* autoware_vehicle_msgs/msg/GearCommand on the command-gate/MRM feedback topology. */
  }
  item def OperateMrmRequestMessage {
    doc /* tier4_system_msgs/srv/OperateMrm request selecting emergency stop. */
  }
  item def MrmStateMessage :> ROS2TopicMessage {
    doc /* MRM handler state on /system/fail_safe/mrm_state; consumed by the legacy gate. */
  }
  item def EmergencyStopOperatorStatusMessage :> ROS2TopicMessage {
    doc /* /system/mrm/emergency_stop/status availability/operating state returned to the MRM handler. */
  }
  item def ControlCommandMessage :> ROS2TopicMessage {
    doc /* autoware_control_msgs/msg/Control; a physical control message, not DiagnosticArray. */
  }
  item def ScenarioControlMessage :> ROS2TopicMessage;
  item def VectorMapInitializationMessage :> ROS2TopicMessage;
  item def InitialPoseMessage :> ROS2TopicMessage;
  item def PlannedTrajectoryMessage :> ROS2TopicMessage;
  item def EngageInitializationMessage :> ROS2TopicMessage;
  item def TfAndVehicleInfoConfiguration {
    doc /* Selected AEB TF transforms and vehicle-info parameters; not simulator odometry. */
  }
  item def OdometryFeedbackMessage :> ROS2TopicMessage;
  item def VelocityReportFeedbackMessage :> VelocityReportMessage;
  item def AccelerationFeedbackMessage :> ROS2TopicMessage;
  item def SteeringReportFeedbackMessage :> ROS2TopicMessage;
  item def ImuFeedbackMessage :> ImuMessage;
  item def VehicleStatusFeedbackMessage :> ROS2TopicMessage;
  item def SimulationEvidenceObservation {
    doc /* Unaccepted observation collected for INC-AEBS-009; not verification evidence here. */
  }

  /* Concrete topic roles specialize the imported ROS 2 protocol definitions. */
  port def DiagnosticIn :> ROS2TopicSubscription { in item diagnostics : AEBEmergencyStopDiagnosticArrayMessage redefines payload; }
  port def DiagnosticOut :> ROS2TopicPublication { out item diagnostics : AEBEmergencyStopDiagnosticArrayMessage redefines payload; }
  port def PointCloudInput :> ROS2TopicSubscription { in item pointCloud : PointCloud2Message redefines payload; }
  port def PointCloudOutput :> ROS2TopicPublication { out item pointCloud : PointCloud2Message redefines payload; }
  port def AutowareStateInput :> ROS2TopicSubscription { in item autowareState : AutowareStateMessage redefines payload; }
  port def AutowareStateOutput :> ROS2TopicPublication { out item autowareState : AutowareStateMessage redefines payload; }
  port def CommandAvailabilityIn :> ROS2TopicSubscription { in item availability : CommandModeAvailabilityMessage redefines payload; }
  port def CommandAvailabilityOut :> ROS2TopicPublication { out item availability : CommandModeAvailabilityMessage redefines payload; }
  port def OperationAvailabilityIn :> ROS2TopicSubscription { in item availability : OperationModeAvailabilityMessage redefines payload; }
  port def OperationAvailabilityOut :> ROS2TopicPublication { out item availability : OperationModeAvailabilityMessage redefines payload; }
  port def OperationModeStateIn :> ROS2TopicSubscription { in item state : OperationModeStateMessage redefines payload; }
  port def OperationModeStateOut :> ROS2TopicPublication { out item state : OperationModeStateMessage redefines payload; }
  port def ControlModeReportIn :> ROS2TopicSubscription { in item mode : ControlModeReportMessage redefines payload; }
  port def ControlModeReportOut :> ROS2TopicPublication { out item mode : ControlModeReportMessage redefines payload; }
  port def GearCommandIn :> ROS2TopicSubscription { in item gear : GearCommandMessage redefines payload; }
  port def GearCommandOut :> ROS2TopicPublication { out item gear : GearCommandMessage redefines payload; }
  /* OperateMrm is a service request, not a topic payload. */
  port def OperateMrmIn { in item request : OperateMrmRequestMessage; }
  port def OperateMrmOut { out item request : OperateMrmRequestMessage; }
  port def MrmStateIn :> ROS2TopicSubscription { in item state : MrmStateMessage redefines payload; }
  port def MrmStateOut :> ROS2TopicPublication { out item state : MrmStateMessage redefines payload; }
  port def EmergencyStopOperatorStatusIn :> ROS2TopicSubscription { in item status : EmergencyStopOperatorStatusMessage redefines payload; }
  port def EmergencyStopOperatorStatusOut :> ROS2TopicPublication { out item status : EmergencyStopOperatorStatusMessage redefines payload; }
  port def ControlCommandIn :> ROS2TopicSubscription { in item command : ControlCommandMessage redefines payload; }
  port def ControlCommandOut :> ROS2TopicPublication { out item command : ControlCommandMessage redefines payload; }
  port def ScenarioControlIn :> ROS2TopicSubscription { in item scenario : ScenarioControlMessage redefines payload; }
  port def ScenarioControlOut :> ROS2TopicPublication { out item scenario : ScenarioControlMessage redefines payload; }
  port def VectorMapInitializationIn :> ROS2TopicSubscription { in item map : VectorMapInitializationMessage redefines payload; }
  port def VectorMapInitializationOut :> ROS2TopicPublication { out item map : VectorMapInitializationMessage redefines payload; }
  port def InitialPoseIn :> ROS2TopicSubscription { in item pose : InitialPoseMessage redefines payload; }
  port def InitialPoseOut :> ROS2TopicPublication { out item pose : InitialPoseMessage redefines payload; }
  port def PlannedTrajectoryIn :> ROS2TopicSubscription { in item trajectory : PlannedTrajectoryMessage redefines payload; }
  port def PlannedTrajectoryOut :> ROS2TopicPublication { out item trajectory : PlannedTrajectoryMessage redefines payload; }
  port def EngageInitializationIn :> ROS2TopicSubscription { in item engage : EngageInitializationMessage redefines payload; }
  port def EngageInitializationOut :> ROS2TopicPublication { out item engage : EngageInitializationMessage redefines payload; }
  port def TfAndVehicleInfoIn { in item configuration : TfAndVehicleInfoConfiguration; }
  port def TfAndVehicleInfoOut { out item configuration : TfAndVehicleInfoConfiguration; }
  port def OdometryFeedbackIn :> ROS2TopicSubscription { in item odometry : OdometryFeedbackMessage redefines payload; }
  port def OdometryFeedbackOut :> ROS2TopicPublication { out item odometry : OdometryFeedbackMessage redefines payload; }
  port def VelocityFeedbackIn :> ROS2TopicSubscription { in item velocity : VelocityReportFeedbackMessage redefines payload; }
  port def VelocityFeedbackOut :> ROS2TopicPublication { out item velocity : VelocityReportFeedbackMessage redefines payload; }
  port def AccelerationFeedbackIn :> ROS2TopicSubscription { in item acceleration : AccelerationFeedbackMessage redefines payload; }
  port def AccelerationFeedbackOut :> ROS2TopicPublication { out item acceleration : AccelerationFeedbackMessage redefines payload; }
  port def SteeringFeedbackIn :> ROS2TopicSubscription { in item steering : SteeringReportFeedbackMessage redefines payload; }
  port def SteeringFeedbackOut :> ROS2TopicPublication { out item steering : SteeringReportFeedbackMessage redefines payload; }
  port def ImuFeedbackIn :> ROS2TopicSubscription { in item imu : ImuFeedbackMessage redefines payload; }
  port def ImuFeedbackOut :> ROS2TopicPublication { out item imu : ImuFeedbackMessage redefines payload; }
  port def VehicleStatusFeedbackIn :> ROS2TopicSubscription { in item status : VehicleStatusFeedbackMessage redefines payload; }
  port def VehicleStatusFeedbackOut :> ROS2TopicPublication { out item status : VehicleStatusFeedbackMessage redefines payload; }
  port def EvidenceObservationOut { out item observation : SimulationEvidenceObservation; }

  /* Source and configuration records are model artifacts, not executed proof. */
  part def PinnedAutowareUniverseSource {
    doc /* Autoware Universe commit f603d8759c92fb2f423f1544844e13086d79ad09. */
  }
  part def PinnedAutowareLaunchSource {
    doc /* Autoware Launch commit f05c4b1f83e0b0e4a01ade34d5199bd5571873f1. */
  }
  part def AEBParameterSelection {
    doc /*
     * use_predicted_trajectory: false (DEF-AEBS-PHY-001 blocked branch);
     * use_imu_path: true; use_pointcloud_data: true;
     * use_predicted_object_data: false; check_autoware_state: true.
     * DEF-AEBS-PHY-002 remains visible: the pinned launch odometry remap does
     * not correspond to an AEB-node subscriber.
     */
  }
  part def DiagnosticGraphSelection {
    doc /*
     * Custom graph key is exactly
     * /control/autonomous_emergency_braking: aeb_emergency_stop. The autonomous
     * unit includes this status; an active AEB status makes autonomous mode
     * unavailable. Emergency-stop availability remains independently available.
     * Timeout semantics mark the autonomous unit unavailable when the exact
     * diagnostic ceases to arrive for the configured interval. For this
     * diagnostic, only timeout and hysteresis are modeled; hysteresis controls
     * level recovery. No per-diagnostic latch behavior is claimed:
     * initial_latch_suppression is aggregator-wide startup behavior, not a latch
     * for this AEB diagnostic. Concrete timing remains review configuration;
     * no confirmation from /diagnostics is claimed in this model.
     */
  }
  part def LegacyVehicleCommandGateSelection {
    doc /*
     * Selected pinned member: autoware_vehicle_cmd_gate, backed by
     * control/autoware_vehicle_cmd_gate/launch/vehicle_cmd_gate.launch.xml and
     * control/autoware_vehicle_cmd_gate/src/vehicle_cmd_gate.cpp at the pinned
     * Universe commit. It consumes both /system/fail_safe/mrm_state and
     * /system/emergency/control_cmd. With MRM emergency handling active, the MRM
     * state selects the emergency command; the control output remains
     * /control/command/control_cmd. The pinned vehicle_cmd_gate parameter file
     * retains use_emergency_handling: true, which is required for substitution.
     */
  }
  part def DeferredControlCommandGateAlternative {
    doc /*
     * autoware_control_command_gate is deferred. Enabling source 21 only makes
     * emergency_stop available; it does not select that source, and this planned
     * deployment has no source-selection owner. It is therefore not the selected
     * gate and carries no command-routing claim.
     */
  }
  part def LinuxSimulationHost {
    doc /* Linux simulation host with no hypervisor; not an ECU or production target. */
  }
  part def ROS2ApplicationRuntime {
    doc /* rclcpp, executor, RMW/DDS, TF, diagnostics, and message runtime internal to Autoware. */
  }

  /* System 1 candidate deployment roles. */
  part def DeployedAEBNode {
    doc /* Selected inputs are point cloud, velocity, IMU, /autoware/state, and TF/vehicle info; no AEB odometry input exists. */
    port pointCloudIn : PointCloudInput;
    port autowareStateIn : AutowareStateInput;
    port velocityIn : VelocityFeedbackIn;
    port imuIn : ImuFeedbackIn;
    port tfAndVehicleInfoIn : TfAndVehicleInfoIn;
    port diagnosticsOut : DiagnosticOut;
  }
  part def DiagnosticGraphAggregatorNode {
    port diagnosticsIn : DiagnosticIn;
    port commandAvailabilityOut : CommandAvailabilityOut;
  }
  part def CommandModeToOperationModeAvailabilityConverterNode {
    doc /* Converts availability schemas only; it does not provide current operation mode. */
    port commandAvailabilityIn : CommandAvailabilityIn;
    port operationAvailabilityOut : OperationAvailabilityOut;
  }
  part def MrmHandlerNode {
    port operationAvailabilityIn : OperationAvailabilityIn {
      doc /* /system/operation_mode/availability. */
    }
    port operationModeStateIn : OperationModeStateIn {
      doc /* /api/operation_mode/state must be AUTONOMOUS for this planned scenario. */
    }
    port controlModeIn : ControlModeReportIn {
      doc /* /vehicle/status/control_mode must be AUTONOMOUS for MRM transition. */
    }
    port kinematicStateIn : OdometryFeedbackIn {
      doc /* /localization/kinematic_state supports stopped-state evaluation. */
    }
    port gearIn : GearCommandIn {
      doc /* /control/command/gear_cmd. */
    }
    port emergencyStopStatusIn : EmergencyStopOperatorStatusIn {
      doc /* /system/mrm/emergency_stop/status must report available. */
    }
    port operateMrmOut : OperateMrmOut;
    port mrmStateOut : MrmStateOut;
    port emergencyGearOut : GearCommandOut {
      doc /* /system/emergency/gear_cmd. */
    }
  }
  part def EmergencyStopOperatorNode {
    port operateMrmIn : OperateMrmIn;
    port initialControlCommandIn : ControlCommandIn {
      doc /* /control/command/control_cmd provides the inspected initial command feedback. */
    }
    port emergencyControlCommandOut : ControlCommandOut {
      doc /* /system/emergency/control_cmd. */
    }
    port operatorStatusOut : EmergencyStopOperatorStatusOut;
  }
  part def LegacyVehicleCommandGateNode {
    port kinematicStateIn : OdometryFeedbackIn {
      doc /* /localization/kinematic_state. */
    }
    port accelerationIn : AccelerationFeedbackIn {
      doc /* /localization/acceleration. */
    }
    port steeringIn : SteeringFeedbackIn {
      doc /* /vehicle/status/steering_status. */
    }
    port operationModeStateIn : OperationModeStateIn {
      doc /* /system/operation_mode/state. */
    }
    port engageIn : EngageInitializationIn {
      doc /* /autoware/engage. */
    }
    port mrmStateIn : MrmStateIn;
    port emergencyControlCommandIn : ControlCommandIn;
    port emergencyGearIn : GearCommandIn {
      doc /* /system/emergency/gear_cmd. */
    }
    port gatedControlCommandOut : ControlCommandOut {
      doc /* /control/command/control_cmd. */
    }
    port gatedGearOut : GearCommandOut {
      doc /* /control/command/gear_cmd. */
    }
  }

  part def AEBSystem1CandidateDeployment {
    doc /*
     * Simulation-only Autoware application deployment. ROS 2 is internal to
     * this application realization and is not the DE4SDV MiddlewareLayer.
     */
    part aeb : DeployedAEBNode;
    part aggregator : DiagnosticGraphAggregatorNode;
    part commandModeToOperationModeAvailabilityConverter : CommandModeToOperationModeAvailabilityConverterNode;
    part mrmHandler : MrmHandlerNode;
    part emergencyStopOperator : EmergencyStopOperatorNode;
    part legacyVehicleCommandGate : LegacyVehicleCommandGateNode;
    part runtime : ROS2ApplicationRuntime;
    part host : LinuxSimulationHost;
    part aebParameters : AEBParameterSelection;
    part diagnosticGraph : DiagnosticGraphSelection;
    part gateParameters : LegacyVehicleCommandGateSelection;
    part deferredControlCommandGate : DeferredControlCommandGateAlternative;

    port pointCloudIn : PointCloudInput;
    port autowareStateIn : AutowareStateInput;
    port velocityFeedbackIn : VelocityFeedbackIn;
    port imuFeedbackIn : ImuFeedbackIn;
    port tfAndVehicleInfoIn : TfAndVehicleInfoIn;
    port operationModeStateIn : OperationModeStateIn;
    port controlModeIn : ControlModeReportIn;
    port kinematicStateIn : OdometryFeedbackIn;
    port gateOperationModeStateIn : OperationModeStateIn;
    port gateKinematicStateIn : OdometryFeedbackIn;
    port gateAccelerationIn : AccelerationFeedbackIn;
    port gateSteeringIn : SteeringFeedbackIn;
    port gateEngageIn : EngageInitializationIn;
    port diagnosticsObservedOut : DiagnosticOut;
    port commandAvailabilityObservedOut : CommandAvailabilityOut;
    port operationAvailabilityObservedOut : OperationAvailabilityOut;
    port mrmRequestObservedOut : OperateMrmOut;
    port mrmStateObservedOut : MrmStateOut;
    port controlCommandOut : ControlCommandOut;
    port gearCommandOut : GearCommandOut;

    bind pointCloudIn = aeb.pointCloudIn;
    bind autowareStateIn = aeb.autowareStateIn;
    bind velocityFeedbackIn = aeb.velocityIn;
    bind imuFeedbackIn = aeb.imuIn;
    bind tfAndVehicleInfoIn = aeb.tfAndVehicleInfoIn;
    bind operationModeStateIn = mrmHandler.operationModeStateIn;
    bind controlModeIn = mrmHandler.controlModeIn;
    bind kinematicStateIn = mrmHandler.kinematicStateIn;
    bind gateOperationModeStateIn = legacyVehicleCommandGate.operationModeStateIn;
    bind gateKinematicStateIn = legacyVehicleCommandGate.kinematicStateIn;
    bind gateAccelerationIn = legacyVehicleCommandGate.accelerationIn;
    bind gateSteeringIn = legacyVehicleCommandGate.steeringIn;
    bind gateEngageIn = legacyVehicleCommandGate.engageIn;
    bind diagnosticsObservedOut = aeb.diagnosticsOut;
    bind commandAvailabilityObservedOut = aggregator.commandAvailabilityOut;
    bind operationAvailabilityObservedOut = commandModeToOperationModeAvailabilityConverter.operationAvailabilityOut;
    bind mrmRequestObservedOut = mrmHandler.operateMrmOut;
    bind mrmStateObservedOut = mrmHandler.mrmStateOut;
    bind controlCommandOut = legacyVehicleCommandGate.gatedControlCommandOut;
    bind gearCommandOut = legacyVehicleCommandGate.gatedGearOut;

    flow from aeb.diagnosticsOut.diagnostics to aggregator.diagnosticsIn.diagnostics;
    flow from aggregator.commandAvailabilityOut.availability
      to commandModeToOperationModeAvailabilityConverter.commandAvailabilityIn.availability;
    flow from commandModeToOperationModeAvailabilityConverter.operationAvailabilityOut.availability
      to mrmHandler.operationAvailabilityIn.availability;
    flow from mrmHandler.operateMrmOut.request to emergencyStopOperator.operateMrmIn.request;
    flow from emergencyStopOperator.operatorStatusOut.status
      to mrmHandler.emergencyStopStatusIn.status;
    flow from mrmHandler.mrmStateOut.state to legacyVehicleCommandGate.mrmStateIn.state;
    flow from emergencyStopOperator.emergencyControlCommandOut.command
      to legacyVehicleCommandGate.emergencyControlCommandIn.command;
    flow from mrmHandler.emergencyGearOut.gear to legacyVehicleCommandGate.emergencyGearIn.gear;
    flow from legacyVehicleCommandGate.gatedGearOut.gear to mrmHandler.gearIn.gear;
    // Inspected feedback topology: the gate output is also the operator's initial command.
    flow from legacyVehicleCommandGate.gatedControlCommandOut.command
      to emergencyStopOperator.initialControlCommandIn.command;
  }

  /* System 2 is test infrastructure, not a member of the production system. */
  part def AEBInputAndScenarioHarness {
    doc /*
     * Planned publisher of /autoware/state = DRIVING, API operation mode =
     * AUTONOMOUS for MRM, and system operation mode = AUTONOMOUS for the legacy
     * gate. It also supplies selected AEB point-cloud and TF/vehicle-info
     * dependencies plus simulator initialization.
     */
    port pointCloudOut : PointCloudOutput;
    port autowareStateDrivingOut : AutowareStateOutput;
    port apiOperationModeAutonomousOut : OperationModeStateOut {
      doc /* /api/operation_mode/state. */
    }
    port systemOperationModeAutonomousOut : OperationModeStateOut {
      doc /* /system/operation_mode/state. */
    }
    port tfAndVehicleInfoOut : TfAndVehicleInfoOut;
    port vectorMapOut : VectorMapInitializationOut;
    port initialPoseOut : InitialPoseOut;
    port plannedTrajectoryOut : PlannedTrajectoryOut;
    port engageOut : EngageInitializationOut;
    port scenarioControlIn : ScenarioControlIn;
  }
  part def ScenarioController {
    port scenarioControlOut : ScenarioControlOut;
  }
  part def SimplePlanningSimulatorTestDouble {
    doc /*
     * autoware_simple_planning_simulator. It is a vehicle-dynamics test double,
     * not a brake ECU, actuator, vehicle interface, or HardwareLayer member. It
     * provides odometry, control-mode, velocity, acceleration, steering, and
     * IMU, but does not publish /autoware/state, /api/operation_mode/state, or
     * /system/operation_mode/state.
     */
    port ackermannControlCommandIn : ControlCommandIn {
      doc /* input/ackermann_control_command consumes /control/command/control_cmd. */
    }
    port gearCommandIn : GearCommandIn;
    port vectorMapIn : VectorMapInitializationIn;
    port initialPoseIn : InitialPoseIn;
    port plannedTrajectoryIn : PlannedTrajectoryIn;
    port engageIn : EngageInitializationIn;
    port odometryOut : OdometryFeedbackOut;
    port controlModeAutonomousOut : ControlModeReportOut;
    port velocityOut : VelocityFeedbackOut;
    port accelerationOut : AccelerationFeedbackOut;
    port steeringOut : SteeringFeedbackOut;
    port imuOut : ImuFeedbackOut;
    port vehicleStatusOut : VehicleStatusFeedbackOut;
  }
  part def SimulationEvidenceCollector {
    doc /* Observation only; acceptance and execution belong to INC-AEBS-009. */
    port diagnosticsIn : DiagnosticIn;
    port commandAvailabilityIn : CommandAvailabilityIn;
    port operationAvailabilityIn : OperationAvailabilityIn;
    port mrmRequestIn : OperateMrmIn;
    port mrmStateIn : MrmStateIn;
    port controlCommandIn : ControlCommandIn;
    port odometryIn : OdometryFeedbackIn;
    port controlModeIn : ControlModeReportIn;
    port velocityIn : VelocityFeedbackIn;
    port accelerationIn : AccelerationFeedbackIn;
    port steeringIn : SteeringFeedbackIn;
    port imuIn : ImuFeedbackIn;
    port vehicleStatusIn : VehicleStatusFeedbackIn;
    port observationOut : EvidenceObservationOut;
  }

  part def AEBSystem2SimulationAssets {
    part harness : AEBInputAndScenarioHarness;
    part scenarioController : ScenarioController;
    part simulator : SimplePlanningSimulatorTestDouble;
    part evidenceCollector : SimulationEvidenceCollector;

    port pointCloudOut : PointCloudOutput;
    port autowareStateDrivingOut : AutowareStateOutput;
    port apiOperationModeAutonomousOut : OperationModeStateOut;
    port systemOperationModeAutonomousOut : OperationModeStateOut;
    port tfAndVehicleInfoOut : TfAndVehicleInfoOut;
    port engageOut : EngageInitializationOut;
    port controlCommandIn : ControlCommandIn;
    port gearCommandIn : GearCommandIn;
    port diagnosticsIn : DiagnosticIn;
    port commandAvailabilityIn : CommandAvailabilityIn;
    port operationAvailabilityIn : OperationAvailabilityIn;
    port mrmRequestIn : OperateMrmIn;
    port mrmStateIn : MrmStateIn;
    port kinematicStateOut : OdometryFeedbackOut;
    port controlModeAutonomousOut : ControlModeReportOut;
    port velocityOut : VelocityFeedbackOut;
    port accelerationOut : AccelerationFeedbackOut;
    port steeringOut : SteeringFeedbackOut;
    port imuOut : ImuFeedbackOut;

    bind pointCloudOut = harness.pointCloudOut;
    bind autowareStateDrivingOut = harness.autowareStateDrivingOut;
    bind apiOperationModeAutonomousOut = harness.apiOperationModeAutonomousOut;
    bind systemOperationModeAutonomousOut = harness.systemOperationModeAutonomousOut;
    bind tfAndVehicleInfoOut = harness.tfAndVehicleInfoOut;
    bind engageOut = harness.engageOut;
    bind controlCommandIn = simulator.ackermannControlCommandIn;
    bind gearCommandIn = simulator.gearCommandIn;
    bind diagnosticsIn = evidenceCollector.diagnosticsIn;
    bind commandAvailabilityIn = evidenceCollector.commandAvailabilityIn;
    bind operationAvailabilityIn = evidenceCollector.operationAvailabilityIn;
    bind mrmRequestIn = evidenceCollector.mrmRequestIn;
    bind mrmStateIn = evidenceCollector.mrmStateIn;
    bind kinematicStateOut = simulator.odometryOut;
    bind controlModeAutonomousOut = simulator.controlModeAutonomousOut;
    bind velocityOut = simulator.velocityOut;
    bind accelerationOut = simulator.accelerationOut;
    bind steeringOut = simulator.steeringOut;
    bind imuOut = simulator.imuOut;

    flow from scenarioController.scenarioControlOut.scenario to harness.scenarioControlIn.scenario;
    flow from harness.vectorMapOut.map to simulator.vectorMapIn.map;
    flow from harness.initialPoseOut.pose to simulator.initialPoseIn.pose;
    flow from harness.plannedTrajectoryOut.trajectory to simulator.plannedTrajectoryIn.trajectory;
    flow from harness.engageOut.engage to simulator.engageIn.engage;
    flow from controlCommandIn.command to evidenceCollector.controlCommandIn.command;
    flow from simulator.odometryOut.odometry to evidenceCollector.odometryIn.odometry;
    flow from simulator.controlModeAutonomousOut.mode to evidenceCollector.controlModeIn.mode;
    flow from simulator.velocityOut.velocity to evidenceCollector.velocityIn.velocity;
    flow from simulator.accelerationOut.acceleration to evidenceCollector.accelerationIn.acceleration;
    flow from simulator.steeringOut.steering to evidenceCollector.steeringIn.steering;
    flow from simulator.imuOut.imu to evidenceCollector.imuIn.imu;
    flow from simulator.vehicleStatusOut.status to evidenceCollector.vehicleStatusIn.status;
  }

  part def AEBTwoSystemSimulationDeployment {
    part system1 : AEBSystem1CandidateDeployment;
    part system2 : AEBSystem2SimulationAssets;

    // Selected AEB inputs only: point cloud, velocity, IMU, /autoware/state, and TF/vehicle info.
    flow from system2.pointCloudOut.pointCloud to system1.pointCloudIn.pointCloud;
    flow from system2.autowareStateDrivingOut.autowareState to system1.autowareStateIn.autowareState;
    flow from system2.velocityOut.velocity to system1.velocityFeedbackIn.velocity;
    flow from system2.imuOut.imu to system1.imuFeedbackIn.imu;
    flow from system2.tfAndVehicleInfoOut.configuration to system1.tfAndVehicleInfoIn.configuration;
    // MRM preconditions are independent of the availability conversion.
    flow from system2.apiOperationModeAutonomousOut.state to system1.operationModeStateIn.state;
    flow from system2.systemOperationModeAutonomousOut.state to system1.gateOperationModeStateIn.state;
    flow from system2.controlModeAutonomousOut.mode to system1.controlModeIn.mode;
    flow from system2.kinematicStateOut.odometry to system1.kinematicStateIn.odometry;
    // The selected legacy gate's source-backed filter and state dependencies.
    flow from system2.kinematicStateOut.odometry to system1.gateKinematicStateIn.odometry;
    flow from system2.accelerationOut.acceleration to system1.gateAccelerationIn.acceleration;
    flow from system2.steeringOut.steering to system1.gateSteeringIn.steering;
    flow from system2.engageOut.engage to system1.gateEngageIn.engage;
    // Exact legacy-gate/simulator command endpoints.
    flow from system1.controlCommandOut.command to system2.controlCommandIn.command;
    flow from system1.gearCommandOut.gear to system2.gearCommandIn.gear;
    // Observation taps do not feed the emergency-control decision.
    flow from system1.diagnosticsObservedOut.diagnostics to system2.diagnosticsIn.diagnostics;
    flow from system1.commandAvailabilityObservedOut.availability
      to system2.commandAvailabilityIn.availability;
    flow from system1.operationAvailabilityObservedOut.availability
      to system2.operationAvailabilityIn.availability;
    flow from system1.mrmRequestObservedOut.request to system2.mrmRequestIn.request;
    flow from system1.mrmStateObservedOut.state to system2.mrmStateIn.state;
  }

  part universeSource : PinnedAutowareUniverseSource;
  part launchSource : PinnedAutowareLaunchSource;
  part deployment : AEBTwoSystemSimulationDeployment;
  part logicalSystem : VehicleTargetAEBSLogicalSystem;

  dependency deploymentTracesUniverse from deployment.system1 to universeSource;
  dependency deploymentTracesLaunch from deployment to launchSource;

  /* P8_PLOM: logical responsibility to physical role only. */
  allocation def SimulationLogicalToPhysicalRealization;
  allocation stateAcquisitionToAEB : SimulationLogicalToPhysicalRealization
    allocate logicalSystem.stateAcquisition to deployment.system1.aeb;
  allocation interventionDecisionToAEB : SimulationLogicalToPhysicalRealization
    allocate logicalSystem.interventionDecision to deployment.system1.aeb;
  allocation emergencyCoordinationToAggregator : SimulationLogicalToPhysicalRealization
    allocate logicalSystem.emergencyCoordination to deployment.system1.aggregator;
  allocation emergencyCoordinationToAvailabilityConverter : SimulationLogicalToPhysicalRealization
    allocate logicalSystem.emergencyCoordination to deployment.system1.commandModeToOperationModeAvailabilityConverter;
  allocation emergencyCoordinationToMrmHandler : SimulationLogicalToPhysicalRealization
    allocate logicalSystem.emergencyCoordination to deployment.system1.mrmHandler;
  allocation emergencyCoordinationToOperator : SimulationLogicalToPhysicalRealization
    allocate logicalSystem.emergencyCoordination to deployment.system1.emergencyStopOperator;
  allocation emergencyCoordinationToLegacyVehicleGate : SimulationLogicalToPhysicalRealization
    allocate logicalSystem.emergencyCoordination to deployment.system1.legacyVehicleCommandGate;
  /* Proposed Physical Logical Item Mapping: logical to physical only. */
  allocation def LogicalToPhysicalItemRealization {
    doc /* Semantic realization, not schema identity or proof of satisfaction. */
  }
  allocation emergencyRequestToOperateMrm : LogicalToPhysicalItemRealization
    allocate EmergencyInterventionRequest to OperateMrmRequestMessage;
  allocation emergencyRequestToLegacyGateControl : LogicalToPhysicalItemRealization
    allocate EmergencyInterventionRequest to ControlCommandMessage;

  allocation vehicleMotionToVelocityFeedback : LogicalToPhysicalItemRealization
    allocate VehicleMotionState to VelocityReportFeedbackMessage;
  allocation vehicleMotionToKinematicFeedback : LogicalToPhysicalItemRealization
    allocate VehicleMotionState to OdometryFeedbackMessage;


  part def ItemNonEquivalenceRecord;
  part diagnosticIsNotEmergencyRequestOrBrakeCommand : ItemNonEquivalenceRecord {
    doc /*
     * AEBEmergencyStopDiagnosticStatus in AEBEmergencyStopDiagnosticArrayMessage is an
     * observed diagnostic transport. It is not EmergencyInterventionRequest,
     * OperateMrmRequestMessage, ControlCommandMessage, or simulator actuation.
     */
  }
  part availabilityStagesAreNotMrmRequest : ItemNonEquivalenceRecord {
    doc /*
     * CommandModeAvailabilityMessage and OperationModeAvailabilityMessage are
     * separate mode-availability stages. OperationModeAvailability.emergency_stop
     * is fallback availability; neither availability item is current
     * OperationModeStateMessage nor an MRM request/state.
     */
  }
  part mrmRequestAndStateAreDistinct : ItemNonEquivalenceRecord {
    doc /*
     * OperateMrmRequestMessage, EmergencyStopOperatorStatusMessage, and the MRM
     * handler's MrmStateMessage are separate request, operator-status, and gate-selection items.
     */
  }

  part simulatorFeedbackIsObservation : ItemNonEquivalenceRecord {
    doc /* Odometry, velocity, acceleration, IMU, and vehicle status are distinct feedback items. */
  }

  /* SAF concerns and direction-neutral review views. */
  concern physicalContextConcern : PhysicalContextConcern { subject candidateSystem : AEBSystem1CandidateDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }
  concern physicalContextExchangeConcern : PhysicalContextExchangeConcern { subject twoSystemDeployment : AEBTwoSystemSimulationDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }
  concern physicalExchangeTypeConcern : PhysicalExchangeTypeConcern { subject twoSystemDeployment : AEBTwoSystemSimulationDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }
  concern physicalStructureConcern : PhysicalStructureConcern { subject twoSystemDeployment : AEBTwoSystemSimulationDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }
  concern physicalInternalExchangeConcern : PhysicalInternalExchangeConcern { subject twoSystemDeployment : AEBTwoSystemSimulationDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }
  concern physicalInterfaceConcern : PhysicalInterfaceConcern { subject twoSystemDeployment : AEBTwoSystemSimulationDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }
  concern physicalLogicalMappingConcern : PhysicalLogicalMappingConcern { subject candidateSystem : AEBSystem1CandidateDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }
  concern physicalLogicalItemMappingConcern : PhysicalLogicalItemMappingConcern { subject candidateSystem : AEBSystem1CandidateDeployment; stakeholder systemsEngineer : SystemsEngineer; stakeholder reviewer : OpenSourceReviewer; }

  view aebsSimulationPhysicalContextView {
    viewpoint selected : PhysicalContextDefinitionViewpoint { frame physicalContextConcern; }
    doc /* System 1 is the candidate subject; sibling System 2 is external test infrastructure. */
    expose deployment::system1; expose deployment::system2;
    render asTreeDiagram;
  }
  view aebsSimulationPhysicalContextExchangeView {
    viewpoint selected : PhysicalContextExchangeViewpoint { frame physicalContextExchangeConcern; }
    expose deployment::*;
    render asTreeDiagram;
  }
  view aebsSimulationPhysicalExchangeTypeView {
    viewpoint selected : PhysicalExchangeTypeDefinitionViewpoint { frame physicalExchangeTypeConcern; }
    expose DE4SDV_AEBSSimulationDeployment::*;
    render asTreeDiagram;
  }
  view aebsSimulationPhysicalStructureView {
    viewpoint selected : PhysicalStructureDefinitionViewpoint { frame physicalStructureConcern; }
    expose deployment; expose deployment::system1::*; expose deployment::system2::*;
    render asTreeDiagram;
  }
  view aebsSimulationPhysicalInternalExchangeView {
    viewpoint selected : PhysicalInternalExchangeViewpoint { frame physicalInternalExchangeConcern; }
    expose deployment::system1::*; expose deployment::system2::*;
    render asTreeDiagram;
  }
  view aebsSimulationPhysicalInterfaceView {
    viewpoint selected : PhysicalInterfaceDefinitionViewpoint { frame physicalInterfaceConcern; }
    /*
     * Imported ROS 2 protocol definitions plus every concrete deployment port
     * definition. No deployment wildcard is admitted here: nodes, runtimes,
     * hosts, configuration records, simulator assets, and collectors belong in
     * structure/context views, not the interface-definition view.
     */
    expose ROS2TopicMessage; expose ROS2TopicSubscription; expose ROS2TopicPublication;
    expose ROS2PublishSubscribeTopicInterface;
    expose DiagnosticIn; expose DiagnosticOut;
    expose PointCloudInput; expose PointCloudOutput;
    expose AutowareStateInput; expose AutowareStateOutput;
    expose CommandAvailabilityIn; expose CommandAvailabilityOut;
    expose OperationAvailabilityIn; expose OperationAvailabilityOut;
    expose OperationModeStateIn; expose OperationModeStateOut;
    expose ControlModeReportIn; expose ControlModeReportOut;
    expose GearCommandIn; expose GearCommandOut;
    expose OperateMrmIn; expose OperateMrmOut;
    expose MrmStateIn; expose MrmStateOut;
    expose EmergencyStopOperatorStatusIn; expose EmergencyStopOperatorStatusOut;
    expose ControlCommandIn; expose ControlCommandOut;
    expose ScenarioControlIn; expose ScenarioControlOut;
    expose VectorMapInitializationIn; expose VectorMapInitializationOut;
    expose InitialPoseIn; expose InitialPoseOut;
    expose PlannedTrajectoryIn; expose PlannedTrajectoryOut;
    expose EngageInitializationIn; expose EngageInitializationOut;
    expose TfAndVehicleInfoIn; expose TfAndVehicleInfoOut;
    expose OdometryFeedbackIn; expose OdometryFeedbackOut;
    expose VelocityFeedbackIn; expose VelocityFeedbackOut;
    expose AccelerationFeedbackIn; expose AccelerationFeedbackOut;
    expose SteeringFeedbackIn; expose SteeringFeedbackOut;
    expose ImuFeedbackIn; expose ImuFeedbackOut;
    expose VehicleStatusFeedbackIn; expose VehicleStatusFeedbackOut;
    expose EvidenceObservationOut;
    render asTreeDiagram;
  }
  view aebsSimulationPhysicalLogicalMappingView {
    viewpoint selected : PhysicalLogicalMappingViewpoint { frame physicalLogicalMappingConcern; }
    /* System 2 is external and intentionally excluded from the System 1 realization mapping. */
    expose logicalSystem::*; expose deployment::system1::*;
    expose stateAcquisitionToAEB; expose interventionDecisionToAEB;
    expose emergencyCoordinationToAggregator; expose emergencyCoordinationToAvailabilityConverter;
    expose emergencyCoordinationToMrmHandler; expose emergencyCoordinationToOperator;
    expose emergencyCoordinationToLegacyVehicleGate;
    render asTreeDiagram;
  }
  view aebsSimulationPhysicalLogicalItemMappingView {
    viewpoint selected : PhysicalLogicalItemMappingViewpoint { frame physicalLogicalItemMappingConcern; }
    expose emergencyRequestToOperateMrm; expose emergencyRequestToLegacyGateControl;

    expose vehicleMotionToVelocityFeedback; expose vehicleMotionToKinematicFeedback;

    expose diagnosticIsNotEmergencyRequestOrBrakeCommand;
    expose availabilityStagesAreNotMrmRequest; expose mrmRequestAndStateAreDistinct;
    expose simulatorFeedbackIsObservation;
    render asTreeDiagram;
  }
}
