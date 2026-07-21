/*
 * DE4SDV AEBS functional behavior model slice.
 *
 * This package mirrors INC-AEBS-004 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-functional-behavior.yaml.
 * It is a functional-domain slice only: no logical component allocation,
 * physical/software realization, accepted VSS interface mapping, or UNECE R152
 * compliance/type-approval claim is made here.
 *
 * Functional information items reuse generated COVESA VSS signal definitions
 * where available and DE4SDV candidate VSS extension definitions where gaps
 * exist. These signal definitions are semantic catalog references; they are
 * not used here as architecture topology or implementation ownership.
 */

package DE4SDV_AEBSFunctionalBehavior {
  package Features {
    package AEBS {
      package FunctionalBehavior {
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import COVESA_VSS::**;
        private import DE4SDV_VSS_Extensions::**;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;
        private import DE4SDV_Stakeholders::*;
        private import Views::*;

        part incAEBS004 : FeatureIncrement;
        part sdvProductLine : SDVProductLine;
        part memberProduct : ProductLineMemberProduct;
        part aebsCommonCapability : CommonProductLineCapability;

        item def VehicleMotionState {
          doc /* Abstract state needed to reason about subject-vehicle motion for the AEBS vehicle-target slice. */
          attribute vehicleSpeed : Vehicle_Speed;
          attribute longitudinalAcceleration : Vehicle_Acceleration_Longitudinal;
        }

        item def ForwardTargetState {
          doc /* Abstract state of the vehicle target ahead of the subject vehicle. */
          attribute obstacleDistance : Vehicle_ADAS_ObstacleDetection_Distance;
          attribute obstacleTimeGap : Vehicle_ADAS_ObstacleDetection_TimeGap;
        }

        item def CollisionRiskAssessment {
          doc /* Functional assessment that forward collision risk is imminent under selected operating conditions. */
          attribute obstacleWarning : Vehicle_ADAS_ObstacleDetection_IsWarning;
          attribute obstacleWarningType : Vehicle_ADAS_ObstacleDetection_WarningType;
          attribute collisionRiskDetected : Vehicle_ADAS_AEBS_CollisionRisk_IsDetected;
        }

        item def DriverWarningRequest {
          doc /* Functional request to warn the driver when selected warning conditions are met. */
          attribute obstacleWarning : Vehicle_ADAS_ObstacleDetection_IsWarning;
          attribute obstacleWarningType : Vehicle_ADAS_ObstacleDetection_WarningType;
          attribute driverWarningActive : Vehicle_ADAS_AEBS_DriverWarning_IsActive;
        }

        item def DriverOverrideInput {
          doc /* Functional input indicating conscious driver override of AEBS intervention. */
          attribute driverOverrideActive : Vehicle_ADAS_AEBS_DriverOverride_IsActive;
        }

        item def DriverOverrideDecision {
          doc /* Functional decision describing whether conscious driver override prevents or modifies AEBS intervention. */
          attribute driverOverrideActive : Vehicle_ADAS_AEBS_DriverOverride_IsActive;
        }

        item def EmergencyBrakingCommand {
          doc /* Functional command expectation for emergency braking when activation conditions are met and no override prevents intervention. */
          attribute ebaEngaged : Vehicle_ADAS_EBA_IsEngaged;
          attribute brakeLightActive : Vehicle_Body_Lights_Brake_IsActive;
          attribute emergencyBrakingCommanded : Vehicle_ADAS_AEBS_EmergencyBraking_IsCommanded;
        }

        item def AEBSFailureStatus {
          doc /* Functional status indicating detected AEBS-related failure conditions. */
          attribute ebaError : Vehicle_ADAS_EBA_IsError;
          attribute absError : Vehicle_ADAS_ABS_IsError;
          attribute aebsError : Vehicle_ADAS_AEBS_IsError;
        }

        item def FailureIndicationRequest {
          doc /* Functional request to indicate AEBS-related failure without hiding safe-operation concerns. */
          attribute failureIndicationActive : Vehicle_ADAS_AEBS_FailureIndication_IsActive;
        }

        item def AEBSEvidenceEvent {
          doc /* Functional event record seed for later verification, validation, and evidence-baseline work. */
          attribute evidenceEventRecorded : Vehicle_ADAS_AEBS_EvidenceEvent_IsRecorded;
        }

        action def AcquireVehicleAndTargetState {
          out vehicleMotionState : VehicleMotionState;
          out forwardTargetState : ForwardTargetState;
        }

        action def AssessForwardCollisionRisk {
          in vehicleMotionState : VehicleMotionState;
          in forwardTargetState : ForwardTargetState;
          out collisionRiskAssessment : CollisionRiskAssessment;
        }

        action def RequestDriverWarning {
          in collisionRiskAssessment : CollisionRiskAssessment;
          out driverWarningRequest : DriverWarningRequest;
        }

        action def EvaluateDriverOverride {
          in driverOverrideInput : DriverOverrideInput;
          in collisionRiskAssessment : CollisionRiskAssessment;
          out driverOverrideDecision : DriverOverrideDecision;
        }

        action def RequestEmergencyBraking {
          in collisionRiskAssessment : CollisionRiskAssessment;
          in driverOverrideDecision : DriverOverrideDecision;
          out emergencyBrakingCommand : EmergencyBrakingCommand;
        }

        action def MonitorAEBSFailureStatus {
          in aebsFailureStatus : AEBSFailureStatus;
          out failureIndicationRequest : FailureIndicationRequest;
        }

        action def RecordAEBSEvidenceEvent {
          in collisionRiskAssessment : CollisionRiskAssessment;
          in driverWarningRequest : DriverWarningRequest;
          in emergencyBrakingCommand : EmergencyBrakingCommand;
          in failureIndicationRequest : FailureIndicationRequest;
          out aebsEvidenceEvent : AEBSEvidenceEvent;
        }

        action def VehicleTargetAEBSFunctionalFlow {
          in item driverOverrideInput : DriverOverrideInput;
          in item aebsFailureStatus : AEBSFailureStatus;
          out item driverWarningRequest : DriverWarningRequest;
          out item emergencyBrakingCommand : EmergencyBrakingCommand;
          out item failureIndicationRequest : FailureIndicationRequest;
          out item aebsEvidenceEvent : AEBSEvidenceEvent;

          action acquireState : AcquireVehicleAndTargetState {
            out vehicleMotionState;
            out forwardTargetState;
          }

          action assessRisk : AssessForwardCollisionRisk {
            in vehicleMotionState;
            in forwardTargetState;
            out collisionRiskAssessment;
          }

          flow from acquireState.vehicleMotionState to assessRisk.vehicleMotionState;
          flow from acquireState.forwardTargetState to assessRisk.forwardTargetState;
          first acquireState then assessRisk;

          action requestWarning : RequestDriverWarning {
            in collisionRiskAssessment;
            out driverWarningRequest = VehicleTargetAEBSFunctionalFlow::driverWarningRequest;
          }

          flow from assessRisk.collisionRiskAssessment to requestWarning.collisionRiskAssessment;
          first assessRisk then requestWarning;

          action evaluateOverride : EvaluateDriverOverride {
            in driverOverrideInput = VehicleTargetAEBSFunctionalFlow::driverOverrideInput;
            in collisionRiskAssessment;
            out driverOverrideDecision;
          }

          flow from assessRisk.collisionRiskAssessment to evaluateOverride.collisionRiskAssessment;
          first assessRisk then evaluateOverride;

          action requestBraking : RequestEmergencyBraking {
            in collisionRiskAssessment;
            in driverOverrideDecision;
            out emergencyBrakingCommand = VehicleTargetAEBSFunctionalFlow::emergencyBrakingCommand;
          }

          flow from assessRisk.collisionRiskAssessment to requestBraking.collisionRiskAssessment;
          flow from evaluateOverride.driverOverrideDecision to requestBraking.driverOverrideDecision;
          first evaluateOverride then requestBraking;

          action monitorFailure : MonitorAEBSFailureStatus {
            in aebsFailureStatus = VehicleTargetAEBSFunctionalFlow::aebsFailureStatus;
            out failureIndicationRequest = VehicleTargetAEBSFunctionalFlow::failureIndicationRequest;
          }

          action recordEvidence : RecordAEBSEvidenceEvent {
            in collisionRiskAssessment;
            in driverWarningRequest;
            in emergencyBrakingCommand;
            in failureIndicationRequest;
            out aebsEvidenceEvent = VehicleTargetAEBSFunctionalFlow::aebsEvidenceEvent;
          }

          flow from assessRisk.collisionRiskAssessment to recordEvidence.collisionRiskAssessment;
          flow from requestWarning.driverWarningRequest to recordEvidence.driverWarningRequest;
          flow from requestBraking.emergencyBrakingCommand to recordEvidence.emergencyBrakingCommand;
          flow from monitorFailure.failureIndicationRequest to recordEvidence.failureIndicationRequest;
          first requestBraking then recordEvidence;
          first monitorFailure then recordEvidence;
        }

        action vehicleTargetAEBSFunctionalFlow : VehicleTargetAEBSFunctionalFlow;

        // ─── Functional interface ports (INC-AEBS-005) ───

        part incAEBS005 : FeatureIncrement;

        // Inbound interface port definitions

        port def DriverOverrideInputInbound {
          doc /* Inbound port for conscious driver override of AEBS intervention. */
          in item driverOverrideInput : DriverOverrideInput;
        }

        port def AEBSFailureStatusInbound {
          doc /* Inbound port for detected AEBS-related failure conditions. */
          in item aebsFailureStatus : AEBSFailureStatus;
        }

        // Outbound interface port definitions

        port def DriverWarningRequestOutbound {
          doc /* Outbound port for driver warning requests when warning conditions are met. */
          out item driverWarningRequest : DriverWarningRequest;
        }

        port def EmergencyBrakingCommandOutbound {
          doc /* Outbound port for emergency braking commands when activation conditions are met. */
          out item emergencyBrakingCommand : EmergencyBrakingCommand;
        }

        port def FailureIndicationRequestOutbound {
          doc /* Outbound port for AEBS failure indication requests. */
          out item failureIndicationRequest : FailureIndicationRequest;
        }

        port def AEBSEvidenceEventOutbound {
          doc /* Outbound port for AEBS evidence event records for later V&V work. */
          out item aebsEvidenceEvent : AEBSEvidenceEvent;
        }

        // Functional chain with typed boundary ports

        part def VehicleTargetAEBSFunctionalChain {
          doc /*
           * Functional chain part owning the AEBS vehicle-target interface ports.
           * Not a logical component allocation — no ECU, software, sensor, or bus
           * assignment is implied. The chain performs the composite functional
           * flow from INC-AEBS-004 and exposes its boundary as typed ports.
           */

          port driverOverrideInputIn : DriverOverrideInputInbound;
          port aebsFailureStatusIn : AEBSFailureStatusInbound;
          port driverWarningRequestOut : DriverWarningRequestOutbound;
          port emergencyBrakingCommandOut : EmergencyBrakingCommandOutbound;
          port failureIndicationRequestOut : FailureIndicationRequestOutbound;
          port aebsEvidenceEventOut : AEBSEvidenceEventOutbound;

          perform vehicleTargetAEBSFunctionalFlow : VehicleTargetAEBSFunctionalFlow {
            in item driverOverrideInput = driverOverrideInputIn.driverOverrideInput;
            in item aebsFailureStatus = aebsFailureStatusIn.aebsFailureStatus;
            out item driverWarningRequest = driverWarningRequestOut.driverWarningRequest;
            out item emergencyBrakingCommand = emergencyBrakingCommandOut.emergencyBrakingCommand;
            out item failureIndicationRequest = failureIndicationRequestOut.failureIndicationRequest;
            out item aebsEvidenceEvent = aebsEvidenceEventOut.aebsEvidenceEvent;
          }
        }

        part vehicleTargetAEBSFunctionalChain : VehicleTargetAEBSFunctionalChain;

        concern functionalBehaviorConcern : FunctionalBehaviorConcern {
          doc /*
           * Reviewers need the AEBS functional responsibilities, information
           * items, flows, and sequencing visible with requirement trace.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        concern functionalInterfaceConcern : FunctionalInterfaceConcern {
          doc /*
           * Reviewers need the AEBS functional boundary ports, signal
           * character, direction, and the functional chain that owns them.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view aebsFunctionalBehaviorView {
          viewpoint selectedFunctionalBehaviorViewpoint : SystemFunctionalBreakdownStructureViewpoint {
            frame functionalBehaviorConcern;
          }

          expose FunctionalBehavior::*;
          render asTreeDiagram;
        }

        view aebsFunctionalInterfaceView {
          viewpoint selectedFunctionalInterfaceViewpoint : SystemInterfaceDefinitionViewpoint {
            frame functionalInterfaceConcern;
          }

          expose FunctionalBehavior::*;
          render asTreeDiagram;
        }
      }
    }
  }
}