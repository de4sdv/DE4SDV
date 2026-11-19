# Bench sessions (INC-DRIVING-002)

Status: draft, not yet validated. Only the dry runs below have run; no session has started a VM.

## The problem

A bench run needs up to three cloud hosts in two GCP projects: the simulator host (a Spot G4 that is often
reclaimed), the S-CORE host (an L4) and the protected guest host with the AAOS SDV guests. Each costs money while it
runs, and the guests break if their host stops under them. A person driving the hosts by hand forgets a stop, starts
the expensive VM first, or stops the guest host before its guests. `da_session.sh` does it in one command, in a fixed
order, and stops everything it started on every exit.

## Session kinds

| Kind | Hosts, in start order | Steps after the starts |
|---|---|---|
| `p10-1` | S-CORE host | the S-CORE build check (`ENTRY_SCORE_P10_1`) |
| `p10-3` | S-CORE host, guest host | guests created fresh, the app and its ACLs installed and verified, VXLAN both ends, S-CORE side up (someipd offers 0x4df1 at 192.168.98.1:30511), the SD multicast route, the broker's unit registration, the app restarted, IVI clock set, display capture on, injected warning requests, capture off, S-CORE side down |
| `p10-2` | simulator host, S-CORE host, guest host | CARLA server, CARLA reachable from the S-CORE host, the guests as in `p10-3`, warm-up with the chase recorder (no candidate), ASM-DRIVING-005 and the camera capture (no candidate), the calibration file made on the lead host and put on the S-CORE host, then the ASM-DRIVING-006 run and two runs of SC-DRIVING-012 at 20 km/h, each with its own S-CORE side start and stop, recorder and display window (below) |

A `p10-1` session judges only the checks of `p10_1_check.sh` that need the S-CORE host alone. C2 to C4 (the alive
notifications, the stalled-candidate fallback, the ASIL B command path) need a ticking CARLA world
(`DA_P10_1_CARLA_HOST` and the world side's pacer), C5 needs `GATEWAYD_RX_REGEX` (a per-session setting), and C8 has
no clip replayer yet, so the check writes NOT RUN for them in such a session. After the fetch the session reads
`score/out/p10_1/p10_1_verdicts.json` and writes one line into `session.log`, and the same into `session.json`
(`p10_1`: the line, `not_run`, `fail`, `pass`, `passed`):

```text
P10-1: <n> of 8 checks NOT RUN: <ids>; FAIL: <ids>; P10-1 NOT passed
```

The FAIL part appears only when a check failed, and the line ends with "passed" in place of "NOT passed" only when
all 8 passed. A missing verdicts file counts all 8 as NOT RUN. Exit 0 of a `p10-1` session means its steps ran; it
never means that the check passed: read `p10_1.passed`.

Each run of `p10-2` (`world_run` in the script): the chase recorder (runs only), the world side spawns and writes
`ready.json`, the S-CORE side starts with the calibration file, the offer checks and the window open (runs only: the
unit, `am start -S`, the IVI clock, the capture), the go file, `run_end.json`, the S-CORE side stops while the world
still ticks, the release file, the world side and the recorder end, the capture ends. The session log's last
`SEQUENCE` line lists every step in order; `tests/test_session_dryrun.py` pins it for each kind.

The order of `p10-3` is the one the guest host's operator gave on 2026-11-18 (`guest-prep-20261118`): the VXLAN up,
the offer, the multicast route, then the broker's unit registration, then the IVI clock just before the window.
The unit check reads the SDV Core guest's log only from a mark taken just before the S-CORE side starts, so a broker
error from before the offer neither fails it nor does a registration from an earlier boot pass it. After the VXLAN
both guests' neighbour caches are flushed (they learn the S-CORE host's MAC for 192.168.98.1 at once). After each
window the session counts the lines of the app's own record in the capture (`app_record_receipts` in
`session.json`) and says `NO RECEIPT IN THE APP'S RECORD OF WINDOW <w>` when there are none: the unit check's log
pattern is still the bench's guess, and only the app's record shows that a request arrived. What the operator
confirms on the first `p10-3`: the broker's exact line for the unit in `unit_inject/core_logcat.txt`, that no line
since the mark names 4df1 as an error, `someipd`'s `REMOTE SUBSCRIBE ... [4df1.0001.0001] ... accepted` on the S-CORE
host, and the app's record and logcat lines in `capture_inject/`; then pin both patterns in the script.

Rules the script enforces (from the brief and the INC-DRIVING-001 bench):

- The simulator host starts first. Every host (all three are Spot) must still be `RUNNING` 30 s after its start; a
  reclaimed start (also one accepted with rc 0 and already `TERMINATED` at the first status read) is retried in
  rounds (45 s pauses, 30 min deadline) before the next host starts. A host found stopped while the session waits
  for its SSH ends the session as preempted (exit 3). A capacity refusal is retried; a quota or other error
  ends the session.
- One GPU per project: the session refuses to start when another GPU VM runs in a project it starts a GPU VM in.
- A VM found running before the session is not adopted: the session refuses.
- The guest host starts only with `--owner-ok-guest-host`.
- Every VM is registered for the stop before its start call. The EXIT trap stops the GPU hosts, then the guests
  (`GUEST_STOP_CMD`: `remote/guest_stop.sh`, `cvd stop` of every group; not the kit's `smoke_boot.sh`, whose image
  records are stale since 2026-11-17), then checks itself that no `crosvm` is left, retries once, and only then stops
  their host. Guests that do not stop keep their host running: the session says `GUEST HOST LEFT RUNNING` and exits
  11. It waits for `TERMINATED` and lists the VMs of both projects at the end. Nothing is created or deleted.
- The exit trap ignores INT, TERM and HUP while it runs: a second Ctrl-C, a hangup or the watchdog's TERM never ends
  it before the guest host's stop and `session.json`. A failed status read of the guest host is read again; only a
  stopped host (`TERMINATED`, `STOPPING`, `SUSPENDED`) counts as "no guests". Any other status, one still unknown
  included, gets the guests' stop, and the host stops only after the session's own `crosvm` count read 0.
- One exception, so that a guest host this session could never reach does not bill on unarmed (S1): when the session
  sent the guest host no step at all (no `guest_up`, so no guest was launched) and the host does not answer SSH in
  the trap, the trap tries SSH for up to `GUEST_NOSSH_S` (180 s) more, then stops the host without a `crosvm` count
  and says `GUEST HOST STOPPED WITHOUT A CROSVM COUNT`. This rests on one assumption: **nothing on the guest host's
  image starts Cuttlefish at boot**. The operator checks it once (the P10-3 block below). Once a guest step was sent,
  an unknown count keeps the host running, as above.
- A failure after the S-CORE side started (a failed step, a wait that timed out, a signal, the cap) first runs the
  S-CORE side's stop (`ENTRY_SCORE_STOP`, step `score_stop_on_failure`), its only collector, then fetches. A signal or
  the cap fetches every host whose files were not fetched yet, bounded (120 s pack, 300 s copy), before its stop.
  `session.json` says what ended the session (`ended_by`: `steps`, `step <name>`, `signal <SIG>`, `cap`, `fetch`, or
  the exit and its message) and which hosts were fetched (`fetched`, `not_fetched`).
- Every step runs detached on its host (`remote/host_step.sh start`) and is polled with SSH calls of at most 60 s
  (`status`, then `tail` for its last lines): a dropped connection costs one poll, not the step. A step reads
  `running` while any process of its process group lives, its leader gone or not. At a step's time-out the session
  sends the step TERM on its host and waits (6 polls) for its end before it fails; a signal or the cap during a
  step does the same in the exit trap, before the S-CORE side's stop and before any stop. So the trap's guests' stop
  never races a guest launch that still runs; a guest step still alive after its TERM keeps the guest host running
  (`GUEST HOST LEFT RUNNING`, exit 11) whatever the `crosvm` count. Only the S-CORE side's stop after a failure
  (`score_stop_on_failure`) runs in the foreground of one call (bounded in the trap).
- A poll that fails reads the host's status: a host found stopped (a Spot preemption) ends the session at once with
  exit 3; it is not fetched (`not_fetched`, `ended_by` `host lost: <role>`), and the other hosts are collected and
  fetched as after any failure.
- Every remote call whose output the session reads writes it to a file first, never through a pipe or a command
  substitution: a signal or the cap ends the session at once, not after a fetch's 20-minute copy.
- A watchdog writes `cost.log` every 30 s (an upper bound: from each start call, at the hourly prices in
  `hosts.env`) and ends the session at the cap. Each VM also gets a power-off at the cap plus 10 min, should the
  lead host lose the session (`remote/safety_net.sh`): on the GPU hosts a transient system timer that runs
  `systemctl poweroff` (not `shutdown -h +N`, whose last 5 minutes lock out a login); on the guest host a timer that
  runs `GUEST_STOP_CMD` first and powers off only when no `crosvm` is left (lead answer B13.3). The arming lists its
  timer (`systemctl list-timers`, logged); a host whose timer is not listed ends the session (exit 4) before any step.
- Every internal IP comes from gcloud at run time (`networkInterfaces[0].networkIP`) and goes into `session.json`;
  none is configured. Owner decision D5 of 2026-11-18 put the simulator host on `carla-net` (10.10.0.2 today), with
  SSH only from Google's IAP range: `SIM_SSH_IAP=1` (the default in `hosts.env`) sends every ssh and scp to that host
  with `--tunnel-through-iap`; `SIM_SSH_IAP=0` is the direct path. The S-CORE host keeps 10.164.0.5: GCP does not
  change a VM's primary internal address in place, so since 2026-11-18 the CARLA rule admits 10.164.0.5/32 instead
  of the reserved 10.164.0.20. The CARLA port check from the S-CORE host stays in every `p10-2`.
- SELinux: the guests run as they boot (Enforcing), and `getenforce` of both guests is recorded at the bring-up and
  at every window (`app_restart_<window>.txt`). The owner allowed a permissive fallback on 2026-11-18: a `p10-3`
  session runs Enforcing first; only if the Gateway lookup fails (the prepare step's `verify` reports no
  `initComms`) does the lead run the session again with `--permissive-ivi`. That sets the IVI guest permissive
  (never the SDV Core guest), and `session.json` marks every result of the session `conditional_on_permissive_ivi`.
  Each window checks the mark before the app's restart (`remote/app_restart.sh`): the SDV Core guest must read
  Enforcing, the IVI guest Enforcing, or Permissive in a `--permissive-ivi` session; any other reading fails the
  step before the window. The README's fallback stays a new session: `verify` alone could be re-run permissive on
  the same guests (the guest build script's rerun), but that would make the whole session conditional after the fact.
- The IVI clock is set just before each window and must then be within `CLOCK_MAX_OFFSET_S` (0.1 s) of the guest
  host's; a set without effect fails the step (`remote/ivi_clock.sh`, which writes its JSON under `LC_ALL=C`).
- Before any VM starts, the session builds the kit (the bench folder at `HEAD`, or as on disk with
  `--kit-from-worktree`), and checks that every entry point the kind needs is in it and executable. Each host's
  upload is checked by its sha256.
- In each run of `p10-2` the go file must follow the S-CORE side's start within `GO_LIMIT_S` (380 s, under the
  candidate's 420 s ready time-out); a later go is refused: the run is marked invalid in the log, the world side is
  sent TERM, the S-CORE side is stopped and collected, and the session ends (exit 5). Every adb call of the guest
  entries has a time-out (`ADB_TO_S`, 30 s).
- `--cap-eur` must be a positive number (exit 2 otherwise). A session id is used once: the session refuses an id
  that names any folder under the evidence root (`incoming_<id>`, or an archived `..._<id>` after rule 15's rename)
  or any `session.json` there, and a host that already holds `~/da-kit/<id>` (exit 4, before any step).
- The evidence goes into a new `incoming_<session id>/` (refused if it exists): `session.log`, `commands.log` (every
  gcloud, ssh and scp call), `cost.log`, `session.json`, `kit.tgz`, and per host `<role>/out/` with each step's log
  and status. A fetched folder whose `session_id` is not this session's fails the session.

Exit codes: 0 done; 2 refused before any start; 3 no capacity or preempted; 4 SSH or upload failed; 5 a step failed;
6 start refused; 9 dry run refused; 10 cost cap; 11 a VM left running (the guest host with its guests, or a VM not
`TERMINATED` after its stop, called again every minute of the 5-minute poll), in place of every other code;
129/130/143 signals. `session.json` keeps the code 11 replaced (`exit_code_without_left_running`), every started VM's
status after the session (`vm_status_after`) and the VMs left running (`left_running`); the session's last line names
them.

## Command lines for the lead

Run from the integrated bench tree (the other lanes' entries merged in), on the lead host. A dry run first, then the
session. Run a session detached from the terminal, its output into a file (`nohup ... > file 2>&1 &`, or
`systemd-run --user`), never behind a pipe whose reader can go away; end a background session with SIGTERM (bash
ignores SIGINT in a background job of a non-interactive shell):

```bash
cd <integrated worktree>
S=implementation/driver-assistance-bench/session
mkdir -p ~/.hermes/cache/scratch/b13-dry && export FAKE_DIR=~/.hermes/cache/scratch/b13-dry DA_GCLOUD=$PWD/$S/tests/fake_gcloud.py
bash $S/da_session.sh --kind p10-1 --dry-run --evidence-root ~/.hermes/cache/scratch/b13-dry/ev   # checks the kit
# p10-2 also needs, before any start: VP_CLONE (a VisionPilot clone holding the pin) and CV_PY with OpenCV
unset FAKE_DIR DA_GCLOUD

nohup bash $S/da_session.sh --kind p10-1 >> ~/p10-1.out 2>&1 &                       # the S-CORE build check, 2026-11-19
nohup bash $S/da_session.sh --kind p10-3 --owner-ok-guest-host >> ~/p10-3.out 2>&1 &  # the warning on the guests, Enforcing
# only if that session's guest_prepare reports no initComms (the Gateway lookup): again, marked conditional
nohup bash $S/da_session.sh --kind p10-3 --owner-ok-guest-host --permissive-ivi >> ~/p10-3.out 2>&1 &
nohup bash $S/da_session.sh --kind p10-2 --owner-ok-guest-host >> ~/p10-2.out 2>&1 &  # the first closed loop, 2026-11-20
```

Then compose the video from the fetched files (see `../recording/README.md`).

## Durations and costs

Expected lengths are PLAN's for each probe; prices from `hosts.env` (Spot, europe-west4, disks not counted).

| Kind | Hosts and EUR/h | Expected | Expected cost | Default cap (time at the cap) |
|---|---|---|---|---|
| `p10-1` | L4 0.483 | about 2 h | about EUR 0.97 | EUR 2.00 (4.1 h) |
| `p10-3` | L4 0.483 + guest host 0.271 | about 3 h | about EUR 2.26 | EUR 3.50 (4.6 h) |
| `p10-2` | G4 1.887 + L4 0.483 + guest host 0.271 | about 1.5 h | about EUR 3.96 | EUR 6.00 (2.3 h) |

Fixed overheads in every session: each start 1-3 min (more in rounds when Spot capacity is short), SSH and kit
upload about 2 min per host, the guests' bring-up 10-15 min, the fetch and the stops 2-5 min.

## Entry-point contracts

Each entry is a path relative to the bench folder (`entrypoints.env`, overridable from the environment). The session
runs it on its host detached through `remote/host_step.sh start`, with the bench folder as the working directory and `DA_OUT`,
`DA_SESSION_ID` and `DA_BENCH` set. The first argument is the step's output folder; everything the entry writes there
is fetched. Exit 0 means the step succeeded; any other status ends the session (the VMs stop).

| Variable | Host | Arguments | Owner | Contract |
|---|---|---|---|---|
| `ENTRY_SCORE_P10_1` | S-CORE | `<out>` | S-CORE build lane | the build check, the clip replay, the late subscriber; its verdicts in `<out>` |
| `ENTRY_SCORE_START` | S-CORE | `<out> <carla_host or none>`; env `DA_CAMERA_CALIBRATION_DIR` (`p10-2`) | Launch Manager lane | starts the Launch Manager with its processes (identity recorder first); copies `H.yaml` and `homography_C_matrix.yaml` from `DA_CAMERA_CALIBRATION_DIR` into the candidate's working directory before the identity record; returns 0 when they run, without waiting for a camera image (the world holds its first tick until the session's go file); called once per run, each with its own `<out>`; someipd offers 0x4df1 |
| `ENTRY_SCORE_INJECT` | S-CORE | `<out>` | warning-app lane | `p10-3`: publishes test warning requests on the candidate's mw::com event; returns when done |
| `ENTRY_SCORE_STOP` | S-CORE | `<out>` (the start's) | Launch Manager lane | ends the processes (SIGTERM, so the candidate's `.rrd` and the visualization file are finished) and collects their files; the world still ticks meanwhile |
| `ENTRY_SIM_SETUP` | simulator | `<out>` | this lane: `remote/sim_setup.sh` | CARLA server up on port 2000, NVENC test, free disk |
| `ENTRY_SIM_WARMUP` | simulator | `<out>` | `../world-side/scripts/warmup.sh` | the survey, the session's road in `world_start.json`, the warm-up pass with every camera (hero role `hero`, moved by pose) |
| `ENTRY_SIM_CALIBRATE` | simulator | `<out>` | `../world-side/scripts/calibrate.sh` | ASM-DRIVING-005 and the camera capture, role `de4sdv_calibration`, no candidate; required for `p10-2` |
| `ENTRY_SIM_RUN` | simulator | `<out> <scenario> <setting>` | `../world-side/scripts/run_scenario.sh` | one run (`SC-DRIVING-012 20kmh`, or `ASM-DRIVING-006 20kmh`), detached, with the go/release handshake (`../world-side/README.md`); its records in `<out>/simulator/` |
| `ENTRY_SIM_RECORD` | simulator | `--out <dir>` | this lane: `../recording/chase_recorder.py` | started before the warm-up and before the run, ends on its own |
| `ENTRY_GUEST_UP` | guest | `<out>` | this lane: `remote/guest_up.sh` | both guests created fresh (`launch_two_vms.sh down`, `up`) and booted; `getenforce` recorded, `setenforce 0` on the IVI only with `IVI_PERMISSIVE=1` |
| `ENTRY_GUEST_PREPARE` | guest | `<out>` | this lane: `remote/guest_prepare.sh` | the guest build script's `install` (ACLs, APK, IVI reboot) and `verify`, unchanged, as its second caller: one `B12_DIR` per session (`$AB/b12-session-<id>`), no `LOGS`, `IDENT` or `WORK`; required, since fresh guests start empty |
| `ENTRY_GUEST_APP_RESTART` | guest | `<out> <window>` | this lane: `remote/app_restart.sh` | `am start -S -W -n $APP_COMPONENT`, the APK's sha256 and both guests' `getenforce`, before each window; exit 1 when a guest's mode is not the session's mark |
| `ENTRY_GUEST_OFFER_CHECK` | guest | `route\|mark\|neigh <out>`, `unit <out> <mark>`, `receipts <capture>` | this lane: `remote/offer_check.sh` | the SD multicast route to `cvd-ebr`; the SDV Core guest's clock before each S-CORE side start (`mark`); the broker's registration of the unit in the log since that mark, negations refused (a guessed log pattern, see the script; changed per session through `UNIT_REGISTERED_RE`, `UNIT_NEGATION_RE`); both guests' neighbour caches flushed after the VXLAN (`neigh`); the lines of the app's record after each window (`receipts`) |
| `ENTRY_GUEST_CLOCK` | guest | `set <out>` | this lane: `remote/ivi_clock.sh` | IVI clock set from the guest host's, offset and bound recorded; exit 1 when the offset left is above `CLOCK_MAX_OFFSET_S` (0.1 s) |
| `ENTRY_GUEST_CAPTURE` | guest | `start\|stop <out>` | this lane: `../recording/display_capture.sh` | the display capture |
| `ENTRY_VXLAN` | guest, S-CORE | `guest-host\|host-half add <peer ip>` | this lane: `remote/cross_vm_guest_bridge.sh` | the VXLAN segment, the S-CORE host at 192.168.98.1 (INC-DRIVING-001's script, unchanged) |

Per-session settings of the remote entries: gcloud ssh does not carry the lead host's environment, so the session
passes a fixed list of names, each set in its own environment, to every step on that name's host as `env
NAME=value` before the command, logs the names and records the values in `session.json` (`remote_env`). The lists
(`REMOTE_ENV_guest`, `REMOTE_ENV_score` in `da_session.sh`): on the guest host `UNIT_REGISTERED_RE`,
`UNIT_NEGATION_RE`, `BROKER_ERROR_RE`, `UNIT_WAIT_S` (`remote/offer_check.sh`), `B12_DIR`, `VERIFY_WAIT_S`,
`ADB_TIMEOUT_S`, `UP_TIMEOUT_S` (the guest build script), `CLOCK_READS`, `CLOCK_MAX_OFFSET_S` (`remote/ivi_clock.sh`),
`START_WAIT_S` (`remote/app_restart.sh`); on the S-CORE host `DA_P10_1_CARLA_HOST`, `GATEWAYD_RX_REGEX` and the
`DA_P10_1_*` waits of `p10_1_check.sh`. A changed guess of the first `p10-3` (the broker's line, say) is then a setting
of the next session, not a commit.

`GUEST_STOP_CMD` (default `remote/guest_stop.sh` in the kit) stops the guests; the session then counts `crosvm` on the
guest host itself and never stops the host while one is left.

The app's values come from the app (`APP_PACKAGE`, `APP_COMPONENT`: `../ivi-warning-app/app/AndroidManifest.xml`;
`APP_RECORD_PATHS`: `WarningRecord.java`'s `files/warning.jsonl` under `/data/user/@user@/<package>/`, the IVI's
current user read at the capture). The session passes them to the guest entries; a test checks them against the
manifest and the code.

## Tests

`tests/test_session_dryrun.py` runs the real script with `--dry-run` against `tests/fake_gcloud.py`, a stateful fake
that logs every call: the full step sequence of each kind, the start order and the 30 s check and a reclaimed G4,
capacity rounds, a quota error, a failed step, the cost cap, SIGTERM, the guests stopped before their host and a
host kept running when they do not stop, the guest host's safety net, IAP on and off, IPs read from gcloud, the
calibration file on the S-CORE host before every start, the refusals (no owner OK, a running VM, another GPU VM, a
missing or non-executable entry, no calibrate or prepare entry, the pin missing from `VP_CLONE`, an existing session
folder, a real gcloud in a dry run, dry-run knobs in a real session), a foreign fetch, and that the dry run prints
every call. `tests/test_remote_scripts.py` runs the guest-host scripts and the safety net against fake `cvd`,
`adb`, `pgrep`, `sudo` and `ip`. The stubs in `tests/stubs/` stand for the S-CORE side's entries (another lane's)
and for `make-h` in dry runs; they never run on a host.

What the dry runs cannot show, and the sessions must: the real SSH and scp paths (IAP included) and their times, the
gcloud output formats the fake imitates, the VXLAN between the S-CORE host and the guest host, the CARLA port from
the S-CORE host to the simulator host on `carla-net` (brief R5, D5), the broker's log line for the unit's
registration, that the S-CORE side's start returns before the first image, the systemd timer of the guest host's
safety net, and the real costs.
