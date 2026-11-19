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
| `p10-1` | simulator host, S-CORE host | CARLA server, the port test (CARLA's tcp 2000-2002 from the S-CORE host), the session's road (the warm-up entry's survey and pass, no recorder), the world spawned (`ready.json`), the go, the S-CORE build check (`ENTRY_SCORE_P10_1`) with `DA_P10_1_CARLA_HOST` set to the simulator host, `run_end.json`, the release, the world side's end |
| `p10-3` | S-CORE host, guest host | guests created fresh, the app and its ACLs installed and verified, VXLAN both ends, S-CORE side up (someipd offers 0x4df1 at 192.168.98.1:30511), the SD multicast route, the IVI app's subscription to the unit (its own `link=SUBSCRIBED` line), the app restarted, IVI clock set, display capture on, injected warning requests, capture off, S-CORE side down |
| `p10-2` | simulator host, S-CORE host, guest host | CARLA server, CARLA reachable from the S-CORE host, the guests as in `p10-3`, warm-up with the chase recorder (no candidate), ASM-DRIVING-005 and the camera capture (no candidate), the calibration file made on the lead host and put on the S-CORE host, then the ASM-DRIVING-006 run and two runs of SC-DRIVING-012 at 20 km/h, each with its own S-CORE side start and stop, recorder and display window (below) |

C1's full configuration needs a CARLA 1.0 server: the real `vision_pilot` and `actuation_adapter` exit at once on a
refused CARLA connection (S-CORE build session 5 on the L4, 2026-11-19). Without `DA_P10_1_CARLA_HOST`, or when its
port 2000 does not answer, `p10_1_check.sh` never starts it, and C1 is NOT RUN with that reason and its path part's
result (FAIL when the path part failed). C2 to C4 (the alive notifications, the stalled-candidate fallback, the ASIL B
command path) need a ticking CARLA world. So a `p10-1` session also starts the simulator host (owner's approval of
2026-11-19) and runs the check while the world ticks: the world side's handshake of a `p10-2` run, with the go
before the check (the world ticks through its three parts, the full start in the third) and the release only after
the check ended, so the check stops its own Launch Manager starts while the world still ticks. The world side holds
(ticks) after `run_end.json` until the release file or `RELEASE_WAIT_S`, which the session sets above the check's
bound (`T_P10_1` plus 5 min). The session sets `DA_P10_1_CARLA_HOST` itself, to the simulator host's internal address
read from gcloud (or `--carla-host`); it is not a `--remote-env` setting and never comes from the caller's shell.
Before the warm-up, the port test connects from the S-CORE host to CARLA's tcp 2000, 2001 and 2002 (5 s each) and
logs one `PORT TEST` line; a closed port ends the session (exit 5, `failed_step` `port_test`) before any Launch
Manager start. No warm-up lap is judged: the warm-up entry runs because its survey writes the session's road
(`world_start.json`), without which `run_scenario.sh` refuses; its pass with the hero moved by pose takes well under a
minute. No calibration: p10-1 judges no geometry, so the check's own stand-in (upstream's `H.yaml` from the bundle,
named as such in `p10_1_calibration/SOURCE.txt`) stays, and the session spends no `calibrate` step and no `make-h`.
C5 needs a receive line of `gatewayd`, which prints none per received sample (session 5: only its offer lines), so it
stays NOT RUN and `p10-3` judges the receipt on the guest. C8 has no clip replayer yet. After the fetch the session
reads
`score/out/p10_1/p10_1_verdicts.json` and writes one line into `session.log`, and the same into `session.json`
(`p10_1`: the line, `not_run`, `fail`, `pass`, `passed`):

```text
P10-1: <n> of 8 checks NOT RUN: <ids>; FAIL: <ids>; P10-1 NOT passed
```

The FAIL part appears only when a check failed, and the line ends with "passed" in place of "NOT passed" only when
all 8 passed. A missing verdicts file counts all 8 as NOT RUN. Exit 0 of a `p10-1` session means its steps ran; it
never means that the check passed: read `p10_1.passed`.

The best a p10-1 session can read is not a pass. C5 (no receive line of `gatewayd`) and C8 (no clip replayer) are
NOT RUN in every p10-1, so a clean paid session ends with exit 0 and this line, the expected best outcome:

```text
P10-1: 2 of 8 checks NOT RUN: C5_gatewayd_receives_from_asil_b_process, C8_candidate_on_a_replayed_clip; P10-1 NOT passed
```

A check that FAILs is the check's result, not a failed step: `p10_1_check.sh` exits 1, and the session still waits
for `run_end.json`, releases the world, waits for the world side's end, logs its `SEQUENCE` line and fetches both
hosts, then exits 12. Any other exit of the check is a failed step (exit 5). The check starts its own Launch Manager
with `setsid`, which the step's TERM does not reach. A cut (a signal, the cap, or the step's time-out `T_P10_1`)
therefore runs the check's own handler: it stops and collects the open start into `p10_1/path/` or `p10_1/full/`
(`score_side/`), bounded, and writes `p10_1_verdicts.json` with the verdicts judged so far and the rest NOT RUN, the cut
named (`cut` in the file, and "the check was cut by ..." in the line). The session marks the S-CORE side up during
the step, so its trap also runs the stop, into `p10_1/trap_stop/`. `stop_score_side.sh` runs one stop of a stage at a
time, so the second stop finds nothing running and only collects. On every trap or abort path a world side that has
not ended gets its release file and then a TERM, after the S-CORE side's stop and before the simulator host's fetch
(`p10-2` runs too).

`T_P10_1` is 2400 s: the check's longest run from its own defaults is about 1990 s (part 1: staging and start 180 s,
the late subscriber's probe 60 s, the test publisher about 40 s, C5's wait 5 s, the stop about 90 s; part 2: 3
networks at `DA_P10_1_ORT_TIMEOUT_S` 300 s each; part 3: the port probe 10 s, staging and start 180 s, the
supervised wait 420 s, the alive hold 10 s, the stall hold 3 s, the stop about 90 s), plus a margin of about 20 %.
With every step before it at its own bound (`sim_setup` 1200 s, the port test's call 60 s, `warmup` 900 s,
`ready.json` 300 s), the step's time-out and its TERM wait (6 polls of 20 s) end within 4980 s, before the cap's
5316 s of both hosts (EUR 3.50 at 1.887 + 0.483 EUR/h). Past that point the S-CORE side's stop and the fetches may
run into the cap; the exit trap then holds each at its bound within p10-1's pre-stop budget of 1560 s ("The exit
trap's pre-stop budget"). `tests/test_p10_1_bounds.py` checks both from the scripts' defaults.

Each run of `p10-2` (`world_run` in the script): the chase recorder (runs only), the world side spawns and writes
`ready.json`, the S-CORE side starts with the calibration file, the offer checks and the window open (runs only: the
unit, `am start -S`, the IVI clock, the capture), the go file, `run_end.json`, the S-CORE side stops while the world
still ticks, the release file, the world side and the recorder end, the capture ends. The session log's last
`SEQUENCE` line lists every step in order; `tests/test_session_dryrun.py` pins it for each kind.

The order of `p10-3` is the one the guest host's operator gave on 2026-11-18 (`guest-prep-20261118`): the VXLAN up,
the offer, the multicast route, then the unit gate, then the IVI clock just before the window. Before the S-CORE
side starts, the session marks both guests' clocks (`logmark_<w>`), each on its own clock: the SDV Core guest's into
`logcat_since.txt`, the IVI guest's into `ivi_logcat_since.txt`. The unit gate (`unit_<w>`) then reads each guest's
log only since its own mark, so neither a broker error from before the offer fails it nor a line from an earlier
boot or run passes it. After the VXLAN both guests' neighbour caches are flushed (they learn the S-CORE host's MAC
for 192.168.98.1 at once). Before each window `remote/app_restart.sh` restarts the app (`am start -S -W`) and waits
up to `APP_SUBSCRIBE_WAIT_S` (30 s) for the new process's own `phase=link link=SUBSCRIBED` line, read by its pid in
the IVI log since an IVI-clock mark taken right before `am start`: the restart kills the process the unit gate saw
subscribe. The new pid's last link line decides (a later `WAITING` or `UNAVAILABLE` means the link dropped, so it waits
on); `UNAVAILABLE` lines are counted and named, never decisive; at the bound the step fails with the new pid's link
lines. After each window the session counts the receipt events of the app's own record in the capture: the lines whose
`"event"` is `"receipt"` after the window's app start (the start line of the pid `app_restart.sh` read), never the
record's lines, since the record is appended and every app start writes lifecycle, link and status lines
(`app_record_receipts` in `session.json`). It says `NO RECEIPT IN THE APP'S RECORD OF WINDOW <w>` when there are none:
only the app's record shows that a request arrived. The same count serves `p10-3` and each recorded `p10-2` run.

### The display capture of a window

A window's capture runs from `window_open` (after the app restart and the IVI clock) to `window_close`. The session
keeps the open window, and when it ends inside one (an abort: no `run_end.json`, a failed S-CORE stop, the world
side or the recorder; a signal; the cost cap), it first runs `display_capture.sh stop` for that window, then the
S-CORE side's stop, then the fetches, and only then stops the guests. So the recording gets its SIGINT and its pull,
and the app's records and `capture.json` are written before the guest host is packed. That stop is bounded by
`T_CAPTURE_END`, and in the exit trap by what the pre-stop phase leaves. Its step is `capture_down<n>_<w>`
(`guest.steps.out`).

A capture that ends with `end: error` (no answer from the guest for `ALIVE_UNKNOWN_S`, or two early ends) has
written `capture.done`, its app records and `capture.json`, and exits 1. The session logs `DISPLAY CAPTURE ERROR IN
WINDOW <w>`, still reads the window's receipts, and goes on to the next run. Any other bad end of the capture
(no `capture.done`, another code) still ends the session with exit 5.

`session.json` keeps each window's capture in `display_capture`: `end` (from `capture.done`), `capture_rc`,
`closed_by` (`window close`, or `session end` for the stop above) and `guest_files_kept`. For `p10-2`, `p10_2`
says whether the display recording is complete: `display_recording_complete` is true only when every recorded run's
capture ended `stop` at its window's close with rc 0 and nothing kept on the guest; otherwise `reason` names each
window and what was wrong. With `--without-guest-host` it is null (no display capture). Exit 0 alone never means the
recording is complete.

The session passes the capture two caps derived from its own bounds (`display capture caps:` in `session.log`).
`--wait-cap-s`, the stop's cap, fits `capture_stop`'s bound:

```text
T_CAPTURE_END                                                240 s
- rstep's start SSH call (its time-out)                       60 s
- the stop's own last poll and exit                            2 s
- one status poll's SSH call that read "running" (time-out)   60 s
- POLL_S                                                      20 s
= --wait-cap-s                                                98 s
```

`--max-s` is the longest window that ends well, every step inside it at its bound: an rstep counts its start SSH call
(60 s), its bound, POLL_S, one poll (60 s) and its tail call (60 s); an rwait or rwaitfile its bound, POLL_S and one
poll; a touch its SSH bound. A step past its bound aborts the session, and the stop above then ends the capture.

```text
the go file (GO_SSH_S)                                        35 s
run_end.json (T_RUN 900 + 20 + 60)                           980 s
score_stop_<w> (60 + T_SCORE_START 900 + 20 + 60 + 60)      1100 s
the release file (its SSH bound)                              60 s
the world side's end (T_RELEASE 400 + 20 + 60)               480 s
the recorder's end (T_REC_END 200 + 20 + 60)                 280 s
capture_stop_<w>'s start SSH call                             60 s
= --max-s of a p10-2 window                                 2995 s

inject (60 + T_INJECT 1200 + 20 + 60 + 60)                  1400 s
capture_stop_inject's start SSH call                          60 s
= --max-s of the p10-3 window                               1460 s
```

A typical p10-2 window lasts 70 to 230 s, so the capture reaches its `--max-s` only when steps run near their bounds.
At 2995 s the capture records up to 18 segments of 170 s; the guest space this needs is in recording/README.md
("The guest's space").

### The unit gate of `p10-3` (and of each recorded `p10-2` run)

What it waits for (`remote/offer_check.sh unit`, `UNIT_SOURCE=app`, the default): the IVI app's own line
`DE4SDV_COLLISION_WARNING: event=lifecycle ... phase=link link=SUBSCRIBED detail="<vm>"`, which the app writes once
its continuous discovery listener (`addListenerForServiceUnitChangeByName`) has seen the broker's unit
`de4sdv-driving-warning-request` and its subscription succeeded. The app subscribes to that one unit only. It waits
up to `UNIT_WAIT_S` (120 s), polling every 5 s, and logs the bound, the source and both marks in its first line.
The last link line since the IVI mark decides, whatever the poll that reads it: `link=SUBSCRIBED` passes
(`UNIT_SUBSCRIBED <unit> source=app`); a later `link=WAITING` or `link=UNAVAILABLE` says the link dropped, so the gate
waits on. At the bound with no link line since the mark, the FAIL line also names the app's last link line before the
mark (a naming problem is logged once, at the app's start). `link=UNAVAILABLE` never decides: the app logs it for every failed
`initComms`, subscribe or read and retries after 5 s (`RETRY_DELAY_MS` in `WarningRequestSubscriber.java`), so the gate
counts those lines, names the last one's detail, and keeps waiting for `link=SUBSCRIBED` up to its bound; `link=WAITING`
keeps waiting too. Until 2026-11-19 the gate failed at once on the first `UNAVAILABLE`; that was changed before the
`p10-3` rerun, because a first subscribe that the app retries would then fail a paid run. The one `UNAVAILABLE` the app
does not retry, a naming problem in its own configuration, also fails only at the bound. A broker error line in the core
log since the core mark that names 4df1 or the unit still fails the gate
(`BROKER_ERROR_RE`). `UNIT_SOURCE=core` (only through `--remote-env UNIT_SOURCE=core`) keeps the earlier gate: a core
log line naming the unit and matching `UNIT_REGISTERED_RE`, negations refused.

Why the app's line (T6 of the `p10-3` record of 2026-11-19, session `20261119T094924Z`): the SDV Core guest's broker
logs no line naming the unit at its default log level. The core log since the mark held 867 lines and none named
`de4sdv-driving-warning-request`, so the earlier gate could not pass whatever its pattern. The S-CORE-to-core leg
did work in that log: the core's `sdv_someip_stack_agent` logged `create_remote_client: 192.168.98.1:30511 reliable`,
`REGISTER EVENT(1221): [4df1.0001.8001:is_provider=false]` and `SUBSCRIBE(1221): [4df1.0001.0001:8001:1]`, and the
S-CORE host's someipd logged `REMOTE SUBSCRIBE(0000): [4df1.0001.0001] from 192.168.98.3:4190 reliable was
accepted.` The core-to-IVI leg was never read: the IVI app's last line, before the S-CORE side was up, was
`link=WAITING`. The app's own link line is the readiness signal of that leg.

How to read the gate's files (`guest/out/unit_<w>/` in the session's evidence folder, fetched with the guest host):

- `unit_context.txt`, kept on a pass and on a fail: the core's `REGISTER EVENT` and `SUBSCRIBE` lines for 4df1 (the
  S-CORE-to-core leg) and the app's link lines (the core-to-IVI leg). Both legs belong in the run's record.
- `core_logcat.txt`, `ivi_logcat.txt`, `app_link_lines.txt`, `broker_errors.txt`: the last poll's reads since the
  marks; `logcat_since.txt` and `ivi_logcat_since.txt` name the marks.
- `diag/`, written on any fail before the step exits, and listed with line counts in the step's `DIAGNOSTICS` line:
  `ivi_collision_warning_since_boot.txt` (every app line since the IVI booted, so a `link=UNAVAILABLE` or a restart
  before the mark shows too), `ivi_sdv_service_manager_broker_mesh.txt` (the IVI's `SdvServiceManager`,
  `SomeIpBroker` and mesh lines), `core_sdv_service_manager_since_mark.txt`, `core_someip_service.txt` (the core's
  someip lines naming 4df1), and `net_core.txt`, `net_ivi.txt` (`ip -br addr`, `ip route`, `ip rule` and the
  addresses in each network namespace, the `sd_mesh_ns` mesh address included). `ivi_logcat_since_boot.txt` is the
  whole IVI buffer they come from.

Reading a fail: no `REGISTER EVENT`/`SUBSCRIBE` for 4df1 in `unit_context.txt` means the offer did not reach the
core (the multicast route, the VXLAN, someipd); those lines present with the app still `WAITING` means the unit did
not reach the IVI (the mesh between the guests, the broker's registration, the app's discovery); `UNAVAILABLE` names
the app's own failing call. The core's `SdvServiceManagerServer` logged a reconnect loop to `instance3`
(192.168.99.5:2000, `Unable to connect to mesh`) about every 9 s in that session. Our two guests are dev-mesh
instance1 (the SDV Core guest, `androidboot.virt.address=3`) and instance2 (the IVI guest, `sdv_ivi_instance2`,
`androidboot.virt.address=4`, its `sd_mesh` address 192.168.99.4 in the bench's guest inventory); no third guest
runs, so the `instance3` loop alone says nothing about the IVI. Whether the core's mesh link to instance2 was up is
not in that log (no line names instance2 after the mark); the IVI's mesh lines and both guests' namespace addresses
in `diag/` answer it at the next fail.

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
  image starts Cuttlefish at boot**, so no guest runs before the session starts one. Every session checks that
  assumption: `guest_up` counts `crosvm` before its launch, and the session logs `crosvm processes on the guest host
  before guest_up: <n>` (`crosvm_before_guest_up` in `session.json`; `S1 VOID: ...` when a guest was found running,
  `unknown` when the count failed). Once a guest step was sent, an unknown count keeps the host running, as above.
- A failure after the S-CORE side started (a failed step, a wait that timed out, a signal, the cap) first runs the
  S-CORE side's stop (`ENTRY_SCORE_STOP`, step `score_stop_on_failure`), its only collector, then fetches. A signal or
  the cap fetches every host whose files were not fetched yet (120 s pack, 300 s copy at most), before its stop.
  The trap's whole pre-stop phase (the running step's end, the open window's capture stop, the S-CORE side's stop,
  the world side's end, the fetches) is bounded at `PRESTOP_S`, the kind's pre-stop budget (below): a host it cannot
  fetch within it is stopped unfetched (`not_fetched`; its files stay on its disk). A GPU host with nothing left to collect or fetch (no kit on it, or already fetched) stops first, at the
  start of the trap. A fetch the signal interrupted is not tried again and is named in `not_fetched`.
  An S-CORE side's stop that exits 7 (`stop_score_side.sh`: stopped and collected, something had to be killed) is
  no failure: `session.log` says so, and `session.json` records every stop per run (`score_stops`: `step`, `rc`,
  `stop_killed`). In `p10-2` such a stop with another run to come ends the session after that run (exit 5): the
  next run would start from a suspect state while every VM bills. Exit 8 (collection failed) fails the session.
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
  `hosts.env`) and ends the session at the cap. Each VM also gets a power-off at the cap plus the trap's pre-stop bound
  (the kind's pre-stop budget, below) plus 10 min, counted from its arming, should the
  lead host lose the session (`remote/safety_net.sh`): on the GPU hosts a transient system timer that runs
  `systemctl poweroff` (not `shutdown -h +N`, whose last 5 minutes lock out a login); on the guest host a timer that
  runs `GUEST_STOP_CMD` first and powers off only when no `crosvm` is left (lead answer B13.3). The arming lists its
  timer (`systemctl list-timers`, logged); a host whose timer is not listed ends the session (exit 4) before any step.
- Every internal IP comes from gcloud at run time (`networkInterfaces[0].networkIP`) and goes into `session.json`;
  none is configured. Owner decision D5 of 2026-11-18 put the simulator host on `carla-net` (10.10.0.2 today), with
  SSH only from Google's IAP range: `SIM_SSH_IAP=1` (the default in `hosts.env`) sends every ssh and scp to that host
  with `--tunnel-through-iap`; `SIM_SSH_IAP=0` is the direct path. The S-CORE host keeps 10.164.0.5: GCP does not
  change a VM's primary internal address in place, so since 2026-11-18 the CARLA rule admits 10.164.0.5/32 instead
  of the reserved 10.164.0.20. The CARLA port check from the S-CORE host stays in every `p10-2`, and every `p10-1`
  has its port test of tcp 2000-2002.
- SELinux: the SDV Core guest runs as it boots (Enforcing). A `p10-3` session runs with `--permissive-ivi` from its
  start (the lead's decision of 2026-11-19): B12's Enforcing run on the same images failed the IVI app's Gateway
  lookup (`ISdvGateway/default not declared`), so an Enforcing `p10-3` would only cost a session. The option sets the
  IVI guest permissive (never the SDV Core guest), every result of the session is conditional on a permissive IVI,
  and `session.json` says so (`conditional_on_permissive_ivi`). `getenforce` of both guests is recorded per run: at
  the bring-up (`guest_identity.txt`) and at every window (`app_restart_<window>.txt`). Each window checks the mark
  before the app's restart (`remote/app_restart.sh`): the SDV Core guest must read Enforcing, the IVI guest
  Permissive in a `--permissive-ivi` session (Enforcing without the option); any other reading fails the step before
  the window. A session without `--permissive-ivi` (both guests Enforcing) stays the default only for a later
  re-test on new images.
- The IVI clock is set just before each window and must then be within `CLOCK_MAX_OFFSET_S` (0.1 s) of the guest
  host's; a set without effect fails the step (`remote/ivi_clock.sh`, which writes its JSON under `LC_ALL=C`).
- Before any VM starts, the session builds the kit (the bench folder at `HEAD`, or as on disk with
  `--kit-from-worktree`), and checks that every entry point the kind needs is in it and executable. Each host's
  upload is checked by its sha256.
- In each run of `p10-2` the go file must follow the S-CORE side's start within `GO_LIMIT_S` (380 s, under the
  candidate's 420 s ready time-out). The clock starts before the start step's own SSH call, since the candidate's
  time-out runs from its process start inside that step; the 40 s left are for the go's own SSH call (IAP to the G4,
  at most `GO_SSH_S`, 35 s). A later go is refused: the run is marked invalid in the log, the world side is
  sent TERM, the S-CORE side is stopped and collected, and the session ends (exit 5). Every adb call of the guest
  entries has a time-out (`ADB_TO_S`, 30 s).
- `--cap-eur` must be a positive number (exit 2 otherwise). A session id is used once: the session refuses an id
  that names any folder under the evidence root (`incoming_<id>`, or an archived `..._<id>` after rule 15's rename)
  or any `session.json` there, and a host that already holds `~/da-kit/<id>` (exit 4, before any step).
- The evidence goes into a new `incoming_<session id>/` (refused if it exists): `session.log`, `commands.log` (every
  gcloud, ssh and scp call), `cost.log`, `session.json`, `kit.tgz`, and per host `<role>/out/` with each step's log
  and status. A fetched folder whose `session_id` is not this session's fails the session.

Exit codes: 0 done; 2 refused before any start; 3 no capacity or preempted; 4 SSH or upload failed; 5 a step failed;
6 start refused; 9 dry run refused; 10 cost cap; 12 a p10-1 check FAILed (every step ran, the world was released and
both hosts fetched; `p10_1.fail` names the checks); 11 a VM left running (the guest host with its guests, or a VM not
`TERMINATED` after its stop, called again every minute of the 5-minute poll), in place of every other code;
129/130/143 signals. `session.json` keeps the code 11 replaced (`exit_code_without_left_running`), every started VM's
status after the session (`vm_status_after`) and the VMs left running (`left_running`); the session's last line names
them.

## Command lines for the lead

Rules behind every block, from the second review of the session runner (S3, S4):

- Run from a detached worktree pinned to the integration commit under test: the kit is `git archive HEAD` of it.
- Start every session, the dry runs too, from a clean environment (`env -i`). An exported `UNIT_WAIT_S`, `B12_DIR`,
  `ADB`, `ENTRY_*`, `GUEST_STOP_CMD` or `DA_T_*` of the shell never reaches the session; a per-session setting of a
  remote entry goes only through `--remote-env NAME=VALUE`.
- Run the session in a user unit that never SIGKILLs its exit trap: `KillMode=mixed`, `TimeoutStopSec=infinity`,
  `SendSIGHUP=no`. The trap needs far longer than systemd's default 90 s stop time-out: the running step's TERM
  and its end, the S-CORE side's stop and the fetch (bounded together at 5 min), the guests' stop (up to 2 x 5 min),
  then the stop polls (5 min per VM). Not `nohup ... &` (the lead's terminal tool refuses it, and a tool-tracked
  background job dies with the agent), not a plain `systemd-run --user`, not `timeout -k`.
- End a session early only with SIGTERM to its main process. **Never `kill -9` a session**, and never use a launcher
  that SIGKILLs at a stop time-out: a SIGKILL skips the trap, leaves the VMs running and writes no `session.json`.
- Linger is on for the lead's user (`loginctl show-user mrk -p Linger` gives `Linger=yes`), so the unit outlives the
  lead's login.

Once, before the first real session, read-only: the real gcloud works from a clean environment.

```bash
env -i HOME="$HOME" PATH=/usr/bin:/bin ~/google-cloud-sdk/bin/gcloud --configuration=de4sdv-gcp config list
```

### `p10-1` (the simulator host and the S-CORE host)

```bash
# one detached worktree at the integration commit under test
C=FULL_SHA_OF_THE_COMMIT_UNDER_TEST      # replace: the integration commit under test
git -C /home/mrk/de4sdv-worktrees/da-integration worktree add --detach /home/mrk/de4sdv-worktrees/p10-$C $C
cd /home/mrk/de4sdv-worktrees/p10-$C || exit 1
S=implementation/driver-assistance-bench/session
# a dry run first, with the tests' fake gcloud (the fake's state in its own folder)
D=$HOME/.hermes/cache/scratch/b13-dry-$(date -u +%H%M%S); mkdir -p "$D"
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin FAKE_DIR="$D" DA_GCLOUD="$PWD/$S/tests/fake_gcloud.py" \
  bash $S/da_session.sh --kind p10-1 --dry-run --evidence-root "$D/ev"; echo "dry run rc=$?"   # expect 0
# the session: a user unit that never SIGKILLs the trap, a clean environment, its own output file
SID=$(date -u +%Y%m%dT%H%M%SZ)
systemd-run --user --unit=da-session-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/p10-1-$SID.out -p StandardError=append:$HOME/p10-1-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin \
  /bin/bash $S/da_session.sh --kind p10-1 --session-id "$SID"
# follow:  tail -f ~/.hermes/outputs/inc-driving-002/phase10/sessions/incoming_$SID/session.log
# end it early, if ever: systemctl --user kill --kill-who=main -s TERM da-session-$SID   (never kill -9)
# done when: systemctl --user is-active da-session-$SID prints "inactive"; then read session.json:
#   exit_code (11 = a VM is left running: stop it by hand at once), p10_1.line, p10_1.passed
```

### `p10-3` (the S-CORE host and the protected guest host, IVI permissive)

```bash
C=FULL_SHA_OF_THE_COMMIT_UNDER_TEST      # replace: the same integration commit as for p10-1
cd /home/mrk/de4sdv-worktrees/p10-$C || exit 1   # the same pinned worktree as for p10-1
S=implementation/driver-assistance-bench/session
D=$HOME/.hermes/cache/scratch/b13-dry-$(date -u +%H%M%S); mkdir -p "$D"
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin FAKE_DIR="$D" DA_GCLOUD="$PWD/$S/tests/fake_gcloud.py" \
  bash $S/da_session.sh --kind p10-3 --owner-ok-guest-host --permissive-ivi --dry-run --evidence-root "$D/ev"; echo "dry run rc=$?"
SID=$(date -u +%Y%m%dT%H%M%SZ)
systemd-run --user --unit=da-session-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/p10-3-$SID.out -p StandardError=append:$HOME/p10-3-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin \
  /bin/bash $S/da_session.sh --kind p10-3 --owner-ok-guest-host --permissive-ivi --session-id "$SID"
# every result is conditional on the permissive IVI (the lead's decision of 2026-11-19); getenforce is recorded per run
# a per-session setting only on purpose, as an option, e.g. after the kind:
#   --remote-env UNIT_WAIT_S=300   (the unit gate's bound; its step bound follows: UNIT_WAIT_S + 240 s;
#   --remote-env UNIT_SOURCE=core: the earlier core-log gate)
# end it early: systemctl --user kill --kill-who=main -s TERM da-session-$SID   (or systemctl --user stop; never kill -9;
#   the trap TERMs the running step first and waits for its end, a guest launch included, before any stop)
# after it: exit_code 11 or "GUEST HOST LEFT RUNNING" in session.log = the guest host bills; follow the log's line
# exit 0 alone is not a pass (it means the steps ran): read p10_3.passed and p10_3.reason in session.json
#   (app_record_receipts.inject > 0: receipt events since the window's app start), conditional_on_permissive_ivi (true), and step_ended_by_term after an early end
```

Once, at the first `p10-3`, while the guest host runs (after `session.log` shows its `kit ok` line), the operator checked
the assumption behind the stop of a guest host that got no guest step and never answered SSH (S1): nothing on the
guest host's image starts Cuttlefish at boot. On the guest host:

```bash
systemctl list-unit-files | grep -i -E 'cvd|cuttlefish'
```

The answer of session `20261119T094924Z` (2026-11-19):

```text
cuttlefish-host-resources.service      generated       -
cuttlefish-operator.service            generated       -
```

`generated` units are made at boot by systemd's SysV generator from the packages' `/etc/init.d` scripts. Upstream
at the host's packages' tag (android-cuttlefish `v1.51.0`: `base/debian/cuttlefish-base.cuttlefish-host-resources.init`,
`frontend/debian/cuttlefish-user.cuttlefish-operator.init`), `cuttlefish-host-resources` enables IP forwarding and
creates the bridges `cvd-ebr` and `cvd-wbr`, the tap devices and their `dnsmasq`, and `cuttlefish-operator` starts
the WebRTC signalling server (`/usr/lib/cuttlefish-common/bin/operator`). Neither script calls `cvd`, `launch_cvd`,
`run_cvd` or `crosvm`: they prepare host networking and the operator for a guest, and start none. So the answer
does not void S1, but it is read from the upstream sources, not from the copies installed on the guest host, and a
unit list cannot show every way a guest could start. That is why every session now counts `crosvm` before
`guest_up` (above): a guest running before the session started one shows as `S1 VOID` in `session.log`, and then
tell the lead before the next session and do not rely on the stop without a count. An `enabled` unit that runs
`cvd` voids the assumption the same way.

### `p10-2` (all three hosts)

A `p10-2` session runs with `--permissive-ivi` from its start (the lead's decision of 2026-11-19, as for `p10-3`):
its unit gate and `app_restart` wait for the IVI app's own `phase=link link=SUBSCRIBED` line, and the app's Gateway
lookup fails under Enforcing on these images (SELinux, above). Every result of the session is conditional on a
permissive IVI: `session.json` says so (`conditional_on_permissive_ivi`, also in its `p10_2` report), and so must
every write-up of it.

```bash
C=FULL_SHA_OF_THE_COMMIT_UNDER_TEST      # replace: the integration commit under test
# --permissive-ivi: every result of the session is conditional on a permissive IVI (the lead's decision of 2026-11-19)
cd /home/mrk/de4sdv-worktrees/p10-$C || exit 1
S=implementation/driver-assistance-bench/session
# the dry run needs the VisionPilot clone at the pin (VP_CLONE, default ~/de4sdv-upstream/vision_pilot); make-h is
# the tests' stand-in there (the fake's capture files are no images); the session itself checks CV_PY's OpenCV
D=$HOME/.hermes/cache/scratch/b13-dry-$(date -u +%H%M%S); mkdir -p "$D"
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin FAKE_DIR="$D" DA_GCLOUD="$PWD/$S/tests/fake_gcloud.py" \
  DA_MAKE_H="$PWD/$S/tests/stubs/make_h.sh" \
  bash $S/da_session.sh --kind p10-2 --owner-ok-guest-host --permissive-ivi --dry-run --evidence-root "$D/ev"; echo "dry run rc=$?"
SID=$(date -u +%Y%m%dT%H%M%SZ)
systemd-run --user --unit=da-session-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/p10-2-$SID.out -p StandardError=append:$HOME/p10-2-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin \
  /bin/bash $S/da_session.sh --kind p10-2 --owner-ok-guest-host --permissive-ivi --session-id "$SID"
# end it early: systemctl --user kill --kill-who=main -s TERM da-session-$SID   (never kill -9)
```

Then compose the video from the fetched files (see `../recording/README.md`).

### The exit trap's pre-stop budget

On a signal or the cost cap, the exit trap runs these steps before any VM stops, each in a slot of its own bound. A
slot never reaches into the time the later slots reserve (the sum of their bounds), and every call inside a slot (the
status reads after a failed poll and the sleeps between polls too) is cut to what the slot has left, so a step that
runs to its bound never takes a fetch's time: an earlier step's overrun of a second or two shortens the next earlier
step, never a fetch. The pre-stop phase (`PRESTOP_S`) is the sum of the
slots of the kind's hosts (`pre-stop budget:` in `session.log`):

- the running step's end: its TERM's call (60 s), `STEP_TERM_POLLS` waits of `POLL_S` (6 of 20 s), the last poll
  (60 s) and its tail (60 s): 300 s;
- the open window's capture stop (guest kinds): `T_CAPTURE_END` (240 s), then its status poll (60 s): 300 s;
- the S-CORE side's stop: `TRAP_SCORE_S`, 120 s;
- the world side's end (simulator kinds): its release and TERM call (60 s), then 3 polls of 60 s and `POLL_S`: 300 s;
- each host's fetch: `TRAP_PACK_S` (120 s) to pack and `TRAP_SCP_S` (300 s) to copy: 420 s per host.

| Kind | Pre-stop budget | Its parts (step, capture, score, world, fetch) |
|---|---|---|
| p10-1 | 1560 s | 300 + 0 + 120 + 300 + 2 x 420 |
| p10-3 | 1560 s | 300 + 300 + 120 + 0 + 2 x 420 |
| p10-2 with the guest host | 2280 s | 300 + 300 + 120 + 300 + 3 x 420 |
| p10-2 --without-guest-host | 1560 s | 300 + 0 + 120 + 300 + 2 x 420 |

`tests/test_session_dryrun.py` checks these sums against the script's defaults and pins a dry run in which the
capture's stop and the S-CORE side's stop both run to their bounds and the guest host is still fetched before the
guests' stop. The cost watchdog still ends the session at the cap; each VM's safety net fires at the cap plus the
kind's budget plus 10 min, counted from its arming, so it never cuts the phase. At its bounds the phase costs, past
the cap, about EUR 1.03 in p10-1 (2.37 EUR/h), EUR 0.33 in p10-3 (0.754 EUR/h), EUR 1.67 in p10-2 (2.641 EUR/h)
and EUR 1.03 in p10-2 without the guest host. One limit remains: a gcloud status read after a failed poll
(`TRAP_GC_TO_S`, 30 s) can run past its slot's end; the safety net's 10 min margin holds it.

## Durations and costs

Expected lengths are PLAN's for each probe; prices from `hosts.env` (Spot, europe-west4, disks not counted).

| Kind | Hosts and EUR/h | Expected | Expected cost | Default cap (time at the cap) |
|---|---|---|---|---|
| `p10-1` | G4 1.887 + L4 0.483 | about 45 min (an estimate from the steps, not yet measured: the starts, both uploads, the CARLA start, the warm-up, the check about 10 min, the fetch and the stops) | about EUR 1.80 | EUR 3.50 (1.5 h), approved by the owner on 2026-11-19 |
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
| `ENTRY_SCORE_P10_1` | S-CORE | `<out>`; env `DA_P10_1_CARLA_HOST` (`p10-1`: the simulator host's address, set by the session) | S-CORE build lane | the build check, the clip replay, the late subscriber; its verdicts in `<out>`; started after the world's go, so its full start finds a ticking world |
| `ENTRY_SCORE_START` | S-CORE | `<out> <carla_host or none>`; env `DA_CAMERA_CALIBRATION_DIR` (`p10-2`) | Launch Manager lane | starts the Launch Manager with its processes (identity recorder first); copies `H.yaml` and `homography_C_matrix.yaml` from `DA_CAMERA_CALIBRATION_DIR` into the candidate's working directory before the identity record; returns 0 when they run, without waiting for a camera image (the world holds its first tick until the session's go file); called once per run, each with its own `<out>`; someipd offers 0x4df1 |
| `ENTRY_SCORE_INJECT` | S-CORE | `<out>` | warning-app lane | `p10-3`: publishes test warning requests on the candidate's mw::com event; returns when done |
| `ENTRY_SCORE_STOP` | S-CORE | `<out>` (the start's) | Launch Manager lane | ends the processes (SIGTERM, so the candidate's `.rrd` and the visualization file are finished) and collects their files; the world still ticks meanwhile |
| `ENTRY_SIM_SETUP` | simulator | `<out>` | this lane: `remote/sim_setup.sh` | CARLA server up on port 2000, NVENC test, free disk; the world side's map (`WORLD_MAP` of `world-side/scripts/common.sh`) in the server's `get_available_maps()`, or it fails naming the AdditionalMaps pack (`world-side/README.md`, "The maps pack") |
| `ENTRY_SIM_WARMUP` | simulator | `<out>` | `../world-side/scripts/warmup.sh` | the survey, the session's road in `world_start.json`, the warm-up pass with every camera (hero role `hero`, moved by pose) |
| `ENTRY_SIM_CALIBRATE` | simulator | `<out>` | `../world-side/scripts/calibrate.sh` | ASM-DRIVING-005 and the camera capture, role `de4sdv_calibration`, no candidate; required for `p10-2` |
| `ENTRY_SIM_RUN` | simulator | `<out> <scenario> <setting>` | `../world-side/scripts/run_scenario.sh` | one run (`SC-DRIVING-012 20kmh`, or `ASM-DRIVING-006 20kmh`), detached, with the go/release handshake (`../world-side/README.md`); its records in `<out>/simulator/`; in `p10-1` the world of `P10_1_SCENARIO` `P10_1_SETTING` with `RELEASE_WAIT_S` above the check's bound |
| `ENTRY_SIM_RECORD` | simulator | `--out <dir>` | this lane: `../recording/chase_recorder.py` | started before the warm-up and before the run, ends on its own |
| `ENTRY_GUEST_UP` | guest | `<out>` | this lane: `remote/guest_up.sh` | both guests created fresh (`launch_two_vms.sh down`, `up`) and booted; `getenforce` recorded, `setenforce 0` on the IVI only with `IVI_PERMISSIVE=1` |
| `ENTRY_GUEST_PREPARE` | guest | `<out>` | this lane: `remote/guest_prepare.sh` | the guest build script's `install` (ACLs, APK, IVI reboot) and `verify`, unchanged, as its second caller: one `B12_DIR` per session (`$AB/b12-session-<id>`), no `LOGS`, `IDENT` or `WORK`; required, since fresh guests start empty |
| `ENTRY_GUEST_APP_RESTART` | guest | `<out> <window>` | this lane: `remote/app_restart.sh` | `am start -S -W -n $APP_COMPONENT`, the APK's sha256 and both guests' `getenforce`, before each window; exit 1 when a guest's mode is not the session's mark, or when the new process logs no `link=SUBSCRIBED` as its last link line since the IVI mark within `APP_SUBSCRIBE_WAIT_S` |
| `ENTRY_GUEST_OFFER_CHECK` | guest | `route\|mark\|neigh <out>`, `unit <out> <mark>`, `receipts <capture> <restart record>` | this lane: `remote/offer_check.sh` | the SD multicast route to `cvd-ebr`; both guests' clocks before each S-CORE side start, each its own (`mark`); the IVI app's last link line in the IVI log since its mark `link=SUBSCRIBED`, `link=UNAVAILABLE` counted, never decisive, no broker error for 4df1 in the core log since its mark, the context lines kept and `diag/` on a fail (`unit`; `UNIT_SOURCE=core`: the earlier core-log pattern, `UNIT_REGISTERED_RE`, `UNIT_NEGATION_RE`); both guests' neighbour caches flushed after the VXLAN (`neigh`); the receipt events of the app's record since the window's app start, after each window (`receipts`) |
| `ENTRY_GUEST_CLOCK` | guest | `set <out>` | this lane: `remote/ivi_clock.sh` | IVI clock set from the guest host's, offset and bound recorded; exit 1 when the offset left is above `CLOCK_MAX_OFFSET_S` (0.1 s) |
| `ENTRY_GUEST_CAPTURE` | guest | `start <out> --max-s <s>`, `stop <out> --wait-cap-s <s>` | this lane: `../recording/display_capture.sh` | the display capture |
| `ENTRY_VXLAN` | guest, S-CORE | `guest-host\|host-half add <peer ip>` | this lane: `remote/cross_vm_guest_bridge.sh` | the VXLAN segment, the S-CORE host at 192.168.98.1 (INC-DRIVING-001's script, unchanged) |

Per-session settings of the remote entries: gcloud ssh does not carry the lead host's environment, so the session
passes the settings given with `--remote-env NAME=VALUE` (repeatable) to every step on that name's host as `env
NAME=value` before the command, logs the names and records the values in `session.json` (`remote_env`). A name off
the allow-list, a malformed or a repeated option is refused (exit 2) before anything starts. A variable merely
exported in the calling shell never reaches a step: the lead's shared terminal has exported other workers'
`UNIT_WAIT_S` and `ADB` before, and `UNIT_WAIT_S=0` would fail a paid `p10-3`'s unit check at once. The allow-lists
(`REMOTE_ENV_guest`, `REMOTE_ENV_score` in `da_session.sh`): on the guest host `UNIT_SOURCE`, `UNIT_REGISTERED_RE`,
`UNIT_NEGATION_RE`, `BROKER_ERROR_RE`, `UNIT_WAIT_S` (`remote/offer_check.sh`), `B12_DIR`, `VERIFY_WAIT_S`,
`ADB_TIMEOUT_S`, `UP_TIMEOUT_S` (the guest build script), `CLOCK_READS`, `CLOCK_MAX_OFFSET_S` (`remote/ivi_clock.sh`),
`START_WAIT_S`, `APP_SUBSCRIBE_WAIT_S` (`remote/app_restart.sh`). `UNIT_WAIT_S`, `START_WAIT_S` and
`APP_SUBSCRIBE_WAIT_S` must be whole seconds, and the step bounds follow them (logged as `step bounds:`): the unit
gate's `UNIT_WAIT_S + 240` s, the app restart's `START_WAIT_S + APP_SUBSCRIBE_WAIT_S + 300` s; on the S-CORE host
`GATEWAYD_RX_REGEX` and the `DA_P10_1_*` waits of `p10_1_check.sh` (not `DA_P10_1_CARLA_HOST`, which `p10-1` sets
from its own simulator host). A changed guess of the first `p10-3` (the broker's line, say) is then a setting
of the next session, not a commit. The `hosts.env` and `entrypoints.env` names (`ENTRY_*`, `GUEST_STOP_CMD`, the VMs,
the caps) can still be overridden from the environment, for the dry runs: start every real session from `env -i`, as
the blocks below do.

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
folder, a real gcloud in a dry run, dry-run knobs in a real session, a session id outside its alphabet, a
`--remote-env` off the allow-list), a foreign fetch, and that the dry run prints every call. Since the second review
also: a signal or the cap during a guest step (the step's TERM before the guests' stop), a guest host never reached
over SSH, an SSH loss after a guest step, an S-CORE stop's exit 7 and 8, the go clock, the trap's bounded pre-stop
phase and its 30 s status reads, the safety net's deadline, and the README's launch lines themselves. Since the
owner's approval of p10-1 with the simulator host: its sequence, the port test (each port logged, a closed port ends
the session before any Launch Manager start), the check's `DA_P10_1_CARLA_HOST` from gcloud only, the world's hold
above the check's bound, and the cap of EUR 3.50. `tests/test_remote_scripts.py` runs the guest-host scripts and the safety net against fake `cvd`,
`adb`, `pgrep`, `sudo` and `ip`. The stubs in `tests/stubs/` stand for the S-CORE side's entries (another lane's)
and for `make-h` in dry runs; they never run on a host.

What the dry runs cannot show, and the sessions must: the real SSH and scp paths (IAP included) and their times, the
gcloud output formats the fake imitates, the VXLAN between the S-CORE host and the guest host, the CARLA port from
the S-CORE host to the simulator host on `carla-net` (brief R5, D5), the broker's log line for the unit's
registration, that the S-CORE side's start returns before the first image, the systemd timer of the guest host's
safety net, and the real costs.
