# INC-AEBS-008 configuration review

These are **proposed, unexecuted simulation controls**. INC-AEBS-008 contains no runnable ROS launch composition. Runtime launch composition and evidence collection belong to INC-AEBS-009.

## Baselines and local controls

- Autoware Universe: `f603d8759c92fb2f423f1544844e13086d79ad09`
- Autoware Launch: `f05c4b1f83e0b0e4a01ade34d5199bd5571873f1`
- [`aebs.param.yaml`](aebs.param.yaml) is a complete derived simulation configuration, not a partial overlay. It retains every pinned upstream AEB parameter and changes only `use_predicted_trajectory` from `true` to `false`. Its comments record the upstream path, Git blob SHA-1, and file SHA-256. It is proposed/unexecuted and does not repair `DEF-AEBS-PHY-002`.
- [`diagnostic-graph.yaml`](diagnostic-graph.yaml) maps `/control/autonomous_emergency_braking: aeb_emergency_stop` to autonomous-mode availability. Its per-diagnostic keys conform to the pinned graph format. `timeout: 1.0` and `hysteresis: 0.0` are explicitly provisional pending timing and fault-injection review.

## Aggregator startup setting and mappings

The aggregator-wide `initial_latch_suppression` setting is separate from the per-diagnostic graph. The exact pinned default is `initial_latch_suppression: true` in [`system/autoware_diagnostic_graph_aggregator/config/default.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/system/autoware_diagnostic_graph_aggregator/config/default.param.yaml) (Git blob `a391dad42ab67fedc3ec41a635778f49414f37e3`, SHA-256 `954fcbd6baa55827743b7ccfa9d6f8089ffd76044a16a8b93249b49df5b9a131`). This is an aggregator startup setting, not a graph-unit field; no persistence or recovery behavior is inferred here.

Do not vendor mapping copies. Exact sources of truth are:

- aggregator `command_mode_mappings` in the same pinned [`default.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/system/autoware_diagnostic_graph_aggregator/config/default.param.yaml), with the hashes above;
- converter IDs in pinned [`system/autoware_diagnostic_graph_aggregator/config/converter.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/system/autoware_diagnostic_graph_aggregator/config/converter.param.yaml) (Git blob `472d40982a10c15f56a3c642d23ab242d1be61a4`, SHA-256 `14eb92be124291bb852fc803c6cc4941609ce8345befd03b704321aca1afb75b`).

## Independently reviewed command boundary

The selected boundary is the stock `autoware_vehicle_cmd_gate` path with `use_control_command_gate=false`. The pinned Autoware Launch [`tier4_universe_launch/tier4_control_launch/launch/control.launch.xml`](https://github.com/autowarefoundation/autoware_launch/blob/f05c4b1f83e0b0e4a01ade34d5199bd5571873f1/tier4_universe_launch/tier4_control_launch/launch/control.launch.xml) defaults that switch to `false` (Git blob `5a56cf6686dce9300872834f5b17e22b5f8d070b`, SHA-256 `29b35d480ee0867d947b2204112513a3f098a8aacef7176e54c270ed86872605`). The vehicle gate consumes `/system/operation_mode/state`, `/system/fail_safe/mrm_state`, and `/system/emergency/control_cmd`, automatically selecting the emergency command while MRM is operating; no command-source selection service is needed for this selected route. The MRM handler's separate mode input remains `/api/operation_mode/state`, and its `OperateMrm` client uses `tier4_system_msgs/srv/OperateMrm`.

The selected behavior additionally depends on `use_emergency_handling: true` in the pinned [`control/autoware_vehicle_cmd_gate/config/vehicle_cmd_gate.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_vehicle_cmd_gate/config/vehicle_cmd_gate.param.yaml) (Git blob `ec230913b51f59c10e32f8436fba5c8ee4f4403e`, SHA-256 `af2255ed174a7d58b8a0ba394a8f91a86cc8cb1652faa1c9ce85d031724854aa`). It is referenced rather than vendored.

`autoware_control_command_gate` source `21: emergency_stop` remains a **deferred alternative**, not the selected gate. Its pinned default is referenced at [`control/autoware_control_command_gate/config/default.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_control_command_gate/config/default.param.yaml) (Git blob `41018566b90ff4be9431d2b46f5d950fe3e66291`, SHA-256 `4560dc284b108e4f7b729d5c08b32c660e5e8154b77c9f4e91714584fcf3d090`). It is blocked because INC-AEBS-008 has no owner for the source-selection service needed to select source 21.

## Preconditions for INC-AEBS-009

Before an AEB diagnostic transition can be interpreted as an autonomous-mode MRM test, the harness must establish and capture:

- `/autoware/state` = `DRIVING`;
- `/api/operation_mode/state` = `AUTONOMOUS`;
- `/system/operation_mode/state` = `AUTONOMOUS` for the selected legacy gate;
- `/vehicle/status/control_mode` = `AUTONOMOUS`;
- valid, fresh odometry on `/localization/kinematic_state`;
- fresh acceleration on `/localization/acceleration`;
- current steering report on `/vehicle/status/steering_status`;
- current gear command on `/control/command/gear_cmd`;
- available emergency operator status on `/system/mrm/emergency_stop/status`.

The simple planning simulator must also be initialized with the intended map, initial pose, trajectory, and engage sequence. It supplies vehicle simulation/status interfaces, but it does **not** publish `/autoware/state`, `/api/operation_mode/state`, or `/system/operation_mode/state`; the INC-AEBS-009 harness must establish those endpoints through the appropriate Autoware interfaces and retain evidence.

## Boundaries

No runtime graph parse, ROS build/launch, topic behavior, simulated braking response, raw command conversion, S-CORE integration, hardware/brake ECU/actuator behavior, safety acceptance, compliance, certification, homologation, or production readiness is claimed. Licensed SysIDE validation passed on the reviewed model commit `1eac51e1c46e111ba2e0dffda7f4bde99bdf535c` in workflow run `30169312059`; the metadata-only successor also passed in run `30170043191`. No local SysIDE validation was run. This proves textual-model tool acceptance only, not runtime behavior or engineering acceptance.
