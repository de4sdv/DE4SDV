# O3 Stage B design — production semantic-authority selection and rollback

Date: 2026-09-17 · Plan: DE4SDV Unified Semantic Engineering Plan v1.2
(wins on conflict) · Permanent Stage-A base: `main` after PR #261 =
`bc2b65abb623e50032f177d566e34e1a41c09f34`.

**Stage B implements EXPLICIT production selection and rollback for the
already-reviewed, already-proven 13-identity O3 authority bundle. The
implementation PR does not activate O3: production remains on legacy
authority by default, and merging Stage B does not itself activate
anything.** The semantic boundary is frozen: no projection/profile
redefinition, no identity added or removed, no support-state promotion, no
authored-ontology retirement (O4), no O4 work of any kind.

Stage A (PR #258, plus #259–#261) established the closed candidate bundle,
the Projection/Profile authority façade, the same-revision comparison
harness, and authority-bundle-aware cache identity, all executed through
privileged exact-revision evidence. Stage B turns that machinery into a
selectable production authority with a tested rollback path.

## 1. Stage-B scope

A. explicit deployment/runtime authority selector
   (`de4sdv/semantic/authority_selection.py`);
B. production startup verification (closed bundle + exact revision +
   revision binding + activation eligibility) inside the existing
   assembly seam (`de4sdv/semantic/runtime.py`, `o3_bundle.py`);
C. production entry-point wiring (MCP server CLI, viewer Ask-model
   semantic service, deployment stack configuration);
D. provenance exposure (`model_status`, `/ask-status.json`);
E. complete per-subject K comparison matrix persisted by the evidence
   runner (`scripts/run_o3_equivalence.py`);
F. activation/rollback operations documentation
   (`o3-activation-and-rollback.md`), tests, and this record.

No traversal strategy internals, no model files, no authored ontology, no
O2 artifacts, and no O1/O2 recorded bound input change in Stage B. The
O3 readiness scope document keeps verifying its recorded comparison base
(`1aabce06…`) through Git objects; later runtime commits cannot silently
rewrite it.

## 2. The selector

```text
DE4SDV_SEMANTIC_AUTHORITY = legacy | o3        (default: legacy)

DE4SDV_O3_AUTHORITY_BUNDLE    = <path to the accepted closed bundle JSON>
DE4SDV_O3_AUTHORITY_BUNDLE_ID = o3b-<32 hex>   (required with o3)
```

Rules (all fail closed):

- an unset/empty selector is legacy — activation never happens implicitly;
- an unknown selector value is refused (no guessing, no "latest");
- `o3` requires BOTH the exact bundle path and the exact bundle id; a
  directory is never scanned and a bundle is never discovered;
- the loaded document must be the declared schema, in the `closed` state,
  and its recomputed id must equal the requested id;
- there is no fallback from a requested O3 bundle to legacy: any selection
  or verification failure refuses the O3 runtime instead of quietly
  serving legacy answers;
- the selector is a DEPLOYMENT input (environment/CLI), never a semantic
  model content change: activation and rollback do not touch model,
  projection, or profile content.

`build_selected_semantic_runtime()` is the single production call path:
resolve the selection, then build through the existing assembly seam
(`build_semantic_runtime`) — one seam, no second semantic runtime.

## 3. Production startup verification

Every check below runs at startup, before the service exists. Any mismatch
prevents O3 startup (`O3BundleError` / `AuthoritySelectionError`; entry
points refuse to serve).

```text
selector          schema, closed state, recomputed bundle id == requested id
bundle id         recomputed content digest over {schema, git revision,
                  migrated identity set, Projection chain, Profile chain,
                  runtime build}
git revision      binding.git_commit == bundle.git_revision == expected
                  runtime revision (exact)
runtime build     recomputed over the runtime build files at the checkout
projection chain  exact paths/schemas/source revisions/digests recomputed
profile chain     exact paths/schemas/source revisions/digests recomputed
revision binding  binding digest == closure binding_sha256; semantic
                  validation passed; ontology compatibility identity equal
SysML project/commit   binding == closure attestation
API closure       attestation schema, structured fields, self-reproducing
                  import closure digest, element count
validation evidence    required validations exactly `passed`, structured
                  records bound to produced-output digests
grounding         VerificationCase grounding result present; BLOCKING_MISMATCH
                  never loads; NOT_YET_COMPARABLE never activates
activation        recomputed activation_eligible must be exactly true for
                  production selection (the same-revision comparison path
                  keeps loading ineligible bundles for evidence)
```

The same closed bundle that the privileged acceptance run attests is what
production loads: nothing is silently reconstructed or refreshed. A stale
bundle fails on content (revision, runtime build, chain digests, binding
digest), never on a string comparison alone.

## 4. Provider routing (unchanged)

```text
if identity in MIGRATED_13:  Projection/Profile-backed O3 provider ONLY
else:                        legacy KernelContract authority
unknown:                     fails exactly like legacy (KeyError)
```

No name heuristic, no fallback to the authored YAML semantic definition,
never two providers for one identity. A migrated identity lookup never
touches the authored mapping table (test-locked with a poisoned legacy
provider); unmigrated identities and classes resolve by explicit
delegation and are swept identity-by-identity in tests.

The authority id is `o3:<bundle_id>` — one stable identity for the
facade, the service, the impact surface, provenance blocks, and the
authority-keyed cache/snapshot identifiers. (Stage-A-era artifacts that
show the old `o3-candidate:` label are historical records of the candidate
machinery; they are not rewritten and not reinterpreted.)

## 5. Runtime integration

| surface | file | change |
| --- | --- | --- |
| assembly seam | `de4sdv/semantic/runtime.py` | explicit `require_activation_eligible` production rule; forwards to the verified loader |
| authority loader | `de4sdv/semantic/o3_bundle.py` | `o3_authority_id`, production eligibility requirement, docstring truth |
| selector | `de4sdv/semantic/authority_selection.py` | new module: resolve + single production build path |
| MCP server | `scripts/semantic_mcp_server.py` | CLI flags + env; invalid selection exits non-zero with a clear error |
| viewer Ask-model service | `tools/sysml_html_viewer/ask_model_semantic.py` | selection-aware runtime build; provenance status; no semantic answers on a failed O3 request |
| viewer status | `tools/sysml_html_viewer/serve.py` | `/ask-status.json` exposes the authority provenance |
| query provenance | `de4sdv/semantic/query.py` | `model_status.semantic_authority` always present (legacy | o3) |
| impact/trace/neighbors/coverage | (no change) | all consume the same service; the O3 impact provenance subclass is Stage-A |

Out of scope by the accepted O3-scope classification: the developer/ops
`query_model_impact.py` CLI (constructs binder+traversal directly; O3
scope "no") and the K-slice proof CLI `prove_derivation_slice.py`
(evidence tooling, not a production serving surface). Ingestion and
validation scripts are unchanged in Stage B — the privileged workflow
already runs the evidence chain, and the cutover re-runs it at the
permanent revision.

## 6. Deployment configuration

`deployment/compose.yaml` (ask-viewer):

- `DE4SDV_SEMANTIC_AUTHORITY` (default `legacy`),
  `DE4SDV_O3_AUTHORITY_BUNDLE` (default the conventional in-container
  path `/run/de4sdv/o3/de4sdv-o3-authority-bundle.json`),
  `DE4SDV_O3_AUTHORITY_BUNDLE_ID` (default empty) — supplied through the
  compose substitution environment (the `--env-file` used by
  `deployment/scripts/deploy.py`), never through the service env file;
- a read-only `${DEPLOY_DIR}/artifacts/o3` mount at `/run/de4sdv/o3`:
  empty and never read under legacy authority; the activation places the
  accepted bundle there. Kept outside the repo checkout so deploy-time
  cleanliness stays authoritative.

Provenance is observable from the deployed service:

```text
GET /ask-status.json
  .semantic_authority.kind          legacy | o3 | invalid
  .semantic_authority.bundle_id     exact accepted bundle (o3)
  .semantic_authority.git_revision  bundle Git revision (o3)
  .semantic_authority.semantic_authority_id  served authority id

MCP model_status
  .semantic_authority.kind          legacy | o3
  .semantic_authority.id            de4sdv.o0-o1-authored-v1 | o3:<bundle id>
  .revision.git_commit              exact revision; .revision.sysml_project_id /
  .revision.sysml_commit_id         bound SysML project/commit
```

No mutable branch name participates in selection or provenance.

## 7. Rollback

Rollback is deliberate and simple: set the selector back to `legacy` (or
remove it) and recreate the service — no semantic model content changes,
no generated artifacts edited, no evidence reinterpreted.

Tested sequence **O3 → legacy → O3** (see stage-B tests): provenance
changes correctly on each step; the engineering binding is identical
throughout; authority-keyed element snapshots and the semantic-context
cache never load across authorities (an O3-warmed snapshot is a miss
under legacy and vice versa — identity mismatch is a cache miss, never
reinterpretation); re-activation reuses only its own O3-keyed cache; the
migrated-identity runtime mappings equal the authored contract's in every
phase, and a real `hasSubject` traversal over the governed fixture shape
answers identically under both authorities. The full runtime-equivalence
proof for the cutover revision remains the privileged same-revision
comparison report.

Rollback artifacts (the bundle file) stay in place after rollback: a
retained artifact is not active authority.

## 8. Evidence persistence — complete K comparison matrix

`scripts/run_o3_equivalence.py compare` now persists
`k_comparison_matrix` in the equivalence report alongside the aggregate K
witness populations: one row per compared (subject, K predicate) pair —
both navigations of the same modeled facts — carrying the subject
identity, predicate, direction and query direction, semantic strength and
claim class, per-side results (target identities, witness identities,
native witness identity with connection and typed ends, support state,
completeness), and the equality classification with its mismatch list,
plus a per-witness index mapping each native witnessed connection to the
subjects/targets it covers on each side.

This is evidence-hardening only: comparison semantics, classifications,
exit codes, and eligibility rules are unchanged. The earlier successful
run's report does not carry the matrix because the runner did not persist
it; that absence is not a defect of that run and does not change its
conclusions.

## 9. No-activation boundary (Stage B)

```text
production viewer / MCP            legacy authored authority by default
                                   (unchanged callers unless explicitly selected)
deployment selector                present; default legacy; no bundle shipped
ontology YAML                      present and still required (unmigrated
                                   identities, legacy path, ingestion
                                   compatibility, rollback)
O2 frozen inputs                   unmodified
support states                     unchanged (no promotion)
O3 bundles                         none accepted by this PR
```

## 10. Required post-merge procedure (after Stage-B squash-merge)

```text
1.  identify the exact permanent Stage-B merge SHA on main;
2.  dispatch the privileged full-model ingestion for that exact SHA
    (workflow_dispatch with ref = the SHA);
3.  generate a NEW closed O3 bundle for that exact revision;
4.  the closure attestation binds the exact revision binding;
5.  the VerificationCase grounding proof runs in the same run;
6.  the runtime equivalence report runs at the same revision;
7.  require all 13 identities EQUIVALENT;
8.  require the complete expected K witness population (no missing,
    no duplicate, no drift from the reviewed baseline);
9.  require no mismatch anywhere in the per-identity, K pair, and
    support-preservation evidence;
10. require activation_eligible = true (and the report's
    k_comparison_matrix fully equivalent).
```

The pre-Stage-B bundle is NOT final cutover evidence: the runtime build
and Git revision have changed, so a new exact-revision bundle is
mandatory. Rollback artifacts are operational safety evidence, never
concurrent authority.

## 11. Independent acceptance

A green privileged run does not activate anything. Activation requires a
separate attributable maintainer/reviewer decision on an acceptance
package containing at least:

```text
exact Git SHA                  the merge revision the evidence binds
workflow run ID                the privileged run producing the evidence
bundle ID                      exact accepted bundle id
closure digest                 import/export closure identity
SysML project/commit           the ingested exact-revision binding
artifact digests               bundle, attestation, grounding, report
migrated identity list         exactly the reviewed 13
comparison result              per-identity classifications (all EQUIVALENT)
K coverage result              expected/old/new witness populations + matrix
grounding result               VerificationCase grounding (EQUIVALENT)
rollback test result           O3 → legacy → O3 evidence at the accepted build
known limitations              stated explicitly, not smoothed over
```

## 12. Interaction with the parallel 93-entry ontology review

The review is non-executable and proposes future semantic changes; Stage B
consumes nothing from it. Stage B stays semantically frozen:

- documentation-only outcomes change no Stage-B behavior;
- a proposed change to an UNMIGRATED identity belongs to a later migration
  wave, not here;
- a proposed change to one of the MIGRATED_13 is not incorporated in
  Stage B: it requires a future versioned migration / O3 amendment with
  new projection, profile, and equivalence evidence. If the review finds a
  defect in a migrated identity, that is recorded as a blocker / future
  amendment; the frozen boundary stands until then.

## 13. Test evidence (Stage B)

`tests/test_o3_stage_b.py` (45): selector semantics (default legacy,
explicit legacy, unknown value refused, no discovery, required path/id,
nonexistent/unparsable/wrong-schema/core-state/wrong-id refused); startup
refusals through the real seam (wrong revision, expected-revision
mismatch, runtime build, projection chain, profile chain, stale binding
digest, wrong SysML project/commit, failed validation evidence,
NOT_YET_COMPARABLE and BLOCKING grounding, tampered eligibility, tampered
bundle id); comparison path still loads ineligible bundles; routing
(migrated never consults the authored provider, full unmigrated
delegation sweep, unknown fails like legacy); rollback (provenance
sequence, mapping equality across phases, traversal answer equality,
snapshot/context caches never cross authorities); entry points (viewer
O3/legacy/invalid + non-semantic fallback labeling; MCP CLI refusal,
flags-over-env, legacy default).

`tests/test_o3_runtime_equivalence.py`: K comparison matrix — complete
subject/predicate coverage (including quiet-absence rows), both authority
results with native witness identities, witness index coverage, mismatch
rows and witness classifications, and report integration with unchanged
comparison fields.

`tests/test_o3_bundle.py`: authority id pinned through
`o3_authority_id` (single identity source).

## 14. Boundary statement

Stage B provides production selection and rollback for the frozen 13-ID
O3 authority bundle. It does not migrate any additional ontology identity
and does not constitute O4.
