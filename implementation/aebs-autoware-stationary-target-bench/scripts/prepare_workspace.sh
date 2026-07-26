#!/usr/bin/env bash
set -euo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$BENCH/scripts/verify_runtime.py" --bench "$BENCH"
mkdir -p "$BENCH/workspace/src" "$BENCH/evidence/009b"
docker compose -f "$BENCH/compose.yaml" run --rm bench bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  set -u
  cd /de4sdv/implementation/aebs-autoware-stationary-target-bench/workspace
  ln -sfn /de4sdv/implementation/aebs-autoware-stationary-target-bench/src/de4sdv_aebs_009b_bench src/de4sdv_aebs_009b_bench
  test "$(find src -mindepth 1 -maxdepth 1 -printf "." | wc -c)" -eq 1
  test -L src/de4sdv_aebs_009b_bench
'
printf '009B overlay workspace prepared; no upstream source was imported.\n'
