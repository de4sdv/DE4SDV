# Retained PLE-S scope-alignment evidence

This directory retains the small receipt of one licensed scope-alignment run
and the comparison the oracle produced from it. It is a **retained** record,
distinguished from fresh evidence: fresh evidence is the artifact of a run on
the exact head under review, which only a licensed run of
`.github/workflows/privileged-ple-scope-alignment.yml` produces; a retained
record is a byte-exact copy of such an artifact, kept because artifacts expire.

**Status: retained, bound to its own revision; historical once those files
move.** The record is verified against the files of the commit that last
changed this directory (`git log -1 -- <this directory>`), which CI extracts
from Git history; it is never verified against the working tree. A later change
to the PLE-S model, the evaluator, the governed scope, the scope validator, the
shared-asset superset, the catalogue or the configurator does not fail CI: it
makes this record historical. A pull request that changes the record itself
must make it consistent at its own commit. (Owner decision, 2026-10-16: the
retained record does not gate production pull requests.)

## What is retained

| File | Origin | Role |
|---|---|---|
| `receipt.json` | `receipt.json` of the artifact | the PLE-S receipt: executor identity, verified input digests, the evaluation (features, bindings, configurations, common assets, the known representation difference) and the non-claims |
| `governed-scope-validation.json` | `governed-scope-validation.json` of the artifact | the governed-scope validation the receipt records by digest: the admitted alternatives and the common, derived, reference-only, deferred and excluded sets with their element ids |
| `comparison.json` | produced by `scripts/compare_ple_scope_alignment.py --evidence retained` on this receipt | the classified comparison of the operational path with the scope alignment; the table in [`ple-s-scope-alignment.md`](../ple-s-scope-alignment.md) renders it |
| `manifest.json` | this record | the identity and digests that bind the three files to the run, the artifact and the merge tree, and the binding rule above |

The serialized element export of the run (`scope-alignment-elements.json`,
1.1 MB) is not retained; `manifest.json` records its digest, which the receipt
also carries, so a copy can be verified. Offline replay of the evaluation needs
that export (`scripts/run_ple_scope_alignment.py --replay`), not this record.

## Identity

- Run `38788579272` of `.github/workflows/privileged-ple-scope-alignment.yml`
  on the head `7e895252ce2b3b3d5d404d2176cc7872b7f671e3` of pull request #376.
  That head's tree is identical to the merge `606141c80ad83b320a88fd2644f23558cf4fdb8b`
  on main (the squash merge changed the commit, not the tree);
  `tests/test_ple_scope_alignment_oracle.py` verifies the merge commit's tree
  from Git, and the pull-request head's where its ref is reachable.
- Artifact `ple-scope-alignment-7e895252ce2b3b3d5d404d2176cc7872b7f671e3-38788579272`,
  expiring on 2026-11-14 (30-day retention). The receipt in this directory is
  the artifact's `scope-alignment/receipt.json`, byte for byte.
- The receipt says `qualified: false`, `adoption_authorized: false` and
  `authority_activation_authorized: false`; so does the comparison.
- `comparison.json` is content-addressed: it carries the digests of the
  catalogue, the configurator, the shared-asset superset, the correspondence
  and the oracle script it was produced with. Its `oracle.executor_revision`
  is the pull-request commit it was produced at and is informational; after
  the squash merge that commit is not on main, and the content digests are
  authoritative. The reproduction ignores the oracle's own identity fields
  (`executor_revision`, `executor_source_dirty`, `tree_source`, `script`,
  `script_sha256`) and compares everything else.
- The digests of the generated probes (`operational_input.sha256`,
  `provenance.bill_of_features_sha256` of the generated rows) depend on the
  YAML emitter: the probes are written with `yaml.safe_dump(..., sort_keys=False)`.
  CI pins `PyYAML==6.0.2`; reproduce with that version.

## How the record stays honest

- `scripts/compare_ple_scope_alignment.py` refuses a receipt as soon as the
  PLE-S model, the evaluator, the governed-scope validator, the governed scope
  source or the shared-asset superset of the tree it is compared with differ
  from the digests the receipt recorded. That is the rule for a fresh
  comparison and for any comparison against a working tree.
- `tests/test_ple_scope_alignment_oracle.py` reproduces `comparison.json`
  from `receipt.json` at every CI run against the files of this record's
  revision (extracted with `git archive`), checks the digests in
  `manifest.json`, and fails, never skips, when the history is missing: every
  workflow that runs it checks out with full history (`fetch-depth: 0`).
- Nothing here is fresh evidence for a later head. The licensed workflow
  produces the fresh comparison of each head in its own artifact; this record
  is the evidence of the run it names.

## How to verify by hand

```bash
revision=$(git log -1 --format=%H -- docs/product-line-engineering/ple-s-scope-alignment-evidence)
mkdir -p /tmp/ple-s-record && git archive "$revision" | tar -x -C /tmp/ple-s-record
python scripts/compare_ple_scope_alignment.py \
  --root /tmp/ple-s-record --revision "$revision" \
  --receipt /tmp/ple-s-record/docs/product-line-engineering/ple-s-scope-alignment-evidence/receipt.json \
  --governed-scope /tmp/ple-s-record/docs/product-line-engineering/ple-s-scope-alignment-evidence/governed-scope-validation.json \
  --evidence retained --run-id 38788579272 \
  --artifact ple-scope-alignment-7e895252ce2b3b3d5d404d2176cc7872b7f671e3-38788579272 \
  --out /tmp/ple-s-record-check/out
```

## How to refresh

Two paths, depending on what changed.

**Licensed refresh** (the PLE-S model, the evaluator, the governed scope, the
scope validator or the shared-asset superset changed; the receipt no longer
describes the tree):

1. Run the privileged scope-alignment workflow on the head to retain (it runs
   on pull requests that touch the scope-alignment paths, or on maintainer
   dispatch with that head as `ref`).
2. Download its artifact; copy `scope-alignment/receipt.json` and
   `scope-alignment/governed-scope-validation.json` here unchanged.
3. Continue with the lighter path below, with the new run id, head and
   artifact name.

**Lighter refresh** (only the catalogue, the configurator, the correspondence
or the oracle script changed, or the oracle's classification of a retained
case changed): no licensed run; the retained receipt still describes the tree.

1. From a clean checkout, run `python scripts/compare_ple_scope_alignment.py
   --receipt <receipt> --governed-scope <validation> --evidence retained
   --run-id <run> --artifact ple-scope-alignment-<head>-<run> --out
   <directory outside the repository>` and copy its `comparison.json` here.
2. Update `manifest.json`: `run_id`, `executor_revision`, `artifact_name`,
   `artifact_expires_at`, `artifact_size_bytes`, the three `files` digests,
   `elements_export.sha256` (from the receipt's `artifact_sha256`) and
   `tree_identical_to` (after a licensed refresh the merge commit is known
   only once the pull request is merged; until then name the pull-request
   head and its tree, and update the entry in the merging pull request).
3. Update the test constants in `tests/test_ple_scope_alignment_oracle.py`:
   `EXECUTOR` (the head of the licensed run), `MERGE` (the merge commit whose
   tree equals it) and `RUN_ID`; the artifact name derives from them.
4. Replace the classified table in `ple-s-scope-alignment.md` with the
   oracle's `comparison.md` (its first line is the identity line the test pins:
   run id and executor revision must appear in the document), and update the
   run id and head in the prose of this README and of the record document.
5. Commit the record, the manifest, the test constants and the document in
   one commit: CI verifies the record at that commit.
