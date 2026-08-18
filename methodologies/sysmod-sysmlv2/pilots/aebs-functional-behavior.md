# AEBS functional behavior and VSS candidate signals

Status: draft  
Increment: `INC-AEBS-004`  
Parent: `INC-AEBS-003`

## Purpose

This increment converts the reviewed AEBS operational story and needs/requirements slice into the first functional-architecture model slice in the SAF Conceptual Domain.

It does **not** define logical components, ECUs, services, sensors, networks, deployment topology, or regulatory compliance evidence.

The goal is narrower:

```text
requirements → functional responsibilities → functional information items → generated VSS reuse + DE4SDV VSS extensions → explicit review gaps
```

## Normalization before functional modeling

The earlier AEBS YAML artifacts contained a few terms that were weaker than the current SysML baseline. This increment normalizes only what affects functional modeling:

| Previous wording | Normalized meaning |
|---|---|
| `applicable member products` | `member products` for AEBS common-capability realization |
| `candidate_feature_or_common_capability` for vehicle-target AEBS | `common_capability` for this first vehicle-target slice |
| `deferred_feature_candidate` for pedestrian/bicycle scope | `deferred_product_line_scope` |
| generic `variation_point` classification | native SysML v2 `variation` / `variant` choices |
| `SysML v2 will be introduced later` | SysML v2 is already the reviewed model expression baseline |
| `configured SDV variant` as the main System 1 framing | product-line member product realizing the common AEBS capability |

This is not a broad rewrite of the earlier baselines. It is a targeted semantic correction so `INC-AEBS-004` does not inherit stale wording.

## Functional boundary

The functional subject is:

```text
AEBS common capability functional behavior for the vehicle-target slice
```

Inputs:

- `VehicleMotionState`
- `ForwardTargetState`
- `DriverOverrideInput`
- `AEBSFailureStatus`

Outputs:

- `CollisionRiskAssessment`
- `DriverWarningRequest`
- `EmergencyBrakingCommand`
- `FailureIndicationRequest`
- `AEBSEvidenceEvent`

## Functional responsibilities

| Function | Responsibility | Draft requirement trace |
|---|---|---|
| `AcquireVehicleAndTargetState` | Acquire abstract vehicle-motion and forward-target state | `REQ-AEBS-001` |
| `AssessForwardCollisionRisk` | Determine whether forward collision risk is imminent | `REQ-AEBS-001` |
| `RequestDriverWarning` | Request driver warning when warning conditions are met | `REQ-AEBS-002` |
| `EvaluateDriverOverride` | Evaluate whether conscious override prevents/modifies intervention | `REQ-AEBS-004` |
| `RequestEmergencyBraking` | Request braking when activation conditions are met and no override prevents it | `REQ-AEBS-003` |
| `MonitorAEBSFailureStatus` | Monitor AEBS-related failure status relevant to safe operation | `REQ-AEBS-005` |
| `RecordAEBSEvidenceEvent` | Record evidence-relevant event expectations for later V&V/evidence work | `REQ-AEBS-007` |

`REQ-AEBS-006` constrains the full slice: common-capability, feature-candidate, and native variation/variant classifications must remain explicit.

## VSS reuse and DE4SDV extensions

The functional SysML slice uses generated COVESA VSS signal definitions as attribute types inside item defs where available (via recursive import). When the generated VSS snapshot lacks an AEBS-specific signal needed by this functional slice, this PR adds a DE4SDV candidate extension signal in `DE4SDV_VSS_Extensions.sysml` and uses it as an attribute type in the relevant item def.

These signal definitions are still semantic catalog references. They are not architecture topology and not implementation ownership.

| Functional item | Generated COVESA VSS reuse | DE4SDV VSS extension | Review gap |
|---|---|---|---|
| `VehicleMotionState` | `Vehicle.Speed`, `Vehicle.Acceleration.Longitudinal` | — | units/sampling/conditions still open |
| `ForwardTargetState` | `Vehicle.ADAS.ObstacleDetection.Distance`, `Vehicle.ADAS.ObstacleDetection.TimeGap` | — | target typing and source semantics open |
| `CollisionRiskAssessment` | `Vehicle.ADAS.ObstacleDetection.IsWarning`, `Vehicle.ADAS.ObstacleDetection.WarningType` | `Vehicle.ADAS.AEBS.CollisionRisk.IsDetected` | threshold/TTC/activation logic and extension suitability open |
| `DriverWarningRequest` | `Vehicle.ADAS.ObstacleDetection.IsWarning`, `Vehicle.ADAS.ObstacleDetection.WarningType` | `Vehicle.ADAS.AEBS.DriverWarning.IsActive` | modality/timing/observability and extension suitability open |
| `EmergencyBrakingCommand` | `Vehicle.ADAS.EBA.IsEngaged`, `Vehicle.Body.Lights.Brake.IsActive` | `Vehicle.ADAS.AEBS.EmergencyBraking.IsCommanded` | command semantics and upstream suitability open |
| `DriverOverrideInput` | — | `Vehicle.ADAS.AEBS.DriverOverride.IsActive` | override semantics and upstream suitability open |
| `DriverOverrideDecision` | — | `Vehicle.ADAS.AEBS.DriverOverride.IsActive` | derived decision semantics open |
| `AEBSFailureStatus` | `Vehicle.ADAS.EBA.IsError`, `Vehicle.ADAS.ABS.IsError` | `Vehicle.ADAS.AEBS.IsError` | accepted AEBS failure model open |
| `FailureIndicationRequest` | — | `Vehicle.ADAS.AEBS.FailureIndication.IsActive` | HMI/diagnostic indication semantics open |
| `AEBSEvidenceEvent` | — | `Vehicle.ADAS.AEBS.EvidenceEvent.IsRecorded` | event schema/logging/upstream suitability open |

## Non-claims

This increment does not claim:

- UNECE R152 compliance;
- type approval or homologation readiness;
- physical sensor choice;
- ECU/software deployment;
- logical component allocation;
- accepted VSS interface mapping or accepted upstream VSS extension;
- accepted braking performance thresholds;
- accepted evidence level or evidence sufficiency.

## Next increment after this

The next useful step after review is one of two paths:

1. **Functional interface refinement** — turn generated/extended VSS-backed items into reviewed functional interfaces and decide which extension signals should be proposed upstream.
2. **Logical realization** — only after interface boundaries are clear, allocate functions to logical responsibilities/services.

Do not jump to physical/software architecture before the interface semantics are reviewed.
