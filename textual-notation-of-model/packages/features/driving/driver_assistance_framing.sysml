/*
 * DE4SDV camera-only driver assistance: Phase 0 framing only.
 * One increment spans framing, realization and closed-loop verification.
 * The framing asserts no implementation, no runtime result, no product-line
 * admission and no compliance.
 */
package DE4SDV_DriverAssistanceFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;

  part def DriverAssistanceIncrement :> EngineeringIncrement;

  part <'INC-DRIVING-002'> driverAssistanceIncrement : DriverAssistanceIncrement {
    doc /*
     * Owner-requested increment on a camera-only driver-assistance
     * application as a candidate for a further member product. VisionPilot
     * of the Autoware Foundation is the application that the owner named.
     * Eclipse S-CORE is the integration path, and CARLA is the enabling
     * closed-loop verification environment. The increment judges the
     * candidate's warning and braking for a vehicle target. It does not
     * change the Autoware-based AEBS. All phases retain this identity. This
     * package holds only Phase 0.
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
     * the Eclipse S-CORE path of the driving bench, meet the product line's
     * requirements to warn of and to brake for a vehicle target, when
     * criteria derived from UNECE R152 judge its closed-loop behavior in
     * simulation? Where it does not, what does the platform have to add?
     * A verdict for each requirement and scenario answers this. A recording
     * of a run that looks right does not.
     */
  }

  part driverAssistanceDecision : IncrementLifecycleDecision {
    doc /*
     * Decide how the candidate goes forward: as a member-product candidate
     * whose own warning and braking stand for the common capability, as a
     * candidate that needs named additions from the platform, or not at all.
     * The decision rests on executed cases with a pass or a fail for each
     * requirement of the increment. A fail is a result to record. It is no
     * reason to change a scenario or a criterion until the candidate passes.
     */
  }

  part def DriverAssistanceSystem {
    doc /*
     * Candidate System 1 boundary. In: the front-camera image and the
     * vehicle speed. Inside: perception of the lane and of the closest
     * vehicle in the path, speed and steering planning, and the warning and
     * braking decision. Out: the driving command and the warning request.
     * It is a proposed application system, not a member product: this
     * increment admits no member to the governed product-line scope.
     * Actors, interfaces and the product-line classification follow in
     * phases 2 and 3.
     */
  }
  part candidateDriverAssistanceSystem : DriverAssistanceSystem;

  part driverAssistanceScope : IncrementScope {
    doc /*
     * Warning and braking of the candidate for a vehicle target ahead in its
     * lane, in closed loop with a rendered camera image, for one
     * configuration and with at most ten requirements. The scenarios are a
     * stationary target, a slower moving target, and two in which no
     * reaction is due. Closed-loop execution and its evidence belong to
     * Phase 10 of this same increment. A readiness probe comes before the
     * architecture rests on what it tests. Implementation is not part of
     * this framing slice.
     */
  }

  part vehicleTargetResponseInScope : InScopeItem {
    doc /*
     * Warning and braking for a stationary and for a slower moving vehicle
     * target ahead.
     */
  }
  part noReactionInScope : InScopeItem {
    doc /* Two scenarios in which neither a warning nor braking is due. */
  }
  part vehicleTargetCriteriaInScope : InScopeItem {
    doc /*
     * Criteria for a vehicle target derived from UNECE R152, each with what a
     * simulation cannot show.
     */
  }
  part scoreCommandPathInScope : InScopeItem {
    doc /*
     * The candidate's commands reach the simulated vehicle through Eclipse
     * S-CORE; no bypass.
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
  part driverInteractionOutOfScope : OutOfScopeItem {
    doc /* Driver monitoring, driver override and deactivation. */
  }
  part warningPresentationOutOfScope : OutOfScopeItem {
    doc /*
     * Presentation of the warning to a driver. The increment judges the
     * warning request at the system boundary.
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
  part roadDeploymentOutOfScope : OutOfScopeItem {
    doc /*
     * On-road operation, production readiness, safety approval, compliance,
     * type approval or certification.
     */
  }

  part driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem {
    doc /*
     * CARLA renders the camera image and moves the vehicle and the targets.
     * Cloud hosts, the scenario runner, the evaluators and the recordings
     * enable engineering and verification. They are not vehicle features and
     * not contents of the candidate System 1 boundary. An AAOS SDV display
     * that shows the warning is an instrument here, not a driver warning
     * function.
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
     * The Eclipse S-CORE path, the actuation adapter and the evaluator
     * structure of the closed-loop driving bench can carry a second
     * application. They are reuse candidates. Their results for the first
     * application are not evidence for this one.
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
     * records its detection, warning, braking and non-activation criteria
     * for a vehicle target as undefined, and it defers the promotion of
     * quantified thresholds into product-line obligations. Phase 5 has to
     * derive the criteria with their provenance: the approach speeds, the
     * target's speed, the time of the warning before the braking, the
     * braking demand and the speed at impact. It also has to state whose
     * obligation each criterion is.
     */
  }
  part gapNoSeparateEmergencyFunction : IncrementGap {
    doc /*
     * At the inspected revision the application marks its forward-collision
     * warning and its emergency braking from the acceleration that its speed
     * planner computes. It has no emergency function apart from that
     * planner. The product line holds a protected emergency command path as
     * common content. Whether the candidate's braking can stand for the
     * common capability, or the platform has to add an independent function,
     * is open. The lifecycle decision turns on it.
     */
  }
  part gapCandidateBehaviorUnverified : IncrementGap {
    doc /*
     * No closed-loop result of the application exists on the DE4SDV bench.
     * The upstream record lists the defects that the project's own open
     * changes report at the inspected revision. A fail is a likely first
     * result. A build that carries a change which upstream has not merged is
     * a different candidate, and its verdicts are reported apart.
     */
  }
  part gapScoreIntegration : IncrementGap {
    doc /*
     * The application is one process with its own loop. At the inspected
     * revision it has no binding to Eclipse S-CORE communication and no
     * S-CORE supervision. How its driving command and its state enter the
     * S-CORE path without a bypass is open. Phases 6 to 8 decide it after a
     * readiness probe.
     */
  }
  part gapCameraImageAndGeometry : IncrementGap {
    doc /*
     * The application's object detection was trained on recorded road
     * images. The simulator's images differ from them. Whether the
     * application detects the simulated target at the distances that the
     * criteria need is not known. Its distance estimate depends on a camera
     * calibration that has to match the simulated camera.
     */
  }
  part gapProductLineAdmission : IncrementGap {
    doc /*
     * The governed scope admits two member products and holds the Autoware
     * application, the sensing baseline and the protected emergency command
     * path as common content. A camera-only application that is not the
     * Autoware application does not fit that content. This increment admits
     * no member and changes no scope decision. Phase 3 classifies the
     * candidate and names the scope decisions that the owner would have to
     * take. Phase 9 establishes configuration applicability before any
     * member-product claim.
     */
  }
  part gapAdoptionAndRights : IncrementGap {
    doc /*
     * The upstream maintainers are not yet involved. Involve them before
     * deep adoption or vendoring, and show them a result about their project
     * before it is published. The code licence does not clear the terms of
     * the network weights or of the data they were trained on, and those
     * terms are not yet read. No upstream contact, endorsement or rights
     * clearance is asserted.
     */
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
    attribute :>> expectedArtifacts = ("DE4SDV_DriverAssistanceFraming");
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

  view driverAssistanceFramingView {
    viewpoint driverAssistanceFramingViewpoint : IncrementFramingViewpoint {
      frame driverAssistanceBoundary;
    }
    expose DriverAssistanceIncrement;
    expose driverAssistanceIncrement;
    expose driverAssistanceProblem;
    expose driverAssistanceQuestion;
    expose driverAssistanceDecision;
    expose candidateDriverAssistanceSystem;
    expose driverAssistanceScope;
    expose driverAssistanceBoundary;
    expose vehicleTargetResponseInScope;
    expose noReactionInScope;
    expose vehicleTargetCriteriaInScope;
    expose scoreCommandPathInScope;
    expose verdictEvidenceInScope;
    expose pedestrianAndBicycleTargetsOutOfScope;
    expose cruiseAndLaneKeepingQualityOutOfScope;
    expose driverInteractionOutOfScope;
    expose warningPresentationOutOfScope;
    expose existingAEBSOutOfScope;
    expose candidateTuningOutOfScope;
    expose roadDeploymentOutOfScope;
    expose driverAssistanceCharter;
    expose driverAssistanceVerificationEnvironment;
    expose asmSimulatorPathUsable;
    expose asmProcessorInferenceSufficient;
    expose asmBenchReuse;
    expose asmSimulatedConfigurationStandsIn;
    expose gapVehicleTargetCriteria;
    expose gapNoSeparateEmergencyFunction;
    expose gapCandidateBehaviorUnverified;
    expose gapScoreIntegration;
    expose gapCameraImageAndGeometry;
    expose gapProductLineAdmission;
    expose gapAdoptionAndRights;
    render asTreeDiagram;
  }
}
