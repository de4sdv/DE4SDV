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
  doc hasRelevantArchitecture /* Reverse relevance: an incoming dependency from an architecture element (part, action,
   * or their definitions) that is derived from or traces to the requirement. Sources
   * grounded in the MemberProduct kernel lineage (resolved through the governed kernel
   * mapping, never by bare name) are excluded — configured-product traces are product-line
   * relationships, not architecture relevance. */
  comment about hasRelevantArchitecture /* Existing frozen O3 incoming-dependency mapping stays
   * PartUsage/PartDefinition/ActionUsage/ActionDefinition with MemberProduct-lineage
   * exclusions. No Interface widening, stronger relation or consumer rewiring. */


  doc specifiesFunction /* Requirement-to-function relevance: a dependency from a draft requirement candidate to
   * the functional action or flow responsibility that addresses it. Relevance only — not
   * satisfaction, allocation, or verification. */
  comment about specifiesFunction /* Existing requirement-to-function dependency/relevance signature and target filter
   * remain unchanged. No allocation, satisfaction or verification claim is introduced. */


  doc derivedRequirementsOfNeed /* Inverse navigation of derivesRequirementFromNeed over the SAME discriminator witness:
   * the need N is the design-input origin of the derived requirement R. This predicate
   * declares no new model fact; it reuses the identical DerivesFromNeed connection
   * traversed in the reverse direction, with the same lineage grounding and fail-closed
   * closure semantics. */
  comment about derivedRequirementsOfNeed /* Existing frozen O3 inverse navigation over the identical DerivesFromNeed witness
   * remains unchanged; no additional model fact or executable mapping. */


  doc derivesRequirementFromNeed /* Requirement R is derived from stakeholder need N. Design-input derivation; direction R
   * -> N. No satisfaction, allocation, verification, evidence, or acceptance claim.
   * Grounded in the DE4SDV application connection definition DerivesFromNeed: the Need
   * grounds the `need` end, the derived design requirement grounds the `derivedRequirement`
   * end. DE4SDV's Requirement -> Need query is inverse navigation over that native witness. */
  comment about derivesRequirementFromNeed /* Existing frozen O3 predicate signature, native DerivesFromNeed witness and inverse
   * query direction remain unchanged; documentation only. */


  doc VerificationMethod /* A method used to check requirement satisfaction. Carried natively by VerificationMethod
   * metadata with the standard method-kind vocabulary (inspect, demo, test, analyze), per
   * the ADR 0009 amendment. */
  comment about VerificationMethod /* ODE4HERA requirements-management verificationMethod and standard VerificationMethodKind
   * remain the accepted external/library authority; no library copy or new method-kind
   * vocabulary. */


  doc VerificationCase /* A planned or executed check that evaluates whether a requirement or model claim is
   * satisfied. */
  comment about VerificationCase /* Native SysML VerificationCaseDefinition/VerificationCaseUsage (verification
   * def/verification) remain the representation. This documentation changes no frozen O3
   * traversal signature, objective, execution, result or acceptance. */


  doc Interface /* A boundary or interaction point through which items, signals, services, or information
   * are exchanged. */
  comment about Interface /* Native SysML kinds remain PortDefinition/PortUsage and connection elements. This
   * documentation preserves the existing Interface meaning and does not widen
   * hasRelevantArchitecture. */


  doc PhysicalElement /* A physical, software, hardware, deployment, or platform element that realizes
   * conceptual elements or functions. */
  comment about PhysicalElement /* Native SysML kinds: PartDefinition/PartUsage in physical/software realization slices,
   * describing concrete software, hardware, deployment or platform roles. No additional
   * PhysicalElement specialization taxonomy is introduced; typing does not prove deployment
   * or execution. */


  doc LogicalElement /* A logical service, component, or responsibility grouping that realizes functions. */
  comment about LogicalElement /* Native SysML kinds: PartDefinition/PartUsage in logical-architecture slices, describing
   * technology-neutral service/component responsibilities. No additional LogicalElement
   * specialization taxonomy is introduced. */


  doc Function /* A behavior or transformation expected from the system or product-line architecture. */
  comment about Function /* Native SysML kinds: ActionDefinition/ActionUsage (action defs/usages), with
   * StateDefinition/StateUsage and behavior definitions where appropriate. No existing
   * functional element must specialize a new Function type; this is a documentation
   * umbrella. */


  doc ArchitectureElement /* Any model element used to describe system context, function, logical realization,
   * physical/software realization, interface, or behavior. */
  comment about ArchitectureElement /* Native SysML kinds: PartDefinition/PartUsage for structural constituents;
   * ActionDefinition/ActionUsage and StateDefinition/StateUsage for behavior;
   * PortDefinition/PortUsage and ConnectionDefinition/ConnectionUsage for interfaces. This
   * is a documentation umbrella, not a parallel type taxonomy. hasRelevantArchitecture
   * remains restricted to PartUsage, PartDefinition, ActionUsage and ActionDefinition;
   * Interface is not added to that executable filter. */


  private import DE4SDV_SYSMODAdapter::*;
  private import DE4SDV_Stakeholders::*;
  /* Requirement derivation discriminator: DE4SDV application connection
   * definition. A requirement usage connected as derivedRequirement
   * originates from the stakeholder need connected as need. The typed ends
   * carry the predicate's domain and range; the definition documentation
   * carries its native direction, claim strength, and claim boundary.
   * Design-input provenance only — no satisfaction, implication,
   * verification, evidence, or acceptance claim. */

  connection def DerivesFromNeed {
    doc ontologyDefinition /* DE4SDV application connection definition for design-input derivation: the
     * derivedRequirement originates from the stakeholder need. Provenance/traceability
     * semantics only - neither satisfaction nor logical implication between the connected
     * usages is claimed. The typed connection ends (need : StakeholderNeedCandidate,
     * derivedRequirement : RequirementCandidate) carry the predicate's domain and range in
     * the model itself. The standard Requirement Derivation Domain Library remains pinned
     * but unadopted: its originalImpliesDerived semantics change the claim (upstream
     * adoption gate still applies; no floating upgrade, no upstream contact without
     * authorization). */
    end need : StakeholderNeedCandidate;
    end derivedRequirement : RequirementCandidate;
    doc /* Design-input provenance: the derivedRequirement originates from
         * the stakeholder need. Native direction: need -> derivedRequirement.
         * Claim strength: derivation (provenance only: neither satisfaction
         * nor logical implication between the connected usages; no
         * allocation, verification, evidence, or acceptance claim). */
  }

  /* Re-exported so feature packages can assign `attribute :>> status =
   * ReqStatus::...` (ADR 0009) without importing the adapter directly. */
  public import ReqStatus;

  /* Re-exported so feature packages can assign `attribute :>>
   * verificationStatus = VVStatus::...` (ADR 0009 amendment) without
   * importing the adapter directly. */
  public import VVStatus;

  comment hasStakeholder about EngineeringIncrement, Stakeholder /* Vocabulary
   * role: EngineeringIncrement -> Stakeholder. Existing native stakeholder
   * membership is preserved; this comment introduces no additional trace
   * slot, executable mapping, participation requirement or acceptance. */

  part def EngineeringIncrement {
    doc /* A bounded DE4SDV work package that changes, tests, or publishes engineering knowledge. */
  }

  connection def HasStakeholder {
    doc /* An engineering increment identifies a stakeholder role participating
         * in or affected by it. Domain EngineeringIncrement; range Stakeholder.
         * Vocabulary-only typed carrier during migration, not executable
         * traversal proof, native StakeholderMembership equivalence, real-person
         * assignment, approval authority, competence or safety acceptance. */
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
    doc ontologyDefinition /* Stakeholder-expressed problem-space intent, before conversion into design input
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
    doc ontologyDefinition /* A verifiable design input obligation or constraint derived from needs, standards, or
     * architecture decisions. The kernel models requirement candidates on the SYSMOD
     * requirement seam with ADR 0009 attributes. */
    doc /* A verifiable design input obligation or constraint derived from needs, standards, or architecture decisions.
         * Generic base for design-input requirement candidates before acceptance.
         * Specializes the SYSMOD requirement seam, inheriting obligation,
         * stability, and motivation metadata for requirement candidates.
         * DE4SDV candidate lifecycle semantics remain local. */
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

  comment hasAcceptanceCriterion about AcceptanceCriterion /* The criterion
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
  }

  requirement def EvidenceContract :> RequirementCandidate {
    doc /* A requirement usage that defines the bounded observations, acceptance
         * boundary, and retained-evidence obligations for a verification case. An
         * evidence contract is planning vocabulary, not proof that a product
         * requirement is verified. */
    /* hasRelevantEvidenceContract can be discriminated by this type and its
     * specialization closure, not by an evidenceContract name prefix. This
     * package does not change the existing runtime dependency mapping. */
  }

  requirement def EvidenceContractTraceabilityRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for evidence-contract traceability to controlled boundaries. */
  }

  requirement def RegulatoryConstraintCandidate :> RequirementsManagementAttributeBase {
    doc ontologyDefinition /* A constraint or reference derived from a standard, regulation, or homologation-
     * relevant source, with controlled source identity and no compliance claim. */
    doc /* A constraint or reference derived from a standard, regulation, or homologation-relevant source, with controlled source identity and no compliance claim. Grounds the ontology RegulatoryConstraint class and R003 derivation targets. */
  }

  part def ArchitectureDecisionRecord {
    doc ontologyDefinition /* A reviewed architecture or method decision recorded as an ADR in Git that can serve
     * as the semantic origin of a design-input requirement. */
    doc /* A reviewed architecture or method decision recorded as an ADR in Git that can serve as the semantic origin of a design-input requirement. Grounds the ontology ArchitectureDecisionRecord class and R003 derivation targets. */
  }

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
}
