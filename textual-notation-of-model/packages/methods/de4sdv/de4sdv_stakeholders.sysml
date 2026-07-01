/*
 * Reusable DE4SDV stakeholder role definitions.
 *
 * SysML v2 requirement stakeholder parameters are declared with the
 * `stakeholder` keyword, but those parameters are still part usages typed by
 * part definitions. This package keeps reusable stakeholder role definitions
 * out of feature-specific model slices.
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

  part def RoadUser :> Stakeholder;
  part def VehicleOccupant :> Stakeholder;
  part def SystemsEngineer :> Stakeholder;
  part def ProductLineEngineer :> Stakeholder;
  part def ComplianceEngineer :> Stakeholder;
  part def VerificationEngineer :> Stakeholder;
  part def OpenSourceReviewer :> Stakeholder;
}
