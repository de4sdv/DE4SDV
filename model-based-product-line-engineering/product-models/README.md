# Product Models

This directory contains generated SysML v2 **platform-stack product-model
projections** for DE4SDV member products. They resolve only the application,
middleware, OS, and hypervisor variation points currently mapped to the shared
SysML v2 platform asset. They are not complete member-product specifications.

These files are **generated**, not hand-written. Each `.sysml` file is produced
by `tools/configure_variant.py` from a Bill-of-Features (YAML) validated against
the feature model. Capability selections without mapped variable assets remain
outside the generated SysML projection and are labelled as unresolved.

## Files

| File | Source BoF |
|---|---|
| [`example_linux_score.sysml`](example_linux_score.sysml) | `feature-configurations/example-linux-score-autoware.yaml` |
| [`apollo_qnx_qvm.sysml`](apollo_qnx_qvm.sysml) | `feature-configurations/apollo-qnx-qvm.yaml` |

## Regenerating

```bash
python tools/configure_variant.py \
  --feature-model model-based-product-line-engineering/feature-models/sdv_product_line.yaml \
  --bof model-based-product-line-engineering/feature-configurations/example-linux-score-autoware.yaml \
  --output model-based-product-line-engineering/product-models/example_linux_score.sysml
```

**Do not edit generated files directly.** Edit the source BoF YAML and
regenerate.

## Validation boundary

The configurator validates BoF structure and constraints, generated identifiers,
and the lexical presence/ownership of mapped package, variation, and variant
declarations. It is deliberately **not a SysML v2 parser** and does not prove
subtype conformance or full model semantics. Treat generated projections as
draft until a maintainer runs the privileged Syside validation workflow on the
reviewed commit with a valid license.
