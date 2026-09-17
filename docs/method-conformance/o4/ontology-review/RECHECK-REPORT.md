# RECHECK-REPORT — DE4SDV 93-entry ontology review, package revision 2

Date: 2026-09-17 · Snapshot: `de4sdv/DE4SDV` `main` @ `bc2b65abb623e50032f177d566e34e1a41c09f34` (read-only) · Repository modification: none.
Scope of this revision: (a) independent architecture recheck (24 identities); (b) full-package integration repair with root-cause fix; (c) hardened machine validation; (d) regenerated deliverables. Semantic decision preservation rule applied throughout.

---

## 1. Architecture recheck (24/24)

**Method.** Each identity was re-checked against actual repository evidence at the pinned revision: ontology YAML row; governed `.sysml` declarations and usages (`grep` over `textual-notation-of-model/`, `model-based-product-line-engineering/`); normative clauses in the formal KerML 1.0 / SysML 2.0 texts; runtime consumers (`de4sdv/semantic/*`, `scripts/check_model_sync.py`); O1 records; ADRs. Naming similarity was never used as evidence; representation was never accepted as semantics.

**Result: 24 identities checked, 24 confirmed unchanged, 0 substantively changed.** No classification, definition, authority target, disposition, migration class, blocker or O3 status changed. Several rows gained stronger evidence anchors.

| Identity | Classification (confirmed) | Disposition (confirmed) | Recheck highlight (new/strengthened evidence) |
|---|---|---|---|
| Stakeholder | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | `de4sdv_stakeholders.sysml:1-17` base def + native stakeholder-parameter mechanics comment; §8.3.21.12 StakeholderMembership; usage sites in slices |
| Concern | NATIVE_EXPLICIT | KEEP_NATIVE | native `concern def`/usages verified (`de4sdv_method_concerns_and_viewpoints.sysml:26-50`, 87 feature-slice concern usages); §7.21.3, §8.3.21.3/.4/.5, §8.4.17.4/.5 |
| Need | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | `StakeholderNeedCandidate` lineage + NRM attrs (`de4sdv_method_context.sysml:98-123`) |
| Requirement | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | `RequirementCandidate :> SYSMODRequirementBase, RequirementsManagementAttributeBase` (`:125-150`) |
| ProblemStatement | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | R003 exclusion grounding (`scripts/check_model_sync.py:934`) |
| RegulatoryConstraint | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | `RegulatoryConstraintCandidate` doc: "Grounds the ontology RegulatoryConstraint class and R003 derivation targets" (`:154-157`); R003 set (`check_model_sync.py:805,1118`) |
| ArchitectureElement | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | **Verified no model-resident declaration**; only model occurrence is a `TraceLink` string literal (`de4sdv_method_process.sysml:122`); declared range of frozen `hasRelevantArchitecture`; c5 constituent filter |
| Function | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | No model declaration; range of `specifiesFunction` with action-typed executable filter; not normative behavior semantics |
| LogicalElement | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | No model declaration; `allocatedTo` range (vocabulary-only); RFLP layer discriminator |
| PhysicalElement | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | No model declaration; `deployedTo` range (blocked redesign) |
| Interface | KEEP_VOCABULARY_ONLY | KEEP_VOCABULARY_ONLY | No model declaration; no predicate names it as executable domain/range |
| Scenario | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | `enum def DegradedInputScenarioIdentity` + scenario-typed attributes (`aebs_degraded_input_verification.sysml:11-72`); parity-enforced sync point 1 (`check_model_sync.py:59`) |
| ValidationScenario | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | In-model statement **"(SysML v2 provides no native validation-case keyword)"** (`middleware_verification_evidence.sysml:422,453,485`) |
| VerificationMethod | NATIVE_EXPLICIT | KEEP_NATIVE | **Native `@VerificationMethod{ kind = … }` metadata annotations confirmed** in ≥5 slices; ADR 0009 NRM A8 attribute carries native `VerificationMethodKind` values; §9.2.17.2.6/.7 |
| AcceptanceCriterion | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | Exactly 2 criterion defs (`MiddlewareAcceptanceCriterion` `middleware_verification_evidence.sysml:146`, `VisualizationAcceptanceCriterion` `:158`); c5 measured 14 role usages; requirement-shape ≠ acceptance semantics |
| EvidenceArtifact | REPRESENTATION_ONLY | KEEP_EXTERNAL_REFERENCE | `item def RetainedMiddlewareEvidence` + 4 retained records (reference-shaped) |
| EvidenceContract | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC (BLOCKED) | **8 lineage-less per-slice defs enumerated** (DegradedInput, Bicycle, Nominal, RegulatoryCriterion, NonActivation, Pedestrian, PartialIntervention, Override) + distinct traceability bridge `EvidenceContractTraceabilityRequirementCandidate :> RequirementCandidate` (`method_context.sysml:152`) |
| EvidenceStatus | ACCEPTED_LIBRARY | KEEP_ACCEPTED_LIBRARY | VVStatus adoption re-verified (`de4sdv_sysmod_adapter.sysml:24`; `verificationStatus = VVStatus::NotStarted` values in usages); slice-local enum dimension noted as outside the library claim |
| Assumption | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | `IncrementAssumption` (`method_context.sysml:164`) + governed usages |
| Gap | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC | `IncrementGap` (`method_context.sysml:168`); distinct from realization records |
| AssuranceClaim | NO_NATIVE_SEMANTIC_FIT | KEEP_DE4SDV_APPLICATION_SEMANTIC | Claim/argument layer confirmed: `VisualizationClaim`/`VisualizationCounterClaim` requirement defs + argument/evidence dependency traces (`aebs_visualization_verification_evidence.sysml:618-742`); ArgumentationAssurance concern/viewpoint frames in ≥6 slices; **zero `assert` usages in the model** (AssertConstraintUsage not a claim construct) |
| Viewpoint | NATIVE_EXPLICIT | KEEP_NATIVE | Native `viewpoint def` catalogue (`de4sdv_method_concerns_and_viewpoints.sysml:85-129`); §8.3.26.8/.9; §8.4.22.3/.4 |
| View | NATIVE_EXPLICIT | KEEP_NATIVE | Native view usages (assurance views `aebs_bicycle_verification.sysml:92`, `aebs_evidence.sysml:312`); §8.3.26.7/.11 |
| DerivesFromNeed | REPRESENTATION_ONLY | KEEP_DE4SDV_APPLICATION_SEMANTIC (ALREADY_COMPLETE) | Connection def (`method_context.sysml:25`); `model_authority.py` locates, never defines; K final decision recorded. Three-way distinction stated: identity = application semantic carrier; native connection = witness/representation only; the two navigations = queries over the same witness (no logical implication, no satisfaction) |

**Special-scrutiny conclusions (as requested):**
- **ArchitectureElement** — genuinely necessary as a declared DE4SDV umbrella (it is the declared range of the frozen `hasRelevantArchitecture` and the carrier of the c5 constituent rules); native typing alone cannot express "architecture elements excluding requirements/product-line traces". Remains application-semantic pending a model home.
- **Function** — not equivalent to normative behavior semantics: DE4SDV `Function` is a selection umbrella over action/state/behavior definitions whose executable admission rules are application-level; representation via actions ≠ semantic equivalence.
- **LogicalElement / PhysicalElement** — layer membership has no native marker; explicit DE4SDV semantics required (or a reviewed model-resident convention). Home decision open.
- **Scenario / ValidationScenario** — representation (parts/enums) is native; scenario and validation *meaning* is application-level (O1 reclassification upheld; the model itself documents the absence of a native validation-case keyword).
- **VerificationMethod / EvidenceStatus** — both verified; VerificationMethod is native-metadata-carrying (O1's "accepted-library-grounded" label conflated the NRM A8 carrier); EvidenceStatus keeps the accepted-library grounding for the requirement-verification dimension only.
- **AcceptanceCriterion** — requirement-based representation does not by itself establish acceptance-criterion semantics; the role identity remains an open contract.
- **EvidenceContract** — remains a DE4SDV method/application concept with a blocked identity discriminator; not native, not library-grounded.
- **AssuranceClaim** — current representation is requirement/assertion-shaped; it does not by itself provide assurance semantics; claim design remains the open gate.
- **DerivesFromNeed** — no overstatement of the native connection in the review package (provenance only).

**Unresolved decisions/blockers in the architecture slice:** umbrella definition homes (5); AcceptanceCriterion kernel promotion; EvidenceContract lineage contract; AssuranceClaim claim design; canonical-architecture source (`instantiatesCanonicalArchitecture`, PLE slice); PLE configurator gates; SAF role-def adoption/publication disposition. All are recorded in the package's open-decisions register.

---

## 2. Full review integrity

| Check | Before repair | After repair |
|---|---|---|
| Rows | 93 | 93 |
| Classes / relationships | 59 / 34 | 59 / 34 |
| Duplicate identities | 0 | 0 |
| Character-split `semantic_consumers` rows | **58** (all parent + architecture rows; e.g. MethodPhase: 123 single-character entries) | **0** |
| Character-split evidence rows | **3** (Stakeholder, EvidenceContract, EvidenceStatus) | **0** |
| `open_decisions` as bare string | **18** (all method rows) | **0** |
| `normative_reference` as unstructured string | 58 rows (parent+arch) | 0 (array of `{source, reference}` objects) |
| Schema/type validation | not enforced (v1 validator checked presence only) | **0 errors** under the hardened contract |
| Mutation self-test | n/a | **9/9 mutants rejected** (single-char path; string consumers; unknown enum; empty evidence; duplicate row; O3 change without amendment; string normative_reference; string blockers; single-char evidence fragment) |
| Pre-repair artifact regression | passed v1 | **rejected** (not v2 envelope; 58 char-split rows detected; row validation fails) |

Root cause (fixed, not patched): the v1 integrator iterated free-text string fields character-by-character. The v2 pipeline (`scripts/ontology_review/normalize_sources.py` → `consolidate_review.py` → `validate_review.py`) normalizes before integration, refuses non-canonical input, and rejects malformed structured data at validation. Canonical schema: `de4sdv-ontology-review-integrated/v2` (envelope with `schema`, `source_revision`, `generated_from`, `row_count`, `rows`).

---

## 3. O3 impact

`No O3 semantic amendment required.`

- The frozen 13 identities remain marked `o3_protected: true`; all carry `migration_class: CURRENT_O3_13`; dispositions and meanings unchanged; validator enforces that any substantive change to them without a complete `o3_amendment` record is an error.
- The architecture recheck touched no frozen semantic: `DerivesFromNeed` (the K-pair witness carrier) was confirmed as representation/application-semantic without changing the frozen pair; `VerificationCase`-adjacent method identities (`VerificationMethod`) are outside the 13 and unchanged in meaning.
- O3 evidence remains the retained exact-revision report (`13/13 EQUIVALENT`, K-pair 5/5) — untouched.

---

## 4. Semantic delta from the previous package

**A. Data/integration corrections (no semantic content):** canonical normalization of `consumers` (string → structured `{path, symbol_or_surface, role}`), `evidence` (string → typed `{type, path_or_reference, finding}`), `normative_reference` (string → `{source, reference}[]`), `open_decisions` (string → array), `blockers` (singular → array); v2 envelope; hardened validator with self-tests; regenerated matrix; repair records (the pre-repair corruption scan and the v1 artifact were kept in the reviewer's working archive — audit-only, not committed; conclusions preserved in §2).

**B. Substantive semantic changes: none.** All 93 dispositions, classifications, definitions, authority targets, migration classes, blockers and O3 statuses are identical to package revision 1. The architecture recheck's evidence additions are anchor strengthening only (documented per row in `architecture-decisions-v2.json` under `recheck.evidence_updates`).

---

## 5. Target ontology effect

Unchanged from revision 1: **90 retained identities** (58 classes, 32 relationships) = 93 − 1 removed (`derivesNeedFromConcern`) − 2 merged (`validatesFitnessForUse`, `IncrementTraceabilityShell`); category counts unchanged (12 native, 9 native-grounded, 1 accepted-library, 50 application-semantic, 10 external, 10 vocabulary-only, 2 gated/blocked). Removal/merge/redesign lists, O4 migration waves and blockers/dependencies are unchanged; no wave content was added or re-scoped by this revision.

---

## 6. Test/validation evidence (exact)

- `python -m pytest -q -p no:cacheprovider` (23 targeted review-relevant test files) in the pinned snapshot: **1029 passed in 78.55s** (exit 0) — re-executed this revision.
- `python scripts/generate_semantic_authority_inventory.py --check`: **passed** (exit 0).
- `python scripts/generate_o3_equivalence_scope.py --check`: **passed** (exit 0).
- `python scripts/ontology_review/normalize_sources.py <working-archive>`: 34 + 18 + 17 rows canonicalized; shape assertions passed (repair-stage provenance).
- `python scripts/ontology_review/consolidate_review.py`: 93 rows (59/34), 13 O3-protected, revision `bc2b65ab…`; strict input contract passed.
- `python scripts/ontology_review/validate_review.py`: **0 errors**; mutation self-test **9/9 rejected**; wired into `scripts/check_repo.py`.
- `python scripts/ontology_review/generate_review_matrix.py`: REVIEW-matrix.md regenerated, 93 data rows.
- Regeneration determinism: `consolidate_review.py` and `generate_review_matrix.py` reproduce the governed artifacts **byte-for-byte** (diff-verified at integration).
- Repository untouched: no commits, no working-tree changes in the snapshot (read-only review).

---

## 7. Cross-domain consistency check (review domains)

Ten cross-slice pairs were checked (architecture vs relationships vs method vs PLE vs O3): VerificationMethod ↔ usesVerificationMethod (consistent, both KEEP_NATIVE); EvidenceStatus ↔ hasEvidenceStatus (deliberate split: class keeps the adopted library vocabulary; the relationship's artifact-status link is REDESIGN); AcceptanceCriterion ↔ hasAcceptanceCriterion (consistent, both blocked on the criterion identity); EvidenceContract ↔ hasRelevantEvidenceContract (consistent, both BLOCKED on the same discriminator); Scenario/ValidationScenario ↔ validatedBy/validatesFitnessForUse redesigns (consistent); DerivesFromNeed ↔ the O3 K pair (consistent, one witness); Gap ↔ Missing/BlockedRealizationRecord (consistent, kept distinct); RegulatoryConstraint ↔ constrainedBy redesign + R003 enforcement (consistent); Concern ↔ c4 retirement of `derivesNeedFromConcern` (consistent); Viewpoint/View/Stakeholder ↔ increment-level vocabulary predicates (consistent). **0 contradictions found; 2 deliberate splits documented (both above).** No competing semantic authorities were created.

---

## 8. Final decision question

**Is this repaired review package now sufficiently complete, internally consistent, normatively supported, and machine-validatable to become the governed target input for DE4SDV's remaining O4 ontology-authority migration?**

**YES — with the following explicit remaining blockers carried inside the package (none of which is an internal inconsistency):**

1. Open owner decisions: the 15 items in REVIEW.md §Open decisions (five predicate renames + deprecation policy; regulatory-provenance semantics; claim/argument design; status-dimension split; umbrella definition homes + constituent widening; AcceptanceCriterion promotion; MethodEvaluationScope exclusions; trace-chain redesign name; PLE configurator position; canonical-architecture source; SAF disposition; ADR 0009 status wording; live-API anchor read-back).
2. Blocked closures: `hasRelevantEvidenceContract`/`EvidenceContract` (identity discriminator), `hasAcceptanceCriterion` (criterion lineage), `instantiatesCanonicalArchitecture` (canonical source), PLE selection predicates (PLE-Q/S/A gates), `allocatedTo`/`deployedTo` typed-end proofs.
3. Verification follow-up: live-API read-back of the 22/34 implied verification anchors before any claim stronger than the export-level equivalence.

These are decision/evidence gates owned by the project — the package identifies each, with the required evidence, and validates mechanically; it is not blocked by any remaining defect in the review data itself.