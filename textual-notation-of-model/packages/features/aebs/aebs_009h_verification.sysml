/* INC-AEBS-009H bicycle-target evidence contract; no product verification claim. */
package DE4SDV_AEBS009HVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  item def Retained009HObservationSet;
  item def Replayed009HEvaluation;
  part def BicycleTargetBench009H;
  requirement def EvidenceContract009H;
  requirement evidenceContract009HConfiguredBicycleTarget : EvidenceContract009H { subject bench : BicycleTargetBench009H; require constraint { doc /* Evidence shall bind the configured bicycle-target trajectory, geometry, timing, and exact bench identity. */ } }
  requirement evidenceContract009HIndependentFootprintOutcome : EvidenceContract009H { subject bench : BicycleTargetBench009H; require constraint { doc /* Replay shall reconstruct ego and bicycle-target footprints independently from retained map-frame observations and reject missing or contradictory samples. */ } }
  requirement evidenceContract009HReplayableProvenance : EvidenceContract009H { subject bench : BicycleTargetBench009H; require constraint { doc /* Scenario, runtime, evaluator, observation, and artifact identities shall be hash-bound and independently replayable. */ } }
  part bicycleTargetBench009H : BicycleTargetBench009H;
  verification def BicycleTargetVerification009H {
    subject verifiedBench : BicycleTargetBench009H;
    objective evidenceObjective009H { verify evidenceContract009HConfiguredBicycleTarget; verify evidenceContract009HIndependentFootprintOutcome; verify evidenceContract009HReplayableProvenance; }
    action collectData { @VerificationMethod{ kind = test; } out item retainedObservations : Retained009HObservationSet; }
    action processData { @VerificationMethod{ kind = analyze; } in item retainedObservations : Retained009HObservationSet = collectData.retainedObservations; out item replayedEvaluation : Replayed009HEvaluation; }
    action evaluateData { @VerificationMethod{ kind = analyze; } in item replayedEvaluation : Replayed009HEvaluation = processData.replayedEvaluation; out verdict : VerdictKind; }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification bicycleTargetVerification009H : BicycleTargetVerification009H { @VerificationMethod{ kind = (test, analyze); } subject verifiedBench :> bicycleTargetBench009H; }
  part verificationSystem009H { perform bicycleTargetVerification009H; }
  dependency bicycleEvidenceRelevantToBicycleCandidate from evidenceContract009HIndependentFootprintOutcome to reqBicycleTargetResponse;
}
