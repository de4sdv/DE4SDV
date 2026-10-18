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
privileged scope-alignment workflow reads it from the frozen experiment
checkout at PLEML 1.1.0 (tag `pleml-1.1.0-frozen`) at the recorded pin.

## Validation

`.github/workflows/privileged-ple-scope-alignment.yml` runs on pull requests
that touch this directory (same-repository, allowlisted authors) and on
maintainer dispatch: licensed `syside check` of the reviewed roots with the
pinned library and this model, then fresh serialization and evaluation by
`scripts/run_ple_scope_alignment.py`, then the unlicensed comparison oracle.
The unlicensed shape, fence, evaluator and oracle tests run in the public CI.

## Comparison oracle

`scripts/compare_ple_scope_alignment.py` runs the unchanged
`tools/configure_variant.py` on the committed configurations and on probes it
generates outside the repository, and sets each result beside the PLE-S
evaluation of the same statement. `catalogue-correspondence.yaml` is its only
declared input: it names, for a catalogue node, the governed-scope element the
node restates, and carries no classification. Whether that element is common,
reference-only, deferred or excluded is read from the serialized governed
scope of the licensed run; which shared-asset variants an admitted alternative
derives is read from the serialized feature bindings. The oracle is a
comparison, not a second selection authority.
