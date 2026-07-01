/*
 * DE4SDV reusable operational-context kernel.
 *
 * This package contains common operational actors/context entities used across
 * SDV feature increments. Feature packages should specialize or instantiate
 * these definitions instead of redefining generic vehicle/driver/context roles.
 */

package DE4SDV_OperationalContext {
  part def OperationalEntity {
    doc /* Reusable entity participating in an operational context or scenario. */
  }

  part def SubjectVehicle :> OperationalEntity {
    doc /* Vehicle or member-product instance whose behavior is under consideration in an operational slice. */
  }

  part def Driver :> OperationalEntity {
    doc /* Human driver or driver role interacting with the subject vehicle. */
  }

  part def RoadEnvironment :> OperationalEntity {
    doc /* Road, lane, traffic, and environmental context relevant to an operational scenario. */
  }

  part def OperationalTarget :> OperationalEntity {
    doc /* External target or object relevant to an operational scenario. */
  }

  part def VehicleTarget :> OperationalTarget {
    doc /* Vehicle target relevant to ADAS/automated-driving operational scenarios. */
  }

  part def DE4SDVEvidenceBaseline :> OperationalEntity {
    doc /* DE4SDV review/evidence baseline referenced by operational or validation slices without implying accepted evidence. */
  }
}
