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
#   Exit 0 when both passed; 1 at the first failure (verify does not run after a failed install). The steps' logs,
#   the summary lines of this run and the app's identity are copied into <out_dir>.
#
# The app module itself is built beforehand by the guest build script's `ivi` step (an operator step, not part of a
# session). SELinux: IVI_PERMISSIVE=1 (the session's --permissive-ivi, which marks every result of the session
# conditional on a permissive IVI) lets verify set the IVI permissive after the install's reboot; without it the
# guests stay as they boot (Enforcing) and only their mode is recorded.
# env: GUEST_BUILD_SCRIPT (default: the kit's guest-build/build_guests_incremental.sh), AB (~/aaos-build),
#      IVI_PERMISSIVE (0), and the build script's own variables.
set -uo pipefail
OUT=${1:?out dir}; mkdir -p "$OUT"
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH=$(cd -- "$HERE/../.." && pwd)
SCRIPT=${GUEST_BUILD_SCRIPT:-$BENCH/guest-build/build_guests_incremental.sh}
: "${AB:=$HOME/aaos-build}"; LOGS=${LOGS:-$AB/logs}; IDENT=${IDENT:-$AB/identity}
export AB LOGS IDENT   # the build script derives the same defaults; exported so both read one place
export IVI_PERMISSIVE=${IVI_PERMISSIVE:-0}
SUMMARY=$IDENT/b12-summary.txt
[ -f "$SCRIPT" ] || { echo "FAIL no guest build script at $SCRIPT"; exit 1; }
FROM=$(wc -l < "$SUMMARY" 2>/dev/null || echo 0)
echo "guest build script $(sha256sum "$SCRIPT" | cut -d' ' -f1) $SCRIPT; IVI_PERMISSIVE=$IVI_PERMISSIVE"

collect() {
  local f
  for f in "$LOGS/b12-install.log" "$LOGS/b12-verify.log" "$IDENT/ivi-warning-app-identity.txt" \
           "$IDENT/b12-app-logcat.txt"; do
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
