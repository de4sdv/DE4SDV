# Partial AEBS 009C native-AEB-to-MRM evidence bench

This bench provides **partial INC-AEBS-009C evidence** for one bounded integration path:

1. a stationary map-frame target is injected after a stable baseline;
2. pinned Autoware `autoware_autonomous_emergency_braking` assesses the target;
3. the observer preserves the exact native intervention message `[AEB]: Emergency Brake` and its RSS distance, object distance, and object speed;
4. Autoware's availability/fail-safe chain transitions into emergency-stop MRM;
5. `autoware_vehicle_cmd_gate` selects the emergency command;
6. the simulator exhibits negative acceleration and a later lower speed.

## What this is not

This is **not nominal AEBS evidence**. It does not demonstrate:

- a moving subject vehicle closing on a same-lane moving vehicle target;
- a driver collision warning;
- an explicit no-override/override decision;
- a direct AEBS braking request in the nominal control path;
- collision avoidance, impact-speed reduction, or minimum-distance outcome;
- regulatory compliance, certification, homologation, or physical brake performance.

The native AEB intervention is intentionally reported by Autoware as an `ERROR` diagnostic. In this scenario that diagnostic means **emergency-brake intervention**, not a generic component failure. The downstream MRM behavior is therefore an integration response to that signal; it must not be described as native nominal AEBS braking.

## Reproduce

From this directory:

```bash
./scripts/build.sh
./scripts/run_scenario.sh
python3 scripts/validate_scenario_evidence.py
```

The scenario runner closes the collector contract, writes a per-run evidence bundle, publishes a canonical evidence document only after validation, and binds the result to the frozen runtime and execution manifests.

## Review boundary

The authoritative scenario contract is `config/scenario-009c-aeb-mrm.yaml`. Canonical evidence is `evidence/009c/scenario-evidence.json`; referenced run artifacts are hash-bound from that document. Generated workspace output and noncanonical convenience copies are intentionally excluded.
