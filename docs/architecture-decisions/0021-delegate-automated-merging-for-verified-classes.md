# ADR 0021: Delegate automated merging for mechanically verified pull request classes

## Status

Proposed

## Context

DE4SDV is operated by a single administrator account (`@de4sdv`, see
MAINTAINERS.md), and GOVERNANCE.md already defines a bounded exceptional
administrator-merge path for the single-maintainer period. Routine merges that
are mechanically safe — provenance-only recovery rebinds and verified
infrastructure-only changes — currently still require a manual administrator
merge each time. The O4 recovery demonstrated the cost: a proven, rehearsed,
independently reviewed sequence (#305, #308–#310, #306, #307) required a manual
merge checkpoint at every stage even though each stage's safety was
mechanically verifiable.

The administrator wants to delegate routine merges where doing so is
demonstrably safe, without weakening any accepted governance, provenance,
review, or validation requirement.

## Decision

Establish two merge categories and their execution protocol. This ADR does not
activate automated merging; activation requires the administrator's explicit
approval of this policy (Status → Accepted) and a decision on the enabling
mechanism below.

### Category AUTOMATED (eligible for delegated merge)

1. **Provenance-only recovery/rebind pull requests.** The complete diff is
   machine-classified as provenance-only: every changed line is a binding
   `source_revision`, artifact digest, revision/digest field in a scope or
   registry artifact, or a committed-revision test pin. No source, model,
   schema, gate, or semantic payload line changes.
2. **Independently reviewed infrastructure-only changes.** Scripts, tests,
   CI configuration, or tooling documentation that introduce no new semantic
   decisions, no authority activation, no runtime behavior change, and no
   governance change.

### Category ADMINISTRATOR APPROVAL (never automated)

Semantic redesigns; model or authority changes; consequential runtime
changes; security or governance decisions; final authority retirement; any
diff that fails machine classification; anything ambiguous. Default when in
doubt: administrator approval.

### Protocol — every automated merge

1. Exact-head CI green on the pushed head (never an earlier head).
2. Required independent review recorded: bounded verdict with scope, evidence,
   and findings disposition, visible in the pull request.
3. Applicable privileged validation (e.g. licensed Syside) green when the diff
   touches validated model paths.
4. Diff classification recorded: the diff equals the classified set; any
   unexpected path or field immediately disqualifies the pull request.
5. Merge-survival evidence: post-merge topology verified per the governing
   merge method (ADR 0020 when accepted; otherwise squash plus the recovery
   procedure).
6. After merging: capture the actual permanent commit, record it in the pull
   request, and continue the dependent sequence automatically — no manual
   checkpoint between stages of an already-reviewed, mechanically verified
   sequence.

### Hard prohibitions

- Never merge outside the AUTOMATED category.
- Never merge with failing or stale checks, and never bypass any status
  check, validation gate, or protection requirement.
- The review requirement must always be satisfied in exactly one of two
  governed ways: (a) the single-administrator exception already sanctioned by
  GOVERNANCE.md, executed with the full checklist above (Option A), or (b) a
  real approving review by a second reviewer account (Option B). Under no
  circumstance may a merge proceed with neither.
- Never force-push `main`; never modify branch protection, validation gates,
  or repository settings.
- A failed verification or an unexpected diff immediately disables automated
  merging for that pull request and escalates to the administrator.

### Enabling mechanism (administrator decision at approval time)

- **Option A (recommended for the single-account present):** the delegated
  merger executes the existing governed administrator-exception path for the
  AUTOMATED category, with the stricter machine checklist above and full
  evidence recorded in each pull request. No other requirement is bypassed.
- **Option B (strict no-bypass):** a second trusted reviewer account is added;
  automated merges then proceed only when the GitHub review requirement is
  satisfied by that reviewer. Requires a new trusted contributor.

## Consequences

- Routine mechanical merges no longer stop the sequence; administrator
  attention is reserved for the ADMINISTRATOR APPROVAL category.
- Every automated merge remains fully auditable through the pull request
  record: exact head, CI run, review verdict, classification, merge commit.
- Risk: misclassification. Mitigated by fail-closed classification, the
  disable-on-anomaly rule, and administrator spot-checks of the recorded
  evidence.
- Risk: drift in review quality. Mitigated by requiring bounded, exact-head
  independent reviews with recorded verdicts, per the review-integrity
  requirements already used in this repository.

## Non-decisions

- The merge method itself (ADR 0020).
- Changing review requirements, branch protection, or the contributor path.
- Tooling implementation details beyond this protocol; any automation tooling
  is a separate, independently reviewed change after approval.
- Expanding the AUTOMATED category beyond the two definitions above.

## Links

- GOVERNANCE.md (review path; exceptional administrator merges), MAINTAINERS.md.
- ADR 0020 (merge method for revision-bound artifacts).
- Evidence of the merge-checkpoint cost: PRs #305, #308, #309, #310, #306,
  #307 and the O4 recovery outputs.
