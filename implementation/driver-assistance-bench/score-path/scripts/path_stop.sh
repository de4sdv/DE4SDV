#!/bin/bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): the stop run's path stop on the S-CORE host (shared contract 3 of
# the S1 build; S1-BUILD-PLAN.md section 4, "Stop run"). The session's step path_stop_<run> calls it at go + 12 s.
#
#   path_stop.sh <out>
#
# 1. Refuses (rc 10) unless a Launch Manager of a mode-full start runs (the state of start_score_side.sh).
# 2. Runs the bundle's LmControl client as root (bin/lm_control_client, launch-manager/control/), which switches the
#    Launch Manager to the run target path_stopped: the identity recorder and the candidate's process stay, the
#    actuation adapter, gatewayd and someipd end (launch-manager/config/launch_manager_config.json). The bundle is the
#    one the start staged (state/staging.json "bundle"; DA_B2_BUNDLE otherwise).
# 3. Checks the effect within DA_PATH_STOP_EFFECT_S (default 5): no process of actuation_adapter, gatewayd or someipd,
#    and the candidate's and the recorder's processes still there.
# 4. Prints exactly one line on stdout and exits with its rc:
#      {"runTarget":"path_stopped","stopInstantRealNs":<int>,"stopInstantMonoNs":<int>,"rc":<int>}
#    The stop instant is the client's: the instant the Launch Manager reported path_stopped active (its components
#    outside the target had ended), on CLOCK_REALTIME and CLOCK_MONOTONIC of this host (the clock of mono_ns in the
#    candidate's and the adapter's records). Without a settlement it is the request's instant; without a request,
#    this script's own clocks. Everything else goes to <out>: path_stop.log, path_stop.json (the client's record,
#    the processes before and after, the bundle, the client's sha256), lm_control_client.out/.err.
#
# rc: 0 stopped and checked; the client's rc 2-6 (lm_control_client.h: 3 no LmControl service, 4 refused, 5 not
# settled, 6 settled on another target); 10 refused (no Launch Manager of mode full); 11 no client or configuration
# in the bundle; 12 the client gave no record; 13 the switch was reported but its effect is not seen.
set -uo pipefail
trap '' PIPE
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib_score_side.sh
. "$HERE/lib_score_side.sh"

OUT=${1:?usage: path_stop.sh <out>}
RUN_TARGET=path_stopped
: "${DA_PATH_STOP_SETTLE_S:=30}"
: "${DA_PATH_STOP_EFFECT_S:=5}"
GONE="actuation_adapter gatewayd someipd"
KEPT="identity_recorder vision_pilot"
mkdir -p "$OUT" || exit 10
LOG=$OUT/path_stop.log
log() { ss_log "$*" >> "$LOG"; }

now_pair() { "$DA_PYTHON" -c 'import time; print(time.time_ns(), time.monotonic_ns())'; }

# pids <names>: "name=pid,pid name=..." of the staged processes
pids() { local n; for n in "$@"; do printf '%s=%s ' "$n" "$(ss_pids_of "$n" | tr '\n' ',' | sed 's/,$//')"; done; }

# emit <rc> <real_ns> <mono_ns> <reason> [client record file]
emit() {
  local rc=$1 real=$2 mono=$3 reason=$4 record=${5:-}
  local line="{\"runTarget\":\"$RUN_TARGET\",\"stopInstantRealNs\":$real,\"stopInstantMonoNs\":$mono,\"rc\":$rc}"
  log "result rc=$rc: $reason"
  "$DA_PYTHON" - "$OUT/path_stop.json" "$line" "$reason" "$record" "${BEFORE:-}" "$(pids $GONE $KEPT)" \
      "${BUNDLE:-}" "${CLIENT:-}" "${LM_PID:-}" <<'PY' || log "path_stop.json not written"
import hashlib, json, os, sys
path, line, reason, record, before, after, bundle, client, lm_pid = sys.argv[1:10]
def table(text):
    out = {}
    for item in text.split():
        name, _, value = item.partition("=")
        out[name] = [int(p) for p in value.split(",") if p]
    return out
doc = json.loads(line)
doc.update({"reason": reason, "processesBefore": table(before), "processesAfter": table(after),
            "bundle": bundle or None, "client": client or None, "launchManagerPid": int(lm_pid) if lm_pid else None})
if client and os.path.isfile(client):
    doc["clientSha256"] = hashlib.sha256(open(client, "rb").read()).hexdigest()
if record:
    doc["clientRecord"] = json.loads(record)
with open(path, "w") as f:
    json.dump(doc, f, indent=1)
    f.write("\n")
PY
  printf '%s\n' "$line"
  exit "$rc"
}

read -r NOW_REAL NOW_MONO < <(now_pair)
log "path_stop: stage $DA_STAGE, out $OUT, run target $RUN_TARGET"
if ! LM_PID=$(ss_lm_running); then
  emit 10 "$NOW_REAL" "$NOW_MONO" "no Launch Manager runs: nothing to stop"
fi
MODE=$(ss_state MODE)
if [ "$MODE" != full ]; then
  emit 10 "$NOW_REAL" "$NOW_MONO" "the Launch Manager runs mode '${MODE:-unknown}', not full: no candidate path to stop"
fi
BUNDLE=$("$DA_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("bundle") or "")' \
  "$DA_STAGE/state/staging.json" 2>/dev/null)
[ -n "$BUNDLE" ] || BUNDLE=$DA_B2_BUNDLE
CLIENT=$BUNDLE/bin/lm_control_client
CONFIG=$BUNDLE/config/launch_manager/mw_com_config_lm_control_client.json
if [ ! -x "$CLIENT" ] || [ ! -f "$CONFIG" ]; then
  emit 11 "$NOW_REAL" "$NOW_MONO" "the bundle $BUNDLE has no LmControl client ($CLIENT) or no configuration ($CONFIG)"
fi
BEFORE=$(pids $GONE $KEPT)
log "before: $BEFORE"
log "running $CLIENT --run-target $RUN_TARGET --mw-com-config $CONFIG"
# shellcheck disable=SC2086
(cd "$OUT" && timeout -k 5 $((DA_PATH_STOP_SETTLE_S + 20)) $DA_SUDO env "LD_LIBRARY_PATH=$DA_STAGE/lib" "$CLIENT" \
   --run-target "$RUN_TARGET" --mw-com-config "$CONFIG" --settle-timeout-ms $((DA_PATH_STOP_SETTLE_S * 1000)) \
   > "$OUT/lm_control_client.out" 2> "$OUT/lm_control_client.err")
CRC=$?
log "client exit $CRC: $(tail -n 1 "$OUT/lm_control_client.out" 2>/dev/null)"
RECORD=$(grep '^{' "$OUT/lm_control_client.out" 2>/dev/null | tail -n 1)
PARSED=$("$DA_PYTHON" - "$RECORD" "$RUN_TARGET" <<'PY'
import json, sys
try:
    r = json.loads(sys.argv[1])
    assert r["runTarget"] == sys.argv[2]
    vals = [r["rc"], r["stopInstantRealNs"], r["stopInstantMonoNs"]]
    assert all(isinstance(v, int) and not isinstance(v, bool) for v in vals)
    print(*vals)
except Exception:
    print("bad")
PY
)
if [ "$PARSED" = bad ] || [ -z "$PARSED" ]; then
  read -r NOW_REAL NOW_MONO < <(now_pair)
  emit 12 "$NOW_REAL" "$NOW_MONO" "the client (exit $CRC) gave no record of $RUN_TARGET"
fi
read -r RC REAL MONO <<< "$PARSED"
[ "$RC" = "$CRC" ] || log "the client's record says rc $RC, its exit status is $CRC: the record counts"
if [ "$RC" != 0 ]; then
  emit "$RC" "$REAL" "$MONO" "the client did not stop the path: $(sed -n 's/.*"error":"\(.*\)"}$/\1/p' <<< "$RECORD")" \
    "$RECORD"
fi
deadline=$(( $(date +%s) + DA_PATH_STOP_EFFECT_S ))
while :; do
  left=""
  for n in $GONE; do [ -z "$(ss_pids_of "$n")" ] || left="$left $n"; done
  lost=""
  for n in $KEPT; do [ -n "$(ss_pids_of "$n")" ] || lost="$lost $n"; done
  [ -z "$left$lost" ] && break
  if [ "$(date +%s)" -ge "$deadline" ]; then
    emit 13 "$REAL" "$MONO" "path_stopped reported, but after ${DA_PATH_STOP_EFFECT_S} s still running:${left:- none}; gone:${lost:- none}" \
      "$RECORD"
  fi
  sleep 0.2
done
emit 0 "$REAL" "$MONO" "path_stopped active: $GONE ended, $KEPT running" "$RECORD"
