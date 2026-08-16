/*
 * DE4SDV middleware stakeholder needs model slice.
 *
 * INC-MW-004 defines stakeholder needs for middleware integration. Needs are
 * separated from requirements (INC-MW-005). System 1 needs are product-level
 * needs from operational stakeholders. System 2 needs are engineering-
 * assurance needs from the DE4SDV engineering team.
 *
 * This increment does NOT define requirements, functional architecture,
 * system architecture, or physical/software realization.
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
        private import SysideViews::**;

        requirement def MiddlewareIntegrationNeed :> StakeholderNeedCandidate;
        requirement def PlatformDecouplingNeed :> StakeholderNeedCandidate;
        requirement def SafetyPathIsolationNeed :> StakeholderNeedCandidate;
        requirement def UpstreamEngagementNeed :> StakeholderNeedCandidate;

        part incMW004 : NeedsRequirementsIncrement {
          doc /* INC-MW-004: middleware integration stakeholder needs. */
        }

        package System1Product {
          requirement needMiddlewareIntegration : MiddlewareIntegrationNeed {
            doc /* N-MW-001 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder platformEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Platform engineers need the SDV product line to provide middleware integration that enables signal access, diagnostic access, lifecycle coordination, health monitoring, and update coordination between an ADAS application and a vehicle-level platform middleware. */ }
          }

          requirement needPlatformDecoupling : PlatformDecouplingNeed {
            doc /* N-MW-002 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder platformEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Platform engineers need the SDV product line to ensure the ADAS application is not coupled to a specific middleware implementation so that middleware selection remains a product-line feature choice. */ }
          }

          requirement needMiddlewareAsFeature : ProductLineClassificationNeed {
            doc /* N-MW-003 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder productLineEngineer : ProductLineEngineer;
            require constraint statement { language "English" /* Product-line engineers need the SDV product line to treat middleware platform selection as a feature that distinguishes member products, with the adapter layer as a common capability derived from the application-middleware feature pair. */ }
          }

          requirement needSafetyPathIsolation : SafetyPathIsolationNeed {
            doc /* N-MW-004 draft System 1 need. */
            subject memberProduct : ProductLineMemberProduct;
            stakeholder safetyExpert : SafetyExpert;
            require constraint statement { language "English" /* Safety experts need each SDV product-line member product to ensure that the emergency intervention path is isolated from middleware failures, whether routed through a safety-certified middleware partition or via a direct vehicle-command path. */ }
          }

          requirement needUpstreamEngagement : UpstreamEngagementNeed {
            doc /* N-MW-005 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder maintainer : Maintainer;
            require constraint statement { language "English" /* Maintainers need the SDV product line to engage upstream middleware maintainers before deeper integration, vendoring, or presenting borrowed methods as settled DE4SDV practice. */ }
          }
        }

        package System2EngineeringAssurance {
          requirement needTraceabilityToOperationalContext : EngineeringTraceabilityNeed {
            doc /* N-MW-006 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder systemsEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Systems engineers need the DE4SDV middleware increment to maintain trace links from stakeholder needs to the operational context scenarios defined in INC-MW-002 and the feature classifications defined in INC-MW-003. */ }
          }

          requirement needExplicitEngineeringBoundary : EngineeringTraceabilityNeed {
            doc /* N-MW-007 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder systemsEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Systems engineers need the DE4SDV middleware increment to keep its engineering boundary, assumptions, source constraints, and out-of-scope cases explicit while needs are derived. */ }
          }

          requirement needVVPlanningAttachment : VerificationPlanningNeed {
            doc /* N-MW-008 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder reviewer : OpenSourceReviewer;
            require constraint statement { language "English" /* Reviewers need the DE4SDV middleware increment to maintain a separate controlled V&V planning attachment for each stakeholder need without changing the product obligation. */ }
          }
        }

        /*
         * Gaps — deferred scope items, same pattern as INC-MW-003.
         */
        part vehicleSignalEnumerationGap : DeferredProductLineScope {
          doc /*
           * GAP-MW-011: The specific vehicle signals needed by the ADAS
           * application are not enumerated at the needs level. Deferred
           * to INC-MW-005 (requirements).
           */
        }

        part securityTrustBoundaryGap : DeferredProductLineScope {
          doc /*
           * GAP-MW-012: The security and trust boundary needs are not yet
           * derived. Deferred to a security-focused increment or
           * INC-MW-005.
           */
        }

        /*
         * Trace links from needs to prior increments.
         */
        dependency need001FromOperationalContext
          from needMiddlewareIntegration
          to DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::operationalCapabilityConcern;

        dependency need002FromClassification
          from needPlatformDecoupling
          to DE4SDV_MWFeatureClassification::Features::Middleware::FeatureClassification::productLineCapabilityClassificationConcern;

        dependency need003FromClassification
          from needMiddlewareAsFeature
          to DE4SDV_MWFeatureClassification::Features::Middleware::FeatureClassification::productLineCapabilityClassificationConcern;

        dependency need004FromOperationalContext
          from needSafetyPathIsolation
          to DE4SDV_MWOperationalContext::Features::Middleware::OperationalContext::operationalCapabilityConcern;

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

        view mwStakeholderNeedsView : TVD::TableView {
          viewpoint selectedStakeholderNeedsViewpoint : StakeholderRequirementDefinitionViewpoint {
            frame stakeholderNeedsConcern;
          }

          expose System1Product::*;
          expose System2EngineeringAssurance::*;
          filter @ SysML::RequirementUsage;
          attribute :>> includeReferenceElements = true;
          attribute :>> maxRowHeight = 300;
          view ID :> columnViews {
            attribute :>> featureToRender = CT::declaredName;
          }
          view Name :> columnViews {
            attribute :>> featureToRender = CT::heritage;
          }
          view Statement :> columnViews {
            attribute :>> featureToRender = CT::constraintLanguage {
              attribute constraintName = "statement";
              attribute constraintType = CL::ConT::required;
              attribute constraintLanguage = "English";
            }
            attribute :>> columnWidth = 360;
          }
        }
      }
    }
  }
}
