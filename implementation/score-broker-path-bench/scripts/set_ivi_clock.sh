#!/usr/bin/env bash
# Hold ASM-MW-030 on the IVI VM: turn off automatic time, set the clock once
# against the host chrony with a standard SNTP client, then slew it if the
# client can, and capture the NTP exchange so the evaluator can measure the
# offset from the raw packets. No DE4SDV code sets or crafts time; this calls
# the image's SNTP client (toybox sntp) and captures with tcpdump.
#
#   set_ivi_clock.sh setup                 auto_time off, set the clock once, start a slew if available
#   set_ivi_clock.sh measure <out.pcap>    capture one NTP query (no setting) for the evaluator
#   set_ivi_clock.sh drift                 two measures ~minutes apart, print the drift and the session length
#
# The measure captures are the clock-start.pcap and clock-end.pcap the
# evaluator reads (ASM-MW-030).
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
S=("$ADB" -s "$IVI_ADB")

_guest() { "${S[@]}" shell "$@"; }

have_sntp() { _guest "command -v sntp toybox" 2>/dev/null | grep -q .; }

setup() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true
  _guest "settings put global auto_time 0; settings put global auto_time_zone 0" 2>/dev/null || true
  if have_sntp; then
    # A one-shot set, then an adjust-mode slew if the client has it. A slew
    # moves CLOCK_REALTIME and CLOCK_MONOTONIC together, so it is no step.
    _guest "toybox sntp -s -S $SNTP_SERVER 2>&1 | tail -1" || _guest "sntp -s $SNTP_SERVER 2>&1 | tail -1" || true
    if _guest "toybox sntp --help 2>&1 | grep -q -- -a"; then
      _guest "start de4sdv_ivi_sntp 2>/dev/null; nohup toybox sntp -a -m 64 $SNTP_SERVER >/dev/null 2>&1 &" || true
      log "started an SNTP slew against $SNTP_SERVER"
    else
      log "the image SNTP client has no slew mode; size each session from the drift (run: $0 drift)"
    fi
  else
    log "no SNTP client in the IVI image; ASM-MW-030 cannot be held, record it as a gap"
    return 1
  fi
}

measure() {
  local out="${1:?usage: $0 measure <out.pcap>}"
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true
  # Capture the exchange on the guest, on the guest clock, then run one query.
  _guest "rm -f /data/local/tmp/clock.pcap; (tcpdump -i any -w /data/local/tmp/clock.pcap 'udp port 123 and host $SNTP_SERVER' >/dev/null 2>&1 &) ; sleep 1; (toybox sntp -q $SNTP_SERVER || sntp $SNTP_SERVER) >/dev/null 2>&1; sleep 1; pkill -f 'tcpdump.*clock.pcap' 2>/dev/null; sync"
  "${S[@]}" pull /data/local/tmp/clock.pcap "$out" 2>&1 | tail -1
  log "captured one NTP exchange into $out"
}

drift() {
  local dir="${RUN_DIR:-$HERE/../run}"; mkdir -p "$dir"
  measure "$dir/clock-start.pcap"
  log "waiting ${DRIFT_WAIT_S:=840} s to measure the drift (the spike saw about 60 ppm)"
  sleep "${DRIFT_WAIT_S}"
  measure "$dir/clock-end.pcap"
  PYTHONPATH="$HERE/../src" python3 - "$dir/clock-start.pcap" "$dir/clock-end.pcap" <<'PY'
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
  setup) setup ;;
  measure) shift; measure "$@" ;;
  drift) drift ;;
  *) echo "usage: $0 {setup|measure <out.pcap>|drift}" >&2; exit 2 ;;
esac
