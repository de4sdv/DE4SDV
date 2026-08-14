/*
 * DE4SDV middleware system architecture model slice.
 *
 * INC-MW-007 allocates the technology-neutral middleware functions to logical
 * responsibilities and defines their internal exchanges. It does not select
 * ROS 2, DDS, AAOS SDV, S-CORE, AUTOSAR, processes, ECUs, networks, or a
 * physical deployment. The emergency intervention command path remains
 * outside this middleware system architecture; only its health/protection
 * status is represented here.
 */

package DE4SDV_MWConceptualArchitecture {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::*;
  private import DE4SDV_MWFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::*;
  private import DE4SDV_MWRequirements::Features::Middleware::Requirements::*;
  private import DE4SDV_AEBSConceptualArchitecture::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part incMW007 : FeatureIncrement {
    doc /* INC-MW-007: middleware integration system architecture. */
  }

  part systemSignalDefinitionGap : DeferredProductLineScope {
    doc /* GAP-MW-016: Conceptual signal contracts remain nominal until signal identity, units, freshness, and conversion rules are baselined. */
  }

  part systemServiceContractGap : DeferredProductLineScope {
    doc /* GAP-MW-017: System service discovery, authentication, and binding contracts remain technology-neutral and incomplete until physical interface selection. */
  }

  part systemSafetyOwnershipGap : DeferredProductLineScope {
    doc /* GAP-MW-018: Ownership and failure-response semantics for safety-path protection remain open pending safety analysis and physical realization. */
  }

  port def SignalAccessApplicationPort {
    in item signalRequest : VehicleSignalAccessRequest;
    out item signalResponse : VehicleSignalAccessResponse;
  }

  port def DiagnosticApplicationPort {
    in item diagnosticRequest : DiagnosticAccessRequest;
    out item diagnosticResponse : DiagnosticAccessResponse;
  }

  port def LifecycleApplicationPort {
    in item lifecycleRequest : LifecycleCoordinationRequest;
    out item lifecycleStatus : LifecycleCoordinationStatus;
  }

  port def HealthApplicationPort {
    out item forwardedHealth : HealthForwardingStatus;
  }

  port def UpdateApplicationPort {
    in item updateNotification : UpdateNotification;
    out item updateStatus : UpdateCoordinationStatus;
  }

  port def ServiceBindingApplicationPort {
    in item bindingRequest : ServiceBindingRequest;
    out item bindingStatus : ServiceBindingStatus;
  }

  port def SafetyPathObservationPort {
    out item safetyPathStatus : SafetyPathProtectionStatus;
  }

  part def SignalTranslator {
    doc /* Conceptual responsibility for translating and exposing vehicle-signal access without selecting a signal schema or transport. */
    port application : SignalAccessApplicationPort;
  }

  part def DiagnosticProxy {
    doc /* Conceptual responsibility for proxying diagnostic requests and responses across the middleware boundary. */
    port application : DiagnosticApplicationPort;
  }

  part def LifecycleBridge {
    doc /* Conceptual responsibility for coordinating application-visible lifecycle state with middleware lifecycle state. */
    port application : LifecycleApplicationPort;
  }

  part def HealthProxy {
    doc /* Conceptual responsibility for forwarding service health and availability status. */
    port application : HealthApplicationPort;
    port safetyObservation : SafetyPathObservationPort;
    exhibit state healthStates {
      state unavailable;
      state degraded;
      state available;
    }
  }

  part def UpdateCoordinator {
    doc /* Conceptual responsibility for coordinating integration updates without selecting an update mechanism. */
    port application : UpdateApplicationPort;
  }

  part def ServiceBindingManager {
    doc /* Conceptual responsibility for service discovery, authentication boundary handling, and service binding. */
    port application : ServiceBindingApplicationPort;
  }

  part def MiddlewareSystem {
    doc /* Technology-neutral logical composition of the middleware integration responsibilities. */
    port signalAccess : SignalAccessApplicationPort;
    port diagnosticAccess : DiagnosticApplicationPort;
    port lifecycle : LifecycleApplicationPort;
    port health : HealthApplicationPort;
    port update : UpdateApplicationPort;
    port serviceBinding : ServiceBindingApplicationPort;
    port safetyPathObservation : SafetyPathObservationPort;

    part signalTranslator : SignalTranslator;
    part diagnosticProxy : DiagnosticProxy;
    part lifecycleBridge : LifecycleBridge;
    part healthProxy : HealthProxy;
    part updateCoordinator : UpdateCoordinator;
    part serviceBindingManager : ServiceBindingManager;

    exhibit state lifecycleStates {
      state uninitialized;
      state initializing;
      state operational;
      state degraded;
      state shuttingDown;
    }

    bind signalAccess = signalTranslator.application;
    bind diagnosticAccess = diagnosticProxy.application;
    bind lifecycle = lifecycleBridge.application;
    bind health = healthProxy.application;
    bind update = updateCoordinator.application;
    bind serviceBinding = serviceBindingManager.application;
    bind safetyPathObservation = healthProxy.safetyObservation;
  }

  action functionalFlow : MiddlewareIntegrationFunctionalFlow;
  part system : MiddlewareSystem;

  allocation def FunctionalToSystemResponsibility;

  allocation signalTranslationAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow::translateSignal
    to system.signalTranslator;
  allocation diagnosticProxyAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow::proxyDiagnostics
    to system.diagnosticProxy;
  allocation lifecycleBridgeAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow::coordinateLifecycle
    to system.lifecycleBridge;
  allocation healthProxyAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow::forwardHealth
    to system.healthProxy;
  allocation updateCoordinatorAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow::coordinateUpdate
    to system.updateCoordinator;
  allocation serviceBindingAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow::bindService
    to system.serviceBindingManager;
  allocation safetyPathObservationAllocation : FunctionalToSystemResponsibility
    allocate functionalFlow::protectSafetyPath
    to system.healthProxy;

  dependency signalTranslatorDerivedFromRequirement
    from system::signalTranslator
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideMiddlewareSignalAccess;
  dependency diagnosticProxyDerivedFromRequirement
    from system::diagnosticProxy
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideMiddlewareDiagnosticAccess;
  dependency lifecycleBridgeDerivedFromRequirement
    from system::lifecycleBridge
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqCoordinateMiddlewareLifecycle;
  dependency healthProxyDerivedFromRequirement
    from system::healthProxy
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqMonitorMiddlewareHealth;
  dependency updateCoordinatorDerivedFromRequirement
    from system::updateCoordinator
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqCoordinateMiddlewareUpdates;
  dependency serviceBindingDerivedFromRequirement
    from system::serviceBindingManager
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideServiceDiscovery;

  dependency aebsVehicleMotionDependsOnSignalTranslator
    from DE4SDV_AEBSConceptualArchitecture::system::vehicleMotionObservationIn
    to system::signalTranslator;
  dependency aebsTargetObservationDependsOnSignalTranslator
    from DE4SDV_AEBSConceptualArchitecture::system::targetObservationIn
    to system::signalTranslator;
  dependency aebsDriverOverrideDependsOnSignalTranslator
    from DE4SDV_AEBSConceptualArchitecture::system::driverOverrideObservationIn
    to system::signalTranslator;
  dependency aebsOperatingContextDependsOnLifecycleBridge
    from DE4SDV_AEBSConceptualArchitecture::system::operatingContextIn
    to system::lifecycleBridge;
  dependency aebsHealthStatusDependsOnHealthProxy
    from DE4SDV_AEBSConceptualArchitecture::system::subsystemHealthIn
    to system::healthProxy;

  concern conceptualStructureConcern : ConceptualStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern conceptualInternalExchangeConcern : ConceptualInternalExchangeConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern conceptualFunctionMappingConcern : ConceptualFunctionMappingConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view mwSystemStructureView {
    viewpoint selectedSystemStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame conceptualStructureConcern;
    }
    expose DE4SDV_MWConceptualArchitecture::*;
    render asTreeDiagram;
  }

  view mwSystemInternalExchangeView {
    viewpoint selectedSystemInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame conceptualInternalExchangeConcern;
    }
    /*
     * Expose the part-usage subtree, not the package: the interconnection
     * renderer draws part usages with their ports and flow edges; a
     * package-level expose resolves to definitions, which are skipped.
     */
    expose system::*;
    render asInterconnectionDiagram;
  }

  view mwSystemFunctionMappingView {
    viewpoint selectedSystemFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame conceptualFunctionMappingConcern;
    }
    expose DE4SDV_MWConceptualArchitecture::*;
    render asTreeDiagram;
  }
}
