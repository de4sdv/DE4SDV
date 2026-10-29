/*
 * DE4SDV middleware variability and configuration model slice for the
 * Eclipse S-CORE realization.
 *
 * INC-MW-011, phase 9: the configured product of the Eclipse S-CORE
 * reference configuration, with the configuration identity MW-CONFIG-002.
 * It pairs two parts. The first is the platform-stack projection that the
 * configurator generates from the receipt of the feature configuration
 * middleware_autoware_score_reference.sysml. The second is the realization
 * of the middleware integration layer from phase 8. INC-MW-009 pairs the
 * projection of its member with the middleware boundary in the same way.
 * The feature configuration and the generated projection own the variant
 * selections. No element of this package restates them. Its docs name some
 * of them, and a guard test keeps those names equal to the receipt.
 *
 * The configuration is valid and not admitted. The receipt gives three
 * reasons. First, Eclipse S-CORE is reference-only. Second, the HMI display
 * has no element in the governed scope. Third, the guest side realizes the
 * AAOS-integrated alternative without its middleware androidSDV. So the
 * configured product specializes no member-product type. The member
 * decision is phase-12 work, after the runnable proof of phase 10 (owner
 * decision of 2026-10-21). This slice is configuration evidence only: it
 * proves no runtime behavior, satisfies no requirement and makes no safety,
 * cybersecurity or compliance claim.
 */

package DE4SDV_MiddlewareSCOREVariabilityConfiguration {
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization::SCOREMiddlewareIntegrationLayerRealization;
  private import DE4SDV_ProductLine::ProductLineConfiguredProduct;
  private import Views::*;

  part def MiddlewareAutowareSCOREConfiguredProduct :> ProductLineConfiguredProduct {
    doc /*
     * The configured product of the Eclipse S-CORE reference configuration.
     * It holds the generated platform-stack projection and the realization of
     * the middleware integration layer, the system of interest of INC-MW-011.
     * The local parts compose the projection and the phase-8 realization.
     * They choose no variant. The context parts of phase 8 stay in the
     * physical context SCORETwoDomainPhysicalSystem. Examples are the
     * Autoware-based AEBS stack, the vehicle-speed provider and the HMI
     * application in the guest.
     *
     * One instance and one owner per layer. The platform stack composes the
     * selected Eclipse S-CORE middleware, the derived Autoware-to-S-CORE
     * adapter, the guest middleware and the guest operating system. The
     * integration layer only refers to its S-CORE services, to its adapter,
     * to the SDV Core of the guest and to the SDV Gateway on IVI (phase 8).
     * Two bindings make the S-CORE services and the adapter of the layer the
     * same things as the selected middleware and the derived adapter. Two
     * more make the SDV Core the same thing as the guest middleware, and its
     * platform software the same thing as the guest operating system. The
     * AAOS-integrated configured member has the same two bindings. So the
     * platform stack is the only owner of each. The platform stack models
     * the guest middleware as one layer, with no feature for the gateway of
     * the IVI VM. So this product leaves the layer's reference to the SDV
     * Gateway on IVI unbound, and phase 8 binds it to the gateway of the IVI
     * VM. The other
     * parts of the layer are no platform layers. The guest side is the guest
     * operating system and the guest middleware of the platform stack: in
     * phase 8, a guest partition of two VMs (ADR 0025). So the product has
     * no second Android or AAOS SDV instance. For the same reason it does
     * not compose SCORETwoDomainPhysicalSystem.
     *
     * No shared asset implements the HMI display, so no feature binding
     * resolves the hmiDisplay selection. The projection lists it among the
     * selections that SysML does not resolve.
     *
     * The definition specializes no member-product type, because the
     * configuration is not admitted. If the owner admits the member in phase
     * 12, it specializes the new member definition. The AAOS-integrated
     * configured member specializes its member definition in the same way.
     * It specializes the kernel's ProductLineConfiguredProduct, the
     * configured product of phase 9 (owner decision of 2026-10-29).
     */
    part platformStack : MiddlewareAutowareSCOREReference;
    part integrationLayer : SCOREMiddlewareIntegrationLayerRealization;
    binding scoreServicesBoundToSelectedMiddleware
      bind integrationLayer.scoreServices = platformStack.middleware;
    binding adapterBoundToDerivedAdapter
      bind integrationLayer.adapter = platformStack.applicationMiddlewareAdapter;
    binding sdvCoreBoundToGuestMiddleware
      bind integrationLayer.sdvCore = platformStack.guestMiddleware;
    binding platformSoftwareBoundToGuestOperatingSystem
      bind integrationLayer.sdvCore.platformSoftware = platformStack.guestOSPlatform;
  }

  part <'MW-CONFIG-002'> configuredProduct : MiddlewareAutowareSCOREConfiguredProduct {
    doc /*
     * MW-CONFIG-002: the configuration identity that the phase-10 evidence
     * binds, as the INC-MW-010 evidence binds MW-CONFIG-001. The identity is
     * bound to the exact receipt that the configurator generated the
     * platform-stack projection from. receiptSha256 is the SHA-256 of
     * model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json.
     * That receipt records the evaluation of the feature configuration
     * middlewareAutowareSCOREReference: valid, with the derived adapter
     * autowareToSCORE, and not admitted. A receipt re-cut keeps this
     * identity and rebinds receiptSha256 here. The pull request that rebinds
     * it states whether the configuration's own receipt record changed.
     * Evidence that binds MW-CONFIG-002 also records the receipt SHA-256 it
     * ran against.
     *
     * The guest side holds two VMs (phase 8, ADR 0025). The headless
     * sdv_core_cf SDV Core VM runs the SOME/IP broker (sdvCoreGuest). The
     * display-capable sdv_ivi_cf IVI VM of INC-AEBS-010 runs the HMI
     * (hmiGuest). The IVI frame relay of phase 8 runs in the IVI VM. For the
     * bench, both images come from one android17-release revision. The
     * SOME/IP mapping and the stack configuration go into the SDV Core image
     * when it is built, and the relay is provisioned on the IVI image. An IVI
     * image built with the relay stays open (GAP-MW-038).
     *
     * Configuration evidence only. This usage proves no provider, transport,
     * gateway, adapter or HMI behavior and no requirement satisfaction.
     */
    attribute receiptSha256 : ScalarValues::String = "cd37335df3f204f67e5d4dd2403e4e790ebed63f5655b1077e9eed69c6fe2ea2";
  }

  dependency configuredIntegrationLayerTrace
    from configuredProduct::integrationLayer
    to DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization::scoreTwoDomainPhysicalSystem::integrationLayer;
  dependency configuredProductGuestImageGap
    from configuredProduct
    to DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization::gapSOMEIPStackOnAAOSGuestUntested;

  comment twoDomainMemberExpressed
    about DE4SDV_MiddlewareSCOREFraming::gapTwoDomainMemberNotExpressible
  /*
   * Phase 9 resolves GAP-MW-032. The SDV platform stack and the SDV feature
   * model have a main side and a guest side on one SoC. The owner decided
   * this on 2026-10-21 and 2026-10-22. The groups guestOperatingSystem and
   * guestMiddleware bind the variations guestOSPlatform and guestMiddleware,
   * and the requires constraints C007 to C010 constrain the guest side. C001
   * reads the main side only. MW-CONFIG-002 expresses the two-domain
   * product. Its main side is Linux with Eclipse S-CORE, and it is also the
   * KVM host. Its guest side is Android with the AAOS SDV middleware.
   * The AAOS-integrated member MW-CONFIG-001 has the same guest side. The
   * VM layout of the guest side is realization content of phase 8, and it
   * differs: one VM in MW-CONFIG-001, two in MW-CONFIG-002 (ADR 0025). The
   * admission of the S-CORE product is not part of this gap. It stays a
   * phase-12 decision.
   */

  comment hmiGuestCandidateCounterpartInPhase12
    about DE4SDV_MiddlewareSCOREFeatureClassification::hmiGuestExecutionDomain,
      DE4SDV_MiddlewareSCOREFeatureClassification::hmiGuestCandidateCounterpartOfAAOSIntegratedMode
  /*
   * CLS-MW-004 after phase 9. The feature model carries the characteristic
   * with the guest side and the optional HMI display: MW-CONFIG-002 selects
   * guestAndroid, guestAndroidSDV and hmiDisplay. The AAOS-integrated member
   * selects the same guest side. So, of this characteristic, only hmiDisplay
   * distinguishes the S-CORE product from it. In phase 9 the counterpart
   * dependency stays on the AAOS-integrated mode. If the owner admits the
   * member, phase 12 re-points it to the new S-CORE Integrated alternative
   * of the integration mode (owner decision of 2026-10-21).
   */

  concern scoreMiddlewareProductLineConfigurationConcern : ProductLineConfigurationConcern {
    doc /*
     * Reviewers need the variant selections of MW-CONFIG-002 in the
     * platform-stack projection that the configurator generates from its
     * receipt. The main side selects Autoware, Eclipse S-CORE and Linux. The
     * hypervisor is KVM. The guest side selects Android with the AAOS SDV
     * middleware. The adapter is the derived Autoware-to-S-CORE adapter. For
     * the S-CORE product, this answers the representation part of the
     * framing's twoDomainMemberRepresentationConcern. This concern is about
     * choices, not assembly.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern scoreMiddlewareProductModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*
     * Reviewers need the assembly of MW-CONFIG-002 with one instance and one
     * owner per platform layer. It holds the platform-stack projection and
     * the realization of the integration layer. The S-CORE services of the
     * layer are the selected middleware, and its adapter is the derived
     * adapter. The SDV Core of the layer is the guest middleware, and its
     * platform software is the guest operating system. The platform stack
     * owns all four. Phase 10 then verifies one product. This concern is
     * about assembled assets, not the variation space.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  alias selectedVehicleApplication
    for MiddlewareAutowareSCOREReference::vehicleApplication;
  alias selectedMiddleware
    for MiddlewareAutowareSCOREReference::middleware;
  alias selectedOperatingSystem
    for MiddlewareAutowareSCOREReference::osPlatform;
  alias selectedHypervisor
    for MiddlewareAutowareSCOREReference::hypervisor;
  alias selectedGuestOperatingSystem
    for MiddlewareAutowareSCOREReference::guestOSPlatform;
  alias selectedGuestMiddleware
    for MiddlewareAutowareSCOREReference::guestMiddleware;
  alias selectedApplicationMiddlewareAdapter
    for MiddlewareAutowareSCOREReference::applicationMiddlewareAdapter;

  view scoreMiddlewareProductLineConfigurationView {
    viewpoint selectedProductLineConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame scoreMiddlewareProductLineConfigurationConcern;
    }
    expose MiddlewareAutowareSCOREReference;
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

  view scoreMiddlewareProductModelAssemblyView {
    viewpoint selectedProductModelAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame scoreMiddlewareProductModelAssemblyConcern;
    }
    doc /*
     * The configured product, its two parts and the four bindings. The
     * S-CORE services, the adapter and the SDV Core of the integration layer
     * are references. The bindings make them the same things as the
     * selected middleware, the derived adapter and the guest middleware of
     * the platform stack, their only owner. A fourth binding makes the
     * platform software of the SDV Core the guest operating system of the
     * stack. The view filters out the phase-8
     * allocations. They target the
     * adapter feature of the realization definition, so every usage of that
     * definition carries them, this product included.
     */
    expose MiddlewareAutowareSCOREConfiguredProduct;
    expose MiddlewareAutowareSCOREConfiguredProduct::platformStack;
    expose MiddlewareAutowareSCOREConfiguredProduct::integrationLayer;
    expose MiddlewareAutowareSCOREConfiguredProduct::scoreServicesBoundToSelectedMiddleware;
    expose MiddlewareAutowareSCOREConfiguredProduct::adapterBoundToDerivedAdapter;
    expose MiddlewareAutowareSCOREConfiguredProduct::sdvCoreBoundToGuestMiddleware;
    expose MiddlewareAutowareSCOREConfiguredProduct::platformSoftwareBoundToGuestOperatingSystem;
    filter not (@ SysML::AllocationUsage);
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
