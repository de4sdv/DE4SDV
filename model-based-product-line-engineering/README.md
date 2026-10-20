# Model-Based Product-Line Engineering

This area implements DE4SDV's in-repository PLE chain. Since the switch of
[ADR 0022](../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)
the PLEML feature models and configurations are the product-line authority:

```text
PLEML feature model (feature-models/*.sysml)
        ↓
PLEML feature configuration (feature-configurations/*.sysml)
        ↓ privileged PLE authority job: licensed serialization, DE4SDV evaluation
Evaluation receipt (feature-models/receipts/)
        ↓ configure_variant.py --receipt
Configured SysML v2 product-model projection (product-models/)
```

The SysML v2 packages under `textual-notation-of-model/packages/architecture/`
are the shared asset supersets (150% models). Native `variation`/`variant`
constructs hold structural choices. The feature models add the hierarchy,
compatibility constraints, stable IDs, binding times and feature-to-asset
bindings that native variability does not provide by itself. DE4SDV evaluates
their configurations and derives the variants that no configuration selects.
PLEML is the configuration-validity authority; nothing executes a PLEML
constraint body natively.

The YAML catalogues and Bills-of-Features stay as a **non-authoritative
shadow** for at least 30 days after the switch. The parity check
(`scripts/check_pleml_parity.py`) compares the two paths on every pull request
until the YAML retires (ADR 0022, step S7). Until then the Bills-of-Features
also carry the evidence records of their configurations.

## Governed product-line scope

The [`scoping/`](scoping/) directory records reviewed planned-member portfolio
decisions. Its SysML/API identity governs which members define the scope,
which differences are product variability, and which technical choices are
derived. It is the admission authority: a configuration can be valid without
being admitted, and the receipts record both verdicts. Portfolio membership
does not change local increment, implementation, configuration, or evidence
status.

## PLEML feature models and configurations

The `.sysml` files of [`feature-models/`](feature-models/) and
[`feature-configurations/`](feature-configurations/) restate the three
catalogues and every Bill-of-Features as PLEML feature models and
configurations. They are model roots of the export, the API baseline and the
served model, like the product models. The fixtures under
`feature-configurations/fixtures/` stay out of the export: the privileged PLE
authority workflow validates and serializes them. See
[`docs/product-line-engineering/pleml-feature-models.md`](../docs/product-line-engineering/pleml-feature-models.md).
They superseded the PLE-S scope-alignment experiment, whose record stays as
history in
[`docs/product-line-engineering/ple-s-scope-alignment.md`](../docs/product-line-engineering/ple-s-scope-alignment.md).

PLEML 1.1.1 comes from the production Sysand lock (`sysand-lock.toml`),
`=1.1.1`, byte-checked against its release tag. See
[`docs/product-line-engineering/pleml-provisioning.md`](../docs/product-line-engineering/pleml-provisioning.md).

## Configurable families

| Family | System role | Feature model | YAML shadow | Shared SysML owner |
|---|---|---|---|---|
| SDV product line | System 1 product | `sdv_product_line.sysml` | `sdv_product_line.yaml` | `SDVPlatformStack` |
| Engineering execution environments | System 2 build/simulation/verification | `engineering_execution_environments.sysml` | `engineering_execution_environments.yaml` | `EngineeringExecutionEnvironment` |
| Vehicle-target execution environments | System 1 deployed compute | `vehicle_execution_environments.sysml` | `vehicle_execution_environments.yaml` | `VehicleTargetExecutionEnvironment` |

Engineering hosts are **not SDV product features**. A Jetson or Apple Silicon
machine used to execute verification is an evidence context. A vehicle compute
node running Zephyr is product architecture. The separate owners and catalogues
prevent evidence portability from being inferred across those roles.

## Derived technical variations

A configuration records user-visible product choices. It holds features only,
so it cannot select a technical adapter that other choices determine. The
feature model declares such a variation as a derived variation with its
derivation rules (`D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER`), and DE4SDV derives
its variant.

For the SDV platform stack, the application and the middleware derive
`applicationMiddlewareAdapter`. Exactly one rule must match a valid
configuration: one that matches none, or several, is rejected, and PLEML
exclusions state the unsupported pairs. The generated projection annotates
the adapter as derived.

For example, selecting `Autoware` and `AndroidSDV` derives
`autowareToAAOSSDV`. Selecting middleware `None` derives the absent `none`
variant. Neither adapter value belongs in a configuration. Until the YAML
retires, the catalogue's `derived_asset_selections` state the same rules for
the shadow, and the parity check compares the two.

## Evidence contract

Until the Bills-of-Features retire, a Bill-of-Features may declare the
evidence of its configuration:

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
specifications. A valid configuration means that the DE4SDV evaluation found
its choices and cross-tree constraints consistent with the bound and derived
SysML variation declarations.
It does not prove runtime support, safety, compliance, certification, or semantic
validity of the full model. Privileged SysML validation remains a review gate.
