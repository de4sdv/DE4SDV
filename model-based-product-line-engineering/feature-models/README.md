# Feature Models

This directory contains the DE4SDV feature model — the Feature Catalogue in
ISO/IEC 26580 terminology.

## What is a feature model?

A feature model defines the hierarchical relationships between features in the
SDV product line. It captures:

- **What features exist** — platform stack layers, vehicle capabilities
- **How they relate** — mandatory, optional, alternative (XOR), or-group
  (an alternative selection is one scalar choice; an or-group selection is a
  non-empty YAML list)
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

This is itself a DE4SDV finding: native SysML v2 handles structural
variation/variant selection in the shared asset, but full feature-model algebra
(mandatory/optional/alternative/or-group hierarchy with cross-tree
requires/excludes) and traceable feature-to-asset links require an external
representation.

The current mappings resolve only the platform-stack subtree into SysML v2.
Capability entries are catalogue/configuration information until corresponding
variable shared assets and mappings exist. The generated files are therefore
platform-stack product-model projections, not complete member-product models.

## Traceability metadata

Every catalogue node has a stable `id`. Mapped platform variations and variants
use `binding_time: design`; deferred capability features use
`binding_time: unassigned` until their variable shared assets and lifecycle
resolution points are defined. A mapped variation must map every child variant,
and each target is checked against the owning variation in the shared SysML v2
model before generation.

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
platform-stack product-model projections.
