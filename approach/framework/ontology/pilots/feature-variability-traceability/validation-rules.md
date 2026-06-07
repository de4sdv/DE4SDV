# Pilot Validation Rules

These are pilot rules for review. They are not yet DE4SDV-wide governance rules
and are not implemented in CI.

## Product-line semantics

### RULE-001 — Feature distinction

A candidate characteristic shall be modeled as a `Feature` only if it
distinguishes at least one member product from another member product in the
product line.

### RULE-002 — Common capability separation

A candidate characteristic that is common to all member products shall be
modeled as a `CommonCapability`, not as a `Feature`.

### RULE-003 — Member-product applicability

Every `Feature` shall declare at least one member product where it is selected
and at least one other member product it distinguishes from, unless the product
line has only one member product under analysis.

## Traceability completeness

### RULE-004 — Requirement or constraint link

Every `Feature` shall link to at least one requirement or constraint that
specifies expected behavior, performance, quality, safety, cybersecurity, or
release conditions.

### RULE-005 — Evidence link

Every `Feature` shall link to at least one planned or actual evidence artifact.

### RULE-006 — Architecture realization link

Every behavioral or functional `Feature` shall link to at least one architecture
element, unless it is intentionally only a commercial, market, or configuration
feature.

### RULE-007 — Certification or release impact

Every `Feature` relevant to safety, cybersecurity, update behavior, or
operational availability shall identify its release/certification impact.

## Feature-based PLE consistency

### RULE-008 — Bill-of-features consistency

Every selected feature in a `BillOfFeatures` shall exist in the
`FeatureCatalogue`.

### RULE-009 — Feature constraint satisfaction

Every `BillOfFeatures` shall satisfy the feature constraints declared in the
`FeatureCatalogue`.

### RULE-010 — Variation point mapping

Every `VariationPoint` in a shared asset superset shall identify the feature
selection or configuration condition that configures it.

## Future implementation options

- YAML schema could check required fields and ID references.
- SHACL could validate RDF representations of these rules.
- SPARQL could report traceability gaps and impact-analysis slices.
- SysML v2 validation should be added only after a later mapping PR introduces
  `.sysml` artifacts.
