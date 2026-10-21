# Feature Models

The PLEML feature models of the product line, one per family, are the
configuration-validity authority since the switch of
[ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md).
DE4SDV evaluates their configurations and derives their variants.

| Feature model | Scope | Shared asset |
|---|---|---|
| `sdv_product_line.sysml` | SDV member-product platform and capability decisions | `DE4SDV_SDVPlatformStack::SDVPlatformStack` |
| `engineering_execution_environments.sysml` | System 2 engineering/verification host family | `DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment` |
| `vehicle_execution_environments.sysml` | System 1 vehicle-target compute family | `DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment` |

Each feature model restates a YAML catalogue node for node by ID; the
catalogues retired at step S7 of ADR 0022. Common capabilities have no
feature. Each feature model carries its projection block: the SysML v2
package and owner that its bound variation groups resolve. See
[`docs/product-line-engineering/pleml-feature-models.md`](../../docs/product-line-engineering/pleml-feature-models.md).

`receipts/` holds their receipts: one per feature model, with the
compressed serialized elements of the licensed run they were evaluated from.
The evaluator of ADR 0022 step S2 writes them and replays them offline, and
the configurator generates the product-model projections from them.

## Changing a feature model

A change to a feature model needs licensed serialization: the privileged PLE
authority workflow writes fresh receipts on the pull request, and they are
committed together with the product-model projections that the configurator
regenerates from them. Until S7 the YAML catalogues were a non-authoritative
shadow beside these models, and the parity check compared the two paths.

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
feature models and SysML owners. The tested Jetson 009A host does not imply that the
same software or evidence is portable to Apple Silicon. The NXP/Zephyr candidate
does not imply that the Autoware ROS 2 composition executes on Zephyr.

## Usage

```bash
# One configuration of a committed receipt, replayed offline (no licence).
python tools/configure_variant.py \
  --receipt model-based-product-line-engineering/feature-models/receipts/<feature model>.receipt.json \
  --configuration <configuration> --check-only

# Every committed receipt, replayed offline, as the public CI runs it.
python scripts/run_pleml_configuration_evaluation.py replay \
  model-based-product-line-engineering/feature-models/receipts/*.receipt.json
```
