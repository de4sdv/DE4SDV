/*
 * DE4SDV AEBS operational context model slice.
 *
 * This package mirrors INC-AEBS-002 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-operational-context.yaml.
 * It is an operational-domain model slice only: no design-input requirements,
 * VSS signal mapping, logical realization, physical/software realization, or
 * UNECE R152 compliance claim is made here.
 *
 * Semantic repair: the operational story is represented with SysML v2 use case
 * and action constructs instead of modeling behavior only as generic parts.
 */

package DE4SDV {
  package Features {
    package AEBS {
      package OperationalContext {
        part def SubjectVehicle;
        part def Driver;
        part def VehicleTarget;
        part def RoadEnvironment;
        part def DE4SDVEvidenceBaseline;
        part def DE4SDVReviewer;

        item def VehicleTargetObservation;
        item def ForwardCollisionRiskEstimate;
        item def DriverCollisionWarning;
        item def DriverOverrideDecision;
        item def EmergencyBrakingCommand;
        item def EvidenceExpectationRecord;
        item def FailureIndication;

        action def ObserveVehicleTarget {
          out observation : VehicleTargetObservation;
        }

        action def DetectImminentForwardCollisionRisk {
          in observation : VehicleTargetObservation;
          out riskEstimate : ForwardCollisionRiskEstimate;
        }

        action def WarnDriverWhenRequired {
          in riskEstimate : ForwardCollisionRiskEstimate;
          out warning : DriverCollisionWarning;
        }

        action def EvaluateDriverOverride {
          in warning : DriverCollisionWarning;
          out overrideDecision : DriverOverrideDecision;
        }

        action def CommandEmergencyBraking {
          in riskEstimate : ForwardCollisionRiskEstimate;
          in overrideDecision : DriverOverrideDecision;
          out brakingCommand : EmergencyBrakingCommand;
        }

        action def RecordOperationalEvidenceExpectation {
          in riskEstimate : ForwardCollisionRiskEstimate;
          in brakingCommand : EmergencyBrakingCommand;
          out evidenceExpectation : EvidenceExpectationRecord;
        }

        action def IndicateAEBSFailureConcern {
          out failureIndication : FailureIndication;
        }

        action def VehicleTargetForwardCollisionMitigationFlow {
          in item observation : VehicleTargetObservation;
          out item brakingCommand : EmergencyBrakingCommand;
          out item evidenceExpectation : EvidenceExpectationRecord;

          action observeVehicleTarget : ObserveVehicleTarget {
            out observation = VehicleTargetForwardCollisionMitigationFlow::observation;
          }

          action detectRisk : DetectImminentForwardCollisionRisk {
            in observation;
            out riskEstimate;
          }

          flow from observeVehicleTarget.observation to detectRisk.observation;
          first observeVehicleTarget then detectRisk;

          action warnDriver : WarnDriverWhenRequired {
            in riskEstimate;
            out warning;
          }

          flow from detectRisk.riskEstimate to warnDriver.riskEstimate;
          first detectRisk then warnDriver;

          action evaluateDriverOverride : EvaluateDriverOverride {
            in warning;
            out overrideDecision;
          }

          flow from warnDriver.warning to evaluateDriverOverride.warning;
          first warnDriver then evaluateDriverOverride;

          action commandEmergencyBraking : CommandEmergencyBraking {
            in riskEstimate;
            in overrideDecision;
            out brakingCommand = VehicleTargetForwardCollisionMitigationFlow::brakingCommand;
          }

          flow from detectRisk.riskEstimate to commandEmergencyBraking.riskEstimate;
          flow from evaluateDriverOverride.overrideDecision to commandEmergencyBraking.overrideDecision;
          first evaluateDriverOverride then commandEmergencyBraking;

          action recordEvidenceExpectation : RecordOperationalEvidenceExpectation {
            in riskEstimate;
            in brakingCommand;
            out evidenceExpectation = VehicleTargetForwardCollisionMitigationFlow::evidenceExpectation;
          }

          flow from detectRisk.riskEstimate to recordEvidenceExpectation.riskEstimate;
          flow from commandEmergencyBraking.brakingCommand to recordEvidenceExpectation.brakingCommand;
          first commandEmergencyBraking then recordEvidenceExpectation;
        }

        use case def MitigateVehicleTargetForwardCollisionRisk {
          subject subjectVehicle : SubjectVehicle;
          actor driver : Driver;
          actor vehicleTarget : VehicleTarget;
          actor roadEnvironment : RoadEnvironment;
          actor evidenceBaseline : DE4SDVEvidenceBaseline;
          actor reviewer : DE4SDVReviewer;

          objective {
            doc /*
             * Establish the operational story for vehicle-target forward
             * collision risk mitigation in the AEBS pilot. This use case
             * frames the operational context only; requirements, functional
             * interfaces, VSS signal candidates, logical realization,
             * physical/software realization, and compliance evidence are
             * intentionally deferred to later increments.
             */
          }
        }

        part subjectVehicle : SubjectVehicle;
        part driver : Driver;
        part vehicleTarget : VehicleTarget;
        part roadEnvironment : RoadEnvironment;
        part de4sdvEvidenceBaseline : DE4SDVEvidenceBaseline;
        part de4sdvReviewer : DE4SDVReviewer;

        use case vehicleTargetForwardCollisionStory : MitigateVehicleTargetForwardCollisionRisk {
          subject subjectVehicle = OperationalContext::subjectVehicle;
          actor driver = OperationalContext::driver;
          actor vehicleTarget = OperationalContext::vehicleTarget;
          actor roadEnvironment = OperationalContext::roadEnvironment;
          actor evidenceBaseline = OperationalContext::de4sdvEvidenceBaseline;
          actor reviewer = OperationalContext::de4sdvReviewer;
        }

        action vehicleTargetForwardCollisionMitigationFlow : VehicleTargetForwardCollisionMitigationFlow;
        action detectedFailureConcern : IndicateAEBSFailureConcern;

        part def StakeholderNeed;
        part def ValidationScenario;
        part def Assumption;
        part def Gap;
        part def AcceptanceCriterion;

        part needReduceForwardCollisionRisk : StakeholderNeed;
        part needExplicitOperationalBoundary : StakeholderNeed;
        part needSeparateCapabilityFromFeatureClassification : StakeholderNeed;
        part needVisibleRegulatoryAssumptions : StakeholderNeed;
        part needLaterVerificationTargets : StakeholderNeed;

        part validationScenarioForCollisionRiskNeed : ValidationScenario;
        part validationScenarioForBoundaryNeed : ValidationScenario;
        part validationScenarioForProductLineNeed : ValidationScenario;
        part validationScenarioForComplianceNeed : ValidationScenario;
        part validationScenarioForVerificationNeed : ValidationScenario;

        part assumptionVehicleTargetOnly : Assumption;
        part assumptionNoQuantifiedOperatingConditionsYet : Assumption;
        part assumptionDriverOverrideIsOperationalPath : Assumption;
        part assumptionFailureHandlingIsConcernOnly : Assumption;
        part assumptionVSSDeferredToFunctionalInterfaces : Assumption;

        part gapOperatingParametersUndefined : Gap;
        part gapActivationCriteriaUndefined : Gap;
        part gapNoDesignInputRequirementsYet : Gap;
        part gapNoVSSSignalMappingsYet : Gap;
        part gapNoExecutableEvidenceYet : Gap;

        part criterionBoundaryExplicit : AcceptanceCriterion;
        part criterionVehicleTargetFocused : AcceptanceCriterion;
        part criterionNeedsSeparateFromRequirements : AcceptanceCriterion;
        part criterionValidationSeedsRecorded : AcceptanceCriterion;
        part criterionNoComplianceClaim : AcceptanceCriterion;
      }
    }
  }
}
