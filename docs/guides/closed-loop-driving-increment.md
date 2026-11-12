# Closed-loop driving increment

DE4SDV needs to distinguish a driving function that actually influences vehicle
behavior from a prediction overlay on a separately driven car. This increment
proposes the former: real camera-based learned planning, a functional S-CORE
integration path, and an AAOS SDV application showing genuine plan/state/health.

**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context,
Phase 3 capability classification, Phase 4 stakeholder needs, Phase 5
requirements, Phase 6 functional architecture, Phase 7 logical architecture
and Phase 8 physical/software realization, proposal.** No implementation,
build, successful driving run, performance result or product-line admission
is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_framing.sysml):
  `INC-DRIVING-001`, its engineering question, charter, scope and open gaps.
- [SysML operational context](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_operational_context.sysml):
  the Phase 2 context, operational behavior and story.
- [SysML capability classification](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_capability_classification.sysml):
  the Phase 3 feature candidate and the scope decisions it needs.
- [SysML needs and requirements](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_needs_requirements.sysml):
  the Phase 4 stakeholder needs, their planned reviews, and the Phase 5
  requirements.
- [SysML functional architecture](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_functional_architecture.sysml)
  and [logical architecture](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_logical_architecture.sysml):
  the Phase 6 functions and interfaces, the Phase 7 logical elements.
- [SysML physical/software realization](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_physical_software_realization.sysml):
  the Phase 8 software elements, their allocations, signal mappings,
  assumptions and gaps.
- [SysML variability and configuration](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_variability_configuration.sysml):
  the Phase 9 configured product DRIVING-CONFIG-001, bound to the receipt
  of its feature configuration.
- [SysML verification and evidence](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_verification_evidence.sysml):
  the Phase 10 verification cases, the run record, the claims and the
  counter-claims; no case has started.
- [Syside review views](../../textual-notation-of-model/packages/features/driving/VIEWS.md):
  the generated model review artifacts, not a runtime architecture claim.
- [Upstream provenance and questions](../../textual-notation-of-model/packages/features/driving/upstream.md).

Orkun Yilmaz owns the increment. One identity covers phases 0 through 11;
CARLA closed-loop verification belongs to Phase 10 of this increment, with
readiness probes earlier in phases 6 through 8.

## Intended outcome, not an implemented architecture

The learned planner's output must influence steering and acceleration through
the S-CORE functional path and a controller back to CARLA. A direct bypass or
CARLA autopilot with an AI overlay is not equivalent evidence. AAOS SDV
Core/Gateway/IVI consumes the real plan, vehicle state and health; display
rendering does not belong in the fast vehicle-control loop.

The proposed driving-function boundary is a candidate **System 1** subject.
CARLA, cloud hosts and evidence/capture instruments are **System 2** enablers,
not vehicle features. Phase 2 draws the boundary and the exchanges across it.
This framing does not modify the existing AEBS behavior, admit an automated-driving
member under [the current scope decision](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md),
or claim production readiness, on-road suitability or safety approval.

## Timing and evidence boundary

The planning objective is at least **20 fresh rendered frames per wall-clock
second**, targeting **24 fps live capture** without speeding up a slow simulation.
These numbers are not model-invocation rates or fulfilled requirements. Simulation
real-time factor, inference cadence, input-to-actuation age, observation age and
capture continuity need separate evidence. Phase 5 fixes the share of the
driving system: input resolution, measurement window, drop tolerance, freshness
limits and control deadlines. The frame rate, capture rate and render
resolution of the simulator, and the CARLA map and route, are fixed with the
System 2 bench before the readiness probe.

The released checkpoint must be evaluated with its compatible geometry and
history. Fast synthetic-input results do not prove its performance. Neither
interface compatibility nor recorded-input inference proves useful closed-loop
driving on CARLA imagery. Invalid, lost or stale plans require a defined
stop/disable response in simulation and retained failure-path evidence.

## Concerns (Phase 1)

Each in-scope item leads to the questions it raises; three items raise two
questions each, with different stakeholders (owner decisions of 2026-11-02).
A question is held by the party it serves, not only by the roles that check
the answer: the vehicle occupants state what they expect of the vehicle. Each
concern is typed by the SAF concern that asks its question, so its domain says
which later view answers it. The framing viewpoint frames all seven until
those views exist.

- **Learned driving:** `drivenAlongTheRouteConcern`, the vehicle occupants are
  taken along the route the driver chose, by the driving system's own plans.
  Operational capability; vehicle occupant. Answered by the Phase 2 story.
- **Learned driving:** `checkpointCommandAuthorityConcern`, the checkpoint's
  plan determines the commands with nothing in between. Physical functional
  mapping; systems engineer, verification engineer, reviewer.
- **Integration and observation:** `scoreCommandPathConcern`, plan and command
  items pass through S-CORE, not beside it. Physical internal exchange; system
  architect, software developer, maintainer.
- **Integration and observation:** `aaosObservationFidelityConcern`, AAOS shows
  the live plan, state and health to the driver, who is a vehicle occupant.
  Physical context exchange, because Phase 2 keeps AAOS SDV in the context;
  vehicle occupant, verification engineer, reviewer.
- **Feedback and timing:** `degradedInputBehaviorConcern`, a defined response
  to invalid, lost or stale camera input, ego state, route or plan. Functional
  behavior; vehicle occupants, road users, safety expert, system architect.
- **Feedback and timing:** `timeDomainHonestyConcern`, every timing claim names
  its time domain. Argumentation assurance; verification engineer, systems
  engineer.
- **Closed-loop evidence:** `reproducibleClosedLoopEvidenceConcern`, rerunnable
  scenarios, per-hop logs and the actual capture. Argumentation assurance;
  verification engineer, maintainer, reviewer.

The Phase 1 gates check that each concern has native stakeholders and a
frame, and that one concern is not the boundary concern. They do not judge
whether the stakeholder, risk and viewpoint coverage is adequate; review does.

## Operational context (Phase 2)

AAOS SDV is a **context role**, not part of the driving system (owner decision
of 2026-11-02). Remove it and the plan-to-command chain is unchanged; only the
observation is lost. Putting it inside would make the display's correctness and
delay something the system delivers, which Phase 0 does not claim.

- **Inside the system of interest:** camera and ego-motion input, learned
  planning, command execution and operational-state publication, as Phase 0
  draws it. The plan and the commands cross S-CORE inside it. The publication
  ends at its receiving end in the AAOS SDV guest, as in INC-MW-011.
- **Around it, System 1 roles only:** the vehicle it drives, the road
  environment its cameras see, navigation, the AAOS SDV guest of the existing
  S-CORE and AAOS SDV integration with the application that presents the
  published state, and the driver who chooses the destination and watches the
  state. CARLA, the cloud bench and the capture instruments realize the
  vehicle, the scene and the route for verification; they are System 2 and
  stay out of the context.
- **Exchanges:** camera images and ego motion from the vehicle, the route from
  navigation, steering and acceleration commands to the vehicle, and the plan,
  vehicle state and health to AAOS SDV. Nothing flows from AAOS SDV back into
  the loop.
- **Navigation** is an operational role, not a platform (owner decision of
  2026-11-02): it holds the road map and gives the route to the destination
  the driver chose. Which computer runs it is a Phase 8 allocation. If a later
  phase allocates it to the AAOS SDV guest, AAOS SDV becomes an input to the
  loop and the context-role decision reopens.

Three words stay apart:

- **route:** where the vehicle is to go, from navigation: the destination,
  the route to it and the map of the roads around the vehicle;
- **plan:** how the vehicle moves through the next seconds, the trajectory
  the checkpoint computes along the route;
- **command:** the steering and acceleration that carry the plan out.

The story has four scenarios:

- **`SC-DRIVING-001`:** the checkpoint plans along the route from navigation,
  its plans move the vehicle, and its motion changes the next images.
- **`SC-DRIVING-002`:** AAOS SDV shows the live plan, vehicle state and health
  of this run, outside the control loop.
- **`SC-DRIVING-003`:** invalid, lost or stale camera images, motion, route
  or plan leads to the defined stop or disable response.
- **`SC-DRIVING-004`:** with AAOS SDV down or late, the loop goes on unchanged
  and no stale state is shown as live.

The response and its deadlines, and how a stale observation is marked, are
fixed with the requirements in Phase 5. The Phase 2 gates check one context
that holds the system of interest and a story bound to it and to the context
parts; review judges the roles and the scenarios.

## Capability classification (Phase 3)

The increment adds one characteristic that distinguishes member products:
**AutoE2E as the driving stack**, the feature candidate `autoE2EDrivingStack`
(owner decisions of 2026-11-02). It traces to the driving-stack variability
the governed scope defers and answers the framing's product-line admission
gap.

- **Sensing:** AutoE2E plans from camera images and its ego-motion history and
  takes no LiDAR input. Phase 9 adds it to the feature model with a constraint
  that it requires the camera feature, and leaves LiDAR selectable. Ego motion
  needs no constraint: it comes from the motion sensors, which every member
  has, so they have no feature. LiDAR itself gets no record: the feature model
  already makes it optional.
- **Why the feature model waits for Phase 9:** a new vehicle application
  needs a derived middleware adapter for every valid configuration, and
  Phase 8 realizes that adapter first.
- **Scope decisions:** the driving member becomes a new planned member;
  Autoware and LiDAR stop being common; Vehicle-Target AEBS and the protected
  emergency command path stay common; Eclipse S-CORE still has to be
  admitted. A comment on the admission gap records them, and the member
  decision amends ADR 0014 with them.

The Phase 3 gate checks only that each recorded characteristic is a feature
candidate or deferred scope; review judges the classification.

## Stakeholder needs (Phase 4)

Seven needs, `NEED-DRIVING-001` to `NEED-DRIVING-007`, take the candidate
driving system as subject. Each is held by the parties it serves, not by the
roles that check the answer, and each is derived from one non-boundary Phase 1
concern, which its source names:

- **Driven along the route:** the driving system's own plans move the vehicle
  along the route the driver chose (001; vehicle occupants).
- **S-CORE command path:** plans and commands pass through S-CORE (002; system
  architects, software developers, maintainers).
- **AAOS observation fidelity:** the loop publishes its live state with
  producer and time (003; vehicle occupants, verification engineers), and runs
  unchanged when AAOS SDV is down or late (004; vehicle occupants).
- **Degraded input behavior:** a defined stop or disable response to degraded
  camera images, motion, route or plans (005; vehicle occupants, road users).
- **Time-domain honesty:** inputs, plans and commands carry their times (006;
  verification engineers, systems engineers).
- **Reproducible evidence:** each run identifies its checkpoint and
  configuration (007; verification engineers, maintainers, open-source
  reviewers).

The form of the inputs the pinned checkpoint takes is no need of its own;
Phase 5 states it as requirements derived from `NEED-DRIVING-001`.

The no-autopilot, replay or overlay condition is likewise not part of what an
occupant states. The planned review `SC-DRIVING-005` checks it, and it is a
success criterion of `REQ-DRIVING-011`.

Each need has its own planned stakeholder review, `SC-DRIVING-005` to
`SC-DRIVING-011`, watching a Phase 2 scenario. Phase 5 fixes the limits and
the deadlines. No need covers driving quality: the charter scopes checkpoint
authority, and poor driving is a hold or redirect condition of the performance
gap. The Phase 4 gates check that each need has a statement, a stakeholder, a
source, a rationale and a planned review; review judges whether the needs are
the right ones.

## Requirements (Phase 5)

Thirty-five requirements, `REQ-DRIVING-001` to `REQ-DRIVING-035`, take the
candidate driving system as subject. Each derives from one need through
`DerivesFromNeed` and carries one verification method, `test`, and its success
criteria; each statement carries one obligation. The terms the statements use,
among them run, step, motion sample, plan, valid plan, health and stop response,
are defined once in the needs-and-requirements model. A value taken from the
AutoE2E source cites it at the checkpoint pin; the freshness limits, the
deadlines, the stop deceleration and the command limits are set in Phase 5, each
with its reason in its rationale.

Two kinds are not functional. The checkpoint, the form of the inputs it takes
and the S-CORE path are design constraints: the increment evaluates them as they are, so
a plan comes from that checkpoint through those inputs, and the commands computed
from it travel over S-CORE. The limits on planning time and on independence from
observation are performance requirements. Neither kind is functional, so only
the other 23 requirements must be allocated to a function in Phase 6. Grouped by
the need they answer:

- **Driven along the route (001):** one plan for each 100 ms step of simulation
  time, no two consecutive steps without one (001); each plan by inference of the pinned checkpoint on the camera
  images, the ego-motion history and the route of its step (002); the input form
  it takes: six camera images at the two sizes it asks for (003),
  seven earlier images per camera (004), one projection operator per image (005),
  the `map_context` raster (006), the `route_mask` raster (007) and 64 motion samples
  100 ms apart before the step, worked out from the vehicle's positions, with yaw
  rate and curvature given as zero (008); standstill until
  both histories are complete (009);
  histories only from images and samples captured in the run (010); commands only
  from the newest valid plan and current motion (011), within the steering and
  acceleration limits the configuration names (012); each plan within 100 ms of
  wall-clock time after its newest camera image (013), kept on this need by owner
  decision.
- **S-CORE command path (002):** plans and the commands computed from them reach
  the actuation only over Eclipse S-CORE (014).
- **AAOS observation fidelity (003, 004):** each plan and each motion sample
  published once, with its producer and its time, within 100 ms of wall-clock
  time (015, 016), and the health at least every 200 ms of wall-clock time, also
  while no plan is produced (017); with the same recorded inputs, the plans and
  commands differ by no more than two reference runs with AAOS SDV receiving on
  time differ from each other, whether it receives on time, 1 s late or not at
  all (018), and the planning time stays within 10 ms of its value with AAOS SDV
  on time (019).
- **Degraded input behavior (005):** one stop response decelerates at 4 m/s² to
  standstill (020), holds the steering command (021) and keeps the vehicle at
  standstill to the end of the run (022); it begins when the images of a camera
  are missing, invalid or more than 200 ms of simulation time old (023), when the
  newest motion sample is invalid or more than 200 ms old (024), when the route
  is more than 1 s old or holds no corridor (025), when the newest valid plan is
  more than 300 ms old (026), when a plan is not 64 finite pairs (027) and when
  no valid command has reached the actuation for 200 ms (028); the stop and its
  cause are published within 100 ms of wall-clock time (029).
- **Time-domain honesty (006):** each camera image and motion sample carries its
  capture time in simulation time (030), each plan the capture time of its newest
  image and its production time on the host clock (031), and each command its
  plan, its issue time on the host clock and its actuation time in simulation
  time (032).
- **Reproducible evidence (007):** each run records the SHA-256 of its
  checkpoint, its source revision and the SHA-256 of its configuration before its
  first plan (033), every plan names that record (034), and a checkpoint that
  differs from the named SHA-256, or a configuration that names none, yields no
  plan (035).

Two time domains stay apart. What the vehicle lives through is counted in
simulation time: input age at the command, the interval between plans, and the
freshness limits and deadlines of the stop response. What the host does is on
its monotonic clock: planning time, publication time and the S-CORE transport
delay. No rate or age is read in a domain it was not measured in.

What stays open with the System 2 bench is the rendered frame rate, the
capture rate and render resolution of the simulator, and the CARLA map and
route of `SC-DRIVING-001`, recorded in the model on `gapClosedLoopPerformance`.

The requirements are not core: the driving system enters a member product
only with the driving stack that Phase 3 records as the feature candidate
`autoE2EDrivingStack`, and Phase 9 adds that feature to the feature model and
links the system of interest to it. No member product, safety, on-road or
production claim is made. The Phase 5 gates check that each requirement has a
statement, derives from a need, has one subject and one verification method,
and, as advisories, that its subject is the system of interest and that it
states its success criteria; review judges whether the requirements are the
right ones and whether their values hold.

## Functional architecture (Phase 6)

Seven functions break the driving system down, in the order of one step:

- **`identifyRun`** compares the SHA-256 of the checkpoint file with the one
  the configuration names, refuses to plan from any other, and records the run
  identity before the first plan;
- **`assembleInputs`** marks each camera image and motion sample with its
  capture time and builds the inputs the checkpoint takes, from inputs
  captured in the run;
- **`planTrajectory`** makes the plan of a step by checkpoint inference and
  marks it;
- **`superviseLoop`** detects degraded camera images, motion, route and plans,
  and sets the mode;
- **`commandVehicle`** computes the steering and acceleration commands of each
  mode;
- **`applyCommands`** gives the commands to the actuation of the vehicle,
  marks their actuation time and reports its actuation state;
- **`publishState`** publishes the plans, the vehicle state, the health and a
  stop for observation.

They are `AllocatableFunction` actions of the functional flow
`ClosedLoopDrivingFunctionalFlow`. The flow takes the camera images, the
ego-motion state and the route of Phase 2 in, and gives the commands to the
actuation and the operational state to the state observer. Inside, the
functions exchange the checkpoint inputs, the input condition, the plan, the
mode, the run record and, since the amendment of 2026-11-06, the actuation
state: what the actuation applied with its time, or that its own stop is in
force, since when and why. It goes from `applyCommands` to `publishState`
and nowhere else, so the stop the actuation decides (REQ-DRIVING-028) is
published with its cause (REQ-DRIVING-029) like the stop the supervision
decides. Before the amendment the publisher saw the supervision's mode only;
Phase 8 found the hole as GAP-DRIVING-005, and the owner decided to amend
rather than to narrow REQ-DRIVING-029.

The boundary items say what the sensing gives the system, with no vehicle
signal specification: a `CameraImageInput` is one image per position, the
six of `CameraPosition` in the order REQ-DRIVING-003 fixes, each with its
capture time in simulation time, its size in pixels and its camera's
calibration, from which the projection operator of REQ-DRIVING-005 is
built; an `EgoMotionInput` is the samples of the vehicle's speed,
longitudinal and lateral acceleration and yaw rate as ISQ quantities, each
with its sample time, and the vehicle's position at each, from which the
checkpoint's history is worked out the source's way (REQ-DRIVING-008). The checkpoint gets the history's yaw rate and curvature
as zero (REQ-DRIVING-008), the bounded deviation of the owner's decision of
2026-11-09 that GAP-DRIVING-010 records: fed back in the closed loop, the
checkpoint's own yaw history turned its plans off the lane.

GAP-DRIVING-011 records a separate limit, accepted on the owner's decision of
2026-11-10: the pinned checkpoint takes no turn from the route. With the same
camera images, map and motion history, swapping a route that turns hard left
for the same route mirrored to a hard right changes the planned heading at
6.4 s by at most 0.02 degrees, where a turn at a junction needs about 60. That
holds with the history as REQ-DRIVING-008 gives it and with the recorded one,
with a road-wide route corridor, with a destination marker 40 m along the
route, and with the cameras blanked and no map. So the scenario's route needs
no branch choice: every junction on it is passed straight on, and CARLA's
route planner gives only lane-follow and straight road options along it. Keep
it so when you change the route; the evidence claims no route following at
junctions. The gap closes only with a checkpoint whose plans take the turn
from the route, and the model revisits it when upstream publishes one.

GAP-DRIVING-012 records a third limit, accepted on the owner's decision of
2026-11-10: the pinned checkpoint does not keep the vehicle in its lane. Two
errors of the bench made the first runs on a straight route drift faster than
the plans asked, and both were corrected that day: the actuation adapter
applied every steering command at twice its angle, because it scaled the steer
by the 35 degree command limit, not by the vehicle's 70 degree maximum, and
the command law asked for 0.6 degrees more steering to the left than the plan
did. In the three runs after both corrections the vehicle stayed within 0.16 m
of the route for 10 s. Then its heading turned 2.3 to 2.4 degrees to the right
between 15 s and 30 s. In two runs it crossed the lane marking on its right
after 31.5 s and 35.1 s; in the third a turn of 1.6 degrees that no command
asked for had put it 1.4 m to the left by then. The plans steered back on
neither side: none of 269 made with the vehicle more than 0.3 m to the right
of the route pointed back, and 25 of 165 made with it more than 0.3 m to the
left did. With the yaw history as REQ-DRIVING-008 gives it the plans do not
correct a drift, and with the checkpoint's own yaw history they turn off the
lane within seconds (GAP-DRIVING-010), so no setting keeps the lane. The
review of NEED-DRIVING-001 (SC-DRIVING-005) names both limits, and the
evidence claims neither lane keeping nor driving along the route. The gap
closes only with a checkpoint that keeps its lane in a closed loop.

Three decisions shape the functional architecture:

- **One command path.** The stop response is a mode of `commandVehicle`, not a
  second source of commands, and only its commands reach the actuation. When
  commands stop arriving there, `applyCommands` applies the stop response
  itself (`REQ-DRIVING-028`).
- **Observation one way.** Nothing `publishState` gives flows back into the
  loop, and it never waits for a receiver. The two requirements on
  independence from observation (018, 019) are allocated to it.
- **Modes.** The health names three modes: priming, driving and stopped.
  `ClosedLoopDrivingModes` holds them. Stopped has no transition out, so a
  stopped run stays stopped until it ends.

Each requirement but one is allocated (`allocatedTo`) to the functions that
carry it: the 23 functional requirements the gate asks for, and the design
constraints and performance limits to the functions they bind, such as the
input form to `assembleInputs` and the planning time to `planTrajectory`.
`REQ-DRIVING-014`, the S-CORE path, is carried by no function. It constrains
how the plan and the commands travel between the functions, and Phase 8 places
the S-CORE elements on those exchanges. An allocation assigns responsibility
only; it claims no satisfaction.

Two views of the SAF System Functional Breakdown Structure viewpoint publish
the architecture:

- the breakdown view `closedLoopDrivingFunctionBreakdownView`, which lists the
  items and the seven functions of the flow but draws no item flows; they are
  in the model;
- the matrix `closedLoopDrivingRequirementFunctionMappingView`, with the
  requirements in rows and the functions in columns.

The matrix also answers the Phase 1 concern `degradedInputBehaviorConcern`: it
shows `superviseLoop` detecting degraded inputs and plans, `commandVehicle`
stopping the vehicle, and `applyCommands` stopping it when commands stop
arriving. The Phase 6 gates check that a function exists and that each
functional requirement is allocated to one, and, as advisories, that each
requirement is carried by the architecture and each function carries a
requirement; review judges whether these are the right functions.

### The loop, the modes and the interfaces

Three more parts of the model answer the rest of what Phase 6 asks: the flows,
the states and the interfaces.

- **The system process.** `ClosedLoopDrivingSystemProcess` is one cycle of the
  loop. Its participants are the parts of the one operational context of
  Phase 2 (`closedLoopDrivingOperationalContext`) and its system of interest,
  bound by reference as the story's actors are: the process declares no part
  of its own, so the increment has one context. Each participant owns and
  performs its functions of the loop, as the swim lane of its function.
  Navigation gives the route, the vehicle's cameras and motion sensing give
  the images and the ego motion, the vehicle's actuation applies the
  commands, and the state observer presents the published state. Those five
  are functions of the context elements (`ContextElementFunction`), outside
  the scope of the driving system: no requirement is allocated to them. The
  driving system performs the one functional flow usage, the same one its
  functional boundary performs, as one action of the process, and the five
  items that cross its boundary are the flows of the process, each chained
  through the participant that gives and the one that takes. Nothing flows
  back from observation.
- **The modes.** Each mode of `ClosedLoopDrivingModes` states what the
  functions that differ by mode do in it, and a dependency runs from each such
  function to each mode it depends on: `commandVehicle` to all three,
  `publishState` to stopped.
- **The interfaces.** `ClosedLoopDrivingFunctionalBoundary` is the driving
  system at its functional boundary: it specializes `ClosedLoopDrivingSystem`
  and carries five port definitions, three in and two out, with one directed
  item each. Each item specializes its Phase 2 item. The ports name no
  computer, transport or technology, and no item is typed with a vehicle
  signal specification: that typing starts in Phase 8, at the port where an
  item enters a software contract.

Three concerns of this phase are held by the parties they serve: the process
by system architects and systems engineers, the modes by system architects
and software developers, and the interfaces by systems engineers and software
developers. One view answers each: the process as an action flow of the SAF
System Process viewpoint, the modes as a table of the System State viewpoint,
which also frames `degradedInputBehaviorConcern`, and the five port
definitions with their items as a tree of the System Interface Definition
viewpoint (SysIDE draws no definition in an interconnection view). With the
breakdown tree and the requirement matrix, whose viewpoint is System
Requirement Traceability (which function a requirement addresses), the phase
publishes five views, listed in `VIEWS.md`.

## Logical architecture (Phase 7)

`closed_loop_driving_logical_architecture.sysml` answers what
technology-independent logical elements realize the seven functions. The
decomposition subject is the system of interest itself:
`ClosedLoopDrivingLogicalSystem` specializes the functional boundary of
Phase 6, keeps its five ports and owns the system's inside, one level below
the boundary. The context elements of Phase 2 stay outside and undivided. The
package's one usage of the definition, `closedLoopDrivingLogicalSystem`, exists
for the views, which draw usages; it is the same system as the context's
`drivingSystem`, not a second one.

The owner decided on six logical elements, not one per function (2026-11-06):
functions share an element when nothing requires them to be separately
placeable, and split where a requirement constrains the exchange between them
or demands that one keeps working when the other does not.

- **Input conditioner** carries the assembly of the checkpoint inputs: the
  ingress of the system.
- **Planner** carries the identification of the run and the planning of the
  trajectory: the identity check is on the checkpoint the planner loads, so
  the two functions share it.
- **Loop supervisor** carries the supervision of the loop and is the one
  authority on the mode; it issues no command.
- **Vehicle commander** carries the commanding of the vehicle, the one command
  source, with the stop response as a mode of its computation.
- **Actuation gateway** carries the application of the commands at the
  actuation and applies the stop response itself when no valid command
  reaches it (REQ-DRIVING-028), so it is separate from the commander. It
  reports its actuation state to the state publisher, off the loop.
- **State publisher** carries the publication of the operational state, one
  way; nothing it provides flows back into the loop. It publishes the stop
  with its cause whether the supervisor or the actuation gateway decided it.

Each function is allocated to its element by a native allocation from the
definition-nested function usage Phase 6 allocated the requirements to; the
allocation is a responsibility assignment, not a realization, deployment or
runtime claim. The exchanges are connections between typed ports: the
boundary items are delegated from the inherited ports (the ego motion to the
input conditioner, the vehicle commander and the state publisher alike), and
inside, the checkpoint inputs and the input condition leave the input
conditioner, the plan goes from the planner to the loop supervisor and to the
state publisher, the newest valid plan and the mode go on to the vehicle
commander, the mode also to the state publisher, the command goes from the
vehicle commander to the actuation gateway, and the actuation state from the
actuation gateway to the state publisher (the amendment of 2026-11-06 for
GAP-DRIVING-005). The plan and command exchanges are the ones REQ-DRIVING-014
constrains, the actuation state the one REQ-DRIVING-029 times, and
Phase 8 places them on a technology. No element, port or exchange names a
computer, a process, a transport or a signal catalogue.

Three concerns of this phase are held by the parties they serve: the
structure by system architects and software developers, the function mapping
by system architects and verification engineers, and the internal exchanges by
systems engineers and software developers. One view answers each, per the
method's list of views per phase: the structure as a tree of the SAF System
Structure Definition viewpoint, the mapping as a matrix of function by logical
element of the System Function Mapping viewpoint, and the exchanges as an
interconnection of the System Internal Exchange viewpoint. The phase publishes
three views, listed in `VIEWS.md`.

## Physical and software realization (Phase 8)

`closed_loop_driving_physical_software_realization.sysml` answers what
software, hardware and deployment elements realize the six logical elements,
and on which technology the exchanges travel that REQ-DRIVING-014 and
REQ-DRIVING-028 constrain. The owner's picks of 2026-11-06, as amended on
2026-11-09 from the readiness probes (below):

- **Topology A, one FEO agent.** The loop is one Eclipse S-CORE program: a
  fixed-execution-order agent (eclipse-score/feo v1.0.5 with a DE4SDV
  **event trigger**) that runs four activities in one Linux process, in the
  order of the loop, once per camera frame: condition the inputs, infer the
  plan, supervise the loop, command the vehicle. The trigger takes the
  newest frame and counts the frames it skipped. Each activity is a software
  element that carries one logical element: a Rust shell over C++ libraries,
  because FEO's topics are Rust-only. The **actuation adapter** and the
  **state publisher** are S-CORE applications of their own, so the stop
  response of REQ-DRIVING-028 survives the agent and the observation stays
  off the loop. The two processes of the S-CORE SOME/IP gateway, `gatewayd`
  and `someipd`, carry the publisher's reach to the guests; the Launch
  Manager of S-CORE Lifecycle, which runs as root, starts and supervises the
  three programs and carries no logical element.
- **The planner on PyTorch in the agent's process.** The plan inference
  activity runs the pinned AutoE2E checkpoint on PyTorch, with DE4SDV's
  rounding-level kernel changes and pinned libraries (torch 2.7.1, triton
  3.3.1, cuDNN 9.26.0.51). The pick of 2026-11-06, an inference engine over
  an ONNX export, failed at the export: the exporter ran out of 64 GB of
  memory. The stack's parity with the reference is an assumption
  (ASM-DRIVING-002) with GAP-DRIVING-003 behind it until phase 10 measures
  it on the bench.
- **S-CORE at v0.10.0** (reference_integration `ca2a5f03`): Communication
  v0.6.0, Lifecycle v0.10.0, Logging v0.2.6, Time v0.3.1, Configuration
  Management v0.3.1. FEO (GAP-DRIVING-001, built beside them with eight
  module overrides) and the SOME/IP gateway of INC-MW-011 sit outside that
  baseline and are pinned separately. No source is vendored. **KUKSA stays
  unselected** (ALT-MW-KUKSA-001).
- **Simulator at wall-clock pace, never waiting for a plan.** The simulator
  runs in synchronous mode with a 100 ms step, ticked by a world-side pacer
  on the wall clock, so no element of the loop ticks it. Capture times come
  from the frame index. Simulation time comes with each measurement and
  from the world snapshot at the actuation adapter; wall-clock time from
  the host. The simulator server and the scenario's route provider are
  System 2 context realizations; the route provider realizes the Phase 2
  navigation on the S-CORE host, not on the AAOS guest, so the context-role
  decision of 2026-11-02 stays closed. The
  sensors of the loop are the simulator's: a simulated sensor rig inside the
  server, six cameras at the positions of `CameraPosition` and one
  ego-motion source. Its geometry is the rig profile of the pinned
  checkpoint's dataset at the source pin (one JSON per dataset rig, six
  cameras with native image size, intrinsic matrix and camera-to-reference
  pose, and the dataset's curvature rule); which profile applies follows the
  checkpoint pinned in Phase 10, so the model states the rule and no number.
  The ego motion is the simulator's vehicle state, ground truth without a
  sensor's noise and latency: ASM-DRIVING-004 says so, and the projection
  operators are built from the simulated cameras' calibration, with the
  profile's principal-point offset recorded at the pin. The product line's
  sensing boundary types its camera as a detection camera, so it does not
  type these; the rig stands for the sensing assembly by dependency.
- **The production observation path, typed.** The publisher takes the plan,
  the mode and the ego-motion sample from the agent and the actuation state
  from the actuation adapter, each an mw::com event
  (`MAP-DRIVING-ACTUATION-STATE` for the last). The operational state leaves
  the publisher as an mw::com event, goes through `gatewayd` and `someipd`,
  crosses a VXLAN segment on SOME/IP into the SDV Core VM, becomes a typed
  Data Tunnel topic (a VSIDL message, GAP-DRIVING-006) and reaches the
  observer on the IVI VM through the SDV Gateway. Nothing flows back.
- **VSS at the contract ports.** The ego-motion sample is typed by COVESA
  VSS where it enters the S-CORE contract; the commanded acceleration and
  steering angle are two `DE4SDV_VSS_Extensions` candidates, local to
  DE4SDV.
- **Three hosts** (2026-11-09). The S-CORE host carries the driving
  software and the route provider on the planner's GPU, an RTX PRO 6000
  class card that runs nothing else; the simulator host renders on its own
  GPU; the guest host runs the two AAOS SDV guests under KVM. The
  simulator's exchanges cross the bench network; a VXLAN segment joins the
  S-CORE host to the guests' bridge, so the guest images stay unchanged.
  The cloud's GPU hosts nest no VM, and the planner missed its budget
  whenever the simulator rendered on its card.
- **Bench rules and recording** (2026-11-09). Eight operating rules: pinned
  planner code, a parity check at start, capture-safe preprocessing, no
  recompilation after the warm-up, a history cache of 64 entries, capture
  times from the frame index, the simulator never on the planner's card,
  and one **warm-up lap** with every camera before any judged or recorded
  run. Each host records its part of a run in real time: the simulator's
  chase view, encoded by its **NVENC** encoder; the IVI screen, on the
  guest; the terminals, as terminal sessions. Nothing is retimed.

Each logical element is allocated to the software element that carries it
(eight allocations; the publisher reaches the observer through three
elements), and each crossing of an item into a software contract has a
system-to-software signal mapping with its record (`MAP-DRIVING-*`, nine
candidates): what the item is, which contract it enters, its type and unit,
its timing, its transformation, where the bench keeps the contract that
Phase 10 authored, and what is left to do. An allocation is a responsibility
assignment, no deployment or runtime claim; a mapping is no interoperability
claim; a pin is no build claim.

Four assumptions and eight gaps record what the realization depends on and
what it found. Four of the gaps, GAP-DRIVING-010 to GAP-DRIVING-013, are
accepted as known limits (see Phase 6 and the readiness probes below); the
others are deferred.
The **readiness probes** of 2026-11-07 to 2026-11-09 retired
two gaps: the SOME/IP gateway built at the v0.10.0 modules and carried 600 of
600 events between two hosts to the IVI VM (GAP-DRIVING-002), and the
simulator's client library linked into an S-CORE application
(GAP-DRIVING-004). They narrowed GAP-DRIVING-003 to the planning stack's
parity and turned GAP-DRIVING-007 into the open question of the three hosts
in one run; a probe is evidence for an amendment, never a result of the
increment. With the simulator on its own card the planner met REQ-DRIVING-013's
budget at wall-clock pace in the probe, so the increment needed no redirect.
The first verification runs missed it narrowly: **GAP-DRIVING-013**, accepted
on the owner's decision of 2026-11-10, records the margin. In three runs on
the straight route 97.5 to 99.2 % of the plans came in time, and in each two
in a row missed, the latest by 7.7 ms; an earlier run met it at its limit,
99.0 %, with the vehicle standing for most of the window. Since the agent
draws a step's navigation raster ahead of the step, the two complete
closed-loop runs met it, with all 600 plans in time and the latest after 96.5
and 98.3 ms. The checkpoint's inference alone takes about 90 ms of the 100, so
a few milliseconds anywhere make a miss. The limit stays at 100 ms.
**GAP-DRIVING-005** was new information from the placement:
the actuation adapter's own stop response (REQ-DRIVING-028) had no path to
the publication REQ-DRIVING-029 asks for, because phases 6 and 7 had no flow
from the actuation gateway to the publisher. The owner decided on 2026-11-06
to amend phases 6 and 7 with an actuation-state flow to the publisher; the
amendment landed in phases 6 to 8 (the `ActuationState` item and flow, the
`actuationStateToPublisher` connection, the `actuationStateOverSCORECommunication`
hop with `MAP-DRIVING-ACTUATION-STATE`) and the record left the model. The
same amendment described the sensing in the places it belongs: the Phase 6
exchange types, the simulated sensor rig of Phase 8 with ASM-DRIVING-004,
and the dependency on the product line's sensing assembly. The sensors stay
the vehicle's, context of the loop: the logical architecture decomposes the
system of interest only.
The reading of the plan hops inside the agent, FEO topics rather than the
Communication module, was settled the same day: they are no hops between
processes and REQ-DRIVING-014 does not constrain them; the comment
`reqPlansAndCommandsOverSCOREReading` holds the reading. The other gaps are
readiness-probe items (FEO and the gateway against v0.10.0, the model export
and its parity, the simulator client's build, the typed topic, a GPU and KVM
host) that run before phase 10 builds anything; a paid host needs the
owner's campaign authorization.

What the IVI observer presents is decided (owner decision 2026-11-06) and
recorded on the observer part: the operational state and nothing else, the
plan with its producer, production time and run record, the vehicle state
sample with its sample time, the health, the mode with the cause of a stop,
and the run identity; no camera images, no commands, no route, nothing back.
Its screen shows two clocks side by side, the simulation time of the newest
input and the wall-clock time of the publication, so that no reading mixes
the time domains; the screen's recording is phase 10 evidence.

Four views answer the phase's questions: the structure as a tree of the SAF
Physical Structure Definition viewpoint, the logical-to-software mapping as
a matrix of the Physical Logical Mapping viewpoint, the S-CORE path as an
interconnection of the software realization (Physical Internal Exchange
viewpoint, framing the Phase 1 concerns for the S-CORE path and the
checkpoint's command authority), and what crosses the realization's
boundary on the bench as an interconnection of the physical system (Physical
Context Exchange viewpoint, framing the Phase 1 observation-fidelity and
command-authority concerns): into the simulator server the vehicle control
and nothing else, out of it the camera stream, the ego motion and the
simulation clock, from the route provider the route, and the operational
state on SOME/IP into the SDV Core VM and on the Data Tunnel topic to the
IVI VM, each exchange a flow labelled with its item. The last viewpoint is
not yet in the method's views-per-phase list for Phase 8; the deviation is
pinned in `tests/test_views_per_phase.py` and a method change proposes the
entry. The phase publishes four views, listed in `VIEWS.md`.

## Variability and configuration (Phase 9)

`closed_loop_driving_variability_configuration.sysml` answers which product
of the line the driving system belongs to, and with which selections. The
owner's picks of 2026-11-06, after the phase 3 decision of 2026-11-02 that
the driving stack is a feature and requires the camera:

- **The feature.** `autoE2E` joins the vehicle-application group of the
  feature model (`F-PLATFORM-VEHICLE-APPLICATION-AUTOE2E`) with two requires
  constraints, C012 on the camera and C013 on Linux (the mirror of C011 for
  Autoware), and corresponds to the driving-stack variability the governed
  scope defers. Its pairing with the middlewares is stated the way openpilot
  and Apollo state theirs: an exclusion of `androidSDV`, `autosarAdaptive`
  and `noMiddleware`, because no derivation rule exists for those pairs, and
  one derivation rule for the pair with Eclipse S-CORE that derives the
  adapter `autoE2EToSCORE`. An exclusion lifts the day someone adds an
  adapter and its rule; a `requires eclipseSCORE` would have frozen the
  bench architecture into the line. The exclusion of `androidSDV` costs the
  driving member nothing: `middleware` is the main-side integration
  middleware, one per product, and the member's AAOS SDV is the guest
  middleware of the guest side.
- **The shared asset.** `sdv_platform_stack.sysml` gains the two variants
  the binding and the rule target: `autoE2E : AutoE2EStack` and
  `autoE2EToSCORE : AutoE2EToSCOREAdapter`. The adapter is the mw::com
  binding code of the three programs of Phase 8, no program of its own.
- **The configuration.** `closedLoopDrivingAutoE2ESCOREReference` selects
  AutoE2E, Eclipse S-CORE, Linux and KVM on the main side, Android with the
  AAOS SDV middleware in the guest, the camera alone, and the HMI display:
  the observer of the IVI VM is this member's display, selected on the same
  ground as MW-CONFIG-002 (no shared asset resolves it; the projection lists
  it among the selections SysML does not resolve). No requirement of the
  increment names the display, so, unlike INC-MW-011, no requirement depends
  on `hmiDisplay`. The privileged PLE authority workflow cut the receipt;
  the configurator generated the projection
  `ClosedLoopDrivingAutoE2ESCOREReference` from it. The receipt records the
  configuration as **valid and not admitted**: the driving stack is deferred
  variability, Eclipse S-CORE is reference-only, the display is outside the
  governed scope, the guest side realizes the AAOS-integrated alternative
  without its middleware, and the configuration does not represent the
  common content (no Autoware, no LiDAR). The same receipt re-cut rebinds
  MW-CONFIG-002's digest; its own record did not change.
- **The configured product.** `DRIVING-CONFIG-001` pairs the projection
  with the Phase 8 realization of the driving system and binds the
  realization's S-CORE services to the selected middleware. Phase 8
  composes those services in the realization, because the two gateway
  processes sit on the observation path, so the binding makes two
  composers hold one instance, where INC-MW-011's layer only refers to
  its services; the product says so rather than hides it. The derived
  adapter and the selected application are dependencies, not parts: the
  adapter is the programs' binding code, and the driving agent runs the
  exported checkpoint of the application. The product does not compose the
  physical context; a test keeps the host and guest layers of that context
  typed by the definitions of the selected variants. The identity binds the
  SHA-256 of the receipt, and Phase 10 evidence binds the identity. The
  definition specializes no member-product type: the member decision that
  amends ADR 0014 follows the runnable proof, as the framing's admission gap
  asks.

Two views answer the phase's questions, both trees: the selections of the
projection (Product Line Configuration viewpoint) and the assembly of the
product with its one binding (Product Model Assembly viewpoint), listed in
`VIEWS.md`.

## Verification and evidence (Phase 10)

`closed_loop_driving_verification_evidence.sysml` answers how each
requirement will be checked and what the increment will claim once it is.
This is the first slice: the cases, not the runs. The owner's picks of
2026-11-06:

- **One case per requirement.** VC-DRIVING-001 to VC-DRIVING-035, one for
  each of the 35 requirements, every objective binding the requirement's
  subject to the driving software of DRIVING-CONFIG-001 on the bench. Each
  case checks the success criteria its requirement states and adds no
  criterion of its own; each collects by test and processes and evaluates
  by analysis, from the record of its run to the increment's own outcome
  vocabulary and the standard verdict. Every case is Not started and every
  requirement keeps NotStarted. The cases of one scenario read the record of
  the same run: 20 of them read one run of SC-DRIVING-001.
- **The increment's own outcome vocabulary.** `DrivingEvidenceOutcome`
  carries the six literals of INC-MW-010's vocabulary, so that a later lift
  into the method is a rename; only the bounded-verification outcome maps to
  pass, a missing or partial record to inconclusive.
- **One record per run.** `RetainedDrivingRunEvidence` binds
  DRIVING-CONFIG-001 and the receipt it ran against, the model revision, the
  checkpoint, source and configuration identities of the run record of
  REQ-DRIVING-033, the pins of the S-CORE components and of the simulator,
  the scenario, the two clock spans kept apart, the retained records and the
  **bench recording**: since 2026-11-09, separate real-time recordings, one
  per host (the simulator's chase view encoded on the simulator host after a
  warm-up lap, the IVI VM's display with the observer application, the
  terminal sessions), each with its clocks; **both clocks** stay visible. A
  public cut may place them side by side, aligned by the run record's
  clocks, never retimed. This supersedes the single capture of 2026-11-06;
  the public cut of the increment comes from these recordings and from
  nothing else.
- **Claims now, counter-claims from the non-claims.** Seven claims, one per
  phase 1 concern this phase answers (driven along the route, checkpoint
  command authority, the S-CORE command path, observation fidelity,
  degraded-input behavior, time-domain honesty, reproducible evidence), each
  with an argument that cites the cases that will support it; seven
  counter-claims that repeat the framing's non-claims (simulated sensors, no
  real time on target, no safety or certification, no membership, checkpoint
  rights, bounded faults, no verdict yet), each tied to the record that keeps
  it open. A claim written before its evidence is a claim to be proven. One
  tree view of the `ArgumentationAssuranceViewpoint` links them, and frames
  the two phase 1 concerns of the Architecture Management domain beside the
  phase's own.
- **The environment's identity stays a gap.** GAP-DRIVING-009: the five
  readiness probes the owner authorized on 2026-11-06 were read from
  2026-11-07 to 2026-11-09, and Phase 8's amendment fixes the hosts, the
  topology and the capture (three hosts, separate recordings per host).
  Still open: the three hosts have not run together, and the evidence record
  does not yet name the hosts, their images and the recordings' clocks.

## Next obligation and execution limits

Use the reviewed revision's **Method Check** export to identify the first
unmet model-content obligation; it is not proof that earlier engineering
work is complete. The next work is the **second slice of Phase 10**: the
bench on three hosts, the runs of the 35 cases and their evidence records
with the bench recordings, then the member
decision that amends ADR 0014 and the baseline of Phase 11. Do
not jump from this context to implementation or claim a passed runtime
gate.

Before deep adoption, involve upstream maintainers and resolve source,
checkpoint and data-use terms. Before a paid cloud run, refresh the regional
quote, capacity/storage and available credit; obtain campaign authorization and
verify bounded shutdown plus evidence export. Starting this increment does not
launch compute or authorize spend.

## Check a model change

Run `sysand sync`, `python scripts/check_repo.py`, `python scripts/smoke_test.py`
and `python -m pytest -q` on `tests/test_closed_loop_driving_framing.py`,
`tests/test_closed_loop_driving_operational_context.py`,
`tests/test_closed_loop_driving_capability_classification.py`,
`tests/test_closed_loop_driving_needs.py`,
`tests/test_closed_loop_driving_requirements.py`,
`tests/test_closed_loop_driving_functional_architecture.py`,
`tests/test_closed_loop_driving_logical_architecture.py`,
`tests/test_closed_loop_driving_physical_software_realization.py`,
`tests/test_closed_loop_driving_variability_configuration.py`,
`tests/test_closed_loop_driving_verification_evidence.py`,
`tests/test_verification_model_invariants.py`,
`tests/test_ple_authority_model.py`, `tests/test_ple_authority_receipts.py`,
`tests/test_trace_allocation_completeness.py`, `tests/test_views_per_phase.py`
and `tests/test_check_naming.py`.
These are repository/lexical checks, not SysML semantic or runtime verification.
Use `python scripts/validate_sysml.py` when a supported licensed validator is
available, or request maintainer-run **Privileged Syside Validation** on the
reviewed head. The views and their published artifacts must come from that
Syside run; no hand-drawn substitute establishes model validation.
