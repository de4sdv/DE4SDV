#!/usr/bin/env bash
# Hold ASM-MW-030 on the IVI VM: let the host chrony serve the IVI, turn off
# automatic time, step the clock against the host and prove the step landed,
# then slew it, and capture the NTP exchange so the evaluator can measure the
# offset from the raw packets. No DE4SDV code sets or crafts time; this calls
# the image's toybox sntp and date and captures with tcpdump.
#
#   set_ivi_clock.sh allow            add a host chrony allow for the IVI (idempotent)
#   set_ivi_clock.sh deny             remove the host chrony allow (the undo)
#   set_ivi_clock.sh set              measure against the host, step, re-measure (no restart)
#   set_ivi_clock.sh setup            auto_time off, prove reachability, set once, start a slew, clear the IVI
#                                     log buffer, restart the ingress (so the capture's relay log opens on a phase_start)
#   set_ivi_clock.sh measure <out>    capture one NTP query (no setting) for the evaluator
#   set_ivi_clock.sh drift            two measures a session apart; print the drift and the session length
#   set_ivi_clock.sh host-steps <out> record the host clock steps over the session (ASM-MW-030)
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
# The step computes an epoch with awk's printf, and a host locale with a decimal
# comma (de_DE and friends) makes that epoch unparseable for the guest's date.
export LC_ALL=C
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

# The guest's default network is buried_eth0, and each network carries its own routing table, so
# HOST_ADDR resolves through the buried_eth0 default route and is unreachable even though eth1
# carries the bench /24 (spike T8 saw exactly this). Add one rule that sends the bench subnet to the
# main table first. It is idempotent, and it does not survive a reboot, which is why setup re-applies
# it instead of asking the operator to fix routing by hand.
_ensure_route_to_host() {
  local net="${HOST_ADDR%.*}.0/24"
  "${S[@]}" shell "ip rule show | grep -q 'to $net lookup main' || ip rule add to $net lookup main priority 15000" >/dev/null 2>&1
  "${S[@]}" shell "ip route get $HOST_ADDR 2>/dev/null | grep -q 'dev eth1'" || {
    log "ERROR: the IVI still routes $HOST_ADDR away from eth1; the guest rule did not take effect"; return 1; }
  log "guest route: $net resolves through the main table, so $HOST_ADDR is on eth1"
}

# `toybox sntp -s` is not a step on this image: it prints the offset, exits 0 and
# leaves the clock where it was (S3 probe, fresh sdv_ivi_cf guest: -183.641 ms
# before, -183.487 ms after; `toybox date -s @<epoch>` on the same guest moves the
# clock at once, and a host-NTP pcap exchange agrees with toybox to under a
# millisecond). An SNTP client's only job here is to make the guest agree with
# the host, so the set is two image-owned steps — measure with `toybox sntp -q`,
# apply with `toybox date -s` — and then a fresh exchange that has to show the
# residual inside the bound. The verification never restates the first reading.
CLOCK_SET_BOUND_MS=${CLOCK_SET_BOUND_MS:-5}
_sntp_offset() {
  _guest "toybox sntp -q $SNTP_SERVER" 2>/dev/null | tr -d '\r' |
    awk '/offset/ { for (i = 1; i < NF; i++) if ($i == "offset") { print $(i + 1); exit } }'
}
_step_by() { # <offset-seconds>: read, add and set inside one guest shell
  # The read, the arithmetic and the set are one guest shell command on purpose:
  # across two adb round trips the set lands 50-150 ms after the read and never
  # converges. One shell is not enough on its own either — the guest still needs
  # ~16 ms to start awk and date between its read and its set (measured on the
  # bench guest: 15.4-18.0 ms over five runs), so a step that ignores that lands
  # 16 ms behind every time and three retries settle at +15.3/+21.7/+18.9 ms.
  # Measure the same chain and carry its duration into the target.
  local latency target_offset guest_cmd
  latency=$(_chain_latency)
  [ -n "$latency" ] || latency=0
  target_offset=$(awk -v o="$1" -v l="$latency" 'BEGIN { printf "%.9f", o + l }')
  guest_cmd="toybox date -s @\$(awk -v n=\$(date +%s.%N) -v o=$target_offset 'BEGIN { printf \"%.9f\", n + o }')"
  if ! _guest "$guest_cmd" >/dev/null; then
    log "ERROR: the guest could not step the clock by $1 s"; return 1
  fi
}
_chain_latency() { # the guest's own read-to-set cost, same command shape
  _guest 't0=$(date +%s.%N); awk -v n=$t0 -v o=1 "BEGIN{printf \"%.9f\", n+o}" >/dev/null; t1=$(date +%s.%N); awk -v a=$t0 -v b=$t1 "BEGIN{printf \"%.6f\", b-a}"' 2>/dev/null | tr -d '\r'
}
set_clock() {
  local attempt offset residual
  # The step needs arithmetic inside the guest shell; say so instead of failing
  # with an unparseable date later.
  if [ -z "$(_guest 'command -v awk' 2>/dev/null | tr -d '\r')" ]; then
    log "ERROR: the IVI image has no awk; the clock step computes its target in the guest shell"; return 1
  fi
  offset=$(_sntp_offset)
  [ -n "$offset" ] || { log "ERROR: toybox sntp -q printed no offset for $SNTP_SERVER"; return 1; }
  _step_by "$offset" || return 1
  log "IVI clock stepped by $offset s against $SNTP_SERVER (toybox date -s)"
  for attempt in 1 2 3; do
    residual=$(_sntp_offset)
    [ -n "$residual" ] || { log "ERROR: toybox sntp -q printed no offset for $SNTP_SERVER"; return 1; }
    if awk -v r="$residual" -v b="$CLOCK_SET_BOUND_MS" \
         'BEGIN { exit ((r < 0 ? -r : r) <= b / 1000) ? 0 : 1 }'; then
      log "IVI clock holds $residual s from $SNTP_SERVER after the step (bound ${CLOCK_SET_BOUND_MS} ms)"
      return 0
    fi
    log "IVI clock still $residual s out; stepping again (attempt $attempt)"
    _step_by "$residual" || return 1
  done
  log "ERROR: the IVI clock is still $residual s from $SNTP_SERVER after 3 steps"
  return 1
}

setup() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true
  _guest "settings put global auto_time 0; settings put global auto_time_zone 0" 2>/dev/null || true
  _ensure_route_to_host || return 1
  # Prove the IVI reaches the server from its default network before relying on it
  # (spike T8 saw TCP to .1 fail via buried_eth0). The reachability gate uses the
  # image's ping; check it exists first, since not every Android image ships it.
  if [ -z "$(_guest 'command -v toybox ping ping 2>/dev/null' | tr -d '\r')" ]; then
    log "ERROR: no ping on the IVI image; use another reachability check (an SNTP query to $SNTP_SERVER)"; return 1
  fi
  if ! _guest "toybox ping -c1 -W2 $SNTP_SERVER >/dev/null 2>&1"; then
    log "ERROR: the IVI VM cannot reach $SNTP_SERVER; add a guest route or fix buried_eth0 routing first"; return 1
  fi
  # Step the clock and prove the step landed before anything else runs: a set
  # that silently does nothing would leave the window measuring the guest's
  # free-running drift (S2 ran +44.5 ms against a 20 ms bound this way).
  set_clock || return 1
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
  # The pre-restart buffer is kept in $before above. Clear the buffer *after* the
  # ingress is stopped and *before* it is started, so the log a capture pulls next
  # opens on this restart's phase_start. Clearing before the stop leaves the
  # stop's own phase_end as the first line, and the evaluator reads a phase_end
  # whose start predates the buffer as an inconclusive relay record (S3 window).
  _guest "stop de4sdv_aebs_ingress" || true
  local i
  for i in $(seq 1 15); do
    [ "$(_guest 'getprop init.svc.de4sdv_aebs_ingress' | tr -d '\r')" = stopped ] && break; sleep 0.5
  done
  # Let the relay notice the disconnect and log its phase_end, then clear: the
  # clear has to come after that line and before the start, or the buffer opens
  # on a phase_end whose start is already gone.
  sleep 1
  _guest "logcat -c" || true
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
  # One UDP query can be dropped, and a missing start reading turns the whole
  # case inconclusive (S3 window 3: clock-start.pcap held no complete exchange
  # while the end reading was -2.35 ms). Capture until the pcap carries one
  # complete exchange, at most three times; the reading is still taken at this
  # point in the run.
  local attempt exchange
  for attempt in 1 2 3; do
    # Capture on the guest, on the guest clock; record tcpdump's own pid and stop
    # it by that pid (not pkill -f, which also matches this shell).
    _guest "rm -f /data/local/tmp/clock.pcap; tcpdump -i any -w /data/local/tmp/clock.pcap 'udp port 123 and host $SNTP_SERVER' >/dev/null 2>&1 & echo \$! > /data/local/tmp/clock.pid; sleep 1; (toybox sntp -q $SNTP_SERVER || true) >/dev/null 2>&1; sleep 1; kill -INT \$(cat /data/local/tmp/clock.pid); for i in \$(seq 1 20); do kill -0 \$(cat /data/local/tmp/clock.pid) 2>/dev/null || break; sleep 0.2; done; sync"
    "${S[@]}" pull /data/local/tmp/clock.pcap "$out" 2>&1 | tail -1
    exchange=$(PYTHONPATH="$HERE/../src" python3 - "$out" <<'PY'
import sys
from de4sdv_broker_path_bench import clock
from de4sdv_broker_path_bench.pcap import read_pcap
try:
    exchanges = clock.exchanges(read_pcap(sys.argv[1]))
except Exception:                                   # noqa: BLE001 - report, do not crash the capture
    print("")
else:
    print("yes" if exchanges and clock.best(exchanges[0]) is not None else "")
PY
)
    [ -n "$exchange" ] && { log "captured one complete NTP exchange into $out"; return 0; }
    log "no complete NTP exchange in $out (attempt $attempt); capturing again"
  done
  log "ERROR: no complete NTP exchange in $out after 3 captures"
  return 1
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
  set) set_clock ;;
  measure) shift; measure "$@" ;;
  host-steps) shift; host_steps "$@" ;;
  drift) drift ;;
  *) echo "usage: $0 {allow|deny|setup|set|measure <out.pcap>|host-steps <out.txt>|drift}" >&2; exit 2 ;;
esac
