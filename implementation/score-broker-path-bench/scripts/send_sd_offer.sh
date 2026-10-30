#!/usr/bin/env bash
# Send one SOME/IP service-discovery offer of the frame service from the IVI VM
# on the shared bridge segment (VC-MW-016: the SD offer that must not redirect
# the SDV Core VM's subscription). It builds the SD bytes and sends them with
# the bench sender, from the SD source port 30490, so the core's SOME/IP stack
# does not ignore the message (a stack drops an SD message from any other
# source port, review R43). Around the send it takes the SDV Core VM's logcat
# and writes sd_core_processed.json: whether the core stack processed the offer
# (its SD module read and refused it) or ignored it before service discovery,
# with the matched log line, or "unknown" when no line matched, which keeps
# VC-MW-016 inconclusive. The default lines are vsomeip 3.1.37.1's (see sd.py);
# S1 confirms them on the image. The evaluator reads the provider after the
# offer from host-cvd-ebr.pcap. It never dispatches a workflow and never runs on CI.
#
#   send_sd_offer.sh send <provider-addr> <reliable-port> <run-dir>   send the offer, record the core's line
#   send_sd_offer.sh bytes <provider-addr> <reliable-port>            print the raw SD datagram (for a test)
#
# Settings: SD_PROCESS_WAIT_S (seconds of core logcat after the send, default 3);
# SD_PROCESSED_PATTERNS and SD_IGNORED_PATTERNS (NAME=REGEX per line) replace
# the vsomeip 3.1.37.1 lines when S1 finds the image logs other ones.
# The offer names service 0x4dee instance 0x0001 major 1 with a positive TTL
# and an IPv4 endpoint of <provider-addr>:<reliable-port>/tcp, so a stack that
# honours it would subscribe to that provider instead of the host.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
: "${PROBE_SENDER:=$PROBE_SENDER_GUEST}"  # the guest sender (provision_probe_sender.sh install)
: "${RUN_DIR:=$HERE/../run}"             # the session run directory with run-manifest.yaml
: "${SD_PROCESS_WAIT_S:=3}"
: "${SD_PROCESSED_PATTERNS:=}"
: "${SD_IGNORED_PATTERNS:=}"
SCAN=(python3 -m de4sdv_broker_path_bench.hostscan)
export PYTHONPATH="$HERE/../src${PYTHONPATH:+:$PYTHONPATH}"

FRAME_SERVICE_HEX=4dee        # service 0x4dee, instance 0x0001 (the overlay's frame service)
FRAME_INSTANCE_HEX=0001

# The SD datagram as a lowercase hex string. All multi-byte fields are
# big-endian. The layout matches the SOME/IP-SD reader (src/.../sd.py) and the
# test builder: a SOME/IP header, the SD payload (flags, one offer entry, one
# IPv4 endpoint option).
_offer_hex() {
  local addr="$1" port="$2" a b c d ip_hex port_hex
  IFS=. read -r a b c d <<EOF
$addr
EOF
  ip_hex="$(printf '%02x%02x%02x%02x' "$a" "$b" "$c" "$d")"
  port_hex="$(printf '%04x' "$port")"
  # IPv4 endpoint option: length 0x0009, type 0x04, reserved, address,
  # reserved, protocol 0x06 (tcp), port.
  local option="00090400${ip_hex}0006${port_hex}"
  # Offer entry (type 0x01): first-option index 0, one option in the first run
  # (0x10), service, instance, major 1, TTL 0x000003, minor 0x00000000.
  local entry="01000010${FRAME_SERVICE_HEX}${FRAME_INSTANCE_HEX}0100000300000000"
  local entries_len options_len
  entries_len="$(printf '%08x' $(( ${#entry} / 2 )))"
  options_len="$(printf '%08x' $(( ${#option} / 2 )))"
  # SD payload: flags 0xc0 (reboot+unicast), 3 reserved bytes, entries, options.
  local payload="c0000000${entries_len}${entry}${options_len}${option}"
  local length
  length="$(printf '%08x' $(( 8 + ${#payload} / 2 )))"
  # SOME/IP header: service 0xffff, method 0x8100, length, client 0, session 1,
  # protocol 1, interface 1, message type 0x02 (notification), return code 0.
  printf 'ffff8100%s0000000101010200%s' "$length" "$payload"
}

case "${1:-}" in
  bytes)
    _offer_hex "${2:?usage: $0 bytes <provider-addr> <reliable-port>}" "${3:?reliable port}" | xxd -r -p
    ;;
  send)
    addr="${2:?usage: $0 send <provider-addr> <reliable-port> <run-dir>}"; port="${3:?reliable port}"
    OUT="${4:?usage: $0 send <provider-addr> <reliable-port> <run-dir>}"; mkdir -p "$OUT"
    require_cmd "$ADB" || true
    "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
    "$ADB" connect "$CORE_ADB" >/dev/null 2>&1 || true
    # The sender must be on the IVI with the bytes the run manifest records
    # (provision_probe_sender.sh install); stop before sending otherwise.
    expected="$(run_manifest_sender_sha256 "$RUN_DIR/run-manifest.yaml" 2>/dev/null)"
    found="$("$ADB" -s "$IVI_ADB" shell "sha256sum $PROBE_SENDER 2>/dev/null" 2>/dev/null | tr -d '\r' | awk '{print $1}')"
    if [ -z "$expected" ] || [ "$found" != "$expected" ]; then
      log "ERROR: the probe sender on the IVI (${found:-missing}) does not match the run manifest (${expected:-not recorded}); run provision_probe_sender.sh install first"
      exit 1
    fi
    local_hex="$(_offer_hex "$addr" "$port")"
    # The IVI's bridge-facing device and source address, from its own routing
    # toward the host segment, so the sender binds the real interface.
    route="$("$ADB" -s "$IVI_ADB" shell "ip route get $HOST_ADDR 2>/dev/null" | tr -d '\r')"
    dev="$(printf '%s\n' "$route" | sed -n 's/.* dev \([^ ]*\).*/\1/p' | head -1)"
    src="$(printf '%s\n' "$route" | sed -n 's/.* src \([^ ]*\).*/\1/p' | head -1)"
    if [ -z "$dev" ] || [ -z "$src" ]; then
      log "ERROR: could not find the IVI's bridge device or source for $HOST_ADDR; cannot send the offer"
      exit 1
    fi
    # The core's logcat around the offer, from a second before the send on the
    # core's own clock (its logcat timestamps), so the stack's line about this
    # offer is found and an older one is not.
    core_now="$("$ADB" -s "$CORE_ADB" shell "date +%s" 2>/dev/null | tr -d '\r' | head -1)"
    case "$core_now" in ''|*[!0-9]*) log "ERROR: could not read the SDV Core VM clock"; exit 1 ;; esac
    since=$(( core_now - 1 ))
    "$ADB" -s "$CORE_ADB" logcat -v epoch -v usec -T 1 > "$OUT/core-logcat-sd-offer.txt" 2>/dev/null &
    logcat_pid=$!
    sleep 1
    log "sending a spoofed SD offer of service 0x${FRAME_SERVICE_HEX}.${FRAME_INSTANCE_HEX} (provider ${addr}:${port}) from the IVI VM, source port ${SD_PORT}"
    # The sender binds the SD source port (${SD_PORT}); the raw bytes are fed on
    # stdin. A stack ignores an SD message from any other source port (R43).
    send_rc=0
    "$ADB" -s "$IVI_ADB" shell "echo -n '$local_hex' | toybox xxd -r -p | timeout ${PROBE_SEND_TIMEOUT:-2} $PROBE_SENDER --device $dev --source $src --sport ${SD_PORT} --host ${SD_GROUP} --port ${SD_PORT}" \
      >/dev/null 2>&1 || send_rc=$?
    sleep "$SD_PROCESS_WAIT_S"
    kill "$logcat_pid" 2>/dev/null || true
    wait "$logcat_pid" 2>/dev/null || true
    pattern_args=()
    if [ -n "$SD_PROCESSED_PATTERNS" ]; then
      while IFS= read -r item; do [ -n "$item" ] && pattern_args+=(--processed-pattern "$item"); done <<< "$SD_PROCESSED_PATTERNS"
    fi
    if [ -n "$SD_IGNORED_PATTERNS" ]; then
      while IFS= read -r item; do [ -n "$item" ] && pattern_args+=(--ignored-pattern "$item"); done <<< "$SD_IGNORED_PATTERNS"
    fi
    "${SCAN[@]}" sd-processed --logcat "$OUT/core-logcat-sd-offer.txt" --since "$since" --provider "$addr" \
      "${pattern_args[@]}" --out "$OUT/sd_core_processed.json" | sed 's/^/core stack: /'
    if [ "$send_rc" != 0 ]; then
      log "ERROR: the guest send returned $send_rc (the sender's errno); the offer may not have left the IVI"
      exit 1
    fi
    log "offer sent; the core stack's record is in $OUT/sd_core_processed.json"
    ;;
  *) echo "usage: $0 {send <provider-addr> <reliable-port> <run-dir>|bytes <provider-addr> <reliable-port>}" >&2; exit 2 ;;
esac
