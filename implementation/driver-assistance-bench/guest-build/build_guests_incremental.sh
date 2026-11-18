#!/usr/bin/env bash
# B12 of INC-DRIVING-002: the incremental guest build on the guest host (de4sdv-aaos-build).
#
# On top of the kept AOSP tree of 2026-11-17 (its guests archived in
# phase10/aaos-build/archive-records/), never a rebuild from scratch:
#
#   preflight  read-only: the tree, both products' recorded variants, the kept images, the disk,
#              this branch's files, the bench's launch script, no build running
#   core       the SDV Core side of B11 (../ivi-warning/): detect it, and only when it is missing
#              stage it with the bench's staging tool (validate: stage + the catalog build G1b) and
#              rebuild the core image with a plain incremental m (sdv_core_cf-cp2a-eng)
#   ivi        the IVI side: stage and build the warning presentation (../ivi-warning-app/) as a
#              module under sdv_ivi_cf-cp2a-userdebug, run its JVM tests, prove the IVI images unchanged
#   boot       create both guests with the bench's launch_two_vms.sh up (foreground only)
#   install    the app's ACLs and APK on the IVI VM, reboot it, PackageManager check
#   verify     start the app; the app is installed, initComms through the gateway succeeded,
#              the SDV Core VM carries 0x4df1 beside 0x4dee and 0x4df0
#   stop       cvd stop both groups (disks kept), no crosvm left: before any host stop
#   all        every step in this order; on a failure after boot the guests are stopped
#
# Rules it keeps (phase10/aaos-build BUILD-PLAN, the variant trap):
#   * a product is built only with its recorded variant (core eng, IVI userdebug); another variant
#     forces an installclean that deletes the images, so the script refuses before lunch;
#   * no installclean, no clean, no deletion of the AOSP tree, its out/ directory or the archive;
#     the only directory it replaces is the app's own staging directory in samples/;
#   * no VM start or stop, no gcloud, no push, no commit. It changes the SELinux mode only when
#     IVI_PERMISSIVE=1 is set, and records the mode either way.
#
# Idempotent: every step detects what is already there. The SDV Core detection, exactly:
#   tree  = the stack config the bench's render makes from ../ivi-warning/interop/vsomeip_config.json
#           with SCORE_SOMEIP_PEER is byte-equal (cmp) to the tree's vsomeip_config.json, the
#           catalog's proto and mapping are byte-equal to ../ivi-warning's, the broker ACL names the
#           unit and broker.vsidl names the message;
#   image = the tree check holds, the stack config installed in the core product's out directory
#           is byte-equal to the same render, and super.img and vbmeta.img are newer than it.
# Both hold: the core step builds nothing.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DA_ROOT="$(cd -- "$HERE/.." && pwd)"

: "${AB:=$HOME/aaos-build}"
: "${LOGS:=$AB/logs}"
: "${IDENT:=$AB/identity}"
: "${STATE:=$AB/state}"
: "${WORK:=$AB/b12}"
: "${AOSP_TOP:=$HOME/aosp}"
: "${DE4SDV_ROOT:=$HOME/de4sdv-e8fa324a}"   # the bench scripts of the 2026-11-17 rebuild (launch_two_vms.sh)
: "${CORE_PRODUCT:=sdv_core_cf}"
: "${IVI_PRODUCT:=sdv_ivi_cf}"
: "${RELEASE:=cp2a}"
: "${RECORDED_CORE_VARIANT:=eng}"        # phase10/aaos-build lib_common.sh CORE_VARIANT
: "${RECORDED_IVI_VARIANT:=userdebug}"   # phase10/aaos-build lib_common.sh IVI_VARIANT_PLAN
: "${SCORE_SOMEIP_PEER:=192.168.98.1}"   # the S-CORE host on the VXLAN segment (the model's address)
: "${BUILD_MIN_FREE_GB:=60}"
: "${UP_TIMEOUT_S:=1800}"
: "${GUESTS:=}"                          # fresh | reuse, when guest groups already exist (see boot)
: "${IVI_PERMISSIVE:=0}"
: "${KEEP_GUESTS_ON_FAILURE:=0}"
export AOSP_TOP
export PATH="$HOME/bin:$PATH"
AOSP_HOST_OUT="$AOSP_TOP/out/host/linux-x86"
ADB="${ADB:-$AOSP_HOST_OUT/bin/adb}"
CVD="${CVD:-}"
CORE_ADB="${CORE_ADB:-0.0.0.0:6521}"   # base instance 2 (score-broker-path-bench bench_env.sh)
IVI_ADB="${IVI_ADB:-0.0.0.0:6522}"     # base instance 3
LAUNCH="$DE4SDV_ROOT/implementation/score-broker-path-bench/scripts/launch_two_vms.sh"
CORE_STAGE="$DA_ROOT/ivi-warning/scripts/stage_sdv_core_interop.sh"
APP_STAGE="$DA_ROOT/ivi-warning-app/scripts/stage_ivi_warning_app.sh"
IDS="$DA_ROOT/interfaces/service_ids.json"
CORE_OUT="$AOSP_TOP/out/target/product/$CORE_PRODUCT"
IVI_OUT="$AOSP_TOP/out/target/product/$IVI_PRODUCT"
IMAGES="super.img vbmeta.img boot.img init_boot.img vendor_boot.img"
SAMPLES="$AOSP_TOP/system/software_defined_vehicle/samples"
STACK_CONFIG="$AOSP_TOP/system/software_defined_vehicle/some_ip/vsomeip_stack/vsomeip_config.json"
CATALOG_DIR="$SAMPLES/some_ip/catalog/de4sdv_driver_assistance"
BROKER_VSIDL="$SAMPLES/some_ip/catalog/agent/broker.vsidl"
BROKER_ACL="$SAMPLES/some_ip/config/broker_apex/someip_acl.textproto"
# The stack config as the core product installs it (the path the guest reads: /vendor/etc/someip/).
: "${CORE_INSTALLED_STACK_CONFIG:=$CORE_OUT/vendor/etc/someip/vsomeip_config.json}"
SUMMARY="$IDENT/b12-summary.txt"
BOOTED_MARK="$WORK/guests-booted-by-this-run"

mkdir -p "$LOGS" "$IDENT" "$STATE" "$WORK"

ts() { date -u +%FT%T.%3NZ; }
log() { printf '%s [b12] %s\n' "$(ts)" "$*"; }
die() { log "ERROR: $*"; exit 1; }
run() { log "+ $*"; local rc=0; "$@" || rc=$?; log "  rc=$rc"; return "$rc"; }
note() { printf '%s %s\n' "$(ts)" "$*" >> "$SUMMARY"; log "$*"; }
step_log() { exec > >(tee -a "$LOGS/b12-$1.log") 2>&1; log "=== step $1 (pid $$, host $(hostname), branch files $DA_ROOT)"; }
ids() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2], {}, {'d': d}))" "$IDS" "$1"; }

UNIT="$(ids "d['icd']['data_tunnel']['service_unit']")"
MESSAGE="$(ids "d['icd']['data_tunnel']['message']")"
WARNING_SERVICE="$(ids "d['icd']['someip_warning_request']['service_id']")"   # 0x4df1

# The variant a product was last built with ("" when never built).
last_variant() { # <product>
  local v
  v="$(sed -n 's/^PREVIOUS_BUILD_CONFIG := *//p' "$AOSP_TOP/out/target/product/$1/previous_build_config.mk" 2>/dev/null | head -1)"
  v="${v#"$1"-}"
  printf '%s' "${v##*-}"
}

# The variant trap: refuse a build of <product> unless its last build used <recorded variant>.
guard_variant() { # <product> <recorded variant>
  local last; last="$(last_variant "$1")"
  [ -n "$last" ] || die "$1 has no previous_build_config.mk under $AOSP_TOP/out: not the kept tree"
  [ "$last" = "$2" ] || die "$1 was last built as '$last', the recorded variant is '$2': a build would installclean and delete its images"
  log "variant guard ok: ${1}-${RELEASE}-$2"
}

# One AOSP build of <product> under its recorded variant, in a subshell; the log is live.
lunch_m() { # <product> <variant> <log> [m args...]
  local product="$1" variant="$2" mlog="$3"; shift 3
  guard_variant "$product" "$variant"
  log "+ (lunch ${product}-${RELEASE}-${variant}; m $*) > $mlog"
  local rc=0
  (
    set +eu
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${product}-${RELEASE}-${variant}" >/dev/null || exit 1
    m "$@"
  ) > "$mlog" 2>&1 || rc=$?
  tail -n 5 "$mlog" || true
  log "  rc=$rc (m $* for ${product}-${RELEASE}-${variant})"
  return "$rc"
}

images_present() { # <product out>
  local img
  for img in $IMAGES; do [ -s "$1/$img" ] || { log "missing $1/$img"; return 1; }; done
}

image_stat() { # <product out>: name size mtime per image, the cheap identity of a build's images
  local img
  for img in $IMAGES; do stat -c '%n %s %Y' "$1/$img"; done
}

crosvm_count() { pgrep -c -x crosvm 2>/dev/null || true; }
in_user_unit() { grep -qE 'user@[0-9]+\.service/.*\.service' /proc/self/cgroup 2>/dev/null; }

cvd_bin() {
  if [ -n "$CVD" ]; then printf '%s' "$CVD"
  elif [ -x "$AOSP_HOST_OUT/bin/cvd" ]; then printf '%s' "$AOSP_HOST_OUT/bin/cvd"
  else command -v cvd || true; fi
}

group_for_instance() { # <base instance number>: the cvd group holding it, or nothing
  "$(cvd_bin)" fleet 2>/dev/null | python3 -c '
import json, sys
raw = sys.stdin.read(); s = raw.find("{")
if s < 0: raise SystemExit(0)
try: fleet = json.loads(raw[s:])
except ValueError: raise SystemExit(0)
for g in fleet.get("groups", []):
    for i in g.get("instances", []):
        if str(i.get("instance_name")) == sys.argv[1]:
            print(g.get("group_name", "")); raise SystemExit(0)
' "$1"
}

booted() { # <serial>
  "$ADB" connect "$1" >/dev/null 2>&1 || true
  [ "$("$ADB" -s "$1" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]
}

wait_booted() { # <serial> <seconds>
  local end=$(( $(date +%s) + $2 ))
  while [ "$(date +%s)" -lt "$end" ]; do booted "$1" && return 0; sleep 5; done
  return 1
}

# ------------------------------------------------------------------ detection of B11 on the core

render_expected() { # -> $WORK/vsomeip_config.expected.json
  SCORE_SOMEIP_PEER="$SCORE_SOMEIP_PEER" AOSP_TOP="$AOSP_TOP" RUN_DIR="$WORK/core-interop" \
    bash "$CORE_STAGE" render "$WORK/vsomeip_config.expected.json" >/dev/null
}

core_tree_has_b11() {
  local ok=0
  render_expected || { log "detect: the render refused"; return 1; }
  cmp -s "$WORK/vsomeip_config.expected.json" "$STACK_CONFIG" || { log "detect: tree stack config differs from the render"; ok=1; }
  cmp -s "$DA_ROOT/ivi-warning/contract/de4sdv_driving_collision_warning_request.proto" \
    "$CATALOG_DIR/de4sdv_driving_collision_warning_request.proto" || { log "detect: catalog proto missing or different"; ok=1; }
  cmp -s "$DA_ROOT/ivi-warning/interop/de4sdv_driving_collision_warning_request.vsidl" \
    "$CATALOG_DIR/de4sdv_driving_collision_warning_request_someip.vsidl" || { log "detect: catalog mapping missing or different"; ok=1; }
  grep -q "topic: \"$UNIT\"" "$BROKER_ACL" 2>/dev/null || { log "detect: broker ACL lacks $UNIT"; ok=1; }
  grep -q "message: \"$MESSAGE\"" "$BROKER_VSIDL" 2>/dev/null || { log "detect: broker.vsidl lacks $MESSAGE"; ok=1; }
  return "$ok"
}

core_image_has_b11() {
  core_tree_has_b11 || return 1
  [ -f "$CORE_INSTALLED_STACK_CONFIG" ] || { log "detect: no installed stack config at $CORE_INSTALLED_STACK_CONFIG"; return 1; }
  cmp -s "$WORK/vsomeip_config.expected.json" "$CORE_INSTALLED_STACK_CONFIG" || { log "detect: installed stack config differs from the render"; return 1; }
  local img
  for img in super.img vbmeta.img; do
    [ "$CORE_OUT/$img" -nt "$CORE_INSTALLED_STACK_CONFIG" ] || { log "detect: $img is not newer than the installed stack config"; return 1; }
  done
}

# ------------------------------------------------------------------ steps

preflight() {
  step_log preflight
  : > "$SUMMARY"
  note "b12 preflight; branch files sha256 of the scripts: $(sha256sum "$0" "$CORE_STAGE" "$APP_STAGE" | awk '{print substr($1,1,16)}' | tr '\n' ' ')"
  [ -f "$AOSP_TOP/build/envsetup.sh" ] || die "no AOSP tree at $AOSP_TOP"
  [ -x "$ADB" ] || die "no adb at $ADB (the tree's host tools)"
  [ -f "$LAUNCH" ] || die "no launch script at $LAUNCH (set DE4SDV_ROOT to the bench scripts of the rebuild)"
  [ -n "$(cvd_bin)" ] || die "no cvd binary"
  local p v
  for p in "$CORE_PRODUCT:$RECORDED_CORE_VARIANT" "$IVI_PRODUCT:$RECORDED_IVI_VARIANT"; do
    v="$(last_variant "${p%%:*}")"
    [ "$v" = "${p##*:}" ] || die "${p%%:*} last built as '${v:-never}', recorded '${p##*:}'"
    images_present "$AOSP_TOP/out/target/product/${p%%:*}" || die "${p%%:*}: kept images missing (restore from the archive, do not rebuild)"
    note "${p%%:*}: last built ${p##*:}, images present"
  done
  # The recipe's digests of the archived IVI images, when they are there: the module build must start from them.
  if [ -f "$STATE/images-$IVI_PRODUCT.sha256" ]; then
    sha256sum --quiet -c "$STATE/images-$IVI_PRODUCT.sha256" || die "the IVI images differ from the recipe's recorded digests"
    note "$IVI_PRODUCT images equal the recorded digests ($STATE/images-$IVI_PRODUCT.sha256)"
  fi
  local free; free="$(df -B1G --output=avail / | tail -1 | tr -d ' ')"
  [ "$free" -ge "$BUILD_MIN_FREE_GB" ] || die "disk free ${free} G < ${BUILD_MIN_FREE_GB} G"
  note "disk free ${free} G"
  if pgrep -u "$(id -u)" -f 'soong_ui|soong_build|bin/ninja' >/dev/null 2>&1; then die "an AOSP build is running (the other operator?)"; fi
  run bash "$CORE_STAGE" check || true   # its NOTEs name what is not staged yet; never fatal here
  run bash "$APP_STAGE" check || die "the app's artifacts disagree"
  note "guests: crosvm processes $(crosvm_count); instance 2 group '$(group_for_instance 2)'; instance 3 group '$(group_for_instance 3)'"
}

core() {
  step_log core
  if core_image_has_b11; then
    note "core: tree and image already carry B11 ($WARNING_SERVICE, unit $UNIT): nothing to build"
    return 0
  fi
  [ "$(crosvm_count)" = 0 ] || die "guests are running; stop them (cvd stop) before the core image is rebuilt under them"
  guard_variant "$CORE_PRODUCT" "$RECORDED_CORE_VARIANT"
  if core_tree_has_b11; then
    note "core: the tree carries B11, the image does not: incremental m"
  else
    note "core: staging B11 into the tree (stage + G1b)"
    run env AOSP_TOP="$AOSP_TOP" SCORE_SOMEIP_PEER="$SCORE_SOMEIP_PEER" VARIANT="$RECORDED_CORE_VARIANT" \
      RUN_DIR="$WORK/core-interop" bash "$CORE_STAGE" validate || die "B11 stage or G1b failed (logs in $WORK/core-interop)"
    core_tree_has_b11 || die "staged, but the tree detection still fails"
  fi
  # A plain m: never the INC-DRIVING-001 script's build, which re-stages its own stack config
  # without 0x4df1 (../ivi-warning/README.md, "In the guest rebuild").
  lunch_m "$CORE_PRODUCT" "$RECORDED_CORE_VARIANT" "$LOGS/b12-core.m.log" \
    || die "core image build failed (log $LOGS/b12-core.m.log; the failing step follows the first FAILED: in out/siso_output)"
  images_present "$CORE_OUT" || die "core images missing after the build"
  core_image_has_b11 || die "core built, but the image detection fails"
  image_stat "$CORE_OUT" > "$IDENT/b12-core-images.stat"
  sha256sum "$CORE_OUT/super.img" "$CORE_OUT/vbmeta.img" > "$IDENT/b12-core-images.sha256"
  note "core: rebuilt; images in $IDENT/b12-core-images.sha256"
}

ivi() {
  step_log ivi
  guard_variant "$IVI_PRODUCT" "$RECORDED_IVI_VARIANT"
  images_present "$IVI_OUT" || die "IVI images missing"
  image_stat "$IVI_OUT" > "$WORK/ivi-images.before"
  run env AOSP_TOP="$AOSP_TOP" RECORDED_IVI_VARIANT="$RECORDED_IVI_VARIANT" RUN_DIR="$WORK/app" \
    bash "$APP_STAGE" build || die "app build failed (log $WORK/app/warning-app-build.log)"
  image_stat "$IVI_OUT" > "$WORK/ivi-images.after"
  cmp -s "$WORK/ivi-images.before" "$WORK/ivi-images.after" || die "the IVI images changed during the module build (installclean?)"
  note "ivi: images unchanged by the module build"
  local jar java="$AOSP_TOP/prebuilts/jdk/jdk21/linux-x86/bin/java"
  jar="$(find "$AOSP_TOP/out/soong/.intermediates/system/software_defined_vehicle/samples/de4sdv_collision_warning/app/De4sdvCollisionWarningPresentationTests" \
    -name 'De4sdvCollisionWarningPresentationTests.jar' -path '*combined*' 2>/dev/null | head -1 || true)"
  if [ -n "$jar" ] && [ -x "$java" ]; then
    run "$java" -cp "$jar" org.junit.runner.JUnitCore \
      org.de4sdv.collisionwarning.WarningRequestReducerTest org.de4sdv.collisionwarning.WarningRecordTest \
      org.de4sdv.collisionwarning.PresentationTimelineTest org.de4sdv.collisionwarning.WarningToneAndScreenTextTest \
      > "$IDENT/b12-app-jvm-tests.txt" 2>&1 || die "the app's JVM tests failed in the tree ($IDENT/b12-app-jvm-tests.txt)"
    note "ivi: JVM tests in the tree: $(grep -E '^OK|^Tests run' "$IDENT/b12-app-jvm-tests.txt" | tail -1)"
  else
    note "ivi: WARNING: test jar or the tree's JDK not found; the JVM tests ran only on the development host"
  fi
  note "ivi: APK $(sha256sum "$IVI_OUT/vendor/priv-app/De4sdvCollisionWarningPresentation/De4sdvCollisionWarningPresentation.apk" | cut -d' ' -f1)"
}

boot() {
  step_log boot
  in_user_unit && die "running inside a systemd unit: its cgroup takes the guests down at the end; run in the SSH foreground"
  local g2 g3
  g2="$(group_for_instance 2)"; g3="$(group_for_instance 3)"
  if [ -n "$g2$g3" ]; then
    case "$GUESTS" in
      fresh)
        # Removes the guest groups and their runtime files only; the images in out/ stay.
        run env AOSP_TOP="$AOSP_TOP" bash "$LAUNCH" down || die "launch_two_vms.sh down failed" ;;
      reuse)
        booted "$CORE_ADB" && booted "$IVI_ADB" || die "GUESTS=reuse, but the guests are not both booted"
        date -u +%FT%TZ > "$BOOTED_MARK"
        note "boot: reusing the running guests ($g2, $g3)"; return 0 ;;
      *) die "guest groups exist (instance 2 '$g2', instance 3 '$g3'): set GUESTS=fresh (remove and create) or GUESTS=reuse (both already booted on the current images)" ;;
    esac
  fi
  date -u +%FT%TZ > "$BOOTED_MARK"
  log "+ timeout $UP_TIMEOUT_S launch_two_vms.sh up"
  AOSP_TOP="$AOSP_TOP" timeout "$UP_TIMEOUT_S" bash "$LAUNCH" up || die "launch_two_vms.sh up failed"
  wait_booted "$CORE_ADB" 900 || die "the SDV Core VM did not boot"
  wait_booted "$IVI_ADB" 900 || die "the IVI VM did not boot"
  note "boot: both guests booted (core $CORE_ADB, IVI $IVI_ADB)"
}

install_app() {
  step_log install
  booted "$IVI_ADB" || die "the IVI VM is not booted"
  run env AOSP_TOP="$AOSP_TOP" ADB="$ADB" IVI_ADB="$IVI_ADB" RECORDED_IVI_VARIANT="$RECORDED_IVI_VARIANT" \
    RUN_DIR="$WORK/app" bash "$APP_STAGE" install || die "app install failed"
  cp -f "$WORK/app/ivi-warning-app-identity.txt" "$IDENT/" 2>/dev/null || true
  note "install: $(grep -E '^apk_guest_sha256' "$WORK/app/ivi-warning-app-identity.txt" 2>/dev/null)"
}

verify() {
  step_log verify
  booted "$CORE_ADB" || die "the SDV Core VM is not booted"
  booted "$IVI_ADB" || die "the IVI VM is not booted"
  "$ADB" -s "$CORE_ADB" root >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" root >/dev/null 2>&1 || true
  sleep 3
  "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  local svc n
  for svc in 4dee 4df0 "${WARNING_SERVICE#0x}"; do
    n="$("$ADB" -s "$CORE_ADB" shell "grep -c $svc /vendor/etc/someip/vsomeip_config.json" 2>/dev/null | tr -d '\r')"
    [ "${n:-0}" -ge 1 ] 2>/dev/null || die "the SDV Core VM's stack config lacks 0x$svc"
  done
  note "verify: the SDV Core VM's stack config carries 0x4dee, 0x4df0, $WARNING_SERVICE"
  if [ "$IVI_PERMISSIVE" = 1 ]; then
    "$ADB" -s "$IVI_ADB" shell setenforce 0
    note "verify: IVI_PERMISSIVE=1: the IVI VM was set permissive (a condition of every result on this boot)"
  fi
  note "verify: SELinux core $("$ADB" -s "$CORE_ADB" shell getenforce | tr -d '\r'), IVI $("$ADB" -s "$IVI_ADB" shell getenforce | tr -d '\r')"
  run env ADB="$ADB" IVI_ADB="$IVI_ADB" RUN_DIR="$WORK/app" bash "$APP_STAGE" start
  run env ADB="$ADB" IVI_ADB="$IVI_ADB" RUN_DIR="$WORK/app" bash "$APP_STAGE" verify \
    || die "the app is not up on the gateway (see the lines above; IVI_PERMISSIVE=1 is the earlier increments' bench condition)"
  "$ADB" -s "$IVI_ADB" logcat -d -s DE4SDV_COLLISION_WARNING 2>/dev/null | tr -d '\r' > "$IDENT/b12-app-logcat.txt" || true
  note "verify: app up; its lines in $IDENT/b12-app-logcat.txt"
}

stop_guests() {
  step_log stop
  local inst g c; c="$(cvd_bin)"
  for inst in 2 3; do
    g="$(group_for_instance "$inst")"
    if [ -n "$g" ]; then run "$c" --group_name="$g" stop || log "WARNING: cvd stop $g returned non-zero"
    else log "instance $inst: no group"; fi
  done
  sleep 5
  "$c" fleet 2>&1 | grep -E '"(group_name|instance_name|status)"' || true
  [ "$(crosvm_count)" = 0 ] || die "crosvm processes left after cvd stop: do not stop the host"
  note "stop: both groups stopped, no crosvm left (disks and provisioning kept)"
}

on_exit() {
  local rc=$?
  if [ "$rc" != 0 ] && [ -f "$BOOTED_MARK" ] && [ "$KEEP_GUESTS_ON_FAILURE" != 1 ]; then
    log "failure after boot (rc $rc): stopping the guests so the host can be stopped safely"
    ( stop_guests ) || true
  fi
  exit "$rc"
}

all() {
  rm -f -- "$BOOTED_MARK"
  trap on_exit EXIT
  ( preflight ) || exit 1
  ( core ) || exit 1
  ( ivi ) || exit 1
  ( boot ) || exit 1
  ( install_app ) || exit 1
  ( verify ) || exit 1
  ( stop_guests ) || exit 1
  trap - EXIT
  log "B12 PASSED ($SUMMARY)"
}

case "${1:-}" in
  preflight) preflight ;;
  core) core ;;
  ivi) ivi ;;
  boot) boot ;;
  install) install_app ;;
  verify) verify ;;
  stop) stop_guests ;;
  detect) step_log detect
          if core_image_has_b11; then echo "core: tree and image carry B11"
          elif core_tree_has_b11; then echo "core: tree carries B11, image does not"
          else echo "core: tree does not carry B11"; fi ;;
  all) all ;;
  *) echo "usage: $0 {preflight|core|ivi|boot|install|verify|stop|detect|all}" >&2; exit 2 ;;
esac
