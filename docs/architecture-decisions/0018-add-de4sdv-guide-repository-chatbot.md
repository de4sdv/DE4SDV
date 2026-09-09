# ADR 0018: Add DE4SDV Guide, a repository-grounded viewer chatbot

## Status

Proposed

## Context

The public viewer (viewer.de4sdv.org) offers one assistant capability:
"Ask the model", reachable through the element context menu. It answers
questions about a single, explicitly selected model element, grounded in
the authoritative `.sysml` source and the method layer.

Newcomers face a different problem. The repository carries substantial
orientation material (README files, `docs/`, architecture decision
records, CONTRIBUTING guidance, deployment and tooling documentation,
product-line material), but a visitor cannot ask "where do I start?",
"how do I contribute?", or "where do ADRs live?" anywhere on the site.
Element-grounded model Q&A cannot answer repository navigation questions
by design.

Two failure modes must be avoided when adding a repository assistant:

1. Blurring authority. A generated assistant that answers freely would
   drift into reinterpreting requirements, model semantics, or
   compliance claims. The repository's rule is that implementation
   claims must reflect the SysML models; a chat answer must not become a
   shadow authority.
2. Doubling the deployment stack. A second service would need its own
   container, credentials, rate limiting, and review burden.

## Decision

Add **DE4SDV Guide** as a second, separate viewer capability on the same
`ask-viewer` service:

- A floating, minimized-by-default chat panel on every viewer page with
  expand/minimize, a clear/new-chat control, newcomer starter questions,
  and client-side-only state (no server-side user memory or accounts).
- A separate endpoint, `POST /api/repo-chat`, implemented in
  `tools/sysml_html_viewer/repo_guide.py`. It does not route through Ask
  the model and never queries the Systems Modeling API.
- Retrieval is a deterministic SQLite FTS5 index built over the exact
  deployed Git checkout. Indexable material: `.md`, `.py`, `.sysml`,
  `.yaml`/`.yml`. Excluded: `.git` and other VCS/dependency/build/cache
  directories, secrets and environment files (name-based rules),
  binary/generated artifacts including generated SVGs. Chunks carry
  repository path plus exact line ranges as provenance.
- The LLM receives only the question plus the retrieved repository
  context. When no trustworthy repository context matches, the endpoint
  fails with a "no trustworthy repository context" error instead of
  answering.
- Answers return source references rendered by the UI as GitHub links
  pinned to the deployed application Git SHA, plus the SHA itself.
- The proxy gains a `/api/repo-chat` route mirroring the `/ask`
  hardening (POST-only, 16 KiB body limit) with an independent
  rate-limit budget so the two capabilities cannot consume each other's
  spend.

The authority boundary is explicit in code, the system prompt, the UI,
and the documentation: DE4SDV Guide is a generated repository and
documentation assistant, not an engineering or model authority. Ask the
model remains the element-grounded model capability and is unchanged.
Neither capability falls back to the other.

Ask the model and the Systems Modeling API are not modified by this
decision.

## Consequences

Positive:

- Newcomers get a grounded path into the repository from the public
  viewer, with citations back to the exact deployed revision.
- The repository checkout becomes the retrieval corpus for V1 without a
  vector database, keeping the stack single-container and reviewable.
- Independent rate-limit budgets make operating cost of each capability
  separately attributable and stoppable.

Negative and follow-up work:

- The retrieval index is English-text FTS; questions phrased far from
  the repository vocabulary can miss. The refusal path covers this, but
  retrieval quality needs monitoring after rollout.
- Index building is lazy on first use; the first Guide question after a
  redeploy pays a one-time build cost.
- FTS matching is not semantic matching. If repository questions
  routinely fail retrieval, a follow-up ADR should evaluate alternatives
  rather than weakening the refusal gate.

## Non-decisions

- This ADR does not change Ask the model, the Systems Modeling API, the
  semantic MCP layer, or the deployment workflow.
- It does not introduce user accounts, server-side conversation memory,
  or analytics.
- It does not decide a vector-database or embedding-based retrieval
  path.
- It does not authorize a production deployment; the merged change is
  deployed only through the existing gated workflow.

## Links

- ADR 0016: Publish bounded public ask viewer (the deployment surface
  this capability shares).
- ADR 0017: Separate engineering authority from agent context (the
  authority principle applied here).
- `tools/sysml_html_viewer/README.md` — capability comparison.
- `docs/guides/model-viewer.md` — user-facing explanation.
- `deployment/README.md` — proxy route and operational controls.
