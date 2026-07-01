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

  part def SystemContext {
    doc /* Context containing the system actors, the system of interest, and their relationships. */
    part actors[*];
    part systemOfInterest;
  }
}
