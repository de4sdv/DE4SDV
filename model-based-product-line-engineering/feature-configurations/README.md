# Feature Configurations

This directory contains Bill-of-Features configurations for DE4SDV member
products.

A Bill-of-Features (BoF) is the ISO/IEC 26580 term for the selection of
features that defines one specific member product. Each `.yaml` file here
is one BoF — the input to the configurator.

## Current derivation scope

The feature configurations cover the broader DE4SDV product-line catalogue, but
`configure_variant.py` currently derives only the **platform-stack SysML v2
product-model projection**. It resolves the application, middleware, OS, and
hypervisor variations in the shared platform model.

Capability selections are retained for configuration traceability and constraint
checking. They are **not** yet resolved into variable requirements, behavior, or
structure, so generated `.sysml` files are not complete member-product
specifications. Do not infer an enabled/disabled capability from the generated
SysML projection alone.

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
- **OR-groups**: the value is a non-empty YAML list of selected child names.
  Constraint equality against an OR-group tests membership in that list.
- **Optional and mandatory Boolean leaves** (e.g.
  `Capabilities.AdaptiveCruiseControl`): the value is the YAML Boolean `true` or
  `false`, not a quoted string or numeric substitute.

The loader rejects duplicate YAML keys and malformed document shapes instead of
applying YAML's usual last-key-wins behavior. Relationship types and constraint
types are also closed vocabularies; misspellings are configuration errors.

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
