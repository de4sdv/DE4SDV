# INC-AEBS-010 — AEBS visualization implementation bench

System 2 implementation of the AEBS visualization on AAOS SDV (INC-AEBS-010
Phases 6–9 are the accepted model baseline; this bench realizes the selected
physical realization).

## Architecture (one direction, always)

```text
pinned native Autoware AEB + DE4SDV 009B coordinator  (vmB, ROS 2)
    -> de4sdv_aebs_010_bridge (read-only ROS 2 adapter, subscriptions only)
    -> length-delimited frame stream, NEW port 4721 (MW-010 port not reused)
    -> de4sdv_aebs_ingress (native service in sdv_ivi_cf guest)
    -> SDV Gateway Data Tunnel (documented client APIs only)
    -> De4sdvAebsVisualizationApp (Java center-display app)
```

Per-field provenance is enforced in code, not comments: native RSS and the
exact `aeb_emergency_stop` diagnostic carry `nativeAutowareAEB`; the target
projection of the native cloud is `displayDerived`; warning/braking/lifecycle
are `de4sdvAebsCoordinator`. The coordinator's combined object distance is
never relabeled as native output.

## Layout

```text
config/test-article.yaml   configured test article (Phase 9 accepted baseline)
runtime-lock.yaml          exact executed pins (bound during the runtime segment)
interface/aebs_visualization.proto   wire contract (SysML is the semantic authority)
src/de4sdv_aebs_010_bridge/          ROS bridge (frame_assembler, source_adapter, ros_node)
aosp/vendor/de4sdv/aebs_visualization/   AOSP overlay (ingress service, Java app, sepolicy)
scripts/                    staging + campaign tooling
evidence/010/               retained Phase 10 evidence (added by the evidence slice)
```

## Local tests (no ROS, no AOSP, no GCP)

```bash
cd src/de4sdv_aebs_010_bridge
PYTHONPATH=. python -m pytest -q test/
```

43 tests cover: provenance contract, monotonic sequencing, sink-side
validation (schema/sequence/age/finiteness/range), the presentation watchdog
(stale/unavailable/invalid/restored), point-cloud projection geometry,
length-delimited transport, and **non-interference** (no publishers, no
services/actions, no control-topic references, send-only server, MW-010 port
unreused).

## Staging into AOSP (on vmA, budget-guarded)

```bash
python scripts/stage_aosp_overlay.py --aosp /home/mrk/aosp
# In the AOSP shell:
source build/envsetup.sh && lunch sdv_ivi_cf-aosp_current-userdebug
m De4sdvAebsIngressService De4sdvAebsVisualizationApp  # see runtime-lock for bound names
m
```

Follow the repository GCP cost guard (`tools/gcp_cost_guard.sh`) for every VM
start/stop. vmA and vmB are stopped when idle.

## Claim boundary

Code in this directory is implemented and locally tested; it is **not**
runtime evidence. Execution claims require the Phase 10 campaign (real
`sdv_ivi_cf` guest, real pinned bench, retained artifacts). No production-HMI,
safety, compliance, or INC-MW-010-modifying claim is made.
