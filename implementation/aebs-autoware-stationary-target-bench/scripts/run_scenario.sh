#!/usr/bin/env bash
# A run is assembled in a private directory and canonical evidence changes only
# after the runtime is quiescent and independent validation succeeds.
set -euo pipefail

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="$BENCH/evidence/009c"
RUNS="$EVIDENCE/runs"
CONTAINER="de4sdv-aebs-009c-runtime"
CANONICAL="$EVIDENCE/scenario-evidence.json"
if [ -L "$EVIDENCE" ] || [ ! -d "$EVIDENCE" ]; then
  printf 'Unsafe or missing 009C evidence directory: %s\n' "$EVIDENCE" >&2
  exit 1
fi
if [ -L "$RUNS" ] || { [ -e "$RUNS" ] && [ ! -d "$RUNS" ]; }; then
  printf 'Unsafe 009C runs path: %s\n' "$RUNS" >&2
  exit 1
fi
if [ ! -e "$RUNS" ]; then mkdir -m 0700 -- "$RUNS"; fi
python3 -c 'import pathlib,sys
root=pathlib.Path(sys.argv[1]); runs=pathlib.Path(sys.argv[2])
if root.is_symlink() or runs.is_symlink() or not runs.is_dir():
 raise SystemExit("unsafe 009C evidence/run directory")
if not runs.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
 raise SystemExit("009C run directory escapes evidence root")' "$EVIDENCE" "$RUNS"
RUN_ID="$(python3 -c 'import datetime,secrets; print(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+secrets.token_hex(8))')"
STAGE="$RUNS/.$RUN_ID.tmp"
FINAL="$RUNS/$RUN_ID"
mkdir -m 0700 -- "$STAGE"
RAW="$STAGE/observer-raw.json"
OBSERVER_LOG="$STAGE/observer.log"
LAUNCH_LOG="$STAGE/launch.log"
FAILURE="$STAGE/run-metadata.json"
PROVENANCE="$STAGE/provenance.json"
ARTIFACTS="$STAGE/artifacts.json"
STAGED="$FINAL/.scenario-evidence.candidate.json"
RUNTIME_STOPPED=0

stop_runtime() {
  if [ "$RUNTIME_STOPPED" -eq 1 ]; then return; fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  if [ -f "$STAGE/runtime.pid" ] && [ ! -L "$STAGE/runtime.pid" ]; then
    pid="$(tr -dc '0-9' < "$STAGE/runtime.pid")"
    if [ -n "$pid" ]; then wait "$pid" 2>/dev/null || true; fi
    rm -f -- "$STAGE/runtime.pid"
  fi
  RUNTIME_STOPPED=1
}
cleanup() {
  status=$?
  stop_runtime
  rm -rf -- "$STAGE"
  return "$status"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

SCENARIO_TIMEOUT="$(python3 -c 'import sys,yaml; print(yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["timeouts"]["scenario_s"])' "$BENCH/runtime-lock.yaml")"
SUPERVISOR_TIMEOUT="$(python3 -c 'import math,sys; value=float(sys.argv[1]); assert math.isfinite(value) and value > 0; print(value + 5.0)' "$SCENARIO_TIMEOUT")"
python3 "$BENCH/scripts/verify_runtime.py" \
  --bench "$BENCH" --inherited-bench "$BENCH/../aebs-autoware-executable-bench"
DE4SDV_009C_RUN_DIR="$STAGE" "$BENCH/scripts/launch.sh"

# Exclusive creation (noclobber) rejects both symlink and regular-file log targets.
if [ -e "$OBSERVER_LOG" ] || [ -L "$OBSERVER_LOG" ]; then
  printf 'Refusing unsafe/existing observer log: %s\n' "$OBSERVER_LOG" >&2
  exit 1
fi
set -C
exec {observer_fd}>"$OBSERVER_LOG"
set +C
CONTAINER_RAW="/de4sdv/implementation/aebs-autoware-stationary-target-bench/${RAW#"$BENCH/"}"
set +e
docker exec --user "$(id -u):$(id -g)" --env HOME=/home/aw "$CONTAINER" bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  source /de4sdv/implementation/aebs-autoware-stationary-target-bench/workspace/install/setup.bash
  set -u
  exec timeout --signal=TERM "$1" ros2 run de4sdv_aebs_009c_bench scenario_observer \
    --ros-args \
    -p "scenario_config:=$2" \
    -p "raw_output:=$3" \
    -p "timeout_s:=$4"
' observer "$SUPERVISOR_TIMEOUT" \
  "/de4sdv/implementation/aebs-autoware-stationary-target-bench/workspace/install/de4sdv_aebs_009c_bench/share/de4sdv_aebs_009c_bench/config/scenario-009c-aeb-mrm.yaml" \
  "$CONTAINER_RAW" "$SCENARIO_TIMEOUT" >&"$observer_fd" 2>&1
observer_exit=$?
set -e
exec {observer_fd}>&-

# The launch process owns launch.log. Stop it and wait before any artifact hash.
stop_runtime
if [ -L "$LAUNCH_LOG" ] || [ ! -f "$LAUNCH_LOG" ]; then
  printf 'Missing/unsafe launch log after runtime stop: %s\n' "$LAUNCH_LOG" >&2
  exit 1
fi

python3 -c '
import json,os,pathlib,sys,tempfile
def write(path,value):
 fd,name=tempfile.mkstemp(prefix="."+path.name+".",dir=path.parent)
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as stream:
   json.dump(value,stream,sort_keys=True,separators=(",",":"),allow_nan=False); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
  os.replace(name,path)
 finally:
  pathlib.Path(name).unlink(missing_ok=True)
write(pathlib.Path(sys.argv[1]),{"observer_exit_code":int(sys.argv[2]),"raw_output":sys.argv[3]})
' "$FAILURE" "$observer_exit" "evidence/009c/runs/$RUN_ID/observer-raw.json"

PYTHONPATH="$BENCH/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 -c '
from datetime import datetime,timezone
import json,os,pathlib,sys,tempfile
from validate_scenario_evidence import _live_provenance_fields
value=_live_provenance_fields(pathlib.Path(sys.argv[1])); value.update(captured_utc=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),command_exit_code=int(sys.argv[3]))
fd,name=tempfile.mkstemp(prefix=".provenance.",dir=pathlib.Path(sys.argv[2]).parent)
with os.fdopen(fd,"w",encoding="utf-8") as stream: json.dump(value,stream,sort_keys=True,separators=(",",":"),allow_nan=False); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
os.replace(name,sys.argv[2])
' "$BENCH" "$PROVENANCE" "$observer_exit"

# Publish the immutable run directory before validation so all canonical paths
# are final. A rejected run may remain for diagnosis but cannot alter canonical.
mv -T -- "$STAGE" "$FINAL"
RUNTIME_STOPPED=1
python3 -c '
import hashlib,json,pathlib,sys
bench=pathlib.Path(sys.argv[1]); run_id=sys.argv[3]; records={}
for name,leaf in (("observer_raw","observer-raw.json"),("observer_log","observer.log"),("launch_log","launch.log"),("run_metadata","run-metadata.json"),("map_runtime","map-runtime.json")):
 relative=f"evidence/009c/runs/{run_id}/{leaf}"; path=bench/relative
 if path.is_symlink() or not path.is_file(): raise SystemExit(f"missing/unsafe artifact: {relative}")
 records[name]={"path":relative,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
path=pathlib.Path(sys.argv[2]); path.write_text(json.dumps(records,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
' "$BENCH" "$FINAL/artifacts.json" "$RUN_ID"

python3 "$BENCH/scripts/evidence_document.py" \
  --bench-root "$BENCH" --raw "$FINAL/observer-raw.json" \
  --provenance "$FINAL/provenance.json" --artifacts "$FINAL/artifacts.json" \
  --output "$STAGED"
python3 "$BENCH/scripts/validate_scenario_evidence.py" --bench-root "$BENCH" "$STAGED"
PYTHONPATH="$BENCH/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 -c '
import pathlib,sys
from evidence_document import publish_validated_evidence
publish_validated_evidence(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
' "$STAGED" "$CANONICAL" "$BENCH"
printf 'Retained replay-validated 009C evidence: %s\n' "$CANONICAL"
