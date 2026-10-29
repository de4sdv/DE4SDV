#!/usr/bin/env bash
# Build the SDV Core image with the DE4SDV broker mapping and stack
# configuration, from a clean, recorded build (GAP-MW-038). The core image
# cannot be remounted and its apexd activates every APEX at bootstrap, so the
# mapping can enter the SDV Core VM only through the image. The spike's cp2a
# eng images with the spike's broker APEX are not acceptable; this starts from
# a clean tree.
#
#   build_sdv_core_image.sh stage     copy the overlay into the AOSP samples tree (idempotent; backs up originals)
#   build_sdv_core_image.sh build     stage, then build the SDV Core image and record digests
#   build_sdv_core_image.sh revert    restore the backed-up originals and remove the added files (the undo)
#
# It records every input and the image digests under the run directory, so the
# evidence names the exact build. It never dispatches a workflow.
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
OVERLAY="$HERE/../aosp-overlay/core"
: "${RUN_DIR:=$HERE/../run}"
: "${SAMPLES:=$AOSP_TOP/system/software_defined_vehicle/samples}"
: "${BACKUP:=$RUN_DIR/core-image-originals}"
# Where the overlay files land in the tree. Confirmed against the AOSP samples
# layout the bench VM holds; override if the tree moves.
CATALOG_DIR="$SAMPLES/some_ip/catalog/de4sdv_score"
BROKER_VSIDL="$SAMPLES/some_ip/catalog/agent/broker.vsidl"
BROKER_ACL="$SAMPLES/some_ip/config/broker_apex/someip_acl.textproto"
STACK_CONFIG="$SAMPLES/some_ip/vsomeip_stack/vsomeip_config.json"

mkdir -p "$RUN_DIR"

stage() {
  [ -d "$SAMPLES" ] || { log "AOSP samples tree not found at $SAMPLES"; return 1; }
  mkdir -p "$BACKUP" "$CATALOG_DIR"
  # Back up each file the overlay changes, once.
  for f in "$BROKER_VSIDL" "$BROKER_ACL" "$STACK_CONFIG"; do
    local name; name="$(basename "$f")"
    [ -f "$BACKUP/$name" ] || { [ -f "$f" ] && cp -p "$f" "$BACKUP/$name"; }
  done
  # 1. The frame type and the mapping (new files; idempotent copy).
  cp "$OVERLAY/de4sdv_score_frame.proto" "$CATALOG_DIR/"
  cp "$OVERLAY/de4sdv_score_frame_someip.vsidl" "$CATALOG_DIR/"
  # 2. The broker ACL gains the publish permission, once.
  if ! grep -q "de4sdv-score-aebs-signal-frame" "$BROKER_ACL" 2>/dev/null; then
    cat "$OVERLAY/broker_acl_append.textproto" >> "$BROKER_ACL"; log "appended broker publish ACL"
  fi
  # 3. The DE4SDV stack configuration (offers no service; endpoint pinned).
  cp "$OVERLAY/vsomeip_config.json" "$STACK_CONFIG"
  log "staged the overlay into $SAMPLES (backup in $BACKUP)"
  log "NOTE: the broker.vsidl publisher entry for De4sdvScoreAebsSignalFrame is added by hand per the samples layout; see README."
}

build() {
  stage || return 1
  require_cmd "$CVD" || true
  ( set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${CORE_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null
    log "building ${CORE_PRODUCT}-${RELEASE}-${VARIANT}"
    m 2>&1 | tail -3
  )
  local product_out="$AOSP_TOP/out/target/product/$CORE_PRODUCT"
  {
    echo "# SDV Core image build $(date -u +%FT%T.%NZ)"
    echo "target: ${CORE_PRODUCT}-${RELEASE}-${VARIANT}"
    ( cd "$AOSP_TOP" && echo "manifest: $(cat .repo/manifests/default.xml 2>/dev/null | md5sum | cut -d' ' -f1 2>/dev/null)" )
    echo "fingerprint: $(grep -m1 ro.build.fingerprint "$product_out/system/build.prop" 2>/dev/null)"
    for img in super.img vbmeta.img boot.img init_boot.img vendor_boot.img; do
      [ -f "$product_out/$img" ] && sha256sum "$product_out/$img"
    done
    echo "overlay inputs:"
    sha256sum "$OVERLAY"/* 2>/dev/null
  } > "$RUN_DIR/core-image-identity.txt"
  log "recorded the build identity in $RUN_DIR/core-image-identity.txt"
}

revert() {
  for name in broker.vsidl someip_acl.textproto vsomeip_config.json; do
    [ -f "$BACKUP/$name" ] && {
      case "$name" in
        broker.vsidl) cp -p "$BACKUP/$name" "$BROKER_VSIDL" ;;
        someip_acl.textproto) cp -p "$BACKUP/$name" "$BROKER_ACL" ;;
        vsomeip_config.json) cp -p "$BACKUP/$name" "$STACK_CONFIG" ;;
      esac
      log "restored $name"
    }
  done
  [ -d "$CATALOG_DIR" ] && { rm -f -- "$CATALOG_DIR/de4sdv_score_frame.proto" "$CATALOG_DIR/de4sdv_score_frame_someip.vsidl"; rmdir "$CATALOG_DIR" 2>/dev/null || true; }
  log "reverted the overlay; rebuild the base image with: lunch ${CORE_PRODUCT}-${RELEASE}-${VARIANT}; m"
}

case "${1:-}" in
  stage) stage ;;
  build) build ;;
  revert) revert ;;
  *) echo "usage: $0 {stage|build|revert}" >&2; exit 2 ;;
esac
