# E/E architecture increment

The model of the product line describes one SoC as the compute of a member
product. The platform stack describes that SoC with a main side and an
optional guest side, and the model names the vehicle network only as a
boundary. It does not say how a driving command leaves that computer and
reaches an actuator across a vehicle network, nor what happens when that
network fails. This increment frames a first part of the electrical/electronic
(E/E) architecture of the product line, its vehicle network: one central
computer, two zone controllers, an Ethernet backbone and CAN at the edge. It
asks whether the path of a driving command keeps, across that network, the
properties that the model asks of the command paths of earlier increments. It
judges two routes: through a zone controller, and over a direct link.

**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context,
Phase 3 capability classification, Phase 4 stakeholder needs, Phase 5
requirements, Phase 6 functional architecture and Phase 7 logical
architecture, proposal.** No implementation, run, result, product-line
admission or compliance is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/ee/ee_architecture_framing.sysml):
  `INC-EE-001`, its engineering question, charter, scope, assumptions,
  open gaps and Phase 1 concerns.
- [SysML operational context](../../textual-notation-of-model/packages/features/ee/ee_architecture_operational_context.sysml):
  the Phase 2 context of the vehicle network and its story of four scenarios.
- [Syside framing review view](../../textual-notation-of-model/packages/features/ee/VIEWS.md):
  the generated model review artifact, not a runtime architecture claim.
- [Upstream provenance](../../textual-notation-of-model/packages/features/ee/upstream.md):
  the public sources read for the
  [route through a zone controller](../../textual-notation-of-model/packages/features/ee/upstream.md#zone-controller-route),
  and what each of them supports.

Orkun Yilmaz owns the increment. One identity covers phases 0 to 11.
Verification on a virtual vehicle belongs to Phase 10 of this increment. A
readiness probe comes before the architecture rests on what it tests.

The increment builds on the [driver-assistance
increment](driver-assistance-increment.md): its driving command, whose form
that increment fixes at its baseline; that increment states no cadence of the
command as such. It takes the driving command as that increment fixes it and
changes none of its criteria or verdicts. The stop response on lost commands
comes from the [closed-loop driving
increment](closed-loop-driving-increment.md), and the safety path from the
[middleware
requirements](../../textual-notation-of-model/packages/features/middleware/middleware_requirements.sysml).
None of them asks these properties of a vehicle network; Phase 5 of this
increment derives its own requirements from them.

## The engineering question

> When the actuation is an ECU on a CAN bus at the edge of a zonal vehicle
> network, does the path of the driving command keep, across that network, the
> properties that the model asks of the command paths of earlier increments,
> on each of two routes: through the Ethernet backbone and a zone controller,
> and over a direct link from the central computer? The properties are a
> command whose loss, delay, repetition or corruption the actuation can
> detect, which REQ-DRIVING-039 asks on the Eclipse S-CORE path; a stop
> response when no valid command has reached the actuation for 200 ms of
> simulation time, which REQ-DRIVING-028 asks of the closed-loop driving
> system; and no uncontrolled emergency intervention command from a failure of
> the non-safety middleware integration path, which REQ-MW-006 asks of each
> member product. For the driving command, the driver-assistance increment
> places a share of that requirement at the actuation: to apply no command
> that the actuation rejects. The model asks none of these properties of a
> vehicle network. Phase 5 derives the requirements of this increment from
> them. A verdict for each requirement of the increment on each route, on a
> virtual vehicle, answers this. A run in which commands arrive does not.

The increment supports one decision: whether the product line admits this
zonal vehicle network, with the route that the driving command takes, as its
reference vehicle network, from which later topologies vary, admits it with
named changes, or does not admit it. The decision rests on executed cases with
a pass or a fail for each requirement of the increment on each route. A fail
is a result to record. It is no reason to change a scenario or a criterion
until the network passes.

## What the increment judges

| In scope | Out of scope |
|---|---|
| One topology of the vehicle network: one central computer, two zone controllers, one Ethernet backbone between them, a CAN bus at the edge of each zone, and a direct link from the central computer to the actuation ECU that passes no zone controller. | Claims on the timing of the vehicle network, such as latency and jitter budgets, and time synchronisation between its nodes. |
| The driving command of the driver-assistance increment, down from its source on the central computer to an actuation ECU on CAN. | Traffic shaping, and the behavior of the command under competing load on the network. |
| Two routes of the driving command to the actuation ECU: through the Ethernet backbone and a zone controller, and over the direct link. | Diagnostics and software update of the ECUs through the zone controllers. |
| Faults of the vehicle network on the route of the command: one link of that route that goes down, and a command that is lost, delayed, repeated or corrupted on its way. | Security hardening: segmentation, authenticated messages and link protection. |
| A pass or a fail for each requirement of the increment on each route, on a virtual vehicle, from the replay of a recorded command stream, bound to the route, the topology, the configuration and the revision that ran. | Redundancy, the operation of the vehicle after the loss of a whole zone, and power modes such as sleep and wake. |
| | A second topology, and any variability of the E/E architecture in the product line. |
| | Sensor data, such as the vehicle speed, up from an ECU on CAN to the central computer. |
| | Closed loop with a driving simulator through the vehicle network. |
| | Effects of hardware: the physical layer, bit timing on CAN and the timing of microcontrollers. |
| | Any safety argument, including freedom from interference, and any compliance, type approval or certification claim. |

The scope is one topology that holds both routes, one configuration and at
most ten requirements. Phase 5 derives those requirements from the needs of
Phase 4 and from REQ-DRIVING-028, REQ-DRIVING-039 and REQ-MW-006. A time limit
of a requirement counts on the clock of the virtual vehicle, and a verdict on
it is no timing claim for a vehicle network.

## Concerns (Phase 1)

A verdict is only useful if it answers the questions of the people who rely on
it. Phase 1 names those questions: one concern per question of the in-scope
items, held by the parties whose interest it states. The vehicle occupants and
the road users hold their own concern beside the engineering roles. Each
concern is typed by the SAF concern that asks its question, and its text names
the view of a later phase that answers it. The framing viewpoint frames all
six, and a view of a later phase that answers a concern frames it as well.

- **The driving command, operational part:** `eeVehicleCommandConcern`. The
  vehicle acts on the driving command that its central computer gives,
  whichever route the command takes, and on no command that a fault of the
  network has made invalid. No safety, timing or performance claim for a
  vehicle network follows from it. Operational capability; vehicle occupants
  and road users. Answered by the operational story of Phase 2.
- **The topology:** `eeTopologyStructureConcern`. Which elements make up the
  one topology, and the role of each: the network side of the central
  computer, the backbone, the two zone controllers as gateways to CAN, the CAN
  bus of each zone, the direct link and the actuation ECU. The lifecycle
  decision is whether the product line admits this topology as its reference
  vehicle network. Physical structure; system architects and product-line
  engineers. Answered by the physical structure definition of Phase 8.
- **The command on the network:** `eeCommandItemConcern`. Which exchange item
  carries the command on the backbone, through a zone controller and on CAN,
  and whether each keeps the parts of the command by which the actuation
  detects its loss, delay, repetition or corruption. The form of the command
  is the one that the driver-assistance increment fixes at its baseline.
  Physical-logical item mapping; systems engineers and safety experts.
  Answered by the view of the claimed path in Phase 8.
- **The two routes:** `eeCommandRouteExchangeConcern`. Which elements exchange
  the command on each route, through a zone controller or over the direct
  link, and the boundary interface by which it enters the network from the
  Eclipse S-CORE path. Neither route is taken as given. Physical internal
  exchange; system architects and systems engineers. Answered by the view of
  the claimed path in Phase 8.
- **Faults of the network:** `eeNetworkFaultResponseConcern`. The sequence
  from each fault on the route, a link that goes down or a command lost,
  delayed, repeated or corrupted, to its detection at the actuation and the
  response there, independent of the elements that realize it. System process;
  safety experts and systems engineers. Answered by the system process of
  Phase 6.
- **Verdicts:** `eeRouteVerdictConcern`. A pass or a fail for each requirement
  on each route, bound to the route, the topology, the configuration and the
  revision that ran. A verdict holds for the software testbed only and is no
  timing claim for a vehicle network. Argumentation assurance; product-line
  engineers and verification engineers. Answered in Phase 10.

The Phase 1 gates check that each concern has native stakeholders and a frame,
and that one concern is not the boundary concern. They do not judge whether
the stakeholder, risk and viewpoint coverage is adequate; review does.

## Operational context and story (Phase 2)

Phase 2 draws the boundary that Phase 0 states and does not move it. One
operational context holds the vehicle network as a black box. Inside the
vehicle network: the network side of the central computer, the Ethernet
backbone, the two zone controllers, a CAN bus in each zone, the direct link
and the actuation ECU. Around it: the source of the driving command
(`DrivingCommandSource`), the Eclipse S-CORE path and the vehicle, which takes
the applied command and sends nothing back. The command crosses the boundary
once in, from the S-CORE path, and once out, to the vehicle. The central
computer lies across the boundary, so the context draws no part for it. The
testbed, the replay, the fault injection, the vehicle model, the records and
the evaluators stay in `eeVerificationEnvironment`.

It imports two names of the operational context of the driver-assistance
increment, `DrivingCommand` and `SCORECommandAndWarningPath`: names, not the
form of the command. The form of the command is the one that the
driver-assistance increment fixes at its baseline
(`asmEECommandFromDrivingBaseline`); that baseline states no cadence of the
command as such.

The story holds four scenarios. `SC-EE-001` carries the command through a zone
controller, `SC-EE-002` over the direct link, `SC-EE-003` covers a command
that is lost, delayed, repeated or corrupted on either route, and `SC-EE-004`
a link of the route that goes down, after which the vehicle gets the stop
response. The stop response comes from the engineering question and
REQ-DRIVING-028 of the closed-loop driving increment, not from the
driver-assistance increment, whose adapter has no stop response
(`gapEEActuationEnd`). The criteria and their limits are fixed with the
requirements in Phase 5, and the verdict for each route comes from Phase 10.
No timing, safety or compliance claim for a vehicle network is made.

The context view frames `eeArchitectureContextConcern`. The story view frames
`eeArchitectureStoryConcern` and the Phase 1 concern
`eeVehicleCommandConcern`, which the story answers.

## Capability classification (Phase 3)

The increment adds no characteristic that distinguishes member products. Its
[capability classification](../../textual-notation-of-model/packages/features/ee/ee_architecture_capability_classification.sysml)
records no feature candidate and no deferred scope. Core elements are common
by default and get no record.

- **The topology:** one topology for one configuration; a second topology and
  any E/E variability are out of scope, and no member of the product line
  holds a vehicle network.
- **The two routes:** a design alternative inside that topology; the increment
  judges both, and its lifecycle decision names the route of the reference
  vehicle network. No member differs by its route.
- **The driving command and its source:** the command is that of the
  driver-assistance increment, and what gives it is that increment's to
  classify; Eclipse S-CORE is a feature of the feature model. The command
  source, the S-CORE path and the vehicle get no feature from this increment.
- **Faults, verdicts and the medium of the direct link:** requirements and
  evidence of Phases 5 and 10 and a choice of Phases 6 to 8, none of them a
  feature. **The vehicle-target compute family:** the deferred vehicle runtime
  variability of the governed scope; the increment selects no compute target.
- **Scope decisions** (`gapEENetworkInProductLine`): whether the governed
  scope takes the reference vehicle network as common content, what that means
  for the AEBS emergency path and the brake hand-off, and whether later
  topologies enter the scope as deferred variability, are open for the
  lifecycle decision. This increment admits nothing.
- **The platform stack and the network boundary**
  (`gapEEStackAndNetworkBoundary`): they get no feature from this increment.
  How the network side of the central computer relates to the SoC and the
  hardware layer of the platform stack is open for Phases 6 to 8, and whether
  Phase 8 allocates a node of the network to the vehicle-target family is open
  for Phase 8.

The one blocking check of Phase 3 evaluates the characteristics recorded, and
this phase records none, so the Method Check reports Phase 3 as having nothing
to evaluate. Review judges the classification.

## Stakeholder needs (Phase 4)

The [stakeholder
needs](../../textual-notation-of-model/packages/features/ee/ee_architecture_needs_requirements.sysml)
say what the parties of the Phase 1 concerns expect of the vehicle network.
Each need is held by the parties it serves and leads its source with the
concern it comes from. Each has one planned stakeholder review on the Phase 2
scenarios it covers, carried out by the roles that check the answer.

- `NEED-EE-001`: the network carries the driving command of the central
  computer to the actuation ECU on each route of the command. Vehicle
  occupants and road users. Reviewed by `SC-EE-005` on `SC-EE-001` and
  `SC-EE-002`.
- `NEED-EE-002`: the network applies to the vehicle no driving command that a
  fault of the network made invalid on its way. Vehicle occupants and road
  users. Reviewed by `SC-EE-006` on `SC-EE-003` and `SC-EE-004`, which also
  asks whether a response followed when no valid command reached the actuation
  ECU, and which.
- `NEED-EE-003`: each run identifies the route that carried the command and
  the topology and the revision of the network that ran. Verification
  engineers and product-line engineers, who use the run identity in their own
  work. Reviewed by `SC-EE-007` on all four scenarios.

Four concerns get no need of their own: the topology, the elements that
exchange the command on each route, the exchange items that carry it, and the
sequence from a fault to its response. Their roles check the answer rather
than use it, as in the stakeholder needs of the driver-assistance increment,
so each is a question for a planned review: `NEED-EE-001` names the first two
in its source and `SC-EE-005` asks them, and `NEED-EE-002` names the other two
and `SC-EE-006` asks them. No need states a number: Phase 5 derives the
requirements, their limits and the share of the network in the response when
no valid command arrives, after REQ-DRIVING-028 of INC-DRIVING-001. The form
of the command comes from the baseline of the driver-assistance increment,
which states no cadence of the command as such; Phase 5 states that input
contract in its requirements.

`tests/test_ee_architecture_needs_requirements.py` pins the needs, their
holders and sources, the planned reviews and their scenarios, and the wording
a need may not use. The Phase 4 gates check that each need has a statement, a
stakeholder, a source, a rationale and a planned review. Review judges whether
the needs are the right ones.

## Requirements (Phase 5)

The
[requirements](../../textual-notation-of-model/packages/features/ee/ee_architecture_needs_requirements.sysml)
state what the vehicle network shall do and how each is verified. Each has one
subject, the vehicle network, derives from one need, and has one verification
method and its success criteria. They derive from the Phase 4 needs and from
REQ-DRIVING-028, REQ-DRIVING-039 and REQ-MW-006, and the scope caps them at
ten. A time limit counts on the clock of the virtual vehicle and makes no
timing claim for a vehicle network.

- `REQ-EE-001`: both routes in one topology. From `NEED-EE-001`, by
  inspection; a design constraint.
- `REQ-EE-002`: driving commands only from the Eclipse S-CORE path. From
  `NEED-EE-001`, by test; a design constraint.
- `REQ-EE-003`: the commands of a run only through the elements of its route.
  From `NEED-EE-001`, by test; a design constraint.
- `REQ-EE-004`: in each run, the delivery to the actuation ECU of each command
  that no fault affects, once, in its order and unchanged. From `NEED-EE-001`,
  by test; functional.
- `REQ-EE-005`: in a run without a fault, each command carried from the
  boundary interface to the actuation ECU within 50 ms of simulation time.
  From `NEED-EE-001`, by test; a performance requirement.
- `REQ-EE-006`: each valid command applied until the stop response starts.
  From `NEED-EE-001`, by test; functional.
- `REQ-EE-007`: each element passes on the issue time, the sequence count and
  the check value as it received them, computing none anew. From
  `NEED-EE-002`, by analysis; a design constraint.
- `REQ-EE-008`: until the stop response, the vehicle gets only the last valid
  command applied. From `NEED-EE-002`, by test; functional.
- `REQ-EE-009`: the stop response once more than 200 ms of simulation time
  pass without a valid command. From `NEED-EE-002`, by test; functional.
- `REQ-EE-010`: the network identity recorded before the first command of each
  run. From `NEED-EE-003`, by test; functional.

The Phase 5 decisions, each with its reason in the rationale of the
requirement that it shapes:

1. A valid driving command is one that the actuation adapter of the
   driver-assistance increment would accept: its check value holds, its
   sequence count is one more than the reference count, and its issue time is
   no more than 100 ms of simulation time old, measured at its arrival in
   place of the newest world time of that adapter.
2. One lost or corrupted command costs two, so at one command each 100 ms the
   valid commands on either side of the gap are issued 300 ms apart and the
   stop response follows, although REQ-DRIVING-028 takes two missed commands
   as the sign of a path that gives no more commands; only when the valid
   command before the gap takes the whole 100 ms to arrive and the one after
   it none is the span exactly 200 ms, with no stop response. Accepting the
   command after a gap would put the span at 200 ms plus the difference of the
   times that the two commands take to arrive, so that whether the stop
   response follows would depend on that difference and on the step of the
   clock of the testbed. A delay that only just makes a command late would put
   the span at exactly 200 ms under either rule, so the run set delays the
   command by 300 ms, after which the stop response follows on every clock.
3. The stop response starts once more than 200 ms of simulation time pass
   without a valid command, so a command that arrives exactly at 200 ms still
   counts: a run without a fault can leave exactly 200 ms between two valid
   commands.
4. The vehicle network gets 50 ms of simulation time from the boundary
   interface to the actuation ECU, half of the delay limit; a run is judged
   only when the path to the boundary interface keeps the other half.
5. The cadence is at most one command each 100 ms of simulation time, from the
   baseline: one image of the front camera each 100 ms, one plan per frame
   with a result and one command per plan. A command carried within 50 ms
   arrives before the next, so the cadence needs no requirement of its own.
6. The stop response gives a deceleration of 4 m/s² with the steering held
   until the run ends, and 0° of steering before any valid command, so the
   actuation ECU needs no vehicle speed; the vehicle model is to keep the
   vehicle at standstill under it.
7. The detection parts are verified by analysis of the realization and of the
   records of the fault runs: a test cannot tell a new check value over
   unchanged parts from the one taken.
8. The run set names every run that the criteria judge: on each route, a run
   without a fault, a run for each of the four command faults on each link,
   with the delay holding the command for 300 ms, and a run for each link that
   goes down. Each run ends 100 ms after the path gives its last command, so
   that the last command can arrive and a run without a fault ends without the
   stop response.
9. The four concerns that are reviewer questions get requirements: the
   topology and the elements of each route in `REQ-EE-001` and `REQ-EE-003`,
   the exchange items in `REQ-EE-007`, and the sequence from a fault to its
   response in `REQ-EE-008` and `REQ-EE-009`.
10. `REQ-EE-002` names the Eclipse S-CORE path, so Phase 9 links it to the
    feature `eclipseSCORE`; the other requirements carry no link of their own.

A comment about `gapEEActuationEnd` records what Phase 5 fixes of that gap and
what stays open, and a comment about `gapEEBenchPlatform` and
`gapEERecordedCommandStream` records what the criteria ask of the testbed.
`tests/test_ee_architecture_requirements.py` pins the requirements, their
derivations, the terms, the two comments and the table. The Phase 5 gates
check that each requirement has a statement, one subject, a derivation from a
need and one verification method. Review judges whether the requirements are
the right ones.

## Functional architecture (Phase 6)

Phase 6 breaks the vehicle network into five functions in
DE4SDV_EEArchitectureFunctionalArchitecture: recordNetworkIdentity,
takeDrivingCommand, carryDrivingCommand, checkDrivingCommand and
applyDrivingCommand. Eight of the ten requirements of Phase 5 are allocated to
them. takeDrivingCommand carries REQ-EE-002; carryDrivingCommand carries
REQ-EE-004, REQ-EE-005 and REQ-EE-007; checkDrivingCommand and
applyDrivingCommand share REQ-EE-006 and REQ-EE-008; applyDrivingCommand
carries REQ-EE-009; and recordNetworkIdentity carries REQ-EE-010. REQ-EE-001
and REQ-EE-003 constrain the structure that realizes the functions, so Phases
7 and 8 carry them by the elements that they place.

The functions do not depend on the route. The stop response is a state of
applyDrivingCommand and leaves on the same output as the applied command, as
the operational context of Phase 2 says: the actuation ECU gives it itself, as
INC-DRIVING-001 does at its own actuation. checkDrivingCommand stands apart
from the application because Phase 5 leaves open which element detects and
rejects a command; Phase 7 gives each function to a logical element.

EEVehicleNetworkSystemProcess runs the network between the parts of the Phase
2 context: the command source, the Eclipse S-CORE path and the vehicle, bound
by reference. Its documentation holds the sequence from a fault to the stop
response, which answers eeNetworkFaultResponseConcern. EEActuationStates holds
the three states of the actuation ECU in a run. The boundary has one input
port, whose item specializes the driving command of the driver-assistance
increment, and one output port, which carries only the steering angle and the
acceleration.

Five views show it: the function breakdown, the requirement by function
matrix, the system process, the state table and the functional interfaces.
Left open for Phases 7 and 8: which element checks a command and where each
element takes the simulation time. Left to Phase 8, which chooses the
technology: how a zone controller repacks the command, whether the command
fits a CAN frame, and the medium of the direct link.

## Logical architecture (Phase 7)

Phase 7 gives the vehicle network three logical elements in
DE4SDV_EEArchitectureLogicalArchitecture. EEVehicleNetworkLogicalSystem
specializes the functional boundary of Phase 6, so it keeps its two ports, and
each of the five functions is allocated to the logical element that carries
it. On 2026-11-26 the owner chose three logical elements for the five
functions: functions share a logical element when nothing requires them to be
separately placeable, and split where a requirement constrains the exchange
between them or demands that one keeps working when the other does not.

- eeIdentityRecorder carries recordNetworkIdentity (REQ-EE-010). The record
  covers the software and the configuration of both other logical elements and
  comes before the first driving command of each run is taken, so it stands
  alone. It exchanges nothing: Phase 6 orders the record by succession, with
  no item.
- eeCommandCarrier carries takeDrivingCommand and carryDrivingCommand
  (REQ-EE-002, REQ-EE-004, REQ-EE-005 and REQ-EE-007). Nothing asks the taking
  and the carrying to be placed apart.
- eeActuationEnd carries checkDrivingCommand and applyDrivingCommand
  (REQ-EE-006, REQ-EE-008 and REQ-EE-009). It keeps working when the carriage
  delivers nothing: by REQ-EE-009 the stop response starts there once more
  than 200 ms of simulation time pass with no valid driving command reaching
  it. So it stands apart from the command carrier. The check stays with the
  application: Phase 5 judges a driving command valid as it reaches the end of
  its route, and both functions share REQ-EE-006 and REQ-EE-008.

The driving command enters by one delegation, to the command carrier, the one
input that REQ-EE-002 keeps; the carried driving commands go from the command
carrier to the actuation end, the one exchange between logical elements, which
REQ-EE-004, REQ-EE-005 and REQ-EE-007 constrain; and the applied command
leaves from the actuation end. REQ-EE-001 and REQ-EE-003 constrain the
topology and the routes, so Phase 8 carries them by the elements that it
places on the routes. Of the two questions that Phase 6 left open, Phase 7
settles which element checks a driving command: the actuation end. Where each
element of the routes takes the simulation time stays with Phase 8.

Three views show it: the logical structure, the function by logical element
matrix and the internal exchange.

## What the framing already records as open

Each point is a gap of the model, in the model's own words.

- **The safety-path architecture** (`gapEESafetyPathArchitecture`). REQ-MW-006
  asks each member product to keep a failure of the non-safety middleware
  integration path from causing an uncontrolled emergency intervention
  command, by a middleware partition with a safety certification or by a
  direct vehicle-command path, and leaves that choice and its containment
  criteria open per GAP-MW-029. That direct path keeps the AEBS emergency
  intervention command around the middleware, from the AEB node to the vehicle
  command gate on the Linux host (ASM-MW-003, ASM-MW-028, REQ-MW-017). It is
  not one of the routes that this increment judges, and this increment does
  not carry that AEBS command. The routes that this increment judges lie after
  the middleware. Whether a verdict on them bears on that choice is open. The
  containment criteria stay open, and this increment makes no
  freedom-from-interference claim.
- **The zone route in vehicles** (`gapEEZoneRouteInVehicles`). The public
  sources in the folder's upstream record describe zone controllers as
  gateways or aggregators of input and output between the central computer and
  the sensors and actuators of their zone. None of them shows a production
  vehicle whose brake command takes a route through a zone controller: one
  plans braking among the systems on the Ethernet backbone of a central
  architecture for 2028, one places the brake actuators apart from the zone
  controllers, and one says that the move of chassis control into the zones
  may need more time. Whether vehicles carry a driving command through a zone
  controller is open. So this increment judges that route and a direct link
  from the central computer, and takes neither as given.
- **The actuation end** (`gapEEActuationEnd`). In the driving benches the
  actuation end is an actuation adapter on the host that runs Eclipse S-CORE.
  The adapter of the closed-loop driving increment applies the stop response
  of REQ-DRIVING-028. The adapter of the driver-assistance increment rejects a
  command whose sequence count, check value or issue time fails, and has no
  stop response. It turns an accepted command into the simulator's control by
  a rule that takes the speed of the ego vehicle from the newest world
  snapshot (MAP-DRIVING-DA-COMMAND). This increment puts the actuation in an
  ECU on CAN. Which element then holds each of these duties, where the
  actuation end takes a vehicle speed if its conversion of the command needs
  one, whether the driving command with its issue time, sequence count and
  check value fits a CAN frame, and whether a zone controller that repacks the
  command from Ethernet to CAN keeps the detection end to end, is open. This
  framing changes neither adapter.
- **The hand-off to the brake ECU** (`gapEEBrakeHandoff`). The AEBS
  realization records the hand-off from the vehicle interface to the brake ECU
  and actuator as an open integration obligation, and deferred the boundary of
  the brake ECU and actuator to INC-AEBS-008. INC-AEBS-008, the AEBS
  simulation deployment, uses a vehicle-dynamics test double and makes no
  brake ECU or actuator claim, so the obligation stays open. This increment
  carries the driving command of the driver-assistance increment to an
  actuation ECU on CAN, not an AEBS command. Whether a result of this
  increment meets that obligation for the AEBS is open, and this increment
  does not decide it.
- **The platform stack and the network boundary**
  (`gapEEStackAndNetworkBoundary`). The platform stack describes one SoC and
  keeps its hardware layer abstract, the execution-environment shared asset
  and its feature model describe one vehicle compute target, with an NXP and
  Zephyr candidate, and VehicleNetworkBoundary of the AAOS SDV middleware
  boundary holds two Ethernet ports and no part. How the vehicle network of
  this increment relates to them is open for Phases 2 and 3. This framing
  changes none of them.
- **The vehicle network's place in the product line**
  (`gapEENetworkInProductLine`). The governed product-line scope has no
  element for the vehicle network. This increment admits no member and changes
  no scope decision. Phase 3 classifies the vehicle network against the scope
  as it then stands.
- **No bench for the vehicle network** (`gapEEBenchPlatform`). No bench of the
  repository runs a vehicle network with zone controllers, a backbone or CAN;
  the driving benches carry the vehicle control and the speed between hosts
  over a bench network. The testbed that stands for the vehicle network in
  this increment is not chosen. Its readiness probe, its cost, its host and
  whether it runs on one host are open.
- **The recorded command stream** (`gapEERecordedCommandStream`). The evidence
  replays a recorded stream of driving commands in the form that the
  driver-assistance increment fixes. Which recording gives that stream, and
  how the stream is bound to the revision that made it, is open.

The sources read for the route through a zone controller, and what each of
them supports, are in the
[upstream record](../../textual-notation-of-model/packages/features/ee/upstream.md#zone-controller-route).

## Boundaries

The vehicle network of one topology is a proposed **System 1** subject: the
network side of the central computer, the Ethernet backbone, two zone
controllers as gateways to CAN, a CAN bus in each zone, a direct link that
passes no zone controller as the other route, and an actuation ECU that
receives the command and acts on it. Two parts of **System 1** are outside its
boundary, and neither is an enabler: the source of the driving command on the
central computer, and the Eclipse S-CORE path that carries the command to the
vehicle network. The software testbed that stands for the vehicle network, its
host, the replay of the command stream, the fault injection, the model of the
vehicle, the records and the evaluators are **System 2** enablers, not vehicle
features. The testbed with its model of the vehicle is the virtual vehicle of
this increment.

The testbed gives functional behavior, not hardware timing: a time that it
measures is the testbed's. It is no safety argument: whether a verdict of this
increment bears on the choice of the safety-path architecture is open, and the
containment criteria and any freedom-from-interference claim stay open.

## Next obligation and execution limits

Use the Method Check of the reviewed pull request to select the next
obligation, not the phase number alone. Phase 3, the capability
classification, records no feature-model delta, and review judges it: its one
blocking check has nothing to evaluate, so the Method Check lists Phase 3 as
vacuous, with a prompt for review. The owner decided on 2026-11-18 to carry
out Phases 1 to 3 of this increment before the baseline of the
driver-assistance increment, whose driving command it carries. After that
baseline, the owner decided on 2026-11-21 to start Phase 4, on 2026-11-22 to
go on with Phase 5, on 2026-11-24 to go on with Phase 6 and on 2026-11-25 to
go on with Phase 7. The next model obligation is **Phase 8**: the E/E and
software realization, which allocates each logical element to a physical
element; its first gate is `logicalElementAllocatedToPhysicalElement`. The
testbed with its readiness probe waits for a further decision of the owner.

The testbed is chosen after a readiness probe. Before a paid cloud run,
refresh the regional price, the capacity and the available credit, obtain the
owner's authorization for the campaign, and verify a bounded shutdown with the
evidence exported first. Starting this increment launches no compute and
authorizes no spend.

## Check the framing change

Run `sysand sync`, `python scripts/check_repo.py`, `python
scripts/smoke_test.py` and `python -m pytest
tests/test_ee_architecture_framing.py
tests/test_ee_architecture_needs_requirements.py
tests/test_ee_architecture_requirements.py
tests/test_ee_architecture_functional_architecture.py
tests/test_ee_architecture_logical_architecture.py -q`. These are
repository and lexical checks, not SysML semantic validation and not runtime
verification. Use `python scripts/validate_sysml.py` where a licensed
validator is available, or request the maintainer-run **Privileged Syside
Validation** on the reviewed head. The framing view and its published diagram
come from that Syside run.
