# Bench sessions (INC-DRIVING-002)

Status: draft, not yet validated. Beyond the dry runs below, eleven sessions have started bench hosts (each session's
`session.json`). The results of these four stand:

- p10-3 run 2 (SID 20261119T130414Z, 2026-11-19, `410293bb`): exit 0; 21 of 21 test requests received on the IVI guest.
- p10-1 try 4 (SID 20261119T160111Z, 2026-11-19, `eae0a6ef`): exit 0; C1 to C4, C6 and C7 met, C5 and C8 not run by
  design.
- p10-2 attempt 3 (SID 20261120T092051Z, 2026-11-20, `39a964a2`): exit 5 on the simulator host's fetch, which the lead
  completed afterwards ("The evidence fetch", below); both SC-DRIVING-012@20 runs judged, a fail of the pinned
  candidate.
- The judged session S1 (SID 20261121T014447Z, 2026-11-21, `508649ba`): exit 0; the 14 runs of SC-DRIVING-012 to -015
  and the stop run. Its verdicts are in the bench README.

The seven others, each at the bench commit named:

- p10-3 run 1 (SID 20261119T094924Z, 2026-11-19, `7b940dc8`): exit 5 at the step `unit_inject`.
- p10-1 try 1 (SID 20261119T123015Z, 2026-11-19, `0a1d83c3`): exit 5 at the step `port_test`.
- p10-1 try 2 (SID 20261119T123937Z, 2026-11-19, `0a1d83c3`): exit 5 at the step `warmup`.
- p10-1 try 3 (SID 20261119T134840Z, 2026-11-19, `14b77ecb`): exit 12 after its steps: the p10_1 check FAILed (C2 to
  C4 failed, C5 and C8 not run).
- p10-2 attempt 1 (SID 20261119T174606Z, 2026-11-19, `414fff5f`): exit 5 at the step `rec_run1`.
- p10-2 attempt 2 (SID 20261119T203947Z, 2026-11-19, `39a964a2`): exit 5 at the step `app_restart_run1`.
- The `s1` rehearsal (SID 20261121T011350Z, 2026-11-21, `f03e3af9`): exit 6 at the S-CORE host's start: the simulator
  host started, the S-CORE host did not (no capacity in 8 rounds, then a quota error on NVIDIA_L4_GPUS), and no step
  ran.

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
| `s1` | simulator host, S-CORE host, guest host | as `p10-2` up to the calibration file, without the upfront disk check; then the ASM-DRIVING-006 run and every run of `s1_runs.tsv` (each setting twice, then the stop run), each with its own disk check before its S-CORE start, recorder and display window; the stop run's S-CORE path stops at the go + 12 s (below) |

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

Each run of `p10-2` (`world_run` in the script): the chase recorder (runs only) and its `listening` file, the world
side spawns and writes
`ready.json`, the S-CORE side starts with the calibration file, the offer checks and the window open (runs only: the
unit, `am start -S`, the IVI clock, the capture), the go file, `run_end.json`, the S-CORE side stops while the world
still ticks, the release file, the world side and the recorder end, the capture ends. The session log's last
`SEQUENCE` line lists every step in order; `tests/test_session_dryrun.py` pins it for each kind.
The recorder writes `rec_<run>/listening` once it has taken its list of the heroes already there
(`../recording/chase_recorder.py`), and the session starts `world_<run>` only after that file, polled every 2 s for
`T_REC_LISTEN` (150 s) at most, so the run's hero is never in the list (T2 of the closure check of 8fae4100: about
4 s apart). Past the bound, or after the recorder's own end, the run goes on with a `WARNING` line in `session.log`.
The wait is no step of `SEQUENCE`.

### What each `p10-2` run records

Each run's facts go to `session.json` `score_runs.<run>` (`calib_steer`, `run1`, `run2`):

- **The candidate's `speed_limit`.** The model has System 2 set it per scenario (PSR
  `VisionPilotSCOREApplication`). Before any VM starts, `run_setting.py` takes each run's setting from
  `../world-side/scenarios.py`: `SC-DRIVING-012@20` (calib_steer runs on that setting's road and vehicle), with the
  tolerance 20 to 22 km/h. The value is that file's proposal, the middle of the tolerance: 21 km/h, 5.833 m/s
  (`Setting.speed_limit_mps`, also in the world side's setting record). The session gives it to the S-CORE start as
  `DA_SPEED_LIMIT`. `speed_limit_source` begins with "bench proposal:": the model sets no value
  (`scenarios.py` marks it PROPOSAL). Why: the first recorded `p10-2` (20261119T174606Z) left upstream's 33.3 m/s,
  and in calib_steer the car reached 108.9 km/h.
- **What was staged.** The start prints one `SCORE_CONFIG` line: the staged `vision_pilot.conf` values, `hero_wait_s`
  of `adapter.json`, the conf's sha256 and whether the identity record hashes that same file. The session records
  it in `staged`, and ends the session before the go (exit 5, `failed_step` `score_start_<run>`) when the value is
  not the run's or the identity record does not hash the staged conf. It ends it the same way when any value the
  model fixes is another or missing (`score_conf_fixed_check`, J4 of the closure review of 44a4be29): `engine.provider`
  `cuda`, `model.precision` `fp32`, `visualization_on` `false` and `rrd_on` `true` (the configuration sentence of
  VisionPilotSCOREApplication, `driver_assistance_physical_software_realization.sysml:541-544`), and `source.mode`
  `score`, the value the kit stages (`score-path/scripts/stage_score_side.py:67`). The fetched
  `score_<run>/vision_pilot.conf` and `score_<run>/score_config.json` carry the same.
- **The candidate's Rerun record.** `rrd_on = true` is the model's (PSR: the evaluators' record of the warnings),
  so it stays on. calib_steer's `visionpilot.rrd` of 20261119T174606Z was 4,729,613,610 B, and the S-CORE host's
  `out.tgz` took from 18:13 to about 18:32 to copy. So the record stays on the S-CORE host as the evaluators'
  record, to be fetched by a separate step later:
  - `stop_score_side.sh` collects it as a hard link where the stage and `<out>` share a filesystem, so the disk
    holds it once, and writes its path, size and sha256, computed on the host, to `score_<run>/candidate_rrd.json`.
  - `host_step.sh pack` leaves every `*.rrd` out and lists each with its size in `out/pack_excluded.tsv`.
  - `session.json` has `score_runs.<run>.candidate_rrd` and `not_fetched_from_hosts`, and the `p10-2` report line
    names each record kept on the S-CORE host. No Rerun record is deleted on any host.
- **The candidate's visualization recording.** The owner decided on 2026-11-17 to keep the DE4SDV visualization
  recorder (patch 0001) in every run and to state its delay. The Launch Manager configuration sets
  `DE4SDV_VISUALIZATION_RECORD` for `vision_pilot` (`launch-manager/README.md`), so every run of mode full records the
  candidate's visualization (nvh264enc, 4000 kbit/s: about 0.5 MB/s) with its sidecars `.frames.csv` (one row per
  frame, `sim_time_s` last) and `.summary.txt`:
  - `stop_score_side.sh` moves the three into `score_<run>/score_side/visualization/` (a rename: nothing in the stop
    copies the video), takes the video's sha256 and writes `score_<run>/visualization_recording.json` (`path`,
    `sha256`, `bytes`, `frames`, `reason`) and a side file `visualization.mkv.sha256`.
  - `host_step.sh pack` leaves the video out and lists it with its size and sha256 in `out/pack_excluded.tsv`; the
    sidecars stay in the pack.
  - `session.json` has `score_runs.<run>.visualization_recording` (the field `case-evaluators/evidence_record.py`
    reads for the bench recording) and the video in `not_fetched_from_hosts.score`; `session.log` names each record and
    the hand fetch after the session, `fetch_chase.sh --role score` ("The chase videos" below).
  - A run whose stop wrote no record, or whose video is missing or empty, gets the field with `sha256` null and a
    named `reason`; that is never a failed step, as the chase recorder's own end is not.
- **The disk check.** The first step of a `p10-2` is `score:disk_check` (`ENTRY_SCORE_DISK`), before the simulator
  host's setup and any run, so a short disk costs the least.
  - The budget is the candidate's highest record rate times each run's planned running, plus 10 % and 5 GB. The rate:
    calib_steer's record of 20261119T174606Z held 4,729,613,610 B for 542 passes, 8,726,224 B a pass, and the
    candidate makes at most 10 passes a second (the front camera's sensor_tick 0.1 s), so 88 MB per second of
    candidate running, rounded up. A run's planned running is its setting's run cap (90 s) plus 60 s of hold until its
    S-CORE stop.
  - For the three runs that is 450 s: 48,560,000,000 B where the stage and `<out>` share a filesystem. Otherwise
    the longest run's 19,520,000,000 B are also needed on the stage's filesystem.
  - A short disk ends the session there: exit 5, `failed_step` `disk_check`, "DISK SPACE SHORT" in `session.log`.
    `session.json` `score_disk_check` holds the rate, the planned seconds, the need and the host's answer.
- **The actuation adapter's attach.** `score_runs.<run>.adapter` holds what the adapter's own record
  (`score_<run>/score_side/run/score/actuationAdapter.jsonl` in the fetched S-CORE output) says: `heroActorId` from
  its `config` event and the text of its first `error` event (`simulator client: no vehicle with role_name hero`),
  or "not fetched" when the S-CORE host was not fetched, or "no adapter record fetched". The `p10-2` report line
  names every run with no attach: such a run sent no command to the car, whatever the session's exit code. Why: in
  20261119T174606Z the adapter of run 1 gave up, the Launch Manager switched to its fallback, and the session ended
  rc 0 with nothing in `session.json` saying so (T4 of the closure check of 8fae4100).
- **The chase view.** A chase recorder that ends with its own exit status, 0 or not, is a result of its run's
  window, never a failed step. `session.json` `chase_view.<run>` holds `complete` (the recorder's rc 0 only), `rc`,
  and from its `summary.json` in the fetched files the `end`, `written`, `gaps` and `ticks_seen`. rc 0 says that the
  recorder attached, wrote at least one frame and ffmpeg ended 0, not that the view has no gap: read `written` and
  `gaps`. The `p10-2` report line says "chase recorder ended rc 0 in every run" or "chase recorder NOT rc 0 in every
  run" with each run's rc and end, and `p10_2.chase_view_complete` says the same. The session goes on
  with the window's capture stop, its receipts and the next run. Only a recorder still running at `T_REC_END`
  (it would attach to the next run's hero) or a lost host ends the session. Why: in 20261119T174606Z the run's
  recorder ended rc 1 ("ego or camera deleted by another client", no frame), and the session skipped
  `receipts_run1` and the whole of run 2. The recorder's own fix is another lane's.

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

### What an `s1` session runs and records

`s1` runs the judged runs of S1 (the S1 build plan, section 4) in one session, in the order of `p10-2`:

- **The run list** is the committed `s1_runs.tsv`, read from the kit, one run a line: `<run id> TAB <run>`. Its rows are
  the shared contract of the S1 build: SC-DRIVING-012 at 20, 42 and 60 km/h, SC-DRIVING-013 at 30 and 60, SC-DRIVING-014
  at 30 and SC-DRIVING-015 at 40, each `r1` and `r2`, then `stop further`, the further run in which the S-CORE path is
  stopped (no setting; it runs the world of `S1_STOP_SCENARIO` `S1_STOP_SETTING`, `entrypoints.env`). A run's label
  names its steps: `SC-DRIVING-012@20 r1` is `012_20_r1`, the stop run `stop`. Any other line, a run named twice or a
  run after `stop` is refused before any VM starts (exit 2), and so is a setting `run_setting.py` does not know. A dry
  run may name its own list (`DA_S1_RUNS`); a real session refuses that knob. A rehearsal names its own list with
  `--rehearsal --runs <tsv>` and is no evidence ("`s1` rehearsal" below); `--runs` without `--rehearsal` is refused.
  `tests/test_session_s1.py` pins the list against the model's seven settings and the `SEQUENCE` of a dry run.
- **The disk check before each S-CORE start** (C2), calib_steer's included, in place of `p10-2`'s upfront check over
  every run (which for S1 would need about 180 GB): one run's Rerun record and visualization recording, 88 MB/s and
  0.5 MB/s times its run cap plus 60 s, plus 10 % and 5 GB (19,602,500,000 B for a 90 s cap). A short disk ends the session cleanly before that run: its stops and
  fetches as on any failure, exit 5, `failed_step` `disk_check_<run>`, `ended_by` `disk short before run <run>: runs
  owed ...`, and `session.json` `s1.runs_owed` lists that run and every later one; no record is cut.
- **Per run** `session.json` `score_runs.<run>` adds to `p10-2`'s: `run_id`, `runIdentity` (`<run id>/<r1|r2|further>`:
  the first or the second run of its setting, or the further run), `scenario`, `setting`, `disk_check` (need, rc, the
  host's answer) and `simulatedConfiguration`: the sha256 of the run's scenario definition (`scenario_digest.py`, from
  the kit: the setting's record of `world-side/scenarios.py` and the sha256 of `scenarios.py`, `da_world_side.py`,
  `sites.py` where the kit has it and `scripts/common.sh`), with the files it covers.
- **The stop run** (REQ-DRIVING-038 and -043 stop clauses): after its go the session waits `PATH_STOP_AFTER_S` (12 s,
  from the go file's touch) and runs `path_stop_stop` (`ENTRY_SCORE_PATH_STOP`, the score-side lane's
  `score-path/scripts/path_stop.sh`, no arguments). Its one JSON line (`runTarget` `path_stopped`, `stopInstantRealNs`,
  `stopInstantMonoNs`, `rc` 0) is the stop instant: `session.json` `s1.stop_instant`, and `s1.path_stop` with the go's
  and the call's times. A step that fails or a line that is missing or says anything else ends the session (exit 5,
  `failed_step` `path_stop_stop`). The world side ends the stop run at its cap, 42 s of simulation time after the go
  (`world-side/scenarios.py` `STOP_RUN_CAP_S`): the stop instant's bound is about 22.2 s after the go (12 s, the step and
  the client's connect, drain and the stopped components' shutdown), so at least 10 s of run ticks follow it.
- **The chase videos stay on the simulator host** (C3): `host_step.sh pack` leaves every `out/rec_*/chase_view.mp4` out
  of the pack and lists each in `out/pack_excluded.tsv` with its size and sha256 (about 144 MB a run, 2.2 GB for S1:
  far past the fetch's bound through IAP). Nothing in the stop path scales with the videos: right after each
  recorder's end the session has the host hash its video once (`host_step.sh hash`, a side file
  `chase_view.mp4.sha256` with the sha256, size and mtime; one SSH call of 120 s at most, not a step of the
  `SEQUENCE`), and the pack takes the sha256 from that file when the size and mtime still match; it hashes only a video
  without one (a run the session's end cut). `session.json` `not_fetched_from_hosts.sim` and `s1.chase_videos_on_the_
  simulator_host` name them, and `session.log` gives the command that fetches them after the session: `fetch_chase.sh`
  ("The chase videos" below). The recorder's `summary.json` is in the pack as before.
- **The evidence record's fields** that no other step writes (`evidence_fields.py`; `case-evaluators/evidence_record.py`
  reads them for RetainedAssistanceRunEvidence). A field the session cannot read is `{"absent": "<reason>"}`, never
  empty and never guessed, and the session goes on. None of them is a step of the `SEQUENCE`.
  - `configuration_identity`, `configuration_receipt_sha256` and `configuration_receipt` (its path, the commit, the
    digest the model binds, `equal_to_model`, and the file and line of each source): read in the preflight from the
    committed files at the session's own commit (`git show <commit>:<path>`): the configured product of
    `driver_assistance_variability_configuration.sysml`, which the evidence item must bind too, and the SHA-256 of the
    receipt file its doc names. No commit (no git) gives both absent.
  - `visualization_recorder_delay`: the model's sentence verbatim with its file, lines and commit
    (`driver_assistance_verification_evidence.sysml`, RetainedAssistanceRunEvidence), only when every S-CORE start ran
    on the GPU the sentence names (an NVIDIA L4); otherwise absent: a run on another host states the delay it measures.
  - `score_platform.{lifecycle_version, communication_version, someip_gateway_commit}` and
    `execution_environment.score_gpu`: from each S-CORE start's `SCORE_PLATFORM` and `SCORE_GPU` lines, kept per run in
    `score_runs.<run>.score_platform` and `.score_gpu`; the session's value is the one every start that ran gave, else
    absent naming each run's.
  - `execution_environment.sdv_core_image` and `.ivi_image`: from `guest_up`'s `GUEST_IMAGE` lines
    (`guest_images.txt`), read from each booted guest: product, build id, fingerprint and vbmeta digest. Without the
    guest host both are absent.
- **The visualization videos stay on the S-CORE host** in the same way (above, "The candidate's visualization
  recording"), each with its sha256 in that host's `out/pack_excluded.tsv`; `session.log` names their hand fetch,
  `fetch_chase.sh --role score`.
- **The report** of `p10-2` holds per run of the list: the chase recorder's end, the adapter's attach, the display
  recording (`session.json` `s1`, with the camera calibration source and `conditional_on_permissive_ivi`).

### The chase videos: `fetch_chase.sh`, the simulator host alone after the session

`fetch_chase.sh <incoming dir>` (C6; adapted from the proven `sim-lead-fetch/fetch_g4_ranges.sh` of 20261120T092051Z)
fetches every video the session's `sim/out/pack_excluded.tsv` lists:

- it refuses unless the simulator host reads `TERMINATED` and no `da-session-*` user unit is active (exit 2);
- it starts the host, reads `RUNNING` back, waits for SSH through IAP and arms the host's power-off safety net (the
  fetch's bound plus 15 min); its EXIT trap stops the host and reads `TERMINATED` back (exit 11 otherwise);
- each video is read as ranges (`dd` on the host, `FETCH_RANGE_MIB` MiB over `FETCH_PARALLEL` IAP tunnels, 3 tries a
  range, each size-checked), joined, and kept under its name (`sim/out/rec_<run>/chase_view.mp4`) only when its
  sha256 equals the list's (exit 5 otherwise; nothing kept under the name); a video already fetched whole is skipped;
- the whole fetch is bounded by 120 s plus the bytes at 0.5 MB/s (half the measured 1.03 MB/s);
- a start refused for capacity costs nothing: rounds every 180 s, up to 20 (an hour), then exit 4;
- a TERM to its main process (`systemctl stop` of its unit) goes on to the round, whose trap ends every tunnel (each
  range's worker outlives a TERM until its tunnel is killed) and stops the host; no round starts after it;
- its records are in `sim/fetch_chase/`: `fetch_chase.log`, `ranges.tsv` and `fetch_chase.json` (each video's result,
  the host's start and stop, its status after and the cost at its hourly price).

For S1's 2.2 GB: about 37-43 min of ranges at 1.03 MB/s plus about 4 min of start and stop, EUR 1.3-1.5 at 1.887
EUR/h. Run it as the `s1` block below shows, in a user unit that never SIGKILLs its trap.

`fetch_chase.sh --role score <incoming dir>` fetches the candidate's visualization videos the same way from the S-CORE
host alone (every `out/score_<run>/score_side/visualization/visualization.mkv` that `score/out/pack_excluded.tsv`
lists), by the same rules: `TERMINATED` first, ranges, each sha256 against the list, the stop in its trap, a refused
start retried every 180 s. It reaches the S-CORE host as the session does (no IAP flag) and keeps its records in
`score/fetch_visualization/` (`fetch_visualization.log`, `ranges.tsv`, `fetch_visualization.json`). For S1, at about
0.5 MB/s of running (about 15 runs of 1.5-2.5 min of candidate running each): about 1 GB, about 20 min of ranges.

### The candidate: `--candidate pin|pr427`

The VisionPilot candidate (decision D4). `pin` (the default) is the S-CORE build's bundle `/opt/da-b2/bundle` and
changes no command. `pr427` is the variant build (`DA_CANDIDATE=pr427`, `score-build/build_score_bench.sh`):
the session gives every S-CORE step `DA_B2_BUNDLE=/opt/da-b2-pr427/bundle` through the remote settings (on the
allow-list, set only by `--candidate`: `--remote-env DA_B2_BUNDLE=...` is refused). Each S-CORE start's `SCORE_CONFIG`
line names the staged facts' diffs (`facts_diffs`, the source difference the identity recorder hashes); the session
ends the run before its go (exit 5, `failed_step` `score_start_<run>`) when `pr427`'s do not list patch 0004 or `pin`'s
do, and when they lack any patch of the kit's series for the candidate (`score-interface/series.sh list`: `pin`
0001-0003 and 0005, `pr427` 0001-0005), so a bundle built from an older series never runs as this kit's candidate.
`session.json` `candidate` records the name and the bundle.

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

an s1 window: a p10-2 window                                2995 s
+ the stop run's wait to the path stop (PATH_STOP_AFTER_S)     12 s
+ path_stop_<w> (60 + T_STEP 300 + 20 + 60 + 60)              500 s
+ the chase video's hash at its recorder's end (SSH bound)     120 s
= --max-s of an s1 window                                   3627 s
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
  the cap fetches every host whose files were not fetched yet (120 s pack; then 300 s copy by scp at most, or the
  ranges of a host reached through IAP within the slot's time left of 420 s), before its stop.
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
  exit 3; it is not fetched (`not_fetched`, `ended_by` `host lost: <role> (<status>)`), and the other hosts are
  collected and fetched as after any failure.
- **The host watch.** A host can be lost while none of its steps is polled (20261119T203947Z: the S-CORE host was
  preempted while the session ran guest steps; a guest step failed 87 s later on the missing offer, the S-CORE stop
  and the fetch SSHed to the stopped VM, and nothing named the loss). Every `HOST_WATCH_S` (30 s) a loop beside the
  cost watchdog reads the states of the VMs this session started, one `instances list` per project bounded at 25 s,
  each VM only once it passed its preemption check, and only until the trap begins its own stops (the trap's first
  act is to write `.trap_stopping`). A VM that reads anything but `RUNNING` ends the session by TERM ("HOST LOST ...
  in the host watch" in `session.log`). The trap then gives that host no SSH, no stop step and no fetch, still ends
  the running step, stops the S-CORE side, ends the world side and fetches every other host not fetched yet (a
  healthy host whose fetch that TERM cut is fetched again in its slot, before its stop: "the fetch from <vm> was cut
  by the host watch's TERM for the loss of <role>"), stops every VM, and exits 3 with `ended_by` `host lost: <role>
  (<status>)`, or the loss the session had named already. The watch skips a role the session has already named lost
  (`host_lost` writes `.lost_known` first), so it never ends the session again for a loss being handled (R1 of the
  closure check of 1bfbd6b4: in attempt 3's order, every run done and the G4's fetch under way when the L4 was
  preempted, its TERM cut the G4's fetch for good).
- Every path of the stop that SSHes to a role host (the S-CORE stop on failure `score_down`, the fetch's pack and
  copy, the running step's TERM `step_down`, the world side's release, the capture's stop) reads the VM's state when
  its SSH fails (rc 255; the copy on any failure). A VM that is not `RUNNING` is a lost host as above, never "fetch
  ... failed or changed (remote '', local '')". A step that failed while a host was already gone stays
  `failed_step`; `ended_by` names the host loss, with exit 3, when GCP's preemption operation is older than the
  step's failure, and the failed step (exit 5) otherwise. The operation's time errs late (in 20261119T203947Z it came
  44 s after the host's own power-off), so a step that failed in between still reads as the end.
- `session.json` `hosts_lost.<role>` holds `status`, `detected_at`, `detected_by` (`host watch`, a poll, or the SSH
  that failed) and `preempted_at`: the newest `compute.instances.preempted` operation of that VM since the session's
  start (`gcloud compute operations list`, in UTC), null when GCP lists none or when a signal cut that read: the row
  is written before the read and its `preempted_at` filled in after it. The session's filter, run once by hand
against the main project on 2026-11-20, listed the S-CORE host's preemption of 20261119T203947Z as
`2026-11-19T13:01:03.560-08:00` (21:01:03.560Z). `not_fetched` names a lost host as
  "`<role>`: records on its disk under ~/da-kit/`<id>`/out (fetch owed)", and the kind's report line names the loss:
  fetch those records by hand before any run whose records they hold is judged; after a signal or the cap,
  `exit_code` and `ended_by` stay the signal's or the cap's; a host found lost in the trap is in `hosts_lost` and
  `not_fetched`: read those two first.
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

Exit codes: 0 done; 2 refused before any start; 3 no capacity, or a host lost (preempted) before any step failed
(`hosts_lost`); 4 SSH or upload failed; 5 a step failed;
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
  `SendSIGHUP=no`. The trap needs far longer than systemd's default 90 s stop time-out: the pre-stop phase (the
  running step's TERM and its end, the open capture's stop, the S-CORE side's stop, the world side's end and the
  fetches, bounded together per kind at 26 to 38 min: "The exit trap's pre-stop budget" below), the guests' stop (up
  to 2 x 5 min), then the stop polls (5 min per VM). Not `nohup ... &` (the lead's terminal tool refuses it, and a tool-tracked
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

A `p10-2` session also runs with `--camcal settings` (the lead's decision of 2026-11-19, owner informed): the
candidate's `H.yaml` is the homography of the road plane computed from the simulated camera's known pose and lens
(`camera_calibration.py make-h --source settings`, `H_settings`), in upstream's `H.yaml` layout, and
`homography_C_matrix.yaml` is derived from it by upstream's `find_homography_C_matrix.py`, as upstream's build does
(VisionPilot/CMakeLists.txt:49-53 at 014e0e7a).

- Why: CARLA 1.0's `apply_texture` sets only material parameters named BaseColor, Difuse, Normal, Emissive or ORMH
  (CarlaGameModeBase.cpp:505-548 at 14ac3b1a50), and the material of the engine plane the boards are laid on
  (`/Engine/BasicShapes/Plane`) has none of them. On the real G4 the boards render flat grey, and upstream's
  calc_front_camera_homography.py finds 0 boards, so the default source would end the session at camera-capture.
- What is checked: on four full-contrast boards rendered at the bench camera's real G4 pose, upstream's own
  procedure agrees with this `H.yaml` to 0.30 % of the distance at 10-60 m (the bench's tolerance is 2 %; the test
  `test_gate_settings_h_yaml_agrees_with_upstreams_procedure_on_full_contrast_boards_at_the_g4_pose`).
- What is lost: upstream's procedure is not exercised on a real frame, and the session has no real-frame
  cross-check. `session.json` records `camera_calibration_source` `settings` with its reason and
  `camera_calibration_cross_check` "not run: no board rendered" (also in its `p10_2` report).
- camera-capture still runs and keeps its frame as evidence. Its board pre-check is recorded
  (`camera_capture_precheck`) and does not end the session. With the default source (`--camcal checkerboard`)
  nothing changes: a failing frame ends the session at camera-capture.
- The source comes only from the flag, never from a fallback: a make-h whose record names another source ends the
  session at `make_h`.
- `gapCameraImageAndGeometry` stays open: the settings' homography is only as right as the camera settings the
  world side reads back, and no real frame has confirmed it.

```bash
C=FULL_SHA_OF_THE_COMMIT_UNDER_TEST      # replace: the integration commit under test
# --permissive-ivi: every result of the session is conditional on a permissive IVI (the lead's decision of 2026-11-19)
# --camcal settings: H.yaml from the simulated camera's settings and pose, not from a board frame (the boards render
# flat grey: CarlaGameModeBase.cpp:505-548 at 14ac3b1a50); no real-frame cross-check; gapCameraImageAndGeometry open
cd /home/mrk/de4sdv-worktrees/p10-$C || exit 1
S=implementation/driver-assistance-bench/session
# the dry run needs the VisionPilot clone at the pin (VP_CLONE, default ~/de4sdv-upstream/vision_pilot); make-h is
# the tests' stand-in there (the fake's capture files are no images); the session itself checks CV_PY's OpenCV
D=$HOME/.hermes/cache/scratch/b13-dry-$(date -u +%H%M%S); mkdir -p "$D"
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin FAKE_DIR="$D" DA_GCLOUD="$PWD/$S/tests/fake_gcloud.py" \
  DA_MAKE_H="$PWD/$S/tests/stubs/make_h.sh" \
  bash $S/da_session.sh --kind p10-2 --owner-ok-guest-host --permissive-ivi --camcal settings --dry-run --evidence-root "$D/ev"; echo "dry run rc=$?"
SID=$(date -u +%Y%m%dT%H%M%SZ)
systemd-run --user --unit=da-session-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/p10-2-$SID.out -p StandardError=append:$HOME/p10-2-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin \
  /bin/bash $S/da_session.sh --kind p10-2 --owner-ok-guest-host --permissive-ivi --camcal settings --session-id "$SID"
# end it early: systemctl --user kill --kill-who=main -s TERM da-session-$SID   (never kill -9)
```

Then compose the video from the fetched files (see `../recording/README.md`).

### `s1` (all three hosts, the judged runs)

An `s1` session runs as `p10-2` does, with `--permissive-ivi` and `--camcal settings` (the same decisions of
2026-11-19), with `--ackermann-gains v1` (the owner's decision D-S1-2 of 2026-11-21: the v1 gains for the judged
runs), and `--candidate pin` unless the lead names `pr427`. Its run list is the committed `s1_runs.tsv`; its
cap is EUR 8.00 (`CAP_EUR_S1`). After it, the chase videos are fetched with the simulator host alone.

The judged runs use an on-demand L4 (the owner's decision D-S1-3 of 2026-11-21): switch the S-CORE host's
provisioning model to on-demand while it is TERMINATED, before the session. Both `s1` lines give `SCORE_EUR_H=0.806`,
the on-demand rate of g2-standard-8 in europe-west4; hosts.env's 0.483 is the Spot rate, which would make the cost
watchdog count about EUR 0.32 an hour low (closure review of 44a4be29, J8). The rehearsal runs on Spot and gives none.

A run whose go would come more than `GO_LIMIT_S` (380 s) after its S-CORE start ends the whole session. The
session logs `INVALID RUN <run>` and exits 5 with `failed_step` `world_<run>`; the runs not yet done need a new
session. The step bounds between the S-CORE start and the go add up to far more than 380 s, while attempt 3 of
p10-2 needed 155-160 s, so the limit, not the bounds, decides (closure review of 44a4be29, J6).

```bash
C=FULL_SHA_OF_THE_COMMIT_UNDER_TEST      # replace: the integration commit under test
# --permissive-ivi, --camcal settings: as for p10-2 (the lead's decisions of 2026-11-19); every result is conditional
# on a permissive IVI. --candidate pin is the default; --candidate pr427 runs the second candidate's bundle
# --ackermann-gains v1: the owner's decision D-S1-2 of 2026-11-21 (the v1 gains for the judged runs)
# SCORE_EUR_H=0.806: the on-demand L4 of D-S1-3 (hosts.env's 0.483 is the Spot rate)
cd /home/mrk/de4sdv-worktrees/p10-$C || exit 1
S=implementation/driver-assistance-bench/session
D=$HOME/.hermes/cache/scratch/b13-dry-$(date -u +%H%M%S); mkdir -p "$D"
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin FAKE_DIR="$D" DA_GCLOUD="$PWD/$S/tests/fake_gcloud.py" \
  DA_MAKE_H="$PWD/$S/tests/stubs/make_h.sh" SCORE_EUR_H=0.806 \
  bash $S/da_session.sh --kind s1 --owner-ok-guest-host --permissive-ivi --camcal settings --ackermann-gains v1 --dry-run --evidence-root "$D/ev"; echo "dry run rc=$?"
SID=$(date -u +%Y%m%dT%H%M%SZ)
systemd-run --user --unit=da-session-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/s1-$SID.out -p StandardError=append:$HOME/s1-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin SCORE_EUR_H=0.806 \
  /bin/bash $S/da_session.sh --kind s1 --owner-ok-guest-host --permissive-ivi --camcal settings --ackermann-gains v1 --session-id "$SID"
# end it early: systemctl --user kill --kill-who=main -s TERM da-session-$SID   (never kill -9)
# after it, once session.json is written and da-session-$SID is inactive: the chase videos, the simulator host alone
# (it refuses unless that host reads TERMINATED; its own unit, so its trap that stops the host is never SIGKILLed)
systemd-run --user --unit=da-chase-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/s1-chase-$SID.out -p StandardError=append:$HOME/s1-chase-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin \
  /bin/bash $S/fetch_chase.sh "$HOME/.hermes/outputs/inc-driving-002/phase10/sessions/incoming_$SID"
# then read sim/fetch_chase/fetch_chase.json: result ok, vm_status_after TERMINATED
# then the candidate's visualization videos, the S-CORE host alone, once da-chase-$SID is inactive (SCORE_EUR_H=0.806:
# the same on-demand L4, which fetch_visualization.json records):
systemd-run --user --unit=da-vis-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/s1-vis-$SID.out -p StandardError=append:$HOME/s1-vis-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin SCORE_EUR_H=0.806 \
  /bin/bash $S/fetch_chase.sh --role score "$HOME/.hermes/outputs/inc-driving-002/phase10/sessions/incoming_$SID"
# then read score/fetch_visualization/fetch_visualization.json: result ok, vm_status_after TERMINATED
```

### `s1` rehearsal (a short run list, not evidence)

A rehearsal runs `s1` as above on a run list of its own, `--rehearsal --runs <tsv>` in the format of `s1_runs.tsv`
(the lead's decision of 2026-11-20). The block below runs one run and the stop run on the simulator host and the S-CORE
host only. A rehearsal is no evidence: `session.log` says `rehearsal: not evidence`, and `session.json` holds
`rehearsal: true` and `runList` (`path`, `sha256` of the file). Its cap is EUR 2.00 (`CAP_EUR_S1_REHEARSAL`, about
50 min of both hosts) unless `--cap-eur` is given; the block below gives EUR 2.50, the cap the rehearsal's decision
names (closure review of 44a4be29, J3), about 63 min of both hosts. `--runs` without `--rehearsal` is refused before
any VM starts (exit 2), as `DA_S1_RUNS` is in a real session. The SEQUENCE is that of `s1` for the listed runs
(`tests/test_session_s1_int.py` pins the one below).

`--ackermann-gains default|v1` (the lead's decision of 2026-11-20, every kind with a simulator host) gives the world
side's Ackermann controller gains to every world and calibration step (`warmup`, `calibrate`, `world_<run>`) as env
`DA_ACKERMANN_GAINS`; `session.json` records it at the top level and in `score_runs.<run>`. The default is `default`;
any other value is refused (exit 2). The owner chose `v1` for the judged runs (D-S1-2, 2026-11-21), so every `s1`
line here gives it, the rehearsal's too: the rehearsal runs as S1 does (`tests/test_s1_readme_lines.py`).

```bash
C=FULL_SHA_OF_THE_COMMIT_UNDER_TEST      # replace: the integration commit under test
cd /home/mrk/de4sdv-worktrees/p10-$C || exit 1
S=implementation/driver-assistance-bench/session
# the rehearsal's run list, committed beside s1_runs.tsv: SC-DRIVING-012@20 r1, then stop further
R="$PWD/$S/s1_rehearsal_runs.tsv"
D=$HOME/.hermes/cache/scratch/b13-dry-$(date -u +%H%M%S); mkdir -p "$D"
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin FAKE_DIR="$D" DA_GCLOUD="$PWD/$S/tests/fake_gcloud.py" \
  DA_MAKE_H="$PWD/$S/tests/stubs/make_h.sh" \
  bash $S/da_session.sh --kind s1 --without-guest-host --camcal settings --ackermann-gains v1 --cap-eur 2.50 --rehearsal --runs "$R" --dry-run --evidence-root "$D/ev"; echo "dry run rc=$?"
SID=$(date -u +%Y%m%dT%H%M%SZ)
systemd-run --user --unit=da-session-$SID --collect --working-directory="$PWD" \
  -p KillMode=mixed -p TimeoutStopSec=infinity -p SendSIGHUP=no \
  -p StandardOutput=append:$HOME/s1-rehearsal-$SID.out -p StandardError=append:$HOME/s1-rehearsal-$SID.out \
  /usr/bin/env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin \
  /bin/bash $S/da_session.sh --kind s1 --without-guest-host --camcal settings --ackermann-gains v1 --cap-eur 2.50 --rehearsal --runs "$R" --session-id "$SID"
# end it early: systemctl --user kill --kill-who=main -s TERM da-session-$SID   (never kill -9)
```

### The exit trap's pre-stop budget

On a signal or the cost cap, the exit trap runs these steps before any VM stops, each in a slot of its own bound. The pre-stop phase (`PRESTOP_S`) is the sum of the
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
| s1 with the guest host | 2280 s | 300 + 300 + 120 + 300 + 3 x 420 |
| s1 --without-guest-host | 1560 s | 300 + 0 + 120 + 300 + 2 x 420 |

`tests/test_session_dryrun.py` checks these sums against the script's defaults and pins a dry run in which the
capture's stop and the S-CORE side's stop both run to their bounds and the guest host is still fetched before the
guests' stop. The cost watchdog still ends the session at the cap; each VM's safety net fires at the cap plus the kind's budget plus 10 min, counted from its
arming, so it never cuts the phase. At its bounds the phase costs, past the cap, about EUR 1.03 in p10-1
(2.37 EUR/h), EUR 0.33 in p10-3 (0.754 EUR/h), EUR 1.67 in p10-2 (2.641 EUR/h) and EUR 1.03 in p10-2 without the
guest host. That is the phase alone. The worst case past the cap adds the watchdog's 30 s, the guests' stop (up to
2 x (300 + 60) s on the guest host, 0.271 EUR/h) and the GPU hosts' stop until TERMINATED (about 1 to 2 min): about
EUR 1.1 in p10-1, EUR 0.4 in p10-3, EUR 1.8 in p10-2 and EUR 1.1 in p10-2 without the guest host.

One limit remains (R5 of the closure check of 7befc3c1, open): a slot can overrun, and the overrun comes out of the
last fetch, the guest host's. A failed poll's status read (`TRAP_GC_TO_S`, 30 s) and a sleep after the last poll run
past their slot's end. With every call hanging to its bound, the closure check's scaled harness cut the guest host's
fetch by about a quarter (110 s of 420 at full scale); with healthy SSH the overrun is only the last sleep (about
22 s). The phase still ends at its bound, and a host whose slot is gone is recorded as not fetched.

### The evidence fetch

At the end of a session (and in the exit trap) each host packs its `~/da-kit/<id>/out` with `host_step.sh pack`,
which prints the pack's sha256 and its size in bytes (`<sha256> <bytes>`). The session then copies `out.tgz` into
`incoming_<id>/<role>/`, compares the sha256 with the host's and unpacks it.

- **A host reached through IAP** (the simulator host, `SIM_SSH_IAP=1`) is read as ranges. In session
  20261120T092051Z the simulator host's pack held two chase videos (305,986,299 B); its single `gcloud compute scp
  --tunnel-through-iap` ran at about 150-175 KB/s, was cut at its 1200 s bound at about 208 MB, and the session ended
  exit 5 by `fetch`. The lead then read the same file as 37 ranges of 8 MiB over 8 parallel IAP tunnels in 4 min 57 s
  (about 1.03 MB/s), sha256 equal. The session now does the same:
  - the pack is cut into ranges of `FETCH_RANGE_MIB` MiB (default 8), read `FETCH_PARALLEL` at a time (default 8;
    both in `hosts.env`, whole numbers of at least 1, recorded in `session.json`);
  - each range is one `gcloud compute ssh --tunnel-through-iap --ssh-flag=-T --command "dd if=$HOME/da-kit/<id>/out.tgz
    bs=1M skip=<k> count=<n> status=none"`: `dd` writes to the tunnel, nothing is written on the host, and `-T` keeps a
    pty from changing the bytes;
  - each range gets up to 3 tries, each bounded by `FETCH_TRY_BASE_S` (30 s) plus twice the range at its tunnel's
    share of the planning rate (8 MiB over 8 tunnels: 165 s; the slowest range of the lead's fetch took 87 s), and each
    try is size-checked against the range's own length (the last range is short);
  - the ranges are joined in order, and the joined file's sha256 must equal the host's;
  - every try is a row of `<role>/fetch_ranges.tsv`: `range`, `try`, `start_s`, `end_s` (Unix seconds), `bytes`,
    `want`, `result` (`ok`, `short`, `rc 124` for a try cut at its bound, `size <n>`).
- **The whole fetch is bounded by the pack's size:** `FETCH_BASE_S` (60 s) plus the size at 1 MB/s (`FETCH_PLAN_BPS`,
  about the lead's 1.03 MB/s), never above the pre-stop phase's fetch budget of a host (`TRAP_PACK_S` +
  `TRAP_SCP_S`: 420 s, the slot of each fetch in the exit trap; there the bound is also cut to the slot's time left
  after the pack, and `session.log` says so). `session.log` gives the bound before the first range (`fetch of <vm>
  by ranges: out.tgz <bytes> B ..., bound <s> s (...)`). Past the bound no new try starts and the fetch fails.
- **A pack over the budget is a fetch owed.** A pack that needs more than 420 s at that rate (above about 360 MB; S1's
  15 chase videos, about 2.2 GB, would need 2260 s, which is why the pack leaves them out: an `s1` pack is about 50 MB)
  is not read at all: the session says so in `session.log` (`... needs
  <s> s ..., more than the bound 420 s ...: not read by the session`), leaves the pack on the host as
  `~/da-kit/<id>/out.tgz`, and ends exit 5 with `ended_by` `fetch` once every host was fetched. `not_fetched` names
  it as "`sim: ~/da-kit/<id>/out.tgz sha256 <sha256> <bytes> B (fetch owed)`", and `fetch.sim` holds the
  `sha256`, `bytes` and `result` `skipped: ...`. A ranged fetch that fails on a `RUNNING` host keeps its whole
  ranges in `sim/.ranges` (beside the file `pack`: the pack's sha256, bytes and range MiB) and is named the same
  way, with "`; <k> of <n> ranges whole in sim/.ranges`". Then follow "A fetch owed" below.
- **A host reached by direct SSH** (the S-CORE host, the guest host) keeps its single `gcloud compute scp`, bounded at
  1200 s (300 s in the exit trap).
- Every failure path reads the VM's state (`lost_check`): a pack whose SSH failed or that printed no sha256 and size,
  a range that failed its 3 tries or a fetch past its bound. A host that is not `RUNNING` then is a lost host
  (`host_lost`, exit 3, `hosts_lost.<role>.detected_by` `ranges: fetch`), never a failed fetch; on a `RUNNING` host
  the fetch fails (`fetch from <vm> failed: <the range and its last result>`, exit 5, `ended_by` `fetch`).
- A signal or the cap during the ranges ends every tunnel (the fetch's own TERM handler) and the fetch is not tried
  again, as for the scp. The one exception is the host watch's TERM for another host's loss: the fetch it cut is
  taken up again in the trap, in its slot (see "The host watch" above).
- `session.json` `fetch.<role>` records each host's last fetch: `method` (`ranges` or `scp`), `bytes`, `sha256` (the
  host's), `bound_s`, `result` (`ok`, `host lost`, `failed: ...`, `failed or changed ...`) and, for ranges, `ranges`,
  `tries`, `seconds`, `parallel`, `range_mib` and `ranges_file`.

### A fetch owed

A pack the session did not bring home (`not_fetched` "`sim: ~/da-kit/<id>/out.tgz sha256 ... (fetch owed...)`", or a
fetch a signal cut) stays on the simulator host's disk. Fetch it by hand after the session, before any run whose
records it holds is judged, with the G4 alone:

1. Wait until the session's unit is inactive (`systemctl --user is-active da-session-<id>`).
2. Run `fetch_owed.sh` on the lead host. It refuses unless the G4 reads `TERMINATED` and no `da-session-*` unit is
   loaded; it starts the G4 (on `ZONE_RESOURCE_POOL_EXHAUSTED` or a stockout it tries again every 3 min, for 1 h at
   most), reads the pack as ranges over `FETCH_PARALLEL` IAP tunnels with `dd` (nothing is written on the host), 3
   tries a range, each size-checked, keeps the whole ranges the session left in `sim/.ranges` when their `pack` file
   names the same sha256, joins the ranges in order, compares the sha256 with `fetch.sim.sha256` of `session.json`,
   unpacks into `sim/` and checks the session id. Its EXIT trap stops the G4 and reads `TERMINATED` back
   ("after: TERMINATED" on its last line). A fetch a signal cut has no sha256 in `session.json`: read it on the
   host first and pass `FETCH_OWED_SHA` and `FETCH_OWED_BYTES`.
3. Read `sim/fetch_owed.json` (`result` `ok`, the ranges kept and read, the seconds) and `sim/fetch_owed_ranges.tsv`.

```bash
SID=THE_SESSION_ID                       # replace: the session whose pack is owed
C=FULL_SHA_OF_THE_COMMIT_UNDER_TEST      # replace: that session's commit (its detached worktree, as above)
bash /home/mrk/de4sdv-worktrees/p10-$C/implementation/driver-assistance-bench/session/fetch_owed.sh \
  ~/.hermes/outputs/inc-driving-002/phase10/sessions/incoming_$SID
```

Cost: the G4 at 1.887 EUR/h, about 1.03 MB/s through 8 tunnels: about 37 min for S1's 2.2 GB (35 min of ranges plus
the start and the stop), about EUR 1.3; a pack of two runs (306 MB) about 9 min, about EUR 0.3. This is the model of
`sessions/incoming_20261120T092051Z/sim-lead-fetch/fetch_g4_ranges.sh`, which read attempt 3's pack the same way.

### Which hand fetch when: `fetch_owed.sh` and `fetch_chase.sh`

Both take the simulator host alone after the session, refuse while it is not `TERMINATED` or a `da-session-*` unit is
active, and stop it in their EXIT trap, so they run one after the other, never together:

- `fetch_owed.sh` only when `session.json` `not_fetched` names the simulator host's pack as a fetch owed (above): it
  brings the pack, `out.tgz`, without which no run of the session is judged.
- `fetch_chase.sh` after every `p10-2` and `s1` session whose `sim/out/pack_excluded.tsv` lists chase videos: it
  brings the videos the pack leaves out.
- `fetch_chase.sh --role score` after every `p10-2` and `s1` session whose `score/out/pack_excluded.tsv` lists
  visualization videos: the S-CORE host alone, by the same rules (from the bench folder:
  `bash session/fetch_chase.sh --role score <incoming dir>`; the `s1` block above runs it in a unit of its own).
- Both owed: `fetch_owed.sh` first. The videos' list, `pack_excluded.tsv`, is inside the owed pack, so `fetch_chase.sh`
  has nothing to read before it; `session.log` then names both commands in that order ("the simulator host's pack is
  owed ... first ... fetch_owed.sh ..., then ... fetch_chase.sh").

## Durations and costs

Expected lengths are PLAN's for each probe; prices from `hosts.env` (Spot, europe-west4, disks not counted).

| Kind | Hosts and EUR/h | Expected | Expected cost | Default cap (time at the cap) |
|---|---|---|---|---|
| `p10-1` | G4 1.887 + L4 0.483 | about 45 min (an estimate from the steps: the starts, both uploads, the CARLA start, the warm-up, the check about 10 min, the fetch and the stops); try 4 (SID 20261119T160111Z) took about 23 min and at most EUR 0.89 | about EUR 1.80 | EUR 3.50 (1.5 h), approved by the owner on 2026-11-19 |
| `p10-3` | L4 0.483 + guest host 0.271 | about 3 h | about EUR 2.26 | EUR 3.50 (4.6 h) |
| `p10-2` | G4 1.887 + L4 0.483 + guest host 0.271 | about 1.5 h | about EUR 3.96 | EUR 6.00 (2.3 h) |
| `s1` | G4 1.887 + L4 0.806 (on-demand, D-S1-3) + guest host 0.271 | about 2.0 h: 22 min to the first run, 14 runs of 5.5-6 min (about 82 min), the stop run about 7 min (its cap 42 s), the fetch and the stops about 6 min | about EUR 5.90 (about EUR 5.30 with the L4 on Spot) | EUR 8.00 (2.7 h) |
| `fetch_chase.sh --role score` after `s1` | L4 0.806 (on-demand, as in the `s1` it follows) | about 20 min of ranges for about 1 GB of visualization videos, plus about 4 min of start and stop | about EUR 0.32 | none: bounded as the chase fetch |
| `fetch_chase.sh` after `s1` | G4 1.887 | 37-43 min of ranges for about 2.2 GB at 1.03 MB/s, plus about 4 min of start and stop | EUR 1.3-1.5 | none: bounded by 120 s plus the bytes at 0.5 MB/s, its safety net 15 min after that |

The `s1` figures are those of the S1 build plan (section 4), from the times of 20261120T092051Z (attempt 3: 22 min from the
wrapper to the first world run, with 5 min of capacity rounds and 5.3 min of calibrate; a 30 s drive one cycle of
5.4-5.6 min); a run of S1 drives 25-60 s.

Fixed overheads in every session: each start 1-3 min (more in rounds when Spot capacity is short), SSH and kit
upload about 2 min per host, the guests' bring-up 10-15 min, the fetch 5-7 min and the stops 1-2 min. The fetch: the
simulator host's pack by ranges through IAP at about 1 MB/s (two runs' chase videos, 306 MB, took about 5 min; at most
420 s, the bound). The pack now leaves every chase video out (`pack_excluded.tsv`, fetched after the session by
`fetch_chase.sh`), so an `s1` pack holds no chase video and takes about a minute. Then the S-CORE host and the guest
host by scp (seconds to a few minutes each; at most 1200 s each). Attempt 3 at the old head fetched for 21.5 min
(09:58:29Z to 10:20:03Z). The fetch runs inside the cap: the cost watchdog counts every host from its start call to
now (`cost_now`), and the preflight line of `session.log` says so ("the cap of <EUR> is <s> s of all of them, the fetch
at the end included"). A cap reached during the fetch cuts it, and the trap does not try it again, so a kind's cap
must hold its runs plus that fetch; the cap of each kind covers it, the `s1` cap's 6 min for the fetch and the stops
included.

## Entry-point contracts

Each entry is a path relative to the bench folder (`entrypoints.env`, overridable from the environment). The session
runs it on its host detached through `remote/host_step.sh start`, with the bench folder as the working directory and `DA_OUT`,
`DA_SESSION_ID` and `DA_BENCH` set. The first argument is the step's output folder; everything the entry writes there
is fetched. Exit 0 means the step succeeded; any other status ends the session (the VMs stop).

| Variable | Host | Arguments | Owner | Contract |
|---|---|---|---|---|
| `ENTRY_SCORE_P10_1` | S-CORE | `<out>`; env `DA_P10_1_CARLA_HOST` (`p10-1`: the simulator host's address, set by the session) | S-CORE build lane | the build check, the clip replay, the late subscriber; its verdicts in `<out>`; started after the world's go, so its full start finds a ticking world |
| `ENTRY_SCORE_START` | S-CORE | `<out> <carla_host or none>`; env `DA_CAMERA_CALIBRATION_DIR` and `DA_SPEED_LIMIT` (`p10-2`, `s1`); `DA_B2_BUNDLE` (every S-CORE entry, `--candidate pr427`) | Launch Manager lane | starts the Launch Manager with its processes (identity recorder first); copies `H.yaml` and `homography_C_matrix.yaml` from `DA_CAMERA_CALIBRATION_DIR` into the candidate's working directory before the identity record; stages `speed_limit` from `DA_SPEED_LIMIT` and prints one `SCORE_CONFIG` line once up, then one `SCORE_PLATFORM` and one `SCORE_GPU` line (`score_platform_record.py`: the bundle's own facts and `nvidia-smi`, each a JSON object, a value it cannot read `{"absent": <reason>}`); returns 0 when they run, without waiting for a camera image (the world holds its first tick until the session's go file); called once per run, each with its own `<out>`; someipd offers 0x4df1 |
| `ENTRY_SCORE_INJECT` | S-CORE | `<out>` | warning-app lane | `p10-3`: publishes test warning requests on the candidate's mw::com event; returns when done |
| `ENTRY_SCORE_STOP` | S-CORE | `<out>` (the start's) | Launch Manager lane | ends the processes (SIGTERM, so the candidate's `.rrd` and the visualization file are finished) and collects their files; in mode full it moves the visualization recording into `<out>/score_side/visualization/` and writes `<out>/visualization_recording.json`; the world still ticks meanwhile |
| `ENTRY_SIM_SETUP` | simulator | `<out>` | this lane: `remote/sim_setup.sh` | CARLA server up on port 2000, NVENC test, free disk; the world side's map (`WORLD_MAP` of `world-side/scripts/common.sh`) in the server's `get_available_maps()`, or it fails naming the AdditionalMaps pack (`world-side/README.md`, "The maps pack") |
| `ENTRY_SIM_WARMUP` | simulator | `<out>`; env `DA_ACKERMANN_GAINS` (`default` or `v1`, the session's `--ackermann-gains`) | `../world-side/scripts/warmup.sh` | the survey, the session's road in `world_start.json`, the warm-up pass with every camera (hero role `hero`, moved by pose) |
| `ENTRY_SIM_CALIBRATE` | simulator | `<out> <checkerboard or settings>` (the session's `--camcal`); env `DA_ACKERMANN_GAINS` | `../world-side/scripts/calibrate.sh` | ASM-DRIVING-005 and the camera capture, role `de4sdv_calibration`, no candidate; required for `p10-2` |
| `ENTRY_SIM_RUN` | simulator | `<out> <scenario> <setting>`; env `DA_ACKERMANN_GAINS` | `../world-side/scripts/run_scenario.sh` | one run (`SC-DRIVING-012 20kmh`, or `ASM-DRIVING-006 20kmh`; `s1`: `<scenario> <setting id>` of each run of `s1_runs.tsv`, the stop run `S1_STOP_SCENARIO S1_STOP_SETTING`), detached, with the go/release handshake (`../world-side/README.md`); its records in `<out>/simulator/`; in `p10-1` the world of `P10_1_SCENARIO` `P10_1_SETTING` with `RELEASE_WAIT_S` above the check's bound |
| `ENTRY_SCORE_PATH_STOP` | S-CORE | `<out>` (the step's own folder, `path_stop_<run>`) | score-side lane: `../score-path/scripts/path_stop.sh` | `s1`'s stop run, at the go + 12 s: activates the Launch Manager's run target `path_stopped` and prints one JSON line `{"runTarget":"path_stopped","stopInstantRealNs":<int>,"stopInstantMonoNs":<int>,"rc":<int>}` (shared contract 3); exit 0 and `rc` 0 when the target is active |
| `ENTRY_SCORE_DISK` | S-CORE | `<out> <need_bytes> <need_stage_bytes>` | this lane: `../score-path/scripts/disk_check.sh` | `p10-2`'s first step, and `s1`'s before each S-CORE start (`disk_check_<run>`, one run's need in both arguments): exit 0 when `<out>`'s filesystem has `<need_bytes>` free (and the stage's `<need_stage_bytes>` when it is another filesystem), 9 ("DISK SPACE SHORT") otherwise; one `DISK_CHECK` line and `<out>/disk_check.json`; deletes nothing |
| `ENTRY_SIM_RECORD` | simulator | `--out <dir>` | this lane: `../recording/chase_recorder.py` | started before the warm-up and before the run, ends on its own; writes `<dir>/listening` once it took its list of the heroes already there, and the session waits for it (bounded) before the warm-up and before each recorded run's world |
| `ENTRY_GUEST_UP` | guest | `<out>` | this lane: `remote/guest_up.sh` | both guests created fresh (`launch_two_vms.sh down`, `up`) and booted; `getenforce` recorded, `setenforce 0` on the IVI only with `IVI_PERMISSIVE=1`; one `GUEST_IMAGE <sdv_core|ivi> serial= product= build_id= fingerprint= vbmeta_digest=` line per booted guest in its tail (`unread` for a property with no answer) |
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
from its own simulator host), and `DA_B2_BUNDLE`, which only `--candidate pr427` sets (refused as a `--remote-env`). A changed guess of the first `p10-3` (the broker's line, say) is then a setting
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
above the check's bound, and the cap of EUR 3.50. Since p10-2 attempt 2 (20261119T203947Z): a host lost while none
of its steps is polled (the host watch ends the session within its interval, the lost host gets no SSH), the watch
reading only the VMs this session started and only until the trap's own stops, a step failed after or before a loss,
a host lost before or during the final fetch, GCP's preemption time (`compute operations list`, which the fake answers
in the zone's offset), and each run's adapter attach (`adapter_attach.py`, fed with the adapter's real record lines).
`tests/test_session_s1.py` covers the kind `s1` (the run list against the model's seven settings, its `SEQUENCE`, the
disk check before each S-CORE start and a short disk before run k, each run's record and scenario digest, the stop
run's path stop and its JSON line, the candidate option and its staged facts, the pack without chase videos) and
`fetch_chase.sh` against the fake gcloud (a host not `TERMINATED` or a session unit refused, the ranges and the
sha256, a mismatch, the capacity rounds).
`tests/test_remote_scripts.py` runs the guest-host scripts and the safety net against fake `cvd`,
`adb`, `pgrep`, `sudo` and `ip`. The stubs in `tests/stubs/` stand for the S-CORE side's entries (another lane's)
and for `make-h` in dry runs; they never run on a host.

What the dry runs cannot show, and the sessions must: the real SSH and scp paths (IAP included) and their times, the
gcloud output formats the fake imitates, the VXLAN between the S-CORE host and the guest host, the CARLA port from
the S-CORE host to the simulator host on `carla-net` (brief R5, D5), the broker's log line for the unit's
registration, that the S-CORE side's start returns before the first image, the systemd timer of the guest host's
safety net, and the real costs.
