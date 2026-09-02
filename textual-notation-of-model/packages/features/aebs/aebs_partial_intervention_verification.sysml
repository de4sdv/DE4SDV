/* INC-AEBS-009C partial native-intervention-to-MRM System 2 verification model. */
package DE4SDV_AEBSPartialInterventionVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  item def PartialInterventionObservationSet;
  item def PartialInterventionEvaluation { attribute outcome : PartialInterventionEvidenceOutcome; }
  enum def PartialInterventionEvidenceOutcome {
    passObservedChain;
    failScenario;
    inconclusivePrecondition;
    inconclusiveInstrumentation;
    aborted;
  }
  calc def MapPartialInterventionOutcomeToVerdict {
    in outcome : PartialInterventionEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == PartialInterventionEvidenceOutcome::passObservedChain? VerdictKind::pass
      else if outcome == PartialInterventionEvidenceOutcome::failScenario? VerdictKind::fail
      else if outcome == PartialInterventionEvidenceOutcome::aborted? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def NativeInterventionBench;
  requirement def PartialInterventionEvidenceContract;
  requirement evidenceContractExactNativeDiagnostic : PartialInterventionEvidenceContract {
    subject bench : NativeInterventionBench;
    require constraint statement { language "English" /* Replay shall observe the exact configured native AEB intervention diagnostic tuple. */ }
  }
  requirement evidenceContractMRMGateChain : PartialInterventionEvidenceContract {
    subject bench : NativeInterventionBench;
    require constraint statement { language "English" /* Replay shall preserve ordered MRM transition, emergency-gate selection, and simulator-response observations with their source and collector stamps. */ }
  }
  requirement evidenceContractFailClosedProvenance : PartialInterventionEvidenceContract {
    subject bench : NativeInterventionBench;
    require constraint statement { language "English" /* Missing, contradictory, identity-mismatched, or unreplayable evidence shall not produce a passing outcome. */ }
  }

  part nativeInterventionBench : NativeInterventionBench;
  verification def NativeInterventionToMRMVerification {
    subject verifiedBench : NativeInterventionBench;
    objective evidenceObjective {
      verify evidenceContractExactNativeDiagnostic;
      verify evidenceContractMRMGateChain;
      verify evidenceContractFailClosedProvenance;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : PartialInterventionObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedObservations : PartialInterventionObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : PartialInterventionEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : PartialInterventionEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapPartialInterventionOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification nativeInterventionToMRMVerification : NativeInterventionToMRMVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> nativeInterventionBench;
  }
  part verificationSystem { perform nativeInterventionToMRMVerification; }

  dependency partialInterventionEvidenceRelevantToBrakingCandidate
    from evidenceContractMRMGateChain to reqCommandEmergencyBraking;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebsPartialInterventionVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBSPartialInterventionVerification::*;
    render asTreeDiagram;
  }
}
