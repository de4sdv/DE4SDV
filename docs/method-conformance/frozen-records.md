# Frozen O1/O2/O3 records

**Status:** active since O4 Wave C1. Owner decisions Q7 and D10
(2026-10-07, recorded in
[o4/owner-decisions-2026-10.md](o4/owner-decisions-2026-10.md)).

## Problem

The O1 inventory, the O2 Semantic Projection and Profile chain (v1 to v1.2)
and the O3 equivalence scope were generated from the authored ontology and
from code that O4 retires. Their gates regenerated them from the live tree and
required every bound input to equal the current working-tree bytes. So every
edit to a bound input (for example `scripts/check_model_sync.py` or a kernel
`.sysml` file) broke a historical record, and deleting the authored ontology
would have broken the whole chain verifier.

## Mechanism

Every file under `o1/`, `o2/` and `o3/` is a **frozen record**. A frozen record
is pinned by digest and never regenerated. Its revision binding is checked at
its own historical revision, never against the live tree. Some frozen records
are still read as read-only data by live code (for example the O2 v1 to v1.2
pairs feed the model-authority runtime's `o2-chain` layer).

The manifest is [frozen-records.json](frozen-records.json)
(`de4sdv.frozen-records/v1`). It has no `binding` block and no top-level
`source_revision`, so it is not revision-bound evidence itself. It records:

- `decision` and `directories` (exactly the three directories);
- `frozen_at_revision`: the `main` commit the freeze was taken from;
- one record per file: `path`, `sha256`, `kind`
  (`generated`, `evidence`, `authored`, `prose`), `binding_source_revision`,
  `live_consumer` and `retired_generator`.

Every digest refers to bytes already on `main`, so the manifest is
squash-safe: no commit of the introducing branch is bound.

## Gate

The frozen lane of `scripts/verify_generated_chain.py` checks, fail-closed:

1. The manifest equals its deterministic rendering from the tree at
   `frozen_at_revision`, which must exist and be an ancestor of `HEAD`.
   Re-derive it for review with
   `python scripts/verify_generated_chain.py --render-frozen-manifest <rev>`.
2. The files present under the three directories equal the record set.
   Adding or removing a file fails, with or without a manifest edit.
3. Each file's current bytes match its recorded `sha256`. Editing or
   regenerating a frozen record fails.
4. For a record with a `binding` block: `source_revision` exists and is an
   ancestor of `HEAD`, and every `bound_inputs` entry exists at that revision
   (`git show <rev>:<path>`) with the recorded digest. The working-tree bytes
   of the inputs are not consulted, so a bound input may be edited or deleted
   at `HEAD` without breaking the record.
5. `extends` blocks and the O3 scope basis may reference frozen records only
   and must match their frozen digests; the O3 `comparison_base_revision`
   exists and is an ancestor of `HEAD`.

`scripts/check_repo.py` runs the frozen lane instead of the former O1 and O2
v1 to v1.2 regeneration checks. The live lanes of the verifier no longer
cover frozen records, and no longer read the authored ontology to derive their
inputs.

## Retired generators

These CLIs refuse to write or check (exit code 2) and point to the manifest:

- `scripts/generate_semantic_authority_inventory.py`
- `scripts/generate_semantic_projection_v1.py`
- `scripts/generate_semantic_projection_o22.py`
- `scripts/generate_semantic_projection_o23.py`
- `scripts/generate_o3_equivalence_scope.py`

O4 Wave C2 deleted or pruned their library code (the O1 inventory builder, the O2
v1/v1.1/v1.2 projection generators and the O3 equivalence machinery all read
the authored ontology, which C2 deleted). The CLIs remain as import-free
stubs that exit 2 and name the manifest.

## Changing a frozen record

Don't. Prose in a frozen record is not edited for supersession; supersession
is stated in the O4 closure record. A real correction needs an owner decision
and a new manifest taken at a new `frozen_at_revision` on `main`.
