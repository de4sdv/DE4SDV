#!/usr/bin/env bash
# Shared settings of the INC-DRIVING-001 typed observation path (slice 10b).
#
# Source it from the other scripts: `. "$(dirname "$0")/bench_env.sh"`. It sets
# names, ids and paths only; it starts nothing and touches no VM. Every value can
# be overridden from the environment. The ids are the ICD's (interfaces/ICD.md
# section 3); tests/test_contract_and_encoding.py holds these files to them.
set -u

# --- the AOSP tree of the aaos-build VM (same tree the AEBS bench uses) ------
: "${AOSP_TOP:=$HOME/aosp}"
: "${AOSP_HOST_OUT:=$AOSP_TOP/out/host/linux-x86}"
: "${CORE_PRODUCT:=sdv_core_cf}"
: "${IVI_PRODUCT:=sdv_ivi_cf}"
: "${RELEASE:=cp2a}"
: "${VARIANT:=eng}"
: "${ADB:=$AOSP_HOST_OUT/bin/adb}"
: "${CVD:=}"
if [ -z "$CVD" ]; then
  if [ -x "$AOSP_HOST_OUT/bin/cvd" ]; then CVD="$AOSP_HOST_OUT/bin/cvd"; else CVD="$(command -v cvd || true)"; fi
fi

# --- the two guests (cvd instance numbers of the bench, adb 6521/6522) ------
: "${CORE_ADB:=0.0.0.0:6521}"
: "${IVI_ADB:=0.0.0.0:6522}"
: "${CORE_ADDR:=192.168.98.3}"
: "${IVI_ADDR:=192.168.98.118}"
: "${HOST_ADDR:=192.168.98.1}"

# The S-CORE host's address on the VXLAN segment: the peer the SDV Core stack
# pins for service 0x4df0 and the address its acceptance rule allows. On the
# three-host bench this is NOT the guest host: the runbook's step 4 reads it off
# the S-CORE host's VXLAN interface before the build. No default: the staging
# script refuses to render the stack config without it (a silent 192.168.98.1
# would pin the guest host and the core would never accept the real offer).
: "${SCORE_SOMEIP_PEER:=}"

# --- the contract (ICD section 3) -------------------------------------------
: "${SERVICE_ID:=0x4df0}"
: "${INSTANCE_ID:=0x0001}"
: "${EVENT_GROUP:=0x0001}"
: "${EVENT_PLAN:=0x8001}"
: "${EVENT_VEHICLE_STATE:=0x8002}"
: "${EVENT_HEALTH:=0x8003}"
: "${SOMEIP_RELIABLE_PORT:=30510}"
: "${SD_GROUP:=224.0.0.0}"
: "${SD_PORT:=30490}"

# --- the Data Tunnel side ----------------------------------------------------
# TOPIC is the base name. MAPPING_VARIANT=three (default) registers one service unit
# per event, SERVICE_UNITS below; MAPPING_VARIANT=one registers all three events on
# the one unit TOPIC (interop/variants/, not decidable from the AOSP source: see the
# generator header). The service unit names are what the ACLs call `topic`.
: "${TOPIC:=de4sdv-driving-operational-state}"
: "${MAPPING_VARIANT:=three}"
if [ "$MAPPING_VARIANT" = one ]; then
  : "${SERVICE_UNITS:=$TOPIC}"
else
  : "${SERVICE_UNITS:=$TOPIC-plan $TOPIC-vehicle-state $TOPIC-health}"
fi
# The typed VSIDL message (the SOME/IP struct the broker translates): the topic's type, the broker's
# publication type, the app's parser and the ACLs' `message` are all this name.
: "${TYPE_PACKAGE:=de4sdv.driving.v1}"
: "${TYPE_NAME:=DrivingOperationalState}"
: "${MESSAGE_NAME:=$TYPE_PACKAGE.$TYPE_NAME}"
: "${BROKER_PACKAGE:=com.android.sdv.someip}"
: "${BROKER_BUNDLE:=SomeIpBroker}"

# --- the observer (IVI) ------------------------------------------------------
: "${OBSERVER_PACKAGE:=org.de4sdv.drivingstate}"
: "${OBSERVER_BUNDLE:=DrivingStateObserver}"
: "${OBSERVER_APP:=De4sdvDrivingStateObserver}"
: "${OBSERVER_TESTS:=De4sdvDrivingStateObserverTests}"
: "${OBSERVER_LOGCAT_TAG:=DE4SDV_DRIVING_STATE}"
: "${OBSERVER_RECORD:=observer.jsonl}"
# A vendor privileged app (the INC-AEBS-010 module shape: the Gateway Java client's
# SDK library is a vendor java_sdk_library), so Soong installs it to vendor/priv-app.
: "${OBSERVER_APK:=$AOSP_TOP/out/target/product/$IVI_PRODUCT/vendor/priv-app/$OBSERVER_APP/$OBSERVER_APP.apk}"
: "${OBSERVER_GUEST_DIR:=/vendor/priv-app/$OBSERVER_APP}"
# The Gateway Java client sources the app compiles in (as the AEBS app carries them).
: "${GATEWAY_JAVA_SRC:=$AOSP_TOP/system/software_defined_vehicle/sdv_gateway/libsdvgatewayclient_java/src}"
# The publisher the app subscribes to by name (the SOME/IP broker of the SDV Core VM).
: "${PUBLISHER_UNIT:=$TOPIC}"
# screenrecord's display: empty = the default display, which on sdv_ivi_cf is the
# 1080 x 600 centre display of the earlier recordings. Otherwise a physical id from
# `dumpsys SurfaceFlinger --display-id`.
: "${IVI_DISPLAY_ID:=}"

# --- the DE4SDV tree ---------------------------------------------------------
_BENCH_SCRIPTS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${DE4SDV_ROOT:=$(cd -- "$_BENCH_SCRIPTS/../../../.." && pwd)}"
: "${SLICE_ROOT:=$(cd -- "$_BENCH_SCRIPTS/.." && pwd)}"
: "${INTEROP:=$SLICE_ROOT/interop}"
: "${CONTRACT:=$SLICE_ROOT/contract}"
: "${RUN_DIR:=$SLICE_ROOT/run}"
: "${SAMPLES:=$AOSP_TOP/system/software_defined_vehicle/samples}"

# The catalog the SDV Core VM reads: the typed message and the mapping, in a
# subdirectory of the platform's some_ip catalog with NO Android.bp of its own, as
# catalog/de4sdv_score/ (the earlier, proven increment). The catalog's Android.bp
# already takes every **/*.proto and **/*.vsidl below it (rust_protobuf
# libsomeip_messages_catalog, filegroup someip_catalog_protos); nothing is
# registered. (The release has no proto_library module type at all.)
: "${CATALOG_DIR:=$SAMPLES/some_ip/catalog/de4sdv_driving}"
: "${BROKER_VSIDL:=$SAMPLES/some_ip/catalog/agent/broker.vsidl}"
: "${BROKER_ACL:=$SAMPLES/some_ip/config/broker_apex/someip_acl.textproto}"
# The stack config's source (prebuilt_etc vsomeip_config.json, sub_dir someip,
# vendor: true -> /vendor/etc/someip/vsomeip_config.json).
: "${STACK_CONFIG:=$AOSP_TOP/system/software_defined_vehicle/some_ip/vsomeip_stack/vsomeip_config.json}"
# The smallest build that validates the type and the mapping (RUNBOOK gate G1b):
# vsidl_rc_generator's pdk29 checks over the whole catalog (it writes both the
# broker's VSIDL schemas and the SOME/IP mappings), vsidlc over the same catalog
# (it generates every service bundle's code, the broker's included), the Rust
# compile of every catalog proto, and aprotoc to decode the generated mappings.
: "${G1B_MODULES:=generate_vsidl_files_someip_catalog_protos_with_bp_file vsidlc_someip_catalog_protos_with_bp_file libsomeip_messages_catalog aprotoc}"
: "${BACKUP:=$RUN_DIR/core-image-originals}"
: "${DISK_FLOOR_GB:=32}"

# --- the ACL roots the IVI SD agent reads -----------------------------------
: "${ACL_ROOTS:=/product/etc/sdv_authz_acls /system/etc/sdv_authz_acls /vendor/etc/sdv_authz_acls /system_ext/etc/sdv_authz_acls}"
: "${ACL_ROOT:=/product/etc/sdv_authz_acls}"

log() { printf '%s %s\n' "$(date -u +%FT%T.%NZ)" "$*"; }

require_cmd() {
  local missing=0 cmd
  for cmd in "$@"; do command -v "$cmd" >/dev/null 2>&1 || { log "MISSING command: $cmd"; missing=1; }; done
  return $missing
}

# adb to one guest, with the serial explicit on every call.
core_adb() { "$ADB" -s "$CORE_ADB" "$@"; }
ivi_adb() { "$ADB" -s "$IVI_ADB" "$@"; }

wait_boot() { # <adb function> <name>
  local call="$1" name="$2" tries=120
  while [ "$tries" -gt 0 ]; do
    if "$call" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' | grep -qx 1; then
      log "$name booted"; return 0
    fi
    try_sleep=5; sleep "$try_sleep"; tries=$((tries - 1))
  done
  log "ERROR: $name did not reach sys.boot_completed=1"; return 1
}
