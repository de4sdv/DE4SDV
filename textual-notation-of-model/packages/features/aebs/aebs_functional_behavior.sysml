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

package DE4SDV {
  package Features {
    package AEBS {
      package FunctionalBehavior {
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import COVESA_VSS::*;
        private import DE4SDV_VSS_Extensions::*;

        part incAEBS004 : FeatureIncrement;
        part sdvProductLine : SDVProductLine;
        part memberProduct : ProductLineMemberProduct;
        part aebsCommonCapability : CommonProductLineCapability;

        item def VehicleMotionState {
          doc /* Abstract subject-vehicle motion state for AEBS functional reasoning. */
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
          attribute aebsCollisionRiskDetected : Vehicle_ADAS_AEBS_CollisionRisk_IsDetected;
        }

        item def DriverWarningRequest {
          doc /* Functional request to warn the driver when selected warning conditions are met. */
          attribute obstacleWarning : Vehicle_ADAS_ObstacleDetection_IsWarning;
          attribute obstacleWarningType : Vehicle_ADAS_ObstacleDetection_WarningType;
          attribute aebsDriverWarningActive : Vehicle_ADAS_AEBS_DriverWarning_IsActive;
        }

        item def DriverOverrideInput {
          doc /* Functional input representing conscious driver override of AEBS intervention. */
          attribute aebsDriverOverrideActive : Vehicle_ADAS_AEBS_DriverOverride_IsActive;
        }

        item def DriverOverrideDecision {
          doc /* Functional decision describing whether override prevents or modifies AEBS intervention. */
          attribute aebsDriverOverrideActive : Vehicle_ADAS_AEBS_DriverOverride_IsActive;
        }

        item def EmergencyBrakingCommand {
          doc /* Functional command expectation for emergency braking when activation conditions are met and no override prevents intervention. */
          attribute aebsEmergencyBrakingCommanded : Vehicle_ADAS_AEBS_EmergencyBraking_IsCommanded;
          attribute ebaEngaged : Vehicle_ADAS_EBA_IsEngaged;
          attribute brakeLightActive : Vehicle_Body_Lights_Brake_IsActive;
        }

        item def AEBSFailureStatus {
          doc /* Functional status for detected AEBS-related failure conditions. */
          attribute aebsError : Vehicle_ADAS_AEBS_IsError;
          attribute ebaError : Vehicle_ADAS_EBA_IsError;
          attribute absError : Vehicle_ADAS_ABS_IsError;
        }

        item def FailureIndicationRequest {
          doc /* Functional request to indicate AEBS-related failure without hiding safe-operation concerns. */
          attribute aebsFailureIndicationActive : Vehicle_ADAS_AEBS_FailureIndication_IsActive;
        }

        item def AEBSEvidenceEvent {
          doc /* Functional event record seed for later V&V/evidence-baseline work. */
          attribute aebsEvidenceEventRecorded : Vehicle_ADAS_AEBS_EvidenceEvent_IsRecorded;
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
      }
    }
  }
}
