/* INC-AEBS-009F degraded/unavailable input matrix; planned System 2 executable contracts. */
package DE4SDV_AEBS009FVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;

  enum def ScenarioIdentity009F {
    staleInput;
    missingInput;
    malformedInput;
    inconsistentInput;
    unavailableInput;
  }
  enum def EvidenceOutcome009F {
    passBoundedDetection;
    failWrongDisposition;
    inconclusiveInstrumentation;
    errorEvidence;
  }
  item def Retained009FObservationSet;
  item def Replayed009FEvaluation {
    attribute scenario : ScenarioIdentity009F;
    attribute outcome : EvidenceOutcome009F;
  }
  calc def Map009FOutcomeToVerdict {
    in outcome : EvidenceOutcome009F;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome009F::passBoundedDetection? VerdictKind::pass
      else if outcome == EvidenceOutcome009F::failWrongDisposition? VerdictKind::fail
      else if outcome == EvidenceOutcome009F::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def DegradedInputMatrixBench009F {
    attribute scenario : ScenarioIdentity009F;
  }
  requirement def EvidenceContract009F;
  requirement evidenceContract009FClosedInputHealthScenario : EvidenceContract009F {
    subject bench : DegradedInputMatrixBench009F;
    require constraint { doc /* The bench shall inject exactly one closed stale, missing, malformed, inconsistent, or unavailable input condition after any required healthy baseline. */ }
  }
  requirement evidenceContract009FStateOwnership : EvidenceContract009F {
    subject bench : DegradedInputMatrixBench009F;
    require constraint { doc /* The bench shall retain producer identity, affected topic, source timing, and ordered degraded-state, suppression, ownership, and indication observations. */ }
  }
  requirement evidenceContract009FObserverFailureIsNotPass : EvidenceContract009F {
    subject bench : DegradedInputMatrixBench009F;
    require constraint { doc /* The bench shall map missing, contradictory, contaminated, or unobservable evidence to inconclusive or error, never pass. */ }
  }

  part staleInputBench009F : DegradedInputMatrixBench009F {
    attribute :>> scenario = ScenarioIdentity009F::staleInput;
  }
  part missingInputBench009F : DegradedInputMatrixBench009F {
    attribute :>> scenario = ScenarioIdentity009F::missingInput;
  }
  part malformedInputBench009F : DegradedInputMatrixBench009F {
    attribute :>> scenario = ScenarioIdentity009F::malformedInput;
  }
  part inconsistentInputBench009F : DegradedInputMatrixBench009F {
    attribute :>> scenario = ScenarioIdentity009F::inconsistentInput;
  }
  part unavailableInputBench009F : DegradedInputMatrixBench009F {
    attribute :>> scenario = ScenarioIdentity009F::unavailableInput;
  }

  verification def DegradedUnavailableVerification009F {
    subject verifiedBench : DegradedInputMatrixBench009F;
    objective evidenceObjective009F {
      verify evidenceContract009FClosedInputHealthScenario;
      verify evidenceContract009FStateOwnership;
      verify evidenceContract009FObserverFailureIsNotPass;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : Retained009FObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity009F = verifiedBench.scenario;
      in item retainedObservations : Retained009FObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : Replayed009FEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : Replayed009FEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = Map009FOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification staleInputVerification009F : DegradedUnavailableVerification009F {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> staleInputBench009F;
  }
  verification missingInputVerification009F : DegradedUnavailableVerification009F {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> missingInputBench009F;
  }
  verification malformedInputVerification009F : DegradedUnavailableVerification009F {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> malformedInputBench009F;
  }
  verification inconsistentInputVerification009F : DegradedUnavailableVerification009F {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> inconsistentInputBench009F;
  }
  verification unavailableInputVerification009F : DegradedUnavailableVerification009F {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> unavailableInputBench009F;
  }
  part verificationSystem009F {
    perform staleInputVerification009F;
    perform missingInputVerification009F;
    perform malformedInputVerification009F;
    perform inconsistentInputVerification009F;
    perform unavailableInputVerification009F;
  }

  dependency degradedEvidenceRelevantToDegradedCandidate
    from evidenceContract009FStateOwnership to reqHandleDegradedUnavailableInputs;
}
