/* INC-AEBS-009I configuration-bounded criterion trace; compliance is always withheld. */
package DE4SDV_AEBS009IVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import ScalarValues::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;

  enum def ScenarioIdentity009I {
    pedestrianCriterion;
    bicycleCriterion;
  }
  enum def EvidenceOutcome009I {
    passBoundedCriterion;
    failBoundedCriterion;
    inconclusiveApplicabilityOrEvidence;
    errorEvidence;
  }
  item def ControlledCriterionIdentity009I {
    attribute sourceId : String;
    attribute sourceOriginalSha256 : String;
    attribute sourceMetadataPath : String;
    attribute criteriaPath : String;
    attribute evaluatorPath : String;
  }
  item controlledCriterionIdentity009I : ControlledCriterionIdentity009I {
    attribute :>> sourceId = "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2";
    attribute :>> sourceOriginalSha256 = "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de";
    attribute :>> sourceMetadataPath = "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml";
    attribute :>> criteriaPath = "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-criteria.yaml";
    attribute :>> evaluatorPath = "scripts/aebs_regulatory_criteria.py";
  }
  item def Retained009ICriterionEvidence {
    attribute sourceOriginalSha256 : String;
    attribute testedConfigurationIdentity : String;
    attribute measurementArtifactSha256 : String;
  }
  item def Replayed009ICriterionEvaluation {
    attribute scenario : ScenarioIdentity009I;
    attribute outcome : EvidenceOutcome009I;
  }
  calc def Map009IOutcomeToVerdict {
    in outcome : EvidenceOutcome009I;
    return verdict : VerdictKind =
      if outcome == EvidenceOutcome009I::passBoundedCriterion? VerdictKind::pass
      else if outcome == EvidenceOutcome009I::failBoundedCriterion? VerdictKind::fail
      else if outcome == EvidenceOutcome009I::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def RegulatoryCriterionBench009I {
    attribute scenario : ScenarioIdentity009I;
  }
  requirement def EvidenceContract009I;
  requirement evidenceContract009ISourceIdentity : EvidenceContract009I {
    subject bench : RegulatoryCriterionBench009I;
    require constraint { doc /* The bench shall bind controlled source E/ECE/TRANS/505/Rev.3/Add.151/Rev.2, original SHA-256 dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de, source metadata, criterion map, evaluator identity, and an explicit applicability disposition. */ }
  }
  requirement evidenceContract009IPedestrianApplicableCriterion : EvidenceContract009I {
    subject bench : RegulatoryCriterionBench009I;
    require constraint { doc /* For the pedestrian scenario only, the bench shall preserve the selected pedestrian-target criterion provenance, units, prescribed conditions, tolerance, uncertainty treatment, repeated-run rule, and tested configuration without making an authority interpretation. */ }
  }
  requirement evidenceContract009IBicycleApplicableCriterion : EvidenceContract009I {
    subject bench : RegulatoryCriterionBench009I;
    require constraint { doc /* For the bicycle scenario only, the bench shall preserve the selected bicycle-target criterion provenance, units, prescribed conditions, tolerance, uncertainty treatment, repeated-run rule, and tested configuration without making an authority interpretation. */ }
  }
  requirement evidenceContract009IMeasurementTrace : EvidenceContract009I {
    subject bench : RegulatoryCriterionBench009I;
    require constraint { doc /* The bench shall trace each bounded result to replayable observations, processing steps, unit conversion, next-higher-speed selection, repeated-run evidence, and boundary decision. */ }
  }
  requirement evidenceContract009IProvenance : EvidenceContract009I {
    subject bench : RegulatoryCriterionBench009I;
    require constraint { doc /* The bench shall hash-bind source metadata, criterion mapping, tested configuration, runtime, evaluator, measurements, and retained artifacts. */ }
  }
  requirement evidenceContract009IConfigurationBoundedVerdict : EvidenceContract009I {
    subject bench : RegulatoryCriterionBench009I;
    require constraint { doc /* The bench shall limit the verdict to one exact tested configuration. Missing applicability, prescribed conditions, target fidelity, uncertainty, repetitions, source control, or provenance shall be inconclusive or error. Compliance, certification, homologation, and type approval remain withheld. */ }
  }

  part pedestrianCriterionBench009I : RegulatoryCriterionBench009I {
    attribute :>> scenario = ScenarioIdentity009I::pedestrianCriterion;
  }
  part bicycleCriterionBench009I : RegulatoryCriterionBench009I {
    attribute :>> scenario = ScenarioIdentity009I::bicycleCriterion;
  }

  verification def RegulatoryCriterionVerification009I {
    subject verifiedBench : RegulatoryCriterionBench009I;
    objective evidenceObjective009I {
      verify evidenceContract009ISourceIdentity;
      verify evidenceContract009IPedestrianApplicableCriterion;
      verify evidenceContract009IBicycleApplicableCriterion;
      verify evidenceContract009IMeasurementTrace;
      verify evidenceContract009IProvenance;
      verify evidenceContract009IConfigurationBoundedVerdict;
    }
    action collectData {
      @VerificationMethod{ kind = inspect; }
      out item retainedObservations : Retained009ICriterionEvidence;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : ScenarioIdentity009I = verifiedBench.scenario;
      in item retainedObservations : Retained009ICriterionEvidence = collectData.retainedObservations;
      out item replayedEvaluation : Replayed009ICriterionEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : Replayed009ICriterionEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = Map009IOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification pedestrianCriterionVerification009I : RegulatoryCriterionVerification009I {
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> pedestrianCriterionBench009I;
  }
  verification bicycleCriterionVerification009I : RegulatoryCriterionVerification009I {
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> bicycleCriterionBench009I;
  }
  part verificationSystem009I {
    perform pedestrianCriterionVerification009I;
    perform bicycleCriterionVerification009I;
  }

  dependency sourceControlRelevantToRegulatoryVisibilityNeed
    from evidenceContract009ISourceIdentity to needVisibleRegulatoryAssumptions;
  dependency pedestrianCriterionRelevantToPedestrianDetectionCandidate
    from evidenceContract009IPedestrianApplicableCriterion to reqPedestrianTargetResponse;
  dependency pedestrianCriterionRelevantToPedestrianResponseCandidate
    from evidenceContract009IPedestrianApplicableCriterion to reqPedestrianTargetControlledResponse;
  dependency bicycleCriterionRelevantToBicycleDetectionCandidate
    from evidenceContract009IBicycleApplicableCriterion to reqBicycleTargetResponse;
  dependency bicycleCriterionRelevantToBicycleResponseCandidate
    from evidenceContract009IBicycleApplicableCriterion to reqBicycleTargetControlledResponse;
}
