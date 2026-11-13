/*
 * DE4SDV closed-loop driving capability: Phase 0 framing, Phase 1 concerns and
 * the baseline decision of Phase 11.
 * One increment spans framing, realization and CARLA verification.
 * The framing asserts no implementation, runtime result or product-line
 * admission; the baseline decision states what the increment reached.
 */
package DE4SDV_ClosedLoopDrivingFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def ClosedLoopDrivingIncrement :> EngineeringIncrement;

  part <'INC-DRIVING-001'> closedLoopDrivingIncrement : ClosedLoopDrivingIncrement {
    doc /*
     * Owner-requested camera-based automated-driving capability, not a
     * middleware audit or an extension of the existing AEBS behavior.
     * AutoE2E, Eclipse S-CORE and AAOS SDV are integration candidates named
     * by the owner; CARLA is the enabling closed-loop verification environment.
     * All phases retain this identity. This package holds Phase 0, the
     * Phase 1 concerns and the baseline decision of Phase 11.
     */
  }

  requirement closedLoopDrivingProblem : ProblemStatement {
    subject closedLoopDrivingSubject : ClosedLoopDrivingIncrement;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder maintainer : Maintainer;
    doc /*
     * How can DE4SDV demonstrate a camera-based driving capability in which
     * learned plans actually determine simulated vehicle commands through
     * the integration path, while an operator observes genuine plan, vehicle
     * and health state, with usable wall-clock timing and explicit behavior
     * when input or planning becomes unavailable?
     */
  }

  part closedLoopDrivingQuestion : IncrementEngineeringQuestion {
    doc /*
     * Can a real, pinned AutoE2E checkpoint influence steering and acceleration
     * in CARLA through an Eclipse S-CORE planning/control path, with actual
     * plan/state/health delivered to AAOS SDV Core, Gateway and IVI, while
     * the scene progresses at wall-clock pace and supports genuine smooth
     * capture? A prediction overlay on CARLA autopilot does not answer this.
     */
  }

  part closedLoopDrivingDecision : IncrementLifecycleDecision {
    doc /*
     * Decide whether to retain the proposed closed-loop integration after
     * evidence for inference feasibility, observed feedback, bounded stale-plan
     * handling and honest timing. An infeasible model or integration calls
     * for an explicit redirect or hold, not an undisclosed autopilot substitute.
     */
  }

  part def ClosedLoopDrivingSystem {
    doc /*
     * Candidate System 1 driving-function boundary: camera/ego-state input,
     * learned planning, command execution and operational-state publication.
     * This is a proposed application/control system, not a new vehicle product
     * line or an admitted member of the existing AEBS product line. Detailed
     * actors, interfaces and product-line classification follow in phases 2/3.
     */
  }
  part candidateDrivingSystem : ClosedLoopDrivingSystem;

  part closedLoopDrivingScope : IncrementScope {
    doc /*
     * One bounded closed-loop driving scenario with real model inference,
     * S-CORE on the functional planning/control path, and genuine AAOS SDV
     * observation. CARLA execution and its evidence belong to Phase 10 of
     * this same increment. Readiness probes are brought forward to phases
     * 6 through 8; implementation is not part of this framing slice.
     */
  }

  part learnedDrivingInScope : InScopeItem {
    doc /* Real checkpoint output influences vehicle actuation; no hidden bypass. */
  }
  part integrationAndObservationInScope : InScopeItem {
    doc /* S-CORE functional-path integration and AAOS plan/state/health observation. */
  }
  part feedbackAndTimingInScope : InScopeItem {
    doc /* Closed-loop behavior, failure handling and separately measured time domains. */
  }
  part closedLoopEvidenceInScope : InScopeItem {
    doc /* CARLA scenarios, reproducible configuration, hop logs and actual capture. */
  }

  part roadDeploymentOutOfScope : OutOfScopeItem {
    doc /* On-road operation, production readiness, safety approval or certification. */
  }
  part existingAEBSBehaviorOutOfScope : OutOfScopeItem {
    doc /* Changing AEBS emergency intervention or reusing its evidence as driving proof. */
  }
  part modelTrainingOutOfScope : OutOfScopeItem {
    doc /* New training, dataset acquisition campaigns or an undisclosed checkpoint swap. */
  }

  part closedLoopVerificationEnvironment : System2EngineeringAndAssuranceSystem {
    doc /*
     * CARLA sensor rendering and vehicle dynamics, candidate cloud GPU and
     * KVM hosts, integration instrumentation and capture enable engineering
     * and verification. They are not vehicle features or contents of the
     * candidate System 1 driving-function boundary. AAOS observation uses
     * real software, without declaring a production driver-HMI capability.
     */
  }

  part asmEngineeringUse : IncrementAssumption {
    doc /*
     * The candidate driving function belongs to System 1; the simulator,
     * cloud bench and evidence instruments belong to System 2. The first
     * intended use is controlled software-in-the-loop engineering. It is
     * production-oriented in functional causality, not production-ready.
     */
  }
  part asmSourceAuthenticity : IncrementAssumption {
    doc /*
     * A pinned checkpoint and its compatible input geometry/history are the
     * inference source. Actual predictions, commands and observation data
     * are retained. Random weights, synthetic-input speed results, repeated
     * camera histories and CARLA autopilot are not substitutes for that source.
     * The history carries one bounded deviation (owner decision of
     * 2026-11-09): the checkpoint gets the ego-motion history with its yaw
     * rate and curvature as zero, because its own yaw history, fed back in the
     * closed loop, turned its plans off the lane. GAP-DRIVING-010 records the
     * deviation and the trigger to revisit it.
     */
  }
  part asmCandidateReuse : IncrementAssumption {
    doc /*
     * The existing S-CORE and AAOS SDV integration is a reuse candidate,
     * not trajectory transport evidence and not safety evidence. Reuse must
     * preserve its Linux/Android execution-domain separation and explicit
     * unqualified integration assumptions. Its AEBS claims remain unchanged.
     */
  }

  part gapClosedLoopPerformance : IncrementGap {
    doc /*
     * Performance is unmeasured on the combined bench. Planning objectives
     * are at least 20 fresh rendered frames per wall-clock second and a
     * 24 fps live-capture target, without retiming a slow simulation. They
     * do not require or prove 24 new predictions per second. Rendering and
     * capture rates, inference cadence, simulation real-time factor,
     * input-to-actuation age and AAOS observation age need separate evidence.
     * Trajectory sample spacing is not model invocation rate. Phase 5 must
     * fix scenario, resolution, duration, measurement windows, drop tolerance,
     * control deadlines and freshness limits before the readiness probe.
     * Poor checkpoint performance is an early hold/redirect condition, not
     * a reason to replace closed-loop actuation with a prediction overlay.
     *
     * At the baseline decision: the planning period is measured on the bench
     * host, and GAP-DRIVING-013 states the runs and their margin. The
     * rendered frame rate and the capture rate of the simulator are not
     * judged: no requirement and no verification case carries the 20 rendered
     * frames per second or the 24 fps capture target. Nothing measured is
     * real-time operation on target hardware or a performance promise
     * (counterClaimNoRealTimeOnTarget). Accepted as a known limit; the gap
     * stays open.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }
  part gapModelInputAndFeedback : IncrementGap {
    doc /*
     * A CARLA adapter is not yet realized. Camera calibration, coordinate
     * frames, image and ego-motion history, time alignment and history priming
     * must match the selected checkpoint; the ego-motion history is read
     * through the bounded deviation of asmSourceAuthenticity. Output
     * acceleration/curvature samples are not already CARLA steering commands
     * or world waypoints.
     * Control conversion and feedback need verification. CARLA imagery
     * introduces domain shift; interface compatibility alone cannot establish
     * useful driving, stability or collision outcomes.
     *
     * At the baseline decision: the conversions between the simulator and the
     * checkpoint are realized where phase 8 placed them
     * (phase8ConversionPlacement) and ran in the closed loop. The runs found
     * two errors of the bench, one in the control conversion and one in the
     * actuation conversion, and both were corrected (GAP-DRIVING-012). What
     * this gap warned of holds: with matching interfaces the pinned
     * checkpoint needs the bounded deviation of its motion history
     * (GAP-DRIVING-010), takes no turn from the route (GAP-DRIVING-011) and
     * keeps no lane (GAP-DRIVING-012). The degraded-input cases cover the
     * faults they inject and no other (counterClaimBoundedFaults). Accepted
     * as a known limit; the gap stays open.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }
  part gapTransportAndControl : IncrementGap {
    doc /*
     * No AutoE2E planning/control contract or AAOS trajectory consumer exists
     * in the existing AEBS path. Later architecture must realize S-CORE on
     * the functional path and avoid a direct planner-to-CARLA bypass. AAOS
     * consumes genuine plan/state/health; its display is not in the fast
     * control loop. Invalid, late, lost or stale plans need a defined
     * stop/disable response in simulation and retained fault-path evidence.
     *
     * At the baseline decision: the design this gap asks for exists. S-CORE
     * is on the functional path (phase8TransportSettled), the observer on the
     * IVI VM consumed the typed plan, vehicle state and health in two runs
     * (GAP-DRIVING-006), and REQ-DRIVING-020 to REQ-DRIVING-029 define the
     * stop response. The evidence it asks for is incomplete: no recorded run
     * has judged that plans and commands pass over S-CORE (VC-DRIVING-014),
     * the stop on lost commands (VC-DRIVING-028), or that planning is
     * independent of the observation (VC-DRIVING-018 and VC-DRIVING-019).
     * Deferred to a later increment with those runs.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapProductLineAdmission : IncrementGap {
    doc /*
     * ADR 0014 bounds the existing AEBS product line. This proposal does not
     * admit a new member or change that decision. Phase 3 must classify the
     * driving capability and identify needed owner scope decisions; Phase 9
     * must establish configuration applicability before any member-product
     * claim. Simulator or cloud selection must not become a vehicle feature.
     *
     * At the baseline decision: phase 3 classified the capability and named
     * the owner scope decisions (memberDecisionScopeInputs), and phase 9 gave
     * DRIVING-CONFIG-001, a valid configuration that is not admitted. The
     * member decision that amends ADR 0014 has not been made, and this
     * baseline admits no member product (counterClaimNoMembership). Deferred
     * to a later increment.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapAdoptionAndRights : IncrementGap {
    doc /*
     * Involve the upstream maintainers before deep adoption or vendoring.
     * Pin source, checkpoint and compatible configuration separately and
     * resolve checkpoint/data terms before distribution or public evidence.
     * An open-source code license is not checkpoint-use clearance. No
     * upstream contact, adoption approval or rights clearance is asserted.
     *
     * At the baseline decision: DE4SDV posted in the upstream repositories on
     * 2026-11-11 (upstream.md of this folder, Upstream contact). No adoption
     * approval and no rights clearance exists, and the checkpoint's terms
     * stay unresolved (counterClaimCheckpointRightsAndTransfer). Deferred to
     * a later increment.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }
  part gapBoundedCloudCampaign : IncrementGap {
    doc /*
     * GPU and KVM host topology is a System 2 candidate, not a selected
     * product deployment. Before a paid run, obtain campaign authorization,
     * check actual capacity, storage and regional cost, refresh credit and
     * enforce a bounded shutdown with evidence exported first. Quota is not
     * spend authorization and budget alerts are not a shutdown mechanism.
     * This framing starts no compute resources and grants no paid-run approval.
     *
     * At the baseline decision: the owner authorized the campaign and its
     * runs were made. The owner ended the runs of this increment on
     * 2026-11-11 and keeps the remaining allowance for a later increment; the
     * machines are stopped, not deleted. Deferred with that allowance: a
     * further paid run needs the same conditions.
     */
    attribute :>> disposition = LifecycleDisposition::deferred;
  }

  part closedLoopDrivingCharter : IncrementCharter {
    ref part :>> increment = closedLoopDrivingIncrement;
    ref part :>> systemOfInterest = candidateDrivingSystem;
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
      "DE4SDV_ClosedLoopDrivingFraming",
      "DE4SDV_ClosedLoopDrivingOperationalContext",
      "DE4SDV_ClosedLoopDrivingCapabilityClassification",
      "DE4SDV_ClosedLoopDrivingNeedsRequirements",
      "DE4SDV_ClosedLoopDrivingFunctionalArchitecture",
      "DE4SDV_ClosedLoopDrivingLogicalArchitecture",
      "DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization",
      "DE4SDV_ClosedLoopDrivingVariabilityConfiguration",
      "DE4SDV_ClosedLoopDrivingVerificationEvidence"
    );
    attribute :>> expectedReviewEvidence = (
      "independent review of the owner question, System 1/2 boundary and nonclaims",
      "repository, smoke and focused regression checks on the reviewed changes",
      "exact-head licensed SysML validation and Syside-generated framing view"
    );
    doc /*
     * Expected artifacts name only content present now, not future packages.
     * Review evidence is expected, not asserted available by this declaration.
     */
  }

  dependency scopeToDrivingQuestion
    from closedLoopDrivingScope to closedLoopDrivingQuestion;
  dependency drivingQuestionToProblem
    from closedLoopDrivingQuestion to closedLoopDrivingProblem;

  concern closedLoopDrivingBoundary : IncrementBoundaryConcern {
    subject increment : ClosedLoopDrivingIncrement;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    doc /*
     * Systems engineers and verification engineers need the owner-selected
     * closed loop kept distinct from a trajectory preview, and the framing
     * proposal kept distinct from realized, tested or accepted scope.
     */
  }

  /* Phase 1: one concern per question of the in-scope items, held by the
   * stakeholders whose interest it states, not only by the roles that check
   * the answer. Each is typed by the SAF concern that asks its question; the
   * views of later phases answer it. The framing viewpoint frames all of them
   * until then. */
  concern drivenAlongTheRouteConcern : OperationalCapabilityConcern {
    doc /*
     * learnedDrivingInScope, operational part. Vehicle occupants need the
     * vehicle to take them along the route to the destination the driver
     * chose on navigation, steered and accelerated by the driving system's
     * own plans. It states what the occupants expect, not how well the
     * vehicle drives: no driving-quality, safety or on-road claim follows
     * from it. Answered by the operational story of phase 2.
     */
    subject;
    stakeholder occupant : VehicleOccupant;
  }

  concern checkpointCommandAuthorityConcern : PhysicalFunctionalMappingConcern {
    doc /*
     * learnedDrivingInScope. Systems engineers, verification engineers and
     * open-source reviewers need to see that the pinned AutoE2E checkpoint's
     * planning output is what determines steering and acceleration in CARLA,
     * with no autopilot, replay or other source of commands in between.
     * Answered by the physical-functional mapping of phase 8.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern scoreCommandPathConcern : PhysicalInternalExchangeConcern {
    doc /*
     * integrationAndObservationInScope, S-CORE part. System architects,
     * software developers and maintainers need to see that the plan and
     * command items pass through Eclipse S-CORE elements between the planner
     * and actuation, not beside them: an exchange that skips S-CORE means
     * S-CORE is not on the path. Answered by the physical internal exchanges
     * of phase 8.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder maintainer : Maintainer;
  }

  concern aaosObservationFidelityConcern : PhysicalContextExchangeConcern {
    doc /*
     * integrationAndObservationInScope, AAOS part. The driver, a vehicle
     * occupant, needs the plan, vehicle state and health shown on AAOS SDV
     * to be those of the running loop. Verification engineers and
     * open-source reviewers need to see which items cross to AAOS SDV Core,
     * Gateway and IVI and from which producer; a mock or replayed stream does
     * not count. Typed for AAOS as a context role of the driving system; if
     * phase 2 places AAOS inside the boundary, the question becomes a
     * physical internal exchange.
     */
    subject;
    stakeholder occupant : VehicleOccupant;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern degradedInputBehaviorConcern : FunctionalBehaviorConcern {
    doc /*
     * feedbackAndTimingInScope, behavior part. Vehicle occupants and road
     * users need the vehicle to stop or the function to disable in a
     * defined way when camera input, ego state, the route or the plan
     * becomes invalid, lost or stale, instead of acting on the last plan.
     * Safety experts and system architects need to see which function
     * detects it, how old an input may be, and how the vehicle stops or the
     * function disables, independent of the software that implements it.
     * No safety claim follows from it.
     */
    subject;
    stakeholder occupant : VehicleOccupant;
    stakeholder roadUser : RoadUser;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemArchitect : SystemArchitect;
  }

  concern timeDomainHonestyConcern : ArgumentationAssuranceConcern {
    doc /*
     * feedbackAndTimingInScope, timing part. Verification engineers and
     * systems engineers need each timing claim to name its time domain:
     * simulation time, rendered frames, inference cadence, transport latency,
     * input-to-actuation age and wall clock are measured separately, so that
     * no real-time claim rests on a single number or on another domain's
     * measurement.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
  }

  concern reproducibleClosedLoopEvidenceConcern : ArgumentationAssuranceConcern {
    doc /*
     * closedLoopEvidenceInScope. Verification engineers, maintainers and
     * open-source reviewers need the closed-loop claims tied to evidence
     * another engineer can rerun: pinned scenarios, configuration and
     * checkpoint, per-hop logs and the actual capture, with every failed or
     * missing run kept as a gap rather than dropped.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  part closedLoopDrivingBaselineDecision : IncrementBaselineDecision {
    doc /*
     * BL-DRIVING-001-P11. The baseline of INC-DRIVING-001 accepts the
     * closed-loop driving integration as built: the model of phases 0 to 10
     * and the bench that implements it. The pinned AutoE2E checkpoint plans
     * inside an Eclipse S-CORE FEO agent, its commands reach the simulated
     * vehicle through the actuation adapter alone, and plan, vehicle state
     * and health reach the observer on the IVI VM of AAOS SDV as a typed
     * message. This answers the framing decision (closedLoopDrivingDecision):
     * the integration is retained, on the drafts named below and not on
     * evidence of record.
     *
     * It accepts no evidence. The increment closes without evidence records:
     * the owner ended its runs on 2026-11-11, the recorded runs were made on
     * the bench's branches before the merge, and the merged bench has not
     * run. Every verification case and every requirement keeps NotStarted.
     * The verdicts of the bench's evaluators are drafts: in the three
     * closed-loop runs after the corrections of GAP-DRIVING-012, 12 of the 23
     * cases those runs judge pass in all three, VC-DRIVING-001 fails in two,
     * and VC-DRIVING-002, -005, -011, -012, -016 and -033 are inconclusive in
     * all three for evidence the runs did not record. Twelve cases have no
     * pass and no fail in any recorded run: those six and VC-DRIVING-035,
     * inconclusive wherever they were judged; VC-DRIVING-014, -024 and -028,
     * whose faults no run injected; and VC-DRIVING-018 and -019, whose runs
     * were not made.
     *
     * Accepted as known limits, still open in this baseline: the bounded
     * deviation of the motion history (GAP-DRIVING-010), the route from which
     * the checkpoint takes no turn (GAP-DRIVING-011), the lane it does not
     * keep (GAP-DRIVING-012), the planning period kept with almost no margin
     * (GAP-DRIVING-013), the performance limits of gapClosedLoopPerformance
     * and the input and feedback limits of gapModelInputAndFeedback.
     *
     * Deferred to a later increment: FEO outside the pinned S-CORE baseline
     * (GAP-DRIVING-001), the unproven parity of the planner stack
     * (GAP-DRIVING-003), the evidence of record for the typed topic
     * (GAP-DRIVING-006), the three-host bench on the merged tree
     * (GAP-DRIVING-007), the environment's identity in the evidence record
     * (GAP-DRIVING-009), the runs gapTransportAndControl still asks for, the
     * member decision of gapProductLineAdmission, the clearances of
     * gapAdoptionAndRights and the campaign of gapBoundedCloudCampaign.
     *
     * No gap is withdrawn.
     *
     * No driving-quality, real-time, safety, certification, compliance,
     * homologation or membership claim follows from this baseline, and no
     * acceptance of evidence. The bench is engineering equipment, and its
     * sensors and vehicle dynamics are simulated.
     */
    attribute :>> disposition = LifecycleDisposition::accepted;
  }

  view closedLoopDrivingFramingView {
    viewpoint closedLoopDrivingFramingViewpoint : IncrementFramingViewpoint {
      frame closedLoopDrivingBoundary;
      frame drivenAlongTheRouteConcern;
      frame checkpointCommandAuthorityConcern;
      frame scoreCommandPathConcern;
      frame aaosObservationFidelityConcern;
      frame degradedInputBehaviorConcern;
      frame timeDomainHonestyConcern;
      frame reproducibleClosedLoopEvidenceConcern;
    }
    expose ClosedLoopDrivingIncrement;
    expose closedLoopDrivingIncrement;
    expose closedLoopDrivingProblem;
    expose closedLoopDrivingQuestion;
    expose closedLoopDrivingDecision;
    expose closedLoopDrivingBaselineDecision;
    expose candidateDrivingSystem;
    expose closedLoopDrivingScope;
    expose closedLoopDrivingBoundary;
    expose drivenAlongTheRouteConcern;
    expose checkpointCommandAuthorityConcern;
    expose scoreCommandPathConcern;
    expose aaosObservationFidelityConcern;
    expose degradedInputBehaviorConcern;
    expose timeDomainHonestyConcern;
    expose reproducibleClosedLoopEvidenceConcern;
    expose learnedDrivingInScope;
    expose integrationAndObservationInScope;
    expose feedbackAndTimingInScope;
    expose closedLoopEvidenceInScope;
    expose roadDeploymentOutOfScope;
    expose existingAEBSBehaviorOutOfScope;
    expose modelTrainingOutOfScope;
    expose closedLoopDrivingCharter;
    expose closedLoopVerificationEnvironment;
    expose asmEngineeringUse;
    expose asmSourceAuthenticity;
    expose asmCandidateReuse;
    expose gapClosedLoopPerformance;
    expose gapModelInputAndFeedback;
    expose gapTransportAndControl;
    expose gapProductLineAdmission;
    expose gapAdoptionAndRights;
    expose gapBoundedCloudCampaign;
    render asTreeDiagram;
  }
}
