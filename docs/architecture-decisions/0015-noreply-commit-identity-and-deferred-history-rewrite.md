# ADR 0015: Noreply commit identity and deferred coordinated history rewrite

## Status

Accepted

## Context

Early commit metadata in this public repository exposes a personal email
address through the author/committer fields of historical commits. This ADR
deliberately does not reproduce that address; it is referred to below only as
"the exposed personal address".

Two concerns follow from the exposure:

1. Future commits must not keep adding occurrences of the exposed personal
   address, so the set of commits carrying it stops growing.
2. The already-published occurrences are only removable by rewriting Git
   history, which is a destructive, repository-wide operation.

Rewriting published history would invalidate many reachable commit SHAs. The
repository has substantial infrastructure bound to exact commit SHAs:

- Branch protection on `main` keeps history linear and disables force pushes,
  so any rewrite requires an administrator bypass and coordinated re-cloning
  by every collaborator.
- The semantic API pipeline binds queries to a reviewed Git baseline: commit
  SHAs and their derived SHA-256 ontology identities are the revision
  authority (see ADR 0010 and ADR 0011). A rewrite orphans every recorded
  binding, artifact run, and evidence tuple.
- Deployment is gated on an exact SHA (see ADR 0013); references in issues,
  pull requests, and ADRs would dangle.

## Decision

1. **Project-owned commits use a GitHub-provided noreply identity.** The lead
   maintainer's repository-local Git configuration uses the noreply address
   associated with `@de4sdv` as both author and committer identity. No new
   project-owned commit may carry the exposed personal address; a commit found
   to carry it is amended or superseded before merge. Other contributors remain
   responsible for choosing their own public commit identity.
2. **A coordinated rewrite of published history to remove the exposed
   personal address is deferred.** No rewrite is scheduled now. The rewrite
   may be revisited only when one of these triggers holds:
   - the exposure causes concrete harm (for example harvesting, spam, or
     identity risk);
   - the repository owner explicitly approves a bounded rewrite window after
     reviewing the final ref inventory, mapping, backup, and recovery plan;
   - a planned major repository restructure would in any case reset baseline
     identities.

   A future rewrite must be a coordinated operation: freeze merges, perform
   the rewrite in a single coordinated event, require every collaborator to
   re-clone, rebase or reopen open pull requests, and re-run the full-model
   ingestion pipeline so that all revision bindings are re-established for
   the new SHAs. SHA-based references in issues, pull requests, and ADRs are
   updated where practical and otherwise annotated as pre-rewrite records.

## Consequences

- The exposed personal address remains visible in the published history until
  a coordinated rewrite happens; this is an accepted trade-off of the
  deferral.
- The set of commits carrying the address stops growing from this decision
  onward.
- Existing SHAs remain stable identifiers: the semantic API baseline
  bindings, deployment gates, and evidence trails stay valid without
  re-establishment.
- A future rewrite is expensive and must re-establish every baseline or
  deployment binding whose authority includes a rewritten commit SHA;
  budgeting for that belongs to the decision that triggers it.

## Non-decisions

This ADR does not:

- decide whether or when GitHub private vulnerability reporting is enabled;
- remove occurrences of the address from forks, mirrors, or other copies
  outside this repository;
- publish or change any contact address;
- schedule the history rewrite or pre-authorize it.

## Links

- [ADR 0010: Bind semantic impact queries to API revisions](0010-bind-semantic-impact-queries-to-api-revisions.md)
- [ADR 0011: Import reviewed SysML baseline into API](0011-import-reviewed-sysml-baseline-into-api.md)
- [ADR 0013: Deploy experimental read-only public SysML API](0013-deploy-experimental-readonly-public-sysml-api.md)
- [GOVERNANCE](../../GOVERNANCE.md) — pull request review and merge process
- [ADR README](README.md) — status values and immutability rule