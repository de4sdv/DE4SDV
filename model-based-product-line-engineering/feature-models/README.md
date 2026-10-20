# Feature Models

The PLEML feature models of the product line, one per family, are the
configuration-validity authority since the switch of
[ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md).
DE4SDV evaluates their configurations and derives their variants.

| Feature model | Scope | Shared asset | YAML shadow |
|---|---|---|---|
| `sdv_product_line.sysml` | SDV member-product platform and capability decisions | `DE4SDV_SDVPlatformStack::SDVPlatformStack` | `sdv_product_line.yaml` |
| `engineering_execution_environments.sysml` | System 2 engineering/verification host family | `DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment` | `engineering_execution_environments.yaml` |
| `vehicle_execution_environments.sysml` | System 1 vehicle-target compute family | `DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment` | `vehicle_execution_environments.yaml` |

Each feature model restates its YAML catalogue node for node by ID;
common-capability nodes have no feature. Each carries its projection block:
the SysML v2 package and owner that its bound variation groups resolve. See
[`docs/product-line-engineering/pleml-feature-models.md`](../../docs/product-line-engineering/pleml-feature-models.md).

`receipts/` holds their receipts: one per feature model, with the
compressed serialized elements of the licensed run they were evaluated from.
The evaluator of ADR 0022 step S2 writes them and replays them offline, and
the configurator generates the product-model projections from them.

## The YAML catalogues: a non-authoritative shadow

The `*.yaml` catalogues are the non-authoritative shadow of the feature models
for at least 30 days after the switch. The parity check
(`scripts/check_pleml_parity.py`) compares the two paths on every pull request
until the YAML retires (ADR 0022, step S7), so a change to a feature model
changes its catalogue in the same pull request until then.

## Relationship to SysML v2

SysML v2 `variation`/`variant` provides structural variability in a shared asset.
The feature model adds:

- stable decision/feature IDs;
- mandatory, optional, XOR, and OR hierarchy;
- binding-time metadata;
- cross-tree `requires`/`excludes` compatibility rules;
- one feature binding per shared-asset variant, and derivation rules for the
  variations that no configuration selects.

Bound variation groups use design-time XOR resolution and bind every child.
Zero-multiplicity SysML variants represent an explicit unresolved/absent
structural choice where needed; they are not physical product features.

## Execution-environment boundary

Engineering environments and vehicle targets deliberately use separate
catalogues and SysML owners. The tested Jetson 009A host does not imply that the
same software or evidence is portable to Apple Silicon. The NXP/Zephyr candidate
does not imply that the Autoware ROS 2 composition executes on Zephyr.

## Usage

```bash
# The authority: one configuration of a committed receipt, replayed offline.
python tools/configure_variant.py \
  --receipt model-based-product-line-engineering/feature-models/receipts/<feature model>.receipt.json \
  --configuration <configuration> --check-only

# The shadow until S7: the YAML path, as the parity check runs it.
python tools/configure_variant.py \
  --feature-model model-based-product-line-engineering/feature-models/<catalogue>.yaml \
  --bof model-based-product-line-engineering/feature-configurations/<config>.yaml \
  --shared-assets-model textual-notation-of-model/packages/architecture/<asset>.sysml \
  --check-only
```
