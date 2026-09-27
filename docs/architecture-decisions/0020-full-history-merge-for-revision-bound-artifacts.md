# ADR 0020: Use full-history merge commits for revision-bound artifact delivery

## Status

Proposed

## Context

DE4SDV generated artifacts bind to a `binding.source_revision` that repository
gates validate by commit existence, ancestry of the checked-out revision, and
per-input byte equality. The repository currently keeps linear history and
squash-merges every pull request (GOVERNANCE.md). Under squash, any commit that
exists only on a pull request branch disappears from `main` ancestry, so every
artifact binding that references such a commit fails after the merge.

The consequence was demonstrated during O4 recovery. The PR #305 artifact chain
bound 13 artifacts to its own branch commits (A1–A8). Squash-merging #305
orphaned every one of those commits and required a three-PR recovery cascade
(#308, #309, #310) with two transiently red `main` states, each PR re-binding
one layer of the chain. This cascade is not incidental: any pull request that
regenerates revision-bound artifacts against inputs it itself changes will
require post-merge recovery under squash-only delivery.

### Simulation evidence (2026-09-27, isolated clone; simulated commits are not permanent provenance)

The real #305 chain tip `104ee52f0546e38a88acc3cda6b1079f3766441c` was merged
into its real base `3ac28f9c9f0615ab104bdcd8a7b340dcd63c9636` with a
full-history merge commit (parents `3ac28f9`, `104ee52f`), producing simulated
commit `910256d0c67e7e0bf866948920e8f6f5fb6c4b10`.

| Check | Squash (actual `f64620c`) | Full-history merge (simulated `910256d`) |
| --- | --- | --- |
| `scripts/check_repo.py` | **exit 1**, 7 lane failures | **exit 0** |
| Artifact bindings failing ancestry | **13 of 13** | **0 of 13** |
| O3 scope `--check` | fails (bindings dead) | **exit 0** |
| Merge tree vs chain-tip tree | n/a | **byte-identical** (`git diff --exit-code 910256d 104ee52f` empty) |
| Recovery PRs required after merge | **3** (#308–#310) | **0** |
| Full test suite | (post-recovery only) | **2582 passed, 4 skipped, 137 subtests** at the merge commit (log: `merge-sim-pytest-rerun.log`) |

The merged tree is identical to the reviewed chain tip; only ancestry topology
differs. All existing gates (binding ancestry, byte-equality, scope, full
suite) accept the merge topology without modification. A first suite run in
the simulation clone showed six failures in the O3 readiness tests; these were
reproduced as a clone-environment artifact (the clone's `origin/main` ref
pointed at an old commit lacking `de4sdv/semantic/kernel_binding_index.py`
rather than at the simulated merged main) and disappeared when `origin/main`
was set to the merge commit, after which the full suite passed. No test
encodes a squash-only or linear-history assumption. The content-addressed
alternatives were not required to achieve this result.

### Branch-protection compatibility

Current repository settings block this method: `allow_merge_commit: false`,
`required_linear_history: true`. Enabling full-history merging requires
administrator settings changes and a governance text update; no code, schema,
or gate change is required.

## Decision

Adopt full-history merge commits as the delivery method for pull requests that
introduce or regenerate revision-bound artifacts whose bindings reference
commits created on the pull request branch. Squash-merge remains permitted for
pull requests without such bindings. Migration procedure:

1. Administrator updates repository settings: enable merge commits, disable
   the linear-history requirement (settings and branch-protection changes are
   administrator-only).
2. GOVERNANCE.md replaces "the history is kept linear; pull requests are
   squash-merged as one commit" with the two-method rule of this ADR, keeping
   review, status-check, force-push, and branch-deletion requirements
   unchanged.
3. Contributor guidance adds: artifact-bearing branches must not be rebased
   after any binding references a branch commit (history rewrite would orphan
   it); merge `main` into the branch if synchronization is needed. Bindings may
   reference branch commits; after a merge commit those commits are permanent
   ancestors of `main`, and the existing ancestry gate continues to enforce
   existence and reachability.
4. Non-normative module and generator docstrings that describe "squash-only
   linear history" are refreshed in a small follow-up documentation change.
5. After each merge, verification continues to run: repository gates, scope
   `--check`, and the whole-chain verifier on the new permanent `main`.

Rollback: re-enabling the previous settings restores squash-only delivery with
the existing recovery-cascade behavior; no artifact regeneration is needed to
roll back.

## Consequences

- Eliminates post-merge recovery cascades for revision-bound artifact work
  (three recovery PRs and two red-main intervals avoided in the #305 case).
- `main` history becomes non-linear. Commit identity of merged branches
  persists permanently instead of being rewritten to a single squash commit.
- Permanent provenance rule clarification: a `source_revision` must be a
  commit that remains permanently reachable from `main`. Under squash-only
  delivery, only squash commits qualify, and branch commits are categorically
  inadmissible; under full-history merging, merged branch commits remain
  permanently reachable and are therefore admissible. The mechanical gates are
  unchanged; the governance wording that discouraged feature-branch revisions
  was written for the squash-only setting and is superseded by this ADR.
- Review practice is unchanged: required checks, independent review, and the
  bounded administrator-exception path continue to apply.

## Non-decisions

- Content-addressed revision bindings (hashing the input set instead of naming
  a commit) remain a future alternative if linear history ever becomes a hard
  requirement. Not needed for the goals of this ADR.
- Delegated or automated merge execution is a separate proposal (ADR 0021).
- The merge method for non-artifact pull requests (squash retained).

## Links

- Recovery chain: PR #305 (`f64620c`), #308 (`04a5775`), #309 (`c26ee2f`),
  #310 (`3783214`).
- Rehearsal and simulation outputs:
  `~/.hermes/outputs/o4-merge-governance/` (simulated commit
  `910256d`, bindings audit, squash contrast log, full-suite log).
- GOVERNANCE.md merge-policy section; `scripts/check_repo.py` binding gates;
  whole-chain verifier `scripts/verify_generated_chain.py`.
