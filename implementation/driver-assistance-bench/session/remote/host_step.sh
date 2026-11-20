#!/bin/bash
# One step of a bench session on one host, with uniform markers for the orchestrator (da_session.sh).
#
#   host_step.sh run    <step> -- <command...>   run in the foreground; exits with the command's status
#   host_step.sh start  <step> -- <command...>   run detached (setsid nohup); returns at once
#   host_step.sh status <step>                   prints "rc <N>", "running" (while any process of the step's
#                                                process group lives, its leader gone or not) or "absent"
#   host_step.sh signal <step> [INT|TERM]        signals the detached step's process group
#   host_step.sh tail   <step>                   the last 20 lines of the step's log
#   host_step.sh pack                            tars the host's output folder to <kit>/out.tgz, prints its sha256
#                                                and its size in bytes ("<sha256> <bytes>", the last line); every
#                                                *.rrd and every chase video (out/rec_*/chase_view.mp4) stays out
#                                                of it, listed in out/pack_excluded.tsv (a video with its sha256)
#
# Layout (made by the orchestrator's upload): ~/da-kit/<session id>/{session_id, bench/, out/}. This script lives in
# bench/session/remote/. Each step writes out/<step>.log and, when it ends, out/<step>.rc. The command runs with
# the bench folder as its working directory and DA_OUT, DA_SESSION_ID and DA_BENCH in its environment.
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DA_BENCH=$(cd -- "$HERE/../.." && pwd)
KIT=$(cd -- "$DA_BENCH/.." && pwd)
DA_OUT=$KIT/out
DA_SESSION_ID=$(cat "$KIT/session_id" 2>/dev/null || echo unknown)
export DA_BENCH DA_OUT DA_SESSION_ID
mkdir -p "$DA_OUT"

ACTION=${1:?run|start|status|tail|signal|pack}; shift
case "$ACTION" in
  run|start)
    STEP=${1:?step name}; shift
    [ "${1:-}" = "--" ] && shift
    [ $# -ge 1 ] || { echo "host_step: no command for $STEP" >&2; exit 2; }
    LOG=$DA_OUT/$STEP.log; RCF=$DA_OUT/$STEP.rc
    [ -e "$RCF" ] && { echo "host_step: step $STEP already ran in this session" >&2; exit 2; }
    if [ "$ACTION" = run ]; then
      echo "=== $STEP start $(date -u +%FT%T.%3NZ)" >> "$LOG"
      (cd "$DA_BENCH" && "$@") >> "$LOG" 2>&1; RC=$?
      echo "=== $STEP end rc=$RC $(date -u +%FT%T.%3NZ)" >> "$LOG"
      echo "$RC" > "$RCF"
      tail -n 20 "$LOG"
      exit "$RC"
    fi
    # detached: its own session and process group, so a later signal reaches the whole tree
    setsid nohup bash -c '
      STEP=$1 LOG=$2 RCF=$3; shift 3
      echo "=== $STEP start $(date -u +%FT%T.%3NZ)" >> "$LOG"
      cd "$DA_BENCH" && "$@" >> "$LOG" 2>&1; RC=$?
      echo "=== $STEP end rc=$RC $(date -u +%FT%T.%3NZ)" >> "$LOG"
      echo "$RC" > "$RCF"' host_step "$STEP" "$LOG" "$RCF" "$@" > /dev/null 2>&1 < /dev/null &
    echo "$!" > "$DA_OUT/$STEP.pid"
    echo "started $STEP pid $!"
    ;;
  status)
    STEP=${1:?step name}
    if [ -s "$DA_OUT/$STEP.rc" ]; then echo "rc $(cat "$DA_OUT/$STEP.rc")"
    # the step's own process group (setsid above): after a TERM its leader is gone at once, while its command may
    # still clean up, or a launch still create guests; the step runs until the last process of the group ends (S2)
    elif [ -s "$DA_OUT/$STEP.pid" ] && { P=$(cat "$DA_OUT/$STEP.pid"); kill -0 -- "-$P" 2>/dev/null || kill -0 "$P" 2>/dev/null; }; then
      echo running
    elif [ -s "$DA_OUT/$STEP.pid" ]; then echo "rc 255"   # ended without writing its status (killed)
    else echo absent; fi
    ;;
  tail)
    STEP=${1:?step name}
    tail -n 20 "$DA_OUT/$STEP.log" 2>/dev/null
    [ -s "$DA_OUT/$STEP.rc" ] && echo "=== $STEP end rc=$(cat "$DA_OUT/$STEP.rc")"
    ;;
  signal)
    STEP=${1:?step name}; SIG=${2:-INT}
    PID=$(cat "$DA_OUT/$STEP.pid" 2>/dev/null) || { echo "no pid for $STEP"; exit 1; }
    kill "-$SIG" -- "-$PID" 2>/dev/null || kill "-$SIG" "$PID" 2>/dev/null
    echo "signalled $STEP ($SIG)"
    ;;
  pack)
    cp "$KIT/session_id" "$DA_OUT/session_id"
    # the candidate's Rerun records stay on this host (4.7 GB for 42 s of calib_steer in 20261119T174606Z): each is
    # listed with its size in out/pack_excluded.tsv and left out of the pack; nothing is deleted
    # the chase videos too (C3 of the S1 build: about 144 MB a run, 2.2 GB for S1, past any fetch bound through IAP):
    # each is listed with its size and sha256 and fetched after the session by session/fetch_chase.sh
    (cd "$KIT" && { find out -type f -name '*.rrd' -printf '%p\t%s\n' | sort
      find out -type f -path 'out/rec_*/chase_view.mp4' | sort | while IFS= read -r f; do
        printf '%s\t%s\t%s\n' "$f" "$(stat -c %s "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"; done; }) > "$DA_OUT/pack_excluded.tsv"
    tar -czf "$KIT/out.tgz" --exclude='*.rrd' --exclude='out/rec_*/chase_view.mp4' -C "$KIT" out
    # the size beside the sha256 (F7): the session reads a host reached through IAP as ranges of this file and bounds
    # the whole fetch by its size
    printf '%s %s\n' "$(sha256sum "$KIT/out.tgz" | cut -d' ' -f1)" "$(stat -c %s "$KIT/out.tgz")"
    ;;
  *) echo "usage: host_step.sh run|start|status|tail|signal|pack ..." >&2; exit 2 ;;
esac
