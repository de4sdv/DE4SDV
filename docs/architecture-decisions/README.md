# Architecture decision records

DE4SDV uses architecture decision records (ADRs) to capture decisions that
shape project architecture, governance, modeling practice, toolchain choices,
or contributor workflow.

ADRs are historical records. They are not living design documents.

## Status values

Use one of these status values:

- `Proposed`: under review and not yet accepted.
- `Accepted`: accepted as the current project decision.
- `Rejected`: considered and intentionally not adopted.
- `Deprecated`: no longer recommended, but not directly replaced.
- `Superseded by ADR NNNN`: replaced by a later accepted ADR.

Avoid ad hoc variants such as `Draft for review`, `approved`, `active`, or
`implemented`. If the ADR has been merged as the current project decision, its
status should normally be `Accepted`.

## Immutability rule

Once an ADR is accepted, do not rewrite its decision content. If the project
changes direction, create a new ADR and update the old ADR status to point to
the replacement, for example:

```markdown
## Status

Superseded by [ADR 0007](0007-pin-sysmod-sysand-dependency.md)
```

Acceptable edits to accepted ADRs:

- typo, formatting, and broken-link fixes;
- status metadata updates that point to a later ADR;
- clearly marked notes that preserve, rather than rewrite, decision history.

Avoid edits that change the original decision, rationale, context, or
consequences after acceptance. Those changes belong in a new ADR.

## File naming

Use four-digit sequence numbers and a short kebab-case title:

```text
NNNN-short-decision-title.md
```

Example:

```text
0005-define-adr-governance.md
```

## Records

Each record's own Status section is authoritative.

- [ADR 0001: Use a documentation-first project
  scaffold](0001-use-documentation-first-scaffold.md)
- [ADR 0002: Adopt the MBSE4U SYSMOD SysML v2 library as a modeling
  reference](0002-adopt-sysmod-sysmlv2-library.md)
- [ADR 0003: Package COVESA VSS as a draft SysML v2
  library](0003-package-covesa-vss-as-sysmlv2-library.md)
- [ADR 0004: Adopt ASELCM three-system framing for
  DE4SDV](0004-adopt-aselcm-three-system-framing.md)
- [ADR 0005: Use SysML v2 API repository as live model
  store](0005-use-sysml-v2-api-repository-as-live-model-store.md)
- [ADR 0006: SysML v2 variant selection construct and PLE
  adequacy](0006-variant-selection-construct-and-ple-adequacy.md)
- [ADR 0007: Pin SYSMOD as a Sysand dependency behind a DE4SDV
  adapter](0007-pin-sysmod-sysand-dependency.md)
- [ADR 0008: Publish the COVESA VSS SysML v2 library on the Sysand
  Index](0008-publish-covesa-vss-sysand-package.md)
- [ADR 0009: Adopt the ODE4HERA requirements-management attribute library as a
  Sysand dependency](0009-adopt-ode4hera-requirements-attributes.md)
- [ADR 0010: Bind semantic impact queries to SysML API
  revisions](0010-bind-semantic-impact-queries-to-api-revisions.md)
- [ADR 0011: Import the reviewed SysML baseline into the API
  repository](0011-import-reviewed-sysml-baseline-into-api.md)
- [ADR 0012: Expose revision-bound semantic reads through
  MCP](0012-expose-revision-bound-semantic-reads-through-mcp.md)
- [ADR 0013: Deploy the validated full-model API as a read-only public
  service](0013-deploy-experimental-readonly-public-sysml-api.md)
- [ADR 0014: Ratify the initial AEBS product-line
  scope](0014-ratify-initial-aebs-product-line-scope.md)
- [ADR 0015: Noreply commit identity and deferred coordinated history
  rewrite](0015-noreply-commit-identity-and-deferred-history-rewrite.md)
- [ADR 0016: Publish Ask-model as a bounded interactive
  viewer](0016-publish-bounded-public-ask-viewer.md)
- [ADR 0017: Separate engineering authority from agent context and historical
  memory](0017-separate-engineering-authority-from-agent-context.md)
- [ADR 0018: Add DE4SDV Guide, a repository-grounded viewer
  chatbot](0018-add-de4sdv-guide-repository-chatbot.md)
- [ADR 0019: Specify the deterministic method-conformance subsystem (Package
  A)](0019-specify-deterministic-method-conformance-subsystem.md)
- [ADR 0020: Give the remaining ontology definitions model-resident kernel
  homes](0020-give-ontology-definitions-model-resident-kernel-homes.md)
- [ADR 0021: Model elements earn their
  place](0021-make-model-elements-earn-their-place.md)
- [ADR 0022: Adopt PLEML as the product-line
  authority](0022-adopt-pleml-as-product-line-authority.md)
- [ADR 0024: Keep the program in the model, with releases as
  increments](0024-keep-the-program-in-the-model.md)

## Template

Use [`TEMPLATE`](TEMPLATE.md) for new ADRs.
