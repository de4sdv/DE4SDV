#!/bin/bash
# One run on the simulator host (entry ENTRY_SIM_RUN; session/README.md "Entry-point contracts").
#
#   run_scenario.sh <out_dir> <scenario> <setting>
#     SC-DRIVING-012 20kmh   a run of the setting SC-DRIVING-012@20 (da_world_side.py run)
#     SC-DRIVING-013 SC-DRIVING-013@30   session kind s1: a run of each setting id of s1_runs.tsv (012 to 015)
#     SC-DRIVING-012 stop    the stop run (world-side/scenarios.py STOP_RUN; session/entrypoints.env S1_STOP_*)
#     ASM-DRIVING-006 20kmh  the steering calibration on that setting's road and vehicle (calib-steer)
# A setting on a site (SC-DRIVING-014, -015) starts where its site puts it; the session's road is not used for it.
#
# The handshake with the session (both files inside <out_dir>):
#   <out>/simulator/ready.json  written once the hero, its camera (and the target) stand; the world does not tick
#   <out>/go                    the session's: the S-CORE side runs; the run's first paced tick follows
#   <out>/simulator/run_end.json  written when the run ended (contact, at rest, cap); the world keeps ticking
#   <out>/release               the session's: the S-CORE side is stopped; the world leaves synchronous mode
# Exit 0 when the run completed (whatever its entry checks say); 2 a bench error (simulator/error.json), the go
# file missing after GO_WAIT_S included; 64 bad arguments. Its world record, setting record, entry checks and
# tick_times.csv are in <out>/simulator/.
# env: see common.sh (DA_ACKERMANN_GAINS among them); GO_WAIT_S (900), RELEASE_WAIT_S (300), RUN_S (the setting's
#      run cap).
set -uo pipefail
OUT=${1:?out dir}; SCENARIO=${2:?scenario}; SETTING_ARG=${3:?setting}
mkdir -p "$OUT"
# shellcheck source=common.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
case "$SCENARIO" in
  SC-DRIVING-012|SC-DRIVING-013|SC-DRIVING-014|SC-DRIVING-015) CMD=run ;;
  ASM-DRIVING-006) CMD=calib-steer ;;
  *) echo "FAIL unknown scenario $SCENARIO (SC-DRIVING-012 to -015, or ASM-DRIVING-006)"; exit 64 ;;
esac
SETTING=$(ws_setting "$SCENARIO" "$SETTING_ARG")
START=$(ws_read_start "$OUT") || exit 2
rm -f "$OUT/go" "$OUT/release"
EXTRA=(); [ -n "${RUN_S:-}" ] && EXTRA+=(--run-s "$RUN_S")
ws_side "$CMD" --setting "$SETTING" --start "$START" --run-dir "$OUT" \
  --go-file "$OUT/go" --go-wait-s "${GO_WAIT_S:-900}" --release-file "$OUT/release" \
  --release-wait-s "${RELEASE_WAIT_S:-300}" "${EXTRA[@]}"; rc=$?
[ "$rc" = 0 ] && echo "RUN_DONE $SCENARIO $SETTING" || echo "FAIL $CMD rc=$rc"
exit "$rc"
