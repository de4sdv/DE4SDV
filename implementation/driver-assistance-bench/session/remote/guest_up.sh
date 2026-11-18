#!/bin/bash
# Guest host bring-up of a session (entry ENTRY_GUEST_UP): the two AAOS SDV guests through the bench's own launch,
# then the per-boot state and the identity a run records. Run in the foreground of the SSH call (host_step.sh run),
# never under systemd-run --user: the transient unit's cgroup takes the guests down with it.
#
#   guest_up.sh <out_dir>      exit 0 when both guests have booted; <out_dir>/guest_identity.txt
#
# env: GUEST_LAUNCH_CMD (default: score-broker-path-bench's launch_two_vms.sh up, as the guest build recipe's smoke
#      boot runs it), CORE_ADB (0.0.0.0:6521, base instance 2), IVI_ADB (0.0.0.0:6522, base instance 3),
#      APP_PACKAGE (org.de4sdv.collisionwarning), APP_COMPONENT (the activity to start; empty: no start),
#      BOOT_WAIT_S (900), LAUNCH_WAIT_S (1800).
set -uo pipefail
OUT=${1:?out dir}; mkdir -p "$OUT"
: "${AOSP_TOP:=$HOME/aosp}"; : "${DE4SDV_ROOT:=$HOME/de4sdv-e8fa324a}"
export ANDROID_HOST_OUT=${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}
export PATH="$ANDROID_HOST_OUT/bin:$PATH"
ADB=${ADB:-$ANDROID_HOST_OUT/bin/adb}
CORE_ADB=${CORE_ADB:-0.0.0.0:6521}; IVI_ADB=${IVI_ADB:-0.0.0.0:6522}
APP_PACKAGE=${APP_PACKAGE:-org.de4sdv.collisionwarning}; APP_COMPONENT=${APP_COMPONENT:-}
LAUNCH=${GUEST_LAUNCH_CMD:-bash $DE4SDV_ROOT/implementation/score-broker-path-bench/scripts/launch_two_vms.sh up}
ID=$OUT/guest_identity.txt

echo "launch: $LAUNCH"
timeout "${LAUNCH_WAIT_S:-1800}" bash -c "$LAUNCH" > "$OUT/launch.log" 2>&1 || { echo "FAIL launch (see launch.log)"; tail -5 "$OUT/launch.log"; exit 1; }
wait_boot() {
  local end=$(( $(date +%s) + ${BOOT_WAIT_S:-900} ))
  while [ "$(date +%s)" -lt "$end" ]; do
    "$ADB" connect "$1" > /dev/null 2>&1
    [ "$("$ADB" -s "$1" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && return 0
    sleep 5
  done
  return 1
}
for s in "$CORE_ADB" "$IVI_ADB"; do
  wait_boot "$s" || { echo "FAIL $s did not boot"; exit 1; }
  "$ADB" -s "$s" root > /dev/null 2>&1; sleep 2; "$ADB" connect "$s" > /dev/null 2>&1; wait_boot "$s"
  # per-boot state: permissive SELinux is a condition of the result and is recorded with it (brief R10)
  "$ADB" -s "$s" shell setenforce 0 > /dev/null 2>&1
  {
    echo "serial $s"
    echo "fingerprint $("$ADB" -s "$s" shell getprop ro.build.fingerprint | tr -d '\r')"
    echo "instance $("$ADB" -s "$s" shell getprop ro.boot.sdv.instance_name | tr -d '\r')"
    echo "getenforce $("$ADB" -s "$s" shell getenforce | tr -d '\r')"
  } | tee -a "$ID"
done
APK=$("$ADB" -s "$IVI_ADB" shell pm path "$APP_PACKAGE" 2>/dev/null | tr -d '\r' | sed -n 's/^package://p' | head -1)
if [ -n "$APK" ]; then
  echo "app $APP_PACKAGE $APK sha256 $("$ADB" -s "$IVI_ADB" shell sha256sum "$APK" | tr -d '\r' | cut -d' ' -f1)" | tee -a "$ID"
  "$ADB" -s "$IVI_ADB" shell am force-stop "$APP_PACKAGE"
  [ -n "$APP_COMPONENT" ] && "$ADB" -s "$IVI_ADB" shell am start -n "$APP_COMPONENT" | tr -d '\r'
else
  echo "app $APP_PACKAGE not installed on the IVI guest" | tee -a "$ID"
fi
echo "GUEST_UP_DONE"
