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

The public CI runs both. The PLE workflows run the byte check before any step
reads the library, and keep its receipt (`pleml-package.json`) with their
evidence.

## Re-pinning

A new release is assessed from its library diff and its changelog, as
[ADR 0022](../../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)
and the plan's release policy require. `--release-diff` downloads the previous
release from the Sysand index, checks it against its record, and classifies
the diff:

- **fast path:** only the version line or the line endings change;
- **full path:** anything else changes.

The path must be the one the record states. The re-pin from 1.1.0 to 1.1.1
took the fast path: the 1.1.0 package carried CRLF line endings, and the two
libraries differ only in the version line.
