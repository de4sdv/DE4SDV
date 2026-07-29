/*
 * DE4SDV AAOS SDV middleware boundary architecture model slice.
 *
 * This package models the internal structure of the Android Automotive OS
 * Software Defined Vehicle platform as visible from DE4SDV's integration
 * perspective. It is NOT a vendored implementation of AAOS SDV — it models
 * the boundary elements that the DE4SDV adapter layer connects to.
 *
 * Source reference:
 *   https://source.android.com/docs/automotive/sdv/workstreams/core/integration-guide
 *   Page last updated: 2026-06-17
 *   License: Apache 2.0 (AOSP)
 *
 * Scope:
 *   - SDV Core boundary definition (headless Android-derived OS guest)
 *   - Core services (Orchestrator, Service Lifecycle Manager, Health Monitor,
 *     Update Manager, Connectivity Manager)
 *   - VSIDL and SDV Middleware (vehicle signal abstraction)
 *   - Communication stack (Service Discovery, RPC, Data Tunnel, SOME/IP)
 *   - Automotive services (Diagnostics, Configuration, Calibration,
 *     Vehicle Power Mode, User Profile)
 *   - Platform software boundary (GKI, virtualization, networking)
 *   - Traceability dependencies to AEBS physical realization required boundaries
 *
 * Out of scope:
 *   - AAOS SDV internal implementation (code, APEX packages, service bundles)
 *   - VM image generation, APEX signing, bootloader integration
 *   - Detailed communication protocol schemas (VSIDL definitions, SOME/IP mappings)
 *   - OEM-specific automotive service logic
 *   - SDV Media and SDV IVI (separate VMs, not in the AEBS integration path)
 *
 * Relationship to SDV platform stack:
 *   AAOS SDV is a middleware variant (AndroidSDVMiddleware) in the SDV platform
 *   stack. This model defines the internal structure of that variant. The
 *   AutowareToAAOSSDVAdapter connects to the boundary ports defined here.
 *
 * Relationship to AEBS:
 *   The AEBS physical software realization defines required boundaries
 *   (RequiredROS2ApplicationRuntimeBoundary, RequiredVehicleInterfaceBoundary,
 *   RequiredHealthSupervisorBoundary, RequiredDiagnosticFailureBridgeBoundary,
 *   RequiredEmergencyMRMHandlerBoundary). This model declares traceability
 *   dependencies showing which AAOS SDV elements can satisfy those boundaries.
 *
 * Architectural notes:
 *   SDV Core is a minimal, headless operating system derived from Android.
 *   It excludes the JVM, Java-based services, Android applications, and GUI
 *   functionality. Vehicle functionality is implemented as native distributed
 *   services. It is primarily designed to run as a VM on a hypervisor.
 *
 *   The architecture has four layers (bottom to top):
 *     1. Platform software (GKI, virtualization, storage, time sync, logging,
 *        power management, networking, security, runtime)
 *     2. Communication stack (Service Discovery, RPC, Data Tunnel, SOME/IP)
 *     3. Core services and frameworks (Orchestrator, Lifecycle Manager,
 *        Health Monitor, Update Manager, VSIDL/Middleware, Connectivity Manager)
 *     4. Automotive services (Diagnostics, Configuration, Calibration,
 *        Vehicle Power Mode, User Profile)
 *
 * Semantic basis:
 * - SysML v2 specification: part def composition, port defs, dependency
 * - DE4SDV increment workflow INC-MW-002
 * - AAOS SDV integration guide (source.android.com, 2026-06-17)
 */

package DE4SDV_AAOSSDVMiddlewareBoundary {
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  /* ──────────────────────────────────────────
   * SDV Core boundary
   * ────────────────────────────────────────── */

  part def SDVCoreBoundary {
    doc /*
     * Headless, native Android-derived operating system guest that hosts
     * distributed vehicle services. Runs on a hypervisor. Excludes JVM,
     * Java services, Android applications, and GUI functionality.
     *
     * One SDV Core instance is one VM. Multiple instances may run on one
     * SoC, on different SoCs, or communicate across the vehicle network.
     * Functions are implemented as distributed services, not permanently
     * tied to a particular processor or ECU.
     */

    /* Core services and frameworks */
    part orchestrator : OrchestratorBoundary;
    part lifecycleManager : ServiceLifecycleManagerBoundary;
    part healthMonitor : HealthMonitorBoundary;
    part updateManager : UpdateManagerBoundary;
    part connectivityManager : ConnectivityManagerBoundary;

    /* VSIDL and SDV Middleware — span the entire platform as a common abstraction */
    part vsidlMiddleware : VSIDLMiddlewareBoundary;

    /* Communication stack */
    part serviceDiscovery : ServiceDiscoveryBoundary;
    part rpc : SDVRPCBoundary;
    part dataTunnel : DataTunnelBoundary;
    part someIp : SomeIpInteropBoundary;

    /* Automotive services */
    part diagnostics : AutomotiveDiagnosticsBoundary;
    part configuration : AutomotiveConfigurationBoundary;
    part calibration : AutomotiveCalibrationBoundary;
    part vehiclePowerMode : VehiclePowerModeBoundary;
    part userProfile : UserProfileBoundary;

    /* Platform software */
    part platformSoftware : SDVPlatformSoftwareBoundary;

    /* Boundary ports exposed to the adapter and other systems */
    port middlewarePort : MiddlewareAdapterPort;
    port vehicleSignalAccessOut : VehicleSignalAccessPort;
    port diagnosticAccessOut : DiagnosticAccessPort;
    port lifecycleCoordinationOut : LifecycleCoordinationPort;
  }

  /* ──────────────────────────────────────────
   * Core services and frameworks
   * ────────────────────────────────────────── */

  part def OrchestratorBoundary {
    doc /*
     * Coordinates services and dependencies across the distributed system.
     * Decides which services run where, manages inter-service dependencies,
     * and coordinates distributed system state.
     */
    port coordinationPort : ServiceCoordinationPort;
  }

  part def ServiceLifecycleManagerBoundary {
    doc /*
     * Starts, stops, and supervises services. Manages APEX-based service
     * deployment units. Services in the same APEX package and certificate
     * may share a process; others are isolated.
     */
    port lifecyclePort : ServiceLifecyclePort;
  }

  part def HealthMonitorBoundary {
    doc /*
     * Observes whether services are functioning correctly. Produces
     * health status that can be consumed by safety-relevant supervisors.
     */
    port healthStatusOut : HealthStatusPort;
  }

  part def UpdateManagerBoundary {
    doc /*
     * Coordinates software changes using Android's A/B system update
     * concepts and APEX packages. Updates are treated as distributed-system
     * transactions, not single-ECU file replacements. Coordinates service
     * dependencies, safe vehicle states, shared partitions, and rollback
     * consistency across VMs.
     */
    port updateCoordinationPort : UpdateCoordinationPort;
  }

  part def ConnectivityManagerBoundary {
    doc /*
     * Native replacement for Android's Java-based connectivity service.
     * Provides centralized network policy, interface selection, and
     * connection management. Prevents every service from independently
     * implementing network policy.
     */
    port networkPolicyPort : NetworkPolicyPort;
  }

  part def VSIDLMiddlewareBoundary {
    doc /*
     * Vehicle Services IDL and SDV Middleware. VSIDL supplies a common
     * definition language for vehicle signals and interfaces. The middleware
     * hides differences between underlying communication technologies
     * (shared memory, vsock, Ethernet, SOME/IP). Together, they provide a
     * source of truth for vehicle data and reduce direct dependencies
     * between applications and individual protocols.
     */
    port signalAccessPort : VehicleSignalAccessPort;
    port serviceInterfacePort : ServiceInterfacePort;
  }

  /* ──────────────────────────────────────────
   * Communication stack
   * ────────────────────────────────────────── */

  part def ServiceDiscoveryBoundary {
    doc /*
     * Finds available services and contributes authentication and
     * authorization. Service discovery is not only a naming directory —
     * it also participates in deciding whether a client is permitted
     * to use a discovered service.
     */
    port discoveryPort : ServiceDiscoveryPort;
  }

  part def SDVRPCBoundary {
    doc /*
     * Request-response remote procedure calls based on predefined APIs.
     * Maps onto different transports (shared memory, vsock, Ethernet)
     * depending on caller and provider location.
     * Semantic: "perform this operation and return a result."
     */
    port rpcPort : RPCPort;
  }

  part def DataTunnelBoundary {
    doc /*
     * Publish-subscribe mechanism. A producer publishes data to a topic;
     * one or more consumers subscribe. Maps onto shared memory (inside VM),
     * vsock (between local VMs), or Ethernet (across systems).
     * Semantic: "publish this data for any interested consumers."
     */
    port topicPublishPort : DataTunnelPort;
    port topicSubscribePort : DataTunnelPort;
  }

  part def SomeIpInteropBoundary {
    doc /*
     * SOME/IP interoperability stack for communication with non-SDV
     * automotive systems. Operates over TCP or UDP. Drawn separately
     * from the native SDV communication abstractions because it is an
     * established automotive protocol, not an SDV-native mechanism.
     */
    port someIpPort : SomeIpPort;
  }

  /* ──────────────────────────────────────────
   * Automotive services
   * ────────────────────────────────────────── */

  part def AutomotiveDiagnosticsBoundary {
    doc /*
     * Vehicle diagnostics service. OEM-specific UDS diagnostic libraries
     * and persistent storage rules are expected here. Provides diagnostic
     * access for external tools and internal health monitoring.
     */
    port diagnosticPort : DiagnosticAccessPort;
  }

  part def AutomotiveConfigurationBoundary {
    doc /*
     * Vehicle configuration service. OEM-specific configuration logic
     * and persistence are expected here.
     */
  }

  part def AutomotiveCalibrationBoundary {
    doc /*
     * Vehicle calibration service. OEM-specific calibration persistence
     * is expected here.
     */
  }

  part def VehiclePowerModeBoundary {
    doc /*
     * Vehicle power mode service. Manages power states, suspend/resume
     * coordination, and vehicle-level power policy.
     */
  }

  part def UserProfileBoundary {
    doc /*
     * User profile service. Manages early availability of user profiles
     * for personalization.
     */
  }

  /* ──────────────────────────────────────────
   * Platform software
   * ────────────────────────────────────────── */

  part def SDVPlatformSoftwareBoundary {
    doc /*
     * Lowest software layer inside SDV Core. Contains:
     * - GKI (Android Generic Kernel Image, currently 6.1 kernel)
     * - Drivers (vsock, Virtio)
     * - HALs (minimal — KeyMint for hardware-backed cryptography)
     * - Core libraries, service runtime
     * - Logging and tracing
     * - Power management
     * - Storage
     * - Time synchronization
     * - Networking (IPv4/IPv6, VLAN, TCP/UDP)
     * - Security and trust (DICE identity, attestation)
     *
     * Virtio is the preferred hardware abstraction. HALs are only used
     * where a standardized virtual device is unavailable.
     */
  }

  /* ──────────────────────────────────────────
   * Port definitions
   * ────────────────────────────────────────── */

  port def ServiceCoordinationPort {
    inout item coordinationRequests;
    inout item coordinationResponses;
  }

  port def ServiceLifecyclePort {
    inout item lifecycleCommands;
    inout item lifecycleStatus;
  }

  port def HealthStatusPort {
    out item healthStatus;
  }

  port def UpdateCoordinationPort {
    inout item updateCommands;
    inout item updateStatus;
  }

  port def NetworkPolicyPort {
    inout item networkPolicy;
    inout item interfaceSelection;
  }

  port def VehicleSignalAccessPort {
    inout item vehicleSignals;
    inout item signalRequests;
  }

  port def ServiceInterfacePort {
    inout item serviceCalls;
    inout item serviceResponses;
  }

  port def ServiceDiscoveryPort {
    inout item discoveryQueries;
    inout item discoveryResults;
    inout item authorizationDecisions;
  }

  port def RPCPort {
    inout item rpcRequests;
    inout item rpcResponses;
  }

  port def DataTunnelPort {
    inout item topicData;
  }

  port def SomeIpPort {
    inout item someIpMessages;
  }

  port def DiagnosticAccessPort {
    inout item diagnosticRequests;
    inout item diagnosticResponses;
  }

  port def LifecycleCoordinationPort {
    doc /* Port type for vehicle lifecycle coordination (suspend, resume, power state). */
    inout item lifecycleEvents;
    inout item powerStateCommands;
  }

  /* ──────────────────────────────────────────
   * Communication transport model
   * ──────────────────────────────────────────
   * The middleware hides transport differences. Applications interact
   * with Middleware, Data Tunnel, or RPC without needing to know whether
   * the underlying transport is shared memory, vsock, or Ethernet.
   */

  item def VsockTransport {
    doc /* Optimized for local host-to-VM and VM-to-VM communication. */
  }

  item def SharedMemoryTransport {
    doc /* Efficient IPC between processes or between host and guest. */
  }

  item def EthernetTransport {
    doc /* Transport for communication between SoCs, to vehicle network, and to legacy ECUs. Supports IPv4 and IPv6, VLAN, TCP and UDP. */
  }

  /* ──────────────────────────────────────────
   * Traceability to AEBS physical realization
   * ──────────────────────────────────────────
   * These dependencies show which AAOS SDV elements can satisfy the
   * AEBS physical software realization's required boundaries. The
   * adapter (AutowareToAAOSSDVAdapter) is the bridge.
   *
   * Key assumption (INC-MW-001, ASM-MW-003): the AEBS emergency
   * intervention path (AEB node → emergency intervention request →
   * vehicle command gate → brake actuation) does NOT go through the
   * adapter or the middleware. The adapter carries vehicle signals,
   * diagnostics, and lifecycle, not safety-critical brake commands.
   */

  dependency vsidlProvidesVehicleSignalAccess
    from VSIDLMiddlewareBoundary to RequiredVehicleInterfaceBoundary;

  dependency healthMonitorSatisfiesHealthSupervision
    from HealthMonitorBoundary to RequiredHealthSupervisorBoundary;

  dependency diagnosticsProvidesDiagnosticBridge
    from AutomotiveDiagnosticsBoundary to RequiredDiagnosticFailureBridgeBoundary;

  dependency lifecycleManagerProvidesRuntimeLifecycle
    from ServiceLifecycleManagerBoundary to RequiredROS2ApplicationRuntimeBoundary;

  dependency orchestratorProvidesMRMCoordination
    from OrchestratorBoundary to RequiredEmergencyMRMHandlerBoundary;

  dependency updateManagerCoordinatesEvidenceService
    from UpdateManagerBoundary to RequiredEvidenceServiceBoundary;

  /*
   * The AutowareToAAOSSDVAdapter connects to this boundary through the
   * MiddlewareAdapterPort. The adapter translates Autoware ROS 2 topics
   * to AAOS SDV VSIDL service calls and Data Tunnel publications.
   */
  dependency adapterConnectsToAAOSSDV
    from AutowareToAAOSSDVAdapter to SDVCoreBoundary;

  /* ──────────────────────────────────────────
   * Network topology boundary
   * ──────────────────────────────────────────
   * SDV Core instances communicate via vsock (same SoC, host-guest),
   * Ethernet (between SoCs, to vehicle network), and shared memory
   * (efficient local IPC). VLAN-capable Ethernet switch provides
   * security segmentation. Optional DMZ for externally exposed systems.
   */

  part def VehicleNetworkBoundary {
    doc /*
     * Vehicle network boundary connecting SDV Core instances, legacy ECUs,
     * and external connectivity. Contains:
     * - VLAN-capable Ethernet switch for security segmentation
     * - Optional DMZ for less trusted or externally exposed systems
     * - Telematics control unit (TCU) with gateway and modem for
     *   controlled Internet access
     *
     * External connectivity passes through the TCU gateway, not directly
     * from every VM.
     */
    port internalNetworkPort : EthernetTransport;
    port externalGatewayPort : EthernetTransport;
  }

  /* ──────────────────────────────────────────
   * SAF concern and view
   * ────────────────────────────────────────── */

  concern def AAOSSDVBoundaryConcern {
    doc /*
     * Reviewers need the AAOS SDV middleware internal structure and its
     * traceability to AEBS physical software realization required boundaries
     * to be visible for the middleware integration increment.
     */
    require constraint {
      doc /*
       * An AAOS SDV boundary view shall show the core services, communication
       * stack, automotive services, platform software boundary, and
       * traceability dependencies to AEBS required boundaries.
       */
    }
  }

  concern aaosSdvBoundaryConcern : AAOSSDVBoundaryConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
    stakeholder platformEngineer : OpenSourceReviewer;
  }

  viewpoint def AAOSSDVBoundaryViewpoint {
    doc /*
     * AAOS SDV middleware boundary viewpoint for reviewing the internal
     * structure and integration surface of the AAOS SDV platform.
     */
    require constraint {
      doc /*
       * The view shall show the SDV Core boundary composition, core
       * services, communication stack, automotive services, platform
       * software, and traceability dependencies.
       */
    }
  }

  view aaosSdvBoundaryView {
    viewpoint selectedAAOSSDVBoundaryViewpoint : AAOSSDVBoundaryViewpoint {
      frame aaosSdvBoundaryConcern;
    }

    expose SDVCoreBoundary;
    expose OrchestratorBoundary;
    expose ServiceLifecycleManagerBoundary;
    expose HealthMonitorBoundary;
    expose UpdateManagerBoundary;
    expose ConnectivityManagerBoundary;
    expose VSIDLMiddlewareBoundary;
    expose ServiceDiscoveryBoundary;
    expose SDVRPCBoundary;
    expose DataTunnelBoundary;
    expose SomeIpInteropBoundary;
    expose AutomotiveDiagnosticsBoundary;
    expose AutomotiveConfigurationBoundary;
    expose AutomotiveCalibrationBoundary;
    expose VehiclePowerModeBoundary;
    expose UserProfileBoundary;
    expose SDVPlatformSoftwareBoundary;
    expose VehicleNetworkBoundary;
    expose vsidlProvidesVehicleSignalAccess;
    expose healthMonitorSatisfiesHealthSupervision;
    expose diagnosticsProvidesDiagnosticBridge;
    expose lifecycleManagerProvidesRuntimeLifecycle;
    expose orchestratorProvidesMRMCoordination;
    expose updateManagerCoordinatesEvidenceService;
    expose adapterConnectsToAAOSSDV;
    render asTreeDiagram;
  }
}
