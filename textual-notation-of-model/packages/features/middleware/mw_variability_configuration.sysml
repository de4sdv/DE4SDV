/*
 * DE4SDV middleware variability and configuration model slice.
 *
 * INC-MW-009 records the configured-member assembly and the realization
 * decision around the deterministic product projection generated from
 * mw-autoware-aaos-sdv-reference.yaml. The BoF and generated projection own
 * the concrete variant selections; this package does not duplicate them.
 *
 * The selected direct realization is planned, not implemented. IFEX informs
 * service-interface classification and COVESA VSS supplies vehicle-signal
 * semantics. Neither is represented as deployed adapter software. The KUKSA
 * brokered path remains an explicit, unselected alternative.
 */

package DE4SDV_MWVariabilityConfiguration {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_MWRequirements::*;
  private import DE4SDV_MWPhysicalSoftwareRealization::*;
  private import Views::*;

  part incMW009 : FeatureIncrement {
    doc /* INC-MW-009: middleware variability and configured AAOS SDV member. */
  }

  part def MWAutowareAAOSSDVConfiguredMember :> ProductLineMemberProduct {
    doc /*
     * Product-level assembly controlled by the Phase 9 BoF and deterministic
     * generated platform-stack projection. The local parts compose accepted
     * shared assets; they do not independently choose platform variants.
     */
    part platformStack : MWAutowareAAOSSDVReference;
    part middlewareBoundary : MiddlewarePhysicalSoftwareBoundary;
  }

  part configuredMember : MWAutowareAAOSSDVConfiguredMember {
    doc /*
     * MW-CONFIG-001. Configuration evidence only. The selected application and
     * middleware derive the adapter through D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER.
     * Runtime support, requirement satisfaction, safety, compliance, and
     * interoperability are not implied by this configured-member usage.
     */
  }

  part ifexInterfaceDesignSource : SourceContributionRecord {
    doc /*
     * SRC-MW-IFEX-001. COVESA IFEX is an external interface-design source.
     * Repository: https://github.com/COVESA/ifex
     * Revision: 987038066ecd05d62a382eeed650449b7144e7f7
     * License: MPL-2.0.
     *
     * IFEX contributes protocol-independent Property, Method, Event, and type
     * classification. It is not a selected VSIDL generator, generated binding,
     * provider, transport, ROS 2 consumer, or deployed adapter implementation.
     */
  }

  part vehicleSpeedPropertyClassification : SourceContributionRecord {
    doc /*
     * SRC-MW-VSS-001. Current COVESA VSS Vehicle.Speed [km/h] is persistent
     * observable state and is therefore classified as an IFEX-informed
     * Property. A binding may provide change notification; this configuration
     * does not duplicate the state update as an independent Event.
     *
     * The canonical VSS semantic source remains the source-backed
     * COVESAVehicleSpeedSemanticSource owned by INC-MW-008.
     */
  }

  part directVSIDLToROS2Realization : MissingRealizationRecord {
    doc /*
     * REAL-MW-DIRECT-001. Selected planned realization style for the first
     * vehicle-speed slice:
     *
     *   AAOS VSIDL provider binding
     *   -> provider-neutral semantic normalizer
     *   -> ROS 2 VelocityReport publisher
     *
     * Vehicle.Speed [km/h] maps to VehicleSpeed.speed_kmh [km/h], then to
     * VelocityReport.longitudinal_velocity [m/s] by division by 3.6. The exact
     * reference contracts remain the reviewed .proto and .vsidl artifacts from
     * INC-MW-008. The provider binding, discovery, transport, publisher,
     * deployment, and observer are not implemented, not deployed, and not
     * empirically verified by INC-MW-009.
     *
     * This generic middleware realization does not carry the safety-critical
     * emergency-braking actuation path.
     */
  }

  part brokeredVehicleDataSource : SourceContributionRecord {
    doc /*
     * Source record for the Eclipse KUKSA Databroker candidate.
     * Repository: https://github.com/eclipse-kuksa/kuksa-databroker
     * Revision: fb07cafd2564e29032a5aeacc1a3361657eca0cb
     * License: Apache-2.0.
     * This is source provenance, not a configured runtime component.
     */
  }

  part kuksaBrokeredAlternative : DeferredProductLineScope {
    doc /*
     * ALT-MW-KUKSA-001. Unselected brokered realization candidate:
     *
     *   AAOS/VSIDL-to-KUKSA provider
     *   -> KUKSA Databroker
     *   -> KUKSA-to-Autoware ROS 2 consumer
     *
     * KUKSA Databroker is not selected for MW-CONFIG-001. No requirement for
     * multiple producers/consumers, shared VSS query/subscription, buffering,
     * or centralized vehicle-data policy currently justifies the additional
     * broker and two custom endpoint bindings.
     */
  }

  part configuredRuntimeEvidenceGap : DeferredProductLineScope {
    doc /*
     * GAP-MW-024: A valid BoF and deterministic product projection prove only
     * controlled configuration. They do not prove generated bindings, provider
     * behavior, discovery, transport, adapter deployment, ROS 2 publication,
     * independent Autoware observation, or retained runtime interoperability.
     */
  }

  dependency configuredPhysicalBoundaryTrace
    from configuredMember::middlewareBoundary
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSoftware;
  dependency selectedDirectRealizationTrace
    from configuredMember
    to directVSIDLToROS2Realization;
  dependency directPhysicalAdapterCandidateTrace
    from directVSIDLToROS2Realization
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSoftware::adapter;
  dependency exactReferenceContractTrace
    from directVSIDLToROS2Realization
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSoftwareSources::referenceInteropBenchSource;
  dependency vssVehicleSpeedSemanticTrace
    from vehicleSpeedPropertyClassification
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSoftwareSources::vssVehicleSpeedSource;
  dependency ifexPropertyClassificationTrace
    from vehicleSpeedPropertyClassification
    to ifexInterfaceDesignSource;
  dependency brokeredAlternativeSourceTrace
    from kuksaBrokeredAlternative
    to brokeredVehicleDataSource;
  dependency configuredRuntimeGapTrace
    from configuredMember
    to configuredRuntimeEvidenceGap;
  dependency directSourceContractGapTrace
    from directVSIDLToROS2Realization
    to DE4SDV_MWPhysicalSoftwareRealization::physicalSourceContractGap;
  dependency directVelocityContractGapTrace
    from directVSIDLToROS2Realization
    to DE4SDV_MWPhysicalSoftwareRealization::velocitySignalContractGap;

  dependency configuredSignalAccessRequirementTrace
    from configuredMember
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::System1Product::reqProvideMiddlewareSignalAccess;
  dependency configuredSafetyPathRequirementTrace
    from configuredMember
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::System1Product::reqIsolateSafetyPath;
  dependency configuredDiscoveryRequirementTrace
    from configuredMember
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::System1Product::reqProvideServiceDiscovery;
  dependency configuredAuthenticationRequirementTrace
    from configuredMember
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::System1Product::reqAuthenticateServiceBinding;

  concern productLineConfigurationConcern : ProductLineConfigurationConcern {
    doc /*
     * Review the selected feature variants in the deterministic generated
     * platform-stack projection. This concern is about choices, not assembly.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern productModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*
     * Review the resulting member-product composition: configured platform
     * stack plus the middleware physical/software boundary. This concern is
     * about assembled assets, not the full variation space.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  alias selectedVehicleApplication
    for MWAutowareAAOSSDVReference::vehicleApplication;
  alias selectedMiddleware
    for MWAutowareAAOSSDVReference::middleware;
  alias selectedOperatingSystem
    for MWAutowareAAOSSDVReference::osPlatform;
  alias selectedHypervisor
    for MWAutowareAAOSSDVReference::hypervisor;
  alias selectedApplicationMiddlewareAdapter
    for MWAutowareAAOSSDVReference::applicationMiddlewareAdapter;

  view mwProductLineConfigurationView {
    viewpoint selectedProductLineConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame productLineConfigurationConcern;
    }
    expose MWAutowareAAOSSDVReference;
    expose selectedVehicleApplication;
    expose selectedMiddleware;
    expose selectedOperatingSystem;
    expose selectedHypervisor;
    expose selectedApplicationMiddlewareAdapter;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }

  view mwProductModelAssemblyView {
    viewpoint selectedProductModelAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame productModelAssemblyConcern;
    }
    expose MWAutowareAAOSSDVConfiguredMember;
    expose MWAutowareAAOSSDVConfiguredMember::platformStack;
    expose MWAutowareAAOSSDVConfiguredMember::middlewareBoundary;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
