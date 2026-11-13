#!/bin/bash
# Stage 1a on P1: drivingAgent with the embedded CPython planner (de4sdv_planner, stub engine:
# numpy only, no GPU), fake frames with six patterned BGRA images and a moving vehicle pose.
#   run A: correct checkpoint pin -> condition + infer every step, plans over mw::com (tap)
#   run B: wrong pin -> REQ-DRIVING-035 refusal: no plan ever, mode kRefused with both hashes
set -uo pipefail
cd /opt/src/feo
OUT=/opt/de4sdv-agent/runs/stage1a
rm -rf $OUT; mkdir -p $OUT
exec > >(tee $OUT/stage1a.log) 2>&1
date -u +"start %T"
bazel build --config=x86_64-linux //de4sdv_bench/agent:driving_agent //de4sdv_bench/agent:agent_tap > $OUT/build.log 2>&1
BRC=$?; grep -E "^ERROR|error:|Build completed" $OUT/build.log | head -20; echo "build rc=$BRC"; [ $BRC -eq 0 ] || exit 1
AG=bazel-bin/de4sdv_bench/agent/driving_agent; TAP=bazel-bin/de4sdv_bench/agent/agent_tap
MW=/opt/src/feo/de4sdv_bench/agent/mw_com_config_driving_agent.json
VENV_PY=/opt/src/wp2a-venv/bin/python
PYHOME=$(dirname "$(dirname "$(readlink -f "$VENV_PY")")")
echo "venv python -> $(readlink -f $VENV_PY); lib $PYHOME/lib"
$VENV_PY -c "import numpy, sys; print('numpy', numpy.__version__, sys.version.split()[0])"
STUB=/opt/de4sdv-agent/stub_checkpoint.bin
head -c 4096 /dev/urandom > $STUB
SHA=$(sha256sum $STUB | cut -c1-64)
run() {  # name pin seconds
  local NAME=$1 PIN=$2 SECS=$3 RUN=$OUT/$1
  mkdir -p $RUN
  cat > $RUN/planner.json <<EOF
{"engine": "stub", "checkpoint_path": "$STUB", "checkpoint_sha256": "$PIN"}
EOF
  cat > $RUN/agent.json <<EOF
{"run_dir": "$RUN", "mw_com_config": "$MW", "source": "fake", "inference": "python",
 "python_executable": "$VENV_PY", "python_paths": ["/opt/src/feo/de4sdv_bench/agent/python"],
 "planner_config": "$RUN/planner.json", "fake_rate_hz": 10.0, "fake_first_frame": 5000,
 "fake_speed_kmh": 18.0, "fake_image_width": 64, "fake_image_height": 36, "wheelbase_m": 2.85}
EOF
  rm -rf /tmp/mw_com_lola /dev/shm/lola-* 2>/dev/null
  FEO_PACE_SOCKET=/tmp/de4sdv_feo_pace.sock LD_LIBRARY_PATH=$PYHOME/lib setsid nohup $AG $RUN/agent.json \
    > $RUN/agent.stdout 2> $RUN/drivingAgent.stderr < /dev/null &
  local APID=$!
  sleep 3
  timeout $((SECS + 30)) $TAP $SECS $RUN/tap.json $MW > $RUN/tap.stdout 2>&1; echo "[$NAME] tap rc=$?: $(tail -1 $RUN/tap.stdout)"
  kill -INT $APID; for i in $(seq 1 50); do kill -0 $APID 2>/dev/null || break; sleep 0.1; done
  kill -0 $APID 2>/dev/null && { echo "[$NAME] agent still running 5 s after SIGINT"; kill -9 $APID; }
  wait $APID 2>/dev/null; echo "[$NAME] agent exit rc=$?"
  echo "[$NAME] tap: $(cat $RUN/tap.json)"
}
run A "$SHA" 30
run B "$(printf '0%.0s' $(seq 1 64))" 10
python3 - <<'EOF'
import json, collections
for name in ("A", "B"):
    base = "/opt/de4sdv-agent/runs/stage1a/" + name
    recs = [json.loads(l) for l in open(base + "/score/drivingAgent.jsonl")]
    c = collections.Counter(r["event"] for r in recs)
    print(name, "events", dict(c))
    for r in recs:
        if r["event"] in ("error",) or (r["event"] == "ready" and r["data"].get("activity") == "inferPlan"):
            print("  ", r["event"], json.dumps(r["data"])[:400])
    modes = collections.Counter((r["data"]["mode"], r["data"]["cause"]) for r in recs if r["event"] == "out.mode")
    print("  modes (mode, cause):", dict(modes))
    plans = [r["data"] for r in recs if r["event"] == "out.plan"]
    if plans:
        p = plans[-1]
        print("  plans", len(plans), "first frame", plans[0]["frameIndex"], "last", p["frameIndex"],
              "x[0..2]", [round(s["x"], 3) for s in p["samples"][:3]], "planner", p.get("planner"))
    try:
        ci = [json.loads(l)["data"] for l in open(base + "/score/checkpointInputs.jsonl")]
        withrows = [d for d in ci if "egomotion_history" in d]
        ms = sorted(d["condition_ms"] for d in ci)
        print("  C2 records", len(ci), "with rows", len(withrows), "primed", sum(d["primed"] for d in ci),
              ("condition_ms p50 %.3f max %.3f" % (ms[len(ms)//2], ms[-1])) if ms else "(no condition calls)")
        if withrows:
            rows = withrows[-1]["egomotion_history"]
            print("  last checkpoint rows: speed", rows[-1][0], "acc", rows[-1][1], "yaw", rows[-1][2], "curv", rows[-1][3],
                  "| any nonzero yaw/curv:", any(r[2] != 0 or r[3] != 0 for d in withrows for r in d["egomotion_history"]))
    except FileNotFoundError:
        print("  no C2 file")
EOF
grep -i -E "Traceback|Error|panic" /opt/de4sdv-agent/runs/stage1a/*/drivingAgent.stderr | grep -v "mw::log" | head -10
date -u +"end %T"
