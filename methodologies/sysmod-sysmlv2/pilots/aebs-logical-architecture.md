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

INC-AEBS-006 closes that ownership gap before implementation names are introduced. The logical model is not justified by renaming actions as components. It earns its place where it adds responsibility boundaries, decomposition, shared ownership, persistent state, or producer-consumer contracts.

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
Intervention context ────────────┤
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
| Emergency Intervention Coordination | Issue and retain a logical intervention request only from an affirmative arbitrated decision |
| Health and Degradation Supervision | Determine valid, degraded and unavailable operation and request failure indication |
| Evidence Recording | Observe risk, intervention decision, degradation, warning, intervention request and failure events and emit an evidence event |

### Independence rule

Driver override, health supervision, emergency-state retention, degradation, and evidence recording remain independent of the primary collision-risk mechanism. A later integrated or learned realization may not erase these responsibilities.

## Functional-to-logical mapping

| Functional action | Logical owner or owners | Architectural responsibility added |
| --- | --- | --- |
| `AcquireVehicleAndTargetState` | State Acquisition and Normalization | Establishes the external-observation boundary; validates and normalizes vehicle and target observations; produces observation health separately from availability |
| `AssessForwardCollisionRisk` | Ego Path Prediction; Target Processing; Collision Risk Evaluation | Splits one functional responsibility into path prediction, target relevance and collision-risk ownership with explicit intermediate exchanges |
| `RequestDriverWarning` | Driver Warning Management | Owns the warning-request boundary and warning state independently from intervention state and HMI realization |
| `EvaluateDriverOverride` | Intervention Decision and Arbitration | Combines override with risk, intervention eligibility/inhibition context and degradation in one arbitration boundary; the same owner also participates in emergency-intervention responsibility |
| `RequestEmergencyBraking` | Intervention Decision and Arbitration; Emergency Intervention Coordination | Separates decision from retention/coordination and replaces actuator-like command ownership with a logical intervention-request boundary |
| `MonitorAEBSFailureStatus` | Health and Degradation Supervision | Reconciles input and subsystem health and solely owns valid/degraded/unavailable availability state |
| `RecordAEBSEvidenceEvent` | Evidence Recording | Creates a cross-cutting observation boundary over risk, decision, degradation, warning, intervention and failure exchanges |

Similar names are retained where they improve traceability; similarity is not the architectural argument. SysML v2 allocations express responsibility assignment. They do not, by themselves, prove decomposition or claim that the logical element is a software node, process, ECU, or physical component. The added responsibility, state and exchange topology above carry the architectural content.

## Logical exchanges

### Boundary inputs

- vehicle-motion observation;
- target observation;
- driver-override observation;
- AEBS intervention context, limited to eligibility and inhibition facts;
- subsystem health.

System lifecycle is owned by the Vehicle-Target AEBS Logical System and is not supplied through this intervention-context boundary. AEBS availability is also excluded: Health and Degradation Supervision reconciles observation health and subsystem health and is the sole logical producer of availability/degradation state.

### Internal exchanges

- normalized vehicle state;
- normalized target state;
- observation-health status;
- predicted ego path;
- relevant target state;
- collision-risk assessment;
- intervention decision;
- degradation state;
- warning request observed by Evidence Recording;
- emergency-intervention request observed by Evidence Recording;
- failure-indication request observed by Evidence Recording.

### Item-contract maturity

The exchanged item definitions have different contract maturity. Three remain intentionally **nominal and opaque** in this increment:

- `AEBSOperatingContext` establishes the intervention eligibility/inhibition boundary, but its facts and value domains are not yet specified;
- `PredictedEgoPath` establishes the producer-consumer boundary, but its horizon, coordinate frame, validity, timing, uncertainty and representation are not yet specified;
- `ObservationHealthStatus` separates observation-specific health from AEBS availability, but its freshness, consistency, validity, timing and aggregation semantics are not yet specified.

Two inherited types contain attributes but remain insufficient for the responsibilities assigned here:

- `VehicleMotionState` carries speed and longitudinal acceleration, but path prediction still lacks heading/curvature or an explicit straight-line assumption, pose/frame, timestamp and validity semantics;
- `ForwardTargetState` carries distance and time gap, but path-relative target processing still lacks lateral position or an explicit in-path assumption, target identity/extent, frame, timestamp and validity semantics.

An item definition with only documentation is valid as a named type, but it is not a complete interface schema. Attribute-bearing types are likewise not automatically adequate for every downstream responsibility. These definitions establish candidate logical boundaries without inventing physical/software schemas; their missing semantic content must be resolved before the affected interfaces can become a physical-realization baseline.

### Boundary outputs

- driver-warning request;
- emergency-intervention request;
- failure-indication request;
- AEBS evidence event.

## Emergency-control boundary

The functional baseline uses `EmergencyBrakingCommand`. INC-AEBS-006 introduces a distinct `EmergencyInterventionRequest` item for logical intent and traces it to that functional output without inheriting command, engagement, or lighting semantics.

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

State semantics are split into independent dimensions instead of one mutually exclusive state list:

| Dimension | Logical owner | States |
| --- | --- | --- |
| Lifecycle | Vehicle-Target AEBS Logical System | standby; monitoring |
| Warning | Driver Warning Management | inactive; warning requested |
| Intervention | Emergency Intervention Coordination | inactive; intervention requested; emergency active |
| Override | Intervention Decision and Arbitration | no override; override accepted |
| Availability | Health and Degradation Supervision | valid; degraded; unavailable |

This increment assigns ownership and makes the states visible. It does not invent numeric transition guards or release criteria that the current draft requirements do not provide. Warning state remains independent from override and intervention state. Health and Degradation Supervision is the sole producer of AEBS availability.

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

AEBS owns `EmergencyInterventionRequest`. The logical type is traced to, but not specialized from, the functional `EmergencyBrakingCommand`. Emergency supervision, command arbitration, vehicle interfacing and brake actuation belong to physical realization.

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
| Intervention eligibility/inhibition facts and value domains | Intervention Decision and Arbitration | Open |
| Predicted-path horizon, frame, validity, timing, uncertainty and representation | Ego Path Prediction | Open |
| Vehicle-motion input sufficiency for path prediction, including pose/frame, timing, validity and heading/curvature or a straight-line assumption | Ego Path Prediction | Open |
| Target-state input sufficiency for path-relative selection, including lateral relevance or an in-path assumption, identity, extent, frame, timing and validity | Target Processing | Open |
| Observation-health freshness, consistency, validity, timing and aggregation semantics | State Acquisition and Normalization | Open |
| Lifecycle transition triggers, guards and source contract | Vehicle-Target AEBS Logical System | Open |
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

## Human-reviewable views

The three SAF-aligned views have distinct membership:

- the structure view exposes the logical system and nine component usages; the tree renderer may list their ports, but this decomposition view does not render bind or flow edges;
- the internal-exchange view selects direct members of the logical-system context, including ports, boundary bindings, and internal flows;
- the functional-mapping view exposes ten named allocation usages.

The current tree renderer is not relationship-complete: it may display ports without drawing the selected bind or flow edges. The textual `bind` and `flow` usages in `VehicleTargetAEBSLogicalSystem` are therefore the authoritative exchange topology. The internal-exchange view remains a bounded selection of that topology, not proof that the generated tree diagram visualizes every connection.

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
- [ ] Nominal and attribute-bearing-but-incomplete contracts remain explicit and are not presented as a stable physical interface baseline.
- [ ] Logical structure, internal exchange and functional mapping views are available for review.

## Validation status

- Public repository checks: passed on the PR branch.
- Local SysML validation: not run by DE4SDV policy.
- Privileged SysML validation: attempted, but the configured Syside license expired before the model could be evaluated.
- Semantic review: two independent static reviews identified and drove corrections to the logical request type, boundary delegation, state ownership, emergency arbitration path, exchange inventory, and view membership.
