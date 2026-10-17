/*
 * DE4SDV middleware capability classification model slice for the Eclipse
 * S-CORE realization.
 *
 * INC-MW-011, phase 3, records the one characteristic the increment adds that
 * distinguishes member products, as a feature candidate: an AAOS SDV HMI
 * guest next to the Linux host. A feature (ISO/IEC 26580) is a product's
 * characteristic that differentiates it from other products within the same
 * product line. Core elements, which every member uses, are common by default
 * and not classified here; the S-CORE middleware and its Autoware adapter are
 * already native variants of DE4SDV_SDVPlatformStack; the assumptions of use
 * belong to phase 5, the bench to phase 10.
 */

package DE4SDV_MiddlewareSCOREFeatureClassification {
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodViewpoints::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  part hmiGuestExecutionDomain : ProductLineFeatureCandidate {
    doc /*
     * CLS-MW-004: an AAOS SDV HMI guest next to the Linux host distinguishes the
     * two-domain member from the standalone member. Acceptance waits for the scope
     * ADR and phase 9; the AAOS-integrated mode is only a candidate counterpart, and
     * the ADR decides. Structural consequence: per-domain platform selection (GAP-MW-032).
     */
  }
  dependency hmiGuestCandidateOnTwoDomainGap
    from hmiGuestExecutionDomain
    to DE4SDV_MiddlewareSCOREFraming::gapTwoDomainMemberNotExpressible;
  dependency hmiGuestCandidateCounterpartOfAAOSIntegratedMode
    from hmiGuestExecutionDomain
    to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;

  /* Phase 3 revalidation of the INC-MW-003 baseline. */
  dependency safetyPathDecisionBoundedByEmergencyPathAssumption
    from DE4SDV_MiddlewareSCOREFraming::asmEmergencyCommandPathStaysOnLinuxHost
    to DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::safetyPathDecision;

  concern scoreTwoDomainClassificationConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * Reviewers need the new member-distinguishing characteristic identified as
     * a feature candidate, with the gap and the scope decision it waits for.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreTwoDomainClassificationView : TVD::TableView {
    viewpoint selectedProductLineClassificationViewpoint : ProductLineClassificationViewpoint {
      frame scoreTwoDomainClassificationConcern;
    }

    expose hmiGuestExecutionDomain;
    filter @ SysML::PartUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Classification :> columnViews {
      attribute :>> featureToRender = CT::heritage;
    }
    view Rationale :> columnViews {
      attribute :>> featureToRender = CT::documentation;
      attribute :>> columnWidth = 360;
    }
  }
}
