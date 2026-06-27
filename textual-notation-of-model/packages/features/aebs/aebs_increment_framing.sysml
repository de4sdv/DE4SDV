/*
 * DE4SDV AEBS increment framing model slice.
 *
 * This package mirrors INC-AEBS-001 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-increment-framing.yaml.
 * It is a framing/model-governance slice, not an AEBS design baseline or
 * UNECE R152 compliance claim.
 *
 * Semantic repair: feature-specific stakeholder concerns are framed by reusable
 * SAF-aligned viewpoint definitions. Concrete AEBS view usages select those
 * viewpoints for this increment; the viewpoints themselves are not AEBS-specific.
 */

package DE4SDV {
  package Features {
    package AEBS {
      package IncrementFraming {
        private import Views::*;

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

        concern productLineCapabilityClassificationConcern {
          doc /*
           * Reviewers need AEBS scope elements to distinguish common product-line
           * capabilities from features and later variation points.
           */
          subject;
          stakeholder productLineEngineer : ProductLineEngineer;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        concern regulatoryScopeWithoutComplianceClaimConcern {
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

        concern incrementBoundaryConcern {
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

        concern methodStackConcern {
          doc /*
           * Reviewers need to see how SAF viewpoint selection, SYSMOD method flow,
           * DE4SDV ontology terms, SysML v2 model expression, and VSS signal
           * catalog usage relate without collapsing them into one method blob.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        viewpoint safIncrementFramingViewpoint {
          frame productLineCapabilityClassificationConcern;
          frame regulatoryScopeWithoutComplianceClaimConcern;
          frame incrementBoundaryConcern;
          frame methodStackConcern;

          require constraint {
            doc /*
             * An AEBS increment framing view shall show the selected concerns,
             * system layers, method-stack elements, feature/common-capability
             * classification hypotheses, scope boundary, deferred scope, and no
             * compliance-claim guardrails for the current increment.
             */
          }
        }

        viewpoint safProductLineClassificationViewpoint {
          frame productLineCapabilityClassificationConcern;

          require constraint {
            doc /*
             * A product-line classification view shall separate common
             * capabilities from candidate features and variation points for the
             * AEBS pilot before downstream functional/VSS modeling starts.
             */
          }
        }

        viewpoint safRegulatoryScopeViewpoint {
          frame regulatoryScopeWithoutComplianceClaimConcern;

          require constraint {
            doc /*
             * A regulatory-scope view shall identify regulatory anchors and
             * assumptions while explicitly avoiding compliance or type-approval
             * claims.
             */
          }
        }

        view def IncrementFramingView {
          satisfy safIncrementFramingViewpoint;
          render asTreeDiagram;
        }

        view def ProductLineClassificationView {
          satisfy safProductLineClassificationViewpoint;
          render asTreeDiagram;
        }

        view def RegulatoryScopeView {
          satisfy safRegulatoryScopeViewpoint;
          render asTreeDiagram;
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

        view aebsIncrementFramingView : IncrementFramingView {
          expose IncrementFraming::*;
        }
        view aebsProductLineClassificationView : ProductLineClassificationView {
          expose IncrementFraming::*;
        }
        view aebsRegulatoryScopeView : RegulatoryScopeView {
          expose IncrementFraming::*;
        }
      }
    }
  }
}
