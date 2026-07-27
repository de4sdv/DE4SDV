/* INC-AEBS-009E bounded non-activation and false-reaction matrix. */
package DE4SDV_AEBS009EVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  item def Retained009EObservationSet;
  item def Replayed009EEvaluation;
  part def FalseReactionMatrixBench009E;
  requirement def EvidenceContract009E;
  requirement evidenceContract009EClosedNonActivationScenario : EvidenceContract009E {
    subject bench : FalseReactionMatrixBench009E;
    require constraint { doc /* Each configured usage shall preserve one closed scenario identity and complete observation window. */ }
  }
  requirement evidenceContract009EWarningSilenceWindow : EvidenceContract009E {
    subject bench : FalseReactionMatrixBench009E;
    require constraint { doc /* A no-warning result requires a complete periodic observation window with fresh terminal coverage and no contradictory warning observation. */ }
  }
  requirement evidenceContract009EBrakingSilenceWindow : EvidenceContract009E {
    subject bench : FalseReactionMatrixBench009E;
    require constraint { doc /* A no-braking result requires a complete periodic command and publisher-topology window with fresh terminal coverage and no contradictory command. */ }
  }
  part clearPathBench009E : FalseReactionMatrixBench009E;
  part adjacentObjectBench009E : FalseReactionMatrixBench009E;
  part falseReactionControlBench009E : FalseReactionMatrixBench009E;
  verification def FalseReactionResistanceVerification009E {
    subject verifiedBench : FalseReactionMatrixBench009E;
    objective evidenceObjective009E {
      verify evidenceContract009EClosedNonActivationScenario;
      verify evidenceContract009EWarningSilenceWindow;
      verify evidenceContract009EBrakingSilenceWindow;
    }
    action collectData { @VerificationMethod{ kind = test; } out item retainedObservations : Retained009EObservationSet; }
    action processData { @VerificationMethod{ kind = analyze; } in item retainedObservations : Retained009EObservationSet = collectData.retainedObservations; out item replayedEvaluation : Replayed009EEvaluation; }
    action evaluateData { @VerificationMethod{ kind = analyze; } in item replayedEvaluation : Replayed009EEvaluation = processData.replayedEvaluation; out verdict : VerdictKind; }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification clearPathNonActivationVerification009E : FalseReactionResistanceVerification009E { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> clearPathBench009E; }
  verification adjacentObjectNonActivationVerification009E : FalseReactionResistanceVerification009E { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> adjacentObjectBench009E; }
  verification falseReactionControlVerification009E : FalseReactionResistanceVerification009E { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> falseReactionControlBench009E; }
  part verificationSystem009E { perform clearPathNonActivationVerification009E; perform adjacentObjectNonActivationVerification009E; perform falseReactionControlVerification009E; }
  dependency nonActivationEvidenceRelevantToFalseReactionCandidate from evidenceContract009EBrakingSilenceWindow to reqResistFalseReaction;
}
