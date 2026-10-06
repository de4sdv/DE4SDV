/*
 * DE4SDV reusable product-line semantic kernel.
 *
 * This package keeps product-line vocabulary out of feature-specific slices.
 * It follows the DE4SDV/ISO 26580-aligned distinction that common capabilities
 * are not features unless they distinguish member products.
 *
 * SysML v2 variability is modeled with native `variation` / `variant` notation:
 * a variation marks the varying definition or usage, and its owned variant
 * usages enumerate allowed choices. Do not introduce a project-local
 * variation-point part definition in place of native SysML v2 variation semantics.
 */

package DE4SDV_ProductLine {
  doc instantiatesCanonicalArchitectureOntologyDefinition /* Explicit binding from a composite member product's contained architecture instances
   * (its logical-system and software usages) to the canonical architecture usages whose
   * allocation and evidence records govern them. The modeled dependencies originate from
   * the contained usages, not from the member-product root; the executable mapping must
   * therefore define which elements carry this relationship and how a query walks it before
   * any product-level query reachability is claimed. Vocabulary only for now: no
   * sysml_mapping is declared because a generic dependency traversal cannot distinguish
   * canonical-architecture bindings from ordinary part-to-part dependencies without
   * inventing a naming heuristic. Declaring an executable mapping requires an explicit
   * canonical-usage selector (for example an API-side allowlist of canonical packages), not
   * a name-based filter. The binding does not restate allocations at product level and does
   * not make a composite projection a resolved configured product. */
  comment about instantiatesCanonicalArchitectureOntologyDefinition /* not queryable; no product-to-canonical reachability claimed. Vocabulary only; no
   * executable mapping and no canonical-package selector are introduced. The selector
   * discussion in the retained definition is a future prerequisite, not implementation in
   * this package. */


  doc FeatureConfigurationOntologyDefinition /* A selection of features, common capabilities, and variation choices for a member
   * product or scenario. */
  comment about FeatureConfigurationOntologyDefinition /* Definition text is model-resident; Bill-of-Features contents and catalogue/configurator
   * authority remain external. No PLEML adoption, selection algebra or consumer wiring
   * changes. */


  doc VariantOntologyDefinition /* A native SysML v2 variant usage owned by a variation point and representing one allowed
   * choice for that variation. */
  comment about VariantOntologyDefinition /* Native SysML variant usage owned by a variation remains the representation; no new
   * reusable variant class or selection authority. */


  doc VariationPointOntologyDefinition /* A native SysML v2 variation definition or usage that identifies an element whose
   * allowed instances vary across product-line configurations. */
  comment about VariationPointOntologyDefinition /* Native SysML variation definition/usage remains the representation, not a generic
   * variation-point part taxonomy or configurator adoption. */


  part def ProductLine {
    doc /* A family of related member products managed through shared assets and variability. */
  }

  part def SDVProductLine :> ProductLine {
    doc /* Software-defined vehicle product line managed through DE4SDV product-line semantics. */
  }

  part def ProductLineMemberProduct {
    doc /* A configured product or product variant that belongs to a product line. */
  }

  part def ProductLineCharacteristic {
    doc /* The product-line classification base: a characteristic is a common capability, a feature candidate, deferred scope, or a native SysML v2 variation choice. */
  }

  part def CommonProductLineCapability :> ProductLineCharacteristic {
    doc ontologyDefinition /* A capability or characteristic present in all relevant member products; not a feature
     * unless it distinguishes variants. */
    doc /* Capability required across member products; not a feature unless it distinguishes member products. */
    /* Feature/common-capability disjointness (owner decision 7, checked-constraint
     * fallback): the licensed toolchain rejects the standalone KerML disjoining in a
     * SysML package, so the axiom is a checked constraint on both definitions. */
    assert constraint notAFeatureCandidate { not (that istype ProductLineFeatureCandidate) }
  }

  part def ProductLineFeatureCandidate :> ProductLineCharacteristic {
    doc ontologyDefinition /* A distinguishing characteristic expressing variability among member products. In the
     * kernel a feature is a candidate until member-product variability is shown; it must
     * not be accepted as a feature before that. */
    doc /* Candidate distinguishing characteristic; must not be accepted as a feature until member-product variability is shown. */
    assert constraint notACommonCapability { not (that istype CommonProductLineCapability) }
  }

  part def DeferredProductLineScope :> ProductLineCharacteristic {
    doc /* Product-line scope deliberately deferred from the current increment, including recorded gaps. */
  }

  part def ProductLineVariantChoice :> ProductLineCharacteristic {
    doc /* Descriptive project vocabulary for variant choices in YAML/Markdown traces. Concrete SysML variant usages should be represented with native `variant` membership and should not rely on this type as a substitute for variation semantics. */
  }

  part def DeferredVariantChoice :> ProductLineVariantChoice {
    doc /* Descriptive vocabulary for unresolved variant choices outside a concrete SysML variation body; not an accepted product configuration choice. */
  }

  /*
   * Generic native variation definition for unresolved product-line choices.
   *
   * SysML v2 requires the owned members of a variation definition/usage to be
   * variant usages. Keep the body limited to `variant` usages.
   */
  variation part def DeferredProductLineVariation {
    variant part deferredChoice;
  }
}
