# PLEML scope alignment (experiment)

`aebs_product_line_scope_alignment.sysml` restates the admitted AEBS
product-line scope with the exact-pinned PLEML library: the one admitted
variability (Vehicle Platform Integration Mode) as a feature tree, the two
planned reference members as feature configurations, two deliberately invalid
probes, and the derived shared-asset variants of the platform stack as feature
bindings. It reaches the governed scope and the shared-asset superset by
qualified reference only.

It is an experiment and not an authority. The receipts of its licensed run say
`qualified: false`; nothing here adopts PLEML, changes the YAML catalogue or
the configurator, or claims compliance. The decision record, the evidence and
the non-claims are in
[`docs/product-line-engineering/ple-s-scope-alignment.md`](../../docs/product-line-engineering/ple-s-scope-alignment.md).

## Boundary

This directory is outside every production selector: not in the reviewed
export roots, not a validation root, not served, not in the method check and
not in any production workflow's trigger (`tests/test_ple_scope_alignment_model.py`
is the fence). PLEML itself is never copied into this repository: the
privileged scope-alignment workflow reads it from the frozen Gate A experiment
checkout at the recorded pin.

## Validation

`.github/workflows/privileged-ple-scope-alignment.yml` runs on pull requests
that touch this directory (same-repository, allowlisted authors) and on
maintainer dispatch: licensed `syside check` of the reviewed roots with the
pinned library and this model, then fresh serialization and evaluation by
`scripts/run_ple_scope_alignment.py`. The unlicensed shape, fence and
evaluator tests run in the public CI.
