#!/bin/bash
# WP2 on the G4 (RTX PRO 6000): drivingAgent with the real checkpoint engine inside the S-CORE binary.
# The fake world feeds the frame store with the profile-exact rig (make_fake_rig.py, 1920-wide
# images); everything is stamped "stage-1b-fake-world": no driving evidence, a timing and
# integration check of the engine port.
#   R refusal    wrong pin: kRefused from the first step, the engine is never built
#   K checkpoint pinned nuplan-epoch-5: warm-up + parity in inferPlan's startup, then ~120 s at 10 Hz
# Usage: g4_checkpoint.sh <package dir>   (binaries in <pkg>/bin, the overlay in <pkg>/de4sdv_bench)
set -uo pipefail
PKG=$(readlink -f "$1")
OUT=$PKG/runs; mkdir -p $OUT
exec > >(tee $OUT/g4_checkpoint.log) 2>&1
date -u +"start %T"
nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total --format=csv,noheader
AG=$PKG/bin/driving_agent; TAP=$PKG/bin/agent_tap
MW=$PKG/de4sdv_bench/agent/mw_com_config_driving_agent.json
VEH=$PKG/de4sdv_bench/actuation-adapter/config/vehicle_limits.json
VENV_PY=/opt/de4sdv-p2/work/venv312-cu128-cudnn9.26.0.51/bin/python
PYHOME=$(dirname "$(dirname "$(readlink -f "$VENV_PY")")")
echo "venv python -> $(readlink -f $VENV_PY); libpython: $(ls $PYHOME/lib/libpython3.12.so* | tr '\n' ' ')"
CKPT=/opt/de4sdv-p2/ckpt/nuplan-epoch-5.pt
SHA=$(sha256sum $CKPT | cut -c1-64); echo "checkpoint sha256 $SHA"
ZERO=$(printf '0%.0s' $(seq 1 64))
$VENV_PY $PKG/de4sdv_bench/agent/scripts/make_fake_rig.py --out $OUT/rig.json || { echo "rig generation failed"; exit 1; }
run() {  # name pin seconds
  local NAME=$1 PIN=$2 SECS=$3 RUN=$OUT/$1
  rm -rf $RUN; mkdir -p $RUN
  cat > $RUN/planner.json <<EOF
{"engine": "checkpoint", "checkpoint_path": "$CKPT", "checkpoint_sha256": "$PIN", "p2_root": "/opt/de4sdv-p2",
 "cudnn": 92600, "input_sample": "/opt/de4sdv-p2/work/inputs_real_sample.npz",
 "fp32_reference": "/opt/de4sdv-p2/work/output_fp32_reference.npy",
 "profile": "/opt/de4sdv-p2/src/Model/plugins/alpasim_driver/alpasim_autoe2e/configs/calibration/nuplan.json"}
EOF
  cat > $RUN/agent.json <<EOF
{"run_dir": "$RUN", "mw_com_config": "$MW", "vehicle_config": "$VEH", "source": "fake", "inference": "python",
 "python_executable": "$VENV_PY", "python_paths": ["$PKG/de4sdv_bench/agent/python"],
 "planner_config": "$RUN/planner.json", "fake_rig": "$OUT/rig.json", "fake_rate_hz": 10.0, "fake_first_frame": 5000,
 "fake_speed_kmh": 18.0, "campaign_id": "wp2-g4-checkpoint", "run_role": "integration-$NAME",
 "scenario": "closedLoopRoute", "fault": "none", "checkpoint_case": "$( [ "$PIN" = "$ZERO" ] && echo wrong_pin || echo pinned )",
 "score_feo_revision": "313b3d8+event-trigger"}
EOF
  rm -rf /tmp/mw_com_lola /dev/shm/lola-* 2>/dev/null
  FEO_PACE_SOCKET=/tmp/de4sdv_feo_pace.sock LD_LIBRARY_PATH=$PYHOME/lib setsid nohup $AG $RUN/agent.json \
    > $RUN/agent.stdout 2> $RUN/drivingAgent.stderr < /dev/null &
  local APID=$!
  # the engine builds before FEO starts (about a minute): wait for the agent's services
  for i in $(seq 1 180); do grep -q '"event":"offered"' $RUN/score/drivingAgent.jsonl 2>/dev/null && break; kill -0 $APID 2>/dev/null || break; sleep 1; done
  echo "[$NAME] services offered after ${i} s"
  sleep 2
  timeout $((SECS + 60)) $TAP $SECS $RUN/tap.json $MW > $RUN/tap.stdout 2>&1; echo "[$NAME] tap rc=$?"
  kill -INT $APID; for i in $(seq 1 100); do kill -0 $APID 2>/dev/null || break; sleep 0.1; done
  kill -0 $APID 2>/dev/null && { echo "[$NAME] agent still running 10 s after SIGINT"; kill -9 $APID; }
  wait $APID 2>/dev/null; echo "[$NAME] agent exit rc=$?"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader
}
run R "$ZERO" 15
run K "$SHA" 180
OUT_DIR=$OUT $VENV_PY - <<'EOF'
import json, collections, os, math
import numpy as np
OUT = os.environ["OUT_DIR"]
MODES = {0: "kStarting", 1: "kDriving", 2: "kStopResponse", 3: "kStandstill", 4: "kRefused"}
for name in "RK":
    base = f"{OUT}/{name}"
    try:
        recs = [json.loads(l) for l in open(base + "/score/drivingAgent.jsonl")]
    except FileNotFoundError:
        print(name, "no agent log"); continue
    ev = collections.Counter(r["event"] for r in recs)
    print(f"== {name}: events", dict(sorted(ev.items())))
    seq = []
    for r in recs:
        if r["event"] == "out.mode":
            m = MODES.get(r["data"]["mode"], r["data"]["mode"])
            if not seq or seq[-1][0] != m:
                seq.append((m, r["data"]["frameIndex"]))
    print("   modes:", seq)
    for r in recs:
        if r["event"] in ("error", "stop_response.begin", "run_record"):
            print("  ", r["event"], json.dumps(r["data"])[:400])
        if r["event"] == "engine":
            d = r["data"]; s = d.get("setup", {}); er = s.get("engineRecord", {}) if isinstance(s, dict) else {}
            print("   engine build (before FEO) setup_s", round(d.get("setup_s", 0), 1), "refused", d.get("refused"),
                  "| engine", json.dumps(er)[:700])
        if r["event"] == "ready":
            d = r["data"]
            print("   ready", d.get("activity"), "bind", json.dumps(d.get("bind")) if d.get("bind") else "",
                  "t_mono_ns", r["t_mono_ns"])
        if r["event"] == "rig":
            res = r["data"].get("result", {})
            print("   rig pose err mm:", res.get("rig_pose_err_mm"))
        if r["event"] == "stop":
            print("   stop:", json.dumps(r["data"])[:600])
    plans = [r["data"] for r in recs if r["event"] == "out.plan"]
    if plans:
        cms = [p["planner"]["compute_ms"] for p in plans if isinstance(p.get("planner"), dict) and "compute_ms" in p["planner"]]
        fin = sum(all(math.isfinite(s["acceleration"]) and math.isfinite(s["curvature"]) for s in p["samples"]) for p in plans)
        print(f"   plans {len(plans)} frames {plans[0]['frameIndex']}..{plans[-1]['frameIndex']} finite {fin}")
        if cms:
            a = np.array(cms); print("   engine compute_ms p50 %.1f p90 %.1f p99 %.1f max %.1f" % tuple(np.percentile(a, [50, 90, 99, 100])))
        frames = [p["frameIndex"] for p in plans]
        gaps = collections.Counter(b - a for a, b in zip(frames, frames[1:]))
        print("   plan frame steps:", dict(sorted(gaps.items())))
    # frame ready (newest camera arrival) -> command production, per step (monotonic)
    try:
        ci = {json.loads(l)["data"]["frame"]: json.loads(l)["data"] for l in open(base + "/score/checkpointInputs.jsonl")}
    except FileNotFoundError:
        ci = {}
    cmd = [r["data"] for r in recs if r["event"] == "out.command"]
    lat = []
    for c in cmd:
        step_frame = c.get("step_capture_sim_ms", 0) // 100
        d = ci.get(step_frame)
        if not d: continue
        arr = [cam["arrival_mono_ns"] for cam in d["cameras"] if cam.get("arrival_mono_ns")]
        if arr and c.get("productionTime") is not None:
            lat.append(c["productionTime"] * 1000 - max(arr) / 1e6)
    if lat:
        a = np.array(lat); print("   frame-ready -> command ms p50 %.1f p90 %.1f p99 %.1f max %.1f (n %d)" % (*np.percentile(a, [50, 90, 99, 100]), len(a)))
    cond = [d["condition_ms"] for d in ci.values() if d.get("conditioned")]
    if cond:
        a = np.array(cond); print("   condition_ms p50 %.1f p99 %.1f max %.1f" % tuple(np.percentile(a, [50, 99, 100])))
    try:
        tap = json.load(open(base + "/tap.json")); print("   tap:", json.dumps(tap)[:500])
    except Exception as e:
        print("   tap: none", e)
EOF
grep -h -o "FEO_PACE {[^}]*}" $OUT/K/agent.stdout $OUT/K/drivingAgent.stderr 2>/dev/null | tail -3
grep -i -E "Traceback|Error|panic|Segmentation" $OUT/*/drivingAgent.stderr | grep -v -E "mw::log|UserWarning" | head -12
date -u +"end %T"
