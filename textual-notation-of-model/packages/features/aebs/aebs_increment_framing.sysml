/*
 * DE4SDV AEBS increment framing model slice.
 *
 * This package mirrors INC-AEBS-001 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-increment-framing.yaml.
 * It is a framing/model-governance slice, not an AEBS design baseline or
 * UNECE R152 compliance claim.
 */

package DE4SDV {
  package Features {
    package AEBS {
      package IncrementFraming {
        part def EngineeringIncrement;
        part def FeatureIncrement :> EngineeringIncrement;

        part def SystemLayer;
        part def System1SDVProductLine :> SystemLayer;
        part def System2EngineeringAndAssuranceSystem :> SystemLayer;
        part def System3OpenSourceGovernanceEcosystem :> SystemLayer;

        part def MethodStackElement;
        part def SAFViewpointSelection :> MethodStackElement;
        part def SYSMODMethodFlow :> MethodStackElement;
        part def DE4SDVOntologyKernel :> MethodStackElement;
        part def SysMLv2ModelExpression :> MethodStackElement;
        part def VSSCandidateSignalCatalog :> MethodStackElement;

        part def ViewpointSubset;
        part def IncrementFramingSubset :> ViewpointSubset;
        part def OperationalFeatureSubset :> ViewpointSubset;
        part def FunctionalSystemSubset :> ViewpointSubset;
        part def LogicalRealizationSubset :> ViewpointSubset;
        part def PhysicalSoftwareRealizationSubset :> ViewpointSubset;
        part def FullSafetySecuritySubset :> ViewpointSubset;
        part def FullComplianceCaseSubset :> ViewpointSubset;

        part def ProductLineCharacteristic;
        part def CandidateCommonCapability :> ProductLineCharacteristic;
        part def CandidateFeatureOrCommonCapability :> ProductLineCharacteristic;
        part def DeferredFeatureCandidate :> ProductLineCharacteristic;
        part def VariationPoint :> ProductLineCharacteristic;

        part def OperationalScopeBoundary;
        part def InScopeItem;
        part def OutOfScopeItem;

        part def StakeholderConcern;
        part def Assumption;
        part def Gap;
        part def AcceptanceCriterion;

        part incAEBS001 : FeatureIncrement;

        part system1SDVProductLine : System1SDVProductLine;
        part system2EngineeringAndAssuranceSystem : System2EngineeringAndAssuranceSystem;
        part system3OpenSourceGovernanceEcosystem : System3OpenSourceGovernanceEcosystem;

        part safViewpointSelection : SAFViewpointSelection;
        part sysmodMethodFlow : SYSMODMethodFlow;
        part de4sdvOntologyKernel : DE4SDVOntologyKernel;
        part sysmlv2ModelExpression : SysMLv2ModelExpression;
        part vssCandidateSignalCatalog : VSSCandidateSignalCatalog;

        part selectedIncrementFramingSubset : IncrementFramingSubset;
        part selectedOperationalFeatureSubset : OperationalFeatureSubset;
        part selectedFunctionalSystemSubset : FunctionalSystemSubset;

        part deferredLogicalRealizationSubset : LogicalRealizationSubset;
        part deferredPhysicalSoftwareRealizationSubset : PhysicalSoftwareRealizationSubset;
        part deferredFullSafetySecuritySubset : FullSafetySecuritySubset;
        part deferredFullComplianceCaseSubset : FullComplianceCaseSubset;

        part forwardCollisionRiskMitigation : CandidateCommonCapability;
        part vehicleTargetAEBSSupport : CandidateFeatureOrCommonCapability;
        part pedestrianTargetAEBSSupport : DeferredFeatureCandidate;
        part bicycleTargetAEBSSupport : DeferredFeatureCandidate;
        part aebsSensorPackageSelection : VariationPoint;
        part aebsEvidenceLevel : VariationPoint;

        part firstSliceScope : OperationalScopeBoundary;
        part vehicleTargetForwardCollisionRiskMitigationScope : InScopeItem;
        part pedestrianTargetOutOfScope : OutOfScopeItem;
        part bicycleTargetOutOfScope : OutOfScopeItem;
        part complianceClaimOutOfScope : OutOfScopeItem;
        part logicalRealizationOutOfScope : OutOfScopeItem;
        part physicalSoftwareRealizationOutOfScope : OutOfScopeItem;

        part noComplianceClaimCriterion : AcceptanceCriterion;
        part vssAsSignalCatalogOnlyCriterion : AcceptanceCriterion;
        part featureClassificationExplicitCriterion : AcceptanceCriterion;
      }
    }
  }
}
