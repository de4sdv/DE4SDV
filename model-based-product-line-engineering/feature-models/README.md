# Feature Models

This directory contains the DE4SDV feature model — the Feature Catalogue in
ISO/IEC 26580 terminology.

## What is a feature model?

A feature model defines the hierarchical relationships between features in the
SDV product line. It captures:

- **What features exist** — platform stack layers, vehicle capabilities
- **How they relate** — mandatory, optional, alternative (XOR), or-group
- **Cross-tree constraints** — requires and excludes relationships between
  features in different subtrees

The feature model is the **decision layer**. It drives which variant selections
are valid for a member product. The SysML v2 base model
(`textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml`)
is the **shared asset superset** (150% model) whose structural variation points
the feature selections resolve.

## File

| File | Description |
|---|---|
| [`sdv_product_line.yaml`](sdv_product_line.yaml) | SDV product-line feature model |

## Relationship to the SysML v2 model

SysML v2 `variation`/`variant` provides structural variability in the shared
asset model — "these are the options for this layer." The feature model adds
the decision logic on top: which options are compatible, which are mandatory,
which capabilities distinguish member products.

This is itself a DE4SDV finding: native SysML v2 handles structural variability
in the shared asset, but full feature-model algebra (mandatory/optional/
alternative/or-group hierarchy with cross-tree requires/excludes) requires an
external representation.

## Usage

The feature model is consumed by the configurator:

```bash
python tools/configure_variant.py \
  --feature-model model-based-product-line-engineering/feature-models/sdv_product_line.yaml \
  --bof model-based-product-line-engineering/feature-configurations/<config>.yaml \
  --output model-based-product-line-engineering/product-models/<output>.sysml
```

See [`../feature-configurations/`](../feature-configurations/) for example
Bill-of-Features and [`../product-models/`](../product-models/) for generated
product instances.
