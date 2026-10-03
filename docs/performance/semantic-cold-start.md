# Semantic service cold starts

A fresh semantic MCP process previously fetched the complete API corpus on its
first semantic tool call, even when a previous process had loaded the same
immutable revision. Ask's disk snapshot avoided that fetch for its query cache,
but did not populate the shared repository; impact and ontology-binding calls
could still fetch the entire corpus after warm-up reported ready.

## Implementation

`de4sdv/semantic/corpus_cache.py` provides a shared, snapshot-first corpus cache.
MCP installs it lazily on the repository: handshake and tool discovery do not
wait for a corpus download. Ask hydrates both the service and shared repository
on a snapshot hit. The binder and impact service use that same repository.

The cache lives in `DE4SDV_SEMANTIC_SNAPSHOT_DIR`, or
`~/.cache/de4sdv/semantic-snapshots`. It is local runtime data, not a model source,
release artifact, ingestion certificate, or Lane D method-conformance snapshot.
Do not copy arbitrary snapshots into this directory or treat their checksums as
independent evidence. Its trust boundary is the service's local cache storage;
a checksum detects corruption, not a malicious actor able to rewrite both data
and checksum.

Snapshot identity includes the exact Git revision, SysML project and commit,
API endpoint digest, complete revision-binding digest (including kernel
bindings), ontology identity, explicit semantic authority identity, and cache
format. Revision gates run before lazy snapshot access. Requests for other
project/commit pairs cannot consume or overwrite the bound snapshot.
Old formats and mismatched identities are cache misses, not migrations.
Malformed entries, duplicate identities, checksum failure and count mismatch
also cause a miss and an exact API retrieval. Structural checks do not establish
independent corpus completeness; the authoritative retrieval remains the source.

Writers use unique temporary files and atomic file replacement. Data and
checksum are separate replacements: concurrent writers or interruption can
produce a checksum mismatch, which safely causes a new API fetch. A repository
lock prevents concurrent first calls in one process from duplicating retrieval;
there is no cross-process download coalescing.

## What this improves—and does not

- Valid snapshot after a process restart: no full-corpus API listing.
- Ask snapshot hit: impact and binder reuse the hydrated repository.
- Truly new revision, invalid snapshot or empty cache: still requires the first
  full download. This change does not accelerate the API server itself.
- Changing the deployment's project/commit or authority identity intentionally
  invalidates reuse. Existing snapshots use an older format and miss once.
- No production restart, deployment, client rebinding, readiness-policy change,
  or new MCP tool is part of this implementation.

## Verification

`tests/test_semantic_corpus_cache.py` includes a real stdio MCP regression:
start the entrypoint against a counting HTTP fixture, call status and impact,
then restart it using the same cache. The first process performs one complete
listing; the second performs zero additional listings and returns identical
status and impact payloads. Handshake itself performs zero listings.

The focused cache, Ask, MCP and deployment test group passed locally: 104 tests.
These are correctness and request-count results, not a production latency claim.
A retained-corpus local benchmark measured 0.77 seconds to decode JSON and
1.59 seconds for loopback transfer; it does not simulate production JVM/database
cost or prove a deployed first-call latency. Production before/after timing
remains required after review and an explicitly authorized rollout.
