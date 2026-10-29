#!/usr/bin/env bash
# Provision the IVI frame relay on the IVI VM before the first case (model
# next action step 5). The relay binary and its init file come from the relay
# lane; the bench takes them as inputs (set RELAY_BIN and RELAY_RC). The SD
# agent reads the ACLs only at its start and exits if a second file names one
# subject, so this installs exactly one ACL file, then reboots the IVI VM.
#
#   provision_ivi_relay.sh install    one ACL, the relay binary and its init file, port 4731, then a reboot
#   provision_ivi_relay.sh remove     remove what install added, then a reboot (the undo)
#
# Interfaces the bench needs from the relay lane (named, not assumed):
#   RELAY_BIN   path to the built relay binary        (default: looks in the IVI product tree)
#   RELAY_RC    path to the relay's init .rc file      (installed under /system/etc/init)
#   RELAY_SUBJECT_PACKAGE / RELAY_SUBJECT_BUNDLE   the relay's authz subject (its ACL path)
#   The relay sets the ingress frame-server port property to 4731 itself; this
#   script also sets it, so a run records the value whichever sets it first.
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
S=("$ADB" -s "$IVI_ADB")
ACL_SRC="$HERE/../aosp-overlay/ivi-acl/relay_subscriber.textproto"
: "${RELAY_SUBJECT_PACKAGE:=org.de4sdv.framerelay}"
: "${RELAY_SUBJECT_BUNDLE:=FrameRelay}"
: "${RELAY_BIN:=$AOSP_TOP/out/target/product/$IVI_PRODUCT/system/bin/de4sdv_someip_receiver}"
: "${RELAY_RC:=}"
ACL_DIR="/product/etc/sdv_authz_acls/${RELAY_SUBJECT_PACKAGE}"
ACL_DST="${ACL_DIR}/${RELAY_SUBJECT_BUNDLE}.textproto"

_wait_boot() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" wait-for-device
  local i; for i in $(seq 1 90); do
    [ "$("${S[@]}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && { log "IVI booted"; return 0; }
    sleep 2
  done; log "IVI boot timed out"; return 1
}

install() {
  require_cmd "$ADB" || return 1
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true; sleep 2; "${S[@]}" wait-for-device
  "${S[@]}" disable-verity >/dev/null 2>&1 || true
  "${S[@]}" reboot; _wait_boot || return 1
  "${S[@]}" root >/dev/null 2>&1 || true; "${S[@]}" remount 2>&1 | tail -1

  # Exactly one ACL file for the relay's subject. Remove any stale sibling in
  # that subject directory first, so a second file cannot make the SD agent exit.
  "${S[@]}" shell "mkdir -p '$ACL_DIR'; for f in '$ACL_DIR'/*.textproto; do [ -f \"\$f\" ] && [ \"\$f\" != '$ACL_DST' ] && rm -f \"\$f\"; done" 2>/dev/null || true
  "${S[@]}" push "$ACL_SRC" "$ACL_DST" 2>&1 | tail -1
  "${S[@]}" shell "chmod 755 '$ACL_DIR'; chmod 644 '$ACL_DST'"
  local count; count="$("${S[@]}" shell "ls '$ACL_DIR'/*.textproto 2>/dev/null | wc -l" | tr -d '\r')"
  [ "$count" = 1 ] || { log "ERROR: $count ACL files for the subject; the SD agent needs exactly one"; return 1; }

  # The relay binary and its init file, on the instance overlay for the bench.
  if [ -f "$RELAY_BIN" ]; then
    "${S[@]}" push "$RELAY_BIN" /system/bin/ 2>&1 | tail -1
    "${S[@]}" shell "chmod 755 /system/bin/$(basename "$RELAY_BIN")"
  else
    log "WARNING: relay binary not at $RELAY_BIN; set RELAY_BIN (built by the relay lane)"
  fi
  if [ -n "$RELAY_RC" ] && [ -f "$RELAY_RC" ]; then
    "${S[@]}" push "$RELAY_RC" /system/etc/init/ 2>&1 | tail -1
  else
    log "NOTE: no RELAY_RC given; the relay's init file must be in the image or set RELAY_RC"
  fi

  # The ingress frame-server port (ASM-MW-029); the relay also sets the host to loopback.
  "${S[@]}" shell "setprop de4sdv.aebs.frame_server.port $RELAY_LOOPBACK_PORT"
  "${S[@]}" shell "sync"
  log "provisioned the relay; rebooting so the SD agent reads the one ACL and the relay starts"
  "${S[@]}" reboot; _wait_boot || return 1
  log "set the IVI VM clock next: scripts/set_ivi_clock.sh setup"
}

remove() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true; "${S[@]}" remount >/dev/null 2>&1 || true
  "${S[@]}" shell "rm -f '$ACL_DST' /system/bin/$(basename "$RELAY_BIN") ${RELAY_RC:+/system/etc/init/$(basename "$RELAY_RC")}; rmdir '$ACL_DIR' 2>/dev/null" 2>/dev/null || true
  log "removed the relay provisioning; rebooting"
  "${S[@]}" reboot; _wait_boot || true
}

case "${1:-}" in
  install) install ;;
  remove) remove ;;
  *) echo "usage: $0 {install|remove}" >&2; exit 2 ;;
esac
