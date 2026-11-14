# Driver-assistance increment

A product line that requires every member product to brake for a vehicle ahead
cannot take in a new driving application on the strength of its demonstration
videos. It needs a verdict: for each requirement and each scenario, did the
application warn and brake as required, in a run that others can repeat? This
increment asks that of a camera-only driver-assistance application,
[VisionPilot](https://github.com/autowarefoundation/vision_pilot) of the
Autoware Foundation.

**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context,
Phase 3 classification, Phase 4 stakeholder needs and Phase 5 requirements,
proposal.** No implementation, run, result, product-line admission or
compliance is claimed.

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
  candidate. ADR 0026, accepted, gives every member a display, so it tells no
  member apart; the feature model keeps `hmiDisplay` optional only so that
  configurations which are not members can leave it out. No member differs by a
  warning mode either. Whether the acoustic warning becomes common content of
  the driver warning is open. A comment on the HMI gap records both.
- **View:** the table view `driverAssistanceClassificationView` exposes only
  the candidate.

`tests/test_driver_assistance_capability_classification.py` pins the
candidate, its two traces, the two comments and the view. The Phase 3 gate
checks only that each recorded characteristic is a feature candidate or
deferred scope; review judges the classification.

## Stakeholder needs (Phase 4)

The [stakeholder needs](../../textual-notation-of-model/packages/features/driving/driver_assistance_needs_requirements.sysml)
say what the parties of the Phase 1 concerns expect of the candidate. Each
need is held by the parties it serves and leads its source with the concern
it comes from. Each has one planned stakeholder review on the Phase 2
scenarios it covers, carried out by the roles that check the answer.

- `NEED-DRIVING-008`: the candidate requests the warning and commands the
  braking when a collision with a stationary or a slower moving vehicle ahead
  is imminent. Vehicle occupants and road users. Reviewed by `SC-DRIVING-016`
  on `SC-DRIVING-012` and `SC-DRIVING-013`.
- `NEED-DRIVING-009`: no warning and no emergency braking when no collision is
  imminent. Vehicle occupants and road users. Reviewed by `SC-DRIVING-017` on
  `SC-DRIVING-014` and `SC-DRIVING-015`.
- `NEED-DRIVING-010`: a warning request at the candidate's boundary, so that
  the AAOS SDV warns the driver on its display and as a sound. Vehicle
  occupants. Reviewed by `SC-DRIVING-018` on `SC-DRIVING-012` and
  `SC-DRIVING-013`.
- `NEED-DRIVING-011`: each run identifies the candidate revision and the
  configuration it ran with. Verification engineers and product-line
  engineers, who use the run identity in their own work. Reviewed by
  `SC-DRIVING-019` on all four scenarios.

Three concerns get no need of their own: the criteria for a vehicle target,
the Eclipse S-CORE path of the command and the warning request, and the
independence of the braking command. Their roles check the answer rather than
use it, so each is a question for a planned review. `NEED-DRIVING-008` names
all three in its source, and `SC-DRIVING-016` asks them. The planned reviews,
not the needs, ask that no autopilot, replay or overlay acts instead of the
candidate. No need states a number: Phase 5 derives the criteria, their limits
and the time of the warning before the braking. Phase 4 kept VisionPilot's
runtime contract at the pinned revision as a comment for Phase 5, whose
rationales now state it: only its ROS 2 build reads a live speed and commands
a vehicle, and its warnings reach only its own visualization and log. The
speed-following, lane-keeping and lane-departure functions get no need, since
no case judges them.

`tests/test_driver_assistance_needs_requirements.py` pins the needs, their
holders and sources, the planned reviews and their scenarios, and the
wording a need may not use. The Phase 4 gates check that each need has a
statement, a stakeholder, a source, a rationale and a planned review; review
judges whether the needs are the right ones.

## Requirements (Phase 5)

The [requirements](../../textual-notation-of-model/packages/features/driving/driver_assistance_needs_requirements.sysml)
derive what the candidate driver-assistance system shall do from the four
needs. There are nine, within the scope's cap of ten. Each has one subject,
the candidate, one verification method and its success criteria. Five are
functional; Phase 6 allocates each of those to a function.

- `REQ-DRIVING-036` `reqEmergencyBrakingForImminentCollision`, from
  `NEED-DRIVING-008`, functional, test: commands 5.0 m/s² or more when a
  collision is imminent.
- `REQ-DRIVING-037` `reqImpactSpeedWithinLimit`, from `NEED-DRIVING-008`,
  performance, test: hits a vehicle target no faster than the limit of the
  regulation for a car.
- `REQ-DRIVING-038` `reqDrivingCommandOverSCORE`, from `NEED-DRIVING-008`,
  design constraint, test: gives its driving command only over the Eclipse
  S-CORE path.
- `REQ-DRIVING-039` `reqIsolateEmergencyBrakingFromSCORE`, from
  `NEED-DRIVING-008`, independence constraint, analyze: no failure of the
  S-CORE path causes an emergency braking that the candidate did not command.
- `REQ-DRIVING-040` `reqWithholdWarningRequest`, from `NEED-DRIVING-009`,
  functional, test: no warning request while no collision is imminent.
- `REQ-DRIVING-041` `reqWithholdEmergencyBraking`, from `NEED-DRIVING-009`,
  functional, test: no emergency braking while no collision is imminent.
- `REQ-DRIVING-042` `reqWarningRequestBeforeEmergencyBraking`, from
  `NEED-DRIVING-010`, functional, test: the warning request at least 1.0 s of
  simulation time before the emergency braking starts.
- `REQ-DRIVING-043` `reqWarningRequestOverSCORE`, from `NEED-DRIVING-010`,
  design constraint, test: gives its warning request to the AAOS SDV only over
  the Eclipse S-CORE path.
- `REQ-DRIVING-044` `reqRecordCandidateIdentity`, from `NEED-DRIVING-011`,
  functional, test: each run records the upstream revision, the local
  difference, the network files and the configuration.

One table, the requirement definition table that the framing names, shows each
requirement with its statement, source, rationale, verification method and
success criteria. It answers the criteria concern of Phase 1,
`vehicleTargetCriteriaConcern`: the source and the rationale of each criterion
for a vehicle target name the provision of the regulation it comes from, the
product-line requirement it judges, whose obligation it is and what a
simulation cannot show of it.

**The terms that carry the criteria.** The package defines each term once.

- *Emergency braking* is a command of the candidate for a deceleration of at
  least 5.0 m/s², the braking demand of the regulation. It starts with the
  first such command after a command for less. The candidate marks its own
  emergency braking for a planned deceleration beyond 5.0 m/s²; when it slows
  the vehicle for a curve or for a vehicle ahead by less, that is no emergency
  braking.
- A collision is *imminent* where the tests of the regulation make it so: in
  every judged run of `SC-DRIVING-012` and `SC-DRIVING-013`, and in no run of
  `SC-DRIVING-014` or `SC-DRIVING-015`. The regulation gives the word no
  value, and the requirements set none.
- A *setting* is a scenario with an approach speed and its tolerance: the
  stationary target of `SC-DRIVING-012` at 20, 42 and 60 km/h; the target of
  `SC-DRIVING-013`, moving at 20 km/h, at 30 and 60 km/h; the curve of
  `SC-DRIVING-014` at 30 km/h; and the vehicle ahead of `SC-DRIVING-015` at 40
  km/h. The speeds of the first two scenarios are test speeds of the
  regulation, those of the last two come from its guidance. Each setting runs
  twice, and both runs count.
- A *judged run* is a run of `SC-DRIVING-012` or `SC-DRIVING-013` with the
  approach of the test of the regulation: the vehicle travels straight, its
  centre line within 0.2 m of that of the target, for at least 2 s before the
  *functional part*. That part starts at the latest instant at which the
  vehicle travels at its approach speed, within the tolerance, with a time to
  collision of at least 4 s, and ends when the vehicle hits the target or
  comes to its speed. A run that misses this, or has no functional part, is
  reported with what it missed and is not judged.

**Whose obligation each criterion is.**

- The candidate's: the braking demand, the speed at impact, the warning
  request and its lead of 1.0 s, and no reaction where none is due. For the
  speed at impact, the simulated vehicle and its brakes stand in for a real
  one.
- The Eclipse S-CORE path's and the AAOS SDV's: 0.2 s of that lead. Each mode
  of the warning, on the display and as a sound, is due within 0.2 s of
  wall-clock time after the request, and so at least 0.8 s before the start of
  the emergency braking while the simulation runs no faster than wall-clock
  time, a condition of the bench. Phases 6 to 8 allocate it.
- System 2's: the settings, the scenarios and the simulated configuration.

A run shows nothing of what a simulation cannot show of a criterion; the
rationale of each criterion names it. Among it are the target that the
regulation prescribes, the measured road surface, the illumination, the test
masses, and the service brakes and the anti-lock function of a real vehicle.

**Values set in Phase 5.** Each is a choice of this increment, not of the
regulation:

1. The emergency braking starts with the first command for 5.0 m/s² or more
   after a command for less: the demand value of the regulation, and the bound
   of the candidate's own emergency band.
2. Imminence follows the tests of the regulation, not a threshold that the
   regulation does not give.
3. 0.2 s of the lead of 1.0 s is the share of the S-CORE path and the AAOS
   SDV; the regulation asks for the warning to the driver at the latest 0.8 s
   before the start of the emergency braking.
4. The limits are those of a car in running order, because the simulated
   vehicle carries no load.
5. Each setting runs twice and both runs count, so a run that misses its
   criterion stays in the result and no repeated run takes its place.
6. The functional part starts at the latest instant that the approach allows,
   so the bench does not choose it.
7. Where no reaction is due, the criterion is none: no warning request and no
   emergency braking. The approach speeds of those two scenarios come from the
   guidance of the regulation, which gives their speeds and times to
   collision; each run records the rest.
8. The independence of the emergency braking from the S-CORE path follows the
   protected emergency command path of the product line (`REQ-MW-006`), and an
   analysis of the realization of Phase 8 shows it.

The rationales state VisionPilot's runtime contract at the pinned revision,
which Phase 4 kept as a comment for Phase 5; the comment is gone. They cite
the files of the application by file name and line, and
[upstream.md](../../textual-notation-of-model/packages/features/driving/upstream.md#visionpilot)
gives each with its path.

`tests/test_driver_assistance_requirements.py` pins the requirements, their
needs, kinds and methods, the values that each statement, rationale and
criterion carries, the terms, the gap record, the table, the wording a
statement may not use and the path of each file that a rationale cites. The
Phase 5 gates check that each requirement has a statement, derives from a
need, has one subject and one verification method; review judges whether they
are the right ones.

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
**Phase 6**: the functional architecture, which allocates each functional
requirement to a function; its first gate is
`functionalRequirementAllocatedToFunction`. Do not jump from the requirements
to implementation, and claim no runtime gate.

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
tests/test_driver_assistance_capability_classification.py
tests/test_driver_assistance_needs_requirements.py -q`. These are
repository and lexical checks, not SysML semantic validation and not runtime
verification. Use `python scripts/validate_sysml.py` where a licensed
validator is available, or request the maintainer-run **Privileged Syside
Validation** on the reviewed head. The framing view and its published diagram
come from that Syside run.
