# Pilot Traceability Queries

The first version keeps queries human-readable. RDF/SPARQL can come later if
this pilot proves useful.

## Product-line classification

- Which candidate characteristics are selected for all member products and
  should be modeled as common capabilities instead of features?
- Which candidate characteristics distinguish one member product from another
  and therefore qualify as features?
- Which features are present in the feature catalogue but never selected in
  any bill-of-features?
- Which selected features violate declared feature constraints?

## Member-product impact

- Which member products include `FEAT-OTA-ROLLBACK`?
- Which member products exclude `FEAT-OTA-ROLLBACK`?
- If `FEAT-OTA-ROLLBACK` changes, which member products, requirements,
  architecture elements, evidence artifacts, and release/certification impacts
  are affected?
- Which affected member products can be derived from a changed feature,
  requirement, architecture element, or evidence artifact rather than asserted
  directly?

## Requirements and architecture traceability

- Which requirements specify `FEAT-OTA-ROLLBACK`?
- Which architecture elements realize the requirements for
  `FEAT-OTA-ROLLBACK`?
- Which variation points are configured by `FEAT-OTA-ROLLBACK`?
- Which shared asset supersets contain those variation points?
- Which trace links are asserted directly, and which are derived from other
  model relationships?

## Evidence and assurance

- Which evidence artifacts verify the requirements linked to
  `FEAT-OTA-ROLLBACK`?
- Which selected features lack planned or actual evidence?
- Which release/certification impacts depend on a changed requirement or
  evidence artifact?

## Future pseudo-SPARQL shape

This is illustrative only. It is not executable in this PR.

```sparql
# Features with missing evidence
SELECT ?feature WHERE {
  ?feature a de4:Feature .
  FILTER NOT EXISTS { ?feature de4:verifiedBy ?evidence . }
}
```

```sparql
# Member products affected by a selected feature
SELECT ?product WHERE {
  ?product a de4:MemberProduct ;
           de4:hasBillOfFeatures ?bill .
  ?bill de4:selectsFeature de4:FEAT-OTA-ROLLBACK .
}
```
