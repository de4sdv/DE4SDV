/*
 * DE4SDV middleware stakeholder needs model slice.
 *
 * INC-MW-004 defines stakeholder needs for middleware integration. Needs are
 * separated from requirements (INC-MW-005). System 1 needs are product-level
 * needs from operational stakeholders. System 2 needs are engineering-
 * assurance needs from the DE4SDV engineering team.
 *
 * This increment does NOT define requirements, functional architecture,
 * logical architecture, or physical/software realization.
 */

package DE4SDV_MWStakeholderNeeds {
  package Features {
    package Middleware {
      package StakeholderNeeds {
        private import Views::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;

        requirement def StakeholderNeedCandidate;
        requirement def MiddlewareIntegrationNeed :> StakeholderNeedCandidate;
        requirement def PlatformDecouplingNeed :> StakeholderNeedCandidate;
        requirement def TraceabilityNeed :> StakeholderNeedCandidate;
        requirement def ProductLineFeatureNeed :> StakeholderNeedCandidate;
        requirement def SafetyPathIsolationNeed :> StakeholderNeedCandidate;
        requirement def UpstreamEngagementNeed :> StakeholderNeedCandidate;
        requirement def EngineeringBoundaryNeed :> StakeholderNeedCandidate;
        requirement def VVPlanningNeed :> StakeholderNeedCandidate;

        part incMW004 : NeedsRequirementsIncrement {
          doc /* INC-MW-004: middleware integration stakeholder needs. */
        }

        part sdvProductLine : SDVProductLine;
        part productLineMemberProduct : ProductLineMemberProduct;

        part mwNeedsSystemContext : SystemContext {
          doc /* DE4SDV method system context for INC-MW-004. */
          part productLine : SDVProductLine :>> systemOfInterest;
          part memberProduct : ProductLineMemberProduct;

          part platformEngineer : SystemsEngineer;
          part systemsEngineer : SystemsEngineer;
          part productLineEngineer : ProductLineEngineer;
          part safetyExpert : SafetyExpert;
          part maintainer : Maintainer;
          part reviewer : OpenSourceReviewer;

          requirement mwNeedsProblemStatement : ProblemStatement {
            doc /* How can DE4SDV define stakeholder needs for middleware integration that preserve platform decoupling, traceability, product-line variability, safety path isolation, and upstream engagement without making realization or compliance claims? */
            subject increment : NeedsRequirementsIncrement;
            stakeholder platformEngineer : SystemsEngineer;
            stakeholder systemsEngineer : SystemsEngineer;
            stakeholder productLineEngineer : ProductLineEngineer;
            stakeholder safetyExpert : SafetyExpert;
            stakeholder maintainer : Maintainer;
            stakeholder reviewer : OpenSourceReviewer;
          }
        }

        package System1Product {
          requirement needMiddlewareIntegration : MiddlewareIntegrationNeed {
            doc /* N-MW-001 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder platformEngineer : SystemsEngineer;
            require constraint { doc /* Platform engineers need the SDV product line to provide middleware integration that enables signal access, diagnostic access, lifecycle coordination, health monitoring, and update coordination between an ADAS application and a vehicle-level platform middleware. */ }
          }

          requirement needPlatformDecoupling : PlatformDecouplingNeed {
            doc /* N-MW-002 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder platformEngineer : SystemsEngineer;
            require constraint { doc /* Platform engineers need the SDV product line to ensure the ADAS application is not coupled to a specific middleware implementation so that middleware selection remains a product-line feature choice. */ }
          }

          requirement needMiddlewareAsFeature : ProductLineFeatureNeed {
            doc /* N-MW-003 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder productLineEngineer : ProductLineEngineer;
            require constraint { doc /* Product-line engineers need the SDV product line to treat middleware platform selection as a feature that distinguishes member products, with the adapter layer as a common capability derived from the application-middleware feature pair. */ }
          }

          requirement needSafetyPathIsolation : SafetyPathIsolationNeed {
            doc /* N-MW-004 draft System 1 need. */
            subject memberProduct : ProductLineMemberProduct;
            stakeholder safetyExpert : SafetyExpert;
            require constraint { doc /* Safety experts need each SDV product-line member product to ensure that the emergency intervention path is isolated from middleware failures, whether routed through a safety-certified middleware partition or via a direct vehicle-command path. */ }
          }

          requirement needUpstreamEngagement : UpstreamEngagementNeed {
            doc /* N-MW-005 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder maintainer : Maintainer;
            require constraint { doc /* Maintainers need the SDV product line to engage upstream middleware maintainers before deeper integration, vendoring, or presenting borrowed methods as settled DE4SDV practice. */ }
          }
        }

        package System2EngineeringAssurance {
          requirement needTraceabilityToOperationalContext : TraceabilityNeed {
            doc /* N-MW-006 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder systemsEngineer : SystemsEngineer;
            require constraint { doc /* Systems engineers need the DE4SDV middleware increment to maintain trace links from stakeholder needs to the operational context scenarios defined in INC-MW-002 and the feature classifications defined in INC-MW-003. */ }
          }

          requirement needExplicitEngineeringBoundary : EngineeringBoundaryNeed {
            doc /* N-MW-007 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder systemsEngineer : SystemsEngineer;
            require constraint { doc /* Systems engineers need the DE4SDV middleware increment to keep its engineering boundary, assumptions, source constraints, and out-of-scope cases explicit while needs are derived. */ }
          }

          requirement needVVPlanningAttachment : VVPlanningNeed {
            doc /* N-MW-008 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder reviewer : OpenSourceReviewer;
            require constraint { doc /* Reviewers need the DE4SDV middleware increment to maintain a separate controlled V&V planning attachment for each stakeholder need without changing the product obligation. */ }
          }
        }

        public import System1Product::*;
        public import System2EngineeringAssurance::*;

        concern stakeholderNeedsConcern : StakeholderNeedsConcern {
          doc /*
           * Reviewers need stakeholder needs for middleware integration
           * separated from requirements, with traceability to the
           * operational context and feature classification.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder productLineEngineer : ProductLineEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view mwStakeholderNeedsView {
          viewpoint selectedStakeholderNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
            frame stakeholderNeedsConcern;
          }

          expose System1Product::*;
          expose System2EngineeringAssurance::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
