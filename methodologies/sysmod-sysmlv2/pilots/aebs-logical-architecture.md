# INC-AEBS-006 — AEBS logical architecture

- **Status:** Draft
- **Domain:** Logical
- **Parent:** INC-AEBS-005
- **Selected baseline:** Decomposed, rule-based logical architecture

## Decision requested

Review whether this logical decomposition and its contracts are stable enough to become the target for the first physical software realization with Autoware.

This increment does **not** model Autoware, ROS 2, Eclipse S-CORE, Android SDV/AAOS, ECUs, sensors, networks, or brake actuators. Those begin in INC-AEBS-007 and INC-AEBS-008.

## Why this increment exists

The functional baseline establishes what AEBS does. It does not yet identify which solution-neutral elements own path prediction, target processing, collision-risk evaluation, override arbitration, emergency-state retention, degradation, or evidence recording.

INC-AEBS-006 closes that ownership gap before implementation names are introduced.

```text
Functional baseline
        │
        ▼
INC-AEBS-006: logical ownership and contracts
        │
        ▼
INC-AEBS-007: Autoware and ROS 2 realization
        │
        ▼
INC-AEBS-008: middleware, execution, sensors and actuators
        │
        ▼
INC-AEBS-009: executable scenarios and evidence
```

## Logical boundary

The system of interest is the **Vehicle-Target AEBS Logical System**.

```text
Vehicle motion observation ──────┐
Target observation ──────────────┤
Driver override observation ─────┤
Operating context ───────────────┤
Subsystem health ────────────────┤
                                 ▼
                    AEBS Logical System
                                 │
                 ┌───────────────┼────────────────┐
                 ▼               ▼                ▼
          Warning request   Emergency         Failure/evidence
                            intervention       outputs
                            request
```

The external providers are intentionally unspecified. They may later be realized through direct vehicle interfaces, ROS 2, a vehicle-platform adapter, or simulation.

## Logical decomposition

```text
Vehicle-Target AEBS Logical System
│
├── State Acquisition and Normalization
├── Ego Path Prediction
├── Target Processing
├── Collision Risk Evaluation
├── Intervention Decision and Arbitration
├── Driver Warning Management
├── Emergency Intervention Coordination
├── Health and Degradation Supervision
└── Evidence Recording
```

| Logical component | Primary responsibility |
| --- | --- |
| State Acquisition and Normalization | Validate and normalize vehicle-motion and target observations |
| Ego Path Prediction | Produce a technology-neutral predicted ego path |
| Target Processing | Select and characterize targets relevant to that path |
| Collision Risk Evaluation | Assess collision risk using state, path and open braking assumptions |
| Intervention Decision and Arbitration | Decide emergency-intervention intent while considering override, context and degradation |
| Driver Warning Management | Produce a logical warning request without prescribing HMI technology |
| Emergency Intervention Coordination | Issue and retain a logical emergency-intervention request |
| Health and Degradation Supervision | Determine valid, degraded and unavailable operation and request failure indication |
| Evidence Recording | Observe risk, health, warning and intervention events and emit an evidence event |

### Independence rule

Driver override, health supervision, emergency-state retention, degradation, and evidence recording remain independent of the primary collision-risk mechanism. A later integrated or learned realization may not erase these responsibilities.

## Functional-to-logical mapping

| Functional action | Logical owner or owners |
| --- | --- |
| `AcquireVehicleAndTargetState` | State Acquisition and Normalization |
| `AssessForwardCollisionRisk` | Ego Path Prediction; Target Processing; Collision Risk Evaluation |
| `RequestDriverWarning` | Driver Warning Management |
| `EvaluateDriverOverride` | Intervention Decision and Arbitration |
| `RequestEmergencyBraking` | Intervention Decision and Arbitration; Emergency Intervention Coordination |
| `MonitorAEBSFailureStatus` | Health and Degradation Supervision |
| `RecordAEBSEvidenceEvent` | Evidence Recording |

SysML v2 allocations express responsibility assignment. They do not claim that the logical element is a software node, process, ECU, or physical component.

## Logical exchanges

### Boundary inputs

- vehicle-motion observation;
- target observation;
- driver-override observation;
- AEBS operating context;
- subsystem health.

### Internal exchanges

- normalized vehicle state;
- normalized target state;
- observation-health status;
- predicted ego path;
- relevant target state;
- collision-risk assessment;
- intervention decision;
- degradation state.

### Boundary outputs

- driver-warning request;
- emergency-intervention request;
- failure-indication request;
- AEBS evidence event.

## Emergency-control boundary

The existing functional model uses `EmergencyBrakingCommand`. The logical architecture treats this as AEBS intervention intent, not direct ownership of a brake-actuator command.

```text
AEBS intervention intent
        │
        ▼
Emergency supervision and arbitration
        │
        ▼
Vehicle-control command
        │
        ▼
Brake controller and actuator
```

The last three steps are physical-domain responsibilities. Their concrete Autoware/MRM, command-gate, vehicle-interface, network and actuator realization is deferred.

## Middleware-independent service boundaries

INC-AEBS-006 distinguishes two integration concerns.

### Safety-control services

- driver override;
- emergency intervention;
- vehicle control.

### General vehicle-platform services

- vehicle state;
- target observation;
- lifecycle and operating mode;
- health and diagnostics;
- warning and HMI;
- evidence and persistency.

ROS 2/DDS will be modeled as Autoware's internal application runtime in INC-AEBS-007. S-CORE or Android SDV/AAOS will be modeled as candidate vehicle-platform service realizations in INC-AEBS-008. They are not a single interchangeable middleware box.

A later physical realization must not place an unverified HLOS or generic vehicle-platform middleware in the emergency-control path.

## Logical state semantics

The logical system recognizes these states:

```text
unavailable
standby
monitoring
warning requested
intervention requested
emergency active
degraded
override accepted
```

This increment assigns ownership and makes the states visible. It does not invent numeric transition guards or release criteria that the current draft requirements do not provide.

Emergency-state retention belongs to Emergency Intervention Coordination. Valid/degraded/unavailable determination belongs to Health and Degradation Supervision.

## Architecture decisions

### DEC-AEBS-LOG-001 — First logical baseline

Use a decomposed, rule-based logical baseline for the first realization.

### DEC-AEBS-LOG-002 — No empty learned variant

Keep these future decision dimensions visible:

```text
Decomposition: decomposed pipeline | integrated policy
Mechanism:     rule-based | learned | hybrid
```

Only the decomposed rule-based choice is modeled now. A learned or hybrid SysML variation will be added only when a concrete second realization exists.

### DEC-AEBS-LOG-003 — Intervention request is not actuator command

AEBS owns intervention intent. Emergency supervision, command arbitration, vehicle interfacing and brake actuation belong to physical realization.

### DEC-AEBS-LOG-004 — Middleware stays physical

Autoware, ROS 2/DDS, S-CORE and Android SDV/AAOS are physical software/platform realization choices. The logical model exposes only the contracts they must realize.

## Open gaps

| Gap | Owner | Status |
| --- | --- | --- |
| Collision thresholds, braking assumptions, timing and operating ranges | Collision Risk Evaluation | Open |
| Warning modality, timing and escalation | Driver Warning Management | Open |
| Driver-override qualification, duration and priority | Intervention Decision and Arbitration | Open |
| Emergency-state retention and release criteria | Emergency Intervention Coordination | Open |
| Missing/stale/inconsistent-input degradation policy | Health and Degradation Supervision | Open |
| Evidence schema, timing, storage and acceptance criteria | Evidence Recording | Open |
| Concrete service providers and middleware adapters | INC-AEBS-007/008 | Deferred |

These are not reasons to block logical decomposition. They are requirements and realization gaps that now have explicit owners.

## Remaining increment plan

### INC-AEBS-007 — Autoware physical software realization

Map each logical component and exchange to a pinned Autoware/ROS 2 artifact. Record exact packages, nodes, topics, diagnostics, parameters, source identity, fit/gap status, required adapters, the diagnostic-to-MRM path, and the two known upstream defects. No logical responsibility may disappear because Autoware lacks it.

### INC-AEBS-008 — Physical platform, middleware and deployment

Refine the shared layered architecture into:

```text
Autoware application
  → ROS 2/DDS application runtime
  → vehicle-platform integration adapter
  → S-CORE | Android SDV/AAOS | other selected services
  → OS and execution domains
  → compute, network, sensors, HMI and brake control
```

The first deployment is simulation-first. Selection of the first S-CORE or Android SDV/AAOS pilot is made only after the Autoware fit/gap assessment shows what services are actually required and testable.

### INC-AEBS-009 — Executable integration and V&V evidence

Run the complete observation-to-braking chain in repeatable scenarios. Record source and parameter identities, input/output data, decision and diagnostic timing, MRM/command behavior, stopping outcome, pass/fail result, and unresolved gaps.

## Acceptance criteria

- [ ] Every functional action has at least one logical owner.
- [ ] Every logical component has one bounded primary responsibility.
- [ ] External vehicle, target, driver, context, and health inputs are explicit.
- [ ] Internal exchanges are typed and directional.
- [ ] Intervention request is distinguished from actuator-command ownership.
- [ ] Override, health, emergency retention and evidence remain independent responsibilities.
- [ ] Safety-control and general platform-service boundaries are explicit.
- [ ] No physical technology appears as a logical realization.
- [ ] Missing thresholds, guards, degradation policy and evidence criteria remain visible.
- [ ] Logical structure, internal exchange and functional mapping views are available for review.

## Validation status

- Public repository checks: pending.
- Local SysML validation: not run by DE4SDV policy.
- Privileged SysML validation: required after initial model review.
- Semantic review: must check allocation meaning, logical/physical separation, boundary ownership, and consistency with the YAML control artifact.
