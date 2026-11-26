/*
 * DE4SDV HMI display variability and configuration model slice.
 *
 * INC-HMI-001, phase 9: the configured product of the HMI display, with the
 * configuration identity HMI-CONFIG-001. It pairs two parts. The first is
 * the platform-stack projection that the configurator generates from the
 * receipt of the feature configuration
 * driver_assistance_visionpilot_score_reference.sysml. The second is the
 * physical realization of the HMI display from phase 8, the system of
 * interest of the increment. Phase 3 records that the display belongs to
 * the VisionPilot configuration, so this phase adds no feature
 * configuration and changes no feature, no shared asset, no receipt and no
 * projection: the configured product types its platform stack by the
 * projection of that configuration, DriverAssistanceVisionPilotSCOREReference.
 * The same configuration configures the configured product of the
 * driver-assistance increment, DRIVING-CONFIG-002; by the kernel, a
 * configuration can configure more than one configured product. The feature
 * configuration and the generated projection own the variant selections. No
 * element of this package restates them. Its docs name some of them, and a
 * guard test keeps those names equal to the receipt.
 *
 * The links of rule 5 are declared with their clients, in the rule's
 * dependency form. This package holds none of them.
 *
 * The receipt records the configuration as valid, and the governed scope
 * does not admit it; the phase 9 package of the driver-assistance increment
 * states why. So the configured product specializes no member-product type.
 * This slice is configuration evidence only: it proves no runtime behavior
 * and satisfies no requirement.
 */

package DE4SDV_HmiDisplayVariabilityConfiguration {
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_HmiDisplayPhysicalSoftwareRealization::HmiDisplayPhysicalSystem;
  private import DE4SDV_ProductLine::ProductLineConfiguredProduct;
  private import Views::*;

  part def HmiDisplayVisionPilotSCOREConfiguredProduct :> ProductLineConfiguredProduct {
    doc /*
     * The configured product of the HMI display in the VisionPilot
     * configuration. It holds the generated platform-stack projection and the
     * physical realization of the HMI display, the system of interest of
     * INC-HMI-001: the central computer with the SDV Core, IVI and SDV Media
     * VMs. The local parts compose the projection and the phase-8
     * realization. They choose no variant.
     *
     * Two bindings. The central computer of phase 8 refers to its own
     * platform and to its hypervisor, and the platform stack owns them: one
     * binding makes the platform the same thing as the selected operating
     * system, Linux, and one makes the hypervisor the same thing as the
     * selected hypervisor, KVM. KVM runs in the kernel of the main-side
     * operating system, so the platform of the central computer is the main
     * side. The SDV Media VM refers to an operating system that no source
     * that DE4SDV keeps names, and the platform stack has no layer for a VM
     * of the guest (ADR 0025), so this product leaves that reference unbound.
     *
     * The guest side departs from one instance and one owner per layer. The
     * platform stack models the guest side as one guest operating system and
     * one guest middleware for one or more VMs, while the realization owns
     * Android in the SDV Core VM and in the IVI VM, and the AAOS SDV
     * middleware in the SDV Core VM. Those parts stay owned and unbound, so
     * the platform stack is not the only owner of the guest operating system
     * and the guest middleware in this product. A test keeps them typed by the
     * definitions of the variants that the projection selects: Android and the
     * AAOS SDV middleware.
     *
     * No shared asset implements the HMI display, so no feature binding
     * resolves the hmiDisplay selection. The projection lists it among the
     * selections that SysML does not resolve. The configuration also selects
     * adaptive cruise control and lane-keep assist, which this increment does
     * not judge (phase 3): they come with the configuration, the projection
     * lists them too, and this increment claims nothing of them.
     *
     * The definition specializes no member-product type, because the
     * governed scope does not admit the configuration. It specializes the
     * kernel's ProductLineConfiguredProduct, the configured product of phase
     * 9.
     */
    part platformStack : DriverAssistanceVisionPilotSCOREReference;
    part displayRealization : HmiDisplayPhysicalSystem;
    binding centralComputerOSBoundToSelectedOperatingSystem
      bind displayRealization.centralComputer.os = platformStack.osPlatform;
    binding centralComputerHypervisorBoundToSelectedHypervisor
      bind displayRealization.centralComputer.hypervisor = platformStack.hypervisor;
  }

  part <'HMI-CONFIG-001'> configuredProduct : HmiDisplayVisionPilotSCOREConfiguredProduct {
    doc /*
     * HMI-CONFIG-001: the configuration identity that the phase-10 evidence
     * binds, as the evidence of the driver-assistance increment binds
     * DRIVING-CONFIG-002. The identity is bound to the exact receipt that the
     * configurator generated the platform-stack projection from.
     * receiptSha256 is the SHA-256 of
     * model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json,
     * the receipt that records the evaluation of the feature configuration
     * driverAssistanceVisionPilotSCOREReference. A receipt re-cut keeps this
     * identity and rebinds receiptSha256 here. The pull request that rebinds
     * it states whether the configuration's own receipt record changed.
     * By the decision of 2026-11-17 that the identity of DRIVING-CONFIG-001
     * records, the record has not changed when its only difference is added
     * states omitted for features that it does not select, and every other
     * entry is the same: validity, reasons, derived variants with their
     * variant ids, admission, the selected features, projection name, source,
     * description and element id. Evidence that binds HMI-CONFIG-001 also
     * records the receipt SHA-256 it ran against.
     *
     * The product inherits three open gaps of phase 8: the renderer's
     * judging of the scene by the term current (GAP-HMI-001), the tolerance
     * of a drawn position (GAP-HMI-003), and the elements that the display
     * identity does not name (GAP-HMI-004). On the bench, the guest host of
     * INC-DRIVING-001 stands in for the central computer, with the SDV Media
     * VM as a third guest, and the simulator stands in for the ECU that
     * measures the vehicle speed and for the vehicle network; the feed of
     * that speed (GAP-HMI-002) is a gap of the bench, not of this product.
     *
     * Configuration evidence only. This usage proves no renderer, app,
     * composition or platform behavior and no requirement satisfaction.
     */
    attribute receiptSha256 : ScalarValues::String = "0447e4a561240dcdc0cc1860eb9a707e0cc5ca965af40c9a6c26b9534458c4db";
  }

  dependency configuredDisplayRealizationTrace
    from configuredProduct::displayRealization
    to DE4SDV_HmiDisplayPhysicalSoftwareRealization::hmiDisplayPhysicalSystem;
  dependency configuredProductSceneCurrencyGap
    from configuredProduct
    to DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiRendererJudgesSceneCurrency;
  dependency configuredProductDrawingToleranceGap
    from configuredProduct
    to DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiDrawingToleranceUnset;
  dependency configuredProductDisplayIdentityGap
    from configuredProduct
    to DE4SDV_HmiDisplayPhysicalSoftwareRealization::gapHmiIdentityMissesPhase8Elements;

  concern hmiDisplayProductLineConfigurationConcern : ProductLineConfigurationConcern {
    doc /*
     * Product-line engineers, system architects and open-source reviewers
     * need the variant selections of HMI-CONFIG-001 in the platform-stack
     * projection that the configurator generates from its receipt, the
     * projection of the VisionPilot configuration. The main side selects
     * VisionPilot, Eclipse S-CORE and Linux. The hypervisor is KVM. The guest
     * side selects Android with the AAOS SDV middleware. The adapter is the
     * derived VisionPilot-to-S-CORE adapter. This concern is about choices,
     * not assembly.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern hmiDisplayProductModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*
     * System architects, verification engineers and open-source reviewers
     * need the assembly of HMI-CONFIG-001: the platform-stack projection and
     * the realization of the HMI display, with the two bindings that make
     * the platform and the hypervisor of the central computer the selected
     * operating system and the selected hypervisor, and the guest layers that
     * the VMs of the realization own. Phase 10 then verifies one product.
     * This concern is about assembled assets, not the variation space.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  alias selectedVehicleApplication
    for DriverAssistanceVisionPilotSCOREReference::vehicleApplication;
  alias selectedMiddleware
    for DriverAssistanceVisionPilotSCOREReference::middleware;
  alias selectedOperatingSystem
    for DriverAssistanceVisionPilotSCOREReference::osPlatform;
  alias selectedHypervisor
    for DriverAssistanceVisionPilotSCOREReference::hypervisor;
  alias selectedGuestOperatingSystem
    for DriverAssistanceVisionPilotSCOREReference::guestOSPlatform;
  alias selectedGuestMiddleware
    for DriverAssistanceVisionPilotSCOREReference::guestMiddleware;
  alias selectedApplicationMiddlewareAdapter
    for DriverAssistanceVisionPilotSCOREReference::applicationMiddlewareAdapter;

  view hmiDisplayProductLineConfigurationView {
    viewpoint selectedProductLineConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame hmiDisplayProductLineConfigurationConcern;
    }
    doc /*
     * The generated projection of the VisionPilot configuration and its seven
     * selected layers: six that the configuration selects, and the derived
     * adapter.
     */
    expose DriverAssistanceVisionPilotSCOREReference;
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

  view hmiDisplayProductModelAssemblyView {
    viewpoint selectedProductModelAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame hmiDisplayProductModelAssemblyConcern;
    }
    doc /*
     * The configured product: its definition with the two parts and the two
     * bindings, and the usage HMI-CONFIG-001 that the phase-10 evidence
     * binds. The view filters out the phase-8 allocations, which target the
     * usage of the realization in phase 8, not this product.
     */
    expose HmiDisplayVisionPilotSCOREConfiguredProduct;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::platformStack;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::displayRealization;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::centralComputerOSBoundToSelectedOperatingSystem;
    expose HmiDisplayVisionPilotSCOREConfiguredProduct::centralComputerHypervisorBoundToSelectedHypervisor;
    expose configuredProduct;
    filter not (@ SysML::AllocationUsage);
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
