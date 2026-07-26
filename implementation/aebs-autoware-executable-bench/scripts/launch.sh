#!/usr/bin/env bash
set -uo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAP_CACHE="${DE4SDV_MAP_CACHE:-$HOME/.cache/de4sdv/autoware/maps}"
export DE4SDV_MAP_CACHE="$MAP_CACHE"
runtime_name="de4sdv-aebs-009a-runtime"
mkdir -p "$BENCH/evidence"
python3 "$BENCH/scripts/verify_map.py" --cache "$MAP_CACHE" || exit $?
rm -f "$BENCH/workspace/bench.pid"
docker rm -f "$runtime_name" >/dev/null 2>&1 || true
docker compose -f "$BENCH/compose.yaml" run --rm --name "$runtime_name" bench bash -lc "
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  set -u
  exec ros2 launch de4sdv_aebs_bench aebs_bench.launch.py map_path:=/map-cache/sample-map-planning
" >"$BENCH/evidence/launch.log" 2>&1 &
pid=$!
printf '%s\n' "$pid" > "$BENCH/workspace/bench.pid"
sleep 5
if [ "$(docker inspect -f '{{.State.Running}}' "$runtime_name" 2>/dev/null || true)" = true ]; then
  status=0
  launched=true
else
  wait "$pid"
  process_status=$?
  status=1
  if [ "$process_status" -ne 0 ]; then status="$process_status"; fi
  launched=false
fi
python3 "$BENCH/scripts/evidence_metadata.py" "$BENCH/evidence/launch-status.json" \
  --status "$status" --launched "$launched"
if [ "$status" -ne 0 ]; then exit "$status"; fi
printf 'Bench process started as PID %s; this is not readiness or scenario evidence.\n' "$pid"
