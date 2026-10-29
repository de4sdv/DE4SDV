#!/usr/bin/env bash
# Provision the IVI frame relay on the IVI VM before the first case (model
# next action step 5). The relay binary, its init file, its logcat tag and its
# authz subject come from the relay lane (#439); they are required inputs with
# no defaults, and the script fails fast when any is unset, so it never
# provisions the wrong subject or pushes nothing (review R6/R10/R23).
#
#   provision_ivi_relay.sh install    install the ACLs, the binary and init, reboot, and check
#   provision_ivi_relay.sh remove     remove what install added, then a reboot (the undo)
#
# Required (export before running; see the README for #439's values):
#   RELAY_BIN RELAY_RC RELAY_LOGCAT_TAG
#   RELAY_SUBJECT_PACKAGE RELAY_SUBJECT_BUNDLE RELAY_SUBJECT_INSTANCE
#
# The SD agent reads the ACLs only at its start and exits if a second file
# names one subject, so this installs exactly one file per subject, across
# /product, /system and /vendor, then reboots the IVI VM. A cross-VM
# subscriber also needs the remote broker's object policy, so this installs
# that too (the feasibility runs did). The relay sets the ingress port and
# host from its own init file on boot, so this does not setprop them (a plain
# setprop would not survive the reboot).
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
require_relay_inputs || exit 2
S=("$ADB" -s "$IVI_ADB")
ACL_SRC="$HERE/../aosp-overlay/ivi-acl/relay_subscriber.textproto"
BROKER_POLICY_SRC="$HERE/../aosp-overlay/ivi-acl/broker_object_policy.textproto"
SUBJECT_DIR="/product/etc/sdv_authz_acls/${RELAY_SUBJECT_PACKAGE}"
SUBJECT_DST="${SUBJECT_DIR}/${RELAY_SUBJECT_BUNDLE}.textproto"
BROKER_DIR="/product/etc/sdv_authz_acls/${BROKER_PACKAGE}"
BROKER_DST="${BROKER_DIR}/${BROKER_BUNDLE}.textproto"
ACL_ROOTS="/product/etc/sdv_authz_acls /system/etc/sdv_authz_acls /vendor/etc/sdv_authz_acls /system_ext/etc/sdv_authz_acls"

_wait_boot() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" wait-for-device
  local i; for i in $(seq 1 90); do
    [ "$("${S[@]}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && { log "IVI booted"; return 0; }
    sleep 2
  done; log "IVI boot timed out"; return 1
}

_reboot() {
  "${S[@]}" reboot
  "${S[@]}" wait-for-disconnect 2>/dev/null || sleep 5
  _wait_boot
}

# Exactly one ACL file for a subject across all ACL roots (the SD agent exits
# on a second file for one subject).
_one_file_per_subject() {
  local dupes
  dupes="$("${S[@]}" shell "find $ACL_ROOTS -name '*.textproto' 2>/dev/null | sed 's#.*/sdv_authz_acls/##' | sort | uniq -d" | tr -d '\r')"
  if [ -n "$dupes" ]; then log "ERROR: duplicate ACL files for a subject: $dupes"; return 1; fi
}

install() {
  require_cmd "$ADB" || return 1
  [ -f "$RELAY_BIN" ] || { log "ERROR: RELAY_BIN not found at $RELAY_BIN"; return 1; }
  [ -f "$RELAY_RC" ] || { log "ERROR: RELAY_RC not found at $RELAY_RC"; return 1; }
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true; sleep 2; "${S[@]}" wait-for-device
  "${S[@]}" disable-verity >/dev/null 2>&1 || true
  _reboot || return 1
  "${S[@]}" root >/dev/null 2>&1 || true; "${S[@]}" remount 2>&1 | tail -1

  # Remove any stale sibling in the two subject directories, then install one each.
  "${S[@]}" shell "mkdir -p '$SUBJECT_DIR' '$BROKER_DIR'"
  "${S[@]}" shell "for f in '$SUBJECT_DIR'/*.textproto; do [ -f \"\$f\" ] && [ \"\$f\" != '$SUBJECT_DST' ] && rm -f \"\$f\"; done" 2>/dev/null || true
  "${S[@]}" push "$ACL_SRC" "$SUBJECT_DST" 2>&1 | tail -1
  "${S[@]}" push "$BROKER_POLICY_SRC" "$BROKER_DST" 2>&1 | tail -1
  "${S[@]}" shell "chmod 755 '$SUBJECT_DIR' '$BROKER_DIR'; chmod 644 '$SUBJECT_DST' '$BROKER_DST'; sync"
  _one_file_per_subject || return 1

  # The relay binary and its init file.
  "${S[@]}" push "$RELAY_BIN" /system/bin/ 2>&1 | tail -1
  "${S[@]}" shell "chmod 755 /system/bin/$(basename "$RELAY_BIN")"
  "${S[@]}" push "$RELAY_RC" /system/etc/init/ 2>&1 | tail -1
  "${S[@]}" shell sync
  log "provisioned; rebooting so the SD agent reads the ACLs and the relay starts (it sets the ingress port and host)"
  _reboot || return 1

  # Post-boot checks.
  "${S[@]}" root >/dev/null 2>&1 || true
  log "sd_agent=$("${S[@]}" shell pidof sdv_sd_agent_no_vpm | tr -d '\r') gateway=$("${S[@]}" shell pidof sdv_gateway | tr -d '\r')"
  log "relay init.svc=$("${S[@]}" shell getprop init.svc.$(basename "$RELAY_BIN") | tr -d '\r')"
  log "frame_server.port=$("${S[@]}" shell getprop de4sdv.aebs.frame_server.port | tr -d '\r') host=$("${S[@]}" shell getprop de4sdv.aebs.frame_server.host | tr -d '\r')"
  "${S[@]}" shell "ls -Z /system/bin/$(basename "$RELAY_BIN")" | tr -d '\r' | sed 's/^/binary: /'
  "${S[@]}" shell "logcat -d -t 2000 2>/dev/null | grep -m1 '\"event\":\"subscribed\"'" | tr -d '\r' | sed 's/^/relay: /' \
    || log "NOTE: no 'subscribed' line yet; the relay's start diagnostic reports an ACL or mapping fault after 30 s"
  log "set the IVI VM clock next: scripts/set_ivi_clock.sh setup"
}

remove() {
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "${S[@]}" root >/dev/null 2>&1 || true; "${S[@]}" remount >/dev/null 2>&1 || true
  "${S[@]}" shell "rm -f '$SUBJECT_DST' '$BROKER_DST' /system/bin/$(basename "$RELAY_BIN") /system/etc/init/$(basename "$RELAY_RC"); rmdir '$SUBJECT_DIR' 2>/dev/null; sync" 2>/dev/null || true
  log "removed the relay provisioning; rebooting"
  _reboot || true
}

case "${1:-}" in
  install) install ;;
  remove) remove ;;
  *) echo "usage: $0 {install|remove}" >&2; exit 2 ;;
esac
