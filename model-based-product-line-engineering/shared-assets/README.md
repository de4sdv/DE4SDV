# Shared Assets

This directory is a reference, not a storage location. The actual SysML v2
shared asset supersets live under `textual-notation-of-model/packages/architecture/`:

| Shared asset | Configurable owners |
|---|---|
| `sdv_platform_stack.sysml` | `SDVPlatformStack` |
| `execution_environments.sysml` | `EngineeringExecutionEnvironment`, `VehicleTargetExecutionEnvironment` |

The PLEML feature bindings and the DE4SDV derivation rules resolve native
`variation`/`variant` declarations in these owners (ADR 0022); the Feature
Catalogue mappings are their non-authoritative shadow until the YAML retires.
Engineering and vehicle-target execution environments remain
separate configurable families even though they reuse common execution-node,
operating-system, runtime, and evidence vocabulary.
