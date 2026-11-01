package DE4SDV_MiddlewareSCOREConditionsFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def SCOREMiddlewareConditionsIncrement :> EngineeringIncrement;

  part <'INC-MW-012'> scoreMiddlewareConditionsIncrement : SCOREMiddlewareConditionsIncrement {
    doc /*
     * INC-MW-012: the conditions under which the S-CORE HMI path was not
     * verified. INC-MW-011 realized the path and closed with one nominal
     * window; its baseline accepted that window and deferred the adversarial,
     * degraded and isolation conditions. This increment answers whether the
     * path keeps its delivery, ordering, discard and isolation claims when
     * the middleware is offered a service by a sender that is not the host,
     * when the subscriber disappears or restarts, and at the host-to-guest
     * isolation boundary. It realizes no new architecture: the layer it
     * verifies is the one INC-MW-011 realized.
     */
  }

  requirement scoreMiddlewareConditionsProblemStatement : ProblemStatement {
    doc /*
     * The S-CORE HMI path of the member product has been shown to deliver in
     * one nominal window. It has not been shown to behave under the
     * conditions an on-board middleware meets in service: a SOME/IP service
     * offer that does not come from the host, a subscriber that stops reading
     * or a guest that restarts, and the boundary that keeps each guest off the
     * host's discovery and frame ports.
     *
     * Without that, the path's delivery claim rests on a single benign run,
     * the verification cases that name the adversarial and degraded
     * conditions stay inconclusive, and a reader cannot tell a bounded
     * demonstration from a property of the design.
     */
    subject increment : SCOREMiddlewareConditionsIncrement;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  part scoreMiddlewareConditionsEngineeringQuestion : IncrementEngineeringQuestion {
    doc /*
     * Under the conditions INC-MW-011 deferred - a service offer from a
     * sender that is not the host, a subscriber that is down at the HMI, at
     * the IVI VM or at the SDV Core VM, a restart of that pair, and the
     * host-to-guest isolation boundary - does the S-CORE HMI path keep the
     * delivery, ordering, discard and isolation behaviour its requirements
     * state, and which of those conditions shows a defect that the baseline
     * must carry as an open gap?
     */
  }

  part scoreMiddlewareConditionsLifecycleDecision : IncrementLifecycleDecision {
    doc /*
     * Decide whether the S-CORE HMI path may be described as holding its
     * delivery and isolation claims under the named conditions, or only under
     * the nominal one, and what each condition leaves open. The decision is
     * about evidence and claim boundary, never about certification, safety
     * integrity or product admission.
     */
  }

  part asmNominalWindowIsTheBaseline : IncrementAssumption {
    doc /*
     * ASM-MW-033: the retained nominal window of INC-MW-011 is the baseline
     * each condition is compared against. Its frames reached the HMI in order
     * and byte-identical, and the guest clock was stepped immediately before
     * it, so a difference observed under a condition is a difference of that
     * condition and not of the clock. A condition runs with the same clock
     * discipline; a window whose clock is not stepped before it is
     * inconclusive, not a pass and not a fail.
     */
  }

  concern scoreConditionsEvidenceBoundaryConcern : RequirementTraceConcern {
    doc /*
     * Reviewers need to see, per condition, what was exercised, what the
     * middleware was asked to accept or refuse, and what the path did - so
     * that the increment's claim is read as the set of conditions that were
     * actually run, and a condition that was not run stays visibly unrun.
     */
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder reviewer : OpenSourceReviewer;
  }

  part scoreMiddlewareConditionsScope : IncrementScope {
    doc /* The scope of INC-MW-012: the conditions the path is exercised under, the evidence of record for the nominal path it compares against, and the isolation boundary. The architecture it verifies is INC-MW-011's and is not re-realized here. */

    part adversarialOfferInScope : InScopeItem {
      doc /*
       * The SOME/IP service the host half offers, exercised against an offer
       * from a sender that is not the host: whether the guest stack takes the
       * spoofed service, and whether a frame the host never produced can
       * reach the HMI.
       */
    }

    part subscriberConditionsInScope : InScopeItem {
      doc /*
       * The subscriber side: the HMI application down, the IVI VM down, the
       * SDV Core VM down, and a restart of the pair, each compared against the
       * nominal window for delivery, ordering and the discard rule of the
       * relay.
       */
    }

    part isolationBoundaryInScope : InScopeItem {
      doc /*
       * The boundary that keeps each guest off the host's DDS ports and off
       * the frame assembler's port, with the expected set the owner names for
       * the mesh, the data tunnel and the RPC surface.
       */
    }

    part nominalEvidenceInScope : InScopeItem {
      doc /*
       * The nominal window of INC-MW-011 registered as evidence of record, so
       * that the conditions above are read against a retention the model
       * points at rather than against prose.
       */
    }

    part upstreamDefectsOutOfScope : OutOfScopeItem {
      doc /*
       * The S-CORE behaviours GAP-MW-039 to GAP-MW-042 record, and the
       * unreleased S-CORE gateway of GAP-MW-036. They are upstream work; this
       * increment observes their effect at the bench and does not fix them.
       */
    }

    part performanceOutOfScope : OutOfScopeItem {
      doc /* Throughput, latency budgets and resource use. The increment states behaviour, not performance. */
    }
  }

  part scoreMiddlewareConditionsCharter : IncrementCharter {
    doc /*
     * Charter declaration of INC-MW-012; traces are the native relationships
     * of this package. The applicable phases are framing, needs,
     * requirements, verification evidence, publication and the baseline
     * decision. Phases 1 to 3 and 6 to 9 are not declared: this increment
     * adds no concern framing beyond the one in this package, no capability,
     * and no architecture - the layer it verifies is INC-MW-011's, and its
     * physical realization, configuration and platform stack are that
     * increment's. Owner, expected artifacts and expected review evidence are
     * declarations, not completion or review evidence.
     */
    attribute :>> applicablePhases = (MethodPhase::phase0_incrementFraming, MethodPhase::phase4_needs, MethodPhase::phase5_requirements, MethodPhase::phase10_vvEvidence, MethodPhase::phase11_publication, MethodPhase::phase12_baselineNextSlice);
    ref part :>> increment = DE4SDV_MiddlewareSCOREConditionsFraming::scoreMiddlewareConditionsIncrement;
    ref part :>> systemOfInterest = DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    attribute :>> owner = "DE4SDV maintainers";
    attribute :>> expectedArtifacts = ("DE4SDV_MiddlewareSCOREConditionsFraming", "DE4SDV_MiddlewareSCOREConditionsNeedsRequirements", "DE4SDV_MiddlewareSCOREConditionsVerificationEvidence");
    attribute :>> expectedReviewEvidence = ("exact-head licensed SysML validation of the increment model slices", "repository gates and the Method Check at the reviewed head", "retained evidence per condition: the capture, the evaluator output and the claim boundary the condition supports");
  }

  view scoreConditionsFramingView {
    viewpoint selectedFramingViewpoint : IncrementFramingViewpoint {
      frame scoreConditionsEvidenceBoundaryConcern;
    }

    expose DE4SDV_MiddlewareSCOREConditionsFraming::*;
    render asTreeDiagram;
  }
}
