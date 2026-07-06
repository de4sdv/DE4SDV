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

Superseded by [ADR 0007](0007-example.md)
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

## Template

Use [`TEMPLATE`](TEMPLATE.md) for new ADRs.
