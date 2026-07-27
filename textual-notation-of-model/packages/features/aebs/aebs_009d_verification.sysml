/* INC-AEBS-009D conscious-override matrix; System 2 contracts only. */
package DE4SDV_AEBS009DVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  item def Retained009DObservationSet;
  item def Replayed009DEvaluation;
  part def OverrideMatrixBench009D;
  requirement def EvidenceContract009D;
  requirement evidenceContract009DClosedOverrideScenario : EvidenceContract009D {
    subject bench : OverrideMatrixBench009D;
    require constraint { doc /* Each configured usage shall bind exactly one closed false, true, stale, missing, malformed, or future-stamped override scenario identity. */ }
  }
  requirement evidenceContract009DOverrideFreshnessReplay : EvidenceContract009D {
    subject bench : OverrideMatrixBench009D;
    require constraint { doc /* Replay shall evaluate source stamp, receipt time, value validity, and the scenario-specific suppress-or-release observation without substituting a stored verdict. */ }
  }
  requirement evidenceContract009DIndependentVerdict : EvidenceContract009D {
    subject bench : OverrideMatrixBench009D;
    require constraint { doc /* Every configured scenario shall retain its own observations, evaluation, provenance, and verdict; observer failure is inconclusive or error, never pass. */ }
  }
  part overrideFalseControlBench009D : OverrideMatrixBench009D;
  part overrideTrueBench009D : OverrideMatrixBench009D;
  part overrideStaleBench009D : OverrideMatrixBench009D;
  part overrideMissingBench009D : OverrideMatrixBench009D;
  part overrideMalformedBench009D : OverrideMatrixBench009D;
  part overrideFutureStampedBench009D : OverrideMatrixBench009D;
  verification def ConsciousOverrideVerification009D {
    subject verifiedBench : OverrideMatrixBench009D;
    objective evidenceObjective009D {
      verify evidenceContract009DClosedOverrideScenario;
      verify evidenceContract009DOverrideFreshnessReplay;
      verify evidenceContract009DIndependentVerdict;
    }
    action collectData { @VerificationMethod{ kind = test; } out item retainedObservations : Retained009DObservationSet; }
    action processData { @VerificationMethod{ kind = analyze; } in item retainedObservations : Retained009DObservationSet = collectData.retainedObservations; out item replayedEvaluation : Replayed009DEvaluation; }
    action evaluateData { @VerificationMethod{ kind = analyze; } in item replayedEvaluation : Replayed009DEvaluation = processData.replayedEvaluation; out verdict : VerdictKind; }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification overrideFalseControlVerification009D : ConsciousOverrideVerification009D { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> overrideFalseControlBench009D; }
  verification overrideTrueVerification009D : ConsciousOverrideVerification009D { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> overrideTrueBench009D; }
  verification overrideStaleVerification009D : ConsciousOverrideVerification009D { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> overrideStaleBench009D; }
  verification overrideMissingVerification009D : ConsciousOverrideVerification009D { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> overrideMissingBench009D; }
  verification overrideMalformedVerification009D : ConsciousOverrideVerification009D { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> overrideMalformedBench009D; }
  verification overrideFutureStampedVerification009D : ConsciousOverrideVerification009D { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> overrideFutureStampedBench009D; }
  part verificationSystem009D {
    perform overrideFalseControlVerification009D; perform overrideTrueVerification009D;
    perform overrideStaleVerification009D; perform overrideMissingVerification009D;
    perform overrideMalformedVerification009D; perform overrideFutureStampedVerification009D;
  }
  dependency overrideEvidenceRelevantToOverrideCandidate from evidenceContract009DOverrideFreshnessReplay to reqAllowDriverOverride;
}
