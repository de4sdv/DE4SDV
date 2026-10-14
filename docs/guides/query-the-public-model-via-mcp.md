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
  the semantic-authority identity the baseline was validated against
  (`baseline.semantic_authority`, `sai-…`) and the served model
  (`baseline.served_model`: the validated export's digest, element count and
  content digest).

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

## Step 1 — Get the deployment binding

The server needs the deployment's own revision binding
(`de4sdv.revision-binding/v2`), exactly as the deploy wrote it. It carries the
ingestion-validated kernel bindings (ADR 0011) and the served-model record
that the server checks the API listing against. It cannot be rebuilt from
`deployment-status.json`, which does not publish the kernel bindings. Public
distribution of the binding file is not set up yet: maintainers copy it from
the host (`/srv/de4sdv/artifacts/current/de4sdv-full-model-binding.json`),
and others request it from the maintainers.

Check that the binding is the deployment's:

```bash
python - <<'EOF'
import json, urllib.request
s = json.load(urllib.request.urlopen(
    'https://sysml-api.de4sdv.org/deployment-status.json'))["baseline"]
b = json.load(open("public-model-binding.json"))
assert b["git_commit"] == s["git_commit"]
assert (b["sysml_project_id"], b["sysml_commit_id"]) == (s["sysml_project_id"], s["sysml_commit_id"])
assert b["semantic_authority"]["id"] == s["semantic_authority"]["id"]
assert b["served_model"] == s["served_model"]
print("binding matches the deployment at Git", s["git_commit"][:12])
EOF
```

## Step 2 — Launch the server and verify

The server starts only when its startup check passes: the checkout is the
expected Git SHA with a clean tree, the binding is that revision's, and the
semantic-authority identity recomputed from the checkout equals the
binding's. It then answers only from a corpus whose content is the validated
export the binding records. That is deliberate: an agent cannot reason over
a stale or mismatched model and present the results as current. There is no
authority selector and no bundle.

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

## The first load is slow; restarts are fast

The first semantic query on a machine retrieves the full model (paginated
from the API) into an in-process cache. Over the public internet this takes
several minutes. The server then saves an identity-bound snapshot of that
revision's elements in `DE4SDV_SEMANTIC_SNAPSHOT_DIR` (default
`~/.cache/de4sdv/semantic-snapshots`), so later server starts for the same
revision load it locally instead. A snapshot is used only for the exact
revision, binding, semantic authority and API endpoint it was written for,
and only when its content is the validated export the binding records;
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
| `resolve_element` | Exact API identity for a UUID, short name, qualified name or unique bare name, fail-closed on ambiguity |
| `inspect_element` | One element without dumping the model: qualified name, keyword, owning package, documentation; for a definition its supertypes, features and enumerated values |
| `semantic_neighbors` | Ontology-mapped neighbors of an element |
| `impact` | Revision-bound requirement impact with strengths and gaps |
| `trace` | Bounded path between two elements, ontology-mapped edges only |
| `verification_coverage` | Verification cases covering a requirement, or explicit gaps |
| `next_obligation`, `method_gaps`, `increment_status`, `phase_contract` | One increment (required, except for `phase_contract`) against the workflow its charter declares in the model; see [drive an increment with the method tools](drive-an-increment-with-the-method-tools.md) |

All tools are read-only and deterministic; results carry exact element and
relationship UUIDs and provenance URIs of the form
`sysml://<project>/<commit>/<element>`.

## Name an element, describe a definition

A tool that takes an identifier accepts an element UUID, a declared short name
(`INC-AEBS-010`), a unique bare name, or a qualified name such as
`DE4SDV_MethodContext::EngineeringIncrement`, the form `phase_contract` and the
Method Check print. A qualified name is computed from the model's ownership
(the package, then each owning element) and matched exactly, every segment; it
never falls back to a bare name. A name that matches no element is refused with
the revision searched; a name that matches several is refused with the
candidates. A bare name can match several elements (`Stakeholder` does); use the
qualified name then.

Only element names along ownership resolve. SysML also reaches a member through
a short name, an alias, an inherited feature or an import, but a qualified name
that takes such a path is refused, and the refusal gives the canonical qualified
name to use instead. For example, `DE4SDV_IncrementWorkflow::IncrementCharter::increment`
is refused because `IncrementCharter` inherits `increment`; the refusal names
`DE4SDV_IncrementWorkflow::IncrementTraceObligations::increment`, where it is
declared. When the name reaches several elements, it is ambiguous there, and the
refusal lists every canonical name: `DE4SDV_MethodContext::RequirementCandidate::priority`
names both `RequirementsManagement::NeedsRequirementsAttributes::priority` and
`SYSMOD::ExtendedConcern::priority`. The explanation follows one import level
(the imported namespace's own members, not what it imports) and inheritance
through authored specializations only; past that, the refusal says only which
prefix resolved. A name that isn't a basic name, or is a SysML reserved word, is
quoted (`'end'`). A declared name that contains `::` must be quoted as one segment.

`inspect_element` gives an element's qualified name, its `keyword` (the SysML
v2 keyword that declares it, such as `part def`, `attribute`, `ref part`, `ref`
or `subject`), its owning package and its documentation. `ref part`, `ref item`,
`ref occurrence` and `ref action` mark a usage that isn't composite; a directed
usage or an end is referential anyway and keeps its plain keyword. For a
definition, `element.definition` adds:

- `supertypes`, nearest first. Every entry has `element_id`, `qualified_name`,
  `sysml_type`, `relationship_id` (the specialization), `direct` and
  `outside_export`. A supertype outside the export, such as a library type, has
  `outside_export: true` and `null` for `element_id`, `qualified_name` and
  `sysml_type`.
- Its owned features and the features it inherits, each with
  `inherited_from`. A feature that an owned or inherited feature redefines is
  not inherited.
- An enumeration's enumerated values (its literals).

A feature gives `name`, `keyword`, `type` and `multiplicity` (`[lower, upper]`,
`null` when none is declared), and when present `direction`, `end`, `redefines`
and `value`. `type` is the declared type as a qualified name, `null` when none
is declared; a redefinition keeps the type of the feature in `redefines`. A
declared type that is not part of the export, such as the library type `String`,
is reported in `type_outside_export`, not dropped: the export's external
references record its target, and this API revision keeps only the typing
relationship.

For example, over an export of the model,
`inspect_element("DE4SDV_MethodProcess::MethodPhase")` answers (abridged):

```json
{
  "resolution_level": "qualified-name-match",
  "element": {
    "sysml_type": "EnumerationDefinition",
    "qualified_name": "DE4SDV_MethodProcess::MethodPhase",
    "keyword": "enum def",
    "owning_package": {"qualified_name": "DE4SDV_MethodProcess"},
    "documentation": ["One of the 13 phases of the DE4SDV increment workflow."],
    "definition": {
      "supertypes": [],
      "owned_features": [],
      "inherited_features": [],
      "enumerated_values": [
        {"name": "phase0_incrementFraming",
         "qualified_name": "DE4SDV_MethodProcess::MethodPhase::phase0_incrementFraming"},
        "… 12 more"
      ]
    }
  },
  "gaps": []
}
```

and two owned features of `DE4SDV_IncrementWorkflow::IncrementCharter` read:

```json
[
  {"name": "expectedArtifacts", "keyword": "attribute", "sysml_type": "AttributeUsage",
   "type": null, "multiplicity": [1, "*"],
   "type_outside_export": "typed by an element outside this export; the export's external references record its target, and this API revision keeps only the typing relationship 6a85847b-…"},
  {"name": "workflow", "keyword": "action", "sysml_type": "ActionUsage",
   "type": "DE4SDV_IncrementWorkflow::IncrementWorkflow", "multiplicity": null}
]
```

## After a new deployment

Each deployment generates fresh Project/Commit UUIDs and may advance the Git
SHA. When `deployment-status.json` changes, get the new deployment binding
(Step 1), update `DE4SDV_EXPECTED_GIT_SHA`, and re-checkout the repository at
the new deployed SHA. The server refuses to start on a stale binding by design.

## Browsing without an agent

Prefer a browser? The interactive API reference is at
`https://sysml-api.de4sdv.org/docs/`, the human-readable model viewer at
[viewer.de4sdv.org](https://viewer.de4sdv.org) (see the
[model viewer guide](model-viewer.md)), and the deployment status document at
[`https://sysml-api.de4sdv.org/deployment-status.json`](https://sysml-api.de4sdv.org/deployment-status.json).
