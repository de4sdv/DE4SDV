#!/usr/bin/env bash
# The public recording harness of the full-chain AEBS event (owner decision of
# 2026-10-28: a recording for public use; posting needs approval). It records
# real terminals and the real IVI HMI display. It never renders or styles
# anything. An edited cut is labeled publication_cut; the raw files stay with
# the evidence. Nothing here posts anywhere.
#
#   record_full_chain.sh start <out-dir>   start the operator-terminal and pane recordings
#   record_full_chain.sh hmi <out-dir>     start the IVI HMI screen recording (only after MONITORING shows)
#   record_full_chain.sh stop <out-dir>    stop every recording and write the manifest
#
# Panes (each a real terminal under script --log-timing): the host stack and
# gatewayd/someipd, the SDV Core broker logcat, the IVI frame relay log, and the
# IVI frame path (the HMI app's per-frame line next to the ingress's per-frame
# line, both with epoch timestamps). The relay's logcat tag comes from
# bench_env.sh (the IVI frame relay's service name).
#
# hmi records the anchors too (hmi-anchor.yaml): the IVI clock read immediately
# before and after the screenrecord launch, and the host time around it. The
# video's t=0 lies inside that interval, so a log line can be placed on the
# video from the anchors instead of being inferred from the pixels.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
[ -n "${2:-}" ] || { echo "usage: $0 {start|hmi|stop} <out-dir>" >&2; exit 2; }
OUT="$2"; mkdir -p "$OUT"
: "${HOST_STACK_UNITS:=de4sdv-*}"          # the host-half units the run uses (set to the Launch Manager's units)
: "${HOST_STACK_LOGS:=}"                   # space-separated host-half log files; preferred over the journal when set
: "${AEB_PANE_CMD:=}"                      # optional Autoware-side pane; needs the bench ROS environment
: "${APP_TAG:=MainActivity}"               # the HMI app's logcat tag (INC-AEBS-010)
: "${INGRESS_TAG:=de4sdv_aebs_ingress}"    # the INC-AEBS-010 ingress's logcat tag (its per-frame line)
: "${MONITORING_MAX_AGE_S:=2}"             # the latest frame line must be at most this old on the guest clock
SCAN=(python3 -m de4sdv_broker_path_bench.hostscan)
export PYTHONPATH="$HERE/../src${PYTHONPATH:+:$PYTHONPATH}"

# The host half does not live in one journal: on the bench the frame assembler is
# a system unit while the S-CORE daemons are the operator's --user units. A single
# `journalctl -u` therefore watches one scope, and without -n 0 it replays the
# other scope's tail instead of following it: the S3 window recorded 13 lines from
# three hours before the run and nothing during it, which reads as evidence and
# isn't. Probe every unit, follow both journals from now on, and say plainly when
# a unit resolves nowhere.
#
# `systemctl cat` is not a probe: it exits 0 for a unit that does not exist (and
# for a glob that matches nothing), so the pane ends up following a unit name no
# journal holds. LoadState is the question being asked.
_unit_scope() {
  local u="$1" state
  state="$(systemctl --user show -p LoadState --value "$u" 2>/dev/null)"
  [ "$state" = loaded ] && { printf 'user'; return 0; }
  state="$(systemctl show -p LoadState --value "$u" 2>/dev/null)"
  [ "$state" = loaded ] && printf 'system'
}

# The bench names its units by pattern (`s2-*`), and a pattern is not a unit: it
# has to be expanded in each scope first, or every unit behind it is invisible.
# --all so a unit that failed before the window (and may be restarted into it) is
# still watched.
_expand_units() {
  local u
  for u in $HOST_STACK_UNITS; do
    case "$u" in
      *'*'*|*'?'*|*'['*)
        systemctl --user list-units --all --plain --no-legend "$u" 2>/dev/null | awk '{print $1}'
        systemctl list-units --all --plain --no-legend "$u" 2>/dev/null | awk '{print $1}'
        ;;
      *) printf '%s\n' "$u" ;;
    esac
  done | sed '/^$/d' | sort -u
}

_host_stack_journal() {
  local u scope has_sys=0 has_user=0 sys_cmd="" user_cmd=""
  local -a sys_args=() user_args=()
  for u in $(_expand_units); do
    scope="$(_unit_scope "$u")"
    case "$scope" in
      user)   user_args+=(-u "$u"); has_user=1 ;;
      system) sys_args+=(-u "$u"); has_sys=1 ;;
      *)      log "WARNING: host-half unit '$u' is in neither the system nor the user scope" >&2 ;;
    esac
  done
  [ "$has_sys" = 1 ] && sys_cmd="journalctl -f -n 0 -o short-iso-precise --no-hostname ${sys_args[*]}"
  [ "$has_user" = 1 ] && user_cmd="journalctl --user -f -n 0 -o short-iso-precise --no-hostname ${user_args[*]}"
  if [ -n "$sys_cmd" ] && [ -n "$user_cmd" ]; then
    printf '%s & %s & wait' "$sys_cmd" "$user_cmd"
  elif [ -n "$sys_cmd" ]; then
    printf '%s' "$sys_cmd"
  elif [ -n "$user_cmd" ]; then
    printf '%s' "$user_cmd"
  else
    # No unit resolves (a CI runner has no user session and no bench units). Follow
    # the whole journal rather than fail the recording, but make the gap explicit:
    # an unfiltered pane is still honest, a silently empty one is not.
    log "WARNING: none of HOST_STACK_UNITS='$HOST_STACK_UNITS' resolves; the host-stack pane follows the unfiltered journal" >&2
    printf '%s' "journalctl -f -n 0 -o short-iso-precise --no-hostname"
  fi
}

_rec_pane() {
  local name="$1"; shift
  script --log-timing "$OUT/$name.timing" --command "$*" "$OUT/$name.typescript" < /dev/null >/dev/null 2>&1 &
  local pid=$!; echo "$pid" > "$OUT/.pane.$name.pid"
  # A pane is only recording once its process is up AND its typescript exists;
  # a pane that died at once (no pty, a command that cannot run) leaves a silent
  # gap in the evidence, so the start fails instead of recording three panes and
  # saying it recorded four.
  local i
  for i in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    [ -e "$OUT/$name.typescript" ] && break
    sleep 0.1
  done
  if ! kill -0 "$pid" 2>/dev/null; then
    log "ERROR: pane $name did not start; nothing was recorded for it (see $OUT/$name.typescript)"
    return 1
  fi
  if [ ! -e "$OUT/$name.typescript" ]; then
    log "ERROR: pane $name is running but wrote no typescript at $OUT/$name.typescript"
    return 1
  fi
  log "recording pane $name"
}

start() {
  require_relay_inputs || return 2
  require_cmd script "$ADB" || true
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" logcat -G 16M >/dev/null 2>&1 || true
  local host_cmd
  if [ -n "$HOST_STACK_LOGS" ]; then
    # The host-half units run with their output redirected to files
    # (`exec … >> logs/bridge.log 2>&1`), so the journal holds only their
    # start/stop lines: a pane that follows the journal next to a live chain
    # records a lifecycle diary and nothing else. Follow the files they write,
    # from now on, or the S-CORE hop is missing from the evidence exactly where
    # the increment is about it.
    local missing=0 f
    for f in $HOST_STACK_LOGS; do
      [ -e "$f" ] || { log "ERROR: host-half log $f does not exist; the pane would record nothing"; missing=1; }
    done
    [ "$missing" = 0 ] || return 1
    host_cmd="tail -F -n 0 $HOST_STACK_LOGS"
  else
    host_cmd="$(_host_stack_journal)"
  fi
  [ -n "$host_cmd" ] || return 1
  if [ -n "$AEB_PANE_CMD" ]; then
    # The Autoware side of the chain, in its own terminal, before the assembler:
    # without it the earliest hop has a pcap and nothing a viewer can read.
    _rec_pane aeb-decision "$AEB_PANE_CMD" || return 1
  else
    log "NOTE: AEB_PANE_CMD unset; the Autoware-side decision pane is not recorded"
  fi
  _rec_pane host-stack "$host_cmd" || return 1
  _rec_pane core-broker "$ADB -s $CORE_ADB logcat -v epoch -v usec sdv_someip_broker_agent_comms:* sdv_someip_stack_agent:* *:S" || return 1
  _rec_pane relay "$ADB -s $IVI_ADB logcat -v epoch -v usec $RELAY_LOGCAT_TAG:* *:S" || return 1
  # The IVI frame path in one terminal: the ingress publishes each frame and the
  # app renders it, both with epoch stamps, so the two lines of one frame sit
  # side by side while the event runs.
  _rec_pane ivi-frames "$ADB -s $IVI_ADB logcat -v epoch -v usec ${INGRESS_TAG}:* ${APP_TAG}:I *:S" || return 1
  log "operator panes recording; verify MONITORING on the HMI, then: $0 hmi $OUT"
}

hmi() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  # The app logs one line per frame (INC-AEBS-010 MainActivity.java): MONITORING
  # is not intervention, not warning, not braking, and lifecycle not released.
  # The latest line decides, and only if it is at most MONITORING_MAX_AGE_S old
  # on the guest clock (review R26): an old MONITORING line in the buffer does
  # not open the gate. hostscan monitoring judges it and keeps the record.
  local now
  now="$("$ADB" -s "$IVI_ADB" shell "date +%s" 2>/dev/null | tr -d '\r' | head -1)"
  "$ADB" -s "$IVI_ADB" logcat -d -v epoch -t 400 "${APP_TAG}:I" '*:S' 2>/dev/null | tr -d '\r' > "$OUT/monitoring-gate-logcat.txt"
  case "$now" in ''|*[!0-9]*) log "REFUSING: could not read the IVI VM clock for the MONITORING gate"; return 1 ;; esac
  if ! "${SCAN[@]}" monitoring --logcat "$OUT/monitoring-gate-logcat.txt" --now "$now" \
        --max-age "$MONITORING_MAX_AGE_S" > "$OUT/monitoring-gate.json"; then
    log "REFUSING: MONITORING is not showing on the HMI now ($(cat "$OUT/monitoring-gate.json")); start the capture only after it does"
    return 1
  fi
  log "MONITORING gate: $(cat "$OUT/monitoring-gate.json")"
  # The anchors: the IVI clock immediately before and after the launch, and the
  # host time around it. screenrecord sets up its encoder between the two reads,
  # so the video's t=0 lies inside that interval; the pair is written down so
  # the alignment is read from the run, not guessed from the frames later.
  local ivi_before ivi_after host_before host_after
  ivi_before="$("$ADB" -s "$IVI_ADB" shell "date +%s.%N" 2>/dev/null | tr -d '\r' | head -1)"
  host_before="$(date -u +%FT%T.%NZ)"
  "$ADB" -s "$IVI_ADB" shell "screenrecord --bit-rate 8000000 --time-limit 180 /data/local/tmp/hmi.mp4" &
  echo $! > "$OUT/.hmi.pid"
  ivi_after="$("$ADB" -s "$IVI_ADB" shell "date +%s.%N" 2>/dev/null | tr -d '\r' | head -1)"
  host_after="$(date -u +%FT%T.%NZ)"
  {
    echo "schema: de4sdv.recording-anchor.v1"
    echo "gate_json: monitoring-gate.json"
    echo "screenrecord_command: $ADB -s $IVI_ADB shell screenrecord --bit-rate 8000000 --time-limit 180 /data/local/tmp/hmi.mp4"
    echo "host_before: $host_before"
    echo "ivi_before_epoch_s: ${ivi_before:-unreadable}"
    echo "ivi_after_epoch_s: ${ivi_after:-unreadable}"
    echo "host_after: $host_after"
    echo "note: the encoder starts between ivi_before_epoch_s and ivi_after_epoch_s, so the video's t=0 lies in that interval; read the alignment from here, do not infer it"
  } > "$OUT/hmi-anchor.yaml"
  log "recording the IVI HMI display; run the event now, then: $0 stop $OUT"
}

stop() {
  # Stop screenrecord gently on the guest and wait for the file to finalize.
  "$ADB" -s "$IVI_ADB" shell "pkill -INT screenrecord" 2>/dev/null || true
  local i; for i in $(seq 1 30); do
    [ -z "$("$ADB" -s "$IVI_ADB" shell pidof screenrecord 2>/dev/null | tr -d '\r')" ] && break; sleep 0.5
  done
  for pid in "$OUT"/.pane.*.pid "$OUT/.hmi.pid"; do [ -f "$pid" ] && kill "$(cat "$pid")" 2>/dev/null || true; done
  "$ADB" -s "$IVI_ADB" pull /data/local/tmp/hmi.mp4 "$OUT/hmi-raw.mp4" 2>&1 | tail -1 || true
  if [ ! -s "$OUT/hmi-raw.mp4" ]; then log "WARNING: hmi-raw.mp4 is empty or missing"; fi
  {
    echo "schema: de4sdv.recording-harness.v1"
    echo "captured_at: $(date -u +%FT%T.%NZ)"
    echo "disposition: deferred_not_proven   # until a review promotes it"
    echo "owner_decision: owner decision of 2026-10-28 (recording for public use; posting needs approval)"
    echo "note: real terminal recordings (script --log-timing) and a real adb screenrecord of the IVI HMI; no rendered or stylized footage; an edited cut is labeled publication_cut"
    echo "host_stack_units: $HOST_STACK_UNITS"
    if [ -n "$HOST_STACK_LOGS" ]; then echo "host_stack_source: logs  # $HOST_STACK_LOGS"; else echo "host_stack_source: journal"; fi
    if [ -n "$AEB_PANE_CMD" ]; then echo "aeb_pane: recorded"; else echo "aeb_pane: not_recorded  # AEB_PANE_CMD was unset"; fi
    echo "files:"
    ( cd "$OUT" && for f in *.typescript *.timing hmi-raw.mp4 hmi-anchor.yaml; do [ -f "$f" ] && echo "  - path: $f"; done )
    echo "sha256:"
    ( cd "$OUT" && sha256sum *.typescript *.timing hmi-raw.mp4 hmi-anchor.yaml 2>/dev/null | sed 's/^/  /' )
  } > "$OUT/recording-manifest.yaml"
  log "wrote $OUT/recording-manifest.yaml; raw files stay with the evidence, posting needs approval"
}

case "${1:-}" in
  start) start ;;
  hmi) hmi ;;
  stop) stop ;;
  *) echo "usage: $0 {start|hmi|stop} <out-dir>" >&2; exit 2 ;;
esac
