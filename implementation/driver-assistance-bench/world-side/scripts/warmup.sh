#!/bin/bash
# The simulator host's warm-up of a session (entry ENTRY_SIM_WARMUP; session/README.md "Entry-point contracts").
#
#   warmup.sh <out_dir>     exit 0 when the warm-up pass ended; 2 a bench error (world side); 3 no road found
#
# 1. survey (unless WORLD_START is set): straight driving lanes long enough for the longest setting
#    (SURVEY_SETTING, default SC-DRIVING-012@60: 280 + 40 m); the first candidate becomes the session's road,
#    written to world_start.json (see common.sh) and to <out>/world_start.json;
# 2. warmup: the hero (role_name hero), its front camera (role_name front) and the target along that road with
#    every camera rendering, the chase recorder's view included (the session starts the recorder first). The
#    hero is moved by pose, never by a control, and is destroyed at the end (da_world_side.py warmup).
# The candidate and the adapter are not running yet: the S-CORE side starts only for the runs.
# env: see common.sh; SURVEY_SETTING, WARMUP_SETTING (SC-DRIVING-012@20).
set -uo pipefail
OUT=${1:?out dir}; mkdir -p "$OUT"
# shellcheck source=common.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
SURVEY_SETTING=${SURVEY_SETTING:-SC-DRIVING-012@60}; WARMUP_SETTING=${WARMUP_SETTING:-SC-DRIVING-012@20}
STATE=$(ws_state_file "$OUT")

if [ -n "${WORLD_START:-}" ]; then
  START=$WORLD_START; SOURCE="WORLD_START"
else
  ws_side survey --setting "$SURVEY_SETTING" --run-dir "$OUT/survey" --limit 20; rc=$?
  [ "$rc" = 0 ] || { echo "FAIL survey rc=$rc"; exit "$rc"; }
  START=$("$PY" -c 'import json, sys; c = json.load(open(sys.argv[1]))["candidates"]; print(c[0]["start"] if c else "")' \
          "$OUT/survey/simulator/survey.json") || exit 2
  [ -n "$START" ] || { echo "FAIL the survey found no straight road for $SURVEY_SETTING on $WORLD_MAP"; exit 3; }
  SOURCE="survey $SURVEY_SETTING: the first candidate by (road, lane, s)"
fi
"$PY" - "$STATE" "$OUT/world_start.json" "$START" "$SOURCE" "$WORLD_MAP" <<'PY'
import json, sys
rec = {"start": sys.argv[3], "source": sys.argv[4], "map": sys.argv[5]}
for path in sys.argv[1:3]:
    with open(path, "w") as f:
        json.dump(rec, f)
print("road of this session:", json.dumps(rec))
PY
ws_side warmup --setting "$WARMUP_SETTING" --start "$START" --run-dir "$OUT/warmup"; rc=$?
[ "$rc" = 0 ] && echo "WARMUP_DONE start $START" || echo "FAIL warmup rc=$rc"
exit "$rc"
