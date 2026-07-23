/*
 * DE4SDV AEBS needs and draft requirements model slice.
 *
 * This package mirrors INC-AEBS-003 from
 * methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml.
 * It is a draft needs/requirements model slice only: no V&V model,
 * functional decomposition, VSS signal mapping, logical realization,
 * physical/software realization, or UNECE R152 compliance claim is made here.
 *
 * Semantic repair: stakeholder needs and requirement candidates use native
 * SysML v2 requirement definitions/usages with stakeholder roles and required
 * constraint bodies. Satisfaction links are intentionally deferred until the
 * functional/logical realization model contains concrete satisfying features.
 */

package DE4SDV_AEBSNeedsRequirements {
  package Features {
    package AEBS {
      package NeedsRequirements {
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;
        private import Views::*;

        part def AEBSCapability :> CommonProductLineCapability;

        requirement def StakeholderNeedCandidate;
        requirement def ProductLineCommonCapabilityNeed :> StakeholderNeedCandidate;
        requirement def EngineeringTraceabilityNeed :> StakeholderNeedCandidate;
        requirement def ProductLineClassificationNeed :> StakeholderNeedCandidate;
        requirement def RegulatoryVisibilityNeed :> StakeholderNeedCandidate;
        requirement def VerificationPlanningNeed :> StakeholderNeedCandidate;

        requirement def RequirementCandidate;
        requirement def FunctionalRequirementCandidate :> RequirementCandidate;
        requirement def SafetyConstraintRequirementCandidate :> RequirementCandidate;
        requirement def ProductLineConstraintRequirementCandidate :> RequirementCandidate;
        requirement def TraceabilityConstraintRequirementCandidate :> RequirementCandidate;

        part incAEBS003 : NeedsRequirementsIncrement;
        part sdvProductLine : SDVProductLine;
        part productLineMemberProduct : ProductLineMemberProduct;
        part aebsCommonCapability : AEBSCapability;

        part aebsNeedsRequirementsSystemContext : SystemContext {
          doc /* DE4SDV method system context for INC-AEBS-003, adapted from the SYSMOD problem-statement pattern without adding a generic project-context abstraction. */

          part productLine : SDVProductLine :>> systemOfInterest;
          part memberProduct : ProductLineMemberProduct;
          part aebsCapability : AEBSCapability;

          part roadUserStakeholder : RoadUser {
            attribute :>> risk = PriorityKind::high;
            attribute :>> effort = PriorityKind::medium;
            attribute :>> categories = (StakeholderCategoryKind::User);
          }

          part occupantStakeholder : VehicleOccupant {
            attribute :>> risk = PriorityKind::high;
            attribute :>> effort = PriorityKind::medium;
            attribute :>> categories = (StakeholderCategoryKind::User);
          }

          part systemsEngineerStakeholder : SystemsEngineer {
            attribute :>> risk = PriorityKind::medium;
            attribute :>> effort = PriorityKind::high;
            attribute :>> categories = (StakeholderCategoryKind::RequirementOwner);
          }

          part productLineEngineerStakeholder : ProductLineEngineer {
            attribute :>> risk = PriorityKind::high;
            attribute :>> effort = PriorityKind::high;
            attribute :>> categories = (StakeholderCategoryKind::Expert);
          }

          part complianceEngineerStakeholder : ComplianceEngineer {
            attribute :>> risk = PriorityKind::high;
            attribute :>> effort = PriorityKind::medium;
            attribute :>> categories = (StakeholderCategoryKind::Expert);
          }

          part verificationEngineerStakeholder : VerificationEngineer {
            attribute :>> risk = PriorityKind::medium;
            attribute :>> effort = PriorityKind::high;
            attribute :>> categories = (StakeholderCategoryKind::RequirementOwner);
          }

          requirement aebsNeedsRequirementsProblemStatement : ProblemStatement {
            doc /*
             * How can DE4SDV define an AEBS needs and draft requirements baseline
             * for the SDV product-line common AEBS capability required across member
             * products that preserves the vehicle-target collision-risk mitigation
             * intent, keeps operational boundaries and regulatory assumptions visible,
             * and exposes requirement quality gaps without claiming functional realization,
             * VSS signal mapping, or UNECE R152 compliance/type-approval fulfillment?
             */
            subject increment : NeedsRequirementsIncrement;
            stakeholder roadUser : RoadUser;
            stakeholder occupant : VehicleOccupant;
            stakeholder systemsEngineer : SystemsEngineer;
            stakeholder productLineEngineer : ProductLineEngineer;
            stakeholder complianceEngineer : ComplianceEngineer;
            stakeholder verificationEngineer : VerificationEngineer;
          }
        }

        requirement needCommonAEBSCapability : ProductLineCommonCapabilityNeed {
          doc /* N-AEBS-001 draft need. */
          subject productLine : SDVProductLine;
          stakeholder roadUser : RoadUser;
          stakeholder occupant : VehicleOccupant;
          require constraint {
            doc /* Road users and vehicle occupants need the SDV product line to define AEBS as a common capability required across member products to reduce forward rear-end in-lane collision risk with a vehicle target under defined operating conditions. */
          }
        }

        requirement needExplicitOperationalBoundary : EngineeringTraceabilityNeed {
          doc /* N-AEBS-002 draft need. */
          subject increment : NeedsRequirementsIncrement;
          stakeholder systemsEngineer : SystemsEngineer;
          require constraint {
            doc /* Systems engineers need the AEBS operational boundary, assumptions, source constraints, and out-of-scope cases to stay explicit while draft requirements are derived. */
          }
        }

        requirement needProductLineClassification : ProductLineClassificationNeed {
          doc /* N-AEBS-003 draft need. */
          subject productLine : SDVProductLine;
          stakeholder productLineEngineer : ProductLineEngineer;
          require constraint {
            doc /* Product-line engineers need AEBS to remain classified as a product-line common capability required across member products, with variation points modeled separately instead of weakening the common-capability classification. */
          }
        }

        requirement needVisibleRegulatoryAssumptions : RegulatoryVisibilityNeed {
          doc /* N-AEBS-004 draft need. */
          subject increment : NeedsRequirementsIncrement;
          stakeholder complianceEngineer : ComplianceEngineer;
          require constraint {
            doc /* Compliance engineers need regulatory assumptions, source references, and open interpretation gaps to be visible without implying UNECE R152 compliance or type approval. */
          }
        }

        requirement needRequirementVVPlanning : VerificationPlanningNeed {
          doc /* N-AEBS-005 draft need. */
          subject increment : NeedsRequirementsIncrement;
          stakeholder verificationEngineer : VerificationEngineer;
          require constraint {
            doc /* Verification engineers need each draft AEBS requirement to carry a planned verification method, validation reference, evidence status, and explicit gap when acceptance criteria are not yet quantified. */
          }
        }

        requirement reqDetectForwardCollisionRisk : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-001 candidate. */
          subject memberProduct : ProductLineMemberProduct;
          require constraint {
            doc /* Each SDV product-line member product shall realize the common AEBS capability by detecting imminent forward collision risk with a vehicle target under selected operating conditions. */
          }
        }

        requirement reqProvideCollisionWarning : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-002 candidate. */
          subject memberProduct : ProductLineMemberProduct;
          require constraint {
            doc /* Each SDV product-line member product shall realize the common AEBS capability by providing a collision warning to the driver when selected warning conditions are met. */
          }
        }

        requirement reqCommandEmergencyBraking : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-003 candidate. */
          subject memberProduct : ProductLineMemberProduct;
          require constraint {
            doc /* Each SDV product-line member product shall realize the common AEBS capability by commanding emergency braking when selected activation conditions are met and no overriding condition prevents intervention. */
          }
        }

        requirement reqAllowDriverOverride : FunctionalRequirementCandidate {
          doc /* REQ-AEBS-004 candidate. */
          subject memberProduct : ProductLineMemberProduct;
          require constraint {
            doc /* Each SDV product-line member product shall allow conscious driver override of AEBS intervention under defined override conditions. */
          }
        }

        requirement reqSupportFailureIndication : SafetyConstraintRequirementCandidate {
          doc /* REQ-AEBS-005 candidate. */
          subject memberProduct : ProductLineMemberProduct;
          require constraint {
            doc /* Each SDV product-line member product shall support detection or indication of AEBS-related failure conditions without hiding safe-operation concerns. */
          }
        }

        requirement reqKeepProductLineClassificationExplicit : ProductLineConstraintRequirementCandidate {
          doc /* REQ-AEBS-006 candidate. */
          subject increment : NeedsRequirementsIncrement;
          require constraint {
            doc /* The AEBS model baseline shall keep common-capability, feature, and variation-point classifications explicit for each AEBS behavior or scope element. */
          }
        }

        requirement reqTraceRequirementVVAndGaps : TraceabilityConstraintRequirementCandidate {
          doc /* REQ-AEBS-007 candidate. */
          subject increment : NeedsRequirementsIncrement;
          require constraint {
            doc /* The DE4SDV AEBS increment shall trace each draft AEBS requirement to its source assumption, stakeholder need, validation reference, planned verification method, evidence status, and unresolved gap when applicable. */
          }
        }

        concern stakeholderNeedsConcern : StakeholderNeedsConcern {
          doc /*
           * Reviewers need AEBS stakeholder needs visible as native
           * requirement usages with stakeholder roles.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        concern requirementTraceConcern : RequirementTraceConcern {
          doc /*
           * Reviewers need AEBS requirement candidates traced to stakeholder
           * needs with verification methods and satisfaction status.
           */
          subject;
          stakeholder verificationEngineer : VerificationEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view aebsStakeholderNeedsView {
          viewpoint selectedStakeholderNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
            frame stakeholderNeedsConcern;
          }

          expose NeedsRequirements::*;
          render asTreeDiagram;
        }

        view aebsRequirementTraceView {
          viewpoint selectedRequirementTraceViewpoint : SystemRequirementTraceabilityViewpoint {
            frame requirementTraceConcern;
          }

          expose NeedsRequirements::*;
          render asTreeDiagram;
        }

      }
    }
  }
}
