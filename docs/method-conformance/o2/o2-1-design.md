# O2.1 — Semantic Projection v1 and API Representation Profile v1 (design record)

**Base:** merged O1 baseline on `main`, commit
`9dc0779ba20745d3d0a7eca15e76891b64911ddc` (PR #249, merged).

**Scope:** exactly the seven settled c1 method-conformance identities whose
representation/equivalence review completed in O1:

`MethodPhase`, `MethodContractObligation`, `EvaluationScopeMembership`,
`EvaluationSourceKind`, `TestedScopeDeclaration`,
`RetainedExecutionRecordReference`, `AcceptanceAttestationReference`.

**Governing inputs:** the DE4SDV Unified Semantic Engineering Plan v1.2
(section 8.1: Semantic Projection / API Representation Profile; section 8.2:
O0–O4 migration states; section 9: identity and provenance requirements) and
the DE4SDV Method Conformance Plan (§4: graph roles — these identities are
reusable vocabulary / method-contract schema, never engineering subjects;
§5: revision-qualified identity, names as presentation aids only; §7: the
typed method-contract schema this vocabulary materializes). Where historical
v1.1 wording survives in old code comments, v1.2 governs.

## What this stage does and does not do

```text
generated in O2
!=
model authority activated
!=
runtime dispatch switched
!=
legacy YAML retired
!=
support automatically promoted
```

- Generation is **not authority activation**: this stage adds no runtime
  read of the artifacts, switches no traversal/query authority, retires no
  authored YAML authority, and changes no evaluator behavior
  (`phase_contract()`, `increment_status()`, `method_gaps()`,
  `next_obligation()` are untouched). O3 owns authority transition; O4 owns
  authored-ontology retirement.
- **No support promotion**: every generated row is `vocabulary-only`; the v1
  builders accept no promotion input at all (no boolean shortcut, no
  attestation flag). Promotion is a later, explicitly reviewed,
  evidence-bearing step.
- **O1 inventory != semantic source**: the generator never reads
  `docs/method-conformance/o1/semantic-authority-inventory.json`,
  `authority-review-decisions.yaml`, or `phase1-inventory-review.md`. The O1
  inventory is migration governance and supplies no semantic field. This is
  machine-checked: the artifacts' bound inputs contain no O1 path, a checkout
  without any O1 directory generates identically, and decoy O1 data cannot
  manufacture a row.
- **Projection v0 preserved**: `de4sdv/semantic/projection.py` (the K slice:
  `derivesRequirementFromNeed` pair, revision-bound closure attestation) is
  byte-unchanged. The v1 module is additive, imports nothing from v0, and
  does not yet emit K predicates. Adding the v1 foundation mutates no v0
  behavior.
- **`MethodEvaluationScope` excluded**: its documentation equivalence is
  reviewed (Layer-B governance), but its structural exclusions-with-rationale
  gap remains open — reviewed text equivalence is not structural admission.
  The model remains the reviewed representation contract for that identity;
  O2.1 simply does not generate from an unsettled structural representation.
  A regression proves the identity is model-resident and discoverable yet
  absent from O2.1 output.
- **`DerivesFromNeed` excluded**: its class-definition equivalence review
  remains separate and its accepted K relationship semantics are unaffected;
  no O2.1 class row is generated.
- **Relationship and native-verification work deferred**: `VerificationCase`,
  `hasSubject`, `verifiedBy` (O2.2) and `derivesRequirementFromNeed`,
  `derivedRequirementsOfNeed`, `hasRelevantArchitecture` (O2.3) remain
  admitted to the overall O2 set (13 identities) and are machine-locked as
  absent from O2.1 output. The v1 schema is relationship-capable for those
  later phases; no relationship row is emitted now.

## Chosen layout and why

| Path | Role |
|---|---|
| `de4sdv/semantic/projection_v1.py` | v1 architecture: admission machine-locks, model-side derivation, artifact builders, profile compatibility gate, committed-artifact consistency check. Build-time/governance module; runtime-inert. |
| `scripts/generate_semantic_projection_v1.py` | offline deterministic generator with `--check` (wired into `scripts/check_repo.py`). |
| `docs/method-conformance/o2/o21-admission.yaml` | the machine-locked reviewed O2.1 admission boundary as explicit governance data (not a runtime artifact; never read by the semantic runtime). |
| `docs/method-conformance/o2/semantic-projection-v1.json` | generated DE4SDV Semantic Projection v1 (semantics). |
| `docs/method-conformance/o2/api-representation-profile-v1.json` | generated SysML API Representation Profile v1 (representation mechanics). |
| `tests/test_semantic_projection_v1.py` | positive/negative/adversarial/admission/compatibility/runtime-independence suite. |

Why this matches the plans: the Unified Plan names the Semantic Projection a
"first-class, machine-readable, revision-bound artifact" (section 8.1) and
requires a separately versioned SysML API Representation Profile for
representation mechanics; the K slice already established the two-artifact
split with v0, and the merged O1 stage established the committed,
revision-bound generated-artifact pattern (`--check` + repository gate +
two-commit binding). This stage continues that pattern instead of inventing a
second one.

Why it does not turn O1 governance artifacts into semantic authority: the
admission manifest encodes **which** identities O2.1 may emit — a reviewed
migration boundary — and supplies **no** engineering semantics. Every field
that asserts engineering meaning for a projected concept (identity grounding
contract, semantic kind, documentation, typed member structure, library base)
is derived from the governed model declarations via the ontology/kernel
contract's declaration locators (locators only — the contract's `definition`
prose is never read). Governance, projection-contract, representation-profile,
and provenance metadata are NOT model-derived and are explicitly separated
(see "Projection contract vs model-derived semantics" below). O1 review
metadata (authority classification, evidence state, text-equivalence review)
appears nowhere in the generated rows; tests machine-lock this.

The precise invariant: **every field that asserts engineering meaning for a
projected concept is derived from the governed model representation;
governance, projection-contract, representation-profile, and provenance
metadata are explicitly separated and identified as such.** No claim is made
that literally every field of the artifact is model-derived.

## Semantic derivation (per identity)

Model-derived concept fields — derived exclusively from the governed model
representation:

- **semantic identity** — the admitted governed vocabulary identity; its API
  resolution contract is the ingestion validation rule (declaredName +
  `@type` + serializer-recorded source-file provenance resolving to exactly
  one element id), consumed at runtime through `KernelBindingIndex`; no
  name/path/doc fallback exists (ADR 0011 discipline).
- **semantic kind** — from the governed declaration kind (`enum def` →
  enumeration, `item def` → item); the declaration kind is cross-verified by
  the block locator itself. Anything else fails closed.
- **definition documentation** — every `doc` comment at the declaration
  body's direct lexical depth (SysML v2 documentation ownership: a doc
  comment is owned by the element whose body it lexically sits in; uniform
  lexical containment). Member-body docs (e.g. per-literal docs) are member
  documentation and never join the definition text. Concept-specific
  boundary statements carried by that model documentation stay verbatim in it.
- **typed member structure** — attributes with their declared types
  (governed classes resolve by identity against the contract's class set;
  the closed Kernel/SysML scalar set `String`/`Natural`/`Boolean` resolves to
  the pinned Kernel Data Type Library) or enumeration literals with their
  member documentation. Unmodeled member forms fail closed.
- **authored default expressions** — an ABSENT default stays absent
  (`"default_expression": null`); an AUTHORED expression is recorded verbatim
  from the model source and never evaluated: `attribute x : String` ≠
  `attribute x : String = ""` ≠ `= false` ≠ `= 0` — absence, empty string,
  boolean, and numeric values are all distinguishable in the generated
  representation. A malformed bare `=` with an empty expression fails closed.
- **standard-library base grounding** — recorded with `provenance: implied`
  (toolchain-materialized implied Subclassification). The resolution
  mechanics live in the representation profile.

## Projection contract vs model-derived semantics

The generic claim policy is projection/schema metadata, NOT per-concept SysML
semantic content, and is serialized exactly once at the projection level
(`projection_contract`):

- `semantic_scope` — vocabulary/schema definitions only;
- `does_not_assert` — obligation satisfaction, method-phase completion,
  acceptance or approval, evidence validity/freshness, tested-scope equality,
  evaluation success;
- `derivation_rule` — the precise model-derivation invariant above;
- `external_artifact_treatment` — referenced external identities remain
  external; generation neither absorbs nor evaluates them;
- `runtime_boundary` — generation is not authority activation; the runtime
  does not read the artifact; support promotion is a separate reviewed
  evidence-bearing step.

These statements are generator/schema-defined; they are deliberately NOT
attached to individual concept rows (and tests prove they never appear as
per-concept fields). The admission scope (`scope` block) is a governance
decision; the representation mechanics live in the representation profile.

## API identity and representation profile

The profile records representation mechanics only and cannot redefine
meaning (a compatibility gate compares every echoed binding contract against
the model-derived projection). Concrete API element UUIDs are **not
invented** and no current API element UUID is claimed: this stage produces no
validated SysML API project/commit closure (`api_binding` is explicitly
`unclaimed`), because licensed validation and full-model ingestion are
privileged/CI-owned and aarch64-local Syside is unavailable. The profile
instead records the exact machine-checkable identity resolution contract, the
witnessed membership/typing/external-reference mechanics, the closed
library-type target table, serializer/importer compatibility, and the
fail-closed completeness check.

Evidence basis for the mechanics: retained privileged full-model API
ingestion run `10195168006` (candidate `0a23902…`). That retained run is a
**shape oracle only** — representation-shape evidence, never proof of
current exact-revision closure; its model text predates the c1 documentation
reconciliation and is not a semantic source for generation. The mechanics
were cross-verified against it during this stage; the artifacts state this
scope explicitly, and all seven identities remain `vocabulary-only`.

## Revision binding

The artifacts bind `source_revision` — a Git commit containing every bound
input byte-for-byte — plus per-input content digests, validated exactly like
the O1 inventory binding (commit existence, ancestry, per-input content
equality; a stale revision cannot pass by string reuse). The binding
distinguishes:

- **generation-software inputs** (the v1 module, its machinery imports, the
  generator script), from
- **semantic-model inputs** (the admission manifest, the ontology/kernel
  contract locators, the governed model files).

Two-commit pattern: Commit A carries the architecture, generator, tests,
design record, and admission manifest; Commit B carries the generated
artifacts bound to A (plus the repository gate wiring). Regeneration over
identical inputs is byte-identical; `--check` fails on any drift.

## Known limitations / intentionally deferred

- No validated API project/commit closure is produced in this stage
  (privileged/CI-owned); the profile's `api_binding` stays unclaimed rather
  than inventing a revision label.
- No K predicates are emitted by v1 yet; the v1 schema foundation is
  relationship-capable for O2.2/O2.3.
- `MethodEvaluationScope`, `DerivesFromNeed`, the O2.2/O2.3 set, and the
  retired/blocked/rename-required identities are intentionally not generated;
  their dispositions are preserved exactly as reviewed in O1.
- Support promotion and any authority transition remain O3 decisions.

## Verification

Gate wiring: `scripts/check_repo.py` runs the v1 `--check` alongside the O1
inventory check. The suite covers: seven-identity positive scope against the
real production declarations; admission machine-locks (manifest vs frozen
locks, both directions); the full negative scope; the adversarial matrix
(extra vocabulary, missing declaration, ambiguous grounding, wrong kind,
missing documentation, unresolved typing, unsupported member form, O1-costume
rows, representation-vs-admission); v0 compatibility; runtime independence;
and committed-artifact consistency. Licensed Syside validation and privileged
ingestion are not dispatched by this stage: no model files and no
repository-workflow inputs change.
