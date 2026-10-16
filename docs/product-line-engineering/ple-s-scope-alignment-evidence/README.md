# Retained PLE-S scope-alignment evidence

This directory retains the small receipt of one licensed scope-alignment run
and the comparison the oracle produced from it. It is a **retained** record,
distinguished from fresh evidence: fresh evidence is the artifact of a run on
the exact head under review; a retained record is a byte-exact copy of such an
artifact, kept because artifacts expire, and bound to the tree by the content
digests it carries, not by a revision.

## What is retained

| File | Origin | Role |
|---|---|---|
| `receipt.json` | `receipt.json` of the artifact | the PLE-S receipt: executor identity, verified input digests, the evaluation (features, bindings, configurations, common assets, the known representation difference) and the non-claims |
| `governed-scope-validation.json` | `governed-scope-validation.json` of the artifact | the governed-scope validation the receipt records by digest: the admitted alternatives and the common, derived, reference-only, deferred and excluded sets with their element ids |
| `comparison.json` | produced by `scripts/compare_ple_scope_alignment.py --evidence retained` on this receipt | the classified comparison of the operational path with the scope alignment; the table in [`ple-s-scope-alignment.md`](../ple-s-scope-alignment.md) renders it |
| `manifest.json` | this record | the identity and digests that bind the three files to the run, the artifact and the merge tree |

The serialized element export of the run (`scope-alignment-elements.json`,
1.1 MB) is not retained; `manifest.json` records its digest, which the receipt
also carries, so a copy can be verified. Offline replay of the evaluation needs
that export (`scripts/run_ple_scope_alignment.py --replay`), not this record.

## Identity

- Run `38788579272` of `.github/workflows/privileged-ple-scope-alignment.yml`
  on the head `7e895252ce2b3b3d5d404d2176cc7872b7f671e3` of pull request #376.
  That head's tree is identical to the merge `606141c80ad83b320a88fd2644f23558cf4fdb8b`
  on main (the squash merge changed the commit, not the tree), which
  `tests/test_ple_scope_alignment_oracle.py` verifies from Git.
- Artifact `ple-scope-alignment-7e895252ce2b3b3d5d404d2176cc7872b7f671e3-38788579272`,
  expiring on 2026-11-14 (30-day retention). The receipt in this directory is
  the artifact's `scope-alignment/receipt.json`, byte for byte.
- The receipt says `qualified: false`, `adoption_authorized: false` and
  `authority_activation_authorized: false`; so does the comparison.

## How the record stays honest

- `scripts/compare_ple_scope_alignment.py` refuses this receipt as soon as the
  PLE-S model, the evaluator, the governed-scope validator, the governed scope
  source or the shared-asset superset in the tree differ from the digests the
  receipt recorded. A change to any of them needs a new licensed run and a new
  retained receipt; the comparison cannot be refreshed from a stale one.
- `tests/test_ple_scope_alignment_oracle.py` reproduces `comparison.json`
  from `receipt.json` at every CI run (ignoring only the oracle's own
  executor revision, which the content digests replace) and checks the
  digests in `manifest.json`. A stale retained comparison fails CI.
- Nothing here is fresh evidence for a later head. The licensed workflow
  produces the fresh comparison of each head in its own artifact; this record
  is the evidence of the run it names.

## How to refresh

1. Run the privileged scope-alignment workflow on the head to retain (it runs
   on pull requests that touch the scope-alignment paths, or on dispatch).
2. Download its artifact; copy `scope-alignment/receipt.json` and
   `scope-alignment/governed-scope-validation.json` here unchanged.
3. Run `python scripts/compare_ple_scope_alignment.py --receipt <receipt>
   --governed-scope <validation> --evidence retained --run-id <run>
   --artifact ple-scope-alignment-<head>-<run> --out <directory outside the
   repository>` and copy its `comparison.json` here.
4. Update `manifest.json` (run, head, artifact, expiry, digests, tree) and the
   table in `ple-s-scope-alignment.md` from the oracle's `comparison.md`.
