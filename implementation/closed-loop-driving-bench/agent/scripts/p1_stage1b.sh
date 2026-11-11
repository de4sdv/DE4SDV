#!/bin/bash
# Stage 1b on P1: drivingAgent with the decision logic (agent_logic), the frame store fed by the
# fake world, the run record, and the embedded CPython planner (stub engine: numpy only, no GPU).
#   A nominal          30 s   starting -> driving at the full 66-pose window, no stop
#   B camera_missing   15 s   cam_front_right withheld from frame 5080: stop at 5080, kCameraMissing
#   C plan_stale       15 s   planning stalls from 5080: stop at 5083 (400 ms > 300 ms), kPlanStale
#   D plan_invalid_nan 15 s   NaN plan at 5080: stop at 5080, kPlanInvalid; later plans never named
#   E refused          10 s   wrong pin: kRefused from the first step, no plan (REQ-DRIVING-035)
# The runs are judged afterwards by the bench's own case-evaluators/evaluate_run.py.
set -uo pipefail
cd /opt/src/feo
OUT=/opt/de4sdv-agent/runs/stage1b
mkdir -p $OUT
for N in A B C D E; do case "${RUNS:-ABCDE}" in *"$N"*) rm -rf $OUT/$N ;; esac; done
exec > >(tee $OUT/stage1b_${RUNS:-ABCDE}.log) 2>&1
date -u +"start %T"
bazel build --config=x86_64-linux //de4sdv_bench/agent:driving_agent //de4sdv_bench/agent:agent_tap > $OUT/build.log 2>&1
BRC=$?; grep -E "^ERROR|error:|Build completed" $OUT/build.log | head -20; echo "build rc=$BRC"; [ $BRC -eq 0 ] || exit 1
AG=bazel-bin/de4sdv_bench/agent/driving_agent; TAP=bazel-bin/de4sdv_bench/agent/agent_tap
MW=/opt/src/feo/de4sdv_bench/agent/mw_com_config_driving_agent.json
VEH=/opt/src/feo/de4sdv_bench/actuation-adapter/config/vehicle_limits.json
VENV_PY=/opt/src/wp2a-venv/bin/python
PYHOME=$(dirname "$(dirname "$(readlink -f "$VENV_PY")")")
STUB=/opt/de4sdv-agent/stub_checkpoint.bin
[ -f $STUB ] || head -c 4096 /dev/urandom > $STUB
SHA=$(sha256sum $STUB | cut -c1-64)
ZERO=$(printf '0%.0s' $(seq 1 64))
RUNS=${RUNS:-ABCDE}  # e.g. RUNS=E to repeat one run
run() {  # name scenario fault pin seconds checkpoint_case extra_json
  local NAME=$1 SCEN=$2 FAULT=$3 PIN=$4 SECS=$5 CASE=$6 EXTRA=$7 RUN=$OUT/$1
  case "$RUNS" in *"$NAME"*) ;; *) return 0 ;; esac
  mkdir -p $RUN
  printf '{"engine": "stub", "checkpoint_path": "%s", "checkpoint_sha256": "%s"}\n' "$STUB" "$PIN" > $RUN/planner.json
  cat > $RUN/agent.json <<EOF
{"run_dir": "$RUN", "mw_com_config": "$MW", "vehicle_config": "$VEH", "source": "fake", "inference": "python",
 "python_executable": "$VENV_PY", "python_paths": ["/opt/src/feo/de4sdv_bench/agent/python"],
 "planner_config": "$RUN/planner.json", "fake_rate_hz": 10.0, "fake_first_frame": 5000,
 "fake_speed_kmh": 18.0, "fake_image_width": 64, "fake_image_height": 36,
 "campaign_id": "wp2-stage-1b", "run_role": "integration-$NAME", "scenario": "$SCEN", "fault": "$FAULT",
 "checkpoint_case": "$CASE", "score_feo_revision": "313b3d8+event-trigger" $EXTRA}
EOF
  rm -rf /tmp/mw_com_lola /dev/shm/lola-* 2>/dev/null
  FEO_PACE_SOCKET=/tmp/de4sdv_feo_pace.sock LD_LIBRARY_PATH=$PYHOME/lib setsid nohup $AG $RUN/agent.json \
    > $RUN/agent.stdout 2> $RUN/drivingAgent.stderr < /dev/null &
  local APID=$!
  sleep 3
  timeout $((SECS + 30)) $TAP $SECS $RUN/tap.json $MW > $RUN/tap.stdout 2>&1; echo "[$NAME] tap rc=$?"
  kill -INT $APID; for i in $(seq 1 50); do kill -0 $APID 2>/dev/null || break; sleep 0.1; done
  kill -0 $APID 2>/dev/null && { echo "[$NAME] agent still running 5 s after SIGINT"; kill -9 $APID; }
  wait $APID 2>/dev/null; echo "[$NAME] agent exit rc=$?  tap: $(cat $RUN/tap.json 2>/dev/null | head -c 400)"
}
run A closedLoopRoute    none             "$SHA"  30 pinned    ''
run B degradedInputOrPlan camera_missing  "$SHA"  15 pinned    ', "fault_camera_stop_frame": 5080, "fault_camera_index": 2'
run C degradedInputOrPlan plan_stale      "$SHA"  15 pinned    ', "fault_plan_stall_frame": 5080'
run D degradedInputOrPlan plan_invalid_nan "$SHA" 15 pinned    ', "fault_plan_invalid_frame": 5080'
run E checkpointRefusal  none             "$ZERO" 10 wrong_pin ''
python3 - <<'EOF'
import json, collections
MODES = {0: "kStarting", 1: "kDriving", 2: "kStopResponse", 3: "kStandstill", 4: "kRefused"}
for name in "ABCDE":
    base = "/opt/de4sdv-agent/runs/stage1b/" + name
    try:
        recs = [json.loads(l) for l in open(base + "/score/drivingAgent.jsonl")]
    except FileNotFoundError:
        print(name, "no agent log"); continue
    c = collections.Counter(r["event"] for r in recs)
    print(f"== {name}: events", dict(sorted(c.items())))
    seq = []
    for r in recs:
        if r["event"] == "out.mode":
            m = MODES.get(r["data"]["mode"], r["data"]["mode"])
            if not seq or seq[-1][0] != m:
                seq.append((m, r["data"]["frameIndex"]))
    print("   mode sequence (mode, first frame):", seq)
    for r in recs:
        if r["event"] in ("stop_response.begin", "stop_response.standstill", "error", "run_record"):
            print("  ", r["event"], json.dumps(r["data"])[:300])
        if r["event"] == "stop":
            print("   stop:", json.dumps(r["data"])[:500])
    cmds = [r["data"] for r in recs if r["event"] == "out.command"]
    plans = [r["data"] for r in recs if r["event"] == "out.plan"]
    if plans:
        print("   plans", len(plans), "frames", plans[0]["frameIndex"], "..", plans[-1]["frameIndex"])
    if cmds:
        refs = collections.Counter(c["planReference"] for c in cmds if c["acceleration"] <= -3.99)
        print("   commands", len(cmds), "| stop commands by planReference:", dict(refs))
EOF
grep -i -E "Traceback|panic|Segmentation|AddressSanitizer" $OUT/*/drivingAgent.stderr | head -10
date -u +"end %T"
