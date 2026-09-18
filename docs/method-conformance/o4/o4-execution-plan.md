# O4 execution plan — register, waves, gates and closure boundary

Status: **planning and governance only.** This document and its
machine-readable companion (`o4-execution-register.json`) derive the O4
execution register mechanically from the accepted review
(`o4/ontology-review/`, canonical source `integrated-review.json`). They
change no runtime behavior, no ontology semantics, no model content, no
Projection/Profile artifact and no migrated identity set. No O4 semantic
migration is performed here; execution begins only after independent review
of this plan.

Machine companions (generated, `--check`-validated via
`scripts/check_repo.py`):

- `docs/method-conformance/o4/o4-execution-register.json`
  (`de4sdv.o4-execution-register/v1`) — the complete account of all 93
  reviewed identities with one proposed migration wave per retained target.
- `scripts/generate_o4_execution_register.py` — generator/checker
  (`--check`); refuses to produce a register that violates the accounting
  invariants.
- `tests/test_o4_execution_register.py` — invariant tests, including the
  binding of the frozen O3 13 to `de4sdv.semantic.o3_bundle.MIGRATED_IDENTITIES`.

## 1. Source binding

| item | value |
| --- | --- |
| canonical source | `docs/method-conformance/o4/ontology-review/integrated-review.json` (recorded `sha256` in the register) |
| source schema | `de4sdv-ontology-review-integrated/v2` |
| reviewed semantic baseline | `bc2b65abb623e50032f177d566e34e1a41c09f34` |
| source inventory | 93 identities (59 classes, 34 relationships) |
| accepted target | 90 retained = 93 − 1 removal (`derivesNeedFromConcern`) − 2 merges (`IncrementTraceabilityShell`, `validatesFitnessForUse`) |

The register is regenerated only from that source; the source is never
edited by this package (it is the accepted governed input).

## 2. Register schema (one row per reviewed identity)

| field | content |
| --- | --- |
| `identity`, `kind` | reviewed identity and its catalog kind (class/relationship) |
| `accounting_status` | `retained` / `merged` / `removed` |
| `membership` | `o3-complete` (frozen 13) / `o4-target` / `merged` / `removed` |
| `merge_into` | named successor for merged rows (accounted, not a target) |
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
| `proposed_wave`, `wave_basis` | exactly one O4 wave per retained target + the governing rule citation |
| `corrections_batch` | Wave-1 correction entries (inventory-description only; no semantic change) |
| `retirement_condition` | the condition under which the authored-YAML row retires as semantic authority |

## 3. Wave derivation rules (mechanical)

Waves are derived from the governed review, not invented. The register
applies, in priority order:

1. `target.merge_into` set → **accounted as merged** (no wave; review
   Deliverable 7 merge list).
2. `migration_class == REMOVE_FROM_ONTOLOGY` → **accounted as removed**.
3. `o3_protected` → **O4-complete (frozen 13)** — outside all O4 waves.
4. Review Deliverable 8 Wave 6 named set + fall-through rule **F2** (rows carrying
   named owner decisions: umbrella definition homes decision 5, acceptance
   criterion decision 6, assurance claim decision 3, evidence contract, canonical
   architecture) → **W7**.
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
   no owner-gated decision) → **W4**.
10. `migration_class == ALREADY_COMPLETE` (remaining) → **closure wave** (closure
    accounting only).
11. Anything else → **generator refuses** (no identity may silently
    disappear or be assigned arbitrarily).

### Deviation notes (vs the review's Deliverable 8 numbering and the test-shape)

- **Three signal-mapping rows** (`SignalMappingDisposition`,
  `LogicalToSoftwareSignalMappingRecord`,
  `SystemToSoftwareSignalMappingCandidate`) are classified `NATIVE_EXPLICIT`
  *and* carry `migration_class == MODEL_AUTHORITY_PARITY`. The review's Wave
  2 text counts "26 MODEL_AUTHORITY_PARITY rows" explicitly, and their
  assessment says "keep; close doc parity only" — so parity takes
  precedence and they migrate with W2. This is the only place the
  register's membership differs from the literal review-Wave-3 name list
  (13 → 10 rows).
- **Seventeen rows are named in no Deliverable 8 wave.** Fall-through rules F1/F2
  place them: ten low-dependency application-semantics/vocabulary rows →
  W4; six architecture/evidence rows carrying named owner decisions →
  W7; one already-model-authoritative row (`DerivesFromNeed`) → the closure
  wave (accounting only).
- **Numbering**: the register uses W0…W7 plus the closure wave; mapping to the
  review's Deliverable 8 numbering: review wave 1 → W1, review wave 2 → W2,
  review wave 3 → W3, review wave 4 → W5, review wave 5 → W6, review wave
  6 → W7; W0 and W4 are additions (infrastructure/accounting; low-dependency
  semantics), and the closure wave is the review's closure arc. The
  task-shape test (the proposed shape in the O4 planning request):
  W0 ✓ (execution/gating infrastructure), W1 ✓ (straightforward
  native/library adoptions = W3), W2 ✓ (low-dependency application
  semantics = W2 + W4, kept in two waves because the review governs parity
  separately from new semantics), W3 ✓ (architecture/evidence bounded
  redesign = W7 members), W4 ✓ (traceability/relationship redesigns = W6),
  W5 ✓ (PLE/canonical/owner-decision dependent = W5 + W7 PLE items), W6 ✓
  (residual blockers → W7 re-entry), closure ✓ — with wave numbering
  following the review's own numbering wherever the review governs a wave.

## 4. Waves, counts and exits

| wave | name | rows | review mapping | exit |
| --- | --- | --- | --- | --- |
| W0 | Execution & gating infrastructure and complete accounting | 0 (infrastructure) | this package | register generated, accounting enforced in `check_repo`, wave rules reviewed |
| W1 | Correction batch (no model changes) | 0 (activity; 3 rows + 2 recorded O3-side) | Deliverable 8 wave 1 | regenerated artifacts bound by the two-commit pattern; CI green at exact head |
| W2 | Definitions parity | 26 | Deliverable 8 wave 2 | normalized-exact or reviewed-equivalent definition text per row; O2 admission unblocked for these rows |
| W3 | Native/library adoption & projection rows | 10 | Deliverable 8 wave 3 core | projection rows generated from model authority; exact-revision equivalence where traversal is claimed |
| W4 | Low-dependency DE4SDV application semantics & vocabulary | 10 | fall-through F1 | model-resident definitions bound + projection rows generated; no redesign |
| W5 | External-boundary contracts | 10 | Deliverable 8 wave 4 | contract docs + profile entries; no traversal; blocked-state surfaced wherever queried |
| W6 | Relationship redesigns & traceability | 9 | Deliverable 8 wave 5 | old names retired through the governed transition; no signature silently changed |
| W7 | Gated/blocked closures (incl. architecture-semantics homes) | 11 | Deliverable 8 wave 6 + F2 | each blocker resolved by the named decision/evidence, then normal earlier-wave treatment |
| closure wave | Closure: authored-YAML consumer retirement & one-authority reproducibility | 1 (+ cross-cutting) | review closure arc | complete inventory accounted; consumers retired or compatibility-generated; one-authority reproducibility demonstrated |

Accounting: 93 = 90 retained (13 O3-complete + 77 O4 targets) + 2 merged +
1 removed — machine-enforced (`scripts/check_repo.py` fails if the register
drifts from the source or violates the invariants).

## 5. Blockers and open owner decisions grouped by the wave they block

| wave | review open decisions | rows carrying row-level blockers |
| --- | --- | --- |
| W0 | decision 13 (live-API anchor read-back before stronger-than-export claims) | — |
| W1 | decision 12 (ADR 0009 status wording) | — |
| W2 | decision 7 (`MethodEvaluationScope` exclusions shape), decision 11 (SAF role-def disposition), decision 14 (Feature/CommonCapability `disjointWith` axiom) | `MethodEvaluationScope` |
| W3 | decision 4 (EvidenceStatus split — library-side) | — |
| W4 | — | — |
| W5 | decision 9 (PLE configurator authority) | `FeatureConfiguration` |
| W6 | decision 1 (five renames), decision 2 (`constrainedBy` semantics), decision 3 (`supportedByEvidence` claim model), decision 4 (status split), decision 8 (trace redesign), decision 15 (trace successor name) | `constrainedBy`, `realizedBy`, `deployedTo`, `validatedBy`, `hasEvidenceStatus`, `supportedByEvidence`, `TraceLink`, `RequiredTraceChain` |
| W7 | decision 3 (`AssuranceClaim`), decision 5 (umbrella definition homes), decision 6 (acceptance criterion), decision 9 (PLE-Q/S/A closure), decision 10 (canonical architecture source) | `EvidenceContract`, `hasRelevantEvidenceContract`, `instantiatesCanonicalArchitecture`, `hasAcceptanceCriterion`, `allocatedTo`, `ArchitectureElement`, `Function`, `LogicalElement`, `PhysicalElement`, `AcceptanceCriterion`, `AssuranceClaim` |

The owner decisions that gate closure (review §19 question 10): the redesign
successor vocabularies (decisions 1, 2, 8, 15), the definition-home and
role decisions (decisions 5, 6, 7), the configurator authority (decision 9)
and the canonical-architecture source (decision 10). Everything else is
bounded engineering with the review's evidence requirements.

## 6. Dependencies between waves

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
- **W7 re-enters earlier waves**: when a named decision resolves, the
  gated row completes normal earlier-wave treatment (no parallel redesign
  path).
- **closure wave requires every wave exit** plus the consumer-retirement inventory
  and the one-authority reproducibility proof.
- **O3 stays frozen throughout**: the 13 O3 identities are outside all
  waves; no O4 wave may change their semantics (review: no amendment
  required; the register binds them to `MIGRATED_IDENTITIES`).

## 7. Recommended sequence

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

**PLE parallelism:** W2, W3 and W4 have **no PLE dependency** and
can proceed in parallel with remaining PLE work. The PLE-bound rows
(W5 `selectsFeature`/`includesCommonCapability`/`appliesToMemberProduct`/
`selectsVariant`/`FeatureConfiguration` and the W7 PLE-Q/S/A closure)
must wait for the decision 9 configurator-authority decision and should not be
started independently. decision 10 (canonical architecture) gates only the
single W7 row. No O4 wave authorizes a PLEML commitment or changes the
current configuration authority.

## 8. O4 completion boundary

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

## 9. Regenerating and validating

```bash
python scripts/generate_o4_execution_register.py          # write
python scripts/generate_o4_execution_register.py --check  # verify
python scripts/check_repo.py                              # includes the register check
python -m pytest tests/test_o4_execution_register.py -q
```
