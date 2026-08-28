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
