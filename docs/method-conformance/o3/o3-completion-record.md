# O3 completion record — production cutover of the frozen 13-identity scope

Date: 2026-09-17 · Evidence package: `o3-production-cutover-evidence.json`
(`de4sdv.o3-production-cutover-evidence/v1`, this directory) · Design and
procedure: `o3-stage-b-design.md`, `o3-activation-and-rollback.md` ·
Acceptance inputs: the operator-side acceptance packages referenced in the
JSON (`operator_evidence_packages`).

**Status: COMPLETE.** O3 — the approved semantic-authority transition from
the authored YAML path to the reviewed O3 authority bundle — is complete in
production for **exactly the frozen 13-identity scope**. No additional
ontology identity is migrated by O3; no O3 semantic amendment exists; the
frozen 13 remain unchanged by the parallel O4 ontology review.

## 1. Identity

| item | value |
| --- | --- |
| deployed Git revision | `020d1d20e5c03542f67f38b1cc716f4332478538` |
| privileged evidence run | `35203768046` (`privileged-full-model-api-ingestion.yml`, success) |
| accepted bundle id | `o3b-31f999503d96233ce974f0bfd72a5df0` (closed) |
| bundle digest (shipped file) | `sha256:bcd853a9f61faa9feb9422a2db9ded4cf76ff9b2013eaa82c0b0ebbc2b99e167` |
| runtime build | `rb-68f6e13c9e27f3a39a7a5b934add8089` |
| deployment binding | project `78c216ab-cb91-4047-89b1-2ceadc372fcf` / commit `c522449f-4475-4758-b320-b4c968c10672`, binding `sha256:de6bf14b…`, element count 82,102 |
| deployment-bound closure | closed + verified, `grounding: EQUIVALENT`, `activation_eligible: true`, verification errors none |
| final production authority | `o3` — `o3:o3b-31f999503d96233ce974f0bfd72a5df0`, warmup `ready` |

The migrated set is exactly: MethodPhase, MethodContractObligation,
EvaluationScopeMembership, EvaluationSourceKind, TestedScopeDeclaration,
RetainedExecutionRecordReference, AcceptanceAttestationReference,
VerificationCase, hasSubject, verifiedBy, derivesRequirementFromNeed,
derivedRequirementsOfNeed, hasRelevantArchitecture. The evidence JSON binds
this list to `de4sdv.semantic.o3_bundle.MIGRATED_IDENTITIES`
(`tests/test_o3_completion_record.py`).

## 2. Deployment-bound closure

The closure that production loads was generated with the Stage-B machinery
for the **deployment binding** (`run_o3_equivalence.py bundle`), from the
exact deployed revision, with the privileged evidence export and
deployment-side validator outputs. Compared against the privileged closure
(`o3-stage-b-deployment-closure-amendment`, PR #264):

- core identical: bundle id, revision, runtime build, the 13 identities,
  projection chain, profile chain, ontology compatibility identity;
- only binding/closure-dependent fields differ: `binding_sha256`, deployment
  project/commit, `import_closure_digest`, `generated_at`, validator records;
- `element_count` equal (82,102); grounding artifact **byte-identical**.

## 3. Production cutover result

Performed under the explicit `DEPLOYMENT_CLOSURE_ACCEPT` decision, without
deploying any other revision:

| phase | outcome |
| --- | --- |
| activation (O3) | startup verification passed fail-closed in production; viewer `kind=o3` with the exact bundle id/revision from the first poll; warmup `ready` (by-design cold load ~18 min) |
| rollback (legacy) | `kind=legacy` / `de4sdv.o0-o1-authored-v1`, warmup ready on the first poll from the legacy authority's own snapshot |
| re-activation (O3) | `kind=o3` again, warmup ready on the first poll from the O3 authority's own snapshot |

Probe batteries (same battery per phase, MCP surface, client-side):

- corrected O3 production battery: **15/15 PASS**;
- legacy rollback battery: **15/15 PASS**, identical answers;
- O3 reactivation battery: **15/15 PASS**, identical answers;
- cross-phase comparison: **all 11 query payloads byte-identical** after
  stripping provenance blocks — only `semantic_authority` differs by phase.

Representative results: K pair both navigations (witness `2581eb6e…`),
`verifiedBy` (6 edges), `hasSubject` (`c1dd6c9d… → b9879c32…`),
`hasRelevantArchitecture` (two authored incoming Dependencies),
`trace` path found, `verification_coverage` governed `partial` — all
identical under both authorities; unmigrated `specifiesFunction`
(`c1dd6c9d… → bf4df0d5…`) answered by the legacy authority while O3 served
the migrated set.

## 4. Retained initial probe-design failures

The **first** O3 probe battery exited 1 with 13/15 checks passing. The two
failures were **probe-design errors, not semantic or runtime failures**, and
their outputs are retained as audit evidence:

1. `hasSubject` was initially queried from the verification-case side; the
   governed ontology contract defines `hasSubject` on the requirement side
   (SubjectMembership `memberElement`). Corrected query passes.
2. The unmigrated-delegation probe scanned a PartUsage with no
   ontology-mapped relations. Corrected to the governed `specifiesFunction`
   Dependency (requirement → ActionUsage). Corrected query passes.

The corrected battery (retained alongside the failed one) passes 15/15 in
all three phases. No production change was required or made.

## 5. Cache isolation evidence

Snapshots are authority-keyed:
`{sysml_commit_id}.{sha256(authority_id)[:12]}.json` — legacy
`…68b20f605453.json` (`sha256:f4e9c1cd…`) and O3 `…39919dbad354.json`
(`sha256:8e7a410e…`). Across activation, rollback and re-activation **no
snapshot mtime changed** and each authority warmed instantly from its own
snapshot: no cross-authority cache reuse, by construction and by
observation.

## 6. Known limitations

- The phase-1 recreate instant is reconstructed (anchors: first poll
  ~19:07Z, O3 snapshot written 19:24Z); containers were replaced twice
  during the exercise.
- The first O3 activation pays a by-design cold load (~18 min at this
  model size); later switches are snapshot-fast.
- MCP probe batteries run client-side over the public endpoint; the
  production host environment was not modified for them.
- `trace`/`verification_coverage` report governed `incomplete`/`partial`
  statuses identically across authorities (path found; no gaps).
- O3 remains frozen: any future semantic change to the 13 requires a
  versioned amendment with new projection/profile/equivalence evidence;
  the parallel O4 review records **no amendment required**.

## 7. Statement

**O3 is complete for exactly the frozen 13-identity scope.** Production
semantic authority is the reviewed closed bundle
`o3b-31f999503d96233ce974f0bfd72a5df0` at revision
`020d1d20e5c03542f67f38b1cc716f4332478538`, with the deployment-bound
closure verified against the deployment's own RevisionBinding. No additional
ontology identity is migrated by O3, and no O3 semantic amendment exists.
Historical O1/O2/O3 evidence is not rewritten; O4 execution planning is
governed separately (`docs/method-conformance/o4/`).
