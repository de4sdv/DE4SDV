#!/bin/bash
# The simulator host's calibration runs of a P10-2 session (entry ENTRY_SIM_CALIBRATE), after the warm-up and
# before any S-CORE side start: no candidate and no adapter may run, and both vehicles have role_name
# de4sdv_calibration, which neither attaches to (world-side/README.md "The calibrations").
#
#   calibrate.sh <out_dir> [checkerboard|settings]
#                             exit 0 when both ended; the world side's status (2: bench error) otherwise
#
# The second argument is the session's camera calibration source (da_session.sh --camcal, default checkerboard):
# checkerboard: camera-capture's pre-check of its frame ends the step on a failing frame (--precheck on); settings:
# H.yaml comes from the simulated camera's settings (camera_calibration.py make-h --source settings), so the frame is
# evidence only and its pre-check verdict is recorded without ending the step (--precheck record).
#
# 1. calib-decel (ASM-DRIVING-005): <out>/calib_decel/simulator/calibration_decel.json;
# 2. camera-capture: upstream's checkerboard laid on the road, one front image:
#    <out>/camcal/simulator/{camera_capture.json, calibration_frame.png}.
# The calibration file itself (camera_calibration.py make-h) needs OpenCV, which the simulator host's venv does not
# carry: the session fetches the two capture files and runs make-h on the lead host, then puts H.yaml and
# homography_C_matrix.yaml on the S-CORE host before the S-CORE side starts (its identity record hashes both).
# ASM-DRIVING-006 (calib-steer) needs the candidate: the session runs it with run_scenario.sh ASM-DRIVING-006.
# env: see common.sh; CALIB_SETTING (SC-DRIVING-012@20), CALIB_SPEEDS (20,42,60), CALIB_DECELS (1,2,3,4,5),
#      CHECKERBOARD (default: the session kit's session-inputs/checkerboard-bw-4x4.png, taken from the
#      VisionPilot pin by the session's preflight).
set -uo pipefail
OUT=${1:?out dir}; mkdir -p "$OUT"
# shellcheck source=common.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
SETTING=${CALIB_SETTING:-SC-DRIVING-012@20}
CHECKERBOARD=${CHECKERBOARD:-$BENCH/session-inputs/checkerboard-bw-4x4.png}
case "${2:-checkerboard}" in
  checkerboard) PRECHECK=on ;;
  settings) PRECHECK=record ;;
  *) echo "FAIL unknown camera calibration source '$2' (checkerboard|settings)"; exit 2 ;;
esac
START=$(ws_read_start "$OUT") || exit 2
[ -s "$CHECKERBOARD" ] || { echo "FAIL no checkerboard at $CHECKERBOARD"; exit 2; }
echo "checkerboard $(sha256sum "$CHECKERBOARD" | cut -d' ' -f1) $CHECKERBOARD"

ws_side calib-decel --setting "$SETTING" --start "$START" --speeds "${CALIB_SPEEDS:-20,42,60}" \
  --decels "${CALIB_DECELS:-1,2,3,4,5}" --run-dir "$OUT/calib_decel"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL calib-decel rc=$rc"; exit "$rc"; }
ws_side camera-capture --setting "$SETTING" --start "$START" --checkerboard "$CHECKERBOARD" \
  --run-dir "$OUT/camcal" --precheck "$PRECHECK"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL camera-capture rc=$rc"; exit "$rc"; }
for f in camera_capture.json calibration_frame.png; do
  [ -s "$OUT/camcal/simulator/$f" ] || { echo "FAIL camera-capture left no $f"; exit 2; }
done
echo "CALIBRATE_DONE"
