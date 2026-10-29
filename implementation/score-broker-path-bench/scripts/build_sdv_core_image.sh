#!/usr/bin/env bash
# Build the SDV Core image with the DE4SDV broker mapping and stack
# configuration, from a clean, recorded build (GAP-MW-038). The core image
# cannot be remounted and its apexd activates every APEX at bootstrap, so the
# mapping can enter the SDV Core VM only through the image. The spike's cp2a
# eng images with the spike's broker APEX are not acceptable; this starts from
# a clean tree and records the identity only on a successful build.
#
#   build_sdv_core_image.sh stage     copy the overlay into the AOSP samples tree (idempotent; backs up originals)
#   build_sdv_core_image.sh build     stage, build the SDV Core image, record the identity (only if the build passed)
#   build_sdv_core_image.sh revert     restore the backed-up originals and remove the added files (the undo)
#
# It never dispatches a workflow.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
OVERLAY="$HERE/../aosp-overlay/core"
: "${RUN_DIR:=$HERE/../run}"
: "${SAMPLES:=$AOSP_TOP/system/software_defined_vehicle/samples}"
: "${BACKUP:=$RUN_DIR/core-image-originals}"
: "${DISK_FLOOR_GB:=15}"
CATALOG_DIR="$SAMPLES/some_ip/catalog/de4sdv_score"
BROKER_VSIDL="$SAMPLES/some_ip/catalog/agent/broker.vsidl"
BROKER_ACL="$SAMPLES/some_ip/config/broker_apex/someip_acl.textproto"

mkdir -p "$RUN_DIR"

# The stack configuration's real source, found in the tree (not assumed under
# samples/). Fail when it is absent.
find_stack_config() {
  local found
  found="$(grep -rl --include=Android.bp 'vsomeip_config.json' "$AOSP_TOP/system/software_defined_vehicle" 2>/dev/null | head -1)"
  [ -n "$found" ] || return 1
  local dir; dir="$(dirname "$found")"
  if [ -f "$dir/vsomeip_config.json" ]; then echo "$dir/vsomeip_config.json"; return 0; fi
  find "$AOSP_TOP/system/software_defined_vehicle" -name vsomeip_config.json -path '*vsomeip_stack*' 2>/dev/null | head -1
}

disk_free_gb() { df -B1G --output=avail / | tail -1 | tr -d ' '; }

stage() {
  [ -d "$SAMPLES" ] || { log "AOSP samples tree not found at $SAMPLES"; return 1; }
  local stack_config; stack_config="$(find_stack_config)" \
    || { log "ERROR: the stack vsomeip_config.json source was not found in the tree"; return 1; }
  log "stack config source: $stack_config"
  mkdir -p "$BACKUP" "$CATALOG_DIR"
  local f name
  for f in "$BROKER_VSIDL" "$BROKER_ACL" "$stack_config"; do
    name="$(basename "$f")"
    [ -f "$BACKUP/$name" ] || { [ -f "$f" ] && cp -p "$f" "$BACKUP/$name"; }
  done
  # 1. The frame type and the mapping (# comments, protobuf text format).
  cp "$OVERLAY/de4sdv_score_frame.proto" "$CATALOG_DIR/"
  cp "$OVERLAY/de4sdv_score_frame_someip.vsidl" "$CATALOG_DIR/"
  # 2. The broker ACL gains the publish permission, once.
  if ! grep -q "de4sdv-score-aebs-signal-frame" "$BROKER_ACL" 2>/dev/null; then
    cat "$OVERLAY/broker_acl_append.textproto" >> "$BROKER_ACL"; log "appended broker publish ACL"
  fi
  # 3. The broker bundle declares the publisher of the new type, at the anchor
  #    of an existing publisher entry (as the feasibility overlay did).
  python3 - "$BROKER_VSIDL" <<'PY' || { log "ERROR: could not insert the broker.vsidl publisher entry"; return 1; }
import re, sys
path = sys.argv[1]; text = open(path).read()
add = '    publisher {\n      message: "De4sdvScoreAebsSignalFrame"\n    }\n'
if "De4sdvScoreAebsSignalFrame" in text:
    sys.exit(0)
m = re.search(r'\n(\s*)publisher \{\n\s*message: "[^"]+"\n\s*\}\n', text)
if not m:
    sys.stderr.write("no existing publisher entry to anchor to\n"); sys.exit(1)
text = text[:m.end()] + add + text[m.end():]
open(path, "w").write(text); print("broker.vsidl publisher inserted")
PY
  # 4. The DE4SDV stack configuration (offers no service; endpoint pinned/secure).
  cp "$OVERLAY/vsomeip_config.json" "$stack_config"
  echo "$stack_config" > "$RUN_DIR/.stack_config_path"
  log "staged the overlay into $SAMPLES (backup in $BACKUP)"
  log "NOTE: the broker-APEX vsidl_schemas_path change is an S1 check; the image-built mapping may not need it (GAP-MW-038)."
}

build() {
  stage || return 1
  local free; free="$(disk_free_gb)"
  log "disk free: ${free} GB (floor ${DISK_FLOOR_GB})"
  [ "$free" -ge "$DISK_FLOOR_GB" ] || { log "ERROR: disk below the floor; prune first (S0)"; return 1; }
  local build_rc=0
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${CORE_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    installclean >/dev/null 2>&1 || true   # a clean build for the recorded identity
    m
  ) 2>&1 | tail -5 || build_rc=1
  # ${PIPESTATUS[0]} is the subshell's status under pipefail.
  [ "${PIPESTATUS[0]:-0}" = 0 ] || build_rc=1
  if [ "$build_rc" != 0 ]; then
    log "ERROR: the SDV Core build failed; no identity record is written"
    return 1
  fi
  local product_out="$AOSP_TOP/out/target/product/$CORE_PRODUCT" stack_config
  stack_config="$(cat "$RUN_DIR/.stack_config_path" 2>/dev/null)"
  {
    echo "# SDV Core image build $(date -u +%FT%T.%NZ)"
    echo "target: ${CORE_PRODUCT}-${RELEASE}-${VARIANT}, boot mode UNLOCKED"
    ( cd "$AOSP_TOP" && repo manifest -r 2>/dev/null | sha256sum | sed 's/^/manifest_r_sha256: /' )
    ( cd "$AOSP_TOP" && repo status 2>/dev/null | sed 's/^/repo_status: /' | head -40 )
    ( cd "$AOSP_TOP/device/google/sdv" 2>/dev/null && git diff | sha256sum | sed 's/^/device_google_sdv_diff_sha256: /' )
    grep -m1 ro.build.fingerprint "$product_out/system/build.prop" 2>/dev/null \
      || grep -m1 ro.system.build.fingerprint "$product_out/system/build.prop" 2>/dev/null
    local img
    for img in super.img vbmeta.img boot.img init_boot.img vendor_boot.img; do
      [ -f "$product_out/$img" ] && sha256sum "$product_out/$img"
    done
    echo "overlay inputs (at their destinations):"
    sha256sum "$CATALOG_DIR/de4sdv_score_frame.proto" "$CATALOG_DIR/de4sdv_score_frame_someip.vsidl" \
      "$BROKER_VSIDL" "$BROKER_ACL" "$stack_config" 2>/dev/null
  } > "$RUN_DIR/core-image-identity.txt"
  log "recorded the build identity in $RUN_DIR/core-image-identity.txt"
}

revert() {
  local stack_config; stack_config="$(cat "$RUN_DIR/.stack_config_path" 2>/dev/null)"
  local name
  for name in broker.vsidl someip_acl.textproto vsomeip_config.json; do
    [ -f "$BACKUP/$name" ] || continue
    case "$name" in
      broker.vsidl) cp -p "$BACKUP/$name" "$BROKER_VSIDL" ;;
      someip_acl.textproto) cp -p "$BACKUP/$name" "$BROKER_ACL" ;;
      vsomeip_config.json) [ -n "$stack_config" ] && cp -p "$BACKUP/$name" "$stack_config" ;;
    esac
    log "restored $name"
  done
  if [ -d "$CATALOG_DIR" ]; then
    rm -f -- "$CATALOG_DIR/de4sdv_score_frame.proto" "$CATALOG_DIR/de4sdv_score_frame_someip.vsidl"
    rmdir "$CATALOG_DIR" 2>/dev/null || true
  fi
  log "reverted the overlay; rebuild the base image with: lunch ${CORE_PRODUCT}-${RELEASE}-${VARIANT}; m"
}

case "${1:-}" in
  stage) stage ;;
  build) build ;;
  revert) revert ;;
  *) echo "usage: $0 {stage|build|revert}" >&2; exit 2 ;;
esac
