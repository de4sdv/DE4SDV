# O4 W4 vocabulary-relationship definition acceptance — bounded engineering review

Status: **accepted-as-engineering-review-evidence** (bounded, revision-bound;
NOT a personal owner approval and NOT authority activation).

## Scope of this review (bounded)

This document closes the *definition acceptance* for exactly the five O4 W4
vocabulary-only relationships whose canonical integrated review target is
`KEEP_VOCABULARY_ONLY` + model-resident method vocabulary authority +
projection required + profile required + no traversal + `vocabulary-only`
support:

| identity | reviewed definition (verbatim from the canonical review) | domain | range |
| --- | --- | --- | --- |
| recordsGap | Engineering increment explicitly records an unresolved engineering/evidence gap. | EngineeringIncrement | Gap |
| recordsAssumption | Engineering increment explicitly records an assumption relevant to its bounded work. | EngineeringIncrement | Assumption |
| addressesConcern | Engineering increment records an explicitly reviewed concern within its scope; no automatic concern satisfaction. | EngineeringIncrement | Concern |
| selectedViewpoint | Engineering increment records a viewpoint explicitly selected for its review questions. | EngineeringIncrement | Viewpoint |
| producesView | Engineering increment identifies a view artifact produced as an increment deliverable. | EngineeringIncrement | View |

Source of record: `docs/method-conformance/o4/ontology-review/integrated-review.json`
(`source_revision: bc2b65abb623e50032f177d566e34e1a41c09f34`, 93 rows). The
definition texts above are *read from that review at check time* — the
admission machinery compares them against each carrier declaration's owned
documentation normalized-exact, so this document is a review record, never a
second source of definition text.

## Review method

1. For each identity, the canonical integrated review records **exactly one
   definition and signature**; no alternative definition, no alternative
   domain/range, and no alternative disposition is documented for any of the
   five. Where an alternative existed it was resolved in the review before
   this acceptance.
2. Each definition was read for **unambiguity**: every term in each sentence
   has a single operative reading within DE4SDV method vocabulary, and each
   sentence names exactly one act (records / records / records / records /
   identifies) over exactly one object kind. No definition asserts
   satisfaction, resolution, coverage, conformance, or acceptance.
3. Each reviewed domain/range pair was checked against the modeled carrier
   ends: domain `EngineeringIncrement`, ranges `Gap` (kernel
   `part def IncrementGap`), `Assumption` (kernel
   `part def IncrementAssumption`), `Concern`/`Viewpoint` (generic
   increment-scoped carrier range bases), `View` (accepted standard-library
   view definition).
4. The claim boundary recorded with each carrier (explicit recording /
   selection / identification only; no traversal) was checked to be strictly
   narrower than the reviewed definition — the carrier never claims more than
   the definition states.

Result: all five definitions were found **unambiguous and admissible as
engineering review evidence**. Acceptance of these definitions is a review
act on the definitions, not a runtime or support-state change: support stays
`vocabulary-only` and no traversal is implemented or claimed.

## Explicit non-claims

- This is engineering review evidence recorded in-repository. It is **not**
  a personal owner approval, not a method-owner signature, and not a
  compliance or certification statement.
- `hasStakeholder` is **not** accepted here. It carries the identical
  mechanical review profile but stays excluded from admission by decision-11
  (the SAF role-def adoption/publication disposition gates its range).
- No runtime behavior changes: the runtime never reads the carrier document,
  the acceptance review, or the generated artifacts.
- No ontology YAML or O1 decision data is edited by this acceptance; the
  kernel mappings required for the new carrier declarations are identified in
  `vocabulary-carrier-design.md` for the integrating change.

## Anchor records (machine-checked)

The admission document references this file per identity
(`…#recordsGap`, `…#recordsAssumption`, `…#addressesConcern`,
`…#selectedViewpoint`, `…#producesView`); the machinery refuses any
`accepted_ref` that does not resolve to a repository governance document
carrying the `accepted-as-engineering-review-evidence` marker and recording
the identity.
