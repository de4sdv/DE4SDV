# AEBS Operational Story

## Status

Draft operational-domain increment for `INC-AEBS-002`. This is not a requirements baseline, SysML v2 model, test procedure, or UNECE R152 compliance claim.

## Purpose

This story turns the AEBS framing baseline into the first stakeholder-visible operational slice. It defines the situation DE4SDV will use before deriving requirements or functional interfaces.

The story is intentionally narrow:

```text
vehicle-target forward collision risk mitigation
```

Pedestrian-target and bicycle-target behavior are acknowledged as candidate future scope, but they are not modeled here.

## Source and framing inputs

| Input | Role |
|---|---|
| `INC-AEBS-001` | framing baseline for scope, method stack, VSS policy, assumptions, and gaps |
| UNECE R152 revision reviewed privately | candidate regulatory anchor for terminology and scope awareness |
| DE4SDV increment workflow | method flow from operational context toward needs, requirements, functional model, V&V, and evidence |

This document uses regulatory source knowledge only as private grounding. It does not copy regulatory text and does not claim compliance.

## System layers

| Layer | Meaning in this story |
|---|---|
| System 1 | configured SDV variant with AEBS-related vehicle-target behavior |
| System 2 | DE4SDV engineering/evidence workflow that captures the story, assumptions, gaps, and later V&V links |
| System 3 | DE4SDV open-source review ecosystem that accepts or rejects the modeling increment |

## Operational boundary

### In scope

- Subject vehicle traveling in-lane behind a passenger-car target.
- Imminent forward collision risk with the vehicle target.
- Collision warning at operational-story level.
- Emergency braking at operational-story level.
- Driver conscious override as an operational path.
- Failure handling as an operational concern.
- Evidence-relevant event expectations as a System 2 concern.

### Out of scope

- Pedestrian-target operational story.
- Bicycle-target operational story.
- Complete UNECE R152 test procedure.
- Compliance, certification, or type-approval claim.
- Sensor physics or perception algorithm design.
- Brake controller design.
- Logical service/component allocation.
- Physical/software deployment architecture.
- VSS signal selection or mapping.

## Actors and external systems

| ID | Actor/system | Role |
|---|---|---|
| `ACT-SUBJECT-VEHICLE` | Subject vehicle | configured SDV variant under consideration |
| `ACT-DRIVER` | Driver | receives warning and may consciously override intervention |
| `ACT-VEHICLE-TARGET` | Vehicle target | passenger-car target ahead in same lane |
| `ACT-ROAD-ENVIRONMENT` | Road environment | operational context; detailed conditions deferred |
| `ACT-DE4SDV-EVIDENCE-BASELINE` | DE4SDV evidence baseline | captures assumptions, gaps, and later evidence expectations |
| `ACT-OPEN-SOURCE-REVIEWER` | DE4SDV reviewer | checks that the slice is traceable and not overclaimed |

## Operational capability

`CAP-AEBS-FCRM` — **Forward collision risk mitigation**

A configured SDV variant should reduce the risk or severity of a forward rear-end in-lane collision with a vehicle target under selected operating conditions by detecting imminent collision risk, warning the driver when required, and commanding emergency braking when activation conditions are met.

This is an operational capability statement, not a final requirement.

Whether this is a common product-line capability or a feature depends on member-product applicability. Do not automatically classify “AEBS” as a feature.

## Nominal operational story

`STORY-AEBS-VEHICLE-TARGET-001`

A configured SDV variant travels in-lane behind a passenger-car target. The relative motion creates an imminent forward collision risk under stated operating conditions. The AEBS-related behavior detects the risk, provides an appropriate driver warning when required, and commands emergency braking if activation conditions are met. The driver can consciously override the intervention. The DE4SDV System 2 baseline records assumptions, gaps, and evidence-relevant event expectations for later review.

## Preconditions

- Subject vehicle is active and traveling in-lane.
- Vehicle target is ahead in the same lane.
- Selected operating conditions are in scope for the scenario seed.
- AEBS-related behavior is available for the configured variant.

## Trigger

Imminent forward collision risk emerges between the subject vehicle and the vehicle target.

## Nominal sequence

| Step | Actor | Action |
|---|---|---|
| 1 | Subject vehicle | Travels in-lane behind the vehicle target. |
| 2 | AEBS-related behavior | Detects imminent forward collision risk under selected operating conditions. |
| 3 | AEBS-related behavior | Provides collision warning to the driver when warning is required by the selected behavior profile. |
| 4 | Driver | May consciously override the intervention. |
| 5 | AEBS-related behavior | Commands emergency braking when activation conditions are met and no overriding condition prevents intervention. |
| 6 | DE4SDV evidence baseline | Records planned evidence expectations, assumptions, and gaps for later verification and validation increments. |

## Alternate paths

| ID | Path | Deferred question |
|---|---|---|
| `ALT-AEBS-OVERRIDE` | Driver consciously overrides the AEBS action. | What override inputs/conditions are accepted? |
| `ALT-AEBS-FAILURE` | AEBS-related behavior has a detected failure. | What warning/failure/safe-operation behavior is expected? |
| `ALT-AEBS-NO-ACTIVATION` | Collision risk does not satisfy selected activation conditions. | What non-activation criteria prevent false braking? |

## Stakeholder needs seed

| ID | Stakeholder | Need |
|---|---|---|
| `N-AEBS-OP-001` | Validation stakeholder | Road users and vehicle occupants need the configured SDV variant to reduce forward rear-end in-lane collision risk with a vehicle target under defined operating conditions. |
| `N-AEBS-OP-002` | Systems engineer | Systems engineers need the AEBS operational boundary, actors, assumptions, and out-of-scope cases to be explicit before requirements are derived. |
| `N-AEBS-OP-003` | Product-line engineer | Product-line engineers need the AEBS operational capability to stay separate from feature/common-capability classification until member-product applicability is known. |
| `N-AEBS-OP-004` | Compliance engineer | Compliance engineers need regulatory source assumptions and operational-scope gaps to be visible without implying UNECE R152 compliance. |
| `N-AEBS-OP-005` | Verification engineer | Verification engineers need the operational story to identify later verification targets without pretending that acceptance criteria already exist. |

## Validation scenario seeds

| ID | Validates | Method | Question | Status |
|---|---|---|---|---|
| `VAL-AEBS-OP-001` | `N-AEBS-OP-001` | stakeholder scenario review | Does the story represent a meaningful stakeholder-visible collision-risk mitigation situation without exceeding first-slice scope? | `planned` |
| `VAL-AEBS-OP-002` | `N-AEBS-OP-002` | inspection | Are actors, boundary, assumptions, and out-of-scope cases explicit enough to derive draft requirements next? | `planned` |
| `VAL-AEBS-OP-003` | `N-AEBS-OP-003` | inspection | Does the capability statement avoid prematurely classifying AEBS as a feature? | `planned` |
| `VAL-AEBS-OP-004` | `N-AEBS-OP-004` | inspection | Are regulatory assumptions visible without compliance wording or copied source text? | `planned` |
| `VAL-AEBS-OP-005` | `N-AEBS-OP-005` | inspection | Does the story identify later verification targets while keeping acceptance criteria as future work? | `planned` |

## Open gaps

| ID | Gap |
|---|---|
| `GAP-AEBS-OP-001` | Operating speed, distance, road, weather, and target-condition parameters remain undefined. |
| `GAP-AEBS-OP-002` | Activation, warning, braking, override, and non-activation criteria remain undefined. |
| `GAP-AEBS-OP-003` | No design-input requirements are derived in this operational increment. |
| `GAP-AEBS-OP-004` | No VSS signal mappings are selected in this operational increment. |
| `GAP-AEBS-OP-005` | No SysML v2 operational package exists yet; this is a structured pre-modeling baseline. |

## Acceptance criteria

This operational slice is acceptable for the next increment if:

- the operational boundary identifies actors, in-scope behavior, and out-of-scope behavior;
- the story remains vehicle-target focused and does not include pedestrian or bicycle behavior;
- stakeholder needs are kept separate from design-input requirements;
- validation scenario seeds are recorded for each stakeholder need;
- gaps are explicit;
- no compliance, certification, or implementation-readiness claim is made.

## Next increment

`INC-AEBS-003` — AEBS needs and draft requirements.

Entry condition: this operational context is reviewed and accepted as a sufficient basis for deriving draft requirements.
