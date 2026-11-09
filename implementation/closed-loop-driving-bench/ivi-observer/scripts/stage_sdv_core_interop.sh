#!/usr/bin/env bash
# Stage and build the SDV Core interop of the driving operational state
# (INC-DRIVING-001 slice 10b, GAP-DRIVING-006), option B: the SOME/IP struct is
# translated in REFLECTION mode into the typed VSIDL message.
#
#   stage_sdv_core_interop.sh check    verify the tree and the artifacts, change nothing
#   stage_sdv_core_interop.sh stage    copy the overlay into the AOSP tree (idempotent, backs up)
#   stage_sdv_core_interop.sh build    stage, build the SDV Core image, record the identity
#   stage_sdv_core_interop.sh revert   restore the backups and remove the added files
#
# Modeled on score-broker-path-bench/scripts/build_sdv_core_image.sh, whose
# overlay this one replaces: the SOME/IP mapping, the type definition, the stack
# configuration and the broker ACL are image content, because the core image
# cannot be remounted and apexd activates every APEX at bootstrap, so a data APEX
# update does not reach it (GAP-MW-038, ADR 0025).
#
# It never starts a VM, never dispatches a workflow, and never commits: the
# staging tree is the VM's checkout.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
SLICE="$SLICE_ROOT"

mkdir -p "$RUN_DIR"

FIELD_COUNT=$(python3 -c "import sys; sys.path.insert(0,'$SLICE'); import codec.icd_table as t; print(len(t.FIELDS))")

# The stack configuration's real source in the tree (not assumed under samples/);
# the AEBS bench used the same search.
find_stack_config() {
  local found dir
  found="$(grep -rl --include=Android.bp 'vsomeip_config.json' "$AOSP_TOP/system/software_defined_vehicle" 2>/dev/null | head -1)"
  [ -n "$found" ] || return 1
  dir="$(dirname "$found")"
  if [ -f "$dir/vsomeip_config.json" ]; then echo "$dir/vsomeip_config.json"; return 0; fi
  find "$AOSP_TOP/system/software_defined_vehicle" -name vsomeip_config.json -path '*vsomeip_stack*' 2>/dev/null | head -1
}

disk_free_gb() { df -B1G --output=avail / | tail -1 | tr -d ' '; }

render_stack_config() { # <destination>
  local destination="$1"
  if grep -q '__SCORE_SOMEIP_PEER__' "$INTEROP/vsomeip_config.json"; then
    sed "s/__SCORE_SOMEIP_PEER__/${SCORE_SOMEIP_PEER}/g" "$INTEROP/vsomeip_config.json" > "$destination"
  else
    cp "$INTEROP/vsomeip_config.json" "$destination"
  fi
  python3 -m json.tool "$destination" >/dev/null || { log "ERROR: rendered stack config is not JSON"; return 1; }
  if grep -q '__SCORE_SOMEIP_PEER__' "$destination"; then
    log "ERROR: peer placeholder survived the render"; return 1
  fi
  log "stack config rendered with SCORE_SOMEIP_PEER=$SCORE_SOMEIP_PEER"
  return 0
}

# The catalog registers the type the broker publishes. Soong only sees a module
# declared in the directory's Android.bp, so the module is appended there (the
# kind is CATALOG_MODULE_KIND; scripts/probe_aosp_tree.sh prints what the tree's
# own catalog uses).
register_catalog_module() {
  python3 - "$CATALOG_BP" "$CATALOG_MODULE" "$CATALOG_MODULE_KIND" <<'PY' || return 1
import os, sys
path, module, kind = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read() if os.path.exists(path) else ""
if f'name: "{module}"' in text:
    print("catalog module already registered")
    sys.exit(0)
add = (
    f"\n// DE4SDV INC-DRIVING-001 slice 10b: the type of the driving operational\n"
    f"// state publication (staged by ivi-observer/scripts/stage_sdv_core_interop.sh).\n"
    f"{kind} {{\n"
    f"    name: \"{module}\",\n"
    f"    srcs: [\"de4sdv_driving_operational_state.proto\"],\n"
    f"    sdk_version: \"system_current\",\n"
    f"    owner: \"de4sdv\",\n"
    f"}}\n"
)
open(path, "a").write(add)
print(f"catalog module {module} appended to {path}")
PY
}

check() {
  local rc=0 f
  [ -d "$SAMPLES" ] || { log "AOSP samples tree not found at $SAMPLES (set AOSP_TOP)"; return 1; }
  for f in "$INTEROP/vsomeip_config.json" "$INTEROP/de4sdv_driving_operational_state.vsidl" \
           "$INTEROP/someip_type_definition.textproto" \
           "$INTEROP/de4sdv_driving_operational_state_bundle.vsidl" \
           "$INTEROP/broker_acl_append.textproto" \
           "$INTEROP/acl/ivi_observer_subscriber.textproto" \
           "$INTEROP/acl/ivi_broker_object_policy.textproto" \
           "$CONTRACT/de4sdv_driving_operational_state.proto"; do
    [ -f "$f" ] || { log "ERROR: missing artifact $f"; rc=1; }
  done
  local stack_config; stack_config="$(find_stack_config)" || { log "ERROR: no vsomeip_config.json source in the tree"; rc=1; }
  [ -n "${stack_config:-}" ] && log "stack config source: $stack_config"

  # The mapping must be the generator's output, not a hand edit.
  python3 "$SLICE/scripts/gen_someip_vsidl.py" --check || rc=1
  grep -q "someip_service_id: 0x4df0" "$INTEROP/de4sdv_driving_operational_state.vsidl" || { log "ERROR: mapping service id"; rc=1; }
  local reflection fields zero
  reflection="$(grep -c 'message_translation_mode: REFLECTION' "$INTEROP/de4sdv_driving_operational_state.vsidl")"
  [ "$reflection" = 3 ] || { log "ERROR: $reflection REFLECTION events, expected 3"; rc=1; }
  fields="$(grep -c 'field_name:' "$INTEROP/de4sdv_driving_operational_state.vsidl")"
  [ "$fields" = "$((FIELD_COUNT * 3))" ] || { log "ERROR: $fields field_names, expected $((FIELD_COUNT * 3))"; rc=1; }
  zero="$(grep -c 'length_field_size: ZERO' "$INTEROP/de4sdv_driving_operational_state.vsidl")"
  [ "$zero" = 3 ] || { log "ERROR: $zero structs without a struct length field, expected 3"; rc=1; }

  # No carrier: the type is the message, not bytes. Match a declaration, not the
  # comment in the header that names option A.
  if grep -Eq '^[[:space:]]*bytes[[:space:]]+[A-Za-z_]' "$CONTRACT/de4sdv_driving_operational_state.proto"; then
    log "ERROR: the contract proto declares a bytes carrier (that is option A)"; rc=1
  fi
  grep -q "message $TYPE_NAME" "$CONTRACT/de4sdv_driving_operational_state.proto" || { log "ERROR: contract message name"; rc=1; }
  grep -q "message: \"$MESSAGE_NAME\"" "$INTEROP/broker_acl_append.textproto" || { log "ERROR: broker ACL message"; rc=1; }
  grep -q "message: \"$MESSAGE_NAME\"" "$INTEROP/acl/ivi_observer_subscriber.textproto" || { log "ERROR: subject ACL message"; rc=1; }
  grep -q "message: \"$MESSAGE_NAME\"" "$INTEROP/acl/ivi_broker_object_policy.textproto" || { log "ERROR: object policy message"; rc=1; }
  [ "$rc" = 0 ] && log "check: ok"
  return "$rc"
}

stage() {
  local stack_config; stack_config="$(find_stack_config)" \
    || { log "ERROR: the stack vsomeip_config.json source was not found in the tree"; return 1; }
  mkdir -p "$BACKUP" "$CATALOG_DIR"
  local f name
  for f in "$BROKER_VSIDL" "$BROKER_ACL" "$stack_config" "$CATALOG_BP"; do
    name="$(basename "$f")"
    [ -f "$BACKUP/$name" ] || { [ -f "$f" ] && cp -p "$f" "$BACKUP/$name"; }
  done

  # 1. The typed message, its SomeIpStruct and the mapping.
  cp "$CONTRACT/de4sdv_driving_operational_state.proto" "$CATALOG_DIR/"
  cp "$INTEROP/someip_type_definition.textproto" "$CATALOG_DIR/"
  cp "$INTEROP/de4sdv_driving_operational_state.vsidl" "$CATALOG_DIR/"

  # 2. The catalog registers the type, so vsidlc can resolve the publication.
  register_catalog_module || { log "ERROR: could not register the catalog module"; return 1; }

  # 3. The broker ACL gains the publish permission, once.
  if ! grep -q "$TOPIC" "$BROKER_ACL" 2>/dev/null; then
    cat "$INTEROP/broker_acl_append.textproto" >> "$BROKER_ACL"; log "appended the broker publish ACL"
  else
    log "broker publish ACL already present"
  fi

  # 4. The broker's bundle declares the publisher of the new type, at the anchor
  #    of an existing publisher entry (the AEBS bench's insertion). The name is
  #    the fully qualified message, because it lives in another package than the
  #    declaration; RUNBOOK step 4 names the bare-name variant if vsidlc wants one.
  python3 - "$BROKER_VSIDL" "$MESSAGE_NAME" <<'PY' || { log "ERROR: could not insert the broker.vsidl publisher entry"; return 1; }
import re, sys
path, message = sys.argv[1], sys.argv[2]
text = open(path).read()
if f'message: "{message}"' in text:
    sys.exit(0)
m = re.search(r'\n(\s*)publisher \{\n\s*message: "[^"]+"\n\s*\}\n', text)
if not m:
    sys.stderr.write("no existing publisher entry to anchor to\n"); sys.exit(1)
indent = m.group(1)
add = indent + "publisher {\n" + indent + '  message: "' + message + '"\n' + indent + "}\n"
open(path, "w").write(text[:m.end()] + add + text[m.end():])
print(f"broker.vsidl publisher inserted: {message}")
PY

  # 5. The DE4SDV stack configuration (offers nothing; peer pinned and secure).
  render_stack_config "$stack_config" || return 1
  echo "$stack_config" > "$RUN_DIR/.stack_config_path"

  log "staged the overlay into $CATALOG_DIR (backup in $BACKUP)"
  log "NOTE: whether the image-built mapping is read without a vsidl_schemas_path"
  log "      change is an S1 check (the AEBS bench left it open, GAP-MW-038)."
}

build() {
  stage || return 1
  local free; free="$(disk_free_gb)"
  log "disk free: ${free} GB (floor ${DISK_FLOOR_GB})"
  [ "$free" -ge "$DISK_FLOOR_GB" ] || { log "ERROR: disk below the floor; prune first (runbook step 2)"; return 1; }

  local build_rc=0
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${CORE_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m
  ) 2>&1 | tail -5 || build_rc=1
  [ "${PIPESTATUS[0]:-0}" = 0 ] || build_rc=1
  [ "$build_rc" = 0 ] || { log "ERROR: the SDV Core build failed; no identity record is written"; return 1; }

  local product_out="$AOSP_TOP/out/target/product/$CORE_PRODUCT" stack_config manifest_r img
  stack_config="$(cat "$RUN_DIR/.stack_config_path" 2>/dev/null)"
  manifest_r="$(cd "$AOSP_TOP" && repo manifest -r 2>/dev/null)"
  {
    echo "# SDV Core image build $(date -u +%FT%T.%NZ)"
    echo "target: ${CORE_PRODUCT}-${RELEASE}-${VARIANT}, boot mode UNLOCKED"
    echo "option: B (SOME/IP struct -> REFLECTION -> $MESSAGE_NAME)"
    echo "score_someip_peer: ${SCORE_SOMEIP_PEER}"
    if [ -n "$manifest_r" ]; then printf '%s' "$manifest_r" | sha256sum | sed 's/^/manifest_r_sha256: /'
    else echo "manifest_r_sha256: ERROR repo manifest -r produced nothing"; fi
    ( cd "$AOSP_TOP" && repo status 2>/dev/null | sed 's/^/repo_status: /' | head -40 )
    ( cd "$AOSP_TOP/device/google/sdv" 2>/dev/null && git diff | sha256sum | sed 's/^/device_google_sdv_diff_sha256: /' )
    grep -m1 ro.build.fingerprint "$product_out/system/build.prop" 2>/dev/null \
      || grep -m1 ro.system.build.fingerprint "$product_out/system/build.prop" 2>/dev/null
    for img in super.img vbmeta.img boot.img init_boot.img vendor_boot.img; do
      [ -f "$product_out/$img" ] && sha256sum "$product_out/$img"
    done
    echo "overlay inputs (at their destinations):"
    sha256sum "$CATALOG_DIR/de4sdv_driving_operational_state.proto" \
      "$CATALOG_DIR/someip_type_definition.textproto" \
      "$CATALOG_DIR/de4sdv_driving_operational_state.vsidl" \
      "$CATALOG_BP" "$BROKER_VSIDL" "$BROKER_ACL" ${stack_config:+"$stack_config"} 2>/dev/null
  } > "$RUN_DIR/core-image-identity.txt"
  log "recorded the build identity in $RUN_DIR/core-image-identity.txt"
}

revert() {
  local stack_config name
  stack_config="$(cat "$RUN_DIR/.stack_config_path" 2>/dev/null)"
  for name in broker.vsidl someip_acl.textproto vsomeip_config.json Android.bp; do
    [ -f "$BACKUP/$name" ] || continue
    case "$name" in
      broker.vsidl) cp -p "$BACKUP/$name" "$BROKER_VSIDL" ;;
      someip_acl.textproto) cp -p "$BACKUP/$name" "$BROKER_ACL" ;;
      vsomeip_config.json) [ -n "$stack_config" ] && cp -p "$BACKUP/$name" "$stack_config" ;;
      Android.bp) cp -p "$BACKUP/$name" "$CATALOG_BP" ;;
    esac
    log "restored $name"
  done
  if [ -d "$CATALOG_DIR" ]; then
    rm -f -- "$CATALOG_DIR/de4sdv_driving_operational_state.proto" \
             "$CATALOG_DIR/someip_type_definition.textproto" \
             "$CATALOG_DIR/de4sdv_driving_operational_state.vsidl"
    # If the catalog's Android.bp was created by this script, there was no backup.
    if [ ! -f "$BACKUP/Android.bp" ]; then rm -f -- "$CATALOG_BP"; fi
    rmdir "$CATALOG_DIR" 2>/dev/null || true
  fi
  log "reverted; rebuild the base image with: lunch ${CORE_PRODUCT}-${RELEASE}-${VARIANT}; m"
}

case "${1:-}" in
  check) check ;;
  stage) stage ;;
  build) build ;;
  revert) revert ;;
  *) echo "usage: $0 {check|stage|build|revert}" >&2; exit 2 ;;
esac
