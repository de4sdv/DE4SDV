/*
 * DE4SDV driver-assistance variability and configuration model slice.
 *
 * INC-DRIVING-002, phase 9: the configured product of the driver-assistance
 * reference configuration, with the configuration identity
 * DRIVING-CONFIG-002. It pairs two parts. The first is the platform-stack
 * projection that the configurator generates from the receipt of the
 * feature configuration driver_assistance_visionpilot_score_reference.sysml.
 * The second is the realization of the driver-assistance system from phase
 * 8, the system of interest of the increment. INC-DRIVING-001 and
 * INC-MW-011 pair the projections of their configurations with their
 * realizations in the same way. The feature configuration and the generated
 * projection own the variant selections. No element of this package
 * restates them. Its docs name some of them, and a guard test keeps those
 * names equal to the receipt.
 *
 * Phase 9 added the feature visionPilot to the feature model, from the
 * phase 3 candidate of 2026-11-14: the camera required (C014), Linux
 * required (C015), the pairs with androidSDV, autosarAdaptive and
 * noMiddleware excluded, and one derivation rule that derives the adapter
 * visionPilotToSCORE for the pair with Eclipse S-CORE, in the form that
 * INC-DRIVING-001 took for AutoE2E on 2026-11-06. The links of rule 5 are
 * declared with their clients, in the rule's dependency form: the framing
 * links the system of interest to the feature visionPilot, and the
 * requirements package links each requirement that names the Eclipse
 * S-CORE path to the feature eclipseSCORE and each requirement that names
 * the warning request, which asks the AAOS SDV for the warning, to the
 * feature guestAndroidSDV. This package holds none of them.
 *
 * The configuration is valid and not admitted. It realizes the alternative
 * S-CORE Integrated with its derived realizations. The model's reading of
 * the correspondences gives two reasons, and the receipt of the privileged
 * PLE authority run records the verdict. First, the selections visionPilot,
 * adaptiveCruiseControl and laneKeepAssist are content the governed scope
 * does not admit: the driving stack is deferred variability, and adaptive
 * cruise control and lane-keep assist have no element in the governed
 * scope. Second, the configuration does not represent the common content:
 * no Autoware, no LiDAR. So the configured product specializes no
 * member-product type. ADR 0014 bounds the existing product line; the
 * member decision follows the runnable proof of phase 10 (framing gap
 * gapCandidateAdmission). This slice is configuration evidence only: it
 * proves no runtime behavior and satisfies no requirement.
 */

package DE4SDV_DriverAssistanceVariabilityConfiguration {
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_DriverAssistancePhysicalSoftwareRealization::DriverAssistanceSoftwareRealization;
  private import DE4SDV_ProductLine::ProductLineConfiguredProduct;
  private import Views::*;

  part def DriverAssistanceVisionPilotSCOREConfiguredProduct :> ProductLineConfiguredProduct {
    doc /*
     * The configured product of the driver-assistance reference
     * configuration. It holds the generated platform-stack projection and
     * the realization of the driver-assistance system, the system of
     * interest of INC-DRIVING-002. The local parts compose the projection
     * and the phase-8 realization. They choose no variant. The context parts
     * of phase 8 stay in the physical context DriverAssistancePhysicalSystem:
     * the S-CORE host with its Linux, the S-CORE services and the actuation
     * adapter, the simulator host, the guest host with KVM, and the SDV Core
     * and IVI guests. As in INC-DRIVING-001 and INC-MW-011, this product does
     * not compose that context. The guide of the increment and a test keep
     * the host and guest layers of the context typed by the definitions of
     * the selected variants: Linux, Eclipse S-CORE, KVM, Android and the
     * AAOS SDV middleware.
     *
     * No binding. Phase 8 kept the Eclipse S-CORE path outside the boundary
     * of phase 0, so the S-CORE services sit on the S-CORE host beside the
     * realization, not in it. No part of the realization is the selected
     * middleware, and the platform stack is the only composer of it in this
     * product, unlike INC-DRIVING-001, whose realization composes its S-CORE
     * services. The derived adapter of the platform stack is the DE4SDV
     * S-CORE interface module of the candidate's process: its camera
     * interface, its vehicle interface and its warning request publisher,
     * three modules of one process and no program of their own, so no part
     * of the realization is the adapter either. A dependency records which
     * parts carry it. The perception and fusion module and the planner
     * module run the selected vehicle application, VisionPilot at its pinned
     * revision; a dependency records that too, because the application layer
     * of the stack is the whole VisionPilot application.
     *
     * No shared asset implements the HMI display, so no feature binding
     * resolves the hmiDisplay selection. The projection lists it among the
     * selections that SysML does not resolve. The collision warning
     * presentation of the IVI guest is the display of this product, context
     * content of phase 8. No requirement of the increment names the display:
     * the warning requirements name the warning request, so this package
     * adds no requirement dependency on hmiDisplay.
     * Adaptive cruise control and lane-keep assist have no shared asset
     * either, and the projection lists them too. VisionPilot runs a
     * speed-following and a lane-keeping function, which no case of
     * INC-DRIVING-002 judges and no requirement of the increment names, so
     * no requirement depends on those two features.
     *
     * The definition specializes no member-product type, because the
     * configuration is not admitted. If the member decision after phase 10
     * admits the member, it specializes the new member definition. This
     * definition specializes the kernel's ProductLineConfiguredProduct, the
     * configured product of phase 9.
     */
    part platformStack : DriverAssistanceVisionPilotSCOREReference;
    part assistanceSoftware : DriverAssistanceSoftwareRealization;
  }

  part <'DRIVING-CONFIG-002'> configuredProduct : DriverAssistanceVisionPilotSCOREConfiguredProduct {
    doc /*
     * DRIVING-CONFIG-002: the configuration identity that the phase-10
     * evidence binds, as the evidence of INC-DRIVING-001 binds
     * DRIVING-CONFIG-001. The identity is bound to the exact receipt that the
     * configurator generates the platform-stack projection from.
     * receiptSha256 is the SHA-256 of
     * model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json,
     * the receipt that records the evaluation of the feature configuration
     * driverAssistanceVisionPilotSCOREReference. A receipt re-cut keeps this
     * identity and rebinds receiptSha256 here. The pull request that rebinds
     * it states whether the configuration's own receipt record changed.
     * By the decision of 2026-11-17, the record has not changed when its
     * only difference is added states omitted for features that it does
     * not select, and every other entry is the same: validity, reasons,
     * derived variants with their variant ids, admission, the selected
     * features, projection name, source, description and element id.
     * Evidence that binds DRIVING-CONFIG-002 also records the receipt
     * SHA-256 it ran against.
     *
     * The bench of phase 8: the S-CORE host runs the candidate's process and
     * the identity recording application under the Launch Manager of S-CORE
     * Lifecycle, with the actuation adapter and the S-CORE gateways; the
     * guest host holds two VMs, the SDV Core VM and the display-capable IVI
     * VM with the collision warning presentation; the simulator host runs
     * CARLA with the front camera. The pins of the programs, the images and
     * the simulator are phase-10 content.
     *
     * Configuration evidence only. This usage proves no candidate, adapter,
     * gateway or presentation behavior and no requirement satisfaction.
     */
    attribute receiptSha256 : ScalarValues::String = "0447e4a561240dcdc0cc1860eb9a707e0cc5ca965af40c9a6c26b9534458c4db";
  }

  dependency configuredAssistanceSoftwareTrace
    from configuredProduct::assistanceSoftware
    to DE4SDV_DriverAssistancePhysicalSoftwareRealization::driverAssistancePhysicalSystem::scoreHost::assistanceSoftware;
  dependency derivedAdapterIsTheInterfaceModule
    from configuredProduct::assistanceSoftware::visionPilotApplication::cameraInterface,
      configuredProduct::assistanceSoftware::visionPilotApplication::vehicleInterface,
      configuredProduct::assistanceSoftware::visionPilotApplication::warningRequestPublisher
    to configuredProduct::platformStack::applicationMiddlewareAdapter;
  dependency candidateProcessRunsTheSelectedApplication
    from configuredProduct::assistanceSoftware::visionPilotApplication::perceptionAndFusion,
      configuredProduct::assistanceSoftware::visionPilotApplication::safetyGuardianPlanner
    to configuredProduct::platformStack::vehicleApplication;
  dependency configuredProductAdmissionGap
    from configuredProduct
    to DE4SDV_DriverAssistanceFraming::gapCandidateAdmission;

  comment visionPilotCandidateExpressed
    about configuredProduct,
      DE4SDV_DriverAssistanceCapabilityClassification::visionPilotDrivingStack
  /*
   * Phase 3 recorded VisionPilot as the vehicle application as a feature
   * candidate, visionPilotDrivingStack, because it distinguishes member
   * products. Phase 9 turned it into the feature visionPilot of the vehicle
   * application group, so the feature model now states what shared assets
   * derive for it: one adapter, for the pair with Eclipse S-CORE, and no
   * adapter for the other three middlewares. The exclusions say only that;
   * a later member may pair VisionPilot with another middleware once an
   * adapter and its derivation rule exist. DRIVING-CONFIG-002 expresses the
   * two-domain product of INC-MW-011 and INC-DRIVING-001 with VisionPilot on
   * the main side and the same guest side. Its admission is not part of this
   * phase. It stays a decision after phase 10.
   */

  concern assistanceProductLineConfigurationConcern : ProductLineConfigurationConcern {
    doc /*
     * Product-line engineers, system architects and open-source reviewers
     * need the variant selections of DRIVING-CONFIG-002 in the platform-stack
     * projection that the configurator generates from its receipt. The main
     * side selects VisionPilot, Eclipse S-CORE and Linux. The hypervisor is
     * KVM. The guest side selects Android with the AAOS SDV middleware. The
     * adapter is the derived VisionPilot-to-S-CORE adapter. This concern is
     * about choices, not assembly.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern assistanceProductModelAssemblyConcern : ProductModelAssemblyConcern {
    doc /*
     * System architects, verification engineers and open-source reviewers
     * need the assembly of DRIVING-CONFIG-002: the platform-stack projection
     * and the realization of the driver-assistance system, with no binding,
     * because the realization composes no platform layer. The derived
     * adapter is the S-CORE interface module of the candidate's process, and
     * its perception and planner modules run the selected application; both
     * are dependencies, not parts. Phase 10 then verifies one product. This
     * concern is about assembled assets, not the variation space.
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

  view driverAssistanceProductLineConfigurationView {
    viewpoint selectedProductLineConfigurationViewpoint : ProductLineConfigurationViewpoint {
      frame assistanceProductLineConfigurationConcern;
    }
    doc /*
     * The generated projection and its seven selected layers: the six
     * selections of the configuration and the derived adapter.
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

  view driverAssistanceProductModelAssemblyView {
    viewpoint selectedProductModelAssemblyViewpoint : ProductModelAssemblyViewpoint {
      frame assistanceProductModelAssemblyConcern;
    }
    doc /*
     * The configured product: its definition with the two parts and no
     * binding, because the realization composes no platform layer, and the
     * usage DRIVING-CONFIG-002 that the phase-10 evidence binds. The view
     * filters out the phase-8 allocations, which target the usages of the
     * physical context, not this product.
     */
    expose DriverAssistanceVisionPilotSCOREConfiguredProduct;
    expose DriverAssistanceVisionPilotSCOREConfiguredProduct::platformStack;
    expose DriverAssistanceVisionPilotSCOREConfiguredProduct::assistanceSoftware;
    expose configuredProduct;
    filter not (@ SysML::AllocationUsage);
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
    render asTreeDiagram;
  }
}
