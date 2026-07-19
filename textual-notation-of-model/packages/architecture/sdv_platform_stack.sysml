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
 *     as structural variation points on the stack's layer parts
 *   - Compatibility constraints between layers
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
 *   - Compatibility constraints use `constraint def`
 *   - File uses a flat top-level package name (DE4SDV_SDVPlatformStack)
 *     to avoid cross-file sibling-package import issues in SysIDE
 */

package DE4SDV_SDVPlatformStack {

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
     * realization from each variation, subject to compatibility
     * constraints.
     */

    variation part vehicleApplication : VehicleApplicationLayer {
      /* ADAS domain candidates shown; other domain applications (body,
       * chassis, telematics, IVI) to be added in domain-specific increments. */
      variant part autoware : AutowareStack;
      variant part openpilot : OpenpilotStack;
      variant part apollo : ApolloStack;
    }

    variation part middleware : MiddlewareLayer {
      variant part eclipseSCORE : EclipseSCORE;
      variant part androidSDV : AndroidSDVMiddleware;
      variant part autosarAdaptive : AUTOSARAdaptive;
    }

    variation part osPlatform : OSPlatformLayer {
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

    part hardware : HardwareLayer;

    /*
     * Inter-layer boundary interfaces.
     * Each boundary is a bidirectional interface between adjacent layers.
     * The contracts at these boundaries are what DE4SDV models; the
     * concrete realizations either conform or don't.
     */
    interface applicationMiddlewareBoundary : ApplicationMiddlewareInterface
      connect vehicleApplication.middlewarePort to middleware.applicationPort;

    interface middlewareOSBoundary : MiddlewareOSInterface
      connect middleware.osPort to osPlatform.middlewarePort;

    interface osHypervisorBoundary : OSHypervisorInterface
      connect osPlatform.hypervisorPort to hypervisor.guestPort;

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

    port middlewarePort : ApplicationMiddlewarePort;
  }

  part def MiddlewareLayer {
    doc /*
     * Vehicle-level middleware / runtime platform.
     * Provides IPC, lifecycle management, service discovery,
     * diagnostics, persistency, and timing orchestration for
     * vehicle applications running on the same compute domain.
     *
     * Candidate realizations: Eclipse S-CORE, Android SDV,
     * AUTOSAR Adaptive (ARA).
     *
     * Note: AGL is a full platform (OS + IVI + app framework),
     * not a middleware layer. It is modeled at the OS platform layer.
     */

    port applicationPort : ApplicationMiddlewarePort;
    port osPort : MiddlewareOSPort;
  }

  part def OSPlatformLayer {
    doc /*
     * Operating system / platform layer.
     * Provides scheduling, memory management, driver support,
     * and POSIX or Android framework services.
     *
     * Candidate realizations: Linux (AGL, generic), Android HLOS,
     * QNX, AUTOSAR Adaptive platform.
     */

    port middlewarePort : MiddlewareOSPort;
    port hypervisorPort : OSHypervisorPort;
  }

  part def HypervisorLayer {
    doc /*
     * Virtualization / hypervisor layer.
     * Provides partition isolation for mixed-criticality systems
     * where multiple OS domains share the same SoC.
     *
     * Optional: single-domain architectures do not use a hypervisor.
     * The variation below includes a "none" variant for this case.
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
   * Candidate realizations — Middleware layer
   * ────────────────────────────────────────── */
  part def EclipseSCORE :> MiddlewareLayer {
    doc /*
     * Eclipse S-CORE (Safe Open Vehicle Core).
     * Open-source automotive middleware (C++ / Rust).
     * Modules: communication (LoLa), orchestration, persistency,
     * time, lifecycle, diagnostics, baselibs.
     * Targets: Linux, QNX. Not designed for Android HLOS.
     * License: Apache 2.0.
     * Status: candidate realization. S-CORE maintainers have
     * not been engaged on SysML v2 model integration.
     */
  }

  part def AndroidSDVMiddleware :> MiddlewareLayer {
    doc /*
     * Android SDV (Google / AOSP).
     * Service bundle architecture with VSIDL, Orchestrator,
     * VM isolation, and DICE identity/attestation.
     * Runs on Android HLOS, Linux, and as QNX QVM guest.
     * License: Apache 2.0 (AOSP).
     * Status: candidate realization.
     */
  }

  part def AUTOSARAdaptive :> MiddlewareLayer {
    doc /*
     * AUTOSAR Adaptive Platform (ARA).
     * Automotive middleware standard with functional safety
     * focus (ASIL).
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
     * Real-time POSIX OS, ASIL-D certified.
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
     * License: BSD-2-Clause.
     * Status: candidate realization.
     */
  }

  part def KVMHypervisor :> HypervisorLayer {
    doc /*
     * KVM (Kernel-based Virtual Machine, Linux).
     * Open-source virtualization in the Linux kernel.
     * License: GPL / LGPL.
     * Status: candidate realization.
     */
  }

  /* ──────────────────────────────────────────
   * Compatibility constraints
   * ──────────────────────────────────────────
   * These constraints encode which combinations of layer
   * realizations are architecturally valid. They are the
   * product-line decision rules that enable trade-off analysis.
   *
   * Constraint bodies are documented as doc comments in this
   * increment. Future increments may formalize them as
   * require constraint bodies when validation confirms the
   * SysML v2 constraint expression syntax.
   */

  constraint def MiddlewareOSCompatibility {
    doc /*
     * Middleware ↔ OS compatibility.
     *
     * Valid combinations:
     *   Eclipse S-CORE  ↔ Linux, QNX (not Android HLOS)
     *   Android SDV     ↔ Linux, Android HLOS, QNX (as QVM guest)
     *   AUTOSAR Adaptive ↔ Linux, QNX
     *
     * Invalid:
     *   Eclipse S-CORE ↔ Android HLOS (architecturally incompatible)
     */
  }

  constraint def HypervisorOSCompatibility {
    doc /*
     * Hypervisor ↔ OS compatibility.
     *
     * Valid combinations:
     *   QNX QVM  ↔ QNX (native), Linux, Android, AGL (all as guests)
     *   ACRN     ↔ Linux, Android, AGL (all as guests; not QNX)
     *   KVM      ↔ Linux, AGL (guests; QNX guest support varies)
     *   none     ↔ any single OS (no virtualization)
     *
     * Invalid:
     *   ACRN ↔ QNX (not supported)
     *   KVM ↔ QNX (community-only, not production)
     */
  }

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
   * products. Concrete configured variants are generated from
   * Bill-of-Features YAML by the PLE configurator
   * (tools/configure_variant.py), not hand-written here.
   *
   * See:
   *   model-based-product-line-engineering/feature-models/sdv_product_line.yaml
   *   model-based-product-line-engineering/feature-configurations/
   *   model-based-product-line-engineering/product-models/
   */
  part def ConfiguredSDVVariant :> SDVPlatformStack {
    doc /*
     * A configured member product of the SDV product line.
     * Selects one variant from each variation, subject to
     * compatibility constraints.
     *
     * Concrete configured variants are generated from Bill-of-Features
     * by the PLE configurator (tools/configure_variant.py).
     */
  }
}

