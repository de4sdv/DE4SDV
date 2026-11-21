#!/bin/bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): P10-3's injected warning requests on the S-CORE host
# (ENTRY_SCORE_INJECT of session/entrypoints.env; contract in session/README.md "Entry-point contracts").
#
#   inject_warning_requests.sh <out>
#
# Runs the test publisher (ivi-warning/injector, staged as $DA_STAGE/bin/warning_injector) on the candidate's
# mw::com event de4sdv/driver_assistance/warning_request, with the sequence $DA_INJECT_SEQUENCE (default
# ivi-warning/injector/config/p10_3_sequence.txt). gatewayd and someipd carry each request to the guests as they
# will carry the candidate's. Evidence of the path, not of the candidate (brief R1).
#
# Needs the S-CORE side up in mode path (start_score_side.sh <out> none): the candidate's process offers the same
# instance, so it must not run. Writes into <out>: warning_injector.jsonl (each send with the S-CORE host's real
# and monotonic time before and after it), the sequence, the clocks and their synchronization before and after
# (brief R9: the IVI receives on its own clock, the session sets it just before the window and records the bound),
# and inputs.sha256 of the binary, the manifest and the sequence.
#
# Exit status: the publisher's (0 every send went out; 3 bad sequence; 4 offer failed; 5 a send failed); 2 usage;
# 9 the S-CORE side is not up in mode path.
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH=$(cd -- "$HERE/../.." && pwd)
# shellcheck source=../../score-path/scripts/lib_score_side.sh
. "$BENCH/score-path/scripts/lib_score_side.sh"

OUT=${1:?usage: inject_warning_requests.sh <out>}
: "${DA_INJECT_SEQUENCE:=$BENCH/ivi-warning/injector/config/p10_3_sequence.txt}"
: "${DA_INJECT_LEAD_IN_S:=5}"
: "${DA_INJECT_TAIL_S:=2}"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/inject_warning_requests.log") 2>&1

refuse() { ss_log "REFUSED: $*"; exit 9; }
[ "$(ss_state STATE)" = up ] || refuse "the S-CORE side is not up ($SCORE_SIDE_STATE)"
[ "$(ss_state MODE)" = path ] || refuse "the S-CORE side runs in mode $(ss_state MODE): start it with carla host none"
ss_alive "$(ss_state LM_PID)" || refuse "its Launch Manager (pid $(ss_state LM_PID)) no longer runs"
for name in identity_recorder someipd gatewayd; do
  [ -n "$(ss_pids_of "$name")" ] || refuse "$name does not run"
done
[ -z "$(ss_pids_of vision_pilot)" ] || refuse "the candidate's process runs: it offers the same warning-request instance"
BIN=$DA_STAGE/bin/warning_injector
MANIFEST=$DA_STAGE/config/mw_com_config_warning_injector.json
[ -x "$BIN" ] || refuse "no test publisher at $BIN (the bundle's bin/warning_injector)"
[ -f "$MANIFEST" ] || refuse "no manifest at $MANIFEST"
[ -f "$DA_INJECT_SEQUENCE" ] || refuse "no sequence at $DA_INJECT_SEQUENCE"

cp "$DA_INJECT_SEQUENCE" "$OUT/sequence.txt"
sha256sum "$BIN" "$MANIFEST" "$DA_INJECT_SEQUENCE" > "$OUT/inputs.sha256"
ss_clock_record > "$OUT/clock_before.txt"
ss_log "injecting $(grep -c -E '^[[:space:]]*[0-9]' "$DA_INJECT_SEQUENCE") requests from $DA_INJECT_SEQUENCE" \
  "after a lead-in of ${DA_INJECT_LEAD_IN_S} s"
# as root, like the other processes of the S-CORE path (one uid on the bench VM, launch-manager/README.md)
$DA_SUDO env MW_COM_CONFIG="$MANIFEST" "$BIN" --sequence "$OUT/sequence.txt" --log "$OUT/warning_injector.jsonl" \
  --lead-in-s "$DA_INJECT_LEAD_IN_S" --tail-s "$DA_INJECT_TAIL_S"
RC=$?
ss_clock_record > "$OUT/clock_after.txt"
[ -n "$DA_SUDO" ] && $DA_SUDO chown "$(id -u):$(id -g)" "$OUT/warning_injector.jsonl" 2>/dev/null
sent=$(grep -c '"event":"out.warning_request".*"ok":true' "$OUT/warning_injector.jsonl" 2>/dev/null || true)
ss_log "test publisher exit $RC, $sent requests sent"
exit "$RC"
