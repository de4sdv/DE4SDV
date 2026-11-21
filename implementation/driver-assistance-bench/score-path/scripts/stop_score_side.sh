#!/bin/bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): stops the S-CORE side on the S-CORE host and collects its files
# (ENTRY_SCORE_STOP of session/entrypoints.env; contract in session/README.md "Entry-point contracts").
#
#   stop_score_side.sh <out>
#
# 1. SIGTERM to the Launch Manager of start_score_side.sh (its state in $DA_STAGE/state/score_side.env). The
#    Launch Manager switches to Off and ends the supervision first, then stops its processes in reverse order with
#    SIGTERM, so the candidate leaves its loop and finishes its .rrd and the visualization file
#    (launch-manager/README.md). The session calls this before the world stops ticking; otherwise the end of every
#    run reads as a supervision failure.
# 2. Waits DA_STOP_TIMEOUT_S (default 45: the candidate's shutdown timeout of 10 s and the others' 3 s, with the
#    run-target transitions). If the Launch Manager or a staged process is still there, SIGKILL, and exit 7.
# 3. Collects into <out>/score_side/: the Launch Manager's log, the run directory (the candidate record, every
#    component's log), what the candidate wrote into its working directory (.rrd, the visualization and its
#    frames.csv), the staged configuration, the state, the clocks at both ends, and the Launch Manager's own lines
#    on the supervision (Alive Supervision ... EXPIRED, the run target switch) in supervision_events.txt, since a
#    killed process records nothing itself. SHA256SUMS over everything collected. The candidate's Rerun record
#    (.rrd) is collected as a hard link where the stage and <out> share a filesystem (else a copy); its path, size and
#    sha256 go to <out>/candidate_rrd.json. It stays on this host: host_step.sh pack leaves every .rrd out.
#    In mode full, the candidate's visualization recording (patch 0001; the video DE4SDV_VISUALIZATION_RECORD of the
#    staged launch configuration names, and its sidecars <video>.frames.csv and <video>.summary.txt) is moved, before
#    the run directory is collected, into <out>/score_side/visualization/: a rename where the stage and <out> share a
#    filesystem, so nothing here copies the video. Its path, sha256 (the one SHA256SUMS holds), size and frames (the
#    rows of frames.csv) go to <out>/visualization_recording.json, and "<sha256> <bytes> <mtime s>" to <video>.sha256,
#    which host_step.sh pack reads to list the video in pack_excluded.tsv while it leaves the video on this host. A
#    missing or empty video is recorded there with its reason and changes neither the exit status nor the collection:
#    the recorder is an observer of the run (the owner's decision of 2026-11-17 keeps it in every run).
#
# 4. Only after a complete collection, marks the stage collected ($DA_STAGE/state/collected): start_score_side.sh
#    clears a stage only with that mark.
#
# Exit status: 0 stopped and collected (or nothing was running); 7 something had to be killed; 8 the collection
# failed.
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib_score_side.sh
. "$HERE/lib_score_side.sh"

OUT=${1:?usage: stop_score_side.sh <out>}
: "${DA_STOP_TIMEOUT_S:=45}"
mkdir -p "$OUT"
LOG=$OUT/stop_score_side.log
exec > >(tee -a "$LOG") 2>&1
RC=0
# one stop of a stage at a time: the p10-1 check's cut handler and the session's exit trap may both stop the same
# stage. The second waits (bounded) for the first, then finds nothing running and collects what is there
LOCK=${DA_STAGE%/}.stop.lock
if exec 9>> "$LOCK" 2>/dev/null; then
  flock -w $(( DA_STOP_TIMEOUT_S + 60 )) 9 || ss_log "stop_score_side: $LOCK still held after $(( DA_STOP_TIMEOUT_S + 60 )) s: going on"
else
  ss_log "stop_score_side: no lock file $LOCK: going on without it"
fi

LM_PID=$(ss_state LM_PID)
MODE=$(ss_state MODE)
if [ -z "$LM_PID" ]; then
  ss_log "stop_score_side: no state in $SCORE_SIDE_STATE: nothing was started"
else
  ss_log "stop_score_side: Launch Manager pid $LM_PID"
fi
ss_clock_record > "$OUT/clock_stop.txt"

# only a Launch Manager that really runs gets the signal (never a process that reused a stale pid)
if LM_PID=$(ss_lm_running); then
  $DA_SUDO kill -TERM "$LM_PID" 2>/dev/null || ss_log "SIGTERM to $LM_PID failed"
  ss_log "SIGTERM sent to the Launch Manager"
  deadline=$(( $(date +%s) + DA_STOP_TIMEOUT_S ))
  while ss_alive "$LM_PID" && [ "$(date +%s)" -lt "$deadline" ]; do sleep 0.5; done
  if ss_alive "$LM_PID"; then
    ss_log "FORCED: the Launch Manager still ran after ${DA_STOP_TIMEOUT_S} s: SIGKILL"
    $DA_SUDO kill -KILL "$LM_PID" 2>/dev/null
    RC=7
  else
    ss_log "the Launch Manager ended"
  fi
fi
# no staged process may outlive the Launch Manager
for name in $COMPONENTS_FULL candidate_record_probe warning_injector; do
  pids=$(ss_pids_of "$name" | tr '\n' ' ')
  [ -n "${pids// /}" ] || continue
  ss_log "LEFT OVER: $name (pids $pids): SIGTERM, then SIGKILL"
  # shellcheck disable=SC2086
  $DA_SUDO kill -TERM $pids 2>/dev/null
  sleep 2
  pids=$(ss_pids_of "$name" | tr '\n' ' ')
  # shellcheck disable=SC2086
  [ -n "${pids// /}" ] && $DA_SUDO kill -KILL $pids 2>/dev/null
  RC=7
done

# collect
C=$OUT/score_side
mkdir -p "$C"
collect() {   # collect <source> <name in C>
  [ -e "$1" ] || return 0
  $DA_SUDO cp -a "$1" "$C/$2" || return 1
}
ok=0; RRD_HOW=""
# the candidate's visualization recording (mode full): moved with its sidecars before run/ is collected, so the video
# is neither copied nor collected twice; a failed move leaves it in run/, collected there, and its record says so
VIS=""; VIS_NOTE=""
if [ "$MODE" = full ]; then
  VIS=$("$DA_PYTHON" -c 'import json, sys
c = json.load(open(sys.argv[1]))
print(c["components"]["vision_pilot"]["deployment_config"]["environmental_variables"].get("DE4SDV_VISUALIZATION_RECORD", ""))' \
    "$DA_STAGE/config/launch_manager_config.json" 2>/dev/null)
  if [ -n "$VIS" ] && [ -e "$VIS" ]; then
    mkdir -p "$C/visualization"
    for f in "$VIS" "$VIS.frames.csv" "$VIS.summary.txt"; do
      [ -e "$f" ] || continue
      $DA_SUDO mv "$f" "$C/visualization/" || VIS_NOTE="not moved: $f stayed in the stage and was collected under run/"
    done
  fi
fi
collect "$DA_STAGE/state" state || ok=1
collect "$DA_STAGE/run" run || ok=1
collect "$DA_STAGE/config" config || ok=1
collect "$DA_STAGE/facts/upstream_revision.txt" upstream_revision.txt || ok=1
if [ -d "$DA_STAGE/vision_pilot" ]; then
  mkdir -p "$C/vision_pilot"
  # what the candidate wrote: everything in its working directory but the staged inputs
  while IFS= read -r -d '' f; do
    rel=${f#"$DA_STAGE/vision_pilot/"}
    case "$rel" in config/*|modules/*|assets/*) continue ;; esac
    mkdir -p "$C/vision_pilot/$(dirname "$rel")"
    # the candidate's Rerun record (rrd_on = true, the evaluators' record; 4.7 GB for calib_steer of
    # 20261119T174606Z): a hard link where the stage and <out> share a filesystem, so the disk holds it once;
    # otherwise a copy. It stays on this host: the pack leaves it out (host_step.sh), candidate_rrd.json names it
    case "$rel" in
      *.rrd)
        if $DA_SUDO ln "$f" "$C/vision_pilot/$rel" 2>/dev/null; then RRD_HOW="$RRD_HOW $rel=hard_link"
        else $DA_SUDO cp -a "$f" "$C/vision_pilot/$rel" || ok=1; RRD_HOW="$RRD_HOW $rel=copy"; fi
        continue ;;
    esac
    $DA_SUDO cp -a "$f" "$C/vision_pilot/$rel" || ok=1
  done < <(find "$DA_STAGE/vision_pilot" -type f -print0 2>/dev/null)
fi
[ -n "$DA_SUDO" ] && $DA_SUDO chown -R "$(id -u):$(id -g)" "$C"
if [ -r "$C/state/launch_manager.log" ]; then
  grep -n -i -E 'expired|run ?target|fallback|supervision|SIGKILL|terminat' "$C/state/launch_manager.log" \
    > "$C/supervision_events.txt" || true
fi
(cd "$C" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS) || ok=1
# each Rerun record kept on this host: its path, size and sha256 (the one SHA256SUMS holds), computed here, in
# <out>/candidate_rrd.json and one CANDIDATE_RRD line each
RRD_JSON="["; sep=""
for x in $RRD_HOW; do
  rel=${x%=*}; how=${x##*=}; f=$C/vision_pilot/$rel
  sum=$(awk -v want="./vision_pilot/$rel" '{ p = $0; sub(/^[0-9a-f]+  /, "", p); if (p == want) print $1 }' "$C/SHA256SUMS" 2>/dev/null)
  size=$(stat -c %s "$f" 2>/dev/null || echo null)
  RRD_JSON="$RRD_JSON$sep
 {\"path\": \"$f\", \"bytes\": $size, \"sha256\": $([ -n "$sum" ] && echo "\"$sum\"" || echo null), \"stage_path\": \"$DA_STAGE/vision_pilot/$rel\", \"collected_as\": \"${how//_/ }\"}"
  sep=,
  ss_log "CANDIDATE_RRD path=$f bytes=$size sha256=${sum:-none} collected_as=$how (kept on this host; the pack leaves it out)"
done
printf '%s\n]\n' "$RRD_JSON" > "$OUT/candidate_rrd.json"
# the visualization recording kept on this host (mode full): <out>/visualization_recording.json, one
# VISUALIZATION_RECORDING line, and <video>.sha256 for the pack
if [ "$MODE" = full ]; then
  V=$C/visualization/$(basename -- "${VIS:-visualization.mkv}"); vsum=""; vbytes=""; vframes=""; vreason=""
  if [ -z "$VIS" ]; then
    vreason="no visualization recording: the staged launch configuration sets no DE4SDV_VISUALIZATION_RECORD for vision_pilot"
  elif [ -n "$VIS_NOTE" ]; then
    vreason="no visualization recording kept: $VIS_NOTE"
  elif [ ! -f "$V" ]; then
    vreason="no visualization recording: the candidate's process left no $VIS (its recorder did not start, or the process did not run)"
  else
    vbytes=$(stat -c %s "$V")
    [ -f "$V.frames.csv" ] && vframes=$(( $(wc -l < "$V.frames.csv") - 1 ))
    if [ "$vbytes" = 0 ]; then
      vreason="empty visualization recording: $VIS has 0 bytes ($(head -n 1 "$V.summary.txt" 2>/dev/null || echo 'no summary'))"
    else
      vsum=$(awk -v want="./visualization/$(basename -- "$V")" '{ p = $0; sub(/^[0-9a-f]+  /, "", p); if (p == want) print $1 }' "$C/SHA256SUMS" 2>/dev/null)
      [ -n "$vsum" ] || vsum=$(sha256sum "$V" | cut -d' ' -f1)
      printf '%s %s %s\n' "$vsum" "$vbytes" "$(stat -c %Y "$V")" > "$V.sha256"
    fi
  fi
  "$DA_PYTHON" - "$OUT/visualization_recording.json" "$([ -f "$V" ] && echo "$V")" "$vsum" "$vbytes" "$vframes" "$vreason" <<'PY'
import json, sys
out, path, sha, size, frames, reason = sys.argv[1:]
json.dump({"path": path or None, "sha256": sha or None, "bytes": int(size) if size else None,
           "frames": int(frames) if frames else None, "reason": reason or None}, open(out, "w"), indent=1)
PY
  if [ -n "$vsum" ]; then
    ss_log "VISUALIZATION_RECORDING path=$V bytes=$vbytes frames=${vframes:-unknown} sha256=$vsum (kept on this host; the pack leaves it out)"
  else
    ss_log "VISUALIZATION_RECORDING none: $vreason"
  fi
fi
[ "$ok" = 0 ] || { ss_log "COLLECTION INCOMPLETE"; [ "$RC" = 0 ] && RC=8; }
# the mark that lets the next start clear the stage: only after a complete collection
if [ "$ok" = 0 ] && [ -d "$DA_STAGE/state" ]; then
  echo "collected into $C $(date -u +%FT%TZ)" | $DA_SUDO tee "$DA_STAGE/state/collected" > /dev/null
fi
ss_log "collected $(wc -l < "$C/SHA256SUMS" 2>/dev/null || echo 0) files into $C"

if [ -f "$SCORE_SIDE_STATE" ]; then
  echo "STATE=stopped rc=$RC $(date -u +%FT%TZ)" | $DA_SUDO tee -a "$SCORE_SIDE_STATE" > /dev/null
  $DA_SUDO mv "$SCORE_SIDE_STATE" "$SCORE_SIDE_STATE.stopped"
fi
exit "$RC"
