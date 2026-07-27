/* INC-AEBS-009E bounded non-activation matrix; planned System 2 executable contracts. */
package DE4SDV_AEBS009EVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;

  enum def ScenarioIdentity009E {
    clearPath;
    adjacentObject;
    nonClosingTarget;
    belowTrigger;
  }
  enum def EvidenceOutcome009E {
    passBoundedSilence;
    failUnexpectedActivation;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def Retained009EObservationSet;
  item def Replayed009EEvaluation {
    attribute scenario : ScenarioIdentity009E;
    attribute outcome : EvidenceOutcome009E;
  }
  calc def Map009EOutcomeToVerdict {
    in outcome : EvidenceOutcome009E;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome009E::passBoundedSilence? VerdictKind::pass
      else if outcome == EvidenceOutcome009E::failUnexpectedActivation? VerdictKind::fail
      else if outcome == EvidenceOutcome009E::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def FalseReactionMatrixBench009E {
    attribute scenario : ScenarioIdentity009E;
  }
  requirement def EvidenceContract009E;
  requirement evidenceContract009EClosedNonActivationScenario : EvidenceContract009E {
    subject bench : FalseReactionMatrixBench009E;
    require constraint { doc /* The bench shall bind one closed scenario identity and a complete observation window. */ }
  }
  requirement evidenceContract009EWarningSilenceWindow : EvidenceContract009E {
    subject bench : FalseReactionMatrixBench009E;
    require constraint { doc /* The bench shall establish warning silence only from a complete periodic window with fresh terminal coverage and no contradictory warning. */ }
  }
  requirement evidenceContract009EBrakingSilenceWindow : EvidenceContract009E {
    subject bench : FalseReactionMatrixBench009E;
    require constraint { doc /* The bench shall establish braking silence only from complete command, required-input-health, and publisher-topology coverage with no contradictory command. */ }
  }

  part clearPathBench009E : FalseReactionMatrixBench009E {
    attribute :>> scenario = ScenarioIdentity009E::clearPath;
  }
  part adjacentObjectBench009E : FalseReactionMatrixBench009E {
    attribute :>> scenario = ScenarioIdentity009E::adjacentObject;
  }
  part nonClosingTargetBench009E : FalseReactionMatrixBench009E {
    attribute :>> scenario = ScenarioIdentity009E::nonClosingTarget;
  }
  part belowTriggerBench009E : FalseReactionMatrixBench009E {
    attribute :>> scenario = ScenarioIdentity009E::belowTrigger;
  }

  verification def FalseReactionResistanceVerification009E {
    subject verifiedBench : FalseReactionMatrixBench009E;
    objective evidenceObjective009E {
      verify evidenceContract009EClosedNonActivationScenario;
      verify evidenceContract009EWarningSilenceWindow;
      verify evidenceContract009EBrakingSilenceWindow;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : Retained009EObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity009E = verifiedBench.scenario;
      in item retainedObservations : Retained009EObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : Replayed009EEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : Replayed009EEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = Map009EOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification clearPathNonActivationVerification009E : FalseReactionResistanceVerification009E {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> clearPathBench009E;
  }
  verification adjacentObjectNonActivationVerification009E : FalseReactionResistanceVerification009E {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> adjacentObjectBench009E;
  }
  verification nonClosingTargetNonActivationVerification009E : FalseReactionResistanceVerification009E {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> nonClosingTargetBench009E;
  }
  verification belowTriggerNonActivationVerification009E : FalseReactionResistanceVerification009E {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> belowTriggerBench009E;
  }
  part verificationSystem009E {
    perform clearPathNonActivationVerification009E;
    perform adjacentObjectNonActivationVerification009E;
    perform nonClosingTargetNonActivationVerification009E;
    perform belowTriggerNonActivationVerification009E;
  }

  dependency warningSilenceEvidenceRelevantToFalseReactionCandidate
    from evidenceContract009EWarningSilenceWindow to reqResistFalseReaction;
  dependency brakingSilenceEvidenceRelevantToFalseReactionCandidate
    from evidenceContract009EBrakingSilenceWindow to reqResistFalseReaction;
}
