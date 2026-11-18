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
| `stage_score_side.py` | (helper) | lays out `bin/`, `lib/`, `config/` (with `de4sdv_score_interface.conf` naming the candidate's manifest), `etc/`, `vision_pilot/` (the working directory with `config/vision_pilot.conf`, `H.yaml`, `homography_C_matrix.yaml`, the networks), `facts/` (the patch series and the upstream revision the identity recorder reads), `run/` and `state/` |
| `derive_path_only_config.py` | (helper) | derives `../config/launch_manager_config_path_only.json` from the Launch Manager lane's file. `supervised_path` loses `vision_pilot` and `actuation_adapter`, and everything else stays. `--check` fails when the committed file is stale |
| `lib_score_side.sh` | (sourced) | the settings (`DA_STAGE`, `DA_B2_BUNDLE`, `DA_SUDO`, `DA_PYTHON`), the process lookup by staged path, the state file and the clock record |

## Mode path

The p10-3 test publisher (`../../ivi-warning/injector/`) offers the candidate's warning-request instance, so the
candidate's process must not run then. p10-1's late subscriber also needs the record's only subscriber slot. Mode
path stages the derived configuration: the identity recorder, someipd and gatewayd only. The recorder then hashes
that file verbatim, so the record shows the mode.

## What these scripts assume of the other lanes

- The bundle (`/opt/da-b2/bundle`, `../../score-build/`) holds `bin/launch_manager` and the serialized
  configurations `etc/launch_manager_config.bin` and `etc/launch_manager_config_path_only.bin`. These are Lifecycle
  v0.10.0's converter output of the two JSON files. B2 does not produce them yet, and the start refuses without them.
- The bundle holds `bin/identity_recorder` and, for p10-1 and p10-3, `bin/candidate_record_probe` and
  `bin/warning_injector`. These are the build-target commit of this lane.
- The Launch Manager logs the expiry of an alive supervision and the switch to `fallback_run_target` on its
  standard output. `stop_score_side.sh` copies the lines that match `expired`, `run target`, `fallback`,
  `supervision`, `SIGKILL` or `terminat` (any case). The exact wording is upstream's, and only p10-1 shows it.

## Tests

```bash
python -m pytest -q implementation/driver-assistance-bench/score-path/tests
```

`fake_launch_manager.py` reads the JSON configuration, starts the components in its order as stub processes, holds
the dependents of a Reporting component until its run log says it reported running, and stops them in reverse order on SIGTERM. It can
ignore SIGTERM, exit early, or play an expiry and the run-target switch. The fakes show the scripts' logic, not
Lifecycle's behavior.
