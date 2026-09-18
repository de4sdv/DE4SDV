# O4 execution plan — register, waves, gates and closure boundary

Status: **planning and governance only.** This document and its
machine-readable companion (`o4-execution-register.json`) are the first O4
execution-planning package. The register is **deterministically generated
from the governed integrated review using reviewed, machine-checked
wave-mapping rules** (`o4/ontology-review/`, canonical source
`integrated-review.json`; the review's own text in `REVIEW.md` is parsed for
the open decisions and the PLE dependency bullet). This package changes no
runtime behavior, no ontology semantics, no model content, no
Projection/Profile artifact and no migrated identity set. No O4 semantic
migration is performed here; execution begins only after independent review
of this plan.

The W1–W6 execution waves and W7 decision gate are subordinate work
packages within O4; they do not alter or supersede the O0–O4 migration
lifecycle defined by the Unified Semantic Engineering Plan.

Machine companions (generated, `--check`-validated via
`scripts/check_repo.py`):

- `docs/method-conformance/o4/o4-execution-register.json`
  (`de4sdv.o4-execution-register/v2`) — the complete account of all 93
  reviewed identities with one base (semantic treatment) wave per retained
  target and the W7 decision gate representation.
- `scripts/generate_o4_execution_register.py` — generator/checker
  (`--check`); refuses to produce a register that violates the accounting
  invariants or any curated mapping assumption.
- `tests/test_o4_execution_register.py` — invariant tests, including the
  binding of the frozen O3 13 to
  `de4sdv.semantic.o3_bundle.MIGRATED_IDENTITIES` and negative tests proving
  that a review edit invalidating a mapping assumption fails the gate.

## 1. Source binding

| item | value |
| --- | --- |
| canonical source | `docs/method-conformance/o4/ontology-review/integrated-review.json` (recorded `sha256` in the register) |
| governed review text | `docs/method-conformance/o4/ontology-review/REVIEW.md` (recorded `sha256`; Deliverable 9 bullets and Deliverable 10 decisions are parsed from it) |
| source schema | `de4sdv-ontology-review-integrated/v2` |
| reviewed semantic baseline | `bc2b65abb623e50032f177d566e34e1a41c09f34` |
| source inventory | 93 identities (59 classes, 34 relationships) |
| accepted target | 90 retained = 93 − 1 removal (`derivesNeedFromConcern`) − 2 merges (`IncrementTraceabilityShell`, `validatesFitnessForUse`) |

The register is regenerated only from those sources; the sources are never
edited by this package (they are the accepted governed input).

## 2. Register schema (one row per reviewed identity)

| field | content |
| --- | --- |
| `identity`, `kind` | reviewed identity and its catalog kind (class/relationship) |
| `accounting_status` | `retained` / `merged` / `removed` |
| `membership` | `o3-complete` (frozen 13) / `o4-target` / `merged` / `removed` |
| `merge_into`, `merge_note` | normalized successor + recorded nuance for merged rows (accounted, not targets); a merge must resolve to a retained identity — no vacuous targets |
| `o3_complete` | true for exactly the frozen O3 13 (bound to runtime code) |
| `review_classification` | `classification.sysml_semantic_classification` (e.g. `NATIVE_EXPLICIT`, `NO_NATIVE_SEMANTIC_FIT`) |
| `final_disposition` | `target.disposition` (e.g. `KEEP_NATIVE`, `REDESIGN`, `MERGE`, `REMOVE`) |
| `migration_class` | the review's migration bin (e.g. `MODEL_AUTHORITY_PARITY`, `EXTERNAL_BOUNDARY`) |
| `current_authority` | `current.authority` (legacy-yaml / native-sysml / accepted-library-grounded / external-reference / …) |
| `desired_target_authority` | `target.authority` (verbatim governed statement) |
| `required_model_or_library_change` | `new_modeling_required`, `native_representation_exists`, `grounding`, `proposed_name` |
| `required_semantic_projection_change` | `target.projection_required` |
| `required_api_representation_profile_change` | `target.api_profile_required` |
| `required_runtime_or_consumer_change` | `runtime_support_target`, `traversal_required`, `current_runtime_support` |
| `validation_evidence_requirement` | `target.evidence_needed` list + `current_evidence_state` |
| `blockers`, `open_decisions` | row-level blockers and review decision notes (verbatim) |
| `dependencies` | review dependency notes; `dependency_flags` adds derived flags: `ple`, `canonical_architecture`, `evidence_lineage`, `saf`, `other_targets` (named reviewed identities) |
| `base_wave`, `wave_basis` | exactly one base (semantic treatment) wave per retained target + the governing rule citation |
| `gate_wave`, `gate_decisions`, `gated_by` | the W7 decision/holding gate: `gate_wave = W7` for held rows, their gate decisions (Deliverable 10 items naming the row) and/or row blockers, and the gate source kind |
| `corrections_batch` | Wave-1 correction entries (inventory-description only; no semantic change) |
| `retirement_condition` | the condition under which the authored-YAML row retires as semantic authority (gated rows append the gate clause) |

## 3. Wave derivation rules (deterministic, machine-checked)

Waves are derived from the governed review, not invented. The register
applies, in priority order:

1. `target.merge_into` set → **accounted as merged** (no wave; review
   Deliverable 7 merge list).
2. `migration_class == REMOVE_FROM_ONTOLOGY` → **accounted as removed**.
3. `o3_protected` → **O3-complete (frozen 13)** — outside all O4 waves.
4. Curated W7 gate set (review Deliverable 8 Wave 6 named set + fall-through
   rule **F2**) → **held at the W7 gate** with a curated, machine-checked
   `base_wave` (the re-entry destination; see §4).
5. Review Deliverable 8 Wave 5 named design set (five renames + trace redesign +
   `hasEvidenceStatus` split + `supportedByEvidence` claim design) →
   **W6**.
6. `migration_class == EXTERNAL_BOUNDARY` (the 10 rows named in Deliverable 8 Wave 4)
   → **W5**.
7. `migration_class == MODEL_AUTHORITY_PARITY` (the review's explicit
   26-row count) → **W2**.
8. Review Deliverable 8 Wave 3 core — native constructs and the accepted library,
   minus the three signal-mapping rows that carry parity work → **W3**.
9. Fall-through rule **F1**: application-semantics/vocabulary rows named in
   no Deliverable 8 wave that need definitions + projection rows only (no redesign,
   no owner-gated decision, no blocker) → **W4**.
10. `migration_class == ALREADY_COMPLETE` (remaining) → **closure wave** (closure
    accounting only).
11. Anything else → **generator refuses** (no identity may silently
    disappear or be assigned arbitrarily).

### Fail-closed mapping checks (a review edit invalidates the gate)

Every curated assumption above is checked against the governed review and
`REVIEW.md` at generation time; violating any of them fails the generator
and `check_repo.py`:

- W2 members assigned by migration class must actually carry
  `MODEL_AUTHORITY_PARITY` (and the ungated count must be exactly 26);
- W3 curated members must retain their expected
  native/accepted-library/projection migration class;
- W4 fall-through members must retain the expected low-dependency
  application/projection class and must not acquire an unacknowledged
  blocker;
- W5 members must retain `EXTERNAL_BOUNDARY`;
- W6 named members must retain the redesign/semantic-migration class
  expected by the plan;
- W7-held rows must keep their curated base wave, their expected migration
  class and a live gate source (their named owner decision and/or row
  blocker);
- dependency flags (`ple`, `canonical_architecture`, `evidence_lineage`,
  `saf`) are re-derived from the governed row text/anchors and must equal
  the registered flags (the PLE set additionally binds to decision-9, the
  curated product-line family and the parsed Deliverable 9 PLE bullet);
- merge bindings must keep resolving to retained identities with their
  recorded nuance (including the decision-15 pending successor name);
- the Deliverable 10 decision list must parse to exactly 15 items and every
  curated decision row list must reference existing identities.

`tests/test_o4_execution_register.py` proves the failure mode end-to-end
with negative tests (mutated review → register gate fails).

### Merge accounting

| merged row | successor | nuance |
| --- | --- | --- |
| `validatesFitnessForUse` | `validatedBy` (retained; W6 redesign) | no separate target remains |
| `IncrementTraceabilityShell` | the redesigned per-increment trace-expectation successor intent (`RequiredTraceChain` redesign) | the final successor identity name is **pending decision-15 — not yet decided**; the register does not pretend otherwise |

### Deviation notes (vs the review's Deliverable 8 numbering and the test-shape)

- **Three signal-mapping rows** (`SignalMappingDisposition`,
  `LogicalToSoftwareSignalMappingRecord`,
  `SystemToSoftwareSignalMappingCandidate`) are classified `NATIVE_EXPLICIT`
  *and* carry `migration_class == MODEL_AUTHORITY_PARITY`. The review's Wave
  2 text counts "26 MODEL_AUTHORITY_PARITY rows" explicitly, and their
  assessment says "keep; close doc parity only" — so parity takes
  precedence and they migrate with W2 (recorded as interpretation 1 in the
  register).
- **Seventeen rows are named in no Deliverable 8 wave** (`W4_LOWDEP` ∪
  `W7_FALLTHROUGH` ∪ the closure row — machine-checked; the register's
  interpretation 2 accounts for exactly these 17). Fall-through rule F1:
  ten low-dependency application-semantics/vocabulary rows → W4.
  Fall-through rule F2: six owner-gated architecture/evidence rows
  (`ArchitectureElement`, `Function`, `LogicalElement`, `PhysicalElement`,
  `AcceptanceCriterion`, `AssuranceClaim`) → the W7 gate with base wave W2.
  Closure accounting: `DerivesFromNeed` → the closure wave. The remaining
  five W7-held rows are explicitly named by Deliverable 8 Wave 6 and are
  not fall-through rows.
- **`hasEvidenceStatus` placement (interpretation 3).** The burn-down prose
  mentions `hasEvidenceStatus` among the external-boundary items (Wave 4),
  while the final integrated review row classifies it as
  `REQUIRES_SEMANTIC_MIGRATION` with disposition `REDESIGN`. The final
  structured row classification **takes precedence**: it is handled in the
  redesign wave (W6). The source review is not modified; this is an
  execution-plan interpretation, recorded in the register.
- **Numbering**: the register uses W0…W7 plus the closure wave, where W7 is
  a **decision/holding gate, not a semantic treatment**. Mapping to the
  review's Deliverable 8 numbering: review wave 1 → W1, review wave 2 → W2,
  review wave 3 → W3, review wave 4 → W5, review wave 5 → W6, review wave
  6 → the W7 gate; W0 and W4 are additions (infrastructure/accounting;
  low-dependency semantics), and the closure wave is the review's closure
  arc. The task-shape test (the proposed shape in the O4 planning request):
  W0 ✓ (execution/gating infrastructure), W1 ✓ (straightforward
  native/library adoptions = W3), W2 ✓ (low-dependency application
  semantics = W2 + W4, kept in two waves because the review governs parity
  separately from new semantics), W3 ✓ (architecture/evidence bounded
  redesign = W7-held rows and their base waves), W4 ✓
  (traceability/relationship redesigns = W6), W5 ✓ (PLE/canonical/
  owner-decision dependent = W5 + W7 PLE items), W6 ✓ (residual blockers →
  W7 re-entry), closure ✓ — with wave numbering following the review's own
  numbering wherever the review governs a wave.

## 4. The W7 decision/holding gate and base-wave re-entry

The review's Wave 6 exit rule is: *each blocker resolved by the named
decision/evidence, then normal earlier-wave treatment.* The register
represents this explicitly — W7 is a holding gate whose exit sends each
held identity back into its **base wave** (its proper semantic treatment):

| held row(s) | base wave (re-entry) | gate |
| --- | --- | --- |
| `ArchitectureElement`, `Function`, `LogicalElement`, `PhysicalElement` | W2 — definitions/model authority (umbrella definition homes) | decision-5 |
| `AcceptanceCriterion`, `hasAcceptanceCriterion` | W2 — definitions/model authority (criterion-role lineage; a promotion may adjust the disposition and re-review the base) | decision-6 |
| `AssuranceClaim` | W2 — definitions/model authority (bounded claim vocabulary) | decision-3 |
| `EvidenceContract`, `hasRelevantEvidenceContract` | W2 — definitions/model authority (contract-role lineage / predicate reopening) | row blocker |
| `allocatedTo` | W3 — native allocation projection (typed allocation-end profile) | row blocker |
| `instantiatesCanonicalArchitecture` | W5 — external-boundary typed reference (selector-backed representation, or retirement if the selector design fails) | decision-10 |

The base waves are curated and machine-checked (§3); a review edit that
invalidates one of them fails the register gate instead of silently
changing the re-entry destination.

## 5. Waves, counts and exits

Counts are by **base wave** (the semantic treatment); the W7 gate holds 11
rows across those base waves.

| wave | name | rows | review mapping | exit |
| --- | --- | --- | --- | --- |
| W0 | Execution & gating infrastructure and complete accounting | 0 (infrastructure) | this package | register generated, accounting enforced in `check_repo`, wave rules reviewed |
| W1 | Correction batch (no model changes) | 0 (activity; 3 rows + 2 recorded O3-side) | Deliverable 8 wave 1 | regenerated artifacts bound by the two-commit pattern; CI green at exact head |
| W2 | Definitions parity & model authority | 35 (26 parity + 9 gated definition rows) | Deliverable 8 wave 2 + W7 re-entries | normalized-exact or reviewed-equivalent definition text per row; O2 admission unblocked for these rows |
| W3 | Native/library adoption & projection rows | 11 (10 core + `allocatedTo` re-entry) | Deliverable 8 wave 3 core + W7 re-entry | projection rows generated from model authority; exact-revision equivalence where traversal is claimed |
| W4 | Low-dependency DE4SDV application semantics & vocabulary | 10 | fall-through F1 | model-resident definitions bound + projection rows generated; no redesign |
| W5 | External-boundary contracts | 11 (10 core + `instantiatesCanonicalArchitecture` re-entry) | Deliverable 8 wave 4 + W7 re-entry | contract docs + profile entries; no traversal; blocked-state surfaced wherever queried |
| W6 | Relationship redesigns & traceability | 9 | Deliverable 8 wave 5 | old names retired through the governed transition; no signature silently changed |
| W7 | Decision/holding gate (not a semantic treatment) | 11 held (across W2/W3/W5 bases) | Deliverable 8 wave 6 + F2 | each held row re-enters its base wave when its named decision/evidence resolves |
| closure wave | Closure: authored-YAML consumer retirement & one-authority reproducibility | 1 (+ cross-cutting) | review closure arc | complete inventory accounted; consumers retired or compatibility-generated; one-authority reproducibility demonstrated |

Accounting: 93 = 90 retained (13 O3-complete + 77 O4 targets) + 2 merged +
1 removed; 77 targets = W2 35 + W3 11 + W4 10 + W5 11 + W6 9 + closure 1 —
machine-enforced (`scripts/check_repo.py` fails if the register drifts from
the source or violates the invariants).

## 6. Blockers and open owner decisions grouped by the wave they block

| wave | review open decisions | blocked rows / held rows |
| --- | --- | --- |
| W0 | decision 13 (live-API anchor read-back before stronger-than-export claims) | — |
| W1 | decision 12 (ADR 0009 status wording) | — |
| W2 | decision 3 (`AssuranceClaim`), decision 5 (umbrella definition homes), decision 6 (acceptance criterion), decision 7 (`MethodEvaluationScope` exclusions shape), decision 11 (SAF role-def disposition), decision 14 (Feature/CommonCapability `disjointWith` axiom) | blocked: `MethodEvaluationScope`; held in gate: `ArchitectureElement`, `Function`, `LogicalElement`, `PhysicalElement`, `AcceptanceCriterion`, `hasAcceptanceCriterion`, `AssuranceClaim`, `EvidenceContract`, `hasRelevantEvidenceContract` |
| W3 | decision 4 (EvidenceStatus split — library-side) | held in gate: `allocatedTo` |
| W4 | — | — |
| W5 | decision 9 (PLE configurator authority), decision 10 (canonical architecture source) | blocked: `FeatureConfiguration`; held in gate: `instantiatesCanonicalArchitecture` |
| W6 | decision 1 (five renames), decision 2 (`constrainedBy` semantics), decision 3 (`supportedByEvidence` claim model), decision 4 (status split), decision 8 (trace redesign), decision 15 (trace successor name) | blocked: `constrainedBy`, `realizedBy`, `deployedTo`, `validatedBy`, `hasEvidenceStatus`, `supportedByEvidence` |
| W7 (gate) | gate sources: decision 3, decision 5, decision 6, decision 10 + the row blockers of `EvidenceContract`, `hasRelevantEvidenceContract`, `allocatedTo` | the 11 held rows (see §4) |

The owner decisions that gate closure (review §19 question 10): the redesign
successor vocabularies (decisions 1, 2, 8, 15), the definition-home and
role decisions (decisions 5, 6, 7), the configurator authority (decision 9)
and the canonical-architecture source (decision 10). Everything else is
bounded engineering with the review's evidence requirements.

## 7. Dependencies between waves

- **W2 is the universal enabler.** Parity text and definition homes feed
  W3, W4, W6 and the W7 re-entries (review Deliverable 8 rule: parity
  unblocks the projection and redesign waves).
- **W3 → W4**: the low-dependency semantics rows reuse the adoption/
  projection mechanics proven in W3.
- **W5 is independent of W3** (review Deliverable 8: "wave 3 is independent of
  4"); it needs parity text (W2) but no projection rows. Its PLE rows
  additionally wait on decision 9.
- **W6 requires W2** (successor definition text must exist before
  redesigns bind) and its owner decisions decision 1/decision 2/decision 8/decision 15.
- **W7 is a gate, not a path**: when a named decision resolves, the held
  row re-enters its base wave and completes normal treatment there (no
  parallel redesign path).
- **closure wave requires every wave exit** plus the consumer-retirement inventory
  and the one-authority reproducibility proof.
- **O3 stays frozen throughout**: the 13 O3 identities are outside all
  waves; no O4 wave may change their semantics (review: no amendment
  required; the register binds them to `MIGRATED_IDENTITIES`).

## 8. Recommended sequence

**First implementation wave (after this planning PR):** W1 — the
correction batch. It is the review's own first step, changes no model
content, and establishes the wave-execution evidence mechanics (two-commit
binding, exact-head CI) on real content at near-zero semantic risk.

**First content wave:** W2 parity, starting with a bounded pilot cluster
so the mechanics are proven before the full 26 rows (candidate clusters:
the five method-increment classes + signal-mapping trio; or the
method-context definition-home set). The pilot cluster is chosen by review
at execution time; the register already carries every row's evidence
requirements. W3 can start once its parity dependencies for the specific
rows are bound; W4 follows W3.

**PLE parallelism:** W2–W4 may proceed in parallel with remaining PLE
work, but individual rows carrying PLE dependency flags cannot complete
their authority migration/retirement until their row-level PLE
prerequisites are satisfied. The distinction is preserved:

- **native structural variation** (`VariationPoint`, `Variant`, `variesAt`)
  can be projected (W3) without committing configurator authority — they
  carry PLE dependency flags but no decision-9 gate;
- **configuration/selection authority** (`FeatureConfiguration`,
  `selectsFeature`, `appliesToMemberProduct`, `includesCommonCapability`,
  `selectsVariant`) is governed by PLE-Q/S/A and decision 9 and must not be
  started independently (held in W5 with the `FeatureConfiguration` row
  blocker and the decision-9 gate);
- decision 10 (canonical architecture) gates only the single held W7 row.

No O4 wave authorizes a PLEML commitment or changes the current
configuration authority.

## 9. O4 completion boundary

O4 is **not** complete when all target identities merely have a reviewed
model representation. Closure requires proving, with machine-enforced
accounting:

- the complete reviewed target inventory is accounted for;
- semantic authority has migrated to the intended model/native/library
  sources;
- Semantic Projection coverage is generated from those governed sources;
- the API Representation Profile carries representation mechanics
  separately;
- all production, ingestion, validation, viewer and tooling consumers of
  authored-ontology authority are retired or explicitly retained only as
  compatibility-generated output;
- the authored YAML is no longer an independent semantic authority;
- one-authority reproducibility is demonstrated;
- exclusions, removals and merges are machine-accounted;
- unresolved items cannot silently disappear.

## 10. Regenerating and validating

```bash
python scripts/generate_o4_execution_register.py          # write
python scripts/generate_o4_execution_register.py --check  # verify
python scripts/check_repo.py                              # includes the register check
python -m pytest tests/test_o4_execution_register.py -q
```
