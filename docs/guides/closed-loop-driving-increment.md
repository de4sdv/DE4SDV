# Closed-loop driving increment

DE4SDV needs to distinguish a driving function that actually influences vehicle
behavior from a prediction overlay on a separately driven car. This increment
proposes the former: real camera-based learned planning, a functional S-CORE
integration path, and an AAOS SDV application showing genuine plan/state/health.

**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context,
Phase 3 capability classification, Phase 4 stakeholder needs, Phase 5
requirements and Phase 6 functional architecture, proposal.** No
implementation, successful driving run, performance result or product-line
admission is claimed.

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
  time (001); each plan by inference of the pinned checkpoint on the camera
  images, the ego-motion history and the route of its step (002); the input form
  it takes: six camera images at the two sizes it asks for (003),
  seven earlier images per camera (004), one projection operator per image (005),
  the `map_context` raster (006), the `route_mask` raster (007) and 64 motion samples
  100 ms apart (008); standstill until both histories are complete (009);
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
- **`planTrajectory`** makes one plan for each step by checkpoint inference
  and marks it;
- **`superviseLoop`** detects degraded camera images, motion, route and plans,
  and sets the mode;
- **`commandVehicle`** computes the steering and acceleration commands of each
  mode;
- **`applyCommands`** gives the commands to the actuation of the vehicle and
  marks their actuation time;
- **`publishState`** publishes the plans, the vehicle state, the health and a
  stop for observation.

They are `AllocatableFunction` actions of the functional flow
`ClosedLoopDrivingFunctionalFlow`. The flow takes the camera images, the
ego-motion state and the route of Phase 2 in, and gives the commands to the
actuation and the operational state to the state observer. Inside, the
functions exchange the checkpoint inputs, the input condition, the plan, the
mode and the run record.

Three decisions shape it:

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
  of its own, so the increment has one context. Navigation gives the route,
  the vehicle's cameras and motion sensing give the images and the ego motion,
  the vehicle's actuation applies the commands, and the state observer
  presents the published state. Those five are functions of the context
  elements (`ContextElementFunction`), outside the scope of the driving
  system: no requirement is allocated to them. The driving system performs
  the one functional flow usage, the same one its functional boundary
  performs, as one action of the process, and the five items that cross its
  boundary are the flows of the process. Nothing flows back from observation.
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
which also frames `degradedInputBehaviorConcern`, and the boundary definition
as an interconnection of the System Interface Definition viewpoint. With the
breakdown tree and the requirement matrix, whose viewpoint is System
Requirement Traceability (which function a requirement addresses), the phase
publishes five views, listed in `VIEWS.md`.

## Next obligation and execution limits

Use the reviewed revision's **Method Check** export to identify the first
unmet model-content obligation; it is not proof that earlier engineering
work is complete. The next work is **Phase 7**, the logical architecture: the
logical elements that realize the functions, with each function allocated to
one of them. Its first gate is `functionAllocatedToLogicalElement`.
Do not jump from this context to implementation or claim a passed runtime
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
`tests/test_trace_allocation_completeness.py` and
`tests/test_check_naming.py`.
These are repository/lexical checks, not SysML semantic or runtime verification.
Use `python scripts/validate_sysml.py` when a supported licensed validator is
available, or request maintainer-run **Privileged Syside Validation** on the
reviewed head. The views and their published artifacts must come from that
Syside run; no hand-drawn substitute establishes model validation.
