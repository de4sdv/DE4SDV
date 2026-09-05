/*
 * DE4SDV INC-AEBS-010 Phase 10 verification and evidence model slice.
 *
 * This slice is the Phase 10 V&V portion of the INC-AEBS-010 visualization
 * chain. It defines the verification cases, acceptance criteria, retained
 * evidence records, bounded assurance claim, deferred counterclaims, and
 * claim-boundary semantics for the System 2 read-only AEBS forward-situation
 * visualization test system.
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
   * identity; verificationSystemS2 below carries the slice's trace.
   */
  reference incAEBS010 : VisualizationIncrement;

  /* ──────────────────────────────────────────
   * Evidence vocabulary and observation records
   * ────────────────────────────────────────── */

  enum def VisualizationScenarioS2 {
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
    partial;
    blocked;
    notClaimed;
  }

  item def VisualizationObservationS2 {
    attribute callbackCount : ScalarValues::Integer;
    attribute sequenceSpan : ScalarValues::String;
    attribute observedRateHz : ScalarValues::Real;
    attribute gapCount : ScalarValues::Integer;
    attribute independentCapture : Boolean;
  }

  item def RetainedVisualizationEvidenceS2 {
    attribute configurationIdentity : ScalarValues::String;
    attribute executionEnvironmentIdentity : ScalarValues::String;
    attribute contractIdentity : ScalarValues::String;
    attribute rawObservationArtifact : ScalarValues::String;
    attribute independentObserverIdentity : ScalarValues::String;
    attribute disposition : VisualizationEvidenceDisposition;
    attribute claimBoundary : ScalarValues::String;
  }

  item def ReplayedVisualizationEvaluationS2 {
    attribute scenario : VisualizationScenarioS2;
    attribute outcome : VisualizationEvidenceDisposition;
    attribute acceptanceSummary : ScalarValues::String;
  }

  /*
   * Verdict mapping: only observedBounded evidence produces pass. partial
   * maps to inconclusive — a partial observation cannot upgrade into an
   * acceptance claim without a separately justified bounded-pass
   * interpretation (none exists for the retained campaign).
   */
  calc def MapS2OutcomeToVerdict {
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

  part def VisualizationVandVBenchS2 {
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
    /* System 2 subject: instrumented visualization test article. */
    part system2TestArticle : AEBSAutowareAAOSSDVVisualizationTestArticle;
    part system2Instrument : System2EngineeringAndAssuranceSystem;
    attribute scenario : VisualizationScenarioS2;
  }

  part liveChainCorrelationBenchS2 : VisualizationVandVBenchS2 {
    attribute :>> scenario = VisualizationScenarioS2::liveChainCorrelation;
  }
  part lifecycleArcBenchS2 : VisualizationVandVBenchS2 {
    attribute :>> scenario = VisualizationScenarioS2::lifecycleArc;
  }
  part readOnlyBoundaryBenchS2 : VisualizationVandVBenchS2 {
    attribute :>> scenario = VisualizationScenarioS2::readOnlyBoundary;
  }
  part provenanceSeparationBenchS2 : VisualizationVandVBenchS2 {
    attribute :>> scenario = VisualizationScenarioS2::provenanceSeparation;
  }
  part failClosedStalenessBenchS2 : VisualizationVandVBenchS2 {
    attribute :>> scenario = VisualizationScenarioS2::failClosedStaleness;
  }
  part degradedStateRenderingBenchS2 : VisualizationVandVBenchS2 {
    attribute :>> scenario = VisualizationScenarioS2::degradedStateRendering;
  }
  part restorationBehaviorBenchS2 : VisualizationVandVBenchS2 {
    attribute :>> scenario = VisualizationScenarioS2::restorationBehavior;
  }

  /* ──────────────────────────────────────────
   * Acceptance criteria (System 2 evidence contracts)
   * ────────────────────────────────────────── */

  requirement def VisualizationAcceptanceCriterionS2
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement acceptanceCriterionS2ChainCorrelation : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-001; bounded verification of source-to-screen correlation. */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* The visualization test system shall retain source, transport, ingress, and guest identity, sequence, timestamp, log, and guest-native capture records for each rendered state so that each rendered state can be correlated with its observed source event, with consecutive accepted callbacks and zero sequence gaps over the retained take. */ }
  }

  requirement acceptanceCriterionS2LifecycleArc : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-002; bounded verification of the four-state arc in one take. */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* The visualization test system shall present the reducer-driven MONITORING, WARNING, INTERVENTION, and RELEASED dispositions from accepted frames of one uninterrupted real-time take, with the release disposition accompanied by a verified zero-speed stop observation and no edited or older-generation footage presented as part of the take. */ }
  }

  requirement acceptanceCriterionS2ReadOnlyBoundary : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-003; read-only boundary verification. */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* The visualization test system shall publish nothing to the vehicle runtime and shall issue no vehicle command, and the public interface shall state the read-only engineering-visualization boundary in every rendered session. */ }
  }

  requirement acceptanceCriterionS2ProvenanceSeparation : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-004; display-derived versus native decision semantics separation. */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* The visualization test system shall render obstacle geometry only from the display-derived filtered point cloud, shall not present coordinator-derived distance values or any display-derived scalar as a native Autoware decision metric, and shall state in the public interface that AEB decision distances are not visualized. */ }
  }

  requirement acceptanceCriterionS2FailClosedStaleness : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-005; fail-closed staleness verification. */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* When the filtered obstacle-cloud source stops updating, the visualization test system shall suppress the expired display-derived obstacle geometry while accepted live frames continue, and no interpolation, smoothing, or prediction shall substitute for missing fresh data. */ }
  }

  requirement acceptanceCriterionS2DegradedRendering : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-006; degraded-state rendering verification (fixture path). */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* Under deterministic closed-loop frame injection, the visualization test system shall render the stale, unavailable, and invalid degraded dispositions with live geometry cleared and the health chip identifying the degraded condition, with color never the sole state cue. */ }
  }

  requirement acceptanceCriterionS2Restoration : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-007; restoration behavior criterion (planned). */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* After a failure disposition, the visualization test system shall present a bounded restored indication after the selected consecutive-valid-frame criterion is met, without application restart. */ }
  }

  requirement acceptanceCriterionS2EvidenceIntegrity : VisualizationAcceptanceCriterionS2 {
    doc /* AC-AEBS-S2-008; evidence integrity and claim-boundary criterion. */
    subject bench : VisualizationVandVBenchS2;
    require constraint statement { language "English" /* Every retained verdict shall bind the configured test article, execution environment, wire contract, raw observation artifacts, and independent observer identities, and missing evidence shall be recorded as planned, partial, blocked, or not claimed, never as an observed runtime pass. */ }
  }

  /* ──────────────────────────────────────────
   * Retained evidence records (exact artifacts in the implementation bench)
   * ────────────────────────────────────────── */

  part liveChainEvidenceS2 : RetainedVisualizationEvidenceS2 {
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
    attribute :>> disposition = VisualizationEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Live observation-chain evidence on the bench deployment; not safety, braking-authority, certification, or production evidence.";
  }

  part lifecycleArcEvidenceS2 : RetainedVisualizationEvidenceS2 {
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
    attribute :>> disposition = VisualizationEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "One continuous take of the corrected generation; title/end cards are editing frames; not safety or certification evidence.";
  }

  part readOnlyBoundaryEvidenceS2 : RetainedVisualizationEvidenceS2 {
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
    attribute :>> disposition = VisualizationEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Structural and rendered-session read-only evidence; no vehicle-interaction behavior is exercised or claimed.";
  }

  part provenanceSeparationEvidenceS2 : RetainedVisualizationEvidenceS2 {
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
    attribute :>> disposition = VisualizationEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Presentation-separation evidence for the corrected generation; not a claim about native Autoware AEB decision internals.";
  }

  part failClosedStalenessEvidenceS2 : RetainedVisualizationEvidenceS2 {
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
    attribute :>> disposition = VisualizationEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Bounded staleness observation within one take; not a certification-grade freshness argument.";
  }

  part degradedRenderingEvidenceS2 : RetainedVisualizationEvidenceS2 {
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
    attribute :>> disposition = VisualizationEvidenceDisposition::observedBounded;
    attribute :>> claimBoundary = "Fixture-path rendering evidence only; not live Autoware degradation evidence.";
  }

  part restorationEvidencePlannedS2 : PlannedExecutionEnvironmentEvidence {
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

  verification def VisualizationChainCorrelationVerificationS2 {
    subject verifiedBench : VisualizationVandVBenchS2;
    objective chainCorrelationObjectiveS2 {
      verify acceptanceCriterionS2ChainCorrelation;
      verify acceptanceCriterionS2EvidenceIntegrity;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidenceS2;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenarioS2 = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidenceS2 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluationS2;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluationS2 = processData.replayedEvaluation;
      out verdict : VerdictKind = MapS2OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationLifecycleArcVerificationS2 {
    subject verifiedBench : VisualizationVandVBenchS2;
    objective lifecycleArcObjectiveS2 {
      verify acceptanceCriterionS2LifecycleArc;
      verify acceptanceCriterionS2EvidenceIntegrity;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidenceS2;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenarioS2 = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidenceS2 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluationS2;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluationS2 = processData.replayedEvaluation;
      out verdict : VerdictKind = MapS2OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationReadOnlyBoundaryVerificationS2 {
    subject verifiedBench : VisualizationVandVBenchS2;
    objective readOnlyBoundaryObjectiveS2 {
      verify acceptanceCriterionS2ReadOnlyBoundary;
      verify acceptanceCriterionS2EvidenceIntegrity;
    }
    action collectData {
      @VerificationMethod{ kind = (inspect, test); }
      out item retainedEvidence : RetainedVisualizationEvidenceS2;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenarioS2 = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidenceS2 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluationS2;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluationS2 = processData.replayedEvaluation;
      out verdict : VerdictKind = MapS2OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationProvenanceSeparationVerificationS2 {
    subject verifiedBench : VisualizationVandVBenchS2;
    objective provenanceSeparationObjectiveS2 {
      verify acceptanceCriterionS2ProvenanceSeparation;
      verify acceptanceCriterionS2EvidenceIntegrity;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidenceS2;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenarioS2 = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidenceS2 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluationS2;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluationS2 = processData.replayedEvaluation;
      out verdict : VerdictKind = MapS2OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationFailClosedStalenessVerificationS2 {
    subject verifiedBench : VisualizationVandVBenchS2;
    objective failClosedStalenessObjectiveS2 {
      verify acceptanceCriterionS2FailClosedStaleness;
      verify acceptanceCriterionS2EvidenceIntegrity;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidenceS2;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenarioS2 = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidenceS2 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluationS2;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluationS2 = processData.replayedEvaluation;
      out verdict : VerdictKind = MapS2OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationDegradedRenderingVerificationS2 {
    doc /*
     * Fixture-path verification case. Its subject scenario uses the PF-004
     * deterministic publisher; any verdict from it is bounded to that path
     * and does not transfer to the live Autoware chain.
     */
    subject verifiedBench : VisualizationVandVBenchS2;
    objective degradedRenderingObjectiveS2 {
      verify acceptanceCriterionS2DegradedRendering;
      verify acceptanceCriterionS2EvidenceIntegrity;
    }
    action collectData {
      @VerificationMethod{ kind = (test, inspect); }
      out item retainedEvidence : RetainedVisualizationEvidenceS2;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenarioS2 = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidenceS2 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluationS2;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluationS2 = processData.replayedEvaluation;
      out verdict : VerdictKind = MapS2OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  verification def VisualizationRestorationVerificationS2 {
    doc /*
     * Planned verification case. No retained campaign exercised restoration;
     * the case exists to bind the criterion and the gap, and its verdict
     * remains inconclusive until evidence is retained by a later campaign.
     */
    subject verifiedBench : VisualizationVandVBenchS2;
    objective restorationObjectiveS2 {
      verify acceptanceCriterionS2Restoration;
      verify acceptanceCriterionS2EvidenceIntegrity;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedEvidence : RetainedVisualizationEvidenceS2;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : VisualizationScenarioS2 = verifiedBench.scenario;
      in item retainedEvidence : RetainedVisualizationEvidenceS2 = collectData.retainedEvidence;
      out item replayedEvaluation : ReplayedVisualizationEvaluationS2;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : ReplayedVisualizationEvaluationS2 = processData.replayedEvaluation;
      out verdict : VerdictKind = MapS2OutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }

  doc /* VC-AEBS-S2-001 verification case usage. */
  verification chainCorrelationVerificationS2 : VisualizationChainCorrelationVerificationS2 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> liveChainCorrelationBenchS2;
  }

  doc /* VC-AEBS-S2-002 verification case usage. */
  verification lifecycleArcVerificationS2 : VisualizationLifecycleArcVerificationS2 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> lifecycleArcBenchS2;
  }

  doc /* VC-AEBS-S2-003 verification case usage. */
  verification readOnlyBoundaryVerificationS2 : VisualizationReadOnlyBoundaryVerificationS2 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> readOnlyBoundaryBenchS2;
  }

  doc /* VC-AEBS-S2-004 verification case usage. */
  verification provenanceSeparationVerificationS2 : VisualizationProvenanceSeparationVerificationS2 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> provenanceSeparationBenchS2;
  }

  doc /* VC-AEBS-S2-005 verification case usage. */
  verification failClosedStalenessVerificationS2 : VisualizationFailClosedStalenessVerificationS2 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> failClosedStalenessBenchS2;
  }

  doc /* VC-AEBS-S2-006 verification case usage. */
  verification degradedRenderingVerificationS2 : VisualizationDegradedRenderingVerificationS2 {
    @VerificationMethod{ kind = (test, inspect, analyze); }
    subject verifiedBench :> degradedStateRenderingBenchS2;
  }

  doc /* VC-AEBS-S2-007 verification case usage. */
  verification restorationVerificationS2 : VisualizationRestorationVerificationS2 {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> restorationBehaviorBenchS2;
  }

  part verificationSystemS2 {
    perform chainCorrelationVerificationS2;
    perform lifecycleArcVerificationS2;
    perform readOnlyBoundaryVerificationS2;
    perform provenanceSeparationVerificationS2;
    perform failClosedStalenessVerificationS2;
    perform degradedRenderingVerificationS2;
    perform restorationVerificationS2;
  }

  /* ──────────────────────────────────────────
   * Requirement derivation dependencies (System 2 candidates only)
   * ────────────────────────────────────────── */

  dependency chainCorrelationToEvidenceRequirement
    from acceptanceCriterionS2ChainCorrelation
    to reqEvidenceCorrelation;
  dependency chainCorrelationToRealAAOSRenderingRequirement
    from acceptanceCriterionS2LifecycleArc
    to reqRealAAOSRendering;
  dependency readOnlyBoundaryToNonInterferenceRequirement
    from acceptanceCriterionS2ReadOnlyBoundary
    to reqNonInterference;
  dependency provenanceSeparationToNoImpersonationRequirement
    from acceptanceCriterionS2ProvenanceSeparation
    to reqNoNativeImpersonation;
  dependency failClosedStalenessToFreshnessRequirement
    from acceptanceCriterionS2FailClosedStaleness
    to reqFailClosedFreshness;
  dependency degradedRenderingToAvailabilityRequirement
    from acceptanceCriterionS2DegradedRendering
    to reqAvailabilityDisposition;
  dependency restorationToRestorationRequirement
    from acceptanceCriterionS2Restoration
    to reqRestorationBehavior;

  /* Cross-increment traceability to the accepted chain baseline. */
  dependency verificationTestArticleTrace
    from verificationSystemS2
    to testArticle;
  dependency verificationPhysicalSystemTrace
    from verificationSystemS2
    to physicalSystem;
  dependency chainEvidenceToPhysicalSystemTrace
    from liveChainEvidenceS2
    to physicalSystem;
  dependency lifecycleEvidenceToPhysicalSystemTrace
    from lifecycleArcEvidenceS2
    to physicalSystem::iviGuest::displayApp;
  dependency provenanceEvidenceToSourceProvenanceTrace
    from provenanceSeparationEvidenceS2
    to coordinatorStateProvenance;

  /* ──────────────────────────────────────────
   * Claim-argument-evidence layer (INC-AEBS-010 Phase 10)
   * ────────────────────────────────────────── */

  requirement def VisualizationClaimS2
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement def VisualizationArgumentS2
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement def VisualizationCounterClaimS2
    :> EvidenceContractTraceabilityRequirementCandidate;

  requirement s2VisualizationInstrumentationClaim : VisualizationClaimS2 {
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
    subject claimSubject : VisualizationVandVBenchS2;
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

  requirement chainCorrelationArgumentS2 : VisualizationArgumentS2 {
    doc /* AGT-AEBS-S2-01: argues AC-AEBS-S2-001 (source-to-screen correlation with zero gaps) within the claim boundary. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement lifecycleArcArgumentS2 : VisualizationArgumentS2 {
    doc /* AGT-AEBS-S2-02: argues AC-AEBS-S2-002 (one-take four-state arc with verified stop) within the claim boundary. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement readOnlyBoundaryArgumentS2 : VisualizationArgumentS2 {
    doc /* AGT-AEBS-S2-03: argues AC-AEBS-S2-003 (read-only, no vehicle command) within the claim boundary. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement provenanceSeparationArgumentS2 : VisualizationArgumentS2 {
    doc /* AGT-AEBS-S2-04: argues AC-AEBS-S2-004 (display-derived versus native separation) within the claim boundary. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement failClosedStalenessArgumentS2 : VisualizationArgumentS2 {
    doc /* AGT-AEBS-S2-05: argues AC-AEBS-S2-005 (fail-closed suppression of expired geometry) within the claim boundary. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement degradedRenderingArgumentS2 : VisualizationArgumentS2 {
    doc /* AGT-AEBS-S2-06: argues AC-AEBS-S2-006 bounded to the fixture path; live-chain degradation is not argued by this branch. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement counterClaimS2Restoration : VisualizationCounterClaimS2 {
    doc /* CCM-AEBS-S2-01: bounds the claim for restoration behavior (AC-AEBS-S2-007); no retained campaign exercised it. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement counterClaimS2LiveDegradation : VisualizationCounterClaimS2 {
    doc /* CCM-AEBS-S2-02: bounds the claim for live degraded dispositions (stale/unavailable/invalid) from real Autoware source conditions; retained degraded-state evidence is fixture-path only. */
    subject bench : VisualizationVandVBenchS2;
  }

  requirement counterClaimS2ProductionBoundaries : VisualizationCounterClaimS2 {
    doc /* CCM-AEBS-S2-03: bounds the claim against inter-VM transport without the bounded adb-reverse bench route, signed-policy enforcement, production HMI, and any safety or certification reading. */
    subject bench : VisualizationVandVBenchS2;
  }

  dependency claimSupportedByChainArgument
    from chainCorrelationArgumentS2 to s2VisualizationInstrumentationClaim;
  dependency claimSupportedByLifecycleArgument
    from lifecycleArcArgumentS2 to s2VisualizationInstrumentationClaim;
  dependency claimSupportedByReadOnlyArgument
    from readOnlyBoundaryArgumentS2 to s2VisualizationInstrumentationClaim;
  dependency claimSupportedByProvenanceArgument
    from provenanceSeparationArgumentS2 to s2VisualizationInstrumentationClaim;
  dependency claimSupportedByStalenessArgument
    from failClosedStalenessArgumentS2 to s2VisualizationInstrumentationClaim;
  dependency claimSupportedByDegradedArgument
    from degradedRenderingArgumentS2 to s2VisualizationInstrumentationClaim;

  dependency chainVerificationReinforcesArgument
    from chainCorrelationVerificationS2 to chainCorrelationArgumentS2;
  dependency lifecycleVerificationReinforcesArgument
    from lifecycleArcVerificationS2 to lifecycleArcArgumentS2;
  dependency readOnlyVerificationReinforcesArgument
    from readOnlyBoundaryVerificationS2 to readOnlyBoundaryArgumentS2;
  dependency provenanceVerificationReinforcesArgument
    from provenanceSeparationVerificationS2 to provenanceSeparationArgumentS2;
  dependency stalenessVerificationReinforcesArgument
    from failClosedStalenessVerificationS2 to failClosedStalenessArgumentS2;
  dependency degradedVerificationReinforcesArgument
    from degradedRenderingVerificationS2 to degradedRenderingArgumentS2;

  dependency chainEvidenceReinforcesChainArgument
    from liveChainEvidenceS2 to chainCorrelationArgumentS2;
  dependency lifecycleEvidenceReinforcesLifecycleArgument
    from lifecycleArcEvidenceS2 to lifecycleArcArgumentS2;
  dependency readOnlyEvidenceReinforcesReadOnlyArgument
    from readOnlyBoundaryEvidenceS2 to readOnlyBoundaryArgumentS2;
  dependency provenanceEvidenceReinforcesProvenanceArgument
    from provenanceSeparationEvidenceS2 to provenanceSeparationArgumentS2;
  dependency stalenessEvidenceReinforcesStalenessArgument
    from failClosedStalenessEvidenceS2 to failClosedStalenessArgumentS2;
  dependency degradedEvidenceReinforcesDegradedArgument
    from degradedRenderingEvidenceS2 to degradedRenderingArgumentS2;

  dependency chainEvidenceTraceToClaim
    from liveChainEvidenceS2 to s2VisualizationInstrumentationClaim;
  dependency lifecycleEvidenceTraceToClaim
    from lifecycleArcEvidenceS2 to s2VisualizationInstrumentationClaim;
  dependency readOnlyEvidenceTraceToClaim
    from readOnlyBoundaryEvidenceS2 to s2VisualizationInstrumentationClaim;
  dependency provenanceEvidenceTraceToClaim
    from provenanceSeparationEvidenceS2 to s2VisualizationInstrumentationClaim;
  dependency stalenessEvidenceTraceToClaim
    from failClosedStalenessEvidenceS2 to s2VisualizationInstrumentationClaim;
  dependency degradedEvidenceTraceToClaim
    from degradedRenderingEvidenceS2 to s2VisualizationInstrumentationClaim;

  dependency counterClaimRestorationCountersClaim
    from counterClaimS2Restoration to s2VisualizationInstrumentationClaim;
  dependency counterClaimLiveDegradationCountersClaim
    from counterClaimS2LiveDegradation to s2VisualizationInstrumentationClaim;
  dependency counterClaimProductionCountersClaim
    from counterClaimS2ProductionBoundaries to s2VisualizationInstrumentationClaim;

  /* ──────────────────────────────────────────
   * Gaps (deferred scope owned by this slice's successors)
   * ────────────────────────────────────────── */

  part gap010RestorationUnexercisedS2 : IncrementGap {
    doc /*
     * GAP-AEBS-010-006: Restoration after a failure disposition
     * (AC-AEBS-S2-007) was not exercised in any retained INC-AEBS-010
     * campaign; the deterministic PF-004 publisher can exercise it without
     * live bench time. Owner: successor increment in this chain.
     */
  }
  part gap010LiveDegradationUnprovenS2 : IncrementGap {
    doc /*
     * GAP-AEBS-010-007: Degraded dispositions from real Autoware source
     * conditions (stale/unavailable/invalid on the live chain) are not
     * observed in retained evidence; the retained degraded-state campaign is
     * fixture-path only. Owner: successor increment in this chain.
     */
  }
  part gap010InterVmRouteDeferredS2 : DeferredProductLineScope {
    doc /*
     * GAP-AEBS-010-008: The retained route is the bounded bench transport
     * (TCP :4721 + adb reverse). An inter-VM route without the adb-reverse
     * shortcut and a signed-policy enforcement path (SELinux stays permissive
     * on the bench guest) remain deferred; production must enforce policy.
     * Owner: successor increment in this chain.
     */
  }

  dependency counterClaimRestorationGapTrace
    from counterClaimS2Restoration to gap010RestorationUnexercisedS2;
  dependency counterClaimLiveDegradationGapTrace
    from counterClaimS2LiveDegradation to gap010LiveDegradationUnprovenS2;
  dependency counterClaimProductionGapTrace
    from counterClaimS2ProductionBoundaries to gap010InterVmRouteDeferredS2;
  dependency plannedRestorationEvidenceGapTrace
    from restorationEvidencePlannedS2 to gap010RestorationUnexercisedS2;

  /* Safety non-claim anchor: the scenario-safety outcome stays deferred. */
  part scenarioSafetyDeferredS2 : DeferredProductLineScope {
    doc /*
     * The visualization observes AEBS behavior; it contributes no braking
     * authority, hazard control, or safety argument. The scenario-safety
     * outcome remains deferred_not_proven by design of this instrumentation.
     */
  }
  dependency readOnlyArgumentSafetyNonClaimTrace
    from readOnlyBoundaryArgumentS2 to scenarioSafetyDeferredS2;

  /* ──────────────────────────────────────────
   * Concern and views (ArgumentationAssurance for evidence claims)
   * ────────────────────────────────────────── */

  concern argumentationAssuranceConcernS2 : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claim, counterclaims, retained evidence, and gaps for the visualization instrumentation. */
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder verificationEngineer : VerificationEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  view aebsVisualizationVerificationAssuranceView {
    viewpoint selectedAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcernS2;
    }
    doc /*
     * Positive Phase 10 slice: the bounded instrumentation claim, its
     * supporting arguments, and the retained evidence branches.
     */
    expose s2VisualizationInstrumentationClaim;
    expose chainCorrelationArgumentS2;
    expose lifecycleArcArgumentS2;
    expose readOnlyBoundaryArgumentS2;
    expose provenanceSeparationArgumentS2;
    expose failClosedStalenessArgumentS2;
    expose degradedRenderingArgumentS2;
    expose liveChainEvidenceS2;
    expose lifecycleArcEvidenceS2;
    expose readOnlyBoundaryEvidenceS2;
    expose provenanceSeparationEvidenceS2;
    expose failClosedStalenessEvidenceS2;
    expose degradedRenderingEvidenceS2;
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
      frame argumentationAssuranceConcernS2;
    }
    doc /*
     * Challenge slice: unresolved counterclaims and gaps that prevent
     * broader restoration, live-degradation, inter-VM, and safety assurance.
     */
    expose s2VisualizationInstrumentationClaim;
    expose counterClaimS2Restoration;
    expose counterClaimS2LiveDegradation;
    expose counterClaimS2ProductionBoundaries;
    expose gap010RestorationUnexercisedS2;
    expose gap010LiveDegradationUnprovenS2;
    expose gap010InterVmRouteDeferredS2;
    expose counterClaimRestorationGapTrace;
    expose counterClaimLiveDegradationGapTrace;
    expose counterClaimProductionGapTrace;
    expose restorationEvidencePlannedS2;
    expose scenarioSafetyDeferredS2;
    attribute maxCompartmentEntries = 0;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
  }
}
