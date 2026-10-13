# Frozen records

The model-built kernel contract still serves 13 identities from six
historical records: the Semantic Projection and API Representation Profile
records v1, v1.1 and v1.2 in [`o2/`](o2/). They were generated from the
authored ontology, which no longer exists, so they can never be regenerated.
They are frozen: pinned by digest and never edited. Their revision bindings
are checked at their own historical revisions, never against the live tree.

The owner froze them on 2026-10-07 together with the other records of the
same migration
([decision record](https://github.com/de4sdv/DE4SDV/blob/release-2026-10-11/docs/method-conformance/o4/owner-decisions-2026-10.md)).
The runtime no longer reads those other records; they are archived at the
[`release-2026-10-11`](https://github.com/de4sdv/DE4SDV/tree/release-2026-10-11)
tag.

## Manifest

[frozen-records.json](frozen-records.json) (`de4sdv.frozen-records/v2`) has no
`binding` block and no top-level `source_revision`, so it is not
revision-bound evidence itself. It records the decision, `frozen_at_revision`
(the `main` commit the freeze was taken from), `historical_directory` (where
the records were at that commit; their own `extends` blocks still name those
paths), `directories`, and one record per file: `path`, `sha256`, `kind`,
`binding_source_revision` and `live_consumer`. Every digest refers to bytes
already on `main`, so the manifest is squash-safe.

## Gate

The frozen lane of `scripts/verify_generated_chain.py`, which
`scripts/check_repo.py` runs, checks fail-closed:

1. The manifest equals its deterministic rendering from the tree at
   `frozen_at_revision`, which must exist and be an ancestor of `HEAD`.
   Re-derive it for review with
   `python scripts/verify_generated_chain.py --render-frozen-manifest <rev>`.
2. The files in the frozen directory equal the record set. Adding or removing
   a file fails, with or without a manifest edit.
3. Each file's bytes match its recorded `sha256`. Editing or regenerating a
   frozen record fails.
4. For a record with a `binding` block: `source_revision` exists and is an
   ancestor of `HEAD`, and every `bound_inputs` entry exists at that revision
   (`git show <rev>:<path>`) with the recorded digest. The working-tree bytes
   of the inputs are not consulted, so a bound input may be edited or deleted
   at `HEAD` without breaking the record.
5. `extends` blocks reference frozen records only, at their frozen digests.

Live projection/profile freshness is a separate check: each generator's check
mode regenerates its output and compares exact bytes.

## Changing a frozen record

Don't. A real correction needs an owner decision and a new manifest taken at
a new `frozen_at_revision` on `main`.
