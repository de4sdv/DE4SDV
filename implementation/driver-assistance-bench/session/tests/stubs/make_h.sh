#!/bin/bash
# Stand-in for camera_calibration.py make-h in the dry-run tests (DA_MAKE_H): the fake capture files are no images.
# Same trailing arguments as the real call: --capture <camera_capture.json> --out-dir <dir>.
set -eu
while [ $# -gt 0 ]; do case "$1" in --capture) CAP=$2; shift 2 ;; --out-dir) OUT=$2; shift 2 ;; *) shift ;; esac; done
[ -s "$CAP" ] || { echo "no capture $CAP"; exit 1; }
mkdir -p "$OUT"
printf '%%YAML:1.0\nH: stub of %s\n' "$CAP" > "$OUT/H.yaml"
printf '%%YAML:1.0\nC: stub\n' > "$OUT/homography_C_matrix.yaml"
echo '{"result": "written", "stub": true}' > "$OUT/camera_calibration_record.json"
