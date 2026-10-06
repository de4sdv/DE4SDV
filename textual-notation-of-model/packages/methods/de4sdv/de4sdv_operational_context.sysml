/*
 * DE4SDV reusable operational-context kernel.
 *
 * This package contains common operational actors/context entities used across
 * SDV feature increments. Feature packages should specialize or instantiate
 * these definitions instead of redefining generic vehicle/driver/context roles.
 */

package DE4SDV_OperationalContext {
  doc ValidationScenarioOntologyDefinition /* A scenario used to assess stakeholder fitness for intended use. */
  comment about ValidationScenarioOntologyDefinition /* Native Scenario parts and bounded validation outcomes remain the representation.
   * ValidationPlanningScenario is planning only; no native validation-case keyword or
   * fitness-for-use verdict is invented. */


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
    private doc ontologyDefinition /* A reviewed and controlled state of model, evidence, configuration, or publication
     * artifacts. */
    doc /* A reviewed and controlled state of model, evidence, configuration, or publication artifacts, referenced without implying accepted evidence. */
  }

  comment BaselineVocabularyRole about DE4SDVEvidenceBaseline /* External
   * boundary: baseline content is external (Git revisions and the identified
   * baseline manifest); the model has no authority over it and keeps no second
   * mutable baseline list. DE4SDVEvidenceBaseline is only the model-resident
   * reference identity and its claim boundary: it describes what is referenced,
   * not who grants approval, and no rename is implied. */

  comment capturedInBaselineVocabularyRole about DE4SDVEvidenceBaseline /* External
   * boundary for capturedInBaseline (EvidenceArtifact to Baseline): membership
   * is exact inclusion of the artifact version identity in the identified
   * immutable manifest under de4sdv.baseline-manifest-reference/v1; content
   * external, no authority. A different revision of the same artifact is not
   * included, inclusion never approves evidence, and no traversal is
   * implemented. */

  part def Scenario {
    doc /* A bounded operational, validation, test, or threat situation used to reason about behavior and evidence. */
  }
}
