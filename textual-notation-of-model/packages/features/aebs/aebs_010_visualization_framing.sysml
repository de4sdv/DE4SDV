/*
 * DE4SDV AEBS visualization increment framing model slice.
 *
 * INC-AEBS-010 frames a bounded, stakeholder-visible AEBS threat and
 * intervention visualization on an AAOS SDV display. This slice is a
 * System 2 engineering-and-evidence increment: it consumes System 1 AEBS
 * behavior but is not a product feature, not a production driver-HMI claim,
 * and not an INC-MW-010 add-on.
 *
 * Predecessor relationship: this increment is the separate capability
 * increment mandated by DE4SDV_Middleware010VerificationEvidence::
 * successorIncrementDecision010. It does not reopen, extend, or retroactively
 * satisfy INC-MW-010 gate 8 or its retained evidence set E-MW-011..E-MW-014.
 */

package DE4SDV_AEBS010VisualizationFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Middleware010VerificationEvidence::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def VisualizationIncrement :> EngineeringIncrement;

  part incAEBS010 : VisualizationIncrement {
    doc /*
     * INC-AEBS-010: AEBS visualization on AAOS SDV — framing through
     * needs and System 2 requirements. Later increments in the same
     * increment chain carry architecture, configuration, implementation,
     * and evidence.
     */
  }

  requirement visualizationProblemStatement : ProblemStatement {
    doc /*
     * How can DE4SDV demonstrate a bounded, stakeholder-visible AEBS threat
     * and intervention visualization on a real AAOS SDV display, consuming
     * live native Autoware AEB output and existing DE4SDV AEBS coordination
     * state, with explicit source provenance, freshness, invalid-input, and
     * provider-loss behavior, without making production driver-HMI, safety,
     * or compliance claims and without altering the closed INC-MW-010
     * baseline?
     */
    subject increment : VisualizationIncrement;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  part visualizationEngineeringQuestion : IncrementEngineeringQuestion {
    doc /*
     * Can a real pinned Autoware AEBS execution and the existing DE4SDV AEBS
     * coordination state be presented as a bounded center-display threat and
     * intervention visualization on a display-capable AAOS SDV member, with
     * honest source provenance and fail-closed degradation behavior?
     */
  }

  part visualizationLifecycleDecision : IncrementLifecycleDecision {
    doc /*
     * Decide whether the visualization increment is framed tightly enough to
     * derive System 2 needs and requirements without dragging architecture,
     * configuration, implementation, or evidence claims into this slice.
     */
  }

  part visualizationScope : IncrementScope {
    doc /*
     * Scope: increment framing, stakeholder concerns, operational scenarios,
     * product-line classification, stakeholder needs, and System 2
     * requirement candidates for the AEBS visualization test system.
     */
  }

  part visualizationTraceabilityShell : IncrementTraceabilityShell {
    doc /*
     * Traceability shell: INC-MW-010 successor decision -> framing ->
     * concerns/views -> operational scenarios -> classification -> needs ->
     * System 2 requirement candidates -> gaps.
     */
  }

  /* Dependency to the mandated predecessor decision (qualified reference,
   * no restatement of predecessor content). */
  dependency successorMandate010
    from incAEBS010 to successorIncrementDecision010;

  dependency framingToProblemStatement010
    from visualizationEngineeringQuestion to visualizationProblemStatement;
  dependency scopeToTraceabilityShell010
    from visualizationScope to visualizationTraceabilityShell;

  part system1ConfiguredAEBSSDVMember : System1SDVProductLine {
    doc /*
     * The configured member product whose live AEBS behavior (native Autoware
     * AEB execution plus DE4SDV AEBS coordination) is observed by the
     * visualization. No member-product behavior is changed by this increment.
     */
  }
  part system2VisualizationInstrument : System2EngineeringAndAssuranceSystem {
    doc /*
     * The visualization test system: source observation, reverse transport,
     * AAOS rendering, health supervision, and evidence recording.
     */
  }
  part system3ReviewEcosystem : System3OpenSourceGovernanceEcosystem;

  part visualizationBoundary : OperationalScopeBoundary;
  part visualizationTestSystemInScope : InScopeItem {
    doc /* Bounded visualization test system observing System 1 AEBS behavior. */
  }
  part sourceProvenancePresentationInScope : InScopeItem {
    doc /* Per-field provenance: native Autoware, DE4SDV AEBS, display-derived. */
  }
  part failureBehaviorInScope : InScopeItem {
    doc /* Stale, unavailable, invalid, and restored display dispositions. */
  }
  part productionDriverHMIOutOfScope : OutOfScopeItem {
    doc /*
     * Production driver-HMI suitability, warning timing/modality, distraction,
     * and human-factors validation remain out of scope.
     */
  }
  part clusterDisplaySafetyOutOfScope : OutOfScopeItem {
    doc /* DriverUI, cluster, HAR, Display Safety, and tell-tale rendering. */
  }
  part mw010RetroactiveClosureOutOfScope : OutOfScopeItem {
    doc /*
     * Any retroactive satisfaction of INC-MW-010 gate 8 or extension of its
     * retained evidence set E-MW-011..E-MW-014.
     */
  }
  part fullAutowareStackOutOfScope : OutOfScopeItem;
  part safetyComplianceClaimOutOfScope : OutOfScopeItem {
    doc /* Safety, ASIL, compliance, certification, homologation claims. */
  }

  part asm010System1Unchanged : IncrementAssumption {
    doc /*
     * ASM-AEBS-010-001: The visualization consumes System 1 AEBS behavior and
     * changes no AEBS detection, warning, intervention, or release behavior.
     */
  }
  part asm010RealSourcesRequired : IncrementAssumption {
    doc /*
     * ASM-AEBS-010-002: Displayed threat state must originate from the pinned
     * native Autoware AEB component and the existing DE4SDV AEBS coordinator;
     * AAOS-originated or display-generated AEBS state is not evidence.
     */
  }
  part asm010BoundedBenchClaim : IncrementAssumption {
    doc /*
     * ASM-AEBS-010-003: Accepted claims remain limited to a deterministic
     * bench environment; no on-road, production, or fleet behavior is claimed.
     */
  }

  part gap010RealizationUnselected : IncrementGap {
    doc /*
     * GAP-AEBS-010-001: No architecture, target, transport, or application
     * realization is selected in this framing slice; deferred to the
     * architecture increment in the same chain.
     */
  }
  part gap010ThresholdsUnpinned : IncrementGap {
    doc /*
     * GAP-AEBS-010-002: Freshness timeouts, restoration counts, frame rates,
     * and transport parameters are named as planning targets only and remain
     * unpinned until the Phase 8/9 configuration work in the chain.
     */
  }
  part gap010EvidenceUnplanned : IncrementGap {
    doc /*
     * GAP-AEBS-010-003: No verification case or evidence artifact exists yet;
     * V&V planning is deferred to the evidence increment in the same chain.
     */
  }

  concern visualizationProvenanceConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * Reviewers need the visualization classified as System 2 engineering and
     * evidence instrumentation, not as a product feature or production HMI.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern visualizationBoundaryConcern : IncrementBoundaryConcern {
    doc /*
     * Reviewers need the framing slice to stay separate from architecture,
     * configuration, implementation, and evidence slices in the same chain.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern predecessorIndependenceConcern : ArgumentationAssuranceConcern {
    doc /*
     * Reviewers need visible assurance that this increment neither reopens
     * INC-MW-010 nor claims its gate 8 reverse path retroactively.
     */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebs010FramingView {
    viewpoint selectedFramingViewpoint : IncrementFramingViewpoint {
      frame visualizationProvenanceConcern;
      frame visualizationBoundaryConcern;
      frame predecessorIndependenceConcern;
    }

    expose VisualizationIncrement::*;
    render asTreeDiagram;
  }
}
