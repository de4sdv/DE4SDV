/*
 * DE4SDV reusable product-line semantic kernel.
 *
 * This package keeps product-line vocabulary out of feature-specific slices.
 * It follows the DE4SDV/ISO 26580-aligned distinction that common capabilities
 * are not features unless they distinguish member products. SysML v2 native
 * variation/variant constructs are intentionally not wrapped here until their
 * exact use is specified and reviewed.
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
    doc /* Product-line classification concept for common capabilities, feature candidates, and deferred variability decisions. */
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

  part def DeferredVariabilityDecision :> ProductLineCharacteristic {
    doc /* Variability topic recorded for later modeling with native SysML v2 variation/variant semantics after syntax and intent are reviewed. */
  }
}
