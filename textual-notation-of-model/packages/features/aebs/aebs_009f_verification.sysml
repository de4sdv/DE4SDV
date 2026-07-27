/* INC-AEBS-009F degraded/unavailable input matrix. */
package DE4SDV_AEBS009FVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  item def Retained009FObservationSet;
  item def Replayed009FEvaluation;
  part def DegradedInputMatrixBench009F;
  requirement def EvidenceContract009F;
  requirement evidenceContract009FClosedInputHealthScenario : EvidenceContract009F {
    subject bench : DegradedInputMatrixBench009F;
    require constraint { doc /* Each configured usage shall inject exactly one stale, missing, malformed, inconsistent, or unavailable input condition from the closed registry. */ }
  }
  requirement evidenceContract009FStateOwnership : EvidenceContract009F {
    subject bench : DegradedInputMatrixBench009F;
    require constraint { doc /* Replay shall preserve the producer identity and ordered degraded/unavailable state and indication observations for the configured case. */ }
  }
  requirement evidenceContract009FObserverFailureIsNotPass : EvidenceContract009F {
    subject bench : DegradedInputMatrixBench009F;
    require constraint { doc /* Missing or contradictory observer evidence shall map to inconclusive or error and shall not establish System 1 behavior. */ }
  }
  part staleInputBench009F : DegradedInputMatrixBench009F;
  part missingInputBench009F : DegradedInputMatrixBench009F;
  part malformedInputBench009F : DegradedInputMatrixBench009F;
  part inconsistentInputBench009F : DegradedInputMatrixBench009F;
  part unavailableInputBench009F : DegradedInputMatrixBench009F;
  verification def DegradedUnavailableVerification009F {
    subject verifiedBench : DegradedInputMatrixBench009F;
    objective evidenceObjective009F {
      verify evidenceContract009FClosedInputHealthScenario;
      verify evidenceContract009FStateOwnership;
      verify evidenceContract009FObserverFailureIsNotPass;
    }
    action collectData { @VerificationMethod{ kind = test; } out item retainedObservations : Retained009FObservationSet; }
    action processData { @VerificationMethod{ kind = analyze; } in item retainedObservations : Retained009FObservationSet = collectData.retainedObservations; out item replayedEvaluation : Replayed009FEvaluation; }
    action evaluateData { @VerificationMethod{ kind = analyze; } in item replayedEvaluation : Replayed009FEvaluation = processData.replayedEvaluation; out verdict : VerdictKind; }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification staleInputVerification009F : DegradedUnavailableVerification009F { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> staleInputBench009F; }
  verification missingInputVerification009F : DegradedUnavailableVerification009F { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> missingInputBench009F; }
  verification malformedInputVerification009F : DegradedUnavailableVerification009F { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> malformedInputBench009F; }
  verification inconsistentInputVerification009F : DegradedUnavailableVerification009F { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> inconsistentInputBench009F; }
  verification unavailableInputVerification009F : DegradedUnavailableVerification009F { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> unavailableInputBench009F; }
  part verificationSystem009F { perform staleInputVerification009F; perform missingInputVerification009F; perform malformedInputVerification009F; perform inconsistentInputVerification009F; perform unavailableInputVerification009F; }
  dependency degradedEvidenceRelevantToDegradedCandidate from evidenceContract009FStateOwnership to reqHandleDegradedUnavailableInputs;
}
