#!/bin/bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): starts the S-CORE side on the S-CORE host (ENTRY_SCORE_START of
# session/entrypoints.env; contract in session/README.md "Entry-point contracts").
#
#   start_score_side.sh <out> <carla_host or none>
#
# 0. Refuses (exit 4) only while a Launch Manager really runs: the state's pid is alive and is a Launch Manager, or a
#    process runs $DA_STAGE/bin/launch_manager. If the stage holds files that no stop has collected (a start whose
#    stop never ran or failed), it first runs stop_score_side.sh into <out>/previous_stage (which also ends staged
#    processes left without a Launch Manager); if that collection fails, it refuses (exit 3) and clears nothing.
#    One p10-2 starts and stops three times (calib_steer, run1, run2), each with its own <out>.
# 1. Stages the bundle and the bench's configs under $DA_STAGE (/tmp/de4sdv-da-bench) with stage_score_side.py:
#    mode full with a CARLA host (all five processes), mode path with none (the warning path only: the identity
#    recorder, someipd and gatewayd; the candidate's process and the adapter are started by no run target, so the
#    P10-3 test publisher can offer the candidate's warning event). The camera calibration comes from
#    DA_CAMERA_CALIBRATION_DIR (H.yaml and homography_C_matrix.yaml): mode full refuses without it (exit 3) and
#    never takes the bundle's upstream files; mode path falls back to them. Which one was staged, with the sha256 of
#    both files, goes to <out>/camera_calibration.json; the identity record hashes the staged files.
# 2. Starts the Launch Manager as root, detached, in $DA_STAGE (LM_BIN, default $DA_STAGE/bin/launch_manager, with
#    LM_ARGS). It reads the serialized configuration staged at $DA_STAGE/etc/launch_manager_config.bin, and mw::com in
#    it reads the daemon's own configuration staged at $DA_STAGE/etc/mw_com_config.json (without it the daemon aborts).
# 3. Waits (DA_START_TIMEOUT_S, default 120) until the Launch Manager runs, the identity recorder has written and
#    offered the record and reported running, someipd and gatewayd run, and in mode full the processes of
#    vision_pilot and actuation_adapter exist. It does NOT wait for the candidate to report running or for a camera
#    image: the world holds its first tick until the session's go file, which the session writes after this start
#    returns, within the candidate's ready timeout of 420 s (launch-manager/README.md "What the session must do").
# 4. Writes the state ($DA_STAGE/state/score_side.env, a copy in <out>) for stop_score_side.sh and the other entries.
#
# Exit status: 0 up; 2 usage; 3 staging failed; 4 already running; 5 the Launch Manager ended; 6 not up in time
# (then stop_score_side.sh collects what there is).
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH=$(cd -- "$HERE/../.." && pwd)
# shellcheck source=lib_score_side.sh
. "$HERE/lib_score_side.sh"

OUT=${1:?usage: start_score_side.sh <out> <carla_host or none>}
CARLA=${2:?usage: start_score_side.sh <out> <carla_host or none>}
: "${DA_START_TIMEOUT_S:=120}"
: "${LM_BIN:=$DA_STAGE/bin/launch_manager}"
: "${LM_ARGS:=}"
mkdir -p "$OUT"
LOG=$OUT/start_score_side.log
exec > >(tee -a "$LOG") 2>&1

if [ "$CARLA" = none ]; then MODE=path; COMPONENTS=$COMPONENTS_PATH; else MODE=full; COMPONENTS=$COMPONENTS_FULL; fi
ss_log "start_score_side: mode $MODE, CARLA host $CARLA, stage $DA_STAGE, bundle $DA_B2_BUNDLE"

if running=$(ss_lm_running); then
  ss_log "REFUSED: a Launch Manager of an earlier start still runs (pid $running); run stop_score_side.sh first"
  exit 4
fi
if [ "$MODE" = full ] && [ -z "${DA_CAMERA_CALIBRATION_DIR:-}" ]; then
  ss_log "REFUSED: mode full needs DA_CAMERA_CALIBRATION_DIR (the session's H.yaml and homography_C_matrix.yaml);" \
    "it never stages the bundle's upstream calibration"
  exit 3
fi
# never clear files that no stop has collected yet
if [ -d "$DA_STAGE/state" ] && [ ! -f "$DA_STAGE/state/collected" ]; then
  ss_log "the stage holds files no stop has collected (previous <out>: $(ss_state OUT)): collecting them first"
  bash "$HERE/stop_score_side.sh" "$OUT/previous_stage"
  rc=$?
  if [ ! -f "$DA_STAGE/state/collected" ]; then
    ss_log "REFUSED: the previous stage could not be collected (stop exit $rc); $DA_STAGE is left as it is"
    exit 3
  fi
  ss_log "previous stage collected into $OUT/previous_stage (stop exit $rc)"
fi

# shellcheck source=../../score-build/pins.sh
. "$BENCH/score-build/pins.sh"
stage_args=(--bundle "$DA_B2_BUNDLE" --stage "$DA_STAGE" --mode "$MODE" --carla-host "$CARLA"
            --upstream-revision "$VP_COMMIT" --require-serialized)
[ -n "${DA_CAMERA_CALIBRATION_DIR:-}" ] && stage_args+=(--calibration-dir "$DA_CAMERA_CALIBRATION_DIR")
[ -n "${DA_SPEED_LIMIT:-}" ] && stage_args+=(--speed-limit "$DA_SPEED_LIMIT")
[ "$DA_STAGE" != /tmp/de4sdv-da-bench ] && stage_args+=(--allow-any-stage)
if [ -n "$DA_SUDO" ]; then
  # the stage of an earlier run is root's: clear it as root first
  $DA_SUDO rm -rf "$DA_STAGE" || { ss_log "cannot clear $DA_STAGE"; exit 3; }
fi
if ! "$DA_PYTHON" "$HERE/stage_score_side.py" "${stage_args[@]}"; then
  ss_log "staging failed"
  exit 3
fi
cp "$DA_STAGE/state/staging.json" "$OUT/staging.json"
cp "$DA_STAGE/state/camera_calibration.json" "$OUT/camera_calibration.json"
ss_log "camera calibration: $(sed -n 's/.*"source": "\(.*\)",/\1/p' "$OUT/camera_calibration.json" | head -1)" \
  "from $(sed -n 's/.*"dir": "\(.*\)",/\1/p' "$OUT/camera_calibration.json" | head -1)"
[ -x "$LM_BIN" ] || { ss_log "no Launch Manager binary at $LM_BIN"; exit 3; }

ss_clock_record > "$OUT/clock_start.txt"
LM_LOG=$DA_STAGE/state/launch_manager.log
LM_PIDFILE=$DA_STAGE/state/launch_manager.pid
# As root, detached in its own session, with the stage as its working directory.
# shellcheck disable=SC2086
$DA_SUDO bash -c 'cd "$1" || exit 1; log=$2; pidfile=$3; shift 3
  setsid nohup "$@" > "$log" 2>&1 < /dev/null & echo $! > "$pidfile"' \
  lm "$DA_STAGE" "$LM_LOG" "$LM_PIDFILE" "$LM_BIN" $LM_ARGS
sleep 0.2
LM_PID=$(cat "$LM_PIDFILE" 2>/dev/null)
[ -n "$LM_PID" ] || { ss_log "the Launch Manager did not start (no pid)"; exit 5; }
ss_log "Launch Manager pid $LM_PID: $LM_BIN $LM_ARGS"
{
  echo "MODE=$MODE"; echo "CARLA_HOST=$CARLA"; echo "STAGE=$DA_STAGE"; echo "LM_PID=$LM_PID"
  echo "LM_BIN=$LM_BIN"; echo "STARTED_REAL_NS=$(date +%s%N)"; echo "OUT=$OUT"; echo "STATE=starting"
} > "$OUT/score_side_state.env"
$DA_SUDO cp "$OUT/score_side_state.env" "$SCORE_SIDE_STATE"

REC_LOG=$DA_STAGE/run/score/identityRecorder.jsonl
fail_up() {
  ss_log "NOT UP: $1"
  [ -r "$LM_LOG" ] && { echo "--- tail of the Launch Manager's log"; tail -n 40 "$LM_LOG"; }
  [ -r "$REC_LOG" ] && { echo "--- the identity recorder's errors"; grep -F '"event":"error"' "$REC_LOG" | tail -5; }
  bash "$HERE/stop_score_side.sh" "$OUT" || true
  exit "$2"
}
deadline=$(( $(date +%s) + DA_START_TIMEOUT_S ))
while :; do
  ss_alive "$LM_PID" || fail_up "the Launch Manager ended" 5
  missing=""
  lifecycle=$(ss_last_event "$REC_LOG" lifecycle)
  case "$lifecycle" in
    *'"state":"running_reported"'*) ;;
    *'"state":"error"'*) fail_up "the identity recorder could not report running (lead fallback: type Native)" 6 ;;
    *) missing="$missing identity_recorder(report_running)" ;;
  esac
  for name in $COMPONENTS; do [ -n "$(ss_pids_of "$name")" ] || missing="$missing $name"; done
  [ -z "$missing" ] && break
  [ "$(date +%s)" -ge "$deadline" ] && fail_up "after ${DA_START_TIMEOUT_S} s still missing:$missing" 6
  sleep 0.5
done

record=$(ss_last_event "$REC_LOG" record)
RECORD_SHA256=$(echo "$record" | sed -n 's/.*"sha256":"\([0-9a-f]\{64\}\)".*/\1/p')
{
  echo "STATE=up"
  echo "RECORD_SHA256=$RECORD_SHA256"
  for name in $COMPONENTS; do
    pid=$(ss_pids_of "$name" | head -1)
    echo "PID_${name}=$pid"
    echo "START_S_${name}=$(ss_start_s "$pid")"
  done
  echo "UP_REAL_NS=$(date +%s%N)"
} >> "$OUT/score_side_state.env"
$DA_SUDO cp "$OUT/score_side_state.env" "$SCORE_SIDE_STATE"
ss_log "S-CORE side up (mode $MODE): $(grep '^PID_' "$OUT/score_side_state.env" | tr '\n' ' ')"
ss_log "candidate record sha256 $RECORD_SHA256"
[ "$MODE" = full ] && ss_log "the candidate reports running after its first pass: start the world pacer within 420 s"
exit 0
