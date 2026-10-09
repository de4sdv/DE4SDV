/*
 * DE4SDV assurance argumentation kinds.
 *
 * A claim, its supporting arguments and its counter-claims are assurance
 * artifacts that consume verification results. They are not design-input
 * requirements: they do not derive from stakeholder needs, record no
 * verification method and are not verified by verification cases. The three
 * definitions keep the requirement keyword only as the textual form of a
 * bounded statement about a subject. They deliberately do not specialize
 * DE4SDV_MethodContext::RequirementCandidate, so the Requirement lineage and
 * the requirement method checks do not apply to their usages.
 *
 * Meaning follows the approved scoped-assurance semantics
 * (DE4SDV_ScopedAssurance): an argument is cited support with rationale and
 * limits; a claim counts as established only after a scoped evidence-set
 * adequacy assessment of the same exact scope; a counter-claim is a disclosed
 * limit on the claim's scope, tied to its gap record; acceptance stays a
 * separate authority record. No richer argumentation metamodel is introduced.
 */
package DE4SDV_AssuranceArgumentation {
  requirement def AssuranceClaim {
    doc /* A bounded statement about a subject, its configuration and conditions that requires argument and evidence before acceptance. It counts as established only after a ScopedEvidenceAdequacyAssessment of the same exact scope; acceptance stays a separate authority record. A claim never implies certification or homologation. */
  }

  requirement def AssuranceArgument {
    doc /* Cited support for a claim: the verification cases and retained evidence it relies on, with rationale and known limits. An argument establishes neither evidence adequacy nor acceptance. */
  }

  requirement def AssuranceCounterClaim {
    doc /* A disclosed limit on the scope of a claim, tied to the gap record that keeps it open. It states what the claim must not be read to cover; it is not an obligation. */
  }
}
