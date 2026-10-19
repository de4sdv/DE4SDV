# PLEML: the fenced Sysand lock

This directory pins the PLEML library for the PLE workflows. It holds a Sysand
project and its committed lock, and no PLEML source. `sysand sync` here
installs `pkg:sysand/mbse4u/pleml` `=1.1.1` (MIT license) into the untracked
`.sysand/` of this directory.

## The fence

Until the switch to PLEML as the product-line authority (step S6 of the
[migration plan](../../../docs/plans/2026-10-19-pleml-product-line-authority.md)),
only the PLE qualification, the PLE scope alignment and their scripts read
this lock. The production lock (`sysand-lock.toml` at the repository root),
`PINNED_DEPENDENCIES`, the reviewed export roots and the production selectors
do not use PLEML. `tests/test_pleml_package.py` holds the fence. It also
checks that only the feature-model packages and their fixtures import PLEML,
apart from two named exemptions.

## The byte check

`de4sdv/semantic/pleml_package.py` records the release tag: the tag commit,
and the Git blob, SHA-256 and size of each file. A tag can be moved, so
`scripts/check_pleml_package.py` compares the installed package with that
record, never with the tag name:

```bash
(cd model-based-product-line-engineering/libraries/pleml && sysand sync)
python scripts/check_pleml_package.py --release-diff
```

The public CI runs both, offline. The PLE workflows run the byte check before
any step reads the library, and keep its receipt (`pleml-package.json`) with
their evidence. They also run the network checks:

- `--verify-tag` fetches the release tag and requires the recorded commit and
  file blobs;
- `--from-index` (PLE scope alignment, which runs on re-pin pull requests)
  downloads the previous release from the Sysand index and requires the
  recorded diff.

## Re-pinning

A new release is assessed from its library diff and its changelog, as
[ADR 0022](../../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)
and the plan's release policy require. The release diff classifies it:

- **fast path:** only the version line of the library's header comment, or the
  line endings, change, and the new version line names the pinned version;
- **full path:** anything else changes, including the license files or the set
  of model files.

A re-pin records what the diff found (`REPIN`): the path, and the previous text
and line endings of each differing line. `--release-diff` then proves it
offline: the record must rebuild the previous release's tag and package bytes
from the installed library. The re-pin from 1.1.0 to 1.1.1 took the fast path:
the 1.1.0 package carried CRLF line endings, and the two libraries differ only
in line 25, the version line. `scripts/compare_ple_qualification_artifacts.py`
compares a PLE qualification run on the new pin with the last run on the
previous one.

## At the switch

When PLEML moves to the production lock (S6), these change together: the
project and library paths and the usage, lock and other-package rules in
`de4sdv/semantic/pleml_package.py`, the `sysand sync` lines and the PLE scope
alignment's `syside check` path in the reader workflows, and the tests that
name the fenced path.
