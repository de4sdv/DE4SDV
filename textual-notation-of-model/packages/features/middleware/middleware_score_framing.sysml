/*
 * DE4SDV middleware integration framing model slice for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011 frames the realization of the DE4SDV middleware integration
 * layer on Eclipse S-CORE: the EclipseSCORE variant of the SDV platform
 * stack, in a member product with two execution domains under a hypervisor.
 * The Linux host runs Autoware, Eclipse S-CORE and the Autoware-to-S-CORE
 * adapter; an AAOS SDV guest runs the HMI. The reference vehicle speed
 * travels over S-CORE communication into Autoware, and the AEBS signals from
 * Autoware travel over S-CORE communication across the domain boundary to
 * the HMI in the guest. One increment identity spans phases 0 to 10: this
 * framing slice and the needs, requirements, physical/software realization,
 * variability and configuration, and verification-evidence slices that
 * follow all belong to it. The framing records the owner decisions of
 * 2026-10-15 on topology, signals, the Linux host and the waiting items.
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
     * INC-MW-011: middleware integration on Eclipse S-CORE, in a member
     * product with two execution domains under a hypervisor: Autoware,
     * S-CORE and the adapter on a Linux host, and an AAOS SDV guest with the
     * HMI. One increment identity spanning phases 0 to 10, from framing
     * through verification evidence: this framing slice and the needs,
     * requirements, physical/software realization, configuration and
     * verification-evidence slices all belong to this increment.
     */
  }

  requirement scoreMiddlewareProblemStatement : ProblemStatement {
    doc /*
     * How can DE4SDV realize its middleware integration layer on Eclipse
     * S-CORE as the EclipseSCORE variant of the platform stack, in a member
     * product with two execution domains under a hypervisor (Autoware and
     * S-CORE on a Linux host, and an AAOS SDV guest with the HMI), carry the
     * reference vehicle speed through S-CORE communication into Autoware and
     * the AEBS signals from Autoware through S-CORE communication to the HMI
     * in the guest, and show it running, without changing the Autoware
     * application, without copying S-CORE code into DE4SDV, and without
     * safety, cybersecurity or compliance claims?
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
     * integration layer (the six logical components of MiddlewareSystem) on
     * the Linux host of a two-domain member product, so that the reference
     * vehicle speed reaches Autoware and the AEBS signals from Autoware reach
     * the HMI in the AAOS SDV guest through S-CORE communication, with the
     * application decoupled through the adapter, and which middleware
     * capabilities and cross-domain paths stay open?
     */
  }

  part scoreMiddlewareLifecycleDecision : IncrementLifecycleDecision {
    doc /*
     * Decide whether Eclipse S-CORE is a viable realization of the middleware
     * feature for the two-domain member product (Autoware on S-CORE on a
     * Linux host, with an AAOS SDV HMI guest under a hypervisor), and whether
     * that product can become a declared member product, based on the
     * realization coverage and the runnable proof. Eclipse S-CORE is a
     * reference-only alternative in the governed product-line scope
     * (ADR 0014), so declaring the member needs a scope revision that the
     * owner accepts in an architecture decision record.
     */
  }

  part scoreMiddlewareScope : IncrementScope {
    doc /*
     * Scope: the S-CORE realization of the six middleware components on the
     * Linux host (phase 8); the two-domain member product and the
     * per-execution-domain platform modeling it needs (phases 8 and 9);
     * needs and requirements for the S-CORE variant, the reference
     * vehicle-speed path and the cross-domain HMI path (phases 4 and 5); a
     * runnable proof with retained evidence (phase 10); and the one-way HMI
     * path from S-CORE on the Linux host into the AAOS SDV guest.
     */
  }

  part def SCOREMiddlewareIntegrationLayer {
    doc /*
     * The INC-MW-011 system of interest: the middleware integration layer of
     * the two-domain member product, that is, the Autoware-to-S-CORE adapter
     * together with the S-CORE services that realize the six logical
     * components of MiddlewareSystem (signal translation, diagnostic proxy,
     * lifecycle bridge, health proxy, update coordination, service binding)
     * on the Linux host, up to the one-way cross-domain HMI path into the
     * AAOS SDV guest. It is a System 1 element of the member product, not an
     * engineering instrument. The HMI application in the guest is part of
     * the member product but outside the system of interest. The needs and
     * requirements of this increment take the layer as their subject, and
     * its physical/software realization specializes it.
     */
  }

  part scoreMiddlewareIntegrationLayer : SCOREMiddlewareIntegrationLayer {
    doc /*
     * The middleware integration layer as realized on Eclipse S-CORE on the
     * Linux host of the two-domain member product; the charter references it
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
     * Phases 1 to 3 and 6 to 7 are declared because the increment
     * revalidates the middleware baseline of INC-MW-002 to INC-MW-007 for
     * the S-CORE variant and extends it where the two-domain member needs
     * it: the cross-domain HMI path and the per-execution-domain platform.
     * Each later slice belongs to this increment and is not a second
     * increment identity. Owner, expected artifacts and expected review
     * evidence are declarations, not completion or review evidence. The
     * expected artifacts name the framing package only; each later slice
     * adds its own package when it is authored. The system of interest is
     * the middleware integration layer: the needs and requirements take it
     * as their subject, the problem statement keeps the increment.
     */
    attribute :>> applicablePhases = (MethodPhase::phase0_incrementFraming, MethodPhase::phase1_concernFraming, MethodPhase::phase2_operationalContext, MethodPhase::phase3_capabilityClassification, MethodPhase::phase4_needs, MethodPhase::phase5_requirements, MethodPhase::phase6_functionalArchitecture, MethodPhase::phase7_logicalArchitecture, MethodPhase::phase8_physicalRealization, MethodPhase::phase9_variabilityConfiguration, MethodPhase::phase10_vvEvidence);
    ref part :>> increment = DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationIncrement;
    ref part :>> systemOfInterest = DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    attribute :>> owner = "DE4SDV maintainers";
    attribute :>> expectedArtifacts = "DE4SDV_MiddlewareSCOREFraming";
    attribute :>> expectedReviewEvidence = ("exact-head licensed SysML validation of the increment model slices", "repository gates and the Method Check at the reviewed head", "retained evidence of the runnable proof: the reference vehicle speed over S-CORE into Autoware and the AEBS signals over S-CORE to the HMI in the AAOS SDV guest");
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
     * The two-domain member product whose middleware integration layer is
     * the system of interest: Autoware, Eclipse S-CORE and the adapter on a
     * Linux host, and an AAOS SDV guest with the HMI, under a hypervisor.
     * Its configuration cannot be expressed in the current product model
     * (GAP-MW-032); the example bill of features "Autoware on S-CORE on
     * Linux" describes only the Linux domain.
     */
  }
  part system2RunnableProofBench : System2EngineeringAndAssuranceSystem {
    doc /*
     * The bounded bench that runs the member product's runnable proof and
     * retains its evidence. It observes the signal path and the HMI
     * read-only; the HMI is a product element, not a bench instrument.
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
    doc /* The S-CORE realization of the six middleware components on the Linux host (phase 8). */
  }
  part scoreMemberProductInScope : InScopeItem {
    doc /* The two-domain member product: Autoware, S-CORE and the adapter on a Linux host, and an AAOS SDV guest with the HMI, under a hypervisor (phases 8 and 9). */
  }
  part referenceVehicleSpeedPathInScope : InScopeItem {
    doc /* The reference vehicle-speed path (VSS Vehicle.Speed) over S-CORE communication into Autoware, like for like with the AAOS SDV realization of INC-MW-008 over the same reference signal. */
  }
  part perExecutionDomainPlatformModelingInScope : InScopeItem {
    doc /* Per-execution-domain platform modeling (operating system, middleware and hypervisor per domain), so that the product model can express the two-domain member (phases 8 and 9). */
  }
  part scoreVariantNeedsRequirementsInScope : InScopeItem {
    doc /* Needs and requirements for the S-CORE variant, the reference vehicle-speed path and the cross-domain HMI path (phases 4 and 5). */
  }
  part runnableProofInScope : InScopeItem {
    doc /* A runnable proof with retained evidence (phase 10). */
  }
  part hmiPathInScope : InScopeItem {
    doc /* The one-way cross-domain HMI path from S-CORE on the Linux host into the AAOS SDV guest, as a product interface of the member product. */
  }

  part complianceClaimOutOfScope : OutOfScopeItem {
    doc /*
     * ISO 26262, ISO 21434, UN R152, UN R155 and UN R156 conformance or
     * compliance claims. The safety and security process of the S-CORE
     * project is not a DE4SDV safety or security claim, and the HMI in the
     * AAOS SDV guest is not claimed as the AEBS driver warning.
     */
  }
  part qnxAndHardwareTargetsOutOfScope : OutOfScopeItem {
    doc /* QNX and hardware targets; the proof runs on Linux x86_64. */
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
     * ASM-MW-024: The HMI application of the member product is the AAOS SDV
     * visualization application of INC-AEBS-010, reused unchanged in the
     * AAOS SDV guest under its visualization contract. It consumes the
     * signal path read-only and feeds nothing back into the application or
     * the middleware. It is an informational display, not the AEBS driver
     * warning.
     */
  }
  part asmBoundedBenchDemonstration : IncrementAssumption {
    doc /*
     * ASM-MW-025: The runnable proof is a bounded bench demonstration, not a
     * product, fleet or on-road claim.
     */
  }
  part asmLinuxHostUbuntuThenAutoSD : IncrementAssumption {
    doc /*
     * ASM-MW-026: The Linux host of the first runnable proof is Ubuntu
     * x86_64, where the linux-x86_64 configuration of S-CORE v0.9.0 and
     * Autoware are both supported. Red Hat AutoSD is the target automotive
     * Linux, proven in a second step: S-CORE builds and tests autosd-x86_64
     * upstream, and Autoware would run in an Ubuntu container on it.
     */
  }
  part asmKVMHypervisorWithAAOSSDVGuest : IncrementAssumption {
    doc /*
     * ASM-MW-027: The hypervisor is KVM on the Linux host, with the AAOS SDV
     * guest, as in the AAOS-integrated reference member (middleware
     * androidSDV, hypervisor kvm, osPlatform android); the INC-AEBS-010
     * bench ran its HMI in an AAOS SDV Cuttlefish guest.
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
     * the Linux host across the domain boundary, through the hypervisor,
     * into the AAOS SDV guest is not selected in this framing slice; the
     * realization slice selects and pins it.
     */
  }
  part gapTwoDomainMemberNotExpressible : IncrementGap {
    doc /*
     * GAP-MW-032: The product model cannot express a member product with two
     * execution domains. The feature model selects exactly one operating
     * system, one middleware alternative and one hypervisor per product
     * (the alternative groups F-PLATFORM-OS, F-PLATFORM-MIDDLEWARE and
     * F-PLATFORM-HYPERVISOR), and constraint C001 requires PlatformStack.OS
     * in [Linux, QNX] when PlatformStack.Middleware is EclipseSCORE; the
     * platform stack mirrors this with one osPlatform, one middleware and
     * one hypervisor variation per stack. The two-domain member needs Linux
     * with S-CORE on the host and Android with the AAOS SDV middleware in
     * the guest. The same limit affects the AAOS-integrated reference member
     * (PLE-S finding D6): its Autoware runs on a Linux ROS 2 runtime while
     * its single operating-system selection says Android. Phases 8 and 9 of
     * this increment close the gap with per-execution-domain platform
     * modeling.
     */
  }

  /* Qualified references to the reused targets of the two-domain framing
   * (no restatement of their content). */
  dependency linuxHostAssumptionOnLinuxVariant
    from asmLinuxHostUbuntuThenAutoSD to DE4SDV_SDVPlatformStack::LinuxPlatform;
  dependency hypervisorAssumptionOnKVMVariant
    from asmKVMHypervisorWithAAOSSDVGuest to DE4SDV_SDVPlatformStack::KVMHypervisor;
  dependency guestTopologyAsInAAOSIntegratedConfiguredMember
    from asmKVMHypervisorWithAAOSSDVGuest to DE4SDV_MiddlewareVariabilityConfiguration::MiddlewareAutowareAAOSSDVConfiguredMember;
  dependency hmiApplicationReusesVisualizationApplication
    from asmVisualizationInstrumentReused to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::JavaCenterDisplayApplication;
  dependency speedPathUsesReferenceVehicleSpeedSource
    from referenceVehicleSpeedPathInScope to DE4SDV_MiddlewarePhysicalSoftwareRealization::COVESAVehicleSpeedSemanticSource;
  dependency speedPathLikeForLikeWithAAOSSDVRealization
    from referenceVehicleSpeedPathInScope to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftware;
  dependency twoDomainGapOnSinglePlatformStackSelections
    from gapTwoDomainMemberNotExpressible to DE4SDV_SDVPlatformStack::SDVPlatformStack;
  dependency twoDomainGapAffectsAAOSIntegratedMember
    from gapTwoDomainMemberNotExpressible to DE4SDV_AEBSProductLineScope::InitialPlannedReferenceMemberPortfolio::aaosIntegratedAutowareAEBSReferenceMember;

  concern scoreRealizationCoverageConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * Reviewers need to see which of the six middleware components Eclipse
     * S-CORE realizes for the EclipseSCORE variant and which stay open, so
     * that the S-CORE variant of the middleware feature is classified from
     * its realization coverage, not from the variant name, and compared like
     * for like with the AAOS SDV realization of INC-MW-008 over the same
     * reference vehicle-speed signal.
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
     * Reviewers need the HMI path to be one-way and read-only across the
     * domain and hypervisor boundary: the AEBS signals flow from S-CORE on
     * the Linux host into the AAOS SDV guest, and nothing flows back into
     * the Autoware application or the middleware.
     */
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder verificationEngineer : VerificationEngineer;
  }

  concern noComplianceClaimConcern : RegulatoryScopeWithoutComplianceClaimConcern {
    doc /*
     * Reviewers need the safety, cybersecurity and regulatory anchors around
     * S-CORE and the AEBS HMI (ISO 26262, ISO 21434, UN R152, UN R155,
     * UN R156) to stay visible as scope boundaries without any DE4SDV
     * conformance, compliance, certification or type-approval claim.
     */
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder maintainer : Maintainer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern twoDomainMemberRepresentationConcern : ProductLineConfigurationConcern {
    doc /*
     * Reviewers need the two-domain member product, with its own operating
     * system, middleware and hypervisor selection per execution domain, to
     * be representable in the product model's variation structure without
     * changing the configurations of the existing members.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreMiddlewareFramingView {
    viewpoint selectedFramingViewpoint : IncrementFramingViewpoint {
      frame scoreRealizationCoverageConcern;
      frame applicationDecouplingConcern;
      frame hmiDomainBoundaryConcern;
      frame noComplianceClaimConcern;
      frame twoDomainMemberRepresentationConcern;
    }

    expose DE4SDV_MiddlewareSCOREFraming::*;
    render asTreeDiagram;
  }
}
