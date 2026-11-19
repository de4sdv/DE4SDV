# The S-CORE host's session entries

Status: draft, not yet validated. Only the dry runs in `../tests/` have run, with a fake Launch Manager and stub
components.

## The problem

The session (`../../session/da_session.sh`) drives the S-CORE host through four entries of
`../../session/entrypoints.env`. Their contracts are in the session README, "Entry-point contracts". The Launch
Manager lane (`../../launch-manager/`) fixes the paths, the start order and the stop. These scripts fill those
entries. They stage what the configuration names under `/tmp/de4sdv-da-bench`, run the Launch Manager as root, and
collect what it leaves behind.

## The scripts

| Script | Entry | What it does |
|---|---|---|
| `start_score_side.sh <out> <carla_host or none>` | `ENTRY_SCORE_START` | stages (mode full with a CARLA host, mode path with none), starts the Launch Manager as root and detached, waits until the identity recorder has reported running and the processes of the mode exist, then writes `$DA_STAGE/state/score_side.env`. It does not wait for the candidate's own report: that needs the world's images, so the session starts the world pacer next, within the 420 s ready timeout |
| `stop_score_side.sh <out>` | `ENTRY_SCORE_STOP` | SIGTERM to the Launch Manager, then waits `DA_STOP_TIMEOUT_S` (45 s). After that it uses SIGKILL and exits 7. It collects the Launch Manager's log, the run directory, the candidate's working-directory output (`.rrd`, the visualization and its `frames.csv`), the staged configuration, the clocks and `SHA256SUMS` into `<out>/score_side/`. The Launch Manager's own lines on the supervision (the expiry, the run-target switch) go to `supervision_events.txt` |
| `stage_score_side.py` | (helper) | lays out `bin/`, `lib/`, `config/` (with `de4sdv_score_interface.conf` naming the candidate's manifest), `etc/` (the Launch Manager's `launch_manager_config.bin` and its own `mw_com_config.json`), `vision_pilot/` (the working directory with `config/vision_pilot.conf`, `H.yaml`, `homography_C_matrix.yaml`, the networks), `facts/` (the patch series and the upstream revision the identity recorder reads), `run/` and `state/` |
| `derive_path_only_config.py` | (helper) | derives `../config/launch_manager_config_path_only.json` from the Launch Manager lane's file. `supervised_path` loses `vision_pilot` and `actuation_adapter`, and everything else stays. `--check` fails when the committed file is stale |
| `lib_score_side.sh` | (sourced) | the settings (`DA_STAGE`, `DA_B2_BUNDLE`, `DA_SUDO`, `DA_PYTHON`), the process lookup by staged path, the state file and the clock record |

## The camera calibration

The session gives the calibration of the CARLA camera as `DA_CAMERA_CALIBRATION_DIR` (a directory with `H.yaml` and
`homography_C_matrix.yaml`). Every p10-2 run passes it: `env DA_CAMERA_CALIBRATION_DIR=<dir> bash
start_score_side.sh <out> <carla_host>`. The start passes it to the staging helper as `--calibration-dir`. That is
the only name.

- Mode full refuses to start without it (exit 3, before the stage is touched). It never takes the bundle's
  `config/visionpilot/` files, which are upstream's calibration of another camera: a judged run on them would use the
  wrong geometry. A directory that lacks one of the two files is refused in both modes.
- Mode path runs no candidate. There, and only when no directory is given, the bundle's files stand in, because
  the identity recorder hashes the staged files.
- Each start writes `<out>/camera_calibration.json`: the mode, the source (`DA_CAMERA_CALIBRATION_DIR` or the
  mode-path fallback), the directory, and for each file its source path, the source's sha256, the staged path and
  the staged sha256. The candidate record hashes the staged files, so the record and this file agree.
- p10-1 (`../../score-build/scripts/p10_1_check.sh`) is no judged run. Without the session's directory, it copies
  upstream's files into `<out>/p10_1_calibration/` with a `SOURCE.txt` that names them as a stand-in, and starts with
  that directory.

## Repeated starts and stops

One p10-2 starts and stops the S-CORE side three times (calib_steer, run1, run2), each with its own `<out>`, while the
world keeps ticking.

- The start refuses with exit 4 only while a Launch Manager really runs: the state's pid is alive and its command
  line is the state's `LM_BIN`, or a process runs `$DA_STAGE/bin/launch_manager`. A stale pid that another process
  reused counts as nothing, and the stop never signals such a process either.
- The stop marks the stage `state/collected` only after a complete collection. A start clears the stage only with
  that mark. Without it (a stop that never ran or failed), the start first collects the stage into
  `<out>/previous_stage/`, which also ends staged processes left without a Launch Manager. If that collection
  fails, the start refuses (exit 3) and leaves the stage as it is.
- The start never waits for a camera image or for the candidate's report. The world holds its first tick until the
  session's go file, which the session writes after the start returns.

## Mode path

The p10-3 test publisher (`../../ivi-warning/injector/`) offers the candidate's warning-request instance, so the
candidate's process must not run then. p10-1's late subscriber also needs the record's only subscriber slot. Mode
path stages the derived configuration: the identity recorder, someipd and gatewayd only. The recorder then hashes
that file verbatim, so the record shows the mode.

## What these scripts assume of the other lanes

- The bundle (`/opt/da-b2/bundle`) is the bundle step of `../../score-build/build_score_bench.sh`. The staging
  reads these paths of it:

  | Bundle path | Produced by | Read by |
  |---|---|---|
  | `bin/vision_pilot`, `bin/actuation_adapter`, `bin/gatewayd`, `bin/someipd` | the S-CORE build | `stage_score_side.py` (required) |
  | `bin/launch_manager` | the S-CORE build (`@score_lifecycle//score/launch_manager:launch_manager`) | `stage_score_side.py`; `start_score_side.sh` refuses without it |
  | `bin/identity_recorder`; `bin/candidate_record_probe`, `bin/warning_injector`, `bin/ort_cuda_check` | the S-CORE build (`//de4sdv_da_bench/identity-recorder:identity_recorder`, `:candidate_record_probe`, `//de4sdv_da_bench/ivi-warning/injector:warning_injector`, `//de4sdv_da_bench/score-build/workspace:ort_cuda_check`) | `stage_score_side.py` (the first required) |
  | `config/launch_manager/launch_manager_config.bin` and `.json` | Lifecycle v0.10.0's `launch_manager_config` rule, `//de4sdv_da_bench/launch-manager:de4sdv_lm_config`; the JSON is the converted file | `stage_score_side.py`, mode full |
  | `config/launch_manager/launch_manager_config_path_only.bin` and `.json` | the same rule, `:de4sdv_lm_config_path_only`, over `../config/launch_manager_config_path_only.json` | `stage_score_side.py`, mode path |
  | `config/launch_manager/mw_com_config_launch_manager.json` | the bundle step, a copy of `../../launch-manager/config/mw_com_config_launch_manager.json` | `stage_score_side.py`, both modes, as `etc/mw_com_config.json` |
  | `config/gateway/someip_gateway_config_warning.bin` | the gateway build | `stage_score_side.py` |
  | `config/visionpilot/vision_pilot.conf`, `H.yaml`, `homography_C_matrix.yaml` | upstream's `config/`; the C matrix by upstream's `scripts/find_homography_C_matrix.py`, as upstream's CMake build makes it | `stage_score_side.py`; the calibration only in mode path and p10-1 |
  | `share/visionpilot/modules/models/weights/*.onnx`, `share/visionpilot/assets/` | the S-CORE build | `stage_score_side.py` |
  | `lib/*`, `facts/*.diff`, `facts/SHA256SUMS` | the S-CORE build; `facts/*.diff` is exactly the patch series that `facts/SHA256SUMS` lists (the build's own diffs are under `facts/build/`) | `stage_score_side.py`; the identity recorder refuses a `.diff` that `SHA256SUMS` does not list |

  `../../score-build/tests/test_score_build.py` (the bundle contract test) reads this script and the build script's
  bundle step and checks that the bundle step produces every path above.

  The staging takes a `.bin` only when the JSON beside it is byte for byte the bench's file of the mode, the file
  it stages as `config/launch_manager_config.json` and the identity recorder hashes. Otherwise the daemon would run
  a configuration that the record does not name, and the staging refuses (exit 3). The start passes
  `--require-serialized`, so a missing `.bin` or JSON refuses too. The daemon reads
  `etc/launch_manager_config.bin` relative to its working directory, the stage (Lifecycle v0.10.0
  `score/launch_manager/src/daemon/src/run.cpp`).
- The daemon also offers its LmControl service (`LaunchManager/StateManager/Instance`) through mw::com and gives
  mw::com no path, so mw::com reads `./etc/mw_com_config.json` in the stage (communication v0.6.0
  `score/mw/com/runtime_configuration.cpp:31`). Without that file it aborts at once, as in session 4's rehearsal on
  the L4. In both modes the staging puts the bundle's `config/launch_manager/mw_com_config_launch_manager.json`
  there, only when it is byte for byte the bench's file (exit 3 otherwise, and with `--require-serialized` when it is
  missing), and records it as `launch_manager_mw_com_config` in `state/staging.json`. Its application id is 3417,
  unique on the host. The reasons, with file and line at the pins, are in
  `../../launch-manager/tests/test_launch_manager_mw_com_config.py`. The daemon finds no logging configuration in the
  stage and falls back to console logging at warning level (baselibs v0.2.17
  `score/mw/log/detail/registry_aware_recorder_factory.cpp:129-132`,
  `score/mw/log/configuration/configuration.h:113-116`):
  the line p10-1's C3 reads is a warning and shows (`Alive Supervision ( vision_pilot ) switched to EXPIRED , ...`,
  Lifecycle v0.10.0 `alive_monitor/details/supervision/Alive.cpp:556-566`), while its info and debug lines do not.
  The switch to `fallback_run_target` after a supervision failure has no line at that level:
  `handleRecoveryRequest` (`process_group_manager/process_group_manager.cpp:335-370`) logs only at debug, and the
  warning `Problem discovered, activating recovery state: fallback_run_target` (`:406`) comes only from a graph in
  an undefined state, not from a supervision failure (p10-1 run 20261119T134840Z: an expiry, the switch's stops,
  and no such line). So C3 judges the switch by its effect, and the stage needs no logging configuration.
- The bundle holds `bin/identity_recorder` and, for p10-1 and p10-3, `bin/candidate_record_probe` and
  `bin/warning_injector`. The `bazel` stage builds them and the bundle step copies them.
- The Launch Manager logs the expiry of an alive supervision on its standard output; the switch to
  `fallback_run_target` stops each component outside it with SIGTERM and, after its `shutdown_timeout_ms`, SIGKILL
  with the warning `Process ( <name> ) did not respond to SIGTERM, sending SIGKILL`
  (`process_group_manager/details/process_info_node.cpp:488-509`). `stop_score_side.sh` copies the lines that match `expired`, `run target`, `fallback`,
  `supervision`, `SIGKILL` or `terminat` (any case). The exact wording is upstream's, and only p10-1 shows it.

## Tests

```bash
python -m pytest -q implementation/driver-assistance-bench/score-path/tests
```

`fake_launch_manager.py` reads the JSON configuration, aborts like the daemon when `etc/mw_com_config.json` is missing
or lacks the daemon's instance, starts the components in its order as stub processes, holds
the dependents of a Reporting component until its run log says it reported running, and stops them in reverse order on SIGTERM. It can
ignore SIGTERM, exit early, or play an expiry and the run-target switch. The fakes show the scripts' logic, not
Lifecycle's behavior.
