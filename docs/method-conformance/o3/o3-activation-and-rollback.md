# O3 activation and rollback operations

Date: 2026-09-17 · Plan: DE4SDV Unified Semantic Engineering Plan v1.2
(wins on conflict) · Companion design record: `o3-stage-b-design.md`.

This document is the operational procedure for selecting the frozen
13-identity O3 semantic authority in production and for returning to
legacy authority. **The Stage-B implementation PR activates nothing**:
before an accepted O3 bundle exists AND a separate attributable
maintainer/reviewer decision authorizes the cutover, production runs the
legacy authored authority and this procedure is not executed.

## 1. Deployment configuration reference

The ask-viewer container (and the MCP server process, where used) reads
three environment variables:

| variable | value | default |
| --- | --- | --- |
| `DE4SDV_SEMANTIC_AUTHORITY` | `legacy` or `o3` | `legacy` |
| `DE4SDV_O3_AUTHORITY_BUNDLE` | path to the accepted closed bundle JSON | `/run/de4sdv/o3/de4sdv-o3-authority-bundle.json` (container path) |
| `DE4SDV_O3_AUTHORITY_BUNDLE_ID` | the exact accepted bundle id (`o3b-…`) | empty (required for `o3`) |

Placement rules (ask-viewer):

- the variables are supplied through the **compose substitution
  environment** — the `--env-file` that `deployment/scripts/deploy.py`
  passes to `docker compose` (`/srv/de4sdv/sysml2-api.env`) or the deploy
  session environment. They are deliberately NOT read from the service
  env file (`/srv/de4sdv/ask-viewer.env`), which the compose
  `environment:` section overrides — a value placed only there has no
  effect and the service will report `legacy`;
- the bundle file is delivered on the host under
  `/srv/de4sdv/artifacts/o3/` (read-only mount at `/run/de4sdv/o3` inside
  the container). The directory is empty under normal legacy operation
  and is never read unless `o3` is selected;
- the bundle placed there is the **deployment-bound closure** for the
  deployed binding (step 0 below), not the privileged run's bundle: the
  privileged bundle binds the CI ingestion's ephemeral binding and is
  refused against the deployment binding by design;
- the bundle is kept OUTSIDE the repository checkout so deploy-time
  cleanliness checks stay authoritative.

Selection semantics are fail-closed: an unknown selector value, a missing
bundle, a wrong bundle id, or any startup verification mismatch refuses
the O3 runtime. There is no automatic bundle discovery and no fallback
from a requested O3 bundle to legacy authority.

## 2. Activation procedure (only after acceptance)

Preconditions:

1. the Stage-B execution is on `main`;
2. the privileged full-model ingestion ran against that exact merge SHA
   and its artifacts passed independent review;
3. an acceptance package exists (exact Git SHA, workflow run ID, bundle
   ID, closure digest, SysML project/commit, artifact digests, migrated
   identity list, comparison result, K coverage result, grounding result,
   rollback test result, known limitations);
4. a maintainer/reviewer decision explicitly authorizes the cutover and
   names the exact bundle id.

Steps:

```text
0. generate the deployment-bound closure — required once per deployed
   binding (a redeploy creates a new binding and needs a new closure):

   a. confirm the deployed revision equals the accepted evidence revision
      (deployment-status.json .baseline.git_commit);
   b. fetch the deployment artifacts READ-ONLY (never modify the host):
      - /srv/de4sdv/artifacts/current/de4sdv-full-model-binding.json
      - /srv/de4sdv/artifacts/current/de4sdv-full-model-semantic-validation.json
      (record their sha256; the binding bytes must be identical to the
      file the deployed service reads);
   c. from a clean checkout AT the deployed revision (the runner refuses
      moving refs), run the three required validators against the
      DEPLOYED read-only API; the semantic_mcp validator runs client-side
      against the deployed endpoint (do not install MCP client
      dependencies on the production host just for this):

        python scripts/validate_full_model_semantic_queries.py \
          --api-url <deployed API> --binding <deployment binding> \
          --semantic-report <deployment semantic-validation report> \
          --output <full_model_semantic_queries.json>

        python scripts/validate_product_line_scope_api.py \
          --api-url <deployed API> --binding <deployment binding> \
          --export <evidence export> --output <product_line_scope.json>

        python scripts/validate_semantic_mcp.py \
          --api-url <deployed API> --binding <deployment binding> \
          --expected-git-revision <deployed SHA> \
          --output <semantic_mcp.json>

   d. generate the closure with the existing machinery:

        python scripts/run_o3_equivalence.py bundle \
          --api-url <deployed API> --binding <deployment binding> \
          --git-revision <deployed SHA> --export <evidence export> \
          --validation full_model_semantic_queries=passed \
          --validation-artifact full_model_semantic_queries=<c output> \
          --validation product_line_scope=passed \
          --validation-artifact product_line_scope=<c output> \
          --validation semantic_mcp=passed \
          --validation-artifact semantic_mcp=<c output> \
          --output-dir <dir>

   e. review the deployment-closure acceptance diff against the
      privileged acceptance bundle: bundle id, git revision, runtime
      build, migrated identity set, Projection/Profile chain digests and
      ontology compatibility identity must be IDENTICAL; only
      binding/closure-dependent fields (binding_sha256, deployment
      project/commit UUIDs, validator records, generated_at) may differ;
      require grounding EQUIVALENT and activation_eligible=true.

1. copy the reviewed deployment-bound closure to the host:
     /srv/de4sdv/artifacts/o3/de4sdv-o3-authority-bundle.json
   and record its sha256 next to the acceptance package;

2. append the selection to the compose environment file
   (/srv/de4sdv/sysml2-api.env):

     DE4SDV_SEMANTIC_AUTHORITY=o3
     DE4SDV_O3_AUTHORITY_BUNDLE=/run/de4sdv/o3/de4sdv-o3-authority-bundle.json
     DE4SDV_O3_AUTHORITY_BUNDLE_ID=o3b-<accepted id>

3. recreate the ask-viewer on the deployed revision (deploy.py does this
   on every deploy; for a selection-only change run the same compose
   command deploy.py uses, with the same environment):

     cd /srv/de4sdv/DE4SDV
     export DEPLOY_DIR=/srv/de4sdv
     export DE4SDV_APP_GIT_SHA=<deployed SHA>
     export DE4SDV_ASK_ENV_FILE=/srv/de4sdv/ask-viewer.env
     docker compose -f deployment/compose.yaml \
       --env-file /srv/de4sdv/sysml2-api.env \
       up -d --force-recreate ask-viewer

4. verify provenance (no semantic answer is trusted before this):

     GET https://viewer.de4sdv.org/ask-status.json
       .semantic_authority.kind          == "o3"
       .semantic_authority.bundle_id     == the accepted id
       .semantic_authority.git_revision  == the deployed SHA
       .semantic_warmup.status           reaches "ready"

5. verify the MCP surface (any launch configuration), e.g.:

     python scripts/semantic_mcp_server.py \
       --api-url <api> --binding <binding> \
       --expected-git-revision <deployed SHA> --semantic-authority o3 \
       --o3-authority-bundle /path/to/de4sdv-o3-authority-bundle.json \
       --o3-authority-bundle-id o3b-<accepted id>
   model_status must report semantic_authority.kind == "o3" with id
   o3:<accepted bundle id>.
```

The service restart is required: the authority is verified once at
startup and its id keys every cache identity.

## 3. Rollback procedure

Rollback returns the deployment to legacy authority without changing any
semantic model content, generated artifact, or evidence record:

```text
1. set DE4SDV_SEMANTIC_AUTHORITY=legacy in /srv/de4sdv/sysml2-api.env
   (or remove the three selection variables entirely);

2. recreate the ask-viewer exactly as in activation step 3;

3. verify provenance:

     GET https://viewer.de4sdv.org/ask-status.json
       .semantic_authority.kind == "legacy"
   model_status on the MCP surface reports
       semantic_authority.kind == "legacy",
       id == "de4sdv.o0-o1-authored-v1"
```

Notes:

- the bundle file stays on the host; a retained artifact is not active
  authority and is never consulted under `legacy`;
- a redeploy (new deployment binding) requires a new deployment-bound
  closure before re-activation: the retained closure fails closed against
  the new binding, by design;
- authority-keyed caches cannot cross the rollback: snapshots and the
  semantic-context cache carry the authority id, so a legacy process
  never loads O3-warmed caches and O3 re-activation reuses only its own
  (identity mismatch is a cache miss, never reinterpretation);
- no generated YAML, projection, profile, or ontology file is edited by
  activation or rollback; both are selector changes only.

## 4. Failure behavior and diagnostics

| failure | behavior |
| --- | --- |
| unknown selector value | runtime refuses to start (wrong spelling never degrades to legacy or O3) |
| `o3` without bundle path/id | refuses to start; the error names the missing variable |
| bundle missing / unreadable / wrong schema / core state / wrong id | refuses to start; the error names the path and the mismatch |
| stale bundle (revision, runtime build, chain digests, binding digest, SysML project/commit) | refuses to start; no silent reconstruction |
| privileged-run bundle against a deployment binding | refuses to start (binding digest / SysML project / SysML commit differ); generate the deployment-bound closure (step 0) instead |
| ineligible bundle (grounding not EQUIVALENT, or any required validation not exactly passed) | refuses to start |
| viewer process with a refused O3 request | serves NO semantic answers; `/ask-status.json` reports `.semantic_authority.kind == "invalid"` with the reason; the explicitly labeled non-semantic regex path (never a semantic authority) may still answer `/ask` method-context questions |
| MCP process with a refused O3 request | exits non-zero at startup with `semantic authority selection failed: …` |

Diagnostics:

- the viewer status document (`.semantic_authority`) is the single source
  of truth for what the deployed service serves;
- frozen container logs carry the same startup failure text;
- the equivalence report (`de4sdv.o3-runtime-equivalence-report.json`)
  and the closure attestation are the evidence artifacts for any
  activation question — the runtime never re-derives them.

## 5. Boundary

Activation and rollback affect ONLY the explicit selector. They do not
change the migrated identity set (still exactly the frozen 13), do not
promote support states, do not retire the authored ontology (O4), and do
not alter any evidence produced by earlier stages. Stage B provides
production selection and rollback for the frozen 13-ID O3 authority
bundle; it does not migrate any additional ontology identity and does not
constitute O4.