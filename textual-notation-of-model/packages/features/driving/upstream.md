# Driving: upstream provenance

These are inspection anchors of the driving increments, not an adopted
dependency set or an execution manifest. No upstream implementation is vendored.
The VisionPilot section and the statements about VisionPilot belong to
INC-DRIVING-002; the rest of the record belongs to INC-DRIVING-001.

## AutoE2E

Inspected source: [Autoware Foundation AutoE2E](https://github.com/autowarefoundation/auto_e2e/tree/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91),
commit `cb50764b8250a3c44ee5b79b87ba02c5a83b0c91`.

Relevant inspected surfaces:

- [Runtime input/output contract](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Model/README.md).
- [Speed-benchmark constructor and timed path](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Model/speed_benchmark/speed_benchmark.py).
- [Released-model AlpaSim integration](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Model/plugins/alpasim_driver/README.md).
- [Checkpoint repository](https://huggingface.co/AutowareFoundation/auto_e2e).
  This is a discovery location, not an immutable checkpoint selection.

Phase 5 inspected surfaces, for the requirements derived from the needs:

- [Camera tiles and history](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Model/reactive_training_contracts.py).
- [Navigation raster geometry and rates](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Model/navigation/geometry.py).
- [Ego-motion history](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Model/data_parsing/kit_scenes/egomotion.py).
- [Control contract of the plan](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Tools/trajectory_visualization/kinematics.py).

Inspected for the history amendment of 2026-11-09, on the ego-motion history the
checkpoint takes in the closed loop:

- [Closed-loop results](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/experiment/closed-loop/RESULTS.md).
- [Closed-loop replay check](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/experiment/closed-loop/replay_driver.py).

Inspected for the route decision of 2026-11-10, on whether the route steers the
plans:

- [Route-conditioned planner model](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Model/model_components/reactive_e2e.py).
- [Route-conditioning evaluation](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Academic_Paper/AutoE2E_Route_Conditioned/paper_en.md).

The speed benchmark and released-checkpoint driver do not establish the same
configuration or timed scope. The existing simulator integration is AlpaSim;
a CARLA adapter and target-hardware evidence remain new work.

Before adopting a runtime configuration, record the immutable checkpoint
revision/digest, constructor/backbone, precision, camera geometry/resolution,
image and ego-motion history, output interpretation, and exact timed scope.
Source-code license, checkpoint terms and source-data terms are separate.

## CARLA

Inspected during framing: [CARLA](https://github.com/carla-simulator/carla/tree/2466fff9c0671f02c198fc606f398a4b7d12fda9),
commit `2466fff9c0671f02c198fc606f398a4b7d12fda9`, on the branch `ue58-dev`.
It was read for the framing. It is not the build that the
[closed-loop driving bench](../../../../implementation/closed-loop-driving-bench/README.md)
runs.

The bench runs release 0.9.16: tag
[`0.9.16`](https://github.com/carla-simulator/carla/tree/0.9.16), commit
`294096eb1c38eabf246e4f3a9cdab704e33a7f4c`, cut from the branch
`ue4/0.9.16`. That commit is not an ancestor of the inspected one. DE4SDV
names the release and records no digest of the installed package. Each run
record carries the version that the simulator server reports, as
`simulatorBuild`.

The documented Autoware end-to-end example concerns VAD, not proof of an
AutoE2E connector. The bench's
[interface control document](../../../../implementation/closed-loop-driving-bench/interfaces/ICD.md)
gives the simulator host, the route and the vehicle configuration with its
steering interpretation. The
[world side](../../../../implementation/closed-loop-driving-bench/world-side/README.md)
sets up the camera rig.

## Eclipse S-CORE FEO

Inspected source: [eclipse-score/feo](https://github.com/eclipse-score/feo/tree/313b3d849c17881d3a11b6bf62aa2afab6565ef0),
release v1.0.5, commit `313b3d849c17881d3a11b6bf62aa2afab6565ef0`.

Phase 8's amendment of 2026-11-09 consumes it with one DE4SDV patch, an event
trigger in the scheduler: one chain per camera frame, the newest frame taken
and the skipped frames counted. The release's scheduler is timer-paced only,
and its topics are Rust-only. The patch and the eight module overrides that
let it build beside reference_integration v0.10.0 are DE4SDV's to keep; no
FEO source is vendored. [Upstream contact](#upstream-contact) says what
DE4SDV has put to the FEO maintainers about the trigger.

## Changes over the AutoE2E pin

The planner of phase 8 runs the checkpoint at `cb50764b` on PyTorch with
DE4SDV's kernel changes, which alter rounding only. They are DE4SDV changes
over the pinned revision, not an upstream release.
[Upstream contact](#upstream-contact) says what DE4SDV has told the AutoE2E
maintainers about them.

The input activity gives the checkpoint the ego-motion history with yaw rate
and curvature as zero (owner decision of 2026-11-09, GAP-DRIVING-010).
Upstream's closed-loop results at the pin trace the checkpoint's divergence to
its own yaw history, fed back in the closed loop, and name zeroing those two
columns as a check without retraining. DE4SDV adopts that check as a bounded
deviation of its own; upstream presents it as a check, not as a supported
configuration.

## Existing DE4SDV integration

The framing was started from repository commit
`954c80da4cfc95f849eaaa8db8847acf34e4629f`.

- [S-CORE/AAOS bench](../../../../implementation/score-broker-path-bench/README.md).
- [S-CORE framing boundary](../middleware/middleware_score_framing.sysml).
- [Existing product-line scope decision](../../../../docs/architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md).

These are reuse/boundary references. Existing AEBS observations do not prove
trajectory transport, AutoE2E actuation or the new timing target. No previous
increment's result is reclassified by this framing.

## VisionPilot

Read for the framing of INC-DRIVING-002 on 2026-11-13:
[Autoware Foundation VisionPilot](https://github.com/autowarefoundation/vision_pilot/tree/014e0e7a56ee8e597c2cab8175233f74edd9b856),
commit `014e0e7a56ee8e597c2cab8175233f74edd9b856` of the branch `main`, with
an [Apache-2.0 licence file](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/LICENSE).
Its release tag `v1.2` is commit `9a96c3e771f9e79e91b6ccfcbf2ce860530024c8`,
an ancestor of the inspected commit. Which revision a bench runs is a decision
of phase 8. DE4SDV has built and run nothing of this project, and vendors
nothing of it.

What the framing's gaps rest on, at the inspected commit:

- [Application loop](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/app/vision_pilot.cpp):
  one process that reads the camera image and the vehicle speed and writes a
  steering and an acceleration command.
- [Warning and braking decision](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/planning/src/planning.cpp):
  the forward-collision warning and the emergency braking are two ranges of
  the acceleration that the
  [speed planner](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/planning/src/longitudinal_planning.cpp)
  returns. The code has no emergency function apart from that planner.
- [Vehicle interface](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/sensing/vehicle_interface/include/vehicle_interface/vehicle_interface.hpp):
  it carries no warning. The warnings go to the application's
  [visualization](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/visual_interface.cpp)
  and to its
  [data log](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/logging/src/logger.cpp),
  each only when the
  [application configuration](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/config/vision_pilot.conf)
  switches it on. In the inspected commit that file switches the visualization
  on and the data log off.
- [Closed-loop simulator path](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/Simulation/CARLA/ROS2/README.md):
  CARLA 0.9.16 over ROS 2.
- [Safety element out of context, draft](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/Functional_Safety/SAFETY_ELEMENT_OUT_OF_CONTEXT.md):
  it lists warning requests among the outputs of the element.
- A search of every text file of the inspected commit for the S-CORE launch
  manager, its communication library and FEO found none: the commit holds no
  binding to Eclipse S-CORE communication and no S-CORE supervision.
- The README of the object-detection network,
  [AutoSpeed](https://github.com/autowarefoundation/auto_speed/tree/b62e55b93ba728787cb1152347463030443634c4)
  (commit `b62e55b93ba728787cb1152347463030443634c4`, Apache-2.0 licence
  file), says that the AutoSpeed 2.0 network is trained on the OpenLane
  dataset. DE4SDV has not checked that the weights in the application's
  repository are the ones that this README describes, and has not read the
  terms of the weights or of that dataset.

## Questions requiring upstream engagement

AutoE2E:

- Which released checkpoint/configuration is supported for camera-based
  closed-loop inference, and what target-hardware timing is actually measured?
- Which temporal/camera geometry and control-output interpretation must a CARLA
  adapter preserve, and which domain-shift limitations are known?
- Which loading path is authoritative for closed-loop use: replaying the
  configuration the checkpoint records, as the AlpaSim driver plugin does, or
  rebuilding it from the training stage
  ([inference pipeline](https://github.com/autowarefoundation/auto_e2e/blob/cb50764b8250a3c44ee5b79b87ba02c5a83b0c91/Platform/pipelines/inference.py))?
- Which measured latency applies to the 512 by 512 input form, since the
  published speed-benchmark rows measure 256 by 256?
- Which checkpoint/data terms permit the intended use and evidence distribution?
- Is a zeroed yaw-rate and curvature history the intended way to drive
  `nuplan-epoch-5` in the closed loop, and is a checkpoint or driver without
  this feedback planned? The readiness probe reproduced the divergence in CARLA
  and the effect of the zeroed history.
  [Upstream contact](#upstream-contact) says what DE4SDV has posted in the
  upstream thread on this divergence.

VisionPilot:

- Which revision and which configuration does the project support for a
  closed-loop run in the simulator?
- Is an emergency function apart from the speed planner planned?
- The safety draft lists warning requests among the outputs of the element. Is
  an output of the warnings planned apart from the visualization and the data
  log?
- Which camera geometry and calibration does a simulated camera have to keep
  for the distance estimate to hold?
- Which terms of the weights and of their training data permit the intended
  use and the publication of results?

## Upstream contact

DE4SDV posted three times in the upstream repositories on 2026-11-11, each
time on the owner's word:

- [Issue 124 of FEO](https://github.com/eclipse-score/feo/issues/124) states
  the need for one task chain per set of camera images. It shows the scheduler
  change as a diff and calls it an experiment, not a proposal for the final
  shape. It asks whether an event trigger is planned and whether a pull
  request would be accepted.
- [Issue 243 of AutoE2E](https://github.com/autowarefoundation/auto_e2e/issues/243)
  reports the inference time measured with the released code and with
  DE4SDV's changes, and describes the changes without their code. It asks
  whether speed work is planned and whether a pull request would be taken.
- A [comment on issue 221 of AutoE2E](https://github.com/autowarefoundation/auto_e2e/issues/221#issuecomment-6787293503),
  the upstream thread on the yaw-history divergence, reports the bench's
  closed-loop results with the yaw-rate and curvature history zeroed, and a
  route experiment.

On 2026-11-12, on the owner's word, DE4SDV posted a
[comment on issue 1430 of S-CORE communication](https://github.com/eclipse-score/communication/issues/1430#issuecomment-6832871010),
the upstream thread on a process that aborts when it destroys a subscribed
proxy. The middleware model records that defect as GAP-MW-041; on this bench it
is the core dump of gatewayd at the stop of a run. The comment reports DE4SDV's
unreviewed feasibility runs of 2026-11-03 with the change that a pull request of
that project proposes (SOME/IP gateway at f30d5668, communication 0.6.0): without
the change, 34 of 34 stops of a subscribed gatewayd ended with SIGABRT; with it,
34 of 34 ended with exit code 0. When the comment was posted, the pull request
was not merged; the pins of the bench do not carry the change.

In the VisionPilot repository DE4SDV has posted nothing.

DE4SDV has opened no pull request in any of these repositories. This record
states what DE4SDV sent. It follows neither the replies, nor whether a thread
is open, nor whether a pull request there is merged. No compatibility
endorsement, adoption approval or rights clearance is asserted. Each further
message to maintainers remains an owner-authorized action.
