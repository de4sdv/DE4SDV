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
  private import DE4SDV_SYSMODAdapter::*;

  part def EngineeringIncrement {
    doc /* Bounded DE4SDV work package that changes, tests, or publishes engineering knowledge. */
  }

  part def FeatureIncrement :> EngineeringIncrement {
    doc /* Engineering increment focused on a product-line feature, common capability, or variability decision. */
  }

  part def NeedsRequirementsIncrement :> EngineeringIncrement {
    doc /* Engineering increment focused on needs, draft requirements, traceability, and V&V planning. */
  }

  part def SystemLayer {
    doc /* Coarse ASELCM-style system layer used to frame DE4SDV increments. */
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
    doc /* The problem that is to be solved by the system or increment. */
  }

  requirement def StakeholderNeedCandidate {
    doc /* Generic base for stakeholder needs before acceptance and quality gate. */
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

  requirement def RequirementCandidate :> SYSMODRequirementBase {
    doc /* Generic base for design-input requirement candidates before acceptance.
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

  requirement def EvidenceContractTraceabilityRequirementCandidate :> RequirementCandidate {
    doc /* Candidate requirement for evidence-contract traceability to controlled boundaries. */
  }

  part def IncrementAssumption {
    doc /* Assumption recorded for an engineering increment. */
  }

  part def IncrementGap {
    doc /* Gap or unresolved item recorded for an engineering increment. */
  }

  part def IncrementScope {
    doc /* Scope boundary for an engineering increment. */
  }

  part def IncrementTraceabilityShell {
    doc /* Traceability structure connecting an increment to its sources and downstream artifacts. */
  }

  part def IncrementEngineeringQuestion {
    doc /* Engineering question that an increment answers. */
  }

  part def IncrementLifecycleDecision {
    doc /* Lifecycle decision that an increment supports. */
  }

  part def MissingRealizationRecord {
    doc /* Record of a missing realization allocation for a conceptual element. */
  }

  part def BlockedRealizationBranchRecord {
    doc /* Record of a blocked realization branch due to a source defect or gap. */
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
