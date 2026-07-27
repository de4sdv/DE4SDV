/* INC-AEBS-009I fail-closed criterion trace model. Controlled source identity does not establish applicability or a regulatory pass. */
package DE4SDV_AEBS009IVerification {
  private import VerificationCases::*;
  private import VerificationMethodKind::*;
  private import DE4SDV_AEBSNeedsRequirements::Features::AEBS::NeedsRequirements::*;
  item def Retained009ICriterionEvidence;
  item def Replayed009ICriterionEvaluation;
  part def RegulatoryCriterionBench009I;
  requirement def EvidenceContract009I;
  requirement evidenceContract009ISourceIdentity : EvidenceContract009I { subject bench : RegulatoryCriterionBench009I; require constraint { doc /* A source-backed evaluation shall bind the controlled public-safe source identifier, revision/amendment state, digest, clause identity, and an explicit applicability disposition; unresolved applicability cannot pass. */ } }
  requirement evidenceContract009IApplicableCriterion : EvidenceContract009I { subject bench : RegulatoryCriterionBench009I; require constraint { doc /* Every selected quantified criterion shall preserve clause provenance, units, conditions, tolerance, uncertainty treatment, and configuration applicability without authority interpretation by the bench. */ } }
  requirement evidenceContract009IMeasurementTrace : EvidenceContract009I { subject bench : RegulatoryCriterionBench009I; require constraint { doc /* Each evaluated criterion shall trace to replayable raw observations, processing steps, unit conversion, interpolation rule, and boundary decision. */ } }
  requirement evidenceContract009IProvenance : EvidenceContract009I { subject bench : RegulatoryCriterionBench009I; require constraint { doc /* Source metadata, criterion mapping, tested configuration, runtime, evaluator, and retained artifacts shall be immutable and hash-bound. */ } }
  requirement evidenceContract009IConfigurationBoundedVerdict : EvidenceContract009I { subject bench : RegulatoryCriterionBench009I; require constraint { doc /* The verdict shall be limited to the exact tested configuration; missing prescribed conditions, target fidelity, uncertainty, repetitions, or source control shall be inconclusive or error rather than pass. */ } }
  part configurationBoundedCriterionBench009I : RegulatoryCriterionBench009I;
  verification def RegulatoryCriterionVerification009I {
    subject verifiedBench : RegulatoryCriterionBench009I;
    objective evidenceObjective009I {
      verify evidenceContract009ISourceIdentity;
      verify evidenceContract009IApplicableCriterion;
      verify evidenceContract009IMeasurementTrace;
      verify evidenceContract009IProvenance;
      verify evidenceContract009IConfigurationBoundedVerdict;
    }
    action collectData { @VerificationMethod{ kind = inspect; } out item retainedObservations : Retained009ICriterionEvidence; }
    action processData { @VerificationMethod{ kind = analyze; } in item retainedObservations : Retained009ICriterionEvidence = collectData.retainedObservations; out item replayedEvaluation : Replayed009ICriterionEvaluation; }
    action evaluateData { @VerificationMethod{ kind = analyze; } in item replayedEvaluation : Replayed009ICriterionEvaluation = processData.replayedEvaluation; out verdict : VerdictKind; }
    return verdict : VerdictKind = evaluateData.verdict;
  }
  verification configurationBoundedCriterionVerification009I : RegulatoryCriterionVerification009I { @VerificationMethod{ kind = (inspect, analyze); } subject verifiedBench :> configurationBoundedCriterionBench009I; }
  part verificationSystem009I { perform configurationBoundedCriterionVerification009I; }
  dependency sourceControlRelevantToRegulatoryVisibilityNeed from evidenceContract009ISourceIdentity to needVisibleRegulatoryAssumptions;
}
