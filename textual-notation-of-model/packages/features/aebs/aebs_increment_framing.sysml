/*
 * DE4SDV AEBS increment framing model slice.
 *
 * This package mirrors INC-AEBS-001 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-increment-framing.yaml.
 * It is a framing/model-governance slice, not an AEBS design baseline or
 * UNECE R152 compliance claim.
 *
 * Semantic repair: feature-specific stakeholder concerns are framed by reusable
 * DE4SDV method viewpoint definitions imported from DE4SDV_MethodViewpoints.
 * Concrete AEBS view usages select those viewpoints for this increment.
 */

package DE4SDV {
  package Features {
    package AEBS {
      package IncrementFraming {
        private import Views::*;
        private import DE4SDV_MethodViewpoints::*;

        part def EngineeringIncrement;
        part def FeatureIncrement :> EngineeringIncrement;

        part def SystemLayer;
        part def System1SDVProductLine :> SystemLayer;
        part def System2EngineeringAndAssuranceSystem :> SystemLayer;
        part def System3OpenSourceGovernanceEcosystem :> SystemLayer;

        part def SystemsEngineer;
        part def ProductLineEngineer;
        part def ComplianceEngineer;
        part def VerificationEngineer;
        part def OpenSourceReviewer;

        part def MethodStackElement;
        part def SAFViewpointSelection :> MethodStackElement;
        part def SYSMODMethodFlow :> MethodStackElement;
        part def DE4SDVOntologyKernel :> MethodStackElement;
        part def SysMLv2ModelExpression :> MethodStackElement;
        part def VSSCandidateSignalCatalog :> MethodStackElement;

        part def ProductLineCharacteristic;
        part def CandidateCommonCapability :> ProductLineCharacteristic;
        part def CandidateFeatureOrCommonCapability :> ProductLineCharacteristic;
        part def DeferredFeatureCandidate :> ProductLineCharacteristic;
        part def VariationPoint :> ProductLineCharacteristic;

        part def OperationalScopeBoundary;
        part def InScopeItem;
        part def OutOfScopeItem;
        part def Assumption;
        part def Gap;
        part def AcceptanceCriterion;

        concern productLineCapabilityClassificationConcern : ProductLineCapabilityClassificationConcern {
          doc /*
           * Reviewers need AEBS scope elements to distinguish common product-line
           * capabilities from features and later variation points.
           */
          subject;
          stakeholder productLineEngineer : ProductLineEngineer;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        concern regulatoryScopeWithoutComplianceClaimConcern : RegulatoryScopeWithoutComplianceClaimConcern {
          doc /*
           * Reviewers need the UNECE R152 regulatory anchor and open compliance
           * assumptions to be visible without treating this increment as evidence
           * of compliance, certification, or type approval.
           */
          subject;
          stakeholder complianceEngineer : ComplianceEngineer;
          stakeholder verificationEngineer : VerificationEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        concern incrementBoundaryConcern : IncrementBoundaryConcern {
          doc /*
           * Reviewers need a small increment boundary that separates framing,
           * operational context, functional modeling, logical realization,
           * physical/software realization, and evidence work.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder verificationEngineer : VerificationEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        concern methodStackConcern : MethodStackConcern {
          doc /*
           * Reviewers need to see how SAF viewpoint selection, SYSMOD method flow,
           * DE4SDV ontology terms, SysML v2 model expression, and VSS signal
           * catalog usage relate without collapsing them into one method blob.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        part incAEBS001 : FeatureIncrement;

        part system1SDVProductLine : System1SDVProductLine;
        part system2EngineeringAndAssuranceSystem : System2EngineeringAndAssuranceSystem;
        part system3OpenSourceGovernanceEcosystem : System3OpenSourceGovernanceEcosystem;

        part safViewpointSelection : SAFViewpointSelection;
        part sysmodMethodFlow : SYSMODMethodFlow;
        part de4sdvOntologyKernel : DE4SDVOntologyKernel;
        part sysmlv2ModelExpression : SysMLv2ModelExpression;
        part vssCandidateSignalCatalog : VSSCandidateSignalCatalog;

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

        view aebsIncrementFramingView {
          viewpoint selectedIncrementFramingViewpoint : IncrementFramingViewpoint {
            frame productLineCapabilityClassificationConcern;
            frame regulatoryScopeWithoutComplianceClaimConcern;
            frame incrementBoundaryConcern;
            frame methodStackConcern;
          }

          expose IncrementFraming::*;
          render asTreeDiagram;
        }
        view aebsProductLineClassificationView {
          viewpoint selectedProductLineClassificationViewpoint : ProductLineClassificationViewpoint {
            frame productLineCapabilityClassificationConcern;
          }

          expose IncrementFraming::*;
          render asTreeDiagram;
        }
        view aebsRegulatoryScopeView {
          viewpoint selectedRegulatoryScopeViewpoint : RegulatoryScopeViewpoint {
            frame regulatoryScopeWithoutComplianceClaimConcern;
          }

          expose IncrementFraming::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
