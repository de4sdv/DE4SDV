/*
 * DE4SDV middleware operational context model slice.
 *
 * INC-MW-002 models the operational world for middleware integration only: no
 * AAOS SDV, Eclipse S-CORE, or AUTOSAR implementation details; no adapter
 * functional behavior; no logical realization; and no physical/software
 * realization.
 */

package DE4SDV_MWOperationalContext {
  package Features {
    package Middleware {
      package OperationalContext {
        private import DE4SDV_Stakeholders::*;
        private import SAF_Viewpoints::*;
        private import Views::*;
        private import COVESA_VSS::*;
        private import DE4SDV_VSS_Extensions::*;

        item def LifecycleCommand {
          doc /* Start, stop, suspend, resume, and shutdown command bundle from the middleware lifecycle manager. */
        }

        item def HealthStatus {
          doc /* Health and availability status forwarded from middleware to the ADAS application. */
        }

        item def UpdateNotification {
          doc /* Over-the-air update coordination and notification data. */
        }

        part def MiddlewareIntegratedVehicleSystem;
        part def ADASApplicationStack :> Stakeholder;
        part def VehiclePlatformMiddleware :> Stakeholder;
        part def ApplicationMiddlewareAdapter :> Stakeholder;
        part def DiagnosticTechnician :> Stakeholder;
        part def OTAUpdateCoordinator :> Stakeholder;
        part def AEBNode :> Stakeholder;
        part def VehicleCommandGate :> Stakeholder;

        action def ExchangeVehicleSignals {
          doc /* ADAS application consumes vehicle speed, yaw rate, longitudinal acceleration, and steering angle from middleware. */
          out vehicleSpeed : Vehicle_Speed;
          out vehicleAngularVelocityYaw : Vehicle_AngularVelocity_Yaw;
          out vehicleAccelerationLongitudinal : Vehicle_Acceleration_Longitudinal;
          out vehicleChassisSteeringWheelAngle : Vehicle_Chassis_SteeringWheel_Angle;
        }

        action def CoordinateLifecycle {
          doc /* Middleware lifecycle manager sends lifecycle commands to the ADAS application through the adapter. */
          in lifecycleCommand : LifecycleCommand;
        }

        action def MonitorHealth {
          doc /* Middleware health monitor detects service failures, and the adapter forwards health status to the ADAS application. */
          in healthStatus : HealthStatus;
          in aebsError : Vehicle_ADAS_AEBS_IsError;
          in aebsFailureIndication : Vehicle_ADAS_AEBS_FailureIndication_IsActive;
        }

        action def AccessDiagnostics {
          doc /* Diagnostic technician accesses diagnostic data through middleware. */
          in diagnosticState : Vehicle_ADAS_AEBS_IsError;
        }

        action def CoordinateUpdate {
          doc /* OTA update coordinator initiates software update through middleware. */
          in updateNotification : UpdateNotification;
        }

        action def EmergencyInterventionDirect {
          doc /* AEB node issues emergency braking directly to the vehicle command gate, explicitly bypassing middleware. */
          out emergencyBrakingCommand : Vehicle_ADAS_AEBS_EmergencyBraking_IsCommanded;
        }

        action def MiddlewareIntegrationOperationalFlow {
          doc /* Operational flow for the middleware-mediated interactions; the emergency path is modeled separately as a direct bypass. */
          in item vehicleSpeed : Vehicle_Speed;
          in item vehicleAngularVelocityYaw : Vehicle_AngularVelocity_Yaw;
          in item vehicleAccelerationLongitudinal : Vehicle_Acceleration_Longitudinal;
          in item vehicleChassisSteeringWheelAngle : Vehicle_Chassis_SteeringWheel_Angle;
          in item lifecycleCommand : LifecycleCommand;
          in item healthStatus : HealthStatus;
          in item aebsError : Vehicle_ADAS_AEBS_IsError;
          in item aebsFailureIndication : Vehicle_ADAS_AEBS_FailureIndication_IsActive;
          in item diagnosticState : Vehicle_ADAS_AEBS_IsError;
          in item updateNotification : UpdateNotification;

          action exchangeVehicleSignals : ExchangeVehicleSignals {
            out vehicleSpeed = MiddlewareIntegrationOperationalFlow::vehicleSpeed;
            out vehicleAngularVelocityYaw = MiddlewareIntegrationOperationalFlow::vehicleAngularVelocityYaw;
            out vehicleAccelerationLongitudinal = MiddlewareIntegrationOperationalFlow::vehicleAccelerationLongitudinal;
            out vehicleChassisSteeringWheelAngle = MiddlewareIntegrationOperationalFlow::vehicleChassisSteeringWheelAngle;
          }

          action coordinateLifecycle : CoordinateLifecycle {
            in lifecycleCommand = MiddlewareIntegrationOperationalFlow::lifecycleCommand;
          }

          action monitorHealth : MonitorHealth {
            in healthStatus = MiddlewareIntegrationOperationalFlow::healthStatus;
            in aebsError = MiddlewareIntegrationOperationalFlow::aebsError;
            in aebsFailureIndication = MiddlewareIntegrationOperationalFlow::aebsFailureIndication;
          }

          action accessDiagnostics : AccessDiagnostics {
            in diagnosticState = MiddlewareIntegrationOperationalFlow::diagnosticState;
          }

          action coordinateUpdate : CoordinateUpdate {
            in updateNotification = MiddlewareIntegrationOperationalFlow::updateNotification;
          }

          first exchangeVehicleSignals then coordinateLifecycle;
          first coordinateLifecycle then monitorHealth;
          first monitorHealth then accessDiagnostics;
          first accessDiagnostics then coordinateUpdate;
        }

        part middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
        part adasApplicationStack : ADASApplicationStack;
        part vehiclePlatformMiddleware : VehiclePlatformMiddleware;
        part applicationMiddlewareAdapter : ApplicationMiddlewareAdapter;
        part diagnosticTechnician : DiagnosticTechnician;
        part otaUpdateCoordinator : OTAUpdateCoordinator;
        part aebNode : AEBNode;
        part vehicleCommandGate : VehicleCommandGate;

        use case def MiddlewareIntegrationOperationalStory {
          subject subjectSystem : MiddlewareIntegratedVehicleSystem;
          actor adasApplicationStack : ADASApplicationStack;
          actor vehiclePlatformMiddleware : VehiclePlatformMiddleware;
          actor applicationMiddlewareAdapter : ApplicationMiddlewareAdapter;
          actor diagnosticTechnician : DiagnosticTechnician;
          actor otaUpdateCoordinator : OTAUpdateCoordinator;
          actor aebNode : AEBNode;
          actor vehicleCommandGate : VehicleCommandGate;

          objective {
            doc /*
             * Establish the operational story for middleware integration. The
             * middleware-mediated story covers vehicle signal exchange, lifecycle
             * coordination, health monitoring, diagnostic access, and update
             * coordination. The emergency intervention path (SCN-MW-006) is a
             * separate direct action from the AEB node to the vehicle command gate
             * and does NOT go through middleware.
             */
          }
        }

        use case middlewareIntegrationOperationalStory : MiddlewareIntegrationOperationalStory {
          subject subjectSystem = OperationalContext::middlewareIntegratedVehicleSystem;
          actor adasApplicationStack = OperationalContext::adasApplicationStack;
          actor vehiclePlatformMiddleware = OperationalContext::vehiclePlatformMiddleware;
          actor applicationMiddlewareAdapter = OperationalContext::applicationMiddlewareAdapter;
          actor diagnosticTechnician = OperationalContext::diagnosticTechnician;
          actor otaUpdateCoordinator = OperationalContext::otaUpdateCoordinator;
          actor aebNode = OperationalContext::aebNode;
          actor vehicleCommandGate = OperationalContext::vehicleCommandGate;
        }

        action middlewareIntegrationOperationalFlow : MiddlewareIntegrationOperationalFlow;
        action emergencyInterventionDirectScenario : EmergencyInterventionDirect;

        concern operationalContextConcern : OperationalContextConcern {
          doc /*
           * Reviewers need the operational actors, context boundary, and the
           * middleware-mediated operational flow visible for this increment.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        concern operationalStoryConcern : OperationalStoryConcern {
          doc /*
           * Reviewers need the operational story to show both the middleware
           * interaction scenarios and the direct emergency boundary case.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view mwOperationalContextView {
          viewpoint selectedOperationalContextViewpoint : OperationalContextDefinitionViewpoint {
            frame operationalContextConcern;
          }

          expose OperationalContext::*;
          render asTreeDiagram;
        }

        view mwOperationalStoryView {
          viewpoint selectedOperationalStoryViewpoint : OperationalStoryViewpoint {
            frame operationalStoryConcern;
          }

          expose OperationalContext::*;
          render asTreeDiagram;
        }

        concern operationalCapabilityConcern : OperationalCapabilityConcern {
          doc /*
           * Reviewers need the operational capability expected from the
           * middleware integration to be described: the system shall be
           * able to exchange vehicle signals, diagnostics, lifecycle
           * coordination, and health status between an ADAS application
           * and a vehicle-level platform middleware.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view mwOperationalCapabilityView {
          viewpoint selectedOperationalCapabilityViewpoint : OperationalCapabilityDefinitionViewpoint {
            frame operationalCapabilityConcern;
          }

          expose OperationalContext::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
