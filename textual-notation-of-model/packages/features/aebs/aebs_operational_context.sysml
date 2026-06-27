/*
 * DE4SDV AEBS operational context model slice.
 *
 * This package mirrors INC-AEBS-002 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-operational-context.yaml.
 * It is an operational-domain model slice only: no design-input requirements,
 * VSS signal mapping, logical realization, physical/software realization, or
 * UNECE R152 compliance claim is made here.
 */

package DE4SDV {
  package Features {
    package AEBS {
      package OperationalContext {
        part def OperationalActor;
        part def HumanActor :> OperationalActor;
        part def ExternalTrafficActor :> OperationalActor;
        part def EnvironmentActor :> OperationalActor;
        part def System1Actor :> OperationalActor;
        part def System2ArtifactSystem :> OperationalActor;
        part def System3ReviewActor :> OperationalActor;

        part def OperationalCapability;
        part def OperationalStory;
        part def OperationalStep;
        part def AlternatePath;
        part def StakeholderNeed;
        part def ValidationScenario;
        part def Assumption;
        part def Gap;
        part def AcceptanceCriterion;

        part def SubjectVehicle :> System1Actor;
        part def Driver :> HumanActor;
        part def VehicleTarget :> ExternalTrafficActor;
        part def RoadEnvironment :> EnvironmentActor;
        part def DE4SDVEvidenceBaseline :> System2ArtifactSystem;
        part def DE4SDVReviewer :> System3ReviewActor;

        part subjectVehicle : SubjectVehicle;
        part driver : Driver;
        part vehicleTarget : VehicleTarget;
        part roadEnvironment : RoadEnvironment;
        part de4sdvEvidenceBaseline : DE4SDVEvidenceBaseline;
        part de4sdvReviewer : DE4SDVReviewer;

        part forwardCollisionRiskMitigation : OperationalCapability;
        part vehicleTargetForwardCollisionStory : OperationalStory;

        part step1FollowVehicleTarget : OperationalStep;
        part step2DetectImminentCollisionRisk : OperationalStep;
        part step3WarnDriverWhenRequired : OperationalStep;
        part step4DriverMayOverride : OperationalStep;
        part step5CommandEmergencyBraking : OperationalStep;
        part step6RecordEvidenceExpectations : OperationalStep;

        part driverOverridePath : AlternatePath;
        part detectedFailurePath : AlternatePath;
        part noActivationPath : AlternatePath;

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
