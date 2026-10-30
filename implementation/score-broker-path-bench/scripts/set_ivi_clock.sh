#!/usr/bin/env bash
# Hold ASM-MW-030 on the IVI VM: let the host chrony serve the IVI, turn off
# automatic time, set the clock once against the host with the image SNTP
# client, then slew it, and capture the NTP exchange so the evaluator can
# measure the offset from the raw packets. No DE4SDV code sets or crafts time;
# this calls the image's toybox sntp and captures with tcpdump.
#
#   set_ivi_clock.sh allow            add a host chrony allow for the IVI (idempotent)
#   set_ivi_clock.sh deny             remove the host chrony allow (the undo)
#   set_ivi_clock.sh setup            auto_time off, prove reachability, set once, start a slew, restart the ingress
#   set_ivi_clock.sh measure <out>    capture one NTP query (no setting) for the evaluator
#   set_ivi_clock.sh drift            two measures a session apart; print the drift and the session length
#   set_ivi_clock.sh host-steps <out> record the host clock steps over the session (ASM-MW-030)
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
S=("$ADB" -s "$IVI_ADB")
: "${RUN_DIR:=$HERE/../run}"; mkdir -p "$RUN_DIR"

_guest() { "${S[@]}" shell "$@"; }

allow() {
  require_cmd chronyc || { log "chrony not installed on the host"; return 1; }
  sudo chronyc allow "${IVI_ADDR}/32" && log "host chrony now serves ${IVI_ADDR}" || { log "chronyc allow failed"; return 1; }
  : "${RUN_DIR:=$HERE/../run}"; mkdir -p "$RUN_DIR"
  cat >> "$RUN_DIR/vm-change-log.session.txt" <<EOF
chrony allow $(date -u +%FT%T.%NZ): host 'chronyc allow ${IVI_ADDR}/32' (IVI queries host chrony for ASM-MW-030); undo 'scripts/set_ivi_clock.sh deny'
EOF
}

deny() { sudo chronyc deny "${IVI_ADDR}/32" && log "host chrony no longer serves ${IVI_ADDR}" || true; }

setup() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true
  _guest "settings put global auto_time 0; settings put global auto_time_zone 0" 2>/dev/null || true
  # Prove the IVI reaches the server from its default network before relying on it
  # (spike T8 saw TCP to .1 fail via buried_eth0). The reachability gate uses the
  # image's ping; check it exists first, since not every Android image ships it.
  if [ -z "$(_guest 'command -v toybox ping ping 2>/dev/null' | tr -d '\r')" ]; then
    log "ERROR: no ping on the IVI image; use another reachability check (an SNTP query to $SNTP_SERVER)"; return 1
  fi
  if ! _guest "toybox ping -c1 -W2 $SNTP_SERVER >/dev/null 2>&1"; then
    log "ERROR: the IVI VM cannot reach $SNTP_SERVER; add a guest route or fix buried_eth0 routing first"; return 1
  fi
  # One-shot set, then an adjust-mode slew as a daemon re-querying every 64 s
  # (-r 6). A slew moves CLOCK_REALTIME and CLOCK_MONOTONIC together, so it is
  # no step. Check the exit codes (no '| tail', which would hide them).
  if ! _guest "toybox sntp -s $SNTP_SERVER"; then log "ERROR: toybox sntp -s failed"; return 1; fi
  log "IVI clock set once against $SNTP_SERVER"
  _guest "stop de4sdv_ivi_sntp_slew 2>/dev/null; nohup toybox sntp -a -d -r 6 $SNTP_SERVER >/dev/null 2>&1 &" || true
  log "started an SNTP slew (adjust mode, re-query every 64 s); if the image sntp has no slew, size each session from the drift"
  # Restart the ingress so its subscription phase starts after the setting
  # (VC-MW-020 condition 2). init ignores `start` for a service that is already
  # running, so the oneshot ingress must be stopped first; the relay's
  # ingress-start property then starts a fresh ingress, which the relay accepts
  # as a new client and logs as a new phase_start (review R37). The relay's
  # logcat tag comes from bench_env.sh, so the new phase can be asserted.
  [ -n "${RELAY_LOGCAT_TAG:-}" ] || { log "ERROR: RELAY_LOGCAT_TAG is set empty; it is needed to assert the new phase_start"; return 2; }
  local before="$RUN_DIR/relay-before-ingress-restart.txt" after="$RUN_DIR/relay-after-ingress-restart.txt"
  _guest "logcat -d -v epoch -v usec ${RELAY_LOGCAT_TAG}:* '*:S'" 2>/dev/null | tr -d '\r' > "$before"
  _guest "stop de4sdv_aebs_ingress" || true
  local i
  for i in $(seq 1 15); do
    [ "$(_guest 'getprop init.svc.de4sdv_aebs_ingress' | tr -d '\r')" = stopped ] && break; sleep 0.5
  done
  _guest "setprop de4sdv.aebs.ingress.start 0; setprop de4sdv.aebs.ingress.start 1" || true
  log "stopped and restarted the ingress after the clock setting; waiting for a new relay phase_start"
  # A phase_start whose (pid, phase) the log did not hold before the restart.
  for i in $(seq 1 30); do
    _guest "logcat -d -v epoch -v usec ${RELAY_LOGCAT_TAG}:* '*:S'" 2>/dev/null | tr -d '\r' > "$after"
    # pipefail (set at the top) makes the pipeline fail when no new phase is found.
    if PYTHONPATH="$HERE/../src" python3 -m de4sdv_broker_path_bench.relay_log new-phase-start \
         --tag "$RELAY_LOGCAT_TAG" --before "$before" --after "$after" | sed 's/^/new phase: /'; then
      log "a new phase started after the clock setting"; return 0
    fi
    sleep 1
  done
  log "ERROR: no new relay phase_start after the clock setting (the ingress did not reconnect); see $after"
  return 1
}

measure() {
  local out="${1:?usage: $0 measure <out.pcap>}"
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true
  # Capture on the guest, on the guest clock; record tcpdump's own pid and stop
  # it by that pid (not pkill -f, which also matches this shell).
  _guest "rm -f /data/local/tmp/clock.pcap; tcpdump -i any -w /data/local/tmp/clock.pcap 'udp port 123 and host $SNTP_SERVER' >/dev/null 2>&1 & echo \$! > /data/local/tmp/clock.pid; sleep 1; (toybox sntp -q $SNTP_SERVER || true) >/dev/null 2>&1; sleep 1; kill -INT \$(cat /data/local/tmp/clock.pid); for i in \$(seq 1 20); do kill -0 \$(cat /data/local/tmp/clock.pid) 2>/dev/null || break; sleep 0.2; done; sync"
  "${S[@]}" pull /data/local/tmp/clock.pcap "$out" 2>&1 | tail -1
  log "captured one NTP exchange into $out"
}

host_steps() {
  local out="${1:?usage: $0 host-steps <out.txt>}"
  { echo "# host clock steps (ASM-MW-030) $(date -u +%FT%T.%NZ)"
    journalctl -u chrony -u chronyd --no-hostname 2>/dev/null | grep -i "System clock was stepped" | tail -50
    python3 -c 'import time;print("realtime_minus_monotonic_ns",int(time.time()*1e9)-time.monotonic_ns())'
  } >> "$out"
  log "recorded host clock steps into $out"
}

drift() {
  measure "$RUN_DIR/clock-start.pcap"
  log "waiting ${DRIFT_WAIT_S:=840} s to measure the drift (the spike saw about 60 ppm)"
  sleep "${DRIFT_WAIT_S}"
  measure "$RUN_DIR/clock-end.pcap"
  PYTHONPATH="$HERE/../src" python3 - "$RUN_DIR/clock-start.pcap" "$RUN_DIR/clock-end.pcap" <<'PY'
import sys
from de4sdv_broker_path_bench import clock
from de4sdv_broker_path_bench.pcap import read_pcap
start = clock.best(clock.exchanges(read_pcap(sys.argv[1]))[0])
end = clock.best(clock.exchanges(read_pcap(sys.argv[2]))[0])
if not start or not end:
    print("no complete exchange captured"); sys.exit(1)
rate = clock.drift_ppm(start, end)
print(f"offset start {start.offset_ns:.0f} ns (+-{start.uncertainty_ns:.0f}), end {end.offset_ns:.0f} ns")
print(f"drift {rate:.1f} ppm; session length after a setting ~= {clock.session_seconds(start, rate):.0f} s")
PY
}

case "${1:-}" in
  allow) allow ;;
  deny) deny ;;
  setup) setup ;;
  measure) shift; measure "$@" ;;
  host-steps) shift; host_steps "$@" ;;
  drift) drift ;;
  *) echo "usage: $0 {allow|deny|setup|measure <out.pcap>|host-steps <out.txt>|drift}" >&2; exit 2 ;;
esac
