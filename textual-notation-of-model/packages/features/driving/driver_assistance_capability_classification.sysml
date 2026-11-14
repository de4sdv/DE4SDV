/*
 * DE4SDV driver-assistance capability classification model slice.
 *
 * INC-DRIVING-002, phase 3, records the one characteristic that distinguishes
 * a member product, VisionPilot as the vehicle application, as a feature
 * candidate. Core elements are common by default and get no record.
 * Camera-only sensing adds no record: the feature model already makes LiDAR
 * optional. The display and the sound get no candidate; the comment on the
 * HMI gap gives the reasons. Eclipse S-CORE gets none: it is an integration
 * mode, not a characteristic of this member, and the comment on the admission
 * gap reads it. The middleware adapter gets none: phase 9 derives it from the
 * configuration.
 */

package DE4SDV_DriverAssistanceCapabilityClassification {
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodViewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  part visionPilotDrivingStack : ProductLineFeatureCandidate {
    doc /*
     * VisionPilot as the vehicle application distinguishes a camera-only
     * driver-assistance member from the Autoware members and from the
     * AutoE2E candidate. At the pinned revision it reads one front-camera
     * image and the vehicle speed, and writes steering and acceleration. It
     * requires the camera, so phase 9 adds a requiresFeatures constraint and
     * leaves LiDAR and radar selectable. It requires Linux on the main side:
     * its camera interface is V4L2, and ROS 2 is a build option only. Phase 9
     * adds that constraint after phase 8 builds the candidate. It needs a
     * middleware adapter to Eclipse S-CORE, which phase 8 realizes first and
     * phase 9 derives. It also runs a speed-following and a lane-keeping
     * function, which no case of this increment judges. Phase 9 decides
     * whether the configuration selects them. Acceptance waits for the member
     * decision.
     */
  }
  dependency visionPilotCandidateOfDeferredDrivingStackVariability
    from visionPilotDrivingStack
    to DE4SDV_AEBSProductLineScope::deferredVariabilitySet::drivingStackVariability;
  dependency visionPilotCandidateAnswersCandidateAdmissionGap
    from visionPilotDrivingStack
    to DE4SDV_DriverAssistanceFraming::gapCandidateAdmission;

  comment memberDecisionScopeInputs about DE4SDV_DriverAssistanceFraming::gapCandidateAdmission
    /*
     * Phase 3 names the scope decisions that admitting the candidate would
     * need. The member decision takes them by amending ADR 0014; this
     * increment admits nothing.
     * - The candidate would be a new planned member.
     * - Autoware and LiDAR stop being common when it is admitted:
     *   driving-stack and sensing variability leave deferral. Phase 3 of
     *   INC-DRIVING-001 identified the same for the driving member.
     * - Vehicle-Target AEBS and the independence of the protected emergency
     *   command path stay common. ADR 0023 decision 5 keeps them common to
     *   the three accepted members, and INC-DRIVING-001 keeps them for the
     *   driving member. The candidate has to meet both;
     *   gapNoSeparateEmergencyFunction holds what is open.
     * - The Linux and ROS 2 runtime of Autoware: the candidate runs on Linux
     *   and needs neither ROS 2 nor the Autoware runtime. Whether that common
     *   content narrows to Linux on the main side and stays common, or stops
     *   being common, is open.
     * - The integration mode: on the model as it stands, Eclipse S-CORE is
     *   reference-only, so a configuration of the candidate with it is valid
     *   and not admitted. ADR 0023, accepted, makes it the S-CORE-integrated
     *   alternative once its scope pull request takes effect in the model.
     *   The candidate then needs no new alternative.
     */

  comment driverHmiClassification about DE4SDV_DriverAssistanceFraming::gapDriverHmiInProductLine
    /*
     * Phase 3 classifies the candidate's display and sound against the scope.
     * - The display: on the model as it stands, the HMI display is an optional
     *   feature that requires the AAOS SDV guest. ADR 0026, accepted, makes a
     *   display common content of every member once its scope pull request
     *   takes effect. Under neither reading is it a feature candidate of this
     *   member. The application's own visualization is not the member's
     *   display.
     * - The sound: neither the feature model nor the governed scope holds a
     *   warning mode, and no member differs by one, so the sound is no
     *   feature candidate. Whether the acoustic warning becomes common
     *   content of the driver warning is open for the member decision.
     */

  concern driverAssistanceClassificationConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * Product-line engineers and systems engineers need VisionPilot
     * identified as the feature candidate that distinguishes a camera-only
     * driver-assistance member, with what it requires of the sensing and the
     * runtime, and the deferred scope it turns into variability.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  view driverAssistanceClassificationView : TVD::TableView {
    viewpoint selectedProductLineClassificationViewpoint : ProductLineClassificationViewpoint {
      frame driverAssistanceClassificationConcern;
    }

    expose visionPilotDrivingStack;
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
