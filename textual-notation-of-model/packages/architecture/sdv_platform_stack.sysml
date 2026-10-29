/*
 * DE4SDV SDV platform stack architecture model slice.
 *
 * This package models the layered architecture of a software-defined vehicle
 * as a product-line variation structure. It defines the stack layers, their
 * boundary interfaces, and the variation points where configurable choices
 * select between open-source realizations.
 *
 * Scope of this slice:
 *   - Stack layer definitions (vehicle applications, middleware, OS, hypervisor, hardware)
 *   - Boundary interface definitions between adjacent layers
 *   - Variation points with candidate variant realizations, inlined
 *     as structural variation points on the stack's layer parts, for the
 *     main side and the optional guest side of one SoC
 *   - Design notes on layer coexistence; the compatibility rules are the
 *     constraints of the PLEML feature model
 *
 * Out of scope for this slice:
 *   - Internal architecture of any specific OSS project (Autoware, S-CORE, etc.)
 *   - Allocation of functional responsibilities to execution platforms
 *   - Timing/safety/security property binding to specific stacks
 *   - Compliance or type-approval claims
 *   - Physical/mechanical domain modeling
 *
 * Conventions:
 *   - Layer definitions use `part def` with doc annotations
 *   - Boundary interfaces use `interface def` with directional ports
 *   - Variability uses native SysML v2 `variation` / `variant` notation
 *   - Candidate realizations are `part def` specializations of layer defs,
 *     marked as candidates with doc-only provenance (no compliance claim)
 *   - Design notes use doc-only `constraint def`s; the compatibility
 *     rules are not restated here
 *   - File uses a flat top-level package name (DE4SDV_SDVPlatformStack)
 *     to avoid cross-file sibling-package import issues in SysIDE
 */

package DE4SDV_SDVPlatformStack {
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  /* ──────────────────────────────────────────
   * Stack layer definitions
   * ──────────────────────────────────────────
   * Each layer is an abstract part def. Concrete realizations
   * specialize these defs and appear as variants in the variation
   * section below.
   */

  part def SDVPlatformStack {
    doc /*
     * Complete layered architecture of a software-defined vehicle
     * computing platform. A configured member product selects one
     * realization from each variation, subject to the constraints of the
     * PLEML feature model.
     *
     * One SoC has a main side and an optional guest side. The main side is
     * the execution domain that runs the vehicle application, on the
     * operating system of osPlatform. With KVM, the main side is the KVM
     * host: its operating system hosts the hypervisor and is not a guest of
     * it. The guest side is a second execution domain under the
     * hypervisor, with guestOSPlatform and guestMiddleware. It is a guest
     * partition of one or more VMs. How many VMs it holds, and which image
     * each one runs, are realization choices (ADR 0025).
     *
     * The middleware variation is the middleware that the vehicle
     * application integrates with through the adapter. Eclipse S-CORE and
     * AUTOSAR Adaptive run on the main side. An AAOS SDV partner runs in
     * the guest (constraint C009 of the feature model), so the androidSDV
     * variant refers to the AAOS SDV of the guest and adds no second
     * instance.
     */

    variation part vehicleApplication : VehicleApplicationLayer {
      /* ADAS domain candidates shown; other domain applications (body,
       * chassis, telematics, IVI) to be added in domain-specific increments. */
      variant part autoware : AutowareStack;
      variant part openpilot : OpenpilotStack;
      variant part apollo : ApolloStack;
    }

    variation part middleware : MiddlewareLayer {
      /* The middleware that the vehicle application integrates with. The
       * AAOS SDV partner is a reference to the AAOS SDV of the guest. */
      variant part eclipseSCORE : EclipseSCORE;
      variant ref part androidSDV : AndroidSDVMiddleware references guestMiddleware::androidSDV;
      variant part autosarAdaptive : AUTOSARAdaptive;
      variant part none[0]; /* single-domain architecture, no vehicle-level middleware */
    }

    variation part applicationMiddlewareAdapter : ApplicationMiddlewareAdapterLayer {
      variant part autowareToSCORE : AutowareToSCOREAdapter;
      variant part autowareToAAOSSDV : AutowareToAAOSSDVAdapter;
      variant part autowareToAUTOSAR : AutowareToAUTOSARAdapter;
      variant part openpilotToSCORE : OpenpilotToSCOREAdapter;
      variant part apolloToSCORE : ApolloToSCOREAdapter;
      variant part none[0]; /* no adapter when no vehicle-level middleware */
    }

    variation part osPlatform : OSPlatformLayer {
      /* The main side: the operating system of the execution domain that
       * runs the vehicle application. */
      variant part linux : LinuxPlatform;
      variant part android : AndroidHLOS;
      variant part qnx : QNXPlatform;
    }

    variation part hypervisor : HypervisorLayer {
      variant part qvm : QNXQVM;
      variant part acrn : ACRNHypervisor;
      variant part kvm : KVMHypervisor;
      variant part none[0]; /* single-domain architecture, no hypervisor */
    }

    variation part guestOSPlatform : OSPlatformLayer {
      /* The guest side: the operating system of the second execution
       * domain, under the hypervisor of the SoC. The domain holds one or
       * more VMs. */
      variant part android : AndroidHLOS;
      variant part none[0]; /* no guest domain */
    }

    variation part guestMiddleware : MiddlewareLayer {
      /* The middleware of the guest side, on the guest operating system. */
      variant part androidSDV : AndroidSDVMiddleware;
      variant part none[0]; /* no guest middleware */
    }

    part hardware : HardwareLayer;

    /*
     * Inter-layer boundary interfaces.
     * Each boundary is a bidirectional interface between adjacent layers.
     * The contracts at these boundaries are what DE4SDV models; the
     * concrete realizations either conform or don't.
     */
    interface applicationMiddlewareBoundary : ApplicationAdapterInterface
      connect vehicleApplication.middlewarePort to applicationMiddlewareAdapter.applicationPort;

    interface adapterMiddlewareBoundary : AdapterMiddlewareInterface
      connect applicationMiddlewareAdapter.middlewarePort to middleware.applicationPort;

    /*
     * The middleware-to-OS boundary, per side. Eclipse S-CORE and AUTOSAR
     * Adaptive run on the main-side OS. The guest middleware runs on the
     * guest OS; the AAOS SDV partner is that guest middleware, so it has
     * no boundary to the main-side OS.
     */
    interface eclipseSCOREOSBoundary : MiddlewareOSInterface
      connect middleware::eclipseSCORE.osPort to osPlatform.middlewarePort;

    interface autosarAdaptiveOSBoundary : MiddlewareOSInterface
      connect middleware::autosarAdaptive.osPort to osPlatform.middlewarePort;

    interface guestMiddlewareOSBoundary : MiddlewareOSInterface
      connect guestMiddleware.osPort to guestOSPlatform.middlewarePort;

    /*
     * Only the guest OS is connected to the guest port. The main-side OS is
     * not: with KVM it hosts the hypervisor; with ACRN it runs in a VM too
     * (ACRNHypervisor), and with QVM its relation is left to the
     * realization. The stack does not model these main-side relations as
     * connections.
     */
    interface guestOSHypervisorBoundary : OSHypervisorInterface
      connect guestOSPlatform.hypervisorPort to hypervisor.guestPort;

    interface hypervisorHardwareBoundary : HardwareHypervisorInterface
      connect hypervisor.hypervisorPort to hardware.hypervisorPort;
  }

  /* ──────────────────────────────────────────
   * Layer abstractions
   * ──────────────────────────────────────────
   * Each layer def declares the boundary ports it exposes to adjacent
   * layers. Internal structure is deliberately not modeled.
   */

  part def VehicleApplicationLayer {
    doc /*
     * Vehicle domain-specific application layer.
     * Provides domain-specific applications such as ADAS (perception,
     * planning, control), body, chassis, powertrain, IVI, telematics,
     * connectivity, and diagnostics.
     *
     * Candidate realizations shown: Autoware, Openpilot, Apollo Auto (ADAS domain).
     * Domain-specific application stacks typically ship their own internal middleware
     * (ROS 2, Cyber RT, custom) for ADAS-internal communication.
     * The boundary port to the vehicle-level middleware handles
     * vehicle signal access, diagnostics, and lifecycle coordination.
     */

    port middlewarePort : ApplicationAdapterPort;
  }

  part def ApplicationMiddlewareAdapterLayer {
    doc /*
     * Adapter between domain-specific application stacks and vehicle-level middleware.
     * Each application stack ships its own internal communication (e.g. Autoware uses ROS 2/DDS);
     * the vehicle-level middleware uses a different communication paradigm (e.g. S-CORE uses LoLa,
     * Android SDV uses VSIDL service bundles, AUTOSAR uses SOME/IP). The adapter translates
     * between these.
     */

    port applicationPort : ApplicationAdapterPort;
    port middlewarePort : MiddlewareAdapterPort;
  }

  part def MiddlewareLayer {
    doc /*
     * Vehicle-level middleware / runtime platform.
     * Provides IPC, lifecycle management, service discovery,
     * diagnostics, persistency, and timing orchestration for
     * the applications of its execution domain.
     *
     * Candidate realizations: Eclipse S-CORE, Android SDV,
     * AUTOSAR Adaptive Platform (AP). The stack has two middleware slots:
     * middleware, the one that the vehicle application integrates with,
     * and guestMiddleware, the one of the guest side.
     *
     * Note: AGL is a full platform (OS + IVI + app framework),
     * not a middleware layer. It is modeled at the OS platform layer.
     */

    port applicationPort : MiddlewareAdapterPort;
    port osPort : MiddlewareOSPort;
  }

  part def OSPlatformLayer {
    doc /*
     * Operating system / platform layer.
     * Provides scheduling, memory management, driver support,
     * and POSIX or Android framework services.
     *
     * Candidate realizations: Linux (AGL, generic), Android HLOS,
     * QNX, AUTOSAR Adaptive platform. The stack has two OS slots:
     * osPlatform for the main side and guestOSPlatform for the guest
     * side. The hypervisorPort serves an OS that runs as a guest.
     */

    port middlewarePort : MiddlewareOSPort;
    port hypervisorPort : OSHypervisorPort;
  }

  part def HypervisorLayer {
    doc /*
     * Virtualization / hypervisor layer.
     * Provides partition isolation for mixed-criticality systems
     * where multiple OS domains share the same SoC. One hypervisor
     * per SoC.
     *
     * Optional: single-domain architectures do not use a hypervisor.
     * The variation below includes a "none" variant for this case.
     *
     * Its guest port serves the guest side. Whether the main side hosts
     * the hypervisor or runs as a guest of it depends on the realization:
     * KVM runs in the Linux kernel of the main side, so the main side is
     * its host. The stack connects only the guest OS to the guest port.
     *
     * Candidate realizations: QNX QVM, ACRN, KVM (Linux).
     */

    port guestPort : OSHypervisorPort;
    port hypervisorPort : HardwareHypervisorPort;
  }

  part def HardwareLayer {
    doc /*
     * Physical compute hardware: SoC, MCU, sensors, actuators.
     * DE4SDV does not model physics, thermodynamics, or mechanics
     * at this layer — only the compute platform boundary that
     * the software stack executes on.
     *
     * Candidate realizations: Qualcomm, NVIDIA, Renesas, NXP, etc.
     * This layer is deliberately abstract; concrete hardware modeling
     * is out of scope for the SDV platform stack slice.
     */

    port hypervisorPort : HardwareHypervisorPort;
  }

  /* ──────────────────────────────────────────
   * Boundary interface definitions
   * ──────────────────────────────────────────
   * Each interface def declares the contract surface between
   * two adjacent layers. These are abstract contracts; specific
   * timing, safety, and security properties will be added in
   * the reference-contract-packages increment.
   */

  port def ApplicationMiddlewarePort {
    doc /*
     * Port type for the Vehicle Application ↔ Middleware boundary.
     * Carries vehicle signal access, diagnostics, lifecycle
     * coordination, and service-binding interactions.
     */
    inout item vehicleSignals;
    inout item diagnosticCommands;
    inout item lifecycleEvents;
    inout item serviceRequests;
  }

  interface def ApplicationMiddlewareInterface {
    doc /*
     * Contract between the vehicle application layer and the
     * vehicle-level middleware. The application stack expects signal
     * access, timing-aware scheduling, and fault containment
     * from the middleware. The middleware expects the application
     * stack to register as a managed application with defined
     * lifecycle hooks.
     */
    end adasSide : ApplicationMiddlewarePort;
    end middlewareSide : ApplicationMiddlewarePort;
  }

  port def ApplicationAdapterPort {
    doc /*
     * Port type for the Vehicle Application ↔ Adapter boundary.
     * Carries application-native communication (e.g. ROS 2 topics for Autoware).
     */
    inout item applicationNativeMessages;
    inout item applicationLifecycleEvents;
  }

  port def MiddlewareAdapterPort {
    doc /*
     * Port type for the Adapter ↔ Middleware boundary.
     * Carries middleware-native communication (e.g. LoLa for S-CORE, VSIDL for Android SDV, SOME/IP for AUTOSAR).
     */
    inout item middlewareNativeMessages;
    inout item middlewareLifecycleEvents;
  }

  interface def ApplicationAdapterInterface {
    doc /*
     * Contract between the vehicle application layer and the adapter. The application stack publishes/subscribes in its native protocol; the adapter translates.
     */
    end applicationSide : ApplicationAdapterPort;
    end adapterSide : ApplicationAdapterPort;
  }

  interface def AdapterMiddlewareInterface {
    doc /*
     * Contract between the adapter and the vehicle-level middleware. The adapter translates application-native messages to middleware-native service calls/signals.
     */
    end adapterSide : MiddlewareAdapterPort;
    end middlewareSide : MiddlewareAdapterPort;
  }

  port def MiddlewareOSPort {
    doc /*
     * Port type for the Middleware ↔ OS boundary.
     * Carries scheduling requests, memory allocation,
     * power management, and watchdog/timeout interactions.
     */
    inout item schedulingRequests;
    inout item memoryAllocation;
    inout item powerManagement;
    inout item watchdogSignals;
  }

  interface def MiddlewareOSInterface {
    doc /*
     * Contract between the middleware runtime and the
     * operating system. The middleware expects preemptive
     * scheduling, memory isolation, deterministic timing
     * support, and driver access from the OS. The OS expects
     * the middleware to respect resource limits and
     * scheduling policies.
     */
    end middlewareSide : MiddlewareOSPort;
    end osSide : MiddlewareOSPort;
  }

  port def OSHypervisorPort {
    doc /*
     * Port type for the OS ↔ Hypervisor boundary.
     * Carries partition configuration, inter-VM communication,
     * resource allocation, and isolation properties.
     */
    inout item partitionConfig;
    inout item interVMCommunication;
    inout item resourceAllocation;
  }

  interface def OSHypervisorInterface {
    doc /*
     * Contract between an OS domain and the hypervisor.
     * The OS expects CPU/memory/I/O allocation, partition
     * isolation, and inter-VM communication channels from
     * the hypervisor. The hypervisor expects the OS to
     * operate within its allocated partition.
     */
    end osSide : OSHypervisorPort;
    end hypervisorSide : OSHypervisorPort;
  }

  port def HardwareHypervisorPort {
    doc /*
     * Port type for the Hypervisor ↔ Hardware boundary.
     * Carries hardware resource access, interrupt routing,
     * and platform initialization.
     */
    inout item hardwareResources;
    inout item interruptRouting;
  }

  interface def HardwareHypervisorInterface {
    doc /*
     * Contract between the hypervisor and the physical
     * compute hardware. The hypervisor expects access to
     * CPU cores, memory regions, interrupt controllers,
     * and I/O devices. This is the lowest software-visible
     * boundary; below it is hardware only.
     */
    end hypervisorSide : HardwareHypervisorPort;
    end hardwareSide : HardwareHypervisorPort;
  }

  /* ──────────────────────────────────────────
   * Candidate realizations — vehicle application layer (ADAS domain shown)
   * ────────────────────────────────────────── */
  part def AutowareStack :> VehicleApplicationLayer {
    doc /*
     * Autoware (Autoware Foundation).
     * Open-source autonomous driving stack based on ROS 2.
     * License: Apache 2.0.
     * Status: candidate realization — no assumption of
     * conformance to DE4SDV boundary contracts without
     * evidence.
     */
  }

  part def OpenpilotStack :> VehicleApplicationLayer {
    doc /*
     * Openpilot (comma.ai).
     * Open-source driver assistance system (L2).
     * Ships its own internal middleware; the boundary port
     * captures vehicle-level integration only.
     * License: MIT / comma.ai custom.
     * Status: candidate realization.
     */
  }

  part def ApolloStack :> VehicleApplicationLayer {
    doc /*
     * Apollo Auto (Baidu).
     * Open-source autonomous driving stack using Cyber RT
     * as internal middleware.
     * License: Apache 2.0.
     * Status: candidate realization.
     */
  }

  /* ──────────────────────────────────────────
   * Candidate realizations — application-middleware adapter layer
   * ────────────────────────────────────────── */
  part def AutowareToSCOREAdapter :> ApplicationMiddlewareAdapterLayer {
    doc /*
     * Adapts Autoware ROS 2 topics to Eclipse S-CORE LoLa IPC.
     */
  }

  part def AutowareToAAOSSDVAdapter :> ApplicationMiddlewareAdapterLayer {
    doc /*
     * Candidate boundary between Autoware ROS 2 and AAOS SDV service
     * interfaces. A configured product may select a direct VSIDL-to-ROS 2
     * realization or a separately justified brokered realization. This
     * definition does not claim generated bindings, transport, deployment,
     * runtime behavior, or interoperability evidence.
     */
  }

  part def AutowareToAUTOSARAdapter :> ApplicationMiddlewareAdapterLayer {
    doc /*
     * Adapts Autoware ROS 2 topics to AUTOSAR Adaptive SOME/IP services.
     */
  }

  part def OpenpilotToSCOREAdapter :> ApplicationMiddlewareAdapterLayer {
    doc /*
     * Adapts Openpilot internal communication to S-CORE LoLa.
     */
  }

  part def ApolloToSCOREAdapter :> ApplicationMiddlewareAdapterLayer {
    doc /*
     * Adapts Apollo Cyber RT to S-CORE LoLa.
     */
  }

  /* ──────────────────────────────────────────
   * Candidate realizations — Middleware layer
   * ────────────────────────────────────────── */
  part def EclipseSCORE :> MiddlewareLayer {
    doc /*
     * Eclipse S-CORE (Safe Open Vehicle Core).
     * Open-source automotive middleware (C++ / Rust).
     * Modules: communication (LoLa), orchestration, persistency,
     * time, lifecycle, diagnostics, baselibs.
     * Targets: Linux, QNX. Not designed for Android HLOS.
     * In the stack it runs on the main side, so the main-side operating
     * system is Linux or QNX (constraint C001 of the feature model).
     * License: Apache 2.0.
     * Status: candidate realization. S-CORE maintainers have
     * not been engaged on SysML v2 model integration.
     */
  }

  part def AndroidSDVMiddleware :> MiddlewareLayer {
    doc /*
     * Android SDV (Google / AOSP): the AAOS SDV middleware, a native
     * Android-derived platform for distributed vehicle services.
     * It runs on Android HLOS (constraint C008 of the feature model). In
     * the stack it runs in the guest domain under a hypervisor: it is the
     * guest middleware, and an AAOS SDV partner of the vehicle application
     * is that guest middleware (C009).
     *
     * The image that carries it is a realization choice. The headless SDV
     * Core image (sdv_core_cf) excludes the JVM, Java services, Android
     * applications and GUI functionality. The display-capable IVI image
     * (sdv_ivi_cf) runs Android applications with a GUI. A product that
     * shows the HMI on a display selects the hmiDisplay capability (C010).
     *
     * Internal structure modeled in:
     *   textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml
     * (DE4SDV_AAOSSDVMiddlewareBoundary package).
     *
     * Key elements: Orchestrator, Service Lifecycle Manager, Health Monitor,
     * Update Manager, VSIDL/Middleware, Service Discovery, RPC, Data Tunnel,
     * SOME/IP interoperability, Automotive Services (Diagnostics, Configuration,
     * Calibration, Vehicle Power Mode, User Profile).
     *
     * License: Apache 2.0 (AOSP).
     * Status: candidate realization. Upstream AAOS SDV maintainers have
     * not been engaged on DE4SDV model integration (GAP-MW-005).
     */
  }

  part def AUTOSARAdaptive :> MiddlewareLayer {
    doc /*
     * AUTOSAR Adaptive Platform (AP).
     * Service-oriented automotive middleware standard.
     * This entry is a placeholder for the standard interface
     * contract, not a specific open-source implementation.
     * License: varies by implementation.
     * Status: candidate realization — interface contract only.
     */
  }

  /* ──────────────────────────────────────────
   * Candidate realizations — OS platform layer
   * ────────────────────────────────────────── */
  part def LinuxPlatform :> OSPlatformLayer {
    doc /*
     * Generic Linux platform (POSIX, preemptive scheduling).
     * Includes AGL and custom Linux distributions.
     * License: GPL (kernel) + Apache 2.0 / varies (user space).
     * Status: candidate realization.
     */
  }

  part def AndroidHLOS :> OSPlatformLayer {
    doc /*
     * Android High-Level OS (Google / AOSP).
     * Linux kernel (GKI) + Android framework.
     * License: Apache 2.0 (AOSP) + GPL (kernel).
     * Status: candidate realization.
     */
  }

  part def QNXPlatform :> OSPlatformLayer {
    doc /*
     * QNX Neutrino RTOS (BlackBerry / QNX).
     * Real-time OS with a microkernel and a POSIX API.
     * License: commercial (not open-source).
     * Status: candidate realization — included for mixed-criticality
     * architectures; acknowledged as non-OSS.
     */
  }

  /* ──────────────────────────────────────────
   * Candidate realizations — Hypervisor layer
   * ────────────────────────────────────────── */
  part def QNXQVM :> HypervisorLayer {
    doc /*
     * QNX Virtual Machine (QVM) hypervisor.
     * Host for mixed-criticality: QNX + Linux + Android guests.
     * License: commercial (QNX).
     * Status: candidate realization.
     */
  }

  part def ACRNHypervisor :> HypervisorLayer {
    doc /*
     * ACRN (Project ACRN, Linux Foundation).
     * Open-source hypervisor for automotive and IoT.
     * Supports Linux and Android guests.
     * It runs each execution domain in a VM, the service VM included, so in
     * the stack the main side is an ACRN guest too.
     * License: BSD-2-Clause.
     * Status: candidate realization.
     */
  }

  part def KVMHypervisor :> HypervisorLayer {
    doc /*
     * KVM (Kernel-based Virtual Machine, Linux).
     * Open-source virtualization in the Linux kernel.
     * In the stack the main side hosts it: KVM runs in the kernel of the
     * main-side operating system, and only the guest OS is a KVM guest.
     * License: GPL / LGPL.
     * Status: candidate realization.
     */
  }

  /* ──────────────────────────────────────────
   * Compatibility rules and design notes
   * ──────────────────────────────────────────
   * The compatibility rules between the layer realizations are the
   * constraints of the PLEML feature model,
   * model-based-product-line-engineering/feature-models/sdv_product_line.sysml:
   * the exclusions C001 and C003 to C005, the requires constraints C007
   * to C011 and the pair exclusions of Openpilot and Apollo. This
   * superset does not restate them. The constraint definitions below are
   * design notes, not rules.
   */

  constraint def ApplicationMiddlewareCoexistence {
    doc /*
     * Application ↔ Middleware coexistence.
     *
     * Domain-specific application stacks (e.g. Autoware, Openpilot, Apollo for ADAS) each
     * ship their own internal communication middleware. They
     * coexist with the vehicle-level middleware (S-CORE, Android SDV,
     * AUTOSAR Adaptive) as separate layers — not as alternatives
     * at the same layer.
     *
     * The application stack handles domain-internal pipelines
     * (e.g. ADAS perception→planning→control).
     * The vehicle middleware handles vehicle signal access,
     * diagnostics, lifecycle, and inter-domain communication.
     *
     * No invalid combination exists at this boundary in principle,
     * but integration effort varies significantly:
     *   Autoware + S-CORE: ROS 2 IPC must bridge to LoLa IPC
     *   Openpilot + anything: custom device model, limited integration
     *   Apollo + anything: Cyber RT must bridge to external middleware
     */
  }

  constraint def ApplicationMiddlewareAdapterCompatibility {
    doc /*
     * Adapter compatibility across application and middleware selections.
     *
     * The adapter variation must match both the selected application stack
     * and the selected vehicle-level middleware. The adapter is present only
     * when a non-none vehicle middleware is selected; when middleware = none,
     * the adapter is also none and the application↔adapter and adapter↔middleware
     * boundaries are absent.
     *
     * Intended pairings:
     *   Autoware ↔ AutowareToSCOREAdapter ↔ EclipseSCORE
     *   Autoware ↔ AutowareToAAOSSDVAdapter ↔ AndroidSDVMiddleware
     *   Autoware ↔ AutowareToAUTOSARAdapter ↔ AUTOSARAdaptive
     *   Openpilot ↔ OpenpilotToSCOREAdapter ↔ EclipseSCORE
     *   Apollo ↔ ApolloToSCOREAdapter ↔ EclipseSCORE
     */
  }

  constraint def AGLPlatformScope {
    doc /*
     * AGL (Automotive Grade Linux) scope note.
     *
     * AGL is a full platform (OS + IVI framework + app framework +
     * compositor), not just an OS kernel. When AGL is selected as
     * the OS platform variant, it includes its own application
     * framework and does not simultaneously run S-CORE or
     * Android SDV middleware — AGL is an alternative to that
     * combination, not a layer beside it.
     *
     * This is a modeling note, not a hard constraint. AGL could
     * coexist with a domain application stack on a separate compute domain
     * via a hypervisor, but not on the same domain as S-CORE.
     */
  }

  /* ──────────────────────────────────────────
   * Configured member product base
   * ──────────────────────────────────────────
   * ConfiguredSDVVariant is the abstract base for configured member
   * products. Concrete configured variants are generated by the PLE
   * configurator (tools/configure_variant.py) from the receipts of the
   * PLEML feature configurations, not hand-written here.
   *
   * See:
   *   model-based-product-line-engineering/feature-models/sdv_product_line.sysml
   *   model-based-product-line-engineering/feature-configurations/
   *   model-based-product-line-engineering/product-models/
   */
  part def ConfiguredSDVVariant :> SDVPlatformStack {
    doc /*
     * A configured member product of the SDV product line.
     * Selects one variant from each variation, subject to the
     * constraints of the PLEML feature model.
     *
     * Concrete configured variants are generated by the PLE configurator
     * (tools/configure_variant.py) from the receipts of the PLEML feature
     * configurations.
     */
  }

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view sdvPlatformStackStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame physicalStructureConcern;
    }

    expose DE4SDV_SDVPlatformStack::*;
    render asTreeDiagram;
  }
}
