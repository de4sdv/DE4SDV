# O4 definition-admission batch 2 — design record

> **O4 Wave C2 note.** The authored ontology was deleted in Wave C2. The 54
> manifest-held contract fields (domain/range/strength, kernel mapping kinds,
> ontology relations, serializer mechanics) are now governed by the admission
> manifest alone and labeled so in every row (owner decision D9); their last
> authored-ontology parity, which tests lock them to, is
> [`closure/contract-equivalence.json`](closure/contract-equivalence.json).
> The five former deprecated aliases are `retired-name` rows that the runtime
> refuses with `retired; use <successor>` (owner decision D4). The text below
> is the original design record.

Status: **draft engineering evidence** (Wave B). Base: `main` at
`c12792b8b352c72cabbe58f095189af9272df4b3` (Wave A #333 plus its rebind
chain #334–#336). Governing inputs:
the O4 execution register, the October 2026 owner record, ADR 0020, the
approved semantic decisions and the W6 transition plan.

## Problem

After Wave A every authored definition has a model home, but only 48
identities have a generated Semantic Projection row: the frozen O3 13,
definition batch 1 (22), O2+ (8) and the W4 vocabulary carriers (5). The
remaining retained register rows, the ontology classes that are not register
rows and the W6 successor predicates still reach consumers only through the
authored YAML. The Wave B model-authority bundle cannot drop that YAML path
while those identities have no generated row.

## Scope (derived, machine-locked)

`definition-admission-batch2.yaml` admits 57 rows. The family is derived and
tests lock it in both directions:

| group | rows | source of the set |
| --- | --- | --- |
| retained register rows without another generated layer | 42 (21 classes, 21 relationships) | register rows with `accounting_status: retained`, not O3-complete, minus O2 chain, batch 1, O2+ and carriers |
| ontology classes that are not register rows | 12 | authored classes absent from the register (successor and scoped-assurance classes) |
| W6 successor predicates that are not register rows | 2 | `hasValidationScenario`, `hasRegulatorySource` (`allocatedTo` is a register row) |
| deprecated name of a merged register row | 1 | `validatesFitnessForUse` (model retirement record `oldValidationInverse`) |

Two non-retained identities are **owner-visible exceptions** (recorded in the
manifest `exceptions` and echoed in the projection `scope.exceptions`):
`IncrementTraceabilityShell` (merged; its successor `IncrementTraceObligations`
is admitted) and `derivesNeedFromConcern` (removed by O1 c4; no model home by
design). No retained row is an exception.

## Admission classes

| class | rows | model home read by the generator | runtime claim in the artifact |
| --- | --- | --- | --- |
| `definition` | 31 classes | owner block (`<kind> def` or `package`) + one directly owned Documentation selected by name and index; normalized-exact against the reviewed definition | `vocabulary-only` |
| `external-reference` | `EvidenceArtifact`, `Baseline`, `hasEvidence`, `capturedInBaseline` | documentation home or vocabulary-role comment; profile echoes the accepted external-reference profile entry | `external` |
| `relationship-vocabulary` | 12 | directly owned named `<predicate>VocabularyRole` comment; every `about` target resolves in the file or through a direct import | `vocabulary-only` |
| `relationship-runtime` | `specifiesFunction`, `hasRelevantEvidenceContract` | documentation home or vocabulary-role comment; profile carries serializer mechanics | `runtime-mapped-candidate` |
| `successor` | `allocatedTo`, `hasValidationScenario`, `hasRegulatorySource` | vocabulary-role comment + every `SuccessorRelationRecord` usage with the predicate (set equality) + carrier ends | `runtime-mapped-candidate` |
| `deprecated-alias` | `realizedBy`, `deployedTo`, `validatedBy`, `constrainedBy`, `validatesFitnessForUse` | `SuccessorRetirementRecord` usage whose predicate is the identity; the named successor record must exist over the named carrier | `deprecated-alias` |

Boundaries carried per row: `native-grounding` (architecture umbrella terms,
`Interface`, `ValidationScenario`, `AssuranceClaim`, `EvidenceStatus`),
`external-content` (`ArchitectureDecisionRecord` and the four external
references), `ple-no-configurator-authority` (`FeatureConfiguration` and the
four selection predicates; decision-9, ADR 0006; the profile states
`configurator_authority: none`), `historical-redesign` (`TraceLink`,
`RequiredTraceChain`, `hasEvidenceStatus`).

### `hasRelevantEvidenceContract`

The range is represented by the owner-adopted type discriminator, not a name
prefix: `relation.range.discriminator` names the kernel lineage
`requirement def EvidenceContract` and the exact closure of eight AEBS
contract definitions. The generator verifies that each pinned definition
specializes `EvidenceContract` and that its file imports the owning kernel
package. A repository test scans every model root and proves no other
definition specializes it. The profile keeps the authored dependency
mechanics; adopting the discriminator in the runtime is the Wave B consumer
change, and the live population is exact-SHA privileged-run evidence.

### Deprecated aliases

Aliases are documented names. `answer_mode: successor-facts` means a
consumer may answer the old name with the successor's facts over the named
carrier, under the successor's (weaker) meaning; the old signature is never
translated into the successor contract. `constrainedBy` is
`documentation-only` because its model retirement record states that
`hasRegulatorySource` is "not an alias": no fact is answered under the old
name.

## Gate resolution

Rows whose register entry is gated list, per gate, the governance record that
resolved it. Tests require the gate set to equal the register's
`gate_decisions` plus `row-blocker` when the row has blockers, and every
reference to resolve to an existing record fragment that names the decision.

| gate | resolved by |
| --- | --- |
| decision-1, -2, -3, -4, -8, -11, -15 | `approved-semantic-decisions.yaml` topics 1–6 |
| decision-5, -6, -7 | ADR 0020 D1, D2, D3 (owner-accepted engineering defaults, 2026-10-05) |
| decision-9 | October owner record, Wave A table (keep the external catalogue authority) |
| decision-10, decision-14 | October owner record items 8 and 7 (ADR 0020 decisions 8 and 7) |
| row blockers | the record that supplied the missing home or decision (ADR 0020 D1–D4 and the D4 follow-up, approved topics, W6 transition plan) |

Resolving a gate unblocks **admission only**. Runtime support targets keep
their forward obligations in the manifest (exact-revision traversal evidence,
the allocation-end closure, the evidence-contract population evidence, the
open `hasAcceptanceCriterion` cardinality, the PLE adoption gates, the
canonical-usage selector). The register itself is not edited: it remains the
generated record of the integrated review.

## Contract fields that are not model witnesses

The model does not structurally carry the relationship domain/range of the
vocabulary-only predicates, the mapping kind of native/external classes, or
the serializer mechanics of the runtime-mapped predicates. Those are reviewed
manifest fields, locked by tests to the authored ontology, and every generated
row labels them with `contract_source`. Nothing is inferred from names.

## Artifacts and binding

| path | role |
| --- | --- |
| `docs/method-conformance/o4/definition-admission-batch2.yaml` | governed manifest (`de4sdv.o4-definition-admission-batch2/v1`) |
| `docs/method-conformance/o4/definition-batch2-projection.json` | generated projection (`de4sdv.o4-definition-batch2-projection/v1`) |
| `docs/method-conformance/o4/definition-batch2-profile.json` | generated profile (`de4sdv.o4-definition-batch2-profile/v1`) |
| `de4sdv/semantic/definition_projection_batch2.py` | build-time module; runtime-inert |
| `scripts/generate_definition_projection.py` | shared generator (`--batch 1|2|all`, `--check`) |
| `tests/test_definition_projection_batch2.py` | family, parity, negative, binding and coverage suite |

Bound inputs: the manifest, this record, the module, the generator, the two
executed shared modules (`authority_inventory.py`, `projection_o2p.py`), every
model file the generator reads, and the accepted external-reference profile.
The batch-1 module is imported by the generator but does not execute during
batch-2 generation, so it is not bound. The pair is bound by the two-commit
pattern and listed in `scripts/verify_generated_chain.py`; `run_check_errors`
is wired into `scripts/check_repo.py`.

## Not done here

No runtime module reads the pair; no production selector, entry point or
workflow changes; no authored-YAML retirement; no O1 decision rows are
re-staged (the O1/O2/O3 records are frozen history in Wave C).
