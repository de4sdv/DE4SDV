# Launch Manager of the S-CORE host (INC-DRIVING-002)

Status: draft, not yet validated. The configuration ran on the S-CORE host in p10-1 try 4 (SID 20261119T160111Z,
2026-11-19, `eae0a6ef`): C1 (the start order, both configurations), C2 (the alive notifications), C3 (the stalled
candidate's fallback, within 10.9 s) and C4 met. It ran every run of p10-2 attempt 3 (SID 20261120T092051Z, 2026-11-20,
`39a964a2`) and of S1 (SID 20261121T014447Z, 2026-11-21, `508649ba`), there with `path_stopped` for the stop run.

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
- reaction (a): on a supervision failure the Launch Manager switches to a run target without the candidate's process
  and the adapter, ending both, so no further driving command reaches the vehicle. The simulator
  keeps its last control, as in the stop run. The run's records log the event.

There is no stop response and no safe state; that stays a recorded gap. Health Monitor deadline monitoring is not
used. There is no ASIL claim: VisionPilot and its GPU libraries are not developed or qualified to ASIL B. The ASIL B
deployment is S-CORE's mechanism on the command's path, nothing more.

At Lifecycle v0.10.0 (`eclipse-score/lifecycle` tag `v0.10.0`, `2afae116`, the version that reference_integration
v0.10.0 pins) the reaction is upstream's own, and the recovery action of a run target can only switch to
`fallback_run_target` (`scripts/config_mapping/lifecycle_config.py:696-706`). `fallback_run_target` is therefore the
recovery target. The daemon's code, not the design drawing
(`docs/features/lifecycle/architecture/_assets/launch_manager_supervision_failure.puml`, which shows a SIGKILL), sets
the timing: a supervision failure queues the switch (`process_group_manager/process_group_manager.cpp:335-370`, with
no log line above debug level), and the switch stops each component outside the target with SIGTERM, then SIGKILL
after its `shutdown_timeout_ms` (`process_group_manager/details/process_info_node.cpp:488-509`). The p10-1 run
20261119T134840Z on the L4 shows it: the adapter wrote its `supervision` `stop` and `stop` records 1 ms after the
expiry, and the candidate ran its shutdown path. A SIGSTOPped candidate keeps the SIGTERM pending and ends by the
SIGKILL 10 s later.

## The file

[`config/launch_manager_config.json`](config/launch_manager_config.json), `schema_version` 2. Lifecycle's converter
(`scripts/config_mapping/lifecycle_config.py` at v0.10.0) turns it into the flatbuffer the daemon reads.

| Component | Type | Starts after | Ready when |
|---|---|---|---|
| `identity_recorder` | `Reporting` | nothing: first | it calls `report_running`, once the record is written and offered |
| `someipd` | `Native` | nothing | its process runs |
| `gatewayd` | `Native` | `someipd` | its process runs |
| `vision_pilot` | `Reporting_And_Supervised` | `identity_recorder` | its first pass with a result (the module calls `report_running` then) |
| `actuation_adapter` | `Reporting_And_Supervised` | `identity_recorder` | it has subscribed to the driving command |

| Run target | Components |
|---|---|
| `supervised_path` (initial) | all five |
| `fallback_run_target` (the recovery target) | `identity_recorder`, `someipd`, `gatewayd` |
| `path_stopped` (the stop run's target) | `identity_recorder`, `vision_pilot` |

The start order is the model's: the identity recorder first, so the candidate record exists before the candidate's
process starts; then the candidate's process and the actuation adapter. The adapter does not wait for the candidate:
it finds the command service itself, so it subscribes before the first command, which comes only after the
candidate's network sessions and first inference. The candidate's process depends on the identity recorder only, so it
can start before someipd and gatewayd (since a9384a0c: an edge to gatewayd would keep the warning path running in
`path_stopped`, below). The warning path is still up before the first warning request: the start
(`score-path/scripts/start_score_side.sh`) returns only once someipd and gatewayd run, the session writes the go only
after it, and the candidate's first warning request needs an image, which comes only after the go.

A component that is in both run targets keeps running across the switch (Lifecycle v0.10.0 does not restart an
active component: `score/launch_manager/src/daemon/src/process_group_manager/details/process_info_node.cpp:517-534`).

Every component runs as root (`sandbox.uid` 0), as Lifecycle's own integration test `complex_monitoring` does, and
the Launch Manager itself must run as root. Because all the processes share one uid, each mw::com manifest of the
host sets its own `applicationID`: gatewayd 3410, someipd 3411, the candidate 3412, the adapter 3413, the identity
recorder 3414 (that last one is an assumption for its manifest). A uid per component is open.

## The stop run's target `path_stopped`

The stop run of REQ-DRIVING-038 and -043 (the S1 build plan, section 4) stops the S-CORE path while the candidate
keeps running: after the stop no driving command may reach the vehicle and no warning request may reach the IVI.
`path_stopped` holds the identity recorder and the candidate's process; switching to it ends the actuation adapter,
gatewayd and someipd (SIGTERM, then SIGKILL after their `shutdown_timeout_ms`), and keeps the candidate, which is not
restarted and stays supervised.

- Lifecycle v0.10.0 runs, for a run target, every node reachable from it through `depends_on`, component
  dependencies included (`process_group_manager/details/transition.hpp:397-445`, `graph.cpp:57-63` at 2afae116). So
  the candidate's process depends on the recorder only: an edge to gatewayd would keep the warning path running in
  `path_stopped`. The warning path is still up before the first warning request: the start returns only once
  someipd and gatewayd run, the session writes the go only after it, and the first request needs an image after the
  go.
- The switch comes through the daemon's LmControl service. Lifecycle ships the client library
  (`//score/launch_manager:control_cc`) but no command-line client, so `control/` holds a small one,
  `lm_control_client`, built into the bundle. It asks with force (the daemon refuses a queued request,
  `control_provider.hpp:131-138`), waits for the activation result of a state manager request naming the target, and
  prints one JSON line. Its mw::com configuration, `config/mw_com_config_lm_control_client.json`, is the proxy side
  of the daemon's instance (`StateManager/LaunchManager/Instance`, application id 3418).
- `../score-path/scripts/path_stop.sh` runs it on the S-CORE host at go + 12 s and prints the stop record of the
  shared contract.

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
- a pass without a result (one that handles no frame, or upstream's first) gives no notification, so when the images
  stop, for whatever reason, the supervision trips.

The supervision starts only when the process reports running. The candidate reports running after its first pass
with a result, so its start (the attach to the hero, the network sessions, the first frames and the first inference)
falls under its ready timeout of 420 s, not under the supervision. Upstream's pipeline returns no result for the first
frame (`VisionPilot/modules/models/src/inference.cpp:152-159` at 014e0e7a: a two-frame buffer), so the first inference
runs in the second pass, before the first report. Why: in p10-1 run 20261119T134840Z the module still reported after
the first pass that handled a frame, a 6 ms pass without a network, and the cold first inference (about 0.72 s on the
L4's CUDA provider) fell into the supervision and tripped it. The adapter reports running once it has subscribed.


## What the evidence record must say (contract for B9)

- The module's event log has `supervision.start` (first pass with a result), `supervision.stop` with `alive_reported`,
  or `supervision.off` with the reason; the summary line has `alive_reported`.
- The adapter's log has `supervision` records with `state` `start`, `stop`, `off` or `error`.
- The record of a supervision failure comes from the Launch Manager's own log (its `Alive Supervision (...)
  switched to EXPIRED`; the run target switch has no line at its warning level) and from the processes' ends: the
  switch's SIGTERM gives the adapter's `supervision` `stop` and `stop` records, and a stalled candidate's end is the
  SIGKILL warning `Process ( vision_pilot ) did not respond to SIGTERM, sending SIGKILL`.
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
- Expect the candidate's visualization recording in every run of mode full (the owner's decision of 2026-11-17: keep
  the DE4SDV visualization recorder in every run and state its delay). `vision_pilot` sets
  `DE4SDV_VISUALIZATION_RECORD` = `/tmp/de4sdv-da-bench/run/visualization.mkv` (patch 0001: unset or empty means off;
  nvh264enc at 4000 kbit/s by default), and `GST_REGISTRY` = `/tmp/de4sdv-da-bench/gst/registry.x86_64.bin`: without
  `HOME`, GStreamer's plugin registry would go to the passwd home of uid 0, outside the stage, and be read again by
  later runs. `gst/` lies outside every folder the stop collects. The stop moves the video and its sidecars
  (`.frames.csv`, `.summary.txt`) into the run's out folder and records the video's sha256; the pack leaves the video
  on the host (`score-path/scripts/stop_score_side.sh`, `session/README.md`). The path-only configuration keeps these
  settings verbatim, and no run target of p10-1 or p10-3 starts `vision_pilot`, so the recorder never runs there.
  `tests/test_visualization_recorder_env.py`.
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
