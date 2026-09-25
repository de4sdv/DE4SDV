# O4 definition-admission batch 1 — design record

Date: 2026-09-25 · Base: permanent `main` after safe-set 2 recovery
(`ba2069c06d51f838769f378cd35024eb445cfc88`). Governing inputs: the O4
execution plan and register (`docs/method-conformance/o4/`), the integrated
review, and the O1 reviewed decisions.

## Scope

**First definition-admission stage**: exactly the 21 retained, ungated O4 rows
whose reviewed W2 definitions-parity treatment is complete and whose target
requires BOTH a generated Semantic Projection row and an API Representation
Profile entry:

`Assumption`, `BlockedRealizationBranchRecord`, `DeferredProductLineScope`,
`EngineeringIncrement`, `FeatureIncrement`, `Gap`,
`IncrementEngineeringQuestion`, `IncrementLifecycleDecision`,
`LogicalToSoftwareSignalMappingRecord`, `MemberProduct`,
`MissingRealizationRecord`, `Need`, `NeedsRequirementsIncrement`,
`ProblemStatement`, `ProductLine`, `ProductLineCharacteristic`,
`RegulatoryConstraint`, `Requirement`, `SignalMappingDisposition`,
`SystemLayer`, `SystemToSoftwareSignalMappingCandidate`.

The admitted family is **derived and machine-locked** (`definition-admission.yaml`
header; tests): O4 register rows that are `o4-target`, not O3-frozen, in base
wave W2/W5, with no gate decision and no W7 hold, requiring both a projection
row and a profile entry, carrying a definitions-parity stage, and not already
admitted in another generated layer (O2 chain / O2+ / W4 carriers).

### Considered and not admitted

| identity | reason |
| --- | --- |
| `Scenario` | Bounded pattern grounding only; no model-side declaration; definition parity stays open. |
| `ArchitectureDecisionRecord`, `Baseline` | External-boundary rows: the canonical review/register require no projection and no profile (flags False/False, runtime support `external`); content authority stays external. Their generic O1 residual string mentioning O2 admission conflicts with the structured flags and is recorded for bounded review — not silently resolved here. |
| `IncrementSize` | Vocabulary-only W3 row; requires neither a projection row nor a profile entry. |
| carrier rows | Already admitted through the W4 carrier pair. |

## What this stage does and does not do

```text
definition admission (generated rows from the reviewed model representation)
!=
authority transition (O3 owns it)
!=
authored-YAML retirement (O4 closure owns it)
!=
support promotion / traversal / runtime read
```

- The generator reads ONLY the governed model documentation and the admission
  manifest. It never reads O1 migration artifacts (`semantic-authority-inventory.json`,
  `authority-review-decisions.yaml`); a checkout without them generates
  identically, and decoy O1 data cannot manufacture a row.
- Every generated row stays `support: vocabulary-only`, `traversal: false`,
  `api_identity: unclaimed`; the profile carries representation mechanics only
  and claims no API element identity. No runtime module imports this machinery
  or reads the artifacts.
- A `differs` documentation observation requires a recorded
  `reviewed-equivalent` bounded review; `normalized-exact` requires a null
  equivalence. No fuzzy comparison anywhere (the shared
  `doc_text_observation` machinery: equality after cosmetic normalization).
- The emitted `definition.documentation` is the **model-owned** doc text
  (model-authoritative direction); the manifest's `reviewed_definition` is the
  parity oracle only and is machine-locked against the authored ontology and
  the integrated review by tests.

## Artifacts and schemas

| path | role |
| --- | --- |
| `docs/method-conformance/o4/definition-admission.yaml` | governed admission manifest (scope + oracles; `de4sdv.o4-definition-admission/v1`) |
| `docs/method-conformance/o4/definition-projection.json` | generated Semantic Projection rows (`de4sdv.o4-definition-projection/v1`) |
| `docs/method-conformance/o4/definition-profile.json` | generated API Representation Profile entries (`de4sdv.o4-definition-profile/v1`) |
| `de4sdv/semantic/definition_projection.py` | build-time/governance module; runtime-inert |
| `scripts/generate_definition_projection.py` | offline deterministic generator with `--check` |
| `tests/test_definition_projection.py` | scope/family/parity/negative/binding/runtime-independence suite |

The pair is **separate from the frozen O2 chain**: it does not extend
`semantic-projection-v1.2` and is not a v1.3; the frozen 13-identity O2/O3
surface is byte-unchanged and machine-locked as not-admitted here.

## Source binding (two-commit pattern)

Bound inputs: the admission manifest, the five model files carrying the
admitted declarations, this design record, the module, and the generator.
Audited exclusion: `de4sdv/semantic/authority_inventory.py` executes during
generation (block/doc extraction and normalization) but is the shared parity
machinery bound as an input of the O1 inventory artifact; it is deliberately
not re-bound here, and the end-to-end regeneration tests exercise the
observation semantics it provides.

Procedure (the O2+/safe-set pattern — an artifact can only bind to a commit
that already contains its inputs):

1. Commit A1: manifest, design record, module, generator, tests, O1 decision
   updates for the 21 rows, and the deliberate later-batch pin updates.
2. Regenerate the O1 inventory from those sources and generate the pair
   (`python scripts/generate_definition_projection.py --source-revision <A1>`)
   — commit A2 (Commit-B gate: the committed-artifact tests are red between A1
   and A2 by design).
3. Register `run_check_errors` in `scripts/check_repo.py` (fail-closed) as
   part of the same change; `--check` must pass at the pushed head.

## Remaining after this batch

The 21 rows' O1 residual becomes the forward runtime note (exact-revision
traversal evidence still outstanding; support remains vocabulary-only). The
authored YAML stays authoritative; O4 overall remains open.