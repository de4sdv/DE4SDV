/*
 * DE4SDV AEBS needs and draft requirements model slice.
 *
 * This package mirrors INC-AEBS-003 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml.
 * It is a draft needs/requirements and V&V planning slice only: no functional
 * decomposition, VSS signal mapping, logical realization, physical/software
 * realization, or UNECE R152 compliance claim is made here.
 *
 * Requirements are represented with native SysML v2 requirement definitions
 * and usages. The statements remain requirement candidates because several
 * GtWR-style quality checks still fail until operating conditions, thresholds,
 * timing, and acceptance criteria are quantified.
 */

package DE4SDV {
  package Features {
    package AEBS {
      package NeedsRequirements {
        part def NeedsRequirementsIncrement;
        part def StakeholderNeed;
        part def ValidationScenario;
        part def VerificationMethod;
        part def AnalysisMethod :> VerificationMethod;
        part def DemonstrationMethod :> VerificationMethod;
        part def SimulationMethod :> VerificationMethod;
        part def InspectionMethod :> VerificationMethod;
        part def EvidenceStatus;
        part def PlannedEvidence :> EvidenceStatus;
        part def GapEvidence :> EvidenceStatus;
        part def AcceptanceCriterion;
        part def Gap;
        part def RequirementQualityFinding;
        part def ApplicableMemberProduct;
        part def AEBSEvidenceBaseline;

        requirement def RequirementCandidate;
        requirement def FunctionalRequirementCandidate :> RequirementCandidate;
        requirement def SafetyConstraintRequirementCandidate :> RequirementCandidate;
        requirement def ProductLineConstraintRequirementCandidate :> RequirementCandidate;
        requirement def TraceabilityConstraintRequirementCandidate :> RequirementCandidate;

        part incAEBS003 : NeedsRequirementsIncrement;
        part applicableMemberProduct : ApplicableMemberProduct;
        part aebsEvidenceBaseline : AEBSEvidenceBaseline;

        part needCommonAEBSCapability : StakeholderNeed;
        part needExplicitOperationalBoundary : StakeholderNeed;
        part needProductLineClassification : StakeholderNeed;
        part needVisibleRegulatoryAssumptions : StakeholderNeed;
        part needRequirementVVPlanning : StakeholderNeed;

        requirement reqDetectForwardCollisionRisk : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-001 candidate: Applicable SDV product-line member products shall realize the common AEBS capability by detecting imminent forward collision risk with a vehicle target under selected operating conditions. */
        }

        requirement reqProvideCollisionWarning : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-002 candidate: Applicable SDV product-line member products shall realize the common AEBS capability by providing a collision warning to the driver when selected warning conditions are met. */
        }

        requirement reqCommandEmergencyBraking : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-003 candidate: Applicable SDV product-line member products shall realize the common AEBS capability by commanding emergency braking when selected activation conditions are met and no overriding condition prevents intervention. */
        }

        requirement reqAllowDriverOverride : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-004 candidate: Applicable SDV product-line member products shall allow conscious driver override of AEBS intervention under defined override conditions. */
        }

        requirement reqSupportFailureIndication : SafetyConstraintRequirementCandidate {
          doc /* REQ-AEBS-005 candidate: Applicable SDV product-line member products shall support detection or indication of AEBS-related failure conditions without hiding safe-operation concerns. */
        }

        requirement reqKeepProductLineClassificationExplicit : ProductLineConstraintRequirementCandidate {
          doc /* REQ-AEBS-006 candidate: The AEBS model baseline shall keep common-capability, feature, and variation-point classifications explicit for each AEBS behavior or scope element. */
        }

        requirement reqTraceRequirementVVAndGaps : TraceabilityConstraintRequirementCandidate {
          doc /* REQ-AEBS-007 candidate: The DE4SDV AEBS increment shall trace each draft AEBS requirement to its source assumption, stakeholder need, validation reference, planned verification method, evidence status, and unresolved gap when applicable. */
        }

        satisfy reqDetectForwardCollisionRisk by applicableMemberProduct;
        satisfy reqProvideCollisionWarning by applicableMemberProduct;
        satisfy reqCommandEmergencyBraking by applicableMemberProduct;
        satisfy reqAllowDriverOverride by applicableMemberProduct;
        satisfy reqSupportFailureIndication by applicableMemberProduct;
        satisfy reqKeepProductLineClassificationExplicit by aebsEvidenceBaseline;
        satisfy reqTraceRequirementVVAndGaps by aebsEvidenceBaseline;

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
        part findingNativeSysMLRequirementNotationRequired : RequirementQualityFinding;
      }
    }
  }
}
