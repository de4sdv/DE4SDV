#!/usr/bin/env bash
# The observer build must use the build variant the IVI product was last built with.
#
# A module build under another variant makes the build system run an installclean of the
# whole product directory first ("Build configuration changed: sdv_ivi_cf-userdebug ->
# sdv_ivi_cf-eng, forcing installclean"). That deletes the IVI images; a guest already
# running from them keeps running on its open files and dies at its next restart. Seen
# on the bench VM on 2026-11-10 with an IVI image built as userdebug.
#
# Runs `stage_ivi_observer.sh build` against a stand-in AOSP tree whose `lunch` and `m`
# record their arguments. No AOSP, no guest, no network.
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SLICE="$(cd -- "$HERE/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
FAILED=0

make_tree() { # <variant the product was last built with | none>
  rm -rf "$T/aosp" "$T/run"
  mkdir -p "$T/aosp/build" "$T/run" \
    "$T/aosp/system/software_defined_vehicle/samples" \
    "$T/aosp/system/software_defined_vehicle/sdv_gateway/libsdvgatewayclient_java/src/google/sdv/gateway/client" \
    "$T/aosp/out/target/product/sdv_ivi_cf"
  cat > "$T/aosp/build/envsetup.sh" <<'EOS'
lunch() { echo "lunch $*" >> "$CALLS"; }
m() { echo "m $*" >> "$CALLS"; mkdir -p "$(dirname "$OBSERVER_APK")"; echo apk > "$OBSERVER_APK"; }
EOS
  if [ "$1" != none ]; then
    echo "PREVIOUS_BUILD_CONFIG := sdv_ivi_cf-$1" > "$T/aosp/out/target/product/sdv_ivi_cf/previous_build_config.mk"
  fi
  : > "$T/calls"
}

run_build() { # [NAME=value ...]
  env -u IVI_VARIANT -u VARIANT AOSP_TOP="$T/aosp" RUN_DIR="$T/run" CALLS="$T/calls" "$@" \
    "$SLICE/scripts/stage_ivi_observer.sh" build > "$T/out" 2>&1
}

expect() { # <case> <condition as a command...>
  local name="$1"; shift
  if "$@"; then echo "ok    $name"; else echo "FAIL  $name"; sed 's/^/      /' "$T/out" | tail -6; sed 's/^/      call: /' "$T/calls"; FAILED=1; fi
}

# 1. The product was last built as userdebug and nothing is set: build as userdebug.
make_tree userdebug; run_build; RC=$?
expect "userdebug product, no setting: exit 0" [ "$RC" = 0 ]
expect "userdebug product, no setting: lunch sdv_ivi_cf-cp2a-userdebug" grep -qx "lunch sdv_ivi_cf-cp2a-userdebug" "$T/calls"
expect "userdebug product, no setting: m ran" grep -q "^m De4sdvDrivingStateObserver" "$T/calls"

# 2. Another variant asked for explicitly: refuse before lunch and m, and say why.
make_tree userdebug; run_build IVI_VARIANT=eng; RC=$?
expect "userdebug product, IVI_VARIANT=eng: refused" [ "$RC" != 0 ]
expect "userdebug product, IVI_VARIANT=eng: no lunch, no m" [ ! -s "$T/calls" ]
expect "userdebug product, IVI_VARIANT=eng: names the installclean" grep -q "installclean" "$T/out"
expect "userdebug product, IVI_VARIANT=eng: names both variants" grep -q "sdv_ivi_cf-userdebug.*sdv_ivi_cf-eng" "$T/out"

# 3. The product was last built as eng: build as eng.
make_tree eng; run_build; RC=$?
expect "eng product: exit 0" [ "$RC" = 0 ]
expect "eng product: lunch sdv_ivi_cf-cp2a-eng" grep -qx "lunch sdv_ivi_cf-cp2a-eng" "$T/calls"

# 4. The product was never built: the bench's default variant.
make_tree none; run_build; RC=$?
expect "no earlier build: exit 0" [ "$RC" = 0 ]
expect "no earlier build: lunch sdv_ivi_cf-cp2a-eng" grep -qx "lunch sdv_ivi_cf-cp2a-eng" "$T/calls"

# 5. The matching variant asked for explicitly is accepted.
make_tree userdebug; run_build IVI_VARIANT=userdebug; RC=$?
expect "userdebug product, IVI_VARIANT=userdebug: exit 0" [ "$RC" = 0 ]

[ "$FAILED" = 0 ] && echo "BUILD VARIANT CHECK PASSED (5 cases)" || { echo "BUILD VARIANT CHECK FAILED"; exit 1; }
