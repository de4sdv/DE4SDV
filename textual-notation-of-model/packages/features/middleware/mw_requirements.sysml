/*
 * DE4SDV middleware design-input requirement model slice.
 *
 * INC-MW-005 derives draft, verifiable requirement candidates from the
 * stakeholder needs in INC-MW-004. This slice does not define functional,
 * logical, or physical architecture; those follow in INC-MW-006 through
 * INC-MW-008.
 */

package DE4SDV_MWRequirements {
  package Features {
    package Middleware {
      package Requirements {
        private import Views::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;
        private import DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::*;
        private import DE4SDV_MWFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::*;

        requirement def MiddlewareSignalAccessRequirement :> FunctionalRequirementCandidate;
        requirement def MiddlewareDiagnosticAccessRequirement :> FunctionalRequirementCandidate;
        requirement def MiddlewareLifecycleCoordinationRequirement :> FunctionalRequirementCandidate;
        requirement def MiddlewareHealthMonitoringRequirement :> FunctionalRequirementCandidate;
        requirement def MiddlewareUpdateCoordinationRequirement :> FunctionalRequirementCandidate;
        requirement def MiddlewareSafetyPathIsolationRequirement :> SafetyConstraintRequirementCandidate;
        requirement def MiddlewareServiceDiscoveryRequirement :> FunctionalRequirementCandidate;
        requirement def MiddlewareServiceAuthenticationRequirement :> SafetyConstraintRequirementCandidate;
        requirement def MiddlewareBoundaryTraceabilityRequirement :> TraceabilityConstraintRequirementCandidate;

        part incMW005 : NeedsRequirementsIncrement {
          doc /* INC-MW-005: middleware integration design-input requirements. */
        }

        package System1Product {
          requirement reqProvideMiddlewareSignalAccess : MiddlewareSignalAccessRequirement {
            doc /* REQ-MW-001 draft design-input requirement. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall provide the ADAS application access to the vehicle signals required by its selected operational use cases through the selected middleware integration boundary. */ }
          }

          requirement reqProvideMiddlewareDiagnosticAccess : MiddlewareDiagnosticAccessRequirement {
            doc /* REQ-MW-002 draft design-input requirement. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall provide the ADAS application access to middleware and vehicle diagnostic status needed to determine the health of the selected integration boundary. */ }
          }

          requirement reqCoordinateMiddlewareLifecycle : MiddlewareLifecycleCoordinationRequirement {
            doc /* REQ-MW-003 draft design-input requirement. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall coordinate middleware integration lifecycle state with the ADAS application so that startup, readiness, degraded operation, and shutdown transitions are observable at the integration boundary. */ }
          }

          requirement reqMonitorMiddlewareHealth : MiddlewareHealthMonitoringRequirement {
            doc /* REQ-MW-004 draft design-input requirement. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall monitor the health of the selected middleware integration boundary and provide an observable indication when a required integration service is stale, missing, inconsistent, or unavailable. */ }
          }

          requirement reqCoordinateMiddlewareUpdates : MiddlewareUpdateCoordinationRequirement {
            doc /* REQ-MW-005 draft design-input requirement. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall coordinate middleware integration updates with the ADAS application lifecycle so that an update does not silently invalidate required signal, diagnostic, lifecycle, or health interfaces. */ }
          }

          requirement reqIsolateSafetyPath : MiddlewareSafetyPathIsolationRequirement {
            doc /* REQ-MW-006 draft safety-constraint requirement; architecture choice remains open. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall prevent a failure of the non-safety middleware integration path from causing an uncontrolled emergency intervention command, whether the selected realization uses a safety-certified middleware partition or a direct vehicle-command path. */ }
          }

          requirement reqProvideServiceDiscovery : MiddlewareServiceDiscoveryRequirement {
            doc /* REQ-MW-007 draft design-input requirement. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall discover and bind the middleware services required by the selected ADAS application integration configuration before those services are used. */ }
          }

          requirement reqAuthenticateServiceBinding : MiddlewareServiceAuthenticationRequirement {
            doc /* REQ-MW-008 draft safety/security constraint; trust-boundary details remain deferred. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint { doc /* Each SDV product-line member product shall authenticate a middleware service binding before accepting service data or commands across a trust boundary defined for the selected integration configuration. */ }
          }
        }

        package System2EngineeringAssurance {
          requirement reqMaintainMiddlewareBoundaryTraceability : MiddlewareBoundaryTraceabilityRequirement {
            doc /* REQ-MW-009 System 2 traceability requirement. */
            subject increment : NeedsRequirementsIncrement;
            require constraint { doc /* The DE4SDV middleware increment shall maintain trace links from each middleware requirement to its stakeholder need, operational-context source, feature/common-capability classification, unresolved gap, and planned verification record. */ }
          }
        }

        dependency req001DerivedFromNeed001
          from reqProvideMiddlewareSignalAccess
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needMiddlewareIntegration;
        dependency req002DerivedFromNeed001
          from reqProvideMiddlewareDiagnosticAccess
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needMiddlewareIntegration;
        dependency req003DerivedFromNeed001
          from reqCoordinateMiddlewareLifecycle
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needMiddlewareIntegration;
        dependency req004DerivedFromNeed001
          from reqMonitorMiddlewareHealth
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needMiddlewareIntegration;
        dependency req005DerivedFromNeed001
          from reqCoordinateMiddlewareUpdates
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needMiddlewareIntegration;
        dependency req006DerivedFromNeed004
          from reqIsolateSafetyPath
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needSafetyPathIsolation;
        dependency req007DerivedFromNeed002
          from reqProvideServiceDiscovery
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needPlatformDecoupling;
        dependency req008DerivedFromNeed012
          from reqAuthenticateServiceBinding
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::securityTrustBoundaryGap;
        dependency req009DerivedFromNeed006
          from reqMaintainMiddlewareBoundaryTraceability
          to DE4SDV_MWStakeholderNeeds::Features::Middleware::StakeholderNeeds::needTraceabilityToOperationalContext;

        /* Requirement traceability to the operational use cases that justify
         * each requirement (SystemRequirementTraceabilityViewpoint targets:
         * use case, process, context). Each requirement is justified by the
         * operational scenario it enables. */
        dependency req001TracedToExchangeVehicleSignals
          from reqProvideMiddlewareSignalAccess
          to 'exchange vehicle signals';
        dependency req001TracedToTranslateSignalAction
          from reqProvideMiddlewareSignalAccess
          to middlewareIntegrationFunctionalFlow::translateSignal;
        dependency req002TracedToAccessDiagnostics
          from reqProvideMiddlewareDiagnosticAccess
          to 'access diagnostics';
        dependency req002TracedToProxyDiagnosticsAction
          from reqProvideMiddlewareDiagnosticAccess
          to middlewareIntegrationFunctionalFlow::proxyDiagnostics;
        dependency req003TracedToCoordinateLifecycle
          from reqCoordinateMiddlewareLifecycle
          to 'coordinate lifecycle';
        dependency req003TracedToCoordinateLifecycleAction
          from reqCoordinateMiddlewareLifecycle
          to middlewareIntegrationFunctionalFlow::coordinateLifecycle;
        dependency req004TracedToMonitorServiceHealth
          from reqMonitorMiddlewareHealth
          to 'monitor service health';
        dependency req004TracedToForwardHealthAction
          from reqMonitorMiddlewareHealth
          to middlewareIntegrationFunctionalFlow::forwardHealth;
        dependency req005TracedToCoordinateUpdate
          from reqCoordinateMiddlewareUpdates
          to 'coordinate software update';
        dependency req005TracedToCoordinateUpdateAction
          from reqCoordinateMiddlewareUpdates
          to middlewareIntegrationFunctionalFlow::coordinateUpdate;
        dependency req006TracedToEmergencySafetyPath
          from reqIsolateSafetyPath
          to 'emergency intervention via safety path';
        dependency req006TracedToProtectSafetyPathAction
          from reqIsolateSafetyPath
          to middlewareIntegrationFunctionalFlow::protectSafetyPath;
        dependency req007TracedToExchangeVehicleSignals
          from reqProvideServiceDiscovery
          to 'exchange vehicle signals';
        dependency req007TracedToBindServiceAction
          from reqProvideServiceDiscovery
          to middlewareIntegrationFunctionalFlow::bindService;
        dependency req008TracedToExchangeVehicleSignals
          from reqAuthenticateServiceBinding
          to 'exchange vehicle signals';
        dependency req008TracedToBindServiceAction
          from reqAuthenticateServiceBinding
          to middlewareIntegrationFunctionalFlow::bindService;

        public import System1Product::*;
        public import System2EngineeringAssurance::*;

        concern requirementTraceConcern : RequirementTraceConcern {
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder verificationEngineer : VerificationEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view mwSystemRequirementsView {
          viewpoint selectedSystemRequirementsViewpoint : SystemRequirementDefinitionViewpoint {
            frame requirementTraceConcern;
          }
          expose System1Product::*;
          expose System2EngineeringAssurance::*;
          render asTreeDiagram;
        }
        view mwRequirementTraceView : GeneralView {
          viewpoint selectedRequirementTraceViewpoint : SystemRequirementTraceabilityViewpoint {
            frame requirementTraceConcern;
          }
          expose System1Product::*;
          expose System2EngineeringAssurance::*;
          expose DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::'exchange vehicle signals';
          expose DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::'access diagnostics';
          expose DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::'coordinate lifecycle';
          expose DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::'monitor service health';
          expose DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::'coordinate software update';
          expose DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::'emergency intervention via safety path';
          expose DE4SDV_MWFunctionalArchitecture::Features::Middleware::FunctionalArchitecture::middlewareIntegrationFunctionalFlow;
          render asTreeDiagram;
        }
      }
    }
  }
}
