# R0-5: Semantic Projection schema v0 and API Representation Profile v0
(k-slice only: derivesRequirementFromNeed — minimal by design; no universal schema)

## DE4SDV Semantic Projection v0 — one predicate row

Machine-readable, revision-bound, generated from validated model semantics +
reviewed model-resident contract. NOT an independent semantic authority.

```yaml
schema: de4sdv.semantic-projection.v0
revision_binding:            # bound at generation time
  git_commit: <full sha>
  sysml_project: <project id>
  sysml_commit: <commit id>
  generated_from:            # provenance of meaning
    model_definitions: [<element uuids>]
    model_resident_contract: <contract identity>
predicate:
  identity: derivesRequirementFromNeed
  definition: >-
    Requirement R is derived from stakeholder need N. Design-input derivation;
    no satisfaction/allocation/verification/evidence claim.
  domain: Requirement
  range: Need
  canonical_direction: Requirement -> Need
  inverse_navigation_identity: derivedRequirementsOfNeed   # same witness, reversed traversal
  semantic_strength: derivation          # discriminating, stronger than relevance
  semantic_exclusions: []                # none declared at v0
  applicability_scope: de4sdv method increments (System 2)
  native_grounding:
    metaclass: <native derivation relationship metaclass from API evidence>
    witness_uuids_required: [relationship, source, target]
  model_external_boundary: none          # fully model-resident at v0
  support_state: vocabulary-only | supported   # avoids advertising unsupported semantics
```

Not permitted in the projection: serializer property paths, dispatch, importer
quirks, transport behavior (those live in the Representation Profile).

## SysML API Representation Profile v0 — one predicate entry

Separately versioned; carries representation mechanics only. Implemented in
tested Python at v0; may never redefine domain/range/direction/strength.

```yaml
schema: de4sdv.api-representation-profile.v0
profile_identity: <versioned id>
for_predicate: derivesRequirementFromNeed
witness:
  api_metaclass: <metaclass>
  relationship_kind: <membership/relationship kind>
  property_paths:                        # exact serialized paths
    source: <path>
    target: <path>
  direction_extraction: <rule>
  ownership_traversal: <rule>
  reference_vs_containment: <rule>
serializer_importer_compatibility:
  known_omissions: []
  uuid_preservation: single-transaction-required
  out_of_export_risk: <checked closure steps>
completeness_check: <named check, fail-closed>
```

## Acceptance for the v0 pair (K exit evidence)

1. Projection generated only from validated model + reviewed contract (UG-24/25
   gates apply); generation is deterministic (UG-23).
2. Profile mechanics pass positive + adversarial cases against realistic
   serializer shapes; profile change without model change fails the semantic
   compatibility gate (UG-25).
3. Actual runtime consumer answers positive/negative cases; missing witness ->
   incomplete/unsupported, never absence-based pass.
