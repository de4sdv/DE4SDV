#!/usr/bin/env bash
# Build, install and verify the IVI observer of the driving operational state
# (INC-DRIVING-001 slice 10b, GAP-DRIVING-006).
#
#   stage_ivi_observer.sh check     the artifacts agree; change nothing
#   stage_ivi_observer.sh stage     copy the Soong modules into the AOSP tree
#   stage_ivi_observer.sh build     stage, then build the app (IVI product)
#   stage_ivi_observer.sh unstage   remove the staged modules from the tree
#   stage_ivi_observer.sh install   ACLs, APK into /system/priv-app, reboot the IVI VM
#   stage_ivi_observer.sh start     stay-awake, launch the observer, tail the record tag
#   stage_ivi_observer.sh verify    the hop checks of the IVI side, read-only
#   stage_ivi_observer.sh record    screenrecord N seconds and pull the clip
#   stage_ivi_observer.sh pull      copy the record file off the IVI VM
#   stage_ivi_observer.sh remove    undo install (ACLs and APK), then reboot
#
# Modeled on aaos-sdv-reference-interop-bench/aosp/vehicle_speed_bridge/stage_aosp_bridge.sh
# (build the module in the AOSP tree) and score-broker-path-bench/scripts/provision_ivi_relay.sh
# (remount, one ACL file per subject, reboot, then the post-boot checks).
#
# The IVI image is NOT rebuilt: the ACLs and the APK are pushed, as the AEBS
# bench pushed its relay and the INC-AEBS-010 bench installed its HMI app. That
# is the cheap path of the two in DESIGN.md section 4; the runbook names the
# fallback (build the app into sdv_ivi_cf) and the gate that decides it.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"

mkdir -p "$RUN_DIR"

check() {
  local rc=0 subscriber="$SLICE_ROOT/app/src/org/de4sdv/drivingstate/TypedStateSubscriber.java"
  [ -f "$SLICE_ROOT/app/AndroidManifest.xml" ] || { log "ERROR: app manifest missing"; rc=1; }
  [ -f "$subscriber" ] || { log "ERROR: the subscriber source is missing"; rc=1; }
  [ -f "$SLICE_ROOT/app/src/org/de4sdv/drivingstate/StateRecord.java" ] || { log "ERROR: StateRecord.java missing"; rc=1; }
  [ -f "$INTEROP/acl/ivi_observer_subscriber.textproto" ] || { log "ERROR: subject ACL missing"; rc=1; }
  [ -f "$INTEROP/acl/ivi_broker_object_policy.textproto" ] || { log "ERROR: object policy missing"; rc=1; }
  grep -q "topic: \"$TOPIC\"" "$INTEROP/acl/ivi_observer_subscriber.textproto" || { log "ERROR: subject ACL topic"; rc=1; }
  grep -q "message: \"$MESSAGE_NAME\"" "$INTEROP/acl/ivi_observer_subscriber.textproto" || { log "ERROR: subject ACL message"; rc=1; }
  grep -q "include: \"$OBSERVER_PACKAGE.$OBSERVER_BUNDLE\"" "$INTEROP/acl/ivi_broker_object_policy.textproto" || { log "ERROR: object policy reader"; rc=1; }
  grep -q "message: \"$MESSAGE_NAME\"" "$INTEROP/acl/ivi_broker_object_policy.textproto" || { log "ERROR: object policy message"; rc=1; }

  # The app must name the typed message and must not carry a bytes type any more.
  grep -q "SUBJECT_PACKAGE = \"$OBSERVER_PACKAGE\"" "$subscriber" || { log "ERROR: java subject package"; rc=1; }
  grep -q "TOPIC_NAME = \"$TOPIC\"" "$subscriber" || { log "ERROR: java topic"; rc=1; }
  grep -q "MESSAGE_NAME = \"$MESSAGE_NAME\"" "$subscriber" || { log "ERROR: java message name"; rc=1; }
  grep -q "REFLECTION" "$subscriber" || log "NOTE: the subscriber should say the translation is REFLECTION"
  if grep -rq 'bytes data' "$SLICE_ROOT/app" 2>/dev/null; then
    log "ERROR: the app still carries a bytes type (that is option A)"; rc=1
  fi

  # The contract proto and the mapping are the ones the core side stages.
  grep -q "message $TYPE_NAME" "$CONTRACT/de4sdv_driving_operational_state.proto" || { log "ERROR: contract message name"; rc=1; }
  python3 "$SLICE_ROOT/scripts/gen_someip_vsidl.py" --check || rc=1
  [ "$rc" = 0 ] && log "check: ok (artifacts agree; nothing touched)"
  return "$rc"
}

# Soong only sees modules inside the AOSP tree, so the app and the contract files
# are copied in, as the visualization bench staged its overlay under
# system/software_defined_vehicle/samples/ (where that release demonstrably
# instantiates modules).
STAGED="$SAMPLES/de4sdv_driving_observer"

stage() {
  [ -d "$SAMPLES" ] || { log "ERROR: no samples tree at $SAMPLES (set AOSP_TOP)"; return 1; }
  rm -rf "$STAGED"
  mkdir -p "$STAGED"
  cp -a "$SLICE_ROOT/app" "$SLICE_ROOT/contract" "$STAGED/" || return 1
  log "staged the Soong modules at $STAGED (app/, contract/)"
  log "UNLOCKED bench: the generated APEX signing material is a staging artifact, not a credential"
}

unstage() {
  rm -rf "$STAGED"
  log "removed $STAGED"
}

build() {
  check || return 1
  stage || return 1
  [ -d "$AOSP_TOP" ] || { log "ERROR: no AOSP tree at $AOSP_TOP"; return 1; }
  local rc=0
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${IVI_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m "$OBSERVER_APP" De4sdvDrivingStateRecordTest
  ) 2>&1 | tail -8 || rc=1
  [ "${PIPESTATUS[0]:-0}" = 0 ] || rc=1
  [ "$rc" = 0 ] || { log "ERROR: the observer build failed"; return 1; }
  [ -f "$OBSERVER_APK" ] || { log "ERROR: built, but no APK at $OBSERVER_APK"; return 1; }
  log "built $OBSERVER_APK ($(stat -c %s "$OBSERVER_APK") bytes)"
  log "JVM record test: run the tree's java_test runner for De4sdvDrivingStateRecordTest"
}

_ivi_root() { ivi_adb root >/dev/null 2>&1 || true; ivi_adb remount 2>&1 | tail -1; }

install() {
  check || return 1
  [ -f "$OBSERVER_APK" ] || { log "ERROR: build first ($OBSERVER_APK is missing)"; return 1; }
  _ivi_root || return 1

  ivi_adb shell "mkdir -p '$ACL_ROOT/$OBSERVER_PACKAGE' '$ACL_ROOT/$BROKER_PACKAGE'" || return 1
  ivi_adb push "$INTEROP/acl/ivi_observer_subscriber.textproto" \
    "$ACL_ROOT/$OBSERVER_PACKAGE/$OBSERVER_BUNDLE.textproto" 2>&1 | tail -1 || return 1
  ivi_adb push "$INTEROP/acl/ivi_broker_object_policy.textproto" \
    "$ACL_ROOT/$BROKER_PACKAGE/$BROKER_BUNDLE.textproto" 2>&1 | tail -1 || return 1

  # The SD agent exits when a second file names one subject: refuse to continue.
  local dupes
  dupes="$(ivi_adb shell "find $ACL_ROOTS -name '*.textproto' 2>/dev/null | sed 's#.*/sdv_authz_acls/##' | sort | uniq -d" | tr -d '\r')"
  if [ -n "$dupes" ]; then
    log "ERROR: duplicate ACL subject files on the IVI VM (the SD agent will exit):"
    printf '%s\n' "$dupes"
    return 1
  fi

  ivi_adb shell "mkdir -p '$OBSERVER_GUEST_DIR'" || return 1
  ivi_adb push "$OBSERVER_APK" "$OBSERVER_GUEST_DIR/$OBSERVER_APP.apk" 2>&1 | tail -1 || return 1
  ivi_adb shell "chmod 0755 '$OBSERVER_GUEST_DIR'; chmod 0644 '$OBSERVER_GUEST_DIR/$OBSERVER_APP.apk'; restorecon -R '$OBSERVER_GUEST_DIR' 2>/dev/null || true"

  log "installed; rebooting so PackageManager scans the APK and the SD agent reads the ACLs"
  ivi_adb reboot || return 1
  wait_boot ivi_adb "IVI VM" || return 1
  ivi_adb shell pm path "$OBSERVER_PACKAGE" | tr -d '\r' | sed 's/^/installed: /'
  ivi_adb shell "dumpsys package $OBSERVER_PACKAGE | grep -m1 -E 'versionName|codePath'" | tr -d '\r' || true

  # The run's identity of the IVI side. The AEBS bench left this to the console
  # (a known limit there); this slice records it here, at install, so the pull at
  # the end of a run has something to bind the records to.
  {
    echo "# IVI observer identity $(date -u +%FT%T.%NZ)"
    echo "product: ${IVI_PRODUCT}-${RELEASE}-${VARIANT}, boot mode UNLOCKED"
    echo -n "ivi_fingerprint: "; ivi_adb shell getprop ro.build.fingerprint | tr -d '\r'
    echo -n "ivi_instance: "; ivi_adb shell getprop ro.boot.sdv.instance_name | tr -d '\r'
    sha256sum "$OBSERVER_APK" | sed 's#^#apk_host_sha256: #'
    echo -n "apk_guest_sha256: "; ivi_adb shell sha256sum "$OBSERVER_GUEST_DIR/$OBSERVER_APP.apk" | tr -d '\r' | awk '{print $1}'
    echo "subject: ${OBSERVER_PACKAGE}.${OBSERVER_BUNDLE}, topic ${TOPIC}, message ${MESSAGE_NAME}"
    sha256sum "$INTEROP/acl/ivi_observer_subscriber.textproto" "$INTEROP/acl/ivi_broker_object_policy.textproto" | sed 's#^#acl_sha256: #'
  } > "$RUN_DIR/ivi-observer-identity.txt"
  log "recorded the IVI identity in $RUN_DIR/ivi-observer-identity.txt"
  log "clock: run ../score-broker-path-bench/scripts/set_ivi_clock.sh allow; ... set (see RUNBOOK step 9)"
}

start() {
  ivi_adb shell "svc power stayon true; input keyevent KEYCODE_WAKEUP" >/dev/null 2>&1 || true
  ivi_adb shell am start -n "$OBSERVER_PACKAGE/.MainActivity" 2>&1 | tail -2
  sleep 2
  ivi_adb shell "dumpsys window 2>/dev/null | grep -m1 mCurrentFocus" | tr -d '\r' || true
  ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | tail -20 || true
}

verify() {
  local rc=0 receipts
  log "--- IVI identity"
  ivi_adb shell getprop ro.build.fingerprint | tr -d '\r'
  ivi_adb shell getprop ro.boot.sdv.instance_name | tr -d '\r' | sed 's/^/instance: /'
  log "--- ACL files"
  ivi_adb shell "ls -l $ACL_ROOT/$OBSERVER_PACKAGE $ACL_ROOT/$BROKER_PACKAGE" 2>/dev/null | tr -d '\r'
  log "--- the observer's own lines (last 15)"
  ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | tail -15 | tr -d '\r'
  receipts="$(ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | grep -c 'kind=' | tr -d '\r')"
  log "receipts in the logcat buffer: ${receipts:-0}"
  [ "${receipts:-0}" -gt 0 ] || { log "NO RECEIPTS: check DESIGN.md section 7 (the hop table)"; rc=1; }
  log "--- SELinux denials of this app (empty is the expected answer)"
  ivi_adb logcat -d 2>/dev/null | grep -i "avc: denied" | grep -i "drivingstate" | tail -5 | tr -d '\r'
  ivi_adb logcat -d 2>/dev/null | grep -qi "avc: denied.*drivingstate" && { log "DENIAL: sepolicy/README.md names the capture and the fix"; rc=1; }
  return "$rc"
}

record() {
  local seconds="${1:-40}" out="$RUN_DIR/ivi_screen.mp4"
  ivi_adb shell "screenrecord --time-limit $seconds --bit-rate 8000000 /data/local/tmp/ivi_screen.mp4" &
  local pid=$!
  log "screenrecord ${seconds}s started (pid $pid)"
  ivi_adb logcat -s "$OBSERVER_LOGCAT_TAG" > "$RUN_DIR/ivi_screen_logcat.txt" 2>&1 &
  local logpid=$!
  wait "$pid" || true
  kill "$logpid" 2>/dev/null || true
  ivi_adb pull /data/local/tmp/ivi_screen.mp4 "$out" 2>&1 | tail -1
  ivi_adb shell rm -f /data/local/tmp/ivi_screen.mp4
  log "pulled $out ($(stat -c %s "$out" 2>/dev/null || echo 0) bytes) and the tag log"
}

pull() {
  local out="${1:-$RUN_DIR/observer.jsonl}"
  ivi_adb root >/dev/null 2>&1 || true
  ivi_adb exec-out "cat /data/data/$OBSERVER_PACKAGE/files/$OBSERVER_RECORD" > "$out" 2>/dev/null
  if [ ! -s "$out" ]; then
    ivi_adb exec-out "run-as $OBSERVER_PACKAGE cat files/$OBSERVER_RECORD" > "$out" 2>/dev/null
  fi
  [ -s "$out" ] || { log "ERROR: no record file on the IVI VM"; return 1; }
  log "pulled $out ($(wc -l < "$out") lines)"
}

remove() {
  _ivi_root || true
  ivi_adb shell "rm -f '$ACL_ROOT/$OBSERVER_PACKAGE/$OBSERVER_BUNDLE.textproto' '$ACL_ROOT/$BROKER_PACKAGE/$BROKER_BUNDLE.textproto'; rmdir '$ACL_ROOT/$OBSERVER_PACKAGE' 2>/dev/null; rm -rf '$OBSERVER_GUEST_DIR'" || true
  ivi_adb uninstall "$OBSERVER_PACKAGE" >/dev/null 2>&1 || true
  ivi_adb reboot || true
  log "removed the observer and its ACLs; rebooted"
}

case "${1:-}" in
  check) check ;;
  stage) stage ;;
  unstage) unstage ;;
  build) build ;;
  install) install ;;
  start) start ;;
  verify) verify ;;
  record) shift; record "${1:-40}" ;;
  pull) shift; pull "${1:-$RUN_DIR/observer.jsonl}" ;;
  remove) remove ;;
  *) echo "usage: $0 {check|stage|unstage|build|install|start|verify|record [s]|pull [path]|remove}" >&2; exit 2 ;;
esac
