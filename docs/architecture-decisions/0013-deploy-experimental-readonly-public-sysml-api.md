# ADR 0013: Deploy the validated full-model API as a read-only public service

## Status

Proposed

## Context

PRs #171–#174 established a revision-bound, ontology-anchored semantic layer
over the SysML v2 API repository:

- ADR 0010 — revision-bound semantic queries;
- ADR 0011 — official full-model export/import with validated bindings;
- ADR 0012 — read-only MCP exposure with the complete semantic authority tuple
  (Git SHA + SysML project/commit + ontology path/SHA-256).

The reviewed DE4SDV baseline is therefore machine-queryable through the standard
Systems Modeling REST/HTTP API — but only inside the privileged workflow and on
machines where a validated import has been run. Contributors, reviewers, and the
upcoming DE4SDV progress publication need a public, read-only view of the real
56,745-element model without cloning the repository or running the importer.

The public surface must not weaken any established boundary:

- the DE4SDV GitHub repository remains the reviewed change-control authority;
- the deployed API state must correspond to one exact validated Git revision;
- no public mutation is acceptable;
- the upstream pilot implementation (Systems-Modeling/SysML-v2-API-Services) is
  experimental software and must not be presented as a production OMG service.

## Decision

DE4SDV operates `sysml-api.de4sdv.org` as an **experimental read-only public
Systems Modeling API** over the pinned pilot implementation, behind a read-only
reverse proxy, with the following contract.

### Topology

```text
Internet
  | HTTPS only (Let's Encrypt, automatic renewal)
  v
Caddy reverse proxy (read-only; 80/443 published)
  | HTTP over internal Docker network only
  v
Pinned Systems Modeling API service (container, no published ports)
  | internal network only
  v
PostgreSQL 16 (container, no published ports)
```

Only the proxy publishes ports (80/443). The API and database are reachable
solely on the internal compose network; host firewall allows 22/80/443 only.

### Read-only enforcement

- POST/PUT/PATCH/DELETE are rejected at the proxy with 405 before any byte
  reaches the API service. OPTIONS is allowed for CORS-preflight/Discovery.
- The API container exposes no ports to the host or Internet; ingestion into
  the database happens server-side through the validated importer path
  (ADR 0011), never through the public interface.
- MCP remains stdio-only. This increment deliberately does NOT host a public
  remote MCP endpoint; clients that want MCP clone the repository and point it
  at the public API.

### Baseline identity and fail-closed deployment

A fresh deployment always imports the validated privileged export into the
deployment's own API repository through the existing DE4SDV importer. The
deployment repository generates its own Project/Commit UUIDs; the privileged
CI run's ephemeral UUIDs are never copied. The deployment binding and the
public status tuple carry the deployment-specific identities together with
the same Git SHA, export digest, and ontology identity validated by the
privileged run. Immutable evidence (element count, internal reference count,
source-document count) must match between the privileged report and the
deployment import; a mismatch refuses the deployment.

A deployment is only valid when the complete ADR 0012 semantic authority tuple
holds for the served state:

```text
Git SHA + SysML project UUID + SysML commit UUID + ontology path/SHA-256
```

The deployment workflow (manual `workflow_dispatch`) refuses to run for PR
heads, requires a green privileged full-model run for the exact SHA, downloads
that run's artifact bundle, and the host-side deploy script fails closed unless:

- the bundle contains export, binding, semantic validation report, query
  coverage, and MCP validation for one Git SHA;
- the deployment host's repository HEAD equals the bundle Git SHA (and is
  clean);
- the semantic report is passed with zero unresolved/ambiguous ontology
  bindings and its recorded export digest matches the bundle bytes;
- the binding is `passed`/`full-model` with an exact ontology identity;
- the MCP validation artifact records the same complete tuple;
- the deployment import completes with a clean ontology summary before the
  proxy is (re)pointed at it.

On any mismatch the deployment is refused before the proxy stage. This is a
single-host stack without a blue/green switch: a redeploy restarts the stack
and causes an interruption; the guarantee is "refused before exposure", not
"running service untouched". A machine-readable `/deployment-status.json`
(served by the proxy) publishes the served Git SHA, the deployment-specific
project/commit UUIDs, ontology digest, deployment timestamp, element count,
and experimental/read-only status — with no secrets and no internal
filesystem paths.

### Restart safety and pins

The pinned upstream stores its DB config in `persistence.xml` with
`hbm2ddl.auto=create-drop`, which destroys all model data at every shutdown —
correct for a CI test fixture, fatal for a service. The deployment image applies
one minimal, documented config patch (`create-drop` → `update`, SQL logging
off). Nothing else changes: no parser, no schema, no API behavior, no second
semantic store. Database identity is injected at container start; no secret is
baked into any image or repository file.

Pins (exact, verified at build time):

- Systems-Modeling/SysML-v2-API-Services `0af711b1` — the same revision the
  privileged workflow stages;
- `eclipse-temurin:11-jdk-jammy` (builder) and `eclipse-temurin:11-jre-jammy`
  (runtime) by digest;
- `postgres:16-alpine` by digest;
- Caddy: digest-pinned `caddy:2.8.4-builder-alpine` / `caddy:2.8.4-alpine`
  stages built with xcaddy and `github.com/mholt/caddy-ratelimit` pinned to
  `b8d8c9a9d99ee352d675cbbe416ec2b489fc8cab` (stock Caddy images lack the
  `rate_limit` directive; see `deployment/caddy/Dockerfile` for the pin
  rationale);
- sbt-launch 1.2.8 by SHA-256.

### Known limitation (documented, not solved here)

The pinned pilot implementation has no server-side QueryService/ElementNavigation
path that avoids serializing large result sets; the public deployment inherits
the full-model cold-fetch behavior measured during PR #174 (one page is fast;
repeated complete-model pagination is expensive server-side). Public read-only
traffic is bounded by rate limiting and request-size limits. Fixing this
properly requires upstream QueryService work (see follow-ups), not a duplicate
semantic graph on top of the deployment.

## Consequences

- The reviewed baseline becomes publicly browsable through the standard
  Systems Modeling API with exact element UUIDs and relationships preserved.
- The public surface is read-only by construction (proxy method filter + no
  exposed write path + no public MCP).
- Future main revisions deploy by re-running the manual workflow for the new
  SHA after its privileged validation is green; nothing deploys automatically.
- The public status document makes the served revision auditable at a glance.

## Non-goals

- No authentication on the public read endpoint (nothing to protect beyond
  read-only model content; rate limiting handles abuse).
- No public remote MCP endpoint in this increment.
- No QueryService/indexing redesign in this increment.
- No deployment of arbitrary PR heads, ever.

## Standards follow-ups (documented, deliberately not implemented here)

1. **Persistent DE4SDV Project with chronological API commits** — deploy one
   long-lived API project whose commits grow with each imported baseline,
   instead of one isolated project per deployment, so API consumers can diff
   revisions.
2. **DataIdentity/DataVersion continuity** — preserve element identity across
   commits as the API lifecycle model intends, enabling change queries between
   baselines.
3. **Server-side QueryService / ElementNavigationService** — avoid forcing
   clients to retrieve the complete 56k-element model; requires upstream pilot
   capability work and evaluation, not a DE4SDV-local workaround.
4. **ExternalData / ExternalRelationshipService evaluation** — assess the API's
   own extension points before introducing any separate federated engineering
   knowledge graph.

## Links

- [Revision-bound semantic queries (ADR 0010)](0010-bind-semantic-impact-queries-to-api-revisions.md)
- [Full-model API import (ADR 0011)](0011-import-reviewed-sysml-baseline-into-api.md)
- [Read-only MCP exposure (ADR 0012)](0012-expose-revision-bound-semantic-reads-through-mcp.md)
- [SysML API integration guide](../../sysmlv2-api/README.md)
- Deployment assets: [`deployment/`](../../deployment/)
