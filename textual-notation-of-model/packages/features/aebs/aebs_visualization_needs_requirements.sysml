/*
 * DE4SDV AEBS visualization needs and System 2 requirements slice.
 *
 * INC-AEBS-010 Phase 3–5 content: product-line classification, stakeholder
 * needs, and System 2 requirement candidates for the AEBS visualization test
 * system. Needs continue the existing N-AEBS series (N-AEBS-009..013);
 * requirements continue the dedicated System 2 series
 * (REQ-AEBS-S2-002..021) to avoid collision with System 1
 * REQ-AEBS-001..015 and REQ-AEBS-S2-001 in aebs_needs_requirements.sysml.
 *
 * All requirements are System 2 engineering-instrumentation candidates.
 * None is a System 1 product obligation, and none prescribes TCP, protobuf,
 * SDV Gateway, Java, or Cuttlefish. Each requirement's subject is the
 * visualization test system framed for INC-AEBS-010
 * (DE4SDV_AEBSVisualizationFraming::system2VisualizationInstrument), the
 * entity its statement constrains; the increment is the subject of the
 * problem statement and the needs, not of the requirements.
 */

package DE4SDV_AEBSVisualizationNeedsRequirements {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_RelationshipSuccessor::*;
  private import DE4SDV_AEBSVisualizationFraming::*;
  private import DE4SDV_AEBSVisualizationOperationalContext::*;
  private import SAF_Viewpoints::*;
  private import Views::*;
  private import SysideViews::**;

  requirement def VisualizationEngineeringNeed :> StakeholderNeedCandidate {
    doc /* Need for bounded, honest AEBS visualization engineering support. */
  }
  requirement def VisualizationInstrumentRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for the System 2 visualization test system. */
  }

  package VisualizationClassification {
    part visualizationTestSystemClassification : DeferredProductLineScope {
      doc /*
       * CLS-AEBS-010-001: The AEBS visualization is System 2 engineering and
       * evidence instrumentation. It is not a product feature, not a common
       * capability, and must not enter any System 1 bill of features.
       */
    }
    part aebsCapabilityRemainsCommon : CommonProductLineCapability {
      doc /*
       * CLS-AEBS-010-002: VehicleTargetAEBS remains a common System 1
       * capability; this increment changes nothing about that classification.
       */
    }
  }

  /* Each need frames visualizationScenarioConcern, the stakeholder concern of
   * this increment's concern-framing and operational-context slice. The needs
   * elaborate the observation story that concern frames: live state on the
   * actual AAOS display, per-field provenance, fail-closed dispositions,
   * display order matching source order, and separation from the unchanged
   * System 1 AEBS story. */
  package VisualizationNeeds {
    requirement needLiveVisualizationOnAAOS : VisualizationEngineeringNeed {
      doc /* N-AEBS-009 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder systemsEngineer : SystemsEngineer;
      stakeholder reviewer : OpenSourceReviewer;
      frame visualizationScenarioConcern;
      require constraint statement { language "English" /* Systems engineers and reviewers need live AEBS threat and intervention state visible on an actual AAOS SDV display so that stakeholder-visible AEBS behavior can be reviewed without a host-side substitute. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing; GCP AAOS runtime proof environment";
      attribute :>> rationale = "Stakeholder-visible AEBS behavior must be reviewable on a real AAOS display, not a host substitute.";
    }
    requirement needPreservedSourceProvenance : VisualizationEngineeringNeed {
      doc /* N-AEBS-010 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder systemsEngineer : SystemsEngineer;
      stakeholder verificationEngineer : VerificationEngineer;
      frame visualizationScenarioConcern;
      require constraint statement { language "English" /* Systems engineers need source provenance, units, coordinate frame, timestamps, rate and freshness, validity, and bounded displayed cardinality preserved between native Autoware output, DE4SDV AEBS coordination state, and display-derived presentation. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "Displayed values must remain traceable to their source identity and context.";
    }
    requirement needFailClosedDegradation : VisualizationEngineeringNeed {
      doc /* N-AEBS-011 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder systemsEngineer : SystemsEngineer;
      stakeholder maintainer : Maintainer;
      frame visualizationScenarioConcern;
      require constraint statement { language "English" /* Systems engineers and maintainers need stale, unavailable, invalid, and restored display behavior so that a lost or invalid source cannot be misread as current AEBS state. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "A lost or invalid source must never be misread as current AEBS state.";
    }
    requirement needCorrelatableEvidence : VisualizationEngineeringNeed {
      doc /* N-AEBS-012 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder verificationEngineer : VerificationEngineer;
      frame visualizationScenarioConcern;
      require constraint statement { language "English" /* Verification engineers need source-to-screen correlation and replayable evidence so that displayed states can be traced to observed source events. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "Verification needs source-to-screen correlation and replayable evidence.";
    }
    requirement needNonInterference : VisualizationEngineeringNeed {
      doc /* N-AEBS-013 draft System 2 need. */
      subject increment : VisualizationIncrement;
      stakeholder maintainer : Maintainer;
      stakeholder verificationEngineer : VerificationEngineer;
      frame visualizationScenarioConcern;
      require constraint statement { language "English" /* Maintainers and verification engineers need assurance that visualization instrumentation cannot command or modify AEBS detection, warning, intervention, or release behavior. */ }
      attribute :>> status = ReqStatus::InDevelopment;
      attribute :>> source = "INC-AEBS-010 increment framing";
      attribute :>> rationale = "Visualization instrumentation must not influence the behavior it observes.";
    }
  }

  /* Each requirement records one primary verification method, as planning
   * data with no result. It is test where the statement constrains runtime
   * behavior, checked by operating the bench under controlled conditions
   * with recorded data. It is inspect where the statement constrains what is
   * presented or structurally absent (no command path, no host browser page,
   * no impersonating or display-derived decision values, stated boundaries,
   * non-color cues), checked by examining retained frames, interface dumps,
   * and the wire contract. Where a verification case exists, the choice
   * follows how its collectData step checks the requirement. */
  package VisualizationRequirements {
    requirement reqSourceFidelity : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-002 System 2 candidate derived from N-AEBS-009 and N-AEBS-010. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall preserve source identity, timestamp, units, coordinate frame, freshness, validity, and bounded cardinality for each displayed AEBS value or state. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009 and N-AEBS-010";
      attribute :>> rationale = "Preserves provenance for each displayed value.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqNativeParticipation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-003 System 2 candidate derived from N-AEBS-009. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall consume live output from the pinned native Autoware AEB component: RSS threshold data and the exact native intervention diagnostic. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "Anchors the display to the pinned native Autoware AEB component.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqNoNativeImpersonation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-014 System 2 candidate derived from N-AEBS-010. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall not present coordinator-derived distance values as native Autoware output. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-010";
      attribute :>> rationale = "Coordinator-derived values must not masquerade as native Autoware output.";
      attribute :>> verificationMethod = "inspect";
    }
    requirement reqDe4sdvParticipation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-004 System 2 candidate derived from N-AEBS-009. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall consume live DE4SDV AEBS warning request, braking request, and intervention lifecycle state from the existing AEBS coordinator. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "Displays the DE4SDV coordinator's own warning, braking, and lifecycle state.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqNonInterference : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-005 System 2 candidate derived from N-AEBS-013. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall expose no command path from display, bridge, or transport into Autoware, the AEBS coordinator, or vehicle control. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-013";
      attribute :>> rationale = "No command path from instrumentation into AEBS or vehicle control.";
      attribute :>> verificationMethod = "inspect";
    }
    requirement reqFailClosedFreshness : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-006 System 2 candidate derived from N-AEBS-011. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* When no valid frame is accepted for the selected bounded timeout, the visualization test system shall suppress threat geometry and present an explicit stale disposition. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Stale input must suppress threat geometry rather than display it.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqAvailabilityDisposition : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-007 System 2 candidate derived from N-AEBS-011. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* When no visualization source or service is available, or before the first valid frame arrives, the visualization test system shall present an explicit unavailable disposition. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Unavailable sources need an explicit disposition, not silence.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqInvalidRejection : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-008 System 2 candidate derived from N-AEBS-011. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall reject unsupported schema, malformed, non-finite, out-of-range, stale-timestamp, and non-monotonic frames without displaying their payload values. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Malformed frames must be rejected without displaying payload values.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqRestorationBehavior : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-009 System 2 candidate derived from N-AEBS-011. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* After a failure disposition, the visualization test system shall present a bounded restored indication after the selected consecutive-valid-frame criterion is met, without application restart. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011";
      attribute :>> rationale = "Recovery must be bounded and observable without application restart.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqRealAAOSRendering : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-010 System 2 candidate derived from N-AEBS-009 and N-AEBS-012. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall render AEBS state in a native application inside a booted display-capable AAOS SDV guest. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009 and N-AEBS-012";
      attribute :>> rationale = "The rendering surface must be the real AAOS guest application.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqAaosEnvironmentObservation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-012 System 2 candidate derived from N-AEBS-009. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* While AEBS state is rendered, the visualization test system shall observe the AAOS SDV guest package manager, system server, display composition, vehicle service, and SDV gateway within the same rendered session. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "Runtime environment evidence must come from the same rendered session.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqNoHostBrowserSurface : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-013 System 2 candidate derived from N-AEBS-009. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall not use a host-side browser page as the AEBS rendering surface. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-009";
      attribute :>> rationale = "A host-side browser page is not the AAOS rendering surface the need demands.";
      attribute :>> verificationMethod = "inspect";
    }
    requirement reqEvidenceCorrelation : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-011 System 2 candidate derived from N-AEBS-012. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall retain source, transport, ingress, and guest identity, sequence, timestamp, log, and guest-native capture records for each rendered state so that each rendered state can be correlated with its observed source event. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-012";
      attribute :>> rationale = "Each rendered state must be correlatable with its observed source event.";
      attribute :>> verificationMethod = "test";
    }

    requirement reqReadOnlyBoundaryStatement : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-015 System 2 candidate derived from N-AEBS-013. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall state the read-only engineering-visualization boundary on its rendered display in every rendered session. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-013; obligation formerly stated in AC-AEBS-S2-003";
      attribute :>> rationale = "Disclosing the read-only boundary in every session supports the non-interference assurance that maintainers and verification engineers need.";
      attribute :>> verificationMethod = "inspect";
    }
    requirement reqObstacleGeometryFromFilteredCloud : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-016 System 2 candidate derived from N-AEBS-010. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall render display-derived obstacle geometry only from the native Autoware filtered obstacle point cloud. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-010; obligation formerly stated in AC-AEBS-S2-004";
      attribute :>> rationale = "Displayed obstacle geometry must keep one identified source.";
      attribute :>> verificationMethod = "inspect";
    }
    requirement reqNoDisplayDerivedDecisionMetric : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-017 System 2 candidate derived from N-AEBS-010. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall not present any display-derived scalar as a native Autoware decision metric. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-010; obligation formerly stated in AC-AEBS-S2-004";
      attribute :>> rationale = "Display-derived values must not masquerade as native Autoware decision metrics.";
      attribute :>> verificationMethod = "inspect";
    }
    requirement reqDecisionDistanceExclusionStatement : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-018 System 2 candidate derived from N-AEBS-010. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall state on its rendered display that AEB decision distances are not visualized. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-010; obligation formerly stated in AC-AEBS-S2-004";
      attribute :>> rationale = "Viewers must not infer native AEB decision distances from the display.";
      attribute :>> verificationMethod = "inspect";
    }
    requirement reqObstacleGeometryExpiry : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-019 System 2 candidate derived from N-AEBS-011. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* When no filtered obstacle-cloud update has been received within the selected receipt-based staleness bound, the visualization test system shall suppress the display-derived obstacle geometry, including while accepted live frames continue. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011; obligation formerly stated in AC-AEBS-S2-005";
      attribute :>> rationale = "Expired obstacle geometry must not be displayed as current while other fields stay live.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqNoFreshDataSubstitution : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-020 System 2 candidate derived from N-AEBS-011. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* When no filtered obstacle-cloud update has been received within the selected receipt-based staleness bound, the visualization test system shall not substitute interpolated, smoothed, or predicted values for the missing fresh data. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011; obligation formerly stated in AC-AEBS-S2-005";
      attribute :>> rationale = "Synthesized values would let a lost source be misread as current AEBS state.";
      attribute :>> verificationMethod = "test";
    }
    requirement reqNonColorStateCue : VisualizationInstrumentRequirementCandidate {
      doc /* REQ-AEBS-S2-021 System 2 candidate derived from N-AEBS-011. */
      subject visualizationTestSystem :> system2VisualizationInstrument;
      require constraint statement { language "English" /* The visualization test system shall not use color as the sole cue of a rendered degraded disposition. */ }
      attribute :>> status = ReqStatus::ReadyForReview;
      attribute :>> source = "Derived from N-AEBS-011; obligation formerly stated in AC-AEBS-S2-006";
      attribute :>> rationale = "A degraded disposition must stay recognizable without relying on color alone.";
      attribute :>> verificationMethod = "inspect";
    }
  }

  public import VisualizationNeeds::*;
  public import VisualizationRequirements::*;

  /* Requirement-to-need derivation: only the governed DerivesFromNeed
   * connection counts (need -> derivedRequirement); a plain dependency does
   * not. Provenance only, no satisfaction claim. */
  connection reqSourceFidelityDerivedFromLiveVisualizationOnAAOS : DerivesFromNeed connect needLiveVisualizationOnAAOS to reqSourceFidelity;
  connection reqSourceFidelityDerivedFromPreservedSourceProvenance : DerivesFromNeed connect needPreservedSourceProvenance to reqSourceFidelity;
  connection reqNativeParticipationDerivedFromLiveVisualizationOnAAOS : DerivesFromNeed connect needLiveVisualizationOnAAOS to reqNativeParticipation;
  connection reqNoNativeImpersonationDerivedFromPreservedSourceProvenance : DerivesFromNeed connect needPreservedSourceProvenance to reqNoNativeImpersonation;
  connection reqDe4sdvParticipationDerivedFromLiveVisualizationOnAAOS : DerivesFromNeed connect needLiveVisualizationOnAAOS to reqDe4sdvParticipation;
  connection reqNonInterferenceDerivedFromNonInterference : DerivesFromNeed connect needNonInterference to reqNonInterference;
  connection reqFailClosedFreshnessDerivedFromFailClosedDegradation : DerivesFromNeed connect needFailClosedDegradation to reqFailClosedFreshness;
  connection reqAvailabilityDispositionDerivedFromFailClosedDegradation : DerivesFromNeed connect needFailClosedDegradation to reqAvailabilityDisposition;
  connection reqInvalidRejectionDerivedFromFailClosedDegradation : DerivesFromNeed connect needFailClosedDegradation to reqInvalidRejection;
  connection reqRestorationBehaviorDerivedFromFailClosedDegradation : DerivesFromNeed connect needFailClosedDegradation to reqRestorationBehavior;
  connection reqRealAAOSRenderingDerivedFromLiveVisualizationOnAAOS : DerivesFromNeed connect needLiveVisualizationOnAAOS to reqRealAAOSRendering;
  connection reqRealAAOSRenderingDerivedFromCorrelatableEvidence : DerivesFromNeed connect needCorrelatableEvidence to reqRealAAOSRendering;
  connection reqAaosEnvironmentObservationDerivedFromLiveVisualizationOnAAOS : DerivesFromNeed connect needLiveVisualizationOnAAOS to reqAaosEnvironmentObservation;
  connection reqNoHostBrowserSurfaceDerivedFromLiveVisualizationOnAAOS : DerivesFromNeed connect needLiveVisualizationOnAAOS to reqNoHostBrowserSurface;
  connection reqEvidenceCorrelationDerivedFromCorrelatableEvidence : DerivesFromNeed connect needCorrelatableEvidence to reqEvidenceCorrelation;
  /* REQ-AEBS-S2-015..021 carry the obligations formerly stated inside
   * acceptance criteria AC-AEBS-S2-003 to AC-AEBS-S2-006. A criterion records
   * the expected result of the requirement it bounds and adds no obligation,
   * so each added obligation is a design-input requirement of its own,
   * derived from the need of the requirement its criterion bounds. */
  connection reqReadOnlyBoundaryStatementDerivedFromNonInterference : DerivesFromNeed connect needNonInterference to reqReadOnlyBoundaryStatement;
  connection reqObstacleGeometryFromFilteredCloudDerivedFromPreservedSourceProvenance : DerivesFromNeed connect needPreservedSourceProvenance to reqObstacleGeometryFromFilteredCloud;
  connection reqNoDisplayDerivedDecisionMetricDerivedFromPreservedSourceProvenance : DerivesFromNeed connect needPreservedSourceProvenance to reqNoDisplayDerivedDecisionMetric;
  connection reqDecisionDistanceExclusionStatementDerivedFromPreservedSourceProvenance : DerivesFromNeed connect needPreservedSourceProvenance to reqDecisionDistanceExclusionStatement;
  connection reqObstacleGeometryExpiryDerivedFromFailClosedDegradation : DerivesFromNeed connect needFailClosedDegradation to reqObstacleGeometryExpiry;
  connection reqNoFreshDataSubstitutionDerivedFromFailClosedDegradation : DerivesFromNeed connect needFailClosedDegradation to reqNoFreshDataSubstitution;
  connection reqNonColorStateCueDerivedFromFailClosedDegradation : DerivesFromNeed connect needFailClosedDegradation to reqNonColorStateCue;

  /* Planned validation scenarios: one per need, each drawn from the bounded
   * operational scenarios SC-AEBS-010-01..06 of this increment and tracing
   * them. Planning only: no execution, result, fitness-for-use verdict or
   * acceptance. Production driver-HMI and human-factors validation stay out
   * of scope. */
  part liveVisualizationOnAAOSValidationPlan : ValidationPlanningScenario {
    doc /* SC-AEBS-010-07, N-AEBS-009: planned stakeholder review. While the
         * instrumented member runs the healthy-monitoring and
         * warning-intervention-release scenarios, can systems engineers and
         * reviewers review live AEBS threat and intervention state on the
         * actual AAOS SDV display, without a host-side substitute? */
  }
  connection liveVisualizationOnAAOSValidationPlanning : ValidationPlanningAssociation connect needLiveVisualizationOnAAOS to liveVisualizationOnAAOSValidationPlan;
  dependency liveVisualizationOnAAOSValidationFromHealthyMonitoring from liveVisualizationOnAAOSValidationPlan to scenarioHealthyMonitoring;
  dependency liveVisualizationOnAAOSValidationFromWarningInterventionRelease from liveVisualizationOnAAOSValidationPlan to scenarioWarningInterventionRelease;

  part preservedSourceProvenanceValidationPlan : ValidationPlanningScenario {
    doc /* SC-AEBS-010-08, N-AEBS-010: planned stakeholder review. In the
         * healthy-monitoring and warning-intervention-release scenarios, can
         * systems engineers and verification engineers attribute each
         * displayed value or state to native Autoware output, DE4SDV AEBS
         * coordination state, or display-derived presentation, together with
         * its units, coordinate frame, timestamp, freshness, and validity? */
  }
  connection preservedSourceProvenanceValidationPlanning : ValidationPlanningAssociation connect needPreservedSourceProvenance to preservedSourceProvenanceValidationPlan;
  dependency preservedSourceProvenanceValidationFromHealthyMonitoring from preservedSourceProvenanceValidationPlan to scenarioHealthyMonitoring;
  dependency preservedSourceProvenanceValidationFromWarningInterventionRelease from preservedSourceProvenanceValidationPlan to scenarioWarningInterventionRelease;

  part failClosedDegradationValidationPlan : ValidationPlanningScenario {
    doc /* SC-AEBS-010-09, N-AEBS-011: planned stakeholder review. Across the
         * stale-source, unavailable-source, invalid-envelope, and restoration
         * scenarios, can systems engineers and maintainers recognize from the
         * display that no lost or invalid source is presented as current AEBS
         * state, and see when the current source state is restored? */
  }
  connection failClosedDegradationValidationPlanning : ValidationPlanningAssociation connect needFailClosedDegradation to failClosedDegradationValidationPlan;
  dependency failClosedDegradationValidationFromStaleSource from failClosedDegradationValidationPlan to scenarioStaleSource;
  dependency failClosedDegradationValidationFromUnavailableSource from failClosedDegradationValidationPlan to scenarioUnavailableSource;
  dependency failClosedDegradationValidationFromInvalidEnvelope from failClosedDegradationValidationPlan to scenarioInvalidEnvelope;
  dependency failClosedDegradationValidationFromRestoration from failClosedDegradationValidationPlan to scenarioRestoration;

  part correlatableEvidenceValidationPlan : ValidationPlanningScenario {
    doc /* SC-AEBS-010-10, N-AEBS-012: planned stakeholder review. After a
         * warning-intervention-release run, can verification engineers trace
         * each displayed state to its observed source event, in source order,
         * from the retained records, and repeat that correlation by replay? */
  }
  connection correlatableEvidenceValidationPlanning : ValidationPlanningAssociation connect needCorrelatableEvidence to correlatableEvidenceValidationPlan;
  dependency correlatableEvidenceValidationFromWarningInterventionRelease from correlatableEvidenceValidationPlan to scenarioWarningInterventionRelease;

  part nonInterferenceValidationPlan : ValidationPlanningScenario {
    doc /* SC-AEBS-010-11, N-AEBS-013: planned stakeholder review. In the
         * warning-intervention-release scenario, does what maintainers and
         * verification engineers can inspect give them the assurance they need
         * that the visualization neither commands nor modifies the unchanged
         * System 1 AEBS detection, warning, intervention, and release behavior? */
  }
  connection nonInterferenceValidationPlanning : ValidationPlanningAssociation connect needNonInterference to nonInterferenceValidationPlan;
  dependency nonInterferenceValidationFromWarningInterventionRelease from nonInterferenceValidationPlan to scenarioWarningInterventionRelease;

  /* Phase order provenance: needs/requirements (Phase 3–5) derive from the
   * framing slice of the same INC-AEBS-010; the increment part incAEBS010
   * (DE4SDV_AEBSVisualizationFraming) is the single increment identity. */


  part gapAaosTargetUnproven : IncrementGap {
    doc /*
     * GAP-AEBS-010-004: A display-capable AAOS SDV target with a working
     * application surface is required by REQ-AEBS-S2-010 but is not yet
     * proven at a pinned revision; realization selection stays deferred.
     */
  }
  part gapFreshnessParametersOpen : IncrementGap {
    doc /*
     * GAP-AEBS-010-005: The bounded timeout, consecutive-valid-frame count,
     * and restoration indication duration referenced by REQ-AEBS-S2-006 and
     * REQ-AEBS-S2-009 remain planning targets until the configuration slice.
     */
  }

  concern visualizationNeedsConcern : StakeholderNeedsConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }
  concern visualizationRequirementTraceConcern : RequirementTraceConcern {
    subject;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsVisualizationNeedsView : TVD::TableView {
    viewpoint selectedNeedsViewpoint : StakeholderRequirementDefinitionViewpoint { frame visualizationNeedsConcern; }
    expose VisualizationNeeds::*;
    filter @ SysML::RequirementUsage;
    attribute :>> includeReferenceElements = true;
    attribute :>> maxRowHeight = 300;
    view ID :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    }
    view Name :> columnViews {
      attribute :>> featureToRender = CT::heritage;
    }
    view Statement :> columnViews {
      attribute :>> featureToRender = CT::constraintLanguage {
        attribute constraintName = "statement";
        attribute constraintType = CL::ConT::required;
        attribute constraintLanguage = "English";
      }
      attribute :>> columnWidth = 360;
    }
  }

  view aebsVisualizationRequirementTraceView {
    viewpoint selectedTraceViewpoint : SystemRequirementTraceabilityViewpoint { frame visualizationRequirementTraceConcern; }
    expose VisualizationNeeds::*;
    expose VisualizationRequirements::*;
    render asTreeDiagram;
  }
}
