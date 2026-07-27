# INC-AEBS-009B nominal moving-vehicle-target evidence bench

This bench provides **bounded, replayable nominal-path evidence** for `INC-AEBS-009B`:

1. a simulated subject vehicle closes on a same-lane moving vehicle target;
2. pinned Autoware AEB performs target processing and native RSS collision assessment;
3. a coordinator derives the driver-warning request from the native RSS threshold and requires a fresh source-stamped `false` override sample;
4. only the exact native intervention diagnostic tuple activates a distinct direct `EmergencyBrakingRequest`;
5. the coordinator is the sole nominal vehicle-gate input publisher and the gate runs with emergency handling disabled;
6. braking remains latched until fresh odometry verifies ego stop for the configured hold duration;
7. replay recomputes oriented ego/target footprint separation from preserved map poses and requires positive, opening noncollision separation through release.

The coordinator telemetry is **not** a second native collision-risk implementation. Native RSS remains the collision-assessment input; the warning margin is coordinator-derived and labeled as such.

## Evidence boundary

The retained evidence demonstrates only the configured simulation chain. It does **not** establish:

- conscious driver override behavior;
- a non-activation or false-reaction matrix;
- failed or degraded operation;
- pedestrian or bicycle target behavior;
- real-vehicle or physical brake performance;
- regulatory compliance, certification, homologation, or type approval.

`EmergencyBrakingRequest` is a nominal-path AEBS demand. It is intentionally distinct from `EmergencyInterventionRequest` and `MinimumRiskManoeuvreRequest`. This composition publishes no fabricated MRM-normal heartbeat and does not select an emergency/MRM gate path.

## Reproduce

From this directory:

```bash
./scripts/build.sh
./scripts/run_scenario.sh
python3 scripts/validate_scenario_evidence.py evidence/009b/scenario-evidence.json
```

The runner stops the runtime before hashing artifacts, preserves each attempted run, and updates canonical evidence only after schema validation and independent evaluator replay succeed.

## Review boundary

- Authoritative scenario contract: `config/scenario-009b-moving-vehicle-target.yaml`
- Evidence schema: `schemas/scenario-evidence.schema.json`
- Canonical evidence: `evidence/009b/scenario-evidence.json`
- SysML architecture/evidence obligations: `textual-notation-of-model/packages/features/aebs/aebs_009b_nominal_evidence.sysml`

The SysML requirement usages are candidate evidence obligations. Satisfaction remains pending review of the retained evidence and privileged Syside validation.
