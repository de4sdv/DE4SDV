# O2+ design — native/library grounding & projection layer (accelerated safe-set 1)

Date: 2026-09-19 · Plan: O4 execution plan (`docs/method-conformance/o4/o4-execution-plan.md`)
· Review: Deliverable 8 wave 3 (native/library projection rows) · Base: `main` after
W2 batch 6 recovery = `2668342c40b0477dab8bb73f353463f0a09cd7b6`.

## Scope

First bounded execution of review wave 3 for the reviewed **safe subset** of
already-native/library constructs, grouped into one accelerated safe-set PR
together with the W5 boundary-record parity work (`ArchitectureDecisionRecord`,
`Baseline`) and the W3 `IncrementSize` definitions-parity closure:

- `VariationPoint`, `Variant` — native SysML v2 variation/variant constructs
  (`api_profile_required`; no projection row required by the review);
- `Concern`, `Viewpoint`, `View` — native SysML v2 concern/viewpoint/view
  constructs (`projection_required`);
- `VerificationMethod`, `usesVerificationMethod` — library-mapped native
  metadata (grounding record only);
- `IncrementSize` — model-resident bounded vocabulary (parity + projection row).

Every other candidate row is recorded in `o2p-admission.yaml` `excluded` with
its concrete reason (owner decision, W7 hold, PLE gate, unsatisfied
dependency, or the definition-carrier machinery gap for vocabulary
relationships).

## The layer

`semantic-projection-o2plus.json` carries one row per admitted identity:
construct, exact-fit finding, standard-construct reference, a verified witness
(the model construct that carries the meaning, checked to exist at generation
time), outputs (projection row / api-profile entry / traversal — matching the
reviewed flags exactly), support `vocabulary-only`, and the claim boundary.
`api-representation-profile-o2plus.json` carries representation mechanics for
the `api_profile_required` rows (native variation/variant membership notation;
pinned toolchain reference).

Grounding records are *bound*: both artifacts bind a `source_revision` that
contains every bound input byte-for-byte (the witness model files, this
admission manifest, the module, the generator, and the syside-pin workflow),
validated fail-closed by the same source-binding machinery the O1/O2 gates
use. The reviewed evidence item ("exact-fit + standard-construct grounding
record at a bound revision") is therefore satisfied mechanically.

## Boundaries

- **No authority activation**: the runtime never reads these artifacts; no
  support promotion; no traversal implemented or claimed (all admitted rows
  are `traversal_required: false`).
- **Frozen surfaces machine-locked**: no frozen O2 identity (v1/v1.1/v1.2
  thirteen) and no frozen O3 identity may be admitted or emitted.
- **No silent expansion**: generation iterates ONLY `admitted`; the admitted
  set and per-row flags are machine-locked against the reviewed values.
- **Exclusions are visible**: every considered-but-excluded row carries its
  reason in the admission manifest (machine-validated for the hard gates
  `allocatedTo`, `EvidenceStatus`, `variesAt`, `FeatureConfiguration`,
  `instantiatesCanonicalArchitecture`).

## Delivery

Two-commit pattern inside the feature PR (sources → inventory → v1.1 → v1.2 →
scope), with the O2+ pair bound to the feature sources commit and included in
the permanent post-squash recovery chain (Rebind 1: O1 + v1.1 + O2+; Rebind 2:
v1.2 + scope).

## Remaining work after this safe-set

- vocabulary-relationship definition carriers (`recordsGap`,
  `recordsAssumption`, `addressesConcern`, `selectedViewpoint`,
  `producesView`) — requires a governed carrier representation + inventory
  machinery support (a follow-up increment);
- T/E evidence-reference design (`EvidenceArtifact`, `hasEvidence`,
  `capturedInBaseline`) — authoring + review;
- decision-gated rows (decisions 4/9/10, W7 holds) — re-enter on resolution.
