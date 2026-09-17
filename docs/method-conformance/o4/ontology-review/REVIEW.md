# DE4SDV Ontology & Semantic-Authority Review — 2026-09-17

**Independent review, classification, and disposition of the complete DE4SDV ontology inventory (59 classes + 34 relationships = 93 identities).**

- **Snapshot:** `de4sdv/DE4SDV` `main` @ `bc2b65abb623e50032f177d566e34e1a41c09f34` (read-only review). No repository, model, YAML, projection, profile, runtime, or evidence files were modified.
- **Baseline verification at the pinned revision:** targeted suite **1,029 passed** (re-executed at package integration; inventory generation `--check` and O3 scope `--check` both green; validator output in `validation-report.json`); retained exact-revision privileged artifact `full-model-api-ingestion-bc2b65a…` (run 35172409514) shows O3 **13/13 EQUIVALENT**, K-pair 5/5 witnesses, verification grounding 22 defs / 34 usages.
- **Normative sources actually used:** attached **SysML v2 formal/2026-03-02** (current) and — because the attached KerML is **1.0 Beta 1 (ptc/2023-06-01), superseded by the repo-pinned 20250201 library generation** — the formal **KerML 1.0 formal/2026-03-01** downloaded and hash-verified during this review (see Deliverable N: `normative-crosscut.md` §1 for hashes and the citation-drift hazard).
- **Data files:** `integrated-review.json` (93 records, schema `de4sdv-ontology-review-integrated/v2`, validator `scripts/ontology_review/validate_review.py` → 0 errors, 9/9 mutation self-tests rejected), `REVIEW-matrix.md` (Deliverable 2, 93 rows, regenerated from the canonical envelope), canonical decision inputs under `decisions/` (`parent-decisions-v2.json`, `method-decisions-v2.json`, `ple-decisions-v2.json`, `architecture-decisions-v2.json`, `base-records.json`), `normative-crosscut.md`, `RECHECK-REPORT.md`. Pre-repair/audit working files are not committed (see `RECHECK-REPORT.md` §2).

---

## Package revision 2 — integration repair & architecture recheck (2026-09-17)

**Trigger.** An independent QA pass found structured-data corruption in the package-revision-1 integration artifact: **58 rows carried character-split `semantic_consumers`** (free-text string fields had been iterated character-by-character — e.g. MethodPhase held `"d","e","4","s",…`), **3 rows carried character-split evidence** (Stakeholder, EvidenceContract, EvidenceStatus), and **18 method rows carried `open_decisions` as a bare string**. Row-count checks had not caught it; row-count completeness alone is not validity.

**Root cause.** The v1 integrator consumed legacy free-text fields (`consumers`, `decisions`, `evidence`) without type discipline, and no stage rejected string-typed array fields.

**Repair (integration-only; no semantic change).** A canonical normalization stage (`scripts/ontology_review/normalize_sources.py`) converts every legacy decision file into the strict machine-readable schema **before** integration; the v2 integrator (`scripts/ontology_review/consolidate_review.py`) refuses non-canonical input (raises on type violations); the hardened validator (`scripts/ontology_review/validate_review.py`) enforces inventory (93/59/34, exact identity set, no duplicates), enum, type, path-sanity, O3-integrity and completeness contracts, carries a **9-case mutation self-test** (all planted defects rejected), and a regression path that rejects the pre-repair artifact where the audit copy is present. Before: 58 + 3 + 18 malformed rows → after: **0**. All derived deliverables were regenerated from the canonical envelope and reproduce byte-for-byte. Evidence: `validation-report.json`; the pre-repair corruption scan is an audit working artifact summarized in `RECHECK-REPORT.md` §2.

**Architecture recheck.** The 24 architecture identities were independently re-verified against repository evidence at the pinned revision (ontology rows, governed declarations, native metadata usage, normative clauses, runtime consumers, ADR/R003 enforcement, tests). Result: **24/24 decisions confirmed unchanged; 0 substantive changes**; several evidence anchors strengthened (native `@VerificationMethod{kind=…}` annotations confirmed across ≥5 slices; the in-model statement "(SysML v2 provides no native validation-case keyword)" recorded; the eight lineage-less EvidenceContract definitions enumerated; the ArgumentationAssurance concern/viewpoint frames and claim/argument/counterclaim layer confirmed; umbrella classes verified as YAML-only with no model home). Full record: `RECHECK-REPORT.md`.

**O3 status after recheck: `No O3 semantic amendment required.`** (unchanged; the 13 frozen identities remain CURRENT_O3_13 with intact meanings and evidence).

---

## Deliverable 1 — Executive assessment

**Overall semantic coherence: moderate but directionally right, with three structural problems.** The O1–K–O3 program has already produced genuinely strong machinery: validated kernel bindings, fail-closed domain enforcement, blocked-vs-absence distinction, and 13 identities with same-revision runtime-equivalence evidence. The remaining 80 identities are older, thinner, and — measured against the review principles — the ontology is still roughly half vocabulary-catalogue rather than semantics.

**Major modeling problems (ranked):**

1. **29 of 34 relationships have no YAML definition text** (only the K pair, `specifiesFunction`, `hasRelevantArchitecture`, `instantiatesCanonicalArchitecture` carry explicit definitions). Domain/range rows without definitions are signatures, not semantics; several also misname their claim (below).
2. **Name/claim mismatches in the executable relationship layer.** `realizedBy` names realization but its only witness is allocation (c5 already recorded rename-required; this review agrees and proposes `allocatedToArchitecture`). `specifiesFunction` names specification but proves only relevance (proposed `hasRelevantFunction`). `validatedBy` names an outcome but is at most a planning relation (proposed `hasValidationScenario`); `validatesFitnessForUse` further implies success with no witness at all.
3. **Evidence/assurance semantics straddle the model/external boundary.** `hasEvidenceStatus` maps external artifact lifecycle onto the library `VVStatus` enum (production/maturity ≠ verification verdict ≠ acceptance); `supportedByEvidence` has no witness; `capturedInBaseline` has no manifest authority. All need explicit external-boundary contracts, not traversal.
4. **The method trace chain is the wrong shape.** `RequiredTraceChain` encodes a universal fixed chain whose first link (`concern → need`) conflicts with the accepted c4 retirement of `derivesNeedFromConcern`, and whose string-typed `TraceLink` endpoints cannot resolve to elements — both confirmed against the c4/c5 records.
5. **Umbrella classes have no model-resident definition home** (`ArchitectureElement`, `Function`, `LogicalElement`, `PhysicalElement`, `Interface`): their c5 executable filters are real, but the classes themselves are still YAML declarations.
6. **Governance inconsistency:** ADR 0009 header says "Proposed" while the amendment it contains is treated as adopted across O1/c1–c5 and the model (re-exported `VVStatus` import). Observed adoption is real; the status wording is wrong.

**Major duplication / excessive DE4SDV-specific semantics:** no wholesale duplication of native semantics was found in the retained set — the O1 reclassification passes (Scenario/ValidationScenario/EvidenceContract already moved off `native-sysml`) hold up under this review. The duplication risk is concentrated in (a) `validatesFitnessForUse` as an independent identity duplicating a not-yet-designed `validatedBy` fact, (b) `IncrementTraceabilityShell` as prose-only vocabulary duplicating the trace-chain concepts it references, and (c) `derivesNeedFromConcern`, retained in YAML three batches after its reviewed retirement.

**Missing DE4SDV-specific semantics:** the Need/Requirement lineage discriminator, MemberProduct restrictions, and the derivation-connection provenance claim are correctly application-semantic and load-bearing — they survive. What is missing is *model-resident* authority for them: lineage exclusions live in traversal code, the exclusions of `MethodEvaluationScope` live in runtime input, and acceptance criteria live in per-slice definitions with no shared lineage.

**Native reuse opportunities (taken):** `VerificationCase`, `Concern`, `Viewpoint`, `View`, `VerificationMethod`, `VariationPoint`, `Variant` classify `NATIVE_EXPLICIT` — the identity survives only as stable projection vocabulary over the native construct. `hasSubject`, `verifiedBy`, `hasRelevantArchitecture`, `allocatedTo`, `specifiesFunction` classify `NATIVE_GROUNDED_DE4SDV` — native witness necessary, DE4SDV restrictions add the claim.

**Accepted-library reuse:** exactly one entry classifies `ACCEPTED_LIBRARY` on class level (`EvidenceStatus` via pinned ODE4HERA `VVStatus`); `usesVerificationMethod` and `VerificationMethod` are normative-SysML metadata, and the "accepted-library-grounded" labels O1 gave them conflate normative library constructs with the ODE4HERA attribute mapping — corrected here. PLEML remains pinned-not-adopted and is **not** counted anywhere as accepted.

**Entries that should disappear from the active ontology:** `derivesNeedFromConcern` (REMOVE; historical c4 evidence untouched). Merged: `validatesFitnessForUse` → redesigned `validatedBy`; `IncrementTraceabilityShell` → redesigned trace expectation.

**Blocked areas:** `hasRelevantEvidenceContract` (no machine-resolvable EvidenceContract identity), `instantiatesCanonicalArchitecture` (canonical-architecture source undefined), `EvidenceContract` role identity, plus the four blocked PLE relationships — each blocked by a named, reviewable gate, not by missing code.

**Findings affecting the O3 13:** none requires semantic amendment (Deliverable 6). One classification correction is recorded against the *inventory descriptions* of two O3 rows (`hasSubject`, `verifiedBy`), which is not a semantic change and touches no frozen meaning, query result, or projection artifact.

---

## Deliverable 2 — Complete 93-entry matrix

See **`REVIEW-matrix.md`** (93 rows, one per identity, regenerated from the validated v2 envelope; data-row count verified = 93). Columns: Identity, Kind, Current authority, SysML/KerML classification, Normative semantic source, DE4SDV semantic delta, Runtime support, O3, Target disposition, Target authority, Migration class, Blocker. Full per-row fields (structured consumers, typed evidence anchors, implicit semantics, targets, change summaries) are in `integrated-review.json` (schema `de4sdv-ontology-review-integrated/v2`).

---

## Deliverable 3 — Detailed per-entry findings (contested / changed / redesign / removal)

Condensed; full records in the four decision files. Format: **finding — decision — why.**

1. **`realizedBy` — REDESIGN → `allocatedToArchitecture`.** O1 c5 already measured: every requirement-sourced allocation is Requirement→Function (10/0/0/0 layer split), zero source-end hops serialize through the configured source property. This review confirms classification as `REPRESENTATION_ONLY` for the *realization* claim (allocation is connection-like, binary-by-norm, "responsible for realizing some or all of the source's intent" — not requirement satisfaction; SysML §7.15.2). Name collision with the existing Function→LogicalElement `allocatedTo` makes that proposed name unusable; `allocatedToArchitecture` preserves the frozen signature. End resolution must move to EndFeatureMembership/ReferenceSubsetting mechanics in the profile.
2. **`specifiesFunction` — REDESIGN → `hasRelevantFunction`.** Dependency is "entirely a model-level Relationship, without instance-level semantics" (KerML §8.3.2.2.2), so the 16/15-hop witness proves relevance only — exactly as the YAML definition says, and the name doesn't. Not merged into `hasRelevantArchitecture`: the two query opposite dependency directions; disjoint by construction, not two navigations of one fact.
3. **`validatedBy` / `validatesFitnessForUse` — REDESIGN + MERGE → `hasValidationScenario`.** No native validation-case construct exists (§8.3.24 defines verification only); fitness-for-use is DE4SDV application meaning. The current pair has zero definitions, zero runtime support, and a direction/outcome mismatch; one fact authority with inverse navigation is the survivable design. A future outcome relation must be separately governed evidence.
4. **`derivesNeedFromConcern` — REMOVE.** c4's three-claim decomposition (origin provenance / native framing / weak addressing) is sound and independent; zero runtime/MCP/viewer consumers; native framing would convert concerns into required constraints of needs, which DE4SDV does not want. Remove only the future active row; historical c4 evidence is immutable.
5. **`constrainedBy` — REDESIGN → `hasRegulatorySource`.** YAML says provenance; native required-constraint semantics (§8.4.17) would silently claim satisfaction conditions. Decide explicitly; recommended: weak regulatory-source reference, external regulation authority.
6. **`deployedTo` — REDESIGN → `logicalAllocatedToPhysical`.** The modeled layer pair is logical→physical; "deployment" implies installed/running software that no allocation witness establishes. A real software→execution-node deployment predicate would be a new identity, not a reinterpretation.
7. **`allocatedTo` — KEEP_DE4SDV_APPLICATION_SEMANTIC.** Native allocation genuinely grounds Function→LogicalElement layer allocation; blocked only on typed-end proof and closure. Do not reuse the name for the requirement relation (finding 1).
8. **`hasEvidenceStatus` — REDESIGN.** The class keeps `ACCEPTED_LIBRARY` (VVStatus is real, pinned, adopted); the *relationship* overclaims: artifact production/maturity status and acceptance decisions are orthogonal to a requirement-verification verdict. Split the dimensions; keep VVStatus for requirement status only.
9. **`supportedByEvidence` — KEEP_DE4SDV_APPLICATION_SEMANTIC (new semantics needed).** Citation-of-support-in-an-argument is a distinct fact from `hasEvidence` (case associates evidence). AssertConstraintUsage is not an argument metaclass; the claim design is the open O1 gate.
10. **`capturedInBaseline` — KEEP_EXTERNAL_REFERENCE.** KerML Membership is containment, not immutable baseline inclusion; the manifest (Git/CM) is the authority; the model carries typed references and the non-claim boundary.
11. **`hasRelevantEvidenceContract` — BLOCKED (confirmed).** The c5 fail-closed gate is correct: 8 per-slice evidence-contract defs share no lineage, no kernel binding, and native verification membership also admits acceptance-criterion role (measured). Reopening requires a reviewed lineage contract in the model, then O2, then O3.
12. **`TraceLink` + `RequiredTraceChain` — joint REDESIGN.** String endpoints cannot resolve to elements; the fixed universal chain conflicts with c4 (no concern→need) and the plan's RFLP invariant. Replacement: per-increment reviewed trace expectation with gap records, expressed over native relationships. The two published shell usages migrate with it (source edit acknowledged, not executed here).
13. **`IncrementTraceabilityShell` — MERGE** into that trace expectation (doc-only; two slice usages).
14. **`MethodEvaluationScope` — REDESIGN (structural gap).** Definition claims explicit exclusions with rationale; model body carries only incrementId/subjectType; exclusions live in runtime input (implementation evidence, not parity). O2/O3 correctly exclude it today; close the structural gap before admission.
15. **`usesVerificationMethod` — KEEP_NATIVE (corrected from accepted-library).** VerificationMethod metadata + VerificationMethodKind are normative (§§7.26.3, 9.2.17.2.6–7); the relationship is a projection of metadata, not a second fact; no execution implication.
16. **`VerificationMethod` (class) — KEEP_NATIVE (corrected from accepted-library).** Same distinction: ODE4HERA `verificationMethod` attribute is the application mapping; the construct is native.
17. **`hasSubject` / `verifiedBy` (O3 rows) — classification correction only.** O1 records `hasSubject` target `de4sdv-application-semantic` (correct) but `verifiedBy` target `native-sysml`, while c5 later enforced the identical kind of Requirement-lineage source restriction on `verifiedBy` that c3 used to justify `hasSubject`'s application-semantic target. The frozen meanings and behaviors are unaffected; this is an inventory-description inconsistency, recorded as such, no O3 amendment.
18. **PLE relationships (`specifiesFeature`, `specifiesCommonCapability`, `appliesToMemberProduct`, `selectsFeature`, `includesCommonCapability`, `selectsVariant`, `FeatureConfiguration`) — external/boundary, not model semantics, until PLE-Q/S/A gates decide.** Native variation/variant (§7.6.7) carries structural choice only; feature-model algebra and configurator authority stay in the governed external catalogues (ADR 0006 position preserved). `VariationPoint`/`Variant` map to native constructs (`KEEP_NATIVE`, already represented); `variesAt` is native-grounded (feature-typing witness).
19. **`instantiatesCanonicalArchitecture` — KEEP_CONDITIONAL/BLOCKED.** No governed "canonical architecture" source exists to instantiate; gate on the PLE architecture-definition decision.
20. **Umbrella classes — keep, definition-home decision required** (ArchitectureElement/Function/LogicalElement/PhysicalElement; Interface stays vocabulary-only pending a reviewed widening of the executable filter).
21. **PLE parity deltas (from the dedicated PLE worker, verified anchors):** (a) the YAML `disjointWith` axiom between Feature and CommonCapability has **no model counterpart** — an ontology axiom with no model-resident witness; close it in the model or explicitly drop the axiom at parity (open decision 14). (b) `appliesToMemberProduct` is genuinely consumed as a runtime **claim-boundary exclusion** (`projection_o22.py:291`, `projection_o23.py:544`, `test_o1_c3_subject_grounding.py:1243`) — PLE selection relations must never collapse into `hasSubject`; the c3 MemberProduct exclusion and this consumer are two sides of the same boundary. (c) real variation/variant witnesses exist in governed slices (`vehicle_sensing_boundary.sysml:203`, `sdv_platform_stack.sysml:56`, `aebs_increment_framing.sysml:95`), supporting `KEEP_NATIVE` for VariationPoint/Variant as already-complete structural mappings. (d) `impact.py:145` labels hops "MemberProduct" as a display string only — labeled provenance, not a semantic assertion (flagged, no change).

---

## Deliverable 4 — Proposed target ontology

**Counts after adoption (identities, not runtime support):**

| Category | Count |
|---|---|
| Total identities retained | **90** (93 − 1 removed − 2 merged) |
| Classes | 58 (59 − `IncrementTraceabilityShell` merged; `validatesFitnessForUse` was a relationship) |
| Relationships | 32 (34 − `derivesNeedFromConcern` removed − `validatesFitnessForUse` merged) |
| Native SysML/KerML (NATIVE_EXPLICIT + identity-as-projection) | 12 |
| Native-grounded DE4SDV | 9 |
| Accepted-library-grounded | 1 (EvidenceStatus class authority; VVStatus) |
| DE4SDV application semantics (incl. representation-only carriers kept as application classes) | 50 |
| External references (external authority, model = typed reference) | 10 |
| Vocabulary-only | 10 |
| Conditional (gated) | 1 (+1 BLOCKED relationship +3 BLOCKED migrations) |
| Removed | 1 (`derivesNeedFromConcern`) |
| Merged | 2 (`validatesFitnessForUse`→`hasValidationScenario` design, `IncrementTraceabilityShell`→trace expectation) |
| Redesigned (renamed, same slot) | 9 (`realizedBy`, `specifiesFunction`, `validatedBy`, `constrainedBy`, `deployedTo`, `hasEvidenceStatus`, `TraceLink`, `RequiredTraceChain`, `MethodEvaluationScope`) |

**Ontology vocabulary vs runtime-query support (explicit):** post-migration runtime-queryable predicates remain exactly the current five O3-proven ones plus, per wave below, `allocatedTo`-family once typed-end proofs exist; `hasEvidence`/`capturedInBaseline`/`hasEvidenceStatus`/PLE selection predicates stay **external-boundary** (no traversal by design, not by omission); ~10 stay vocabulary-only. Runtime support is a per-identity property recorded in the matrix; nothing in the target architecture lets a traversal existence claim stand in for semantics.

---

## Deliverable 5 — Native/implicit semantic map

- **Native explicit (12):** VerificationCase, Concern, Viewpoint, View, VerificationMethod, VariationPoint, Variant, SignalMappingDisposition\*, LogicalToSoftwareSignalMappingRecord\*, SystemToSoftwareSignalMappingCandidate\*, IncrementSize\*, DerivesFromNeed-as-declaration (native *connection* semantics; the *provenance claim* is DE4SDV — see \* note: the three signal enums and IncrementSize are native *enumeration constructs* whose value sets are DE4SDV vocabulary).
- **Native implicit (normative implied semantics actually consumed):** VerificationCase library anchoring (checkVerificationCaseSpecialization/UsageSpecialization → implied Subclassification/Subsetting; 22/34 grounding witnesses); verifiedRequirement derivation from RVMs; SubjectMembership subject-parameter structure; ReferenceSubsetting shadow bridge; specialization/typing transitivity behind all lineage gates; variation-is-abstract and variant-kind constraints (PLE structural layer). All are listed per-row in `integrated-review.json` (`implicit_detail`) with the API-observability caveat: the verification anchors are **export-implied external references, not imported first-class API symbols** — do not restate them as live-API observables.
- **Native-grounded DE4SDV (9):** hasSubject, verifiedBy, hasRelevantArchitecture, specifiesFunction, allocatedTo, variesAt, hasAcceptanceCriterion (objective-structure witness), DerivesFromNeed pair (typed ends witness), plus DerivesFromNeed class.
- **Accepted library (1):** EvidenceStatus (VVStatus).
- **Representation-only (48):** all O2.1 method-schema records, all umbrella classes, Need/Requirement/ProblemStatement/RegulatoryConstraint/AcceptanceCriterion/EvidenceContract/Assumption/Gap/Scenario/ValidationScenario/Stakeholder/AssuranceClaim/Baseline/ArchitectureDecisionRecord, the PLE classes, and the increment-shell/trace vocabulary.
- **No-native-fit (23):** the increment-association predicates, PLE selection/configurator predicates, validation pair, evidence/baseline/status relations, TraceLink — each carries a disposition (application semantic, external boundary, redesign, merge, or remove), never an invented native meaning.

---

## Deliverable 6 — O3-protected findings

`No O3 semantic amendment required.`

All 13 identities were assessed against the normative sources; their frozen meanings, directions, and claim boundaries hold. Two **non-semantic** records:

1. `verifiedBy`/`hasSubject` authority-target descriptions are mutually inconsistent under c5's source-domain enforcement (finding 17 above) — inventory-prose correction in a future batch, not a meaning change.
2. The O3 grounding evidence proves export-implied library anchoring; a live-API read-back of the 22/34 anchors remains an open verification item before any claim stronger than "equivalent at the pinned revision."

---

## Deliverable 7 — Removal / deprecation / merge list (do NOT simply migrate)

- **REMOVE:** `derivesNeedFromConcern` — retired by reviewed c4 decomposition; no required meaning, no consumer; native framing would add an unwanted required-constraint claim.
- **MERGE:** `validatesFitnessForUse` → the redesigned `validatedBy` fact (one authority, inverse navigation; its name asserts an outcome nothing witnesses). `IncrementTraceabilityShell` → the redesigned per-increment trace expectation (doc-only duplicate of the concepts it names; two slice usages migrate).
- **REDESIGN-not-migrate (renames with explicit semantic migration):** `realizedBy`→`allocatedToArchitecture`, `specifiesFunction`→`hasRelevantFunction`, `validatedBy`→`hasValidationScenario`, `constrainedBy`→`hasRegulatorySource`, `deployedTo`→`logicalAllocatedToPhysical`, `hasEvidenceStatus`→split status dimensions, `TraceLink`/`RequiredTraceChain`→native-relationship trace expectation, `MethodEvaluationScope`→exclusions-carried scope.
- **Migrate-with-changed-authority:** `usesVerificationMethod`/`VerificationMethod` (accepted-library → normative-SysML label), `EvidenceStatus` (keep library), PLE selection predicates (vocabulary → external-boundary contracts).

---

## Deliverable 8 — O4 migration burn-down (semantic waves)

**Wave 1 — Correction batch (no model changes):** inventory-description corrections from this review (verifiedBy/hasSubject target consistency; usesVerificationMethod/VerificationMethod authority labels; IncrementSize demotion note; ADR 0009 status wording). *Exit:* regenerated artifacts bound by the two-commit pattern; CI green at exact head.

**Wave 2 — Definitions parity (26 MODEL_AUTHORITY_PARITY rows):** move the 29 missing relationship definitions + class definition-text parity into the model; no semantic changes; en route fix `MethodEvaluationScope` structural exclusions and the umbrella-class definition homes. *Exit:* normalized-exact or reviewed-equivalent text for every retained identity; O2 admission unblocked for these rows.

**Wave 3 — Native/library projection rows (12 NATIVE + 1 ACCEPTED_LIBRARY + variesAt):** projection/profile entries over already-native constructs (VerificationCase-adjacent, Concern/Viewpoint/View, VerificationMethod metadata, VariationPoint/Variant); runtime stays vocabulary for all but already-proven predicates. *Exit:* projection rows generated from model authority; same-revision equivalence evidence per identity where traversal is claimed.

**Wave 4 — External-boundary contracts (10 EXTERNAL_BOUNDARY):** hasEvidence, capturedInBaseline, hasEvidenceStatus (split), PLE selection predicates, FeatureConfiguration, appliesToMemberProduct, selectsVariant, ArchitectureDecisionRecord, Baseline, EvidenceArtifact: write the governed external-authority contracts (evidence system, CM/baseline manifest, feature catalogue, ADR corpus) and the typed-reference schemas. *Exit:* contract docs + profile entries; no traversal; blocked-state surfaced wherever queried.

**Wave 5 — Relationship redesigns (REQUIRES_SEMANTIC_MIGRATION):** the five renames + trace-chain redesign + supportedByEvidence/claim design. Each: owner-approved name/signature → model vocabulary → O2 projection → exact-revision equivalence evidence before any traversal claim; compatibility aliases/deprecation intervals per predicate-change safeguards. *Exit:* old names retired through the governed transition; no signature silently changed.

**Wave 6 — Gated/blocked closures (BLOCKED + KEEP_CONDITIONAL):** hasRelevantEvidenceContract + EvidenceContract lineage contract; hasAcceptanceCriterion criterion-role promotion; allocatedTo typed-end proof; instantiatesCanonicalArchitecture canonical-architecture decision; PLE-Q/S/A configurator authority. *Exit:* each blocker resolved by the named decision/evidence, then normal wave 2–5 treatment.

Dependency rule: wave 2 unblocks 3/5; wave 3 is independent of 4; wave 6 items re-enter earlier waves when unblocked; O3-protected rows stay outside all waves (frozen).

---

## Deliverable 9 — Dependency graph (identity → requirement)

- `verifiedBy`, `hasSubject`, `derivesRequirementFromNeed`/`derivedRequirementsOfNeed`, `hasRelevantArchitecture`, `specifiesFunction` → **Need + Requirement lineages** (validated kernel bindings) and → **DerivesFromNeed connection def** (K pair witness).
- `hasRelevantArchitecture`, `specifiesFunction`, `allocatedTo`, `deployedTo` → **umbrella classes** (ArchitectureElement/Function/LogicalElement/PhysicalElement) — definition-home decision gates their projection rows.
- `hasAcceptanceCriterion` → **AcceptanceCriterion lineage promotion**; `hasRelevantEvidenceContract` → **EvidenceContract lineage contract** (measured counterexample: acceptance-criterion role).
- `supportedByEvidence` → **AssuranceClaim claim design**; both → external evidence authority.
- `hasEvidence`, `capturedInBaseline`, `hasEvidenceStatus` → **external evidence/CM manifest authority** (T/E design).
- `specifiesFeature`/`selectsFeature`/`includesCommonCapability`/`appliesToMemberProduct`/`FeatureConfiguration`/`selectsVariant` → **PLE-Q/S/A gates** (external configurator authority; native variation covers structural choice only).
- `instantiatesCanonicalArchitecture` → **canonical-architecture source decision**.
- `TraceLink`/`RequiredTraceChain`/`IncrementTraceabilityShell` → **c4 disposition + RFLP invariant** (mutual redesign).
- Runtime support for every claimed-queryable predicate → **API Representation Profile closure + exact-revision equivalence evidence** (per the O3 pattern); export-implied anchors ≠ live-API observables.

---

## Deliverable 10 — Open decisions (human/domain-owner)

1. Approve the five renames (`allocatedToArchitecture`, `hasRelevantFunction`, `hasValidationScenario`, `hasRegulatorySource`, `logicalAllocatedToPhysical`) and the deprecation/alias policy per predicate.
2. `constrainedBy`: provenance-reference vs normative required-constraint semantics (recommend the former).
3. `supportedByEvidence`/AssuranceClaim: claim/argument/counterclaim model; cited vs assessed-sufficient support.
4. EvidenceStatus split: approve the orthogonal status dimensions (production/maturity vs verification verdict vs acceptance) and their authorities.
5. Umbrella-class definition homes (method-context package?) and whether `hasRelevantArchitecture`'s executable filter widens to interface/behavior constituents.
6. AcceptanceCriterion kernel promotion vs retained slice mapping.
7. `MethodEvaluationScope` exclusions: model-resident representation shape.
8. Trace-chain redesign: approve per-increment trace expectation replacing the fixed universal chain (touches published slices).
9. PLE configurator authority: keep external catalogue position (ADR 0006) or model selection algebra after PLE-Q/S/A.
10. Canonical architecture source for `instantiatesCanonicalArchitecture`.
11. SAF role-def adoption/publication disposition (unrecorded provenance flag).
12. ADR 0009 status header correction (Proposed → adopted-amendment wording).
13. Live-API read-back of the 22/34 implied verification anchors before any stronger-than-export claim.
14. Feature/CommonCapability `disjointWith` axiom: close it model-resident (typed constraint or reviewed declaration) or explicitly drop the axiom from the ontology at parity — it currently has no model witness.
15. Renaming successor for the trace-chain redesign: confirm the per-increment trace-expectation identity name before Wave 5 (used by the two slice usages and the merged shell).

---

## Final questions (§19)

**1. What would the final ontology contain?** 90 identities (58 classes, 32 relationships): 12 native + 9 native-grounded + 1 accepted-library + 50 application-semantic + 10 external references + 10 vocabulary-only (+2 gated), every one with a model-resident or externally-governed definition and a recorded target authority. Names match claims; external facts stay external; no shadow ontology in Python/YAML.

**2. Survive unchanged?** The 13 O3 identities (meanings frozen; two inventory-description corrections recorded separately), plus as identities: Concern, Viewpoint, View, VerificationMethod, VariationPoint, Variant, Stakeholder, Need, Requirement, ProblemStatement, RegulatoryConstraint, Assumption, Gap, Scenario, ValidationScenario, EvidenceContract, EvidenceArtifact, EvidenceStatus, Baseline, ArchitectureDecisionRecord, the O2.1 schema records, SignalMappingDisposition, the two signal-mapping records, SystemLayer, Missing/BlockedRealizationRecord, ProductLine/MemberProduct/Feature/ProductLineCharacteristic/CommonCapability/DeferredProductLineScope, `addressesConcern`, `hasStakeholder`, `selectedViewpoint`, `producesView`, `recordsAssumption`, `recordsGap`, `allocatedTo`, `hasEvidence`, `capturedInBaseline`, `DerivesFromNeed`.

**3. Survive with different semantic authority?** `usesVerificationMethod` + `VerificationMethod` (accepted-library → normative-SysML label), `EvidenceStatus` (relationship dimension split), PLE selection predicates (vocabulary → external-boundary contracts), umbrella classes (YAML → model-resident homes), `MethodEvaluationScope` (runtime-input exclusions → model-carried), `TraceLink`/`RequiredTraceChain` (string chain → native-relationship expectation).

**4. Merged / redesigned / deprecated / removed?** Removed: `derivesNeedFromConcern`. Merged: `validatesFitnessForUse`, `IncrementTraceabilityShell`. Redesigned (renamed): `realizedBy`, `specifiesFunction`, `validatedBy`, `constrainedBy`, `deployedTo`, `hasEvidenceStatus`, `TraceLink`, `RequiredTraceChain`, `MethodEvaluationScope`.

**5. Truly native / implicitly native?** Explicit: VerificationCase, Concern, Viewpoint, View, VerificationMethod, VariationPoint, Variant (plus the native *constructs* behind the signal enums). Implicit (normative-implied, actually consumed): verification library anchoring (Subclassification/Subsetting), verifiedRequirement derivation from RVMs, SubjectMembership structure, ReferenceSubsetting bridge, lineage transitivity, variation-abstract/variant-kind constraints.

**6. Only LOOK native?** `realizedBy` (allocation ≠ realization), `specifiesFunction` (dependency ≠ specification), `validatedBy`/`validatesFitnessForUse` (no native validation construct), `hasEvidenceStatus` (verdict enum ≠ artifact lifecycle), `deployedTo` (allocation ≠ deployment), `capturedInBaseline` (membership ≠ baselining), `DerivesFromNeed`'s *provenance claim* (connection ≠ derivation), PLE selection predicates (variation ≠ feature-model configuration), `TraceLink` (item record ≠ relationship), `ArchitectureDecisionRecord`/`Baseline`/`EvidenceArtifact` (part defs ≠ external facts), and every umbrella class (part def ≠ the DE4SDV category).

**7. Genuinely require DE4SDV application semantics?** The Need/Requirement lineage discrimination, MemberProduct and architecture-constituent restrictions, derivation-provenance claim, method-contract schema and evaluation-scope semantics, bounded evidence/claim/acceptance boundaries, regulatory no-compliance boundary, product-line feature-vs-common-capability discipline, and the per-increment trace expectation — each with the native or external witness recorded, never replaced by it.

**8. O3 13 amendment needed?** No. `No O3 semantic amendment required.` Two inventory-description corrections and one evidence follow-up (live-API anchor read-back) recorded without touching frozen semantics.

**9. Exact work between current O3 state and O4 closure:** the six waves of Deliverable 8 — corrections, definitions parity (including the 29 missing relationship definitions and MethodEvaluationScope exclusions), native/library projection rows, external-boundary contracts, the five relationship redesigns + trace redesign, and the gated closures — each closed with the established two-commit binding, exact-revision equivalence evidence, and batch-guard conventions; O3-protected rows stay frozen throughout.

**10. What would still exist only in hand-authored YAML?** **None — for semantic authority.** After the proposed migration every retained identity's meaning is model-resident (DE4SDV application packages) or carried by the normative/accepted-library/external authority it names, with YAML reduced to generated parity artifacts and review metadata (never runtime authority). What still blocks reaching "None" today, in order: (a) the 29 missing relationship definitions, (b) the structural exclusions of MethodEvaluationScope, (c) the umbrella-class definition homes, (d) the five redesigns' successor vocabularies, (e) the EvidenceContract/AcceptanceCriterion lineage contracts. Until those six decision/evidence items close, a residue of definitions remains YAML-established; everything else is already on the model-authority path.

---

*Governed review artifacts: `integrated-review.json`, `REVIEW-matrix.md`, `RECHECK-REPORT.md`, `normative-crosscut.md`, `validation-report.json`, `decisions/` (canonical inputs), and the tooling under `scripts/ontology_review/` (validator → 0 errors, 9/9 mutation self-tests rejected). This package is migration governance only; it is never runtime semantic authority.*
