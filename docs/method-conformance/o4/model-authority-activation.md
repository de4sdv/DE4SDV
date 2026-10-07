# O4 model-authority activation and rollback

Date: 2026-10-07 · Plan: DE4SDV Unified Semantic Engineering Plan v1.2
(wins on conflict) · Owner decisions: `owner-decisions-2026-10.md`
(2026-10-07, Wave B) · O3 predecessor procedure:
`../o3/o3-activation-and-rollback.md`.

This is the operational procedure for selecting the **model-authority
bundle** (`mab-…`) in production, for rolling back to the O3 bundle (legacy
second), and for proving that rollback in production. **The Wave B
implementation PR activates nothing.** Production keeps its recorded
authority until every precondition in section 2 holds and the owner
decides the cutover by naming the exact `mab-` id.

## 1. Configuration reference

The ask-viewer container (and the MCP server / impact CLI, where used)
select authority explicitly:

| variable | value | default |
| --- | --- | --- |
| `DE4SDV_SEMANTIC_AUTHORITY` | `legacy`, `o3` or `model` | `legacy` |
| `DE4SDV_MODEL_AUTHORITY_BUNDLE` | path to the accepted closed model bundle JSON | `/run/de4sdv/model/de4sdv-model-authority-bundle.json` (container path) |
| `DE4SDV_MODEL_AUTHORITY_BUNDLE_ID` | the exact accepted id (`mab-<32 hex>`) | empty (required for `model`) |
| `DE4SDV_O3_AUTHORITY_BUNDLE`, `DE4SDV_O3_AUTHORITY_BUNDLE_ID` | the O3 rollback bundle (unchanged O3 procedure) | see the O3 document |

Placement rules are the O3 rules: the variables go in the **compose
substitution environment** (`/srv/de4sdv/sysml2-api.env` or the deploy
session), never only in `ask-viewer.env`; the bundle is delivered on the
host under `/srv/de4sdv/artifacts/model/` (read-only mount at
`/run/de4sdv/model`), outside the checkout; the directory is never read
unless `model` is selected.

Selection is fail-closed and bundle-id-bound: a missing path or id, a
malformed id, a missing file, a bundle that is not closed and
`activation_eligible`, a served id different from the requested one, or a
runtime `semantic_authority_id` other than `mab:<id>` refuses startup. A
requested model authority **never falls back** to O3 or legacy; rollback
is an explicit selector change. Every cache and snapshot key carries the
`mab:` id, so model and O3 caches never cross.

`legacy` and `o3` resolve through the frozen O3 machinery unchanged
(`authority_selection.py` is an O3 runtime-build member and is not
edited): the O3 rollback path is byte-identical to the one in production.

## 2. Preconditions (all required)

1. The Wave B PR is merged into `main` **with a merge commit** (no
   squash), so its exact PR head SHA stays reachable from `main`, and the
   exact-SHA CI for that head is green. The accepted SHA is the exact PR
   head (or the exact merged SHA when the merge commit's tree differs from
   the PR head tree, e.g. because `main` moved before the merge); it is
   named once and used for every step below.
2. The privileged full-model ingestion was dispatched at that exact SHA
   (`gh workflow run privileged-full-model-api-ingestion.yml --ref main
   -f ref=<sha>`), and BOTH jobs completed:
   - `ingest-and-validate` success (O3 bundle closed, O3 comparison
     `EQUIVALENT`);
   - `model-authority-evidence` **success** (the job carries
     `continue-on-error` so it never blocks the deploy/core-evidence
     consumers of the ingestion run; its own conclusion must therefore be
     read from the jobs API, not from the run conclusion).
3. The artifact `model-authority-evidence-<sha>` contains
   `de4sdv-model-authority-activation-eligibility.json` with
   `activation_eligible: true`, which is derived (never asserted) as:
   O3 `activation_eligible` AND O4 definition closure `closed` AND the
   model-projection coverage report equal to the checkout's recomputation
   with no residual drift and the bundle bound to the checkout AND
   model-vs-O3 and model-vs-legacy runtime equivalence `EQUIVALENT` AND the
   **decision-13 live-API read-back passed** (owner decision 4: a failed
   read-back blocks activation; no claim stronger than the export is made
   before it passes). Each gate is sha256-bound to its artifact in the
   closure attestation.
4. The requirement-population delta report
   (`de4sdv-o4-requirement-population-delta.json`, owner decision 6) is
   reviewed and disclosed. It is measured evidence, not a gate: a
   difference from the recorded 27 usages / 28 `verify` statements is
   reported, never adjusted (structurally the model carries 31 `verify`
   statements reaching the 27 usages, because four Regulatory usages are
   verified by both the pedestrian and the bicycle objective; the run
   measures which count the runtime grounds).
5. Independent review of the evidence (`de4sdv-assurance`), recorded as
   an acceptance package: exact SHA, run id, `mab-` id, O3 bundle id,
   closure digests, artifact digests, per-gate results, discriminator
   population, delta report, known residual (must be empty for retained
   rows).
6. **Owner-gated:** the `sysml-api-production` environment approval for
   any production deploy, and the activation decision that names the
   exact `mab-` id.

## 3. Activation procedure

```text
0. deployment-bound closure (once per deployed binding; the privileged
   bundle binds the CI binding and is refused against the deployment
   binding by design):
   a. confirm deployment-status.json .baseline.git_commit == accepted SHA;
   b. fetch the deployment binding and semantic report READ-ONLY;
   c. produce the deployment-bound O3 closure exactly as in the O3
      procedure, step 0 (it is also the rollback bundle);
   d. from a clean checkout at the deployed SHA, against the DEPLOYED API:

        python scripts/readback_verification_anchors.py \
          --api-url <deployed API> --binding <deployment binding> \
          --export <evidence export> \
          --semantic-report <deployment semantic report> \
          --git-revision <SHA> --output <dir>/readback.json
        python scripts/probe_definition_migration.py --root . \
          --binding <deployment binding> --export <evidence export> \
          --expected-git-revision <SHA> > <dir>/definition-probe.json
        python scripts/run_model_authority_bundle.py bundle \
          --source-revision <SHA> --o3-bundle <deployment O3 bundle> --out <dir>
        python scripts/check_model_projection_coverage.py \
          --json <dir>/coverage.json \
          --bundle <dir>/de4sdv-model-authority-candidate-bundle.json
        python scripts/run_model_authority_bundle.py compare \
          --model <dir>/de4sdv-model-authority-candidate-bundle.json \
          --o3 <deployment O3 bundle> --out <dir> \
          --api-url <deployed API> --binding <deployment binding> \
          --export <evidence export> --git-revision <SHA>
        python scripts/run_model_authority_bundle.py close \
          --model <dir>/de4sdv-model-authority-candidate-bundle.json \
          --binding <deployment binding> --git-revision <SHA> \
          --definition-probe <dir>/definition-probe.json \
          --coverage <dir>/coverage.json \
          --equivalence <dir>/de4sdv-model-authority-equivalence-report.json \
          --readback <dir>/readback.json --out <dir>

   e. review against the privileged acceptance: the mab- id, git
      revision, O3 component id, layer/successor/routing digests and
      ontology identity must be IDENTICAL; only binding-dependent closure
      fields may differ; require activation_eligible=true.

1. copy the reviewed closed bundle to
     /srv/de4sdv/artifacts/model/de4sdv-model-authority-bundle.json
   and keep the deployment-bound O3 bundle in /srv/de4sdv/artifacts/o3/
   (the tested, inactive rollback);

2. set in /srv/de4sdv/sysml2-api.env:

     DE4SDV_SEMANTIC_AUTHORITY=model
     DE4SDV_MODEL_AUTHORITY_BUNDLE=/run/de4sdv/model/de4sdv-model-authority-bundle.json
     DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-<accepted id>
     DE4SDV_O3_AUTHORITY_BUNDLE_ID=o3b-<deployment-bound O3 id>   # rollback, unused under model

3. recreate the ask-viewer exactly as in the O3 procedure, step 3
   (docker compose ... --env-file /srv/de4sdv/sysml2-api.env
    up -d --force-recreate ask-viewer); expect a cold load for the new
   authority id (no cache is shared with O3);

4. verify provenance before trusting any answer:

     GET https://viewer.de4sdv.org/ask-status.json
       .semantic_authority.kind         == "model"
       .semantic_authority.authority_id == "mab:<accepted id>"
       .semantic_authority.bundle_id    == the accepted id
       .semantic_warmup.status          reaches "ready"
   and the MCP surface (scripts/semantic_mcp_server.py
   --semantic-authority model --model-authority-bundle <path>
   --model-authority-bundle-id mab-<id>): model_status reports the mab: id.
```

## 4. Rollback procedure

Rollback is a selector change only; no model, generated artifact, YAML or
evidence record is edited.

```text
first fallback — O3 (fresh deployment-bound O3 bundle at the SAME SHA):
  1. DE4SDV_SEMANTIC_AUTHORITY=o3 with DE4SDV_O3_AUTHORITY_BUNDLE /
     DE4SDV_O3_AUTHORITY_BUNDLE_ID set to the deployment-bound O3 closure
     produced in activation step 0c;
  2. recreate the ask-viewer (activation step 3);
  3. verify .semantic_authority.kind == "o3" and the o3: id.

second fallback — legacy:
  1. DE4SDV_SEMANTIC_AUTHORITY=legacy (or remove the selection variables);
  2. recreate; verify .semantic_authority.kind == "legacy".
```

The model bundle file stays in place on rollback: a retained artifact is
not active authority and is never read under `o3` or `legacy`.

## 5. Production rollback proof (required once, right after activation)

The rollback must be proven in production, not only in tests. Run
activate → rollback → reactivate on the deployed revision and record:

1. **activate** (`model`): verify provenance (section 3 step 4), then run
   the three batteries;
2. **rollback** (`o3`, deployment-bound O3 bundle, same SHA): verify
   provenance, run the same three batteries;
3. **reactivate** (`model`, same `mab-` id): verify provenance, run the
   three batteries.

The three batteries are the existing exact-revision validators against the
deployed API with the selected authority: `validate_full_model_semantic_queries.py`
(three production concerns), `validate_product_line_scope_api.py`, and
`validate_semantic_mcp.py` (all accept `--semantic-authority model
--model-authority-bundle … --model-authority-bundle-id …`, or `o3` with the
O3 flags). Acceptance: for each battery the payloads of the three phases
are **byte-identical minus provenance** (after removing the
`semantic_authority`/authority-id, bundle-id and `generated_at` fields the
canonical JSON bytes are equal), and the reactivated payloads are
byte-identical to the first activation's. Any other difference is a
blocking finding: roll back to O3 and open an issue; do not re-activate.

Retain the nine battery outputs, the provenance snapshots and the diff
results with the acceptance package. Legacy is not part of the production
proof (it is the second fallback, proven by the privileged
model-vs-legacy comparison).

## 6. Failure behavior

| failure | behavior |
| --- | --- |
| `model` without bundle path/id, malformed `mab-` id, missing file | refuses to start; the error names the variable or path |
| bundle not closed or `activation_eligible` false (e.g. read-back failed) | refuses to start |
| served bundle id or `semantic_authority_id` differs from the request | refuses to start |
| model-authority runtime module unavailable or refusing | refuses to start; never substitutes O3 or legacy |
| viewer with a refused model request | serves no semantic answers; `/ask-status.json` reports `.semantic_authority.kind == "invalid"` with the reason |

## 7. Boundary

Activation selects the model-authority bundle as the runtime source of the
projected identities. It does not delete the authored YAML (Wave C), does
not remove the deprecated alias names (`realizedBy`, `deployedTo`,
`validatedBy`, `constrainedBy`, … stay answerable as documented
deprecated aliases until Wave C), and makes no compliance, certification
or homologation claim. The decision-13 read-back establishes presence and
shape of the implied verification anchors in the live API at one
revision, not verification adequacy. AI-produced evidence and reviews in
this chain are inputs to the owner's decision, not expert approval.
