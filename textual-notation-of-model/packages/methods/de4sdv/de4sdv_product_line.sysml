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
 *
 * kernel-vocabulary:
 * Classification of every declaration below for the ontology sync gate
 * (scripts/check_model_sync.py sync point 6). See
 * de4sdv_method_context.sysml for the status definitions.
 * Every new declaration must be classified here in the same commit.
 *
 * - ProductLine: ontology
 * - SDVProductLine: kernel-internal (concrete product-line instance type;
 *   the ontology covers the generic ProductLine concept)
 * - ProductLineMemberProduct: ontology
 * - ProductLineCharacteristic: ontology
 * - CommonProductLineCapability: ontology
 * - ProductLineFeatureCandidate: ontology
 * - DeferredProductLineScope: ontology
 * - ProductLineVariantChoice: kernel-internal (descriptive YAML/Markdown
 *   vocabulary, deliberately not an accepted configuration choice)
 * - DeferredVariantChoice: kernel-internal (descriptive vocabulary for
 *   unresolved choices outside a concrete SysML variation body)
 * - DeferredProductLineVariation: kernel-internal (generic deferred-choice
 *   variation placeholder, not ontology vocabulary)
 */

package DE4SDV_ProductLine {
  part def ProductLine {
    doc /* Family of related member products managed through shared assets and controlled variability. */
  }

  part def SDVProductLine :> ProductLine {
    doc /* Software-defined vehicle product line managed through DE4SDV product-line semantics. */
  }

  part def ProductLineMemberProduct {
    doc /* Configured product or product variant belonging to a product line. */
  }

  part def ProductLineCharacteristic {
    doc /* Product-line classification concept for common capabilities, feature candidates, deferred scope, and native SysML v2 variation choices. */
  }

  part def CommonProductLineCapability :> ProductLineCharacteristic {
    doc /* Capability required across member products; not a feature unless it distinguishes member products. */
  }

  part def ProductLineFeatureCandidate :> ProductLineCharacteristic {
    doc /* Candidate distinguishing characteristic; must not be accepted as a feature until member-product variability is shown. */
  }

  part def DeferredProductLineScope :> ProductLineCharacteristic {
    doc /* Scope deliberately deferred from the current increment. */
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
