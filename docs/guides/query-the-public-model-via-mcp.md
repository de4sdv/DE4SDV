# Query the public model via MCP

The DE4SDV full SysML baseline is deployed as a read-only API at
**[sysml-api.de4sdv.org](https://sysml-api.de4sdv.org)**. The repository ships
a small MCP (Model Context Protocol) server that lets any MCP-capable AI agent
query that deployment with revision-bound, provenance-preserving semantic
queries: resolve an element, walk its neighbors, trace a path between two
elements, or ask which verification cases cover a requirement.

This guide walks through connecting an agent to the **public** deployment.
For the design and why the contract is this strict, see
[ADR 0012](../architecture-decisions/0012-expose-revision-bound-semantic-reads-through-mcp.md)
and [ADR 0013](../architecture-decisions/0013-deploy-experimental-readonly-public-sysml-api.md).

## What is deployed

- API base URL: `https://sysml-api.de4sdv.org`
- Read-only: GET/HEAD/OPTIONS only; all write methods are rejected.
- One exact Git revision of the reviewed baseline, ~57k elements.
- A machine-readable status document at
  [`/deployment-status.json`](https://sysml-api.de4sdv.org/deployment-status.json)
  publishing the deployed Git SHA, the deployment's SysML Project/Commit UUIDs,
  and the semantic identity the baseline was validated against:
  `baseline.semantic_authority` (the model-built semantic-authority identity,
  `sai-…`) for a revision that contains O4 Wave C2, `baseline.ontology` (the
  retired authored-ontology identity) for an earlier revision.

Project/Commit UUIDs are specific to each deployment (the importer generates
them fresh); element UUIDs are stable across deployments. Never reuse a binding
from a previous deployment or from a CI run — CI ingestion runs use ephemeral
UUIDs that do not exist in the public deployment.

## Prerequisites

- Python 3.11+ with the `mcp` package (`pip install -r requirements-mcp.txt`
  from the repository root installs the pinned version).
- A clone of this repository at the **deployed Git SHA** (the
  `baseline.git_commit` field in `deployment-status.json`). The server
  recomputes the semantic-authority identity from the model layers in the
  repository, so the checkout must be the exact revision the deployment was
  built from. A
  detached worktree is the cleanest way to pin one:

  ```bash
  git clone https://github.com/de4sdv/DE4SDV.git
  cd DE4SDV
  git checkout <DEPLOYED_SHA>          # from deployment-status.json
  ```

## Step 1 — Build a client revision binding

The server needs a revision-binding JSON file (`de4sdv.revision-binding/v2`).
For the public deployment, build it from the live status document
(Project/Commit UUIDs and the semantic-authority identity come straight from
what is actually deployed). This works for a deployment whose status carries
`baseline.semantic_authority`; a binding v1 (`ontology` block) is refused:

```bash
python - <<'EOF'
import json, urllib.request
s = json.load(urllib.request.urlopen(
    'https://sysml-api.de4sdv.org/deployment-status.json'))
b = s['baseline']
if "semantic_authority" not in b:
    raise SystemExit("deployment predates O4 Wave C2 (baseline.ontology): "
                     "use that revision's copy of this guide")
binding = {
    "schema": "de4sdv.revision-binding/v2",
    "git_repository": "de4sdv/DE4SDV",
    "git_commit": b["git_commit"],
    "sysml_project_id": b["sysml_project_id"],
    "sysml_commit_id": b["sysml_commit_id"],
    "import_timestamp": s["deployed_at_utc"],
    "import_tool_version": "de4sdv-full-model-import/1+official-syside-json",
    "semantic_validation": "passed",
    "scope": "full-model",
    "semantic_authority": b["semantic_authority"],
}
with open("public-model-binding.json", "w") as f:
    f.write(json.dumps(binding, indent=2) + "\n")
print("wrote public-model-binding.json for Git", b["git_commit"][:12])
EOF
```

## Step 2 — Launch the server and verify

The server fails closed unless binding, semantic-authority identity,
expected Git SHA and the model-authority bundle all match. That is
deliberate: an agent cannot reason over a stale or mismatched model and
present the results as current.

The semantic authority is selected explicitly: `--semantic-authority model`
with the closed model-authority bundle accepted for the deployed revision and
its exact `mab-` id (the deployed id is published at
`https://viewer.de4sdv.org/ask-status.json` as `.semantic_authority.bundle_id`).
There is no default; an unset selector refuses to start. The bundle closure
is bound to the deployment binding, so only the bundle closed for this
deployment starts. Public distribution of that bundle file is not set up yet;
until it is, the public MCP route needs the bundle from the maintainers (see
[model-authority activation](../method-conformance/o4/model-authority-activation.md)).

```bash
python scripts/semantic_mcp_server.py \
  --api-url https://sysml-api.de4sdv.org \
  --binding public-model-binding.json \
  --expected-git-revision <DEPLOYED_SHA> \
  --semantic-authority model \
  --model-authority-bundle /path/to/de4sdv-model-authority-bundle.json \
  --model-authority-bundle-id mab-<DEPLOYED_BUNDLE_ID>
```

Equivalent environment variables (`DE4SDV_SYSML_API_URL`,
`DE4SDV_REVISION_BINDING`, `DE4SDV_EXPECTED_GIT_SHA`,
`DE4SDV_SEMANTIC_AUTHORITY`, `DE4SDV_MODEL_AUTHORITY_BUNDLE`,
`DE4SDV_MODEL_AUTHORITY_BUNDLE_ID`) are available for stdio clients that
pass configuration through the environment.

## Step 3 — Register with your MCP client

Any MCP-capable client can launch the same command. For example, with Hermes:

```bash
hermes mcp add de4sdv-semantic \
  --command python3 \
  --connect-timeout 60 \
  --env DE4SDV_SYSML_API_URL=https://sysml-api.de4sdv.org \
    DE4SDV_REVISION_BINDING=/absolute/path/to/public-model-binding.json \
    DE4SDV_EXPECTED_GIT_SHA=<DEPLOYED_SHA> \
    DE4SDV_SEMANTIC_AUTHORITY=model \
    DE4SDV_MODEL_AUTHORITY_BUNDLE=/absolute/path/to/de4sdv-model-authority-bundle.json \
    DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-<DEPLOYED_BUNDLE_ID> \
  --args /path/to/DE4SDV/scripts/semantic_mcp_server.py --api-timeout 600
```

Notes for the `hermes mcp add` syntax: all environment variables must be passed
as a single `--env` flag with space-separated `KEY=VALUE` pairs — repeated
`--env` flags overwrite each other — and the enable prompt reads from stdin.

## The first load is slow; restarts are fast

The first semantic query on a machine retrieves the full model (paginated
from the API) into an in-process cache. Over the public internet this takes
several minutes. The server then saves an identity-bound snapshot of that
revision's elements in `DE4SDV_SEMANTIC_SNAPSHOT_DIR` (default
`~/.cache/de4sdv/semantic-snapshots`), so later server starts for the same
revision load it locally instead. A snapshot is used only for the exact
revision, binding, semantic authority and API endpoint it was written for;
anything else loads from the API. Every query after the load runs against
memory.

`model_status` reports whether the runtime can make a current-baseline claim:
it returns `current_baseline: true` only when the binding is synchronized with
the expected Git SHA, the scope is full-model, and the semantic-authority
identity matches. Every result carries the complete Git/API/semantic-authority
provenance tuple —
treat anything less as a gap, not a fact.

## The tools

| Tool | Answers |
| --- | --- |
| `model_status` | Can this runtime claim the current baseline? |
| `resolve_element` | Exact API identity for a UUID or name, fail-closed on ambiguity |
| `inspect_element` | One element's semantics without dumping the model |
| `semantic_neighbors` | Ontology-mapped neighbors of an element |
| `impact` | Revision-bound requirement impact with strengths and gaps |
| `trace` | Bounded path between two elements, ontology-mapped edges only |
| `verification_coverage` | Verification cases covering a requirement, or explicit gaps |
| `next_obligation`, `method_gaps`, `increment_status`, `phase_contract` | One increment against the workflow its charter declares in the model; see [drive an increment with the method tools](drive-an-increment-with-the-method-tools.md) |

All tools are read-only and deterministic; results carry exact element and
relationship UUIDs and provenance URIs of the form
`sysml://<project>/<commit>/<element>`.

## After a new deployment

Each deployment generates fresh Project/Commit UUIDs and may advance the Git
SHA. When `deployment-status.json` changes, rebuild the binding (Step 1),
update `DE4SDV_EXPECTED_GIT_SHA`, and re-checkout the repository at the new
deployed SHA. The server refuses queries against a stale binding by design.

## Browsing without an agent

Prefer a browser? The interactive API reference is at
`https://sysml-api.de4sdv.org/docs/`, the human-readable model viewer at
[viewer.de4sdv.org](https://viewer.de4sdv.org) (see the
[model viewer guide](model-viewer.md)), and the deployment status document at
[`https://sysml-api.de4sdv.org/deployment-status.json`](https://sysml-api.de4sdv.org/deployment-status.json).
