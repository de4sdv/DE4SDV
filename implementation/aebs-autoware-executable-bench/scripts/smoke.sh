#!/usr/bin/env bash
set -uo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pid_file="$BENCH/workspace/bench.pid"
runtime_name="de4sdv-aebs-009a-runtime"
readiness_timeout="$(python3 -c 'import sys,yaml; print(yaml.safe_load(open(sys.argv[1]))["readiness"]["collection_timeout_seconds"])' "$BENCH/runtime-lock.yaml")"
cleanup() {
  docker stop --time 10 "$runtime_name" >/dev/null 2>&1 || true
  if [ -f "$pid_file" ]; then
    pid="$(cat "$pid_file")"
    kill -TERM "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -KILL "$pid" 2>/dev/null || true
    rm -f "$pid_file"
  fi
}
trap cleanup EXIT INT TERM
"$BENCH/scripts/launch.sh" || exit $?
docker exec -e DE4SDV_READINESS_TIMEOUT="$readiness_timeout" "$runtime_name" bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  set -u
  ros2 run de4sdv_aebs_bench readiness_collector \
    --output /de4sdv/implementation/aebs-autoware-executable-bench/evidence/readiness-ros.json \
    --timeout "$DE4SDV_READINESS_TIMEOUT"
'
status=$?
python3 "$BENCH/scripts/evidence_metadata.py" "$BENCH/evidence/readiness.json" \
  --status "$status" --launched true --ready "$([ "$status" -eq 0 ] && printf true || printf false)" \
  --details "$BENCH/evidence/readiness-ros.json"
exit "$status"
