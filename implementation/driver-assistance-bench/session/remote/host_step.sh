#!/bin/bash
# One step of a bench session on one host, with uniform markers for the orchestrator (da_session.sh).
#
#   host_step.sh run    <step> -- <command...>   run in the foreground; exits with the command's status
#   host_step.sh start  <step> -- <command...>   run detached (setsid nohup); returns at once
#   host_step.sh status <step>                   prints "rc <N>", "running" or "absent"
#   host_step.sh signal <step> [INT|TERM]        signals the detached step's process group
#   host_step.sh pack                            tars the host's output folder to <kit>/out.tgz, prints its sha256
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

ACTION=${1:?run|start|status|signal|pack}; shift
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
    elif [ -s "$DA_OUT/$STEP.pid" ] && kill -0 "$(cat "$DA_OUT/$STEP.pid")" 2>/dev/null; then echo running
    elif [ -s "$DA_OUT/$STEP.pid" ]; then echo "rc 255"   # ended without writing its status (killed)
    else echo absent; fi
    ;;
  signal)
    STEP=${1:?step name}; SIG=${2:-INT}
    PID=$(cat "$DA_OUT/$STEP.pid" 2>/dev/null) || { echo "no pid for $STEP"; exit 1; }
    kill "-$SIG" -- "-$PID" 2>/dev/null || kill "-$SIG" "$PID" 2>/dev/null
    echo "signalled $STEP ($SIG)"
    ;;
  pack)
    cp "$KIT/session_id" "$DA_OUT/session_id"
    tar -czf "$KIT/out.tgz" -C "$KIT" out
    sha256sum "$KIT/out.tgz" | cut -d' ' -f1
    ;;
  *) echo "usage: host_step.sh run|start|status|signal|pack ..." >&2; exit 2 ;;
esac
