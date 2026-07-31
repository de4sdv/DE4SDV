/*
 * DE4SDV middleware physical/software realization model slice.
 *
 * INC-MW-008 maps the middleware logical responsibilities to a concrete
 * candidate software/platform boundary: the Autoware-to-AAOS SDV adapter and
 * the AAOS SDV boundary model. This is a model of the integration boundary,
 * not a vendored AAOS implementation and not runtime evidence.
 *
 * The adapter and AAOS boundary remain candidate realizations. Concrete ROS 2
 * topics, VSIDL service schemas, SOME/IP mappings, process deployment, and
 * executable behavior are deferred until their source contracts are pinned.
 */

package DE4SDV_MWPhysicalSoftwareRealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MWLogicalArchitecture::*;
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import DE4SDV_ROS2Types::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part incMW008 : FeatureIncrement {
    doc /* INC-MW-008: middleware integration physical/software realization. */
  }

  part physicalSourceContractGap : DeferredProductLineScope {
    doc /* GAP-MW-019: Candidate ROS 2, VSIDL, SOME/IP, and service schemas are not pinned to reviewed source revisions. */
  }

  part physicalProcessDeploymentGap : DeferredProductLineScope {
    doc /* GAP-MW-020: Adapter process, executor, runtime, VM, and network deployment are not selected in this realization slice. */
  }

  part physicalServiceSatisfactionGap : DeferredProductLineScope {
    doc /* GAP-MW-021: The candidate AAOS SDV boundary has not been shown to satisfy the logical service responsibilities or requirements. */
  }

  part def AAOSSDVSourceArtifact {
    doc /*
     * Pinned AOSP source manifest for the AAOS SDV build. Manifest branch:
     * android-latest-release; manifest revision:
     * ad156f32caaa06dae91c02d443f6a8fe210eaa54. The SDV projects below use
     * the android17-release revision declared by that manifest.
     *
     * Manifest repository:
     * https://android.googlesource.com/platform/manifest
     * Build target: sdv_core_cf-trunk_staging-userdebug.
     */
  }

  part def AAOSVSIDLProviderAgentSource {
    doc /*
     * VSIDL provider agent from
     * system/software_defined_vehicle/vsidl/provider/agent/sdv. The pinned
     * implementation exposes metadata RPCs including diagnostics declaration,
     * message descriptor, publication descriptor, and RPC method descriptor.
     * Source repository:
     * https://android.googlesource.com/platform/system/software_defined_vehicle/vsidl
     * Source revision: 9d6bfa55d7448844c36af7c5aeadb3e981b6c995.
     * Source files:
     * provider/agent/sdv/src/main.rs
     * provider/agent/sdv/api/protos/messages.proto
     */
  }

  part def AAOSMiddlewareSource {
    doc /*
     * Source-backed AAOS SDV middleware communication implementation from
     * system/software_defined_vehicle/middleware. Source revision:
     * 7ab87b58959e638fc9f1e5a5860cfed20ed29cab.
     * Source repository:
     * https://android.googlesource.com/platform/system/software_defined_vehicle/middleware
     */
  }

  part def AAOSHardwareSDVInterfacesSource {
    doc /*
     * Source-backed hardware/sdv interface definitions for middleware,
     * lifecycle, service discovery, RPC, and data-tunnel boundaries.
     * Source repository:
     * https://android.googlesource.com/platform/hardware/sdv/interfaces
     * Source revision: 3682a3968292032a31d74c450380aa81d5e547ec.
     */
  }

  part def AAOSLifecycleServiceSource {
    doc /*
     * Source-backed lifecycle-management project at
     * system/software_defined_vehicle/lifecycle_management; revision
     * 74813463c7293bf12e0791701b2037b1a26f48f8.
     * Source repository:
     * https://android.googlesource.com/platform/system/software_defined_vehicle/lifecycle_management
     * Relevant source areas: aidl, src, service_bundle_runner, tests.
     */
  }

  part def AAOSHealthMonitorSource {
    doc /*
     * Source-backed health-monitor project at
     * system/software_defined_vehicle/health_monitor; revision
     * a3ffbe9caf8b94041c013deac36c4e5f27b69932.
     * Source repository:
     * https://android.googlesource.com/platform/system/software_defined_vehicle/health_monitor
     * Relevant source areas: src, apex, catalog, integration_tests.
     */
  }

  part def AAOSDiagnosticsSource {
    doc /*
     * Source-backed automotive diagnostics project at
     * system/software_defined_vehicle/automotive_services; revision
     * 1d4dcb7f908a6df97b036a90a5802de8cedebd63.
     * Source repository:
     * https://android.googlesource.com/platform/system/software_defined_vehicle/automotive_services
     * Relevant source area: diagnostics.
     */
  }

  part def SignalAccessClient {
    doc /* Candidate physical/software client for vehicle signal access through the selected adapter and platform boundary. */
    port vehicleSignal : VehicleSignalAccessPort;
  }

  part def DiagnosticAccessClient {
    doc /* Candidate physical/software client for diagnostic access through the selected adapter and platform boundary. */
    port diagnostics : DiagnosticAccessPort;
  }

  part def LifecycleClient {
    doc /* Candidate physical/software client for lifecycle coordination. */
    port lifecycle : LifecycleCoordinationPort;
  }

  part def HealthClient {
    doc /* Candidate physical/software client for health status observation and forwarding. */
    port health : HealthStatusPort;
  }

  part def UpdateClient {
    doc /* Candidate physical/software client for update coordination. */
    port update : UpdateCoordinationPort;
  }

  part def ServiceDiscoveryClient {
    doc /* Candidate physical/software client for service discovery and authorization boundary handling. */
    port discovery : ServiceDiscoveryPort;
  }

  port def VelocityReportPublication :> ROS2TopicPublication {
    out item velocityReport : VelocityReportMessage redefines payload;
  }

  part def AutowareToAAOSSDVAdapterPhysical :> AutowareToAAOSSDVAdapter {
    doc /*
     * Physical adapter candidate with explicit application-side logical ports
     * and AAOS SDV-side service ports. The port contracts are integration
     * boundaries; concrete ROS 2 topic and VSIDL schemas remain controlled by
     * GAP-MW-019 until reviewed source revisions are pinned.
     */
    port applicationSignal : SignalAccessApplicationPort;
    port applicationDiagnostics : DiagnosticApplicationPort;
    port applicationLifecycle : LifecycleApplicationPort;
    port applicationHealth : HealthApplicationPort;
    port applicationUpdate : UpdateApplicationPort;
    port applicationDiscovery : ServiceBindingApplicationPort;

    port aaosSignal : VehicleSignalAccessPort;
    port aaosDiagnostics : DiagnosticAccessPort;
    port aaosLifecycle : LifecycleCoordinationPort;
    port aaosHealth : HealthStatusPort;
    port aaosUpdate : UpdateCoordinationPort;
    port aaosDiscovery : ServiceDiscoveryPort;

    port ros2VelocityOut : VelocityReportPublication {
      doc /* Adapter publication to Autoware topic /vehicle/status/velocity_status. */
    }
    port ros2AutowareStateIn : AutowareStateSubscription {
      doc /* Existing Autoware topic /autoware/state. */
    }
    port ros2DiagnosticsOut : DiagnosticPublication {
      doc /* Existing Autoware diagnostic publication /diagnostics. */
    }
  }

  part def MiddlewarePhysicalSoftwareBoundary {
    doc /*
     * Candidate physical/software integration boundary for an Autoware-to-AAOS
     * SDV configuration. The AAOS model is a boundary reference; no internal
     * implementation, deployment, or runtime claim is made.
     */
    part adapter : AutowareToAAOSSDVAdapterPhysical;
    part aaosSdvBoundary : SDVCoreBoundary;
    part aaosSourceArtifact : AAOSSDVSourceArtifact;
    part vsidlProviderSource : AAOSVSIDLProviderAgentSource;
    part middlewareSource : AAOSMiddlewareSource;
    part hardwareInterfacesSource : AAOSHardwareSDVInterfacesSource;
    part lifecycleServiceSource : AAOSLifecycleServiceSource;
    part healthMonitorSource : AAOSHealthMonitorSource;
    part diagnosticsSource : AAOSDiagnosticsSource;

    part signalAccessClient : SignalAccessClient;
    part diagnosticAccessClient : DiagnosticAccessClient;
    part lifecycleClient : LifecycleClient;
    part healthClient : HealthClient;
    part updateClient : UpdateClient;
    part serviceDiscoveryClient : ServiceDiscoveryClient;
  }

  part physicalSoftware : MiddlewarePhysicalSoftwareBoundary;

  allocation def LogicalToPhysicalSoftwareCandidate {
    doc /* Candidate logical-to-physical mapping. This does not imply complete realization, satisfaction, runtime execution, or acceptance. */
  }

  allocation signalTranslatorCandidate : LogicalToPhysicalSoftwareCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::signalTranslator
    to physicalSoftware::signalAccessClient;
  allocation diagnosticProxyCandidate : LogicalToPhysicalSoftwareCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::diagnosticProxy
    to physicalSoftware::diagnosticAccessClient;
  allocation lifecycleBridgeCandidate : LogicalToPhysicalSoftwareCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::lifecycleBridge
    to physicalSoftware::lifecycleClient;
  allocation healthProxyCandidate : LogicalToPhysicalSoftwareCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::healthProxy
    to physicalSoftware::healthClient;
  allocation updateCoordinatorCandidate : LogicalToPhysicalSoftwareCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::updateCoordinator
    to physicalSoftware::updateClient;
  allocation serviceBindingManagerCandidate : LogicalToPhysicalSoftwareCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::serviceBindingManager
    to physicalSoftware::serviceDiscoveryClient;

  dependency aaosBoundaryCandidateForSignalAccess
    from physicalSoftware::signalAccessClient
    to physicalSoftware::aaosSdvBoundary::vsidlMiddleware;
  dependency aaosBoundaryCandidateForDiagnostics
    from physicalSoftware::diagnosticAccessClient
    to physicalSoftware::aaosSdvBoundary::diagnostics;
  dependency aaosBoundaryCandidateForLifecycle
    from physicalSoftware::lifecycleClient
    to physicalSoftware::aaosSdvBoundary::lifecycleManager;
  dependency aaosBoundaryCandidateForHealth
    from physicalSoftware::healthClient
    to physicalSoftware::aaosSdvBoundary::healthMonitor;
  dependency aaosBoundaryCandidateForUpdates
    from physicalSoftware::updateClient
    to physicalSoftware::aaosSdvBoundary::updateManager;
  dependency aaosBoundaryCandidateForDiscovery
    from physicalSoftware::serviceDiscoveryClient
    to physicalSoftware::aaosSdvBoundary::serviceDiscovery;

  dependency adapterCandidateAtApplicationBoundary
    from physicalSoftware::adapter
    to DE4SDV_MWLogicalArchitecture::logicalSystem;

  dependency adapterSignalMapping
    from physicalSoftware::adapter::applicationSignal
    to physicalSoftware::adapter::aaosSignal;
  dependency adapterDiagnosticMapping
    from physicalSoftware::adapter::applicationDiagnostics
    to physicalSoftware::adapter::aaosDiagnostics;
  dependency adapterLifecycleMapping
    from physicalSoftware::adapter::applicationLifecycle
    to physicalSoftware::adapter::aaosLifecycle;
  dependency adapterHealthMapping
    from physicalSoftware::adapter::applicationHealth
    to physicalSoftware::adapter::aaosHealth;
  dependency adapterUpdateMapping
    from physicalSoftware::adapter::applicationUpdate
    to physicalSoftware::adapter::aaosUpdate;
  dependency adapterDiscoveryMapping
    from physicalSoftware::adapter::applicationDiscovery
    to physicalSoftware::adapter::aaosDiscovery;

  dependency adapterSignalServiceCandidate
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::aaosSdvBoundary::vsidlMiddleware;
  dependency adapterDiagnosticServiceCandidate
    from physicalSoftware::adapter::aaosDiagnostics
    to physicalSoftware::aaosSdvBoundary::diagnostics;
  dependency adapterLifecycleServiceCandidate
    from physicalSoftware::adapter::aaosLifecycle
    to physicalSoftware::aaosSdvBoundary::lifecycleManager;
  dependency adapterHealthServiceCandidate
    from physicalSoftware::adapter::aaosHealth
    to physicalSoftware::aaosSdvBoundary::healthMonitor;
  dependency adapterUpdateServiceCandidate
    from physicalSoftware::adapter::aaosUpdate
    to physicalSoftware::aaosSdvBoundary::updateManager;
  dependency adapterDiscoveryServiceCandidate
    from physicalSoftware::adapter::aaosDiscovery
    to physicalSoftware::aaosSdvBoundary::serviceDiscovery;

  dependency vsidlSignalToROS2Velocity
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::adapter::ros2VelocityOut;
  dependency ros2AutowareStateToVSIDLLifecycle
    from physicalSoftware::adapter::ros2AutowareStateIn
    to physicalSoftware::adapter::aaosLifecycle;
  dependency vsidlDiagnosticsToROS2Diagnostics
    from physicalSoftware::adapter::aaosDiagnostics
    to physicalSoftware::adapter::ros2DiagnosticsOut;

  dependency aaosVSIDLSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::vsidlProviderSource;
  dependency aaosMiddlewareSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::middlewareSource;
  dependency aaosHardwareInterfacesSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::hardwareInterfacesSource;
  dependency aaosLifecycleSourceTrace
    from physicalSoftware::aaosSdvBoundary::lifecycleManager
    to physicalSoftware::lifecycleServiceSource;
  dependency aaosHealthSourceTrace
    from physicalSoftware::aaosSdvBoundary::healthMonitor
    to physicalSoftware::healthMonitorSource;
  dependency aaosDiagnosticsSourceTrace
    from physicalSoftware::aaosSdvBoundary::diagnostics
    to physicalSoftware::diagnosticsSource;
  dependency aaosAdapterSourceManifestTrace
    from physicalSoftware::adapter
    to physicalSoftware::aaosSourceArtifact;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern physicalInterfaceConcern : PhysicalInterfaceConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern physicalFunctionalMappingConcern : PhysicalFunctionalMappingConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern physicalLogicalMappingConcern : PhysicalLogicalMappingConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view mwPhysicalStructureView {
    viewpoint selectedPhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame physicalStructureConcern;
    }
    expose DE4SDV_MWPhysicalSoftwareRealization::*;
    render asTreeDiagram;
  }

  view mwPhysicalInterfaceView {
    viewpoint selectedPhysicalInterfaceViewpoint : PhysicalInterfaceDefinitionViewpoint {
      frame physicalInterfaceConcern;
    }
    expose DE4SDV_MWPhysicalSoftwareRealization::*;
    render asTreeDiagram;
  }

  view mwPhysicalFunctionalMappingView {
    viewpoint selectedPhysicalFunctionalMappingViewpoint : PhysicalFunctionalMappingViewpoint {
      frame physicalFunctionalMappingConcern;
    }
    expose DE4SDV_MWPhysicalSoftwareRealization::*;
    render asTreeDiagram;
  }

  view mwPhysicalLogicalMappingView {
    viewpoint selectedPhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame physicalLogicalMappingConcern;
    }
    expose DE4SDV_MWPhysicalSoftwareRealization::*;
    render asTreeDiagram;
  }
}
