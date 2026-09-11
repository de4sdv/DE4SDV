# O1 Phase 1 — parity-controlled semantic-authority extension: inventory review

**Edition 2 — review-correction pass 1** (per the independent second review of PR #249).
This edition replaces the initial Phase-1 classification scheme on this branch: semantic
authority and evidence maturity are now separate dimensions, the native classifications
were re-reviewed against exact semantic fit, library adoption status is explicit, the
O1/O2 boundary is corrected, fuzzy similarity is removed as a parity mechanism, and the
inventory separates observed facts from reviewed decisions. **No runtime or model change;
no new support promotion; no privileged ingestion.**

**Status: awaiting second review.** No migration, no runtime change, no O2/O3/O4.

- **Branch:** `feat/o1-semantic-authority-inventory`
- **Base SHA:** `e99f46d0455376815859aa4afeb1812e3463690f` (exact `origin/main` at task start)
- **Head SHA:** the tip of the branch carrying this document (see the PR for the exact head)
- **Governing document:** DE4SDV Unified Semantic Engineering Plan v1.1 (wins on conflict).
  **Supporting:** DE4SDV Method Conformance Plan (A–D invariants).
- **Precedent:** merged K slice, PR #243 — `DerivesFromNeed`. Reference, not template.

Companion artifacts on this branch:

- `semantic-authority-inventory.draft.json` — the draft machine-readable inventory
  (revision 2; all 93 entries; observed/reviewed layers; closure-evidence record;
  explicitly labeled *phase-1-review-draft*, not a runtime input, not a generated
  artifact of a reviewed generator).
- This document.

---

## 0. Required report items — map (revised after correction pass 1)

| # | Item | Where |
|---|---|---|
| 1 | Exact branch name | header |
| 2 | Exact base SHA | header |
| 3 | Current branch SHA | header (tip of branch) |
| 4 | Files inspected | §3 |
| 5 | Ontology counts | §4 |
| 6 | Revised category counts | §5.3–§5.5 |
| 7 | Model-authoritative entries | §6.1 |
| 8 | Native KerML/SysML entries | §6.2 (with the exact-fit re-review) |
| 9 | Accepted-library-grounded entries | §6.3 |
| 10 | DE4SDV application semantic entries | §6.4 |
| 11 | External/policy/configuration entries | §6.5 |
| 12 | Vocabulary concepts | §6.6 |
| 13 | Legacy/mixed YAML entries | §6.7 |
| 14 | Unknowns | §6.8 + §14 |
| 15 | Runtime semantic dependencies on YAML | §7 |
| 16 | API Representation Profile concerns | §8 |
| 17 | Machine-readable inventory schema | §9 |
| 18 | Proposed files to add/change | §10 |
| 19 | Proposed test matrix | §11 |
| 20 | Bounded migration sequence (O1/O2 boundary corrected) | §12 |

Correction-pass record: §2. Findings: §13. Evidence sufficiency: §15. Non-claims: §16.

---

## 1. Goal and boundary of this phase

O1 is **parity-controlled extension**: establish a reviewed, machine-checkable semantic
authority inventory across the existing ontology/model/runtime surface; record where each
entry's meaning comes from today, where it should come from, and the evidence that
supports each claim. This phase does **not** cut over runtime authority, does not retire
authored YAML, and does not change any runtime semantic behavior.

The governing decision rule applied throughout:

> Reuse native semantics when they match; define a tiny application semantic relation
> when they don't. Exact semantic fit matters more than native reuse.

Correction-pass 1 adds two standing rules:

- **Authority is a location claim; evidence is a maturity claim.** Never merge them.
  A future architectural target is never current proof.
- **Representation is not semantics.** Using native SysML elements to represent a
  concept does not make the concept a native SysML semantic construct.

---

## 2. Correction pass 1 record (review items 1–9 of the disposition)

| Review point | Applied as |
|---|---|
| 1. Separate authority from evidence maturity | §5 schema: `authority_current` / `authority_target` (location) + `evidence_state` (maturity ladder). No entry is "proven" via its target; `privileged-closure-proven` requires a closure-evidence record (§9.3). |
| 2. Re-review `native-sysml` | §6.2: `Scenario`, `ValidationScenario`, `EvidenceContract` reclassified to `legacy-yaml` (representation ≠ semantics); all remaining native entries re-checked against exact semantic fit. |
| 3. Library adoption status explicit | `adoption_status` + `transition_gate` + `conditional_target` fields; PLEML family recorded `pinned-not-adopted`; target counts split unconditional vs conditional (§5.5). |
| 4. Correct O1/O2 boundary | §12: O1 keeps K-only parity/generalization (inverse-row parity F5, closure-evidence representation, behavior-preserving refactor); generating new Semantic Projection rows for unmigrated entries is O2 and not authorized. |
| 5. No fuzzy parity | §9.4 + §12: only exact comparison after purely cosmetic normalization, structured field comparison, or an explicit reviewed equivalence record. `differs` ⟹ `semantic_text_equivalence = review-required`. Similarity percentages removed. |
| 6. Generated facts vs reviewed decisions | §9.2: every entry is split into `observed` (mechanically derivable) and `reviewed` (governance metadata, never runtime authority); the generator must join layers without opaque Python constants. |
| 7. Closure evidence strengthened | §9.3: structured, revision-bound closure-evidence schema; K R6 #3 recorded as historical accepted evidence; no new entry promotes to `supported`. |
| 8. Revised migration order | §12: Wave 0a/0b/0c then candidates c1–c5 in the review's order. |
| 9. Findings kept | §13: F1–F8 retained (F6 and F8 updated to reference their corrections). |

---

## 3. Evidence basis — what was inspected

Read in full (repository, base SHA above):

- `approach/framework/ontology/de4sdv-basic-ontology.yaml` (645 lines; 93 entries) and
  `approach/framework/ontology/README.md`.
- Method kernel `textual-notation-of-model/packages/methods/de4sdv/` — all eight
  `.sysml` files (110 declarations total; verified by script).
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

Regression checks executed locally for this edition (exact results recorded in the PR at
the correction head): the K + projection + proof subset; `scripts/check_model_sync.py`;
`scripts/check_repo.py`; `tools/check_markdown_links.py`; and the full local suite.
Only files under `docs/method-conformance/o1/` differ from the base SHA.

Retained K closure record (historical, for K only): privileged run `34630102233`
(success), K SHA `72926c958d2bd3b1001088fa657ec906dffd53e7`; SysML project
`ea96301d-343a-4592-bad4-5dd997ca906a`; 82,088 elements / 62 source documents;
binding validation 40 mapped / 15 native / 4 external / 0 unresolved / 0 ambiguous.

---

## 4. Ontology accounting (recounted from the contract, not from summaries)

| Quantity | Count | Notes |
|---|---|---|
| Classes | **59** | |
| Relationships | **34** | |
| Total semantic entries | **93** | every one classified in the draft inventory |
| Class kernel mappings | 59 | 40 file + 15 native + 4 external |
| — file-mapped | 40 | 39 in the governed kernel dir + 1 cross-slice |
| — native | 15 | represented using SysML v2 constructs; no kernel declaration |
| — external | 4 | outside the SysML API baseline |
| Relationship mappings | 9 | 2 derivation-connection (K), 6 other executable strategies, 1 external |
| Vocabulary-only relationships | 25 | no `sysml_mapping` |
| Kernel declarations (governed dir) | **110** | = 39 ontology-mapped + 71 exclusions (exact pairs) |
| Cross-slice mapping | 1 | `AcceptanceCriterion` → `requirement def MiddlewareAcceptanceCriterion` in a feature slice |
| Validation rules | 10 | `DE4SDV-ONT-R001` … `R010` |

R0 reconciliation (R0 CSV, 84 rows → current 93): **+9 added, −0 removed, 0 kind-changed**
(seven Lane-A/B conformance classes, `DerivesFromNeed`, `derivedRequirementsOfNeed`).

---

## 5. Classification model (revised)

### 5.1 Rules

- **`authority_current`** = where the entry's engineering meaning is authoritatively
  established **today** (single source, per the precedence below).
- **`authority_target`** = where it should be established after migration. A target is
  never evidence; targets may be **conditional** (`conditional_target: true` + a
  `transition_gate`) and conditional targets are never counted as current authority.
- **`evidence_state`** = how strongly the (current) claim is supported, on the ladder
  `proposed` < `repository-evidenced` < `parity-reviewed` <
  `exact-toolchain-validated` < `privileged-closure-proven`; plus `blocked` and `unknown`.
  `privileged-closure-proven` requires a structured closure-evidence record (§9.3).
- Current-authority precedence: (1) model-resident consumed semantics →
  `model-authoritative`; (2) an accepted upstream library carries the vocabulary/status →
  `accepted-library-grounded`; (3) meaning outside the model → `external-reference`;
  (4) the concept itself is a native language construct → `native-sysml`;
  (5) otherwise the authored YAML definition is the established source → `legacy-yaml`;
  (6) insufficient information → `unknown`. *Representation primitives alone never
  qualify an entry as native.*
- **`adoption_status`** (`accepted` | `pinned-not-adopted` | `candidate` | `rejected` |
  `not-applicable`) records upstream-library disposition per entry; a pinned library is
  never counted as adopted.

### 5.2 Counts — current authority (93 entries)

| `authority_current` | Count |
|---|---|
| `model-authoritative` | **3** |
| `native-sysml` | **6** |
| `accepted-library-grounded` | **2** |
| `external-reference` | **3** |
| `legacy-yaml` | **78** |
| `unknown` | **1** |
| `native-kerml`, `de4sdv-application-semantic`, `policy-governance`, `representation-profile-only` | 0 currently |

Old→new mapping of the initial edition's counts (for the reviewer's delta check):
`model-authoritative-proven 3` → `model-authoritative 3` (evidence split to
`privileged-closure-proven`); `mixed-authority 45` → `legacy-yaml` (39 classes + 6
runtime-mapped relationships — their declarations/config exist, but the reviewed meaning
is still YAML-established and unparitied); `legacy-yaml-authoritative 30` → `legacy-yaml`;
`native-sysml 9` → `native-sysml 6` + `legacy-yaml 3` (reclassification, §6.2);
`external-reference 3`, `accepted-library-grounded 2`, `unknown 1` unchanged.

### 5.3 Counts — evidence state (93 entries)

| `evidence_state` | Count |
|---|---|
| `privileged-closure-proven` | **3** (the K triple only, via closure record `r6-3`) |
| `repository-evidenced` | **75** |
| `blocked` | **14** (8 PLE-family under the adoption gate; `derivesNeedFromConcern`; `allocatedTo`; `deployedTo`; `instantiatesCanonicalArchitecture`; `validatedBy`; `validatesFitnessForUse`) |
| `unknown` | **1** (`AssuranceClaim`) |
| `parity-reviewed`, `exact-toolchain-validated`, `proposed` | 0 currently |

### 5.4 Counts — adoption status (93 entries)

`not-applicable` 77 · `pinned-not-adopted` 8 (PLEML family) · `accepted` 4 (ODE4HERA
grounding) · `rejected` 3 (Requirement Derivation library, per K decision) · `candidate`
1 (GfSE SAF stakeholder source — flagged for disposition).

### 5.5 Counts — target authority (split unconditional vs conditional)

| `authority_target` | Unconditional | Conditional (`conditional_target`) |
|---|---|---|
| `model-authoritative` | **61** | 0 |
| `native-sysml` | **8** | 0 |
| `accepted-library-grounded` | **4** | **8** (PLEML family; gate `PLE-R → PLE-Q → PLE-S → PLE-A`) |
| `de4sdv-application-semantic` | **3** | **1** (`derivesNeedFromConcern`; gate: concern-usage inventory) |
| `external-reference` | **2** | 0 |
| `unknown` (deferred with blockers) | **6** | 0 |
| Totals | **84** | **9** |

Library-target split (review item 3, explicitly): **authorized 4** (ODE4HERA-backed
`VerificationMethod`, `EvidenceStatus`, `usesVerificationMethod`, `hasEvidenceStatus`) vs
**conditional 8** (PLEML family — not counted as adopted).

---

## 6. Per-category membership

### 6.1 Model-authoritative (current, 3)

The K triple — `DerivesFromNeed`, `derivesRequirementFromNeed`,
`derivedRequirementsOfNeed` — with `evidence_state = privileged-closure-proven` recorded
through closure record `r6-3` (revision-bound; §9.3). Semantics: provenance-only
derivation; typed ends carry domain/range/roles; owned Documentation carries strength and
claim boundary; the standard Requirement Derivation library is `rejected` with rationale
(`originalImpliesDerived` overclaims). No `SemanticMetadata` workaround.

### 6.2 Native SysML — with the exact-fit re-review (review item 2)

Retained `native-sysml` (6): `VariationPoint`, `Variant`, `Concern`, `Viewpoint`, `View`,
`VerificationCase` — each re-checked: the *concept itself* is carried by a native SysML
construct (variation/variant; concern def; viewpoint/view defs; verification case), and
the YAML row is a vocabulary pointer, not an added semantics. `VerificationCase`
additionally needs the plan §10 standard-library grounding witness before any stronger
claim (candidate c2).

**Reclassified to `legacy-yaml` (3)** — representation primitives only:

| Entry | Old label | New label | Why (exact-fit re-review) |
|---|---|---|---|
| `Scenario` | `native-sysml` | `legacy-yaml` | Operational-context parts + scenario-identity enums are representation; there is no native SysML concept named Scenario. Meaning established by the DE4SDV definition. |
| `ValidationScenario` | `native-sysml` | `legacy-yaml` | Scenario parts with bounded outcomes are representation; no native/library validation semantics established (the `validatedBy` family remains an explicit unknown). |
| `EvidenceContract` | `native-sysml` | `legacy-yaml` | Requirement usages associated with verification cases are representation; the bounded-observations contract is a DE4SDV method concept. |

No entry was changed merely because its YAML `kernel.native` field names native
constructs — the criterion is the concept's own meaning.

### 6.3 Accepted-library-grounded (2 current; 4 authorized targets)

`VerificationMethod` and `EvidenceStatus` — ODE4HERA via ADR 0009; `adoption_status =
accepted`; evidence `repository-evidenced` with ADR grounding records as required
evidence. Target-side additions: `usesVerificationMethod`, `hasEvidenceStatus`
(authorized). The PLEML family is **not** in this category (§5.5 conditional).

### 6.4 DE4SDV application semantic targets (4)

`specifiesFunction`, `hasRelevantArchitecture`, `hasRelevantEvidenceContract` (target,
unconditional — reviewed decision work, c5) and `derivesNeedFromConcern` (target,
**conditional** on the concern-usage inventory, c4). The K triple is the proven exemplar
of DE4SDV application semantics.

### 6.5 External / policy / configuration (3)

`hasEvidence` (explicit external boundary; no traversal by design), `EvidenceArtifact`
(external evidence registers), `FeatureConfiguration` (Bill-of-Features YAML —
external today; PLEML target conditional). Governance content inside the YAML
(`kernel_sync` + 71 exclusions, 10 validation rules) stays policy-governance with R003
mechanically enforced by sync point 6.

### 6.6 Vocabulary concepts

15 entries are proposed to remain **vocabulary-only in runtime support** while their
definitions move into the model (they are part of the 78 `legacy-yaml` current-authority
entries; support state is a separate observed field): the increment/concern family (6),
`constrainedBy`, `hasAcceptanceCriterion`, `supportedByEvidence`, `capturedInBaseline`,
and the five umbrella classes.

### 6.7 Legacy-yaml current authority (78)

Groups: 39 file-mapped method-vocabulary classes (declaration + doc model-resident;
reviewed definition text still YAML-established; parity not reviewed); the 3
reclassified entries above; 5 umbrella classes (no model-resident definition home yet);
6 runtime-mapped relationships (model carries facts; mapping meaning/config still YAML);
25 vocabulary-only relationships. Per-entry detail in the draft inventory and Appendices.

**Text observations (observed layer; not parity evidence):** `normalized-exact` 7 ·
`differs` 30 · `doc-absent` 3 (incl. one bodyless declaration). Every `differs` /
`doc-absent` entry carries `semantic_text_equivalence = review-required` and non-empty
`required_evidence` — no entry's model authority is treated as demonstrated without a
reviewed equivalence record or a model-side update (§9.4).

### 6.8 Unknowns (current: 1; target-unknown: 6)

`AssuranceClaim` (current `unknown`). Target-unknown with explicit blockers:
`AssuranceClaim`, `allocatedTo`, `deployedTo`, `instantiatesCanonicalArchitecture`,
`validatedBy`, `validatesFitnessForUse`. Bounded open questions per entry are in the
draft inventory; summary in §14.

---

## 7. Current runtime semantic dependencies on the authored YAML

Unchanged from edition 1 (verified again in this pass): the YAML is loaded at runtime by
`de4sdv/semantic/kernel_contract.py`; the revision binding pins the YAML path + SHA-256
and refuses a runtime whose contract digest differs. Consumers: `traversal` (executes
only declared strategies; raises on unknown strategy; no name fallback), `query`
(`_mapped_predicates` for `semantic_neighbors`/`trace`), `impact` (6 mappings), and the
identity-type expectations in `api_binding`/`validation`/`kernel_binding_index`. Kernel
identity itself comes from ingestion-validated `kernel_bindings` UUIDs (ADR 0011) — YAML
supplies expectations, the binding supplies identity; missing bindings fail closed.
Additional consumers: `check_model_sync` (SP5/SP6), ingestion/validator scripts, the
ask-viewer tooling, and the test suites.

---

## 8. API Representation Profile concerns (unchanged findings)

Profile v0 covers 1 of 9 mappings; `sysml_mapping` blocks still mix semantics and
mechanics (F2); two implemented strategies (`verification`, `property-reference`) remain
unassociated with any ontology mapping (F4); per-entry completeness checks need
generalization; the external strategy is honest but its boundary must stay explicit.

---

## 9. Proposed machine-readable inventory schema (revised)

Schema id proposed: `de4sdv.semantic-authority-inventory/v1` (review artifact;
runtime-inert). One record per semantic entry; two nested layers:

### 9.1 Record shape

- `identity` — canonical identity; kind; current YAML path.
- `observed` (Layer A — mechanically derivable): grounding kind and references (file +
  declaration | native | external | sysml_mapping strategy), domain/range,
  query direction, runtime support state, and the **doc-text observation**
  (`normalized-exact` | `differs` | `doc-absent` | `block-not-located`).
- `reviewed` (Layer B — governance/migration metadata, **never runtime semantic
  authority**): `authority_current`, `authority_target`, `conditional_target`,
  `evidence_state`, `adoption_status`, `transition_gate`, `exact_fit_decision`,
  `disposition`, `confidence`, `stage`, `note`, `unknowns`, `required_evidence`,
  `semantic_text_equivalence`, and `closure_evidence_ref` where applicable.

### 9.2 Generated facts vs reviewed decisions (review item 6)

- **Layer A** is derived mechanically from: `KernelContract`; ontology structure; kernel
  mappings; the runtime strategy registry; model declarations/bindings; representation
  evidence where available.
- **Layer B** is a committed, reviewable decisions dataset (edited through PRs). It
  carries classification, exact-fit decisions, targets, adoption decisions, boundaries,
  owners/stages, and unresolved questions. It is **not** runtime authority and must not
  be encoded as opaque Python lookup constants — the Phase-2 generator joins A + B,
  validates consistency, and preserves which fields came from which layer.
- The Phase-1 assembly script used for this draft is a session-side analysis aid, **not**
  the proposed generator.

### 9.3 Closure-evidence schema (review item 7)

`privileged-closure-proven` requires a structured, revision-bound record
(schema `de4sdv.closure-evidence/v1`): exact Git SHA; SysML project ID; SysML commit ID;
workflow/run or retained-evidence identity; artifact name and content digest (digest may
be explicitly `not recorded` — never fabricated); proof result; closure scope; subject
and predicate identities. K's R6 #3 is recorded as historical accepted evidence
(`r6-3`); the K runtime's bare `witness_closure_verified` boolean is **not** treated as
sufficient evidence in the schema. No new entry is promoted to `supported` in this pass.

### 9.4 Text-parity rule (review item 5)

Allowed: exact comparison after purely **cosmetic** normalization (case, punctuation,
whitespace/line wrapping); structured comparison of machine-readable semantic fields;
an explicit reviewed equivalence record when wording differs. Material wording
difference ⟹ `semantic_text_equivalence = review-required` with non-empty
`required_evidence`. Fuzzy similarity, word-overlap scores, and normalized-similarity
percentages are **not** parity and were removed from this edition.

---

## 10. Proposed files to add/change (Phase 2, review-gated)

1. `de4sdv/semantic/authority_inventory.py` — Layer A fact extraction + validator;
   reuses `KernelContract`; deterministic ordering.
2. `docs/method-conformance/o1/authority-review-decisions.yaml` — Layer B reviewed
   decisions as a committed, reviewable dataset (never Python constants).
3. `scripts/generate_semantic_authority_inventory.py` — joins A + B with per-field layer
   provenance; refuses to emit on missing coverage or inconsistent decisions.
4. `docs/method-conformance/o1/semantic-authority-inventory.json` (generated) and
   `authority-inventory.md` (generated review table; asserted row-for-row).
5. `docs/method-conformance/o1/closure-evidence.json` — structured closure records
   (§9.3); K `r6-3` recorded; no other entries added.
6. `tests/test_semantic_authority_inventory.py` — coverage/schema/determinism tests (§11).
7. K-only hardening (Wave 0b, behavior-preserving): extend `de4sdv/semantic/projection.py`
   for the F5 inverse-row parity **without changing K output semantics**.
8. `approach/framework/ontology/README.md` — stale-text repair (F1, Wave 0c).

NOT proposed: no new graph, no second evaluator, no second ontology, no generator-driven
YAML authority, no new generated semantic rows in O1 (that is O2), no runtime change.

---

## 11. Proposed test matrix (revised)

| Test | Asserts |
|---|---|
| coverage/classes, coverage/relationships | every class/relationship has exactly one record (recounted from YAML) |
| coverage/mappings, coverage/runtime | all mappings accounted; every runtime strategy associated or flagged |
| determinism | two generations byte-identical |
| K precedent | K triple rows consistent with closure record `r6-3`; K suites stay green |
| authority/evidence separation | no entry can claim `privileged-closure-proven` without a closure record; targets never count as evidence; conditional targets flagged |
| adoption gate | `pinned-not-adopted` libraries never counted as adopted; conditional targets excluded from authorized counts |
| text-parity rule | `normalized-exact` allowed; `differs` ⟹ `review-required` + non-empty required evidence; no similarity metrics accepted |
| layer provenance | every field attributable to observed/reviewed; generator rejects Layer-B fields entering runtime paths |
| classification closure | category vocabularies closed; `unknown` requires a bounded question |
| adoption evidence | `accepted-library-grounded` requires the upstream grounding record (ADR 0009 / pin) |
| external boundary | `hasEvidence` stays external; no reclassification |
| duplicate refusal | duplicate identity or incompatible semantics fails generation |
| binding identity | inventory binds base SHA + contract identity |
| no-runtime-change | all A–D/K suites retained; no runtime module changed on the branch |

---

## 12. Proposed bounded migration sequence (revised, O1/O2 boundary corrected)

**O1/O2 boundary (explicit):** O1 is reviewed mapping / parity-controlled extension.
Generating **new** Semantic Projection rows for previously unmigrated
predicates/classes — or advertising new entries through generated projection — is
**O2**, not authorized here, even if the inventory describes the entries. O1 may refactor
the K projection/profile internals, make the existing K projection inventory-aware
internally, fix the K inverse-row parity gap (F5), add coverage/parity validation, and
keep K output semantically equivalent.

**Wave 0a — inventory foundation (no semantic change):** schema + Layer A fact
extraction + Layer B reviewed-decision dataset + deterministic coverage validator
(§9–§11).

**Wave 0b — K-only parity/generalization hardening (behavior-preserving):** inverse-row
parity F5; structured closure-evidence representation; inventory-aware K projection
internals; **no new generated semantic rows**.

**Wave 0c — documentation repair:** stale ontology README and other K-era drift (F1).

**Semantic parity candidates (in the review's order):**

1. **c1 — Lane-A/B method-conformance class batch** (7 classes): low semantic
   ambiguity; proves the inventory/parity mechanism. Meaning: typed method-contract
   vocabulary (obligations, scopes, memberships, source kinds, tested-scope declarations,
   retained-record and attestation references). Fit: already model-resident with
   attribute-level docs; definition-level parity work only.
2. **c2 — `verifiedBy`** after exact standard/library grounding is established.
   Meaning: "verification case VC is the verification objective for requirement R";
   coverage is not execution success. Fit: native `RequirementVerificationMembership`
   already the runtime carrier; missing piece is the §10 library grounding
   (`VerificationCases::VerificationCase` / `verificationCases`) and moving
   roles/strength under parity discipline.
3. **c3 — `hasSubject`** after native `SubjectMembership` semantics and the DE4SDV
   MemberProduct restriction are **explicitly separated** (native subject meaning vs the
   added member-product scope restriction — recorded as a reviewed contract note; never
   widened to other subject kinds).
4. **c4 — `derivesNeedFromConcern`** only after the concern-usage inventory resolves its
   endpoint semantics. Meaning: "the stakeholder need N originates from stakeholder
   concern C" — provenance only. Fit: no exact native requirement-to-concern derivation
   identified; the K pattern (minimal application connection) applies only if concern
   usages exist to ground the ends; otherwise blocked with the blocker recorded.
5. **c5 — relevance family + `realizedBy`** remain reviewed decision work afterward
   (claim boundaries, endpoint-type discrimination under UG-05, allocation-vs-realization
   boundary under the frozen signature).

**Deferred to owning lanes:** PLE family (PLEML, pinned-not-adopted), T/E items
(`hasEvidence` boundary, `EvidenceArtifact` design, `allocatedTo`, `deployedTo`,
`instantiatesCanonicalArchitecture`), validation construct inspection (`validatedBy`,
`validatesFitnessForUse`), and the AssuranceClaim design.

---

## 13. Findings (retained; F6/F8 annotated with their corrections)

- **F1 — stale ontology README after K** (fix in Wave 0c).
- **F2 — YAML mixes semantics and mechanics** in `sysml_mapping` (split per §9).
- **F3 — R0 inventory supersession** (reconcile + supersede pointer once inventory v1 exists).
- **F4 — unassociated runtime strategies** (`verification`, `property-reference`).
- **F5 — K inverse-row parity gap** (fix scoped to Wave 0b, behavior-preserving).
- **F6 — closure evidence not machine-bound** — accepted; corrected by the §9.3
  structured closure-evidence schema; K runtime unchanged in this pass.
- **F7 — cross-slice `AcceptanceCriterion` mapping** (kernel promotion vs governed
  cross-slice mapping decision).
- **F8 — documentation wording drift** — accepted; corrected by the §9.4 text-parity
  rule (normalized-exact or explicit review; no fuzzy similarity).

---

## 14. Explicit unknowns (summary; per-entry detail in the draft)

1. `AssuranceClaim` — native construct, accepted library, or application definition?
2. `validatedBy` / `validatesFitnessForUse` — which native/library validation relation
   (if any) fits fitness-for-use validation?
3. `allocatedTo` — native allocation ends/exact types; collision with frozen `realizedBy`.
4. `deployedTo` — signature migration vs distinct reviewed predicate.
5. `instantiatesCanonicalArchitecture` — canonical-usage selector design.
6. Concern-link inventory for `derivesNeedFromConcern` (candidate c4 gate).
7. Umbrella vocabulary home (`ArchitectureElement`, `Function`, `LogicalElement`,
   `PhysicalElement`, `Interface`).
8. Closure-artifact digest retrieval for `r6-3` (record completeness; never fabricated).
9. GfSE SAF stakeholder source — adoption/publication disposition review
   (`adoption_status = candidate`).

---

## 15. Evidence sufficiency (stop-condition check)

All edition-2 conclusions come from repository evidence at the base SHA plus retained K
records. No new privileged ingestion is required or proposed for Phase 1 or this
correction pass. Nothing here depends on evidence that cannot be established from the
repository; later steps that cannot be so established must be stopped and justified
before any privileged dispatch (Unified Plan stop conditions).

---

## 16. Non-claims

- Not an authority cutover; YAML remains the current runtime authority for unmigrated scope.
- Not O2/O3/O4 progress; no new generated semantic rows; no retirement.
- **No new support promotion**: only the K triple is `privileged-closure-proven`; nothing
  else is labeled proven or supported by this pass.
- The reviewed decision layer is governance/migration metadata only — never runtime
  semantic authority.
- Not a claim that all vocabulary is supported; 78 entries remain `legacy-yaml` current
  authority and 6 targets stay `unknown`.
- Not a redesign of K; the K representation and closure record are preserved as-is.
- Not a privileged-evidence claim; the K R6 record is historical exact-revision evidence
  for K only.

---

## Appendix A — classes (59), full classification

Columns: authority (current → target; `[cond]` = conditional target) · evidence state ·
adoption status · disposition · confidence · stage · note.

| id | auth | ev | adopt | disp | conf | stage | note |
|---|---|---|---|---|---|---|---|
| EngineeringIncrement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| FeatureIncrement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| NeedsRequirementsIncrement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| IncrementEngineeringQuestion | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| IncrementLifecycleDecision | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| IncrementTraceabilityShell | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| MethodPhase | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Enum literals carry per-phase docs in the model; YAML summary; conformance consumers reference phases. Declaration + doc model-res… |
| SignalMappingDisposition | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Enum literal docs resident. Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet revi… |
| LogicalToSoftwareSignalMappingRecord | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Attribute-level docs resident. Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet r… |
| SystemToSoftwareSignalMappingCandidate | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | batched-parity (post-0a/0b) | Allocation def with non-claiming doc; allocation realization semantics unresolved. Declaration + doc model-resident; reviewed defi… |
| IncrementSize | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| SystemLayer | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| ProductLine | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| MemberProduct | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Kernel declaration ProductLineMemberProduct; specialization lineage consumed by the hasRelevantArchitecture exclusion. Declaration… |
| Feature | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | ISO 26580 rule carried by specialization structure + R001 review. Declaration + doc model-resident; reviewed definition text still… |
| ProductLineCharacteristic | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| CommonCapability | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| DeferredProductLineScope | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| VariationPoint | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | high | O2+ (parity pointer) | Native SysML variation definition/usage. YAML row is a vocabulary pointer; representation/usage conventions remain method context. |
| Variant | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | high | O2+ (parity pointer) | Native variant usage. YAML row is a vocabulary pointer; representation/usage conventions remain method context. |
| FeatureConfiguration | external-reference -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | retain-explicit-external-boundary | high | PLE | Bill-of-Features YAML under model-based-product-line-engineering/; operational authority until an authorized PLE cutover; PLEML ta… |
| Stakeholder | legacy-yaml -> model-authoritative | repository-evidenced | candidate | move-meaning-into-model | high | batched-parity (post-0a/0b) | Roles source-backed from the GfSE SAF stakeholder library (re-declared as part defs; Apache-2.0; see saf-source.yaml); adoption/pu… |
| Concern | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | high | O2+ (parity pointer) | Native concern def/usage; SAF viewpoint selections in kernel. YAML row is a vocabulary pointer; representation/usage conventions r… |
| Need | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | StakeholderNeedCandidate requirement def; ODE4HERA attribute set via ADR 0009; consumed by K lineage and R003. Declaration + doc m… |
| Requirement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | RequirementCandidate requirement def; SYSMOD seam + ODE4HERA attrs; consumed by impact/K. Declaration + doc model-resident; review… |
| ProblemStatement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | R003 exclusion grounding (traced into, not out of). Declaration + doc model-resident; reviewed definition text still YAML-establis… |
| ArchitectureDecisionRecord | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | R003 origin grounding. Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| RegulatoryConstraint | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | R003 origin grounding; no-compliance-claim boundary must stay model-carried. Declaration + doc model-resident; reviewed definition… |
| ArchitectureElement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | low | O2+ (design decision) | Umbrella over native part/port/behavior definitions used in architecture slices. No model-resident definition home exists yet; rev… |
| Function | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | low | O2+ (design decision) | Umbrella over native action/state/behavior definitions in functional-architecture slices. No model-resident definition home exists… |
| LogicalElement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | low | O2+ (design decision) | Umbrella over native part defs in logical-architecture slices. No model-resident definition home exists yet; reviewed decision nee… |
| PhysicalElement | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | low | O2+ (design decision) | Umbrella over native part defs in physical/software realization slices. No model-resident definition home exists yet; reviewed dec… |
| Interface | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | defer | low | O2+ (design decision) | Umbrella over native port defs and connection elements. No model-resident definition home exists yet; reviewed decision needed on … |
| Scenario | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | batched-parity (post-0a/0b) | RECLASSIFIED from native-sysml: operational-context parts + scenario-identity enums are representation, not native "Scenario" sema… |
| VerificationCase | native-sysml -> native-sysml | repository-evidenced | not-applicable | prove-existing-model-authority | medium | c2 | Native verification case; plan Section 10 requires standard Systems Model Library grounding (VerificationCases::VerificationCase /… |
| ValidationScenario | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | O2+ | RECLASSIFIED from native-sysml: scenario parts with bounded outcomes are representation; no native/library validation semantics es… |
| VerificationMethod | accepted-library-grounded -> accepted-library-grounded | repository-evidenced | accepted | keep-as-is | high | O2+ (parity) | ODE4HERA requirements-management library verificationMethod attribute populated with standard VerificationMethodKind values (ADR 0… |
| AcceptanceCriterion | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | batched-parity (post-0a/0b) | Kernel mapping points at MiddlewareAcceptanceCriterion in a feature slice (cross-slice mapping); decide kernel promotion vs retain… |
| EvidenceArtifact | external-reference -> external-reference | repository-evidenced | not-applicable | retain-explicit-external-boundary | high | T/E | Evidence registers and retained-evidence items; plan Section 10/12 evidence-reference modeling pending. |
| EvidenceContract | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | batched-parity (post-0a/0b) | RECLASSIFIED from native-sysml: "Requirement usages associated with verification cases" is representation; the bounded-observation… |
| EvidenceStatus | accepted-library-grounded -> accepted-library-grounded | repository-evidenced | accepted | keep-as-is | high | O2+ (parity) | ODE4HERA VVStatus via the method-context adapter; no parallel status vocabulary. |
| Assumption | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| Gap | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | IncrementGap; "must not be hidden" boundary. Declaration + doc model-resident; reviewed definition text still YAML-established; pa… |
| MissingRealizationRecord | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| BlockedRealizationBranchRecord | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| AssuranceClaim | unknown -> unknown | unknown | not-applicable | defer | low | O2+ | YAML claims "Claim usages framed by the argumentation-assurance viewpoint"; no standard argumentation construct identified; mechan… |
| Viewpoint | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | high | O2+ (parity pointer) | Native viewpoint def; selections in DE4SDV_MethodViewpoints + SAF_Viewpoints. YAML row is a vocabulary pointer; representation/usa… |
| View | native-sysml -> native-sysml | repository-evidenced | not-applicable | keep-as-is | high | O2+ (parity pointer) | Native view. YAML row is a vocabulary pointer; representation/usage conventions remain method context. |
| TraceLink | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Declaration + doc model-resident; reviewed definition text still YAML-established; parity not yet reviewed. |
| RequiredTraceChain | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | Chain vocabulary used in review; no executable chain validation. Declaration + doc model-resident; reviewed definition text still … |
| Baseline | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | batched-parity (post-0a/0b) | DE4SDVEvidenceBaseline; "review/evidence baseline without implying accepted evidence" boundary. Declaration + doc model-resident; … |
| MethodContractObligation | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | c1 (conformance batch) | Model carries attribute-level schema docs (richer than YAML); schema intent model-resident. |
| EvaluationSourceKind | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | c1 (conformance batch) | Enum literal docs model-resident. |
| MethodEvaluationScope | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | c1 (conformance batch) | Scope binding semantics model-resident; R0 baseline Section 6 lineage. |
| EvaluationScopeMembership | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | c1 (conformance batch) | contributes-flag semantics model-resident. |
| TestedScopeDeclaration | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | c1 (conformance batch) | Conservative scope-equality fields model-resident. |
| RetainedExecutionRecordReference | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | c1 (conformance batch) | External bytes + digest reference contract model-resident; no def-level doc (attribute docs). |
| AcceptanceAttestationReference | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | c1 (conformance batch) | Policy reference boundary model-resident; policy status external. |
| DerivesFromNeed | model-authoritative -> model-authoritative | privileged-closure-proven | rejected | keep-as-is | high | K | DE4SDV application connection definition; typed ends + owned Documentation carry domain/range/roles/strength/boundary. Standard Re… |

## Appendix B — relationships (34), full classification

| id | auth | ev | adopt | disp | conf | stage | note |
|---|---|---|---|---|---|---|---|
| addressesConcern | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | domain/range authored in YAML; no executable mapping; definition moves into the model. |
| hasStakeholder | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | domain/range authored in YAML; no executable mapping; definition moves into the model. |
| selectedViewpoint | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | domain/range authored in YAML; no executable mapping; definition moves into the model. |
| producesView | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | domain/range authored in YAML; no executable mapping; definition moves into the model. |
| derivesNeedFromConcern | legacy-yaml -> de4sdv-application-semantic [cond] | blocked | not-applicable | introduce-minimal-de4sdv-relation | medium | c4 | Same family as K; Need -> Concern provenance: "the stakeholder need N originates from stakeholder concern C" - provenance only. No… |
| derivesRequirementFromNeed | model-authoritative -> model-authoritative | privileged-closure-proven | rejected | keep-as-is | high | K | Requirement -> Need; inverse traversal over the same witness; YAML row is the O0/O1 parity oracle. Standard Requirement Derivation… |
| derivedRequirementsOfNeed | model-authoritative -> model-authoritative | privileged-closure-proven | rejected | keep-as-is | high | K | Forward traversal over the same witness; declares no new model fact. Standard Requirement Derivation library evaluated and deliber… |
| constrainedBy | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | batched-parity (post-0a/0b) | Regulatory constraint provenance; R003 family; no executable mapping planned. |
| specifiesFeature | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | medium | PLE | Product-line relationship; PLEML target is conditional on adoption for the admitted scope; signature/strength decision pending (pl… |
| specifiesCommonCapability | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | medium | PLE | Product-line relationship; PLEML target is conditional on adoption for the admitted scope; signature/strength decision pending (pl… |
| realizedBy | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | prove-existing-model-authority | medium | c5 | Allocation facts model-resident; signature frozen (plan Section 10); reviewed semantic-fit (allocation vs realization) required be… |
| specifiesFunction | legacy-yaml -> de4sdv-application-semantic | repository-evidenced | not-applicable | prove-existing-model-authority | medium | c5 | Relevance only over generic Dependency with typed endpoint filters; endpoint types alone never establish stronger meaning (UG-05). |
| hasRelevantArchitecture | legacy-yaml -> de4sdv-application-semantic | repository-evidenced | not-applicable | prove-existing-model-authority | medium | c5 | Incoming dependency relevance with MemberProduct-lineage source exclusion (application semantics currently in YAML config + code). |
| allocatedTo | legacy-yaml -> unknown | blocked | not-applicable | defer | low | T/E | Function -> LogicalElement; native allocation ends proof required; collision risk with the frozen realizedBy signature (plan Secti… |
| deployedTo | legacy-yaml -> unknown | blocked | not-applicable | defer | low | T/E | LogicalElement -> PhysicalElement; realization vs software-deployment distinction unresolved. |
| verifiedBy | legacy-yaml -> native-sysml | repository-evidenced | not-applicable | prove-existing-model-authority | medium | c2 | Native RequirementVerificationMembership reverse traversal; verification-objective semantics; coverage is not execution success; p… |
| usesVerificationMethod | legacy-yaml -> accepted-library-grounded | repository-evidenced | accepted | adopt-accepted-library-relation | medium | batched-parity (post-0a/0b) | Method carried natively by VerificationMethod metadata with standard method-kind vocabulary (ADR 0009 amendment). |
| hasAcceptanceCriterion | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | batched-parity (post-0a/0b) | Verification-case objective/criterion vocabulary; consider native verification objective representation during verification-family… |
| validatedBy | legacy-yaml -> unknown | blocked | not-applicable | defer | low | O2+ | Need -> ValidationScenario; native validation construct not yet inspected. |
| validatesFitnessForUse | legacy-yaml -> unknown | blocked | not-applicable | defer | low | O2+ | ValidationScenario -> Need; inverse family of validatedBy. |
| hasEvidence | external-reference -> external-reference | repository-evidenced | not-applicable | retain-explicit-external-boundary | high | T/E | Explicit external boundary (external-data-required); traversal returns nothing by design; model-resident reference semantics only … |
| hasEvidenceStatus | legacy-yaml -> accepted-library-grounded | repository-evidenced | accepted | adopt-accepted-library-relation | medium | batched-parity (post-0a/0b) | Connects external evidence artifacts to the ODE4HERA VVStatus vocabulary; status already carried in model slices. |
| recordsAssumption | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | domain/range authored in YAML; no executable mapping; definition moves into the model. |
| recordsGap | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | high | batched-parity (post-0a/0b) | domain/range authored in YAML; no executable mapping; definition moves into the model. |
| supportedByEvidence | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | O2+ | Assurance-claim family; contract migrates with the claim-design decision (see AssuranceClaim). |
| appliesToMemberProduct | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | medium | PLE | Product-line relationship; PLEML target is conditional on adoption for the admitted scope; signature/strength decision pending (pl… |
| hasSubject | legacy-yaml -> native-sysml | repository-evidenced | not-applicable | prove-existing-model-authority | medium | c3 | Native SubjectMembership; separate the native subject semantics from the DE4SDV member-product restriction explicitly; do NOT wide… |
| hasRelevantEvidenceContract | legacy-yaml -> de4sdv-application-semantic | repository-evidenced | not-applicable | prove-existing-model-authority | medium | c5 | Incoming dependency relevance restricted to requirement-usage sources; disjointness with specifiesFunction must stay enforced. |
| selectsFeature | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | medium | PLE | Product-line relationship; PLEML target is conditional on adoption for the admitted scope; signature/strength decision pending (pl… |
| instantiatesCanonicalArchitecture | legacy-yaml -> unknown | blocked | not-applicable | defer | low | T/E | Vocabulary only; requires an explicit canonical-usage selector (no name-based filter). |
| includesCommonCapability | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | medium | PLE | Product-line relationship; PLEML target is conditional on adoption for the admitted scope; signature/strength decision pending (pl… |
| variesAt | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | medium | PLE | Product-line relationship; PLEML target is conditional on adoption for the admitted scope; signature/strength decision pending (pl… |
| selectsVariant | legacy-yaml -> accepted-library-grounded [cond] | blocked | pinned-not-adopted | defer | medium | PLE | Product-line relationship; PLEML target is conditional on adoption for the admitted scope; signature/strength decision pending (pl… |
| capturedInBaseline | legacy-yaml -> model-authoritative | repository-evidenced | not-applicable | move-meaning-into-model | medium | O2+ | Evidence-to-baseline provenance; T/E evidence design dependent. |
