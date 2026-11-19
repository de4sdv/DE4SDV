#!/bin/bash
# A stub component for the dry runs of the S-CORE side's scripts. Test code only. It logs its start (arguments,
# working directory and the variables the Launch Manager sets) and its stop into <run>/score/stubs/<name>.log, and
# runs until SIGTERM. Beside that, to stand for the real processes' records in the dry runs of p10_1_check.sh:
#   - as vision_pilot it writes supervision.start and two out.driving_command lines into log.path of its interface
#     settings once LCM_ALIVE_INTERFACE_PATH is set, and visionpilot.rrd into its working directory at the stop;
#   - as actuation_adapter it writes a supervision start and an accepted in.driving_command into
#     <run>/score/actuationAdapter.jsonl;
#   - as gatewayd it prints DA_STUB_GATEWAYD_LINE once a second, when that is set.
name=$(basename "$0")
run=""
for ((i = 1; i <= $#; i++)); do
  [ "${!i}" = --run-dir ] && { j=$((i + 1)); run=${!j}; }
done
[ -n "$run" ] || run=$(cd "$(dirname "$0")/.." && pwd)/run
mkdir -p "$run/score/stubs"
log=$run/score/stubs/$name.log
echo "start $name pid $$ cwd $PWD args $* MW_COM_CONFIG=${MW_COM_CONFIG:-} LCM_ALIVE_INTERFACE_PATH=${LCM_ALIVE_INTERFACE_PATH:-}" >> "$log"
stop() {
  echo "stop $name" >> "$log"
  [ "$name" = vision_pilot ] && echo "synthetic rrd" > visionpilot.rrd
  exit 0
}
trap stop TERM INT
if [ "$name" = vision_pilot ] && [ -n "${LCM_ALIVE_INTERFACE_PATH:-}" ] && [ -n "${DE4SDV_SCORE_INTERFACE_CONFIG:-}" ]; then
  si=$(sed -n 's/^log.path = //p' "$DE4SDV_SCORE_INTERFACE_CONFIG")
  if [ -n "$si" ]; then
    mkdir -p "$(dirname "$si")"
    { echo '{"kind":"start"}'; echo '{"kind":"supervision.start"}'
      echo '{"kind":"out.driving_command","seq":1}'; echo '{"kind":"out.driving_command","seq":2}'; } >> "$si"
  fi
fi
if [ "$name" = actuation_adapter ] && [ -n "${LCM_ALIVE_INTERFACE_PATH:-}" ]; then
  { echo '{"t_mono_ns":1,"event":"supervision","data":{"state":"start"}}'
    echo '{"t_mono_ns":2,"event":"in.driving_command","data":{"seq":1,"verdict":"accepted"}}'; } \
    >> "$run/score/actuationAdapter.jsonl"
fi
n=0
while :; do
  sleep 0.1
  n=$((n + 1))
  if [ "$name" = gatewayd ] && [ -n "${DA_STUB_GATEWAYD_LINE:-}" ] && [ $((n % 10)) = 0 ]; then
    echo "$DA_STUB_GATEWAYD_LINE"
  fi
done
