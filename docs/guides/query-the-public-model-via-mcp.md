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
  and the ontology identity the baseline was validated against.

Project/Commit UUIDs are specific to each deployment (the importer generates
them fresh); element UUIDs are stable across deployments. Never reuse a binding
from a previous deployment or from a CI run — CI ingestion runs use ephemeral
UUIDs that do not exist in the public deployment.

## Prerequisites

- Python 3.11+ with the `mcp` package (`pip install -r requirements-mcp.txt`
  from the repository root installs the pinned version).
- A clone of this repository at the **deployed Git SHA** (the
  `baseline.git_commit` field in `deployment-status.json`). The server
  recomputes the ontology contract identity from files in the repository, so
  the checkout must be the exact revision the deployment was built from. A
  detached worktree is the cleanest way to pin one:

  ```bash
  git clone https://github.com/de4sdv/DE4SDV.git
  cd DE4SDV
  git checkout <DEPLOYED_SHA>          # from deployment-status.json
  ```

## Step 1 — Build a client revision binding

The server needs a revision-binding JSON file. For the public deployment, build
it from the live status document (Project/Commit UUIDs and ontology identity
come straight from what is actually deployed):

```bash
python - <<'EOF'
import json, urllib.request
s = json.load(urllib.request.urlopen(
    'https://sysml-api.de4sdv.org/deployment-status.json'))
b = s['baseline']
binding = {
    "git_repository": "de4sdv/DE4SDV",
    "git_commit": b["git_commit"],
    "sysml_project_id": b["sysml_project_id"],
    "sysml_commit_id": b["sysml_commit_id"],
    "import_timestamp": s["deployed_at_utc"],
    "import_tool_version": "de4sdv-full-model-import/1+official-syside-json",
    "semantic_validation": "passed",
    "scope": "full-model",
    "ontology": b["ontology"],
}
with open("public-model-binding.json", "w") as f:
    f.write(json.dumps(binding, indent=2) + "\n")
print("wrote public-model-binding.json for Git", b["git_commit"][:12])
EOF
```

## Step 2 — Launch the server and verify

The server fails closed unless binding, ontology identity, and expected Git SHA
all match. That is deliberate: an agent cannot reason over a stale or
mismatched model and present the results as current.

```bash
python scripts/semantic_mcp_server.py \
  --api-url https://sysml-api.de4sdv.org \
  --binding public-model-binding.json \
  --expected-git-revision <DEPLOYED_SHA>
```

Equivalent environment variables (`DE4SDV_SYSML_API_URL`,
`DE4SDV_REVISION_BINDING`, `DE4SDV_EXPECTED_GIT_SHA`) are available for stdio
clients that pass configuration through the environment.

## Step 3 — Register with your MCP client

Any MCP-capable client can launch the same command. For example, with Hermes:

```bash
hermes mcp add de4sdv-semantic \
  --command python3 \
  --connect-timeout 60 \
  --env DE4SDV_SYSML_API_URL=https://sysml-api.de4sdv.org \
    DE4SDV_REVISION_BINDING=/absolute/path/to/public-model-binding.json \
    DE4SDV_EXPECTED_GIT_SHA=<DEPLOYED_SHA> \
  --args /path/to/DE4SDV/scripts/semantic_mcp_server.py --api-timeout 600
```

Notes for the `hermes mcp add` syntax: all environment variables must be passed
as a single `--env` flag with space-separated `KEY=VALUE` pairs — repeated
`--env` flags overwrite each other — and the enable prompt reads from stdin.

## First query is slow; after that it is fast

The first semantic query in a server session retrieves the full model (~57k
elements paginated from the API) into an in-process cache. Over the public
internet this takes on the order of ten minutes. Every query afterwards runs
against memory and returns in well under a second. The cache lives for the
lifetime of the server process; a client that keeps the server running pays the
cold cost once.

`model_status` reports whether the runtime can make a current-baseline claim:
it returns `current_baseline: true` only when the binding is synchronized with
the expected Git SHA, the scope is full-model, and the ontology identity
matches. Every result carries the complete Git/API/ontology provenance tuple —
treat anything less as a gap, not a fact.

## The seven tools

| Tool | Answers |
| --- | --- |
| `model_status` | Can this runtime claim the current baseline? |
| `resolve_element` | Exact API identity for a UUID or name, fail-closed on ambiguity |
| `inspect_element` | One element's semantics without dumping the model |
| `semantic_neighbors` | Ontology-mapped neighbors of an element |
| `impact` | Revision-bound requirement impact with strengths and gaps |
| `trace` | Bounded path between two elements, ontology-mapped edges only |
| `verification_coverage` | Verification cases covering a requirement, or explicit gaps |

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
