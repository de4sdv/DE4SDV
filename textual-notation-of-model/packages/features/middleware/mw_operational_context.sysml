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
        part def SafetyCertifiedMiddlewarePartition :> VehiclePlatformMiddleware;
        part def ApplicationMiddlewareAdapter :> Stakeholder;
        part def DiagnosticTechnician :> Stakeholder;
        part def OTAUpdateCoordinator :> Stakeholder;
        part def AEBNode :> Stakeholder;
        part def VehicleCommandGate :> Stakeholder;

        use case 'integrate ADAS with vehicle platform' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor adasApplication : ADASApplicationStack;
          actor vehicleMiddleware : VehiclePlatformMiddleware;
          actor adapter : ApplicationMiddlewareAdapter;
          actor diagnosticTechnician : DiagnosticTechnician;
          actor otaCoordinator : OTAUpdateCoordinator;
          actor aebNode : AEBNode;
          actor vehicleCommandGate : VehicleCommandGate;

          objective {
            doc /*
             * Enable safe and managed exchange of vehicle signals, diagnostics,
             * lifecycle, health, and updates between the ADAS application and
             * the vehicle platform.
             *
             * The operational story presents both emergency intervention
             * options — through a safety-certified middleware partition and
             * via a direct vehicle-command path — without deciding between
             * them. The selection is deferred to requirements and logical
             * architecture phases.
             */
          }

          first start;
          then include 'exchange vehicle signals' {
            subject;
            actor :>> adasApplication = 'integrate ADAS with vehicle platform'::adasApplication;
            actor :>> vehicleMiddleware = 'integrate ADAS with vehicle platform'::vehicleMiddleware;
            actor :>> adapter = 'integrate ADAS with vehicle platform'::adapter;
          }
          then include 'coordinate lifecycle' {
            subject;
            actor :>> adasApplication = 'integrate ADAS with vehicle platform'::adasApplication;
            actor :>> vehicleMiddleware = 'integrate ADAS with vehicle platform'::vehicleMiddleware;
            actor :>> adapter = 'integrate ADAS with vehicle platform'::adapter;
          }
          then include 'monitor service health' {
            subject;
            actor :>> adasApplication = 'integrate ADAS with vehicle platform'::adasApplication;
            actor :>> vehicleMiddleware = 'integrate ADAS with vehicle platform'::vehicleMiddleware;
            actor :>> adapter = 'integrate ADAS with vehicle platform'::adapter;
          }
          then include 'access diagnostics' {
            subject;
            actor :>> diagnosticTechnician = 'integrate ADAS with vehicle platform'::diagnosticTechnician;
            actor :>> vehicleMiddleware = 'integrate ADAS with vehicle platform'::vehicleMiddleware;
            actor :>> adapter = 'integrate ADAS with vehicle platform'::adapter;
          }
          then include 'coordinate software update' {
            subject;
            actor :>> otaCoordinator = 'integrate ADAS with vehicle platform'::otaCoordinator;
            actor :>> vehicleMiddleware = 'integrate ADAS with vehicle platform'::vehicleMiddleware;
            actor :>> adapter = 'integrate ADAS with vehicle platform'::adapter;
          }
          then include 'emergency intervention via safety path' [0..1] {
            subject;
            actor :>> aebNode = 'integrate ADAS with vehicle platform'::aebNode;
            actor :>> vehicleCommandGate = 'integrate ADAS with vehicle platform'::vehicleCommandGate;
          }
          then include 'emergency intervention direct path' [0..1] {
            subject;
            actor :>> aebNode = 'integrate ADAS with vehicle platform'::aebNode;
            actor :>> vehicleCommandGate = 'integrate ADAS with vehicle platform'::vehicleCommandGate;
          }
          then done;
        }

        use case 'exchange vehicle signals' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor adasApplication : ADASApplicationStack;
          actor vehicleMiddleware : VehiclePlatformMiddleware;
          actor adapter : ApplicationMiddlewareAdapter;

          objective {
            doc /*
             * Exchange normal-driving vehicle signals through VSS-backed
             * interfaces so the ADAS application can consume vehicle speed,
             * yaw rate, longitudinal acceleration, and steering wheel angle.
             *
             * VSS signal references: Vehicle_Speed,
             * Vehicle_AngularVelocity_Yaw,
             * Vehicle_Acceleration_Longitudinal,
             * Vehicle_Chassis_SteeringWheel_Angle.
             */
          }

          first start;
          then done;
        }

        use case 'coordinate lifecycle' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor adasApplication : ADASApplicationStack;
          actor vehicleMiddleware : VehiclePlatformMiddleware;
          actor adapter : ApplicationMiddlewareAdapter;

          objective {
            doc /*
             * Coordinate vehicle startup and shutdown lifecycle transitions via
             * middleware-managed lifecycle commands.
             *
             * VSS-related lifecycle state and mode transitions are represented
             * through the operational handoff between the ADAS application and
             * the vehicle platform, including init, running, suspend, resume,
             * and shutdown coordination.
             */
          }

          first start;
          then done;
        }

        use case 'monitor service health' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor adasApplication : ADASApplicationStack;
          actor vehicleMiddleware : VehiclePlatformMiddleware;
          actor adapter : ApplicationMiddlewareAdapter;

          objective {
            doc /*
             * Monitor service health and fault conditions so the ADAS
             * application can detect degraded or unavailable middleware
             * services and respond to health status updates.
             *
             * VSS signal references: Vehicle_ADAS_AEBS_IsError,
             * Vehicle_ADAS_AEBS_FailureIndication_IsActive.
             */
          }

          first start;
          then done;
        }

        use case 'access diagnostics' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor diagnosticTechnician : DiagnosticTechnician;
          actor vehicleMiddleware : VehiclePlatformMiddleware;
          actor adapter : ApplicationMiddlewareAdapter;

          objective {
            doc /*
             * Provide authenticated diagnostic access during service so a
             * technician can inspect vehicle and ADAS diagnostic state through
             * middleware-mediated diagnostic services.
             *
             * VSS signal references: Vehicle_ADAS_AEBS_IsError and related
             * diagnostic-state indicators exposed through the platform.
             */
          }

          first start;
          then done;
        }

        use case 'coordinate software update' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor otaCoordinator : OTAUpdateCoordinator;
          actor vehicleMiddleware : VehiclePlatformMiddleware;
          actor adapter : ApplicationMiddlewareAdapter;

          objective {
            doc /*
             * Coordinate over-the-air software updates so the middleware can
             * manage service dependencies, safe vehicle states, partition-aware
             * update sequencing, and rollback consistency.
             */
          }

          first start;
          then done;
        }

        use case 'emergency intervention via safety path' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor aebNode : AEBNode;
          actor vehicleMiddleware : SafetyCertifiedMiddlewarePartition;
          actor vehicleCommandGate : VehicleCommandGate;

          objective {
            doc /*
             * Route emergency braking through a safety-certified middleware
             * partition to maintain unified lifecycle and health monitoring
             * while ensuring safety integrity.
             *
             * This option assumes the middleware path is qualified to the
             * required ASIL level and preserves a single managed operational
             * chain for monitoring and update control.
             */
          }

          first start;
          then done;
        }

        use case 'emergency intervention direct path' {
          subject middlewareIntegratedVehicleSystem : MiddlewareIntegratedVehicleSystem;
          actor aebNode : AEBNode;
          actor vehicleCommandGate : VehicleCommandGate;

          objective {
            doc /*
             * Route emergency braking directly to the vehicle command gate,
             * bypassing the middleware, to minimize latency and avoid
             * dependency on middleware safety qualification.
             *
             * This option creates a parallel communication path and therefore
             * must be assessed later against lifecycle, health, and assurance
             * implications.
             */
          }

          first start;
          then done;
        }

        concern operationalContextConcern : OperationalContextConcern {
          doc /*
           * Reviewers need the operational actors, context boundary, and both
           * emergency path options visible for this increment.
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

        concern operationalStoryConcern : OperationalStoryConcern {
          doc /*
           * Reviewers need the operational story to show vehicle signal
           * exchange, lifecycle, health, diagnostics, updates, and both
           * emergency intervention options.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
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
           * middleware integration to be described: the system shall be able
           * to exchange vehicle signals, diagnostics, lifecycle coordination,
           * health status, and software updates between an ADAS application
           * and a vehicle-level platform middleware, while presenting both
           * emergency intervention options instead of pre-deciding the path.
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
