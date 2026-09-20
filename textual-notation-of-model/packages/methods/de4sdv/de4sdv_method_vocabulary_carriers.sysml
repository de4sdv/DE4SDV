/*
 * DE4SDV vocabulary-relationship definition carriers (O4 W4).
 *
 * Model-resident carriers for the reviewed vocabulary-only relationship
 * family: recordsGap, recordsAssumption, addressesConcern,
 * selectedViewpoint, producesView.
 *
 * ONE reusable representation, mirroring the accepted requirement-derivation
 * carrier pattern (DE4SDV_MethodContext::DerivesFromNeed): each carrier is a
 * `connection def` whose typed ends carry the predicate's reviewed domain and
 * range, and whose owned documentation carries the reviewed definition
 * (normalized-exact) plus its claim boundary.
 *
 * Vocabulary-only: these carriers declare method vocabulary. They implement
 * and claim no runtime traversal, no satisfaction, no allocation, and no
 * acceptance semantics. The runtime never reads this package.
 *
 * Range types: the increment-scoped range declarations live in this package
 * (generic bases for the reviewed range kinds); the view range uses the
 * accepted standard-library `View` (Views library, imported below) because no
 * repo-resident generic view definition exists.
 */

package DE4SDV_MethodVocabularyCarriers {
  private import DE4SDV_MethodContext::*;
  private import Views::*;

  /* Generic range bases for the reviewed vocabulary-only predicates: the
   * predicate is generic over the reviewed range kind, so the carrier ends
   * are typed by these bases rather than by one concrete method concern or
   * viewpoint. Concrete method/SAF concern and viewpoint definitions may
   * specialize them in a later reviewed step; this file changes nothing
   * about the existing concrete declarations. */
  abstract concern def IncrementConcern;

  abstract viewpoint def IncrementViewpoint;

  /* Carrier claim-boundary note (one shared boundary statement; each carrier
   * additionally carries its own reviewed definition verbatim as an owned
   * documentation body):
   * recording, selection, and production are explicit authoring facts only.
   * No traversal, satisfaction, allocation, verification, evidence, or
   * acceptance semantics are implemented or claimed. */

  connection def RecordsGap {
    end gap : IncrementGap;
    end recordingIncrement : EngineeringIncrement;
    doc /* Engineering increment explicitly records an unresolved engineering/evidence gap. */
    doc /* Claim boundary: explicit recording only. The gap remains open; this
         * carrier never closes, resolves, or prioritizes a gap and asserts no
         * evidence status. */
  }

  connection def RecordsAssumption {
    end assumption : IncrementAssumption;
    end recordingIncrement : EngineeringIncrement;
    doc /* Engineering increment explicitly records an assumption relevant to its bounded work. */
    doc /* Claim boundary: explicit recording only. The assumption is not
         * validated, not promoted to a requirement, and no confidence or
         * acceptance state is asserted. */
  }

  connection def AddressesConcern {
    end concern : IncrementConcern;
    end reviewingIncrement : EngineeringIncrement;
    doc /* Engineering increment records an explicitly reviewed concern within its scope; no automatic concern satisfaction. */
    doc /* Claim boundary: explicit recording of review scope only. No
         * automatic concern satisfaction, no coverage metric, and no claim
         * that the concern is resolved by the increment. */
  }

  connection def SelectedViewpoint {
    end viewpoint : IncrementViewpoint;
    end selectingIncrement : EngineeringIncrement;
    doc /* Engineering increment records a viewpoint explicitly selected for its review questions. */
    doc /* Claim boundary: explicit selection only. Selection asserts neither
         * that a conforming view was produced nor that the viewpoint's
         * concerns are addressed. */
  }

  connection def ProducesView {
    end view : View;
    end producingIncrement : EngineeringIncrement;
    doc /* Engineering increment identifies a view artifact produced as an increment deliverable. */
    doc /* Claim boundary: explicit identification of a produced view artifact
         * only. No completeness, conformance, or review-outcome claim, and no
         * API element identity is asserted. */
  }
}
