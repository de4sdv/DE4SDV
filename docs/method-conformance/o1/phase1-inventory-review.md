# O1 Phase 1 — parity-controlled semantic-authority extension: inventory review

**Status: Phase-1 review deliverable (analysis only).** No runtime semantic change,
no YAML retirement, no O2/O3/O4 activity, no privileged ingestion. Independent review
is requested before any Phase-2 implementation.

- **Branch:** `feat/o1-semantic-authority-inventory`
- **Base SHA:** `e99f46d0455376815859aa4afeb1812e3463690f` (exact `origin/main` at task start)
- **Head SHA:** the tip of the branch carrying this document (the squash-safe record is the branch itself; see the PR for the exact head)
- **Governing document:** DE4SDV Unified Semantic Engineering Plan v1.1 (wins on conflict).
  **Supporting:** DE4SDV Method Conformance Plan (A–D invariants).
- **Precedent:** merged K slice, PR #243 — `DerivesFromNeed`. Reference, not template.

Companion artifacts on this branch:

- `semantic-authority-inventory.draft.json` — the draft machine-readable inventory
  (all 93 entries classified, evidence pointers, counts, kernel accounting; explicitly
  labeled *phase-1-review-draft*, not a runtime input, not a generated artifact of a
  reviewed generator).
- This document — the analysis/review report.

---

## 0. Required report items — map

| # | Item | Where |
|---|---|---|
| 1 | Exact branch name | header |
| 2 | Exact base SHA | header |
| 3 | Current branch SHA | header (tip of branch; not fixed in this file) |
| 4 | Files inspected | §2 |
| 5 | Ontology counts | §3 |
| 6 | Proposed authority-category counts | §4.2 (current + target) |
| 7 | Already model-authoritative | §5.1 |
| 8 | Likely native KerML/SysML | §5.2 |
| 9 | Likely accepted-library grounded | §5.3 |
| 10 | Likely requiring DE4SDV application semantics | §5.4 |
| 11 | Should remain external/policy/configuration | §5.5 |
| 12 | Vocabulary-only concepts | §5.6 |
| 13 | Mixed / legacy YAML authority | §5.7 |
| 14 | Unknowns | §5.8 + §13 |
| 15 | Current runtime semantic dependencies on YAML | §6 |
| 16 | API Representation Profile concerns | §7 |
| 17 | Proposed machine-readable inventory schema | §8 |
| 18 | Proposed files to add/change | §9 |
| 19 | Proposed test matrix | §10 |
| 20 | Proposed bounded migration sequence | §11 |

Findings: §12. Explicit unknowns: §13. Evidence sufficiency: §14. Non-claims: §15.

---

## 1. Goal and boundary of this phase

O1 is **parity-controlled extension**: establish a reviewed, machine-checkable semantic
authority inventory across the existing ontology/model/runtime surface; record where each
entry's meaning comes from today, where it should come from, and what evidence exists.
This phase does **not** cut over runtime authority, does not retire authored YAML, and
does not change any runtime semantic behavior. Per the task's end condition, this report
is the deliverable; broad migration waits for independent review.

The governing decision rule applied throughout:

> Reuse native semantics when they match; define a tiny application semantic relation
> when they don't. Exact semantic fit matters more than native reuse.

---

## 2. Evidence basis — what was inspected

Read in full (repository, base SHA above):

- `approach/framework/ontology/de4sdv-basic-ontology.yaml` (645 lines; 93 entries) and
  `approach/framework/ontology/README.md`.
- Method kernel `textual-notation-of-model/packages/methods/de4sdv/` — all eight
  `.sysml` files: `de4sdv_method_context.sysml`, `de4sdv_method_process.sysml`,
  `de4sdv_method_conformance.sysml`, `de4sdv_product_line.sysml`,
  `de4sdv_operational_context.sysml`, `de4sdv_stakeholders.sysml`,
  `de4sdv_method_concerns_and_viewpoints.sysml`, `de4sdv_sysmod_adapter.sysml`
  (110 declarations total; verified by script).
- Runtime: `de4sdv/semantic/kernel_contract.py`, `kernel_binding_index.py`,
  `api_binding.py`, `validation.py`, `traversal.py`, `query.py`, `impact.py`,
  `model_authority.py`, `model_edges.py`, `projection.py`, `relationships.py`,
  `runtime.py`, `mcp_server.py`; `de4sdv/sysml_api/revisions.py`, `identity.py`.
- Gates and proof tooling: `scripts/check_model_sync.py`, `scripts/check_repo.py`,
  `scripts/prove_derivation_slice.py`; `.github/workflows/ci.yml`,
  `.github/workflows/privileged-full-model-api-ingestion.yml`.
- Governance and prior records: `AGENTS.md`; `docs/method-conformance/README.md`,
  `r0-handoff/` (inventory CSV 84 rows, stats, K-predicate selection, projection
  profile v0), `k-slice/` (final decision + superseded audit trails); PR #243 record
  incl. the fresh R6 closure run.
- Regression check executed locally at the Phase-1 head: `python3 -m pytest` on
  `tests/test_derivation_connection_traversal.py tests/test_semantic_projection_v0.py
  tests/test_projection_model_authority.py tests/test_prove_derivation_slice.py` →
  **44 passed**; `python3 scripts/check_model_sync.py` → passed.

Located by mechanical search (not each line reviewed): the remaining consumers of the
ontology contract listed in §6.

Retained K closure record (historical, for K only): privileged run `34630102233`
(success), K SHA `72926c958d2bd3b1001088fa657ec906dffd53e7`; SysML project
`ea96301d-343a-4592-bad4-5dd997ca906a`; 82,088 elements / 62 source documents;
binding validation 40 mapped / 15 native / 4 external / 0 unresolved / 0 ambiguous;
support state transitioned to `supported` only after full witness closure.

---

## 3. Ontology accounting (recounted from the contract, not from summaries)

Recounted programmatically from the YAML at the base SHA — the plan's §2 counts
(51/33) predate Lanes A–D and K and were **not** trusted:

| Quantity | Count | Notes |
|---|---|---|
| Classes | **59** | |
| Relationships | **34** | |
| Total semantic entries | **93** | every one classified in the draft inventory |
| Class kernel mappings | 59 | 40 file + 15 native + 4 external |
| — file-mapped | 40 | 39 in the governed kernel dir + 1 cross-slice (see below) |
| — native | 15 | SysML v2 constructs; no kernel declaration |
| — external | 4 | outside the SysML API baseline |
| Relationship mappings | 9 | 2 derivation-connection (K), 6 other executable strategies, 1 external |
| Vocabulary-only relationships | 25 | no `sysml_mapping` |
| Kernel declarations (governed dir) | **110** | = 39 ontology-mapped + 71 exclusions (exact pairs) |
| Cross-slice mapping | 1 | `AcceptanceCriterion` → `requirement def MiddlewareAcceptanceCriterion` in a feature slice |
| Validation rules | 10 | `DE4SDV-ONT-R001` … `R010` |
| Pilot queries | 6 | informational |

R0 reconciliation (R0 CSV, 84 rows at its own baseline → current 93):
**+9 added, −0 removed, 0 kind-changed.** Added since R0: seven Lane-A/B conformance
classes (`MethodContractObligation`, `MethodEvaluationScope`, `EvaluationScopeMembership`,
`EvaluationSourceKind`, `TestedScopeDeclaration`, `RetainedExecutionRecordReference`,
`AcceptanceAttestationReference`), `DerivesFromNeed` (K class) and
`derivedRequirementsOfNeed` (K inverse). No R0 row was silently dropped; reconciling the
R0 CSV into this inventory (supersession labels, per-row refresh) is proposed Phase-2 work.

Root `origin/main` log confirms the baseline: `e99f46d` (K, #243) on top of #248/#246/#247/#245/#242/#239.

---

## 4. Classification rules and results

### 4.1 Rules (stated so the reviewer can re-apply them)

- The category describes **where the entry's engineering meaning is established**, and
  what machinery enforces (or fails to enforce) that meaning — not merely which file
  mentions it.
- API metaclass fit alone is never semantic equivalence (UG-28 pattern). Serializer
  acceptance alone is never normative evidence.
- `mixed-authority` is used where two sources materially carry the meaning today and
  nothing enforces text parity between them (typically: kernel declaration + doc are
  model-resident, while the reviewed definition text is still authored YAML-first).
- `legacy-yaml-authoritative` is used where the meaning (e.g. domain/range, definition
  text, or an umbrella vocabulary contract) is established by authored YAML text with no
  model-resident counterpart.
- Unknowns stay explicit; where classification confidence is low the entry is marked
  `unknown` or carries a bounded open question rather than a guessed category.

### 4.2 Counts

**Current classification (93 entries):**

| Category | Count |
|---|---|
| `model-authoritative-proven` | 3 |
| `native-sysml` | 9 |
| `accepted-library-grounded` | 2 |
| `external-reference` | 3 |
| `legacy-yaml-authoritative` | 30 |
| `mixed-authority` | 45 |
| `unknown` | 1 |
| `native-kerml`, `de4sdv-application-semantic`, `policy-governance`, `representation-profile-only`, `vocabulary-only` | 0 as *current* source (they appear as targets; see §5) |

**Target classification (proposed):**

| Target | Count |
|---|---|
| `model-authoritative-proven` (incl. definition-level parity for method vocabulary) | 43 |
| `accepted-library-grounded` (ODE4HERA / PLEML-with-adoption-gate) | 12 |
| `vocabulary-only` with a model-resident definition (non-executable end state) | 15 |
| `native-sysml` | 11 |
| `de4sdv-application-semantic` | 4 |
| `unknown` (deferred with explicit blockers) | 6 |
| `external-reference` (retained explicit boundary) | 2 |

Notes on the target split: `model-authoritative-proven` as a class-level target means
"definition + declaration + parity under model authority", not that every class becomes
executable; runtime support states are recorded per entry separately. The K triple is
the only executable **relation** proven end to end so far.

---

## 5. Per-category membership (items 7–14)

### 5.1 Already model-authoritative (item 7)

The K triple — the only closure-proven model-authoritative semantics today:

1. `DerivesFromNeed` — application connection definition; typed ends
   (`need : StakeholderNeedCandidate`, `derivedRequirement : RequirementCandidate`) and
   owned Documentation carry domain/range/roles/native direction/claim strength/claim
   boundary. Standard Requirement Derivation library evaluated and **deliberately not
   adopted** (`originalImpliesDerived` overclaims); no `SemanticMetadata` workaround.
2. `derivesRequirementFromNeed` — Requirement → Need; inverse traversal over the **same
   witness**; YAML row is the O0/O1 parity oracle.
3. `derivedRequirementsOfNeed` — forward traversal over the same witness; declares no
   new model fact.

### 5.2 Likely native KerML/SysML (item 8)

Classes whose semantics are carried by native constructs today (YAML row = vocabulary
pointer): `VariationPoint`, `Variant`, `Concern`, `Viewpoint`, `View`, `Scenario`,
`ValidationScenario`, `EvidenceContract`; plus `VerificationCase`, which additionally
requires the plan §10 standard-library grounding proof (`VerificationCases::VerificationCase`
/ `verificationCases`) before stronger claims. No `native-kerml`-category entries were
identified; KerML grounding today is indirect (via the standard libraries used in tooling),
and any future KerML-native claim must carry its own grounding evidence.

### 5.3 Likely accepted-library grounded (item 9)

- `VerificationMethod` — ODE4HERA `verificationMethod` attribute populated with the
  SysML standard method-kind vocabulary (ADR 0009 amendment).
- `EvidenceStatus` — ODE4HERA `VVStatus` via the method-context adapter; no parallel
  status vocabulary.
- (Target-side) the seven product-line relationships and `FeatureConfiguration` —
  PLEML remains pinned/experimental; adoption gate (PLE-Q/S/A) unresolved.

### 5.4 Likely requiring DE4SDV application semantics (item 10)

Target-side entries where no exact native/library fit has been demonstrated and the
smallest sufficient representation is likely a DE4SDV application semantic definition
(or a reviewed contract over an existing construct):

- `derivesNeedFromConcern` — Need → Concern provenance; same family as K; needs a model
  inventory of concern usages before a representation can be selected.
- `specifiesFunction`, `hasRelevantArchitecture`, `hasRelevantEvidenceContract` —
  relevance-only semantics over a generic `Dependency` with typed endpoint filters and a
  member-product-lineage exclusion; the filters/exclusion are application semantics
  currently living in YAML config + code.
- The K triple itself is the proven exemplar (`de4sdv-application-semantic` by nature,
  classified `model-authoritative-proven` by status).

### 5.5 Should remain external / policy / configuration (item 11)

- `hasEvidence` (VerificationCase → EvidenceArtifact) — explicit external boundary
  (`external-data-required`); runtime returns nothing by design. Do not change the
  boundary without the T/E design; introduce model-resident reference semantics only
  through that reviewed design.
- `EvidenceArtifact` — external evidence registers/retained items (T/E lane).
- `FeatureConfiguration` — Bill-of-Features YAML remains operational authority until an
  authorized PLE cutover; explicitly retained as external now.
- Governance content inside the YAML (`kernel_sync` contract + 71 exclusions, the 10
  validation rules) — policy-governance; R003 has a mechanical enforcement path (sync
  point 6), the others are review-enforced and stay policy until O-stage migration.

### 5.6 Vocabulary-only concepts (item 12)

25 relationships currently have no executable mapping; 15 of them are proposed to remain
**vocabulary-only** at the target (definition moves into the model; no runtime
execution claim): increment/concern families (`addressesConcern`, `hasStakeholder`,
`selectedViewpoint`, `producesView`, `recordsAssumption`, `recordsGap`), `constrainedBy`,
`hasAcceptanceCriterion`, `supportedByEvidence`, `capturedInBaseline`, and the five
umbrella classes in 5.7. Keeping these vocabulary-only may be the correct end state; what
O4 forbids is their definitions surviving as independently authored YAML.

### 5.7 Mixed / legacy YAML-authority entries (item 13)

- **Mixed (45):** all 39 file-mapped method-vocabulary classes (declaration + doc
  model-resident; reviewed definition text still YAML-first; no text-parity machinery) —
  plus the six runtime-mapped relationships (`realizedBy`, `specifiesFunction`,
  `hasRelevantArchitecture`, `hasRelevantEvidenceContract`, `verifiedBy`, `hasSubject`),
  where the model carries the facts but the mapping configuration (strategy, filters,
  strength, exclusion rule) is YAML-authored.
- **Legacy YAML-authoritative (30):** the 25 vocabulary-only relationships and five
  umbrella classes (`ArchitectureElement`, `Function`, `LogicalElement`,
  `PhysicalElement`, `Interface`) that have no model-resident definition home yet.
- The draft inventory records, per entry, a **doc spot-check** heuristic (declaration
  block located; doc text compared against the YAML definition). Result: 7 entries
  `doc-contains-definition`, most others `doc-variant` (mostly phrasing-length
  differences — e.g. YAML definitions that fold in examples), `doc-absent` for
  `Stakeholder` and `RetainedExecutionRecordReference`, `block-not-located` for the
  `;`-terminated cross-slice declaration. This is **survey data, not parity evidence**;
  the parity machinery is proposed in Phase 2. Spot-checked variants exist (e.g.
  `SystemLayer` lost “and their environments” in the model doc), so the current
  YAML/model text relationship must not be assumed to be exact.

### 5.8 Unknowns (item 14)

Six target-`unknown` entries, each with a bounded blocker (details in the draft JSON and
§13): `AssuranceClaim`, `allocatedTo`, `deployedTo`, `instantiatesCanonicalArchitecture`,
`validatedBy`, `validatesFitnessForUse`.

---

## 6. Current runtime semantic dependencies on the authored YAML (item 15)

The YAML is loaded at runtime by `de4sdv/semantic/kernel_contract.py`; the revision
binding additionally pins the YAML **path + SHA-256** (`OntologyIdentity`) and refuses a
runtime whose contract digest differs (`RevisionBinding.require_ontology`). What the
runtime actually depends on today:

| Consumer | YAML fields consumed | Role |
|---|---|---|
| `kernel_contract.KernelContract` | classes (kernel mappings), relationships (`sysml_mapping`), `kernel_sync`, identity digest | The loader; runtime authority for mapping configuration |
| `traversal.SemanticTraversal` | `sysml_mapping` strategy + configuration (relationship types, filters, properties, direction, lineage, roles) | Executes only declared strategies; raises on unknown strategy; no name-based fallback |
| `query.SemanticQueryService` | relationship list with `sysml_mapping` (`_mapped_predicates`) | `semantic_neighbors` / `trace` default predicate set (9) |
| `impact.ImpactService` | mappings for `realizedBy`, `specifiesFunction`, `hasRelevantArchitecture`, `hasSubject`, `hasRelevantEvidenceContract`, `verifiedBy` | Requirement impact composition |
| `api_binding.OntologyApiBinder` | class kernel mappings | Expected API type for identity pinning (UUIDs come from the binding index, not YAML) |
| `kernel_binding_index` / `validation` | `declaration_identity()` kind→API-type normalization; class list | Identity validation at ingestion; fail-closed classification |
| `projection` (K) | K predicate rows + `Need`/`Requirement` declarations | **Parity oracle only** (drift fails generation) |
| `scripts/check_model_sync.py` | `kernel_sync` (SP5), R003 groundings (SP6) | CI gate: bidirectional contract + derivation coverage |
| Ingestion/validators | contract identity; class mappings | `import_sysml_api_baseline.py`, `validate_full_model_semantic_queries.py`, `validate_product_line_scope_api.py`, `validate_semantic_mcp.py`, `seed_aebs_api_fixture.py`, `query_model_impact.py` |
| Viewer / deployment | contract load path | `tools/sysml_html_viewer/ask_model_semantic.py`, `deployment/ask_viewer/entrypoint.py` |
| Tests | many | contract-drift and behavior pinning |

Kernel identity at runtime never comes from YAML names: it comes from the
ingestion-validated `kernel_bindings` UUIDs (ADR 0011) — YAML supplies the *expectations*
(type/declaration), the binding supplies the identity. No name fallback exists; missing
bindings fail closed (`IdentityNotFoundError`).

---

## 7. API Representation Profile concerns (item 16)

- Profile v0 covers exactly **one** predicate (K). The other eight mappings' mechanics
  live implicitly in `traversal.py` + YAML config; there is no per-entry profile yet.
- The `sysml_mapping` block currently **mixes semantics and mechanics** (e.g.
  `semantic_strength` and the member-product lineage exclusion next to property paths and
  serializer shapes). O1 must split: meaning/strength/exclusions → model/parity (projection);
  property paths/witness shapes/quirks → Representation Profile.
- Two implemented strategies are **not associated with any ontology mapping**:
  `verification` and `property-reference`. The inventory records them as unassociated
  runtime capability; either associate them with entries or flag them for removal review —
  silently leaving them unaccounted for fails completeness (see §10, test matrix).
- K's completeness checks (C1 closure) are predicate-specific; generalization must keep
  per-entry "completeness_check" and fail-closed semantics.
- The external strategy is honest (returns nothing; strength `external-data-required`),
  but the profile must state the boundary explicitly for consumers.

---

## 8. Proposed machine-readable inventory schema (item 17)

Schema id proposed: `de4sdv.semantic-authority-inventory/v1` (runtime-inert; review
artifact). One record per semantic entry (classes, relationships, governance rows,
kernel exclusions), with the field groups required by the task:

- **identity** — canonical identity; kind; current YAML path/location;
  model grounding (file+declaration | native | external | strategy).
- **current semantic contract** — domain, range, native direction (where known),
  canonical query direction, inverse identity, semantic strength, exclusions,
  claim boundary, applicability scope.
- **model authority** — declaration, source model/library, declaration identity,
  DE4SDV application specialization/role, and *residency flags* (meaning /
  domain+range+roles / claim boundary model-resident? yes|no|partial) plus
  model-authority status.
- **standard/native grounding** — **separate fields**: applicable API metaclass;
  native KerML grounding; native SysML grounding; standard/domain-library grounding;
  accepted upstream library; pinned-but-not-adopted library; incompatibility/adoption
  rationale. (Never collapsed into one field.)
- **API representation** — validated API metaclass; serialized witness form; authored
  vs implied provenance requirements; ownership/member traversal; reference resolution;
  known serializer/importer variants; completeness requirements; revision/provenance
  requirements.
- **runtime/query support** — current consumer; mapping strategy; query direction;
  support state; fail-closed behavior; known gap/error modes; name fallback (=none);
  whether runtime still depends on YAML semantic fields.
- **classification** — authority category; migration disposition; confidence;
  unresolved questions; required evidence; proposed later O-stage.

Draft-vs-final: the committed `semantic-authority-inventory.draft.json` demonstrates the
shape for the phase-1 fields (classification, grounding, counts, accounting). The full
rich record population is proposed to be produced **deterministically** in Phase 2 by a
reviewed generator that reuses the existing loader (`KernelContract`), the kernel
inventory, and the runtime strategy tables — never by hand and never by re-parsing the
model with a second parser.

---

## 9. Proposed files to add/change (item 18)

Add (Phase 2), reusing existing infrastructure — no parallel authority:

1. `de4sdv/semantic/authority_inventory.py` — schema constants + loader + validator;
   consumes `KernelContract` and static strategy/consumer tables; deterministic ordering.
2. `scripts/generate_semantic_authority_inventory.py` — generator entry point; emits the
   inventory JSON and the review table; refuses to emit on missing coverage.
3. `docs/method-conformance/o1/semantic-authority-inventory.json` — the committed
   generated inventory (supersedes the phase-1 draft; R0 CSV gets a supersession pointer).
4. `docs/method-conformance/o1/authority-inventory.md` — generated human review table
   (asserted row-for-row by tests; no hand-maintained duplicate).
5. `tests/test_semantic_authority_inventory.py` — coverage/classification/determinism
   tests (§10).
6. Extend `de4sdv/semantic/projection.py` — inventory-driven generation for proven rows
   (remove the single-predicate hard-coding while keeping K behavior byte-equal for the
   K row; parity oracle retained; inverse-row parity added).
7. `approach/framework/ontology/README.md` — fix the stale query-coverage text (finding F1).

Change (small, reviewable): wire the inventory generator's coverage check into the
existing gates (`check_repo.py` step or CI) only after review — not in Phase 1.

Explicitly NOT proposed: no new graph, no second evaluator, no second ontology, no
generator-driven YAML authority, no runtime semantic change in O1 bytes.

---

## 10. Proposed test matrix (item 19)

New tests (deterministic, offline):

| Test | Asserts |
|---|---|
| coverage/classes | every ontology class has exactly one inventory record (recounted from YAML; fails on additions/removals) |
| coverage/relationships | every relationship accounted; mapping vs vocabulary-only partition exact |
| coverage/mappings | every `sysml_mapping`, every class kernel mapping, every exclusion (exact pairs), and the cross-slice mapping are accounted |
| coverage/runtime | every traversal strategy implementation is associated with an inventory entry or explicitly flagged (verification / property-reference) |
| determinism | two generations are byte-identical; ordering rules fixed (YAML order + explicit sort) |
| K precedent | K triple rows remain consistent with merged closure state; existing K suites stay green (44 tests) |
| class classification | category vocabulary is a closed set; `unknown` requires a bounded question |
| relationship classification | same, plus direction/strength fields required for mapped relationships |
| metaclass vs grounding | schema keeps API metaclass and library grounding separate; a grounding claim without evidence fails |
| adoption evidence | `accepted-library-grounded` rows require upstream identity (ODE4HERA/ADR 0009; PLEML pin) or fail |
| parity roles | YAML-only vs parity-oracle distinction is explicit per row; proven rows get drift checks (K parity tests generalized) |
| external boundary | `hasEvidence` stays external; traversal returns nothing; no row silently reclassifies it |
| unknown handling | unknown rows fail closed for any "supported" projection claim |
| duplicate refusal | duplicate canonical identity, or one identity with incompatible semantics, fails generation |
| binding identity | inventory binds base SHA + contract identity; rebind required when they move |
| no-runtime-change | Phase-1 claim is enforced by retaining all A/B/C/D/K suites plus an explicit assertion that no runtime module changed on the branch |

Retention: all existing A–D and K suites remain; no existing test may be weakened.

---

## 11. Proposed bounded migration sequence for later O1 work (item 20)

Ordered by semantic importance, existing grounding, runtime consumption, provability with
the current API, and overclaim risk. **Nothing below is executed in Phase 1.**

### Wave 0 — foundation (no semantic change to existing entries)

- **0a. Inventory schema + generator + coverage validator + committed inventory v1**
  (replaces the phase-1 draft; deterministic; R0 CSV superseded with pointer).
- **0b. Generalize projection/profile generation** from the single-predicate K constants
  to inventory-driven generation for proven rows — same-witness inverse, parity oracle,
  and fail-closed behavior preserved; K row output unchanged. Includes the inverse-row
  parity gap (finding F5).
- **0c. Stale-text sweep** (finding F1 and any other K-era drift readers).

### Wave 1 — high-confidence model-authority / parity wins

1. **`verifiedBy` (Requirement → VerificationCase).**
   *Exact engineering meaning:* “verification case VC is the verification objective for
   requirement R” — the case *verifies* R; coverage is not execution success.
   *Fit:* native `RequirementVerificationMembership` already proven by the runtime
   strategy; the missing piece is the plan §10 standard-library grounding proof
   (`VerificationCases::VerificationCase` / `verificationCases`) and moving
   roles/strength under parity discipline. Native reuse — no new relation.
2. **`hasSubject` (Requirement → MemberProduct).**
   *Exact engineering meaning:* “requirement R is stated about member product MP” (the
   actual evaluated item — subject semantics, never widened).
   *Fit:* native `SubjectMembership` exactly; the member-product restriction is a DE4SDV
   application constraint → keep it as a reviewed model-resident contract note, not a
   new predicate. No widening to verification subjects (plan §10).
3. **Method-conformance class batch (7 Lane-A/B classes).**
   *Meaning:* typed method-contract vocabulary (obligations, scopes, memberships,
   source kinds, tested-scope declarations, retained-record and attestation references).
   *Fit:* already model-resident with attribute-level docs (richer than YAML); this is a
   parity/definition move with low ambiguity, and it unblocks conformance-surface
   accounting in the inventory.
4. **`derivesNeedFromConcern` (Need → Concern).**
   *Exact engineering meaning:* “the stakeholder need N originates from stakeholder
   concern C” — provenance only; no satisfaction/implication/allocation/verification claim.
   *Fit:* no exact native requirement-to-concern derivation construct identified; the K
   pattern (minimal application connection definition with typed ends) applies **only if**
   the model carries concern usages to ground its ends. Open questions: does the AEBS/method
   model contain concern usages suitable as connection ends, and is the origin a concern
   or a problem statement? Blocked until the concern inventory is executed; if blocked,
   keep vocabulary-only with the blocker recorded.

### Wave 2 — decision-dependent (still O1-bounded, but requires reviewed semantic decisions)

5. **Relevance family — `specifiesFunction`, `hasRelevantArchitecture`,
   `hasRelevantEvidenceContract`.** *Meaning:* relevance-only trace over generic
   `Dependency` with typed endpoint filters (and the MemberProduct-lineage exclusion).
   *Fit:* a generic Dependency natively establishes only its generic meaning; the
   stronger “relevance” contract is DE4SDV application semantics. Decide: keep relevance
   with a reviewed model-resident claim boundary + UG-05 negative tests, or mint a
   minimal application relation. No silent strength change (UG-04).
6. **`realizedBy` (Requirement → ArchitectureElement).** *Meaning:* the requirement is
   realized by / allocated to an architecture element (allocation strength).
   *Fit:* native allocation facts exist; the reviewed question is whether “realizedBy”
   claims exactly native allocation semantics or more (plan §10 forbids reuse for
   LogicalElement → SoftwareElement without versioned migration). Signature frozen;
   parameterize nothing until the decision.
7. **`hasEvidence` external boundary.** *Meaning:* evidence artifact reference — external
   by design. *Fit:* retain the boundary; design explicit model-resident
   execution/reference semantics only through the T/E design (plan §10/§12). No O1 change
   beyond inventory status.

### Deferred past O1 core (recorded, not scheduled here)

- PLE family (7 relationships + `FeatureConfiguration`): PLE-led (PLE-Q/S/A) — O does not
  own their semantics; O1 records them with explicit dependency.
- `allocatedTo`, `deployedTo`, `instantiatesCanonicalArchitecture`: T-lane; blockers from
  plan §10 recorded in the draft.
- `validatedBy` / `validatesFitnessForUse`: needs a native validation-construct
  inspection before any representation decision.
- `AssuranceClaim` family (`supportedByEvidence`): unknown grounding; defer with question.
- Evidence family (`capturedInBaseline`, `hasEvidenceStatus`, `usesVerificationMethod`):
  migrate with T/E and ADR 0009 decisions respectively.

**K-specific vs generalizable (explicit):** the K mechanisms that generalize are the
model-authority extraction (typed-end reading, provenance-separated lineage, fail-closed
witness closure), the parity-oracle pattern, the mechanics-only profile, and the
inventory-driven projection idea. K-specific by intent: the single predicate's named
roles/constants and the derivation-connection strategy's role semantics. The K
representation itself is not rewritten.

---

## 12. Findings (from this inspection — report-only in Phase 1)

- **F1 — stale ontology README after K.** `approach/framework/ontology/README.md` still
  says “Derivation has no API traversal strategy yet” and its query-coverage table and
  strategy list omit both derivation predicates and the `derivation-connection` strategy.
  Proposed: fix in Wave 0c with the K parity record as evidence.
- **F2 — YAML mixes semantics and mechanics.** `sysml_mapping` blocks carry
  `semantic_strength` and exclusion semantics next to serializer mechanics; O1 must split
  per §8.1 (projection/profile boundary). Affects all eight non-K mappings.
- **F3 — R0 inventory supersession.** The R0 CSV (84 rows) no longer matches the 93-entry
  ontology; it remains the historical R0 record. Proposed: supersede with a pointer once
  inventory v1 is generated (Wave 0a).
- **F4 — unassociated runtime strategies.** `verification` and `property-reference` are
  implemented in `traversal.py` but no ontology mapping uses them; completeness gate #4
  requires association or an explicit flag. Recorded now in the draft; decide in Wave 0a.
- **F5 — inverse-row parity gap (K).** Projection v0 parity-checks only
  `derivesRequirementFromNeed`; the `derivedRequirementsOfNeed` YAML row and the
  `inverse_navigation_identity` value are not parity-checked. Bounded generalization
  proposed in Wave 0b (no K behavior change).
- **F6 — closure evidence not machine-bound.** `witness_closure_verified` is a
  caller-supplied boolean; the R6 closure lives in run records/PR text, not in a
  repo-checkable artifact reference. The inventory should carry a machine-checkable
  evidence reference for `supported` states — flagged for design in Wave 0a.
- **F7 — cross-slice kernel mapping.** `AcceptanceCriterion` maps to a declaration inside
  a feature slice (outside the governed kernel dir). Decide in a later stage: promote to
  kernel or retain as a governed cross-slice mapping with an explicit rule.
- **F8 — model-doc variant drift.** Spot-check found declaration docs that are not
  verbatim mirrors of the YAML definitions (e.g. `SystemLayer`), so text parity cannot be
  assumed; parity machinery must compare normalized text and surface variants, not assume
  equality (feeds Wave 0a/0b).

---

## 13. Explicit unknowns (summary; per-entry detail in the draft)

1. `AssuranceClaim` — native construct, accepted library, or application definition?
2. `validatedBy` / `validatesFitnessForUse` — which native/library validation relation
   (if any) fits fitness-for-use validation?
3. `allocatedTo` — native allocation ends/exact types; collision risk with the frozen
   `realizedBy` signature.
4. `deployedTo` — signature migration vs distinct reviewed predicate.
5. `instantiatesCanonicalArchitecture` — canonical-usage selector design (no name filter).
6. Concern-link inventory for `derivesNeedFromConcern` (Wave 1 candidate gating).
7. Umbrella vocabulary home (`ArchitectureElement`, `Function`, `LogicalElement`,
   `PhysicalElement`, `Interface`) — where does the model-resident definition live?
8. Machine-checkable closure-evidence binding for `supported` states (F6).

---

## 14. Evidence sufficiency (stop-condition check)

Every Phase-1 conclusion is established from repository evidence at the base SHA plus
retained K records; no new privileged ingestion is required or proposed for Phase 1.
Nothing in this report depends on a fact that retained evidence cannot establish. If a
later O1 step cannot be established from repository/model evidence, it must be stopped
and justified before any privileged dispatch (Unified Plan stop conditions).

---

## 15. Non-claims

- Not an authority cutover; YAML remains the current runtime authority for unmigrated scope.
- Not O2/O3/O4 progress; no retirement; no generated-YAML authority.
- Not a claim that all vocabulary is supported; 25 relationships remain vocabulary-only,
  and 6 targets stay `unknown`.
- Not a redesign of K; the K representation and closure record are preserved as-is.
- Not a privileged-evidence claim; the K R6 record is historical exact-revision evidence
  for K only.
- Not acceptance of any migration listed in §11 — review first.

---

## Appendix A — classes (59), full classification

| id | cur | tgt | disp | conf | stage | note |
|---|---|---|---|---|---|---|
| EngineeringIncrement | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity. |
| FeatureIncrement | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity. |
| NeedsRequirementsIncrement | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity. |
| IncrementEngineeringQuestion | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity. |
| IncrementLifecycleDecision | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity. |
| IncrementTraceabilityShell | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity. |
| MethodPhase | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Enum literals carry per-phase docs in the model; YAML summary; conformance consumers reference phases. |
| SignalMappingDisposition | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Enum literal docs resident. |
| LogicalToSoftwareSignalMappingRecord | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Attribute-level docs resident. |
| SystemToSoftwareSignalMappingCandidate | mixed-authority | model-authoritative-proven | move-meaning-into-model | medium | O1/O2 | Allocation def with non-claiming doc; allocation realization semantics unresolved (plan §10 style). |
| IncrementSize | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| SystemLayer | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity. |
| ProductLine | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| MemberProduct | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration ProductLineMemberProduct; specialization lineage consumed by hasRelevantArchitecture exclus… |
| Feature | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | ISO 26580 rule carried by specialization structure + R001 review; candidate-until-variability semantics. |
| ProductLineCharacteristic | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| CommonCapability | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| DeferredProductLineScope | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| VariationPoint | native-sysml | native-sysml | keep-as-is | high | O2+ (parity pointer) | Native SysML variation definition/usage; do not model as a part taxonomy. YAML row is vocabulary pointing at t… |
| Variant | native-sysml | native-sysml | keep-as-is | high | O2+ (parity pointer) | Native variant usage owned by a variation point. YAML row is vocabulary pointing at the construct; definition … |
| FeatureConfiguration | external-reference | accepted-library-grounded | retain-explicit-external-boundary | high | PLE | Bill-of-Features YAML under model-based-product-line-engineering/; operational authority until PLE-authorized … |
| Stakeholder | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| Concern | native-sysml | native-sysml | keep-as-is | high | O2+ (parity pointer) | Native concern def/usage; SAF viewpoint selections in kernel. YAML row is vocabulary pointing at the construct… |
| Need | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | StakeholderNeedCandidate requirement def; ODE4HERA attribute set via ADR 0009; consumed by K lineage and R003. |
| Requirement | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | RequirementCandidate requirement def; SYSMOD seam + ODE4HERA attrs; consumed by impact/K. |
| ProblemStatement | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | R003 exclusion grounding (traced into, not out of). |
| ArchitectureDecisionRecord | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | R003 origin grounding. |
| RegulatoryConstraint | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | R003 origin grounding; no compliance claim boundary must stay model-carried. |
| ArchitectureElement | legacy-yaml-authoritative | vocabulary-only | defer | low | O2+ (design decision) | Umbrella over native part/port/behavior definitions used in architecture slices. No model-resident definition … |
| Function | legacy-yaml-authoritative | vocabulary-only | defer | low | O2+ (design decision) | Umbrella over native action/state/behavior definitions in functional-architecture slices. No model-resident de… |
| LogicalElement | legacy-yaml-authoritative | vocabulary-only | defer | low | O2+ (design decision) | Umbrella over native part defs in logical-architecture slices. No model-resident definition home exists yet; r… |
| PhysicalElement | legacy-yaml-authoritative | vocabulary-only | defer | low | O2+ (design decision) | Umbrella over native part defs in physical/software realization slices. No model-resident definition home exis… |
| Interface | legacy-yaml-authoritative | vocabulary-only | defer | low | O2+ (design decision) | Umbrella over native port defs and connection elements. No model-resident definition home exists yet; reviewed… |
| Scenario | native-sysml | native-sysml | keep-as-is | high | O2+ (parity pointer) | Operational-context parts plus scenario-identity enums (slice-local). YAML row is vocabulary pointing at the c… |
| VerificationCase | native-sysml | native-sysml | prove-existing-model-authority | medium | O1/O2 | Native verification def; plan §10 requires standard Systems Model Library grounding (VerificationCases::Verifi… |
| ValidationScenario | native-sysml | native-sysml | keep-as-is | high | O2+ (parity pointer) | Scenario parts with bounded validation outcomes (slice-local). YAML row is vocabulary pointing at the construc… |
| VerificationMethod | accepted-library-grounded | accepted-library-grounded | keep-as-is | high | O2+ (parity) | ODE4HERA requirements-management library verificationMethod attribute populated with standard VerificationMeth… |
| AcceptanceCriterion | mixed-authority | model-authoritative-proven | move-meaning-into-model | medium | O1/O2 | Kernel mapping points at MiddlewareAcceptanceCriterion in a feature slice (outside governed dir) — cross-slice… |
| EvidenceArtifact | external-reference | external-reference | retain-explicit-external-boundary | high | T/E | Evidence registers and retained-evidence items; plan §10/§12 evidence-reference modeling pending. |
| EvidenceContract | native-sysml | native-sysml | keep-as-is | medium | O2+ (parity pointer) | Requirement usages defining bounded observations; planning vocabulary, not proof. YAML row is vocabulary point… |
| EvidenceStatus | accepted-library-grounded | accepted-library-grounded | keep-as-is | high | O2+ (parity) | ODE4HERA VVStatus via the method-context adapter; no parallel status vocabulary. |
| Assumption | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| Gap | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | IncrementGap; "must not be hidden" boundary. |
| MissingRealizationRecord | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| BlockedRealizationBranchRecord | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| AssuranceClaim | unknown | unknown | defer | low | O2+ | YAML claims "Claim usages framed by the argumentation-assurance viewpoint"; no standard argumentation construc… |
| Viewpoint | native-sysml | native-sysml | keep-as-is | high | O2+ (parity pointer) | Native viewpoint def; selections in DE4SDV_MethodViewpoints + SAF_Viewpoints. YAML row is vocabulary pointing … |
| View | native-sysml | native-sysml | keep-as-is | high | O2+ (parity pointer) | Native view. YAML row is vocabulary pointing at the construct; definition parity to the native usage review. |
| TraceLink | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Kernel declaration + doc resident; YAML carries the reviewed definition text; add definition parity; no execut… |
| RequiredTraceChain | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1/O2 | Chain vocabulary used in review; no executable chain validation. |
| Baseline | mixed-authority | model-authoritative-proven | move-meaning-into-model | medium | O1/O2 | DE4SDVEvidenceBaseline; "review/evidence baseline without implying accepted evidence" boundary. |
| MethodContractObligation | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1 (batch) | Model carries attribute-level schema docs (richer than YAML); schema intent model-resident. |
| EvaluationSourceKind | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1 (batch) | Enum literal docs model-resident. |
| MethodEvaluationScope | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1 (batch) | Scope binding semantics model-resident; R0 baseline §6 lineage. |
| EvaluationScopeMembership | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1 (batch) | contributes flag semantics model-resident. |
| TestedScopeDeclaration | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1 (batch) | Conservative scope-equality fields model-resident. |
| RetainedExecutionRecordReference | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1 (batch) | External bytes + digest reference contract model-resident. |
| AcceptanceAttestationReference | mixed-authority | model-authoritative-proven | move-meaning-into-model | high | O1 (batch) | Policy reference boundary model-resident; policy status external. |
| DerivesFromNeed | model-authoritative-proven | model-authoritative-proven | keep-as-is | high | K (merged) | DE4SDV application connection definition; typed ends + owned Documentation carry domain/range/roles/strength/b… |

## Appendix B — relationships (34), full classification

| id | cur | tgt | disp | conf | stage | note |
|---|---|---|---|---|---|---|
| addressesConcern | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | high | O2+ | domain/range authored in YAML; no executable mapping. |
| hasStakeholder | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | high | O2+ | domain/range authored in YAML; no executable mapping. |
| selectedViewpoint | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | high | O2+ | domain/range authored in YAML; no executable mapping. |
| producesView | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | high | O2+ | domain/range authored in YAML; no executable mapping. |
| derivesNeedFromConcern | legacy-yaml-authoritative | de4sdv-application-semantic | introduce-minimal-de4sdv-relation | medium | O1 wave 1 candidate | Same family as K; Need -> Concern provenance (concern is the origin). Exact meaning: "the stakeholder need N o… |
| derivesRequirementFromNeed | model-authoritative-proven | model-authoritative-proven | keep-as-is | high | K (merged) | Requirement -> Need, inverse traversal over the same DerivesFromNeed witness; YAML row is the O0/O1 parity ora… |
| derivedRequirementsOfNeed | model-authoritative-proven | model-authoritative-proven | keep-as-is | high | K (merged) | Forward traversal over the same witness; declared no new model fact. |
| constrainedBy | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | medium | O2+ | Regulatory constraint provenance; R003 family; definition moves into model; no executable mapping planned. |
| specifiesFeature | legacy-yaml-authoritative | accepted-library-grounded | defer | medium | PLE (PLE-S/A) | Product-line relationship; target PLEML model-native authority for the admitted scope (unadopted; upstream gat… |
| specifiesCommonCapability | legacy-yaml-authoritative | accepted-library-grounded | defer | medium | PLE (PLE-S/A) | Product-line relationship; target PLEML model-native authority for the admitted scope (unadopted; upstream gat… |
| realizedBy | mixed-authority | model-authoritative-proven | prove-existing-model-authority | medium | O1 wave 2 | Allocation usage facts model-resident; strategy/strength config YAML. Signature frozen (plan §10); semantic-fi… |
| specifiesFunction | mixed-authority | de4sdv-application-semantic | prove-existing-model-authority | medium | O1 wave 2 | Relevance only over generic Dependency with typed endpoint filters; reviewed significance decision needed; end… |
| hasRelevantArchitecture | mixed-authority | de4sdv-application-semantic | prove-existing-model-authority | medium | O1 wave 2 | Incoming dependency relevance with MemberProduct-lineage source exclusion (exclusion rule is application seman… |
| allocatedTo | legacy-yaml-authoritative | unknown | defer | low | T | Function -> LogicalElement; native allocation proof required; carries collision risk with the frozen realizedB… |
| deployedTo | legacy-yaml-authoritative | unknown | defer | low | T | LogicalElement -> PhysicalElement; realization vs software-deployment distinction unresolved; migrate signatur… |
| verifiedBy | mixed-authority | native-sysml | prove-existing-model-authority | medium | O1 wave 1 | Native RequirementVerificationMembership reverse traversal; verification-objective semantics; coverage is not … |
| usesVerificationMethod | legacy-yaml-authoritative | accepted-library-grounded | adopt-accepted-library-relation | medium | O2+ | Method carried natively by VerificationMethod metadata with standard method-kind vocabulary (ADR 0009 amendmen… |
| hasAcceptanceCriterion | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | medium | O2+ | Verification-case objective/criterion vocabulary; consider native verification objective representation during… |
| validatedBy | legacy-yaml-authoritative | unknown | defer | low | O2+ | Need -> ValidationScenario; native validation construct not yet inspected. |
| validatesFitnessForUse | legacy-yaml-authoritative | unknown | defer | low | O2+ | ValidationScenario -> Need; inverse family of validatedBy. |
| hasEvidence | external-reference | external-reference | retain-explicit-external-boundary | high | T/E | Explicit external boundary (external-data-required); traversal returns nothing by design; introduce model-resi… |
| hasEvidenceStatus | legacy-yaml-authoritative | accepted-library-grounded | adopt-accepted-library-relation | medium | O2+ | Connects external evidence artifacts to the ODE4HERA VVStatus vocabulary; status is already carried in model s… |
| recordsAssumption | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | high | O2+ | domain/range authored in YAML; no executable mapping. |
| recordsGap | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | high | O2+ | domain/range authored in YAML; no executable mapping. |
| supportedByEvidence | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | medium | O2+ | Assurance-claim family; contract migrates with the claim-design decision (see AssuranceClaim). |
| appliesToMemberProduct | legacy-yaml-authoritative | accepted-library-grounded | defer | medium | PLE (PLE-S/A) | Product-line relationship; target PLEML model-native authority for the admitted scope (unadopted; upstream gat… |
| hasSubject | mixed-authority | native-sysml | prove-existing-model-authority | medium | O1 wave 1 | Native SubjectMembership; do NOT widen beyond declared member-product subjects; subject must be the actual ite… |
| hasRelevantEvidenceContract | mixed-authority | de4sdv-application-semantic | prove-existing-model-authority | medium | O1 wave 2 | Incoming dependency relevance restricted to requirement-usage sources; disjointness with specifiesFunction mus… |
| selectsFeature | legacy-yaml-authoritative | accepted-library-grounded | defer | medium | PLE (PLE-S/A) | Product-line relationship; target PLEML model-native authority for the admitted scope (unadopted; upstream gat… |
| instantiatesCanonicalArchitecture | legacy-yaml-authoritative | unknown | defer | low | T | Vocabulary only; requires an explicit canonical-usage selector (no name-based filter). Product-level canonical… |
| includesCommonCapability | legacy-yaml-authoritative | accepted-library-grounded | defer | medium | PLE (PLE-S/A) | Product-line relationship; target PLEML model-native authority for the admitted scope (unadopted; upstream gat… |
| variesAt | legacy-yaml-authoritative | accepted-library-grounded | defer | medium | PLE (PLE-S/A) | Product-line relationship; target PLEML model-native authority for the admitted scope (unadopted; upstream gat… |
| selectsVariant | legacy-yaml-authoritative | accepted-library-grounded | defer | medium | PLE (PLE-S/A) | Product-line relationship; target PLEML model-native authority for the admitted scope (unadopted; upstream gat… |
| capturedInBaseline | legacy-yaml-authoritative | vocabulary-only | move-meaning-into-model | medium | O2+ | Evidence-to-baseline provenance; T/E evidence design dependent. |
