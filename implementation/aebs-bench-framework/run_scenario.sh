#!/usr/bin/env bash
# Shared scenario runner parameterized by environment variables.
#
# A run is assembled in a private directory and canonical evidence changes only
# after the runtime is quiescent and independent validation succeeds.
#
# Required environment variables:
#   BENCH_ROOT             — absolute path to the bench directory
#   FRAMEWORK_DIR          — absolute path to aebs-bench-framework
#   AEBS_INCREMENT         — increment id, e.g. INC-AEBS-009D
#   AEBS_PROFILE           — closed profile value, e.g. fresh_false_control
#   AEBS_CONTRACT          — absolute path to the contract YAML
#   AEBS_SCENARIO_CONFIG   — container-side scenario config path (ros2 param)
#   AEBS_EVIDENCE_DIR      — bench-relative evidence dir, e.g. evidence/009d
#   AEBS_PROFILE_PREFIX    — profile subdirectory under evidence dir,
#                            e.g. "profiles" (009D/009E) or the profile name
#                            itself (009F single-scenario layout).
#                            Leave empty for the single-scenario layout where
#                            evidence lives at $AEBS_EVIDENCE_DIR/$PROFILE.
#   AEBS_OBSERVER_PARAM    — ros2 parameter name for the profile passed to the
#                            scenario observer (e.g. override_scenario,
#                            non_activation_scenario, degraded_input_profile)
#   AEBS_LAUNCH_ENV_PREFIX — prefix for the env var consumed by launch.sh
#                            (e.g. DE4SDV_009D)
#   AEBS_PROVENANCE_MODULE — python import path for the provenance builder
#                            (optional; if empty the framework default is used)
#
set -euo pipefail

: "${BENCH_ROOT:?BENCH_ROOT is required}"
: "${FRAMEWORK_DIR:?FRAMEWORK_DIR is required}"
: "${AEBS_INCREMENT:?AEBS_INCREMENT is required}"
: "${AEBS_PROFILE:?AEBS_PROFILE is required}"
: "${AEBS_CONTRACT:?AEBS_CONTRACT is required}"
: "${AEBS_SCENARIO_CONFIG:?AEBS_SCENARIO_CONFIG is required}"
: "${AEBS_EVIDENCE_DIR:?AEBS_EVIDENCE_DIR is required}"
: "${AEBS_OBSERVER_PARAM:?AEBS_OBSERVER_PARAM is required}"
: "${AEBS_LAUNCH_ENV_PREFIX:?AEBS_LAUNCH_ENV_PREFIX is required}"

BENCH="$BENCH_ROOT"
PROFILE="$AEBS_PROFILE"

# Resolve the evidence layout: profiles/ subdirectory or flat.
if [ -n "${AEBS_PROFILE_PREFIX:-}" ]; then
  EVIDENCE="$BENCH/$AEBS_EVIDENCE_DIR/$AEBS_PROFILE_PREFIX/$PROFILE"
else
  EVIDENCE="$BENCH/$AEBS_EVIDENCE_DIR/$PROFILE"
fi

RUNS="$EVIDENCE/runs"
CONTAINER="de4sdv-aebs-009b-runtime"
CANONICAL="$EVIDENCE/scenario-evidence.json"
if [ ! -e "$EVIDENCE" ]; then mkdir -p -m 0700 -- "$EVIDENCE"; fi
if [ -L "$EVIDENCE" ] || [ ! -d "$EVIDENCE" ]; then
  printf 'Unsafe evidence directory: %s\n' "$EVIDENCE" >&2
  exit 1
fi
if [ -L "$RUNS" ] || { [ -e "$RUNS" ] && [ ! -d "$RUNS" ]; }; then
  printf 'Unsafe runs path: %s\n' "$RUNS" >&2
  exit 1
fi
if [ ! -e "$RUNS" ]; then mkdir -m 0700 -- "$RUNS"; fi
python3 -c 'import pathlib,sys
root=pathlib.Path(sys.argv[1]); runs=pathlib.Path(sys.argv[2])
if root.is_symlink() or runs.is_symlink() or not runs.is_dir():
 raise SystemExit("unsafe evidence/run directory")
if not runs.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
 raise SystemExit("run directory escapes evidence root")' "$EVIDENCE" "$RUNS"
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
"${AEBS_LAUNCH_ENV_PREFIX}_PROFILE=$PROFILE" "${AEBS_LAUNCH_ENV_PREFIX}_RUN_DIR=$STAGE" "$BENCH/scripts/launch.sh"

# Exclusive creation (noclobber) rejects both symlink and regular-file log targets.
if [ -e "$OBSERVER_LOG" ] || [ -L "$OBSERVER_LOG" ]; then
  printf 'Refusing unsafe/existing observer log: %s\n' "$OBSERVER_LOG" >&2
  exit 1
fi
set -C
exec {observer_fd}>"$OBSERVER_LOG"
set +C
CONTAINER_RAW="/de4sdv/implementation/aebs-autoware-nominal-vehicle-target-bench/${RAW#"$BENCH/"}"
set +e
docker exec --user "$(id -u):$(id -g)" --env HOME=/home/aw "$CONTAINER" bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  source /de4sdv/implementation/aebs-autoware-executable-bench/workspace/install/setup.bash
  source /de4sdv/implementation/aebs-autoware-nominal-vehicle-target-bench/workspace/install/setup.bash
  set -u
  exec timeout --signal=TERM "$1" ros2 run de4sdv_aebs_009b_bench scenario_observer \
    --ros-args \
    -p "scenario_config:=$2" \
    -p "raw_output:=$3" \
    -p "timeout_s:=$4" \
    -p "'"$AEBS_OBSERVER_PARAM"'=$5"
' observer "$SUPERVISOR_TIMEOUT" \
  "$AEBS_SCENARIO_CONFIG" \
  "$CONTAINER_RAW" "$SCENARIO_TIMEOUT" "$PROFILE" >&"$observer_fd" 2>&1
observer_exit=$?
set -e
exec {observer_fd}>&-

# The launch process owns launch.log. Stop it and wait before any artifact hash.
stop_runtime
if [ -L "$LAUNCH_LOG" ] || [ ! -f "$LAUNCH_LOG" ]; then
  printf 'Missing/unsafe launch log after runtime stop: %s\n' "$LAUNCH_LOG" >&2
  exit 1
fi
if LC_ALL=C grep -Eq 'QH[0-9]+ qhull input error|ConvexHull::.*ERROR|process has died|Traceback \(most recent call last\)' "$LAUNCH_LOG"; then
  printf 'Rejected runtime log: native geometry/process failure detected in %s\n' "$LAUNCH_LOG" >>"$OBSERVER_LOG"
  observer_exit=97
fi

# Build run metadata.
RAW_RELATIVE="${RAW#"$BENCH/"}"
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
extra=json.loads(sys.argv[5]) if sys.argv[5] else {}
payload={"observer_exit_code":int(sys.argv[2]),"raw_output":sys.argv[3]}
if sys.argv[4]: payload[sys.argv[4]]=sys.argv[6]
payload.update(extra)
write(pathlib.Path(sys.argv[1]),payload)
' "$FAILURE" "$observer_exit" "$RAW_RELATIVE" "${AEBS_METADATA_PROFILE_FIELD:-}" "{}" "$PROFILE"

# Build provenance using the framework helper.
PYTHONPATH="$FRAMEWORK_DIR:$BENCH/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 -c '
from datetime import datetime,timezone
import json,os,pathlib,sys,tempfile
from validate_scenario_evidence import _live_provenance_fields
from evidence_document import sha256_file
bench=pathlib.Path(sys.argv[1]); profile=sys.argv[4]; contract_path=sys.argv[5]
import yaml
contract=yaml.safe_load(open(contract_path,encoding="utf-8"))
value=_live_provenance_fields(bench)
value.update(captured_utc=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),command_exit_code=int(sys.argv[3]))
# Apply contract-declared extra provenance fields.
for key, expr in contract.get("provenance_extras",{}).items():
    if expr=="profile":
        value[key]=profile
    elif expr=="config_sha256":
        value[key]=sha256_file(bench/"config"/contract["matrix_config"])
    elif expr=="execution_manifest":
        from execution_identity import execution_manifest_sha256
        value[key]=execution_manifest_sha256(bench)
fd,name=tempfile.mkstemp(prefix=".provenance.",dir=pathlib.Path(sys.argv[2]).parent)
with os.fdopen(fd,"w",encoding="utf-8") as stream: json.dump(value,stream,sort_keys=True,separators=(",",":"),allow_nan=False); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
os.replace(name,sys.argv[2])
' "$BENCH" "$PROVENANCE" "$observer_exit" "$PROFILE" "$AEBS_CONTRACT"

# Publish the immutable run directory before validation so all canonical paths
# are final. A rejected run may remain for diagnosis but cannot alter canonical.
mv -T -- "$STAGE" "$FINAL"
RUNTIME_STOPPED=1
python3 -c '
import hashlib,json,pathlib,sys
bench=pathlib.Path(sys.argv[1]); run_id=sys.argv[3]; evidence_subpath=sys.argv[4]; records={}
for name,leaf in (("observer_raw","observer-raw.json"),("observer_log","observer.log"),("launch_log","launch.log"),("run_metadata","run-metadata.json"),("map_runtime","map-runtime.json")):
 relative=f"evidence/{evidence_subpath}/runs/{run_id}/{leaf}"; path=bench/relative
 if path.is_symlink() or not path.is_file(): raise SystemExit(f"missing/unsafe artifact: {relative}")
 records[name]={"path":relative,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
path=pathlib.Path(sys.argv[2]); path.write_text(json.dumps(records,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
' "$BENCH" "$FINAL/artifacts.json" "$RUN_ID" "${FINAL#"$BENCH/evidence/"}"

# Build and validate evidence using the framework.
PYTHONPATH="$FRAMEWORK_DIR:$BENCH/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 "$FRAMEWORK_DIR/evidence_pipeline.py" \
  --contract "$AEBS_CONTRACT" --bench-root "$BENCH" \
  --raw "$FINAL/observer-raw.json" \
  --provenance "$FINAL/provenance.json" --artifacts "$FINAL/artifacts.json" \
  --profile "$PROFILE" --output "$STAGED"
PYTHONPATH="$FRAMEWORK_DIR:$BENCH/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 "$FRAMEWORK_DIR/evidence_validator.py" \
  --contract "$AEBS_CONTRACT" --bench-root "$BENCH" --candidate "$STAGED"
PYTHONPATH="$FRAMEWORK_DIR:$BENCH/scripts${PYTHONPATH:+:$PYTHONPATH}" python3 -c '
import pathlib,sys
from evidence_document import publish_validated_evidence
publish_validated_evidence(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
' "$STAGED" "$CANONICAL" "$BENCH"
printf 'Retained replay-validated %s %s evidence: %s\n' "$AEBS_INCREMENT" "$PROFILE" "$CANONICAL"
