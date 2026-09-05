# ADR 0017: Separate engineering authority from agent context and historical memory

## Status

Proposed

## Context

DE4SDV exposes engineering information to automation and agent clients from
several sources with different purposes and authority.

The reviewed Git repository contains project history, architecture decisions,
methodology, documentation, source models, implementation, and validation
artifacts.

The SysML v2 API repository provides revision-scoped access to the live model
graph.

The DE4SDV ontology/kernel contract defines shared engineering concepts and the
allowed interpretation of modeled relationships.

Agent clients may additionally maintain operational context or historical
memory derived from previous interactions, investigations, experiments, and
engineering work.

These sources must not be treated as interchangeable.

In particular, information remembered by an agent may describe an earlier
project state, an investigation, an assumption, or a previously discussed
interpretation. Such information is useful for continuity but cannot establish
the current modeled engineering state.

## Decision

DE4SDV separates authoritative engineering knowledge from non-authoritative
agent context.

The following authority boundaries apply.

| Concern                                  | Authority                        |
| ---------------------------------------- | -------------------------------- |
| Reviewed project baseline                | Accepted/merged Git revision     |
| Accepted decisions and governance        | Merged/reviewed ADRs and docs    |
| Contribution and decision history        | Git and pull-request history     |
| Current modeled elements, relations      | Validated revision-bound API     |
| Engineering concepts and semantics       | Ontology/kernel contract         |
| Semantic queries: trace, impact, V&V     | Validated revision-bound service |
| Agent experience and lessons learned     | Agent memory; non-authoritative  |

In this table, modeled relations means native SysML v2 relationships, and the
authoritative SysML source is a validated, revision-bound SysML v2 API
project/commit. Stale, unvalidated, ontology-mismatched, missing, or ambiguous
runtime state must fail closed and is not current engineering truth (ADR 0012).
The reviewed project baseline is the accepted/merged Git revision itself; the
accepted decisions and governance are the merged, reviewed ADRs and
documentation within it; pull-request and Git history record contribution and
discussion rather than accepted project authority.

Operational agent memory is an implementation-independent capability. DE4SDV
does not require a particular memory product, database, hosting model, or
personal knowledge-management system.

Agent memory may contain useful historical information such as:

* approaches previously attempted;
* implementation or deployment problems encountered;
* debugging observations;
* unresolved questions;
* experiment outcomes;
* historical engineering discussions; and
* working conventions.

Such information may inform agent reasoning but must not independently
establish a current engineering claim.

## Authority rule

When operational memory conflicts with an authoritative source, the
authoritative source takes precedence.

For current model state:

```text
agent memory
     │
     │ historical context
     ▼
agent reasoning
     │
     ├──────────────► revision-bound semantic query
     │                         │
     │                         ▼
     │                  ontology/kernel
     │                         +
     │                    SysML v2 API
     │
     ▼
current engineering answer
```

For example, an agent may remember that requirement `X` was previously
associated with verification case `Y`.

If the current revision-bound semantic query returns verification case `Z`, the
agent must use `Z` when answering a question about the current model.

The remembered relationship may still be reported as historical context when
relevant.

## Epistemic routing

Agent clients should select information sources according to the type of
question being answered.

```text
"What is modeled now?"
        -> revision-bound semantic service

"What is impacted by this?"
        -> revision-bound semantic service

"What verifies this requirement?"
        -> revision-bound semantic service

"Why was this architecture chosen?"
        -> reviewed ADRs / documentation / Git history

"What did we previously try or learn?"
        -> operational agent context / memory

"What is the accepted project decision?"
        -> reviewed Git artifacts
```

Queries involving multiple concerns may combine sources, but their different
authority levels must remain visible.

## Promotion of knowledge

Useful information may move from informal experience toward increasingly
authoritative project representations.

```text
engineering interaction or investigation
                |
                v
       operational context
                |
       important / recurring?
                |
                v
      issue / PR / documentation
                |
       architectural decision?
                |
                v
               ADR
                |
     engineering semantics needed?
                |
                v
        ontology / SysML model
                |
          review + baseline
                |
                v
          SysML v2 API
```

No automatic promotion occurs solely because an agent remembered or inferred
something.

Promotion into reviewed documentation, ontology, or the SysML model requires
the normal DE4SDV review and validation process.

## Agent integration

Agent-specific protocols and memory systems remain adapters around the DE4SDV
engineering architecture.

The existing semantic MCP interface provides agent-independent, read-only
access to revision-bound engineering semantics.

Operational memory providers may be used by individual agents or deployments,
but they do not become part of the semantic authority tuple and must not
introduce new engineering relationships.

The semantic authority for current modeled claims remains:

```text
Git revision
+
SysML API project/commit
+
ontology contract identity
```

## Privacy and deployment boundary

Operational agent memory may contain user-specific, deployment-specific,
private, or otherwise non-project information.

Therefore:

* DE4SDV does not require operational memory contents to be stored in the
  public repository;
* DE4SDV does not prescribe where such memory is hosted;
* credentials, memory databases, conversation history, user profiles, and
  private memory configuration are outside the reviewed public project
  baseline;
* contributors may use different memory implementations or none at all; and
* the behavior of authoritative DE4SDV semantic queries must not depend on
  access to private agent memory.

## Consequences

* Agent continuity can improve without weakening engineering authority.
* Historical project experience can assist reasoning without becoming model
  truth.
* Current engineering answers remain reproducible against explicit Git,
  ontology, and SysML API revisions.
* Memory technology can be replaced without changing DE4SDV semantic
  architecture.
* Contributors do not need access to another contributor's personal or
  operational memory.
* Private agent context does not have to be published as part of the
  open-source project.
* Conflicts between remembered and current information have an explicit
  resolution rule.

## Non-decisions

This decision does not:

* standardize a specific agent-memory product;
* require contributors to maintain agent memory;
* require publication of conversation history or personal knowledge;
* require a personal knowledge-management system;
* make remembered or inferred relationships engineering evidence;
* ingest the DE4SDV repository into an agent-memory database;
* replace reviewed ADRs or documentation with agent memory; or
* change the existing SysML v2 API, ontology, revision-binding, or semantic
  MCP authority model.

## Links

* [ADR 0004: Adopt ASEL/CM three-system framing](0004-adopt-aselcm-three-system-framing.md)
* [ADR 0005: Use SysML v2 API repository as live model store](0005-use-sysml-v2-api-repository-as-live-model-store.md)
* [ADR 0010: Bind semantic impact queries to SysML API revisions](0010-bind-semantic-impact-queries-to-api-revisions.md)
* [ADR 0011: Import the reviewed SysML baseline into the API repository](0011-import-reviewed-sysml-baseline-into-api.md)
* [ADR 0012: Expose revision-bound semantic reads through MCP](0012-expose-revision-bound-semantic-reads-through-mcp.md)
  (ADR 0017 builds directly on its semantic authority tuple and MCP boundary)
