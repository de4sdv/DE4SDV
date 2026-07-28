/* INC-AEBS-009C partial native-intervention-to-MRM System 2 verification model. */
package DE4SDV_AEBS009CVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;

  item def Retained009CObservationSet;
  item def Replayed009CEvaluation { attribute outcome : EvidenceOutcome009C; }
  enum def EvidenceOutcome009C {
    passObservedChain;
    failScenario;
    inconclusivePrecondition;
    inconclusiveInstrumentation;
    aborted;
  }
  calc def Map009COutcomeToVerdict {
    in outcome : EvidenceOutcome009C;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome009C::passObservedChain? VerdictKind::pass
      else if outcome == EvidenceOutcome009C::failScenario? VerdictKind::fail
      else if outcome == EvidenceOutcome009C::aborted? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def NativeInterventionBench009C;
  requirement def EvidenceContract009C;
  requirement evidenceContract009CExactNativeDiagnostic : EvidenceContract009C {
    subject bench : NativeInterventionBench009C;
    require constraint { doc /* Replay shall observe the exact configured native AEB intervention diagnostic tuple. */ }
  }
  requirement evidenceContract009CMRMGateChain : EvidenceContract009C {
    subject bench : NativeInterventionBench009C;
    require constraint { doc /* Replay shall preserve ordered MRM transition, emergency-gate selection, and simulator-response observations with their source and collector stamps. */ }
  }
  requirement evidenceContract009CFailClosedProvenance : EvidenceContract009C {
    subject bench : NativeInterventionBench009C;
    require constraint { doc /* Missing, contradictory, identity-mismatched, or unreplayable evidence shall not produce a passing outcome. */ }
  }

  part nativeInterventionBench009C : NativeInterventionBench009C;
  verification def NativeInterventionToMRMVerification009C {
    subject verifiedBench : NativeInterventionBench009C;
    objective evidenceObjective009C {
      verify evidenceContract009CExactNativeDiagnostic;
      verify evidenceContract009CMRMGateChain;
      verify evidenceContract009CFailClosedProvenance;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : Retained009CObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedObservations : Retained009CObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : Replayed009CEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : Replayed009CEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = Map009COutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification nativeInterventionToMRMVerification009C : NativeInterventionToMRMVerification009C {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> nativeInterventionBench009C;
  }
  part verificationSystem009C { perform nativeInterventionToMRMVerification009C; }

  dependency partialInterventionEvidenceRelevantToBrakingCandidate
    from evidenceContract009CMRMGateChain to reqCommandEmergencyBraking;
}
