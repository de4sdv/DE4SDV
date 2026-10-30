#!/usr/bin/env bash
# Launch the two-domain guest: the SDV Core VM (dev-mesh instance 1) and the
# IVI VM (dev-mesh instance 2), both from one android17-release revision, both
# UNLOCKED (ADR 0025, decision 8). It launches as the feasibility runs did:
# the cvd --config of each instance for its identity (truststore, DICE,
# keymint), plus the full extra bootconfig argument set with the boot mode
# forced to UNLOCKED and SOME/IP enabled on the core. The reboot path reboots
# the guest in place, so it keeps the launch configuration (GAP-MW-048).
#
#   launch_two_vms.sh up            create both groups (idempotent) and assert the boot properties
#   launch_two_vms.sh reboot-core   reboot the SDV Core VM in place (GAP-MW-048)
#   launch_two_vms.sh reboot-ivi    reboot the IVI VM (its SD agent reads ACLs only at start)
#   launch_two_vms.sh down          stop and remove both groups (the undo)
#   launch_two_vms.sh status        print the fleet
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
export ANDROID_HOST_OUT="$AOSP_HOST_OUT"
export PATH="$AOSP_HOST_OUT/bin:$PATH"

_group_present() { "$CVD" fleet 2>/dev/null | grep -q "\"group_name\" : \"$1\""; }

_create() {
  local group="$1" product="$2" instance="$3" config="$4" bootcfg="$5" cpus="$6" mem="$7"
  if _group_present "$group"; then log "group $group already present; leaving it"; return 0; fi
  ANDROID_PRODUCT_OUT="$AOSP_TOP/out/target/product/$product" \
    "$CVD" create --group_name="$group" --base_instance_num="$instance" --config="$config" \
      --cpus="$cpus" --memory_mb="$mem" \
      --extra_bootconfig_args="$bootcfg" --report_anonymous_usage_stats=n
  local rc=$?
  [ "$rc" = 0 ] || { log "cvd create $group failed (rc $rc)"; return 1; }
  log "created $group from $product (instance $instance, config $config)"
}

_assert_core() {
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  local s=("$ADB" -s "$CORE_ADB"); "${s[@]}" wait-for-device
  local props; props="$("${s[@]}" shell getprop ro.boot.sdv.instance_name; "${s[@]}" shell getprop ro.boot.sdv.boot_mode; "${s[@]}" shell getprop ro.boot.sdv.someip.enable)"
  log "core properties: $(echo "$props" | tr '\n' ' ')"
  echo "$props" | grep -qi unlocked || { log "ERROR: the SDV Core VM is not UNLOCKED"; return 1; }
  echo "$props" | grep -qi true || { log "ERROR: someip.enable is not true on the core"; return 1; }
  # The SD connection, from the core logcat.
  "${s[@]}" shell "logcat -d -t 2000 2>/dev/null | grep -m1 -E 'SDV Boot Mode is Unlocked|Connected to SD Agent on VM'" | tr -d '\r' | sed 's/^/core: /' || true
}

_assert_ivi() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  local s=("$ADB" -s "$IVI_ADB"); "${s[@]}" wait-for-device
  log "ivi properties: $("${s[@]}" shell getprop ro.boot.sdv.instance_name | tr -d '\r') $("${s[@]}" shell getprop ro.boot.sdv.boot_mode | tr -d '\r')"
  "${s[@]}" shell "logcat -d -t 2000 2>/dev/null | grep -m1 'Connected to SD Agent on VM'" | tr -d '\r' | sed 's/^/ivi: /' || true
}

up() {
  require_cmd "$CVD" "$ADB" || return 1
  "$CVD" fleet 2>&1 | head -20 || true
  _create "$CORE_GROUP" "$CORE_PRODUCT" "$CORE_INSTANCE" "$CORE_CONFIG" "$(core_bootconfig)" 4 4096 || return 1
  _create "$IVI_GROUP" "$IVI_PRODUCT" "$IVI_INSTANCE" "$IVI_CONFIG" "$(ivi_bootconfig)" 8 8192 || return 1
  _assert_core || return 1
  _assert_ivi || return 1
}

_reboot() {
  local serial="$1" what="$2"
  "$ADB" connect "$serial" >/dev/null 2>&1 || true
  "$ADB" -s "$serial" reboot
  # Wait for the device to drop and come back, so the boot wait does not race.
  "$ADB" -s "$serial" wait-for-disconnect 2>/dev/null || sleep 5
  "$ADB" connect "$serial" >/dev/null 2>&1 || true
  "$ADB" -s "$serial" wait-for-device
  local i; for i in $(seq 1 90); do
    [ "$("$ADB" -s "$serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && break; sleep 2
  done
  log "rebooted $what in place (launch configuration kept)"
}

case "${1:-status}" in
  up) up ;;
  reboot-core) _reboot "$CORE_ADB" "the SDV Core VM" ;;
  reboot-ivi) _reboot "$IVI_ADB" "the IVI VM" ;;
  down)
    for group in "$CORE_GROUP" "$IVI_GROUP"; do
      if _group_present "$group"; then
        "$CVD" --group_name="$group" stop 2>&1 | tail -1 || true
        "$CVD" --group_name="$group" remove 2>&1 | tail -1 || true
        log "stopped and removed $group"
      fi
    done ;;
  status) "$CVD" fleet 2>&1 | head -40 ;;
  *) echo "usage: $0 {up|reboot-core|reboot-ivi|down|status}" >&2; exit 2 ;;
esac
