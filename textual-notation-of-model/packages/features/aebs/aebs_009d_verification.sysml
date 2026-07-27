/* INC-AEBS-009D conscious-override matrix; planned System 2 executable contracts. */
package DE4SDV_AEBS009DVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;

  enum def ScenarioIdentity009D {
    freshFalseControl;
    freshTrueOverride;
    staleOverride;
    missingOverride;
    malformedOverride;
    futureStampedOverride;
  }
  enum def EvidenceOutcome009D {
    passBoundedScenario;
    failObservedBehavior;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def Retained009DObservationSet;
  item def Replayed009DEvaluation {
    attribute scenario : ScenarioIdentity009D;
    attribute outcome : EvidenceOutcome009D;
  }
  calc def Map009DOutcomeToVerdict {
    in outcome : EvidenceOutcome009D;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome009D::passBoundedScenario? VerdictKind::pass
      else if outcome == EvidenceOutcome009D::failObservedBehavior? VerdictKind::fail
      else if outcome == EvidenceOutcome009D::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def OverrideMatrixBench009D {
    attribute scenario : ScenarioIdentity009D;
  }
  requirement def EvidenceContract009D;
  requirement evidenceContract009DClosedOverrideScenario : EvidenceContract009D {
    subject bench : OverrideMatrixBench009D;
    require constraint { doc /* The bench shall bind exactly one closed override scenario identity. */ }
  }
  requirement evidenceContract009DOverrideFreshnessReplay : EvidenceContract009D {
    subject bench : OverrideMatrixBench009D;
    require constraint { doc /* The bench shall replay source stamp, receipt time, value validity, exact diagnostic-source authorization, and the scenario-specific suppression, release, or degraded disposition. */ }
  }
  requirement evidenceContract009DIndependentVerdict : EvidenceContract009D {
    subject bench : OverrideMatrixBench009D;
    require constraint { doc /* The bench shall retain separate observations, evaluation, provenance, and verdict for each scenario; observer failure shall not pass. */ }
  }

  part overrideFalseControlBench009D : OverrideMatrixBench009D {
    attribute :>> scenario = ScenarioIdentity009D::freshFalseControl;
  }
  part overrideTrueBench009D : OverrideMatrixBench009D {
    attribute :>> scenario = ScenarioIdentity009D::freshTrueOverride;
  }
  part overrideStaleBench009D : OverrideMatrixBench009D {
    attribute :>> scenario = ScenarioIdentity009D::staleOverride;
  }
  part overrideMissingBench009D : OverrideMatrixBench009D {
    attribute :>> scenario = ScenarioIdentity009D::missingOverride;
  }
  part overrideMalformedBench009D : OverrideMatrixBench009D {
    attribute :>> scenario = ScenarioIdentity009D::malformedOverride;
  }
  part overrideFutureStampedBench009D : OverrideMatrixBench009D {
    attribute :>> scenario = ScenarioIdentity009D::futureStampedOverride;
  }

  verification def ConsciousOverrideVerification009D {
    subject verifiedBench : OverrideMatrixBench009D;
    objective evidenceObjective009D {
      verify evidenceContract009DClosedOverrideScenario;
      verify evidenceContract009DOverrideFreshnessReplay;
      verify evidenceContract009DIndependentVerdict;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : Retained009DObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity009D = verifiedBench.scenario;
      in item retainedObservations : Retained009DObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : Replayed009DEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : Replayed009DEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = Map009DOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification overrideFalseControlVerification009D : ConsciousOverrideVerification009D {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideFalseControlBench009D;
  }
  verification overrideTrueVerification009D : ConsciousOverrideVerification009D {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideTrueBench009D;
  }
  verification overrideStaleVerification009D : ConsciousOverrideVerification009D {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideStaleBench009D;
  }
  verification overrideMissingVerification009D : ConsciousOverrideVerification009D {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideMissingBench009D;
  }
  verification overrideMalformedVerification009D : ConsciousOverrideVerification009D {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideMalformedBench009D;
  }
  verification overrideFutureStampedVerification009D : ConsciousOverrideVerification009D {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideFutureStampedBench009D;
  }
  part verificationSystem009D {
    perform overrideFalseControlVerification009D;
    perform overrideTrueVerification009D;
    perform overrideStaleVerification009D;
    perform overrideMissingVerification009D;
    perform overrideMalformedVerification009D;
    perform overrideFutureStampedVerification009D;
  }

  dependency overrideEvidenceRelevantToOverrideCandidate
    from evidenceContract009DOverrideFreshnessReplay to reqAllowDriverOverride;
}
