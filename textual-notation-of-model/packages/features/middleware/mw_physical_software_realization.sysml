/*
 * DE4SDV middleware physical/software realization model slice.
 *
 * INC-MW-008 maps the middleware logical responsibilities to a concrete
 * candidate software/platform boundary: the Autoware-to-AAOS SDV adapter and
 * the AAOS SDV boundary model. This is a model of the integration boundary,
 * not a vendored AAOS implementation and not middleware runtime evidence.
 * A bounded AAOS/Cuttlefish build-and-boot observation is retained as
 * enabling-system evidence in the companion record; it does not establish
 * framework, service, adapter, ROS 2, Autoware, or vehicle interoperability.
 *
 * The adapter and AAOS boundary remain candidate realizations. The selected
 * Autoware ROS 2 topic and AOSP SDV gateway/middleware source artifacts are
 * pinned; the vehicle-velocity VSIDL service bundle, process deployment, and
 * executable behavior remain deferred until their source contracts are pinned.
 */

package DE4SDV_MWPhysicalSoftwareRealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ExecutionEnvironments::*;
  private import DE4SDV_MWLogicalArchitecture::*;
  private import DE4SDV_SDVPlatformStack::*;
  private import DE4SDV_AAOSSDVMiddlewareBoundary::*;
  private import DE4SDV_AEBSPhysicalSoftwareRealization::*;
  private import DE4SDV_ROS2Types::*;
  private import COVESA_VSS::**;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part incMW008 : FeatureIncrement {
    doc /* INC-MW-008: middleware integration physical/software realization. */
  }

  part physicalSourceContractGap : DeferredProductLineScope {
    doc /* GAP-MW-019: The Autoware ROS 2 topic and AOSP SDV transport sources are pinned, but the selected vehicle-velocity VSIDL/service-bundle schema and its generated client contract are not. */
  }

  part physicalProcessDeploymentGap : DeferredProductLineScope {
    doc /* GAP-MW-020: Adapter process, executor, runtime, VM, and network deployment are not selected in this realization slice. */
  }

  part physicalServiceSatisfactionGap : DeferredProductLineScope {
    doc /* GAP-MW-021: The candidate AAOS SDV boundary has not been shown to satisfy the logical service responsibilities or requirements. */
  }

  part physicalEnablingSystemGap : DeferredProductLineScope {
    doc /*
     * GAP-MW-023: The candidate AAOS build/runtime enabling environment has
     * not yet passed a readiness probe for the resource envelope, Linux
     * execution, storage, quota, and nested-KVM requirements.
     */
  }

  part velocitySignalContractGap : DeferredProductLineScope {
    doc /* GAP-MW-022: The pinned public AOSP SDV tree provides gateway, service-discovery, data-tunnel, RPC-agent, and transport interfaces, but does not provide the selected production vehicle-velocity VSIDL service bundle, FQIN, payload contract, or generated client binding. The DE4SDV reference payload and VSIDL catalog remain candidates only. */
  }

  part def AAOSSDVSourceArtifact {
    doc /*
     * Source ID: AOSP-AAOS-SDV-MANIFEST.
     * Pinned AOSP source manifest and build target for the AAOS SDV build.
     * Detailed repository, revision, branch, and path provenance is maintained
     * in the INC-MW-008 pilot source_alignment record.
     */
  }

  part def COVESAVehicleSpeedSemanticSource {
    doc /*
     * Source ID: COVESA-VSS-VEHICLE-SPEED.
     * Source-backed semantic definition for VSS Vehicle.Speed. This is the
     * canonical vehicle-speed meaning used between the AAOS contract and the
     * Autoware ROS 2 representation; it is not an AAOS VSIDL service contract.
     * VSS path: Vehicle.Speed; quantity: speed; unit: km/h.
     * The canonical field/unit transformation is recorded by mapping
     * VSS-SIM-AEBS-001 in
     * methodologies/sysmod-sysmlv2/pilots/aebs-simulation-deployment/
     * vss-simulation-realization.yaml; this increment traces that mapping
     * rather than redefining it.
     */
  }

  part def DE4SDVVSSVehicleSpeedAdapterSource {
    doc /*
     * Source ID: DE4SDV-VSS-VEHICLE-SPEED-ADAPTER.
     * Source-backed DE4SDV provider-neutral adapter implementation.
     * This implementation normalizes VSS Vehicle.Speed [km/h] to a
     * provider-neutral longitudinal velocity [m/s]. It does not claim AAOS,
     * VSIDL, ROS 2, transport, deployment, or runtime interoperability.
     */
  }

  part def DE4SDVAAOSSDVReferenceInteropBenchSource {
    doc /*
     * Source ID: DE4SDV-AAOS-SDV-REFERENCE-INTEROP-BENCH.
     * Source-backed DE4SDV-owned reference contract and executable rehearsal.
     * The reference protobuf message is `VehicleSpeed` with the semantic
     * field `speed_kmh`; the companion VSIDL catalog identifies the
     * `DE4SDVVehicleSpeedProvider` publisher, `VehicleSpeed` message, and
     * `VEHICLE_SPEED` channel. These artifacts define a reference contract
     * candidate, not a selected OEM or production AAOS service.
     * The rehearsal proves the DE4SDV reference contract and independent
     * observer path. AAOS runtime interoperability remains pending an AOSP
     * SDV target and generated VSIDL binding.
     */
  }

  item def DE4SDVReferenceVehicleSpeedPayload {
    doc /*
     * Candidate semantic payload slice for the DE4SDV-owned reference
     * contract. `speed_kmh` is the explicit identity mapping from COVESA VSS
     * `Vehicle.Speed` [km/h]. The reference protobuf also carries timestamp
     * and quality fields; their semantics remain outside this signal slice
     * until they are separately mapped.
     */
    attribute speed_kmh : Vehicle_Speed;
  }

  port def DE4SDVReferenceVehicleSpeedAccessPort :> VehicleSignalAccessPort {
    doc /*
     * Candidate typed AAOS-side access port for the reference vehicle-speed
     * slice. The type binds the current signal boundary to the reference
     * payload without selecting a production VSIDL service, generated
     * binding, deployment, or runtime transport.
     */
    inout item vehicleSpeed : DE4SDVReferenceVehicleSpeedPayload redefines vehicleSignals;
  }

  part def AAOSVSIDLProviderAgentSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-VSIDL.
     * VSIDL provider agent from
     * system/software_defined_vehicle/vsidl/provider/agent/sdv. The pinned
     * implementation exposes metadata RPCs including diagnostics declaration,
     * message descriptor, publication descriptor, and RPC method descriptor.
     */
  }

  part def AAOSMiddlewareSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-MIDDLEWARE.
     * Source-backed AAOS SDV middleware communication implementation from
     * system/software_defined_vehicle/middleware.
     * The pinned source provides the middleware communication boundary.
     */
  }

  part def AAOSHardwareSDVInterfacesSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-INTERFACES.
     * Source-backed hardware/sdv interface definitions for middleware,
     * lifecycle, service discovery, RPC, and data-tunnel boundaries.
     */
  }

  part def AAOSSDVGatewaySessionSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-INTERFACES.
     * Source-backed AAOS SDV gateway session interface. It exposes
     * serviceDiscoveryAgent(), dataTunnelAgent(), createPublication(), and
     * findRpcServerByName().
     */
  }

  part def AAOSSDVDataTunnelPublicationSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-INTERFACES.
     * Source-backed AAOS SDV data-tunnel publication interface. It exposes
     * publication ownership and publisher metadata at the gateway boundary.
     */
  }

  part def AAOSSDVRpcAgentSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-MIDDLEWARE.
     * Source-backed AAOS SDV RPC-agent implementation. It registers RPC
     * servers and transport metadata with the SDV middleware.
     */
  }

  part def AAOSLifecycleServiceSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-LIFECYCLE.
     * Source-backed lifecycle-management project at
     * system/software_defined_vehicle/lifecycle_management.
     */
  }

  part def AAOSHealthMonitorSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-HEALTH.
     * Source-backed health-monitor project at
     * system/software_defined_vehicle/health_monitor.
     */
  }

  part def AAOSDiagnosticsSource {
    doc /*
     * Source ID: AOSP-AAOS-SDV-DIAGNOSTICS.
     * Source-backed automotive diagnostics project at
     * system/software_defined_vehicle/automotive_services, relevant source
     * area: diagnostics.
     */
  }

  part def SignalAccessClient {
    doc /* Candidate generic physical/software client for vehicle signal access through the selected adapter and platform boundary. Concrete signal slices specialize the adapter endpoint and retain their own mapping records. */
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
     * boundaries; concrete production ROS 2 topic and VSIDL schemas remain
     * controlled by GAP-MW-019 and GAP-MW-022 until reviewed source revisions
     * are pinned. The typed vehicle-speed port below is a DE4SDV reference
     * contract candidate, not that production binding.
     */
    port applicationSignal : SignalAccessApplicationPort;
    port applicationDiagnostics : DiagnosticApplicationPort;
    port applicationLifecycle : LifecycleApplicationPort;
    port applicationHealth : HealthApplicationPort;
    port applicationUpdate : UpdateApplicationPort;
    port applicationDiscovery : ServiceBindingApplicationPort;

    port aaosSignal : DE4SDVReferenceVehicleSpeedAccessPort;
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
    ref part aaosSourceArtifact : AAOSSDVSourceArtifact;
    ref part vssVehicleSpeedSource : COVESAVehicleSpeedSemanticSource;
    ref part de4sdvVehicleSpeedAdapterSource : DE4SDVVSSVehicleSpeedAdapterSource;
    ref part referenceInteropBenchSource : DE4SDVAAOSSDVReferenceInteropBenchSource;
    ref part vsidlProviderSource : AAOSVSIDLProviderAgentSource;
    ref part middlewareSource : AAOSMiddlewareSource;
    ref part hardwareInterfacesSource : AAOSHardwareSDVInterfacesSource;
    ref part gatewaySessionSource : AAOSSDVGatewaySessionSource;
    ref part dataTunnelPublicationSource : AAOSSDVDataTunnelPublicationSource;
    ref part rpcAgentSource : AAOSSDVRpcAgentSource;
    ref part lifecycleServiceSource : AAOSLifecycleServiceSource;
    ref part healthMonitorSource : AAOSHealthMonitorSource;
    ref part diagnosticsSource : AAOSDiagnosticsSource;

    part signalAccessClient : SignalAccessClient;
    part diagnosticAccessClient : DiagnosticAccessClient;
    part lifecycleClient : LifecycleClient;
    part healthClient : HealthClient;
    part updateClient : UpdateClient;
    part serviceDiscoveryClient : ServiceDiscoveryClient;
  }

  part physicalSoftware : MiddlewarePhysicalSoftwareBoundary;

  part aaosBuildRuntimeEnvironmentCandidate : AOSPAAOSBuildRuntimeEnvironment {
    doc /*
     * Planned System 2 enabling-system candidate for the AAOS source/build
     * and Cuttlefish attempt. Provider, region, quota, disk, KVM, and access
     * remain unverified; this candidate does not claim AAOS or ROS 2 runtime
     * interoperability.
     */
  }

  allocation def LogicalToPhysicalSoftwareCandidate {
    doc /* Candidate logical-to-physical mapping. This does not imply complete realization, satisfaction, runtime execution, or acceptance. */
  }

  allocation signalTranslatorCandidate : LogicalToPhysicalSoftwareCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::signalTranslator
    to physicalSoftware::signalAccessClient;
  allocation vehicleSpeedLogicalToSoftwareSignalCandidate : LogicalToSoftwareSignalMappingCandidate
    allocate DE4SDV_MWLogicalArchitecture::logicalSystem::signalTranslator
    to physicalSoftware::adapter::aaosSignal::vehicleSpeed;
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
  dependency referenceVehicleSpeedContractTrace
    from physicalSoftware::adapter::aaosSignal::vehicleSpeed
    to physicalSoftware::referenceInteropBenchSource;
  dependency referenceVehicleSpeedVSIDLCandidate
    from physicalSoftware::adapter::aaosSignal::vehicleSpeed
    to physicalSoftware::aaosSdvBoundary::vsidlMiddleware;
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
    from physicalSoftware::adapter::aaosSignal::vehicleSpeed
    to physicalSoftware::adapter::ros2VelocityOut;
  dependency ros2AutowareStateToVSIDLLifecycle
    from physicalSoftware::adapter::ros2AutowareStateIn
    to physicalSoftware::adapter::aaosLifecycle;
  dependency vsidlDiagnosticsToROS2Diagnostics
    from physicalSoftware::adapter::aaosDiagnostics
    to physicalSoftware::adapter::ros2DiagnosticsOut;

  dependency vehicleSpeedSemanticTrace
    from physicalSoftware::adapter::aaosSignal::vehicleSpeed
    to physicalSoftware::vssVehicleSpeedSource;
  dependency de4sdvAdapterImplementationTrace
    from physicalSoftware::adapter
    to physicalSoftware::de4sdvVehicleSpeedAdapterSource;
  dependency referenceInteropBenchTrace
    from physicalSoftware::adapter
    to physicalSoftware::referenceInteropBenchSource;
  dependency aaosVSIDLSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::vsidlProviderSource;
  dependency aaosMiddlewareSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::middlewareSource;
  dependency aaosHardwareInterfacesSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::hardwareInterfacesSource;
  dependency aaosGatewaySessionSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::gatewaySessionSource;
  dependency aaosDataTunnelSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::dataTunnelPublicationSource;
  dependency aaosRpcAgentSourceTrace
    from physicalSoftware::adapter::aaosSignal
    to physicalSoftware::rpcAgentSource;
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
  dependency aaosSourceBuildEnvironmentCandidate
    from physicalSoftware::aaosSourceArtifact
    to aaosBuildRuntimeEnvironmentCandidate;
  dependency aaosCuttlefishEnvironmentCandidate
    from physicalSoftware::aaosSdvBoundary
    to aaosBuildRuntimeEnvironmentCandidate;

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
