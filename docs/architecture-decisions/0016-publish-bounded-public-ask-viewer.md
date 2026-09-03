# ADR 0016: Publish Ask-model as a bounded interactive viewer

## Status

Proposed

## Context

The public model viewer is a static site. It can publish model pages and viewer
assets, but it cannot run the Python `/ask` endpoint. The Ask-model capability
therefore works locally while the public viewer correctly rejects `POST /ask`.

Making `/ask` public introduces concerns that do not exist for static browsing:

- every accepted question can consume a shared inference budget;
- model answers must remain grounded in the deployed, revision-bound model;
- the inference credential must never reach a browser;
- arbitrary clients must not receive an unbounded public inference proxy;
- reviewers need machine-readable evidence of both the viewer application
  revision and the model revision used for semantic grounding.

The existing public Systems Modeling API already provides the validated model
binding and an internal container network behind the TLS proxy.

## Decision

Operate `ask.de4sdv.org` as a separate, experimental interactive viewer on the
existing deployment host. Keep `viewer.de4sdv.org` as the static browse-only
viewer.

The interactive hostname serves the viewer and `/ask` from the same origin. The
browser never receives the inference key. The Ask service reaches the Systems
Modeling API only through the internal container network and mounts the
revision binding read-only.

### Identity contract

Two revisions are reported separately at `/ask-status.json`:

- **application revision** — the exact Git revision containing the viewer and
  Ask server code;
- **model revision** — the exact Git revision in the deployed semantic binding.

The application revision may be newer than the model revision only when Git
proves that no governed model source or ontology file changed between them.
The container refuses startup on a revision mismatch, non-ancestor binding, or
model/ontology drift. A code-only viewer release therefore does not require a
new model ingestion.

### Abuse and cost controls

The public boundary applies all of these controls:

- same-origin `POST /ask`; missing or different `Origin` is rejected;
- request bodies capped at 16 KiB and questions capped by the application;
- three Ask requests per remote host per minute;
- sixty Ask requests globally per hour;
- one hundred twenty Ask requests globally per day;
- one in-flight inference call in the application; additional calls receive
  `429` rather than queueing indefinitely;
- no direct host port for the Ask container;
- non-root, read-only container with all Linux capabilities dropped;
- one externally executed live grounded query after deployment.

These controls bound casual abuse and cap accepted public requests per day.
They do not turn anonymous inference into an exact monetary limit because
request token sizes vary. A scheduled GET-only monitor verifies availability,
semantic readiness, model identity, and that the deployed application revision
remains on `main`; it does not consume inference quota. The service remains
experimental and the owner may disable it immediately if usage or cost becomes
abnormal.

### Deployment contract

Deployment is manual and protected by the existing production environment. It
requires one exact application SHA on `main`, an owner-verified SSH host key,
the inference key in an environment secret, and DNS already resolving the Ask
hostname to the production host.

The workflow transfers an exact Git bundle and a root-readable service env
file. It starts the Ask container, waits for semantic warmup to report `ready`,
validates the proxy configuration, and only then exposes the route. External
verification checks TLS, application/model identity, structured answer assets,
method rejection, Origin enforcement, and one live API-grounded answer. A
failure restores the prior source checkout and proxy configuration.

## Alternatives considered

### Add cross-origin `/ask` to the static viewer

Rejected. It requires a separate API origin, CORS policy, and client endpoint
configuration while still needing the same dynamic service and abuse controls.
It couples the zero-cost static viewer to a paid backend without improving the
trust boundary.

### Replace the static viewer with the dynamic service

Rejected for the first deployment. It removes the stable browse-only fallback
and makes every public viewer visit depend on the single deployment host.

### Expose `/ask` anonymously without global limits

Rejected. Per-IP limits alone do not bound aggregate traffic or shared account
cost.

## Consequences

- Contributors retain a stable public browse path even if Ask-model is paused.
- Public answers are revision-bound and the application/model distinction is
  visible rather than implied.
- The deployment host gains one small Python service and one persistent
  semantic snapshot volume.
- The project accepts a brief proxy recreation during deployment and a
  single-host availability model.
- DNS creation, production secret installation, workflow approval, and the
  first public deployment remain explicit owner actions.
