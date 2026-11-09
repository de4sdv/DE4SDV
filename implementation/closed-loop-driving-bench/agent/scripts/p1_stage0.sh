#!/bin/bash
# WP2 stage 0 on P1: build drivingAgent (FEO + 4 Rust activities + C++ over FFI + mw::com) and
# agent_tap with the S-CORE toolchain, then run one paced skeleton run:
#   agent (fake 10 Hz frames -> pace datagrams -> one chain per frame) + agent_tap in a second
#   process (mw::com across the process boundary), 30 s, then SIGINT.
# Output: /opt/de4sdv-agent/runs/stage0/ (agent log, tap summary, FEO_PACE lines, build log).
set -uo pipefail
cd /opt/src/feo
RUN=/opt/de4sdv-agent/runs/stage0
rm -rf $RUN; mkdir -p $RUN
exec > >(tee $RUN/stage0.log) 2>&1
date -u +"start %T"
git diff --stat -- src/feo/src/scheduler.rs | tail -1
bazel build --config=x86_64-linux //de4sdv_bench/agent:driving_agent //de4sdv_bench/agent:agent_tap > $RUN/build.log 2>&1
BRC=$?
grep -E "^ERROR|error(\[|:)|warning: unused|Build completed|Elapsed" $RUN/build.log | head -40
echo "build rc=$BRC"
[ $BRC -eq 0 ] || exit 1
date -u +"built %T"
AG=bazel-bin/de4sdv_bench/agent/driving_agent
TAP=bazel-bin/de4sdv_bench/agent/agent_tap
CFG=/opt/src/feo/de4sdv_bench/agent/config/agent_config.stage0.json
MW=/opt/src/feo/de4sdv_bench/agent/mw_com_config_driving_agent.json
ls -la $AG $TAP
ldd $AG | head -12
rm -rf /tmp/mw_com_lola /dev/shm/lola-* 2>/dev/null
export FEO_PACE_SOCKET=/tmp/de4sdv_feo_pace.sock
setsid nohup $AG $CFG > $RUN/agent.stdout 2> $RUN/drivingAgent.stderr < /dev/null &
APID=$!
sleep 2
timeout 60 $TAP 30 $RUN/tap.json $MW > $RUN/tap.stdout 2>&1
TRC=$?
echo "tap rc=$TRC: $(cat $RUN/tap.stdout)"
kill -INT $APID
for i in $(seq 1 50); do kill -0 $APID 2>/dev/null || break; sleep 0.1; done
kill -0 $APID 2>/dev/null && { echo "agent still running after SIGINT + 5 s"; kill -9 $APID; }
wait $APID 2>/dev/null; echo "agent exit rc=$?"
echo "== tap.json"; cat $RUN/tap.json
echo "== agent log events"; python3 - <<'EOF'
import json, collections
recs = [json.loads(l) for l in open("/opt/de4sdv-agent/runs/stage0/score/drivingAgent.jsonl")]
c = collections.Counter(r["event"] for r in recs)
print(dict(c))
print("first:", recs[0]["event"], recs[0]["data"])
print("last:", recs[-1]["event"], recs[-1]["data"])
plans = [r for r in recs if r["event"] == "out.plan"]
cmds = [r for r in recs if r["event"] == "out.command"]
if plans:
    print("plans frames", plans[0]["data"]["frameIndex"], "..", plans[-1]["data"]["frameIndex"], "n", len(plans))
if cmds:
    print("cmd age (step-plan) ms set:", sorted({r["data"]["step_capture_sim_ms"] - r["data"]["plan_capture_sim_ms"] for r in cmds}))
EOF
echo "== FEO_PACE"; grep -c "FEO_PACE" $RUN/drivingAgent.stderr; grep "FEO_PACE" $RUN/drivingAgent.stderr | head -3; grep "FEO_PACE" $RUN/drivingAgent.stderr | tail -2
python3 - <<'EOF'
import json, re
ev = [json.loads(m.group(1)) for m in (re.search(r"FEO_PACE (\{.*\})", l) for l in open("/opt/de4sdv-agent/runs/stage0/drivingAgent.stderr")) if m]
if ev:
    print("cycles", len(ev), "events", sum(e["events"] for e in ev), "skipped", sum(e["skipped"] for e in ev))
    t = [e["t_real_ns"] for e in ev]; d = sorted((b - a) / 1e6 for a, b in zip(t, t[1:]))
    if d: print("inter-cycle ms p50 %.1f min %.1f max %.1f" % (d[len(d)//2], d[0], d[-1]))
EOF
grep -i -E "error|panic|warn" $RUN/drivingAgent.stderr | head -10
date -u +"end %T"
