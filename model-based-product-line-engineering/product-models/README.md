# Product Models

These files are generated SysML v2 projections. Do not edit them directly.
Since the switch of
[ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)
the configurator generates each one from the committed receipt of its PLEML
configuration. One file in this directory is hand-authored (see the table
below); it is reviewed like any other model asset through the normal PR and
privileged validation path.

| File | Source configuration (receipt) | Scope |
|---|---|---|
| `aebs_autoware_linux_lidar_camera.sysml` | `aebsAutowareLinuxLidarCamera` (`sdv_product_line.receipt.json`) | Standalone AEBS reference member platform projection |
| `middleware_autoware_aaos_sdv_reference.sysml` | `middlewareAutowareAAOSSDVReference` (`sdv_product_line.receipt.json`) | AAOS-integrated middleware reference member platform projection |
| `middleware_autoware_score_reference.sysml` | `middlewareAutowareSCOREReference` (`sdv_product_line.receipt.json`) | Eclipse S-CORE reference configuration platform projection (INC-MW-011; not admitted) |
| `apollo_qnx_qvm.sysml` | `apolloQNXQVMVariant` (`sdv_product_line.receipt.json`) | SDV platform projection |
| `inc_aebs_009a_jetson_execution_environment.sysml` | `incAEBS009AJetsonExecutionEnvironment` (`engineering_execution_environments.receipt.json`) | Inspected exact maintained System 2 environment projection; historical run has coarser identity |
| `apple_silicon_macos_candidate.sysml` | `appleSiliconMacOSCandidate` (`engineering_execution_environments.receipt.json`) | Planned System 2 candidate projection |
| `nxp_zephyr_vehicle_target_candidate.sysml` | `nxpZephyrVehicleTargetCandidate` (`vehicle_execution_environments.receipt.json`) | Planned System 1 candidate projection |
| `aebs_autoware_reference_product.sysml` | hand-authored composite | Composite AEBS reference member: specializes the governed `StandaloneAutowareAEBSReferenceMember` decision, types its `platformStack` by the generated `AEBSAutowareLinuxLidarCamera` projection, and records model-native reference dependencies from its `aebsLogicalSystem`/`aebsSoftware` instances to the canonical `DE4SDV_AEBSLogicalArchitecture::system` and `DE4SDV_AEBSPhysicalSoftwareRealization::physicalSoftware` usages. These are reference traces only — no executable semantic query maps them yet. The canonical binding itself does not resolve platform-stack variants (the projection does) or sensing selections (the feature configuration), and does not make the composite a resolved configured product. |

Each generated file records the digests of its receipt, of the receipt's
elements, of its configuration, of its feature model and of its shared asset.
Regeneration from the receipt must reproduce committed bytes:

```bash
python tools/configure_variant.py \
  --receipt model-based-product-line-engineering/feature-models/receipts/<feature model>.receipt.json \
  --configuration <configuration> \
  --output model-based-product-line-engineering/product-models/<file>.sysml
```

The configurator replays the receipt first and refuses one that does not
hold. Variation and variant identity come from the receipt, and each
selection outside the projection is labelled by its PLEML feature path. Until
step S7 of ADR 0022 the YAML path of the configurator was a non-authoritative
shadow, and the parity check required its projection of each committed file
to have the same normalised body.

## Derived product models and configured products

A product model has two stages in DE4SDV.

A **derived product model** (a projection) is generated. The configurator
writes it from a feature configuration and the receipt of that
configuration. It specializes the shared asset of its feature model, for
example `SDVPlatformStack`. It only selects one variant for each variation
(`part :>> x = x::variant;`). The generated
files in this directory are derived product models. Do not edit them by
hand. Generation goes in one direction only: an edit here does not reach
the feature configuration or the shared asset. To change a derived product
model, change its feature configuration or the shared asset, and generate
it again.

A **configured product** completes one derived product model for one
product. Its increment models it in its own slice, not in this directory.
It adds the engineering content that the product line does not manage as
variants. An example is a middleware integration layer with its processes
and connections. That content refers to the platform-stack parts that it
uses. A binding makes each reference the same thing as its part, so each
part has one owner. A configured product carries a configuration identity,
for example `MW-CONFIG-001` or `MW-CONFIG-002`, and verification evidence
binds that identity. `MW-CONFIG-002` also records the SHA-256 of its
receipt. A **configured member** is the configured product of an admitted
member. The examples are the configured member
[`MW-CONFIG-001`](../../textual-notation-of-model/packages/features/middleware/middleware_variability_configuration.sysml)
of INC-MW-009 and the configured product
[`MW-CONFIG-002`](../../textual-notation-of-model/packages/features/middleware/middleware_score_variability_configuration.sysml)
of INC-MW-011.

Only content that varies across member products belongs in the shared
assets. Content that one product needs stays in the slice of its increment
and enters through the configured product.

## Validation boundary

The configurator writes what the receipt records: the DE4SDV evaluation of
the serialized configuration. It decides nothing itself, and it does not
prove subtype conformance or full semantic validity. Treat a projection as
draft until the privileged SysML validation workflow passes on the reviewed
commit.
