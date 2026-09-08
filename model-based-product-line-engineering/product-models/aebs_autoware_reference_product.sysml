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
 *   - Product-level traceability dependencies (sensors to AEB node, AEBS
 *     required boundaries to platform elements)
 *   - Allocation links from AEBS logical architecture to physical software
 *
 * Out of scope:
 *   - Vehicle-level middleware integration (S-CORE, Android SDV) — this
 *     product selects no vehicle-level middleware
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
  private import DE4SDV_AEBSProductLineScope::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def AEBSAutowareReferenceProduct :> StandaloneAutowareAEBSReferenceMember {
    doc /*
     * Composite AEBS reference member product. Specializes the governed
     * planned-member decision (StandaloneAutowareAEBSReferenceMember in
     * DE4SDV_AEBSProductLineScope), so this composite carries the
     * ProductLineMemberProduct lineage that product-line queries resolve.
     *
     * Platform: Autoware on Linux, no vehicle-level middleware, no hypervisor.
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
    part aebsLogicalSystem : VehicleTargetAEBSSystem;

    /*
     * Product-level traceability: sensing assembly resides in the hardware
     * layer of the platform stack.
     */
    dependency productSensingToPlatformStack from sensingAssembly to platformStack;

    /*
     * Product-level traceability: the AEB node's ROS 2 topic inputs trace
     * back to sensors and the perception pipeline. Key links (declared in
     * DE4SDV_VehicleSensingBoundary, visible through import):
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
     *
     * Canonical-architecture binding: the composite usages above are
     * product-level instances, while the canonical allocation and evidence
     * records bind the canonical usages
     * DE4SDV_AEBSLogicalArchitecture::system and
     * DE4SDV_AEBSPhysicalSoftwareRealization::physicalSoftware. The
     * explicit dependencies below bind this product's instances to those
     * canonical elements, so product-level trace queries can reach the
     * canonical allocation and evidence records without claiming that the
     * composite owns them.
     *
     * Bounded projection limitation (unchanged): importing the packages
     * does not transfer instance-level identity, and the explicit reference
     * dependencies do not restate the canonical allocations at product
     * level. Platform-stack variant selections are resolved only in the
     * generated projection (aebs_autoware_linux_lidar_camera.sysml), and
     * sensing-boundary perception-sensor selections live in the
     * bill-of-features, not in this composite. Product-level trace claims
     * must still cite the canonical allocation records; these dependencies
     * make the binding path explicit, they do not make this composite a
     * resolved configured product.
     */
    dependency aebsLogicalSystemBindingToCanonicalSystem
      from aebsLogicalSystem
      to DE4SDV_AEBSLogicalArchitecture::system;
    dependency aebsSoftwareBindingToCanonicalPhysicalSoftware
      from aebsSoftware
      to DE4SDV_AEBSPhysicalSoftwareRealization::physicalSoftware;
  }

  /*
   * SAF physical-domain concerns and views.
   *
   * Uses SAF PhysicalLogicalMappingViewpoint (P8_PLOM) for the
   * product-level traceability view — not an invented viewpoint. The
   * composite product maps logical architecture to physical software
   * realization, which is exactly what P8_PLOM addresses.
   *
   * Uses SAF PhysicalStructureDefinitionViewpoint (P2_PSTD) for the
   * product structure view showing the composition of platform stack,
   * sensing boundary, and AEBS software.
   */

  concern productStructureConcern : PhysicalStructureConcern {
    doc /*
     * Reviewers need the product-level composition visible: platform stack,
     * sensing boundary, AEBS physical software, and their structural
     * relationships.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern productMappingConcern : PhysicalLogicalMappingConcern {
    doc /*
     * Reviewers need the product-level traceability visible: which physical
     * elements (sensors, AEB node, required boundaries) realize which logical
     * responsibilities, and where the gaps are.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view productStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame productStructureConcern;
    }

    expose AEBSAutowareReferenceProduct;
    expose SDVPlatformStack;
    expose VehicleSensingAssembly;
    expose VehicleTargetAEBSPhysicalSoftwareBoundary;
    expose VehicleTargetAEBSSystem;
    render asTreeDiagram;
  }

  view productMappingView {
    viewpoint selectedPhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame productMappingConcern;
    }

    expose AEBSAutowareReferenceProduct;
    render asTreeDiagram;
  }
}
