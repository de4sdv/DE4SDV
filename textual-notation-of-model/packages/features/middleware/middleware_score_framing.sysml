/*
 * DE4SDV middleware integration framing model slice for the Eclipse S-CORE
 * realization.
 *
 * INC-MW-011 frames the realization of the DE4SDV middleware integration
 * layer on Eclipse S-CORE: the EclipseSCORE variant of the SDV platform
 * stack, in a member product with two execution domains under a hypervisor.
 * The Linux host runs Autoware, Eclipse S-CORE and the Autoware-to-S-CORE
 * adapter; an AAOS SDV guest runs the HMI. The reference vehicle speed
 * travels over S-CORE communication into Autoware. The AEBS signals of the
 * Autoware-based AEBS stack on the Linux host travel over S-CORE
 * communication inside the host, and the S-CORE SOME/IP gateway carries them
 * across the domain boundary to the HMI in the guest. One increment identity
 * spans phases 0 to 12: this framing slice, the needs, requirements,
 * physical/software realization, variability and configuration, and
 * verification-evidence slices that follow, and the publication and baseline
 * decision all belong to it.
 *
 * Predecessor relationship: the increment builds on the closed INC-MW-010
 * baseline and on the INC-MW-002 to INC-MW-007 baseline (ASM-MW-023). It
 * does not reopen, extend, or retroactively satisfy the closed baseline,
 * copies no S-CORE code into DE4SDV, and makes no safety, cybersecurity or
 * compliance claim.
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
     * HMI. One increment identity spanning phases 0 to 12, from framing
     * through verification evidence, publication and the baseline decision:
     * this framing slice and the needs, requirements, physical/software
     * realization, configuration and verification-evidence slices all
     * belong to this increment.
     */
  }

  requirement scoreMiddlewareProblemStatement : ProblemStatement {
    doc /*
     * DE4SDV's middleware integration layer is realized only on AAOS SDV
     * (INC-MW-008). The product line names Eclipse S-CORE as a middleware
     * alternative, but there is no evidence that S-CORE can realize the
     * layer (GAP-MW-030), no planned member product uses it, and the product
     * model cannot describe the product it would need: Autoware and S-CORE
     * on a Linux host, with an AAOS SDV guest for the HMI (GAP-MW-032).
     * Until that changes, S-CORE stays a reference-only alternative of the
     * governed product-line scope (ADR 0014), and product-line engineers,
     * architects and reviewers cannot judge it as an open-source automotive
     * middleware option.
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
     * vehicle speed reaches Autoware and the AEBS signals of the
     * Autoware-based AEBS stack on the Linux host reach the HMI in the AAOS
     * SDV guest through S-CORE communication, with the application
     * decoupled through the adapter, and which middleware capabilities and
     * cross-domain paths stay open?
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
    doc /* The scope of INC-MW-011: the engineering question, GAP-MW-030, GAP-MW-032 and the charter set its realization, member-product and platform scope; the nested parts are the two signal paths later slices trace to; the OutOfScopeItem parts of this package bound it. */
    part referenceVehicleSpeedPathInScope : InScopeItem {
      doc /* The reference vehicle-speed path (VSS Vehicle.Speed) over S-CORE communication into the same Autoware consumer, like for like with the AAOS SDV realization of INC-MW-008 over the same reference signal, with evidence comparable with the retained evidence of INC-MW-010. */
    }
    part hmiPathInScope : InScopeItem {
      doc /*
       * The one-way cross-domain HMI path from S-CORE on the Linux host into
       * the AAOS SDV guest, as a product interface of the member product. It
       * carries the AEBS signals of the Autoware-based AEBS stack with the
       * per-field provenance INC-AEBS-010 assigns: the native Autoware AEB
       * outputs (RSS, the filtered obstacle cloud and the intervention
       * diagnostic) and the DE4SDV coordinator's warning request, braking
       * request and intervention lifecycle state (MONITORING, WARNING,
       * INTERVENTION, RELEASED); coordinator output is never relabeled as
       * native Autoware output.
       */
    }
  }

  part def SCOREMiddlewareIntegrationLayer {
    doc /*
     * The INC-MW-011 system of interest: the middleware integration layer of
     * the two-domain member product, that is, the Autoware-to-S-CORE adapter
     * together with the S-CORE services that realize the six logical
     * components of MiddlewareSystem (signal translation, diagnostic proxy,
     * lifecycle bridge, health proxy, update coordination, service binding)
     * on the Linux host, and the one-way cross-domain HMI path into the AAOS
     * SDV guest up to the HMI application. It is part of the member product,
     * not an engineering instrument. The HMI application in the guest is part
     * of the member product but outside the system of interest. The needs and
     * requirements of this increment take the layer as their subject, and its
     * physical/software realization specializes it.
     */
  }

  part scoreMiddlewareIntegrationLayer : SCOREMiddlewareIntegrationLayer {
    doc /*
     * The middleware integration layer as realized on Eclipse S-CORE on the
     * Linux host of the two-domain member product, up to the HMI application
     * in the AAOS SDV guest; the charter references it as the system of
     * interest.
     */
  }

  part scoreMiddlewareCharter : IncrementCharter {
    doc /*
     * Charter declaration of the increment; traces are the native
     * relationships of this package. The applicable phases cover framing,
     * concern framing, operational context, capability classification, needs,
     * requirements, functional and logical architecture, physical/software
     * realization, variability and configuration, verification evidence,
     * publication, and the baseline and next-slice decision. Phases 1 to 3
     * and 6 to 7 are declared because the increment revalidates the
     * middleware baseline of INC-MW-002 to INC-MW-007 for the S-CORE variant
     * and extends it where the two-domain member needs it: the cross-domain
     * HMI path and the per-execution-domain platform. Phases 11 and 12 are
     * declared because the lifecycle decision and the scope-revision
     * decision record that admits the member are phase 12 work.
     * Each later slice belongs to this increment and is not a second
     * increment identity. Owner, expected artifacts and expected review
     * evidence are declarations, not completion or review evidence. The
     * expected artifacts name the packages of phases 0 to 8; each later slice
     * adds its own package when it is authored. The system of interest is
     * the middleware integration layer: the needs and requirements take it
     * as their subject, the problem statement keeps the increment.
     */
    attribute :>> applicablePhases = (MethodPhase::phase0_incrementFraming, MethodPhase::phase1_concernFraming, MethodPhase::phase2_operationalContext, MethodPhase::phase3_capabilityClassification, MethodPhase::phase4_needs, MethodPhase::phase5_requirements, MethodPhase::phase6_functionalArchitecture, MethodPhase::phase7_logicalArchitecture, MethodPhase::phase8_physicalRealization, MethodPhase::phase9_variabilityConfiguration, MethodPhase::phase10_vvEvidence, MethodPhase::phase11_publication, MethodPhase::phase12_baselineNextSlice);
    ref part :>> increment = DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationIncrement;
    ref part :>> systemOfInterest = DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationLayer;
    attribute :>> owner = "DE4SDV maintainers";
    attribute :>> expectedArtifacts = ("DE4SDV_MiddlewareSCOREFraming", "DE4SDV_MiddlewareSCOREOperationalContext", "DE4SDV_MiddlewareSCOREFeatureClassification", "DE4SDV_MiddlewareSCORENeedsRequirements", "DE4SDV_MiddlewareSCOREFunctionalArchitecture", "DE4SDV_MiddlewareSCORELogicalArchitecture", "DE4SDV_MiddlewareSCOREPhysicalSoftwareRealization");
    attribute :>> expectedReviewEvidence = ("exact-head licensed SysML validation of the increment model slices", "repository gates and the Method Check at the reviewed head", "retained evidence of the runnable proof: the reference vehicle speed over S-CORE into Autoware and the AEBS signals over S-CORE inside the Linux host and over the S-CORE SOME/IP gateway to the HMI in the AAOS SDV guest");
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
  part scoreSourceVendoringOutOfScope : OutOfScopeItem {
    doc /* Copying (vendoring) S-CORE code into DE4SDV. */
  }
  part otherStackVariantsOutOfScope : OutOfScopeItem {
    doc /* The Apollo, Openpilot and AUTOSAR Adaptive variants of the platform stack. */
  }
  part closedMiddlewareBaselineOutOfScope : OutOfScopeItem {
    doc /* Reopening the closed INC-MW-010 baseline or extending its retained evidence. */
  }
  part scoreUpstreamEngagementOutOfScope : OutOfScopeItem {
    doc /*
     * Engagement with the Eclipse S-CORE project beyond defect reports, and
     * endorsement by it; the increment claims neither. With the owner's
     * approval, DE4SDV reported the gateway integration defects upstream on
     * 2026-10-22 (GAP-MW-036). Code contributions, and a cross-domain
     * integration test for the gateway, stay a later decision of the owner.
     */
  }

  part asmSCOREBaselinePinned : IncrementAssumption {
    doc /*
     * ASM-MW-021: Eclipse S-CORE v0.9.0 is the pinned baseline:
     * eclipse-score/reference_integration tag v0.9.0, commit
     * 71b00dda29e73433064f0b2536e916099ffe75a9. It is a pre-1.0 release, and
     * the project states that it is not a ready-to-integrate series product.
     * Every S-CORE statement of this increment is bound to that commit, with
     * one bounded deviation (owner decision of 2026-10-22). The middleware
     * integration layer carries the AEBS signal frames over the S-CORE
     * SOME/IP gateway, which is not in that baseline:
     * eclipse-score/inc_someip_gateway at commit
     * 951fbc09bfbe9011eb81471cd31e1379700669b8, with no tag. The gateway
     * needs communication 0.5.0 and baselibs 0.2.15, each with a patch of the
     * gateway, in place of the communication 0.4.0 and baselibs 0.2.12 of
     * v0.9.0. No S-CORE baseline holds that set. The deviation covers these
     * two modules, for every mw::com user on the Linux host, and the gateway
     * with its patched vsomeip 3.6.1. Statements about them are bound to the
     * versions and the commit named here. Everything else stays bound to
     * v0.9.0, among it lifecycle v0.6.1 and the assumptions of use of
     * eclipse-score/score v0.7.2 that NEED-MW-004 cites. GAP-MW-036 records
     * the deviation and the trigger to revisit it.
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
     * ASM-MW-023: The concerns, operational context and story, capability
     * classification, needs, requirements, and functional and logical
     * architecture of INC-MW-002 to INC-MW-007 hold for the S-CORE variant
     * unless phases 1 to 7 of this increment show otherwise.
     */
  }
  part asmVisualizationApplicationReusedAsHMI : IncrementAssumption {
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
     * product, fleet or on-road claim. The bench observes the signal path and
     * the HMI read-only and retains the evidence.
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
     * bench ran its HMI in an AAOS SDV Cuttlefish guest. The Linux host is
     * both the KVM host and the domain that owns the AEBS emergency
     * intervention command path (ASM-MW-028), so the hypervisor boundary
     * isolates the informational HMI guest from the host.
     */
  }
  part asmEmergencyCommandPathStaysOnLinuxHost : IncrementAssumption {
    doc /*
     * ASM-MW-028: The AEBS emergency intervention command path stays inside
     * the Linux host, within the Autoware-based AEBS stack: it is not carried
     * over S-CORE communication and does not cross the hypervisor boundary
     * to the AAOS SDV guest. This keeps the middleware baseline (ASM-MW-003:
     * the brake command path remains direct from the AEB node to the vehicle
     * command gate, not through the adapter). With KVM (ASM-MW-027) the
     * Linux host is both the hypervisor host and the owner of that path, so
     * the hypervisor boundary isolates the HMI guest from the host. No
     * freedom-from-interference claim is made; REQ-MW-006
     * (reqIsolateSafetyPath, in development) and GAP-MW-029 stay open.
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
     * the guest; the example feature configuration "Autoware on S-CORE on
     * Linux" describes only the Linux domain. The same limit affects the
     * AAOS-integrated reference member: its Autoware runs on a Linux ROS 2
     * runtime while its single operating-system selection says Android.
     * Phases 8 and 9 of this increment close the gap with
     * per-execution-domain platform modeling.
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
    from asmVisualizationApplicationReusedAsHMI to DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::JavaCenterDisplayApplication;
  dependency speedPathUsesReferenceVehicleSpeedSource
    from scoreMiddlewareScope::referenceVehicleSpeedPathInScope to DE4SDV_MiddlewarePhysicalSoftwareRealization::COVESAVehicleSpeedSemanticSource;
  dependency speedPathLikeForLikeWithAAOSSDVRealization
    from scoreMiddlewareScope::referenceVehicleSpeedPathInScope to DE4SDV_MiddlewarePhysicalSoftwareRealization::physicalSoftware;
  dependency twoDomainGapOnSinglePlatformStackSelections
    from gapTwoDomainMemberNotExpressible to DE4SDV_SDVPlatformStack::SDVPlatformStack;
  dependency twoDomainGapAffectsAAOSIntegratedMember
    from gapTwoDomainMemberNotExpressible to DE4SDV_AEBSProductLineScope::InitialPlannedReferenceMemberPortfolio::aaosIntegratedAutowareAEBSReferenceMember;
  dependency emergencyPathAssumptionOnProtectedPathIndependence
    from asmEmergencyCommandPathStaysOnLinuxHost to DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::protectedEmergencyCommandPathIndependence;

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
      frame hmiDomainBoundaryConcern;
      frame twoDomainMemberRepresentationConcern;
    }

    expose DE4SDV_MiddlewareSCOREFraming::*;
    render asTreeDiagram;
  }
}
