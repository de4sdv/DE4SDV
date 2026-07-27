#!/usr/bin/env bash
set -euo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INHERITED="$BENCH/../aebs-autoware-executable-bench"
VERIFY_MAP="$BENCH/scripts/verify_map.py"
MAP_CACHE="${DE4SDV_MAP_CACHE:-$HOME/.cache/de4sdv/autoware/maps}"
export DE4SDV_MAP_CACHE="$MAP_CACHE"
runtime_name="de4sdv-aebs-009b-runtime"
profile="${DE4SDV_009D_PROFILE:-}"
mode="009b"
launch_profile_argument=""
scenario_config_argument=""
warning_margin_argument=""
if [ -n "$profile" ]; then
  case "$profile" in
    fresh_false_control|fresh_true_conscious_override|stale|missing|malformed|future_stamped) ;;
    *) printf 'Invalid 009D override profile: %s\n' "$profile" >&2; exit 2 ;;
  esac
  mode="009d"
  launch_profile_argument="override_scenario:=$profile"
  scenario_config_argument="scenario_config_name:=scenario-009d-moving-vehicle-target.yaml"
  warning_margin="$(python3 -c 'import math,sys,yaml; value=float(yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["outcome_contract"]["warning_margin_m"]); assert math.isfinite(value) and value > 0; print(value)' "$BENCH/config/scenario-009d-moving-vehicle-target.yaml")"
  warning_margin_argument="warning_margin_m:=$warning_margin"
  run_dir="${DE4SDV_009D_RUN_DIR:-$BENCH/evidence/009d}"
else
  run_dir="${DE4SDV_009B_RUN_DIR:-$BENCH/evidence/009b}"
fi
if [ -L "$run_dir" ] || [ ! -d "$run_dir" ]; then
  printf 'Unsafe or missing %s run directory: %s\n' "$mode" "$run_dir" >&2
  exit 1
fi
python3 -c 'import pathlib,sys
bench=pathlib.Path(sys.argv[1]).resolve(strict=True)
run=pathlib.Path(sys.argv[2])
mode=sys.argv[3]
if run.is_symlink() or not run.is_dir() or not run.resolve(strict=True).is_relative_to(bench/"evidence"/mode):
 raise SystemExit(f"unsafe {mode} run directory")' "$BENCH" "$run_dir" "$mode"
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
  --evidence-namespace "$mode" --output "$run_dir/map-runtime.json"

# Remove only the uniquely named prior 009B container; never signal an unverified host PID.
if [ -f "$pid_file" ]; then
  old_pid="$(tr -dc '0-9' < "$pid_file")"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    old_command="$(ps -p "$old_pid" -o args= 2>/dev/null || true)"
    case "$old_command" in
      *docker*de4sdv-aebs-009b-runtime*) kill "$old_pid" 2>/dev/null || true ;;
    esac
  fi
  rm -f "$pid_file"
fi
docker rm -f "$runtime_name" >/dev/null 2>&1 || true

docker compose -f "$BENCH/compose.yaml" run --rm --name "$runtime_name" bench bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  source /de4sdv/implementation/aebs-autoware-nominal-vehicle-target-bench/workspace/install/setup.bash
  set -u
  arguments=(map_path:=/map-cache/sample-map-planning)
  for argument in "$1" "$2" "$3"; do
    if [ -n "$argument" ]; then arguments+=("$argument"); fi
  done
  exec ros2 launch de4sdv_aebs_009b_bench aebs_009b_bench.launch.py "${arguments[@]}"
' launch "$launch_profile_argument" "$scenario_config_argument" "$warning_margin_argument" >&"$launch_fd" 2>&1 &
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
  printf '009B launch container did not remain running; inspect %s.\n' \
    "$launch_log" >&2
  exit "$status"
fi
printf '%s process started as PID %s; this is not readiness, scenario, safety, or compliance evidence.\n' "$mode" "$pid"
