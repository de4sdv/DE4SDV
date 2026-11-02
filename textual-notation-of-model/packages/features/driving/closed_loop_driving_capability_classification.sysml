/*
 * DE4SDV closed-loop driving capability classification model slice.
 *
 * INC-DRIVING-001, phase 3, records the one characteristic the increment adds
 * that distinguishes member products, as a feature candidate: AutoE2E as the
 * driving stack. A feature (ISO/IEC 26580) is a product's characteristic that
 * differentiates it from other products within the same product line. Core
 * elements, which every member uses, are common by default and not classified
 * here. LiDAR adds no record: the feature model already makes it optional.
 */

package DE4SDV_ClosedLoopDrivingCapabilityClassification {
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodViewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  part autoE2EDrivingStack : ProductLineFeatureCandidate {
    doc /*
     * AutoE2E as the vehicle application distinguishes the driving member from
     * the Autoware members. It plans from camera images and ego motion and takes
     * no LiDAR input. So phase 9 adds it to the feature model with a constraint
     * that it requires the camera feature, and leaves LiDAR selectable (owner
     * decision of 2026-11-02). Phase 9 also derives its middleware adapter, which
     * phase 8 realizes first. Acceptance waits for the member decision.
     */
  }
  dependency autoE2ECandidateOfDeferredDrivingStackVariability
    from autoE2EDrivingStack
    to DE4SDV_AEBSProductLineScope::deferredVariabilitySet::drivingStackVariability;
  dependency autoE2ECandidateAnswersProductLineAdmissionGap
    from autoE2EDrivingStack
    to DE4SDV_ClosedLoopDrivingFraming::gapProductLineAdmission;

  comment memberDecisionScopeInputs about DE4SDV_ClosedLoopDrivingFraming::gapProductLineAdmission
    /*
     * The owner scope decisions phase 3 identified (owner direction of
     * 2026-11-02). The member decision records them by amending ADR 0014:
     * - the driving member becomes a new planned member;
     * - Autoware and LiDAR stop being common: driving-stack and sensing
     *   variability leave deferral, and LiDAR becomes a mid- and premium-tier
     *   option;
     * - Vehicle-Target AEBS and the protected emergency command path stay
     *   common;
     * - Eclipse S-CORE, reference-only today, is admitted, because the driving
     *   member commands the vehicle through it. This one is still open.
     */

  concern closedLoopDrivingClassificationConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * Reviewers need the driving stack identified as the feature candidate that
     * distinguishes the driving member, with what it requires of the sensing
     * and the deferred scope it turns into variability.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  view closedLoopDrivingClassificationView : TVD::TableView {
    viewpoint selectedProductLineClassificationViewpoint : ProductLineClassificationViewpoint {
      frame closedLoopDrivingClassificationConcern;
    }

    expose autoE2EDrivingStack;
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
