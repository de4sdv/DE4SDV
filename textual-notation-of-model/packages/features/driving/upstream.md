# Closed-loop driving: upstream provenance

These are inspection anchors for framing, not an adopted dependency set or an
execution manifest. No upstream implementation is vendored in this increment.

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

The speed benchmark and released-checkpoint driver do not establish the same
configuration or timed scope. The existing simulator integration is AlpaSim;
a CARLA adapter and target-hardware evidence remain new work.

Before adopting a runtime configuration, record the immutable checkpoint
revision/digest, constructor/backbone, precision, camera geometry/resolution,
image and ego-motion history, output interpretation, and exact timed scope.
Source-code license, checkpoint terms and source-data terms are separate.

## CARLA

Inspected source: [CARLA](https://github.com/carla-simulator/carla/tree/2466fff9c0671f02c198fc606f398a4b7d12fda9),
commit `2466fff9c0671f02c198fc606f398a4b7d12fda9`.
This is an inspection pin, not a selected installable image or build.

The documented Autoware end-to-end example concerns VAD, not proof of an
AutoE2E connector. Select and pin a compatible simulator build, sensor rig,
scenario and vehicle/control interpretation before execution.

## Existing DE4SDV integration

The framing was started from repository commit
`954c80da4cfc95f849eaaa8db8847acf34e4629f`.

- [S-CORE/AAOS bench](../../../../implementation/score-broker-path-bench/README.md).
- [S-CORE framing boundary](../middleware/middleware_score_framing.sysml).
- [Existing product-line scope decision](../../../../docs/architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md).

These are reuse/boundary references. Existing AEBS observations do not prove
trajectory transport, AutoE2E actuation or the new timing target. No previous
increment's result is reclassified by this framing.

## Questions requiring upstream engagement

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

No upstream contact, compatibility endorsement, adoption approval or rights
clearance is asserted. Contacting maintainers remains an owner-authorized action
before deep adoption, not a message sent by this framing change.
