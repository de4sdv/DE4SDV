/* INC-AEBS-009H bicycle-target evidence contract; no product verification claim. */
package DE4SDV_AEBS009HVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  enum def BicycleEvidenceOutcome {
    passBoundedTargetResponse;
    failConfiguredOutcome;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def BicycleObservationSet;
  item def BicycleEvaluation {
    attribute outcome : BicycleEvidenceOutcome;
  }
  calc def MapBicycleOutcomeToVerdict {
    in outcome : BicycleEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == BicycleEvidenceOutcome::passBoundedTargetResponse? VerdictKind::pass
      else if outcome == BicycleEvidenceOutcome::failConfiguredOutcome? VerdictKind::fail
      else if outcome == BicycleEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def BicycleTargetBench;
  requirement def BicycleEvidenceContract;
  requirement evidenceContractConfiguredBicycleTarget : BicycleEvidenceContract {
    subject bench : BicycleTargetBench;
    require constraint statement { language "English" /* The bench shall bind the configured bicycle trajectory, geometry, timing, and exact bench identity: crossing speed 4.0 m/s, a closed observation window of 2.0 s, and map-frame source observations no older than 0.5 s. */ }
  }
  requirement evidenceContractIndependentFootprintOutcome : BicycleEvidenceContract {
    subject bench : BicycleTargetBench;
    require constraint statement { language "English" /* The bench shall reconstruct ego and bicycle footprints independently from retained map-frame observations and reject missing or contradictory samples. */ }
  }
  requirement evidenceContractReplayableProvenance : BicycleEvidenceContract {
    subject bench : BicycleTargetBench;
    require constraint statement { language "English" /* The bench shall hash-bind scenario, runtime, evaluator, observation, map-runtime, and artifact identities for independent replay. */ }
  }

  part bicycleTargetBench : BicycleTargetBench;
  verification def BicycleTargetVerification {
    subject verifiedBench : BicycleTargetBench;
    objective evidenceObjective {
      verify evidenceContractConfiguredBicycleTarget;
      verify evidenceContractIndependentFootprintOutcome;
      verify evidenceContractReplayableProvenance;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : BicycleObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedObservations : BicycleObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : BicycleEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : BicycleEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapBicycleOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification bicycleTargetVerification : BicycleTargetVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> bicycleTargetBench;
  }
  part verificationSystem {
    perform bicycleTargetVerification;
  }

  dependency bicycleConfigurationRelevantToBicycleDetectionCandidate
    from evidenceContractConfiguredBicycleTarget to reqBicycleTargetResponse;
  dependency bicycleOutcomeRelevantToBicycleResponseCandidate
    from evidenceContractIndependentFootprintOutcome to reqBicycleTargetControlledResponse;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebsBicycleVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBS009HVerification::*;
    render asTreeDiagram;
  }
}
