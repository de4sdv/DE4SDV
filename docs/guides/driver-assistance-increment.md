# Driver-assistance increment

A product line that requires every member product to brake for a vehicle ahead
cannot take in a new driving application on the strength of its demonstration
videos. It needs a verdict: for each requirement and each scenario, did the
application warn and brake as required, in a run that others can repeat? This
increment asks that of a camera-only driver-assistance application,
[VisionPilot](https://github.com/autowarefoundation/vision_pilot) of the
Autoware Foundation.

**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context
and Phase 3 classification, proposal.** No implementation, run, result,
product-line admission or compliance is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/driving/driver_assistance_framing.sysml):
  `INC-DRIVING-002`, its engineering question, charter, scope, assumptions,
  open gaps and Phase 1 concerns.
- [Syside framing review view](../../textual-notation-of-model/packages/features/driving/VIEWS.md):
  the generated model review artifact, not a runtime architecture claim.
- [Upstream provenance](../../textual-notation-of-model/packages/features/driving/upstream.md#visionpilot)
  and the
  [questions for the maintainers](../../textual-notation-of-model/packages/features/driving/upstream.md#questions-requiring-upstream-engagement).

Orkun Yilmaz owns the increment. One identity covers phases 0 to 11.
Closed-loop verification belongs to Phase 10 of this increment. A readiness
probe comes before the architecture rests on what it tests.

## The engineering question

> Does a camera-only driver-assistance application, with its commands on the
> Eclipse S-CORE command path, request the collision warning and command the
> braking that the product line requires for a vehicle target, with the
> warning shown on the AAOS SDV display and sounded, when criteria derived
> from UNECE R152 judge its closed-loop behavior in simulation? A verdict for
> each requirement and scenario answers this. A recording of a run that looks
> right does not.

The increment supports one decision: whether the candidate goes forward on its
own warning and braking, with named additions from the platform, or not at
all. The additions are named from the requirements that fail and from the gaps
of this increment; the increment builds none of them. A fail is a result to
record. It is no reason to change a scenario or a criterion until the
candidate passes.

## What the increment judges

| In scope | Out of scope |
|---|---|
| The warning request and the braking for a stationary and for a slower moving vehicle target ahead. | Pedestrian and bicycle targets. |
| The collision warning that the AAOS SDV gives the driver in two modes, on its display and as a sound: whether each mode is given, and when, relative to the warning request and to the start of the emergency braking. | How well the candidate holds speed, distance and lane. These functions run; no case judges them. |
| Two scenarios in which neither a warning nor braking is due, taken from the false-reaction scenarios of the regulation. | Driver monitoring, driver override and deactivation. |
| Criteria for a vehicle target derived from UNECE R152, each with what a simulation cannot show. | The haptic mode of the collision warning, the regulation's further rules on the warning signals (their description, the failure and unavailability signals, their check at ignition and their visibility in daylight), and whether a driver perceives the warning. The regulation asks for the warning in at least two modes; this increment judges two, the warning on the display and the sound, by whether and when each is given. The product line's requirement of a collision warning to the driver is answered that far and no further. |
| The candidate's commands reach the simulated vehicle, and its warning request reaches the AAOS SDV, through Eclipse S-CORE; no bypass. | Changing the Autoware-based AEBS or reusing its evidence for this candidate. |
| A pass or a fail for each requirement and scenario, bound to the candidate revision that ran. | Training the candidate's networks, or tuning the candidate or a scenario until a case passes. |
| | On-road operation, production readiness, safety approval, compliance, type approval or certification. |

The scope is one configuration and at most ten requirements. Phase 5 derives
those requirements from the product line's requirements on the collision
warning, the emergency braking and the false reaction. The regulation-derived
criteria of record are in
[`aebs-regulatory-source.yaml`](../../methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml);
the clauses for a vehicle target are not yet anchored there.

## Concerns (Phase 1)

A verdict is only useful if it answers the questions of the people who rely
on it. Phase 1 names those questions: one concern per question of the
in-scope items, held by the parties whose interest it states. The occupants
and the road users hold their own concern beside the engineering roles. Each
concern is typed by the SAF or DE4SDV concern that asks its question, and its
text names the view of a later phase that answers it. The framing viewpoint
frames all six until those views exist.

- **Vehicle target and no reaction:** `vehicleTargetResponseConcern`. The
  vehicle warns its driver and brakes when a collision with a vehicle ahead is
  imminent, and does neither otherwise. Operational capability; vehicle
  occupants and road users. Answered by the operational story of Phase 2.
- **Vehicle target, braking:** `emergencyBrakingIndependenceConcern`. Which
  software element of the candidate realizes the emergency braking, and how
  its braking command keeps the independence of the protected emergency
  command path. Physical functional mapping; safety experts and product-line
  engineers. Answered in Phase 8, by the physical-logical mapping and by the
  view of the claimed path; the lifecycle decision turns on it.
- **Driver warning:** `driverWarningSequenceConcern`. The sequence from the
  warning request to the display, the sound and the start of the emergency
  braking. System process; the driver as a vehicle occupant, and safety
  experts. Answered by the system process of Phase 6.
- **Eclipse S-CORE command path:** `scoreCommandAndWarningPathConcern`. The
  driving command and the warning request pass from the candidate through the
  S-CORE path, with no exchange beside it. Physical internal exchange of the
  realization that Phases 6 to 8 decide; the candidate's boundary stays as
  Phase 0 draws it. Systems engineers and product-line engineers. Answered by
  the view of the claimed path in Phase 8.
- **Criteria for a vehicle target:** `vehicleTargetCriteriaConcern`. Each
  criterion traced to the regulation, to the product-line requirement it
  judges and to whose obligation it is, with what a simulation cannot show.
  Regulatory scope without a compliance claim; compliance engineers and
  verification engineers. Answered by the requirements of Phase 5.
- **Verdicts:** `candidateVerdictConcern`. A pass or a fail for each
  requirement and scenario, bound to the candidate revision that ran. A fail
  that the simulated camera image may explain stays a fail. Argumentation
  assurance; product-line engineers and verification engineers. Answered in
  Phase 10.

The Phase 1 gates check that each concern has native stakeholders and a
frame, and that one concern is not the boundary concern. They do not judge
whether the stakeholder, risk and viewpoint coverage is adequate; review does.

## Operational context and story (Phase 2)

Phase 2 implements the boundary that Phase 0 draws and does not move it. The
[operational context](../../textual-notation-of-model/packages/features/driving/driver_assistance_operational_context.sysml)
holds the candidate as a black box and the System 1 parts around it.

- **System of interest:** `candidateSystem`, typed by
  `DriverAssistanceSystem`, the charter's system of interest. No nested parts
  until the architecture phases.
- **Context:** the vehicle, the road environment, a stationary and a moving
  vehicle target, the Eclipse S-CORE path (`SCORECommandAndWarningPath`), the
  AAOS SDV (the guest definition of INC-MW-011, imported alone) with the
  warning presentation, and the driver. The S-CORE path and the AAOS SDV stay
  outside the candidate, as the Phase 1 concern on the path says.
- **Flows across the boundary:** the front-camera image and the vehicle speed
  in; the driving command and the warning request out, both through the
  S-CORE path. The driver only receives the collision warning.
- **Story:** `driverAssistanceStory` includes one use case per scenario:
  `SC-DRIVING-012`, a stationary vehicle target ahead; `SC-DRIVING-013`, a
  slower moving vehicle target ahead; `SC-DRIVING-014`, a stationary vehicle
  just outside the guard pipes of a curve; `SC-DRIVING-015`, a vehicle ahead
  that turns off at a corner while the vehicle goes straight on. The last two
  follow situations of the regulation's false-reaction scenarios. Phase 2
  proposes them; Phase 5 confirms the selection and states the criterion
  (`gapVehicleTargetCriteria`).
- **Views:** a context view and a story view. The story view also frames
  `vehicleTargetResponseConcern`, which Phase 1 says the story answers.
- **System 2 stays out:** CARLA, the cloud hosts, the scenario runner, the
  evaluators, the capture and the recordings stay in
  `driverAssistanceVerificationEnvironment`.

`tests/test_driver_assistance_operational_context.py` pins the boundary, the
bindings, the scenarios, the flows, the views and the traces to Phase 0.

## Capability classification (Phase 3)

The increment adds one characteristic that distinguishes member products:
**VisionPilot as the vehicle application**, the feature candidate
`visionPilotDrivingStack` of the
[capability classification](../../textual-notation-of-model/packages/features/driving/driver_assistance_capability_classification.sysml).
It traces to the driving-stack variability that the governed scope defers and
answers the framing's admission gap (`gapCandidateAdmission`). Core elements
are common by default and get no record.

- **Inputs and outputs:** at the pinned revision the application reads one
  front-camera image and the vehicle speed, and writes steering and
  acceleration.
- **Sensing and runtime:** the candidate requires the camera, so Phase 9 adds a
  `requiresFeatures` constraint and leaves LiDAR and radar selectable.
  Camera-only sensing gets no record of its own: the feature model already
  makes LiDAR optional. The candidate also requires Linux on the main side: its
  live camera source uses V4L2, a Linux interface. ROS 2 is a build option,
  which its upstream simulator path uses; at the pinned revision only that
  build carries steering and acceleration to a vehicle.
- **Why the feature model waits for Phase 9:** the candidate needs a middleware
  adapter to Eclipse S-CORE, which Phase 8 realizes first and Phase 9 derives.
  Phase 9 also decides whether the configuration selects the application's
  speed-following and lane-keeping functions, which no case of this increment
  judges. They get no record of their own: the feature model already holds them
  as optional features. Nor do the application's lane-departure warnings, which
  come with it and which no case judges either.
- **Scope decisions:** the candidate would be a new planned member; Autoware
  and LiDAR stop being common at its admission; Vehicle-Target AEBS and the
  independence of the protected emergency command path stay common, and the
  candidate has to meet both (`gapNoSeparateEmergencyFunction`). Three items
  are open. First, the Linux and ROS 2 runtime of Autoware: the candidate does
  not use the Autoware runtime, and ROS 2 is a build option of it. Second, the
  integration mode: ADR 0023, accepted, takes Eclipse S-CORE out of the
  reference-only set into the S-CORE-integrated alternative once its scope pull
  request takes effect, but each integration-mode alternative characterizes
  exactly one planned member, so whether the candidate shares that alternative
  or needs its own is open. Third, the sound (below). On the model as it stands
  no configuration of the candidate exists; once Phase 9 adds it, a
  configuration is valid, but the scope does not admit it. A comment on the
  admission gap records these decisions, and the member decision amends ADR
  0014 with them. This increment admits nothing.
- **Display and sound** (`gapDriverHmiInProductLine`): neither is a feature
  candidate. On the model as it stands the HMI display is an optional feature;
  ADR 0026, accepted, makes a display common content of every member once its
  scope pull request takes effect. No member differs by a warning mode.
  Whether the acoustic warning becomes common content of the driver warning
  is open. A comment on the HMI gap records both.
- **View:** the table view `driverAssistanceClassificationView` exposes only
  the candidate.

`tests/test_driver_assistance_capability_classification.py` pins the
candidate, its two traces, the two comments and the view. The Phase 3 gate
checks only that each recorded characteristic is a feature candidate or
deferred scope; review judges the classification.

## What the framing already records as open

Each point is a gap of the model, in the model's own words.

- **No criteria for a vehicle target** (`gapVehicleTargetCriteria`). The
  regulation-derived criteria of record cover the pedestrian and the bicycle
  target. None exists for a vehicle target.
- **No emergency function apart from the speed planner**
  (`gapNoSeparateEmergencyFunction`). At the inspected revision the
  application marks its forward-collision warning and its emergency braking
  from the acceleration that its speed planner computes. It has no emergency
  function apart from that planner. Whether the candidate's braking can stand
  for the common capability, or the platform has to add an independent
  function, is open. The lifecycle decision turns on it.
- **No warning output** (`gapWarningOutput`). At the inspected revision the
  application writes its steering and its acceleration to its vehicle
  interface. That interface carries no warning. The warnings go to the
  application's own visualization and to its own data log, each only when it
  is switched on. A warning request at the system boundary, which the AAOS SDV
  needs, is an output that the application does not have.
- **No result on the DE4SDV bench** (`gapCandidateBehaviorUnverified`). No
  closed-loop result of the application exists on the DE4SDV bench, and DE4SDV
  has run neither the inspected revision nor a change to it.
- **No Eclipse S-CORE binding** (`gapScoreIntegration`). The application is
  one process with its own loop. At the inspected revision it has no binding
  to Eclipse S-CORE communication and no S-CORE supervision. How its driving
  command, its warning request and its state enter the S-CORE path without a
  bypass is open.
- **Simulated images** (`gapCameraImageAndGeometry`). Whether the application
  detects the simulated target at the distances that the criteria need is not
  known. Its distance estimate depends on a camera calibration that has to
  match the simulated camera.
- **No admission** (`gapCandidateAdmission`). This increment admits no member
  and changes no scope decision. Phase 3 classifies the candidate and names
  the scope decisions that the owner would have to take.
- **No upstream contact and no rights clearance**
  (`gapUpstreamContactAndRights`). The upstream maintainers are not yet
  involved. Involve them before deep adoption or vendoring, and show them a
  result about their project before it is published.
- **The HMI display's place in the product line**
  (`gapDriverHmiInProductLine`). The feature model holds the HMI display as an
  optional feature that requires the AAOS SDV guest, and neither governed
  member selects it, while the product line requires every member product to
  warn the driver. The owner decided on 2026-11-13 that every member product
  has an HMI display, realized according to the member's integration mode;
  that revision of the governed scope is made outside this increment.

The gaps refer to the
[AEBS requirements](../../textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml)
and to the
[governed scope](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md).

## Boundaries

The candidate driver-assistance system is a proposed **System 1** subject. Two
parts of **System 1** are outside its boundary, and neither is an enabler: the
Eclipse S-CORE path that carries its driving command to the actuation and its
warning request to the AAOS SDV, and the AAOS SDV, which gives the driver the
collision warning on its display and as a sound. CARLA, the cloud hosts, the
scenario runner, the evaluators, the capture of the display and of the sound,
and the recordings are **System 2** enablers, not vehicle features. The
capture observes the AAOS SDV and is no part of it.

A criterion that is derived from the regulation and met in simulation holds
for the simulated configuration only. It is no statement about compliance or
type approval.

## Next obligation and execution limits

Use the Method Check of the reviewed pull request to select the next
obligation, not the phase number alone. The next model obligation is
**Phase 4**: the stakeholder needs, elaborated from the Phase 1 concerns; its
first gate is `needHasStatement`. Do not jump from this classification to
implementation, and claim no runtime gate.

Involve the upstream maintainers before deep adoption, and show them a result
about their project before it is published. Before a paid cloud run, refresh
the regional price, the capacity and the available credit, obtain the owner's
authorization for the campaign, and verify a bounded shutdown with the
evidence exported first. Starting this increment launches no compute and
authorizes no spend.

## Check the framing change

Run `sysand sync`, `python scripts/check_repo.py`,
`python scripts/smoke_test.py` and
`python -m pytest tests/test_driver_assistance_framing.py
tests/test_driver_assistance_operational_context.py
tests/test_driver_assistance_capability_classification.py -q`. These are
repository and lexical checks, not SysML semantic validation and not runtime
verification. Use `python scripts/validate_sysml.py` where a licensed
validator is available, or request the maintainer-run **Privileged Syside
Validation** on the reviewed head. The framing view and its published diagram
come from that Syside run.
