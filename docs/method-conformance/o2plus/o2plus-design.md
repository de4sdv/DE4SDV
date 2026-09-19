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

`semantic-projection-o2plus.json` carries one **grounding/admission record**
per admitted identity: construct, exact-fit finding, standard-construct
reference, a verified witness (the model construct that carries the meaning,
checked to exist at generation time), the governed `category`, support
`vocabulary-only`, and the claim boundary. A grounding record is NOT a
semantic projection output.

Each record's `outputs` block states which outputs the identity actually
carries, and it must equal the reviewed flags exactly:

- `outputs.projection_row == projection_required` — actual projection outputs:
  `Concern`, `Viewpoint`, `View`, `IncrementSize` (four rows; the artifact's
  `scope.projection_outputs` mirrors this set);
- `outputs.api_profile_entry == api_profile_required` — actual
  `api-representation-profile-o2plus.json` entries: `VariationPoint`,
  `Variant` (native variation/variant membership notation; pinned toolchain
  reference);
- `outputs.traversal == traversal_required` — none.

`VerificationMethod` and `usesVerificationMethod` are **grounding-record-only**
(no projection output, no profile entry). The reviewed flags are never
reinterpreted because the record lives in a file named
`semantic-projection-o2plus.json`.

Grounding records are *bound*: both artifacts bind a `source_revision` that
contains every bound input byte-for-byte, validated fail-closed by the same
source-binding machinery the O1/O2 gates use. Bound inputs are classified:
**semantic-model inputs** (`semantic_model_revision.model_inputs` — only the
governed witness model files), **tooling/toolchain provenance**
(`tooling_revision` — the pinned Syside workflow/version reference, kept
revision-bound for reproducibility but supplying no semantics), and
**program inputs** (this manifest, the module, the generator). The reviewed
evidence item ("exact-fit + standard-construct grounding record at a bound
revision") is therefore satisfied mechanically.

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

Multi-commit pattern inside the feature PR (sources → inventory + v1 → v1.1 +
O2+ → v1.2 → scope), with the O2+ pair bound to the feature sources commit
(plus amendments) and included in the permanent post-squash recovery chain.
Because `de4sdv_method_process.sysml` is a v1-bound input (the `IncrementSize`
change), the permanent recovery is a **three-stage chain**: Rebind 1 (O1 +
**v1** + O2+ → `M2`), Rebind 2 (v1.1 → `M3`, `extends v1 @ M`), Rebind 3
(v1.2 + O3 scope → `M4`, `extends v1.1 @ M2`). Final topology: `v1 @ M`,
`v1.1 @ M2`, `v1.2 @ M3`, O2+ `@ M`.

## No separate semantic-kind field

Rows carry no `semantic_kind` field: the governed `category` (`native`,
`library-mapped-native`, `model-resident-vocabulary`) carries the precise
distinction once, and a duplicated kind field would invite misclassification
(for example `IncrementSize` or the library-mapped rows as "native
pointers").

## Remaining work after this safe-set

- vocabulary-relationship definition carriers (`recordsGap`,
  `recordsAssumption`, `addressesConcern`, `selectedViewpoint`,
  `producesView`) — requires a governed carrier representation + inventory
  machinery support (a follow-up increment);
- T/E evidence-reference design (`EvidenceArtifact`, `hasEvidence`,
  `capturedInBaseline`) — authoring + review;
- decision-gated rows (decisions 4/9/10, W7 holds) — re-enter on resolution.
