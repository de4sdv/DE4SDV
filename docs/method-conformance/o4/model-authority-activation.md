# O4 model-authority activation and rollback

Date: 2026-10-08 (O4 Wave C2) · Plan: DE4SDV Unified Semantic Engineering
Plan v1.2 (wins on conflict) · Owner decisions: `owner-decisions-2026-10.md`
(Wave B 2026-10-07, Wave C 2026-10-07/08).

This is the operational procedure for deploying the **model-authority
bundle** (`mab-…`) in production, for rolling back, and for proving that
rollback in production. Since O4 Wave C2 the model authority is the **only**
semantic authority: the authored ontology YAML, the O3 bundle runtime and
the legacy runtime were deleted, so there is no in-revision fallback
selector. **Rollback is a redeploy of the pre-C2 revision** (section 4).
Merging the C2 PR activates nothing; production keeps its recorded
deployment until the owner deploys a revision and names the exact `mab-`
id.

## 1. Configuration reference

The ask-viewer container (and the MCP server / impact CLI, where used)
select authority explicitly:

| variable | value | default |
| --- | --- | --- |
| `DE4SDV_SEMANTIC_AUTHORITY` | `model` (the only accepted value) | unset (refused) |
| `DE4SDV_MODEL_AUTHORITY_BUNDLE` | path to the accepted closed model bundle JSON | `/run/de4sdv/model/de4sdv-model-authority-bundle.json` (container path) |
| `DE4SDV_MODEL_AUTHORITY_BUNDLE_ID` | the exact accepted id (`mab-<32 hex>`) | empty (required) |

Placement rules: the variables go in the **compose substitution
environment** (`/srv/de4sdv/sysml2-api.env` or the deploy session), never
only in `ask-viewer.env`; the bundle is delivered on the host under
`/srv/de4sdv/artifacts/model/` (read-only mount at `/run/de4sdv/model`),
outside the checkout.

Selection is fail-closed and bundle-id-bound (owner decision D6): an unset
selector, the retired values `legacy` and `o3` (refused with a message that
names this document: rollback is a redeploy), any other value, a missing
path or id, a malformed id, a missing file, a bundle that is not closed and
`activation_eligible`, a served id different from the requested one, or a
runtime `semantic_authority_id` other than `mab:<id>` refuses startup.
Every cache and snapshot key carries the `mab:` id.

Revision bindings are `de4sdv.revision-binding/v2`: they carry the
model-built **semantic-authority identity** (`semantic_authority`:
`sai-<32 hex>` over the projection layer paths and digests and the contract
content). A v1 binding (`ontology` block, the authored-YAML identity) is
refused; the deployment binding of a C2 revision is produced by that
revision's ingestion.

## 2. Preconditions (all required)

1. The C2 PR is merged into `main` **with a merge commit** (never squash):
   the generated pairs it regenerates are bound to a branch commit that
   must stay reachable from `main`. The exact-SHA CI for the accepted SHA
   is green. The accepted SHA is named once and used for every step below.
2. The privileged full-model ingestion was dispatched at that exact SHA
   (`gh workflow run privileged-full-model-api-ingestion.yml --ref main
   -f ref=<sha>`), and BOTH jobs completed:
   - `ingest-and-validate` success. Since C2 it builds the **candidate
     model-authority bundle** right after ingestion and runs the three
     batteries (production semantic concerns, product-line scope, semantic
     MCP) under it (`--allow-candidate-bundle`, evidence only);
   - `model-authority-evidence` **success** (the job carries
     `continue-on-error`; read its own conclusion from the jobs API). It
     rebuilds the candidate bundle (the id must equal the ingest job's, so
     the batteries ran under exactly that bundle), computes coverage, the
     runtime answers over the migrated identity set, the decision-13
     read-back, and closes the bundle.

   A **reuse run** (section 2a) may supply the `model-authority-evidence`
   success; the acceptance package then names both run ids.
3. The artifact `model-authority-evidence-<sha>` contains
   `de4sdv-model-authority-activation-eligibility.json` with
   `activation_eligible: true`, derived (never asserted) as: O4 definition
   closure `closed` AND every required validation passed, each sha256-bound
   to its artifact in the closure attestation:
   `model_projection_coverage` (the report equals the checkout's
   recomputation, the bundle is bound to the checkout, **no residual**:
   any residual identity or governed declaration blocks),
   `model_runtime_answers` (the live `EvidenceContract` closure equals, by
   element id, the eight bound members validated from the export; the K
   pair answers), `verification_anchor_readback` (owner decision 4: a
   failed read-back blocks activation), `full_model_semantic_queries`,
   `product_line_scope` and `semantic_mcp` (each battery report bound to
   the candidate bundle id). In this privileged job the read-back queries a
   `pg_restore`d snapshot of the same run's API database, identity-checked
   against the export; the deployment-bound read-back is activation step
   0d.
4. The requirement-population delta report
   (`de4sdv-o4-requirement-population-delta.json`, owner decision 6) is
   reviewed and disclosed. It is measured evidence, not a gate.
5. Independent review of the evidence (`de4sdv-assurance`), recorded as an
   acceptance package: exact SHA, run id(s), `mab-` id, closure digests,
   artifact digests, per-gate results, discriminator population, delta
   report, and the coverage dispositions: the residual is empty; the
   **refused** identities (`IncrementTraceabilityShell` MERGE,
   `derivesNeedFromConcern` REMOVE, answered only with their register
   disposition, owner decision D5) and the **retired** names (`realizedBy`,
   `deployedTo`, `validatedBy`, `constrainedBy`, `validatesFitnessForUse`,
   refused as `retired; use <successor>`, owner decision D4) are listed
   and acknowledged.
6. Record the API database snapshot size and step time on the first
   dispatch, and the `Prove the restored API serves the export corpus`
   result (`de4sdv-o4-restored-corpus-proof.json`, `passed: true`).
7. The rollback target is still deployable (section 4): its ingestion
   artifact has not expired, or a fresh ingestion of it exists.
8. **Owner-gated:** the `sysml-api-production` environment approval for any
   production deploy, and the activation decision that names the exact
   `mab-` id.

## 2a. Restore proof and reuse mode

**Schema preservation.** `model-authority-evidence` serves a
`pg_restore`d database with the pinned API build. That build's
`persistence.xml` sets `hibernate.hbm2ddl.auto=create-drop`,
which recreates the schema at startup and wipes restored data. The job
therefore patches it to `update` before staging, behind a guard that the
expected line exists and an assertion that no `create-drop` remains, the
same patch `deployment/sysml2-api/Dockerfile` applies for production.
`ingest-and-validate` keeps `create-drop`: it starts on an empty database,
which is the intended behavior there.

**Restore proof.** Right after the API starts, before any evidence step,
`scripts/verify_restored_api_corpus.py` proves that the binding's SysML
project and commit exist in the restored API and that the element count
and element id set read through the API equal the export's (and the
semantic report's `element_count`). A refusal is an `::error::` naming the
cause, every evidence step is skipped, and the proof report and API log
tail are still uploaded.

**Reuse mode.** The `reuse_ingestion_run` dispatch input repeats only the
model-authority job, on the artifacts of an earlier run, without
re-ingesting (~4.5 h saved):

```text
gh workflow run privileged-full-model-api-ingestion.yml --ref main \
  -f ref=<sha> -f reuse_ingestion_run=<earlier run id>
```

`ingest-and-validate` is skipped. Before anything is downloaded,
`scripts/verify_reuse_ingestion_run.py` checks through the GitHub API, and
refuses unless all hold:

- `ref` is set to an exact 40-character SHA, and the run id is numeric and
  not the current run;
- the source run is a run of this same workflow file in this repository,
  `event=workflow_dispatch`, `status=completed`, and its `head_sha` equals
  `ref`;
- the source run's `ingest-and-validate` job concluded `success`;
- `full-model-api-ingestion-<ref>` and `model-authority-api-db-<ref>` each
  exist exactly once, `expired=false`, originating from `ref`. The
  snapshot is retained for 3 days and the ingestion evidence for 14, so a
  reuse run must start within 3 days of the source run.

Artifact names come from the `ref` input, never from `github.sha` (a reuse
dispatch runs on a newer `main`). Both downloads are bound to the verified
artifact ids, and the existing `Verify inputs are bound to the checked-out
revision` step still re-checks the content (export, binding and candidate bundle
name the checked-out SHA; the dump matches its sha256). The verified
source run is recorded as `de4sdv-o4-ingestion-source.json` in the
evidence artifact, which is named `model-authority-evidence-<ref>`. Only
`model-authority-evidence` gets `actions: read`, for the cross-run
verification and download. A dispatch with the input empty behaves as
before.

The two helpers (`verify_reuse_ingestion_run.py`,
`verify_restored_api_corpus.py`) are workflow wiring. They are taken from
the workflow's own revision (`github.sha`, materialized to
`/tmp/de4sdv-ci`), not from the evidence checkout, because a reuse run
checks out an older `ref` that can predate them. Every model-evidence step
still runs from the checked-out `ref`.

A reuse run concludes `success` without an ingestion artifact. The deploy
workflow's automatic run selection and the core-evidence workflow fail
closed on such a run (an ambiguous selection or a missing
`full-model-api-ingestion-<sha>`); pass the ingestion run id explicitly.

**Run history and pitfalls.**

- Run 37677500924 (dispatch at `ff0311b`, 2026-10-08):
  `ingest-and-validate` succeeded (4 h 22 min); `model-authority-evidence`
  failed after 6 min. The job restored the same-run dump and then started
  the unpatched pinned build, whose `create-drop` dropped the constraints
  and recreated the schema. The API served 0 elements, so read-back
  (`missing=84429`), population delta, comparison (`O3BundleError`, closure
  element count) and close all refused. They refused correctly, but only
  through secondary symptoms. Fixed by the schema-preservation patch and
  the restore proof above. That run's artifacts are the intended input of
  the first reuse run.

## 3. Activation procedure

The `mab-` id digests only closure-independent content: the Git revision,
the semantic-authority identity, and the components (every model layer
digest; the successor contract; routing; the implementation manifest).
Every binding-dependent value (binding digest, SysML project/commit,
validated `EvidenceContract` member ids, validation digests,
`generated_at`) lives in the closure attestation, which is not part of the
id. Re-closing at the deployment binding therefore reproduces the
privileged `mab-` id exactly; only the attestation changes.

**Before the C2 deploy (mandatory; the C2 revision refuses `legacy`, `o3`
and an unset selector).** Production runs `ff0311b` with the `legacy`
selector until this step, and the C2 deploy recreates the ask-viewer from
the compose substitution environment. Edit it first, or the deploy recreates
a viewer that refuses every semantic answer:

```text
P1. record the current /srv/de4sdv/sysml2-api.env semantic-authority lines
    (DE4SDV_SEMANTIC_AUTHORITY, DE4SDV_MODEL_AUTHORITY_BUNDLE[_ID],
    DE4SDV_O3_*) with the acceptance package: section 4 restores exactly them;
P2. copy the privileged closed bundle (same mab- id as the accepted one) to
      /srv/de4sdv/artifacts/model/de4sdv-model-authority-bundle.json
    (its closure is bound to the privileged binding, so after the deploy the
    viewer reports the request, kind == "model", but does not serve it until
    step 1 replaces it with the deployment-bound closure);
P3. set in /srv/de4sdv/sysml2-api.env:
      DE4SDV_SEMANTIC_AUTHORITY=model
      DE4SDV_MODEL_AUTHORITY_BUNDLE=/run/de4sdv/model/de4sdv-model-authority-bundle.json
      DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-<accepted id>
P4. dispatch the deploy with the declared authority:
      gh workflow run deploy-public-sysml-api.yml --ref main \
        -f git_sha=<SHA> -f expected_semantic_authority=mab-<accepted id>
    The mandatory post-deploy verification fails the run when
    /ask-status.json .semantic_authority.kind is not "model" (invalid
    included) or its bundle_id is not the declared id.
```

```text
0. deployment-bound closure (once per deployed binding):
   a. confirm deployment-status.json .baseline.git_commit == accepted SHA;
   b. fetch the deployment binding and semantic report READ-ONLY;
   c. from a clean checkout at the deployed SHA:

        python scripts/run_model_authority_bundle.py bundle \
          --source-revision <SHA> --out <dir>

      the printed candidate must carry EXACTLY the accepted mab- id (stop
      otherwise);
   d. against the DEPLOYED API, with the candidate bundle:

        python scripts/readback_verification_anchors.py \
          --api-url <deployed API> --binding <deployment binding> \
          --export <evidence export> \
          --semantic-report <deployment semantic report> \
          --api-source deployed-api \
          --git-revision <SHA> --output <dir>/readback.json
        python scripts/probe_definition_migration.py --root . \
          --binding <deployment binding> --export <evidence export> \
          --expected-git-revision <SHA> > <dir>/definition-probe.json
        python scripts/check_model_projection_coverage.py \
          --json <dir>/coverage.json \
          --bundle <dir>/de4sdv-model-authority-candidate-bundle.json
        python scripts/run_model_authority_bundle.py compare \
          --model <dir>/de4sdv-model-authority-candidate-bundle.json \
          --out <dir> --api-url <deployed API> \
          --binding <deployment binding> --export <evidence export> \
          --git-revision <SHA>
        # the three batteries, each with
        #   --semantic-authority model --allow-candidate-bundle
        #   --model-authority-bundle <dir>/de4sdv-model-authority-candidate-bundle.json
        #   --model-authority-bundle-id mab-<accepted id>
        python scripts/validate_full_model_semantic_queries.py ... --output <dir>/queries.json
        python scripts/validate_product_line_scope_api.py ... --output <dir>/scope.json
        python scripts/validate_semantic_mcp.py ... --output <dir>/mcp.json
        python scripts/run_model_authority_bundle.py close \
          --model <dir>/de4sdv-model-authority-candidate-bundle.json \
          --binding <deployment binding> --git-revision <SHA> \
          --definition-probe <dir>/definition-probe.json \
          --coverage <dir>/coverage.json \
          --answers <dir>/de4sdv-model-authority-answers.json \
          --readback <dir>/readback.json \
          --full-model-semantic-queries <dir>/queries.json \
          --product-line-scope <dir>/scope.json \
          --semantic-mcp <dir>/mcp.json --out <dir>

   e. review against the privileged acceptance: same mab- id; only the
      closure attestation differs (deployment binding). Require
      activation_eligible=true.

1. copy the reviewed closed bundle to
     /srv/de4sdv/artifacts/model/de4sdv-model-authority-bundle.json

2. confirm /srv/de4sdv/sysml2-api.env still carries the P3 values (the
   DE4SDV_O3_* variables are no longer read; remove them);

3. recreate the ask-viewer
   (docker compose ... --env-file /srv/de4sdv/sysml2-api.env
    up -d --force-recreate ask-viewer); expect a cold load for the new
   authority id;

4. verify provenance before trusting any answer (the Ask verifier fails
   unless the runtime SERVES the accepted bundle, and on invalid):

     python3 deployment/scripts/verify_public_ask.py \
       --application-sha <SHA> \
       --expected-model-authority-bundle-id mab-<accepted id> --live-query

   which checks, in GET https://viewer.de4sdv.org/ask-status.json:
       .semantic_authority.kind         == "model"
       .semantic_authority.authority_id == "mab:<accepted id>"
       .semantic_authority.bundle_id    == the accepted id
       .semantic_warmup.status          reaches "ready"
   and the MCP surface (scripts/semantic_mcp_server.py
   --semantic-authority model --model-authority-bundle <path>
   --model-authority-bundle-id mab-<id>): model_status reports the mab: id.
```

## 4. Rollback procedure (redeploy)

After C2 there is no in-revision fallback: the C2 revision cannot select O3
or legacy (both refused, D6). Rollback is a **redeploy of the pre-C2
revision `ff0311b`** (the Wave B revision in production before C2; at the
time of writing it serves the `legacy` selector and its model activation is
pending), following that revision's copy of this document (its model, O3
and legacy selectors remain available there). No model, generated artifact
or evidence record is edited.

The environment is edited **before** the redeploy, exactly as for the C2
deploy: the deploy recreates the ask-viewer from the compose substitution
environment, and `ff0311b` cannot serve the C2 bundle.

```text
1. BEFORE dispatching, restore /srv/de4sdv/sysml2-api.env to the lines
   recorded in P1 (legacy at the time of writing; or model with the
   accepted Wave B mab- bundle and id; or that revision's O3 selection);
2. deploy ff0311b through the production deploy workflow (owner-approved
   sysml-api-production environment), with that revision's ingestion
   artifact (full-model-api-ingestion-ff0311b…) and the authority it must
   report:
     gh workflow run deploy-public-sysml-api.yml --ref main \
       -f git_sha=<ff0311b full SHA> -f artifact_run_id=<run> \
       -f expected_semantic_authority=<legacy | o3:<bundle id> | mab-<Wave B id>>
   (the workflow's verifier accepts the pre-C2 status shape,
   baseline.ontology, and fails on invalid or any other authority; a
   model expectation must be SERVED by ff0311b, not only requested);
   a red post-deploy verification does NOT roll the API back: the stack
   swap has already happened, so fix the environment and recreate the
   ask-viewer, or redeploy;
3. verify .semantic_authority.kind and the id of that revision.
```

**Expiry.** The `ff0311b` ingestion artifact expires on **2026-10-22**.
C2 must be deployed and its rollback drill (section 5) completed before
then; afterwards the rollback path needs a fresh privileged ingestion of
`ff0311b` (about 4.5 h) before it can be deployed.

## 5. Production rollback proof (required once, right after the C2 deploy)

Run deploy C2 → redeploy `ff0311b` → redeploy C2 and record, for each phase,
the provenance snapshot and the three batteries
(`validate_full_model_semantic_queries.py`,
`validate_product_line_scope_api.py`, `validate_semantic_mcp.py`) against
the deployed API:

1. **C2** (`model`, accepted C2 `mab-` id);
2. **rollback** (`ff0311b`, its accepted Wave B authority);
3. **redeploy C2** (same C2 `mab-` id).

Every phase edits the environment **before** its deploy (P1 to P4 for a C2
phase, section 4 step 1 for the rollback) and dispatches with the matching
`expected_semantic_authority`. Each deploy produces a new deployment
binding, so phase 3 repeats activation step 0 (deployment-bound closure)
before its batteries.

Acceptance: the phase-1 and phase-3 payloads are **byte-identical minus
provenance** (after removing the semantic-authority/authority-id,
bundle-id and `generated_at` fields the canonical JSON bytes are equal).
The phase-2 payloads differ from phase 1 only by the classified C2
changes: the retired names answer as `retired; use <successor>` and the
refused identities with their disposition under C2, while `ff0311b` still
serves them; every other difference is a blocking finding (stay on or
return to `ff0311b`, open an issue). `run_model_authority_bundle.py
compare-answers --old … --new … --allow-revision-change` compares two
runtime-answer reports across revisions with their real labels.

Retain the nine battery outputs, the provenance snapshots and the diff
results with the acceptance package.

## 6. Failure behavior

| failure | behavior |
| --- | --- |
| `DE4SDV_SEMANTIC_AUTHORITY` unset, `legacy`, `o3` or another value | refuses to start; the message names this procedure (rollback = redeploy) |
| missing bundle path/id, malformed `mab-` id, missing file | refuses to start; the error names the variable or path |
| bundle not closed or `activation_eligible` false (e.g. read-back failed) | refuses to start |
| served bundle id or `semantic_authority_id` differs from the request | refuses to start |
| binding v1 (`ontology` block) or a semantic authority other than the checkout's | refuses to start |
| viewer with a refused model request | serves no semantic answers; `/ask-status.json` reports `.semantic_authority.kind == "invalid"` with the reason |
| deploy with an unset, stale or wrong selector | the API deploy's mandatory verification fails the run (`kind` is not the declared one, `invalid`, another bundle id, or on a pre-C2 rollback a model bundle that is not served). That red run does **not** roll back the API: the new stack stays deployed and the operator fixes the environment and recreates the ask-viewer (or redeploys). The Ask deploy refuses before any host change when its declared id is malformed or differs from the host's `DE4SDV_MODEL_AUTHORITY_BUNDLE_ID`; its verifier fails unless the runtime serves the accepted `mab:` id, and its rollback restores the previous checkout and ask-viewer. The monitor alerts on `invalid` |

## 7. Boundary

The model authority is the runtime source of every served identity. The
retired names are refused, not answered; their model retirement records are
kept as history. The refused identities are answered only with their
register disposition. The decision-13 read-back establishes presence and
shape of the implied verification anchors in the live API at one revision,
not verification adequacy. Nothing here makes a compliance, certification
or homologation claim; AI-produced evidence and reviews in this chain are
inputs to the owner's decision, not expert approval.
