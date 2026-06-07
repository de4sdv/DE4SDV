# Feature Models

Feature models in DE4SDV should represent product-line variability, not a loose
list of capabilities.

## Source-aligned distinction

ISO/IEC 26580 frames a feature as a characteristic of a member product that
distinguishes it from other member products in the product line. It also states
the key modeling consequence: characteristics common to all member products are
not modeled as features in feature-based PLE.

DE4SDV adopts this distinction as a working rule:

> Model a characteristic as a DE4SDV feature only when it expresses variability
> among member products.

If every member product has the characteristic, model it as a common product-
line capability instead.

## Working concepts

- **Product line** — family of similar products with variation among member
  products.
- **Member product** — one product belonging to the product line.
- **Feature** — distinguishing characteristic selected for at least one member
  product and not all member products.
- **Common capability** — capability or characteristic present in every member
  product; important, but not a feature.
- **Feature catalogue** — model of available feature options and feature
  constraints across the product line.
- **Bill-of-features** — selected feature set for a member product.
- **Feature constraint** — required relationship among features, such as
  requires/excludes rules.
- **Variation point** — location in a shared asset superset configured according
  to feature selections.

## Example

In a DE4SDV OTA update slice:

- `OTAUpdateSupport` is a common capability when every member product supports
  OTA updates.
- `AutomaticRollbackForOTAUpdate` is a feature when it is selected for
  `PremiumSDV` and not for `BaseSDV`.

The second item is a feature because it distinguishes member products. The first
is not a feature because it is common across the example product line.

## Current pilot

See [`../../approach/framework/ontology/pilots/feature-variability-
traceability/`](../../approach/framework/ontology/pilots/feature-variability-
traceability/) for the first reviewable ontology-style feature variability
pilot.
