#!/bin/bash
# The guests' stop on the guest host (GUEST_STOP_CMD's default), run by the session's exit trap and by the safety
# net before any stop or power-off of the host.
#
#   guest_stop.sh     cvd stop for every group the fleet lists, then the crosvm count; exit 0 only when none is left
#
# It depends on nothing of the guest build kit's records: the kit's smoke_boot.sh checks the images against
# records that are stale since 2026-11-17 and refuses (guest-prep-20261118 report, "tomorrow" item 1). The route
# is the one that report's operator used: cvd stop per group, then no crosvm may be left. The last line is always
#   crosvm_processes_after_stop: <N>     (<N> is "unknown" when pgrep fails; the exit is then 1)
# env: AOSP_TOP (~/aosp), CVD (default: $AOSP_TOP/out/host/linux-x86/bin/cvd, else cvd on PATH),
#      STOP_SETTLE_S (5), STOP_TRIES (2).
set -uo pipefail
: "${AOSP_TOP:=$HOME/aosp}"
CVD=${CVD:-}
if [ -z "$CVD" ]; then
  if [ -x "$AOSP_TOP/out/host/linux-x86/bin/cvd" ]; then CVD=$AOSP_TOP/out/host/linux-x86/bin/cvd
  else CVD=$(command -v cvd || true); fi
fi
# a number only when pgrep answered (rc 0 or 1); a pgrep that errors is "unknown", never 0 (S11)
crosvm() { local n rc; n=$(pgrep -c -x crosvm 2>/dev/null); rc=$?
  if [ "$rc" -le 1 ] && [[ "$n" =~ ^[0-9]+$ ]]; then echo "$n"; else echo unknown; fi; }
groups() {
  [ -n "$CVD" ] || return 0
  "$CVD" fleet 2>/dev/null | python3 -c '
import json, sys
raw = sys.stdin.read(); s = raw.find("{")
if s < 0: raise SystemExit(0)
try: fleet = json.loads(raw[s:])
except ValueError: raise SystemExit(0)
for g in fleet.get("groups", []):
    if g.get("group_name"): print(g["group_name"])
'
}
echo "cvd: ${CVD:-none}; crosvm before: $(crosvm)"
for try in $(seq 1 "${STOP_TRIES:-2}"); do
  for g in $(groups); do
    echo "+ $CVD --group_name=$g stop"
    "$CVD" --group_name="$g" stop 2>&1 | tail -3 || echo "WARNING cvd stop $g returned non-zero"
  done
  sleep "${STOP_SETTLE_S:-5}"
  [ "$(crosvm)" = 0 ] && break
  echo "crosvm still running after try $try"
done
N=$(crosvm)
echo "crosvm_processes_after_stop: $N"
[ "$N" = 0 ]
