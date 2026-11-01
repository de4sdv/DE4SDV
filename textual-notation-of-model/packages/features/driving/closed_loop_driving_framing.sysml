/*
 * DE4SDV closed-loop driving capability: Phase 0 framing only.
 * One increment spans framing, realization and CARLA verification.
 * No implementation, runtime result or product-line admission is asserted.
 */
package DE4SDV_ClosedLoopDrivingFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;

  part def ClosedLoopDrivingIncrement :> EngineeringIncrement;

  part <'INC-DRIVING-001'> closedLoopDrivingIncrement : ClosedLoopDrivingIncrement {
    doc /*
     * Owner-requested camera-based automated-driving capability, not a
     * middleware audit or an extension of the existing AEBS behavior.
     * AutoE2E, Eclipse S-CORE and AAOS SDV are integration candidates named
     * by the owner; CARLA is the enabling closed-loop verification environment.
     * All phases retain this identity. This package holds only Phase 0.
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
     */
  }
  part gapModelInputAndFeedback : IncrementGap {
    doc /*
     * A CARLA adapter is not yet realized. Camera calibration, coordinate
     * frames, image and ego-motion history, time alignment and history priming
     * must match the selected checkpoint. Output acceleration/curvature
     * samples are not already CARLA steering commands or world waypoints.
     * Control conversion and feedback need verification. CARLA imagery
     * introduces domain shift; interface compatibility alone cannot establish
     * useful driving, stability or collision outcomes.
     */
  }
  part gapTransportAndControl : IncrementGap {
    doc /*
     * No AutoE2E planning/control contract or AAOS trajectory consumer exists
     * in the existing AEBS path. Later architecture must realize S-CORE on
     * the functional path and avoid a direct planner-to-CARLA bypass. AAOS
     * consumes genuine plan/state/health; its display is not in the fast
     * control loop. Invalid, late, lost or stale plans need a defined
     * stop/disable response in simulation and retained fault-path evidence.
     */
  }
  part gapProductLineAdmission : IncrementGap {
    doc /*
     * ADR 0014 bounds the existing AEBS product line. This proposal does not
     * admit a new member or change that decision. Phase 3 must classify the
     * driving capability and identify needed owner scope decisions; Phase 9
     * must establish configuration applicability before any member-product
     * claim. Simulator or cloud selection must not become a vehicle feature.
     */
  }
  part gapAdoptionAndRights : IncrementGap {
    doc /*
     * Involve the upstream maintainers before deep adoption or vendoring.
     * Pin source, checkpoint and compatible configuration separately and
     * resolve checkpoint/data terms before distribution or public evidence.
     * An open-source code license is not checkpoint-use clearance. No
     * upstream contact, adoption approval or rights clearance is asserted.
     */
  }
  part gapBoundedCloudCampaign : IncrementGap {
    doc /*
     * GPU and KVM host topology is a System 2 candidate, not a selected
     * product deployment. Before a paid run, obtain campaign authorization,
     * check actual capacity, storage and regional cost, refresh credit and
     * enforce a bounded shutdown with evidence exported first. Quota is not
     * spend authorization and budget alerts are not a shutdown mechanism.
     * This framing starts no compute resources and grants no paid-run approval.
     */
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
      MethodPhase::phase11_publication,
      MethodPhase::phase12_baselineNextSlice
    );
    attribute :>> expectedArtifacts = ("DE4SDV_ClosedLoopDrivingFraming");
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
     * Keep the owner-selected closed loop distinct from a trajectory preview,
     * and the framing proposal distinct from realized, tested or accepted scope.
     */
  }

  view closedLoopDrivingFramingView {
    viewpoint closedLoopDrivingFramingViewpoint : IncrementFramingViewpoint {
      frame closedLoopDrivingBoundary;
    }
    expose ClosedLoopDrivingIncrement;
    expose closedLoopDrivingIncrement;
    expose closedLoopDrivingProblem;
    expose closedLoopDrivingQuestion;
    expose closedLoopDrivingDecision;
    expose candidateDrivingSystem;
    expose closedLoopDrivingScope;
    expose closedLoopDrivingBoundary;
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
