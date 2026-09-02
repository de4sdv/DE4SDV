/* INC-AEBS-009G pedestrian-target evidence contract; no product verification claim. */
package DE4SDV_AEBS009GVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  enum def PedestrianEvidenceOutcome {
    passBoundedTargetResponse;
    failConfiguredOutcome;
    inconclusiveCoverage;
    errorEvidence;
  }
  item def PedestrianObservationSet;
  item def PedestrianEvaluation {
    attribute outcome : PedestrianEvidenceOutcome;
  }
  calc def MapPedestrianOutcomeToVerdict {
    in outcome : PedestrianEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == PedestrianEvidenceOutcome::passBoundedTargetResponse? VerdictKind::pass
      else if outcome == PedestrianEvidenceOutcome::failConfiguredOutcome? VerdictKind::fail
      else if outcome == PedestrianEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def PedestrianTargetBench;
  requirement def PedestrianEvidenceContract;
  requirement evidenceContractConfiguredPedestrianTarget : PedestrianEvidenceContract {
    subject bench : PedestrianTargetBench;
    require constraint statement { language "English" /* The bench shall bind the configured pedestrian trajectory, geometry, timing, and exact bench identity: crossing speed 1.5 m/s, a closed observation window of 2.0 s, and map-frame source observations no older than 0.5 s. */ }
  }
  requirement evidenceContractIndependentFootprintOutcome : PedestrianEvidenceContract {
    subject bench : PedestrianTargetBench;
    require constraint statement { language "English" /* The bench shall reconstruct ego and pedestrian footprints independently from retained map-frame observations and reject missing or contradictory samples. */ }
  }
  requirement evidenceContractReplayableProvenance : PedestrianEvidenceContract {
    subject bench : PedestrianTargetBench;
    require constraint statement { language "English" /* The bench shall hash-bind scenario, runtime, evaluator, observation, map-runtime, and artifact identities for independent replay. */ }
  }

  part pedestrianTargetBench : PedestrianTargetBench;
  verification def PedestrianTargetVerification {
    subject verifiedBench : PedestrianTargetBench;
    objective evidenceObjective {
      verify evidenceContractConfiguredPedestrianTarget;
      verify evidenceContractIndependentFootprintOutcome;
      verify evidenceContractReplayableProvenance;
    }
    action collectData {
      @VerificationMethod{ kind = test; }
      out item retainedObservations : PedestrianObservationSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in item retainedObservations : PedestrianObservationSet = collectData.retainedObservations;
      out item replayedEvaluation : PedestrianEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : PedestrianEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapPedestrianOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification pedestrianTargetVerification : PedestrianTargetVerification {
    @VerificationMethod{ kind = (test, analyze); }
    subject verifiedBench :> pedestrianTargetBench;
  }
  part verificationSystem {
    perform pedestrianTargetVerification;
  }

  dependency pedestrianConfigurationRelevantToPedestrianDetectionCandidate
    from evidenceContractConfiguredPedestrianTarget to reqPedestrianTargetResponse;
  dependency pedestrianOutcomeRelevantToPedestrianResponseCandidate
    from evidenceContractIndependentFootprintOutcome to reqPedestrianTargetControlledResponse;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebsPedestrianVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBS009GVerification::*;
    render asTreeDiagram;
  }
}
