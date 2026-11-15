#!/usr/bin/env bash
# One scripted end-to-end demo of the virtual E/E vehicle.
#
# It brings the vehicle up, waits for the architecture to be alive, captures
# every bus it can see, drives both functions through the signal plane and one
# diagnostic through the gateway, then tears the vehicle down and writes an
# archive a stranger can read:
#
#   results/<utc>-<head12>/
#     manifest.json        what ran: full head and tree, identity digest, vxedge,
#                          lock hash, image digests, kernel
#     identity-before.json the committed inputs this run started from
#     identity-after.json  the same inputs re-verified after the run
#     candump-*.log        four buses, absolute timestamps, one clock domain
#     commands.jsonl       what was commanded, with the client's t0 and t5
#     uds.txt              the tester's own output
#     logs/                every container's log, gateway stats included
#     summary.json         the numbers, and what they do not claim
#     summary.txt          the same, readable
#
# The exit code is the demo's verdict: non-zero means a required capture, copy,
# priming or diagnostic step failed, the declared command matrix was not met
# command by command, a denied frame crossed, a routed path carried nothing, the
# diagnostic was not a positive answer, or an input changed during the run.
#
# The run starts only from a clean, committed Git checkout (checks/run_identity.py);
# a tree copied without .git, with or without a .git-sha file, is refused.
#
# Host paths, overridable per run: HOST_PY (evaluators), CLIENT_PY (KUKSA
# client venv), UDS_PY, UDS_TOOL, UDS_CFG (OpenBSW UdsTool).
#
# Usage: checks/run_demo.sh [--duration 45] [--keep]
set -euo pipefail

DURATION=60
KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --duration) DURATION="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACKAGE="$ROOT/vehicle"

FL_CTR=vx-zone-fl-payload
RL_CTR=vx-zone-rl-payload
GW_CTR=vx-hpc1-payload
HOST_PY="${HOST_PY:-python3}"
CLIENT_PY="${CLIENT_PY:-/home/mrk/kv/bin/python}"
UDS_PY="${UDS_PY:-/home/mrk/uds/bin/python}"
UDS_TOOL="${UDS_TOOL:-/opt/ee/openbsw/tools/UdsTool/udsTool.py}"
UDS_CFG="${UDS_CFG:-/opt/ee/openbsw/tools/UdsTool/app/canConfig.json}"
SCENARIO=alternating-8

say() { printf '[demo] %s\n' "$*"; }
die() { printf '[demo] FAILED: %s\n' "$*" >&2; exit 1; }
# A required step that fails does not stop the collection, but fails the run.
REQUIRED_ERRORS=()
required_fail() { say "REQUIRED STEP FAILED: $*"; REQUIRED_ERRORS+=("$*"); }

# Bind the run to committed bytes before anything executes: full head and tree,
# a clean scope, every tracked input by content, and the external UDS tool.
IDENTITY_TMP="$(mktemp)"
"$HOST_PY" "$ROOT/checks/run_identity.py" capture --scope "$ROOT" \
  --extra uds_tool="$UDS_TOOL" --extra uds_config="$UDS_CFG" --out "$IDENTITY_TMP" \
  || { rm -f "$IDENTITY_TMP"; die "run identity rejected (see above); commit or remove local changes"; }
HEAD_SHA="$("$HOST_PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["git"]["head"])' "$IDENTITY_TMP")"
HEAD_TREE="$("$HOST_PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["git"]["tree"])' "$IDENTITY_TMP")"
HEAD_BRANCH="$("$HOST_PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["git"]["branch"] or "detached")' "$IDENTITY_TMP")"
OUT="$ROOT/results/$(date -u +%Y%m%dT%H%M%SZ)-${HEAD_SHA:0:12}"
mkdir -p "$OUT/logs"
mv "$IDENTITY_TMP" "$OUT/identity-before.json"
IDENTITY_SHA256="$(sha256sum "$OUT/identity-before.json" | cut -d' ' -f1)"

pid_of() { podman inspect -f '{{.State.Pid}}' "$1" 2>/dev/null; }

teardown() {
  [ "${TORN_DOWN:-0}" -eq 1 ] && return 0
  TORN_DOWN=1
  if [ "$KEEP" -eq 1 ]; then
    say "--keep: leaving the vehicle up"
    return 0
  fi
  say "tearing the vehicle down"
  vxedge experiment down >"$OUT/logs/experiment-down.log" 2>&1 || true
}
trap 'rc=$?; [ $rc -ne 0 ] && say "aborted with exit $rc"; teardown; exit $rc' EXIT

# --- preconditions -----------------------------------------------------------
command -v vxedge >/dev/null || die "vxedge is not on PATH"
command -v podman >/dev/null || die "podman is not on PATH"
sudo -n true 2>/dev/null || die "passwordless sudo is required (nsenter into container netns)"
podman container exists ee-registry 2>/dev/null || die "the local registry container ee-registry does not exist"
podman start ee-registry >/dev/null 2>&1 || true

# The CLI defaults to unix:///run/vxedge.sock — the path a root daemon owns. A
# user-scoped daemon listens under XDG_RUNTIME_DIR; follow it instead of
# demanding a system service, and prove the endpoint answers before going on.
if [ -z "${VXEDGE_ENDPOINT:-}" ] && [ ! -S /run/vxedge.sock ]; then
  user_sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/vxedge.sock"
  [ -S "$user_sock" ] || die "no vxedged socket at /run/vxedge.sock or $user_sock"
  export VXEDGE_ENDPOINT="unix://$user_sock"
fi
timeout 20 vxedge status >/dev/null 2>&1 || die "vxedge cannot reach vxedged at ${VXEDGE_ENDPOINT:-unix:///run/vxedge.sock}"

# A container that exited in an earlier run keeps its name, and `up` then fails
# to create its replacement. Clear them before provisioning.
podman ps -a --filter status=exited --format '{{.Names}}' 2>/dev/null | grep '^vx-' | xargs -r podman rm -f >/dev/null 2>&1 || true

# The OTA service refuses to serve without a TUF root. Seed one per checkout
# with a throwaway key: the key goes into the archive, never into the tree.
if [ ! -f "$PACKAGE/ota-store/root.json" ]; then
  say "seeding the OTA store with a throwaway root (key written to the archive)"
  command -v vxota >/dev/null || die "vxota is not on PATH; the ota service needs a store"
  key_path="${OTA_KEY_PATH:-$HOME/.cache/de4sdv-ee/ota-demo.key}"
  mkdir -p "$(dirname "$key_path")"
  say "throwaway root key at $key_path (outside the tree and outside the archive)"
  vxota keygen --artifacts-dir "$PACKAGE/ota-store" --out-priv "$key_path" \
    >"$OUT/logs/ota-keygen.log" 2>&1 || die "vxota keygen failed (see logs/ota-keygen.log)"
fi

# --- manifest ----------------------------------------------------------------
{
  cat <<JSON
{
  "when_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_sha": "$HEAD_SHA",
  "git_head": "$HEAD_SHA",
  "git_tree": "$HEAD_TREE",
  "git_branch": "$HEAD_BRANCH",
  "identity_sha256": "$IDENTITY_SHA256",
  "scenario": "$SCENARIO",
  "vxedge": "$(vxedge --version 2>/dev/null | head -1)",
  "lock_sha256": "$(sha256sum "$PACKAGE/vxp.lock" 2>/dev/null | cut -d' ' -f1)",
  "ota_root_sha256": "$(sha256sum "$PACKAGE/ota-store/root.json" 2>/dev/null | cut -d' ' -f1)",
  "host": "$(uname -srmo)",
  "kernel_clock": "candump -ta and every process share CLOCK_REALTIME on one host",
JSON
  echo '  "images": ['
  awk '
    /^- ref:/ { ref=$0; sub(/^- ref:[ ]*/,"",ref) }
    /^[[:space:]]+digest:/ {
      d=$0; sub(/^[[:space:]]*digest:[ ]*/,"",d);
      printf("%s    {\"ref\": \"%s\", \"digest\": \"%s\"}", sep, ref, d); sep=",\n"
    }
  ' "$PACKAGE/vxp.lock"
  echo ''
  echo '  ]'
  echo '}'
} >"$OUT/manifest.json"

say "writing to $OUT"

# --- bring the vehicle up ----------------------------------------------------
say "starting from a clean vehicle"
vxedge experiment down >"$OUT/logs/experiment-preclean.log" 2>&1 || true
say "vehicle up (this is the package's own manifest, nothing hand-assembled)"
if ! timeout 180 vxedge experiment up --chdir "$PACKAGE" >"$OUT/logs/experiment-up.log" 2>&1; then
  tail -5 "$OUT/logs/experiment-up.log" >&2
  die "experiment up returned non-zero (see logs/experiment-up.log)"
fi

for ctr in "$FL_CTR" "$RL_CTR" "$GW_CTR"; do
  for _ in $(seq 1 60); do
    state="$(podman inspect -f '{{.State.Status}}' "$ctr" 2>/dev/null || true)"
    [ "$state" = "running" ] && break
    sleep 1
  done
  [ "$(podman inspect -f '{{.State.Status}}' "$ctr" 2>/dev/null || true)" = "running" ] || die "$ctr never reached running"
done
say "all three payloads are running"

say "waiting for the architecture to be alive (a status frame from the rear zone)"
alive=0
for _ in $(seq 1 30); do
  if podman exec "$RL_CTR" sh -c 'timeout 5 candump -T 1000 -n 1 vcan0' 2>/dev/null | grep -qi '281'; then
    alive=1
    break
  fi
done
[ "$alive" -eq 1 ] || die "no 0x281 status frame from the rear zone within 150 s"

# --- capture ----------------------------------------------------------------
# Put both plants into a known state first. Without this the first captured
# command is often a no-op — the previous run left the lamp on — and a no-op has
# no bus event to time, only the next periodic status frame to mis-attribute.
say "priming: headlamp off, wiper off, so every captured command is a transition"
gw_pid="$(pid_of "$GW_CTR")"
# A plant left in an unknown state turns the first command into a possible
# non-transition, so a failed prime ends the run here.
sudo nsenter -n -t "$gw_pid" -- "$CLIENT_PY" "$ROOT/checks/measure_client.py" \
  Vehicle.Body.Lights.Beam.Low.IsOn false 3.0 >/dev/null 2>&1 || die "headlamp prime did not converge"
sudo nsenter -n -t "$gw_pid" -- "$CLIENT_PY" "$ROOT/checks/measure_client.py" \
  Vehicle.Body.Windshield.Front.Wiping.Mode OFF 3.0 >/dev/null 2>&1 || die "wiper prime did not converge"
sleep 1

CAP_S=$((DURATION + 20))
say "capturing four buses for ${CAP_S}s"
podman exec "$FL_CTR" sh -c "timeout $CAP_S candump -ta vcan0 > /tmp/demo-fl.log 2>&1" & CAP1=$!
podman exec "$RL_CTR" sh -c "timeout $CAP_S candump -ta vcan0 > /tmp/demo-rl.log 2>&1" & CAP2=$!
podman exec "$GW_CTR" sh -c "timeout $CAP_S candump -ta vcan-front > /tmp/demo-gwf.log 2>&1" & CAP3=$!
podman exec "$GW_CTR" sh -c "timeout $CAP_S candump -ta vcan-rear > /tmp/demo-gwr.log 2>&1" & CAP4=$!
# The plan's deliverable asks for packet captures as well as traces. The
# interesting packets are the CAN-over-Ethernet datagrams, not all traffic.
CAP5=""
if command -v tcpdump >/dev/null 2>&1; then
  sudo timeout "$CAP_S" tcpdump -i any -U -w "$OUT/slice.pcap" \
    'udp and (port 10001 or port 10002 or port 20001 or port 20002)' \
    >"$OUT/logs/tcpdump.log" 2>&1 & CAP5=$!
else
  say "tcpdump is not installed: this archive has no packet capture"
fi
sleep 2

# --- drive ------------------------------------------------------------------
drive() { # arm path on off value...
  local arm="$1" path="$2" on="$3" off="$4"
  shift 4
  local value pid rec
  for value in "$@"; do
    pid="$(pid_of "$GW_CTR")"
    rec="$(sudo nsenter -n -t "$pid" -- "$CLIENT_PY" "$ROOT/checks/measure_client.py" "$path" "$value" 3.0 2>/dev/null | tail -1 || true)"
    if [ -z "$rec" ]; then
      printf '{"arm":"%s","path":"%s","on":"%s","off":"%s","value":"%s","ok":false,"t0":null,"t5":null}\n' \
        "$arm" "$path" "$on" "$off" "$value" >>"$OUT/commands.jsonl"
      say "$arm: client produced no record"
      continue
    fi
    "$HOST_PY" -c 'import json,sys; r=json.loads(sys.argv[1]); r.update(arm=sys.argv[2],on=sys.argv[3],off=sys.argv[4]); print(json.dumps(r))' \
      "$rec" "$arm" "$on" "$off" >>"$OUT/commands.jsonl"
    say "$arm -> $value: $("$HOST_PY" -c 'import json,sys;r=json.loads(sys.argv[1]);print("converged" if r.get("ok") else "DID NOT CONVERGE")' "$rec")"
    sleep 1
  done
}

: >"$OUT/commands.jsonl"
# Every step changes the value. A repeated value is not a transition: the
# provider has nothing new to send, so it would time nothing and pollute the
# table with a frame that belongs to the next command. These two lines are
# scenario alternating-8 in checks/demo_measure.py; change both together.
# drive() takes the on/off labels first, then the values: the earlier call
# passed eight words, so two became labels and each arm drove six commands
# (the twelve-command historical archives).
say "driving the headlamp through the front zone"
drive headlamp Vehicle.Body.Lights.Beam.Low.IsOn true false \
  true false true false true false true false
say "driving the wiper through the rear zone"
drive wiper Vehicle.Body.Windshield.Front.Wiping.Mode FAST OFF \
  FAST OFF FAST OFF FAST OFF FAST OFF

# --- diagnostic across the gateway ------------------------------------------
say "sending one UDS session request from the front bus to the rear ECU"
if [ -x "$UDS_PY" ] && [ -f "$UDS_TOOL" ]; then
  fl_pid="$(pid_of "$FL_CTR")"
  sudo nsenter -n -t "$fl_pid" -- "$UDS_PY" "$UDS_TOOL" session \
    --can --channel vcan0 --txid 7E0 --rxid 7E8 --id 3 --config "$UDS_CFG" \
    >"$OUT/uds.txt" 2>&1 || required_fail "UdsTool exited $? (output kept in uds.txt)"
  tail -3 "$OUT/uds.txt" | sed 's/^/[demo]   /'
else
  echo "UdsTool not installed on this host: $UDS_TOOL" >"$OUT/uds.txt"
  required_fail "UdsTool missing: $UDS_PY / $UDS_TOOL"
fi

# --- collect ----------------------------------------------------------------
# candump runs under `timeout`, so 124 is its normal end; anything else is a
# capture that did not run for the whole window.
wait_capture() { # pid name
  local rc=0
  wait "$1" || rc=$?
  [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ] || required_fail "capture $2 exited $rc"
}
wait_capture "$CAP1" demo-fl
wait_capture "$CAP2" demo-rl
wait_capture "$CAP3" demo-gwf
wait_capture "$CAP4" demo-gwr
if [ -n "$CAP5" ]; then
  wait "$CAP5" 2>/dev/null || true
  sudo chown "$(id -u):$(id -g)" "$OUT/slice.pcap" 2>/dev/null || true
  pcap_packets="$(tcpdump -r "$OUT/slice.pcap" 2>/dev/null | wc -l | tr -d ' ')"
  say "packet capture: ${pcap_packets:-0} datagrams of the CAN-over-Ethernet path"
fi
copy_capture() { # container source destination
  podman exec "$1" cat "$2" >"$OUT/$3" 2>>"$OUT/logs/capture-copy.log" \
    || required_fail "capture copy failed: $1:$2 -> $3"
}
copy_capture "$FL_CTR" /tmp/demo-fl.log candump-front-left.log
copy_capture "$RL_CTR" /tmp/demo-rl.log candump-rear-left.log
copy_capture "$GW_CTR" /tmp/demo-gwf.log candump-gw-front.log
copy_capture "$GW_CTR" /tmp/demo-gwr.log candump-gw-rear.log
for ctr in "$FL_CTR" "$RL_CTR" "$GW_CTR"; do
  podman logs "$ctr" >"$OUT/logs/$ctr.log" 2>&1 || true
done

# --- verdict ----------------------------------------------------------------
say "stopping the gateway so it prints its counters, then tearing down"
podman stop -t 5 "$GW_CTR" >/dev/null 2>&1 || true
podman logs "$GW_CTR" >"$OUT/logs/$GW_CTR.log" 2>&1 || true
teardown
grep -A20 'gateway stats' "$OUT/logs/$GW_CTR.log" >"$OUT/gateway-stats.txt" 2>/dev/null || true
# Logs are the bulk of the archive and compress ~10x; the traces stay plain text
# because they are what a reader diffs.
gzip -9 "$OUT"/logs/*.log 2>/dev/null || true

# Re-verify every input the run started from; a change means the archive does
# not describe one revision.
IDENTITY_RC=0
"$HOST_PY" "$ROOT/checks/run_identity.py" verify --identity "$OUT/identity-before.json" \
  --out "$OUT/identity-after.json" || IDENTITY_RC=$?

set +e
"$HOST_PY" "$ROOT/checks/demo_measure.py" \
  --fl "$OUT/candump-front-left.log" \
  --rl "$OUT/candump-rear-left.log" \
  --gw-front "$OUT/candump-gw-front.log" \
  --gw-rear "$OUT/candump-gw-rear.log" \
  --commands "$OUT/commands.jsonl" \
  --uds "$OUT/uds.txt" \
  --scenario "$SCENARIO" \
  --out "$OUT/summary.json" >"$OUT/summary.txt" 2>&1
RC=$?
set -e
cat "$OUT/summary.txt"
if [ "$IDENTITY_RC" -ne 0 ]; then
  say "inputs changed during the run (identity-after.json)"
  RC=1
fi
if [ "${#REQUIRED_ERRORS[@]}" -ne 0 ]; then
  printf '%s\n' "${REQUIRED_ERRORS[@]}" >"$OUT/required-errors.txt"
  say "required steps failed: $(printf '%s; ' "${REQUIRED_ERRORS[@]}")"
  RC=1
fi
say "verdict: $([ $RC -eq 0 ] && echo PASS || echo FAIL)"
say "archive: $OUT"
exit $RC
