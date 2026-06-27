/*
 * DE4SDV AEBS needs and draft requirements model slice.
 *
 * This package mirrors INC-AEBS-003 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml.
 * It is a draft needs/requirements and V&V planning slice only: no functional
 * decomposition, VSS signal mapping, logical realization, physical/software
 * realization, or UNECE R152 compliance claim is made here.
 */

package DE4SDV {
  package Features {
    package AEBS {
      package NeedsRequirements {
        part def NeedsRequirementsIncrement;
        part def StakeholderNeed;
        part def DesignInputRequirement;
        part def FunctionalRequirement :> DesignInputRequirement;
        part def SafetyConstraintRequirement :> DesignInputRequirement;
        part def ProductLineConstraintRequirement :> DesignInputRequirement;
        part def TraceabilityConstraintRequirement :> DesignInputRequirement;

        part def VerificationMethod;
        part def AnalysisMethod :> VerificationMethod;
        part def DemonstrationMethod :> VerificationMethod;
        part def SimulationMethod :> VerificationMethod;
        part def InspectionMethod :> VerificationMethod;

        part def ValidationScenario;
        part def EvidenceStatus;
        part def PlannedEvidence :> EvidenceStatus;
        part def GapEvidence :> EvidenceStatus;
        part def AcceptanceCriterion;
        part def Gap;
        part def RequirementQualityFinding;

        part incAEBS003 : NeedsRequirementsIncrement;

        part needCommonAEBSCapability : StakeholderNeed;
        part needExplicitOperationalBoundary : StakeholderNeed;
        part needProductLineClassification : StakeholderNeed;
        part needVisibleRegulatoryAssumptions : StakeholderNeed;
        part needRequirementVVPlanning : StakeholderNeed;

        part reqDetectForwardCollisionRisk : FunctionalRequirement;
        part reqProvideCollisionWarning : FunctionalRequirement;
        part reqCommandEmergencyBraking : FunctionalRequirement;
        part reqAllowDriverOverride : FunctionalRequirement;
        part reqSupportFailureIndication : SafetyConstraintRequirement;
        part reqKeepProductLineClassificationExplicit : ProductLineConstraintRequirement;
        part reqTraceRequirementVVAndGaps : TraceabilityConstraintRequirement;

        part analysisVerification : AnalysisMethod;
        part demonstrationVerification : DemonstrationMethod;
        part simulationVerification : SimulationMethod;
        part inspectionVerification : InspectionMethod;

        part validationCommonAEBSCapability : ValidationScenario;
        part validationOperationalBoundary : ValidationScenario;
        part validationProductLineClassification : ValidationScenario;
        part validationRegulatoryAssumptions : ValidationScenario;
        part validationRequirementVVPlanning : ValidationScenario;

        part plannedEvidenceStatus : PlannedEvidence;
        part gapEvidenceStatus : GapEvidence;

        part criterionDetectionConditionsTBD : AcceptanceCriterion;
        part criterionWarningConditionsTBD : AcceptanceCriterion;
        part criterionBrakingActivationTBD : AcceptanceCriterion;
        part criterionDriverOverrideTBD : AcceptanceCriterion;
        part criterionFailureHandlingTBD : AcceptanceCriterion;
        part criterionClassificationExplicit : AcceptanceCriterion;
        part criterionRequirementTraceComplete : AcceptanceCriterion;

        part gapOperatingConditionsUndefined : Gap;
        part gapVehicleTargetDetectionCriteriaUndefined : Gap;
        part gapWarningTimingUndefined : Gap;
        part gapBrakingActivationUndefined : Gap;
        part gapFalseReactionConstraintsUndefined : Gap;
        part gapDriverOverrideUndefined : Gap;
        part gapFailureHandlingUndefined : Gap;
        part gapVariationPointsUndefined : Gap;
        part gapVSSDeferred : Gap;

        part findingQuantitativeCriteriaDeferred : RequirementQualityFinding;
        part findingVehicleTargetOnly : RequirementQualityFinding;
        part findingVSSDeferred : RequirementQualityFinding;
        part findingNoComplianceClaim : RequirementQualityFinding;
      }
    }
  }
}
