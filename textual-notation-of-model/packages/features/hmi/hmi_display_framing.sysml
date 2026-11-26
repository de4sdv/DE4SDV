/*
 * DE4SDV HMI display: Phase 0 framing and the Phase 1 concerns only.
 * One increment spans framing, realization and closed-loop verification.
 * The framing asserts no implementation, no runtime result, no product-line
 * admission and no compliance.
 */
package DE4SDV_HmiDisplayFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def HmiDisplayIncrement :> EngineeringIncrement;

  part <'INC-HMI-001'> hmiDisplayIncrement : HmiDisplayIncrement {
    doc /*
     * Owner-requested increment on what the HMI display shows the driver. The
     * owner decided on 2026-11-17 that the display of the VisionPilot
     * configuration of the driver-assistance increment shows the scene that
     * VisionPilot builds from its own perception, beside the speed and the
     * collision warning. The same decision gives the speed, the collision
     * warning and the warning's sound to the high availability renderer (HAR)
     * of AAOS SDV, in an SDV Media VM, and the scene to an app in the IVI VM.
     * The increment does not change what the candidate application perceives,
     * plans, requests or commands. The owner decided on 2026-11-21 that the
     * increment goes on without waiting for Phase 10 of the driver-assistance
     * increment. Phase 3 and later phases waited for the revision of the
     * governed scope (gapHmiDisplayInProductLine), which the model now holds,
     * so they go on. All phases retain this identity. This package holds
     * Phase 0 and the Phase 1 concerns.
     */
  }

  requirement hmiDisplayProblem : ProblemStatement {
    subject hmiDisplaySubject : HmiDisplayIncrement;
    stakeholder occupant : VehicleOccupant;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
    doc /*
     * The owner decided on 2026-11-13 that every member product has an HMI
     * display, and left open what it shows. The product line asks every member
     * product to warn the driver of an imminent collision, and to make the
     * availability of the AEBS apparent when its inputs or its functions are
     * not healthy. In the driver-assistance increment the AAOS SDV is to give
     * its candidate's collision warning on the display and as a sound. DE4SDV
     * does not know what else the display has to show the driver of a vehicle
     * with driver assistance, how much of what a driving application perceives
     * and plans reaches the display, and whether the driver still sees the
     * speed and the warning, or that the warning is unavailable, while Android
     * in the IVI VM hangs, boots or restarts.
     */
  }

  part hmiDisplayQuestion : IncrementEngineeringQuestion {
    doc /*
     * Can the HMI display of the VisionPilot configuration show the driver the
     * scene that the candidate application perceives, its lane, the path it
     * fits to its lane and the objects it detects, together with the speed and
     * the collision warning, with the speed and the warning drawn by the high
     * availability renderer of AAOS SDV in an SDV Media VM, which also sounds
     * the warning, so that the speed and the warning, or the fact that the
     * warning is unavailable, stay apparent and correct while Android in the
     * IVI VM hangs, boots or restarts? A verdict for each requirement and
     * scenario answers this, holding what the display shows against what the
     * candidate gives and when. A recording of a display that looks right does
     * not.
     */
  }

  part hmiDisplayDecision : IncrementLifecycleDecision {
    doc /*
     * Decide what the product line takes from this display: which of its
     * content becomes common to the member products and which derives from a
     * member's driving application, and whether the high availability renderer
     * or an app in the IVI VM draws the common content where a member has an
     * AAOS SDV guest. The decision rests on executed cases with a pass or a
     * fail for each requirement of the increment. A fail is a result to
     * record. It is no reason to change a scenario or a criterion until the
     * display passes.
     */
  }

  part def HmiDisplaySystem {
    doc /*
     * Candidate System 1 boundary. In: the scene and the warning request that
     * the candidate application gives, and the vehicle speed. Inside: what the
     * display shows and where; an app in the IVI VM that draws the scene; the
     * high availability renderer in an SDV Media VM that draws the speed and
     * the collision warning and gives the warning's sound; and the paths from
     * the SDV Core VM to both. Out: the picture on the display and the sound.
     * Two parts of System 1 are outside this boundary, and neither is an
     * enabling system: the candidate application, which perceives, plans and
     * requests the warning, and the Eclipse S-CORE path that carries its
     * outputs to the SDV Core VM. Which part of System 1 brings the vehicle
     * speed to the SDV Core VM is for the architecture phases to place.
     * Phases 6 to 8 decide the realization. The display belongs to a
     * configuration that is not a member product: this increment admits no
     * member to the governed product-line scope. Phases 2 and 3 add the
     * actors, the interfaces and the product-line classification.
     */
  }
  part hmiDisplaySystem : HmiDisplaySystem;
  /* Rule 5 of the increment workflow, in its dependency form, declared with
   * the system of interest (phase 9). The display of this increment is the
   * display of the VisionPilot configuration (owner decision of 2026-11-17),
   * inside the AAOS SDV guest: the app in the IVI VM, the high availability
   * renderer in an SDV Media VM, and the paths from the SDV Core VM to both.
   * So it enters a member product only with the features visionPilot and
   * guestAndroidSDV, and two dependencies name both. By the owner decision of
   * 2026-11-26, its requirements follow it, and none links a feature of its
   * own (rule 11). The warning request that REQ-HMI-004, REQ-HMI-005 and
   * REQ-HMI-007 name comes with both: the requirements of the
   * driver-assistance increment that name it follow a system of interest that
   * brings visionPilot and apply only where the AAOS SDV guest middleware is
   * selected. By ADR 0026 every member product is to have an HMI display, and
   * what it shows in each is open (hmiDisplayContentScopeDecisions). The
   * binding form gives an element one link and derives no variant for this
   * pair, so the move of the links takes this combination to the owner
   * (rule 5). */
  dependency hmiDisplaySystemOnVisionPilotFeature
    from hmiDisplaySystem
    to DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::visionPilot;
  dependency hmiDisplaySystemOnGuestAndroidSDVFeature
    from hmiDisplaySystem
    to DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::guestAndroidSDV;

  part hmiDisplayScope : IncrementScope {
    doc /*
     * What the HMI display of the VisionPilot configuration shows and which
     * renderer draws each element of it: the candidate's scene, the vehicle
     * speed and the collision warning, in closed loop on the bench and in the
     * scenarios of the driver-assistance increment, with faults of Android in
     * the IVI VM added to them, for one configuration and with at most ten
     * requirements. Phase 5 derives those requirements from the needs of Phase
     * 4 and from the product line's requirements on the collision warning and
     * on the indication of the AEBS status (REQ-AEBS-002 and REQ-AEBS-013).
     * The warning request is the driver-assistance increment's; this increment
     * takes it as that increment defines it. Closed-loop execution and its
     * evidence belong to Phase 10 of this same increment. A readiness probe
     * comes before the architecture rests on what it tests. Implementation is
     * not part of this framing slice.
     */
  }

  part hmiSceneInScope : InScopeItem {
    doc /*
     * The scene as the candidate builds it from its own perception: its lane,
     * the path it fits to that lane, the objects it detects, and the closest
     * object in its path with the distance that its fusion gives.
     */
  }
  part hmiSpeedInScope : InScopeItem {
    doc /* The vehicle speed that the candidate is given. */
  }
  part hmiCollisionWarningInScope : InScopeItem {
    doc /*
     * The collision warning on the display and as a sound, when the
     * candidate's warning request asks for it and within the time that the
     * driver-assistance increment allots from the request to each mode.
     */
  }
  part hmiRendererSplitInScope : InScopeItem {
    doc /*
     * Which elements the high availability renderer in an SDV Media VM draws
     * and which an app in the IVI VM draws, and the paths that bring their
     * inputs from the SDV Core VM.
     */
  }
  part hmiAndroidOutageInScope : InScopeItem {
    doc /*
     * What the display shows while the app that draws the scene hangs or ends,
     * and while Android in the IVI VM hangs, boots or restarts: the speed and
     * the warning, or the fact that the warning is unavailable.
     */
  }
  part hmiStaleContentInScope : InScopeItem {
    doc /*
     * What the display shows when an input is late or missing, so that no
     * element is shown as current when it is not.
     */
  }
  part hmiVerdictEvidenceInScope : InScopeItem {
    doc /*
     * A pass or a fail for each requirement and scenario, bound to the
     * candidate revision, the display build and the configuration that ran.
     */
  }

  part hmiSimulatorTruthOutOfScope : OutOfScopeItem {
    doc /*
     * Objects that the candidate does not give: the simulator's own record of
     * the scene, and any estimate of objects that the display would make
     * itself.
     */
  }
  part hmiPerceptionQualityOutOfScope : OutOfScopeItem {
    doc /*
     * How well the candidate perceives: whether it finds an object, and how
     * far its positions and its distances are from the simulator's. The
     * display shows what the candidate gives, right or wrong.
     */
  }
  part hmiOtherDrivingApplicationsOutOfScope : OutOfScopeItem {
    doc /*
     * The scenes of other driving applications, those of the Autoware-based
     * members and of the closed-loop driving increment among them, and
     * adapters that would bring them to the display.
     */
  }
  part hmiDriverInteractionOutOfScope : OutOfScopeItem {
    doc /*
     * Driver interaction: engagement, override, driving modes and controls on
     * the display.
     */
  }
  part hmiFurtherContentOutOfScope : OutOfScopeItem {
    doc /*
     * Gear, set speed, speed limit and the other telltales, unless a need of
     * Phase 4 asks for one; media, navigation, maps, telephony and camera
     * views.
     */
  }
  part hmiHumanFactorsOutOfScope : OutOfScopeItem {
    doc /*
     * How a driver perceives and reads the display, with glance time,
     * comprehension and distraction, and the display's visual design.
     */
  }
  part hmiCandidateChangeOutOfScope : OutOfScopeItem {
    doc /*
     * Changing what the candidate perceives, plans, requests or commands, its
     * camera geometry included, and the criteria and the verdicts of the
     * driver-assistance increment.
     */
  }
  part hmiStandaloneDisplayOutOfScope : OutOfScopeItem {
    doc /*
     * The display of a member product without an AAOS SDV guest, the
     * Linux-side display of the standalone member among them.
     */
  }
  part hmiOnRoadOperationOutOfScope : OutOfScopeItem {
    doc /*
     * On-road operation, production readiness, a safety approval of the
     * display or of the renderer's monitor, compliance, type approval or
     * certification.
     */
  }

  part hmiDisplayVerificationEnvironment : System2EngineeringAndAssuranceSystem {
    doc /*
     * CARLA renders the camera image and moves the vehicle and the targets, as
     * on the bench of the driver-assistance increment. Cloud hosts, the
     * scenario runner, the means that make Android in the IVI VM hang, end and
     * restart, the record of what the candidate gives, the capture of the
     * display and of the sound, the evaluators and the recordings enable
     * engineering and verification. They are not vehicle features and not
     * contents of the System 1 boundary. The capture observes the AAOS SDV and
     * is no part of it.
     */
  }

  part asmHmiDrivingBenchReuse : IncrementAssumption {
    doc /*
     * The bench of the driver-assistance increment, its candidate build and
     * the path that brings the candidate's warning request into the AAOS SDV
     * can carry the display. They are reuse candidates. Their results for that
     * increment are not evidence for this one.
     */
  }
  part asmHmiRendererWithoutGraphicsCard : IncrementAssumption {
    doc /*
     * The high availability renderer draws on a guest host without a graphics
     * card, with the SDV Core, IVI and SDV Media VMs running on it together. A
     * readiness probe tests this first. If it does not hold, the owner decides
     * how the increment goes on.
     */
  }
  part asmHmiSimulationStandsIn : IncrementAssumption {
    doc /*
     * The simulated road, vehicle and targets, and the vehicle speed that the
     * simulator gives, stand in for the road, the vehicle and its speed
     * signal. A verdict holds for that simulated configuration only.
     */
  }

  part gapHmiSceneOutput : IncrementGap {
    doc /*
     * At the inspected revision the candidate builds a top-down scene of its
     * lane, its path and its detections only inside its own visualization, and
     * only when that visualization is built with it, which upstream's build
     * does not do by default. The configuration that the driver-assistance
     * increment realizes for the candidate keeps the visualization in the
     * candidate's loop off. That increment's visualization recorder, an
     * observer of System 2 in the candidate's process, draws upstream's
     * visualization into the bench's recording only, from a copy that a second
     * hand-off in the loop gives it. With the recorder the candidate gives its
     * command a few milliseconds later (phase8VisualizationRecorderPlaced).
     * None of the outputs that the driver-assistance increment realizes for
     * the candidate, its driving command and its warning request among them,
     * carries the scene. Whether the scene can leave the candidate's process
     * without a change to what it perceives and plans is open. A build of the
     * candidate that adds such an output differs from the build that the
     * driver-assistance increment judges.
     */
  }
  part gapHmiSceneContent : IncrementGap {
    doc /*
     * The candidate's detections carry a level of their place relative to its
     * path, such as in its lane or in the next, not a type of object. The
     * closest object in its path carries a distance and a speed from the
     * candidate's fusion; the other detections are placed on the road through
     * the candidate's camera geometry, which has to match the simulated camera
     * (gapCameraImageAndGeometry of the driver-assistance increment). The
     * candidate's panel also makes estimates that its perception does not
     * give: it takes a detection for a truck from its projected width, gives
     * each box a fixed size, and labels the closest object with its projected
     * position instead of the fused distance. Such estimates are the display's
     * own, which this increment leaves out. What a driver needs from the scene
     * is for Phase 4 to state; what the candidate gives bounds it.
     */
  }
  part gapHmiRendererCollisionWarning : IncrementGap {
    doc /*
     * The vehicle data of the high availability renderer holds the vehicle
     * speed but no collision warning. Its reference code draws a
     * front-collision mark only in a scripted demonstration of a
     * driver-assistance scene, whose state it computes from the time alone,
     * and its reference app has no sound for a collision warning. How a
     * collision warning and an indication that the warning is unavailable
     * reach the renderer, and how their symbols and their sound are designed
     * and reviewed, is open.
     */
  }
  part gapHmiRendererIntegration : IncrementGap {
    doc /*
     * No high availability renderer has run on the DE4SDV bench. Its path from
     * the SDV Core VM to the SDV Media VM, its drawing over the display of the
     * IVI VM in the bench's launch form, the app in the IVI VM that tells it
     * that Android is alive, its sound output and the capture of that sound,
     * and the IVI image that this takes are not observed.
     */
  }
  part gapHmiWarningPresentation : IncrementGap {
    doc /*
     * The driver-assistance increment realizes the collision warning with an
     * app in the IVI VM, a build item of its bench, and allots 0.1 s of the
     * 0.2 s from the warning request to each mode to the path to that app and
     * 0.1 s to the app. Its realization records the high availability renderer
     * for that warning as an alternative that the owner did not select for it
     * on 2026-11-17 (ALT-DRIVING-HARWARNING-001). Whether a build of this
     * display replaces that app in the VisionPilot configuration, and how the
     * 0.2 s divides on a path to the SDV Media VM, is open. The realization
     * and the verdicts of the driver-assistance increment stay as they are.
     */
  }
  part gapHmiWarningAvailability : IncrementGap {
    doc /*
     * At the inspected revision the candidate gives no indication that its
     * warning is unavailable, and the driver-assistance increment leaves the
     * failure and unavailability signals of the warning out of its scope. The
     * product line asks that the availability of the AEBS be apparent when its
     * inputs or its functions are not healthy. Whether the display learns that
     * the warning is unavailable from the age of its inputs or from a signal
     * of its own is open.
     */
  }
  part gapHmiMemberGuestLayout : IncrementGap {
    doc /*
     * ADR 0025 gives the S-CORE-integrated member of ADR 0023 a guest
     * partition of two VMs, an SDV Core VM and an IVI VM that runs the HMI
     * application, and the Eclipse S-CORE middleware increment assumes that
     * this HMI application is an informational display, not the AEBS driver
     * warning (ASM-MW-024). A renderer in an SDV Media VM adds a third VM to
     * the guest. What the lifecycle decision means for that layout and that
     * assumption is open, and it is settled outside this increment.
     */
  }
  part gapHmiStandaloneLinuxDisplay : IncrementGap {
    doc /*
     * The standalone member selects the HMI display, common content of every
     * member product (ADR 0026). It has no AAOS SDV guest, so its display is
     * a Linux-side display, and no such display exists: no shared asset
     * implements one, and the standalone member selects a display that has
     * no realization. That the display is common is a scope classification,
     * not evidence about the display. This increment leaves the Linux-side
     * display out of its scope (hmiStandaloneDisplayOutOfScope), and its
     * design is open.
     */
  }
  part gapHmiAAOSIntegratedGuestDisplay : IncrementGap {
    doc /*
     * The AAOS-integrated member, MW-CONFIG-001, selects the HMI display,
     * which it holds in its AAOS SDV guest (ADR 0026). Its configured member
     * models a headless guest: its guest middleware is a headless SDV Core
     * boundary, and its retained evidence names the headless sdv_core_cf
     * image. Its guest now needs a display. Which VM of the guest holds the
     * display is realization content, as ADR 0025 says for the S-CORE
     * member, and it is open. The records of INC-MW-010 stay retained
     * against the earlier content and are not edited.
     */
  }
  part gapHmiDisplayInProductLine : IncrementGap {
    doc /*
     * The owner decided on 2026-11-13 that every member product has an HMI
     * display (ADR 0026). The governed scope holds the HMI display as common
     * content of every planned member, bound during Development, and every
     * member configuration selects the feature hmiDisplay, which corresponds
     * to that common content. Where the display runs follows the integration
     * mode: in the AAOS SDV guest of the two integrated members, and on the
     * Linux side of the standalone member. No shared asset implements the
     * display yet, and what it shows in each member is open. The owner
     * decided on 2026-11-21 that this increment records the two gaps that the
     * scope revision leaves in the members (gapHmiStandaloneLinuxDisplay,
     * gapHmiAAOSIntegratedGuestDisplay). Phase 3 classifies the content of
     * the display against the scope as it now stands.
     */
  }
  comment about gapHmiDisplayInProductLine
  /*
   * Owner direction of 2026-11-26: the display of every member is to show the
   * vehicle speed, the collision warning, the outdated marks and the scene,
   * and the HMI display is to stay independent of the driving application
   * that feeds it. It is to take each input in a form that does not depend on
   * that application, and each application that feeds it is to give its
   * inputs in that form through a translation of its own. The vehicle speed
   * has such a form, as COVESA VSS types it, and the warning request has the
   * form that the driver-assistance increment gives it. The scene has the
   * form of the scene of the panel of VisionPilot
   * (termsHmiDisplayRequirements), and its message type stays open until
   * phase 10 (DisplaySceneMessage). In this increment VisionPilot is the
   * source of the scene, which it does not give at its boundary yet
   * (gapHmiSceneOutput), and of the warning request. It is a direction for
   * the scope decisions that hmiDisplayContentScopeDecisions lists, for the
   * AEBS requirements on the warning and for the message type of the scene;
   * it changes no member here.
   */
  part gapHmiUpstreamContact : IncrementGap {
    doc /*
     * The maintainers of the display safety of AAOS SDV and of the candidate
     * application are not yet involved. A collision warning in the renderer's
     * vehicle data and app, and a scene output of the candidate, are changes
     * to their projects. Involve them before deep adoption or vendoring, and
     * show them a result about their project before it is published. No
     * upstream contact, endorsement or rights clearance is asserted.
     */
  }

  part hmiDisplayCharter : IncrementCharter {
    ref part :>> increment = hmiDisplayIncrement;
    ref part :>> systemOfInterest = hmiDisplaySystem;
    attribute :>> owner = "Orkun Yilmaz";
    attribute :>> applicablePhases = (
      MethodPhase::phase0_incrementFraming,
      MethodPhase::phase1_concernFraming,
      MethodPhase::phase2_operationalContext,
      MethodPhase::phase3_capabilityClassification,
      MethodPhase::phase4_needs,
      MethodPhase::phase5_requirements,
      MethodPhase::phase6_functionalArchitecture,
      MethodPhase::phase7_logicalArchitecture,
      MethodPhase::phase8_physicalRealization,
      MethodPhase::phase9_variabilityConfiguration,
      MethodPhase::phase10_vvEvidence,
      MethodPhase::phase11_baseline
    );
    attribute :>> expectedArtifacts = (
      "DE4SDV_HmiDisplayFraming",
      "DE4SDV_HmiDisplayOperationalContext",
      "DE4SDV_HmiDisplayCapabilityClassification",
      "DE4SDV_HmiDisplayNeedsRequirements",
      "DE4SDV_HmiDisplayFunctionalArchitecture",
      "DE4SDV_HmiDisplayLogicalArchitecture",
      "DE4SDV_HmiDisplayPhysicalSoftwareRealization",
      "DE4SDV_HmiDisplayVariabilityConfiguration"
    );
    attribute :>> expectedReviewEvidence = (
      "owner confirmation of the engineering question and the scope",
      "independent review of the System 1 and System 2 boundary and the nonclaims",
      "repository, smoke and focused regression checks on the reviewed changes",
      "exact-head licensed SysML validation and Syside-generated framing view"
    );
    doc /*
     * Expected artifacts name only content present now, not future packages.
     * Review evidence is expected, not asserted available by this declaration.
     */
  }

  dependency scopeToHmiDisplayQuestion
    from hmiDisplayScope to hmiDisplayQuestion;
  dependency hmiDisplayQuestionToProblem
    from hmiDisplayQuestion to hmiDisplayProblem;

  concern hmiDisplayBoundary : IncrementBoundaryConcern {
    subject increment : HmiDisplayIncrement;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    doc /*
     * Systems engineers and verification engineers need the framing proposal
     * kept distinct from realized, tested or accepted scope, and the verdicts
     * of Phase 10, which hold what the display shows against what the
     * candidate gives, kept distinct from a recording that looks right.
     */
  }

  /* Phase 1: one concern per question of the in-scope items, held by the
   * parties whose interest it states, not only by the roles that check the
   * answer. Each is typed by the SAF concern that asks its question, the
   * product-line question by the method's classification concern, and names
   * the view of a later phase that answers it, save the product-line
   * question, for which phase 3 has no view; that is the viewpoint selection
   * of this phase. The framing viewpoint frames all of them, and a view of a
   * later phase that answers a concern frames it as well. */
  concern hmiDriverSupervisionConcern : OperationalCapabilityConcern {
    doc /*
     * hmiSceneInScope, hmiSpeedInScope, hmiCollisionWarningInScope and
     * hmiAndroidOutageInScope, operational part. The driver, a vehicle
     * occupant, needs to see on the HMI display what the driving application
     * perceives, its lane, the path it fits to that lane and the objects it
     * detects, beside the vehicle speed, to get a warning of an imminent
     * collision on the display and as a sound, and to see the speed and the
     * warning, or the fact that the warning is unavailable, also while Android
     * in the IVI VM hangs, boots or restarts. It states what the driver
     * expects to see, not how a driver reads it: no human-factors, safety or
     * on-road claim follows from it. Answered by the operational story of
     * phase 2.
     */
    subject;
    stakeholder occupant : VehicleOccupant;
  }

  concern hmiDisplayInputsConcern : SystemContextExchangeConcern {
    doc /*
     * hmiSceneInScope, hmiSpeedInScope and hmiCollisionWarningInScope.
     * Systems engineers and safety experts need to see which items cross into
     * the HMI display from outside its boundary: the lane of the candidate
     * application, the path it fits to that lane, the objects it detects with
     * their level relative to its path, the closest object in its path with
     * the distance and the speed that its fusion gives, the vehicle speed that
     * the candidate is given, and the candidate's warning request. Each item
     * reaches the display as its source gives it. The display takes no object
     * that the candidate does not give: neither the simulator's own record of
     * the scene nor an estimate of its own (hmiSimulatorTruthOutOfScope), so
     * it shows what the candidate perceives, right or wrong. Whether the scene
     * can leave the candidate's process is open (gapHmiSceneOutput), and what
     * the scene carries bounds what the display can show of it
     * (gapHmiSceneContent). Answered by the system process of phase 6.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder safetyExpert : SafetyExpert;
  }

  concern hmiContentVarianceConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * hmiSceneInScope, hmiSpeedInScope and hmiCollisionWarningInScope,
     * product-line part. Product-line engineers need to see which content of
     * the HMI display is common to the member products and which derives from
     * a member's driving application. The scene is what one driving
     * application perceives, and the scenes of the other driving applications
     * of the product line are out of scope
     * (hmiOtherDrivingApplicationsOutOfScope). The classification is made
     * against the governed scope as its revision leaves it
     * (gapHmiDisplayInProductLine). The framing view frames it. Phase 3 gives
     * each content item its reason in its classification and records no
     * characteristic, since the increment adds none that tells the member
     * products apart, so phase 3 has no view; which content becomes common is
     * for the lifecycle decision.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  concern hmiWarningSequenceConcern : SystemProcessConcern {
    doc /*
     * hmiCollisionWarningInScope. Safety experts and systems engineers need to
     * see the sequence from the candidate's warning request to the collision
     * warning on the display and to its sound, and the time of each step
     * within the time that the driver-assistance increment allots from the
     * request to each mode, independent of the elements that realize it. The
     * warning request is taken as the driver-assistance increment defines it,
     * and how that time divides on a path to the SDV Media VM is open
     * (gapHmiWarningPresentation). Answered by the system process of phase 6.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  concern hmiContentCurrencyConcern : SystemStateConcern {
    doc /*
     * hmiStaleContentInScope. Safety experts and verification engineers need
     * to see the states that each element of the HMI display can be in,
     * current, late or missing, and what the display shows in each, so that no
     * element is shown as current when it is not: late data is never shown as
     * live. The warning can also be unavailable, and whether the display
     * learns that from the age of its inputs or from a signal of its own is
     * open (gapHmiWarningAvailability). From which age an element counts as
     * late is for phase 5 to state. Answered by the system state of phase 6.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  concern hmiAndroidOutageConcern : SystemProcessConcern {
    doc /*
     * hmiAndroidOutageInScope. Safety experts and systems engineers need to
     * see the sequence from each outage of the drawing of the scene and of the
     * environment that hosts it, the drawing hanging or ending and its host
     * hanging, booting or restarting, to its detection and to what the display
     * shows then: the speed and the warning, or the fact that the warning is
     * unavailable, independent of the elements that realize it. Phase 6 treats
     * each outage as an event of an element inside the boundary of the HMI
     * display. It rests on the product line's need that the availability of
     * the AEBS be apparent when its inputs or its functions are not healthy
     * (N-AEBS-008) and on the status indication of REQ-AEBS-013. No safety
     * argument follows from it. Answered by the system process of phase 6.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  concern hmiRendererAllocationConcern : PhysicalFunctionalMappingConcern {
    doc /*
     * hmiRendererSplitInScope, drawing part. Product-line engineers and safety
     * experts need to see which renderer realizes the drawing of each element
     * of the HMI display: the high availability renderer in an SDV Media VM
     * the speed, the collision warning and its sound, and an app in the IVI VM
     * the scene, as the owner decided on 2026-11-17. The split rests on what
     * the driver sees while Android in the IVI VM hangs, boots or restarts
     * (N-AEBS-008, REQ-AEBS-013), not on an end of the app that draws the
     * scene. The renderer's vehicle data holds no collision warning
     * (gapHmiRendererCollisionWarning), and drawing an element with it is no
     * safety approval of that element. The lifecycle decision is whether the
     * renderer or an app in the IVI VM draws the common content where a member
     * has an AAOS SDV guest. Answered by the physical-logical mapping of phase
     * 8.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder safetyExpert : SafetyExpert;
  }

  concern hmiRendererPathConcern : PhysicalInternalExchangeConcern {
    doc /*
     * hmiRendererSplitInScope, paths part. System architects and systems
     * engineers need to see which elements exchange each input of the HMI
     * display on its way from the SDV Core VM to the high availability
     * renderer in the SDV Media VM and to the app in the IVI VM that draws the
     * scene, the exchange by which that app tells the renderer that Android is
     * alive, and the boundary interface by which each input enters the
     * display. A renderer in an SDV Media VM adds a third VM to the guest
     * (gapHmiMemberGuestLayout), and the renderer's path from the SDV Core VM
     * is not observed (gapHmiRendererIntegration). Answered by the view of the
     * claimed path of phase 8.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  concern hmiDisplayVerdictConcern : ArgumentationAssuranceConcern {
    doc /*
     * hmiVerdictEvidenceInScope. Product-line engineers and verification
     * engineers need the lifecycle decision to rest on a pass or a fail for
     * each requirement and scenario, each bound to the candidate revision, the
     * display build and the configuration that ran, holding what the display
     * shows against what the candidate gives and when. A recording of a
     * display that looks right is no verdict, a verdict holds for the
     * simulated configuration only (asmHmiSimulationStandsIn), and a fail
     * stays a recorded result. Answered by the argumentation assurance view of
     * phase 10.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  view hmiDisplayFramingView {
    viewpoint hmiDisplayFramingViewpoint : IncrementFramingViewpoint {
      frame hmiDisplayBoundary;
      frame hmiDriverSupervisionConcern;
      frame hmiDisplayInputsConcern;
      frame hmiContentVarianceConcern;
      frame hmiWarningSequenceConcern;
      frame hmiContentCurrencyConcern;
      frame hmiAndroidOutageConcern;
      frame hmiRendererAllocationConcern;
      frame hmiRendererPathConcern;
      frame hmiDisplayVerdictConcern;
    }
    expose HmiDisplayIncrement;
    expose hmiDisplayIncrement;
    expose hmiDisplayProblem;
    expose hmiDisplayQuestion;
    expose hmiDisplayDecision;
    expose hmiDisplaySystem;
    expose hmiDisplayScope;
    expose hmiDisplayBoundary;
    expose hmiDriverSupervisionConcern;
    expose hmiDisplayInputsConcern;
    expose hmiContentVarianceConcern;
    expose hmiWarningSequenceConcern;
    expose hmiContentCurrencyConcern;
    expose hmiAndroidOutageConcern;
    expose hmiRendererAllocationConcern;
    expose hmiRendererPathConcern;
    expose hmiDisplayVerdictConcern;
    expose hmiSceneInScope;
    expose hmiSpeedInScope;
    expose hmiCollisionWarningInScope;
    expose hmiRendererSplitInScope;
    expose hmiAndroidOutageInScope;
    expose hmiStaleContentInScope;
    expose hmiVerdictEvidenceInScope;
    expose hmiSimulatorTruthOutOfScope;
    expose hmiPerceptionQualityOutOfScope;
    expose hmiOtherDrivingApplicationsOutOfScope;
    expose hmiDriverInteractionOutOfScope;
    expose hmiFurtherContentOutOfScope;
    expose hmiHumanFactorsOutOfScope;
    expose hmiCandidateChangeOutOfScope;
    expose hmiStandaloneDisplayOutOfScope;
    expose hmiOnRoadOperationOutOfScope;
    expose hmiDisplayCharter;
    expose hmiDisplayVerificationEnvironment;
    expose asmHmiDrivingBenchReuse;
    expose asmHmiRendererWithoutGraphicsCard;
    expose asmHmiSimulationStandsIn;
    expose gapHmiSceneOutput;
    expose gapHmiSceneContent;
    expose gapHmiRendererCollisionWarning;
    expose gapHmiRendererIntegration;
    expose gapHmiWarningPresentation;
    expose gapHmiWarningAvailability;
    expose gapHmiMemberGuestLayout;
    expose gapHmiStandaloneLinuxDisplay;
    expose gapHmiAAOSIntegratedGuestDisplay;
    expose gapHmiDisplayInProductLine;
    expose gapHmiUpstreamContact;
    render asTreeDiagram;
  }
}
