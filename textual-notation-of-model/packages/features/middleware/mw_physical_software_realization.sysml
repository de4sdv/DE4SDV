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

  part def MiddlewarePhysicalSoftwareBoundary {
    doc /*
     * Candidate physical/software integration boundary for an Autoware-to-AAOS
     * SDV configuration. The AAOS model is a boundary reference; no internal
     * implementation, deployment, or runtime claim is made.
     */
    part adapter : AutowareToAAOSSDVAdapter;
    part aaosSdvBoundary : SDVCoreBoundary;

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
