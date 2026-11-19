# Bench recording (INC-DRIVING-002)

Status: draft, not yet validated. Only the local tests below have run; nothing here has recorded a bench run.

## The problem

The owner wants to see a run: what happens around the car in the simulator, and what the driver's display shows at
the same moment. Both must be real captures, never a rendered stand-in, and a viewer must be able to check that the
two sides belong to the same instant. Three scripts do this: one records the simulator's chase view, one captures the
IVI display with its clock, and one puts the two side by side by their recorded clocks.

| Script | Host | What it does |
|---|---|---|
| `chase_recorder.py` | simulator host | chase view B (x -10 m, z 5 m, 15 degrees down on the spring arm, own pitch +11.57), 1920x1080, one image per 0.05 s step (20 fps of simulation time), NVENC with libx264 as the named fallback; `chase_view.mp4`, `chase_view.mp4.frames.csv`, `summary.json` |
| `display_capture.sh` | guest host | `adb screenrecord` of the IVI display in segments, each launch bracketed by two reads of the guest clock; `screencap -d` per display; the clock offset at the start and the end; `dumpsys media.audio_flinger`; the window's logcat; the app's own timestamp record; `capture.json` with sha256 |
| `compose_side_by_side.py` | lead host, after the session | the side-by-side 1920x1080 video with the visualization inset, the two clocks and one caption line; `manifest.json` and `timeline.csv` |

The chase camera stands for no sensor of the vehicle, as the phase 8 model's simulator server says. The candidate's
visualization comes from the DE4SDV visualization recorder on the S-CORE host, an observer that goes only into the
bench's recording; it is not the driver's display. The inset is composited after the run by the composer, and its
manifest says so.

## The chase recorder

It is INC-DRIVING-001's recorder v3 with the changes listed in its header: view B, the full HD size, one frame per
step, the NVENC test and fallback, the 120 s wait for the simulator's world, the 20 s grace for ffmpeg, and a frames
CSV (`video_index, carla_frame, sim_time_s, arrival_unix_s`). It lists the heroes on the server before its encoder
test and attaches to the first new hero, so a hero that appears during the test encode is still taken. It exits 0
only if it attached and wrote frames; the session's lap rule reads that.

Run by the session (`--out` only); by hand: `/opt/sim20g4/venv/bin/python chase_recorder.py --out <dir>`.

## The display capture

`display_capture.sh start <dir>` (detached) and `display_capture.sh stop <dir>`. The guest clock is read with
`date +%s.%N` in the same guest shell immediately before and after the backgrounded `screenrecord`, whose output goes
to `/dev/null` so the call returns at once. `stop` sends SIGINT, so the file is finished. No segment starts after a
stop. A stop that comes after a segment ended by its time limit (at the poll that finds it ended) leaves that
segment `time-limit` and the capture's `end` `stop`. A recording that reaches its time limit between the poll and the
SIGINT says `time-limit` too: the signal reports whether it reached a live process (`kill -INT ... && echo sent`). The clock offset to the guest host is measured
with `../session/remote/ivi_clock.sh measure` (Cristian's method: 15 reads, the shortest round trip gives the offset
and a bound of half of it).

### The gap at a segment boundary

`screenrecord` stops at 180 s, so the capture records in segments of 170 s (`SEGMENT_S`). Between two segments the
display is not recorded. A warning shown in that span is missing from the video, so the span is kept small and every
one is reported.

What the span holds now, from segment k's last frame to segment k+1's first frame:

- the end of segment k's file (the muxer's finish after its time limit);
- the detection: within `NEAR_END_S` (2 s) of the time limit the capture polls every `FAST_POLL_S` (0.2 s) instead of
  every `POLL_S` (1 s), so at most 0.2 s plus one adb round trip;
- the next launch: one adb round trip. Its first guest clock read is also segment k's end read (`guest_end_s`), so
  no extra round trip is spent on that read;
- the encoder start of segment k+1 (about 0.2 s in INC-DRIVING-001, not yet measured on this guest).

So the expected span is about 0.2 s + 2 round trips + the encoder start + the file's finish, roughly 0.5 s on a local
adb link. Before the background pulls, the boundary also held the pull of segment k (about 170 MB, 17 s at 10 MB/s),
a separate clock read and up to 1 s of poll: up to about 18.5 s. The pull now runs in the background while segment
k+1 records (`pulls.jsonl`).

What the capture does around the recording of the cluster display:

- **The end of a segment.** The alive poll asks the guest `kill -0 <pid> && echo alive || echo ended <guest clock>`
  and reads adb's whole answer. A segment ends only on the guest's own `ended`. An empty or other answer (adb's
  `error: closed`, a time-out) is polled again; after `ALIVE_UNKNOWN_S` (15 s) without an answer the capture ends
  with `end: error`. It then sends the recording SIGINT, polls up to 5 more times, pulls the file only if the guest
  reports it ended (`no-answer` segment), and otherwise keeps it on the guest unpulled. The app's records and
  `capture.json` are still written.
- **A recording that ends early.** When the guest sees a recording end more than `EARLY_S` (2 s) before its time
  limit, with no stop asked (a full `/data`, a display gone, an encoder failure), the segment is labeled
  `ended-early`. The second early end ends the capture with `end: error` instead of relaunching.
- **The pulls.** At most `MAX_PULLS` (2) pulls run at a time; a segment whose pull cannot start yet waits its turn
  and is still pulled before the end. A pull writes `seg_<k>.mp4.part` and renames it to `seg_<k>.mp4` only when it
  has the guest's size; its sha256 is taken then, so the end never reads a whole recording again. The guest file is
  removed once the pull is complete. A failed or cut pull keeps the guest file, keeps the part as
  `seg_<k>.mp4.partial`, names the guest file (`pull_failures`, `guest_dir_kept`) and says so in `capture.done`;
  the capture still ends with exit 0, so the session still reads the app's records.
- **The guest's space.** The guest holds the segment that records and every segment not yet pulled: two while the
  pulls keep up with the segments (170 MB in 170 s, about 1 MB/s), more when they are slower. `df -k /data` is read
  at the start and again in every launch's own guest shell, after the second clock read (no time added to the
  bracket). The capture warns when less than two segments' bound is free, and keeps each reading
  (`guest_data_free_kb`, at the start and per segment). The IVI guest's `/data` size is not in the guest-build
  records.
- **Every adb call is bounded** with `timeout --foreground`: the alive poll by `POLL_TIMEOUT_S` (5 s), each segment
  pull by `PULL_TIMEOUT_S` (600 s), every other call by `ADB_TIMEOUT_S` (10 s), and the clock measurement by
  `CLOCK_TIMEOUT_S` (30 s). After the last recording ended, the app's records are pulled first, before the end
  stills, the audio dump, the logcat and the clock.
- `capture.json` and `capture.done` are written, and the guest's folder removed, only after every pull ended.

How to read the numbers: `capture.json` has one `boundaries` entry per boundary, on the guest clock:

- `unrecorded_min_s`: k+1's `guest_before_s` minus k's `guest_end_s`. Since the launch's first read is the end read,
  it is 0 for every segment but the last: the clock reads give no lower bound;
- `unrecorded_max_s` is null in `capture.json`: the capture reads no frame times, since a probe of every segment
  would make its end grow with the recording. `not_filled_here` and `unrecorded_max_where` say where it is
  computed: `compose_side_by_side.py`, on the host that composes, from the segments' packet times (no decode,
  `--probe-timeout-s` per file), in `manifest.json` `display.boundaries`. Segment k's first frame comes after its
  `guest_before_s` and segment k+1's last frame before its `guest_end_s`, so (k+1's `guest_end_s` minus its packet
  span) minus (k's `guest_before_s` plus its packet span) bounds the span from above. A display that did not change
  near either end makes the bound larger, never smaller. Quote this figure as the gap at a boundary.

The composer lists every held display frame at a segment boundary in `manifest.json` (`display.held_spans`, kind
`segment boundary`, with its output frames and the bounds), a boundary whose frame times overlap included, and, over
those frames, the IVI clock line reads "IVI display not recorded since ... (segment boundary)". A segment that was
not pulled is left out of the composition and listed as kind `segment not pulled`, from its launch to its end read.
`display.gap_free` is false when a boundary falls in the output or a segment was not pulled, and null otherwise.
Holds of at least `--held-span-min-s` (0.5 s) within a segment are listed too: a display that did not change, or an
encoder stall, which the frame times cannot tell apart. Never call a video gap-free.

The stop: `stop` waits `--wait-s` (60 s) for the capture's tail, counted from the stop or from the last progress of
the pulls (a pull that ended, or a local `.part` file that grew), plus the bytes still to pull at `PULL_BPS`
(10 MB/s, an assumption: no sustained adb pull rate from this guest is recorded). So a pull that keeps growing is
waited for up to the hard cap, `--wait-cap-s` (95 s from the stop). When the cap is reached, the stop exits 1 and
names the guest files still to pull. Those files stay on the guest until they are pulled.

The cap fits the session's step bound. The session gives the stop `T_CAPTURE_END` (180 s), counted from before
rstep's start SSH call:

```text
start SSH call (its time-out)            60 s
stop's cap                               95 s
stop's own last poll and exit             2 s
one status poll of rstep (POLL_S)        20 s
total                                   177 s  <= 180 s
```

What the cap allows a 900 s capture: at a stop, the stopped segment (up to 170 MB at 8 Mbit/s) is still to pull,
and the segment before it too when the stop comes within one pull's time of a boundary. The tail's other calls take
a few seconds. So the stop ends within its cap when the sustained pull rate is above about 2 MB/s (one full segment
pending) or about 4 MB/s (two). Below that, the session's window close fails.

What only a real multi-segment run on the IVI guest can show (p10-2's first run): the adb round trip and the
encoder start, so the real `unrecorded_max_s`; whether the background pull costs the recording frames (compare the
within-segment holds the composer lists with the pull times in `pulls.jsonl`); the real pull rate; and `/data`'s
free space. p10-3's single short window shows none of these: it has no boundary.

Sound (brief R8): no route is known to capture the Cuttlefish guest's audio on the host, so no audio is recorded. The
capture keeps the audio route state and the app's own timestamp record (`APP_RECORD_PATHS`); without that record the
sound start is unmeasured, and it is reported so.

## The composition

```bash
R=<incoming_id>   # the session's evidence folder
python3 compose_side_by_side.py \
  --chase $R/sim/out/rec_run/chase_view.mp4 \
  --display-capture $R/guest/out/capture \
  --inset $R/score/out/score/<visualization video> \
  --out $R/video --caption "SC-DRIVING-012 at 20 km/h. Left: CARLA chase view, VisionPilot's visualization inset placed after the run. Right: the IVI display."
```

How each side is placed (all on UTC; details in the script's header):

- a chase frame at the real time of its tick: `--tick-times` from the world side when given, else its arrival at
  the recorder; over a simulator stall the last frame is held;
- a display frame at t0 + pts on the IVI clock, t0 = the guest clock read just after the segment's launch plus
  `--display-t0-correction-s`, moved to the host's clock by the measured offset. Until that correction is read
  from the clock the app draws on the display (INC-DRIVING-001's `ivi_t0_frames.py` method), the display may lead
  by up to about 0.2 s;
- an inset frame: the newest visualization frame whose capture simulation time is at or before the chase frame's.
  The visualization recorder's `frames.csv` must carry that time (`--inset-time-column`, default `sim_time_s`); the
  composer refuses an inset without it.

On screen: the caption line, "simulation time <s>" under the chase view and "IVI clock <UTC>" under the display.
The raw files are only read: their sha256 are taken before and after and must be equal; the manifest lists them with
every offset used.

## Tests

- `tests/test_chase_recorder.py`: the spring-arm pitch rule against `math.atan2`; the encoder choice; a recording on
  a fake CARLA module (`tests/fake_carla/`) with the real ffmpeg: spawn pose and mount, frame count by ffprobe, the
  frames CSV, the label of 20 fps, the fallback named; a simulator that answers late; one that never answers.
- `tests/test_display_capture.py`: against a fake adb whose guest clock runs 0.25 s ahead: the bracket in one guest
  shell, segments ended by the time limit and by the stop (SIGINT), a stop that comes just after a segment's time
  limit (at the poll that finds it ended, and during its pull), the stills per display, the sha256 of every file, the
  measured offset within its bound; the clock set brings the offset to within the bound. The test orders the events
  through the fake (`FAKE_LIMIT_DIR`, `FAKE_HOLD_POLL`, `FAKE_HOLD_PULL`, `FAKE_HOLD_INT`), never by a sleep, and runs
  the bracket once more with every adb call 0.25 s slower (`FAKE_CALL_DELAY_S`), as on a loaded host. The boundary:
  segment 2 starts while segment 1's pull is held; a failed pull (`FAKE_PULL_FAIL`, which leaves half a file) is
  reported, keeps the guest file and leaves no file under the final name; a SIGINT that finds the recording ended
  says `time-limit`; the stop waits for a 6 s pull (`FAKE_PULL_DELAY_S`) and for an 8 s pull that grows
  (`FAKE_PULL_GROW`), gives up at its cap and names the guest file; the fast poll finds the end with `POLL_S` at 8 s.
  With the last segment's pull held past the stop, `capture.json` and `capture.done` come after it, with that file's
  sha256; with segment 1's pull held, segment 3 starts and the stop reaches it; an adb that writes more after `alive`
  (`FAKE_ALIVE_TAIL_S`) does not end a live recording. One failed poll (`FAKE_POLL_FAIL`) ends nothing; polls with no
  answer end the capture as an error that still writes its records. Recordings that die at once (`FAKE_DEAD_FROM`)
  are labeled `ended-early`, and the second ends the capture. With every pull held, only two run. A hung tail call
  (`FAKE_HANG`) costs neither the app's records nor the stop. An ffprobe that takes 30 s costs the stop nothing, and
  no line of the capture runs ffprobe. Static checks: every adb call has a bound, and the stop's cap fits the
  session's `T_CAPTURE_END`.
- `tests/test_compose_side_by_side.py`: on flat-level synthetic videos made with ffmpeg, the pane pixels of every
  output frame show the source frame the test computes from the synthetic times, a chase stall included; the
  manifest's digests; the refusals; a 1 s hold at a segment boundary listed with its output frames, the output not
  called gap-free, the IVI clock line saying the display was not recorded; one segment makes no gap-free claim. The
  boundary's upper bound from packet times, against the test's own probe; a packet probe that hangs is cut at its
  bound; a boundary whose frame times overlap is listed; a segment not pulled is left out and its span listed.

What only the sessions can show: NVENC and the 20 Hz rules with view B on the G4 (`p10-2`), the screenrecord frame
rate and t0 on the IVI guest, the clock bound over the real adb path, and any sound route (`p10-3`).
