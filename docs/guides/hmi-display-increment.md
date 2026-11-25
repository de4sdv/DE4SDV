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

**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase
3 capability classification, Phase 4 stakeholder needs, Phase 5 requirements,
Phase 6 functional architecture and Phase 7 logical architecture, proposal.**
No implementation, run, result, product-line admission or compliance is
claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/hmi/hmi_display_framing.sysml):
  `INC-HMI-001`, its engineering question, charter, scope, assumptions,
  open gaps and Phase 1 concerns.
- [SysML operational context](../../textual-notation-of-model/packages/features/hmi/hmi_display_operational_context.sysml):
  the Phase 2 context of the HMI display and its story of seven scenarios.
- [SysML capability classification](../../textual-notation-of-model/packages/features/hmi/hmi_display_capability_classification.sysml):
  the Phase 3 classification of the display's content, which records no
  feature-model delta.
- [SysML stakeholder needs](../../textual-notation-of-model/packages/features/hmi/hmi_display_needs_requirements.sysml):
  the Phase 4 needs of the HMI display and their planned reviews.
- [SysML requirements](../../textual-notation-of-model/packages/features/hmi/hmi_display_needs_requirements.sysml):
  the Phase 5 requirements of the HMI display.
- [SysML functional architecture](../../textual-notation-of-model/packages/features/hmi/hmi_display_functional_architecture.sysml):
  the Phase 6 functional architecture of the HMI display.
- [SysML logical architecture](../../textual-notation-of-model/packages/features/hmi/hmi_display_logical_architecture.sysml):
  the Phase 7 logical architecture of the HMI display.
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
of a later phase that answers it, save the product-line question: Phase 3
records no characteristic and has no view. The framing viewpoint frames all
nine, and a view of a later phase that answers a concern frames it as well.

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
  engineers. The framing view frames it. Phase 3 gives each content item its
  reason in its classification and records no characteristic, since the
  increment adds none that tells the member products apart, so Phase 3 has
  no view; which content becomes common is for the lifecycle decision.
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

The story holds seven scenarios. Two are the scenarios of the driver-assistance
increment as the driver sees them on the display, each tied to them by a
dependency and none restating them: `SC-HMI-001` the warning scenarios
`SC-DRIVING-012` and `SC-DRIVING-013`, with the scene, the speed and the
collision warning on the display and as a sound, and `SC-HMI-002` the
no-reaction scenarios `SC-DRIVING-014` and `SC-DRIVING-015`, with the scene and
the speed and no warning. Four add an outage in the IVI VM to them:
`SC-HMI-003` the app that draws the scene ends or hangs, `SC-HMI-004` Android
in the IVI VM boots, `SC-HMI-005` it hangs with its last frame on the display,
and `SC-HMI-006` it restarts. One adds a missing input: in `SC-HMI-007` the
warning request stops reaching the display during the further run of
`SC-DRIVING-012` that stops the Eclipse S-CORE path, which the stop-run
decision of 2026-11-18 of the driver-assistance increment names, and the
display shows that the warning is unavailable. In each the driver sees the
speed and the warning, or the fact that the warning is unavailable, and the
display shows no element as current when it is not. The display shows what the
candidate perceives, never the simulator's record of the scene. The story
states the aim of the engineering question; whether the display achieves it is
the verdict of Phase 10. The criteria, the age from which an element counts as
late and how the time that the driver-assistance increment allots from the
warning request to each mode divides (`gapHmiWarningPresentation`) are fixed
with the requirements in Phase 5. No human-factors, timing, safety or
compliance claim is made.

Two corrections of Phase 2 come with Phase 4. On 2026-11-22 the owner decided
that the story gains `SC-HMI-007`: the missing-request decision of 2026-11-22.
On 2026-11-22 the owner decided that the scene carries its time, as the vehicle
speed and the warning request carry theirs: the scene-time decision of
2026-11-22.

The context view frames `hmiDisplayContextConcern`. The story view frames
`hmiDisplayStoryConcern` and the Phase 1 concern `hmiDriverSupervisionConcern`,
which the story answers.

## Capability classification (Phase 3)

The increment adds no characteristic that distinguishes member products. Its
[capability classification](../../textual-notation-of-model/packages/features/hmi/hmi_display_capability_classification.sysml)
records no feature candidate and no deferred scope. Core elements are common
by default and get no record.

- **The display itself:** common content of every member (ADR 0026) and no
  selectable feature for members. In the feature model `hmiDisplay` is
  optional, so that configurations which are not members can leave it out
  (validity), and it corresponds to that common content (admission).
- **Where it runs:** derived from the integration mode, in the AAOS SDV guest
  of an integrated member or on the Linux side of the standalone member. The
  guest is the feature candidate `hmiGuestExecutionDomain` of the Eclipse
  S-CORE middleware increment.
- **The scene:** VisionPilot's own, so it comes with the vehicle application,
  a feature of the feature model. The display of this increment belongs to the
  VisionPilot configuration, which is not a member product.
- **The speed, the warning and its sound:** no member differs by them. The
  collision warning and the indication that it is unavailable rest on
  REQ-AEBS-002, N-AEBS-008 and REQ-AEBS-013 of the product line, and neither
  the feature model nor the governed scope holds a warning mode.
- **Behavior, realization and evidence:** late content and the outages of
  Android are behavior for Phases 5 and 6; which renderer draws what, the VMs
  of the guest and the displays of the members are realization; the verdicts
  are System 2. None of them is a feature.
- **Scope decisions** (`gapHmiDisplayInProductLine`): whether the scene of
  each member's driving application and the speed become common content of
  the display; whether the warning and the indication that it is unavailable
  become content of the display of every member, a question that belongs to
  the AEBS requirements and architecture; whether the acoustic warning
  becomes common content of the driver warning; and whether the high
  availability renderer or an app in the IVI VM draws the common content
  where a member has an AAOS SDV guest, are open for the lifecycle decision.
  This increment admits nothing.

The one blocking check of Phase 3 evaluates the characteristics recorded, and
this phase records none, so the Method Check reports Phase 3 as having nothing
to evaluate. Review judges the classification.

## Stakeholder needs (Phase 4)

The
[stakeholder needs](../../textual-notation-of-model/packages/features/hmi/hmi_display_needs_requirements.sysml)
say what the parties of the Phase 1 concerns expect of the HMI display. Each
need is held by the parties it serves and leads its source with the concern it
comes from. Each has one planned stakeholder review on the Phase 2 scenarios it
covers, carried out by the roles that check the answer.

- `NEED-HMI-001`: the display shows the driver the scene as the
  driver-assistance system gives it from its own perception, with the
  object that the system acts on marked. Vehicle occupants. Reviewed by
  `SC-HMI-008` on `SC-HMI-001` and `SC-HMI-002`.
- `NEED-HMI-002`: the display shows the driver the vehicle speed that the
  driver-assistance system is given. Vehicle occupants. Reviewed by
  `SC-HMI-009` on `SC-HMI-001` and `SC-HMI-002`.
- `NEED-HMI-003`: the display gives the collision warning on the display and as
  a sound when the warning request asks for it, and none without a request.
  Vehicle occupants. Reviewed by `SC-HMI-010` on `SC-HMI-001` and `SC-HMI-002`.
- `NEED-HMI-004`: the speed and the warning, or, when the warning cannot be
  given, the fact that it is unavailable, stay on the display while the app
  that draws the scene or Android in the IVI VM is out. Vehicle occupants.
  Reviewed by `SC-HMI-011` on `SC-HMI-003` to `SC-HMI-006`.
- `NEED-HMI-005`: the display shows no element as current when it is not, and
  shows when the collision warning is unavailable. Vehicle occupants. Reviewed
  by `SC-HMI-012` on `SC-HMI-003` to `SC-HMI-007`.
- `NEED-HMI-006`: each run identifies the build and the configuration of the
  display that ran. Verification engineers and product-line engineers, who use
  the run identity in their own work. Reviewed by `SC-HMI-013` on all seven
  scenarios.

On 2026-11-22 the owner decided that the display shows what the
driver-assistance system perceives, right or wrong, with the object that the
system acts on marked, and not only what reaches the control of the vehicle:
the display-rule decision of 2026-11-22. `NEED-HMI-001` and `SC-HMI-008` carry
it.

Seven concerns get no need of their own: the items that cross into the display,
its common content, the warning's sequence, the outages of the scene's drawing,
which renderer draws what, the paths to the renderers, and the late and missing
content. Their roles check the answer rather than use it, as in the stakeholder
needs of the driver-assistance and the E/E architecture increments, so each is
a question for a planned review: `NEED-HMI-001` names the first two in its
source and `SC-HMI-008` asks them, `NEED-HMI-003` names the third and
`SC-HMI-010` asks it, `NEED-HMI-004` names the next three and `SC-HMI-011` asks
them, and `NEED-HMI-005` names the last and `SC-HMI-012` asks it.

No need states a number or names a drawing: Phase 5 derives the requirements
and their limits, how the app in the IVI VM draws the scene is a choice of
Phase 8, and no need asks for gear, set speed, speed limit or another telltale.
Phase 5 states in its requirements what the scene of the pinned
driver-assistance system carries and what the warning request asks for and
carries.

`SC-DRIVING-018` of the driver-assistance increment watches the collision
warning in `SC-DRIVING-012` and `SC-DRIVING-013`, which `SC-HMI-010` watches
too, for another subject: its need, `NEED-DRIVING-010`, asks the candidate to
give the warning request, and `NEED-HMI-003` asks the display to give the
warning from it.

`tests/test_hmi_display_needs_requirements.py` pins the needs, their holders
and sources, the planned reviews and their scenarios, and the wording a need
may not use. The Phase 4 gates check that each need has a statement, a
stakeholder, a source, a rationale and a planned review. Review judges whether
the needs are the right ones.

## Requirements (Phase 5)

The
[requirements](../../textual-notation-of-model/packages/features/hmi/hmi_display_needs_requirements.sysml)
state what the HMI display shall do and how each is verified. There are ten,
the cap of the scope. Each has one subject, the HMI display, derives from one
need, and has one verification method and its success criteria. They derive
from the Phase 4 needs and rest on `REQ-AEBS-002` and `REQ-AEBS-013`. Eight are
functional; Phase 6 allocates each of those to a function.

- `REQ-HMI-001` `reqShowTheSceneAsGiven`, from `NEED-HMI-001`, functional,
  test: shows each scene that reaches it, or a newer one, within the
  presentation time and as the driver-assistance system gives it, apart from
  the outages in the IVI VM.
- `REQ-HMI-002` `reqMarkTheObjectTheSystemActsOn`, from `NEED-HMI-001`,
  functional, test: shows the object that the system acts on, and no other,
  apart from the objects of the scene, with its distance to the whole metre and
  its speed to the whole km/h.
- `REQ-HMI-003` `reqShowTheVehicleSpeed`, from `NEED-HMI-002`, functional,
  test: shows each vehicle speed, or a newer one, within the presentation time,
  to the whole km/h.
- `REQ-HMI-004` `reqCollisionWarningWhileRequested`, from `NEED-HMI-003`,
  functional, test: gives the collision warning on the display and as a sound
  while, and only while, the warning request asks for it.
- `REQ-HMI-005` `reqStartEachWarningModeWithinLimit`, from `NEED-HMI-003`, a
  performance requirement, test: starts each mode within 0.1 s of wall-clock
  time after the start of a request reaches the display.
- `REQ-HMI-006` `reqShowOutdatedElementsAsOutdated`, from `NEED-HMI-005`,
  functional, test: shows each element as outdated while, and only while, it is
  outdated.
- `REQ-HMI-007` `reqShowWarningUnavailableWhileRequestOutdated`, from
  `NEED-HMI-005`, functional, test: shows that the collision warning is
  unavailable while, and only while, the warning request is outdated; the one
  degraded response of the set.
- `REQ-HMI-008` `reqSpeedAndWarningThroughOutages`, from `NEED-HMI-004`,
  functional, test: keeps the speed, the warning and its unavailability
  throughout each outage in the IVI VM.
- `REQ-HMI-009` `reqRendererSplitAndInputPaths`, from `NEED-HMI-004`, a design
  constraint, inspect: the speed, the warning and its sound by the high
  availability renderer in an SDV Media VM, the scene by an app in the IVI VM,
  and their paths from the SDV Core VM inside the display.
- `REQ-HMI-010` `reqRecordDisplayIdentity`, from `NEED-HMI-006`, functional,
  test: records the display identity before its first frame on the display in
  each run.

A comment of terms defines each word that a statement uses, among them the
scene, the object that the system acts on, the warning request, the
presentation time, current and outdated, the outage in the IVI VM and the
display identity. Each time limit names simulation time or wall-clock time and
makes no timing claim for a vehicle.

The Phase 5 decisions, each with its reason in the rationale of the requirement
that it shapes:

1. The speed of the closest object is shown as the fusion of the
   driver-assistance system gives it, with the sign that the fusion declares,
   in km/h: a speed that the display works out itself would be an estimate of
   its own.
2. The object that the system acts on is the closest object that the fusion
   gives as valid below 150 m; at the fixed distance of 150 m none is marked.
   The value is compared when the pin moves.
3. The display shows that object as an element of its own and marks none of the
   objects of the scene as it, since the scene names none.
4. Distances are shown to the whole metre and speeds to the whole km/h; the
   rest of the scene is shown as the system gives it.
5. The vehicle speed is the speed that the vehicle gives the driver-assistance
   system at its input, with its sample time, and not the copy that the system
   reads in each pass.
6. The collision warning lasts while, and only while, the warning request asks
   for it; a continuing request continues it.
7. The share of the display in the time that the driver-assistance increment
   allots from the warning request to each mode is 0.1 s of wall-clock time
   from the boundary of the display, chosen by analogy with the division on the
   path to the app of that increment and unmeasured for the renderer, for the
   app that draws the scene and for the sound. Every change of what the display
   shows takes the same 0.1 s as its presentation time.
8. An element is outdated once its time is more than 0.2 s of simulation time
   older than the newest time at the display, or once 0.2 s of wall-clock time
   pass with no new value of its input: two periods of 0.1 s. Late and missing
   values count alike.
9. The warning is unavailable while the warning request is outdated and
   available again once it is current. A renderer that cannot give the warning
   is left for a later increment.
10. The speed and the warning hold throughout each outage in the IVI VM. While
    the app that draws the scene gives no frame, the scene is shown as outdated
    within the limits of the term current and the presentation time, which no
    probe has measured for an outage; no limit on the return of the scene is
    set before a probe measures it.
11. The speed, the warning and its sound go to the high availability renderer
    in an SDV Media VM and the scene to an app in the IVI VM, by the owner's
    decision of 2026-11-17.
12. The display identity hashes the builds of the renderer and of the app that
    draws the scene, the images of both guest VMs, the sound file and each
    configuration file, and records the settings of its start, before the first
    frame of each run.
13. No requirement carries a feature link yet: phase 9 links `REQ-HMI-001` and
    `REQ-HMI-002` to the driving application and `REQ-HMI-001`, `REQ-HMI-008`,
    `REQ-HMI-009` and `REQ-HMI-010` to the AAOS SDV guest.

The rationales cite the files of VisionPilot by file name and line, and the
upstream record gives each with its path at the pinned commit.

Comments about `gapHmiWarningPresentation` and `gapHmiWarningAvailability`
record what Phase 5 fixes of those gaps and what stays open, a renderer that
cannot give the warning among them, and a comment about
`gapHmiRendererIntegration` records what the criteria ask of System 2. The
table of the requirements frames `hmiDisplayRequirementTraceConcern`.
`tests/test_hmi_display_requirements.py` pins the requirements, their
derivations, the terms, the comments and the table. The Phase 5 gates check
that each requirement has a statement, one subject, a derivation from a need
and one verification method. Review judges whether the requirements are the
right ones.

## Functional architecture (Phase 6)

The
[functional architecture](../../textual-notation-of-model/packages/features/hmi/hmi_display_functional_architecture.sysml)
breaks the HMI display down into five functions:

- **`recordDisplayIdentity`** records the display identity before the first
  frame on the display in each run;
- **`drawScene`** draws each scene that reaches the display, with the object
  that the system acts on as an element of its own, and gives each scene that
  it draws with the time of that scene;
- **`judgeCurrency`** judges, by the term current, whether each element and
  the warning request are current or outdated;
- **`showContent`** shows the drawn scene and the vehicle speed, each element
  as outdated while, and only while, it is outdated, and that the collision
  warning is unavailable while, and only while, the warning request is
  outdated;
- **`giveWarning`** gives the collision warning on the display and as a sound
  while, and only while, the warning request asks for it.

They are `AllocatableFunction` actions of the functional flow
`HmiDisplayFunctionalFlow`. The flow takes the scene, the vehicle speed and the
warning request in, and gives what the display shows and the collision warning
out. Inside, the functions exchange the drawn scenes and the currency of the
content, and the display identity is recorded before the display gives its
first frame. The functions state what the display has to do, not what any
element does at an inspected revision; Phase 8 maps them to its software.

Four decisions shape the functional architecture:

- **The drawing of the scene stands apart.** `judgeCurrency` and `showContent`
  take nothing from `drawScene` but the drawn scenes, and `giveWarning` takes
  nothing from it at all. An outage of the drawing of the scene or of the
  environment that hosts it is an event inside the display: the drawn scenes
  stop, `judgeCurrency` finds the scene outdated by the term current, and
  `showContent` shows it as outdated until the drawing gives a current scene
  again, while the vehicle speed and the warning go on. The drawn scenes are
  the exchange that carries the outage inside the display, so no separate
  function detects it: `judgeCurrency` finds it from the drawn scenes. Phase 8
  maps that exchange to the realization.
- **The share of the display in the time.** Each mode of the warning starts
  within 0.1 s of wall-clock time after the start of a request reaches the
  display (`REQ-HMI-005`). The driver-assistance increment allots 0.2 s of
  wall-clock time from the warning request at the boundary of the candidate to
  each mode, and the other 0.1 s lies before the boundary of the display, on
  the path, which the architecture phases of both increments place. Phase 8
  divides the 0.1 s of the display among its elements.
- **States, not modes.** Phase 5 calls a form of the warning, on the display
  or as a sound, a mode, so the conditions of the display are states:
  `ElementCurrency`, outdated or current for each element on its own, and
  `CollisionWarningStates`, unavailable, not asking or asking. `showContent`
  and `giveWarning` depend on the states in which their behavior differs.
- **`REQ-HMI-009` is left to Phase 8.** It constrains which elements draw the
  scene, the vehicle speed and the warning, and the paths that bring them
  their inputs, not what a function does. Phase 8 carries it by the elements
  that it places, and the inspection of the realization that Phase 8 records
  verifies it.

Each of the other nine requirements is allocated (`allocatedTo`) to the
functions that carry it, seventeen allocations in all, and each function
carries at least one. `REQ-HMI-004` and the performance requirement
`REQ-HMI-005` go to `judgeCurrency` and `giveWarning`, since the asking and
its start depend on the currency judgement. An allocation assigns
responsibility only; it claims no satisfaction.

The display in operation is the process `HmiDisplaySystemProcess`. Its
participants are the parts of the operational context of Phase 2, each the
swim lane of its functions: the candidate gives the scene and the warning
request every 0.1 s of simulation time, the command and warning path carries
the warning request to the display, the vehicle gives its speed with each
world snapshot, every step of 0.05 s, and the driver supervises the system
with what the display shows and gets the collision warning. The display
performs its functional flow as one action. The context of Phase 2 holds no
other presentation of the warning beside the display; whether a build of this
display replaces the presentation of the warning in the driver-assistance
increment stays open.

The conceptual interfaces are the five ports of
`HmiDisplayFunctionalBoundary`, the display at its boundary: the scene, the
vehicle speed and the warning request in, each with its time, and what the
display shows and the collision warning out. The items of the vehicle speed
and of the warning request specialize the items that the driver-assistance
increment defines at its own boundary and add nothing to them, so each
quantity is defined once. The items carry ISQ quantities; no vehicle signal
specification is used, and the signal typing starts at Phase 8.

Five views publish the architecture, one per SAF question:

- the breakdown `hmiDisplayFunctionBreakdownView`, which lists the items and
  the five functions of the flow but draws no item flows, and frames
  `hmiDisplayFunctionsConcern`;
- the matrix `hmiDisplayRequirementFunctionMatrixView`, with the ten
  requirements in rows, `REQ-HMI-009` an empty one, and the functions in
  columns, which frames `hmiDisplayFunctionsConcern` as well;
- the process `hmiDisplaySystemProcessView`, with its participants as swim
  lanes and the items that cross the boundary, which answers the Phase 1
  concerns `hmiDisplayInputsConcern`, `hmiWarningSequenceConcern` and
  `hmiAndroidOutageConcern`; it prints no doc, so the times of the warning
  sequence and the sequence of an outage are in the docs of the process and
  of its lanes;
- the table `hmiDisplayStateTableView` of the states and what the functions
  that depend on them do in each, which answers the Phase 1 concern
  `hmiContentCurrencyConcern`;
- the tree `hmiDisplayFunctionalInterfaceView` of the five port definitions,
  each with its directed item, which frames `hmiDisplayInterfaceConcern`.

`tests/test_hmi_display_functional_architecture.py` pins the functions, their
flows and allocations, the process with its times, the states, the interfaces,
the five views and this section. The Phase 6 gates check that a function exists
and that each functional requirement is allocated to one; review judges whether
they are the right ones.

## Logical architecture (Phase 7)

The
[logical architecture](../../textual-notation-of-model/packages/features/hmi/hmi_display_logical_architecture.sysml)
answers what technology-independent logical elements realize the five
functions. The decomposition subject is the system of interest itself:
`HmiDisplayLogicalSystem` specializes the functional boundary of Phase 6,
keeps its five ports and owns the display's inside, one level below the
boundary. The context elements of Phase 2 stay outside and undivided. The
package's one usage of the definition, `hmiDisplayLogicalSystem`, exists for
the views, which draw usages; it depicts the context's `hmiDisplay`, whose
definition `HmiDisplayLogicalSystem` specializes, and is bound to nothing.

The owner decided on three logical elements for the five functions
(2026-11-24). Functions share an element when nothing requires them to be
separately placeable, and split where a requirement constrains the exchange
between them or demands that one keeps working when the other does not:

- **Scene drawer** carries `drawScene` alone. REQ-HMI-009 sets the drawing of
  the scene apart from the drawing of the vehicle speed and the collision
  warning, and REQ-HMI-008 asks the speed and the warning to go on through
  each outage of the drawing of the scene.
- **Presenter** carries `judgeCurrency`, `showContent` and `giveWarning`. The
  three share the currency verdict, and no requirement asks one of them to go
  on when another does not. It takes nothing from the scene drawer but the
  drawn scenes, so it goes on through each outage of the drawing.
- **Identity recorder** carries `recordDisplayIdentity`. The record covers
  both other elements and comes before the first frame of either, so Phase 8
  realizes it beside their software, not inside either.

Each function is allocated to its element by a native allocation from the
definition-nested function usage Phase 6 allocated the requirements to; the
allocation is a responsibility assignment, not a realization, deployment or
runtime claim. The exchanges are connections between typed ports. The
boundary items are delegated from the inherited ports: the scene to the scene
drawer and to the presenter, the vehicle speed and the warning request to the
presenter, and what the display shows and the collision warning from the
presenter. Inside, the drawn scenes go from the scene drawer to the
presenter, the one exchange between elements. The drawn scenes carry
REQ-HMI-001 and REQ-HMI-002 across two elements, and their stop leaves the
vehicle speed and the warning going, as REQ-HMI-008 asks. Nothing runs from
the presenter to another element, and the identity recorder exchanges
nothing. REQ-HMI-009 keeps the paths of the inputs inside the boundary and
stays with Phase 8, which carries it by the elements it places on those
paths; Phase 8 places each exchange on a technology. No element, port or
exchange names a computer, a process, a transport or a signal catalogue.

What crosses the boundary agrees in three places: the boundary flows of the
operational context, the ports of Phase 6 and the delegations of Phase 7.
Nothing goes back to the candidate or to the command and warning path, and
nothing comes from the driver, who only receives. No identity port: Phase 6
orders the record before the first frame by succession, with no item, so it
crosses no exchange. No liveness signal of its own: the drawn scenes carry an
outage of the drawing to the presenter, as Phase 6 decided. Phase 7 shows no
timing: Phase 8 divides the 0.1 s of the display among the elements it
places.

Three concerns of this phase are held by the parties they serve: the
structure by system architects and software developers, the function mapping
by system architects and verification engineers, and the internal exchanges
by systems engineers and software developers. One view answers each, per the
method's list of views per phase: the structure as a tree of the SAF System
Structure Definition viewpoint, the mapping as a matrix of function by
logical element of the System Function Mapping viewpoint, and the exchanges
as an interconnection of the System Internal Exchange viewpoint. The phase
publishes three views, listed in
[`VIEWS.md`](../../textual-notation-of-model/packages/features/hmi/VIEWS.md).

`tests/test_hmi_display_logical_architecture.py` pins the system, the
elements and their ports, the exchanges, the allocations, the views and this
section.

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
the architecture phases to place. CARLA, the cloud hosts, the scenario
runner, the means that make Android in the IVI VM hang, end and restart, the
record of what the candidate gives, the capture of the display and of the
sound, the evaluators and the recordings are **System 2** enablers, not vehicle
features.
The capture observes the AAOS SDV and is no part of it.

The renderer's drawing of the speed and the warning is examined as behavior on
the bench. It is no safety claim: the documentation calls the renderer a
quality management process, the reference safety monitor of AAOS SDV carries no
ASIL certification, and this increment certifies nothing.

## Next obligation and execution limits

Use the Method Check of the reviewed pull request to select the next
obligation, not the phase number alone. Phase 3, the capability classification,
records no feature-model delta, and review judges it: its one blocking check
has nothing to evaluate, so the Method Check lists Phase 3 as vacuous, with a
prompt for review. The next model obligation is **Phase 8**: the physical and
software realization, which allocates each logical element to a physical
element; its first gate is `logicalElementAllocatedToPhysicalElement`. On
2026-11-21 the owner decided that the increment goes on without waiting for
Phase 10 of the driver-assistance increment. Phase 3 and later phases waited
for the revision of the governed scope, which the model now holds, so they go
on. On 2026-11-17 the owner decided that the readiness probe of the high
availability renderer runs with its cost put to him first.

Involve the upstream maintainers before deep adoption, and show them a result
about their project before it is published. Before a paid cloud run, refresh
the regional price, the capacity and the available credit, obtain the owner's
authorization for the campaign, and verify a bounded shutdown with the
evidence exported first. Starting this increment launches no compute and
authorizes no spend.

## Check the framing change

Run `sysand sync`, `python scripts/check_repo.py`,
`python scripts/smoke_test.py` and
`python -m pytest tests/test_hmi_display_framing.py
tests/test_hmi_display_functional_architecture.py
tests/test_hmi_display_logical_architecture.py -q`. These are repository and
lexical checks, not SysML semantic validation and not runtime verification. Use
`python scripts/validate_sysml.py` where a licensed validator is available, or
request the maintainer-run **Privileged Syside Validation** on the reviewed
head. The framing view and its published diagram come from that Syside run.
