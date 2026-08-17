/*
 * DE4SDV vehicle sensing boundary architecture model slice.
 *
 * This package models the platform-level sensing boundary between physical
 * sensors and the ADAS application stack. It defines sensor categories,
 * observation semantics, perception pipeline boundary, and the traceability
 * path from sensor outputs to the ROS 2 topic message types consumed by the
 * AEBS physical software realization.
 *
 * Scope:
 *   - Abstract and concrete sensor boundary definitions
 *   - Observation item types bridging sensors to functional vocabulary
 *   - Perception pipeline boundary (raw sensor data to object-level output)
 *   - Vehicle sensing assembly with PLE variation points for sensor selection
 *   - Traceability dependencies from sensors to ROS 2 message types
 *
 * Out of scope:
 *   - Sensor internals (specs, range, resolution, calibration)
 *   - Concrete perception algorithm implementation
 *   - Physical wiring harness or ECU topology
 *   - Sensor-to-OS driver binding
 *
 * Relationship to SDV platform stack:
 *   Sensors reside in the HardwareLayer of the SDV platform stack. This slice
 *   specializes that boundary without coupling to any specific hardware vendor.
 *   Sensor suite composition is a product-line variation point: concrete member
 *   products select sensor variants per the PLE feature model.
 *
 * Relationship to AEBS:
 *   The AEBS physical software realization consumes ROS 2 topics published by
 *   sensors and the perception pipeline. This slice establishes the traceability
 *   from physical sensor types through observation items to those message types.
 *   It does not import AEBS logical architecture — the connection is through
 *   typed dependencies, not functional or logical flows.
 *
 * Semantic basis:
 * - SysML v2 specification: variation/variant notation (section 7.9)
 * - Systems-Modeling/SysML-v2-Release:
 *   training/36. Variability/Variation Definitions.sysml (definition-level variations)
 *   validation/07-Variant Configuration/7b-Variant Configurations.sysml (composition)
 */

package DE4SDV_VehicleSensingBoundary {
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_AEBSFunctionalBehavior::Features::AEBS::FunctionalBehavior::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;

  /* ──────────────────────────────────────────
   * Sensor boundary abstractions
   * ────────────────────────────────────────── */

  abstract part def SensorBoundary {
    doc /*
     * Abstract base for physical sensor boundaries at the vehicle sensing
     * layer. Concrete sensor types specialize this boundary and expose a typed
     * sensing output port for their observation stream.
     */

    port sensingOutputOut : SensingOutputPort;
  }

  abstract part def PerceptionSensorBoundary :> SensorBoundary {
    doc /*
     * Base boundary for sensors that produce perception-oriented data such as
     * point clouds or object-level detections.
     */
  }

  abstract part def VehicleStateSensorBoundary :> SensorBoundary {
    doc /*
     * Base boundary for sensors that produce vehicle motion or state data used
     * by the ADAS application stack and downstream vehicle behavior functions.
     */
  }

  /* ──────────────────────────────────────────
   * Sensor observation abstractions
   * ────────────────────────────────────────── */

  abstract item def SensorObservation {
    doc /*
     * Abstract base for all sensor outputs crossing the sensing boundary.
     * Concrete observation types carry the semantic meaning of each sensor
     * stream before it is mapped into application-facing software messages.
     */
  }

  item def PointCloudObservation :> SensorObservation {
    doc /* Raw 3D point cloud data from LiDAR or similar ranging sensors. */
  }

  item def IMUObservation :> SensorObservation {
    doc /* Inertial measurement data from an IMU sensor. */
  }

  item def VehicleMotionObservation :> SensorObservation {
    doc /* Vehicle speed, acceleration, and related motion-state observation data. */
  }

  item def PerceivedObjectObservation :> SensorObservation {
    doc /* Processed object-detection output produced by a perception pipeline. */
  }

  /*
   * Traceability from sensing observations to functional-behavior item types.
   * These links keep the platform sensing boundary aligned with the AEBS
   * functional-behavior vocabulary without importing logical architecture.
   */
  dependency pointCloudObservationSupportsVehicleMotionState from PointCloudObservation to VehicleMotionState;
  dependency imuObservationSupportsVehicleMotionState from IMUObservation to VehicleMotionState;
  dependency vehicleMotionObservationSupportsVehicleMotionState from VehicleMotionObservation to VehicleMotionState;
  dependency perceivedObjectObservationSupportsForwardTargetState from PerceivedObjectObservation to ForwardTargetState;

  /* ──────────────────────────────────────────
   * Sensing output port definition
   * ────────────────────────────────────────── */

  port def SensingOutputPort {
    doc /*
     * Generic sensing output port used by physical sensor boundaries and the
     * platform-level perception pipeline boundary.
     */
    out item observation : SensorObservation;
  }

  /* ──────────────────────────────────────────
   * Concrete sensor boundary specializations
   * ────────────────────────────────────────── */

  part def LiDARSensorBoundary :> PerceptionSensorBoundary {
    doc /* LiDAR sensor producing 3D point cloud observations. */
    port pointCloudOut : SensingOutputPort;
  }

  part def RadarSensorBoundary :> PerceptionSensorBoundary {
    doc /* Radar sensor producing object detection observations. */
    port radarObjectOut : SensingOutputPort;
  }

  part def CameraSensorBoundary :> PerceptionSensorBoundary {
    doc /* Camera sensor producing image-based object detection observations. */
    port cameraObjectOut : SensingOutputPort;
  }

  part def IMUSensorBoundary :> VehicleStateSensorBoundary {
    doc /* IMU sensor producing inertial motion observations. */
    port imuOut : SensingOutputPort;
  }

  part def WheelOdometrySensorBoundary :> VehicleStateSensorBoundary {
    doc /* Wheel odometry producing vehicle velocity observations. */
    port velocityOut : SensingOutputPort;
  }

  /*
   * Traceability from concrete sensor types to observation semantics and ROS 2
   * message types consumed by the AEBS physical software realization.
   */
  dependency lidarProducesPointCloudObservation from LiDARSensorBoundary to PointCloudObservation;
  dependency lidarProducesPointCloud2Message from LiDARSensorBoundary to PointCloud2Message;
  dependency radarProducesPerceivedObjectObservation from RadarSensorBoundary to PerceivedObjectObservation;
  dependency cameraProducesPerceivedObjectObservation from CameraSensorBoundary to PerceivedObjectObservation;
  dependency imuProducesImuObservation from IMUSensorBoundary to IMUObservation;
  dependency imuProducesImuMessage from IMUSensorBoundary to ImuMessage;
  dependency wheelOdometryProducesVehicleMotionObservation from WheelOdometrySensorBoundary to VehicleMotionObservation;
  dependency wheelOdometryProducesVelocityReportMessage from WheelOdometrySensorBoundary to VelocityReportMessage;

  /* ──────────────────────────────────────────
   * Sensor suite composition
   *
   * Motion sensors (IMU, wheel odometry) are common capabilities required
   * across all member products. They are NOT variation points — they are
   * plain parts of the sensing assembly, not features that distinguish
   * member products (ISO/IEC 26580).
   *
   * Perception sensors (LiDAR, radar, camera) are optional features that
   * distinguish member products. A product may have any combination (LiDAR +
   * camera, radar-only, all three, etc). SysML v2 variation/variant is
   * exclusive choice, so multi-select cannot be expressed as a single
   * variation. Instead, each perception sensor is an independent include/
   * exclude variation point using the [0]/[1] multiplicity pattern (same
   * pattern as the SDV platform stack's hypervisor "none" variant).
   *
   * The PLE feature model (sdv_product_line.yaml) uses or_group for perception
   * sensors, which expresses multi-select at the feature level. The
   * configurator resolves the YAML selections and annotates which sensors
   * are enabled in the generated product-model projection.
   * ────────────────────────────────────────── */

  part def SensorSuite {
    doc /* Abstract composite of one or more physical sensor boundaries selected for a member product. */
  }

  /*
   * Perception sensor variation points — independent include/exclude per
   * sensor. Each variation offers a present [1] or absent [0] variant.
   * A configured product selects present or absent for each independently,
   * enabling any combination (LiDAR + camera, radar-only, all three, etc).
   */
  variation part lidarSensor : LiDARSensorBoundary {
    variant part lidarPresent[1] : LiDARSensorBoundary;
    variant part lidarAbsent[0];
  }

  variation part radarSensor : RadarSensorBoundary {
    variant part radarPresent[1] : RadarSensorBoundary;
    variant part radarAbsent[0];
  }

  variation part cameraSensor : CameraSensorBoundary {
    variant part cameraPresent[1] : CameraSensorBoundary;
    variant part cameraAbsent[0];
  }

  /* ──────────────────────────────────────────
   * Perception pipeline boundary
   * ────────────────────────────────────────── */

  part def PerceptionPipelineBoundary {
    doc /*
     * Boundary between raw sensor observations and processed perception outputs
     * consumed by ADAS applications. The perception pipeline fuses raw sensor
     * data into object-level perception results. Concrete perception
     * implementation (e.g. Autoware perception stack) is a separate concern.
     */

    port rawSensorIn : SensingOutputPort;
    port perceivedObjectsOut : SensingOutputPort;
  }

  dependency perceptionPipelineProducesPerceivedObjectObservation from PerceptionPipelineBoundary to PerceivedObjectObservation;
  dependency perceptionPipelineProducesPredictedObjectsMessage from PerceptionPipelineBoundary to PredictedObjectsMessage;
  dependency perceptionPipelineRelaysPointCloud2Message from PerceptionPipelineBoundary to PointCloud2Message;

  /* ──────────────────────────────────────────
   * Vehicle sensing assembly
   * ────────────────────────────────────────── */

  part def VehicleSensingAssembly {
    doc /*
     * Platform-level sensing assembly for an SDV member product. Composes
     * common motion sensors (present in all member products) with optional
     * perception sensors (selected per product-line configuration) and the
     * perception pipeline.
     */

    // Common capabilities — present in all member products, not variation points
    part imuSensor : IMUSensorBoundary;
    part wheelOdometrySensor : WheelOdometrySensorBoundary;

    // Perception sensor variation points — independent include/exclude per sensor
    variation part lidarSensor : LiDARSensorBoundary;
    variation part radarSensor : RadarSensorBoundary;
    variation part cameraSensor : CameraSensorBoundary;

    part perceptionPipeline : PerceptionPipelineBoundary;
  }

  /*
   * The sensing assembly resides in the hardware layer of the SDV platform
   * stack. This dependency makes the stack relationship explicit without
   * modeling internal hardware topology.
   */
  dependency sensingAssemblyResidesInHardwareLayer from VehicleSensingAssembly to HardwareLayer;

  /* ──────────────────────────────────────────
   * SAF physical-domain concern and view
   * ──────────────────────────────────────────
   * Uses SAF PhysicalStructureDefinitionViewpoint (P2_PSTD) — not an
   * invented viewpoint. The sensing boundary is a physical/software
   * structure that needs to be visible for integration review.
   */

  concern sensingBoundaryStructureConcern : PhysicalStructureConcern {
    doc /*
     * Reviewers need the sensor-to-application traceability boundary to be
     * visible: which physical sensors produce the observations that feed the
     * ADAS application stack.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view sensingBoundaryView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame sensingBoundaryStructureConcern;
    }

    expose SensorBoundary;
    expose PerceptionSensorBoundary;
    expose VehicleStateSensorBoundary;
    expose SensorObservation;
    expose PointCloudObservation;
    expose IMUObservation;
    expose VehicleMotionObservation;
    expose PerceivedObjectObservation;
    expose SensingOutputPort;
    expose LiDARSensorBoundary;
    expose RadarSensorBoundary;
    expose CameraSensorBoundary;
    expose IMUSensorBoundary;
    expose WheelOdometrySensorBoundary;
    expose SensorSuite;
    expose PerceptionPipelineBoundary;
    expose VehicleSensingAssembly;
    expose pointCloudObservationSupportsVehicleMotionState;
    expose imuObservationSupportsVehicleMotionState;
    expose vehicleMotionObservationSupportsVehicleMotionState;
    expose perceivedObjectObservationSupportsForwardTargetState;
    expose lidarProducesPointCloudObservation;
    expose lidarProducesPointCloud2Message;
    expose radarProducesPerceivedObjectObservation;
    expose cameraProducesPerceivedObjectObservation;
    expose imuProducesImuObservation;
    expose imuProducesImuMessage;
    expose wheelOdometryProducesVehicleMotionObservation;
    expose wheelOdometryProducesVelocityReportMessage;
    expose perceptionPipelineProducesPerceivedObjectObservation;
    expose perceptionPipelineProducesPredictedObjectsMessage;
    expose perceptionPipelineRelaysPointCloud2Message;
    expose SensorSuite;
    expose sensingAssemblyResidesInHardwareLayer;
    render asTreeDiagram;
  }
}
