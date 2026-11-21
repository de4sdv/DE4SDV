#!/bin/bash
# The guest host's prepare step of a session (entry ENTRY_GUEST_PREPARE), after guest_up.sh. guest_up.sh creates
# the guests fresh, and fresh groups start as stock guests with an empty /data (guest-prep-20261118 report,
# "tomorrow" item 6), so every session puts the app and its two IVI ACLs on again and reboots the IVI, before any
# window. This is a wrapper over the guest build script's own steps, which it does not change:
#
#   guest_prepare.sh <out_dir>
#     1. build_guests_incremental.sh install   ACLs (the subject grant and the merged broker object policy) and the
#                                              APK into /vendor/priv-app, IVI reboot, PackageManager check, identity
#     2. build_guests_incremental.sh verify    0x4dee, 0x4df0, 0x4df1 in the SDV Core VM's stack config; the app
#                                              (re)started with am start -S; initComms through the gateway; the
#                                              SELinux mode of both guests recorded
#   Exit 0 when both passed; 1 at the first failure (verify does not run after a failed install), and when no
#   session id is set. The steps' logs, the summary lines of this run, the app's identity and logcat lines and
#   verify's output are copied into <out_dir>.
#
# The session is the guest build script's second caller (guest-build/README.md): it calls install and verify
# directly, on guests it created itself, with one B12_DIR per session ($AB/b12-session-<session id>) and none of
# LOGS, IDENT or WORK set. The script derives those under B12_DIR, and refuses (exit 2) any of them inside the
# 2026-11-17 kit's logs/ or identity/. The app module itself is built beforehand by the guest build script's `ivi`
# step (an operator step, not part of a session).
# SELinux: IVI_PERMISSIVE=1 (the session's --permissive-ivi, which marks every result of the session conditional on
# a permissive IVI) lets verify set the IVI permissive after the install's reboot; without it the guests stay as
# they boot (Enforcing) and only their mode is recorded. On a Gateway lookup failure under Enforcing, verify prints
# B12_RERUN_CMD as the command to run next: here, the session again with --permissive-ivi, never a step on its own.
# env: DA_SESSION_ID (set by host_step.sh), GUEST_BUILD_SCRIPT (default: the kit's
#      guest-build/build_guests_incremental.sh), AB (~/aaos-build), B12_DIR (default above), IVI_PERMISSIVE (0),
#      B12_RERUN_CMD (default above), and the build script's own variables except LOGS, IDENT and WORK.
set -uo pipefail
OUT=${1:?out dir}; mkdir -p "$OUT"
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH=$(cd -- "$HERE/../.." && pwd)
SCRIPT=${GUEST_BUILD_SCRIPT:-$BENCH/guest-build/build_guests_incremental.sh}
[ -n "${DA_SESSION_ID:-}" ] || { echo "FAIL guest prepare: no DA_SESSION_ID, so no B12_DIR of this session"; exit 1; }
: "${AB:=$HOME/aaos-build}"
: "${B12_DIR:=$AB/b12-session-$DA_SESSION_ID}"
unset LOGS IDENT WORK   # the build script derives them under B12_DIR
export AB B12_DIR
export IVI_PERMISSIVE=${IVI_PERMISSIVE:-0}
export B12_RERUN_CMD=${B12_RERUN_CMD:-"on the lead host, this session's da_session.sh --kind <its kind> --owner-ok-guest-host --permissive-ivi (a new session; every result conditional on a permissive IVI)"}
SUMMARY=$B12_DIR/identity/b12-summary.txt
[ -f "$SCRIPT" ] || { echo "FAIL no guest build script at $SCRIPT"; exit 1; }
FROM=$(wc -l < "$SUMMARY" 2>/dev/null || echo 0)
echo "guest build script $(sha256sum "$SCRIPT" | cut -d' ' -f1) $SCRIPT; B12_DIR=$B12_DIR; IVI_PERMISSIVE=$IVI_PERMISSIVE"

collect() {
  local f
  for f in "$B12_DIR/logs/b12-install.log" "$B12_DIR/logs/b12-verify.log" \
           "$B12_DIR/identity/ivi-warning-app-identity.txt" "$B12_DIR/identity/b12-app-logcat.txt" \
           "$B12_DIR/work/app-verify.out"; do
    [ -f "$f" ] && cp -f "$f" "$OUT/"
  done
  [ -f "$SUMMARY" ] && tail -n "+$((FROM + 1))" "$SUMMARY" > "$OUT/b12-summary-this-run.txt"
}
for step in install verify; do
  echo "+ bash $SCRIPT $step"
  bash "$SCRIPT" "$step"; rc=$?
  echo "step $step rc=$rc"
  if [ "$rc" != 0 ]; then collect; echo "FAIL guest prepare: $step rc=$rc"; exit 1; fi
done
collect
echo "GUEST_PREPARE_DONE"
