#!/usr/bin/env bash
set -euo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INHERITED="$BENCH/../aebs-autoware-executable-bench"
VERIFY_MAP="$BENCH/scripts/verify_map.py"
MAP_CACHE="${DE4SDV_MAP_CACHE:-$HOME/.cache/de4sdv/autoware/maps}"
export DE4SDV_MAP_CACHE="$MAP_CACHE"
runtime_name="de4sdv-aebs-009c-runtime"
run_dir="${DE4SDV_009C_RUN_DIR:-$BENCH/evidence/009c}"
if [ -L "$run_dir" ] || [ ! -d "$run_dir" ]; then
  printf 'Unsafe or missing 009C run directory: %s\n' "$run_dir" >&2
  exit 1
fi
python3 -c 'import pathlib,sys
bench=pathlib.Path(sys.argv[1]).resolve(strict=True)
run=pathlib.Path(sys.argv[2])
if run.is_symlink() or not run.is_dir() or not run.resolve(strict=True).is_relative_to(bench/"evidence"/"009c"):
 raise SystemExit("unsafe 009C run directory")' "$BENCH" "$run_dir"
pid_file="$run_dir/runtime.pid"
launch_log="$run_dir/launch.log"
if [ -e "$launch_log" ] || [ -L "$launch_log" ]; then
  printf 'Refusing unsafe/existing launch log: %s\n' "$launch_log" >&2
  exit 1
fi
set -C
exec {launch_fd}>"$launch_log"
set +C
python3 "$BENCH/scripts/verify_runtime.py" --bench "$BENCH" --inherited-bench "$INHERITED"
python3 "$VERIFY_MAP" --cache "$MAP_CACHE" --bench "$BENCH" \
  --output "$run_dir/map-runtime.json"

# Remove only the uniquely named prior 009C container; never signal an unverified host PID.
if [ -f "$pid_file" ]; then
  old_pid="$(tr -dc '0-9' < "$pid_file")"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    old_command="$(ps -p "$old_pid" -o args= 2>/dev/null || true)"
    case "$old_command" in
      *docker*de4sdv-aebs-009c-runtime*) kill "$old_pid" 2>/dev/null || true ;;
    esac
  fi
  rm -f "$pid_file"
fi
docker rm -f "$runtime_name" >/dev/null 2>&1 || true

docker compose -f "$BENCH/compose.yaml" run --rm --name "$runtime_name" bench bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  source /de4sdv/implementation/aebs-autoware-stationary-target-bench/workspace/install/setup.bash
  set -u
  exec ros2 launch de4sdv_aebs_009c_bench aebs_009c_bench.launch.py \
    map_path:=/map-cache/sample-map-planning
' >&"$launch_fd" 2>&1 &
pid=$!
printf '%s\n' "$pid" > "$pid_file"

sleep 5
if [ "$(docker inspect -f '{{.State.Running}}' "$runtime_name" 2>/dev/null || true)" != true ]; then
  set +e
  wait "$pid"
  status=$?
  set -e
  rm -f "$pid_file"
  [ "$status" -ne 0 ] || status=1
  printf '009C launch container did not remain running; inspect %s.\n' \
    "$launch_log" >&2
  exit "$status"
fi
printf '009C process started as PID %s; this is not readiness, scenario, safety, or compliance evidence.\n' "$pid"
