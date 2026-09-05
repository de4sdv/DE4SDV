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

package DE4SDV_MiddlewareStakeholderNeeds {
  package Features {
    package Middleware {
      package StakeholderNeeds {
        private import Views::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MiddlewareOperationalContext::Features::Middleware::OperationalContext::*;
        private import DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::*;
        private import DE4SDV_MiddlewareIncrementFraming::Features::Middleware::IncrementFraming::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;
        private import SysideViews::**;

        requirement def MiddlewareIntegrationNeed :> StakeholderNeedCandidate;
        requirement def PlatformDecouplingNeed :> StakeholderNeedCandidate;
        requirement def SafetyPathIsolationNeed :> StakeholderNeedCandidate;
        requirement def UpstreamEngagementNeed :> StakeholderNeedCandidate;
        requirement def SecurityTrustBoundaryNeed :> StakeholderNeedCandidate;

        part incMW004 : NeedsRequirementsIncrement {
          doc /* INC-MW-004: middleware integration stakeholder needs. */
        }

        package System1Product {
          requirement needMiddlewareIntegration : MiddlewareIntegrationNeed {
            doc /* N-MW-001 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder platformEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Platform engineers need the SDV product line to provide middleware integration connecting the ADAS application with a vehicle-level platform middleware for signal access, diagnostic access, lifecycle coordination, health monitoring, and update coordination. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-MW-002 operational context and INC-MW-003 feature classification";
            attribute :>> rationale = "ADAS application capability depends on signal, diagnostic, lifecycle, health, and update access through platform middleware.";
          }

          requirement needPlatformDecoupling : PlatformDecouplingNeed {
            doc /* N-MW-002 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder platformEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Platform engineers need the SDV product line to ensure the ADAS application is not coupled to a specific middleware implementation so that middleware selection remains a product-line feature choice. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-MW-003 feature classification";
            attribute :>> rationale = "Middleware selection must remain a product-line feature choice, not an application property.";
          }

          requirement needMiddlewareAsFeature : ProductLineClassificationNeed {
            doc /* N-MW-003 draft System 1 need; derived requirements are owned by the PLE configuration increment INC-MW-009 rather than INC-MW-005. */
            subject productLine : SDVProductLine;
            stakeholder productLineEngineer : ProductLineEngineer;
            require constraint statement { language "English" /* Product-line engineers need the SDV product line to treat middleware platform selection as a feature that distinguishes member products, with the adapter layer as a common capability derived from the application-middleware feature pair. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-MW-003 feature classification";
            attribute :>> rationale = "Adapter-layer commonality derives from the application-middleware feature pair.";
          }

          requirement needSafetyPathIsolation : SafetyPathIsolationNeed {
            doc /* N-MW-004 draft System 1 need; isolation and containment criteria remain open per GAP-MW-029. */
            subject memberProduct : ProductLineMemberProduct;
            stakeholder safetyExpert : SafetyExpert;
            require constraint statement { language "English" /* Safety experts need each SDV product-line member product to ensure that the emergency intervention path is isolated from middleware failures, whether routed through a safety-certified middleware partition or via a direct vehicle-command path. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-MW-002 operational context emergency-intervention scenario";
            attribute :>> rationale = "Emergency intervention must survive middleware failure regardless of selected architecture; criteria open per GAP-MW-029.";
          }
        }

        package System2EngineeringAssurance {
          requirement needUpstreamEngagement : UpstreamEngagementNeed {
            doc /* N-MW-005 draft System 2 need; moved from System 1 because upstream engagement is a DE4SDV project obligation, not a product-line capability. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder maintainer : Maintainer;
            require constraint statement { language "English" /* Maintainers need the DE4SDV middleware increment to engage upstream middleware maintainers before deeper integration, vendoring, or presenting borrowed methods as settled DE4SDV practice. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV governance policy on external methodology adoption";
            attribute :>> rationale = "Upstream maintainers must be involved before deeper integration or vendoring.";
          }

          requirement needSecurityTrustBoundary : SecurityTrustBoundaryNeed {
            doc /* N-MW-009 draft System 2 need; parents REQ-MW-008, trust-boundary details remain deferred per GAP-MW-012. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder securityExpert : SecurityExpert;
            require constraint statement { language "English" /* Security experts need the DE4SDV middleware increment to define the trust boundary that middleware service bindings must authenticate across before the ADAS application accepts service data or commands. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Requirements QA gate review of the INC-MW-005 baseline";
            attribute :>> rationale = "Service-binding authentication needs a defined trust boundary to authenticate across; details deferred per GAP-MW-012.";
          }
          requirement needTraceabilityToOperationalContext : EngineeringTraceabilityNeed {
            doc /* N-MW-006 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder systemsEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Systems engineers need the DE4SDV middleware increment to maintain trace links from stakeholder needs to the operational context scenarios defined in INC-MW-002 and the feature classifications defined in INC-MW-003. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV method increment workflow";
            attribute :>> rationale = "Needs must trace to the operational scenarios that justify them.";
          }

          requirement needExplicitEngineeringBoundary : EngineeringTraceabilityNeed {
            doc /* N-MW-007 draft System 2 need; satisfied by the increment framing and gap records rather than a derived requirement. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder systemsEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Systems engineers need the DE4SDV middleware increment to keep its engineering boundary, assumptions, source constraints, and out-of-scope cases explicit while needs are derived. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV method increment workflow";
            attribute :>> rationale = "Boundary, assumptions, and out-of-scope cases stay explicit while needs are derived.";
          }

          requirement needVVPlanningAttachment : VerificationPlanningNeed {
            doc /* N-MW-008 draft System 2 need; satisfied by the separate verification_planning attachment in the INC-MW-004 and INC-MW-005 artifacts rather than a derived requirement. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder reviewer : OpenSourceReviewer;
            require constraint statement { language "English" /* Reviewers need the DE4SDV middleware increment to maintain a separate controlled V&V planning attachment for each stakeholder need without changing the product obligation. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV verification and assurance workflow";
            attribute :>> rationale = "Per-need V&V planning attachments stay separate from product obligations.";
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

        part safetyPathIsolationCriteriaGap : DeferredProductLineScope {
          doc /*
           * GAP-MW-029: The isolation criteria and failure-containment
           * expectations for the emergency intervention path remain
           * undefined; the selected safety-path architecture is deferred
           * to INC-MW-005.
           */
        }

        /*
         * Trace links from needs to prior increments.
         */
        dependency need001FromOperationalContext
          from needMiddlewareIntegration
          to DE4SDV_MiddlewareOperationalContext::Features::Middleware::OperationalContext::operationalCapabilityConcern;

        dependency need002FromClassification
          from needPlatformDecoupling
          to DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::productLineCapabilityClassificationConcern;

        dependency need003FromClassification
          from needMiddlewareAsFeature
          to DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::productLineCapabilityClassificationConcern;

        dependency need004FromOperationalContext
          from needSafetyPathIsolation
          to DE4SDV_MiddlewareOperationalContext::Features::Middleware::OperationalContext::operationalCapabilityConcern;

        public import System1Product::*;
        public import System2EngineeringAssurance::*;

        dependency needOperationalContextTrace
          from DE4SDV_MiddlewareStakeholderNeeds::Features::Middleware::StakeholderNeeds::System1Product::needMiddlewareIntegration
          to DE4SDV_MiddlewareOperationalContext::Features::Middleware::OperationalContext::'integrate ADAS with vehicle platform';
        dependency needClassificationTrace
          from DE4SDV_MiddlewareStakeholderNeeds::Features::Middleware::StakeholderNeeds::System1Product::needMiddlewareIntegration
          to DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::adapterLayer;
        dependency needFramingTrace
          from DE4SDV_MiddlewareStakeholderNeeds::Features::Middleware::StakeholderNeeds::System1Product::needMiddlewareIntegration
          to DE4SDV_MiddlewareIncrementFraming::Features::Middleware::IncrementFraming::middlewareIntegrationProblemStatement;

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

        view middlewareStakeholderNeedsView : TVD::TableView {
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
