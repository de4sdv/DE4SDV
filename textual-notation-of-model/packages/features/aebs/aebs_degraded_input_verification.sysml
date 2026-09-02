/* INC-AEBS-009F degraded/unavailable input matrix; planned System 2 executable contracts. */
package DE4SDV_AEBS009FVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  enum def DegradedInputScenarioIdentity {
    staleInput;
    missingInput;
    malformedInput;
    inconsistentInput;
    unavailableInput;
  }
  enum def DegradedInputEvidenceOutcome {
    passBoundedDetection;
    failWrongDisposition;
    inconclusiveInstrumentation;
    errorEvidence;
  }
  item def DegradedInputObservationSet;
  item def DegradedInputEvaluation {
    attribute scenario : DegradedInputScenarioIdentity;
    attribute outcome : DegradedInputEvidenceOutcome;
  }
  calc def MapDegradedInputOutcomeToVerdict {
    in outcome : DegradedInputEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == DegradedInputEvidenceOutcome::passBoundedDetection? VerdictKind::pass
      else if outcome == DegradedInputEvidenceOutcome::failWrongDisposition? VerdictKind::fail
      else if outcome == DegradedInputEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def DegradedInputMatrixBench {
    attribute scenario : DegradedInputScenarioIdentity;
  }
  requirement def DegradedInputEvidenceContract;
  requirement evidenceContractClosedInputHealthScenario : DegradedInputEvidenceContract {
    subject bench : DegradedInputMatrixBench;
    require constraint statement { language "English" /* The bench shall inject exactly one closed stale, missing, malformed, inconsistent, or unavailable input condition after any required healthy baseline. A degraded state is accepted only while its observation age stays within 0.2 s, detection is closed within a 0.25 s window, and runtime-graph sampling gaps stay at or below 0.2 s. */ }
  }
  requirement evidenceContractStateOwnership : DegradedInputEvidenceContract {
    subject bench : DegradedInputMatrixBench;
    require constraint statement { language "English" /* The bench shall retain producer identity, affected topic, source timing, and ordered degraded-state transition and ownership observations. */ }
  }
  requirement evidenceContractStatusIndication : DegradedInputEvidenceContract {
    subject bench : DegradedInputMatrixBench;
    require constraint statement { language "English" /* The bench shall retain ordered AEBS status-indication observations for the bound input-health scenario. */ }
  }
  requirement evidenceContractObserverFailureIsNotPass : DegradedInputEvidenceContract {
    subject bench : DegradedInputMatrixBench;
    require constraint statement { language "English" /* The bench shall map missing, contradictory, contaminated, or unobservable evidence to inconclusive or error, never pass. */ }
  }

  part staleInputBench : DegradedInputMatrixBench {
    attribute :>> scenario = DegradedInputScenarioIdentity::staleInput;
  }
  part missingInputBench : DegradedInputMatrixBench {
    attribute :>> scenario = DegradedInputScenarioIdentity::missingInput;
  }
  part malformedInputBench : DegradedInputMatrixBench {
    attribute :>> scenario = DegradedInputScenarioIdentity::malformedInput;
  }
  part inconsistentInputBench : DegradedInputMatrixBench {
    attribute :>> scenario = DegradedInputScenarioIdentity::inconsistentInput;
  }
  part unavailableInputBench : DegradedInputMatrixBench {
    attribute :>> scenario = DegradedInputScenarioIdentity::unavailableInput;
  }

  verification def DegradedUnavailableVerification {
    subject verifiedBench : DegradedInputMatrixBench;
    objective evidenceObjective {
      verify evidenceContractClosedInputHealthScenario;
      verify evidenceContractStateOwnership;
      verify evidenceContractStatusIndication;
      verify evidenceContractObserverFailureIsNotPass;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : DegradedInputObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : DegradedInputScenarioIdentity = verifiedBench.scenario;
      in item retainedObservations : DegradedInputObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : DegradedInputEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : DegradedInputEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapDegradedInputOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification staleInputVerification : DegradedUnavailableVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> staleInputBench;
  }
  verification missingInputVerification : DegradedUnavailableVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> missingInputBench;
  }
  verification malformedInputVerification : DegradedUnavailableVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> malformedInputBench;
  }
  verification inconsistentInputVerification : DegradedUnavailableVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> inconsistentInputBench;
  }
  verification unavailableInputVerification : DegradedUnavailableVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> unavailableInputBench;
  }
  part verificationSystem {
    perform staleInputVerification;
    perform missingInputVerification;
    perform malformedInputVerification;
    perform inconsistentInputVerification;
    perform unavailableInputVerification;
  }

  dependency degradedStateEvidenceRelevantToStateTransitionCandidate
    from evidenceContractStateOwnership to reqHandleDegradedUnavailableInputs;
  dependency degradedStatusEvidenceRelevantToStatusIndicationCandidate
    from evidenceContractStatusIndication to reqIndicateDegradedUnavailableStatus;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebsDegradedInputVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBS009FVerification::*;
    render asTreeDiagram;
  }
}
