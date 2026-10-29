# Implementation

Reference implementation code lives here. Each implementation must state its
execution maturity and retain reproducible evidence rather than treating static
configuration or model validation as runtime proof.

## Active implementations

- [`aebs-autoware-executable-bench`](aebs-autoware-executable-bench/README.md)
  — INC-AEBS-009A reproducible Autoware build, launch, and readiness bench.
- [`aebs-autoware-nominal-vehicle-target-bench`](aebs-autoware-nominal-vehicle-target-bench/README.md)
  — INC-AEBS-009B replay-validated nominal moving-vehicle-target chain.
- [`aebs-autoware-stationary-target-bench`](aebs-autoware-stationary-target-bench/README.md)
  — INC-AEBS-009C replay-validated, explicitly partial stationary-target
  native-intervention-to-MRM/gate chain. Negative, override, degraded, and
  pedestrian/bicycle matrices remain later increments.
- [`aebs-aaos-sdv-visualization-bench`](aebs-aaos-sdv-visualization-bench/README.md)
  — INC-AEBS-010 read-only AEBS visualization bridge, AAOS SDV ingress, and
  center-display app. Implemented and locally tested; runtime evidence
  pending the Phase 10 campaign.
- [`score-reference-interop-bench`](score-reference-interop-bench/README.md)
  — INC-MW-011 Eclipse S-CORE member: the one-process AutowareToSCORE
  adapter (S-CORE communication and ROS 2), its CI build, the REQ-MW-018
  abort matrix and a soak on GitHub-hosted runners. CI regression and design
  data, not evidence of record.
- [`score-broker-path-bench`](score-broker-path-bench/README.md)
  — INC-MW-011 phase 10 AAOS SDV broker path: the two-VM bench scripts (SDV
  Core image build, two-VM launch, host SD route and isolation firewall, IVI
  relay provisioning, clock, recovery), the recording harness, and pure
  evaluators that verdict the HMI-path cases (VC-MW-015/016/017/020) from raw
  run artifacts. Bench tooling and evaluators, not evidence of record.
