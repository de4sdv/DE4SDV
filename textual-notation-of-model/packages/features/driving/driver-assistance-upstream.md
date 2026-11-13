# Camera-only driver assistance: upstream provenance

These are inspection anchors for the framing of `INC-DRIVING-002`. They are not
an adopted dependency set and not an execution manifest. DE4SDV has built and
run nothing of this upstream project. Nothing of it is vendored.

## VisionPilot

Inspected source: [Autoware Foundation VisionPilot](https://github.com/autowarefoundation/vision_pilot/tree/014e0e7a56ee8e597c2cab8175233f74edd9b856),
commit `014e0e7a56ee8e597c2cab8175233f74edd9b856` of the branch `main`, read on
2026-11-13. The repository carries an
[Apache-2.0 licence file](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/LICENSE).
Its release tag `v1.2` is commit `9a96c3e771f9e79e91b6ccfcbf2ce860530024c8`, an
ancestor of the inspected commit. The framing was read from the inspected
commit, not from the release. Which revision a bench runs is a decision of
phase 8.

Inspected surfaces:

- [Application loop](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/app/vision_pilot.cpp):
  one process that reads the camera image and the vehicle speed and writes a
  steering and an acceleration command.
- [Warning and braking decision](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/planning/src/planning.cpp):
  the forward-collision warning and the emergency braking are two ranges of
  the acceleration that the speed planner returns. The code has no emergency
  function apart from that planner.
- [Vehicle interface](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/sensing/vehicle_interface/include/vehicle_interface/vehicle_interface.hpp):
  the application reads the vehicle speed from it and writes a steering and an
  acceleration to it. It carries no warning. The warnings go to the
  [application's display](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/visual_interface.cpp)
  and to its [data log](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/logging/src/logger.cpp),
  each only when the application configuration switches it on. In the
  inspected commit that file switches the display on and the data log off.
- [Speed planner](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/planning/src/longitudinal_planning.cpp)
  and the [fusion of the closest in-path object](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp).
- [Application configuration](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/config/vision_pilot.conf)
  and the [ROS 2 topics](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/config/vision_pilot_ros2.conf):
  the inference provider, the precision of the networks, the speed limit as a
  constant, and the topics of the camera image, the vehicle speed and the two
  commands.
- [Closed-loop simulator path](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/Simulation/CARLA/ROS2/README.md):
  CARLA 0.9.16 over ROS 2, with one node that publishes the vehicle speed and
  [one that merges](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/Simulation/CARLA/ROS2/src/carla_control_publisher/README.md)
  the steering command and the longitudinal command into one command message
  for the simulator.
- [Safety element out of context, draft](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/Functional_Safety/SAFETY_ELEMENT_OUT_OF_CONTEXT.md):
  what the project leaves to the integrator. The draft lists warning requests
  among the outputs of the element.

The inspected commit holds no binding to Eclipse S-CORE communication and no
S-CORE supervision. A search of every text file of the inspected commit for the
S-CORE launch manager, its communication library and FEO found none.

## What the project's own open changes report

On 2026-11-13 these three pull requests of the project were open drafts, not
merged. This repository holds no reproduction of their results. They are
recorded because the framing's gaps rest on them. None of the three starts from
the inspected commit. Pull requests 427 and 423 branch from the default branch
as it was on 2026-09-11. The inspected commit holds none of the 123 commits
that led to that state: the common ancestor of these two pull requests and the
inspected commit dates from 2026-08-11. Pull request 448 branches from the
default branch as it was on 2026-10-09.

- [Pull request 427](https://github.com/autowarefoundation/vision_pilot/pull/427)
  states that the speed planner takes the relative speed of the object ahead as
  its closing speed, so that the term has the wrong sign. Its table gives, for
  the application's vehicle at 9.4 m/s, a stopped object ahead and a 20 m gap,
  an acceleration of +1.48 m/s² before the change and −3.62 m/s² after it. The
  same pull request stops one network alone from starting the track of an
  object ahead.
- [Pull request 448](https://github.com/autowarefoundation/vision_pilot/pull/448)
  runs the loop step of the application, bound to Python and with the pull
  request's own correction of a sign in the lateral control, in closed loop on
  a processor, in a later CARLA release than the one above. It ran the first
  case of each of its three scenarios: the vehicle that cuts in is hit, the
  pedestrian that steps out is hit and never braked for, and the straight
  junction passes.
- [Pull request 423](https://github.com/autowarefoundation/vision_pilot/pull/423)
  publishes the driving command and its reference as typed messages with the
  identity of the camera cycle, for a supervisor outside the application. Its
  description lists no warning among their contents.

## Networks and their data

The application reads its networks' weights from its own repository. The
README of the object-detection network,
[AutoSpeed](https://github.com/autowarefoundation/auto_speed/tree/b62e55b93ba728787cb1152347463030443634c4)
(commit `b62e55b93ba728787cb1152347463030443634c4`, Apache-2.0 licence file),
says that the AutoSpeed 2.0 network is trained on the OpenLane dataset. DE4SDV
has not checked that the weights in the application's repository are the ones
that this README describes. It has not read the terms of that dataset, the
records of the two other networks, or the terms of the weights.

## Simulator, middleware and regulation

- The simulator release and the Eclipse S-CORE revisions of the driving bench
  are recorded in the [closed-loop driving record](upstream.md) and in the
  [bench README](../../../../implementation/closed-loop-driving-bench/README.md).
  The framing treats that bench as a reuse candidate.
- The regulation that the criteria are to be derived from is recorded in
  [`aebs-regulatory-source.yaml`](../../../../methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml).
  That record anchors the performance and procedure clauses for the pedestrian
  and the bicycle target. The clauses for a vehicle target are not yet anchored
  there.
- The governed product-line scope is
  [the scope decision](../../../../docs/architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md).

## Questions requiring upstream engagement

- Which revision and which configuration does the project support for a
  closed-loop run in the simulator: the release, the default branch, or the
  default branch with the open changes above?
- Is an emergency function apart from the speed planner planned, or is the
  supervisor outside the application the intended place for it?
- The safety draft lists warning requests among the outputs. Is an output of
  the warnings planned apart from the display and the data log?
- Which camera geometry and calibration does a simulated camera have to keep
  for the distance estimate to hold?
- Which terms of the weights and of their training data permit the intended
  use and the publication of results?

## Upstream contact

None. DE4SDV has posted nothing in this project and has opened no issue and no
pull request there. No compatibility endorsement, adoption approval or rights
clearance is asserted. Each message to the maintainers is an owner-authorized
action.
