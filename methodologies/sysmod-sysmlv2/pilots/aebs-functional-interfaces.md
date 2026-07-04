# AEBS functional interface refinement

Status: draft  
Increment: `INC-AEBS-005`  
Parent: `INC-AEBS-004`

## Purpose

This increment refines the INC-AEBS-004 functional behavior boundary into typed functional interface ports. It makes the AEBS functional boundary directional and classifies each VSS signal attribute by signal character, direction, producer, consumer, and upstreaming posture.

It does **not** define logical components, ECUs, services, sensors, networks, deployment topology, or regulatory compliance evidence.

## What changed from INC-AEBS-004

INC-AEBS-004 defined the composite flow `VehicleTargetAEBSFunctionalFlow` with `in item` / `out item` boundary parameters. Those parameters were typed but had no port definitions — the boundary was implicit in the action signature.

INC-AEBS-005 introduces:

1. **Port definitions** — each boundary-crossing item now has a typed `port def` with explicit `in`/`out` direction.
2. **Functional chain part** — `VehicleTargetAEBSFunctionalChain` performs the INC-AEBS-004 composite flow and owns the boundary ports.
3. **Signal classification** — every VSS signal attribute in every functional item is classified.
4. **Upstreaming posture** — every DE4SDV candidate VSS extension signal has a proposed upstreaming stance with rationale and review priority.

The port definitions and functional chain are added to the existing `aebs_functional_behavior.sysml` file inside the `FunctionalBehavior` package, not in a separate file. SysIDE does not support cross-file sibling package imports within the same `DE4SDV` namespace.

Port-to-action bindings use the `perform` block parameter binding pattern from the SysML v2 Pilot Implementation corpus: inside a `perform` body, bind performed action parameters to port items using `=` assignment.

```sysml
perform vehicleTargetAEBSFunctionalFlow : VehicleTargetAEBSFunctionalFlow {
    in item driverOverrideInput = driverOverrideInputIn.driverOverrideInput;
    out item emergencyBrakingCommand = emergencyBrakingCommandOut.emergencyBrakingCommand;
}
```

This is the correct SysML v2 construct for binding performed action parameters to port items. The earlier `flow from port.x to action.x` pattern was rejected by SysIDE as a direction-redefinition error.

## Functional boundary ports

### Inbound

| Port | Item type | Signal character | What it carries |
|---|---|---|---|
| `DriverOverrideInputInbound` | DriverOverrideInput | observation | Conscious driver override of AEBS intervention |
| `AEBSFailureStatusInbound` | AEBSFailureStatus | status | Detected AEBS-related failure conditions |

### Outbound

| Port | Item type | Signal character | What it carries |
|---|---|---|---|
| `DriverWarningRequestOutbound` | DriverWarningRequest | command | Request to warn the driver |
| `EmergencyBrakingCommandOutbound` | EmergencyBrakingCommand | command | Request to command emergency braking |
| `FailureIndicationRequestOutbound` | FailureIndicationRequest | command | Request to indicate AEBS failure |
| `AEBSEvidenceEventOutbound` | AEBSEvidenceEvent | event | Evidence-relevant event record for V&V |

### Internal (not on boundary)

| Item | Why internal | Open question |
|---|---|---|
| VehicleMotionState | Acquired internally by AcquireVehicleAndTargetState | Should this become an external inbound? (GAP-AEBS-INT-010) |
| ForwardTargetState | Same — acquired internally | Same gap |
| CollisionRiskAssessment | Produced and consumed entirely within the chain | Threshold/TTC/activation logic open |
| DriverOverrideDecision | Internal decision consumed by RequestEmergencyBraking | Override semantics open |

## Signal character classification

Each VSS signal attribute in the functional items is classified as:

| Character | Meaning | Count |
|---|---|---|
| observation | Perceived state from sensors or external sources | 8 |
| assessment | Functional judgment derived from observations | 2 |
| command | Functional request to an external subsystem | 4 |
| status | Reported state from an external subsystem | 4 |
| event | Recorded occurrence for later evidence | 1 |

## Upstreaming posture for DE4SDV VSS extensions

| VSS path | Priority | Rationale |
|---|---|---|
| `Vehicle.ADAS.AEBS.DriverOverride.IsActive` | **high** | No COVESA VSS signal captures conscious driver override of AEBS. Real gap. |
| `Vehicle.ADAS.AEBS.EmergencyBraking.IsCommanded` | **high** | VSS has EBA.IsEngaged (status) but no AEBS-specific braking command. Distinction matters for functional safety. |
| `Vehicle.ADAS.AEBS.CollisionRisk.IsDetected` | medium | AEBS-specific collision risk detection missing from VSS. |
| `Vehicle.ADAS.AEBS.DriverWarning.IsActive` | medium | AEBS-specific driver warning activation missing from VSS. |
| `Vehicle.ADAS.AEBS.IsError` | medium | VSS has EBA/ABS errors but no AEBS-level error aggregate. |
| `Vehicle.ADAS.AEBS.FailureIndication.IsActive` | low | No VSS signal for AEBS-specific failure indication. May be too specific for upstream. |
| `Vehicle.ADAS.AEBS.EvidenceEvent.IsRecorded` | low | Evidence event recording is DE4SDV-specific. May not fit upstream VSS. |

## Open review gaps

| Gap | What remains open |
|---|---|
| GAP-AEBS-INT-003 | Collision-risk assessment thresholds, TTC, activation logic |
| GAP-AEBS-INT-004 | Driver warning request: modality, timing, observability |
| GAP-AEBS-INT-005 | Emergency braking command: authority, priority, arbitration |
| GAP-AEBS-INT-006 | Driver override: conscious vs unconscious, threshold, duration |
| GAP-AEBS-INT-007 | AEBS failure model: which errors are in-scope |
| GAP-AEBS-INT-008 | Failure indication: HMI/diagnostic semantics |
| GAP-AEBS-INT-009 | Evidence event: schema, log destination, retention |
| GAP-AEBS-INT-010 | Should VehicleMotionState / ForwardTargetState become external inbound ports? |

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

After interface ports are reviewed:

1. **Logical realization** — allocate functions to logical components/services, now that the functional boundary is explicit.
2. **Upstream VSS proposal** — prepare a COVESA review document for the high-priority extension candidates.

Do not jump to physical/software architecture before logical allocation reviews the functional interfaces.