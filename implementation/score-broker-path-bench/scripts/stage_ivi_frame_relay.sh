#!/usr/bin/env bash
# Stage the DE4SDV IVI frame relay and its identity package in the AOSP tree and build them
# (INC-MW-011 phase 10). The relay's Android.bp header states the destination: the android17-release
# tree of the bench, next to the other DE4SDV modules, in system/software_defined_vehicle/samples/.
#
#   stage_ivi_frame_relay.sh stage   copy both directories and build both modules
#   stage_ivi_frame_relay.sh build   build both modules only (assumes they are staged)
#   stage_ivi_frame_relay.sh remove  remove both staged directories (the undo)
#
# The identity package exists because AAOS SDV identity is PackageManager-based: the relay runs as
# `user system` (uid 1000) and claims the subject package de4sdv.ivi_frame_relay, so that package
# must be installed and resolve to uid 1000. Without it the SD agent rejects the registration with
# `passed_verification` and the relay exits 4 in a restart loop. See identity/AndroidManifest.xml.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"

SRC_RELAY="$DE4SDV_ROOT/implementation/score-reference-interop-bench/ivi-frame-relay"
SAMPLES="$AOSP_TOP/system/software_defined_vehicle/samples"
DST_RELAY="$SAMPLES/ivi_frame_relay"
DST_IDENTITY="$SAMPLES/ivi_frame_relay_identity"
RELAY_MODULE=de4sdv_ivi_frame_relay
IDENTITY_MODULE=de4sdv_ivi_frame_relay_identity

stage() {
  [ -d "$AOSP_TOP/system/software_defined_vehicle" ] || {
    log "ERROR: no SDV samples tree at $AOSP_TOP/system/software_defined_vehicle"; return 1; }
  [ -d "$SRC_RELAY" ] || { log "ERROR: $SRC_RELAY is missing"; return 1; }
  mkdir -p "$DST_RELAY" "$DST_IDENTITY"
  # The identity module is staged on its own; it must not be nested inside the relay module.
  rsync -a --delete --exclude identity/ "$SRC_RELAY/" "$DST_RELAY/" || return 1
  rsync -a --delete "$SRC_RELAY/identity/" "$DST_IDENTITY/" || return 1
  log "staged $RELAY_MODULE and $IDENTITY_MODULE in $SAMPLES"
  build
}

build() {
  [ -d "$AOSP_TOP/build" ] || { log "ERROR: no AOSP tree at $AOSP_TOP"; return 1; }
  local rc=0
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${IVI_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m "$RELAY_MODULE" "$IDENTITY_MODULE" || exit 1
  ) 2>&1 | tail -5
  [ "${PIPESTATUS[0]:-0}" = 0 ] || rc=1
  if [ "$rc" != 0 ]; then
    log "ERROR: the relay or identity module build failed"
    return 1
  fi
  local relay="$AOSP_TOP/out/target/product/$IVI_PRODUCT/system/bin/$RELAY_MODULE"
  local identity="$AOSP_TOP/out/target/product/$IVI_PRODUCT/system/app/$IDENTITY_MODULE/$IDENTITY_MODULE.apk"
  [ -f "$relay" ] || { log "ERROR: $relay is missing after the build"; return 1; }
  [ -f "$identity" ] || { log "ERROR: $identity is missing after the build"; return 1; }
  log "built $relay ($(stat -c%s "$relay") B, sha256 $(sha256sum "$relay" | cut -c1-16)…)"
  log "built $identity ($(stat -c%s "$identity") B)"
  log "the IVI image does not contain either: the relay is provisioned and the identity package is installed"
}

remove() {
  rm -rf "$DST_RELAY" "$DST_IDENTITY" && log "removed the staged relay and identity modules" \
    || { log "ERROR: could not remove the staged directories"; return 1; }
}

case "${1:-}" in
  stage) stage ;;
  build) build ;;
  remove) remove ;;
  *) echo "usage: $0 {stage|build|remove}" >&2; exit 2 ;;
esac
