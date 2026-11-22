/*
 * DE4SDV HMI display capability classification model slice.
 *
 * INC-HMI-001, phase 3, adds no characteristic that distinguishes member
 * products, so it records no feature candidate and no deferred scope. Core
 * elements are common by default and get no record. The HMI display gets
 * none: by ADR 0026, which the owner decided on 2026-11-13, it is common
 * content of every member of the governed scope (driverHMIDisplay) and no
 * selectable feature for members. In the feature model hmiDisplay is
 * optional, so that configurations which are not members can leave it out
 * (validity), and it corresponds to that common content (admission). Where
 * the display runs gets none: each integration-mode alternative derives it
 * as part of its execution-domain topology, the AAOS SDV guest of an
 * integrated member or a Linux-side display on the standalone member (ADR
 * 0026 decision 2). The guest itself is the feature candidate
 * hmiGuestExecutionDomain of the Eclipse S-CORE middleware increment, whose
 * counterpart is both integrated alternatives by the owner's decision of
 * 2026-11-21. The scene gets none: the owner decided on 2026-11-17 that it
 * is the scene that VisionPilot builds from its own perception, so it comes
 * with the vehicle application, and VisionPilot is a feature of the feature
 * model (visionPilot) that corresponds to the deferred driving-stack
 * variability of the governed scope (drivingStackVariability). The display
 * of this increment belongs to the VisionPilot configuration, which is not
 * a member product. The vehicle speed on the display gets none: no member
 * differs by it, and neither the feature model nor the governed scope holds
 * a display of the speed. Its source is the vehicle, and its carrier goes to
 * the architecture phases (vehicleSpeedSourceComment). The collision warning
 * on the display gets none: REQ-AEBS-002 asks every member product for a
 * collision warning to the driver, and whether the display carries it
 * belongs to the AEBS requirements and architecture, which ADR 0026 leaves
 * open. The warning as a sound gets none: neither the feature model nor the
 * governed scope holds a warning mode, and no member differs by one; phase 3
 * of the driver-assistance increment identified the same. The indication
 * that the warning is unavailable gets none: it rests on N-AEBS-008 and
 * REQ-AEBS-013, the product line's need and requirement on the status of the
 * AEBS, and how the display learns of it is open
 * (gapHmiWarningAvailability). Showing no element as current when it is not
 * gets none: it is behavior, which phase 5 states as requirements and phase
 * 6 as states (hmiContentCurrencyConcern). Which renderer draws what gets
 * none: it is a realization that phase 8 maps (hmiRendererAllocationConcern),
 * which the owner decided on 2026-11-17 for this configuration; a renderer
 * needs the AAOS SDV guest, which follows the integration mode. The third VM
 * of the guest gets none: the VM layout of a guest is realization content
 * (ADR 0026, after ADR 0025), and the gap leaves it to a decision outside
 * this increment (gapHmiMemberGuestLayout). The outages of Android in the IVI
 * VM get none: they are events inside the black box of the operational
 * context, whose detection phases 6 to 8 decide (guestAcrossBoundaryComment).
 * The verdicts and the verification environment get none: they are System
 * 2, which the governed scope keeps out of product variability
 * (excludedSystem2ConcernSet). The candidate application and the Eclipse
 * S-CORE path, outside the boundary, get none: VisionPilot and Eclipse
 * S-CORE are features of the feature model (visionPilot, eclipseSCORE), and
 * this increment changes no feature. Adaptive cruise control and lane-keep
 * assist of the candidate get none: the feature model holds them as
 * adaptiveCruiseControl and laneKeepAssist, which the governed scope does
 * not hold, and this increment does not judge them. The Linux-side display
 * of the standalone member gets none: its place derives from the standalone
 * integration mode, this increment leaves it out of its scope
 * (hmiStandaloneDisplayOutOfScope), and its design is open
 * (gapHmiStandaloneLinuxDisplay). The display in the headless guest of the
 * AAOS-integrated member gets none: which VM of the guest holds it is
 * realization content (gapHmiAAOSIntegratedGuestDisplay). The owner decided
 * on 2026-11-21 that this increment records these two gaps. The items that
 * the framing puts out of scope get none: they are out-of-scope items of the
 * framing.
 */

package DE4SDV_HmiDisplayCapabilityClassification {
  comment hmiDisplayContentScopeDecisions about DE4SDV_HmiDisplayFraming::gapHmiDisplayInProductLine
  /*
   * Phase 3 classifies the content of the HMI display against the governed
   * scope as it stands and names the scope decisions that the lifecycle
   * decision of this increment needs. This increment admits nothing; a scope
   * change follows the change control of ADR 0014.
   * - The scene: whether the scene of a member's driving application becomes
   *   common content of the display, each member showing the scene of its own
   *   application, or tells the members apart, as a feature candidate of a
   *   later increment, is open.
   * - The vehicle speed: whether the speed becomes common content of the
   *   display is open.
   * - The collision warning: whether the warning and the indication that it
   *   is unavailable become content of the display of every member belongs
   *   to the AEBS requirements and architecture, and is open.
   * - The sound: phase 3 of the driver-assistance increment identified the
   *   same item; whether the acoustic warning becomes common content of the
   *   driver warning is open.
   * - The renderers: whether the high availability renderer or an app in the
   *   IVI VM draws the common content where a member has an AAOS SDV guest is
   *   open.
   * - The members: the Linux-side display of the standalone member
   *   (gapHmiStandaloneLinuxDisplay) and the display in the guest of the
   *   AAOS-integrated member (gapHmiAAOSIntegratedGuestDisplay) are
   *   realization content, and both are open.
   */
}
