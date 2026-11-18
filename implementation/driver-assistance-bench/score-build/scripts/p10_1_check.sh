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
#      GATEWAYD_RX_REGEX once per send
#   C6 cuda_pass_time                         no pass after the first of the three networks on the CUDA provider
#      (ort_cuda_check, the S-CORE toolchain's ONNX Runtime) takes longer than 0.4 s
#   C7 candidate_record_late_subscriber       the candidate record reaches a subscriber that subscribes after it was
#      published (candidate_record_probe), and its digest is the file's
#   C8 candidate_on_a_replayed_clip           NOT RUN: the S-CORE interface module has no clip replayer
#
# C2 to C4 need the candidate's first completed pass, so images: a CARLA 1.0 server at DA_P10_1_CARLA_HOST with a
# world that ticks (the world side's pacer, started by the caller). Without it they are NOT RUN. C1, C5 to C7 need no
# simulator: C1 starts the full configuration against a CARLA host nobody serves and stops it after the start order.
#
# Settings: DA_P10_1_CARLA_HOST (none), GATEWAYD_RX_REGEX (unset), DA_P10_1_LATE_WAIT_S (3), DA_P10_1_CUDA_RUNS
# (20), DA_P10_1_ALIVE_HOLD_S (10), DA_P10_1_STALL_HOLD_S (3), DA_P10_1_SUPERVISED_WAIT_S (420), and those of
# ../../score-path/scripts/lib_score_side.sh.
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
if bash "$SP/start_score_side.sh" "$OUT/path" none; then
  path_order=$(order_check path)
  # C7: subscribe after the record was published
  probe=$DA_STAGE/bin/candidate_record_probe
  if [ -x "$probe" ]; then
    first_pub=$(json_num "$(grep -F '"event":"publish"' "$REC_LOG" | head -1)" t_real_ns)
    $DA_SUDO env MW_COM_CONFIG="$DA_STAGE/config/mw_com_config_candidate_record_probe.json" "$probe" \
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
  sleep 1
  if [ "$irc" != 0 ]; then
    verdict FAIL C5_gatewayd_receives_from_asil_b_process "the test publisher exited $irc (see $OUT/inject)"
  elif [ -z "$GATEWAYD_RX_REGEX" ]; then
    verdict NOT_RUN C5_gatewayd_receives_from_asil_b_process "3 sends went out; no receive line of gatewayd is" \
      "known (set GATEWAYD_RX_REGEX); P10-3 shows the receipt on the guest"
  else
    hits=$(tail -n +"$((lines_before + 1))" "$LM_LOG" | grep -c -E "$GATEWAYD_RX_REGEX" || true)
    if [ "$hits" -ge 3 ]; then
      verdict PASS C5_gatewayd_receives_from_asil_b_process "$hits lines match '$GATEWAYD_RX_REGEX' for 3 sends"
    else
      verdict FAIL C5_gatewayd_receives_from_asil_b_process "$hits lines match '$GATEWAYD_RX_REGEX' for 3 sends"
    fi
  fi
  bash "$SP/stop_score_side.sh" "$OUT/path"
else
  path_order="the path-only start failed (see $OUT/path)"
  verdict FAIL C7_candidate_record_late_subscriber "the warning path did not start"
  verdict FAIL C5_gatewayd_receives_from_asil_b_process "the warning path did not start"
fi

# Part 2: the CUDA passes, outside the Launch Manager.
ss_log "part 2: the networks on the CUDA provider"
ort=$DA_B2_BUNDLE/bin/ort_cuda_check
weights=$DA_B2_BUNDLE/share/visionpilot/modules/models/weights
if [ ! -x "$ort" ]; then
  verdict NOT_RUN C6_cuda_pass_time "no $ort in the bundle"
else
  : > "$OUT/cuda_runs.txt"
  ok=1
  for net in autodrive autosteer autospeed; do
    if ! "$ort" "$weights/${net}_fp32.onnx" "$DA_P10_1_CUDA_RUNS" > "$OUT/ort_${net}.txt" 2>&1 ||
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

# Part 3: the full configuration and the candidate.
ss_log "part 3: the full configuration"
carla=$DA_P10_1_CARLA_HOST
have_world=0
if [ "$carla" != none ]; then
  if [ "$DA_P10_1_SKIP_PORT_CHECK" = 1 ] || timeout 10 bash -c "</dev/tcp/$carla/2000" 2>/dev/null; then
    have_world=1
  else
    ss_log "CARLA port 2000 at $carla does not answer: the candidate's checks do not run"
  fi
fi
[ "$have_world" = 1 ] || carla=127.0.0.1   # nobody serves it: enough for the start order
not_run_candidate() {
  local why="needs the candidate's first pass: a CARLA 1.0 server with a ticking world at DA_P10_1_CARLA_HOST, or a clip replayer (none in score-interface)"
  verdict NOT_RUN C2_alive_notifications "$why"
  verdict NOT_RUN C3_stalled_candidate_fallback "$why"
  verdict NOT_RUN C4_asil_b_command_path "$why"
}
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
  if [ "$have_world" != 1 ]; then
    not_run_candidate
  else
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
  fi
  bash "$SP/stop_score_side.sh" "$OUT/full"
fi

verdict NOT_RUN C8_candidate_on_a_replayed_clip "the S-CORE interface module has no clip replayer (score-interface:" \
  "CARLA camera only), and the brief's B0 clip replayer is not in the bench"
ss_clock_record > "$OUT/clock_end.txt"

# the summary
fails=$(grep -c '^FAIL ' "$VERDICTS" || true)
passes=$(grep -c '^PASS ' "$VERDICTS" || true)
notrun=$(grep -c '^NOT RUN ' "$VERDICTS" || true)
"$DA_PYTHON" - "$VERDICTS" "$OUT/p10_1_verdicts.json" << 'EOF'
import json, re, sys
rows = []
for line in open(sys.argv[1], encoding="utf-8"):
    m = re.match(r"(PASS|FAIL|NOT RUN) (\S+): (.*)", line.rstrip("\n"))
    if m:
        rows.append({"verdict": m.group(1), "check": m.group(2), "detail": m.group(3)})
json.dump({"checks": rows}, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
EOF
ss_log "P10-1: $passes PASS, $fails FAIL, $notrun NOT RUN"
[ "${fails:-0}" = 0 ]
