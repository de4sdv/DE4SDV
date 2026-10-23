/*
 * DE4SDV middleware variability and configuration model slice for the
 * Eclipse S-CORE realization.
 *
 * INC-MW-011, phase 9: the configured product of the Eclipse S-CORE
 * reference configuration, with the configuration identity MW-CONFIG-002.
 * It pairs the platform-stack projection that the configurator generates
 * from the receipt of the feature configuration
 * middleware_autoware_score_reference.sysml with the realization of the
 * middleware integration layer from phase 8, as INC-MW-009 pairs the
 * projection of its member with the middleware boundary. The feature
 * configuration and the generated projection own the variant selections.
 * This package does not restate them.
 *
 * The configuration is valid and not admitted. Eclipse S-CORE is a
 * reference-only alternative of the governed product-line scope, and the
 * HMI display is not in that scope (ADR 0014). So the configured product
 * specializes no member-product type. The member decision is phase-12 work,
 * after the runnable proof of phase 10 (owner decision of 2026-10-21). This
 * slice is configuration evidence only: it proves no runtime behavior,
 * satisfies no requirement and makes no safety, cybersecurity or compliance
 * claim.
 */

package DE4SDV_MiddlewareSCOREVariabilityConfiguration {
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization::SCOREMiddlewareIntegrationLayerRealization;
  private import Views::*;

  part def MiddlewareAutowareSCOREConfiguredProduct {
    doc /*
     * The configured product of the Eclipse S-CORE reference configuration:
     * the generated platform-stack projection and the realization of the
     * middleware integration layer, the system of interest of INC-MW-011.
     * The local parts compose the projection and the phase-8 realization.
     * They choose no variant. The context parts of phase 8, such as the
     * Autoware-based AEBS stack, the vehicle-speed provider and the HMI
     * application in the guest, stay in the physical context
     * SCORETwoDomainPhysicalSystem.
     *
     * One instance per layer. The platform stack composes the selected
     * Eclipse S-CORE middleware and the derived Autoware-to-S-CORE adapter.
     * In this product the integration layer refers to these two parts: one
     * binding makes its S-CORE services the selected middleware, and one
     * binding makes its adapter the derived adapter. Its other parts are no
     * platform layers. The guest side is the guest operating system and the
     * guest middleware of the platform stack. So the product composes no
     * second Android or AAOS SDV instance. For the same reason it does not
     * compose SCORETwoDomainPhysicalSystem.
     *
     * No shared asset implements the HMI display, so no feature binding
     * resolves the hmiDisplay selection. The projection lists it among the
     * selections that SysML does not resolve.
     *
     * The definition specializes no member-product type, because the
     * configuration is not admitted. If the owner admits the member in phase
     * 12, it specializes the new member definition, as the AAOS-integrated
     * configured member specializes its member decision.
     */
    part platformStack : MiddlewareAutowareSCOREReference;
    part integrationLayer : SCOREMiddlewareIntegrationLayerRealization {
      ref part :>> scoreServices;
      ref part :>> adapter;
    }
    binding scoreServicesBoundToSelectedMiddleware
      bind integrationLayer.scoreServices = platformStack.middleware;
    binding adapterBoundToDerivedAdapter
      bind integrationLayer.adapter = platformStack.applicationMiddlewareAdapter;
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
     * autowareToSCORE, and not admitted. A new receipt needs a new binding
     * here.
     *
     * The guest side runs the display-capable sdv_ivi_cf guest of
     * INC-AEBS-010 (ASM-MW-027), not the headless sdv_core_cf guest of the
     * MW-CONFIG-001 evidence. For the SOME/IP receiver, that guest needs a
     * rebuild with vsomeip (GAP-MW-038).
     *
     * Configuration evidence only. This usage proves no provider, transport,
     * gateway, adapter or HMI behavior and no requirement satisfaction.
     */
    attribute receiptSha256 : ScalarValues::String = "c5df6d3135b652c85dab97b0464b9292b3767c522bf0af7bdce57c2e77cbaed7";
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
   * model have a main side and a guest side on one SoC (owner decisions of
   * 2026-10-21 and 2026-10-22). The groups guestOperatingSystem and
   * guestMiddleware bind the variations guestOSPlatform and guestMiddleware,
   * and the requires constraints C007 to C010 constrain the guest side. C001
   * reads the main side only. MW-CONFIG-002 expresses the two-domain
   * product: Linux with Eclipse S-CORE on the main side, which is also the
   * KVM host, and Android with the AAOS SDV middleware on the guest side.
   * The AAOS-integrated member MW-CONFIG-001 has the same guest side. The
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
     * receipt: Autoware, Eclipse S-CORE and Linux on the main side, KVM,
     * Android with the AAOS SDV middleware on the guest side, and the
     * derived Autoware-to-S-CORE adapter. For the S-CORE product, this
     * answers the twoDomainMemberRepresentationConcern of the framing. This
     * concern is about choices, not assembly.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern scoreMiddlewareProductModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*
     * Reviewers need the assembly of MW-CONFIG-002 with one instance per
     * platform layer: the platform-stack projection and the realization of
     * the integration layer, whose S-CORE services are the selected
     * middleware and whose adapter is the derived adapter. Phase 10 then
     * verifies one product. This concern is about assembled assets, not the
     * variation space.
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
    expose MiddlewareAutowareSCOREConfiguredProduct;
    expose MiddlewareAutowareSCOREConfiguredProduct::platformStack;
    expose MiddlewareAutowareSCOREConfiguredProduct::integrationLayer;
    expose MiddlewareAutowareSCOREConfiguredProduct::integrationLayer::scoreServices;
    expose MiddlewareAutowareSCOREConfiguredProduct::integrationLayer::adapter;
    expose MiddlewareAutowareSCOREConfiguredProduct::scoreServicesBoundToSelectedMiddleware;
    expose MiddlewareAutowareSCOREConfiguredProduct::adapterBoundToDerivedAdapter;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
