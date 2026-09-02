/* INC-AEBS-009E bounded non-activation matrix; planned System 2 executable contracts. */
package DE4SDV_AEBS009EVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  enum def NonActivationScenarioIdentity {
    clearPath;
    adjacentObject;
    nonClosingTarget;
    belowTrigger;
  }
  enum def NonActivationEvidenceOutcome {
    passBoundedSilence;
    failUnexpectedActivation;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def NonActivationObservationSet;
  item def NonActivationEvaluation {
    attribute scenario : NonActivationScenarioIdentity;
    attribute outcome : NonActivationEvidenceOutcome;
  }
  calc def MapNonActivationOutcomeToVerdict {
    in outcome : NonActivationEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == NonActivationEvidenceOutcome::passBoundedSilence? VerdictKind::pass
      else if outcome == NonActivationEvidenceOutcome::failUnexpectedActivation? VerdictKind::fail
      else if outcome == NonActivationEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def FalseReactionMatrixBench {
    attribute scenario : NonActivationScenarioIdentity;
  }
  requirement def NonActivationEvidenceContract;
  requirement evidenceContractClosedNonActivationScenario : NonActivationEvidenceContract {
    subject bench : FalseReactionMatrixBench;
    require constraint statement { language "English" /* The bench shall bind one closed scenario identity and a complete observation window: at least 4.0 s duration with no sample gap above 0.75 s and every required input no older than 0.5 s at window close. */ }
  }
  requirement evidenceContractWarningSilenceWindow : NonActivationEvidenceContract {
    subject bench : FalseReactionMatrixBench;
    require constraint statement { language "English" /* The bench shall establish warning silence only from a complete periodic window with fresh terminal coverage and no contradictory warning. */ }
  }
  requirement evidenceContractBrakingSilenceWindow : NonActivationEvidenceContract {
    subject bench : FalseReactionMatrixBench;
    require constraint statement { language "English" /* The bench shall establish braking silence only from complete command, required-input-health, and publisher-topology coverage with no contradictory command. */ }
  }

  part clearPathBench : FalseReactionMatrixBench {
    attribute :>> scenario = NonActivationScenarioIdentity::clearPath;
  }
  part adjacentObjectBench : FalseReactionMatrixBench {
    attribute :>> scenario = NonActivationScenarioIdentity::adjacentObject;
  }
  part nonClosingTargetBench : FalseReactionMatrixBench {
    attribute :>> scenario = NonActivationScenarioIdentity::nonClosingTarget;
  }
  part belowTriggerBench : FalseReactionMatrixBench {
    attribute :>> scenario = NonActivationScenarioIdentity::belowTrigger;
  }

  verification def FalseReactionResistanceVerification {
    subject verifiedBench : FalseReactionMatrixBench;
    objective evidenceObjective {
      verify evidenceContractClosedNonActivationScenario;
      verify evidenceContractWarningSilenceWindow;
      verify evidenceContractBrakingSilenceWindow;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : NonActivationObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : NonActivationScenarioIdentity = verifiedBench.scenario;
      in item retainedObservations : NonActivationObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : NonActivationEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : NonActivationEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapNonActivationOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification clearPathNonActivationVerification : FalseReactionResistanceVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> clearPathBench;
  }
  verification adjacentObjectNonActivationVerification : FalseReactionResistanceVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> adjacentObjectBench;
  }
  verification nonClosingTargetNonActivationVerification : FalseReactionResistanceVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> nonClosingTargetBench;
  }
  verification belowTriggerNonActivationVerification : FalseReactionResistanceVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> belowTriggerBench;
  }
  part verificationSystem {
    perform clearPathNonActivationVerification;
    perform adjacentObjectNonActivationVerification;
    perform nonClosingTargetNonActivationVerification;
    perform belowTriggerNonActivationVerification;
  }

  dependency warningSilenceEvidenceRelevantToWarningSilenceCandidate
    from evidenceContractWarningSilenceWindow to reqResistFalseReaction;
  dependency brakingSilenceEvidenceRelevantToBrakingSilenceCandidate
    from evidenceContractBrakingSilenceWindow to reqResistFalseBrakingCommand;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebsNonActivationVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBS009EVerification::*;
    render asTreeDiagram;
  }
}
