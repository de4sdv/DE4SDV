/*
 * DE4SDV middleware integration framing model slice for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011 frames the realization of the DE4SDV middleware integration
 * layer on Eclipse S-CORE: the EclipseSCORE variant of the SDV platform
 * stack, as selected by the example configuration "Autoware on S-CORE on
 * Linux". One increment identity spans phases 0 to 10: this framing slice
 * and the needs, requirements, physical/software realization, variability
 * and configuration, and verification-evidence slices that follow all belong
 * to it.
 *
 * Predecessor relationship: the increment builds on the closed INC-MW-010
 * baseline and on the needs, requirements and logical architecture of
 * INC-MW-004 to INC-MW-007. It does not reopen, extend, or retroactively
 * satisfy that baseline, copies no S-CORE code into DE4SDV, and makes no
 * safety, cybersecurity or compliance claim.
 */

package DE4SDV_MiddlewareSCOREFraming {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_IncrementWorkflow::IncrementCharter;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_MethodViewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  part def SCOREMiddlewareIntegrationIncrement :> EngineeringIncrement;

  part <'INC-MW-011'> scoreMiddlewareIntegrationIncrement : SCOREMiddlewareIntegrationIncrement {
    doc /*
     * INC-MW-011: middleware integration on Eclipse S-CORE. One increment
     * identity spanning phases 0 to 10, from framing through verification
     * evidence: this framing slice and the needs, requirements,
     * physical/software realization, configuration and verification-evidence
     * slices all belong to this increment.
     */
  }

  requirement scoreMiddlewareProblemStatement : ProblemStatement {
    doc /*
     * How can DE4SDV realize its middleware integration layer on Eclipse
     * S-CORE as the EclipseSCORE variant of the platform stack, carry the
     * AEBS signals from Autoware on Linux through S-CORE communication to an
     * HMI in an AAOS SDV guest, and show it running, without changing the
     * Autoware application, without copying S-CORE code into DE4SDV, and
     * without safety, cybersecurity or compliance claims?
     */
    subject increment : SCOREMiddlewareIntegrationIncrement;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  part scoreMiddlewareEngineeringQuestion : IncrementEngineeringQuestion {
    doc /*
     * Can Eclipse S-CORE, pinned at v0.9.0, realize DE4SDV's middleware
     * integration layer (the six logical components of MiddlewareSystem) so
     * that AEBS signals from Autoware on Linux reach an AAOS SDV HMI through
     * S-CORE communication, with the application decoupled through the
     * adapter, and which middleware capabilities stay open?
     */
  }

  part scoreMiddlewareLifecycleDecision : IncrementLifecycleDecision {
    doc /*
     * Decide whether Eclipse S-CORE is a viable realization of the middleware
     * feature for the "Autoware on S-CORE on Linux" member product, that is,
     * whether that example configuration can become a declared member
     * product, based on the realization coverage and the runnable proof.
     */
  }

  part scoreMiddlewareScope : IncrementScope {
    doc /*
     * Scope: the S-CORE realization of the six middleware components
     * (phase 8); the member product "Autoware on S-CORE on Linux" (phase 9);
     * needs and requirements for the S-CORE variant and the HMI path
     * (phases 4 and 5); a runnable proof with retained evidence (phase 10);
     * and the HMI path from S-CORE on Linux to the AAOS SDV guest.
     */
  }

  part def SCOREMiddlewareIntegrationLayer {
    doc /*
     * The INC-MW-011 system of interest: the middleware integration layer of
     * the "Autoware on S-CORE on Linux" member product. It is the
     * Autoware-to-S-CORE adapter together with the S-CORE services that
     * realize the six logical components of MiddlewareSystem (signal
     * translation, diagnostic proxy, lifecycle bridge, health proxy, update
     * coordination, service binding), up to the one-way HMI path into the
     * AAOS SDV guest. It is a System 1 element of the member product, not an
     * engineering instrument. The needs and requirements of this increment
     * take it as their subject, and its physical/software realization
     * specializes it.
     */
  }

  part scoreMiddlewareIntegrationLayer : SCOREMiddlewareIntegrationLayer {
    doc /*
     * The middleware integration layer as realized on Eclipse S-CORE for the
     * "Autoware on S-CORE on Linux" member product; the charter references it
     * as the system of interest.
     */
  }

  connection scoreMiddlewareStakeholderParticipation : HasStakeholder
    connect scoreMiddlewareIntegrationIncrement to scoreMiddlewareProblemStatement.systemArchitect;

  part scoreMiddlewareCharter : IncrementCharter {
    doc /*
     * Charter declaration of the increment; traces are the native
     * relationships of this package. The applicable phases cover framing,
     * concern framing, operational context, capability classification, needs,
     * requirements, functional and logical architecture, physical/software
     * realization, variability and configuration, and verification evidence.
     * Phases 1 to 3 and 6 to 7 are declared because the increment reuses and
     * revalidates the middleware baseline of INC-MW-002 to INC-MW-007 for the
     * S-CORE variant; each later slice belongs to this increment and is not a
     * second increment identity. Owner, expected artifacts and expected review
     * evidence are declarations, not completion or review evidence. The
     * expected artifacts name the framing package only; each later slice adds
     * its own package when it is authored. The system of interest is the
     * middleware integration layer: the needs and requirements take it as
     * their subject, the problem statement keeps the increment.
     */
    attribute :>> applicablePhases = (MethodPhase::phase0_incrementFraming, MethodPhase::phase1_concernFraming, MethodPhase::phase2_operationalContext, MethodPhase::phase3_capabilityClassification, MethodPhase::phase4_needs, MethodPhase::phase5_requirements, MethodPhase::phase6_functionalArchitecture, MethodPhase::phase7_logicalArchitecture, MethodPhase::phase8_physicalRealization, MethodPhase::phase9_variabilityConfiguration, MethodPhase::phase10_vvEvidence);
    ref part :>> increment = DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationIncrement;
    ref part :>> systemOfInterest = DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    attribute :>> owner = "DE4SDV maintainers";
    attribute :>> expectedArtifacts = "DE4SDV_MiddlewareSCOREFraming";
    attribute :>> expectedReviewEvidence = ("exact-head licensed SysML validation of the increment model slices", "repository gates and the Method Check at the reviewed head", "retained evidence of the runnable proof: the AEBS signal path over S-CORE to the AAOS SDV HMI");
  }

  /* Qualified references to the accepted baseline and to the platform-stack
   * variants the increment realizes (no restatement of their content). */
  dependency scoreIncrementToClosedMiddlewareBaseline
    from scoreMiddlewareIntegrationIncrement to DE4SDV_MiddlewareVerificationEvidence::boundedBaselineDecision010;
  dependency scoreLayerRealizesLogicalMiddlewareSystem
    from scoreMiddlewareIntegrationLayer to DE4SDV_MiddlewareLogicalArchitecture::system;
  dependency scoreLayerOnEclipseSCOREVariant
    from scoreMiddlewareIntegrationLayer to DE4SDV_SDVPlatformStack::EclipseSCORE;
  dependency scoreLayerOnAutowareToSCOREAdapter
    from scoreMiddlewareIntegrationLayer to DE4SDV_SDVPlatformStack::AutowareToSCOREAdapter;

  dependency scoreQuestionToProblemStatement
    from scoreMiddlewareEngineeringQuestion to scoreMiddlewareProblemStatement;
  dependency scoreScopeToCharter
    from scoreMiddlewareScope to scoreMiddlewareCharter;

  part system1SCOREMemberProduct : System1SDVProductLine {
    doc /*
     * The "Autoware on S-CORE on Linux" member product whose middleware
     * integration layer is the system of interest; its example configuration
     * is the Autoware, EclipseSCORE, Linux, no-hypervisor bill of features.
     */
  }
  part system2RunnableProofBench : System2EngineeringAndAssuranceSystem {
    doc /*
     * The bounded bench that runs the proof and retains its evidence; it
     * reuses the AAOS SDV visualization instrument of INC-AEBS-010 as the
     * read-only HMI observer.
     */
  }
  part system3UpstreamReviewEcosystem : System3OpenSourceGovernanceEcosystem {
    doc /*
     * DE4SDV reviewers and the Eclipse S-CORE upstream project. No upstream
     * engagement or endorsement is claimed by this increment.
     */
  }

  part scoreMiddlewareScopeBoundary : OperationalScopeBoundary;
  part scoreRealizationInScope : InScopeItem {
    doc /* The S-CORE realization of the six middleware components (phase 8). */
  }
  part scoreMemberProductInScope : InScopeItem {
    doc /* The member product "Autoware on S-CORE on Linux" (phase 9). */
  }
  part scoreVariantNeedsRequirementsInScope : InScopeItem {
    doc /* Needs and requirements for the S-CORE variant and the HMI path (phases 4 and 5). */
  }
  part runnableProofInScope : InScopeItem {
    doc /* A runnable proof with retained evidence (phase 10). */
  }
  part hmiPathInScope : InScopeItem {
    doc /* The HMI path from S-CORE on Linux to the AAOS SDV guest. */
  }

  part complianceClaimOutOfScope : OutOfScopeItem {
    doc /*
     * ISO 26262, ISO 21434, UN R155 and UN R156 conformance or compliance
     * claims. The safety and security process of the S-CORE project is not a
     * DE4SDV safety or security claim.
     */
  }
  part qnxAndHardwareTargetsOutOfScope : OutOfScopeItem {
    doc /* QNX and hardware targets; the proof runs on Linux. */
  }
  part productionDeploymentOutOfScope : OutOfScopeItem {
    doc /* Production deployment of any kind. */
  }
  part scoreSourceVendoringOutOfScope : OutOfScopeItem {
    doc /* Copying (vendoring) S-CORE code into DE4SDV. */
  }
  part otherStackVariantsOutOfScope : OutOfScopeItem {
    doc /* The Apollo, Openpilot and AUTOSAR Adaptive variants of the platform stack. */
  }
  part closedMiddlewareBaselineOutOfScope : OutOfScopeItem {
    doc /* Reopening the closed INC-MW-010 baseline or extending its retained evidence. */
  }

  part asmSCOREBaselinePinned : IncrementAssumption {
    doc /*
     * ASM-MW-021: Eclipse S-CORE v0.9.0 is the pinned baseline. It is a
     * pre-1.0 release, and the project states that it is not a
     * ready-to-integrate series product; every S-CORE statement of this
     * increment is bound to that version.
     */
  }
  part asmAutowareApplicationUnchanged : IncrementAssumption {
    doc /*
     * ASM-MW-022: The Autoware application is unchanged; only the adapter
     * binds to S-CORE. The adapter is a common capability of the product
     * line, not a feature.
     */
  }
  part asmMiddlewareBaselineHolds : IncrementAssumption {
    doc /*
     * ASM-MW-023: The needs, requirements and logical architecture of
     * INC-MW-004 to INC-MW-007 hold for the S-CORE variant unless phases 4
     * to 7 of this increment show otherwise.
     */
  }
  part asmVisualizationInstrumentReused : IncrementAssumption {
    doc /*
     * ASM-MW-024: The AAOS SDV visualization instrument of INC-AEBS-010 is
     * reused as the HMI; it observes the signal path read-only and feeds
     * nothing back into the application or the middleware.
     */
  }
  part asmBoundedBenchDemonstration : IncrementAssumption {
    doc /*
     * ASM-MW-025: The runnable proof is a bounded bench demonstration, not a
     * product, fleet or on-road claim.
     */
  }

  part gapRealizationCoverageUnknown : IncrementGap {
    doc /*
     * GAP-MW-030: Which of the six middleware components S-CORE v0.9.0
     * realizes, and which stay open, is unknown until the physical/software
     * realization slice of this increment records the coverage.
     */
  }
  part gapHMITransportUnselected : IncrementGap {
    doc /*
     * GAP-MW-031: The transport that carries the AEBS signals from S-CORE on
     * Linux into the AAOS SDV guest is not selected in this framing slice;
     * the realization slice selects and pins it.
     */
  }

  concern scoreRealizationCoverageConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * Reviewers need to see which of the six middleware components Eclipse
     * S-CORE realizes for the EclipseSCORE variant and which stay open, so
     * that the S-CORE variant of the middleware feature is classified from
     * its realization coverage, not from the variant name.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern applicationDecouplingConcern : IncrementBoundaryConcern {
    doc /*
     * Reviewers need the Autoware application to stay unchanged, with only the
     * adapter binding to S-CORE, and the realization, configuration and
     * evidence slices of this increment to stay separate from this framing.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern hmiDomainBoundaryConcern : FunctionalInterfaceConcern {
    doc /*
     * Reviewers need the HMI domain boundary to be one-way and read-only: the
     * AEBS signals flow from S-CORE on Linux into the AAOS SDV guest, and
     * nothing flows back into the Autoware application or the middleware.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  concern noComplianceClaimConcern : RegulatoryScopeWithoutComplianceClaimConcern {
    doc /*
     * Reviewers need the safety, cybersecurity and regulatory anchors around
     * S-CORE (ISO 26262, ISO 21434, UN R155, UN R156) to stay visible as scope
     * boundaries without any DE4SDV conformance, compliance, certification or
     * type-approval claim.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareFramingView {
    viewpoint selectedFramingViewpoint : IncrementFramingViewpoint {
      frame scoreRealizationCoverageConcern;
      frame applicationDecouplingConcern;
      frame hmiDomainBoundaryConcern;
      frame noComplianceClaimConcern;
    }

    expose DE4SDV_MiddlewareSCOREFraming::*;
    render asTreeDiagram;
  }
}
