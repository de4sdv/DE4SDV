#!/usr/bin/env bash
# Build, install and check the IVI warning presentation (INC-DRIVING-002, B10:
# CollisionWarningPresentationApplication, MAP-DRIVING-DA-WARNING-REQUEST hop 8).
#
#   stage_ivi_warning_app.sh check      the artifacts agree with ../interfaces/service_ids.json; change nothing
#   stage_ivi_warning_app.sh stage      copy the Soong modules, the typed message and the tree's Gateway Java
#                                       client sources into $AOSP_TOP/.../samples/de4sdv_collision_warning
#   stage_ivi_warning_app.sh build      stage, then m the app and its JVM tests under the IVI product's
#                                       recorded variant only (refuses any other: installclean trap)
#   stage_ivi_warning_app.sh install    ACLs (subject grant, broker object policy merged and logged), APK into
#                                       /vendor/priv-app, reboot the IVI VM, check PackageManager and that the
#                                       guest's APK sha256 equals the host's, write the identity
#
# Every push is checked (rc and the guest copy's sha256) and every adb call is bounded by
# ADB_TIMEOUT_S: a failed push or a wedged adb fails the step.
#   stage_ivi_warning_app.sh start      (re)start the app (am start -S) and show its first lines
#   stage_ivi_warning_app.sh verify     read-only: package, SELinux mode, gateway, the app's link lines
#   stage_ivi_warning_app.sh pull [f]   copy files/warning.jsonl off the IVI VM
#   stage_ivi_warning_app.sh unstage    remove the staged modules from the tree
#
# Modeled on closed-loop-driving-bench/ivi-observer/scripts/stage_ivi_observer.sh. The IVI image is
# not rebuilt: the module build makes the APK and install pushes it into the remounted vendor
# partition. It never changes the SELinux mode, never starts or stops a VM and never commits.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd -- "$HERE/.." && pwd)"
DA_ROOT="$(cd -- "$APP_ROOT/.." && pwd)"
IDS="$DA_ROOT/interfaces/service_ids.json"
ACLS="$DA_ROOT/ivi-warning/interop/acl"
PROTO_SRC="$DA_ROOT/ivi-warning/contract/de4sdv_driving_collision_warning_request.proto"

: "${AOSP_TOP:=$HOME/aosp}"
: "${AOSP_HOST_OUT:=$AOSP_TOP/out/host/linux-x86}"
: "${IVI_PRODUCT:=sdv_ivi_cf}"
: "${RELEASE:=cp2a}"
# The IVI product's recorded variant (phase10/aaos-build lib_common.sh IVI_VARIANT_PLAN, the
# INC-DRIVING-001 IVI identity sdv_ivi_cf-cp2a-userdebug). The build refuses to run under any other.
: "${RECORDED_IVI_VARIANT:=userdebug}"
: "${ADB:=$AOSP_HOST_OUT/bin/adb}"
: "${IVI_ADB:=0.0.0.0:6522}"
: "${ADB_TIMEOUT_S:=120}"
: "${VERIFY_WAIT_S:=60}"
: "${RUN_DIR:=$APP_ROOT/run}"
: "${GATEWAY_JAVA_SRC:=$AOSP_TOP/system/software_defined_vehicle/sdv_gateway/libsdvgatewayclient_java/src}"
: "${ACL_ROOTS:=/product/etc/sdv_authz_acls /system/etc/sdv_authz_acls /vendor/etc/sdv_authz_acls /system_ext/etc/sdv_authz_acls}"
: "${ACL_ROOT:=/product/etc/sdv_authz_acls}"
SAMPLES="$AOSP_TOP/system/software_defined_vehicle/samples"
STAGED="$SAMPLES/de4sdv_collision_warning"
APP_MODULE=De4sdvCollisionWarningPresentation
TEST_MODULE=De4sdvCollisionWarningPresentationTests
APK="$AOSP_TOP/out/target/product/$IVI_PRODUCT/vendor/priv-app/$APP_MODULE/$APP_MODULE.apk"
GUEST_DIR="/vendor/priv-app/$APP_MODULE"
TAG=DE4SDV_COLLISION_WARNING
RECORD=warning.jsonl
SUBSCRIBER="$APP_ROOT/app/src/org/de4sdv/collisionwarning/WarningRequestSubscriber.java"

log() { printf '%s %s\n' "$(date -u +%FT%T.%3NZ)" "$*"; }
ids() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2], {}, {'d': d}))" "$IDS" "$1"; }
POLICY_LINES=()
ivi_adb() { timeout "$ADB_TIMEOUT_S" "$ADB" -s "$IVI_ADB" "$@"; }
adb_bounded() { timeout "$ADB_TIMEOUT_S" "$ADB" "$@"; }
guest_sha256() { # <guest path> -> the 64-hex sha256, or nothing
  ivi_adb shell sha256sum "$1" 2>/dev/null | tr -d '\r' | awk 'NR == 1 && length($1) == 64 && $1 ~ /^[0-9a-f]+$/ {print $1}'
}
# One push whose failure fails the caller: the push's rc, then the guest copy's sha256 against the host's.
push_checked() { # <host file> <guest path>
  local out rc=0 want got
  out="$(ivi_adb push "$1" "$2" 2>&1)" || rc=$?
  printf '%s\n' "$out" | tail -1
  [ "$rc" = 0 ] || { log "ERROR: adb push $1 -> $2 failed (rc $rc)"; return 1; }
  want="$(sha256sum "$1" | cut -d' ' -f1)"
  got="$(guest_sha256 "$2")"
  [ "$got" = "$want" ] || { log "ERROR: after the push, $2 on the IVI VM has sha256 '${got:-none}', the host file $want"; return 1; }
}

APP_PACKAGE="$(ids "d['lane_choices']['ivi_subscriber']['package']")"
APP_BUNDLE="$(ids "d['lane_choices']['ivi_subscriber']['bundle']")"
BROKER_PACKAGE="$(ids "d['lane_choices']['sdv_core_broker']['package']")"
BROKER_BUNDLE="$(ids "d['lane_choices']['sdv_core_broker']['bundle']")"
MESSAGE="$(ids "d['icd']['data_tunnel']['message']")"
UNIT="$(ids "d['icd']['data_tunnel']['service_unit']")"

# The variant the IVI product was last built with ("" when never built).
last_ivi_variant() {
  local v
  v="$(sed -n 's/^PREVIOUS_BUILD_CONFIG := *//p' "$AOSP_TOP/out/target/product/$IVI_PRODUCT/previous_build_config.mk" 2>/dev/null | head -1)"
  v="${v#"$IVI_PRODUCT"-}"
  printf '%s' "${v##*-}"
}

check() {
  local rc=0
  for f in "$APP_ROOT/app/Android.bp" "$APP_ROOT/app/AndroidManifest.xml" "$APP_ROOT/contract/Android.bp" "$SUBSCRIBER" \
           "$PROTO_SRC" "$ACLS/ivi_warning_subscriber.textproto" "$ACLS/ivi_broker_object_policy.textproto"; do
    [ -f "$f" ] || { log "ERROR: missing $f"; rc=1; }
  done
  [ "$rc" = 0 ] || return 1
  grep -q "package=\"$APP_PACKAGE\"" "$APP_ROOT/app/AndroidManifest.xml" || { log "ERROR: manifest package is not $APP_PACKAGE"; rc=1; }
  grep -q "SUBJECT_PACKAGE = \"$APP_PACKAGE\"" "$SUBSCRIBER" || { log "ERROR: java subject package"; rc=1; }
  grep -q "SUBJECT_BUNDLE = \"$APP_BUNDLE\"" "$SUBSCRIBER" || { log "ERROR: java subject bundle"; rc=1; }
  grep -q "PUBLISHER_PACKAGE = \"$BROKER_PACKAGE\"" "$SUBSCRIBER" || { log "ERROR: java publisher package"; rc=1; }
  grep -q "PUBLISHER_BUNDLE = \"$BROKER_BUNDLE\"" "$SUBSCRIBER" || { log "ERROR: java publisher bundle"; rc=1; }
  grep -q "MESSAGE_NAME = \"$MESSAGE\"" "$SUBSCRIBER" || { log "ERROR: java message name"; rc=1; }
  grep -q "UNIT = \"$UNIT\"" "$SUBSCRIBER" || { log "ERROR: java unit name"; rc=1; }
  grep -q "message: \"$MESSAGE\"" "$ACLS/ivi_warning_subscriber.textproto" || { log "ERROR: subject ACL message"; rc=1; }
  grep -q "topic: \"$UNIT\"" "$ACLS/ivi_warning_subscriber.textproto" || { log "ERROR: subject ACL topic"; rc=1; }
  grep -q "include: \"$APP_PACKAGE.$APP_BUNDLE\"" "$ACLS/ivi_broker_object_policy.textproto" || { log "ERROR: object policy reader"; rc=1; }
  grep -q "name: \"$UNIT\"" "$ACLS/ivi_broker_object_policy.textproto" || { log "ERROR: object policy unit"; rc=1; }
  grep -q "srcs: \[\"$(basename "$PROTO_SRC")\"\]" "$APP_ROOT/contract/Android.bp" || { log "ERROR: contract/Android.bp does not name $(basename "$PROTO_SRC")"; rc=1; }
  grep -qE '^[[:space:]]*soong_namespace[[:space:]]*\{' "$APP_ROOT/app/Android.bp" "$APP_ROOT/contract/Android.bp" \
    && { log "ERROR: a soong_namespace module hides app modules on this tree"; rc=1; }
  [ "$rc" = 0 ] && log "check: ok (subject $APP_PACKAGE.$APP_BUNDLE, unit $UNIT, message $MESSAGE)"
  return "$rc"
}

stage() {
  check || return 1
  [ -d "$SAMPLES" ] || { log "ERROR: no samples tree at $SAMPLES (set AOSP_TOP)"; return 1; }
  [ -f "$GATEWAY_JAVA_SRC/google/sdv/gateway/client/SdvGatewayClient.java" ] || {
    log "ERROR: no Gateway Java client sources at $GATEWAY_JAVA_SRC (set GATEWAY_JAVA_SRC)"; return 1; }
  # Only our own staging directory is replaced; nothing else in the tree is touched.
  case "$STAGED" in */samples/de4sdv_collision_warning) ;; *) log "ERROR: unexpected staging path $STAGED"; return 1 ;; esac
  rm -rf -- "$STAGED"
  mkdir -p "$STAGED/app" "$STAGED/contract" "$STAGED/app/src/google/sdv/gateway/client" || return 1
  cp -a "$APP_ROOT/app/Android.bp" "$APP_ROOT/app/AndroidManifest.xml" "$APP_ROOT/app/src" "$APP_ROOT/app/tests" "$STAGED/app/" || return 1
  cp -a "$APP_ROOT/contract/Android.bp" "$PROTO_SRC" "$STAGED/contract/" || return 1
  cp -a "$GATEWAY_JAVA_SRC/google/sdv/gateway/client/." "$STAGED/app/src/google/sdv/gateway/client/" || return 1
  log "staged $STAGED (app/, contract/ with $(basename "$PROTO_SRC"), $(find "$STAGED/app/src/google" -name '*.java' | wc -l) Gateway client sources)"
}

unstage() {
  case "$STAGED" in */samples/de4sdv_collision_warning) rm -rf -- "$STAGED"; log "removed $STAGED" ;; esac
}

build() {
  local last; last="$(last_ivi_variant)"
  # The variant trap: a module build under another variant than the product's last one makes the build system
  # installclean the product directory and delete the IVI images. Build only with the recorded one.
  if [ -z "$last" ]; then
    log "ERROR: $IVI_PRODUCT has no previous_build_config.mk: the kept IVI images are not where AOSP_TOP says"; return 1
  fi
  if [ "$last" != "$RECORDED_IVI_VARIANT" ]; then
    log "ERROR: $IVI_PRODUCT was last built as '$last', the recorded variant is '$RECORDED_IVI_VARIANT'; refusing (installclean deletes the images)"; return 1
  fi
  log "variant guard ok: ${IVI_PRODUCT}-${RELEASE}-${RECORDED_IVI_VARIANT} (previous_build_config.mk says '$last')"
  stage || return 1
  mkdir -p "$RUN_DIR"
  local rc=0 build_log="$RUN_DIR/warning-app-build.log"
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${IVI_PRODUCT}-${RELEASE}-${RECORDED_IVI_VARIANT}" >/dev/null || exit 1
    m "$APP_MODULE" "$TEST_MODULE"
  ) > "$build_log" 2>&1 || rc=1
  tail -n 8 "$build_log"
  [ "$rc" = 0 ] || { log "ERROR: the app build failed (full log: $build_log)"; return 1; }
  [ -f "$APK" ] || { log "ERROR: built, but no APK at $APK"; return 1; }
  log "built $APK ($(stat -c %s "$APK") bytes, sha256 $(sha256sum "$APK" | cut -d' ' -f1))"
}

_ivi_root() {
  ivi_adb root >/dev/null 2>&1 || true; sleep "${ROOT_SETTLE_S:-2}"; adb_bounded connect "$IVI_ADB" >/dev/null 2>&1 || true
  ivi_adb wait-for-device || { log "ERROR: the IVI VM did not come back within ${ADB_TIMEOUT_S} s (adb wait-for-device)"; return 1; }
}

wait_boot() {
  local tries=180
  while [ "$tries" -gt 0 ]; do
    adb_bounded connect "$IVI_ADB" >/dev/null 2>&1 || true
    ivi_adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx 1 && { log "IVI VM booted"; return 0; }
    sleep 5; tries=$((tries - 1))
  done
  log "ERROR: the IVI VM did not reach sys.boot_completed=1"; return 1
}

_reboot() {
  ivi_adb reboot || return 1
  ivi_adb wait-for-disconnect 2>/dev/null || sleep 10
  wait_boot || return 1
  _ivi_root
}

# The broker object policy has one file per IVI VM; another increment's subscriber (the
# INC-DRIVING-001 observer) may already own it. Lead decision B10/B12-3: merge our blocks into it,
# idempotently, and log the sha256 before and after and the appended blocks. Sets POLICY_LINES.
merge_object_policy() { # <guest policy path>
  local policy="$1" ours="$ACLS/ivi_broker_object_policy.textproto" state sha_before sha_after want
  local acl_name include merged="$RUN_DIR/object-policy.merged.textproto" current="$RUN_DIR/object-policy.guest.read"
  acl_name="$(sed -n 's/^[[:space:]]*name: "\([A-Za-z0-9]*Reader\)"$/\1/p' "$ours" | head -1)"
  include="include: \"$APP_PACKAGE.$APP_BUNDLE\""
  [ -n "$acl_name" ] || { log "ERROR: no ACL name in $ours"; return 1; }
  state="$(ivi_adb shell "test -f '$policy' && echo present || echo absent" 2>/dev/null | tr -d '\r')"
  POLICY_LINES=()
  case "$state" in
    absent)
      sha_before=absent
      log "object policy: object_policy_sha256_before: absent ($policy)"
      cp "$ours" "$merged" || return 1
      POLICY_LINES+=("object_policy_action: installed ours (the guest had no file)") ;;
    present)
      ivi_adb exec-out "cat '$policy'" > "$current" || { log "ERROR: cannot read the guest's $policy"; return 1; }
      sha_before="$(guest_sha256 "$policy")"
      [ -n "$sha_before" ] && [ "$(sha256sum "$current" | cut -d' ' -f1)" = "$sha_before" ] \
        || { log "ERROR: the read of $policy is incomplete (guest ${sha_before:-no sha256}, read $(sha256sum "$current" | cut -c1-16))"; return 1; }
      log "object policy: object_policy_sha256_before: $sha_before ($policy)"
      # The guest's original is kept under its own digest and never overwritten.
      [ -f "$RUN_DIR/object-policy.guest.$sha_before.textproto" ] || cp "$current" "$RUN_DIR/object-policy.guest.$sha_before.textproto" || return 1
      local has_name=0 has_include=0
      grep -q "name: \"$acl_name\"" "$current" && has_name=1
      grep -qF "$include" "$current" && has_include=1
      if [ "$has_name$has_include" = 11 ]; then
        log "object policy: the guest's file already holds our ACL $acl_name and our $include; left as it is"
        POLICY_LINES+=("object_policy_action: already merged; left as it is")
        POLICY_LINES+=("object_policy_sha256_before: $sha_before" "object_policy_sha256_after: $sha_before")
        printf '%s\n' "${POLICY_LINES[@]}" | sed 's/^/object policy: /'
        return 0
      fi
      if [ "$has_name$has_include" != 00 ]; then
        log "ERROR: the guest's $policy holds only part of our blocks (ACL $acl_name: $has_name, $include: $has_include); merge it by hand"
        return 1
      fi
      { cat "$current"; echo; cat "$ours"; } > "$merged" || return 1
      POLICY_LINES+=("object_policy_action: merged our blocks into the guest's file (original kept as object-policy.guest.$sha_before.textproto)") ;;
    *) log "ERROR: cannot tell whether $policy exists on the IVI VM (answer '${state}')"; return 1 ;;
  esac
  push_checked "$merged" "$policy" || return 1
  want="$(sha256sum "$merged" | cut -d' ' -f1)"
  sha_after="$(guest_sha256 "$policy")"
  [ "$sha_after" = "$want" ] || { log "ERROR: the guest's $policy reads back as ${sha_after:-nothing}, the merged file is $want"; return 1; }
  POLICY_LINES+=("object_policy_sha256_before: $sha_before" "object_policy_sha256_after: $sha_after")
  local line
  while IFS= read -r line; do POLICY_LINES+=("object_policy_appended: $line"); done < <(grep -v '^[[:space:]]*#' "$ours" | grep -v '^[[:space:]]*$')
  printf '%s\n' "${POLICY_LINES[@]}" | sed 's/^/object policy: /'
}

# remount /vendor and /product read-write; on a verity-enabled guest the first remount disables
# verity and asks for a reboot: reboot once and remount again.
_ivi_remount() {
  local out
  _ivi_root || return 1
  out="$(ivi_adb remount 2>&1)"; printf '%s\n' "$out" | tail -2
  if printf '%s' "$out" | grep -qi "reboot"; then
    log "remount needs a reboot (verity was on); rebooting once"
    _reboot || return 1
    out="$(ivi_adb remount 2>&1)"; printf '%s\n' "$out" | tail -2
  fi
  printf '%s' "$out" | grep -qiE "remount succeeded|remounted" || { log "ERROR: remount did not succeed"; return 1; }
}

install() {
  check || return 1
  [ -f "$APK" ] || { log "ERROR: build first ($APK is missing)"; return 1; }
  mkdir -p "$RUN_DIR"
  _ivi_remount || return 1

  # The SD agent exits when two files name one subject: refuse before pushing.
  local subject root existing
  for subject in "$APP_PACKAGE/$APP_BUNDLE.textproto" "$BROKER_PACKAGE/$BROKER_BUNDLE.textproto"; do
    for root in $ACL_ROOTS; do
      [ "$root" = "$ACL_ROOT" ] && continue
      existing="$(ivi_adb shell "ls $root/$subject 2>/dev/null" | tr -d '\r')"
      [ -z "$existing" ] || { log "ERROR: $existing already exists; merge the grant into it instead of adding a second file"; return 1; }
    done
  done
  ivi_adb shell "mkdir -p '$ACL_ROOT/$APP_PACKAGE' '$ACL_ROOT/$BROKER_PACKAGE'" || return 1
  push_checked "$ACLS/ivi_warning_subscriber.textproto" "$ACL_ROOT/$APP_PACKAGE/$APP_BUNDLE.textproto" || return 1

  local policy="$ACL_ROOT/$BROKER_PACKAGE/$BROKER_BUNDLE.textproto"
  merge_object_policy "$policy" || return 1

  if ivi_adb shell pm path "$APP_PACKAGE" 2>/dev/null | tr -d '\r' | grep -q '/data/app/'; then
    log "removing the /data/app copy of $APP_PACKAGE (it would shadow the vendor copy)"
    ivi_adb uninstall "$APP_PACKAGE" >/dev/null 2>&1 || true
  fi
  ivi_adb shell "mkdir -p '$GUEST_DIR'" || return 1
  push_checked "$APK" "$GUEST_DIR/$APP_MODULE.apk" || return 1
  ivi_adb shell "chmod 0755 '$GUEST_DIR'; chmod 0644 '$GUEST_DIR/$APP_MODULE.apk'; restorecon -R '$GUEST_DIR' 2>/dev/null || true" || return 1

  log "installed; rebooting the IVI VM so PackageManager scans the APK and the SD agent reads the ACLs"
  _reboot || return 1
  local path
  path="$(ivi_adb shell pm path "$APP_PACKAGE" | tr -d '\r')"
  log "installed: ${path:-NOT FOUND}"
  case "$path" in *"$GUEST_DIR/"*) ;; *) log "ERROR: PackageManager does not report $GUEST_DIR"; return 1 ;; esac
  local host_sha guest_sha
  host_sha="$(sha256sum "$APK" | cut -d' ' -f1)"
  guest_sha="$(guest_sha256 "$GUEST_DIR/$APP_MODULE.apk")"
  [ "$guest_sha" = "$host_sha" ] || { log "ERROR: guest APK differs after the reboot (guest ${guest_sha:-none}, host $host_sha)"; return 1; }
  log "apk sha256 $host_sha on the host and on the IVI VM"
  {
    echo "# IVI warning presentation identity $(date -u +%FT%T.%3NZ)"
    echo "product: ${IVI_PRODUCT}-${RELEASE}-${RECORDED_IVI_VARIANT}"
    echo -n "ivi_fingerprint: "; ivi_adb shell getprop ro.build.fingerprint | tr -d '\r'
    echo -n "ivi_instance: "; ivi_adb shell getprop ro.boot.sdv.instance_name | tr -d '\r'
    echo -n "selinux_at_install: "; ivi_adb shell getenforce | tr -d '\r'
    sha256sum "$APK" | sed 's#^#apk_host_sha256: #'
    echo "apk_guest_sha256: $guest_sha"
    echo "subject: $APP_PACKAGE.$APP_BUNDLE; message $MESSAGE; unit $UNIT; publisher $BROKER_PACKAGE.$BROKER_BUNDLE"
    sha256sum "$ACLS/ivi_warning_subscriber.textproto" "$ACLS/ivi_broker_object_policy.textproto" | sed 's#^#acl_sha256: #'
    echo "object_policy_guest_sha256: $(guest_sha256 "$policy")"
    printf '%s\n' "${POLICY_LINES[@]}"
  } > "$RUN_DIR/ivi-warning-app-identity.txt"
  log "identity in $RUN_DIR/ivi-warning-app-identity.txt"
}

start() {
  ivi_adb shell "svc power stayon true; input keyevent KEYCODE_WAKEUP" >/dev/null 2>&1 || true
  # -S: a real restart. Issue times restart with every run, so restart the app before each window.
  ivi_adb shell am start -S -W -n "$APP_PACKAGE/.MainActivity" 2>&1 | tail -4
  sleep "${START_SETTLE_S:-5}"
  ivi_adb shell "dumpsys window 2>/dev/null | grep -m1 mCurrentFocus" | tr -d '\r' || true
  ivi_adb logcat -d -s "$TAG" 2>/dev/null | tail -12 | tr -d '\r' || true
}

verify() {
  local rc=0 lines
  log "--- IVI identity"
  ivi_adb shell getprop ro.build.fingerprint | tr -d '\r'
  ivi_adb shell getenforce | tr -d '\r' | sed 's/^/selinux: /'
  log "--- package"
  ivi_adb shell pm path "$APP_PACKAGE" | tr -d '\r' | grep -q "$GUEST_DIR/" || { log "FAIL: $APP_PACKAGE not installed from $GUEST_DIR"; rc=1; }
  log "--- gateway on the IVI VM"
  [ -n "$(ivi_adb shell pidof sdv_gateway 2>/dev/null | tr -d '\r')" ] || { log "FAIL: sdv_gateway is not running"; rc=1; }
  # The app retries initComms every 5 s: wait up to VERIFY_WAIT_S for its success line.
  local end=$(( $(date +%s) + VERIFY_WAIT_S ))
  while :; do
    lines="$(ivi_adb logcat -d -s "$TAG" 2>/dev/null | tr -d '\r')"
    printf '%s\n' "$lines" | grep -q 'key=initComms' && break
    [ "$(date +%s)" -lt "$end" ] || break
    sleep 5
  done
  printf '%s\n' "$lines" | grep -E 'phase=(start|config|link)' | tail -10
  printf '%s\n' "$lines" | grep -q 'key=initComms' || { log "FAIL: the app's initComms did not succeed (gateway lookup; see SELinux mode and denials)"; rc=1; }
  if printf '%s\n' "$lines" | grep -q 'link=SUBSCRIBED'; then
    log "subscribed to $UNIT"
  else
    log "NOTE: not subscribed yet: the broker registers $UNIT once the S-CORE host's SOME/IP offer of 0x4df1 reaches the SDV Core VM"
  fi
  log "--- denials naming this app or the gateway (empty is the expected answer)"
  ivi_adb logcat -d 2>/dev/null | grep -i "avc: denied" | grep -iE "collisionwarning|ISdvGateway" | tail -5 | tr -d '\r'
  return "$rc"
}

pull() {
  local out="${1:-$RUN_DIR/$RECORD}" user
  mkdir -p "$(dirname "$out")"
  _ivi_root || return 1
  user="$(ivi_adb shell am get-current-user 2>/dev/null | tr -d '\r')"
  case "$user" in ''|*[!0-9]*) user=0 ;; esac
  ivi_adb exec-out "cat /data/user/$user/$APP_PACKAGE/files/$RECORD 2>/dev/null" > "$out" 2>/dev/null
  [ -s "$out" ] || { log "ERROR: no record file on the IVI VM (user $user)"; return 1; }
  head -c 1 "$out" | grep -q '{' || { log "ERROR: $out does not start with a JSON record"; return 1; }
  log "pulled $out ($(wc -l < "$out") lines)"
}

case "${1:-}" in
  check) check ;;
  stage) stage ;;
  unstage) unstage ;;
  build) build ;;
  install) install ;;
  start) start ;;
  verify) verify ;;
  pull) shift; pull "${1:-}" ;;
  *) echo "usage: $0 {check|stage|unstage|build|install|start|verify|pull [file]}" >&2; exit 2 ;;
esac
