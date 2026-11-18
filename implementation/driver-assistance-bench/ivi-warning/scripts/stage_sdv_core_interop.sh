#!/usr/bin/env bash
# Stage the SDV Core interop of the warning request (INC-DRIVING-002, MAP-DRIVING-DA-WARNING-REQUEST)
# into an AOSP tree: the SOME/IP struct of service 0x4df1 is translated in REFLECTION mode into the
# typed message de4sdv.driving.v1.CollisionWarningRequest and published as one Data Tunnel unit.
# Adapted from the closed-loop driving bench's ivi-observer/scripts/stage_sdv_core_interop.sh.
#
#   stage_sdv_core_interop.sh check          verify the tree and the artifacts, change nothing
#   stage_sdv_core_interop.sh render <file>  render the stack config with SCORE_SOMEIP_PEER into <file>
#   stage_sdv_core_interop.sh stage          copy the overlay into the tree (idempotent, backs up)
#   stage_sdv_core_interop.sh validate       stage, then the small catalog build (G1b) and its decode
#   stage_sdv_core_interop.sh revert         restore the backups and remove the added files
#
# Order in the guest rebuild recipe (phase10/aaos-build, BUILD-PLAN section b): after S6 (INC-MW-011)
# and S7 (INC-DRIVING-001), because everything here is added BESIDE their entries and the stack
# config render refuses to drop or change a service the tree carries (0x4dee, 0x4df0). Nothing here
# builds the image: an image build that re-runs S7's stage afterwards re-renders the stack config
# without 0x4df1, so stage this again after it.
# It never starts a VM, never dispatches a workflow, and never commits.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$HERE/.." && pwd)"
IDS="$ROOT/../interfaces/service_ids.json"

: "${AOSP_TOP:=$HOME/aosp}"
: "${AOSP_HOST_OUT:=$AOSP_TOP/out/host/linux-x86}"
: "${CORE_PRODUCT:=sdv_core_cf}"
: "${RELEASE:=cp2a}"
: "${VARIANT:=eng}"
# The S-CORE host's address on the VXLAN segment: 192.168.98.1 in the model. No default, as in the
# closed-loop driving bench: the caller states the address the guests' segment really has.
: "${SCORE_SOMEIP_PEER:=}"
: "${RUN_DIR:=$ROOT/run}"
: "${BACKUP:=$RUN_DIR/core-originals}"
SAMPLES="$AOSP_TOP/system/software_defined_vehicle/samples"
CATALOG="$SAMPLES/some_ip/catalog"
: "${CATALOG_DIR:=$CATALOG/de4sdv_driver_assistance}"
: "${BROKER_VSIDL:=$CATALOG/agent/broker.vsidl}"
: "${BROKER_ACL:=$SAMPLES/some_ip/config/broker_apex/someip_acl.textproto}"
: "${STACK_CONFIG:=$AOSP_TOP/system/software_defined_vehicle/some_ip/vsomeip_stack/vsomeip_config.json}"
: "${G1B_MODULES:=generate_vsidl_files_someip_catalog_protos_with_bp_file vsidlc_someip_catalog_protos_with_bp_file libsomeip_messages_catalog aprotoc}"

PROTO_SRC="$ROOT/contract/de4sdv_driving_collision_warning_request.proto"
MAPPING_SRC="$ROOT/interop/de4sdv_driving_collision_warning_request.vsidl"
ACL_SRC="$ROOT/interop/broker_acl_append.textproto"
TEMPLATE="$ROOT/interop/vsomeip_config.json"
PROTO_DST="de4sdv_driving_collision_warning_request.proto"
MAPPING_DST="de4sdv_driving_collision_warning_request_someip.vsidl"
# The earlier increments' broker entries: kept if the tree has them (a NOTE if it has not).
PRIOR_MARKERS=("De4sdvScoreAebsSignalFrame" "de4sdv.driving.v1.DrivingOperationalState")

log() { printf '%s %s\n' "$(date -u +%FT%T.%NZ)" "$*"; }
ids() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2], {}, {'d': d}))" "$IDS" "$1"; }

MESSAGE="$(ids "d['icd']['data_tunnel']['message']")"
UNIT="$(ids "d['icd']['data_tunnel']['service_unit']")"
TYPE_PACKAGE="${MESSAGE%.*}"
SERVICE_DEC="$(ids "int(d['icd']['someip_warning_request']['service_id'], 16)")"
EVENT_DEC="$(ids "int(d['icd']['someip_warning_request']['event_id'], 16)")"

render() { # <destination> [<current tree config>]
  [ -n "$SCORE_SOMEIP_PEER" ] || { log "ERROR: export SCORE_SOMEIP_PEER (the S-CORE host's address on the VXLAN segment; 192.168.98.1 in the model)"; return 1; }
  local current=()
  [ -n "${2:-}" ] && [ -f "$2" ] && current=(--current "$2")
  python3 "$HERE/render_stack_config.py" --template "$TEMPLATE" --peer "$SCORE_SOMEIP_PEER" --out "$1" "${current[@]}"
}

check() {
  local rc=0 f n
  [ -d "$CATALOG" ] || { log "ERROR: AOSP catalog not found under $SAMPLES (set AOSP_TOP)"; return 1; }
  for f in "$PROTO_SRC" "$MAPPING_SRC" "$ACL_SRC" "$TEMPLATE" "$BROKER_VSIDL" "$BROKER_ACL" "$STACK_CONFIG"; do
    [ -f "$f" ] || { log "ERROR: missing $f"; rc=1; }
  done
  grep -q 'name: "vsomeip_config.json"' "$(dirname "$STACK_CONFIG")/Android.bp" 2>/dev/null \
    || { log "ERROR: $STACK_CONFIG is not the prebuilt_etc source of vsomeip_config.json"; rc=1; }
  # The catalog takes **/*.proto and **/*.vsidl; an Android.bp below it would cut the directory out.
  [ -e "$CATALOG_DIR/Android.bp" ] && { log "ERROR: $CATALOG_DIR/Android.bp exists; remove it"; rc=1; }
  grep -q '"\*\*/\*.proto"' "$CATALOG/Android.bp" 2>/dev/null && grep -q '"\*\*/\*.vsidl"' "$CATALOG/Android.bp" 2>/dev/null \
    || { log "ERROR: the catalog Android.bp no longer globs **/*.proto and **/*.vsidl"; rc=1; }
  python3 "$HERE/gen_someip_vsidl.py" --check || rc=1
  n="$(grep -c 'message_translation_mode: REFLECTION' "$MAPPING_SRC")"; [ "$n" = 1 ] || { log "ERROR: $n REFLECTION events, expected 1"; rc=1; }
  n="$(grep -c "package_name: \"$TYPE_PACKAGE\"" "$MAPPING_SRC")"; [ "$n" = 1 ] || { log "ERROR: sdv_unit_type.package_name must be $TYPE_PACKAGE"; rc=1; }
  grep -q "^package $TYPE_PACKAGE;" "$PROTO_SRC" || { log "ERROR: proto package"; rc=1; }
  grep -q 'option (.sdv.vsidl.v1.publication)' "$PROTO_SRC" || { log "ERROR: the proto is not a VSIDL publication"; rc=1; }
  grep -q "topic: \"$UNIT\"" "$ACL_SRC" && grep -q "message: \"$MESSAGE\"" "$ACL_SRC" || { log "ERROR: broker ACL append"; rc=1; }
  grep -q "\"$UNIT\"" "$MAPPING_SRC" || { log "ERROR: mapping lacks unit $UNIT"; rc=1; }
  for f in "${PRIOR_MARKERS[@]}"; do
    if [ -f "$BROKER_VSIDL" ] && [ -f "$BROKER_ACL" ]; then
      grep -q "$f" "$BROKER_VSIDL" && grep -q "$f" "$BROKER_ACL" || log "NOTE: the earlier increment ($f) is not in this tree; stage it first (BUILD-PLAN S6, S7)"
    fi
  done
  [ "$rc" = 0 ] && log "check: ok (unit $UNIT, message $MESSAGE)"
  return "$rc"
}

stage() {
  [ -n "$SCORE_SOMEIP_PEER" ] || { log "ERROR: export SCORE_SOMEIP_PEER; nothing staged"; return 1; }
  check || return 1
  mkdir -p "$RUN_DIR" "$BACKUP"
  local f name rendered="$RUN_DIR/vsomeip_config.rendered.json"
  # 0. The stack config first: if the render refuses, nothing in the tree has changed.
  render "$rendered" "$STACK_CONFIG" || { log "ERROR: stack config render refused; nothing staged"; return 1; }
  for f in "$BROKER_VSIDL" "$BROKER_ACL" "$STACK_CONFIG"; do
    name="$(basename "$f")"
    [ -f "$BACKUP/$name" ] || cp -p "$f" "$BACKUP/$name"
  done

  # 1. The typed message and the mapping; no Android.bp (the catalog globs them).
  mkdir -p "$CATALOG_DIR"
  cp "$PROTO_SRC" "$CATALOG_DIR/$PROTO_DST"
  cp "$MAPPING_SRC" "$CATALOG_DIR/$MAPPING_DST"

  # 2. The broker ACL gains the publish permission of the unit, once, beside the existing entries.
  if grep -q "topic: \"$UNIT\"" "$BROKER_ACL"; then log "broker publish ACL for $UNIT already present"
  else { echo; cat "$ACL_SRC"; } >> "$BROKER_ACL"; log "appended the broker publish ACL for $UNIT"; fi

  # 3. The broker's bundle declares the publisher of the new type, after its first publisher entry.
  python3 - "$BROKER_VSIDL" "$MESSAGE" <<'PY' || { log "ERROR: could not insert the broker.vsidl publisher entry"; return 1; }
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

  # 4. The stack configuration: 0x4dee and 0x4df0 kept unchanged, 0x4df1 added with the peer.
  cp "$rendered" "$STACK_CONFIG"

  # 5. The earlier increments are still staged.
  for f in "${PRIOR_MARKERS[@]}"; do
    if grep -q "$f" "$BACKUP/broker.vsidl" && ! grep -q "$f" "$BROKER_VSIDL"; then log "ERROR: $f lost from broker.vsidl"; return 1; fi
    if grep -q "$f" "$BACKUP/someip_acl.textproto" && ! grep -q "$f" "$BROKER_ACL"; then log "ERROR: $f lost from the ACL"; return 1; fi
  done
  log "staged into $CATALOG_DIR (backup in $BACKUP), stack config with peer $SCORE_SOMEIP_PEER"
}

# The small validating build (G1b of the closed-loop driving bench): the catalog's pdk29 checks, the
# Rust compile of every catalog proto, and a decode of the generated SOME/IP config, which must hold
# 0x4df1 with one REFLECTION event of two fields, beside the services the tree had.
validate() {
  stage || return 1
  local log_file="$RUN_DIR/g1b-build.log" rc gen
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${CORE_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m $G1B_MODULES
  ) > "$log_file" 2>&1
  rc=$?
  tail -n 20 "$log_file"
  [ "$rc" = 0 ] || { log "ERROR: G1b failed (rc=$rc), see $log_file"; return 1; }
  gen="$(find "$AOSP_TOP/out/soong/.intermediates/system/software_defined_vehicle/samples/some_ip/vsidl_provider_targets/generate_vsidl_files_someip_catalog_protos_with_bp_file" -name someip-config.binpb 2>/dev/null | head -n 1)"
  [ -n "$gen" ] || { log "ERROR: someip-config.binpb not found under out/soong/.intermediates"; return 1; }
  "$AOSP_HOST_OUT/bin/aprotoc" --decode=sdv.runtime.v1.SomeipRuntimeConfig \
      -I "$AOSP_TOP/system/software_defined_vehicle/vsidl/language/src/protos" -I "$AOSP_TOP/external/protobuf/src" \
      sdv/runtime/v1/runtime_config.proto < "$gen" > "$RUN_DIR/someip-config.decoded.txt" \
    || { log "ERROR: cannot decode $gen"; return 1; }
  python3 - "$RUN_DIR/someip-config.decoded.txt" "$SERVICE_DEC" "$EVENT_DEC" "$TYPE_PACKAGE" "${MESSAGE##*.}" "$BACKUP/broker.vsidl" <<'PY' || return 1
import re, sys
path, service, event, package, name, prior_broker = sys.argv[1:7]
t = open(path).read()
blocks = re.split(r"\n(?=some_ip_mapping \{)", t)
mine = [b for b in blocks if f"someip_service_id: {service}" in b]
assert len(mine) == 1, f"service {service} not exactly once in someip-config.binpb"
b = mine[0]
assert re.findall(r"event_id: (\d+)", b) == [event], re.findall(r"event_id: (\d+)", b)
assert b.count("field_name:") == 2, b.count("field_name:")
assert f'package_name: "{package}"' in b and f'type_name: "{name}"' in b
assert "INTERPRET_AS_BYTES" not in b
if "DrivingOperationalState" in open(prior_broker).read():
    assert "someip_service_id: 19952" in t, "0x4df0 is gone from someip-config.binpb"
print(f"G1b: someip-config.binpb holds service {service}, event {event}, 2 fields, unit type {package}.{name}")
PY
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
    rm -f -- "$BACKUP/$name"
    log "restored $name"
  done
  if [ -d "$CATALOG_DIR" ]; then
    rm -f -- "$CATALOG_DIR/$PROTO_DST" "$CATALOG_DIR/$MAPPING_DST"
    rmdir "$CATALOG_DIR" 2>/dev/null || true
  fi
  log "reverted"
}

case "${1:-}" in
  check) check ;;
  render) [ -n "${2:-}" ] || { echo "usage: $0 render <file>" >&2; exit 2; }; render "$2" ;;
  stage) stage ;;
  validate) validate ;;
  revert) revert ;;
  *) echo "usage: $0 {check|render <file>|stage|validate|revert}" >&2; exit 2 ;;
esac
