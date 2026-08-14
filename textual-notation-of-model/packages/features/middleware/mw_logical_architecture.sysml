/*
 * DE4SDV middleware logical architecture model slice.
 *
 * INC-MW-007 allocates the technology-neutral middleware functions to logical
 * responsibilities and defines their internal exchanges. It does not select
 * ROS 2, DDS, AAOS SDV, S-CORE, AUTOSAR, processes, ECUs, networks, or a
 * physical deployment. The emergency intervention command path remains
 * outside this middleware logical architecture; only its health/protection
 * status is represented here.
 */

package DE4SDV_MWLogicalArchitecture {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::*;
  private import DE4SDV_MWFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::*;
  private import DE4SDV_MWRequirements::Features::Middleware::Requirements::*;
  private import DE4SDV_AEBSLogicalArchitecture::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part incMW007 : FeatureIncrement {
    doc /* INC-MW-007: middleware integration logical architecture. */
  }

  part logicalSignalDefinitionGap : DeferredProductLineScope {
    doc /* GAP-MW-016: Logical signal contracts remain nominal until signal identity, units, freshness, and conversion rules are baselined. */
  }

  part logicalServiceContractGap : DeferredProductLineScope {
    doc /* GAP-MW-017: Logical service discovery, authentication, and binding contracts remain technology-neutral and incomplete until physical interface selection. */
  }

  part logicalSafetyOwnershipGap : DeferredProductLineScope {
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
    doc /* Logical responsibility for translating and exposing vehicle-signal access without selecting a signal schema or transport. */
    port application : SignalAccessApplicationPort;
  }

  part def DiagnosticProxy {
    doc /* Logical responsibility for proxying diagnostic requests and responses across the middleware boundary. */
    port application : DiagnosticApplicationPort;
  }

  part def LifecycleBridge {
    doc /* Logical responsibility for coordinating application-visible lifecycle state with middleware lifecycle state. */
    port application : LifecycleApplicationPort;
  }

  part def HealthProxy {
    doc /* Logical responsibility for forwarding service health and availability status. */
    port application : HealthApplicationPort;
    port safetyObservation : SafetyPathObservationPort;
    exhibit state healthStates {
      state unavailable;
      state degraded;
      state available;
    }
  }

  part def UpdateCoordinator {
    doc /* Logical responsibility for coordinating integration updates without selecting an update mechanism. */
    port application : UpdateApplicationPort;
  }

  part def ServiceBindingManager {
    doc /* Logical responsibility for service discovery, authentication boundary handling, and service binding. */
    port application : ServiceBindingApplicationPort;
  }

  part def MiddlewareLogicalSystem {
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
  part logicalSystem : MiddlewareLogicalSystem;

  allocation def FunctionalToLogicalResponsibility;

  allocation signalTranslationAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow::translateSignal
    to logicalSystem.signalTranslator;
  allocation diagnosticProxyAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow::proxyDiagnostics
    to logicalSystem.diagnosticProxy;
  allocation lifecycleBridgeAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow::coordinateLifecycle
    to logicalSystem.lifecycleBridge;
  allocation healthProxyAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow::forwardHealth
    to logicalSystem.healthProxy;
  allocation updateCoordinatorAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow::coordinateUpdate
    to logicalSystem.updateCoordinator;
  allocation serviceBindingAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow::bindService
    to logicalSystem.serviceBindingManager;
  allocation safetyPathObservationAllocation : FunctionalToLogicalResponsibility
    allocate functionalFlow::protectSafetyPath
    to logicalSystem.healthProxy;

  dependency signalTranslatorDerivedFromRequirement
    from logicalSystem::signalTranslator
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideMiddlewareSignalAccess;
  dependency diagnosticProxyDerivedFromRequirement
    from logicalSystem::diagnosticProxy
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideMiddlewareDiagnosticAccess;
  dependency lifecycleBridgeDerivedFromRequirement
    from logicalSystem::lifecycleBridge
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqCoordinateMiddlewareLifecycle;
  dependency healthProxyDerivedFromRequirement
    from logicalSystem::healthProxy
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqMonitorMiddlewareHealth;
  dependency updateCoordinatorDerivedFromRequirement
    from logicalSystem::updateCoordinator
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqCoordinateMiddlewareUpdates;
  dependency serviceBindingDerivedFromRequirement
    from logicalSystem::serviceBindingManager
    to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideServiceDiscovery;

  dependency aebsVehicleMotionDependsOnSignalTranslator
    from DE4SDV_AEBSLogicalArchitecture::logicalSystem::vehicleMotionObservationIn
    to logicalSystem::signalTranslator;
  dependency aebsTargetObservationDependsOnSignalTranslator
    from DE4SDV_AEBSLogicalArchitecture::logicalSystem::targetObservationIn
    to logicalSystem::signalTranslator;
  dependency aebsDriverOverrideDependsOnSignalTranslator
    from DE4SDV_AEBSLogicalArchitecture::logicalSystem::driverOverrideObservationIn
    to logicalSystem::signalTranslator;
  dependency aebsOperatingContextDependsOnLifecycleBridge
    from DE4SDV_AEBSLogicalArchitecture::logicalSystem::operatingContextIn
    to logicalSystem::lifecycleBridge;
  dependency aebsHealthStatusDependsOnHealthProxy
    from DE4SDV_AEBSLogicalArchitecture::logicalSystem::subsystemHealthIn
    to logicalSystem::healthProxy;

  concern systemStructureConcern : SystemStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern systemInternalExchangeConcern : SystemInternalExchangeConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern systemFunctionMappingConcern : SystemFunctionMappingConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view mwSystemStructureView {
    viewpoint selectedSystemStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame systemStructureConcern;
    }
    expose DE4SDV_MWLogicalArchitecture::*;
    render asTreeDiagram;
  }

  view mwSystemInternalExchangeView {
    viewpoint selectedSystemInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame systemInternalExchangeConcern;
    }
    expose DE4SDV_MWLogicalArchitecture::*;
    render asTreeDiagram;
  }

  view mwSystemFunctionMappingView {
    viewpoint selectedSystemFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame systemFunctionMappingConcern;
    }
    expose DE4SDV_MWLogicalArchitecture::*;
    render asTreeDiagram;
  }
}
