#!/usr/bin/env bash
# Launch the two-domain guest: the SDV Core VM (instance 1) and the IVI VM
# (instance 2), both from one android17-release revision, both UNLOCKED
# (ADR 0025, decision 8). The SDV Core VM boots with
# androidboot.sdv.someip.enable=true; the reboot path keeps that launch
# configuration (GAP-MW-048), because it restarts the guest in place rather
# than creating it anew.
#
#   launch_two_vms.sh up            create both groups (idempotent; a present group is left running)
#   launch_two_vms.sh reboot-core   reboot the SDV Core VM, keeping its launch configuration (GAP-MW-048)
#   launch_two_vms.sh reboot-ivi    reboot the IVI VM (its SD agent reads ACLs only at start)
#   launch_two_vms.sh down          stop and remove both groups (the undo)
#   launch_two_vms.sh status        print the fleet
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
export ANDROID_HOST_OUT="$AOSP_HOST_OUT"
export PATH="$AOSP_HOST_OUT/bin:$PATH"

# UNLOCKED boot, with the SOME/IP stack enabled on the core. The addresses and
# instance names follow the documented SDV development mesh.
CORE_BOOT="androidboot.sdv.instance_name=instance1 androidboot.sdv.boot_mode=unlocked androidboot.virt.address=3 androidboot.sdv.someip.enable=true androidboot.sdv.ignore_avb_state=true"
IVI_BOOT="androidboot.sdv.instance_name=instance2 androidboot.sdv.boot_mode=unlocked androidboot.virt.address=4 androidboot.sdv.someip.enable=false androidboot.sdv.ignore_avb_state=true"

_group_present() { "$CVD" fleet 2>/dev/null | grep -q "\"group_name\" : \"$1\""; }

_create() {
  local group="$1" product="$2" instance="$3" bootcfg="$4" cpus="$5" mem="$6"
  if _group_present "$group"; then log "group $group already present; leaving it"; return 0; fi
  ANDROID_PRODUCT_OUT="$AOSP_TOP/out/target/product/$product" \
    "$CVD" create --group_name="$group" --base_instance_num="$instance" \
      --cpus="$cpus" --memory_mb="$mem" \
      --extra_bootconfig_args="$bootcfg" --report_anonymous_usage_stats=n 2>&1 | tail -2
  log "created $group from $product (instance $instance)"
}

up() {
  require_cmd "$CVD" "$ADB" || return 1
  _create "$CORE_GROUP" "$CORE_PRODUCT" "$CORE_INSTANCE" "$CORE_BOOT" 4 4096
  _create "$IVI_GROUP" "$IVI_PRODUCT" "$IVI_INSTANCE" "$IVI_BOOT" 8 8192
}

reboot_core() {
  # In-guest reboot keeps the launch configuration (the extra kernel command
  # line), so androidboot.sdv.someip.enable=true survives (GAP-MW-048).
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$CORE_ADB" reboot
  log "rebooted the SDV Core VM in place (launch configuration kept)"
}

reboot_ivi() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" reboot
  log "rebooted the IVI VM in place"
}

down() {
  for group in "$CORE_GROUP" "$IVI_GROUP"; do
    if _group_present "$group"; then
      "$CVD" --group_name="$group" stop 2>&1 | tail -1 || true
      "$CVD" --group_name="$group" remove 2>&1 | tail -1 || true
      log "stopped and removed $group"
    fi
  done
}

case "${1:-status}" in
  up) up ;;
  reboot-core) reboot_core ;;
  reboot-ivi) reboot_ivi ;;
  down) down ;;
  status) "$CVD" fleet 2>&1 | head -40 ;;
  *) echo "usage: $0 {up|reboot-core|reboot-ivi|down|status}" >&2; exit 2 ;;
esac
