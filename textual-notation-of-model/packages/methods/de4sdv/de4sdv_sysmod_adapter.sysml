/*
 * DE4SDV adapter boundary for exact-pinned external requirements-management
 * packages.
 *
 * Only this package imports upstream requirements-management namespaces.
 * DE4SDV model packages specialize the DE4SDV-owned seam definitions below
 * rather than importing upstream definitions directly. This keeps package
 * upgrades reviewable and prevents upstream library structures from becoming
 * a second DE4SDV method root.
 *
 * Dependencies:
 *   pkg:sysand/mbse4u/sysmod =5.1.1
 *   pkg:sysand/ode4hera/requirements-management =2.0.1
 * Provenance: methodologies/sysmod-sysmlv2/upstream.md
 */

package DE4SDV_SYSMODAdapter {
  private import SYSMOD::ExtendedStakeholder;
  private import SYSMOD::ExtendedRequirement;
  private import SYSMOD::SystemUseCase;
  private import SYSMOD::ConstrainedOccurrence;
  private import RequirementsManagement::NeedsRequirementsAttributes;
  public import RequirementsManagement::ReqStatus;
  public import RequirementsManagement::VVStatus;

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

  requirement def RequirementsManagementAttributeBase :> NeedsRequirementsAttributes {
    doc /*
     * Selected upstream attribute seam from the ODE4HERA requirements-management
     * library (NRM Chapter 15 attribute catalog). Specialized by DE4SDV method
     * need and candidate definitions. Adopted scope per ADR 0009: rationale,
     * source, status, and authoring-provenance attributes; ReqPriority and
     * ReqImplementationStatus are intentionally not adopted at this time.
     *
     * ReqStatus is re-exported publicly so feature packages can assign
     * `attribute :>> status = ReqStatus::...` through this seam.
     */
  }
}
