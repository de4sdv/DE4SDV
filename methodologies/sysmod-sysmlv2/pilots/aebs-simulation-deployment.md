# INC-AEBS-008 — Autoware AEBS simulation deployment controls

- **Status:** Draft
- **Parent:** `INC-AEBS-007`
- **Evidence:** pinned source/configuration inspection and static YAML checks only
- **Execution:** not executed; launch composition and evidence belong to `INC-AEBS-009`

## Decision requested

Review a simulation-only deployment candidate that carries the pinned Autoware AEB diagnostic through MRM and the selected stock vehicle command gate to a vehicle-dynamics test double. INC-AEBS-008 intentionally contains no runnable ROS launch.

## Pinned baseline and boundary

| Repository | Commit |
| --- | --- |
| `autowarefoundation/autoware_universe` | `f603d8759c92fb2f423f1544844e13086d79ad09` |
| `autowarefoundation/autoware_launch` | `f05c4b1f83e0b0e4a01ade34d5199bd5571873f1` |

**System 1:** AEB; diagnostic graph aggregator and converter; MRM handler; emergency-stop operator; selected `autoware_vehicle_cmd_gate`; ROS 2 application runtime; Linux/no-hypervisor simulation host.

**System 2:** scenario/input harness, scenario controller, evidence collector, and `autoware_simple_planning_simulator`. The simulator is a dynamics test double, not product hardware, a brake ECU, an actuator, or a real vehicle. ROS 2 remains part of the application realization and is not mapped to the DE4SDV middleware layer.

## Independently reviewed command boundary

The selected gate is **`autoware_vehicle_cmd_gate` with stock `use_control_command_gate=false`**. The pinned Autoware Launch [`tier4_universe_launch/tier4_control_launch/launch/control.launch.xml`](https://github.com/autowarefoundation/autoware_launch/blob/f05c4b1f83e0b0e4a01ade34d5199bd5571873f1/tier4_universe_launch/tier4_control_launch/launch/control.launch.xml) defaults the switch to `false` and wires `/system/operation_mode/state`, `/system/fail_safe/mrm_state`, and `/system/emergency/control_cmd` into the vehicle gate (Git blob `5a56cf6686dce9300872834f5b17e22b5f8d070b`, SHA-256 `29b35d480ee0867d947b2204112513a3f098a8aacef7176e54c270ed86872605`). The MRM state causes this gate to select the emergency command automatically. The MRM handler's separate mode input remains `/api/operation_mode/state`, and its `OperateMrm` client uses `tier4_system_msgs/srv/OperateMrm`.

That substitution also requires `use_emergency_handling: true`, retained in the pinned Universe [`control/autoware_vehicle_cmd_gate/config/vehicle_cmd_gate.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_vehicle_cmd_gate/config/vehicle_cmd_gate.param.yaml) (Git blob `ec230913b51f59c10e32f8436fba5c8ee4f4403e`, SHA-256 `af2255ed174a7d58b8a0ba394a8f91a86cc8cb1652faa1c9ce85d031724854aa`). This upstream file is referenced, not vendored.

The `autoware_control_command_gate` source **`21: emergency_stop`** route is a deferred alternative, not the selected route. Its pinned [`default.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_control_command_gate/config/default.param.yaml) is only referenced (Git blob `41018566b90ff4be9431d2b46f5d950fe3e66291`, SHA-256 `4560dc284b108e4f7b729d5c08b32c660e5e8154b77c9f4e91714584fcf3d090`). That alternative is blocked because no owner has been assigned for the source-selection service required to select source 21.

## Planned chain

```text
AEB `/control/autonomous_emergency_braking: aeb_emergency_stop`
  on `/diagnostics`
→ diagnostic graph aggregator
→ autonomous CommandModeAvailability becomes unavailable
→ converter → OperationModeAvailability
→ MRM handler detects current AUTONOMOUS mode unavailable
→ emergency-stop operator → `/system/emergency/control_cmd`
→ vehicle gate observes `/system/fail_safe/mrm_state` and selects emergency input
→ `/control/command/control_cmd`
→ simple planning simulator `input/ackermann_control_command`
→ simulated observations
```

Availability is not selection or command generation. The MRM handler performs behavior selection; the selected vehicle gate performs the emergency command selection.

## Static control artifacts

[`aebs.param.yaml`](aebs-simulation-deployment/aebs.param.yaml) is now a **complete derived simulation configuration**, not an overlay. It retains every value from pinned Universe [`control/autoware_autonomous_emergency_braking/config/autonomous_emergency_braking.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/config/autonomous_emergency_braking.param.yaml) except `use_predicted_trajectory`, changed from `true` to `false` (Git blob `b23c3bbdd4d5954b69b70e92512610e9beaab234`, SHA-256 `6a620ee2275e48ea3a12b00a42657c1bab35ec5e0e722011556ddd08ca403e5c`). It remains proposed and unexecuted.

[`diagnostic-graph.yaml`](aebs-simulation-deployment/diagnostic-graph.yaml) uses the deployed identity `/control/autonomous_emergency_braking: aeb_emergency_stop`. It keeps emergency-stop availability independently constant OK. `timeout: 1.0` and `hysteresis: 0.0` are explicit but **provisional**, pending timing, scheduling, and fault-injection review.

[`vss-simulation-realization.yaml`](aebs-simulation-deployment/vss-simulation-realization.yaml) traces every VSS-backed functional attribute from INC-AEBS-004 to a proposed simulation transformation, field, conditional observation, semantic-state rule, or explicit gap. It preserves the distinction between collision diagnostic, emergency request, selected command, simulated response, and EBA engagement. `Vehicle.Speed` requires the explicit `m/s → km/h` conversion; the emergency diagnostic must not be reused as AEBS component failure or driver-warning state.

This map is proposed and unexecuted. The pinned Universe `packages_above.repos` declares `autoware_simple_planning_simulator` at floating `main`, and INC-AEBS-008 does not pin the exact ROS message-schema dependency revisions. INC-AEBS-009 must pin those dependencies before accepting field-level mappings.

### Aggregator startup setting and mapping references

The aggregator-wide `initial_latch_suppression` setting is separate from graph-unit configuration. Its exact pinned default is `true` in Universe [`system/autoware_diagnostic_graph_aggregator/config/default.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/system/autoware_diagnostic_graph_aggregator/config/default.param.yaml) (Git blob `a391dad42ab67fedc3ec41a635778f49414f37e3`, SHA-256 `954fcbd6baa55827743b7ccfa9d6f8089ffd76044a16a8b93249b49df5b9a131`). This records a startup setting only; no per-diagnostic persistence or recovery behavior is inferred.

Do not vendor mapping copies. The exact pinned references are:

- `command_mode_mappings`: the aggregator `default.param.yaml` above;
- converter IDs: [`system/autoware_diagnostic_graph_aggregator/config/converter.param.yaml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/system/autoware_diagnostic_graph_aggregator/config/converter.param.yaml), Git blob `472d40982a10c15f56a3c642d23ab242d1be61a4`, SHA-256 `14eb92be124291bb852fc803c6cc4941609ce8345befd03b704321aca1afb75b`.

## Required execution preconditions

Before INC-AEBS-009 injects an AEB transition, it must establish and capture:

- `/autoware/state` = `DRIVING`;
- `/api/operation_mode/state` = `AUTONOMOUS`;
- `/system/operation_mode/state` = `AUTONOMOUS` for the selected legacy gate;
- `/vehicle/status/control_mode` = `AUTONOMOUS`;
- fresh odometry on `/localization/kinematic_state`;
- fresh acceleration on `/localization/acceleration`;
- current steering report on `/vehicle/status/steering_status`;
- current gear command on `/control/command/gear_cmd`;
- available emergency operator status on `/system/mrm/emergency_stop/status`.

The simulator setup must load the intended map, set an initial pose, provide a trajectory, and complete the engage sequence. `autoware_simple_planning_simulator` does **not** publish `/autoware/state`, `/api/operation_mode/state`, or `/system/operation_mode/state`; the execution harness must establish all three through appropriate Autoware interfaces. The MRM handler's `OperateMrm` client uses `tier4_system_msgs/srv/OperateMrm`.

## Evidence, blockers, and non-claims

Static YAML/repository checks are the only execution-independent evidence here. Runtime graph parsing, mode setup, VSS transformation and state-rule execution, MRM selection, gate behavior, simulator wiring, and response evidence remain for INC-AEBS-009. `DEF-AEBS-PHY-002` still blocks acceptance of the pinned AEB launch. The provisional timeout/hysteresis values need review, the simulator and message-schema dependencies need exact pins, and the alternative control-command-gate route lacks a source-selection service owner.

No runtime parse, ROS build/launch, topic behavior, simulated braking response, raw command conversion, S-CORE integration, hardware/brake ECU/actuator behavior, safety acceptance, compliance, certification, homologation, production readiness, upstream contact, or upstream acceptance is claimed.

## Validation

Repository checks, all unit tests, YAML structural assertions, the diagnostic graph-key allowlist, and `git diff --check` pass. The focused VSS simulation-map tests enforce exact functional-catalog coverage, unique mapping IDs, and declared mapping kinds. Licensed SysIDE validation passed on the reviewed model commit `1eac51e1c46e111ba2e0dffda7f4bde99bdf535c` in workflow run `30169312059`; the earlier metadata-only successor also passed in run `30170043191`. The review-response head requires its own privileged run before final acceptance. No local SysIDE validation was run. This establishes tool acceptance of the textual model, not ROS build, launch, simulation, braking behavior, requirement satisfaction, or safety evidence.
