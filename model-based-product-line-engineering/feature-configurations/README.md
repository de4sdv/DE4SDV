# Feature Configurations

This directory contains Bill-of-Features configurations for DE4SDV member
products.

A Bill-of-Features (BoF) is the ISO/IEC 26580 term for the selection of
features that defines one specific member product. Each `.yaml` file here
is one BoF — the input to the configurator.

## Files

| File | Status | Description |
|---|---|---|
| [`example-linux-score-autoware.yaml`](example-linux-score-autoware.yaml) | Valid | Autoware + S-CORE + Linux, single-domain |
| [`apollo-qnx-qvm.yaml`](apollo-qnx-qvm.yaml) | Valid | Apollo + AUTOSAR Adaptive + QNX + QVM (mixed-criticality) |
| [`invalid-score-android.yaml`](invalid-score-android.yaml) | **Invalid** | S-CORE + Android HLOS — deliberately violates C001; used for testing |

## Selection semantics

Each BoF file contains a `selections` block mapping feature paths to values:

- **Alternative groups** (e.g. `PlatformStack.Middleware`): the value is the
  selected child feature name (e.g. `EclipseSCORE`).
- **Optional features** (e.g. `Capabilities.AdaptiveCruiseControl`): the value
  is `true` or `false`.
- **Mandatory features** are typically listed explicitly for traceability but
  are enforced by the feature model regardless.

## Creating a new member product

1. Copy an existing BoF as a template.
2. Edit the selections to match your target configuration.
3. Validate:

```bash
python tools/configure_variant.py \
  --feature-model model-based-product-line-engineering/feature-models/sdv_product_line.yaml \
  --bof model-based-product-line-engineering/feature-configurations/<your-config>.yaml \
  --check-only
```

4. Generate:

```bash
python tools/configure_variant.py \
  --feature-model model-based-product-line-engineering/feature-models/sdv_product_line.yaml \
  --bof model-based-product-line-engineering/feature-configurations/<your-config>.yaml \
  --output model-based-product-line-engineering/product-models/<output>.sysml
```
