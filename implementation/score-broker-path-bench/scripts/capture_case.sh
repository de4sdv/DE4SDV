#!/usr/bin/env bash
# Produce the raw artifacts a running case needs (review R20): the host frame
# stream, the guest frame stream, the relay log, the frame-assembler client
# check, the SD capture and the clock exchanges. The evaluator
# (de4sdv_broker_path_bench.run) reads them off the VM. Standard tools only; it
# never dispatches a workflow.
#
#   capture_case.sh start <out-dir>        start the captures and record the ss client check and clock start
#   capture_case.sh ivi-vm-down <out-dir>  the IVI-VM-down condition: reboot the IVI VM, start the captures
#                                          after the reboot, set the clock, then measure the clock start
#   capture_case.sh stop <out-dir>         stop the captures, pull the guest stream, clock end, ss check again
#
# Window: start, verify MONITORING, run the AEBS event, then stop. The relay
# logcat tag is a required input (the relay lane owns it).
#
# The guest captures and the relay-log stream end when the IVI VM reboots, so
# a run whose IVI VM rebooted inside the window cannot pass. Each run records
# the IVI boot identity at the start and the stop (ivi_boot.txt), and stop
# fails when they differ. For the IVI-VM-down condition of VC-MW-020 the
# captures therefore start after the reboot: ivi-vm-down reboots the IVI VM,
# checks that it came back with a new boot identity, starts the captures, sets
# the clock (set_ivi_clock.sh setup, which restarts the ingress so the judged
# phase starts after the setting) and only then measures the clock start
# (VC-MW-020 condition 2). The first phase after the reboot is in the relay log's
# buffer, so it is recorded as data.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
[ -n "${2:-}" ] || { echo "usage: $0 {start|ivi-vm-down|stop} <out-dir>" >&2; exit 2; }
OUT="$2"; mkdir -p "$OUT"
SCAN=(python3 -m de4sdv_broker_path_bench.hostscan)
export PYTHONPATH="$HERE/../src${PYTHONPATH:+:$PYTHONPATH}"
: "${VM_SCRIPT:=$HERE/launch_two_vms.sh}"
: "${CLOCK_SCRIPT:=$HERE/set_ivi_clock.sh}"

# The IVI VM's boot identity; it changes on every boot.
_ivi_boot_id() { "$ADB" -s "$IVI_ADB" shell "cat /proc/sys/kernel/random/boot_id" 2>/dev/null | tr -d '\r' | head -1; }

# The adapter must be the only client of the frame assembler (ASM-MW-029), and
# both steps of VC-MW-015 run: one lists the connections the frame assembler accepted
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

_start_captures() {
  require_relay_inputs || return 2
  require_cmd tcpdump ss "$ADB" || true
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" root >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" logcat -G 16M >/dev/null 2>&1 || true
  echo "capture_start: $(_ivi_boot_id)" >> "$OUT/ivi_boot.txt"
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
  # the subscription start of VC-MW-020. The VC-MW-020 evaluator takes the later of
  # the relay's phase start and the loopback accept; this capture is retained
  # for review (consuming it is a known limit, see the README).
  "$ADB" -s "$IVI_ADB" shell "rm -f /data/local/tmp/data-tunnel-vlan2.pcap; ip netns exec sdv_dt_ns tcpdump -i sdv_dt -s0 -U -w /data/local/tmp/data-tunnel-vlan2.pcap >/dev/null 2>&1 & echo \$! > /data/local/tmp/dt.pid" >/dev/null 2>&1 || true
  # Guest: the relay log, streamed from before the event with epoch microseconds.
  ( "$ADB" -s "$IVI_ADB" logcat -v epoch -v usec "$RELAY_LOGCAT_TAG":* "*:S" > "$OUT/relay-logcat.txt" 2>/dev/null & echo "relaylog $!" >> "$OUT/.pids" )
  _ss_client_check before
}

start() {
  _start_captures || return $?
  "$CLOCK_SCRIPT" measure "$OUT/clock-start.pcap" || true
  sleep 1
  log "captures started in $OUT; verify MONITORING, run the AEBS event, then: $0 stop $OUT"
}

# The IVI-VM-down condition (VC-MW-020 condition 2), scripted so the
# captures start after the reboot and the clock start follows the setting.
ivi_vm_down() {
  require_relay_inputs || return 2
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  local before after
  before="$(_ivi_boot_id)"
  echo "before_reboot: ${before:-unknown}" > "$OUT/ivi_boot.txt"
  log "IVI-VM-down: rebooting the IVI VM (boot ${before:-unknown})"
  "$VM_SCRIPT" reboot-ivi || { log "ERROR: the IVI VM reboot did not complete"; return 1; }
  after="$(_ivi_boot_id)"
  if [ -z "$after" ] || [ "$after" = "$before" ]; then
    log "ERROR: the IVI VM did not come back with a new boot identity (${after:-unknown}); no capture started"
    return 1
  fi
  # The captures start now, after the reboot; the relay log's buffer still
  # holds the first phase after the reboot, which the case records as data.
  _start_captures || return $?
  # Set the clock and restart the ingress; the judged phase starts after this.
  if ! "$CLOCK_SCRIPT" setup; then
    log "ERROR: the clock setting failed; this run cannot be judged. Stop it with: $0 stop $OUT"
    return 1
  fi
  "$CLOCK_SCRIPT" measure "$OUT/clock-start.pcap" || true
  sleep 1
  log "IVI-VM-down: captures started after the reboot (boot $after) and the clock is set; set condition ivi_vm_down in settings.json, run the AEBS event, then: $0 stop $OUT"
}

stop() {
  # A reboot of the IVI VM inside the window ends the guest captures and the
  # relay-log stream, so the run cannot pass; record it and fail at the end.
  local start_boot stop_boot rebooted=false
  start_boot="$(awk '$1=="capture_start:"{v=$2} END{print v}' "$OUT/ivi_boot.txt" 2>/dev/null)"
  stop_boot="$(_ivi_boot_id)"
  echo "capture_stop: ${stop_boot:-unknown}" >> "$OUT/ivi_boot.txt"
  if [ -z "$start_boot" ] || [ -z "$stop_boot" ] || [ "$start_boot" != "$stop_boot" ]; then rebooted=true; fi
  "$CLOCK_SCRIPT" measure "$OUT/clock-end.pcap" || true
  _ss_client_check after
  # Stop the HOST captures first (produced.pcap, the SD capture), then settle at
  # least a second, then stop the GUEST captures. The guest (received) capture
  # must outlive the host (produced) capture, or the host stream would record
  # frames the stack produced after the guest capture ended, a false stop and a
  # false completeness failure (review B1). The relay-log stream is stopped with
  # the guest captures, so it covers the whole window.
  if [ -f "$OUT/.pids" ]; then
    while read -r name pid; do
      case "$name" in relaylog) : ;; *) sudo kill -INT "$pid" 2>/dev/null || true ;; esac
    done < "$OUT/.pids"
  fi
  sleep 2
  "$ADB" -s "$IVI_ADB" shell "kill -INT \$(cat /data/local/tmp/received.pid 2>/dev/null) \$(cat /data/local/tmp/dt.pid 2>/dev/null) 2>/dev/null; sleep 1; sync" >/dev/null 2>&1 || true
  if [ -f "$OUT/.pids" ]; then
    while read -r name pid; do [ "$name" = relaylog ] && { kill "$pid" 2>/dev/null || true; }; done < "$OUT/.pids"
  fi
  "$ADB" -s "$IVI_ADB" pull /data/local/tmp/received.pcap "$OUT/received.pcap" 2>&1 | tail -1 || true
  "$ADB" -s "$IVI_ADB" pull /data/local/tmp/data-tunnel-vlan2.pcap "$OUT/data-tunnel-vlan2.pcap" 2>&1 | tail -1 || true
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
    echo "ivi_boot_start: ${start_boot:-unknown}"
    echo "ivi_boot_stop: ${stop_boot:-unknown}"
    echo "ivi_rebooted_in_window: $rebooted"
  } > "$OUT/capture-manifest.yaml"
  if [ "$rebooted" = true ]; then
    log "ERROR: the IVI VM boot identity changed inside the window (${start_boot:-unknown} -> ${stop_boot:-unknown}); the guest captures ended at the reboot, so this run cannot pass"
    return 1
  fi
  log "captures stopped; artifacts in $OUT. Evaluate with: python -m de4sdv_broker_path_bench.run $OUT"
}

case "${1:-}" in
  start) start ;;
  ivi-vm-down) ivi_vm_down ;;
  stop) stop ;;
  *) echo "usage: $0 {start|ivi-vm-down|stop} <out-dir>" >&2; exit 2 ;;
esac
