#!/usr/bin/env bash
# The public recording harness of the full-chain AEBS event (owner approved a
# real recording on 2026-10-28; posting needs a separate approval). It records
# real terminals and the real IVI HMI display. It never renders or styles
# anything. An edited cut is labeled publication_cut; the raw files stay with
# the evidence. Nothing here posts anywhere.
#
#   record_full_chain.sh start <out-dir>   start the operator-terminal and pane recordings
#   record_full_chain.sh hmi <out-dir>     start the IVI HMI screen recording (only after MONITORING shows)
#   record_full_chain.sh stop <out-dir>    stop every recording and write the manifest
#
# Panes recorded (each a real terminal under script --log-timing, or asciinema
# on the operator's terminal):
#   - the host stack and gatewayd/someipd logs;
#   - the SDV Core broker logcat;
#   - the IVI frame relay log.
# The HMI is captured with adb screenrecord on the IVI VM during the event
# (MONITORING, WARNING, INTERVENTION, RELEASED), started only after MONITORING
# shows, so the take is the real display.
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
OUT="${2:?usage: $0 {start|hmi|stop} <out-dir>}"; mkdir -p "$OUT"
RELAY_TAG="${RELAY_LOGCAT_TAG:-frame_relay}"

_rec_pane() {
  local name="$1"; shift
  # script --log-timing keeps the real terminal stream and its timing.
  script --log-timing "$OUT/$name.timing" --command "$*" "$OUT/$name.typescript" >/dev/null 2>&1 &
  echo $! > "$OUT/.pane.$name.pid"
  log "recording pane $name"
}

start() {
  require_cmd script "$ADB" || true
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  _rec_pane host-stack "journalctl -f -u 'de4sdv-*' --no-hostname"
  _rec_pane core-broker "$ADB -s $CORE_ADB logcat -v epoch sdv_someip_broker_agent_comms:* sdv_someip_stack_agent:* '*:S'"
  _rec_pane relay "$ADB -s $IVI_ADB logcat -v epoch '$RELAY_TAG':* '*:S'"
  log "operator panes recording; verify MONITORING on the HMI, then: $0 hmi $OUT"
}

hmi() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  local state; state="$("$ADB" -s "$IVI_ADB" logcat -d -t 400 | grep -o 'disposition=[A-Z]*' | tail -1)"
  log "latest HMI disposition line: ${state:-none}"
  case "$state" in
    *MONITORING*) : ;;
    *) log "REFUSING: MONITORING is not showing yet; start the HMI capture only after it does"; return 1 ;;
  esac
  # Real display capture on the guest; pull after stop.
  "$ADB" -s "$IVI_ADB" shell "screenrecord --bit-rate 8000000 --time-limit 180 /data/local/tmp/hmi.mp4" &
  echo $! > "$OUT/.hmi.pid"
  log "recording the IVI HMI display (adb screenrecord); run the event now, then: $0 stop $OUT"
}

stop() {
  for pid in "$OUT"/.pane.*.pid "$OUT/.hmi.pid"; do [ -f "$pid" ] && kill "$(cat "$pid")" 2>/dev/null || true; done
  sleep 2
  "$ADB" -s "$IVI_ADB" pull /data/local/tmp/hmi.mp4 "$OUT/hmi-raw.mp4" 2>&1 | tail -1 || true
  {
    echo "schema: de4sdv.recording-harness.v1"
    echo "captured_at: $(date -u +%FT%T.%NZ)"
    echo "disposition: observed_bounded"
    echo "note: real terminal recordings and a real adb screenrecord of the IVI HMI; no rendered or stylized footage"
    echo "posting: needs Orkun's approval; an edited cut is labeled publication_cut"
    echo "files:"
    ( cd "$OUT" && for f in *.typescript *.timing hmi-raw.mp4; do [ -f "$f" ] && echo "  - path: $f"; done )
    echo "sha256:"
    ( cd "$OUT" && sha256sum *.typescript hmi-raw.mp4 2>/dev/null | sed 's/^/  /' )
  } > "$OUT/recording-manifest.yaml"
  log "wrote $OUT/recording-manifest.yaml; raw files stay with the evidence, posting needs approval"
}

case "${1:-}" in
  start) start ;;
  hmi) hmi ;;
  stop) stop ;;
  *) echo "usage: $0 {start|hmi|stop} <out-dir>" >&2; exit 2 ;;
esac
