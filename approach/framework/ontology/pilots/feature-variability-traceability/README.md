# Feature Variability Traceability Pilot

This pilot tests whether ontology-style modeling helps DE4SDV make product-line
variability explicit and traceable without committing the project to a final
ontology stack.

## Engineering question

Can DE4SDV represent a product-line feature as a distinguishing characteristic
of selected member products and trace that feature to requirements,
architecture, verification evidence, and release/certification impact?

## Source basis

The pilot uses ISO/IEC 26580 terminology as the primary product-line source. In
that framing:

- a **feature** distinguishes one member product from other member products in
  the product line;
- a characteristic common to every member product is not modeled as a feature;
- a **bill-of-features** specifies the selected features for a member product;
- a **feature catalogue** contains the available feature options and constraints
  across the product line;
- shared asset supersets contain variation points that are configured from
  feature selections.

ISO/IEC 26580 also points to ISO/IEC/IEEE 12207 and ISO/IEC/IEEE 15288 for
lifecycle terminology, and notes ISO/IEC/IEEE 24765/SEVOCAB for systems and
software vocabulary. DE4SDV should treat those as vocabulary anchors, not as a
claim that the project has adopted their full process models.

## Non-goals

This pilot does not:

- choose a final ontology notation or toolchain;
- adopt OML/openCAESAR;
- add RDF, SHACL, or SPARQL validation to CI;
- map the pilot into SysML v2;
- import VSS, VSSo, SOSA/SSN, or OSLC vocabularies;
- model the full DE4SDV product line.

## Scope of the example

The pilot uses a small OTA update slice:

- `OTAUpdateSupport` is modeled as a common capability because it is included in
  all example member products.
- `AutomaticRollbackForOTAUpdate` is modeled as a feature because it is selected
  for `PremiumSDV` and distinguishes that member product from `BaseSDV`.

This distinction is deliberate. Calling every capability a feature would erase
the variability semantics that feature-based PLE needs.

## Pilot artifacts

- [`model.yaml`](model.yaml) — reviewable source model for the example slice.
- [`diagrams.md`](diagrams.md) — Mermaid diagrams for the ontology views.
- [`validation-rules.md`](validation-rules.md) — plain-language model quality
  rules.
- [`traceability-queries.md`](traceability-queries.md) — questions the ontology
  should answer.
- [`notation-options.md`](notation-options.md) — stack-neutral notation tradeoff
  notes.

## Concepts in this pilot

- `ProductLine` — the managed family of similar products.
- `MemberProduct` — one product belonging to the product line.
- `Feature` — distinguishing characteristic selected for at least one member
  product and not all member products.
- `CommonCapability` — characteristic present in all member products; useful to
  model, but not as a feature.
- `FeatureCatalogue` — available feature options and constraints for the product
  line.
- `BillOfFeatures` — selected features for a member product.
- `SharedAssetSuperset` — shared lifecycle artifact containing all content
  needed by member products.
- `VariationPoint` — location in a shared asset whose content is configured from
  feature selections.
- `EvidenceArtifact` — planned or actual evidence used to support verification,
  validation, assurance, or release decisions.

## Intended use

Use this pilot to review whether DE4SDV's product-line semantics are clear
enough before introducing heavier ontology tooling.

A useful review result is one of:

1. Accept the conceptual slice and later evaluate RDF/SHACL.
2. Revise the feature/common-capability distinction or example.
3. Reject ontology-style modeling for this concern and record why.
