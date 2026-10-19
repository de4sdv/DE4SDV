# Feature Models

These YAML files are DE4SDV Feature Catalogues and configuration-decision
models. Each catalogue declares a `projection` target naming the SysML v2
package and owner that its mapped variation groups resolve.

| File | Scope | Shared asset |
|---|---|---|
| `sdv_product_line.yaml` | SDV member-product platform and capability decisions | `DE4SDV_SDVPlatformStack::SDVPlatformStack` |
| `engineering_execution_environments.yaml` | System 2 engineering/verification host family | `DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment` |
| `vehicle_execution_environments.yaml` | System 1 vehicle-target compute family | `DE4SDV_ExecutionEnvironments::VehicleTargetExecutionEnvironment` |

## PLEML feature models (fenced)

`sdv_product_line.sysml`, `engineering_execution_environments.sysml` and
`vehicle_execution_environments.sysml` restate the three catalogues as PLEML
feature models under
[ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md),
node for node by ID; common-capability nodes have no feature. They are
fenced until its switch: outside every production selector and validated
only by the privileged PLE authority workflow. Until the switch the
catalogues above remain the selection authority. See
[`docs/product-line-engineering/pleml-feature-models.md`](../../docs/product-line-engineering/pleml-feature-models.md).

## Relationship to SysML v2

SysML v2 `variation`/`variant` provides structural variability in a shared asset.
The catalogue adds:

- stable decision/feature IDs;
- mandatory, optional, XOR, and OR hierarchy;
- binding-time metadata;
- cross-tree `requires`/`excludes` compatibility rules;
- traceable mappings from decisions to owning variations and variants.

Mapped variation groups use design-time XOR resolution and must map every child.
Zero-multiplicity SysML variants represent an explicit unresolved/absent
structural choice where needed; they are not physical product features.

## Execution-environment boundary

Engineering environments and vehicle targets deliberately use separate
catalogues and SysML owners. The tested Jetson 009A host does not imply that the
same software or evidence is portable to Apple Silicon. The NXP/Zephyr candidate
does not imply that the Autoware ROS 2 composition executes on Zephyr.

## Usage

```bash
python tools/configure_variant.py \
  --feature-model model-based-product-line-engineering/feature-models/<catalogue>.yaml \
  --bof model-based-product-line-engineering/feature-configurations/<config>.yaml \
  --shared-assets-model textual-notation-of-model/packages/architecture/<asset>.sysml \
  --check-only
```
