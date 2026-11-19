#!/bin/bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): the P10-1 check on the S-CORE host (ENTRY_SCORE_P10_1 of
# session/entrypoints.env; contract in session/README.md "Entry-point contracts").
#
#   p10_1_check.sh <out>
#
# One line per check, "PASS <check>: <detail>", "FAIL <check>: <detail>" or "NOT RUN <check>: <why>", into
# <out>/p10_1_verdicts.txt (and p10_1_verdicts.json); exit 1 when any check FAILs, else 0. A NOT RUN is no pass:
# the line says what is missing.
#
#   C1 launch_manager_config_and_start_order  the Launch Manager takes the full configuration and starts the
#      identity recorder first: vision_pilot and actuation_adapter start only after the recorder reported running,
#      gatewayd after someipd (process start times against the recorder's lifecycle record)
#   C2 alive_notifications                    LCM_ALIVE_INTERFACE_PATH is set in vision_pilot's and the adapter's
#      environment, both log the start of their supervision and none is off, and for DA_P10_1_ALIVE_HOLD_S the
#      Launch Manager logs no expiry while both run
#   C3 stalled_candidate_fallback             a SIGSTOPped vision_pilot leads to fallback_run_target: the Launch
#      Manager's log has the expiry and the switch, vision_pilot and the adapter are gone, the recorder, someipd and
#      gatewayd run on with the same pids
#   C4 asil_b_command_path                    mw::com takes the driving command's ASIL B deployment: the candidate
#      sent commands and the adapter accepted one
#   C5 gatewayd_receives_from_asil_b_process  gatewayd (QM) takes the warning request from a process of global ASIL
#      B: the test publisher (the candidate's manifest values) sends, and gatewayd's output matches
#      GATEWAYD_RX_REGEX once per send. gatewayd as built prints no line per received sample (session 5 on the L4:
#      only its offer lines), so without that pattern C5 is NOT RUN and p10-3 judges the receipt on the guest
#   C6 cuda_pass_time                         no pass after the first of the three networks on the CUDA provider
#      (ort_cuda_check, the S-CORE toolchain's ONNX Runtime) takes longer than 0.4 s
#   C7 candidate_record_late_subscriber       the candidate record reaches a subscriber that subscribes after it was
#      published (candidate_record_probe), and its digest is the file's
#   C8 candidate_on_a_replayed_clip           NOT RUN: the S-CORE interface module has no clip replayer
#
# The full start needs DA_CAMERA_CALIBRATION_DIR; without it, upstream's calibration from the bundle stands in, copied
# into <out>/p10_1_calibration and named there (p10-1 judges nothing on the geometry).
# C1's full part and C2 to C4 need a CARLA 1.0 server at DA_P10_1_CARLA_HOST whose port 2000 answers; C2 to C4 also a
# world that ticks (the world side's pacer, started by the caller), since they need the candidate's first completed
# pass. The real vision_pilot and actuation_adapter exit at once on a refused CARLA connection (session 5 on the L4),
# so without such a server the full configuration is never started: C1 is NOT RUN, with the reason and its path
# part's result (FAIL when the path part failed), and C2 to C4 are NOT RUN. C5 to C7 need no simulator.
#
# Settings: DA_CAMERA_CALIBRATION_DIR (unset), DA_P10_1_CARLA_HOST (none), GATEWAYD_RX_REGEX (unset), DA_P10_1_C5_WAIT_S
# (5, whole seconds: C5's bound for the 3 receive lines), DA_P10_1_LATE_WAIT_S (3), DA_P10_1_CUDA_RUNS
# (20), DA_P10_1_ALIVE_HOLD_S (10), DA_P10_1_STALL_HOLD_S (3), DA_P10_1_SUPERVISED_WAIT_S (420),
# DA_P10_1_ORT_TIMEOUT_S (300: each ort_cuda_check run), DA_P10_1_PROBE_TIMEOUT_S (60: the late subscriber's probe),
# DA_P10_1_CUT_STOP_S (100: the cut's stop), and those of ../../score-path/scripts/lib_score_side.sh.
#
# A cut (TERM, INT or HUP: the session's step TERM, its time-out, the cap) never leaves the Launch Manager this check
# started: it runs with setsid, so the step's group signal does not reach it. The handler stops it with
# stop_score_side.sh into the open part's folder (path/ or full/, else cut_stop/), bounded by DA_P10_1_CUT_STOP_S and in
# a session of its own (a second TERM to the step cannot cut the collection), writes p10_1_verdicts.txt and .json with
# the verdicts judged so far and "NOT RUN <check>: cut by <signal> ..." for the rest (the json's "cut" names the
# signal, the part and the stop's exit status), and exits 128 + the signal's number.
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH=$(cd -- "$HERE/../.." && pwd)
SP=$BENCH/score-path/scripts
# shellcheck source=../../score-path/scripts/lib_score_side.sh
. "$SP/lib_score_side.sh"

OUT=${1:?usage: p10_1_check.sh <out>}
: "${DA_P10_1_CARLA_HOST:=none}"
: "${GATEWAYD_RX_REGEX:=}"
: "${DA_P10_1_LATE_WAIT_S:=3}"
: "${DA_P10_1_CUDA_RUNS:=20}"
: "${DA_P10_1_ALIVE_HOLD_S:=10}"
: "${DA_P10_1_STALL_HOLD_S:=3}"
: "${DA_P10_1_SUPERVISED_WAIT_S:=420}"
: "${DA_P10_1_SKIP_PORT_CHECK:=0}"
: "${DA_P10_1_C5_WAIT_S:=5}"
: "${DA_P10_1_ORT_TIMEOUT_S:=300}"
: "${DA_P10_1_PROBE_TIMEOUT_S:=60}"
: "${DA_P10_1_CUT_STOP_S:=100}"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/p10_1_check.log") 2>&1
VERDICTS=$OUT/p10_1_verdicts.txt
: > "$VERDICTS"
verdict() {   # verdict PASS|FAIL|NOT_RUN <check> <detail>
  local v=$1 c=$2; shift 2
  local word=$v; [ "$v" = NOT_RUN ] && word="NOT RUN"
  echo "$word $c: $*" | tee -a "$VERDICTS"
}
REC_LOG=$DA_STAGE/run/score/identityRecorder.jsonl
LM_LOG=$DA_STAGE/state/launch_manager.log
json_num() { sed -n "s/.*\"$2\":\([0-9.e+-]*\).*/\1/p" <<< "$1" | head -1; }
CHECKS="C1_launch_manager_config_and_start_order C2_alive_notifications C3_stalled_candidate_fallback
  C4_asil_b_command_path C5_gatewayd_receives_from_asil_b_process C6_cuda_pass_time
  C7_candidate_record_late_subscriber C8_candidate_on_a_replayed_clip"
write_json() {   # write_json [<signal> <part> <stop rc>]: p10_1_verdicts.json from the .txt (and the cut, if any)
  "$DA_PYTHON" - "$VERDICTS" "$OUT/p10_1_verdicts.json" "$@" << 'EOF'
import json, re, sys
rows = []
for line in open(sys.argv[1], encoding="utf-8"):
    m = re.match(r"(PASS|FAIL|NOT RUN) (\S+): (.*)", line.rstrip("\n"))
    if m:
        rows.append({"verdict": m.group(1), "check": m.group(2), "detail": m.group(3)})
doc = {"checks": rows}
if len(sys.argv) > 3:
    doc["cut"] = {"signal": sys.argv[3], "part": sys.argv[4], "stop_rc": sys.argv[5]}
json.dump(doc, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
EOF
}

# the cut (see the header): the open start stopped and collected, the verdicts so far kept, the rest NOT RUN
PART="setup" PART_OUT=""
on_cut() {
  local sig=$1 num=$2 src stop_rc=none c
  trap '' TERM INT HUP PIPE
  # the tee of this script's output had the step's group signal too: the log file directly from here on
  exec >> "$OUT/p10_1_check.log" 2>&1
  ss_log "CUT by $sig during part $PART"
  src=$PART_OUT
  [ -z "$src" ] && ss_lm_running > /dev/null && src=$OUT/cut_stop
  if [ -n "$src" ]; then
    ss_log "the cut's stop of the S-CORE side into $src (at most $DA_P10_1_CUT_STOP_S s)"
    setsid -w timeout --foreground "$DA_P10_1_CUT_STOP_S" bash "$SP/stop_score_side.sh" "$src" < /dev/null
    stop_rc=$?
    ss_log "the cut's stop: rc $stop_rc"
  fi
  for c in $CHECKS; do
    grep -q "^[A-Z ]* ${c}: " "$VERDICTS" 2>/dev/null ||
      verdict NOT_RUN "$c" "cut by $sig during part $PART before this check's verdict"
  done
  write_json "$sig" "$PART" "$stop_rc"
  ss_log "P10-1: cut by $sig during part $PART"
  exit $(( 128 + num ))
}
trap 'on_cut TERM 15' TERM
trap 'on_cut INT 2' INT
trap 'on_cut HUP 1' HUP

# The recorder's report, in monotonic ns.
reported_mono_ns() { json_num "$(ss_last_event "$REC_LOG" lifecycle)" t_mono_ns; }
# A component's start (state file) in ns since boot.
start_ns() { awk -v s="$(ss_state "START_S_$1")" 'BEGIN { if (s == "") exit 1; printf "%.0f\n", s * 1e9 }'; }

order_check() {   # order_check <mode>: the start order in the state of a start; prints the problems
  local problems="" rep vp
  rep=$(reported_mono_ns)
  [ -n "$rep" ] || problems="$problems no lifecycle record of the recorder;"
  local s_someipd s_gatewayd
  s_someipd=$(start_ns someipd) s_gatewayd=$(start_ns gatewayd)
  [ -n "$s_someipd" ] && [ -n "$s_gatewayd" ] && [ "$s_gatewayd" -ge "$s_someipd" ] \
    || problems="$problems gatewayd did not start after someipd;"
  if [ "$1" = full ]; then
    for name in vision_pilot actuation_adapter; do
      vp=$(start_ns "$name") || { problems="$problems no $name;"; continue; }
      # /proc start times have the clock tick's resolution (10 ms): allow one tick
      [ -n "$rep" ] && [ "$vp" -ge $(( rep - 10000000 )) ] || problems="$problems $name started before the record;"
    done
  fi
  echo "$problems"
}

# ---------------------------------------------------------------------------------------------------------------
ss_log "P10-1 check on $(hostname), stage $DA_STAGE, bundle $DA_B2_BUNDLE, CARLA host $DA_P10_1_CARLA_HOST"
ss_clock_record > "$OUT/clock_start.txt"

# Part 1: the warning path alone (the path-only configuration): the late subscriber and gatewayd.
ss_log "part 1: the warning path"
PART="1 (the warning path)" PART_OUT=$OUT/path
if bash "$SP/start_score_side.sh" "$OUT/path" none; then
  path_order=$(order_check path)
  # C7: subscribe after the record was published
  probe=$DA_STAGE/bin/candidate_record_probe
  if [ -x "$probe" ]; then
    first_pub=$(json_num "$(grep -F '"event":"publish"' "$REC_LOG" | head -1)" t_real_ns)
    timeout --foreground "$DA_P10_1_PROBE_TIMEOUT_S" $DA_SUDO env \
      MW_COM_CONFIG="$DA_STAGE/config/mw_com_config_candidate_record_probe.json" "$probe" \
      --wait-s "$DA_P10_1_LATE_WAIT_S" --timeout-s 10 --out "$OUT/late_subscriber.json" > /dev/null
    rc=$?
    sub=$(json_num "$(cat "$OUT/late_subscriber.json" 2>/dev/null)" subscribed_real_ns)
    want=$(ss_state RECORD_SHA256)
    if [ "$rc" = 0 ] && grep -q "\"record_sha256\":\"$want\"" "$OUT/late_subscriber.json" &&
       [ -n "$sub" ] && [ -n "$first_pub" ] && [ "$sub" -gt "$first_pub" ]; then
      verdict PASS C7_candidate_record_late_subscriber "subscribed $(( (sub - first_pub) / 1000000 )) ms after" \
        "the first publication and got record $want"
    else
      verdict FAIL C7_candidate_record_late_subscriber "probe exit $rc: $(cat "$OUT/late_subscriber.json" 2>/dev/null)"
    fi
  else
    verdict NOT_RUN C7_candidate_record_late_subscriber "no $probe in the bundle"
  fi
  # C5: the test publisher, a process of global ASIL B like the candidate, to gatewayd (QM)
  printf '0 false 2000.000\n0.5 true 2000.050\n1.0 false 2000.100\n' > "$OUT/p10_1_sequence.txt"
  lines_before=$(wc -l < "$LM_LOG" 2>/dev/null || echo 0)
  DA_INJECT_SEQUENCE=$OUT/p10_1_sequence.txt bash "$BENCH/ivi-warning/scripts/inject_warning_requests.sh" \
    "$OUT/inject"
  irc=$?
  if [ "$irc" != 0 ]; then
    verdict FAIL C5_gatewayd_receives_from_asil_b_process "the test publisher exited $irc (see $OUT/inject)"
  elif [ -z "$GATEWAYD_RX_REGEX" ]; then
    verdict NOT_RUN C5_gatewayd_receives_from_asil_b_process "3 sends went out; gatewayd prints no line per received" \
      "sample (its output as built: session 5), so no GATEWAYD_RX_REGEX can count the receipts here; p10-3 judges" \
      "the receipt on the guest"
  else
    # a bounded poll for the 3 receive lines, never a fixed wait: under load the third came after a fixed 1 s
    # (f67241db, bench_unit) and C5 FAILed falsely
    ss_log "C5: up to ${DA_P10_1_C5_WAIT_S} s for 3 lines matching '$GATEWAYD_RX_REGEX' in the Launch Manager's log"
    c5_end=$(( $(date +%s%N) + ${DA_P10_1_C5_WAIT_S%.*} * 1000000000 ))
    while :; do
      hits=$(tail -n +"$((lines_before + 1))" "$LM_LOG" | grep -c -E "$GATEWAYD_RX_REGEX" || true)
      [ "${hits:-0}" -ge 3 ] && break
      [ "$(date +%s%N)" -ge "$c5_end" ] && break
      sleep 0.2
    done
    if [ "${hits:-0}" -ge 3 ]; then
      verdict PASS C5_gatewayd_receives_from_asil_b_process "$hits lines match '$GATEWAYD_RX_REGEX' for 3 sends"
    else
      verdict FAIL C5_gatewayd_receives_from_asil_b_process "${hits:-0} lines match '$GATEWAYD_RX_REGEX' for 3 sends" \
        "within ${DA_P10_1_C5_WAIT_S} s"
    fi
  fi
  bash "$SP/stop_score_side.sh" "$OUT/path"
  PART_OUT=""
else
  path_order="the path-only start failed (see $OUT/path)"
  verdict FAIL C7_candidate_record_late_subscriber "the warning path did not start"
  verdict FAIL C5_gatewayd_receives_from_asil_b_process "the warning path did not start"
fi

# Part 2: the CUDA passes, outside the Launch Manager.
ss_log "part 2: the networks on the CUDA provider"
PART="2 (the CUDA passes)" PART_OUT=""
ort=$DA_B2_BUNDLE/bin/ort_cuda_check
weights=$DA_B2_BUNDLE/share/visionpilot/modules/models/weights
if [ ! -x "$ort" ]; then
  verdict NOT_RUN C6_cuda_pass_time "no $ort in the bundle"
else
  : > "$OUT/cuda_runs.txt"
  ok=1
  for net in autodrive autosteer autospeed; do
    if ! timeout --foreground "$DA_P10_1_ORT_TIMEOUT_S" "$ort" "$weights/${net}_fp32.onnx" "$DA_P10_1_CUDA_RUNS" > "$OUT/ort_${net}.txt" 2>&1 ||
       ! grep -q "ORT_CUDA_CHECK PASS" "$OUT/ort_${net}.txt"; then
      ok=0
    fi
    sed -n "s/^run \([0-9]*\): .* \([0-9.]*\) ms$/$net \1 \2/p" "$OUT/ort_${net}.txt" >> "$OUT/cuda_runs.txt"
  done
  if [ "$ok" != 1 ]; then
    verdict FAIL C6_cuda_pass_time "ort_cuda_check failed (see $OUT/ort_*.txt)"
  else
    # a pass = one run of each network; run 0 or 1 is the first (ort_cuda_check numbers from either)
    result=$(awk -v n="$DA_P10_1_CUDA_RUNS" '
      { ms[$2] += $3; if (!($1 in nets)) { nets[$1] = 1; nnets++ } if (min == "" || $2 + 0 < min + 0) min = $2 }
      END {
        if (nnets != 3) { print "FAIL fewer than three networks ran"; exit }
        worst = 0; count = 0
        for (k in ms) { if (k == min) { first = ms[k]; continue } count++; if (ms[k] > worst) worst = ms[k] }
        if (count < 1) { print "FAIL no pass after the first"; exit }
        printf "%s first pass %.1f ms; worst of %d later passes %.1f ms (bound 400 ms)\n",
               (worst <= 400 ? "PASS" : "FAIL"), first, count, worst
      }' "$OUT/cuda_runs.txt")
    verdict "${result%% *}" C6_cuda_pass_time "${result#* }; the three networks one after another, not the loop"
  fi
fi

# Part 3: the full configuration and the candidate, only against a CARLA server that answers.
ss_log "part 3: the full configuration"
PART="3 (the full configuration)"
carla=$DA_P10_1_CARLA_HOST
have_world=0 no_world="no DA_P10_1_CARLA_HOST"
if [ "$carla" != none ]; then
  if [ "$DA_P10_1_SKIP_PORT_CHECK" = 1 ] || timeout --foreground 10 bash -c "</dev/tcp/$carla/2000" 2>/dev/null; then
    have_world=1
  else
    no_world="CARLA port 2000 at $carla does not answer"
    ss_log "$no_world: the candidate's checks do not run"
  fi
fi
not_run_candidate() {
  local why="needs the candidate's first pass: a CARLA 1.0 server with a ticking world at DA_P10_1_CARLA_HOST, or a clip replayer (none in score-interface)"
  verdict NOT_RUN C2_alive_notifications "$why"
  verdict NOT_RUN C3_stalled_candidate_fallback "$why"
  verdict NOT_RUN C4_asil_b_command_path "$why"
}
if [ "$have_world" != 1 ]; then
  # Session 5 on the real L4: the real vision_pilot and actuation_adapter exit at once on a refused CARLA
  # connection, so a full start against a host nobody serves can never pass. It is not started; C1 is NOT RUN with
  # its path part's result, or FAIL when that part failed.
  ss_log "part 3: not started ($no_world)"
  why="the full start needs a CARLA 1.0 server ($no_world): vision_pilot and actuation_adapter exit at once on a refused connection; path part:"
  if [ -z "$path_order" ]; then
    verdict NOT_RUN C1_launch_manager_config_and_start_order "$why ok"
  else
    verdict FAIL C1_launch_manager_config_and_start_order "$why $path_order"
  fi
  not_run_candidate
else
  # Mode full needs a camera calibration (start_score_side.sh). p10-1 is no judged run: without the session's
  # DA_CAMERA_CALIBRATION_DIR, upstream's calibration from the bundle stands in, copied into <out> and named as such.
  if [ -z "${DA_CAMERA_CALIBRATION_DIR:-}" ]; then
    export DA_CAMERA_CALIBRATION_DIR=$OUT/p10_1_calibration
    mkdir -p "$DA_CAMERA_CALIBRATION_DIR"
    if ! cp "$DA_B2_BUNDLE/config/visionpilot/H.yaml" "$DA_B2_BUNDLE/config/visionpilot/homography_C_matrix.yaml" \
        "$DA_CAMERA_CALIBRATION_DIR/"; then
      ss_log "the bundle lacks upstream's calibration in $DA_B2_BUNDLE/config/visionpilot: the full start refuses"
    fi
    echo "p10-1 stand-in: upstream's calibration from $DA_B2_BUNDLE/config/visionpilot, not the CARLA camera's" \
      > "$DA_CAMERA_CALIBRATION_DIR/SOURCE.txt"
    ss_log "no DA_CAMERA_CALIBRATION_DIR: upstream's calibration stands in for the full start (no judged run)"
  fi
  PART_OUT=$OUT/full
  if ! bash "$SP/start_score_side.sh" "$OUT/full" "$carla"; then
    verdict FAIL C1_launch_manager_config_and_start_order "the full start failed (see $OUT/full); path part: ${path_order:-ok}"
    not_run_candidate
  else
    full_order=$(order_check full)
    if [ -z "$path_order$full_order" ]; then
      verdict PASS C1_launch_manager_config_and_start_order "recorder reported running before vision_pilot and" \
        "actuation_adapter started; gatewayd after someipd; in both configurations"
    else
      verdict FAIL C1_launch_manager_config_and_start_order "full:${full_order:- ok} path:${path_order:- ok}"
    fi
    SI_LOG=$DA_STAGE/run/score/score_interface.jsonl
    AD_LOG=$DA_STAGE/run/score/actuationAdapter.jsonl
    deadline=$(( $(date +%s) + DA_P10_1_SUPERVISED_WAIT_S ))
    until grep -q '"kind":"supervision.start"' "$SI_LOG" 2>/dev/null &&
          grep -q '"event":"supervision".*"state":"start"' "$AD_LOG" 2>/dev/null; do
      [ "$(date +%s)" -ge "$deadline" ] && break
      sleep 1
    done
    vp=$(ss_pids_of vision_pilot | head -1) ad=$(ss_pids_of actuation_adapter | head -1)
    env_ok=1
    for pid in $vp $ad; do
      $DA_SUDO cat "/proc/$pid/environ" 2>/dev/null | tr '\0' '\n' | grep -q '^LCM_ALIVE_INTERFACE_PATH=.' || env_ok=0
    done
    [ -n "$vp" ] && [ -n "$ad" ] || env_ok=0
    sup_ok=1
    grep -q '"kind":"supervision.start"' "$SI_LOG" 2>/dev/null || sup_ok=0
    grep -q '"kind":"supervision.off"' "$SI_LOG" 2>/dev/null && sup_ok=0
    grep -q '"event":"supervision".*"state":"start"' "$AD_LOG" 2>/dev/null || sup_ok=0
    grep -q '"event":"supervision".*"state":"off"' "$AD_LOG" 2>/dev/null && sup_ok=0
    sleep "$DA_P10_1_ALIVE_HOLD_S"
    expired=$(grep -c -i 'expired' "$LM_LOG" 2>/dev/null || true)
    if [ "$env_ok" = 1 ] && [ "$sup_ok" = 1 ] && [ "${expired:-0}" = 0 ] && ss_alive "$vp" && ss_alive "$ad"; then
      verdict PASS C2_alive_notifications "LCM_ALIVE_INTERFACE_PATH set in both; both supervised; no expiry in" \
        "${DA_P10_1_ALIVE_HOLD_S} s"
    else
      verdict FAIL C2_alive_notifications "environment $env_ok, supervision logs $sup_ok, expiries ${expired:-0}"
    fi
    sent=$(grep -c '"kind":"out.driving_command"' "$SI_LOG" 2>/dev/null || true)
    accepted=$(grep -c '"event":"in.driving_command".*"verdict":"accepted"' "$AD_LOG" 2>/dev/null || true)
    if [ "${sent:-0}" -gt 0 ] && [ "${accepted:-0}" -gt 0 ]; then
      verdict PASS C4_asil_b_command_path "the candidate sent $sent commands, the adapter accepted $accepted"
    else
      verdict FAIL C4_asil_b_command_path "the candidate sent ${sent:-0} commands, the adapter accepted ${accepted:-0}"
    fi
    keep=""
    for name in identity_recorder someipd gatewayd; do keep="$keep $name=$(ss_pids_of "$name" | head -1)"; done
    lines_before=$(wc -l < "$LM_LOG" 2>/dev/null || echo 0)
    if [ -n "$vp" ]; then
      $DA_SUDO kill -STOP "$vp"
      ss_log "SIGSTOP to vision_pilot ($vp); holding ${DA_P10_1_STALL_HOLD_S} s"
      sleep "$DA_P10_1_STALL_HOLD_S"
    fi
    after=$(tail -n +"$((lines_before + 1))" "$LM_LOG" 2>/dev/null)
    problems=""
    grep -q -i 'expired' <<< "$after" || problems="$problems no expiry in the Launch Manager's log;"
    grep -q 'fallback_run_target' <<< "$after" || problems="$problems no switch to fallback_run_target;"
    [ -z "$(ss_pids_of vision_pilot)" ] || problems="$problems vision_pilot still there;"
    [ -z "$(ss_pids_of actuation_adapter)" ] || problems="$problems actuation_adapter still there;"
    for kv in $keep; do
      name=${kv%%=*} pid=${kv#*=}
      [ -n "$pid" ] && ss_alive "$pid" || problems="$problems $name did not run on;"
    done
    if [ -z "$problems" ]; then
      verdict PASS C3_stalled_candidate_fallback "expiry and switch to fallback_run_target logged; the recorder," \
        "someipd and gatewayd ran on ($keep )"
    else
      verdict FAIL C3_stalled_candidate_fallback "$problems"
    fi
    bash "$SP/stop_score_side.sh" "$OUT/full"
  fi
  PART_OUT=""
fi

verdict NOT_RUN C8_candidate_on_a_replayed_clip "the S-CORE interface module has no clip replayer (score-interface:" \
  "CARLA camera only), and the brief's B0 clip replayer is not in the bench"
ss_clock_record > "$OUT/clock_end.txt"

# the summary
fails=$(grep -c '^FAIL ' "$VERDICTS" || true)
passes=$(grep -c '^PASS ' "$VERDICTS" || true)
notrun=$(grep -c '^NOT RUN ' "$VERDICTS" || true)
PART="the summary"
write_json
ss_log "P10-1: $passes PASS, $fails FAIL, $notrun NOT RUN"
[ "${fails:-0}" = 0 ]
