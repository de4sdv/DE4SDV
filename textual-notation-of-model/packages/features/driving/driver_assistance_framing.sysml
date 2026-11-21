/*
 * DE4SDV camera-only driver assistance: Phase 0 framing, the Phase 1 concerns
 * and the baseline decision of Phase 11, beside the link of rule 5 that phase
 * 9 declares with the system of interest.
 * One increment spans framing, realization and closed-loop verification.
 * The framing asserts no implementation, no runtime result, no product-line
 * admission and no compliance; the baseline decision states what the
 * increment reached.
 */
package DE4SDV_DriverAssistanceFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def DriverAssistanceIncrement :> EngineeringIncrement;

  part <'INC-DRIVING-002'> driverAssistanceIncrement : DriverAssistanceIncrement {
    doc /*
     * Owner-requested increment on a camera-only driver-assistance application
     * as a candidate for a further member product. VisionPilot of the Autoware
     * Foundation is the application that the owner named. Eclipse S-CORE is
     * the integration path, and CARLA is the enabling closed-loop verification
     * environment. The increment judges the candidate's warning request and
     * braking for a vehicle target, and the collision warning that the AAOS
     * SDV then gives the driver on its display and as a sound. It does not
     * change the Autoware-based AEBS. All phases retain this identity. This
     * package holds Phase 0, the Phase 1 concerns and the baseline decision of
     * Phase 11.
     */
  }

  requirement driverAssistanceProblem : ProblemStatement {
    subject driverAssistanceSubject : DriverAssistanceIncrement;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder complianceEngineer : ComplianceEngineer;
    doc /*
     * The product line holds AEBS for a vehicle target as common content:
     * its requirements ask every member product to detect an imminent
     * forward collision with a vehicle target, to warn the driver and to
     * command emergency braking. A camera-only driver-assistance application
     * is a candidate for a further member product. DE4SDV does not know
     * whether its warning and braking meet those requirements, and the model
     * holds no regulation-derived criteria for a vehicle target to judge
     * them by.
     */
  }

  part driverAssistanceQuestion : IncrementEngineeringQuestion {
    doc /*
     * Does a camera-only driver-assistance application, with its commands on
     * the Eclipse S-CORE command path, request the collision warning and
     * command the braking that the product line requires for a vehicle target,
     * with the warning shown on the AAOS SDV display and sounded, when
     * criteria derived from UNECE R152 judge its closed-loop behavior in
     * simulation? A verdict for each requirement and scenario answers this. A
     * recording of a run that looks right does not.
     */
  }

  part driverAssistanceDecision : IncrementLifecycleDecision {
    doc /*
     * Decide how the candidate goes forward: as a member-product candidate
     * whose own warning and braking stand for the common capability, as a
     * candidate that needs named additions from the platform, or not at all.
     * The decision rests on executed cases with a pass or a fail for each
     * requirement of the increment. The additions are named from the
     * requirements that fail and from the gaps of this increment; the
     * increment builds none of them. A fail is a result to record. It is no
     * reason to change a scenario or a criterion until the candidate passes.
     */
  }

  part def DriverAssistanceSystem {
    doc /*
     * Candidate System 1 boundary. In: the front-camera image and the vehicle
     * speed. Inside: perception of the lane and of the closest object in the
     * path, speed and steering planning, and the warning and braking decision.
     * Out: the driving command and the warning request. Two parts of System 1
     * are outside this boundary, and neither is an enabling system: the
     * Eclipse S-CORE path that carries the driving command to the actuation
     * and the warning request to the AAOS SDV, and the AAOS SDV, which gives
     * the driver the collision warning on its display and as a sound. Phases 6
     * to 8 decide their realization. The candidate is a proposed application
     * system, not a member product: this increment admits no member to the
     * governed product-line scope. Phases 2 and 3 add the actors, the
     * interfaces and the product-line classification.
     */
  }
  part candidateDriverAssistanceSystem : DriverAssistanceSystem;
  /* Rule 5 of the increment workflow, in its dependency form, declared with
   * the system of interest (phase 9): the candidate enters a member product
   * only with the feature visionPilot, which phase 9 added to the feature
   * model. Its requirements follow it; a requirement links a feature of its
   * own only for what this subject does not bring. */
  dependency assistanceSystemOnVisionPilotFeature
    from candidateDriverAssistanceSystem
    to DE4SDV_SDVProductLineFeatureModel::SDVProductLineFeatureTree::platformStack::visionPilot;

  part driverAssistanceScope : IncrementScope {
    doc /*
     * The warning request and the braking of the candidate for a vehicle
     * target ahead in its lane, and the collision warning that the AAOS SDV
     * then gives the driver on its display and as a sound, in closed loop with
     * a rendered camera image, for one configuration and with at most ten
     * requirements. Phase 5 derives those requirements from the product line's
     * requirements on the collision warning, the emergency braking and the
     * false reaction (REQ-AEBS-002, REQ-AEBS-003, REQ-AEBS-008 and
     * REQ-AEBS-012). The scenarios are a stationary target, a slower moving
     * target, and two in which no reaction is due. Closed-loop execution and
     * its evidence belong to Phase 10 of this same increment. A readiness
     * probe comes before the architecture rests on what it tests.
     * Implementation is not part of this framing slice.
     */
  }

  part vehicleTargetResponseInScope : InScopeItem {
    doc /*
     * The warning request and the braking for a stationary and for a slower
     * moving vehicle target ahead.
     */
  }
  part driverWarningInScope : InScopeItem {
    doc /*
     * The collision warning that the AAOS SDV gives the driver in two modes,
     * on its display and as a sound: whether each mode is given, and when,
     * relative to the warning request and to the start of the emergency
     * braking.
     */
  }
  part noReactionInScope : InScopeItem {
    doc /*
     * Two scenarios in which neither a warning nor braking is due, taken from
     * the false-reaction scenarios of the regulation.
     */
  }
  part vehicleTargetCriteriaInScope : InScopeItem {
    doc /*
     * Criteria for a vehicle target derived from UNECE R152, each with what a
     * simulation cannot show.
     */
  }
  part scoreCommandPathInScope : InScopeItem {
    doc /*
     * The candidate's commands reach the simulated vehicle, and its warning
     * request reaches the AAOS SDV, through Eclipse S-CORE; no bypass.
     */
  }
  part verdictEvidenceInScope : InScopeItem {
    doc /*
     * A pass or a fail for each requirement and scenario, bound to the
     * candidate revision that ran.
     */
  }

  part pedestrianAndBicycleTargetsOutOfScope : OutOfScopeItem {
    doc /* Pedestrian and bicycle targets. */
  }
  part cruiseAndLaneKeepingQualityOutOfScope : OutOfScopeItem {
    doc /*
     * How well the candidate holds speed, distance and lane. These functions
     * run; no case judges them.
     */
  }
  part laneDepartureFunctionsOutOfScope : OutOfScopeItem {
    doc /*
     * The candidate's lane-departure warning and lane-departure avoidance.
     * They come with the application; no case judges them.
     */
  }
  part speedAssistanceOutOfScope : OutOfScopeItem {
    doc /*
     * The candidate's intelligent speed assistance, which its documentation
     * bases on speed-limit map data. No run of this increment gives it map
     * data, and no case judges it.
     */
  }
  part handsFreeModeOutOfScope : OutOfScopeItem {
    doc /*
     * The candidate's hands-free mode as a product function: driving one lane
     * of a highway without the driver's hands. The candidate drives the
     * vehicle in the runs, but no case judges the mode.
     */
  }
  part driverInteractionOutOfScope : OutOfScopeItem {
    doc /* Driver monitoring, driver override and deactivation. */
  }
  part furtherWarningProvisionsOutOfScope : OutOfScopeItem {
    doc /*
     * The haptic mode of the collision warning, the regulation's further rules
     * on the warning signals (their description, the failure and
     * unavailability signals, their check at ignition and their visibility in
     * daylight), and whether a driver perceives the warning. The regulation
     * asks for the warning in at least two modes; this increment judges two,
     * the warning on the display and the sound, by whether and when each is
     * given. The product line's requirement of a collision warning to the
     * driver is answered that far and no further.
     */
  }
  part existingAEBSOutOfScope : OutOfScopeItem {
    doc /* Changing the Autoware-based AEBS or reusing its evidence for this candidate. */
  }
  part candidateTuningOutOfScope : OutOfScopeItem {
    doc /*
     * Training the candidate's networks, or tuning the candidate or a
     * scenario until a case passes.
     */
  }
  part onRoadOperationOutOfScope : OutOfScopeItem {
    doc /*
     * On-road operation, production readiness, safety approval, compliance,
     * type approval or certification.
     */
  }

  part driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem {
    doc /*
     * CARLA renders the camera image and moves the vehicle and the targets.
     * Cloud hosts, the scenario runner, the evaluators, the capture of the
     * display and of the sound, and the recordings enable engineering and
     * verification. They are not vehicle features and not contents of the
     * candidate System 1 boundary. The capture observes the AAOS SDV and is no
     * part of it.
     */
  }

  part asmSimulatorPathUsable : IncrementAssumption {
    doc /*
     * The closed-loop simulator path that the application documents works
     * with the simulator release of the driving bench, and the application's
     * commands can be taken from it without a change to its decision logic.
     * A readiness probe tests this first.
     */
  }
  part asmProcessorInferenceSufficient : IncrementAssumption {
    doc /*
     * The application's networks run on a processor alone, without a
     * graphics card, fast enough for its control cycle in closed loop. A
     * readiness probe measures this on the bench host before the bench
     * topology rests on it.
     */
  }
  part asmBenchReuse : IncrementAssumption {
    doc /*
     * The Eclipse S-CORE command path, the actuation adapter and the path to
     * the AAOS SDV display of the closed-loop driving increment, and the
     * evaluator structure of its bench, can carry a second application. They
     * are reuse candidates. Their results for the first application are not
     * evidence for this one. That increment built its path to the display to
     * show the driving state, with no deadline for its delivery; whether the
     * path carries a warning in time is for a readiness probe or Phase 7 to
     * show.
     */
  }
  part asmSimulatedConfigurationStandsIn : IncrementAssumption {
    doc /*
     * The simulated vehicle, its brakes, the road surface and the simulated
     * target stand in for the vehicle, the surface and the test target that
     * the source regulation prescribes. A verdict holds for that simulated
     * configuration only.
     */
  }

  part gapVehicleTargetCriteria : IncrementGap {
    doc /*
     * The regulation-derived criteria of record cover the pedestrian and the
     * bicycle target. None exists for a vehicle target. The AEBS model
     * records as undefined its detection criteria for a vehicle target, the
     * timing, modality and observability of its collision warning, the
     * activation conditions and the braking demand profile of its emergency
     * braking, and its non-activation and false-reaction constraints. It
     * defers the promotion of quantified thresholds into System 1
     * obligations. Phase 5 has to derive the criteria with their provenance:
     * the approach speeds, the target's speed, the time of the warning before
     * the braking, the braking demand and the speed at impact. For the two
     * scenarios without a reaction, the regulation lists false-reaction
     * scenarios for an assessment and gives their parameters as guidance, not
     * as a test. Phase 5 has to select the two and to state their criterion.
     * It also has to state whose obligation each criterion is.
     *
     * At the baseline decision: phase 5 derived the criteria for a vehicle
     * target with their provenance and the owner of each
     * (vehicleTargetCriteriaFixedInPhase5), and the cases of phase 10 read
     * them. The AEBS model still records its criteria for a vehicle target as
     * undefined, and no verdict covers what a simulation cannot show of a
     * criterion. Deferred to a later increment: taking the criteria into the
     * obligations of the product line.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapNoSeparateEmergencyFunction : IncrementGap {
    doc /*
     * At the inspected revision the application marks its forward-collision
     * warning and its emergency braking from the acceleration that its speed
     * planner computes. It has no emergency function apart from that planner.
     * Whether the candidate's braking can stand for the common capability, or
     * the platform has to add an independent function, is open. The lifecycle
     * decision turns on it. The product line also holds the independence of
     * the protected emergency command path as common content. How a candidate
     * whose braking leaves in its one driving command keeps that independence
     * is open as well.
     *
     * At the baseline decision: the realization answers the gap for this
     * candidate (phase8EmergencyFunctionAnswered): the warning and the
     * emergency braking come from the one planned acceleration and leave in the
     * one driving command, and the candidate realizes no independent protected
     * emergency command path (counterClaimNoIndependentEmergencyPath). The
     * cases that judge that braking: VC-DRIVING-036, VC-DRIVING-037 and
     * VC-DRIVING-042 a fail, since in the five judged runs of SC-DRIVING-012
     * the candidate commanded no deceleration beyond 0.53 m/s² before the
     * contact with the stationary target, and VC-DRIVING-041 inconclusive by
     * the rule on dropped images. Deferred to a later increment: whether the
     * candidate's braking can stand for the common capability is for the member
     * decision.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapWarningOutput : IncrementGap {
    doc /*
     * At the inspected revision the application writes its steering and its
     * acceleration to its vehicle interface. That interface carries no
     * warning. The warnings go to the application's own visualization and to
     * its own data log, each only when it is switched on. A warning request at
     * the system boundary, which the AAOS SDV needs, is an output that the
     * application does not have. Whether it can be added without a change to
     * the application's decision logic is open. The data log can give the
     * evaluators a record of the warnings, not the warning for the driver.
     *
     * At the baseline decision: the warning request leaves the candidate
     * through the hand-off that phase 8 placed (phase8WarningOutputPlaced), a
     * change that upstream has not merged. The cases that judge the warning
     * request: VC-DRIVING-042 a fail, since in the five judged runs of
     * SC-DRIVING-012 the candidate started no warning request, and
     * VC-DRIVING-040 and VC-DRIVING-043 inconclusive by the rule on dropped
     * images. The inspected revision has no warning output of its own; whether
     * upstream takes the hand-off is open until its maintainers have seen the
     * draft (gapUpstreamContactAndRights). Deferred to a later increment.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapCandidateBehaviorUnverified : IncrementGap {
    doc /*
     * No closed-loop result of the application exists on the DE4SDV bench, and
     * DE4SDV has run neither the inspected revision nor a change to it. A
     * build that carries a change which upstream has not merged is a different
     * candidate, and its verdicts are reported apart.
     *
     * At the baseline decision: the judged session S1 of 2026-11-21 gives the
     * first closed-loop results of record of the candidate on the DE4SDV bench.
     * Every verdict is of the build 014e0e7a with the DE4SDV S-CORE interface
     * and the visualization recorder, changes that upstream has not merged
     * (phase8CandidateBuildCarriesTheSCOREInterface,
     * phase8VisualizationRecorderPlaced, counterClaimBuildWithUnmergedChanges);
     * the inspected revision without them has run on no DE4SDV bench. Accepted
     * as a known limit; the gap stays open.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }
  part gapScoreIntegration : IncrementGap {
    doc /*
     * The application is one process with its own loop. At the inspected
     * revision it has no binding to Eclipse S-CORE communication and no S-CORE
     * supervision. How its driving command, its warning request and its state
     * enter the S-CORE path without a bypass is open. Phases 6 to 8 decide it
     * after a readiness probe.
     *
     * At the baseline decision: the candidate's process is an Eclipse S-CORE
     * application through the DE4SDV S-CORE interface module, which the Launch
     * Manager starts and supervises (phase8ScoreIntegrationPlaced), and its
     * driving command and its warning request enter the S-CORE path at the
     * boundary of the process. The readiness items that phase 8 left open went
     * on as GAP-DRIVING-014. The cases that judge the path: VC-DRIVING-038 and
     * VC-DRIVING-043, each inconclusive by the rule on dropped images. The stop
     * clause of VC-DRIVING-038 is inconclusive by the same rule: 32 dropped
     * camera images fall inside its judged window, from 2855.010 s to 2897.010
     * s of simulation time, and the stop came at about 2871.06 s, so about 26 s
     * of ticks follow it. The module is a change that upstream has not merged,
     * and the inspected revision has no S-CORE binding of its own. Deferred to
     * a later increment: its take-up upstream.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapCameraImageAndGeometry : IncrementGap {
    doc /*
     * The README of the application's object-detection network names the
     * dataset that the network is trained on. The simulator's images are not
     * images of that dataset. Whether the application detects the simulated
     * target at the distances that the criteria need is not known. Its
     * distance estimate depends on a camera calibration that has to match the
     * simulated camera.
     *
     * At the baseline decision: the cases read the candidate on rendered camera
     * images, with the calibration of the simulated camera. A fail that a
     * mismatch of the image or of the calibration may explain stays a fail: S1
     * does not show whether the detection of the target at the distances that
     * the criteria need, or the calibration, explains the fails of
     * VC-DRIVING-036, VC-DRIVING-037 and VC-DRIVING-042. A verdict holds for
     * the rendered images only (counterClaimRenderedCameraImages). Deferred to
     * a later increment: which of the two explains the fails, if either.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapDeclaredOperatingConditions : IncrementGap {
    doc /*
     * The candidate's documentation declares its hands-free mode only for
     * highways and motorways with clearly marked lane lines, in fair weather
     * and visibility, at up to 70 mph (about 113 km/h) and away from
     * construction zones and roadwork, with a human driver supervising it at
     * all times. Supervision by a driver falls under driver monitoring, which
     * is out of scope (driverInteractionOutOfScope); the road, the weather and
     * the speed place each scenario. The scenarios with a stationary and with
     * a slower moving vehicle target ahead in the lane run on a highway-type
     * road in fair weather, inside these conditions. The two scenarios in
     * which no reaction is due lie outside the declared conditions: a tight
     * curve with guard pipes and a turn at a corner are no highway situations.
     * Both come from the regulation's false-reaction scenarios and stay in the
     * scope. Phase 10 reports the runs outside the declared conditions apart
     * from the runs inside them.
     *
     * At the baseline decision: the runs of SC-DRIVING-014 and SC-DRIVING-015,
     * outside the declared conditions, are reported apart from the runs of
     * SC-DRIVING-012 and SC-DRIVING-013
     * (counterClaimOutsideDeclaredConditions). Reported apart: no run of
     * SC-DRIVING-014 or SC-DRIVING-015 gives a verdict, since the cases that
     * read them judge over the whole run and are inconclusive by the rule on
     * dropped images. Accepted as a known limit; the gap stays open.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }
  part gapCandidateAdmission : IncrementGap {
    doc /*
     * The governed scope holds two planned reference members. Its common
     * content is the AEBS for a vehicle target, the Autoware application, the
     * Linux and ROS 2 runtime of Autoware, the sensing baseline with LiDAR,
     * camera, inertial measurement and wheel odometry, and the independence
     * of the protected emergency command path. A camera-only application that
     * is not the Autoware application does not fit that content. This
     * increment admits no member and changes no scope decision. Phase 3
     * classifies the candidate and names the scope decisions that the owner
     * would have to take. Phase 9 establishes configuration applicability
     * before any member-product claim.
     *
     * At the baseline decision: phase 3 classified the candidate and named the
     * scope decisions (memberDecisionScopeInputs), and phase 9 gave
     * DRIVING-CONFIG-002, a valid configuration that no member decision has
     * taken in. This baseline admits no member product
     * (counterClaimNoMemberProduct), and the member decision that amends ADR
     * 0014 has not been made. Deferred to a later increment.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapUpstreamContactAndRights : IncrementGap {
    doc /*
     * The upstream maintainers are not yet involved. Involve them before
     * deep adoption or vendoring, and show them a result about their project
     * before it is published. The code licence does not clear the terms of
     * the network weights or of the data they were trained on, and those
     * terms are not yet read. No upstream contact, endorsement or rights
     * clearance is asserted.
     *
     * At the baseline decision: by the upstream contact decision of 2026-11-18
     * the VisionPilot maintainers are shown the draft of the warning output and
     * the interface seam, with the results, after the scenarios of phase 10
     * have run in CARLA: at the baseline the maintainers have not seen the
     * results or the draft, and nothing is posted to them before the owner
     * approves its exact text. No endorsement and no rights clearance exists,
     * and the terms of the network weights and of their data are not read
     * (counterClaimNoUpstreamEndorsementOrRights). Deferred to a later
     * increment.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part gapDriverHmiInProductLine : IncrementGap {
    doc /*
     * The feature model holds the HMI display as an optional feature that
     * requires the AAOS SDV guest, and neither governed member selects it,
     * while the product line requires every member product to warn the driver.
     * The owner decided on 2026-11-13 that every member product has an HMI
     * display, realized according to the member's integration mode; that
     * revision of the governed scope is made outside this increment. The
     * Eclipse S-CORE middleware increment assumes that the HMI of the
     * S-CORE-integrated member is the visualization of the AEBS visualization
     * increment, an informational display and not the AEBS driver warning. The
     * AEBS visualization increment keeps that visualization in System 2, out
     * of every System 1 feature configuration. Here the display is System 1
     * content that gives the collision warning, so it is not that
     * visualization. Phase 3 classifies the candidate's display and sound
     * against the scope as it then stands.
     *
     * At the baseline decision: phase 3 classified the display and the sound
     * (driverHmiClassification). The governed scope takes in the display as
     * common content with the scope pull request of ADR 0026, outside this
     * increment, and whether the acoustic warning becomes common content of the
     * driver warning is for the member decision. Deferred to a later increment.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part driverAssistanceCharter : IncrementCharter {
    ref part :>> increment = driverAssistanceIncrement;
    ref part :>> systemOfInterest = candidateDriverAssistanceSystem;
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
      "DE4SDV_DriverAssistanceFraming",
      "DE4SDV_DriverAssistanceOperationalContext",
      "DE4SDV_DriverAssistanceCapabilityClassification",
      "DE4SDV_DriverAssistanceNeedsRequirements",
      "DE4SDV_DriverAssistanceFunctionalArchitecture",
      "DE4SDV_DriverAssistanceLogicalArchitecture",
      "DE4SDV_DriverAssistancePhysicalSoftwareRealization",
      "DE4SDV_DriverAssistanceVariabilityConfiguration",
      "DE4SDV_DriverAssistanceVerificationEvidence"
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

  dependency scopeToDriverAssistanceQuestion
    from driverAssistanceScope to driverAssistanceQuestion;
  dependency driverAssistanceQuestionToProblem
    from driverAssistanceQuestion to driverAssistanceProblem;

  concern driverAssistanceBoundary : IncrementBoundaryConcern {
    subject increment : DriverAssistanceIncrement;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    doc /*
     * Systems engineers and verification engineers need the candidate's
     * judged behavior kept distinct from a demonstration recording, and the
     * framing proposal kept distinct from realized, tested or accepted
     * scope.
     */
  }

  /* Phase 1: one concern per question of the in-scope items, held by the
   * parties whose interest it states, not only by the roles that check the
   * answer. Each is typed by the SAF or DE4SDV concern that asks its question
   * and names the view of a later phase that answers it; that is the
   * viewpoint selection of this phase. The framing viewpoint frames all of
   * them until then. */
  concern vehicleTargetResponseConcern : OperationalCapabilityConcern {
    doc /*
     * vehicleTargetResponseInScope and noReactionInScope, operational part.
     * Vehicle occupants and road users need the vehicle to warn its driver
     * and to brake when a collision with a stationary or a slower moving
     * vehicle ahead in its lane is imminent, and to do neither when no
     * collision is imminent. It states what they expect, not how well the
     * candidate meets it: no safety or on-road claim follows from it.
     * Answered by the operational story of phase 2.
     */
    subject;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
  }

  concern emergencyBrakingIndependenceConcern : PhysicalFunctionalMappingConcern {
    doc /*
     * vehicleTargetResponseInScope, braking part. Safety experts and
     * product-line engineers need to see which software element of the
     * candidate realizes the emergency braking, whether it is a function apart
     * from the speed planner (gapNoSeparateEmergencyFunction), and how its
     * braking command keeps the independence of the protected emergency
     * command path that the product line holds as common content. Whether the
     * candidate's braking can stand for the common capability turns on it, and
     * so does the lifecycle decision. Answered by the physical-logical mapping
     * of phase 8 for the element that realizes the emergency braking, and by
     * the view of the claimed path in phase 8 for the independence of its
     * braking command.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  concern driverWarningSequenceConcern : SystemProcessConcern {
    doc /*
     * driverWarningInScope. The driver, a vehicle occupant, needs a warning
     * of an imminent collision on the display and as a sound. Safety
     * experts need to see the sequence from the candidate's warning request
     * to each of the two modes of the warning and to the start of the
     * emergency braking, and the time between them, independent of the
     * software that realizes it. Phase 5 states the time of the warning
     * before the braking as a criterion. Answered by the system process of
     * phase 6. Whether a driver perceives the warning is out of scope.
     */
    subject;
    stakeholder occupant : VehicleOccupant;
    stakeholder safetyExpert : SafetyExpert;
  }

  concern scoreCommandAndWarningPathConcern : PhysicalInternalExchangeConcern {
    doc /*
     * scoreCommandPathInScope. Systems engineers and product-line engineers
     * need to see the driving command pass from the candidate through Eclipse
     * S-CORE elements to the actuation, and the warning request through S-CORE
     * to the AAOS SDV, with no exchange beside S-CORE, and the boundary
     * interface by which each leaves the candidate. At the inspected revision
     * the candidate has neither a warning output nor an S-CORE binding
     * (gapWarningOutput, gapScoreIntegration), and a run that bypasses S-CORE
     * does not judge the candidate on the command path of the question. The
     * candidate's boundary stays as phase 0 draws it: the path is an internal
     * exchange of the realization that holds the candidate, the S-CORE path
     * and the AAOS SDV, which phases 6 to 8 decide. Answered by the view of
     * the claimed path in phase 8.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
  }

  concern vehicleTargetCriteriaConcern : RegulatoryScopeWithoutComplianceClaimConcern {
    doc /*
     * vehicleTargetCriteriaInScope. Compliance engineers and verification
     * engineers need each criterion for a vehicle target traced to the
     * provision of UNECE R152 it is derived from, with the product-line
     * requirement it judges, whose obligation it is, and what a simulation
     * cannot show of it (gapVehicleTargetCriteria). A criterion met in
     * simulation holds for the simulated configuration only
     * (asmSimulatedConfigurationStandsIn) and is no statement about
     * compliance or type approval. Answered by the requirement definition
     * table of phase 5.
     */
    subject;
    stakeholder complianceEngineer : ComplianceEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  concern candidateVerdictConcern : ArgumentationAssuranceConcern {
    doc /*
     * verdictEvidenceInScope. Product-line engineers and verification
     * engineers need the lifecycle decision to rest on a pass or a fail for
     * each requirement and scenario, each bound to the candidate revision that
     * ran and to the simulated configuration. A build that carries a change
     * that upstream has not merged is a different candidate, with its verdicts
     * reported apart (gapCandidateBehaviorUnverified), and a fail stays a
     * recorded result. A fail that a mismatch of the simulated camera image or
     * of the camera calibration may explain stays a fail, and names
     * gapCameraImageAndGeometry. Answered by the argumentation assurance view
     * of phase 10.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  part driverAssistanceBaselineDecision : IncrementBaselineDecision {
    doc /*
     * BL-DRIVING-002-P11. The baseline of INC-DRIVING-002 accepts the
     * driver-assistance integration as built: the model of phases 0 to 10 and
     * the bench that implements it. VisionPilot at 014e0e7a, built with the
     * DE4SDV S-CORE interface and the visualization recorder, runs as an
     * Eclipse S-CORE application that the Launch Manager starts and supervises;
     * the bench carries its driving command to the simulated vehicle in CARLA
     * 1.0 through the actuation adapter, and its warning request to the AAOS
     * SDV guests, on the Eclipse S-CORE path. This answers the framing decision
     * (driverAssistanceDecision): the candidate goes forward as a candidate
     * that needs the additions named below before it can be the AEBS of a
     * member product, by the decision of 2026-11-21.
     *
     * The evidence it accepts: by the decision of 2026-11-21, the judged
     * session S1, session 20261121T014447Z at bench commit 508649ba, run on
     * 2026-11-21 on the three hosts with 14 judged runs and the run that stops
     * the path, and its records, on the condition that the bench files that ran
     * are byte-identical to those that the second slice of phase 10 merges, the
     * check that the evidence README of that slice states.
     *
     * The verdicts, one for each case: VC-DRIVING-036, VC-DRIVING-037 and
     * VC-DRIVING-042 a fail of the pinned candidate on this bench in
     * simulation: in each of the five judged runs of SC-DRIVING-012 the
     * candidate started no warning request and commanded no deceleration beyond
     * 0.53 m/s², and the contact with the stationary target came at the
     * approach speed (19.7, 40.6, 40.6, 58.6 and 58.6 km/h); the second run at
     * 20 km/h is not judged, its center line 0.245 m from the target's against
     * a limit of 0.2 m. Of SC-DRIVING-013, the first run at 30 km/h is judged
     * and meets the three criteria, since the candidate settled at the target's
     * speed and no collision became imminent; the second run at 30 km/h and
     * both runs at 60 km/h have no functional part and are not judged.
     * VC-DRIVING-038, VC-DRIVING-040, VC-DRIVING-041, VC-DRIVING-043 and
     * VC-DRIVING-044 inconclusive: every run drops 23 or 24 camera images in
     * the first 5 s after its first image, and by the rule of phase 8 no run
     * whose judged window holds a dropped image is judged; for these cases the
     * window is the whole run. Read with that rule set aside, for diagnosis
     * only and as no verdict, VC-DRIVING-038 and VC-DRIVING-044 meet their
     * criteria in all 14 runs, and VC-DRIVING-040, VC-DRIVING-041 and
     * VC-DRIVING-043 in the runs of SC-DRIVING-012 and SC-DRIVING-013.
     * VC-DRIVING-039 a pass, by a desk analysis of the realization in an
     * independent agent session, within its bounds: a loss of a driving command
     * shows only when a later command arrives, a delay of up to 0.1 s of
     * simulation time goes unseen, and the second slice of phase 10 corrects
     * the realization's sentence about later valid commands to what the check
     * value catches.
     *
     * The runs of SC-DRIVING-014 and SC-DRIVING-015 lie outside the candidate's
     * declared operating conditions and are reported apart: no run of either
     * gives a verdict, since VC-DRIVING-038, VC-DRIVING-040, VC-DRIVING-041 and
     * VC-DRIVING-044, the cases that read them, judge over the whole run and
     * are inconclusive by the rule on dropped images. A fail is a recorded
     * result: no scenario, criterion or setting is changed for it
     * (counterClaimNoTuningToPass). The additions named from the requirements
     * that fail and from the gaps of this increment: by the decision of
     * 2026-11-21, a warning and an emergency braking for a stationary vehicle
     * ahead in its lane, and a camera path that keeps every image from a run's
     * first image on, so that the criteria over every run can be judged; the
     * increment builds none of them.
     *
     * Accepted as known limits, still open in this baseline: the verdicts of a
     * build with changes that upstream has not merged
     * (gapCandidateBehaviorUnverified), and the runs outside the declared
     * operating conditions (gapDeclaredOperatingConditions).
     *
     * Deferred to a later increment: the product line's criteria for a vehicle
     * target (gapVehicleTargetCriteria), the member decision on the braking
     * that leaves in the one driving command (gapNoSeparateEmergencyFunction),
     * the upstream take-up of the warning hand-off (gapWarningOutput) and of
     * the S-CORE interface module (gapScoreIntegration), whether the rendered
     * camera images or the calibration of the simulated camera explain the
     * fails (gapCameraImageAndGeometry), the member decision that amends ADR
     * 0014 (gapCandidateAdmission), the upstream contact and the rights
     * clearance (gapUpstreamContactAndRights), the display in the governed
     * scope and the acoustic warning (gapDriverHmiInProductLine), and the
     * readiness items that S1 leaves open: the candidate's cycle on the GPU of
     * the S-CORE host, on which every run drops 23 or 24 camera images in the
     * first 5 s after its first image and up to 2 more inside the run, with no
     * cause shown, what S1 does not show of the start of the sound on the IVI
     * guest, the showing of the results to the VisionPilot maintainers, and the
     * bench item B-1 for the next session, the end of the second runs of
     * SC-DRIVING-013 after 62 ticks at the speed of the target
     * (GAP-DRIVING-014).
     *
     * No gap is withdrawn.
     *
     * No safety, on-road, compliance, type-approval, certification,
     * homologation or membership claim follows from this baseline, and nothing
     * about UNECE R152: a criterion met in simulation holds for the simulated
     * configuration only (asmSimulatedConfigurationStandsIn). The bench is
     * engineering equipment, and its camera images, vehicle dynamics and
     * targets are simulated.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }

  view driverAssistanceFramingView {
    viewpoint driverAssistanceFramingViewpoint : IncrementFramingViewpoint {
      frame driverAssistanceBoundary;
      frame vehicleTargetResponseConcern;
      frame emergencyBrakingIndependenceConcern;
      frame driverWarningSequenceConcern;
      frame scoreCommandAndWarningPathConcern;
      frame vehicleTargetCriteriaConcern;
      frame candidateVerdictConcern;
    }
    expose DriverAssistanceIncrement;
    expose driverAssistanceIncrement;
    expose driverAssistanceProblem;
    expose driverAssistanceQuestion;
    expose driverAssistanceDecision;
    expose driverAssistanceBaselineDecision;
    expose candidateDriverAssistanceSystem;
    expose driverAssistanceScope;
    expose driverAssistanceBoundary;
    expose vehicleTargetResponseConcern;
    expose emergencyBrakingIndependenceConcern;
    expose driverWarningSequenceConcern;
    expose scoreCommandAndWarningPathConcern;
    expose vehicleTargetCriteriaConcern;
    expose candidateVerdictConcern;
    expose vehicleTargetResponseInScope;
    expose driverWarningInScope;
    expose noReactionInScope;
    expose vehicleTargetCriteriaInScope;
    expose scoreCommandPathInScope;
    expose verdictEvidenceInScope;
    expose pedestrianAndBicycleTargetsOutOfScope;
    expose cruiseAndLaneKeepingQualityOutOfScope;
    expose laneDepartureFunctionsOutOfScope;
    expose speedAssistanceOutOfScope;
    expose handsFreeModeOutOfScope;
    expose driverInteractionOutOfScope;
    expose furtherWarningProvisionsOutOfScope;
    expose existingAEBSOutOfScope;
    expose candidateTuningOutOfScope;
    expose onRoadOperationOutOfScope;
    expose driverAssistanceCharter;
    expose driverAssistanceVerificationEnvironment;
    expose asmSimulatorPathUsable;
    expose asmProcessorInferenceSufficient;
    expose asmBenchReuse;
    expose asmSimulatedConfigurationStandsIn;
    expose gapVehicleTargetCriteria;
    expose gapNoSeparateEmergencyFunction;
    expose gapWarningOutput;
    expose gapCandidateBehaviorUnverified;
    expose gapScoreIntegration;
    expose gapCameraImageAndGeometry;
    expose gapDeclaredOperatingConditions;
    expose gapCandidateAdmission;
    expose gapUpstreamContactAndRights;
    expose gapDriverHmiInProductLine;
    render asTreeDiagram;
  }
}
