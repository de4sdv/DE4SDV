/*
 * DE4SDV ontology validation-rule homes (O4 Wave A).
 *
 * Owner decision 2026-10-06: each validation rule of the basic ontology
 * (approach/framework/ontology/de4sdv-basic-ontology.yaml, validation_rules
 * DE4SDV-ONT-R001 to DE4SDV-ONT-R010) gets one model-resident home. Each home
 * is a package-owned constraint usage whose first owned documentation is the
 * rule statement (normalized-exact) and whose second is its enforcement note.
 *
 * The constraint usages are rule declarations only: they carry no Boolean
 * expression, are not asserted on any element, and evaluate nothing. Rule
 * enforcement stays where each enforcement note says it is (scripts, tests and
 * reviews). The YAML entries remain in place; retiring them is a separate,
 * later change. Since O4 Wave C1 the R003 origin and exclusion groundings are
 * read from the ontologyRuleR003 home below (see its reader comment). No
 * compliance, certification or acceptance claim is made.
 *
 * This package also records the vocabulary-only role of IncrementSize. It
 * lives here, not in DE4SDV_MethodProcess, so the method-process view, which
 * exposes every DE4SDV_MethodProcess member, is not changed by this note.
 */

package DE4SDV_OntologyValidationRules {
  private import DE4SDV_MethodProcess::*;

  constraint ontologyRuleR001 {
    doc /* Every Feature shall distinguish at least one member product from another member
     * product. */
    doc /* Rule DE4SDV-ONT-R001. Enforced by: Kernel rule (a feature stays a
     * ProductLineFeatureCandidate until variability is shown) plus feature-catalogue
     * review. */
  }

  constraint ontologyRuleR002 {
    doc /* Every FeatureIncrement shall identify selected SAF viewpoints and out-of-scope
     * viewpoints. */
    doc /* Rule DE4SDV-ONT-R002. Enforced by: Increment framing review against the kernel
     * viewpoint selections. */
  }

  constraint ontologyRuleR003 {
    doc /* Every Requirement in a feature increment shall trace to at least one Need,
     * RegulatoryConstraint, or ArchitectureDecisionRecord. */
    doc /* Rule DE4SDV-ONT-R003. Enforced by: scripts/check_model_sync.py sync point 6 resolves
     * each derivation target to its modeled type (including specialization closure) and
     * accepts only targets whose semantic type grounds Need (StakeholderNeedCandidate
     * specializations), RegulatoryConstraint (RegulatoryConstraintCandidate
     * specializations), or ArchitectureDecisionRecord (ArchitectureDecisionRecord
     * specializations); identifier prefixes are never consulted. Remaining
     * semantic-strength questions stay with requirements QA review. */
    doc /* Origin groundings: Need: requirement def StakeholderNeedCandidate in
     * textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml;
     * RegulatoryConstraint: requirement def RegulatoryConstraintCandidate in
     * textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml;
     * ArchitectureDecisionRecord: part def ArchitectureDecisionRecord in
     * textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml.
     * Exclusion groundings: ProblemStatement: requirement def ProblemStatement in
     * textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml. */
    comment /* Reader: since O4 Wave C1, scripts/check_model_sync.py sync point 6 reads the
     * origin and exclusion groundings above from this rule home, not from the ontology
     * YAML. Their text format is fixed and drift fails closed. A test keeps them equal to
     * the YAML validation_rules entry until that entry is retired. */
  }

  constraint ontologyRuleR004 {
    doc /* Every compliance-oriented claim shall be marked as draft, planned, example,
     * verified, or accepted. */
    doc /* Rule DE4SDV-ONT-R004. Enforced by: Verification-model invariant tests (product-claim
     * bans) and evidence-register status review. */
  }

  constraint ontologyRuleR005 {
    doc /* Common capabilities shall not be modeled as Features unless they distinguish member
     * products. */
    doc /* Rule DE4SDV-ONT-R005. Enforced by: Kernel ProductLineCharacteristic specialization
     * structure plus product-line classification review. */
  }

  constraint ontologyRuleR006 {
    doc /* Every VerificationCase shall identify a verification method and at least one
     * acceptance criterion or open gap. */
    doc /* Rule DE4SDV-ONT-R006. Enforced by: ADR 0009 amendment attributes (VerificationMethod
     * metadata, verificationStatus) plus capability-agnostic verification-model invariant
     * tests. */
  }

  constraint ontologyRuleR007 {
    doc /* Every ValidationScenario shall identify the Need or stakeholder concern whose
     * fitness-for-use it evaluates. */
    doc /* Rule DE4SDV-ONT-R007. Enforced by: V&V planning review. */
  }

  constraint ontologyRuleR008 {
    doc /* Every EvidenceArtifact shall carry an explicit status value. */
    doc /* Rule DE4SDV-ONT-R008. Enforced by: ADR 0009 amendment (VVStatus in the model);
     * evidence YAML records no longer duplicate method or evidence_status columns. */
  }

  constraint ontologyRuleR009 {
    doc /* Every AssuranceClaim shall be supported by evidence or recorded as an open gap. */
    doc /* Rule DE4SDV-ONT-R009. Enforced by: Argumentation-assurance viewpoint review. */
  }

  constraint ontologyRuleR010 {
    doc /* Product-line variation points represented in SysML v2 shall use native variation
     * with owned variant usages; do not substitute a generic variation-point part
     * taxonomy. */
    doc /* Rule DE4SDV-ONT-R010. Enforced by: Kernel guard doc plus variability-configuration
     * tests. */
  }

  comment IncrementSizeVocabularyRole about IncrementSize /* Vocabulary only (O4 W3,
   * KEEP_VOCABULARY_ONLY). IncrementSize and its literals XS, S, M and L stay
   * model-resident as size-guidance labels for increment planning. They are never
   * promoted to semantic authority: no sizing rule, gate, completion claim or runtime
   * traversal is derived from them. */
}
