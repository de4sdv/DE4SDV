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

**Status: Phase 0 framing, Phase 1 concerns and Phase 2 operational context,
proposal.** No implementation, run, result, product-line admission or
compliance is claimed.

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

The increment builds on the
[driver-assistance increment](driver-assistance-increment.md): its driving
command, whose form and cadence that increment fixes at its baseline. It takes
the driving command as that increment fixes it and changes none of its
criteria or verdicts. The stop response on lost commands comes from the
[closed-loop driving increment](closed-loop-driving-increment.md), and the
safety path from the
[middleware requirements](../../textual-notation-of-model/packages/features/middleware/middleware_requirements.sysml).
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
form of the command. The form and the cadence of the command are those that
the driver-assistance increment fixes at its baseline
(`asmEECommandFromDrivingBaseline`).

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
obligation, not the phase number alone. The next model obligation is **Phase
3**, the capability classification: the feature-model delta of this increment,
which review judges. With an empty delta the one blocking check of Phase 3 has
nothing to evaluate, so the Method Check names its next obligation in Phase 4
and lists Phase 3 as vacuous, with a prompt for review. The owner decided on
2026-11-18 to carry out Phases 1 to 3 of this increment before the baseline of
the driver-assistance increment, whose driving command it carries. Phase 4
onward and the testbed with its readiness probe wait for that baseline and for
a further decision of the owner.

The testbed is chosen after a readiness probe. Before a paid cloud run,
refresh the regional price, the capacity and the available credit, obtain the
owner's authorization for the campaign, and verify a bounded shutdown with the
evidence exported first. Starting this increment launches no compute and
authorizes no spend.

## Check the framing change

Run `sysand sync`, `python scripts/check_repo.py`,
`python scripts/smoke_test.py` and
`python -m pytest tests/test_ee_architecture_framing.py -q`. These are
repository and lexical checks, not SysML semantic validation and not runtime
verification. Use `python scripts/validate_sysml.py` where a licensed
validator is available, or request the maintainer-run **Privileged Syside
Validation** on the reviewed head. The framing view and its published diagram
come from that Syside run.
