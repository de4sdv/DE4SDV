/* Scoped assurance records; draft pending exact-head privileged Syside validation.
 * Item definitions represent identifiable review/activity records, not executable
 * cases or product requirements. Records use native item definitions and
 * reference usages; they do not turn referenced observations into executions.
 * External evidence/reference contract remains de4sdv.evidence-reference/v1.
 */
package DE4SDV_ScopedAssurance {
  doc AssuranceClaimOntologyDefinition /* A claim about safety, security, compliance alignment, release readiness, or fitness-
   * for-use that requires argument and evidence before acceptance. Claims are bounded and
   * never imply certification or homologation. */
  comment about AssuranceClaimOntologyDefinition /* Bounded claim vocabulary only; no claim/argument/counterclaim taxonomy or generic
   * adequacy/acceptance result is introduced. Existing scoped-assurance records and their
   * boundaries stay intact. */


  doc EvidenceStatusOntologyDefinition /* Lifecycle status for evidence and verification results. DE4SDV does not define its own
   * status vocabulary: requirement verification status uses the upstream VVStatus enum, and
   * bounded evidence outcomes/dispositions use slice-local enums such as
   * MiddlewareEvidenceOutcome and MiddlewareEvidenceDisposition. */
  comment about EvidenceStatusOntologyDefinition /* The upstream VVStatus enum and slice-local bounded outcomes/dispositions remain
   * distinct authorities. No status copy, new enum, lifecycle-result collapse or policy
   * acceptance is introduced. */


  doc EvidenceArtifactOntologyDefinition /* A reviewable artifact that supports a verification, validation, assurance, or release
   * decision. */
  comment about EvidenceArtifactOntologyDefinition /* Artifact contents remain in evidence registers, retained files and typed references,
   * not in this documentation. Definition residence does not establish artifact
   * availability, maturity, adequacy or acceptance. */


  private import ScalarValues::*;
  private import DE4SDV_SYSMODAdapter::VVStatus;
  private import DE4SDV_MethodConformance::*;

  comment EvidenceArtifactVocabularyRole about EvidenceArtifactOntologyDefinition /* External
   * boundary: evidence-artifact content is external; the model has no authority
   * over it. The model owns only the typed reference role: the accepted
   * de4sdv.evidence-reference/v1 schema (case identity, artifact identity, exact
   * revision, digest, run, tested scope) and the model-resident reference
   * records RetainedExecutionRecordReference and EvidenceSupportCitation
   * evidenceRef. No artifact bytes, status, maturity, verdict or acceptance are
   * mirrored, and no API element identity is claimed for an artifact. */

  comment hasEvidenceVocabularyRole about EvidenceArtifactOntologyDefinition /* External boundary for hasEvidence
   * (VerificationCase to EvidenceArtifact): artifact association only, carried
   * by the case's typed de4sdv.evidence-reference/v1 record; content external, no
   * authority. The association exposes no verdict, pass, approval or acceptance
   * and implements no traversal: external data is required and an absent record
   * is never reported as an empty hop. It is not supportedByEvidence. */

  comment supportedByEvidenceVocabularyRole about EvidenceSupportCitation, ScopedEvidenceAdequacyAssessment /* The
   * supportedByEvidence relation (AssuranceClaim to EvidenceArtifact) is
   * represented by one EvidenceSupportCitation per cited artifact: the exact
   * scoped claim (claim, subject, configuration, conditions), the versioned
   * evidence reference, the rationale and the known limits. This is cited
   * support, distinct from hasEvidence artifact association. A claim is
   * treated as established, or acceptance is sought, only after a
   * ScopedEvidenceAdequacyAssessment of the evidence set for the same exact
   * scope, which reuses the cases, criteria, results, references and gaps it
   * assesses. The designated authority's scoped acceptance stays a separate
   * AcceptanceAttestationReference, with exceptions kept visible. Citation,
   * adequacy and acceptance never imply each other. Vocabulary only at this
   * revision: no runtime traversal is implemented here. */

  comment hasEvidenceStatusVocabularyRole about ScopedVVActivityRecord /* Successor
   * for the legacy hasEvidenceStatus (EvidenceArtifact to EvidenceStatus)
   * predicate. Scoped verification and validation activity status is the
   * unchanged adopted VVStatus on ScopedVVActivityRecord status, identified
   * with its subject, configuration, activity, comparison basis and result or
   * evidence references; EvidenceStatus resolves to that pinned VVStatus and
   * to slice-local bounded outcome/disposition enums. No new universal status
   * enum is introduced. Artifact maturity, evidence-set adequacy and authority
   * acceptance stay separate, and Completed never means passed or accepted.
   * Retirement: hasEvidenceStatus takes no new model usage; consumers move to
   * this successor in a reviewed runtime change, which then retires the
   * legacy predicate (the authored ontology that declared it is removed). */

  item def EvidenceSupportCitation {
    doc /* supportedByEvidence cites one identified artifact as support for an
     * exact scoped claim, with rationale and known limitations. Neither this
     * citation nor hasEvidence (case-to-artifact association) asserts adequacy,
     * satisfaction, a passing result, or acceptance. Evidence bytes and artifact
     * maturity remain external. Scope identifiers must match without inference. */
    attribute id : String;
    attribute claim : String;
    attribute subjectIdentity : String;
    attribute configuration : String;
    attribute conditions : String[*];
    attribute evidenceRef : String;
    attribute rationale : String;
    attribute limitations : String[*];
  }

  item def ScopedVVActivityRecord {
    doc /* One explicitly scoped verification OR validation activity. Applicable
     * across needs, requirements, designs, production outputs, system elements,
     * integrated systems and artifacts without inheriting requirement attributes.
     * Native need/requirement verificationStatus attachments remain unchanged.
     * Results and evidence are references to retained external records, not a
     * second result/evidence store; native VerdictKind execution values remain
     * distinct from this activity's status. Artifact maturity is not this status.
     * Completed includes necessary result approval, but never infers PASS or
     * designated-authority acceptance. CompletedUnsuccessful could not complete;
     * CompletedFailed completed with technical failure; CompletedPassed completed
     * successfully against the activity basis only, not a broader scoped claim. */
    attribute id : String;
    attribute subjectIdentity : String;
    attribute configuration : String;
    attribute conditions : String[*];
    attribute activityKind : String;
    assert constraint activityKindVocabulary {
      activityKind == "verification" or activityKind == "validation"
    }
    attribute lifecycleContext : String;
    attribute comparisonBasis : String;
    attribute criteria : String[1..*];
    attribute status : VVStatus;
    assert constraint adoptedStatusVocabulary {
      status == VVStatus::NotStarted or status == VVStatus::InProgress or
      status == VVStatus::Completed or status == VVStatus::CompletedUnsuccessful or
      status == VVStatus::CompletedFailed or status == VVStatus::CompletedPassed
    }
    attribute caseIdentity : String;
    attribute resultRefs : String[*];
    attribute evidenceRefs : String[*];
    attribute responsibleActor : String;
    attribute resultApprovalRequired : Boolean;
    attribute resultApprovalRef : String[0..1];
    ref item retainedExecutions : RetainedExecutionRecordReference[*];
    ref item acceptanceReferences : AcceptanceAttestationReference[*];
  }

  item def ScopedEvidenceAdequacyAssessment {
    doc /* Proportionate evidence-SET assessment for this exact claim, subject,
     * configuration, conditions and agreed criteria. Required before presenting
     * a claim as established or seeking acceptance; not a universal sufficiency
     * verdict on each artifact. Reuse cases, criteria, executions, evidence and
     * gap identities. Coverage, confidence and rigor bases, contrary results,
     * discrepancies, unresolved gaps, assessor, conclusion and reasoning must
     * remain explicit. An adequate set can establish a negative conclusion.
     * supportsClaim records the assessor's scoped conclusion, not checker truth.
     * Accepted exceptions stay visible; neither assessment nor acceptance turns
     * exceptions or generic Completed status into unqualified satisfaction.
     * AcceptanceAttestationReference remains a separate designated-authority
     * decision reference, not the assessor's conclusion or result approval. */
    attribute id : String;
    attribute claim : String;
    attribute subjectIdentity : String;
    attribute configuration : String;
    attribute conditions : String[*];
    attribute comparisonBasis : String;
    attribute criteria : String[1..*];
    attribute agreementRef : String;
    attribute coverageBasis : String;
    attribute confidenceBasis : String;
    attribute rigorBasis : String;
    attribute evidenceRefs : String[*];
    attribute resultRefs : String[*];
    attribute activityRefs : String[*];
    attribute caseRefs : String[*];
    attribute limitations : String[*];
    attribute contraryResultRefs : String[*];
    attribute discrepancyRefs : String[*];
    attribute gapRefs : String[*];
    attribute assessor : String;
    attribute adequateForScope : Boolean;
    attribute supportsClaim : Boolean;
    attribute conclusion : String;
    attribute reasoning : String;
    ref item activities : ScopedVVActivityRecord[*];
    ref item citations : EvidenceSupportCitation[*];
    ref item retainedExecutions : RetainedExecutionRecordReference[*];
    ref item acceptanceReferences : AcceptanceAttestationReference[*];
  }
}
