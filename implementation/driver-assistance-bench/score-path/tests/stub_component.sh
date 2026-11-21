#!/bin/bash
# A stub component for the dry runs of the S-CORE side's scripts. Test code only. It logs its start (arguments,
# working directory and the variables the Launch Manager sets) and its stop into <run>/score/stubs/<name>.log, and
# runs until SIGTERM. As vision_pilot or actuation_adapter it dies of SIGSEGV without HOME and CARLA_CACHE_DIR, as the
# real binaries do (LibCarla's static initializer). Beside that, to stand for the real processes' records in the dry
# runs of p10_1_check.sh:
#   - as vision_pilot it writes supervision.start and two out.driving_command lines into log.path of its interface
#     settings once LCM_ALIVE_INTERFACE_PATH is set, and visionpilot.rrd into its working directory at the stop;
#   - as actuation_adapter it writes a supervision start and an accepted in.driving_command into
#     <run>/score/actuationAdapter.jsonl, and at SIGTERM the supervision stop and stop records the real adapter writes
#     (alive_ticker.cpp, actuation_adapter_main.cpp);
#   - as vision_pilot with DA_STUB_VP_VISUALIZATION=<n> and DE4SDV_VISUALIZATION_RECORD set (the recorder of patch
#     0001), at the stop it writes the video (<n> blocks of bytes; 0: an empty file), <video>.frames.csv with <n> rows
#     and <video>.summary.txt, as the recorder does when it closes, and the video's inode into
#     <run>/score/stubs/vision_pilot.vis_inode;
#   - as vision_pilot with DA_STUB_VP_EXIT_AFTER_S=<s> it exits with status 134 after s seconds (the real candidate's
#     abort in run 20261119T134840Z);
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
echo "start $name pid $$ cwd $PWD args $* MW_COM_CONFIG=${MW_COM_CONFIG:-} LCM_ALIVE_INTERFACE_PATH=${LCM_ALIVE_INTERFACE_PATH:-} HOME=${HOME:-} CARLA_CACHE_DIR=${CARLA_CACHE_DIR:-} DE4SDV_VISUALIZATION_RECORD=${DE4SDV_VISUALIZATION_RECORD:-} GST_REGISTRY=${GST_REGISTRY:-}" >> "$log"
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
  if [ "$name" = vision_pilot ] && [ -n "${DA_STUB_VP_VISUALIZATION:-}" ] && [ -n "${DE4SDV_VISUALIZATION_RECORD:-}" ]; then
    v=$DE4SDV_VISUALIZATION_RECORD
    : > "$v"; echo "video_index,frame_id,t_arrive_ns,t_submit_ns,t_worker_start_ns,t_drawn_ns,t_encoded_ns,sim_time_s" > "$v.frames.csv"
    for ((k = 0; k < DA_STUB_VP_VISUALIZATION; k++)); do
      head -c 4096 /dev/urandom >> "$v"; echo "$k,$((k + 1)),1,2,3,4,5,$((100 + k)).05" >> "$v.frames.csv"
    done
    echo "submitted=$DA_STUB_VP_VISUALIZATION dropped=0 written=$DA_STUB_VP_VISUALIZATION failed=0 encoder=gst encoder_open=1" > "$v.summary.txt"
    stat -c %i "$v" > "$run/score/stubs/vision_pilot.vis_inode"
  fi
  if [ "$name" = actuation_adapter ] && [ -n "${LCM_ALIVE_INTERFACE_PATH:-}" ]; then
    { echo '{"t_mono_ns":3,"event":"supervision","data":{"state":"stop","alive_reported":1}}'
      echo '{"t_mono_ns":4,"event":"stop","data":{"applied":0,"dropped":0}}'; } >> "$run/score/actuationAdapter.jsonl"
  fi
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
  if [ "$name" = vision_pilot ] && [ -n "${DA_STUB_VP_EXIT_AFTER_S:-}" ] &&
     awk -v n="$n" -v s="$DA_STUB_VP_EXIT_AFTER_S" 'BEGIN { exit !(n / 10 >= s) }'; then
    echo "exit $name 134 (DA_STUB_VP_EXIT_AFTER_S)" >> "$log"; exit 134
  fi
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
