# Driver-assistance increment

A product line that requires every member product to brake for a vehicle ahead
cannot take in a new driving application on the strength of its demonstration
videos. It needs a verdict: for each requirement and each scenario, did the
application warn and brake as required, in a run that others can repeat? This
increment asks that of a camera-only driver-assistance application,
[VisionPilot](https://github.com/autowarefoundation/vision_pilot) of the
Autoware Foundation.

**Status: Phase 0 framing proposal.** No implementation, run, result,
product-line admission or compliance is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/driving/driver_assistance_framing.sysml):
  `INC-DRIVING-002`, its engineering question, charter, scope, assumptions and
  open gaps.
- [Syside framing review view](../../textual-notation-of-model/packages/features/driving/VIEWS.md):
  the generated model review artifact, not a runtime architecture claim.
- [Upstream provenance and questions](../../textual-notation-of-model/packages/features/driving/upstream.md#visionpilot).

Orkun Yilmaz owns the increment. One identity covers phases 0 to 11.
Closed-loop verification belongs to Phase 10 of this increment. A readiness
probe comes before the architecture rests on what it tests.

## The engineering question

> Does a camera-only driver-assistance application, with its commands on the
> Eclipse S-CORE command path, show the driver its collision warning on the
> AAOS SDV display and command the braking that the product line requires for
> a vehicle target, when criteria derived from UNECE R152 judge its
> closed-loop behavior in simulation? A verdict for each requirement and
> scenario answers this. A recording of a run that looks right does not.

The increment supports one decision: whether the candidate goes forward on its
own warning and braking, with named additions from the platform, or not at
all. The additions are named from the requirements that fail and from the gaps
of this increment; the increment builds none of them. A fail is a result to
record. It is no reason to change a scenario or a criterion until the
candidate passes.

## What the increment judges

| In scope | Out of scope |
|---|---|
| The collision warning and the braking for a stationary and for a slower moving vehicle target ahead. | Pedestrian and bicycle targets. |
| The collision warning as the AAOS SDV display shows it to the driver: whether it is shown, and when, relative to the start of the braking. | How well the candidate holds speed, distance and lane. These functions run; no case judges them. |
| Two scenarios in which neither a warning nor braking is due, taken from the false-reaction scenarios of the regulation. | Driver monitoring, driver override and deactivation. |
| Criteria for a vehicle target derived from UNECE R152, each with what a simulation cannot show. | Acoustic and haptic modes of the collision warning. The regulation asks for the warning in at least two modes; this increment judges one, the optical warning on the display. |
| The candidate's commands reach the simulated vehicle, and its warning reaches the display, through Eclipse S-CORE; no bypass. | Changing the Autoware-based AEBS or reusing its evidence for this candidate. |
| A pass or a fail for each requirement and scenario, bound to the candidate revision that ran. | Training the candidate's networks, or tuning the candidate or a scenario until a case passes. |
| | On-road operation, production readiness, safety approval, compliance, type approval or certification. |

The scope is one configuration and at most ten requirements. Phase 5 derives
those requirements from the product line's requirements on the collision
warning, the emergency braking and the false reaction.

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
  is switched on.
- **No result on the DE4SDV bench** (`gapCandidateBehaviorUnverified`). No
  closed-loop result of the application exists on the DE4SDV bench, and DE4SDV
  has run neither the inspected revision nor a change to it.
- **No Eclipse S-CORE binding** (`gapScoreIntegration`). The application is
  one process with its own loop. At the inspected revision it has no binding
  to Eclipse S-CORE communication and no S-CORE supervision. How its driving
  command and its state enter the S-CORE path without a bypass is open.
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

The gaps refer to the
[AEBS requirements](../../textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml)
and to the
[governed scope](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md).

## Boundaries

The candidate driver-assistance system is a proposed **System 1** subject. The
Eclipse S-CORE command path that carries its driving command to the actuation
is platform content of **System 1**. The AAOS SDV display that shows its
collision warning to the driver is **System 1** content too: the HMI display
that the product line holds as an optional feature. Both are outside the
candidate's boundary, and neither is an enabler. CARLA, the cloud hosts, the
scenario runner, the evaluators, the capture of the display and the recordings
are **System 2** enablers, not vehicle features. The capture of the display
observes it and is no part of it.

A criterion that is derived from the regulation and met in simulation holds
for the simulated configuration only. It is no statement about compliance or
type approval.

## Next obligation and execution limits

Use the Method Check of the reviewed pull request to select the next
obligation, not the phase number alone. The framing's boundary concern does
not open Phase 1. The next model obligation is **Phase 1 concern framing**: at
least one concern of the engineering scope, held by the parties whose interest
it states.

Involve the upstream maintainers before deep adoption, and show them a result
about their project before it is published. Before a paid cloud run, refresh
the regional price, the capacity and the available credit, obtain the owner's
authorization for the campaign, and verify a bounded shutdown with the
evidence exported first. Starting this increment launches no compute and
authorizes no spend.

## Check the framing change

Run `sysand sync`, `python scripts/check_repo.py`,
`python scripts/smoke_test.py` and
`python -m pytest tests/test_driver_assistance_framing.py -q`. These are
repository and lexical checks, not SysML semantic validation and not runtime
verification. Use `python scripts/validate_sysml.py` where a licensed
validator is available, or request the maintainer-run **Privileged Syside
Validation** on the reviewed head. The framing view and its published diagram
come from that Syside run.
