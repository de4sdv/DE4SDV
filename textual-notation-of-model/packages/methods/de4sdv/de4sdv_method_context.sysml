/*
 * DE4SDV method context and problem statement kernel.
 *
 * This package adapts only the useful SYSMOD/SysML v2 problem-statement pattern
 * for DE4SDV. It is not a full SYSMOD implementation or vendored upstream
 * library.
 *
 * A problem statement is modeled as a requirement. A system context captures
 * the system of interest, actors, and relevant context elements for an
 * increment. DE4SDV intentionally does not introduce a generic ProjectContext
 * abstraction here; feature increments can compose problem statements,
 * stakeholders, and system context directly.
 */

package DE4SDV_MethodContext {
  doc hasRelevantArchitectureOntologyDefinition /* Reverse relevance: an incoming dependency from an architecture element (part, action,
   * or their definitions) that is derived from or traces to the requirement. Sources
   * grounded in the MemberProduct kernel lineage (resolved through the governed kernel
   * mapping, never by bare name) are excluded — configured-product traces are product-line
   * relationships, not architecture relevance. */
  comment about hasRelevantArchitectureOntologyDefinition /* The incoming-dependency mapping served from the frozen
   * records stays PartUsage/PartDefinition/ActionUsage/ActionDefinition with
   * MemberProduct-lineage exclusions. No Interface widening, stronger relation or consumer
   * rewiring. */


  doc specifiesFunctionOntologyDefinition /* Requirement-to-function relevance: a dependency from a draft requirement candidate to
   * the functional action or flow responsibility that addresses it. Relevance only — not
   * satisfaction, allocation, or verification. */
  comment about specifiesFunctionOntologyDefinition /* Existing requirement-to-function dependency/relevance signature and target filter
   * remain unchanged. No allocation, satisfaction or verification claim is introduced. */


  doc derivedRequirementsOfNeedOntologyDefinition /* Inverse navigation of derivesRequirementFromNeed over the SAME discriminator witness:
   * the need N is the design-input origin of the derived requirement R. This predicate
   * declares no new model fact; it reuses the identical DerivesFromNeed connection
   * traversed in the reverse direction, with the same lineage grounding and fail-closed
   * closure semantics. */
  comment about derivedRequirementsOfNeedOntologyDefinition /* The navigation served from the frozen records over the
   * identical DerivesFromNeed witness is unchanged; no additional model fact or executable
   * mapping. */


  doc derivesRequirementFromNeedOntologyDefinition /* Requirement R is derived from stakeholder need N. Design-input derivation; direction R
   * -> N. No satisfaction, allocation, verification, evidence, or acceptance claim.
   * Grounded in the DE4SDV application connection definition DerivesFromNeed: the Need
   * grounds the `need` end, the derived design requirement grounds the `derivedRequirement`
   * end. DE4SDV's Requirement -> Need query is inverse navigation over that native witness. */
  comment about derivesRequirementFromNeedOntologyDefinition /* The predicate signature served from the frozen records,
   * the native DerivesFromNeed witness and the inverse query direction are unchanged;
   * documentation only. */


  doc VerificationMethodOntologyDefinition /* A method used to check requirement satisfaction. Carried natively by VerificationMethod
   * metadata with the standard method-kind vocabulary (inspect, demo, test, analyze), per
   * the ADR 0009 amendment. */
  comment about VerificationMethodOntologyDefinition /* ODE4HERA requirements-management verificationMethod and standard VerificationMethodKind
   * remain the accepted external/library authority; no library copy or new method-kind
   * vocabulary. */
  comment about VerificationMethodOntologyDefinition /* Grounding record (native library adoption).
   * Two distinct representations, never merged: (1) metadata — the Systems Library
   * VerificationCases package declares metadata def VerificationMethod with
   * attribute kind : VerificationMethodKind[1..*] (inspect, analyze, demo, test);
   * models annotate verification-case steps with it, for example
   * @VerificationMethod{ kind = test; }; (2) attribute mapping — the ODE4HERA
   * requirements-management attribute verificationMethod set on requirement usages
   * records the planned method for a requirement. The metadata annotates how a
   * verification case checks; the attribute records requirement planning data. Neither
   * is a verification result, evidence status or acceptance. No library type is copied. */
  comment usesVerificationMethodVocabularyRole about VerificationMethodOntologyDefinition /* Vocabulary
   * role of the reviewed relationship usesVerificationMethod: domain VerificationCase,
   * range VerificationMethod. Native grounding: the normative SysML VerificationCases
   * library, where the VerificationMethod metadata annotating a verification case (or
   * its steps) carries the method kind. This comment records the model-resident home
   * only: no DE4SDV relationship definition, no sysml_mapping, no runtime traversal and
   * no change to the frozen VerificationCase or verifiedBy semantics. */


  doc VerificationCaseOntologyDefinition /* A planned or executed check that evaluates whether a requirement or model claim is
   * satisfied. */
  comment about VerificationCaseOntologyDefinition /* Native SysML VerificationCaseDefinition/VerificationCaseUsage (verification
   * def/verification) remain the representation. This documentation changes no traversal
   * signature served from the frozen records, and no objective, execution, result or
   * acceptance. */


  doc InterfaceOntologyDefinition /* A boundary or interaction point through which items, signals, services, or information
   * are exchanged. */
  comment about InterfaceOntologyDefinition /* Native SysML kinds remain PortDefinition/PortUsage and connection elements. This
   * documentation preserves the existing Interface meaning and does not widen
   * hasRelevantArchitecture. */


  doc PhysicalElementOntologyDefinition /* A physical, software, hardware, deployment, or platform element that realizes
   * conceptual elements or functions. */
  comment about PhysicalElementOntologyDefinition /* Native SysML kinds: PartDefinition/PartUsage in physical/software realization slices,
   * describing concrete software, hardware, deployment or platform roles. No additional
   * PhysicalElement specialization taxonomy is introduced; typing does not prove deployment
   * or execution. */


  doc LogicalElementOntologyDefinition /* A logical service, component, or responsibility grouping that realizes functions. */
  comment about LogicalElementOntologyDefinition /* Native SysML kinds: PartDefinition/PartUsage in logical-architecture slices, describing
   * technology-neutral service/component responsibilities. No additional LogicalElement
   * specialization taxonomy is introduced. */


  doc FunctionOntologyDefinition /* A behavior or transformation expected from the system or product-line architecture. */
  comment about FunctionOntologyDefinition /* Native SysML kinds: ActionDefinition/ActionUsage (action defs/usages), with
   * StateDefinition/StateUsage and behavior definitions where appropriate. No existing
   * functional element must specialize a new Function type; this is a documentation
   * umbrella. */


  doc ArchitectureElementOntologyDefinition /* Any model element used to describe system context, function, logical realization,
   * physical/software realization, interface, or behavior. */
  comment about ArchitectureElementOntologyDefinition /* Native SysML kinds: PartDefinition/PartUsage for structural constituents;
   * ActionDefinition/ActionUsage and StateDefinition/StateUsage for behavior;
   * PortDefinition/PortUsage and ConnectionDefinition/ConnectionUsage for interfaces. This
   * is a documentation umbrella, not a parallel type taxonomy. hasRelevantArchitecture
   * remains restricted to PartUsage, PartDefinition, ActionUsage and ActionDefinition;
   * Interface is not added to that executable filter. */


  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_Stakeholders::*;

  /* Re-exported so feature packages can assign `attribute :>> status =
   * ReqStatus::...` (ADR 0009) without importing the adapter directly. */
  public import ReqStatus;

  /* Re-exported so feature packages can assign `attribute :>>
   * verificationStatus = VVStatus::...` (ADR 0009 amendment) without
   * importing the adapter directly. */
  public import VVStatus;

  comment hasStakeholderVocabularyRole about EngineeringIncrement, Stakeholder /* Vocabulary
   * role: EngineeringIncrement -> Stakeholder. Existing native stakeholder
   * membership is preserved; this comment introduces no additional trace
   * slot, executable mapping, participation requirement or acceptance. */

  part def EngineeringIncrement {
    doc /* A bounded DE4SDV work package that changes, tests, or publishes engineering knowledge. */
  }

  connection def HasStakeholder {
    doc /* An engineering increment identifies a stakeholder role participating
         * in or affected by it. Domain EngineeringIncrement; range Stakeholder.
         * Vocabulary-only typed carrier: not executable traversal proof,
         * native StakeholderMembership equivalence, real-person assignment,
         * approval authority, competence or safety acceptance. */
    end increment : EngineeringIncrement;
    end stakeholderRole : Stakeholder;
  }

  part def FeatureIncrement :> EngineeringIncrement {
    doc /* An engineering increment focused on a product-line feature, common capability, or native SysML v2 variation/variant choice. */
  }

  part def NeedsRequirementsIncrement :> EngineeringIncrement {
    doc /* An engineering increment focused on needs, draft requirements, traceability, and V&V planning. */
  }

  part def SystemLayer {
    doc /* Coarse ASELCM-style layer used to frame DE4SDV increments and their environments. */
  }

  part def System1SDVProductLine :> SystemLayer {
    doc /* Configurable SDV product line and configured vehicle/software variants. */
  }

  part def System2EngineeringAndAssuranceSystem :> SystemLayer {
    doc /* DE4SDV model-based life-cycle engineering, assurance, simulation, and evidence system. */
  }

  part def System3OpenSourceGovernanceEcosystem :> SystemLayer {
    doc /* Open innovation ecosystem that governs, evolves, reviews, and improves DE4SDV. */
  }

  part def MethodStackElement {
    doc /* Method/tooling layer participating in a DE4SDV increment. */
  }

  part def SAFViewpointSelection :> MethodStackElement;
  part def SYSMODMethodFlow :> MethodStackElement;
  part def DE4SDVOntologyKernel :> MethodStackElement;
  part def SysMLv2ModelExpression :> MethodStackElement;
  part def VSSCandidateSignalCatalog :> MethodStackElement;

  part def OperationalScopeBoundary {
    doc /* Boundary separating in-scope and out-of-scope content for an increment. */
  }

  part def InScopeItem {
    doc /* Scope item included in the current increment. */
  }

  part def OutOfScopeItem {
    doc /* Scope item explicitly deferred or excluded from the current increment. */
  }

  requirement def ProblemStatement {
    doc /* The problem that is to be solved by the system or increment, modeled as a requirement. */
  }

  requirement def StakeholderNeedCandidate :> RequirementsManagementAttributeBase {
    private doc ontologyDefinition /* Stakeholder-expressed problem-space intent, before conversion into design input
     * requirements. The kernel models needs as requirement usages of
     * StakeholderNeedCandidate specializations carrying the ADR 0009 attribute set. */
    doc /* Stakeholder-expressed problem-space intent, before conversion into design-input requirements. Inherits the NRM Chapter 15 attribute set adopted via ADR 0009. */
  }

  requirement def ProductLineCommonCapabilityNeed :> StakeholderNeedCandidate {
    doc /* Need for a common product-line capability required across member products. */
  }
  requirement def EngineeringTraceabilityNeed :> StakeholderNeedCandidate {
    doc /* Need for engineering traceability, boundary visibility, and controlled scope. */
  }

  requirement def ProductLineClassificationNeed :> StakeholderNeedCandidate {
    doc /* Need for explicit feature/common-capability classification and variation modeling. */
  }

  requirement def RegulatoryVisibilityNeed :> StakeholderNeedCandidate {
    doc /* Need for visible regulatory assumptions without compliance claims. */
  }

  requirement def VerificationPlanningNeed :> StakeholderNeedCandidate {
    doc /* Need for separate controlled V&V planning attachments. */
  }

  requirement def ProductSafetyAvailabilityNeed :> StakeholderNeedCandidate {
    doc /* Need for bounded degradation and availability indication. */
  }

  requirement def RequirementCandidate :> SYSMODRequirementBase, RequirementsManagementAttributeBase {
    private doc ontologyDefinition /* A verifiable design input obligation or constraint derived from needs, standards, or
     * architecture decisions. The kernel models requirement candidates on the SYSMOD
     * requirement seam with ADR 0009 attributes. */
    doc /* A verifiable design input obligation or constraint derived from needs, standards, or architecture decisions.
         * Generic base for design-input requirement candidates before acceptance.
         * Specializes the SYSMOD requirement seam, inheriting obligation,
         * stability, and motivation metadata for requirement candidates.
         * DE4SDV candidate lifecycle semantics remain local. */
    attribute successCriteria : ScalarValues::String[0..1] {
      doc /* System verification success criteria: the observable conditions under which verification shows
           * this requirement is met. A test-verdict criterion, not an acceptance decision. */
    }
  }

  requirement def FunctionalRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for functional behavior. */
  }

  requirement def SafetyConstraintRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for safety constraints and non-activation. */
  }

  requirement def SecurityConstraintRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for security and trust-boundary constraints. */
  }

  requirement def ProductLineConstraintRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for product-line classification and variability constraints. */
  }

  requirement def TraceabilityConstraintRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for traceability and V&V planning constraints. */
  }

  comment hasAcceptanceCriterionVocabularyRole about AcceptanceCriterion /* The criterion
   * role in a native verification objective is distinguished by
   * AcceptanceCriterion typing/specialization, not a criterion name. This
   * is a test-verdict criterion, not acceptance under
   * de4sdv.acceptance.maintainer-decision.v1. No cardinality or executable
   * predicate mapping is introduced here. */

  requirement def AcceptanceCriterion {
    doc /* A condition used to decide whether a verification result, validation result, evidence artifact, or increment output is acceptable for its stated purpose. */
    /* Test-verdict criterion, not an authorized acceptance decision under
     * de4sdv.acceptance.maintainer-decision.v1. Typing supplies no result,
     * approval or acceptance; policy decisions remain separate records. */
    comment /* Kept only in the records of closed increments. New work declares no
             * AcceptanceCriterion elements: each requirement states its success criteria
             * in RequirementCandidate::successCriteria. */
  }

  requirement def EvidenceContract :> RequirementCandidate {
    doc /* A requirement usage that defines the bounded observations, acceptance
         * boundary, and retained-evidence obligations for a verification case. An
         * evidence contract is planning vocabulary, not proof that a product
         * requirement is verified. */
    /* Specialized by exactly the eight AEBS evidence-contract definitions:
     * OverrideEvidenceContract, DegradedInputEvidenceContract,
     * BicycleEvidenceContract, NominalEvidenceContractRequirement,
     * RegulatoryCriterionEvidenceContract, NonActivationEvidenceContract,
     * PedestrianEvidenceContract and PartialInterventionEvidenceContract.
     * MiddlewareAcceptanceCriterion is an AcceptanceCriterion only, so
     * acceptance-criterion typing never makes a requirement an evidence
     * contract. This specialization closure is the evidence-contract
     * population that the hasRelevantEvidenceContract discriminator lists;
     * the runtime refuses any other number of members, so a change updates
     * that check and its population test together. The existing runtime
     * dependency mapping is unchanged. */
  }

  comment hasRelevantEvidenceContractVocabularyRole about EvidenceContract /* The
   * hasRelevantEvidenceContract range is discriminated by type lineage: a
   * target requirement usage is an evidence contract if and only if its
   * definition is in the specialization closure of this kernel
   * EvidenceContract, resolved through the governed kernel mapping, never by
   * a name, prefix or verification-membership heuristic. AcceptanceCriterion
   * typing, native verify memberships and EvidenceContractTraceability
   * candidates do not qualify. Relevance only: no verification, satisfaction,
   * evidence adequacy or acceptance. Vocabulary only at this revision; the
   * runtime predicate keeps its existing dependency mapping until a reviewed
   * consumer change adopts this discriminator. */

  requirement def EvidenceContractTraceabilityRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for evidence-contract traceability to controlled boundaries. */
  }

  requirement def RegulatoryConstraintCandidate :> RequirementsManagementAttributeBase {
    private doc ontologyDefinition /* A constraint or reference derived from a standard, regulation, or homologation-
     * relevant source, with controlled source identity and no compliance claim. */
    doc /* A constraint or reference derived from a standard, regulation, or homologation-relevant source, with controlled source identity and no compliance claim. Grounds the ontology RegulatoryConstraint class and R003 derivation targets. */
  }

  part def ArchitectureDecisionRecord {
    private doc ontologyDefinition /* A reviewed architecture or method decision recorded as an ADR in Git that can serve
     * as the semantic origin of a design-input requirement. */
    doc /* A reviewed architecture or method decision recorded as an ADR in Git that can serve as the semantic origin of a design-input requirement. Grounds the ontology ArchitectureDecisionRecord class and R003 derivation targets. */
  }

  comment ArchitectureDecisionRecordVocabularyRole about ArchitectureDecisionRecord /* External
   * boundary: ADR content is external (the Git documents under
   * docs/architecture-decisions/); the model has no authority over it and does
   * not mirror it. ArchitectureDecisionRecord is only the model-resident
   * reference identity and typing role for R003 derivation origins. Referencing
   * an ADR does not make its decision accepted or its status current. */

  part def IncrementAssumption {
    doc /* A stated condition treated as true for the purpose of an increment, model, scenario, analysis, or evidence record. */
  }

  part def IncrementGap {
    doc /* A known missing trace link, missing evidence item, unresolved uncertainty, or unproven claim that must not be hidden. */
  }

  part def IncrementScope {
    doc /* Scope boundary for an engineering increment. */
  }

  part def IncrementEngineeringQuestion {
    doc /* The engineering question that an increment answers. */
  }

  part def IncrementLifecycleDecision {
    doc /* A lifecycle decision that an increment supports (accepted, deferred, or invalidated). */
  }

  part def MissingRealizationRecord {
    doc /* A record of a missing or blocked realization allocation for a conceptual element. */
  }

  part def BlockedRealizationBranchRecord {
    doc /* A record of a realization branch blocked by a source defect or gap. */
  }

  part def SourceContributionRecord {
    doc /* Record of an observable source contribution to a partial realization. */
  }

  part def SystemContext {
    doc /* Context containing the system actors, the system of interest, and their relationships. */
    part actors[*];
    part systemOfInterest;
  }

  doc AssuranceClaimOntologyDefinition /* A claim about safety, security, compliance alignment, release readiness, or fitness-
   * for-use that requires argument and evidence before acceptance. Claims are bounded and
   * never imply certification or homologation. */
  comment about AssuranceClaimOntologyDefinition /* Bounded claim vocabulary only; no generic adequacy/acceptance
   * result is introduced. The assurance argumentation kinds below add no richer
   * claim/argument/counterclaim taxonomy. */


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

  comment EvidenceArtifactVocabularyRole about EvidenceArtifactOntologyDefinition /* External
   * boundary: evidence-artifact content is external; the model has no authority
   * over it. The model owns only the typed reference role: the accepted
   * de4sdv.evidence-reference/v1 schema (case identity, artifact identity, exact
   * revision, digest, run, tested scope) and the model-resident reference
   * record RetainedExecutionRecordReference. No artifact bytes, status,
   * maturity, verdict or acceptance are mirrored, and no API element identity
   * is claimed for an artifact. */

  comment hasEvidenceVocabularyRole about EvidenceArtifactOntologyDefinition /* External boundary for hasEvidence
   * (VerificationCase to EvidenceArtifact): artifact association only, carried
   * by the case's typed de4sdv.evidence-reference/v1 record; content external, no
   * authority. The association exposes no verdict, pass, approval or acceptance
   * and implements no traversal: external data is required and an absent record
   * is never reported as an empty hop. It is not supportedByEvidence. */

  comment supportedByEvidenceVocabularyRole about AssuranceClaimOntologyDefinition /* The
   * supportedByEvidence relation (AssuranceClaim to EvidenceArtifact) records
   * one citation per cited artifact: the exact scoped claim (claim, subject,
   * configuration, conditions), the versioned evidence reference, the
   * rationale and the known limits. This is cited support, distinct from
   * hasEvidence artifact association. A claim is treated as established, or
   * acceptance is sought, only after an adequacy assessment of the evidence
   * set for the same exact scope, which reuses the cases, criteria, results,
   * references and gaps it assesses. The designated authority's scoped
   * acceptance stays a separate AcceptanceAttestationReference, with
   * exceptions kept visible. Citation, adequacy and acceptance never imply
   * each other. Vocabulary only at this revision: no runtime traversal is
   * implemented here. */

  comment hasEvidenceStatusVocabularyRole about EvidenceStatusOntologyDefinition /* Successor
   * for the legacy hasEvidenceStatus (EvidenceArtifact to EvidenceStatus)
   * predicate. Scoped verification and validation activity status is the
   * unchanged adopted VVStatus, identified with the activity's subject,
   * configuration, comparison basis and result or evidence references;
   * EvidenceStatus resolves to that pinned VVStatus and to slice-local
   * bounded outcome/disposition enums. No new universal status enum is
   * introduced. Artifact maturity, evidence-set adequacy and authority
   * acceptance stay separate, and Completed never means passed or accepted.
   * Retirement: hasEvidenceStatus takes no new model usage; consumers move to
   * this successor in a reviewed runtime change, which then retires the
   * legacy predicate (the authored ontology that declared it is removed). */

  /* Assurance argumentation kinds. A claim, its supporting arguments and its
   * counter-claims are assurance artifacts that consume verification results.
   * They are not design-input requirements: they do not derive from
   * stakeholder needs, record no verification method and are not verified by
   * verification cases. The three definitions keep the requirement keyword
   * only as the textual form of a bounded statement about a subject. They
   * deliberately do not specialize RequirementCandidate, so the Requirement
   * lineage and the requirement method checks do not apply to their usages.
   *
   * Meaning follows the approved assurance semantics of the
   * supportedByEvidence role above: an argument is cited support with
   * rationale and limits; a claim counts as established only after a scoped
   * evidence-set adequacy assessment of the same exact scope; a counter-claim
   * is a disclosed limit on the claim's scope, tied to its gap record;
   * acceptance stays a separate authority record. No richer argumentation
   * metamodel is introduced.
   */
  requirement def AssuranceClaim {
    doc /* A bounded statement about a subject, its configuration and conditions that requires argument and evidence before acceptance. It counts as established only after an adequacy assessment of the evidence set for the same exact scope; acceptance stays a separate authority record. A claim never implies certification or homologation. */
  }

  requirement def AssuranceArgument {
    doc /* Cited support for a claim: the verification cases and retained evidence it relies on, with rationale and known limits. An argument establishes neither evidence adequacy nor acceptance. */
  }

  requirement def AssuranceCounterClaim {
    doc /* A disclosed limit on the scope of a claim, tied to the gap record that keeps it open. It states what the claim must not be read to cover; it is not an obligation. */
  }
}
