#!/usr/bin/env bash
# B12 of INC-DRIVING-002: the incremental guest build on the guest host (de4sdv-aaos-build).
#
# On top of the kept AOSP tree of 2026-11-17 (its guests archived in
# phase10/aaos-build/archive-records/), never a rebuild from scratch:
#
#   preflight  read-only: the tree, both products' recorded variants, the kept images against B12's
#              own image records (image-records/; never the kit's stale state/images-*.sha256), the
#              disk, this branch's files, the bench's launch script, no build running
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
#   all        every step in this order; on a failure or a signal (HUP, INT, TERM) once boot has
#              begun, the guests are stopped. Run it detached with b12_launch.sh (setsid nohup), never
#              under systemd-run and never in an SSH foreground that a dropped connection ends.
#
# Rules it keeps (phase10/aaos-build BUILD-PLAN, the variant trap):
#   * a product is built only with its recorded variant (core eng, IVI userdebug); another variant
#     forces an installclean that deletes the images, so the script refuses before lunch;
#   * no installclean, no clean, no deletion of the AOSP tree, its out/ directory or the archive;
#     the only directory it replaces is the app's own staging directory in samples/;
#   * no VM start or stop, no gcloud, no push, no commit. It changes the SELinux mode only when
#     IVI_PERMISSIVE=1 is set, and records the mode either way. Under the default (Enforcing) a
#     failed Gateway lookup stops the run and prints the rerun command with IVI_PERMISSIVE=1 (the
#     owner allowed that fallback on 2026-11-18; its results are conditional on a permissive IVI);
#   * its own files go to $AB/b12-<date>/{logs,identity,work}, never into the kit's identity/ or logs/;
#     a B12_DIR, LOGS, IDENT or WORK inside them is refused (exit 2);
#   * every adb call is bounded (ADB_TIMEOUT_S), so a wedged adb fails the step instead of hanging.
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
# B12's own directory: never the 2026-11-17 kit's identity/ or logs/ (b12_launch.sh sets one per run).
: "${B12_DIR:=$AB/b12-$(date -u +%Y%m%d)}"
: "${LOGS:=$B12_DIR/logs}"
: "${IDENT:=$B12_DIR/identity}"
: "${WORK:=$B12_DIR/work}"
# B12's own image records (image-records/README is in ../README.md): the IVI images as they are since
# the first boot of 2026-11-17 rewrote super.img in place (91a4d73f...), and the 27 core images of the
# 2026-11-18 B11 build. The kit's state/images-*.sha256 are stale and are never read.
: "${IVI_IMAGE_RECORD:=$HERE/image-records/sdv_ivi_cf.sha256}"
: "${CORE_IMAGE_RECORD:=$HERE/image-records/sdv_core_cf.sha256}"
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
: "${ADB_TIMEOUT_S:=120}"                # one adb call; a wedged adb is a failure, not a hang
: "${CVD_STOP_TIMEOUT_S:=300}"
: "${VERIFY_WAIT_S:=60}"                 # how long verify waits for the app's initComms line
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

# Never into the 2026-11-17 kit's own folders: refuse B12_DIR, LOGS, IDENT or WORK at or under
# $AB/logs or $AB/identity (exit 2, before anything is created).
inside_kit_dirs() { # <path> -> 0 when it is $AB/logs, $AB/identity or below one of them
  local path kit
  path="$(realpath -m -- "$1")"
  for kit in "$AB/logs" "$AB/identity"; do
    kit="$(realpath -m -- "$kit")"
    case "$path/" in "$kit/"*) return 0 ;; esac
  done
  return 1
}
for _var in B12_DIR LOGS IDENT WORK; do
  if inside_kit_dirs "${!_var}"; then
    printf '%s [b12] ERROR: %s=%s is inside the 2026-11-17 kit'"'"'s logs/ or identity/ under %s; B12 writes only below its own B12_DIR (default %s)\n' \
      "$(date -u +%FT%T.%3NZ)" "$_var" "${!_var}" "$AB" "$AB/b12-<date>"
    exit 2
  fi
done
unset _var
mkdir -p "$LOGS" "$IDENT" "$WORK"

ts() { date -u +%FT%T.%3NZ; }
log() { printf '%s [b12] %s\n' "$(ts)" "$*"; }
die() { log "ERROR: $*"; exit 1; }
run() { log "+ $*"; local rc=0; "$@" || rc=$?; log "  rc=$rc"; return "$rc"; }
note() { printf '%s %s\n' "$(ts)" "$*" >> "$SUMMARY"; log "$*"; }
step_log() { exec > >(tee -a "$LOGS/b12-$1.log") 2>&1; log "=== step $1 (pid $$, host $(hostname), branch files $DA_ROOT)"; }
adb_t() { timeout "$ADB_TIMEOUT_S" "$ADB" "$@"; }
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
in_user_unit() { grep -qE 'user@[0-9]+\.service/.*\.service' "${B12_CGROUP_FILE:-/proc/self/cgroup}" 2>/dev/null; }

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
' "$1" || true
}

booted() { # <serial>
  adb_t connect "$1" >/dev/null 2>&1 || true
  [ "$(adb_t -s "$1" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]
}

# The images of <product out> against a B12 image record (names relative to the product directory).
check_image_record() { # <product out> <record> -> 0 when every listed image matches
  [ -s "$2" ] || { log "no B12 image record at $2"; return 1; }
  ( cd "$1" && sha256sum --quiet --strict -c "$2" )
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
  # B12's own image records, never the kit's state/images-*.sha256 (stale since the first boot of
  # 2026-11-17 rewrote the IVI super.img in place, and since the core build of 2026-11-18).
  check_image_record "$IVI_OUT" "$IVI_IMAGE_RECORD" \
    || die "the IVI images differ from the B12 record $IVI_IMAGE_RECORD (or it is missing): stop, do not build"
  note "$IVI_PRODUCT images equal the B12 record ($(wc -l < "$IVI_IMAGE_RECORD") images, $IVI_IMAGE_RECORD)"
  check_image_record "$CORE_OUT" "$CORE_IMAGE_RECORD" \
    || die "the core images differ from the B12 record $CORE_IMAGE_RECORD (or it is missing): stop, do not build"
  note "$CORE_PRODUCT images equal the B12 record ($(wc -l < "$CORE_IMAGE_RECORD") images, $CORE_IMAGE_RECORD)"
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
    core_image_identity
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
  note "core: rebuilt"
  core_image_identity
  note "core: the B12 core record no longer applies to the rebuilt images; the next preflight needs CORE_IMAGE_RECORD=$IDENT/b12-core-images.sha256"
}

# The core images this run boots, in the identity, and whether they are the recorded ones.
core_image_identity() {
  image_stat "$CORE_OUT" > "$IDENT/b12-core-images.stat"
  ( cd "$CORE_OUT" && sha256sum $(awk '{print $2}' "$CORE_IMAGE_RECORD" 2>/dev/null || echo super.img vbmeta.img) ) \
    > "$IDENT/b12-core-images.sha256" || die "cannot hash the core images"
  note "core: super.img $(awk '$2 ~ /super.img$/ {print $1}' "$IDENT/b12-core-images.sha256"), vbmeta.img $(awk '$2 ~ /vbmeta.img$/ {print $1}' "$IDENT/b12-core-images.sha256") ($IDENT/b12-core-images.sha256)"
  if check_image_record "$CORE_OUT" "$CORE_IMAGE_RECORD" >/dev/null 2>&1; then
    note "core: the images equal the B12 record (the operator's B11 build of 2026-11-18, $CORE_IMAGE_RECORD)"
  else
    note "core: the images differ from the B12 record $CORE_IMAGE_RECORD"
  fi
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
  check_image_record "$IVI_OUT" "$IVI_IMAGE_RECORD" || die "the IVI images no longer equal the B12 record after the module build"
  note "ivi: images unchanged by the module build (stat and the B12 record)"
  local jar java="$AOSP_TOP/prebuilts/jdk/jdk21/linux-x86/bin/java"
  jar="$(find "$AOSP_TOP/out/soong/.intermediates/system/software_defined_vehicle/samples/de4sdv_collision_warning/app/De4sdvCollisionWarningPresentationTests" \
    -name 'De4sdvCollisionWarningPresentationTests.jar' -path '*combined*' 2>/dev/null | head -1 || true)"
  if [ -n "$jar" ] && [ -x "$java" ]; then
    run "$java" -cp "$jar" org.junit.runner.JUnitCore \
      org.de4sdv.collisionwarning.WarningRequestReducerTest org.de4sdv.collisionwarning.WarningRecordTest \
      org.de4sdv.collisionwarning.RecordWriterTest \
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
    ADB_TIMEOUT_S="$ADB_TIMEOUT_S" RUN_DIR="$WORK/app" bash "$APP_STAGE" install || die "app install failed"
  local identity="$WORK/app/ivi-warning-app-identity.txt" host_sha guest_sha
  [ -s "$identity" ] || die "the app install wrote no identity ($identity)"
  cp -f "$identity" "$IDENT/" || die "cannot copy the app identity into $IDENT"
  host_sha="$(sed -n 's/^apk_host_sha256: \([0-9a-f]\{64\}\) .*/\1/p' "$identity")"
  guest_sha="$(sed -n 's/^apk_guest_sha256: \([0-9a-f]\{64\}\)$/\1/p' "$identity")"
  [ -n "$host_sha" ] && [ "$guest_sha" = "$host_sha" ] \
    || die "the APK on the IVI VM (${guest_sha:-none}) is not the one built (${host_sha:-none})"
  note "install: apk sha256 $host_sha on the host and on the IVI VM"
  { grep -E '^object_policy_' "$identity" || true; } | while IFS= read -r line; do note "install: $line"; done
}

verify() {
  step_log verify
  booted "$CORE_ADB" || die "the SDV Core VM is not booted"
  booted "$IVI_ADB" || die "the IVI VM is not booted"
  adb_t -s "$CORE_ADB" root >/dev/null 2>&1 || true
  adb_t -s "$IVI_ADB" root >/dev/null 2>&1 || true
  sleep "${ROOT_SETTLE_S:-3}"
  adb_t connect "$CORE_ADB" >/dev/null 2>&1 || true
  adb_t connect "$IVI_ADB" >/dev/null 2>&1 || true
  local svc n
  for svc in 4dee 4df0 "${WARNING_SERVICE#0x}"; do
    n="$(adb_t -s "$CORE_ADB" shell "grep -c $svc /vendor/etc/someip/vsomeip_config.json" 2>/dev/null | tr -d '\r')" || true
    [ "${n:-0}" -ge 1 ] 2>/dev/null || die "the SDV Core VM's stack config lacks 0x$svc"
  done
  note "verify: the SDV Core VM's stack config carries 0x4dee, 0x4df0, $WARNING_SERVICE"
  # The broker APEX must name the unit too (the operator's boot check, boot_check.sh).
  n="$(adb_t -s "$CORE_ADB" shell "grep -c $UNIT /apex/com.android.sdv.someip/etc/vsidl_provider/someip-config.binpb" 2>/dev/null | tr -d '\r')" || true
  [ "${n:-0}" -ge 1 ] 2>/dev/null || die "the SDV Core VM's broker APEX (someip-config.binpb) does not name $UNIT"
  note "verify: the broker APEX's someip-config.binpb names $UNIT"
  if [ "$IVI_PERMISSIVE" = 1 ]; then
    adb_t -s "$IVI_ADB" shell setenforce 0 || die "setenforce 0 on the IVI VM failed"
    [ "$(adb_t -s "$IVI_ADB" shell getenforce | tr -d '\r')" = Permissive ] || die "IVI_PERMISSIVE=1, but the IVI VM's getenforce does not read Permissive"
    note "verify: IVI_PERMISSIVE=1: the IVI VM was set permissive (the owner's fallback of 2026-11-18): every result of this run is conditional on a permissive IVI"
  fi
  local core_mode ivi_mode
  core_mode="$(adb_t -s "$CORE_ADB" shell getenforce | tr -d '\r')" || true
  ivi_mode="$(adb_t -s "$IVI_ADB" shell getenforce | tr -d '\r')" || true
  note "verify: SELinux core ${core_mode:-unknown}, IVI ${ivi_mode:-unknown} (getenforce at run time)"
  run env ADB="$ADB" IVI_ADB="$IVI_ADB" ADB_TIMEOUT_S="$ADB_TIMEOUT_S" RUN_DIR="$WORK/app" bash "$APP_STAGE" start || true
  local rc=0
  env ADB="$ADB" IVI_ADB="$IVI_ADB" ADB_TIMEOUT_S="$ADB_TIMEOUT_S" VERIFY_WAIT_S="$VERIFY_WAIT_S" RUN_DIR="$WORK/app" \
    bash "$APP_STAGE" verify > "$WORK/app-verify.out" 2>&1 || rc=$?
  cat "$WORK/app-verify.out"
  adb_t -s "$IVI_ADB" logcat -d -s DE4SDV_COLLISION_WARNING 2>/dev/null | tr -d '\r' > "$IDENT/b12-app-logcat.txt" || true
  if [ "$rc" != 0 ]; then
    if [ "$ivi_mode" = Enforcing ] && grep -q 'initComms did not succeed' "$WORK/app-verify.out"; then
      note "verify: the app's Gateway lookup (initComms) failed with the IVI VM Enforcing; B12 never sets permissive on its own"
      note "verify: the owner allowed a permissive IVI as the fallback (2026-11-18); every result of that rerun is conditional on a permissive IVI"
      note "verify: the rerun command: $(rerun_cmd)"
      die "the Gateway lookup failed under SELinux Enforcing on the IVI VM; rerun with IVI_PERMISSIVE=1 (the command above)"
    fi
    die "the app is not up on the gateway (see the lines above; SELinux IVI ${ivi_mode:-unknown})"
  fi
  note "verify: app up (SELinux IVI ${ivi_mode:-unknown}); its lines in $IDENT/b12-app-logcat.txt"
}

# The command that reruns with a permissive IVI: the caller's own (B12_RERUN_CMD; b12_launch.sh
# passes one), else `all` again for an `all` run, else `verify` again on the same guests.
B12_MODE=step
rerun_cmd() {
  if [ -n "${B12_RERUN_CMD:-}" ]; then printf '%s' "$B12_RERUN_CMD"
  elif [ "$B12_MODE" = all ]; then
    printf 'cd %q && IVI_PERMISSIVE=1 GUESTS=fresh B12_DIR=%q ./build_guests_incremental.sh all' "$HERE" "$B12_DIR-permissive"
  else
    printf 'cd %q && IVI_PERMISSIVE=1 B12_DIR=%q ./build_guests_incremental.sh verify' "$HERE" "$B12_DIR"
  fi
}

stop_guests() {
  step_log stop
  local inst g c; c="$(cvd_bin)"
  [ -n "$c" ] || die "no cvd binary: cannot stop the guests; do not stop the host"
  for inst in 2 3; do
    g="$(group_for_instance "$inst")"
    if [ -n "$g" ]; then run timeout "$CVD_STOP_TIMEOUT_S" "$c" --group_name="$g" stop || log "WARNING: cvd stop $g returned non-zero"
    else log "instance $inst: no group"; fi
  done
  sleep "${STOP_SETTLE_S:-5}"
  timeout 60 "$c" fleet 2>&1 | grep -E '"(group_name|instance_name|status)"' || true
  [ "$(crosvm_count)" = 0 ] || die "crosvm processes left after cvd stop: do not stop the host"
  note "stop: both groups stopped, no crosvm left (disks and provisioning kept)"
}

# ------------------------------------------------------------------ all, and its failure path

STEP_PID=
# Each step runs as a child that the shell waits for with the wait builtin, so a signal is handled
# at once (a foreground child would defer the trap until the step ends).
run_step() { # <function>
  ( "$1" ) &
  STEP_PID=$!
  local rc=0
  wait "$STEP_PID" || rc=$?
  STEP_PID=
  return "$rc"
}

kill_tree() { # <pid> <signal>: the pid and every descendant, children first
  local child
  for child in $(pgrep -P "$1" 2>/dev/null); do kill_tree "$child" "$2"; done
  kill -"$2" "$1" 2>/dev/null || true
}

on_signal() { # <exit code> <name>
  trap '' HUP INT TERM
  log "signal $2: ending the run"
  if [ -n "$STEP_PID" ]; then
    kill_tree "$STEP_PID" TERM
    wait "$STEP_PID" 2>/dev/null || true
    STEP_PID=
  fi
  exit "$1"
}

# Reached on every exit of all except its success (all clears the trap): stop the guests once boot
# has begun, whatever the exit status.
on_exit() {
  local rc=$?
  trap - EXIT
  trap '' HUP INT TERM
  [ "$rc" != 0 ] || rc=1
  if [ -f "$BOOTED_MARK" ] && [ "$KEEP_GUESTS_ON_FAILURE" != 1 ]; then
    log "the run ends without passing (rc $rc) after boot began: stopping the guests so the host can be stopped safely"
    ( stop_guests ) || log "ERROR: the guest stop failed: do not stop the host before the guests are stopped"
  elif [ -f "$BOOTED_MARK" ]; then
    log "KEEP_GUESTS_ON_FAILURE=1: the guests stay up for a diagnosis; stop them (./build_guests_incremental.sh stop) before the host"
  fi
  log "B12 FAILED (rc $rc; $SUMMARY)"
  exit "$rc"
}

all() {
  B12_MODE=all
  rm -f -- "$BOOTED_MARK"
  trap 'on_signal 129 HUP' HUP
  trap 'on_signal 130 INT' INT
  trap 'on_signal 143 TERM' TERM
  trap on_exit EXIT
  run_step preflight || exit 1
  run_step core || exit 1
  run_step ivi || exit 1
  run_step boot || exit 1
  run_step install_app || exit 1
  run_step verify || exit 1
  run_step stop_guests || exit 1
  trap - EXIT HUP INT TERM
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
