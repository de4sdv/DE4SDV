# HMI display increment

By the owner's decision of 2026-11-13
([ADR 0026](../architecture-decisions/0026-hmi-display-in-every-member-product.md))
every member product of the line is to get an HMI display, and what it shows is
still open. A driver who lets a driving application steer and brake can see on
such a display what the application perceives. The same display gives the speed
and the collision warning. AAOS SDV has a renderer for the elements that have
to be present quickly after a cold boot and while Android is unavailable, and
the owner decided on 2026-11-17 to use it for the speed and the warning. This
increment asks whether the HMI display of the VisionPilot configuration can do
both, and holds what it shows against what the application gives.

**Status: Phase 0 framing, Phase 1 concerns and Phase 2 operational context,
proposal.** No implementation, run, result, product-line admission or
compliance is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/hmi/hmi_display_framing.sysml):
  `INC-HMI-001`, its engineering question, charter, scope, assumptions,
  open gaps and Phase 1 concerns.
- [SysML operational context](../../textual-notation-of-model/packages/features/hmi/hmi_display_operational_context.sysml):
  the Phase 2 context of the HMI display and its story of six scenarios.
- [Syside framing review view](../../textual-notation-of-model/packages/features/hmi/VIEWS.md):
  the generated model review artifact, not a runtime architecture claim.
- [Upstream provenance](../../textual-notation-of-model/packages/features/hmi/upstream.md)
  of the high availability renderer and of the scene of VisionPilot, and the
  [questions for the maintainers](../../textual-notation-of-model/packages/features/hmi/upstream.md#questions-requiring-upstream-engagement).

Orkun Yilmaz owns the increment. One identity covers phases 0 to 11.
Closed-loop verification belongs to Phase 10 of this increment. A readiness
probe comes before the architecture rests on what it tests.

The increment builds on the
[driver-assistance increment](driver-assistance-increment.md): its bench, its
scenarios, its candidate application and its warning request. It takes the
warning request as that increment defines it and changes none of its criteria
or verdicts.

## The engineering question

> Can the HMI display of the VisionPilot configuration show the driver the
> scene that the candidate application perceives, its lane, the path it fits to
> its lane and the objects it detects, together with the speed and the
> collision warning, with the speed and the warning drawn by the high
> availability renderer of AAOS SDV in an SDV Media VM, which also sounds the
> warning, so that the speed and the warning, or the fact that the warning is
> unavailable, stay apparent and correct while Android in the IVI VM hangs,
> boots or restarts? A verdict for each requirement and scenario answers this,
> holding what the display shows against what the candidate gives and when. A
> recording of a display that looks right does not.

The increment supports one decision: which content of the display becomes
common to the member products and which derives from a member's driving
application, and whether the high availability renderer or an app in the IVI
VM draws the common content where a member has an AAOS SDV guest. A fail is a
result to record. It is no reason to change a scenario or a criterion until the
display passes.

## What the increment judges

| In scope | Out of scope |
|---|---|
| The scene as the candidate builds it from its own perception: its lane, the path it fits to that lane, the objects it detects, and the closest object in its path with the distance that its fusion gives. | Objects that the candidate does not give: the simulator's own record of the scene, and any estimate of objects that the display would make itself. |
| The vehicle speed that the candidate is given. | How well the candidate perceives: whether it finds an object, and how far its positions and its distances are from the simulator's. The display shows what the candidate gives, right or wrong. |
| The collision warning on the display and as a sound, when the candidate's warning request asks for it and within the time that the driver-assistance increment allots from the request to each mode. | The scenes of other driving applications, those of the Autoware-based members and of the closed-loop driving increment among them, and adapters that would bring them to the display. |
| Which elements the high availability renderer in an SDV Media VM draws and which an app in the IVI VM draws, and the paths that bring their inputs from the SDV Core VM. | Driver interaction: engagement, override, driving modes and controls on the display. |
| What the display shows while the app that draws the scene hangs or ends, and while Android in the IVI VM hangs, boots or restarts: the speed and the warning, or the fact that the warning is unavailable. | Gear, set speed, speed limit and the other telltales, unless a need of Phase 4 asks for one; media, navigation, maps, telephony and camera views. |
| What the display shows when an input is late or missing, so that no element is shown as current when it is not. | How a driver perceives and reads the display, with glance time, comprehension and distraction, and the display's visual design. |
| A pass or a fail for each requirement and scenario, bound to the candidate revision, the display build and the configuration that ran. | Changing what the candidate perceives, plans, requests or commands, its camera geometry included, and the criteria and the verdicts of the driver-assistance increment. |
| | The display of a member product without an AAOS SDV guest, the Linux-side display of the standalone member among them. |
| | On-road operation, production readiness, a safety approval of the display or of the renderer's monitor, compliance, type approval or certification. |

The scope is one configuration and at most ten requirements. Phase 5 derives
those requirements from the needs of Phase 4 and from the product line's
requirements on the collision warning and on the indication of the AEBS status
in the
[AEBS requirements](../../textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml).

## Concerns (Phase 1)

A verdict is only useful if it answers the questions of the people who rely on
it. Phase 1 names those questions: one concern per question of the in-scope
items, held by the parties whose interest it states. The driver, a vehicle
occupant, holds the operational concern beside the engineering roles. Each
concern is typed by the SAF concern that asks its question, the product-line
question by the method's classification concern, and its text names the view
of a later phase that answers it. The framing viewpoint frames all nine, and a
view of a later phase that answers a concern frames it as well.

- **What the driver sees:** `hmiDriverSupervisionConcern`. What the driving
  application perceives, its lane, the path it fits to that lane and the
  objects it detects, beside the speed; the collision warning on the display
  and as a sound; and the speed and the warning, or the fact that the warning
  is unavailable, also while Android in the IVI VM hangs, boots or restarts. No
  human-factors, safety or on-road claim follows from it. Operational
  capability; vehicle occupants. Answered by the operational story of Phase 2.
- **What the display takes in:** `hmiDisplayInputsConcern`. The items that
  cross into the display: the candidate's lane, its path, its detections with
  their level relative to the path, the closest object with its fused distance
  and speed, the vehicle speed, and the candidate's warning request, each as
  its source gives it. The display takes no object that the candidate does not
  give: neither the simulator's own record of the scene nor an estimate of its
  own. System context exchange; systems engineers and safety experts. Answered
  by the system process of Phase 6.
- **Common or derived content:** `hmiContentVarianceConcern`. Which content of
  the display is common to the member products and which derives from a
  member's driving application. The scenes of the other driving applications
  are out of scope. Product-line capability classification; product-line
  engineers. Answered by the product-line classification view of Phase 3.
- **The warning's sequence:** `hmiWarningSequenceConcern`. The sequence from
  the warning request to the warning on the display and to its sound, and the
  time of each step within the time that the driver-assistance increment
  allots, independent of the elements that realize it. The warning request is
  taken as the driver-assistance increment defines it. System process; safety
  experts and systems engineers. Answered by the system process of Phase 6.
- **Late and missing content:** `hmiContentCurrencyConcern`. The states of each
  element, current, late or missing, and of the warning, unavailable, and what
  the display shows in each. No element is shown as current when it is not:
  late data is never shown as live. System state; safety experts and
  verification engineers. Answered by the system state of Phase 6.
- **Outages of the scene's drawing:** `hmiAndroidOutageConcern`. The sequence
  from a hang or an end of the drawing of the scene, and from the environment
  that hosts it hanging, booting or restarting, to its detection and to what
  the display shows then: the speed and the warning, or the fact that the
  warning is unavailable. Phase 6 treats each outage as an event of an element
  inside the display's boundary. It rests on N-AEBS-008 and REQ-AEBS-013. No
  safety argument follows from it. System process; safety experts and systems
  engineers. Answered by the system process of Phase 6.
- **Which renderer draws what:** `hmiRendererAllocationConcern`. The high
  availability renderer draws the speed, the warning and its sound, and an app
  in the IVI VM the scene. The split rests on what the driver sees while
  Android in the IVI VM hangs, boots or restarts, not on an end of the app that
  draws the scene. Drawing an element with the renderer is no safety approval
  of that element. Physical functional mapping; product-line engineers and
  safety experts. Answered by the physical-logical mapping of Phase 8.
- **The paths to the renderers:** `hmiRendererPathConcern`. Which elements
  exchange each input on its way from the SDV Core VM to the renderer in the
  SDV Media VM and to the app in the IVI VM, and how that app tells the
  renderer that Android is alive. Physical internal exchange; system architects
  and systems engineers. Answered by the view of the claimed path in Phase 8.
- **Verdicts:** `hmiDisplayVerdictConcern`. A pass or a fail for each
  requirement and scenario, bound to the candidate revision, the display build
  and the configuration that ran. A recording of a display that looks right is
  no verdict. Argumentation assurance; product-line engineers and verification
  engineers. Answered by the argumentation assurance view of Phase 10.

The Phase 1 gates check that each concern has native stakeholders and a frame,
and that one concern is not the boundary concern. They do not judge whether
the stakeholder, risk and viewpoint coverage is adequate; review does.

## Operational context and story (Phase 2)

Phase 2 draws the boundary that Phase 0 states and does not move it. One
operational context holds the HMI display as a black box: what it shows and
where, the app in the IVI VM that draws the scene, the high availability
renderer in an SDV Media VM, and the paths from the SDV Core VM to both. Around
it: the candidate application of the driver-assistance increment, which gives
its scene and its warning request; the Eclipse S-CORE path, which carries the
warning request; the vehicle, which gives its speed; and the driver, who only
receives. Nothing flows back to the candidate. The road, the vehicle targets
and the simulator reach the display only as the candidate perceives them, so
the context draws no part for them. The AAOS SDV guest lies across the
boundary, so the context draws no part for it either, and an outage of Android
in the IVI VM is an event inside the black box. CARLA, the cloud hosts, the
scenario runner, the means that make Android in the IVI VM hang, end and
restart, the record of what the candidate gives, the captures, the evaluators
and the recordings stay in `hmiDisplayVerificationEnvironment`.

The context reuses the elements of the driver-assistance increment by
reference: it types its parts and items with `DriverAssistanceSystem`,
`SCORECommandAndWarningPath`, `VehicleSpeed`, `WarningRequest` and
`CollisionWarning`, each imported singly, and declares only the scene
(`PerceivedScene`) and what the display shows (`HmiDisplayContent`). Phase 2
places the source of the vehicle speed at the vehicle; which element of
System 1 carries it to the SDV Core VM, and on which path the scene leaves the
candidate's process (`gapHmiSceneOutput`), stay open.

The story holds six scenarios. Two are the scenarios of the driver-assistance
increment as the driver sees them on the display, each tied to them by a
dependency and none restating them: `SC-HMI-001` the warning scenarios
`SC-DRIVING-012` and `SC-DRIVING-013`, with the scene, the speed and the
collision warning on the display and as a sound, and `SC-HMI-002` the
no-reaction scenarios `SC-DRIVING-014` and `SC-DRIVING-015`, with the scene and
the speed and no warning. Four add an outage in the IVI VM to them:
`SC-HMI-003` the app that draws the scene ends or hangs, `SC-HMI-004` Android
in the IVI VM boots, `SC-HMI-005` it hangs with its last frame on the display,
and `SC-HMI-006` it restarts. In each the driver sees the speed and the
warning, or the fact that the warning is unavailable, and the display shows no
element as current when it is not. The display shows what the candidate
perceives, never the simulator's record of the scene. The story states the aim
of the engineering question; whether the display achieves it is the verdict of
Phase 10. The criteria, the age from which an element counts as late and how
the time that the driver-assistance increment allots from the warning request
to each mode divides (`gapHmiWarningPresentation`) are fixed with the
requirements in Phase 5. No human-factors, timing, safety or compliance claim
is made.

The context view frames `hmiDisplayContextConcern`. The story view frames
`hmiDisplayStoryConcern` and the Phase 1 concern `hmiDriverSupervisionConcern`,
which the story answers.

## What the framing already records as open

Each point is a gap of the model, in the model's own words.

- **No scene output** (`gapHmiSceneOutput`). At the inspected revision the
  candidate builds a top-down scene of its lane, its path and its detections
  only inside its own visualization, and only when that visualization is built
  with it, which upstream's build does not do by default. The configuration
  that the driver-assistance increment realizes for the candidate keeps the
  visualization in the candidate's loop off. That increment's visualization
  recorder, an observer of System 2 in the candidate's process, draws
  upstream's visualization into the bench's recording only, from a copy that a
  second hand-off in the loop gives it.
- **What the scene can carry** (`gapHmiSceneContent`). The candidate's
  detections carry a level of their place relative to its path, such as in its
  lane or in the next, not a type of object.
- **No collision warning in the renderer** (`gapHmiRendererCollisionWarning`).
  The vehicle data of the high availability renderer holds the vehicle speed
  but no collision warning.
- **The renderer on the bench** (`gapHmiRendererIntegration`). No high
  availability renderer has run on the DE4SDV bench.
- **Two presentations of the warning** (`gapHmiWarningPresentation`). The
  driver-assistance increment realizes the collision warning with an app in the
  IVI VM, a build item of its bench, and allots 0.1 s of the 0.2 s from the
  warning request to each mode to the path to that app and 0.1 s to the app.
  Its realization records the high availability renderer for that warning as an
  alternative that the owner did not select for it on 2026-11-17
  (ALT-DRIVING-HARWARNING-001). Whether a build of this display replaces that
  app in the VisionPilot configuration, and how the 0.2 s divides on a path to
  the SDV Media VM, is open.
- **No indication that the warning is unavailable**
  (`gapHmiWarningAvailability`). At the inspected revision the candidate gives
  no indication that its warning is unavailable, and the driver-assistance
  increment leaves the failure and unavailability signals of the warning out
  of its scope.
- **The guest layout of the members** (`gapHmiMemberGuestLayout`). ADR 0025
  gives the S-CORE-integrated member of ADR 0023 a guest partition of two VMs,
  an SDV Core VM and an IVI VM that runs the HMI application, and the Eclipse
  S-CORE middleware increment assumes that this HMI application is an
  informational display, not the AEBS driver warning (ASM-MW-024). A renderer
  in an SDV Media VM adds a third VM to the guest.
- **No Linux-side display** (`gapHmiStandaloneLinuxDisplay`). The standalone
  member selects the HMI display, common content of every member product (ADR
  0026). It has no AAOS SDV guest, so its display is a Linux-side display, and
  no such display exists: no shared asset implements one, and the standalone
  member selects a display that has no realization.
- **A headless guest with a display** (`gapHmiAAOSIntegratedGuestDisplay`).
  The AAOS-integrated member, MW-CONFIG-001, selects the HMI display, which it
  holds in its AAOS SDV guest (ADR 0026). Its configured member models a
  headless guest: its guest middleware is a headless SDV Core boundary, and
  its retained evidence names the headless sdv_core_cf image. Its guest now
  needs a display.
- **The HMI display's place in the product line**
  (`gapHmiDisplayInProductLine`). The governed scope holds the HMI display as
  common content of every planned member, bound during Development, and every
  member configuration selects the feature hmiDisplay, which corresponds to
  that common content. Where the display runs follows the integration mode: in
  the AAOS SDV guest of the two integrated members, and on the Linux side of
  the standalone member. No shared asset implements the display yet, and what
  it shows in each member is open. The owner decided on 2026-11-21 that this
  increment records the two gaps that the scope revision leaves in the members
  (gapHmiStandaloneLinuxDisplay, gapHmiAAOSIntegratedGuestDisplay).
- **No upstream contact** (`gapHmiUpstreamContact`). The maintainers of the
  display safety of AAOS SDV and of the candidate application are not yet
  involved.

The gaps of the scene rest on the
[VisionPilot section](../../textual-notation-of-model/packages/features/hmi/upstream.md#visionpilot-scene)
of the upstream record, and those of the renderer on its
[renderer section](../../textual-notation-of-model/packages/features/hmi/upstream.md#high-availability-renderer).

## Boundaries

The HMI display of the VisionPilot configuration is a proposed **System 1**
subject: what it shows and where, the app in the IVI VM that draws the scene,
the high availability renderer in an SDV Media VM that draws the speed and the
warning and gives the warning's sound, and the paths from the SDV Core VM to
both. Two parts of **System 1** are outside its boundary, and neither is an
enabler: the candidate application, which perceives, plans and requests the
warning, and the Eclipse S-CORE path that carries its outputs to the SDV Core
VM. Which part of System 1 brings the vehicle speed to the SDV Core VM is for
Phases 2 and 3 to place. CARLA, the cloud hosts, the scenario runner, the means that make Android in
the IVI VM hang, end and restart, the record of what the candidate gives, the
capture of the display and of the sound, the evaluators and the recordings are
**System 2** enablers, not vehicle features. The capture observes the AAOS SDV
and is no part of it.

The renderer's drawing of the speed and the warning is examined as behavior on
the bench. It is no safety claim: the documentation calls the renderer a
quality management process, the reference safety monitor of AAOS SDV carries no
ASIL certification, and this increment certifies nothing.

## Next obligation and execution limits

Use the Method Check of the reviewed pull request to select the next
obligation, not the phase number alone. The next model obligation is **Phase
3**, the capability classification, which review judges: which content of the
display is common to the member products and which derives from a member's
driving application. With no characteristic recorded, the one blocking check of
Phase 3 has nothing to evaluate, so the Method Check lists Phase 3 as vacuous
and names its next obligation in Phase 4. On 2026-11-21 the owner decided that
the increment goes on without waiting for Phase 10 of the driver-assistance
increment. Phase 3 and later phases waited for the revision of the governed
scope, which the model now holds, so they go on. On 2026-11-17 the owner
decided that the readiness probe of the high availability renderer runs with
its cost put to him first.

Involve the upstream maintainers before deep adoption, and show them a result
about their project before it is published. Before a paid cloud run, refresh
the regional price, the capacity and the available credit, obtain the owner's
authorization for the campaign, and verify a bounded shutdown with the
evidence exported first. Starting this increment launches no compute and
authorizes no spend.

## Check the framing change

Run `sysand sync`, `python scripts/check_repo.py`,
`python scripts/smoke_test.py` and
`python -m pytest tests/test_hmi_display_framing.py -q`. These are repository
and lexical checks, not SysML semantic validation and not runtime
verification. Use `python scripts/validate_sysml.py` where a licensed
validator is available, or request the maintainer-run **Privileged Syside
Validation** on the reviewed head. The framing view and its published diagram
come from that Syside run.
