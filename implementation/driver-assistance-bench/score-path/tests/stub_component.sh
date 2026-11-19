#!/bin/bash
# A stub component for the dry runs of the S-CORE side's scripts. Test code only. It logs its start (arguments,
# working directory and the variables the Launch Manager sets) and its stop into <run>/score/stubs/<name>.log, and
# runs until SIGTERM. As vision_pilot or actuation_adapter it dies of SIGSEGV without HOME and CARLA_CACHE_DIR, as the
# real binaries do (LibCarla's static initializer). Beside that, to stand for the real processes' records in the dry
# runs of p10_1_check.sh:
#   - as vision_pilot it writes supervision.start and two out.driving_command lines into log.path of its interface
#     settings once LCM_ALIVE_INTERFACE_PATH is set, and visionpilot.rrd into its working directory at the stop;
#   - as actuation_adapter it writes a supervision start and an accepted in.driving_command into
#     <run>/score/actuationAdapter.jsonl;
#   - as gatewayd it prints DA_STUB_GATEWAYD_LINE once a second, when that is set; with DA_STUB_GATEWAYD_PER_SEND
#     ("<delay s>,<delay s>,..." per send, "-" never) instead once per send the test publisher recorded in
#     DA_TEST_SINK_FILE, each that many seconds after this stub saw the send (a late or a lost receive line).
name=$(basename "$0")
run=""
for ((i = 1; i <= $#; i++)); do
  [ "${!i}" = --run-dir ] && { j=$((i + 1)); run=${!j}; }
done
[ -n "$run" ] || run=$(cd "$(dirname "$0")/.." && pwd)/run
mkdir -p "$run/score/stubs"
log=$run/score/stubs/$name.log
echo "start $name pid $$ cwd $PWD args $* MW_COM_CONFIG=${MW_COM_CONFIG:-} LCM_ALIVE_INTERFACE_PATH=${LCM_ALIVE_INTERFACE_PATH:-} HOME=${HOME:-} CARLA_CACHE_DIR=${CARLA_CACHE_DIR:-}" >> "$log"
# vision_pilot and actuation_adapter link LibCarla's client, whose static initializer takes getenv("HOME") unchecked
# when CARLA_CACHE_DIR is unset (CARLA 14ac3b1a50 LibCarla/source/carla/client/FileTransfer.cpp:17-31): without both
# the real binaries die of SIGSEGV before main, as on the L4 in session 5
case "$name" in
  vision_pilot|actuation_adapter)
    if [ -z "${CARLA_CACHE_DIR:-}" ] && [ -z "${HOME+set}" ]; then
      echo "segfault $name: no HOME and no CARLA_CACHE_DIR" >> "$log"; kill -SEGV $$
    fi ;;
esac
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
n=0 seen=0 due=()
while :; do
  sleep 0.1
  n=$((n + 1))
  [ "$name" = gatewayd ] && [ -n "${DA_STUB_GATEWAYD_LINE:-}" ] || continue
  if [ -z "${DA_STUB_GATEWAYD_PER_SEND:-}" ]; then
    [ $((n % 10)) = 0 ] && echo "$DA_STUB_GATEWAYD_LINE"
    continue
  fi
  sends=$(wc -w < "${DA_TEST_SINK_FILE:-/nonexistent}" 2>/dev/null) || sends=0
  now=$(date +%s.%N)
  while [ "$seen" -lt "${sends:-0}" ]; do
    seen=$((seen + 1))
    d=$(cut -d, -f"$seen" <<< "$DA_STUB_GATEWAYD_PER_SEND")
    if [ "$d" = - ]; then due[$seen]=never; else due[$seen]=$(awk -v a="$now" -v b="${d:-0}" 'BEGIN { printf "%.3f", a + b }'); fi
  done
  for k in "${!due[@]}"; do
    [ "${due[$k]}" = never ] || [ "${due[$k]}" = done ] && continue
    if awk -v a="$now" -v b="${due[$k]}" 'BEGIN { exit !(a >= b) }'; then echo "$DA_STUB_GATEWAYD_LINE"; due[$k]=done; fi
  done
done
