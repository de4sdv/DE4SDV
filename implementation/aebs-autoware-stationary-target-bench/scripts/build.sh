#!/usr/bin/env bash
set -euo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$BENCH/scripts/verify_runtime.py" --bench "$BENCH"
mkdir -p "$BENCH/evidence/009c"
docker compose -f "$BENCH/compose.yaml" run --rm bench bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  set -u
  cd /de4sdv/implementation/aebs-autoware-stationary-target-bench/workspace
  test -L src/de4sdv_aebs_009c_bench
  colcon build --symlink-install --parallel-workers 1 \
    --packages-select de4sdv_aebs_009c_bench
' >"$BENCH/evidence/009c/build.log" 2>&1
printf '009C overlay package build command completed; no runtime or scenario claim is implied.\n'
