# Closed-loop driving increment

DE4SDV needs to distinguish a driving function that actually influences vehicle
behavior from a prediction overlay on a separately driven car. This increment
proposes the former: real camera-based learned planning, a functional S-CORE
integration path, and an AAOS SDV application showing genuine plan/state/health.

**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context,
Phase 3 capability classification and Phase 4 stakeholder needs,
proposal.** No implementation, successful driving run, performance result or
product-line admission is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_framing.sysml):
  `INC-DRIVING-001`, its engineering question, charter, scope and open gaps.
- [SysML operational context](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_operational_context.sysml):
  the Phase 2 context, operational behavior and story.
- [SysML capability classification](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_capability_classification.sysml):
  the Phase 3 feature candidate and the scope decisions it needs.
- [SysML needs and requirements](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_needs_requirements.sysml):
  the Phase 4 stakeholder needs and their planned reviews.
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
capture continuity need separate evidence. Phase 5 must fix scenario, resolution,
duration, windows, drop tolerance and freshness/control deadlines before testing.

The released checkpoint must be evaluated with its compatible geometry and
history. Fast synthetic-input results do not prove its performance. Neither
interface compatibility nor recorded-input inference proves useful closed-loop
driving on CARLA imagery. Invalid, lost or stale plans require a defined
stop/disable response in simulation and retained failure-path evidence.

## Concerns (Phase 1)

Each in-scope item leads to the reviewer questions it raises; two items raise
two questions each, with different stakeholders (owner decision of
2026-11-02). Each concern is typed by the SAF concern that asks its question,
so its domain says which later view answers it. The framing viewpoint frames
all six until those views exist.

- **Learned driving:** `checkpointCommandAuthorityConcern`, the checkpoint's
  plan determines the commands with nothing in between. Physical functional
  mapping; systems engineer, verification engineer, reviewer.
- **Integration and observation:** `scoreCommandPathConcern`, plan and command
  items pass through S-CORE, not beside it. Physical internal exchange; system
  architect, software developer, maintainer.
- **Integration and observation:** `aaosObservationFidelityConcern`, AAOS shows
  the live plan, state and health. Physical context exchange, because Phase 2
  keeps AAOS SDV in the context; verification engineer, reviewer.
- **Feedback and timing:** `degradedInputBehaviorConcern`, a defined response
  to invalid, lost or stale input or plan. Functional behavior; safety expert,
  system architect.
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

Eight needs, `NEED-DRIVING-001` to `NEED-DRIVING-008`, take the candidate
driving system as subject. Each is elaborated from one non-boundary Phase 1
concern and is held by stakeholders of that concern:

- **Checkpoint command authority:** the checkpoint's plans move the vehicle
  (001); it plans from the inputs its runtime contract fixes, which are
  calibrated camera images, the ego-motion history, and the map and route
  (002).
- **S-CORE command path:** plans and commands pass through S-CORE (003).
- **AAOS observation fidelity:** the loop publishes its live state with
  producer and time (004), and runs unchanged when AAOS SDV is down or late
  (005).
- **Degraded input behavior:** a defined stop or disable response to degraded
  camera images, motion, route or plans (006).
- **Time-domain honesty:** inputs, plans and commands carry their times (007).
- **Reproducible evidence:** each run identifies its checkpoint and
  configuration (008).

Each need has its own planned stakeholder review, `SC-DRIVING-005` to
`SC-DRIVING-012`, watching a Phase 2 scenario. The limits and the deadlines
come with the requirements in Phase 5. No need covers driving quality: the
charter scopes checkpoint authority, and poor driving is a hold or redirect
condition of the performance gap. The Phase 4 gates check that each need has
a statement, a stakeholder, a source, a rationale and a planned review;
review judges whether the needs are the right ones.

## Next obligation and execution limits

Use the reviewed revision's **Method Check** export to identify the first
unmet model-content obligation; it is not proof that earlier engineering
work is complete. The next work is **Phase 5**: the requirements derived
from the needs, each with a verification method and success criteria; its
first gate is `requirementHasStatement`.
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
`tests/test_closed_loop_driving_needs.py` and
`tests/test_check_naming.py`.
These are repository/lexical checks, not SysML semantic or runtime verification.
Use `python scripts/validate_sysml.py` when a supported licensed validator is
available, or request maintainer-run **Privileged Syside Validation** on the
reviewed head. The views and their published artifacts must come from that
Syside run; no hand-drawn substitute establishes model validation.
