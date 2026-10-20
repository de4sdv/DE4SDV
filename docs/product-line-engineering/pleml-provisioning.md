# PLEML provisioning: the pinned library

**Status:** the production pin of the product-line authority of
[ADR 0022](../architecture-decisions/0022-adopt-pleml-as-product-line-authority.md).
Nothing here is qualification, adoption evidence or a compliance claim.

The production Sysand project at the repository root pins
`pkg:sysand/mbse4u/pleml` `=1.1.1` (MIT license) in the committed
`sysand-lock.toml`, as [ADR 0007](../architecture-decisions/0007-pin-sysmod-sysand-dependency.md)
pins SYSMOD. `sysand sync` installs it with the other pinned libraries into
the untracked `.sysand/`, at `.sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml`.
The repository holds no PLEML source.

That path is one of the `PINNED_DEPENDENCIES` of the API baseline
(`de4sdv/sysml_api/baseline.py`): the export, the API import and the served
model read the library with the feature models, and the deploy host
materializes it with the same lock. Only the feature-model packages and
their fixtures import PLEML, and `tests/test_pleml_package.py` checks it, with
one named exemption.

Until the switch (step S6 of the
[migration plan](../plans/2026-10-19-pleml-product-line-authority.md)) the
pin was a fenced Sysand project, `model-based-product-line-engineering/libraries/pleml/`,
which only the PLE workflows read. The switch moved it to the production
lock. The release and its bytes did not change.

## The byte check

`de4sdv/semantic/pleml_package.py` records the release tag: the tag commit,
and the Git blob, SHA-256 and size of each file. A tag can be moved, so
`scripts/check_pleml_package.py` compares the installed package with that
record, never with the tag name:

```bash
sysand sync
python scripts/check_pleml_package.py --release-diff
```

The public CI and the privileged full-model ingestion run both, offline,
before any step reads the library. The PLE workflows run the byte check too,
keep its receipt (`pleml-package.json`) with their evidence, and add the
network checks:

- `--verify-tag` fetches the release tag and requires the recorded commit and
  file blobs;
- `--from-index` (the PLE authority job, which runs on re-pin pull requests)
  downloads the previous release from the Sysand index and requires the
  recorded diff.

## Re-pinning

A new release is assessed from its library diff and its changelog, as ADR
0022 and the plan's release policy require. The release diff classifies it:

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
previous one. A re-pin also adds the new release's entry to `PROVISION_PATHS`,
where its run reads the library; a test fails until it does.

A re-pin changes the served model, because the library's path names its
version, and the export, the receipts and the `FeatureConfiguration` kernel
mapping name that path. On either path it therefore needs fresh receipts from
the authority job, the regenerated kernel-vocabulary pair, and its own
privileged ingestion and deploy.
