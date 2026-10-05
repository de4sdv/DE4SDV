/*
 * Reusable DE4SDV stakeholder role definitions.
 *
 * Native `stakeholder` parameters are PartUsages. Explicit item definitions
 * are not forbidden as their types (OMG SysML v2 Part 1, 7.11.2). Local roles
 * remain reusable non-individual part definitions specializing Stakeholder;
 * `individual` identifies one unique real or perceived entity, not a reusable
 * role. This package keeps role vocabulary out of feature-specific slices.
 *
 * Eight roles below are locally adapted from GfSE/SAF-SysMLV2, Apache-2.0,
 * revision c57bd42db60a00c51168f6aba8e2229ba0165b6c,
 * Stakeholders/stakeholders_library.sysml. Attribution: GfSE SAF contributors.
 * Upstream `individual item def` declarations specializing Stakeholders are
 * structurally modified into reusable local `part def` specializations of
 * Stakeholder, with local risk/effort/contact/categories. HardwareDeveloper's
 * description is narrowed to hardware; Supplier's description is shortened.
 * Descriptions below express role responsibilities, not achieved obligations.
 * These are adaptations, not unchanged imports, full SAF adoption or upstream
 * endorsement. Retain the Apache-2.0 terms in the repository LICENSE. The
 * pinned upstream tree has no NOTICE-named file; this is provenance, not legal
 * clearance. See methodologies/sysmod-sysmlv2/pilots/saf-source.yaml.
 * Role typing assigns no real person, competence, approval authority or safety
 * acceptance; ComplianceEngineer is not an external regulatory authority.
 */

package DE4SDV_Stakeholders {
  enum def PriorityKind :> ScalarValues::Real {
    none = 0.0;
    low = 0.25;
    medium = 0.5;
    high = 0.75;
    critical = 1.0;
  }

  enum def StakeholderCategoryKind {
    Expert;
    RequirementOwner;
    User;
    Other;
  }

  part def Stakeholder {
    doc ontologyDefinition /* A role, person, organization, or community with concerns about the system or
     * increment. */
    doc /* Reusable role of a party participating in or affected by engineering.
         * Not one identified individual or a grant of acceptance authority. */
    attribute risk : PriorityKind;
    attribute effort : PriorityKind;
    attribute contact : ScalarValues::String;
    attribute categories[*] : StakeholderCategoryKind;
  }

  // ─── DE4SDV-originated roles ───

  part def RoadUser :> Stakeholder;
  part def VehicleOccupant :> Stakeholder;
  part def SystemsEngineer :> Stakeholder;
  part def ProductLineEngineer :> Stakeholder;
  part def ComplianceEngineer :> Stakeholder;
  part def VerificationEngineer :> Stakeholder;
  part def OpenSourceReviewer :> Stakeholder;

  // ─── Eight locally adapted GfSE SAF roles (separate from local roles) ───
  // Source: https://github.com/GfSE/SAF-SysMLV2/blob/c57bd42db60a00c51168f6aba8e2229ba0165b6c/Stakeholders/stakeholders_library.sysml
  // License: Apache-2.0

  part def SafetyExpert :> Stakeholder {
    doc /*
     * Evaluates system safety and ensures safety measures are implemented.
     * Source: GfSE SAF stakeholder library — SafetyExpert.
     */
  }

  part def SecurityExpert :> Stakeholder {
    doc /*
     * Ensures the system design meets security requirements and mitigates
     * vulnerabilities.
     * Source: GfSE SAF stakeholder library — SecurityExpert.
     */
  }

  part def SystemArchitect :> Stakeholder {
    doc /*
     * Designs and maintains the system architecture.
     * Source: GfSE SAF stakeholder library — SystemArchitect.
     */
  }

  part def SoftwareDeveloper :> Stakeholder {
    doc /*
     * Organization or individual responsible for system development,
     * including design and testing.
     * Source: GfSE SAF stakeholder library — SoftwareDeveloper.
     */
  }

  part def HardwareDeveloper :> Stakeholder {
    doc /*
     * Organization or individual responsible for hardware development,
     * including design and testing.
     * Source: GfSE SAF stakeholder library — HardwareDeveloper.
     */
  }

  part def Maintainer :> Stakeholder {
    doc /*
     * Ensures system availability through maintenance during its lifecycle.
     * Source: GfSE SAF stakeholder library — Maintainer.
     */
  }

  part def Supplier :> Stakeholder {
    doc /*
     * Organization or individual that enters into an agreement with the
     * Acquirer for the supply of a product or service.
     * Source: GfSE SAF stakeholder library — Supplier (ISO/IEC 15288:2022).
     */
  }

  part def ProjectManager :> Stakeholder {
    doc /*
     * Responsible for project resources, planning, and meeting milestones.
     * Source: GfSE SAF stakeholder library — ProjectManager.
     */
  }
}
