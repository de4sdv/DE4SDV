#!/usr/bin/env bash
# Build, install and verify the IVI observer of the driving operational state
# (INC-DRIVING-001 slice 10b, GAP-DRIVING-006).
#
#   stage_ivi_observer.sh check       the artifacts agree; change nothing
#   stage_ivi_observer.sh stage       copy the Soong modules (and the tree's Gateway Java client
#                                     sources) into the AOSP tree
#   stage_ivi_observer.sh build       stage, then build the app and its JVM tests (IVI product)
#   stage_ivi_observer.sh unstage     remove the staged modules from the tree
#   stage_ivi_observer.sh install     ACLs, APK into /vendor/priv-app, reboot the IVI VM
#   stage_ivi_observer.sh selinux     print the SELinux mode and this app's denials (read-only;
#                                     never set the guest permissive: sepolicy/README.md)
#   stage_ivi_observer.sh start       stay-awake, (re)start the observer, show its first lines
#   stage_ivi_observer.sh verify      the hop checks of the IVI side, read-only
#   stage_ivi_observer.sh record [s]  screenrecord s seconds (<= 180), guest clock around it, pull
#   stage_ivi_observer.sh pull [path] copy the record file off the IVI VM
#   stage_ivi_observer.sh remove      undo install (ACLs and APK), then reboot
#
# Modeled on the INC-AEBS-010 bench (the app module shape, the ACL files) and on
# score-broker-path-bench/scripts/provision_ivi_relay.sh (remount, one ACL file per
# subject, reboot, then the post-boot checks).
#
# The IVI image is NOT rebuilt: the module build produces the APK and the script pushes
# it, with the ACLs, into the remounted vendor partition. The fallback is building the
# app into the sdv_ivi_cf image (the AEBS app's route, about 3 h for the IVI product).
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
  # The app subscribes to the three units of the default mapping; the one-unit variant
  # (interop/variants/) has no IVI side.
  [ "$MAPPING_VARIANT" = three ] || { log "ERROR: MAPPING_VARIANT=$MAPPING_VARIANT: the app and the IVI ACLs name the three units only"; rc=1; }
  local u
  for u in $SERVICE_UNITS; do
    grep -q "topic: \"$u\"" "$INTEROP/acl/ivi_observer_subscriber.textproto" || { log "ERROR: subject ACL lacks unit $u"; rc=1; }
    grep -q "topic: \"$u\"" "$INTEROP/acl/ivi_broker_object_policy.textproto" || { log "ERROR: object policy lacks subscriber unit $u"; rc=1; }
    grep -q "name: \"$u\"" "$INTEROP/acl/ivi_broker_object_policy.textproto" || { log "ERROR: object policy lacks service_units $u"; rc=1; }
    grep -q "\"$u\"" "$subscriber" || { log "ERROR: java lacks unit $u"; rc=1; }
  done
  grep -q "message: \"$MESSAGE_NAME\"" "$INTEROP/acl/ivi_observer_subscriber.textproto" || { log "ERROR: subject ACL message"; rc=1; }
  grep -q "include: \"$OBSERVER_PACKAGE.$OBSERVER_BUNDLE\"" "$INTEROP/acl/ivi_broker_object_policy.textproto" || { log "ERROR: object policy reader"; rc=1; }
  grep -q "message: \"$MESSAGE_NAME\"" "$INTEROP/acl/ivi_broker_object_policy.textproto" || { log "ERROR: object policy message"; rc=1; }

  # The app must name the typed message, subscribe by name to the broker's units, and
  # must not carry a bytes type any more.
  grep -q "SUBJECT_PACKAGE = \"$OBSERVER_PACKAGE\"" "$subscriber" || { log "ERROR: java subject package"; rc=1; }
  grep -q "SUBJECT_BUNDLE = \"$OBSERVER_BUNDLE\"" "$subscriber" || { log "ERROR: java subject bundle"; rc=1; }
  grep -q "MESSAGE_NAME = \"$MESSAGE_NAME\"" "$subscriber" || { log "ERROR: java message name"; rc=1; }
  grep -q "PUBLISHER_PACKAGE = \"$BROKER_PACKAGE\"" "$subscriber" || { log "ERROR: java publisher package"; rc=1; }
  grep -q "PUBLISHER_BUNDLE = \"$BROKER_BUNDLE\"" "$subscriber" || { log "ERROR: java publisher bundle"; rc=1; }
  grep -q "subscribeToPublicationByName" "$subscriber" || { log "ERROR: java does not subscribe by name"; rc=1; }
  grep -q "REFLECTION" "$subscriber" || log "NOTE: the subscriber should say the translation is REFLECTION"
  if grep -rq 'bytes data' "$SLICE_ROOT/app" 2>/dev/null; then
    log "ERROR: the app still carries a bytes type (that is option A)"; rc=1
  fi
  grep -qE '^[[:space:]]*soong_namespace[[:space:]]*\{' "$SLICE_ROOT/app/Android.bp" "$CONTRACT/Android.bp" && { log "ERROR: a soong_namespace module hides app modules on this tree"; rc=1; }

  # The contract proto and the mapping are the ones the core side stages.
  grep -q "message $TYPE_NAME" "$CONTRACT/de4sdv_driving_operational_state.proto" || { log "ERROR: contract message name"; rc=1; }
  # The proto imports the catalog's publication annotations; the app's Java lite module
  # must have their directory (and protobuf's, for descriptor.proto) on its include path.
  if grep -q '^import "sdv/vsidl/v1/annotations.proto";' "$CONTRACT/de4sdv_driving_operational_state.proto"; then
    grep -q '"system/software_defined_vehicle/vsidl/language/src/protos"' "$CONTRACT/Android.bp" \
      && grep -q '"external/protobuf/src"' "$CONTRACT/Android.bp" \
      || { log "ERROR: contract/Android.bp lacks the include path of sdv/vsidl/v1/annotations.proto"; rc=1; }
  fi
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
  [ -d "$GATEWAY_JAVA_SRC/google/sdv/gateway/client" ] || {
    log "ERROR: no Gateway Java client sources at $GATEWAY_JAVA_SRC (set GATEWAY_JAVA_SRC)"; return 1; }
  rm -rf "$STAGED"
  mkdir -p "$STAGED"
  cp -a "$SLICE_ROOT/app" "$SLICE_ROOT/contract" "$STAGED/" || return 1
  # The client sources compiled into the app, exactly as the INC-AEBS-010 app carries
  # them (its app/src/google/sdv/gateway/client/). Copied from this tree, so they match
  # the image's client library; never committed to the repository.
  mkdir -p "$STAGED/app/src/google/sdv/gateway/client"
  cp -a "$GATEWAY_JAVA_SRC/google/sdv/gateway/client/." "$STAGED/app/src/google/sdv/gateway/client/" || return 1
  log "staged the Soong modules at $STAGED (app/, contract/) and $(find "$STAGED/app/src/google" -name '*.java' | wc -l) Gateway client sources"
  # Every proto_library in the tree breaks Soong analysis for EVERY product on this
  # release (the module type is not registered), so a core-side staging that appended
  # one stops this build too.
  if grep -rlsE '^proto_library[[:space:]]*\{' "$SAMPLES" --include=Android.bp | grep -q .; then
    log "WARNING: a proto_library module is staged in $SAMPLES; Soong will refuse the whole tree:"
    grep -rlsE '^proto_library[[:space:]]*\{' "$SAMPLES" --include=Android.bp | sed 's/^/  /'
  fi
}

unstage() {
  rm -rf "$STAGED"
  log "removed $STAGED"
}

build() {
  check || return 1
  # Never build the module under another variant than the product's last build: the
  # build system would installclean the product directory and delete the IVI images
  # (bench_env.sh, IVI_VARIANT).
  if [ -n "$IVI_LAST_BUILT" ] && [ "$IVI_LAST_BUILT" != "${IVI_PRODUCT}-${IVI_VARIANT}" ]; then
    log "ERROR: $IVI_PRODUCT was last built as $IVI_LAST_BUILT; a build as ${IVI_PRODUCT}-${IVI_VARIANT} forces an installclean that deletes its images. Unset IVI_VARIANT, or rebuild the whole product first."
    return 1
  fi
  stage || return 1
  [ -d "$AOSP_TOP" ] || { log "ERROR: no AOSP tree at $AOSP_TOP"; return 1; }
  local rc=0 build_log="$RUN_DIR/observer-build.log"
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${IVI_PRODUCT}-${RELEASE}-${IVI_VARIANT}" >/dev/null || exit 1
    m "$OBSERVER_APP" "$OBSERVER_TESTS"
  ) > "$build_log" 2>&1 || rc=1
  tail -8 "$build_log"
  [ "$rc" = 0 ] || { log "ERROR: the observer build failed (full log: $build_log)"; return 1; }
  [ -f "$OBSERVER_APK" ] || { log "ERROR: built, but no APK at $OBSERVER_APK"; return 1; }
  log "built $OBSERVER_APK ($(stat -c %s "$OBSERVER_APK") bytes, sha256 $(sha256sum "$OBSERVER_APK" | cut -c1-16))"
  log "JVM tests: built, not run by m; RUNBOOK step 8 runs them with the tree's JDK"
}

_ivi_root() {
  ivi_adb root >/dev/null 2>&1 || true
  ivi_adb wait-for-device
}

# remount /vendor and /product read-write. On a verity-enabled guest the first remount
# disables verity and asks for a reboot; reboot once and remount again.
_ivi_remount() {
  local out
  _ivi_root
  out="$(ivi_adb remount 2>&1)"; printf '%s\n' "$out" | tail -2
  if printf '%s' "$out" | grep -qi "reboot"; then
    log "remount needs a reboot (verity was on); rebooting once"
    ivi_adb reboot || return 1
    wait_boot ivi_adb "IVI VM" || return 1
    _ivi_root
    out="$(ivi_adb remount 2>&1)"; printf '%s\n' "$out" | tail -2
  fi
  printf '%s' "$out" | grep -qiE "remount succeeded|remounted" || { log "ERROR: remount did not succeed"; return 1; }
}

# Every ACL file of one subject must be unique across the roots the SD agent reads.
_acl_duplicates() {
  ivi_adb shell "find $ACL_ROOTS -name '*.textproto' 2>/dev/null | sed 's#.*/sdv_authz_acls/##' | sort | uniq -d" | tr -d '\r'
}

install() {
  check || return 1
  [ -f "$OBSERVER_APK" ] || { log "ERROR: build first ($OBSERVER_APK is missing)"; return 1; }
  _ivi_remount || return 1

  # Refuse BEFORE pushing when another root already holds a file for one of our subjects:
  # the SD agent exits on a duplicate subject, and only a reboot would show it.
  local subject root existing
  for subject in "$OBSERVER_PACKAGE/$OBSERVER_BUNDLE.textproto" "$BROKER_PACKAGE/$BROKER_BUNDLE.textproto"; do
    for root in $ACL_ROOTS; do
      [ "$root" = "$ACL_ROOT" ] && continue
      existing="$(ivi_adb shell "ls $root/$subject 2>/dev/null" | tr -d '\r')"
      if [ -n "$existing" ]; then
        log "ERROR: $existing already exists; merge our grant into it instead of adding a second file"
        return 1
      fi
    done
  done

  ivi_adb shell "mkdir -p '$ACL_ROOT/$OBSERVER_PACKAGE' '$ACL_ROOT/$BROKER_PACKAGE'" || return 1
  ivi_adb push "$INTEROP/acl/ivi_observer_subscriber.textproto" \
    "$ACL_ROOT/$OBSERVER_PACKAGE/$OBSERVER_BUNDLE.textproto" 2>&1 | tail -1
  ivi_adb push "$INTEROP/acl/ivi_broker_object_policy.textproto" \
    "$ACL_ROOT/$BROKER_PACKAGE/$BROKER_BUNDLE.textproto" 2>&1 | tail -1

  local dupes
  dupes="$(_acl_duplicates)"
  if [ -n "$dupes" ]; then
    log "ERROR: duplicate ACL subject files on the IVI VM (the SD agent will exit):"
    printf '%s\n' "$dupes"
    return 1
  fi

  # A /data/app copy of the package (an earlier `adb install`) would shadow the
  # vendor/priv-app copy as an "update"; remove it first.
  if ivi_adb shell pm path "$OBSERVER_PACKAGE" 2>/dev/null | tr -d '\r' | grep -q '/data/app/'; then
    log "removing the /data/app copy of $OBSERVER_PACKAGE"
    ivi_adb uninstall "$OBSERVER_PACKAGE" >/dev/null 2>&1 || true
  fi
  ivi_adb shell "mkdir -p '$OBSERVER_GUEST_DIR'" || return 1
  ivi_adb push "$OBSERVER_APK" "$OBSERVER_GUEST_DIR/$OBSERVER_APP.apk" 2>&1 | tail -1
  ivi_adb shell "chmod 0755 '$OBSERVER_GUEST_DIR'; chmod 0644 '$OBSERVER_GUEST_DIR/$OBSERVER_APP.apk'; restorecon -R '$OBSERVER_GUEST_DIR' 2>/dev/null || true"

  log "installed; rebooting so PackageManager scans the APK and the SD agent reads the ACLs"
  ivi_adb reboot || return 1
  wait_boot ivi_adb "IVI VM" || return 1
  _ivi_root
  local path
  path="$(ivi_adb shell pm path "$OBSERVER_PACKAGE" | tr -d '\r')"
  log "installed: ${path:-NOT FOUND}"
  case "$path" in
    *"$OBSERVER_GUEST_DIR/"*) ;;
    *) log "ERROR: PackageManager does not report $OBSERVER_GUEST_DIR (see RUNBOOK step 9)"; return 1 ;;
  esac
  ivi_adb shell "dumpsys package $OBSERVER_PACKAGE | grep -m3 -E 'codePath|pkgFlags|privateFlags'" | tr -d '\r' || true
  ivi_adb shell "dumpsys package $OBSERVER_PACKAGE | grep -A2 -m1 'usesLibraries\|usesLibraryFiles'" | tr -d '\r' || true

  # The run's identity of the IVI side, bound to the records pulled at the end of a run.
  {
    echo "# IVI observer identity $(date -u +%FT%T.%NZ)"
    echo "product: ${IVI_PRODUCT}-${RELEASE}-${IVI_VARIANT}, boot mode UNLOCKED"
    echo -n "ivi_fingerprint: "; ivi_adb shell getprop ro.build.fingerprint | tr -d '\r'
    echo -n "ivi_instance: "; ivi_adb shell getprop ro.boot.sdv.instance_name | tr -d '\r'
    echo -n "selinux: "; ivi_adb shell getenforce | tr -d '\r'
    sha256sum "$OBSERVER_APK" | sed 's#^#apk_host_sha256: #'
    echo -n "apk_guest_sha256: "; ivi_adb shell sha256sum "$OBSERVER_GUEST_DIR/$OBSERVER_APP.apk" | tr -d '\r' | awk '{print $1}'
    echo "subject: ${OBSERVER_PACKAGE}.${OBSERVER_BUNDLE}, message ${MESSAGE_NAME}"
    echo "publisher: ${BROKER_PACKAGE}.${BROKER_BUNDLE} units ${SERVICE_UNITS} (subscribed by name)"
    sha256sum "$INTEROP/acl/ivi_observer_subscriber.textproto" "$INTEROP/acl/ivi_broker_object_policy.textproto" | sed 's#^#acl_sha256: #'
  } > "$RUN_DIR/ivi-observer-identity.txt"
  log "recorded the IVI identity in $RUN_DIR/ivi-observer-identity.txt"
  log "clock: run ../score-broker-path-bench/scripts/set_ivi_clock.sh allow; ... set (see RUNBOOK step 10)"
}

selinux() {
  log "--- SELinux mode"
  ivi_adb shell getenforce | tr -d '\r'
  log "--- denials naming this app or the gateway (empty is the expected answer)"
  ivi_adb logcat -d 2>/dev/null | grep -i "avc: denied" | grep -iE "drivingstate|sdv_gateway|ISdvGateway|platform_app" | tail -10 | tr -d '\r'
  log "--- the app's gateway lines"
  ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" SdvGatewayClient 2>/dev/null | grep -iE "gateway|initComms|declared|statusCode" | tail -10 | tr -d '\r'
}

start() {
  ivi_adb shell "svc power stayon true; input keyevent KEYCODE_WAKEUP" >/dev/null 2>&1 || true
  # -S: a real restart (a restarted publisher resets its sequences; an old process would
  # show them as restarts), -W: wait for the launch.
  # OBSERVER_IMMERSIVE=1 asks the app to hide the system bars (the IVI's system bar policy decides).
  local extra=()
  [ "${OBSERVER_IMMERSIVE:-0}" = 1 ] && extra=(--ez immersive true)
  ivi_adb shell am start -S -W -n "$OBSERVER_PACKAGE/.MainActivity" ${extra[@]+"${extra[@]}"} 2>&1 | tail -4
  sleep 3
  ivi_adb shell "dumpsys window 2>/dev/null | grep -m1 mCurrentFocus" | tr -d '\r' || true
  ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | tail -20 || true
}

verify() {
  local rc=0 receipts
  log "--- IVI identity"
  ivi_adb shell getprop ro.build.fingerprint | tr -d '\r'
  ivi_adb shell getprop ro.boot.sdv.instance_name | tr -d '\r' | sed 's/^/instance: /'
  ivi_adb shell getenforce | tr -d '\r' | sed 's/^/selinux: /'
  log "--- ACL files"
  ivi_adb shell "ls -l $ACL_ROOT/$OBSERVER_PACKAGE $ACL_ROOT/$BROKER_PACKAGE" 2>/dev/null | tr -d '\r'
  log "--- the observer's own lines (last 15)"
  ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | tail -15 | tr -d '\r'
  log "--- the publisher units the discovery found, and the subscriptions (one per unit)"
  ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | grep -E "publisher_registered|subscribed=|gateway=|ready link=" | tail -8 | tr -d '\r'
  receipts="$(ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | grep -c 'kind=' | tr -d '\r')"
  log "receipts in the logcat buffer: ${receipts:-0}"
  local kind
  for kind in PLAN VEHICLE_STATE HEALTH; do
    log "  kind=$kind: $(ivi_adb logcat -d -s "$OBSERVER_LOGCAT_TAG" 2>/dev/null | grep -c " kind=$kind " | tr -d '\r')"
  done
  [ "${receipts:-0}" -gt 0 ] || { log "NO RECEIPTS: DESIGN.md section 1 (the hops) and section 8 (localizing a failure)"; rc=1; }
  log "--- SELinux denials of this app (empty is the expected answer)"
  ivi_adb logcat -d 2>/dev/null | grep -i "avc: denied" | grep -iE "drivingstate|ISdvGateway" | tail -5 | tr -d '\r'
  ivi_adb logcat -d 2>/dev/null | grep -qiE "avc: denied.*(drivingstate|ISdvGateway)" && { log "DENIAL: sepolicy/README.md names the capture and the fix"; rc=1; }
  return "$rc"
}

record() {
  local seconds="${1:-40}" out="$RUN_DIR/ivi_screen.mp4" display=()
  [ "$seconds" -le 180 ] 2>/dev/null || { log "ERROR: screenrecord's limit is 180 s"; return 1; }
  [ -n "$IVI_DISPLAY_ID" ] && display=(--display-id "$IVI_DISPLAY_ID")
  # adb itself in the background, not the ivi_adb function: killing a function's subshell leaves
  # its adb running, and the capture then keeps growing after the recording has ended.
  "$ADB" -s "$IVI_ADB" logcat -v epoch -T 1 -s "$OBSERVER_LOGCAT_TAG" > "$RUN_DIR/ivi_screen_logcat.txt" 2>&1 &
  local logpid=$!
  # The video has no usable creation time: bracket its start with the guest clock.
  ivi_adb shell 'date +%s.%N' | tr -d '\r' | sed 's/^/guest_real_before_start: /' > "$RUN_DIR/ivi_screen_t0.txt"
  ivi_adb shell screenrecord ${display[@]+"${display[@]}"} --time-limit "$seconds" --bit-rate 8000000 /data/local/tmp/ivi_screen.mp4 \
    > "$RUN_DIR/ivi_screen_screenrecord.txt" 2>&1 &
  local pid=$!
  ivi_adb shell 'date +%s.%N' | tr -d '\r' | sed 's/^/guest_real_after_start: /' >> "$RUN_DIR/ivi_screen_t0.txt"
  log "screenrecord ${seconds}s started (pid $pid); t0 bracket in $RUN_DIR/ivi_screen_t0.txt"
  wait "$pid" || true
  kill "$logpid" 2>/dev/null || true
  wait "$logpid" 2>/dev/null || true
  ivi_adb pull /data/local/tmp/ivi_screen.mp4 "$out" 2>&1 | tail -1
  ivi_adb shell rm -f /data/local/tmp/ivi_screen.mp4
  log "pulled $out ($(stat -c %s "$out" 2>/dev/null || echo 0) bytes) and the tag log"
}

pull() {
  local out="${1:-$RUN_DIR/observer.jsonl}"
  ivi_adb root >/dev/null 2>&1 || true
  ivi_adb wait-for-device
  # The app runs as the IVI's current user (user 10, "Driver", on sdv_ivi_cf), so its files
  # are under /data/user/<user>/, not under user 0's /data/data/.
  local user
  user="$(ivi_adb shell am get-current-user 2>/dev/null | tr -d '\r')"
  case "$user" in ''|*[!0-9]*) user=0 ;; esac
  ivi_adb exec-out "cat /data/user/$user/$OBSERVER_PACKAGE/files/$OBSERVER_RECORD 2>/dev/null" > "$out" 2>/dev/null
  if [ ! -s "$out" ]; then
    ivi_adb exec-out "run-as $OBSERVER_PACKAGE --user $user cat files/$OBSERVER_RECORD 2>/dev/null" > "$out" 2>/dev/null
  fi
  [ -s "$out" ] || { log "ERROR: no record file on the IVI VM (user $user)"; return 1; }
  # An error text in place of the file must not pass for a record.
  head -c 1 "$out" | grep -q '{' || { log "ERROR: $out does not start with a JSON record: $(head -c 120 "$out")"; return 1; }
  log "pulled $out ($(wc -l < "$out") lines)"
}

remove() {
  _ivi_remount || true
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
  selinux) selinux ;;
  start) start ;;
  verify) verify ;;
  record) shift; record "${1:-40}" ;;
  pull) shift; pull "${1:-$RUN_DIR/observer.jsonl}" ;;
  remove) remove ;;
  *) echo "usage: $0 {check|stage|unstage|build|install|selinux|start|verify|record [s]|pull [path]|remove}" >&2; exit 2 ;;
esac
