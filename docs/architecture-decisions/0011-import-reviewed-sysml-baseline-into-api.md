# ADR 0011: Import the reviewed SysML baseline into the API repository

## Status

Proposed

## Context

ADR 0010 established revision-bound semantic queries and proved the path with a
bounded AEBS API fixture. That fixture is useful for deterministic integration
tests, but it is not the reviewed DE4SDV model and cannot support production
claims about the full baseline.

DE4SDV needs one controlled path from reviewed textual SysML in Git to a SysML
API project and commit. The path must use an existing SysML implementation to
parse and resolve the language. A DE4SDV-specific parser would create a second
semantic authority and is not acceptable.

The official serializer and the API service currently use different JSON
profiles. A controlled adapter is therefore required between serialization and
commit creation. That adapter must transform serialized objects only; it must
not parse textual SysML or infer missing model semantics.

## Decision

DE4SDV will import the reviewed model through this pipeline:

```text
reviewed Git SHA
  -> official SysML parser and semantic validation
  -> per-document standard JSON serialization
  -> loss-bounded API payload adapter
  -> one API project and baseline commit
  -> exact UUID and internal-reference readback
  -> complete ontology/kernel binding report
  -> Git/API revision binding
  -> production semantic queries
```

The import scope contains:

- every `.sysml` document under `textual-notation-of-model/`, excluding
  rejected snapshot mirrors;
- every product model under
  `model-based-product-line-engineering/product-models/`; and
- the pinned SysML library sources required to resolve those documents.

Every source document is recorded with its authority, path, size, and digest.
The export records which document produced each API element UUID.

The adapter preserves official serializer UUIDs as API data identities. It
removes only references whose targets are outside the exported document set and
reports every removed external reference with source UUID, property path,
target UUID, and source URI. It does not synthesize replacement objects.

The importer creates a new project and one immutable baseline commit. It reads
the commit back and fails unless:

- the set of API element UUIDs exactly matches the exported set; and
- every internal UUID reference from the export survives at the same property
  path.

A failed import may leave a disposable, unbound API project. It must not emit a
`passed` revision binding.

## Ontology validation

After API readback, every ontology class in the ontology/kernel contract is
classified explicitly:

- `mapped`: one exact file/declaration mapping resolved to one API UUID;
- `native`: the class intentionally maps to native SysML vocabulary rather than
  one kernel declaration;
- `external`: the authoritative object intentionally remains outside the API
  baseline;
- `unresolved`: an exact file/declaration mapping resolved to no API UUID; or
- `ambiguous`: an exact file/declaration mapping resolved to multiple API UUIDs.

File-mapped resolution uses the expected API metatype, declaration name, and
serializer-recorded source document. Matching a name in the wrong document is
not accepted. Any `unresolved` or `ambiguous` result blocks the revision binding.

Native and external classifications remain explicit semantic boundaries. They
must not be silently promoted into file-mapped API objects.

## Runtime source

A validated full-model binding is the primary runtime source for API semantic
queries. The bounded AEBS fixture remains only for fast, deterministic tests of
transport, identity, traversal, and failure behavior.

The textual backend remains available for offline use and bounded parity checks.
It is not the source for API-mode results.

Production validation exercises change-impact queries across distinct modeled
concerns and includes `impact(reqCommandEmergencyBraking)`. Query results retain
API UUIDs, revision metadata, provenance, ontology-controlled semantic strength,
ambiguity failure, and explicit gaps.

## Privileged execution

The official parser is a native, licensed tool and is unavailable on every
contributor host. The repository therefore provides a privileged workflow that:

1. resolves pinned model dependencies;
2. exports the exact checked-out Git revision;
3. starts the pinned API service implementation;
4. imports and reads back the full model;
5. validates ontology bindings;
6. runs production semantic queries; and
7. publishes the binding and validation reports as review artifacts.

Public pull-request checks remain available without the privileged tool. A full
model binding is not accepted without privileged exact-head evidence.

## Consequences

- The API repository can represent the reviewed DE4SDV baseline rather than a
  hand-created semantic fixture.
- Runtime semantic queries use real imported model objects and relationships.
- Source-file provenance remains available even though it is not a native API
  property.
- Serializer/API profile differences are visible and testable instead of hidden
  in a custom parser.
- External standard-library references are reported as an import boundary.
- Imports use more memory and time than fixture tests and belong in privileged
  integration validation, not every fast test run.
- A future API implementation that accepts project-interchange packages directly
  may replace the adapter without changing ADR 0010's semantic architecture.

## Non-goals

This decision does not introduce:

- a custom SysML parser;
- a graph database or federated knowledge graph;
- a required semantic cache;
- Hermes model-repository write access;
- evidence-repository ingestion; or
- verification, compliance, certification, or homologation claims.

## Links

- [Revision-bound semantic query decision](0010-bind-semantic-impact-queries-to-api-revisions.md)
- [SysML API integration guide](../../sysmlv2-api/README.md)
