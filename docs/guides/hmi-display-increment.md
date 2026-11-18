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

**Status: Phase 0 framing proposal.** No implementation, run, result,
product-line admission or compliance is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/hmi/hmi_display_framing.sysml):
  `INC-HMI-001`, its engineering question, charter, scope, assumptions and
  open gaps.
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
- **The HMI display's place in the product line**
  (`gapHmiDisplayInProductLine`). The feature model holds the HMI display as an
  optional feature that requires the AAOS SDV guest, with no binding time
  assigned, and neither governed member selects it.
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
obligation, not the phase number alone. The framing's boundary concern does
not open Phase 1. The next model obligation is **Phase 1 concern framing**: at
least one concern of the engineering scope, held by the parties whose interest
it states. The owner decided on 2026-11-17 that Phase 1 starts after Phase 10 of
the driver-assistance increment, and that the readiness probe of the high
availability renderer runs when the build host is free, with its cost put to
him first.

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
