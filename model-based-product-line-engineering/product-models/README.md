# Product Models

These files are generated SysML v2 projections. Do not edit them directly.

| File | Source BoF | Scope |
|---|---|---|
| `example_linux_score.sysml` | `example-linux-score-autoware.yaml` | SDV platform projection |
| `apollo_qnx_qvm.sysml` | `apollo-qnx-qvm.yaml` | SDV platform projection |
| `inc_aebs_009a_jetson_execution_environment.sysml` | `inc-aebs-009a-jetson.yaml` | Inspected exact maintained System 2 environment projection; historical run has coarser identity |
| `apple_silicon_macos_candidate.sysml` | `apple-silicon-macos-candidate.yaml` | Planned System 2 candidate projection |
| `nxp_zephyr_vehicle_target_candidate.sysml` | `nxp-zephyr-vehicle-target-candidate.yaml` | Planned System 1 candidate projection |

Each generated file records content hashes for its shared asset, catalogue, and
BoF. Regeneration must reproduce committed bytes.

## Validation boundary

The configurator validates BoF structure, evidence metadata, compatibility
constraints, generated identifiers, and lexical ownership of mapped package,
variation, and variant declarations. It is deliberately not a SysML v2 parser
and does not prove subtype conformance or full semantic validity. Treat a
projection as draft until the privileged SysML validation workflow passes on the
reviewed commit.
