# Product Models

This directory contains generated SysML v2 product instances — configured member
products of the DE4SDV SDV product line.

These files are **generated**, not hand-written. Each `.sysml` file is produced
by `tools/configure_variant.py` from a Bill-of-Features (YAML) validated against
the feature model.

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
