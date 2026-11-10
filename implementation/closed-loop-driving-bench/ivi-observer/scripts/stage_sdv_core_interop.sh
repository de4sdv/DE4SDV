#!/usr/bin/env bash
# Stage and build the SDV Core interop of the driving operational state
# (INC-DRIVING-001 slice 10b, GAP-DRIVING-006), option B: the SOME/IP struct is
# translated in REFLECTION mode into the typed VSIDL message.
#
#   stage_sdv_core_interop.sh check     verify the tree and the artifacts, change nothing
#   stage_sdv_core_interop.sh stage     copy the overlay into the AOSP tree (idempotent, backs up)
#   stage_sdv_core_interop.sh validate  stage, then the small G1b build (catalog checks + protos)
#   stage_sdv_core_interop.sh build     stage, G1b, the SDV Core image, record the identity
#   stage_sdv_core_interop.sh revert    restore the backups and remove the added files
#
# Everything is added BESIDE the earlier increment's edits that the tree already
# carries (catalog/de4sdv_score, the De4sdvScoreAebsSignalFrame publisher and ACL,
# the 0x4dee stack service); the script checks they are still there after staging.
# It never starts a VM, never dispatches a workflow, and never commits.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
SLICE="$SLICE_ROOT"
mkdir -p "$RUN_DIR"

FIELD_COUNT=$(python3 -c "import sys; sys.dont_write_bytecode=True; sys.path.insert(0,'$SLICE'); import codec.icd_table as t; print(len(t.FIELDS))")
if [ "$MAPPING_VARIANT" = one ]; then
  MAPPING_SRC="$INTEROP/variants/de4sdv_driving_operational_state.one_unit.vsidl"
  ACL_SRC="$INTEROP/variants/broker_acl_append.one_unit.textproto"
else
  MAPPING_SRC="$INTEROP/de4sdv_driving_operational_state.vsidl"
  ACL_SRC="$INTEROP/broker_acl_append.textproto"
fi
PROTO_SRC="$CONTRACT/de4sdv_driving_operational_state.proto"
PRIOR_MARKERS=("De4sdvScoreAebsSignalFrame")   # the earlier increment, must survive staging

disk_free_gb() { df -B1G --output=avail / | tail -1 | tr -d ' '; }

# The stack config, rendered with the peer; acceptances for one address are merged.
render_stack_config() { # <destination>
  [ -n "${SCORE_SOMEIP_PEER:-}" ] || { log "ERROR: export SCORE_SOMEIP_PEER (the S-CORE host's VXLAN address, RUNBOOK step 4)"; return 1; }
  python3 - "$INTEROP/vsomeip_config.json" "$1" "$SCORE_SOMEIP_PEER" <<'PY' || return 1
import json, sys
src, dst, peer = sys.argv[1:4]
text = open(src).read().replace("__SCORE_SOMEIP_PEER__", peer)
cfg = json.loads(text)
merged = {}
for acc in cfg.get("acceptances", []):
    merged.setdefault(acc["address"], {"address": acc["address"], "reliable": []})["reliable"] += acc.get("reliable", [])
cfg["acceptances"] = list(merged.values())
services = {s["service"] for s in cfg["services"]}
assert {"0x4dee", "0x4df0"} <= services, f"both services must stay configured, found {services}"
assert "__SCORE_SOMEIP_PEER__" not in json.dumps(cfg)
open(dst, "w").write(json.dumps(cfg, indent=2) + "\n")
print(f"stack config rendered: services {sorted(services)}, 0x4df0 provider {peer}")
PY
}

check() {
  local rc=0 f u
  [ -d "$SAMPLES/some_ip/catalog" ] || { log "AOSP catalog not found under $SAMPLES (set AOSP_TOP)"; return 1; }
  for f in "$INTEROP/vsomeip_config.json" "$MAPPING_SRC" "$ACL_SRC" \
           "$INTEROP/acl/ivi_observer_subscriber.textproto" \
           "$INTEROP/acl/ivi_broker_object_policy.textproto" "$PROTO_SRC" \
           "$BROKER_VSIDL" "$BROKER_ACL" "$STACK_CONFIG"; do
    [ -f "$f" ] || { log "ERROR: missing $f"; rc=1; }
  done
  grep -q 'name: "vsomeip_config.json"' "$(dirname "$STACK_CONFIG")/Android.bp" 2>/dev/null \
    || { log "ERROR: $STACK_CONFIG is not the prebuilt_etc source of vsomeip_config.json"; rc=1; }
  # The catalog takes **/*.proto and **/*.vsidl; a sub-Android.bp would cut CATALOG_DIR out.
  [ -e "$CATALOG_DIR/Android.bp" ] && { log "ERROR: $CATALOG_DIR/Android.bp exists; remove it (left by the old stage script)"; rc=1; }
  grep -q '"\*\*/\*.proto"' "$SAMPLES/some_ip/catalog/Android.bp" && grep -q '"\*\*/\*.vsidl"' "$SAMPLES/some_ip/catalog/Android.bp" \
    || { log "ERROR: the catalog Android.bp no longer globs **/*.proto and **/*.vsidl"; rc=1; }
  if [ "$MAPPING_VARIANT" = one ]; then
    python3 "$SLICE/scripts/gen_someip_vsidl.py" --check --one-unit || rc=1
  else
    python3 "$SLICE/scripts/gen_someip_vsidl.py" --check || rc=1
  fi
  local n
  n="$(grep -c 'message_translation_mode: REFLECTION' "$MAPPING_SRC")"; [ "$n" = 3 ] || { log "ERROR: $n REFLECTION events, expected 3"; rc=1; }
  n="$(grep -c '^    instance_impl {' "$MAPPING_SRC")"; [ "$n" = 3 ] || { log "ERROR: $n instance_impl blocks, expected 3 (interface_type is a oneof)"; rc=1; }
  n="$(grep -c 'field_name:' "$MAPPING_SRC")"; [ "$n" = "$((FIELD_COUNT * 3))" ] || { log "ERROR: $n field_names, expected $((FIELD_COUNT * 3))"; rc=1; }
  n="$(grep -c "package_name: \"$TYPE_PACKAGE\"" "$MAPPING_SRC")"; [ "$n" = 3 ] || { log "ERROR: sdv_unit_type.package_name must be the proto package $TYPE_PACKAGE (found $n)"; rc=1; }
  grep -q 'sdv_topic_parameterization' "$MAPPING_SRC" && { log "ERROR: sdv_topic_parameterization in a pdk29 catalog mapping"; rc=1; }
  grep -q "^package $TYPE_PACKAGE;" "$PROTO_SRC" || { log "ERROR: proto package"; rc=1; }
  grep -q 'option (.sdv.vsidl.v1.publication)' "$PROTO_SRC" || { log "ERROR: the proto is not a VSIDL publication (pdk29 PublicationTypeDoesNotExist)"; rc=1; }
  n="$(grep -cE '^\s*string .*variable_type_max_size' "$PROTO_SRC")"; [ "$n" = "$(grep -cE '^\s*string ' "$PROTO_SRC")" ] || { log "ERROR: a string field lacks variable_type_max_size"; rc=1; }
  n="$(grep -cE '^\s*repeated .*repeated_field_max_count' "$PROTO_SRC")"; [ "$n" = "$(grep -cE '^\s*repeated ' "$PROTO_SRC")" ] || { log "ERROR: a repeated field lacks repeated_field_max_count"; rc=1; }
  for u in $SERVICE_UNITS; do
    grep -q "topic: \"$u\"" "$ACL_SRC" || { log "ERROR: broker ACL lacks unit $u"; rc=1; }
    grep -q "\"$u\"" "$MAPPING_SRC" || { log "ERROR: mapping lacks unit $u"; rc=1; }
  done
  grep -q "message: \"$MESSAGE_NAME\"" "$ACL_SRC" || { log "ERROR: broker ACL message"; rc=1; }
  for f in "${PRIOR_MARKERS[@]}"; do
    grep -q "$f" "$BROKER_VSIDL" && grep -q "$f" "$BROKER_ACL" || log "NOTE: the earlier increment ($f) is not in this tree"
  done
  [ "$rc" = 0 ] && log "check: ok (variant: $MAPPING_VARIANT, units: $SERVICE_UNITS)"
  return "$rc"
}

stage() {
  [ -n "${SCORE_SOMEIP_PEER:-}" ] || { log "ERROR: export SCORE_SOMEIP_PEER (the S-CORE host's VXLAN address, RUNBOOK step 4); nothing staged"; return 1; }
  check || return 1
  mkdir -p "$BACKUP" "$CATALOG_DIR"
  local f name u
  for f in "$BROKER_VSIDL" "$BROKER_ACL" "$STACK_CONFIG"; do
    name="$(basename "$f")"
    [ -f "$BACKUP/$name" ] || cp -p "$f" "$BACKUP/$name"
  done

  # 1. The typed message and the mapping; no Android.bp (the catalog globs them).
  cp "$PROTO_SRC" "$CATALOG_DIR/de4sdv_driving_operational_state.proto"
  rm -f "$CATALOG_DIR"/de4sdv_driving_operational_state*.vsidl "$CATALOG_DIR/someip_type_definition.textproto"
  cp "$MAPPING_SRC" "$CATALOG_DIR/de4sdv_driving_operational_state_someip.vsidl"

  # 2. The broker ACL gains one publish permission per unit, beside the existing entries.
  for u in $SERVICE_UNITS; do
    if grep -q "topic: \"$u\"" "$BROKER_ACL"; then log "broker publish ACL for $u already present"; fi
  done
  if ! grep -q "topic: \"$(set -- $SERVICE_UNITS; echo "$1")\"" "$BROKER_ACL"; then
    { echo; cat "$ACL_SRC"; } >> "$BROKER_ACL"; log "appended the broker publish ACL ($MAPPING_VARIANT unit variant)"
  fi

  # 3. The broker's bundle declares the publisher of the new type, after the first
  #    `publisher { message: ... }` entry. Fully qualified, as the tree's own
  #    cross-package entries (com.android.sdv.sample.someip.Cuj26SomeIpPayload, ...).
  python3 - "$BROKER_VSIDL" "$MESSAGE_NAME" <<'PY' || { log "ERROR: could not insert the broker.vsidl publisher entry"; return 1; }
import re, sys
path, message = sys.argv[1], sys.argv[2]
text = open(path).read()
if f'message: "{message}"' in text:
    print("broker.vsidl publisher already present"); sys.exit(0)
m = re.search(r'\n([ \t]*)publisher \{\n[ \t]*message: "[^"]+"\n[ \t]*\}\n', text)
if not m:
    sys.stderr.write("no existing publisher entry to anchor to\n"); sys.exit(1)
indent = m.group(1)
add = indent + "publisher {\n" + indent + '  message: "' + message + '"\n' + indent + "}\n"
open(path, "w").write(text[:m.end()] + add + text[m.end():])
print(f"broker.vsidl publisher inserted: {message}")
PY

  # 4. The stack configuration: 0x4dee kept, 0x4df0 added and pinned to the peer.
  render_stack_config "$STACK_CONFIG" || return 1

  # 5. The earlier increment is still staged.
  for f in "${PRIOR_MARKERS[@]}"; do
    if grep -q "$f" "$BACKUP/broker.vsidl" && ! grep -q "$f" "$BROKER_VSIDL"; then log "ERROR: $f lost from broker.vsidl"; return 1; fi
    if grep -q "$f" "$BACKUP/someip_acl.textproto" && ! grep -q "$f" "$BROKER_ACL"; then log "ERROR: $f lost from the ACL"; return 1; fi
  done
  log "staged into $CATALOG_DIR (backup in $BACKUP); variant $MAPPING_VARIANT"
}

# The small validating build (G1b, G1B_MODULES in bench_env.sh): vsidl_rc_generator and
# vsidlc over the whole catalog in pdk29 (PublicationType, annotations, unresolved
# publisher, unit name length), every catalog proto compiled, then the generated
# someip-config.binpb must hold 0x4df0 with three REFLECTION events.
validate() {
  stage || return 1
  local log_file="$RUN_DIR/g1b-build.log" rc
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${CORE_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m $G1B_MODULES
  ) > "$log_file" 2>&1
  rc=$?
  tail -20 "$log_file"
  [ "$rc" = 0 ] || { log "ERROR: G1b failed (rc=$rc), see $log_file"; return 1; }
  local gen
  gen="$(find "$AOSP_TOP/out/soong/.intermediates/system/software_defined_vehicle/samples/some_ip/vsidl_provider_targets/generate_vsidl_files_someip_catalog_protos_with_bp_file" -name someip-config.binpb 2>/dev/null | head -1)"
  [ -n "$gen" ] || { log "ERROR: someip-config.binpb not found under out/soong/.intermediates"; return 1; }
  "$AOSP_HOST_OUT/bin/aprotoc" --decode=sdv.runtime.v1.SomeipRuntimeConfig \
      -I "$AOSP_TOP/system/software_defined_vehicle/vsidl/language/src/protos" -I "$AOSP_TOP/external/protobuf/src" \
      sdv/runtime/v1/runtime_config.proto < "$gen" > "$RUN_DIR/someip-config.decoded.txt" \
    || { log "ERROR: cannot decode $gen"; return 1; }
  python3 - "$RUN_DIR/someip-config.decoded.txt" <<'PY' || return 1
import re, sys
t = open(sys.argv[1]).read()
blocks = [b for b in re.split(r"\n(?=some_ip_mapping \{)", t) if "someip_service_id: 19952" in b]  # 0x4df0
assert blocks, "0x4df0 not in someip-config.binpb"
b = blocks[0]
ev = re.findall(r"event_id: (\d+)", b)
assert sorted(set(ev)) == ["32769", "32770", "32771"], ev
assert b.count("field_name:") == 129, b.count("field_name:")
assert 'package_name: "de4sdv.driving.v1"' in b
assert "INTERPRET_AS_BYTES" not in b
print("G1b: someip-config.binpb holds 0x4df0, events 0x8001-0x8003, 3 x 43 fields, unit type de4sdv.driving.v1")
PY
}

build() {
  validate || return 1
  local free; free="$(disk_free_gb)"
  log "disk free: ${free} GB (floor ${DISK_FLOOR_GB})"
  [ "$free" -ge "$DISK_FLOOR_GB" ] || { log "ERROR: disk below the floor; prune first (runbook step 2)"; return 1; }
  local log_file="$RUN_DIR/core-build.log" rc
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${CORE_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m   # droid: system_ext/product/vendor images, then super.img, then vbmeta.img
  ) > "$log_file" 2>&1
  rc=$?
  tail -5 "$log_file"
  [ "$rc" = 0 ] || { log "ERROR: the SDV Core build failed (rc=$rc); no identity record is written"; return 1; }

  local product_out="$AOSP_TOP/out/target/product/$CORE_PRODUCT" manifest_r img
  for img in super.img vbmeta.img; do
    [ "$product_out/$img" -nt "$CATALOG_DIR/de4sdv_driving_operational_state.proto" ] \
      || { log "ERROR: $img is older than the staged overlay (stale image would boot the old partitions)"; return 1; }
  done
  manifest_r="$(cd "$AOSP_TOP" && PATH="$HOME/bin:$PATH" repo manifest -r 2>/dev/null)"
  {
    echo "# SDV Core image build $(date -u +%FT%T.%NZ)"
    echo "target: ${CORE_PRODUCT}-${RELEASE}-${VARIANT}, boot mode UNLOCKED"
    echo "option: B (SOME/IP struct -> REFLECTION -> $MESSAGE_NAME), units: $SERVICE_UNITS"
    echo "score_someip_peer: ${SCORE_SOMEIP_PEER}"
    if [ -n "$manifest_r" ]; then printf '%s' "$manifest_r" | sha256sum | sed 's/^/manifest_r_sha256: /'
    else echo "manifest_r_sha256: ERROR repo manifest -r produced nothing"; fi
    ( cd "$AOSP_TOP/device/google/sdv" 2>/dev/null && git diff | sha256sum | sed 's/^/device_google_sdv_diff_sha256: /' )
    grep -m1 ro.build.fingerprint "$product_out/system/build.prop" 2>/dev/null \
      || grep -m1 ro.system.build.fingerprint "$product_out/system/build.prop" 2>/dev/null
    for img in super.img vbmeta.img boot.img init_boot.img vendor_boot.img; do
      [ -f "$product_out/$img" ] && sha256sum "$product_out/$img"
    done
    echo "overlay inputs (at their destinations):"
    sha256sum "$CATALOG_DIR/de4sdv_driving_operational_state.proto" \
      "$CATALOG_DIR/de4sdv_driving_operational_state_someip.vsidl" \
      "$BROKER_VSIDL" "$BROKER_ACL" "$STACK_CONFIG" 2>/dev/null
  } > "$RUN_DIR/core-image-identity.txt"
  log "recorded the build identity in $RUN_DIR/core-image-identity.txt"
}

revert() {
  local name
  for name in broker.vsidl someip_acl.textproto vsomeip_config.json; do
    [ -f "$BACKUP/$name" ] || continue
    case "$name" in
      broker.vsidl) cp -p "$BACKUP/$name" "$BROKER_VSIDL" ;;
      someip_acl.textproto) cp -p "$BACKUP/$name" "$BROKER_ACL" ;;
      vsomeip_config.json) cp -p "$BACKUP/$name" "$STACK_CONFIG" ;;
    esac
    log "restored $name"
  done
  if [ -d "$CATALOG_DIR" ]; then
    rm -f -- "$CATALOG_DIR/de4sdv_driving_operational_state.proto" \
             "$CATALOG_DIR"/de4sdv_driving_operational_state*.vsidl \
             "$CATALOG_DIR/someip_type_definition.textproto"
    rmdir "$CATALOG_DIR" 2>/dev/null || true
  fi
  log "reverted; rebuild the base image with: lunch ${CORE_PRODUCT}-${RELEASE}-${VARIANT}; m"
}

case "${1:-}" in
  check) check ;;
  stage) stage ;;
  validate) validate ;;
  build) build ;;
  revert) revert ;;
  *) echo "usage: $0 {check|stage|validate|build|revert}" >&2; exit 2 ;;
esac
