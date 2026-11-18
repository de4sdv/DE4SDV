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
| `p10-3` | S-CORE host, guest host | guests up, VXLAN both ends, S-CORE side up, IVI clock set, display capture on, injected warning requests, capture off, S-CORE side down |
| `p10-2` | simulator host, S-CORE host, guest host | CARLA server, CARLA reachable from the S-CORE host, guests up, VXLAN, S-CORE side up (VisionPilot connects to CARLA), warm-up with the chase recorder, optional calibration runs, IVI clock set, display capture on, chase recorder on, the scenario run, capture off, S-CORE side down |

Rules the script enforces (from the brief and the INC-DRIVING-001 bench):

- The simulator host starts first and must still be `RUNNING` 30 s later; a reclaimed start is retried in rounds
  (45 s pauses, 30 min deadline) before the next host starts. A capacity refusal is retried; a quota or other error
  ends the session.
- One GPU per project: the session refuses to start when another GPU VM runs in a project it starts a GPU VM in.
- A VM found running before the session is not adopted: the session refuses.
- The guest host starts only with `--owner-ok-guest-host`.
- Every VM is registered for the stop before its start call. The EXIT trap stops the GPU hosts, then stops the guests
  with `cvd stop` (the guest build recipe's `smoke_boot.sh --stop-only`), then their host, and waits for
  `TERMINATED`. It lists the VMs of both projects at the end. Nothing is created or deleted.
- A watchdog writes `cost.log` every 30 s (an upper bound: from each start call, at the hourly prices in
  `hosts.env`) and ends the session at the cap. Each VM also gets `shutdown -h` at the cap plus 10 min, should the
  lead host lose the session.
- Before any VM starts, the session builds the kit (the bench folder at `HEAD`, or as on disk with
  `--kit-from-worktree`), and checks that every entry point the kind needs is in it and executable. Each host's
  upload is checked by its sha256.
- The evidence goes into a new `incoming_<session id>/` (refused if it exists): `session.log`, `commands.log` (every
  gcloud, ssh and scp call), `cost.log`, `session.json`, `kit.tgz`, and per host `<role>/out/` with each step's log
  and status. A fetched folder whose `session_id` is not this session's fails the session.

Exit codes: 0 done; 2 refused before any start; 3 no capacity or preempted; 4 SSH or upload failed; 5 a step failed;
6 start refused; 9 dry run refused; 10 cost cap; 11 a stop not confirmed; 129/130/143 signals.

## Command lines for the lead

Run from the integrated bench tree (the other lanes' entries merged in), on the lead host. A dry run first, then the
session:

```bash
cd <integrated worktree>
S=implementation/driver-assistance-bench/session
mkdir -p ~/.hermes/cache/scratch/b13-dry && export FAKE_DIR=~/.hermes/cache/scratch/b13-dry DA_GCLOUD=$PWD/$S/tests/fake_gcloud.py
bash $S/da_session.sh --kind p10-1 --dry-run --evidence-root ~/.hermes/cache/scratch/b13-dry/ev   # checks the kit
unset FAKE_DIR DA_GCLOUD

bash $S/da_session.sh --kind p10-1 2>&1 | tee -a ~/p10-1.out                          # the S-CORE build check, 2026-11-19
bash $S/da_session.sh --kind p10-3 --owner-ok-guest-host 2>&1 | tee -a ~/p10-3.out    # the warning on the guests, with the owner's OK
bash $S/da_session.sh --kind p10-2 --owner-ok-guest-host 2>&1 | tee -a ~/p10-2.out    # the first closed loop, 2026-11-20
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
runs it on its host through `remote/host_step.sh`, with the bench folder as the working directory and `DA_OUT`,
`DA_SESSION_ID` and `DA_BENCH` set. The first argument is the step's output folder; everything the entry writes there
is fetched. Exit 0 means the step succeeded; any other status ends the session (the VMs stop).

| Variable | Host | Arguments | Owner | Contract |
|---|---|---|---|---|
| `ENTRY_SCORE_P10_1` | S-CORE | `<out>` | S-CORE build lane | the build check, the clip replay, the late subscriber; its verdicts in `<out>` |
| `ENTRY_SCORE_START` | S-CORE | `<out> <carla_host or none>` | Launch Manager lane | starts the Launch Manager with its processes (identity recorder first); returns 0 when they run |
| `ENTRY_SCORE_INJECT` | S-CORE | `<out>` | warning-app lane | `p10-3`: publishes test warning requests on the candidate's mw::com event; returns when done |
| `ENTRY_SCORE_STOP` | S-CORE | `<out>` | Launch Manager lane | ends the processes (SIGTERM, so the candidate's `.rrd` and the visualization file are finished) and collects their files |
| `ENTRY_SIM_SETUP` | simulator | `<out>` | this lane: `remote/sim_setup.sh` | CARLA server up on port 2000, NVENC test, free disk |
| `ENTRY_SIM_WARMUP` | simulator | `<out>` | world-side lane | the warm-up pass with every camera; it spawns a hero with role `hero` |
| `ENTRY_SIM_CALIBRATE` | simulator | `<out>` | calibration lane (optional) | the ASM-DRIVING-005/006 runs |
| `ENTRY_SIM_RUN` | simulator | `<out> <scenario> <setting>` | world-side lane | one run (default `SC-DRIVING-012 20kmh`), its world record in `<out>`; leaves synchronous mode at the end |
| `ENTRY_SIM_RECORD` | simulator | `--out <dir>` | this lane: `../recording/chase_recorder.py` | started before the warm-up and before the run, ends on its own |
| `ENTRY_GUEST_UP` | guest | `<out>` | this lane: `remote/guest_up.sh` | both guests booted, `setenforce 0`, identity and APK sha256 recorded |
| `ENTRY_GUEST_PREPARE` | guest | `<out>` | guest build lane (optional) | install the app, push ACLs |
| `ENTRY_GUEST_CLOCK` | guest | `set <out>` | this lane: `remote/ivi_clock.sh` | IVI clock set from the guest host's, offset and bound recorded |
| `ENTRY_GUEST_CAPTURE` | guest | `start\|stop <out>` | this lane: `../recording/display_capture.sh` | the display capture |
| `ENTRY_VXLAN` | guest, S-CORE | `guest-host\|host-half add <peer ip>` | this lane: `remote/cross_vm_guest_bridge.sh` | the VXLAN segment, the S-CORE host at 192.168.98.1 (INC-DRIVING-001's script, unchanged) |

`GUEST_STOP_CMD` (default `bash $HOME/aaos-build/recipe/smoke_boot.sh --stop-only`) must print
`crosvm_processes_after_stop: 0`; otherwise the session warns and still stops the host.

## Tests

`tests/test_session_dryrun.py` runs the real script with `--dry-run` against `tests/fake_gcloud.py`, a stateful fake
that logs every call: the start order of each kind, the 30 s check and a reclaimed G4, capacity rounds, a quota
error, a failed step, the cost cap, SIGTERM, the guests stopped before their host, the refusals (no owner OK, a
running VM, another GPU VM, a missing or non-executable entry, an existing session folder, a real gcloud in a dry
run, dry-run knobs in a real session), a foreign fetch, and that the dry run prints every call. The stubs in
`tests/stubs/` stand for the other lanes' entries; they never run.

What the dry runs cannot show, and the sessions must: the real SSH and scp paths and their times, the gcloud output
formats the fake imitates, the VXLAN between the S-CORE host and the guest host, the CARLA port from the S-CORE host
to the simulator host in the other project (brief R5, owner decision D5), whether `launch_two_vms.sh up` resumes stopped guests, and the real costs.
