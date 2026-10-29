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
# gatewayd/someipd, the SDV Core broker logcat, the IVI frame relay log. The
# relay's logcat tag is a required input (the relay lane owns it).
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
[ -n "${2:-}" ] || { echo "usage: $0 {start|hmi|stop} <out-dir>" >&2; exit 2; }
OUT="$2"; mkdir -p "$OUT"
: "${HOST_STACK_UNITS:=de4sdv-*}"          # the host-half units the run uses (set to the Launch Manager's units)
: "${APP_TAG:=MainActivity}"               # the HMI app's logcat tag (INC-AEBS-010)
: "${MONITORING_MAX_AGE_S:=2}"             # the latest frame line must be at most this old on the guest clock
SCAN=(python3 -m de4sdv_broker_path_bench.hostscan)
export PYTHONPATH="$HERE/../src${PYTHONPATH:+:$PYTHONPATH}"

_rec_pane() {
  local name="$1"; shift
  script --log-timing "$OUT/$name.timing" --command "$*" "$OUT/$name.typescript" < /dev/null >/dev/null 2>&1 &
  echo $! > "$OUT/.pane.$name.pid"
  log "recording pane $name"
}

start() {
  require_relay_inputs || return 2
  require_cmd script "$ADB" || true
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" logcat -G 16M >/dev/null 2>&1 || true
  _rec_pane host-stack "journalctl -f -u '$HOST_STACK_UNITS' --no-hostname"
  _rec_pane core-broker "$ADB -s $CORE_ADB logcat -v epoch -v usec sdv_someip_broker_agent_comms:* sdv_someip_stack_agent:* *:S"
  _rec_pane relay "$ADB -s $IVI_ADB logcat -v epoch -v usec $RELAY_LOGCAT_TAG:* *:S"
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
  "$ADB" -s "$IVI_ADB" shell "screenrecord --bit-rate 8000000 --time-limit 180 /data/local/tmp/hmi.mp4" &
  echo $! > "$OUT/.hmi.pid"
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
    echo "files:"
    ( cd "$OUT" && for f in *.typescript *.timing hmi-raw.mp4; do [ -f "$f" ] && echo "  - path: $f"; done )
    echo "sha256:"
    ( cd "$OUT" && sha256sum *.typescript *.timing hmi-raw.mp4 2>/dev/null | sed 's/^/  /' )
  } > "$OUT/recording-manifest.yaml"
  log "wrote $OUT/recording-manifest.yaml; raw files stay with the evidence, posting needs approval"
}

case "${1:-}" in
  start) start ;;
  hmi) hmi ;;
  stop) stop ;;
  *) echo "usage: $0 {start|hmi|stop} <out-dir>" >&2; exit 2 ;;
esac
