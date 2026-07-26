# Shared Assets

This directory is a reference, not a storage location. The actual SysML v2
shared asset supersets live under `textual-notation-of-model/packages/architecture/`:

| Shared asset | Configurable owners |
|---|---|
| `sdv_platform_stack.sysml` | `SDVPlatformStack` |
| `execution_environments.sysml` | `EngineeringExecutionEnvironment`, `VehicleTargetExecutionEnvironment` |

Feature Catalogue mappings resolve native `variation`/`variant` declarations in
these owners. Engineering and vehicle-target execution environments remain
separate configurable families even though they reuse common execution-node,
operating-system, runtime, and evidence vocabulary.
