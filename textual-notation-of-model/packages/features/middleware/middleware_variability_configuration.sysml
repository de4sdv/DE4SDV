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
     * One instance and one owner per layer (owner decisions of 2026-10-23
     * and 2026-10-25). The platform stack owns the derived Autoware-to-AAOS
     * SDV adapter and the two layers of its guest side: the guest operating
     * system and the guest middleware. The middleware boundary only refers
     * to its adapter and to its AAOS SDV boundary. The AAOS SDV boundary
     * only refers to its platform software. Three bindings make these
     * references the same things as the derived adapter, the guest
     * middleware and the guest operating system. The middleware variant
     * androidSDV of the stack also refers to the guest middleware
     * (constraint C009). So the member has one adapter, one AAOS SDV and one
     * guest operating system, and the platform stack is their only owner.
     */
    part platformStack : MiddlewareAutowareAAOSSDVReference;
    part middlewareBoundary : MiddlewarePhysicalSoftwareBoundary;
    binding adapterBoundToDerivedAdapter
      bind middlewareBoundary.adapter = platformStack.applicationMiddlewareAdapter;
    binding aaosSdvBoundaryBoundToGuestMiddleware
      bind middlewareBoundary.aaosSdvBoundary = platformStack.guestMiddleware;
    binding platformSoftwareBoundToGuestOperatingSystem
      bind middlewareBoundary.aaosSdvBoundary.platformSoftware = platformStack.guestOSPlatform;
  }

  part configuredMember : MiddlewareAutowareAAOSSDVConfiguredMember {
    doc /*
     * MW-CONFIG-001. Configuration evidence only. The selected application and
     * middleware derive the adapter through D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER.
     * Runtime support, requirement satisfaction, safety, compliance, and
     * interoperability are not implied by this configured-member usage.
     *
     * Configuration management note: under the owner decision of one owner
     * per layer (2026-10-23), the structure of this configured member changed
     * twice. The first change, narrowed to the adapter on 2026-10-25, removed
     * the second adapter of the middleware boundary. Later on 2026-10-25 the
     * owner decided to give the AAOS SDV guest one owner too. Before, the
     * middleware boundary owned a second representation of the guest
     * (aaosSdvBoundary), and SDVCoreBoundary owned guest operating-system
     * content (platformSoftware: GKI, drivers, HALs). Now the middleware
     * boundary refers to its AAOS SDV boundary, and that boundary refers to
     * its platform software. Bindings make them the guest middleware and the
     * guest operating system of the platform stack, which owns both. So the
     * open item about the duplicate guest in this member is closed. Its
     * platform stack also changed in INC-MW-011 phase 9 (a Linux main side
     * and a guest side); the projection records that change. The identity
     * MW-CONFIG-001 is not renumbered, and no variant selection changed in
     * these two changes. E-MW-011 to E-MW-014 bind this identity, and
     * BL-MW-010-P12 rests on them. CLM-MW-010-01 and the other INC-MW-010
     * records take MiddlewareIntegrationVandVBench as subject, whose System 1
     * part is typed by MiddlewareAutowareAAOSSDVConfiguredMember, so they
     * inherit the change. So do the INC-AEBS-010 test article and its
     * verification bench, and with them EVID-AEBS-S2-001 to EVID-AEBS-S2-006,
     * which bind AEBS-CONFIG-010-001. All these records were retained against
     * the earlier content, the INC-MW-010 records at the baseline revision
     * b8170f6953567b07164b8c02be05be137f8047f0. No record is edited.
     *
     * Headless or display: the binding makes the guest middleware of this
     * member a headless SDV Core boundary (no JVM, no Android applications,
     * no GUI). That is right for MW-CONFIG-001: it selects no HMI display,
     * and its runtime evidence names the headless sdv_core_cf image
     * (E-MW-011, E-MW-013). The INC-AEBS-010 test article inherits this
     * headless guest middleware. It also composes a second AAOS SDV guest:
     * the display-capable sdv_ivi_cf guest of its System 2 instrument
     * (iviGuest : SdvIviCfGuestTarget). Its evidence ran that image. The doc
     * of SdvIviCfGuestTarget says that it replaces the headless sdv_core_cf
     * target, and the binding now contradicts that statement. So the binding
     * sharpens the discrepancy that INC-AEBS-010 records. How to model the
     * guest of the test article (one guest, headless or display) stays a
     * later owner decision.
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
     * stack plus the middleware physical/software boundary, with one instance
     * and one owner per platform layer. The boundary refers to the derived
     * adapter and to the guest middleware, and the guest middleware refers to
     * the guest operating system. The platform stack owns all three. This
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
     * The configured member, its two parts and the three bindings. Two
     * bindings make the adapter and the AAOS SDV boundary of the middleware
     * boundary the same things as the derived adapter and the guest
     * middleware. The third makes the platform software of the AAOS SDV
     * boundary the same thing as the guest operating system. The platform
     * stack is the only owner of all three.
     */
    expose MiddlewareAutowareAAOSSDVConfiguredMember;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::platformStack;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::middlewareBoundary;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::adapterBoundToDerivedAdapter;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::aaosSdvBoundaryBoundToGuestMiddleware;
    expose MiddlewareAutowareAAOSSDVConfiguredMember::platformSoftwareBoundToGuestOperatingSystem;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
