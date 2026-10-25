/*
 * DE4SDV middleware variability and configuration model slice.
 *
 * INC-MW-009 records the configured-member assembly and the realization
 * decision around the deterministic product projection generated from the
 * receipt of the feature configuration
 * middleware_autoware_aaos_sdv_reference.sysml. The feature configuration and
 * generated projection own the concrete variant selections; this package does
 * not duplicate them.
 *
 * The selected direct realization is planned, not implemented. IFEX informs
 * service-interface classification and COVESA VSS supplies vehicle-signal
 * semantics. Neither is represented as deployed adapter software. The KUKSA
 * brokered path remains an explicit, unselected alternative.
 */

package DE4SDV_MiddlewareVariabilityConfiguration {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_MiddlewareRequirements::*;
  private import DE4SDV_MiddlewarePhysicalSoftwareRealization::*;
  private import Views::*;

  part incMW009 : FeatureIncrement {
    doc /* INC-MW-009: middleware variability and configured AAOS SDV member. */
  }

  part def MiddlewareAutowareAAOSSDVConfiguredMember :> DE4SDV_AEBSProductLineScope::AAOSIntegratedAutowareAEBSReferenceMember {
    doc /*
     * Product-level assembly controlled by its feature configuration (the
     * PLEML restatement of the Phase 9 BoF) and deterministic generated
     * platform-stack projection. The local parts compose accepted
     * shared assets; they do not independently choose platform variants.
     *
     * One owner for the adapter layer (owner decisions of 2026-10-23 and
     * 2026-10-25). The platform stack owns the derived Autoware-to-AAOS SDV
     * adapter. The middleware boundary only refers to its adapter, and one
     * binding makes that reference the same thing as the derived adapter. So
     * the member has one adapter, and the platform stack is its only owner.
     * The AAOS SDV guest still has two representations: the guest
     * middleware of the platform stack, and the AAOS SDV boundary of the
     * middleware boundary. The configuration management note of
     * configuredMember records this open item.
     */
    part platformStack : MiddlewareAutowareAAOSSDVReference;
    part middlewareBoundary : MiddlewarePhysicalSoftwareBoundary;
    binding adapterBoundToDerivedAdapter
      bind middlewareBoundary.adapter = platformStack.applicationMiddlewareAdapter;
  }

  part configuredMember : MiddlewareAutowareAAOSSDVConfiguredMember {
    doc /*
     * MW-CONFIG-001. Configuration evidence only. The selected application and
     * middleware derive the adapter through D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER.
     * Runtime support, requirement satisfaction, safety, compliance, and
     * interoperability are not implied by this configured-member usage.
     *
     * Configuration management note: on 2026-10-23 the owner decided one
     * owner per layer for this configured member, and on 2026-10-25 the owner
     * narrowed the change to the adapter. Before, the middleware boundary
     * owned a second adapter. Now it refers to the derived adapter that the
     * platform stack owns. The identity MW-CONFIG-001 is not renumbered, and
     * no variant selection changed. E-MW-011 to E-MW-014 bind this identity,
     * and BL-MW-010-P12 rests on them. CLM-MW-010-01 and the other INC-MW-010
     * records take MiddlewareIntegrationVandVBench as subject, whose System 1
     * part is typed by MiddlewareAutowareAAOSSDVConfiguredMember, so they
     * inherit the change. So do the INC-AEBS-010 test article and its
     * verification bench. All these records were retained against the
     * earlier content, the INC-MW-010 records at the baseline revision
     * b8170f6953567b07164b8c02be05be137f8047f0. No record is edited.
     *
     * Open item (owner decision of 2026-10-25): the middleware boundary still
     * represents the AAOS SDV guest a second time (aaosSdvBoundary). The
     * first representation is the guest middleware of the platform stack.
     * SDVCoreBoundary also holds guest operating-system content
     * (platformSoftware: GKI, drivers, HALs). It describes the headless
     * sdv_core_cf image, while the INC-AEBS-010 evidence ran the
     * display-capable sdv_ivi_cf image. How to model the AAOS SDV guest
     * (operating system or middleware, headless or display) is a later owner
     * decision.
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
     * GAP-MW-024: A valid feature configuration and deterministic product
     * projection prove only controlled configuration. They do not prove
     * generated bindings, provider behavior, discovery, transport, adapter
     * deployment, ROS 2 publication, independent Autoware observation, or
     * retained runtime interoperability.
     */
  }

  dependency configuredPhysicalBoundaryTrace
    from configuredMember::middlewareBoundary
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftware;
  dependency selectedDirectRealizationTrace
    from configuredMember
    to directVSIDLToROS2Realization;
  dependency directPhysicalAdapterCandidateTrace
    from directVSIDLToROS2Realization
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftware::adapter;
  dependency exactReferenceContractTrace
    from directVSIDLToROS2Realization
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftwareSources::referenceInteropBenchSource;
  dependency vssVehicleSpeedSemanticTrace
    from vehicleSpeedPropertyClassification
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftwareSources::vssVehicleSpeedSource;
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
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSourceContractGap;
  dependency directVelocityContractGapTrace
    from directVSIDLToROS2Realization
    to DE4SDV_MiddlewarePhysicalSoftwareRealization::velocitySignalContractGap;

  dependency configuredSignalAccessRequirementTrace
    from configuredMember
    to DE4SDV_MiddlewareRequirements::Features::Middleware::Requirements::System1Product::reqProvideMiddlewareSignalAccess;
  dependency configuredSafetyPathRequirementTrace
    from configuredMember
    to DE4SDV_MiddlewareRequirements::Features::Middleware::Requirements::System1Product::reqIsolateSafetyPath;
  dependency configuredDiscoveryRequirementTrace
    from configuredMember
    to DE4SDV_MiddlewareRequirements::Features::Middleware::Requirements::System1Product::reqProvideServiceDiscovery;
  dependency configuredAuthenticationRequirementTrace
    from configuredMember
    to DE4SDV_MiddlewareRequirements::Features::Middleware::Requirements::System1Product::reqAuthenticateServiceBinding;

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
     * stack plus the middleware physical/software boundary. The boundary
     * refers to the derived adapter, which the platform stack owns. It still
     * owns a second representation of the AAOS SDV guest, an open item. This
     * concern is about assembled assets, not the full variation space.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  alias selectedVehicleApplication
    for MiddlewareAutowareAAOSSDVReference::vehicleApplication;
  alias selectedMiddleware
    for MiddlewareAutowareAAOSSDVReference::middleware;
  alias selectedOperatingSystem
    for MiddlewareAutowareAAOSSDVReference::osPlatform;
  alias selectedHypervisor
    for MiddlewareAutowareAAOSSDVReference::hypervisor;
  alias selectedApplicationMiddlewareAdapter
    for MiddlewareAutowareAAOSSDVReference::applicationMiddlewareAdapter;
  /* The guest side of the platform stack, added in INC-MW-011 phase 9. */
  alias selectedGuestOperatingSystem
    for MiddlewareAutowareAAOSSDVReference::guestOSPlatform;
  alias selectedGuestMiddleware
    for MiddlewareAutowareAAOSSDVReference::guestMiddleware;

  view middlewareProductLineConfigurationView {
    viewpoint selectedProductLineConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame productLineConfigurationConcern;
    }
    expose MiddlewareAutowareAAOSSDVReference;
    expose selectedVehicleApplication;
    expose selectedMiddleware;
    expose selectedOperatingSystem;
    expose selectedHypervisor;
    expose selectedGuestOperatingSystem;
    expose selectedGuestMiddleware;
    expose selectedApplicationMiddlewareAdapter;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }

  view middlewareProductModelAssemblyView {
    viewpoint selectedProductModelAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame productModelAssemblyConcern;
    }
    doc /*
     * The configured member, its two parts and the binding. The binding
     * makes the adapter of the middleware boundary the same thing as the
     * derived adapter of the platform stack. The boundary only refers to the
     * adapter. The platform stack is its only owner.
     */
    expose MiddlewareAutowareAAOSSDVConfiguredMember;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::platformStack;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::middlewareBoundary;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::adapterBoundToDerivedAdapter;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
