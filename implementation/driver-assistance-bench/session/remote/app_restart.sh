#!/bin/bash
# The IVI app's restart before each window (lead answer B10.2 of 2026-11-18): a first `true` after the app starts
# shows the warning, so the app is restarted with am start -S right before the window, and no message of an
# earlier run can be on the display. Also records, for this window, the app's APK and both guests' SELinux mode
# (guest-prep-20261118 report, item 5: getenforce on every run).
#
#   app_restart.sh <out_dir> <label>     exit 0 when the app's process runs again; <out_dir>/app_restart_<label>.txt
#
# Fails, before the restart, when a guest's SELinux mode is not the session's mark: the SDV Core guest Enforcing, the
# IVI guest Enforcing, or Permissive with IVI_PERMISSIVE=1 (the session's --permissive-ivi).
# env: ADB, IVI_ADB (0.0.0.0:6522), CORE_ADB (0.0.0.0:6521), APP_PACKAGE, APP_COMPONENT (both from the session's
#      entrypoints.env, read from the app's manifest), IVI_PERMISSIVE (0), START_WAIT_S (5), ADB_TO_S (30).
set -uo pipefail
OUT=${1:?out dir}; LABEL=${2:?label}; mkdir -p "$OUT"
: "${AOSP_TOP:=$HOME/aosp}"
ADB=${ADB:-${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}/bin/adb}
IVI_ADB=${IVI_ADB:-0.0.0.0:6522}; CORE_ADB=${CORE_ADB:-0.0.0.0:6521}
APP_PACKAGE=${APP_PACKAGE:?APP_PACKAGE}; APP_COMPONENT=${APP_COMPONENT:?APP_COMPONENT}
REC=$OUT/app_restart_$LABEL.txt
a() { timeout "${ADB_TO_S:-30}" "$ADB" -s "$IVI_ADB" "$@"; }
{
  echo "window $LABEL $(date -u +%FT%T.%3NZ)"
  echo "getenforce core $(timeout "${ADB_TO_S:-30}" "$ADB" -s "$CORE_ADB" shell getenforce 2>/dev/null | tr -d '\r')"
  echo "getenforce ivi $(a shell getenforce 2>/dev/null | tr -d '\r')"
  APK=$(a shell pm path "$APP_PACKAGE" 2>/dev/null | tr -d '\r' | sed -n 's/^package://p' | head -1)
  echo "apk ${APK:-none} sha256 $([ -n "$APK" ] && a shell sha256sum "$APK" 2>/dev/null | tr -d '\r' | cut -d' ' -f1)"
} | tee "$REC"
grep -q '^apk none' "$REC" && { echo "FAIL $APP_PACKAGE is not installed on the IVI guest" | tee -a "$REC"; exit 1; }
# the session's mark (owner decision (b) of 2026-11-18): the SDV Core guest always Enforcing; the IVI guest Enforcing,
# or Permissive only in a session started with --permissive-ivi (IVI_PERMISSIVE=1), which marks every result (R16)
WANT_IVI=Enforcing; [ "${IVI_PERMISSIVE:-0}" = 1 ] && WANT_IVI=Permissive
for g in "core Enforcing" "ivi $WANT_IVI"; do
  set -- $g
  got=$(sed -n "s/^getenforce $1 //p" "$REC")
  [ "$got" = "$2" ] || { echo "FAIL SELinux on the $1 guest reads '${got:-nothing}', this session's mark needs $2" \
    "(IVI_PERMISSIVE=${IVI_PERMISSIVE:-0})" | tee -a "$REC"; exit 1; }
done
echo "selinux core Enforcing, ivi $WANT_IVI: as this session's mark" | tee -a "$REC"
a shell "svc power stayon true; input keyevent KEYCODE_WAKEUP" > /dev/null 2>&1
START=$(a shell am start -S -W -n "$APP_COMPONENT" 2>&1 | tr -d '\r')
echo "$START" | sed 's/^/am: /' | tee -a "$REC"
echo "$START" | grep -q -E '^Error|Exception' && { echo "FAIL am start" | tee -a "$REC"; exit 1; }
sleep "${START_WAIT_S:-5}"
PID=$(a shell pidof "$APP_PACKAGE" 2>/dev/null | tr -d '\r')
echo "pid ${PID:-none} $(date -u +%FT%T.%3NZ)" | tee -a "$REC"
[ -n "$PID" ] || { echo "FAIL the app's process is not running" | tee -a "$REC"; exit 1; }
echo "APP_RESTARTED $LABEL"
