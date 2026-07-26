#!/usr/bin/env bash
set -uo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$BENCH/evidence"
python3 "$BENCH/scripts/evidence_metadata.py" "$BENCH/evidence/source-import.json" --status 0
python3 "$BENCH/scripts/record_source_heads.py" \
  "$BENCH" "$BENCH/evidence/source-import.json" || exit $?
docker compose -f "$BENCH/compose.yaml" run --rm bench bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  set -u
  cd /de4sdv/implementation/aebs-autoware-executable-bench/workspace
  colcon build --symlink-install --parallel-workers 1 \
    --packages-select \
      autoware_autonomous_emergency_braking \
      autoware_diagnostic_graph_aggregator \
      autoware_mrm_emergency_stop_operator \
      autoware_mrm_handler \
      autoware_simple_planning_simulator \
      autoware_vehicle_cmd_gate \
      tier4_map_launch \
      de4sdv_aebs_bench \
    --cmake-args -DBUILD_TESTING=OFF
' >"$BENCH/evidence/build.log" 2>&1
status=$?
python3 "$BENCH/scripts/evidence_metadata.py" "$BENCH/evidence/build-status.json" \
  --status "$status" --built "$([ "$status" -eq 0 ] && printf true || printf false)"
exit "$status"
