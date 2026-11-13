#!/usr/bin/env bash
# Build the probe sender (de4sdv_probe_send) in the AOSP tree and push it to
# both guests, so the isolation probe (host_isolation_probe.sh), its control
# and the spoofed SD offer (send_sd_offer.sh) run the same, recorded bytes on
# the SDV Core VM and the IVI VM. The probe and the offer stop when a guest
# lacks the sender or holds other bytes than the run manifest records.
#
#   provision_probe_sender.sh build     stage aosp-overlay/probe-sender in the tree, build it, note the output path
#   provision_probe_sender.sh install   push the built sender to both guests, check and record its sha256
#   provision_probe_sender.sh remove    remove it from both guests and unstage it from the tree (the undo)
#
# The build uses the IVI lunch target; both guests are x86_64 Cuttlefish, so
# one binary serves both. The Android.bp flags are first checked by this build
# in S1 (CI compiles the C source with the host compiler only). The install
# writes the probe_sender block of RUN_DIR/run-manifest.yaml: the host path and
# sha256, the guest path, and the sha256 read back from each guest. It never
# dispatches a workflow and never runs on CI.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
: "${RUN_DIR:=$HERE/../run}"
OVERLAY="$HERE/../aosp-overlay/probe-sender"
: "${PROBE_SENDER_STAGE:=$AOSP_TOP/vendor/de4sdv_bench/probe-sender}"
MANIFEST="$RUN_DIR/run-manifest.yaml"

# The built sender: PROBE_SENDER_BIN, else the path the last build noted.
built_sender() {
  if [ -n "${PROBE_SENDER_BIN:-}" ]; then echo "$PROBE_SENDER_BIN"; return 0; fi
  [ -f "$RUN_DIR/.probe_sender_path" ] && cat "$RUN_DIR/.probe_sender_path"
}

build() {
  [ -d "$AOSP_TOP/build" ] || { log "ERROR: no AOSP tree at $AOSP_TOP"; return 1; }
  mkdir -p "$PROBE_SENDER_STAGE" "$RUN_DIR"
  cp "$OVERLAY/de4sdv_probe_send.c" "$OVERLAY/Android.bp" "$PROBE_SENDER_STAGE/"
  log "staged the probe sender in $PROBE_SENDER_STAGE"
  local out_path="$RUN_DIR/.probe_sender_path" rc=0
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${IVI_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m de4sdv_probe_send || exit 1
    echo "$ANDROID_PRODUCT_OUT/vendor/bin/de4sdv_probe_send" > "$out_path"
  ) 2>&1 | tail -5 || rc=1
  [ "${PIPESTATUS[0]:-0}" = 0 ] || rc=1
  if [ "$rc" != 0 ] || [ ! -f "$(cat "$out_path" 2>/dev/null)" ]; then
    log "ERROR: the probe sender build failed (the Android.bp flags are first checked here, in S1)"
    rm -f "$out_path"
    return 1
  fi
  log "built $(cat "$out_path")"
}

# Replace the probe_sender block of the run manifest (the rest is kept).
record_manifest() {
  local host_path="$1" host_sha="$2" core_sha="$3" ivi_sha="$4"
  mkdir -p "$RUN_DIR"
  MANIFEST="$MANIFEST" python3 - "$host_path" "$host_sha" "$core_sha" "$ivi_sha" "$PROBE_SENDER_GUEST" <<'PY'
import datetime, os, sys
path = os.environ["MANIFEST"]
host_path, host_sha, core_sha, ivi_sha, guest_path = sys.argv[1:6]
lines = open(path).read().splitlines() if os.path.exists(path) else []
kept, skipping = [], False
for line in lines:
    if line.startswith("probe_sender:"):
        skipping = True
        continue
    if skipping and line and not line.startswith(" "):
        skipping = False
    if not skipping:
        kept.append(line)
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
kept += ["probe_sender:", f"  recorded_at: {now}", f"  host_path: {host_path}", f"  host_sha256: {host_sha}",
         f"  guest_path: {guest_path}", f"  core_sha256: {core_sha}", f"  ivi_sha256: {ivi_sha}"]
open(path, "w").write("\n".join(kept) + "\n")
PY
}

install() {
  require_cmd "$ADB" sha256sum || return 1
  local host_path host_sha serial guest_sha core_sha="" ivi_sha=""
  host_path="$(built_sender)"
  if [ -z "$host_path" ] || [ ! -f "$host_path" ]; then
    log "ERROR: the built probe sender was not found (${host_path:-no path}); run $0 build or set PROBE_SENDER_BIN"
    return 1
  fi
  host_sha="$(sha256sum "$host_path" | awk '{print $1}')"
  for serial in "$CORE_ADB" "$IVI_ADB"; do
    "$ADB" connect "$serial" >/dev/null 2>&1 || true
    "$ADB" -s "$serial" root >/dev/null 2>&1 || true
    "$ADB" -s "$serial" wait-for-device
    "$ADB" -s "$serial" push "$host_path" "$PROBE_SENDER_GUEST" 2>&1 | tail -1
    "$ADB" -s "$serial" shell "chmod 755 $PROBE_SENDER_GUEST" >/dev/null 2>&1 || true
    guest_sha="$("$ADB" -s "$serial" shell "sha256sum $PROBE_SENDER_GUEST 2>/dev/null" 2>/dev/null | tr -d '\r' | awk '{print $1}')"
    if [ "$guest_sha" != "$host_sha" ]; then
      log "ERROR: the sender on $serial (${guest_sha:-missing}) differs from $host_path ($host_sha); nothing recorded"
      return 1
    fi
    if [ "$serial" = "$CORE_ADB" ]; then core_sha="$guest_sha"; else ivi_sha="$guest_sha"; fi
    log "pushed the probe sender to $serial at $PROBE_SENDER_GUEST (sha256 $guest_sha)"
  done
  record_manifest "$host_path" "$host_sha" "$core_sha" "$ivi_sha"
  log "recorded the probe sender in $MANIFEST"
  mkdir -p "$RUN_DIR"
  echo "probe sender $(date -u +%FT%T.%NZ): pushed to both guests at $PROBE_SENDER_GUEST (sha256 $host_sha); undo 'scripts/provision_probe_sender.sh remove'" \
    >> "$RUN_DIR/vm-change-log.session.txt"
}

remove() {
  local serial
  for serial in "$CORE_ADB" "$IVI_ADB"; do
    "$ADB" connect "$serial" >/dev/null 2>&1 || true
    "$ADB" -s "$serial" shell "rm -f $PROBE_SENDER_GUEST" >/dev/null 2>&1 || true
  done
  if [ -d "$PROBE_SENDER_STAGE" ]; then
    rm -f -- "$PROBE_SENDER_STAGE/de4sdv_probe_send.c" "$PROBE_SENDER_STAGE/Android.bp"
    rmdir "$PROBE_SENDER_STAGE" 2>/dev/null || true
  fi
  log "removed the probe sender from both guests and from the tree"
}

case "${1:-}" in
  build) build ;;
  install) install ;;
  remove) remove ;;
  *) echo "usage: $0 {build|install|remove}" >&2; exit 2 ;;
esac
