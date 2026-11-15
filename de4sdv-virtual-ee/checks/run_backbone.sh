#!/usr/bin/env bash
# Run the backbone service and measure it.
#
# The same vehicle as the CAN demo: the zone controllers additionally expose a
# service on the Ethernet spine — an event at 10 Hz and one method at 2 Hz. This
# script brings the vehicle up, waits for both roles, lets them run, collects the
# JSON lines they log, and scores the run.
#
#   results/<utc>-<sha>-backbone/
#     provider.log     the provider container's log (kept on the testbed)
#     client.log       the client container's log (kept on the testbed)
#     provider.jsonl   only the service records, what the reader consumes
#     client.jsonl
#     summary.json     method RTT, event latency, jitter, misses
#     manifest.json    sha, lock hash, image digests, kernel
#
# Exit code: non-zero if the method never answered or no event arrived.
#
# Usage: checks/run_backbone.sh [--duration 30] [--keep]
set -euo pipefail

DURATION=30
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

SHA="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || cat "$ROOT/.git-sha" 2>/dev/null || echo unknown)"
OUT="$ROOT/results/$(date -u +%Y%m%dT%H%M%SZ)-$SHA-backbone"
mkdir -p "$OUT"

say() { printf '[backbone] %s\n' "$*"; }
die() { printf '[backbone] FAILED: %s\n' "$*" >&2; exit 1; }

teardown() {
  [ "${TORN_DOWN:-0}" -eq 1 ] && return 0
  TORN_DOWN=1
  if [ "$KEEP" -eq 1 ]; then say "--keep: leaving the vehicle up"; return 0; fi
  say "tearing the vehicle down"
  vxedge experiment down >"$OUT/experiment-down.log" 2>&1 || true
}
trap 'rc=$?; [ $rc -ne 0 ] && say "aborted with exit $rc"; teardown; exit $rc' EXIT

command -v vxedge >/dev/null || die "vxedge is not on PATH"
command -v podman >/dev/null || die "podman is not on PATH"
podman container exists ee-registry 2>/dev/null || die "the registry container ee-registry does not exist"
podman start ee-registry >/dev/null 2>&1 || true
if [ -z "${VXEDGE_ENDPOINT:-}" ] && [ ! -S /run/vxedge.sock ]; then
  user_sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/vxedge.sock"
  [ -S "$user_sock" ] || die "no vxedged socket"
  export VXEDGE_ENDPOINT="unix://$user_sock"
fi
timeout 20 vxedge status >/dev/null 2>&1 || die "vxedge cannot reach vxedged"
podman ps -a --filter status=exited --format '{{.Names}}' 2>/dev/null | grep '^vx-' | xargs -r podman rm -f >/dev/null 2>&1 || true
if [ ! -f "$PACKAGE/ota-store/root.json" ]; then
  command -v vxota >/dev/null || die "vxota is not on PATH"
  vxota keygen --artifacts-dir "$PACKAGE/ota-store" --out-priv "${OTA_KEY_PATH:-$HOME/.cache/de4sdv-ee/ota-demo.key}" \
    >"$OUT/ota-keygen.log" 2>&1 || die "vxota keygen failed"
fi

{
  echo "{"
  echo "  \"when_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"git_sha\": \"$SHA\","
  echo "  \"vxedge\": \"$(vxedge --version 2>/dev/null | head -1)\","
  echo "  \"lock_sha256\": \"$(sha256sum "$PACKAGE/vxp.lock" 2>/dev/null | cut -d' ' -f1)\","
  echo "  \"host\": \"$(uname -srmo)\","
  echo "  \"clock\": \"one host, one CLOCK_REALTIME: service stamps and reader share it\""
  echo "}"
} >"$OUT/manifest.json"

say "starting from a clean vehicle"
vxedge experiment down >"$OUT/experiment-preclean.log" 2>&1 || true
say "vehicle up"
timeout 180 vxedge experiment up --chdir "$PACKAGE" >"$OUT/experiment-up.log" 2>&1 || {
  tail -5 "$OUT/experiment-up.log" >&2
  die "experiment up failed"
}

say "waiting for both service roles"
ready=0
for _ in $(seq 1 45); do
  prov="$(podman logs "$FL_CTR" 2>&1 | grep -c 'provider_up' || true)"
  cli="$(podman logs "$RL_CTR" 2>&1 | grep -c 'client_up' || true)"
  if [ "${prov:-0}" -ge 1 ] && [ "${cli:-0}" -ge 1 ]; then ready=1; break; fi
  sleep 2
done
[ "$ready" -eq 1 ] || die "the service did not report up on both zones (see container logs)"

say "running for ${DURATION}s"
sleep "$DURATION"

say "collecting"
podman logs "$FL_CTR" >"$OUT/provider.log" 2>&1 || true
podman logs "$RL_CTR" >"$OUT/client.log" 2>&1 || true
grep -E '^\s*\[someip\] \{' "$OUT/provider.log" | sed -E 's/^\s*\[someip\] //' >"$OUT/provider.jsonl" || true
grep -E '^\s*\[someip\] \{' "$OUT/client.log" | sed -E 's/^\s*\[someip\] //' >"$OUT/client.jsonl" || true

teardown

set +e
python3 "$ROOT/checks/backbone_measure.py" \
  --provider-log "$OUT/provider.jsonl" \
  --client-log "$OUT/client.jsonl" \
  --out "$OUT/summary.json" >"$OUT/summary.txt" 2>&1
RC=$?
set -e
cat "$OUT/summary.txt"
say "verdict: $([ $RC -eq 0 ] && echo PASS || echo FAIL)"
say "archive: $OUT"
exit $RC
