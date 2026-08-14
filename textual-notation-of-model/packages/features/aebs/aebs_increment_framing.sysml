/*
 * DE4SDV AEBS increment framing model slice.
 *
 * This package mirrors INC-AEBS-001 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-increment-framing.yaml.
 * It is a framing/model-governance slice, not an AEBS design baseline or
 * UNECE R152 compliance claim.
 *
 * Shared DE4SDV method, stakeholder, product-line, and viewpoint definitions
 * are imported from reusable method packages. This feature package keeps only
 * AEBS-specific concern usages, product-line classification usages, scope
 * usages, and concrete views.
 */

package DE4SDV_AEBSIncrementFraming {
  package Features {
    package AEBS {
      package IncrementFraming {
        private import Views::*;
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;

        concern productLineCapabilityClassificationConcern : ProductLineCapabilityClassificationConcern {
          doc /*
           * Reviewers need AEBS scope elements to distinguish common product-line
           * capabilities from candidate features and later variability decisions.
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
           * operational context, functional modeling, conceptual realization,
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

        part forwardCollisionRiskMitigation : CommonProductLineCapability;
        part vehicleTargetAEBSSupport : CommonProductLineCapability;
        part pedestrianTargetAEBSScope : DeferredProductLineScope;
        part bicycleTargetAEBSScope : DeferredProductLineScope;

        /*
         * Native SysML v2 variation usages record unresolved AEBS variability
         * topics without inventing a project-local variation-point part definition. The only variants
         * in this framing slice are deferred choices; concrete sensor/evidence
         * variants require later functional/evidence increments.
         */
        variation part aebsSensorPackageSelection {
          variant part sensorPackageChoiceDeferred;
        }

        variation part aebsEvidenceLevelSelection {
          variant part evidenceLevelChoiceDeferred;
        }

        part firstSliceScope : OperationalScopeBoundary;
        part vehicleTargetForwardCollisionRiskMitigationScope : InScopeItem;
        part pedestrianTargetOutOfScope : OutOfScopeItem;
        part bicycleTargetOutOfScope : OutOfScopeItem;
        part complianceClaimOutOfScope : OutOfScopeItem;
        part conceptualRealizationOutOfScope : OutOfScopeItem;
        part physicalSoftwareRealizationOutOfScope : OutOfScopeItem;

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
