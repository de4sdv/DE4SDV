#!/usr/bin/env bash
# Bench recovery of a SOME/IP broker or stack death in the SDV Core VM
# (GAP-MW-048, owner decision of 2026-10-29). Both are oneshot services, so
# init does not restart them. The operator reboots the SDV Core VM in place,
# which keeps the launch configuration and needs no restart on the host (no
# GAP-MW-039 burst); one procedure covers both deaths. Manual, bench only; no
# availability claim.
#
#   recover_core_vm.sh watch-health <out>  stream VmHealth into a file (run it during a case)
#   recover_core_vm.sh detect              report whether the broker or the stack has died
#   recover_core_vm.sh recover <out-dir>   save the detection evidence, then reboot and wait for the frames
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
S=("$ADB" -s "$CORE_ADB")

# VmHealth reaches logcat only through a subscriber; start it into a file
# before a case, so the 10 Hz all_service_bundles_alive series is retained.
watch_health() {
  local out="${1:?usage: $0 watch-health <out.txt>}"
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true
  log "streaming VmHealth into $out (Ctrl-C to stop)"
  "${S[@]}" shell "timeout ${HEALTH_SECONDS:-600} test_vm_health_subscriber" | tee "$out"
}

detect() {
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  local critical alive
  critical="$("${S[@]}" shell "logcat -d -t 4000 2>/dev/null | grep -c 'Critical agent has died'" | tr -d '\r')"
  alive="$("${S[@]}" shell "logcat -d -t 4000 2>/dev/null | grep -o 'all_service_bundles_alive: [a-z]*' | tail -1" | tr -d '\r')"
  echo "critical_agent_died=${critical:-0} ${alive:-all_service_bundles_alive:unknown}"
  { [ "${critical:-0}" != 0 ] || echo "$alive" | grep -q false; }
}

recover() {
  local out="${1:-$HERE/../run}"; mkdir -p "$out"
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  # Save the detection evidence before the reboot clears it.
  "${S[@]}" shell "logcat -d -b all" > "$out/core-logcat-pre-recovery.txt" 2>/dev/null || true
  detect > "$out/death-detection.txt" || true
  log "saved pre-recovery logcat and detection into $out"
  log "GAP-MW-048 recovery: rebooting the SDV Core VM in place"
  "$HERE/launch_two_vms.sh" reboot-core
  "${S[@]}" root >/dev/null 2>&1 || true
  log "SDV Core VM back up; someip.enable=$("${S[@]}" shell getprop ro.boot.sdv.someip.enable | tr -d '\r')"
  log "broker=$("${S[@]}" shell getprop init.svc.sdv_someip_broker_agent | tr -d '\r') stack=$("${S[@]}" shell getprop init.svc.sdv_someip_stack_agent | tr -d '\r')"
  log "measure the stale duration on the HMI and the relay's new subscription (phase 10)"
}

case "${1:-detect}" in
  watch-health) shift; watch_health "$@" ;;
  detect) detect && log "a death is present" || log "no death detected" ;;
  recover) shift; recover "$@" ;;
  *) echo "usage: $0 {watch-health <out>|detect|recover <out-dir>}" >&2; exit 2 ;;
esac
