/* INC-AEBS-009D conscious-override matrix; planned System 2 executable contracts. */
package DE4SDV_AEBSOverrideVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;

  enum def OverrideScenarioIdentity {
    freshFalseControl;
    freshTrueOverride;
    staleOverride;
    missingOverride;
    malformedOverride;
    futureStampedOverride;
  }
  enum def OverrideEvidenceOutcome {
    passBoundedScenario;
    failObservedBehavior;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def OverrideObservationSet;
  item def OverrideEvaluation {
    attribute scenario : OverrideScenarioIdentity;
    attribute outcome : OverrideEvidenceOutcome;
  }
  calc def MapOverrideOutcomeToVerdict {
    in outcome : OverrideEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == OverrideEvidenceOutcome::passBoundedScenario? VerdictKind::pass
      else if outcome == OverrideEvidenceOutcome::failObservedBehavior? VerdictKind::fail
      else if outcome == OverrideEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def OverrideMatrixBench {
    attribute scenario : OverrideScenarioIdentity;
  }
  requirement def OverrideEvidenceContract;
  requirement <'EC-009D-01'>evidenceContractClosedOverrideScenario : OverrideEvidenceContract {
    subject bench : OverrideMatrixBench;
    require constraint statement { language "English" /* The bench shall bind exactly one closed override scenario identity. */ }
  }
  requirement <'EC-009D-02'>evidenceContractOverrideFreshnessReplay : OverrideEvidenceContract {
    subject bench : OverrideMatrixBench;
    require constraint statement { language "English" /* The bench shall replay source stamp, receipt time, value validity, exact diagnostic-source authorization, and the scenario-specific suppression, release, or degraded disposition. A fresh sample is one with source-stamp-to-receipt age at most 0.2 s; suppression is evaluated within a closed window of 0.25 s; runtime-graph sampling gaps above 0.2 s fail the replay. */ }
  }
  requirement <'EC-009D-03'>evidenceContractIndependentVerdict : OverrideEvidenceContract {
    subject bench : OverrideMatrixBench;
    require constraint statement { language "English" /* The bench shall retain separate observations, evaluation, provenance, and verdict for each scenario; observer failure shall not pass. */ }
  }

  part overrideFalseControlBench : OverrideMatrixBench {
    attribute :>> scenario = OverrideScenarioIdentity::freshFalseControl;
  }
  part overrideTrueBench : OverrideMatrixBench {
    attribute :>> scenario = OverrideScenarioIdentity::freshTrueOverride;
  }
  part overrideStaleBench : OverrideMatrixBench {
    attribute :>> scenario = OverrideScenarioIdentity::staleOverride;
  }
  part overrideMissingBench : OverrideMatrixBench {
    attribute :>> scenario = OverrideScenarioIdentity::missingOverride;
  }
  part overrideMalformedBench : OverrideMatrixBench {
    attribute :>> scenario = OverrideScenarioIdentity::malformedOverride;
  }
  part overrideFutureStampedBench : OverrideMatrixBench {
    attribute :>> scenario = OverrideScenarioIdentity::futureStampedOverride;
  }

  verification def <'VC-AEBS-009D-DE'>ConsciousOverrideVerification {
    subject verifiedBench : OverrideMatrixBench;
    objective evidenceObjective {
      verify evidenceContractClosedOverrideScenario;
      verify evidenceContractOverrideFreshnessReplay;
      verify evidenceContractIndependentVerdict;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : OverrideObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : OverrideScenarioIdentity = verifiedBench.scenario;
      in item retainedObservations : OverrideObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : OverrideEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : OverrideEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapOverrideOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification <'VC-AEBS-009D-01'>overrideFalseControlVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideFalseControlBench;
  }
  verification <'VC-AEBS-009D-02'>overrideTrueVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideTrueBench;
  }
  verification <'VC-AEBS-009D-03'>overrideStaleVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideStaleBench;
  }
  verification <'VC-AEBS-009D-04'>overrideMissingVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideMissingBench;
  }
  verification <'VC-AEBS-009D-05'>overrideMalformedVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideMalformedBench;
  }
  verification <'VC-AEBS-009D-06'>overrideFutureStampedVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideFutureStampedBench;
  }
  part verificationSystem {
    perform overrideFalseControlVerification;
    perform overrideTrueVerification;
    perform overrideStaleVerification;
    perform overrideMissingVerification;
    perform overrideMalformedVerification;
    perform overrideFutureStampedVerification;
  }

  dependency overrideEvidenceRelevantToOverrideCandidate
    from evidenceContractOverrideFreshnessReplay to reqAllowDriverOverride;

  /* ─────────────────────────────────────────────────────────────────
   * Lane B: model-resident evaluation scope for the INC-AEBS-009D
   * method-conformance pilot (ADR 0019; docs/method-conformance/).
   *
   * The scope binds the six declared verification usages by their stable
   * explicit identifiers. Contribution set and evaluation scope are
   * distinct: the usages are reused scope members (contributes = false);
   * the scope binding itself is the increment's contribution.
   * ───────────────────────────────────────────────────────────────── */
  private import ScalarValues::*;
  private import DE4SDV_MethodConformance::*;

  part def AebsOverridePilotScopeBase :> MethodEvaluationScope;

  part <'PSC-009D'>aebsOverridePilotScope : AebsOverridePilotScopeBase {
    attribute :>> incrementId = "INC-AEBS-009D";
    attribute :>> subjectType = "VerificationCaseUsage";
  }

  /* Evaluation-scope memberships: the six declared verification usages are
     reused scope members (contributes = false); the scope binding itself is
     the increment's contribution. Model-resident per Lane B-R5. */
  item scopeMember01 : EvaluationScopeMembership {
    attribute :>> scopeId = "PSC-009D";
    attribute :>> subjectId = "VC-AEBS-009D-01";
    attribute :>> contributes = false;
  }
  item scopeMember02 : EvaluationScopeMembership {
    attribute :>> scopeId = "PSC-009D";
    attribute :>> subjectId = "VC-AEBS-009D-02";
    attribute :>> contributes = false;
  }
  item scopeMember03 : EvaluationScopeMembership {
    attribute :>> scopeId = "PSC-009D";
    attribute :>> subjectId = "VC-AEBS-009D-03";
    attribute :>> contributes = false;
  }
  item scopeMember04 : EvaluationScopeMembership {
    attribute :>> scopeId = "PSC-009D";
    attribute :>> subjectId = "VC-AEBS-009D-04";
    attribute :>> contributes = false;
  }
  item scopeMember05 : EvaluationScopeMembership {
    attribute :>> scopeId = "PSC-009D";
    attribute :>> subjectId = "VC-AEBS-009D-05";
    attribute :>> contributes = false;
  }
  item scopeMember06 : EvaluationScopeMembership {
    attribute :>> scopeId = "PSC-009D";
    attribute :>> subjectId = "VC-AEBS-009D-06";
    attribute :>> contributes = false;
  }

  /* Accepted method-contract obligations (PC-009D-*), instantiated from the
     accepted A specification (docs/method-conformance/pilot-obligations.yaml
     + pilot-scope.md). Dependency edges are normative in the YAML twin and
     the pilot-scope dependency graph; they are contract data here, not
     applicability conditions. */
  item obligationScopePopulation : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-SCOPE-POPULATION";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "the declared pilot scope itself";
    attribute :>> applicability = "candidate revision declares the INC-AEBS-009D pilot scope";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "scope-composition";
    attribute :>> targetFilter = "element type VerificationCaseUsage";
    attribute :>> cardinalityMinimum = 6;
    attribute :>> cardinalityMaximum = 6;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "declared scope resolves to exactly the six pinned usages as distinct identities";
  }
  item obligationVcBinding : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-VC-BINDING";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each of the six declared usages (VerificationCaseUsage)";
    attribute :>> applicability = "candidate revision declares the INC-AEBS-009D pilot scope";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "binding-resolution";
    attribute :>> targetFilter = "API element";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each usage binds to exactly one API element by explicit identifier";
  }
  item obligationSubjectMembership : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-SUBJECT-MEMBERSHIP";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each of the six usages (VerificationCaseUsage)";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "verification-subject-membership";
    attribute :>> targetFilter = "member element type OverrideMatrixBench specialization";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each usage has exactly one OverrideMatrixBench-specialization subject member";
  }
  item obligationObjectiveContracts : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-OBJECTIVE-CONTRACTS";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each of the six usages (VerificationCaseUsage)";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "verifiedBy-reverse-witness";
    attribute :>> targetFilter = "the three pinned evidence-contract requirement usages";
    attribute :>> cardinalityMinimum = 3;
    attribute :>> cardinalityMaximum = 3;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each usage inherits the objective verify witnesses to EC-009D-01..03";
  }
  item obligationUsageMethodMetadata : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-USAGE-METHOD-METADATA";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each of the six usages (VerificationCaseUsage)";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "verification-method-metadata";
    attribute :>> targetFilter = "method-kind value set exactly {test, analyze}";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each usage carries @VerificationMethod{kind=(test, analyze)}";
  }
  item obligationDefinitionMethodMetadata : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-DEFINITION-METHOD-METADATA";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "the shared verification definition ConsciousOverrideVerification (VerificationCaseDefinition)";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "verification-method-metadata";
    attribute :>> targetFilter = "per-action kind: collectData test; processData analyze; evaluateData analyze";
    attribute :>> cardinalityMinimum = 3;
    attribute :>> cardinalityMaximum = 3;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedModelRecord;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "the definition's three actions carry the declared method kinds";
  }
  item obligationProfilePopulation : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-PROFILE-POPULATION";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "the declared tested scope";
    attribute :>> applicability = "candidate declares the INC-AEBS-009D tested-scope manifest";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "scope-composition";
    attribute :>> targetFilter = "profile identity equality (pinned set, exact)";
    attribute :>> cardinalityMinimum = 6;
    attribute :>> cardinalityMaximum = 6;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedRepositoryArtifact;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "the declared tested scope contains exactly the six pinned OverrideScenario identities";
  }
  item obligationExecutionRecord : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-EXECUTION-RECORD";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each profile in the declared tested scope";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "external-evidence-reference";
    attribute :>> targetFilter = "record integrity: sha256 of scenario-evidence.json matches the manifest entry";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedRepositoryArtifact;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "each profile has exactly one canonical record with manifest-verified digest";
  }
  item obligationExecutionOutcome : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-EXECUTION-OUTCOME";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each profile's canonical record";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "execution-outcome";
    attribute :>> targetFilter = "disposition from the pinned OverrideDisposition vocabulary; unknown literal = ERROR";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedRepositoryArtifact;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "record evaluation.passed == true with the pinned per-profile expected disposition";
  }
  item obligationScopeEquality : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-SCOPE-EQUALITY";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each profile's canonical record";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "conservative-scope-equality";
    attribute :>> targetFilter = "all pinned fields compared; no field may be skipped";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedRepositoryArtifact;
    attribute :>> attestationPolicyRef = "";
    attribute :>> claimBoundary = "pinned provenance fingerprint fields equal the candidate's declared tested-scope values";
  }
  item obligationAcceptanceAuthority : MethodContractObligation {
    attribute :>> obligationId = "PC-009D-ACCEPTANCE-AUTHORITY";
    attribute :>> phase = MethodPhase::phase10_vvEvidence;
    attribute :>> subjectSelector = "each profile's canonical record";
    attribute :>> applicability = "(no applicability condition)";
    attribute :>> minimumPopulation = 1;
    attribute :>> permittedEmpty = false;
    attribute :>> predicate = "acceptance-record-match";
    attribute :>> targetFilter = "decision population completeness over the closed six-profile universe";
    attribute :>> cardinalityMinimum = 1;
    attribute :>> cardinalityMaximum = 1;
    attribute :>> required = true;
    attribute :>> evaluationSource = EvaluationSourceKind::pinnedRepositoryArtifact;
    attribute :>> attestationPolicyRef = "de4sdv.acceptance.maintainer-decision.v1";
    attribute :>> claimBoundary = "an attributable authorized acceptance decision covers the profile under the proposed policy";
  }

  /* Tested-scope declaration (candidate-declared comparison target). */
  item testedScope : TestedScopeDeclaration {
    attribute :>> executionHead = "01d9f586865bf7fb4bc0b3f76be2b5a916451da4";
    attribute :>> profileIdentities = "fresh_false_control, fresh_true_conscious_override, stale, missing, malformed, future_stamped";
  }

  /* Acceptance attestation reference: policy identity + registry location.
     The policy is Proposed (not activated); the registry is currently
     absent — a missing registry is a distinct state, never an empty pass. */
  item acceptanceAttestation : AcceptanceAttestationReference {
    attribute :>> policyRef = "de4sdv.acceptance.maintainer-decision.v1";
    attribute :>> decisionRegistryPath = "docs/acceptance-decisions/";
  }
}
