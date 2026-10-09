/*
 * DE4SDV INC-AEBS-010 Phase 10 verification and evidence model slice.
 *
 * This slice is the Phase 10 V&V portion of the INC-AEBS-010 visualization
 * chain. It defines the verification cases, acceptance criteria, retained
 * evidence records, bounded assurance claim, deferred counterclaims, and
 * claim-boundary semantics for the System 2 read-only AEBS forward-situation
 * visualization test system.
 *
 * Acceptance criteria are not requirements: each records the expected
 * result of the design-input requirement it bounds, and each verification
 * case verifies that requirement next to its criterion. The claim, arguments
 * and counter-claims are assurance artifacts (DE4SDV_AssuranceArgumentation),
 * outside the requirement lineage.
 *
 * It consumes the retained evidence committed by the implementation campaign
 * (implementation/aebs-aaos-sdv-visualization-bench/evidence/010/). Every
 * evidence part below names the exact retained artifact; the dispositions
 * follow the evidence ladder vocabulary (observed_bounded /
 * deferred_not_proven / not_claimed) with scenario-safety outcome explicitly
 * deferred_not_proven. No safety, certification, homologation,
 * production-readiness, or vehicle-command claim is made or implied.
 *
 * Package name note: the visualization chain increment ID is INC-AEBS-010,
 * and this slice is its Phase 10 V&V evidence record
 * (DE4SDV_AEBSVisualizationVerificationEvidence). The package drops the
 * increment number per naming-conventions.md section 7: it is the enduring
 * canonical verification-evidence model of the visualization concern; the
 * increment identity stays owned by the framing slice (incAEBS010).
 */

package DE4SDV_AEBSVisualizationVerificationEvidence {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_AssuranceArgumentation::*;
  private import DE4SDV_ProductLine::*;
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_ExecutionEnvironments::*;
  private import DE4SDV_AEBSVisualizationFraming::*;
  private import DE4SDV_AEBSVisualizationNeedsRequirements::*;
  private import DE4SDV_AEBSVisualizationPhysicalSoftwareRealization::*;
  private import DE4SDV_AEBSVisualizationVariabilityConfiguration::*;
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import ScalarValues::*;
  private import SAF_Viewpoints::*;
  private import Views::*;

  /*
   * INC-AEBS-010 increment identity: owned by the canonical framing slice
   * (DE4SDV_AEBSVisualizationFraming::incAEBS010). This evidence slice is
   * bounded Phase 10 V&V content for that increment, not a second increment
   * identity; visualizationVerificationSystem below carries the slice's trace.
   */
  references incAEBS010;

  /* ──────────────────────────────────────────
   * Evidence vocabulary and observation records
   * ────────────────────────────────────────── */

  enum def VisualizationScenario {
    liveChainCorrelation;
    lifecycleArc;
    readOnlyBoundary;
    provenanceSeparation;
    failClosedStaleness;
    degradedStateRendering;
    restorationBehavior;
  }

  enum def VisualizationEvidenceDisposition {
    planned;
    observedBounded;
    observedUnidentifiedBuild;
    partial;
    blocked;
    notClaimed;
  }

  item def VisualizationObservation {
    attribute callbackCount : ScalarValues::Integer;
    attribute sequenceSpan : ScalarValues::String;
    attribute observedRateHz : ScalarValues::Real;
    attribute gapCount : ScalarValues::Integer;
    attribute independentCapture : Boolean;
  }

  item def RetainedVisualizationEvidence {
    attribute configurationIdentity : ScalarValues::String;
    attribute executionEnvironmentIdentity : ScalarValues::String;
    attribute contractIdentity : ScalarValues::String;
    attribute rawObservationArtifact : ScalarValues::String;
    attribute independentObserverIdentity : ScalarValues::String;
    attribute disposition : VisualizationEvidenceDisposition;
    attribute claimBoundary : ScalarValues::String;
  }

  item def ReplayedVisualizationEvaluation {
    attribute scenario : VisualizationScenario;
    attribute outcome : VisualizationEvidenceDisposition;
    attribute acceptanceSummary : ScalarValues::String;
  }

  /*
   * Verdict mapping: only observedBounded evidence produces pass. partial
   * maps to inconclusive — a partial observation cannot upgrade into an
   * acceptance claim without a separately justified bounded-pass
   * interpretation (none exists for the retained campaign).
   * observedUnidentifiedBuild (observed on a build that is not exactly
   * identified, GAP-AEBS-010-009) falls to inconclusive until re-capture.
   */
  calc def MapVisualizationOutcomeToVerdict {
    in outcome : VisualizationEvidenceDisposition;
    return verdict : VerdictKind =
      if outcome == VisualizationEvidenceDisposition::observedBounded? VerdictKind::pass
      else if outcome == VisualizationEvidenceDisposition::partial? VerdictKind::inconclusive
      else if outcome == VisualizationEvidenceDisposition::blocked? VerdictKind::inconclusive
      else if outcome == VisualizationEvidenceDisposition::notClaimed? VerdictKind::inconclusive
      else VerdictKind::inconclusive;
  }

  /* ──────────────────────────────────────────
   * Verification bench (System 1 unchanged / System 2 instrument)
   * ────────────────────────────────────────── */

  part def VisualizationVerificationBench {
    doc /*
     * System 1 is the configured member executing unchanged AEBS behavior:
     * the uninstrumented AAOS-integrated Autoware member governed by the
     * accepted product-line scope. System 2 is the visualization test system
     * and its campaign environment — the instrumented test article plus
     * observation instrumentation; it is not a product selection. The
     * instrument observes System 1 read-only and issues no vehicle command.
     */
    /* System 1 subject: uninstrumented configured member (scope member). */
    part system1MemberProduct : DE4SDV_MiddlewareVariabilityConfiguration::MiddlewareAutowareAAOSSDVConfiguredMember;
    /* Configuration role: the configured test article AEBS-CONFIG-010-001. */
    part system2TestArticle :> testArticle;
    /* Subject role: the visualization test system as realized in that article; the verified design-input requirements bind to it. */
    ref part system2Instrument :> system2VisualizationInstrument = system2TestArticle.visualizationChain.instrument;
    attribute scenario : VisualizationScenario;
  }

  part liveChainCorrelationBench : VisualizationVerificationBench {
    attribute :>> scenario = VisualizationScenario::liveChainCorrelation;
  }
  part lifecycleArcBench : VisualizationVerificationBench {
    attribute :>> scenario = VisualizationScenario::lifecycleArc;
  }
  part readOnlyBoundaryBench : VisualizationVerificationBench {
    attribute :>> scenario = VisualizationScenario::readOnlyBoundary;
  }
  part provenanceSeparationBench : VisualizationVerificationBench {
    attribute :>> scenario = VisualizationScenario::provenanceSeparation;
  }
  part failClosedStalenessBench : VisualizationVerificationBench {
    attribute :>> scenario = VisualizationScenario::failClosedStaleness;
  }
  part degradedStateRenderingBench : VisualizationVerificationBench {
    attribute :>> scenario = VisualizationScenario::degradedStateRendering;
  }
  part restorationBehaviorBench : VisualizationVerificationBench {
    attribute :>> scenario = VisualizationScenario::restorationBehavior;
  }

  /* ──────────────────────────────────────────
   * Acceptance criteria: expected results, not requirements
   * ────────────────────────────────────────── */

  /* Each criterion records the expected result of the design-input
   * requirement it bounds ("will be shown to have been met when ...") and
   * adds no obligation of its own; AC-AEBS-S2-008 is the verdict-record rule
   * applied by every case. Obligations the criteria formerly added are
   * design-input requirements REQ-AEBS-S2-015..021 in
   * DE4SDV_AEBSVisualizationNeedsRequirements. */
  requirement def VisualizationAcceptanceCriterion :> AcceptanceCriterion;

  requirement acceptanceCriterionChainCorrelation : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-001; bounded verification of source-to-screen correlation. */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* REQ-AEBS-S2-011 will be shown to have been met when the retained take holds source, transport, ingress, and guest identity, sequence, timestamp, log, and guest-native capture records for each rendered state, each rendered state is correlated with its observed source event, and the accepted callbacks are consecutive with zero sequence gaps over the retained take. */ }
  }

  requirement acceptanceCriterionLifecycleArc : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-002; bounded verification of the four-state arc in one take. */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* REQ-AEBS-S2-010 will be shown to have been met when one uninterrupted real-time take of the native application in the booted display-capable AAOS SDV guest presents the reducer-driven MONITORING, WARNING, INTERVENTION, and RELEASED dispositions from accepted frames, the release disposition is accompanied by a verified zero-speed stop observation, and no edited or older-generation footage is presented as part of the take. */ }
  }

  requirement acceptanceCriterionReadOnlyBoundary : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-003; read-only boundary verification. */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* REQ-AEBS-S2-005 will be shown to have been met when the visualization test system publishes nothing to the vehicle runtime and issues no vehicle command. */ }
  }

  requirement acceptanceCriterionProvenanceSeparation : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-004; display-derived versus native decision semantics separation. */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* REQ-AEBS-S2-014 will be shown to have been met when no retained frame or user-interface dump presents a coordinator-derived distance value as native Autoware output. */ }
  }

  requirement acceptanceCriterionFailClosedStaleness : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-005; fail-closed staleness verification. */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* REQ-AEBS-S2-019 will be shown to have been met when the retained take shows the obstacle range, bearing, and points cleared within the receipt-based staleness bound after the filtered obstacle-cloud source stops updating, while the accepted frame sequence continues. */ }
  }

  requirement acceptanceCriterionDegradedRendering : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-006; degraded-state rendering verification (fixture path). */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* REQ-AEBS-S2-007 will be shown to have been met when, under deterministic closed-loop frame injection, the unavailable disposition is rendered with live geometry cleared and the health chip identifying the degraded condition whenever no visualization source or service is available or no valid frame has yet arrived. The same campaign renders the stale and invalid degraded dispositions the same way; that observation is not a success criterion of REQ-AEBS-S2-006 or REQ-AEBS-S2-008. */ }
  }

  requirement acceptanceCriterionRestoration : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-007; restoration behavior criterion (planned). */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* REQ-AEBS-S2-009 will be shown to have been met when a retained run shows that, after each failure disposition, the restored indication appears once the consecutive-valid-frame count bound as AO-AEBS-010-006 is reached, stays for the selected bounded duration, and the same application process runs throughout. */ }
  }

  requirement acceptanceCriterionEvidenceIntegrity : VisualizationAcceptanceCriterion {
    doc /* AC-AEBS-S2-008; evidence integrity and claim-boundary criterion. */
    subject bench : VisualizationVerificationBench;
    require constraint statement { language "English" /* A retained verdict is acceptable only when it binds the configured test article, execution environment, wire contract, raw observation artifacts, and independent observer identities. Missing evidence is recorded as planned, partial, blocked, or not claimed, never as an observed runtime pass. */ }
  }

  /* ──────────────────────────────────────────
   * Retained evidence records (exact artifacts in the implementation bench)
   * ────────────────────────────────────────── */

  part liveChainEvidence : RetainedVisualizationEvidence {
    doc /*
     * EVID-AEBS-S2-001. Retained live-chain correlation evidence for the
     * corrected final campaign (2026-09-01): 1090 consecutive app-side
     * onGatewayFrame callbacks, sequence span 22891-23980, zero gaps, 10 Hz,
     * mirrored by ingress-side publishes over the chain pinned Autoware AEB
     * f603d8759c92fb2f423f1544844e13086d79ad09 -> ROS bridge frame assembler
     * -> TCP frame server :4721 -> adb reverse -> native ingress -> Gateway
     * Data Tunnel topic aebs-visualization-frame (schema v1.1) -> app
     * onGatewayFrame. Observer pass_observed_chain, exit 0, 1597
     * observations, 0 errors.
     */
    attribute :>> configurationIdentity = "AEBS-CONFIG-010-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a de4sdv-aaos-build + de4sdv-ros2-autoware, sdv_ivi_cf guest, corrected final generation";
    attribute :>> contractIdentity = "interface/aebs_visualization.proto schema v1.1, topic aebs-visualization-frame";
    attribute :>> rawObservationArtifact = "implementation/aebs-aaos-sdv-visualization-bench/evidence/010/forward-ui/final-hmi-v21-corrected/app-ingress-frame.log";
    attribute :>> independentObserverIdentity = "scenario_observer (pass_observed_chain, 1597 observations, 0 errors)";
    attribute :>> disposition = VisualizationEvidenceDisposition::observedUnidentifiedBuild;
    attribute :>> claimBoundary = "Live observation-chain evidence on the bench deployment, observed on a build that is not exactly identified (GAP-AEBS-010-009, re-capture pending); not verification of the configured test article, and not safety, braking-authority, certification, or production evidence.";
  }

  part lifecycleArcEvidence : RetainedVisualizationEvidence {
    doc /*
     * EVID-AEBS-S2-002. Retained continuous-take lifecycle evidence: one
     * uninterrupted 70.15 s screenrecord of the corrected final UI
     * generation covering MONITORING 0-10 s, WARNING ~10-11.5 s (24 obstacle
     * points, no braking), INTERVENTION ~11.5-14 s (braking latched), and
     * RELEASED ~14 s onward (ego speed 0.0 m/s, verified stop). Release
     * relation honestly recorded as release_while_native_diagnostic_retained;
     * scenario-safety outcome remains deferred_not_proven. The approved
     * publication cut composes a 3 s title card, the untouched 0-20 s of this
     * take, and a 3 s end card; the cards are editing frames, not app output.
     */
    attribute :>> configurationIdentity = "AEBS-CONFIG-010-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a de4sdv-aaos-build + de4sdv-ros2-autoware, sdv_ivi_cf guest, corrected final generation";
    attribute :>> contractIdentity = "screenrecord display 0, 1080x600";
    attribute :>> rawObservationArtifact = "implementation/aebs-aaos-sdv-visualization-bench/evidence/010/forward-ui/final-hmi-v21-corrected/raw-continuous.mp4";
    attribute :>> independentObserverIdentity = "scenario_observer state boundary extraction (segment.yaml)";
    attribute :>> disposition = VisualizationEvidenceDisposition::observedUnidentifiedBuild;
    attribute :>> claimBoundary = "One continuous take of the corrected generation, observed on a build that is not exactly identified (GAP-AEBS-010-009, re-capture pending); title/end cards are editing frames; not safety or certification evidence.";
  }

  part readOnlyBoundaryEvidence : RetainedVisualizationEvidence {
    doc /*
     * EVID-AEBS-S2-003. Read-only boundary evidence: the wire contract carries
     * no command path, the bridge subscribes only (no publishers, no
     * services, no actions), the ingress publishes into the Gateway Data
     * Tunnel only, and the provenance ribbon is present in every retained
     * public frame. Enforced additionally by the presentation-contract guard
     * tests in the repository test suite.
     */
    attribute :>> configurationIdentity = "AEBS-CONFIG-010-001";
    attribute :>> executionEnvironmentIdentity = "repository test suite + retained campaign artifacts";
    attribute :>> contractIdentity = "implementation/aebs-aaos-sdv-visualization-bench/interface/aebs_visualization.proto";
    attribute :>> rawObservationArtifact = "implementation/aebs-aaos-sdv-visualization-bench/evidence/010/forward-ui/final-hmi-v21-corrected/state-monitoring.png";
    attribute :>> independentObserverIdentity = "tests/test_aebs_visualization_hmi_presentation_contract.py + bridge non-interference tests";
    attribute :>> disposition = VisualizationEvidenceDisposition::observedUnidentifiedBuild;
    attribute :>> claimBoundary = "Structural and rendered-session read-only evidence; the rendered session ran on a build that is not exactly identified (GAP-AEBS-010-009, re-capture pending); no vehicle-interaction behavior is exercised or claimed.";
  }

  part provenanceSeparationEvidence : RetainedVisualizationEvidence {
    doc /*
     * EVID-AEBS-S2-004. Display-derived versus native decision semantics
     * separation evidence for the corrected generation: no
     * Target range / AEB braking threshold pair or RSS reference line is
     * rendered anywhere in the retained stills or UI dumps, obstacle geometry
     * is drawn only from the filtered cloud in base_link, and the
     * engineering-status panel states that AEB decision distances are not
     * visualized. Verified pre-recording against guest UI dumps and after by
     * visual review of the retained stills.
     */
    attribute :>> configurationIdentity = "AEBS-CONFIG-010-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a de4sdv-aaos-build + de4sdv-ros2-autoware, sdv_ivi_cf guest, corrected final generation";
    attribute :>> contractIdentity = "implementation/aebs-aaos-sdv-visualization-bench/VISUALIZATION-CONTRACT.md section 3 removal list";
    attribute :>> rawObservationArtifact = "implementation/aebs-aaos-sdv-visualization-bench/evidence/010/forward-ui/final-hmi-v21-corrected/state-warning.png";
    attribute :>> independentObserverIdentity = "tests/test_aebs_visualization_hmi_presentation_contract.py";
    attribute :>> disposition = VisualizationEvidenceDisposition::observedUnidentifiedBuild;
    attribute :>> claimBoundary = "Presentation-separation evidence for the corrected generation, observed on a build that is not exactly identified (GAP-AEBS-010-009, re-capture pending); not a claim about native Autoware AEB decision internals.";
  }

  part failClosedStalenessEvidence : RetainedVisualizationEvidence {
    doc /*
     * EVID-AEBS-S2-005. Fail-closed staleness evidence: within the retained
     * take, when the filtered obstacle-cloud source stopped updating, the
     * display-derived obstacle geometry was suppressed (range/bearing/points
     * cleared) while accepted live frames continued; obstacle geometry also
     * expired after cloud silence per the receipt-based bound. No
     * interpolation or prediction substituted for missing fresh data.
     */
    attribute :>> configurationIdentity = "AEBS-CONFIG-010-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a de4sdv-aaos-build + de4sdv-ros2-autoware, sdv_ivi_cf guest, corrected final generation";
    attribute :>> contractIdentity = "frame assembler receipt-based staleness bound (bridge source)";
    attribute :>> rawObservationArtifact = "implementation/aebs-aaos-sdv-visualization-bench/evidence/010/forward-ui/final-hmi-v21-corrected/segment.yaml";
    attribute :>> independentObserverIdentity = "app-ingress-frame.log field-level observation";
    attribute :>> disposition = VisualizationEvidenceDisposition::observedUnidentifiedBuild;
    attribute :>> claimBoundary = "Bounded staleness observation within one take, on a build that is not exactly identified (GAP-AEBS-010-009, re-capture pending); not a certification-grade freshness argument.";
  }

  part degradedRenderingEvidence : RetainedVisualizationEvidence {
    doc /*
     * EVID-AEBS-S2-006. Degraded-state rendering evidence from the state
     * campaign: stale, unavailable, and invalid dispositions rendered with
     * live geometry cleared and the health chip identifying the degraded
     * condition. The frame source was the PF-004 deterministic publisher,
     * NOT live Autoware 009B data; this evidence is fixture-path only and
     * must not be presented as live-chain evidence.
     */
    attribute :>> configurationIdentity = "AEBS-CONFIG-010-001";
    attribute :>> executionEnvironmentIdentity = "gcp-europe-west4-a de4sdv-aaos-build, sdv_ivi_cf guest, state-campaign generation";
    attribute :>> contractIdentity = "PF-004 deterministic publisher injection contract";
    attribute :>> rawObservationArtifact = "implementation/aebs-aaos-sdv-visualization-bench/evidence/010/state-campaign/stale.png";
    attribute :>> independentObserverIdentity = "per-state UI hierarchy dumps (state-campaign/*.xml)";
    attribute :>> disposition = VisualizationEvidenceDisposition::observedUnidentifiedBuild;
    attribute :>> claimBoundary = "Fixture-path rendering evidence only, on a build whose identity the state campaign does not record (GAP-AEBS-010-009, re-capture pending); not live Autoware degradation evidence.";
  }

  part restorationEvidencePlanned : PlannedExecutionEnvironmentEvidence {
    doc /*
     * EVID-AEBS-S2-007 (planned). Restoration behavior after a failure
     * disposition was not exercised in any retained INC-AEBS-010 campaign.
     * This record is explicitly planned evidence: it supports no observed
     * claim and is bound to the restoration gap below. Planned scope: the
     * restored indication after the selected consecutive-valid-frame
     * criterion, without application restart.
     */
  }

  /* ──────────────────────────────────────────
   * Verification cases
   * ────────────────────────────────────────── */

  /* Each objective verifies its acceptance criterion, the verdict-record rule
   * (AC-AEBS-S2-008) and the design-input requirements whose expected result
   * the criterion records, including the requirements that now carry the
   * obligations the criterion formerly added. A requirement's subject is the
   * visualization test system, so each verified requirement binds it to the
   * bench's system2Instrument, the visualization test system as realized in
   * the configured test article, instead of the whole bench. A verify is a
   * planned verification objective, not a verdict: the verdict stays the
   * case's evidence-bound return value. */

  verification def VisualizationChainCorrelationVerification {
    subject verifiedBench : VisualizationVerificationBench;
    objective chainCorrelationObjective {
      verify acceptanceCriterionChainCorrelation;
      verify acceptanceCriterionEvidenceIntegrity;
      verify reqEvidenceCorrelation { subject visualizationTestSystem = verifiedBench.system2Instrument; }
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenario = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapVisualizationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationLifecycleArcVerification {
    subject verifiedBench : VisualizationVerificationBench;
    objective lifecycleArcObjective {
      verify acceptanceCriterionLifecycleArc;
      verify acceptanceCriterionEvidenceIntegrity;
      verify reqRealAAOSRendering { subject visualizationTestSystem = verifiedBench.system2Instrument; }
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenario = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapVisualizationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationReadOnlyBoundaryVerification {
    subject verifiedBench : VisualizationVerificationBench;
    objective readOnlyBoundaryObjective {
      verify acceptanceCriterionReadOnlyBoundary;
      verify acceptanceCriterionEvidenceIntegrity;
      verify reqNonInterference { subject visualizationTestSystem = verifiedBench.system2Instrument; }
      verify reqReadOnlyBoundaryStatement { subject visualizationTestSystem = verifiedBench.system2Instrument; }
    }
    action collectData {
      @VerificationMethod{ kind = (inspect, test); }
      out item retainedEvidence : RetainedVisualizationEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenario = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapVisualizationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationProvenanceSeparationVerification {
    subject verifiedBench : VisualizationVerificationBench;
    objective provenanceSeparationObjective {
      verify acceptanceCriterionProvenanceSeparation;
      verify acceptanceCriterionEvidenceIntegrity;
      verify reqNoNativeImpersonation { subject visualizationTestSystem = verifiedBench.system2Instrument; }
      verify reqObstacleGeometryFromFilteredCloud { subject visualizationTestSystem = verifiedBench.system2Instrument; }
      verify reqNoDisplayDerivedDecisionMetric { subject visualizationTestSystem = verifiedBench.system2Instrument; }
      verify reqDecisionDistanceExclusionStatement { subject visualizationTestSystem = verifiedBench.system2Instrument; }
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenario = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapVisualizationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationFailClosedStalenessVerification {
    subject verifiedBench : VisualizationVerificationBench;
    objective failClosedStalenessObjective {
      verify acceptanceCriterionFailClosedStaleness;
      verify acceptanceCriterionEvidenceIntegrity;
      verify reqObstacleGeometryExpiry { subject visualizationTestSystem = verifiedBench.system2Instrument; }
      verify reqNoFreshDataSubstitution { subject visualizationTestSystem = verifiedBench.system2Instrument; }
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenario = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapVisualizationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationDegradedRenderingVerification {
    doc /*
     * Fixture-path verification case. Its subject scenario uses the PF-004
     * deterministic publisher; any verdict from it is bounded to that path
     * and does not transfer to the live Autoware chain.
     */
    subject verifiedBench : VisualizationVerificationBench;
    objective degradedRenderingObjective {
      verify acceptanceCriterionDegradedRendering;
      verify acceptanceCriterionEvidenceIntegrity;
      verify reqAvailabilityDisposition { subject visualizationTestSystem = verifiedBench.system2Instrument; }
      verify reqNonColorStateCue { subject visualizationTestSystem = verifiedBench.system2Instrument; }
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenario = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapVisualizationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationRestorationVerification {
    doc /*
     * Planned verification case. No retained campaign exercised restoration;
     * the case exists to bind the criterion and the gap, and its verdict
     * remains inconclusive until evidence is retained by a later campaign.
     */
    subject verifiedBench : VisualizationVerificationBench;
    objective restorationObjective {
      verify acceptanceCriterionRestoration;
      verify acceptanceCriterionEvidenceIntegrity;
      verify reqRestorationBehavior { subject visualizationTestSystem = verifiedBench.system2Instrument; }
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedVisualizationEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenario = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidence = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapVisualizationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  doc /* VC-AEBS-S2-001 verification case usage. */
  verification chainCorrelationVerification : VisualizationChainCorrelationVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> liveChainCorrelationBench;
  }

  doc /* VC-AEBS-S2-002 verification case usage. */
  verification lifecycleArcVerification : VisualizationLifecycleArcVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> lifecycleArcBench;
  }

  doc /* VC-AEBS-S2-003 verification case usage. */
  verification readOnlyBoundaryVerification : VisualizationReadOnlyBoundaryVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> readOnlyBoundaryBench;
  }

  doc /* VC-AEBS-S2-004 verification case usage. */
  verification provenanceSeparationVerification : VisualizationProvenanceSeparationVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> provenanceSeparationBench;
  }

  doc /* VC-AEBS-S2-005 verification case usage. */
  verification failClosedStalenessVerification : VisualizationFailClosedStalenessVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> failClosedStalenessBench;
  }

  doc /* VC-AEBS-S2-006 verification case usage. */
  verification degradedRenderingVerification : VisualizationDegradedRenderingVerification {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> degradedStateRenderingBench;
  }

  doc /* VC-AEBS-S2-007 verification case usage. */
  verification restorationVerification : VisualizationRestorationVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> restorationBehaviorBench;
  }

  part visualizationVerificationSystem {
    perform chainCorrelationVerification;
    perform lifecycleArcVerification;
    perform readOnlyBoundaryVerification;
    perform provenanceSeparationVerification;
    perform failClosedStalenessVerification;
    perform degradedRenderingVerification;
    perform restorationVerification;
  }

  /* ──────────────────────────────────────────
   * Criterion-to-requirement traces: the requirement each criterion bounds
   * ────────────────────────────────────────── */

  /* AC-AEBS-S2-005 bounds REQ-AEBS-S2-019 (expiry of obstacle geometry when
   * its source stops while frames continue), the behavior its retained take
   * exercised; the frame-timeout trigger of REQ-AEBS-S2-006 was not
   * exercised by that take. */

  dependency chainCorrelationToEvidenceRequirement
    from acceptanceCriterionChainCorrelation
    to reqEvidenceCorrelation;
  dependency chainCorrelationToRealAAOSRenderingRequirement
    from acceptanceCriterionLifecycleArc
    to reqRealAAOSRendering;
  dependency readOnlyBoundaryToNonInterferenceRequirement
    from acceptanceCriterionReadOnlyBoundary
    to reqNonInterference;
  dependency provenanceSeparationToNoImpersonationRequirement
    from acceptanceCriterionProvenanceSeparation
    to reqNoNativeImpersonation;
  dependency failClosedStalenessToGeometryExpiryRequirement
    from acceptanceCriterionFailClosedStaleness
    to reqObstacleGeometryExpiry;
  dependency degradedRenderingToAvailabilityRequirement
    from acceptanceCriterionDegradedRendering
    to reqAvailabilityDisposition;
  dependency restorationToRestorationRequirement
    from acceptanceCriterionRestoration
    to reqRestorationBehavior;

  /* Cross-increment traceability to the configured test article. The
   * configuration role (AEBS-CONFIG-010-001, testArticle) and the subject
   * role (the visualization test system as realized in that article) are
   * traced separately; no allocation relates them. */
  dependency verificationTestArticleTrace
    from visualizationVerificationSystem
    to testArticle;
  dependency verificationInstrumentTrace
    from visualizationVerificationSystem
    to testArticle::visualizationChain::instrument;
  dependency chainEvidenceToTestArticleChainTrace
    from liveChainEvidence
    to testArticle::visualizationChain;
  dependency lifecycleEvidenceToDisplayAppTrace
    from lifecycleArcEvidence
    to testArticle::visualizationChain::instrument::iviGuest::displayApp;
  dependency provenanceEvidenceToSourceProvenanceTrace
    from provenanceSeparationEvidence
    to coordinatorStateProvenance;

  /* ──────────────────────────────────────────
   * Claim-argument-evidence layer (INC-AEBS-010 Phase 10)
   * ────────────────────────────────────────── */

  /* Assurance artifacts, not requirements: they consume the verification
   * results above and do not derive from needs. */
  requirement def VisualizationClaim :> AssuranceClaim;

  requirement def VisualizationArgument :> AssuranceArgument;

  requirement def VisualizationCounterClaim :> AssuranceCounterClaim;

  requirement visualizationInstrumentationClaim : VisualizationClaim {
    doc /*
     * CLM-AEBS-S2-001: for AEBS-CONFIG-010-001 on the retained campaign
     * environment, the read-only visualization instrumentation observed the
     * live pinned-Autoware chain into the AAOS guest, rendered the complete
     * reducer-driven four-state arc in one uninterrupted take, preserved the
     * display-derived versus native decision-semantics separation in every
     * public frame, suppressed expired display-derived geometry fail-closed,
     * and rendered degraded dispositions under deterministic fixture
     * injection. The scenario-safety outcome remains deferred_not_proven:
     * this claim is about the instrumentation, never about AEBS safety.
     */
    subject claimSubject : VisualizationVerificationBench;
    require constraint {
      doc /*
       * The claim requires retained EVID-AEBS-S2-001 through EVID-AEBS-S2-006
       * evidence bound to the configured test article, exact wire contract,
       * execution environment, and independent observer identities. It
       * excludes restoration behavior, live degradation beyond the retained
       * take, inter-VM transport without the bounded bench route, signed-
       * policy enforcement, post-release re-approach, safety, certification,
       * homologation, and production-readiness claims.
       */
    }
  }

  requirement chainCorrelationArgument : VisualizationArgument {
    doc /* AGT-AEBS-S2-01: argues AC-AEBS-S2-001 (source-to-screen correlation with zero gaps) within the claim boundary. */
    subject bench : VisualizationVerificationBench;
  }

  requirement lifecycleArcArgument : VisualizationArgument {
    doc /* AGT-AEBS-S2-02: argues AC-AEBS-S2-002 (one-take four-state arc with verified stop) within the claim boundary. */
    subject bench : VisualizationVerificationBench;
  }

  requirement readOnlyBoundaryArgument : VisualizationArgument {
    doc /* AGT-AEBS-S2-03: argues AC-AEBS-S2-003 (read-only, no vehicle command) within the claim boundary. */
    subject bench : VisualizationVerificationBench;
  }

  requirement provenanceSeparationArgument : VisualizationArgument {
    doc /* AGT-AEBS-S2-04: argues AC-AEBS-S2-004 (display-derived versus native separation) within the claim boundary. */
    subject bench : VisualizationVerificationBench;
  }

  requirement failClosedStalenessArgument : VisualizationArgument {
    doc /* AGT-AEBS-S2-05: argues AC-AEBS-S2-005 (fail-closed suppression of expired geometry) within the claim boundary. */
    subject bench : VisualizationVerificationBench;
  }

  requirement degradedRenderingArgument : VisualizationArgument {
    doc /* AGT-AEBS-S2-06: argues AC-AEBS-S2-006 bounded to the fixture path; live-chain degradation is not argued by this branch. */
    subject bench : VisualizationVerificationBench;
  }

  requirement counterClaimRestoration : VisualizationCounterClaim {
    doc /* CCM-AEBS-S2-01: bounds the claim for restoration behavior (AC-AEBS-S2-007); no retained campaign exercised it. */
    subject bench : VisualizationVerificationBench;
  }

  requirement counterClaimLiveDegradation : VisualizationCounterClaim {
    doc /* CCM-AEBS-S2-02: bounds the claim for live degraded dispositions (stale/unavailable/invalid) from real Autoware source conditions; retained degraded-state evidence is fixture-path only. */
    subject bench : VisualizationVerificationBench;
  }

  requirement counterClaimProductionBoundaries : VisualizationCounterClaim {
    doc /* CCM-AEBS-S2-03: bounds the claim against inter-VM transport without the bounded adb-reverse bench route, signed-policy enforcement, production HMI, and any safety or certification reading. */
    subject bench : VisualizationVerificationBench;
  }

  requirement counterClaimUnidentifiedBuild : VisualizationCounterClaim {
    doc /* CCM-AEBS-S2-04: bounds the claim to observations on builds that are not exactly identified (GAP-AEBS-010-009); it verifies nothing on the configured test article until the evidence is re-captured from an exact clean commit. */
    subject bench : VisualizationVerificationBench;
  }

  dependency claimSupportedByChainArgument
    from chainCorrelationArgument to visualizationInstrumentationClaim;
  dependency claimSupportedByLifecycleArgument
    from lifecycleArcArgument to visualizationInstrumentationClaim;
  dependency claimSupportedByReadOnlyArgument
    from readOnlyBoundaryArgument to visualizationInstrumentationClaim;
  dependency claimSupportedByProvenanceArgument
    from provenanceSeparationArgument to visualizationInstrumentationClaim;
  dependency claimSupportedByStalenessArgument
    from failClosedStalenessArgument to visualizationInstrumentationClaim;
  dependency claimSupportedByDegradedArgument
    from degradedRenderingArgument to visualizationInstrumentationClaim;

  dependency chainVerificationReinforcesArgument
    from chainCorrelationVerification to chainCorrelationArgument;
  dependency lifecycleVerificationReinforcesArgument
    from lifecycleArcVerification to lifecycleArcArgument;
  dependency readOnlyVerificationReinforcesArgument
    from readOnlyBoundaryVerification to readOnlyBoundaryArgument;
  dependency provenanceVerificationReinforcesArgument
    from provenanceSeparationVerification to provenanceSeparationArgument;
  dependency stalenessVerificationReinforcesArgument
    from failClosedStalenessVerification to failClosedStalenessArgument;
  dependency degradedVerificationReinforcesArgument
    from degradedRenderingVerification to degradedRenderingArgument;

  dependency chainEvidenceReinforcesChainArgument
    from liveChainEvidence to chainCorrelationArgument;
  dependency lifecycleEvidenceReinforcesLifecycleArgument
    from lifecycleArcEvidence to lifecycleArcArgument;
  dependency readOnlyEvidenceReinforcesReadOnlyArgument
    from readOnlyBoundaryEvidence to readOnlyBoundaryArgument;
  dependency provenanceEvidenceReinforcesProvenanceArgument
    from provenanceSeparationEvidence to provenanceSeparationArgument;
  dependency stalenessEvidenceReinforcesStalenessArgument
    from failClosedStalenessEvidence to failClosedStalenessArgument;
  dependency degradedEvidenceReinforcesDegradedArgument
    from degradedRenderingEvidence to degradedRenderingArgument;

  dependency chainEvidenceTraceToClaim
    from liveChainEvidence to visualizationInstrumentationClaim;
  dependency lifecycleEvidenceTraceToClaim
    from lifecycleArcEvidence to visualizationInstrumentationClaim;
  dependency readOnlyEvidenceTraceToClaim
    from readOnlyBoundaryEvidence to visualizationInstrumentationClaim;
  dependency provenanceEvidenceTraceToClaim
    from provenanceSeparationEvidence to visualizationInstrumentationClaim;
  dependency stalenessEvidenceTraceToClaim
    from failClosedStalenessEvidence to visualizationInstrumentationClaim;
  dependency degradedEvidenceTraceToClaim
    from degradedRenderingEvidence to visualizationInstrumentationClaim;

  dependency counterClaimRestorationCountersClaim
    from counterClaimRestoration to visualizationInstrumentationClaim;
  dependency counterClaimLiveDegradationCountersClaim
    from counterClaimLiveDegradation to visualizationInstrumentationClaim;
  dependency counterClaimProductionCountersClaim
    from counterClaimProductionBoundaries to visualizationInstrumentationClaim;
  dependency counterClaimUnidentifiedBuildCountersClaim
    from counterClaimUnidentifiedBuild to visualizationInstrumentationClaim;

  /* ──────────────────────────────────────────
   * Gaps (deferred scope owned by this slice's successors)
   * ────────────────────────────────────────── */

  part gap010RestorationUnexercised : IncrementGap {
    doc /*
     * GAP-AEBS-010-006: Restoration after a failure disposition
     * (AC-AEBS-S2-007) was not exercised in any retained INC-AEBS-010
     * campaign; the deterministic PF-004 publisher can exercise it without
     * live bench time. Owner: successor increment in this chain.
     */
  }
  part gap010LiveDegradationUnproven : IncrementGap {
    doc /*
     * GAP-AEBS-010-007: Degraded dispositions from real Autoware source
     * conditions (stale/unavailable/invalid on the live chain) are not
     * observed in retained evidence; the retained degraded-state campaign is
     * fixture-path only. REQ-AEBS-S2-006 (no-valid-frame timeout) and
     * REQ-AEBS-S2-008 (invalid-frame rejection) are therefore not verified by
     * any case of this slice. Owner: successor increment in this chain.
     */
  }
  part gap010InterVmRouteDeferred : DeferredProductLineScope {
    doc /*
     * GAP-AEBS-010-008: The retained route is the bounded bench transport
     * (TCP :4721 + adb reverse). An inter-VM route without the adb-reverse
     * shortcut and a signed-policy enforcement path (SELinux stays permissive
     * on the bench guest) remain deferred; production must enforce policy.
     * Owner: successor increment in this chain.
     */
  }
  part gapRetainedTakeBuildUnidentified : IncrementGap {
    doc /*
     * GAP-AEBS-010-009: The retained v21 take (final-hmi-v21-corrected), the
     * source of EVID-AEBS-S2-001..005, was captured from HEAD 4d8dc1b plus 17
     * uncommitted files. It is identified only by sha256 prefixes of six
     * corrected sources (revision-checksums.md), so its tested build is not
     * exactly identified. The fixture-path state campaign (EVID-AEBS-S2-006)
     * records no build identity at all. These records are therefore
     * observations on unidentified builds of AEBS-CONFIG-010-001, not
     * verification of the configured test article. Re-capture from an exact
     * clean commit is planned separately. Owner: successor increment in this
     * chain.
     */
  }

  dependency counterClaimRestorationGapTrace
    from counterClaimRestoration to gap010RestorationUnexercised;
  dependency counterClaimLiveDegradationGapTrace
    from counterClaimLiveDegradation to gap010LiveDegradationUnproven;
  dependency counterClaimProductionGapTrace
    from counterClaimProductionBoundaries to gap010InterVmRouteDeferred;
  dependency plannedRestorationEvidenceGapTrace
    from restorationEvidencePlanned to gap010RestorationUnexercised;
  dependency counterClaimUnidentifiedBuildGapTrace
    from counterClaimUnidentifiedBuild to gapRetainedTakeBuildUnidentified;
  dependency liveChainEvidenceBuildGapTrace
    from liveChainEvidence to gapRetainedTakeBuildUnidentified;
  dependency lifecycleArcEvidenceBuildGapTrace
    from lifecycleArcEvidence to gapRetainedTakeBuildUnidentified;
  dependency readOnlyBoundaryEvidenceBuildGapTrace
    from readOnlyBoundaryEvidence to gapRetainedTakeBuildUnidentified;
  dependency provenanceSeparationEvidenceBuildGapTrace
    from provenanceSeparationEvidence to gapRetainedTakeBuildUnidentified;
  dependency failClosedStalenessEvidenceBuildGapTrace
    from failClosedStalenessEvidence to gapRetainedTakeBuildUnidentified;
  dependency degradedRenderingEvidenceBuildGapTrace
    from degradedRenderingEvidence to gapRetainedTakeBuildUnidentified;

  /* Safety non-claim anchor: the scenario-safety outcome stays deferred. */
  part scenarioSafetyDeferred : DeferredProductLineScope {
    doc /*
     * The visualization observes AEBS behavior; it contributes no braking
     * authority, hazard control, or safety argument. The scenario-safety
     * outcome remains deferred_not_proven by design of this instrumentation.
     */
  }
  dependency readOnlyArgumentSafetyNonClaimTrace
    from readOnlyBoundaryArgument to scenarioSafetyDeferred;

  /* ──────────────────────────────────────────
   * Concern and views (ArgumentationAssurance for evidence claims)
   * ────────────────────────────────────────── */

  concern visualizationArgumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claim, counterclaims, retained evidence, and gaps for the visualization instrumentation. */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsVisualizationVerificationAssuranceView {
    viewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame visualizationArgumentationAssuranceConcern;
    }
    doc /*
     * Positive Phase 10 slice: the bounded instrumentation claim, its
     * supporting arguments, and the retained evidence branches.
     */
    expose visualizationInstrumentationClaim;
    expose chainCorrelationArgument;
    expose lifecycleArcArgument;
    expose readOnlyBoundaryArgument;
    expose provenanceSeparationArgument;
    expose failClosedStalenessArgument;
    expose degradedRenderingArgument;
    expose liveChainEvidence;
    expose lifecycleArcEvidence;
    expose readOnlyBoundaryEvidence;
    expose provenanceSeparationEvidence;
    expose failClosedStalenessEvidence;
    expose degradedRenderingEvidence;
    expose claimSupportedByChainArgument;
    expose claimSupportedByLifecycleArgument;
    expose claimSupportedByReadOnlyArgument;
    expose claimSupportedByProvenanceArgument;
    expose claimSupportedByStalenessArgument;
    expose claimSupportedByDegradedArgument;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }

  view aebsVisualizationOpenCounterclaimAssuranceView {
    viewpoint selectedOpenCounterclaimViewpoint : ArgumentationAssuranceViewpoint {
      frame visualizationArgumentationAssuranceConcern;
    }
    doc /*
     * Challenge slice: unresolved counterclaims and gaps that prevent
     * broader restoration, live-degradation, inter-VM, and safety assurance,
     * and verification on an exactly identified build.
     */
    expose visualizationInstrumentationClaim;
    expose counterClaimRestoration;
    expose counterClaimLiveDegradation;
    expose counterClaimProductionBoundaries;
    expose counterClaimUnidentifiedBuild;
    expose gap010RestorationUnexercised;
    expose gap010LiveDegradationUnproven;
    expose gap010InterVmRouteDeferred;
    expose gapRetainedTakeBuildUnidentified;
    expose counterClaimRestorationGapTrace;
    expose counterClaimLiveDegradationGapTrace;
    expose counterClaimProductionGapTrace;
    expose counterClaimUnidentifiedBuildGapTrace;
    expose restorationEvidencePlanned;
    expose scenarioSafetyDeferred;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
