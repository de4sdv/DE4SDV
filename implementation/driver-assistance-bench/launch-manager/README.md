# Launch Manager of the S-CORE host (INC-DRIVING-002)

Status: draft, not yet validated. Nothing here has run on the S-CORE host yet.

## The problem

On the S-CORE host, five processes must start in an order that the phase 8 model fixes, and the S-CORE path must
stop carrying driving commands when the candidate's process or the actuation adapter stops working. The model gives
both jobs to the Launch Manager of S-CORE Lifecycle v0.10.0 (the `launchManager` part of `scoreServices` in
`driver_assistance_physical_software_realization.sysml`). This folder holds its configuration and the tests that
hold it to the model and to the supervision decision of 2026-11-18.

## The supervision decision of 2026-11-18

The increment uses S-CORE's own mechanisms:

- the Launch Manager's alive supervision of the candidate's process (`vision_pilot`) and of the actuation adapter;
- the driving command's mw::com deployment at ASIL B (provider and consumer, below);
- reaction (a): on a supervision failure the Launch Manager kills the process (SIGKILL) and switches to a run target
  without the candidate's process and the adapter, so no further driving command reaches the vehicle. The simulator
  keeps its last control, as in the stop run. The run's records log the event.

There is no stop response and no safe state; that stays a recorded gap. Health Monitor deadline monitoring is not
used. There is no ASIL claim: VisionPilot and its GPU libraries are not developed or qualified to ASIL B. The ASIL B
deployment is S-CORE's mechanism on the command's path, nothing more.

At Lifecycle v0.10.0 (`eclipse-score/lifecycle` tag `v0.10.0`, `2afae116`, the version that reference_integration
v0.10.0 pins) the reaction is upstream's own: on a supervision failure the Launch Manager sends SIGKILL, then acts
as for a crash (`docs/features/lifecycle/architecture/_assets/launch_manager_supervision_failure.puml`), and the
recovery action of a run target can only switch to `fallback_run_target`
(`scripts/config_mapping/lifecycle_config.py:696-706`). `fallback_run_target` is therefore the recovery target.

## The file

[`config/launch_manager_config.json`](config/launch_manager_config.json), `schema_version` 2. Lifecycle's converter
(`scripts/config_mapping/lifecycle_config.py` at v0.10.0) turns it into the flatbuffer the daemon reads.

| Component | Type | Starts after | Ready when |
|---|---|---|---|
| `identity_recorder` | `Reporting` | nothing: first | it calls `report_running`, once the record is written and offered |
| `someipd` | `Native` | nothing | its process runs |
| `gatewayd` | `Native` | `someipd` | its process runs |
| `vision_pilot` | `Reporting_And_Supervised` | `identity_recorder`, `gatewayd` | its first completed pass (the module calls `report_running` then) |
| `actuation_adapter` | `Reporting_And_Supervised` | `identity_recorder` | it has subscribed to the driving command |

| Run target | Components |
|---|---|
| `supervised_path` (initial) | all five |
| `fallback_run_target` (the recovery target) | `identity_recorder`, `someipd`, `gatewayd` |

The start order is the model's: the identity recorder first, so the candidate record exists before the candidate's
process starts; then the candidate's process and the actuation adapter. The adapter does not wait for the candidate:
it finds the command service itself, so it subscribes before the first command, which comes only after the
candidate's network sessions and first inference. someipd and gatewayd start before the candidate's process, so the
warning path is up before the first warning request.

A component that is in both run targets keeps running across the switch (Lifecycle v0.10.0 does not restart an
active component: `score/launch_manager/src/daemon/src/process_group_manager/details/process_info_node.cpp:517-534`).

Every component runs as root (`sandbox.uid` 0), as Lifecycle's own integration test `complex_monitoring` does, and
the Launch Manager itself must run as root. Because all the processes share one uid, each mw::com manifest of the
host sets its own `applicationID`: gatewayd 3410, someipd 3411, the candidate 3412, the adapter 3413, the identity
recorder 3414 (that last one is an assumption for its manifest). A uid per component is open.

## The alive supervision values

The candidate gets one image, makes one plan and sends one command per 0.1 s of simulation time, and the world side
paces the simulation at wall-clock pace, so its loop completes one pass per 0.1 s of wall-clock time. The adapter
gives one notification per 0.1 s of its receive loop. VIS8 measured the image-to-command latency with the
visualization recorder at a median of 43.6 ms and a p99 of 65.1 ms, within the cycle.

| Value | | Rule |
|---|---|---|
| `reporting_cycle_ms` | 200 | two cycles per window, so the phase of the notifications against the window does not matter |
| `min_indications` | 1 | at least one notification per window |
| `max_indications` | 6 | three times the nominal two, so the passes that catch up after a slow one do not count as a fault |
| `failed_cycles_tolerance` | 1 | one failed window is tolerated; the second in a row trips |
| `evaluation_cycle_ms` | 100 | the Launch Manager evaluates twice per window |

What this gives, by `tests/test_launch_manager_config.py`'s reading of upstream's evaluation (`Alive.cpp:362-436` at
v0.10.0):

- a single slow pass of up to 0.4 s, six times VIS8's p99, never trips the supervision, whatever its phase;
- no notification for 0.6 s always trips it; the Launch Manager reacts within about one more window;
- a pass that handles no frame gives no notification, so when the images stop, for whatever reason, the supervision
  trips.

The supervision starts only when the process reports running. The candidate reports running after its first
completed pass, so its start (the attach to the hero, the network sessions, the first frame and the first
inference) falls under its ready timeout of 420 s, not under the supervision. The adapter reports running once it
has subscribed.

## What the evidence record must say (contract for B9)

- The module's event log has `supervision.start` (first completed pass), `supervision.stop` with `alive_reported`,
  or `supervision.off` with the reason; the summary line has `alive_reported`.
- The adapter's log has `supervision` records with `state` `start`, `stop`, `off` or `error`.
- A supervision failure leaves no record in either process, since SIGKILL ends it. The record of the run must take
  it from the Launch Manager's own log (its `Alive Supervision (...) switched to EXPIRED` and the run target switch),
  and must show that both processes ended without a `supervision.stop` or `stop` record.
- A world stall makes the candidate miss its notifications too. A supervision failure whose last notification lies
  just before a late world tick (more than 0.2 s after the one before) is a bench event, not the candidate's fault.

## What the session must do (contract for B13)

- Stage the files under `/tmp/de4sdv-da-bench` (`bin/`, `lib/`, `config/`, `vision_pilot/` as the candidate's working
  directory with `H.yaml` and `config/vision_pilot.conf`, `run/` as the run directory), and the interface settings
  `config/de4sdv_score_interface.conf` with `mw_com.config` naming `mw_com_config_vision_pilot.json`.
- Stage `etc/launch_manager_config.bin` and the daemon's own mw::com configuration
  `config/mw_com_config_launch_manager.json` as `etc/mw_com_config.json`, and run the daemon in the stage. The daemon
  offers its LmControl service (`LaunchManager/StateManager/Instance`) through mw::com, which reads
  `./etc/mw_com_config.json`; without it the daemon aborts at its start. The file holds that one instance, as
  upstream's example does, with the application id 3417 (`tests/test_launch_manager_mw_com_config.py` gives the
  reasons at the pins).
- Expect each process to get exactly the environment its component configures: Lifecycle v0.10.0 passes nothing of
  its own environment (no `HOME`), only `LCM_ALIVE_INTERFACE_PATH` for a supervised component. `vision_pilot` and
  `actuation_adapter` link LibCarla's client, whose static initializer reads `CARLA_CACHE_DIR`, else `HOME` without a
  check, and both died of SIGSEGV before `main` on the L4 in session 5. So both components set `CARLA_CACHE_DIR` to
  `/tmp/de4sdv-da-bench/run/carla_cache`. `tests/test_launch_manager_environment.py` gives the reasons at the pins.
- Start the world's pacer before the candidate's ready timeout ends.
- Stop the Launch Manager (SIGTERM: it switches to `Off` and ends the supervision first) before the world stops
  ticking. Otherwise the end of every run reads as a supervision failure.

## What the local tests cannot show

The tests check the file's structure, its values and their effect by a re-implementation of upstream's
evaluation. Only the probes show:

- that Lifecycle v0.10.0's converter and daemon accept the file on the S-CORE host, and the start order (the S-CORE
  build probe of phase 10);
- the alive notifications of the real processes, and that a killed or stalled candidate leads to
  `fallback_run_target` with the recorder and the gateway still running (the same probe, with a stop of the
  notifications);
- that mw::com 0.6.0 accepts the ASIL B deployment of the command between the candidate and the adapter (the same
  probe);
- that no run at 20 km/h trips the supervision (the first closed-loop run of phase 10).

## Tests

```bash
python -m pytest -q implementation/driver-assistance-bench/launch-manager/tests
# with Lifecycle's converter and schema:
LIFECYCLE_SRC=<eclipse-score/lifecycle at v0.10.0> python -m pytest -q implementation/driver-assistance-bench/launch-manager/tests
```

The suite is registered in `tools/run_bench_unit_tests.py`. `tests/lifecycle_mock/` holds test-only declarations of
the Lifecycle v0.10.0 API, used by the score-interface and actuation-adapter suites for a syntax check of their
lifecycle bindings; they are not S-CORE code.
