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
to `/dev/null` so the call returns at once. `stop` sends SIGINT, so the file is finished. The clock offset to the
guest host is measured with `../session/remote/ivi_clock.sh measure` (Cristian's method: 15 reads, the shortest
round trip gives the offset and a bound of half of it).

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
  shell, segments ended by the time limit and by the stop (SIGINT), the stills per display, the sha256 of every file,
  the measured offset within its bound; the clock set brings the offset to within the bound.
- `tests/test_compose_side_by_side.py`: on flat-level synthetic videos made with ffmpeg, the pane pixels of every
  output frame show the source frame the test computes from the synthetic times, a chase stall included; the
  manifest's digests; the refusals.

What only the sessions can show: NVENC and the 20 Hz rules with view B on the G4 (`p10-2`), the screenrecord frame
rate and t0 on the IVI guest, the clock bound over the real adb path, and any sound route (`p10-3`).
