#!/bin/bash
# Guest host bring-up of a session (entry ENTRY_GUEST_UP): the two AAOS SDV guests through the bench's own launch,
# then the identity a run records. Run in the foreground of the SSH call (host_step.sh run), never under
# systemd-run --user: the transient unit's cgroup takes the guests down with it.
#
#   guest_up.sh <out_dir>      exit 0 when both guests have booted; <out_dir>/guest_identity.txt
#
# Once both have booted it prints one GUEST_IMAGE line per guest (sdv_core, then ivi), read from the booted guest:
# serial, product, build_id, fingerprint and vbmeta_digest (`unread` for a property with no answer). The session
# reads them from the step's tail into session.json execution_environment.sdv_core_image and .ivi_image.
#
# The guests are created fresh: launch_two_vms.sh down, then up. `up` alone skips the creation when stopped groups
# exist and then waits for adb without end, and a create is needed after any image change anyway (guest-prep-20261118
# report, steps 2 and 4). Fresh groups are stock guests with an empty /data: the session's prepare step
# (guest_prepare.sh) puts the app and its ACLs on again and reboots the IVI before any window.
# SELinux (that report, item 5): both guests boot Enforcing, and their mode is recorded. setenforce 0 is applied to
# the IVI guest only with IVI_PERMISSIVE=1, the session's --permissive-ivi, which marks the session's results
# conditional on a permissive IVI.
# env: GUEST_LAUNCH_CMD (default: score-broker-path-bench's launch_two_vms.sh down, then up), CORE_ADB (0.0.0.0:6521,
#      base instance 2), IVI_ADB (0.0.0.0:6522, base instance 3), APP_PACKAGE (org.de4sdv.collisionwarning),
#      IVI_PERMISSIVE (0), BOOT_WAIT_S (900), LAUNCH_WAIT_S (1800), ADB_TO_S (30, each adb call).
set -uo pipefail
OUT=${1:?out dir}; mkdir -p "$OUT"
: "${AOSP_TOP:=$HOME/aosp}"; : "${DE4SDV_ROOT:=$HOME/de4sdv-e8fa324a}"
export AOSP_TOP
export ANDROID_HOST_OUT=${ANDROID_HOST_OUT:-$AOSP_TOP/out/host/linux-x86}
export PATH="$ANDROID_HOST_OUT/bin:$PATH"
ADB=${ADB:-$ANDROID_HOST_OUT/bin/adb}
CORE_ADB=${CORE_ADB:-0.0.0.0:6521}; IVI_ADB=${IVI_ADB:-0.0.0.0:6522}
APP_PACKAGE=${APP_PACKAGE:-org.de4sdv.collisionwarning}; IVI_PERMISSIVE=${IVI_PERMISSIVE:-0}
L2=$DE4SDV_ROOT/implementation/score-broker-path-bench/scripts/launch_two_vms.sh
LAUNCH=${GUEST_LAUNCH_CMD:-bash $L2 down; bash $L2 up}
ID=$OUT/guest_identity.txt

# Every adb call is bounded (ADB_TO_S, default 30 s) with --foreground: the call stays in the step's process group,
# so a TERM to the step reaches it (plain GNU timeout would move it into a group of its own, which outlives the step)
adbt() { timeout --foreground "${ADB_TO_S:-30}" "$ADB" "$@"; }

# S1 (session/README.md): the trap may stop a guest host that never answered SSH without a crosvm count, on the
# assumption that no guest runs there before the session starts one. Counted here, before this launch, every session:
# a number only when pgrep answered (rc 0: some, rc 1: none); an error is "unknown", never 0. The last line repeats it,
# so the session reads it from the step's tail
CB=$(pgrep -c -x crosvm 2>/dev/null); cbrc=$?
[ "$cbrc" -le 1 ] && [[ "$CB" =~ ^[0-9]+$ ]] || CB=unknown
echo "$CB" > "$OUT/crosvm_before_launch.txt"
echo "crosvm processes before the launch: $CB"
echo "launch: $LAUNCH"
# GNU timeout (without --foreground) moves itself and the launch into a new process group, which a TERM to the step's
# group does not reach: the step then read as ended at once while the launch still created guests, and the session
# stopped the guest host under it (T1). So the launch runs in the background and is awaited with the wait builtin;
# a TERM, INT or HUP goes on to timeout (which signals the launch's own group), and the launch's end is awaited
# before this step ends: the step reads "running" on its host until the launch has ended, and fails.
launch_signal() {   # <signal> <exit code>
  trap '' TERM INT HUP
  local p=${LP:-$!} r
  kill -TERM "$p" 2>/dev/null; wait "$p"; r=$?
  echo "FAIL launch ended by $1 (the launch's rc $r; its end awaited before this step ended; see launch.log)"
  tail -5 "$OUT/launch.log"; exit "$2"
}
LP=""
trap 'launch_signal TERM 143' TERM; trap 'launch_signal INT 130' INT; trap 'launch_signal HUP 129' HUP
timeout "${LAUNCH_WAIT_S:-1800}" bash -c "$LAUNCH" > "$OUT/launch.log" 2>&1 & LP=$!
wait "$LP"; lrc=$?
trap - TERM INT HUP
[ "$lrc" = 0 ] || { echo "FAIL launch (rc $lrc; see launch.log)"; tail -5 "$OUT/launch.log"; exit 1; }
wait_boot() {
  local end=$(( $(date +%s) + ${BOOT_WAIT_S:-900} ))
  while [ "$(date +%s)" -lt "$end" ]; do
    adbt connect "$1" > /dev/null 2>&1
    [ "$(adbt -s "$1" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && return 0
    sleep 5
  done
  return 1
}
IMAGES=()
for s in "$CORE_ADB" "$IVI_ADB"; do
  wait_boot "$s" || { echo "FAIL $s did not boot"; exit 1; }
  adbt -s "$s" root > /dev/null 2>&1; sleep 2; adbt connect "$s" > /dev/null 2>&1; wait_boot "$s"
  # SELinux as the guest booted; permissive only by the session's mark (brief R10, the operator's item 5)
  if [ "$s" = "$IVI_ADB" ] && [ "$IVI_PERMISSIVE" = 1 ]; then
    adbt -s "$s" shell setenforce 0 > /dev/null 2>&1
    echo "IVI_PERMISSIVE=1: setenforce 0 on $s (the session's results are conditional on a permissive IVI)" | tee -a "$ID"
  fi
  {
    echo "serial $s"
    echo "fingerprint $(adbt -s "$s" shell getprop ro.build.fingerprint | tr -d '\r')"
    echo "instance $(adbt -s "$s" shell getprop ro.boot.sdv.instance_name | tr -d '\r')"
    echo "getenforce $(adbt -s "$s" shell getenforce | tr -d '\r')"
  } | tee -a "$ID"
  # the image this guest booted, from the guest itself, for the evidence record's executionEnvironmentIdentity:
  # its product, build id, build fingerprint and the vbmeta digest of the images it verified at boot; printed with
  # the step's last lines below (the session reads the tail); a property with no answer is `unread`, never empty
  role=ivi; [ "$s" = "$CORE_ADB" ] && role=sdv_core
  line="GUEST_IMAGE $role serial=$s"
  for kp in product=ro.product.name build_id=ro.build.id fingerprint=ro.build.fingerprint \
            vbmeta_digest=ro.boot.vbmeta.digest; do
    v=$(adbt -s "$s" shell getprop "${kp#*=}" 2>/dev/null | tr -d '\r' | head -1 | tr -s ' \t' '__')
    line="$line ${kp%%=*}=${v:-unread}"
  done
  IMAGES+=("$line")
done
APK=$(adbt -s "$IVI_ADB" shell pm path "$APP_PACKAGE" 2>/dev/null | tr -d '\r' | sed -n 's/^package://p' | head -1)
if [ -n "$APK" ]; then
  echo "app $APP_PACKAGE $APK sha256 $(adbt -s "$IVI_ADB" shell sha256sum "$APK" | tr -d '\r' | cut -d' ' -f1)" | tee -a "$ID"
else
  echo "app $APP_PACKAGE not installed on the IVI guest (expected after a fresh create: the prepare step installs it)" | tee -a "$ID"
fi
for line in "${IMAGES[@]}"; do echo "$line" | tee -a "$ID"; done
echo "GUEST_UP_DONE"
echo "CROSVM_BEFORE_LAUNCH $CB"
