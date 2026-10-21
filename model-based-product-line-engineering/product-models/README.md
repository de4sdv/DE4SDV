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
| `example_linux_score.sysml` | `exampleLinuxSCOREVariant` (`sdv_product_line.receipt.json`) | SDV platform projection |
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

Receipt mode replays the receipt first and refuses one that does not hold.
Variation and variant identity come from the receipt. The YAML path of the
configurator, the Bill-of-Features beside each configuration, is the
non-authoritative shadow until the YAML retires: the parity check
(`scripts/check_pleml_parity.py`) requires its projection of each committed
file to have the same normalised body.

## Validation boundary

In receipt mode the configurator writes what the receipt records: the DE4SDV
evaluation of the serialized configuration. In the YAML shadow it validates
BoF structure, evidence metadata, compatibility constraints, generated
identifiers, and lexical ownership of mapped package, variation, and variant
declarations. It is deliberately not a SysML v2 parser and does not prove
subtype conformance or full semantic validity. Treat a
projection as draft until the privileged SysML validation workflow passes on the
reviewed commit.
