/*
 * DE4SDV reusable operational-context kernel.
 *
 * This package contains common operational actors/context entities used across
 * SDV feature increments. Feature packages should specialize or instantiate
 * these definitions instead of redefining generic vehicle/driver/context roles.
 *
 * kernel-vocabulary:
 * Classification of every declaration below for the ontology sync gate
 * (scripts/check_model_sync.py sync point 6). See
 * de4sdv_method_context.sysml for the status definitions. All other
 * declarations here are reusable operational-context actors for feature
 * slices, not DE4SDV method vocabulary.
 * Every new declaration must be classified here in the same commit.
 *
 * - OperationalEntity: kernel-internal (operational-context entity base)
 * - SubjectVehicle: kernel-internal (operational-context entity)
 * - Driver: kernel-internal (operational-context entity)
 * - RoadEnvironment: kernel-internal (operational-context entity)
 * - OperationalTarget: kernel-internal (operational-context entity)
 * - VehicleTarget: kernel-internal (operational-context entity)
 * - DE4SDVEvidenceBaseline: ontology
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
