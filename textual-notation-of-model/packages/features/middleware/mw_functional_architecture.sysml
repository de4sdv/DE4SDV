/*
 * DE4SDV middleware functional architecture model slice.
 *
 * INC-MW-006 defines middleware integration functions, information exchanges,
 * and a functional boundary. It does not allocate functions to logical or
 * physical components, select a middleware implementation, or decide the
 * final safety-path architecture.
 */

package DE4SDV_MWFunctionalArchitecture {
  package Features {
    package Middleware {
      package FunctionalArchitecture {
        private import Views::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::*;
        private import DE4SDV_MWRequirements::Features::Middleware::Requirements::*;
        private import SAF_Viewpoints::*;

        part incMW006 : FeatureIncrement {
          doc /* INC-MW-006: middleware integration functional architecture. */
        }

        part functionalSignalDefinitionGap : DeferredProductLineScope {
          doc /* GAP-MW-013: Functional signal names, units, freshness criteria, and conversion rules are not yet enumerated. */
        }

        part lifecycleVocabularyGap : DeferredProductLineScope {
          doc /* GAP-MW-014: Lifecycle state vocabulary and transition timing are not yet baselined. */
        }

        part safetyPathFunctionalOwnershipGap : DeferredProductLineScope {
          doc /* GAP-MW-015: Functional ownership of safety-path protection remains unresolved until logical architecture and safety analysis. */
        }

        item def VehicleSignalAccessRequest {
          doc /* Functional request for a vehicle signal required by an ADAS application use case. */
        }

        item def VehicleSignalAccessResponse {
          doc /* Functional response containing a vehicle signal value and its health/freshness status. */
        }

        item def DiagnosticAccessRequest {
          doc /* Functional request for middleware or vehicle diagnostic status. */
        }

        item def DiagnosticAccessResponse {
          doc /* Functional diagnostic status returned to the ADAS application. */
        }

        item def LifecycleCoordinationRequest {
          doc /* Functional lifecycle request exchanged between the ADAS application and middleware boundary. */
        }

        item def LifecycleCoordinationStatus {
          doc /* Functional lifecycle state made observable at the integration boundary. */
        }

        item def HealthForwardingStatus {
          doc /* Functional health and availability status forwarded to the ADAS application. */
        }

        item def UpdateCoordinationRequest {
          doc /* Functional request or notification for middleware integration update coordination. */
        }

        item def UpdateCoordinationStatus {
          doc /* Functional status indicating whether an update preserves required integration interfaces. */
        }

        item def ServiceBindingRequest {
          doc /* Functional request to discover and bind a required middleware service. */
        }

        item def ServiceBindingStatus {
          doc /* Functional result of service discovery, authentication, and binding. */
        }

        item def SafetyPathProtectionStatus {
          doc /* Functional status indicating whether non-safety middleware failure is contained at the intervention boundary. */
        }

        action def TranslateVehicleSignal {
          in signalRequest : VehicleSignalAccessRequest;
          out signalResponse : VehicleSignalAccessResponse;
        }

        action def ProxyDiagnosticAccess {
          in diagnosticRequest : DiagnosticAccessRequest;
          out diagnosticResponse : DiagnosticAccessResponse;
        }

        action def CoordinateLifecycle {
          in lifecycleRequest : LifecycleCoordinationRequest;
          out lifecycleStatus : LifecycleCoordinationStatus;

          exhibit state lifecycleStates {
            state uninitialized;
            state initializing;
            state operational;
            state degraded;
            state shuttingDown;
            transition first uninitialized then initializing;
            transition initializing then operational;
            transition operational then degraded;
            transition degraded then operational;
            transition operational then shuttingDown;
            transition degraded then shuttingDown;
          }
        }

        action def ForwardServiceHealth {
          in healthStatus : HealthStatus;
          out forwardedHealth : HealthForwardingStatus;

          exhibit state healthStates {
            state unavailable;
            state degraded;
            state available;
            transition first unavailable then degraded;
            transition degraded then available;
            transition available then degraded;
            transition degraded then unavailable;
          }
        }

        action def CoordinateIntegrationUpdate {
          in updateNotification : UpdateNotification;
          out updateStatus : UpdateCoordinationStatus;
        }

        action def DiscoverAndBindService {
          in bindingRequest : ServiceBindingRequest;
          out bindingStatus : ServiceBindingStatus;

          exhibit state connectionStates {
            state undiscovered;
            state discovered;
            state authenticating;
            state bound;
            state failed;
            transition first undiscovered then discovered;
            transition discovered then authenticating;
            transition authenticating then bound;
            transition discovered then failed;
            transition authenticating then failed;
            transition bound then failed;
            transition failed then discovered;
          }
        }

        action def ProtectEmergencyInterventionPath {
          in middlewareHealth : HealthForwardingStatus;
          in lifecycleStatus : LifecycleCoordinationStatus;
          out safetyPathStatus : SafetyPathProtectionStatus;
        }

        action def MiddlewareIntegrationFunctionalFlow {
          in item signalRequest : VehicleSignalAccessRequest;
          in item diagnosticRequest : DiagnosticAccessRequest;
          in item lifecycleRequest : LifecycleCoordinationRequest;
          in item healthStatus : HealthStatus;
          in item updateNotification : UpdateNotification;
          in item bindingRequest : ServiceBindingRequest;
          out item signalResponse : VehicleSignalAccessResponse;
          out item diagnosticResponse : DiagnosticAccessResponse;
          out item lifecycleStatus : LifecycleCoordinationStatus;
          out item forwardedHealth : HealthForwardingStatus;
          out item updateStatus : UpdateCoordinationStatus;
          out item bindingStatus : ServiceBindingStatus;
          out item safetyPathStatus : SafetyPathProtectionStatus;

          action translateSignal : TranslateVehicleSignal {
            in signalRequest = MiddlewareIntegrationFunctionalFlow::signalRequest;
            out signalResponse = MiddlewareIntegrationFunctionalFlow::signalResponse;
          }
          action proxyDiagnostics : ProxyDiagnosticAccess {
            in diagnosticRequest = MiddlewareIntegrationFunctionalFlow::diagnosticRequest;
            out diagnosticResponse = MiddlewareIntegrationFunctionalFlow::diagnosticResponse;
          }
          action coordinateLifecycle : CoordinateLifecycle {
            in lifecycleRequest = MiddlewareIntegrationFunctionalFlow::lifecycleRequest;
            out lifecycleStatus = MiddlewareIntegrationFunctionalFlow::lifecycleStatus;
          }
          action forwardHealth : ForwardServiceHealth {
            in healthStatus = MiddlewareIntegrationFunctionalFlow::healthStatus;
            out forwardedHealth = MiddlewareIntegrationFunctionalFlow::forwardedHealth;
          }
          action coordinateUpdate : CoordinateIntegrationUpdate {
            in updateNotification = MiddlewareIntegrationFunctionalFlow::updateNotification;
            out updateStatus = MiddlewareIntegrationFunctionalFlow::updateStatus;
          }
          action bindService : DiscoverAndBindService {
            in bindingRequest = MiddlewareIntegrationFunctionalFlow::bindingRequest;
            out bindingStatus = MiddlewareIntegrationFunctionalFlow::bindingStatus;
          }
          action protectSafetyPath : ProtectEmergencyInterventionPath {
            in middlewareHealth = forwardHealth.forwardedHealth;
            in lifecycleStatus = coordinateLifecycle.lifecycleStatus;
            out safetyPathStatus = MiddlewareIntegrationFunctionalFlow::safetyPathStatus;
          }

          first coordinateLifecycle then protectSafetyPath;
          first forwardHealth then protectSafetyPath;
        }

        action middlewareIntegrationFunctionalFlow : MiddlewareIntegrationFunctionalFlow;

        port def VehicleSignalAccessInbound {
          in item signalRequest : VehicleSignalAccessRequest;
        }
        port def VehicleSignalAccessOutbound {
          out item signalResponse : VehicleSignalAccessResponse;
        }
        port def DiagnosticAccessInbound {
          in item diagnosticRequest : DiagnosticAccessRequest;
        }
        port def DiagnosticAccessOutbound {
          out item diagnosticResponse : DiagnosticAccessResponse;
        }
        port def LifecycleCoordinationInbound {
          in item lifecycleRequest : LifecycleCoordinationRequest;
        }
        port def LifecycleCoordinationOutbound {
          out item lifecycleStatus : LifecycleCoordinationStatus;
        }
        port def HealthStatusInbound {
          in item healthStatus : HealthStatus;
        }
        port def HealthStatusOutbound {
          out item forwardedHealth : HealthForwardingStatus;
        }
        port def UpdateCoordinationInbound {
          in item updateNotification : UpdateNotification;
        }
        port def UpdateCoordinationOutbound {
          out item updateStatus : UpdateCoordinationStatus;
        }
        port def ServiceBindingInbound {
          in item bindingRequest : ServiceBindingRequest;
        }
        port def ServiceBindingOutbound {
          out item bindingStatus : ServiceBindingStatus;
        }
        port def SafetyPathStatusOutbound {
          out item safetyPathStatus : SafetyPathProtectionStatus;
        }

        part def MiddlewareFunctionalBoundary {
          port signalAccessIn : VehicleSignalAccessInbound;
          port signalAccessOut : VehicleSignalAccessOutbound;
          port diagnosticAccessIn : DiagnosticAccessInbound;
          port diagnosticAccessOut : DiagnosticAccessOutbound;
          port lifecycleIn : LifecycleCoordinationInbound;
          port lifecycleOut : LifecycleCoordinationOutbound;
          port healthIn : HealthStatusInbound;
          port healthOut : HealthStatusOutbound;
          port updateIn : UpdateCoordinationInbound;
          port updateOut : UpdateCoordinationOutbound;
          port serviceBindingIn : ServiceBindingInbound;
          port serviceBindingOut : ServiceBindingOutbound;
          port safetyPathOut : SafetyPathStatusOutbound;

          perform middlewareIntegrationFunctionalFlow : MiddlewareIntegrationFunctionalFlow {
            in item signalRequest = signalAccessIn.signalRequest;
            in item diagnosticRequest = diagnosticAccessIn.diagnosticRequest;
            in item lifecycleRequest = lifecycleIn.lifecycleRequest;
            in item healthStatus = healthIn.healthStatus;
            in item updateNotification = updateIn.updateNotification;
            in item bindingRequest = serviceBindingIn.bindingRequest;
            out item signalResponse = signalAccessOut.signalResponse;
            out item diagnosticResponse = diagnosticAccessOut.diagnosticResponse;
            out item lifecycleStatus = lifecycleOut.lifecycleStatus;
            out item forwardedHealth = healthOut.forwardedHealth;
            out item updateStatus = updateOut.updateStatus;
            out item bindingStatus = serviceBindingOut.bindingStatus;
            out item safetyPathStatus = safetyPathOut.safetyPathStatus;
          }
        }

        part middlewareFunctionalBoundary : MiddlewareFunctionalBoundary;

        dependency functionalSignalAccessDerivedFromRequirement
          from TranslateVehicleSignal
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideMiddlewareSignalAccess;
        dependency functionalDiagnosticAccessDerivedFromRequirement
          from ProxyDiagnosticAccess
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideMiddlewareDiagnosticAccess;
        dependency functionalLifecycleDerivedFromRequirement
          from CoordinateLifecycle
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqCoordinateMiddlewareLifecycle;
        dependency functionalHealthDerivedFromRequirement
          from ForwardServiceHealth
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqMonitorMiddlewareHealth;
        dependency functionalUpdateDerivedFromRequirement
          from CoordinateIntegrationUpdate
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqCoordinateMiddlewareUpdates;
        dependency functionalSafetyPathDerivedFromRequirement
          from ProtectEmergencyInterventionPath
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqIsolateSafetyPath;
        dependency functionalBindingDerivedFromRequirement
          from DiscoverAndBindService
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqProvideServiceDiscovery;
        dependency functionalAuthenticationBoundaryDerivedFromRequirement
          from DiscoverAndBindService
          to DE4SDV_MWRequirements::Features::Middleware::Requirements::reqAuthenticateServiceBinding;

        concern functionalBehaviorConcern : FunctionalBehaviorConcern {
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }
        concern functionalInterfaceConcern : FunctionalInterfaceConcern {
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }
        concern functionalProcessConcern : SystemProcessConcern {
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view mwFunctionalBehaviorView {
          viewpoint selectedFunctionalBehaviorViewpoint : SystemFunctionalBreakdownStructureViewpoint {
            frame functionalBehaviorConcern;
          }
          expose FunctionalArchitecture::*;
          render asTreeDiagram;
        }
        view mwFunctionalInterfaceView {
          viewpoint selectedFunctionalInterfaceViewpoint : SystemInterfaceDefinitionViewpoint {
            frame functionalInterfaceConcern;
          }
          expose FunctionalArchitecture::*;
          render asTreeDiagram;
        }
        view mwFunctionalProcessView {
          viewpoint selectedFunctionalProcessViewpoint : SystemProcessViewpoint {
            frame functionalProcessConcern;
          }
          expose FunctionalArchitecture::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
