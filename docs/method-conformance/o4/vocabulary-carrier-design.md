# O4 vocabulary-relationship definition carriers — design

Status: **ADMITTED — five carriers admitted as engineering review evidence;
Projection/Profile generation integrated; runtime unchanged.** The reviewed
definition carriers for the vocabulary-relationship family (`recordsGap`,
`recordsAssumption`, `addressesConcern`, `selectedViewpoint`, `producesView`)
now exist as model-resident kernel `connection def`s, and the carrier
machinery emits the generated Projection and API-representation Profile
artifacts bound to a Git source revision. Nothing here changes runtime
behavior, ontology data, or any migrated identity.

Governed inputs: the canonical integrated review (O4 ontology review), the
bounded engineering-review acceptance document
(`vocabulary-carrier-acceptance-review.md`), and the O4 execution register.
The candidate family is *derived and machine-locked* against the review; this
document records the mechanism, not new decisions.

## The problem this closed

Five reviewed vocabulary-only relationships needed a **model-resident
semantic definition**, a generated Projection representation, an
API-representation profile entry, and explicitly **no executable traversal
claim**. The O2+ layer recorded this as its "definition-carrier machinery
gap": the semantics were governed, but no reusable carrier representation
existed to carry them.

A sixth relationship, `hasStakeholder`, carries the identical reviewed
profile and is therefore a family member, but remains **excluded from
admission** by decision-11 (the SAF role-def adoption/publication disposition
gates its range). The family lock distinguishes the mechanical profile match
from that governance exclusion.

## The carrier representation (one reusable mechanism)

| layer | representation | carries | must never carry |
| --- | --- | --- | --- |
| model | kernel `connection def` whose typed ends carry the predicate's domain and range, and whose owned documentation carries the reviewed definition and claim boundary (the accepted requirement-derivation carrier pattern) | the reviewed definition text, normalized-exact; end typings | runtime strategy, cardinality claims |
| Projection | one generated row per admitted relationship: identity, definition, domain/range lineage, direction, strength, support `vocabulary-only`, `traversal: false` | semantic meaning | representation mechanics, UUID claims |
| API profile | one entry per admitted relationship: `model-resident-connection-carrier`, mechanics text, carrier file/declaration | representation mechanics | a second semantic statement |
| runtime | none — vocabulary-only support; no traversal implemented or claimed | — | any `sysml_mapping` (refused outright; that field carries implemented runtime-strategy meaning and must not be overloaded) |

Carrier declarations live in
`textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_vocabulary_carriers.sysml`
(package `DE4SDV_MethodVocabularyCarriers`):

- ends: domain `recordingIncrement`/`reviewingIncrement`/`selectingIncrement`/
  `producingIncrement : EngineeringIncrement`; ranges `gap : IncrementGap`,
  `assumption : IncrementAssumption`, `concern : IncrementConcern`,
  `viewpoint : IncrementViewpoint`, `view : View`.
- `IncrementConcern` and `IncrementViewpoint` are generic increment-scoped
  range bases declared in the carrier package itself: the reviewed predicates
  are generic over the range kind, and no repo-resident generic concern or
  viewpoint definition existed. Concrete method/SAF concern and viewpoint
  definitions may specialize them in a later reviewed step; this package
  changes nothing about the existing concrete declarations.
- `View` is the accepted standard-library view definition (`Views` library),
  declared per admission via `library_types` because it is not repo-resident.

## Fail-closed rules (all machine-checked)

1. **Family lock.** `expected_candidates` must equal the set derived from the
   canonical review (relationships whose target is exactly
   `KEEP_VOCABULARY_ONLY` + model-resident method vocabulary authority +
   projection required + profile required + no traversal + vocabulary-only).
   A review edit that adds or removes such a row breaks generation.
2. **Exclusions are visible.** An excluded member needs a non-empty governed
   reason, must be a family member, and can never be admitted.
3. **Acceptance is required and resolvable.** Every admission carries a
   non-empty `accepted_ref`; it must resolve to a repository governance
   document under `docs/` that carries the
   `accepted-as-engineering-review-evidence` marker and records the identity.
   Free-text references and personal owner-approval claims are refused. The
   five admissions close as engineering review evidence
   (`vocabulary-carrier-acceptance-review.md`), never as a personal approval.
4. **Unknown keys refuse.** An admission carries exactly `identity`,
   `carrier`, `ends`, `accepted_ref` (and optional `library_types`).
5. **No traversal overloading.** Any admission containing `sysml_mapping` is
   refused.
6. **Definition parity.** The carrier declaration must exist (body-carrying,
   parsed by the verified O1 declaration/brace machinery) and its owned
   documentation must equal the reviewed definition normalized-exact (the
   verified O1 normalization; never fuzzy).
7. **End resolution.** Each end must appear as `end <feature> : <Type>` in the
   carrier block; each type must be a model declaration found under the
   model roots or be explicitly listed in `library_types` (accepted-library
   constructs, e.g. the standard-library `View`, are not repo-resident).
8. **Identity binding.** The reviewed identity of each end (the review's
   domain/range) is resolved against the authored ontology: a repo-resident
   identity's end type must be exactly the ontology-mapped declaration (name
   and file); a native/external identity's end type must be a listed
   accepted-library type or carry an explicit `declaration` pin that resolves
   to that exact declaration (and agrees with the ontology mapping where one
   exists). A type claimed both as a model declaration and as a listed
   library type is refused.
9. **Carrier placement.** The carrier file must be a model file; governance
   data paths are refused.

## Generation (two-commit source binding)

`scripts/generate_vocabulary_carriers.py` emits:

- `docs/method-conformance/o4/vocabulary-carriers-projection.json`
- `docs/method-conformance/o4/vocabulary-carriers-profile.json`

Both artifacts reuse the verified O1/O2+ binding machinery: a `binding` block
records the source revision, the bound-input digests (admission document,
canonical review, carrier model file, acceptance review, this design
document, the module, and the generator), and explicitly unclaimed
`artifact_commit`/`api_binding` states. Generation refuses a revision that
does not contain every bound input byte-for-byte, and the check refuses
committed bytes that differ from regeneration.

Procedure (the O2+/O1 two-commit pattern — the artifact can only bind to a
commit that already contains its inputs):

1. Commit the admission inputs (carrier model file, `vocabulary-carriers.yaml`,
   acceptance review, design, module, generator).
2. `python scripts/generate_vocabulary_carriers.py` (binds to that commit).
3. Commit the two generated artifacts.
4. `python scripts/generate_vocabulary_carriers.py --check` must pass;
   registering `run_check_errors` in `scripts/check_repo.py` is the
   integrating change's step.

## Ontology-kernel contract (integration decision)

The five carrier declarations and the two generic range bases are new
declarations in the governed method-kernel directory, so the ontology-kernel
contract set equation requires them to be classified in the same change. The
integrating change classifies **all seven as `kernel_sync.exclusions` with
reasons** (`approach/framework/ontology/de4sdv-basic-ontology.yaml`):

- the five carriers are the model-resident definition carriers OF existing
  ontology relationship identities. Mapping them would require inventing five
  new ontology class identities that the canonical review does not contain
  (the canonical identity set stays the review's 93 rows), while the
  definition parity they exist for is already machine-enforced by the O4
  carrier machinery against that same canonical review;
- `IncrementConcern`/`IncrementViewpoint` are generic range-kind bases, not
  ontology identities of their own.

The ontology's existing `Concern`/`Viewpoint`/`View` classes stay as they are
(native/library grounding); this change does not re-ground them.

## Boundaries

- Read-only reuse of the O1 normalization/declaration and O2+ binding
  machinery; no new parser, no name-based resolution.
- The carrier package itself edits no authored ontology data; the integrating
  change adds `kernel_sync` exclusions only (no ontology classes, no
  relationship data). No YAML retirement; O3 stays frozen at exactly 13.
- The runtime never reads this document, the acceptance review, the
  admission document, or the generated artifacts.
- SysML validation of the new carrier package is requested through the
  repository's licensed validation path (local `scripts/validate_sysml.py`
  or maintainer-run privileged Syside validation); this package makes no
  claim about validation it did not run.
