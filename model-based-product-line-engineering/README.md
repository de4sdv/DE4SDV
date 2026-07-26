# Model-Based Product-Line Engineering

This area implements DE4SDV's lightweight in-repository PLE chain:

```text
Feature Catalogue (YAML)
        ↓
Bill-of-Features (YAML)
        ↓ configure_variant.py
Configured SysML v2 product-model projection
```

The SysML v2 packages under `textual-notation-of-model/packages/architecture/`
are the shared asset supersets (150% models). Native `variation`/`variant`
constructs hold structural choices. The YAML catalogues hold hierarchy,
compatibility constraints, stable IDs, binding times, and feature-to-asset
mappings that native variability does not provide by itself.

## Configurable families

| Family | System role | Feature catalogue | Shared SysML owner |
|---|---|---|---|
| SDV product line | System 1 product | `sdv_product_line.yaml` | `SDVPlatformStack` |
| Engineering execution environments | System 2 build/simulation/verification | `engineering_execution_environments.yaml` | `EngineeringExecutionEnvironment` |
| Vehicle-target execution environments | System 1 deployed compute | `vehicle_execution_environments.yaml` | `VehicleTargetExecutionEnvironment` |

Engineering hosts are **not SDV product features**. A Jetson or Apple Silicon
machine used to execute verification is an evidence context. A vehicle compute
node running Zephyr is product architecture. The separate owners and catalogues
prevent evidence portability from being inferred across those roles.

## Evidence contract

A Bill-of-Features may declare:

```yaml
evidence:
  status: tested
  artifacts:
    - id: EVID-EXAMPLE
      path: repository/relative/path.json
```

Evidence-bearing states require retained, existing repository artifacts.
`planned` configurations may have no artifacts and remain explicitly
unverified. Status metadata is not a feature selection and does not alter the
configured structure.

## Scope boundary

Generated files are product-model **projections**, not complete member-product
specifications. A valid configuration proves that the declared choices and
cross-tree constraints are consistent with mapped SysML variation declarations.
It does not prove runtime support, safety, compliance, certification, or semantic
validity of the full model. Privileged SysML validation remains a review gate.
