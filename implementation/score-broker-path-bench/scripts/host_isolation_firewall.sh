#!/usr/bin/env bash
# Host isolation of the KVM guest segment (GAP-MW-046, owner-approved 2026-10-29).
# Defensive only: it drops the ports that no guest domain may reach. It never
# opens a port and never sends a packet.
#
#   host_isolation_firewall.sh add      install the rules (idempotent)
#   host_isolation_firewall.sh remove   remove them (the undo)
#   host_isolation_firewall.sh show     print the tables and their counters
#
# Two owner-approved rules, each in its own table so the undo is one delete:
# - REQ-MW-016 (verdict): in an inet input chain, drop the DDS ports of the
#   host ROS 2 domain and port 4721 of the frame assembler on every interface
#   except lo. By interface, not by source address: each VM also has a network
#   of its own, and CycloneDDS binds its receive sockets to every address.
# - REQ-MW-019 and REQ-MW-015 hardening (recorded design measure, not a pass
#   condition): in a bridge input chain, accept the SOME/IP ports to the host
#   only from the SDV Core VM's bridge port, matched by its address and MAC;
#   drop them from every other bridge port. The host's own traffic goes through
#   the bridge input hook, not the forward hook, so the rule sits there. An IP
#   match alone is not enough on a shared bridge, so it also matches the MAC and
#   pins a static neighbour entry. If the tap or MAC is unknown, the rule is
#   not installed and the script fails (no silent open).
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
ACTION="${1:-show}"
TABLE_INET="de4sdv_bench"
TABLE_BRIDGE="de4sdv_bench_bridge"

discover_core() {
  : "${CORE_MAC:=$(ip neigh show "$CORE_ADDR" dev "$HOST_BRIDGE" 2>/dev/null | awk '/lladdr/ {for(i=1;i<=NF;i++) if($i=="lladdr") print $(i+1)}')}"
  if [ -z "${CORE_TAP:-}" ] && [ -n "${CORE_MAC:-}" ]; then
    CORE_TAP="$(bridge fdb show br "$HOST_BRIDGE" 2>/dev/null | awk -v m="$CORE_MAC" '$1==m {print $3; exit}')"
  fi
}

ports_nft_set() {
  local out="" p
  for p in $(dds_udp_port_set); do out="${out:+$out, }$p"; done
  echo "$out"
}

add() {
  require_cmd nft ip bridge || { log "install nftables and iproute2 first"; return 1; }
  local dds; dds="$(ports_nft_set)"
  # REQ-MW-016: by-interface drop (every interface except lo). The two lines
  # before the block make the load idempotent: a re-run replaces the table
  # rather than appending the rules again (nft 1.0.2 has no `destroy`, so
  # `add table` ensures it exists and `delete table` then clears it; review R4).
  if ! sudo nft -f - <<NFT
add table inet ${TABLE_INET}
delete table inet ${TABLE_INET}
table inet ${TABLE_INET} {
  set dds_domain_udp { type inet_service; flags interval; elements = { ${dds} } }
  chain input {
    type filter hook input priority filter; policy accept;
    iifname "lo" accept
    udp dport @dds_domain_udp counter drop comment "REQ-MW-016: DDS ports off the guest, every interface but lo"
    tcp dport ${FRAME_ASSEMBLER_PORT} counter drop comment "ASM-MW-029: frame assembler off the guest"
  }
}
NFT
  then log "ERROR: installing inet ${TABLE_INET} failed"; return 1; fi
  sudo nft list table inet ${TABLE_INET} >/dev/null || { log "ERROR: inet ${TABLE_INET} not present after add"; return 1; }
  log "installed inet ${TABLE_INET} (DDS set ${dds}; TCP ${FRAME_ASSEMBLER_PORT})"

  discover_core
  if [ -z "${CORE_TAP:-}" ] || [ -z "${CORE_MAC:-}" ]; then
    log "ERROR: the SDV Core VM's tap or MAC is unknown (tap='${CORE_TAP:-}' mac='${CORE_MAC:-}')."
    log "Bring the core VM up first, or set CORE_TAP and CORE_MAC, then add again. Not installing the SOME/IP rule."
    return 1
  fi
  if ! sudo nft -f - <<NFT
add table bridge ${TABLE_BRIDGE}
delete table bridge ${TABLE_BRIDGE}
table bridge ${TABLE_BRIDGE} {
  chain input {
    type filter hook input priority filter; policy accept;
    iifname "${CORE_TAP}" ether saddr ${CORE_MAC} ip saddr ${CORE_ADDR} ip daddr { ${HOST_ADDR}, ${SD_GROUP} } udp dport ${SD_PORT} counter accept comment "SOME/IP SD from the SDV Core VM only"
    iifname "${CORE_TAP}" ether saddr ${CORE_MAC} ip saddr ${CORE_ADDR} ip daddr ${HOST_ADDR} tcp dport ${SOMEIP_RELIABLE_PORT} counter accept comment "SOME/IP event from the SDV Core VM only"
    ip daddr { ${HOST_ADDR}, ${SD_GROUP} } udp dport ${SD_PORT} counter drop comment "SOME/IP SD from any other bridge port"
    ip daddr ${HOST_ADDR} tcp dport ${SOMEIP_RELIABLE_PORT} counter drop comment "SOME/IP event from any other bridge port"
  }
}
NFT
  then log "ERROR: installing bridge ${TABLE_BRIDGE} failed"; return 1; fi
  sudo ip neigh replace "$CORE_ADDR" lladdr "$CORE_MAC" dev "$HOST_BRIDGE" nud permanent 2>/dev/null || true
  log "installed bridge ${TABLE_BRIDGE} bound to tap ${CORE_TAP} mac ${CORE_MAC} (recorded hardening, not a pass condition)"
}

remove() {
  sudo nft delete table inet ${TABLE_INET} 2>/dev/null && log "removed inet ${TABLE_INET}" || log "no inet ${TABLE_INET}"
  sudo nft delete table bridge ${TABLE_BRIDGE} 2>/dev/null && log "removed bridge ${TABLE_BRIDGE}" || log "no bridge ${TABLE_BRIDGE}"
  sudo ip neigh del "$CORE_ADDR" dev "$HOST_BRIDGE" 2>/dev/null || true
}

case "$ACTION" in
  add) add ;;
  remove) remove ;;
  show) sudo nft list table inet ${TABLE_INET} 2>&1 || true; sudo nft list table bridge ${TABLE_BRIDGE} 2>&1 || true ;;
  *) echo "usage: $0 {add|remove|show}" >&2; exit 2 ;;
esac
