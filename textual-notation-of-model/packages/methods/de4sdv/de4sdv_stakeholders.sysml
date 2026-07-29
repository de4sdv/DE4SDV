/*
 * Reusable DE4SDV stakeholder role definitions.
 *
 * SysML v2 requirement stakeholder parameters are declared with the
 * `stakeholder` keyword, but those parameters are still part usages typed by
 * part definitions. This package keeps reusable stakeholder role definitions
 * out of feature-specific model slices.
 *
 * Several roles below are source-backed from the GfSE SAF SysML v2 stakeholder
 * library (https://github.com/GfSE/SAF-SysMLV2, Apache-2.0). The GfSE
 * definitions use `individual item def` with string-quoted names; DE4SDV
 * re-declares them as `part def` specializations of its own Stakeholder base
 * with identifier names. See methodologies/sysmod-sysmlv2/pilots/saf-source.yaml
 * for source provenance.
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

  // ─── Roles adopted from GfSE SAF stakeholder library ───
  // Source: https://github.com/GfSE/SAF-SysMLV2/blob/main/Stakeholders/stakeholders_library.sysml
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
