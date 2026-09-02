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
  requirement evidenceContractClosedOverrideScenario : OverrideEvidenceContract {
    subject bench : OverrideMatrixBench;
    require constraint statement { language "English" /* The bench shall bind exactly one closed override scenario identity. */ }
  }
  requirement evidenceContractOverrideFreshnessReplay : OverrideEvidenceContract {
    subject bench : OverrideMatrixBench;
    require constraint statement { language "English" /* The bench shall replay source stamp, receipt time, value validity, exact diagnostic-source authorization, and the scenario-specific suppression, release, or degraded disposition. A fresh sample is one with source-stamp-to-receipt age at most 0.2 s; suppression is evaluated within a closed window of 0.25 s; runtime-graph sampling gaps above 0.2 s fail the replay. */ }
  }
  requirement evidenceContractIndependentVerdict : OverrideEvidenceContract {
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

  verification def ConsciousOverrideVerification {
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
  verification overrideFalseControlVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideFalseControlBench;
  }
  verification overrideTrueVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideTrueBench;
  }
  verification overrideStaleVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideStaleBench;
  }
  verification overrideMissingVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideMissingBench;
  }
  verification overrideMalformedVerification : ConsciousOverrideVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> overrideMalformedBench;
  }
  verification overrideFutureStampedVerification : ConsciousOverrideVerification {
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
}
