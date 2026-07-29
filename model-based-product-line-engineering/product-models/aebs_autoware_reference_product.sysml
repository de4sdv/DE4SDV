/*
 * DE4SDV AEBS Autoware reference member product — composite projection.
 *
 * This is a hand-authored composite product model that ties together the
 * platform-stack shared asset, the vehicle sensing boundary, and the AEBS
 * physical software realization into a single AEBS-equipped member product.
 *
 * The platform-stack variant selections for this product are documented in
 * the bill-of-features (aebs-autoware-linux-lidar-camera.yaml) and resolved
 * in the generated projection (aebs_autoware_linux_lidar_camera.sysml).
 * This composite model references the shared-asset definitions directly and
 * composes them with the sensing boundary and AEBS physical software to make
 * the full product-level traceability visible:
 *
 *   platform stack (Autoware on Linux)
 *     -> sensing boundary (LiDAR + camera + IMU + wheel odometry)
 *       -> perception pipeline (raw sensor data to object-level output)
 *         -> AEBS physical software (AEB node consuming ROS 2 topics)
 *
 * The sensing selections (LiDAR + camera) match the bill-of-features.
 * The common motion sensors (IMU, wheel odometry) are present in all member
 * products per the feature model (mandatory, not a feature).
 *
 * Scope:
 *   - Composition of platform stack, sensing boundary, and AEBS software
 *   - Dependency links from sensing boundary to AEB node ROS 2 topic types
 *   - Allocation links from AEBS logical architecture to physical software
 *
 * Out of scope:
 *   - Vehicle-level middleware integration (S-CORE, Android SDV)
 *   - Brake actuation, vehicle command gate, MRM handler
 *   - Runtime deployment configuration (INC-AEBS-008)
 *   - Evidence generation (INC-AEBS-009)
 *
 * Relationship to PLE:
 *   The platform-stack projection is generated from the bill-of-features.
 *   The sensing boundary is a shared-asset superset (150% model) with
 *   independent include/exclude variation points per perception sensor.
 *   This composite model does not resolve those variations in SysML —
 *   it references the sensing assembly and its traceability dependencies
 *   as the structural context for the AEB node's ROS 2 topic inputs.
 */

package DE4SDV_AEBSAutowareReferenceProduct {
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_VehicleSensingBoundary::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import DE4SDV_AEBSLogicalArchitecture::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def AEBSAutowareReferenceProduct {
    doc /*
     * Composite AEBS reference member product.
     *
     * Platform: Autoware on Eclipse S-CORE on Linux, no hypervisor.
     * Sensing: LiDAR + camera perception sensors, IMU + wheel odometry common.
     * AEBS: Vehicle-target forward collision mitigation only.
     *
     * This product composes the platform stack with the sensing boundary
     * and the AEBS physical software realization. It makes the traceability
     * from physical sensors through ROS 2 topics to the AEB node visible
     * in a single product-level view.
     */

    /* Platform stack — shared-asset superset. Variant selections are
     * resolved in the generated projection
     * (aebs_autoware_linux_lidar_camera.sysml). */
    part platformStack : SDVPlatformStack;

    /* Sensing boundary — common motion sensors + selected perception sensors. */
    part sensingAssembly : VehicleSensingAssembly;

    /* AEBS physical software — the Autoware AEB node and its required boundaries. */
    part aebsSoftware : VehicleTargetAEBSPhysicalSoftwareBoundary;

    /* AEBS logical system — the technology-neutral logical architecture. */
    part aebsLogicalSystem : VehicleTargetAEBSLogicalSystem;

    /*
     * Product-level traceability: sensing assembly resides in the hardware
     * layer of the platform stack. The sensing boundary model declares
     * this dependency (sensingAssemblyResidesInHardwareLayer from
     * VehicleSensingAssembly to HardwareLayer); restated here at the
     * product level by linking the product's sensing assembly to its
     * platform stack.
     */
    dependency productSensingToPlatformStack from sensingAssembly to platformStack;

    /*
     * Product-level traceability: the AEB node's ROS 2 topic inputs trace
     * back to sensors and the perception pipeline. These dependencies are
     * declared in DE4SDV_VehicleSensingBoundary and are visible through
     * the import. Key links:
     *
     *   LiDARSensorBoundary -> PointCloud2Message (AEB node port pointCloudIn)
     *   IMUSensorBoundary -> ImuMessage (AEB node port imuIn)
     *   WheelOdometrySensorBoundary -> VelocityReportMessage (AEB node port velocityIn)
     *   PerceptionPipelineBoundary -> PredictedObjectsMessage (AEB node port predictedObjectsIn)
     */

    /*
     * Product-level traceability: the AEBS logical-to-physical allocation is
     * declared in DE4SDV_AEBSPhysicalSoftwareRealization. The logical
     * system's responsibilities are allocated to the AEB node with typed
     * coverage records (available, partial, missing).
     */
  }

  /*
   * SAF concern: product-level traceability.
   */
  concern def ProductTraceabilityConcern {
    doc /*
     * Product-level traceability concern for composite member products
     * that compose platform stack, sensing boundary, and ADAS physical
     * software realization.
     */
    require constraint {
      doc /*
       * A product traceability view shall show the platform-stack layers,
       * sensing boundary sensor types and observation items, perception
       * pipeline, and AEBS physical software ROS 2 topic dependencies.
       */
    }
  }

  concern productTraceabilityConcern : ProductTraceabilityConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }
}
