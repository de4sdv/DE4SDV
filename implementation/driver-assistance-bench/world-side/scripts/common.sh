# Shared part of the world side's session entries (warmup.sh, calibrate.sh, run_scenario.sh); sourced, not run.
#
# The road: warmup.sh finds it once per session (survey with the longest setting, SC-DRIVING-012 at 60 km/h:
# 280 + 40 m) and writes it to $WORLD_STATE (default <the host's session out folder>/world_start.json); the later
# entries read it there, so every run of the session starts at the same road:lane:s. WORLD_START=road:lane:s
# skips the survey.
#
# env: SIM_PY (the CARLA 1.0 venv's Python; default python3), WORLD_MAP (Town06_Opt: from CARLA's AdditionalMaps
#      pack, by the exact name the server lists; world-side/README.md "The maps pack"), CARLA_PORT (2000),
#      WORLD_STATE (see above), WORLD_START.
WS_SCRIPTS=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WS=$(cd -- "$WS_SCRIPTS/.." && pwd)
BENCH=$(cd -- "$WS/.." && pwd)
PY=${SIM_PY:-python3}
WORLD_MAP=${WORLD_MAP:-Town06_Opt}
CARLA_PORT=${CARLA_PORT:-2000}

ws_state_file() {   # ws_state_file <out>: the session's state file of the road
  if [ -n "${WORLD_STATE:-}" ]; then echo "$WORLD_STATE"
  elif [ -n "${DA_OUT:-}" ]; then echo "$DA_OUT/world_start.json"
  else echo "$(cd -- "$(dirname -- "$1")" && pwd)/world_start.json"; fi
}

ws_read_start() {   # ws_read_start <out>: prints road:lane:s, or fails
  local f; f=$(ws_state_file "$1")
  if [ -n "${WORLD_START:-}" ]; then echo "$WORLD_START"; return 0; fi
  [ -s "$f" ] || { echo "no road chosen yet: $f is missing (warmup.sh writes it; or set WORLD_START)" >&2; return 1; }
  "$PY" -c 'import json, sys; print(json.load(open(sys.argv[1]))["start"])' "$f"
}

ws_side() {   # ws_side <subcommand> <args...>: da_world_side.py on the local CARLA server
  local cmd=("$PY" "$WS/da_world_side.py" "$1" --map "$WORLD_MAP" --port "$CARLA_PORT" "${@:2}")
  echo "+ ${cmd[*]}"
  "${cmd[@]}"
}

ws_setting() {   # ws_setting <scenario> <setting>: SC-DRIVING-012 + 20kmh|20|SC-DRIVING-012@20 -> SC-DRIVING-012@20
  local sc=$1 se=$2
  case "$se" in *@*) echo "$se"; return 0 ;; esac
  se=${se%kmh}; se=${se%km/h}
  case "$sc" in SC-DRIVING-*) ;; *) sc=SC-DRIVING-012 ;; esac   # the calibration runs use that road and vehicle
  echo "$sc@$se"
}
