# O2.2 — Semantic Projection v1.1 extension (design record)

**Base:** permanent `main` after O2.1 completion, commit
`4be6a7bfbfb9f737dd525c9f1c7e22a47fdd8218` (PR #252 squash-merge). The O2.1
baseline (`semantic-projection-v1.json` /
`api-representation-profile-v1.json`, bound to
`f1095fc027cc20948d8fb7933964b96d443920e2`) remains **immutable**.

**Delivery:** squash-safe two-PR sequence — Stage A (PR #253) delivered the
additive implementation foundation and was squash-merged as
`7dbbf4b83ea2a14e2aa1b8998564b3167b99c9a1` (topology: Stage A squash → X =
`7dbbf4b…`; Stage B artifacts bind to X; Stage B squash → Y with X still an
ancestor of Y — a feature-branch commit can never serve as durable
`source_revision` in a squash-only repository). Stage B publishes the v1.1
artifacts bound to that permanent revision and activates repository
enforcement.

**Scope:** exactly the three settled c2/c3 identities:

- `VerificationCase` — native verification-case construct;
- `hasSubject` — `Requirement -> MemberProduct` subject relation;
- `verifiedBy` — `Requirement -> VerificationCase` native
  verification-objective relation.

**Governing inputs:** the DE4SDV Unified Semantic Engineering Plan v1.2
(section 3 authority boundaries; section 8.1 projection/profile content;
section 8.2 O-states; section 10 predicate contracts; section 17 UG-24/25/28;
section 18 verification) and the DE4SDV Method Conformance Plan (§4 graph
roles; §5 identity; §7–§8 contract/result semantics). v1.2 governs on
conflict. The merged O1 reviewed decisions (c2 verification grounding, c3
subject grounding, c5 §17.2 verifiedBy source-domain closure) determine
admission and the reviewed contract locks; O1 governance artifacts are never
read at generation and supply no semantic field.

## What this stage does and does not do

```text
generated in O2.2
!=
model authority activated
!=
runtime dispatch switched
!=
legacy contract authority retired
!=
support automatically promoted
```

- Generation is **not authority activation**: no runtime read of the v1.1
  artifacts, no traversal/query-authority switch, no authored-contract
  retirement, no evaluator change (`phase_contract()`,
  `increment_status()`, `method_gaps()`, `next_obligation()` untouched).
  O3 owns authority transition; O4 owns authored-ontology retirement.
- **No support promotion**: the established DE4SDV support rule applies —
  without structured exact-revision closure evidence, `support_state` is
  `vocabulary-only`. All three rows emit `vocabulary-only`; generation of a
  row is not promotion, an existing runtime mapping is not promotion, and
  retained historical API evidence is not current exact-revision closure.
  The existing runtime-mapping fact is recorded only as non-support profile
  metadata (`runtime_mapping_state = existing-not-authority`). No other
  support vocabulary exists and the builders accept no promotion input.
- **Additive, never mutating**: the projection extension independently
  extends the O2.1 **projection** baseline; the profile extension
  independently extends the O2.1 **profile** baseline. Each `extends` pin
  records and verifies path, schema, source revision, and artifact digest;
  both baselines are bound inputs. The O2.1 seven are guarded — never
  re-emitted, never re-bound.
- **O1 inventory != semantic source**: the generator never reads
  `semantic-authority-inventory.json`, `authority-review-decisions.yaml`, or
  `phase1-inventory-review.md` (machine-checked: a checkout without any O1
  directory generates identically; decoy O1 data cannot manufacture a row).
- **O2.3 untouched**: `derivesRequirementFromNeed`,
  `derivedRequirementsOfNeed`, `hasRelevantArchitecture` remain absent and
  guarded.

## Source-of-truth and separation rule (corrected)

**Model/contract-derived semantic core.** Per identity the projection
derives `identity`, `semantic_kind`, domain, range (with the governed
lineage anchor declarations), canonical engineering direction, semantic
strength, the load-bearing scope restrictions, the native grounding identity
at the semantic level, and model witness anchors from the validated
authoritative representation at the bound source revision:

- the **reviewed representation contract** — the governed ontology/kernel
  contract's declared entries, consumed read-only as the current
  permitted-interpretation authority for this unmigrated scope (Unified Plan
  section 3). The consumed fields are locked against the reviewed O2.2 locks;
  domain/range/strategy/strength/witness drift fails closed (explicit review
  required — never silent regeneration);
- the **governed model declarations** — the lineage anchors
  (`requirement def RequirementCandidate`, `part def ProductLineMemberProduct`)
  located exactly once per file with an adjacency guard, and the governed
  verification constructs located structurally by declaration shape
  (`verification def <'VC-AEBS-009D-DE'>ConsciousOverrideVerification`, its
  objective `verify` witnesses, and the six declared usages specializing it).

**Projection-schema / reviewed claim-boundary metadata.** The explicit
negative laws and claim boundaries live in the projection-level
`projection_contract.identity_claim_boundaries` block as schema-level
reviewed contract metadata — never as per-row engineering-semantic fields.
They are transcribed from the merged reviewed decisions and governing plans
and machine-locked by tests; the generator reads no review artifact at
generation time.

**Representation profile.** All serializer/API mechanics — witness
strategies, membership types, property paths, owner chains, direction
extraction, the ReferenceSubsetting bridge, ownership-chain traversal,
serialized-shadow mechanics, resolution rules, library grounding mechanics
(implied edges, the controlled library-proof step, run-pinned anchors, the
retained-run evidence), and API metaclasses — live only in the
representation profile. The profile echoes the projection's semantic
contract per identity (`semantic_contract_echo`) and the compatibility gate
fails closed if the echo contradicts it: representation mechanics can never
redefine domain, range, canonical direction, semantic strength, scope
restrictions, or claim boundaries (UG-25 analogue).

Explicitly NOT semantic sources: the O1 migration artifacts, review prose at
generation time, element/qualified names, package paths, source filenames, or
doc text.

## Semantic content and claim boundaries

- **`VerificationCase`** — a native construct that carries a verification
  objective/check-for-satisfaction purpose; the projection records the
  native grounding identity at the semantic level. Claim boundary: an
  objective carrier only — no execution occurred, no result exists, no
  satisfaction, approval, acceptance, or certification is asserted. The
  library-qualified role identities, implied-edge mechanisms, API
  metaclasses, and evidence/export mechanics live in the representation
  profile; the metaclass alone is not the semantic proof (UG-28).
- **`verifiedBy`** — the requirement is declared as a verification objective
  of the returned verification case (coverage relation only). Named negative
  laws stay explicit at the schema-level claim-boundary block: generic
  Dependency, SubjectMembership, `VerificationMethod` metadata, retained
  execution records, evaluation records, name-only correspondence, and
  verification-looking names are NOT witnesses. Source-domain closure: the
  anchored source must be machine-proven in the governed Requirement domain;
  unresolved anchors fail closed. The reverse traversal direction never
  reverses the modeled fact; its serialization mechanics live in the profile.
- **`hasSubject`** — a DE4SDV application semantic: native subject-membership
  semantics narrowed by two load-bearing restrictions (source in the governed
  Requirement lineage, target in the governed MemberProduct lineage — the
  restrictions are the predicate's meaning, not query conveniences). Excluded
  by meaning, at the schema-level claim-boundary block: Need-sourced
  subjects, benches, increments, claim subjects, generic untyped part usages,
  and same-named parts outside the lineage; `RequirementVerificationMembership`
  is not a witness; and `hasSubject` is not selection, configuration
  membership, allocation, realization, instantiation, satisfaction, or
  verification success. The witness serializer mechanics live in the profile.

## Artifact layout

| Path | Role |
|---|---|
| `de4sdv/semantic/projection_o22.py` | O2.2 extension architecture: admission locks, contract-locked semantic-core derivation, independent baseline anchoring (projection pin → projection baseline; profile pin → profile baseline), artifact builders, profile compatibility gate (per-identity semantic-contract echo), committed-artifact check. Build-time/governance module; runtime-inert. |
| `scripts/generate_semantic_projection_o22.py` | offline deterministic generator with `--check`; gate registered in `scripts/check_repo.py`. |
| `docs/method-conformance/o2/o22-admission.yaml` | machine-locked O2.2 admission boundary (governance data; never runtime-read). |
| `docs/method-conformance/o2/semantic-projection-v1.1.json` | published extension projection (Stage B), bound to `7dbbf4b…`, extends `semantic-projection-v1.json`. |
| `docs/method-conformance/o2/api-representation-profile-v1.1.json` | published extension profile (Stage B), bound to `7dbbf4b…`, extends `api-representation-profile-v1.json`. |
| `tests/test_semantic_projection_o22.py` | positive/negative/adversarial/lock/preservation/runtime-independence/committed-artifact/gate-wiring suite. |

Why an extension (v1.1) instead of an in-place widening of v1: the v1
artifacts are revision-bound and repository-gated; mutating them would
invalidate the completed O2.1 binding by design. The extension keeps every
artifact's `source_revision` a real commit that contains its inputs and
remains an ancestor of the checked-out revision, and makes the cumulative O2
surface (7 + 3 = 10) machine-provable. Assembly model: the extension
architecture is additive (new module, new generator, new manifest, new
artifacts); the O2.1 module is imported for its frozen locks and shared
machinery but never modified. The projection and profile are assembled from
one semantic build with independent baseline pins and validated by the
compatibility gate before serialization.

## Admission locks

- admitted: exactly `VerificationCase`, `hasSubject`, `verifiedBy`;
- sequencing union: the frozen 13-identity O2 admission (imported from the
  O2.1 module);
- cumulative surface: exactly ten distinct identities (O2.1 seven + O2.2
  three), with the O2.1 seven guarded against re-emission;
- guarded: the 24-identity guard set machine-derived from the frozen locks
  (O2.1 seven + O2.3 three + the O2.1-guarded identities), each with a
  reviewed reason — retired ≠ absent, blocked ≠ absent, rename-required ≠
  admitted, reviewed text equivalence ≠ structural admission.

## Revision binding and the gate

Artifacts bind `source_revision` (commit existence, ancestry, per-input
content equality, recorded digests — the shared O2.1/O1 binding machinery)
plus two INDEPENDENT `extends` pins (the projection extension → the O2.1
projection baseline; the profile extension → the O2.1 profile baseline).
Each pin records path, schema, source revision, and artifact digest; both
baselines are bound inputs. The gate enforces, per pin: digest equality
against the committed baseline bytes and baseline-`source_revision` ancestry
of the extension `source_revision`. Generation-software inputs and
semantic-model inputs are listed separately. `api_binding` stays explicitly
`unclaimed`: no current exact-revision API closure exists (privileged/
CI-owned).

## Known limitations / intentionally deferred

- The v1.1 artifacts are published and repository-gated: `scripts/check_repo.py`
  now enforces O1 inventory + O2.1 v1 + O2.2 v1.1 fail-closed; the committed
  artifacts are byte-checked against deterministic regeneration, and missing
  artifacts are errors — never "missing means pass". (Delivery history:
  Stage A shipped the machinery without artifacts; Stage B bound them to the
  permanent Stage A squash-merge commit.)
- `api_binding` unclaimed; retained privileged runs are shape evidence only.
- O2.3 identities, `MethodEvaluationScope`, `DerivesFromNeed`, and the
  retired/blocked/rename-required identities remain untouched by design.
- No runtime or model changes: the subject/verification semantics already
  exist in the model; no parallel SysML relationships were added.

## Verification

Stage B suite additions: committed artifacts exist, parse, byte-match
deterministic regeneration, bind to `7dbbf4b…`, keep `api_binding` unclaimed
and all rows `vocabulary-only`, retain the independent extends pins with
digests matched against the committed baseline bytes, and stay
mechanics-free; a real-git end-to-end gate test proves editing either
committed artifact fails the gate (and restoring it passes); the repository
wiring is proven by sentinel-failure, all-gates-pass, and pass-through-spy
tests. Stage A suite (63 tests) remains: positive scope against the real
production
declarations (definition, six usages, three verify targets, lineage anchors);
projection/profile separation (no serializer mechanics in projection rows —
banned-key and banned-term scans; mechanics asserted present in the profile;
per-identity semantic-contract echo equality and the compatibility gate's
fail-closed behavior on a mutated echo and on support promotion); baseline
pairing (projection extends projection baseline; profile extends profile
baseline; not blindly identical; both bound inputs; shared source revision
verified not assumed; per-baseline missing/swapped-schema/revision-less/edited
fail-closed, parametrized over both baselines); support-state honesty (all
rows `vocabulary-only`; removed O2.2 vocabulary absent; no promotion input;
runtime-mapping fact only as non-secret profile metadata); claim boundaries
(schema-level block present with the reviewed registry laws covered and
machine-locked; no row serializes them); admission machine-locks (manifest vs
frozen locks both directions, cumulative ten, guard set equality); negative
scope (guarded sample absent; O2.1 baseline not re-emitted;
model-resident-but-guarded identities absent); adversarial matrix (extra
vocabulary; missing/duplicate declarations; wrong structural identity;
foreign usage lineage; wrong metaclass shape; missing objective witnesses;
contract drift in domain/strategy/witness; non-file-mapped anchors);
O1-independence (no O1 dir, decoy O1); preservation (v1 gate green; v0
immutable); runtime independence (no runtime import/read; ontology not
retired); Stage A gate behavior (missing-artifact errors; generator `--check`
non-permissive). Licensed Syside validation and privileged ingestion are not
dispatched: no model files change.