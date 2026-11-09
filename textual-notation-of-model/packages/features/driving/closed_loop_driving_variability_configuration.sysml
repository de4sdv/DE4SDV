/*
 * DE4SDV closed-loop driving variability and configuration model slice.
 *
 * INC-DRIVING-001, phase 9: the configured product of the closed-loop
 * driving reference configuration, with the configuration identity
 * DRIVING-CONFIG-001. It pairs two parts. The first is the platform-stack
 * projection that the configurator generates from the receipt of the
 * feature configuration closed_loop_driving_autoe2e_score_reference.sysml.
 * The second is the realization of the driving system from phase 8, the
 * system of interest of the increment. INC-MW-011 pairs the projection of
 * its configuration with the realization of its integration layer in the
 * same way. The feature configuration and the generated projection own the
 * variant selections. No element of this package restates them. Its docs
 * name some of them, and a guard test keeps those names equal to the
 * receipt.
 *
 * Phase 9 added the feature autoE2E to the feature model, with the camera
 * required (C012, owner decision of 2026-11-02), Linux required (C013) and
 * the pairs with androidSDV, autosarAdaptive and noMiddleware excluded, and
 * one derivation rule that derives the adapter autoE2EToSCORE for the pair
 * with Eclipse S-CORE (owner decisions of 2026-11-06). This package links
 * the system of interest to that feature and to the two shared-asset
 * variants, as phase 5 promised.
 *
 * The configuration is valid and not admitted. The receipt gives three
 * reasons. First, the selections autoE2E, eclipseSCORE and hmiDisplay are
 * content the governed scope does not admit: the driving stack is deferred
 * variability, Eclipse S-CORE is reference-only, and the HMI display has no
 * element in the governed scope. Second, the guest side realizes the
 * AAOS-integrated alternative without its middleware androidSDV. Third, the
 * configuration does not represent the common content: no Autoware, no
 * LiDAR. So the configured product specializes no member-product type. ADR
 * 0014 bounds the existing product line; the member decision follows the
 * runnable proof of phase 10 (framing gap gapProductLineAdmission). This
 * slice is configuration evidence only: it proves no runtime behavior,
 * satisfies no requirement and makes no safety, cybersecurity or
 * compliance claim.
 */

package DE4SDV_ClosedLoopDrivingVariabilityConfiguration {
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::ClosedLoopDrivingSoftwareRealization;
  private import DE4SDV_ProductLine::ProductLineConfiguredProduct;
  private import Views::*;

  part def ClosedLoopDrivingAutoE2ESCOREConfiguredProduct :> ProductLineConfiguredProduct {
    doc /*
     * The configured product of the closed-loop driving reference
     * configuration. It holds the generated platform-stack projection and
     * the realization of the driving system, the system of interest of
     * INC-DRIVING-001. The local parts compose the projection and the
     * phase-8 realization. They choose no variant. The context parts of
     * phase 8 stay in the physical context ClosedLoopDrivingPhysicalSystem:
     * the Linux host with its operating system and hypervisor, the SDV Core
     * guest, the IVI guest with the observer, the simulation server with
     * its sensor rig and the navigation. For the same reason as INC-MW-011,
     * this product does not compose that context. The guide of the
     * increment and a test keep the host and guest layers of the context
     * typed by the definitions of the selected variants: Linux, KVM, Android
     * and the AAOS SDV middleware.
     *
     * One binding. The realization composes the S-CORE services it uses,
     * one instance on the host, because phase 8 put the two gateway
     * processes of those services on the observation path of the driving
     * system. The binding makes those services the same thing as the
     * selected middleware of the platform stack. So, unlike INC-MW-011,
     * where the integration layer only refers to its S-CORE services and the
     * platform stack is their only owner, this product has two composers of
     * one middleware instance: the realization by the phase-8 decision, the
     * platform stack by the projection. The product states it rather than
     * hides it.
     *
     * No second binding. The derived adapter of the platform stack is the
     * mw::com binding code of the three programs of the realization, no
     * program of its own, so no part of the realization is the adapter. A
     * dependency records which parts carry it. The driving agent runs the
     * pinned checkpoint of the selected vehicle application in its own
     * process (phase 8's engine decision of 2026-11-08); a dependency records
     * that too, because the application layer of the stack is the whole
     * AutoE2E stack, and the agent is the program DE4SDV writes around it.
     *
     * No shared asset implements the HMI display, so no feature binding
     * resolves the hmiDisplay selection. The projection lists it among the
     * selections that SysML does not resolve. The observer application of
     * the IVI guest is the display of this product, context content of
     * phase 8. No requirement of the increment names the display: the
     * publication requirements hold without it, so this package adds no
     * requirement dependency on hmiDisplay, where INC-MW-011 added four.
     *
     * The definition specializes no member-product type, because the
     * configuration is not admitted. If the owner admits the member after
     * phase 10, it specializes the new member definition. This definition
     * specializes the kernel's ProductLineConfiguredProduct, the configured
     * product of phase 9 (owner decision of 2026-10-29).
     */
    part platformStack : ClosedLoopDrivingAutoE2ESCOREReference;
    part drivingSoftware : ClosedLoopDrivingSoftwareRealization;
    binding scoreServicesBoundToSelectedMiddleware
      bind drivingSoftware.scoreServices = platformStack.middleware;
  }

  part <'DRIVING-CONFIG-001'> configuredProduct : ClosedLoopDrivingAutoE2ESCOREConfiguredProduct {
    doc /*
     * DRIVING-CONFIG-001: the configuration identity that the phase-10
     * evidence binds, as the INC-MW-011 evidence binds MW-CONFIG-002. The
     * identity is bound to the exact receipt that the configurator generated
     * the platform-stack projection from. receiptSha256 is the SHA-256 of
     * model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json.
     * That receipt records the evaluation of the feature configuration
     * closedLoopDrivingAutoE2ESCOREReference: valid, with the derived
     * adapter autoE2EToSCORE, and not admitted. A receipt re-cut keeps this
     * identity and rebinds receiptSha256 here. The pull request that rebinds
     * it states whether the configuration's own receipt record changed.
     * Evidence that binds DRIVING-CONFIG-001 also records the receipt
     * SHA-256 it ran against.
     *
     * The bench of phase 8: the Linux host runs the three programs under
     * the Launch Manager of S-CORE Lifecycle and the SOME/IP gateway; the
     * guest side holds two VMs, the headless SDV Core VM and the
     * display-capable IVI VM with the observer; the CARLA server with its
     * simulated sensor rig and the navigation are the simulated vehicle
     * and its context. The pins of the programs, the images and the
     * simulator are phase-10 content.
     *
     * Configuration evidence only. This usage proves no agent, adapter,
     * publisher, gateway or observer behavior and no requirement
     * satisfaction.
     */
    attribute receiptSha256 : ScalarValues::String = "b5fe031941baa6f43d7b8ab2c48b5d0bee992c2afe53d1cb4d1f21fc56bdcae1";
  }

  dependency configuredDrivingSoftwareTrace
    from configuredProduct::drivingSoftware
    to DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::closedLoopDrivingPhysicalSystem::linuxHost::drivingSoftware;
  dependency derivedAdapterIsTheProgramsBindingCode
    from configuredProduct::drivingSoftware::drivingAgent,
      configuredProduct::drivingSoftware::actuationAdapter,
      configuredProduct::drivingSoftware::statePublisherApplication
    to configuredProduct::platformStack::applicationMiddlewareAdapter;
  dependency drivingAgentRunsTheSelectedApplication
    from configuredProduct::drivingSoftware::drivingAgent
    to configuredProduct::platformStack::vehicleApplication;
  dependency configuredProductAdmissionGap
    from configuredProduct
    to DE4SDV_ClosedLoopDrivingFraming::gapProductLineAdmission;

  dependency drivingSystemOnAutoE2EFeature
    from ClosedLoopDrivingSoftwareRealization
    to DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::autoE2E;
  dependency drivingSystemOnAutoE2EStackVariant
    from ClosedLoopDrivingSoftwareRealization
    to DE4SDV_SDVPlatformStack::AutoE2EStack;
  dependency drivingSystemOnAutoE2EToSCOREAdapter
    from ClosedLoopDrivingSoftwareRealization
    to DE4SDV_SDVPlatformStack::AutoE2EToSCOREAdapter;

  comment drivingMemberCandidateExpressed
    about configuredProduct,
      DE4SDV_ClosedLoopDrivingCapabilityClassification::autoE2EDrivingStack
  /*
   * Phase 3 recorded the closed-loop driving capability as a feature
   * candidate, autoE2EDrivingStack, because it distinguishes member
   * products. Phase 9 turned it into the feature autoE2E of the vehicle
   * application group, so the feature model now states what shared assets
   * derive for it: one adapter, for the pair with Eclipse S-CORE, and no
   * adapter for the other three middlewares. The exclusions say only that;
   * a later member may pair AutoE2E with another middleware once an adapter
   * and its derivation rule exist. DRIVING-CONFIG-001 expresses the
   * two-domain product of INC-MW-011 with AutoE2E in place of Autoware on
   * the main side and the same guest side. Its admission is not part of
   * this phase. It stays a decision after phase 10.
   */

  concern drivingProductLineConfigurationConcern : ProductLineConfigurationConcern {
    doc /*
     * Product-line engineers, system architects and open-source reviewers
     * need the variant selections of DRIVING-CONFIG-001 in the platform-stack
     * projection that the configurator generates from its receipt. The main
     * side selects AutoE2E, Eclipse S-CORE and Linux. The hypervisor is KVM.
     * The guest side selects Android with the AAOS SDV middleware. The
     * adapter is the derived AutoE2E-to-S-CORE adapter. This concern is
     * about choices, not assembly.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern drivingProductModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*
     * System architects, verification engineers and open-source reviewers
     * need the assembly of DRIVING-CONFIG-001: the platform-stack projection
     * and the realization of the driving system, and the one binding that
     * makes the S-CORE services of the realization the selected middleware.
     * The derived adapter is the binding code of the three programs, and
     * the driving agent runs the selected application; both are
     * dependencies, not parts. Phase 10 then verifies one product. This
     * concern is about assembled assets, not the variation space.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  alias selectedVehicleApplication
    for ClosedLoopDrivingAutoE2ESCOREReference::vehicleApplication;
  alias selectedMiddleware
    for ClosedLoopDrivingAutoE2ESCOREReference::middleware;
  alias selectedOperatingSystem
    for ClosedLoopDrivingAutoE2ESCOREReference::osPlatform;
  alias selectedHypervisor
    for ClosedLoopDrivingAutoE2ESCOREReference::hypervisor;
  alias selectedGuestOperatingSystem
    for ClosedLoopDrivingAutoE2ESCOREReference::guestOSPlatform;
  alias selectedGuestMiddleware
    for ClosedLoopDrivingAutoE2ESCOREReference::guestMiddleware;
  alias selectedApplicationMiddlewareAdapter
    for ClosedLoopDrivingAutoE2ESCOREReference::applicationMiddlewareAdapter;

  view closedLoopDrivingProductLineConfigurationView {
    viewpoint selectedProductLineConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame drivingProductLineConfigurationConcern;
    }
    doc /*
     * The generated projection and its seven selected layers: the six
     * selections of the configuration and the derived adapter.
     */
    expose ClosedLoopDrivingAutoE2ESCOREReference;
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

  view closedLoopDrivingProductModelAssemblyView {
    viewpoint selectedProductModelAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame drivingProductModelAssemblyConcern;
    }
    doc /*
     * The configured product, its two parts and the one binding. The
     * S-CORE services of the realization are composed, not referred to,
     * so the binding makes two composers hold one instance; the product
     * doc says why. The view filters out the phase-8 allocations, which
     * target the usages of the physical context, not this product.
     */
    expose ClosedLoopDrivingAutoE2ESCOREConfiguredProduct;
    expose ClosedLoopDrivingAutoE2ESCOREConfiguredProduct::platformStack;
    expose ClosedLoopDrivingAutoE2ESCOREConfiguredProduct::drivingSoftware;
    expose ClosedLoopDrivingAutoE2ESCOREConfiguredProduct::scoreServicesBoundToSelectedMiddleware;
    filter not (@ SysML::AllocationUsage);
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
