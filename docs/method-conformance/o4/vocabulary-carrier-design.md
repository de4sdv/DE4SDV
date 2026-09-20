# O4 vocabulary-relationship definition carriers — design (prepared)

Status: **PREPARED — machinery only; no admission is active.** The reviewed
definition carriers for the vocabulary-relationship family await the
method-owner definition acceptance (`accepted_ref`), so this package ships
with `admitted: []` and generates nothing. Nothing here changes model
content, ontology data, runtime behavior, or any migrated identity.

Governed inputs: the canonical integrated review (O4 ontology review) and the
O4 execution register. The candidate family is *derived and machine-locked*
against the review; this document records the mechanism, not new decisions.

## The problem this closes

Five reviewed vocabulary-only relationships (`recordsGap`,
`recordsAssumption`, `addressesConcern`, `selectedViewpoint`, `producesView`)
need a **model-resident semantic definition**, a generated Projection
representation, an API-representation profile entry, and explicitly **no
executable traversal claim**. The O2+ layer recorded this as its
"definition-carrier machinery gap": the semantics are governed, but no
reusable carrier representation existed to carry them.

A sixth relationship, `hasStakeholder`, carries the identical reviewed
profile and is therefore a family member, but remains **excluded from
admission** by decision-11 (the SAF role-def adoption/publication
disposition gates its range). The family lock distinguishes the mechanical
profile match from that governance exclusion.

## The carrier representation (one reusable mechanism)

| layer | representation | carries | must never carry |
| --- | --- | --- | --- |
| model | kernel `connection def` whose typed ends carry the predicate's domain and range, and whose owned documentation carries the reviewed definition and claim boundary (the accepted requirement-derivation carrier pattern) | the reviewed definition text, normalized-exact; end typings | runtime strategy, cardinality claims |
| Projection | one generated row per admitted relationship: identity, definition, domain/range lineage, direction, strength, support `vocabulary-only`, `traversal: false` | semantic meaning | representation mechanics, UUID claims |
| API profile | one entry per admitted relationship: `model-resident-connection-carrier`, mechanics text, carrier file/declaration | representation mechanics | a second semantic statement |
| runtime | none — vocabulary-only support; no traversal implemented or claimed | — | any `sysml_mapping` (refused outright; that field carries implemented runtime-strategy meaning and must not be overloaded) |

## Fail-closed rules (all machine-checked)

1. **Family lock.** `expected_candidates` must equal the set derived from the
   canonical review (relationships whose target is exactly
   `KEEP_VOCABULARY_ONLY` + model-resident method vocabulary authority +
   projection required + profile required + no traversal + vocabulary-only).
   A review edit that adds or removes such a row breaks generation.
2. **Exclusions are visible.** An excluded member needs a non-empty governed
   reason, must be a family member, and can never be admitted.
3. **Acceptance is required.** Every admission carries a non-empty
   `accepted_ref` (the method-owner acceptance); missing acceptance refuses
   generation — the machinery never treats a reviewed *proposal* as accepted.
4. **Unknown keys refuse.** An admission carries exactly `identity`,
   `carrier`, `ends`, `accepted_ref` (and optional `library_types`).
5. **No traversal overloading.** Any admission containing `sysml_mapping` is
   refused.
6. **Definition parity.** The carrier declaration must exist (body-carrying,
   parsed by the verified O1 declaration/brace machinery) and its owned
   documentation must equal the reviewed definition normalized-exact (the
   verified O1 normalization; never fuzzy).
7. **End resolution.** Each end must appear as `end <feature> : <Type>` in
   the carrier block; each type must be a model declaration found under the
   model roots or be explicitly listed in `library_types` (accepted-library
   constructs, e.g. native concern/viewpoint/view types, are not
   repo-resident).
8. **Carrier placement.** The carrier file must be a model file; governance
   data paths are refused.

## What remains before any admission (tomorrow's steps, post-acceptance)

1. Method owner accepts the five proposed definitions (the consolidated
   vocabulary-definition acceptance item of the owner-decision packet);
   record the acceptance reference.
2. Author the five kernel carriers (connection defs with typed ends and the
   reviewed docs) in the method-context kernel package; add the
   corresponding kernel mappings to the authored ontology data so the
   ontology-kernel contract set equation still holds.
3. Move the five rows into `admitted` with carrier/ends/accepted_ref filled.
4. Extend generation: emit the carrier projection/profile artifacts (bound to
   the carrier revision, mirroring the O2+ two-commit pattern) and register
   the check in `check_repo`.
5. Regenerate the O1 inventory rows for these identities (definition
   carrier observed) under the two-commit pattern; update the O4 register
   row evidence; run licensed validation via CI; then the rows may complete
   their normal O4 treatment.

## Boundaries

- Read-only reuse of the O1 normalization/declaration machinery; no new
  parser, no name-based resolution.
- No authored-ontology data is edited by this package; no YAML retirement;
  O3 stays frozen at exactly 13.
- The runtime never reads this document or the module.