/* INC-AEBS-009I configuration-bounded criterion trace; compliance is always withheld. */
package DE4SDV_AEBSRegulatoryCriterionVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import ScalarValues::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  enum def RegulatoryCriterionScenarioIdentity {
    pedestrianCriterion;
    bicycleCriterion;
  }
  enum def RegulatoryCriterionEvidenceOutcome {
    passBoundedCriterion;
    failBoundedCriterion;
    inconclusiveApplicabilityOrEvidence;
    errorEvidence;
  }
  item def ControlledCriterionIdentity {
    attribute sourceId : String;
    attribute sourceOriginalSha256 : String;
    attribute sourceMetadataPath : String;
    attribute criteriaPath : String;
    attribute evaluatorPath : String;
  }
  item controlledCriterionIdentity : ControlledCriterionIdentity {
    attribute :>> sourceId = "E/ECE/TRANS/505/Rev.3/Add.151/Rev.2";
    attribute :>> sourceOriginalSha256 = "dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de";
    attribute :>> sourceMetadataPath = "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml";
    attribute :>> criteriaPath = "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-criteria.yaml";
    attribute :>> evaluatorPath = "scripts/aebs_regulatory_criteria.py";
  }
  item def RegulatoryCriterionEvidenceSet {
    attribute sourceOriginalSha256 : String;
    attribute testedConfigurationIdentity : String;
    attribute measurementArtifactSha256 : String;
  }
  item def RegulatoryCriterionEvaluation {
    attribute scenario : RegulatoryCriterionScenarioIdentity;
    attribute outcome : RegulatoryCriterionEvidenceOutcome;
  }
  calc def MapRegulatoryCriterionOutcomeToVerdict {
    in outcome : RegulatoryCriterionEvidenceOutcome;
    return verdict : VerdictKind =
      if outcome == RegulatoryCriterionEvidenceOutcome::passBoundedCriterion? VerdictKind::pass
      else if outcome == RegulatoryCriterionEvidenceOutcome::failBoundedCriterion? VerdictKind::fail
      else if outcome == RegulatoryCriterionEvidenceOutcome::errorEvidence? VerdictKind::error
      else VerdictKind::inconclusive;
  }

  part def RegulatoryCriterionBench {
    attribute scenario : RegulatoryCriterionScenarioIdentity;
  }
  requirement def RegulatoryCriterionEvidenceContract;
  requirement evidenceContractSourceIdentity : RegulatoryCriterionEvidenceContract {
    subject bench : RegulatoryCriterionBench;
    require constraint statement { language "English" /* The bench shall bind controlled source E/ECE/TRANS/505/Rev.3/Add.151/Rev.2, original SHA-256 dc9cc84498dcae8f0888067ad3967fb5a346e814bc2f19128987a654c8a193de, source metadata, criterion map, evaluator identity, and an explicit applicability disposition. */ }
  }
  requirement evidenceContractPedestrianApplicableCriterion : RegulatoryCriterionEvidenceContract {
    subject bench : RegulatoryCriterionBench;
    require constraint statement { language "English" /* For the pedestrian scenario only, the bench shall preserve the selected pedestrian-target criterion provenance, units, prescribed conditions, tolerance, uncertainty treatment, repeated-run rule, and tested configuration without making an authority interpretation. */ }
  }
  requirement evidenceContractBicycleApplicableCriterion : RegulatoryCriterionEvidenceContract {
    subject bench : RegulatoryCriterionBench;
    require constraint statement { language "English" /* For the bicycle scenario only, the bench shall preserve the selected bicycle-target criterion provenance, units, prescribed conditions, tolerance, uncertainty treatment, repeated-run rule, and tested configuration without making an authority interpretation. */ }
  }
  requirement evidenceContractMeasurementTrace : RegulatoryCriterionEvidenceContract {
    subject bench : RegulatoryCriterionBench;
    require constraint statement { language "English" /* The bench shall trace each bounded result to replayable observations, processing steps, unit conversion, next-higher-speed selection, repeated-run evidence, and boundary decision. */ }
  }
  requirement evidenceContractProvenance : RegulatoryCriterionEvidenceContract {
    subject bench : RegulatoryCriterionBench;
    require constraint statement { language "English" /* The bench shall hash-bind source metadata, criterion mapping, tested configuration, runtime, evaluator, measurements, and retained artifacts. */ }
  }
  requirement evidenceContractConfigurationBoundedVerdict : RegulatoryCriterionEvidenceContract {
    subject bench : RegulatoryCriterionBench;
    require constraint statement { language "English" /* The bench shall limit the verdict to one exact tested configuration. Missing applicability, prescribed conditions, target fidelity, uncertainty, repetitions, source control, or provenance shall be inconclusive or error. Compliance, certification, homologation, and type approval remain withheld. */ }
  }

  part pedestrianCriterionBench : RegulatoryCriterionBench {
    attribute :>> scenario = RegulatoryCriterionScenarioIdentity::pedestrianCriterion;
  }
  part bicycleCriterionBench : RegulatoryCriterionBench {
    attribute :>> scenario = RegulatoryCriterionScenarioIdentity::bicycleCriterion;
  }

  verification def PedestrianCriterionVerification {
    subject verifiedBench : RegulatoryCriterionBench;
    objective pedestrianEvidenceObjective {
      verify evidenceContractSourceIdentity;
      verify evidenceContractPedestrianApplicableCriterion;
      verify evidenceContractMeasurementTrace;
      verify evidenceContractProvenance;
      verify evidenceContractConfigurationBoundedVerdict;
    }
    action collectData {
      @VerificationMethod{ kind = inspect; }
      out item retainedObservations : RegulatoryCriterionEvidenceSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : RegulatoryCriterionScenarioIdentity = verifiedBench.scenario;
      in item retainedObservations : RegulatoryCriterionEvidenceSet = collectData.retainedObservations;
      out item replayedEvaluation : RegulatoryCriterionEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : RegulatoryCriterionEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapRegulatoryCriterionOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification def BicycleCriterionVerification {
    subject verifiedBench : RegulatoryCriterionBench;
    objective bicycleEvidenceObjective {
      verify evidenceContractSourceIdentity;
      verify evidenceContractBicycleApplicableCriterion;
      verify evidenceContractMeasurementTrace;
      verify evidenceContractProvenance;
      verify evidenceContractConfigurationBoundedVerdict;
    }
    action collectData {
      @VerificationMethod{ kind = inspect; }
      out item retainedObservations : RegulatoryCriterionEvidenceSet;
    }
    action processData {
      @VerificationMethod{ kind = analyze; }
      in scenarioIdentity : RegulatoryCriterionScenarioIdentity = verifiedBench.scenario;
      in item retainedObservations : RegulatoryCriterionEvidenceSet = collectData.retainedObservations;
      out item replayedEvaluation : RegulatoryCriterionEvaluation;
    }
    action evaluateData {
      @VerificationMethod{ kind = analyze; }
      in item replayedEvaluation : RegulatoryCriterionEvaluation = processData.replayedEvaluation;
      out verdict : VerdictKind = MapRegulatoryCriterionOutcomeToVerdict(replayedEvaluation.outcome);
    }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification pedestrianCriterionVerification : PedestrianCriterionVerification {
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> pedestrianCriterionBench;
  }
  verification bicycleCriterionVerification : BicycleCriterionVerification {
    @VerificationMethod{ kind = (inspect, analyze); }
    subject verifiedBench :> bicycleCriterionBench;
  }
  part verificationSystem {
    perform pedestrianCriterionVerification;
    perform bicycleCriterionVerification;
  }

  dependency sourceControlRelevantToRegulatoryVisibilityNeed
    from evidenceContractSourceIdentity to needVisibleRegulatoryAssumptions;
  dependency pedestrianCriterionRelevantToPedestrianDetectionCandidate
    from evidenceContractPedestrianApplicableCriterion to reqPedestrianTargetResponse;
  dependency pedestrianCriterionRelevantToPedestrianResponseCandidate
    from evidenceContractPedestrianApplicableCriterion to reqPedestrianTargetControlledResponse;
  dependency bicycleCriterionRelevantToBicycleDetectionCandidate
    from evidenceContractBicycleApplicableCriterion to reqBicycleTargetResponse;
  dependency bicycleCriterionRelevantToBicycleResponseCandidate
    from evidenceContractBicycleApplicableCriterion to reqBicycleTargetControlledResponse;

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebsRegulatoryCriterionVerificationAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBSRegulatoryCriterionVerification::*;
    render asTreeDiagram;
  }
}
