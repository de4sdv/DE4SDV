#!/usr/bin/env bash
# Bench recovery of a SOME/IP broker or stack death in the SDV Core VM
# (GAP-MW-048, owner decision of 2026-10-29). Both are oneshot services, so
# init does not restart them. The operator reboots the SDV Core VM in place,
# which keeps the launch configuration and so needs no restart on the host (no
# GAP-MW-039 burst); one procedure covers both deaths. Manual, bench only; no
# availability claim.
#
#   recover_core_vm.sh detect     report whether the broker or the stack has died
#   recover_core_vm.sh recover    reboot the SDV Core VM in place and wait for the frames
#   recover_core_vm.sh watch      poll detect; on a death, print the time and stop (the operator runs recover)
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
S=("$ADB" -s "$CORE_ADB")

# Detection: the SDV Core VM's logcat shows "Critical agent has died", and
# VmHealth reports all_service_bundles_alive=false (at 10 Hz) after a stack
# death.
detect() {
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  local critical alive
  critical="$("${S[@]}" shell "logcat -d -t 2000 2>/dev/null | grep -c 'Critical agent has died'" | tr -d '\r')"
  alive="$("${S[@]}" shell "logcat -d -t 2000 2>/dev/null | grep -o 'all_service_bundles_alive: [a-z]*' | tail -1" | tr -d '\r')"
  echo "critical_agent_died=${critical:-0} ${alive:-all_service_bundles_alive:unknown}"
  if [ "${critical:-0}" != 0 ] || echo "$alive" | grep -q false; then
    return 0  # a death is present
  fi
  return 1
}

recover() {
  log "GAP-MW-048 recovery: rebooting the SDV Core VM in place"
  "$HERE/launch_two_vms.sh" reboot-core
  local i; for i in $(seq 1 90); do
    "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
    [ "$("${S[@]}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && break
    sleep 2
  done
  log "SDV Core VM back up; the stack REQUESTs the frame service and the broker re-creates its publication"
  log "measure the stale duration on the HMI and the relay's new subscription (phase 10)"
}

watch() {
  log "watching the SDV Core VM for a broker or stack death (Ctrl-C to stop)"
  while true; do
    if detect >/dev/null; then log "DEATH detected: $(detect)"; log "run: $0 recover"; return 0; fi
    sleep "${WATCH_PERIOD_S:=5}"
  done
}

case "${1:-detect}" in
  detect) detect && log "a death is present" || log "no death detected" ;;
  recover) recover ;;
  watch) watch ;;
  *) echo "usage: $0 {detect|recover|watch}" >&2; exit 2 ;;
esac
