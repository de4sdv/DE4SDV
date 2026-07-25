# INC-AEBS-007 — Autoware AEBS physical software realization

- **Status:** Draft
- **Domain:** Physical software realization
- **Parent:** INC-AEBS-006
- **Evidence status:** Source inspected; runtime not executed
- **Source checked:** 2026-07-25

## Decision requested

Decide whether a pinned Autoware AEB package is an adequate candidate for a simulation-first pilot, with its incomplete logical coverage and two source blockers retained explicitly.

This increment combines source-to-architecture control artifacts with a SysML
physical-software realization and SAF physical-domain views. It is **not**
evidence that AEBS requirements are satisfied or that braking occurs.

## Pinned source baseline

| Item | Pinned value |
| --- | --- |
| Repository | [`autowarefoundation/autoware_universe`](https://github.com/autowarefoundation/autoware_universe) |
| Commit | [`f603d8759c92fb2f423f1544844e13086d79ad09`](https://github.com/autowarefoundation/autoware_universe/commit/f603d8759c92fb2f423f1544844e13086d79ad09) |
| Package | [`control/autoware_autonomous_emergency_braking`](https://github.com/autowarefoundation/autoware_universe/tree/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking) |
| Package version | `0.52.0` |
| License | Apache-2.0 |
| ROS 2 executable | `autoware_autonomous_emergency_braking` |
| Launch node name | `autonomous_emergency_braking` |

The version and license were checked in the pinned [`package.xml`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/package.xml). Interfaces and behavior were inspected in the pinned [`node.hpp`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/include/autoware/autonomous_emergency_braking/node.hpp), [`node.cpp`](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/src/node.cpp), [default parameters](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/config/autonomous_emergency_braking.param.yaml), [launch XML](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/launch/autoware_autonomous_emergency_braking.launch.xml), and [README](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/README.md). Every source link is commit-pinned and was checked on 2026-07-25.

## Node input contract

| Private input | ROS 2 message type | Default launch remap | Use |
| --- | --- | --- | --- |
| `~/input/pointcloud` | `sensor_msgs/msg/PointCloud2` | `/perception/obstacle_segmentation/pointcloud` | Point-cloud obstacles; selected by `use_pointcloud_data` |
| `~/input/velocity` | `autoware_vehicle_msgs/msg/VelocityReport` | `/vehicle/status/velocity_status` | Ego longitudinal velocity |
| `~/input/imu` | `sensor_msgs/msg/Imu` | `/sensing/imu/imu_data` | IMU-derived ego path; selected by `use_imu_path` |
| `~/input/predicted_trajectory` | `autoware_planning_msgs/msg/Trajectory` | `/control/trajectory_follower/lateral/predicted_trajectory` | Predicted-trajectory ego path; selected by `use_predicted_trajectory`; **blocked at this pin** |
| `~/input/objects` | `autoware_perception_msgs/msg/PredictedObjects` | `/perception/object_recognition/objects` | Predicted-object targets; selected by `use_predicted_object_data` |
| `/autoware/state` | `autoware_system_msgs/msg/AutowareState` | unchanged | Lifecycle gate; selected by `check_autoware_state` |

These are source interfaces, not accepted logical contracts. In particular, they do not establish complete freshness, validity, timing, uncertainty, observation-health, or degradation semantics.

## Node outputs and observability

| Output | Type/mechanism | Meaning and limit |
| --- | --- | --- |
| `/diagnostics` task `aeb_emergency_stop` | `diagnostic_updater` → `diagnostic_msgs/msg/DiagnosticArray` | ERROR-level collision indication; **not** a brake command |
| `~/metrics` | `tier4_metric_msgs/msg/MetricArray` | Collision-assessment metrics |
| `~/debug/obstacle_pointcloud` | `sensor_msgs/msg/PointCloud2` | Debug obstacle point cloud |
| `~/debug/markers` | `visualization_msgs/msg/MarkerArray` | Debug visualization |
| `~/debug/rss_distance` | `tier4_debug_msgs/msg/Float32Stamped` | Debug RSS distance |
| `~/debug/processing_time_detail_ms` | `autoware_utils/ProcessingTimeDetail` | Processing-time detail |
| `~/virtual_wall` | `visualization_msgs/msg/MarkerArray` | Virtual-wall visualization |

Diagnostics, metrics, and debug topics provide transient observability. They do not by themselves implement evidence persistence, provenance, retention, time alignment, or acceptance.

## Coverage of the nine logical components

| Logical component | Status | Source-backed coverage | Retained gap or blocker |
| --- | --- | --- | --- |
| State Acquisition and Normalization | **Partial** | Typed point-cloud, velocity, IMU, trajectory, object, and Autoware-state subscribers; transforms and local processing | No complete freshness, consistency, validity, timing, normalization, or independent observation-health contract |
| Ego Path Prediction | **Partial** | IMU-derived and predicted-trajectory-derived path code exists | IMU branch is available; predicted-trajectory branch is blocked by `DEF-AEBS-PHY-001`; logical path semantics and acceptance evidence remain open |
| Target Processing | **Available, configuration-dependent** | Point-cloud clustering/path filtering and a predicted-object branch | Coverage depends on `use_pointcloud_data` and `use_predicted_object_data`; target-relevance requirement satisfaction is not accepted |
| Collision Risk Evaluation | **Available as source realization only** | RSS-distance checks, collision persistence, and collision diagnostic | Source availability is not accepted requirement satisfaction for thresholds, operating range, timing, or braking assumptions |
| Intervention Decision and Arbitration | **Partial** | Local collision decision and Autoware-state check | No driver override, complete operating context/inhibition, degradation arbitration, or arbitration against other commands |
| Driver Warning Management | **Gap** | None | Warning request, timing, escalation, modality, and HMI integration remain unallocated |
| Emergency Intervention Coordination | **Partial source contribution; no realization allocation** | ERROR-level `aeb_emergency_stop` diagnostic | The diagnostic is not the logical `EmergencyInterventionRequest`; diagnostic/failure-state routing, external emergency/MRM handling, retention/release, command gating, vehicle interface, and actuation are required |
| Health and Degradation Supervision | **Partial** | Diagnostic updater and limited input-presence checks | No complete input-health policy or owned valid/degraded/unavailable state behavior |
| Evidence Recording | **Partial** | Diagnostics, metrics, debug point cloud/markers/RSS/processing time, and virtual wall | No evidence-event schema, persistence, retention, provenance, time alignment, or acceptance criteria |

No responsibility from INC-AEBS-006 disappears merely because this package lacks it. Missing responsibilities remain integration or implementation obligations.

## Required emergency-control chain

The selected package emits an emergency diagnostic, not a physical intervention request or actuator command. The required chain is:

```text
AEB diagnostic: aeb_emergency_stop on /diagnostics
        │
        ▼
Diagnostic / failure-state bridge
        │
        ▼
External emergency / MRM handler
        │
        ▼
Command gate
        │
        ▼
Vehicle interface
        │
        ▼
Brake ECU / actuator
```

Every downstream element, interface, retention/release rule, failure mode, and test result must be selected and verified before making an emergency-intervention or braking-actuation claim. The diagnostic must not be wired directly to an actuator or described as a brake command.

At the pinned revision, `autoware_diagnostic_graph_aggregator` is a candidate
bridge from `/diagnostics` to `/system/operation_mode/availability`, which
`autoware_mrm_handler` consumes. However, no active repository graph
configuration routing `aeb_emergency_stop` into that result was verified; the
only repository hit in the scenario-simulator adapter configuration is commented
out. The bridge and its configuration therefore remain an explicit blocker, not
an assumed Autoware connection.

## Blocking source findings

### DEF-AEBS-PHY-001 — Predicted-trajectory branch

**Status: blocked.** In pinned [`node.cpp` lines 743–754](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/src/node.cpp#L743-L754), the predicted-trajectory `generateEgoPath` overload reserves an empty local `Path`, then evaluates `path.back()` before the first `push_back` while filtering close points. The pinned [default configuration](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/config/autonomous_emergency_braking.param.yaml) sets `use_predicted_trajectory: true`.

The predicted-trajectory branch is therefore blocked unless an upstream-fixed revision replaces this pin or a reviewed patch is applied and tested. Upstream has **not been contacted**, and this artifact makes **no fix claim**.

### DEF-AEBS-PHY-002 — Stale launch contract

**Status: blocked.** Pinned [launch XML line 16](https://github.com/autowarefoundation/autoware_universe/blob/f603d8759c92fb2f423f1544844e13086d79ad09/control/autoware_autonomous_emergency_braking/launch/autoware_autonomous_emergency_braking.launch.xml#L16) remaps `~/input/odometry` through `$(var input_odometry)`. The launch file does not declare that argument, and the current node has no odometry subscriber.

The launch contract is stale and cannot be accepted as-is. Correct or remove the remap, review the intended interface, and execute launch validation. Upstream has **not been contacted**, and this artifact makes **no fix claim**.

## Proposed simulation-first pilot configuration

A risk-reducing candidate is:

```yaml
use_predicted_trajectory: false
use_imu_path: true
```

This avoids the known predicted-trajectory branch while retaining the source-available IMU path. It is **proposed and unexecuted**. It is not evidence that the IMU path is safe, that launch succeeds, that collision decisions satisfy requirements, or that braking occurs.

Before pilot execution:

1. correct or replace the stale launch contract;
2. pin every parameter and remapping;
3. build and launch the exact source baseline;
4. exercise input-health, collision, and non-collision cases;
5. inspect diagnostic levels, timing, persistence, and release behavior;
6. verify the external emergency/MRM chain independently.

## Explicit blockers

| Blocker | Blocks | Release condition |
| --- | --- | --- |
| `BLK-AEBS-PHY-001` / source defect 001 | Predicted-trajectory pilot branch | Upstream-fixed source or reviewed patch, followed by executed tests |
| `BLK-AEBS-PHY-002` / source defect 002 | Acceptance of pinned launch contract | Corrected launch and executed launch validation |
| `BLK-AEBS-PHY-003` | End-to-end intervention or braking claim | Configure and verify diagnostic/failure-state routing, then allocate and test the emergency/MRM handler, command gate, vehicle interface, and brake ECU/actuator in INC-AEBS-008/009 |
| `BLK-AEBS-PHY-004` | Complete realization of the logical baseline | Allocate, implement, and verify warning, override, context, degradation, retention, and evidence responsibilities |

## Claim boundaries

This increment makes **no** claim of:

- UNECE R152 compliance;
- certification, homologation, or production readiness;
- real-vehicle execution;
- braking actuation;
- calibrated requirement satisfaction or safety;
- an upstream report, acceptance, or fix.

Source inspection establishes traceable implementation coverage and defects only. Runtime evidence remains not executed.

## Acceptance criteria

- [ ] Repository, commit, package, version, license, source URLs, and checked date are explicit.
- [ ] Exact node inputs and relevant outputs are inventoried with message types and default remaps where present.
- [ ] All nine logical components have explicit source coverage and missing-responsibility status.
- [ ] Both source defects are pinned, linked, and treated as blockers.
- [ ] The diagnostic-to-actuator chain and its external ownership are explicit.
- [ ] The pilot configuration remains labeled proposed and unexecuted.
- [ ] No compliance, certification, production, real-vehicle, or braking-actuation claim is made.
- [ ] The SysML slice exposes physical structure, reusable interface definitions with typed boundary delegation, and logical-to-physical realization mappings without requirement-satisfaction claims.

## Validation status

- Artifact status: source inspected against the pinned commit.
- Runtime/build/simulation status: not executed in this increment.
- SysML validation: maintainer-run privileged Syside validation requested for the complete textual model root; no local Jetson validation is claimed.
- Repository validation: `python scripts/check_repo.py`, `python scripts/smoke_test.py`, YAML parse, and `git diff --check` are required before publication.
