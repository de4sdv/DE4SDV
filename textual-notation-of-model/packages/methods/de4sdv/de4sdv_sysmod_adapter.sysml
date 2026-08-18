/*
 * DE4SDV adapter boundary for the exact-pinned external SYSMOD package.
 *
 * Only this package imports the upstream SYSMOD namespace. DE4SDV model
 * packages specialize the DE4SDV-owned seam definitions below rather than
 * importing upstream definitions directly. This keeps package upgrades
 * reviewable and prevents the upstream Project/context chain from becoming a
 * second DE4SDV architecture root.
 *
 * Dependency: pkg:sysand/mbse4u/sysmod =5.1.1
 * Provenance: methodologies/sysmod-sysmlv2/upstream.md
 */

package DE4SDV_SYSMODAdapter {
  private import SYSMOD::ExtendedStakeholder;
  private import SYSMOD::ExtendedRequirement;
  private import SYSMOD::SystemUseCase;
  private import SYSMOD::ConstrainedOccurrence;

  part def SYSMODStakeholderBase :> ExtendedStakeholder {
    doc /* Selected upstream stakeholder-metadata seam. Existing DE4SDV roles are not migrated by this definition. */
  }

  requirement def SYSMODRequirementBase :> ExtendedRequirement {
    doc /* Selected upstream requirement-metadata seam. Specialized by DE4SDV_MethodContext::RequirementCandidate; DE4SDV candidate lifecycle semantics remain local. */
  }

  use case def SYSMODSystemUseCaseBase :> SystemUseCase {
    doc /* Selected upstream system-use-case seam. Specialized by the AEBS and middleware integration use cases. */
  }

  occurrence def SYSMODConstrainedOccurrenceBase :> ConstrainedOccurrence {
    doc /* Opt-in seam for occurrences whose lifecycle is governed by explicit preconditions and postconditions. */
  }
}
