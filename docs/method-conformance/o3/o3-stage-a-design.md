# O3 Stage A design — candidate authority bundle and equivalence harness

Date: 2026-09-15 · Plan: DE4SDV Unified Semantic Engineering Plan v1.2
(wins on conflict) · Permanent readiness base: `main` after PR #257 =
`6aa34b7c4d83dbd10f2544c3591ae22ca121691b` (parent
`1aabce06ee3a927f94e997e723331d3e2455e6a7`).

**Stage A implements candidate machinery only — no activation.** Production
semantic authority remains the authored `KernelContract` path. No authored
YAML is retired (O4). No current exact-revision runtime equivalence is
claimed. The accepted #257 readiness record
(`docs/method-conformance/o3/o3-readiness.md`,
`o3-equivalence-scope.json`) remains evidence about its recorded
comparison-base revision (`1aabce06…` for the old-bundle digests); its
conclusions are not rewritten here.

## 1. Exact Stage-A scope

A. revision-bound O3 candidate authority bundle
   (`de4sdv/semantic/o3_bundle.py`);
B. Projection/Profile-backed authority façade (same module);
C. old-vs-new same-revision runtime comparison runner
   (`scripts/run_o3_equivalence.py`);
D. authority-bundle-aware cache/snapshot identity
   (`tools/sysml_html_viewer/ask_model_semantic.py`).

Plus: the minimum runtime assembly seam
(`de4sdv/semantic/runtime.py`, `query.py`, `impact.py`,
`authority_ids.py`), the extended privileged ingestion workflow, this
design record, and the Stage-A test suites. No O2 frozen input changes; no
production authority switch; no deployment selector; no ontology change.

## 2. Candidate authority bundle schema

`de4sdv.o3-authority-bundle/v1`:

```text
schema
state                      core | closed
bundle_id                  deterministic content/revision digest (below)
git_revision               full lowercase SHA of the candidate revision
migrated_identities        exactly the reviewed 13 (order fixed)
projection_chain           [{path, schema, source_revision, sha256} × 3]
profile_chain              [{path, schema, source_revision, sha256} × 3]
runtime_build              {id, files: {path: sha256}, policy}
ontology_compatibility_identity  {path, sha256}   ← ingestion compatibility ONLY
api_closure                null (core) | attestation (closed)
evidence                   {comparison_manifest_schema, bundle_id_policy}
```

The authored ontology appears exclusively as the **ingestion compatibility
identity** — the bundle never labels it semantic authority for the migrated
set. Semantics come from the Projection; representation mechanics from the
Profile; the loader verifies and assembles them but invents nothing.

## 3. Bundle ID derivation

```text
bundle_id = "o3b-" + sha256(canonical_json({
    schema, git_revision, migrated_identities,
    projection_chain, profile_chain, runtime_build,
}))[:32]
```

The ID changes whenever ANY semantic-authority-critical component changes:
the Git revision, the exact migrated identity set, either chain's artifact
identity/digest/source revision, or the runtime build identity (over
`runtime.py`, `query.py`, `traversal.py`, `impact.py`, `api_binding.py`,
`kernel_binding_index.py`, `kernel_contract.py`, `authority_ids.py`,
`o3_bundle.py`, `sysml_api/revisions.py`). The API closure attestation is
**bound TO** the bundle ID rather than included in the core digest — that
avoids circular identity (the closure attests a bundle whose ID must exist
first). No feature-branch SHA may become a permanent accepted cutover
bundle ID; Stage A therefore publishes no final canonical cutover bundle —
only the machinery that will produce one at the permanent post-merge
revision.

## 4. Bundle core vs executable closure

- **Candidate bundle CORE** — constructible offline from the checked-out
  revision; NOT executable authority.
- **Executable CLOSED bundle** — core + a structured exact-revision API
  closure attestation (`de4sdv.o3-api-closure-attestation/v1`):
  bundle_id, git_revision, binding digest, SysML project/commit, element
  count, export digest, import/export closure digest, structured validation
  evidence records (`full_model_semantic_queries`, `product_line_scope`,
  `semantic_mcp`) each carrying an exactly-`passed` status + artifact name
  + path + the sha256 of the exact produced output, an explicit recomputed
  `activation_eligible`, the structured VerificationCase grounding result,
  and a generation timestamp.

Candidate execution requires a closed bundle; an unclosed bundle fails
closed (`load_o3_authority` refuses). A closure attesting
`BLOCKING_MISMATCH` grounding refuses execution; `NOT_YET_COMPARABLE`
grounding loads for comparison but marks `activation_blocked`.

## 5. Provider split — exactly 13 migrated identities

```text
if identity in MIGRATED_13:
    Projection/Profile provider is the only semantic provider
else:
    legacy KernelContract provider (explicit delegation)
```

Migrated: `MethodPhase`, `MethodContractObligation`,
`EvaluationScopeMembership`, `EvaluationSourceKind`,
`TestedScopeDeclaration`, `RetainedExecutionRecordReference`,
`AcceptanceAttestationReference`, `VerificationCase`, `hasSubject`,
`verifiedBy`, `derivesRequirementFromNeed`, `derivedRequirementsOfNeed`,
`hasRelevantArchitecture` — no fourteenth.

The façade (`O3AuthorityFacade`) exposes the `KernelContract`-compatible
surface the runtime already consumes — `identity`, `classes`,
`relationships`, `mapping`, `class_mapping`, `relationship_mapping` — with
identical interface shapes (`KernelFileMapping`/`KernelNativeMapping`/
`RelationshipMapping`, reused unmodified). Rules:

- **no fallback**: a migrated identity NEVER consults the authored mapping;
- **no name heuristic**: routing is by the explicit identity set;
- **no ambiguous overlap**: every identity has exactly one provider;
- an unknown identity fails exactly like the legacy contract (`KeyError`).

## 6. Runtime assembly seam

`build_semantic_runtime(..., semantic_authority=None)` — the single new
explicit argument:

- `None` (production default): legacy path, behaviorally unchanged
  (`KernelContract.load`, `binding.require_ontology`, existing kernel
  bindings, existing traversal/query implementation);
- a closed candidate bundle: the loader verifies it (revision, binding,
  chains, runtime build, closure) and the façade replaces the contract for
  the migrated 13; the candidate loader runs in O3 code — `revisions.py`
  stays O2-frozen and unmodified.

`semantic_authority_id` is exposed on the assembled service and on
`ImpactService`; it labels provenance/cache identity only and never changes
query semantics. Candidate outputs distinguish `semantic-authority`
(Projection), `representation-authority` (Profile), and `compatibility`
(ontology ingestion role); legacy outputs are byte-shape unchanged.

## 7. Candidate bundle validation rules (fail closed)

```text
binding.git_commit            == bundle.git_revision
binding.sysml_project_id      == closure.sysml_project_id
binding.sysml_commit_id       == closure.sysml_commit_id
binding.semantic_validation   == "passed"
binding ontology identity     == bundle ontology compatibility identity
binding digest                == closure.binding_sha256
projection/profile chains     == recomputed from the checkout (path, schema,
                                 source revision, digest)
runtime build identity        == recomputed from the checkout
bundle_id                     == recomputed content digest
import_closure_digest         == reproduced from the attestation's own
                                 structured fields (a recorded string alone
                                 is never accepted)
required validation statuses  == "passed" EXACTLY (failed / error / unknown /
                                 missing can never close an executable
                                 bundle)
validation evidence digests   == sha256 of the exact produced validation
                                 outputs (re-verified against the artifacts
                                 when they are available)
activation_eligible           == recomputed (grounding EQUIVALENT AND every
                                 required validation exactly passed); a
                                 BLOCKING grounding is never eligible
```

Any mismatch fails closed. Identity resolution still uses the
ingestion-produced `KernelBindingIndex`; no source parsing, no name
fallback. The candidate runner additionally requires
`requested git revision == checked-out HEAD` (exact-revision evidence
refuses moving refs).

## 8. Same-revision comparison runner

`scripts/run_o3_equivalence.py`, two modes:

- `bundle`: builds the candidate core at the checked-out exact revision,
  runs the VerificationCase grounding proof against the bound API revision,
  closes the bundle with the closure attestation, writes
  `de4sdv-o3-candidate-bundle.json`,
  `de4sdv-o3-api-closure-attestation.json`,
  `de4sdv-o3-verification-case-grounding.json`;
- `compare`: instantiates BOTH authority paths under the same runtime build
  and writes `de4sdv.o3-runtime-equivalence-report/v1`.

Comparison contract (the accepted #257 schema — never weakened):
`de4sdv.o3-comparison-manifest/v1` with equal `git_revision`,
`sysml_project_id`, `sysml_commit_id`, `import_closure_digest`,
`subject_ids`, `evaluation_scope`, `runtime_build`, `completeness_boundary`
and DISTINCT `authority_path`; any difference blocks.

Subject coverage: for each of the five runtime-queryable relationships the
runner sweeps the COMPLETE witness-derived eligible population (owners,
members, referenced endpoints of every governed witness) — deterministic,
UUID-sorted — so qualifying hops and quiet absence are both exercised.
Per subject the comparator checks revision/project/commit, predicate,
canonical direction, semantic strength, claim class, runtime support
state, completeness, target sets, witness sets, and diagnostics; sets
canonicalize; trace-path ordering (where present) stays meaningful.

Runtime support is a SEPARATE dimension from artifact support: the report
proves (a) `artifact_support_preservation` — publication never promotes
support (rows stay `vocabulary-only`), and (b) `runtime_behavior` — old/new
runtime states preserve exactly. Runtime claim text does not exist; the
compared claim CLASS is the authority-declared strength class (the
artifact-level claim text was compared statically by the readiness
package).

Class identities: the SEVEN file-mapped migrated classes compare
ingestion-validated kernel UUIDs + sysml types + declaration + source file
under both paths (never names). `VerificationCase` is native-grounded and
NEVER passes through the file-mapped binder (which rejects native mappings
by design — proven against the real `OntologyApiBinder`/`KernelContract`);
its runtime result consumes the structured grounding proof:
EQUIVALENT → EQUIVALENT, NOT_YET_COMPARABLE → NOT_YET_COMPARABLE,
BLOCKING_MISMATCH → BLOCKING_MISMATCH, absent/unknown → NOT_YET_COMPARABLE.
No ingestion kernel UUID is ever manufactured for the native mapping.

One closure identity: the runner never recomputes a second closure digest.
`compare` consumes the bundle-attested `import_closure_digest` after
independently verifying it — self-reproduction from structured fields,
binding digest, SysML project/commit, git revision, chain/runtime
identities, strict validation evidence re-verified against the produced
outputs — and requires the live element count to equal the attested
ingestion closure. The report and BOTH manifests carry that same digest;
any divergence fails closed before a report exists.

K pair: the runner compares the exact same-revision witness population
old-vs-new (must be equal), machine-locks ONE modeled fact / TWO
navigations via the accepted consistency check (duplication blocks), and
separately flags drift from the reviewed O2.3 baseline count (the baseline
statement is carried into the report for review; the constant is
test-locked against the artifact).

Exit codes: `compare` is GREEN only for a fully `EQUIVALENT` result; every
other classification (`NOT_YET_COMPARABLE`,
`INTENTIONAL_MIGRATION_REVIEW_REQUIRED`, `UNSUPPORTED_BOTH`,
`BLOCKING_MISMATCH`) exits non-zero while STILL writing the structured
report. `bundle` exits non-zero on closure errors or a BLOCKING grounding;
it may close a `NOT_YET_COMPARABLE` bundle so the comparison machinery can
run, with `activation_eligible` explicitly `false`, and the compare step
owns final workflow success.

## 9. VerificationCase grounding proof

`de4sdv.semantic.verification_grounding` — ONE shared reviewed mechanism,
used by the privileged pilot read-back (`scripts/verify_pilot_readback.py`)
and the O3 runner alike. The proof runs on the exact-revision EXPORT
ARTIFACT (elements + `external_references` + `library_anchors`); the export
`git_commit` must equal the checked-out revision, else the proof refuses.
Identity is finished by STRUCTURE, never by name text:

- anchor identity comes from the exporter-resolved `library_anchors` map
  (element ids resolved BY NAME from the pinned library at export time);
- for each governed `VerificationCaseDefinition`, an IMPLIED
  `Subclassification` witness (specific end = the governed element) must
  link to the definition anchor, either inline (reference `@uri`) or via
  the exporter's split `external_references` record — with the uri inside
  the pinned `Systems Library/VerificationCases.sysml` document;
- for each governed `VerificationCaseUsage`, the analogous implied
  `Subsetting` to the usage anchor;
- a NON-implied edge linking a governed element to the anchor with the
  right uri is contradictory evidence (conflict) and blocks.

Results: `EQUIVALENT` (every governed element proves its role); `BLOCKING_MISMATCH`
(conflicts — non-implied shapes); `NOT_YET_COMPARABLE` (missing anchors,
witnesses or uri evidence — blocks O3 activation until proven at the cutover
revision). The closure attestation carries this result; `BLOCKING_MISMATCH`
refuses candidate execution. Measured on the first exact-revision attempt's
retained export (revision `62d1a435…`): 22/22 definitions + 34/34 usages
proved → `EQUIVALENT`.

## 10. Authority-bundle-aware cache and snapshot identity

Viewer (`tools/sysml_html_viewer/ask_model_semantic.py`):

- snapshot format bumped to v2; `_snapshot_identity` gains
  `semantic_authority_id`; the snapshot filename gains a stable
  authority-derived component (`sha256(authority_id)[:12]`) so old/new
  authority caches never collide or overwrite each other; identity mismatch
  stays a cache miss, never reinterpretation (existing fail-closed load
  path);
- `_SEMANTIC_CTX_CACHE` keys become `authority_id|target-ids`, so old and
  new authority paths never share semantic-context answers.

No `/ask` redesign, no regex-fallback change, no UI change, no viewer
environment selector.

## 11. Privileged workflow integration (no dispatch in Stage A)

`.github/workflows/privileged-full-model-api-ingestion.yml`:

- optional `workflow_dispatch` input `ref` (full 40-hex); checkout uses
  `github.event.inputs.ref || github.sha`; a validation step fails when the
  requested SHA is non-empty and differs from the checked-out SHA, and
  records the exact checked-out revision (nightly schedule behavior
  unchanged);
- after the existing ingestion/validation steps, two O3 evidence steps run
  `scripts/run_o3_equivalence.py bundle` and `compare` against the same
  local API service + binding + exact-revision export artifact, with all
  existing behavior preserved;
- the O3 outputs are uploaded alongside the existing exact-head evidence;
- the job timeout is 300 minutes (raised from 180 after the first
  exact-revision attempt — the full pipeline plus the runtime-equivalence
  comparison exceeded 3 hours; the comparison itself was cut off at 38
  minutes of progress).

Production deployment/selection is untouched. Scheduled nightly behavior
remains functional.

## 12. No-activation boundary (Stage A)

```text
production viewer / MCP / CLI      legacy authored authority (unchanged callers)
deployment selector                unchanged (no O3 environment variable)
ontology YAML                      present; still required (unmigrated
                                   identities, legacy path, ingestion
                                   compatibility, rollback)
O2 frozen inputs                   unmodified (provenance preserved)
support states                     unchanged (no promotion)
```

## 13. Historical readiness record preservation

The merged #257 readiness record stays evidence about its recorded
comparison-base revision: `check_scope_document` regenerates the old-bundle
file digests from THAT revision's Git objects (never the feature-branch
working tree), so later runtime implementation commits cannot silently
rewrite the accepted baseline. A rewrite requires an explicitly
regenerated, reviewed document. Regression tests lock this (later-commit
drift stays green; tampered recorded digests fail; unresolvable bases fail
closed).

## 14. Post-merge evidence procedure (after Stage-A squash-merge)

```text
1. Stage-A squash-merge → permanent main revision C.
2. Reviewers may dispatch the privileged full-model ingestion at C
   (workflow_dispatch with ref = C) → binding + export + validations +
   O3 bundle, closure attestation, grounding proof, runtime equivalence
   report (uploaded as exact-head evidence).
3. Independent review of the equivalence report; any BLOCKING_MISMATCH
   stops the cutover; NOT_YET_COMPARABLE keeps activation blocked.
4. Any activation decision is a SEPARATE reviewed O3 cutover (deployment
   selector, cache invalidation, rollback plan) — never this PR.
```

## 15. Rollback implications

Unchanged from the readiness design and strengthened by the bundle
identity: the candidate path cannot be silently mixed with the legacy path
(one provider per identity); caches are authority-keyed (rollback cannot
reuse candidate-warmed caches); a rollback is re-pointing the deployment to
the legacy path, whose behavior this PR leaves byte-shape identical. No
activation selector is introduced in Stage A.

## 16. Test evidence (Stage A)

`tests/test_o3_bundle.py` (30): bundle integrity (wrong revision, both
chain digests, missing/extra identity, runtime build, binding digest,
SysML project/commit, ontology compatibility digest; unclosed cannot
execute; grounding-blocked refuses), routing (migrated → Projection only,
unmigrated → legacy, unknown → legacy failure), authority independence
(four fixture old-YAML mutations leave the candidate mapping untouched
while the legacy contract observes them), cross-pins (13-set, chains,
runtime-build coverage, K baseline constant), cache safety (snapshot
identity/paths never collide or load across authorities; semantic-context
cache is authority-scoped).

`tests/test_o3_runtime_equivalence.py` (26): population determinism,
comparison blocking (revision/project/commit/population/targets/witnesses/
strength/runtime-support), irrelevant ordering canonicalization, K pair
(shared witnesses pass; independent new facts block; population change
blocks), VerificationCase grounding (proven; wrong anchors/roles/
conflicting anchors block; name-only and missing implied edges stay
NOT_YET_COMPARABLE; source-document evidence proves), support separation
(publication vs runtime dimensions independent).

