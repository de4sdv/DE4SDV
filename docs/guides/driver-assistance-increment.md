# Driver-assistance increment

A product line that requires every member product to brake for a vehicle ahead
cannot take in a new driving application on the strength of its demonstration
videos. It needs a verdict: for each requirement and each scenario, did the
application warn and brake as required, in a run that others can repeat? This
increment asks that of a camera-only driver-assistance application,
[VisionPilot](https://github.com/autowarefoundation/vision_pilot) of the
Autoware Foundation.

**Status: baselined (Phase 11).** The baseline accepts the model of phases 0
to 10 and the bench as built, and as evidence the judged session S1 of
2026-11-21 at bench commit 508649ba: three cases are a fail, five are
inconclusive and one is a pass. No product-line admission, safety, compliance
or type-approval claim follows; see [Baseline (Phase 11)](#baseline-phase-11).

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/driving/driver_assistance_framing.sysml):
  `INC-DRIVING-002`, its engineering question, charter, scope, assumptions,
  open gaps, Phase 1 concerns and the baseline decision of Phase 11.
- [SysML variability and configuration](../../textual-notation-of-model/packages/features/driving/driver_assistance_variability_configuration.sysml):
  the Phase 9 configured product DRIVING-CONFIG-002, bound to the receipt of
  its feature configuration.
- [SysML verification and evidence](../../textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml):
  the Phase 10 cases, the evidence record of a run and the claims, and the
  evidence of record of the judged session S1 with the status of each case.
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
| Two scenarios in which neither a warning nor braking is due, taken from the false-reaction scenarios of the regulation. | The candidate's lane-departure warning and lane-departure avoidance. They come with the application; no case judges them. |
| Criteria for a vehicle target derived from UNECE R152, each with what a simulation cannot show. | The candidate's intelligent speed assistance, which its documentation bases on speed-limit map data. No run of this increment gives it map data, and no case judges it. |
| The candidate's commands reach the simulated vehicle, and its warning request reaches the AAOS SDV, through Eclipse S-CORE; no bypass. | The candidate's hands-free mode as a product function: driving one lane of a highway without the driver's hands. The candidate drives the vehicle in the runs, but no case judges the mode. |
| A pass or a fail for each requirement and scenario, bound to the candidate revision that ran. | Driver monitoring, driver override and deactivation. |
| | The haptic mode of the collision warning, the regulation's further rules on the warning signals (their description, the failure and unavailability signals, their check at ignition and their visibility in daylight), and whether a driver perceives the warning. The regulation asks for the warning in at least two modes; this increment judges two, the warning on the display and the sound, by whether and when each is given. The product line's requirement of a collision warning to the driver is answered that far and no further. |
| | Changing the Autoware-based AEBS or reusing its evidence for this candidate. |
| | Training the candidate's networks, or tuning the candidate or a scenario until a case passes. |
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
- **Declared conditions:** the candidate's documentation declares its
  hands-free mode only for highways and motorways with clearly marked lane
  lines, in fair weather and visibility, at up to 70 mph and away from
  construction zones and roadwork, with a human driver supervising it at all
  times. Supervision falls under driver monitoring, which is out of scope, so
  the road, the weather and the speed place each scenario. `SC-DRIVING-012` and
  `SC-DRIVING-013` are set on a highway-type road in fair weather, inside these
  conditions. `SC-DRIVING-014` and `SC-DRIVING-015` lie outside them, since a
  tight curve and a turn at a corner are no highway situations. They stay in
  the scope, and Phase 10 reports their runs apart
  (`gapDeclaredOperatingConditions`).
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
  as optional features. Nor do the application's lane-departure warning and
  avoidance, its intelligent speed assistance and its hands-free mode, which
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
  `NEED-DRIVING-008`, functional, test: commands 5.0 m/s² or more while
  avoiding a vehicle ahead needs that much.
- `REQ-DRIVING-037` `reqImpactSpeedWithinLimit`, from `NEED-DRIVING-008`,
  performance, test: when a collision is imminent, hits the vehicle ahead no
  faster than the limit of the regulation for a car.
- `REQ-DRIVING-038` `reqDrivingCommandOverSCORE`, from `NEED-DRIVING-008`,
  design constraint, test: gives its driving command only over the Eclipse
  S-CORE path.
- `REQ-DRIVING-039` `reqDetectableDrivingCommand`, from `NEED-DRIVING-008`,
  design constraint, analyze: gives each driving command in a form that lets
  the actuation detect its loss, delay, repetition or corruption on the Eclipse
  S-CORE path.
- `REQ-DRIVING-040` `reqWithholdWarningRequest`, from `NEED-DRIVING-009`,
  functional, test: starts its warning request only while a collision is
  imminent.
- `REQ-DRIVING-041` `reqWithholdEmergencyBraking`, from `NEED-DRIVING-009`,
  functional, test: starts an emergency braking only while a collision is
  imminent.
- `REQ-DRIVING-042` `reqWarningRequestBeforeEmergencyBraking`, from
  `NEED-DRIVING-010`, functional, test: when a collision is imminent, gives the
  warning request at least 1.0 s of simulation time before the emergency
  braking starts.
- `REQ-DRIVING-043` `reqWarningRequestOverSCORE`, from `NEED-DRIVING-010`,
  design constraint, test: gives its warning request to the AAOS SDV only over
  the Eclipse S-CORE path.
- `REQ-DRIVING-044` `reqRecordCandidateIdentity`, from `NEED-DRIVING-011`,
  functional, test: records its candidate identity before its first driving
  command of each run: the upstream revision, the local difference, the SHA-256
  of each network file and of each configuration file, and the settings of its
  launch, verbatim.

One table, the requirement definition table that the framing names, shows each
requirement with its statement, source, rationale, verification method and
success criteria. It answers the criteria concern of Phase 1,
`vehicleTargetCriteriaConcern`: the source and the rationale of each criterion
for a vehicle target name the provision of the regulation it comes from, the
product-line requirement it judges, whose obligation it is and what a
simulation cannot show of it.

**The terms that carry the criteria.** The package defines each term once.

- A collision is *imminent* when the vehicle is at most 4.0 s from a vehicle
  ahead in its lane, its *time to collision*, and would have to brake at 1.0
  m/s² or more to come to the speed of that vehicle just as it reaches it, its
  *needed deceleration*: the square of the closing speed over twice the
  distance. The regulation gives the word no value; both values are the owner's
  decision of 2026-11-14. The tests of the regulation judge a run from a time
  to collision of 4 s on. With 1.0 m/s², in every setting at a constant
  approach speed the collision becomes imminent at least 1.11 s before 5.0 m/s²
  is needed, which leaves room for the warning lead of 1.0 s. The vehicle ahead
  that turns off in the guidance of the regulation needs 0.47 to 0.67 m/s² at
  the speeds and times to collision that the guidance names, and the stationary
  vehicle beyond the curve stands outside the lane, so neither collision is
  imminent.
- *Emergency braking* is a command of the candidate for a deceleration of at
  least 5.0 m/s². It starts with the first such command after a command for
  less. The regulation calls any braking demand of the system an emergency
  braking; the requirements take its demand value of 5.0 m/s² as the bound,
  because the candidate brakes for its speed control with the same planner.
  When it slows the vehicle for a curve or for a vehicle ahead by less, that is
  no emergency braking.
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
  collision of at least 4 s, and ends when the vehicle hits the target or comes
  to its speed. A run that misses this, or has no functional part, is reported
  with what it missed and is not judged. A setting is judged when both of its
  runs are; a setting with a run that is not judged meets none of the criteria
  of `REQ-DRIVING-036`, `REQ-DRIVING-037` and `REQ-DRIVING-042`. The further run
  of `SC-DRIVING-012` that stops the Eclipse S-CORE path, which
  `REQ-DRIVING-038` and `REQ-DRIVING-043` name, is no run of a setting and no
  judged run; only the stop clauses of those two requirements read it (the
  stop-run decision of 2026-11-18).

**Whose obligation each criterion is.**

- The candidate's: the braking demand, the speed at impact, the warning request
  and its lead of 1.0 s, no warning request and no emergency braking that
  starts while no collision is imminent, the form of its driving command, and
  the record of its identity. For the speed at impact, the simulated vehicle
  and its brakes stand in for a real one.
- The Eclipse S-CORE path's and the AAOS SDV's: 0.2 s of that lead. Each mode
  of the warning, on the display and as a sound, is due within 0.2 s of
  wall-clock time after the request, and so at least 0.8 s before the start of
  the emergency braking while the simulation runs no faster than wall-clock
  time. Phases 6 to 8 allocate it.
- The product's that holds the Eclipse S-CORE path: rejecting a driving command
  whose loss, delay, repetition or corruption the actuation can detect
  (`REQ-MW-006`).
- System 2's: the settings, the scenarios, the simulated configuration, a
  simulation that runs no faster than wall-clock time, and in each run of
  `SC-DRIVING-014` and `SC-DRIVING-015` a record of the speeds and times to
  collision that the guidance names.

A run shows nothing of what a simulation cannot show of a criterion; the
rationale of each criterion names it. Among it are the target that the
regulation prescribes, the measured road surface, the illumination, the test
masses, and the service brakes and the anti-lock function of a real vehicle.

**Values set in Phase 5.** Each is a choice of this increment, not of the
regulation:

1. A collision is imminent at a time to collision of at most 4.0 s and a needed
   deceleration of at least 1.0 m/s², the owner's decision of 2026-11-14. The
   regulation gives the word no value.
2. The emergency braking starts with the first command for 5.0 m/s² or more
   after a command for less. The regulation calls any braking demand an
   emergency braking and asks for at least 5.0 m/s² once a collision is
   imminent; the bound keeps the speed control of the candidate, which brakes
   with the same planner, apart from its emergency braking. A demand below 5.0
   m/s² may therefore come before the warning request; the regulation would
   count the lead from it.
3. The emergency braking is due while 5.0 m/s² is needed to avoid the vehicle
   ahead, a condition of the world rather than a detection by the candidate.
4. The relative approach speed, which selects the limit of the speed at impact,
   is taken when the collision becomes imminent; the regulation takes the test
   speed. At a constant approach speed the two are the same.
5. The warning request is due in every imminent collision. The regulation asks
   for the warning above the relative speed up to which the vehicle can still
   avoid the collision; the need asks for it in every imminent collision, and
   the requirement follows the need.
6. 0.2 s of the lead of 1.0 s is the share of the S-CORE path and the AAOS SDV;
   the regulation asks for the warning to the driver at the latest 0.8 s before
   the start of the emergency braking.
7. The limits are those of a car in running order, because the simulated
   vehicle carries no load.
8. Each setting runs twice and both runs count, so a run that misses its
   criterion stays in the result and no repeated run takes its place; the
   regulation allows one repeat. A setting whose runs are not both judged meets
   none of the criteria that rest on judged runs.
9. The functional part starts at the latest instant that the approach allows,
   so the bench does not choose it.
10. `REQ-DRIVING-040` and `REQ-DRIVING-041` bind the start of a warning request
    and of an emergency braking in every run, in `SC-DRIVING-012` and
    `SC-DRIVING-013` too before the collision becomes imminent. They bind the
    start because braking can end the imminence while the warning or the
    braking goes on.
11. The approach speeds of the scenarios without a reaction come from the
    guidance of the regulation, which gives their speeds and times to
    collision; System 2 records the rest in each run.
12. The candidate's share of the independence of the emergency braking from the
    S-CORE path is a driving command whose loss, delay, repetition or
    corruption the actuation can detect; rejecting it is the share of the
    product that holds the path (`REQ-MW-006`). An analysis of the realization
    of Phase 8 shows it.

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

## Functional architecture (Phase 6)

The [functional architecture](../../textual-notation-of-model/packages/features/driving/driver_assistance_functional_architecture.sysml)
breaks the candidate driver-assistance system down into four functions, in the
order of one step:

- **`identifyCandidate`** records the candidate identity before the first
  driving command of each run;
- **`assessVehicleAhead`** perceives the lane and the closest vehicle ahead in
  it from the front-camera image and works out, with the vehicle's speed, the
  time to collision, the needed deceleration and whether a collision is
  imminent;
- **`requestWarning`** starts the warning request at the boundary when a
  collision becomes imminent, and starts none while no collision is;
- **`commandVehicle`** gives the one driving command: none before the identity
  is recorded, lane and speed following below 5.0 m/s² of deceleration, and
  the emergency braking.

They are `AllocatableFunction` actions of the functional flow
`DriverAssistanceFunctionalFlow`. The flow takes the front-camera image and
the vehicle speed of Phase 2 in, and gives the driving command and the warning
request out. Inside, the functions exchange the assessment of the vehicle
ahead, the state of the warning request and the record of the candidate
identity. The functions state what the system has to do, not what the
candidate does at its inspected revision, which has no warning output at its
boundary (`gapWarningOutput`); Phase 8 maps them to its software.

Three decisions shape the functional architecture:

- **One command path.** The emergency braking is a mode of `commandVehicle`,
  not a second source of commands, and only `commandVehicle` gives a driving
  command. The braking leaves in the driving command, as the term of Phase 5
  allows. Whether the candidate's braking can stand for the common capability
  stays open (`gapNoSeparateEmergencyFunction`); a function apart from the
  command would decide it in advance.
- **The warning request first.** `requestWarning` starts the request with the
  imminence of the collision, and `commandVehicle` takes the state of the
  request and starts an emergency braking only after it. In each setting at a
  constant approach speed the collision becomes imminent at least 1.11 s
  before 5.0 m/s² is needed, which gives the lead of `REQ-DRIVING-042`.
- **A command the actuation can check.** Each driving command leaves the
  system with its issue time, a sequence count and a check value. By them the
  actuation can detect a delay, a loss or a repetition, and a corruption of
  the command on the path (`REQ-DRIVING-039`). Rejecting what it detects is
  the share of the product that holds the path (`REQ-MW-006`), which Phase 8
  allocates.

Each requirement but two is allocated (`allocatedTo`) to the functions that
carry it: the five functional requirements the gate asks for, and the speed at
impact and the form of the command to `commandVehicle`. `REQ-DRIVING-038` and
`REQ-DRIVING-043`, the Eclipse S-CORE path of the driving command and of the
warning request, are carried by no function. They constrain how the two
outputs travel to the actuation and to the AAOS SDV, and Phase 8 places the
S-CORE elements on those exchanges. An allocation assigns responsibility only;
it claims no satisfaction.

The system in operation is the process `DriverAssistanceSystemProcess`. Its
participants are the parts of the operational context of Phase 2, each the
swim lane of its functions: the vehicle's front camera and motion sensing give
the image and the speed, and the S-CORE path carries the driving command to
the actuation and the warning request to the warning presentation of the AAOS
SDV, which gives the driver the collision warning on the display and as a
sound. The process answers the Phase 1 concern `driverWarningSequenceConcern`
with the sequence and its times:

- the warning request at the boundary at least 1.0 s of simulation time before
  the start of the emergency braking (`REQ-DRIVING-042`);
- each mode of the warning within 0.2 s of wall-clock time after the request,
  the share of the S-CORE path and the AAOS SDV, which Phase 8 divides
  between them;
- so each mode at least 0.8 s before the emergency braking, while the
  simulation runs no faster than wall-clock time, which is the obligation of
  System 2.

The modes of `DriverAssistanceModes` follow from the requirements: identifying
until the identity is recorded, with no driving command; assisting, with no
collision imminent; warning, while a collision is imminent and before an
emergency braking; and the emergency braking, until the collision is no longer
imminent. The conceptual interfaces are the four ports of
`DriverAssistanceFunctionalBoundary`, the system at its boundary: the image
and the speed in, each with its time, and the driving command and the warning
request out. Their items carry ISQ quantities; no vehicle signal specification
is used, and the signal typing starts at Phase 8.

Five views publish the architecture, one per SAF question:

- the breakdown `driverAssistanceFunctionBreakdownView`, which lists the items
  and the four functions of the flow but draws no item flows;
- the matrix `driverAssistanceRequirementFunctionMappingView`, with the
  requirements in rows and the functions in columns;
- the process `driverAssistanceSystemProcessView`, with its participants as
  swim lanes and the items that cross the boundary;
- the table `driverAssistanceModeDependenceTableView` of the modes and what
  the functions that depend on them do in each;
- the tree `driverAssistanceFunctionalInterfaceView` of the four port
  definitions, each with its directed item.

`tests/test_driver_assistance_functional_architecture.py` pins the functions,
their flows and allocations, the process with its times, the modes, the
interfaces and the five views. The Phase 6 gates check that a function exists
and that each functional requirement is allocated to one; review judges
whether they are the right ones.

## Logical architecture (Phase 7)

The
[logical architecture](../../textual-notation-of-model/packages/features/driving/driver_assistance_logical_architecture.sysml)
answers what technology-independent logical elements realize the four
functions. The decomposition subject is the system of interest itself:
`DriverAssistanceLogicalSystem` specializes the functional boundary of Phase 6,
keeps its four ports and owns the system's inside, one level below the
boundary. The context elements of Phase 2 stay outside and undivided. The
package's one usage of the definition, `driverAssistanceLogicalSystem`, exists
for the views, which draw usages; it is the same system as the context's
`candidateSystem`, not a second one.

The owner decided on four logical elements, one per function (2026-11-15):

- **Identity recorder** carries the identification of the candidate. The record
  covers the network and configuration files of the other elements and comes
  before any command, so Phase 8 realizes it beside the software that gives the
  commands.
- **Vehicle-ahead assessor** carries the assessment of the vehicle ahead: the
  one producer of the assessment that both decisions take, and the only element
  that reads the front-camera image (`gapCameraImageAndGeometry`).
- **Warning requester** carries the request of the collision warning and is its
  only source. It stands alone so that Phase 8 can place the request on a
  realization of its own (`gapWarningOutput`).
- **Driving commander** carries the commanding of the vehicle: the one command
  source, with the emergency braking as a mode of its one function
  (`gapNoSeparateEmergencyFunction` stays open).

Each function is allocated to its element by a native allocation from the
definition-nested function usage Phase 6 allocated the requirements to; the
allocation is a responsibility assignment, not a realization, deployment or
runtime claim. The exchanges are connections between typed ports. The boundary
items are delegated from the inherited ports: the front-camera image to the
assessor, the vehicle speed to the assessor and to the driving commander, the
driving command from the driving commander and the warning request from the
warning requester. Inside, the assessment goes from the assessor to the warning
requester and to the driving commander, the warning state from the warning
requester to the driving commander, and the candidate record from the identity
recorder to the driving commander. The warning state carries the order of
REQ-DRIVING-042 across two elements, and the candidate record that of
REQ-DRIVING-044. Nothing runs from the driving commander to another element.
REQ-DRIVING-038 and REQ-DRIVING-043 stay with Phase 8, which carries them by
the elements it places on the path; Phase 8 places each exchange on a
technology. No element, port or exchange names a computer, a process, a
transport or a signal catalogue.

What crosses the boundary agrees in three places: the boundary flows of the
operational context, the ports of Phase 6 and the delegations of Phase 7. No
state output crosses the boundary: no requirement asks for one, and a port
would need an item of Phase 6. There is no driver input, since the driver only
receives, and no configuration port, since the configuration is read at start
and the calibration travels with the image. Phase 7 shows no timing: whether
the reused path carries the warning in time is for the readiness probe of
Phase 8 to show.

Three concerns of this phase are held by the parties they serve: the structure
by system architects and software developers, the function mapping by system
architects and verification engineers, and the internal exchanges by systems
engineers and software developers. One view answers each, per the method's list
of views per phase: the structure as a tree of the SAF System Structure
Definition viewpoint, the mapping as a matrix of function by logical element of
the System Function Mapping viewpoint, and the exchanges as an interconnection
of the System Internal Exchange viewpoint. The phase publishes three views,
listed in
[`VIEWS.md`](../../textual-notation-of-model/packages/features/driving/VIEWS.md).

`tests/test_driver_assistance_logical_architecture.py` pins the system, the
elements and their ports, the exchanges, the allocations, the views and the
guide.

## Physical and software realization (Phase 8)

The
[physical and software realization](../../textual-notation-of-model/packages/features/driving/driver_assistance_physical_software_realization.sysml)
answers what software, hardware and deployment elements realize the four logical
elements, and on which technology the driving command and the warning request
travel. On 2026-11-15 the owner chose that the candidate's process becomes an
Eclipse S-CORE application through a DE4SDV S-CORE interface module: an S-CORE
branch beside the existing interface selection in the application's main
function, before its loop, and one hand-off of the warnings that the planner
already computes, in the loop. The decision logic of the candidate is unchanged.
Every build on the S-CORE path carries this change, which upstream has not
merged, so every verdict names the build, 014e0e7a with the DE4SDV S-CORE
interface, and the candidate record of REQ-DRIVING-044 carries the difference
(`gapCandidateBehaviorUnverified`).

On 2026-11-18 the owner chose that nothing goes upstream before the scenarios of
Phase 10 have run in CARLA: then the VisionPilot maintainers are shown a draft
of the warning output and the interface seam, with the results; nothing is
posted without the owner (the upstream contact decision of 2026-11-18).

The candidate stays one process. Six software elements carry the four logical
elements:

- **Identity recording application** carries the identity recorder: an S-CORE
  application of its own, started first, that hashes every configuration,
  calibration, manifest and network file the candidate's process reads and
  publishes the candidate record on an mw::com event. The candidate publishes no
  driving command before the record has arrived.
- **Camera interface** (DE4SDV) and **perception and fusion** (upstream,
  unchanged) carry the vehicle-ahead assessor. The camera interface hands the
  newest image to the loop and counts the images it drops: the candidate's
  fusion takes two processed frames as 0.1 s apart, so Phase 10 judges no run
  with a dropped image in its judged window. The candidate computes no time to
  collision, no needed deceleration and no imminence, so the assessment is
  realized in part; Phase 10 judges the imminence from the simulator's ground
  truth.
- **Safety guardian planner** (upstream, unchanged) carries both the warning
  requester and the driving commander: the warning requester and the driving
  commander share the planner module, since the forward-collision warning and
  the emergency braking are two ranges of one planned acceleration
  (`gapNoSeparateEmergencyFunction` stays open). Its warnings go to the warning
  request publisher; the warning state that Phase 7 passes from the requester to
  the commander has no realization in the candidate.
- **Vehicle interface** (DE4SDV) carries the driving commander's output: it
  adds the issue time, a sequence count and a 32-bit cyclic redundancy check
  value and publishes the command on an mw::com event.
- **Warning request publisher** (DE4SDV) carries the warning requester's
  output: it publishes the warning request on an mw::com event.

Each logical element is allocated to the elements that carry it, seven
allocations in all; an allocation is a responsibility assignment, no
deployment or runtime claim. The vehicle interface carries
`reqDrivingCommandOverSCORE` and the warning request publisher
`reqWarningRequestOverSCORE`, each by a dependency from its definition.

The S-CORE path and the AAOS SDV stay outside the candidate, as Phase 0 drew
them. Their realizations on the bench carry no logical element: the actuation
adapter, an S-CORE application with a simulator client; the SOME/IP gateway
of the S-CORE services; the SDV Core VM; and the IVI VM with the warning
presentation, a build item of the bench that shows the warning on the display
and plays a sound. The adapter rejects a command whose sequence count, check
value or issue time fails and applies nothing in place of a rejected command:
the simulator keeps the last valid control. The adapter has no stop response.
REQ-DRIVING-038's success criterion runs the stop scenario with the S-CORE
path shut down and requires that no driving command reaches the actuation after
the stop; a stop or neutral control applied by the adapter would blur that
run, and no requirement of this increment asks for one.

Two decisions of INC-DRIVING-001 carry over: the clock decision of 2026-11-08
(CARLA 0.9.16 in synchronous mode with a fixed step of 0.1 s, paced at
wall-clock speed, issue times in simulation time) and the three-host decision
of 2026-11-09 (the S-CORE host, the simulator host and the guest host with
KVM, joined to the guests by a VXLAN segment). The warning request takes the
chain that INC-DRIVING-001 ran into the AAOS SDV, with a new message type that
stays open until Phase 10. Of the 0.2 s that REQ-DRIVING-042 allots from the
request to each mode of the warning, Phase 8 gives 0.1 s for the path and
0.1 s for the presentation; the start of the sound on the guest is unmeasured,
and the split is revisited when it is measured.

On 2026-11-15 the owner also chose a GPU of its own for the S-CORE host, an
NVIDIA L4, for the candidate's networks: the readiness probe of Phase 8 found
the processor alone too slow for the 0.1 s cycle, so the framing's assumption
that the networks run on a processor alone does not hold. The candidate runs
with the CUDA provider that its own configuration sets. The probe also ran
upstream's simulator path with CARLA 0.9.16 as the framing assumed. Still to be
shown before Phase 10: the one S-CORE process linked with the build of ONNX
Runtime for CUDA, and the candidate record reaching a vehicle interface that
subscribes after it was published.

On the same day the owner chose CARLA 1.0 on Unreal Engine 5.8 for the bench's
simulator, in place of CARLA 0.9.16 on Unreal Engine 4, and the build that the
readiness probe ran: commit `14ac3b1a50` of CARLA's branch `ue58-dev`, two
commits after the tag `1.0`, from CARLA's weekly package of 2026-11-15, of which
DE4SDV keeps a copy
([`upstream.md`](../../textual-notation-of-model/packages/features/driving/upstream.md)).
The probe ran its server in synchronous mode with the 0.1 s step at wall-clock
pace on one NVIDIA L4, and its C++ client library, which needs C++20, inside an
S-CORE process whose other code stays C++17. Upstream's camera rig sits on a
vehicle that CARLA 1.0 does not have, so the bench mounts the camera on another
one. The candidate itself has not yet driven on CARLA 1.0.

On 2026-11-17 the owner chose a fixed step of 0.05 s for the bench's simulator,
so that the bench's recording view can be rendered at 20 frames per second. The
front camera keeps one image per 0.1 s, every second step, so the candidate
still receives images 0.1 s apart, and the actuation adapter's delay limit is
written as 0.1 s of simulation time instead of one step. On the same day the
owner chose an NVIDIA RTX PRO 6000 for the simulator host: at the new step, with
the front camera and a recording camera of 1920 by 1080 pixels, one NVIDIA L4
did not keep wall-clock pace in a readiness probe, and the RTX PRO 6000 did.
The owner also chose that the bench records the candidate's own visualization
with each run: upstream's drawing of what the candidate perceives and plans over
its camera image. It is not the driver's display; it goes only into the bench's
recording. A DE4SDV visualization recorder in the candidate's process draws it
on a thread of its own from a copy that the loop hands over after it writes the
command, and encodes it with the video encoder of the S-CORE host's GPU;
upstream's drawing in the loop stays switched off. The recorder only observes
and carries no logical element, but every build on the S-CORE path carries it,
so the candidate record holds it and every verdict names it. A readiness probe
measured its cost: with the recorder on, the candidate gave its command about
2 ms later at the median and about 6 ms later at the 99th percentile, 0.8 ms
over the bound that the probe had set, and dropped no more images. The owner
kept the recorder in every run, so that each run's recording shows the run that
is judged, and every verdict states the delay.

The owner also chose to keep the collision warning on the application of the IVI
VM for this increment. The High Availability Renderer of Android SDV's display
safety, which draws the safety-relevant parts of the cluster display behind the
steering wheel in a guest of its own, SDV Media, was considered and not selected
(`ALT-DRIVING-HARWARNING-001`): Android SDV's vehicle data has no collision
signal and the renderer's reference application no collision symbol or chime, so
DE4SDV would add all three and a bridge from SDV Core to SDV Media.

On 2026-11-18 the owner chose how the actuation adapter counts the commands it
receives: from the last received command whose check value holds, so that one
lost or late command, or one whose corruption the check value detects, does not
make every later command fail its sequence count. The adapter checks the check
value, then the sequence count, then the issue time. Its reference count is the
highest sequence count among the earlier commands of the run whose check value
holds; it is 0 when the run starts, and the vehicle interface counts from 1. A
command whose check value fails is rejected as a corruption and leaves the
reference count as it is. A command whose count is not greater than the
reference count is rejected as a repetition and leaves the reference count as it
is. A command whose count is more than one greater reveals a loss: it is
rejected, and counting resumes from it. A command whose count is one greater is
accepted unless its issue time is older than the newest world time by more than
0.1 s of simulation time, when it is rejected as a delay; either way counting
continues from it. A late command or a repetition costs that one command; a loss
or a corruption that the check value detects costs the lost or corrupted command
and the next one, which reveals the gap; none of them makes later valid commands
fail. A corruption that the check value misses is none of them: the command
counts as valid and, if its sequence count is higher, that count becomes the
reference count, so that the later valid commands up to it are rejected as
repetitions (the check-value bound decision of 2026-11-21).

The adapter drives the simulated vehicle by CARLA's Ackermann control, as
upstream's own simulator path does, and gives the simulator the candidate's
steering unchanged, as that path does. The VSS steering angle of the driving
command is positive to the left, so the vehicle interface writes the negative of
the candidate's steering, which the integration takes in the sign of CARLA's
steer, positive to the right. `ASM-DRIVING-006` assumes that this sign turns the
vehicle back toward its lane centre, and `ASM-DRIVING-005` that the simulated
vehicle follows the commanded deceleration up to 5.0 m/s²; a calibration run
before Phase 10 shows both. VSS types the items at the ports only: the command's
acceleration and steering angle, the speed and the warning request. Eight signal
mappings record each crossing into a software contract; a mapping is no
interoperability claim.

Two concerns of this phase are held by the parties they serve: the structure
by system architects and software developers, the logical-to-software mapping
by system architects and verification engineers. Three views answer them and
the two Physical concerns of Phase 1: the structure as a tree, the mapping as
a matrix of logical element by software element, and the S-CORE path as an
interconnection of the S-CORE host. The functional-mapping concern is framed
on the matrix and on the path view, not by a matrix of function by software
element. The views are listed in
[`VIEWS.md`](../../textual-notation-of-model/packages/features/driving/VIEWS.md)
once the licensed render has run.

`tests/test_driver_assistance_physical_software_realization.py` pins the
elements and their ports, the context realizations, the allocations, the
dependencies, the signal mappings, the records Phase 8 settles, the views and
this section.

## Variability and configuration (Phase 9)

[`driver_assistance_variability_configuration.sysml`](../../textual-notation-of-model/packages/features/driving/driver_assistance_variability_configuration.sysml)
answers which product of the line the driver-assistance system belongs to, and
with which selections. Phase 3 recorded VisionPilot as the feature candidate
`visionPilotDrivingStack` on 2026-11-14; Phase 9 makes it a feature of the SDV
product line.

- **The feature.** `visionPilot` joins the vehicle-application group of the
  feature model (`F-PLATFORM-VEHICLE-APPLICATION-VISIONPILOT`) with two
  requires constraints: C014 on the camera, which leaves LiDAR and radar
  selectable, and C015 on Linux on the main side, whose V4L2 interface the live
  camera source uses. It corresponds to the driving-stack variability that the
  governed scope defers. Its pairing with the middlewares takes the form chosen
  for AutoE2E on 2026-11-06: an exclusion of `androidSDV`, `autosarAdaptive` and
  `noMiddleware`, because no derivation rule exists for those pairs, and one
  derivation rule for the pair with Eclipse S-CORE that derives the adapter
  `visionPilotToSCORE`. An exclusion lifts when an adapter and its rule are
  added; a requires constraint on `eclipseSCORE` would freeze the bench
  architecture into the line.
- **The shared asset.** `sdv_platform_stack.sysml` gains the two variants that
  the binding and the rule target: `visionPilot : VisionPilotStack` and
  `visionPilotToSCORE : VisionPilotToSCOREAdapter`. The adapter is the DE4SDV
  S-CORE interface module of Phase 8, three modules of the candidate's process
  and no program of its own.
- **The configuration.** `driverAssistanceVisionPilotSCOREReference` selects
  VisionPilot, Eclipse S-CORE, Linux and KVM on the main side, Android with the
  AAOS SDV middleware in the guest, the camera alone and the HMI display, as
  DRIVING-CONFIG-001 does with AutoE2E. It selects no pedestrian or bicycle
  detection. It selects adaptive cruise control and lane-keep assist:
  VisionPilot runs a speed-following and a lane-keeping function, which no case
  of this increment judges.
  No requirement of the increment names the display, so no
  requirement depends on `hmiDisplay`. The privileged PLE authority run of the
  pull request cuts the receipt, and the configurator generates the projection
  `DriverAssistanceVisionPilotSCOREReference` from it. By the model's reading
  of the correspondences the configuration is **valid, and the governed scope
  does not admit it**: the driving stack is deferred variability, Eclipse
  S-CORE is reference-only, the display, adaptive cruise control and lane-keep
  assist are outside the governed scope, the guest side realizes the
  AAOS-integrated alternative without its middleware, and the configuration
  does not represent the common content (no Autoware, no LiDAR). The receipt
  records the verdict.
- **The configured product.** `DRIVING-CONFIG-002` pairs the projection with
  the Phase 8 realization of the driver-assistance system and binds nothing.
  Phase 8 kept the S-CORE path outside the boundary of Phase 0, so the S-CORE
  services sit on the host beside the realization, and the platform stack is
  the only composer of the selected middleware; INC-DRIVING-001's realization
  composes its services and binds them. The derived adapter and the selected
  application are dependencies, not parts: the adapter is the three modules of
  the interface module, and the perception and planner modules run the
  application. The product does not compose the physical context; a test keeps
  the host and guest layers of that context typed by the definitions of the
  selected variants. The identity binds the SHA-256 of the receipt, and Phase 10
  evidence binds the identity. The definition specializes no member-product
  type: the member decision that amends ADR 0014 follows the runnable proof, as
  the framing's admission gap asks.
- **The links of rule 5.** Until the configuration evaluator reads links of
  increment elements and the existing links have moved, rule 5 takes its
  dependency form (ADR 0027 decision 8). The links are declared with their
  clients: `assistanceSystemOnVisionPilotFeature` from the system of interest
  to `visionPilot` in the framing, and one dependency each from REQ-DRIVING-038,
  REQ-DRIVING-039, REQ-DRIVING-042 and REQ-DRIVING-043 to `eclipseSCORE` in the
  requirements package. REQ-DRIVING-040, REQ-DRIVING-042 and REQ-DRIVING-043
  also depend on `guestAndroidSDV`: their term *warning request* asks the AAOS
  SDV for the warning, and the guest-middleware group has a none alternative.
  The requirements follow their subject to VisionPilot; each link adds a
  middleware that the statement names, directly or through a term. No check
  reads them:
  `tests/test_driver_assistance_variability_configuration.py` pins each link,
  and that no feature-model or configuration document names an element of the
  increment.

Two views answer the phase's questions, both trees: the selections of the
projection (Product Line Configuration viewpoint) and the assembly of the
product with its two parts and the configured-product usage (Product Model
Assembly viewpoint). Their diagrams come from the licensed Syside run;
[`VIEWS.md`](../../textual-notation-of-model/packages/features/driving/VIEWS.md)
lists the views.

## Verification and evidence (Phase 10)

[`driver_assistance_verification_evidence.sysml`](../../textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml)
states how each requirement will be judged before any run, so that each verdict
is read against a case written first. The first slice held the cases only. The
second records the evidence of the judged session S1 ([Phase 10
evidence](#phase-10-evidence)). The evidence decisions of 2026-11-18 fix its
shape.

- **One case per requirement.** VC-DRIVING-036 to VC-DRIVING-044 verify
  REQ-DRIVING-036 to REQ-DRIVING-044. Each binds the subject of its
  requirement to the realization of the driver-assistance system in
  DRIVING-CONFIG-002 on the bench, checks the success criteria of its
  requirement and adds none. The bench refers to the configured product, owns
  nothing and is no product selection.
- **The runs.** Seven settings, each run twice, both runs counting:
  SC-DRIVING-012 at 20, 42 and 60 km/h, SC-DRIVING-013 at 30 and 60 km/h,
  SC-DRIVING-014 at 30 km/h and SC-DRIVING-015 at 40 km/h, fourteen runs. A
  further run of SC-DRIVING-012, the stop run, stops the S-CORE path of the
  candidate, as REQ-DRIVING-038 and REQ-DRIVING-043 ask. By the Phase 5 terms,
  as the stop-run decision of 2026-11-18 amended them, it is no run of a setting
  and no judged run, and only the stop clauses of those two requirements read
  it, in VC-DRIVING-038 and VC-DRIVING-043; the next slice chooses its approach
  speed. In the stop run the candidate's process keeps running, and the Launch
  Manager stops the path's carriers of the driving command and of the warning
  request; the next slice fixes which processes these are. The runs of
  SC-DRIVING-014 and SC-DRIVING-015 lie outside the candidate's declared
  operating conditions and are reported apart.

| Case | Requirement | Runs it reads | Method |
|---|---|---|---|
| VC-DRIVING-036 | REQ-DRIVING-036, braking demand | the ten runs of SC-DRIVING-012 and SC-DRIVING-013 | test |
| VC-DRIVING-037 | REQ-DRIVING-037, impact speed | the ten runs of SC-DRIVING-012 and SC-DRIVING-013 | test |
| VC-DRIVING-038 | REQ-DRIVING-038, driving command only over S-CORE | the fourteen runs and the stop run, for the stop clause | test |
| VC-DRIVING-039 | REQ-DRIVING-039, detectable driving command | no run: the Phase 8 realization | analysis |
| VC-DRIVING-040 | REQ-DRIVING-040, no warning request without an imminent collision | the fourteen runs | test |
| VC-DRIVING-041 | REQ-DRIVING-041, no emergency braking without an imminent collision | the fourteen runs | test |
| VC-DRIVING-042 | REQ-DRIVING-042, warning request 1.0 s before the emergency braking | the ten runs of SC-DRIVING-012 and SC-DRIVING-013 | test |
| VC-DRIVING-043 | REQ-DRIVING-043, warning request only over S-CORE | the ten runs and the stop run, for the stop clause | test |
| VC-DRIVING-044 | REQ-DRIVING-044, candidate identity record | the fourteen runs | test |

- **Outcome and verdict.** The increment's own `AssistanceEvidenceOutcome` has
  the six literals of INC-DRIVING-001's vocabulary.
  `MapAssistanceEvidenceOutcomeToVerdict` maps the two pass outcomes to pass,
  `failObservedBehavior` to fail, `errorEvidence` to error and the rest to
  inconclusive. Missing or partial evidence, and a setting whose runs are not
  judged, is inconclusive, never pass. In the cases that read every run, a run
  that is missing, or whose record shows a dropped image within the run, is
  inconclusive too: for them the judged window is the whole run.
- **One evidence record per run.** Every case that reads a run reads its
  `RetainedAssistanceRunEvidence`: DRIVING-CONFIG-002 and the receipt digest,
  the model revision, the candidate identity record of REQ-DRIVING-044, the
  build (VisionPilot at 014e0e7a with the DE4SDV S-CORE interface and the
  visualization recorder) with the recorder's stated delay, measured on an
  S-CORE host with an NVIDIA L4 (a run on another host states its own), the pins
  of the S-CORE platform and the SOME/IP gateway, the simulator build, the
  scenario, the setting and the simulated configuration (the vehicles, the map
  and road, the weather, the 0.05 s step in synchronous mode and the camera
  rig), the simulation-clock and wall-clock spans, kept apart, the three hosts
  with the S-CORE host's GPU and the guest images, the message type of the
  warning request, and the criteria record with the revision of the evaluators
  that read it. The analysis of REQ-DRIVING-039 keeps its own record,
  `RetainedCommandFormAnalysis`.
- **Claims before evidence.** Five claims, one for each Phase 1 concern whose
  question the cases answer, each with an argument that cites its cases.
  `vehicleTargetCriteriaConcern` has no claim: the requirement table of Phase 5
  answers it, and no run does. Twelve counter-claims restate the framing's
  non-claims, each tied to its record: the simulated configuration, the rendered
  camera images, no compliance or approval and nothing about UNECE R152 (tied
  also to `gapVehicleTargetCriteria`), the runs outside the declared conditions,
  no independent emergency path, the build with changes that upstream has not
  merged, the warning modes that the planned review SC-DRIVING-018 observes, no
  membership, no upstream endorsement or rights clearance, no tuning until a
  case passes, no evidence from the reused bench's earlier results, and the open
  test environment. The claims, arguments and counter-claims specialize the
  kernel's assurance kinds; nothing is satisfied.
- **The test environment** is GAP-DRIVING-014, which continued the readiness
  items of Phase 8 until the probes ran; S1 leaves them so (the environment
  decision of 2026-11-21): the link with the build of ONNX Runtime for CUDA in
  the S-CORE process: shown; a second C++ standard library in that process:
  settled by the build that ran; the candidate record reaching a late
  subscriber: shown; the candidate on CARLA 1.0: shown; the typed message of the
  warning request on the guests: shown; the calibration runs of ASM-DRIVING-005
  and ASM-DRIVING-006 came before the first judged run; the S-CORE build's cycle
  on the host's own GPU: answered no, every run of S1 drops camera images: 23 or
  24 in the first 5 s after its first image, 2 to 6 in the last 0.6 s of its
  image stream, after the run's end, and 0 to 3 isolated ones in between, with
  no cause shown; the warm start of D-S1-1 ran before the attach in every run,
  in 678.3 to 706.8 ms, and did not keep the first 5 s free of dropped images;
  the capture of the start of the sound on the IVI guest: open, the guest
  records hold no start of the sound; showing the draft and the results to the
  VisionPilot maintainers: open, not done, and the owner approves any text
  first; the end of the second runs of SC-DRIVING-013 after 62 ticks at the
  speed of the target (B1): open, a bench item for the next session. The gap
  stays a record; Phase 11 decides its disposition. Each probe runs only on the
  owner's word.
- **No validation case.** The validation of the needs stays planned in
  Phase 4 (SC-DRIVING-016 to SC-DRIVING-019).

One view answers the phase's question, a tree of the Argumentation Assurance
viewpoint: the claims with their arguments and the cases they cite, the
evidence records, the counter-claims, the records they are tied to and the
gaps. It frames `candidateVerdictConcern` beside the phase's own concern. Its
diagram comes from the licensed Syside run;
[`VIEWS.md`](../../textual-notation-of-model/packages/features/driving/VIEWS.md)
lists the views.

### Phase 10 evidence

The evidence of record is the judged session S1, session 20261121T014447Z of the
bench at commit 508649ba, with all three hosts: the 14 runs of SC-DRIVING-012 to
SC-DRIVING-015 (10 of them meet their entry conditions), the run that stops the
path and the calibration runs before the first judged run. Its small records and
the identities of everything it leaves outside Git are in the [S1 evidence
directory](../../implementation/driver-assistance-bench/evidence/s1-20261121T014447Z/README.md),
whose README carries the table of the verdicts, generated from the verdict
files. A verdict of S1 is a verdict of the pinned candidate on this bench in
simulation, and no statement about compliance or on-road behavior.

- **Generated, not written.** The fifteen run records, the record of the
  analysis of REQ-DRIVING-039 and the status that opens the doc of each case
  are written by `tools/generate_driver_assistance_evidence_text.py` from the
  files of the evidence directory, and
  `tools/refresh_driver_assistance_s1_evidence.py` refreshes the directory and
  the model in one command when the evaluators or the desk records change. No
  outcome, value or evaluator revision is copied by hand into the model or this
  guide; read them in the case docs and the evidence README.
- **Of record, on one condition.** S1 is the evidence of record if the bench
  files that ran on a host are byte-identical to those that the pull request of
  the bench merges; the evidence README gives the check (the evidence-of-record
  decision of 2026-11-21).
- **The drop rule stands.** By the rule of Phase 8, no run whose judged window
  holds a dropped camera image is judged, and for the cases over every run that
  window is the whole run. The evaluators' readings with the rule set aside are
  diagnosis only, never a verdict (the drop-rule decision of 2026-11-21).
- **The deceleration calibration.** The condition on ASM-DRIVING-005 bears on a
  pass of VC-DRIVING-036 and VC-DRIVING-037, not on their fail in S1: it
  concerns how the simulated vehicle achieves a commanded deceleration. No run
  of SC-DRIVING-012 holds a commanded deceleration stronger than 0.533 m/s², and
  the commanded decelerations of each run, fully achieved, would have lowered
  its speed before the contact by at most 2.4 km/h, so the condition does not
  bear on these fails (the deceleration calibration decision of 2026-11-21).
- **The statuses.** The verification status records the process of the
  verification, never its verdict: `VVStatus::Completed` for REQ-DRIVING-036,
  REQ-DRIVING-037, REQ-DRIVING-039 and REQ-DRIVING-042, and
  `VVStatus::CompletedUnsuccessful` for REQ-DRIVING-038, REQ-DRIVING-040,
  REQ-DRIVING-041, REQ-DRIVING-043 and REQ-DRIVING-044 (the status decision of
  2026-11-21).
- **The analysis of REQ-DRIVING-039** is an independent desk record, bounded as
  its record states: a loss is recognized only when a later command arrives, a
  delay of up to 0.1 s of simulation time goes unrecognized, and a corruption is
  recognized only as far as the check value does. The Phase 8 realization now
  says what a corruption that the check value misses does (the check-value bound
  decision of 2026-11-21).
- **The test environment** after S1 is GAP-DRIVING-014 as the environment
  decision of 2026-11-21 records it; it stays a record, and Phase 11 decides its
  disposition.

## Baseline (Phase 11)

`driver_assistance_framing.sysml` holds the baseline decision of the
increment, `driverAssistanceBaselineDecision` (BL-DRIVING-002-P11), and each
of the 11 gap records states the disposition the baseline gives it. The
framing view shows the decision beside the framing decision it answers.

- **Accepted: the integration as built.** The model of phases 0 to 10 and the
  bench under `implementation/driver-assistance-bench/`. VisionPilot at
  014e0e7a, built with the DE4SDV S-CORE interface and the visualization
  recorder, runs as an Eclipse S-CORE application that the Launch Manager
  starts and supervises. The framing decision asked how the candidate goes
  forward; the baseline answers: as a candidate that needs the additions named
  below before it can be the AEBS of a member product, by the decision of
  2026-11-21.
- **Evidence and verdicts.** By the decision of 2026-11-21, the judged session
  S1, session 20261121T014447Z at bench commit 508649ba, run on 2026-11-21 on
  the three hosts with the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 (10 of
  them meet their entry conditions) and the run that stops the path, and its
  records, on the condition that the bench files that ran are byte-identical to
  those that the second slice of phase 10 merges, the check that the evidence
  README of that slice states. One verdict for each case, in the table below;
  each verdict is of the pinned candidate on this bench, in simulation. The runs
  of SC-DRIVING-014 and SC-DRIVING-015 lie outside the candidate's declared
  operating conditions and are reported apart: no run of either gives a verdict,
  since VC-DRIVING-038, VC-DRIVING-040, VC-DRIVING-041 and VC-DRIVING-044, the
  cases that read them, judge over the whole run and are inconclusive by the
  rule on dropped images. A fail is a recorded result, and no scenario,
  criterion or setting is changed for it. The additions named from the
  requirements that fail and from the gaps: by the decision of 2026-11-21, a
  warning and an emergency braking for a stationary vehicle ahead in its lane, a
  camera path that keeps every image from a run's first image on, so that the
  criteria over every run can be judged, and for the stop clauses of
  VC-DRIVING-038 and VC-DRIVING-043 a judged window that ends at the stop
  instant or a camera input that stops with the candidate, since after the stop
  the interface drops the images that the candidate no longer takes; the
  increment builds none of them.
- **Known limits: accepted, still open.** `gapCandidateBehaviorUnverified`: S1
  gives the first closed-loop results of record of the candidate on the DE4SDV
  bench, and every verdict is of the build with the DE4SDV S-CORE interface
  and the visualization recorder, changes that upstream has not merged.
  `gapDeclaredOperatingConditions`: the runs outside the declared conditions
  are reported apart, and none of them gives a verdict.
- **Deferred to a later increment.** `gapVehicleTargetCriteria`: taking the
  criteria of Phase 5 into the obligations of the product line.
  `gapNoSeparateEmergencyFunction`: whether the candidate's braking, which
  leaves in its one driving command, can stand for the common capability, for
  the member decision. `gapWarningOutput` and `gapScoreIntegration`: the take-up
  upstream of the warning hand-off and of the S-CORE interface module.
  `gapCameraImageAndGeometry`: S1 does not show whether the detection of the
  target at the distances that the criteria need, or the calibration of the
  simulated camera, explains the fails. `gapCandidateAdmission`: the member
  decision that amends ADR 0014. `gapUpstreamContactAndRights`: at the baseline
  the maintainers have not seen the results or the draft; no endorsement, no
  rights clearance. `gapDriverHmiInProductLine`: the display in the governed
  scope and the acoustic warning. GAP-DRIVING-014: the readiness items that S1
  leaves open: the candidate's cycle on the GPU of the S-CORE host, on which
  each of the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 drops 23 or 24 camera
  images in the first 5 s after its first image and up to 2 more inside the run,
  with no cause shown, what S1 does not show of the start of the sound on the
  IVI guest, the showing of the results to the VisionPilot maintainers, and the
  bench item B1 for the next session, the end of the second runs of
  SC-DRIVING-013 after 62 ticks at the speed of the target.
- **Withdrawn.** None.

| Case | Verdict | What S1 shows |
| --- | --- | --- |
| VC-DRIVING-036 | fail | In the five judged runs of SC-DRIVING-012 the candidate commands no deceleration stronger than 0.46 m/s²; the contact comes at the approach speed (19.7, 40.6, 40.6, 58.6 and 58.6 km/h). |
| VC-DRIVING-037 | fail | The same runs: the speed at the contact is the approach speed. |
| VC-DRIVING-038 | inconclusive | No run is judged by the rule on dropped images. Its stop clause is inconclusive by the same rule: 32 dropped images fall inside its judged window, from 2855.010 s to 2897.010 s, and the stop came at about 2871.06 s, so about 26 s of ticks follow it. |
| VC-DRIVING-039 | pass | A desk analysis of the realization: a loss shows only when a later command arrives, and a delay of up to 0.1 s of simulation time goes unseen. |
| VC-DRIVING-040 | inconclusive | No run is judged by the rule on dropped images. |
| VC-DRIVING-041 | inconclusive | No run is judged by the rule on dropped images. |
| VC-DRIVING-042 | fail | In the five judged runs of SC-DRIVING-012 the candidate starts no warning request. |
| VC-DRIVING-043 | inconclusive | No run is judged by the rule on dropped images. |
| VC-DRIVING-044 | inconclusive | No run is judged by the rule on dropped images. |

Of SC-DRIVING-012 the second run at 20 km/h is not judged (its center line 0.245
m from the target's, the limit is 0.2 m). Of SC-DRIVING-013 the first run at 30
km/h is judged and meets the criteria of VC-DRIVING-036, VC-DRIVING-037 and
VC-DRIVING-042; the other three runs have no functional part and are not judged.
Each of the 14 runs and the run that stops the path drops 23 or 24 camera images
in the first 5 s after its first image, and for the five inconclusive cases the
judged window is the whole run. Read with that rule set aside, for diagnosis
only and as no verdict, VC-DRIVING-038 and VC-DRIVING-044 meet their criteria in
all 14 runs, and VC-DRIVING-040, VC-DRIVING-041 and VC-DRIVING-043 in the runs
of SC-DRIVING-012 and SC-DRIVING-013.

No safety, on-road, compliance, type-approval, certification or membership
claim follows from the baseline. A criterion met in simulation holds for the
simulated configuration only.

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
- **Two scenarios outside the declared conditions**
  (`gapDeclaredOperatingConditions`). The candidate's documentation declares
  its hands-free mode only for highways and motorways with clearly marked lane
  lines, in fair weather and visibility, at up to 70 mph (about 113 km/h) and
  away from construction zones and roadwork, with a human driver supervising it
  at all times. Supervision by a driver falls under driver monitoring, which is
  out of scope (driverInteractionOutOfScope); the road, the weather and the
  speed place each scenario. The scenarios with a stationary and with a slower
  moving vehicle target ahead in the lane run on a highway-type road in fair
  weather, inside these conditions. The two scenarios in which no reaction is
  due lie outside the declared conditions: a tight curve with guard pipes and a
  turn at a corner are no highway situations. Both come from the regulation's
  false-reaction scenarios and stay in the scope. Phase 10 reports the runs
  outside the declared conditions apart from the runs inside them.
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

The increment ended at its baseline decision. Use the Method Check of the
reviewed pull request to see the state of the model-content gates; it is not
proof that earlier engineering work is complete. Phase 10 holds the cases that
`verificationCaseVerifiesRequirement` and
`requirementVerifiedByVerificationCase` read. A later increment takes up what
the baseline deferred: the member decision that amends ADR 0014, the take-up
upstream of the warning hand-off and of the S-CORE interface module, the
clearances and the product line's criteria for a vehicle target. Claim no
runtime gate from the baseline.

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
tests/test_driver_assistance_needs_requirements.py
tests/test_driver_assistance_requirements.py
tests/test_driver_assistance_functional_architecture.py
tests/test_driver_assistance_logical_architecture.py
tests/test_driver_assistance_physical_software_realization.py
tests/test_driver_assistance_variability_configuration.py
tests/test_driver_assistance_verification_evidence.py
tests/test_driver_assistance_s1_evidence_directory.py
tests/test_refresh_driver_assistance_s1_evidence.py
tests/test_generate_driver_assistance_evidence_text.py
tests/test_ple_authority_model.py tests/test_ple_authority_receipts.py
tests/test_trace_allocation_completeness.py -q`. These are
repository and lexical checks, not SysML semantic validation and not runtime
verification. Use `python scripts/validate_sysml.py` where a licensed
validator is available, or request the maintainer-run **Privileged Syside
Validation** on the reviewed head. The framing view and its published diagram
come from that Syside run.
