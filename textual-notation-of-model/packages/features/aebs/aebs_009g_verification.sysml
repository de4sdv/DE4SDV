/* INC-AEBS-009G pedestrian-target evidence contract; no product verification claim. */
package DE4SDV_AEBS009GVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;

  enum def EvidenceOutcome009G {
    passBoundedTargetResponse;
    failConfiguredOutcome;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def Retained009GObservationSet;
  item def Replayed009GEvaluation {
    attribute outcome : EvidenceOutcome009G;
  }
  calc def Map009GOutcomeToVerdict {
    in outcome : EvidenceOutcome009G;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome009G::passBoundedTargetResponse? VerdictKind::pass
      else if outcome == EvidenceOutcome009G::failConfiguredOutcome? VerdictKind::fail
      else if outcome == EvidenceOutcome009G::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def PedestrianTargetBench009G;
  requirement def EvidenceContract009G;
  requirement evidenceContract009GConfiguredPedestrianTarget : EvidenceContract009G {
    subject bench : PedestrianTargetBench009G;
    require constraint { doc /* The bench shall bind the configured pedestrian trajectory, geometry, timing, and exact bench identity. */ }
  }
  requirement evidenceContract009GIndependentFootprintOutcome : EvidenceContract009G {
    subject bench : PedestrianTargetBench009G;
    require constraint { doc /* The bench shall reconstruct ego and pedestrian footprints independently from retained map-frame observations and reject missing or contradictory samples. */ }
  }
  requirement evidenceContract009GReplayableProvenance : EvidenceContract009G {
    subject bench : PedestrianTargetBench009G;
    require constraint { doc /* The bench shall hash-bind scenario, runtime, evaluator, observation, map-runtime, and artifact identities for independent replay. */ }
  }

  part pedestrianTargetBench009G : PedestrianTargetBench009G;
  verification def PedestrianTargetVerification009G {
    subject verifiedBench : PedestrianTargetBench009G;
    objective evidenceObjective009G {
      verify evidenceContract009GConfiguredPedestrianTarget;
      verify evidenceContract009GIndependentFootprintOutcome;
      verify evidenceContract009GReplayableProvenance;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : Retained009GObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedObservations : Retained009GObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : Replayed009GEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : Replayed009GEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = Map009GOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification pedestrianTargetVerification009G : PedestrianTargetVerification009G {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> pedestrianTargetBench009G;
  }
  part verificationSystem009G {
    perform pedestrianTargetVerification009G;
  }

  dependency pedestrianEvidenceRelevantToPedestrianCandidate
    from evidenceContract009GIndependentFootprintOutcome to reqPedestrianTargetResponse;
}
