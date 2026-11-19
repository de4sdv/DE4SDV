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
#    killed process records nothing itself. SHA256SUMS over everything collected.
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

LM_PID=$(ss_state LM_PID)
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
ok=0
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
    $DA_SUDO cp -a "$f" "$C/vision_pilot/$rel" || ok=1
  done < <(find "$DA_STAGE/vision_pilot" -type f -print0 2>/dev/null)
fi
[ -n "$DA_SUDO" ] && $DA_SUDO chown -R "$(id -u):$(id -g)" "$C"
if [ -r "$C/state/launch_manager.log" ]; then
  grep -n -i -E 'expired|run ?target|fallback|supervision|SIGKILL|terminat' "$C/state/launch_manager.log" \
    > "$C/supervision_events.txt" || true
fi
(cd "$C" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS) || ok=1
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
