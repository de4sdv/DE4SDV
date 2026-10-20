# Product Models

These files are generated SysML v2 projections. Do not edit them directly.
One file in this directory is hand-authored (see the table below); it is
reviewed like any other model asset through the normal PR and privileged
validation path.

| File | Source BoF | Scope |
|---|---|---|
| `example_linux_score.sysml` | `example-linux-score-autoware.yaml` | SDV platform projection |
| `apollo_qnx_qvm.sysml` | `apollo-qnx-qvm.yaml` | SDV platform projection |
| `inc_aebs_009a_jetson_execution_environment.sysml` | `inc-aebs-009a-jetson.yaml` | Inspected exact maintained System 2 environment projection; historical run has coarser identity |
| `apple_silicon_macos_candidate.sysml` | `apple-silicon-macos-candidate.yaml` | Planned System 2 candidate projection |
| `nxp_zephyr_vehicle_target_candidate.sysml` | `nxp-zephyr-vehicle-target-candidate.yaml` | Planned System 1 candidate projection |
| `aebs_autoware_reference_product.sysml` | hand-authored composite | Composite AEBS reference member: specializes the governed `StandaloneAutowareAEBSReferenceMember` decision, types its `platformStack` by the generated `AEBSAutowareLinuxLidarCamera` projection, and records model-native reference dependencies from its `aebsLogicalSystem`/`aebsSoftware` instances to the canonical `DE4SDV_AEBSLogicalArchitecture::system` and `DE4SDV_AEBSPhysicalSoftwareRealization::physicalSoftware` usages. These are reference traces only — no executable semantic query maps them yet. The canonical binding itself does not resolve platform-stack variants (the projection does) or sensing selections (bill-of-features), and does not make the composite a resolved configured product. |

Each generated file records content hashes for its shared asset, catalogue, and
BoF. Regeneration must reproduce committed bytes.

## Receipt mode

The configurator also generates a projection from a committed PLEML receipt
([ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)),
with the same writer:
`python tools/configure_variant.py --receipt <receipt> --configuration <name>`.
It replays the receipt first and refuses one that does not hold. Its header
names the receipt and the configuration instead of the BoF. Until the switch
(step S6) the committed projections stay those of the YAML path, and the
parity check (`scripts/check_pleml_parity.py`) requires the receipt's
projection of each to have the same normalised body.

## Validation boundary

The configurator validates BoF structure, evidence metadata, compatibility
constraints, generated identifiers, and lexical ownership of mapped package,
variation, and variant declarations. It is deliberately not a SysML v2 parser
and does not prove subtype conformance or full semantic validity. Treat a
projection as draft until the privileged SysML validation workflow passes on the
reviewed commit.
