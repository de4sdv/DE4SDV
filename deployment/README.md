# Public deployment: sysml-api.de4sdv.org

## DE4SDV Experimental Read-Only Systems Modeling API

This directory contains the complete, reproducible deployment for serving the
validated DE4SDV full-model SysML v2 baseline through the standard Systems
Modeling REST/HTTP API at `https://sysml-api.de4sdv.org`.

See [ADR 0013](../docs/architecture-decisions/0013-deploy-experimental-readonly-public-sysml-api.md)
for the decision, the fail-closed rules, and the standards follow-ups.

## What is served

- The pinned pilot Systems Modeling API implementation
  (Systems-Modeling/SysML-v2-API-Services `0af711b1`), the same revision the
  privileged DE4SDV full-model workflow validates.
- One exact validated Git revision of the DE4SDV baseline (56,745 API elements
  at the time of the first deployment), preserving exact SysML element UUIDs.
- Swagger/OpenAPI documentation from the implementation at `/docs`.
- A machine-readable status document at `/deployment-status.json` with the
  served Git SHA, SysML project/commit UUIDs, ontology SHA-256, deployment
  timestamp, and read-only/experimental status.

## What is blocked (by design)

- POST, PUT, PATCH, DELETE → rejected 405 at the reverse proxy.
- Any direct network path to the API or PostgreSQL (no published ports).
- Remote MCP endpoints (MCP stays stdio; clone the repo and point it here).

## Layout

```text
deployment/
  compose.yaml                  three-service stack (caddy, sysml2-api, postgres)
  sysml2-api/Dockerfile         pinned upstream + restart-safety config patch
  sysml2-api/conf/…             production config layer
  sysml2-api/docker-entrypoint.sh
  caddy/Caddyfile               TLS, method filter, limits, status doc
  scripts/provision-server.sh   one-time host provisioning (Docker, ufw, secrets)
  scripts/deploy.py             fail-closed validated deployment (host-side)
  scripts/verify_public_api.py  external public verification
  status/                       deployment-status.json (generated at deploy time)
```

## One-time host setup (Hetzner, Ubuntu 24.04)

Performed by the repository owner (requires Hetzner console access):

1. Create the server (CX43 class, x86, IPv4+IPv6, SSH key auth) and note its
   IPv4 address.
2. DNS (Cloudflare, DNS-only/grey-cloud for Let's Encrypt HTTP-01):

   ```text
   sysml-api.de4sdv.org.   IN   A   <SERVER-IPv4>   (proxied: NO / DNS only)
   ```

3. Point SSH at the server and run, as root:

   ```bash
   ACME_EMAIL=<your-email> bash deployment/scripts/provision-server.sh
   ```

   This installs Docker, creates `/srv/de4sdv/sysml2-api.env` (600, generated
   DB password + Play secret), and locks the firewall to 22/80/443.

## Deploying a validated baseline

Prerequisite: a green `Privileged Full-Model API Ingestion` run for the exact
SHA (the workflow uploads `full-model-api-ingestion-<sha>`).

Then run **Deploy Public SysML API** (`workflow_dispatch`) with:

- `git_sha`: the exact 40-hex SHA (must be on `main`);
- `artifact_run_id`: optional, auto-detects the privileged run for that SHA.

The workflow checks out that SHA, refuses PR heads, downloads the validated
bundle, transfers everything to the host, and runs `deploy.py`, which fails
closed on any mismatch (stale export digest, dirty repo, missing ontology
identity, unclean ontology summary, tuple disagreement, unimported model).
Only after the API serves the bound project/commit does it (re)point the
public proxy and write `/srv/de4sdv/status/deployment-status.json`.

## Verifying the public service

```bash
python3 deployment/scripts/verify_public_api.py
```

Proves HTTPS, GET/HEAD/OPTIONS behavior, 405 on all mutation methods, the
status document, the served project/commit against the status tuple, the
known element `reqCommandEmergencyBraking` via its API UUID path, and
full-model pagination (>50,000 elements across pages).

## Secrets hygiene

- DB password and Play secret: generated on the host, stored in
  `/srv/de4sdv/sysml2-api.env` (0600), never in git, never in images.
- GitHub side: only `DEPLOY_SSH_KEY` / `DEPLOY_SSH_HOST` / `DEPLOY_SSH_USER`
  secrets are needed; the Syside license never touches the deployment host
  (exports are produced in the privileged GitHub workflow).
- The status document contains no secrets and no internal paths.

## Restart safety

`restart: unless-stopped` on all three services plus the `create-drop` →
`update` schema patch means the service survives reboots and restarts without
losing the imported model. Schema creation happens once; committed model data
is never dropped.

## Known limitations

- The pilot implementation serializes large result sets server-side; complete
  model pagination is expensive upstream (measured during PR #174). Rate
  limiting bounds abuse; the real fix is upstream QueryService work (ADR 0013
  follow-ups).
- One isolated API project per imported baseline; chronological commits within
  a persistent project is a documented follow-up.
