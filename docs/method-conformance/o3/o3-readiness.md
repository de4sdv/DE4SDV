# O3 readiness — semantic authority equivalence and cutover readiness

Date: 2026-09-15 · Plan: DE4SDV Unified Semantic Engineering Plan v1.2
(wins on conflict) + DE4SDV Method Conformance Plan · Base: permanent
`main` `1aabce06ee3a927f94e997e723331d3e2455e6a7` (PR #256 squash-merge).

**Status: planning and evidence only. This document is NOT activation
authority.** No runtime authority is switched, no authored YAML is retired
(that is O4), no support state is promoted, and no current exact-revision
API closure is claimed. O3 — the approved authority transition — begins only
after independent review of this package and the privileged evidence it
requires.

Machine-readable companion (generated, `--check`-validated):

- `docs/method-conformance/o3/o3-equivalence-scope.json`
  (`de4sdv.o3-equivalence-scope/v1`) — identity boundary, old and proposed
  new bundles, per-identity declared-semantics comparison, reviewed contract
  checks, support-preservation matrix, comparison-base revision.
- `de4sdv/semantic/o3_equivalence.py` — read-only extraction/comparison
  machinery (never imported by the runtime path; test-locked).
- `scripts/generate_o3_equivalence_scope.py` — generator/checker (writes
  exactly one repository path; write-guard enforced).

## 1. Current runtime-authority inventory (Task A)

Traced executable call paths (not grep alone): every non-test
`KernelContract.load(...)` call site, every `RevisionBinding.load(...)` /
`build_semantic_runtime(...)` / `SemanticTraversal(...)` construction, and
every direct authored-ontology read were inspected and classified.

### Production runtime (the O3 routing seam)

| file | entry point | authority data loaded | scope | meaning vs provenance | O3 scope | O4 relevance |
| --- | --- | --- | --- | --- | --- | --- |
| `de4sdv/semantic/runtime.py` | `build_semantic_runtime` | ontology YAML (via `KernelContract.load`), revision binding, kernel bindings | all 8 strategies + class identity | interprets (constructs the executing traversal) | YES — the single assembly seam | removes the authored-YAML read for migrated identities |
| `de4sdv/semantic/traversal.py` | `SemanticTraversal.traverse` + strategy methods | `contract.relationship_mapping`, `KernelBindingIndex` | 8 strategies incl. all 5 O3 relationships | interprets | YES | migrated-identity semantics must come from the bundle |
| `de4sdv/semantic/query.py` | `SemanticQueryService` (neighbors/impact/trace/coverage/model_status) | contract mappings, `blocked_predicates`, binder | executable predicates | interprets | YES | idem |
| `de4sdv/semantic/impact.py` | `ImpactService.impact` | `binder.bind_class("Requirement")`, traversal strategies | realizedBy, specifiesFunction, hasRelevantArchitecture, hasSubject, verifiedBy, hasRelevantEvidenceContract | interprets | YES | idem |
| `de4sdv/semantic/api_binding.py` | `OntologyApiBinder.bind_class` | `contract.class_mapping`, kernel bindings | file-mapped classes | identity only (provenance) | YES | idem |
| `de4sdv/semantic/kernel_binding_index.py` | `KernelBindingIndex` | revision binding `kernel_bindings` | all file-mapped classes | identity only | YES | retained (validated ingestion product) |
| `de4sdv/sysml_api/revisions.py` | `RevisionBinding.require_current` / `require_ontology` | binding + ontology identity | every query | enforcement (provenance) | YES | idem |
| `de4sdv/semantic/mcp_server.py` | `create_mcp_server` | via service only | tool surface | none (adapter) | YES (surface) | none |
| `tools/sysml_html_viewer/ask_model_semantic.py` | `_semantic_runtime()` (module-level `build_semantic_runtime`) | vía runtime + per-revision element snapshot | viewer ask surfaces | interprets (through the service) | YES | idem |
| `deployment/compose.yaml` + `.github/workflows/deploy-public-ask-viewer.yml` | ask-viewer service env (`DE4SDV_REVISION_BINDING`, `DE4SDV_SYSML_API_URL`, `DE4SDV_APP_GIT_SHA`) | binding artifact + ontology path | deployed authority selection | deployment authority selection | YES (activation/rollback selector lives here) | idem |

### Production ingestion / validation

| file | entry point | authority data | classification | O3 scope |
| --- | --- | --- | --- | --- |
| `scripts/import_sysml_api_baseline.py` | main (line ~74) `KernelContract.load` + `validate_ontology_bindings` | ontology classes, per-class validation | production ingestion (writes binding + kernel bindings) | YES (produces the identity the new bundle consumes) |
| `de4sdv/semantic/validation.py` | `validate_ontology_bindings` | `contract.classes`, `contract.mapping` | production ingestion validation | YES |
| `scripts/validate_full_model_semantic_queries.py` | binder+traversal construction (lines ~87–107) | ontology + kernel bindings | privileged validation | YES (must re-run at cutover revision) |
| `scripts/validate_product_line_scope_api.py` | main (line ~41) | ontology | privileged validation | YES |
| `scripts/validate_semantic_mcp.py` | traversal construction (lines ~629–634) | ontology + kernel bindings | privileged MCP validation | YES |
| `scripts/verify_pilot_readback.py` | main (`RevisionBinding.load`, candidate scope) | binding + kernel index + class names | pilot read-back gate | YES (pilot path) |

### Developer / ops / CI / tooling

| file | classification | O3 scope | notes |
| --- | --- | --- | --- |
| `scripts/query_model_impact.py` | developer/ops CLI | read path (same service semantics) | constructs binder+traversal directly |
| `scripts/prove_derivation_slice.py` | proof CLI (K pair) | tooling | via `build_semantic_runtime` |
| `scripts/check_model_sync.py` | developer/CI validation | no (validates ontology↔kernel sync; does not interpret runtime meaning) | reads authored YAML text; O4 must eventually remove |
| `scripts/seed_aebs_api_fixture.py` | test/dev fixture seeding | no | `OntologyIdentity.from_file`; O4-relevant |
| `de4sdv/semantic/authority_inventory.py` + `scripts/generate_semantic_authority_inventory.py` | generation/inventory gate | no | reads YAML as inventory input by design (O1 gate) |
| `de4sdv/semantic/projection*.py` + `scripts/generate_semantic_projection_*.py` | generation only | no | O2 generators; unchanged by O3 |
| `de4sdv/semantic/snapshot.py`, `delivery_gate.py` | lane-D tooling | no | binding/git-level trust; no ontology read |
| `tools/`, `scripts/windows/`, remaining scripts | no ontology/KernelContract consumption (verified) | no | — |
| `build/*.py` probes | local, untracked | excluded from the inventory | not repository consumers |

Non-consumers (checked): `de4sdv/sysml_api/{client,repository,identity,ingestion,fixture}.py`,
`de4sdv/semantic/{method_contract,method_evaluator,method_pilot}.py` (model consumers
through API element ids; no authored-ontology read), `tools/*` beyond the viewer.

## 2. Migration boundary — exactly 13 identities

O2.1 (7, in `semantic-projection-v1.json`): `MethodPhase`,
`MethodContractObligation`, `EvaluationScopeMembership`, `EvaluationSourceKind`,
`TestedScopeDeclaration`, `RetainedExecutionRecordReference`,
`AcceptanceAttestationReference`.

O2.2 (3, in `semantic-projection-v1.1.json`): `VerificationCase`,
`hasSubject`, `verifiedBy`.

O2.3 (3, in `semantic-projection-v1.2.json`):
`derivesRequirementFromNeed`, `derivedRequirementsOfNeed`,
`hasRelevantArchitecture`.

No fourteenth identity. Reviewed exclusions (must NOT migrate, machine-checked
absent from the chain): `MethodEvaluationScope`, `DerivesFromNeed` class row,
`derivesNeedFromConcern`, `realizedBy`, `specifiesFunction`,
`hasRelevantEvidenceContract`, `EvidenceContract`, `allocatedTo`,
`deployedTo`. Everything outside the scope remains under the old authority
path until separately migrated.

## 3. Old authority bundle (Task B)

Machine-readable record: scope document `basis` + `identities[].old_authority`.
Extracted executably from the repository at the comparison base (never
hand-written):

- **Git revision identification**: `basis.comparison_base_revision` =
  `1aabce06ee3a927f94e997e723331d3e2455e6a7` (permanent main; validated as an
  existing ancestor of the checked-out revision; squash-safe — no
  feature-branch commit is ever recorded).
- **Ontology YAML**: `approach/framework/ontology/de4sdv-basic-ontology.yaml`,
  sha256 recorded in `basis.ontology.sha256` (59 classes / 34 relationships).
- **KernelContract implementation identity**: `de4sdv/semantic/kernel_contract.py`
  digest + `OntologyIdentity` (path + sha256) — the identity enforced by
  `RevisionBinding.require_ontology` on every query.
- **RevisionBinding identity**: `git_repository`, `git_commit` (full SHA),
  `sysml_project_id`, `sysml_commit_id`, `scope`, `semantic_validation`;
  `status()`/`require_current()` fail closed on any drift.
- **KernelBindingIndex requirements**: ingestion-validated
  `kernel_bindings` per file-mapped class; missing binding = hard error
  (ADR 0011: no runtime source parsing, no name fallback).
- **Runtime/query implementation files** (digests recorded in
  `basis.runtime_files`): `runtime.py`, `query.py`, `traversal.py`,
  `impact.py`, `api_binding.py`, `kernel_binding_index.py`,
  `kernel_contract.py`, `sysml_api/revisions.py`.
- **API Representation mechanics currently used**: the ontology's
  `sysml_mapping.configuration` per relationship (strategy, directions,
  roles, exclusion, property keys) plus the traversal implementations
  (representation mechanics; semantics are the declared domain/range +
  strength).
- **Per-identity old records** (in the scope document): semantic source,
  strategy, support state, blocked/unsupported boundary, query direction,
  domain/range, semantic strength. All 13 identities resolve; all five
  relationships execute (none blocked — `hasRelevantEvidenceContract` is
  blocked but is NOT in scope).

The old path is executable/reproducible: every recorded digest resolves to
real bytes at the comparison base, and the strategy table is read from the
live contract (not documentation).

## 4. Proposed new O3 bundle (Task C)

For the migrated subset, the authority bundle becomes:

- **Authoritative semantic-model revision**: the governed KerML/SysML model
  revision (all model inputs of the O2 chain) at the exact cutover revision.
- **Semantic Projection chain through v1.2**: `semantic-projection-v1.json`
  → `v1.1` → `v1.2` (schemas `de4sdv.semantic-projection.v1/.v1.1/.v1.2`),
  digests recorded in the scope document; the v1.2 artifacts bind
  `source_revision = b6db63643a7613f1582b72a1d6daf43d64fd206b`.
- **API Representation Profile chain through v1.2**: the three profile
  artifacts, digests recorded; representation mechanics only, each entry's
  `semantic_contract_echo` locked to the projection declaration (drift
  blocks — UG-25).
- **Runtime/query implementation build**: the cutover runtime build id
  (recorded per comparison manifest).
- **Exact Git revision**: the cutover candidate revision (permanent main).
- **Validated SysML project/commit**: an exact-revision validated full-model
  ingestion (binding + export) at the cutover revision.

**`api_binding.status = unclaimed` is NOT sufficient for O3.** The v1.2
artifacts intentionally carry no exact-revision API closure. O3 readiness
must obtain the exact-revision validated ingestion (§9); until it exists,
this is a recorded blocker, and no support state may be promoted on the
strength of the chain's existence (UG-24/UG-26).

## 5. Same-revision comparison contract

The plan requires old and new authority paths to be compared over the SAME
engineering inputs; the only intended variable is the authority path.
Executable contract (`de4sdv/semantic/o3_equivalence.py`):

- `validate_manifest_pair(old, new)` — `de4sdv.o3-comparison-manifest/v1`
  requiring equal `git_revision`, `sysml_project_id`, `sysml_commit_id`,
  `import_closure_digest`, `subject_ids`, `evaluation_scope`, `runtime_build`,
  `completeness_boundary`, and DISTINCT `authority_path`. Any difference
  blocks the comparison (test-locked).
- `compare_semantic_results(old, new)` — per-subject comparison of predicate,
  canonical direction, semantic strength, claim boundary, support state,
  completeness, unsupported/incomplete records, target identity sets,
  witness identity sets, diagnostics. Identifiers compared exactly; sets
  canonicalized (irrelevant enumeration order); trace paths remain ordered
  (meaningful SysML ordering — UG-17/UG-23).
- `check_k_pair_witness_consistency(...)` — the K pair must remain ONE
  modeled fact under both paths; a new path that materializes two
  independent facts blocks.

Same-revision requirements: same Git revision, same SysML API project and
commit, same import/dependency closure, same subject ids, same
configuration/evaluation scope, same runtime build, same representation
completeness boundary. No comparison across different ingestions is called
equivalence.

## 6. Equivalence matrix (Task D) — per-dimension

Full per-identity records: scope document `identities[].comparison`. Static
parity is compared per identity across SEPARATE dimensions, and an identity
is never `EQUIVALENT` merely because its semantic core matches. Summary at
the comparison base:

- **declared_semantic_core: 13/13 EQUIVALENT** (domain, range, canonical
  direction, semantic strength; kernel mapping kind for classes).
- **representation_contract: 13/13 EQUIVALENT** — the old mapping mechanics
  and the new Profile serializer mechanics carry exactly the reviewed fields
  with equal values; missing, extra, or differing fields are load-bearing
  drift and block (§8).
- **grounding_identity: 12/13 EQUIVALENT; 1/13 NOT_YET_COMPARABLE**
  (`VerificationCase` — the construct identity, reviewed standard-library
  anchors, and covered type population all compare EQUIVALENT, but the
  executable library-grounding proof is not bound to the cutover revision on
  either authority path; see §8).
- **claim_boundary: 13/13 EQUIVALENT** — every new-side claim text satisfies
  the old strength class's reviewed boundary contract.
- **scope_exclusions: 13/13 EQUIVALENT** — restriction axes and the
  `MemberProduct` exclusion lineage match the old enforcement points.
- **Reviewed contract checks: 62/62 PASS** (K pair one-fact/two-navigations
  integrity, hasSubject and verifiedBy restrictions, bounded
  hasRelevantArchitecture, no promotion keys, vocabulary-only honesty,
  projection/profile separation and echo consistency, excluded identities
  absent).
- **Runtime behavior: NOT_YET_COMPARABLE (13/13)** — the new authority path
  has no runtime implementation at readiness; the cutover PR must execute
  the same-revision comparison harness over a privileged exact-revision
  ingestion before any activation claim.

Honest totals at readiness:

```text
static authority-contract parity: 12/13 identities fully equivalent across
all static dimensions; 1/13 (VerificationCase) carries one dimension pending
the cutover-revision grounding proof. No static mismatch exists anywhere.
runtime equivalence: 0/13 completed; 13/13 NOT_YET_COMPARABLE.
```

| identity | core | repr | grounding | claim | scope | overall static | runtime |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MethodPhase | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| MethodContractObligation | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| EvaluationScopeMembership | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| EvaluationSourceKind | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| TestedScopeDeclaration | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| RetainedExecutionRecordReference | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| AcceptanceAttestationReference | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| VerificationCase | EQ | EQ | pending proof | EQ | EQ | NOT_YET_COMPARABLE | NOT_YET_COMPARABLE |
| hasSubject | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| verifiedBy | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| derivesRequirementFromNeed | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| derivedRequirementsOfNeed | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |
| hasRelevantArchitecture | EQ | EQ | EQ | EQ | EQ | EQUIVALENT | NOT_YET_COMPARABLE |

No `BLOCKING_MISMATCH` exists; there are no
`INTENTIONAL_MIGRATION_REVIEW_REQUIRED` rows. Any mismatch the cutover
produces blocks activation until reviewed (UG-26).

## 7. Support-state preservation

Matrix: scope document `support_preservation`. Per identity: the old runtime
support is recorded (`runtime-queryable` for the implemented relationships,
`runtime-binding-identity` for file-mapped classes, native vocabulary for
`VerificationCase`), `new_support_state = vocabulary-only`,
`promotion = none`, `readiness_verdict = NO_PROMOTION`,
`runtime_preservation = NOT_YET_COMPARABLE`.

At readiness this proves ONLY that artifact publication does not promote
support. Runtime support preservation is a separate, future obligation: the
O3 harness must prove the new authority path preserves the old path's exact
queryable/blocked behavior for every identity. Generated row ≠ supported;
runtime mapping exists ≠ supported; historical retained run ≠ current
support; API metaclass exists ≠ semantic support. Negative tests lock
accidental promotion.

## 8. Special equivalence contracts

**Representation contract (per relationship).** The old mapping mechanics
are compared field-by-field against the new Profile serializer mechanics
with reviewed exact field sets:

```text
hasSubject:            strategy, membership_types, member_property, owner_types
verifiedBy:            strategy, membership_types, element_types,
                       owner_membership_types, reference_property, direction
K pair:                strategy, connection_definition, need_role,
                       requirement_role, query_direction, source_lineage_of,
                       target_lineage_of, native modeled direction
hasRelevantArchitecture: strategy, relationship_types, direction,
                       source_property, target_property, source_types,
                       exclude_source_specializations_of = MemberProduct
```

Missing, extra, or differing fields are load-bearing drift
(`BLOCKING_MISMATCH`). Adversarial tests mutate ONE old-side field at a time
while keeping domain/range/direction/strength unchanged and prove the block
(direction `incoming` → `outgoing`; exclusion removed or class-changed;
`source_types` changed; `membership_types`/`member_property` changed;
`reference_property` changed; `query_direction` swapped;
`connection_definition`/`need_role`/`requirement_role` changed). Serializer
mechanics stay representation — this is an O3 authority-path parity check,
never a change to the Projection/Profile separation. The K pair
additionally machine-locks ONE modeled `DerivesFromNeed` fact / TWO
navigations.

**VerificationCase grounding (UG-28).** `native == native` is never
sufficient and API metaclass equality alone is never accepted. The
comparison checks the construct identity, the reviewed standard-library
anchors — `VerificationCases::VerificationCase` (implied Subclassification,
definition role) and `VerificationCases::verificationCases` (implied
Subsetting, usage role) — and the covered type population
(`{VerificationCaseDefinition, VerificationCaseUsage}`); all three compare
EQUIVALENT against the old path's machine contract. The executable
library-grounding PROOF remains `NOT_YET_COMPARABLE`: the old side's
evidence is a parity-reviewed record and the retained privileged run
(`34576049742` at candidate `0a23902370`) is historical, and the new side's
proof step (licensed exporter anchor resolution + read-back) has not been
executed at the cutover revision. Construct/anchor/type-population drift
blocks.

- **K pair** (`derivesRequirementFromNeed`, `derivedRequirementsOfNeed`):
  ONE `connection def DerivesFromNeed` witness; typed roles
  (`need : StakeholderNeedCandidate`, `derivedRequirement :
  RequirementCandidate`); validated native direction `Need -> Requirement`;
  inverse and forward navigations over the SAME witness population (5
  authored usages at the reviewed baseline); provenance-only strength
  (`derivation`); companion linkage symmetric; duplication blocks. The
  harness fails if the new path materializes two independent facts.
- **O2.2 relationships**: `hasSubject` stays `Requirement -> MemberProduct`
  with BOTH governed lineage restrictions (source Requirement lineage,
  target MemberProduct lineage); `verifiedBy` stays
  `Requirement -> VerificationCase` with native verification-objective
  semantics only (coverage relation only; no execution-success,
  satisfaction, or acceptance promotion).
- **hasRelevantArchitecture**: `Requirement -> ArchitectureElement`,
  strength `relevance`, bounded by: Requirement-domain closure, architecture
  part/action representation, authored incoming Dependency witness,
  MemberProduct-lineage exclusion; no fabricated ArchitectureElement kernel
  binding; no realization/allocation/satisfaction promotion; no RFLP
  collapse (`Requirement -> Function -> LogicalElement -> PhysicalElement`
  is never folded into a direct realization relation).

## 9. Current API-closure readiness (Task 19)

Classification for the current `main` (`1aabce0…`): **MISSING** — no
privileged full-model API ingestion exists at this revision.

Retained evidence is HISTORICAL_ONLY:

- Run `34630102233` (success) at Git `72926c958d…` — the K closure run;
  structured record `docs/method-conformance/o1/closure-evidence.json`
  (id `r6-3`, subjects: `DerivesFromNeed`, `derivesRequirementFromNeed`,
  `derivedRequirementsOfNeed`; status: historical accepted evidence for the
  K slice only). Not an ancestor of `main` (squash-merged lineage).
- Run `34576049742` (success) at Git `0a23902370…` — Lane B candidate
  ingestion; retained bundle under
  `~/.hermes/outputs/pr249-review-a5f2a5c/`. Historical.
- The deployed ask-viewer's binding artifact and the local development
  binding are tied to their own historical revisions; neither is a
  current-main closure.

Required privileged evidence before O3 activation (not dispatched by this
task):

1. A privileged full-model API ingestion (`workflow_dispatch` on the exact
   cutover revision) producing: the full-model revision binding
   (`git_commit` = cutover SHA; ontology identity = current ontology digest;
   validated `kernel_bindings`), the export, and a green run of
   `validate_full_model_semantic_queries`, `validate_product_line_scope_api`,
   `validate_semantic_mcp`.
2. The same-revision comparison harness executed over that revision: old
   path vs the proposed new bundle for all 13 identities (query-result
   equivalence, K pair witness consistency, support-state preservation),
   producing the classified equivalence report.
3. An extended snapshot/cache identity including the authority bundle id
   (§12) so cross-bundle reuse is impossible.

## 10. Runtime routing design (design only — no implementation)

Invariant (no silent fallback, no implicit winner, no mixed authority, no
name-based routing, no feature-branch-dependent state):

```text
if identity in approved O3 migrated set (the 13):
    resolve via ONE explicitly versioned, revision-bound O3 authority bundle
else:
    retain the current authored authority
```

The bundle identity is explicit and revision-bound (bundle id = model
revision + projection/profile chain digests + runtime build + API closure
reference). Mixed authority for one identity is impossible by construction:
exactly one provider per identity, selected by an explicit set, fail-closed
on an unknown or unset selector.

Minimum runtime seam (the exact surface a cutover PR would change — designed,
not implemented):

1. `de4sdv/semantic/runtime.py::build_semantic_runtime` — gains one explicit
   bundle input (e.g. `semantic_authority` / verified bundle document path).
   No implicit default: an absent selector is a hard error for migrated
   deployments.
2. `de4sdv/semantic/o3_bundle.py` (new, cutover) — loads and verifies the
   O3 authority bundle (chain digests, budgeted identity set, API closure
   reference) and exposes an authority facade with the SAME surface the
   runtime already consumes: `relationship_mapping(name)`,
   `class_mapping(name)`, `mapping(name)`, `identity` — identical interface
   to `KernelContract` for migrated identities, delegating to the old
   contract for the rest.
3. `de4sdv/semantic/traversal.py` / `query.py` / `impact.py` /
   `api_binding.py` — unchanged strategy internals: they consume the facade
   through the existing `contract` parameter (duck-typed; no rewrite).
   `KernelBindingIndex` identity consumption is unchanged (identity stays
   ingestion-validated).
4. `de4sdv/sysml_api/revisions.py` — `require_ontology` generalizes to the
   bundle's identity requirement (old: ontology digest; new: bundle id +
   model revision) in the cutover PR.

The seam is deliberately one constructor argument plus one module: the
semantic runtime is not rewritten, and no strategy logic moves.

## 11. Rollback design (design only)

Reversible activation model:

- **Old bundle identity**: `o0-o1-authored` — ontology digest
  `80dd19ae…` (see scope document) + kernel-contract digest + old runtime
  build + the deployed binding of the pre-cutover revision.
- **New bundle identity**: `o3-<revision>` — cutover revision + v1/v1.1/v1.2
  projection and profile chain digests + new runtime build + the privileged
  exact-revision ingestion reference.
- **Activation selector**: an explicit deployment input (for example
  `DE4SDV_SEMANTIC_AUTHORITY_BUNDLE`) set to the new bundle id, plus the
  matching binding artifact and app SHA; the deployed ask-viewer/env and the
  MCP server launch configuration carry it. Unknown, unset, or mismatched
  selector → refuse to serve (never a silent default).
- **Rollback selector**: the same input set back to `o0-o1-authored` plus
  the previous binding artifact and app SHA, then restart. Rollback never
  edits generated artifacts, never reinterprets old evidence, and never
  silently re-imports a different baseline: the old bundle bytes are
  restored by reference (deployment artifact + recorded digests).
- **Stale cache/binding rejection**: revision binding must satisfy
  `require_current(expected)` and the bundle's identity requirement;
  snapshots/element caches/indexes carry the authority bundle id and are
  rejected (cache miss, not reinterpretation) when it differs.
- **API/project revision mismatch**: binding `git_commit` must equal the
  deployed app SHA and the bundle must reference the same SysML
  project/commit as the binding; any mismatch fails closed
  (`RevisionMismatchError`).

## 12. Cache/snapshot invalidation findings

| store | current identity | cutover impact |
| --- | --- | --- |
| Viewer element snapshots (`ask_model_semantic.py`, `~/.cache/de4sdv/semantic-snapshots/<sysml_commit>.json`) | `{format, git_commit, sysml_project_id, sysml_commit_id}` + sidecar sha256 | MUST gain the authority bundle id: today a snapshot built under the old authority would be silently reused under the new one. Identity mismatch = miss (existing fail-closed read path). Regeneration not strictly required (the element corpus is authority-independent) — but bundle-keyed identity is required. |
| Viewer semantic-context cache (`_SEMANTIC_CTX_CACHE`) | key = sorted target element ids | MUST include the authority bundle id (or be scoped to the service instance) before activation; otherwise answers computed under one bundle are served under the other. |
| Viewer guide index / generation cache (`serve.py` `ask_index`) | keyed per served revision | content = guide HTML, not semantic authority; refresh with the normal deploy; no semantic-correctness impact. |
| Deployment artifacts (`deployment/artifacts/current/de4sdv-full-model-binding.json`) | per-deploy binding + app SHA | must be re-pointed alongside the selector (activation and rollback); never edited in place. |
| Revision binding `kernel_bindings` | ingestion-validated | retained in the new bundle (identity stays ingestion-owned); no regeneration by O3. |
| Method snapshots (`snapshot.py`, Lane D) | externally supplied payload digest + evaluation key + commit | evaluator build unchanged by O3; if the evaluator build ever changes, snapshots re-verify against the external binding (existing fail-closed rule). |
| API-side caches (sysml2-api service) | none semantic (serves imported revisions) | none. |

Deployment restart is required at activation and rollback (env selector +
binding artifact change). No persisted index may be reused across
incompatible authority bundles.

## 13. Acceptance-case mapping (Task 20)

| case | requirement | how this package addresses it |
| --- | --- | --- |
| UG-20 | generated YAML edited / adapter changes domain/range/strength without a model change → reject drift; exact-revision comparison detects unauthorized reinterpretation | declared comparator is exact-field; chain digests + `--check` regeneration make any adapter-side reinterpretation a regeneration failure; the runtime comparison harness re-checks at cutover. |
| UG-23 | same revision + profile with irrelevant enumeration/serialization ordering → same canonical digest and equivalent answers | result comparator canonicalizes declared set fields; trace paths stay ordered; scope generation is byte-deterministic (`--check`). |
| UG-24 | omitted model-authoritative identity → generation/coverage gate fails; runtime must not silently operate with reduced semantics | scope build fails on a missing identity (`missing-identity` blocks; test-locked); cutover must refuse a bundle whose identity set is incomplete. |
| UG-25 | profile changes traversal so domain/range/direction/strength changes without an authoritative revision → compatibility gate fails | profile `semantic_contract_echo` is locked to the projection declaration (drift blocks); profile carries mechanics only; projection rows are mechanics-free. |
| UG-26 | O3 comparison finds disagreement between unchanged old semantics and new semantics → block activation until classified/reviewed | comparator returns BLOCKING_MISMATCH with reasons; runtime dimension stays NOT_YET_COMPARABLE until the harness runs; no activation without a classified report. |
| UG-28 | expected metaclass but missing/wrong library grounding → report unsupported/incomplete | class identity stays ingestion-validated (kernel bindings); no name/metaclass fallback; the chain's class rows carry the ingestion-validated resolution contract. |

Related cases informing the design: UG-15 (per-field authority; missing
semantic definition blocks — the declared matrix is per-field), UG-17
(meaningful ordering preserved), UG-19 (O4 failure if any consumer still
reads authored YAML — inventory §1 records every YAML reader for the O4
sweep), UG-27 (compatibility output cannot become independent authority —
the readiness tooling is planning evidence, not runtime input).

## 14. Blocking mismatches and intentional migrations

- **Blocking mismatches (declared): none.** All 13 identities are
  EQUIVALENT; all contract checks pass.
- **Blocking items for O3 activation (evidence-gated, not semantic):**
  1. no current exact-revision validated ingestion for the cutover
     candidate revision (§9) — MISSING;
  2. the same-revision runtime comparison has not run (runtime: 0/13
     completed; 13/13 NOT_YET_COMPARABLE by design);
  3. the `VerificationCase` standard-library grounding proof is not bound to
     the cutover revision on either authority path
     (`grounding_identity` pending — §8);
  4. snapshot/context cache identities do not yet include an authority
     bundle id (§12).
- **Intentional migrations requiring review: none currently declared.**
  Any future difference the cutover classifies as
  INTENTIONAL_MIGRATION_REVIEW_REQUIRED must be reviewed explicitly (UG-26)
  before activation.

## 15. Exact implementation files for the later O3 cutover PR

Designed surface (none of this is implemented here):

```text
de4sdv/semantic/o3_bundle.py            (new: bundle loader + authority facade)
de4sdv/semantic/runtime.py              (one explicit bundle input)
de4sdv/sysml_api/revisions.py           (bundle identity requirement)
scripts/run_o3_equivalence.py           (new: same-revision harness runner)
tools/sysml_html_viewer/ask_model_semantic.py   (snapshot/context identity)
deployment/compose.yaml + ask-viewer env + MCP launch config (selector)
scripts/validate_semantic_mcp.py / validate_full_model_semantic_queries.py
                                        (re-run + bundle-aware assertions)
```

No traversal strategy internals, no model files, no ontology YAML, no O2
artifacts change in a cutover PR.

## 16. Plan boundary

This package performs no O3 authority activation and no O4 YAML retirement.
After O3 is implemented and independently accepted, the correct statement is
scoped to the reviewed 13-identity surface; the remainder of the semantic
runtime stays on the old authority path until separately migrated, and the
Unified Semantic Engineering Plan is never called complete by this work.

