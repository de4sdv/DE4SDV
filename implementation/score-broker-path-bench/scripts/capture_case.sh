#!/usr/bin/env bash
# Produce the raw artifacts a running case needs (review R20): the host frame
# stream, the guest frame stream, the relay log, the frame-assembler client
# check, the SD capture and the clock exchanges. The evaluator
# (de4sdv_broker_path_bench.run) reads them off the VM. Standard tools only; it
# never dispatches a workflow.
#
#   capture_case.sh start <out-dir>   start the captures and record the ss client check and clock start
#   capture_case.sh stop <out-dir>    stop the captures, pull the guest stream, clock end, ss check again
#
# Window: start, verify MONITORING, run the AEBS event, then stop. The relay
# logcat tag is a required input (the relay lane owns it).
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
[ -n "${2:-}" ] || { echo "usage: $0 {start|stop} <out-dir>" >&2; exit 2; }
OUT="$2"; mkdir -p "$OUT"
SCAN=(python3 -m de4sdv_broker_path_bench.hostscan)
export PYTHONPATH="$HERE/../src${PYTHONPATH:+:$PYTHONPATH}"

# The adapter must be the only client of the frame assembler (ASM-MW-029), and
# both #448 steps run: one lists the connections the frame assembler accepted
# (sport = :4721), the other names the process of each peer's client socket
# (dport = :4721), which must be the adapter. The record keeps the before and
# the after check; adapter_only holds only when both hold (review R17/R35).
_ss_client_check() {
  local phase="$1"
  ss -H -t -n -p state established "( sport = :$FRAME_ASSEMBLER_PORT )" 2>/dev/null \
    > "$OUT/ss_frame_assembler_sport_$phase.txt"
  ss -H -t -n -p state established "( dport = :$FRAME_ASSEMBLER_PORT )" 2>/dev/null \
    > "$OUT/ss_frame_assembler_dport_$phase.txt"
  "${SCAN[@]}" clients --sport "$OUT/ss_frame_assembler_sport_$phase.txt" \
    --dport "$OUT/ss_frame_assembler_dport_$phase.txt" --phase "$phase" \
    --record "$OUT/frame_assembler_clients.json" >/dev/null
}

start() {
  require_relay_inputs || return 2
  require_cmd tcpdump ss "$ADB" || true
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" root >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" logcat -G 16M >/dev/null 2>&1 || true
  : > "$OUT/.pids"
  # Host: the frame assembler stream on loopback.
  sudo tcpdump -i lo -s0 -U -w "$OUT/produced.pcap" "tcp port $FRAME_ASSEMBLER_PORT" >/dev/null 2>&1 &
  echo "produced $!" >> "$OUT/.pids"
  # Host: the SOME/IP crossing and SD on the bridge.
  sudo tcpdump -i "$HOST_BRIDGE" -s0 -U -w "$OUT/host-cvd-ebr.pcap" \
    "udp port $SD_PORT or tcp port $SOMEIP_RELIABLE_PORT" >/dev/null 2>&1 &
  echo "sd $!" >> "$OUT/.pids"
  # Guest: the relay stream on the IVI loopback, captured on the guest.
  "$ADB" -s "$IVI_ADB" shell "rm -f /data/local/tmp/received.pcap; tcpdump -i lo -s0 -U -w /data/local/tmp/received.pcap 'tcp port $RELAY_LOOPBACK_PORT' >/dev/null 2>&1 & echo \$! > /data/local/tmp/received.pid" >/dev/null 2>&1 || true
  # Guest: the cleartext Data Tunnel on VLAN 2, in the sdv_dt_ns namespace, for
  # the subscription corroboration of #448. The evaluator corroborates the
  # phase start with the loopback accept; this capture is retained for review
  # (consuming it is a known limit, see the README).
  "$ADB" -s "$IVI_ADB" shell "rm -f /data/local/tmp/data-tunnel-vlan2.pcap; ip netns exec sdv_dt_ns tcpdump -i sdv_dt -s0 -U -w /data/local/tmp/data-tunnel-vlan2.pcap >/dev/null 2>&1 & echo \$! > /data/local/tmp/dt.pid" >/dev/null 2>&1 || true
  # Guest: the relay log, streamed from before the event with epoch microseconds.
  ( "$ADB" -s "$IVI_ADB" logcat -v epoch -v usec "$RELAY_LOGCAT_TAG":* "*:S" > "$OUT/relay-logcat.txt" 2>/dev/null & echo "relaylog $!" >> "$OUT/.pids" )
  _ss_client_check before
  "$HERE/set_ivi_clock.sh" measure "$OUT/clock-start.pcap" || true
  sleep 1
  log "captures started in $OUT; verify MONITORING, run the AEBS event, then: $0 stop $OUT"
}

stop() {
  "$HERE/set_ivi_clock.sh" measure "$OUT/clock-end.pcap" || true
  _ss_client_check after
  # Stop the guest captures by their recorded pids, then the host captures.
  "$ADB" -s "$IVI_ADB" shell "kill -INT \$(cat /data/local/tmp/received.pid 2>/dev/null) \$(cat /data/local/tmp/dt.pid 2>/dev/null) 2>/dev/null; sleep 1; sync" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" pull /data/local/tmp/received.pcap "$OUT/received.pcap" 2>&1 | tail -1 || true
  "$ADB" -s "$IVI_ADB" pull /data/local/tmp/data-tunnel-vlan2.pcap "$OUT/data-tunnel-vlan2.pcap" 2>&1 | tail -1 || true
  if [ -f "$OUT/.pids" ]; then
    while read -r name pid; do
      case "$name" in relaylog) kill "$pid" 2>/dev/null || true ;; *) sudo kill -INT "$pid" 2>/dev/null || true ;; esac
    done < "$OUT/.pids"
  fi
  sleep 1
  for pcap in produced.pcap host-cvd-ebr.pcap; do [ -f "$OUT/$pcap" ] && sudo chown "$USER" "$OUT/$pcap" 2>/dev/null || true; done
  # Record the capture commands for the run manifest. The kernel drop count is
  # printed by the capture tool on exit (not into the pcap), so it is taken
  # from the run console; with -s0 it should be 0.
  { echo "captured_at: $(date -u +%FT%T.%NZ)"
    echo "produced: tcpdump -i lo tcp port $FRAME_ASSEMBLER_PORT"
    echo "received: guest tcpdump -i lo tcp port $RELAY_LOOPBACK_PORT"
    echo "data_tunnel_vlan2: guest ip netns exec sdv_dt_ns tcpdump -i sdv_dt (retained for review; not consumed)"
    echo "relay_logcat_tag: $RELAY_LOGCAT_TAG"
    echo "kernel_drops: record 'N packets dropped by kernel' from the capture tool's exit line (-s0 should give 0)"
  } > "$OUT/capture-manifest.yaml"
  log "captures stopped; artifacts in $OUT. Evaluate with: python -m de4sdv_broker_path_bench.run $OUT"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  *) echo "usage: $0 {start|stop} <out-dir>" >&2; exit 2 ;;
esac
