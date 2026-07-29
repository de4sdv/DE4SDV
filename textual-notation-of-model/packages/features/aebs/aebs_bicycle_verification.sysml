/* INC-AEBS-009H bicycle-target evidence contract; no product verification claim. */
package DE4SDV_AEBS009HVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  enum def EvidenceOutcome009H {
    passBoundedTargetResponse;
    failConfiguredOutcome;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def Retained009HObservationSet;
  item def Replayed009HEvaluation {
    attribute outcome : EvidenceOutcome009H;
  }
  calc def Map009HOutcomeToVerdict {
    in outcome : EvidenceOutcome009H;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome009H::passBoundedTargetResponse? VerdictKind::pass
      else if outcome == EvidenceOutcome009H::failConfiguredOutcome? VerdictKind::fail
      else if outcome == EvidenceOutcome009H::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def BicycleTargetBench009H;
  requirement def EvidenceContract009H;
  requirement evidenceContract009HConfiguredBicycleTarget : EvidenceContract009H {
    subject bench : BicycleTargetBench009H;
    require constraint { doc /* The bench shall bind the configured bicycle trajectory, geometry, timing, and exact bench identity. */ }
  }
  requirement evidenceContract009HIndependentFootprintOutcome : EvidenceContract009H {
    subject bench : BicycleTargetBench009H;
    require constraint { doc /* The bench shall reconstruct ego and bicycle footprints independently from retained map-frame observations and reject missing or contradictory samples. */ }
  }
  requirement evidenceContract009HReplayableProvenance : EvidenceContract009H {
    subject bench : BicycleTargetBench009H;
    require constraint { doc /* The bench shall hash-bind scenario, runtime, evaluator, observation, map-runtime, and artifact identities for independent replay. */ }
  }

  part bicycleTargetBench009H : BicycleTargetBench009H;
  verification def BicycleTargetVerification009H {
    subject verifiedBench : BicycleTargetBench009H;
    objective evidenceObjective009H {
      verify evidenceContract009HConfiguredBicycleTarget;
      verify evidenceContract009HIndependentFootprintOutcome;
      verify evidenceContract009HReplayableProvenance;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : Retained009HObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedObservations : Retained009HObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : Replayed009HEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : Replayed009HEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = Map009HOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification bicycleTargetVerification009H : BicycleTargetVerification009H {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> bicycleTargetBench009H;
  }
  part verificationSystem009H {
    perform bicycleTargetVerification009H;
  }

  dependency bicycleConfigurationRelevantToBicycleDetectionCandidate
    from evidenceContract009HConfiguredBicycleTarget to reqBicycleTargetResponse;
  dependency bicycleOutcomeRelevantToBicycleResponseCandidate
    from evidenceContract009HIndependentFootprintOutcome to reqBicycleTargetControlledResponse;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebs009HVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBS009HVerification::*;
    render asTreeDiagram;
  }
}
