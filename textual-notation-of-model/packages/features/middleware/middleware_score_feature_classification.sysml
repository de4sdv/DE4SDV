/*
 * DE4SDV middleware feature/common-capability classification model slice for
 * the Eclipse S-CORE realization.
 *
 * INC-MW-011, phase 3: each characteristic of the two-domain member product
 * is classified as a feature, a common capability, a variability-structure
 * change, a constraint or an evidence capability, with its reason, before
 * phase 4 derives needs. The middleware baseline classification of INC-MW-003
 * (DE4SDV_MiddlewareFeatureClassification) holds for the S-CORE variant and
 * is referenced, not duplicated: the middleware and application selections
 * stay native variation/variant in DE4SDV_SDVPlatformStack, and the baseline
 * common capabilities stay common. Phase 9 declares no member configuration;
 * it waits for the PLEML adoption decision. No safety, cybersecurity,
 * compliance or upstream-engagement claim is made.
 */

package DE4SDV_MiddlewareSCOREFeatureClassification {
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodViewpoints::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;

  part def MemberConstraintCharacteristic :> ProductLineCharacteristic {
    doc /*
     * A characteristic that constrains every member using the element it
     * belongs to; neither a feature nor a capability. Slice-local
     * specialization of the product-line classification base for the
     * method's "constraint" outcome; a candidate for the kernel.
     */
  }

  part def EvidenceCapabilityCharacteristic :> ProductLineCharacteristic {
    doc /*
     * An engineering and assurance capability of the bench and its retained
     * evidence, not a characteristic of the member product. Slice-local
     * specialization of the product-line classification base for the
     * method's "evidence capability" outcome; a candidate for the kernel.
     */
  }

  part eclipseSCOREMiddlewareVariant : DeferredVariantChoice {
    doc /*
     * CLS-MW-001, feature: the EclipseSCORE middleware variant is a native
     * variant of the middleware variation in DE4SDV_SDVPlatformStack and
     * distinguishes member products, as the baseline classification of
     * INC-MW-003 already records. It is reference-only in the governed
     * product-line scope (ADR 0014) until a scope revision admits the member;
     * selecting it is phase 9 work after the PLEML adoption decision. This
     * record points at the existing variation and declares no configuration.
     */
  }

  part autowareToSCOREAdapter : CommonProductLineCapability {
    doc /*
     * CLS-MW-002, common capability: the Autoware-to-S-CORE adapter is the
     * adapter layer the baseline classifies as common for every
     * (application, middleware) pair; it follows from the pair and does not
     * distinguish members (ASM-MW-022). The Autoware application stays
     * unchanged; only the adapter binds to S-CORE.
     */
  }

  part perExecutionDomainPlatformVariability : DeferredProductLineScope {
    doc /*
     * CLS-MW-003, variability-structure change: one operating system, one
     * middleware and one hypervisor selection per execution domain, so that
     * the product model can express the two-domain member (GAP-MW-032).
     * Neither a feature nor a capability of the member; a change to the
     * variation structure that phases 8 and 9 make, without changing the
     * existing members' configurations.
     */
  }

  part aaosSDVHMIGuest : DeferredVariantChoice {
    doc /*
     * CLS-MW-004, feature-level choice: the AAOS SDV guest with the HMI
     * distinguishes the member from the standalone member. It is a candidate
     * counterpart of the governed scope's AAOS-integrated vehicle-platform
     * integration mode, which the scope defines with AAOS as the
     * vehicle-platform domain; in this member S-CORE is on the host and AAOS
     * SDV runs the HMI guest. Whether the scope revision reuses that mode or
     * introduces another one is the ADR's decision; declaring a
     * configuration is phase 9 work after the PLEML adoption decision.
     */
  }

  part crossDomainHMIPath : CommonProductLineCapability {
    doc /*
     * CLS-MW-005, common capability conditional on the integration mode: the
     * one-way cross-domain HMI path is present whenever a member has an HMI
     * guest and absent otherwise, as the adapter layer is present whenever
     * middleware is selected. It does not itself distinguish members; the
     * integration mode does. It is a product interface of the member
     * (hmiPathInScope), not an engineering instrument.
     */
  }

  part scoreAssumptionsOfUseConformance : MemberConstraintCharacteristic {
    doc /*
     * CLS-MW-006, constraint: the assumptions of use that Eclipse S-CORE
     * v0.9.0 states for the application and for the operating system bound
     * every member that realizes the middleware layer on S-CORE; phases 5
     * and 8 carry them as requirements and realization constraints. No
     * conformance is claimed here.
     */
  }

  part integratorObligationsAndBench : EvidenceCapabilityCharacteristic {
    doc /*
     * CLS-MW-007, evidence capability: the integrator's obligations under the
     * assumptions of use and the bench of the runnable proof (ASM-MW-025)
     * with its retained evidence belong to the engineering and assurance
     * system, not to the member product; phase 10 argues the proof from
     * them.
     */
  }

  /* Phase 3 revalidation of the INC-MW-003 baseline, and the increment binding. */
  comment ClassificationRevalidationNote about scoreTwoDomainClassificationConcern /*
   * Holds unchanged for the S-CORE variant: the features middleware
   * selection and application selection as native variation/variant in the
   * platform stack; the baseline common capabilities adapter layer, signal
   * access, lifecycle coordination, health monitoring, diagnostic access and
   * update coordination; the deferred security and trust boundary. The
   * deferred safety-path decision stays deferred but is bounded for this
   * member by ASM-MW-028. Extended: the per-execution-domain platform
   * variability, the AAOS SDV HMI guest, the cross-domain HMI path, the
   * assumptions-of-use constraint and the evidence capability above.
   */
  dependency scoreClassificationBelongsToIncrement
    from scoreTwoDomainClassificationConcern
    to DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareIntegrationIncrement;
  dependency scoreClassificationFromOperationalContext
    from scoreTwoDomainClassificationConcern
    to DE4SDV_MiddlewareSCOREOperationalContext::scoreTwoDomainOperationalContext;
  dependency scoreVariantHoldsBaselineClassificationConcern
    from eclipseSCOREMiddlewareVariant
    to DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::productLineCapabilityClassificationConcern;
  dependency scoreVariantOnMiddlewareVariation
    from eclipseSCOREMiddlewareVariant
    to DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware;
  dependency scoreVariantReferenceOnlyInGovernedScope
    from eclipseSCOREMiddlewareVariant
    to DE4SDV_AEBSProductLineScope::ReferenceOnlyAlternativeSet::eclipseSCORE;
  dependency scoreAdapterHoldsBaselineAdapterLayer
    from autowareToSCOREAdapter
    to DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::adapterLayer;
  dependency scoreAdapterOnAdapterVariant
    from autowareToSCOREAdapter
    to DE4SDV_SDVPlatformStack::AutowareToSCOREAdapter;
  dependency perDomainVariabilityClosesTwoDomainGap
    from perExecutionDomainPlatformVariability
    to DE4SDV_MiddlewareSCOREFraming::gapTwoDomainMemberNotExpressible;
  dependency hmiGuestCandidateCounterpartOfAAOSIntegratedMode
    from aaosSDVHMIGuest
    to DE4SDV_AEBSProductLineScope::vehiclePlatformIntegrationMode::aaosIntegrated;
  dependency hmiPathOnFramingScopeItem
    from crossDomainHMIPath
    to DE4SDV_MiddlewareSCOREFraming::scoreMiddlewareScope::hmiPathInScope;
  dependency safetyPathDecisionBoundedByEmergencyPathAssumption
    from DE4SDV_MiddlewareSCOREFraming::asmEmergencyCommandPathStaysOnLinuxHost
    to DE4SDV_MiddlewareFeatureClassification::Features::Middleware::FeatureClassification::safetyPathDecision;
  dependency assumptionsOfUseConstraintOnPinnedBaseline
    from scoreAssumptionsOfUseConformance
    to DE4SDV_MiddlewareSCOREFraming::asmSCOREBaselinePinned;
  dependency evidenceCapabilityOnBenchAssumption
    from integratorObligationsAndBench
    to DE4SDV_MiddlewareSCOREFraming::asmBoundedBenchDemonstration;

  concern scoreTwoDomainClassificationConcern : ProductLineCapabilityClassificationConcern {
    doc /*
     * Reviewers need each characteristic of the two-domain member classified
     * as a feature, a common capability, a variability-structure change, a
     * constraint or an evidence capability, with its reason and its baseline
     * revalidation, before phase 4 derives needs; the realization coverage
     * of the S-CORE variant is the framing's concern, not this one.
     */
    subject;
    stakeholder productLineEngineer : ProductLineEngineer;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view scoreTwoDomainClassificationView : TVD::TableView {
    viewpoint selectedProductLineClassificationViewpoint : ProductLineClassificationViewpoint {
      frame scoreTwoDomainClassificationConcern;
    }

    expose eclipseSCOREMiddlewareVariant;
    expose autowareToSCOREAdapter;
    expose perExecutionDomainPlatformVariability;
    expose aaosSDVHMIGuest;
    expose crossDomainHMIPath;
    expose scoreAssumptionsOfUseConformance;
    expose integratorObligationsAndBench;
    filter @ SysML::PartUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Classification :> columnViews {
      attribute :>> featureToRender = CT::heritage;
    }
    view Rationale :> columnViews {
      attribute :>> featureToRender = CT::documentation;
      attribute :>> columnWidth = 360;
    }
  }
}
