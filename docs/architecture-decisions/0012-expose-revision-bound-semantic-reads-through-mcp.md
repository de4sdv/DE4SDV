# ADR 0012: Expose revision-bound semantic reads through MCP

## Status

Proposed

## Context

ADR 0010 established revision-bound semantic queries over the SysML v2 API.
ADR 0011 made the validated full-model import the production runtime source.
The ontology and native traversal strategies define which SysML relationships
can be interpreted as DE4SDV engineering semantics.

Agent clients need compact access to those results without receiving the full
model or being allowed to mutate it. The protocol adapter must not become a
second semantic authority, a model cache, or a client-specific integration.

## Decision

DE4SDV exposes a read-only Model Context Protocol server over an
agent-independent semantic query service.

The runtime chain is:

```text
SysML API service URL
  + validated full-model revision binding
  + expected Git SHA
  + ontology/kernel contract
  -> existing repository, binder, traversal, and impact services
  -> compact semantic query service
  -> read-only MCP protocol adapter
  -> Hermes or any other MCP-capable client
```

MCP handlers only translate typed tool arguments into calls on the semantic
query service. They contain no engineering relationship interpretation,
prompts, search rules, or client-specific logic.

Hermes is the first demonstrated client. It is not imported by the server and
is not required by the semantic service or MCP tests.

## Tool surface

The protocol exposes seven tools:

- `model_status` — reports whether the runtime can make an exact current,
  validated, full-model claim;
- `resolve_element` — resolves one API identity and fails closed on ambiguity;
- `inspect_element` — returns a compact resolved element plus API-resident
  documentation and reference UUIDs;
- `semantic_neighbors` — traverses selected ontology-declared mappings;
- `impact` — delegates to the existing revision-bound impact service;
- `trace` — searches a bounded path using only executable ontology mappings;
- `verification_coverage` — projects evidence-contract and verification-case
  coverage from the impact service, including explicit gaps.

Every tool is declared read-only, non-destructive, idempotent, and closed-world.
There is no raw API tool in the normal agent surface.

## Binding and failure contract

Every semantic operation requires:

- a binding whose semantic validation status is `passed`;
- an expected full Git SHA equal to the binding's Git SHA;
- the exact bound SysML project and commit to be readable; and
- identity resolution to produce one unambiguous API object.

A stale, unvalidated, missing, or ambiguous runtime fails closed. A validated,
revision-bound fixture may answer deterministic test queries, but
`model_status` reports it as not current and every result retains
`scope: fixture`. Only `scope: full-model` can make a current-baseline claim.

Results retain:

- Git SHA, API project UUID, and API commit UUID;
- element and relationship-object UUIDs;
- `sysml://` provenance URIs;
- ontology predicates and traversal strategies;
- semantic strengths; and
- explicit gaps when a mapped relationship is unavailable.

Generic dependencies remain relevance only. Verification relationships require
the native verification semantics established in the ontology and traversal
layer. Names, textual similarity, embeddings, and language-model inference are
not semantic evidence.

## Runtime and validation

The stdio server accepts four explicit inputs:

1. SysML API service URL;
2. validated binding JSON path;
3. expected Git SHA; and
4. ontology contract path.

The same values can be supplied as documented environment variables for MCP
clients that launch stdio subprocesses.

Fast tests run the complete MCP protocol path against the bounded fixture. The
privileged full-model workflow imports the exact reviewed model, starts the MCP
server, calls all seven tools through an MCP client, and retains the structured
result as exact-head evidence.

A real Hermes proof uses the same stdio command and binding. The proof must
retain the tool results and revision tuple; a prose answer without tool-backed
identities is not sufficient evidence.

## Consequences

- Agent clients receive compact, auditable semantic subgraphs instead of model
  dumps.
- MCP remains replaceable protocol plumbing over the existing architecture.
- Another MCP-capable client can use the same seven tools without Hermes.
- No second graph, persistent semantic cache, or model write surface is added.
- Adding a semantic relation still requires an ontology mapping and traversal
  tests; adding an MCP handler cannot create engineering semantics.

## Non-goals

This decision does not introduce:

- SysML, Git, evidence, or documentation writes;
- model-editing tools for agents;
- a graph database or federated knowledge graph;
- a custom SysML parser;
- repository-text search as semantic resolution;
- heuristic or model-generated relationship inference; or
- a compliance, certification, safety, or verification-pass claim.

## Links

- [Revision-bound semantic query decision](0010-bind-semantic-impact-queries-to-api-revisions.md)
- [Full-model API import decision](0011-import-reviewed-sysml-baseline-into-api.md)
- [SysML API integration guide](../../sysmlv2-api/README.md)
