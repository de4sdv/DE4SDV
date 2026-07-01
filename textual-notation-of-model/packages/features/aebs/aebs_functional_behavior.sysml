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

        package VSSSignalReuse {
          doc /*
           * Local aliases for generated COVESA VSS signals and DE4SDV candidate
           * extension signals reused by the AEBS functional behavior slice.
           * These aliases keep VSS reuse explicit without treating catalog
           * definitions as architecture-owned ports, connectors, or components.
           */
          alias vehicleSpeedSignal for COVESA_VSS::Vehicle_Speed;
          alias longitudinalAccelerationSignal for COVESA_VSS::Vehicle_Acceleration_Longitudinal;
          alias obstacleDistanceSignal for COVESA_VSS::Vehicle_ADAS_ObstacleDetection_Distance;
          alias obstacleTimeGapSignal for COVESA_VSS::Vehicle_ADAS_ObstacleDetection_TimeGap;
          alias obstacleWarningSignal for COVESA_VSS::Vehicle_ADAS_ObstacleDetection_IsWarning;
          alias obstacleWarningTypeSignal for COVESA_VSS::Vehicle_ADAS_ObstacleDetection_WarningType;
          alias ebaEngagedSignal for COVESA_VSS::Vehicle_ADAS_EBA_IsEngaged;
          alias brakeLightActiveSignal for COVESA_VSS::Vehicle_Body_Lights_Brake_IsActive;
          alias ebaErrorSignal for COVESA_VSS::Vehicle_ADAS_EBA_IsError;
          alias absErrorSignal for COVESA_VSS::Vehicle_ADAS_ABS_IsError;

          alias aebsCollisionRiskDetectedSignal for DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_CollisionRisk_IsDetected;
          alias aebsDriverWarningActiveSignal for DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_DriverWarning_IsActive;
          alias aebsDriverOverrideActiveSignal for DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_DriverOverride_IsActive;
          alias aebsEmergencyBrakingCommandedSignal for DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_EmergencyBraking_IsCommanded;
          alias aebsErrorSignal for DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_IsError;
          alias aebsFailureIndicationActiveSignal for DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_FailureIndication_IsActive;
          alias aebsEvidenceEventRecordedSignal for DE4SDV_VSS_Extensions::Vehicle_ADAS_AEBS_EvidenceEvent_IsRecorded;
        }

        item def VehicleMotionState {
          doc /* Reuses VSSSignalReuse::vehicleSpeedSignal and VSSSignalReuse::longitudinalAccelerationSignal for AEBS vehicle-motion semantics. */
        }

        item def ForwardTargetState {
          doc /* Reuses VSSSignalReuse::obstacleDistanceSignal and VSSSignalReuse::obstacleTimeGapSignal for forward-target semantics. */
        }

        item def CollisionRiskAssessment {
          doc /* Reuses generated obstacle warning signals plus VSSSignalReuse::aebsCollisionRiskDetectedSignal for AEBS-specific risk semantics. */
        }

        item def DriverWarningRequest {
          doc /* Reuses generated obstacle warning signals plus VSSSignalReuse::aebsDriverWarningActiveSignal for AEBS-specific driver warning semantics. */
        }

        item def DriverOverrideInput {
          doc /* Reuses VSSSignalReuse::aebsDriverOverrideActiveSignal for conscious AEBS driver override semantics. */
        }

        item def DriverOverrideDecision {
          doc /* Derived functional decision based on VSSSignalReuse::aebsDriverOverrideActiveSignal and risk assessment semantics. */
        }

        item def EmergencyBrakingCommand {
          doc /* Reuses VSSSignalReuse::aebsEmergencyBrakingCommandedSignal plus generated EBA/brake-light status signals. */
        }

        item def AEBSFailureStatus {
          doc /* Reuses VSSSignalReuse::aebsErrorSignal plus generated EBA/ABS error status signals. */
        }

        item def FailureIndicationRequest {
          doc /* Reuses VSSSignalReuse::aebsFailureIndicationActiveSignal for AEBS-specific failure indication semantics. */
        }

        item def AEBSEvidenceEvent {
          doc /* Reuses VSSSignalReuse::aebsEvidenceEventRecordedSignal for AEBS evidence-event recording semantics. */
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
